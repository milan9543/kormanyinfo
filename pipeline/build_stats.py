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
