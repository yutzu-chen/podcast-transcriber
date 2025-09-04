#!/usr/bin/env python3
"""
Script to fix the final indentation issue in main.py
"""

def fix_final_indentation():
    # Read the current main.py
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Fix the _process_transcription method indentation
    # The method definition should be at class level (4 spaces), not nested (8 spaces)
    content = content.replace('        def _process_transcription(self, text):', '    def _process_transcription(self, text):')
    
    # Write the fixed content back
    with open('main.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed final indentation issue in main.py")

if __name__ == '__main__':
    fix_final_indentation()
