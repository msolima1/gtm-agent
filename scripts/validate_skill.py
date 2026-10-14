#!/usr/bin/env python3
"""Validate SKILL.md files for correctness."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

FRONTMATTER_RE = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n([\s\S]*))?", re.DOTALL)
NAME_RE = re.compile(r"^[a-z0-9-_]+$")


def infer_name(skill_path: Path, root: Path) -> str:
    rel = skill_path.resolve().relative_to(root.resolve()).parts
    if len(rel) == 1 and rel[0] == "SKILL.md":
        n = root.resolve().name
        return n[len("skill-"):] if n.startswith("skill-") else n
    if len(rel) >= 3 and rel[0] == "skills" and rel[-1] == "SKILL.md":
        return rel[1]
    raise ValueError(f"cannot infer skill name for {skill_path}")


def discover(root: Path) -> list[Path]:
    files: list[Path] = []
    if (root / "SKILL.md").exists():
        files.append(root / "SKILL.md")
    if (root / "skills").exists():
        files.extend((root / "skills").rglob("SKILL.md"))
    return sorted({p.resolve() for p in files})


def validate(path: Path, expected: str | None = None) -> list[str]:
    if yaml is None:
        return ["PyYAML required in the active Python environment"]
    if not path.exists():
        return [f"not found: {path}"]
    errs: list[str] = []
    content = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(content)
    if not m:
        return ["missing or invalid YAML frontmatter"]
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception as e:
        return [f"invalid YAML: {e}"]
    if not isinstance(fm, dict):
        return [f"frontmatter must be a mapping (got {type(fm).__name__})"]
    name = fm.get("name")
    desc = fm.get("description")
    if not isinstance(name, str) or not name.strip():
        errs.append("missing required field: name")
    elif not NAME_RE.fullmatch(name):
        errs.append(f"invalid name slug: {name!r}")
    elif expected and name != expected:
        errs.append(f"name mismatch: expected {expected!r}, got {name!r}")
    if not isinstance(desc, str) or not desc.strip():
        errs.append("missing required field: description")
    body = (m.group(2) or "").strip()
    if not body:
        errs.append("no content after frontmatter")
    elif not re.search(r"^#\s+", body, re.MULTILINE):
        errs.append("no markdown heading found")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate SKILL.md")
    ap.add_argument("path", nargs="?", default="SKILL.md")
    ap.add_argument("--name")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    if args.all:
        root = Path(".").resolve()
        files = discover(root)
        if not files:
            print("no SKILL.md files found"); return 1
        ok = True
        for f in files:
            try:
                exp = infer_name(f, root)
            except ValueError as e:
                print(f"FAIL: {e}"); ok = False; continue
            for err in validate(f, exp):
                print(f"FAIL: {f}: {err}"); ok = False
        if ok and not args.quiet:
            print(f"OK: validated {len(files)} file(s)")
        return 0 if ok else 1

    p = Path(args.path)
    errs = validate(p, args.name)
    if errs:
        print(f"FAIL: {p}")
        for e in errs:
            print(f"  - {e}")
        return 1
    if not args.quiet:
        print(f"OK: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
