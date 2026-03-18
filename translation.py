from deep_translator import GoogleTranslator
from utils import logger
from config import SOURCE_LANGUAGE, TARGET_LANGUAGE
import time
import copy
import re


def is_counting_text(text: str) -> bool:
    """
    Check if text contains counting patterns like 'one', 'two', 'three', etc.
    """
    text_lower = text.lower().strip()
    
    counting_words = [
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty',
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
        'first', 'second', 'third', 'fourth', 'fifth'
    ]
    
    text_clean = re.sub(r'[,\.\!\?\-\:\;]', ' ', text_lower)
    words = re.findall(r'\b\w+\b', text_clean)
    
    if not words:
        return False
    
    counting_matches = sum(1 for w in words if w in counting_words)
    
    if len(words) <= 3 and counting_matches >= 1:
        return True
    
    return counting_matches >= len(words) * 0.3


def translate_segments(segments: list, progress_callback=None) -> list:
    """
    Translates the transcribed text segments from source to target language.
    Preserves the start and end timestamps.
    Marks counting segments to keep original audio.
    """
    logger.info(f"Translating {len(segments)} segments from {SOURCE_LANGUAGE} to {TARGET_LANGUAGE}...")
    
    translator = GoogleTranslator(source=SOURCE_LANGUAGE, target=TARGET_LANGUAGE)
    
    translated_segments = []
    
    for i, segment in enumerate(segments):
        original_text = segment['text'].strip()
        
        # Check if this is counting - mark it to keep original audio
        keep_original = is_counting_text(original_text)
        
        if not original_text:
            translated_text = ""
        elif keep_original:
            logger.info(f"Segment {i}: Counting detected - '{original_text}' - will keep original audio")
            translated_text = original_text  # Don't translate counting
        else:
            try:
                translated_text = translator.translate(original_text)
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"Translation failed for segment {i}: '{original_text}'. Error: {e}")
                translated_text = original_text
        
        new_segment = copy.deepcopy(segment)
        new_segment['text'] = translated_text
        new_segment['keep_original'] = keep_original  # Mark for TTS
        translated_segments.append(new_segment)
        
        if (i + 1) % 10 == 0:
            logger.info(f"Translated {i + 1}/{len(segments)} segments.")
            
    logger.info("Translation complete.")
    return translated_segments
