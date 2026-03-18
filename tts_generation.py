import os
import asyncio
import tempfile
import re
import numpy as np
import soundfile as sf
from config import AUDIO_DIR, TARGET_LANGUAGE
from utils import logger
import traceback
import librosa


def is_counting_text(text: str) -> bool:
    """
    Check if text contains counting patterns like 'one', 'two', 'three', etc.
    Returns True if text IS counting (majority or entirely counting words).
    """
    text_lower = text.lower().strip()
    
    counting_words = [
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty',
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
        'first', 'second', 'third', 'fourth', 'fifth'
    ]
    
    # Clean punctuation
    text_clean = re.sub(r'[,\.\!\?\-\:\;]', ' ', text_lower)
    words = re.findall(r'\b\w+\b', text_clean)
    
    if not words:
        return False
    
    # Check if at least 2 counting words present (for short texts) or 30% for longer
    counting_matches = sum(1 for w in words if w in counting_words)
    
    # If very short (1-3 words) and has counting, skip
    if len(words) <= 3 and counting_matches >= 1:
        return True
    
    # For longer text, use 30% threshold
    return counting_matches >= len(words) * 0.3


def detect_speech_regions(audio_path: str, sample_rate: int = 16000) -> list:
    """
    Detect speech and silence regions in the original audio.
    """
    logger.info("Detecting speech regions in original audio...")
    
    y, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
    
    energy = np.abs(librosa.stft(y))
    energy_db = librosa.amplitude_to_db(energy, ref=np.max)
    energy_per_frame = energy_db.mean(axis=0)
    
    silence_threshold = -50
    
    frame_length = 2048
    hop_length = 512
    frame_duration = hop_length / sr
    
    is_speech = energy_per_frame > silence_threshold
    
    regions = []
    current_speech = is_speech[0]
    start_frame = 0
    
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
    
    merged_regions = []
    for r in regions:
        if r['speech'] and merged_regions and not merged_regions[-1]['speech']:
            gap = r['start'] - merged_regions[-1]['end']
            if gap < 0.3:
                merged_regions[-1]['end'] = r['end']
                continue
        merged_regions.append(r)
    
    logger.info(f"Detected {len(merged_regions)} audio regions (speech/silence)")
    speech_count = sum(1 for r in merged_regions if r['speech'])
    logger.info(f"Speech regions: {speech_count}, Silence regions: {len(merged_regions) - speech_count}")
    
    return merged_regions


VOICE_MAP = {
    "hi": "hi-IN-MadhurNeural",
    "en": "en-US-GuyNeural",
}


async def _synthesize_segment(text: str, voice: str, output_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_dubbed_audio(segments: list, original_audio_path: str,
                           video_duration_sec: float, progress_callback=None) -> tuple[str, str]:
    """
    Segment-wise dubbing: each segment fits exactly in its original time gap.
    Skip counting patterns and use original audio instead.
    """
    voice = VOICE_MAP.get(TARGET_LANGUAGE, "hi-IN-MadhurNeural")
    logger.info(f"Using edge-tts voice: {voice}")

    speech_regions = detect_speech_regions(original_audio_path)
    
    # Load original audio for copying counting segments
    original_audio, orig_sr = librosa.load(original_audio_path, sr=24000, mono=True)
    
    sample_rate = 24000
    total_samples = int((video_duration_sec + 30.0) * sample_rate)
    final_audio = np.zeros(total_samples, dtype=np.float32)

    filename = os.path.basename(original_audio_path)
    name_without_ext = os.path.splitext(filename)[0]
    output_audio_path = os.path.join(AUDIO_DIR, f"{name_without_ext}_dubbed.wav")

    timing_data = []
    regions_to_process = [r for r in speech_regions if r['speech']]
    
    logger.info(f"Processing {len(segments)} segments into {len(regions_to_process)} speech regions")

    for idx, seg in enumerate(segments):
        text = seg.get('text', '').strip()
        if not text:
            continue
        
        orig_start = seg.get('start', 0)
        orig_end = seg.get('end', orig_start + 2)
        orig_duration = orig_end - orig_start
        
        # Find matching speech region
        target_start = orig_start
        target_end = orig_end
        
        # Find speech region that contains or is closest to this segment
        for region in regions_to_process:
            if region['start'] <= orig_start <= region['end']:
                target_start = region['start']
                target_end = region['end']
                break
            elif region['start'] > orig_start and (idx == 0 or regions_to_process[regions_to_process.index(region) - 1]['end'] <= orig_start):
                target_start = region['start']
                target_end = region['end']
                break
        
        target_duration = target_end - target_start
        
        # Check if this segment should keep original audio (marked during translation)
        if seg.get('keep_original', False):
            logger.info(f"Segment {idx+1}: keep_original flag set - using original audio")
            logger.info(f"Segment {idx+1}: SKIPPING (counting) - using original audio - '{text}'")
            
            # Copy original audio for this segment
            start_sample = int(target_start * sample_rate)
            end_sample = int(target_end * sample_rate)
            
            if end_sample > len(original_audio):
                end_sample = len(original_audio)
            
            if start_sample < len(original_audio) and end_sample <= len(original_audio):
                original_segment = original_audio[start_sample:end_sample]
                
                # Ensure we have exact number of samples
                target_samples = int(target_duration * sample_rate)
                if len(original_segment) < target_samples:
                    silence = np.zeros(target_samples - len(original_segment), dtype=np.float32)
                    original_segment = np.concatenate([original_segment, silence])
                elif len(original_segment) > target_samples:
                    original_segment = original_segment[:target_samples]
                
                # Place in final audio
                if start_sample + len(original_segment) <= len(final_audio):
                    final_audio[start_sample:start_sample + len(original_segment)] = original_segment
            
            timing_data.append({
                'text': text,
                'start': float(target_start),
                'end': float(target_end),
                'duration': float(target_duration),
                'type': 'original'  # Mark as original audio
            })
            continue
        
        logger.info(f"Segment {idx+1}: original={orig_duration:.2f}s, target={target_duration:.2f}s - '{text[:30]}...'")

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            asyncio.run(_synthesize_segment(text, voice, tmp_path))

            wav_data, _ = librosa.load(tmp_path, sr=sample_rate, mono=True)
            os.unlink(tmp_path)
            
            target_samples = int(target_duration * sample_rate)
            
            # Stretch/compress to fit exactly in target duration
            if len(wav_data) > 0 and target_samples > 0:
                rate = len(wav_data) / target_samples
                if 0.5 <= rate <= 2.0:
                    wav_data = librosa.effects.time_stretch(wav_data, rate=rate)
                elif rate > 2.0:
                    wav_data = librosa.effects.time_stretch(wav_data, rate=2.0)
                elif rate < 0.5:
                    wav_data = librosa.effects.time_stretch(wav_data, rate=0.5)
            
            # Pad or trim to exact target
            if len(wav_data) < target_samples:
                silence = np.zeros(target_samples - len(wav_data), dtype=np.float32)
                wav_data = np.concatenate([wav_data, silence])
            elif len(wav_data) > target_samples:
                wav_data = wav_data[:target_samples]
            
            start_sample = int(target_start * sample_rate)
            end_sample = start_sample + len(wav_data)
            
            if end_sample > len(final_audio):
                padding = np.zeros(end_sample - len(final_audio), dtype=np.float32)
                final_audio = np.concatenate([final_audio, padding])
            
            # Place at correct position
            final_audio[start_sample:end_sample] = wav_data.astype(np.float32)
            
            timing_data.append({
                'text': text,
                'start': float(target_start),
                'end': float(target_end),
                'duration': float(target_duration),
                'type': 'dubbed'
            })

        except Exception as e:
            logger.warning(f"Failed TTS: {e}")
            continue

        if progress_callback:
            progress_callback((idx + 1) / len(segments),
                              f"Generated {idx + 1}/{len(segments)}")

    max_val = np.max(np.abs(final_audio))
    if max_val > 0:
        final_audio = final_audio / max_val * 0.95

    logger.info(f"Saving to: {output_audio_path}")
    sf.write(output_audio_path, final_audio, sample_rate)
    
    timing_map_path = os.path.join(AUDIO_DIR, f"{name_without_ext}_timing.json")
    import json
    with open(timing_map_path, 'w') as f:
        json.dump({
            'segments': timing_data,
            'speech_regions': [{'start': r['start'], 'end': r['end'], 'speech': r['speech']} for r in speech_regions]
        }, f)
    
    return output_audio_path, timing_map_path
