import os
import asyncio
import tempfile
import numpy as np
import soundfile as sf
from config import AUDIO_DIR, TARGET_LANGUAGE
from utils import logger
import traceback

# Map language codes to edge-tts voices
VOICE_MAP = {
    "hi": "hi-IN-MadhurNeural",   # Hindi male (natural)
    "en": "en-US-GuyNeural",
}

async def _synthesize_segment(text: str, voice: str, output_path: str):
    """Async helper to call edge-tts for a single segment."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def _time_stretch(wav: np.ndarray, target_length: int) -> np.ndarray:
    """Stretch or compress audio to match target length using librosa."""
    import librosa
    current_length = len(wav)
    if current_length == target_length:
        return wav
    if current_length > target_length:
        return wav[:target_length]
    # Stretch to target length
    stretched = librosa.resample(wav, orig_sr=len(wav), target_sr=target_length)
    if len(stretched) > target_length:
        stretched = stretched[:target_length]
    elif len(stretched) < target_length:
        padding = np.zeros(target_length - len(stretched))
        stretched = np.concatenate([stretched, padding])
    return stretched


def generate_dubbed_audio(segments: list, original_audio_path: str,
                           video_duration_sec: float, progress_callback=None) -> tuple[str, str]:
    """
    Group segments into larger chunks for smooth flow.
    """
    voice = VOICE_MAP.get(TARGET_LANGUAGE, "hi-IN-MadhurNeural")
    logger.info(f"Using edge-tts voice: {voice}")

    sample_rate = 24000
    total_samples = int((video_duration_sec + 30.0) * sample_rate)
    final_audio = np.zeros(total_samples, dtype=np.float32)

    filename = os.path.basename(original_audio_path)
    name_without_ext = os.path.splitext(filename)[0]
    output_audio_path = os.path.join(AUDIO_DIR, f"{name_without_ext}_dubbed.wav")

    # Group segments into larger chunks (gap < 3 seconds)
    groups = []
    current_group = None
    
    for seg in segments:
        text = seg.get('text', '').strip()
        if not text:
            continue
        
        start = seg.get('start', 0)
        
        if current_group is None:
            current_group = {'text': text, 'start': start, 'end': seg.get('end', start + 2)}
        elif start - current_group['end'] < 3.0:
            current_group['text'] += ' ' + text
            current_group['end'] = seg.get('end', start + 2)
        else:
            groups.append(current_group)
            current_group = {'text': text, 'start': start, 'end': seg.get('end', start + 2)}
    
    if current_group:
        groups.append(current_group)
    
    logger.info(f"Grouped into {len(groups)} chunks")

    for idx, chunk in enumerate(groups):
        text = chunk['text']
        start_time = chunk['start']
        end_time = chunk['end']
        
        logger.info(f"Chunk {idx+1}/{len(groups)}: [{start_time:.2f}s] '{text[:30]}...'")

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            asyncio.run(_synthesize_segment(text, voice, tmp_path))

            import librosa
            wav_data, _ = librosa.load(tmp_path, sr=sample_rate, mono=True)
            os.unlink(tmp_path)
            
            # Slight speedup
            wav_data = librosa.effects.time_stretch(wav_data, rate=1.25)
            
            start_sample = int(start_time * sample_rate)
            
            # Use modulo to handle overlaps cleanly
            existing = final_audio[start_sample:start_sample + len(wav_data)]
            if len(existing) > 0:
                # Blend with small weight on existing
                wav_data = wav_data * 0.7 + existing * 0.3
            
            end_sample = start_sample + len(wav_data)

            if end_sample > len(final_audio):
                padding = np.zeros(end_sample - len(final_audio), dtype=np.float32)
                final_audio = np.concatenate([final_audio, padding])

            final_audio[start_sample:end_sample] = wav_data.astype(np.float32)

        except Exception as e:
            logger.warning(f"Failed TTS: {e}")
            continue

        if progress_callback:
            progress_callback((idx + 1) / len(groups),
                              f"Generated {idx + 1}/{len(groups)}")

    max_val = np.max(np.abs(final_audio))
    if max_val > 0:
        final_audio = final_audio / max_val * 0.95

    logger.info(f"Saving to: {output_audio_path}")
    sf.write(output_audio_path, final_audio, sample_rate)
    
    timing_map_path = os.path.join(AUDIO_DIR, f"{name_without_ext}_timing.json")
    import json
    with open(timing_map_path, 'w') as f:
        json.dump([{"note": "grouped chunks, natural speed"}], f)
    
    return output_audio_path, timing_map_path
