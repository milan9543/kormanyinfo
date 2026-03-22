#!/usr/bin/env python3
"""Process SRT with Claude API → structured JSON.

Usage: python pipeline/process_srt.py VIDEO_ID_YYYY-MM-DD.mp3.srt
"""
import anthropic, json, re, sys, os

client = anthropic.Anthropic()

if len(sys.argv) < 2:
    print("Usage: python pipeline/process_srt.py VIDEO_ID_YYYY-MM-DD.mp3.srt")
    sys.exit(1)

srt_path = sys.argv[1]

# Filename format: VIDEO_ID_YYYY-MM-DD.mp3.srt
basename = os.path.basename(srt_path)
match = re.match(r'^(.+)_(\d{4}-\d{2}-\d{2})\.', basename)
if not match:
    print(f"Filename must be VIDEO_ID_YYYY-MM-DD.*.srt, got: {basename}")
    sys.exit(1)

video_id = match.group(1)
date = match.group(2)
print(f"Video ID: {video_id}  Date: {date}")

with open(srt_path, "r", encoding="utf-8") as f:
    srt_text = f.read()


SYSTEM_PROMPT = """You are analyzing Hungarian government press conference (Kormányinfó)
auto-generated subtitles. Your job:

1. Identify speaker changes using timing gaps, >> markers, and context
2. For each reporter: extract name and outlet from self-introductions
3. Separate every distinct question and its answer
4. For opening statements: extract speaker, time range, summary, tags

For each Q&A pair provide:
- start_time, end_time (from subtitle timestamps) — start_time MUST be when the question begins, not the answer
- reporter name and outlet
- question (extremely short Hungarian summary, max ~15 words)
- answer (extremely short Hungarian summary, max ~20 words)
- tags (array of lowercase Hungarian topic keywords with hyphens)
- criticism_percent (0-100: how critical the question is of the government)
- hostility_percent (0-100: how hostile/dismissive the minister's reply is)

Return ONLY valid JSON. No markdown fences. Schema:
{
  "speakers": [{"id": "s_01", "name": "...", "role": "miniszter|szóvivő", "position": "..."}],
  "opening_statements": [{"speaker_id": "s_01", "start_time": "...", "end_time": "...", "summary": "...", "tags": [...]}],
  "questions": [{"id": "q_01", "start_time": "...", "end_time": "...", "reporter": "...", "outlet": "...",
                  "question": "...", "answer": "...", "tags": [...],
                  "criticism_percent": N, "hostility_percent": N}]
}

RULES:
- Questions and answers must be EXTREMELY short — summaries, not transcriptions
- Tags: lowercase, hyphens, Hungarian (e.g. "druzsba-vezeték", "eu-csúcs"). Don't overuse tags, only the most important ones, and try to generalize so that tags are really useful.
- The >> marker often indicates a speaker change
- Number question IDs sequentially: q_01, q_02, ...
- Number speaker IDs sequentially: s_01, s_02, ... and use them consistently in opening_statements
"""

print("Processing...")

with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=64000,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": f"Process this subtitle file:\n\n{srt_text}"}]
) as stream:
    text = stream.get_final_text()

raw_dir = "src/data/responses"
os.makedirs(raw_dir, exist_ok=True)
raw_path = f"{raw_dir}/{date}.txt"
with open(raw_path, "w", encoding="utf-8") as f:
    f.write(text)
print(f"Raw response saved → {raw_path}")

text = re.sub(r'^```json\s*', '', text)
text = re.sub(r'\s*```\s*$', '', text)
result = json.loads(text)

output = {
    "meta": {
        "title": "Kormányinfó",
        "date": date,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "youtube_video_id": video_id,
        "duration": "",
        "location": "Budapest"
    },
    "speakers": result.get("speakers", []),
    "opening_statements": result.get("opening_statements", []),
    "questions": result.get("questions", [])
}

output_path = f"src/data/conferences/{date}.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Done: {len(output['questions'])} questions → {output_path}")
