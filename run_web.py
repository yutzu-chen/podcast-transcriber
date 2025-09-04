#!/usr/bin/env python3
"""
Podcast Transcriber Web Application Launcher
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for required environment variables
if not os.getenv('OPENAI_API_KEY'):
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    print("Please create a .env file with your OpenAI API key:")
    print("OPENAI_API_KEY=your_api_key_here")
    sys.exit(1)

# Import and run the Flask app
from app import app

if __name__ == '__main__':
    print("🎙️ Starting Podcast Transcriber Web Application...")
    print("📱 Open your browser to: http://localhost:5000")
    print("🔑 API Key loaded successfully")
    
    # Run the application
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
