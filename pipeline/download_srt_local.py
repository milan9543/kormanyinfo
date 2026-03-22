#!/usr/bin/env python3
"""Download Hungarian auto-generated subtitles from YouTube (local use).

Uses cookies from your browser to bypass bot detection.
Usage: python pipeline/download_srt_local.py "https://www.youtube.com/watch?v=..."

Tries Chrome first, then Firefox.
"""
import subprocess, sys, re, os

url = sys.argv[1]
video_id = re.search(r'v=([^&]+)', url).group(1)

os.makedirs("pipeline/tmp", exist_ok=True)

for browser in ("chrome", "firefox", "safari"):
    result = subprocess.run([
        "yt-dlp",
        "--cookies-from-browser", browser,
        "--write-auto-sub",
        "--sub-lang", "hu",
        "--skip-download",
        "--sub-format", "srt",
        "-o", f"pipeline/tmp/{video_id}",
        url
    ])
    if result.returncode == 0:
        break
    print(f"[warn] {browser} cookies failed, trying next browser...")
else:
    print("Error: could not download with any browser cookies.")
    sys.exit(1)

srt_path = f"pipeline/tmp/{video_id}.hu.srt"
if not os.path.exists(srt_path):
    for f in os.listdir("pipeline/tmp"):
        if f.endswith(".srt"):
            srt_path = f"pipeline/tmp/{f}"
            break

print(f"Downloaded: {srt_path}")
