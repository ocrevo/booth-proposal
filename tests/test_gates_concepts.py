"""gates.py concepts and report concepts: G-GEO rules for the selected concepts only, read-only."""
import copy
import hashlib
import json
import os

import pytest

import common
import draw_plan

BOOTH = {"unit": "m", "width": 8, "depth": 6, "max_height": 4.5, "open_sides": ["front", "right"],
         "source": "RFP 3.2"}

OSTARA = {
    "title": "A · Roastery Gate", "width": 8, "depth": 6, "max_height": 4.5, "unit": "m",
    "open_sides": ["front", "right"],
    "elements": [
        {"id": "X1", "shape": "extrusion", "label": "Roastery arch", "kind": "hero", "x": 0, "y": 2, "w": 3,
         "h": 0.2, "profile": [[0, 0], [1.5, 4.2], [3, 0]], "support": "floor"},
        {"id": "T1", "label": "Tasting bar", "x": 4, "y": 1, "w": 2, "h": 0.8, "height": 1.1},
        {"id": "T2", "label": "Tasting bar", "x": 4, "y": 3, "w": 2, "h": 0.8, "height": 1.1}]}

A = "concepts/set-1/A"


def put_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")


def spec_of(**changes):
    spec = copy.deepcopy(OSTARA)
    spec.update(changes)
    return spec


def draw(root, key="set-1/A"):
    outbase = str(root / "concepts" / key / "plan")
    code = draw_plan.main(["plan", str(root / "concepts" / key / "geometry.json"), outbase, "--project", str(root)])
    assert code == 0


@pytest.fixture
def setup(make_project, run_gates):
    """A project with a valid geometry and a drawn plan for set-1/A, and set-1/A selected."""
    root = make_project(renders=False)
    brief = common.read_json(str(root / "brief" / "brief.json"))
    brief["booth"] = dict(BOOTH)
    common.write_json(str(root / "brief" / "brief.json"), brief)
    put_json(root / A / "geometry.json", OSTARA)
    draw(root)
    code, out, err = run_gates(root, "select", "set-1/A")
    assert code == 0, out + err
    return root


def snapshot(root):
    out = {}
    for folder, _, names in os.walk(root):
        for n in names:
            p = os.path.join(folder, n)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = hashlib.sha256(f.read()).hexdigest()
    return out


def test_pass_read_only(setup, run_gates):
    root = setup
    put_json(root / "concepts" / "set-1" / "B" / "geometry.json", "{")
    before = snapshot(root)
    code, out, err = run_gates(root, "concepts", "--json")
    assert code == 0, out + err
    data = json.loads(out)
    assert data["counts"]["error"] == 0
    assert not any("set-1/B" in json.dumps(f) for f in data["findings"])
    assert snapshot(root) == before


def _case_no_selection(root, run_gates):
    code, out, err = run_gates(root, "select", "--clear")
    assert code == 0, out + err


def _case_missing(root, run_gates):
    (root / A / "geometry.json").unlink()


def _case_check(root, run_gates):
    spec = spec_of()
    spec["elements"].append({"id": "O1", "x": 4.5, "y": 1, "w": 1, "h": 0.5, "height": 1})
    put_json(root / A / "geometry.json", spec)
    draw(root)


def _case_invalid(root, run_gates):
    spec = spec_of()
    spec["elements"][0]["w"] = "2"
    put_json(root / A / "geometry.json", spec)


def _case_envelope(root, run_gates):
    put_json(root / A / "geometry.json", spec_of(width=7.5))
    draw(root)


def _case_plan(root, run_gates):
    (root / A / "plan.json").unlink()


def _case_stale(root, run_gates):
    spec = spec_of()
    spec["elements"][1]["x"] = 4.2
    put_json(root / A / "geometry.json", spec)


G_GEO = {
    "no_selection": (_case_no_selection, 1, "G-SELECT", None, None),
    "missing": (_case_missing, 1, "G-GEO", "missing", None),
    "check": (_case_check, 1, "G-GEO", "check", "GEO-FIT"),
    "invalid": (_case_invalid, 1, "G-GEO", "invalid", "elements[0].w"),
    "envelope": (_case_envelope, 1, "G-GEO", "envelope", None),
    "plan": (_case_plan, 1, "G-GEO", "plan", None),
    "stale": (_case_stale, 1, "G-GEO", "stale", None),
}


@pytest.mark.parametrize("case", list(G_GEO))
def test_g_geo(setup, run_gates, has, case):
    root = setup
    change, want_code, code_name, rule, inside = G_GEO[case]
    change(root, run_gates)
    code, out, err = run_gates(root, "concepts")
    assert code == want_code, out + err
    hits = has(out, code_name, rule)
    assert hits, out
    if inside:
        assert any(inside in line for line in hits), hits
    if case == "stale":
        draw(root)
        code, out, err = run_gates(root, "concepts")
        assert code == 0, out + err


def _env_lower(root):
    put_json(root / A / "geometry.json", spec_of(max_height=4.0))


def _env_ft_booth(root):
    brief = common.read_json(str(root / "brief" / "brief.json"))
    f = common.unit_factor("ft")
    brief["booth"] = {**BOOTH, "unit": "ft", "width": 8 * f, "depth": 6 * f, "max_height": 4.5 * f}
    common.write_json(str(root / "brief" / "brief.json"), brief)


def _override(reason, value):
    def prep(root):
        put_json(root / A / "geometry.json", spec_of(
            max_height=5.0, envelope_override=[{"field": "max_height", "value": value, "reason": reason}]))
    return prep


ENVELOPE = {
    "lower": (_env_lower, False),
    "ft_booth": (_env_ft_booth, False),
    "override": (_override("Venue approved a 5 m tower", 5.0), False),
    # A blank reason is a valid spec (it still draws) but the envelope rule does not accept it as an override.
    "blank_reason": (_override(" ", 5.0), "envelope"),
    "wrong_value": (_override("Venue approved a 5 m tower", 4.8), True),
}


@pytest.mark.parametrize("case", list(ENVELOPE))
def test_envelope(setup, run_gates, has, case):
    root = setup
    prep, expect = ENVELOPE[case]
    prep(root)
    draw(root)
    code, out, err = run_gates(root, "concepts")
    if expect is True:
        assert has(out, "G-GEO", "envelope"), out
        assert code == 1
    elif expect:
        assert has(out, "G-GEO", expect), out
        assert code == 1
    else:
        assert not has(out, "G-GEO", "envelope"), out


def test_report_concepts(setup, run_gates):
    root = setup
    L = common.load_labels("en")["report"]
    code, out, err = run_gates(root, "report", "concepts")
    assert code == 0, out + err
    assert out.startswith("# " + L["concepts"])
    assert f"| A | set-1/A | {L['pass']} | concepts/set-1/A/plan.png |" in out
    put_json(root / A / "geometry.json", spec_of(width=7.5))
    draw(root)
    code, out, err = run_gates(root, "report", "concepts")
    assert code == 0, out + err
    assert f"| A | set-1/A | {L['fail']} (G-GEO) | concepts/set-1/A/plan.png |" in out
    code, out, err = run_gates(root, "select", "--clear")
    assert code == 0, out + err
    code, out, err = run_gates(root, "report", "concepts")
    assert code == 0 and L["none"] in out and "| A |" not in out
