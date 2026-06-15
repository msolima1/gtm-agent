# GTM Agent — Captured Process Rules (durable source of truth)

Captured 2026-06-15 from real Geotab docs. Verbatim where quoted. Do NOT fabricate beyond this.

## Source docs

| Source | ID | Status |
|---|---|---|
| GTM Checklist (Sheet, "Launch and Release Checklist", 112 rows) | `1dHxDm_EuDNT-ZQLVKChLfdzE33_TvPm6z5Kxm5GvHcQ` | extracted (level booleans) |
| Stakeholder roster (Doc) | `13nwRXCSCYdDmLijgNrcuSW6hKw-FpYUnT1hme7HPaiQ` | extracted |
| Beta program (Doc) | `1ttRa_yrpQLyWeKf_gqh0XZuVydEMSug6dJYeleM_I1I` | extracted |
| FF Release Strategy intake form (Doc, IMAGE-ONLY — OCR'd) | `1Tg0dv4PRzM-_hsqguaeb5h7kbdpC1R_Q-bbdgtHE6CY` | OCR'd → see below. PNGs in assets/tier-doc-{1..4}.png |
| HW filled launch template (output target) | `1aiNZ1TDnlKaRx0r0735dzsKzR2Dlf9UMSuIQZnOffGc` | extracted |

## Three distinct "level/tier" axes (do NOT conflate)

1. **GTM Level / Launch Tier 1-4** — marketing investment. JPD field `Launch Level`, checklist `LEVEL 1..4` booleans, template "Launch Tier" (PMM-recommended). Drives which checklist rows apply.
2. **Customer-impact tier (Low / Medium Additive / Medium Disruptive / High)** — UX disruption. Drives release strategy + comms intensity.
3. **Release strategy** — code release / FF fast / FF slow / closed beta / open beta / experimental / GA.

## Customer-impact tiers (verbatim)

- **Low** — "The customer may notice a small change in the UI, but it will not impact their current workflow." e.g. changing a button colour; Save+icon -> icon only.
- **Medium Additive** — "The customer will notice something new, but their existing workflow is unchanged. They may choose to explore it or ignore it." e.g. new tab on existing table; Download button on existing page.
- **Medium Disruptive** — "The customer will notice a change that affects how they complete an existing task. They need to know it is coming before it happens." e.g. moving a button top->side nav; renaming/repurposing a table column.
- **High** — "A major change to an existing workflow, or a significant new feature that introduces an entirely new workflow. The most disruptive tier." e.g. brand-new Maintenance Overview page; redesigning Trips History.

## FF Release Strategy intake form (OCR'd from 1Tg0dv4 — the LCV Speed Limit filled example)

This is the schema of a Feature Flag rollout decision. Fields (with example values):

1. **Feature Description** (Problem -> Solution -> Impact/Outcome) — e.g. "Introducing new type of Speed Limit for Light Commercial Vehicle in MyGeotab. Currently only launched for the UK market."
2. **Customer Impact** — Low / Medium Additive / Medium Disruptive / High (see tiers above).
3. **Roll out to FedRAMP** (if NO, justify) — e.g. No, "no real benefit to fedramp."
4. **Add to public release notes?** (Product Ops does this) — Yes/No.
5. **Accessibility testing completed** — Yes/No/N-A.
6. **Pre-release Testing / UAT across all completed features** — *required for High Impact Customer/Risk Initiatives*. (UAT Pre-launch Template.)
7. **Product Guide reviewed/updated** — submit Technical Writing service request.
8. **Dev Lead** (+ **Manager**) — named people. (HITL routing target for technical gaps.)
9. **Feature Flag Identifier** — naming convention `<COMPONENT>.<DESCRIPTION>.<KILLSWITCH|RELEASE>` e.g. `DATAINGESTION.ENABLE_LCV_SPEED_LIMIT_SUPPORT.RELEASE`.
10. **How was the feature tested & how long** — e.g. "tested by customer in alpha ~2-3 weeks."
11. **Monitoring the rollout** (NEW & MANDATORY) — dashboards (Sentry/Grafana/Superset) + how you'll detect adverse events.
12. **Restart required** (server restart?) — Yes/No.
13. **Feature Flag without Datastore** — Yes/No.
14. **Translations complete** — Yes/No.
15. **Anticipated duration of feature flag** — e.g. "2 weeks."
16. **Feature Flag removal template cloned + linked** (MANDATORY) — FF Removal Template.
17. **Rollout method** — **Fast Rollout** | Slow Rollout.
18. **Product Designer** (if applicable).
19. **Notes.**

## Beta program rules (from 1ttRa)

- **Closed Beta** — invite-only via backend FF; not shown in Beta list; duration = PM discretion. Needs: core functionality complete, use case defined, team assigned, customer consent.
- **Open Beta** — FF toggle OR Beta pill; **8-12 weeks, max 12**. Path A (redesign): toggle in User Preferences, OFF for existing users / ON for new DBs. Path B (net-new): roll to Production with Beta pill. Needs docs, feedback channels, usage tracking, graduation criteria.
- **Experimental** — explicit opt-in FF; **4-12 weeks**; may be pulled anytime; hypothesis-driven; transparent about instability.
- Beta pill + "Send Feedback" required; survey setup needs **48h advance** to research@geotab.com.
- **FF graduation (3 steps)**: beta FF adds User-Options toggle -> `.PROD` FF overrides/removes toggle -> remove both flags to make default.

## Output target — Product Launch one-source-of-truth (from 1aiNZ)

Sections to populate per launch:
- **Project Info** + feature name.
- **Primary Stakeholders**: Group PM, Product Manager, Lead Developer, Product Marketing Manager, Solutions Delivery Manager, Engineering Support (ESUP).
- **Supporting Stakeholders** (Team | role | owner) — auto-fill owners from roster.
- **Marketing Launch Stakeholders** (Team | role | owner).
- **Primary Files & Links**: Product Jira ticket, Dev ticket(s), GTM Jira ticket, FF Rollout ticket, GTM Launch Tracker (the curated+dated checklist), Figma, meeting notes.
- **Positioning Overview**: messaging/positioning, Product Pillar, **Launch Tier + rationale** (PMM recommends).

## JPD field mapping (resolve by NAME at runtime)

- `Launch Level` = `customfield_10556` (stable across MYGJPD + EXPJPD) — GTM Level, often pre-set.
- `Production Target` = `customfield_10562` ({start,end}) — backward-plan anchor.
- `Season` = `customfield_13259` (MYGJPD) — but season is board-specific (HW uses event labels like "Connect 2025"). Take season as a flexible filter: label OR Season field OR free-text.
- Other useful: `FF Customer Impact`, `Impact`, `Merge is behind a Feature Flag`.
- Verified board query: `project = MYGJPD AND issuetype = Idea AND labels = Fall2026 ORDER BY updated DESC` (15+ results, each with Season/Level/Production Target).

## Reasoning chain (agent's brain)

JPD summary -> **customer-impact tier** (4 tiers) -> **release strategy** (FF fast/slow via intake-form logic, or beta track, or code/GA) -> and Launch Level (field or PMM) -> **GTM Level** -> curate checklist by Level + release stage -> **backward-plan** dates on Production Target anchor -> populate launch template. Emit rationale for audit.

## Human-in-the-loop (release-strategy gap-filler)

When release strategy / level / anchor date can't be determined confidently, emit a "Questions for SDM" block naming WHO to ask: **Dev Lead** (FF mechanics/technical), **PM** (release timing/target), **PMM** (level/positioning). Demo cases with `Level = None`: MYGJPD-2830, MYGJPD-3771.

## REMAINING GAP

The explicit **"Your action is your release strategy"** narrative (tier -> recommended rollout method/comms) was NOT in 1Tg0dv4 (that's the FF intake form). Only the 4 tiers table was seen (via screenshot). Agent reasons the mapping from tiers + FF form + beta rules, and routes to SDM when uncertain. Ask Mohamed for this narrative if a deterministic mapping is required.
