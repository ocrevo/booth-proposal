"""gates.py renders and gates.py report renders (phase 1, S5). State is built through real render.py calls; the
network is replaced by fake_send, so no call leaves the machine."""
import shutil
from pathlib import Path

import pytest

import common
import factory
import render

A = "concepts/set-1/A"
CHOSEN = f"{A}/renders/hero-v2.png"
FIX_ADD = "Remove the hanging banner; nothing else changes."


@pytest.fixture
def rr(monkeypatch, capsys):
    """rr(root, *args) -> (exit code, stdout, stderr) for render.py; file arguments are relative to root."""
    def go(root, *args):
        monkeypatch.chdir(root)
        capsys.readouterr()
        try:
            code = render.main([*args, "--project", str(root)])
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
        out = capsys.readouterr()
        return code, out.out, out.err
    return go


def set_front_matter(root, key, text):
    (Path(root) / "concepts" / key / "concept.md").write_text(text, encoding="utf-8", newline="\n")


def review(rr, root, image_rel, *, verdict="pass", scope="full"):
    return rr(root, "review", image_rel, "--reviewer", "subagent", "--verdict", verdict, "--premium", "yes",
              "--scope", scope, "--size-json", '{"observed": {"w": 4.6, "d": 3.4, "h": 2.6}}', "--marks-json", "[]")


def reviewed_project(make_project):
    """A project whose set-1/A chosen render has a passing full review."""
    root = make_project()
    factory.review_pass(root, CHOSEN)
    return root


def external(tmp_path, name="ext.png"):
    from PIL import Image
    path = tmp_path / name
    Image.new("RGB", (64, 48), factory._next_rgb()).save(path, "PNG")
    return path


def test_renders_ok(make_project, run_gates):
    root = make_project()
    for key in ("set-1/A", "set-1/B", "set-2/A", "set-2/B"):
        factory.review_pass(root, f"concepts/{key}/renders/hero-v2.png")
    code, out, err = run_gates(root, "renders")
    assert code == 0, out + err
    assert "ERROR" not in out and "RESULT: PASS" in out


CASES = {
    "no-chosen": ("G-RENDER", "nochosen"),
    "chosen-blocked": ("G-RENDER", "blocked"),
    "sidecar-deleted": ("G-RENDER", "sidecar"),
    "image-changed": ("G-RENDER", "sidecar"),
    "chosen-reference-copy": ("G-RENDER", "chain"),
    "import-other-set-ref": ("G-RENDER", "refset"),
    "no-review": ("G-REVIEW", "missing"),
    "stale-review": ("G-REVIEW", "stale"),
    "scope-whole": ("G-REVIEW", "scope"),
    "review-fail": ("G-REVIEW", "fail"),
    "fix-max-plus-one": ("R-FIX-MAX", "fix-max"),
}


@pytest.mark.parametrize("case", list(CASES))
def test_renders_findings(make_project, run_gates, rr, fake_send, has, tmp_path, case):
    root = make_project()
    renders = root / A / "renders"
    chosen = CHOSEN
    reviewed = True
    if case == "no-chosen":
        set_front_matter(root, "set-1/A", "---\n---\nNotes.\n")
    elif case == "chosen-blocked":
        set_front_matter(root, "set-1/A", "---\nchosen: renders/hero-v2.png\nblocked: renders/hero-v2.png\n---\n")
    elif case == "sidecar-deleted":
        (renders / "hero-v2.json").unlink()
    elif case == "image-changed":
        (renders / "hero-v2.png").write_bytes(factory.png_bytes(factory._next_rgb()))
    elif case == "chosen-reference-copy":
        shutil.copyfile(root / "input" / "refs" / "set-1" / "r01.png", renders / "hero-v9.png")
        factory.put_sidecar(root, f"{A}/renders/hero-v9.png", "hero")
        chosen = f"{A}/renders/hero-v9.png"
        set_front_matter(root, "set-1/A", f"---\nchosen: renders/hero-v9.png\n---\n")
    elif case == "import-other-set-ref":
        code, out, err = rr(root, "import", str(external(tmp_path)), "--concept", "set-1/A",
                            "--ref", "input/refs/set-2/r01.png")
        assert code == 0, out + err
        chosen = f"{A}/renders/hero-v3.png"
        set_front_matter(root, "set-1/A", "---\nchosen: renders/hero-v3.png\n---\n")
    elif case == "no-review":
        reviewed = False
    elif case == "fix-max-plus-one":
        base = CHOSEN
        for _ in range(common.DEFAULTS["fix_max"] + 1):
            code, out, err = rr(root, "fix", "--concept", "set-1/A", "--base", base, "--add", FIX_ADD)
            assert code in (0,), out + err
            newest = max((p.name for p in renders.glob("hero-v*.png")), key=lambda n: int(n[6:-4]))
            base = f"{A}/renders/{newest}"
        chosen = base
        set_front_matter(root, "set-1/A", f"---\nchosen: {chosen.split(f'{A}/')[1]}\n---\n")
    if reviewed and case not in ("no-chosen", "chosen-blocked", "sidecar-deleted", "chosen-reference-copy"):
        verdict = "fail" if case == "review-fail" else "pass"
        scope = "whole" if case == "scope-whole" else "full"
        if case != "image-changed":
            code, out, err = review(rr, root, chosen, verdict=verdict, scope=scope)
            assert code == (1 if verdict == "fail" else 0), out + err
    if case == "stale-review":
        data = common.read_json(str(root / A / "renders" / "hero-v2.review.json"))
        data["sha256"] = "0" * 64
        common.write_json(str(root / A / "renders" / "hero-v2.review.json"), data)
    code, out, err = run_gates(root, "renders", "--concept", "set-1/A")
    want_code, rule = CASES[case]
    assert has(out, want_code, rule), out + err
    assert code == (0 if want_code == "R-FIX-MAX" else 1), out + err
    if case == "no-review":
        assert "run render.py review" in out
    if case == "fix-max-plus-one":
        assert "ERROR" not in out


def test_renders_v1_legacy(make_project, run_gates, rr, has):
    root = make_project(legacy=True, renders=False)
    rel = factory.add_render(root, "_legacy/A", "hero-v1.png", mode="hero", version=1, refs=["input/r01.png"])
    set_front_matter(root, "_legacy/A", "---\nchosen: renders/hero-v1.png\n---\n")
    code, out, err = review(rr, root, rel)
    assert code == 0, out + err
    code, out, err = run_gates(root, "renders")
    assert code == 0, out + err
    assert has(out, "C-LEGACY") and "ERROR" not in out


def test_renders_reports_reference_findings(make_project, run_gates, has):
    root = make_project()
    (root / "input" / "refs" / "set-1" / "extra.png").write_bytes(factory.png_bytes(factory._next_rgb()))
    code, out, err = run_gates(root, "renders", "--concept", "set-1/B")
    assert code == 1 and has(out, "G-REFS", "stale"), out + err


def test_renders_options(make_project, run_gates):
    root = make_project()
    code, out, err = run_gates(root, "renders", "--concept", "set-9/Z")
    assert code == 2 and "C-INPUT" in err
    code, out, err = run_gates(root, "renders", "--concept", "set-1/A", "set-1/B", "--json")
    assert code == 1
    data = __import__("json").loads(out)
    assert data["counts"]["error"] == 2 and {f["code"] for f in data["findings"]} == {"G-REVIEW"}
    assert {f["where"].split("/")[2] for f in data["findings"]} == {"A", "B"}


def test_renders_invalid_front_matter_skips_concept(make_project, run_gates, has):
    root = make_project()
    set_front_matter(root, "set-1/A", "---\nchosen: renders/missing.png\n---\n")
    code, out, err = run_gates(root, "renders", "--concept", "set-1/A")
    assert code == 1 and has(out, "G-FM") and not has(out, "G-RENDER") and not has(out, "G-REVIEW")


def test_renders_concept_without_images_is_quiet(make_project, run_gates):
    root = make_project(renders=False)
    code, out, err = run_gates(root, "renders")
    assert code == 0, out + err


def test_report_renders(make_project, run_gates, rr):
    root = make_project()
    factory.review_pass(root, CHOSEN)
    code, out, err = run_gates(root, "report", "renders")
    assert code == 0, out + err
    L = common.load_labels("en")["report"]
    assert out.startswith("# " + L["renders"])
    assert "| concept | image | verdict | chosen |" in out
    section = out.split("## set-1")[1].split("## set-2")[0]
    assert f"| A | hero-v2.png | {L['pass']} (full) | ✓ |" in section
    assert f"| A | hero-v1.png | {L['none']} |  |" in section
    assert section.rstrip().endswith(L["none"])          # no sheet written yet


def test_report_renders_sheets_and_stale_review(make_project, run_gates, rr):
    root = make_project()
    factory.review_pass(root, CHOSEN)
    code, out, err = rr(root, "sheet", "--set", "set-1", "--candidates")
    assert code == 0, out + err
    (root / A / "renders" / "hero-v2.png").write_bytes(factory.png_bytes(factory._next_rgb()))
    code, out, err = run_gates(root, "report", "renders")
    assert code == 0, out + err
    L = common.load_labels("en")["report"]
    section = out.split("## set-1")[1].split("## set-2")[0]
    assert "- work/sheets/set-1-candidates.png" in section
    assert f"| A | hero-v2.png | {L['none']} | ✓ |" in section        # a stale review shows as none


def test_report_renders_lists_chosen_non_candidate(make_project, run_gates, rr):
    """A chosen fix or logo output is not a hero/import candidate; it still gets a row with the check mark."""
    root = make_project()
    factory.review_pass(root, CHOSEN)
    code, out, err = rr(root, "logo", CHOSEN, "--logo", "brief/brand/logo.png", "--quad", "10,8 50,8 50,30 10,30")
    assert code == 0, out + err
    set_front_matter(root, "set-1/A", "---\nchosen: renders/hero-v3.png\n---\n")
    code, out, err = run_gates(root, "report", "renders")
    assert code == 0, out + err
    L = common.load_labels("en")["report"]
    section = out.split("## set-1")[1].split("## set-2")[0]
    assert f"| A | hero-v3.png | {L['pass']} (full) | ✓ |" in section
    assert f"| A | hero-v2.png | {L['pass']} (full) |  |" in section
    assert section.count("hero-v3.png") == 1
