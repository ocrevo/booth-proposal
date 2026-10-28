"""Shared base for the booth-proposal scripts (phase 1a part).

Findings and exit codes, JSON and hash helpers, the project object, label files and thresholds,
unit and CJK helpers, colour helpers, concept folders, reference sets and concept.md front matter.
Standard library only. Language data comes only from the label file named by brief.json "lang".
"""
from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import os
import re
from typing import NamedTuple

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {  # contract 4.2, the only place a threshold number lives
    "appendix_pages_max": 3, "upscale_max": 1.3, "imageless_run_max": 3, "image_reuse_max": 2,
    "prompt_words_warn": 350, "size_tolerance": 0.20, "person_height_m": 1.75, "fix_max": 3,
    "candidates_per_concept": 2, "seconds_per_image": 100, "walkway_m": 0.9, "headroom_m": 2.1,
    "span_m": 1.5, "geometry_tol": 0.005, "claim_min_digits": 2, "tiles_grid": "3x2",
    "architecture": "tender",   # the only architecture id in code; brief proposal.architecture and deck-style override it
}
ARCHITECTURES_DIR = os.path.join(SKILL_DIR, "assets", "architectures")   # tests monkeypatch this
CLAUSE_KINDS = ("design", "interaction", "graphics", "material", "hospitality", "execution", "price", "other")
IMAGE_KINDS = ("render", "plan", "logo", "site", "graphic")   # "graphic": classified from stage A2 on
CLAUSE_N_RE = re.compile(r"\d{1,3}(?:\.\d{1,3}){0,3}[a-z]?")   # 2, 8.1, 4.2.1, 3a (use fullmatch)
_ARCH_ID_RE = re.compile(r"[a-z][a-z0-9-]{0,31}")
_REQUIRED = ("always", "never", "if-kind")
LEGIBLE_RATIO = 3.0  # least contrast ratio of text against its background (large-text level)
GRAPHICS_FOLDER = "graphics"                # the only literal of the graphics folder name in code
PROJECT_FOLDERS = ("input", "refs", "brief", "concepts", "pack", "work", "renders", "prompts",
                   GRAPHICS_FOLDER)  # project layout
PLAIN_WORD_FOLDERS = ("input", "pack", "work", GRAPHICS_FOLDER)  # also ordinary words: work/life is not a project path
ROLES = ("cover", "agenda", "divider", "overview", "board", "compare", "annotated", "plan", "materials",
         "interaction", "response", "signoff", "text", "graphic")  # contract 6.5
MARK_TYPES = {"legible_text": "fail", "number": "fail", "name": "fail", "logo_like": "fail", "emblem": "fail",
              "pseudo_text_legible": "fail", "pasted_photo": "fail", "pseudo_text": "record",
              "venue_background": "record", "composited_logo": "allow"}  # contract 2.5
GRAPHIC_ID_RE = re.compile(r"GR\d+")
GRAPHIC_AREAS = ("top", "bottom", "left", "right")   # where a graphic keeps its artwork empty for the text
_SET_ID_RE = re.compile(r"^[^\W_][\w-]{0,39}$")  # Unicode \w: non-Latin set names allowed
_CONCEPT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,15}$")
_LEGACY_SET = "_legacy"
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")  # compare with os.path.splitext(name)[1].lower()


# ---------- findings and errors ----------

class Finding(NamedTuple):
    code: str                    # contract section 5
    level: str                   # "error" | "warn" | "pending"
    where: str                   # file:line, "page 7 A-board", "set-1/A", "elements[3].w" ...
    message: str                 # one English sentence naming the rule; says what to run when something is stale
    page: int | None = None      # deck findings only: 1-based slide number
    page_id: str | None = None   # deck findings only: the slide's data-id


class InputError(Exception):
    """Unusable input. main() prints it to stderr and exits 2."""

    def __init__(self, code: str, where: str, message: str):
        super().__init__(message)
        self.code = code
        self.where = where


def print_findings(findings: list[Finding], as_json: bool = False) -> int:
    """Print findings (text or JSON); return 1 if any has level "error", else 0."""
    e = sum(1 for f in findings if f.level == "error")
    w = sum(1 for f in findings if f.level == "warn")
    p = sum(1 for f in findings if f.level == "pending")
    if as_json:
        print(json.dumps({"counts": {"error": e, "warn": w, "pending": p},
                          "findings": [f._asdict() for f in findings]}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            where = f"{f.where}: " if f.where else ""
            print(f"{f.level.upper():<7} {f.code:<18} {where}{f.message}")
        print(f"RESULT: {'FAIL' if e else 'PASS'} \u2013 {e} error{'s' * (e != 1)}, "
              f"{w} warning{'s' * (w != 1)}, {p} pending")
    return 1 if e else 0


# ---------- JSON, hashes, time, paths ----------

def read_json(path: str, schema: str | None = None) -> dict:
    """Read a JSON object (BOM accepted). Any problem raises InputError C-INPUT."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except OSError as e:
        raise InputError("C-INPUT", path, f"cannot read file: {e.strerror or e}") from None
    except ValueError as e:
        line = getattr(e, "lineno", None)
        raise InputError("C-INPUT", f"{path}:{line}" if line else path, f"invalid JSON: {e}") from None
    if not isinstance(data, dict):
        raise InputError("C-INPUT", path, "top level must be a JSON object")
    if schema is not None and data.get("schema") != schema:
        raise InputError("C-INPUT", path, f'expected "schema": "{schema}"')
    return data


def read_json_opt(path: str) -> dict | None:
    """None when the file does not exist, else read_json(path)."""
    if not os.path.exists(path):
        return None
    return read_json(path)


def write_json(path: str, data: dict) -> None:
    """UTF-8, ensure_ascii=False, indent 2, LF, atomic (temp file + os.replace)."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def real(path: str) -> str:
    """A path as the file system resolves it (symlinks and junctions followed), case-folded where the OS does.
    Never store it in JSON."""
    return os.path.normcase(os.path.realpath(path))


def inside(root: str, path: str) -> bool:
    """True when path lies inside root (or is root); False across drives."""
    r = real(root)
    try:
        return os.path.commonpath([r, real(path)]) == r
    except ValueError:
        return False


# ---------- project, labels, thresholds ----------

@dataclasses.dataclass
class Project:
    root: str
    brief: dict
    lang: str
    labels: dict
    style: dict
    thresholds: dict
    selection: dict | None = None
    architecture: dict | None = None

    def path(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)

    def rel(self, path: str) -> str:
        """Project-relative path with forward slashes; a path outside the root comes back absolute."""
        absolute = os.path.abspath(path)
        try:
            r = os.path.relpath(absolute, self.root).replace("\\", "/")
        except ValueError:
            return absolute.replace("\\", "/")
        if r == ".." or r.startswith("../"):
            return absolute.replace("\\", "/")
        return r


def _labels_file(lang) -> str | None:
    if not isinstance(lang, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,20}", lang):
        return None
    p = os.path.join(SKILL_DIR, "assets", "labels", f"{lang}.json")
    return p if os.path.isfile(p) else None


def load_labels(lang: str) -> dict:
    p = _labels_file(lang)
    if p is None:
        raise InputError("C-INPUT", f"assets/labels/{lang}.json", "no label file for this lang")
    return read_json(p)


def thresholds(style: dict, base: dict | None = None) -> dict:
    """DEFAULTS, then base (an architecture's thresholds, already validated), then style["thresholds"];
    unknown keys ignored, a wrong type is C-INPUT."""
    out = dict(DEFAULTS)
    out.update(base or {})
    given = style.get("thresholds", {})
    if not isinstance(given, dict):
        raise InputError("C-INPUT", "brief/deck-style.json thresholds", "expected object")
    for key, value in given.items():
        if key not in DEFAULTS:
            continue
        default = DEFAULTS[key]
        if isinstance(default, str):
            ok, kind = isinstance(value, str), "str"
        elif isinstance(default, float):
            ok, kind = isinstance(value, (int, float)) and not isinstance(value, bool), "number"
        else:
            ok, kind = isinstance(value, int) and not isinstance(value, bool), "int"
        if not ok:
            raise InputError("C-INPUT", f"brief/deck-style.json thresholds.{key}", f"expected {kind}")
        out[key] = value
    return out


def _check_selection(sel: dict) -> None:
    w = "brief/selection.json"
    if sel.get("schema") != "selection/1":
        raise InputError("C-INPUT", f"{w} schema", 'expected "schema": "selection/1"')
    selected = sel.get("selected")
    if not isinstance(selected, list) or not all(isinstance(k, str) for k in selected):
        raise InputError("C-INPUT", f"{w} selected", "expected a list of strings")
    lead = sel.get("lead")
    if lead is not None and not isinstance(lead, str):
        raise InputError("C-INPUT", f"{w} lead", "expected a string or null")
    display = sel.get("display")
    if not isinstance(display, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                                for k, v in display.items()):
        raise InputError("C-INPUT", f"{w} display", "expected an object of strings")


def find_project(arg: str | None, *, check_selection: bool = True) -> Project:
    """Load a project folder. brief.json content is not checked here (that is gates.py brief).
    check_selection=False ignores brief/selection.json (selection is None), so `gates.py select --clear` can
    remove a malformed file. An unknown or malformed architecture choice never raises here: project.architecture
    stays None (gates.py brief reports it, architecture_for raises it)."""
    root = os.path.abspath(arg or ".")
    if not os.path.isdir(os.path.join(root, "brief")):
        raise InputError("C-INPUT", root, "no brief/ folder; pass --project <project folder>")
    brief = read_json(os.path.join(root, "brief", "brief.json"), "brief/2")
    lang = brief.get("lang")
    lang = lang if isinstance(lang, str) and lang else ""
    labels = load_labels(lang) if _labels_file(lang) else {}
    style = read_json_opt(os.path.join(root, "brief", "deck-style.json")) or {}
    th = thresholds(style)
    selection = None
    if check_selection:
        selection = read_json_opt(os.path.join(root, "brief", "selection.json"))
        if selection is not None:
            _check_selection(selection)
    project = Project(root=root, brief=brief, lang=lang, labels=labels, style=style, thresholds=th,
                      selection=selection)
    registry = load_architectures()            # a broken shipped file raises (exit 2 everywhere)
    try:
        aid = architecture_choice(project)[0]
    except InputError:
        aid = None
    arch = registry.get(aid)
    if arch is not None:
        project.thresholds = thresholds(style, base=arch["thresholds"])
        project.architecture = arch
    return project


# ---------- architectures (assets/architectures/<id>.json) ----------

def _arch_fail(file: str, path: str, message: str):
    raise InputError("C-INPUT", f"assets/architectures/{file} {path}".rstrip(), message)


def _arch_lang_map(file: str, path: str, v) -> None:
    if not isinstance(v, dict) or not isinstance(v.get("en"), str) or not v["en"].strip():
        _arch_fail(file, path, 'expected an object of non-empty strings with an "en" key')
    for k, x in v.items():
        if not isinstance(k, str) or not isinstance(x, str) or not x.strip():
            _arch_fail(file, f"{path}.{k}", "expected a non-empty string")


def _arch_str_list(file: str, path: str, v, allowed, *, non_empty: bool) -> None:
    if not isinstance(v, list) or (non_empty and not v) or not all(isinstance(x, str) for x in v):
        _arch_fail(file, path, "expected a " + ("non-empty " if non_empty else "") + "list of strings")
    if len(set(v)) != len(v):
        _arch_fail(file, path, "expected unique values")
    for i, x in enumerate(v):
        if x not in allowed:
            _arch_fail(file, f"{path}[{i}]", f"'{x}' is not one of {', '.join(allowed)}")


def _threshold_kind_error(key: str, value) -> str | None:
    """The expected-kind word when value has the wrong type for DEFAULTS[key], else None."""
    default = DEFAULTS[key]
    if isinstance(default, str):
        return None if isinstance(value, str) else "str"
    if isinstance(default, float):
        return None if isinstance(value, (int, float)) and not isinstance(value, bool) else "number"
    return None if isinstance(value, int) and not isinstance(value, bool) else "int"


def _normalise_architecture(file: str, stem: str, data: dict) -> dict:
    if data.get("schema") != "architecture/1":
        _arch_fail(file, "schema", 'expected "schema": "architecture/1"')
    aid = data.get("id")
    if not isinstance(aid, str) or not _ARCH_ID_RE.fullmatch(aid) or aid != stem:
        _arch_fail(file, "id", "expected an id matching [a-z][a-z0-9-]* equal to the file name")
    _arch_lang_map(file, "label", data.get("label"))
    _arch_lang_map(file, "summary", data.get("summary"))
    if data.get("response") not in ("clauses", "design_points"):
        _arch_fail(file, "response", 'expected "clauses" or "design_points"')
    _arch_str_list(file, "allowed_kinds", data.get("allowed_kinds"), IMAGE_KINDS, non_empty=True)
    _arch_str_list(file, "separate_submission", data.get("separate_submission"), CLAUSE_KINDS, non_empty=False)
    th = data.get("thresholds", {})
    if not isinstance(th, dict):
        _arch_fail(file, "thresholds", "expected an object")
    for key, value in th.items():
        if key == "architecture" or key not in DEFAULTS:
            _arch_fail(file, f"thresholds.{key}", "not a threshold key")
        kind = _threshold_kind_error(key, value)
        if kind:
            _arch_fail(file, f"thresholds.{key}", f"expected {kind}")
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        _arch_fail(file, "chapters", "expected a non-empty list")
    out_ch, seen, separates = [], set(), 0
    for i, ch in enumerate(chapters):
        p = f"chapters[{i}]"
        if not isinstance(ch, dict):
            _arch_fail(file, p, "expected an object")
        cid = ch.get("id")
        if not isinstance(cid, str) or not _ARCH_ID_RE.fullmatch(cid):
            _arch_fail(file, f"{p}.id", "expected an id such as 'design'")
        if cid in seen:
            _arch_fail(file, f"{p}.id", f"duplicate chapter id '{cid}'")
        seen.add(cid)
        _arch_lang_map(file, f"{p}.title", ch.get("title"))
        if not isinstance(ch.get("purpose"), str) or not ch["purpose"].strip():
            _arch_fail(file, f"{p}.purpose", "expected a non-empty string")
        _arch_str_list(file, f"{p}.roles", ch.get("roles"), ROLES, non_empty=True)
        req = ch.get("required")
        if req not in _REQUIRED:
            _arch_fail(file, f"{p}.required", "expected one of " + ", ".join(_REQUIRED))
        if req == "if-kind":
            _arch_str_list(file, f"{p}.kinds", ch.get("kinds"), CLAUSE_KINDS, non_empty=True)
        elif ch.get("kinds"):
            _arch_fail(file, f"{p}.kinds", 'only a chapter with required "if-kind" has kinds')
        skeleton = ch.get("skeleton")
        if skeleton is not None and (not isinstance(skeleton, str) or not skeleton.strip()):
            _arch_fail(file, f"{p}.skeleton", "expected LAYOUT[:VARIANT] or null")
        part = ch.get("part")
        if part not in (None, "appendix"):
            _arch_fail(file, f"{p}.part", 'expected "appendix" or null')
        sep = ch.get("separate", False)
        if not isinstance(sep, bool):
            _arch_fail(file, f"{p}.separate", "expected true or false")
        separates += 1 if sep else 0
        out_ch.append({"id": cid, "title": ch["title"], "purpose": ch["purpose"], "roles": list(ch["roles"]),
                       "required": req, "kinds": list(ch["kinds"]) if req == "if-kind" else [],
                       "skeleton": skeleton, "part": part, "separate": sep})
    if "cover" not in out_ch[0]["roles"]:
        _arch_fail(file, "chapters[0].roles", 'the first chapter must have the role "cover"')
    if separates > 1:
        _arch_fail(file, "chapters", "at most one chapter has separate true")
    if data["separate_submission"] and separates != 1:
        _arch_fail(file, "chapters", "separate_submission needs exactly one chapter with separate true")
    return {"schema": "architecture/1", "id": aid, "label": data["label"], "summary": data["summary"],
            "response": data["response"], "allowed_kinds": list(data["allowed_kinds"]),
            "separate_submission": list(data["separate_submission"]), "thresholds": dict(th),
            "chapters": out_ch}


def load_architectures(folder: str | None = None) -> dict[str, dict]:
    """{id: architecture} of every *.json in folder (default: the module global ARCHITECTURES_DIR read at call
    time), sorted by id and validated; any problem is InputError C-INPUT. No cache."""
    folder = folder or ARCHITECTURES_DIR
    try:
        names = sorted(n for n in os.listdir(folder) if n.lower().endswith(".json"))
    except OSError as e:
        raise InputError("C-INPUT", "assets/architectures", f"cannot read folder: {e.strerror or e}") from None
    out = {}
    for name in names:
        data = read_json(os.path.join(folder, name))
        arch = _normalise_architecture(name, os.path.splitext(name)[0], data)
        out[arch["id"]] = arch
    return out


def architecture_choice(project) -> tuple[str, str]:
    """(id, source); source "brief" | "deck-style" | "default". A present but non-string or blank brief
    proposal.architecture, or a non-object proposal, is InputError C-INPUT."""
    proposal = project.brief.get("proposal")
    if proposal is not None:
        bad = InputError("C-INPUT", "brief/brief.json proposal.architecture", "expected a non-empty string")
        if not isinstance(proposal, dict):
            raise bad
        if "architecture" in proposal:
            v = proposal["architecture"]
            if not isinstance(v, str) or not v.strip():
                raise bad
            return v.strip(), "brief"
    th = project.style.get("thresholds")
    if isinstance(th, dict) and "architecture" in th:
        return project.thresholds["architecture"], "deck-style"
    return DEFAULTS["architecture"], "default"


_ARCH_WHERE = {"brief": "brief/brief.json proposal.architecture",
               "deck-style": "brief/deck-style.json thresholds.architecture",
               "default": "common.DEFAULTS architecture"}


def architecture_for(project) -> dict:
    """The project's architecture; an unknown id is InputError C-INPUT at the place the id came from."""
    aid, source = architecture_choice(project)
    reg = load_architectures()
    if aid not in reg:
        raise InputError("C-INPUT", _ARCH_WHERE[source],
                         f"unknown architecture '{aid}'; known: {', '.join(sorted(reg))}")
    return reg[aid]


def clauses_of(brief: dict) -> list[dict]:
    """The clause dicts of brief.json whose n is a string (others are left to gates.py brief)."""
    v = brief.get("clauses")
    return [c for c in v if isinstance(c, dict) and isinstance(c.get("n"), str)] if isinstance(v, list) else []


def deliverables_of(brief: dict) -> list[dict]:
    """The deliverable dicts of brief.json whose id is a string (others are left to gates.py brief)."""
    v = brief.get("deliverables")
    return [d for d in v if isinstance(d, dict) and isinstance(d.get("id"), str)] if isinstance(v, list) else []


def graphics_of(brief: dict) -> list[dict]:
    """The dict entries of brief.json graphics (empty when missing or not a list)."""
    v = brief.get("graphics")
    return [g for g in v if isinstance(g, dict)] if isinstance(v, list) else []


def kinds_of(item: dict) -> list[str]:
    """The kinds of a clause or deliverable: kind is one kind or a list of kinds; unknown values are dropped."""
    k = item.get("kind")
    ks = k if isinstance(k, list) else [k]
    return [x for x in ks if isinstance(x, str) and x in CLAUSE_KINDS]


def brief_kinds(brief: dict) -> set:
    """Every kind the brief asks for: the kinds of its clauses and deliverables, plus "graphics" when it lists
    graphics (a graphic is a deliverable of that kind)."""
    out = set()
    for it in clauses_of(brief) + deliverables_of(brief):
        out.update(kinds_of(it))
    if graphics_of(brief):
        out.add("graphics")
    return out


def required_chapters(arch: dict, brief: dict) -> list[str]:
    """Chapter ids required for this brief, in order: always; if-kind when a kind of brief_kinds is in the
    chapter kinds."""
    kinds = brief_kinds(brief)
    return [ch["id"] for ch in arch["chapters"]
            if ch["required"] == "always" or (ch["required"] == "if-kind" and kinds & set(ch["kinds"]))]


def separate_items(arch: dict | None, brief: dict) -> list[str]:
    """The items submitted separately, in the words of the page: "<n> <title>" for each clause and "<title>" for
    each deliverable whose kinds include a separate-submission kind (clauses first, brief order). The title of a
    clause is its title, else its text. Empty without an architecture or without such items."""
    if arch is None:
        return []
    sep = set(arch["separate_submission"])
    out = []
    for c in clauses_of(brief):
        t = c.get("title") if isinstance(c.get("title"), str) and c["title"].strip() else c.get("text")
        if sep & set(kinds_of(c)) and isinstance(t, str) and t.strip():
            out.append(f"{c['n']} {' '.join(t.split())}")
    for d in deliverables_of(brief):
        t = d.get("title")
        if sep & set(kinds_of(d)) and isinstance(t, str) and t.strip():
            out.append(" ".join(t.split()))
    return out


def separate_chapter(arch: dict) -> dict | None:
    """The chapter with separate true, or None."""
    return next((c for c in arch["chapters"] if c["separate"]), None)


# ---------- units, CJK, terms, colour ----------

_UNIT_FACTORS = {"m": 1.0, "ft": 3.28084}


def unit_factor(unit: str) -> float:
    if unit not in _UNIT_FACTORS:
        raise ValueError(f"unknown unit: {unit!r}")
    return _UNIT_FACTORS[unit]


def to_m(value: float, unit: str) -> float:
    return value / unit_factor(unit)


_CJK_RANGES = (("\u2e80", "\u9fff"), ("\uac00", "\ud7af"), ("\uf900", "\ufaff"), ("\ufe30", "\ufe4f"),
               ("\uff00", "\uffef"), ("\U00020000", "\U0003134f"))


def is_cjk(ch: str) -> bool:
    return any(lo <= ch <= hi for lo, hi in _CJK_RANGES)


def has_cjk(s: str) -> bool:
    return any(is_cjk(ch) for ch in s)


def cjk_ratio(s: str) -> float:
    """CJK characters divided by non-whitespace characters; 0.0 when there are none."""
    chars = [ch for ch in s if not ch.isspace()]
    if not chars:
        return 0.0
    return sum(1 for ch in chars if is_cjk(ch)) / len(chars)


def _latin_word_char(ch: str) -> bool:
    return (ch.isalnum() or ch == "_") and not is_cjk(ch)


def find_term(term: str, text: str, case: bool = False) -> list[tuple[int, int]]:
    """Non-overlapping (start, end) matches, left to right. A term edge that is a non-CJK word character
    needs a non-word character (or the text edge) beside it; CJK edges need no boundary."""
    if not term:
        return []
    pat = re.compile(re.escape(term), 0 if case else re.IGNORECASE)
    check_first, check_last = _latin_word_char(term[0]), _latin_word_char(term[-1])
    out: list[tuple[int, int]] = []
    pos = 0
    while pos <= len(text):
        m = pat.search(text, pos)
        if not m:
            break
        s, e = m.span()
        if e == s:
            break
        if (check_first and s > 0 and _latin_word_char(text[s - 1])) or \
                (check_last and e < len(text) and _latin_word_char(text[e])):
            pos = s + 1
            continue
        out.append((s, e))
        pos = e
    return out


def hex_rgb(h: str | None) -> tuple | None:
    h = (h or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if not re.fullmatch(r"[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(rgb) -> float:
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def legible(fg: str, bg: str, ratio: float = LEGIBLE_RATIO) -> str | None:
    """fg (#hex) mixed toward white on a dark background, toward black on a light one, until it reaches ratio
    against bg; None when either is not a hex colour."""
    f, b = hex_rgb(fg), hex_rgb(bg)
    if not f or not b:
        return None
    if contrast(f, b) >= ratio:
        return fg
    target = (255, 255, 255) if luminance(b) < 0.18 else (0, 0, 0)
    for k in range(1, 21):
        m = tuple(round(x + (t - x) * k / 20) for x, t in zip(f, target))
        if contrast(m, b) >= ratio:
            return "#{:02X}{:02X}{:02X}".format(*m)
    return "#{:02X}{:02X}{:02X}".format(*target)


# ---------- concept folders (contract 1) ----------

class ConceptRef(NamedTuple):
    key: str   # "set-1/A"
    set: str
    id: str
    dir: str   # absolute


def _subdirs(path: str) -> list[str]:
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return []
    return [n for n in names if os.path.isdir(os.path.join(path, n))]


def list_concepts(project: Project) -> list[ConceptRef]:
    """Every concept folder (holds concept.md or renders/) under concepts/<set>/<concept>/, sorted by set, id."""
    base = project.path("concepts")
    out = []
    for s in _subdirs(base):
        if not (_SET_ID_RE.fullmatch(s) or s == _LEGACY_SET):
            continue
        for c in _subdirs(os.path.join(base, s)):
            if not _CONCEPT_ID_RE.fullmatch(c):
                continue
            d = os.path.join(base, s, c)
            if os.path.isfile(os.path.join(d, "concept.md")) or os.path.isdir(os.path.join(d, "renders")):
                out.append(ConceptRef(f"{s}/{c}", s, c, d))
    return sorted(out, key=lambda r: (r.set, r.id))


def concept_ref(project: Project, key: str) -> ConceptRef:
    for c in list_concepts(project):
        if c.key == key:
            return c
    raise InputError("C-INPUT", key, "no concept folder for this key (expected concepts/<set>/<concept>/)")


def concept_of_path(project: Project, path: str) -> ConceptRef | None:
    for c in list_concepts(project):
        if inside(c.dir, path):
            return c
    return None


# ---------- graphic folders (graphics/<GR>/, one per brief.json graphics entry) ----------

class GraphicRef(NamedTuple):
    key: str   # "graphics/GR1"
    id: str    # "GR1"
    dir: str   # absolute <root>/graphics/GR1 (may not exist yet)


def graphic_item(brief: dict, gid: str) -> dict | None:
    """The brief.json graphics entry with that id, or None."""
    return next((g for g in graphics_of(brief) if g.get("id") == gid), None)


def list_graphics(project: Project) -> list[GraphicRef]:
    """Every graphic folder on disk (holds graphic.md or renders/) under graphics/<GR number>/, by number."""
    base = project.path(GRAPHICS_FOLDER)
    out = []
    for n in _subdirs(base):
        if not GRAPHIC_ID_RE.fullmatch(n):
            continue
        d = os.path.join(base, n)
        if os.path.isfile(os.path.join(d, "graphic.md")) or os.path.isdir(os.path.join(d, "renders")):
            out.append(GraphicRef(f"{GRAPHICS_FOLDER}/{n}", n, d))
    return sorted(out, key=lambda g: int(g.id[2:]))


def graphic_ref(project: Project, gid: str) -> GraphicRef:
    """The graphic with that id; it must be listed in brief.json graphics (the folder may not exist yet)."""
    if not GRAPHIC_ID_RE.fullmatch(gid) or graphic_item(project.brief, gid) is None:
        raise InputError("C-INPUT", "brief/brief.json graphics",
                         f"no graphic {gid} in brief.json graphics; add it and run gates.py brief")
    return GraphicRef(f"{GRAPHICS_FOLDER}/{gid}", gid, project.path(GRAPHICS_FOLDER, gid))


def graphic_of_path(project: Project, path: str) -> GraphicRef | None:
    """The graphic folder a path lies in (listed in brief.json or not), else None."""
    base = project.path(GRAPHICS_FOLDER)
    for n in _subdirs(base):
        if GRAPHIC_ID_RE.fullmatch(n) and inside(os.path.join(base, n), path):
            return GraphicRef(f"{GRAPHICS_FOLDER}/{n}", n, os.path.join(base, n))
    return None


def owner_of_path(project: Project, path: str):
    """The concept or graphic a path lies in, else None."""
    return concept_of_path(project, path) or graphic_of_path(project, path)


def is_graphic(owner) -> bool:
    return isinstance(owner, GraphicRef)


def owner_md(owner) -> tuple[str, str]:
    """(absolute path, path as shown) of the concept.md or graphic.md of a concept or a graphic."""
    if is_graphic(owner):
        return os.path.join(owner.dir, "graphic.md"), f"{GRAPHICS_FOLDER}/{owner.id}/graphic.md"
    return os.path.join(owner.dir, "concept.md"), f"concepts/{owner.set}/{owner.id}/concept.md"


def ratio_value(ratio) -> float | None:
    """Width divided by height of an "a:b" ratio string (a and b above 0); None for anything else."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)", ratio) if isinstance(ratio, str) else None
    if not m or float(m.group(1)) <= 0 or float(m.group(2)) <= 0:
        return None
    return float(m.group(1)) / float(m.group(2))


# ---------- reference sets (contract 1, 1.2) ----------

def _images_in(folder: str) -> list[str]:
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    return [n for n in names if os.path.splitext(n)[1].lower() in _IMAGE_EXTS
            and os.path.isfile(os.path.join(folder, n))]


def scan_reference_sets(project: Project) -> tuple[list[dict], list[Finding]]:
    """Reference sets as they are on disk, in the shape of brief.json references.sets, plus findings."""
    sets: list[dict] = []
    findings: list[Finding] = []
    refs = project.path("input", "refs")

    def entry(set_id: str, rel_dir: str, abs_dir: str, names: list[str]) -> dict:
        files = [{"path": f"{rel_dir}/{n}", "sha256": sha256_file(os.path.join(abs_dir, n))} for n in names]
        files.sort(key=lambda f: f["path"])
        return {"id": set_id, "dir": rel_dir, "files": files}

    if os.path.isdir(refs):
        for name in _subdirs(refs):
            where = f"input/refs/{name}"
            if not _SET_ID_RE.fullmatch(name):
                findings.append(Finding("G-REFS", "error", where,
                                        "name: invalid set folder name; use 1 to 40 letters, digits, '-' or '_', "
                                        "not starting with '_'"))
                continue
            names = _images_in(os.path.join(refs, name))
            if not names:
                findings.append(Finding("G-REFS", "error", where,
                                        "empty: set folder has no png/jpg/jpeg/webp image"))
                continue
            sets.append(entry(name, where, os.path.join(refs, name), names))
    else:
        findings.append(Finding("C-LEGACY", "warn", "input/refs",
                                "legacy-set: no input/refs/ folder; every image directly inside input/ is "
                                f"reference set {_LEGACY_SET}"))
        names = _images_in(project.path("input"))
        if not names:
            findings.append(Finding("G-REFS", "error", "input",
                                    "empty: input/ has no png/jpg/jpeg/webp image directly inside"))
        else:
            sets.append(entry(_LEGACY_SET, "input", project.path("input"), names))
    sets.sort(key=lambda s: s["id"])
    return sets, findings


# ---------- concept.md front matter (contract 3) ----------

_FM_KEYS = ("chosen", "blocked", "accent")
_ACCENT_RE = re.compile(r"#[0-9A-Fa-f]{6}")


def _parse_fm(text: str, where_prefix: str | None = None):
    """Returns (dict, body, findings, lines); lines maps "chosen"/"accent" to a line number and
    "blocked" to a list of line numbers (in the order of the dict's blocked list)."""
    def at(n: int) -> str:
        return f"line {n}" if where_prefix is None else f"{where_prefix}:{n}"

    result: dict = {"chosen": None, "blocked": [], "accent": None}
    lines_of: dict = {"chosen": None, "accent": None, "blocked": []}
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = [ln[:-1] if ln.endswith("\r") else ln for ln in text.split("\n")]
    empty = {"chosen": None, "blocked": [], "accent": None}
    if lines[0] != "---":
        return empty, text, [], lines_of
    close = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
    if close is None:
        return empty, "", [Finding("G-FM", "error", at(1), "front matter has no closing ---")], lines_of
    findings: list[Finding] = []

    def bad(n: int, msg: str) -> None:
        findings.append(Finding("G-FM", "error", at(n), msg))

    for i in range(1, close):
        n = i + 1
        raw = lines[i].strip()
        if not raw or raw.startswith("#"):
            continue
        if ":" not in raw:
            bad(n, "expected key: value")
            continue
        key, _, value = raw.partition(":")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key not in _FM_KEYS:
            bad(n, f"unknown key '{key}' (allowed: chosen, blocked, accent)")
        elif not value:
            bad(n, f"'{key}' has an empty value")
        elif key == "blocked":
            result["blocked"].append(value)
            lines_of["blocked"].append(n)
        elif result[key] is not None:
            bad(n, f"'{key}' is given more than once")
        elif key == "accent" and not _ACCENT_RE.fullmatch(value):
            bad(n, "accent must be #RRGGBB")
        else:
            result[key] = value
            lines_of[key] = n
    body = "\n".join(lines[close + 1:])
    return result, body, findings, lines_of


def parse_front_matter(text: str) -> tuple[dict, str, list[Finding]]:
    result, body, findings, _ = _parse_fm(text)
    return result, body, findings


def read_front_matter(concept) -> tuple[dict, list[Finding]]:
    """Front matter of the concept.md of a concept or the graphic.md of a graphic, with chosen/blocked paths
    checked (inside the owner's renders/, existing)."""
    md, prefix = owner_md(concept)
    if not os.path.isfile(md):
        return {"chosen": None, "blocked": [], "accent": None}, []
    try:
        with open(md, encoding="utf-8-sig") as f:
            text = f.read()
    except (OSError, ValueError) as e:
        raise InputError("C-INPUT", prefix, f"cannot read file: {e}") from None
    result, _, findings, lines_of = _parse_fm(text, prefix)
    renders = os.path.join(concept.dir, "renders")

    def path_ok(p: str) -> bool:
        if os.path.isabs(p) or p.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", p):
            return False
        full = os.path.normpath(os.path.join(concept.dir, p.replace("\\", "/")))
        return inside(renders, full) and os.path.isfile(full)

    msg = f"path must name an existing file inside this {'graphic' if is_graphic(concept) else 'concept'}'s renders/"
    if result["chosen"] is not None:
        if path_ok(result["chosen"]):
            result["chosen"] = result["chosen"].replace("\\", "/")
        else:
            findings.append(Finding("G-FM", "error", f"{prefix}:{lines_of['chosen']}", msg))
            result["chosen"] = None
    kept = []
    for p, n in zip(result["blocked"], lines_of["blocked"]):
        if path_ok(p):
            kept.append(p.replace("\\", "/"))
        else:
            findings.append(Finding("G-FM", "error", f"{prefix}:{n}", msg))
    result["blocked"] = kept
    findings.sort(key=lambda f: int(f.where.rsplit(":", 1)[1]))
    return result, findings


# ---------- sidecars and reviews (contract 2.4, 2.5) ----------

_SIDECAR_REQUIRED = ("tool", "mode", "set", "concept", "inputs", "prompt_sha256", "lint")


def sidecar_path(image: str) -> str:
    return os.path.splitext(image)[0] + ".json"


def read_sidecar(image: str) -> dict | None:
    """The sidecar dict beside an image, or None when it is missing, unreadable or not an object."""
    try:
        return read_json(sidecar_path(image))
    except InputError:
        return None


def sidecar_version(data) -> int:
    """0 = none or unknown schema, 1 = old sidecar without a schema key, 2 = sidecar/2."""
    if not isinstance(data, dict):
        return 0
    if "schema" not in data:
        return 1
    return 2 if data["schema"] == "sidecar/2" else 0


def write_sidecar(image_or_stem: str, data: dict) -> None:
    """Write sidecar/2 beside an image. outputs = {basename: sha256 read from disk now}."""
    missing = [k for k in _SIDECAR_REQUIRED if k not in data]
    if missing:
        raise ValueError(f"sidecar data lacks: {', '.join(missing)}")
    folder = os.path.dirname(image_or_stem)

    def digest(path: str) -> str:
        try:
            return sha256_file(path)
        except OSError as e:
            raise ValueError(f"cannot hash output file {path}: {e.strerror or e}") from None

    given = data.get("outputs")
    if isinstance(given, dict):
        outputs = {name: digest(os.path.join(folder, name)) for name in given}
    else:
        outputs = {os.path.basename(image_or_stem): digest(image_or_stem)}
    out: dict = {"schema": "sidecar/2"}
    out.update({k: v for k, v in data.items() if k not in ("schema", "outputs", "created_at")})
    out["outputs"] = outputs
    out["created_at"] = now_iso()
    write_json(sidecar_path(image_or_stem), out)


def review_path(image: str) -> str:
    return os.path.splitext(image)[0] + ".review.json"


def read_review(image: str) -> dict | None:
    """The review dict beside an image, or None when missing, unreadable or not review/1."""
    try:
        data = read_json(review_path(image))
    except InputError:
        return None
    return data if data.get("schema") == "review/1" else None


def review_is_current_pass(image: str, need_full: bool) -> tuple[bool, str]:
    """(True, "") when the image has a review of its current bytes with verdict pass (and scope full if needed)."""
    r = read_review(image)
    if r is None:
        return False, "missing: no review; run render.py review"
    try:
        current = sha256_file(image)
    except OSError:
        current = None
    if r.get("sha256") != current:
        return False, "stale: the image changed after review; run render.py review"
    if r.get("verdict") != "pass":
        return False, "fail: review verdict is fail"
    if need_full and r.get("scope") != "full":
        return False, "scope: a chosen render needs --scope full; run render.py review"
    return True, ""


# ---------- forbidden and logo hashes (contract 6.6) ----------

_MAX_HASH_BYTES = 300 * 1024 * 1024


def _files_under(folder: str):
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames.sort()
        for name in sorted(filenames):
            yield os.path.join(dirpath, name)


def _hash_or_none(path: str) -> str | None:
    try:
        if os.path.getsize(path) > _MAX_HASH_BYTES:
            return None
        return sha256_file(path)
    except OSError:
        return None


def logo_hashes(project: Project) -> set[str]:
    """Hashes of the deck-style logo (path relative to brief/) and of every file under brief/brand/."""
    paths = list(_files_under(project.path("brief", "brand")))
    logo = project.style.get("logo")
    if isinstance(logo, str) and logo:
        p = os.path.join(project.path("brief"), logo)
        if os.path.isfile(p):
            paths.append(p)
    return {h for h in (_hash_or_none(p) for p in paths) if h}


def forbidden_hashes(project: Project) -> dict[str, str]:
    """{sha256: project-relative path} of everything that must never appear as a render or in the deck:
    stamped reference files, input/, brief/media/ and the ref inputs of sidecars. Logo files are removed
    unless the hash is a stamped reference file."""
    out: dict[str, str] = {}
    stamped: set[str] = set()

    def add(h, path) -> None:
        if isinstance(h, str) and h and h not in out:
            out[h] = path

    refs = project.brief.get("references")
    sets = refs.get("sets") if isinstance(refs, dict) else None
    for s in sets if isinstance(sets, list) else []:
        files = s.get("files") if isinstance(s, dict) else None
        for f in files if isinstance(files, list) else []:
            if isinstance(f, dict) and isinstance(f.get("sha256"), str) and isinstance(f.get("path"), str):
                stamped.add(f["sha256"])
                add(f["sha256"], f["path"])
    for folder in (("input",), ("brief", "media")):
        for p in _files_under(project.path(*folder)):
            add(_hash_or_none(p), project.rel(p))
    for c in list_concepts(project) + list_graphics(project):
        renders = os.path.join(c.dir, "renders")
        try:
            names = sorted(os.listdir(renders))
        except OSError:
            continue
        for name in names:
            low = name.lower()
            if not low.endswith(".json") or low.endswith(".review.json"):
                continue
            sc = read_sidecar(os.path.join(renders, name))
            ver = sidecar_version(sc)
            if ver == 2:
                inputs = sc.get("inputs")
                for i in inputs if isinstance(inputs, list) else []:
                    if isinstance(i, dict) and i.get("role") == "ref":
                        add(i.get("sha256"), i["path"] if isinstance(i.get("path"), str) else "")
            elif ver == 1:
                imgs = sc.get("input_images")
                for p in imgs if isinstance(imgs, list) else []:
                    if not isinstance(p, str) or p.replace("\\", "/").startswith("concepts/"):
                        continue
                    full = os.path.join(project.root, p)
                    if os.path.isfile(full):
                        add(_hash_or_none(full), p.replace("\\", "/"))
    for h in logo_hashes(project):
        if h not in stamped:
            out.pop(h, None)
    return out


# ---------- base chain (contract 2.4) ----------

_CHAIN_MAX = 20
_BASE_MODES = ("fix", "front", "logo", "label")
_ROOT_MODES = {False: ("hero", "import"), True: ("graphic", "import")}       # key: is_graphic(owner)
_BASE_MODES_OF = {False: _BASE_MODES, True: ("fix", "logo", "label")}


def trace_base_chain(project: Project, image: str) -> tuple[list[str], Finding | None]:
    """Follow the single base input of a render back to a hero or import. Returns (visited project-relative
    paths, None) or (visited, Finding R-SOURCE); callers outside render.py re-code the finding."""
    where = project.rel(image)
    visited: list[str] = []

    def fail(msg: str):
        return visited, Finding("R-SOURCE", "error", where, msg)

    c = owner_of_path(project, image)
    if c is None:
        return fail("chain: not a render of any concept")
    graphic = is_graphic(c)
    renders = real(os.path.join(c.dir, "renders"))
    forbidden = forbidden_hashes(project)
    seen: set[str] = set()
    cur = image
    while True:
        rel = project.rel(cur)
        if not os.path.isfile(cur) or not inside(renders, cur):
            return fail(f"chain: {rel} is not a render of {c.key}")
        key = real(cur)
        if key in seen:
            return fail(f"chain: cycle at {rel}")
        seen.add(key)
        visited.append(rel)
        h = sha256_file(cur)
        if h in forbidden:
            return fail(f"chain: {rel} has the same content as {forbidden[h]}")
        sc = read_sidecar(cur)
        ver = sidecar_version(sc)
        if ver == 0:
            return fail(f"chain: {rel} has no sidecar")
        if ver == 1:
            if graphic:
                return fail(f"chain: {rel} has an old sidecar; graphics need sidecar/2")
            return visited, None
        outputs = sc.get("outputs")
        if not isinstance(outputs, dict) or outputs.get(os.path.basename(cur)) != h:
            return fail(f"chain: sidecar hash differs from {rel}")
        if (sc.get("kind") == "graphic") != graphic:
            return fail(f"chain: {rel} is not a {'graphic' if graphic else 'concept'} render (sidecar kind)")
        inputs = sc.get("inputs") if isinstance(sc.get("inputs"), list) else []
        bases = [i for i in inputs if isinstance(i, dict) and i.get("role") == "base"]
        mode = sc.get("mode")
        if mode in _ROOT_MODES[graphic] and not bases:
            return visited, None
        if mode in _BASE_MODES_OF[graphic] and len(bases) == 1 and isinstance(bases[0].get("path"), str):
            base = os.path.join(project.root, bases[0]["path"])
            if _hash_or_none(base) != bases[0].get("sha256"):
                return fail(f"chain: {bases[0]['path']} changed after {rel} was made")
            if len(visited) >= _CHAIN_MAX:
                return fail(f"chain: longer than {_CHAIN_MAX} steps")
            cur = base
            continue
        return fail(f"chain: mode {mode} cannot start a chain")


# ---------- fonts ----------

_CJK_FONTS = ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "/System/Library/Fonts/PingFang.ttc",
              "/usr/share/fonts/**/NotoSansCJK*.ttc", "C:/Windows/Fonts/msyhbd.ttc",
              "/System/Library/Fonts/Hiragino Sans GB.ttc", "/usr/share/fonts/**/NotoSansCJK*.otf")
_LATIN_FONTS = ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/**/DejaVuSans.ttf")


def find_font(cjk: bool) -> str | None:
    """First font file that exists (CJK-capable when cjk is true); None means use Pillow's default font."""
    import glob
    for pattern in _CJK_FONTS if cjk else _LATIN_FONTS:
        for path in sorted(glob.glob(pattern, recursive=True)):
            if os.path.isfile(path):
                return path
    return None


# ---------- geometry helpers (contract 6.3, phase 2 card steps 3-4) ----------

def normalise_geometry(spec: dict) -> dict:
    """Fill defaults in place and return the spec: elements (or zones), id, z, shape; a repeat row becomes its
    bounding box, the single piece is kept under "piece" for drawing."""
    spec.setdefault("elements", spec.get("zones", []))
    for i, e in enumerate(spec["elements"], 1):
        e.setdefault("id", f"E{i}")
        e.setdefault("z", 0)
        e.setdefault("shape", "frame" if e.get("kind") == "overhead" and e.get("legs") else "box")
        r = e.get("repeat")
        if r and "piece" not in e:   # the checked footprint of a row is its bounding box
            r["_from"] = e.get("height", 0)
            e["piece"] = {"w": e["w"], "h": e["h"]}
            e["w"] = (r["count"] - 1) * abs(r.get("dx", 0)) + e["w"]
            e["h"] = (r["count"] - 1) * abs(r.get("dy", 0)) + e["h"]
            e["height"] = max(e.get("height", 0), r.get("height_to", e.get("height", 0)))
    return spec


def expand_repeat(element: dict) -> list[dict]:
    """Expand a normalised repeated element into its individual pieces (for drawing)."""
    r = element.get("repeat")
    if not r:
        return [element]
    out, n = [], r["count"]
    for i in range(n):
        p = dict(element)
        p.pop("repeat", None)
        p.update(x=element["x"] + i * r.get("dx", 0), y=element["y"] + i * r.get("dy", 0),
                 w=element["piece"]["w"], h=element["piece"]["h"])
        if "height_to" in r:
            p["height"] = r["_from"] + (r["height_to"] - r["_from"]) * (i / (n - 1) if n > 1 else 0)
        out.append(p)
    return out


def zone_numbers(elements: list[dict]) -> dict[str, int]:
    """{label: number}: distinct non-empty labels in list order; a repeat row is one element."""
    out: dict[str, int] = {}
    for z in elements:
        lab = z.get("label") or ""
        if lab and lab not in out:
            out[lab] = len(out) + 1
    return out


_GEO_SIDES = ("front", "back", "left", "right")
_GEO_SHAPES = ("box", "cylinder", "circle", "frame", "extrusion")
_GEO_SUPPORTS = ("floor", "wall", "legs", "columns", "hung")
_GEO_ACCENT_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_MISSING = object()


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def _got(v) -> str:
    return "nothing (missing)" if v is _MISSING else json.dumps(v, ensure_ascii=False, default=str)


def validate_geometry(spec: dict) -> list[Finding]:
    """Validate a raw geometry spec (phase 2 card, step 4). One C-INPUT finding per problem, where = JSON path.
    Unknown keys are ignored."""
    out: list[Finding] = []

    def bad(path: str, rule: str, value=_MISSING) -> None:
        out.append(Finding("C-INPUT", "error", path, f"{path} must be {rule}, got {_got(value)}"))

    def num(obj: dict, key: str, path: str, *, required=False, lo=None, strict=True) -> None:
        """Number check; lo is a lower bound (strict: value > lo, else value >= lo)."""
        v = obj.get(key, _MISSING)
        rule = "a number" if lo is None else f"a number {'>' if strict else '>='} {lo}"
        if v is _MISSING:
            if required:
                bad(path, rule)
            return
        if not _is_num(v) or (lo is not None and (v <= lo if strict else v < lo)):
            bad(path, rule, v)

    def string(obj: dict, key: str, path: str) -> None:
        v = obj.get(key, _MISSING)
        if v is not _MISSING and not isinstance(v, str):
            bad(path, "a string", v)

    def one_of(obj: dict, key: str, path: str, options) -> None:
        v = obj.get(key, _MISSING)
        if v is not _MISSING and not (isinstance(v, str) and v in options):
            bad(path, "one of " + ", ".join(f'"{o}"' for o in options), v)

    def boolean(obj: dict, key: str, path: str) -> None:
        v = obj.get(key, _MISSING)
        if v is not _MISSING and not isinstance(v, bool):
            bad(path, "true or false", v)

    def triple(obj: dict, key: str, path: str) -> None:
        v = obj.get(key, _MISSING)
        if not isinstance(v, list) or len(v) != 3:
            bad(path, "a list of 3 numbers", v)
            return
        for k, item in enumerate(v):
            if not _is_num(item):
                bad(f"{path}[{k}]", "a number", item)

    if not isinstance(spec, dict):
        bad("(root)", "an object", spec)
        return out

    one_of(spec, "unit", "unit", ("m", "ft"))
    for key in ("width", "depth", "max_height"):
        num(spec, key, key, required=True, lo=0)

    sides = spec.get("open_sides", _MISSING)
    if sides is not _MISSING:
        if not isinstance(sides, list):
            bad("open_sides", "a list of front, back, left, right", sides)
        else:
            seen = set()
            for i, s in enumerate(sides):
                if not (isinstance(s, str) and s in _GEO_SIDES):
                    bad(f"open_sides[{i}]", "one of " + ", ".join(f'"{x}"' for x in _GEO_SIDES), s)
                elif s in seen:
                    bad(f"open_sides[{i}]", "a side listed once", s)
                else:
                    seen.add(s)

    key = "elements" if "elements" in spec else ("zones" if "zones" in spec else "elements")
    elements = spec.get(key, _MISSING)
    if not isinstance(elements, list) or not elements:
        bad(key, "a non-empty list of objects", elements)
    else:
        for i, e in enumerate(elements):
            p = f"{key}[{i}]"
            if not isinstance(e, dict):
                bad(p, "an object", e)
                continue
            num(e, "x", f"{p}.x", required=True)
            num(e, "y", f"{p}.y", required=True)
            num(e, "w", f"{p}.w", required=True, lo=0)
            num(e, "h", f"{p}.h", required=True, lo=0)
            num(e, "z", f"{p}.z", lo=0, strict=False)
            num(e, "height", f"{p}.height", lo=0, strict=False)
            for f in ("id", "label", "kind", "group", "render_hint"):
                string(e, f, f"{p}.{f}")
            one_of(e, "shape", f"{p}.shape", _GEO_SHAPES)
            num(e, "band", f"{p}.band", lo=0)
            if e.get("shape") == "extrusion":
                prof = e.get("profile", _MISSING)
                if not isinstance(prof, list) or len(prof) < 2:
                    bad(f"{p}.profile", "a list of at least 2 [number, number] points", prof)
                else:
                    for k, pt in enumerate(prof):
                        if not (isinstance(pt, list) and len(pt) == 2 and all(_is_num(c) for c in pt)):
                            bad(f"{p}.profile[{k}]", "a [number, number] point", pt)
            one_of(e, "axis", f"{p}.axis", ("x", "y"))
            r = e.get("repeat", _MISSING)
            if r is not _MISSING:
                if not isinstance(r, dict):
                    bad(f"{p}.repeat", "an object", r)
                else:
                    c = r.get("count", _MISSING)
                    if not (isinstance(c, int) and not isinstance(c, bool) and c >= 1):
                        bad(f"{p}.repeat.count", "an integer >= 1", c)
                    num(r, "dx", f"{p}.repeat.dx")
                    num(r, "dy", f"{p}.repeat.dy")
                    num(r, "height_to", f"{p}.repeat.height_to", lo=0, strict=False)
            prog = e.get("program", _MISSING)
            if prog is not _MISSING:
                if isinstance(prog, list):
                    for k, item in enumerate(prog):
                        if not isinstance(item, str):
                            bad(f"{p}.program[{k}]", "a string", item)
                elif not isinstance(prog, str):
                    bad(f"{p}.program", "a string or a list of strings", prog)
            one_of(e, "support", f"{p}.support", _GEO_SUPPORTS)
            boolean(e, "contains", f"{p}.contains")
            boolean(e, "legs", f"{p}.legs")
            one_of(e, "label_pos", f"{p}.label_pos", ("top",))
            num(e, "layer", f"{p}.layer")

    string(spec, "title", "title")
    acc = spec.get("accent", _MISSING)
    if acc is not _MISSING and not (isinstance(acc, str) and _GEO_ACCENT_RE.match(acc)):
        bad("accent", "a colour like #1F5FAE", acc)
    one_of(spec, "camera_corner", "camera_corner", ("left", "right"))
    cam = spec.get("camera", _MISSING)
    if cam is not _MISSING:
        if not isinstance(cam, dict):
            bad("camera", "an object", cam)
        else:
            for name, c in cam.items():
                p = f"camera.{name}"
                if not isinstance(c, dict):
                    bad(p, "an object with eye and target", c)
                    continue
                triple(c, "eye", f"{p}.eye")
                triple(c, "target", f"{p}.target")
                num(c, "lens_mm", f"{p}.lens_mm", lo=0)
    num(spec, "wall_height", "wall_height", lo=0, strict=False)
    num(spec, "walkway", "walkway", lo=0)
    num(spec, "headroom", "headroom", lo=0)

    zones = spec.get("height_zones", _MISSING)
    if zones is not _MISSING:
        if not isinstance(zones, list):
            bad("height_zones", "a list of objects", zones)
        else:
            for i, z in enumerate(zones):
                p = f"height_zones[{i}]"
                if not isinstance(z, dict):
                    bad(p, "an object", z)
                    continue
                num(z, "y_from", f"{p}.y_from", required=True)
                lo = z.get("y_from")
                num(z, "y_to", f"{p}.y_to", required=True, lo=lo if _is_num(lo) else None)
                num(z, "max", f"{p}.max", required=True, lo=0)
                string(z, "note", f"{p}.note")

    rig = spec.get("rigging_allowed", _MISSING)
    if rig is not _MISSING and rig is not None and not isinstance(rig, bool):
        bad("rigging_allowed", "true, false or null", rig)

    req = spec.get("required", _MISSING)
    if req is not _MISSING:
        if not isinstance(req, list):
            bad("required", "a list of non-empty strings", req)
        else:
            for i, item in enumerate(req):
                if not (isinstance(item, str) and item.strip()):
                    bad(f"required[{i}]", "a non-empty string", item)

    ov = spec.get("envelope_override", _MISSING)
    if ov is not _MISSING:
        if not isinstance(ov, list):
            bad("envelope_override", "a list of objects", ov)
        else:
            for i, o in enumerate(ov):
                p = f"envelope_override[{i}]"
                if not isinstance(o, dict):
                    bad(p, "an object", o)
                    continue
                f = o.get("field", _MISSING)
                if not (isinstance(f, str) and f in ("max_height", "width", "depth")):
                    bad(f"{p}.field", 'one of "max_height", "width", "depth"', f)
                num(o, "value", f"{p}.value", required=True, lo=0)
                rs = o.get("reason", _MISSING)
                if not isinstance(rs, str):      # blank is allowed here; gates.py concepts rule envelope rejects it
                    bad(f"{p}.reason", "a string", rs)
    return out
