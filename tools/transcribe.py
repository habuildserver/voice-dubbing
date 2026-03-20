#!/usr/bin/env python3
"""
Standalone Transcription Tool

Transcribes audio to text using OpenAI Whisper.
Supports multiple languages and model sizes.

Usage:
    python tools/transcribe.py audio.wav -l en -o transcript.txt
    python tools/transcribe.py audio.wav -m base -l en -o transcript.json
"""
import argparse
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import whisper

MODELS = ['tiny', 'base', 'small', 'medium', 'large']
LANGUAGES = {
    'en': 'English', 'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French',
    'de': 'German', 'it': 'Italian', 'pt': 'Portuguese', 'ja': 'Japanese',
    'ko': 'Korean', 'zh': 'Chinese', 'ru': 'Russian', 'ar': 'Arabic',
}

def list_models():
    """List available Whisper models."""
    print("\nAvailable Models:")
    print("-" * 40)
    print("  tiny    - ~1GB, fastest, lowest quality")
    print("  base    - ~1GB, fast, low quality")
    print("  small   - ~2GB, medium speed, medium quality")
    print("  medium  - ~5GB, slow, high quality")
    print("  large   - ~10GB, slowest, highest quality")
    print()

def transcribe(audio_path: str, model_name: str = "tiny",
               language: str = None, output_path: str = None, 
               json_output: bool = False) -> dict:
    """
    Transcribe audio file.
    
    Returns:
        Dictionary with 'text' and optionally 'segments'
    """
    print(f"Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)
    
    print(f"Transcribing: {audio_path}")
    result = model.transcribe(audio_path, language=language)
    
    text = result['text']
    segments = result.get('segments', [])
    
    print(f"\nTranscription complete!")
    print(f"Duration: {result.get('duration', 'unknown')}s")
    print(f"Segments: {len(segments)}")
    
    if output_path:
        if json_output:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
        print(f"Saved to: {output_path}")
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio using Whisper")
    parser.add_argument("audio", help="Path to audio file (WAV, MP3, etc.)")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument("-m", "--model", default="tiny",
                        choices=MODELS, help="Whisper model size (default: tiny)")
    parser.add_argument("-l", "--language", help="Source language (auto-detect if not specified)")
    parser.add_argument("-j", "--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    args = parser.parse_args()
    
    if args.list_models:
        list_models()
        return
    
    if not os.path.exists(args.audio):
        print(f"Error: Audio file not found: {args.audio}")
        sys.exit(1)
    
    result = transcribe(
        args.audio,
        model_name=args.model,
        language=args.language,
        output_path=args.output,
        json_output=args.json
    )
    
    if not args.output:
        print("\n" + "="*50)
        print("TRANSCRIPTION:")
        print("="*50)
        print(result['text'])

if __name__ == "__main__":
    main()
