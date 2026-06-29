# gtm-agent

A Claude Code skill that turns a product backlog + season into a backward-planned GTM plan.

## What it does

Given a set of product ideas and a release season, the agent:

1. Filters ideas to the current season
2. Reads and summarizes each item
3. Classifies by GTM level (1-4) and customer-impact tier
4. Judges release strategy (GA, beta, silent, etc.)
5. Curates a GTM checklist per item
6. Backward-plans dated owners from the season end date
7. Flags gaps that need SDM input

Output is an actionable HTML dashboard with highlighted gaps and owner assignments.

## Stack

- Claude Code skill (multi-step agentic pipeline)
- Python 3 (stdlib only, no dependencies)
- Jira API for backlog data
- LLM reasoning for classification and checklist curation

## Usage

```
/gtm-agent
```
