import os
import argparse
import yt_dlp
from pathlib import Path

def setup_logger(verbose=False):
    import logging
    logger = logging.getLogger("downloader")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger

logger = setup_logger()

def download_youtube_video(url: str, output_dir: str = None) -> str:
    """
    Downloads a YouTube video as an MP4 file.
    
    Args:
        url: YouTube video URL
        output_dir: Directory to save video (default: ./data/inputs)
    
    Returns:
        Absolute path to the downloaded video file
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'inputs')
    
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Preparing to download video from: {url}")
    logger.info(f"Output directory: {output_dir}")
    
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_id = info_dict.get("id", None)
            video_ext = info_dict.get("ext", "mp4")
            
            if not video_id:
                raise ValueError("Could not extract video ID from the URL.")
                
            video_path = os.path.join(output_dir, f"{video_id}.{video_ext}")
            
            if not os.path.exists(video_path):
                for f in os.listdir(output_dir):
                    if f.startswith(video_id):
                        video_path = os.path.join(output_dir, f)
                        break
                        
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Download seemed to finish, but file not found at {video_path}")
                
            logger.info(f"Video successfully downloaded to: {video_path}")
            return video_path
            
    except Exception as e:
        logger.error(f"Failed to download video from {url}. Error: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download YouTube video")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: ./data/inputs)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    logger = setup_logger(args.verbose)
    
    video_path = download_youtube_video(args.url, args.output)
    print(f"\nDownloaded: {video_path}")
