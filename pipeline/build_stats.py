#!/usr/bin/env python3
"""Rebuild outlets.json and reporters.json from all conference files."""
import json, glob, os
from collections import defaultdict

# Brand colors for known outlets: (bg_color, text_color)
OUTLET_COLORS = {
    "Telex":         {"color": "#113356", "text_color": "#ffffff"},
    "Közmédia":      {"color": "#001224", "text_color": "#ffffff"},
    "ATV":           {"color": "#F8313F", "text_color": "#ffffff"},
    "HírTV":         {"color": "#22366D", "text_color": "#ffffff"},
    "444":           {"color": "#FFF670", "text_color": "#1B1B1B"},
    "RTL Híradó":    {"color": "#66E0C1", "text_color": "#ffffff"},
    "Index":         {"color": "#FF9903", "text_color": "#ffffff"},
    "Magyar Nemzet": {"color": "#ffffff", "text_color": "#000000"},
    "Blikk":         {"color": "#E20000", "text_color": "#ffffff"},
    "TV2":           {"color": "#ED262B", "text_color": "#ffffff"},
    "Pesti Srácok":  {"color": "#FF8200", "text_color": "#1A1826"},
    "M1 Híradó":     {"color": "#324BCF", "text_color": "#ffffff"},
    "Magyar Hírlap": {"color": "#ffffff", "text_color": "#000000"},
}
DEFAULT_COLORS = {"color": "#6B7280", "text_color": "#ffffff"}

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
    colors = OUTLET_COLORS.get(name, DEFAULT_COLORS)
    outlets.append({
        "name": name,
        "total_questions": len(qs),
        "avg_criticism": round(sum(q["criticism_percent"] for q in qs) / len(qs), 1) if qs else 0,
        "avg_hostility": round(sum(q["hostility_percent"] for q in qs) / len(qs), 1) if qs else 0,
        "conferences_attended": len(data["conferences"]),
        "color": colors["color"],
        "text_color": colors["text_color"],
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
