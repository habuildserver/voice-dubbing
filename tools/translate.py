#!/usr/bin/env python3
"""
Standalone Translation Tool

Translates text files or direct input between languages.
Uses Google Translate via deep-translator.

Usage:
    python tools/translate.py "Hello world" -t hi
    python tools/translate.py input.txt -t hi -o output.txt
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_translator import GoogleTranslator

LANGUAGES = {
    'en': 'English', 'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French',
    'de': 'German', 'it': 'Italian', 'pt': 'Portuguese', 'ja': 'Japanese',
    'ko': 'Korean', 'zh': 'Chinese', 'ru': 'Russian', 'ar': 'Arabic',
    'auto': 'Auto-detect'
}

def translate_text(text: str, source: str, target: str) -> str:
    """Translate text from source to target language."""
    translator = GoogleTranslator(source=source, target=target)
    return translator.translate(text)

def main():
    parser = argparse.ArgumentParser(description="Translate text between languages")
    parser.add_argument("input", help="Text to translate or path to text file")
    parser.add_argument("-s", "--source", default="en", help=f"Source language (default: en)")
    parser.add_argument("-t", "--target", default="hi", help=f"Target language (default: hi)")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument("-i", "--input-is-file", action="store_true", help="Treat input as file path")
    args = parser.parse_args()
    
    source_name = LANGUAGES.get(args.source, args.source)
    target_name = LANGUAGES.get(args.target, args.target)
    print(f"Translating ({source_name} → {target_name})...")
    
    if args.input_is_file or (os.path.isfile(args.input) if os.path.exists(args.input) else False):
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"Loaded {len(text)} characters from file")
    else:
        text = args.input
    
    result = translate_text(text, args.source, args.target)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Translated text saved to: {args.output}")
    else:
        print("\n" + "="*50)
        print("TRANSLATION:")
        print("="*50)
        print(result)
    
    return result

if __name__ == "__main__":
    main()
