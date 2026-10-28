"""Release checks: deterministic dist build, metadata, README, repository hygiene."""
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import common

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import build_dist  # noqa: E402

DIST = REPO / "dist" / "booth-proposal.skill"
STALE = ["--out-dir", "check.txt", "pack/preview", "pack/boards", "deck-backups", "A-1-hero", "A-2-front",
         "Do-not-mention", "style-cards.md", "design-points.md", "deck/plan.json", "deck_build", "View 1", "View 2",
         "Detail view", "halvard", "Halvard", "LabWorld", "starts from somewhere else", "at least one concept starts",
         "at least one concept not", "at least one of the three", "three clearly different", "new --lead",
         "prompt-pack", "Intensity", "Supporting system", "Built from:", "built_from", "signature_names", "75-inch",
         "--tool", "report frame", "concepts_per_set"]


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r", "")


def test_dist_build(tmp_path):
    a, b = tmp_path / "a" / "x.skill", tmp_path / "b" / "x.skill"
    build_dist.build(a)
    build_dist.build(b)
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as z:
        names = z.namelist()
    for need in ["SKILL.md", "scripts/common.py", "scripts/gates.py", "scripts/deck.py",
                 "assets/deck/template.html", "assets/labels/zh.json", "assets/prompts/lint.json",
                 "assets/architectures/tender.json",
                 "references/review.md"]:
        assert f"booth-proposal/{need}" in names, need
    assert not any(n.startswith("booth-proposal/evals/") for n in names)
    assert not any("__pycache__" in n or "halvard" in n.lower() for n in names)


def test_dist_skips_hidden_dirs(tmp_path):
    skill = tmp_path / "skill"
    shutil.copytree(build_dist.SKILL, skill, ignore=shutil.ignore_patterns("evals", "__pycache__", ".*"))
    base = build_dist.included_files(skill)
    (skill / "scripts" / ".ruff_cache").mkdir()
    (skill / "scripts" / ".ruff_cache" / "CACHEDIR.TAG").write_text("x", encoding="utf-8")
    (skill / ".hidden").mkdir()
    (skill / ".hidden" / "note.md").write_text("x", encoding="utf-8")
    (skill / "references" / ".draft.md").write_text("x", encoding="utf-8")
    assert [n for n, _ in build_dist.included_files(skill)] == [n for n, _ in base]
    out = tmp_path / "x.skill"
    count, _ = build_dist.build(out, skill)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert count == len(names) == len(base)
    assert not any("/." in n for n in names), names
    assert build_dist.main(["--out", str(tmp_path / "y.skill"), "--skill-dir", str(skill)]) == 0


def test_dist_is_current(tmp_path):
    fresh = tmp_path / "fresh.skill"
    build_dist.build(fresh)
    assert DIST.read_bytes() == fresh.read_bytes(), "run: python tools/build_dist.py"


def test_release_metadata():
    plugin = json.loads(read(REPO / ".claude-plugin" / "plugin.json"))
    market = json.loads(read(REPO / ".claude-plugin" / "marketplace.json"))
    assert plugin["version"] == "0.6.0"
    first = next(ln for ln in read(REPO / "CHANGELOG.md").split("\n") if ln.startswith("## "))
    assert first.startswith("## 0.6.0 – ")
    yaml_text = read(REPO / "skills" / "booth-proposal" / "agents" / "openai.yaml")
    short = re.search(r'short_description:\s*"([^"]*)"', yaml_text).group(1)
    for d in [plugin["description"], market["plugins"][0]["description"], short]:
        assert d and not re.search(r"\bthree\b", d, re.I), d


def test_readme():
    text = read(REPO / "README.md")
    letters = "".join(ch for ch in text if ch.isalpha())
    assert common.cjk_ratio(letters) > 0.3
    for need in ["gates.py select", "input/refs/", "deck.py export"]:
        assert need in text, need
    assert "assets/examples" not in text
    assert [s for s in STALE if s in text] == []


def test_repo_hygiene():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                             check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git not available")
    files = [ln for ln in out.split("\n") if ln.strip()]
    assert not [f for f in files if f.startswith(("input/", "output/"))]
    assert not [f for f in files if f.split("/")[-1] == ".env"]
    ignore = read(REPO / ".gitignore").split("\n")
    for need in [".env", "input/", "output/"]:
        assert need in ignore, need
    attrs = read(REPO / ".gitattributes").split("\n")
    for need in ["skills/booth-proposal/evals/*/files/** -text", "dist/*.skill binary"]:
        assert need in attrs, need
