"""common.py: JSON I/O, findings output, project loading, term matching, small helpers."""
import hashlib
import json
import re
import sys

import pytest

import common
import factory


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



# ---------- sidecars, forbidden hashes, base chain, review state (phase 1, step 3) ----------

def test_sidecar_write_read(tmp_path):
    img = tmp_path / "hero-v1.png"
    img.write_bytes(factory.png_bytes((1, 2, 3)))
    data = {"tool": "render.py", "mode": "hero", "set": "set-1", "concept": "A", "inputs": [],
            "prompt_sha256": None, "lint": None, "outputs": {"hero-v1.png": "bogus"}, "created_at": "old",
            "schema": "old"}
    common.write_sidecar(str(img), data)
    side = common.read_sidecar(str(img))
    assert common.sidecar_path(str(img)) == str(tmp_path / "hero-v1.json")
    assert common.sidecar_version(side) == 2
    assert side["outputs"] == {"hero-v1.png": common.sha256_file(str(img))}
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", side["created_at"])
    assert list(side)[0] == "schema" and list(side)[-2:] == ["outputs", "created_at"]
    assert list(side)[1:-2] == ["tool", "mode", "set", "concept", "inputs", "prompt_sha256", "lint"]
    bad = {k: v for k, v in data.items() if k != "lint"}
    with pytest.raises(ValueError):
        common.write_sidecar(str(img), bad)
    with pytest.raises(ValueError):
        common.write_sidecar(str(img), {**data, "outputs": {"missing.png": "x"}})


@pytest.mark.parametrize("data,expected", [
    (None, 0), ([], 0), ({"schema": "sidecar/2"}, 2), ({"mode": "hero"}, 1), ({"schema": "sidecar/3"}, 0)])
def test_sidecar_version(data, expected):
    assert common.sidecar_version(data) == expected


def test_read_sidecar_unreadable(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    assert common.read_sidecar(str(img)) is None
    (tmp_path / "a.json").write_text("[1]", encoding="utf-8")
    assert common.read_sidecar(str(img)) is None
    (tmp_path / "a.json").write_text("{bad", encoding="utf-8")
    assert common.read_sidecar(str(img)) is None


@pytest.mark.parametrize("case", ["reference", "rfp", "media", "logo_copy", "logo_that_is_a_reference"])
def test_forbidden_hashes(project, case):
    ref = project / "input" / "refs" / "set-1" / "r01.png"
    if case == "media":
        media = project / "brief" / "media" / "m.png"
        media.parent.mkdir(parents=True)
        media.write_bytes(factory.png_bytes(factory._next_rgb()))
    if case == "logo_that_is_a_reference":
        (project / "brief" / "brand" / "ref-copy.png").write_bytes(ref.read_bytes())
    path = {"reference": ref, "rfp": project / "input" / "rfp.md", "media": project / "brief" / "media" / "m.png",
            "logo_copy": project / "input" / "brand-logo.png",
            "logo_that_is_a_reference": project / "brief" / "brand" / "ref-copy.png"}[case]
    forbidden = common.forbidden_hashes(common.find_project(str(project)))
    h = common.sha256_file(str(path))
    if case == "logo_copy":
        assert h not in forbidden
    else:
        assert h in forbidden
    if case in ("reference", "logo_that_is_a_reference"):
        assert forbidden[h] == "input/refs/set-1/r01.png"


@pytest.mark.parametrize("case", ["factory_hero", "v1_hero", "reference_copy", "other_concept", "cycle"])
def test_base_chain(project, case):
    proj = common.find_project(str(project))
    ref = "input/refs/set-1/r01.png"
    if case == "factory_hero":
        rel = "concepts/set-1/A/renders/hero-v1.png"
    elif case == "v1_hero":
        rel = factory.add_render(project, "set-1/A", "hero-v5.png", version=1, refs=[ref])
    elif case == "reference_copy":
        rel = factory.add_render(project, "set-1/A", "hero-v9.png", refs=[ref],
                                 data=(project / ref).read_bytes())
    elif case == "other_concept":
        rel = factory.add_render(project, "set-1/A", "hero-v8.png", mode="fix",
                                 base="concepts/set-1/B/renders/hero-v1.png")
    else:
        a = factory.add_render(project, "set-1/A", "hero-v6.png", version=None)
        rel = factory.add_render(project, "set-1/A", "hero-v7.png", mode="fix", base=a)
        factory.put_sidecar(project, a, "fix", base=rel)
    visited, finding = common.trace_base_chain(proj, str(project / rel))
    if case in ("factory_hero", "v1_hero"):
        assert finding is None and visited[0] == rel
        return
    assert finding.code == "R-SOURCE" and finding.level == "error" and finding.where == rel
    assert finding.message.startswith("chain: ")
    expected = {"reference_copy": f"has the same content as {ref}",
                "other_concept": "is not a render of set-1/A", "cycle": "cycle at "}[case]
    assert expected in finding.message
    if case == "cycle":
        assert len(visited) == 2


def test_base_chain_ends_at_hero_through_fix(project):
    proj = common.find_project(str(project))
    hero = factory.add_render(project, "set-1/A", "hero-v6.png", refs=["input/refs/set-1/r01.png"])
    fix = factory.add_render(project, "set-1/A", "hero-v7.png", mode="fix", base=hero)
    assert common.trace_base_chain(proj, str(project / fix)) == ([fix, hero], None)
    (project / hero).write_bytes(factory.png_bytes(factory._next_rgb()))     # the base changes after the fix
    _, finding = common.trace_base_chain(proj, str(project / fix))
    assert finding.code == "R-SOURCE" and "changed after" in finding.message
    assert common.trace_base_chain(proj, str(project / "input" / "product.png"))[1].message == \
        "chain: not a render of any concept"


def _review(project, rel, **over):
    image = project / rel
    review = {"schema": "review/1", "image": image.name, "sha256": common.sha256_file(str(image)),
              "scope": "full", "verdict": "pass"}
    review.update(over)
    common.write_json(common.review_path(str(image)), review)
    return str(image)


@pytest.mark.parametrize("case", ["missing", "stale", "fail", "scope"])
def test_review_is_current_pass(project, case):
    rel = "concepts/set-1/A/renders/hero-v1.png"
    image = str(project / rel)
    if case == "missing":
        assert common.read_review(image) is None
        ok, why = common.review_is_current_pass(image, True)
        assert not ok and why.startswith("missing:")
        return
    _review(project, rel, **({"verdict": "fail"} if case == "fail" else {"scope": "whole"} if case == "scope" else {}))
    if case == "stale":
        (project / rel).write_bytes(factory.png_bytes(factory._next_rgb()))
    ok, why = common.review_is_current_pass(image, True)
    assert not ok and why.startswith(f"{case}:")
    if case == "stale":
        assert "run render.py review" in why
    if case == "scope":
        assert common.review_is_current_pass(image, False) == (True, "")


def test_read_review_schema(project):
    rel = "concepts/set-1/A/renders/hero-v1.png"
    image = _review(project, rel, schema="review/0")
    assert common.read_review(image) is None
    image = _review(project, rel)
    assert common.read_review(image)["verdict"] == "pass"
    assert common.review_is_current_pass(image, True) == (True, "")


def test_logo_hashes_and_find_font(project):
    proj = common.find_project(str(project))
    logo = common.sha256_file(str(project / "input" / "brand-logo.png"))
    assert common.logo_hashes(proj) == {logo}
    extra = project / "brief" / "extra-logo.png"
    extra.write_bytes(factory.png_bytes(factory._next_rgb()))
    proj.style["logo"] = "extra-logo.png"
    assert common.logo_hashes(proj) == {logo, common.sha256_file(str(extra))}
    for cjk in (False, True):
        font = common.find_font(cjk)
        assert font is None or font.lower().endswith((".ttf", ".ttc", ".otf"))


def test_geometry_helpers():
    spec = {"width": 8, "depth": 6, "max_height": 4.5, "elements": [
        {"label": "Fins", "x": 1, "y": 1, "w": 0.2, "h": 1, "height": 1,
         "repeat": {"count": 5, "dx": 0.3, "height_to": 2}},
        {"label": "Tasting bar", "x": 0, "y": 4, "w": 2, "h": 1, "height": 1},
        {"label": "Tasting bar", "x": 3, "y": 4, "w": 2, "h": 1, "height": 1},
        {"x": 6, "y": 4, "w": 1, "h": 1}]}
    out = common.normalise_geometry(spec)
    assert out is spec
    fins, bar, _, bare = spec["elements"]
    assert [e["id"] for e in spec["elements"]] == ["E1", "E2", "E3", "E4"]
    assert bar["z"] == 0 and bar["shape"] == "box"
    assert abs(fins["w"] - 1.4) < 1e-9 and fins["height"] == 2 and fins["piece"] == {"w": 0.2, "h": 1}
    assert common.normalise_geometry(spec)["elements"][0]["w"] == fins["w"]   # idempotent
    pieces = common.expand_repeat(fins)
    assert len(pieces) == 5 and all(p["w"] == 0.2 and "repeat" not in p for p in pieces)
    assert abs(pieces[4]["x"] - 2.2) < 1e-9 and pieces[0]["height"] == 1 and pieces[4]["height"] == 2
    assert common.expand_repeat(bar) == [bar]
    assert common.zone_numbers(spec["elements"]) == {"Fins": 1, "Tasting bar": 2}
    assert common.zone_numbers([]) == {}
