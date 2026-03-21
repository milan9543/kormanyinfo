#!/usr/bin/env python3
"""Download Hungarian auto-generated subtitles from YouTube."""
import subprocess, sys, re, os

url = sys.argv[1]
video_id = re.search(r'v=([^&]+)', url).group(1)

subprocess.run([
    "yt-dlp",
    "--write-auto-sub",
    "--sub-lang", "hu",
    "--skip-download",
    "--sub-format", "srt",
    "-o", f"pipeline/tmp/{video_id}",
    url
], check=True)

srt_path = f"pipeline/tmp/{video_id}.hu.srt"
if not os.path.exists(srt_path):
    for f in os.listdir("pipeline/tmp"):
        if f.endswith(".srt"):
            srt_path = f"pipeline/tmp/{f}"
            break

print(f"Downloaded: {srt_path}")
