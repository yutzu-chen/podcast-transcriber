"""
Background Service - Handles audio processing and transcription in the background
"""

import threading
import queue
import time
from typing import Dict, Any, Optional

from .audio_service import AudioService
from .transcription_service import TranscriptionService

class BackgroundService:
    """Background service for processing audio and transcriptions"""
    
    def __init__(self, audio_service: AudioService, transcription_service: TranscriptionService):
        self.audio_service = audio_service
        self.transcription_service = transcription_service
        self.processing_threads: Dict[str, threading.Thread] = {}
        self.is_running = True
        
        # Start the main processing loop
        self.main_thread = threading.Thread(target=self._main_processing_loop, daemon=True)
        self.main_thread.start()
    
    def _main_processing_loop(self):
        """Main processing loop that handles audio from all sessions"""
        while self.is_running:
            try:
                # Check all active sessions for audio data
                for session_id in list(self.audio_service.active_sessions.keys()):
                    if session_id not in self.processing_threads:
                        # Start processing thread for this session
                        thread = threading.Thread(
                            target=self._process_session_audio,
                            args=(session_id,),
                            daemon=True
                        )
                        self.processing_threads[session_id] = thread
                        thread.start()
                
                # Clean up finished threads
                finished_sessions = []
                for session_id, thread in self.processing_threads.items():
                    if not thread.is_alive() and session_id not in self.audio_service.active_sessions:
                        finished_sessions.append(session_id)
                
                for session_id in finished_sessions:
                    del self.processing_threads[session_id]
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                print(f"Error in main processing loop: {e}")
                time.sleep(1)
    
    def _process_session_audio(self, session_id: str):
        """Process audio for a specific session"""
        try:
            audio_queue = self.audio_service.get_audio_queue(session_id)
            if not audio_queue:
                return
            
            while (session_id in self.audio_service.active_sessions and 
                   self.audio_service.is_recording(session_id)):
                try:
                    # Get audio data from queue (with timeout)
                    audio_data = audio_queue.get(timeout=1.0)
                    
                    if audio_data['type'] == 'audio_chunk':
                        # Transcribe the audio
                        result = self.transcription_service.transcribe_audio_data(
                            audio_data['data'],
                            audio_data['sample_rate']
                        )
                        
                        if result['success'] and result['text'].strip():
                            # Process the transcription
                            processed = self.transcription_service.process_transcription(result['text'])
                            
                            if processed['success']:
                                # Send complete sentences to the session
                                for sentence in processed['complete_sentences']:
                                    self._send_transcription_to_session(session_id, sentence, complete=True)
                                
                                # Send current sentence if it exists
                                if processed['current_sentence']:
                                    self._send_transcription_to_session(session_id, processed['current_sentence'], complete=False)
                    
                    audio_queue.task_done()
                    
                except queue.Empty:
                    # No audio data available, continue
                    continue
                except Exception as e:
                    print(f"Error processing audio for session {session_id}: {e}")
                    break
                    
        except Exception as e:
            print(f"Error in session audio processing for {session_id}: {e}")
    
    def _send_transcription_to_session(self, session_id: str, text: str, complete: bool = False):
        """Send transcription to session (this would integrate with the Flask app)"""
        # This method would be called by the Flask app to update sessions
        # For now, we'll just print the result
        print(f"Session {session_id}: {'Complete' if complete else 'Current'} - {text}")
    
    def stop(self):
        """Stop the background service"""
        self.is_running = False
        if self.main_thread.is_alive():
            self.main_thread.join(timeout=2.0)
