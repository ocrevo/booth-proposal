"""Gates for the early steps of a booth proposal project.

Commands: brief [--stamp], frame, ideas [--scaffold], select, report brief|ideas.
Every command takes --project (default "."), written after the command name.
Exit codes: 0 done, 1 at least one error finding, 2 bad invocation or unusable input.
Messages are English and start with the rule name ("stale: ..."); only `report` prints text in
the project language, taken from the label file named by brief.json "lang".
Writes: `brief --stamp` -> brief/brief.json; `select` -> brief/selection.json (`--clear` deletes it);
`ideas --scaffold` -> concepts/<set>/<concept>/; `report --out` -> the named file. Nothing else.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

from common import (Finding, InputError, _CONCEPT_ID_RE, _LEGACY_SET, _SET_ID_RE, concept_ref, list_concepts,
                    load_labels, now_iso, print_findings, read_front_matter, read_json, scan_reference_sets,
                    write_json, find_project)

_BRIEF = "brief/brief.json"
_IDEAS = "brief/ideas.json"
_SIDES = ("front", "back", "left", "right")
_REPORT_KEYS = ("brief", "ideas", "renders", "concepts", "pass", "fail", "none", "cost_line")


# ---------- shared helpers ----------

def _nonempty_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _refs_shape_ok(refs) -> bool:
    """True when brief.json references has the stamped shape {sets: [{id, dir, files: [{path, sha256}]}]}."""
    if not isinstance(refs, dict) or not isinstance(refs.get("sets"), list):
        return False
    for s in refs["sets"]:
        if not (isinstance(s, dict) and isinstance(s.get("id"), str) and isinstance(s.get("dir"), str)
                and isinstance(s.get("files"), list)):
            return False
        for f in s["files"]:
            if not (isinstance(f, dict) and isinstance(f.get("path"), str) and isinstance(f.get("sha256"), str)):
                return False
    return True


def _stale(project, disk_sets: list[dict]) -> list[Finding]:
    """G-REFS stale: the sets stamped in brief.json differ from the images on disk."""
    fix = "run gates.py brief --stamp"
    refs = project.brief.get("references")
    if not _refs_shape_ok(refs):
        return [Finding("G-REFS", "error", f"{_BRIEF} references",
                        f"stale: reference sets not stamped; {fix}")]
    stamped = {s["id"]: s for s in refs["sets"]}
    disk = {s["id"]: s for s in disk_sets}
    out: list[Finding] = []
    for sid in sorted(set(stamped) | set(disk)):
        if sid not in stamped:
            out.append(Finding("G-REFS", "error", disk[sid]["dir"],
                               f"stale: set '{sid}' is on disk but not stamped; {fix}"))
            continue
        if sid not in disk:
            out.append(Finding("G-REFS", "error", stamped[sid]["dir"],
                               f"stale: set '{sid}' is stamped but not found on disk; {fix}"))
            continue
        old = {f["path"]: f["sha256"] for f in stamped[sid]["files"]}
        new = {f["path"]: f["sha256"] for f in disk[sid]["files"]}
        for path in sorted(set(old) | set(new)):
            if path not in old:
                out.append(Finding("G-REFS", "error", path, f"stale: file added since the stamp; {fix}"))
            elif path not in new:
                out.append(Finding("G-REFS", "error", path, f"stale: file removed since the stamp; {fix}"))
            elif old[path] != new[path]:
                out.append(Finding("G-REFS", "error", path, f"stale: file changed since the stamp; {fix}"))
    return out


# ---------- brief ----------

def _brief_problems(project) -> list[Finding]:
    """G-BRIEF errors for brief.json content (rules: field, id, source, dnm, labels)."""
    b = project.brief
    out: list[Finding] = []

    def add(path: str, rule: str, msg: str) -> None:
        out.append(Finding("G-BRIEF", "error", f"{_BRIEF} {path}", f"{rule}: {msg}"))

    lang = b.get("lang")
    if not _nonempty_str(lang):
        add("lang", "field", "lang must be a non-empty string")

    client = b.get("client")
    names = client.get("names") if isinstance(client, dict) else None
    if not (isinstance(names, list) and names and all(_nonempty_str(n) for n in names)):
        add("client.names", "field", "client.names must be a list of at least one non-empty string")

    for key in ("protected_terms", "do_not_mention"):
        value = b.get(key)
        if not isinstance(value, list):
            add(key, "field", f"{key} must be a list (it may be empty)")
            continue
        for i, item in enumerate(value):
            if not isinstance(item, str):
                add(f"{key}[{i}]", "field", "expected a string")
            elif key == "do_not_mention" and len(item.strip()) < 2:
                add(f"{key}[{i}]", "dnm", "entry must be at least 2 characters")

    def items(key: str, id_re: str, strs: tuple, needs_source: bool, optional: bool = False) -> None:
        value = b.get(key)
        if value is None and optional:
            return
        if not isinstance(value, list):
            add(key, "field", f"{key} must be a list" + ("" if optional else " (it may be empty)"))
            return
        pattern = re.compile(id_re)
        seen: set = set()
        for i, item in enumerate(value):
            p = f"{key}[{i}]"
            if not isinstance(item, dict):
                add(p, "field", "expected an object")
                continue
            for fld in strs:
                if not _nonempty_str(item.get(fld)):
                    add(f"{p}.{fld}", "field", f"{fld} must be a non-empty string")
            ident = item.get("id")
            if _nonempty_str(ident):
                if not pattern.fullmatch(ident):
                    add(f"{p}.id", "id", f"'{ident}' does not match {id_re}")
                elif ident in seen:
                    add(f"{p}.id", "id", f"duplicate id '{ident}'")
                else:
                    seen.add(ident)
            if needs_source:
                if "source" in item and not isinstance(item["source"], str):
                    add(f"{p}.source", "field", "source must be a string")
                elif not _nonempty_str(item.get("source")):
                    add(f"{p}.source", "source", "source is missing or blank")
            if key == "claims":
                if not isinstance(item.get("flag"), bool):
                    add(f"{p}.flag", "field", "flag must be true or false")
                if "keys" in item:
                    k = item["keys"]
                    if not (isinstance(k, list) and all(isinstance(x, str) and len(x.strip()) >= 2 for x in k)):
                        add(f"{p}.keys", "field", "keys must be a list of strings of at least 2 characters")
            if key == "assumptions" and item.get("impact") not in ("high", "low"):
                add(f"{p}.impact", "field", 'impact must be "high" or "low"')

    items("design_points", r"D\d+", ("id", "type", "text"), True)
    items("claims", r"C\d+", ("id", "text"), True)
    items("assumptions", r"A\d+", ("id", "text"), False, optional=True)

    if _nonempty_str(lang) and not project.labels:
        out.append(Finding("G-BRIEF", "error", f"assets/labels/{lang}.json",
                           "labels: no label file for the lang named in brief.json"))
    return out


def cmd_brief(project, args) -> int:
    disk_sets, scan = scan_reference_sets(project)
    if args.stamp:
        project.brief["references"] = {"sets": disk_sets, "stamped_at": now_iso()}
        write_json(project.path("brief", "brief.json"), project.brief)
        if not args.json:
            n = sum(len(s["files"]) for s in disk_sets)
            print(f"stamped {len(disk_sets)} set(s), {n} file(s) into {_BRIEF}")
    findings = _brief_problems(project) + scan + _stale(project, disk_sets)
    return print_findings(findings, args.json)


# ---------- frame ----------

def _frame_problems(project) -> list[Finding]:
    out: list[Finding] = []

    def add(path: str, msg: str) -> None:
        out.append(Finding("G-BRIEF", "error", f"{_BRIEF} {path}", f"booth: {msg}"))

    booth = project.brief.get("booth")
    if not isinstance(booth, dict):
        add("booth", "booth is missing or not an object")
        return out
    if booth.get("unit") not in ("m", "ft"):
        add("booth.unit", 'unit must be "m" or "ft"')
    for fld in ("width", "depth", "max_height"):
        v = booth.get(fld)
        if not (_is_number(v) and v > 0):
            add(f"booth.{fld}", f"{fld} must be a number greater than 0")
    sides = booth.get("open_sides")
    if not isinstance(sides, list):
        add("booth.open_sides", "open_sides must be a list")
    else:
        seen: list = []
        for i, s in enumerate(sides):
            if s not in _SIDES:
                add(f"booth.open_sides[{i}]", "open side must be one of front, back, left, right")
            elif s in seen:
                add(f"booth.open_sides[{i}]", f"duplicate open side '{s}'")
            seen.append(s)
    if not _nonempty_str(booth.get("source")):
        add("booth.source", "source must be a non-empty string")
    if "rigging_allowed" in booth and booth["rigging_allowed"] is not None \
            and not isinstance(booth["rigging_allowed"], bool):
        add("booth.rigging_allowed", "rigging_allowed must be true, false or null")
    if "program" in booth:
        prog = booth["program"]
        if not (isinstance(prog, list) and all(isinstance(x, str) for x in prog)):
            add("booth.program", "program must be a list of strings")
    return out


def cmd_frame(project, args) -> int:
    return print_findings(_frame_problems(project), args.json)


# ---------- ideas ----------

def cmd_ideas(project, args) -> int:
    ideas = read_json(project.path("brief", "ideas.json"), "ideas/1")
    refs = project.brief.get("references")
    stamped = {s["id"] for s in refs["sets"]} if _refs_shape_ok(refs) else set()
    out: list[Finding] = []

    def add(path: str, rule: str, msg: str) -> None:
        out.append(Finding("G-IDEAS", "error", f"{_IDEAS} {path}", f"{rule}: {msg}"))

    insights = ideas.get("insights")
    if not isinstance(insights, list):
        add("insights", "field", "insights must be a list (it may be empty)")
        insights = []
    seen_ids: set = set()
    for i, ins in enumerate(insights):
        p = f"insights[{i}]"
        if not isinstance(ins, dict):
            add(p, "field", "expected an object")
            continue
        ident = ins.get("id")
        if not isinstance(ident, str):
            add(f"{p}.id", "field", "id must be a string")
        elif not re.fullmatch(r"I\d+", ident):
            add(f"{p}.id", "id", f"'{ident}' does not match I\\d+")
        elif ident in seen_ids:
            add(f"{p}.id", "id", f"duplicate id '{ident}'")
        else:
            seen_ids.add(ident)
        if not _nonempty_str(ins.get("text")):
            add(f"{p}.text", "field", "text must be a non-empty string")
        source = ins.get("source", "")
        if not isinstance(source, str):
            add(f"{p}.source", "field", "source must be a string")
            source = ""
        judgement = ins.get("judgement", False)
        if not isinstance(judgement, bool):
            add(f"{p}.judgement", "field", "judgement must be true or false")
            judgement = False
        if not source.strip() and judgement is not True:
            add(f"{p}.source", "source", "an insight needs a source, or judgement true")

    sets = ideas.get("sets")
    if not isinstance(sets, list):
        add("sets", "field", "sets must be a list (it may be empty)")
        sets = []
    listed: set = set()
    idea_ids: dict = {}      # set id -> ids seen
    booth_types: dict = {}   # set id -> normalised booth_type of chosen ideas
    to_check: list = []      # (set, id, jsonpath) of chosen ideas to look up as concept folders
    for i, entry in enumerate(sets):
        p = f"sets[{i}]"
        if not isinstance(entry, dict):
            add(p, "field", "expected an object")
            continue
        sid = entry.get("set")
        set_ok = False
        if not isinstance(sid, str):
            add(f"{p}.set", "field", "set must be a string")
        elif sid not in stamped:
            add(f"{p}.set", "set", f"'{sid}' is not a stamped reference set; run gates.py brief --stamp")
        else:
            set_ok = True
            if sid in listed:
                add(f"{p}.set", "set", f"'{sid}' is listed more than once")
            listed.add(sid)
        entry_ideas = entry.get("ideas")
        if not isinstance(entry_ideas, list):
            add(f"{p}.ideas", "field", "ideas must be a list")
            continue
        for j, idea in enumerate(entry_ideas):
            q = f"{p}.ideas[{j}]"
            if not isinstance(idea, dict):
                add(q, "field", "expected an object")
                continue
            ok = True
            for fld in ("id", "name", "idea", "booth_type"):
                if not isinstance(idea.get(fld), str):
                    add(f"{q}.{fld}", "field", f"{fld} must be a string")
                    ok = False
            if not isinstance(idea.get("chosen"), bool):
                add(f"{q}.chosen", "field", "chosen must be true or false")
                ok = False
            id_ok = False
            ident = idea.get("id")
            if isinstance(ident, str):
                seen = idea_ids.setdefault(sid if isinstance(sid, str) else None, set())
                if not _CONCEPT_ID_RE.fullmatch(ident):
                    add(f"{q}.id", "id", f"'{ident}' is not a valid concept id")
                elif ident in seen:
                    add(f"{q}.id", "id", f"duplicate id '{ident}' in this set")
                else:
                    id_ok = True
                seen.add(ident)
            if not ok or idea.get("chosen") is not True:
                continue
            if isinstance(sid, str):
                norm = " ".join(idea["booth_type"].lower().split())
                prior = booth_types.setdefault(sid, {})
                if norm in prior:
                    add(f"{q}.booth_type", "same-type",
                        f"same booth_type as chosen idea '{prior[norm]}' of this set")
                else:
                    prior[norm] = ident
            if set_ok and id_ok and (_SET_ID_RE.fullmatch(sid) or sid == _LEGACY_SET) \
                    and not any(c[:2] == (sid, ident) for c in to_check):
                to_check.append((sid, ident, f"{q}.id"))

    existing = {c.key for c in list_concepts(project)}
    for sid, ident, path in to_check:
        if f"{sid}/{ident}" in existing:
            continue
        folder = project.path("concepts", sid, ident)
        if args.scaffold:
            renders = os.path.join(folder, "renders")
            os.makedirs(renders, exist_ok=True)
            if not args.json:
                print(f"created {project.rel(renders)}")
            md = os.path.join(folder, "concept.md")
            if not os.path.exists(md):
                with open(md, "w", encoding="utf-8", newline="\n") as f:
                    f.write("---\n---\n")
                if not args.json:
                    print(f"created {project.rel(md)}")
        else:
            add(path, "folder",
                f"chosen idea has no concept folder concepts/{sid}/{ident}/; run gates.py ideas --scaffold")

    out += _stale(project, scan_reference_sets(project)[0])
    return print_findings(out, args.json)


# ---------- select ----------

def cmd_select(project, args) -> int:
    sel_path = project.path("brief", "selection.json")
    if args.show:
        if project.selection is None:
            print("no brief/selection.json yet")
        else:
            print(json.dumps(project.selection, ensure_ascii=False, indent=2))
        return 0
    if args.clear:
        if os.path.exists(sel_path):
            os.remove(sel_path)
            print("removed brief/selection.json")
        else:
            print("no brief/selection.json")
        return 0

    keys = list(args.keys)
    findings: list[Finding] = []
    known = []
    for k in keys:
        try:
            known.append(concept_ref(project, k))
        except InputError as e:
            findings.append(Finding("G-SELECT", "error", k, f"unknown: {e}"))
    if args.lead is not None and args.lead not in keys:
        findings.append(Finding("G-SELECT", "error", args.lead, "lead: --lead is not among the selected keys"))
    for ref in known:
        findings += read_front_matter(ref)[1]
    findings += _stale(project, scan_reference_sets(project)[0])
    if any(f.level == "error" for f in findings):
        return print_findings(findings)

    write_json(sel_path, {
        "schema": "selection/1",
        "selected": keys,
        "lead": args.lead or None,
        "display": {k: chr(ord("A") + i) for i, k in enumerate(keys)},
        "updated_at": now_iso(),
    })
    shown = ", ".join(f"{chr(ord('A') + i)}={k}" for i, k in enumerate(keys))
    print(f"wrote brief/selection.json: {shown}" + (f" (lead {args.lead})" if args.lead else ""))
    return 0


# ---------- report ----------

def _cell(v) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _table(headers: list[str], rows: list[dict], none: str) -> list[str]:
    if not rows:
        return [none]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(_cell(r[h] if h in r else "") for h in headers) + " |")
    return lines


def _dicts(value) -> list[dict]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _report_labels(project) -> dict:
    labels = load_labels(project.lang)
    rep = labels.get("report")
    missing = [k for k in _REPORT_KEYS if not (isinstance(rep, dict) and isinstance(rep.get(k), str))]
    if missing:
        raise InputError("C-INPUT", f"assets/labels/{project.lang}.json report",
                         "missing report label key: " + ", ".join(missing))
    return rep


def _report_brief(project, L: dict) -> list[str]:
    b = project.brief
    none = L["none"]
    lines = [f"# {L['brief']}", "", "## design_points", ""]
    lines += _table(["id", "type", "text", "source"], _dicts(b.get("design_points")), none)
    lines += ["", "## assumptions", ""]
    lines += _table(["id", "text", "impact"], [a for a in _dicts(b.get("assumptions")) if a.get("impact") == "high"], none)
    lines += ["", "## claims", ""]
    lines += _table(["id", "text", "source"], [c for c in _dicts(b.get("claims")) if c.get("flag") is True], none)
    return lines


def _report_ideas(project, L: dict) -> list[str]:
    ideas = read_json(project.path("brief", "ideas.json"), "ideas/1")
    none = L["none"]
    lines = [f"# {L['ideas']}", "", "## insights", ""]
    lines += _table(["id", "text", "source", "judgement"], _dicts(ideas.get("insights")), none)
    chosen = 0
    for entry in _dicts(ideas.get("sets")):
        rows = _dicts(entry.get("ideas"))
        chosen += sum(1 for r in rows if r.get("chosen") is True)
        lines += ["", f"## {_cell(entry.get('set', ''))}", ""]
        lines += _table(["id", "name", "idea", "booth_type", "chosen"], rows, none)
    per = project.thresholds["candidates_per_concept"]
    minutes = math.ceil(chosen * per * project.thresholds["seconds_per_image"] / 60)
    lines += ["", L["cost_line"].format(concepts=chosen, per=per, images=chosen * per, minutes=minutes)]
    return lines


def cmd_report(project, args) -> int:
    L = _report_labels(project)
    lines = _report_brief(project, L) if args.what == "brief" else _report_ideas(project, L)
    text = "\n".join(lines) + "\n"
    if args.out:
        folder = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(folder, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


# ---------- entry point ----------

def _build_parser():
    ap = argparse.ArgumentParser(description="Booth proposal gates: brief, frame, ideas, select, report")
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=".", help="project folder (default: current folder)")

    p = sub.add_parser("brief", parents=[common], help="validate brief.json and the reference sets")
    p.add_argument("--stamp", action="store_true", help="rewrite brief.json references from disk first")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("frame", parents=[common], help="validate the booth block of brief.json")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("ideas", parents=[common], help="validate ideas.json")
    p.add_argument("--scaffold", action="store_true", help="create folders for chosen ideas that have none")
    p.add_argument("--json", action="store_true")

    sel = sub.add_parser("select", parents=[common], help="choose the concepts to develop")
    sel.add_argument("keys", nargs="*", metavar="KEY", help="<set>/<concept>, in display order")
    sel.add_argument("--lead", metavar="KEY", help="the lead concept (one of the keys)")
    sel.add_argument("--show", action="store_true", help="print brief/selection.json")
    sel.add_argument("--clear", action="store_true", help="delete brief/selection.json")

    p = sub.add_parser("report", parents=[common], help="Markdown summary for the user")
    p.add_argument("what", choices=["brief", "ideas"])
    p.add_argument("--out", metavar="FILE", help="write the Markdown to this file")
    return ap, sel


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    ap, sel = _build_parser()
    args = ap.parse_args(argv)
    if args.cmd == "select":
        modes = int(bool(args.keys)) + int(args.show) + int(args.clear)
        if modes != 1:
            sel.error("give exactly one of: KEY [KEY ...], --show, --clear")
        if args.lead is not None and not args.keys:
            sel.error("--lead only goes with KEY arguments")
        if len(set(args.keys)) != len(args.keys):
            sel.error("duplicate keys")
        if len(args.keys) > 26:
            sel.error("at most 26 keys")
    try:
        project = find_project(args.project)
        return globals()[f"cmd_{args.cmd}"](project, args)
    except InputError as e:
        print(f"{'ERROR':<7} {e.code:<18} {e.where}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
