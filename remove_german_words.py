#!/usr/bin/env python3
"""
Script to remove the unnecessary hardcoded German words list
"""

def remove_german_words():
    # Read the current main.py
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Find and remove the entire german_words dictionary and its usage
    lines = content.split('\n')
    new_lines = []
    skip_lines = False
    
    for i, line in enumerate(lines):
        # Check if this line starts the german_words dictionary
        if 'german_words = {' in line:
            skip_lines = True
            # Replace with simple fallback
            new_lines.append('        # Fallback display when no API data is available')
            continue
        
        # Skip lines until we find the closing brace and the usage
        if skip_lines:
            if '}' in line and 'german_words' in line:
                skip_lines = False
                continue
            elif 'word_lower = word.lower()' in line:
                skip_lines = False
                # Add the simple fallback code
                new_lines.append('        self.adj_def1.setText(f"Word: {word}")')
                new_lines.append('        self.adj_def2.setText("(No definition available)")')
                continue
            else:
                continue
        
        new_lines.append(line)
    
    # Write the cleaned content back
    with open('main.py', 'w') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ Removed unnecessary hardcoded German words list")

if __name__ == '__main__':
    remove_german_words()
