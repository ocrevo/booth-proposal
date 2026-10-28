"""Structure tests for the eval cases (phase 5): folder set, file formats, fictional inputs, check coverage and
fixture hashes. Pure stdlib + pytest; the cases are judged by people or by the CLI, not run here."""
import json
import re
import shutil
import subprocess
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
         "chatgpt-import", "multi-set-free-selection", "tender-default", "showcase-explicit"]
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


# ---------- architectures: every fixture project is valid under the architecture it names ----------

# case -> proposal.architecture written in the fixture brief (None: not written, the default applies)
ARCH_OF_FIXTURE = {"failed-fix-blocked": "showcase", "paraphrased-narration": "showcase",
                   "multi-set-free-selection": "showcase", "chatgpt-import": None, "tender-default": None,
                   "showcase-explicit": None}


def _copy(case: str, tmp_path: Path) -> Path:
    """A copy of the case's fixture project: the commands write work/ and the fixture must stay as built."""
    dest = tmp_path / case
    shutil.copytree(EVALS / case / "files", dest)
    return dest


def _skill(script: str, *args: str):
    return subprocess.run([sys.executable, str(SKILL / "scripts" / script), *args], capture_output=True, text=True,
                          encoding="utf-8", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})


@pytest.mark.parametrize("case", sorted(ARCH_OF_FIXTURE))
def test_fixture_architecture(case, tmp_path):
    project = _copy(case, tmp_path)
    brief = json.loads((project / "brief" / "brief.json").read_text(encoding="utf-8"))
    want = ARCH_OF_FIXTURE[case]
    assert (brief.get("proposal") or {}).get("architecture") == want
    run = _skill("gates.py", "brief", "--project", str(project))
    assert run.returncode == 0, run.stdout + run.stderr
    shown = _skill("gates.py", "architectures", "--json", "--project", str(project))
    assert json.loads(shown.stdout)["current"] == (want or "tender")


def test_paraphrased_deck_is_valid_under_showcase(tmp_path):
    """The planted findings are the only ones: no structure, chapter or separate-page finding."""
    project = _copy("paraphrased-narration", tmp_path)
    run = _skill("deck.py", "check", "--json", "--project", str(project))
    findings = json.loads(run.stdout)["findings"]
    codes = {f["code"] for f in findings}
    assert codes == {"D-TXT-PENDING", "D-IMG-FORBIDDEN", "D-IMG-URL"}, codes


@pytest.mark.parametrize("case", ["tender-default", "showcase-explicit"])
def test_tender_fixture_brief(case, tmp_path):
    project = _copy(case, tmp_path)
    brief = json.loads((project / "brief" / "brief.json").read_text(encoding="utf-8"))
    kinds = [c["kind"] for c in brief["clauses"]]
    flat = {k for kind in kinds for k in (kind if isinstance(kind, list) else [kind])}
    assert {"design", "interaction", "execution", "price"} <= flat
    assert any(isinstance(k, list) and set(k) == {"design", "execution"} for k in kinds), "no mixed clause"
    assert {d["kind"] for d in brief["deliverables"]} >= {"design", "graphics", "execution", "price"}
    assert [g["id"] for g in brief["graphics"]] == ["GR1"]
    assert all(not any(ch.isdigit() for ch in c.get("title", "")) for c in brief["clauses"])
    # the graphic prompt passes lint, the images made elsewhere are there and the graphic has the brief ratio
    lint = _skill("render.py", "lint", "--mode", "graphic", "--prompt", str(project / "graphics" / "GR1" / "prompts" / "graphic.txt"),
                  "--graphic", "GR1", "--area", "top", "--project", str(project))
    assert lint.returncode == 0, lint.stdout + lint.stderr
    for name in ("set-1-A-1", "set-1-A-2", "set-1-B-1", "GR1-1"):
        assert (project / "incoming" / f"{name}.png").is_file(), name
    from PIL import Image
    with Image.open(project / "incoming" / "GR1-1.png") as im:
        assert im.size == (1024, 1536)


def test_new_cases_check_the_architecture():
    data = json.loads(CHECKS.read_text(encoding="utf-8"))["cases"]
    pick = lambda case: [c for c in data[case] if c["type"] == "json_equals" and c.get("key") == "proposal.architecture"]
    for case in ("showcase-explicit", "failed-fix-blocked", "paraphrased-narration", "multi-set-free-selection"):
        assert [c["value"] for c in pick(case)] == ["showcase"], case
    assert pick("tender-default") == []                                  # the default is never written
    assert any(c["type"] == "text" and "present" in c for c in data["tender-default"])
    assert any(c["type"] == "text" and "absent" in c for c in data["showcase-explicit"])
