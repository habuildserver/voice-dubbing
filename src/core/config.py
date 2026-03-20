import os
from pathlib import Path

# Base directories (project root is 3 levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Data directories
INPUTS_DIR = BASE_DIR / "data" / "inputs"       # Source videos
INTERMEDIATE_DIR = BASE_DIR / "data" / "intermediate"  # Extracted/generated audio
OUTPUTS_DIR = BASE_DIR / "data" / "outputs"      # Final dubbed videos
TEMP_DIR = BASE_DIR / "temp"                    # Temporary files

# Aliases for backward compatibility
VIDEOS_DIR = INPUTS_DIR
AUDIO_DIR = INTERMEDIATE_DIR

# Model configurations
WHISPER_MODEL = "tiny"  # Can be 'tiny', 'base', 'small', 'medium', 'large'
TARGET_LANGUAGE = "hi"
SOURCE_LANGUAGE = "en"

# Helper to ensure directories exist
def setup_directories():
    for directory in [INPUTS_DIR, INTERMEDIATE_DIR, OUTPUTS_DIR, TEMP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
