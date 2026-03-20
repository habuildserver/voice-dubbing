import argparse
import sys
import os
import time
import json

from src.pipeline.stage_01_download import download_youtube_video
from src.pipeline.stage_02_extract_audio import extract_audio
from src.pipeline.stage_03_transcribe import transcribe_audio
from src.pipeline.stage_04_translate import translate_file
from src.pipeline.stage_05_tts import generate_tts
from src.pipeline.stage_06_merge import merge_video_audio

TTS_SPEED = 0.95
VIDEO_SPEED = 1.0

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    try:
        import ffmpeg
        probe = ffmpeg.probe(video_path)
        return float(probe['format']['duration'])
    except Exception as e:
        from src.core.logger import logger
        logger.warning(f"Failed to extract video duration. Defaulting to 1000s. {e}")
        return 1000.0

def run_pipeline(video_source: str, status_updater=None,
                 source_lang: str = "en", target_lang: str = "hi",
                 whisper_model: str = "tiny"):
    """
    Run the complete dubbing pipeline.
    
    Args:
        video_source: YouTube URL or local video file path
        status_updater: Callback for progress updates
        source_lang: Source language code
        target_lang: Target language code
        whisper_model: Whisper model size
    """
    from src.core.logger import logger, initialize_project_environment
    initialize_project_environment()
    
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
    logger.info(f"Source: {source_lang} → Target: {target_lang}")
    
    try:
        is_url = video_source.startswith('http://') or video_source.startswith('https://')
        
        if is_url:
            update(2, "Downloading", "Downloading video from YouTube...")
            video_path = download_youtube_video(video_source)
        else:
            update(2, "Loading", f"Loading local video...")
            video_path = os.path.abspath(video_source)
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

        update(10, "Extracting Audio", "Extracting audio track...")
        audio_path = extract_audio(video_path)
        video_duration = get_video_duration(video_path)

        update(17, "Transcribing", "Transcribing audio with Whisper...")
        transcript_path = transcribe_audio(audio_path, model_name=whisper_model, language=source_lang)

        update(31, "Translating", f"Translating {source_lang} → {target_lang}...")
        def translation_progress(fraction, msg):
            pct = 30 + fraction * 20
            update(round(pct, 1), "Translating", msg)
        
        translated_path = translate_file(transcript_path, source_lang=source_lang, target_lang=target_lang)

        update(51, "Generating TTS", "Synthesizing speech...")
        dubbed_audio_path, timing_path = generate_tts(
            translated_path, audio_path, target_lang=target_lang, speed=TTS_SPEED
        )

        update(92, "Merging", "Combining video and audio...")
        final_video_path = merge_video_audio(video_path, dubbed_audio_path, video_speed=VIDEO_SPEED)

        update(100, "Done", "Pipeline finished!")
        logger.info("========== Pipeline Complete ==========")
        logger.info(f"Output: {final_video_path}")
        
        return final_video_path

    except Exception as e:
        from src.core.logger import logger
        logger.critical(f"Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Video Dubbing Pipeline")
    parser.add_argument("source", help="YouTube URL or local video file path")
    parser.add_argument("-s", "--source-lang", default="en", help="Source language (default: en)")
    parser.add_argument("-t", "--target-lang", default="hi", help="Target language (default: hi)")
    parser.add_argument("-m", "--model", default="tiny", 
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: tiny)")
    args = parser.parse_args()
    
    run_pipeline(args.source, source_lang=args.source_lang, 
                target_lang=args.target_lang, whisper_model=args.model)
