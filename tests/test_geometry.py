"""booth_geometry.py: validation, rules and codes, thresholds, facts, CLI exit codes, massing sidecar."""
import copy
import json
import os
import subprocess
import sys

import pytest

import booth_geometry
import common

SCRIPT = os.path.join(str(common.SKILL_DIR), "scripts", "booth_geometry.py")
BASE = {"width": 8, "depth": 6, "max_height": 4.5, "unit": "m", "open_sides": ["front", "right"]}
E0 = {"x": 0, "y": 0, "w": 1, "h": 1, "height": 1}


def spec_of(*elements, **extra):
    return {**copy.deepcopy(BASE), "elements": [copy.deepcopy(e) for e in elements], **extra}


def P(spec):
    return booth_geometry.problems(common.normalise_geometry(spec))


def run(*args, cwd=None):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, SCRIPT, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd, env=env)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


def _validate_case(case):
    s = spec_of(E0)
    if case == "unknown_keys":
        s.update(subtitle="from renders/hero-v1.png", built_from="x")
    elif case == "no_width":
        del s["width"]
    elif case == "string":
        s["elements"].append({**E0, "x": 3, "w": "2"})
    elif case == "bool":
        s["elements"][0]["h"] = True
    elif case == "unit":
        s["unit"] = "mm"
    elif case == "extrusion":
        s["elements"][0]["shape"] = "extrusion"
    elif case == "profile_point":
        s["elements"][0].update(shape="extrusion", profile=[[0, 0], [1, 1], [2]])
    elif case == "zones":
        s["zones"] = [{k: v for k, v in E0.items() if k != "x"}]
        del s["elements"]
    elif case == "override":
        s["envelope_override"] = [{"field": "area", "value": 5, "reason": "x"}]
    return s


VALIDATE = {"clean": None, "unknown_keys": None, "no_width": "width", "string": "elements[1].w", "bool": "elements[0].h",
            "unit": "unit", "extrusion": "elements[0].profile", "profile_point": "elements[0].profile[2]",
            "zones": "zones[0].x", "override": "envelope_override[0].field"}


@pytest.mark.parametrize("case", list(VALIDATE))
def test_validate(case):
    found = common.validate_geometry(_validate_case(case))
    if VALIDATE[case] is None:
        assert found == []
        assert P(_validate_case(case)) == []
    else:
        assert [(f.code, f.where) for f in found] == [("C-INPUT", VALIDATE[case])]


RIG = {"id": "O1", "kind": "overhead", "x": 0, "y": 0, "w": 2, "h": 2, "z": 3, "height": 0.5, "support": "hung"}
RULES = {
    "footprint": ("GEO-FIT", "error", [{"id": "E1", "x": 7.5, "y": 0, "w": 1, "h": 1, "height": 1}], {}),
    "height": ("GEO-FIT", "error", [{"id": "E1", "x": 0, "y": 0, "w": 1, "h": 1, "height": 5}], {}),
    "headroom": ("GEO-FIT", "error", [{"id": "F1", "shape": "frame", "x": 0, "y": 3, "w": 4, "h": 0.3, "height": 2.2,
                                       "band": 0.3, "support": "legs"}], {}),
    "profile": ("GEO-FIT", "error", [{"id": "X1", "shape": "extrusion", "x": 0, "y": 2, "w": 3, "h": 0.2,
                                      "profile": [[0, 0], [3.5, 2]], "support": "floor"}], {}),
    "zone-height": ("GEO-FIT", "error", [{"x": 0, "y": 4.5, "w": 1, "h": 1, "height": 2}],
                    {"height_zones": [{"y_from": 4, "y_to": 6, "max": 1.2}]}),
    "overlap": ("GEO-FIT", "error", [{"id": "A", "x": 0, "y": 0, "w": 2, "h": 2, "height": 1},
                                     {"id": "B", "x": 1, "y": 1, "w": 2, "h": 2, "height": 1}], {}),
    "rigging": ("GEO-FIT", "error", [RIG], {"rigging_allowed": False}),
    "program": ("GEO-PROGRAM", "error", [{**E0, "program": "counter"}], {"required": ["storage"]}),
    "walkway": ("GEO-ADVICE", "warn", [E0, {"x": 1.5, "y": 0, "w": 1, "h": 1, "height": 1}], {}),
    "underside": ("GEO-ADVICE", "warn", [{"kind": "overhead", "x": 0, "y": 0, "w": 2, "h": 2, "z": 1.8, "height": 0.3,
                                          "support": "columns"}], {}),
    "support": ("GEO-ADVICE", "warn", [{"kind": "overhead", "x": 0, "y": 0, "w": 2, "h": 2, "z": 2.5, "height": 0.3}], {}),
    "rigging-unconfirmed": ("GEO-ADVICE", "warn", [RIG], {}),
    "span": ("GEO-ADVICE", "warn", [{"kind": "overhead", "x": 0, "y": 0, "w": 2, "h": 0.5, "z": 2.5, "height": 0.3,
                                    "support": "wall"}], {}),
    "noheight": ("GEO-ADVICE", "warn", [{"x": 0, "y": 0, "w": 1, "h": 1}], {}),
}


@pytest.mark.parametrize("rule", list(RULES))
def test_geo_rules(rule):
    code, level, elements, extra = RULES[rule]
    found = P(spec_of(*elements, **extra))
    hits = [f for f in found if f.message.startswith(rule + ":")]
    assert len(hits) == 1, found
    assert (hits[0].code, hits[0].level) == (code, level)
    assert hits[0].where


def test_extrusion_height():
    arch = {"id": "X1", "shape": "extrusion", "x": 0, "y": 2, "w": 3, "h": 0.2,
            "profile": [[0, 0], [1.5, 5.0], [3, 0]], "support": "floor"}
    found = P(spec_of(arch))
    assert [(f.code, f.where) for f in found] == [("GEO-FIT", "X1")]
    assert found[0].message.startswith("height:")
    assert "top at 5.00 exceeds the 4.5 height limit" in found[0].message
    low = {**arch, "profile": [[0, 0], [1.5, 3.0], [3, 0]]}
    found = P(spec_of(low, height_zones=[{"y_from": 1, "y_to": 3, "max": 1.2}]))
    assert [(f.code, f.where) for f in found] == [("GEO-FIT", "X1")]
    assert found[0].message.startswith("zone-height:")


def _walk(case):
    box = {"x": 0, "y": 0, "w": 1, "h": 1, "height": 1}
    if case.startswith("ft"):
        g = 2.5 if case == "ft_near" else 3.0
        spec = {"width": 26, "depth": 20, "max_height": 15, "unit": "ft",
                "elements": [box, {**box, "x": 1 + g}]}
        return spec, None
    spec = spec_of(box, {**box, "x": 1.5})
    th = {"defaults": None, "th": {"walkway_m": 0.4}, "th_spec": {"walkway_m": 0.4}}[case]
    if case == "th_spec":
        spec["walkway"] = 0.6
    return spec, th


@pytest.mark.parametrize("case,expected", [("defaults", True), ("th", False), ("th_spec", True), ("ft_near", True),
                                           ("ft_far", False)])
def test_walkway_threshold(case, expected):
    spec, th = _walk(case)
    found = booth_geometry.problems(common.normalise_geometry(spec), th)
    hits = [f for f in found if f.code == "GEO-ADVICE" and f.message.startswith("walkway:")]
    assert bool(hits) is expected, found


def test_cli_exit(tmp_path):
    bad = write(tmp_path / "bad.json", spec_of(E0, {**E0, "x": 3, "w": "2"}))
    for cmd in ("check", "facts", "hints", "massing"):
        extra = [str(tmp_path / "out")] if cmd == "massing" else []
        r = run(cmd, bad, *extra)
        assert r.returncode == 2, (cmd, r.stdout, r.stderr)
        assert "C-INPUT" in r.stderr and "elements[1].w" in r.stderr, (cmd, r.stderr)
    broken = write(tmp_path / "broken.json", '{"width": 8,')
    r = run("check", broken)
    assert r.returncode == 2 and "C-INPUT" in r.stderr
    r = run("check", write(tmp_path / "clean.json", spec_of(E0)))
    assert r.returncode == 0 and "RESULT: PASS" in r.stdout, r.stdout + r.stderr
    over = write(tmp_path / "over.json", spec_of({**E0, "id": "A", "w": 2, "h": 2}, {**E0, "id": "B", "x": 1, "y": 1, "w": 2, "h": 2}))
    r = run("check", over)
    assert r.returncode == 1, r.stdout + r.stderr
    assert any("GEO-FIT" in ln and "overlap:" in ln for ln in r.stdout.splitlines()), r.stdout


def ostara():
    return spec_of(
        {"id": "X1", "label": "Roastery arch", "kind": "hero", "shape": "extrusion", "x": 0, "y": 0.5, "w": 4, "h": 0.4,
         "profile": [[0, 0], [2, 4.2], [4, 0]], "support": "floor"},
        {"id": "B1", "label": "Tasting bar", "kind": "zone", "x": 1, "y": 2, "w": 2, "h": 0.6, "height": 1.1,
         "program": "counter"},
        {"id": "B2", "label": "Tasting bar", "kind": "zone", "x": 4, "y": 2, "w": 2, "h": 0.6, "height": 1.1,
         "program": "storage"},
        required=["counter", "storage", "screen"])


def test_facts():
    f = booth_geometry.facts(common.normalise_geometry(ostara()))
    assert list(f) == ["unit", "width", "depth", "max_height", "highest_point", "open_sides", "area", "floor_cover",
                       "zones", "program_served", "required_missing"]
    assert f["highest_point"] == 4.2 and f["area"] == 48 and f["floor_cover"] == 2.4
    assert f["zones"][0]["n"] == 1 and f["zones"][0]["label"] == "Roastery arch" and f["zones"][0]["top"] == 4.2
    assert f["zones"][1]["program"] == ["counter", "storage"] and f["zones"][1]["kind"] == "zone"
    assert f["program_served"] == ["counter", "storage"] and f["required_missing"] == ["screen"]


@pytest.mark.parametrize("mode", ["project", "standalone"])
def test_massing_sidecar(mode, project, tmp_path):
    if mode == "project":
        spec = write(project / "concepts" / "set-1" / "A" / "geometry.json", ostara())
        folder = spec.parent
        r = run("massing", spec, folder / "massing", "--views", "hero", "--size", "600x400", "--project", project)
    else:
        folder = tmp_path / "loose"
        spec = write(folder / "geometry.json", ostara())
        r = run("massing", "geometry.json", "massing", "--views", "hero", "--size", "600x400", cwd=folder)
    assert r.returncode == 0, r.stdout + r.stderr
    png = folder / "massing-hero.png"
    assert png.is_file()
    if mode == "standalone":
        assert not (folder / "massing-hero.json").exists()
        assert "sidecar not written" in r.stderr
        return
    side = json.loads((folder / "massing-hero.json").read_text(encoding="utf-8"))
    assert side["schema"] == "sidecar/2" and side["tool"] == "booth_geometry.py" and side["mode"] == "massing"
    assert (side["set"], side["concept"]) == ("set-1", "A")
    assert side["inputs"] == [{"role": "spec", "path": "concepts/set-1/A/geometry.json",
                               "sha256": common.sha256_file(str(spec))}]
    assert side["outputs"] == {"massing-hero.png": common.sha256_file(str(png))}
    assert side["prompt_sha256"] is None and side["lint"] is None
