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
import argparse, csv, json, os, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.normpath(os.path.join(HERE, "..", "references"))

STRATEGIES = {"code_release","ff_fast","ff_slow","hidden_url","closed_beta","open_beta","experimental","ga"}
CATEGORIES = {"primary","supporting","launch"}

def load_lead_times(path):
    strat, cat = {}, {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or not row[0] or row[0] in ("release_strategy","category"): continue
            key = row[0].strip()
            try: num = int(row[1])
            except (IndexError, ValueError): continue
            if key in STRATEGIES: strat[key] = num
            elif key in CATEGORIES: cat[key] = num
    return strat, cat

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

def plan_jpd(teams, anchor, strategy, strat_win, cat_off):
    # release strategy widens the earliest team's runway
    extra = max(0, strat_win.get(strategy, 9) - 9)  # ff_fast(9) is the baseline
    dated = []
    earliest = anchor
    for g in teams:
        off = cat_off.get(g["category"], 21) + extra
        start = anchor - timedelta(days=off)
        if start < earliest: earliest = start
        dated.append({
            "team": g["team"], "category": g["category"], "owner": g["owner"],
            "role": g.get("role",""), "contact": g.get("contact",""),
            "task_count": len(g["tasks"]),
            "start_date": start.isoformat(), "due_date": anchor.isoformat(),
            "tasks": g["tasks"],
        })
    dated.sort(key=lambda d: d["start_date"])
    return dated, earliest

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--curated-file", required=True)
    ap.add_argument("--anchor", help="YYYY-MM-DD override (for single-level curated input)")
    ap.add_argument("--release-strategy", default="ff_fast", choices=sorted(STRATEGIES))
    ap.add_argument("--lead-times", default=os.path.join(REF, "lead_times.csv"))
    ap.add_argument("--output", choices=["json","table"], default="json")
    a = ap.parse_args()

    strat_win, cat_off = load_lead_times(a.lead_times)
    data = json.load(open(a.curated_file))

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
        anchor = anchor_start(pt) or (date.fromisoformat(a.anchor) if a.anchor else None)
        if not anchor:
            unplanned.append({"key": key, "summary": summary, "level": level,
                              "reason": "no Production Target anchor — ask PM for release date"})
            continue
        dated, earliest = plan_jpd(teams, anchor, a.release_strategy, strat_win, cat_off)
        out.append({"key": key, "summary": summary, "level": level,
                    "release_strategy": a.release_strategy,
                    "anchor_date": anchor.isoformat(), "kickoff_by": earliest.isoformat(),
                    "teams": dated})

    result = {"project": data.get("project"), "season": data.get("season"),
              "planned": out, "unplanned": unplanned, "needs_sdm": needs if data.get("mode")=="season" else []}

    if a.output == "json":
        print(json.dumps(result, indent=2, default=str)); return

    for p in out:
        print(f"\n{p['key']} (Level {p['level']}, {p['release_strategy']}) — {(p['summary'] or '')[:50]}")
        print(f"  Anchor (release): {p['anchor_date']}   Kick off GTM by: {p['kickoff_by']}")
        for t in p["teams"]:
            print(f"    {t['start_date']} -> {t['due_date']}  [{t['category']:10}] {t['team'][:34]:34} {t['task_count']:>2} tasks  ({t['owner']})")
    if unplanned:
        print("\nUnplanned (no anchor date):", ", ".join(x["key"] for x in unplanned))
    if result["needs_sdm"]:
        print("Needs SDM input (no level):", ", ".join(x["key"] for x in result["needs_sdm"]))

if __name__ == "__main__":
    main()
