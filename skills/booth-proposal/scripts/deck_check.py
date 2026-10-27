"""Deck check v2, text blocks and the review record (deck.py calls cmd_check, cmd_text and cmd_review_record).

resources/Images: every URL of the deck and what it points at (contract 5, D-IMG-*); run_check: structure,
placement, references, text lint, claims, numbers and layout; page_hashes and the review record (contract 2.6).
Read-only: nothing here writes a file except cmd_check --json (work/check.json) and cmd_review_record.
Pure ASCII: non-ASCII characters are written as unicode escapes.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from typing import NamedTuple
from urllib.parse import unquote

import booth_geometry
import common
import deck_html
from common import Finding
from deck_html import NUM_CLASSES, is_lbl, leaf_slots, page_lines, page_text, slides_of, visible_len, visible_text

SEC_SLOTS = {"sec", "num", "no", "section", "secno", "sec-no", "section-no", "number"}

# Number tokens: an optional unit suffix (percent, 10^4, 10^8, area units in CJK and Latin spelling, metres).
NUM_TOKEN = re.compile(
    r"(?<![A-Za-z0-9.#_\-/])(\d+(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(%|\u4e07|\u4ebf|\u33a1|m\u00b2|m2\b|\u5e73\u65b9\u7c73|\u5e73\u7c73|\u7c73|m(?![A-Za-z]))?")
FULLWIDTH = str.maketrans("\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19\uff0e\uff05",
                          "0123456789.%")


def norm_num(s):
    s = s.replace(",", "")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.lstrip("0") or "0"


def _read_text(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except OSError:
        return ""


def _unstamped(obj):
    """obj without the keys that hold hashes or times (references, *_at, *sha256): their digits are not facts."""
    if isinstance(obj, dict):
        return {k: _unstamped(v) for k, v in obj.items()
                if k != "references" and not (isinstance(k, str) and (k.endswith("_at") or k.endswith("sha256")))}
    if isinstance(obj, list):
        return [_unstamped(v) for v in obj]
    return obj


def corpus_numbers(project):
    """Every number the brief side knows: brief.json, ideas.json, the deck-style header, and per selected concept
    its concept.md, geometry.json and the geometry facts."""
    texts = [json.dumps(_unstamped(project.brief), ensure_ascii=False)]
    ideas = common.read_json_opt(project.path("brief", "ideas.json"))
    if ideas is not None:
        texts.append(json.dumps(_unstamped(ideas), ensure_ascii=False))
    texts.append(str(project.style.get("header") or ""))
    for key in (project.selection or {}).get("selected", []):
        try:
            c = common.concept_ref(project, key)
        except common.InputError:
            continue
        texts.append(_read_text(os.path.join(c.dir, "concept.md")))
        geo = os.path.join(c.dir, "geometry.json")
        if os.path.isfile(geo):
            texts.append(_read_text(geo))
            spec, _ = booth_geometry.load_spec(geo)
            if spec is not None:
                texts.append(json.dumps(booth_geometry.facts(spec), ensure_ascii=False))
    nums = set()
    for t in texts:
        t = re.sub(r"#[0-9A-Fa-f]{3,8}\b", " ", t.translate(FULLWIDTH))   # same exclusions as the slide text:
        for m in re.finditer(r"(?<![A-Za-z0-9.#_\-/])\d+(?:[.,]\d+)*", t):    # no hex, no D8 / PX-8 / v2
            s = m.group(0)
            if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?|\d+(\.\d+)?", s):
                nums.add(norm_num(s))
            else:                           # a list such as 3,4,5 or a version 1.2.3: each part
                nums.update(norm_num(x) for x in re.split(r"[.,]", s) if x)
    derived = set()
    for v in nums:
        try:
            x = float(v)
        except ValueError:
            continue
        for y in (x * 3.28084, x / 3.28084, x * 10.7639, x / 10.7639):   # m <-> ft, m2 <-> ft2
            derived.add(norm_num(f"{y:.1f}"))
            if y >= 20:                     # whole numbers only for large values, or every small integer passes
                derived.add(norm_num(f"{y:.0f}"))
    return nums | derived


def visible_numbers(sec):
    """Number tokens of a slide's visible text, without page references, section numbers, labels and hex colours."""
    parts = []

    def walk(n):
        for c in n.children:
            if c.tag == "#text":
                parts.append(html.unescape(c.raw))
            elif c.is_el and c.tag not in ("script", "style", "template", "code") and c.get("data-ref") is None \
                    and (c.get("data-slot") or "").lower() not in SEC_SLOTS and not is_lbl(c) \
                    and not any(x in NUM_CLASSES for x in c.classes()):
                walk(c)
                parts.append(" ")
    walk(sec)
    text = re.sub(r"#[0-9A-Fa-f]{3,8}\b", " ", " ".join(parts).translate(FULLWIDTH))
    out = []
    for m in NUM_TOKEN.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if (len(digits) >= 2 or m.group(2)) and not re.fullmatch(r"0\d", m.group(1)):
            out.append((m.group(0).strip(), norm_num(m.group(1))))
    return out


def has_image(sec):
    for n in sec.iter():
        if n.tag == "img" and n.get("src") and not any(
                "logo" in c for a in [n] + list(n.ancestors()) if a.is_el for c in a.classes()):
            return True
        if "url(" in (n.get("style") or ""):
            return True
    return False


# ---------- step 5: every URL of the deck, and what it points at ----------

CSS_ESC = re.compile(r"\\([0-9A-Fa-f]{1,6})[ \t\r\n\f]?|\\(.)", re.S)
URL_ATTRS = ("src", "href", "xlink:href", "poster", "data")
_SCHEME = re.compile(r"^[a-z][a-z0-9+.\-]*:")


def css_urls(css):
    """Every URL a piece of CSS loads: url(), image-set() strings and @import, after CSS escapes are decoded."""
    def unesc(m):
        if m.group(1):
            try:
                return chr(int(m.group(1), 16))
            except (ValueError, OverflowError):
                return ""
        return m.group(2)
    css = CSS_ESC.sub(unesc, re.sub(r"/\*.*?\*/", " ", css or "", flags=re.S))
    out = [next(g for g in m.groups() if g is not None).strip()
           for m in re.finditer(r"(?i)url\(\s*(?:\"([^\"]*)\"|'([^']*)'|([^)]*?))\s*\)", css)]
    for m in re.finditer(r"(?i)image-set\(", css):
        depth, i = 1, m.end()
        while i < len(css) and depth:
            depth += {"(": 1, ")": -1}.get(css[i], 0)
            i += 1
        inner = re.sub(r"(?i)url\([^)]*\)", " ", css[m.end():i - 1])
        out += [a or b for a, b in re.findall(r"\"([^\"]*)\"|'([^']*)'", inner)]
    out += [a or b for a, b in re.findall(r"(?i)@import\s+(?:\"([^\"]*)\"|'([^']*)')", css)]
    return [u for u in out if u]


def srcset_urls(v):
    if "data:" in v.lower():
        return [v.strip()]
    return [c.strip().split()[0] for c in v.split(",") if c.strip()]


def resources(root):
    """(element, attribute, url) for every URL under root (the node itself included): src, srcset, imagesrcset,
    href, xlink:href, poster, data, every style attribute and every <style> block; a <base> element is
    (element, "base", None). Style urls come back with the attribute name "style"."""
    out = []
    for n in [root] + list(root.iter()):
        if n.tag == "base":
            out.append((n, "base", None))
        if n.tag == "style":
            out += [(n, "style", u) for u in css_urls("".join(c.raw for c in n.children if c.tag == "#text"))]
        for k, v in n.attrs:
            if k == "style" and v is not None:
                out += [(n, "style", u) for u in css_urls(v)]
            elif k in ("srcset", "imagesrcset") and v is not None:
                out += [(n, k, u) for u in srcset_urls(v)]
            elif k in URL_ATTRS:
                out.append((n, k, v if v is not None else ""))
    return out


class ImageInfo(NamedTuple):
    url: str
    path: str | None
    rel: str | None
    sha256: str | None
    kind: str | None                       # "render" | "plan" | "logo" | "site" | None
    concept: "common.ConceptRef | None"
    problems: list                         # (code, level, message), independent of where the image is placed


def _short(url, n=60):
    u = " ".join(str(url).split())
    return u if len(u) <= n else u[:n - 3] + "..."


class Images:
    """Resolves the URLs of a deck to files and checks what each file may be used for (contract 5, 6.6).
    Results are cached by real path; the forbidden-hash set is computed once."""

    def __init__(self, project):
        self.project = project
        self._forbidden = None
        self._ref_hashes = None
        self._by_real = {}
        self._by_url = {}
        lp = deck_html.logo_path(project)
        self._logo_real = common.real(lp) if lp else None

    @property
    def forbidden(self):
        if self._forbidden is None:
            self._forbidden = common.forbidden_hashes(self.project)
        return self._forbidden

    @property
    def reference_hashes(self):
        if self._ref_hashes is None:
            out = set()
            refs = self.project.brief.get("references")
            sets = refs.get("sets") if isinstance(refs, dict) else None
            for s in sets if isinstance(sets, list) else []:
                files = s.get("files") if isinstance(s, dict) else None
                for f in files if isinstance(files, list) else []:
                    if isinstance(f, dict) and isinstance(f.get("sha256"), str):
                        out.add(f["sha256"])
            self._ref_hashes = out
        return self._ref_hashes

    def resolve(self, url, attr):
        """ImageInfo for one URL, or None for an in-page "#..." href."""
        key = (url, attr == "base")
        if key not in self._by_url:
            self._by_url[key] = self._resolve(url or "", attr)
        return self._by_url[key]

    def _fail(self, shown, code, message):
        return ImageInfo(shown, None, None, None, None, None, [(code, "error", message)])

    def _resolve(self, url, attr):
        project = self.project
        raw = url.strip()
        shown = _short(raw) if raw else "<empty>"
        if attr == "base":
            return self._fail(raw or "<base>", "D-IMG-URL",
                              "scheme: a <base> element changes where every image loads from")
        if attr in ("href", "xlink:href") and raw.startswith("#"):
            return None
        low = raw.lower()
        m = _SCHEME.match(low)
        if low.startswith(("//", "\\\\")):
            return self._fail(shown, "D-IMG-URL", f"scheme: a network path is not allowed ({shown}); "
                                                  "use a file inside the project")
        if low.startswith(("data:", "http:", "https:")) or (m and len(m.group(0)) - 1 >= 2):
            name = m.group(0) if m else "scheme"
            return self._fail(shown, "D-IMG-URL", f"scheme: {name} URLs are not allowed ({shown}); "
                                                  "use a file inside the project")
        path = unquote(re.split(r"[?#]", raw)[0]).replace("\\", "/")
        if re.match(r"^/[A-Za-z]:/", path):
            path = path[1:]
        if not path:
            return self._fail(shown, "D-IMG-URL", "missing: the image URL is empty")
        full = os.path.normpath(path if os.path.isabs(path) or re.match(r"^[A-Za-z]:", path)
                                else os.path.join(project.path("pack"), path))
        if not os.path.isfile(full):
            return self._fail(shown, "D-IMG-URL", f"missing: image file not found ({shown})")
        if not common.inside(project.root, full):
            return self._fail(shown, "D-IMG-URL", f"outside: {shown} lies outside the project folder")
        rp = common.real(full)
        if rp in self._by_real:
            return self._by_real[rp]._replace(url=shown)
        try:
            sha = common.sha256_file(full)
        except OSError:
            return self._fail(shown, "D-IMG-URL", f"missing: image file cannot be read ({shown})")
        info = self._classify(full, rp, sha, shown)
        self._by_real[rp] = info
        return info

    def _classify(self, full, rp, sha, shown):
        project = self.project
        rel = project.rel(full)
        problems = []

        def info(kind, concept=None):
            return ImageInfo(shown, full, rel, sha, kind, concept, problems)

        def forbid(msg):
            problems.append(("D-IMG-FORBIDDEN", "error", msg))

        if rp == self._logo_real or common.inside(project.path("brief", "brand"), full):
            if sha in self.reference_hashes:
                forbid(f"logo-ref: the logo {rel} has the same content as a reference image")
            return info("logo")
        if sha in self.forbidden:
            forbid(f"forbidden: same content as {self.forbidden[sha]}")
            return info(None)
        c = common.concept_of_path(project, full)
        base = os.path.basename(full).lower()
        ext = os.path.splitext(base)[1]
        folder = os.path.dirname(rp)
        if c is not None and folder == common.real(os.path.join(c.dir, "renders")) and ext in common._IMAGE_EXTS:
            self._render_problems(c, full, rp, sha, rel, problems)
            return info("render", c)
        if c is not None and folder == common.real(c.dir):
            if base in ("plan.png", "plan.svg"):
                self._plan_problems(c, full, sha, problems)
                return info("plan", c)
            if base.startswith("massing-") and ext == ".png":
                forbid("massing: massing images are internal and never go in the deck")
                return info(None, c)
        if rp == common.real(project.path("pack", "site.svg")):
            return info("site")
        forbid(f"kind: {rel} is not a render, plan, logo or pack/site.svg")
        return info(None, c)

    def _selection_problem(self, c, problems):
        sel = self.project.selection
        if sel is not None and c.key not in (sel.get("selected") or []):
            problems.append(("D-IMG-RENDER", "error", f"unselected: {c.key} is not in brief/selection.json"))

    def _render_problems(self, c, full, rp, sha, rel, problems):
        project = self.project

        def bad(msg):
            problems.append(("D-IMG-RENDER", "error", msg))

        sc = common.read_sidecar(full)
        version = common.sidecar_version(sc)
        if version == 0:
            bad(f"sidecar: {rel} has no sidecar; make it with render.py")
        elif version == 1:
            problems.append(("C-LEGACY", "warn", f"v1 sidecar: {rel} has an old sidecar; "
                                                 "its hashes and base chain are not checked"))
        else:
            outputs = sc.get("outputs")
            if not isinstance(outputs, dict) or outputs.get(os.path.basename(full)) != sha:
                bad(f"sidecar: the sidecar hash differs from {rel}; the image changed after it was made")
            else:
                if sc.get("mode") == "label":
                    problems.append(("D-IMG-FORBIDDEN", "error",
                                     "label: a labelled copy (render.py label) is never used in the deck"))
                _, finding = common.trace_base_chain(project, full)
                if finding is not None:
                    bad(finding.message)
        ok, why = common.review_is_current_pass(full, True)
        if not ok:
            bad(f"review: {why}")
        self._selection_problem(c, problems)
        fm, fm_findings = common.read_front_matter(c)
        chosen = fm.get("chosen")
        if chosen is None or common.real(os.path.join(c.dir, chosen)) != rp:
            more = "; concept.md front matter is invalid" if any(f.code == "G-FM" for f in fm_findings) else ""
            bad(f"not-chosen: {rel} is not the chosen render in concept.md{more}")
        if any(common.real(os.path.join(c.dir, b)) == rp for b in fm.get("blocked") or []):
            bad(f"blocked: concept.md lists {rel} under blocked")

    def _plan_problems(self, c, full, sha, problems):
        sc = common.read_sidecar(full)
        outputs = sc.get("outputs") if common.sidecar_version(sc) == 2 else None
        if not isinstance(outputs, dict) or outputs.get(os.path.basename(full)) != sha:
            problems.append(("D-IMG-RENDER", "error", f"sidecar: {self.project.rel(full)} has no current v2 sidecar; "
                                                      "run draw_plan.py plan"))
        else:
            geo = os.path.join(c.dir, "geometry.json")
            geo_sha = common.sha256_file(geo) if os.path.isfile(geo) else None
            specs = [i for i in (sc.get("inputs") or []) if isinstance(i, dict) and i.get("role") == "spec"]
            if not specs or any(i.get("sha256") != geo_sha for i in specs):
                problems.append(("D-IMG-RENDER", "error", "stale: the plan was drawn from another geometry.json; "
                                                          "run draw_plan.py plan"))
        self._selection_problem(c, problems)


# ---------- text vocabulary (D-TXT-*) ----------

_FILE_RE = re.compile(r"(?i)\b[\w.-]+\.(?:png|jpe?g|webp|json|md|svg|txt|pdf|html)\b")
_NAME = r"[A-Za-z0-9_.-]"          # a path part is ASCII: CJK text next to it has no spaces
_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(common.PROJECT_FOLDERS) + r")[/\\](" + _NAME
                      + r"+(?:[/\\]" + _NAME + r"+)*)", re.IGNORECASE)
_WHAT = {"todo": "working-note marker", "id": "brief ID", "set": "reference set name",
         "file": "file name or path", "source": "brief source text", "source-col": "source column header",
         "dnm": "do-not-mention phrase", "phrase": "reference phrase"}


def _quotes(s):
    return s.replace("\u2018", "'").replace("\u2019", "'")


def css_unquote(v):
    v = (v or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return re.sub(r"\\3C ?", "<", v).replace('\\"', '"').replace("\\\\", "\\")


def squash(s):
    """Claim matching text: half-width digits, no thousands commas, no spaces, lower case."""
    s = (s or "").translate(FULLWIDTH)
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)
    return re.sub(r"\s+", "", s).lower()


class _Vocab:
    """Everything the text rules match against, read once per check."""

    def __init__(self, project):
        lab, brief = project.labels, project.brief
        self.todo = [x for x in lab.get("todo_markers") or [] if isinstance(x, str) and x]
        self.source_headers = [x.casefold() for x in lab.get("source_headers") or [] if isinstance(x, str)]
        self.phrases = [x for x in lab.get("reference_phrases") or [] if isinstance(x, str) and x]
        self.evolution = [x for x in lab.get("evolution_words") or [] if isinstance(x, str) and x]
        self.comparison = [x for x in lab.get("comparison_words") or [] if isinstance(x, str) and x]
        self.dnm = [x for x in brief.get("do_not_mention") or [] if isinstance(x, str) and len(x) >= 2]

        def items(key):
            v = brief.get(key)
            return [i for i in v if isinstance(i, dict)] if isinstance(v, list) else []

        ids = {}
        for key in ("design_points", "claims", "assumptions"):
            for it in items(key):
                if isinstance(it.get("id"), str) and it["id"]:
                    ids[it["id"]] = True
        ideas = common.read_json_opt(project.path("brief", "ideas.json")) or {}
        for it in ideas.get("insights") if isinstance(ideas.get("insights"), list) else []:
            if isinstance(it, dict) and isinstance(it.get("id"), str) and it["id"]:
                ids[it["id"]] = True
        client = brief.get("client") if isinstance(brief.get("client"), dict) else {}
        protect = [x for x in list(client.get("names") or []) + list(brief.get("protected_terms") or [])
                   if isinstance(x, str)]
        protect += [it["text"] for k in ("design_points", "claims") for it in items(k)
                    if isinstance(it.get("text"), str)]
        self.ids = list(ids)
        self.protect = protect
        sets = {c.set for c in common.list_concepts(project)}
        refs = brief.get("references")
        for s in refs.get("sets") if isinstance(refs, dict) and isinstance(refs.get("sets"), list) else []:
            if isinstance(s, dict) and isinstance(s.get("id"), str):
                sets.add(s["id"])
        self.sets = sorted((s for s in sets if s != common._LEGACY_SET), key=lambda s: (-len(s), s))
        files = set()
        for _, _, names in os.walk(project.path("input")):
            files.update(names)
        self.layout_names = set()                  # names the project has below its folders (a path tail may be one)
        for folder in ("input", "brief", "concepts", "pack", "work"):
            for n, (_, dirs, names) in enumerate(os.walk(project.path(folder))):
                self.layout_names.update(x.lower() for x in dirs + names)
                if n > 400:
                    break
        self.input_files = sorted(files, key=lambda s: (-len(s), s))
        sources = []
        booth = brief.get("booth")
        if isinstance(booth, dict):
            sources.append(booth.get("source"))
        sources += [it.get("source") for k in ("design_points", "claims") for it in items(k)]
        self.sources = sorted({s for s in sources if isinstance(s, str) and len(s) >= 4})

    def internal(self, text, headers=()):
        """(rule, entry) for every D-TXT-INTERNAL hit in the text; headers = the th texts of the slide."""
        out = []
        out += [("todo", t) for t in self.todo if common.find_term(t, text, True)]
        left = text                                 # an id inside a client name, protected term or claim text is
        for t in self.protect:                      # that text, not a reference: blank those spans, look at the rest
            for a, b in common.find_term(t, left, False):
                left = left[:a] + " " * (b - a) + left[b:]
        out += [("id", i) for i in self.ids if common.find_term(i, left, True)]
        out += [("set", s) for s in self.sets if common.find_term(s, text, False)]
        hits = {}
        for m in _FILE_RE.finditer(text):
            hits.setdefault(m.group(0).lower(), m.group(0))
        for m in _PATH_RE.finditer(text):
            tail = re.split(r"[/\\]", m.group(2).rstrip(".-"))
            if m.group(1).lower() in common.PLAIN_WORD_FOLDERS and len(tail) == 1 \
                    and not (re.search(r"[.][A-Za-z0-9]{1,5}$", tail[0]) or tail[0].lower() in self.layout_names
                             or tail[0].lower() in common.PROJECT_FOLDERS):
                continue                            # work/life: an ordinary word pair, not a project path
            t = m.group(0).rstrip(".-")
            hits.setdefault(t.lower(), t)
        for name in self.input_files:
            if common.find_term(name, text, False):
                hits.setdefault(name.lower(), name)
        out += [("file", h) for h in hits.values()]
        flat = " ".join(text.split())
        out += [("source", s) for s in self.sources if s in flat]
        out += [("source-col", h) for h in headers if h.casefold() in self.source_headers]
        return out

    def reference(self, text):
        q = _quotes(text)
        out = [("dnm", t) for t in self.dnm if common.find_term(_quotes(t), q, False)]
        out += [("phrase", t) for t in self.phrases if common.find_term(_quotes(t), q, False)]
        return out

    def pending(self, text):
        out = [("evolution", t) for t in self.evolution if common.find_term(t, text, False)]
        out += [("comparison", t) for t in self.comparison if common.find_term(t, text, False)]
        return out


def claim_keys(claim, th):
    """Patterns that find a claim in squash(visible text): its numbers (digits >= claim_min_digits, or with a unit
    suffix; years skipped) and its `keys` phrases. A claim without either is never matched."""
    keys = []
    for m in re.finditer(r"(?<![\d.])(\d+(?:\.\d+)?)(%|\u4e07|\u4ebf|\+)?", squash(claim.get("text"))):
        digits, suffix = m.group(1).replace(".", ""), m.group(2)
        if not suffix and re.fullmatch(r"19\d\d|20\d\d", m.group(1)):
            continue
        if suffix or len(digits) >= th["claim_min_digits"]:
            keys.append(re.compile(r"(?<![\d.])" + re.escape(m.group(0)) + r"(?![\d])"))
    for k in claim.get("keys") or []:
        if isinstance(k, str) and squash(k):
            keys.append(re.compile(re.escape(squash(k))))
    return keys


# ---------- step 6-7: run_check ----------

class CheckResult(NamedTuple):
    findings: list
    slides: int
    deck_sha256: str
    root: "deck_html.Node"
    pending: list


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def read_record(project):
    """work/deck-review.json, or None when there is none; a file of another schema is C-INPUT."""
    path = project.path("work", "deck-review.json")
    return common.read_json(path, "deck-review/1") if os.path.isfile(path) else None


def _read_render_json(project):
    path = project.path("work", "render.json")
    return common.read_json(path, "render/1") if os.path.isfile(path) else None


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def run_check(project, deck_text=None, render_json=True) -> CheckResult:
    """The check of the whole deck. Writes nothing. deck_text None reads pack/proposal.html (a missing deck is a
    DeckError); render_json False ignores work/render.json (deck.py render calls it before it measures)."""
    if not project.labels:
        raise common.InputError("C-INPUT", f"assets/labels/{project.lang}.json", "no label file for this lang")
    if deck_text is None:
        deck_text = deck_html.read_deck(project)
        if deck_text is None:
            raise deck_html.DeckError("no pack/proposal.html; run deck.py new")
    sha = common.sha256_text(deck_text)
    root = deck_html.parse(deck_text)
    slides = slides_of(root)
    th = project.thresholds
    sel = project.selection
    out = []

    def add(code, level, where, message, page=None, page_id=None):
        out.append(Finding(code, level, where, message, page, page_id))

    info_of = {id(s): (n, s.get("data-id") or "", s.get("data-role") or "") for n, s in enumerate(slides, 1)}
    ids_of = {v[0]: v[1] for v in info_of.values()}

    def slide_add(code, level, n, message):
        add(code, level, f"page {n} {ids_of[n]}".rstrip(), message, n, ids_of[n] or None)

    # selection
    if sel is None:
        add("G-SELECT", "error", "brief/selection.json", "no brief/selection.json; run gates.py select")

    # structure
    seen = set()
    roles = []
    for n, s in enumerate(slides, 1):
        _, pid, role = info_of[id(s)]
        roles.append(role)
        if not pid.strip():
            slide_add("D-STRUCT", "error", n, "id: the slide has no data-id")
        elif pid in seen:
            slide_add("D-STRUCT", "error", n, f"id: data-id '{pid}' is used twice")
        elif not _ID_RE.fullmatch(pid):
            slide_add("D-STRUCT", "error", n, f"id: data-id '{pid}' must match [a-z0-9][a-z0-9-]*")
        seen.add(pid)
        if role not in common.ROLES:
            slide_add("D-STRUCT", "error", n, f"role: data-role '{role}' is missing or not a known role")
        for fig in (x for x in s.iter() if x.tag == "figure"):
            if any(a.tag == "figure" for a in fig.ancestors()):
                slide_add("D-STRUCT", "error", n, "nest: a figure inside a figure")
        for x in s.iter():
            if x.has_class("placeholder"):
                slide_add("D-STRUCT", "error", n, "placeholder: a placeholder element is still on the page")
    if "cover" not in roles:
        add("D-STRUCT", "error", "deck", "cover: the deck has no slide with data-role cover")
    if sel is not None:
        display = sel.get("display") if isinstance(sel.get("display"), dict) else {}
        for key in sel.get("selected") or []:
            letter = display.get(key)
            if letter and not any(s.get("data-role") == "board" and s.get("data-concept") == letter for s in slides):
                add("D-STRUCT", "error", key, f"board: concept {letter} ({key}) has no board slide")

    # images: every URL once, placement, reuse
    images = Images(project)
    uses = []                                   # (slide tuple | None, node, ImageInfo)
    for node, attr, url in resources(root):
        info = images.resolve(url or "", attr)
        if info is None:
            continue
        sec = next((a for a in [node] + list(node.ancestors()) if id(a) in info_of), None)
        uses.append((info_of[id(sec)] if sec is not None else None, node, info))
    done = set()
    for loc, node, info in uses:
        key = (info.path or info.url, loc[0] if loc else None)
        if key in done:
            continue
        done.add(key)
        where = f" (page {loc[0]} {loc[1]})".replace(" )", ")") if loc else ""
        for code, level, message in info.problems:
            add(code, level, info.rel or info.url, message + where, loc[0] if loc else None,
                (loc[1] or None) if loc else None)
    placed = set()
    for loc, node, info in uses:
        if info.kind != "render" or loc is None or id(node) in placed:
            continue
        placed.add(id(node))
        n, pid, role = loc
        fig = next((a for a in node.ancestors() if a.tag == "figure"), None)
        in_render = fig is not None and fig.has_class("render")
        if node.tag != "img" or not in_render:
            slide_add("D-PLACE", "error", n, f"figure: the render {info.rel} must be an img inside figure.render")
        if role in ("materials", "interaction") and not (in_render and fig.has_class("annotated")):
            slide_add("D-PLACE", "error", n, f"hero: a render on the {role} page must sit in figure.render.annotated")
    lead = (sel or {}).get("lead")
    pages_of = {}
    for loc, node, info in uses:
        if loc is None or not info.sha256 or info.kind == "logo":
            continue
        n, pid, role = loc
        if role in ("cover", "overview", "board", "compare"):
            continue
        if role == "annotated" and info.kind == "render" and info.concept is not None and info.concept.key == lead:
            continue
        pages_of.setdefault(info.sha256, [])
        if n not in pages_of[info.sha256]:
            pages_of[info.sha256].append(n)
    for sha_, pages in pages_of.items():
        if len(pages) > th["image_reuse_max"]:
            slide_add("D-REUSE", "warn", pages[th["image_reuse_max"]],
                      f"image used on {len(pages)} counted pages (max {th['image_reuse_max']})")

    # page references
    record = read_record(project)
    points = {p.get("id") for p in project.brief.get("design_points") or [] if isinstance(p, dict)}
    for node, target, expected in deck_html.compute_refs(root, project, record):
        sec = next((a for a in node.ancestors() if id(a) in info_of), None)
        if sec is None:
            continue
        n = info_of[id(sec)][0]
        if not target:
            slide_add("D-REF", "error", n, "target: data-ref is empty")
        elif target in points and not expected:
            slide_add("D-REF", "error", n, f"target: no page covers design point {target} yet")
        elif target not in points and not expected:
            slide_add("D-REF", "error", n, f"target: data-ref '{target}' names no design point or page")
        elif " ".join(node.text().split()) != expected:
            slide_add("D-REF", "error", n, f"stale: reference text should read '{expected}'; run deck.py render")

    # text
    vocab = _Vocab(project)
    pending = []
    for n, s in enumerate(slides, 1):
        text = visible_text(s)
        headers = [" ".join(x.text().split()) for x in s.iter()
                   if x.tag == "th" or (x.tag == "td" and any(a.tag == "thead" for a in x.ancestors()))]
        for rule, entry in vocab.internal(text, headers):
            slide_add("D-TXT-INTERNAL", "error", n, f'{rule}: {_WHAT[rule]} "{entry}" on a client page')
        for rule, entry in vocab.reference(text):
            slide_add("D-TXT-REFERENCE", "error", n, f'{rule}: {_WHAT[rule]} "{entry}" on a client page')
        for rule, entry in vocab.pending(text):
            slide_add("D-TXT-PENDING", "pending", n, f'{rule} word "{entry}" \u2013 decide in review pass 1')
            pending.append(out[-1])
    m = deck_html.TOKENS_RE.search(deck_text)
    tokens = deck_html.parse_vars(m.group(2)) if m else {}
    for var in ("--header", "--stamp"):
        value = css_unquote(tokens.get(var, ""))
        if not value:
            continue
        where = f"tokens {var}"
        for rule, entry in vocab.internal(value):
            add("D-TXT-INTERNAL", "error", where, f'{rule}: {_WHAT[rule]} "{entry}" in the {var} token')
        for rule, entry in vocab.reference(value):
            add("D-TXT-REFERENCE", "error", where, f'{rule}: {_WHAT[rule]} "{entry}" in the {var} token')

    # claims
    claims = [(c["id"], claim_keys(c, th)) for c in project.brief.get("claims") or []
              if isinstance(c, dict) and c.get("flag") is True and isinstance(c.get("id"), str)]
    first_use, signoff_tagged = {}, set()
    for n, s in enumerate(slides, 1):
        tagged = set()
        for x in [s] + list(s.iter()):
            tagged.update((x.get("data-claim") or "").split())
        if s.get("data-role") == "signoff":
            signoff_tagged |= tagged
        squashed = squash(visible_text(s))
        for cid, keys in claims:
            if keys and any(k.search(squashed) for k in keys):
                first_use.setdefault(cid, n)
                if cid not in tagged:
                    slide_add("D-CLAIM", "error", n, f"untagged: the page uses claim {cid} without data-claim=\"{cid}\"")
    for cid, n in first_use.items():
        if cid not in signoff_tagged:
            slide_add("D-CLAIM", "error", n, f"signoff: claim {cid} is used but no signoff page carries "
                                             f"data-claim=\"{cid}\"")

    # numbers
    corpus = corpus_numbers(project)
    for n, s in enumerate(slides, 1):
        shown = set()
        for token, norm in visible_numbers(s):
            if norm not in corpus and token not in shown:
                shown.add(token)
                slide_add("D-NUMBER", "warn", n, f'"{token}" is not in the brief, ideas or selected concept material')

    # layout
    appendix, run = [], []

    def flush_run():
        if len(run) > th["imageless_run_max"]:
            slide_add("D-LAYOUT", "warn", run[0],
                      f"imageless: slides {run[0]}-{run[-1]}: {len(run)} pages in a row without an image")
        run.clear()

    for n, s in enumerate(slides, 1):
        for slot in leaf_slots(s):
            cap = slot.get("data-max")
            if cap and cap.isdigit():
                length = visible_len(deck_html.slot_text(slot))
                if length > int(cap):
                    slide_add("D-LAYOUT", "warn", n, f'max: slot "{slot.get("data-slot")}" has {length} characters '
                                                     f"(max {cap}); cut {length - int(cap)}")
        if s.get("data-part") == "appendix":
            appendix.append(n)
            flush_run()
        elif has_image(s):
            flush_run()
        else:
            run.append(n)
    flush_run()
    if len(appendix) > th["appendix_pages_max"]:
        slide_add("D-LAYOUT", "warn", appendix[th["appendix_pages_max"]],
                  f"appendix: {len(appendix)} appendix pages (max {th['appendix_pages_max']})")

    # measured results
    rj = _read_render_json(project) if render_json else None
    if rj is not None and rj.get("deck_sha256") == sha:
        for e in rj.get("upscale") if isinstance(rj.get("upscale"), list) else []:
            f = _num(e.get("factor")) if isinstance(e, dict) else None
            if f is not None and f > th["upscale_max"]:
                page, pid = _int(e.get("page")), e.get("page_id")
                add("D-LAYOUT", "warn", f"page {page} {pid}".rstrip(),
                    f"upscale: an image is enlarged {f:g} times (max {th['upscale_max']:g}); use a larger render",
                    page, pid if isinstance(pid, str) and pid else None)
        for e in rj.get("overflow") if isinstance(rj.get("overflow"), list) else []:
            if isinstance(e, dict):
                page, pid = _int(e.get("page")), e.get("page_id")
                add("D-OVERFLOW", "error", f"page {page} {pid} {e.get('slot')}",
                    f"overflow by {e.get('px')} px (~{e.get('chars')} chars)",
                    page, pid if isinstance(pid, str) and pid else None)

    out.sort(key=lambda f: (f.page is None, f.page or 0, f.code))
    return CheckResult(out, len(slides), sha, root, [f for f in out if f.code == "D-TXT-PENDING"])


# ---------- step 8: check ----------

def _usage(e) -> int:
    print(f"error: {e}", file=sys.stderr)
    return 2


def cmd_check(project, as_json) -> int:
    try:
        res = run_check(project)
    except deck_html.DeckError as e:
        return _usage(e)
    code = common.print_findings(res.findings, as_json)
    if as_json:
        counts = {lv: sum(1 for f in res.findings if f.level == lv) for lv in ("error", "warn", "pending")}
        common.write_json(project.path("work", "check.json"), {
            "schema": "check/1", "deck_sha256": res.deck_sha256, "checked_at": common.now_iso(),
            "slides": res.slides, "counts": counts, "findings": [f._asdict() for f in res.findings]})
    return code


# ---------- step 10: text, page hashes, review record ----------

def page_hashes(project, root, images) -> dict:
    """{page_id: {"text_sha256", "image_sha256s"}} for every slide with a data-id."""
    out = {}
    for s in slides_of(root):
        pid = s.get("data-id")
        if not pid:
            continue
        shas = set()
        for node, attr, url in resources(s):
            info = images.resolve(url or "", attr)
            if info is not None and info.sha256:
                shas.add(info.sha256)
        out.setdefault(pid, {"text_sha256": common.sha256_text(page_text(s)), "image_sha256s": sorted(shas)})
    return out


def _block(n, slide) -> list:
    return [f"=== {n} {slide.get('data-id') or ''} [{slide.get('data-role') or ''}] ===", *page_lines(slide), ""]


def cmd_text(project, diff) -> int:
    text = deck_html.read_deck(project)
    if text is None:
        return _usage("no pack/proposal.html; run deck.py new")
    root = deck_html.parse(text)
    slides = slides_of(root)
    if not diff:
        print("\n".join(line for n, s in enumerate(slides, 1) for line in _block(n, s)))
        return 0
    record = read_record(project)
    if record is None:
        return _usage("no work/deck-review.json; run a full review first")
    old = record.get("pages") if isinstance(record.get("pages"), dict) else {}
    cur = page_hashes(project, root, Images(project))
    lines, show = [], []
    for pid in cur:
        if pid not in old:
            lines.append(f"ADDED {pid}")
            show.append(pid)
            continue
        was = old[pid] if isinstance(old[pid], dict) else {}
        t = was.get("text_sha256") != cur[pid]["text_sha256"]
        i = list(was.get("image_sha256s") or []) != cur[pid]["image_sha256s"]
        if t or i:
            lines.append(f"CHANGED {pid} ({'text+images' if t and i else 'text' if t else 'images'})")
            show.append(pid)
    lines += [f"REMOVED {pid}" for pid in old if pid not in cur]
    if not lines:
        print(f"no changes since {record.get('recorded_at')}")
        return 0
    out = lines + [""]
    for n, s in enumerate(slides, 1):
        if s.get("data-id") in show:
            out += _block(n, s)
    print("\n".join(out))
    return 0


_REVIEWERS = ("subagent", "self")
_ACTIONS = ("rewritten", "kept")
_DECISIONS = ("narrates_reference", "keep")
_KINDS = ("mismatch", "design_intent", "title_is_label", "cover", "adjacent_layout", "other")
# list name -> (pass, {field: kind}); kinds: "str", "id" (a slide id), "point", "code", or a tuple of choices, "bool"
_LISTS = {
    "unexplained": ("pass1", {"page_id": "id", "quote": "str", "action": _ACTIONS}),
    "internal_notes": ("pass1", {"page_id": "id", "quote": "str", "action": _ACTIONS}),
    "coverage": ("pass1", {"point": "point", "page_id": "id", "quote": "str"}),
    "pending": ("pass1", {"code": "code", "page_id": "id", "text": "str", "decision": _DECISIONS,
                          "note": "note"}),
    "findings": ("pass2", {"page_id": "id", "kind": _KINDS, "note": "note", "resolved": "bool"}),
}


def _validate(project, path, data, page_ids, points):
    """Shape of the review input (contract 2.6); returns {list name: [normalised items]} and the reviewers."""
    base = project.rel(path)

    def bad(loc, message):
        raise common.InputError("C-INPUT", f"{base}:{loc}", message)

    if not any(k in data for k in ("pass1", "pass2")):
        raise common.InputError("C-INPUT", base, "expected pass1 and/or pass2")
    reviewers, lists = {}, {name: [] for name in _LISTS}
    for pn in ("pass1", "pass2"):
        block = data.get(pn)
        if block is None:
            continue
        if not isinstance(block, dict):
            bad(pn, "expected an object")
        r = block.get("reviewer")
        if r is not None and r not in _REVIEWERS:
            bad(f"{pn}.reviewer", 'expected "subagent" or "self"')
        reviewers[pn] = r
        for name, (owner, fields) in _LISTS.items():
            if owner != pn or block.get(name) is None:
                continue
            seq = block[name]
            if not isinstance(seq, list):
                bad(f"{pn}.{name}", "expected a list")
            for i, item in enumerate(seq):
                loc = f"{pn}.{name}[{i}]"
                if not isinstance(item, dict):
                    bad(loc, "expected an object")
                norm = {}
                for field, kind in fields.items():
                    v = item.get(field)
                    where = f"{loc}.{field}"
                    if kind == "note":
                        if v is not None and not isinstance(v, str):
                            bad(where, "expected a string")
                        v = v or ""
                    elif kind == "bool":
                        if not isinstance(v, bool):
                            bad(where, "expected true or false")
                    elif isinstance(kind, tuple):
                        if v not in kind:
                            bad(where, "expected one of " + ", ".join(kind))
                    else:
                        if not isinstance(v, str) or not v.strip():
                            bad(where, "expected a non-empty string")
                        if kind == "id" and v not in page_ids:
                            bad(where, f"'{v}' names no slide of the deck")
                        if kind == "point" and v not in points:
                            bad(where, f"'{v}' is not a design point of brief.json")
                        if kind == "code" and v != "D-TXT-PENDING":
                            bad(where, 'expected "D-TXT-PENDING"')
                    norm[field] = v
                lists[name].append(norm)
    return lists, reviewers


def pending_key(finding):
    """(code, page_id, entry) of a D-TXT-PENDING finding; the entry is the word as the labels file spells it."""
    m = re.search(r'word "(.*)" \u2013', finding.message)
    return finding.code, finding.page_id, m.group(1) if m else ""


def cmd_review_record(project, path) -> int:
    data = common.read_json(path)
    text = deck_html.read_deck(project)
    if text is None:
        return _usage("no pack/proposal.html; run deck.py new")
    res = run_check(project, text, render_json=False)
    slides = slides_of(res.root)
    page_ids = {s.get("data-id") for s in slides if s.get("data-id")}
    points = {p.get("id") for p in project.brief.get("design_points") or [] if isinstance(p, dict)}
    lists, reviewers = _validate(project, path, data, page_ids, points)
    old = read_record(project) or {}
    hashes = page_hashes(project, res.root, Images(project))
    flat = {}
    for s in slides:
        if s.get("data-id"):
            flat.setdefault(s.get("data-id"), s)

    def collapse(s):
        return " ".join(s.split())

    errors = []
    for item in lists["coverage"]:
        if collapse(item["quote"]) not in collapse(page_text(flat[item["page_id"]])):
            errors.append(f"error: coverage {item['point']} quote not found on {item['page_id']}")

    # merge: old items of unchanged pages stay unless the input names the page in the same list
    old_pages = old.get("pages") if isinstance(old.get("pages"), dict) else {}
    unchanged = {pid for pid, h in hashes.items() if isinstance(old_pages.get(pid), dict)
                 and old_pages[pid].get("text_sha256") == h["text_sha256"]
                 and list(old_pages[pid].get("image_sha256s") or []) == h["image_sha256s"]}
    merged = {}
    for name, (owner, _) in _LISTS.items():
        was = old.get(owner) if isinstance(old.get(owner), dict) else {}
        previous = was.get(name) if isinstance(was.get(name), list) else []
        named = {i["page_id"] for i in lists[name]}
        kept = [i for i in previous if isinstance(i, dict) and i.get("page_id") in unchanged
                and i.get("page_id") not in named]
        merged[name] = kept + lists[name]
    decided = {("D-TXT-PENDING", i["page_id"], i["text"].casefold()): i["decision"] for i in merged["pending"]
               if isinstance(i.get("text"), str) and isinstance(i.get("page_id"), str)}
    for f in res.pending:
        code, page_id, entry = pending_key(f)
        if (code, page_id, entry.casefold()) not in decided:
            errors.append(f'error: pending {code} {page_id} "{entry}" has no decision')
    for item in merged["pending"]:
        s = flat.get(item.get("page_id"))
        if item.get("decision") == "narrates_reference" and s is not None \
                and common.find_term(item["text"], visible_text(s), False):
            errors.append(f'error: {item["page_id"]} still contains "{item["text"]}" decided narrates_reference; '
                          "rewrite it")
    reviewer_of = {}
    for pn in ("pass1", "pass2"):
        was = old.get(pn) if isinstance(old.get(pn), dict) else {}
        reviewer_of[pn] = reviewers.get(pn) or was.get("reviewer")
        if pn in reviewers and reviewer_of[pn] is None:
            raise common.InputError("C-INPUT", f"{project.rel(path)}:{pn}.reviewer", 'expected "subagent" or "self"')
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    record = {"schema": "deck-review/1", "pages": hashes,
              "pass1": {k: merged[k] for k in ("unexplained", "internal_notes", "coverage", "pending")},
              "pass2": {"findings": merged["findings"]}, "recorded_at": common.now_iso()}
    for pn in ("pass1", "pass2"):
        if reviewer_of[pn]:
            record[pn] = {"reviewer": reviewer_of[pn], **record[pn]}
    common.write_json(project.path("work", "deck-review.json"), record)
    print(f"recorded: {len(hashes)} pages, {len(merged['coverage'])} coverage quotes, "
          f"{len(merged['pending'])} pending decisions, {len(merged['findings'])} pass-2 findings")
    return 0
