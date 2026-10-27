"""Draw a booth floor plan in the style of an architectural presentation drawing.

Usage:  python draw_plan.py plan SPEC OUTBASE [--project P] [--lang L] [--units m|ft] [--title TEXT]
Writes OUTBASE.png, OUTBASE.svg and OUTBASE.json (a sidecar/2 record, mode "plan", with the spec as its input),
prints the written paths one per line, then any moved-label or legend lines. Exit 0, or 2 for a bad invocation
or unusable input (C-INPUT, an unknown language). Geometry problems never stop the drawing (run
booth_geometry.py check for those).

SPEC is the geometry file booth_geometry.py reads (key "elements"; the older key "zones" also works) and is
validated the same way. Only these keys are used:
{
  "title": "A \u00b7 Rings of Time",
  "width": 6, "depth": 3, "unit": "m", "max_height": 4,
  "open_sides": ["front", "right"],
  "accent": "#1F5FAE",
  "elements": [
    {"label": "Hero portal", "x": 0, "y": 2.4, "w": 6, "h": 0.6, "kind": "hero"},
    {"label": "Lounge", "x": 2.4, "y": 1.0, "w": 1.0, "h": 1.0, "kind": "furniture", "shape": "cylinder"}
  ]
}
Coordinates: x from the left wall, y from the back wall toward the main aisle (front). Elements with shape
"frame" are drawn as overhead portals with their legs (band wide, default 0.3 m); "cylinder" or "circle" as a
circle; a "repeat" row piece by piece with one label; everything else, extrusions included, by its footprint.
kind: "hero" (tinted in the accent colour), "zone" (light tone), "furniture" and any other kind (outline only),
"overhead" (dashed accent outline, the drawing convention for elements above head height; "legs": true marks
where it touches the floor). "label_pos": "top" puts a zone's label near its top edge. Closed sides are drawn
as thick walls, open sides dashed, with the aisle marked.

Title: --title as given, else the spec title with file names and paths removed and a leading concept id
("A \u00b7 ", "B: ") stripped. Subtitle: built here from the spec's numbers and the language file, never read
from the spec: size, open sides and highest point, joined by " \u00b7 ", in exactly one unit.
Units: --units m (default) or ft; the spec may be in either, values are converted for display only.
Language: --lang, else brief.lang in a project; standalone it is zh when the title or a label contains CJK and
assets/labels/zh.json exists, else en. Plan words (aisle, size, sides ...) come from assets/labels/<lang>.json.
Zone numbers: every distinct label gets a number in the spec's order (common.zone_numbers; elements sharing a
label share its number; a repeat row counts once), drawn in a small disc before the label. With no installed
font that covers the text, only the numbers are drawn and the legend is printed instead.
Label placement: a label stays in place only when its number disc lies inside its own footprint and its text box
covers no other element's footprint; otherwise it moves just outside the stand with a leader line, to the free spot
with the shortest leader over all four sides (an open side wins when within 25%). A leader starts at the middle of
an edge of its own element (or its centre), is at most max(width, depth) / 3 long, and crosses no other element,
label or leader. Placed labels are grown by LABEL_GAP_REL x the label line height when a spot is tested, so two
labels never touch. A label with no spot under that cap is shown by its number alone and listed in the legend
(printed, and returned by draw()); the legend is also drawn into the plan as a key ("<n>  <label>") in the bottom
strip, right of the aisle text and the scale bar, in two columns above KEY_ROWS entries, at the label size. The
key is an obstacle for every label and leader, and the bottom margin grows to hold it. Labels never shrink.
Size: the saved PNG/SVG is cropped to the visible drawing (small pad), and every text size is multiplied by one
factor so that a zone label line is at least about 1.2% of the image width tall (legible at deck size); the
constants are at the top of this file.
Colours and fonts come from brief/deck-style.json in a project, else built-in values. The accent is the
concept.md front matter accent, else the spec accent, else the deck-style accent.
Sidecar: written only for a spec inside a concept folder of a project; otherwise a warning line goes to stderr.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import math
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ft2font import FT2Font  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

import booth_geometry  # noqa: E402
import common  # noqa: E402
from common import InputError  # noqa: E402

PAPER, INK, MUTED, ZONE = "#FAF8F4", "#23262B", "#8C9097", "#ECE8E1"
DEFAULT_ACCENT = "#1F5FAE"
# Drawing-style constants. Text sizes are in points at font scale 1; every size is multiplied by one scale factor,
# chosen so that a zone label line is at least LABEL_REL of the final image width tall (legible at deck size).
LABEL_PT, NUM_PT, TITLE_PT, SUB_PT, AISLE_PT, BAR_PT = 7.5, 5.2, 11.0, 7.0, 7.0, 6.5
LABEL_REL = 0.0125                   # height of one label line / image width, at least
FIT_PASSES = 8                       # layout passes while the font scale converges
INCH_PER_M = 1.5                     # drawing scale: inches per metre of stand
LAYOUT_DPI, SAVE_DPI = 100, 220      # layout accuracy, and the PNG resolution
CROP_PAD_IN = 0.2                    # padding around the visible artists in the saved image (in)
MARGIN = {"left": 1.7, "right": 1.9, "top": 1.0, "bottom": 0.95}      # figure margins around the stand (m), cropped later
SUB_UP, TITLE_GAP = 0.5, 0.06        # vertical chrome (m): subtitle baseline above the stand; gap between subtitle and title
ARROW_Y, AISLE_Y, BAR_Y = (0.1, 0.42), 0.46, 0.3   # below the stand (m): main-aisle arrow head/tail, its text, the scale bar
LEADER_CAP_DIV = 3                   # a leader is at most max(width, depth) / this long (spec units)
LEGEND_SEP = "\n"
LEADER_CLEAR_PX = 4                  # a leader keeps this far from every other element's outline (no running along it)
FOOT_EPS_PX = 0.5                   # a label box within this of another element's outline counts as touching it
SPOT_STEP, RING_STEP, RINGS = 0.18, 0.35, 6    # label spots: step along a side, outward per ring (m), rings
LEADER_OPEN_TOL = 0.25               # an open-side spot wins when its leader is within this of the shortest
LABEL_GAP_REL = 0.4                  # placed labels are grown by this x the label line height on every side when a spot is tested
KEY_ROWS = 4                         # the key of number-only labels has one column up to this many entries, else two
KEY_TOP, KEY_GAP, KEY_COL_GAP = 0.22, 0.4, 0.5   # key: top below the stand; gap right of the aisle text / scale bar; between columns (m)
KEY_SEP = "  "                       # between the number and the text in a key entry
FIT_LIMIT = 14                       # hard cap on layout passes (font scale and key content converge together)
_PUNCT = "\u00b7,\uff0c;\uff1b()\uff08\uff09"
PATH_RE = (rf"[^\s{_PUNCT}]*(?:renders|concepts|brief|input|pack|prompts)[/\\][^\s{_PUNCT}]*"
           rf"|[^\s{_PUNCT}]+\.(?:png|jpe?g|webp|json|md|svg|txt)\b")
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_GENERIC_FONTS = {"sans-serif", "serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif",
                  "ui-serif", "ui-monospace", "-apple-system", "blinkmacsystemfont"}


# ---------- language, colours, accent, font ----------

def _all_text(spec: dict) -> str:
    return spec.get("title", "") + "".join(e.get("label", "") for e in spec.get("elements", spec.get("zones", [])))


def resolve_lang(arg: str | None, project, spec: dict) -> str:
    """--lang, else brief.lang; standalone: zh when the title or a label is CJK and zh.json exists, else en."""
    if arg:
        return arg
    if project is not None and project.lang:
        return project.lang
    if common.has_cjk(_all_text(spec)) and os.path.isfile(os.path.join(common.SKILL_DIR, "assets", "labels",
                                                                        "zh.json")):
        return "zh"
    return "en"


def resolve_accent(front_matter: dict, spec: dict, style: dict) -> str:
    """Concept front matter, then the spec, then the deck-style accent, then a built-in blue."""
    colours = style.get("colors") if isinstance(style.get("colors"), dict) else {}
    for value in ((front_matter or {}).get("accent"), spec.get("accent"), colours.get("accent")):
        if isinstance(value, str) and _HEX_RE.match(value):
            return value
    return DEFAULT_ACCENT


def plan_colours(style: dict) -> dict:
    colours = style.get("colors") if isinstance(style.get("colors"), dict) else {}
    out = {}
    for key, field, default in (("paper", "paper", PAPER), ("ink", "ink", INK), ("muted", "muted_text", MUTED),
                                ("zone", "tint", ZONE)):
        value = colours.get(field)
        out[key] = value if isinstance(value, str) and _HEX_RE.match(value) else default
    return out


def _covers(path: str, chars: set[str]) -> bool:
    try:
        charmap = FT2Font(path).get_charmap()
    except Exception:
        return False
    return all(ord(c) in charmap for c in chars)


def _family(path: str) -> str | None:
    try:
        font_manager.fontManager.addfont(path)
        return FT2Font(path).family_name
    except Exception:
        return None


def pick_font(texts: list[str], style: dict) -> tuple[str | None, bool]:
    """(family, covers all text). The deck-style sans families first, then a system font, then matplotlib's own
    default (returned as None). (None, False) when nothing covers the text."""
    chars = {c for t in texts for c in t if not c.isspace()}
    fonts = style.get("fonts") if isinstance(style.get("fonts"), dict) else {}
    sans = fonts.get("sans") if isinstance(fonts.get("sans"), str) else ""
    names = [n.strip().strip("\"'").strip() for n in sans.split(",")]
    for name in names:
        if not name or name.lower() in _GENERIC_FONTS:
            continue
        for f in font_manager.fontManager.ttflist:
            if f.name.lower() == name.lower() and _covers(f.fname, chars):
                return f.name, True
    path = common.find_font(cjk=common.has_cjk("".join(texts)))
    if path and _covers(path, chars):
        family = _family(path)
        if family:
            return family, True
    default = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans"), fallback_to_default=True)
    if _covers(default, chars):
        return None, True
    return None, False


# ---------- numbers, title, subtitle ----------

def fmt_len(value: float, units: str) -> str:
    text = f"{value:.2f}" if units == "m" else f"{value:.1f}"
    text = text.rstrip("0").rstrip(".") if "." in text else text
    return "0" if text in ("-0", "") else text


def subtitle(fact: dict, chrome: dict, units: str) -> str:
    """Size, open sides and highest point from the facts; one unit; no text taken from the spec."""
    su = fact["unit"]
    f = common.unit_factor(units)

    def show(v):
        return fmt_len(common.to_m(v, su) * f, units)

    parts = [f"{chrome['size']} {show(fact['width'])} \u00d7 {show(fact['depth'])} {units}"]
    sides = [s for s in ("front", "back", "left", "right") if s in fact.get("open_sides", [])]
    if sides:
        parts.append(f"{chrome['open_sides']} " + chrome["list_sep"].join(chrome["sides"][s] for s in sides))
    parts.append(f"{chrome['highest_point']} {show(fact['highest_point'])} {units}")
    return " \u00b7 ".join(parts)


def clean_title(title: str) -> str:
    """No file names or paths in a plan title."""
    s = title or ""
    s = re.sub(rf"(?i)\b(?:built\s+from|based\s+on|from)\s+(?:{PATH_RE})", "", s)
    s = re.sub(PATH_RE, "", s, flags=re.I)
    parts = [p.strip(" ,;\uff0c\uff1b") for p in re.split(r"\s*\u00b7\s*", s)]
    return " \u00b7 ".join(p for p in parts if p)


def strip_id(title: str) -> str:
    """Drop a leading concept id: "A \u00b7 Gate" and "B: Quay" become "Gate" and "Quay"."""
    return re.sub("^\\s*[A-Za-z0-9]{1,3}\\s*(?:\u00b7|:|\\s[-\u2013]\\s)\\s*", "", title)


# ---------- label placement ----------

def _bb(art, renderer, pad=1.5):
    """Display box of an artist, or of a label with its number badge (a dict)."""
    arts = [art["art"]] + ([art["num"]] if art.get("num") else []) if isinstance(art, dict) else [art]
    bs = [a.get_window_extent(renderer=renderer) for a in arts]
    return (min(b.x0 for b in bs) - pad, min(b.y0 for b in bs) - pad,
            max(b.x1 for b in bs) + pad, max(b.y1 for b in bs) + pad)


def _hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _inside(a, f):
    return a[0] >= f[0] and a[1] >= f[1] and a[2] <= f[2] and a[3] <= f[3]


def _seg_hits_box(p, q, b):
    """True when the segment p-q touches the box b = (x0, y0, x1, y1) (Liang-Barsky clipping)."""
    x0, y0 = p
    dx, dy = q[0] - x0, q[1] - y0
    t0, t1 = 0.0, 1.0
    for num, den in ((x0 - b[0], -dx), (b[2] - x0, dx), (y0 - b[1], -dy), (b[3] - y0, dy)):
        if den == 0:
            if num < 0:
                return False
            continue
        t = num / den
        if den < 0:
            if t > t1:
                return False
            t0 = max(t0, t)
        else:
            if t < t0:
                return False
            t1 = min(t1, t)
    return True


def _segs_cross(a, b, c, d):
    def turn(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return turn(a, b, c) * turn(a, b, d) < 0 and turn(c, d, a) * turn(c, d, b) < 0


def _clear(bb, placed, frame, segs=()):
    """Free of every placed box and leader line, and either wholly inside or wholly outside the stand outline."""
    if any(_hit(bb, p) for p in placed) or any(_seg_hits_box(s[0], s[1], bb) for s in segs):
        return False
    return _inside(bb, frame) or not _hit(bb, frame)


def _touch(a, b, eps=FOOT_EPS_PX):
    """True when the boxes overlap or touch (b is grown by eps pixels): another element's outline counts."""
    return a[0] <= b[2] + eps and b[0] - eps <= a[2] and a[1] <= b[3] + eps and b[1] - eps <= a[3]


def _disc(lab, r, fig):
    """Display box of the number disc (or, with no disc, of the number text itself)."""
    num = lab.get("num")
    if num is None:
        b = lab["art"].get_window_extent(renderer=r)
        return (b.x0, b.y0, b.x1, b.y1)
    b = num.get_window_extent(renderer=r)
    pad = 0.22 * num.get_fontsize() * fig.dpi / 72
    side = max(b.width, b.height) + 2 * pad
    cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
    return (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)


def _anchors(rects):
    """Leader anchors on a footprint: the midpoints of its four edges, then its centre (never a corner)."""
    out = []
    for x0, y0, x1, y1 in rects:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        out += [(x0, cy), (x1, cy), (cx, y0), (cx, y1), (cx, cy)]
    return out


_SIDE_NAME = {"left": "left", "right": "right", "top": "back", "bottom": "front"}     # outside spot -> booth side
_ANCHOR = {"left": ("right", "center"), "right": ("left", "center"),
           "top": ("center", "bottom"), "bottom": ("center", "top")}


def _spots(lab, ax, r, W, D, k):
    """Every candidate spot outside the stand for one label: (side, label position, display box).
    The display box of a spot is the label's box moved there (measured once per anchor type)."""
    art = lab["art"]
    x0, y0, x1, y1 = lab["box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    right0, left0, bottom0 = W + 0.12 * k, -0.12 * k, D + 0.12 * k      # the aisle text and arrow are obstacles
    offsets = {}
    for side, (ha, va) in _ANCHOR.items():
        art.set_position((cx, cy))
        art.set_ha(ha)
        art.set_va(va)
        bb = _bb(lab, r)
        ax0, ay0 = ax.transData.transform((cx, cy))
        offsets[side] = (bb[0] - ax0, bb[1] - ay0, bb[2] - ax0, bb[3] - ay0)
    art.set_position(lab["pos"])
    art.set_ha(lab["ha"])
    art.set_va(lab["va"])
    steps = [0.0] + [s * j * SPOT_STEP * k for j in range(1, 60) for s in (1, -1)]
    for ring in range(RINGS):
        out = ring * RING_STEP * k
        for side in ("left", "right", "top", "bottom"):
            for d in steps:
                if side == "left":
                    pos = (left0 - out, cy + d)
                elif side == "right":
                    pos = (right0 + out, cy + d)
                elif side == "top":
                    pos = (cx + d, -0.12 * k - out)
                else:
                    pos = (cx + d, bottom0 + out)
                if side in ("left", "right") and not -0.6 * k <= pos[1] <= D + 0.6 * k:
                    continue
                if side in ("top", "bottom") and not -1.4 * k <= pos[0] <= W + 1.6 * k:
                    continue
                px, py = ax.transData.transform(pos)
                o = offsets[side]
                yield side, pos, (px + o[0], py + o[1], px + o[2], py + o[3])


def number_only(lab, ax):
    """Show the label as its number alone, centred on its own footprint (the text goes to the legend)."""
    x0, y0, x1, y1 = max(lab["foot"], key=lambda f: (f[2] - f[0]) * (f[3] - f[1]))
    centre = ((x0 + x1) / 2, (y0 + y1) / 2)
    art = lab["art"]
    if lab.get("num") is not None:
        lab["num"].remove()
        art.set_text("")
        lab["num"] = ax.annotate(lab["n"], xy=centre, xycoords="data", ha="center", va="center",
                                 fontsize=lab["num_pt"], color="white", fontweight="bold", zorder=5,
                                 bbox=dict(boxstyle="circle,pad=0.22", fc=lab["disc_fc"], ec="none"))
    else:
        art.set_position(centre)
        art.set_ha("center")
        art.set_va("center")
    lab["only"] = True


def place_labels(fig, ax, labels, obstacles, W, D, k, open_sides, muted=MUTED, feet=(), cap=None):
    """Place every label. A label stays where it is only when its number disc lies inside its own footprint, its
    text box covers no other element's footprint (touching an outline counts) and it is clear of the chrome, the
    other labels and the leaders. Any other label moves outside the stand with a leader line: the free spot with
    the shortest leader over all sides (an open-side spot wins when its leader is within LEADER_OPEN_TOL of the
    shortest). A leader starts at the midpoint of an edge of its own element (or its centre), is at most `cap` long
    (spec units), crosses no other element's footprint, no placed or pending label and no other leader; the strict
    pass also keeps it clear of the chrome (title, scale bar, aisle text). When no spot fits, the label is shown by
    its number alone, centred on its footprint. `feet` is a list of {"eid", "rect"} (data units): every element's
    footprint; a label's own are those with its "eid". Returns (leaders, only): leaders are dicts {label (index in
    labels), seg (display points), length (spec units)}, only the indexes of the labels shown by number alone."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()

    def disp(rect):
        (a, b), (c, d) = ax.transData.transform(rect[:2]), ax.transData.transform(rect[2:])
        return (min(a, c), min(b, d), max(a, c), max(b, d))

    (fx0, fy0), (fx1, fy1) = ax.transData.transform((0, 0)), ax.transData.transform((W, D))
    frame = (min(fx0, fx1), min(fy0, fy1), max(fx0, fx1), max(fy0, fy1))
    walls = [_bb(o, r, 0) for o in obstacles]
    label_boxes: dict[int, tuple] = {}      # boxes of labels placed so far (leaders may not cross them)
    probe = ax.text(0, 0, "Ag", fontsize=labels[0]["art"].get_fontsize()) if labels else None
    gap = LABEL_GAP_REL * probe.get_window_extent(renderer=r).height if probe is not None else 0.0
    if probe is not None:
        probe.remove()

    def occupied():
        """Boxes a label may not overlap: the chrome as it is, the placed labels grown by the minimum gap."""
        return walls + [(b[0] - gap, b[1] - gap, b[2] + gap, b[3] + gap) for b in label_boxes.values()]

    leaders: list[dict] = []
    only: list[int] = []
    order = sorted(range(len(labels)), key=lambda i: labels[i]["prio"])
    pending = {i: _bb(labels[i], r) for i in order}
    eps = 1e-6 * max(W, D, 1.0)
    for i in order:
        lab = labels[i]
        art = lab["art"]
        pending.pop(i)
        own = [f["rect"] for f in feet if f["eid"] == lab["eid"]] or [lab["box"]]
        lab["foot"] = own
        own_d = [disp(f) for f in own]
        # footprints of the other elements; one that wholly contains this element (a floor, a platform) is its host
        # and not an obstacle
        foreign = [disp(f["rect"]) for f in feet if f["eid"] != lab["eid"]
                   and not all(f["rect"][0] <= o[0] + eps and f["rect"][1] <= o[1] + eps
                               and f["rect"][2] >= o[2] - eps and f["rect"][3] >= o[3] - eps for o in own)]
        foreign_g = [(f[0] - LEADER_CLEAR_PX, f[1] - LEADER_CLEAR_PX, f[2] + LEADER_CLEAR_PX, f[3] + LEADER_CLEAR_PX)
                     for f in foreign]
        segs = [lv["seg"] for lv in leaders]
        placed = occupied()
        bb = _bb(lab, r)
        disc = _disc(lab, r, fig)
        if (_clear(bb, placed, frame, segs) and any(_inside(disc, f) for f in own_d)
                and not any(_touch(_bb(lab, r, 0), f) for f in foreign)):
            label_boxes[i] = bb
            continue
        anchors = _anchors(own)
        blockers = list(label_boxes.values()) + list(pending.values())
        found = []
        for side, pos, sbb in _spots(lab, ax, r, W, D, k):
            near = sorted(((((pos[0] - a[0]) ** 2 + (pos[1] - a[1]) ** 2) ** 0.5, a) for a in anchors),
                          key=lambda t: t[0])
            if cap is not None and near[0][0] > cap:
                continue
            if any(_hit(sbb, p) for p in placed) or _hit(sbb, frame) or any(_touch(sbb, f) for f in foreign):
                continue
            if any(_seg_hits_box(s[0], s[1], sbb) for s in segs):
                continue
            for length, anchor in near:
                if cap is not None and length > cap:
                    break
                seg = (tuple(ax.transData.transform(anchor)), tuple(ax.transData.transform(pos)))
                if any(_seg_hits_box(seg[0], seg[1], f) for f in foreign_g):
                    continue
                if any(_seg_hits_box(seg[0], seg[1], b) for b in blockers):
                    continue
                if any(_segs_cross(seg[0], seg[1], s[0], s[1]) for s in segs):
                    continue
                strict = not any(_seg_hits_box(seg[0], seg[1], w) for w in walls)
                found.append((length, side, pos, anchor, seg, sbb, strict))
                break
        pick = None
        for want in (True, False):          # strict: the leader also stays clear of title, scale bar, aisle text
            cands = [c for c in found if c[6] or not want]
            if cands:
                best = min(cands, key=lambda c: c[0])
                near_open = [c for c in cands if c[0] <= best[0] * (1 + LEADER_OPEN_TOL)
                             and _SIDE_NAME[c[1]] in open_sides]
                pick = min(near_open, key=lambda c: c[0]) if near_open else best
                break
        if pick is None:                    # nowhere free under the cap: the number alone, the text in the legend
            number_only(lab, ax)
            only.append(i)
            label_boxes[i] = _bb(lab, r)
            continue
        length, side, pos, anchor, seg, sbb, _ = pick
        ha, va = _ANCHOR[side]
        art.set_position(pos)
        art.set_ha(ha)
        art.set_va(va)
        label_boxes[i] = _bb(lab, r)
        leaders.append({"label": i, "seg": seg, "length": length})
        ax.plot([anchor[0], pos[0]], [anchor[1], pos[1]], color=muted, lw=0.5, clip_on=False, zorder=1)
        ax.plot([anchor[0]], [anchor[1]], marker="o", ms=1.6, color=muted, clip_on=False, zorder=1)
    return leaders, only


# ---------- drawing ----------

def _pieces(spec: dict) -> list[dict]:
    """Elements ready to draw: a repeat row is its pieces (no labels) plus one label-only box over the row."""
    out = []
    for eid, e in enumerate(spec["elements"]):
        e = dict(e, eid=eid)
        e.setdefault("label", "")
        if e.get("shape") == "frame":
            e["kind"], e["legs"] = "overhead", True
        if not e.get("repeat"):
            out.append(e)
            continue
        for p in common.expand_repeat(e):
            out.append(dict(p, label="", eid=eid))
        out.append({"label": e["label"], "x": e["x"], "y": e["y"], "w": e["w"], "h": e["h"],
                    "kind": "furniture", "label_only": True, "eid": eid})
    return out


def draw(spec: dict, outbase: str, *, chrome: dict, units: str, title: str, sub: str, colours: dict,
         accent: str, font: tuple[str | None, bool]) -> dict:
    spec = common.normalise_geometry(spec)
    paper, ink, muted, zone = colours["paper"], colours["ink"], colours["muted"], colours["zone"]
    family, ok = font
    if family and os.path.isfile(family):
        family = _family(family)
    ctx = {"font.family": [family]} if family else {}
    with plt.rc_context(ctx):
        return _draw(spec, outbase, chrome, units, title, sub, (paper, ink, muted, zone), accent, ok)


def _visible_extent(fig, ax, renderer):
    """Union of the window extents of the artists that show, in inches: (x0, y0, x1, y1), padded."""
    boxes = []
    for art in list(ax.patches) + list(ax.lines) + list(ax.texts):
        if not art.get_visible() or art.get_alpha() == 0:
            continue
        if hasattr(art, "get_text") and not art.get_text() and not getattr(art, "arrow_patch", None):
            continue
        b = art.get_window_extent(renderer=renderer)
        if all(map(math.isfinite, (b.x0, b.y0, b.x1, b.y1))) and b.width >= 0 and b.height >= 0:
            boxes.append(b)
    dpi = fig.dpi
    return (min(b.x0 for b in boxes) / dpi - CROP_PAD_IN, min(b.y0 for b in boxes) / dpi - CROP_PAD_IN,
            max(b.x1 for b in boxes) / dpi + CROP_PAD_IN, max(b.y1 for b in boxes) / dpi + CROP_PAD_IN)


def _key_columns(lines):
    """The key entries "<n> <text>" as "<n>  <text>", split into one column (up to KEY_ROWS) or two."""
    entries = [KEY_SEP.join(line.partition(" ")[::2]) for line in lines]
    rows = max(1, -(-len(entries) // (1 if len(entries) <= KEY_ROWS else 2)))
    return [entries[i:i + rows] for i in range(0, len(entries), rows)], rows


def _layout(spec, chrome, units, title, sub, palette, accent, ok, fs, key=()):
    """Build the figure with every text size multiplied by fs and the labels placed. `key` is the legend to draw as
    a key in the bottom strip (an obstacle for the labels). Returns (fig, info)."""
    paper, ink, muted, zone = palette
    W, D = spec["width"], spec["depth"]
    su = spec.get("unit", "m")
    k = common.unit_factor(su)
    open_sides = spec.get("open_sides", [])
    numbers = common.zone_numbers(spec["elements"])
    items = _pieces(spec)
    scale = INCH_PER_M / k                          # inches per unit

    def u(pt):                                      # a font size in drawing units
        return pt * fs / 72 / scale

    ml, mr = MARGIN["left"] * k * fs, MARGIN["right"] * k * fs
    mt, mb = MARGIN["top"] * k * fs, MARGIN["bottom"] * k * fs
    key_cols, key_rows = _key_columns(key) if key else ([], 0)
    if key_rows:                                    # the bottom margin grows to hold the key
        mb = max(mb, (KEY_TOP + 0.1) * k + key_rows * 1.9 * u(LABEL_PT))
    fig = plt.figure(figsize=((W + ml + mr) * scale, (D + mt + mb) * scale), dpi=LAYOUT_DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    fig.patch.set_facecolor(paper)
    ax.set_facecolor(paper)
    ax.set_xlim(-ml, W + mr)
    ax.set_ylim(D + mb, -mt)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.patch.set_visible(False)

    legend, labels, seen = [], [], set()
    feet = [{"eid": z["eid"], "rect": (z["x"], z["y"], z["x"] + z["w"], z["y"] + z["h"])}
            for z in items if not z.get("label_only")]
    for z in items:
        kind = z.get("kind", "zone")
        if not z.get("label_only"):
            face = {"hero": accent, "zone": zone}.get(kind, "none")
            alpha = 0.22 if kind == "hero" else 1
            edge = accent if kind == "hero" else ink
            lw = 1.4 if kind == "hero" else 0.8
            if kind == "overhead":
                ax.add_patch(Rectangle((z["x"], z["y"]), z["w"], z["h"], fill=False, edgecolor=accent,
                                       lw=1.0, ls=(0, (3, 2))))
                if z.get("legs"):
                    leg = z.get("band", 0.3 * k)
                    for lx in (z["x"], z["x"] + z["w"] - leg):
                        ax.add_patch(Rectangle((lx, z["y"]), leg, z["h"], facecolor=accent, edgecolor="none"))
            elif z.get("shape") in ("circle", "cylinder"):
                patch = Circle((z["x"] + z["w"] / 2, z["y"] + z["h"] / 2), min(z["w"], z["h"]) / 2,
                               facecolor=face, alpha=alpha, edgecolor="none")
                ax.add_patch(patch)
                ax.add_patch(Circle(patch.center, patch.radius, fill=False, edgecolor=edge, lw=lw))
            else:
                ax.add_patch(Rectangle((z["x"], z["y"]), z["w"], z["h"], facecolor=face, alpha=alpha,
                                       edgecolor="none"))
                ax.add_patch(Rectangle((z["x"], z["y"]), z["w"], z["h"], fill=False, edgecolor=edge, lw=lw))
        if not z["label"]:
            continue
        n = numbers[z["label"]]
        first = z["label"] not in seen
        seen.add(z["label"])
        if not ok and first:
            legend.append(f"{n} {z['label']}")
        text = z["label"] if ok else str(n)
        if z.get("label_only"):
            pos, ha, va, color, weight = (z["x"] + z["w"] / 2, z["y"] + z["h"] + 0.18 * k), "center", "top", ink, "bold"
        elif kind == "overhead":
            pos, ha, va, color, weight = (z["x"] + 0.25 * k, z["y"] - 0.05 * k), "left", "bottom", accent, "normal"
        else:
            ly = z["y"] + 0.22 * k if z.get("label_pos") == "top" else z["y"] + z["h"] / 2
            pos, ha, va, color = (z["x"] + z["w"] / 2, ly), "center", "center", ink
            weight = "bold" if kind == "hero" else "normal"
        art = ax.text(pos[0], pos[1], text, ha=ha, va=va, fontsize=LABEL_PT * fs, color=color, fontweight=weight,
                      zorder=4, bbox=dict(boxstyle="square,pad=0.12", fc=paper, ec="none", alpha=0.78))   # lines stop here
        num = None
        if ok:      # the zone number in a small dark disc just left of the label; it follows the label when moved
            num = ax.annotate(str(n), xy=(0, 0.5), xycoords=art, xytext=(-2.5 * fs, 0), textcoords="offset points",
                              ha="right", va="center", fontsize=NUM_PT * fs, color="white", fontweight="bold",
                              zorder=5, bbox=dict(boxstyle="circle,pad=0.22", fc=accent if kind == "hero" else ink,
                                                  ec="none"))
        labels.append({"art": art, "num": num, "pos": pos, "ha": ha, "va": va, "eid": z["eid"], "n": str(n),
                       "text": z["label"], "num_pt": NUM_PT * fs, "disc_fc": accent if kind == "hero" else ink,
                       "box": (z["x"], z["y"], z["x"] + z["w"], z["y"] + z["h"]),
                       "prio": (0 if kind == "hero" else 2 if kind == "overhead" else 1, len(labels))})

    wall_lines = {"back": ((0, W), (0, 0)), "front": ((0, W), (D, D)),
                  "left": ((0, 0), (0, D)), "right": ((W, W), (0, D))}
    for name, (xs, ys) in wall_lines.items():
        if name in open_sides:
            ax.plot(xs, ys, color=muted, lw=0.8, ls=(0, (4, 3)))
        else:
            ax.plot(xs, ys, color=ink, lw=4, solid_capstyle="butt")

    aisle, side = chrome["main_aisle"], chrome["aisle"]
    renderer = fig.canvas.get_renderer()
    obstacles = []
    aisle_span = None                               # x range of the main-aisle text (data units)
    if "front" in open_sides:
        ax.annotate("", xy=(W / 2, D + ARROW_Y[0] * k), xytext=(W / 2, D + ARROW_Y[1] * k),
                    arrowprops=dict(arrowstyle="->", color=muted, lw=0.8))
        text = ax.text(W / 2, D + AISLE_Y * k, aisle, ha="center", va="top", fontsize=AISLE_PT * fs, color=muted)
        obstacles.append(text)
        obstacles.append(ax.plot([W / 2 - 0.08 * k, W / 2 + 0.08 * k], [D + 0.08 * k, D + (ARROW_Y[1] + 0.02) * k],
                                 alpha=0)[0])
        tb = text.get_window_extent(renderer=renderer)
        aisle_span = tuple(ax.transData.inverted().transform((x, tb.y0))[0] for x in (tb.x0, tb.x1))
    if "right" in open_sides:
        obstacles.append(ax.text(W + 0.35 * k, D / 2, side, ha="center", va="center", rotation=90,
                                 fontsize=AISLE_PT * fs, color=muted))
    if "left" in open_sides:
        obstacles.append(ax.text(-0.35 * k, D / 2, side, ha="center", va="center", rotation=90,
                                 fontsize=AISLE_PT * fs, color=muted))
    if "back" in open_sides:
        obstacles.append(ax.text(W / 2, -0.3 * k, side, ha="center", va="bottom", fontsize=AISLE_PT * fs,
                                 color=muted))

    # the scale bar sits in the bottom strip, beside the main-aisle arrow (left of its text, right of it when the
    # stand is too narrow); title and subtitle are the only things above the stand
    bar = 5 if units == "ft" else 1
    length = common.to_m(bar, units) * k            # the bar's length in the spec's own unit
    bar_y = D + BAR_Y * k
    bar_x = 0.0
    bar_text = ax.text(0, bar_y, f"{bar} {units}", va="center", fontsize=BAR_PT * fs, color=ink)
    btw = bar_text.get_window_extent(renderer=renderer)
    bar_w = length + 0.08 * k + (ax.transData.inverted().transform((btw.x1, btw.y0))[0]
                                 - ax.transData.inverted().transform((btw.x0, btw.y0))[0])
    if aisle_span and bar_x + bar_w + 0.15 * k > aisle_span[0]:
        bar_x = aisle_span[1] + 0.25 * k
    bar_text.set_position((bar_x + length + 0.08 * k, bar_y))
    obstacles.append(ax.plot([bar_x, bar_x + length], [bar_y, bar_y], color=ink, lw=1.2)[0])
    obstacles.append(bar_text)
    key_arts = []
    if key_cols:                                    # right of the aisle text and the scale bar, top just below the stand
        inv = ax.transData.inverted()

        def span(t):
            b = t.get_window_extent(renderer=renderer)
            return inv.transform((b.x1, b.y0))[0] - inv.transform((b.x0, b.y0))[0]

        kx = max(bar_x + bar_w, aisle_span[1] if aisle_span else 0.0) + KEY_GAP * k
        for col in key_cols:
            t = ax.text(kx, D + KEY_TOP * k, "\n".join(col), ha="left", va="top", fontsize=LABEL_PT * fs, color=ink,
                        linespacing=1.35)
            key_arts.append(t)
            kx += span(t) + KEY_COL_GAP * k
        obstacles += key_arts
    sub_y = -SUB_UP * k
    title_y = sub_y - 1.4 * u(SUB_PT) - TITLE_GAP * k
    obstacles.append(ax.text(0, title_y, title, fontsize=TITLE_PT * fs, fontweight="bold", color=ink, va="bottom"))
    obstacles.append(ax.text(0, sub_y, sub, fontsize=SUB_PT * fs, color=muted, va="bottom"))

    cap = max(W, D) / LEADER_CAP_DIV
    leaders, only = place_labels(fig, ax, labels, obstacles, W, D, k, open_sides, muted, feet=feet, cap=cap)
    if ok:                      # with no covering font the legend already lists every label
        for i in only:
            line = f"{labels[i]['n']} {labels[i]['text']}"
            if line not in legend:
                legend.append(line)
        legend.sort(key=lambda line: int(line.partition(" ")[0]))
    renderer = fig.canvas.get_renderer()
    boxes = [_bb(lab, renderer) for lab in labels]
    crop = _visible_extent(fig, ax, renderer)
    probe = ax.text(0, 0, "Ag", fontsize=LABEL_PT * fs)
    label_in = probe.get_window_extent(renderer=renderer).height / fig.dpi      # height of one label line (in)
    probe.remove()
    foot = {}
    for f in feet:
        (a, b), (c, d) = ax.transData.transform(f["rect"][:2]), ax.transData.transform(f["rect"][2:])
        foot.setdefault(f["eid"], []).append((min(a, c), min(b, d), max(a, c), max(b, d)))
    discs = [_disc(lab, renderer, fig) for lab in labels]
    kb = [t.get_window_extent(renderer=renderer) for t in key_arts]
    key_box = (min(b.x0 for b in kb), min(b.y0 for b in kb), max(b.x1 for b in kb), max(b.y1 for b in kb)) if kb else None
    info = {"key_box": key_box, "key": list(key), "leaders": leaders, "boxes": boxes, "numbers": numbers,
            "legend": legend, "crop": crop, "label_in": label_in, "fs": fs, "only": only, "cap": cap, "owners": [lab["eid"] for lab in labels],
            "footprints": foot, "discs": discs, "stand_in": D * scale}
    return fig, info


def _draw(spec, outbase, chrome, units, title, sub, palette, accent, ok):
    """Lay the plan out until the font scale and the key agree: the key lists the labels shown by number only, and it
    is itself an obstacle (and widens the image), so it is redrawn until it equals the legend of its own layout. If
    that does not settle, the key only grows (a union), so that it always covers the legend."""
    fs, key = 1.0, []
    for attempt in range(FIT_LIMIT):
        fig, info = _layout(spec, chrome, units, title, sub, palette, accent, ok, fs, key)
        width_in = info["crop"][2] - info["crop"][0]
        rel = info["label_in"] / width_in
        legend = info["legend"] if ok else []        # with no covering font the printed legend lists every label
        same = set(legend) <= set(key) if attempt >= 4 else legend == key
        if (rel >= LABEL_REL and same) or attempt == FIT_LIMIT - 1:
            break
        plt.close(fig)
        if rel < LABEL_REL:
            fs *= LABEL_REL / rel * 1.03
        key = list(legend) if attempt < 4 else sorted(set(key) | set(legend), key=lambda t: int(t.partition(" ")[0]))
    x0, y0, x1, y1 = info["crop"]
    folder = os.path.dirname(outbase)
    if folder:
        os.makedirs(folder, exist_ok=True)
    box = Bbox([[x0, y0], [x1, y1]])
    fig.savefig(f"{outbase}.png", bbox_inches=box, facecolor=palette[0], dpi=SAVE_DPI)
    fig.savefig(f"{outbase}.svg", bbox_inches=box, facecolor=palette[0], metadata={"Date": None})
    plt.close(fig)
    leaders = info["leaders"]
    if leaders:
        print(f"{len(leaders)} crowded label(s) moved outside the stand with a leader line")
    if not ok:
        print("No font covers the plan text: zones are numbered on the plan; show this legend next to it:")
        print(LEGEND_SEP.join(info["legend"]))
    elif info["only"]:
        print(f"{len(info['only'])} label(s) shown by number only; see the legend")
        print(LEGEND_SEP.join(info["legend"]))
    return {"moved": len(leaders), "boxes": info["boxes"], "numbers": info["numbers"], "legend": info["legend"],
            "leaders": leaders, "max_leader": max((lv["length"] for lv in leaders), default=0.0),
            "leader_cap": info["cap"], "number_only": list(info["only"]), "owners": info["owners"],
            "footprints": info["footprints"], "discs": info["discs"],
            "stand_frac": info["stand_in"] / (info["crop"][3] - info["crop"][1]),
            "key_box": info["key_box"], "key": info["key"], "crop_in": info["crop"],
            "label_rel": info["label_in"] / width_in, "width_in": width_in, "width_px": round(width_in * SAVE_DPI),
            "font_scale": info["fs"]}


# ---------- command line ----------

def _project(arg):
    """The project for --project P, or for "." when ./brief/ exists, else None (standalone)."""
    if arg is not None:
        return common.find_project(arg)
    if os.path.isdir("brief"):
        return common.find_project(".")
    return None


def _build_parser():
    ap = argparse.ArgumentParser(description="Draw a booth floor plan (PNG, SVG and sidecar) from a geometry spec.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="draw the plan of one geometry spec")
    p.add_argument("spec", help="geometry spec (JSON)")
    p.add_argument("outbase", metavar="OUTBASE", help="output path without extension")
    p.add_argument("--project", help="project folder (default: . when it has brief/, else standalone)")
    p.add_argument("--lang", help="plan language (default: brief.lang, else from the labels)")
    p.add_argument("--units", choices=("m", "ft"), default="m", help="display unit (default m)")
    p.add_argument("--title", help="plan title (default: the spec title without paths and concept id)")
    return ap


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    a = _build_parser().parse_args(argv)
    try:
        project = _project(a.project)
        spec, found = booth_geometry.load_spec(a.spec)
        if found:
            for f in found:
                print(f"{'ERROR':<7} {f.code:<18} {f.where}: {f.message}", file=sys.stderr)
            return 2
        lang = resolve_lang(a.lang, project, spec)
        chrome = common.load_labels(lang)["chrome"]
        style = project.style if project else {}
        concept = common.concept_of_path(project, a.spec) if project else None
        front = common.read_front_matter(concept)[0] if concept else {}
        title = a.title if a.title is not None else strip_id(clean_title(spec.get("title", "")))
        sub = subtitle(booth_geometry.facts(spec), chrome, a.units)
        texts = [title, sub, chrome["main_aisle"], chrome["aisle"]] + [e.get("label", "") for e in spec["elements"]]
        font = pick_font(texts, style)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            draw(spec, a.outbase, chrome=chrome, units=a.units, title=title, sub=sub,
                 colours=plan_colours(style), accent=resolve_accent(front, spec, style), font=font)
        written = [a.outbase + ".png", a.outbase + ".svg"]
        if project is None:
            print(f"warning: {a.outbase}: no project found \u2013 sidecar not written", file=sys.stderr)
        elif concept is None:
            print(f"warning: {a.outbase}: spec is not inside a concept folder \u2013 sidecar not written",
                  file=sys.stderr)
        else:
            name = os.path.basename(a.outbase)
            common.write_sidecar(a.outbase + ".png", {
                "tool": "draw_plan.py", "mode": "plan", "set": concept.set, "concept": concept.id,
                "inputs": [{"role": "spec", "path": project.rel(a.spec), "sha256": common.sha256_file(a.spec)}],
                "outputs": {name + ".png": "", name + ".svg": ""}, "prompt_sha256": None, "lint": None})
            written.append(common.sidecar_path(a.outbase + ".png"))
        print("\n".join(written))
        sys.stdout.write(buf.getvalue())
        return 0
    except InputError as e:
        print(f"{'ERROR':<7} {e.code:<18} {e.where}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
