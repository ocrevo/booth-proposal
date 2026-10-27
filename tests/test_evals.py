"""Structure tests for the eval cases (phase 5): folder set, file formats, fictional inputs, check coverage and
fixture hashes. Pure stdlib + pytest; the cases are judged by people or by the CLI, not run here."""
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "booth-proposal"
EVALS = SKILL / "evals"
CHECKS = REPO / "tools" / "eval_checks.json"
sys.path.insert(0, str(SKILL / "scripts"))

import common  # noqa: E402

CASES = ["brief-from-rfp", "start-shows-every-stage", "geometry-conflict-caught", "us-inline-line-of-sight",
         "reference-first", "render-text-trap", "failed-fix-blocked", "paraphrased-narration", "no-key",
         "chatgpt-import", "multi-set-free-selection"]
TYPES = {"exists", "absent", "command", "json_equals", "check_clean", "text", "pack_only", "unchanged", "lint_all",
         "geometry_all"}
SETTINGS_KEYS = {"tags", "max_turns", "timeout_seconds", "allowed_tools"}
GRADER_HEAD = "---\ntype: llm\nfocus: trace\nweight: 1\n---\n\n"
BANNED = ["Halvard", "LabWorld", "--out-dir", "View 1", "View 2"]


def _read(path: Path) -> str:
    data = path.read_bytes()
    assert b"\r\n" not in data, f"{path} has CRLF line endings"
    return data.decode("utf-8")


def _settings(text: str):
    m = re.match(r"---\n(.*?)\n---\n\n(.+)\Z", text, re.S)
    assert m, "prompt.md must start with a --- settings block, a blank line and the prompt"
    pairs = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(": ")
        assert key and value, f"bad settings line {line!r}"
        pairs[key] = value
    return pairs, m.group(2)


def test_case_set():
    folders = sorted(p.name for p in EVALS.iterdir() if p.is_dir())
    assert folders == sorted(CASES)


@pytest.mark.parametrize("case", CASES)
def test_case_format(case):
    folder = EVALS / case
    # prompt.md
    settings, body = _settings(_read(folder / "prompt.md"))
    assert set(settings) <= SETTINGS_KEYS, set(settings) - SETTINGS_KEYS
    assert settings.get("tags") == "[booth-proposal]"
    assert settings.get("max_turns", "").isdigit() and settings.get("timeout_seconds", "").isdigit()
    assert re.fullmatch(r"\[[A-Za-z, ]+\]", settings.get("allowed_tools", "")), settings.get("allowed_tools")
    # case.yaml
    cy = _read(folder / "case.yaml")
    lines = cy.splitlines()
    assert lines[0] == 'schema_version: "1.1"'
    assert lines[1] == f"name: {case}"
    assert lines[2] == "expected_outcome: |"
    outcome = []
    for line in lines[3:]:
        if line and not line.startswith("  "):
            break
        outcome.append(line)
    assert any(x.strip() for x in outcome), "expected_outcome is empty"
    assert all(x.startswith("  ") for x in outcome if x), "expected_outcome must be indented"
    # graders
    graders = sorted((folder / "graders").glob("*.md"))
    assert graders, "no graders"
    for g in graders:
        assert re.fullmatch(r"\d\d-[a-z0-9-]+\.md", g.name), g.name
        text = _read(g)
        assert text.startswith(GRADER_HEAD), f"{g.name}: front matter must be exactly the 4-line block"
        assert text[len(GRADER_HEAD):].strip(), f"{g.name}: empty statement"
    # inputs
    files = folder / "files"
    if files.is_dir():
        assert (folder / "place-files.sh").is_file()
        assert re.search(r"^context:\n  scaffold_script: place-files\.sh$", cy, re.M), "scaffold_script missing"
        last = body.rstrip("\n").splitlines()[-1]
        assert last.startswith("Input files: "), last
        listed = re.sub(r"project folder \([^)]*\)", "", last[len("Input files: "):])
        paths = [p.strip() for p in listed.split(",") if p.strip()]
        for p in paths:
            assert (files / p).is_file(), f"listed but missing: {p}"
        inputs = sorted(f.relative_to(files).as_posix() for f in (files / "input").rglob("*") if f.is_file())
        assert sorted(paths) == inputs, "Input files: must list every file under files/input/"
    else:
        assert not (folder / "place-files.sh").exists()
        assert "scaffold_script" not in cy


def test_inputs_fictional():
    docs = [p for name in ("rfp.md", "brochure.md") for p in EVALS.glob(f"*/files/**/{name}")]
    assert len(docs) >= 10
    for p in docs:
        assert _read(p).startswith("> FICTIONAL EXAMPLE."), p
    needles = [n.encode("utf-8") for n in BANNED]
    for p in EVALS.rglob("*"):
        if p.is_file():
            data = p.read_bytes()
            for n in needles:
                assert n not in data, f"{p.relative_to(REPO)} contains {n.decode()!r}"


def test_checks_cover_cases():
    data = json.loads(CHECKS.read_text(encoding="utf-8"))
    assert data["schema"] == "eval-checks/1"
    assert sorted(data["cases"]) == sorted(CASES)
    for case, checks in data["cases"].items():
        assert checks, case
        ids = [c["id"] for c in checks]
        assert ids == [f"{case}-{i:02d}" for i in range(1, len(checks) + 1)], ids
        for c in checks:
            assert c["type"] in TYPES, c


def test_fixtures_current():
    sidecars = [p for p in EVALS.glob("*/files/concepts/**/renders/*.json") if not p.name.endswith(".review.json")]
    reviews = list(EVALS.glob("*/files/concepts/**/renders/*.review.json"))
    assert sidecars and reviews, "fixtures are missing: run python tools/build_eval_fixtures.py --all"
    for sc in sidecars:
        image = sc.with_suffix(".png")
        assert image.is_file(), image
        data = common.read_sidecar(str(image))
        assert data is not None, f"unreadable sidecar {sc}"
        assert data["outputs"], sc
        for name, sha in data["outputs"].items():
            assert common.sha256_file(str(sc.parent / name)) == sha, f"{sc.relative_to(REPO)}: {name} changed"
    for rv in reviews:
        data = json.loads(rv.read_text(encoding="utf-8"))
        image = rv.parent / data["image"]
        assert common.sha256_file(str(image)) == data["sha256"], f"{rv.relative_to(REPO)} is stale"
