"""Graphics (stage A2): render.py graphic and its lint mode, import/fix/logo/review/tiles/sheet on a graphic, the
graphic checks of gates.py renders and of the deck check, the graphic layout and the cost line.
No network: render.send is always replaced, urlopen is never reached."""
import json
import re
import shutil
from pathlib import Path

import pytest

import common
import deck
import deck_check
import deck_html
import factory
import render

GR = "graphics/GR1"
GP = f"{GR}/prompts/graphic.txt"
G1 = f"{GR}/renders/graphic-v1.png"
G2 = f"{GR}/renders/graphic-v2.png"
A = "concepts/set-1/A"
FIX_ADD = "Remove the stray gull; nothing else changes."
TEXT_MARK = '[{"type": "legible_text", "where": "r1c1", "note": "headline painted"}]'
FIXED = json.loads((Path(common.SKILL_DIR) / "assets" / "prompts" / "fixed.json").read_text(encoding="utf-8"))


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


def write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    return rel


def names(root, rel):
    folder = Path(root) / rel
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def edit_brief(root, fn):
    path = str(Path(root) / "brief" / "brief.json")
    brief = common.read_json(path)
    fn(brief)
    common.write_json(path, brief)


@pytest.fixture
def gbare(make_project):
    """A project with the graphic GR1 in brief.json and a passing graphic prompt, no renders at all."""
    root = make_project(renders=False, graphics=True)
    write(root, GP, factory.graphic_ok())
    return root


@pytest.fixture
def gdone(make_project):
    """A project with GR1 rendered twice (graphic-v1, graphic-v2) through render.py graphic, and concept renders."""
    root = make_project(graphics=True)
    factory._render_graphic(root)
    return root


def graphic_args(*extra, area="top", refs=("input/product.png",)):
    args = ["graphic", "--graphic", "GR1", "--prompt", GP, "--area", area]
    for r in refs:
        args += ["--ref", r]
    return [*args, *extra]


def prompt_without(*needles):
    return "\n".join(ln for ln in factory.graphic_ok().split("\n") if not any(n in ln for n in needles))


def external(tmp_path, name="ext.png", size=(64, 96)):
    from PIL import Image
    path = tmp_path / name
    Image.new("RGB", size, factory._next_rgb()).save(path)
    return path


def lint_findings(run, root, text, *extra, area="top"):
    write(root, GP, text)
    code, out, err = run(root, "lint", "--mode", "graphic", "--prompt", GP, "--graphic", "GR1", "--area", area,
                         "--json", *extra)
    return code, json.loads(out)["findings"]


def names_of(findings, code):
    return [f["message"].split(":", 1)[0] for f in findings if f["code"] == code]


# ---------- size from ratio ----------

@pytest.mark.parametrize("ratio, want", [("2:3", "1024x1536"), ("9:16", "1024x1536"), ("4:5", "1024x1536"),
                                         ("1:1", "1024x1024"), ("3:2", "1536x1024"), ("16:9", "1536x1024")])
def test_size_for_ratio(ratio, want):
    assert render.size_for_ratio(ratio) == want


def test_size_for_ratio_unusable():
    with pytest.raises(common.InputError) as e:
        render.size_for_ratio("tall")
    assert e.value.code == "C-INPUT"


# ---------- lint mode graphic ----------

def test_graphic_lint_ok(gbare, run):
    code, findings = lint_findings(run, gbare, factory.graphic_ok(), "--ref", "input/product.png")
    assert code == 0 and findings == []


BLOCKS = {
    "graphic": (prompt_without("Graphic – Calm"), "graphic", "top"),
    "colours": (prompt_without("Brand colours:"), "colours", "top"),
    "composition": (prompt_without("Composition:", "- A tall portrait", "- The upper third", "- The subject fills"),
                    "composition", "top"),
    "text-area": (prompt_without("- The upper third"), "text-area", "top"),
    "subject": (prompt_without("Subject:", "- A modern hybrid", "- Gulls and"), "subject", "top"),
    "no-text": (prompt_without(FIXED["graphic_no_text"]), "no-text", "top"),
    "area-sentence": (prompt_without(FIXED["graphic_text_area"]), "area-sentence", "top"),
    "ref-sentence": (prompt_without(FIXED["graphic_ref"]), "ref-sentence", "top"),
    "area-left": (factory.graphic_ok(), "text-area", "left"),
}


@pytest.mark.parametrize("case", list(BLOCKS))
def test_graphic_lint_blocks(gbare, run, case):
    text, rule, area = BLOCKS[case]
    code, findings = lint_findings(run, gbare, text, "--ref", "input/product.png", area=area)
    assert code == 1
    assert rule in names_of(findings, "L-BLOCKS"), findings
    if case == "area-left":
        msg = next(f["message"] for f in findings if f["message"].startswith("text-area:"))
        assert "left" in msg


def test_graphic_lint_no_refs_needs_no_ref_sentence(gbare, run):
    code, findings = lint_findings(run, gbare, factory.graphic_ok(refs=False))
    assert code == 0 and names_of(findings, "L-BLOCKS") == []


PAINTED = ["the headline Sail the quiet way across the sky", "a big title in bold type",
           "the ferry name painted on the bow"]
BANS = [("a sign that reads Welcome aboard", "logo-text"), ("three 3 ferries", "digit"), ("Nordvik", "client"),
        ("a 船 shape", "cjk"), ('a "quoted" word', "quote"), ("founded long ago", "timeline")]


@pytest.mark.parametrize("extra, rule", BANS, ids=[r for _, r in BANS])
def test_graphic_lint_ban(gbare, run, extra, rule):
    text = factory.graphic_ok().replace("the hull panels are plain.", f"the hull panels are plain, {extra}.")
    code, findings = lint_findings(run, gbare, text, "--ref", "input/product.png")
    assert code == 1 and rule in names_of(findings, "L-BAN"), findings


@pytest.mark.parametrize("extra", PAINTED)
@pytest.mark.parametrize("block", ["subject", "graphic"])
def test_graphic_lint_painted_text_banned_in_graphic_and_subject(gbare, run, extra, block):
    old = {"subject": "the hull panels are plain.", "graphic": "at the stand."}[block]
    text = factory.graphic_ok().replace(old, f"{old[:-1]}, {extra}.", 1)
    assert text != factory.graphic_ok()
    code, findings = lint_findings(run, gbare, text, "--ref", "input/product.png")
    assert code == 1 and "graphic-text" in names_of(findings, "L-BAN"), findings


def test_graphic_lint_composition_may_name_the_title(gbare, run):
    line = "- The upper third is kept empty: a calm field of deep navy for the title, and nothing reaches into it."
    assert line in factory.graphic_ok()
    for new in ("- The top third is left empty for the title.",
                "- The top third is left empty for the headline and the tagline."):
        text = factory.graphic_ok().replace(line, new)
        code, findings = lint_findings(run, gbare, text, "--ref", "input/product.png")
        assert code == 0 and findings == [], findings


@pytest.mark.parametrize("new", ["- The upper third is kept empty and the subject fills it.",
                                 "- The subject covers the upper third, which is left empty elsewhere."])
def test_graphic_lint_reserved_line_that_the_subject_fills_does_not_count(gbare, run, new):
    line = "- The upper third is kept empty: a calm field of deep navy for the title, and nothing reaches into it."
    text = factory.graphic_ok().replace(line, new)
    code, findings = lint_findings(run, gbare, text, "--ref", "input/product.png")
    assert code == 1 and "text-area" in names_of(findings, "L-BLOCKS"), findings


def test_graphic_lint_bans_skip_fixed_sentences_and_colours(gbare, run):
    # the colours line holds hex digits and the fixed sentences hold banned words: neither is a finding
    code, findings = lint_findings(run, gbare, factory.graphic_ok(), "--ref", "input/product.png")
    assert code == 0 and findings == []


def test_graphic_lint_refs(gdone, run):
    code, findings = lint_findings(run, gdone, factory.graphic_ok(), "--ref", "input/brand-logo.png")
    assert code == 1 and "graphic" in names_of(findings, "L-REF")
    code, findings = lint_findings(run, gdone, factory.graphic_ok(), "--ref", f"{A}/renders/hero-v1.png")
    assert code == 1 and "render" in names_of(findings, "L-REF")
    code, findings = lint_findings(run, gdone, factory.graphic_ok(), "--ref", G1)
    assert "render" in names_of(findings, "L-REF")


@pytest.mark.parametrize("args", [["--area", "top"], ["--ref", "input/product.png"],
                                  ["--graphic", "GR1", "--concept", "set-1/A"], ["--graphic", "GR1"]],
                         ids=["area", "ref", "both", "graphic-in-hero-mode"])
def test_graphic_lint_usage(gbare, run, args):
    write(gbare, GP, factory.graphic_ok())
    base = ["lint", "--mode", "hero", "--prompt", GP]
    code, out, err = run(gbare, *base, *args)
    assert code == 2


@pytest.mark.parametrize("mode", ["fix", "front"])
def test_graphic_lint_graphic_option_only_with_graphic_mode(gbare, run, mode):
    write(gbare, GP, factory.graphic_ok())
    code, out, err = run(gbare, "lint", "--mode", mode, "--prompt", GP, "--graphic", "GR1")
    assert code == 2 and "--graphic goes only with --mode graphic" in err


def test_graphic_lint_concept_with_graphic_mode(gbare, run):
    write(gbare, GP, factory.graphic_ok())
    code, out, err = run(gbare, "lint", "--mode", "graphic", "--prompt", GP, "--area", "top", "--concept", "set-1/A")
    assert code == 2 and "--concept does not go with --mode graphic" in err
    code, out, err = run(gbare, "lint", "--mode", "graphic", "--prompt", GP, "--area", "top", "--graphic", "GR1")
    assert code == 0, out + err


def test_lint_data_validates_graphic_keys(monkeypatch, tmp_path):
    data = load(render.LINT_PATH)
    for key, value in (("text_area_words", "empty"), ("text_area_words", [""]), ("area_words", {"top": ["x"]}),
                       ("area_words", {**data["area_words"], "left": []})):
        bad = tmp_path / f"{key}-{len(str(value))}.json"
        bad.write_text(json.dumps({**data, key: value}), encoding="utf-8")
        monkeypatch.setattr(render, "LINT_PATH", str(bad))
        with pytest.raises(common.InputError) as e:
            render.load_prompt_data()
        assert e.value.code == "C-INPUT" and key in str(e.value)


# ---------- render.py graphic ----------

def test_graphic_dry_run(gbare, fake_send, run):
    code, out, err = run(gbare, *graphic_args("--dry-run"))
    assert code == 0, out + err
    assert fake_send.calls == []
    for want in ("images/edits", "size: 1024x1536", "n: 2", f"would save {G1}"):
        assert want in out, want
    assert names(gbare, f"{GR}/renders") == []


def test_graphic_call_sidecar(gbare, fake_send, run):
    for _ in range(2):
        code, out, err = run(gbare, *graphic_args())
        assert code == 0, out + err
    assert names(gbare, f"{GR}/renders") == sorted(f"graphic-v{k}.{x}" for k in range(1, 5)
                                                   for x in ("json", "png", "prompt.txt"))
    side = load(gbare / GR / "renders" / "graphic-v1.json")
    assert side["schema"] == "sidecar/2" and side["mode"] == "graphic" and side["kind"] == "graphic"
    assert (side["graphic"], side["area"], side["ratio"]) == ("GR1", "top", "2:3")
    assert side["set"] is None and side["concept"] is None
    assert side["inputs"] == [{"role": "ref", "path": "input/product.png",
                               "sha256": common.sha256_file(str(gbare / "input" / "product.png"))}]
    sent = (gbare / GR / "renders" / "graphic-v1.prompt.txt").read_text(encoding="utf-8")
    assert side["prompt_sha256"] == common.sha256_text(sent)
    assert side["lint"] == {"status": "pass", "codes": []}
    assert side["api"]["size"] == "1024x1536"
    assert [c[1]["size"] for c in fake_send.calls] == ["1024x1536", "1024x1536"]
    assert fake_send.calls[0][0].endswith("/images/edits") and fake_send.calls[0][2] == ["input/product.png"]
    proj = common.find_project(str(gbare))
    fm, findings = common.read_front_matter(common.graphic_ref(proj, "GR1"))
    assert fm["chosen"] is None and findings == []
    assert (gbare / GR / "graphic.md").read_text(encoding="utf-8") == "---\n---\nNotes.\n"


def test_graphic_without_refs_uses_generation(gbare, fake_send, run):
    write(gbare, GP, factory.graphic_ok(refs=False))
    code, out, err = run(gbare, *graphic_args(refs=()))
    assert code == 0, out + err
    assert fake_send.calls[0][0].endswith("/images/generations") and fake_send.calls[0][2] == []


def test_graphic_square_and_wide_sizes(gbare, fake_send, run):
    edit_brief(gbare, lambda b: b["graphics"][0].update(ratio="16:9"))
    code, out, err = run(gbare, *graphic_args("--dry-run", "--candidates", "1"))
    assert code == 0 and "size: 1536x1024" in out and "n: 1" in out
    code, out, err = run(gbare, *graphic_args("--dry-run", "--size", "1024x1024"))
    assert "size: 1024x1024" in out


def test_graphic_refusals_unknown_and_candidates(gbare, fake_send, run):
    code, out, err = run(gbare, *graphic_args()[:2], "GR9", *graphic_args()[3:])
    assert code == 2 and "C-INPUT" in err and "GR9" in err
    code, out, err = run(gbare, *graphic_args("--candidates", "11"))
    assert code == 2
    assert fake_send.calls == []


def test_graphic_refusal_showcase(gbare, fake_send, run):
    edit_brief(gbare, lambda b: b.update(proposal={"architecture": "showcase"}))
    code, out, err = run(gbare, *graphic_args())
    assert code == 2 and "shows no graphics" in err
    assert fake_send.calls == []


def test_graphic_refusal_lint_error(gbare, fake_send, run):
    write(gbare, GP, factory.graphic_ok().replace("low hills behind.", "low hills behind, 3 ferries."))
    code, out, err = run(gbare, *graphic_args())
    assert code == 1 and "L-BAN" in out
    assert fake_send.calls == [] and names(gbare, f"{GR}/renders") == []


def test_graphic_refusal_no_key(gbare, monkeypatch, run, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    (tmp_path / ".git").mkdir()
    calls = []
    monkeypatch.setattr(render, "send", lambda *a, **k: calls.append(a))
    code, out, err = run(gbare, *graphic_args())
    assert code == 3 and "R-API" in err and calls == []


def test_graphic_ref_not_of_this_graphic_blocks(gbare, fake_send, run):
    code, out, err = run(gbare, *graphic_args(refs=("input/brand-logo.png",)))
    assert code == 1 and "L-REF" in out and fake_send.calls == []


# ---------- import ----------

IMPORTS = ["ok", "product", "stamped", "no-area", "view", "concept-area"]


@pytest.mark.parametrize("case", IMPORTS)
def test_graphic_import(gbare, run, tmp_path, case):
    src = external(tmp_path)
    args = ["import", str(src), "--graphic", "GR1", "--area", "bottom"]
    if case == "product":
        args[1] = str(gbare / "input" / "product.png")
    elif case == "stamped":
        args[1] = str(gbare / "input" / "refs" / "set-1" / "r01.png")
    elif case == "no-area":
        args = args[:-2]
    elif case == "view":
        args += ["--view", "x"]
    elif case == "concept-area":
        args = ["import", str(src), "--concept", "set-1/A", "--area", "top"]
    code, out, err = run(gbare, *args)
    folder = gbare / GR / "renders"
    if case == "ok":
        assert code == 0, out + err
        side = common.read_sidecar(str(folder / "graphic-v1.png"))
        assert side["mode"] == "import" and side["kind"] == "graphic" and side["graphic"] == "GR1"
        assert (side["area"], side["ratio"]) == ("bottom", "2:3")
        assert side["set"] is None and common.sidecar_version(side) == 2
        assert (gbare / GR / "graphic.md").is_file()
    elif case in ("product", "stamped"):
        assert code == 1 and "R-SOURCE" in out
        if case == "product":
            assert "same content as input/product.png" in out
        assert names(gbare, f"{GR}/renders") == []
    else:
        assert code == 2, out + err


def test_graphic_import_prompt_never_blocks(gbare, run, tmp_path):
    write(gbare, GP, factory.graphic_ok().replace("low hills behind.", "low hills behind, 3 ferries."))
    code, out, err = run(gbare, "import", str(external(tmp_path)), "--graphic", "GR1", "--area", "top",
                         "--prompt", GP, "--ref", "input/product.png")
    assert code == 0 and "L-BAN" in out
    side = common.read_sidecar(str(gbare / GR / "renders" / "graphic-v1.png"))
    assert side["lint"]["status"] == "fail" and side["inputs"][0]["role"] == "ref"


def test_import_graphic_shows_no_graphics_in_showcase(gbare, run, tmp_path):
    edit_brief(gbare, lambda b: b.update(proposal={"architecture": "showcase"}))
    code, out, err = run(gbare, "import", str(external(tmp_path)), "--graphic", "GR1", "--area", "top")
    assert code == 2 and "shows no graphics" in err


# ---------- chains: fix, logo, label ----------

def test_graphic_fix(gdone, fake_send, run):
    code, out, err = run(gdone, "fix", "--graphic", "GR1", "--base", G2, "--add", FIX_ADD)
    assert code == 0, out + err
    assert fake_send.calls[0][1]["size"] == "1024x1536"
    assert "Edit this flat graphic artwork" in fake_send.calls[0][1]["prompt"]
    out_rel = f"{GR}/renders/graphic-v3.png"
    side = common.read_sidecar(str(gdone / out_rel))
    assert side["mode"] == "fix" and side["kind"] == "graphic" and side["graphic"] == "GR1"
    assert (side["area"], side["ratio"]) == ("top", "2:3")
    assert side["inputs"] == [{"role": "base", "path": G2, "sha256": common.sha256_file(str(gdone / G2))}]
    proj = common.find_project(str(gdone))
    chain, finding = common.trace_base_chain(proj, str(gdone / out_rel))
    assert finding is None and chain == [out_rel, G2]


def test_graphic_fix_refuses_concept_base_and_view(gdone, fake_send, run):
    code, out, err = run(gdone, "fix", "--graphic", "GR1", "--base", f"{A}/renders/hero-v1.png", "--add", FIX_ADD)
    assert code == 1 and "R-SOURCE" in out
    code, out, err = run(gdone, "fix", "--graphic", "GR1", "--base", G2, "--add", FIX_ADD, "--view", "x")
    assert code == 2
    code, out, err = run(gdone, "fix", "--concept", "set-1/A", "--graphic", "GR1", "--base", G2, "--add", FIX_ADD)
    assert code == 2
    assert fake_send.calls == []


def test_graphic_logo_uses_normal_blend(gdone, run):
    from PIL import Image
    code, out, err = run(gdone, "logo", G2, "--logo", "brief/brand/logo.png", "--quad", "10,8 40,8 40,20 10,20")
    assert code == 0, out + err
    out_rel = f"{GR}/renders/graphic-v3.png"
    side = common.read_sidecar(str(gdone / out_rel))
    assert side["mode"] == "logo" and side["kind"] == "graphic" and (side["area"], side["ratio"]) == ("top", "2:3")
    logo = Image.open(gdone / "brief" / "brand" / "logo.png").convert("RGB").getpixel((5, 5))
    pixel = Image.open(gdone / out_rel).convert("RGB").getpixel((25, 14))
    assert all(abs(a - b) <= 3 for a, b in zip(pixel, logo)), (pixel, logo)
    proj = common.find_project(str(gdone))
    chain, finding = common.trace_base_chain(proj, str(gdone / out_rel))
    assert finding is None and chain == [out_rel, G2]


def test_graphic_logo_carries_review(gdone, run):
    factory.review_graphic_pass(gdone, G2)
    code, out, err = run(gdone, "logo", G2, "--logo", "brief/brand/logo.png", "--quad", "10,8 40,8 40,20 10,20")
    assert code == 0, out + err
    review = load(gdone / GR / "renders" / "graphic-v3.review.json")
    assert review["kind"] == "graphic" and review["graphic"] == "GR1" and review["size"] is None
    assert [m["type"] for m in review["marks"]] == ["composited_logo"]
    assert review["verdict"] == "pass" and review["inherited_from"]["image"] == "graphic-v2.png"


def test_graphic_label_keeps_graphic_fields(gdone, run):
    code, out, err = run(gdone, "label", G2, "--title", "Fleet story")
    assert code == 0, out + err
    side = common.read_sidecar(str(gdone / "work" / "labelled" / "graphic-v2-label.png"))
    assert side["mode"] == "label" and side["kind"] == "graphic" and side["graphic"] == "GR1"


def _concept_sidecar_kind_graphic(root):
    rel = factory.add_render(root, "set-1/A", "hero-v9.png")
    image = str(Path(root) / rel)
    data = common.read_sidecar(image)
    data["kind"] = "graphic"
    common.write_sidecar(image, data)
    return rel


CHAINS = {
    "concept-base": (lambda r: factory.add_graphic(r, "GR1", "graphic-v9.png", mode="fix",
                                                   base=f"{A}/renders/hero-v1.png"), "is not a render of graphics/GR1"),
    "no-kind": (lambda r: factory.add_graphic(r, "GR1", "graphic-v9.png", kind=None), "(sidecar kind)"),
    "hero-mode": (lambda r: factory.add_graphic(r, "GR1", "graphic-v9.png", mode="hero"), "cannot start a chain"),
    "in-concept": (_concept_sidecar_kind_graphic, "(sidecar kind)"),
}


@pytest.mark.parametrize("case", list(CHAINS))
def test_graphic_chain_refusals(gdone, case):
    make, want = CHAINS[case]
    rel = make(gdone)
    proj = common.find_project(str(gdone))
    _, finding = common.trace_base_chain(proj, str(gdone / rel))
    assert finding is not None and finding.code == "R-SOURCE" and want in finding.message, finding


def test_graphic_old_sidecar_refused(gdone):
    rel = factory.add_graphic(gdone, "GR1", "graphic-v9.png")
    common.write_json(common.sidecar_path(str(gdone / rel)), {"image": "graphic-v9.png", "mode": "hero"})
    proj = common.find_project(str(gdone))
    _, finding = common.trace_base_chain(proj, str(gdone / rel))
    assert finding is not None and "graphics need sidecar/2" in finding.message


def test_concept_chain_messages_unchanged(gdone):
    proj = common.find_project(str(gdone))
    _, finding = common.trace_base_chain(proj, str(gdone / "input" / "product.png"))
    assert finding.message == "chain: not a render of any concept"


def test_forbidden_graphic_refs(make_project):
    root = make_project(renders=False, graphics=True)
    (root / "work").mkdir()
    (root / "work" / "sketch.png").write_bytes(factory.png_bytes(factory._next_rgb()))
    factory.add_graphic(root, "GR1", "graphic-v1.png", refs=("work/sketch.png",))
    proj = common.find_project(str(root))
    forbidden = common.forbidden_hashes(proj)
    assert forbidden[common.sha256_file(str(root / "work" / "sketch.png"))] == "work/sketch.png"


# ---------- review ----------

def review_args(image, *extra, marks="[]", premium="yes", verdict="pass"):
    return ["review", image, "--reviewer", "subagent", "--verdict", verdict, "--premium", premium,
            "--marks-json", marks, *extra]


CONCEPT_SIZE = ["--size-json", '{"observed": {"w": 4.4, "d": 3.3, "h": 2.5}}']
REVIEWS = {
    "pass": ({}, ["--text-area", "yes"], 0, "verdict: pass"),
    "legible-text": ({"marks": TEXT_MARK}, ["--text-area", "yes"], 1, "R-REVIEW"),
    "pseudo-text": ({"marks": TEXT_MARK.replace("legible_text", "pseudo_text")}, ["--text-area", "yes"], 1,
                    "read up close"),
    "pasted-photo": ({"marks": TEXT_MARK.replace("legible_text", "pasted_photo")}, ["--text-area", "yes"], 1,
                     "pasted_photo"),
    "text-area-no": ({}, ["--text-area", "no"], 1, "not clean and usable"),
    "premium-no": ({"premium": "no"}, ["--text-area", "yes"], 1, "not premium"),
    "size-json": ({}, ["--text-area", "yes", *CONCEPT_SIZE], 2, ""),
    "no-text-area": ({}, [], 2, ""),
}


@pytest.mark.parametrize("case", list(REVIEWS))
def test_graphic_review(gdone, run, case):
    kw, extra, want_code, want_text = REVIEWS[case]
    code, out, err = run(gdone, *review_args(G2, *extra, **kw))
    assert code == want_code, out + err
    assert want_text in out + err
    path = gdone / GR / "renders" / "graphic-v2.review.json"
    if want_code == 2:
        assert not path.exists()
        return
    review = load(path)
    assert review["kind"] == "graphic" and review["graphic"] == "GR1" and review["size"] is None
    assert review["set"] is None and review["concept"] is None
    assert review["text_area"] is (case != "text-area-no")
    assert review["verdict"] == ("pass" if want_code == 0 else "fail")


@pytest.mark.parametrize("case", ["text-area", "no-size"])
def test_concept_review_option_checks(gdone, run, case):
    if case == "text-area":
        args = review_args(f"{A}/renders/hero-v1.png", *CONCEPT_SIZE, "--text-area", "yes")
    else:
        args = review_args(f"{A}/renders/hero-v1.png")
    code, out, err = run(gdone, *args)
    assert code == 2


def test_graphic_pseudo_text_concept_unchanged(gdone, run):
    marks = '[{"type": "pseudo_text", "where": "whole", "note": "texture"}]'
    code, out, err = run(gdone, *review_args(f"{A}/renders/hero-v1.png", *CONCEPT_SIZE, marks=marks))
    assert code == 0 and "verdict: pass" in out


def test_review_after_graphic_logo_fail_blocks(gdone, run):
    # a graphic with painted text: the logo carry-over recomputes the verdict, so the output stays failed
    code, out, err = run(gdone, *review_args(G2, "--text-area", "yes", marks=TEXT_MARK))
    assert code == 1
    code, out, err = run(gdone, "logo", G2, "--logo", "brief/brand/logo.png", "--quad", "10,8 40,8 40,20 10,20")
    assert code == 0 and "verdict: fail" in out
    assert load(gdone / GR / "renders" / "graphic-v3.review.json")["verdict"] == "fail"


# ---------- tiles and sheet ----------

def test_tiles_graphic(make_project, run):
    root = make_project(renders=False, graphics=True)
    rel = factory.add_graphic(root, "GR1", "graphic-v1.png")
    code, out, err = run(root, "tiles", rel)
    assert code == 0, out + err
    assert names(root, "work/tiles/graphics/GR1/graphic-v1") == sorted(f"r{r}c{c}.png" for r in (1, 2, 3)
                                                                       for c in (1, 2))
    code, out, err = run(root, "tiles", rel, "--grid", "3x2")
    assert len(names(root, "work/tiles/graphics/GR1/graphic-v1")) == 6
    assert "r2c3.png" in names(root, "work/tiles/graphics/GR1/graphic-v1")


def test_sheet_graphics(gdone, run, make_project):
    code, out, err = run(gdone, "sheet", "--graphics")
    assert code == 0, out + err
    assert (gdone / "work" / "sheets" / "graphics.png").is_file()
    bare = make_project(renders=False)
    code, out, err = run(bare, "sheet", "--graphics")
    assert code == 2 and "no graphics in brief.json" in err


def test_sheet_graphics_row_without_images(gbare, run):
    code, out, err = run(gbare, "sheet", "--graphics")
    assert code == 0 and (gbare / "work" / "sheets" / "graphics.png").is_file()


def test_renders_of_graphic_candidates(gdone):
    proj = common.find_project(str(gdone))
    g = common.graphic_ref(proj, "GR1")
    assert [Path(p).name for p in render.renders_of(g)] == ["graphic-v1.png", "graphic-v2.png"]
    factory.add_graphic(gdone, "GR1", "graphic-v3.png", mode="fix", base=G2)
    assert [Path(p).name for p in render.renders_of(g)] == ["graphic-v1.png", "graphic-v2.png"]


# ---------- gates.py renders ----------

def chosen_deck(tmp_path):
    return factory.deck_project(tmp_path, arch="tender", graphics=True)


def test_gates_renders_graphics(tmp_path, run_gates):
    root = chosen_deck(tmp_path)
    code, out, err = run_gates(root, "renders")
    assert code == 0, out + err
    assert "RESULT: PASS – 0 errors, 0 warnings" in out


def _nochosen(root):
    write(root, f"{GR}/graphic.md", "---\n---\nNotes.\n")


def _unreviewed(root):
    (root / GR / "renders" / "graphic-v2.review.json").unlink()


def _text_painted(root):
    render.main(review_args(str(root / G2), "--text-area", "yes", "--scope", "full", marks=TEXT_MARK)
                + ["--project", str(root)])


def _unlisted(root):
    factory.add_graphic(root, "GR7", "graphic-v1.png")


def _chain_ref(root):
    factory.put_graphic_sidecar(root, G2, "graphic", refs=("input/brand-logo.png",))


def _product_copy(root):
    rel = factory.add_graphic(root, "GR1", "graphic-v9.png", data=(root / "input" / "product.png").read_bytes())
    factory.review_graphic_pass(root, rel)
    write(root, f"{GR}/graphic.md", "---\nchosen: renders/graphic-v9.png\n---\nNotes.\n")


def _no_renders(root):
    shutil.rmtree(root / GR)


RULES = {
    "nochosen": (_nochosen, [], "G-RENDER", "nochosen", 1),
    "unreviewed": (_unreviewed, [], "G-REVIEW", "missing", 1),
    "text-painted": (_text_painted, [], "G-REVIEW", "fail", 1),
    "unlisted": (_unlisted, [], "G-RENDER", "unlisted", 1),
    "chain-ref": (_chain_ref, [], "G-RENDER", "refs", 1),
    "product-copy": (_product_copy, [], "G-RENDER", "chain", 1),
    "no-renders": (_no_renders, [], "G-RENDER", "missing", 0),
}


@pytest.mark.parametrize("case", list(RULES))
def test_gates_renders_graphic_rules(tmp_path, run_gates, has, case):
    make, extra, code_name, rule, want_code = RULES[case]
    root = chosen_deck(tmp_path)
    make(root)
    code, out, err = run_gates(root, "renders", *extra)
    assert code == want_code, out + err
    assert has(out, code_name, rule), out
    if case == "nochosen":
        assert f"{GR}/graphic.md" in has(out, code_name, rule)[0]
    if case == "product-copy":
        assert "same content as input/product.png" in out
    if case == "no-renders":
        assert any(ln.startswith("WARN") for ln in has(out, code_name, rule))


def test_gates_renders_filters(tmp_path, run_gates):
    root = chosen_deck(tmp_path)
    factory.add_graphic(root, "GR7", "graphic-v1.png")                 # on disk, not in brief.json: broken
    code, out, err = run_gates(root, "renders", "--graphic", "GR1")
    assert code == 0 and "GR7" not in out, out
    code, out, err = run_gates(root, "renders", "--graphic", "GR7")
    assert code == 2 and "C-INPUT" in err
    code, out, err = run_gates(root, "renders", "--concept", "set-1/A")
    assert code == 0 and "GR7" not in out
    code, out, err = run_gates(root, "renders", "--concept", "set-1/A", "--graphic", "GR1")
    assert code == 0


def test_gates_renders_missing_only_when_architecture_shows_graphics(make_project, run_gates, has):
    root = make_project(renders=False, graphics=True)
    code, out, err = run_gates(root, "renders", "--graphic", "GR1")
    assert code == 0 and has(out, "G-RENDER", "missing")
    edit_brief(root, lambda b: b.update(proposal={"architecture": "showcase"}))
    code, out, err = run_gates(root, "renders", "--graphic", "GR1")
    assert code == 0 and not has(out, "G-RENDER", "missing")


# ---------- template, layout, deck ----------

def test_template_graphic():
    src = open(deck_html.DEFAULT_TEMPLATE, encoding="utf-8-sig").read()
    tpl = deck_html.load_template(deck_html.DEFAULT_TEMPLATE)
    found = {e.variant: e for e in tpl.examples if e.layout == "graphic"}
    assert set(found) == {"", "wide"}
    for ex in found.values():
        assert ex.roles == ("graphic",)
        figs = [n for n in ex.node.iter() if n.tag == "figure" and n.has_class("graphic")]
        assert len(figs) == 1
        assert re.fullmatch(r"\d+:\d+", figs[0].get("data-ratio"))
        assert figs[0].get("data-area") in common.GRAPHIC_AREAS
        assert [n.get("data-img") for n in figs[0].iter() if n.tag == "img"] == ["graphic"]
    assert "--rw" in src and "--rh" in src


def test_template_graphic_emit_and_catalogue(make_project):
    project = common.find_project(str(make_project(renders=False)))
    tpl = deck_html.load_template(deck_html.DEFAULT_TEMPLATE)
    ex = deck_html.find_example(tpl, "graphic")
    out = deck_html.emit(ex, project)
    assert 'data-role="graphic"' in out and 'src=""' in out
    lines = deck_html.catalogue_lines(tpl, 1, "en", project.architecture)
    row = next(ln for ln in lines if ln.startswith("graphic  "))
    assert "images=graphic" in row and "chapters=" in row and "graphics" in row


def emit_graphic(root, *args):
    import contextlib
    import io
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = deck.main(["layouts", *args, "--project", str(root)])
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


def test_layouts_emit_graphic(tmp_path):
    root = chosen_deck(tmp_path)
    code, out, err = emit_graphic(root, "--emit", "graphic", "--graphic", "GR1")
    assert code == 0, err
    assert 'src="../graphics/GR1/renders/graphic-v2.png"' in out
    assert 'data-ratio="2:3"' in out and 'data-area="top"' in out and 'data-role="graphic"' in out
    assert err == ""
    write(root, f"{GR}/graphic.md", "---\n---\nNotes.\n")
    code, out, err = emit_graphic(root, "--emit", "graphic", "--graphic", "GR1")
    assert code == 2 and "no chosen render" in err
    code, out, err = emit_graphic(root, "--emit", "board", "--graphic", "GR1")
    assert code == 2
    code, out, err = emit_graphic(root, "--emit", "graphic", "--graphic", "GR9")
    assert code == 2


def test_layouts_emit_graphic_notes_shape(tmp_path):
    root = chosen_deck(tmp_path)
    edit_brief(root, lambda b: b["graphics"][0].update(ratio="16:9"))
    code, out, err = emit_graphic(root, "--emit", "graphic", "--graphic", "GR1")
    assert code == 0 and "graphic:wide fits it" in err and 'data-ratio="16:9"' in out
    code, out, err = emit_graphic(root, "--emit", "graphic:wide", "--graphic", "GR1")
    assert code == 0 and err == ""
    edit_brief(root, lambda b: b["graphics"][0].update(ratio="2:3"))
    code, out, err = emit_graphic(root, "--emit", "graphic:wide", "--graphic", "GR1")
    assert "graphic fits it" in err


def test_graphic_deck_clean(tmp_path):
    root = chosen_deck(tmp_path)
    assert [f for f in factory.findings(root) if f.level == "error"] == []
    assert deck.main(["check", "--project", str(root)]) == 0


def deck_edit(root, old, new):
    path = Path(root) / "pack" / "proposal.html"
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def _drop_page(root):
    path = Path(root) / "pack" / "proposal.html"
    text = path.read_text(encoding="utf-8")
    slide = next(s for s in deck_html.slides_of(deck_html.parse(text)) if s.get("data-id") == "gr1")
    path.write_text(text[:slide.start] + text[slide.end:], encoding="utf-8", newline="")


def _ratio_3_4(root):
    edit_brief(root, lambda b: b["graphics"][0].update(ratio="3:4"))
    deck_edit(root, 'data-ratio="2:3"', 'data-ratio="3:4"')


def _blocked(root):
    write(root, f"{GR}/graphic.md",
          "---\nchosen: renders/graphic-v2.png\nblocked: renders/graphic-v2.png\n---\nNotes.\n")


PLACE = {
    "figure": (lambda r: deck_edit(r, '<figure class="graphic"', '<figure class="render"'),
               [("D-PLACE", "figure")]),
    "area": (lambda r: deck_edit(r, 'data-area="top"', 'data-area="bottom"'), [("D-PLACE", "area")]),
    "ratio": (lambda r: deck_edit(r, 'data-ratio="2:3"', 'data-ratio="3:4"'), [("D-PLACE", "ratio")]),
    "role": (lambda r: deck_edit(r, 'data-role="graphic"', 'data-role="text"'),
             [("D-PLACE", "role"), ("D-STRUCT", "graphic")]),
    "no-page": (_drop_page, [("D-STRUCT", "graphic")]),
    "not-chosen": (lambda r: deck_edit(r, "graphic-v2.png", "graphic-v1.png"), [("D-IMG-RENDER", "not-chosen")]),
    "no-review": (lambda r: (Path(r) / GR / "renders" / "graphic-v2.review.json").unlink(),
                  [("D-IMG-RENDER", "review")]),
    "blocked": (_blocked, [("D-IMG-RENDER", "blocked")]),
    "stale": (_ratio_3_4, [("D-IMG-RENDER", "stale")]),
    "unlisted": (lambda r: edit_brief(r, lambda b: b.update(graphics=[])), [("D-IMG-RENDER", "unlisted")]),
}


@pytest.mark.parametrize("case", list(PLACE))
def test_graphic_place(tmp_path, case):
    root = chosen_deck(tmp_path)
    make, wants = PLACE[case]
    make(root)
    for code, rule in wants:
        assert factory.has(root, code, rule), (code, rule, [(f.code, f.message) for f in factory.findings(root)
                                                            if f.level == "error"])
    if case == "no-page":
        assert "has no page" in factory.has(root, "D-STRUCT", "graphic")[0].message


# ---------- text legibility over the artwork ----------

def _swap_art(root, data, name="graphic-v9.png"):
    """Make data the reviewed, chosen graphic of GR1 and point the page at it."""
    rel = factory.add_graphic(root, "GR1", name, data=data)
    factory.review_graphic_pass(root, rel)
    write(root, f"{GR}/graphic.md", f"---\nchosen: renders/{name}\n---\nNotes.\n")
    deck_edit(root, "graphic-v2.png", name)


def _split_art(top, bottom, split=0.4):
    """A 64x96 png whose top `split` share is one colour and the rest another."""
    import io
    from PIL import Image
    im = Image.new("RGB", (64, 96), bottom)
    im.paste(Image.new("RGB", (64, round(96 * split)), top), (0, 0))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def legibility(root):
    return factory.has(root, "D-LAYOUT", "legibility:")


def test_graphic_legible_reference_deck_has_no_warning(tmp_path):
    root = chosen_deck(tmp_path)
    assert 'data-tone="dark"' in (Path(root) / "pack" / "proposal.html").read_text(encoding="utf-8")
    assert legibility(root) == []
    assert [f for f in factory.findings(root) if f.level != "pending"] == []


def test_graphic_dark_area_with_dark_text_warns_and_names_the_other_tone(tmp_path):
    root = chosen_deck(tmp_path)
    _swap_art(root, factory.png_bytes((20, 30, 50), (64, 96)))
    hits = legibility(root)
    assert len(hits) == 1 and hits[0].level == "warn"
    assert hits[0].where.startswith("page ") and "gr1" in hits[0].where and "top area" in hits[0].message
    assert "data-tone dark" in hits[0].message and "use data-tone light" in hits[0].message
    assert [f for f in factory.findings(root) if f.level == "error"] == []
    deck_edit(root, 'data-tone="dark"', 'data-tone="light"')        # the fix the warning names
    assert legibility(root) == []


def test_graphic_light_area_with_light_text_warns_and_names_the_other_tone(tmp_path):
    root = chosen_deck(tmp_path)
    deck_edit(root, 'data-tone="dark"', 'data-tone="light"')
    hits = legibility(root)
    assert len(hits) == 1 and "data-tone light" in hits[0].message and "use data-tone dark" in hits[0].message


def test_graphic_legibility_reads_the_reserved_area_only(tmp_path):
    root = chosen_deck(tmp_path)
    _swap_art(root, _split_art((235, 235, 230), (15, 20, 30)))      # light top 40%, dark below
    assert legibility(root) == []                                    # data-area top: the light part
    deck_edit(root, 'data-area="top"', 'data-area="bottom"')
    hits = legibility(root)
    assert len(hits) == 1 and "bottom area" in hits[0].message


def test_graphic_legibility_mid_tone_neither_tone_reads(tmp_path):
    root = chosen_deck(tmp_path)
    _swap_art(root, factory.png_bytes((128, 128, 128), (64, 96)))
    assert legibility(root) == []                                    # the default tokens always give one a pass
    deck_edit(root, "--ink-strong:#121210", "--ink-strong:#707070")
    deck_edit(root, "--paper:#FAFAF7", "--paper:#909090")
    hits = legibility(root)
    assert len(hits) == 1 and "neither tone reaches it" in hits[0].message


def test_graphic_legibility_follows_the_deck_tokens(tmp_path):
    root = chosen_deck(tmp_path)
    deck_edit(root, "--ink-strong:#121210", "--ink-strong:#EEEEEE")     # the dark tone's text colour turns light
    hits = legibility(root)
    assert len(hits) == 1 and "use data-tone light" not in hits[0].message


@pytest.mark.parametrize("tone", ["bold", "Dark", ""])
def test_graphic_unknown_tone_is_an_error(tmp_path, tone):
    root = chosen_deck(tmp_path)
    deck_edit(root, 'data-tone="dark"', f'data-tone="{tone}"')
    hits = factory.has(root, "D-STRUCT", "tone:")
    if tone == "":
        assert hits == []                    # missing or empty: the template default (dark) applies
    else:
        assert len(hits) == 1 and hits[0].level == "error" and "dark, light" in hits[0].message
        assert legibility(root) == []


def test_graphic_page_without_image_is_an_error(tmp_path):
    root = chosen_deck(tmp_path)
    deck_edit(root, 'src="../graphics/GR1/renders/graphic-v2.png"', 'src="../pack/missing.png"')
    msgs = [f.message for f in factory.findings(root)]
    assert any(m.startswith("graphic: a graphic page shows no graphic render") for m in msgs)


def test_graphic_in_showcase(tmp_path):
    root = chosen_deck(tmp_path)
    edit_brief(root, lambda b: b.update(proposal={"architecture": "showcase"}))
    hits = factory.has(root, "D-IMG-FORBIDDEN", "kind:")
    assert hits and "is a graphic image" in hits[0].message
    assert not [f for f in factory.has(root, "D-STRUCT", "graphic") if f.where == "deck"]


def test_product_photo_in_deck(tmp_path):
    root = chosen_deck(tmp_path)
    deck_edit(root, "../graphics/GR1/renders/graphic-v2.png", "../input/product.png")
    hits = factory.has(root, "D-IMG-FORBIDDEN", "forbidden:")
    assert hits and "same content as input/product.png" in hits[0].message
    root = factory.deck_project(tmp_path / "second", arch="tender", graphics=True)
    rel = factory.add_graphic(root, "GR1", "graphic-v9.png", data=(root / "input" / "product.png").read_bytes())
    factory.review_graphic_pass(root, rel)
    write(root, f"{GR}/graphic.md", "---\nchosen: renders/graphic-v9.png\n---\nNotes.\n")
    deck_edit(root, "graphic-v2.png", "graphic-v9.png")
    hits = factory.has(root, "D-IMG-FORBIDDEN", "forbidden:")
    assert hits and "same content as input/product.png" in hits[0].message


def test_graphics_path_in_deck_text_is_internal(tmp_path):
    root = chosen_deck(tmp_path)
    deck_edit(root, "Portrait panel, back wall", "See graphics/GR1/renders/graphic-v2.png")
    assert factory.has(root, "D-TXT-INTERNAL", "file:")


# ---------- reports and cost ----------

def test_report_ideas_graphics(make_project, run_gates):
    root = make_project(renders=False, graphics=True)
    code, out, err = run_gates(root, "report", "ideas")
    assert code == 0, out + err
    assert "4 concepts × 2 candidates = 8 images, about 14 min" in out
    assert "1 graphic × 2 candidates = 2 images, about 4 min" in out and "1 graphics" not in out
    root = make_project(renders=False, graphics=True, arch="showcase")
    code, out, err = run_gates(root, "report", "ideas")
    assert code == 0 and "4 concepts × 2" in out and "graphics ×" not in out
    root = make_project(renders=False)
    code, out, err = run_gates(root, "report", "ideas")
    assert code == 0 and "4 concepts × 2" in out and "graphics ×" not in out


def test_report_ideas_singular_concept(make_project, run_gates):
    root = make_project(renders=False, graphics=True)
    path = str(Path(root) / "brief" / "ideas.json")
    ideas = common.read_json(path)
    for entry in ideas["sets"]:
        for row in entry["ideas"]:
            row["chosen"] = row is ideas["sets"][0]["ideas"][0]
    common.write_json(path, ideas)
    code, out, err = run_gates(root, "report", "ideas")
    assert code == 0, out + err
    assert "1 concept × 2 candidates = 2 images, about 4 min" in out and "1 concepts" not in out
    root = make_project(renders=False, graphics=True, lang="zh")
    for entry in ideas["sets"]:
        for row in entry["ideas"]:
            row["chosen"] = row is ideas["sets"][0]["ideas"][0]
    common.write_json(str(Path(root) / "brief" / "ideas.json"), ideas)
    code, out, err = run_gates(root, "report", "ideas")
    assert code == 0 and "1 个方案" in out and "1 张平面稿" in out     # zh has no plural: the same text


def test_report_ideas_graphics_zh(make_project, run_gates):
    root = make_project(renders=False, graphics=True, lang="zh")
    code, out, err = run_gates(root, "report", "ideas")
    assert code == 0 and "1 张平面稿" in out


def test_report_renders_graphics(tmp_path, run_gates):
    root = chosen_deck(tmp_path)
    code, out, err = run_gates(root, "report", "renders")
    assert code == 0, out + err
    assert "## Graphics" in out
    row = next(ln for ln in out.splitlines() if "graphic-v2.png" in ln)
    assert "GR1" in row and "✓" in row


def test_report_renders_without_graphics_has_no_section(make_project, run_gates):
    code, out, err = run_gates(make_project(renders=False), "report", "renders")
    assert code == 0 and "## Graphics" not in out


def test_area_line_may_mention_subject_elsewhere():
    """A reserved-area line may say where the subject stays, as long as it does not fill the area."""
    import render
    _fixed, data = render.load_prompt_data()
    assert "subject" not in data["area_filled_words"]
    assert "fills" in data["area_filled_words"]
