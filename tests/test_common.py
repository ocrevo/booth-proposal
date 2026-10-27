"""common.py: JSON I/O, findings output, project loading, term matching, small helpers."""
import hashlib
import json
import re
import sys

import pytest

import common


@pytest.mark.parametrize("case", ["roundtrip", "bom", "invalid_json", "missing", "list", "wrong_schema",
                                  "no_schema", "opt_missing"])
def test_json_io(tmp_path, case):
    p = tmp_path / "sub" / "a.json"
    if case == "roundtrip":
        data = {"schema": "x/1", "name": "\u6e2f"}
        common.write_json(str(p), data)
        raw = p.read_bytes()
        assert "\u6e2f".encode("utf-8") in raw and b"\\u" not in raw
        assert raw.endswith(b"\n") and b"\r\n" not in raw
        assert not list(p.parent.glob("*.tmp"))
        assert common.read_json(str(p)) == data
        assert common.read_json(str(p), "x/1") == data
    elif case == "bom":
        p.parent.mkdir()
        p.write_bytes(b"\xef\xbb\xbf" + b'{"a": 1}')
        assert common.read_json(str(p)) == {"a": 1}
    elif case == "opt_missing":
        assert common.read_json_opt(str(p)) is None
    else:
        p.parent.mkdir()
        schema = None
        if case == "invalid_json":
            p.write_text("{not json", encoding="utf-8")
        elif case == "list":
            p.write_text("[1, 2]", encoding="utf-8")
        elif case == "wrong_schema":
            p.write_text('{"schema": "y/1"}', encoding="utf-8")
            schema = "x/1"
        elif case == "no_schema":
            p.write_text('{"a": 1}', encoding="utf-8")
            schema = "x/1"
        with pytest.raises(common.InputError) as ei:
            common.read_json(str(p), schema)
        assert ei.value.code == "C-INPUT"


def test_print_findings(capsys):
    F = common.Finding
    three = [
        F("L-BAN", "error", "concepts/set-1/A/prompts/hero.txt:1",
          'quote: a quote mark (") in a free-text block'),
        F("L-WORDS", "warn", "concepts/set-1/A/prompts/hero.txt", "372 words (guide 350)"),
        F("D-TXT-PENDING", "pending", "page 9 A-detail", 'evolution word "evolve" \u2013 decide in review pass 1'),
    ]
    expected = (
        'ERROR   L-BAN              concepts/set-1/A/prompts/hero.txt:1: quote: a quote mark (") in a free-text block\n'
        'WARN    L-WORDS            concepts/set-1/A/prompts/hero.txt: 372 words (guide 350)\n'
        'PENDING D-TXT-PENDING      page 9 A-detail: evolution word "evolve" \u2013 decide in review pass 1\n'
        'RESULT: FAIL \u2013 1 error, 1 warning, 1 pending\n')
    assert common.print_findings(three) == 1
    assert capsys.readouterr().out == expected

    two = [F("L-WORDS", "warn", "a", "x"), F("L-WORDS", "warn", "b", "y")]
    assert common.print_findings(two) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "RESULT: PASS \u2013 0 errors, 2 warnings, 0 pending"

    assert common.print_findings(three, as_json=True) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["counts"] == {"error": 1, "warn": 1, "pending": 1}
    assert set(data["findings"][0]) == {"code", "level", "where", "message", "page", "page_id"}


def _write_style(root, style):
    common.write_json(str(root / "brief" / "deck-style.json"), style)


@pytest.mark.parametrize("case", ["empty_folder", "no_brief_json", "selection_schema", "thr_str", "thr_bool",
                                  "thr_float_for_int", "thr_override", "claim_flag_loads"])
def test_find_project(tmp_path, make_project, case):
    if case == "empty_folder":
        (tmp_path / "e").mkdir()
        with pytest.raises(common.InputError) as ei:
            common.find_project(str(tmp_path / "e"))
        assert ei.value.code == "C-INPUT"
        return
    if case == "no_brief_json":
        (tmp_path / "b" / "brief").mkdir(parents=True)
        with pytest.raises(common.InputError) as ei:
            common.find_project(str(tmp_path / "b"))
        assert ei.value.code == "C-INPUT"
        return
    root = make_project(stamp=False, ideas=False, scaffold=False, renders=False)
    if case == "selection_schema":
        common.write_json(str(root / "brief" / "selection.json"),
                          {"schema": "selection/0", "selected": ["set-1/A"], "lead": None,
                           "display": {"set-1/A": "A"}})
        with pytest.raises(common.InputError) as ei:
            common.find_project(str(root))
        assert ei.value.code == "C-INPUT"
    elif case in ("thr_str", "thr_bool", "thr_float_for_int"):
        bad = {"thr_str": "3", "thr_bool": True, "thr_float_for_int": 2.5}[case]
        _write_style(root, {"thresholds": {"fix_max": bad}})
        with pytest.raises(common.InputError) as ei:
            common.find_project(str(root))
        assert ei.value.code == "C-INPUT"
    elif case == "thr_override":
        _write_style(root, {"thresholds": {"image_reuse_max": 3, "bogus": 1}})
        th = common.find_project(str(root)).thresholds
        assert th["image_reuse_max"] == 3
        assert {k: v for k, v in th.items() if k != "image_reuse_max"} == \
            {k: v for k, v in common.DEFAULTS.items() if k != "image_reuse_max"}
    elif case == "claim_flag_loads":
        brief = common.read_json(str(root / "brief" / "brief.json"))
        brief["claims"][0]["flag"] = "yes"
        common.write_json(str(root / "brief" / "brief.json"), brief)
        assert common.find_project(str(root)).brief["claims"][0]["flag"] == "yes"


@pytest.mark.parametrize("term,text,case,expected", [
    ("D3", "see D3.", False, [(4, 6)]),
    ("D3", "AD3", False, []),
    ("D3", "D30", False, []),
    ("D3", "\u89c1D3\u9875", False, [(1, 3)]),
    ("tidewater pass", "The Tidewater Pass app", False, [(4, 18)]),
    ("tidewater pass", "The Tidewater Pass app", True, []),
    ("\u6e2f\u53e3", "\u5927\u6e2f\u53e3\u5e02", False, [(1, 3)]),
    ("", "anything", False, []),
])
def test_find_term(term, text, case, expected):
    assert common.find_term(term, text, case=case) == expected


ABC_SHA = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


@pytest.mark.parametrize("case", ["sha256", "now_iso", "inside", "inside_drives", "is_cjk", "cjk_ratio",
                                  "to_m", "unit_factor", "hex_rgb"])
def test_small_helpers(tmp_path, case):
    if case == "sha256":
        assert common.sha256_text("abc") == ABC_SHA
        p = tmp_path / "abc.bin"
        p.write_bytes(b"abc")
        assert common.sha256_file(str(p)) == ABC_SHA == hashlib.sha256(b"abc").hexdigest()
    elif case == "now_iso":
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", common.now_iso())
    elif case == "inside":
        root = tmp_path / "root"
        root.mkdir()
        assert common.inside(str(root), str(root / "x"))
        assert common.inside(str(root), str(root))
        assert not common.inside(str(root), str(tmp_path))
        assert not common.inside(str(root), str(tmp_path / "other"))
    elif case == "inside_drives":
        if sys.platform != "win32":
            pytest.skip("drive letters exist on Windows only")
        assert common.inside("C:\\a", "D:\\a") is False
    elif case == "is_cjk":
        for ch in "\u6e2f\uff0c\u300c\uac00":
            assert common.is_cjk(ch), hex(ord(ch))
        for ch in "a\u00b7\u2013\u00d7":
            assert not common.is_cjk(ch), hex(ord(ch))
    elif case == "cjk_ratio":
        assert common.cjk_ratio("ab\u6e2f\u53e3") == 0.5
        assert common.cjk_ratio("") == 0.0
    elif case == "to_m":
        assert common.to_m(10, "ft") == pytest.approx(3.048, abs=1e-3)
        assert common.to_m(10, "m") == 10
    elif case == "unit_factor":
        with pytest.raises(ValueError):
            common.unit_factor("cm")
    elif case == "hex_rgb":
        assert common.hex_rgb("#0B3D5C") == (11, 61, 92)

