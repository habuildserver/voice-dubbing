# Voice Dubbing Pipeline - Implementation Guide

## Overview

This pipeline takes a video (local file or YouTube URL), transcribes the audio, translates it to Hindi, generates new Hindi speech, and merges it back with the video while preserving the original timing and pauses.

---

## Project Structure

```
Voice dubbing/
├── app.py                    # Flask web server (UI at http://127.0.0.1:5050)
├── main.py                   # Main pipeline orchestrator
├── config.py                 # Configuration (paths, languages, models)
├── utils.py                  # Logger and directory setup
│
├── Pipeline Modules:
│   ├── downloader.py         # Downloads YouTube videos (yt-dlp)
│   ├── audio_processing.py   # Extracts audio from video (ffmpeg)
│   ├── transcription.py      # Transcribes audio to text (Whisper)
│   ├── translation.py        # Translates English → Hindi (Google Translate)
│   ├── tts_generation.py     # Generates Hindi speech (Edge TTS)
│   ├── video_merger.py       # Merges dubbed audio with video
│   └── sync_lipsync.py       # Lip sync via Sync.so API
│
├── Directories:
│   ├── videos/               # Source videos (input)
│   ├── audio/                # Extracted & generated audio (intermediate)
│   ├── outputs/              # Final dubbed videos + hindi.mp3
│   ├── static/               # CSS for web UI
│   └── templates/            # HTML for web UI
│
└── Other:
    ├── rhubarb/              # Rhubarb lip sync tool (phoneme-based)
    ├── wav2lip_pipeline/     # Wav2Lip implementation (not used)
    └── requirements.txt      # Python dependencies
```

---

## Index by Feature

| Feature | File | Key Function |
|---------|------|--------------|
| Web UI | `app.py`, `templates/index.html` | `/api/dub`, `/api/status` |
| Pipeline | `main.py` | `run_pipeline()` |
| YouTube Download | `downloader.py` | `download_youtube_video()` |
| Audio Extraction | `audio_processing.py` | `extract_audio()` |
| Transcription | `transcription.py` | `transcribe_audio()` |
| Translation | `translation.py` | `translate_segments()` |
| TTS Generation | `tts_generation.py` | `generate_dubbed_audio()` |
| Video Merge | `video_merger.py` | `run_lipsync()` |
| Lip Sync (Sync.so) | `sync_lipsync.py` | `run_lipsync()` |
| Configuration | `config.py` | Settings and paths |

---

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        VIDEO INPUT                            │
│                    (YouTube URL or Local File)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     1. DOWNLOADER                             │
│                 (yt-dlp if YouTube URL)                      │
│                   Output: .mp4 file                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  2. AUDIO EXTRACTION                         │
│              (ffmpeg - extract 16kHz mono WAV)              │
│                   Output: audio/*.wav                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    3. TRANSCRIPTION                          │
│                   (OpenAI Whisper model)                     │
│         Input: WAV → Output: [{text, start, end}, ...]       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     4. TRANSLATION                           │
│              (Google Translate via deep-translator)           │
│              Input: English segments → Hindi segments         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    5. TTS GENERATION                         │
│                      (Microsoft Edge TTS)                    │
│  - Detect speech regions in original audio                    │
│  - Generate Hindi speech for each segment                     │
│  - Time-stretch to fit original speech gaps                   │
│  - Preserve pauses (silence regions)                          │
│  - Output: dubbed WAV + timing JSON                          │
│  - Also saves: outputs/hindi.mp3                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    6. VIDEO MERGER                            │
│                      (ffmpeg)                                 │
│  - Merge dubbed audio with original video                     │
│  - Extend video if audio is longer                            │
│  - Output: outputs/*_final.mp4                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   7. OPTIONAL LIP SYNC                       │
│                  (Sync.so API - paid)                        │
│  - Requires clear face in video                              │
│  - Max 20 seconds on free tier                               │
│  - Uses file.io for temporary hosting                         │
│  - Output: Lip-synced video                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Settings (main.py)

```python
# Current fixed settings
TTS_SPEED = 0.95    # Audio slightly slowed (0.95x)
VIDEO_SPEED = 1.0   # Video at normal speed
```

---

## How TTS Works

### Speech Region Detection
```python
# Compute energy spectrum of original audio
y, sr = librosa.load(audio_path, sr=16000)
energy = np.abs(librosa.stft(y))
energy_db = librosa.amplitude_to_db(energy)

# Frames above -60dB are speech
is_speech = energy_db.mean(axis=0) > -60
```

### Time Stretching
```python
target_duration = (original_end - original_start) / TTS_SPEED
target_samples = target_duration * sample_rate

# Calculate stretch rate
rate = len(wav_data) / target_samples
wav_data = librosa.effects.time_stretch(wav_data, rate=rate)
```

### Preserving Pauses
```python
# Initialize with silence (zeros)
final_audio = np.zeros(total_samples, dtype=np.float32)

# Place dubbed audio only at speech timestamps
# Silence regions remain as zeros
```

---

## Running the Pipeline

### Web Interface
```bash
python app.py
```
Open http://127.0.0.1:5050

### Command Line
```bash
python main.py <video_path_or_youtube_url>
```

---

## Output Files

| File | Description |
|------|-------------|
| `outputs/*_final.mp4` | Final dubbed video |
| `outputs/hindi.mp3` | Hindi dubbed audio only |
| `audio/*_dubbed.wav` | Intermediate dubbed WAV |
| `audio/*_timing.json` | Segment timing data |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `whisper` | Audio transcription |
| `deep-translator` | English → Hindi translation |
| `edge-tts` | Hindi speech synthesis |
| `librosa` | Audio processing & time stretching |
| `soundfile` | Audio file I/O |
| `yt-dlp` | YouTube video downloading |
| `ffmpeg` | Video/audio manipulation |
| `flask` | Web server |

---

## Future Scope

### 1. Multi-language Support
- Add support for languages beyond Hindi
- Language selection in UI
- Configurable target language in `config.py`

### 2. Voice Cloning
- Use ElevenLabs API for custom voices
- Clone original speaker's voice in dubbed version
- Currently `config.py` has ElevenLabs API key slot

### 3. Improved Lip Sync
- **Sync.so API** integration is ready but requires:
  - Paid subscription for longer videos
  - Clear, front-facing face in video
- **Wav2Lip** implementation exists in `wav2lip_pipeline/` but needs GPU
- Future: Local GPU-based lip sync (Wav2Lip, DiffTalk)

### 4. Video Speed Control UI
- Add slider in UI for speed adjustment
- Currently hardcoded in `main.py`

### 5. Batch Processing
- Process multiple videos in queue
- Background job management

### 6. Subtitle Generation
- Add SRT/VTT subtitles in Hindi
- Burn subtitles into video

### 7. Audio-Only Mode
- Generate dubbed audio without video
- Already partially works (hindi.mp3)

### 8. Quality Improvements
- Better silence detection
- Improved translation quality (LLM-based)
- Prosody control for natural speech

---

## Troubleshooting

### Lip Sync Fails
- Sync.so requires clear face visibility
- Video must be ≤20 seconds (free tier)
- Check `sync_lipsync.py` for API key

### Audio Too Long/Short
- Adjust `TTS_SPEED` in `main.py`
- Check silence threshold in `tts_generation.py`

### YouTube Download Fails
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Check video is not age-restricted or private

### Poor Translation Quality
- Currently using Google Translate
- Could replace with OpenAI/Gemini API for better results
