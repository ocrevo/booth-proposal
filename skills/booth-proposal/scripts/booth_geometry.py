"""Booth geometry: check that a concept fits its envelope, and render a scaled white massing model.

The geometry spec (JSON) is the single source of truth for a concept's dimensions. The plan drawing
(draw_plan.py), the geometry check and the massing images all read the same file, so the renders can be
locked to real dimensions.

Usage:
  python booth_geometry.py check   spec.json
  python booth_geometry.py massing spec.json out_basename     -> out_basename-hero.png, out_basename-front.png

Spec:
{
  "title": "A · Rings of Time", "width": 6, "depth": 3, "max_height": 6, "unit": "m",
  "open_sides": ["front", "right"],            # front = main aisle
  "camera_corner": "right",                    # hero view from the front-right (or "left") corner
  "elements": [
    {"id": "Z1", "label": "Counter", "kind": "zone", "shape": "box",
     "x": 3.9, "y": 2.15, "w": 1.8, "h": 0.5, "z": 0, "height": 1.1},
    {"id": "Z2", "label": "Ring 1", "kind": "overhead", "shape": "frame",
     "x": 0, "y": 2.75, "w": 6, "h": 0.12, "height": 4.2, "band": 0.3},
    {"id": "Z3", "label": "Table", "kind": "furniture", "shape": "cylinder",
     "x": 2.35, "y": 1.36, "w": 0.6, "h": 0.6, "height": 0.75}
  ]
}
Coordinates in metres (or feet): x from the left wall as seen from the main aisle, y from the back wall
toward the aisle, z up from the floor. w is the size along x, h the size along y, height along z.
shape: box (default) | cylinder | frame (a portal: two legs and a top beam, "band" thick, spanning w)
       | extrusion (a curved or stepped surface: "profile" is a list of [dx, z] points across the width,
         dx from the element's x, extruded over its depth h; use it for shells, canopies, vaults, steps).
kind: hero | zone | furniture | overhead. "contains": true lets an element enclose others in plan
(for example a canopy over a lounge) without counting as an overlap.

Constraints the check enforces (all optional except width, depth, max_height):
  "unit": "m" or "ft"            thresholds below scale with the unit (0.9 m = 3 ft walkway, 2.1 m = 7 ft headroom)
  "walkway", "headroom"          override the default minimums with the venue's own rules
  "height_zones": [{"y_from": 0, "y_to": 1.5, "max": 1.22, "note": "line of sight"}]
                                 extra height limits by depth band (y from the back wall), e.g. line-of-sight rules
  "rigging_allowed": true/false  from the venue card; null or missing = not confirmed
  "required": ["screen", "counter", "storage", ...]
                                 program items from the brief; each must be served by an element's "program"
Per element:
  "repeat": {"count": 75, "dx": 0.056, "dy": 0, "height_to": 4.2}
                                 a row of identical pieces (fins, steps, columns): count pieces, each moved by dx/dy;
                                 heights run linearly from "height" to "height_to". The whole row must fit, and it is
                                 checked as one block, so count x pitch errors are caught before rendering.
  "program": "counter" or ["counter", "storage"]   which required items it serves
  "support": "floor" | "wall" | "legs" | "columns" | "hung"   required for overhead, frame and extrusion elements
"""
import itertools
import json
import sys

WALKWAY_M = 0.9    # minimum comfortable passage between floor elements, in metres; check local rules
HEADROOM_M = 2.1   # minimum clear height under elements people walk under, in metres
SPAN_M = 1.5       # free span from a single support beyond which structure needs review, in metres
TOL = 0.005


def unit_factor(spec):
    return 3.28084 if spec.get("unit", "m") == "ft" else 1.0


def load(path):
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    spec.setdefault("elements", spec.get("zones", []))
    for i, e in enumerate(spec["elements"], 1):
        e.setdefault("id", f"E{i}")
        e.setdefault("z", 0)
        e.setdefault("shape", "frame" if e.get("kind") == "overhead" and e.get("legs") else "box")
        r = e.get("repeat")
        if r:   # the checked footprint of a row is its bounding box; the single piece is kept for drawing
            r["_from"] = e.get("height", 0)
            e["piece"] = {"w": e["w"], "h": e["h"]}
            e["w"] = (r["count"] - 1) * abs(r.get("dx", 0)) + e["w"]
            e["h"] = (r["count"] - 1) * abs(r.get("dy", 0)) + e["h"]
            e["height"] = max(e.get("height", 0), r.get("height_to", e.get("height", 0)))
    return spec


def pieces(e):
    """Expand a repeated element into its individual pieces (for drawing)."""
    r = e.get("repeat")
    if not r:
        return [e]
    out, n = [], r["count"]
    for i in range(n):
        p = dict(e)
        p.pop("repeat", None)
        p.update(x=e["x"] + i * r.get("dx", 0), y=e["y"] + i * r.get("dy", 0), w=e["piece"]["w"], h=e["piece"]["h"])
        if "height_to" in r:
            p["height"] = r["_from"] + (r["height_to"] - r["_from"]) * (i / (n - 1) if n > 1 else 0)
        out.append(p)
    return out


def on_floor(e):
    return (e["z"] <= TOL and e.get("kind") != "overhead" and e.get("shape") not in ("frame", "extrusion")
            and not e.get("contains"))


def gap(a, b):
    dx = max(b["x"] - (a["x"] + a["w"]), a["x"] - (b["x"] + b["w"]), 0)
    dy = max(b["y"] - (a["y"] + a["h"]), a["y"] - (b["y"] + b["h"]), 0)
    return (dx * dx + dy * dy) ** 0.5, dx, dy


def check(spec):
    W, D, H = spec["width"], spec["depth"], spec.get("max_height")
    k = unit_factor(spec)
    WALKWAY = spec.get("walkway", WALKWAY_M * k)
    HEADROOM = spec.get("headroom", HEADROOM_M * k)
    errors, warnings = [], []
    for e in spec["elements"]:
        name = f'{e["id"]} {e.get("label", "")}'.strip()
        if e["x"] < -TOL or e["y"] < -TOL or e["x"] + e["w"] > W + TOL or e["y"] + e["h"] > D + TOL:
            errors.append(f"{name}: outside the {W} × {D} footprint "
                          f"(x {e['x']}–{e['x'] + e['w']:.2f}, y {e['y']}–{e['y'] + e['h']:.2f})")
        if "height" not in e:
            warnings.append(f"{name}: no height given")
        elif H and e["z"] + e["height"] > H + TOL:
            errors.append(f"{name}: top at {e['z'] + e['height']:.2f} exceeds the {H} height limit")
        if e.get("shape") == "frame" and "height" in e:
            clear = e["height"] - e.get("band", 0.3)
            if clear < HEADROOM:
                errors.append(f"{name}: clear opening {clear:.2f} is below {HEADROOM} headroom")
        if e.get("shape") == "extrusion":
            prof = e.get("profile", [])
            if prof and (max(p[0] for p in prof) > e["w"] + TOL or min(p[0] for p in prof) < -TOL):
                errors.append(f"{name}: profile runs outside its width {e['w']}")
            if prof and H and max(p[1] for p in prof) > H + TOL:
                errors.append(f"{name}: profile rises above the {H} height limit")
        if e.get("kind") == "overhead" and e.get("shape") not in ("frame", "extrusion") and e["z"] < HEADROOM - TOL:
            warnings.append(f"{name}: underside at {e['z']:.2f}, below {HEADROOM} headroom")
        top_e = e["z"] + e.get("height", 0)
        for zone in spec.get("height_zones", []):
            if e["y"] < zone["y_to"] - TOL and e["y"] + e["h"] > zone["y_from"] + TOL and top_e > zone["max"] + TOL:
                errors.append(f"{name}: top at {top_e:.2f} exceeds {zone['max']} in the band y {zone['y_from']}–{zone['y_to']}"
                              + (f" ({zone['note']})" if zone.get("note") else ""))
        structural = e.get("kind") == "overhead" or e.get("shape") in ("frame", "extrusion")
        if structural:
            support = e.get("support")
            if not support:
                warnings.append(f"{name}: state how it is supported (floor, wall, legs, columns or hung)")
            elif support == "hung":
                if spec.get("rigging_allowed") is False:
                    errors.append(f"{name}: hung, but the venue does not allow rigging")
                elif spec.get("rigging_allowed") is None:
                    warnings.append(f"{name}: hung, but rigging is not confirmed by the venue")
            elif support == "wall" and e["w"] > SPAN_M * k + TOL:
                warnings.append(f"{name}: spans {e['w']:.2f} from a single wall; add columns or have the structure reviewed")
    floor = [e for e in spec["elements"] if on_floor(e)]
    legs = []
    for e in spec["elements"]:
        if e.get("shape") == "frame":
            band = e.get("band", 0.3)
            for side, lx in (("left leg", e["x"]), ("right leg", e["x"] + e["w"] - band)):
                legs.append({"id": f'{e["id"]} {side}', "x": lx, "y": e["y"], "w": band, "h": e["h"], "leg": True})
    for a, b in itertools.combinations(floor + legs, 2):
        d, dx, dy = gap(a, b)
        if a.get("leg") or b.get("leg"):
            ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            if ox > TOL and oy > TOL and not (a.get("leg") and b.get("leg")):
                errors.append(f"{a['id']} and {b['id']} overlap on the floor")
            continue
        if dx <= TOL and dy <= TOL:
            overlap_x = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            overlap_y = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            if overlap_x > TOL and overlap_y > TOL:
                errors.append(f"{a['id']} and {b['id']} overlap on the floor")
        elif d < WALKWAY - TOL:
            warnings.append(f"{a['id']} and {b['id']}: only {d:.2f} apart (walkway guide {WALKWAY})")
    served = set()
    for e in spec["elements"]:
        p = e.get("program", [])
        served.update([p] if isinstance(p, str) else p)
    for item in spec.get("required", []):
        if item not in served:
            errors.append(f"required program item '{item}' is not served by any element")
    used = sum(e["w"] * e["h"] for e in floor)
    print(f"GEOMETRY CHECK · {spec.get('title', '')} · {W} × {D}, max height {H}")
    print(f"Floor elements cover {used:.1f} of {W * D:.1f} ({used / (W * D):.0%}); "
          f"walkway {WALKWAY:.2f}, headroom {HEADROOM:.2f} {spec.get('unit', 'm')}")
    for m in errors:
        print("ERROR  ", m)
    for m in warnings:
        print("WARNING", m)
    print("RESULT: PASS" if not errors else "RESULT: FAIL – fix the design before rendering")
    return not errors


# ---------- massing ----------

def boxes(e):
    """Return the element as a list of (x0, y0, z0, x1, y1, z1) boxes or a cylinder marker."""
    x, y, z, w, h = e["x"], e["y"], e["z"], e["w"], e["h"]
    t = e.get("height", 0.05)
    if e.get("shape") == "frame":
        b = e.get("band", 0.3)
        return [(x, y, z, x + b, y + h, z + t), (x + w - b, y, z, x + w, y + h, z + t),
                (x, y, z + t - b, x + w, y + h, z + t)]
    return [(x, y, z, x + w, y + h, z + t)]


def massing(spec, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    W, D = spec["width"], spec["depth"]
    k = unit_factor(spec)
    top = max(e["z"] + e.get("height", 0) for e in spec["elements"])
    right = spec.get("camera_corner", "right") == "right"

    def faces(b):
        x0, y0, z0, x1, y1, z1 = b
        Y0, Y1 = D - y0, D - y1          # flip: back wall at Y = D, aisle at Y = 0, camera on the aisle side
        p = [(x0, Y0, z0), (x1, Y0, z0), (x1, Y1, z0), (x0, Y1, z0),
             (x0, Y0, z1), (x1, Y0, z1), (x1, Y1, z1), (x0, Y1, z1)]
        idx = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]
        return [[p[i] for i in f] for f in idx]

    def cylinder(e, n=28):
        cx, cy = e["x"] + e["w"] / 2, D - (e["y"] + e["h"] / 2)
        r, z0, z1 = e["w"] / 2, e["z"], e["z"] + e.get("height", 0.75)
        a = np.linspace(0, 2 * np.pi, n + 1)
        side = [[(cx + r * np.cos(a[i]), cy + r * np.sin(a[i]), z0), (cx + r * np.cos(a[i + 1]), cy + r * np.sin(a[i + 1]), z0),
                 (cx + r * np.cos(a[i + 1]), cy + r * np.sin(a[i + 1]), z1), (cx + r * np.cos(a[i]), cy + r * np.sin(a[i]), z1)]
                for i in range(n)]
        lid = [[(cx + r * np.cos(t), cy + r * np.sin(t), z1) for t in a]]
        return side + lid

    views = {"hero": (8, -58 if right else -122), "front": (5, -90)}
    for name, (elev, azim) in views.items():
        fig = plt.figure(figsize=(12, 7.5), dpi=160)
        ax = fig.add_subplot(projection="3d", computed_zorder=False)
        ax.set_proj_type("persp", focal_length=1.4)
        el, az = np.radians(elev), np.radians(azim)
        cam = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        centre = np.array([W / 2, D / 2, 1.0])

        def depth(poly):
            return float(np.dot(np.mean(np.array(poly), axis=0) - centre, cam))

        m = 2.0 * k
        ax.add_collection3d(Poly3DCollection([[(-m, -m * 2.5, 0), (W + m, -m * 2.5, 0), (W + m, D + m, 0), (-m, D + m, 0)]],
                                             facecolor="#E9E9E6", edgecolor="none", zorder=0))
        ax.add_collection3d(Poly3DCollection([[(0, 0, 0), (W, 0, 0), (W, D, 0), (0, D, 0)]],
                                             facecolor="#F7F7F5", edgecolor="#9A9A96", linewidths=0.8, zorder=1))
        items = []
        sides = {"back": [(0, D), (W, D)], "left": [(0, 0), (0, D)], "right": [(W, 0), (W, D)]}
        wall_h = spec.get("wall_height", 0)
        for s, ((ax0, ay0), (ax1, ay1)) in sides.items():
            if s not in spec.get("open_sides", []) and wall_h:
                items.append(([(ax0, ay0, 0), (ax1, ay1, 0), (ax1, ay1, wall_h), (ax0, ay0, wall_h)], "#FFFFFF", "#B5B5B0"))
        for e in [p for el in spec["elements"] for p in pieces(el)]:
            shade = "#DCE3EE" if e.get("kind") == "hero" or e.get("shape") == "frame" else "#FFFFFF"
            if e.get("shape") == "cylinder":
                polys = cylinder(e)
            elif e.get("shape") == "extrusion":
                prof = e.get("profile", [])
                ya, yb = D - e["y"], D - (e["y"] + e["h"])
                polys = [[(e["x"] + p0[0], ya, p0[1]), (e["x"] + p1[0], ya, p1[1]),
                          (e["x"] + p1[0], yb, p1[1]), (e["x"] + p0[0], yb, p0[1])]
                         for p0, p1 in zip(prof, prof[1:])]
            else:
                polys = [f for b in boxes(e) for f in faces(b)]
            items += [(f, shade, "#8E8E8A") for f in polys]
        # a 1.75 m person for scale, standing in the aisle
        px, py = (W - 0.5 * k, -0.8 * k) if (right and name == "hero") else ((0.5 * k, -0.8 * k) if name == "hero" else (W / 2 + 1.4 * k, -0.9 * k))
        a = np.linspace(0, 2 * np.pi, 20)
        for i in range(19):
            items.append(([(px + 0.18 * k * np.cos(a[i]), py + 0.12 * k * np.sin(a[i]), 0), (px + 0.18 * k * np.cos(a[i + 1]), py + 0.12 * k * np.sin(a[i + 1]), 0),
                           (px + 0.18 * k * np.cos(a[i + 1]), py + 0.12 * k * np.sin(a[i + 1]), 1.5 * k), (px + 0.18 * k * np.cos(a[i]), py + 0.12 * k * np.sin(a[i]), 1.5 * k)],
                          "#BDBDB8", "none"))
        head = [(px + 0.11 * k * np.cos(t), py, 1.63 * k + 0.11 * k * np.sin(t)) for t in a]
        items.append((head, "#BDBDB8", "none"))
        for order, (poly, face, edge) in enumerate(sorted(items, key=lambda it: depth(it[0]))):
            ax.add_collection3d(Poly3DCollection([poly], facecolor=face, edgecolor=edge, linewidths=0.5, zorder=2 + order))
        ax.set_xlim(-0.8 * k, W + 0.8 * k)
        ax.set_ylim(-1.6 * k, D + 0.4 * k)
        ax.set_zlim(0, max(top, 3 * k) + 0.3 * k)
        ax.set_box_aspect((W + 1.6 * k, D + 2.0 * k, max(top, 3 * k) + 0.3 * k))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        fig.patch.set_facecolor("#F3F3F1")
        fig.savefig(f"{out}-{name}.png", bbox_inches="tight", facecolor="#F3F3F1", pad_inches=0.05)
        plt.close(fig)
    print(f"Massing views written: {out}-hero.png, {out}-front.png")


if __name__ == "__main__":
    cmd, path = sys.argv[1], sys.argv[2]
    s = load(path)
    if cmd == "check":
        sys.exit(0 if check(s) else 1)
    elif cmd == "massing":
        massing(s, sys.argv[3])
    else:
        sys.exit("usage: booth_geometry.py check|massing spec.json [out_basename]")
