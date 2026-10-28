"""Client-term scanner (tools/scan_client_terms.py). Fictional terms only; CJK written as escapes."""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOL = str(REPO / "tools" / "scan_client_terms.py")
TERM = "Zephyr Mills"


def run(*args):
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, encoding="utf-8")


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def terms_file(root: Path, *terms: str) -> str:
    return str(write(root, "words.txt", "# fictional\n" + "\n".join(terms) + "\n"))


def _case_text(root):
    write(root, "skills/a.md", "Visit Zephyr Mills today\n")
    return run("--root", str(root), "--terms", terms_file(root, TERM), "--paths", "skills")


def _case_case(root):
    write(root, "skills/a.md", "visit zephyr mills today\n")
    return run("--root", str(root), "--terms", terms_file(root, TERM), "--paths", "skills")


def _case_cjk(root):
    write(root, "skills/a.md", "\u6211\u4eec\u7684\u4e91\u6749\u5c55\u53f0\n")
    return run("--root", str(root), "--terms", terms_file(root, "\u4e91\u6749"), "--paths", "skills")


def _case_brief(root):
    brief = {"client": {"names": [TERM]}, "protected_terms": ["Gale Card"], "do_not_mention": ["the old mill stand"]}
    write(root, "output/run-x/brief/brief.json", json.dumps(brief))
    write(root, "skills/a.md", f"{TERM}\n")
    write(root, "skills/b.md", "the Gale Card\n")
    write(root, "skills/c.md", "not the old mill stand\n")
    return run("--root", str(root), "--paths", "skills")


def _case_zip(root):
    (root / "dist").mkdir(parents=True)
    with zipfile.ZipFile(root / "dist" / "x.skill", "w") as z:
        z.writestr("booth-proposal/a.md", f"{TERM}\n")
    return run("--root", str(root), "--terms", terms_file(root, TERM), "--paths", "dist")


@pytest.mark.parametrize("case", ["text", "case", "cjk", "brief", "zip"])
def test_scan_hits(tmp_path, case):
    r = {"text": _case_text, "case": _case_case, "cjk": _case_cjk, "brief": _case_brief, "zip": _case_zip}[case](tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    if case == "text":
        assert "skills/a.md:1: Zephyr Mills" in r.stdout
    if case == "brief":
        assert "RESULT: FAIL \u2013 3 hits" in r.stdout
    if case == "zip":
        assert "dist/x.skill!booth-proposal/a.md:1" in r.stdout


@pytest.mark.parametrize("case", ["boundary", "skipped", "short"])
def test_scan_no_hit(tmp_path, case):
    if case == "boundary":
        write(tmp_path, "skills/a.md", "Zephyr\n")
        words = terms_file(tmp_path, "Zeph")
        args = ["--paths", "skills"]
    elif case == "skipped":
        for rel in ("output/x.md", "input/x.md", ".git/x.md", ".env"):
            write(tmp_path, rel, f"{TERM}\n")
        words = terms_file(tmp_path, TERM)
        args = ["--paths", "output", "input", ".git", ".env"]
    else:
        write(tmp_path, "skills/a.md", "Z\n")
        words = terms_file(tmp_path, "Z", TERM)
        args = ["--paths", "skills"]
    r = run("--root", str(tmp_path), "--terms", words, *args)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT: PASS" in r.stdout


def test_nested_input_dir_is_scanned(tmp_path):
    write(tmp_path, "skills/x/evals/c/files/input/rfp.md", f"{TERM}\n")
    write(tmp_path, "skills/x/output/y.md", f"{TERM}\n")
    r = run("--root", str(tmp_path), "--terms", terms_file(tmp_path, TERM), "--paths", "skills")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "skills/x/evals/c/files/input/rfp.md:1" in r.stdout
    assert "skills/x/output/y.md:1" in r.stdout
    assert "RESULT: FAIL \u2013 2 hits" in r.stdout


def test_nested_git_and_pycache_still_skipped(tmp_path):
    write(tmp_path, "skills/x/.git/a.md", f"{TERM}\n")
    write(tmp_path, "skills/x/__pycache__/a.md", f"{TERM}\n")
    write(tmp_path, "skills/x/node_modules/a.md", f"{TERM}\n")
    r = run("--root", str(tmp_path), "--terms", terms_file(tmp_path, TERM), "--paths", "skills")
    assert r.returncode == 0, r.stdout + r.stderr


def test_missing_path_exit2(tmp_path):
    write(tmp_path, "skills/a.md", "text\n")
    r = run("--root", str(tmp_path), "--terms", terms_file(tmp_path, TERM), "--paths", "skills", "nope")
    assert r.returncode == 2
    assert "not found" in r.stderr and "nope" in r.stderr


def test_corrupt_zip_exit2(tmp_path):
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "bad.skill").write_bytes(b"this is not a zip file")
    r = run("--root", str(tmp_path), "--terms", terms_file(tmp_path, TERM), "--paths", "dist")
    assert r.returncode == 2
    assert "bad.skill" in r.stderr


def test_no_sources_exit2(tmp_path):
    write(tmp_path, "skills/a.md", "text\n")
    r = run("--root", str(tmp_path), "--paths", "skills")
    assert r.returncode == 2
    assert "no client terms" in r.stderr


def test_repo_has_no_client_terms():
    r = run("--paths", "skills", "docs", "tests", "tools", "README.md", "CHANGELOG.md", ".claude-plugin")
    if r.returncode == 2:
        pytest.skip(r.stderr.strip())
    # never print the matched term: only the count and file:line
    places = [m.group(1) for m in re.finditer(r"^(.+?:\d+): ", r.stdout, re.M)]
    assert r.returncode == 0, f"{len(places)} client-term hits at: {', '.join(places)}"
