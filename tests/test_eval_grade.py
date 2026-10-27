"""tools/eval_grade.py: the deterministic checks of the eval cases, run against a workspace built with the factory
(two selected concepts, a filled deck, check clean). Each test writes its own small checks file."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import factory

REPO = Path(__file__).resolve().parents[1]
TOOL = str(REPO / "tools" / "eval_grade.py")


def checks_file(tmp_path: Path, checks: list, case: str = "demo") -> str:
    path = tmp_path / "checks.json"
    numbered = [{"id": f"{case}-{i:02d}", **c} for i, c in enumerate(checks, 1)]
    path.write_text(json.dumps({"schema": "eval-checks/1", "cases": {case: numbered}}), encoding="utf-8")
    return str(path)


def grade(tmp_path, ws, checks, *extra, case="demo", ask="demo"):
    """Run the grader on a checks file that holds `case`, asking for the case `ask`."""
    p = subprocess.run([sys.executable, TOOL, "--case", ask, "--workspace", str(ws),
                        "--checks", checks_file(tmp_path, checks, case), *extra],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path))
    return p.returncode, p.stdout, p.stderr


def status(out: str) -> dict:
    return {m.group(2): m.group(1) for m in re.finditer(r"^(PASS|FAIL) (\S+) \u2013 ", out, re.M)}


@pytest.fixture
def ws(tmp_path):
    return factory.deck_project(tmp_path)


def baseline(tmp_path, rel: str, text: str) -> tuple:
    base = tmp_path / "base"
    (base / rel).parent.mkdir(parents=True, exist_ok=True)
    (base / rel).write_bytes(text.encode("utf-8"))
    return ("--baseline", str(base))


PASSING = [{"type": "exists", "path": "pack/proposal.html"}, {"type": "check_clean"}, {"type": "pack_only"},
           {"type": "text", "present": ["Tidewater Pass"], "absent": ["set-1/A", "TODO"]}]


def test_grade_pass(tmp_path, ws):
    code, out, err = grade(tmp_path, ws, PASSING)
    assert code == 0, out + err
    assert out.rstrip().endswith("RESULT: 4/4")
    assert set(status(out).values()) == {"PASS"}


@pytest.mark.parametrize("kind", ["pack", "unchanged"])
def test_grade_fail(tmp_path, ws, kind):
    extra = ()
    if kind == "pack":
        (ws / "pack" / "notes.txt").write_text("stray", encoding="utf-8")
        checks = [PASSING[0], PASSING[2]]
    else:
        shown = ws / "brief" / "brief.json"
        extra = baseline(tmp_path, "brief/brief.json", shown.read_bytes().decode("utf-8"))
        shown.write_text(shown.read_text(encoding="utf-8") + " ", encoding="utf-8")
        checks = [PASSING[0], {"type": "unchanged", "path": "brief/brief.json"}]
    code, out, err = grade(tmp_path, ws, checks, *extra)
    assert code == 1, out + err
    assert status(out) == {"demo-01": "PASS", "demo-02": "FAIL"}
    assert out.rstrip().endswith("RESULT: 1/2")


def test_unchanged_passes_on_identical_file(tmp_path, ws):
    extra = baseline(tmp_path, "brief/brief.json", (ws / "brief" / "brief.json").read_bytes().decode("utf-8"))
    code, out, err = grade(tmp_path, ws, [{"type": "unchanged", "path": "brief/brief.json"}], *extra)
    assert code == 0 and "RESULT: 1/1" in out, out + err


@pytest.mark.parametrize("what", ["case", "type", "workspace", "field"])
def test_grade_bad_input_exit2(tmp_path, ws, what):
    checks, target, ask = [{"type": "exists", "path": "pack/proposal.html"}], ws, "demo"
    if what == "case":
        ask = "no-such-case"
    elif what == "type":
        checks = [{"type": "telepathy"}]
    elif what == "field":
        checks = [{"type": "json_equals", "path": "brief/brief.json"}]
    else:
        target = tmp_path / "nowhere"
    code, out, err = grade(tmp_path, target, checks, ask=ask)
    assert code == 2, out + err
    assert "RESULT" not in out and err.strip()


def test_shipped_checks_load():
    """Every case of the shipped file is accepted by the grader's own validation (no workspace needed)."""
    sys.path.insert(0, str(REPO / "tools"))
    import eval_grade
    path = str(REPO / "tools" / "eval_checks.json")
    for case in json.loads(Path(path).read_text(encoding="utf-8"))["cases"]:
        assert eval_grade.load_checks(path, case)


# ---- negative probes: every check type can fail, and the content checks can pass

def _break_geometry(ws):
    path = ws / "concepts" / "set-1" / "A" / "geometry.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    spec["elements"][1]["x"] = 40
    path.write_text(json.dumps(spec), encoding="utf-8")


def _break_prompt(ws):
    (ws / "concepts" / "set-1" / "A" / "prompts" / "hero.txt").write_text(
        'Nordvik 2027 "Every crossing, calmer."\n', encoding="utf-8")


def _break_deck(ws):
    deck = ws / "pack" / "proposal.html"
    text = deck.read_text(encoding="utf-8")
    new = text.replace('src="../concepts/set-1/A/renders/hero-v2.png"', 'src="data:image/png;base64,iVBORw0KGgo="', 1)
    assert new != text
    deck.write_text(new, encoding="utf-8")


def _stray(ws):
    (ws / "pack" / "x.txt").write_text("x", encoding="utf-8")


PROBES = {
    "exists": ([{"type": "exists", "path": "pack/proposal.pdf"}], None),
    "absent": ([{"type": "absent", "path": "pack/proposal.html"}], None),
    "command": ([{"type": "command", "argv": ["{py}", "{scripts}/gates.py", "select", "set-9/Z", "--project", "{ws}"],
                  "exit": [0]}], None),
    "json_equals": ([{"type": "json_equals", "path": "brief/selection.json", "key": "lead", "value": "set-2/B"}],
                    None),
    "check_clean": ([{"type": "check_clean", "codes": ["D-IMG-URL"]}], _break_deck),
    "text": ([{"type": "text", "present": ["a sentence that is not in the deck"]}], None),
    "pack_only": ([{"type": "pack_only"}], _stray),
    "unchanged": ([{"type": "unchanged", "path": "brief/brief.json"}], None),
    "lint_all": ([{"type": "lint_all", "glob": "concepts/*/*/prompts/*.txt"}], _break_prompt),
    "geometry_all": ([{"type": "geometry_all", "glob": "**/geometry.json"}], _break_geometry),
}


@pytest.mark.parametrize("kind", sorted(PROBES))
def test_every_check_type_can_fail(tmp_path, ws, kind):
    checks, damage = PROBES[kind]
    extra = baseline(tmp_path, "brief/brief.json", "{}") if kind == "unchanged" else ()
    if damage:
        damage(ws)
    code, out, err = grade(tmp_path, ws, checks, *extra)
    assert code == 1, out + err
    assert status(out) == {"demo-01": "FAIL"}
    assert out.rstrip().endswith("RESULT: 0/1")


CAN_PASS = {
    "lint_all": {"type": "lint_all", "glob": "concepts/*/*/prompts/*.txt"},
    "geometry_all": {"type": "geometry_all", "glob": "**/geometry.json"},
    "check_clean": {"type": "check_clean", "codes": ["D-IMG-URL"]},
    "command": {"type": "command", "argv": ["{py}", "{scripts}/gates.py", "concepts", "--json", "--project", "{ws}"],
                "exit": [0]},
    "json_equals": {"type": "json_equals", "path": "brief/selection.json", "key": "lead", "value": "set-1/A"},
}


@pytest.mark.parametrize("kind", sorted(CAN_PASS))
def test_content_checks_can_pass(tmp_path, ws, kind):
    code, out, err = grade(tmp_path, ws, [CAN_PASS[kind]])
    assert code == 0, out + err


def test_geometry_all_without_brief(tmp_path, ws):
    """The geometry-only cases have no brief/: the check runs the spec without --project."""
    (tmp_path / "bare" / "work").mkdir(parents=True)
    (tmp_path / "bare" / "work" / "geometry.json").write_bytes(
        (ws / "concepts" / "set-1" / "A" / "geometry.json").read_bytes())
    code, out, err = grade(tmp_path, tmp_path / "bare", [CAN_PASS["geometry_all"]])
    assert code == 0, out + err
