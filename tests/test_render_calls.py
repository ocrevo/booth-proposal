"""The API modes of render.py (phase 1, S2): hero, fix, front, --dry-run, key search, retries. No network:
render.send is always replaced (fixture fake_send or a local function), time.sleep too."""
import io
import json
import os
import urllib.error
from pathlib import Path

import pytest

import common
import factory
import render

FRONT_PROMPT = ("The same exhibition stand as in this image, same design, colours and light, every element in the "
                "same place, seen from the front: from the main aisle, nearly straight on, the whole width visible "
                "with some hall on both sides. A few visitors for scale. No other changes.")
FIX_ADD = "Remove the hanging banner; nothing else changes."
A = "concepts/set-1/A"


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


def files(root, rel):
    folder = Path(root) / rel
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


@pytest.fixture
def bare(make_project):
    """A project with concept folders and a passing hero prompt for set-1/A, but no renders yet."""
    root = make_project(renders=False)
    write(root, f"{A}/prompts/hero.txt", factory.hero_ok())
    return root


SET1 = ["input/refs/set-1/r01.png", "input/refs/set-1/r02.png"]


def hero_args(root, *extra, refs=SET1, prompt=f"{A}/prompts/hero.txt"):
    args = ["hero", "--concept", "set-1/A", "--prompt", prompt]
    for r in refs:
        args += ["--ref", r]
    return [*args, *extra]


def test_hero_writes_sidecar_v2(bare, fake_send, run):
    code, out, err = run(bare, *hero_args(bare))
    assert code == 0, out + err
    assert files(bare, f"{A}/renders") == [
        "hero-v1.json", "hero-v1.png", "hero-v1.prompt.txt", "hero-v2.json", "hero-v2.png", "hero-v2.prompt.txt"]
    assert len(fake_send.calls) == 1 and fake_send.calls[0][1]["n"] == 2
    for k in (1, 2):
        stem = bare / A / "renders" / f"hero-v{k}"
        side = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
        assert side["schema"] == "sidecar/2" and side["tool"] == "render.py" and side["mode"] == "hero"
        assert (side["set"], side["concept"]) == ("set-1", "A")
        assert side["inputs"] == [{"role": "ref", "path": r, "sha256": common.sha256_file(str(bare / r))}
                                  for r in SET1]
        assert side["outputs"] == {f"hero-v{k}.png": common.sha256_file(str(stem) + ".png")}
        assert side["prompt_sha256"] == common.sha256_file(str(stem) + ".prompt.txt")
        assert side["lint"] == {"status": "pass", "codes": []}
        assert isinstance(side["api"], dict) and side["api"]["n"] == 2
        assert side["created_at"]


@pytest.mark.parametrize("case", ["digit", "foreign_ref"])
def test_hero_refused_sends_nothing(bare, fake_send, run, case):
    refs = SET1
    if case == "digit":
        write(bare, f"{A}/prompts/bad.txt", factory.hero_ok().replace("a large screen;", "a 75-inch screen;", 1))
        args = hero_args(bare, prompt=f"{A}/prompts/bad.txt")
    else:
        args = hero_args(bare, refs=["input/refs/set-2/r01.png"])
    code, out, err = run(bare, *args)
    assert code == 1
    assert "L-BAN" in out + err if case == "digit" else "L-REF" in out + err
    assert fake_send.calls == []
    assert files(bare, f"{A}/renders") == []


@pytest.mark.parametrize("args", [["--n", "0"], ["--n", "11"]])
def test_hero_n_range(bare, fake_send, run, args):
    code, out, err = run(bare, *hero_args(bare, *args))
    assert code == 2 and "--n" in err
    assert fake_send.calls == [] and files(bare, f"{A}/renders") == []


def test_dry_run(bare, fake_send, run):
    code, out, err = run(bare, *hero_args(bare, "--dry-run"))
    assert code == 0, out + err
    assert fake_send.calls == []
    assert files(bare, f"{A}/renders") == []
    assert "images/edits" in out
    assert "ref: input/refs/set-1/" in out
    assert "would save concepts/set-1/A/renders/hero-v1.png" in out
    assert "found in the environment" in out
    assert "sk-test-SECRET" not in out + err


def test_dry_run_errors_exit_1(bare, fake_send, run):
    write(bare, f"{A}/prompts/bad.txt", factory.hero_ok().replace("a large screen;", "a 75-inch screen;", 1))
    code, out, err = run(bare, *hero_args(bare, "--dry-run", prompt=f"{A}/prompts/bad.txt"))
    assert code == 1 and "L-BAN" in out
    assert fake_send.calls == []


@pytest.fixture
def env_free(monkeypatch, tmp_path):
    """No key in the environment; HOME points at an empty folder."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


@pytest.mark.parametrize("case", ["project_root", "stops_at_git", "repo_root", "stops_at_home"])
def test_find_key(env_free, tmp_path, case):
    line = "OPENAI_API_KEY=sk-from-file\n"
    base = tmp_path / "keys"
    if case == "project_root":
        proj = base / "proj"
        write(proj, ".env", line)
        expect = (("sk-from-file", str(proj / ".env")))
    elif case == "stops_at_git":
        proj = base / "outer" / "repo" / "proj"
        proj.mkdir(parents=True)
        (base / "outer" / "repo" / ".git").mkdir()
        write(base / "outer", ".env", line)
        expect = (None, None)
    elif case == "repo_root":
        proj = base / "repo" / "proj"
        proj.mkdir(parents=True)
        (base / "repo" / ".git").mkdir()
        write(base / "repo", ".env", line)
        expect = ("sk-from-file", str(base / "repo" / ".env"))
    else:
        proj = env_free / "proj"
        proj.mkdir()
        write(tmp_path, ".env", line)
        expect = (None, None)
    key, where = render.find_key("openai", str(proj))
    assert (key, where and os.path.normcase(where)) == (expect[0], expect[1] and os.path.normcase(expect[1]))


def test_find_key_env_first(env_free, monkeypatch, tmp_path):
    write(tmp_path, ".env", "OPENAI_API_KEY=sk-from-file\n")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert render.find_key("openai", str(tmp_path)) == ("sk-from-env", "the environment")


def test_no_key_exit3(bare, env_free, monkeypatch, run, tmp_path):
    (tmp_path / ".git").mkdir()      # the search from proj<n> stops here
    calls = []
    monkeypatch.setattr(render, "send", lambda *a, **k: calls.append(a))
    code, out, err = run(bare, *hero_args(bare))
    assert code == 3 and "R-API" in err and "OPENAI_API_KEY" in err
    assert str(bare) in err               # the message names the project folder
    assert calls == [] and files(bare, f"{A}/renders") == []


@pytest.mark.parametrize("headers, want", [({"Retry-After": "7"}, 7.0), ({"Retry-After": "500"}, 120.0),
                                           ({}, 20.0), ({"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}, 20.0)],
                         ids=["seconds", "capped", "absent", "http-date"])
def test_retry_wait(headers, want):
    assert render.retry_wait(headers) == want


def http_error(code, body, headers=None):
    return urllib.error.HTTPError("https://example.invalid", code, "x", headers or {}, io.BytesIO(body.encode()))


def test_http_429_retried(bare, fake_send, run, monkeypatch):
    real_send = render.send
    state = {"n": 0}

    def flaky(*a, **k):
        state["n"] += 1
        if state["n"] == 1:
            raise http_error(429, json.dumps({"error": {"message": "slow down"}}), {"Retry-After": "7"})
        return real_send(*a, **k)

    sleeps = []
    monkeypatch.setattr(render, "send", flaky)
    monkeypatch.setattr(render.time, "sleep", sleeps.append)
    code, out, err = run(bare, *hero_args(bare, "--n", "1"))
    assert code == 0, out + err
    assert sleeps == [7.0] and "retrying in 7 s" in out
    assert files(bare, f"{A}/renders") == ["hero-v1.json", "hero-v1.png", "hero-v1.prompt.txt"]


def test_http_401_masks_key(bare, fake_send, run, monkeypatch):
    body = json.dumps({"error": {"message": "Incorrect API key provided: sk-test-SECRET", "code": "invalid_api_key"}})

    def refuse(*a, **k):
        raise http_error(401, body)

    monkeypatch.setattr(render, "send", refuse)
    monkeypatch.setattr(render.time, "sleep", lambda s: pytest.fail("a 401 is not retried"))
    code, out, err = run(bare, *hero_args(bare, "--n", "1"))
    assert code == 3 and "R-API" in err and "HTTP 401" in err
    assert "sk-test-SECRET" not in out + err
    assert files(bare, f"{A}/renders") == []


def test_numbering_counts_other_ext(bare, fake_send, run):
    write(bare, f"{A}/renders/hero-v3.jpg", "not an image, only a name")
    code, out, err = run(bare, "hero", "--concept", "set-1/A", "--prompt", f"{A}/prompts/hero.txt", "--n", "1")
    assert code == 0, out + err
    assert "hero-v4.png" in files(bare, f"{A}/renders")
    assert fake_send.calls[0][0].endswith("/images/generations")      # no --ref: the generation endpoint


@pytest.mark.parametrize("mode", ["fix", "front"])
def test_fix_and_front_outputs(project, fake_send, run, mode):
    base = f"{A}/renders/hero-v1.png"
    if mode == "fix":
        args = ["fix", "--concept", "set-1/A", "--base", base, "--add", FIX_ADD]
        want = "hero-v3.png"
    else:
        write(project, f"{A}/prompts/front.txt", FRONT_PROMPT)
        args = ["front", "--concept", "set-1/A", "--base", base, "--prompt", f"{A}/prompts/front.txt"]
        want = "front-v1.png"
    code, out, err = run(project, *args)
    assert code == 0, out + err
    assert len(fake_send.calls) == 1 and fake_send.calls[0][1]["n"] == 1
    assert fake_send.calls[0][0].endswith("/images/edits")
    side = common.read_sidecar(str(project / A / "renders" / want))
    assert side["mode"] == mode and common.sidecar_version(side) == 2
    assert side["inputs"] == [{"role": "base", "path": base, "sha256": common.sha256_file(str(project / base))}]
    proj = common.find_project(str(project))
    chain, finding = common.trace_base_chain(proj, str(project / A / "renders" / want))
    assert finding is None and chain[-1] == base


def test_fix_view_override(project, fake_send, run):
    code, out, err = run(project, "fix", "--concept", "set-1/A", "--base", f"{A}/renders/hero-v1.png",
                         "--add", FIX_ADD, "--view", "detail")
    assert code == 0, out + err
    assert "detail-v1.png" in files(project, f"{A}/renders")


def test_fix_prompt_is_linted_in_hero_mode(project, fake_send, run):
    write(project, f"{A}/prompts/orig.txt", "Make it look premium.")       # no blocks: L-BLOCKS in hero mode
    code, out, err = run(project, "fix", "--concept", "set-1/A", "--base", f"{A}/renders/hero-v1.png",
                         "--add", FIX_ADD, "--prompt", f"{A}/prompts/orig.txt")
    assert code == 1 and "L-BLOCKS" in out
    assert fake_send.calls == []


@pytest.mark.parametrize("case", ["reference", "reference_copy", "other_concept"])
def test_fix_base_refused(project, fake_send, run, case):
    if case == "reference":
        base = "input/refs/set-1/r01.png"
    elif case == "reference_copy":
        ref = "input/refs/set-1/r01.png"
        base = factory.add_render(project, "set-1/A", "hero-v9.png", refs=[ref], data=(project / ref).read_bytes())
    else:
        base = "concepts/set-1/B/renders/hero-v1.png"
    before = files(project, f"{A}/renders")
    code, out, err = run(project, "fix", "--concept", "set-1/A", "--base", base, "--add", FIX_ADD)
    assert code == 1 and "R-SOURCE" in out
    assert fake_send.calls == []
    assert files(project, f"{A}/renders") == before


@pytest.mark.parametrize("mode", ["fix", "front"])
def test_dry_run_bad_base_prints_findings_only(project, fake_send, run, mode):
    """A dry run whose base is refused shows the findings, not a request block with no base image."""
    base = "input/refs/set-1/r01.png"
    if mode == "fix":
        args = ["fix", "--concept", "set-1/A", "--base", base, "--add", FIX_ADD, "--dry-run"]
    else:
        write(project, f"{A}/prompts/front.txt", FRONT_PROMPT)
        args = ["front", "--concept", "set-1/A", "--base", base, "--prompt", f"{A}/prompts/front.txt", "--dry-run"]
    before = files(project, f"{A}/renders")
    code, out, err = run(project, *args)
    assert code == 1 and "R-SOURCE" in out
    assert "DRY RUN" not in out and "POST" not in out and "would save" not in out and "API key" not in out
    assert fake_send.calls == [] and files(project, f"{A}/renders") == before


def test_fix_max_warn(project, fake_send, run):
    th = common.find_project(str(project)).thresholds["fix_max"]
    base = f"{A}/renders/hero-v1.png"
    for k in range(3, 3 + th):
        base = factory.add_render(project, "set-1/A", f"hero-v{k}.png", mode="fix", base=base)
    code, out, err = run(project, "fix", "--concept", "set-1/A", "--base", base, "--add", FIX_ADD)
    assert code == 0, out + err
    assert "R-FIX-MAX" in out
    assert len(fake_send.calls) == 1
    assert f"hero-v{3 + th}.png" in files(project, f"{A}/renders")


def test_unknown_concept_exit_2(project, fake_send, run):
    code, out, err = run(project, "hero", "--concept", "set-9/Z", "--prompt", f"{A}/prompts/hero.txt")
    assert code == 2 and "C-INPUT" in err
    assert fake_send.calls == []
