"""deck.py text, text --diff and review --record: page text blocks, shape and content errors, merging."""
import json
from pathlib import Path

import pytest

import common
import deck
import deck_check
import deck_html
import factory

RENDER_A = "../concepts/set-2/B/renders/hero-v2.png"
PLAN_A = "../concepts/set-2/B/plan.png"


@pytest.fixture
def dp(tmp_path):
    return factory.deck_project(tmp_path)


def deck_file(root):
    return Path(root) / "pack" / "proposal.html"


def tree(root):
    return deck_html.parse(deck_file(root).read_text(encoding="utf-8"))


def slide(root, pid):
    return next(s for s in deck_html.slides_of(tree(root)) if s.get("data-id") == pid)


def edit(root, pid, fn):
    t = deck_html.parse(deck_file(root).read_text(encoding="utf-8"))
    fn(next(s for s in deck_html.slides_of(t) if s.get("data-id") == pid))
    deck_file(root).write_text(t.html(), encoding="utf-8", newline="\n")


def say(root, pid, name, text):
    edit(root, pid, lambda s: next(n for n in deck_html.leaf_slots(s) if n.get("data-slot") == name).set_text(text))


def first_line(root, pid):
    return deck_html.page_lines(slide(root, pid))[0]


def pass1(root, **extra):
    """A valid pass 1: D1 and D2 covered with verbatim quotes, one note on b-board and two on compare."""
    data = {
        "reviewer": "subagent",
        "unexplained": [{"page_id": "compare", "quote": first_line(root, "compare"), "action": "kept"}],
        "internal_notes": [{"page_id": "b-board", "quote": first_line(root, "b-board"), "action": "rewritten"},
                           {"page_id": "compare", "quote": "c", "action": "kept"}],
        "coverage": [{"point": "D1", "page_id": "a-board", "quote": first_line(root, "a-board")},
                     {"point": "D2", "page_id": "cover", "quote": first_line(root, "cover")}],
        "pending": [],
    }
    data.update(extra)
    return data


def pass2(*findings):
    return {"reviewer": "self", "findings": list(findings)}


def finding(pid, resolved=True, kind="other"):
    return {"page_id": pid, "kind": kind, "note": "checked", "resolved": resolved}


def recorded(root):
    return json.loads((Path(root) / "work" / "deck-review.json").read_text(encoding="utf-8"))


def blocks(out):
    """{slide id: block lines} of deck.py text output."""
    result, current = {}, None
    for line in out.splitlines():
        if line.startswith("=== "):
            current = line.split()[2]
            result[current] = [line]
        elif current is not None:
            result[current].append(line)
    return result


def run(root, *args):
    return deck.main([*args, "--project", str(root)])


# ---------- text and --diff ----------

def test_text_and_diff(dp, capsys):
    capsys.readouterr()
    assert run(dp, "text") == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "=== 1 cover [cover] ==="
    shown = blocks(out)
    assert list(shown) == ["cover", "a-board", "a-plan", "b-board", "b-plan", "b-annotated", "compare", "claims"]
    assert "[image]" in shown["b-annotated"] and "[ref:a-plan]" not in shown["b-annotated"]
    assert any("[ref:a-plan]" in line for line in shown["compare"])
    assert any("[ref:D1]" in line for line in shown["compare"])
    assert shown["claims"][0] == "=== 8 claims [signoff] ==="
    assert shown["cover"][1] == "[image]"                     # the render is the first thing on the cover

    assert run(dp, "text", "--diff") == 2
    assert capsys.readouterr().err.startswith("error: no work/deck-review.json")

    assert factory.record(dp, {"pass1": pass1(dp), "pass2": pass2()}) == 0
    capsys.readouterr()
    assert run(dp, "text", "--diff") == 0
    assert capsys.readouterr().out.startswith("no changes since ")

    say(dp, "compare", "c1-next", "A new sentence about the next step")
    assert run(dp, "text", "--diff") == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "CHANGED compare (text)"
    assert list(blocks(out)) == ["compare"] and "A new sentence about the next step" in out
    assert len([x for x in out.splitlines() if x.startswith(("CHANGED", "ADDED", "REMOVED"))]) == 1

    edit(dp, "b-plan", lambda s: [n for n in s.iter() if n.tag == "img"][0].set("src", PLAN_A))
    edit(dp, "a-board", lambda s: next(n for n in deck_html.leaf_slots(s) if n.get("data-slot") == "para")
         .set_text("Changed"))
    assert run(dp, "text", "--diff") == 0
    lines = capsys.readouterr().out.splitlines()
    assert "CHANGED b-plan (images)" in lines and "CHANGED a-board (text)" in lines

    edit(dp, "b-board", lambda s: [n for n in s.iter() if n.tag == "img"][0].set("src", PLAN_A))
    say(dp, "b-board", "para", "Changed too")
    assert run(dp, "text", "--diff") == 0
    assert "CHANGED b-board (text+images)" in capsys.readouterr().out.splitlines()

    t = tree(dp)
    deck_html.slides_of(t)[4].remove()                       # b-plan is gone, a new page is added
    new = factory.fill(factory._emit(dp, "statement"), None, (), {"data-id": "extra"})
    text = t.html().replace('<section class="slide table"', new + "\n<section class=\"slide table\"", 1)
    deck_file(dp).write_text(text, encoding="utf-8", newline="\n")
    assert run(dp, "text", "--diff") == 0
    lines = capsys.readouterr().out.splitlines()
    assert "REMOVED b-plan" in lines and "ADDED extra" in lines

    deck_file(dp).unlink()
    assert run(dp, "text") == 2 and capsys.readouterr().err.startswith("error: no pack/proposal.html")


# ---------- content errors ----------

def test_record_errors(dp, capsys):
    assert factory.record(dp, {"pass1": pass1(dp), "pass2": pass2()}) == 0
    path = Path(dp) / "work" / "deck-review.json"
    before = path.read_bytes()
    capsys.readouterr()

    bad = pass1(dp)
    bad["coverage"][0]["quote"] = "words that are not on the page"
    assert factory.record(dp, {"pass1": bad}) == 1
    err = capsys.readouterr().err
    assert err.strip() == "error: coverage D1 quote not found on a-board"
    assert path.read_bytes() == before

    say(dp, "compare", "c1-next", "Wider than ever before")
    assert factory.record(dp, {"pass1": pass1(dp)}) == 1
    err = capsys.readouterr().err
    assert 'error: pending D-TXT-PENDING compare "than ever" has no decision' in err
    assert path.read_bytes() == before

    item = {"code": "D-TXT-PENDING", "page_id": "compare", "text": "than ever", "decision": "narrates_reference",
            "note": "compares with the old stand"}
    assert factory.record(dp, {"pass1": pass1(dp, pending=[item])}) == 1
    err = capsys.readouterr().err
    assert 'error: compare still contains "than ever" decided narrates_reference; rewrite it' in err
    assert path.read_bytes() == before

    item["decision"] = "keep"
    assert factory.record(dp, {"pass1": pass1(dp, pending=[item])}) == 0
    assert capsys.readouterr().err == ""
    assert recorded(dp)["pass1"]["pending"] == [item]
    # the decision is kept while the page does not change; a pass-2 record alone is accepted
    assert factory.record(dp, {"pass2": pass2(finding("compare"))}) == 0

    say(dp, "compare", "c1-next", "Wider than ever before, and again")      # the page changed: decide again
    assert factory.record(dp, {"pass2": pass2(finding("compare"))}) == 1
    assert 'has no decision' in capsys.readouterr().err
    # a word spelled in another case is the same word
    item = dict(item, text="Than Ever", decision="keep")
    assert factory.record(dp, {"pass1": pass1(dp, pending=[item])}) == 0
    # two errors at once are both reported
    bad = pass1(dp)
    bad["coverage"][1]["quote"] = "not there"
    say(dp, "b-board", "para", "Even more than before")
    assert factory.record(dp, {"pass1": bad}) == 1
    err = capsys.readouterr().err.splitlines()
    assert len([x for x in err if x.startswith("error: ")]) == 3


# ---------- shape errors ----------

def test_record_shape(dp, capsys):
    good = {"pass1": pass1(dp), "pass2": pass2(finding("compare"))}

    def broken(path, value):
        data = json.loads(json.dumps(good))
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return data

    cases = [
        (["pass2", "findings", 0, "kind"], "bogus", "pass2.findings[0].kind"),
        (["pass2", "findings", 0, "resolved"], "yes", "pass2.findings[0].resolved"),
        (["pass2", "findings", 0, "page_id"], "no-such-page", "pass2.findings[0].page_id"),
        (["pass2", "reviewer"], "robot", "pass2.reviewer"),
        (["pass1", "reviewer"], "user", "pass1.reviewer"),
        (["pass1", "unexplained", 0, "action"], "ignored", "pass1.unexplained[0].action"),
        (["pass1", "internal_notes", 1, "action"], "fixed", "pass1.internal_notes[1].action"),
        (["pass1", "coverage", 1, "point"], "D9", "pass1.coverage[1].point"),
        (["pass1", "coverage", 0, "quote"], "", "pass1.coverage[0].quote"),
        (["pass1", "coverage", 0, "page_id"], "nowhere", "pass1.coverage[0].page_id"),
        (["pass1", "pending"], [{"code": "D-NUMBER", "page_id": "compare", "text": "x", "decision": "keep",
                                 "note": ""}], "pass1.pending[0].code"),
        (["pass1", "pending"], [{"code": "D-TXT-PENDING", "page_id": "compare", "text": "x", "decision": "maybe",
                                 "note": ""}], "pass1.pending[0].decision"),
        (["pass1", "coverage"], "none", "pass1.coverage"),
        (["pass1"], ["x"], "pass1"),
    ]
    for path, value, where in cases:
        capsys.readouterr()
        assert factory.record(dp, broken(path, value)) == 2, where
        err = capsys.readouterr().err
        assert err.startswith("ERROR   C-INPUT ") and f":{where}:" in err, (where, err)
        assert not (Path(dp) / "work" / "deck-review.json").exists()

    assert factory.record(dp, {}) == 2                                   # neither pass
    assert "C-INPUT" in capsys.readouterr().err
    assert factory.record(dp, {"pass1": {"coverage": []}}) == 2           # no reviewer, none recorded
    assert "pass1.reviewer" in capsys.readouterr().err
    bad = Path(dp) / "work" / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert run(dp, "review", "--record", str(bad)) == 2
    assert "C-INPUT" in capsys.readouterr().err
    assert run(dp, "review", "--record", str(Path(dp) / "work" / "missing.json")) == 2
    assert factory.record(dp, good) == 0


# ---------- merge ----------

def test_record_merge(dp, capsys):
    project = common.find_project(str(dp))
    first = {"pass1": pass1(dp), "pass2": pass2(finding("a-board"), finding("compare", kind="mismatch"))}
    assert factory.record(dp, first) == 0
    out = capsys.readouterr().out
    assert out.strip() == "recorded: 8 pages, 2 coverage quotes, 0 pending decisions, 2 pass-2 findings"
    rec = recorded(dp)
    assert rec["schema"] == "deck-review/1" and rec["recorded_at"]
    assert list(rec["pages"]) == ["cover", "a-board", "a-plan", "b-board", "b-plan", "b-annotated", "compare", "claims"]
    for h in rec["pages"].values():
        assert len(h["text_sha256"]) == 64 and isinstance(h["image_sha256s"], list)
    assert rec["pages"]["claims"]["image_sha256s"] == []
    assert len(rec["pages"]["cover"]["image_sha256s"]) == 2          # the render and the logo
    assert rec["pass1"]["reviewer"] == "subagent" and rec["pass2"]["reviewer"] == "self"
    assert len(rec["pass1"]["internal_notes"]) == 2 and len(rec["pass2"]["findings"]) == 2

    say(dp, "compare", "c1-next", "A changed sentence")
    assert factory.record(dp, {"pass2": {"findings": [finding("compare")]}}) == 0      # no reviewer: the old one stays
    again = recorded(dp)
    assert again["pass2"]["reviewer"] == "self" and again["pass1"]["reviewer"] == "subagent"
    assert [i["page_id"] for i in again["pass1"]["internal_notes"]] == ["b-board"]    # compare's notes are gone
    assert again["pass1"]["unexplained"] == []
    assert [i["point"] for i in again["pass1"]["coverage"]] == ["D1", "D2"]           # other pages' items stay
    assert [i["page_id"] for i in again["pass2"]["findings"]] == ["a-board", "compare"]
    assert again["pass2"]["findings"][0] == first["pass2"]["findings"][0]
    assert again["pass2"]["findings"][1]["kind"] == "other"                            # replaced by the new item
    assert again["pages"]["compare"] != rec["pages"]["compare"]
    assert {k: v for k, v in again["pages"].items() if k != "compare"} == \
        {k: v for k, v in rec["pages"].items() if k != "compare"}

    # a layout-only edit changes no hash
    images = deck_check.Images(common.find_project(str(dp)))
    hashes = deck_check.page_hashes(project, tree(dp), images)
    edit(dp, "a-board", lambda s: s.set_classes(s.classes() + ["tight"]))
    edit(dp, "a-board", lambda s: s.set("style", "--accent:#1F5FAE"))
    assert deck_check.page_hashes(project, tree(dp), images) == hashes
    assert run(dp, "text", "--diff") == 0
    assert "no changes since " in capsys.readouterr().out

    # naming a page in a list replaces that page's items of that list only
    assert factory.record(dp, {"pass1": {"internal_notes": [
        {"page_id": "b-board", "quote": "q", "action": "kept"}]}}) == 0
    third = recorded(dp)
    assert third["pass1"]["internal_notes"] == [{"page_id": "b-board", "quote": "q", "action": "kept"}]
    assert [i["point"] for i in third["pass1"]["coverage"]] == ["D1", "D2"]

    # a page that is gone loses its items
    t = tree(dp)
    deck_html.slides_of(t)[3].remove()                                  # b-board
    deck_file(dp).write_text(t.html(), encoding="utf-8", newline="\n")
    assert factory.record(dp, {"pass2": {"findings": []}}) == 0
    last = recorded(dp)
    assert "b-board" not in last["pages"] and last["pass1"]["internal_notes"] == []
    assert len(last["pages"]) == 7


# ---------- references/review.md, deck part (step 13) ----------

REVIEW_MD = Path(common.SKILL_DIR) / "references" / "review.md"
DECK_ANCHORS = ["deck.py text", "text --diff", "review --record", "narrates_reference", '"self"', "pass1", "pass2",
                "contact.png"]
SCAN_BRIEF = Path(__file__).resolve().parent.parent / "output" / "run-051-v2" / "brief" / "brief.json"


def test_review_md_deck_anchors():
    text = REVIEW_MD.read_text(encoding="utf-8")
    deck_part = text[text.index("## Proposal review"):]
    assert [a for a in DECK_ANCHORS if a not in deck_part] == []
    if not SCAN_BRIEF.is_file():
        pytest.skip("no output/run-051-v2/brief/brief.json for the client-word scan")
    brief = json.loads(SCAN_BRIEF.read_text(encoding="utf-8-sig"))
    terms = [x for x in brief["client"]["names"] + brief["protected_terms"] + brief["do_not_mention"] if len(x) >= 2]
    assert [x for x in terms if x.lower() in text.lower()] == []
