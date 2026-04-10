#!/usr/bin/env python3
"""Check a conference JSON for reporters or outlets not yet in base_data/outlets.json."""
import json, sys, glob

conference_arg = sys.argv[1] if len(sys.argv) > 1 else None

if conference_arg:
    paths = [conference_arg]
else:
    paths = sorted(glob.glob("src/data/conferences/*.json"))

with open("src/data/base_data/outlets.json", encoding="utf-8") as f:
    base_outlets = json.load(f)

known_outlets = set()
known_reporters: dict[str, set] = {}
for o in base_outlets:
    all_names = [o["name"]] + o.get("aliases", [])
    for name in all_names:
        known_outlets.add(name)
        known_reporters[name] = set()
    for r in o["reporters"]:
        for rname in [r["name"]] + r.get("aliases", []):
            known_reporters[o["name"]].add(rname)
            for alias in all_names:
                known_reporters.setdefault(alias, set()).add(rname)

for path in paths:
    with open(path, encoding="utf-8") as f:
        conf = json.load(f)

    new_outlets: set[str] = set()
    new_reporters: set[tuple[str, str]] = set()

    for q in conf.get("questions", []):
        outlet = q.get("outlet", "")
        reporter = q.get("reporter", "")
        if outlet not in known_outlets:
            new_outlets.add(outlet)
        elif reporter and reporter not in known_reporters.get(outlet, set()):
            new_reporters.add((reporter, outlet))

    if new_outlets or new_reporters:
        print(f"\n{path}")
        if new_outlets:
            print("  New outlets:")
            for o in sorted(new_outlets):
                print(f"    - {o}")
        if new_reporters:
            print("  New reporters:")
            for reporter, outlet in sorted(new_reporters):
                print(f"    - {reporter} ({outlet})")

if not any(True for p in paths for _ in [p]):
    print("No conference files found.")
