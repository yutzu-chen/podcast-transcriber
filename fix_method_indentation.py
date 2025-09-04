#!/usr/bin/env python3
"""
Script to fix method indentation issues in main.py
"""

def fix_method_indentation():
    # Read the current main.py
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Fix the _process_audio_chunk method indentation
    content = content.replace('def _process_audio_chunk(self, audio_data, sample_rate):', '    def _process_audio_chunk(self, audio_data, sample_rate):')
    
    # Fix the _process_transcription method indentation
    content = content.replace('def _process_transcription(self, text):', '    def _process_transcription(self, text):')
    
    # Write the fixed content back
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed method indentation issues in main.py")

if __name__ == '__main__':
    fix_method_indentation()
