"""Booth geometry: check that a concept fits its envelope; massing is an internal white model, never in the proposal.

The geometry spec (JSON) is the single source of truth for a concept's dimensions. The geometry check, the plan
drawing (draw_plan.py) and the massing images all read the same file. The spec is written after the renders, from
the chosen hero view, and fixes that design at its real size; if the check fails, the design changes and is rendered
again. The massing images are internal documentation only, never an image-model input and never in the proposal.

Usage (every command also takes --project P; without it the project is "." when ./brief/ exists, else the command
runs standalone with the default thresholds and writes no sidecar):
  python booth_geometry.py check   SPEC [--json]   -> findings (GEO-*) and "RESULT: PASS" or "RESULT: FAIL" (exit 1)
  python booth_geometry.py massing SPEC OUTBASE [--views hero,front] [--size 1536x1024]
                                   -> OUTBASE-hero.png (three-quarter view from the open corner), OUTBASE-front.png,
                                      and, inside a project concept folder, OUTBASE-<view>.json (mode "massing")
  python booth_geometry.py hints   SPEC            -> prints every element's render_hint (what its pieces stand for)
  python booth_geometry.py facts   SPEC            -> JSON: unit, width, depth, max_height, highest_point, open_sides,
                                      area, floor_cover, zones (n, label, kind, program, top), program_served,
                                      required_missing
Exit codes: 0 done, 1 at least one error finding, 2 unusable input (C-INPUT: unreadable JSON, a field of the wrong
type with its JSON path, a unit other than m or ft, a bad option).

Findings: GEO-FIT (error: footprint, height, headroom, profile, zone-height, overlap, rigging), GEO-PROGRAM (error:
program) and GEO-ADVICE (warning: walkway, underside, support, rigging-unconfirmed, span, noheight). The message
starts with the rule name; "where" is the element id.

Units: "unit" is "m" (default) or "ft". Thresholds come from common.DEFAULTS (metres, scaled by the unit) and may be
overridden per project in brief/deck-style.json "thresholds"; a spec's own "walkway" and "headroom" win for that spec.

Massing views: a white scaled model seen through a pinhole camera at eye level, 35 mm, with a person for scale
(common.DEFAULTS person_height_m), fitted so the stand fills the frame. A spec may fix a camera:
"camera": {"hero": {"eye": [x, y, z], "target": [x, y, z], "lens_mm": 35}}. "wall_height" draws the closed sides
as walls of that height.

Spec:
{
  "title": "Harbour Gate", "width": 6, "depth": 3, "max_height": 6, "unit": "m",
  "open_sides": ["front", "right"],            # front = main aisle
  "camera_corner": "right",                    # hero view from the front-right (or "left") corner
  "elements": [
    {"id": "Z1", "label": "Counter", "kind": "zone", "shape": "box",
     "x": 3.9, "y": 2.15, "w": 1.8, "h": 0.5, "z": 0, "height": 1.1},
    {"id": "Z2", "label": "Ring 1", "kind": "overhead", "shape": "frame",
     "x": 0, "y": 2.75, "w": 6, "h": 0.12, "height": 4.2, "band": 0.3, "support": "legs"},
    {"id": "Z3", "label": "Table", "kind": "furniture", "shape": "cylinder",
     "x": 2.35, "y": 1.36, "w": 0.6, "h": 0.6, "height": 0.75}
  ]
}
Coordinates in metres (or feet): x from the left wall as seen from the main aisle, y from the back wall
toward the aisle, z up from the floor. w is the size along x, h the size along y, height along z.
shape: box (default) | cylinder (w is the diameter; h is ignored) | frame (a portal: two legs and a top beam,
       "band" thick, spanning w) | extrusion (a curved or stepped surface: "profile" is a list of [d, z] points
       along "axis" ("x", the default: d from the element's x across its width, swept over its depth h;
       or "y": d from the element's y across its depth, swept over its width w); use it for shells, canopies,
       vaults, ribbons, steps. The highest profile point counts as the element's top).
kind: hero | zone | furniture | overhead (any other word, such as brand, is a plain element).
"contains": true lets an element enclose others in plan
(for example a canopy over a lounge) without counting as an overlap.

Constraints the check enforces (all optional except width, depth, max_height):
  "unit": "m" or "ft"            thresholds (common.DEFAULTS, metres) scale with the unit
  "walkway", "headroom"          override the default minimums with the venue's own rules
  "height_zones": [{"y_from": 0, "y_to": 1.5, "max": 1.22, "note": "line of sight"}]
                                 extra height limits by depth band (y from the back wall), e.g. line-of-sight rules
  "rigging_allowed": true/false  from the venue card; null or missing = not confirmed
  "required": ["screen", "counter", "storage", ...]
                                 program items from the brief; each must be served by an element's "program"
  "envelope_override": [{"field": "max_height", "value": 5.0, "reason": "..."}]
                                 declares that width, depth or max_height deliberately differs from the booth in
                                 brief.json (value in the spec's unit, a reason that says why); read by gates.py concepts, which
                                 accepts an override only with a non-blank reason
Per element:
  "repeat": {"count": 75, "dx": 0.056, "dy": 0, "height_to": 4.2}
                                 a row of identical pieces (fins, steps, columns): count pieces, each moved by dx/dy;
                                 heights run linearly from "height" to "height_to". The whole row must fit, and it is
                                 checked as one block, so count x pitch errors are caught.
  "group": "ridge"               members of a group are one compound piece: no overlap or walkway checks between
                                 them, and the group's bounding box is checked against everything else
  "program": "counter" or ["counter", "storage"]   which required items it serves
  "support": "floor" | "wall" | "legs" | "columns" | "hung"   state it for every overhead, frame and extrusion element;
                                 a missing support is a warning, "hung" where rigging_allowed is false an error
  "render_hint": "..."           what the element really looks like (as in the chosen render) when its spec shape is
                                 only an approximation ("one continuous layered mountain ridge, low at the left,
                                 highest near the right"); printed by `hints`. A note for reading plan, massing and
                                 render together, not text for a hero prompt
  "layer": 0                     manual paint order for the massing (lower paints first); only needed when two
                                 pieces intersect, e.g. a ribbon resting on a counter
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys

import common
from common import Finding, InputError


def load_spec(path: str) -> tuple[dict | None, list[Finding]]:
    """Read and validate a geometry spec. InputError C-INPUT propagates for unreadable JSON; schema problems come
    back as findings (spec None); otherwise the normalised spec."""
    raw = common.read_json(path)
    found = common.validate_geometry(raw)
    if found:
        return None, found
    return common.normalise_geometry(raw), []


def element_top(e: dict) -> float:
    """z + height; for an extrusion with a profile also the highest profile point (the larger wins)."""
    top = e.get("z", 0) + e.get("height", 0)
    if e.get("shape") == "extrusion" and e.get("profile"):
        top = max(top, max(p[1] for p in e["profile"]))
    return top


def on_floor(e, tol):
    return (e["z"] <= tol and e.get("kind") != "overhead" and e.get("shape") not in ("frame", "extrusion")
            and not e.get("contains"))


def gap(a, b):
    dx = max(b["x"] - (a["x"] + a["w"]), a["x"] - (b["x"] + b["w"]), 0)
    dy = max(b["y"] - (a["y"] + a["h"]), a["y"] - (b["y"] + b["h"]), 0)
    return (dx * dx + dy * dy) ** 0.5, dx, dy


def union(members):
    """Bounding box of a group of floor pieces, checked as one piece against everything else."""
    x0, y0 = min(b["x"] for b in members), min(b["y"] for b in members)
    x1, y1 = max(b["x"] + b["w"] for b in members), max(b["y"] + b["h"] for b in members)
    return {"id": f'group {members[0]["group"]}', "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
            "leg": all(b.get("leg") for b in members)}


def _thresholds(th: dict | None) -> dict:
    return {**common.DEFAULTS, **(th or {})}


def problems(spec: dict, th: dict | None = None) -> list[Finding]:
    """Geometry findings for a normalised spec: GEO-FIT and GEO-PROGRAM errors, GEO-ADVICE warnings."""
    th = _thresholds(th)
    W, D, H = spec["width"], spec["depth"], spec["max_height"]
    k = common.unit_factor(spec.get("unit", "m"))
    tol = th["geometry_tol"] * k
    WALKWAY = spec.get("walkway", th["walkway_m"] * k)
    HEADROOM = spec.get("headroom", th["headroom_m"] * k)
    SPAN = th["span_m"] * k
    out: list[Finding] = []

    def fit(where, rule, text):
        out.append(Finding("GEO-FIT", "error", where, f"{rule}: {text}"))

    def advice(where, rule, text):
        out.append(Finding("GEO-ADVICE", "warn", where, f"{rule}: {text}"))

    for e in spec["elements"]:
        eid = e["id"]
        top = element_top(e)
        if e["x"] < -tol or e["y"] < -tol or e["x"] + e["w"] > W + tol or e["y"] + e["h"] > D + tol:
            fit(eid, "footprint", f"outside the {W} × {D} footprint "
                                  f"(x {e['x']}–{e['x'] + e['w']:.2f}, y {e['y']}–{e['y'] + e['h']:.2f})")
        if "height" not in e and not (e.get("shape") == "extrusion" and e.get("profile")):
            advice(eid, "noheight", "no height given")
        if top > H + tol:
            fit(eid, "height", f"top at {top:.2f} exceeds the {H} height limit")
        if e.get("shape") == "frame" and "height" in e:
            clear = e["height"] - e.get("band", 0.3 * k)
            if clear < HEADROOM:
                fit(eid, "headroom", f"clear opening {clear:.2f} is below {round(HEADROOM, 2)} headroom")
        if e.get("shape") == "extrusion":
            prof = e.get("profile", [])
            span, along = (e["w"], "width") if e.get("axis", "x") == "x" else (e["h"], "depth")
            if prof and (max(p[0] for p in prof) > span + tol or min(p[0] for p in prof) < -tol):
                fit(eid, "profile", f"profile runs outside its {along} {span}")
        if e.get("kind") == "overhead" and e.get("shape") not in ("frame", "extrusion") and e["z"] < HEADROOM - tol:
            advice(eid, "underside", f"underside at {e['z']:.2f}, below {round(HEADROOM, 2)} headroom")
        for zone in spec.get("height_zones", []):
            if e["y"] < zone["y_to"] - tol and e["y"] + e["h"] > zone["y_from"] + tol and top > zone["max"] + tol:
                fit(eid, "zone-height",
                    f"top at {top:.2f} exceeds {zone['max']} in the band y {zone['y_from']}–{zone['y_to']}"
                    + (f" ({zone['note']})" if zone.get("note") else ""))
        structural = e.get("kind") == "overhead" or e.get("shape") in ("frame", "extrusion")
        if structural:
            support = e.get("support")
            if not support:
                advice(eid, "support", "state how it is supported (floor, wall, legs, columns or hung)")
            elif support == "hung":
                if spec.get("rigging_allowed") is False:
                    fit(eid, "rigging", "hung, but the venue does not allow rigging")
                elif spec.get("rigging_allowed") is None:
                    advice(eid, "rigging-unconfirmed", "hung, but rigging is not confirmed by the venue")
            elif support == "wall" and e["w"] > SPAN + tol:
                advice(eid, "span", f"spans {e['w']:.2f} from a single wall; add columns or have the structure reviewed")
    floor = [e for e in spec["elements"] if on_floor(e, tol)]
    legs = []
    for e in spec["elements"]:
        if e.get("shape") == "frame":
            band = e.get("band", 0.3 * k)
            for side, lx in (("left leg", e["x"]), ("right leg", e["x"] + e["w"] - band)):
                legs.append({"id": f'{e["id"]} {side}', "x": lx, "y": e["y"], "w": band, "h": e["h"], "leg": True,
                             "group": e.get("group")})
    bodies = [b for b in floor + legs if b.get("group") is None]
    for g in dict.fromkeys(b["group"] for b in floor + legs if b.get("group") is not None):
        bodies.append(union([b for b in floor + legs if b.get("group") == g]))
    for a, b in itertools.combinations(bodies, 2):
        pair = f"{a['id']} / {b['id']}"
        d, dx, dy = gap(a, b)
        if a.get("leg") or b.get("leg"):
            ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            if ox > tol and oy > tol and not (a.get("leg") and b.get("leg")):
                fit(pair, "overlap", f"{a['id']} and {b['id']} overlap on the floor")
            continue
        if dx <= tol and dy <= tol:
            overlap_x = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            overlap_y = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            if overlap_x > tol and overlap_y > tol:
                fit(pair, "overlap", f"{a['id']} and {b['id']} overlap on the floor")
        elif d < WALKWAY - tol:
            advice(pair, "walkway", f"{a['id']} and {b['id']}: only {d:.2f} apart (walkway guide {round(WALKWAY, 2)})")
    served = set()
    for e in spec["elements"]:
        p = e.get("program", [])
        served.update([p] if isinstance(p, str) else p)
    for item in spec.get("required", []):
        if item not in served:
            out.append(Finding("GEO-PROGRAM", "error", "required",
                               f"program: required program item '{item}' is not served by any element"))
    return out


def facts(spec: dict) -> dict:
    """Numbers and names of a normalised spec, in the spec's unit (3 decimals): size, highest point, floor cover,
    one zone per distinct label (numbered as the plan numbers them), the program served and what is missing."""
    k = common.unit_factor(spec.get("unit", "m"))
    tol = common.DEFAULTS["geometry_tol"] * k
    els = spec["elements"]

    def r(v):
        return round(v, 3)

    served = set()
    for e in els:
        p = e.get("program", [])
        served.update([p] if isinstance(p, str) else p)
    zones = []
    for label, n in common.zone_numbers(els).items():
        members = [e for e in els if e.get("label") == label]
        prog = set()
        for e in members:
            p = e.get("program", [])
            prog.update([p] if isinstance(p, str) else p)
        zones.append({"n": n, "label": label, "kind": members[0].get("kind", "zone"), "program": sorted(prog),
                      "top": r(max(element_top(e) for e in members))})
    return {
        "unit": spec.get("unit", "m"),
        "width": r(spec["width"]), "depth": r(spec["depth"]), "max_height": r(spec["max_height"]),
        "highest_point": r(max(element_top(e) for e in els)),
        "open_sides": list(spec.get("open_sides", [])),
        "area": r(spec["width"] * spec["depth"]),
        "floor_cover": r(sum(e["w"] * e["h"] for e in els if on_floor(e, tol))),
        "zones": zones,
        "program_served": sorted(served),
        "required_missing": [i for i in spec.get("required", []) if i not in served],
    }


def check(spec: dict, th: dict, extra: list[Finding], as_json: bool) -> int:
    th = _thresholds(th)
    W, D, H = spec["width"], spec["depth"], spec["max_height"]
    k = common.unit_factor(spec.get("unit", "m"))
    tol = th["geometry_tol"] * k
    if not as_json:
        used = sum(e["w"] * e["h"] for e in spec["elements"] if on_floor(e, tol))
        print(f"GEOMETRY CHECK · {spec.get('title', '')} · {W} × {D}, max height {H}")
        print(f"Floor elements cover {used:.1f} of {W * D:.1f} ({used / (W * D):.0%}); "
              f"walkway {spec.get('walkway', th['walkway_m'] * k):.2f}, "
              f"headroom {spec.get('headroom', th['headroom_m'] * k):.2f} {spec.get('unit', 'm')}")
    return common.print_findings(list(extra) + problems(spec, th), as_json)


def hints(spec):
    """Print each element's render_hint: what its approximate spec shape stands for."""
    for e in spec["elements"]:
        if e.get("render_hint"):
            print(" ".join(f'{e["id"]} {e.get("label", "")}:'.split()), e["render_hint"])


# ---------- massing: a white scaled model, internal, never in the proposal ----------

COLOURS = dict(bg="#F3F3F1", ground="#E9E9E6", plate="#F7F7F5", plate_edge="#9A9A96", wall="#FFFFFF",
               body="#FFFFFF", hero="#DCE3EE", person="#BDBDB8", edge="#8E8E8A")


def boxes(e):
    """Return the element as a list of (x0, y0, z0, x1, y1, z1) boxes."""
    x, y, z, w, h = e["x"], e["y"], e["z"], e["w"], e["h"]
    t = e.get("height", 0.05)
    if e.get("shape") == "frame":
        b = e.get("band", 0.3)
        return [(x, y, z, x + b, y + h, z + t), (x + w - b, y, z, x + w, y + h, z + t),
                (x, y, z + t - b, x + w, y + h, z + t)]
    return [(x, y, z, x + w, y + h, z + t)]


def box_faces(b):
    x0, y0, z0, x1, y1, z1 = b
    p = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    idx = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7), (0, 3, 2, 1)]
    return [[p[i] for i in f] for f in idx]


def cylinder_polys(e, n=28):
    cx, cy = e["x"] + e["w"] / 2, e["y"] + e["h"] / 2
    r, z0, z1 = e["w"] / 2, e["z"], e["z"] + e.get("height", 0.75)
    a = [2 * math.pi * i / n for i in range(n + 1)]
    ring = [(cx + r * math.cos(t), cy + r * math.sin(t)) for t in a]
    side = [[(*ring[i], z0), (*ring[i + 1], z0), (*ring[i + 1], z1), (*ring[i], z1)] for i in range(n)]
    return side + [[(*q, z1) for q in ring]] + [[(*q, z0) for q in ring]]


def extrusion_polys(e):
    """A profile [d, z] along the axis (x by default, or y), swept over the other size."""
    prof, along_y = e.get("profile", []), e.get("axis", "x") == "y"

    def pt(d, zz, s):
        return (e["x"] + (s * e["w"] if along_y else d), e["y"] + (d if along_y else s * e["h"]), zz)

    return [[pt(*p0, 0), pt(*p1, 0), pt(*p1, 1), pt(*p0, 1)] for p0, p1 in zip(prof, prof[1:])]


def element_bodies(spec):
    """Every drawable piece: (aabb, polygons, colour key, layer)."""
    W, D = spec["width"], spec["depth"]
    out = []
    wall_h = spec.get("wall_height", 0)
    for s, (x0, y0, x1, y1) in {"back": (0, 0, W, 0), "left": (0, 0, 0, D), "right": (W, 0, W, D)}.items():
        if s not in spec.get("open_sides", []) and wall_h:
            poly = [(x0, y0, 0), (x1, y1, 0), (x1, y1, wall_h), (x0, y0, wall_h)]
            out.append(((min(x0, x1), min(y0, y1), 0, max(x0, x1), max(y0, y1), wall_h), [poly], "wall", -1))
    for e in [p for el in spec["elements"] for p in common.expand_repeat(el)]:
        key = "hero" if e.get("kind") == "hero" or e.get("shape") == "frame" else "body"
        layer = e.get("layer", 0)
        if e.get("shape") == "cylinder":
            out.append((boxes(e)[0], cylinder_polys(e), key, layer))
        elif e.get("shape") == "extrusion":
            zs = [p[1] for p in e.get("profile", [[0, 0]])] or [0]
            out.append(((e["x"], e["y"], min(zs), e["x"] + e["w"], e["y"] + e["h"], max(zs)), extrusion_polys(e), key, layer))
        else:
            out += [(b, box_faces(b), key, layer) for b in boxes(e)]
    return out


def person_body(px, py, k, cam, s=1.0):
    """A person for scale (1.75 m times s): a body and a head disc facing the camera."""
    import numpy as np
    n = 20
    k = k * s
    a = [2 * math.pi * i / n for i in range(n + 1)]
    ring = [(px + 0.18 * k * math.cos(t), py + 0.12 * k * math.sin(t)) for t in a]
    polys = [[(*ring[i], 0), (*ring[i + 1], 0), (*ring[i + 1], 1.5 * k), (*ring[i], 1.5 * k)] for i in range(n)]
    polys.append([(*q, 1.5 * k) for q in ring])
    c = np.array([px, py, 1.63 * k])
    polys.append([tuple(c + 0.11 * k * (math.cos(t) * cam.r + math.sin(t) * cam.u)) for t in a])
    return ((px - 0.18 * k, py - 0.12 * k, 0, px + 0.18 * k, py + 0.12 * k, 1.75 * k), polys, "person", 0)


def paint_order(aabbs, eye, tol):
    """Back-to-front order for axis-aligned boxes seen from the point eye.

    A may be painted before B when an axis-aligned plane separates them with the eye on B's side: every ray from
    the eye to B stays on B's side, so A can never cover B. Exact for every non-intersecting pair; intersecting
    boxes give no constraint and fall back to centre distance (use "layer" for those)."""
    def clears(a, b):
        return any((a[i + 3] <= b[i] + tol and eye[i] >= a[i + 3] - tol) or (b[i + 3] <= a[i] + tol and eye[i] <= a[i] + tol)
                   for i in range(3))

    before = [set() for _ in aabbs]
    for i, j in itertools.combinations(range(len(aabbs)), 2):
        ij, ji = clears(aabbs[i], aabbs[j]), clears(aabbs[j], aabbs[i])
        if ij and not ji:
            before[j].add(i)
        elif ji and not ij:
            before[i].add(j)
    far = sorted(range(len(aabbs)), key=lambda i: -sum(((aabbs[i][d] + aabbs[i][d + 3]) / 2 - eye[d]) ** 2 for d in range(3)))
    order = []
    while far:
        i = next((i for i in far if not before[i]), far[0])
        order.append(i)
        far.remove(i)
        for s in before:
            s.discard(i)
    return order


class Camera:
    """A pinhole camera in stand coordinates: eye, target, 35 mm-equivalent lens, frame aspect (height / width).
    Image coordinates: x from -1 (left edge) to 1 (right edge), y from -aspect (bottom) to aspect (top)."""

    def __init__(self, eye, target, lens_mm, aspect):
        import numpy as np
        self.eye, self.target, self.lens, self.aspect = np.array(eye, float), np.array(target, float), lens_mm, aspect
        f = self.target - self.eye
        self.f = f / np.linalg.norm(f)
        r = np.cross(np.array([0.0, 0.0, 1.0]), self.f)   # x grows to the right of the picture
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.f, self.r)
        self.tan = 18.0 / lens_mm      # half the 36 mm sensor over the focal length

    def to_cam(self, pts):
        import numpy as np
        d = np.asarray(pts, float) - self.eye
        return np.column_stack([d @ self.r, d @ self.u, d @ self.f])

    def project(self, poly, near=0.08):
        """Image coordinates of a polygon, clipped at the near plane (None if nothing is in front of the camera)."""
        import numpy as np
        pts = self.to_cam(poly)
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ina, inb = a[2] >= near, b[2] >= near
            if ina:
                out.append(a)
            if ina != inb:
                t = (near - a[2]) / (b[2] - a[2])
                out.append(a + t * (b - a))
        if len(out) < 3:
            return None
        o = np.array(out)
        return np.column_stack([o[:, 0] / o[:, 2] / self.tan, o[:, 1] / o[:, 2] / self.tan])

    def pixels(self, pts, size):
        """Pixel coordinates (u right, v down) of 3D points in front of the camera, for an image of size (w, h)."""
        import numpy as np
        P = self.to_cam(pts)
        x, y = P[:, 0] / P[:, 2] / self.tan, P[:, 1] / P[:, 2] / self.tan
        return np.column_stack([(x + 1) / 2 * size[0], (self.aspect - y) / (2 * self.aspect) * size[1]])


def preset(spec, view, aspect, person_xy, s=1.0):
    """Appendix cameras, fitted so the whole stand and the scale person fill about 86 % of the frame.
    hero: eye level 1.6 m from the open front corner, 35 mm. front: eye level 1.6 m on the main aisle, 10 degrees off
    the centre line, 35 mm. A spec may fix a camera: "camera": {"hero": {"eye": [x, y, z], "target": [x, y, z], "lens_mm": 35}}."""
    import numpy as np
    W, D, k = spec["width"], spec["depth"], common.unit_factor(spec.get("unit", "m"))
    top = max(element_top(e) for e in spec["elements"])
    right = spec.get("camera_corner", "right") == "right"
    fixed = (spec.get("camera") or {}).get(view)
    if fixed:
        return Camera(fixed["eye"], fixed["target"], fixed.get("lens_mm", 35), aspect)
    if view == "hero":
        eye = ((W + 1.8 * k) if right else -1.8 * k, D + 2.4 * k, 1.6 * k)
        target = ((0.55 * W) if right else 0.45 * W, 0.45 * D, 0.45 * top)
    elif view == "front":
        d, s = max(W, D) + 2 * k, (1 if right else -1)
        eye = (W / 2 + s * d * math.sin(math.radians(10)), D + d * math.cos(math.radians(10)), 1.6 * k)
        target = (W / 2, D / 2, min(1.6 * k, 0.45 * top))
    else:
        raise ValueError(f"unknown view {view}: use hero or front")
    # every vertex the frame must hold: the floor plate, each piece and the scale person
    pts = [(x, y, 0) for x in (0, W) for y in (0, D)]
    pts += [v for _, polys, _, _ in element_bodies(spec) for p in polys for v in p]
    pts += [(person_xy[0] + sx, person_xy[1] + sy, z) for sx in (-0.2 * k * s, 0.2 * k * s) for sy in (-0.2 * k * s, 0.2 * k * s) for z in (0, 1.75 * k * s)]
    pts = np.array(pts, float)
    eye, target = np.array(eye, float), np.array(target, float)
    for _ in range(10):
        cam = Camera(eye, target, 35, aspect)
        P = cam.to_cam(pts)
        zc = np.maximum(P[:, 2], 0.5 * k)      # points beside or behind the camera count as huge: move back
        X, Y = P[:, 0] / zc / cam.tan, P[:, 1] / zc / cam.tan
        s = max((X.max() - X.min()) / 2 / 0.86, (Y.max() - Y.min()) / (2 * aspect) / 0.86)
        horiz = eye - target
        horiz[2] = 0
        eye = target + horiz * s + np.array([0, 0, eye[2] - target[2]])
        half = np.linalg.norm(target - eye) * cam.tan
        target = target + (X.max() + X.min()) / 2 * half * cam.r + (Y.max() + Y.min()) / 2 * half * cam.u
    return Camera(eye, target, 35, aspect)


def draw_view(spec, view, size, path, th=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    th = _thresholds(th)
    W, D, k = spec["width"], spec["depth"], common.unit_factor(spec.get("unit", "m"))
    s = th["person_height_m"] / 1.75
    tol = th["geometry_tol"] * k
    aspect = size[1] / size[0]
    right = spec.get("camera_corner", "right") == "right"
    person_xy = {"hero": (0.25 * W if right else 0.75 * W, D + 0.6 * k),
                 "front": ((W + 0.6 * k) if right else -0.6 * k, D + 0.3 * k)}[view]
    cam = preset(spec, view, aspect, person_xy, s)

    fig = plt.figure(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    fig.patch.set_facecolor(COLOURS["bg"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-1, 1)
    ax.set_ylim(-aspect, aspect)
    ax.axis("off")

    def add(polys3d, face, edge, lw=0.5, z=1):
        polys = [p for p in (cam.project(q) for q in polys3d) if p is not None]
        if polys:
            ax.add_collection(PolyCollection(polys, facecolors=face, edgecolors=edge, linewidths=lw, zorder=z))

    m = 40 * k
    add([[(-m, -m, 0), (W + m, -m, 0), (W + m, D + m, 0), (-m, D + m, 0)]], COLOURS["ground"], "none", z=1)
    add([[(0, 0, 0), (W, 0, 0), (W, D, 0), (0, D, 0)]], COLOURS["plate"], COLOURS["plate_edge"], lw=0.8, z=2)
    bodies = element_bodies(spec) + [person_body(person_xy[0], person_xy[1], k, cam, s)]
    order = []
    for layer in sorted({b[3] for b in bodies}):
        idx = [i for i, b in enumerate(bodies) if b[3] == layer]
        order += [idx[j] for j in paint_order([bodies[i][0] for i in idx], cam.eye, tol)]
    for z, i in enumerate(order, start=10):
        _, polys, key, _ = bodies[i]
        faces = sorted(polys, key=lambda p: -sum((sum(v[d] for v in p) / len(p) - cam.eye[d]) ** 2 for d in range(3)))
        add(faces, COLOURS[key], "none" if key == "person" else COLOURS["edge"], z=z)
    fig.savefig(path, dpi=100, facecolor=COLOURS["bg"])
    plt.close(fig)


def massing(spec, out, views=("hero", "front"), size=(1536, 1024), th=None):
    """Draw OUTBASE-<view>.png for each view; returns the written paths."""
    folder = os.path.dirname(out)
    if folder:
        os.makedirs(folder, exist_ok=True)
    paths = []
    for view in views:
        path = f"{out}-{view}.png"
        draw_view(spec, view, size, path, th)
        paths.append(path)
    print("Massing views written: " + ", ".join(paths))
    return paths


def _report_input(findings):
    for f in findings:
        print(f"{'ERROR':<7} {f.code:<18} {f.where}: {f.message}", file=sys.stderr)
    return 2


def _project(arg):
    """The project for --project P, or for "." when ./brief/ exists, else None (standalone)."""
    if arg is not None:
        return common.find_project(arg)
    if os.path.isdir("brief"):
        return common.find_project(".")
    return None


def _build_parser():
    ap = argparse.ArgumentParser(description="Booth geometry: check, massing, hints, facts")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, help_):
        p = sub.add_parser(name, help=help_, description=help_)
        p.add_argument("spec", metavar="SPEC", help="geometry.json")
        p.add_argument("--project", default=None, help="project folder (default: . when ./brief/ exists)")
        return p

    p = add("check", "findings (GEO-*) and a PASS / FAIL result")
    p.add_argument("--json", action="store_true", help="print the findings as JSON")
    p = add("massing", "white scaled model images (internal use only)")
    p.add_argument("out", metavar="OUTBASE", help="output basename: OUTBASE-<view>.png")
    p.add_argument("--views", default="hero,front", help="hero, front or both (comma separated)")
    p.add_argument("--size", default="1536x1024", help="image size in pixels, WxH")
    add("hints", "each element's render_hint")
    add("facts", "sizes, highest point, zones and program as JSON")
    return ap, sub.choices["massing"]


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    ap, mp = _build_parser()
    a = ap.parse_args(argv)
    views, size = (), None
    if a.cmd == "massing":
        views = [v.strip() for v in a.views.split(",") if v.strip()]
        if not views or any(v not in ("hero", "front") for v in views):
            mp.error("--views takes hero, front or hero,front")
        parts = a.size.lower().split("x")
        if len(parts) != 2 or not all(p.isdigit() and int(p) > 0 for p in parts):
            mp.error("--size must look like 1536x1024")
        size = (int(parts[0]), int(parts[1]))
    try:
        spec, found = load_spec(a.spec)
        if found:
            return _report_input(found)
        project = _project(a.project) if a.cmd in ("check", "massing") else None
        th = project.thresholds if project else dict(common.DEFAULTS)
        if a.cmd == "check":
            return check(spec, th, [], a.json)
        if a.cmd == "hints":
            hints(spec)
            return 0
        if a.cmd == "facts":
            print(json.dumps(facts(spec), ensure_ascii=False, indent=2))
            return 0
        concept = common.concept_of_path(project, a.spec) if project else None
        paths = massing(spec, a.out, views, size, th)
        if project is None:
            print(f"warning: {a.out}: no project found – sidecar not written", file=sys.stderr)
        elif concept is None:
            print(f"warning: {a.out}: spec is not inside a concept folder – sidecar not written", file=sys.stderr)
        else:
            for path in paths:
                common.write_sidecar(path, {
                    "tool": "booth_geometry.py", "mode": "massing", "set": concept.set, "concept": concept.id,
                    "inputs": [{"role": "spec", "path": project.rel(a.spec), "sha256": common.sha256_file(a.spec)}],
                    "prompt_sha256": None, "lint": None})
        return 0
    except InputError as e:
        print(f"{'ERROR':<7} {e.code:<18} {e.where}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
