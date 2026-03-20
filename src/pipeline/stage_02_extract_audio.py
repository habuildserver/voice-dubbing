import os
import argparse
import ffmpeg

def setup_logger(verbose=False):
    import logging
    logger = logging.getLogger("extract_audio")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger

logger = setup_logger()

def extract_audio(video_path: str, output_dir: str = None) -> str:
    """
    Extracts audio track from video as 16kHz mono WAV.
    
    Args:
        video_path: Path to input video file
        output_dir: Directory to save audio (default: ./data/intermediate)
    
    Returns:
        Absolute path to the extracted audio file
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'intermediate')
    
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    logger.info(f"Extracting audio from: {video_path}")
    logger.info(f"Output directory: {output_dir}")
    
    filename = os.path.basename(video_path)
    name_without_ext = os.path.splitext(filename)[0]
    audio_output_path = os.path.join(output_dir, f"{name_without_ext}.wav")
    
    try:
        (
            ffmpeg
            .input(video_path)
            .output(audio_output_path, ac=1, ar='16000', format='wav')
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
        logger.info(f"Audio extracted to: {audio_output_path}")
        return audio_output_path
        
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg failed: {e.stderr.decode('utf8')}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract audio from video")
    parser.add_argument("video", help="Path to input video file")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: ./data/intermediate)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    logger = setup_logger(args.verbose)
    
    audio_path = extract_audio(args.video, args.output)
    print(f"\nExtracted: {audio_path}")
