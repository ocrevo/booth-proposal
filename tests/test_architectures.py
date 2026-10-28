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
    assert ("  chapters: cover, understanding, design, interaction (if kind interaction), "
            "graphics (if kind graphics), separate (if kind execution/price), appendix") in lines
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


# ---------- A1b: deliverables, graphics trigger, coverage, separate list, auto text, mixed kinds ----------

@pytest.fixture
def rich(tmp_path):
    """rich() -> a new copy of the tender fixture whose brief also has a mixed clause (9) and four deliverables."""
    count = [0]

    def make():
        count[0] += 1
        return factory.deck_project(tmp_path / f"rich{count[0]}", arch="tender", rich=True)

    return make


def _set_deliverable(i, **kw):
    def fn(b):
        b["deliverables"][i].update(kw)
    return fn


def _rich_brief(fn=None):
    def edit(b):
        b["clauses"].append(copy.deepcopy(factory.MIXED_CLAUSE))
        b["deliverables"] = copy.deepcopy(factory.DELIVERABLES)
        if fn:
            fn(b)
    return edit


DELIVERABLE_CASES = {
    "id": (_set_deliverable(0, id="D1"), "id"),
    "duplicate": (_set_deliverable(1, id="DL1"), "id"),
    "title_missing": (lambda b: b["deliverables"][0].pop("title"), "field"),
    "title_digit": (_set_deliverable(0, title="Phase 2 scheme"), "title"),
    "title_fullwidth_digit": (_set_deliverable(0, title="Scheme ２"), "title"),
    "kind": (_set_deliverable(0, kind="catering"), "clause-kind"),
    "kind_missing": (lambda b: b["deliverables"][0].pop("kind"), "clause-kind"),
    "kind_empty_list": (_set_deliverable(0, kind=[]), "clause-kind"),
    "kind_repeated": (_set_deliverable(0, kind=["design", "design"]), "clause-kind"),
    "kind_bad_in_list": (_set_deliverable(0, kind=["design", "catering"]), "clause-kind"),
    "points": (_set_deliverable(0, points=["D9"]), "points"),
    "points_type": (_set_deliverable(0, points="D1"), "field"),
    "source": (_set_deliverable(0, source=""), "source"),
    "not_list": (lambda b: b.update(deliverables="x"), "field"),
    "valid": (lambda b: None, None),
    "kind_list_valid": (_set_deliverable(0, kind=["design", "execution"]), None),
}


@pytest.mark.parametrize("case", sorted(DELIVERABLE_CASES))
def test_brief_deliverables(make_project, run_gates, has, case):
    fn, rule = DELIVERABLE_CASES[case]

    def edit(b):
        _rich_brief()(b)
        fn(b)

    code, out, _ = _brief_case(make_project, run_gates, edit)
    if rule is None:
        assert code == 0, out
    else:
        assert code == 1 and has(out, "G-BRIEF", rule), out


CLAUSE_KIND_CASES = {
    "list": (_set_clause(0, kind=["design", "execution"]), None),
    "list_one": (_set_clause(0, kind=["price"]), None),
    "empty_list": (_set_clause(0, kind=[]), "clause-kind"),
    "list_unknown": (_set_clause(0, kind=["design", "catering"]), "clause-kind"),
    "list_repeated": (_set_clause(0, kind=["design", "design"]), "clause-kind"),
    "list_not_str": (_set_clause(0, kind=["design", 3]), "clause-kind"),
    "title": (_set_clause(0, title="Open entrance"), None),
    "title_digit": (_set_clause(0, title="Entrance 2"), "title"),
    "title_blank": (_set_clause(0, title=" "), "field"),
    "digit_text_separate_no_title": (_set_clause(2, text="Build schedule in 12 weeks"), "title"),
    "digit_text_price_no_title": (_set_clause(3, text="Overall price in 2 parts"), "title"),
    "digit_text_mixed_no_title": (_set_clause(0, text="Entrance 2 m wide", kind=["design", "price"]), "title"),
    "digit_text_separate_title": (_set_clause(2, text="Build schedule in 12 weeks", title="Build schedule"), None),
    "digit_text_design_no_title": (_set_clause(0, text="Entrance 2 m wide"), None),
    "no_digit_separate_no_title": (_set_clause(2, text="Build schedule and staff"), None),
}


@pytest.mark.parametrize("case", sorted(CLAUSE_KIND_CASES))
def test_brief_clause_kinds_and_title(make_project, run_gates, has, case):
    fn, rule = CLAUSE_KIND_CASES[case]
    code, out, _ = _brief_case(make_project, run_gates, fn)
    if rule is None:
        assert code == 0, out
    else:
        assert code == 1 and has(out, "G-BRIEF", rule), out


def test_brief_coverage_warning(make_project, run_gates, has):
    root = make_project(renders=False)
    code, out, _ = run_gates(root, "brief")
    assert code == 0 and not has(out, "G-BRIEF", "coverage")
    set_brief(root, lambda b: b["clauses"][1].update(points=[]))          # D2 is left in no clause
    code, out, _ = run_gates(root, "brief")
    hits = has(out, "G-BRIEF", "coverage")
    assert code == 0 and len(hits) == 1 and "D2" in hits[0], out
    set_brief(root, lambda b: b.update(deliverables=[
        {"id": "DL1", "title": "Design scheme", "kind": "design", "points": ["D2"], "source": "Tender p.5 list"}]))
    code, out, _ = run_gates(root, "brief")
    assert code == 0 and not has(out, "G-BRIEF", "coverage"), out         # a deliverable covers it
    set_brief(root, lambda b: (b.pop("deliverables"), b.pop("clauses")))
    code, out, _ = run_gates(root, "brief")
    assert code == 0 and not has(out, "G-BRIEF", "coverage"), out         # no clauses, no deliverables: no rule
    set_brief(root, lambda b: b.update(clauses=[], proposal={"architecture": "showcase"}))
    code, out, _ = run_gates(root, "brief")
    assert code == 0 and not has(out, "G-BRIEF", "coverage"), out


def test_coverage_in_check(rich):
    root = rich()
    assert msgs(root, "D-STRUCT", "points") == []
    set_brief(root, lambda b: (b["deliverables"][0].update(points=["D1"]), b["clauses"][1].update(points=[])))
    hits = msgs(root, "D-STRUCT", "points", "warn")
    assert len(hits) == 1 and "D2" in hits[0]
    assert [f for f in factory.findings(root) if f.level == "error"] == []
    set_brief(root, lambda b: b.update(proposal={"architecture": "showcase"}))
    assert msgs(root, "D-STRUCT", "points") == []


def test_required_chapters_by_kind():
    reg = common.load_architectures()["tender"]
    base = factory.brief_dict()
    assert "graphics" not in common.required_chapters(reg, base)

    def with_(**kw):
        b = copy.deepcopy(base)
        b.update(kw)
        return common.required_chapters(reg, b)

    graphic_clause = dict(factory.CLAUSES[0], n="3", kind="graphics")
    assert "graphics" in with_(clauses=base["clauses"] + [graphic_clause])
    assert "graphics" in with_(clauses=base["clauses"] + [dict(graphic_clause, kind=["design", "graphics"])])
    assert "graphics" in with_(deliverables=[factory.DELIVERABLES[1]])
    assert "graphics" in with_(graphics=[{"id": "GR1", "title": "Fleet story", "purpose": "Wall", "ratio": "2:3"}])
    assert "graphics" not in with_(deliverables=[factory.DELIVERABLES[0]])
    no_clauses = copy.deepcopy(base)
    del no_clauses["clauses"]
    only = copy.deepcopy(no_clauses)
    only["deliverables"] = [factory.DELIVERABLES[2]]                    # an execution deliverable
    assert common.required_chapters(reg, only) == ["cover", "understanding", "design", "separate", "appendix"]
    mixed = copy.deepcopy(no_clauses)
    mixed["clauses"] = [dict(factory.MIXED_CLAUSE)]
    assert "separate" in common.required_chapters(reg, mixed)
    assert common.kinds_of({"kind": ["design", "x", "price"]}) == ["design", "price"]
    assert common.kinds_of({"kind": "design"}) == ["design"] and common.kinds_of({}) == []


def test_if_kind_in_registry(tmp_path, monkeypatch):
    tender = common.load_architectures()["tender"]
    assert [(c["id"], c["kinds"]) for c in tender["chapters"] if c["required"] == "if-kind"] == [
        ("interaction", ["interaction"]), ("graphics", ["graphics"]), ("separate", ["execution", "price"])]
    for old in ("if-graphics", "if-clause-kind"):
        (tmp_path / old).mkdir()
        tmp_registry(tmp_path / old, monkeypatch, _edit(lambda t, old=old: t["chapters"][4].update(required=old)))
        with pytest.raises(common.InputError):
            common.load_architectures()


def test_separate_items():
    reg = common.load_architectures()
    brief = factory.brief_dict(rich=True)
    assert common.separate_items(reg["tender"], brief) == [
        "7 Build schedule and on-site staff", "8.1 Overall price and itemised price",
        "9 Lounge furniture delivery", "Schedule and headcount", "Itemised price"]
    assert common.separate_items(reg["showcase"], brief) == []
    assert common.separate_items(None, brief) == []
    assert common.separate_items(reg["tender"], factory.brief_dict()) == [
        "7 Build schedule and on-site staff", "8.1 Overall price and itemised price"]


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_new_emits_separate_list(make_project, capsys, lang):
    root = make_project(renders=False, lang=lang)
    set_brief(root, _rich_brief())
    code, out = _new(root, capsys)
    assert code == 0
    tree = deck_html.parse(read(root))
    items = [n for n in slide(tree, "separate").iter() if n.get("data-auto") == "separate.item"]
    assert [n.tag for n in items] == ["li"] * 5
    assert [" ".join(n.text().split()) for n in items] == common.separate_items(
        common.load_architectures()["tender"], common.read_json(str(root / "brief" / "brief.json")))
    assert [x.get("data-id") for x in deck_html.slides_of(tree)] == [
        "cover", "understanding", "design", "interaction", "graphics", "separate", "appendix"]
    assert [f for f in factory.findings(root) if f.code == "D-STRUCT" and f.message.startswith("separate")] == []


def test_emit_separate_items(make_project, capsys):
    root = make_project(renders=False, arch="showcase")
    capsys.readouterr()
    assert deck.main(["layouts", "--emit", "statement:separate", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    assert "data-auto" in out and "<li" not in out and "<ul" not in out        # no items, no empty list
    root = make_project(renders=False)
    assert deck.main(["layouts", "--emit", "statement:separate", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    assert out.count("<li") == 2 and "7 Build schedule" in out and "8.1 Overall price" in out
    assert deck.main(["layouts", "--emit", "statement", "--project", str(root)]) == 0
    assert "<li" not in capsys.readouterr().out


def test_separate_example_not_empty():
    tpl = deck_html.load_template(deck_html.DEFAULT_TEMPLATE)
    ex = deck_html.find_example(tpl, "statement:separate")
    keys = [n.get("data-auto") for n in ex.node.iter() if n.get("data-auto")]
    assert keys == ["separate.title", "separate.sentence", "separate.item"]
    assert any(n.tag == "ul" and n.has_class("items") for n in ex.node.iter())
    assert deck_html.find_example(tpl, "statement").variant == ""


def test_rich_fixture_clean(rich, capsys):
    root = rich()
    assert [f for f in factory.findings(root) if f.level == "error"] == []
    assert factory.has(root, "D-STRUCT", "points") == []
    capsys.readouterr()
    assert deck.main(["check", "--project", str(root)]) == 0


def test_table_emit_count(make_project, capsys):
    root = make_project(renders=False)
    for n in (2, 9, 12):
        capsys.readouterr()
        assert deck.main(["layouts", "--emit", "table", "--count", str(n), "--project", str(root)]) == 0
        out = capsys.readouterr().out
        assert out.count('data-repeat="row"') == n
        assert f'data-slot="r{n}-c"' in out and f'data-slot="r{n + 1}-c"' not in out


def _deliverable_row(tree, key):
    return next(x for x in tree.iter() if x.get("data-deliverable") == key)


def _has_ref(n):
    return n.get("data-ref") is not None


def test_deliverable_rows(rich):
    def case(fn):
        root = rich()
        edit_deck(root, fn)
        return msgs(root, "D-STRUCT", "deliverable", "error")

    assert case(lambda t: None) == []
    assert any("deliverable DL2 has no row" in m for m in case(
        lambda t: _deliverable_row(t, "DL2").set("data-deliverable", None)))
    assert any("does not list" in m for m in case(
        lambda t: _deliverable_row(t, "DL2").set("data-deliverable", "DL9")))
    assert any("more than one row" in m for m in case(
        lambda t: _deliverable_row(t, "DL2").set("data-deliverable", "DL1")))
    assert any("no page reference" in m for m in case(
        lambda t: _deliverable_row(t, "DL1").find(_has_ref).set("data-ref", None)))
    assert any("must point to the separate-submission page" in m for m in case(
        lambda t: _deliverable_row(t, "DL4").find(_has_ref).set("data-ref", "a-board")))
    assert any("must point to the separate-submission page" in m for m in case(
        lambda t: _deliverable_row(t, "DL3").find(_has_ref).set("data-ref", "graphics")))
    root = rich()
    set_brief(root, lambda b: b.pop("deliverables"))
    assert len(msgs(root, "D-STRUCT", "deliverable", "error")) == 4      # the rows now name unknown deliverables


def test_deliverables_without_rows(rich):
    root = rich()
    edit_deck(root, lambda t: [x.set("data-deliverable", None) for x in list(t.iter()) if x.get("data-deliverable")])
    errors = msgs(root, "D-STRUCT", "deliverable", "error")
    assert sorted(m.split()[2] for m in errors) == ["DL1", "DL2", "DL3", "DL4"]


def test_mixed_clause_refs(rich):
    def case(fn):
        root = rich()
        edit_deck(root, fn)
        return msgs(root, "D-STRUCT", "clause", "error")

    def refs_of_9(target):
        return lambda t: [r.set("data-ref", target) for r in row_of(t, "9").iter() if _has_ref(r)]

    assert case(lambda t: None) == []
    only_design = case(refs_of_9("a-board"))
    assert any("clause 9 (design, execution) must point to the separate-submission page as well" in m
               for m in only_design), only_design
    assert case(refs_of_9("separate")) == []
    # a pure execution clause still points only to the separate page
    assert any("clause 7 (execution) must point" in m for m in case(
        lambda t: row_of(t, "7").find(_has_ref).set("data-ref", "a-board")))
    # a design clause is not forced anywhere
    assert case(lambda t: row_of(t, "2").find(_has_ref).set("data-ref", "b-board")) == []


def test_mixed_kind_makes_separate_required(make_project):
    root = make_project(renders=False)
    set_brief(root, lambda b: b.update(clauses=[c for c in b["clauses"] if c["kind"] in ("design", "interaction")]
                                       + [copy.deepcopy(factory.MIXED_CLAUSE)]))
    project = common.find_project(str(root))
    assert common.required_chapters(project.architecture, project.brief) == [
        "cover", "understanding", "design", "interaction", "separate", "appendix"]


def test_clause_cards_on_any_page(rich):
    def card(clause, target="a-board"):
        return f'<div class="note" data-clause="{clause}"><span data-ref="{target}"></span></div>'

    def case(markup, kind="clause"):
        root = rich()
        add_para(root, "b-annotated", markup)
        return msgs(root, "D-STRUCT", kind, "error")

    assert case(card("2")) == []                                              # a card is not a second table row
    assert case(card("9", "separate")) == []
    assert any("does not list" in m for m in case(card("77")))
    assert any("no page reference" in m for m in case('<div data-clause="2">Entrance</div>'))
    assert any("must point to the separate-submission page" in m for m in case(card("7")))
    assert any("as well" in m for m in case(card("9")))
    deliverable = '<div data-deliverable="%s"><span data-ref="a-board"></span></div>'
    assert case(deliverable % "DL1", "deliverable") == []
    assert any("must point to the separate" in m for m in case(deliverable % "DL4", "deliverable"))
    assert any("does not list" in m for m in case(deliverable % "DL9", "deliverable"))
    assert any("no page reference" in m for m in case('<div data-deliverable="DL1">Scheme</div>', "deliverable"))


def test_clause_cards_ignored_in_showcase(tmp_path):
    root = factory.deck_project(tmp_path)
    add_para(root, "a-board", '<div data-clause="2">no ref</div>')
    assert not [m for m in msgs(root, "D-STRUCT") if m.startswith(("clause", "deliverable"))]


def test_separate_list_check(rich):
    def case(fn):
        root = rich()
        edit_deck(root, fn)
        return msgs(root, "D-STRUCT", "separate", "error")

    def items(t):
        return [n for n in slide(t, "separate").iter() if n.get("data-auto") == "separate.item"]

    assert case(lambda t: None) == []
    assert any("is not a clause or deliverable" in m for m in case(lambda t: items(t)[0].set_text("7 Something else")))
    assert any("lacks" in m and "Itemised price" in m for m in case(lambda t: items(t)[-1].remove()))
    assert any("other than" in m for m in case(lambda t: items(t)[0].set("data-auto", None)))
    assert any("other than" in m for m in case(_append("<ul><li>Extra item</li></ul>")))


def test_separate_page_without_list_stays_valid(tender):
    root = tender()

    def drop_list(tree):
        for ul in [n for n in slide(tree, "separate").iter() if n.tag == "ul"]:
            ul.remove()

    edit_deck(root, drop_list)
    assert msgs(root, "D-STRUCT", "separate", "error") == []


def test_separate_list_numbers(rich):
    def numbers(fn):
        root = rich()
        edit_deck(root, fn)
        return msgs(root, "D-NUMBER", "separate", "error")

    def items(t):
        return [n for n in slide(t, "separate").iter() if n.get("data-auto") == "separate.item"]

    assert numbers(lambda t: None) == []                          # 7, 8.1 and 9 are clause numbers
    assert any('"4"' in m for m in numbers(_append("<p>4</p>")))
    assert any('"4"' in m for m in numbers(lambda t: items(t)[3].set_text("Schedule and headcount 4")))
    assert any('"12"' in m for m in numbers(lambda t: items(t)[0].set_text("7 Build schedule in 12 weeks")))
    root = rich()
    set_brief(root, lambda b: b["clauses"][2].update(n="12"))     # a clause number with two digits
    edit_deck(root, lambda t: (row_of(t, "7").set("data-clause", "12"),
                               [r for r in t.iter() if r.get("data-auto") == "separate.item"][0]
                               .set_text("12 Build schedule and on-site staff")))
    assert msgs(root, "D-NUMBER", "separate", "error") == []


def test_clause_text_with_digits_on_separate_page(tmp_path):
    root = factory.deck_project(tmp_path / "x", arch="tender")
    set_brief(root, lambda b: b["clauses"][2].update(text="Build schedule in 12 weeks"))
    # without a title the list expects the clause text: the page no longer matches the brief
    assert msgs(root, "D-STRUCT", "separate", "error")
    set_brief(root, lambda b: b["clauses"][2].update(title="Build schedule and staff"))
    assert any("is not a clause or deliverable" in m for m in msgs(root, "D-STRUCT", "separate", "error"))


def test_text_marks_auto(tender, capsys):
    root = tender()
    capsys.readouterr()
    assert deck.main(["text", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    labels = common.load_labels("en")["separate"]
    block = re.split(r"=== \d+ separate \[text\] ===", out)[1].split("===")[0]
    lines = [x for x in block.splitlines() if x]
    assert lines == [f"[auto] {labels['title']}", f"[auto] {labels['sentence']}",
                     "[auto] 7 Build schedule and on-site staff", "[auto] 8.1 Overall price and itemised price"]
    assert "[auto]" not in re.split(r"=== \d+ a-board", out)[1].split("===")[0]    # slots stay unmarked


def test_page_lines_auto_flag():
    sec = deck_html.element('<section class="slide"><p data-auto="a.b">Label</p><p data-slot="x">Body</p>'
                            '<ul><li data-auto="separate.item">One</li><li data-auto="separate.item"></li></ul>'
                            '</section>')
    assert deck_html.page_lines(sec) == ["Body"]
    assert deck_html.page_lines(sec, True) == ["[auto] Label", "Body", "[auto] One"]
    assert deck_html.page_text(sec, True).splitlines()[0] == "[auto] Label"


def test_auto_text_not_in_review_hash(tender):
    """The separate list is validated against the brief; its text is not part of the review hash."""
    import deck_check
    root = tender()
    project = common.find_project(str(root))
    tree = deck_html.parse(read(root))
    before = deck_check.page_hashes(project, tree, deck_check.Images(project))["separate"]["text_sha256"]
    items = [n for n in slide(tree, "separate").iter() if n.get("data-auto") == "separate.item"]
    items[0].set_text("7 Something else")
    after = deck_check.page_hashes(project, tree, deck_check.Images(project))["separate"]["text_sha256"]
    assert before == after


def test_export_rich_tender(rich, capsys):
    """The rich tender deck (mixed clause, deliverables, separate list, nine-row table) renders and exports."""
    import deck_render
    if deck_render.find_browser() is None:
        pytest.skip("no Chrome/Edge")
    root = rich()

    def first_line(pid):
        return deck_html.page_lines(slide(deck_html.parse(read(root)), pid))[0]

    capsys.readouterr()
    assert deck.main(["render", "--project", str(root)]) == 0, capsys.readouterr().out
    assert factory.record(root, {
        "pass1": {"reviewer": "subagent", "unexplained": [], "internal_notes": [], "pending": [],
                  "coverage": [{"point": "D1", "page_id": "a-board", "quote": first_line("a-board")},
                               {"point": "D2", "page_id": "cover", "quote": first_line("cover")}]},
        "pass2": {"reviewer": "self", "findings": [
            {"page_id": "compare", "kind": "other", "note": "checked", "resolved": True}]}}) == 0
    capsys.readouterr()
    code = deck.main(["export", "--project", str(root)])
    out = capsys.readouterr()
    assert code == 0, out.out + out.err
    assert out.out.strip().endswith("pack/proposal.pdf: 14 pages")


def test_deliverable_id_is_internal(rich):
    root = rich()
    add_para(root, "a-board", "<p>Our design scheme answers DL1</p>")
    assert [m for m in msgs(root, "D-TXT-INTERNAL", "id", "error") if "DL1" in m]
    root = rich()
    add_para(root, "a-board", "<p>Tender p.5 list</p>")
    assert msgs(root, "D-TXT-INTERNAL", "source")
    root = rich()
    add_para(root, "a-board", "<p>The design scheme and the graphic designs follow</p>")
    assert msgs(root, "D-TXT-INTERNAL") == []


# ---------- A1b review fixes: separate page substrings, title rule by architecture, review hash ----------

def test_brief_title_rule_reads_architecture(tmp_path, monkeypatch, make_project, run_gates, has):
    """The separate kinds come from the architecture: with only "price" separate, an execution clause may keep
    a text with digits and no title."""
    tmp_registry(tmp_path, monkeypatch, lambda d: d["tender"].update(separate_submission=["price"]))
    code, out, _ = _brief_case(make_project, run_gates, _set_clause(2, text="Build schedule in 12 weeks"))
    assert code == 0, out
    code, out, _ = _brief_case(make_project, run_gates, _set_clause(3, text="Overall price in 2 parts"))
    assert code == 1 and has(out, "G-BRIEF", "title"), out
    assert "add a short title without digits" in out


def test_brief_title_rule_showcase(make_project, run_gates):
    """No separate-submission kind in showcase: a clause text with digits and no title is fine."""
    root = make_project(renders=False)
    set_brief(root, lambda b: (b.update(proposal={"architecture": "showcase"}),
                               b["clauses"][2].update(text="Build schedule in 12 weeks")))
    code, out, _ = run_gates(root, "brief")
    assert code == 0, out


SEPARATE_WORDS = {"en": "pricing", "zh": "报价"}     # a word of the fixed sentence of each language


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_separate_items_equal_sentence_words(tmp_path, lang):
    """An item that is a substring of the fixed sentence is no leftover text (the page is read by its DOM)."""
    root = factory.deck_project(tmp_path / lang, lang=lang, arch="tender", rich=True)
    word = SEPARATE_WORDS[lang]
    assert word in common.load_labels(lang)["separate"]["sentence"]
    set_brief(root, lambda b: b["deliverables"][2].update(title=word))
    edit_deck(root, lambda t: [n for n in slide(t, "separate").iter()
                               if n.get("data-auto") == "separate.item"][3].set_text(word))
    assert msgs(root, "D-STRUCT", "separate", "error") == []
    assert msgs(root, "D-NUMBER", "separate", "error") == []
    add_para(root, "separate", "<p>" + word + " extra</p>")       # text that is not a list item still counts
    assert any("other than" in m for m in msgs(root, "D-STRUCT", "separate", "error"))


def _old_record(project, root):
    """A review record as written before A1b: the hash of the page text without auto text."""
    import deck_check
    tree = deck_html.parse(read(root))
    pages = deck_check.page_hashes(project, tree, deck_check.Images(project))
    for s in deck_html.slides_of(tree):
        if s.get("data-id") in pages:
            pages[s.get("data-id")]["text_sha256"] = common.sha256_text("\n".join(deck_html.page_lines(s)))
    common.write_json(project.path("work", "deck-review.json"),
                      {"schema": "deck-review/1", "pages": pages, "recorded_at": "2026-01-01T00:00:00Z"})
    return pages


@pytest.mark.parametrize("arch", ["showcase", "tender"])
def test_old_review_record_stays_current(tmp_path, capsys, arch):
    import deck_check
    root = factory.deck_project(tmp_path, arch=arch)
    project = common.find_project(str(root))
    old = _old_record(project, root)
    now = deck_check.page_hashes(project, deck_html.parse(read(root)), deck_check.Images(project))
    assert {k: v["text_sha256"] for k, v in now.items()} == {k: v["text_sha256"] for k, v in old.items()}
    capsys.readouterr()
    assert deck.main(["text", "--diff", "--project", str(root)]) == 0
    assert "no changes since" in capsys.readouterr().out


def test_text_prints_auto_with_old_record(tender, capsys):
    root = tender()
    _old_record(common.find_project(str(root)), root)
    capsys.readouterr()
    assert deck.main(["text", "--project", str(root)]) == 0
    assert "[auto]" in capsys.readouterr().out
