#!/bin/bash

# Podcast Transcriber Installation Script
# This script sets up the app for personal use

echo "🎙️  Podcast Transcriber - Installation"
echo "======================================"
echo ""

# Create installation directory
INSTALL_DIR="$HOME/Applications/PodcastTranscriber"
echo "📁 Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Copy files
echo "📋 Copying application files..."
cp dist/PodcastTranscriber "$INSTALL_DIR/"
cp README_DEPLOYMENT.md "$INSTALL_DIR/"
cp env_template.txt "$INSTALL_DIR/"
cp launch.sh "$INSTALL_DIR/"

# Make executable
chmod +x "$INSTALL_DIR/PodcastTranscriber"
chmod +x "$INSTALL_DIR/launch.sh"

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Go to: $INSTALL_DIR"
echo "2. Copy 'env_template.txt' to '.env'"
echo "3. Edit '.env' and add your OpenAI API key"
echo "4. Run the app: ./launch.sh"
echo ""
echo "🎯 Or simply double-click 'PodcastTranscriber' to run!"
echo ""
echo "📖 Read 'README_DEPLOYMENT.md' for detailed instructions."
echo ""

read -p "Press Enter to open the installation directory..."
open "$INSTALL_DIR"
