import os
import json
import argparse
import whisper

def setup_logger(verbose=False):
    import logging
    logger = logging.getLogger("transcribe")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger

logger = setup_logger()

def transcribe_audio(audio_path: str, output_dir: str = None, 
                     model_name: str = "tiny", language: str = "en") -> str:
    """
    Transcribes audio to text using OpenAI Whisper.
    
    Args:
        audio_path: Path to input audio file (WAV)
        output_dir: Directory to save transcription (default: ./data/intermediate)
        model_name: Whisper model size (tiny, base, small, medium, large)
        language: Source language code (en, hi, etc.)
    
    Returns:
        Absolute path to the JSON transcription file
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'intermediate')
    
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    logger.info(f"Loading Whisper model '{model_name}'...")
    logger.info(f"Transcribing: {audio_path}")
    
    try:
        model = whisper.load_model(model_name)
        result = model.transcribe(audio_path, language=language)
        
        segments = result.get('segments', [])
        logger.info(f"Transcription complete. Found {len(segments)} segments.")
        
        filename = os.path.basename(audio_path)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}_transcript.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'text': result['text'],
                'segments': segments,
                'language': language
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Transcription saved to: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio to text using Whisper")
    parser.add_argument("audio", help="Path to input audio file (WAV)")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: ./data/intermediate)")
    parser.add_argument("-m", "--model", default="tiny", 
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: tiny)")
    parser.add_argument("-l", "--language", default="en", help="Source language code (default: en)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    logger = setup_logger(args.verbose)
    
    transcript_path = transcribe_audio(args.audio, args.output, args.model, args.language)
    print(f"\nTranscription: {transcript_path}")
