import os
import subprocess
from config import OUTPUTS_DIR
from utils import logger
import traceback

def run_lipsync(video_path: str, dubbed_audio_path: str, timing_map_path: str = None) -> str:
    """
    Merges the original video with the dubbed audio directly.
    Audio is already timed to match original speech segments.
    """
    logger.info("Merging generated Hindi audio with the original video...")

    filename = os.path.basename(video_path)
    name_without_ext = os.path.splitext(filename)[0]
    final_output_path = os.path.join(OUTPUTS_DIR, f"{name_without_ext}_final.mp4")

    try:
        video_duration = None
        audio_duration = None
        
        try:
            video_dur = subprocess.run(
                f'ffprobe -v error -show_entries format=duration -of default=noprintwrappers=1:nokey=1 "{video_path}"',
                shell=True, capture_output=True, text=True, check=True
            ).stdout.strip()
            video_duration = float(video_dur)
        except:
            logger.warning("Could not get video duration")
        
        try:
            audio_dur = subprocess.run(
                f'ffprobe -v error -show_entries format=duration -of default=noprintwrappers=1:nokey=1 "{dubbed_audio_path}"',
                shell=True, capture_output=True, text=True, check=True
            ).stdout.strip()
            audio_duration = float(audio_dur)
        except:
            logger.warning("Could not get audio duration")
        
        if video_duration and audio_duration:
            logger.info(f"Video: {video_duration:.2f}s, Audio: {audio_duration:.2f}s")
        
        temp_video = video_path

        # If audio is longer than video, extend video
        if video_duration and audio_duration and audio_duration > video_duration:
            try:
                logger.info(f"Extending video from {video_duration:.2f}s to {audio_duration:.2f}s")
                temp_extended = video_path.replace('.mp4', '_extended.mp4')
                subprocess.run(
                    f'ffmpeg -y -i "{video_path}" -f lavfi -i color=c=black:s=640x360:r=25 -filter_complex "[0:v]loop=999:1:0,setpts=N/FRAME_RATE/TB[a]" -map "[a]" -t {audio_duration} -c:v libx264 -preset fast -crf 23 "{temp_extended}"',
                    shell=True, capture_output=True, check=True
                )
                temp_video = temp_extended
            except Exception as e:
                logger.warning(f"Could not extend video: {e}")
        
        # Merge video and audio
        subprocess.run(
            f'ffmpeg -y -i "{temp_video}" -i "{dubbed_audio_path}" -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 44100 -ac 2 "{final_output_path}"',
            shell=True, capture_output=True, check=True
        )
        
        if temp_video != video_path and os.path.exists(temp_video):
            os.remove(temp_video)

        logger.info(f"Video merged successfully! Final dubbed video saved to: {final_output_path}")
        return final_output_path

    except Exception as e:
        logger.error(f"Failed during video assembly. Error: {e}")
        logger.debug(traceback.format_exc())
        raise e
