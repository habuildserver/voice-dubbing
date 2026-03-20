# AI Video Dubbing Pipeline

Automated pipeline that translates and dubs videos from English to Hindi using AI.

---

## Project Structure

```
voice-dubbing/
├── main.py                     # CLI entry point (full pipeline)
├── requirements.txt            # Dependencies
│
├── src/                        # Source code
│   ├── core/                   # Core utilities
│   │   ├── config.py           # Configuration & paths
│   │   └── logger.py           # Logging setup
│   │
│   ├── pipeline/               # Sequential pipeline stages
│   │   ├── stage_01_download.py
│   │   ├── stage_02_extract_audio.py
│   │   ├── stage_03_transcribe.py
│   │   ├── stage_04_translate.py
│   │   ├── stage_05_tts.py
│   │   └── stage_06_merge.py
│   │
│   └── api/                    # Web server
│       └── server.py
│
├── tools/                      # Standalone tools (use independently)
│   ├── download.py             # Download YouTube videos
│   ├── transcribe.py           # Transcribe audio to text
│   ├── translate.py            # Translate text between languages
│   ├── tts.py                  # Text-to-Speech synthesis
│   └── merge.py                # Merge video with audio
│
├── web/                        # Web UI
│   ├── static/style.css
│   └── templates/index.html
│
├── data/                       # Data directories
│   ├── inputs/                 # Source videos
│   ├── intermediate/           # Extracted/generated audio
│   └── outputs/                # Final dubbed videos
│
└── temp/                      # Temporary files
```

---

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Run Full Pipeline

```bash
# Using YouTube URL
python main.py "https://youtube.com/watch?v=..."

# Using local video
python main.py ./video.mp4

# Custom languages
python main.py "URL" -s en -t es
```

### 3. Run Web UI

```bash
python -m src.api.server
# Open http://localhost:5050
```

---

## Standalone Tools

Each tool can be used independently. No pipeline required.

### Download Videos

```bash
# Download from YouTube
python tools/download.py "https://youtube.com/watch?v=..."

# Save to specific directory
python tools/download.py "URL" -o ./my_videos/

# Get video info only
python tools/download.py "URL" --info
```

### Transcribe Audio

```bash
# Basic transcription
python tools/transcribe.py audio.wav -o transcript.txt

# Higher quality model, JSON output
python tools/transcribe.py audio.wav -m base -j -o transcript.json

# List available models
python tools/transcribe.py --list-models
```

### Translate Text

```bash
# Translate text directly
python tools/translate.py "Hello world" -t hi

# Translate file content
python tools/translate.py input.txt -t hi -o output.txt

# Spanish to French
python tools/translate.py "Hola mundo" -s es -t fr
```

### Text-to-Speech

```bash
# Generate Hindi speech
python tools/tts.py "नमस्ते" -l hi -o hello.mp3

# Use specific text file
python tools/tts.py script.txt -l hi -o audio.mp3

# List available voices
python tools/tts.py --list-voices
```

### Merge Video + Audio

```bash
# Basic merge
python tools/merge.py video.mp4 audio.wav -o output.mp4

# Adjust video speed to match audio
python tools/merge.py video.mp4 audio.wav -s 0.95 -o output.mp4
```

---

## Pipeline Flow

```
Video Input
    │
    ▼
┌─────────────────────────────────────────┐
│ Stage 1: Download (yt-dlp)              │
│ Input: YouTube URL → Output: .mp4       │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Stage 2: Extract Audio (ffmpeg)          │
│ Input: .mp4 → Output: 16kHz WAV        │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Stage 3: Transcribe (Whisper)           │
│ Input: WAV → Output: transcript.json   │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Stage 4: Translate (Google)             │
│ Input: transcript.json → Output:        │
│        translated.json                  │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Stage 5: TTS (Edge TTS)                │
│ Input: translated.json → Output:        │
│        dubbed.wav, timing.json          │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Stage 6: Merge (ffmpeg)                 │
│ Input: original.mp4 + dubbed.wav →      │
│        Output: final.mp4               │
└─────────────────────────────────────────┘
```

---

## Using Individual Pipeline Stages

Each stage can be run independently:

```bash
# Stage 1: Download
python src/pipeline/stage_01_download.py "URL" -o ./data/inputs/

# Stage 2: Extract audio
python src/pipeline/stage_02_extract_audio.py ./video.mp4 -o ./data/intermediate/

# Stage 3: Transcribe
python src/pipeline/stage_03_transcribe.py ./audio.wav -m tiny -o ./data/intermediate/

# Stage 4: Translate
python src/pipeline/stage_04_translate.py ./transcript.json -t hi

# Stage 5: TTS
python src/pipeline/stage_05_tts.py ./translated.json -a ./audio.wav -l hi

# Stage 6: Merge
python src/pipeline/stage_06_merge.py ./video.mp4 ./dubbed.wav -o ./data/outputs/
```

---

## Data Directories

| Directory | Purpose |
|-----------|---------|
| `data/inputs/` | Source videos (YouTube downloads or uploaded files) |
| `data/intermediate/` | Extracted audio, transcripts, translations, dubbed audio |
| `data/outputs/` | Final dubbed videos |
| `temp/` | Temporary processing files |

---

## Configuration

Edit `src/core/config.py`:

```python
WHISPER_MODEL = "tiny"      # tiny, base, small, medium, large
TARGET_LANGUAGE = "hi"       # Target language code
SOURCE_LANGUAGE = "en"       # Source language code
```

Edit `main.py` for pipeline settings:

```python
TTS_SPEED = 0.95             # TTS audio speed (higher = faster)
VIDEO_SPEED = 1.0             # Video playback speed
```

---

## Supported Languages

| Code | Language | Code | Language |
|------|----------|------|----------|
| en | English | ja | Japanese |
| hi | Hindi | ko | Korean |
| es | Spanish | zh | Chinese |
| fr | French | ru | Russian |
| de | German | ar | Arabic |
| it | Italian | pt | Portuguese |

---

## Dependencies

- **yt-dlp** - YouTube video downloading
- **ffmpeg-python** - Audio/video processing
- **openai-whisper** - Speech transcription
- **deep-translator** - Text translation
- **edge-tts** - Text-to-speech synthesis
- **librosa** - Audio analysis
- **flask** - Web server
