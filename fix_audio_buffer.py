#!/usr/bin/env python3
"""
Script to fix the missing audio_buffer attribute in main.py
"""

def fix_audio_buffer():
    # Read the current main.py
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Add the missing audio_buffer initialization
    content = content.replace(
        '        # Smart audio buffering settings\n        self.chunk_count = 0',
        '        # Smart audio buffering settings\n        self.audio_buffer = []\n        self.chunk_count = 0'
    )
    
    # Write the fixed content back
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed missing audio_buffer attribute in main.py")

if __name__ == '__main__':
    fix_audio_buffer()
