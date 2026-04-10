#!/usr/bin/env python3
"""Merge any new reporters/outlets from a conference JSON into base_data/outlets.json.

Uses Claude to handle the merge so IDs and structure stay consistent.

Usage: python pipeline/update_entities.py src/data/conferences/YYYY-MM-DD.json
"""
import anthropic, json, re, sys, os


def find_new_entities(conf, base_outlets):
    known_outlets = {}
    for o in base_outlets:
        for name in [o["name"]] + o.get("aliases", []):
            known_outlets[name] = o["id"]

    known_reporters: dict[str, set] = {}
    for o in base_outlets:
        oid = o["id"]
        known_reporters[oid] = set()
        for r in o["reporters"]:
            for rname in [r["name"]] + r.get("aliases", []):
                known_reporters[oid].add(rname)

    new_outlets: set[str] = set()
    new_reporters: list[dict] = []
    seen_reporters: set[tuple] = set()

    for q in conf.get("questions", []):
        outlet = q.get("outlet", "").strip()
        reporter = q.get("reporter", "").strip()
        if not outlet:
            continue
        if outlet not in known_outlets:
            new_outlets.add(outlet)
        elif reporter:
            oid = known_outlets[outlet]
            if reporter not in known_reporters.get(oid, set()):
                key = (reporter, outlet)
                if key not in seen_reporters:
                    seen_reporters.add(key)
                    new_reporters.append({"reporter": reporter, "outlet": outlet})

    return sorted(new_outlets), new_reporters


def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline/update_entities.py src/data/conferences/YYYY-MM-DD.json")
        sys.exit(1)

    conf_path = sys.argv[1]
    outlets_path = os.path.join(os.path.dirname(__file__), "../src/data/base_data/outlets.json")

    with open(conf_path, encoding="utf-8") as f:
        conf = json.load(f)

    with open(outlets_path, encoding="utf-8") as f:
        base_outlets = json.load(f)

    new_outlets, new_reporters = find_new_entities(conf, base_outlets)

    if not new_outlets and not new_reporters:
        print("No new entities — outlets.json unchanged.")
        return

    print(f"Found: {len(new_outlets)} new outlet(s), {len(new_reporters)} new reporter(s)")
    if new_outlets:
        for o in new_outlets:
            print(f"  New outlet: {o}")
    if new_reporters:
        for r in new_reporters:
            print(f"  New reporter: {r['reporter']} ({r['outlet']})")

    client = anthropic.Anthropic()

    new_section = ""
    if new_outlets:
        new_section += "\nNew outlets (not yet in the registry):\n"
        for o in new_outlets:
            new_section += f"  - {o}\n"
    if new_reporters:
        new_section += "\nNew reporters at known outlets:\n"
        for r in new_reporters:
            new_section += f"  - {r['reporter']} ({r['outlet']})\n"

    prompt = f"""You are updating the known outlets/reporters registry for Hungarian government press conferences.

Current outlets.json:
{json.dumps(base_outlets, ensure_ascii=False, indent=2)}

The following names were found in today's conference but are not in the registry:
{new_section}
These names come from auto-generated whisper transcriptions of spoken Hungarian, so they may contain transcription errors: mishearing, wrong accent marks, swapped characters, or phonetic approximations of the real name.

STEP 1 — Error correction (do this first):
For each unrecognised name, check whether it is likely a mis-transcription of an existing entry:
- Compare it against every name and alias already in the registry
- Consider common whisper errors: dropping/swapping accent marks (é↔e, á↔a, ő↔o, ü↔u, etc.), similar-sounding syllables, partial names, or added/missing letters
- If you are confident it is a mis-transcription of an existing entry, do NOT add a new entry — instead add the mis-transcribed form as a new alias on the existing entry (e.g. add "Nyilász Gergő" as an alias on Nyilas Gergely's reporter object)
- Only treat a name as genuinely new if it is clearly different from everything in the registry

STEP 2 — Add genuinely new entries:
- New outlet: generate a concise snake_case id (e.g. "Magyar Hang" → "magyar_hang", "HVG" → "hvg"). Add it with an empty reporters array unless a reporter was also listed.
- New reporter at a known outlet: append to that outlet's reporters array with the next sequential id (e.g. if last is "telex_r03" → new one is "telex_r04").

Other rules:
- Do NOT modify any existing entries other than appending aliases as described above.
- Return ONLY valid JSON. No markdown fences, no explanation.
"""

    print("Calling Claude to update outlets.json...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)

    updated = json.loads(text)

    with open(outlets_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"outlets.json updated: +{len(new_outlets)} outlet(s), +{len(new_reporters)} reporter(s)")


if __name__ == "__main__":
    main()
