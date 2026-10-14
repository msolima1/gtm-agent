# GTM Agent

An AI agent that turns a product backlog and a release season into a backward-planned,
per-team go-to-market (GTM) launch plan.

## The problem

Launch planning usually defaults to the engineering timeline: "ship date minus a week" for
marketing, docs, support, and sales enablement. That ignores two things:

- **Dev effort is not the same as customer impact.** A one-line config change and a brand-new
  workflow can take the same engineering time but need wildly different GTM treatment (a tweet
  vs. a full enablement campaign).
- **GTM work has its own lead times**, and they don't all start from the same date. Localization,
  training content, and sales playbooks need weeks of runway; a release-notes line needs days.
  Planning backward from a single "launch day" and applying one blanket lead time either starts
  everyone too late or wastes effort starting everyone too early.

This agent reads the backlog, classifies each item by actual customer impact (not engineering
cost), works out the right release strategy, and backward-plans a dated, per-team GTM plan from
the release date — flagging every assumption and gap so a human can confirm or correct it instead
of discovering it was wrong two weeks before launch.

## How it works

### Pipeline

```
Backlog board + season
        |
        v
[1] list_jpds.py        filter items by season, resolve custom fields by name
        |                (board-agnostic — works on any Jira-like project)
        v
[2] LLM reasoning        fan out one sub-agent per item:
        |                 - summarize + tie to customer impact
        |                 - classify customer-impact tier (Low / Med Additive /
        |                   Med Disruptive / High)
        |                 - classify GTM level 1-4 (marketing investment, NEVER
        |                   inferred from dev effort)
        |                 - judge release strategy (GA / beta / flag rollout / silent)
        v
[2.5] Bundle              combine the season's items into ONE GTM narrative —
        |                 what's shipping, why it matters, how it bundles together
        v
[3] curate.py             filter the GTM checklist to the right level, group by
        |                 team, join each team's default owner from the roster
        v
[4] plan.py               backward-plan each team's start date from the release
        |                 date (anchor), using per-team + per-strategy lead times;
        |                 falls back to end-of-season when no release date is set
        |                 yet, and marks that as an assumption
        v
[5] render_html.py        single self-contained HTML dashboard: gaps and
                          assumptions banner-called-out at the top, then one
                          card per item with its dated per-team plan
```

### Three axes the agent keeps separate

1. **GTM level (1-4)** — how much marketing investment this gets. Drives which checklist rows
   apply.
2. **Customer-impact tier** (Low / Medium Additive / Medium Disruptive / High) — how disruptive
   the change is to an existing workflow. Drives release strategy and comms intensity.
3. **Release strategy** (code release / feature-flag fast or slow rollout / hidden URL / closed
   beta / open beta / experimental / GA) — the actual rollout mechanism.

Conflating these three is the most common planning mistake this agent is designed to catch: a
high-dev-effort feature can be low customer-impact (skip the campaign), and a trivial-to-build
feature can be high customer-impact (needs training content and advance notice).

### Human-in-the-loop by design

The agent never silently guesses on anything that materially changes the plan. When it can't
determine a level, release strategy, or release date with confidence, it flags the item and names
who should resolve it (dev lead for flag mechanics, PM for timing, product marketing for
positioning). The rendered HTML puts every such gap in a banner at the top plus inline on the
affected item, so the dashboard drives action instead of sitting as a static report.

## Architecture

- **Orchestrator** — a Claude Code skill (`skills/workflow-gtm-agent/SKILL.md`) that runs the
  pipeline end to end and does the LLM reasoning steps (classification, judgment, narrative
  bundling).
- **Sub-agents** — one per backlog item, fanned out in parallel, each reading/summarizing/
  classifying in isolation to keep context clean.
- **Python scripts** — deterministic data fetching, filtering, and rendering:
  - `list_jpds.py` — pulls and filters backlog items from a Jira-compatible API.
  - `curate.py` — filters the GTM checklist by level and groups tasks by team.
  - `plan.py` — computes backward-planned dates per team from a release-date anchor.
  - `render_html.py` — renders the final plan as a single-file HTML dashboard.

LLM reasoning handles judgment calls (impact classification, release strategy, narrative
bundling); the Python layer handles everything deterministic (filtering, date math, rendering) so
the LLM isn't re-deriving arithmetic every run.

## Reference data (sample)

`skills/workflow-gtm-agent/references/*.csv` ship with small, generic **sample data** — a
10-row GTM checklist, a handful of fictional stakeholders, and a 3-row product roster — just
enough to exercise the pipeline end to end. Swap in your own checklist, roster, and lead-time
data to point this at a real org; the schemas are documented inline in `curate.py` and `plan.py`.

## Running it with sample data

```bash
# 3. Curate a single-level template straight from the sample checklist (no backlog data needed):
python3 skills/workflow-gtm-agent/scripts/curate.py --level 3 --output table

# 4. Backward-plan it from an explicit anchor date:
python3 skills/workflow-gtm-agent/scripts/curate.py --level 3 --output json > level3.json
python3 skills/workflow-gtm-agent/scripts/plan.py --curated-file level3.json \
  --anchor 2026-08-01 --release-strategy ff_fast --output table

# 5. Render the HTML dashboard:
python3 skills/workflow-gtm-agent/scripts/plan.py --curated-file level3.json \
  --anchor 2026-08-01 --output json > plan.json
python3 skills/workflow-gtm-agent/scripts/render_html.py --plan-file plan.json --out gtm_plan.html
```

Step 1 (`list_jpds.py`, pulling live backlog items) needs a Jira-compatible API token in
`~/jira.json` (`{"email", "token", "base_url"}`). Everything else runs on local JSON/CSV, so you
can try steps 3-5 immediately with the bundled sample data.

## Stack

- Claude Code skill (orchestrator) + Claude sub-agents (one per backlog item, parallel fan-out)
- Python 3, stdlib only — `list_jpds.py`, `curate.py`, `plan.py`, `render_html.py`
- A Jira-compatible issue tracker for backlog data

## Usage

```
/gtm-agent
```
