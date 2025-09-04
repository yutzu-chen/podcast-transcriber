import sys
import threading
import queue
import time
import tempfile
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel,
    QTextBrowser, QHBoxLayout, QSplitter, QFrame, QPushButton,
    QScrollArea, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor, QTextCharFormat

# OpenAI imports
try:
    import requests
    import sounddevice as sd
    import numpy as np
    import wave
    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    print(f"Required packages not available: {e}")
    print("Install with: pip install requests sounddevice numpy")

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    print(f"API Key loaded: {bool(OPENAI_API_KEY)}")
    if OPENAI_API_KEY:
        print(f"API Key starts with: {OPENAI_API_KEY[:10]}...")
except ImportError:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    print(f"API Key loaded (no dotenv): {bool(OPENAI_API_KEY)}")

class AudioTranscriber(QObject):
    transcription_updated = pyqtSignal(str)
    status_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.is_listening = False
        self.audio_thread = None
        self.sentences = []  # Store completed sentences
        self.current_sentence = ""  # Current sentence being transcribed
        
        # Smart audio buffering settings
        self.audio_buffer = []
        self.chunk_count = 0
        self.silence_detection_threshold = 0.01  # Volume threshold for silence
        self.silence_duration = 0  # Track silence duration in seconds
        self.min_silence_for_send = 1.5  # Send after 1.5 seconds of silence
        self.max_buffer_duration = 8  # Maximum 8 seconds before forced send
        self.last_audio_time = 0
        self.chunk_duration = 0.1  # Process in 100ms chunks for responsiveness
        self.last_processing_time = 0
        
        if OPENAI_AVAILABLE and OPENAI_API_KEY:
            print("OpenAI API ready (using direct requests)")
            self.api_key = OPENAI_API_KEY
            self.client = "requests"  # Use requests instead of OpenAI client
        else:
            print("OpenAI not available or API key not found")
    
    def start_listening(self):
        if not OPENAI_AVAILABLE:
            self.status_updated.emit("OpenAI not available")
            return
            
        if not self.client:
            self.status_updated.emit("OpenAI API not ready")
            return
            
        if self.is_listening:
            print("Already listening, ignoring start request")
            return
            
        print("Starting listening...")
        self.is_listening = True
        self.status_updated.emit("Listening...")
        
        # Reset audio buffering state
        self.chunk_count = 0
        self.silence_duration = 0
        self.last_audio_time = 0
        self.last_processing_time = 0
        
        # Don't clear previous transcription - keep accumulating
        
        # Start audio recording thread
        self.audio_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.audio_thread.start()
        print("Audio thread started")
    
    def stop_listening(self):
        self.is_listening = False
        # Process any remaining audio in buffer
        if self.audio_buffer and len(self.audio_buffer) > 16000:  # At least 1 second
            print("Processing remaining audio on stop...")
            self._process_audio_chunk(self.audio_buffer, 16000)
        
        # If there's a current sentence, add it as a completed sentence
        if self.current_sentence and self.current_sentence.strip():
            self.sentences.append(self.current_sentence.strip())
            self.transcription_updated.emit(self.current_sentence.strip())
            self.current_sentence = ""
        self.status_updated.emit("Ready to listen")
    
    def _record_audio(self):
        try:
            # Audio recording parameters
            sample_rate = 16000
            channels = 1
            
            print("Starting audio recording...")
            print("Available audio devices:")
            print(sd.query_devices())
            
            # Try to use the default input device (usually microphone)
            try:
                with sd.InputStream(
                    samplerate=sample_rate, 
                    channels=channels, 
                    dtype=np.float32,
                    device=None,  # Use default input device
                    blocksize=int(sample_rate * self.chunk_duration)  # 100ms chunks
                ) as stream:
                    chunk_count = 0
                    chunk_count = 0
                    
                    while self.is_listening:
                        try:
                            # Record audio in chunks
                            audio_chunk, _ = stream.read(int(sample_rate * self.chunk_duration))
                            self.audio_buffer.extend(audio_chunk.flatten())
                            chunk_count += 1
                            
                            # Process audio every 3 seconds
                            if len(self.audio_buffer) >= sample_rate * 3:  # 3 seconds of audio
                                print(f"Processing audio chunk {chunk_count}...")
                                self._process_audio_chunk(self.audio_buffer, sample_rate)
                                self.audio_buffer = self.audio_buffer[sample_rate * 3:]  # Keep last 3 seconds
                                
                        except Exception as e:
                            print(f"Audio recording error: {e}")
                            break
                            
            except Exception as e:
                print(f"Failed to open audio stream: {e}")
                print("Trying alternative audio device...")
                # Try with explicit device selection
                devices = sd.query_devices()
                input_devices = [i for i, device in enumerate(devices) if device['max_input_channels'] > 0]
                if input_devices:
                    print(f"Available input devices: {input_devices}")
                    device_id = input_devices[0]  # Use first available input device
                    print(f"Using device {device_id}: {devices[device_id]['name']}")
                    
                    with sd.InputStream(
                        samplerate=sample_rate, 
                        channels=channels, 
                        dtype=np.float32,
                        device=device_id,
                        blocksize=int(sample_rate * self.chunk_duration)  # 100ms chunks
                    ) as stream:
                        chunk_count = 0
                        chunk_count = 0
                        
                        while self.is_listening:
                            try:
                                # Record audio in chunks
                                audio_chunk, _ = stream.read(int(sample_rate * self.chunk_duration))
                                self.audio_buffer.extend(audio_chunk.flatten())
                                chunk_count += 1
                                
                                # Calculate current time
                                current_time = chunk_count * self.chunk_duration
                                
                                # Check if we should process audio
                                should_process = self._should_process_audio(current_time)
                                
                                if should_process:
                                    print(f"Processing audio chunk {chunk_count} (smart timing)...")
                                    self._process_audio_chunk(self.audio_buffer.copy(), sample_rate)
                                    # Keep last 2 seconds for context
                                    keep_samples = int(sample_rate * 2)
                                    self.audio_buffer = self.audio_buffer[-keep_samples:] if len(self.audio_buffer) > keep_samples else []
                                    self.last_processing_time = current_time
                                    
                            except Exception as e:
                                print(f"Audio recording error: {e}")
                                break
                else:
                    print("No input devices found!")
                    self.status_updated.emit("No microphone found")
                        
        except Exception as e:
            print(f"Audio setup error: {e}")
            self.status_updated.emit(f"Audio error: {e}")
    
    def _should_process_audio(self, current_time):
        """Smart logic to determine when to send audio for transcription"""
        if not self.audio_buffer:
            return False
            
        # Calculate audio volume (RMS) from last 0.5 seconds
        recent_samples = int(16000 * 0.5)  # 0.5 seconds
        audio_array = np.array(self.audio_buffer[-recent_samples:]) if len(self.audio_buffer) >= recent_samples else np.array(self.audio_buffer)
        
        if len(audio_array) == 0:
            return False
            
        rms_volume = np.sqrt(np.mean(audio_array**2))
        
        # Check for silence
        is_silent = rms_volume < self.silence_detection_threshold
        
        if is_silent:
            self.silence_duration += self.chunk_duration
        else:
            self.silence_duration = 0
            self.last_audio_time = current_time
        
        # Decision logic:
        # 1. Send if we've had silence for min_silence_for_send seconds
        if self.silence_duration >= self.min_silence_for_send:
            print(f"Sending due to silence: {self.silence_duration:.1f}s")
            return True
            
        # 2. Send if buffer is getting too long (max_buffer_duration)
        buffer_duration = len(self.audio_buffer) / 16000
        if buffer_duration >= self.max_buffer_duration:
            print(f"Sending due to max buffer duration: {buffer_duration:.1f}s")
            return True
            
        # 3. Send if we've been recording for a while without processing
        time_since_last_processing = current_time - self.last_processing_time
        if time_since_last_processing >= 5.0:  # 5 seconds without processing
            print(f"Sending due to time since last processing: {time_since_last_processing:.1f}s")
            return True
            
        return False

    def _process_audio_chunk(self, audio_data, sample_rate):
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                
                # Write WAV file
                with wave.open(temp_filename, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes((np.array(audio_data) * 32767).astype(np.int16).tobytes())
                
                # Transcribe with OpenAI Whisper API using direct requests
                try:
                    with open(temp_filename, 'rb') as audio_file:
                        files = {
                            'file': ('audio.wav', audio_file, 'audio/wav')
                        }
                        data = {
                            'model': 'whisper-1',
                            'language': 'de'
                        }
                        headers = {
                            'Authorization': f'Bearer {self.api_key}'
                        }
                        
                        response = requests.post(
                            'https://api.openai.com/v1/audio/transcriptions',
                            headers=headers,
                            files=files,
                            data=data,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            transcript = response.json()
                        else:
                            print(f"API error: {response.status_code} - {response.text}")
                            return
                            
                except Exception as api_error:
                    print(f"OpenAI API error: {api_error}")
                    return
                
                # Clean up temp file
                os.unlink(temp_filename)
                
                # Process the transcription
                transcript_text = transcript.get('text', '') if isinstance(transcript, dict) else str(transcript)
                if transcript_text.strip():
                    print(f"Transcription result: {transcript_text.strip()}")
                    self._process_transcription(transcript_text.strip())
                else:
                    print("No transcription text received")
                    
        except Exception as e:
            print(f"Audio processing error: {e}")
    
    def _process_transcription(self, text):
        """Process transcription and handle sentence completion"""
        # Simple sentence detection (look for periods, exclamation marks, question marks)
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in '.!?':
                sentence = current.strip()
                if sentence and len(sentence) > 1:  # Only add meaningful sentences
                    sentences.append(sentence)
                current = ""
        
        # If we have complete sentences, emit them
        if sentences:
            for sentence in sentences:
                if sentence and sentence not in self.sentences:  # Avoid duplicates
                    self.sentences.append(sentence)
                    self.transcription_updated.emit(sentence)
        
        # Update current sentence with remaining text
        remaining = current.strip()
        if remaining and remaining != self.current_sentence:
            self.current_sentence = remaining
            self.transcription_updated.emit(f"CURRENT:{remaining}")

class ScrollingTextDisplay(QFrame):
    word_clicked = pyqtSignal(str)  # Signal emitted when a word is clicked
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #E52217; border-radius: 10px;")
        self.setupUI()
        self.sentences = []  # Store completed sentences
        self.current_sentence = ""  # Current sentence being transcribed
        
    def setupUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        
        # "Read along" label
        read_along_label = QLabel("Read along")
        read_along_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: bold;
                background-color: transparent;
                margin: 0px 0px 15px 0px;
            }
        """)
        read_along_label.setAlignment(Qt.AlignLeft)
        
        # Main text display area
        self.text_display = QTextEdit()
        self.text_display.setStyleSheet("""
            QTextEdit {
                color: white;
                font-size: 24px;
                font-weight: normal;
                background-color: transparent;
                border: none;
                padding: 0px;
                line-height: 1.4;
            }
        """)
        self.text_display.setReadOnly(True)
        self.text_display.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_display.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Enable text selection, clicking, and hover effects
        self.text_display.setMouseTracking(True)
        self.text_display.mousePressEvent = self.on_mouse_press
        self.text_display.mouseMoveEvent = self.on_mouse_move
        self.text_display.leaveEvent = self.on_mouse_leave
        
        # Track current hovered word
        self.current_hovered_word = None
        self.hovered_start = None
        self.hovered_end = None
        
        # Status and button container (aligned horizontally)
        status_button_container = QWidget()
        status_button_layout = QHBoxLayout()
        status_button_layout.setContentsMargins(0, 0, 0, 0)
        status_button_layout.setSpacing(20)
        
        # Status label
        self.status_label = QLabel("Ready to listen")
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                background-color: transparent;
                margin: 0px 0px 0px 0px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Add status label to the layout
        status_button_layout.addWidget(self.status_label)
        status_button_layout.addStretch()  # Push button to the right
        
        self.play_button = QPushButton("▶")
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 30px;
                width: 60px;
                height: 60px;
                font-size: 24px;
                font-weight: bold;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.4);
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
        """)
        self.play_button.setFixedSize(60, 60)
        self.play_button.setFocusPolicy(Qt.NoFocus)  # Remove focus outline
        
        # Add button to the status-button layout
        status_button_layout.addWidget(self.play_button)
        status_button_container.setLayout(status_button_layout)
        
        layout.addWidget(read_along_label)
        layout.addWidget(self.text_display)
        layout.addWidget(status_button_container)
        
        self.setLayout(layout)
    
    def add_sentence(self, sentence):
        """Add a completed sentence (will be displayed in black)"""
        self.sentences.append(sentence)
        self.current_sentence = ""  # Clear current sentence when adding completed one
        self._update_display()
    
    def update_current_sentence(self, sentence):
        """Update the current sentence being transcribed (displayed in white)"""
        self.current_sentence = sentence
        self._update_display()
    
    def _update_display(self):
        """Update the text display with completed and current sentences"""
        # Create clean text content without HTML
        text_content = ""
        
        # Add completed sentences in black
        for sentence in self.sentences:
            if sentence.strip():  # Only add non-empty sentences
                clean_sentence = self._clean_text(sentence.strip())
                text_content += clean_sentence + "\n\n"
        
        # Add current sentence in white (newest sentence)
        if self.current_sentence and self.current_sentence.strip():
            clean_current = self._clean_text(self.current_sentence.strip())
            text_content += clean_current
        
        # Set plain text instead of HTML
        self.text_display.setPlainText(text_content)
        
        # Apply styling to the text
        self._apply_text_styling()
        
        # Ensure proper scrolling - scroll to show the current sentence
        cursor = self.text_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_display.setTextCursor(cursor)
        
        # Force scroll to bottom
        scrollbar = self.text_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _clean_text(self, text):
        """Clean text by removing any HTML tags and unwanted characters"""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Remove any remaining HTML-like patterns
        clean = re.sub(r'[;"]>:[^>]*>', '', clean)
        clean = re.sub(r'cursor:\s*pointer[^>]*>', '', clean)
        clean = re.sub(r'font-weight:\s*bold[^>]*>', '', clean)
        clean = re.sub(r'text-shadow:[^>]*>', '', clean)
        clean = re.sub(r'color:\s*[^;]*;', '', clean)
        clean = re.sub(r'style="[^"]*"', '', clean)
        clean = re.sub(r'<span[^>]*>', '', clean)
        clean = re.sub(r'</span>', '', clean)
        # Clean up any remaining artifacts
        clean = re.sub(r'[;"]>', '', clean)
        clean = re.sub(r'^\s*[;"]*', '', clean)
        return clean.strip()
    
    def _apply_text_styling(self):
        """Apply styling to the text using QTextCharFormat"""
        cursor = self.text_display.textCursor()
        cursor.movePosition(QTextCursor.Start)
        
        # Style completed sentences (black)
        for sentence in self.sentences:
            if sentence.strip():
                clean_sentence = self._clean_text(sentence.strip())
                if clean_sentence:
                    # Find and style this sentence
                    cursor.select(QTextCursor.LineUnderCursor)
                    format = QTextCharFormat()
                    format.setForeground(QColor("black"))
                    format.setFontPointSize(24)
                    cursor.setCharFormat(format)
                    cursor.movePosition(QTextCursor.Down)
                    cursor.movePosition(QTextCursor.Down)  # Skip empty line
        
        # Style current sentence (white, bold)
        if self.current_sentence and self.current_sentence.strip():
            clean_current = self._clean_text(self.current_sentence.strip())
            if clean_current:
                cursor.select(QTextCursor.LineUnderCursor)
                format = QTextCharFormat()
                format.setForeground(QColor("white"))
                format.setFontPointSize(24)
                format.setFontWeight(QFont.Bold)
                cursor.setCharFormat(format)
    
    
    
    def on_mouse_press(self, event):
        """Handle mouse clicks to detect word clicks"""
        if event.button() == Qt.LeftButton:
            # Get the cursor position and find the word at that position
            cursor = self.text_display.cursorForPosition(event.pos())
            cursor.select(QTextCursor.WordUnderCursor)
            word = cursor.selectedText().strip()
            
            if word and word.isalpha():  # Only process alphabetic words
                print(f"Word clicked: {word}")
                # Emit signal to show word definition
                self.word_clicked.emit(word)
        
        # Call the original mouse press event
        QTextEdit.mousePressEvent(self.text_display, event)
    
    def on_mouse_move(self, event):
        """Handle mouse movement for hover effects"""
        # Get the cursor position and find the word at that position
        cursor = self.text_display.cursorForPosition(event.pos())
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()
        
        if word and word.isalpha():
            # Change cursor to pointing hand when hovering over words
            self.setCursor(Qt.PointingHandCursor)
            self.text_display.setCursor(Qt.PointingHandCursor)
            
            # Update hover effect if word changed
            if word != self.current_hovered_word:
                self.current_hovered_word = word
                # Remember the hovered selection range
                self.hovered_start = cursor.selectionStart()
                self.hovered_end = cursor.selectionEnd()
                self._update_hover_effect(word)
            else:
                # Update hovered range if mouse moved within same word
                self.hovered_start = cursor.selectionStart()
                self.hovered_end = cursor.selectionEnd()
        else:
            # Reset cursor to default
            self.setCursor(Qt.ArrowCursor)
            self.text_display.setCursor(Qt.ArrowCursor)
            if self.current_hovered_word:
                self.current_hovered_word = None
                self.hovered_start = None
                self.hovered_end = None
                self._update_display()  # Refresh to remove hover effects
        
        # Call the original mouse move event
        QTextEdit.mouseMoveEvent(self.text_display, event)
    
    def on_mouse_leave(self, event):
        """Handle mouse leaving the text area"""
        self.setCursor(Qt.ArrowCursor)
        self.text_display.setCursor(Qt.ArrowCursor)
        if self.current_hovered_word:
            self.current_hovered_word = None
            self.hovered_start = None
            self.hovered_end = None
            self._update_display()  # Refresh to remove hover effects
        QTextEdit.leaveEvent(self.text_display, event)
    
    def _update_hover_effect(self, hovered_word):
        """Update display with hover effect for specific word using QTextCharFormat"""
        # Get the current text content
        text_content = ""
        
        # Add completed sentences in black
        for sentence in self.sentences:
            if sentence.strip():
                clean_sentence = self._clean_text(sentence.strip())
                text_content += clean_sentence + "\n\n"
        
        # Add current sentence in white
        if self.current_sentence and self.current_sentence.strip():
            clean_current = self._clean_text(self.current_sentence.strip())
            text_content += clean_current
        
        # Set plain text
        self.text_display.setPlainText(text_content)
        
        # Apply styling with hover effect
        self._apply_text_styling_with_hover(hovered_word)
        
        # Ensure proper scrolling
        cursor = self.text_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_display.setTextCursor(cursor)
        scrollbar = self.text_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _apply_text_styling_with_hover(self, hovered_word):
        """Apply styling to the text with hover effect using QTextCharFormat"""
        cursor = self.text_display.textCursor()
        cursor.movePosition(QTextCursor.Start)

        # 1) Base styling: completed sentences black, current sentence white/bold
        for sentence in self.sentences:
            if sentence.strip():
                cursor.select(QTextCursor.LineUnderCursor)
                base_format = QTextCharFormat()
                base_format.setForeground(QColor("black"))
                base_format.setFontPointSize(24)
                cursor.setCharFormat(base_format)
                cursor.movePosition(QTextCursor.Down)
                cursor.movePosition(QTextCursor.Down)  # Skip empty line

        if self.current_sentence and self.current_sentence.strip():
            cursor.select(QTextCursor.LineUnderCursor)
            current_format = QTextCharFormat()
            current_format.setForeground(QColor("white"))
            current_format.setFontPointSize(24)
            current_format.setFontWeight(QFont.Bold)
            cursor.setCharFormat(current_format)

        # 2) Hover styling: highlight only the hovered word range
        if hovered_word and self.hovered_start is not None and self.hovered_end is not None:
            word_cursor = self.text_display.textCursor()
            word_cursor.setPosition(self.hovered_start)
            word_cursor.setPosition(self.hovered_end, QTextCursor.KeepAnchor)
            hover_format = QTextCharFormat()
            hover_format.setForeground(QColor("white"))
            hover_format.setFontWeight(QFont.Bold)
            # Slightly increase size for a modern effect
            hover_format.setFontPointSize(26)
            word_cursor.setCharFormat(hover_format)
    
    def update_status(self, status):
        self.status_label.setText(status)
    
    def clear_all(self):
        """Clear all sentences and current text"""
        self.sentences = []
        self.current_sentence = ""
        self.text_display.clear()

class WordDefinitionPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: none;
            }
        """)
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)
        
        # Word and star icon
        word_header_layout = QHBoxLayout()
        word_header_layout.setContentsMargins(0, 0, 0, 0)
        word_header_layout.setSpacing(10)
        
        self.word_label = QLabel("Click on a word to look up its meaning")
        self.word_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 18px;
                font-weight: normal;
                font-style: italic;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.word_label.setAlignment(Qt.AlignCenter)
        
        self.star_icon = QLabel("☆")
        self.star_icon.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 24px;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.star_icon.setVisible(False)  # Hide by default
        
        word_header_layout.addWidget(self.word_label)
        word_header_layout.addStretch()  # Push star to the right
        word_header_layout.addWidget(self.star_icon)
        
        # Phonetic transcription
        self.phonetic = QLabel("/'vısnʃaftlıç/")
        self.phonetic.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 16px;
                font-style: italic;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 20px 0px 0px 0px;
            }
        """)
        self.phonetic.setVisible(False)  # Hide by default
        
        # Separator line
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setStyleSheet("""
            QFrame {
                background-color: #E0E0E0;
                border: none;
                margin: 15px 0px;
                max-height: 0.5px;
                min-height: 0.5px;
            }
        """)
        self.separator.setVisible(False)  # Hide by default
        
        # Adjective definition
        self.adj_label = QLabel("ADJECTIVE")
        self.adj_label.setStyleSheet("""
            QLabel {
                color: #E52217;
                font-size: 12px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 10px 0px 0px 0px;
            }
        """)
        self.adj_label.setVisible(False)  # Hide by default
        
        self.adj_def1 = QLabel("• scientific")
        self.adj_def1.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 18px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-weight: 400;
                line-height: 1.4;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 5px 0px 0px 10px;
            }
        """)
        self.adj_def1.setVisible(False)  # Hide by default
        
        self.adj_def2 = QLabel("• academic (geisteswissenschaftlich)")
        self.adj_def2.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 18px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-weight: 400;
                line-height: 1.4;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 5px 0px 0px 10px;
            }
        """)
        self.adj_def2.setVisible(False)  # Hide by default
        
        # Adverb definition
        self.adv_label = QLabel("ADVERB")
        self.adv_label.setStyleSheet("""
            QLabel {
                color: #E52217;
                font-size: 12px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                border-top: 1px solid #E0E0E0;
                padding: 15px 0px 0px 0px;
                margin: 20px 0px 0px 0px;
            }
        """)
        self.adv_label.setVisible(False)  # Hide by default
        
        self.adv_def = QLabel("• scientifically (arbeiten etw untersuchen)")
        self.adv_def.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 18px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-weight: 400;
                line-height: 1.4;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 5px 0px 0px 10px;
            }
        """)
        self.adv_def.setVisible(False)  # Hide by default
        
        layout.addLayout(word_header_layout)
        layout.addWidget(self.phonetic)
        layout.addWidget(self.separator)
        layout.addWidget(self.adj_label)
        layout.addWidget(self.adj_def1)
        layout.addWidget(self.adj_def2)
        layout.addWidget(self.adv_label)
        layout.addWidget(self.adv_def)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def show_word_loading(self, word):
        """Show word immediately with loading state"""
        print(f"show_word_loading called with: {word}")
        
        # Update word label styling and show elements
        self.word_label.setText(word)
        self.word_label.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 28px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        # Show star icon
        self.star_icon.setVisible(True)
        
        # Show loading state
        self.phonetic.setText("Loading...")
        self.phonetic.setVisible(True)
        
        # Show separator
        self.separator.setVisible(True)
        
        # Show definition sections with loading text
        self.adj_label.setVisible(True)
        self.adj_def1.setVisible(True)
        self.adj_def2.setVisible(False)
        self.adv_label.setVisible(False)
        self.adv_def.setVisible(False)
        
        self.adj_label.setText("LOADING")
        self.adj_def1.setText("Loading definition...")
        self.adj_def2.setText("")
        self.adv_def.setText("")

    def update_word(self, word):
        """Update the panel with a new word"""
        print(f"update_word called with: {word}")
        # The show_word_loading method already shows the word, so we just need to fetch definition
        
        # Look up word in dictionary API
        self.lookup_word_definition(word)
    
    def lookup_word_definition(self, word):
        """Look up word definition using multiple dictionary APIs"""
        import requests
        import threading
        
        def fetch_definition():
            try:
                # Try a simple, reliable API first
                print(f"Looking up word: '{word}'")
                
                # 0) Try OpenAI dictionary API first
                try:
                    openai_entry = self._try_openai_dictionary(word)
                    if openai_entry:
                        print(f"OpenAI dictionary success, calling UI update for: {word}")
                        self._update_with_api_data(word, openai_entry)
                        return
                    else:
                        print(f"OpenAI dictionary returned None for: {word}")
                except Exception as e:
                    print(f"OpenAI dictionary error: {e}")
                
                # Try Wiktionary (EN/DE) as a fallback via REST v1
                try:
                    def parse_wiktionary_json(wk_data):
                        # Wiktionary structure: { lang: [{partOfSpeech, definitions:[{definition}]}] }
                        preferred_langs = ['de', 'en']
                        for lang in preferred_langs:
                            if lang in wk_data and wk_data[lang]:
                                items = wk_data[lang]
                                entry = {
                                    'phonetic': '',
                                    'phonetics': [],
                                    'meanings': []
                                }
                                for item in items[:3]:
                                    pos = item.get('partOfSpeech', '')
                                    defs = item.get('definitions', [])
                                    entry['meanings'].append({
                                        'partOfSpeech': pos,
                                        'definitions': [{'definition': d.get('definition', '')} for d in defs[:2]]
                                    })
                                return entry
                        # Fallback: pick any language present
                        for lang_key, items in wk_data.items():
                            if isinstance(items, list) and items:
                                entry = {
                                    'phonetic': '',
                                    'phonetics': [],
                                    'meanings': []
                                }
                                for item in items[:3]:
                                    pos = item.get('partOfSpeech', '')
                                    defs = item.get('definitions', [])
                                    entry['meanings'].append({
                                        'partOfSpeech': pos,
                                        'definitions': [{'definition': d.get('definition', '')} for d in defs[:2]]
                                    })
                                return entry
                        return None

                    # EN Wiktionary
                    print("Trying Wiktionary (EN) fallback...")
                    wk_url_en = f"https://en.wiktionary.org/api/rest_v1/page/definition/{word.lower()}"
                    wk_resp_en = requests.get(wk_url_en, timeout=6, headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                    })
                    print(f"Wiktionary EN status: {wk_resp_en.status_code}")
                    if wk_resp_en.status_code == 200:
                        wk_data_en = wk_resp_en.json()
                        entry = parse_wiktionary_json(wk_data_en)
                        if entry:
                            from PyQt5.QtCore import QTimer
                            QTimer.singleShot(0, lambda: self._update_with_api_data(word, entry))
                            return

                    # DE Wiktionary
                    print("Trying Wiktionary (DE) fallback...")
                    wk_url_de = f"https://de.wiktionary.org/api/rest_v1/page/definition/{word.lower()}"
                    wk_resp_de = requests.get(wk_url_de, timeout=6, headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                    })
                    print(f"Wiktionary DE status: {wk_resp_de.status_code}")
                    if wk_resp_de.status_code == 200:
                        wk_data_de = wk_resp_de.json()
                        entry = parse_wiktionary_json(wk_data_de)
                        if entry:
                            from PyQt5.QtCore import QTimer
                            QTimer.singleShot(0, lambda: self._update_with_api_data(word, entry))
                            return
                except Exception as e:
                    print(f"Wiktionary fallback error: {e}")

                # Try OpenAI chat-based dictionary fallback
                try:
                    print("Trying OpenAI dictionary fallback...")
                    openai_entry = self._try_openai_dictionary(word)
                    if openai_entry:
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self._update_with_api_data(word, openai_entry))
                        return
                except Exception as e:
                    print(f"OpenAI dictionary fallback error: {e}")

                # Try translation as fallback
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._try_translation_api(word))
                    
            except Exception as e:
                print(f"Dictionary lookup error: {e}")
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._update_with_fallback(word))
        
        # Run in background thread to avoid blocking UI
        thread = threading.Thread(target=fetch_definition, daemon=True)
        thread.start()


    def _try_openai_dictionary(self, word):
        """Use OpenAI to get a structured dictionary-style entry for a word (EN/German)."""
        import os
        import json
        import requests

        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("OPENAI_API_KEY not set; skipping OpenAI dictionary fallback")
            return None

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        system_prompt = (
            "You are a comprehensive dictionary assistant. Always return a JSON object with keys: "
            "phonetic (string with IPA pronunciation, REQUIRED - never empty), meanings (array), similarWords (object). "
            "Each meanings item has partOfSpeech (string) and definitions (array of objects with 'definition'). "
            "similarWords should have 'english' (array of similar English words) and 'german' (array of similar German words). "
            "Always respond in English. If the word is German, provide English definitions and identify the part of speech in English. "
            "ALWAYS provide IPA pronunciation in phonetic field. Limit to at most 3 meanings and 2 definitions per meaning. "
            "Include 3-5 similar words for each language."
        )
        user_prompt = (
            f"Word: {word}\n"
            "Return only the JSON object, no extra text."
        )
        payload = {
            "model": "gpt-4o-mini",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            print(f"OpenAI dictionary status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"OpenAI error: {resp.text}")
                return None
            data = resp.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not content:
                return None
            print("=== OPENAI DICTIONARY JSON ===")
            print(content)
            print("=== END OPENAI JSON ===")
            try:
                parsed = json.loads(content)
            except Exception as e:
                print(f"Failed to parse OpenAI JSON: {e}")
                return None

            # Map OpenAI JSON to our expected entry format
            entry = {
                'phonetic': parsed.get('phonetic', ''),
                'phonetics': [],
                'meanings': [],
                'similarWords': parsed.get('similarWords', {})
            }
            for m in parsed.get('meanings', [])[:3]:
                pos = m.get('partOfSpeech', '')
                defs = m.get('definitions', [])
                # Normalize definitions into list of {definition: ...}
                norm_defs = []
                for d in defs[:2]:
                    if isinstance(d, dict) and 'definition' in d:
                        norm_defs.append({'definition': d['definition']})
                    elif isinstance(d, str):
                        norm_defs.append({'definition': d})
                entry['meanings'].append({
                    'partOfSpeech': pos,
                    'definitions': norm_defs
                })

            if entry['meanings']:
                print(f"OpenAI dictionary returning entry: {entry}")
                return entry
            else:
                print("OpenAI dictionary returned empty meanings")
                return None
        except Exception as e:
            print(f"OpenAI dictionary request failed: {e}")
            return None
    
    def _try_translation_api(self, word):
        """Try a simple translation API as fallback"""
        import requests
        
        try:
            print(f"Trying translation for German word: '{word}'")
            
            # Try LibreTranslate (free translation service)
            url = "https://libretranslate.de/translate"
            data = {
                'q': word,
                'source': 'de',  # German
                'target': 'en',  # English
                'format': 'text'
            }
            
            response = requests.post(url, data=data, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            
            print(f"Translation response status: {response.status_code}")
            print(f"Translation response text: {response.text}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print("=== TRANSLATION API RESPONSE STRUCTURE ===")
                    print(f"Word: {word}")
                    print(f"Full response: {result}")
                    print("=== END TRANSLATION RESPONSE ===")
                    if 'translatedText' in result:
                        translation = result['translatedText']
                        print(f"Translation found for '{word}': {translation}")
                        self._update_with_translation(word, translation)
                        # Chain: try to fetch English definitions for the translated word
                        self._lookup_english_definitions_and_update(translation)
                        return
                except Exception as json_error:
                    print(f"JSON parsing error: {json_error}")
                    print(f"Raw response: {response.text}")
        except Exception as e:
            print(f"Translation API error: {e}")
        
        # Final fallback
        print(f"All APIs failed for word: '{word}', using fallback")
        self._update_with_fallback(word)

    def _lookup_english_definitions_and_update(self, english_word):
        """Fetch definitions for an English word and update UI (runs in background)."""
        import threading
        import requests

        def do_fetch():
            try:
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{english_word.lower()}"
                print(f"Chained EN lookup: {url}")
                r = requests.get(url, timeout=8, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                })
                if r.status_code == 200:
                    data = r.json()
                    if data:
                        entry = data[0]
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self._update_with_api_data(english_word, entry))
                        return
                print(f"Chained EN lookup failed with status {r.status_code}")
            except Exception as e:
                print(f"Chained EN lookup error: {e}")

        threading.Thread(target=do_fetch, daemon=True).start()
    
    def _update_with_api_data(self, word, entry):
        """Update panel with API data"""
        print(f"Processing API data for word: {word}")
        print(f"Entry structure: {entry}")
        print(f"Entry type: {type(entry)}")
        
        # Get phonetic - try both 'phonetic' and 'phonetics'
        phonetic = ""
        if 'phonetic' in entry and entry['phonetic']:
            phonetic = entry['phonetic']
        elif 'phonetics' in entry and entry['phonetics']:
            for ph in entry['phonetics']:
                if 'text' in ph and ph['text']:
                    phonetic = ph['text']
                    break
        
        print(f"Found phonetic: {phonetic}")
        
        # Get meanings - handle all parts of speech
        meanings = entry.get('meanings', [])
        all_definitions = []
        
        print(f"Found {len(meanings)} meanings")
        
        for meaning in meanings:
            part_of_speech = meaning.get('partOfSpeech', '').lower()
            definitions = meaning.get('definitions', [])
            
            print(f"Processing {part_of_speech} with {len(definitions)} definitions")
            
            for def_item in definitions[:2]:  # Take first 2 definitions per part of speech
                definition = def_item.get('definition', '')
                if definition:
                    all_definitions.append({
                        'part_of_speech': part_of_speech,
                        'definition': definition
                    })
                    print(f"Added definition: {part_of_speech} - {definition[:50]}...")
        
        print(f"Total definitions collected: {len(all_definitions)}")
        
        # Get similar words
        similar_words = entry.get('similarWords', {})
        english_similar = similar_words.get('english', [])
        german_similar = similar_words.get('german', [])
        print(f"Similar words - English: {english_similar}, German: {german_similar}")
        
        # Update UI directly
        print(f"Calling UI update for word: {word}")
        self._update_ui_with_api_data(word, phonetic, all_definitions, english_similar, german_similar)
    
    def _update_ui_with_api_data(self, word, phonetic, all_definitions, english_similar=None, german_similar=None):
        """Update UI with API data"""
        print(f"Updating UI for word: {word}")
        print(f"Phonetic: {phonetic}")
        print(f"Definitions count: {len(all_definitions)}")
        print(f"Similar words - English: {english_similar}, German: {german_similar}")
        
        # Update word label styling and show elements
        self.word_label.setText(word)
        self.word_label.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 28px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        # Show star icon
        self.star_icon.setVisible(True)
        
        # Format phonetic with slashes if not already present
        if phonetic:
            if not phonetic.startswith('/'):
                phonetic = f"/{phonetic}"
            if not phonetic.endswith('/'):
                phonetic = f"{phonetic}/"
        else:
            phonetic = f"/{word.lower()}/"
        self.phonetic.setText(phonetic)
        self.phonetic.setVisible(True)
        
        # Show separator
        self.separator.setVisible(True)
        
        # Display definitions based on part of speech
        if all_definitions:
            print("Updating definitions in UI...")
            
            # Show first definition
            first_def = all_definitions[0]
            part_of_speech = first_def['part_of_speech'].upper()
            definition = first_def['definition']
            
            # Show definition sections
            self.adj_label.setVisible(True)
            self.adj_def1.setVisible(True)
            self.adj_def2.setVisible(True)
            
            # Update the part of speech label dynamically
            self.adj_label.setText(part_of_speech)
            print(f"Updated part of speech label to: {part_of_speech}")
            
            print(f"Setting first definition: {definition[:50]}...")
            self.adj_def1.setText(f"• {definition}")
            
            # Show second definition if available
            if len(all_definitions) > 1:
                second_def = all_definitions[1]
                definition2 = second_def['definition']
                print(f"Setting second definition: {definition2[:50]}...")
                self.adj_def2.setText(f"• {definition2}")
            else:
                print("No second definition")
                self.adj_def2.setText("")
            
            # Show third definition in adverb field if available
            if len(all_definitions) > 2:
                third_def = all_definitions[2]
                definition3 = third_def['definition']
                print(f"Setting third definition: {definition3[:50]}...")
                self.adv_def.setText(f"• {definition3}")
            else:
                print("No third definition")
                self.adv_def.setText("")
            
            # Display similar words if available
            if english_similar or german_similar:
                print("Displaying similar words...")
                similar_text = ""
                if english_similar:
                    similar_text += f"English: {', '.join(english_similar[:3])}\n"
                if german_similar:
                    similar_text += f"German: {', '.join(german_similar[:3])}"
                
                # Show the adverb label and similar words with separator
                self.adv_label.setText("SIMILAR WORDS")
                self.adv_def.setText(similar_text.strip())
                self.adv_label.setVisible(True)
                self.adv_def.setVisible(True)
                print(f"Set similar words: {similar_text.strip()}")
            else:
                # Hide adverb section if no similar words
                self.adv_label.setVisible(False)
                self.adv_def.setVisible(False)
                print("No similar words, hiding adverb section")
        else:
            print("No definitions found, setting fallback text")
            # Show definition sections even for fallback
            self.adj_label.setVisible(True)
            self.adj_def1.setVisible(True)
            self.adj_def2.setVisible(False)
            self.adj_label.setText("NOUN")  # Default fallback
            self.adj_def1.setText("No definition found")
            self.adj_def2.setText("")
            self.adv_label.setVisible(False)
            self.adv_def.setVisible(False)
        
        print("UI update completed")
    
    def _update_with_translation(self, word, translation):
        """Update panel with translation data"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._update_ui_with_translation(word, translation))
    
    def _update_ui_with_translation(self, word, translation):
        """Update UI with translation data"""
        self.word_label.setText(word)
        self.phonetic.setText(f"/{word.lower()}/")
        self.adj_def1.setText(f"Translation: {translation}")
        self.adj_def2.setText("(German to English translation)")
        self.adv_def.setText("")
    
    def _update_with_fallback(self, word):
        """Update panel with fallback data"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._update_ui_with_fallback(word))
    
    def _update_ui_with_fallback(self, word):
        """Update UI with fallback data"""
        self.word_label.setText(word)
        self.phonetic.setText(f"/{word.lower()}/")
        
        # Provide some basic German word information
        # Fallback display when no API data is available
        self.adj_def1.setText(f"Word: {word}")
        self.adj_def2.setText("(No definition available)")
        if word_lower in german_words:
            self.adj_def1.setText(f"German: {german_words[word_lower]}")
            self.adj_def2.setText("(Basic German translation)")
        else:
            self.adj_def1.setText(f"Word: {word}")
            self.adj_def2.setText("(No definition available)")
        
        self.adv_def.setText("")

class TranscriberApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify Podcast Transcriber")
        self.setGeometry(200, 200, 1400, 900)  # Increased height and adjusted position
        self.setStyleSheet("background-color: #2C2C2C;")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  # Add margins to prevent cutting off
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #2C2C2C;
            }
            QTabBar {
                background-color: #2C2C2C;
                border: none;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #B0B0B0;
                padding: 15px 30px;
                margin-right: 0px;
                margin-top: 10px;
                border: none;
                font-weight: bold;
                font-size: 14px;
                min-height: 20px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                color: white;
                background-color: #E52217;
                border-radius: 5px;
            }
            QTabBar::tab:hover {
                color: white;
                background-color: transparent;
            }
        """)

        # Add tabs
        self.tabs.addTab(self.createTranscribeTab(), "Transcribe")
        self.tabs.addTab(QLabel("Vocabulary"), "Vocabulary")
        self.tabs.addTab(QLabel("Transcript"), "Transcript")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Initialize audio transcriber
        self.audio_transcriber = AudioTranscriber()
        self.audio_transcriber.transcription_updated.connect(self.on_transcription_updated)
        self.audio_transcriber.status_updated.connect(self.on_status_updated)

    def createTranscribeTab(self):
        # Main content area
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Left panel: Scrolling text display
        self.text_display = ScrollingTextDisplay()
        # Connect the play button to toggle listening
        self.text_display.play_button.clicked.connect(self.toggle_listening)
        # Connect word click signal
        self.text_display.word_clicked.connect(self.on_word_clicked)
        main_layout.addWidget(self.text_display, 2)  # 2:1 ratio
        
        # Right panel: Word definition
        self.word_panel = WordDefinitionPanel()
        main_layout.addWidget(self.word_panel, 1)
        
        main_widget.setLayout(main_layout)
        return main_widget
    
    def toggle_listening(self):
        if self.audio_transcriber.is_listening:
            self.audio_transcriber.stop_listening()
            self._update_button_to_play()
        else:
            self.audio_transcriber.start_listening()
            self._update_button_to_stop()
    
    def _update_button_to_play(self):
        """Update button to play state"""
        self.text_display.play_button.setText("▶")
        self.text_display.play_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 30px;
                width: 60px;
                height: 60px;
                font-size: 24px;
                font-weight: bold;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.4);
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
        """)
    
    def _update_button_to_stop(self):
        """Update button to stop state"""
        self.text_display.play_button.setText("⏹")
        self.text_display.play_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 0, 0, 0.3);
                color: white;
                border: 2px solid rgba(255, 0, 0, 0.5);
                border-radius: 30px;
                width: 60px;
                height: 60px;
                font-size: 24px;
                font-weight: bold;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.4);
                border: 2px solid rgba(255, 0, 0, 0.6);
            }
            QPushButton:pressed {
                background-color: rgba(255, 0, 0, 0.5);
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid rgba(255, 0, 0, 0.5);
            }
        """)
    
    def on_transcription_updated(self, text):
        """Handle transcription updates from the audio transcriber"""
        if text.startswith("CURRENT:"):
            # This is the current sentence being transcribed
            current_text = text[8:]  # Remove "CURRENT:" prefix
            self.text_display.update_current_sentence(current_text)
        else:
            # This is a completed sentence
            self.text_display.add_sentence(text)
    
    def on_status_updated(self, status):
        self.text_display.update_status(status)
        # Update button state based on status
        if status == "Ready to listen" and self.audio_transcriber.is_listening:
            self._update_button_to_play()
        elif status == "Listening..." and not self.audio_transcriber.is_listening:
            self._update_button_to_stop()
    
    def on_word_clicked(self, word):
        """Handle word clicks to show definitions"""
        print(f"Showing definition for: {word}")
        if hasattr(self, 'word_panel') and self.word_panel is not None:
            # Show word immediately with loading state
            self.word_panel.show_word_loading(word)
            # Then fetch definition
            self.word_panel.update_word(word)
        else:
            print("Word panel not available yet")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    transcriber = TranscriberApp()
    transcriber.show()
    sys.exit(app.exec_())