#!/usr/bin/env python3
"""Deterministic checks for the eval cases of the booth-proposal skill.

Usage: python tools/eval_grade.py --case NAME --workspace DIR [--checks FILE] [--baseline DIR]
  --checks FILE    checks file (default: tools/eval_checks.json); meant for tests
  --baseline DIR   folder holding the fixture files for 'unchanged' (default: the case's files/); meant for tests

Reads tools/eval_checks.json ({"schema": "eval-checks/1", "cases": {"<case>": [check, ...]}}) and runs every check of
the case against a workspace (the folder a run worked in). Output: one line 'PASS|FAIL <id> \u2013 <evidence>' per check,
then 'RESULT: <passed>/<total>'. Exit 0 all pass, 1 any fail, 2 unknown case, unknown type, bad check or missing
workspace. Nothing is written outside the workspace (deck.py check --json writes work/check.json inside it).

Check types: exists, absent, command, json_equals, check_clean, text, pack_only, unchanged, lint_all, geometry_all.
argv placeholders: {py} = this Python, {scripts} = the skill's scripts folder, {ws} = the workspace.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "skills", "booth-proposal")
SCRIPTS = os.path.join(SKILL, "scripts")
CHECKS_DEFAULT = os.path.join(REPO, "tools", "eval_checks.json")
PACK_ALLOWED = {"proposal.html", "proposal.pdf", "site.svg"}
TYPES = ("exists", "absent", "command", "json_equals", "check_clean", "text", "pack_only", "unchanged", "lint_all",
         "geometry_all")
REQUIRED = {
    "exists": ("path",), "absent": ("path",), "command": ("argv", "exit"), "json_equals": ("path", "key", "value"),
    "check_clean": (), "text": (), "pack_only": (), "unchanged": ("path",), "lint_all": ("glob",),
    "geometry_all": ("glob",),
}
TIMEOUT = 180


class BadInput(Exception):
    """Unknown case, unknown type, malformed check or missing workspace: exit 2."""


def _short(s: str, n: int = 160) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 3] + "..."


def _rel(path: str, ws: str) -> str:
    return os.path.relpath(path, ws).replace(os.sep, "/")


def _glob(ws: str, pattern: str) -> list[str]:
    """Workspace-relative matches of a glob (recursive '**'), forward slashes, sorted."""
    hits = glob.glob(os.path.join(glob.escape(ws), pattern), recursive=True)
    return sorted(_rel(h, ws) for h in hits)


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(argv: list[str], ws: str) -> tuple[int, str, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("OPENAI_API_KEY", None)           # a check must never be able to spend money
    try:
        p = subprocess.run(argv, cwd=ws, capture_output=True, env=env, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {TIMEOUT}s"
    except OSError as e:
        return 127, "", str(e)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def _skill(script: str, *args: str) -> list[str]:
    return [sys.executable, os.path.join(SCRIPTS, script), *args]


def _codes(node, found: list) -> list:
    """Every value of a 'code' key in a parsed JSON document, in order, without repeats."""
    if isinstance(node, dict):
        if isinstance(node.get("code"), str) and node["code"] not in found:
            found.append(node["code"])
        for v in node.values():
            _codes(v, found)
    elif isinstance(node, list):
        for v in node:
            _codes(v, found)
    return found


def _first_line(out: str, err: str) -> str:
    """Evidence for a failed command: finding codes when stdout is JSON, else the first line with words in it."""
    try:
        codes = _codes(json.loads(out), [])
    except ValueError:
        codes = []
    if codes:
        return "codes " + ", ".join(codes[:6])
    for text in (err, out):
        lines = [x.strip() for x in text.splitlines()]
        for line in lines:
            if line.startswith("ERROR") or line.startswith("error"):
                return line
    for text in (err, out):
        for line in text.splitlines():
            if re.search(r"[A-Za-z]{3}", line):
                return line.strip()
    return ""


# ---------------------------------------------------------------- the check types
# each returns (ok, evidence)

def c_exists(ck, ws, ctx):
    hits = _glob(ws, ck["path"])
    return bool(hits), (f"{len(hits)} match(es): {', '.join(hits[:3])}" if hits else f"no match for {ck['path']}")


def c_absent(ck, ws, ctx):
    hits = _glob(ws, ck["path"])
    return not hits, (f"no match for {ck['path']}" if not hits else f"found {', '.join(hits[:3])}")


def c_command(ck, ws, ctx):
    argv = [a.replace("{py}", sys.executable).replace("{scripts}", SCRIPTS).replace("{ws}", ws) for a in ck["argv"]]
    want = [int(x) for x in ck["exit"]]
    code, out, err = _run(argv, ws)
    ok = code in want
    line = _first_line(out, err)
    return ok, f"exit {code}, want {want}" + (f"; {_short(line, 110)}" if line and not ok else "")


def _dig(data, key: str):
    cur = data
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.lstrip("-").isdigit() and -len(cur) <= int(part) < len(cur):
            cur = cur[int(part)]
        else:
            raise KeyError(key)
    return cur


def c_json_equals(ck, ws, ctx):
    hits = _glob(ws, ck["path"])
    if not hits:
        return False, f"missing {ck['path']}"
    try:
        with open(os.path.join(ws, hits[0]), "rb") as f:
            data = json.loads(f.read().decode("utf-8-sig"))
    except (OSError, ValueError) as e:
        return False, f"{hits[0]} is not readable JSON ({_short(e, 60)})"
    try:
        got = _dig(data, ck["key"])
    except KeyError:
        return False, f"{hits[0]} has no key {ck['key']}"
    ok = got == ck["value"]
    return ok, f"{hits[0]} {ck['key']} = {_short(json.dumps(got, ensure_ascii=False), 80)}" + \
        ("" if ok else f", want {_short(json.dumps(ck['value'], ensure_ascii=False), 80)}")


def _deck_check(ws):
    code, out, err = _run(_skill("deck.py", "check", "--json", "--project", ws), ws)
    try:
        return json.loads(out), None
    except ValueError:
        return None, f"deck.py check --json gave no JSON (exit {code}): {_short(_first_line(out, err), 100)}"


def c_check_clean(ck, ws, ctx):
    data, problem = _deck_check(ws)
    if problem:
        return False, problem
    errors = (data.get("counts") or {}).get("error")
    found = sorted({f.get("code") for f in data.get("findings", []) if f.get("code") in set(ck.get("codes") or [])})
    problems = []
    if errors != 0:
        codes = sorted({f.get("code") for f in data.get("findings", []) if f.get("level") == "error"})
        problems.append(f"{errors} error(s): {', '.join(codes)}")
    if found:
        problems.append("forbidden code(s): " + ", ".join(found))
    return not problems, "; ".join(problems) if problems else "0 errors" + \
        (f", none of {', '.join(ck['codes'])}" if ck.get("codes") else "")


def _norm(s: str) -> str:
    return " ".join(s.split())


def c_text(ck, ws, ctx):
    if "deck_text" not in ctx:
        code, out, err = _run(_skill("deck.py", "text", "--project", ws), ws)
        ctx["deck_text"] = (code, out, err)
    code, out, err = ctx["deck_text"]
    if code != 0:
        return False, f"deck.py text exit {code}: {_short(_first_line(out, err), 100)}"
    text = _norm(out)
    still = [s for s in ck.get("absent", []) if _norm(s) in text]
    missing = [s for s in ck.get("present", []) if _norm(s) not in text]
    problems = []
    if still:
        problems.append("still in the deck: " + "; ".join(_short(s, 50) for s in still))
    if missing:
        problems.append("missing from the deck: " + "; ".join(_short(s, 50) for s in missing))
    n = len(ck.get("absent", [])) + len(ck.get("present", []))
    return not problems, "; ".join(problems) if problems else f"{n} string(s) as wanted"


def c_pack_only(ck, ws, ctx):
    folder = os.path.join(ws, "pack")
    if not os.path.isdir(folder):
        return True, "no pack/ folder"
    extra = sorted(set(os.listdir(folder)) - PACK_ALLOWED)
    return not extra, ("pack/ holds only deliverables" if not extra else "unexpected in pack/: " + ", ".join(extra[:5]))


def c_unchanged(ck, ws, ctx):
    now = os.path.join(ws, ck["path"])
    base = os.path.join(ctx["baseline"], ck["path"])
    if not os.path.isfile(base):
        return False, f"no baseline file {ck['path']}"
    if not os.path.isfile(now):
        return False, f"missing in workspace: {ck['path']}"
    same = _sha(now) == _sha(base)
    return same, f"{ck['path']} {'identical to' if same else 'differs from'} the fixture"


def _each(ck, ws, make_argv):
    files = [f for f in _glob(ws, ck["glob"]) if os.path.isfile(os.path.join(ws, f))]
    if not files:
        return False, f"no file matches {ck['glob']}"
    bad = []
    for f in files:
        argv = make_argv(f)
        if argv is None:
            bad.append(f"{f} (not under concepts/<set>/<concept>/)")
            continue
        code, out, err = _run(argv, ws)
        if code != 0:
            bad.append(f"{f} (exit {code}: {_short(_first_line(out, err), 60)})")
    return not bad, (f"{len(files)} file(s) pass" if not bad else "; ".join(bad[:3]))


def c_lint_all(ck, ws, ctx):
    def make(f):
        parts = f.split("/")
        if len(parts) < 5 or parts[0] != "concepts":
            return None
        return _skill("render.py", "lint", "--mode", "hero", "--prompt", f, "--concept", f"{parts[1]}/{parts[2]}",
                      "--project", ws)
    return _each(ck, ws, make)


def c_geometry_all(ck, ws, ctx):
    # the geometry-only cases have no brief/; booth_geometry.py then runs without --project
    project = ["--project", ws] if os.path.isdir(os.path.join(ws, "brief")) else []
    return _each(ck, ws, lambda f: _skill("booth_geometry.py", "check", f, *project))


RUNNERS = {
    "exists": c_exists, "absent": c_absent, "command": c_command, "json_equals": c_json_equals,
    "check_clean": c_check_clean, "text": c_text, "pack_only": c_pack_only, "unchanged": c_unchanged,
    "lint_all": c_lint_all, "geometry_all": c_geometry_all,
}


# ---------------------------------------------------------------- driver

def load_checks(path: str, case: str) -> list[dict]:
    try:
        with open(path, "rb") as f:
            data = json.loads(f.read().decode("utf-8-sig"))
    except (OSError, ValueError) as e:
        raise BadInput(f"cannot read {path}: {e}")
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, dict) or data.get("schema") != "eval-checks/1":
        raise BadInput(f"{path} is not an eval-checks/1 file")
    if case not in cases:
        raise BadInput(f"unknown case {case!r}; known: {', '.join(sorted(cases))}")
    checks = cases[case]
    if not isinstance(checks, list) or not checks:
        raise BadInput(f"case {case!r} has no checks")
    for i, ck in enumerate(checks, 1):
        if not isinstance(ck, dict) or not isinstance(ck.get("id"), str):
            raise BadInput(f"check {i} of {case!r} has no id")
        if ck.get("type") not in TYPES:
            raise BadInput(f"{ck['id']}: unknown type {ck.get('type')!r}")
        miss = [k for k in REQUIRED[ck["type"]] if k not in ck]
        if miss:
            raise BadInput(f"{ck['id']}: missing field(s) {', '.join(miss)}")
    return checks


def grade(case: str, workspace: str, checks_path: str = CHECKS_DEFAULT, baseline: str | None = None):
    """Returns (lines, passed, total). Raises BadInput for exit-2 problems."""
    checks = load_checks(checks_path, case)
    ws = os.path.abspath(workspace)
    if not os.path.isdir(ws):
        raise BadInput(f"workspace {workspace} is not a folder")
    ctx = {"baseline": os.path.abspath(baseline) if baseline else os.path.join(SKILL, "evals", case, "files")}
    lines, passed = [], 0
    for ck in checks:
        try:
            ok, evidence = RUNNERS[ck["type"]](ck, ws, ctx)
        except Exception as e:  # noqa: BLE001 - a crashing check is a failed check, not a crashed grader
            ok, evidence = False, f"check crashed: {_short(e, 100)}"
        passed += bool(ok)
        lines.append(f"{'PASS' if ok else 'FAIL'} {ck['id']} \u2013 {evidence}")
    return lines, passed, len(checks)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Run the deterministic checks of an eval case against a workspace")
    ap.add_argument("--case", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--checks", default=CHECKS_DEFAULT,
                    help="checks file (default: tools/eval_checks.json); a test option")
    ap.add_argument("--baseline", help="folder holding the fixture files for 'unchanged' "
                                        "(default: skills/booth-proposal/evals/<case>/files); a test option")
    a = ap.parse_args(argv)
    try:
        lines, passed, total = grade(a.case, a.workspace, a.checks, a.baseline)
    except BadInput as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    print(f"RESULT: {passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
