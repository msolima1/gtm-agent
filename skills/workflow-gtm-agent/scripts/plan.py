#!/usr/bin/env python3
"""
plan.py — Backward-plan dated owners for a curated GTM plan.

Anchors on the JPD's Production Target start (the FF enablement / release date) and
computes each team's start date = anchor - lead time. Lead times come from
references/lead_times.csv (per-category offsets; release-strategy windows widen the
earliest start). Deliverables are due by the anchor.

Input modes:
  1. Season:  plan.py --curated-file curated.json
              (output of curate.py --jpds-file ... --output json ; uses each JPD's production_target)
  2. Single:  plan.py --curated-file level3.json --anchor 2026-08-01 --release-strategy ff_fast
              (curate.py --level N --output json ; you supply the anchor)

Usage:
  python3 curate.py --jpds-file jpds.json --output json > curated.json
  python3 plan.py --curated-file curated.json --output table
"""
import argparse, csv, json, os, re, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.normpath(os.path.join(HERE, "..", "references"))

STRATEGIES = {"code_release","ff_fast","ff_slow","hidden_url","closed_beta","open_beta","experimental","ga"}
DEFAULT_SLA = 21

def load_lead_times(path):
    strat, team_sla, default_sla = {}, {}, DEFAULT_SLA
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kind = (row.get("kind") or "").strip()
            key = (row.get("key") or "").strip()
            try: days = int(row.get("days"))
            except (TypeError, ValueError): continue
            if kind == "strategy": strat[key] = days
            elif kind == "team": team_sla[key.upper()] = days
            elif kind == "default": default_sla = days
    return strat, team_sla, default_sla

def team_lead(team, team_sla, default_sla):
    t = (team or "").upper()
    best = None
    for kw, days in team_sla.items():
        if kw in t or t.startswith(kw):
            if best is None or len(kw) > best[0]:
                best = (len(kw), days)
    return best[1] if best else default_sla

def anchor_start(production_target):
    if isinstance(production_target, str):
        try: production_target = json.loads(production_target)
        except Exception: return None
    if isinstance(production_target, dict):
        s = production_target.get("start")
        if s:
            try: return date.fromisoformat(s[:10])
            except ValueError: return None
    return None

# Season -> end-of-season date (fallback anchor when a JPD has no Production Target).
_SEASON_END = {"spring": (5,31), "summer": (8,31), "fall": (11,30),
               "autumn": (11,30), "winter": (2,28)}
def season_end(season):
    """'Fall 2026' -> date(2026,11,30). Returns None if unparseable."""
    if not season: return None
    s = season.lower()
    yr = re.search(r"(20\d{2})", s)
    if not yr: return None
    year = int(yr.group(1))
    for name,(m,d) in _SEASON_END.items():
        if name in s:
            return date(year, m, d)
    return None

def plan_jpd(teams, anchor, strategy, strat_win, team_sla, default_sla):
    # release strategy widens every team's runway relative to ff_fast(9) baseline
    extra = max(0, strat_win.get(strategy, 9) - 9)
    dated = []
    earliest = anchor
    for g in teams:
        off = team_lead(g["team"], team_sla, default_sla) + extra
        start = anchor - timedelta(days=off)
        if start < earliest: earliest = start
        dated.append({
            "team": g["team"], "category": g["category"], "owner": g["owner"],
            "role": g.get("role",""), "contact": g.get("contact",""),
            "sla_days": off, "task_count": len(g["tasks"]),
            "start_date": start.isoformat(), "due_date": anchor.isoformat(),
            "tasks": g["tasks"],
        })
    dated.sort(key=lambda d: d["start_date"])
    return dated, earliest

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--curated-file", required=True)
    ap.add_argument("--anchor", help="YYYY-MM-DD override anchor for ALL JPDs lacking a target date")
    ap.add_argument("--season-end", help="YYYY-MM-DD season-end fallback (overrides auto season parsing)")
    ap.add_argument("--release-strategy", default="ff_fast", choices=sorted(STRATEGIES))
    ap.add_argument("--lead-times", default=os.path.join(REF, "lead_times.csv"))
    ap.add_argument("--output", choices=["json","table"], default="json")
    a = ap.parse_args()

    strat_win, team_sla, default_sla = load_lead_times(a.lead_times)
    data = json.load(open(a.curated_file))
    # season-end fallback anchor (most JPDs lack a Production Target)
    season = data.get("season")
    fallback = (date.fromisoformat(a.season_end) if a.season_end
                else (date.fromisoformat(a.anchor) if a.anchor else season_end(season)))

    jobs = []
    if data.get("mode") == "season":
        for c in data.get("curated", []):
            jobs.append((c["key"], c["summary"], c["level"], c.get("production_target"), c["teams"]))
        needs = data.get("needs_sdm", [])
    elif data.get("mode") == "level":
        jobs.append((f"LEVEL-{data['level']}", f"Level {data['level']} template", data["level"], None, data["teams"]))
        needs = []
    else:
        sys.exit("ERROR: --curated-file must be curate.py JSON output (mode season|level)")

    out, unplanned = [], []
    for key, summary, level, pt, teams in jobs:
        real = anchor_start(pt)
        anchor = real or fallback
        if not anchor:
            unplanned.append({"key": key, "summary": summary, "level": level,
                              "reason": f"no Production Target and season '{season}' not parseable — "
                                        f"pass --season-end YYYY-MM-DD or ask PM for release date"})
            continue
        anchor_source = "production_target" if real else f"ASSUMED end-of-season ({season})"
        dated, earliest = plan_jpd(teams, anchor, a.release_strategy, strat_win, team_sla, default_sla)
        out.append({"key": key, "summary": summary, "level": level,
                    "release_strategy": a.release_strategy,
                    "anchor_date": anchor.isoformat(), "anchor_source": anchor_source,
                    "anchor_assumed": real is None,
                    "kickoff_by": earliest.isoformat(), "teams": dated})

    result = {"project": data.get("project"), "season": data.get("season"),
              "planned": out, "unplanned": unplanned, "needs_sdm": needs if data.get("mode")=="season" else []}

    if a.output == "json":
        print(json.dumps(result, indent=2, default=str)); return

    n_assumed = sum(1 for p in out if p["anchor_assumed"])
    print(f"{data.get('project')} / {season}: {len(out)} planned ({n_assumed} on ASSUMED season-end anchor), "
          f"{len(unplanned)} unplanned")
    for p in out:
        flag = "  [ASSUMED end-of-season]" if p["anchor_assumed"] else ""
        print(f"\n{p['key']} (Level {p['level']}, {p['release_strategy']}) — {(p['summary'] or '')[:50]}")
        print(f"  Anchor (release): {p['anchor_date']}{flag}   Kick off GTM by: {p['kickoff_by']}")
        for t in p["teams"]:
            print(f"    {t['start_date']} -> {t['due_date']}  [{t['category']:10}] {t['team'][:34]:34} {t['task_count']:>2} tasks  ({t['owner']})")
    if unplanned:
        print("\nUnplanned (no anchor date):", ", ".join(x["key"] for x in unplanned))
    if result["needs_sdm"]:
        print("Needs SDM input (no level):", ", ".join(x["key"] for x in result["needs_sdm"]))

if __name__ == "__main__":
    main()
