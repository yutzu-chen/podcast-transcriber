# Podcast Transcriber - Deployment Guide

## 🚀 Quick Start

### Option 1: Run the Executable (Recommended)
1. **Download the app**: The `PodcastTranscriber` executable is in the `dist/` folder
2. **Set up your API key**: Create a `.env` file in the same directory as the executable with:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
3. **Run the app**: Double-click `PodcastTranscriber` or run it from terminal

### Option 2: Run from Source
1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Set up your API key**: Create a `.env` file with your OpenAI API key
3. **Run the app**:
   ```bash
   python main.py
   ```

## 📋 Requirements

- **macOS** (tested on macOS 15.1)
- **OpenAI API Key** (for transcription and dictionary)
- **Microphone access** (granted when first run)

## 🔧 Features

- **Live Speech-to-Text**: Real-time transcription using OpenAI Whisper API
- **Interactive Dictionary**: Click any word to see definitions, pronunciation, and similar words
- **Karaoke-Style Display**: New sentences appear in white, older ones fade to black
- **Persistent Transcription**: Text accumulates across sessions
- **Modern UI**: Clean, responsive interface with hover effects

## 🎯 Usage

1. **Start the app** and grant microphone permissions
2. **Click the play button** to start listening
3. **Speak clearly** - the app will transcribe in real-time
4. **Click any word** to see its definition and pronunciation
5. **Click stop** to pause transcription (text remains visible)

## 🛠️ Troubleshooting

### Microphone Issues
- Make sure no other apps are using the microphone
- Check System Preferences > Security & Privacy > Microphone
- Try selecting a different audio device in the app

### API Issues
- Verify your OpenAI API key is correct
- Check your internet connection
- Ensure you have sufficient OpenAI credits

### App Won't Start
- Make sure you have the `.env` file with your API key
- Try running from terminal to see error messages
- Check that all dependencies are installed

## 📁 File Structure

```
podcast_transcriber/
├── PodcastTranscriber          # Executable (run this!)
├── .env                        # Your API key (create this)
├── main.py                     # Source code
├── requirements.txt            # Dependencies
└── README_DEPLOYMENT.md        # This file
```

## 🔐 Security Notes

- Keep your `.env` file secure and never share it
- The app only sends audio to OpenAI for transcription
- No data is stored locally except the transcribed text

## 🆘 Support

If you encounter issues:
1. Check the terminal output for error messages
2. Verify your API key and internet connection
3. Make sure microphone permissions are granted
4. Try restarting the app

---

**Enjoy your personal podcast transcriber! 🎙️✨**
