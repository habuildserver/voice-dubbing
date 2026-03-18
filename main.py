import argparse
import sys
import os
import time

from utils import logger, initialize_project_environment
from downloader import download_youtube_video
from audio_processing import extract_audio
from transcription import transcribe_audio
from translation import translate_segments
from tts_generation import generate_dubbed_audio
from video_merger import run_lipsync
import ffmpeg

def get_video_duration(video_path: str) -> float:
    """Helper purely to get the video duration in seconds using ffprobe."""
    try:
        probe = ffmpeg.probe(video_path)
        return float(probe['format']['duration'])
    except Exception as e:
        logger.warning(f"Failed to extract video duration. Defaulting to 1000s. {e}")
        return 1000.0

def run_pipeline(video_source: str, status_updater=None):
    """
    Main dubbing pipeline.
    video_source: YouTube URL or local video file path
    status_updater(progress: float 0-100, stage: str, message: str, eta_seconds: float | None)
    """
    pipeline_start = time.time()

    def update(progress, stage, message):
        logger.info(message)
        if status_updater:
            elapsed = time.time() - pipeline_start
            eta = None
            if progress > 0:
                eta = (elapsed / (progress / 100)) - elapsed
            status_updater(progress=progress, stage=stage, message=message, eta_seconds=eta)

    logger.info("========== Starting Pipeline ==========")
    try:
        initialize_project_environment()

        # Check if input is URL or local file
        is_url = video_source.startswith('http://') or video_source.startswith('https://')
        
        # Stage 1 – Download or Load
        if is_url:
            update(2, "Downloading", "Downloading video from YouTube...")
            video_path = download_youtube_video(video_source)
        else:
            update(2, "Loading", f"Loading local video...")
            video_path = video_source
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            update(10, "Loading", "Video loaded successfully.")

        video_duration = get_video_duration(video_path)

        # Stage 2 – Audio extraction (10 → 15%)
        update(12, "Extracting Audio", "Extracting audio track from video...")
        audio_path = extract_audio(video_path)
        update(15, "Extracting Audio", "Audio extraction complete.")

        # Stage 3 – Transcription (15 → 30%)
        update(17, "Transcribing", "Loading Whisper model and transcribing audio...")
        english_segments = transcribe_audio(audio_path)
        update(30, "Transcribing", f"Transcription complete. {len(english_segments)} segments found.")

        # Stage 4 – Translation (30 → 50%)
        update(31, "Translating", "Translating segments to Hindi...")
        total_segs = len(english_segments)

        def translation_progress(fraction, msg):
            pct = 30 + fraction * 20  # maps 0-1 → 30-50%
            update(round(pct, 1), "Translating", msg)

        hindi_segments = translate_segments(english_segments, progress_callback=translation_progress)
        update(50, "Translating", "Translation complete.")

        # Stage 5 – TTS (50 → 90%)
        update(51, "Generating Hindi Audio", "Initialising TTS model...")

        def tts_progress(fraction, msg):
            pct = 50 + fraction * 40  # maps 0-1 → 50-90%
            update(round(pct, 1), "Generating Hindi Audio", msg)

        dubbed_audio_path, timing_map_path = generate_dubbed_audio(
            hindi_segments, audio_path, video_duration, progress_callback=tts_progress
        )
        update(90, "Generating Hindi Audio", "TTS generation complete.")

        # Stage 6 – Final assembly (90 → 100%)
        update(92, "Assembling Video", "Merging Hindi audio with original video...")
        final_video_path = run_lipsync(video_path, dubbed_audio_path, timing_map_path)
        update(100, "Done", "Pipeline finished successfully!")

        logger.info("========== Pipeline Successfully Finished ==========")
        logger.info(f"Final output: {final_video_path}")
        return final_video_path

    except Exception as e:
        logger.critical(f"Pipeline failed at a critical stage. Error: {e}")
        raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated YouTube Video Dubbing Pipeline")
    parser.add_argument("url", type=str, help="YouTube video URL to be processed")
    args = parser.parse_args()
    run_pipeline(args.url)

