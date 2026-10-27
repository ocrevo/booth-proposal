"""import, review, logo and label of render.py (phase 1, S3). No network: these commands never call the API."""
import json
import shutil
from pathlib import Path

import pytest

import common
import factory
import gates
import render

A = "concepts/set-1/A"
HERO1 = f"{A}/renders/hero-v1.png"
QUAD = "10,8 50,8 50,30 10,30"
OBSERVED = '{"observed": {"w": 4.4, "d": 3.3, "h": 2.5}}'


@pytest.fixture
def run(monkeypatch, capsys):
    """run(root, *args) -> (exit code, stdout, stderr); --project is appended, file arguments are relative to root."""
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


def names(root, rel):
    folder = Path(root) / rel
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def review_args(image, *, marks="[]", size=OBSERVED, premium="yes", verdict="pass", extra=()):
    return ["review", image, "--reviewer", "subagent", "--verdict", verdict, "--premium", premium,
            "--size-json", size, "--marks-json", marks, *extra]


def external(tmp_path, name="ext.png", fmt="PNG"):
    """An image made outside the project, with a colour no other image in the process has."""
    from PIL import Image
    path = tmp_path / name
    Image.new("RGB", (64, 48), factory._next_rgb()).save(path, fmt)
    return path


# ---------- import ----------

@pytest.mark.parametrize("case", ["png", "jpeg", "prompt-lint-fail"])
def test_import_ok(make_project, run, tmp_path, case):
    root = make_project(renders=False)
    if case == "jpeg":
        src, want = external(tmp_path, "ext.jpg", "JPEG"), "hero-v1.jpg"
    else:
        src, want = external(tmp_path), "hero-v1.png"
    args = ["import", str(src), "--concept", "set-1/A"]
    if case == "prompt-lint-fail":
        (root / "bad.txt").write_text(factory.hero_ok().replace("a large screen;", "a 75-inch screen;", 1),
                                      encoding="utf-8")
        args += ["--prompt", "bad.txt"]
    code, out, err = run(root, *args)
    assert code == 0, out + err
    assert "render.py review" in out
    folder = root / A / "renders"
    side = common.read_sidecar(str(folder / want))
    assert common.sidecar_version(side) == 2 and side["mode"] == "import" and side["tool"] == "render.py"
    assert (side["set"], side["concept"]) == ("set-1", "A")
    assert side["api"] is None and side["inputs"] == []
    assert side["outputs"] == {want: common.sha256_file(str(src))}
    if case == "prompt-lint-fail":
        assert side["lint"]["status"] == "fail" and "L-BAN" in side["lint"]["codes"]
        prompt = (folder / "hero-v1.prompt.txt").read_bytes()
        assert common.sha256_text(prompt.decode("utf-8")) == side["prompt_sha256"]
    else:
        assert side["lint"] is None and side["prompt_sha256"] is None
        assert names(root, f"{A}/renders") == sorted([want[:-4] + ".json", want])


def test_import_refs_recorded_not_blocking(make_project, run, tmp_path):
    root = make_project(renders=False)
    src = external(tmp_path)
    code, out, err = run(root, "import", str(src), "--concept", "set-1/A", "--ref", "input/refs/set-2/r01.png")
    assert code == 0, out + err
    side = common.read_sidecar(str(root / A / "renders" / "hero-v1.png"))
    assert side["inputs"] == [{"role": "ref", "path": "input/refs/set-2/r01.png",
                               "sha256": common.sha256_file(str(root / "input/refs/set-2/r01.png"))}]


@pytest.mark.parametrize("case", ["client-file", "reference", "not-an-image"])
def test_import_refused(make_project, run, tmp_path, case):
    root = make_project(renders=False)
    if case == "client-file":
        src = tmp_path / "copy.png"
        shutil.copyfile(root / "input" / "product.png", src)
    elif case == "reference":
        src = tmp_path / "copy.png"
        shutil.copyfile(root / "input" / "refs" / "set-2" / "r01.png", src)
    else:
        src = tmp_path / "x.png"
        src.write_text("this is text, not a picture", encoding="utf-8")
    code, out, err = run(root, "import", str(src), "--concept", "set-1/A")
    assert names(root, f"{A}/renders") == []
    if case == "not-an-image":
        assert code == 2 and "C-INPUT" in err
    else:
        assert code == 1 and "R-SOURCE" in out and "forbidden:" in out


def test_import_unknown_concept(make_project, run, tmp_path):
    root = make_project(renders=False)
    code, out, err = run(root, "import", str(external(tmp_path)), "--concept", "set-9/Z")
    assert code == 2 and "C-INPUT" in err


# ---------- review ----------

def test_review_pass(project, run):
    (project / "marks.json").write_text(
        json.dumps([{"type": "pseudo_text", "where": "r1c3", "note": "texture on the screen"}]), encoding="utf-8")
    code, out, err = run(project, *review_args(HERO1, marks="marks.json"))
    assert code == 0, out + err
    assert "verdict: pass" in out
    r = load(project / A / "renders" / "hero-v1.review.json")
    assert list(r) == ["schema", "image", "sha256", "set", "concept", "scope", "marks", "size", "premium",
                       "reviewer_verdict", "verdict", "reviewer", "notes", "inherited_from", "reviewed_at"]
    assert r["schema"] == "review/1" and r["verdict"] == "pass" and r["scope"] == "whole"
    assert r["image"] == "hero-v1.png" and r["sha256"] == common.sha256_file(str(project / HERO1))
    assert (r["set"], r["concept"]) == ("set-1", "A")
    assert r["size"]["expected"] == {"w": 4.571, "d": 3.429, "h": 2.571}
    assert r["size"]["deviation"]["w"] == 0.037 and r["size"]["within"] is True
    assert r["size"]["deviation"]["h"] == -0.028      # h is signed: below the cap is a negative value
    assert r["marks"] == [{"type": "pseudo_text", "where": "r1c3", "note": "texture on the screen"}]
    assert r["premium"] is True and r["inherited_from"] is None and r["notes"] == ""


def test_review_height_is_one_sided(project, run):
    """booth.max_height is a cap: a stand clearly lower than expected is within; one above by more than
    size_tolerance fails; width stays two-sided."""
    low = '{"observed": {"w": 4.5, "d": 3.4, "h": 1.5}}'          # expected h 2.571: deviation -0.417
    code, out, err = run(project, *review_args(HERO1, size=low))
    assert code == 0, out + err
    r = load(project / A / "renders" / "hero-v1.review.json")
    assert r["size"]["deviation"]["h"] == -0.417 and r["size"]["within"] is True and r["verdict"] == "pass"
    high = '{"observed": {"w": 4.5, "d": 3.4, "h": 3.3}}'         # deviation +0.284
    code, out, err = run(project, *review_args(HERO1, size=high))
    assert code == 1 and "R-REVIEW" in out and "h off by 0.284" in out
    r = load(project / A / "renders" / "hero-v1.review.json")
    assert r["size"]["deviation"]["h"] == 0.284 and r["size"]["within"] is False and r["verdict"] == "fail"
    wide = '{"observed": {"w": 6.0, "d": 3.4, "h": 2.5}}'         # width is two-sided: too wide fails too
    code, out, err = run(project, *review_args(HERO1, size=wide))
    assert code == 1 and "w off by" in out


@pytest.mark.parametrize("case", ["fail-mark", "size", "not-premium", "logo-mark-on-hero"])
def test_review_fail(project, run, case):
    kw = {}
    if case == "fail-mark":
        kw["marks"] = json.dumps([{"type": "number", "where": "r2c1", "note": "a digit on the wall"}])
    elif case == "size":
        kw["size"] = '{"observed": {"w": 3.4, "d": 3.3, "h": 2.5}}'
    elif case == "not-premium":
        kw["premium"] = "no"
    else:
        kw["marks"] = json.dumps([{"type": "composited_logo", "where": "whole", "note": "logo"}])
    code, out, err = run(project, *review_args(HERO1, **kw))
    assert code == 1 and "R-REVIEW" in out and "verdict: fail" in out
    r = load(project / A / "renders" / "hero-v1.review.json")
    assert r["verdict"] == "fail"
    if case == "size":
        assert r["size"]["within"] is False


@pytest.mark.parametrize("marks", [json.dumps([{"type": "text", "where": "r1c1", "note": "x"}]),
                                   json.dumps([{"type": "pseudo_text", "where": "top-left", "note": "x"}])],
                         ids=["mark-type", "mark-where"])
def test_review_bad_input(project, run, marks):
    code, out, err = run(project, *review_args(HERO1, marks=marks))
    assert code == 2 and "C-INPUT" in err and "marks[0]" in err
    assert not (project / A / "renders" / "hero-v1.review.json").exists()


def test_review_v1_image(make_project, run):
    root = make_project(legacy=True)
    rel = "concepts/_legacy/A/renders/hero-v1.png"
    factory.put_sidecar(root, rel, "hero", version=1)
    code, out, err = run(root, *review_args(rel))
    assert code == 0, out + err
    assert "C-LEGACY" in out
    r = load(root / "concepts/_legacy/A/renders/hero-v1.review.json")
    assert (r["set"], r["concept"], r["verdict"]) == ("_legacy", "A", "pass")


def test_review_without_sidecar(project, run):
    rel = factory.add_render(project, "set-1/A", "hero-v9.png", version=None)
    code, out, err = run(project, *review_args(rel))
    assert code == 0, out + err
    assert load(project / A / "renders" / "hero-v9.review.json")["concept"] == "A"


def test_review_not_a_render(project, run):
    code, out, err = run(project, *review_args("input/refs/set-1/r01.png"))
    assert code == 2 and "C-INPUT" in err


# ---------- logo ----------

def test_logo_ok(project, run, capsys):
    factory.review_pass(project, HERO1)
    code, out, err = run(project, "logo", HERO1, "--logo", "brief/brand/logo.png", "--quad", QUAD)
    assert code == 0, out + err
    new = project / A / "renders" / "hero-v3.png"
    assert new.is_file()
    side = common.read_sidecar(str(new))
    assert side["mode"] == "logo" and side["prompt_sha256"] is None and side["lint"] is None and side["api"] is None
    assert side["inputs"] == [
        {"role": "base", "path": HERO1, "sha256": common.sha256_file(str(project / HERO1))},
        {"role": "logo", "path": "brief/brand/logo.png",
         "sha256": common.sha256_file(str(project / "brief/brand/logo.png"))}]
    chain, finding = common.trace_base_chain(common.find_project(str(project)), str(new))
    assert finding is None and chain == [f"{A}/renders/hero-v3.png", HERO1]
    r = load(project / A / "renders" / "hero-v3.review.json")
    assert r["inherited_from"]["image"] == "hero-v1.png"
    assert r["inherited_from"]["sha256"] == load(project / A / "renders" / "hero-v1.review.json")["sha256"]
    assert r["image"] == "hero-v3.png" and r["sha256"] == common.sha256_file(str(new))
    assert r["marks"][-1] == {"type": "composited_logo", "where": "whole", "note": "brief/brand/logo.png"}
    assert r["scope"] == "full" and r["verdict"] == "pass"
    # provenance: the composited output as the chosen render passes `gates.py renders`
    (project / A / "concept.md").write_text("---\nchosen: renders/hero-v3.png\n---\n", encoding="utf-8", newline="\n")
    capsys.readouterr()
    code = gates.main(["renders", "--concept", "set-1/A", "--project", str(project)])
    out = capsys.readouterr().out
    assert code == 0 and "ERROR" not in out, out


@pytest.mark.parametrize("case", ["logo-on-reference", "logo-source", "logo-ref", "label-on-reference"])
def test_logo_label_refused(project, run, has, case):
    before = names(project, f"{A}/renders")
    if case == "logo-on-reference":
        args, rule = ["logo", "input/refs/set-1/r01.png", "--logo", "brief/brand/logo.png", "--quad", QUAD], "chain"
    elif case == "logo-source":
        args, rule = ["logo", HERO1, "--logo", "input/brand-logo.png", "--quad", QUAD], "logo-source"
    elif case == "logo-ref":
        shutil.copyfile(project / "input/refs/set-1/r01.png", project / "brief/brand/x.png")
        args, rule = ["logo", HERO1, "--logo", "brief/brand/x.png", "--quad", QUAD], "logo-ref"
    else:
        args, rule = ["label", "input/refs/set-1/r01.png", "--title", "Tidal Gate"], "chain"
    code, out, err = run(project, *args)
    assert code == 1, out + err
    assert has(out, "R-SOURCE", rule)
    assert names(project, f"{A}/renders") == before
    assert not (project / "work").exists()


@pytest.mark.parametrize("case", ["no-review", "stale-review"])
def test_logo_review_not_copied(project, run, case):
    if case == "stale-review":
        factory.review_pass(project, HERO1)
        path = project / A / "renders" / "hero-v1.review.json"
        data = load(path)
        data["sha256"] = "0" * 64
        path.write_text(json.dumps(data), encoding="utf-8")
    code, out, err = run(project, "logo", HERO1, "--logo", "brief/brand/logo.png", "--quad", QUAD)
    assert code == 0, out + err
    assert (project / A / "renders" / "hero-v3.png").is_file()
    assert not (project / A / "renders" / "hero-v3.review.json").exists()
    assert "no current review on the base" in out


@pytest.mark.parametrize("quad", ["1,2 3,4", "a,b c,d e,f g,h", "10,10 20,20 30,30 40,40"],
                         ids=["two-points", "not-numbers", "degenerate"])
def test_logo_bad_quad(project, run, quad):
    code, out, err = run(project, "logo", HERO1, "--logo", "brief/brand/logo.png", "--quad", quad)
    assert code == 2 and ("--quad" in err)
    assert not (project / A / "renders" / "hero-v3.png").exists()


# ---------- label ----------

def test_label(make_project, run):
    root = make_project()
    proj = common.find_project(str(root))
    assert render.stamp_text(proj, "Tidal Gate").endswith(proj.labels["stamp"])
    styled = common.find_project(str(make_project(style={"stamp": "Concept only"})))
    assert render.stamp_text(styled, "Tidal Gate").endswith("Concept only")
    assert render.stamp_text(styled, "") == "Concept only"
    code, out, err = run(root, "label", HERO1, "--title", "Tidal Gate")
    assert code == 0, out + err
    out_png = root / "work" / "labelled" / "hero-v1-label.png"
    assert out_png.is_file() and "work/labelled/hero-v1-label.png" in out
    side = common.read_sidecar(str(out_png))
    assert side["mode"] == "label" and common.sidecar_version(side) == 2
    assert (side["set"], side["concept"]) == ("set-1", "A")
    assert side["inputs"] == [{"role": "base", "path": HERO1, "sha256": common.sha256_file(str(root / HERO1))}]
    assert common.sha256_file(str(out_png)) != common.sha256_file(str(root / HERO1))
    assert side["outputs"] == {"hero-v1-label.png": common.sha256_file(str(out_png))}


def test_label_out_not_the_image(project, run):
    code, out, err = run(project, "label", HERO1, "--title", "x", "--out", HERO1)
    assert code == 2 and "--out" in err


# ---------- tiles ----------

def sizes(folder):
    from PIL import Image
    out = {}
    for p in sorted(Path(folder).iterdir()):
        with Image.open(p) as im:
            out[p.name] = im.size
    return out


@pytest.mark.parametrize("case", ["default-grid", "grid-2x2", "outside-renders"])
def test_tiles(project, run, case):
    from PIL import Image
    Image.new("RGB", (1536, 1024), (90, 120, 150)).save(project / HERO1)
    folder = project / "work/tiles/set-1/A/hero-v1"
    if case == "outside-renders":
        code, out, err = run(project, "tiles", "input/product.png")
        assert code == 2 and "C-INPUT" in err
        assert not (project / "work").exists()
        return
    code, out, err = run(project, "tiles", HERO1)
    assert code == 0, out + err
    found = sizes(folder)
    assert sorted(found) == [f"r{r}c{c}.png" for r in (1, 2) for c in (1, 2, 3)]
    assert found["r1c1.png"] == (553, 553) and found["r1c2.png"] == (594, 553) and found["r2c3.png"] == (553, 553)
    assert "work/tiles/set-1/A/hero-v1/r1c1.png" in out
    if case == "grid-2x2":
        code, out, err = run(project, "tiles", HERO1, "--grid", "2x2")
        assert code == 0, out + err
        assert sorted(sizes(folder)) == ["r1c1.png", "r1c2.png", "r2c1.png", "r2c2.png"]


@pytest.mark.parametrize("grid", ["0x2", "7x1", "3-2"])
def test_tiles_bad_grid(project, run, grid):
    code, out, err = run(project, "tiles", HERO1, "--grid", grid)
    assert code == 2 and "--grid" in err
    assert not (project / "work").exists()


# ---------- sheet ----------

def image_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


@pytest.mark.parametrize("case", ["candidates", "chosen-one-missing", "chosen-all"])
def test_sheet(project, run, case):
    if case == "candidates":
        factory.review_pass(project, f"{A}/renders/hero-v2.png")
        code, out, err = run(project, "sheet", "--set", "set-1", "--candidates")
        board = project / "work/sheets/set-1-candidates.png"
        assert code == 0, out + err
        assert board.is_file() and image_size(board)[1] >= 2 * 512
        assert "work/sheets/set-1-candidates.png" in out
    elif case == "chosen-one-missing":
        (project / "concepts/set-1/B/concept.md").write_text("---\n---\n", encoding="utf-8")
        code, out, err = run(project, "sheet", "--set", "set-1", "--chosen")
        assert code == 0, out + err
        assert (project / "work/sheets/set-1-chosen.png").is_file()
    else:
        code, out, err = run(project, "sheet", "--chosen-all")
        assert code == 0, out + err
        assert (project / "work/sheets/chosen-all.png").is_file()


def test_sheet_captions(project, run, monkeypatch):
    """The overview of all sets qualifies each caption with its set; a set's own sheets keep the bare id."""
    seen = []
    monkeypatch.setattr(render, "make_sheet", lambda title, rows, out: seen.append([[c for _, c in r] for r in rows]))
    (project / "concepts/set-2/B/concept.md").write_text("---\n---\n", encoding="utf-8")
    code, out, err = run(project, "sheet", "--chosen-all")
    assert code == 0, out + err
    assert seen[-1] == [["set-1/A · hero-v2.png · no review", "set-1/B · hero-v2.png · no review"],
                        ["set-2/A · hero-v2.png · no review", "set-2/B · no chosen"]]
    code, out, err = run(project, "sheet", "--set", "set-2", "--chosen")
    assert code == 0, out + err
    assert seen[-1] == [["A · hero-v2.png · no review", "B · no chosen"]]
    code, out, err = run(project, "sheet", "--set", "set-1", "--candidates")
    assert code == 0, out + err
    assert all(cap.startswith(("A · ", "B · ")) for row in seen[-1] for cap in row)


def test_sheet_errors(project, run):
    code, out, err = run(project, "sheet", "--set", "set-9", "--candidates")
    assert code == 2 and "C-INPUT" in err
    code, out, err = run(project, "sheet", "--candidates")
    assert code == 2 and "--set" in err
    assert not (project / "work").exists()


def test_review_state(project):
    img = project / A / "renders" / "hero-v2.png"
    assert render.review_state(str(img)) == "no review"
    factory.review_pass(project, f"{A}/renders/hero-v2.png")
    assert render.review_state(str(img)) == "pass full"
    factory.review_pass(project, f"{A}/renders/hero-v2.png", scope="whole")
    assert render.review_state(str(img)) == "pass whole"
    img.write_bytes(img.read_bytes() + b"x")
    assert render.review_state(str(img)) == "stale review"
