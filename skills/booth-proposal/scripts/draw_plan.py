"""Draw a booth floor plan in the style of an architectural presentation drawing.

Usage:  python draw_plan.py spec.json out_basename
Writes out_basename.png and out_basename.svg.

It reads the same geometry spec as booth_geometry.py, unchanged (key "elements"; the older key "zones" also works).
Elements with shape "frame" are drawn as overhead portals with their legs; shape "cylinder" (or "circle") as a
circle; a "repeat" row piece by piece with one label; everything else, extrusions included, by its footprint.

Spec (only the keys the plan uses):
{
  "title": "A · Rings of Time",
  "subtitle": "6 m × 3 m · open front and right",
  "width": 6, "depth": 3, "unit": "m",
  "open_sides": ["front", "right"],
  "accent": "#1F5FAE",
  "elements": [
    {"label": "Hero portal", "x": 0, "y": 2.4, "w": 6, "h": 0.6, "kind": "hero"},
    {"label": "Lounge", "x": 2.4, "y": 1.0, "w": 1.0, "h": 1.0, "kind": "furniture", "shape": "cylinder"}
  ]
}
Coordinates: x from the left wall, y from the back wall toward the main aisle (front).
kind: "hero" (tinted in the accent colour), "zone" (light tone), "furniture" and any other kind (outline only),
"overhead" (dashed accent outline, the drawing convention for elements above head height;
add "legs": true to mark where it touches the floor at both ends).
Optional "label_pos": "top" puts a zone's label near its top edge, for a zone that contains others.
Closed sides are drawn as thick walls, open sides dashed, with the aisle marked. With Chinese labels and no CJK
font installed, elements are numbered and the legend is printed.
"""
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

PAPER, INK, MUTED, ZONE = "#FAF8F4", "#23262B", "#8C9097", "#ECE8E1"
CJK_HINTS = ("Noto Sans CJK", "Noto Sans SC", "Source Han Sans", "PingFang", "Microsoft YaHei",
             "SimHei", "WenQuanYi", "Hiragino Sans")


def has_cjk(text):
    return any("\u3000" <= c <= "\u9fff" or "\uff00" <= c <= "\uffef" for c in text)


def pick_font(spec):
    text = spec.get("title", "") + spec.get("subtitle", "") + "".join(z.get("label", "") for z in spec["zones"])
    if not has_cjk(text):
        return None, True
    for f in font_manager.fontManager.ttflist:
        if any(h.lower() in f.name.lower() for h in CJK_HINTS):
            return f.name, True
    return None, False


def draw(spec, out):
    spec.setdefault("zones", spec.get("elements", []))
    for z in spec["zones"]:
        if z.get("shape") == "frame":
            z["kind"], z["legs"] = "overhead", True
        z.setdefault("label", "")
    W, D = spec["width"], spec["depth"]
    k = 3.28084 if spec.get("unit", "m") == "ft" else 1.0
    accent = spec.get("accent", "#1F5FAE")
    font, ok = pick_font(spec)
    if font:
        plt.rcParams["font.family"] = font
    fig, ax = plt.subplots(figsize=(W / k * 1.5 + 1.6, D / k * 1.5 + 2.0), dpi=220)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)

    expanded = []
    for z in spec["zones"]:
        r = z.get("repeat")
        if not r:
            expanded.append(z)
            continue
        for i in range(r["count"]):
            p = dict(z, x=z["x"] + i * r.get("dx", 0), y=z["y"] + i * r.get("dy", 0), label="")
            p.pop("repeat")
            expanded.append(p)
        n = r["count"]
        expanded.append({"label": z.get("label", ""), "x": z["x"], "y": z["y"],
                         "w": (n - 1) * abs(r.get("dx", 0)) + z["w"], "h": (n - 1) * abs(r.get("dy", 0)) + z["h"],
                         "kind": "furniture", "label_only": True})
    spec["zones"] = expanded

    legend = []
    for i, z in enumerate(spec["zones"], 1):
        if z.get("label_only"):
            ax.text(z["x"] + z["w"] / 2, z["y"] + z["h"] + 0.18 * k, z["label"], ha="center", va="top",
                    fontsize=7.5, color=INK, fontweight="bold")
            continue
        kind = z.get("kind", "zone")
        face = {"hero": accent, "zone": ZONE}.get(kind, "none")
        alpha = 0.22 if kind == "hero" else 1
        edge = accent if kind == "hero" else INK
        lw = 1.4 if kind == "hero" else 0.8
        if kind == "overhead":
            ax.add_patch(Rectangle((z["x"], z["y"]), z["w"], z["h"], fill=False, edgecolor=accent,
                                   lw=1.0, ls=(0, (3, 2))))
            if z.get("legs"):
                leg = z.get("band", 0.12 * k)
                for lx in (z["x"], z["x"] + z["w"] - leg):
                    ax.add_patch(Rectangle((lx, z["y"]), leg, z["h"], facecolor=accent, edgecolor="none"))
        elif z.get("shape") in ("circle", "cylinder"):
            patch = Circle((z["x"] + z["w"] / 2, z["y"] + z["h"] / 2), min(z["w"], z["h"]) / 2,
                           facecolor=face, alpha=alpha, edgecolor="none")
            ax.add_patch(patch)
            ax.add_patch(Circle(patch.center, patch.radius, fill=False, edgecolor=edge, lw=lw))
        else:
            ax.add_patch(Rectangle((z["x"], z["y"]), z["w"], z["h"], facecolor=face, alpha=alpha, edgecolor="none"))
            ax.add_patch(Rectangle((z["x"], z["y"]), z["w"], z["h"], fill=False, edgecolor=edge, lw=lw))
        label = z["label"] if ok else str(i)
        if not ok:
            legend.append(f"{i} {z['label']}")
        if kind == "overhead":
            ax.text(z["x"] + 0.25 * k, z["y"] - 0.05 * k, label, ha="left", va="bottom", fontsize=6.5, color=accent)
        else:
            ly = z["y"] + 0.22 * k if z.get("label_pos") == "top" else z["y"] + z["h"] / 2
            ax.text(z["x"] + z["w"] / 2, ly, label, ha="center", va="center",
                    fontsize=7.5, color=INK, fontweight="bold" if kind == "hero" else "normal")

    sides = {"back": ((0, W), (0, 0)), "front": ((0, W), (D, D)),
             "left": ((0, 0), (0, D)), "right": ((W, W), (0, D))}
    for name, (xs, ys) in sides.items():
        if name in spec.get("open_sides", []):
            ax.plot(xs, ys, color=MUTED, lw=0.8, ls=(0, (4, 3)))
        else:
            ax.plot(xs, ys, color=INK, lw=4, solid_capstyle="butt")

    cjk = has_cjk(spec.get("title", "") + spec.get("subtitle", ""))
    aisle = "主通道" if cjk else "MAIN AISLE"
    side = "通道" if cjk else "AISLE"
    if "front" in spec.get("open_sides", []):
        ax.annotate("", xy=(W / 2, D + 0.12 * k), xytext=(W / 2, D + 0.7 * k),
                    arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8))
        ax.text(W / 2, D + 0.85 * k, aisle, ha="center", va="top", fontsize=7, color=MUTED)
    if "right" in spec.get("open_sides", []):
        ax.text(W + 0.35 * k, D / 2, side, ha="center", va="center", rotation=90, fontsize=7, color=MUTED)
    if "left" in spec.get("open_sides", []):
        ax.text(-0.35 * k, D / 2, side, ha="center", va="center", rotation=90, fontsize=7, color=MUTED)

    unit = spec.get("unit", "m")
    bar = 5 if unit == "ft" else 1
    ax.plot([0, bar], [-0.45 * k, -0.45 * k], color=INK, lw=1.2)
    ax.text(bar + 0.08 * k, -0.45 * k, f"{bar} {unit}", va="center", fontsize=6.5, color=INK)
    ax.text(0, -1.05 * k, spec.get("title", ""), fontsize=11, fontweight="bold", color=INK, va="bottom")
    ax.text(0, -0.8 * k, spec.get("subtitle", ""), fontsize=7, color=MUTED, va="bottom")
    if legend:
        ax.text(W + 0.7 * k, 0, "\n".join(legend), fontsize=6.5, color=INK, va="top")

    ax.set_xlim(-0.6 * k, W + (2.6 if legend else 0.8) * k)
    ax.set_ylim(D + 1.2 * k, -1.3 * k)
    ax.set_aspect("equal")
    ax.axis("off")
    for ext in ("png", "svg"):
        fig.savefig(f"{out}.{ext}", bbox_inches="tight", facecolor=PAPER, pad_inches=0.25)
    plt.close(fig)
    if not ok:
        print("No CJK font found: zones are numbered on the plan; show this legend next to it:")
        print("\n".join(legend))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        draw(json.load(f), sys.argv[2])
