#!/usr/bin/env bash
# Full local pipeline for minister candidate hearings:
# YouTube URL → mp3 → whisper SRT → Claude JSON
#
# Usage: ./pipeline/run_pipeline_minister.sh <youtube_url> <YYYY-MM-DD> <"Firstname Lastname">
#
# Example:
#   ./pipeline/run_pipeline_minister.sh "https://www.youtube.com/watch?v=AbCdEfG" "2026-05-11" "Vitézy Dávid"
#
# Prerequisites:
#   - yt-dlp in PATH
#   - whisper.cpp built at WHISPER_DIR below
#   - ANTHROPIC_API_KEY set in environment
#   - Python deps: pip install -r pipeline/requirements.txt

set -euo pipefail

WHISPER_DIR="/Users/milanhorvath/code/fundev/whisper.cpp"
WHISPER_MODEL="models/ggml-large-v3-turbo.bin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

URL="${1:?Usage: $0 <youtube_url> <YYYY-MM-DD> <\"Candidate Name\">}"
DATE="${2:?Usage: $0 <youtube_url> <YYYY-MM-DD> <\"Candidate Name\">}"
CANDIDATE_NAME="${3:?Usage: $0 <youtube_url> <YYYY-MM-DD> <\"Candidate Name\">}"

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

# Build candidate slug: "Vitézy Dávid" → "Vitézy_Dávid" (spaces to underscores, for filename)
CANDIDATE_SLUG=$(echo "$CANDIDATE_NAME" | tr ' ' '_')

echo "================================================"
echo "  Video ID  : $VIDEO_ID"
echo "  Date      : $DATE"
echo "  Candidate : $CANDIDATE_NAME"
echo "================================================"

TMP_DIR="${SCRIPT_DIR}/tmp"
mkdir -p "$TMP_DIR"

MP3_PATH="${TMP_DIR}/${VIDEO_ID}_${DATE}_${CANDIDATE_SLUG}.mp3"
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
        -o "${TMP_DIR}/${VIDEO_ID}_${DATE}_${CANDIDATE_SLUG}.%(ext)s" \
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
# Step 3: Process SRT → minister interview JSON via Claude
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 3: Processing SRT → minister interview JSON ==="
python pipeline/process_srt_minister.py "$SRT_PATH"

echo ""
echo "================================================"
echo "  Done! Interview ${DATE} / ${CANDIDATE_NAME} processed."
echo "================================================"
