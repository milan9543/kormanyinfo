# Kormányinfó Tracker — Implementation Plan

## Architecture

```
You (or cron)
    │
    │  Trigger: paste YouTube URL
    ▼
┌──────────────────────────────────────────────────────┐
│                   GitHub Actions                      │
│                                                      │
│  ┌─────────┐    ┌───────────┐    ┌────────────────┐  │
│  │ yt-dlp  │───▶│ Claude    │───▶│ git commit     │  │
│  │ get SRT │    │ API       │    │ JSON to repo   │  │
│  └─────────┘    │ parse &   │    └───────┬────────┘  │
│                 │ structure │            │           │
│                 └───────────┘            ▼           │
│                              ┌────────────────────┐  │
│                              │ Astro build        │  │
│                              │ static HTML + CSS  │  │
│                              └───────┬────────────┘  │
│                                      │               │
│                              ┌───────▼────────────┐  │
│                              │ Deploy to          │  │
│                              │ Cloudflare Pages   │  │
│                              └────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

**Everything happens in GitHub Actions. You just provide a YouTube URL.**

---

## File Structure

```
kormanyinfo/
├── .github/
│   └── workflows/
│       ├── process-new.yml          # Triggered manually: download → process → commit
│       └── deploy.yml               # Triggered on push to main: build → deploy
│
├── pipeline/
│   ├── download_srt.py              # Downloads .srt via yt-dlp
│   ├── process_srt.py               # Sends to Claude API, outputs structured JSON
│   ├── build_stats.py               # Rebuilds outlets.json + reporters.json from all conferences
│   └── requirements.txt             # yt-dlp, anthropic
│
├── src/
│   ├── data/
│   │   ├── conferences/
│   │   │   ├── 2025-03-20.json      # One file per event
│   │   │   └── ...
│   │   ├── outlets.json             # Aggregated stats (rebuilt by pipeline)
│   │   └── reporters.json           # Aggregated stats (rebuilt by pipeline)
│   ├── layouts/
│   │   └── Base.astro
│   ├── components/
│   │   ├── QuestionCard.astro
│   │   ├── OutletChart.astro
│   │   ├── StatsBar.astro
│   │   └── TagFilter.astro
│   ├── pages/
│   │   ├── index.astro              # List of all press conferences
│   │   ├── conference/
│   │   │   └── [date].astro         # Single conference detail
│   │   ├── outlets/
│   │   │   ├── index.astro          # All outlets ranked
│   │   │   └── [name].astro         # Single outlet history
│   │   └── reporters/
│   │       ├── index.astro          # All reporters ranked
│   │       └── [name].astro         # Single reporter history
│   ├── lib/
│   │   ├── data.ts                  # Loads JSON, types, helpers
│   │   └── stats.ts                 # Compute averages at build time
│   └── styles/
│       └── global.css
│
├── public/
│   └── favicon.svg
├── astro.config.mjs
├── tailwind.config.mjs
├── tsconfig.json
├── package.json
└── README.md
```

---

## JSON Data Format

Each conference file (`src/data/conferences/2025-03-20.json`):

```jsonc
{
  "meta": {
    "title": "Kormányinfó",
    "date": "2025-03-20", // also the filename
    "youtube_url": "https://...",
    "youtube_video_id": "XXXXX",
    "duration": "01:51:00",
    "location": "Budapest",
  },
  "speakers": [
    {
      "name": "Gulyás Gergely",
      "role": "miniszter",
      "position": "Miniszterelnökséget vezető miniszter",
    },
    { "name": "Vitályos Eszter", "role": "szóvivő" },
  ],
  "opening_statements": [
    {
      "speaker": "Gulyás Gergely",
      "start_time": "00:00:01",
      "end_time": "00:07:59",
      "tags": ["eu-csúcs", "ukrajna", "druzsba-vezeték"],
      "summary": "...",
    },
  ],
  "questions": [
    {
      "id": "q_01",
      "start_time": "13:49",
      "end_time": "14:09",
      "reporter": "Csuhaj Ildikó",
      "outlet": "Közmedia",
      "tags": ["usa", "vance", "diplomácia"],
      "question": "Meg tudja erősíteni, hogy J.D. Vance Budapestre jöhet?",
      "answer": "Külföldi állami látogatásokról megfelelő időben tájékoztatunk.",
      "criticism_percent": 5,
      "hostility_percent": 0,
    },
    // ... all questions
  ],
}
```

Aggregated files are rebuilt by the pipeline from all conference files:

`src/data/outlets.json`:

```jsonc
[
  {
    "name": "Telex",
    "type": "független",
    "total_questions": 14,
    "avg_criticism": 53.9,
    "avg_hostility": 16.8,
    "conferences_attended": 1, // grows over time
  },
]
```

`src/data/reporters.json`:

```jsonc
[
  {
    "name": "Nyilas Gergely",
    "outlet": "Telex",
    "total_questions": 14,
    "avg_criticism": 53.9,
    "avg_hostility": 16.8,
    "conferences_attended": 1,
  },
]
```

---

## GitHub Actions Workflows

### Workflow 1: Process new conference

Triggered manually from GitHub UI. You paste a YouTube URL and date.

```yaml
# .github/workflows/process-new.yml
name: Process new Kormányinfó

on:
  workflow_dispatch:
    inputs:
      youtube_url:
        description: "YouTube video URL"
        required: true
        type: string
      date:
        description: "Conference date (YYYY-MM-DD)"
        required: true
        type: string

jobs:
  process:
    runs-on: ubuntu-latest
    permissions:
      contents: write # needed to push commits

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r pipeline/requirements.txt

      - name: Download subtitles
        run: python pipeline/download_srt.py "${{ inputs.youtube_url }}"

      - name: Process with Claude
        run: python pipeline/process_srt.py "${{ inputs.date }}"
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Rebuild aggregated stats
        run: python pipeline/build_stats.py

      - name: Commit and push
        run: |
          git config user.name "Kormányinfó Bot"
          git config user.email "bot@kormanyinfo.example"
          git add src/data/
          git commit -m "Add conference ${{ inputs.date }}"
          git push
```

When this pushes to `main`, the deploy workflow triggers automatically.

### Workflow 2: Build and deploy

Triggered on every push to `main`.

```yaml
# .github/workflows/deploy.yml
name: Build & Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install dependencies
        run: npm install

      - name: Build Astro
        run: npm run build

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          command: pages deploy dist --project-name=kormanyinfo
```

### Flow diagram

```
You click "Run workflow" in GitHub UI
  → paste YouTube URL + date
    → Actions: download SRT
      → Actions: Claude processes SRT → JSON
        → Actions: rebuild stats JSONs
          → Actions: git commit + push
            → (auto-triggers deploy workflow)
              → Actions: Astro builds static site
                → Actions: deploys to Cloudflare Pages
                  → Live at kormanyinfo.pages.dev
```

Total time: ~3-5 minutes. You do nothing after clicking the button.

---

## Pipeline Scripts

### pipeline/requirements.txt

```
yt-dlp
anthropic
```

### pipeline/download_srt.py

```python
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

# Find the output file (yt-dlp adds .hu.srt)
srt_path = f"pipeline/tmp/{video_id}.hu.srt"
if not os.path.exists(srt_path):
    # Try alternative naming
    for f in os.listdir("pipeline/tmp"):
        if f.endswith(".srt"):
            srt_path = f"pipeline/tmp/{f}"
            break

print(f"Downloaded: {srt_path}")
```

### pipeline/process_srt.py

````python
#!/usr/bin/env python3
"""Process SRT with Claude API → structured JSON."""
import anthropic, json, re, sys, os, glob

date = sys.argv[1]  # e.g. "2025-03-20"
client = anthropic.Anthropic()

# Find the SRT file
srt_files = glob.glob("pipeline/tmp/*.srt")
if not srt_files:
    print("No SRT file found!")
    sys.exit(1)

srt_path = srt_files[0]
video_id = os.path.basename(srt_path).split(".")[0]

with open(srt_path, "r", encoding="utf-8") as f:
    srt_text = f.read()

# Chunk the SRT into overlapping segments
def chunk_srt(text, chunk_size=120, overlap=15):
    blocks = re.split(r'\n\n+', text.strip())
    chunks = []
    for i in range(0, len(blocks), chunk_size - overlap):
        chunk = '\n\n'.join(blocks[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

SYSTEM_PROMPT = """You are analyzing Hungarian government press conference (Kormányinfó)
auto-generated subtitles. Your job:

1. Identify speaker changes using timing gaps, >> markers, and context
2. For each reporter: extract name and outlet from self-introductions
3. Separate every distinct question and its answer
4. For opening statements: extract speaker, time range, summary, tags

For each Q&A pair provide:
- start_time, end_time (from subtitle timestamps)
- reporter name and outlet
- question (extremely short Hungarian summary, max ~15 words)
- answer (extremely short Hungarian summary, max ~20 words)
- tags (array of lowercase Hungarian topic keywords with hyphens)
- criticism_percent (0-100: how critical the question is of the government)
- hostility_percent (0-100: how hostile/dismissive the minister's reply is)

Return ONLY valid JSON. No markdown fences. Schema:
{
  "speakers": [{"name": "...", "role": "miniszter|szóvivő", "position": "..."}],
  "opening_statements": [{"speaker": "...", "start_time": "...", "end_time": "...", "summary": "...", "tags": [...]}],
  "questions": [{"id": "q_01", "start_time": "...", "end_time": "...", "reporter": "...", "outlet": "...",
                  "question": "...", "answer": "...", "tags": [...],
                  "criticism_percent": N, "hostility_percent": N}]
}

RULES:
- Questions and answers must be EXTREMELY short — summaries, not transcriptions
- Tags: lowercase, hyphens, Hungarian (e.g. "druzsba-vezeték", "eu-csúcs"). Don't overuse tags, only the most important ones, and try to generalize so that tags are really useful.
- The >> marker often indicates a speaker change
- Be consistent with reporter names across chunks
- Number question IDs sequentially: q_01, q_02, ...
"""

def process_chunk(chunk, chunk_index, prev_context="", q_offset=0):
    context_msg = ""
    if prev_context:
        context_msg = f"\n\nPrevious chunk ended with:\n{prev_context}\nContinue question numbering from q_{q_offset+1:02d}.\n"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Process this subtitle chunk (chunk {chunk_index + 1}):{context_msg}\n\n{chunk}"
        }]
    )

    text = response.content[0].text
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)
    return json.loads(text)


def merge_chunks(results):
    merged = {
        "speakers": [],
        "opening_statements": [],
        "questions": []
    }
    seen_times = set()

    for r in results:
        for s in r.get("opening_statements", []):
            if s["start_time"] not in seen_times:
                merged["opening_statements"].append(s)
                seen_times.add(s["start_time"])

        for q in r.get("questions", []):
            if q["start_time"] not in seen_times:
                merged["questions"].append(q)
                seen_times.add(q["start_time"])

        if not merged["speakers"] and r.get("speakers"):
            merged["speakers"] = r["speakers"]

    # Renumber question IDs
    for i, q in enumerate(merged["questions"]):
        q["id"] = f"q_{i+1:02d}"

    return merged


# Process
chunks = chunk_srt(srt_text)
print(f"Processing {len(chunks)} chunks...")

results = []
prev_context = ""
q_count = 0

for i, chunk in enumerate(chunks):
    print(f"  Chunk {i+1}/{len(chunks)}...")
    result = process_chunk(chunk, i, prev_context, q_count)
    results.append(result)

    new_qs = result.get("questions", [])
    q_count += len(new_qs)
    if new_qs:
        prev_context = json.dumps(new_qs[-3:], ensure_ascii=False)

merged = merge_chunks(results)

# Build final output
output = {
    "meta": {
        "title": "Kormányinfó",
        "date": date,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "youtube_video_id": video_id,
        "duration": "",
        "location": "Budapest"
    },
    "speakers": merged["speakers"],
    "opening_statements": merged["opening_statements"],
    "questions": merged["questions"]
}

# Write to the data directory
output_path = f"src/data/conferences/{date}.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Done: {len(merged['questions'])} questions → {output_path}")

# Cleanup
import shutil
shutil.rmtree("pipeline/tmp", ignore_errors=True)
````

### pipeline/build_stats.py

```python
#!/usr/bin/env python3
"""Rebuild outlets.json and reporters.json from all conference files."""
import json, glob, os
from collections import defaultdict

conferences = sorted(glob.glob("src/data/conferences/*.json"))

outlet_data = defaultdict(lambda: {"questions": [], "conferences": set()})
reporter_data = defaultdict(lambda: {"outlet": "", "questions": [], "conferences": set()})

for conf_path in conferences:
    with open(conf_path, "r", encoding="utf-8") as f:
        conf = json.load(f)

    date = conf["meta"]["date"]

    for q in conf.get("questions", []):
        outlet = q.get("outlet", "Ismeretlen")
        reporter = q.get("reporter", "Ismeretlen")

        outlet_data[outlet]["questions"].append(q)
        outlet_data[outlet]["conferences"].add(date)

        reporter_data[reporter]["outlet"] = outlet
        reporter_data[reporter]["questions"].append(q)
        reporter_data[reporter]["conferences"].add(date)

# Build outlets.json
outlets = []
for name, data in sorted(outlet_data.items(), key=lambda x: -len(x[1]["questions"])):
    qs = data["questions"]
    outlets.append({
        "name": name,
        "total_questions": len(qs),
        "avg_criticism": round(sum(q["criticism_percent"] for q in qs) / len(qs), 1) if qs else 0,
        "avg_hostility": round(sum(q["hostility_percent"] for q in qs) / len(qs), 1) if qs else 0,
        "conferences_attended": len(data["conferences"])
    })

# Build reporters.json
reporters = []
for name, data in sorted(reporter_data.items(), key=lambda x: -len(x[1]["questions"])):
    qs = data["questions"]
    reporters.append({
        "name": name,
        "outlet": data["outlet"],
        "total_questions": len(qs),
        "avg_criticism": round(sum(q["criticism_percent"] for q in qs) / len(qs), 1) if qs else 0,
        "avg_hostility": round(sum(q["hostility_percent"] for q in qs) / len(qs), 1) if qs else 0,
        "conferences_attended": len(data["conferences"])
    })

os.makedirs("src/data", exist_ok=True)

with open("src/data/outlets.json", "w", encoding="utf-8") as f:
    json.dump(outlets, f, ensure_ascii=False, indent=2)

with open("src/data/reporters.json", "w", encoding="utf-8") as f:
    json.dump(reporters, f, ensure_ascii=False, indent=2)

print(f"Stats rebuilt: {len(outlets)} outlets, {len(reporters)} reporters from {len(conferences)} conferences")
```

---

## Astro Setup

### Initial setup

```bash
npm create astro@latest kormanyinfo -- --template minimal
cd kormanyinfo
npx astro add tailwind
```

### astro.config.mjs

```javascript
import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";

export default defineConfig({
  integrations: [tailwind()],
  output: "static", // fully static build
});
```

### Loading data (src/lib/data.ts)

```typescript
import type { Conference, OutletStats, ReporterStats } from "./types";

// Load all conferences at build time
const conferenceFiles = import.meta.glob("../data/conferences/*.json", {
  eager: true,
});

export function getAllConferences(): Conference[] {
  return Object.values(conferenceFiles)
    .map((mod: any) => mod.default)
    .sort((a, b) => b.meta.date.localeCompare(a.meta.date));
}

export function getConference(date: string): Conference | undefined {
  return getAllConferences().find((c) => c.meta.date === date);
}

// Outlets and reporters (pre-aggregated by pipeline)
import outletsData from "../data/outlets.json";
import reportersData from "../data/reporters.json";

export const outlets: OutletStats[] = outletsData;
export const reporters: ReporterStats[] = reportersData;
```

### Types (src/lib/types.ts)

```typescript
export interface Question {
  id: string;
  start_time: string;
  end_time: string;
  reporter: string;
  outlet: string;
  tags: string[];
  question: string;
  answer: string;
  criticism_percent: number;
  hostility_percent: number;
}

export interface OpeningStatement {
  speaker: string;
  start_time: string;
  end_time: string;
  tags: string[];
  summary: string;
}

export interface Speaker {
  name: string;
  role: string;
  position?: string;
}

export interface ConferenceMeta {
  title: string;
  date: string;
  youtube_url: string;
  youtube_video_id: string;
  duration: string;
  location: string;
}

export interface Conference {
  meta: ConferenceMeta;
  speakers: Speaker[];
  opening_statements: OpeningStatement[];
  questions: Question[];
}

export interface OutletStats {
  name: string;
  total_questions: number;
  avg_criticism: number;
  avg_hostility: number;
  conferences_attended: number;
}

export interface ReporterStats {
  name: string;
  outlet: string;
  total_questions: number;
  avg_criticism: number;
  avg_hostility: number;
  conferences_attended: number;
}
```

---

## Deployment: Cloudflare Pages

### One-time setup

1. Go to Cloudflare Dashboard → Pages
2. Connect your GitHub repo
3. Build settings:
   - Build command: `npm run build`
   - Output directory: `dist`
4. Save → first deploy happens automatically

After that, every `git push` to `main` auto-deploys. You don't even need the deploy workflow — Cloudflare Pages has native GitHub integration that does this for you.

**Simplified workflow (if using Cloudflare Pages GitHub integration):**

You only need ONE workflow file:

```yaml
# .github/workflows/process-new.yml
# Cloudflare Pages auto-deploys on push — no deploy step needed
name: Process new Kormányinfó

on:
  workflow_dispatch:
    inputs:
      youtube_url:
        description: "YouTube video URL"
        required: true
      date:
        description: "Conference date (YYYY-MM-DD)"
        required: true

jobs:
  process:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r pipeline/requirements.txt
      - run: python pipeline/download_srt.py "${{ inputs.youtube_url }}"
      - run: python pipeline/process_srt.py "${{ inputs.date }}"
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - run: python pipeline/build_stats.py
      - run: |
          git config user.name "Kormányinfó Bot"
          git config user.email "bot@kormanyinfo.example"
          git add src/data/
          git commit -m "Új kormányinfó: ${{ inputs.date }}"
          git push
    # ↑ push triggers Cloudflare Pages auto-deploy
```

---

## Progress Tracker

### Phase 0: Scaffold (30 min)

- [ ] Create GitHub repo
- [ ] `npm create astro@latest` with Tailwind
- [ ] Create directory structure (`src/data/conferences/`, `pipeline/`)
- [ ] Add `pipeline/requirements.txt`
- [ ] Copy existing `kormanyinfo_qa.json` as `src/data/conferences/2025-03-20.json`
- [ ] Run `build_stats.py` locally to generate `outlets.json` + `reporters.json`
- [ ] Verify Astro dev server loads the data

### Phase 1: Core pages (1-2 days)

- [ ] Home page — list conferences by date with basic stats
- [ ] Conference detail page — opening statements + Q&A cards
- [ ] Q&A cards with criticism/hostility meters (reuse the design we built)
- [ ] Tag filtering (client-side JS island)
- [ ] YouTube timestamp links (`youtube_url + ?t=seconds`)
- [ ] Basic responsive layout

### Phase 2: Analytics pages (1 day)

- [ ] Outlets index — ranked by avg criticism, bar chart
- [ ] Outlet detail — all questions from that outlet across conferences
- [ ] Reporters index — ranked by avg criticism
- [ ] Reporter detail — all questions by that reporter

### Phase 3: Pipeline (half day)

- [ ] Write `download_srt.py`
- [ ] Write `process_srt.py`
- [ ] Write `build_stats.py`
- [ ] Test locally end-to-end with a new conference
- [ ] Create GitHub Actions workflow
- [ ] Add `ANTHROPIC_API_KEY` to GitHub Secrets
- [ ] Test: trigger workflow → verify auto-deploy

### Phase 4: Deploy (30 min)

- [ ] Connect repo to Cloudflare Pages
- [ ] Verify auto-deploy on push
- [ ] Optional: custom domain

### Phase 5: Polish

- [ ] Search across all Q&A (client-side)
- [ ] Dark mode
- [ ] SEO meta tags + OG images
- [ ] Conference comparison view (how did coverage shift?)
- [ ] Trend charts (outlet criticism over time)
- [ ] RSS feed for new conferences

---

## Secrets needed

| Secret                            | Where               | Purpose                                               |
| --------------------------------- | ------------------- | ----------------------------------------------------- |
| `ANTHROPIC_API_KEY`               | GitHub repo secrets | Claude API for SRT processing                         |
| (optional) `CLOUDFLARE_API_TOKEN` | GitHub repo secrets | Only if NOT using Cloudflare Pages GitHub integration |

---

## Cost

| Service          | Cost                                            |
| ---------------- | ----------------------------------------------- |
| GitHub repo      | Free                                            |
| GitHub Actions   | Free (2000 min/month, you use ~5 min per event) |
| Cloudflare Pages | Free (unlimited sites, unlimited bandwidth)     |
| Claude API       | ~$1-2 per conference (~30k tokens processed)    |
| Custom domain    | ~$10/year (optional)                            |
| **Total**        | **~$4-8/month**                                 |

---

## When to upgrade

Stay with this static approach **until** any of these become true:

| Trigger                                              | Solution                                               |
| ---------------------------------------------------- | ------------------------------------------------------ |
| Need full-text search across 100+ events             | Add Pagefind (static search, no backend needed)        |
| Need user accounts / admin panel                     | Add Cloudflare D1 + Hono API                           |
| Need real-time updates during live press conferences | Add a Worker with WebSocket                            |
| Need collaborative editing / corrections             | Add a CMS (Decap CMS works with static Git repos)      |
| Need the data as an API for others                   | Add Cloudflare Worker as API layer over the JSON files |

The beautiful thing: your JSON data format stays the same regardless. The frontend reads the same files whether they come from Git or an API.
