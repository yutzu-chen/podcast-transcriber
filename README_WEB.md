# 🎙️ Podcast Transcriber - Web Application

A modern web-based podcast transcriber with smart audio processing and interactive dictionary features.

## ✨ Features

- **🌐 Web-Based Interface** - Modern, responsive web application
- **🎤 Live Speech-to-Text** - Real-time transcription using OpenAI Whisper API
- **📚 Interactive Dictionary** - Click any word to see definitions and pronunciation
- **🎵 Karaoke-Style Display** - New sentences in white, older ones fade to black
- **🧠 Smart Audio Processing** - Waits for natural speech pauses (1.5s silence)
- **📱 Responsive Design** - Works on desktop, tablet, and mobile
- **🔄 Real-Time Updates** - Live transcription updates via WebSocket-like polling

## 🏗️ Architecture

### **Modular Components:**
- **`app.py`** - Main Flask application with REST API endpoints
- **`services/audio_service.py`** - Audio recording and processing
- **`services/transcription_service.py`** - Speech-to-text conversion
- **`services/dictionary_service.py`** - Word definitions and lookups
- **`services/background_service.py`** - Background audio processing
- **`templates/index.html`** - Modern web interface
- **`static/css/style.css`** - Responsive styling
- **`static/js/app.js`** - Frontend JavaScript logic

### **API Endpoints:**
- `POST /api/start-recording` - Start audio recording session
- `POST /api/stop-recording` - Stop audio recording session
- `GET /api/transcriptions/<session_id>` - Get transcriptions for session
- `POST /api/transcriptions/<session_id>` - Add transcription to session
- `GET /api/dictionary/<word>` - Get word definition
- `POST /api/upload-audio` - Upload audio file for transcription
- `GET /api/sessions` - List all active sessions
- `DELETE /api/sessions/<session_id>` - Delete session
- `GET /api/health` - Health check

## 🚀 Quick Start

### **1. Install Dependencies**
```bash
pip install -r requirements-web.txt
```

### **2. Set Up Environment**
Create a `.env` file:
```bash
OPENAI_API_KEY=your_openai_api_key_here
FLASK_DEBUG=False
PORT=5000
```

### **3. Run the Application**
```bash
python run_web.py
```

### **4. Open in Browser**
Navigate to: `http://localhost:5000`

## 🔧 Smart Audio Processing

### **Intelligent Timing:**
- **1.5s Silence Detection** - Waits for natural speech pauses
- **8s Maximum Buffer** - Prevents infinite waiting
- **5s Safety Net** - Ensures system responsiveness
- **2s Context Preservation** - Keeps audio context for better accuracy
- **100ms Chunk Processing** - Responsive real-time updates

### **Benefits:**
- ✅ **Complete Sentences** - No more broken fragments
- ✅ **Better Accuracy** - Full context preserved
- ✅ **Efficient API Usage** - Only sends meaningful chunks
- ✅ **Natural Speech Flow** - Respects actual speech patterns

## 🎨 Modern Web Interface

### **Design Features:**
- **Dark Theme** - Easy on the eyes for long sessions
- **Red Left Panel** - Transcription display with scrolling text
- **White Right Panel** - Dictionary definitions and word lookups
- **Responsive Grid** - Adapts to different screen sizes
- **Smooth Animations** - Professional user experience
- **Clickable Words** - Interactive dictionary integration

### **User Experience:**
- **One-Click Recording** - Simple play/stop button
- **Real-Time Updates** - Live transcription as you speak
- **Word Hover Effects** - Visual feedback for clickable words
- **Loading States** - Clear feedback during processing
- **Error Handling** - Graceful error messages and recovery

## 📱 Mobile Support

The web application is fully responsive and works on:
- **Desktop** - Full-featured experience
- **Tablet** - Optimized layout for touch
- **Mobile** - Simplified interface for small screens

## 🔒 Security & Privacy

- **Local Processing** - Audio processed locally before API calls
- **Session Management** - Isolated sessions for multiple users
- **API Key Protection** - Server-side API key handling
- **No Data Storage** - Transcriptions not permanently stored
- **HTTPS Ready** - Secure deployment support

## 🚀 Deployment Options

### **Local Development:**
```bash
python run_web.py
```

### **Production Deployment:**
```bash
# Using Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Using Docker
docker build -t podcast-transcriber .
docker run -p 5000:5000 -e OPENAI_API_KEY=your_key podcast-transcriber
```

### **Cloud Deployment:**
- **Heroku** - Easy deployment with Procfile
- **Railway** - Modern cloud platform
- **DigitalOcean** - VPS deployment
- **AWS/GCP** - Enterprise deployment

## 🛠️ Development

### **Project Structure:**
```
podcast-transcriber/
├── app.py                 # Main Flask application
├── run_web.py            # Application launcher
├── services/             # Modular services
│   ├── audio_service.py
│   ├── transcription_service.py
│   ├── dictionary_service.py
│   └── background_service.py
├── templates/            # HTML templates
│   └── index.html
├── static/              # Static assets
│   ├── css/style.css
│   └── js/app.js
├── requirements-web.txt  # Web dependencies
└── README_WEB.md        # This file
```

### **Adding Features:**
1. **New API Endpoint** - Add to `app.py`
2. **New Service** - Create in `services/` directory
3. **Frontend Changes** - Modify `templates/` and `static/`
4. **Styling** - Update `static/css/style.css`

## 🔄 Migration from Desktop App

The web version maintains all features from the desktop app:
- ✅ Smart audio buffering
- ✅ Complete sentence handling
- ✅ Interactive dictionary
- ✅ Modern UI design
- ✅ Real-time transcription

**Additional Benefits:**
- 🌐 Cross-platform compatibility
- 📱 Mobile device support
- 🔄 Easy updates and deployment
- 👥 Multi-user support
- 🔧 Easier maintenance

## 📞 Support

For issues or questions:
1. Check the console for error messages
2. Verify your OpenAI API key is correct
3. Ensure microphone permissions are granted
4. Check network connectivity

---

**🎯 Result: A modern, maintainable web application that provides the same great transcription experience with improved architecture and deployment options!**
