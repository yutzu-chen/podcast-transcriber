"""
Transcription Service - Handles speech-to-text conversion
"""

import os
import tempfile
import wave
import requests
from typing import Dict, Any, Optional

import numpy as np

class TranscriptionService:
    """Service for handling speech-to-text transcription"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
    
    def transcribe_audio_data(self, audio_data: list, sample_rate: int = 16000) -> Dict[str, Any]:
        """Transcribe audio data using OpenAI Whisper API"""
        try:
            # Convert to numpy array if not already
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data)
            
            # Normalize audio
            if len(audio_data) > 0:
                max_val = np.max(np.abs(audio_data))
                if max_val > 0:
                    audio_data = audio_data / max_val
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                
                # Write WAV file
                with wave.open(temp_filename, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    
                    # Convert float32 to int16
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                    wav_file.writeframes(audio_int16.tobytes())
                
                # Transcribe using OpenAI API
                result = self._transcribe_file(temp_filename)
                
                # Clean up temp file
                os.unlink(temp_filename)
                
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    def transcribe_file(self, file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using OpenAI Whisper API"""
        try:
            result = self._transcribe_file(file_path)
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    def _transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        """Internal method to transcribe audio file"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'No API key available',
                    'text': ''
                }
            
            # Prepare the request
            url = "https://api.openai.com/v1/audio/transcriptions"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Read the audio file
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': (audio_file_path, audio_file, 'audio/wav')
                }
                data = {
                    'model': 'whisper-1',
                    'language': 'de',  # German
                    'response_format': 'json'
                }
                
                # Make the request
                response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        'success': True,
                        'text': result.get('text', ''),
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'error': f"API error: {response.status_code} - {response.text}",
                        'text': ''
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    def process_transcription(self, text: str) -> Dict[str, Any]:
        """Process transcription text and extract sentences"""
        try:
            # Simple sentence detection
            sentences = []
            current = ""
            
            for char in text:
                current += char
                if char in '.!?':
                    sentence = current.strip()
                    if sentence and len(sentence) > 1:
                        sentences.append(sentence)
                    current = ""
            
            # Handle remaining text
            remaining = current.strip()
            
            return {
                'success': True,
                'complete_sentences': sentences,
                'current_sentence': remaining,
                'full_text': text
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'complete_sentences': [],
                'current_sentence': '',
                'full_text': text
            }
