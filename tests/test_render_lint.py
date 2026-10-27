"""Prompt lint (phase 1, S1): render.lint_prompt, lint_status and the `render.py lint` command."""
import json
import os
import re

import pytest

import common
import render

FIXED = json.loads(open(render.FIXED_PATH, encoding="utf-8").read())

HERO_TEMPLATE = """Idea – Tidal Gate: one deep gate of folded ribs that visitors walk through into a calm lounge; the gate carries the counter and a large screen.

Brand colours: deep navy #0B3D5C, signal yellow #F2B705, white

Size:
- One platform about four and a half person-heights wide and three and a half person-heights deep; the whole stand, the gate included, stands on it and nothing stands outside it.
- Open at the front and the right side; the other sides are closed.
- The tallest element, the gate, is about 2.6 times the height of a person.

Essentials: the gate carries the counter and a large screen; a lounge with low seats, three plain product plinths, storage as a door in the back wall. No ceiling and nothing hung from the hall ceiling. A few visitors for scale, one at the front edge.
{logo_panel}
{no_lettering}

{reference}
{do_not_copy}
"""


def hero_ok():
    return HERO_TEMPLATE.format(**FIXED)


# Fallbacks: the verbatim blocks of references/4-renders.md (written by the docs sub-task); the doc wins once it exists.
OSTARA_BLOCK = """Idea – Roasting Hall: a single long vaulted canopy of ribs that visitors walk under, from the aisle to a tasting bar at the back; the canopy carries the screen, and the bar grows out of its last rib.

Brand colours: espresso brown #3B2418, crema #E9D8B4, white

Size:
- One platform about three and a half person-heights wide and two and a half person-heights deep; the whole stand, the canopy included, stands on it and nothing stands outside it.
- Open at the front and the left side; the other sides are closed.
- The tallest element, the canopy, is about 2.3 times the height of a person.

Essentials: the canopy carries the tasting bar and a large screen; three plain product plinths, a few stools, storage as a door in the back wall. No ceiling and nothing hung from the hall ceiling. A few visitors for scale, one at the front edge.
One plain panel in a brand colour is left empty for the logo, which is added later.
No lettering, numbers, names, emblems or logos anywhere; screens, product labels and signs are plain.

The attached photos are references for form, space and mood only. Carry their design language into a new stand that is clearly more premium and refined, in the brand colours above.
Do not copy any logo, lettering, slogan, poster or other brand from the photos, or anything from neighbouring stands.
"""

TEMPLATE_BLOCK = """Idea – [concept name, no quotes]: [the idea and its main form in two or three sentences: what visitors do in it, and which functions the main form carries].

Brand colours: [colour words with #RRGGBB, e.g. deep navy #0B3D5C, signal yellow #F2B705, white]

Size:
- One platform about [W in m / 1.75] person-heights wide and [D in m / 1.75] person-heights deep; the whole stand, the main form included, stands on it and nothing stands outside it.
- Open at [the open sides]; the other sides are closed.
- The tallest element, [the main form], is about [H in m / 1.75] times the height of a person.

Essentials: [which functions the main form carries, then what else a visitor sees, in words: a large screen, product displays, a counter, seating, storage as a door in the back wall]. No ceiling and nothing hung from the hall ceiling. A few visitors for scale, one at the front edge.
One plain panel in a brand colour is left empty for the logo, which is added later.
No lettering, numbers, names, emblems or logos anywhere; screens, product labels and signs are plain.

The attached photos are references for form, space and mood only. Carry their design language into a new stand that is clearly more premium and refined, in the brand colours above.
Do not copy any logo, lettering, slogan, poster or other brand from the photos, or anything from neighbouring stands.
"""


def doc_blocks():
    """(template block, Ostara block) from the shipped 4-renders.md, else the embedded copies."""
    path = os.path.join(common.SKILL_DIR, "references", "4-renders.md")
    if os.path.isfile(path):
        text = open(path, encoding="utf-8").read()
        section = text.split("## Prompt template", 1)[-1].split("\n## ", 1)[0]
        blocks = re.findall(r"```[^\n]*\n(.*?)```", section, re.S)
        if len(blocks) >= 2:
            return blocks[0], blocks[1]
    return TEMPLATE_BLOCK, OSTARA_BLOCK


FIX_ROWS = [
    "The stand is only about three person-heights deep from the front edge to the back wall; bring the back wall "
    "forward and keep every design element.",
    "The platform is only about four person-heights wide; bring both side edges in and keep every design element.",
    "The top of the gate is about two times the height of a person; change its height only.",
    "Remove the hanging banner; nothing else changes.",
    "Show exactly three plinths; nothing else changes.",
    "Clear the left pillar: it becomes a plain navy surface with nothing on it; nothing else changes.",
    "The niches hold plain white blocks with nothing on them; nothing else changes.",
]

FRONT_OK = ("The same exhibition stand as in this image, same design, colours and light, every element in the same "
            "place, seen from the front: from the main aisle, nearly straight on, the whole width visible with some "
            "hall on both sides. A few visitors for scale. No other changes.")


def sub(text, a, b):
    assert a in text, a
    return text.replace(a, b, 1)


def rules(fs):
    return sorted({(f.code, f.message.split(":")[0]) if f.code != "L-WORDS" else (f.code,) for f in fs})


@pytest.fixture
def lint(project):
    """lint(text, mode="hero", names=None, refs=(), concept="set-1/A", brief=None) -> findings."""
    def run(text, mode="hero", names=None, refs=(), concept="set-1/A", drop_references=False):
        p = common.find_project(str(project))
        if names is not None:
            p.brief["client"]["names"] = names
        if drop_references:
            p.brief.pop("references")
        c = common.concept_ref(p, concept) if concept else None
        return render.lint_prompt(p, mode, text, "prompt.txt", concept=c, refs=refs)

    return run


@pytest.fixture
def refs1(project):
    return [str(project / f"input/refs/set-1/r{i:02d}.png") for i in (1, 2)]


def _cli(argv, capsys):
    capsys.readouterr()
    try:
        code = render.main(argv)
    except SystemExit as e:
        code = e.code
    return code, capsys.readouterr()


# ---------- data files ----------

def test_data_files_shape():
    for path in (render.FIXED_PATH, render.LINT_PATH):
        raw = open(path, "rb").read()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert "schema" not in json.loads(raw)
    fixed, data = render.load_prompt_data()
    assert sorted(fixed) == sorted(render.FIXED_KEYS)
    assert sorted(data) == ["logo_text_phrases", "one_per_patterns", "timeline_words"]
    for word in ("logo", "slogan", "century", "reads", "reading"):
        assert word not in data["logo_text_phrases"] and word not in data["timeline_words"]


def test_classify_blocks():
    text = hero_ok()
    lines = render.classify(text, FIXED)
    blocks = [pl.block for pl in lines]
    assert blocks[:3] == ["idea", "blank", "colours"]
    assert blocks[4:8] == ["size", "size", "size", "size"]
    assert blocks.count("fixed") == 4 and "other" not in blocks
    assert [pl.no for pl in lines] == list(range(1, len(lines) + 1))


def test_lint_status():
    F = common.Finding
    assert render.lint_status([]) == {"status": "pass", "codes": []}
    assert render.lint_status([F("L-WORDS", "warn", "w", "m")]) == {"status": "warn", "codes": ["L-WORDS"]}
    both = [F("L-BAN", "error", "w", "m"), F("L-BAN", "error", "w", "m"), F("L-WORDS", "warn", "w", "m")]
    assert render.lint_status(both) == {"status": "fail", "codes": ["L-BAN", "L-WORDS"]}
    assert render.lint_status(None) is None


# ---------- 6.2 ----------

def _clean_cases():
    cases = [
        pytest.param(lambda: hero_ok(), "hero", None, id="hero-ok"),
        pytest.param(lambda: doc_blocks()[1], "hero", ["Ostara Coffee"], id="ostara-block"),
        pytest.param(lambda: re.sub(r"\[[^\]]*\]", "two", doc_blocks()[0]), "hero", None, id="template-block"),
        pytest.param(lambda: sub(hero_ok(), "a calm lounge", "the Ostarabrook valley mood"), "hero", ["Ostara"],
                     id="ostara-word-boundary"),
        pytest.param(lambda: sub(hero_ok(), "a calm lounge", "the ferry's calm lounge"), "hero", None,
                     id="apostrophe-in-word"),
        pytest.param(lambda: sub(hero_ok(), "low seats", "mid-century lounge chairs"), "hero", None, id="mid-century"),
        pytest.param(lambda: sub(hero_ok(), "into a calm lounge", "into a calm lounge; the stand reads as one object"),
                     "hero", None, id="reads-as-one"),
        pytest.param(lambda: sub(hero_ok(), "low seats", "a reading nook"), "hero", None, id="reading-nook"),
        pytest.param(lambda: sub(hero_ok(), "low seats", "a table to read and sign papers"), "hero", None,
                     id="table-to-read"),
        pytest.param(lambda: sub(hero_ok(), "into a calm lounge", "into a calm lounge; a facade that reads as one surface"),
                     "hero", None, id="facade-that-reads"),
        pytest.param(lambda: sub(hero_ok(), "Idea – Tidal Gate:", "Idea – Captain's Wharf:"), "hero", None,
                     id="name-apostrophe-in-word"),
        pytest.param(lambda: "\n".join(("  ".join(l.split(" ")) if any(l == v for v in FIXED.values()) else l)
                                       for l in hero_ok().split("\n")), "hero", None, id="doubled-spaces"),
    ]
    for i, row in enumerate(FIX_ROWS, 1):
        cases.append(pytest.param(lambda row=row: row, "fix", None, id=f"fix-row-{i}"))
    cases.append(pytest.param(lambda: FRONT_OK, "front", None, id="front"))
    return cases


@pytest.mark.parametrize("build, mode, names", _clean_cases())
def test_clean_prompts_pass(lint, refs1, build, mode, names):
    text = build()
    assert lint(text, mode, names=names, refs=refs1 if mode == "hero" else ()) == []


def _ban_cases():
    H = hero_ok()
    to = lambda a, b, text=H: sub(text, a, b)
    return [
        pytest.param(to("folded ribs", "Nordvik ribs"), "hero", [("L-BAN", "client")], id="client-idea"),
        pytest.param(to("deep navy", "Nordvik navy"), "hero", [("L-BAN", "client")], id="client-colours"),
        pytest.param(to("a large screen;", "a Tidewater Pass kiosk;"), "hero", [("L-BAN", "client")],
                     id="client-protected"),
        pytest.param(to("a large screen;", "a 75-inch screen;"), "hero", [("L-BAN", "digit")], id="digit-75-inch"),
        pytest.param(to("three plain product plinths", "three #F2B705 plinths"), "hero", [("L-BAN", "digit")],
                     id="digit-hex"),
        pytest.param(to("a large screen;", "the A75 grinder;"), "hero", [("L-BAN", "digit")], id="digit-model"),
        pytest.param(to("calm lounge", '"calm lounge"'), "hero", [("L-BAN", "quote")], id="quote-straight"),
        pytest.param(to("calm lounge", "“calm lounge”"), "hero", [("L-BAN", "quote")], id="quote-curly"),
        pytest.param(to("calm lounge", "「calm lounge」"), "hero", [("L-BAN", "quote")], id="quote-corner"),
        pytest.param(to("a calm lounge", "the visitors' lounge"), "hero", [("L-BAN", "quote")], id="quote-apostrophe"),
        pytest.param(to("Idea – Tidal Gate:", 'Idea – "Tidal Gate":'), "hero",
                     [("L-BAN", "name-quoted"), ("L-BAN", "quote")], id="name-quoted"),
        pytest.param(to("one at the front edge.", "one at the front edge. 诺德."), "hero",
                     [("L-BAN", "cjk")], id="cjk"),
        pytest.param(to("folded ribs", "five folded ribs, one for each of the five routes,"), "hero",
                     [("L-BAN", "one-per")], id="one-per"),
        pytest.param(to("\n\nBrand colours", " A fine timeline from 1931 to today runs along the inner curve."
                        "\n\nBrand colours"), "hero", [("L-BAN", "digit"), ("L-BAN", "timeline")], id="timeline"),
        pytest.param(to("a lounge with low seats", "the logo as in the photos once on the back wall"), "hero",
                     [("L-BAN", "logo-text")], id="logo-text"),
        pytest.param(to(FIXED["logo_panel"], "One plain panel with the logo of the client."), "hero",
                     [("L-BAN", "logo-text")], id="logo-text-edited-fixed"),
        pytest.param("Replace it with a plaque to read Harbour Line 1931", "fix",
                     [("L-BAN", "digit"), ("L-BAN", "logo-text")], id="fix-plaque"),
        pytest.param(to("Idea – Tidal Gate:", "Idea – 'Tidal Gate:"), "hero",
                     [("L-BAN", "name-quoted"), ("L-BAN", "quote")], id="name-leading-apostrophe"),
        pytest.param(to("Idea – Tidal Gate:", "Idea – “Tidal Gate”:"), "hero",
                     [("L-BAN", "name-quoted"), ("L-BAN", "quote")], id="name-curly-quotes"),
        pytest.param(sub(FRONT_OK, "the whole width", "the whole 8 m width"), "front", [("L-BAN", "digit")],
                     id="front-digit"),
    ]


@pytest.mark.parametrize("text, mode, expected", _ban_cases())
def test_ban_rules(lint, refs1, text, mode, expected):
    fs = lint(text, mode, refs=refs1 if mode == "hero" else ())
    assert rules(fs) == sorted(expected)
    assert all(f.level == "error" for f in fs)


def test_ban_messages_name_the_token(lint):
    fs = lint(sub(hero_ok(), "a large screen;", "a 75-inch screen;"))
    assert [f for f in fs if f.code == "L-BAN" and "75-inch" in f.message]
    assert all(re.fullmatch(r"prompt\.txt:\d+", f.where) for f in fs)


def _block_cases():
    H = hero_ok()
    size = ("Size:\n- One platform about four and a half person-heights wide and three and a half person-heights deep; "
            "the whole stand, the gate included, stands on it and nothing stands outside it.\n"
            "- Open at the front and the right side; the other sides are closed.\n"
            "- The tallest element, the gate, is about 2.6 times the height of a person.\n\n")
    third = "- The tallest element, the gate, is about 2.6 times the height of a person.\n"
    return [
        pytest.param(sub(H, size, ""), "size", id="size-removed"),
        pytest.param(sub(H, size, "Size – keep it exactly: one platform about four person-heights wide.\n\n"),
                     "size", id="size-dash"),
        pytest.param(sub(H, third, ""), "size", id="size-two-lines"),
        pytest.param(sub(H, "Brand colours:", "Make it premium. Brand colours:"), "colours", id="colours-not-first"),
    ]


@pytest.mark.parametrize("text, rule", _block_cases())
def test_blocks_missing(lint, text, rule):
    assert ("L-BLOCKS", rule) in rules(lint(text, refs=()))


def test_blocks_idea_and_essentials(lint):
    no_colon = sub(hero_ok(), "Idea – Tidal Gate:", "Idea – Tidal Gate")
    assert ("L-BLOCKS", "idea") in rules(lint(no_colon))
    no_ess = sub(hero_ok(), "Essentials:", "Extras:")
    assert ("L-BLOCKS", "essentials") in rules(lint(no_ess))
    assert not [f for f in lint(hero_ok()) if f.code == "L-BLOCKS"]
    # blocks are only demanded of hero prompts
    assert lint("Remove the hanging banner; nothing else changes.", "fix") == []


def test_ref_rules(lint, project, refs1):
    other = str(project / "input/refs/set-2/r01.png")
    assert ("L-REF", "set") in rules(lint(hero_ok(), refs=[other]))
    fs = lint(hero_ok(), refs=refs1, drop_references=True)
    assert [f for f in fs if f.code == "L-REF" and f.message.startswith("set:") and "gates.py brief --stamp" in f.message]
    render_ref = str(project / "concepts/set-1/B/renders/hero-v1.png")
    assert ("L-REF", "render") in rules(lint(hero_ok(), refs=[render_ref]))
    assert not [f for f in lint(hero_ok(), refs=refs1) if f.code == "L-REF"]


def test_ref_rules_need_concept(lint, refs1):
    assert lint(hero_ok(), refs=refs1, concept=None) == []


def test_words_warn_only(lint, project, tmp_path, capsys):
    text = sub(hero_ok(), "Essentials: ", "Essentials: " + "calm " * 400)
    fs = lint(text, refs=())
    assert rules(fs) == [("L-WORDS",)] and fs[0].level == "warn"
    p = tmp_path / "long.txt"
    p.write_text(text, encoding="utf-8")
    code, out = _cli(["lint", "--mode", "hero", "--prompt", str(p), "--project", str(project)], capsys)
    assert code == 0 and "L-WORDS" in out.out and "RESULT: PASS" in out.out


def test_cli_usage_errors(project, tmp_path, capsys):
    p = tmp_path / "p.txt"
    p.write_text(hero_ok(), encoding="utf-8")
    proj = ["--project", str(project)]
    code, out = _cli(["lint", "--mode", "hero", "--prompt", str(p), "--ref", "x.jpg", *proj], capsys)
    assert code == 2 and "--ref needs --concept" in out.err
    code, out = _cli(["lint", "--mode", "hero", "--add", "x", *proj], capsys)
    assert code == 2 and "--add goes only with --mode fix" in out.err


def test_cli_fix_add_json(project, capsys):
    code, out = _cli(["lint", "--mode", "fix", "--add", "Show 3 niches", "--json", "--project", str(project)], capsys)
    assert code == 1
    data = json.loads(out.out)
    assert data["counts"] == {"error": 1, "warn": 0, "pending": 0}
    (f,) = data["findings"]
    assert f["code"] == "L-BAN" and f["message"].startswith("digit:") and f["where"] == "--add:1"


def test_cli_clean_prompt_with_refs(project, refs1, capsys):
    p = project / "concepts/set-1/A/prompts/lint-ok.txt"
    p.write_text(hero_ok(), encoding="utf-8")
    argv = ["lint", "--mode", "hero", "--prompt", str(p), "--concept", "set-1/A", "--project", str(project)]
    for r in refs1:
        argv += ["--ref", r]
    code, out = _cli(argv, capsys)
    assert code == 0 and "RESULT: PASS" in out.out


def test_cli_input_errors(project, tmp_path, capsys):
    p = tmp_path / "p.txt"
    p.write_text(hero_ok(), encoding="utf-8")
    code, out = _cli(["lint", "--mode", "hero", "--prompt", str(p), "--concept", "set-9/Z", "--project",
                      str(project)], capsys)
    assert code == 2 and "C-INPUT" in out.err
    code, out = _cli(["lint", "--mode", "hero", "--prompt", str(p), "--project", str(tmp_path / "nowhere")], capsys)
    assert code == 2 and "C-INPUT" in out.err
    empty = tmp_path / "empty.txt"
    empty.write_text("  \n", encoding="utf-8")
    code, out = _cli(["lint", "--mode", "hero", "--prompt", str(empty), "--project", str(project)], capsys)
    assert code == 2 and "empty" in out.err
    code, out = _cli(["lint", "--mode", "hero", "--prompt", str(tmp_path / "none.txt"), "--project", str(project)],
                     capsys)
    assert code == 2 and "not found" in out.err


OLD_STYLE = (
    "A stunning, high-end exhibition stand design visualization for Nordvik Ferries at a national maritime fair.\n\n"
    'Idea – "The Harbour Gate": the familiar gateway made deep and sculptural, its left leg a pillar of five '
    "layered bands (one for each of the five routes), and a fine timeline from 1931 to today along the inner curve.\n\n"
    "Make it look premium and memorable. Brand colours: Nordvik navy #0B3D5C, signal yellow #F2B705, white.\n"
    "Size – keep it exactly: one 8 m × 6 m platform, about four and a half person-heights wide. "
    "Open at the front and the right side.\n"
    "Essentials: a 75-inch screen, the Tidewater Pass kiosk, a counter. The Nordvik logo as in the photos "
    "(诺德维克) once on the back wall and once on the counter.\n"
)


def test_old_style_prompt_blocked(lint):
    got = set(rules(lint(OLD_STYLE, refs=())))
    ban = {("L-BAN", r) for r in ("client", "quote", "cjk", "digit", "one-per", "timeline", "logo-text",
                                  "name-quoted")}
    assert ban <= got
    assert {r for r in got if r[0] == "L-BLOCKS"} >= {("L-BLOCKS", "size"), ("L-BLOCKS", "colours")}
