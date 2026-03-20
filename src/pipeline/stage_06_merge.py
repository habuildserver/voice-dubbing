import os
import argparse
import subprocess

def setup_logger(verbose=False):
    import logging
    logger = logging.getLogger("merge")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger

logger = setup_logger()

def merge_video_audio(video_path: str, audio_path: str,
                      output_dir: str = None, video_speed: float = 1.0) -> str:
    """
    Merges video with dubbed audio.
    
    Args:
        video_path: Path to original video
        audio_path: Path to dubbed audio
        output_dir: Directory to save output (default: ./data/outputs)
        video_speed: Speed factor for video (1.0 = normal, <1 = slower)
    
    Returns:
        Absolute path to the final merged video
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'outputs')
    
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    logger.info(f"Video: {video_path}")
    logger.info(f"Audio: {audio_path}")
    logger.info(f"Video speed: {video_speed}x")
    
    video_path = os.path.abspath(video_path)
    audio_path = os.path.abspath(audio_path)
    
    video_duration = None
    audio_duration = None
    
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
            capture_output=True, text=True, check=True
        )
        video_duration = float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not get video duration: {e}")
    
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            capture_output=True, text=True, check=True
        )
        audio_duration = float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not get audio duration: {e}")
    
    if video_duration and audio_duration:
        logger.info(f"Video duration: {video_duration:.2f}s, Audio duration: {audio_duration:.2f}s")
    
    filename = os.path.basename(video_path)
    name_without_ext = os.path.splitext(filename)[0]
    final_output_path = os.path.join(output_dir, f"{name_without_ext}_final.mp4")
    
    temp_video = video_path
    
    if video_speed < 1.0 and video_duration:
        pts_multiplier = 1.0 / video_speed
        temp_slowed = video_path.replace('.mp4', '_slowed.mp4')
        
        logger.info(f"Slowing video to {video_speed}x (setpts={pts_multiplier:.2f})")
        
        subprocess.run(
            ['ffmpeg', '-y', '-i', video_path, '-filter:v', f'setpts={pts_multiplier}*PTS',
             '-c:a', 'copy', temp_slowed],
            capture_output=True, check=True
        )
        
        slowed_duration = video_duration / video_speed
        temp_video = temp_slowed
        
        if audio_duration and slowed_duration < audio_duration:
            extension_needed = audio_duration - slowed_duration
            temp_extended = video_path.replace('.mp4', '_extended.mp4')
            logger.info(f"Extending video by {extension_needed:.2f}s")
            
            subprocess.run(
                ['ffmpeg', '-y', '-i', temp_slowed, '-f', 'lavfi', '-i',
                 f'color=c=black:s=640x360:r=25:d={extension_needed}',
                 '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[outv]',
                 '-map', '[outv]', '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                 temp_extended],
                capture_output=True, check=True
            )
            
            temp_video = temp_extended
            if os.path.exists(temp_slowed):
                os.remove(temp_slowed)
    
    logger.info(f"Merging video with audio...")
    
    subprocess.run(
        ['ffmpeg', '-y', '-i', temp_video, '-i', audio_path,
         '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
         '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-ac', '2', final_output_path],
        capture_output=True, check=True
    )
    
    for temp_file in [video_path.replace('.mp4', '_slowed.mp4'),
                      video_path.replace('.mp4', '_extended.mp4')]:
        if os.path.exists(temp_file) and temp_file != video_path:
            try:
                os.remove(temp_file)
            except:
                pass
    
    logger.info(f"Final video saved to: {final_output_path}")
    return final_output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge video with dubbed audio")
    parser.add_argument("video", help="Path to original video")
    parser.add_argument("audio", help="Path to dubbed audio")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: ./data/outputs)")
    parser.add_argument("-s", "--speed", type=float, default=1.0, 
                        help="Video speed factor (default: 1.0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    logger = setup_logger(args.verbose)
    
    final_path = merge_video_audio(args.video, args.audio, args.output, args.speed)
    print(f"\nFinal video: {final_path}")
