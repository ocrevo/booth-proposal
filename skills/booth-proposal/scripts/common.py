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
}
ROLES = ("cover", "agenda", "divider", "overview", "board", "compare", "annotated", "plan", "materials",
         "interaction", "response", "signoff", "text")  # contract 6.5
MARK_TYPES = {"legible_text": "fail", "number": "fail", "name": "fail", "logo_like": "fail", "emblem": "fail",
              "pseudo_text_legible": "fail", "pseudo_text": "record", "venue_background": "record",
              "composited_logo": "allow"}  # contract 2.5
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


def thresholds(style: dict) -> dict:
    """DEFAULTS updated from style["thresholds"]; unknown keys ignored, a wrong type is C-INPUT."""
    out = dict(DEFAULTS)
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


def find_project(arg: str | None) -> Project:
    """Load a project folder. brief.json content is not checked here (that is gates.py brief)."""
    root = os.path.abspath(arg or ".")
    if not os.path.isdir(os.path.join(root, "brief")):
        raise InputError("C-INPUT", root, "no brief/ folder; pass --project <project folder>")
    brief = read_json(os.path.join(root, "brief", "brief.json"), "brief/2")
    lang = brief.get("lang")
    lang = lang if isinstance(lang, str) and lang else ""
    labels = load_labels(lang) if _labels_file(lang) else {}
    style = read_json_opt(os.path.join(root, "brief", "deck-style.json")) or {}
    th = thresholds(style)
    selection = read_json_opt(os.path.join(root, "brief", "selection.json"))
    if selection is not None:
        _check_selection(selection)
    return Project(root=root, brief=brief, lang=lang, labels=labels, style=style, thresholds=th,
                   selection=selection)


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


def legible(fg: str, bg: str, ratio: float = 3.0) -> str | None:
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


def read_front_matter(concept: ConceptRef) -> tuple[dict, list[Finding]]:
    """Front matter of a concept's concept.md, with chosen/blocked paths checked (inside renders/, existing)."""
    md = os.path.join(concept.dir, "concept.md")
    if not os.path.isfile(md):
        return {"chosen": None, "blocked": [], "accent": None}, []
    prefix = f"concepts/{concept.set}/{concept.id}/concept.md"
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

    msg = "path must name an existing file inside this concept's renders/"
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
