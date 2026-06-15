#!/usr/bin/env python3
"""
list_jpds.py — Filter a JPD/Polaris board by season and extract GTM-relevant fields.

Board-agnostic: resolves custom field IDs BY NAME at runtime (Launch Level,
Production Target, Season) so it works on MYGJPD, EXPJPD, Safety, HW, etc.
Season is flexible: a label (e.g. Fall2026), a Season-field value (e.g. "Fall 2026"),
or free text — we try label first, then the Season field, then a text contains.

Auth: ~/jira.json  {"email","token","base_url"}

Usage:
  python3 list_jpds.py --project MYGJPD --season "Fall 2026"
  python3 list_jpds.py --project EXPJPD --season "Connect 2025" --max 50
  python3 list_jpds.py --project MYGJPD --season Fall2026 --output table

Output: JSON list (default) of {key, summary, launch_level, level_source,
production_target, season, behind_ff, assignee, url}. Use --output table for humans.
"""
import argparse, json, os, sys, urllib.parse, urllib.request

def creds():
    p = os.path.expanduser("~/jira.json")
    if not os.path.exists(p):
        sys.exit("ERROR: ~/jira.json not found. Set up Jira auth first (util-auth).")
    c = json.load(open(p))
    return c["email"], c["token"], c["base_url"].rstrip("/")

def api(base, email, token, path, params=None):
    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    import base64
    tok = base64.b64encode(f"{email}:{token}".encode()).decode()
    req.add_header("Authorization", "Basic " + tok)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def field_map(base, email, token):
    """name(lower) -> id"""
    fields = api(base, email, token, "/rest/api/3/field")
    m = {}
    for f in fields:
        m.setdefault(f["name"].strip().lower(), f["id"])
    return m

def fid(fmap, name, default=None):
    return fmap.get(name.strip().lower(), default)

def val(v):
    if v is None: return None
    if isinstance(v, dict):
        return v.get("value") or v.get("name") or v.get("displayName") or v
    if isinstance(v, list):
        return [val(x) for x in v]
    return v

def as_daterange(v):
    """Production Target may arrive as a JSON string '{"start":..,"end":..}' or a dict."""
    if v is None: return None
    if isinstance(v, str):
        try: v = json.loads(v)
        except Exception: return v
    return v if isinstance(v, dict) else None

def search(base, email, token, jql, fields, mx):
    out, token_pg = [], None
    while len(out) < mx:
        params = {"jql": jql, "maxResults": min(100, mx - len(out)),
                  "fields": ",".join(fields)}
        if token_pg: params["nextPageToken"] = token_pg
        d = api(base, email, token, "/rest/api/3/search/jql", params)
        out.extend(d.get("issues", []))
        token_pg = d.get("nextPageToken")
        if d.get("isLast") or not token_pg or not d.get("issues"):
            break
    return out[:mx]

def build_jql(project, season, season_fid):
    label = season.replace(" ", "")
    clauses = [f'project = "{project}"', "issuetype = Idea"]
    season_clauses = [f'labels = "{label}"']
    if season_fid:
        season_clauses.append(f'"{season_fid}" = "{season}"')
    # text fallback (Polaris description/summary mentions)
    clauses.append("(" + " OR ".join(season_clauses) + ")")
    return " AND ".join(clauses) + " ORDER BY updated DESC"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--season", required=True)
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--output", choices=["json", "table"], default="json")
    a = ap.parse_args()

    email, token, base = creds()
    fmap = field_map(base, email, token)
    f_level = fid(fmap, "Launch Level")
    f_prod  = fid(fmap, "Production Target")
    f_season= fid(fmap, "Season")
    f_ff    = fid(fmap, "Merge is behind a Feature Flag")

    jql = build_jql(a.project, a.season, f_season)
    wanted = ["summary", "assignee", "labels"]
    for x in (f_level, f_prod, f_season, f_ff):
        if x: wanted.append(x)

    try:
        issues = search(base, email, token, jql, wanted, a.max)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: Jira search failed ({e.code}). JQL was: {jql}\n{e.read().decode()[:400]}")

    rows = []
    for i in issues:
        f = i.get("fields", {})
        lvl = val(f.get(f_level)) if f_level else None
        rows.append({
            "key": i["key"],
            "summary": f.get("summary"),
            "launch_level": lvl,
            "level_source": "field:Launch Level" if lvl else "MISSING -> infer or ask SDM",
            "production_target": as_daterange(f.get(f_prod)) if f_prod else None,
            "season": val(f.get(f_season)) if f_season else None,
            "behind_ff": val(f.get(f_ff)) if f_ff else None,
            "assignee": (f.get("assignee") or {}).get("displayName") if f.get("assignee") else None,
            "labels": f.get("labels"),
            "url": f"{base}/browse/{i['key']}",
        })

    if not rows:
        # Self-service: show what seasons/labels actually exist on this board.
        try:
            probe = search(base, email, token,
                           f'project = "{a.project}" AND issuetype = Idea ORDER BY updated DESC',
                           ["labels"] + ([f_season] if f_season else []), 60)
            labels, seasons = set(), set()
            for i in probe:
                f = i.get("fields", {})
                for l in (f.get("labels") or []): labels.add(l)
                if f_season and f.get(f_season): seasons.add(str(val(f.get(f_season))))
            hint = {"message": f"No JPDs matched season '{a.season}' on {a.project}.",
                    "season_field_values_seen": sorted(seasons),
                    "labels_seen_sample": sorted(labels)[:40],
                    "jql_tried": jql}
            if a.output == "table":
                print(hint["message"])
                if seasons: print("Season field values on this board:", ", ".join(hint["season_field_values_seen"]))
                print("Labels on this board (sample):", ", ".join(hint["labels_seen_sample"]))
            else:
                print(json.dumps(hint, indent=2))
            return
        except Exception:
            pass

    if a.output == "table":
        print(f"{len(rows)} JPDs in {a.project} / season '{a.season}'\n")
        print(f"{'KEY':14} {'LEVEL':10} {'ANCHOR':24} SUMMARY")
        for r in rows:
            pt = r["production_target"]
            anchor = (pt.get("start","?")+".."+pt.get("end","?")) if isinstance(pt, dict) else "(none)"
            print(f"{r['key']:14} {str(r['launch_level'] or '-'):10} {anchor:24} {(r['summary'] or '')[:50]}")
        missing = [r["key"] for r in rows if not r["launch_level"] or not r["production_target"]]
        if missing:
            print(f"\nNeeds SDM input (missing level or anchor): {', '.join(missing)}")
    else:
        print(json.dumps({"project": a.project, "season": a.season, "jql": jql,
                          "count": len(rows), "jpds": rows}, indent=2, default=str))

if __name__ == "__main__":
    main()
