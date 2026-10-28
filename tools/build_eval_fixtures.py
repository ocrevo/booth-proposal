#!/usr/bin/env python
"""Build the generated files of the eval cases (images and, for the fixture cases, a finished project folder).

Usage: python tools/build_eval_fixtures.py (--case NAME | --all)

Writes only below skills/booth-proposal/evals/<case>/files/ and only these paths: input/refs/, input/nordvik-logo.png,
brief/, concepts/, graphics/, deck/, pack/, incoming/. The hand-written input/rfp.md and input/brochure.md are never touched.

Images are synthetic Pillow drawings (no text, no glyphs) with a fixed seed per file. The Nordvik fixtures are built in a
temporary folder by the real command line tools (gates.py, render.py import and review, booth_geometry.py,
draw_plan.py, deck.py) with a fake clock and a fixed SOURCE_DATE_EPOCH, so two runs give identical bytes. Files that a
model writes in a real run (brief.json, ideas.json, prompts, geometry, deck text) are literals below. Nothing here
calls the network, and work/, .env and keys are never copied into files/.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import random
import shutil
import sys
import tempfile
import zlib
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
EVALS = REPO / "skills" / "booth-proposal" / "evals"
SCRIPTS = REPO / "skills" / "booth-proposal" / "scripts"
for _p in (str(SCRIPTS), str(REPO / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PIL import Image, ImageDraw  # noqa: E402

import booth_geometry  # noqa: E402
import common  # noqa: E402
import deck  # noqa: E402
import deck_html as h  # noqa: E402
import draw_plan  # noqa: E402
import factory  # noqa: E402  (tests/factory.py: fill, _emit, _write helpers)
import gates  # noqa: E402
import render  # noqa: E402

PHOTO_SIZE = (1024, 683)
RENDER_SIZE = (1536, 1024)

# paths below files/ that this tool owns (everything else, e.g. input/rfp.md, belongs to the case author)
OWNED = ("input/refs", "input/nordvik-logo.png", "brief", "concepts", "graphics", "deck", "pack", "incoming")


# ---------------------------------------------------------------- synthetic images (no text, no glyphs)

def _rng(key: str) -> random.Random:
    return random.Random(zlib.crc32(key.encode("utf-8")))


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _palette(r: random.Random) -> dict:
    wall = r.choice([(214, 206, 192), (196, 205, 210), (222, 214, 200), (188, 196, 190)])
    floor = r.choice([(150, 140, 128), (128, 134, 140), (160, 150, 136)])
    form = r.choice([(176, 120, 78), (88, 124, 150), (190, 168, 110), (110, 140, 112), (154, 96, 96)])
    return {"wall": wall, "floor": floor, "form": form}


def _backdrop(d: ImageDraw.ImageDraw, size, pal, r: random.Random, horizon: float) -> int:
    w, h_ = size
    hy = int(h_ * horizon)
    for y in range(hy):
        d.line([(0, y), (w, y)], fill=_mix(pal["wall"], (255, 255, 255), 0.18 * (1 - y / hy)))
    for y in range(hy, h_):
        t = (y - hy) / (h_ - hy)
        d.line([(0, y), (w, y)], fill=_mix(pal["floor"], (92, 90, 88), t * 0.55))
    for _ in range(14):                                  # floor seams towards a vanishing point
        x0 = r.randint(-w // 2, w + w // 2)
        d.line([(w // 2 + (x0 - w // 2) * 0.15, hy), (x0, h_)], fill=_mix(pal["floor"], (60, 60, 60), 0.35), width=2)
    for _ in range(260):                                 # fine speckle so the picture is not flat
        x, y = r.randint(0, w - 1), r.randint(0, h_ - 1)
        d.point((x, y), fill=_mix(pal["floor"] if y > hy else pal["wall"], (0, 0, 0), 0.12))
    return hy


def _figure(d: ImageDraw.ImageDraw, x: int, foot: int, height: int, tone: int) -> None:
    """A grey person silhouette standing with its feet at (x, foot)."""
    col = (tone, tone, tone + 4)
    head = height * 0.13
    body_w = height * 0.26
    top = foot - height
    d.ellipse([x - head, top, x + head, top + 2 * head], fill=col)
    d.rounded_rectangle([x - body_w, top + 2.1 * head, x + body_w, foot - height * 0.42], radius=int(body_w * 0.6),
                        fill=col)
    d.rectangle([x - body_w * 0.7, foot - height * 0.45, x - body_w * 0.12, foot], fill=col)
    d.rectangle([x + body_w * 0.12, foot - height * 0.45, x + body_w * 0.7, foot], fill=col)


def _form(d: ImageDraw.ImageDraw, size, hy, pal, r: random.Random) -> None:
    """One sculptural form: stacked ribs, an arch or a fan."""
    w, h_ = size
    cx = int(w * r.uniform(0.35, 0.65))
    base = int(hy + (h_ - hy) * 0.55)
    kind = r.choice(["ribs", "arch", "fan"])
    col, dark = pal["form"], _mix(pal["form"], (0, 0, 0), 0.35)
    if kind == "ribs":
        for i in range(7):
            x = cx - 210 + i * 70
            top = base - int(h_ * (0.34 + 0.05 * abs(3 - i) * -1 + 0.1))
            d.rounded_rectangle([x, top, x + 34, base], radius=16, fill=_mix(col, dark, i % 2 * 0.4))
    elif kind == "arch":
        d.pieslice([cx - 260, base - 430, cx + 260, base + 90], 180, 360, fill=col)
        d.pieslice([cx - 170, base - 330, cx + 170, base + 10], 180, 360, fill=pal["wall"])
        d.rectangle([cx - 262, base - 170, cx - 168, base], fill=col)
        d.rectangle([cx + 168, base - 170, cx + 262, base], fill=col)
    else:
        for i in range(6):
            a = -80 + i * 32
            d.polygon([(cx, base), (cx + a * 3.2 - 40, base - 380), (cx + a * 3.2 + 40, base - 380)],
                      fill=_mix(col, dark, i / 8))
    d.ellipse([cx - 280, base - 14, cx + 280, base + 40], outline=dark, width=3)


def make_photo(key: str, blue_wall: bool = False) -> Image.Image:
    """A 1024x683 reference photo: floor, back wall, one sculptural form, grey figures. blue_wall = a deep blue
    curved wall instead of the form (the client's previous stand)."""
    r = _rng(key)
    img = Image.new("RGB", PHOTO_SIZE, (200, 200, 200))
    d = ImageDraw.Draw(img)
    pal = _palette(r)
    hy = _backdrop(d, PHOTO_SIZE, pal, r, 0.52)
    w, h_ = PHOTO_SIZE
    if blue_wall:
        import math
        blue, deep = (22, 66, 124), (12, 40, 84)
        for x in range(0, w, 4):                                       # a long wall that sweeps in a gentle S-curve
            t = x / w
            top = int(hy - 250 + 70 * math.sin(t * 5.0))
            foot = int(hy + 70 + 40 * math.sin(t * 5.0 + 0.6))
            d.rectangle([x, top, x + 4, foot], fill=_mix(blue, deep, 0.5 + 0.5 * math.sin(t * 5.0 + 1.2)))
    else:
        _form(d, PHOTO_SIZE, hy, pal, r)
    for i in range(r.randint(3, 5)):
        foot = r.randint(hy + 90, h_ - 20)
        height = int(70 + (foot - hy) * 0.32)
        _figure(d, r.randint(60, w - 60), foot, height, r.randint(96, 140))
    return img


def make_render(key: str) -> Image.Image:
    """A 1536x1024 concept render: a raised platform with a gate, counter, screen, lounge and visitors."""
    r = _rng(key)
    img = Image.new("RGB", RENDER_SIZE, (200, 200, 200))
    d = ImageDraw.Draw(img)
    pal = _palette(r)
    pal["wall"] = _mix(pal["wall"], (236, 238, 240), 0.4)
    hy = _backdrop(d, RENDER_SIZE, pal, r, 0.42)
    w, h_ = RENDER_SIZE
    blue, yellow = (11, 61, 92), (242, 183, 5)
    px0, px1, py0, py1 = 260, 1276, hy + 120, h_ - 150                        # platform
    d.polygon([(px0 + 90, py0), (px1 - 90, py0), (px1, py1), (px0, py1)], fill=(226, 224, 218))
    d.polygon([(px0, py1), (px1, py1), (px1, py1 + 26), (px0, py1 + 26)], fill=(168, 166, 160))
    gx = r.randint(560, 760)                                                    # the gate: layered ribs
    for i in range(5):
        k = i * 34
        d.pieslice([gx - 250 + k, py0 - 470 + k, gx + 250 - k, py0 + 130 - k], 180, 360,
                   fill=_mix(blue, (255, 255, 255), i * 0.12))
        d.pieslice([gx - 214 + k, py0 - 430 + k, gx + 214 - k, py0 + 90 - k], 180, 360, fill=_mix(pal["wall"], (255, 255, 255), 0.3))
    d.rectangle([gx - 250, py0 - 170, gx - 214, py0 + 20], fill=blue)
    d.rectangle([gx + 214, py0 - 170, gx + 250, py0 + 20], fill=blue)
    d.rectangle([px0 + 60, py0 - 250, px0 + 330, py0 - 90], fill=(34, 40, 48))         # the screen
    d.rectangle([px0 + 74, py0 - 238, px0 + 316, py0 - 102], fill=_mix(blue, (255, 255, 255), 0.35))
    d.rounded_rectangle([px1 - 400, py0 + 110, px1 - 120, py0 + 250], radius=10, fill=yellow)   # the counter
    d.rectangle([px1 - 400, py0 + 96, px1 - 120, py0 + 118], fill=_mix(yellow, (255, 255, 255), 0.4))
    d.rectangle([px1 - 150, py0 - 160, px1 - 70, py0 + 40], fill=_mix(blue, (255, 255, 255), 0.2))  # storage door
    for i in range(4):                                                          # the lounge
        d.ellipse([px0 + 120 + i * 96, py1 - 150, px0 + 190 + i * 96, py1 - 96], fill=(92, 104, 112))
    for i in range(r.randint(3, 4)):
        foot = r.randint(py0 + 150, py1 + 90)
        _figure(d, r.randint(px0 + 80, px1 - 80), foot, int(90 + (foot - hy) * 0.2), r.randint(90, 130))
    return img


def make_logo(key: str) -> Image.Image:
    """An abstract mark (waves and a half disc), no letters."""
    r = _rng(key)
    img = Image.new("RGBA", (640, 320), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    blue, yellow = (11, 61, 92, 255), (242, 183, 5, 255)
    d.pieslice([60, 40, 300, 280], 180, 360, fill=yellow)
    for i in range(3):
        y = 150 + i * 46
        d.arc([60 + i * 6, y, 300 + i * 6, y + 90], 200, 340, fill=blue, width=18)
    d.rounded_rectangle([340, 120, 580, 200], radius=40, fill=blue)
    d.ellipse([360 + r.randint(0, 6), 138, 404, 182], fill=yellow)
    return img


def make_graphic(key: str) -> Image.Image:
    """A 1024x1536 portrait wall-panel artwork: a calm, plain pale field in the top third (kept empty for the text),
    layered paper-cut hills, a sun, sea and a ferry below. No letters, no digits, no logo."""
    r = _rng(key)
    w, h_ = 1024, 1536
    img = Image.new("RGB", (w, h_), (238, 234, 222))
    d = ImageDraw.Draw(img)
    edge = 520                                                    # the top of the subject; everything above stays plain
    for y in range(edge, h_):                                     # dawn sky, warmer towards the horizon
        d.line([(0, y), (w, y)], fill=_mix((238, 234, 222), (246, 208, 150), (y - edge) / (h_ - edge) * 0.9))
    navy, yellow = (11, 61, 92), (242, 183, 5)
    d.ellipse([w // 2 - 130, 760 - 130, w // 2 + 130, 760 + 130], fill=_mix(yellow, (255, 255, 255), 0.15))
    for i, (base, tone) in enumerate(((880, 0.62), (940, 0.4), (1000, 0.2))):      # three layers of hills
        pts = [(0, base)]
        x = 0
        while x < w:
            x += r.randint(90, 170)
            pts.append((min(x, w), base - r.randint(40, 150)))
        pts += [(w, h_), (0, h_)]
        d.polygon(pts, fill=_mix(navy, (238, 234, 222), tone))
    d.rectangle([0, 1080, w, h_], fill=_mix(navy, (238, 234, 222), 0.12))           # the sea
    for i in range(7):                                                              # wake lines
        y = 1180 + i * 46
        d.line([(120 + i * 20, y), (w - 120 - i * 20, y)], fill=_mix(navy, (255, 255, 255), 0.45), width=4)
    d.polygon([(250, 1040), (800, 1040), (740, 1130), (310, 1130)], fill=(250, 248, 242))   # the ferry hull
    d.rectangle([320, 1000, 700, 1040], fill=(250, 248, 242))
    d.rectangle([420, 960, 620, 1000], fill=yellow)
    d.rectangle([505, 920, 535, 960], fill=navy)
    for _ in range(3):                                                              # gulls as small arcs
        gx, gy = r.randint(180, 840), r.randint(620, 800)
        d.arc([gx, gy, gx + 40, gy + 24], 200, 340, fill=navy, width=4)
        d.arc([gx + 36, gy, gx + 76, gy + 24], 200, 340, fill=navy, width=4)
    for _ in range(1400):                                                           # fine grain, below the empty area only
        x, y = r.randint(0, w - 1), r.randint(edge + 10, h_ - 1)
        d.point((x, y), fill=_mix(img.getpixel((x, y)), (0, 0, 0), 0.06))
    return img


def save_png(img: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=False)
    return path


# ---------------------------------------------------------------- the Nordvik project (literals)

CLAIMS = [
    {"id": "C1", "text": "14 hybrid vessels in service", "flag": True, "source": "Fleet brochure p.4"},
    {"id": "C2", "text": "The first fully electric car ferry on the northern coast", "flag": True,
     "source": "Fleet brochure p.4"},
    {"id": "C3", "text": "Founded in 1931", "flag": False, "source": "Fleet brochure p.2"},
]


def nordvik_brief(lang: str, architecture: str | None = None) -> dict:
    """The brief of the design-point cases. architecture: written as proposal.architecture; None = left to the
    default."""
    brief = {
        "schema": "brief/2", "lang": lang,
        "client": {"names": ["Nordvik Ferries", "Nordvik"]},
        "protected_terms": ["Tidewater Pass"],
        "do_not_mention": ["last season's stand"],
        "booth": {"unit": "m", "width": 8, "depth": 6, "max_height": 4.5, "open_sides": ["front", "right"],
                  "source": "RFP §3.2", "rigging_allowed": None},
        "design_points": [
            {"id": "D1", "type": "space", "text": "Open, walk-in stand", "source": "RFP §2.1"},
            {"id": "D2", "type": "theme", "text": "Crossings made calm", "source": "RFP §2.1"},
            {"id": "D3", "type": "function", "text": "Tidewater Pass sign-up counter", "source": "RFP §4.1"},
            {"id": "D4", "type": "media", "text": "Large screen for route films", "source": "RFP §4.2"},
            {"id": "D5", "type": "function", "text": "Lounge that seats eight", "source": "RFP §4.3"},
            {"id": "D6", "type": "function", "text": "Storage", "source": "RFP §4.4"},
            {"id": "D7", "type": "function", "text": "A giveaway for visitors", "source": "RFP §4.5"},
        ],
        "claims": [dict(c) for c in CLAIMS],
        "assumptions": [
            {"id": "A1", "text": "The open sides are front and right; the organiser has not confirmed them",
             "impact": "high"},
            {"id": "A2", "text": "Nothing may be hung from the hall ceiling until the organiser confirms rigging",
             "impact": "high"},
        ],
    }
    if architecture:
        brief["proposal"] = {"architecture": architecture}
    return brief


def tender_brief(lang: str, architecture: str | None = None) -> dict:
    """The brief of a numbered tender (input/rfp.md of tender-default and showcase-explicit): clauses of several
    kinds (one mixed), the unnumbered list as deliverables, one requested graphic."""
    brief = nordvik_brief(lang)
    brief["booth"]["source"] = "Tender, Event and stand"
    brief["design_points"] = [
        {"id": "D1", "type": "space", "text": "Open, walk-in stand with a clear entrance", "source": "Tender item 2"},
        {"id": "D2", "type": "theme", "text": "Crossings made calm", "source": "Tender item 2"},
        {"id": "D3", "type": "function", "text": "Tidewater Pass sign-up counter", "source": "Tender item 3"},
        {"id": "D4", "type": "media", "text": "Large screen for route films", "source": "Tender item 3"},
        {"id": "D5", "type": "product", "text": "An area where visitors try the Tidewater Pass app",
         "source": "Tender item 5"},
        {"id": "D6", "type": "function", "text": "Lounge that seats eight", "source": "Tender item 8"},
    ]
    brief["clauses"] = [
        {"n": "2", "text": "An open, walk-in stand with a clear entrance, in the spirit of crossings made calm",
         "source": "Tender item 2", "kind": "design", "points": ["D1", "D2"]},
        {"n": "3", "text": "A Tidewater Pass sign-up counter and a large screen for route films",
         "source": "Tender item 3", "kind": "design", "points": ["D3", "D4"]},
        {"n": "5", "text": "An area where visitors try the Tidewater Pass app", "source": "Tender item 5",
         "kind": "interaction", "points": ["D5"]},
        {"n": "7.1", "text": "An overall price and an itemised price", "title": "Overall and itemised price",
         "source": "Tender item 7.1", "kind": "price", "points": []},
        {"n": "8", "text": "Lounge furniture for eight, supplied and delivered to the hall by the bidder",
         "title": "Lounge furniture and its delivery", "source": "Tender item 8", "kind": ["design", "execution"],
         "points": ["D6"]},
    ]
    brief["deliverables"] = [
        {"id": "DL1", "title": "Design scheme with renderings and floor plan", "kind": "design",
         "points": ["D1", "D2", "D3", "D4", "D5", "D6"], "source": "Tender, the proposal must contain"},
        {"id": "DL2", "title": "Graphic design of the back wall panel", "kind": "graphics", "points": [],
         "source": "Tender, the proposal must contain"},
        {"id": "DL3", "title": "Build schedule and on-site headcount", "kind": "execution", "points": [],
         "source": "Tender, the proposal must contain"},
        {"id": "DL4", "title": "Itemised price", "kind": "price", "points": [],
         "source": "Tender, the proposal must contain"},
    ]
    brief["graphics"] = [{"id": "GR1", "title": "Fleet story", "purpose": "A back wall panel that tells the story of "
                          "the fleet", "ratio": "2:3", "refs": [], "content": ["C3"]}]
    if architecture:
        brief["proposal"] = {"architecture": architecture}
    return brief


# per concept key: (name, idea sentence for ideas.json, booth type, idea line of the prompt, essentials of the prompt)
CONCEPTS = {
    "A": ("Tidal Gate", "A deep gate of layered blue ribs that visitors walk through into a calm lounge",
          "a gate you walk through",
          "one deep gate of folded ribs that visitors walk through into a calm lounge; the gate carries the counter "
          "and a large screen",
          "the gate carries the counter and a large screen; a lounge with low seats, three plain product plinths, "
          "storage as a door in the back wall"),
    "B": ("Hull", "A curved timber hull with a lounge inside its ribs", "an object you walk around",
          "a curved timber hull standing in the middle of the platform, open ribs on the sides that face the aisles "
          "and a lounge inside",
          "a reception counter beside the hull, a large screen on the back wall, low seats inside the ribs, storage "
          "behind the back wall"),
}
SET_CONCEPTS = {   # per reference set: concept id -> (name, idea, booth type, prompt idea line, essentials)
    "ref-north": {
        "A": CONCEPTS["A"],
        "B": ("Ferry Room", "A calm room with a low ceiling of paper lanterns and a long bench", "a room you step into",
              "a calm room with a low ceiling of soft lanterns, open at the front and the right side, with a long bench "
              "along the back wall", "a counter at the entrance, a large screen above the bench, storage behind a "
              "plain door, three plain product plinths"),
    },
    "ref-grove": {
        "A": ("Canopy", "A floating canopy over a ring of benches", "a roof you stand under",
              "a wide floating canopy of pale timber slats over a ring of benches, with a counter at the edge",
              "a counter at the edge of the canopy, a large screen on a single post, storage as a closed box at the "
              "back, low seats under the canopy"),
        "B": ("Lantern Hull", "A hull of lanterns that visitors walk around", "an object you walk around",
              "a rounded hull made of stacked lanterns, with a counter on one side and a lounge on the other",
              "a counter on one side, a large screen on the hull, low seats on the other side, storage in the back "
              "wall"),
    },
}

HERO_TEMPLATE = """Idea – {name}: {idea}.

Brand colours: deep navy #0B3D5C, signal yellow #F2B705, white

Size:
- One platform about four and a half person-heights wide and three and a half person-heights deep; the whole stand stands on it and nothing stands outside it.
- Open at the front and the right side; the other sides are closed.
- The tallest element is about 2.6 times the height of a person.

Essentials: {essentials}. No ceiling and nothing hung from the hall ceiling. A few visitors for scale, one at the front edge.
{logo_panel}
{no_lettering}

{reference}
{do_not_copy}
"""


def hero_prompt(entry: tuple) -> str:
    name, _idea, _type, idea_line, essentials = entry
    fixed = json.loads((SCRIPTS.parent / "assets" / "prompts" / "fixed.json").read_text(encoding="utf-8"))
    return HERO_TEMPLATE.format(name=name, idea=idea_line, essentials=essentials, **fixed)


GRAPHIC_TEMPLATE = """Graphic – {title}: a tall wall panel that tells the story of the ferry line to visitors at the stand.

Brand colours: deep navy #0B3D5C, signal yellow #F2B705, white

Composition:
- A tall portrait panel in a flat, layered paper-cut style with soft grain.
- The upper third is kept empty: a calm, plain field of pale cream for the title, and nothing reaches into it.
- The subject fills the lower part, centred, with a quiet margin at every edge.

Subject:
- A modern hybrid ferry crossing a calm fjord at dawn, seen from the side, low hills behind.
- Gulls and a soft wake; the hull panels are plain.
{graphic_no_text}
{graphic_text_area}
"""


def graphic_prompt(title: str) -> str:
    fixed = json.loads((SCRIPTS.parent / "assets" / "prompts" / "fixed.json").read_text(encoding="utf-8"))
    return GRAPHIC_TEMPLATE.format(title=title, **fixed)


def ideas_json(sets: dict) -> dict:
    """sets: {set id: {concept id: entry}} (every entry is chosen), plus an unchosen alternative per set."""
    out = []
    for sid, ents in sets.items():
        ideas = [{"id": cid, "name": e[0], "idea": e[1], "booth_type": e[2], "chosen": True} for cid, e in ents.items()]
        ideas.append({"id": "C", "name": "Pier", "idea": "A long jetty of pale boards leading to a counter",
                      "booth_type": "a facade you face", "chosen": False})
        out.append({"set": sid, "ideas": ideas})
    return {"schema": "ideas/1",
            "insights": [{"id": "I1", "text": "Crossings are remembered as thresholds that visitors pass", "source": "D1"}],
            "sets": out}


def geometry_json(entry: tuple) -> dict:
    return {
        "title": f"A · {entry[0]}", "width": 8, "depth": 6, "max_height": 4.5, "unit": "m",
        "open_sides": ["front", "right"], "rigging_allowed": None,
        "elements": [
            {"id": "X1", "shape": "extrusion", "label": "Gate", "kind": "hero", "x": 2.4, "y": 2.4, "w": 3.2, "h": 0.25,
             "profile": [[0, 0], [1.6, 4.2], [3.2, 0]], "support": "floor"},
            {"id": "C1", "label": "Sign-up counter", "kind": "service", "x": 5.8, "y": 0.4, "w": 2.0, "h": 0.8,
             "height": 1.1, "support": "floor"},
            {"id": "S1", "label": "Large screen", "kind": "media", "x": 0.4, "y": 5.6, "w": 1.5, "h": 0.2,
             "z": 0.9, "height": 1.2, "support": "wall"},
            {"id": "L1", "label": "Lounge", "kind": "seating", "x": 0.5, "y": 0.8, "w": 2.4, "h": 1.4, "height": 0.45,
             "support": "floor"},
            {"id": "T1", "label": "Storage", "kind": "storage", "x": 6.4, "y": 4.6, "w": 1.4, "h": 1.2, "height": 2.4,
             "support": "floor"},
        ]}


# ---------------------------------------------------------------- running the real tools in-process

class Clock:
    """now_iso() replacement: one second later on every call, so every stamp is the same on every run."""

    def __init__(self):
        self.n = 0

    def __call__(self) -> str:
        self.n += 1
        t = 9 * 3600 + self.n
        return f"2026-10-01T{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}+02:00"


@contextlib.contextmanager
def frozen_env():
    """Fixed clock, fixed SOURCE_DATE_EPOCH (matplotlib svg), no API key, no network."""
    def no_network(*a, **k):
        raise AssertionError("network")

    clock = Clock()
    env = {"SOURCE_DATE_EPOCH": "1790000000", "PYTHONHASHSEED": "0"}
    with mock.patch.object(common, "now_iso", clock), mock.patch.object(gates, "now_iso", clock), \
            mock.patch("urllib.request.urlopen", side_effect=no_network), \
            mock.patch.dict(os.environ, env), \
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        os.environ.pop("OPENAI_API_KEY", None)
        import matplotlib
        with matplotlib.rc_context({"svg.hashsalt": "booth-proposal-eval-fixtures"}):   # fixed svg element ids
            yield


def run(module, argv, root: Path, ok=(0,)) -> str:
    out = io.StringIO()
    with contextlib.chdir(root), contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            code = module.main(argv)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
    if code not in ok:
        raise RuntimeError(f"{module.__name__} {' '.join(map(str, argv))} exited {code}:\n{out.getvalue()}")
    return out.getvalue()


def review(root: Path, image_rel: str, *, verdict: str, scope: str, marks: list, premium: str = "yes") -> None:
    argv = ["review", image_rel, "--reviewer", "subagent", "--verdict", verdict, "--premium", premium, "--scope", scope,
            "--size-json", '{"observed": {"w": 4.6, "d": 3.4, "h": 2.5}}', "--marks-json", json.dumps(marks),
            "--project", str(root)]
    run(render, argv, root, ok=(0, 1))


def _write(root: Path, rel: str, data) -> None:
    factory._write(Path(root) / rel, data)


def build_nordvik(dest: Path, sets: dict, upto: int, *, lang: str, case: str, renders: dict | None = None,
                  selected: list | None = None, lead: str | None = None, with_deck: bool = False,
                  architecture: str | None = None, brief: dict | None = None,
                  graphic_prompts: dict | None = None) -> None:
    """Build a Nordvik project in `dest` (an empty temp folder) with the real tools, up to the end of step `upto`.

    sets: {set id: {concept id: entry of CONCEPTS}}; upto: 3 = prompts written (ideas scaffolded), 4 = renders imported
    and reviewed, 5 = selection, geometry and plan. renders: {concept key: [(chosen?, verdict, scope, marks) | None, ...]}
    one tuple per hero-v<k> in order (None = imported and left unreviewed). architecture: written as
    proposal.architecture of the brief (None = the default); brief: a ready brief instead of the design-point one;
    graphic_prompts: {graphic id: prompt text} written to graphics/<id>/prompts/graphic.txt."""
    dest.mkdir(parents=True, exist_ok=True)
    src = dest.parent / (dest.name + "-src")                          # images "made elsewhere", outside the project
    refs_of: dict[str, list[str]] = {}
    for sid in sets:
        refs_of[sid] = []
        for i in (1, 2):
            rel = f"input/refs/{sid}/r{i:02d}.png"
            save_png(make_photo(f"{case}/{rel}"), dest / rel)
            refs_of[sid].append(rel)
    common.write_json(str(dest / "brief" / "brief.json"), brief or nordvik_brief(lang, architecture))
    run(gates, ["brief", "--stamp", "--project", str(dest)], dest)
    common.write_json(str(dest / "brief" / "ideas.json"), ideas_json(sets))
    run(gates, ["ideas", "--scaffold", "--project", str(dest)], dest)
    for sid, ents in sets.items():
        for cid, entry in ents.items():
            _write(dest, f"concepts/{sid}/{cid}/prompts/hero.txt", hero_prompt(entry))
    for gid, text in (graphic_prompts or {}).items():
        _write(dest, f"graphics/{gid}/prompts/graphic.txt", text)
    if upto < 4:
        return

    for key, specs in (renders or {}).items():
        sid, cid = key.split("/")
        prompt = f"concepts/{key}/prompts/hero.txt"
        chosen = None
        for k, spec in enumerate(specs, start=1):
            image = save_png(make_render(f"{case}/{key}/hero-v{k}"), src / f"{sid}-{cid}-{k}.png")
            argv = ["import", str(image), "--concept", key, "--prompt", prompt, "--project", str(dest)]
            for r in refs_of[sid]:
                argv += ["--ref", r]
            run(render, argv, dest)
            rel = f"concepts/{key}/renders/hero-v{k}.png"
            if spec is None:
                continue
            is_chosen, verdict, scope, marks = spec
            review(dest, rel, verdict=verdict, scope=scope, marks=marks)
            if is_chosen:
                chosen = f"renders/hero-v{k}.png"
        if chosen:
            _write(dest, f"concepts/{key}/concept.md", f"---\nchosen: {chosen}\n---\nNotes.\n")
    if upto < 5:
        return

    run(gates, ["select", *selected, *(["--lead", lead] if lead else []), "--project", str(dest)], dest)
    for key in selected:
        sid, cid = key.split("/")
        folder = dest / "concepts" / key
        common.write_json(str(folder / "geometry.json"), geometry_json(sets[sid][cid]))
        run(booth_geometry, ["check", str(folder / "geometry.json"), "--project", str(dest)], dest)
        run(draw_plan, ["plan", str(folder / "geometry.json"), str(folder / "plan"), "--project", str(dest)], dest)
    if with_deck:
        build_paraphrased_deck(dest)


# ---------------------------------------------------------------- the draft deck of paraphrased-narration

P1 = "This time the hull wall goes deeper and brighter than before."
P2 = "Visitors who knew the old blue hull will feel at home."
P3 = "We kept the familiar curve and made it calmer."
P4 = "It builds on the stand people already know."
P5 = "The palette carries forward Nordvik's Signal Yellow."
ONE_PIXEL_PNG = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")

STORYBOARD = """# Storyboard – Nordvik Ferries

| page | role | purpose | image | covers |
|---|---|---|---|---|
| cover | cover | Name the proposal | hero of the lead concept | – |
| a-board | board | Show the idea of the gate | hero | D1, D2 |
| a-plan | plan | Show how the stand is used | plan | D3, D4, D5, D6 |
| a-story | text | Explain what visitors will notice | – | D7 |
| a-palette | text | State the colour decision | – | – |
| a-site | text | A moment from the hall | photo | – |
| a-divider | divider | Close the proposal | – | – |
"""


def build_paraphrased_deck(root: Path) -> None:
    """deck/storyboard.md and pack/proposal.html from `deck.py new` and `layouts --emit`, with the planted items."""
    key = "set-1/A"
    _write(root, "deck/storyboard.md", STORYBOARD)
    run(deck, ["new", "--project", str(root)], root)
    text = (root / "pack" / "proposal.html").read_text(encoding="utf-8")
    slides = h.slides_of(h.parse(text))
    render_of = f"../concepts/{key}/renders/hero-v1.png"
    plan_of = f"../concepts/{key}/plan.png"

    def emit(spec: str, count: int | None = None) -> str:
        return factory._emit(root, spec, count)

    pages = [factory.fill(slides[0].html(), {"title": "Tidewater Pass", "subtitle": "A calm place in a busy hall"},
                          [render_of], {"data-id": "cover"})]
    pages.append(factory.fill(emit("board"), {"name": "Tidal Gate", "manifesto": P3,
                                              "para": f"{P1} The gate opens onto the lounge."},
                              [render_of], {"data-id": "a-board", "data-concept": "A", "data-covers": "D1 D2"}))
    pages.append(factory.fill(emit("plan"), None, [plan_of],
                              {"data-id": "a-plan", "data-concept": "A", "data-covers": "D3 D4 D5 D6"}))
    cards = emit("cards:n3")
    pages.append(factory.fill(cards, {"title": "What visitors notice", "lead": "Three things stay with a visitor.",
                                      "c1-k": "Welcome", "c1-title": "A calm arrival", "c1-body": P2,
                                      "c2-k": "Rest", "c2-title": "A place to sit", "c2-body": P4,
                                      "c3-k": "Take away", "c3-title": "A small giveaway",
                                      "c3-body": "Every visitor leaves with a pass holder in signal yellow."},
                              (), {"data-id": "a-story", "data-concept": "A", "data-covers": "D7"}))
    pages.append(factory.fill(emit("statement"), {"label": "Palette", "statement": P5, "by": "Colour decision"}, (),
                              {"data-id": "a-palette", "data-concept": "A"}))
    pages.append(factory.fill(emit("free"), {"title": "A moment from the hall", "k": "Hall", "h": "Open and calm",
                                             "p": "Visitors walk straight in.", "big": "Calm",
                                             "big-d": "The feeling we want."},
                              ["../input/refs/set-1/r01.png"], {"data-id": "a-site", "data-concept": "A"}))
    pages.append(factory.fill(emit("divider"), {"title": "Thank you", "sub": "We look forward to the conversation."},
                              (), {"data-id": "a-divider",
                                   "style": f"background-image:url(data:image/png;base64,{ONE_PIXEL_PNG})"}))
    body = "\n".join(p.rstrip("\n") + "\n" for p in pages)
    out = text[:slides[0].start] + body + "\n" + text[slides[-1].end:].lstrip("\n")
    project = common.find_project(str(root))
    tree = h.parse(out)
    h.refresh_refs(tree, project, None)
    h.write_deck(project, tree.html())


# ---------------------------------------------------------------- cases

def copy_tree(src: Path, dest: Path) -> list[str]:
    """Copy a built project into files/ (never work/, .env or keys). Returns the copied relative paths."""
    copied = []
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src).as_posix()
        top = rel.split("/")[0]
        if p.is_dir() or top in ("work", ".env") or p.name == ".env":
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        copied.append(rel)
    return copied


def clean_owned(files: Path) -> None:
    for rel in OWNED:
        p = files / rel
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


def _images(case: str, files: Path, items: list) -> list[str]:
    out = []
    for rel, kind in items:
        key = f"{case}/{rel}"
        img = make_logo(key) if kind == "logo" else make_photo(key, blue_wall=(kind == "blue"))
        save_png(img, files / rel)
        out.append(rel)
    return out


SET1_PHOTOS = [("input/refs/set-1/r01.png", "photo"), ("input/refs/set-1/r02.png", "photo")]
IMAGE_CASES = {
    "start-shows-every-stage": SET1_PHOTOS + [("input/refs/set-2/r01.png", "photo"), ("input/refs/set-2/r02.png", "photo")],
    "reference-first": [("input/refs/ref-prev/stand-1.png", "blue"), ("input/refs/ref-prev/stand-2.png", "blue"),
                        ("input/nordvik-logo.png", "logo")],
    "render-text-trap": [("input/nordvik-logo.png", "logo")] + SET1_PHOTOS,
    "no-key": SET1_PHOTOS,
}

PASS_FULL = (True, "pass", "full", [])
FAIL_TEXT = (True, "fail", "full", [{"type": "legible_text", "where": "r1c2",
                                     "note": "readable lettering on the back wall"}])
PASS_OTHER = (False, "pass", "full", [])      # a current passing review of a render that is not chosen


def build_failed_fix_blocked(files: Path) -> list[str]:
    sets = {"set-1": {"A": CONCEPTS["A"]}}
    with frozen_env(), tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        build_nordvik(root, sets, 5, lang="zh", case="failed-fix-blocked", selected=["set-1/A"], lead="set-1/A",
                      architecture="showcase",
                      renders={"set-1/A": [FAIL_TEXT, PASS_OTHER]})
        return copy_tree(root, files)


def build_paraphrased_narration(files: Path) -> list[str]:
    sets = {"set-1": {"A": CONCEPTS["A"]}}
    with frozen_env(), tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        build_nordvik(root, sets, 5, lang="en", case="paraphrased-narration", selected=["set-1/A"], lead="set-1/A",
                      architecture="showcase",
                      renders={"set-1/A": [PASS_FULL, PASS_OTHER]}, with_deck=True)
        return copy_tree(root, files)


def build_chatgpt_import(files: Path) -> list[str]:
    sets = {"set-1": {"A": CONCEPTS["A"], "B": CONCEPTS["B"]}}
    with frozen_env(), tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        build_nordvik(root, sets, 3, lang="zh", case="chatgpt-import")
        copied = copy_tree(root, files)
    for name in ("set-1-A-1", "set-1-A-2", "set-1-B-1"):
        save_png(make_render(f"chatgpt-import/incoming/{name}"), files / "incoming" / f"{name}.png")
        copied.append(f"incoming/{name}.png")
    shutil.copyfile(files / "input/refs/set-1/r02.png", files / "incoming" / "set-1-B-2.png")   # a copy of a reference
    copied.append("incoming/set-1-B-2.png")
    return copied


def build_multi_set(files: Path) -> list[str]:
    sets = {"ref-north": SET_CONCEPTS["ref-north"], "ref-grove": SET_CONCEPTS["ref-grove"]}
    renders = {f"{sid}/{cid}": [None, (True, "pass", "full", [])]
               for sid, ents in sets.items() for cid in ents}
    with frozen_env(), tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        build_nordvik(root, sets, 4, lang="zh", case="multi-set-free-selection", renders=renders,
                      architecture="showcase")
        return copy_tree(root, files)


def _build_tender_project(case: str, files: Path) -> list[str]:
    """tender-default and showcase-explicit: the same numbered Nordvik tender, finished up to step 3 (prompts for two
    concepts and for the graphic GR1) with the images made elsewhere in incoming/. No architecture is written to the
    brief: the first case gets the default, the second is told in its prompt."""
    sets = {"set-1": {"A": CONCEPTS["A"], "B": CONCEPTS["B"]}}
    with frozen_env(), tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        build_nordvik(root, sets, 3, lang="en", case=case, brief=tender_brief("en"),
                      graphic_prompts={"GR1": graphic_prompt("Fleet story")})
        copied = copy_tree(root, files)
    for name in ("set-1-A-1", "set-1-A-2", "set-1-B-1"):
        save_png(make_render(f"{case}/incoming/{name}"), files / "incoming" / f"{name}.png")
        copied.append(f"incoming/{name}.png")
    save_png(make_graphic(f"{case}/incoming/GR1-1"), files / "incoming" / "GR1-1.png")
    copied.append("incoming/GR1-1.png")
    return copied


def build_tender_default(files: Path) -> list[str]:
    return _build_tender_project("tender-default", files)


def build_showcase_explicit(files: Path) -> list[str]:
    return _build_tender_project("showcase-explicit", files)


FIXTURES = {
    "tender-default": build_tender_default,
    "showcase-explicit": build_showcase_explicit,
    "failed-fix-blocked": build_failed_fix_blocked,
    "paraphrased-narration": build_paraphrased_narration,
    "chatgpt-import": build_chatgpt_import,
    "multi-set-free-selection": build_multi_set,
}
NOTHING = ("brief-from-rfp", "geometry-conflict-caught", "us-inline-line-of-sight")


def build_case(name: str) -> list[str]:
    files = EVALS / name / "files"
    if name in NOTHING:
        return []
    if name not in IMAGE_CASES and name not in FIXTURES:
        raise SystemExit(f"error: unknown case {name!r}")
    clean_owned(files)
    if name in IMAGE_CASES:
        return _images(name, files, IMAGE_CASES[name])
    return FIXTURES[name](files)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Build the generated files of the eval cases")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--case", help="a case folder name under skills/booth-proposal/evals/")
    g.add_argument("--all", action="store_true", help="every case")
    a = ap.parse_args(argv)
    names = sorted(p.name for p in EVALS.iterdir() if p.is_dir()) if a.all else [a.case]
    for name in names:
        if not (EVALS / name).is_dir():
            ap.error(f"no such case: {name}")
        built = build_case(name)
        print(f"{name}: {len(built)} generated file(s)")
        for rel in built:
            print(f"  {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
