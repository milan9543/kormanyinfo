# Hangnem

A static website tracking Hungarian government press conferences: who asked what, from which outlet, and how critical/hostile each exchange was.

## How it works

```
You run run_pipeline.sh with a YouTube URL and date
  → yt-dlp downloads the audio as mp3
    → whisper.cpp transcribes it to SRT
      → Claude API parses the SRT into structured JSON
        → Astro builds a static site from the JSON
          → Cloudflare Pages deploys on git push
```

No backend. No database. Everything is static files.

## Adding a new conference

```bash
export ANTHROPIC_API_KEY=sk-ant-...
./pipeline/run_pipeline.sh "https://www.youtube.com/watch?v=VIDEO_ID" "YYYY-MM-DD"
```

The script runs all steps end-to-end and pushes to `main` when done.

## Prerequisites

| Requirement         | Notes                                                                                        |
| ------------------- | -------------------------------------------------------------------------------------------- |
| Python 3            | `pip install -r pipeline/requirements.txt`                                                   |
| yt-dlp              | `brew install yt-dlp`                                                                        |
| whisper.cpp         | Built at `/Users/milanhorvath/code/fundev/whisper.cpp` with `models/ggml-large-v3-turbo.bin` |
| `ANTHROPIC_API_KEY` | Export in your shell before running                                                          |

## Pipeline steps

| Step | Script               | What it does                                                               |
| ---- | -------------------- | -------------------------------------------------------------------------- |
| 1    | `run_pipeline.sh`    | Downloads mp3 via yt-dlp                                                   |
| 2    | `run_pipeline.sh`    | Transcribes mp3 → SRT via whisper.cpp                                      |
| 3    | `process_srt.py`     | Claude API: SRT → structured conference JSON                               |
| 4    | `update_entities.py` | Claude API: merges any new reporters/outlets into `base_data/outlets.json` |
| 5    | `build_stats.py`     | Rebuilds aggregated `outlets_stats.json` + `reporters.json`                |
| 6    | `run_pipeline.sh`    | Commits and pushes — triggers Cloudflare Pages deploy                      |

Steps 1–2 are skipped automatically if the output file already exists, so you can re-run safely after a failure.

## Project structure

```
kormanyinfo/
├── pipeline/
│   ├── run_pipeline.sh        # Entry point: run this to process a new conference
│   ├── process_srt.py         # Claude API: SRT → structured JSON
│   ├── update_entities.py     # Claude API: merge new reporters/outlets
│   ├── build_stats.py         # Rebuild outlets_stats.json + reporters.json
│   ├── check_new_entities.py  # Diagnostic: list unknown reporters/outlets
│   ├── tmp/                   # Temporary mp3 + srt files (git-ignored)
│   └── requirements.txt
├── src/
│   ├── data/
│   │   ├── base_data/
│   │   │   ├── outlets.json        # Canonical outlet + reporter registry
│   │   │   └── outlet_colors.json  # Brand colors per outlet
│   │   ├── conferences/            # One JSON file per press conference
│   │   └── generated/              # Built by build_stats.py (git-ignored)
│   ├── components/
│   ├── layouts/
│   ├── pages/
│   └── lib/
└── public/
```

## Local development

```bash
npm install
npm run dev
```

## Setup

### Cloudflare Pages

Connect the GitHub repo in the Cloudflare dashboard:

- Build command: `npm run build`
- Output directory: `dist`

Every push to `main` triggers an automatic deploy.

## Cost

| Service          | Cost                  |
| ---------------- | --------------------- |
| Cloudflare Pages | Free                  |
| Claude API       | ~$0.5 per conference  |
| Custom domain    | ~$7.5/year (optional) |
