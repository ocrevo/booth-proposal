"""Fixture factory for the booth-proposal tests (plain module, importable without pytest).

Builds small projects for a fictional client (Nordvik Ferries, product Tidewater Pass). Renders are written
through the real render.py save path with the network call replaced by fake_send.

Usage: python tests/factory.py OUT_DIR [--lang zh|en] [--legacy]
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import io
import os
import sys
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "booth-proposal" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import gates  # noqa: E402
import render  # noqa: E402

SET_SIZES = {"set-1": 2, "set-2": 3}
SEND_LOG: list[dict] = []          # one entry per fake API call: {"url", "fields", "images"}

_COLOUR_COUNTER = [0]


def _next_rgb() -> tuple[int, int, int]:
    """A new colour on every call, so no two images in a process share bytes."""
    i = _COLOUR_COUNTER[0]
    _COLOUR_COUNTER[0] += 1
    return (i & 255, (i >> 8) & 255, (i * 29 + 60) & 255)


def png_bytes(rgb, size=(64, 48)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, tuple(rgb)).save(buf, "PNG")
    return buf.getvalue()


def brief_dict(lang="en") -> dict:
    return {
        "schema": "brief/2",
        "lang": lang,
        "client": {"names": ["Nordvik Ferries", "Nordvik"]},
        "protected_terms": ["Tidewater Pass"],
        "do_not_mention": ["last season's stand"],
        "booth": {"unit": "m", "width": 8, "depth": 6, "max_height": 4.5, "open_sides": ["front", "right"],
                  "source": "RFP §3.2"},
        "design_points": [
            {"id": "D1", "type": "space", "text": "Open, walk-in stand", "source": "RFP §2.1"},
            {"id": "D2", "type": "product", "text": "Show the Tidewater Pass app on a large screen",
             "source": "RFP §2.3"},
        ],
        "claims": [
            {"id": "C1", "text": "14 hybrid vessels in service", "flag": True, "source": "Fleet brochure p.4"},
            {"id": "C2", "text": "Shortest crossing on the route", "flag": False, "source": "Client email"},
        ],
        "assumptions": [
            {"id": "A1", "text": "The stand is built on the venue's raised floor", "impact": "low"},
            {"id": "A2", "text": "Rigging points are available above the stand", "impact": "high"},
        ],
    }


def _idea(cid, name, idea, booth_type, chosen) -> dict:
    return {"id": cid, "name": name, "idea": idea, "booth_type": booth_type, "chosen": chosen}


def ideas_dict(sets=("set-1", "set-2")) -> dict:
    set1 = [
        _idea("A", "Tidal Gate", "A tall archway of layered blue ribbon that visitors pass through",
              "a gate you walk through", True),
        _idea("B", "Hull", "A curved timber hull with a lounge inside its ribs",
              "an object you walk around", True),
        _idea("C", "Pier", "A long jetty of pale boards leading to a counter",
              "a facade you face", False),
    ]
    set2 = [
        _idea("A", "Lantern Room", "A warm room of paper lanterns and soft screens",
              "a room you step into", True),
        _idea("B", "Canopy", "A floating canopy over a ring of benches",
              "a roof you stand under", True),
    ]
    out = []
    for s in sets:
        if s == "set-1":
            out.append({"set": "set-1", "ideas": set1})
        elif s == "set-2":
            out.append({"set": "set-2", "ideas": set2})
        elif s == "_legacy":
            out.append({"set": "_legacy", "ideas": set1[:2]})
        else:
            raise ValueError(f"no ideas for set {s!r}")
    return {"schema": "ideas/1",
            "insights": [{"id": "I1", "text": "Crossings are remembered as thresholds", "source": "D1"}],
            "sets": out}


def fake_send(url, key, fields, images, image_field) -> dict:
    """Same signature as render.send; records the call and returns n new images."""
    SEND_LOG.append({"url": url, "fields": dict(fields), "images": list(images)})
    data = [{"b64_json": base64.b64encode(png_bytes(_next_rgb())).decode("ascii")}
            for _ in range(int(fields["n"]))]
    return {"data": data, "usage": {"total_tokens": 0}}


def _write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8", newline="\n")
    else:
        path.write_bytes(data)


def _hero_prompt(name: str, idea: str) -> str:
    return (f"Idea – {name}: {idea}.\n\n"
            "Brand colours: deep sea blue #0B3D5C and signal yellow #F2B705.\n\n"
            "Size:\n"
            "Width about four person heights.\n"
            "Depth about three person heights.\n"
            "Height about two and a half person heights.\n\n"
            "Essentials: a reception counter, closed storage, a large screen, a small lounge.\n")


def _render_hero(root, concept_key: str, prompt_rel: str, refs: list[str]) -> None:
    """Write hero-v1/v2 through the real render.py hero (lint, call, save) with the network replaced."""
    argv = ["hero", "--concept", concept_key, "--prompt", prompt_rel, "--n", "2"]
    for r in refs:
        argv += ["--ref", r]

    def no_network(*a, **k):
        raise AssertionError("network")

    with contextlib.chdir(root), \
            mock.patch.object(render, "send", fake_send), \
            mock.patch("urllib.request.urlopen", side_effect=no_network), \
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-not-real"}), \
            contextlib.redirect_stdout(io.StringIO()):
        code = render.main(argv)
    assert code == 0, f"render.py hero failed for {concept_key}"


def review_pass(root, image_rel: str, scope: str = "full") -> None:
    """Record a passing review of an image through render.py review (needs the review command)."""
    argv = ["review", image_rel, "--reviewer", "subagent", "--verdict", "pass", "--premium", "yes",
            "--scope", scope, "--size-json", '{"observed": {"w": 4.6, "d": 3.4, "h": 2.6}}', "--marks-json", "[]",
            "--project", str(root)]
    with contextlib.chdir(root), contextlib.redirect_stdout(io.StringIO()):
        code = render.main(argv)
    assert code == 0, f"render.py review failed for {image_rel}"


def hero_ok() -> str:
    """A hero prompt that passes lint: the template filled for Tidal Gate, with the shipped fixed sentences."""
    import json
    fixed = json.loads((SCRIPTS.parent / "assets" / "prompts" / "fixed.json").read_text(encoding="utf-8"))
    return HERO_OK_TEMPLATE.format(**fixed)


HERO_OK_TEMPLATE = """Idea – Tidal Gate: one deep gate of folded ribs that visitors walk through into a calm lounge; the gate carries the counter and a large screen.

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


def put_sidecar(root, image_rel: str, mode: str, *, base: str | None = None, refs=(), version: int = 2) -> None:
    """Write a sidecar beside concepts/<set>/<concept>/renders/<name>. version 2 = sidecar/2 (hashes read from
    the files now), 1 = the old key-less sidecar. base/refs are project-relative paths."""
    root = Path(root)
    parts = image_rel.split("/")
    image = str(root / image_rel)
    if version == 1:
        common.write_json(common.sidecar_path(image), {
            "image": parts[-1], "timestamp": "2026-01-01T00:00:00", "mode": mode,
            "input_images": [*([base] if base else []), *refs]})
        return
    inputs = [{"role": "ref", "path": r, "sha256": common.sha256_file(str(root / r))} for r in refs]
    if base:
        inputs.append({"role": "base", "path": base, "sha256": common.sha256_file(str(root / base))})
    common.write_sidecar(image, {"tool": "render.py", "mode": mode, "set": parts[1], "concept": parts[2],
                                 "inputs": inputs, "prompt_sha256": None, "lint": None, "api": None})


def add_render(root, key: str, name: str, *, mode: str = "hero", base: str | None = None, refs=(),
               version: int | None = 2, data: bytes | None = None) -> str:
    """Write a new image concepts/<key>/renders/<name> (a fresh colour unless data is given) and, when version
    is 1 or 2, its sidecar. Returns the project-relative path."""
    rel = f"concepts/{key}/renders/{name}"
    _write(Path(root) / rel, data if data is not None else png_bytes(_next_rgb()))
    if version:
        put_sidecar(root, rel, mode, base=base, refs=refs, version=version)
    return rel


def build_project(root, *, lang="en", legacy=False, stamp=True, ideas=True, scaffold=True,
                  renders=True, chosen=True, style=None) -> Path:
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"{root} is not empty")
    if (scaffold or renders) and not stamp:
        raise ValueError("scaffold and renders need stamp=True")
    if scaffold and not ideas:
        raise ValueError("scaffold needs ideas=True")
    root.mkdir(parents=True, exist_ok=True)

    common.write_json(str(root / "brief" / "brief.json"), brief_dict(lang))
    if style is not None:
        common.write_json(str(root / "brief" / "deck-style.json"), style)

    _write(root / "input" / "rfp.md", "# Nordvik Ferries - stand brief (fictional)\n")
    refs_of: dict[str, list[str]] = {}
    if legacy:
        for name in ("r01.png", "r02.png"):
            _write(root / "input" / name, png_bytes(_next_rgb()))
        _write(root / "input" / "sub" / "deep.png", png_bytes(_next_rgb()))
        refs_of["_legacy"] = ["input/r01.png", "input/r02.png"]
    else:
        logo = png_bytes(_next_rgb())
        _write(root / "input" / "brand-logo.png", logo)
        _write(root / "input" / "product.png", png_bytes(_next_rgb()))
        _write(root / "brief" / "brand" / "logo.png", logo)
        for sid, count in SET_SIZES.items():
            refs_of[sid] = []
            for i in range(1, count + 1):
                rel = f"input/refs/{sid}/r{i:02d}.png"
                _write(root / rel, png_bytes(_next_rgb()))
                refs_of[sid].append(rel)

    if stamp:
        assert gates.main(["brief", "--stamp", "--project", str(root)]) == 0

    ideas_data = ideas_dict(("_legacy",) if legacy else ("set-1", "set-2"))
    if ideas:
        common.write_json(str(root / "brief" / "ideas.json"), ideas_data)
        if scaffold:
            assert gates.main(["ideas", "--scaffold", "--project", str(root)]) == 0

    if renders:
        for entry in ideas_data["sets"]:
            for idea in entry["ideas"]:
                if not idea["chosen"]:
                    continue
                key = f"{entry['set']}/{idea['id']}"
                prompt_rel = f"concepts/{key}/prompts/hero.txt"
                _write(root / prompt_rel, _hero_prompt(idea["name"], idea["idea"]))
                _render_hero(root, key, prompt_rel, refs_of[entry["set"]])
                if chosen:
                    _write(root / "concepts" / key / "concept.md",
                           "---\nchosen: renders/hero-v2.png\n---\nNotes.\n")
    return root


# ---------- deck fixture (phase 3): a project with two selected concepts and a filled deck ----------

DECK_SELECTED = ("set-2/B", "set-1/A")         # display letters A and B; lead set-1/A
DECK_LEAD = "set-1/A"
_FILLER = "Open timber lounge for visitors to rest and talk"
_DECK_CACHE: dict[str, str] = {}               # lang -> a built project folder, copied for each test


def _geometry(title: str, arch: str, bar: str) -> dict:
    return {
        "title": title, "width": 8, "depth": 6, "max_height": 4.5, "unit": "m", "open_sides": ["front", "right"],
        "elements": [
            {"id": "X1", "shape": "extrusion", "label": arch, "kind": "hero", "x": 0, "y": 2, "w": 3, "h": 0.2,
             "profile": [[0, 0], [1.5, 4.2], [3, 0]], "support": "floor"},
            {"id": "T1", "label": bar, "x": 4, "y": 1, "w": 2, "h": 0.8, "height": 1.1},
            {"id": "T2", "label": bar, "x": 4, "y": 3, "w": 2, "h": 0.8, "height": 1.1}]}


def fill(fragment: str, texts: dict | None = None, imgs=(), attrs: dict | None = None) -> str:
    """Fill a deck.py layouts --emit fragment (or one slide of a deck).

    texts: {slot name: HTML} for the leaf slots; every other leaf slot gets a neutral phrase cut to its data-max.
    imgs: src values for the img elements in document order (fewer than the imgs leaves the rest as they are).
    attrs: attributes set on the section, e.g. {"data-id": "a-board", "data-concept": "A", "data-covers": "D1"};
    a data-concept also sets the single capital letter of .no and .letter elements."""
    import deck_html as h
    sec = h.element(fragment)
    for name, value in (attrs or {}).items():
        sec.set(name, value)
    texts = texts or {}
    for slot in h.leaf_slots(sec):
        name = slot.get("data-slot")
        if name in texts:
            slot.set_inner(h.fragment(texts[name]))
            continue
        cap = slot.get("data-max")
        limit = min(int(cap) if cap and cap.isdigit() else 40, 40)
        out = ""
        for w in _FILLER.split():
            if len((out + " " + w).strip()) > limit:
                break
            out = (out + " " + w).strip()
        slot.set_text(out or _FILLER[:max(1, limit)])
    srcs = list(imgs)
    for img in [n for n in sec.iter() if n.tag == "img"][:len(srcs)]:
        img.set("src", srcs.pop(0))
    letter = sec.get("data-concept")
    if letter:
        for n in sec.iter():
            if (n.has_class("no") or n.has_class("letter")) and not any(c.is_el for c in n.children) \
                    and len(n.text().strip()) == 1 and n.text().strip().isalpha():
                n.set_text(letter)
    return sec.html() + "\n"


def _emit(root, spec: str, count: int | None = None) -> str:
    import deck
    argv = ["layouts", "--emit", spec, "--project", str(root)]
    if count is not None:
        argv[3:3] = ["--count", str(count)]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = deck.main(argv)
    assert code == 0, f"deck.py layouts --emit {spec} failed"
    return out.getvalue()


def _build_deck_project(root: Path, lang: str) -> None:
    import deck
    import deck_html as h
    import draw_plan
    build_project(root, lang=lang, style={"logo": "brand/logo.png"})
    brief = common.read_json(str(root / "brief" / "brief.json"))
    brief["protected_terms"].append("Tidewater C1")
    common.write_json(str(root / "brief" / "brief.json"), brief)
    _write(root / "input" / "tender-brief.docx", b"PK fictional tender document")
    for key in ("set-1/A", "set-1/B", "set-2/A", "set-2/B"):
        review_pass(root, f"concepts/{key}/renders/hero-v2.png")
    assert gates.main(["select", *DECK_SELECTED, "--lead", DECK_LEAD, "--project", str(root)]) == 0
    specs = {"set-2/B": _geometry("A · Canopy Lounge", "Canopy arch", "Coffee bar"),
             "set-1/A": _geometry("B · Tidal Gate", "Boarding arch", "Info counter")}
    for key, spec in specs.items():
        folder = root / "concepts" / key
        common.write_json(str(folder / "geometry.json"), spec)
        assert draw_plan.main(["plan", str(folder / "geometry.json"), str(folder / "plan"),
                               "--project", str(root)]) == 0

    def render_of(key):
        return f"../concepts/{key}/renders/hero-v2.png"

    def plan_of(key):
        return f"../concepts/{key}/plan.png"

    with contextlib.redirect_stdout(io.StringIO()):
        assert deck.main(["new", "--project", str(root)]) == 0
    a, b = DECK_SELECTED
    text = (root / "pack" / "proposal.html").read_text(encoding="utf-8")
    slides = h.slides_of(h.parse(text))
    pages = [fill(slides[0].html(), {"title": "Tidewater Pass"}, [render_of(DECK_LEAD)], {"data-id": "cover"})]
    pages.append(fill(_emit(root, "board"), None, [render_of(a)],
                      {"data-id": "a-board", "data-concept": "A", "data-covers": "D1"}))
    pages.append(fill(_emit(root, "plan"), None, [plan_of(a)], {"data-id": "a-plan", "data-concept": "A"}))
    pages.append(fill(_emit(root, "board"), None, [render_of(b)], {"data-id": "b-board", "data-concept": "B"}))
    pages.append(fill(_emit(root, "plan"), None, [plan_of(b)], {"data-id": "b-plan", "data-concept": "B"}))
    pages.append(fill(_emit(root, "annotated"), None, [render_of(b)],
                      {"data-id": "b-annotated", "data-concept": "B"}))
    compare = _emit(root, "compare", 2).replace(
        "</section>", '  <figure class="render" style="width:320px;height:200px"><img data-img="render" alt="" '
        'src=""></figure>\n</section>')
    pages.append(fill(compare, {"c1-why": 'Strong entrance <span data-ref="a-plan"></span>',
                                "c2-why": 'Open lounge <span data-ref="D1"></span>'},
                      [render_of(DECK_LEAD)], {"data-id": "compare"}))
    claims = _emit(root, "table").replace('data-slot="r1-a"', 'data-slot="r1-a" data-claim="C1"')
    pages.append(fill(claims, {"r1-a": "14 hybrid vessels in service", "title": "Claims to confirm"}, (),
                      {"data-id": "claims", "data-role": "signoff", "data-part": "appendix"}))
    body = "\n".join(p.rstrip("\n") + "\n" for p in pages)
    out = text[:slides[0].start] + body + "\n" + text[slides[-1].end:].lstrip("\n")
    project = common.find_project(str(root))
    tree = h.parse(out)
    h.refresh_refs(tree, project, None)
    h.write_deck(project, tree.html())


def deck_project(tmp_path, lang: str = "en") -> Path:
    """tmp_path/deck-project: build_project (with the logo in brief/brand), two selected concepts (set-2/B shown as
    A, set-1/A shown as B and lead), reviewed chosen renders, geometry and plans, and a deck of eight slides:
    cover, a-board, a-plan, b-board, b-plan, b-annotated, compare, claims (signoff, appendix). Built once per
    language with the real commands and copied for each caller."""
    import atexit
    import shutil
    import tempfile
    if lang not in _DECK_CACHE:
        base = Path(tempfile.mkdtemp(prefix="deck-project-"))
        atexit.register(shutil.rmtree, str(base), True)
        _build_deck_project(base / "p", lang)
        _DECK_CACHE[lang] = str(base / "p")
    dest = Path(tmp_path) / "deck-project"
    shutil.copytree(_DECK_CACHE[lang], dest)
    return dest


def _as_project(project):
    return project if isinstance(project, common.Project) else common.find_project(str(project))


def findings(project) -> list:
    """The findings of deck_check.run_check for the project's deck (a Project or a folder)."""
    import deck_check
    return list(deck_check.run_check(_as_project(project)).findings)


def has(project, code: str, rule: str | None = None) -> list:
    """The findings with this code whose message starts with rule (any message when rule is None)."""
    return [f for f in findings(project) if f.code == code and (rule is None or f.message.startswith(rule))]


def write_render_json(project, overflow=(), upscale=(), *, measured: bool = True) -> str:
    """Write work/render.json for the deck as it is now (current deck_sha256). Returns the path."""
    import deck_html as h
    p = _as_project(project)
    text = h.read_deck(p) or ""
    slides = len(h.slides_of(h.parse(text)))
    path = p.path("work", "render.json")
    common.write_json(path, {
        "schema": "render/1", "deck_sha256": common.sha256_text(text), "rendered_at": common.now_iso(),
        "browser": "test-browser", "slides": slides, "pdf_pages": slides, "previews": slides,
        "measured": measured, "overflow": list(overflow), "upscale": list(upscale)})
    return path


def record(project, data: dict) -> int:
    """Write work/deck-review.input.json and run deck.py review --record on it; returns the exit code."""
    import deck
    p = _as_project(project)
    path = p.path("work", "deck-review.input.json")
    common.write_json(path, data)
    return deck.main(["review", "--record", path, "--project", p.root])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build a fictional demo project")
    ap.add_argument("out_dir")
    ap.add_argument("--lang", choices=["zh", "en"], default="en")
    ap.add_argument("--legacy", action="store_true")
    a = ap.parse_args(argv)
    root = build_project(a.out_dir, lang=a.lang, legacy=a.legacy)
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    print("\n".join(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
