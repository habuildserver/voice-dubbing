#!/usr/bin/env python3
"""
Standalone Video Downloader

Downloads videos from YouTube and other platforms using yt-dlp.

Usage:
    python tools/download.py "https://youtube.com/watch?v=..."
    python tools/download.py "https://youtube.com/watch?v=..." -o ./videos/
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yt_dlp

def list_formats():
    """Show available formats/qualities."""
    print("\nCommon Format Options:")
    print("-" * 40)
    print("  best       - Best available quality")
    print("  best[ext=mp4] - Best MP4 quality")
    print("  1080p      - Full HD (add 'best' prefix)")
    print("  720p       - HD")
    print("  480p       - SD")
    print()

def download(url: str, output_dir: str = "./data/inputs",
             format_spec: str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
             info_only: bool = False):
    """
    Download video from URL.
    
    Args:
        url: Video URL
        output_dir: Output directory
        format_spec: yt-dlp format specification
        info_only: Only show info, don't download
    """
    os.makedirs(output_dir, exist_ok=True)
    
    ydl_opts = {
        'format': format_spec,
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': False,
    }
    
    if info_only:
        ydl_opts['skip_download'] = True
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if info_only:
                info = ydl.extract_info(url, download=False)
                print_video_info(info)
            else:
                info = ydl.extract_info(url, download=True)
                video_path = ydl.prepare_filename(info)
                print(f"\nDownloaded: {video_path}")
                return video_path
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def print_video_info(info):
    """Print video information."""
    print("\n" + "="*50)
    print("VIDEO INFO:")
    print("="*50)
    print(f"Title: {info.get('title', 'Unknown')}")
    print(f"Duration: {info.get('duration', 0)}s ({int(info.get('duration', 0)//60)}:{int(info.get('duration', 0)%60):02d})")
    print(f"Uploader: {info.get('uploader', 'Unknown')}")
    print(f"View count: {info.get('view_count', 'Unknown')}")
    print(f"Upload date: {info.get('upload_date', 'Unknown')}")
    
    formats = info.get('formats', [])
    print(f"\nAvailable formats: {len(formats)}")
    
    quality_set = set()
    for f in formats:
        height = f.get('height')
        if height:
            quality_set.add(f"{height}p")
    
    print(f"Qualities: {', '.join(sorted(quality_set, reverse=True))}")

def main():
    parser = argparse.ArgumentParser(description="Download videos from YouTube")
    parser.add_argument("url", help="Video URL")
    parser.add_argument("-o", "--output", default="./data/inputs", help="Output directory")
    parser.add_argument("-f", "--format", default=None, help="Format specification (default: best MP4)")
    parser.add_argument("-i", "--info", action="store_true", help="Show video info only, don't download")
    parser.add_argument("--list-formats", action="store_true", help="Show format options")
    args = parser.parse_args()
    
    if args.list_formats:
        list_formats()
        return
    
    format_spec = args.format or "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    
    download(args.url, args.output, format_spec, args.info)

if __name__ == "__main__":
    main()
