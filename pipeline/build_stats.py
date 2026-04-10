#!/usr/bin/env python3
"""Rebuild outlets_stats.json and reporters.json from all conference files."""
import json, glob, os
from collections import defaultdict


def parse_seconds(t):
    """Parse HH:MM:SS or MM:SS string to total seconds."""
    parts = t.strip().split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return parts[0] * 60 + parts[1]


def question_duration(q):
    try:
        return parse_seconds(q["end_time"]) - parse_seconds(q["start_time"])
    except (KeyError, ValueError):
        return 0


def annotate_effective_durations(questions):
    """Set _effective_duration on each question: next question's start_time minus
    current start_time. For the last question, fall back to end_time - start_time."""
    for i, q in enumerate(questions):
        if i + 1 < len(questions):
            try:
                q["_effective_duration"] = (
                    parse_seconds(questions[i + 1]["start_time"])
                    - parse_seconds(q["start_time"])
                )
            except (KeyError, ValueError):
                q["_effective_duration"] = question_duration(q)
        else:
            q["_effective_duration"] = question_duration(q)

# Load canonical outlet base data
with open("src/data/base_data/outlets.json", "r", encoding="utf-8") as f:
    base_outlets = json.load(f)

with open("src/data/base_data/outlet_colors.json", "r", encoding="utf-8") as f:
    outlet_colors = json.load(f)

DEFAULT_COLORS = {"color": "#6B7280", "text_color": "#ffffff"}

# Build outlet name/alias → outlet_id mapping
outlet_name_to_id = {}
for outlet in base_outlets:
    outlet_name_to_id[outlet["name"]] = outlet["id"]
    for alias in outlet.get("aliases", []):
        outlet_name_to_id[alias] = outlet["id"]

# Build (outlet_id, reporter_name/alias) → reporter_id mapping
reporter_name_to_id = {}
for outlet in base_outlets:
    for reporter in outlet["reporters"]:
        reporter_name_to_id[(outlet["id"], reporter["name"])] = reporter["id"]
        for alias in reporter.get("aliases", []):
            reporter_name_to_id[(outlet["id"], alias)] = reporter["id"]

conferences = sorted(glob.glob("src/data/conferences/*.json"))

outlet_stats = defaultdict(lambda: {"questions": [], "conferences": set()})
reporter_stats = defaultdict(lambda: {"questions": [], "conferences": set()})

for conf_path in conferences:
    with open(conf_path, "r", encoding="utf-8") as f:
        conf = json.load(f)

    date = conf["meta"]["date"]

    questions = conf.get("questions", [])
    annotate_effective_durations(questions)

    for q in questions:
        outlet_name = q.get("outlet", "ismeretlen")
        reporter_name = q.get("reporter", "ismeretlen")

        outlet_id = outlet_name_to_id.get(outlet_name, "ismeretlen")
        reporter_id = reporter_name_to_id.get((outlet_id, reporter_name))

        outlet_stats[outlet_id]["questions"].append(q)
        outlet_stats[outlet_id]["conferences"].add(date)

        if reporter_id:
            reporter_stats[(outlet_id, reporter_id)]["questions"].append(q)
            reporter_stats[(outlet_id, reporter_id)]["conferences"].add(date)

# Build outlets_stats.json (base structure extended with stats)
outlets_out = []
for outlet in base_outlets:
    oid = outlet["id"]
    qs = outlet_stats[oid]["questions"]
    confs = outlet_stats[oid]["conferences"]

    reporters_out = []
    for reporter in outlet["reporters"]:
        rid = reporter["id"]
        rqs = reporter_stats[(oid, rid)]["questions"]
        rconfs = reporter_stats[(oid, rid)]["conferences"]
        reporters_out.append({
            "id": rid,
            "name": reporter["name"],
            "total_questions": len(rqs),
            "avg_criticism": round(sum(q["criticism_percent"] for q in rqs) / len(rqs), 1) if rqs else 0,
            "avg_hostility": round(sum(q["hostility_percent"] for q in rqs) / len(rqs), 1) if rqs else 0,
            "conferences_attended": len(rconfs),
        })
    reporters_out.sort(key=lambda r: -r["total_questions"])

    outlets_out.append({
        "id": oid,
        "name": outlet["name"],
        "color": outlet_colors.get(oid, DEFAULT_COLORS)["color"],
        "text_color": outlet_colors.get(oid, DEFAULT_COLORS)["text_color"],
        "total_questions": len(qs),
        "avg_criticism": round(sum(q["criticism_percent"] for q in qs) / len(qs), 1) if qs else 0,
        "avg_hostility": round(sum(q["hostility_percent"] for q in qs) / len(qs), 1) if qs else 0,
        "conferences_attended": len(confs),
        "total_question_time_seconds": sum(q.get("_effective_duration", question_duration(q)) for q in qs),
        "reporters": reporters_out,
    })

outlets_out.sort(key=lambda o: -o["total_questions"])

os.makedirs("src/data/generated", exist_ok=True)

with open("src/data/generated/outlets_stats.json", "w", encoding="utf-8") as f:
    json.dump(outlets_out, f, ensure_ascii=False, indent=2)

# Also generate flat reporters.json
reporters_flat = []
for outlet_entry in outlets_out:
    for r in outlet_entry["reporters"]:
        reporters_flat.append({
            "id": r["id"],
            "name": r["name"],
            "outlet": outlet_entry["name"],
            "outlet_id": outlet_entry["id"],
            "total_questions": r["total_questions"],
            "avg_criticism": r["avg_criticism"],
            "avg_hostility": r["avg_hostility"],
            "conferences_attended": r["conferences_attended"],
        })
reporters_flat.sort(key=lambda r: -r["total_questions"])

with open("src/data/generated/reporters.json", "w", encoding="utf-8") as f:
    json.dump(reporters_flat, f, ensure_ascii=False, indent=2)

print(f"Stats rebuilt: {len(outlets_out)} outlets, {sum(len(o['reporters']) for o in outlets_out)} reporters from {len(conferences)} conferences")
