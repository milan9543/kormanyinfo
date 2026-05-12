#!/usr/bin/env python3
"""Process minister candidate interview SRT with Claude API → structured JSON.

Usage: python pipeline/process_srt_minister.py VIDEO_ID_YYYY-MM-DD_CANDIDATE_NAME.mp3.srt
"""
import anthropic, json, re, sys, os

client = anthropic.Anthropic()

if len(sys.argv) < 2:
    print("Usage: python pipeline/process_srt_minister.py VIDEO_ID_YYYY-MM-DD_CANDIDATE_NAME.mp3.srt")
    sys.exit(1)

srt_path = sys.argv[1]

basename = os.path.basename(srt_path)
# e.g. AbCdEfG_2026-03-12_Kovacs_Peter.mp3.srt
match = re.match(r'^(.+?)_(\d{4}-\d{2}-\d{2})_(.+?)\.', basename)
if not match:
    print(f"Filename must be VIDEO_ID_YYYY-MM-DD_CANDIDATE_NAME.*.srt, got: {basename}")
    sys.exit(1)

video_id = match.group(1)
date = match.group(2)
candidate_slug = match.group(3).lower().replace("_", "-")
print(f"Video ID: {video_id}  Date: {date}  Candidate slug: {candidate_slug}")

with open(srt_path, "r", encoding="utf-8") as f:
    srt_text = f.read()

SYSTEM_PROMPT = """You are analyzing auto-generated subtitles from a Hungarian parliamentary minister candidate hearing (miniszterjelölti meghallgatás).

The format is:
1. The candidate delivers an opening qualifications speech (expozé)
2. Committee members each ask their questions in a single batch (all questions first)
3. The candidate then answers all questions

Your tasks:

1. EXPOSÉ: Extract the candidate's qualifications speech as well-structured markdown.
   - Use ## headings to separate logical sections (e.g. Szakmai háttér, Korábbi tapasztalatok, Tervek és célkitűzések, Prioritások, etc.)
   - Write in flowing, readable Hungarian prose — not bullet points unless the candidate listed items
   - Capture the substance of what was said, not a verbatim transcript

2. COMMITTEE MEMBERS: Identify each committee member from their self-introductions (name, party/fraction, role if stated)

3. Q&A PAIRS: For each question asked by a committee member:
   - question_start_time — when the committee member begins speaking (HH:MM:SS)
   - answer_start_time — when the candidate begins their answer to this question (HH:MM:SS)
   - end_time — when the answer to this question ends (HH:MM:SS)
   - questioner name and party
   - question: extremely short Hungarian summary (~15 words max)
   - answer: extremely short Hungarian summary (~20 words max)

   Note: Questions are batched (all committee members ask, then the candidate answers all). Match each question to the corresponding part of the candidate's answer by topic.

Return ONLY valid JSON. No markdown fences. Schema:
{
  "candidate": "Full Name",
  "position": "Proposed ministry/position",
  "expose": {
    "start_time": "HH:MM:SS",
    "end_time": "HH:MM:SS",
    "content_markdown": "## Szakmai háttér\\n\\n..."
  },
  "committee_members": [{"id": "c_01", "name": "...", "party": "...", "role": "..."}],
  "questions": [{
    "id": "q_01",
    "question_start_time": "HH:MM:SS",
    "answer_start_time": "HH:MM:SS",
    "end_time": "HH:MM:SS",
    "questioner": "...",
    "party": "...",
    "question": "...",
    "answer": "..."
  }]
}

RULES:
- All text (summaries, markdown content) must be in Hungarian
- Question and answer summaries must be EXTREMELY short — summaries, not transcriptions
- The >> marker often indicates a speaker change
- Number question IDs sequentially: q_01, q_02, ...
- Number committee member IDs sequentially: c_01, c_02, ...
- If a committee member asks multiple questions, create separate Q&A entries for each
- The candidate's name and proposed position should be inferred from context (introductions, committee chairman's words)
- CRITICAL: All string values in the JSON must have double-quote characters escaped as \\". Never output a raw unescaped " inside a string value — it will break JSON parsing
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
raw_path = f"{raw_dir}/minister_{date}_{candidate_slug}.txt"
with open(raw_path, "w", encoding="utf-8") as f:
    f.write(text)
print(f"Raw response saved → {raw_path}")

text = re.sub(r'^```json\s*', '', text)
text = re.sub(r'\s*```\s*$', '', text)
result = json.loads(text)

candidate_name = result.get("candidate", candidate_slug.replace("-", " ").title())

output = {
    "meta": {
        "type": "minister_interview",
        "title": f"{candidate_name} miniszterjelölti meghallgatása",
        "date": date,
        "candidate": candidate_name,
        "position": result.get("position", ""),
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "youtube_video_id": video_id,
        "duration": "",
        "location": ""
    },
    "expose": result.get("expose", {}),
    "committee_members": result.get("committee_members", []),
    "questions": result.get("questions", [])
}

output_path = f"src/data/minister_interviews/{date}_{candidate_slug}.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Done: {len(output['questions'])} questions → {output_path}")
