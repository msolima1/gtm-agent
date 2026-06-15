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

# Pillar -> keywords used to match rows in product_roster.csv (focus_areas/portfolio/dev team)
PILLAR_KEYWORDS = {
    "maintenance": ["work order","fault","predictive maintenance","maintenance rules","schedules",
                    "asset health","fleet health","aftertreatment","downtime","vmrs","dvir","repair",
                    "vehicle maintenance","maintenance"],
    "safety": ["safety","collision","incident","camera","adas","driver behaviour","driver behavior"],
    "compliance": ["compliance","hos","eld","inspection","dvir"],
}

def pillar_owners(roster_path, pillar):
    """Resolve real named owners for a pillar from product_roster.csv (first non-empty per role)."""
    if not pillar or not os.path.exists(roster_path):
        return {}
    rows = load_csv(roster_path)
    kws = PILLAR_KEYWORDS.get(pillar.lower(), [pillar.lower()])
    roles = ["product_leader","design_leader","product_manager","product_design",
             "sdm","data_science","product_marketing","sol_eng","esup"]
    found = {r: "" for r in roles}
    pms = []
    for row in rows:
        blob = " ".join([row.get("portfolio",""), row.get("focus_areas",""),
                         row.get("development_team","")]).lower()
        if not any(k in blob for k in kws):
            continue
        for r in roles:
            v = (row.get(r) or "").strip()
            if v and not found[r]:
                found[r] = v
        pm = (row.get("product_manager") or "").strip()
        if pm and pm not in pms: pms.append(pm)
    found["product_managers_all"] = "; ".join(pms)
    return {k: v for k, v in found.items() if v}

# Maps a GTM checklist team -> which roster role fills its owner (when --pillar is set)
TEAM_ROLE = {
    "PRODUCT MANAGEMENT": "product_leader",
    "PRODUCT MARKETING": "product_marketing",
    "SOLUTIONS ENGINEERING": "sol_eng",
}

def curate_level(level, checklist, roster, powners=None):
    col = f"L{level}"
    teams = {}
    for row in checklist:
        if row.get(col) != "1":
            continue
        team = row.get("team") or "OTHER"
        st = owner_for(team, roster)
        owner = (st or {}).get("default_owner", "UNASSIGNED — ask SDM")
        # override with the pillar's real named owner when available
        if powners:
            for key, role in TEAM_ROLE.items():
                if key in team.upper() and powners.get(role):
                    owner = powners[role]
                    break
        g = teams.setdefault(team, {
            "team": team,
            "category": (st or {}).get("category", "supporting"),
            "owner": owner,
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
    ap.add_argument("--roster", default=os.path.join(REF, "product_roster.csv"))
    ap.add_argument("--pillar", help="Pillar (e.g. Maintenance) to fill real named owners from product_roster.csv")
    ap.add_argument("--output", choices=["json", "table"], default="json")
    a = ap.parse_args()
    if not a.level and not a.jpds_file:
        sys.exit("ERROR: provide --level N or --jpds-file <path>")

    checklist = load_csv(a.checklist)
    roster = load_csv(a.stakeholders)
    powners = pillar_owners(a.roster, a.pillar) if a.pillar else {}

    if a.level:
        result = {"mode": "level", "level": a.level, "pillar": a.pillar,
                  "pillar_stakeholders": powners,
                  "teams": curate_level(a.level, checklist, roster, powners)}
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
                "teams": curate_level(lvl, checklist, roster, powners),
            })
        result = {"mode": "season", "project": data.get("project"),
                  "season": data.get("season"), "pillar": a.pillar,
                  "pillar_stakeholders": powners,
                  "curated": curated, "needs_sdm": needs_sdm}
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
