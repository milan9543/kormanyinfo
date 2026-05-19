#!/usr/bin/env python3
"""Process SRT with Claude API → structured JSON.

Usage: python pipeline/process_srt_generic.py VIDEO_ID_YYYY-MM-DD.mp3.srt
"""
import anthropic, json, re, sys, os

client = anthropic.Anthropic()

if len(sys.argv) < 2:
    print("Usage: python pipeline/process_srt_generic.py VIDEO_ID_YYYY-MM-DD.mp3.srt")
    sys.exit(1)

srt_path = sys.argv[1]

basename = os.path.basename(srt_path)
match = re.match(r'^(.+)_(\d{4}-\d{2}-\d{2})(?:_part\d+)?\.', basename)
if not match:
    print(f"Filename must be VIDEO_ID_YYYY-MM-DD[_partN].*.srt, got: {basename}")
    sys.exit(1)

video_id = match.group(1)
date = match.group(2)
print(f"Video ID: {video_id}  Date: {date}")

with open(srt_path, "r", encoding="utf-8") as f:
    srt_text = f.read()

outlets_path = os.path.join(os.path.dirname(__file__), "../src/data/base_data/outlets.json")
with open(outlets_path, "r", encoding="utf-8") as f:
    outlets_data = f.read()

SYSTEM_PROMPT = f"""You are analyzing auto-generated subtitles from a Hungarian government press conference (Kormányinfó).
Your job:

1. Identify speaker changes using timing gaps, >> markers, and context
2. For each reporter: extract name and outlet from self-introductions
3. Separate every distinct question and its answer
4. For opening statements: extract speaker, time range, summary, tags
   - summary must be JSON-escaped markdown — short but detailed

KNOWN OUTLETS AND REPORTERS
The following JSON lists all known outlets and their regular reporters. Auto-generated subtitles
often mishear or misspell names — if a name in the subtitles is close to one in this list,
use the correct spelling from the list. Unknown reporters or outlets may appear; use whatever
the subtitles say as accurately as possible.

{outlets_data}

For each Q&A pair provide:
- question_start_time — when the reporter begins speaking (HH:MM:SS, no milliseconds)
- start_time — when the official begins their answer (HH:MM:SS, no milliseconds)
- end_time — when the answer ends (HH:MM:SS, no milliseconds)
- reporter name and outlet (use canonical spelling from the known list when possible)
- question (extremely short Hungarian summary, max ~15 words)
- answer (extremely short Hungarian summary, max ~20 words)
- tags (1–3 broad topic tags, see rules)
- criticism_percent (0-100: how critical the question is toward the government/officials — 0 = friendly/supportive, 100 = maximally adversarial)
- hostility_percent (0-100: how hostile or dismissive the official's reply is toward the reporter — 0 = respectful/cooperative, 100 = openly contemptuous)

Return ONLY valid JSON. No markdown fences. Schema:
{{
  "speakers": [{{"id": "s_01", "name": "...", "role": "...", "position": "..."}}],
  "opening_statements": [{{"speaker_id": "s_01", "start_time": "HH:MM:SS", "end_time": "HH:MM:SS", "summary": "markdown string with \\n escapes", "tags": [...]}}],
  "questions": [{{"id": "q_01", "question_start_time": "HH:MM:SS", "start_time": "HH:MM:SS", "end_time": "HH:MM:SS",
                  "reporter": "...", "outlet": "...",
                  "question": "...", "answer": "...", "tags": [...],
                  "criticism_percent": N, "hostility_percent": N}}]
}}

RULES:
- Opening statement summaries must be markdown. Keep it short but cover all major points. The string must be valid JSON (escape newlines as \\n, no literal line breaks).
- Questions and answers must be EXTREMELY short — summaries, not transcriptions
- All summaries and tags must be in Hungarian
- Tags: 1–3 per entry, lowercase, broad topic categories ONLY. Preferred tags:
  "gazdaság", "külpolitika", "belpolitika", "egészségügy", "oktatás", "energia",
  "migráció", "igazságszolgáltatás", "honvédelem", "környezet", "szociálpolitika",
  "média", "korrupció", "eu", "választás"
  Do NOT use specific names, event names, or narrow subtopics as tags.
- The >> marker often indicates a speaker change
- If a reporter asks multiple questions in one turn, split them into separate Q&A entries (each with the same reporter/outlet, each paired with the relevant part of the answer)
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
        "title": "",
        "date": date,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "youtube_video_id": video_id,
        "duration": "",
        "location": ""
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
