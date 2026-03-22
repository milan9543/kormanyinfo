#!/usr/bin/env python3
"""Process SRT with OpenAI API → structured JSON using Structured Outputs.

Usage: python pipeline/process_srt_openai.py 2025-03-12 src/data/raw_srt/2025-03-12.srt
Requires: OPENAI_API_KEY environment variable
"""
import openai, json, sys, os, glob

date = sys.argv[1]
client = openai.OpenAI()

if len(sys.argv) >= 3:
    srt_path = sys.argv[2]
else:
    srt_files = glob.glob("pipeline/tmp/*.srt")
    if not srt_files:
        print("No SRT file found in pipeline/tmp/")
        sys.exit(1)
    srt_path = srt_files[0]

video_id = os.path.basename(srt_path).split(".")[0]

with open(srt_path, "r", encoding="utf-8") as f:
    srt_text = f.read()


# ---------------------------------------------------------------------------
# Schema definition for OpenAI Structured Outputs
# strict: true requires additionalProperties: false at every object level
# ---------------------------------------------------------------------------

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "kormanyinfo_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "speakers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":       {"type": "string", "description": "Sequential ID: s_01, s_02, ..."},
                            "name":     {"type": "string", "description": "Full name of the speaker"},
                            "role":     {"type": "string", "description": "miniszter, szóvivő, or other role"},
                            "position": {"type": "string", "description": "Official title/position, empty string if unknown"}
                        },
                        "required": ["id", "name", "role", "position"],
                        "additionalProperties": False
                    }
                },
                "opening_statements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "speaker_id":  {"type": "string", "description": "Reference to speaker ID (s_01, s_02)"},
                            "start_time":  {"type": "string", "description": "HH:MM:SS or MM:SS format"},
                            "end_time":    {"type": "string", "description": "HH:MM:SS or MM:SS format"},
                            "summary":     {"type": "string", "description": "Short Hungarian summary of the statement"},
                            "tags":        {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Lowercase Hungarian topic keywords with hyphens"
                            }
                        },
                        "required": ["speaker_id", "start_time", "end_time", "summary", "tags"],
                        "additionalProperties": False
                    }
                },
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":                  {"type": "string", "description": "Sequential ID: q_01, q_02, ..."},
                            "start_time":          {"type": "string", "description": "Timestamp when the QUESTION begins"},
                            "end_time":            {"type": "string", "description": "Timestamp when the answer ends"},
                            "reporter":            {"type": "string", "description": "Reporter's full name"},
                            "outlet":              {"type": "string", "description": "News outlet name"},
                            "question":            {"type": "string", "description": "Extremely short Hungarian summary of the question, max ~15 words"},
                            "answer":              {"type": "string", "description": "Extremely short Hungarian summary of the answer, max ~20 words"},
                            "tags":                {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Lowercase Hungarian topic keywords with hyphens, only the most important ones"
                            },
                            "criticism_percent":   {"type": "integer", "description": "0-100: how critical the question is of the government"},
                            "hostility_percent":   {"type": "integer", "description": "0-100: how hostile/dismissive the minister's reply is"}
                        },
                        "required": [
                            "id", "start_time", "end_time", "reporter", "outlet",
                            "question", "answer", "tags",
                            "criticism_percent", "hostility_percent"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["speakers", "opening_statements", "questions"],
            "additionalProperties": False
        }
    }
}


# ---------------------------------------------------------------------------
# Prompt & processing
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are analyzing Hungarian government press conference (Kormányinfó)
auto-generated subtitles. Your job:

1. Identify speaker changes using timing gaps, >> markers, and context
2. For each reporter: extract name and outlet from self-introductions
3. Separate every distinct question and its answer
4. For opening statements: extract speaker, time range, summary, tags

RULES:
- Questions and answers must be EXTREMELY short — summaries, not transcriptions
- start_time for questions MUST be when the question begins, not the answer
- Tags: lowercase, hyphens, Hungarian (e.g. "druzsba-vezeték", "eu-csúcs"). Don't overuse tags, only the most important ones, generalize so tags are useful across events.
- The >> marker often indicates a speaker change
- The moderator says "Köszönjük szépen. [Outlet]." before each new reporter
- Number question IDs sequentially: q_01, q_02, ...
- Number speaker IDs sequentially: s_01, s_02, ...
- criticism_percent: 0 = neutral factual question, 100 = maximally critical of government
- hostility_percent: 0 = friendly/neutral reply, 100 = maximally hostile/dismissive reply
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

print("Processing with structured output schema...")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Process this subtitle file:\n\n{srt_text}"}
    ],
    response_format=RESPONSE_SCHEMA,
)

raw = response.choices[0].message.content

raw_dir = "pipeline/responses"
os.makedirs(raw_dir, exist_ok=True)
raw_path = f"{raw_dir}/{date}_openai.txt"
with open(raw_path, "w", encoding="utf-8") as f:
    f.write(raw)
print(f"Raw response saved → {raw_path}")

if response.choices[0].message.refusal:
    print(f"Model refused: {response.choices[0].message.refusal}")
    sys.exit(1)

result = json.loads(raw)

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

print(f"Done: {len(result.get('speakers', []))} speakers, "
      f"{len(result.get('opening_statements', []))} statements, "
      f"{len(result.get('questions', []))} questions → {output_path}")

import shutil
shutil.rmtree("pipeline/tmp", ignore_errors=True)