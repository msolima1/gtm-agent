#!/usr/bin/env python3
"""
curate.py — Deterministic GTM checklist curation, grouped into per-team briefs.

Given a GTM level (1-4), filters the baked checklist to the tasks that apply at that
level, groups them by team, and joins the default owner from the stakeholder roster.
The output is structured as per-team briefs (the bundling engine fills the narrative +
"what we need from you" later) — NOT a flat list.

Two input modes:
  1. Single level:   curate.py --level 3
  2. Whole season:   curate.py --jpds-file jpds.json   (output of list_jpds.py --output json)
     Uses each JPD's launch_level; JPDs with no level go to needs_sdm.

Usage:
  python3 curate.py --level 3 --output table
  python3 list_jpds.py --project MYGJPD --season "Fall 2026" --output json > jpds.json
  python3 curate.py --jpds-file jpds.json --output json > curated.json
"""
import argparse, csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.normpath(os.path.join(HERE, "..", "references"))

def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def parse_level(v):
    """'Level 3' / '3' / 3 -> 3 ; None/'' -> None"""
    if v is None: return None
    m = re.search(r"([1-4])", str(v))
    return int(m.group(1)) if m else None

def owner_for(team, roster):
    """Match checklist team name to a stakeholder roster keyword (case-insensitive)."""
    t = (team or "").upper()
    best = None
    for r in roster:
        kw = (r["team_keyword"] or "").upper().strip()
        if not kw: continue
        if kw in t or t.startswith(kw) or (len(t) > 4 and t in kw):
            if best is None or len(kw) > len(best["team_keyword"]):
                best = r
    return best

def curate_level(level, checklist, roster):
    col = f"L{level}"
    teams = {}
    for row in checklist:
        if row.get(col) != "1":
            continue
        team = row.get("team") or "OTHER"
        st = owner_for(team, roster)
        g = teams.setdefault(team, {
            "team": team,
            "category": (st or {}).get("category", "supporting"),
            "owner": (st or {}).get("default_owner", "UNASSIGNED — ask SDM"),
            "role": (st or {}).get("role", ""),
            "contact": (st or {}).get("contact", ""),
            "tasks": [],
        })
        g["tasks"].append({
            "task": row.get("task"),
            "release_stage": row.get("release_stage") or "",
            "timing": row.get("timing") or "",
            "audience": row.get("audience") or "",
            "new_or_update": row.get("new_or_update") or "",
            "localization": row.get("localization") or "",
            "dependencies": row.get("dependencies") or "",
        })
    # order: primary -> supporting -> launch
    order = {"primary": 0, "supporting": 1, "launch": 2}
    return sorted(teams.values(), key=lambda g: (order.get(g["category"], 3), g["team"]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, choices=[1, 2, 3, 4])
    ap.add_argument("--jpds-file")
    ap.add_argument("--checklist", default=os.path.join(REF, "gtm_checklist.csv"))
    ap.add_argument("--stakeholders", default=os.path.join(REF, "stakeholders.csv"))
    ap.add_argument("--output", choices=["json", "table"], default="json")
    a = ap.parse_args()
    if not a.level and not a.jpds_file:
        sys.exit("ERROR: provide --level N or --jpds-file <path>")

    checklist = load_csv(a.checklist)
    roster = load_csv(a.stakeholders)

    if a.level:
        result = {"mode": "level", "level": a.level,
                  "teams": curate_level(a.level, checklist, roster)}
        jpds_out = None
    else:
        data = json.load(open(a.jpds_file))
        jpds_in = data.get("jpds", data if isinstance(data, list) else [])
        curated, needs_sdm = [], []
        for j in jpds_in:
            lvl = parse_level(j.get("launch_level"))
            if not lvl:
                needs_sdm.append({"key": j.get("key"), "summary": j.get("summary"),
                                  "reason": "no Launch Level — infer or ask PMM"})
                continue
            curated.append({
                "key": j.get("key"), "summary": j.get("summary"), "level": lvl,
                "production_target": j.get("production_target"),
                "teams": curate_level(lvl, checklist, roster),
            })
        result = {"mode": "season", "project": data.get("project"),
                  "season": data.get("season"), "curated": curated, "needs_sdm": needs_sdm}
        jpds_out = curated

    if a.output == "json":
        print(json.dumps(result, indent=2, default=str))
        return

    # table
    def print_teams(teams, level):
        ntasks = sum(len(g["tasks"]) for g in teams)
        print(f"  Level {level}: {len(teams)} teams, {ntasks} tasks")
        for g in teams:
            print(f"    [{g['category']}] {g['team']}  —  owner: {g['owner']} ({len(g['tasks'])} tasks)")
            for t in g["tasks"][:4]:
                print(f"        - {t['task']}")
            if len(g["tasks"]) > 4:
                print(f"        ... +{len(g['tasks'])-4} more")
    if a.level:
        print_teams(result["teams"], a.level)
    else:
        print(f"{result['project']} / {result['season']}: {len(result['curated'])} JPDs curated, "
              f"{len(result['needs_sdm'])} need SDM input\n")
        for c in result["curated"]:
            print(f"{c['key']} (Level {c['level']}) — {(c['summary'] or '')[:55]}")
            print_teams(c["teams"], c["level"]); print()
        if result["needs_sdm"]:
            print("Needs SDM input:", ", ".join(x["key"] for x in result["needs_sdm"]))

if __name__ == "__main__":
    main()
