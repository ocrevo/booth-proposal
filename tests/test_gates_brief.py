"""gates.py brief / frame: stamping, reference sets, brief content, legacy set, CLI under a narrow code page."""
import copy
import os
import re
import subprocess
import sys

import pytest

import common
import factory

GATES_PY = str(factory.SCRIPTS / "gates.py")


def _brief(root):
    return common.read_json(str(root / "brief" / "brief.json"))


def _save_brief(root, brief):
    common.write_json(str(root / "brief" / "brief.json"), brief)


def _bare(make_project, **kw):
    return make_project(**{"stamp": False, "ideas": False, "scaffold": False, "renders": False, **kw})


def _add_image(root, rel):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(factory.png_bytes(factory._next_rgb()))


def test_stamp(make_project, run_gates):
    root = _bare(make_project)
    before = _brief(root)
    code, out, err = run_gates(root, "brief", "--stamp")
    assert code == 0, out + err
    after = _brief(root)
    refs = after["references"]
    assert [s["id"] for s in refs["sets"]] == ["set-1", "set-2"]
    assert [len(s["files"]) for s in refs["sets"]] == [2, 3]
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", refs["stamped_at"])
    paths = []
    for s in refs["sets"]:
        assert [f["path"] for f in s["files"]] == sorted(f["path"] for f in s["files"])
        for f in s["files"]:
            assert "\\" not in f["path"]
            assert f["sha256"] == common.sha256_file(str(root / f["path"]))
            paths.append(f["path"])
    assert not {"input/rfp.md", "input/brand-logo.png", "input/product.png"} & set(paths)
    assert not any(p.startswith("brief/") for p in paths)
    assert list(after) == list(before) + ["references"]
    assert {k: v for k, v in after.items() if k != "references"} == before
    code, out, _ = run_gates(root, "brief")
    assert code == 0 and "RESULT: PASS" in out


STALE = {
    "unstamped": None,
    "add": lambda r: _add_image(r, "input/refs/set-1/r09.png"),
    "delete": lambda r: (r / "input/refs/set-1/r01.png").unlink(),
    "rewrite": lambda r: _add_image(r, "input/refs/set-1/r01.png"),
    "new_set": lambda r: _add_image(r, "input/refs/set-3/r01.png"),
}


@pytest.mark.parametrize("case", ["unstamped", "add", "delete", "rewrite", "new_set",
                                  "name_underscore", "name_space", "name_long", "empty_set", "cjk_set"])
def test_refs_gate(make_project, run_gates, has, case):
    if case == "unstamped":
        root = _bare(make_project)
    else:
        root = make_project(ideas=False, scaffold=False, renders=False)
    if case in STALE:
        if STALE[case]:
            STALE[case](root)
        code, out, _ = run_gates(root, "brief")
        assert code == 1 and has(out, "G-REFS", "stale"), out
        code, out, _ = run_gates(root, "brief", "--stamp")
        assert code == 0, out
    elif case.startswith("name_"):
        name = {"name_underscore": "_bad", "name_space": "bad name", "name_long": "a" * 41}[case]
        _add_image(root, f"input/refs/{name}/r01.png")
        code, out, _ = run_gates(root, "brief")
        assert code == 1 and has(out, "G-REFS", "name"), out
    elif case == "empty_set":
        folder = root / "input" / "refs" / "set-3"
        folder.mkdir()
        (folder / "notes.txt").write_text("x", encoding="utf-8")
        code, out, _ = run_gates(root, "brief")
        assert code == 1 and has(out, "G-REFS", "empty"), out
    elif case == "cjk_set":
        name = "\u6e2f\u53e3"
        _add_image(root, f"input/refs/{name}/r01.png")
        code, out, _ = run_gates(root, "brief", "--stamp")
        assert code == 0, out
        assert name in [s["id"] for s in _brief(root)["references"]["sets"]]


def _walk(b, path):
    parts = path.split(".")
    obj = b
    for part in parts[:-1]:
        obj = obj[int(part)] if part.isdigit() else obj[part]
    last = parts[-1]
    return obj, (int(last) if last.isdigit() else last)


def _set(path, value):
    def mutate(b):
        obj, key = _walk(b, path)
        obj[key] = value
    return mutate


def _del(path):
    def mutate(b):
        obj, key = _walk(b, path)
        del obj[key]
    return mutate


BRIEF_CASES = {
    "dup_id": ("brief", lambda b: b["design_points"].append(
        {"id": "D1", "type": "space", "text": "again", "source": "RFP"}), "id"),
    "bad_id": ("brief", _set("design_points.1.id", "DP1"), "id"),
    "claim_no_source": ("brief", _del("claims.0.source"), "source"),
    "point_blank_source": ("brief", _set("design_points.0.source", "  "), "source"),
    "dnm_short": ("brief", _set("do_not_mention", ["x"]), "dnm"),
    "keys_short": ("brief", _set("claims.0.keys", ["x"]), "field"),
    "flag_str": ("brief", _set("claims.0.flag", "yes"), "field"),
    "names_empty": ("brief", _set("client.names", []), "field"),
    "points_missing": ("brief", _del("design_points"), "field"),
    "lang_unknown": ("brief", _set("lang", "xx"), "labels"),
    "booth_missing": ("frame", _del("booth"), "booth"),
    "unit_cm": ("frame", _set("booth.unit", "cm"), "booth"),
    "width_zero": ("frame", _set("booth.width", 0), "booth"),
    "width_bool": ("frame", _set("booth.width", True), "booth"),
    "side_top": ("frame", _set("booth.open_sides", ["top"]), "booth"),
    "side_dup": ("frame", _set("booth.open_sides", ["front", "front"]), "booth"),
    "booth_source_blank": ("frame", _set("booth.source", ""), "booth"),
    "rigging_str": ("frame", _set("booth.rigging_allowed", "yes"), "booth"),
}


@pytest.mark.parametrize("case", ["ok_brief", "ok_frame"] + list(BRIEF_CASES))
def test_brief_content(make_project, run_gates, has, case):
    root = make_project(ideas=False, scaffold=False, renders=False)
    if case in ("ok_brief", "ok_frame"):
        code, out, err = run_gates(root, case.split("_")[1])
        assert code == 0 and "RESULT: PASS" in out, out + err
        return
    cmd, mutate, rule = BRIEF_CASES[case]
    brief = copy.deepcopy(_brief(root))
    mutate(brief)
    _save_brief(root, brief)
    code, out, _ = run_gates(root, cmd)
    assert code == 1, out
    assert has(out, "G-BRIEF", rule), out
    if case == "flag_str":
        assert any("claims[0].flag" in line for line in has(out, "G-BRIEF", rule))


def test_legacy_set(make_project, run_gates, has):
    root = make_project(legacy=True, renders=False)
    sets = _brief(root)["references"]["sets"]
    assert len(sets) == 1 and sets[0]["id"] == "_legacy" and sets[0]["dir"] == "input"
    assert [f["path"] for f in sets[0]["files"]] == ["input/r01.png", "input/r02.png"]
    code, out, _ = run_gates(root, "brief")
    assert code == 0 and has(out, "C-LEGACY", "legacy-set"), out
    project = common.find_project(str(root))
    assert [c.key for c in common.list_concepts(project)] == ["_legacy/A", "_legacy/B"]
    code, out, err = run_gates(root, "select", "_legacy/B", "_legacy/A")
    assert code == 0, out + err


@pytest.mark.parametrize("case", ["empty_set_folder", "no_project"])
def test_cli_subprocess(make_project, tmp_path, case):
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    if case == "empty_set_folder":
        root = _bare(make_project)
        name = "\u6e2f\u53e3"
        (root / "input" / "refs" / name).mkdir()
        r = subprocess.run([sys.executable, GATES_PY, "brief", "--stamp", "--project", str(root)],
                           capture_output=True, env=env)
        out, err = r.stdout.decode("utf-8"), r.stderr.decode("utf-8", "replace")
        assert r.returncode == 1, out + err
        assert "Traceback" not in err
        assert name in out and "RESULT: FAIL" in out
    else:
        empty = tmp_path / "empty"
        empty.mkdir()
        r = subprocess.run([sys.executable, GATES_PY, "brief", "--project", str(empty)],
                           capture_output=True, env=env)
        assert r.returncode == 2
        assert "C-INPUT" in r.stderr.decode("utf-8", "replace")
