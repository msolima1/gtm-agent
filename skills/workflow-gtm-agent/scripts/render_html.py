#!/usr/bin/env python3
"""
render_html.py — Render a GTM season plan into a single self-contained HTML page.

V0: content meaningful and visible (not yet polished). The page is ACTIONABLE — every
gap / human-in-the-loop item is highlighted at the top and inline so the SDM knows what
to resolve to firm up the plan.

Input: plan.py JSON output (mode season). Optionally carries, per JPD:
  - "gates": ["PM must test with 10 users before open beta", ...]  (from the reasoning step)
  - "questions_for_sdm": [...]
These are auto-augmented with deterministic gaps (assumed anchors, missing levels, TBD owners).

Usage:
  python3 plan.py --curated-file curated.json --output json > plan.json
  python3 render_html.py --plan-file plan.json --out gtm_plan.html
"""
import argparse, html, json, os, sys

NAVY="#003B5C"; BLUE="#0072CE"; LIGHT="#00A3E0"; ORANGE="#E87722"
RED="#d93025"; AMBER="#f59e0b"; GREEN="#22c55e"; GREY="#5f6b7a"

def esc(s): return html.escape(str(s if s is not None else ""))

def placeholder_owner(o):
    o = (o or "").lower()
    return (not o) or ("unassigned" in o) or o.startswith("from jpd") or "ask sdm" in o or "delegate" in o or "team" == o.split()[-1:] and False

def collect_gaps(plan):
    """Return (items, summaries). items = distinct actionable (severity,key,text);
    summaries = one-liners for repetitive gaps so the banner doesn't spam."""
    items, summaries = [], []
    assumed = [p["key"] for p in plan.get("planned", []) if p.get("anchor_assumed")]
    # distinct, real human-in-the-loop items
    for p in plan.get("planned", []):
        k = p["key"]
        for g in p.get("gates", []):
            items.append(("high", k, g))
        for q in p.get("questions_for_sdm", []):
            items.append(("med", k, q))
    for n in plan.get("needs_sdm", []):
        items.append(("high", n.get("key"), f"No GTM level set — ask PMM to set Launch Tier"))
    for u in plan.get("unplanned", []):
        items.append(("high", u.get("key"), f"Cannot date plan — {u.get('reason','')}"))
    # repetitive gaps -> single summary lines
    if assumed:
        d = plan["planned"][0].get("anchor_date") if plan.get("planned") else ""
        summaries.append(f"{len(assumed)} of {len(plan.get('planned',[]))} JPDs have no target date — "
                         f"dated from assumed end-of-season; confirm real release dates with PM.")
    return items, summaries

def badge(text, color, fg="#fff"):
    return f'<span style="background:{color};color:{fg};border-radius:10px;padding:2px 9px;font-size:11px;font-weight:600;white-space:nowrap">{esc(text)}</span>'

def _squad(ps):
    """Header line of the named pillar squad (primary stakeholders) from the roster."""
    if not ps: return ""
    label = {"product_leader":"Product Leader","product_manager":"PM","design_leader":"Design",
             "sdm":"SDM","product_marketing":"Product Mktg","sol_eng":"Sol Eng","esup":"ESUP"}
    parts = [f"{lab}: {esc(ps[k])}" for k,lab in label.items() if ps.get(k)]
    if not parts: return ""
    return ('<div style="margin-top:8px;font-size:12px;opacity:.85">Squad &nbsp;'
            + " &nbsp;|&nbsp; ".join(parts) + "</div>")

def _banner(summaries, high, med, gap_rows):
    """Concise action banner: one-line summaries for repetitive gaps + distinct items only."""
    n = len(high) + len(med)
    sum_html = "".join(f'<div style="font-size:13px;margin:3px 0;color:{NAVY}">• {esc(s)}</div>' for s in summaries)
    parts = []
    if high:
        parts.append(f'<div style="font-weight:700;color:{RED};font-size:14px;margin-top:6px">Needs a decision ({len(high)})</div>'
                     f'<ul style="list-style:none;padding:0;margin:6px 0">{gap_rows(high)}</ul>')
    if med:
        parts.append(f'<div style="font-weight:700;color:{AMBER};font-size:14px;margin-top:6px">Follow-ups ({len(med)})</div>'
                     f'<ul style="list-style:none;padding:0;margin:6px 0">{gap_rows(med)}</ul>')
    title = f"⚠ Action needed to firm up this plan ({n})" if n else "Plan summary — confirm assumptions"
    color = RED if n else AMBER
    return (f'<div style="background:#fff;border:2px solid {color};border-radius:10px;padding:16px;margin:16px 0">'
            f'<div style="font-weight:700;color:{color};font-size:15px">{title}</div>'
            f'{sum_html}{"".join(parts)}</div>')

def render(plan):
    proj=esc(plan.get("project")); season=esc(plan.get("season"))
    planned=plan.get("planned",[])
    n_assumed=sum(1 for p in planned if p.get("anchor_assumed"))
    items, summaries = collect_gaps(plan)
    high=[g for g in items if g[0]=="high"]; med=[g for g in items if g[0]=="med"]

    def gap_rows(items):
        out=[]
        for sev,k,txt in items:
            dot=RED if sev=="high" else AMBER
            out.append(f'<li style="margin:4px 0"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{dot};margin-right:8px"></span>'
                       f'<b style="color:{NAVY}">{esc(k)}</b> &nbsp;{esc(txt)}</li>')
        return "\n".join(out) or '<li style="color:%s">None</li>'%GREEN

    cards=[]
    for p in planned:
        assumed = p.get("anchor_assumed")
        anchor_badge = badge(f"release {p['anchor_date']}" + (" • ASSUMED" if assumed else ""),
                             AMBER if assumed else GREEN, "#3a2c00" if assumed else "#053")
        rows=[]
        for t in p.get("teams",[]):
            own=t.get("owner",""); own_flag = ' '+badge("owner TBD",ORANGE) if placeholder_owner(own) else ""
            tasks="".join(f"<li>{esc(x.get('task'))}</li>" for x in t.get("tasks",[])[:8])
            more = f"<li style='color:{GREY}'>+{len(t['tasks'])-8} more…</li>" if len(t.get('tasks',[]))>8 else ""
            cat=t.get("category","")
            catcolor={"primary":BLUE,"supporting":LIGHT,"launch":ORANGE}.get(cat,GREY)
            rows.append(f"""<tr>
              <td style="white-space:nowrap">{badge(cat,catcolor)}</td>
              <td><b>{esc(t['team'])}</b><br><span style="color:{GREY};font-size:12px">{esc(own)}{own_flag}</span></td>
              <td style="white-space:nowrap;font-variant-numeric:tabular-nums">{esc(t.get('start_date'))}<br><span style="color:{GREY}">→ {esc(t.get('due_date'))}</span></td>
              <td style="text-align:center">{t.get('task_count')}</td>
              <td><ul style="margin:0 0 0 16px;padding:0;font-size:12.5px">{tasks}{more}</ul></td>
            </tr>""")
        jpd_gates=[g for g in items if g[1]==p["key"]]
        gate_html = ""
        if jpd_gates:
            gate_html = '<div style="background:#fff5f0;border-left:4px solid %s;padding:8px 12px;margin:8px 0;border-radius:4px">'%RED \
                + "".join(f'<div style="font-size:13px;margin:2px 0">⚠ {esc(t)}</div>' for _,_,t in jpd_gates) + "</div>"
        cards.append(f"""<div style="background:#fff;border:1px solid #e3e8ee;border-radius:10px;padding:16px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.05)">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
            <div style="font-size:16px;font-weight:700;color:{NAVY}">{esc(p['key'])} — {esc(p['summary'])}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">{badge('Level '+str(p['level']),NAVY)} {badge(p.get('release_strategy',''),BLUE)} {anchor_badge}</div>
          </div>
          <div style="color:{GREY};font-size:13px;margin:6px 0">Kick off GTM by <b style="color:{ORANGE}">{esc(p['kickoff_by'])}</b></div>
          {gate_html}
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead><tr style="text-align:left;color:{GREY};border-bottom:2px solid #eef2f6">
              <th>Stage</th><th>Team / owner</th><th>Window</th><th>#</th><th>What they own</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
        </div>""")

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>GTM Plan — {proj} / {season}</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f4f6f9;color:#1a2430}}
.wrap{{max-width:1080px;margin:0 auto;padding:24px}} table td,table th{{padding:8px;vertical-align:top;border-bottom:1px solid #f0f3f7}}
h1{{margin:0;font-size:22px}} a{{color:{BLUE}}}</style></head><body>
<div style="background:{NAVY};color:#fff;padding:20px 0"><div class="wrap">
  <h1>GTM Plan — {proj} <span style="color:{LIGHT}">/ {season}</span>{(' <span style="color:'+ORANGE+'">• '+esc(plan.get('pillar'))+'</span>') if plan.get('pillar') else ''}</h1>
  <div style="opacity:.85;font-size:13px;margin-top:6px">
    {len(planned)} JPDs planned &nbsp;•&nbsp; {n_assumed} on assumed season-end anchor &nbsp;•&nbsp;
    {len(high)+len(med)} action items
  </div>
  {_squad(plan.get('pillar_stakeholders'))}
  </div></div>
<div class="wrap">
  {_banner(summaries, high, med, gap_rows)}
  {''.join(cards)}
  <div style="color:{GREY};font-size:12px;margin:24px 0">Generated by workflow-gtm-agent. Assumed anchors and gates above are not final — confirm with PM/PMM/Dev Lead.</div>
</div></body></html>"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--plan-file", required=True)
    ap.add_argument("--out", default="gtm_plan.html")
    a=ap.parse_args()
    plan=json.load(open(a.plan_file))
    if "planned" not in plan:
        sys.exit("ERROR: --plan-file must be plan.py JSON output (needs 'planned').")
    htmlout=render(plan)
    open(a.out,"w",encoding="utf-8").write(htmlout)
    print(f"Wrote {a.out} ({len(htmlout)} bytes) — {len(plan['planned'])} JPDs, "
          f"{sum(1 for p in plan['planned'] if p.get('anchor_assumed'))} assumed anchors.")

if __name__=="__main__":
    main()
