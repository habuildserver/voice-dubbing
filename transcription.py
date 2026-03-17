import whisper
from utils import logger
from config import WHISPER_MODEL
import os

def transcribe_audio(audio_path: str) -> list:
    """
    Transcribes the given audio file using OpenAI Whisper.
    Returns a list of segment dictionaries with text and timestamps.
    """
    logger.info(f"Loading Whisper model '{WHISPER_MODEL}' for transcription...")
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    try:
        model = whisper.load_model(WHISPER_MODEL)
        
        logger.info(f"Transcribing audio: {audio_path}")
        result = model.transcribe(audio_path, language="en")
        
        segments = result.get('segments', [])
        logger.info(f"Transcription complete. Found {len(segments)} segments.")
        
        return segments
        
    except Exception as e:
        logger.error(f"Failed to transcribe audio. Error: {e}")
        raise e
