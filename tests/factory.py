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
    """Write hero-v1/v2 through the real render.generate -> call -> save with the network replaced."""
    renders_rel = f"concepts/{concept_key}/renders"
    argv = ["hero", "--prompt", prompt_rel, "--out-dir", renders_rel, "--n", "2"]
    for r in refs:
        argv += ["--ref", r]

    def no_network(*a, **k):
        raise AssertionError("network")

    with contextlib.chdir(root), \
            mock.patch.object(render, "send", fake_send), \
            mock.patch("urllib.request.urlopen", side_effect=no_network), \
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-not-real"}), \
            contextlib.redirect_stdout(io.StringIO()):
        render.main(argv)


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
