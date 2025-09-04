"""
Dictionary Service - Handles word definitions and lookups
"""

import os
import requests
import json
from typing import Dict, Any, Optional

class DictionaryService:
    """Service for handling word definitions and dictionary lookups"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
    
    def get_definition(self, word: str) -> Dict[str, Any]:
        """Get word definition using OpenAI API"""
        try:
            # Clean the word
            clean_word = word.strip().lower()
            if not clean_word:
                return {
                    'success': False,
                    'error': 'Empty word provided',
                    'word': word,
                    'definition': None
                }
            
            # Try OpenAI dictionary API first
            result = self._get_openai_definition(clean_word)
            if result['success']:
                return result
            
            # Fallback to basic response
            return {
                'success': True,
                'word': clean_word,
                'definition': {
                    'phonetic': f"/{clean_word}/",
                    'meanings': [{
                        'partOfSpeech': 'unknown',
                        'definitions': [{
                            'definition': f'Word: {clean_word}'
                        }]
                    }],
                    'similarWords': {
                        'english': [],
                        'german': []
                    }
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'word': word,
                'definition': None
            }
    
    def _get_openai_definition(self, word: str) -> Dict[str, Any]:
        """Get definition using OpenAI Chat API"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            system_prompt = """You are a dictionary API that provides word definitions in JSON format. 
            For the given word, return a JSON object with the following structure:
            {
                "phonetic": "string with IPA pronunciation, REQUIRED - never empty",
                "meanings": [
                    {
                        "partOfSpeech": "string (noun, verb, adjective, etc.)",
                        "definitions": [
                            {"definition": "string"}
                        ]
                    }
                ],
                "similarWords": {
                    "english": ["word1", "word2", "word3"],
                    "german": ["word1", "word2", "word3"]
                }
            }
            
            ALWAYS provide IPA pronunciation in phonetic field.
            Include similar words in both English and German when relevant.
            Provide accurate definitions and part of speech information."""
            
            user_prompt = f"Provide a dictionary definition for the word: {word}"
            
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON response
                try:
                    definition = json.loads(content)
                    return {
                        'success': True,
                        'word': word,
                        'definition': definition
                    }
                except json.JSONDecodeError:
                    # If JSON parsing fails, return the raw content
                    return {
                        'success': True,
                        'word': word,
                        'definition': {
                            'phonetic': f"/{word}/",
                            'meanings': [{
                                'partOfSpeech': 'unknown',
                                'definitions': [{
                                    'definition': content
                                }]
                            }],
                            'similarWords': {
                                'english': [],
                                'german': []
                            }
                        }
                    }
            else:
                return {
                    'success': False,
                    'error': f"OpenAI API error: {response.status_code} - {response.text}",
                    'word': word,
                    'definition': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'word': word,
                'definition': None
            }
    
    def format_definition_for_ui(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        """Format definition data for UI display"""
        try:
            if not definition:
                return {
                    'phonetic': '',
                    'part_of_speech': 'unknown',
                    'definitions': [],
                    'similar_words': {
                        'english': [],
                        'german': []
                    }
                }
            
            # Extract phonetic
            phonetic = definition.get('phonetic', '')
            if phonetic and not phonetic.startswith('/'):
                phonetic = f"/{phonetic}"
            if phonetic and not phonetic.endswith('/'):
                phonetic = f"{phonetic}/"
            
            # Extract meanings
            meanings = definition.get('meanings', [])
            part_of_speech = 'unknown'
            definitions = []
            
            if meanings:
                first_meaning = meanings[0]
                part_of_speech = first_meaning.get('partOfSpeech', 'unknown')
                defs = first_meaning.get('definitions', [])
                definitions = [d.get('definition', '') for d in defs[:3]]  # Limit to 3 definitions
            
            # Extract similar words
            similar_words = definition.get('similarWords', {})
            english_similar = similar_words.get('english', [])[:3]  # Limit to 3
            german_similar = similar_words.get('german', [])[:3]  # Limit to 3
            
            return {
                'phonetic': phonetic,
                'part_of_speech': part_of_speech.upper(),
                'definitions': definitions,
                'similar_words': {
                    'english': english_similar,
                    'german': german_similar
                }
            }
            
        except Exception as e:
            return {
                'phonetic': '',
                'part_of_speech': 'unknown',
                'definitions': [],
                'similar_words': {
                    'english': [],
                    'german': []
                }
            }
