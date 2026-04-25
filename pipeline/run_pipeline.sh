#!/usr/bin/env bash
# Full local pipeline: YouTube URL → mp3 → whisper SRT → Claude JSON → stats → git push
#
# Usage: ./pipeline/run_pipeline.sh "https://www.youtube.com/watch?v=VIDEO_ID" "YYYY-MM-DD"
#
# Prerequisites:
#   - yt-dlp in PATH
#   - whisper.cpp built at WHISPER_DIR below
#   - ANTHROPIC_API_KEY set in environment (or export it before running)
#   - Python deps: pip install -r pipeline/requirements.txt

set -euo pipefail

WHISPER_DIR="/Users/milanhorvath/code/fundev/whisper.cpp"
WHISPER_MODEL="models/ggml-large-v3-turbo.bin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

URL="${1:?Usage: $0 <youtube_url> <YYYY-MM-DD>}"
DATE="${2:?Usage: $0 <youtube_url> <YYYY-MM-DD>}"

# Validate date format
if ! [[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Error: date must be YYYY-MM-DD, got: $DATE"
    exit 1
fi

# Extract video ID from URL
VIDEO_ID=$(echo "$URL" | grep -oE '[?&]v=([^&]+)' | grep -oE '[^=]+$')
if [[ -z "$VIDEO_ID" ]]; then
    echo "Error: could not extract video ID from URL: $URL"
    exit 1
fi

echo "================================================"
echo "  Video ID : $VIDEO_ID"
echo "  Date     : $DATE"
echo "================================================"

TMP_DIR="${SCRIPT_DIR}/tmp"
mkdir -p "$TMP_DIR"

MP3_PATH="${TMP_DIR}/${VIDEO_ID}_${DATE}.mp3"
SRT_PATH="${MP3_PATH}.srt"

cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Step 1: Download mp3
# ---------------------------------------------------------------------------
if [[ -f "$MP3_PATH" ]]; then
    echo ""
    echo "=== Step 1: mp3 already exists, skipping download ==="
else
    echo ""
    echo "=== Step 1: Downloading mp3 ==="
    yt-dlp -x --audio-format mp3 \
        -o "${TMP_DIR}/${VIDEO_ID}_${DATE}.%(ext)s" \
        "$URL"
fi

# ---------------------------------------------------------------------------
# Step 2: Whisper transcription → SRT
# ---------------------------------------------------------------------------
if [[ -f "$SRT_PATH" ]]; then
    echo ""
    echo "=== Step 2: SRT already exists, skipping whisper ==="
else
    echo ""
    echo "=== Step 2: Running whisper.cpp ==="
    cd "$WHISPER_DIR"
    ./build/bin/whisper-cli \
        -m "$WHISPER_MODEL" \
        -f "$MP3_PATH" \
        -l hu -osrt --max-len 100 --temperature 0
    cd "$REPO_ROOT"
fi

# ---------------------------------------------------------------------------
# Step 3: Process SRT → conference JSON via Claude
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 3: Processing SRT → conference JSON ==="
python pipeline/process_srt_generic.py "$SRT_PATH"

# ---------------------------------------------------------------------------
# Step 4: Merge any new reporters/outlets into base_data/outlets.json
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 4: Updating entities ==="
python pipeline/update_entities.py "src/data/conferences/${DATE}.json"

# ---------------------------------------------------------------------------
# Step 5: Rebuild aggregated stats
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 5: Rebuilding stats ==="
python pipeline/build_stats.py

# ---------------------------------------------------------------------------
# Step 6: Commit and push
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 6: Committing and pushing ==="
git add src/data/
git commit -m "Add conference ${DATE} (${VIDEO_ID})"
git push

echo ""
echo "================================================"
echo "  Done! Conference ${DATE} is live."
echo "================================================"
