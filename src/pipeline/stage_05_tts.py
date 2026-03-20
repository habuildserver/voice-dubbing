import os
import json
import argparse
import asyncio
import tempfile
import re
import numpy as np
import soundfile as sf
import librosa
import subprocess

def setup_logger(verbose=False):
    import logging
    logger = logging.getLogger("tts")
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

VOICE_MAP = {
    "hi": "hi-IN-MadhurNeural",
    "en": "en-US-GuyNeural",
}

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


def detect_speech_regions(audio_path: str, sample_rate: int = 16000) -> list:
    """Detect speech and silence regions in audio."""
    logger.info("Detecting speech regions...")
    
    y, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
    energy = np.abs(librosa.stft(y))
    energy_db = librosa.amplitude_to_db(energy, ref=np.max)
    energy_per_frame = energy_db.mean(axis=0)
    
    is_speech = energy_per_frame > -60
    
    regions = []
    current_speech = is_speech[0]
    start_frame = 0
    frame_duration = 512 / sr
    
    for i in range(1, len(is_speech)):
        if is_speech[i] != current_speech:
            regions.append({
                'speech': bool(current_speech),
                'start': float(start_frame * frame_duration),
                'end': float(i * frame_duration)
            })
            current_speech = is_speech[i]
            start_frame = i
    
    regions.append({
        'speech': bool(current_speech),
        'start': float(start_frame * frame_duration),
        'end': float(len(is_speech) * frame_duration)
    })
    
    merged = []
    for r in regions:
        if r['speech'] and merged and not merged[-1]['speech']:
            gap = r['start'] - merged[-1]['end']
            if gap < 0.3:
                merged[-1]['end'] = r['end']
                continue
        merged.append(r)
    
    speech_count = sum(1 for r in merged if r['speech'])
    logger.info(f"Detected {len(merged)} regions ({speech_count} speech, {len(merged) - speech_count} silence)")
    
    return merged


async def _synthesize(text: str, voice: str, output_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_tts(translated_path: str, original_audio_path: str = None,
                 output_dir: str = None, target_lang: str = "hi",
                 speed: float = 1.0) -> tuple:
    """
    Generates TTS audio from translated segments.
    
    Args:
        translated_path: Path to translated JSON file
        original_audio_path: Original audio for timing reference (optional)
        output_dir: Directory to save output (default: ./data/intermediate)
        target_lang: Target language for TTS voice
        speed: TTS speed multiplier (higher = faster)
    
    Returns:
        Tuple of (dubbed_audio_path, timing_json_path)
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'intermediate')
    
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(translated_path):
        raise FileNotFoundError(f"Translated file not found: {translated_path}")
    
    with open(translated_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    segments = data.get('segments', [])
    logger.info(f"Processing {len(segments)} segments for TTS...")
    
    voice = VOICE_MAP.get(target_lang, "hi-IN-MadhurNeural")
    logger.info(f"Using voice: {voice}")
    
    sample_rate = 24000
    
    if original_audio_path and os.path.exists(original_audio_path):
        logger.info(f"Using original audio for timing: {original_audio_path}")
        speech_regions = detect_speech_regions(original_audio_path)
        original_audio, _ = librosa.load(original_audio_path, sr=sample_rate, mono=True)
    else:
        logger.info("No original audio provided, generating without timing constraints")
        speech_regions = []
        original_audio = None
    
    video_duration = max((seg.get('end', 0) for seg in segments), default=60)
    adjusted_duration = video_duration / speed
    total_samples = int((adjusted_duration + 5.0) * sample_rate)
    final_audio = np.zeros(total_samples, dtype=np.float32)
    
    filename = os.path.basename(translated_path)
    name_without_ext = os.path.splitext(filename)[0]
    dubbed_audio_path = os.path.join(output_dir, f"{name_without_ext}_dubbed.wav")
    
    timing_data = []
    regions_to_process = [r for r in speech_regions if r['speech']] if speech_regions else []
    
    for idx, seg in enumerate(segments):
        text = seg.get('text', '').strip()
        if not text:
            continue
        
        orig_start = seg.get('start', 0)
        orig_end = seg.get('end', orig_start + 2)
        
        if regions_to_process:
            for region in regions_to_process:
                if region['start'] <= orig_start <= region['end']:
                    target_start = region['start']
                    target_end = region['end']
                    break
            else:
                target_start = orig_start
                target_end = orig_end
        else:
            target_start = orig_start
            target_end = orig_end
        
        target_duration = (target_end - target_start) / speed
        
        if seg.get('keep_original', False) and original_audio is not None:
            logger.info(f"Segment {idx+1}: Using original audio for counting")
            start_sample = int(target_start * sample_rate)
            end_sample = int(target_end * sample_rate)
            end_sample = min(end_sample, len(original_audio))
            
            if start_sample < len(original_audio):
                segment_audio = original_audio[start_sample:end_sample]
                target_samples = int(target_duration * sample_rate)
                
                if len(segment_audio) < target_samples:
                    segment_audio = np.concatenate([segment_audio, np.zeros(target_samples - len(segment_audio))])
                elif len(segment_audio) > target_samples:
                    segment_audio = segment_audio[:target_samples]
                
                final_audio[start_sample:start_sample + len(segment_audio)] = segment_audio
            
            timing_data.append({'text': text, 'start': target_start, 'end': target_end, 'type': 'original'})
            continue
        
        logger.info(f"Segment {idx+1}: '{text[:30]}...' ({target_duration:.2f}s)")
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            
            asyncio.run(_synthesize(text, voice, tmp_path))
            
            wav_data, _ = librosa.load(tmp_path, sr=sample_rate, mono=True)
            os.unlink(tmp_path)
            
            target_samples = int(target_duration * sample_rate)
            
            if len(wav_data) > 0 and target_samples > 0:
                rate = len(wav_data) / target_samples
                rate = max(0.5, min(2.0, rate))
                wav_data = librosa.effects.time_stretch(wav_data, rate=rate)
            
            if len(wav_data) < target_samples:
                wav_data = np.concatenate([wav_data, np.zeros(target_samples - len(wav_data))])
            elif len(wav_data) > target_samples:
                wav_data = wav_data[:target_samples]
            
            start_sample = int(target_start * sample_rate)
            end_sample = start_sample + len(wav_data)
            
            if end_sample > len(final_audio):
                final_audio = np.concatenate([final_audio, np.zeros(end_sample - len(final_audio))])
            
            final_audio[start_sample:end_sample] = wav_data.astype(np.float32)
            
            timing_data.append({'text': text, 'start': target_start, 'end': target_end, 'type': 'dubbed'})
            
        except Exception as e:
            logger.warning(f"TTS failed for segment {idx+1}: {e}")
    
    max_val = np.max(np.abs(final_audio))
    if max_val > 0:
        final_audio = final_audio / max_val * 0.95
    
    sf.write(dubbed_audio_path, final_audio, sample_rate)
    logger.info(f"Dubbed audio saved to: {dubbed_audio_path}")
    
    outputs_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'outputs')
    os.makedirs(outputs_dir, exist_ok=True)
    mp3_path = os.path.join(outputs_dir, "hindi.mp3")
    subprocess.run(['ffmpeg', '-y', '-i', dubbed_audio_path, '-codec:a', 'libmp3lame', '-b:a', '192k', mp3_path],
                  capture_output=True)
    logger.info(f"MP3 saved to: {mp3_path}")
    
    timing_path = os.path.join(output_dir, f"{name_without_ext}_timing.json")
    with open(timing_path, 'w') as f:
        json.dump({'segments': timing_data, 'speech_regions': speech_regions}, f)
    logger.info(f"Timing saved to: {timing_path}")
    
    return dubbed_audio_path, timing_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TTS audio from translated text")
    parser.add_argument("translated", help="Path to translated JSON file")
    parser.add_argument("-a", "--audio", default=None, help="Original audio for timing (optional)")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: ./data/intermediate)")
    parser.add_argument("-l", "--language", default="hi", help="Target language code (default: hi)")
    parser.add_argument("-s", "--speed", type=float, default=1.0, help="TTS speed multiplier (default: 1.0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    logger = setup_logger(args.verbose)
    
    audio_path, timing_path = generate_tts(args.translated, args.audio, args.output, args.language, args.speed)
    print(f"\nDubbed audio: {audio_path}")
    print(f"Timing data: {timing_path}")
