"""deck_html: tree round trip, catalogue and emit, new and style, page references, text extraction, deck.py shape."""
import ast
import os
import re
from pathlib import Path

import pytest

import common
import deck
import deck_html
import factory

SCRIPTS = Path(deck.__file__).resolve().parent


@pytest.fixture
def deck_project(tmp_path):
    return factory.deck_project(tmp_path)


def run(root, *args):
    """deck.py in-process: exit code (the output is left to capsys)."""
    return deck.main([*args, "--project", str(root)])


def slides(text):
    return deck_html.slides_of(deck_html.parse(text))


def tokens_of(text):
    return deck_html.parse_vars(deck_html.TOKENS_RE.search(text).group(2))


def test_roundtrip(deck_project):
    src = open(deck_html.DEFAULT_TEMPLATE, encoding="utf-8-sig").read()
    assert deck_html.parse(src).html() == src
    text = (deck_project / "pack" / "proposal.html").read_text(encoding="utf-8")
    assert deck_html.parse(text).html() == text
    assert len(slides(text)) == 8


def test_layouts(make_project, capsys):
    root = make_project(renders=False)
    capsys.readouterr()
    assert run(root, "layouts") == 0
    lines = capsys.readouterr().out.splitlines()
    tpl = deck_html.load_template(deck_html.DEFAULT_TEMPLATE)
    assert len(lines) == 1 + len(tpl.examples)
    assert lines[0].startswith("budget_factor 1.8") and "lang en" in lines[0]
    board = next(x for x in lines if x.startswith("board "))
    assert "roles=board" in board and "images=render" in board and "name:14" in board
    assert any(x.startswith("cards:n3 ") and "repeat=cardx3" in x for x in lines)

    assert run(root, "layouts", "--emit", "board") == 0
    frag = capsys.readouterr().out
    sec = deck_html.element(frag)
    assert sec.get("data-role") == "board" and sec.get("data-id") == "" and sec.get("data-covers") == ""
    assert "data-roles" not in frag
    imgs = [n for n in sec.iter() if n.tag == "img"]
    assert imgs and all(n.get("src") == "" for n in imgs)

    assert run(root, "layouts", "--emit", "cards:n3") == 0
    en = deck_html.element(capsys.readouterr().out)
    assert next(s for s in deck_html.leaf_slots(en) if s.get("data-slot") == "title").get("data-max") == "40"

    assert run(root, "layouts", "--emit", "cards:n3", "--count", "5") == 0
    out = capsys.readouterr()
    sec = deck_html.element(out.out)
    cards = [n for n in sec.iter() if n.tag == "article" and n.has_class("card")]
    assert len(cards) == 5
    names = [s.get("data-slot") for s in deck_html.leaf_slots(sec)]
    assert [f"c{k}-title" for k in range(1, 6)] == [n for n in names if n.endswith("-title")]
    assert [n.text() for n in sec.iter() if n.has_class("num")] == ["01", "02", "03", "04", "05"]
    assert "no cards variant for 5 units" in out.err

    assert run(root, "layouts", "--emit", "cards:n3", "--count", "4") == 0
    out = capsys.readouterr()
    assert "n4" in deck_html.element(out.out).classes() and not out.err

    assert run(root, "layouts", "--emit", "overview", "--count", "2") == 0
    sec = deck_html.element(capsys.readouterr().out)
    assert [n.get("data-concept") for n in sec.iter() if n.tag == "article"] == ["A", "B"]

    assert run(root, "layouts", "--emit", "plan") == 0         # data-auto labels come from the labels file
    sec = deck_html.element(capsys.readouterr().out)
    assert [n.text() for n in sec.iter() if n.get("data-auto")] == ["Size", "Highest point", "Open sides"]

    assert run(root, "layouts", "--emit", "no-such-layout") == 2
    assert "unknown layout 'no-such-layout'" in capsys.readouterr().err
    assert run(root, "layouts", "--emit", "board", "--count", "2") == 2
    assert capsys.readouterr().err.startswith("error:")

    zh = make_project(lang="zh", renders=False)
    capsys.readouterr()
    assert run(zh, "layouts", "--emit", "cards:n3") == 0
    sec = deck_html.element(capsys.readouterr().out)
    assert next(s for s in deck_html.leaf_slots(sec) if s.get("data-slot") == "title").get("data-max") == "22"


def test_new_and_style(make_project, capsys):
    root = make_project(renders=False, style={"logo": "brand/logo.png"}, arch="showcase")
    deck_file = root / "pack" / "proposal.html"
    capsys.readouterr()
    assert run(root, "new") == 0
    text = deck_file.read_text(encoding="utf-8")
    assert len(slides(text)) == 1 and slides(text)[0].get("data-role") == "cover"
    assert '<html lang="en">' in text
    labels = common.load_labels("en")
    assert tokens_of(text)["--stamp"] == deck_html.css_string(labels["stamp"])
    logo = deck_html.parse(text).find(lambda n: n.tag == "img" and n.get("data-img") == "logo")
    assert logo.get("src") == "../brief/brand/logo.png"
    assert os.listdir(root / "pack") == ["proposal.html"]

    capsys.readouterr()
    assert run(root, "new") == 1
    assert "use --force" in capsys.readouterr().err
    assert deck_file.read_text(encoding="utf-8") == text
    deck_file.write_text(text + "\n<!-- edited -->\n", encoding="utf-8")
    assert run(root, "new", "--force") == 0
    backups = os.listdir(root / "work" / "backup")
    assert len(backups) == 1 and re.fullmatch(r"proposal\.\d{8}-\d{6}\.html", backups[0])
    assert "<!-- edited -->" in (root / "work" / "backup" / backups[0]).read_text(encoding="utf-8")
    assert deck_file.read_text(encoding="utf-8") == text
    assert os.listdir(root / "pack") == ["proposal.html"]

    style = common.read_json(str(root / "brief" / "deck-style.json")) if (root / "brief" / "deck-style.json").is_file() \
        else {}
    style["colors"] = {"primary": "#0B3D5C"}
    common.write_json(str(root / "brief" / "deck-style.json"), style)
    assert run(root, "style") == 0
    new = deck_file.read_text(encoding="utf-8")
    assert new != text and tokens_of(new)["--primary"] == "#0B3D5C"
    m, n = deck_html.TOKENS_RE.search(text), deck_html.TOKENS_RE.search(new)
    assert text[:m.start(2)] == new[:n.start(2)] and text[m.end(2):] == new[n.end(2):]
    assert os.listdir(root / "pack") == ["proposal.html"]

    plain = make_project(renders=False)                      # no deck-style: no logo, so no logo tile
    assert run(plain, "new") == 0
    assert "logo-tile" not in (plain / "pack" / "proposal.html").read_text(encoding="utf-8").split("<body>")[1]

    empty = make_project(renders=False)
    assert run(empty, "style") == 2                          # no deck yet
    assert "error:" in capsys.readouterr().err


def test_ref_pages(deck_project):
    project = common.find_project(str(deck_project))
    text = (deck_project / "pack" / "proposal.html").read_text(encoding="utf-8")
    root = deck_html.parse(text)
    refs = {t: e for _, t, e in deck_html.compute_refs(root, project, None)}
    assert refs == {"a-plan": "see p. 3", "D1": "see p. 2"}          # before a record, data-covers decides
    assert deck_html.refresh_refs(root, project, None) == 0 and root.html() == text

    review = {"pass1": {"coverage": [{"point": "D1", "page_id": "b-board", "quote": "x"}]}}
    assert deck_html.ref_pages(root, review)["D1"] == [4]
    assert deck_html.refresh_refs(root, project, review) == 1
    refs = {t: e for _, t, e in deck_html.compute_refs(root, project, review)}
    assert refs == {"a-plan": "see p. 3", "D1": "see p. 4"}
    gone = {"pass1": {"coverage": [{"point": "D1", "page_id": "no-such-page", "quote": "x"}]}}
    assert deck_html.ref_pages(root, gone)["D1"] == [2]               # a cited page that is gone is ignored

    fmt = project.labels["ref_formats"]
    assert deck_html.ref_text(fmt, [], None) == "" and deck_html.ref_text(fmt, [2], None) == "see p. 2"
    assert deck_html.ref_text(fmt, [2, 5], None) == "see pp. 2, 5"
    assert deck_html.ref_text(fmt, [2, 5], "num") == "02, 05"


def test_text_extraction():
    root = deck_html.parse(
        '<section class="slide" data-id="x"><h1 data-slot="t">Fish &amp; <b>chips</b><br>daily</h1>'
        '<script>var a=1;</script><figure><img src="a.png" alt="Quay view"></figure>'
        '<p>see <span data-ref="a-plan">see p. 3</span></p>'
        '<div data-slot="outer"><p data-slot="inner">Inner text</p><p>loose</p></div>'
        '<div data-slot="r">Go <span data-ref="D1">see p. 2</span></div></section>')
    sec = deck_html.slides_of(root)[0]
    assert deck_html.page_lines(sec) == ["Fish & chips daily", "[image]", "[ref:a-plan]", "Inner text",
                                         "Go [ref:D1]"]
    assert deck_html.page_text(sec).splitlines()[1] == "[image]"
    vis = deck_html.visible_text(sec)
    assert "Fish & chips daily" in vis and "see p." not in vis and "var a" not in vis
    assert vis.splitlines()[-1] == "Quay view"          # alt values come after the text


def test_deck_cli_only():
    tree = ast.parse((SCRIPTS / "deck.py").read_text(encoding="utf-8"))
    assert {n.name for n in tree.body if isinstance(n, ast.FunctionDef)} == {"build_parser", "main"}
