# Kormányinfó

A static website that tracks Hungarian government press conferences (Kormányinfó): who asked what, from which outlet, how critical the question was, and how hostile the minister's reply was.

## Tech Stack

- **Frontend:** Astro (fully static output), Tailwind CSS
- **Hosting:** Cloudflare Pages (auto-deploys on push to `main`)
- **Pipeline:** Python (yt-dlp + Claude API) running in GitHub Actions
- **Key constraint:** No backend, no database — everything is static JSON files built at deploy time

## JSON Schema

Conference file (`src/data/conferences/YYYY-MM-DD.json`):

```json
{
  "meta": { "title", "date", "youtube_url", "youtube_video_id", "duration", "location" },
  "speakers": [{ "name", "role", "position" }],
  "opening_statements": [{ "speaker", "start_time", "end_time", "summary", "tags" }],
  "questions": [{
    "id", "start_time", "end_time",
    "reporter", "outlet", "tags",
    "question", "answer",
    "criticism_percent", "hostility_percent"
  }]
}
```

Aggregated files (rebuilt by `pipeline/build_stats.py` after each new conference):

- `src/data/outlets.json` — `[{ name, total_questions, avg_criticism, avg_hostility, conferences_attended }]`
- `src/data/reporters.json` — `[{ name, outlet, total_questions, avg_criticism, avg_hostility, conferences_attended }]`

---

# Progress Tracker

## Phase 0: Scaffold

- [x] Create GitHub repo
- [x] `npm create astro@latest` with Tailwind
- [x] Create directory structure (`src/data/conferences/`, `pipeline/`)
- [x] Add `pipeline/requirements.txt`
- [x] Copy existing `kormanyinfo_qa.json` as `src/data/conferences/2025-03-20.json`
- [ ] Run `build_stats.py` locally to generate `outlets.json` + `reporters.json`
- [ ] Verify Astro dev server loads the data

## Phase 1: Core pages

- [ ] Home page — list conferences by date with basic stats
- [ ] Conference detail page — opening statements + Q&A cards
- [ ] Q&A cards with criticism/hostility meters
- [ ] Tag filtering (client-side JS island)
- [ ] YouTube timestamp links (`youtube_url + ?t=seconds`)
- [ ] Basic responsive layout

## Phase 2: Analytics pages

- [ ] Outlets index — ranked by avg criticism, bar chart
- [ ] Outlet detail — all questions from that outlet across conferences
- [ ] Reporters index — ranked by avg criticism
- [ ] Reporter detail — all questions by that reporter

## Phase 3: Pipeline

- [ ] Write `download_srt.py`
- [ ] Write `process_srt.py`
- [ ] Write `build_stats.py`
- [ ] Test locally end-to-end with a new conference
- [ ] Create GitHub Actions workflow
- [ ] Add `ANTHROPIC_API_KEY` to GitHub Secrets
- [ ] Test: trigger workflow → verify auto-deploy

## Phase 4: Deploy

- [ ] Connect repo to Cloudflare Pages
- [ ] Verify auto-deploy on push
- [ ] Optional: custom domain

## Phase 5: Polish

- [ ] Search across all Q&A (client-side)
- [ ] Dark mode
- [ ] SEO meta tags + OG images
- [ ] Conference comparison view
- [ ] Trend charts (outlet criticism over time)
- [ ] RSS feed for new conferences
