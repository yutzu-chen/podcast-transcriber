#!/usr/bin/env python3
"""
Script to fix remaining audio_buffer references in main.py
"""

def fix_audio_buffer_references():
    # Read the current main.py
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Fix the remaining audio_buffer references
    content = content.replace('if len(audio_buffer) >= sample_rate * 3:', 'if len(self.audio_buffer) >= sample_rate * 3:')
    content = content.replace('self._process_audio_chunk(audio_buffer, sample_rate)', 'self._process_audio_chunk(self.audio_buffer, sample_rate)')
    content = content.replace('audio_buffer = audio_buffer[sample_rate * 3:]', 'self.audio_buffer = self.audio_buffer[sample_rate * 3:]')
    
    # Write the fixed content back
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed remaining audio_buffer references in main.py")

if __name__ == '__main__':
    fix_audio_buffer_references()
