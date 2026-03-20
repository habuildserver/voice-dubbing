#!/usr/bin/env python3
"""
Standalone TTS (Text-to-Speech) Tool

Converts text to speech using Microsoft Edge TTS.
Supports multiple languages and voices.

Usage:
    python tools/tts.py "नमस्ते, कैसे हो आप?" -l hi -o output.mp3
    python tools/tts.py input.txt -l hi -o output.mp3
"""
import argparse
import os
import sys
import asyncio
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

VOICE_MAP = {
    'hi': 'hi-IN-MadhurNeural',
    'en': 'en-US-GuyNeural',
    'en-GB': 'en-GB-SoniaNeural',
    'es': 'es-ES-AlvaroNeural',
    'fr': 'fr-FR-DeniseNeural',
    'de': 'de-DE-ConradNeural',
    'it': 'it-IT-DiegoNeural',
    'pt': 'pt-BR-AntonioNeural',
    'ja': 'ja-JP-NanamiNeural',
    'ko': 'ko-KR-SunHiNeural',
    'zh': 'zh-CN-XiaoxiaoNeural',
}

VOICE_NAMES = {
    'hi-IN-MadhurNeural': 'Hindi (Madhur)',
    'en-US-GuyNeural': 'English (US, Guy)',
    'en-GB-SoniaNeural': 'English (UK, Sonia)',
    'es-ES-AlvaroNeural': 'Spanish (Alvaro)',
    'fr-FR-DeniseNeural': 'French (Denise)',
    'de-DE-ConradNeural': 'German (Conrad)',
    'it-IT-DiegoNeural': 'Italian (Diego)',
    'pt-BR-AntonioNeural': 'Portuguese (Antonio)',
    'ja-JP-NanamiNeural': 'Japanese (Nanami)',
    'ko-KR-SunHiNeural': 'Korean (SunHi)',
    'zh-CN-XiaoxiaoNeural': 'Chinese (Xiaoxiao)',
}

def list_voices():
    """List all available voices."""
    print("\nAvailable Voices:")
    print("-" * 40)
    for lang, voice in sorted(VOICE_MAP.items()):
        name = VOICE_NAMES.get(voice, voice)
        print(f"  {lang:6} - {name}")
    print()

async def synthesize(text: str, voice: str, output_path: str):
    """Generate speech audio."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def text_to_speech(text: str, language: str, output_path: str, voice: str = None):
    """Convert text to speech."""
    if voice is None:
        voice = VOICE_MAP.get(language, VOICE_MAP['hi'])
    
    voice_name = VOICE_NAMES.get(voice, voice)
    print(f"Using voice: {voice_name}")
    print(f"Generating speech...")
    
    asyncio.run(synthesize(text, voice, output_path))
    print(f"Audio saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Text-to-Speech using Edge TTS")
    parser.add_argument("input", help="Text to synthesize or path to text file")
    parser.add_argument("-o", "--output", required=True, help="Output audio file (MP3/WAV)")
    parser.add_argument("-l", "--language", default="hi", help="Language code (default: hi)")
    parser.add_argument("-v", "--voice", help="Specific voice name (default: auto from language)")
    parser.add_argument("-i", "--input-is-file", action="store_true", help="Treat input as file path")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    args = parser.parse_args()
    
    if args.list_voices:
        list_voices()
        return
    
    if args.input_is_file or (os.path.isfile(args.input) if os.path.exists(args.input) else False):
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"Loaded {len(text)} characters from file")
    else:
        text = args.input
    
    text_to_speech(text, args.language, args.output, args.voice)

if __name__ == "__main__":
    main()
