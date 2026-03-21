# Kormányinfó Tracker

A static website tracking Hungarian government press conferences: who asked what, from which outlet, and how critical/hostile each exchange was.

## How it works

```
You trigger a GitHub Actions workflow with a YouTube URL
  → yt-dlp downloads Hungarian subtitles
    → Claude API parses them into structured JSON
      → Astro builds a static site from the JSON
        → Cloudflare Pages deploys it automatically
```

No backend. No database. Everything is static files.

## Project structure

```
kormanyinfo/
├── .github/workflows/
│   └── process-new.yml       # Manual trigger: URL → JSON → push → deploy
├── pipeline/
│   ├── download_srt.py        # Downloads .srt via yt-dlp
│   ├── process_srt.py         # Claude API: SRT → structured JSON
│   ├── build_stats.py         # Rebuilds outlets.json + reporters.json
│   └── requirements.txt
├── src/
│   ├── data/
│   │   ├── conferences/       # One JSON file per press conference
│   │   ├── outlets.json       # Aggregated outlet stats
│   │   └── reporters.json     # Aggregated reporter stats
│   ├── components/
│   ├── layouts/
│   ├── pages/
│   └── lib/
└── public/
```

## Adding a new conference

1. Go to the GitHub repo → **Actions** → **Process new Kormányinfó**
2. Click **Run workflow**
3. Paste the YouTube URL and the date (`YYYY-MM-DD`)
4. Wait ~3–5 minutes — the site updates automatically

## Local development

```bash
npm install
npm run dev
```

To run the pipeline locally:

```bash
pip install -r pipeline/requirements.txt
python pipeline/download_srt.py "https://youtube.com/watch?v=..."
ANTHROPIC_API_KEY=... python pipeline/process_srt.py "2025-03-20"
python pipeline/build_stats.py
```

## Setup

### GitHub Secrets required

| Secret | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API for SRT processing |

### Cloudflare Pages

Connect the GitHub repo in the Cloudflare dashboard:
- Build command: `npm run build`
- Output directory: `dist`

After that, every push to `main` auto-deploys.

## Cost

| Service | Cost |
|---|---|
| GitHub Actions | Free (~5 min per conference) |
| Cloudflare Pages | Free |
| Claude API | ~$1–2 per conference |
| Custom domain | ~$10/year (optional) |
