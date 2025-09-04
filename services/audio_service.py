"""
Audio Service - Handles audio recording and processing
"""

import os
import threading
import queue
import tempfile
import wave
import time
from typing import Dict, Any, Optional

import numpy as np
import sounddevice as sd

class AudioService:
    """Service for handling audio recording and processing"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.audio_threads: Dict[str, threading.Thread] = {}
        self.audio_queues: Dict[str, queue.Queue] = {}
        
        # Audio settings
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_duration = 0.1  # 100ms chunks
        self.silence_threshold = 0.01
        self.min_silence_duration = 1.5  # seconds
        self.max_buffer_duration = 8  # seconds
        
    def start_recording(self, session_id: str) -> bool:
        """Start audio recording for a session"""
        try:
            if session_id in self.active_sessions:
                print(f"Session {session_id} already recording")
                return True
            
            # Initialize session
            self.active_sessions[session_id] = {
                'is_recording': True,
                'audio_buffer': [],
                'silence_duration': 0,
                'last_audio_time': 0,
                'last_processing_time': 0
            }
            
            # Create audio queue for this session
            self.audio_queues[session_id] = queue.Queue()
            
            # Start audio recording thread
            audio_thread = threading.Thread(
                target=self._record_audio,
                args=(session_id,),
                daemon=True
            )
            self.audio_threads[session_id] = audio_thread
            audio_thread.start()
            
            print(f"Started recording for session {session_id}")
            return True
            
        except Exception as e:
            print(f"Error starting recording for session {session_id}: {e}")
            return False
    
    def stop_recording(self, session_id: str) -> bool:
        """Stop audio recording for a session"""
        try:
            if session_id not in self.active_sessions:
                print(f"Session {session_id} not found")
                return False
            
            # Stop recording
            self.active_sessions[session_id]['is_recording'] = False
            
            # Wait for audio thread to finish
            if session_id in self.audio_threads:
                self.audio_threads[session_id].join(timeout=2.0)
                del self.audio_threads[session_id]
            
            # Clean up session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            if session_id in self.audio_queues:
                del self.audio_queues[session_id]
            
            print(f"Stopped recording for session {session_id}")
            return True
            
        except Exception as e:
            print(f"Error stopping recording for session {session_id}: {e}")
            return False
    
    def _record_audio(self, session_id: str):
        """Audio recording thread function"""
        try:
            print(f"Starting audio recording thread for session {session_id}")
            
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                device=None,
                blocksize=int(self.sample_rate * self.chunk_duration)
            ) as stream:
                chunk_count = 0
                
                while (session_id in self.active_sessions and 
                       self.active_sessions[session_id]['is_recording']):
                    try:
                        # Record audio chunk
                        audio_chunk, _ = stream.read(int(self.sample_rate * self.chunk_duration))
                        self.active_sessions[session_id]['audio_buffer'].extend(audio_chunk.flatten())
                        chunk_count += 1
                        
                        # Calculate current time
                        current_time = chunk_count * self.chunk_duration
                        
                        # Check if we should process audio
                        if self._should_process_audio(session_id, current_time):
                            print(f"Processing audio chunk {chunk_count} for session {session_id}")
                            self._process_audio_chunk(session_id)
                            self.active_sessions[session_id]['last_processing_time'] = current_time
                            
                    except Exception as e:
                        print(f"Audio recording error for session {session_id}: {e}")
                        break
                        
        except Exception as e:
            print(f"Audio setup error for session {session_id}: {e}")
        finally:
            print(f"Audio recording thread ended for session {session_id}")
    
    def _should_process_audio(self, session_id: str, current_time: float) -> bool:
        """Determine if audio should be processed based on silence detection"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        audio_buffer = session['audio_buffer']
        
        if not audio_buffer:
            return False
        
        # Calculate audio volume (RMS) from last 0.5 seconds
        recent_samples = int(self.sample_rate * 0.5)
        audio_array = np.array(audio_buffer[-recent_samples:]) if len(audio_buffer) >= recent_samples else np.array(audio_buffer)
        
        if len(audio_array) == 0:
            return False
        
        rms_volume = np.sqrt(np.mean(audio_array**2))
        
        # Check for silence
        is_silent = rms_volume < self.silence_threshold
        
        if is_silent:
            session['silence_duration'] += self.chunk_duration
        else:
            session['silence_duration'] = 0
            session['last_audio_time'] = current_time
        
        # Decision logic:
        # 1. Send if we've had silence for min_silence_duration seconds
        if session['silence_duration'] >= self.min_silence_duration:
            print(f"Sending due to silence: {session['silence_duration']:.1f}s")
            return True
        
        # 2. Send if buffer is getting too long
        buffer_duration = len(audio_buffer) / self.sample_rate
        if buffer_duration >= self.max_buffer_duration:
            print(f"Sending due to max buffer duration: {buffer_duration:.1f}s")
            return True
        
        # 3. Send if we've been recording for a while without processing
        time_since_last_processing = current_time - session['last_processing_time']
        if time_since_last_processing >= 5.0:
            print(f"Sending due to time since last processing: {time_since_last_processing:.1f}s")
            return True
        
        return False
    
    def _process_audio_chunk(self, session_id: str):
        """Process audio chunk and send for transcription"""
        try:
            session = self.active_sessions[session_id]
            audio_buffer = session['audio_buffer'].copy()
            
            # Keep last 2 seconds for context
            keep_samples = int(self.sample_rate * 2)
            session['audio_buffer'] = audio_buffer[-keep_samples:] if len(audio_buffer) > keep_samples else []
            
            # Send audio data to queue for transcription
            if session_id in self.audio_queues:
                self.audio_queues[session_id].put({
                    'type': 'audio_chunk',
                    'data': audio_buffer,
                    'sample_rate': self.sample_rate,
                    'timestamp': time.time()
                })
            
        except Exception as e:
            print(f"Error processing audio chunk for session {session_id}: {e}")
    
    def get_audio_queue(self, session_id: str) -> Optional[queue.Queue]:
        """Get audio queue for a session"""
        return self.audio_queues.get(session_id)
    
    def is_recording(self, session_id: str) -> bool:
        """Check if a session is currently recording"""
        return (session_id in self.active_sessions and 
                self.active_sessions[session_id]['is_recording'])
