"""deck.py export (the X-* gate) and deck.py status. Browser-free except test_export_ok."""
import os
from pathlib import Path

import pytest

import deck
import deck_html
import deck_render
import factory

WHITELIST = {"proposal.html", "proposal.pdf", "site.svg"}


def deck_file(root):
    return Path(root) / "pack" / "proposal.html"


def tree(root):
    return deck_html.parse(deck_file(root).read_text(encoding="utf-8"))


def edit(root, pid, fn):
    t = tree(root)
    fn(next(s for s in deck_html.slides_of(t) if s.get("data-id") == pid))
    deck_file(root).write_text(t.html(), encoding="utf-8", newline="\n")


def say(root, pid, name, text):
    edit(root, pid, lambda s: next(n for n in deck_html.leaf_slots(s) if n.get("data-slot") == name).set_text(text))


def first_line(root, pid):
    s = next(s for s in deck_html.slides_of(tree(root)) if s.get("data-id") == pid)
    return deck_html.page_lines(s)[0]


def review_input(root, *, resolved=True, pending=()):
    """A valid pass 1 and pass 2 for the fixture deck."""
    return {
        "pass1": {
            "reviewer": "subagent", "unexplained": [], "internal_notes": [],
            "coverage": [{"point": "D1", "page_id": "a-board", "quote": first_line(root, "a-board")},
                         {"point": "D2", "page_id": "cover", "quote": first_line(root, "cover")}],
            "pending": list(pending)},
        "pass2": {"reviewer": "self", "findings": [
            {"page_id": "compare", "kind": "other", "note": "checked", "resolved": resolved}]}}


def ready(tmp_path, name, **kw):
    """A fixture deck with a current render.json and a full review record: only the browser is missing."""
    root = factory.deck_project(tmp_path / name)
    factory.write_render_json(root)
    assert factory.record(root, review_input(root, **kw)) == 0
    return root


def export(root, capsys):
    capsys.readouterr()
    code = deck.main(["export", "--project", str(root)])
    out = capsys.readouterr()
    return code, out.out, out.err


def pdf_of(root):
    return Path(root) / "pack" / "proposal.pdf"


@pytest.fixture
def no_browser(monkeypatch):
    monkeypatch.setattr(deck_render, "find_browser", lambda arg=None: None)


def test_export_refused(tmp_path, capsys, has, no_browser):
    def refused(name, code, rule, mutate=None, *, extra=()):
        root = ready(tmp_path, name)
        if mutate:
            mutate(root)
        status, out, err = export(root, capsys)
        assert status == 1, (name, out, err)
        found = has(out, code, rule)
        assert found, (name, out)
        assert "RESULT: FAIL" in out
        assert not pdf_of(root).exists()
        for text in extra:
            assert text in found[0], (name, found[0])
        return root, out

    # the clean fixture is only stopped by the missing browser
    root = ready(tmp_path, "clean")
    status, out, err = export(root, capsys)
    assert status == 3 and has(out, "X-PDF", "browser") and not pdf_of(root).exists()

    # X-CHECK
    root, out = refused("todo", "X-CHECK", "errors", lambda r: say(r, "compare", "c1-next", "TODO next step"),
                        extra=("D-TXT-INTERNAL",))
    assert "run deck.py check" in out

    # X-RENDER
    refused("no-render", "X-RENDER", "missing", lambda r: (Path(r) / "work" / "render.json").unlink())
    refused("unmeasured", "X-RENDER", "unmeasured", lambda r: factory.write_render_json(r, measured=False))

    def touch_layout(r):                       # a layout-only edit: the render is stale, the review is not
        edit(r, "a-board", lambda s: s.set_classes(s.classes() + ["tight"]))

    root, out = refused("stale-render", "X-RENDER", "stale", touch_layout, extra=("deck.py render",))
    assert not has(out, "X-REVIEW")
    row = {"page": 4, "page_id": "b-board", "slot": "para", "px": 64, "chars": 12}
    root, out = refused("overflow", "X-RENDER", "overflow", lambda r: factory.write_render_json(r, overflow=[row]),
                        extra=("page 4 b-board para", "64 px"))
    assert not has(out, "X-CHECK")             # the overflow is reported once, by X-RENDER

    # X-REVIEW
    refused("no-record", "X-REVIEW", "missing", lambda r: (Path(r) / "work" / "deck-review.json").unlink())

    def add_slide(r):
        new = factory.fill(factory._emit(r, "statement"), None, (), {"data-id": "extra"})
        text = deck_file(r).read_text(encoding="utf-8")
        text = text.replace('<section class="slide table"', new + '\n<section class="slide table"', 1)
        deck_file(r).write_text(text, encoding="utf-8", newline="\n")

    root, out = refused("new-page", "X-REVIEW", "page", add_slide, extra=("extra",))

    root, out = refused("edited", "X-REVIEW", "stale",
                        lambda r: say(r, "compare", "c1-next", "A sentence written after the review"),
                        extra=("deck.py text --diff", "page 7 compare"))

    def swap_image(r):                         # an image change is a stale page too
        edit(r, "b-plan", lambda s: [n for n in s.iter() if n.tag == "img"][0]
             .set("src", "../concepts/set-2/B/plan.png"))

    refused("image", "X-REVIEW", "stale", swap_image, extra=("b-plan",))

    root = ready(tmp_path, "open")
    assert factory.record(root, review_input(root, resolved=False)) == 0
    status, out, err = export(root, capsys)
    assert status == 1 and has(out, "X-REVIEW", "open") and not pdf_of(root).exists()
    assert factory.record(root, {"pass2": {"findings": [
        {"page_id": "compare", "kind": "other", "note": "checked", "resolved": True}]}}) == 0
    assert export(root, capsys)[0] == 3            # resolved: only the browser is missing

    # a pending finding needs a keep decision in the record
    root = ready(tmp_path, "pending")
    say(root, "compare", "c1-next", "Wider than ever before")
    item = {"code": "D-TXT-PENDING", "page_id": "compare", "text": "than ever", "decision": "keep", "note": "brand"}
    assert factory.record(root, review_input(root, pending=[item])) == 0
    factory.write_render_json(root)
    status, out, err = export(root, capsys)
    assert status == 3 and not has(out, "X-REVIEW"), out                  # decided keep: the gate is open
    say(root, "b-board", "para", "A familiar entrance")                   # a new pending word, no decision recorded
    factory.write_render_json(root)
    status, out, err = export(root, capsys)
    found = has(out, "X-REVIEW", "pending")
    assert status == 1 and found and '"familiar"' in found[0] and not pdf_of(root).exists()
    assert has(out, "X-REVIEW", "stale")

    # a stale proposal.pdf is left alone by a refused export, and status says it is older than the deck
    root = ready(tmp_path, "old-pdf")
    pdf_of(root).write_bytes(b"%PDF-1.4 stale")
    os.utime(pdf_of(root), (1_600_000_000, 1_600_000_000))
    say(root, "compare", "c1-next", "Edited after the review")
    assert export(root, capsys)[0] == 1
    assert pdf_of(root).read_bytes() == b"%PDF-1.4 stale"
    capsys.readouterr()
    assert deck.main(["status", "--project", str(root)]) == 0
    status_out = capsys.readouterr().out
    assert "pack/proposal.pdf older than the deck" in status_out
    assert len(status_out.strip().splitlines()) == 1                      # one paragraph
    assert "8 slides" in status_out and "set-2/B (A)" in status_out and "set-1/A (B, lead)" in status_out
    assert "render: stale" in status_out and "review: recorded " in status_out and "1 pages changed since" in status_out
    assert "check: not run" in status_out
    os.utime(pdf_of(root), None)
    capsys.readouterr()
    deck.main(["status", "--project", str(root)])
    assert "pack/proposal.pdf newer than the deck" in capsys.readouterr().out

    # status without a record, a render or a pdf; a check marks itself current or stale
    root = factory.deck_project(tmp_path / "bare")
    capsys.readouterr()
    assert deck.main(["check", "--json", "--project", str(root)]) == 0
    capsys.readouterr()
    deck.main(["status", "--project", str(root)])
    status_out = capsys.readouterr().out
    assert "render: not run" in status_out and "review: none" in status_out and "export: none" in status_out
    assert "check: 0 errors" in status_out and "(current)" in status_out
    say(root, "compare", "c1-next", "Changed after the check")
    deck.main(["status", "--project", str(root)])
    assert "(stale)" in capsys.readouterr().out
    deck_file(root).unlink()
    deck.main(["status", "--project", str(root)])
    assert capsys.readouterr().out.strip() == "No deck yet; run deck.py new."
    assert deck.main(["export", "--project", str(root)]) == 2


def test_export_ok(tmp_path, capsys):
    if deck_render.find_browser() is None:
        pytest.skip("no Chrome/Edge")
    root = factory.deck_project(tmp_path)
    capsys.readouterr()
    assert deck.main(["render", "--project", str(root)]) == 0, capsys.readouterr().out
    assert factory.record(root, review_input(root)) == 0
    status, out, err = export(root, capsys)
    assert status == 0, out + err
    assert out.strip().endswith("pack/proposal.pdf: 8 pages")
    assert deck_render.pdf_pages(str(pdf_of(root))) == 8
    assert {p.name for p in (Path(root) / "pack").iterdir()} <= WHITELIST


def test_export_pdf_pages(tmp_path, capsys, has, monkeypatch):
    """X-PDF pages: exit 3 when the browser writes no PDF, or a PDF whose page count is not the slide count."""
    root = ready(tmp_path, "pdf-pages")
    monkeypatch.setattr(deck_render, "find_browser", lambda arg=None: "fake-browser")

    def fake_chrome(write):
        def run(browser, args, budget, timeout=180):
            target = next(a for a in args if a.startswith("--print-to-pdf=")).split("=", 1)[1]
            if write:
                Path(target).write_bytes(b"%PDF-1.4\n" + b"<< /Type /Page >>\n" * write)
            return type("Done", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        return run

    for written, text in ((0, "no PDF was written"), (1, "the PDF has 1 pages for 8 slides")):
        monkeypatch.setattr(deck_render, "chrome", fake_chrome(written))
        status, out, err = export(root, capsys)
        found = has(out, "X-PDF", "pages")
        assert status == 3 and found and text in found[0], (written, out, err)
        assert not pdf_of(root).exists()
    monkeypatch.setattr(deck_render, "chrome", fake_chrome(8))          # the right count passes the gate
    status, out, err = export(root, capsys)
    assert status == 0 and out.strip().endswith("pack/proposal.pdf: 8 pages") and pdf_of(root).exists()
