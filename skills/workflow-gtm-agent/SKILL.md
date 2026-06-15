---
name: workflow-gtm-agent
description: "GTM Agent for Geotab launches. Given a JPD board + season, filters the season's ideas, classifies each by GTM level and customer-impact tier, judges release strategy, curates the GTM checklist, and backward-plans dated owners. Use for GTM planning, launch readiness, release planning, season GTM, JPD-to-GTM, or 'what GTM work does this feature need'."
---

# GTM Agent

## Overview

Turns a JPD board + season into a backward-planned GTM plan. The SDM sets direction; the agent
drives execution. Pipeline (matches the team whiteboard):

`Filter season -> read & summarize each JPD -> classify GTM level + customer-impact tier ->
judge release strategy -> curate the GTM checklist -> backward-plan dated owners -> flag SDM gaps`.

**Status: V0** — `list_jpds.py` (filter + field extraction) is working and board-agnostic.
Curation, backward-planning, and the launch-template output are being layered in.

## Prerequisites

- `~/jira.json` with `{email, token, base_url}` (Jira API token). Set up via `util-auth` if missing.
- Python 3 (stdlib only — no pip installs).

## Three axes the agent must keep distinct

1. **GTM Level / Launch Tier 1-4** — marketing investment. From JPD field **Launch Level** (often
   pre-set), else inferred, else ask SDM. Decides *which checklist rows apply*.
2. **Customer-impact tier** — Low / Medium Additive / Medium Disruptive / High (UX disruption).
   Decides *release strategy + comms intensity*. See `references/PROCESS-RULES.md`.
3. **Release strategy** — code release / FF fast / FF slow / hidden URL / closed beta / open beta /
   experimental / GA.

## Step 1 — Filter the board by season (works now)

```bash
python3 scripts/list_jpds.py --project <BOARD> --season "<Season>" --output table
# JSON for piping into later steps:
python3 scripts/list_jpds.py --project <BOARD> --season "<Season>" --output json
```

- Board-agnostic: resolves `Launch Level`, `Production Target`, `Season` field IDs BY NAME at runtime
  (works on MYGJPD, EXPJPD, Safety, HW, ...).
- Season is flexible: a **label** (e.g. `Fall2026`, `Connect_2025_Target`), a Season-field value
  (e.g. `Fall 2026`), or free text. **If 0 results, the tool prints the labels/season values that
  actually exist on that board** — pick yours and re-run.

Verified examples:
- `--project MYGJPD --season "Fall 2026"` -> 32 JPDs
- `--project EXPJPD --season "Connect_2025_Target"` -> 3 JPDs

Each JPD returns: `key, summary, launch_level, level_source, production_target (anchor), season,
behind_ff, assignee, url`. JPDs missing level or anchor are flagged for SDM input.

## Step 2 — Read, summarize & classify each JPD (agent reasoning, fan-out)

For each JPD (fan out one sub-agent per JPD when the list is long, to keep context isolated), read
the summary/description and produce:
- **Summary / Why / Who** (the PM/assignee) and tie it to **customer impact**.
- **GTM level**: use `launch_level` if present; else infer L1-L4 from customer + market impact
  (NEVER dev effort); else flag.
- **Customer-impact tier** (Low / Med Additive / Med Disruptive / High) from the change description.
- **Release strategy**: judge from the summary + signals (`behind_ff`, anchor shape, beta language),
  using `references/PROCESS-RULES.md` (FF intake-form logic, Beta tracks, rollout method).
- Output a record: `{key, summary, gtm_level, level_source, impact_tier, release_strategy,
  anchor_date, confidence, questions_for_sdm[]}`.

## Step 2.5 — Bundle into ONE GTM narrative (the core value)

The agent is a **translation + bundling engine**, not a checklist printer. The GTM roster does not
care about individual JPDs (those are PM/dev requirement artifacts). Synthesize the season's JPDs
into **one combined product-change / release narrative** aimed at the GTM crew — the message a SDM
would craft: what is shipping this season, why it matters to customers, how it bundles together.

## Step 3 — Per-team briefs (translate the narrative for each team)

Do NOT emit a flat checklist. For each relevant GTM team, produce a **tailored brief** based on what
THAT team actually needs:
- **What we're giving you** — the inputs/context/assets relevant to this team (e.g. Video team =
  Figma link + instructions only; Localization = source content + locales; Sales Enablement =
  positioning + talk-track inputs).
- **What we need from you** — their deliverables + due date.

Use `references/gtm_checklist.csv` (86 tasks, `L1..L4` + team + release stage) to know WHICH teams
and tasks apply at this GTM level, and `references/stakeholders.csv` for the named owner. But the
deliverable is the per-team brief, not the raw row. If a team's brief is large, emit it as a
**linked ticket or linked doc** rather than overstuffing one checklist row. *(Helper `curate.py`
lands in V1.)*

## Step 4 — Backward-plan dated owners

Anchor on `production_target.start`; compute each task's start = anchor - lead time using
`references/lead_times.csv` (code ~7d, FF fast ~9d, FF slow ~30d, open beta ~84d, etc.; plus per-
category offsets). *(Helper `plan.py` lands in V1.)*

## Step 5 — Output

The output is a **bundled GTM message + per-team brief set**, not a flat list. Populate a copy of the
**Product Launch one-source-of-truth** template: the bundled narrative as the positioning/overview,
stakeholders, files/links, Launch Tier, and the per-team briefs (each with what-we-give / what-we-
need / dates) as the GTM Launch Tracker — large team briefs linked out as their own ticket/doc.
Optional: season-portfolio HTML + per-JPD Gantt. *(V1.)*

## Human-in-the-loop (release-strategy gap-filler)

When level / release strategy / anchor can't be determined confidently, emit a **"Questions for
SDM"** block naming WHO to ask: **Dev Lead** (FF mechanics), **PM** (release timing), **PMM**
(level/positioning). Never silently guess.

## References

- `references/PROCESS-RULES.md` — captured Geotab rules (4 impact tiers verbatim, FF intake-form
  schema, Beta tracks + durations, output-template sections, field mapping, reasoning chain).
- `references/gtm_checklist.csv` — 86 GTM tasks x level applicability x team x release stage.
- `references/stakeholders.csv` — team -> role -> default owner.
- `references/lead_times.csv` — release-strategy windows + per-category lead offsets.
