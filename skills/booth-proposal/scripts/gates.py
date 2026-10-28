"""Gates for the early steps of a booth proposal project.

Commands: brief [--stamp], frame, ideas [--scaffold], select, renders, concepts, architectures [--json],
report brief|ideas|renders|concepts.
Every command takes --project (default "."), written after the command name.
Exit codes: 0 done, 1 at least one error finding, 2 bad invocation or unusable input.
Messages are English and start with the rule name ("stale: ..."); only `report` prints text in
the project language, taken from the label file named by brief.json "lang".
Writes: `brief --stamp` -> brief/brief.json; `select` -> brief/selection.json (`--clear` deletes it);
`ideas --scaffold` -> concepts/<set>/<concept>/; `report --out` -> the named file. Nothing else
(`concepts` only reads, and only the selected concepts).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

from common import (CLAUSE_KINDS, CLAUSE_N_RE, DEFAULTS, Finding, InputError, _CONCEPT_ID_RE, _LEGACY_SET,
                    _SET_ID_RE, _images_in, architecture_choice, concept_ref, find_project, inside, list_concepts,
                    load_architectures, load_labels, now_iso, print_findings, read_front_matter, read_json,
                    read_review, read_sidecar, real, required_chapters, review_is_current_pass, scan_reference_sets,
                    sha256_file, sidecar_version, to_m, trace_base_chain, write_json)

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


def _reference_findings(project, disk_sets: list[dict], scan: list[Finding]) -> list[Finding]:
    """The reference-set findings shared by `brief` and `renders`: scan findings (G-REFS, C-LEGACY) + stale."""
    return scan + _stale(project, disk_sets)


# ---------- brief ----------

def _ids_of(brief: dict, key: str) -> set:
    v = brief.get(key)
    return {i["id"] for i in v if isinstance(i, dict) and isinstance(i.get("id"), str)} if isinstance(v, list) \
        else set()


def _proposal_problems(project, add, out) -> None:
    """proposal.architecture of brief.json and thresholds.architecture of deck-style.json (rule: field, architecture)."""
    reg = load_architectures()

    def unknown(v):
        return f"unknown architecture '{v}'; known: {', '.join(sorted(reg))}; run gates.py architectures"

    proposal = project.brief.get("proposal")
    if proposal is not None:
        if not isinstance(proposal, dict):
            add("proposal", "field", "proposal must be an object")
        elif "architecture" in proposal:
            v = proposal["architecture"]
            if not _nonempty_str(v):
                add("proposal.architecture", "field", "architecture must be a non-empty string")
            elif v.strip() not in reg:
                add("proposal.architecture", "architecture", unknown(v.strip()))
    th = project.style.get("thresholds")
    if isinstance(th, dict) and isinstance(th.get("architecture"), str) and th["architecture"] not in reg:
        out.append(Finding("G-BRIEF", "error", "brief/deck-style.json thresholds.architecture",
                           "architecture: " + unknown(th["architecture"])))


def _clause_problems(project, add) -> None:
    """clauses[] of brief.json (rule: field, clause-n, clause-kind, points, source)."""
    b = project.brief
    value = b.get("clauses")
    if value is None:
        return
    if not isinstance(value, list):
        add("clauses", "field", "clauses must be a list")
        return
    points = _ids_of(b, "design_points")
    seen: set = set()
    for i, item in enumerate(value):
        p = f"clauses[{i}]"
        if not isinstance(item, dict):
            add(p, "field", "expected an object")
            continue
        n = item.get("n")
        if not isinstance(n, str):
            add(f"{p}.n", "field", 'n must be a string such as "2" or "8.1"')
        elif not CLAUSE_N_RE.fullmatch(n):
            add(f"{p}.n", "clause-n", f"'{n}' is not a clause number such as 2, 8.1 or 3a")
        elif n in seen:
            add(f"{p}.n", "clause-n", f"duplicate clause number '{n}'")
        else:
            seen.add(n)
        if not _nonempty_str(item.get("text")):
            add(f"{p}.text", "field", "text must be a non-empty string")
        if "source" in item and not isinstance(item["source"], str):
            add(f"{p}.source", "field", "source must be a string")
        elif not _nonempty_str(item.get("source")):
            add(f"{p}.source", "source", "source is missing or blank")
        if item.get("kind") not in CLAUSE_KINDS:
            add(f"{p}.kind", "clause-kind", "kind must be one of " + ", ".join(CLAUSE_KINDS))
        pts = item.get("points", [])
        if not (isinstance(pts, list) and all(isinstance(x, str) for x in pts)):
            add(f"{p}.points", "field", "points must be a list of design point ids")
        else:
            for j, x in enumerate(pts):
                if x not in points:
                    add(f"{p}.points[{j}]", "points", f"'{x}' is not a design point id")


def _graphic_ref_ok(project, ref: str) -> bool:
    if "\\" in ref or ref.startswith("/") or re.match(r"[A-Za-z]:", ref):
        return False
    parts = ref.split("/")
    if len(parts) < 2 or parts[0] != "input" or any(x in ("", ".", "..") for x in parts):
        return False
    full = project.path(*parts)
    return os.path.isfile(full) and inside(project.path("input"), full)


def _graphic_problems(project, add) -> None:
    """graphics[] beyond the shared item rules (rule: ratio, graphic-ref, content, field)."""
    value = project.brief.get("graphics")
    if not isinstance(value, list):
        return
    claims = _ids_of(project.brief, "claims")
    for i, item in enumerate(value):
        p = f"graphics[{i}]"
        if not isinstance(item, dict):
            continue
        ratio = item.get("ratio")
        if isinstance(ratio, str) and ratio.strip() and not re.fullmatch(r"\d+(\.\d+)?:\d+(\.\d+)?", ratio):
            add(f"{p}.ratio", "ratio", "ratio must look like 2:3 or 16:9")
        refs = item.get("refs", [])
        if not (isinstance(refs, list) and all(isinstance(x, str) for x in refs)):
            add(f"{p}.refs", "field", "refs must be a list of paths")
        else:
            for j, ref in enumerate(refs):
                if not _graphic_ref_ok(project, ref):
                    add(f"{p}.refs[{j}]", "graphic-ref", f"'{ref}' must name an existing file inside input/")
        content = item.get("content", [])
        if not (isinstance(content, list) and all(isinstance(x, str) for x in content)):
            add(f"{p}.content", "field", "content must be a list of claim ids")
        else:
            for j, x in enumerate(content):
                if x not in claims:
                    add(f"{p}.content[{j}]", "content", f"'{x}' is not a claim id")


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
    items("graphics", r"GR\d+", ("id", "title", "purpose", "ratio"), False, optional=True)
    _proposal_problems(project, add, out)
    _clause_problems(project, add)
    _graphic_problems(project, add)

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
    findings = _brief_problems(project) + _reference_findings(project, disk_sets, scan)
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


# ---------- renders ----------

def _own_set_hashes(project, set_id: str) -> set[str]:
    """The stamped sha256 values of the reference set a concept belongs to (empty when not stamped)."""
    refs = project.brief.get("references")
    if not _refs_shape_ok(refs):
        return set()
    return {f["sha256"] for s in refs["sets"] if s["id"] == set_id for f in s["files"]}


def _chain_ref_hashes(project, chain: list[str]) -> list[tuple[str, str, str]]:
    """(chain step, ref path, sha256) of every reference input along a base chain. A v2 sidecar records the
    hash; an old sidecar lists input_images, hashed now (files under concepts/ are bases, not references)."""
    out: list[tuple[str, str, str]] = []
    for step in chain:
        sc = read_sidecar(project.path(step))
        ver = sidecar_version(sc)
        if ver == 2:
            inputs = sc.get("inputs")
            for i in inputs if isinstance(inputs, list) else []:
                if isinstance(i, dict) and i.get("role") == "ref" and isinstance(i.get("sha256"), str):
                    out.append((step, str(i.get("path", "")), i["sha256"]))
        elif ver == 1:
            imgs = sc.get("input_images")
            for p in imgs if isinstance(imgs, list) else []:
                if not isinstance(p, str):
                    continue
                p = p.replace("\\", "/")
                if p.startswith("concepts/"):
                    continue
                try:
                    out.append((step, p, sha256_file(os.path.join(project.root, p))))
                except OSError:
                    continue
    return out


def _concept_render_findings(project, c) -> list[Finding]:
    """G-FM, G-RENDER, G-REVIEW, R-FIX-MAX and C-LEGACY for one concept folder."""
    fm, fm_findings = read_front_matter(c)
    if fm_findings:
        return fm_findings
    if not _images_in(os.path.join(c.dir, "renders")):
        return []
    md = f"concepts/{c.set}/{c.id}/concept.md"
    if fm["chosen"] is None:
        return [Finding("G-RENDER", "error", md, "nochosen: the concept has renders but concept.md names no chosen one")]
    image = os.path.normpath(os.path.join(c.dir, fm["chosen"]))
    rel = project.rel(image)
    out: list[Finding] = []

    def add(code: str, level: str, message: str, where: str = rel) -> None:
        out.append(Finding(code, level, where, message))

    if real(image) in {real(os.path.join(c.dir, b)) for b in fm["blocked"]}:
        add("G-RENDER", "error", "blocked: the chosen render is also listed as blocked in concept.md")
    sc = read_sidecar(image)
    ver = sidecar_version(sc)
    outputs = sc.get("outputs") if ver == 2 else None
    if ver == 0:
        add("G-RENDER", "error", "sidecar: the chosen render has no usable sidecar; re-render or re-import")
    elif ver == 2 and not (isinstance(outputs, dict) and outputs.get(os.path.basename(image)) == sha256_file(image)):
        add("G-RENDER", "error", "sidecar: image changed after it was written; re-render or re-import")
    else:
        chain, finding = trace_base_chain(project, image)
        if finding is not None:
            out.append(finding._replace(code="G-RENDER"))
        else:
            own = _own_set_hashes(project, c.set)
            seen: set = set()
            for step, path, digest in _chain_ref_hashes(project, chain):
                if digest not in own and digest not in seen:
                    seen.add(digest)
                    add("G-RENDER", "error",
                        f"refset: reference input {path or digest[:12]} is not a photo of set {c.set}", step)
            fixes = sum(1 for step in chain if (read_sidecar(project.path(step)) or {}).get("mode") == "fix")
            fix_max = project.thresholds["fix_max"]
            if fixes > fix_max:
                add("R-FIX-MAX", "warn",
                    f"fix-max: the base chain has {fixes} fixes (fix_max {fix_max}); a new hero may serve better")
            if sidecar_version(read_sidecar(project.path(chain[-1]))) == 1:
                add("C-LEGACY", "warn", "legacy: the base chain ends at an image with an old sidecar", chain[-1])
    ok, reason = review_is_current_pass(image, True)
    if not ok:
        add("G-REVIEW", "error", reason)
    return out


def cmd_renders(project, args) -> int:
    keys = list(dict.fromkeys(k for group in (args.concept or []) for k in group))
    concepts = [concept_ref(project, k) for k in keys] if keys else list_concepts(project)
    findings = _reference_findings(project, *scan_reference_sets(project))
    for c in concepts:
        findings += _concept_render_findings(project, c)
    return print_findings(findings, args.json)


# ---------- concepts ----------

def _concept_geo_findings(project, c, booth_ok: bool) -> list[Finding]:
    """G-GEO findings for one selected concept: missing | invalid, check, envelope, plan, stale."""
    import booth_geometry      # imported late: it needs only the standard library and common

    out: list[Finding] = []

    def add(message: str) -> None:
        out.append(Finding("G-GEO", "error", c.key, message))

    spec_path = os.path.join(c.dir, "geometry.json")
    spec_rel = project.rel(spec_path)
    outbase = f"concepts/{c.set}/{c.id}/plan"
    spec = None
    if not os.path.isfile(spec_path):
        add(f"missing: no {spec_rel}")
    else:
        try:
            spec, found = booth_geometry.load_spec(spec_path)
        except InputError as e:
            spec, found = None, [Finding(e.code, "error", e.where, str(e))]
        if found:
            paths = "; ".join(f"{f.where} {f.message}" for f in found)
            add(f"invalid: {paths}; run booth_geometry.py check {spec_rel}")
    if spec is not None:
        errors = [f for f in booth_geometry.problems(spec, project.thresholds) if f.level == "error"]
        if errors:
            codes = ", ".join(sorted({f.code for f in errors}))
            add(f"check: {len(errors)} error(s) ({codes}); run booth_geometry.py check {spec_rel}")
        if booth_ok:
            for msg in _envelope_messages(project, spec):
                add(f"envelope: {msg}")

    plan_json = os.path.join(c.dir, "plan.json")
    has_json = os.path.isfile(plan_json)
    has_image = os.path.isfile(os.path.join(c.dir, "plan.png")) or os.path.isfile(os.path.join(c.dir, "plan.svg"))
    gone = [name for name, ok in (("plan.json", has_json), ("plan.png or plan.svg", has_image)) if not ok]
    if gone:
        add(f"plan: missing {' and '.join(gone)}; run draw_plan.py plan {spec_rel} {outbase}")
    if has_json and os.path.isfile(spec_path):
        sc = read_sidecar(os.path.join(c.dir, "plan.png"))
        inputs = sc.get("inputs") if sidecar_version(sc) == 2 and isinstance(sc.get("inputs"), list) else []
        specs = [i for i in inputs if isinstance(i, dict) and i.get("role") == "spec"]
        current = len(specs) == 1 and specs[0].get("path") == spec_rel \
            and specs[0].get("sha256") == sha256_file(spec_path)
        if not current:
            add(f"stale: the plan was not drawn from the current {spec_rel}; "
                f"run draw_plan.py plan {spec_rel} {outbase}")
    return out


def _envelope_messages(project, spec: dict) -> list[str]:
    """Rule envelope: width, depth and max_height of the spec against the brief booth (metres, geometry_tol)."""
    booth = project.brief["booth"]
    tol = project.thresholds["geometry_tol"]
    su, bu = spec.get("unit", "m"), booth["unit"]
    overrides = spec.get("envelope_override") or []
    out: list[str] = []
    for fld in ("width", "depth", "max_height"):
        have, want = to_m(spec[fld], su), to_m(booth[fld], bu)
        bad = have - want > tol if fld == "max_height" else abs(have - want) > tol
        if not bad:
            continue
        if any(isinstance(o, dict) and o.get("field") == fld and isinstance(o.get("reason"), str)
               and o["reason"].strip() and abs(to_m(o["value"], su) - have) <= tol for o in overrides):
            continue
        out.append(f"{fld} {round(have, 3):g} m ≠ booth {round(want, 3):g} m (no matching envelope_override)")
    return out


def _concepts_run(project) -> tuple[list[Finding], dict]:
    """(findings in report order, findings by selected key). Selected concepts only; reads, never writes."""
    sel = project.selection
    if sel is None:
        return [Finding("G-SELECT", "error", "brief/selection.json", "no selection: run gates.py select")], {}
    booth = _frame_problems(project)
    out: list[Finding] = list(booth)
    by_key: dict = {}
    for key in sel["selected"]:
        try:
            c = concept_ref(project, key)
        except InputError as e:
            by_key[key] = [Finding("G-SELECT", "error", key, str(e))]
        else:
            by_key[key] = read_front_matter(c)[1] + _concept_geo_findings(project, c, not booth)
        out += by_key[key]
    return out, by_key


def cmd_concepts(project, args) -> int:
    return print_findings(_concepts_run(project)[0], args.json)


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


def _report_renders(project, L: dict) -> list[str]:
    import render      # renders_of: the candidate images of a concept (stdlib only at import time)
    none = L["none"]
    lines = [f"# {L['renders']}"]
    by_set: dict = {}
    for c in list_concepts(project):
        by_set.setdefault(c.set, []).append(c)
    for sid, concepts in by_set.items():
        rows = []
        for c in concepts:
            fm, _ = read_front_matter(c)
            chosen = real(os.path.join(c.dir, fm["chosen"])) if fm["chosen"] else None
            images = list(render.renders_of(c))
            if chosen is not None and os.path.isfile(chosen) and chosen not in [real(i) for i in images]:
                images.append(chosen)      # a fix, front or logo output is not a candidate but can be chosen
            for img in images:
                review = read_review(img)
                verdict = none
                if review is not None and review.get("sha256") == sha256_file(img):
                    verdict = L["pass" if review.get("verdict") == "pass" else "fail"] + f" ({review.get('scope')})"
                rows.append({"concept": c.id, "image": os.path.basename(img), "verdict": verdict,
                             "chosen": "✓" if chosen is not None and real(img) == chosen else ""})
        lines += ["", f"## {_cell(sid)}", ""]
        lines += _table(["concept", "image", "verdict", "chosen"], rows, none)
        sheets = [project.rel(p) for p in (project.path("work", "sheets", f"{sid}-candidates.png"),
                                           project.path("work", "sheets", f"{sid}-chosen.png"))
                  if os.path.isfile(p)]
        lines += [""] + ([f"- {p}" for p in sheets] if sheets else [none])
    return lines


def _report_concepts(project, L: dict) -> list[str]:
    lines = [f"# {L['concepts']}", ""]
    sel = project.selection
    if sel is None:
        return lines + [L["none"]]
    by_key = _concepts_run(project)[1]
    rows = []
    for key in sel["selected"]:
        errors = [f for f in by_key[key] if f.level == "error"]
        geometry = L["fail"] + " (" + ", ".join(sorted({f.code for f in errors})) + ")" if errors else L["pass"]
        plan = f"concepts/{key}/plan.png"
        rows.append({"display": sel["display"].get(key, ""), "concept": key, "geometry": geometry,
                     "plan": plan if os.path.isfile(project.path(*plan.split("/"))) else L["none"]})
    return lines + _table(["display", "concept", "geometry", "plan"], rows, L["none"])


def cmd_report(project, args) -> int:
    L = _report_labels(project)
    builders = {"brief": _report_brief, "ideas": _report_ideas, "renders": _report_renders,
                "concepts": _report_concepts}
    lines = builders[args.what](project, L)
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


# ---------- architectures ----------

def _chapter_note(ch: dict) -> str:
    if ch["required"] == "never":
        return f"{ch['id']} (optional)"
    if ch["required"] == "if-clause-kind":
        return f"{ch['id']} (if clause kind {'/'.join(ch['kinds'])})"
    if ch["required"] == "if-graphics":
        return f"{ch['id']} (if graphics)"
    return ch["id"]


_SOURCE_WORDS = {"brief": "brief.json proposal.architecture", "deck-style": "deck-style thresholds.architecture",
                 "default": "default"}


def cmd_architectures(project, args) -> int:
    reg = load_architectures()
    default = project.thresholds["architecture"] if project else DEFAULTS["architecture"]
    current, source, problem = None, None, None
    if project is not None:
        try:
            current, source = architecture_choice(project)
        except InputError as e:
            problem = str(e)
    order = ([default] if default in reg else []) + [k for k in sorted(reg) if k != default]
    known = current in reg
    required = required_chapters(reg[current], project.brief) if project is not None and known else None
    if args.json:
        print(json.dumps({"default": default, "current": current if known else None,
                          "source": source if known else None, "required": required,
                          "architectures": [reg[k] for k in order]}, ensure_ascii=False, indent=2))
        return 0 if problem is None and (current is None or known) else 1
    for k in order:
        a = reg[k]
        marks = [m for m, on in (("default", k == default), ("current", k == current)) if on]
        label = a["label"].get(project.lang if project else "") or a["label"]["en"]
        print(f"{k:<12}{label}" + (f"  [{', '.join(marks)}]" if marks else ""))
        print(f"  {a['summary']['en']}")
        print(f"  response: {a['response']}; images: {', '.join(a['allowed_kinds'])}; "
              f"separate: {', '.join(a['separate_submission']) or '-'}")
        print(f"  chapters: {', '.join(_chapter_note(c) for c in a['chapters'])}")
    if problem is not None:
        print(f"current: not usable ({problem}); run gates.py brief")
        return 1
    if project is not None and not known:
        print(f"current: {current} is unknown; known: {', '.join(sorted(reg))}")
        return 1
    if project is not None:
        print(f"current: {current} (from {_SOURCE_WORDS[source]}); required chapters now: {', '.join(required) or '-'}")
    return 0


# ---------- entry point ----------

def _build_parser():
    ap = argparse.ArgumentParser(description="Booth proposal gates: brief, frame, ideas, select, renders, concepts, report")
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

    p = sub.add_parser("renders", parents=[common], help="check the chosen render of each concept")
    p.add_argument("--concept", action="append", nargs="+", metavar="KEY",
                   help="only these concepts (<set>/<concept>)")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("concepts", parents=[common], help="check geometry and plan of the selected concepts")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("architectures", parents=[common], help="list the proposal architectures")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("report", parents=[common], help="Markdown summary for the user")
    p.add_argument("what", choices=["brief", "ideas", "renders", "concepts"])
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
        if args.cmd == "architectures":
            try:
                project = find_project(args.project)
            except InputError:
                project = None
            return cmd_architectures(project, args)
        project = find_project(args.project, check_selection=not (args.cmd == "select" and args.clear))
        return globals()[f"cmd_{args.cmd}"](project, args)
    except InputError as e:
        print(f"{'ERROR':<7} {e.code:<18} {e.where}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
