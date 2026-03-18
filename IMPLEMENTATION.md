# Voice Dubbing Pipeline - Implementation Guide

## Overview

This pipeline takes a video (local file or YouTube URL), transcribes the audio, translates it to Hindi, generates new Hindi speech, and merges it back with the video while preserving the original timing and pauses.

---

## Project Structure

```
Voice dubbing/
├── app.py                    # Flask web server (run this for web UI)
├── main.py                   # Main pipeline orchestrator
├── config.py                 # Configuration (paths, languages, models)
├── utils.py                  # Logger and directory setup
│
├── video_merger.py          # Merges dubbed audio with video
├── tts_generation.py        # Generates Hindi speech from translated text
├── translation.py           # Translates English text to Hindi
├── transcription.py         # Transcribes audio to text using Whisper
├── audio_processing.py      # Extracts audio from video
├── downloader.py            # Downloads YouTube videos
│
├── videos/                  # Source videos (input)
├── audio/                   # Extracted & generated audio (intermediate)
├── outputs/                 # Final dubbed videos (output)
├── static/                  # CSS for web UI
└── templates/               # HTML for web UI
```

---

## Pipeline Flow

```
┌─────────────────┐
│  Video Input    │ ──► YouTube URL or Local File
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Downloader      │ ──► (Skip if local file)
│ (YouTube)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Audio Extractor │ ──► Extracts audio as 16kHz mono WAV
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Transcription   │ ──► Whisper model: audio → text segments
│ (Whisper)       │     Each segment: {text, start, end}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Translation     │ ──► Google Translate: English → Hindi
│ (deep-translator│     Output: Hindi text segments
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TTS Generation  │ ──► Edge TTS: Hindi text → speech
│                 │     - Detect speech regions in original audio
│                 │     - Stretch/compress to fit original time gaps
│                 │     - Preserve pauses (silence in original = silence in output)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Video Merger     │ ──► Merge dubbed audio with video
│                 │     - Extend video if audio is longer
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Final Output    │ ──► Dubbed video in outputs/
└─────────────────┘
```

---

## Key Calculations

### 1. Speech Region Detection (`tts_generation.py`)

```python
# Load audio and compute energy spectrum
y, sr = librosa.load(audio_path, sr=16000)
energy = np.abs(librosa.stft(y))
energy_db = librosa.amplitude_to_db(energy, ref=np.max)

# Threshold: frames above -50dB are speech
is_speech = energy_db.mean(axis=0) > -50
```

**Output:** List of regions `[{start, end, speech}, ...]`

### 2. Time Stretching for Dubbed Audio

Each translated segment is stretched/compressed to fit exactly in its original time gap:

```python
target_duration = original_end - original_start  # e.g., 3.0 seconds
target_samples = target_duration * sample_rate   # 3.0 * 24000 = 72000

# Calculate stretch rate
rate = len(wav_data) / target_samples            # if TTS produces 4s audio for 3s gap

# Stretch to fit
wav_data = librosa.effects.time_stretch(wav_data, rate=rate)
```

**Result:** If original speech was 3 seconds, dubbed audio is also 3 seconds - preserving timing.

### 3. Preserving Pauses

The final audio array is initialized with zeros (silence):

```python
final_audio = np.zeros(total_samples, dtype=np.float32)
```

Audio is placed only at timestamps where original had speech. Silence regions remain as zeros.

### 4. Video Extension (`video_merger.py`)

If dubbed audio is longer than video:
- Extend video by looping last frame
- Use FFmpeg: `loop=999:1:0` filter

---

## Important Locations

| Purpose | File | Key Function |
|---------|------|--------------|
| Web UI | `app.py` | Flask routes `/`, `/api/dub`, `/api/status` |
| Pipeline | `main.py` | `run_pipeline()` - orchestrates all stages |
| Audio Extraction | `audio_processing.py` | `extract_audio()` |
| Transcription | `transcription.py` | `transcribe_audio()` |
| Translation | `translation.py` | `translate_segments()` |
| TTS Generation | `tts_generation.py` | `generate_dubbed_audio()` |
| Video Merge | `video_merger.py` | `run_lipsync()` |
| Configuration | `config.py` | `WHISPER_MODEL`, `TARGET_LANGUAGE`, directories |

---

## Running the Pipeline

### Web Interface
```bash
python app.py
```
Then open http://127.0.0.1:5050

### Command Line
```bash
python main.py <video_path_or_youtube_url>
```

---

## Dependencies

- **Whisper** - Transcription
- **deep-translator** - Translation  
- **edge-tts** - Hindi speech synthesis
- **librosa** - Audio processing & time stretching
- **ffmpeg** - Video/audio manipulation
- **Flask** - Web server
