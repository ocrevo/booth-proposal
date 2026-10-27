"""deck_check: image provenance, placement, structure, references, text lint, claims, numbers, layout, read-only check.

Every case changes one thing in a copy of the fixture deck (factory.deck_project) and asserts a code and its rule tag
(the message starts with the tag). Cases that change the deck text restore it; cases that change files use a fresh copy.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

import booth_geometry
import common
import deck
import deck_check
import deck_html
import factory
import render

SCRIPTS = Path(deck.__file__).resolve().parent
RENDER_B = "../concepts/set-1/A/renders/hero-v2.png"        # the lead concept, shown as B
RENDER_A = "../concepts/set-2/B/renders/hero-v2.png"        # shown as A
QUAD = "10,8 50,8 50,30 10,30"


@pytest.fixture
def dp(tmp_path):
    return factory.deck_project(tmp_path)


@pytest.fixture
def fresh(tmp_path):
    """fresh() -> a new copy of the fixture project (for cases that change files)."""
    count = [0]

    def make(lang="en"):
        count[0] += 1
        return factory.deck_project(tmp_path / f"copy{count[0]}", lang)

    return make


# ---------- helpers ----------

def deck_file(root):
    return Path(root) / "pack" / "proposal.html"


def read(root):
    return deck_file(root).read_text(encoding="utf-8")


def write(root, text):
    deck_file(root).write_text(text, encoding="utf-8", newline="\n")


@contextmanager
def edit(root):
    """The parsed deck; written back when the block ends."""
    tree = deck_html.parse(read(root))
    yield tree
    write(root, tree.html())


@contextmanager
def changed(root):
    """Whatever the block does to the deck text is undone afterwards."""
    orig = read(root)
    try:
        yield
    finally:
        write(root, orig)


def sec(tree, pid):
    return next(s for s in deck_html.slides_of(tree) if s.get("data-id") == pid)


def slot(tree, pid, name):
    return next(n for n in deck_html.leaf_slots(sec(tree, pid)) if n.get("data-slot") == name)


def say(root, pid, name, markup):
    with edit(root) as t:
        slot(t, pid, name).set_inner(deck_html.fragment(markup))


def image(root, pid, src, index=0):
    with edit(root) as t:
        [n for n in sec(t, pid).iter() if n.tag == "img"][index].set("src", src)


def hit(root, code, rule=None):
    return factory.has(root, code, rule)


def codes(root):
    return {f.code for f in factory.findings(root)}


def rules(root, code):
    return {f.message.split(":")[0] for f in factory.findings(root) if f.code == code}


def set_chosen(root, key, name, blocked=None):
    text = f"---\nchosen: renders/{name}\n" + (f"blocked: renders/{blocked}\n" if blocked else "") + "---\nNotes.\n"
    (Path(root) / "concepts" / key / "concept.md").write_text(text, encoding="utf-8", newline="\n")


def rewrite(root, old, new):
    text = read(root)
    assert old in text
    write(root, text.replace(old, new))


def new_slide(root, spec, **attrs):
    """A slide fragment from deck.py layouts --emit, filled."""
    return factory.fill(factory._emit(root, spec), None, (), attrs)


def insert_before(root, pid, fragment):
    text = read(root)
    mark = f'data-id="{pid}"'
    start = text.rfind("<section", 0, text.index(mark))
    write(root, text[:start] + fragment.rstrip("\n") + "\n\n" + text[start:])


def make_link(link, target):
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        return done.returncode == 0 and os.path.isdir(link)
    return False


def tree_hashes(root):
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def cli(*args):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, str(SCRIPTS / "deck.py"), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", env=env)


# ---------- baseline ----------

@pytest.mark.parametrize("lang", ["en", "zh"])
def test_baseline_clean(tmp_path, lang, capsys):
    root = factory.deck_project(tmp_path, lang)
    found = factory.findings(root)
    assert [f for f in found if f.level in ("error", "pending")] == [], found
    capsys.readouterr()
    assert deck.main(["check", "--project", str(root)]) == 0
    assert "RESULT: PASS" in capsys.readouterr().out
    res = deck_check.run_check(common.find_project(str(root)))
    assert res.slides == 8 and res.pending == [] and len(res.deck_sha256) == 64


# ---------- D-IMG-URL ----------

def test_d_img_url(dp, tmp_path):
    other = tmp_path / "outside"
    other.mkdir()
    (other / "a.png").write_bytes(factory.png_bytes(factory._next_rgb()))

    def src(value):
        image(dp, "b-board", value)

    for value in ("data:image/png;base64,AAAA", "https://x.test/a.png", "//x.test/a.png", "file:///C:/x/a.png"):
        with changed(dp):
            src(value)
            assert hit(dp, "D-IMG-URL", "scheme"), value
    with changed(dp):
        with edit(dp) as t:
            [n for n in sec(t, "b-board").iter() if n.tag == "img"][0].set(
                "srcset", "a.png 1x, https://x.test/b.png 2x")
        assert hit(dp, "D-IMG-URL", "scheme")
    with changed(dp):
        with edit(dp) as t:
            sec(t, "a-plan").append(deck_html.element("<div style=\"background:url('http://x.test/a.png')\"></div>"))
        assert hit(dp, "D-IMG-URL", "scheme")
    with changed(dp):
        rewrite(dp, "</head>", '<style>@import "http://x.test/a.css";</style>\n</head>')
        found = hit(dp, "D-IMG-URL", "scheme")
        assert found and found[0].page is None
    with changed(dp):
        rewrite(dp, "<head>", '<head>\n<base href="../">')
        assert any("<base>" in f.message for f in hit(dp, "D-IMG-URL", "scheme"))
    with changed(dp):
        src("../concepts/set-1/A/renders/hero-v9.png")
        assert hit(dp, "D-IMG-URL", "missing")
    with changed(dp):
        src("")
        assert hit(dp, "D-IMG-URL", "missing")
    with changed(dp):
        src(str(other / "a.png"))                                   # an absolute Windows path with backslashes
        assert hit(dp, "D-IMG-URL", "outside")
    with changed(dp):
        src((other / "a.png").as_posix())
        assert hit(dp, "D-IMG-URL", "outside")
    with changed(dp):                                               # an in-page link is not an image
        say(dp, "compare", "c1-next", '<a href="#cover">back</a>')
        assert not hit(dp, "D-IMG-URL")
    with changed(dp):                                               # a junction or symlink is followed
        link = dp / "concepts" / "link"
        if make_link(link, other):
            src("../concepts/link/a.png")
            assert hit(dp, "D-IMG-URL", "outside")
        else:
            pytest.skip("cannot create a symlink or junction")


# ---------- D-IMG-FORBIDDEN ----------

def test_d_img_forbidden(fresh, tmp_path):
    root = fresh()
    shutil.copyfile(root / "input/refs/set-1/r01.png", root / "concepts/set-1/A/renders/hero-v5.png")
    image(root, "b-board", "../concepts/set-1/A/renders/hero-v5.png")
    found = hit(root, "D-IMG-FORBIDDEN", "forbidden")
    assert found and "input/refs/set-1/r01.png" in found[0].message and found[0].page == 4

    root = fresh()
    (root / "brief" / "media").mkdir()
    (root / "brief/media/slide-6.png").write_bytes(factory.png_bytes(factory._next_rgb()))
    image(root, "b-board", "../brief/media/slide-6.png")
    assert hit(root, "D-IMG-FORBIDDEN", "forbidden")

    root = fresh()
    shutil.copyfile(root / "input/refs/set-1/r01.png", root / "brief/brand/logo.png")   # the deck-style logo
    assert hit(root, "D-IMG-FORBIDDEN", "logo-ref") and not hit(root, "D-IMG-FORBIDDEN", "forbidden")

    root = fresh()
    (root / "brief/notes.png").write_bytes(factory.png_bytes(factory._next_rgb()))
    image(root, "b-board", "../brief/notes.png")
    assert hit(root, "D-IMG-FORBIDDEN", "kind")

    root = fresh()
    geo = root / "concepts/set-1/A/geometry.json"
    assert booth_geometry.main(["massing", str(geo), str(geo.parent / "massing"), "--views", "hero",
                                "--size", "600x400", "--project", str(root)]) == 0
    image(root, "b-plan", "../concepts/set-1/A/massing-hero.png")
    assert hit(root, "D-IMG-FORBIDDEN", "massing")

    root = fresh()
    chosen = root / "concepts/set-2/B/renders/hero-v2.png"
    out = root / "concepts/set-2/B/renders/hero-v8.png"
    assert render.main(["label", str(chosen), "--title", "T", "--out", str(out), "--project", str(root)]) == 0
    image(root, "a-board", "../concepts/set-2/B/renders/hero-v8.png")
    assert hit(root, "D-IMG-FORBIDDEN", "label")


# ---------- D-IMG-RENDER ----------

def test_d_img_render(fresh, tmp_path, capsys):
    root = fresh()
    with open(root / "concepts/set-1/A/renders/hero-v2.png", "ab") as f:
        f.write(b"x")
    assert hit(root, "D-IMG-RENDER", "sidecar")

    for mode in ("fix", "logo"):
        root = fresh()
        rel = factory.add_render(root, "set-1/A", "hero-v6.png", mode=mode, base="input/refs/set-1/r01.png")
        set_chosen(root, "set-1/A", "hero-v6.png")
        factory.review_pass(root, rel)
        write(root, read(root).replace("set-1/A/renders/hero-v2.png", "set-1/A/renders/hero-v6.png"))
        assert hit(root, "D-IMG-RENDER", "chain"), mode
        assert rules(root, "D-IMG-RENDER") == {"chain"}

    root = fresh()
    ext = tmp_path / "ext.png"
    ext.write_bytes(factory.png_bytes(factory._next_rgb()))
    assert render.main(["import", str(ext), "--concept", "set-2/B", "--view", "hero", "--project", str(root)]) == 0
    set_chosen(root, "set-2/B", "hero-v3.png")
    image(root, "a-board", "../concepts/set-2/B/renders/hero-v3.png")
    assert hit(root, "D-IMG-RENDER", "review")
    assert rules(root, "D-IMG-RENDER") == {"review"}

    root = fresh()
    image(root, "a-board", "../concepts/set-2/A/renders/hero-v2.png")      # reviewed, chosen, but not selected
    assert rules(root, "D-IMG-RENDER") == {"unselected"}

    root = fresh()
    factory.review_pass(root, "concepts/set-1/A/renders/hero-v1.png")
    image(root, "b-board", "../concepts/set-1/A/renders/hero-v1.png")
    assert rules(root, "D-IMG-RENDER") == {"not-chosen"}

    root = fresh()
    set_chosen(root, "set-1/A", "hero-v2.png", blocked="hero-v2.png")
    assert "blocked" in rules(root, "D-IMG-RENDER")

    root = fresh()
    geo = root / "concepts/set-1/A/geometry.json"
    spec = json.loads(geo.read_text(encoding="utf-8"))
    spec["title"] = "B changed after the plan"
    geo.write_text(json.dumps(spec), encoding="utf-8")
    found = hit(root, "D-IMG-RENDER", "stale")
    assert found and "draw_plan.py plan" in found[0].message and found[0].page_id == "b-plan"
    assert rules(root, "D-IMG-RENDER") == {"stale"}

    root = fresh()                                                  # a plan without its sidecar
    (root / "concepts/set-2/B/plan.json").unlink()
    assert hit(root, "D-IMG-RENDER", "sidecar")


def test_logo_composited_ok(fresh, monkeypatch, capsys):
    root = fresh()
    monkeypatch.chdir(root)
    base = "concepts/set-1/A/renders/hero-v2.png"
    code = render.main(["logo", base, "--logo", "brief/brand/logo.png", "--quad", QUAD, "--project", str(root)])
    assert code == 0, capsys.readouterr()
    out = root / "concepts/set-1/A/renders/hero-v3.png"
    assert out.is_file()
    set_chosen(root, "set-1/A", "hero-v3.png")
    write(root, read(root).replace("set-1/A/renders/hero-v2.png", "set-1/A/renders/hero-v3.png"))
    assert [f for f in factory.findings(root) if f.level == "error"] == []


def test_c_legacy_v1(fresh):
    root = fresh()
    side = root / "concepts/set-1/A/renders/hero-v2.json"
    common.write_json(str(side), {"image": "hero-v2.png", "timestamp": "2026-01-01T00:00:00", "mode": "hero",
                                  "input_images": ["input/refs/set-1/r01.png"]})
    found = factory.findings(root)
    legacy = [f for f in found if f.code == "C-LEGACY"]
    assert legacy and all(f.level == "warn" for f in legacy)
    assert not [f for f in found if f.code == "D-IMG-RENDER"]
    assert [f for f in found if f.level == "error"] == []


def test_g_select_none(fresh):
    root = fresh()
    (root / "brief" / "selection.json").unlink()
    found = factory.findings(root)
    assert len([f for f in found if f.code == "G-SELECT"]) == 1
    assert [f.level for f in found if f.code == "G-SELECT"] == ["error"]
    assert not hit(root, "D-IMG-RENDER", "unselected") and not hit(root, "D-STRUCT", "board")


# ---------- D-PLACE ----------

def test_d_place(dp):
    with changed(dp):                                              # a render in figure.pic
        with edit(dp) as t:
            sec(t, "b-board").find(lambda n: n.tag == "figure").set_classes(["pic"])
        assert hit(dp, "D-PLACE", "figure") and not hit(dp, "D-PLACE", "hero")
    with changed(dp):                                              # a render as a CSS background
        with edit(dp) as t:
            sec(t, "a-plan").append(deck_html.element(
                f"<div style=\"background:url('{RENDER_B}')\"></div>"))
        assert hit(dp, "D-PLACE", "figure")
    with changed(dp):                                              # a plain render on a materials page
        with edit(dp) as t:
            sec(t, "b-board").set("data-role", "materials")
        assert hit(dp, "D-PLACE", "hero") and not hit(dp, "D-PLACE", "figure")
    with changed(dp):                                              # the same in figure.render.annotated
        with edit(dp) as t:
            sec(t, "b-board").set("data-role", "materials")
            sec(t, "b-board").find(lambda n: n.tag == "figure").set_classes(["render", "annotated"])
        assert not hit(dp, "D-PLACE")


# ---------- D-STRUCT ----------

def test_d_struct(dp):
    def tweak(fn):
        with changed(dp):
            with edit(dp) as t:
                fn(t)
            return rules(dp, "D-STRUCT")

    assert "id" in tweak(lambda t: sec(t, "b-plan").set("data-id", None))
    assert "id" in tweak(lambda t: sec(t, "b-plan").set("data-id", "a-plan"))
    assert "id" in tweak(lambda t: sec(t, "b-plan").set("data-id", "B Plan"))
    assert "role" in tweak(lambda t: sec(t, "b-plan").set("data-role", "hero"))
    assert "role" in tweak(lambda t: sec(t, "b-plan").set("data-role", None))
    assert "cover" in tweak(lambda t: sec(t, "cover").remove())
    assert "board" in tweak(lambda t: sec(t, "a-board").remove())
    assert "board" in tweak(lambda t: sec(t, "a-board").set("data-concept", "C"))
    assert "nest" in tweak(lambda t: sec(t, "b-board").find(lambda n: n.tag == "figure").append(
        deck_html.element('<figure class="render"></figure>')))
    assert "placeholder" in tweak(lambda t: sec(t, "compare").append(
        deck_html.element('<div class="placeholder">x</div>')))
    with changed(dp):                                              # an appendix page too, and it is an error
        with edit(dp) as t:
            sec(t, "claims").append(deck_html.element('<div class="placeholder">x</div>'))
        found = hit(dp, "D-STRUCT", "placeholder")
        assert found and found[0].level == "error" and found[0].page_id == "claims"
    assert tweak(lambda t: None) == set()


# ---------- D-REF ----------

def test_d_ref(dp):
    refs = {"D1": "see p. 2", "a-plan": "see p. 3"}
    assert not hit(dp, "D-REF")

    def ref(old, new=None, text=None):
        with edit(dp) as t:
            node = t.find(lambda n: n.get("data-ref") == old)
            if new is not None:
                node.set("data-ref", new)
            if text is not None:
                node.set_text(text)

    with changed(dp):
        ref("D1", "D9")
        assert hit(dp, "D-REF", "target") and not hit(dp, "D-REF", "stale")
    with changed(dp):
        ref("D1", "D2")                                            # a design point no page covers yet
        found = hit(dp, "D-REF", "target")
        assert found and "D2" in found[0].message
    with changed(dp):
        ref("D1", "")
        assert hit(dp, "D-REF", "target")
    with changed(dp):
        ref("a-plan", text="see p. 99")
        found = hit(dp, "D-REF", "stale")
        assert found and "deck.py render" in found[0].message and refs["a-plan"] in found[0].message
    with changed(dp):
        ref("a-plan", text="")
        assert hit(dp, "D-REF", "stale")


# ---------- D-TXT-INTERNAL ----------

def test_d_txt_internal(fresh, capsys):
    root = fresh()

    def para(text):
        say(root, "a-board", "para", text)

    def got(text, rule=None):
        para(text)
        return hit(root, "D-TXT-INTERNAL", rule)

    assert got("Work in progress TODO", "todo")
    assert got("Geometry check PASS", "todo")
    assert got("as D2 asks", "id:")
    assert not got("Tidewater C1 on show", "id:") and not got("model A75", "id:") and not got("AD2X", "id:")
    # only the matched span of a protected term is blanked: an ID left over elsewhere in the text still counts
    assert got("Tidewater C1 on show; see C1", "id:")
    assert got("Tidewater C1 und C1", "id:")
    assert not got("Tidewater C1 on show", "id:")
    assert not got("Open timber lounge")
    # the same rules run on a caption and on an alt text
    with edit(root) as t:
        fig = next(n for n in sec(t, "a-board").iter() if n.tag == "figure")
        cap = next((n for n in fig.iter() if n.tag == "figcaption"), None)
        if cap is None:
            cap = deck_html.fragment("<figcaption>x</figcaption>")[0]
            fig.append(cap)
        cap.set_inner(deck_html.fragment("Geometry check PASS"))
    assert hit(root, "D-TXT-INTERNAL", "todo")
    with edit(root) as t:
        fig = next(n for n in sec(t, "a-board").iter() if n.tag == "figure")
        next(n for n in fig.iter() if n.tag == "figcaption").set_inner(deck_html.fragment("Open timber lounge"))
        [n for n in fig.iter() if n.tag == "img"][0].set("alt", "Geometry check PASS")
    assert hit(root, "D-TXT-INTERNAL", "todo")
    with edit(root) as t:
        [n for n in sec(t, "a-board").iter() if n.tag == "img"][0].set("alt", "Open timber lounge")
    assert not hit(root, "D-TXT-INTERNAL", "todo")
    assert got("see set-1 for more", "set")
    assert got("hero-v2.png", "file") and got("brief/notes", "file") and got("tender-brief.docx", "file")
    # paths inside text with no spaces (CJK), and ordinary word pairs that only look like a path
    assert got("\u89c1brief/notes\u6587\u4ef6", "file") and got("\u89c1work\\notes.md\u6587\u4ef6", "file")
    assert not got("work/life balance", "file") and not got("a work/life balance, input/output", "file")
    assert got("see work/render.json", "file")
    assert got("per RFP §2.1", "source:")
    assert not got("per RFP 2.1", "source:")
    with edit(root) as t:
        slot(t, "claims", "col1").set_text("Source")
    found = hit(root, "D-TXT-INTERNAL", "source-col")
    assert found and found[0].page_id == "claims"
    # the header token is checked too, with no page
    style = {"logo": "brand/logo.png", "header": "TODO header"}
    common.write_json(str(root / "brief" / "deck-style.json"), style)
    capsys.readouterr()
    assert deck.main(["style", "--project", str(root)]) == 0
    found = hit(root, "D-TXT-INTERNAL", "todo")
    assert any(f.where == "tokens --header" and f.page is None for f in found)
    style["header"] = "Nordvik Ferries"
    common.write_json(str(root / "brief" / "deck-style.json"), style)
    assert deck.main(["style", "--project", str(root)]) == 0
    assert not [f for f in factory.findings(root) if f.where.startswith("tokens")]

    legacy = fresh()                                                # _legacy is not a set name on a page
    (legacy / "concepts/_legacy/A/renders").mkdir(parents=True)
    say(legacy, "a-board", "para", "see _legacy and set-1")
    found = hit(legacy, "D-TXT-INTERNAL", "set")
    assert len(found) == 1 and "set-1" in found[0].message

    zh = fresh("zh")
    say(zh, "a-board", "para", "回应D2的要求")
    assert hit(zh, "D-TXT-INTERNAL", "id:")


def test_text_checks_at_element_edges(fresh):
    """Terms sitting at the edge of two inline elements are not run together by the text extraction."""
    root = fresh()

    def got(markup, code, rule):
        say(root, "a-board", "para", markup)
        return hit(root, code, rule)

    assert got("<span>Tasting bar harbour</span><span>D2</span>", "D-TXT-INTERNAL", "id:")
    assert got("<span>D2</span><span>harbour</span>", "D-TXT-INTERNAL", "id:")
    assert got("<b>Harbour view</b><i>D2</i>", "D-TXT-INTERNAL", "id:")
    assert got("<span>See</span><span>set-1</span>", "D-TXT-INTERNAL", "set")
    assert got("<span>Work in</span><span>TODO</span>", "D-TXT-INTERNAL", "todo")
    assert got("<span>the old</span><span>stand</span>", "D-TXT-REFERENCE", "phrase")
    assert got("<a>the previous</a><a>stand</a>", "D-TXT-REFERENCE", "phrase")
    assert got("<span>It</span><span>builds on</span><span>the quay</span>", "D-TXT-PENDING", "evolution")
    # a typographic tag inside one word does not split it; block and other tags do
    assert not got("Tide<b>water</b> lounge", "D-TXT-REFERENCE", "phrase")
    vis = deck_html.visible_text(deck_html.parse("<section>Tide<b>water</b>s <em>a</em><em>b</em> x<a>y</a>z</section>"))
    assert vis.splitlines()[0].split() == ["Tidewaters", "a", "b", "x", "y", "z"]
    say(root, "a-board", "para", "Open timber lounge")
    assert not codes(root) & {"D-TXT-INTERNAL", "D-TXT-REFERENCE"}


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_reference_phrases_flagged(fresh, lang):
    root = fresh(lang)
    phrases = json.loads((SCRIPTS.parent / "assets" / "labels" / f"{lang}.json").read_text(encoding="utf-8"))["reference_phrases"]
    assert len(phrases) >= 6
    wanted = ["old stand", "previous booth", "last year's booth", "current stand", "existing stand"] if lang == "en"         else ["旧展位", "之前的展台", "现有展台", "当前展台", "上次展台"]
    assert set(wanted) <= set(phrases)
    for phrase in phrases:
        say(root, "a-board", "para", f"Unlike the {phrase} here" if lang == "en" else f"不同于{phrase}的做法")
        assert hit(root, "D-TXT-REFERENCE", "phrase"), phrase


# ---------- D-TXT-REFERENCE ----------

def test_d_txt_reference(fresh):
    root = fresh()
    say(root, "a-board", "para", "Unlike last season's stand")
    assert hit(root, "D-TXT-REFERENCE", "dnm")
    say(root, "a-board", "para", "Unlike last season\u2019s stand")      # a typographic apostrophe does not hide it
    assert hit(root, "D-TXT-REFERENCE", "dnm")
    say(root, "a-board", "para", "the reference image shows")
    assert hit(root, "D-TXT-REFERENCE", "phrase") and not hit(root, "D-TXT-REFERENCE", "dnm")
    say(root, "a-board", "para", "Open timber lounge")
    assert not hit(root, "D-TXT-REFERENCE")
    zh = fresh("zh")
    say(zh, "a-board", "para", "参考图")
    assert hit(zh, "D-TXT-REFERENCE", "phrase")


# ---------- D-TXT-PENDING ----------

def test_d_txt_pending(fresh, capsys):
    root = fresh()
    say(root, "a-board", "para", "A hall that builds on the harbour")
    found = hit(root, "D-TXT-PENDING", "evolution")
    assert len(found) == 1 and found[0].level == "pending" and found[0].page_id == "a-board"
    assert 'evolution word "builds on" \u2013 decide in review pass 1' == found[0].message
    res = deck_check.run_check(common.find_project(str(root)))
    assert res.pending == found and [f for f in res.findings if f.level == "error"] == []
    capsys.readouterr()
    assert deck.main(["check", "--project", str(root)]) == 0
    assert "PENDING D-TXT-PENDING" in capsys.readouterr().out
    say(root, "a-board", "para", "Wider than ever and builds on the harbour; builds on it again")
    assert len(hit(root, "D-TXT-PENDING", "comparison")) == 1 and len(hit(root, "D-TXT-PENDING", "evolution")) == 1
    zh = fresh("zh")
    say(zh, "a-board", "para", "延续品牌蓝")
    assert len(hit(zh, "D-TXT-PENDING", "evolution")) == 1 and not hit(zh, "D-TXT-PENDING", "comparison")
    assert [f for f in factory.findings(zh) if f.level == "error"] == []


# ---------- D-CLAIM ----------

def test_d_claim(fresh):
    root = fresh()
    say(root, "compare", "c1-next", "14 hybrid vessels sail every day")
    found = hit(root, "D-CLAIM", "untagged")
    assert found and found[0].page_id == "compare" and "C1" in found[0].message
    say(root, "compare", "c1-next", '<span data-claim="C1">14 hybrid vessels</span> sail every day')
    assert not hit(root, "D-CLAIM")
    say(root, "compare", "c1-next", "140 seats on board")
    assert not hit(root, "D-CLAIM")
    say(root, "compare", "c1-next", "a fleet of 2014 vessels")        # a longer number is not 14
    assert not hit(root, "D-CLAIM")

    brief = common.read_json(str(root / "brief" / "brief.json"))
    brief["claims"][0]["keys"] = ["fleet-wide"]
    common.write_json(str(root / "brief" / "brief.json"), brief)
    say(root, "compare", "c1-next", "fleet-wide service")
    assert hit(root, "D-CLAIM", "untagged")
    say(root, "compare", "c1-next", "Fleet - wide service")           # spaces are squashed away
    assert hit(root, "D-CLAIM", "untagged")

    say(root, "compare", "c1-next", '<span data-claim="C1">14 hybrid vessels</span> sail')
    with edit(root) as t:                                           # the signoff page no longer carries C1
        cell = slot(t, "claims", "r1-a")
        cell.set("data-claim", None)
        cell.set_text("Open timber lounge for visitors")
    found = hit(root, "D-CLAIM", "signoff")
    assert found and "C1" in found[0].message and not hit(root, "D-CLAIM", "untagged")

    other = fresh()                                                 # a claim that is not flagged needs nothing
    brief = common.read_json(str(other / "brief" / "brief.json"))
    brief["claims"][0]["flag"] = False
    common.write_json(str(other / "brief" / "brief.json"), brief)
    say(other, "compare", "c1-next", "14 hybrid vessels sail every day")
    assert not hit(other, "D-CLAIM")


# ---------- D-NUMBER ----------

def test_d_number(dp):
    say(dp, "a-board", "para", "a 37 m canopy")
    found = hit(dp, "D-NUMBER")
    assert len(found) == 1 and found[0].level == "warn" and found[0].page_id == "a-board"
    # a hash fragment or a stamp of the brief is no source for a number
    brief = common.read_json(str(dp / "brief" / "brief.json"))
    brief["references"] = {"sets": [{"id": "set-1", "sha256": "ab4821cd90ef"}], "stamped_at": "2026-07-19T13:57:00Z"}
    common.write_json(str(dp / "brief" / "brief.json"), brief)
    for text, number in (("a 4821 m canopy", "4821"), ("a 57 m canopy", "57")):
        say(dp, "a-board", "para", text)
        found = hit(dp, "D-NUMBER")
        assert found and number in found[0].message, text
    for text in ("8 m wide", "26.2 ft", "colour <code>#0B3D5C</code>", "14 hybrid vessels", "Open timber lounge"):
        say(dp, "a-board", "para", text)
        assert not hit(dp, "D-NUMBER"), text


# ---------- D-LAYOUT ----------

def test_d_layout(fresh):
    root = fresh()
    say(root, "a-board", "name", "Longname " * 4)
    found = hit(root, "D-LAYOUT", "max")
    assert len(found) == 1 and found[0].level == "warn" and "name" in found[0].message
    assert "max 14" in found[0].message

    root = fresh()                                                  # appendix pages: 3 are fine, 4 are not
    text = read(root)
    start = text.index('<section class="slide table"')
    end = text.index("</section>", start) + len("</section>")
    block = text[start:end]
    copies = "".join("\n\n" + block.replace('data-id="claims"', f'data-id="claims{i}"') for i in (2, 3))
    write(root, text[:end] + copies + text[end:])
    assert not hit(root, "D-LAYOUT", "appendix")
    text = read(root)
    last = text.rindex("</section>") + len("</section>")
    write(root, text[:last] + "\n\n" + block.replace('data-id="claims"', 'data-id="claims4"') + text[last:])
    found = hit(root, "D-LAYOUT", "appendix")
    assert len(found) == 1 and found[0].page_id == "claims4"

    root = fresh()                                                  # imageless runs
    for i in range(3):
        insert_before(root, "claims", new_slide(root, "statement", **{"data-id": f"t{i}"}))
    assert not hit(root, "D-LAYOUT", "imageless")
    insert_before(root, "claims", new_slide(root, "statement", **{"data-id": "t3"}))
    found = hit(root, "D-LAYOUT", "imageless")
    assert len(found) == 1 and found[0].page_id == "t0" and "4 pages in a row without an image" in found[0].message
    assert found[0].message.startswith("imageless: slides 8-11")
    with edit(root) as t:                                           # the same pages in the appendix
        for i in range(4):
            sec(t, f"t{i}").set("data-part", "appendix")
    assert not hit(root, "D-LAYOUT", "imageless")

    root = fresh()
    entry = {"page": 2, "page_id": "a-board", "src": RENDER_A, "factor": 1.41}
    factory.write_render_json(root, upscale=[entry])
    found = hit(root, "D-LAYOUT", "upscale")
    assert len(found) == 1 and found[0].page == 2 and found[0].page_id == "a-board"
    factory.write_render_json(root, upscale=[{**entry, "factor": 1.25}])
    assert not hit(root, "D-LAYOUT", "upscale")
    factory.write_render_json(root, upscale=[entry])
    rewrite(root, "<body", '<!-- edited -->\n<body')                # a render.json of an older deck is ignored
    assert not hit(root, "D-LAYOUT", "upscale")


# ---------- D-REUSE ----------

def text_page_with(root, pid, src):
    """A role-text page (counted for D-REUSE) holding a render, placed before the claims page."""
    frag = new_slide(root, "statement", **{"data-id": pid}).replace(
        "</section>", f'<figure class="render"><img data-img="render" alt="" src="{src}"></figure></section>')
    insert_before(root, "claims", frag)


def test_d_reuse(fresh):
    root = fresh()
    assert not hit(root, "D-REUSE")                          # the lead render: cover, board, annotated, compare
    for i in range(2):
        text_page_with(root, f"t{i}", RENDER_B)
    assert not hit(root, "D-REUSE")                          # the annotated page of the lead is not counted
    text_page_with(root, "t2", RENDER_B)
    found = hit(root, "D-REUSE")
    assert len(found) == 1 and found[0].level == "warn" and found[0].page_id == "t2"
    assert found[0].message.endswith("used on 3 counted pages (max 2)")
    assert not [f for f in factory.findings(root) if f.level == "error"]

    root = fresh()                                           # another concept: board pages do not count, text ones do
    for i in range(2):
        text_page_with(root, f"t{i}", RENDER_A)
    assert not hit(root, "D-REUSE")
    with edit(root) as t:                                    # the annotated page counts for a concept that is not the lead: b-annotated, t0, t1
        [n for n in sec(t, "b-annotated").iter() if n.tag == "img"][0].set("src", RENDER_A)
    found = hit(root, "D-REUSE")
    assert len(found) == 1 and found[0].page_id == "t1" and found[0].message.endswith("(max 2)")

    root = fresh()                                           # the limit comes from the thresholds of deck-style.json
    common.write_json(str(root / "brief" / "deck-style.json"),
                      {"logo": "brand/logo.png", "thresholds": {"image_reuse_max": 3}})
    for i in range(3):
        text_page_with(root, f"t{i}", RENDER_A)
    assert not hit(root, "D-REUSE")
    text_page_with(root, "t3", RENDER_A)
    found = hit(root, "D-REUSE")
    assert len(found) == 1 and found[0].page_id == "t3" and found[0].message.endswith("4 counted pages (max 3)")


# ---------- D-OVERFLOW ----------

def test_d_overflow(dp):
    entry = {"page": 4, "page_id": "b-board", "slot": "para", "px": 64, "chars": 12}
    factory.write_render_json(dp, overflow=[entry])
    found = hit(dp, "D-OVERFLOW")
    assert len(found) == 1 and found[0].level == "error" and found[0].where == "page 4 b-board para"
    assert found[0].message == "overflow by 64 px (~12 chars)" and found[0].page == 4
    path = factory.write_render_json(dp, overflow=[entry])
    data = common.read_json(path)
    data["deck_sha256"] = "0" * 64
    common.write_json(path, data)
    assert not hit(dp, "D-OVERFLOW")
    factory.write_render_json(dp, overflow=[entry])
    assert hit(dp, "D-OVERFLOW")
    res = deck_check.run_check(common.find_project(str(dp)), render_json=False)   # deck.py render checks first
    assert not [f for f in res.findings if f.code == "D-OVERFLOW"]


# ---------- read-only ----------

def test_check_read_only(dp):
    say(dp, "a-board", "para", "TODO a hall that builds on the harbour, 37 m wide")
    before = tree_hashes(dp)
    done = cli("check", "--project", dp)
    assert done.returncode == 1 and "RESULT: FAIL" in done.stdout and "PENDING D-TXT-PENDING" in done.stdout
    assert tree_hashes(dp) == before

    done = cli("check", "--json", "--project", dp)
    assert done.returncode == 1
    after = tree_hashes(dp)
    assert {p for p in after if after.get(p) != before.get(p)} == {"work/check.json"}
    written = json.loads((dp / "work" / "check.json").read_text(encoding="utf-8"))
    printed = json.loads(done.stdout)
    found = factory.findings(dp)
    assert written["schema"] == "check/1" and written["slides"] == 8
    assert written["deck_sha256"] == common.sha256_text(read(dp)) and written["checked_at"]
    assert written["counts"] == printed["counts"] == {
        lv: sum(1 for f in found if f.level == lv) for lv in ("error", "warn", "pending")}
    assert written["counts"]["error"] >= 1 and written["counts"]["pending"] == 1 and written["counts"]["warn"] >= 1
    assert written["findings"] == printed["findings"] == [f._asdict() for f in found]

    deck_file(dp).unlink()                                           # no deck: error, exit 2
    done = cli("check", "--project", dp)
    assert done.returncode == 2 and done.stderr.startswith("error: no pack/proposal.html")


def test_check_json_help_and_contrast_constant():
    """--json prints JSON instead of the text report (and writes work/check.json); one contrast ratio in common."""
    sub = next(a for a in deck.build_parser()._actions if getattr(a, "choices", None))
    text = " ".join(sub.choices["check"].format_help().split())
    assert "instead of the text report" in text and "work/check.json" in text
    assert common.LEGIBLE_RATIO == 3.0
    assert common.legible.__defaults__ == (common.LEGIBLE_RATIO,)
    assert not [w for w in common.PLAIN_WORD_FOLDERS if w not in common.PROJECT_FOLDERS]
