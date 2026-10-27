"""deck.py render: draft PDF, previews, contact sheet, measurement; and the pack/ whitelist."""
import json
from pathlib import Path

import pytest

import common
import deck
import deck_html
import deck_render
import factory
import render

needs_browser = pytest.mark.skipif(deck_render.find_browser() is None, reason="no Chrome/Edge")

WHITELIST = {"proposal.html", "proposal.pdf", "site.svg"}


def deck_file(root):
    return Path(root) / "pack" / "proposal.html"


def tree(root):
    return deck_html.parse(deck_file(root).read_text(encoding="utf-8"))


def edit(root, pid, fn):
    t = tree(root)
    fn(next(s for s in deck_html.slides_of(t) if s.get("data-id") == pid))
    deck_file(root).write_text(t.html(), encoding="utf-8", newline="\n")


def rendered(root):
    return json.loads((Path(root) / "work" / "render.json").read_text(encoding="utf-8"))


def pack_names(root):
    return {p.name for p in (Path(root) / "pack").iterdir()}


def run_render(root, capsys):
    capsys.readouterr()
    code = deck.main(["render", "--project", str(root)])
    return code, capsys.readouterr().out


@needs_browser
def test_render_outputs(tmp_path, capsys):
    root = factory.deck_project(tmp_path)
    before = deck_file(root).read_text(encoding="utf-8")
    edit(root, "compare", lambda s: [n for n in s.iter() if n.get("data-ref") == "a-plan"][0].set_text("see p. 99"))
    assert "see p. 99" in deck_file(root).read_text(encoding="utf-8")
    code, out = run_render(root, capsys)
    assert code == 0, out
    work = Path(root) / "work"
    for name in ("proposal-draft.pdf", "preview/slide-01.png", "preview/slide-08.png", "contact.png", "render.json"):
        assert (work / name).is_file(), name
    info = rendered(root)
    assert info["schema"] == "render/1" and info["measured"] is True
    assert info["slides"] == 8 and info["pdf_pages"] == 8 and info["previews"] == 8
    text = deck_file(root).read_text(encoding="utf-8")
    assert "see p. 99" not in text and text == before                  # the reference text was recomputed
    assert info["deck_sha256"] == common.sha256_text(text)
    assert "updated 1 page reference(s)" in out and "check: 0 errors" in out
    assert pack_names(root) == {"proposal.html"}
    assert not list((Path(root) / "pack").glob(".*"))                  # no probe or temp file is left behind
    assert deck.main(["check", "--project", str(root)]) == 0

    # a second render finds nothing to update; a missing deck is a usage error
    code, out = run_render(root, capsys)
    assert code == 0 and "updated" not in out
    deck_file(root).unlink()
    assert deck.main(["render", "--project", str(root)]) == 2


@needs_browser
def test_render_measures(tmp_path, capsys):
    root = factory.deck_project(tmp_path)
    edit(root, "b-board", lambda s: next(n for n in deck_html.leaf_slots(s) if n.get("data-slot") == "para")
         .set_text("A very long sentence about the stand. " * 40))
    # a reviewed render of 200 x 133 px, chosen and shown on a-board
    small = tmp_path / "small.png"
    small.write_bytes(factory.png_bytes(factory._next_rgb(), size=(200, 133)))
    assert render.main(["import", str(small), "--concept", "set-2/B", "--view", "hero", "--project", str(root)]) == 0
    name = "hero-v3.png"
    assert (Path(root) / "concepts/set-2/B/renders" / name).is_file()
    (Path(root) / "concepts/set-2/B/concept.md").write_text(f"---\nchosen: renders/{name}\n---\nNotes.\n",
                                                            encoding="utf-8", newline="\n")
    factory.review_pass(root, f"concepts/set-2/B/renders/{name}")
    edit(root, "a-board", lambda s: [n for n in s.iter() if n.tag == "img"][0]
         .set("src", f"../concepts/set-2/B/renders/{name}"))
    code, out = run_render(root, capsys)
    assert code == 0, out
    info = rendered(root)
    assert info["measured"] is True
    hits = [e for e in info["overflow"] if e["page_id"] == "b-board" and e["slot"] == "para"]
    assert hits and hits[0]["page"] == 4 and hits[0]["px"] > 0 and hits[0]["chars"] > 0
    ups = [e for e in info["upscale"] if e["page_id"] == "a-board"]
    assert ups and ups[0]["factor"] > 1.3 and ups[0]["page"] == 2 and ups[0]["src"].endswith(name)
    assert "b-board para" in out and "image enlarged" in out
    # the measured results reach the check (the deck itself did not change, so the render is current)
    codes = {(f.code, f.page_id) for f in factory.findings(root)}
    assert ("D-OVERFLOW", "b-board") in codes and ("D-LAYOUT", "a-board") in codes
    assert deck.main(["check", "--project", str(root)]) == 1


def test_render_no_browser(tmp_path, capsys, monkeypatch):
    root = factory.deck_project(tmp_path)
    monkeypatch.setattr(deck_render, "find_browser", lambda arg=None: None)
    code, out = run_render(root, capsys)
    assert code == 3 and "no Chrome or Edge found" in out
    assert not (Path(root) / "work" / "render.json").exists()


def test_pack_whitelist(tmp_path, capsys):
    """Every command on the fixture leaves only whitelisted names in pack/ (render and export need a browser)."""
    root = factory.deck_project(tmp_path)
    p = ["--project", str(root)]
    record = Path(root) / "work" / "deck-review.input.json"
    common.write_json(str(record), {"pass2": {"reviewer": "self", "findings": []}})
    steps = [["new", "--force"], ["style"], ["layouts"], ["check", "--json"], ["text"], ["review", "--record", str(record)]]
    if deck_render.find_browser() is not None:
        steps += [["render"], ["export"]]
    for step in steps:
        capsys.readouterr()
        deck.main([*step, *p])
        assert pack_names(root) <= WHITELIST, (step, pack_names(root))
    assert any((Path(root) / "work" / "backup").glob("proposal.*.html"))
