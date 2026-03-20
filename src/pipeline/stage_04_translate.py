import os
import json
import argparse
import time
import copy
import re
from deep_translator import GoogleTranslator

def setup_logger(verbose=False):
    import logging
    logger = logging.getLogger("translate")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger

logger = setup_logger()

COUNTING_WORDS = [
    'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
    'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
    'first', 'second', 'third', 'fourth', 'fifth'
]

def is_counting_text(text: str) -> bool:
    """Check if text contains counting patterns."""
    text_lower = text.lower().strip()
    text_clean = re.sub(r'[,\.\!\?\-\:\;]', ' ', text_lower)
    words = re.findall(r'\b\w+\b', text_clean)
    
    if not words:
        return False
    
    counting_matches = sum(1 for w in words if w in COUNTING_WORDS)
    
    if len(words) <= 3 and counting_matches >= 1:
        return True
    
    return counting_matches >= len(words) * 0.3


def translate_segments(segments: list, source_lang: str = "en", target_lang: str = "hi") -> list:
    """
    Translates transcribed segments from source to target language.
    Preserves timestamps and marks counting segments.
    """
    logger.info(f"Translating {len(segments)} segments: {source_lang} → {target_lang}")
    
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    translated_segments = []
    
    for i, segment in enumerate(segments):
        original_text = segment.get('text', '').strip()
        keep_original = is_counting_text(original_text)
        
        if not original_text:
            translated_text = ""
        elif keep_original:
            logger.info(f"Segment {i}: Counting detected - keeping original: '{original_text}'")
            translated_text = original_text
        else:
            try:
                translated_text = translator.translate(original_text)
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"Translation failed for segment {i}: '{original_text}'. Error: {e}")
                translated_text = original_text
        
        new_segment = copy.deepcopy(segment)
        new_segment['text'] = translated_text
        new_segment['keep_original'] = keep_original
        translated_segments.append(new_segment)
        
        if (i + 1) % 10 == 0:
            logger.info(f"Translated {i + 1}/{len(segments)} segments.")
    
    logger.info("Translation complete.")
    return translated_segments


def translate_file(transcript_path: str, output_dir: str = None,
                   source_lang: str = "en", target_lang: str = "hi") -> str:
    """
    Translates a transcription JSON file.
    
    Args:
        transcript_path: Path to transcription JSON from stage_03
        output_dir: Directory to save translation (default: ./data/intermediate)
        source_lang: Source language code
        target_lang: Target language code
    
    Returns:
        Absolute path to the translated JSON file
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'intermediate')
    
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
    
    logger.info(f"Loading transcript: {transcript_path}")
    
    with open(transcript_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    segments = data.get('segments', [])
    translated_segments = translate_segments(segments, source_lang, target_lang)
    
    filename = os.path.basename(transcript_path)
    name_without_ext = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{name_without_ext}_translated.json")
    
    output_data = {
        **data,
        'segments': translated_segments,
        'source_language': source_lang,
        'target_language': target_lang
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Translation saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate transcription to target language")
    parser.add_argument("transcript", help="Path to transcription JSON file")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: ./data/intermediate)")
    parser.add_argument("-s", "--source", default="en", help="Source language code (default: en)")
    parser.add_argument("-t", "--target", default="hi", help="Target language code (default: hi)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    logger = setup_logger(args.verbose)
    
    translated_path = translate_file(args.transcript, args.output, args.source, args.target)
    print(f"\nTranslated: {translated_path}")
