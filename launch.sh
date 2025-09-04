#!/bin/bash

# Podcast Transcriber Launcher Script
# This script helps launch the app with proper environment setup

echo "🎙️  Podcast Transcriber Launcher"
echo "================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your OpenAI API key:"
    echo "OPENAI_API_KEY=your_api_key_here"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if executable exists
if [ -f "dist/PodcastTranscriber" ]; then
    echo "✅ Found executable, launching app..."
    echo ""
    ./dist/PodcastTranscriber
elif [ -f "PodcastTranscriber" ]; then
    echo "✅ Found executable, launching app..."
    echo ""
    ./PodcastTranscriber
else
    echo "❌ Executable not found!"
    echo "Please run: pyinstaller podcast_transcriber.spec"
    echo "Or run from source: python main.py"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi
