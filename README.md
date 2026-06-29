# GTM Agent — Multi-Agent Launch Planner

A multi-agent orchestrator that turns a product backlog and release season into a backward-planned GTM plan.

## Architecture

The skill is a two-layer system:
- **Orchestrator** — the Claude Code skill that runs the pipeline and coordinates everything
- **Sub-agents** — one Claude sub-agent spun up per product idea, each reading, summarizing, and classifying in isolation to keep context clean

Python scripts handle data fetching and rendering; LLM reasoning handles classification and judgment.

## Pipeline

```
Filter season ideas
  → fan-out: one sub-agent per idea
      → read & summarize
      → classify GTM level (1-4) + customer-impact tier
      → judge release strategy (GA / beta / silent / phased)
      → curate GTM checklist rows
  → backward-plan dated owners from season end date
  → flag gaps needing human input
  → render HTML dashboard
```

## Stack

- Claude Code skill (orchestrator)
- Claude sub-agents (one per product idea, parallel fan-out)
- Python 3 — `list_jpds.py`, `curate.py`, `plan.py`, `render_html.py`
- Jira API for backlog data

## Usage

```
/gtm-agent
```
