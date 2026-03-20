#!/usr/bin/env python3
"""
Standalone Video-Audio Merger

Merges a video file with an audio track.
Can adjust video speed to match audio duration.

Usage:
    python tools/merge.py video.mp4 audio.wav -o output.mp4
    python tools/merge.py video.mp4 audio.wav -s 0.95 -o output.mp4
"""
import argparse
import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def get_duration(file_path: str) -> float:
    """Get media file duration in seconds."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())
    except:
        return None

def merge(video_path: str, audio_path: str, output_path: str,
          video_speed: float = 1.0):
    """
    Merge video with audio track.
    
    Args:
        video_path: Path to video file
        audio_path: Path to audio file
        output_path: Output file path
        video_speed: Video speed factor (<1 = slower)
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found: {audio_path}")
        sys.exit(1)
    
    video_path = os.path.abspath(video_path)
    audio_path = os.path.abspath(audio_path)
    output_path = os.path.abspath(output_path)
    
    video_duration = get_duration(video_path)
    audio_duration = get_duration(audio_path)
    
    print(f"Video: {os.path.basename(video_path)} ({video_duration:.1f}s)")
    print(f"Audio: {os.path.basename(audio_path)} ({audio_duration:.1f}s)")
    print(f"Video speed: {video_speed}x")
    
    temp_video = video_path
    
    if video_speed < 1.0 and video_duration:
        pts = 1.0 / video_speed
        slowed = video_path.replace('.mp4', '_slow.mp4')
        
        print(f"Slowing video (setpts={pts:.2f})...")
        subprocess.run(
            ['ffmpeg', '-y', '-i', video_path, '-filter:v', f'setpts={pts}*PTS',
             '-c:a', 'copy', slowed],
            capture_output=True, check=True
        )
        temp_video = slowed
        
        slowed_dur = get_duration(slowed)
        
        if slowed_dur and slowed_dur < audio_duration:
            gap = audio_duration - slowed_dur
            extended = video_path.replace('.mp4', '_ext.mp4')
            
            print(f"Extending video by {gap:.1f}s...")
            subprocess.run(
                ['ffmpeg', '-y', '-i', slowed, '-f', 'lavfi', '-i',
                 f'color=c=black:s=640x360:r=25:d={gap}',
                 '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[outv]',
                 '-map', '[outv]', '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                 extended],
                capture_output=True, check=True
            )
            temp_video = extended
            
            if os.path.exists(slowed):
                os.remove(slowed)
    
    print("Merging...")
    subprocess.run(
        ['ffmpeg', '-y', '-i', temp_video, '-i', audio_path,
         '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
         '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-ac', '2', output_path],
        capture_output=True, check=True
    )
    
    if temp_video != video_path and os.path.exists(temp_video):
        os.remove(temp_video)
    
    print(f"Output: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Merge video with audio track")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument("-s", "--speed", type=float, default=1.0,
                        help="Video speed factor (default: 1.0)")
    args = parser.parse_args()
    
    merge(args.video, args.audio, args.output, args.speed)

if __name__ == "__main__":
    main()
