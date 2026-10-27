"""Anchor tests for the skill documents (phase 4): file set, word budgets, front matter, tables, anchors, stale
strings, every command and flag the docs name, and every error code of the scripts.

Pure stdlib + pytest. The docs describe what the scripts do; when a test fails, fix the docs, not the code."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "booth-proposal"
SCRIPTS = SKILL / "scripts"
REFS = ["1-brief.md", "2-frame.md", "3-ideas.md", "4-renders.md", "5-develop.md", "6-proposal.md", "review.md"]
OLD_REFS = ["art-direction.md", "content-strategy.md", "frame.md", "image-prompts.md", "layout-card.md",
            "proposal-deck.md", "proposal-pack.md", "requirement-card.md", "style-card.md", "venue-card.md"]
SCRIPTS_CMDS = ["render", "gates", "deck", "booth_geometry", "draw_plan"]
CODE_IN_PY = r"""["']((?:GEO|C|L|R|G|D|X)-[A-Z][A-Z0-9-]*)["']"""
CODE_IN_DOC = r"\b((?:GEO|C|L|R|G|D|X)-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)\b"
DOCS = ["SKILL.md"] + ["references/" + r for r in REFS]

ANCHORS = {
    "SKILL.md": ["gates.py select", "step mode", "one stop", "--chosen-all", "## Reference sets", "input/refs/",
                 "concepts/<set>/<concept>/", "brief/selection.json", "pack/proposal.html", "deck.py export",
                 "--project", "render.py import", "OPENAI_API_KEY", "work/"],
    "references/1-brief.md": ["brief/brief.json", "gates.py brief", "design_points", "claims", "protected_terms",
                              "do_not_mention", "gates.py report brief", "exhibitor manual"],
    "references/2-frame.md": ["gates.py frame", "booth.program", "Area budget", "Depth budget", "height_zones",
                              "rigging_allowed"],
    "references/3-ideas.md": ["brief/ideas.json", "booth_type", "a gate you walk through", "gates.py brief --stamp",
                              "gates.py ideas --scaffold", "gates.py report ideas", "no-swap test"],
    "references/4-renders.md": ["--dry-run", "401", "403", "429", "400", "Never start a second call",
                                "| Problem | Correction sentence |", "Known habits", "render.py lint",
                                "render.py import", "render.py tiles", "render.py sheet", "render.py logo",
                                "assets/prompts/fixed.json", "fix_max", "timeout"],
    "references/5-develop.md": ["booth_geometry.py check", "draw_plan.py plan", "booth_geometry.py facts",
                                "envelope_override", "gates.py concepts", "massing", "geometry_tol"],
    "references/6-proposal.md": ["deck/storyboard.md", "deck.py layouts --emit", "deck.py check --json",
                                 "deck.py render", "deck.py text --diff", "deck.py review --record",
                                 "deck.py export", "data-role", "data-claim", "data-ref", "figure.render",
                                 "work/deck-review.input.json", "pack/proposal.pdf"],
    "references/review.md": ["legible_text", "logo_like", "pseudo_text", "composited_logo", "premium",
                             "render.py review", "--scope full", "Pass 1", "Pass 2", "\"self\"", "render.py sheet",
                             "work/deck-review.input.json"],
}
STALE = ["--out-dir", "check.txt", "pack/preview", "pack/boards", "deck-backups", "A-1-hero", "A-2-front",
         "Do-not-mention", "style-cards.md", "design-points.md", "deck/plan.json", "deck_build", "View 1", "View 2",
         "Detail view", "halvard", "Halvard", "LabWorld", "starts from somewhere else", "at least one concept starts",
         "at least one concept not", "at least one of the three", "three clearly different", "new --lead",
         "prompt-pack", "Intensity", "Supporting system", "Built from:", "built_from", "signature_names", "75-inch",
         "--tool", "report frame", "concepts_per_set"]


def words(text: str) -> int:
    return len(text.split())


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r", "")


def doc_text(rel: str) -> str:
    return read(SKILL / rel)


def front_matter(text: str) -> dict:
    """Unindented `key: value` lines between the first two `---` lines."""
    lines = text.split("\n")
    assert lines and lines[0].strip() == "---", "SKILL.md must start with a front matter block"
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    assert end is not None, "front matter has no closing ---"
    out = {}
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def first_table(text: str, heading: str) -> list:
    """First cells of the body rows of the first markdown table under `heading`, backticks removed."""
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == heading), None)
    assert start is not None, f"no {heading} section"
    rows = []
    in_table = False
    for ln in lines[start + 1:]:
        if ln.startswith("## ") and not in_table:
            break
        if ln.strip().startswith("|"):
            in_table = True
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))]
            rows.append(cells)
        elif in_table:
            break
    assert len(rows) >= 3, f"no table under {heading}"
    body = [r for r in rows[1:] if not all(re.fullmatch(r":?-{2,}:?", c) for c in r if c)]
    return [r[0].replace("`", "").strip() for r in body]


def test_reference_files_exact():
    names = sorted(p.name for p in (SKILL / "references").glob("*.md"))
    assert names == sorted(REFS)
    for old in OLD_REFS:
        assert not (SKILL / "references" / old).exists(), old
    assert not (SKILL / "assets" / "examples").exists()


def test_word_budgets():
    assert words(doc_text("SKILL.md")) <= 1800
    total = sum(words(doc_text("references/" + r)) for r in REFS)
    assert total <= 12000, total


def test_skill_md_frontmatter():
    fm = front_matter(doc_text("SKILL.md"))
    allowed = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
    assert set(fm) <= allowed, sorted(set(fm) - allowed)
    assert fm.get("name") == "booth-proposal"
    desc = fm.get("description", "")
    assert desc and len(desc) <= 1024, len(desc)
    assert "<" not in desc and ">" not in desc
    assert not re.search(r"\bthree\b", desc, re.I)


@pytest.mark.parametrize("which", ["flow", "platforms", "commands"])
def test_skill_md_tables(which):
    text = doc_text("SKILL.md")
    if which == "flow":
        cells = first_table(text, "## Flow")
        assert cells == ["1 Brief", "2 Frame", "3 Ideas", "4 Renders", "5 Develop", "6 Proposal"]
    elif which == "platforms":
        cells = first_table(text, "## Platforms")
        assert cells == ["Claude Code", "Codex", "ChatGPT", "Claude.ai"]
    else:
        cells = first_table(text, "## Commands")
        for name in ["start", "step mode", "change", "add set", "select", "show", "render", "pack", "status"]:
            assert any(c.startswith(name) for c in cells), f"no command row starting with {name!r}: {cells}"


def test_reference_rule_once():
    skill = doc_text("SKILL.md")
    assert skill.count("## Reference sets") == 1
    assert skill.count("never shown or narrated") == 1
    for r in REFS:
        assert doc_text("references/" + r).count("never shown or narrated") == 0, r


@pytest.mark.parametrize("rel", list(ANCHORS), ids=list(ANCHORS))
def test_anchors(rel):
    text = doc_text(rel)
    missing = [a for a in ANCHORS[rel] if a not in text]
    assert not missing, missing


@pytest.mark.parametrize("rel", DOCS, ids=DOCS)
def test_stale_strings_absent(rel):
    text = doc_text(rel)
    found = [s for s in STALE if s in text]
    assert not found, found


_HELP_CACHE = {}


def _help(script: str, sub=None) -> str:
    key = (script, sub)
    if key not in _HELP_CACHE:
        cmd = [sys.executable, str(SCRIPTS / (script + ".py"))] + ([sub] if sub else []) + ["--help"]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        _HELP_CACHE[key] = (r.stdout or "") + (r.stderr or "")
    return _HELP_CACHE[key]


def test_doc_references_exist():
    problems = []
    cmd_re = re.compile(r"\b(" + "|".join(SCRIPTS_CMDS) + r")\.py\s+([a-z][a-z-]*)([^`|\n]*)")
    for rel in DOCS:
        text = doc_text(rel)
        for m in re.finditer(r"references/[\w-]+\.md|assets/[\w./-]+\.(?:json|html)", text):
            if not (SKILL / m.group(0)).exists():
                problems.append(f"{rel}: missing path {m.group(0)}")
        for m in cmd_re.finditer(text):
            script, sub, rest = m.group(1), m.group(2), m.group(3)
            top = _help(script)
            choices = re.search(r"\{([^}]+)\}", top)
            names = choices.group(1).split(",") if choices else []
            if sub not in names:
                problems.append(f"{rel}: {script}.py has no command {sub!r} (choices {names})")
                continue
            sub_help = _help(script, sub)
            for flag in re.findall(r"--[a-z][a-z-]*", rest):
                if flag in ("--project", "--help"):
                    continue
                if flag not in sub_help:
                    problems.append(f"{rel}: {script}.py {sub} has no flag {flag}")
    assert not problems, "\n".join(sorted(set(problems)))


def test_codes_documented():
    py_codes = set()
    for p in SCRIPTS.glob("*.py"):
        py_codes |= set(re.findall(CODE_IN_PY, read(p)))
    assert py_codes, "no codes found in the scripts"
    per_doc = {rel: set(re.findall(CODE_IN_DOC, doc_text(rel))) for rel in DOCS}
    all_doc = set().union(*per_doc.values())
    problems = []
    for code in sorted(py_codes):
        if code.startswith(("D-", "X-")):
            if code not in per_doc["references/6-proposal.md"]:
                problems.append(f"{code} not in 6-proposal.md")
        elif code.startswith(("L-", "R-")):
            if code not in per_doc["references/4-renders.md"] | per_doc["references/review.md"]:
                problems.append(f"{code} not in 4-renders.md or review.md")
        elif code.startswith("GEO-"):
            if code not in per_doc["references/5-develop.md"]:
                problems.append(f"{code} not in 5-develop.md")
        elif code.startswith(("G-", "C-")):
            if code not in all_doc:
                problems.append(f"{code} in no document")
    for code in sorted(all_doc - py_codes):
        problems.append(f"{code} is documented but no script uses it")
    assert not problems, "\n".join(problems)
