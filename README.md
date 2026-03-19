# 🎙 AI Video Dubbing Pipeline

A fully automated, locally-run Python pipeline + Web UI that takes a YouTube video URL or local video file and produces a **Hindi-dubbed version** — with AI voice synthesis, timing preservation, and optional lip sync.

---

## ✨ Features

| Stage | Tool Used | What it does |
|---|---|---|
| **Download** | `yt-dlp` | Downloads video from YouTube |
| **Audio Extraction** | `ffmpeg` | Extracts WAV audio track |
| **Transcription** | `OpenAI Whisper` | Converts English speech → timestamped text |
| **Translation** | `Google Translate` | Translates English → Hindi |
| **TTS** | `Microsoft Edge TTS` | Synthesizes Hindi speech |
| **Video Assembly** | `ffmpeg` | Merges dubbed audio with original video |
| **Lip Sync** | `Sync.so API` (optional) | Syncs mouth movements to audio |

---

## 🖥️ Web Interface (Recommended)

```bash
source venv/bin/activate
python app.py
```

Then open **[http://localhost:5050](http://localhost:5050)**, paste a YouTube URL or upload a video and hit **Dub Video**.

Features:
- 🔵 Animated progress bar with stage labels
- 📊 Percentage complete + ETA
- 🎬 In-browser video playback
- ⬇️ Download Video + Download Audio buttons
- ▲▼ Scroll buttons

---

## 🚀 Quick Start

### 1. System Prerequisites

- **Python 3.9–3.11**
- **FFmpeg**:
  ```bash
  # macOS
  brew install ffmpeg
  # Ubuntu/Debian
  sudo apt install ffmpeg
  ```

### 2. Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run

```bash
python app.py
```

---

## 📁 Project Structure

```
Voice dubbing/
├── app.py                    # Flask web server (UI at http://127.0.0.1:5050)
├── main.py                   # Main pipeline orchestrator
├── config.py                 # Configuration (paths, languages, models)
├── utils.py                 # Logger and directory setup
│
├── Pipeline Modules:
│   ├── downloader.py         # Downloads YouTube videos (yt-dlp)
│   ├── audio_processing.py   # Extracts audio from video (ffmpeg)
│   ├── transcription.py     # Transcribes audio to text (Whisper)
│   ├── translation.py        # Translates English → Hindi
│   ├── tts_generation.py    # Generates Hindi speech (Edge TTS)
│   ├── video_merger.py      # Merges dubbed audio with video
│   └── sync_lipsync.py      # Lip sync via Sync.so API
│
├── Directories:
│   ├── videos/               # Source videos (input)
│   ├── audio/                # Extracted & generated audio (intermediate)
│   ├── outputs/              # Final dubbed videos + hindi.mp3
│   ├── static/               # CSS for web UI
│   └── templates/            # HTML for web UI
│
└── Other:
    ├── rhubarb/              # Rhubarb lip sync tool
    ├── wav2lip_pipeline/    # Wav2Lip (GPU required)
    └── requirements.txt      # Python dependencies
```

---

## 🔧 Feature Index

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

## ⚙️ Current Settings

```python
# main.py - Fixed settings
TTS_SPEED = 0.95    # Audio slightly slowed (0.95x)
VIDEO_SPEED = 1.0    # Video at normal speed
```

To change settings, edit these values in `main.py`.

---

## 🔄 Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        VIDEO INPUT                            │
│                    (YouTube URL or Local File)                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     1. DOWNLOADER                             │
│                 (yt-dlp if YouTube URL)                      │
│                   Output: .mp4 file                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  2. AUDIO EXTRACTION                         │
│              (ffmpeg - extract 16kHz mono WAV)              │
│                   Output: audio/*.wav                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    3. TRANSCRIPTION                          │
│                   (OpenAI Whisper model)                     │
│         Input: WAV → Output: [{text, start, end}, ...]      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     4. TRANSLATION                           │
│              (Google Translate via deep-translator)         │
│              Input: English segments → Hindi segments        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    5. TTS GENERATION                         │
│                      (Microsoft Edge TTS)                    │
│  - Detect speech regions in original audio                    │
│  - Generate Hindi speech for each segment                    │
│  - Time-stretch to fit original speech gaps                  │
│  - Preserve pauses (silence regions)                         │
│  - Output: dubbed WAV + timing JSON                          │
│  - Also saves: outputs/hindi.mp3                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    6. VIDEO MERGER                           │
│                      (ffmpeg)                                │
│  - Merge dubbed audio with original video                     │
│  - Extend video if audio is longer                           │
│  - Output: outputs/*_final.mp4                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔊 TTS Technical Details

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

## 📤 Output Files

| File | Description |
|------|-------------|
| `outputs/*_final.mp4` | Final dubbed video |
| `outputs/hindi.mp3` | Hindi dubbed audio only |
| `audio/*_dubbed.wav` | Intermediate dubbed WAV |
| `audio/*_timing.json` | Segment timing data |

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| `ffmpeg: command not found` | Install system ffmpeg (not pip) |
| Lip sync fails | Sync.so requires clear face visibility + ≤20s video (free tier) |
| Audio too long/short | Adjust `TTS_SPEED` in `main.py` |
| YouTube download fails | Update yt-dlp or check video is not age-restricted |
| Port 5000 forbidden | Use `localhost:5050` instead |

---

## 🚀 Future Scope

### 1. Multi-language Support
- Add support for languages beyond Hindi
- Language selection in UI
- Configurable target language

### 2. Voice Cloning
- Use ElevenLabs API for custom voices
- Clone original speaker's voice in dubbed version
- `config.py` has ElevenLabs API key slot ready

### 3. Improved Lip Sync
- **Sync.so API** ready but requires paid subscription for longer videos
- **Wav2Lip** in `wav2lip_pipeline/` needs GPU
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

### 7. Quality Improvements
- Better silence detection
- LLM-based translation for better quality
- Prosody control for natural speech

---

## 📜 License

This project uses open-source tools. Please ensure you comply with individual licenses of `Edge TTS`, `OpenAI Whisper` (MIT), and `yt-dlp` (Unlicense).
