"""Deck HTML tree, template catalogue and emit, tokens, deck I/O, page references, text extraction.

deck.py calls cmd_new, cmd_style and cmd_layouts; deck_check and deck_render use the rest.
Pure ASCII: non-ASCII characters are written as unicode escapes.
"""
from __future__ import annotations

import datetime
import html
import os
import re
import shutil
import sys
from html.parser import HTMLParser
from typing import NamedTuple

import common
from common import LEGIBLE_RATIO, contrast, hex_rgb

DEFAULT_TEMPLATE = os.path.join(common.SKILL_DIR, "assets", "deck", "template.html")

NUM_CLASSES = ("n", "no", "num", "number", "idx")
COLOR_VARS = (("paper", "--paper"), ("surface", "--surface"), ("tint", "--tint"), ("line", "--line"),
              ("muted", "--muted"), ("muted_text", "--muted-text"), ("ink", "--ink"), ("ink_strong", "--ink-strong"),
              ("primary", "--primary"), ("primary_alt", "--primary-alt"), ("accent", "--accent"),
              ("brand_extra", "--brand-extra"), ("warn", "--warn"))
NEUTRAL_TOKENS = {   # used only when the template has no tokens block
    "--paper": "#FAFAF7", "--surface": "#F1F0EB", "--tint": "#E6E4DD", "--line": "#D6D3CA", "--muted": "#A19D93",
    "--muted-text": "#6C685F", "--ink": "#26251F", "--ink-strong": "#121210", "--primary": "#22313B",
    "--primary-alt": "#3D5260", "--accent": "#A8743F", "--brand-extra": "#6B8A8E", "--warn": "#C27C12",
    "--sans": '"Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif',
    "--header": '""', "--stamp": '""', "--rec-label": '"Recommended"', "--todo-label": '"To supply"',
    "--claim-label": '"To be confirmed"',
}


# ---------- HTML tree: html.parser based, serialises back to the exact source where nothing changed ----------

VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())


class Node:
    def __init__(self, tag, attrs=None, raw="", raw_end=""):
        self.tag = tag                      # "#text", "#raw" (comment, doctype), "#root" or an element name
        self.attrs = [[k, v] for k, v in (attrs or [])]
        self.children = []
        self.parent = None
        self.raw = raw                      # text: the source; element: the start tag as written
        self.raw_end = raw_end              # element: the end tag as written ("" when implied or void)
        self.dirty = not raw                # attributes changed (or generated): rebuild the start tag
        self.start = self.end = 0           # source offsets (parsed nodes only)
        self.filled = False                 # set by deck.py new once a slot has its content

    @property
    def is_el(self):
        return not self.tag.startswith("#")

    def get(self, name, default=None):
        for k, v in self.attrs:
            if k == name:
                return "" if v is None else v
        return default

    def set(self, name, value):
        self.dirty = True
        if value is None:
            self.attrs = [a for a in self.attrs if a[0] != name]
            return
        for a in self.attrs:
            if a[0] == name:
                a[1] = value
                return
        self.attrs.append([name, value])

    def classes(self):
        return (self.get("class") or "").split()

    def has_class(self, c):
        return c in self.classes()

    def set_classes(self, classes):
        seen = []
        for c in classes:
            if c and c not in seen:
                seen.append(c)
        self.set("class", " ".join(seen) or None)

    def iter(self):
        for c in self.children:
            if c.is_el:
                yield c
                yield from c.iter()

    def find_all(self, pred):
        return [n for n in self.iter() if pred(n)]

    def find(self, pred):
        return next((n for n in self.iter() if pred(n)), None)

    def ancestors(self):
        p = self.parent
        while p is not None:
            yield p
            p = p.parent

    def append(self, child):
        child.parent = self
        self.children.append(child)

    def insert_after(self, ref, child, gap=None):
        i = self.children.index(ref) + 1
        if gap:
            t = Node("#text", raw=gap)
            t.parent = self
            self.children.insert(i, t)
            i += 1
        child.parent = self
        self.children.insert(i, child)

    def remove(self):
        if self.parent is None:
            return
        sib = self.parent.children
        i = sib.index(self)
        if i > 0 and sib[i - 1].tag == "#text" and not sib[i - 1].raw.strip():
            del sib[i - 1]
            i -= 1
        del sib[i]
        self.parent = None

    def replace_with(self, other):
        sib = self.parent.children
        sib[sib.index(self)] = other
        other.parent, self.parent = self.parent, None

    def text(self):
        out = []
        for c in self.children:
            if c.tag == "#text":
                out.append(html.unescape(c.raw))
            elif c.is_el and c.tag not in ("script", "style", "template"):
                out.append(c.text())
                if c.tag in ("br", "p", "li", "div", "td", "th", "dt", "dd", "h1", "h2", "h3", "h4", "tr"):
                    out.append(" ")
        return "".join(out)

    def set_text(self, s, keep=()):
        """Replace the content with text; element children whose tag is in keep (e.g. a <small> unit) stay."""
        t = Node("#text", raw=html.escape(s, quote=False))
        kept = [c for c in self.children if c.is_el and c.tag in keep]
        self.children = []
        for c in [t] + kept:
            self.append(c)

    def set_inner(self, nodes):
        self.children = []
        for n in nodes:
            self.append(n)

    def start_tag(self):
        if not self.dirty:
            return self.raw
        parts = [self.tag]
        for k, v in self.attrs:
            parts.append(k if v is None else f'{k}="{html.escape(v, quote=True)}"')
        return "<" + " ".join(parts) + ">"

    def html(self):
        if self.tag in ("#text", "#raw"):
            return self.raw
        inner = "".join(c.html() for c in self.children)
        if self.tag == "#root":
            return inner
        if self.tag in VOID:
            return self.start_tag()
        if self.raw_end:
            end = self.raw_end
        elif not self.raw:                      # generated here
            end = f"</{self.tag}>"
        elif self.raw.endswith("/>"):           # written self-closing
            end = f"</{self.tag}>" if self.dirty or self.children else ""
        else:                                   # end tag implied in the source: keep it implied
            end = ""
        return self.start_tag() + inner + end

    def clone(self):
        c = Node(self.tag, self.attrs, self.raw, self.raw_end)
        c.dirty = self.dirty
        for ch in self.children:
            c.append(ch.clone())
        return c


class TreeBuilder(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", src)]
        self.root = Node("#root", raw="#root")
        self.root.end = len(src)
        self.stack = [self.root]
        self.last = 0

    def pos(self):
        line, col_ = self.getpos()
        return self.line_starts[line - 1] + col_

    def add(self, node):
        self.stack[-1].append(node)

    def flush(self, upto):
        if upto > self.last:
            t = Node("#text", raw=self.src[self.last:upto])
            t.start, t.end = self.last, upto
            self.add(t)
        self.last = max(self.last, upto)

    def handle_starttag(self, tag, attrs):
        p = self.pos()
        self.flush(p)
        raw = self.get_starttag_text()
        n = Node(tag, attrs, raw)
        n.start, n.end = p, p + len(raw)
        self.add(n)
        self.last = p + len(raw)
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        p = self.pos()
        self.flush(p)
        raw = self.get_starttag_text()
        n = Node(tag, attrs, raw)
        n.start, n.end = p, p + len(raw)
        self.add(n)
        self.last = p + len(raw)

    def handle_endtag(self, tag):
        p = self.pos()
        end = self.src.find(">", p) + 1 or len(self.src)
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.flush(p)
                for open_node in self.stack[i + 1:]:
                    open_node.end = p           # closed implicitly
                n = self.stack[i]
                n.raw_end, n.end = self.src[p:end], end
                del self.stack[i:]
                self.last = end
                return
        self.flush(p)                           # a stray end tag: keep it as written
        self.add(Node("#raw", raw=self.src[p:end]))
        self.last = end

    def _raw(self, end_marker):
        p = self.pos()
        self.flush(p)
        end = self.src.find(end_marker, p)
        end = len(self.src) if end < 0 else end + len(end_marker)
        self.add(Node("#raw", raw=self.src[p:end]))
        self.last = end

    def handle_comment(self, data):
        self._raw("-->" if self.src.startswith("<!--", self.pos()) else ">")

    def handle_decl(self, decl):
        self._raw(">")

    def handle_pi(self, data):
        self._raw(">")

    def unknown_decl(self, data):
        self._raw("]]>" if data.startswith("CDATA[") else ">")

    def finish(self):
        self.feed(self.src)
        self.close()
        self.flush(len(self.src))
        for open_node in self.stack[1:]:
            open_node.end = len(self.src)
        return self.root


def parse(src):
    return TreeBuilder(src).finish() if src else Node("#root", raw="#root")


def fragment(markup):
    kids = list(parse(markup).children)
    for k in kids:
        k.parent = None
    return kids


def element(markup):
    return next(k for k in fragment(markup) if k.is_el)


def slides_of(root):
    return [n for n in root.iter() if n.tag == "section" and n.has_class("slide") and not any(
        a.tag == "section" and a.has_class("slide") for a in n.ancestors())]


def slot_nodes(node):
    own = [node] if node.is_el and node.get("data-slot") is not None else []
    return own + [n for n in node.iter() if n.get("data-slot") is not None]


def leaf_slots(node):
    return [n for n in slot_nodes(node) if not any(d.get("data-slot") is not None for d in n.iter())]


def is_lbl(s):
    return (s.get("data-slot") or "").startswith("lbl-")


def content_slots(node):
    return [s for s in leaf_slots(node) if not is_lbl(s)]


def esc(s):
    return html.escape(str(s), quote=True)


def visible_len(s):
    return len(" ".join(s.split()))

# ---------- numbered units ----------

def number_el(u):
    return [n for n in [u] + list(u.iter()) if n.get("data-slot") is None and any(c in NUM_CLASSES for c in n.classes())
            and re.fullmatch(r"\s*\d{1,2}\s*", n.text())]


def renumber(unit, old, new, names=True):
    """Advance a cloned unit's numbers: slot names (c1-title -> c4-title) when they are numbered, and number
    elements such as <span class="n">01</span>."""
    for s in slot_nodes(unit) if names else []:
        s.set("data-slot", re.sub(rf"(?<!\d){old}(?!\d)", str(new), s.get("data-slot"), count=1))
    for n in number_el(unit):
        t = n.text().strip()
        if int(t) == old:
            n.set_text(f"{new:0{len(t)}d}")


def set_count_class(sec, prefix, n):
    """The variant class that encodes a count (cards n3, gallery g2) follows the number of units."""
    sec.set_classes([c for c in sec.classes() if not re.fullmatch(rf"{prefix}\d", c)] + [f"{prefix}{n}"])

# ---------- tokens (brief/deck-style.json -> <style id="tokens">) ----------

TOKENS_RE = re.compile(r"(<style\b[^>]*\bid\s*=\s*[\"']?tokens[\"']?[^>]*>)(.*?)(</style\s*>)", re.S | re.I)


def css_string(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("<", "\\3C ")
    return f'"{s}"'


def parse_vars(css):
    """--name: value pairs of a :root{} block, quotes respected."""
    out, buf, quote = {}, "", None
    body = css[css.find("{") + 1:css.rfind("}")] if "{" in css else css
    for ch in body + ";":
        if quote:
            buf += ch
            if ch == quote and not buf[:-1].endswith("\\"):
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ";":
            k, _, v = buf.partition(":")
            if k.strip().startswith("--") and v.strip():
                out[k.strip()] = v.strip()
            buf = ""
        else:
            buf += ch
    return out


def template_tokens(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            m = TOKENS_RE.search(f.read())
        return parse_vars(m.group(2)) if m else {}
    except OSError:
        return {}


def write_tokens(text, css):
    m = TOKENS_RE.search(text)
    return None if not m else text[:m.start(2)] + css + text[m.end(2):]


def logo_path(project) -> str | None:
    """deck-style "logo" resolved relative to brief/ (as common.logo_hashes does); None when unset or missing."""
    logo = project.style.get("logo")
    path = os.path.normpath(project.path("brief", logo)) if isinstance(logo, str) and logo else None
    return path if path and os.path.isfile(path) else None


def build_tokens(project, defaults) -> str:
    style = project.style
    chrome = project.labels.get("chrome") or {}
    v = dict(defaults) if defaults else dict(NEUTRAL_TOKENS)
    colors = style.get("colors") or {}
    for key, var in COLOR_VARS:
        val = str(colors.get(key) or "").strip()
        if not val:
            continue
        if re.fullmatch(r"#[0-9A-Fa-f]{3,8}|(?:rgb|rgba|hsl|hsla)\([\d\s.,%/]+\)", val):
            v[var] = val
        else:
            print(f"warning: deck-style colors.{key} = {val!r} is not a colour; template default kept")
    if colors.get("primary") and not colors.get("primary_alt") and v.get("--primary") == str(colors["primary"]).strip():
        v["--primary-alt"] = v["--primary"]
    sans = (style.get("fonts") or {}).get("sans")
    if sans and not re.search(r"[;{}<>]", sans):
        v["--sans"] = sans
    v["--header"] = css_string(style["header"]) if style.get("header") else '""'
    v["--stamp"] = css_string(style["stamp"]) if style.get("stamp") else css_string(project.labels.get("stamp", ""))
    for var, key in (("--rec-label", "recommended"), ("--todo-label", "to_supply"), ("--claim-label", "to_confirm")):
        if chrome.get(key):
            v[var] = css_string(chrome[key])
    if style.get("logo") and not logo_path(project):
        print(f"warning: deck-style logo {style['logo']} not found under brief/")
    acc, ink = hex_rgb(v.get("--accent", "")), hex_rgb(v.get("--ink-strong", ""))
    if acc and ink:     # labels drawn on the accent (recommended tag): white, or the darkest ink if white fails
        v["--on-accent"] = "#FFFFFF" if contrast((255, 255, 255), acc) >= LEGIBLE_RATIO or \
            contrast((255, 255, 255), acc) >= contrast(ink, acc) else v["--ink-strong"]
    return "\n:root{\n" + "".join(f"  {k}:{val};\n" for k, val in v.items()) + "}\n"


# ---------- page references ----------

def page_map(root):
    slides = slides_of(root)
    by_id, covers = {}, {}
    for i, s in enumerate(slides, 1):
        if s.get("data-id"):
            by_id.setdefault(s.get("data-id"), i)
        for d in (s.get("data-covers") or "").split():
            covers.setdefault(d, []).append(i)
    return slides, by_id, covers


def ref_text(formats: dict, nums: list, style) -> str:
    """Reference text from labels["ref_formats"] (page, pages, sep, num)."""
    if not nums:
        return ""
    if style == "num":
        return formats["sep"].join(formats["num"].format(n) for n in nums)
    if len(nums) == 1:
        return formats["page"].format(nums[0])
    return formats["pages"].format(formats["sep"].join(str(n) for n in nums))


def ref_pages(root, review=None) -> dict:
    """Pages per design point id (ascending, unique, first 3). With a review record the pages that its
    pass1.coverage entries cite win; every other id falls back to the data-covers notes."""
    _, by_id, covers = page_map(root)
    out = {d: sorted(set(nums))[:3] for d, nums in covers.items()}
    cited = {}
    coverage = ((review or {}).get("pass1") or {}).get("coverage")
    for item in coverage if isinstance(coverage, list) else []:
        if not isinstance(item, dict):
            continue
        n = by_id.get(item.get("page_id"))
        if n and isinstance(item.get("point"), str):
            cited.setdefault(item["point"], set()).add(n)
    for d, nums in cited.items():
        out[d] = sorted(nums)[:3]
    return out


def compute_refs(root, project, review=None) -> list:
    """(node, target, expected text) for every element with a data-ref attribute, in document order."""
    _, by_id, _ = page_map(root)
    formats = project.labels["ref_formats"]
    points = {p.get("id") for p in (project.brief.get("design_points") or []) if isinstance(p, dict)}
    pages = ref_pages(root, review)
    out = []
    for n in root.iter():
        target = n.get("data-ref")
        if target is None:
            continue
        target = target.strip()
        if target in points:
            nums = pages.get(target, [])
        elif target in by_id:
            nums = [by_id[target]]
        else:
            nums = []
        out.append((n, target, ref_text(formats, nums, n.get("data-ref-style"))))
    return out


def refresh_refs(root, project, review=None) -> int:
    """Rewrite the text of every data-ref element to the computed text; returns the number of texts changed."""
    changed = 0
    for n, _, expected in compute_refs(root, project, review):
        if " ".join(n.text().split()) != expected:
            n.set_text(expected)
            changed += 1
    return changed


# ---------- text extraction (text, review record, check, export) ----------

_SKIP = ("script", "style", "template")
_BLOCK = ("br", "p", "li", "div", "td", "th", "dt", "dd", "h1", "h2", "h3", "h4", "tr")


def _ref_marker(node) -> str:
    return " [ref:" + (node.get("data-ref") or "").strip() + "] "


def _collect(node, out):
    for c in node.children:
        if c.tag == "#text":
            out.append(html.unescape(c.raw))
        elif c.is_el and c.tag not in _SKIP:
            if c.get("data-ref") is not None:
                out.append(_ref_marker(c))
            elif c.tag == "img":
                out.append(" [image] ")
            else:
                _collect(c, out)
                if c.tag in _BLOCK:
                    out.append(" ")


def slot_text(node) -> str:
    """Text of a slot: a data-ref element becomes [ref:<target>], an img [image]; script, style and template are
    skipped; whitespace is collapsed and entities are unescaped."""
    if node.get("data-ref") is not None:
        return _ref_marker(node).strip()
    if node.tag == "img":
        return "[image]"
    out = []
    _collect(node, out)
    return " ".join("".join(out).split())


def page_lines(slide) -> list:
    """The page's content in document order: each leaf slot's text, [image] for an img outside the leaf slots and
    [ref:<target>] for a data-ref element outside them. Empty lines are dropped."""
    lines = []

    def walk(n):
        for c in n.children:
            if not c.is_el or c.tag in _SKIP:
                continue
            if c.get("data-slot") is not None and not any(d.get("data-slot") is not None for d in c.iter()):
                lines.append(slot_text(c))
            elif c.get("data-ref") is not None:
                lines.append(slot_text(c))
            elif c.tag == "img":
                lines.append("[image]")
            else:
                walk(c)
    walk(slide)
    return [x for x in lines if x]


def page_text(slide) -> str:
    return "\n".join(page_lines(slide))


def visible_text(slide) -> str:
    """Client-visible text of a slide: text nodes outside script, style and template with data-ref subtrees
    skipped (joined as Node.text does), then every alt and title value."""
    out, extra = [], []

    def walk(n):
        for c in n.children:
            if c.tag == "#text":
                out.append(html.unescape(c.raw))
            elif c.is_el and c.tag not in _SKIP and c.get("data-ref") is None:
                for a in ("alt", "title"):
                    v = c.get(a)
                    if v:
                        extra.append(html.unescape(v))
                walk(c)
                if c.tag in _BLOCK:
                    out.append(" ")
    walk(slide)
    for a in ("alt", "title"):
        if slide.get(a):
            extra.append(html.unescape(slide.get(a)))
    return "\n".join(["".join(out)] + extra)


# ---------- deck I/O ----------

def deck_path(project) -> str:
    return project.path("pack", "proposal.html")


def read_deck(project):
    try:
        with open(deck_path(project), encoding="utf-8-sig") as f:
            return f.read()
    except OSError:
        return None


def write_deck(project, text) -> None:
    path = deck_path(project)
    tmp = os.path.join(os.path.dirname(path), ".proposal.html.tmp")
    os.makedirs(os.path.dirname(path), exist_ok=True)
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


# ---------- template catalogue and emit ----------

class DeckError(Exception):
    """A usage error without a code: the command prints "error: <message>" and returns 2."""


class Example(NamedTuple):
    layout: str            # classes[1] of the section
    variant: str           # ".".join(classes[2:]) or ""
    roles: tuple           # data-roles split
    node: Node


class Template(NamedTuple):
    prefix: str            # source before the first example, trailing comments stripped, plus a blank line
    examples: list
    suffix: str            # source after the last example


def load_template(path) -> Template:
    try:
        with open(path, encoding="utf-8-sig") as f:
            src = f.read()
    except OSError:
        raise DeckError(f"template not found: {path}")
    root = parse(src)
    slides = slides_of(root)
    if not slides:
        raise DeckError(f'the template has no <section class="slide ...">: {path}')
    examples = []
    for s in slides:
        cls, roles = s.classes(), (s.get("data-roles") or "").split()
        if len(cls) < 2 or not roles:
            raise DeckError(f"template example {s.get('data-id') or '?'} has no layout class or data-roles")
        examples.append(Example(cls[1], ".".join(cls[2:]), tuple(roles), s))
    prefix = src[:slides[0].start].rstrip()
    while prefix.endswith("-->") and "<!--" in prefix:      # the first example's doc comment
        prefix = prefix[:prefix.rfind("<!--")].rstrip()
    return Template(prefix + "\n\n", examples, src[slides[-1].end:])


def find_example(tpl, spec):
    layout, _, variant = spec.partition(":")
    cands = [e for e in tpl.examples if e.layout == layout]
    if not cands:
        return None
    if ":" in spec:
        return next((e for e in cands if e.variant == variant), None)
    return next((e for e in cands if e.variant == ""), cands[0])


def _scaled(value, factor):
    v = str(value).strip()
    return str(round(int(v) * factor)) if v.isdigit() else None


def _repeat_units(node):
    """(group, units) of the first data-repeat group in document order, else (None, [])."""
    first = node.find(lambda n: n.get("data-repeat") is not None)
    if first is None:
        return None, []
    group = first.get("data-repeat")
    return group, [n for n in node.iter() if n.get("data-repeat") == group]


def catalogue_lines(tpl, budget_factor, lang="") -> list:
    lines = [f"budget_factor {budget_factor:g} (lang {lang})"]
    for ex in tpl.examples:
        group, units = _repeat_units(ex.node)
        skip = {id(d) for u in units[1:] for d in [u] + list(u.iter())}
        slots = []
        for s in leaf_slots(ex.node):
            if id(s) in skip:
                continue
            m = _scaled(s.get("data-max"), budget_factor) if s.get("data-max") else None
            slots.append(f"{s.get('data-slot')}:{m if m is not None else '-'}")
        kinds = list(dict.fromkeys(i.get("data-img") for i in ex.node.iter()
                                   if i.tag == "img" and i.get("data-img")))
        name = ex.layout + (":" + ex.variant if ex.variant else "")
        rep = f"{group}x{len(units)}" if group else "-"
        lines.append(f"{name}  roles={','.join(ex.roles)}  repeat={rep}  images={','.join(kinds) or '-'}  "
                     f"slots={','.join(slots) or '-'}")
    return lines


def _concept_letter(node):
    for n in [node] + list(node.ancestors()):
        if n.is_el and n.get("data-concept"):
            return n.get("data-concept")
    return ""


def _dotted(labels, key):
    v = labels
    for part in key.split("."):
        if not isinstance(v, dict) or part not in v:
            return None
        v = v[part]
    return v if isinstance(v, str) else None


def _apply_count(sec, ex, count):
    group, units = _repeat_units(sec)
    if not group:
        raise DeckError(f"layout '{ex.layout}' has no repeat group; --count does not apply")
    proto = units[0].clone()
    for u in units[count:]:
        u.remove()
    units = units[:count]
    parent = units[-1].parent
    prev = parent.children[parent.children.index(units[-1]) - 1]
    gap = prev.raw if prev.tag == "#text" and not prev.raw.strip() else "\n"
    last = units[-1]
    for k in range(len(units) + 1, count + 1):
        c = proto.clone()
        renumber(c, 1, k)
        parent.insert_after(last, c, gap)
        units.append(c)
        last = c
    for k, u in enumerate(units, 1):
        if u.get("data-concept") is not None:
            u.set("data-concept", chr(64 + k))
        for lt in [u] + list(u.iter()):
            if lt.has_class("letter") and not any(c.is_el for c in lt.children):
                lt.set_text(chr(64 + k))
    cls = next((c for c in sec.classes() if re.fullmatch(r"[a-z]\d+", c)), None)
    if cls:
        sibs = [x for x in (ex.node.parent.children if ex.node.parent else []) if x.is_el
                and x.tag == "section" and x.has_class("slide") and len(x.classes()) > 1
                and x.classes()[1] == ex.layout]
        if any(f"{cls[0]}{count}" in x.classes() for x in sibs):
            set_count_class(sec, cls[0], count)
        else:
            print(f"note: no {ex.layout} variant for {count} units; check the layout in the previews",
                  file=sys.stderr)


def emit(ex, project, count=None) -> str:
    sec = ex.node.clone()
    sec.set("data-role", ex.roles[0])
    sec.set("data-roles", None)
    sec.set("data-id", "")
    sec.set("data-covers", "")
    factor = project.labels.get("budget_factor", 1)
    for n in sec.iter():
        if n.get("data-max") is not None:
            m = _scaled(n.get("data-max"), factor)
            if m is not None:
                n.set("data-max", m)
        if n.tag == "img":
            n.set("src", "")
    if count is not None:
        _apply_count(sec, ex, count)
    for n in [sec] + list(sec.iter()):
        key = n.get("data-auto")
        if key:
            value = _dotted(project.labels, key)
            if value is not None:
                n.set_text(value.replace("{}", _concept_letter(n)))
    return sec.html() + "\n"


def _report(e) -> int:
    print(f"error: {e}", file=sys.stderr)
    return 2


def cmd_layouts(project, emit_spec, count) -> int:
    try:
        tpl = load_template(DEFAULT_TEMPLATE)
        if emit_spec is None:
            print("\n".join(catalogue_lines(tpl, project.labels.get("budget_factor", 1), project.lang)))
            return 0
        ex = find_example(tpl, emit_spec)
        if ex is None:
            raise DeckError(f"unknown layout '{emit_spec}'; run deck.py layouts")
        sys.stdout.write(emit(ex, project, count))
        return 0
    except DeckError as e:
        return _report(e)


# ---------- new / style ----------

def _backup(project) -> str:
    folder = project.path("work", "backup")
    os.makedirs(folder, exist_ok=True)
    stamp, k = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"), 1
    dest = os.path.join(folder, f"proposal.{stamp}.html")
    while os.path.exists(dest):
        k += 1
        dest = os.path.join(folder, f"proposal.{stamp}-{k}.html")
    shutil.copy2(deck_path(project), dest)
    return dest


def cmd_new(project, template, force) -> int:
    try:
        path = template or DEFAULT_TEMPLATE
        exists = os.path.isfile(deck_path(project))
        if exists and not force:
            print("error: pack/proposal.html exists; use --force (the old deck goes to work/backup/)",
                  file=sys.stderr)
            return 1
        tpl = load_template(path)
        cover = next((e for e in tpl.examples if "cover" in e.roles), None)
        if cover is None:
            raise DeckError("the template has no cover example")
        doc = parse(tpl.prefix + emit(cover, project) + "\n\n" + tpl.suffix)
        h = doc.find(lambda n: n.tag == "html")
        if h is not None:
            h.set("lang", project.lang)
        title = doc.find(lambda n: n.tag == "title")
        if title is not None:
            title.set_text(project.style.get("header") or project.style.get("name") or "Proposal")
        logo = logo_path(project)
        rel = None
        if logo and common.inside(project.root, logo):
            rel = os.path.relpath(logo, project.path("pack")).replace("\\", "/")
        elif logo:
            print("warning: deck-style logo lies outside the project folder; the cover has no logo")
        for tile in doc.find_all(lambda n: n.has_class("logo-tile")):
            img = tile.find(lambda n: n.tag == "img" and n.get("data-img") == "logo")
            if rel and img is not None:
                img.set("src", rel)
            else:
                tile.remove()
        text = write_tokens(doc.html(), build_tokens(project, template_tokens(path)))
        if text is None:
            raise DeckError(f'the template has no <style id="tokens"> block: {path}')
        if exists:
            print(f"backup: {project.rel(_backup(project))}")
        write_deck(project, text)
        print(f"wrote pack/proposal.html: shell with 1 cover slide (lang {project.lang})")
        print("next: deck.py layouts, then paste --emit fragments")
        return 0
    except DeckError as e:
        return _report(e)


def cmd_style(project, template) -> int:
    text = read_deck(project)
    if text is None:
        return _report("no pack/proposal.html; run deck.py new")
    path = template or DEFAULT_TEMPLATE
    if template and not os.path.isfile(path):
        return _report(f"template not found: {path}")
    defaults = template_tokens(path) if os.path.isfile(path) else {}
    if not defaults:
        m = TOKENS_RE.search(text)
        defaults = parse_vars(m.group(2)) if m else {}
    new = write_tokens(text, build_tokens(project, defaults))
    if new is None:
        return _report('pack/proposal.html has no <style id="tokens"> block')
    if new == text:
        print("tokens unchanged")
        return 0
    write_deck(project, new)
    print("rewrote the tokens block of pack/proposal.html from brief/deck-style.json")
    return 0
