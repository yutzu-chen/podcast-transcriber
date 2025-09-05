#!/usr/bin/env python3
"""
Podcast Transcriber Web Application
Main Flask application with REST API endpoints
"""

import os
import json
import threading
import queue
import tempfile
import wave
import time
from datetime import datetime
from typing import Dict, Any, Optional

import numpy as np
import sounddevice as sd
import requests
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Import our services
from services.audio_service import AudioService
from services.dictionary_service import DictionaryService
from services.transcription_service import TranscriptionService
from services.background_service import BackgroundService

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp'

# Create upload directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

# Initialize services
audio_service = AudioService()
dictionary_service = DictionaryService()
transcription_service = TranscriptionService()
background_service = BackgroundService(audio_service, transcription_service)

# Global state for active sessions
active_sessions: Dict[str, Dict[str, Any]] = {}

# Background processing thread
def process_audio_transcriptions():
    """Background thread to process audio and generate transcriptions"""
    while True:
        try:
            # Check all active sessions for audio data
            for session_id in list(active_sessions.keys()):
                if session_id in audio_service.audio_queues:
                    audio_queue = audio_service.audio_queues[session_id]
                    
                    try:
                        # Get audio data from queue (with timeout)
                        audio_data = audio_queue.get(timeout=1.0)
                        
                        if audio_data['type'] == 'audio_chunk':
                            print(f"Processing audio chunk for session {session_id}")
                            # Transcribe the audio
                            result = transcription_service.transcribe_audio_data(
                                audio_data['data'],
                                audio_data['sample_rate']
                            )
                            
                            print(f"Transcription result: {result}")
                            
                            if result['success'] and result['text'].strip():
                                print(f"Got transcription text: {result['text']}")
                                # Process the transcription
                                processed = transcription_service.process_transcription(result['text'])
                                
                                print(f"Processed transcription: {processed}")
                                
                                if processed['success']:
                                    # Send complete sentences to the session
                                    for sentence in processed['complete_sentences']:
                                        if session_id in active_sessions:
                                            active_sessions[session_id]['transcriptions'].append({
                                                'text': sentence,
                                                'timestamp': datetime.now().isoformat(),
                                                'complete': True
                                            })
                                            print(f"Added complete sentence: {sentence}")
                                    
                                    # Update current sentence if it exists
                                    if processed['current_sentence']:
                                        if session_id in active_sessions:
                                            active_sessions[session_id]['current_sentence'] = processed['current_sentence']
                                            print(f"Updated current sentence: {processed['current_sentence']}")
                            else:
                                print(f"Transcription failed or empty: {result}")
                        
                        audio_queue.task_done()
                        
                    except queue.Empty:
                        # No audio data available, continue
                        continue
                    except Exception as e:
                        print(f"Error processing audio for session {session_id}: {e}")
                        break
            
            time.sleep(0.1)  # Small delay to prevent busy waiting
            
        except Exception as e:
            print(f"Error in transcription processing loop: {e}")
            time.sleep(1)

# Start background processing thread
transcription_thread = threading.Thread(target=process_audio_transcriptions, daemon=True)
transcription_thread.start()

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return app.send_static_file('favicon.ico')

@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon():
    """Serve apple touch icon"""
    return app.send_static_file('favicon.ico')

@app.route('/api/start-recording', methods=['POST'])
def start_recording():
    """Start audio recording session"""
    session_id = request.json.get('session_id', f'session_{int(time.time())}')
    
    try:
        # Initialize session
        active_sessions[session_id] = {
            'is_recording': True,
            'transcriptions': [],
            'current_sentence': '',
            'start_time': datetime.now().isoformat()
        }
        
        # Start audio recording
        audio_service.start_recording(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Recording started'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stop-recording', methods=['POST'])
def stop_recording():
    """Stop audio recording session"""
    session_id = request.json.get('session_id')
    
    if not session_id or session_id not in active_sessions:
        return jsonify({
            'success': False,
            'error': 'Invalid session ID'
        }), 400
    
    try:
        # Stop audio recording
        audio_service.stop_recording(session_id)
        
        # Update session
        active_sessions[session_id]['is_recording'] = False
        active_sessions[session_id]['end_time'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': 'Recording stopped'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transcriptions/<session_id>')
def get_transcriptions(session_id):
    """Get transcriptions for a session"""
    if session_id not in active_sessions:
        return jsonify({
            'success': False,
            'error': 'Session not found'
        }), 404
    
    session = active_sessions[session_id]
    return jsonify({
        'success': True,
        'transcriptions': session['transcriptions'],
        'current_sentence': session['current_sentence'],
        'is_recording': session['is_recording']
    })

@app.route('/api/transcriptions/<session_id>', methods=['POST'])
def add_transcription(session_id):
    """Add a new transcription to a session"""
    if session_id not in active_sessions:
        return jsonify({
            'success': False,
            'error': 'Session not found'
        }), 404
    
    data = request.json
    transcription_text = data.get('text', '').strip()
    is_complete = data.get('complete', False)
    
    if not transcription_text:
        return jsonify({
            'success': False,
            'error': 'No transcription text provided'
        }), 400
    
    try:
        session = active_sessions[session_id]
        
        if is_complete:
            # Add as completed sentence
            session['transcriptions'].append({
                'text': transcription_text,
                'timestamp': datetime.now().isoformat(),
                'complete': True
            })
            session['current_sentence'] = ''
        else:
            # Update current sentence
            session['current_sentence'] = transcription_text
        
        return jsonify({
            'success': True,
            'message': 'Transcription added'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dictionary/<word>')
def get_word_definition(word):
    """Get word definition from dictionary service"""
    try:
        definition = dictionary_service.get_definition(word)
        return jsonify({
            'success': True,
            'word': word,
            'definition': definition
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    """Upload audio file for transcription"""
    if 'audio' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No audio file provided'
        }), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Transcribe the audio
        transcription = transcription_service.transcribe_file(filepath)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'transcription': transcription
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sessions')
def list_sessions():
    """List all active sessions"""
    return jsonify({
        'success': True,
        'sessions': list(active_sessions.keys())
    })

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return jsonify({
            'success': True,
            'message': 'Session deleted'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Session not found'
        }), 404

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len(active_sessions)
    })

if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the application
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🎙️ Starting Podcast Transcriber Web App on port {port}")
    print(f"📱 Open your browser to: http://localhost:{port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
