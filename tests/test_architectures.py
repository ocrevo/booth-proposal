"""Architectures (stage A1): the registry, the choice, brief.json clauses and graphics, gates.py architectures,
deck.py new / layouts with chapters, and the deck_check rules chapter, clause, separate and image kind.

Projects are built by tests/factory.py (fictional client Nordvik Ferries, product Tidewater Pass); the deck cases
change one thing in a fresh copy of the tender fixture and assert a code and its rule tag.
"""
import copy
import json
import re
from pathlib import Path

import pytest

import common
import deck
import deck_html
import factory

FIRST_SIX = ["cover", "understanding", "design", "interaction", "separate", "appendix"]


# ---------- helpers ----------

@pytest.fixture
def tender(tmp_path):
    """tender() -> a new copy of the tender fixture deck project."""
    count = [0]

    def make():
        count[0] += 1
        return factory.deck_project(tmp_path / f"copy{count[0]}", arch="tender")

    return make


def tmp_registry(tmp_path, monkeypatch, edit=None):
    """Copy the shipped architecture files to tmp_path/arch, let edit({id: dict}) change them, and point
    common.ARCHITECTURES_DIR at the copy."""
    folder = tmp_path / "arch"
    folder.mkdir()
    data = {}
    for f in Path(common.ARCHITECTURES_DIR).glob("*.json"):
        data[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    if edit:
        edit(data)
    for aid, d in data.items():
        (folder / f"{aid}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr(common, "ARCHITECTURES_DIR", str(folder))
    return folder


def deck_file(root):
    return Path(root) / "pack" / "proposal.html"


def read(root):
    return deck_file(root).read_text(encoding="utf-8")


def write(root, text):
    deck_file(root).write_text(text, encoding="utf-8", newline="\n")


def edit_deck(root, fn):
    """Parse the deck, let fn(tree) change it, write it back."""
    tree = deck_html.parse(read(root))
    fn(tree)
    write(root, tree.html())


def slide(tree, pid):
    return next(s for s in deck_html.slides_of(tree) if s.get("data-id") == pid)


def body_of(sec):
    return sec.find(lambda n: n.has_class("body")) or sec


def add_para(root, pid, markup):
    edit_deck(root, lambda t: body_of(slide(t, pid)).append(deck_html.element(markup)))


def msgs(root, code, rule=None, level=None):
    return [f.message for f in factory.has(root, code, rule) if level is None or f.level == level]


def set_brief(root, fn):
    p = str(Path(root) / "brief" / "brief.json")
    brief = common.read_json(p)
    fn(brief)
    common.write_json(p, brief)


def row_of(tree, n):
    return next(x for x in tree.iter() if x.get("data-clause") == n)


# ---------- registry ----------

def test_registry_shipped():
    reg = common.load_architectures()
    assert list(reg) == ["showcase", "tender"]
    assert common.DEFAULTS["architecture"] == "tender"
    t, s = reg["tender"], reg["showcase"]
    assert [c["id"] for c in t["chapters"]] == ["cover", "understanding", "design", "interaction", "graphics",
                                                 "separate", "appendix"]
    assert s["response"] == "design_points" and s["separate_submission"] == []
    assert s["allowed_kinds"] == ["render", "plan", "logo", "site"]
    assert "graphic" in t["allowed_kinds"]
    for a in reg.values():
        for c in a["chapters"]:
            assert c["title"]["en"] and c["title"]["zh"], (a["id"], c["id"])
    assert all(c["required"] == "never" for c in s["chapters"])


def test_registry_generic():
    path = Path(common.ARCHITECTURES_DIR) / "tender.json"
    text = path.read_text(encoding="utf-8").lower()
    for word in ("drink", "coffee", "beverage", "giveaway", "theme", "brand"):
        assert word not in text, word
    for c in json.loads(text)["chapters"]:
        assert not re.search(r"\d", c["purpose"]), c["id"]


def _edit(fn):
    return lambda d: fn(d["tender"])


INVALID = {
    "id_not_stem": _edit(lambda t: t.update(id="other")),
    "schema": _edit(lambda t: t.update(schema="architecture/2")),
    "response": _edit(lambda t: t.update(response="x")),
    "allowed_kind": _edit(lambda t: t.update(allowed_kinds=["render", "photo"])),
    "required": _edit(lambda t: t["chapters"][1].update(required="sometimes")),
    "no_kinds": _edit(lambda t: t["chapters"][3].pop("kinds")),
    "bad_kinds": _edit(lambda t: t["chapters"][3].update(kinds=["catering"])),
    "two_separate": _edit(lambda t: t["chapters"][2].update(separate=True)),
    "no_separate_chapter": _edit(lambda t: t["chapters"][5].update(separate=False)),
    "first_not_cover": _edit(lambda t: t["chapters"][0].update(roles=["text"])),
    "bogus_threshold": _edit(lambda t: t.update(thresholds={"bogus": 1})),
    "threshold_type": _edit(lambda t: t.update(thresholds={"fix_max": "3"})),
    "duplicate_id": _edit(lambda t: t["chapters"][2].update(id="understanding")),
    "bad_role": _edit(lambda t: t["chapters"][2].update(roles=["poster"])),
}


@pytest.mark.parametrize("case", sorted(INVALID))
def test_registry_invalid(tmp_path, monkeypatch, case):
    tmp_registry(tmp_path, monkeypatch, INVALID[case])
    with pytest.raises(common.InputError) as ei:
        common.load_architectures()
    assert ei.value.code == "C-INPUT"
    assert "tender" in ei.value.where


# ---------- the choice ----------

@pytest.mark.parametrize("case", ["default", "deck-style", "brief-over-style", "brief"])
def test_choice(make_project, case):
    kw = {"default": {}, "deck-style": {"style": {"thresholds": {"architecture": "showcase"}}},
          "brief-over-style": {"arch": "tender", "style": {"thresholds": {"architecture": "showcase"}}},
          "brief": {"arch": "showcase"}}[case]
    want = {"default": ("tender", "default"), "deck-style": ("showcase", "deck-style"),
            "brief-over-style": ("tender", "brief"), "brief": ("showcase", "brief")}[case]
    project = common.find_project(str(make_project(renders=False, **kw)))
    assert common.architecture_choice(project) == want
    assert project.architecture["id"] == want[0]


def test_unknown_architecture(make_project, capsys):
    root = make_project(renders=False, arch="showcase")
    assert deck.main(["new", "--project", str(root)]) == 0
    set_brief(root, lambda b: b.update(proposal={"architecture": "gala"}))
    project = common.find_project(str(root))
    assert project.architecture is None
    with pytest.raises(common.InputError) as ei:
        common.architecture_for(project)
    assert ei.value.code == "C-INPUT" and "known: showcase, tender" in str(ei.value)
    capsys.readouterr()
    assert deck.main(["check", "--project", str(root)]) == 2
    assert "unknown architecture 'gala'" in capsys.readouterr().err
    assert deck.main(["new", "--force", "--project", str(root)]) == 2


def test_arch_thresholds(tmp_path, monkeypatch, make_project):
    tmp_registry(tmp_path, monkeypatch, lambda d: d["tender"].update(thresholds={"appendix_pages_max": 5}))
    root = make_project(renders=False)
    assert common.find_project(str(root)).thresholds["appendix_pages_max"] == 5
    common.write_json(str(root / "brief" / "deck-style.json"), {"thresholds": {"appendix_pages_max": 2}})
    assert common.find_project(str(root)).thresholds["appendix_pages_max"] == 2


def test_required_chapters():
    reg = common.load_architectures()
    brief = factory.brief_dict()
    assert common.required_chapters(reg["tender"], brief) == FIRST_SIX
    bare = copy.deepcopy(brief)
    del bare["clauses"]
    assert common.required_chapters(reg["tender"], bare) == ["cover", "understanding", "design", "appendix"]
    graphic = copy.deepcopy(brief)
    graphic["graphics"] = [{"id": "GR1", "title": "Fleet story", "purpose": "Wall panel", "ratio": "2:3"}]
    assert common.required_chapters(reg["tender"], graphic) == [
        "cover", "understanding", "design", "interaction", "graphics", "separate", "appendix"]
    assert common.required_chapters(reg["showcase"], brief) == []


# ---------- brief.json ----------

def _brief_case(make_project, run_gates, fn):
    root = make_project(renders=False)
    set_brief(root, fn)
    return run_gates(root, "brief")


@pytest.mark.parametrize("case", ["proposal_str", "arch_int", "arch_unknown", "style_unknown", "ok"])
def test_brief_architecture(make_project, run_gates, has, case):
    root = make_project(renders=False)
    rule = {"proposal_str": "field", "arch_int": "field", "arch_unknown": "architecture",
            "style_unknown": "architecture", "ok": None}[case]
    if case == "proposal_str":
        set_brief(root, lambda b: b.update(proposal="x"))
    elif case == "arch_int":
        set_brief(root, lambda b: b.update(proposal={"architecture": 7}))
    elif case == "arch_unknown":
        set_brief(root, lambda b: b.update(proposal={"architecture": "gala"}))
    elif case == "style_unknown":
        common.write_json(str(root / "brief" / "deck-style.json"), {"thresholds": {"architecture": "gala"}})
    else:
        set_brief(root, lambda b: b.update(proposal={"architecture": "showcase"}))
    code, out, _ = run_gates(root, "brief")
    if rule is None:
        assert code == 0, out
        return
    assert code == 1
    hits = has(out, "G-BRIEF", rule)
    assert hits, out
    if rule == "architecture":
        assert "showcase, tender" in hits[0]


def _set_clause(i, **kw):
    def fn(b):
        b["clauses"][i].update(kw)
    return fn


CLAUSE_CASES = {
    "n_int": (_set_clause(0, n=2), "field"),
    "n_word": (_set_clause(0, n="two"), "clause-n"),
    "n_duplicate": (_set_clause(0, n="5"), "clause-n"),
    "kind": (_set_clause(0, kind="catering"), "clause-kind"),
    "points": (_set_clause(0, points=["D9"]), "points"),
    "source": (_set_clause(0, source=""), "source"),
    "text": (_set_clause(0, text=""), "field"),
    "not_list": (lambda b: b.update(clauses="x"), "field"),
    "removed": (lambda b: b.pop("clauses"), None),
}


@pytest.mark.parametrize("case", sorted(CLAUSE_CASES))
def test_brief_clauses(make_project, run_gates, has, case):
    fn, rule = CLAUSE_CASES[case]
    code, out, _ = _brief_case(make_project, run_gates, fn)
    if rule is None:
        assert code == 0, out
    else:
        assert code == 1 and has(out, "G-BRIEF", rule), out


GRAPHIC = {"id": "GR1", "title": "Fleet story", "purpose": "Wall panel", "ratio": "2:3",
           "refs": ["input/product.png"], "content": ["C1"]}


def _graphics(*items):
    return lambda b: b.update(graphics=[dict(GRAPHIC, **i) if i else dict(GRAPHIC) for i in items])


GRAPHIC_CASES = {
    "id": (_graphics({"id": "G1"}), "id"),
    "duplicate": (_graphics({}, {}), "id"),
    "ratio": (_graphics({"ratio": "tall"}), "ratio"),
    "ref_outside": (_graphics({"refs": ["brief/brand/logo.png"]}), "graphic-ref"),
    "ref_missing": (_graphics({"refs": ["input/missing.png"]}), "graphic-ref"),
    "content": (_graphics({"content": ["C9"]}), "content"),
    "valid": (_graphics({}), None),
}


@pytest.mark.parametrize("case", sorted(GRAPHIC_CASES))
def test_brief_graphics(make_project, run_gates, has, case):
    fn, rule = GRAPHIC_CASES[case]
    code, out, _ = _brief_case(make_project, run_gates, fn)
    if rule is None:
        assert code == 0, out
    else:
        assert code == 1 and has(out, "G-BRIEF", rule), out


# ---------- gates.py architectures ----------

def test_gates_architectures(make_project, run_gates, tmp_path):
    root = make_project(renders=False)
    code, out, _ = run_gates(root, "architectures")
    assert code == 0
    lines = out.splitlines()
    t = next(x for x in lines if x.startswith("tender"))
    assert t.endswith("[default, current]")
    assert any(x.startswith("showcase") for x in lines)
    assert ("  chapters: cover, understanding, design, interaction (if clause kind interaction), "
            "graphics (if graphics), separate (if clause kind execution/price), appendix") in lines
    assert lines[-1] == ("current: tender (from default); required chapters now: cover, understanding, design, "
                         "interaction, separate, appendix")
    code, out, _ = run_gates(root, "architectures", "--json")
    data = json.loads(out)
    assert code == 0 and data["default"] == data["current"] == "tender" and data["source"] == "default"
    assert data["required"] == FIRST_SIX
    assert [a["id"] for a in data["architectures"]] == ["tender", "showcase"]
    (tmp_path / "empty").mkdir()
    code, out, _ = run_gates(tmp_path / "empty", "architectures")
    assert code == 0 and "current" not in out and "tender" in out
    show = make_project(renders=False, arch="showcase")
    code, out, _ = run_gates(show, "architectures")
    lines = out.splitlines()
    assert next(x for x in lines if x.startswith("showcase")).endswith("[current]")
    assert next(x for x in lines if x.startswith("tender")).endswith("[default]")


# ---------- deck.py new and layouts ----------

def _new(root, capsys, *args):
    capsys.readouterr()
    code = deck.main(["new", *args, "--project", str(root)])
    return code, capsys.readouterr().out


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_new_tender_skeleton(make_project, capsys, lang):
    root = make_project(renders=False, lang=lang)
    code, out = _new(root, capsys)
    assert code == 0 and "architecture tender" in out and "optional: graphics" in out
    tree = deck_html.parse(read(root))
    slides = deck_html.slides_of(tree)
    assert [(s.get("data-id"), s.get("data-chapter")) for s in slides] == [(c, c) for c in FIRST_SIX]
    arch = common.load_architectures()["tender"]
    titles = {c["id"]: c["title"][lang] for c in arch["chapters"]}
    dividers = [s for s in slides if s.has_class("divider")]
    assert [s.get("data-id") for s in dividers] == ["understanding", "design", "interaction"]
    for s, number in zip(dividers, ("01", "02", "03")):
        assert next(n for n in s.iter() if n.get("data-slot") == "title").text() == titles[s.get("data-id")]
        assert next(n for n in s.iter() if n.has_class("dno")).text() == number
    appendix = slide(tree, "appendix")
    assert appendix.get("data-role") == "response" and appendix.get("data-part") == "appendix"
    sentence = common.load_labels(lang)["separate"]["sentence"]
    assert sentence in " ".join(deck_html.visible_text(slide(tree, "separate")).split())


def test_new_showcase(make_project, capsys):
    root = make_project(renders=False, arch="showcase")
    code, out = _new(root, capsys)
    assert code == 0
    slides = deck_html.slides_of(deck_html.parse(read(root)))
    assert len(slides) == 1 and slides[0].get("data-chapter") == "cover"
    assert any(x.startswith("optional: project") for x in out.splitlines())


def test_layouts_chapter(make_project, capsys):
    root = make_project(renders=False)
    capsys.readouterr()
    assert deck.main(["layouts", "--emit", "board", "--chapter", "design", "--project", str(root)]) == 0
    assert 'data-chapter="design"' in capsys.readouterr().out
    assert deck.main(["layouts", "--emit", "board", "--chapter", "nope", "--project", str(root)]) == 2
    assert "unknown chapter 'nope'" in capsys.readouterr().err
    with pytest.raises(SystemExit) as ei:
        deck.main(["layouts", "--chapter", "design", "--project", str(root)])
    assert ei.value.code == 2
    capsys.readouterr()
    assert deck.main(["layouts", "--project", str(root)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "architecture tender" in lines[0]
    assert next(x for x in lines if x.startswith("board  ")).endswith("chapters=design")
    assert any(x.startswith("statement:separate") for x in lines)
    show = make_project(renders=False, arch="showcase")
    assert deck.main(["layouts", "--project", str(show)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert next(x for x in lines if x.startswith("board  ")).endswith("chapters=concepts")


# ---------- deck_check ----------

def test_tender_fixture_clean(tmp_path, capsys):
    root = factory.deck_project(tmp_path, arch="tender")
    assert [f for f in factory.findings(root) if f.level == "error"] == []
    capsys.readouterr()
    assert deck.main(["check", "--project", str(root)]) == 0


def test_showcase_unchanged(tmp_path):
    root = factory.deck_project(tmp_path)

    def claims_as_response(tree):
        slide(tree, "claims").set("data-role", "response")

    edit_deck(root, claims_as_response)
    base = [(f.code, f.level, f.page) for f in factory.findings(root)]

    def noise(tree):
        for s in deck_html.slides_of(tree):
            s.set("data-chapter", None)
        for tr in [n for n in slide(tree, "claims").iter() if n.tag == "tr"][:2]:
            tr.set("data-clause", "zzz")

    edit_deck(root, noise)
    after = factory.findings(root)
    assert [(f.code, f.level, f.page) for f in after] == base
    for f in after:
        assert not (f.code == "D-STRUCT" and f.message.split(":")[0] in ("chapter", "clause", "separate"))
        assert not (f.code == "D-NUMBER" and f.message.startswith("separate"))


def test_chapter_missing(tender):
    root = tender()

    def drop(tree):
        row_of(tree, "5").find(lambda n: n.get("data-ref") is not None).set("data-ref", "a-board")
        slide(tree, "interaction").remove()

    edit_deck(root, drop)
    errors = msgs(root, "D-STRUCT", "chapter", "error")
    assert any("'interaction'" in m for m in errors), errors
    set_brief(root, lambda b: b.update(clauses=[c for c in b["clauses"] if c["n"] != "5"]))
    assert msgs(root, "D-STRUCT", "chapter", "error") == []


def test_chapter_unknown(tender):
    root = tender()
    edit_deck(root, lambda t: slide(t, "b-plan").set("data-chapter", "extras"))
    errors = msgs(root, "D-STRUCT", "chapter", "error")
    assert len(errors) == 1 and "not a chapter" in errors[0]


def test_chapter_order(tender):
    root = tender()

    def move(tree):
        inter, design = slide(tree, "interaction"), slide(tree, "design")
        inter.remove()
        parent = design.parent
        parent.children.insert(parent.children.index(design), inter)
        inter.parent = parent

    edit_deck(root, move)
    assert msgs(root, "D-STRUCT", "chapter", "error") == []
    warns = msgs(root, "D-STRUCT", "chapter", "warn")
    assert len(warns) == 1 and "'design' comes after 'interaction'" in warns[0]


def test_chapter_unchaptered(tender):
    root = tender()
    edit_deck(root, lambda t: slide(t, "cover").set("data-chapter", None))
    assert len([m for m in msgs(root, "D-STRUCT", "chapter", "error") if "belong to no chapter" in m]) == 1


def test_clause_rows(tender):
    def case(fn):
        root = tender()
        edit_deck(root, fn)
        return msgs(root, "D-STRUCT", "clause", "error")

    assert any("clause 5 has no row" in m for m in case(lambda t: row_of(t, "5").set("data-clause", None)))
    assert any("does not list" in m for m in case(lambda t: row_of(t, "5").set("data-clause", "9")))
    assert any("more than one row" in m for m in case(lambda t: row_of(t, "5").set("data-clause", "2")))
    assert any("no page reference" in m for m in case(
        lambda t: row_of(t, "2").find(lambda n: n.get("data-ref") is not None).set("data-ref", None)))
    assert any("must point to the separate-submission page" in m for m in case(
        lambda t: row_of(t, "8.1").find(lambda n: n.get("data-ref") is not None).set("data-ref", "a-board")))
    root = tender()
    set_brief(root, lambda b: b.pop("clauses"))
    assert msgs(root, "D-STRUCT", "clause") == []


def _append(markup):
    return lambda t: body_of(slide(t, "separate")).append(deck_html.element(markup))


def test_separate_page(tender):
    def numbers(root):
        return msgs(root, "D-NUMBER", "separate", "error")

    root = tender()
    edit_deck(root, _append("<p>about EUR 120,000</p>"))
    assert any("120,000" in m for m in numbers(root))
    assert any("other than the fixed labels" in m for m in msgs(root, "D-STRUCT", "separate", "error"))
    root = tender()
    edit_deck(root, _append("<p>3 weeks</p>"))
    assert numbers(root)
    root = tender()
    edit_deck(root, _append("<p>３</p>"))
    assert numbers(root)
    root = tender()
    edit_deck(root, lambda t: slide(t, "separate").find(lambda n: n.has_class("say")).set_text("Something else"))
    assert any("fixed sentence" in m for m in msgs(root, "D-STRUCT", "separate", "error"))
    root = tender()
    edit_deck(root, _append("<p>TODO</p>"))
    assert msgs(root, "D-TXT-INTERNAL", "todo", "error")
    root = tender()
    edit_deck(root, lambda t: slide(t, "appendix").set("data-chapter", None))
    assert any("has 3 pages" in m for m in msgs(root, "D-STRUCT", "separate", "error"))
    assert any("'appendix'" in m for m in msgs(root, "D-STRUCT", "chapter", "error"))


def test_clause_numbers_on_pages(tender):
    root = tender()
    add_para(root, "a-board", "<p>As clause 8.1 asks, the lounge stays open</p>")
    assert factory.has(root, "D-NUMBER") == [] and factory.has(root, "D-TXT-INTERNAL") == []
    root = tender()
    add_para(root, "a-board", "<p>D2</p>")
    assert msgs(root, "D-TXT-INTERNAL", "id")
    root = tender()
    set_brief(root, lambda b: b.update(graphics=[dict(GRAPHIC)]))
    add_para(root, "a-board", "<p>GR1</p>")
    assert msgs(root, "D-TXT-INTERNAL", "id")
    root = tender()
    add_para(root, "a-board", "<p>Tender p.3 item 2</p>")
    assert msgs(root, "D-TXT-INTERNAL", "source")


def test_kind_allowed(tender, tmp_path, monkeypatch):
    root = tender()
    (root / "pack" / "site.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>',
        encoding="utf-8")
    add_para(root, "understanding",
             '<figure class="pic contain"><img data-img="plan" alt="" src="site.svg"></figure>')
    assert factory.has(root, "D-IMG-FORBIDDEN") == []

    def no_site(d):
        d["tender"]["allowed_kinds"] = ["render", "plan", "logo"]

    tmp_registry(tmp_path, monkeypatch, no_site)
    hits = msgs(root, "D-IMG-FORBIDDEN", "kind")
    assert hits and "site image" in hits[0]


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_labels_separate(lang):
    sep = common.load_labels(lang)["separate"]
    for key in ("title", "sentence"):
        assert sep[key].strip()
        assert re.search(r"[0-9０-９]", sep[key]) is None
