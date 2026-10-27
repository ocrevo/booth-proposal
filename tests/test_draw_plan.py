"""draw_plan.py: files and sidecar, subtitle, title, label avoidance, zone numbers, language, accent, UTF-8, legend."""
import copy
import json
import os
import re
import subprocess
import sys

import pytest

import booth_geometry
import common
import draw_plan

SCRIPT = os.path.join(str(common.SKILL_DIR), "scripts", "draw_plan.py")
CH = common.load_labels("en")["chrome"]
FONT = (None, True)


def ostara(**extra):
    spec = {"title": "A · Roastery Gate", "width": 8, "depth": 6, "max_height": 4.5, "unit": "m",
            "open_sides": ["front", "right"],
            "elements": [
                {"id": "X1", "shape": "extrusion", "label": "Roastery arch", "kind": "hero", "x": 0, "y": 2, "w": 3,
                 "h": 0.2, "profile": [[0, 0], [1.5, 4.2], [3, 0]], "support": "floor"},
                {"label": "Tasting bar", "x": 4, "y": 1, "w": 2, "h": 0.8, "height": 1.1},
                {"label": "Tasting bar", "x": 4, "y": 3, "w": 2, "h": 0.8, "height": 1.1}]}
    spec.update(extra)
    return spec


def in_feet(spec):
    f = common.unit_factor("ft")
    out = copy.deepcopy(spec)
    out["unit"] = "ft"
    for key in ("width", "depth", "max_height"):
        out[key] = out[key] * f
    for e in out["elements"]:
        for key in ("x", "y", "w", "h", "height"):
            if key in e:
                e[key] = e[key] * f
        if "profile" in e:
            e["profile"] = [[d * f, z * f] for d, z in e["profile"]]
    return out


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def run(*args, cwd=None, env=None):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    return subprocess.run([sys.executable, SCRIPT, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd, env=env)


def facts_of(spec):
    return booth_geometry.facts(common.normalise_geometry(copy.deepcopy(spec)))


def draw_args(**kw):
    args = dict(chrome=CH, units="m", title="T", sub="S", colours=draw_plan.plan_colours({}),
                accent="#1F5FAE", font=FONT)
    args.update(kw)
    return args


def test_plan_files_and_sidecar(project):
    spec = write(project / "concepts" / "set-1" / "A" / "geometry.json", ostara())
    r = run("plan", spec, spec.parent / "plan", "--project", project)
    assert r.returncode == 0, r.stdout + r.stderr
    folder = spec.parent
    for name in ("plan.png", "plan.svg", "plan.json"):
        assert (folder / name).is_file()
    side = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    assert side["schema"] == "sidecar/2" and side["tool"] == "draw_plan.py" and side["mode"] == "plan"
    assert (side["set"], side["concept"]) == ("set-1", "A")
    assert side["inputs"] == [{"role": "spec", "path": "concepts/set-1/A/geometry.json",
                               "sha256": common.sha256_file(str(spec))}]
    assert side["outputs"] == {"plan.png": common.sha256_file(str(folder / "plan.png")),
                               "plan.svg": common.sha256_file(str(folder / "plan.svg"))}


SUB_EN = "Size 8 × 6 m · Open sides front, right · Highest point 4.2 m"


@pytest.mark.parametrize("case", ["m", "ft", "ft_spec_in_m", "spec_subtitle", "cli_spec_subtitle"])
def test_subtitle(case, tmp_path, monkeypatch, capsys):
    spec = ostara()
    units = "m"
    if case == "ft":
        units = "ft"
    elif case == "ft_spec_in_m":
        spec = in_feet(spec)
    elif case in ("spec_subtitle", "cli_spec_subtitle"):
        spec["subtitle"] = "from renders/hero-v1.png (19.7 x 9.8 ft)"
    if case == "cli_spec_subtitle":
        # the whole CLI run; the SVG keeps its text as text (not outlines) so that it can be searched
        monkeypatch.setitem(draw_plan.matplotlib.rcParams, "svg.fonttype", "none")
        monkeypatch.chdir(tmp_path)
        write(tmp_path / "geometry.json", spec)
        assert draw_plan.main(["plan", "geometry.json", "out"]) == 0
        capsys.readouterr()
        svg = (tmp_path / "out.svg").read_text(encoding="utf-8")
        text = " ".join(re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S))
        assert "Size 8" in text and "Open sides front, right" in text and "Roastery Gate" in text
        assert not any(w in text for w in ("renders", ".png", "hero-v1", "from renders", "19.7 x 9.8"))
        assert not re.search(r"ft", text)
        return
    text = draw_plan.subtitle(facts_of(spec), CH, units)
    if case in ("m", "ft_spec_in_m"):
        assert text == SUB_EN
    elif case == "ft":
        assert "26.2 × 19.7 ft" in text and "13.8 ft" in text and " m" not in text
    else:
        assert text == SUB_EN
        assert not any(w in text for w in ("renders", ".png", "(", "ft"))


@pytest.mark.parametrize("fn, given, want", [
    (draw_plan.clean_title, "A · Harbour Gate · from concepts/set-1/A/renders/hero-v2.png",
     "A · Harbour Gate"),
    (draw_plan.clean_title, "B · Quay built from brief/notes.md", "B · Quay"),
    (draw_plan.strip_id, "A · Harbour Gate", "Harbour Gate"),
    (draw_plan.strip_id, "B: Quay", "Quay"),
    (draw_plan.strip_id, "Harbour Gate", "Harbour Gate"),
    (draw_plan.strip_id, "Pop-up Roastery", "Pop-up Roastery"),
    (draw_plan.strip_id, "Sky-high Lounge", "Sky-high Lounge"),
    (draw_plan.strip_id, "3-D Gate", "3-D Gate"),
    (draw_plan.strip_id, "B - Quay", "Quay"),
])
def test_title(fn, given, want):
    assert fn(given) == want


def _hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_labels_do_not_collide(tmp_path):
    names = ["Tasting bar", "Cold brew taps", "Retail shelf", "Grinder demo", "Staff"]
    spec = {"width": 8, "depth": 6, "max_height": 4.5, "unit": "m", "open_sides": ["front", "right"],
            "elements": [{"label": n, "x": 0.5 + 0.7 * i, "y": 2, "w": 0.6, "h": 0.4, "height": 1}
                         for i, n in enumerate(names)]}
    result = draw_plan.draw(common.normalise_geometry(spec), str(tmp_path / "plan"), **draw_args())
    boxes = result["boxes"]
    assert len(boxes) == 5
    assert not any(_hit(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1:])


def _leader_problems(result):
    """Leaders that cross a label box other than their own, or another leader."""
    bad = []
    leaders, boxes = result["leaders"], result["boxes"]
    for lv in leaders:
        for j, box in enumerate(boxes):
            if j != lv["label"] and draw_plan._seg_hits_box(lv["seg"][0], lv["seg"][1], box):
                bad.append(("box", lv["label"], j))
    for i, a in enumerate(leaders):
        for b in leaders[i + 1:]:
            if draw_plan._segs_cross(*a["seg"], *b["seg"]):
                bad.append(("leader", a["label"], b["label"]))
    return bad


def test_long_labels_leaders(tmp_path):
    names = ["Tasting bar and cupping table", "Cold brew tap wall", "Retail shelf and gift packs",
             "Grinder demonstration", "Staff station and storage", "Seating lounge", "Roastery theatre",
             "Sample wall"]
    spec = {"width": 8, "depth": 6, "max_height": 4.5, "unit": "m", "open_sides": ["front", "right"],
            "elements": [{"label": n, "x": 0.6 + 1.1 * (i % 4), "y": 4.0 + 1.0 * (i // 4), "w": 0.9, "h": 0.6,
                          "height": 1} for i, n in enumerate(names)]}
    result = draw_plan.draw(common.normalise_geometry(spec), str(tmp_path / "plan"), **draw_args())
    assert result["leaders"], "the spec is meant to crowd the labels"
    assert _leader_problems(result) == []
    assert result["max_leader"] <= result["leader_cap"]
    boxes = result["boxes"]
    assert not any(_hit(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1:])


def test_legible_and_cropped(tmp_path):
    from PIL import Image
    spec = ostara()
    spec["elements"][1]["label"] = "Tasting bar"
    result = draw_plan.draw(common.normalise_geometry(spec), str(tmp_path / "plan"), **draw_args(title="Roastery Gate"))
    img = Image.open(tmp_path / "plan.png").convert("RGB")
    assert abs(img.width - result["width_px"]) <= 2
    assert result["label_rel"] >= 0.012              # a zone label line is at least 1.2% of the image width tall
    bg = img.getpixel((0, 0))
    px = img.load()
    xs = [x for x in range(0, img.width, 4) for y in range(0, img.height, 4) if px[x, y] != bg]
    ys = [y for x in range(0, img.width, 4) for y in range(0, img.height, 4) if px[x, y] != bg]
    pad = 0.2 * draw_plan.SAVE_DPI + 12              # the saved crop pad (in) in pixels, plus a margin for rounding
    assert min(xs) <= pad and min(ys) <= pad
    assert img.width - max(xs) <= pad and img.height - max(ys) <= pad


def test_zone_numbers(tmp_path):
    spec = ostara()
    spec["elements"].append({"label": "Fins", "x": 0.5, "y": 4, "w": 0.1, "h": 1, "height": 2,
                             "repeat": {"count": 5, "dx": 0.3}})
    norm = common.normalise_geometry(spec)
    result = draw_plan.draw(norm, str(tmp_path / "plan"), **draw_args())
    assert result["numbers"] == {"Roastery arch": 1, "Tasting bar": 2, "Fins": 3}
    assert result["numbers"] == common.zone_numbers(norm["elements"])
    assert len(result["boxes"]) == 4        # arch, two bars, and one box for the five fins


@pytest.mark.parametrize("case", ["project_zh", "arg_en", "standalone_en", "standalone_cjk", "unknown"])
def test_lang(case, make_project, tmp_path):
    if case == "unknown":
        spec = write(tmp_path / "s" / "geometry.json", ostara())
        r = run("plan", "geometry.json", "plan", "--lang", "xx", cwd=spec.parent)
        assert r.returncode == 2 and "C-INPUT" in r.stderr
        return
    spec = ostara()
    if case in ("project_zh", "arg_en"):
        project = common.find_project(str(make_project(lang="zh")))
        arg = "en" if case == "arg_en" else None
        assert draw_plan.resolve_lang(arg, project, spec) == ("en" if arg else "zh")
    elif case == "standalone_en":
        assert draw_plan.resolve_lang(None, None, spec) == "en"
    else:
        spec["elements"][0]["label"] = "咨询台"
        assert draw_plan.resolve_lang(None, None, spec) == "zh"


def test_accent_precedence():
    fm, sp, st = {"accent": "#111111"}, {"accent": "#222222"}, {"colors": {"accent": "#333333"}}
    assert draw_plan.resolve_accent(fm, sp, st) == "#111111"
    assert draw_plan.resolve_accent({}, sp, st) == "#222222"
    assert draw_plan.resolve_accent({}, {}, st) == "#333333"
    assert draw_plan.resolve_accent({}, {}, {}) == "#1F5FAE"


def test_stdout_utf8_cjk_path(tmp_path):
    spec = write(tmp_path / "geometry.json", ostara())
    folder = "方案 A"
    r = run("plan", spec, tmp_path / folder / "plan", cwd=tmp_path, env={"PYTHONIOENCODING": "ascii"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert folder in r.stdout
    assert (tmp_path / folder / "plan.png").is_file()


def test_no_font_legend(tmp_path, monkeypatch, capsys):
    spec = ostara()
    labels = ["咨询台", "试饮区", "展示墙"]
    for e, lab in zip(spec["elements"], labels):
        e["label"] = lab
    result = draw_plan.draw(common.normalise_geometry(copy.deepcopy(spec)), str(tmp_path / "direct"),
                            **draw_args(font=(None, False)))
    assert result["legend"] == [f"{i} {lab}" for i, lab in enumerate(labels, 1)]
    out = capsys.readouterr().out
    assert all(line in out for line in result["legend"])
    monkeypatch.setattr(draw_plan, "pick_font", lambda texts, style: (None, False))
    monkeypatch.chdir(tmp_path)
    write(tmp_path / "geometry.json", spec)
    assert draw_plan.main(["plan", "geometry.json", "cli"]) == 0
    out = capsys.readouterr().out
    assert all(line in out for line in result["legend"])


# ---------- labels and footprints (contract Revision 3.1, items 14-19) ----------

def _foreign_boxes(result, label):
    """Display footprints of every element except the owner of `label`."""
    own = result["owners"][label]
    return [b for eid, boxes in result["footprints"].items() if eid != own for b in boxes]


def _check_labels_on_footprints(result, skip_boxes=()):
    """Every leader starts on its own footprint (an edge midpoint or the centre, never a corner), crosses no other
    element's footprint and is no longer than the cap; a label without a leader has its number disc inside its own
    footprint; no label box covers another element's footprint (labels in `skip_boxes` excepted)."""
    leaders = {lv["label"]: lv for lv in result["leaders"]}
    for i, box in enumerate(result["boxes"]):
        own = result["footprints"][result["owners"][i]]
        foreign = _foreign_boxes(result, i)
        if i in leaders:
            lv = leaders[i]
            a, b = lv["seg"]
            assert lv["length"] <= result["leader_cap"] + 1e-9
            assert not any(draw_plan._seg_hits_box(a, b, f) for f in foreign), f"leader {i} crosses a footprint"
            on = [f for f in own if f[0] - 1 <= a[0] <= f[2] + 1 and f[1] - 1 <= a[1] <= f[3] + 1]
            assert on, f"leader {i} does not start on its own footprint"
            f = on[0]
            mid_x, mid_y = (f[0] + f[2]) / 2, (f[1] + f[3]) / 2
            at_edge_mid = (abs(a[0] - mid_x) < 1.5 and (abs(a[1] - f[1]) < 1.5 or abs(a[1] - f[3]) < 1.5)
                           or abs(a[1] - mid_y) < 1.5 and (abs(a[0] - f[0]) < 1.5 or abs(a[0] - f[2]) < 1.5))
            at_centre = abs(a[0] - mid_x) < 1.5 and abs(a[1] - mid_y) < 1.5
            assert at_edge_mid or at_centre, f"leader {i} is anchored at a corner or off-centre"
        else:
            disc = result["discs"][i]
            assert any(draw_plan._inside(disc, f) for f in own), f"disc {i} is not inside its own footprint"
        if i not in skip_boxes:
            inner = (box[0] + 1.5, box[1] + 1.5, box[2] - 1.5, box[3] - 1.5)     # _bb pads every box by 1.5 px
            assert not any(_hit(inner, f) for f in foreign), f"label {i} covers another element's footprint"


def _tight_spec():
    """12 elements with long labels in two rows of six, 0.2 m apart, in an 8 x 6 m stand."""
    names = ["Espresso tasting bar with cupping table", "Cold brew tap wall and nitro taps",
             "Retail shelf with seasonal gift packs", "Grinder demonstration counter",
             "Staff station with hidden storage", "Seating lounge for buyer meetings",
             "Roastery theatre and live roast", "Sample wall of single origins",
             "Green bean sorting table", "Barista training corner", "Brand story projection wall",
             "Welcome desk and badge scan"]
    return {"width": 8, "depth": 6, "max_height": 4.5, "unit": "m", "open_sides": ["front", "right"],
            "elements": [{"label": n, "x": 0.4 + 1.2 * (i % 6), "y": 2.6 + 1.3 * (i // 6), "w": 1.0, "h": 0.6,
                          "height": 1.1} for i, n in enumerate(names)]}


def test_tight_labels_stay_on_their_own_boxes(tmp_path, capsys):
    result = draw_plan.draw(common.normalise_geometry(_tight_spec()), str(tmp_path / "plan"), **draw_args())
    out = capsys.readouterr().out
    assert len(result["boxes"]) == 12
    assert result["leader_cap"] == pytest.approx(8 / draw_plan.LEADER_CAP_DIV)
    assert result["max_leader"] <= result["leader_cap"]
    assert _leader_problems(result) == []
    _check_labels_on_footprints(result)
    # the labels that fit no spot under the cap are shown by their number and listed in the legend
    assert result["number_only"], "the spec is meant to leave some labels without a spot under the cap"
    assert len(result["legend"]) == len(result["number_only"])
    assert f"{len(result['number_only'])} label(s) shown by number only; see the legend" in out
    assert all(line in out for line in result["legend"])
    for line in result["legend"]:
        n, _, text = line.partition(" ")
        assert result["numbers"][text] == int(n)
    # nothing is silently left on a neighbour's box: every label either has a leader, a number-only disc or an
    # in-place disc inside its own footprint (checked above)
    assert len(result["leaders"]) + len(result["number_only"]) <= 12


def test_ostara_style_plan(tmp_path):
    """A thin screen strip along the back wall, a lounge (circle) and a kiosk, with long labels."""
    spec = {"width": 8, "depth": 6, "max_height": 4.5, "unit": "m", "open_sides": ["front", "right"],
            "elements": [
                {"label": "Brand story projection screen", "kind": "hero", "x": 1, "y": 0.1, "w": 6, "h": 0.15,
                 "height": 3},
                {"label": "Seating lounge for buyer meetings", "x": 1.0, "y": 2.2, "w": 1.6, "h": 1.6,
                 "shape": "cylinder", "height": 0.5},
                {"label": "Welcome kiosk and badge scan", "x": 3.2, "y": 2.4, "w": 0.9, "h": 0.9, "height": 1.1},
                {"label": "Espresso tasting bar", "x": 4.6, "y": 2.2, "w": 2.2, "h": 0.8, "height": 1.1}]}
    result = draw_plan.draw(common.normalise_geometry(spec), str(tmp_path / "plan"), **draw_args())
    # Documented exception: the screen strip (label 0) is only 0.15 m deep. Depending on the font scale its number
    # disc fits or not; when it does not, the label moves (leader) or becomes a bare number whose disc is wider
    # than the strip, and its text or disc may then touch what lies next to the strip. Its own box is therefore not
    # checked for covering a footprint; its leader and every other label are checked as usual.
    _check_labels_on_footprints(result, skip_boxes={0})


def test_stand_fills_the_image(tmp_path):
    for i, (w, d) in enumerate([(6, 3), (4, 4), (8, 6), (9, 6)]):
        spec = {"width": w, "depth": d, "max_height": 4, "unit": "m", "open_sides": ["front"],
                "elements": [{"label": "Tasting bar", "x": 0.5, "y": d / 2 - 0.4, "w": 1.5, "h": 0.8, "height": 1}]}
        result = draw_plan.draw(common.normalise_geometry(spec), str(tmp_path / f"p{i}"), **draw_args())
        assert result["stand_frac"] > 0.55, (w, d, result["stand_frac"])
        assert result["label_rel"] >= 0.0125 * 0.99          # the minimum label height is kept


def test_no_silent_keep_when_nowhere_free(tmp_path):
    """A label that fits nowhere under the cap is not left on a neighbour: number only plus a legend line."""
    spec = _tight_spec()
    result = draw_plan.draw(common.normalise_geometry(spec), str(tmp_path / "plan"), **draw_args())
    for i in result["number_only"]:
        assert any(draw_plan._inside(result["discs"][i], f) for f in result["footprints"][result["owners"][i]])


def _gap(a, b):
    """Distance between two boxes along the axis that separates them (negative when they overlap)."""
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def test_key_drawn_for_number_only_labels(tmp_path, capsys):
    """Labels shown by number only get a key in the image: it is returned as key_box, overlaps nothing, lies inside
    the saved image and holds ink."""
    from PIL import Image
    result = draw_plan.draw(common.normalise_geometry(_tight_spec()), str(tmp_path / "plan"), **draw_args())
    out = capsys.readouterr().out
    assert result["legend"] and result["key"] == result["legend"]
    assert [int(x.split()[0]) for x in result["legend"]] == sorted(int(x.split()[0]) for x in result["legend"])
    assert all(line in out for line in result["legend"])             # the stdout lines stay
    key = result["key_box"]
    assert key is not None
    assert not any(_hit(key, b) for b in result["boxes"]), "the key overlaps a label"
    assert not any(_hit(key, f) for boxes in result["footprints"].values() for f in boxes), "the key overlaps an element"
    assert not any(draw_plan._seg_hits_box(lv["seg"][0], lv["seg"][1], key) for lv in result["leaders"])
    # the key is inside the saved PNG and not blank there
    img = Image.open(tmp_path / "plan.png").convert("RGB")
    x0, y0, x1, y1 = result["crop_in"]
    dpi, scale = draw_plan.LAYOUT_DPI, draw_plan.SAVE_DPI
    left, right = (key[0] / dpi - x0) * scale, (key[2] / dpi - x0) * scale
    top, bottom = (y1 - key[3] / dpi) * scale, (y1 - key[1] / dpi) * scale
    assert 0 <= left < right <= img.width and 0 <= top < bottom <= img.height
    bg = img.getpixel((0, 0))
    px = img.load()
    ink = sum(1 for x in range(int(left), int(right), 3) for y in range(int(top), int(bottom), 3) if px[x, y] != bg)
    assert ink > 50
    svg = (tmp_path / "plan.svg").read_text(encoding="utf-8")
    assert svg.count('<g id="text_') >= len(result["boxes"]) - len(result["number_only"]) + len(result["key"]) // 2


def test_no_key_without_number_only_labels(tmp_path):
    result = draw_plan.draw(common.normalise_geometry(ostara()), str(tmp_path / "plan"), **draw_args())
    assert result["legend"] == [] and result["key_box"] is None and result["key"] == []


def test_labels_keep_a_minimum_gap(tmp_path):
    """Run-051 style: long labels in a bottom row; no two label boxes touch or read as one run."""
    names = ["1 Welcome kiosk", "2 Brand story wall", "3 Tasting bar", "4 Retail shelf", "5 Seating lounge",
             "6 Grinder demonstration"]
    spec = {"width": 8, "depth": 6, "max_height": 4.5, "unit": "m", "open_sides": ["front", "right"],
            "elements": [{"label": n.split(" ", 1)[1], "x": 0.3 + 1.25 * i, "y": 4.6, "w": 1.0, "h": 0.8,
                          "height": 1.1} for i, n in enumerate(names)]}
    for spec_ in (spec, _tight_spec()):
        result = draw_plan.draw(common.normalise_geometry(spec_), str(tmp_path / "plan"), **draw_args())
        line = result["label_rel"] * result["width_in"] * draw_plan.LAYOUT_DPI     # one label line (px)
        boxes = result["boxes"]
        gaps = [_gap(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1:]]
        assert min(gaps) >= 0.3 * line, (min(gaps), line)
