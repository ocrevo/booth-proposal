"""gates.py select: writing, show/clear, refusals."""
import json
import re

import pytest

import common
import factory

ISO = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d"


def _sel_path(root):
    return root / "brief" / "selection.json"


def test_select_write(make_project, run_gates):
    root = make_project(renders=False)
    code, out, err = run_gates(root, "select", "set-2/B", "set-1/A", "--lead", "set-1/A")
    assert code == 0, out + err
    sel = json.loads(_sel_path(root).read_text(encoding="utf-8"))
    assert list(sel) == ["schema", "selected", "lead", "display", "updated_at"]
    assert sel["schema"] == "selection/1"
    assert sel["selected"] == ["set-2/B", "set-1/A"]
    assert sel["lead"] == "set-1/A"
    assert sel["display"] == {"set-2/B": "A", "set-1/A": "B"}
    assert re.fullmatch(ISO, sel["updated_at"])
    assert common.find_project(str(root)).selection["selected"] == ["set-2/B", "set-1/A"]

    code, out, err = run_gates(root, "select", "set-1/B")
    assert code == 0, out + err
    sel = json.loads(_sel_path(root).read_text(encoding="utf-8"))
    assert sel["lead"] is None and sel["display"] == {"set-1/B": "A"}

    code, out, _ = run_gates(root, "select", "--show")
    assert code == 0 and json.loads(out) == sel

    code, out, _ = run_gates(root, "select", "--clear")
    assert code == 0 and not _sel_path(root).exists()
    code, out, _ = run_gates(root, "select", "--clear")
    assert code == 0
    code, out, _ = run_gates(root, "select", "--show")
    assert code == 0 and "no brief/selection.json" in out


def _rewrite_ref(root):
    p = root / "input" / "refs" / "set-1" / "r01.png"
    p.write_bytes(factory.png_bytes(factory._next_rgb()))


def _bad_front_matter(root):
    (root / "concepts" / "set-1" / "A" / "concept.md").write_text("---\nlead: yes\n---\n", encoding="utf-8",
                                                                  newline="\n")


REFUSED = {
    "unknown": (None, ("select", "set-1/A", "set-3/A"), 1, "G-SELECT", "unknown"),
    "lead": (None, ("select", "set-1/A", "--lead", "set-2/A"), 1, "G-SELECT", "lead"),
    "stale": (_rewrite_ref, ("select", "set-1/A"), 1, "G-REFS", "stale"),
    "front_matter": (_bad_front_matter, ("select", "set-1/A"), 1, "G-FM", None),
    "no_args": (None, ("select",), 2, None, None),
    "show_and_clear": (None, ("select", "--show", "--clear"), 2, None, None),
    "lead_alone": (None, ("select", "--lead", "set-1/A"), 2, None, None),
    "duplicate": (None, ("select", "set-1/A", "set-1/A"), 2, None, None),
    "too_many": (None, ("select", *[f"set-1/K{i}" for i in range(27)]), 2, None, None),
}


@pytest.mark.parametrize("case", list(REFUSED))
def test_select_refused(make_project, run_gates, has, case):
    root = make_project(renders=False)
    code, out, err = run_gates(root, "select", "set-2/B", "set-1/A")
    assert code == 0, out + err
    before = _sel_path(root).read_bytes()
    prep, args, want_code, code_name, rule = REFUSED[case]
    if prep:
        prep(root)
    code, out, err = run_gates(root, *args)
    assert code == want_code, out + err
    if code_name:
        assert has(out, code_name, rule), out
    assert _sel_path(root).read_bytes() == before


def test_select_clear_with_malformed_selection(make_project, run_gates):
    root = make_project(renders=False)
    _sel_path(root).write_text('{"schema": "selection/1", "selected": "not a list"}', encoding="utf-8")
    code, out, err = run_gates(root, "select", "--show")
    assert code == 2 and "C-INPUT" in err
    code, out, err = run_gates(root, "brief")
    assert code == 2 and "C-INPUT" in err
    code, out, err = run_gates(root, "select", "--clear")
    assert code == 0, out + err
    assert not _sel_path(root).exists()
    code, out, err = run_gates(root, "select", "set-1/A")
    assert code == 0, out + err
