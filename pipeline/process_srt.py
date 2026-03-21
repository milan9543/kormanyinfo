#!/usr/bin/env python3
"""Process SRT with Claude API → structured JSON."""
import anthropic, json, re, sys, os, glob

date = sys.argv[1]  # e.g. "2025-03-20"
client = anthropic.Anthropic()

srt_files = glob.glob("pipeline/tmp/*.srt")
if not srt_files:
    print("No SRT file found!")
    sys.exit(1)

srt_path = srt_files[0]
video_id = os.path.basename(srt_path).split(".")[0]

with open(srt_path, "r", encoding="utf-8") as f:
    srt_text = f.read()


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
    merged = {"speakers": [], "opening_statements": [], "questions": []}
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

    for i, q in enumerate(merged["questions"]):
        q["id"] = f"q_{i+1:02d}"

    return merged


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

output_path = f"src/data/conferences/{date}.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Done: {len(merged['questions'])} questions → {output_path}")

import shutil
shutil.rmtree("pipeline/tmp", ignore_errors=True)
