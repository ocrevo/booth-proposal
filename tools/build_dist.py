#!/usr/bin/env python3
"""Build dist/booth-proposal.skill deterministically from skills/booth-proposal.

Usage: python tools/build_dist.py [--out dist/booth-proposal.skill] [--skill-dir DIR]
"""
import argparse
import hashlib
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "booth-proposal"
TOP = "booth-proposal"
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".html", ".txt", ".svg", ".css", ".js"}
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}


def check_front_matter(text: str) -> list:
    """Same rules as test_skill_md_frontmatter; returns a list of problems."""
    lines = text.replace("\r", "").split("\n")
    if not lines or lines[0].strip() != "---":
        return ["SKILL.md must start with a front matter block"]
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return ["front matter has no closing ---"]
    fm = {}
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    out = []
    extra = sorted(set(fm) - ALLOWED_KEYS)
    if extra:
        out.append(f"unknown front matter keys: {extra}")
    if fm.get("name") != "booth-proposal":
        out.append("name must be booth-proposal")
    desc = fm.get("description", "")
    if not desc or len(desc) > 1024:
        out.append(f"description must be 1-1024 characters (is {len(desc)})")
    if "<" in desc or ">" in desc:
        out.append("description must not contain < or >")
    if re.search(r"\bthree\b", desc, re.I):
        out.append("description must not contain 'three'")
    return out


def included_files(skill: Path = None) -> list:
    skill = Path(skill) if skill else SKILL
    files = []
    for path in skill.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(skill)
        parts = rel.parts
        if parts[0] == "evals" or "__pycache__" in parts:
            continue
        if any(p.startswith(".") for p in parts):
            continue
        if path.suffix == ".pyc" or path.name in EXCLUDE_NAMES:
            continue
        files.append((f"{TOP}/{rel.as_posix()}", path))
    return sorted(files)


def build(out: Path, skill: Path = None) -> tuple:
    """Write the archive to `out`; return (entry count, sha256)."""
    problems = check_front_matter((Path(skill or SKILL) / "SKILL.md").read_text(encoding="utf-8"))
    if problems:
        print("SKILL.md front matter: " + "; ".join(problems), file=sys.stderr)
        raise SystemExit(1)
    files = included_files(skill)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(out.parent), suffix=".tmp")
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name, path in files:
                data = path.read_bytes()
                if path.suffix in TEXT_SUFFIXES:
                    data = data.replace(b"\r\n", b"\n")
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(tmp, out)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return len(files), hashlib.sha256(out.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the deterministic .skill archive")
    ap.add_argument("--out", default=str(REPO / "dist" / "booth-proposal.skill"))
    ap.add_argument("--skill-dir", default=None, help="skill folder to pack (default: skills/booth-proposal)")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out
    count, digest = build(out, Path(args.skill_dir) if args.skill_dir else None)
    print(f"entries: {count}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
