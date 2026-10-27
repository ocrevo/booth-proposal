"""Pitch deck: build, check and export the proposal as one self-contained HTML file (16:9, 1920 x 1080 per slide).

The deck is pack/proposal.html, made from the skill's template (assets/deck/template.html), which holds the design
system and one example section per component. Everything client-specific comes from the project folder at run time:
brief/deck-style.json (colours, fonts, running header, draft stamp, logo, language), brief/design-points.md (the
design points D1, D2 ... the deck must answer) and concepts/<L>/ (concept.md, renders, plan, massing).
Run every command from the project folder (or pass --project).

Usage:
  python deck.py new    [--project .] [--lang zh|en] [--lead B] [--template T] [--force]
        -> pack/proposal.html: tokens from deck-style.json and a page skeleton built from what the project holds.
           Facts already in the project (design points, assumptions, claims, ideas considered, geometry, chosen
           renders, and the name, manifesto, idea, moments, messages, palette and note of each concept.md) are
           filled in; project text longer than its slot's budget is left as "TODO: <that text>" to be cut down;
           text that needs writing is "TODO: hint". Budgets (data-max) are the template's, which count CJK
           characters; an English deck gets 1.8 x as many letters. Long tables continue on further slides by their
           estimated height, with column widths that follow the content. A concept accent (or, on dark pages, the
           deck accent) too faint for its page is lightened or darkened on that page only. Never overwrites an
           existing deck without --force; with --force the old one is kept as pack/proposal.YYYYMMDD-HHMM.bak.html.
  python deck.py style  [--project .] [--template T]
        -> rewrites only the <style id="tokens"> block from brief/deck-style.json; keys left out fall back to the
           template's tokens (a neutral studio palette).
  python deck.py check  [--project .]
        -> pack/check.txt, exit 1 on errors. Refreshes the page references first (see below).
           ERRORS: missing image files; TODO text left (also in the running header or stamp); a design point that
           no page covers (data-covers); duplicate or missing data-id; a booth render (concepts/*/renders/*) outside
           figure.render; a slot over its data-max.
           WARNINGS: placeholders (their data-todo); numbers in slide text found in no brief/*.md, concept.md or
           geometry.json (numbers with 2+ digits or with %, 万, 亿, m, m², ㎡; IDs, page numbers, section numbers,
           hex colours and lbl-* labels ignored; m/ft and m²/ft² conversions and W x D areas count as found);
           more than 2 free slides; more than 3 pages in a row without an image (appendix excluded); unknown
           layouts; data-covers IDs that are not design points; deck-style colour pairs with too little contrast.
  python deck.py render [--project .] [--browser PATH] [--jobs 4] [--budget 8000]
        -> refreshes page references and runs check, then with headless Chrome or Edge: pack/proposal.pdf,
           pack/preview/slide-NN.png (1920 x 1080 each), pack/preview/contact.png (4 columns, numbered) and the
           overflow check (?check=1), printed as "slide 9 A-board para overflows by 64 px (~12 字)" and appended
           to pack/check.txt. Browser: --browser, env BROWSER, PATH, then the standard install folders. Without
           one it says so: open pack/proposal.html in Chrome or Edge and print to PDF (margins none, background
           graphics on).
  python deck.py status [--project .]
        -> one paragraph: pages, open TODOs and placeholders, last check, outputs present and up to date.

Contract with the template:
  - <style id="tokens">:root{...}</style> holds the CSS custom properties, the only block deck.py rewrites:
    --paper --surface --tint --line --muted --muted-text --ink --ink-strong --primary --primary-alt --accent
    --brand-extra --warn (deck-style "colors"), --sans ("fonts"), --header and --stamp (CSS strings), --logo
    (url(), relative to pack/) and --on-accent (text on accent tags: white, or --ink-strong when white is too
    faint on the accent). The running header is drawn by the template from --header.
  - Pages are <section class="slide LAYOUT [variants]" data-id=".." [data-covers="D1 D4"] [data-concept="A"]
    [style="--accent:#hex"]>, layouts: cover agenda divider statement cards facts overview board image stage plan
    detail compare flow gallery table free. new clones the template's example of a layout for each page;
    repeated units inside it (cards, columns, steps, rows, zones, swatches) are cloned or removed to fit, with
    numbered slot names (c1-title, z3) and concept-letter slot names (A-name) renumbered.
  - Text slots: data-slot="name" [data-max="N"]; N counts every character after collapsing whitespace (a CJK
    character or a Latin letter is 1). Slot "title" is the page title; ".head .no" (or a slot named no/num/sec)
    takes the section number, or the concept letter on a concept's own pages. Slots named lbl-* are fixed labels
    written in Chinese in the template: kept for zh, translated from LBL_EN for en (unknown ones are reported).
  - Booth renders sit in <figure class="render"> (the template stamps --stamp on them), other images in
    <figure class="pic">; new switches the class to match the image it puts in. A missing image becomes
    <div class="placeholder" data-todo="..."> in place of the figure.

Page references (decided here, not in the template): an element with data-ref="D3" (a design point) or
data-ref="A-board" (a page's data-id) gets its text from deck.py: "见第 9、12 页" / "see pp. 9, 12" for a design
point (the first three pages whose data-covers name it), "见第 9 页" / "see p. 9" for a page id; with
data-ref-style="num" the bare number "09" (agenda). The language follows <html lang>. new fills them; check and
render refresh them, rewriting the deck only when a number changed. An unresolvable reference reads TODO, so
check reports it. Page numbers count every section.slide from 1, like the template's CSS counter.

Which pages answer which design-point type (data-covers is set from this table; move an ID by hand when a point is
answered elsewhere):
  space       -> project facts, zones & flow            theme       -> insight & theme, every concept board
  brand       -> every concept board, details & materials
  content     -> what the booth says, every concept's experience page
  product     -> screens & products, zones & flow       screen      -> screens & products
  interactive -> interaction                            hospitality -> hospitality & branded items, zones & flow
  giveaway    -> hospitality & branded items            graphic     -> graphic design
  other       -> further responses
The brief-reading table and the appendix response table list every point but cover none, so the coverage check
means something.

Page order made by new: cover (bleed with the recommended concept's render, split without one), agenda, project
facts (with our own massing model, never a tender or venue image), brief reading (table, continued as needed),
insight & theme, what the booth says, concept overview; per concept (folders under concepts/, sorted) a board
(chosen render), a front view (stage) and an experience page (detail: four moments, what it says, palette,
director's note); comparison; for the recommended concept (--lead, else the first) zones & flow (plan) and
details & materials (facts); then by design-point type: screens & products, interaction (flow), hospitality &
branded items, graphic design (gallery of placeholders), further responses; appendix divider, design-point
response table, assumptions (the A-rows of brief/requirement-card.md), claims for sign-off (flagged C-rows of
brief/content.md), geometry & massing (plan and massing per concept), ideas considered (first table of
brief/ideas.md). Appendix pages carry data-part="appendix".

concept.md, as the skill writes it: "chosen: renders/hero-vN.png – reason", optional "front: renders/front-vN.png",
a title "# A · 名称 Second-language name" (split into name and second name, the deck language first), the
manifesto as the first bold or quoted line under the title, and sections (any heading level 2-4, in Chinese or
English) for the idea (想法 / The idea), the experience (体验 / The experience: four bullets, 10 m, 3 m, inside,
photo moment), what it says (说什么 / What it says: headline and key messages), the atmosphere (氛围 /
Atmosphere: materials, colour with #HEX values and names, light, signature detail, supporting system,
intensity) and the creative director's note (创意总监点评 / Creative director's note). Explicit lines "name:",
"name2:", "manifesto:", "accent: #hex", "palette: #hex #hex ..." take precedence; the accent falls back to
geometry.json "accent". Board image: the chosen render, else the first renders/hero-*.png (with a note). Front
view (stage page): the "front:" render, else the newest renders/front-*.png, else a placeholder.

Standard library only; render's contact sheet needs Pillow.
"""
import argparse
import datetime
import glob
import html
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import unquote

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEMPLATE = os.path.join(SKILL_DIR, "assets", "deck", "template.html")

LAYOUTS = ("cover", "agenda", "divider", "statement", "cards", "facts", "overview", "board", "image", "stage",
           "plan", "detail", "compare", "flow", "gallery", "table", "free")
VARIANTS = {"cover": ("bleed", "split"), "board": ("framed", "bleed", "mirror"), "cards": ("n2", "n3", "n4", "n6"),
            "gallery": ("g1", "g2", "g3", "g4")}
TYPES = ("space", "theme", "brand", "content", "product", "screen", "interactive", "hospitality", "giveaway",
         "graphic", "other")
TYPE_PAGES = {   # design-point type -> page kinds that answer it ("board" and "detail" exist once per concept)
    "space": ("facts", "zones"),
    "theme": ("insight", "board"),
    "brand": ("board", "materials"),
    "content": ("message", "detail"),
    "product": ("screens", "zones"),
    "screen": ("screens",),
    "interactive": ("interaction",),
    "hospitality": ("hospitality", "zones"),
    "giveaway": ("hospitality",),
    "graphic": ("graphic",),
    "other": ("responses",),
}
COLOR_VARS = (("paper", "--paper"), ("surface", "--surface"), ("tint", "--tint"), ("line", "--line"),
              ("muted", "--muted"), ("muted_text", "--muted-text"), ("ink", "--ink"), ("ink_strong", "--ink-strong"),
              ("primary", "--primary"), ("primary_alt", "--primary-alt"), ("accent", "--accent"),
              ("brand_extra", "--brand-extra"), ("warn", "--warn"))
NEUTRAL_TOKENS = {   # used only when the template has no tokens block
    "--paper": "#FAFAF7", "--surface": "#F1F0EB", "--tint": "#E6E4DD", "--line": "#D6D3CA", "--muted": "#A19D93",
    "--muted-text": "#6C685F", "--ink": "#26251F", "--ink-strong": "#121210", "--primary": "#22313B",
    "--primary-alt": "#3D5260", "--accent": "#A8743F", "--brand-extra": "#6B8A8E", "--warn": "#C27C12",
    "--sans": '"Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif',
    "--header": '""', "--stamp": '"Draft – concept visualization, not for construction"',
}
TABLE_HEIGHT = 600      # px of table rows per slide (content area minus the header row and the foot note)
TABLE_ROWS = 12         # at most this many rows per slide (a table example's data-rows overrides it)
BRIEF_WIDTHS = ["7%", "8%", None, "15%", "16%"]
ZONES_MAX = 8

LABELS = {
    "zh": {
        "groups": {1: "项目理解", 2: "创意策略", 3: "设计方案", 4: "推荐方案深化", 5: "附录"},
        "agenda": "目录", "facts": "项目概况", "brief": "需求解读",
        "insight": "洞察与主题", "insight_label": "洞察", "message": "展台要说什么", "overview": "方案总览",
        "compare": "方案对比", "front": "正面视角", "detail": "{} · 体验与表达", "concept": "方案 {}",
        "zones": "分区与动线", "materials": "细节与材料", "screens": "屏幕与产品展示", "interaction": "互动体验",
        "hospitality": "接待与品牌物料", "graphic": "平面设计", "responses": "更多设计回应", "appendix": "附录",
        "response": "设计要点回应", "assumptions": "假设", "claims": "待客户确认的表述",
        "geometry": "尺寸与体量核查", "ideas": "备选创意",
        "appendix_sub": "设计要点回应 · 假设 · 待确认表述 · 尺寸与体量 · 备选创意",
        "cont": "（续）", "see": "见第 {} 页", "sep": "、",
        "col_id": "编号", "col_type": "类型", "col_point": "设计要点", "col_source": "出处", "col_page": "页码",
        "col_where": "回应页面",
        "col_concept": "方案 {}",
        "types": {"space": "空间", "theme": "主题", "brand": "品牌", "content": "内容", "product": "产品",
                  "screen": "屏幕", "interactive": "互动", "hospitality": "接待", "giveaway": "物料",
                  "graphic": "平面", "other": "其他"},
        "key_msg": "关键信息 {:02d}",
        "ph_hero": "方案 {} 主视角效果图", "ph_front": "方案 {} 正面效果图", "ph_plan": "方案 {} 平面图",
        "ph_massing": "方案 {} 体量图",
        "ph_graphic": "平面设计稿：{}", "ph_image": "图片", "ph_concepts": "concepts/ 下还没有方案",
        "ph_table": "表格内容（{}）",
        "cap_massing": "{} · 体量示意（按几何参数）", "cap_plan": "{} · 平面图",
        "material_keys": ["主材", "色彩", "灯光", "标志细节", "配套系统"],
        "plan_note": "尺寸以几何规格与平面图为准；效果图为概念示意。",
        "foot": {"brief": "出处为标书中的位置；页码为本提案回应该要点的页面。",
                 "response": "每个方案如何回应各设计要点；页码为正文中的对应页面。",
                 "assumptions": "资料未明确之处的假设，客户确认后更新。",
                 "claims": "以上表述用于展台前须经客户确认。",
                 "ideas": "考虑过但未采用的创意及原因。"},
        "sides": {"front": "正面", "back": "背面", "left": "左侧", "right": "右侧"}, "side_sep": "、",
        "extra_card": "补充说明",
    },
    "en": {
        "groups": {1: "The brief", 2: "Strategy", 3: "The concepts", 4: "Recommended concept", 5: "Appendix"},
        "agenda": "Contents", "facts": "Project facts", "brief": "Reading the brief",
        "insight": "Insight and theme", "insight_label": "Insight", "message": "What the booth says",
        "overview": "The concepts", "compare": "Comparison", "front": "Front view",
        "detail": "{} · Experience", "concept": "Concept {}", "zones": "Zones and flow",
        "materials": "Details and materials", "screens": "Screens and products", "interaction": "Interaction",
        "hospitality": "Hospitality and giveaways", "graphic": "Graphic design", "responses": "Further responses",
        "appendix": "Appendix", "response": "Design-point responses", "assumptions": "Assumptions",
        "claims": "Claims for sign-off", "geometry": "Geometry and massing", "ideas": "Ideas considered",
        "appendix_sub": "Responses · assumptions · claims · geometry · ideas considered",
        "cont": " (cont.)", "see": "see p. {}", "see_pl": "see pp. {}", "sep": ", ",
        "col_id": "ID", "col_type": "Type", "col_point": "Design point", "col_source": "Source", "col_page": "Page",
        "col_where": "Answered",
        "col_concept": "Concept {}",
        "types": {t: t for t in TYPES},
        "key_msg": "Key message {:02d}",
        "ph_hero": "concept {} hero render", "ph_front": "concept {} front view", "ph_plan": "concept {} plan",
        "ph_massing": "concept {} massing", "ph_graphic": "graphic design: {}",
        "ph_image": "image", "ph_concepts": "no concepts under concepts/ yet", "ph_table": "table content ({})",
        "cap_massing": "{} · massing (geometry spec)", "cap_plan": "{} · plan",
        "material_keys": ["Materials", "Colour", "Light", "Signature", "System"],
        "plan_note": "Dimensions follow the geometry spec and the plan; renders are concept visualizations.",
        "foot": {"brief": "Source: where the point appears in the brief. Page: where this proposal answers it.",
                 "response": "How each concept meets each design point; the page shows where.",
                 "assumptions": "Assumptions where the brief is silent, to be confirmed by the client.",
                 "claims": "These claims need the client's sign-off before they go on the stand.",
                 "ideas": "Ideas considered and not taken forward, with the reason."},
        "sides": {"front": "front", "back": "back", "left": "left", "right": "right"}, "side_sep": ", ",
        "extra_card": "supporting detail",
    },
}
# fixed labels the template writes in Chinese (slots named lbl-*), translated for English decks
LBL_EN = {"目录": "Contents", "Contents": "", "面积": "Area", "长 × 宽": "W × D", "最高点": "Highest point",
          "远处": "From afar", "走近": "Approaching", "走进": "Inside", "拍照点": "Photo moment",
          "它说什么": "What it says", "氛围": "Atmosphere", "标志细节": "Signature", "配套系统": "System",
          "强度": "Intensity", "创意总监点评": "Creative director's note", "创意": "Idea", "感受": "Feeling",
          "出发点": "Starting point", "适合的客户": "Best for", "主要风险": "Main risk", "编号": "ID",
          "要求": "Requirement", "本方案如何满足": "How it is met", "状态": "Status", "开口": "Open sides",
          "限高": "Height limit", "尺寸": "Size", "远观": "From afar", "被吸引": "drawn in",
          "被邀请": "invited in", "发现与交流": "discover and talk", "带走的画面": "The picture they keep"}
HINTS = {   # TODO hints by slot name (first regex that matches); builders pass page-specific hints
    "zh": [(r"manifesto|^man$", "一句宣言：这个方案给人的感受"), (r"alt$|name2|name-en", "第二语言名称"),
           (r"name", "方案名"), (r"statement|^say", "一句话洞察，关键词可加粗"), (r"^by$", "依据或出处"),
           (r"^m\d+$", "这一刻看到、感受到什么"), (r"headline", "主标题（L1）"), (r"^msg\d+$", "关键信息（L2）"),
           (r"^sw\d+$", "颜色名"), (r"atmos", "材料、色彩与光"), (r"^sig$", "标志细节"), (r"^sys$", "配套系统"),
           (r"^int$", "强度：克制 / 均衡 / 张扬"), (r"note", "创意总监点评：优势与风险，一句"),
           (r"eyebrow", "展会名称 · 展位号"), (r"subtitle", "一句话副标题"), (r"meta", "客户 · 面积 · 日期"),
           (r"idea|para", "创意说明"), (r"view", "视角"), (r"cap", "图注"), (r"lead", "一句导语"),
           (r"-k$|^k$|kicker", "小标题"), (r"-d$", "一句说明"), (r"title", "标题"), (r"body|^p$", "正文")],
    "en": [(r"manifesto|^man$", "one-line manifesto: the feeling"), (r"alt$|name2|name-en", "name in the second language"),
           (r"name", "concept name"), (r"statement|^say", "the insight in one sentence, key phrase in <b>"),
           (r"^by$", "basis or source"), (r"^m\d+$", "what the visitor sees and feels here"),
           (r"headline", "headline (L1)"), (r"^msg\d+$", "key message (L2)"), (r"^sw\d+$", "colour name"),
           (r"atmos", "material, colour and light"), (r"^sig$", "signature detail"), (r"^sys$", "supporting system"),
           (r"^int$", "intensity: restrained / balanced / expressive"),
           (r"note", "creative director's note: strength and risk, one line"), (r"eyebrow", "event · stand number"),
           (r"subtitle", "one-line subtitle"), (r"meta", "client · area · date"), (r"idea|para", "the idea"),
           (r"view", "view"), (r"cap", "caption"), (r"lead", "one lead sentence"), (r"-k$|^k$|kicker", "kicker"),
           (r"-d$", "one line"), (r"title", "title"), (r"body|^p$", "text")],
}
SEC_SLOTS = {"sec", "num", "no", "section", "secno", "sec-no", "section-no", "number"}
HEADER_SLOTS = {"header", "running", "running-header"}
NUM_CLASSES = ("n", "no", "num", "number", "idx")
REF_RE = re.compile(r"^[A-Z]{1,3}\d+[a-z]?$")
EN_BUDGET = 1.8     # data-max in the template counts CJK characters; an English deck gets 1.8 x as many letters
UNIT_RE = re.compile(r"(?<=\d)[ \t]+(?=(?:m²|m2|m³|㎡|mm|cm|m|ft²|ft|in|kg|K|%|°)(?![A-Za-z0-9]))")


def keep_units(s):
    """A number and its unit never break across lines: '4.2 m' -> '4.2\u00a0m' (no-break space)."""
    return UNIT_RE.sub("\u00a0", s)


def hex_rgb(h):
    h = (h or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if not re.fullmatch(r"[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def legible(fg, bg, ratio=3.0):
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


def say(msg=""):
    print(msg, flush=True)


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


def layout_of(sec):
    return next((c for c in sec.classes() if c in LAYOUTS), "")


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


# ---------- project files ----------

class Concept:
    def __init__(self, letter, folder):
        self.letter, self.dir = letter, folder
        self.md = ""
        self.hero = self.front = self.plan = None
        self.massing = []
        self.geometry = {}
        self.name = self.name2 = self.manifesto = self.accent = None
        self.palette, self.swatches, self.moments, self.messages = [], [], [], []
        self.idea = self.headline = self.atmos = self.signature = self.system = self.intensity = self.note = None


class Project:
    def __init__(self, root, template=None, lang=None, lead=None):
        self.root = os.path.abspath(root)
        self.brief = os.path.join(self.root, "brief")
        self.pack = os.path.join(self.root, "pack")
        self.deck = os.path.join(self.pack, "proposal.html")
        self.template = os.path.abspath(template) if template else DEFAULT_TEMPLATE
        self.style = load_style(self)
        self.lang = (lang or str(self.style.get("lang") or "zh")).lower()[:2]
        if self.lang not in LABELS:
            self.lang = "zh"
        self.L = LABELS[self.lang]
        self.points = load_points(self)
        self.concepts = load_concepts(self)
        self.lead = None
        if self.concepts:
            want = (lead or "").upper()
            self.lead = next((c for c in self.concepts if c.letter.upper() == want), None)
            if lead and not self.lead:
                say(f"note: --lead {lead}: no such concept, using {self.concepts[0].letter}")
            self.lead = self.lead or self.concepts[0]

    def colour(self, var):
        """The effective value of a colour token: deck-style.json, else the template's tokens, else neutral."""
        key = next((k for k, v in COLOR_VARS if v == var), None)
        val = str(((self.style.get("colors") or {}).get(key) or "")).strip() if key else ""
        if not hex_rgb(val):
            if not hasattr(self, "_tpl_tokens"):
                self._tpl_tokens = template_tokens(self.template) if os.path.isfile(self.template) else {}
            val = self._tpl_tokens.get(var) or NEUTRAL_TOKENS.get(var, "")
        return val

    def read(self, *rel):
        try:
            with open(os.path.join(self.root, *rel), encoding="utf-8-sig") as f:
                return f.read()
        except OSError:
            return ""

    def rel(self, path):
        """A project file as the deck references it: relative to pack/, forward slashes."""
        return os.path.relpath(path, self.pack).replace(os.sep, "/")


def load_style(proj):
    path = os.path.join(proj.brief, "deck-style.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as e:
        say(f"warning: brief/deck-style.json is not valid JSON ({e}); template defaults used")
        return {}


def md_clean(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return s.replace("**", "").replace("`", "").replace("<br>", " ").strip()


def md_tables(text):
    """Markdown tables as (header, rows), cells cleaned of emphasis, code marks and links."""
    tables, cur = [], []
    for line in text.splitlines() + [""]:
        s = line.strip()
        if s.startswith("|"):
            cells = [md_clean(c.replace("\0", "|")) for c in s.replace("\\|", "\0").strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells if c):
                cur.append(cells)
            continue
        if cur:
            if len(cur) > 1:
                tables.append((cur[0], cur[1:]))
            cur = []
    return tables


def col(header, *keys):
    for i, h in enumerate(header):
        if any(k in h.lower() for k in keys):
            return i
    return None


def load_points(proj):
    text = proj.read("brief", "design-points.md")
    rev = {v: k for k, v in LABELS["zh"]["types"].items()}
    points = []
    for header, rows in md_tables(text):
        i_id, i_type = col(header, "id", "编号"), col(header, "类型", "type")
        i_text, i_src = col(header, "设计要点", "design point", "要点", "point"), col(header, "出处", "source", "来源")
        if i_id is None or i_text is None:
            continue
        for r in rows:
            def cell(i):
                return r[i].strip() if i is not None and i < len(r) else ""
            pid = cell(i_id)
            if not REF_RE.match(pid):
                continue
            t = cell(i_type).lower()
            t = t if t in TYPES else rev.get(t, "other")
            points.append({"id": pid, "type": t, "text": cell(i_text), "source": cell(i_src)})
    return points


def version_key(path):
    m = re.search(r"-v(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else 0


def md_value(md, *keys):
    for k in keys:
        m = re.search(rf"^\s*[-*]?\s*\**{re.escape(k)}\**\s*[:：]\s*(.+?)\s*$", md, re.M | re.I)
        if m:
            return md_clean(m.group(1))
    return None


def md_path(md, folder, key):
    v = md_value(md, key)
    m = re.search(r"[\w./\\-]+\.(?:png|jpe?g|webp)", v or "", re.I)
    if not m:
        return None
    p = m.group(0).replace("\\", "/")
    for base in (folder, os.path.dirname(os.path.dirname(folder))):
        full = os.path.normpath(os.path.join(base, p))
        if os.path.isfile(full):
            return full
    return os.path.normpath(os.path.join(folder, p))


def load_concepts(proj):
    base = os.path.join(proj.root, "concepts")
    out = []
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        folder = os.path.join(base, name)
        if not os.path.isdir(folder) or name.startswith((".", "_")):
            continue
        has = [os.path.exists(os.path.join(folder, f)) for f in ("concept.md", "renders", "geometry.json")]
        if not any(has) or not (has[0] or re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,2}", name)):
            continue
        c = Concept(name, folder)
        c.md = proj.read("concepts", name, "concept.md")
        heroes = sorted(glob.glob(os.path.join(folder, "renders", "hero-*.png")), key=version_key)
        fronts = sorted(glob.glob(os.path.join(folder, "renders", "front-*.png")), key=version_key)
        chosen = md_path(c.md, folder, "chosen")
        c.hero = chosen if chosen and os.path.isfile(chosen) else (heroes[0] if heroes else None)
        if chosen and not os.path.isfile(chosen):
            say(f"note: concepts/{name}/concept.md chooses {os.path.relpath(chosen, proj.root)}, which does not exist")
        elif not chosen and c.hero:
            say(f"note: concepts/{name}/concept.md has no 'chosen:' line; using {os.path.relpath(c.hero, folder)}")
        fr = md_path(c.md, folder, "front")
        c.front = fr if fr and os.path.isfile(fr) else (fronts[-1] if fronts else None)
        c.plan = next((p for p in (os.path.join(folder, "plan.png"), os.path.join(folder, "plan.svg"))
                       if os.path.isfile(p)), None)
        c.massing = [p for p in (os.path.join(folder, "massing-hero.png"), os.path.join(folder, "massing-front.png"))
                     if os.path.isfile(p)]
        try:
            with open(os.path.join(folder, "geometry.json"), encoding="utf-8-sig") as f:
                c.geometry = json.load(f)
        except (OSError, ValueError):
            c.geometry = {}
        heading = re.search(rf"^#{{1,3}}\s*(?:concept|方案)?\s*{re.escape(name)}\s*[·:：.\-–—|]\s*(.+?)\s*$",
                            c.md, re.M | re.I)
        c.name = md_value(c.md, "name", "名称", "方案名") or (md_clean(heading.group(1)) if heading else None)
        c.name2 = md_value(c.md, "name2", "name_en", "second name", "英文名")
        if c.name and not c.name2:          # "之光门 The Halvard Gate": name in the deck language + second name
            first, second = split_name(c.name, proj.lang)
            if second:
                c.name, c.name2 = first, second
        if c.name and c.name2 and has_cjk(c.name) != has_cjk(c.name2) and has_cjk(c.name) != (proj.lang == "zh"):
            c.name, c.name2 = c.name2, c.name    # the name in the deck's language first
        c.manifesto = md_value(c.md, "manifesto", "宣言")
        if not c.manifesto and heading:     # the skill's concept.md: a bold or quoted line under the title
            head = re.split(r"^#{1,4}\s", c.md[heading.end():], maxsplit=1, flags=re.M)[0]
            for ln in head.splitlines():
                m = re.match(r"\s*(?:\*\*|__)([^*_]+?)(?:\*\*|__)\s*$|\s*>\s*(.+?)\s*$", ln)
                if m:
                    c.manifesto = md_clean((m.group(1) or m.group(2)).strip("“”\"'")) or None
                    break
        acc = md_value(c.md, "accent") or str(c.geometry.get("accent") or "")
        c.accent = acc if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", acc or "") else None
        pal = md_value(c.md, "palette", "色彩", "配色", "颜色", "colours", "colors", "colour", "color") or \
            md_section(c.md, "atmosphere", "氛围")
        c.swatches = palette_names(pal)
        c.palette = [h for h, _ in c.swatches]
        c.idea = first_paragraph(md_section(c.md, "the idea", "idea", "想法", "创意"))
        c.moments = [md_clean(re.sub(r"^\s*(?:\*\*[^*]+\*\*|[^:：]{1,16})\s*[:：]\s*", "", b))
                     for b in md_bullets(md_section(c.md, "the experience", "experience", "体验"))][:4]
        says = md_section(c.md, "what it says", "说什么", "它说什么", "内容")
        c.headline = clean_say(md_value(says, "headline", "主标题", "主标题（L1）", "headline (L1)"))
        msgs = re.search(r"(?:key messages?|关键信息)[^\n]*?[:：]\s*(.*?)(?=\n\s*[-*]\s*\*\*|\Z)", says, re.S | re.I)
        c.messages = []
        if msgs:
            items = md_bullets(msgs.group(1)) or re.split(r"\s+·\s+", msgs.group(1).strip())
            c.messages = [clean_say(x) for x in items if x.strip()][:3]
        c.atmos = first_sentence(md_section(c.md, "atmosphere", "氛围"))
        c.signature = md_value(c.md, "signature detail", "signature", "标志细节")
        c.system = md_value(c.md, "supporting system", "配套系统")
        c.intensity = md_value(c.md, "intensity", "强度")
        c.note = first_paragraph(md_section(c.md, "creative director's note", "creative director", "director",
                                            "创意总监点评", "创意总监", "点评"))
        out.append(c)
    return out


def split_name(s, lang):
    """'之光门 The Halvard Gate' -> ('之光门', 'The Halvard Gate') for zh, the other way round for en."""
    s = s.strip()
    m = re.match(r"^(.*[\u3400-\u9fff\uf900-\ufaff][^\sA-Za-z]*)\s*[/|（(]?\s*([A-Za-z][^\u3400-\u9fff]*?)[)）]?\s*$", s)
    if not m or not re.search(r"[A-Za-z]{2}", m.group(2)):
        m = re.match(r"^([A-Za-z][^\u3400-\u9fff]*?)\s*([/|（(]?)\s*([\u3400-\u9fff].*?)[)）]?\s*$", s)
        # Latin first only with a separator or a name of two words or more: "Halvard 之光" is one name
        if not m or not (m.group(2) or len(m.group(1).split()) >= 2):
            return s, None
        m = re.match(r"^(.*?)\s*[/|（(]?\s*([\u3400-\u9fff].*?)[)）]?\s*$", s)
        latin, cjk = m.group(1).strip(" /|·"), m.group(2).strip(" /|·")
    else:
        cjk, latin = m.group(1).strip(" /|·"), m.group(2).strip(" /|·")
    return (latin, cjk) if lang == "en" else (cjk, latin)


def md_section(md, *names):
    """The text under the first heading (## …) whose title starts with one of names, up to the next heading."""
    for n in names:     # the heading is the name, optionally numbered, with "the" or an annotation after it
        m = re.search(rf"^#{{2,4}}\s*(?:\d+[.、]\s*)?(?:the\s+)?{re.escape(n)}(?:\s*|[\s（(:：·\-–—与和及&,，].*)$",
                      md or "", re.M | re.I)
        if m:
            rest = md[m.end():]
            nxt = re.search(r"^#{1,4}\s", rest, re.M)
            return rest[:nxt.start()] if nxt else rest
    return ""


def md_bullets(text):
    return [md_clean(m.group(1)) for m in re.finditer(r"^\s*(?:[-*•]|\d+[.、)])\s+(.+?)\s*$", text or "", re.M)]


def first_paragraph(text):
    for para in re.split(r"\n\s*\n", text or ""):
        p = " ".join(ln.strip() for ln in para.strip().splitlines())
        if p and not re.match(r"^([-*•|>]|\d+[.、])", p):
            return md_clean(p)
    return None


def first_sentence(text):
    for line in md_bullets(text) + [first_paragraph(text) or ""]:
        line = re.sub(r"^[^:：]{1,16}[:：]\s*", "", line)
        if line:
            return re.split(r"(?<=[。.!?！？；;])\s*", line)[0].strip().rstrip("；;，,、")
    return None


def clean_say(s):
    """A headline or message from concept.md without its source notes: '… (C1)', '（edited from C1），放在…'."""
    if not s:
        return None
    s = re.sub(r"\s*[（(][^)）]*\b(?:C|R|A|D)\d+[^)）]*[)）]", "", s)
    s = re.split(r"[；;]|，(?=放在|位于|随|用于|placed|on the)", s)[0]
    return md_clean(s).strip(" ，,。“”\"'") or None


def has_cjk(s):
    return bool(re.search(r"[\u3400-\u9fff]", s or ""))


def palette_names(text):
    """[(#HEX, name)] from a palette line: 'Halvard 绿 #0F4D3A、白 #F7F7F4' or '#0F4D3A Halvard Green, …'."""
    out = []
    for m in re.finditer(r"#[0-9A-Fa-f]{6}\b", text or ""):
        before = re.split(r"[、,，;；:：(（·/]|\s{2,}|\*\*", text[:m.start()])[-1]
        before = re.sub(r"#[0-9A-Fa-f]{3,8}\b", "", before).strip(" -*")
        hexv = m.group(0).upper()
        if hexv not in [h for h, _ in out]:
            out.append((hexv, md_clean(before) if 0 < len(before) <= 16 else ""))
    return out


def num(x):
    return f"{x:.2f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x)


def geometry_facts(c, L):
    """{kind: (label, value, unit)} from the geometry spec: size, area, open sides, highest point or limit."""
    g = (c.geometry if c else None) or {}
    w, d, unit = g.get("width"), g.get("depth"), g.get("unit", "m")
    facts = {}
    if isinstance(w, (int, float)) and isinstance(d, (int, float)):
        facts["size"] = ("长 × 宽" if L is LABELS["zh"] else "W × D", f"{num(w)} × {num(d)}", unit)
        facts["area"] = ("面积" if L is LABELS["zh"] else "Area", num(float(w) * float(d)), f"{unit}²")
    sides = [L["sides"].get(s, s) for s in g.get("open_sides") or []]
    if sides:
        facts["open"] = ("开口" if L is LABELS["zh"] else "Open sides", L["side_sep"].join(sides), "")
    tops = []
    for e in g.get("elements") or g.get("zones") or []:
        try:
            h = max(float(e.get("height", 0) or 0), float((e.get("repeat") or {}).get("height_to", 0) or 0))
            tops.append(float(e.get("z", 0) or 0) + h)
        except (TypeError, ValueError, AttributeError):
            pass
    if tops:
        facts["height"] = ("最高点" if L is LABELS["zh"] else "Highest point", num(max(tops)), unit)
    if isinstance(g.get("max_height"), (int, float)):
        facts["limit"] = ("限高" if L is LABELS["zh"] else "Height limit", num(g["max_height"]), unit)
    return facts


def geometry_zones(c):
    els = ((c.geometry if c else None) or {}).get("elements") or ((c.geometry if c else None) or {}).get("zones") or []
    out = []     # in the spec's order, which is the order draw_plan.py numbers them in
    for e in [e for e in els if isinstance(e, dict) and e.get("label")]:
        if e["label"] not in out:
            out.append(e["label"])
    return out


IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def find_file(proj, name):
    name = name.replace("\\", "/")
    for base in (proj.root, proj.brief, os.path.join(proj.root, "input"), os.path.join(proj.brief, "media")):
        p = os.path.normpath(os.path.join(base, name))
        if os.path.isfile(p):
            return p
    hits = glob.glob(os.path.join(proj.root, "**", glob.escape(os.path.basename(name))), recursive=True)
    return hits[0] if hits else None


def reference_images(proj):
    """Reference images named in the style card. They go to the image model only and must never be shown in the deck;
    check() uses this list to refuse them."""
    found = []
    for m in re.finditer(r"[^\s`'\"()<>|,，、：:]+\.(?:png|jpe?g|webp)", proj.read("brief", "style-cards.md"), re.I):
        p = find_file(proj, m.group(0))
        if p and p not in found:
            found.append(p)
    return found


# The deck shows only the studio's own work for this project (renders, plans, massing, boards made in pack/) and the
# client's logo named in deck-style.json. Reference photos, tender illustrations and anything from input/ or
# brief/media/ may be another company's design: they are never placed in the deck.
OWN_WORK_DIRS = ("concepts", "pack")


def own_work(proj, path):
    """True when an image file is the studio's own work for this project, or the client logo from deck-style.json."""
    p = os.path.normcase(os.path.abspath(path))
    for d in OWN_WORK_DIRS:
        root = os.path.normcase(os.path.abspath(os.path.join(proj.root, d))) + os.sep
        if p.startswith(root):
            return True
    logo = (proj.style or {}).get("logo") if hasattr(proj, "style") else None
    if logo:
        lp = os.path.normcase(os.path.abspath(os.path.join(proj.brief, logo)))
        if p == lp:
            return True
    return False


def table_with(text, first_col_re=None):
    for header, rows in md_tables(text):
        if first_col_re:
            rows = [r for r in rows if r and re.match(first_col_re, r[0].strip())]
        if rows:
            return header, rows
    return None


def claims_table(proj):
    flags = ("superlative", "comparative", "regulated", "dated", "sign-off", "最高级", "比较", "监管", "过时", "需确认", "签")
    for header, rows in md_tables(proj.read("brief", "content.md")):
        i_flag = col(header, "flag", "标记", "标注")
        if i_flag is None or not rows or not re.match(r"^C\d+", rows[0][0].strip()):
            continue
        keep = [r for r in rows if i_flag < len(r) and any(f in r[i_flag].lower() for f in flags)]
        if keep:
            return header, keep
    return None


MATERIAL_KEYS = (   # concept.md keys for the details & materials rows, in the order of LABELS[..]["material_keys"]
    ("materials", "material", "主材", "材料", "材质"), ("colour", "color", "colours", "colors", "palette", "色彩", "颜色", "配色"),
    ("light", "lighting", "灯光", "光"), ("signature detail", "signature", "标志细节"),
    ("supporting system", "配套系统"))
FACT_KEYS = (   # (pattern on the requirement card's bullet key, zh label, en label), in the order shown
    (r"event|展会|活动", "展会", "Event"), (r"venue|场馆|地点", "场馆", "Venue"),
    (r"date|show|展期|日期|时间", "日期", "Dates"), (r"size|尺寸|面积", "展位", "Stand"),
    (r"booth type|展位类型", "类型", "Type"), (r"open side|开口", "开口", "Open sides"),
    (r"max height|height|限高|高度", "限高", "Height"), (r"location|位置", "位置", "Location"),
    (r"client|exhibitor|客户|参展", "客户", "Client"))


def fact_rows(proj, lang):
    """Key facts from the bullet lines of brief/requirement-card.md, labelled in the deck language."""
    found = {}
    for line in proj.read("brief", "requirement-card.md").splitlines():
        m = re.match(r"^\s*[-*]\s*([^:：|]{1,24})[:：]\s*(.+)$", line)
        if not m:
            continue
        k, v = md_clean(m.group(1)).lower(), md_clean(m.group(2))
        v = re.split(r"\s+(?:Source|来源|出处)\s*[:：]", v)[0].strip()
        v = re.sub(r"\s*[（(]\s*(?:§|s\.\s*\d|p\.\s*\d|pp\.|page|slide|第\s*\d)[^()（）]*[)）]", "", v, flags=re.I)
        v = re.split(r"[；;]", v)[0].strip(" ，,。")
        if not v or "<" in v or "…" in v:
            continue
        for i, (pat, zh, en) in enumerate(FACT_KEYS):
            if re.search(pat, k) and i not in found:
                found[i] = (zh if lang == "zh" else en, v)
                break
    # what the geometry spec knows fills the gaps: size and area, open sides, height limit
    g = geometry_facts(proj.lead, LABELS[lang]) if proj.lead else {}
    if 3 not in found and "size" in g:
        size = f"{g['size'][1]} {g['size'][2]}" + (f" · {g['area'][1]} {g['area'][2]}" if "area" in g else "")
        found[3] = (FACT_KEYS[3][1] if lang == "zh" else FACT_KEYS[3][2], size)
    if 5 not in found and "open" in g:
        found[5] = (FACT_KEYS[5][1] if lang == "zh" else FACT_KEYS[5][2], g["open"][1])
    if 6 not in found and "limit" in g:
        found[6] = (FACT_KEYS[6][1] if lang == "zh" else FACT_KEYS[6][2], f"{g['limit'][1]} {g['limit'][2]}")
    order = (0, 1, 2, 3, 5, 6, 8, 4, 7)     # event, venue, dates, stand, open sides, height, client, type, location
    return [found[i] for i in order if i in found]


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


def logo_path(proj):
    logo = proj.style.get("logo")
    path = os.path.normpath(os.path.join(proj.brief, logo)) if logo else None
    return path if path and os.path.isfile(path) else None


def build_tokens(proj, defaults):
    style = proj.style
    v = dict(defaults) if defaults else dict(NEUTRAL_TOKENS)
    colors = style.get("colors") or {}
    for key, var in COLOR_VARS:
        val = str(colors.get(key) or "").strip()
        if not val:
            continue
        if re.fullmatch(r"#[0-9A-Fa-f]{3,8}|(?:rgb|rgba|hsl|hsla)\([\d\s.,%/]+\)", val):
            v[var] = val
        else:
            say(f"warning: deck-style colors.{key} = {val!r} is not a colour; template default kept")
    if colors.get("primary") and not colors.get("primary_alt") and v.get("--primary") == str(colors["primary"]).strip():
        v["--primary-alt"] = v["--primary"]
    sans = (style.get("fonts") or {}).get("sans")
    if sans and not re.search(r"[;{}<>]", sans):
        v["--sans"] = sans
    for key in ("header", "stamp"):
        if style.get(key):
            v[f"--{key}"] = css_string(style[key])
    if style.get("logo"):
        path = logo_path(proj)
        if path:
            v["--logo"] = f'url("{proj.rel(path)}")'
        else:
            say(f"warning: deck-style logo {style['logo']} not found under brief/")
    acc, ink = hex_rgb(v.get("--accent", "")), hex_rgb(v.get("--ink-strong", ""))
    if acc and ink:     # labels drawn on the accent (recommended tag): white, or the darkest ink if white fails
        v["--on-accent"] = "#FFFFFF" if contrast((255, 255, 255), acc) >= 3.0 or \
            contrast((255, 255, 255), acc) >= contrast(ink, acc) else v["--ink-strong"]
    return "\n:root{\n" + "".join(f"  {k}:{val};\n" for k, val in v.items()) + "}\n"


def colour_warnings(proj):
    """Token pairs the template relies on: ink on paper and surface, accent on paper and primary (divider
    numbers), white on accent and primary (recommended tags, dividers)."""
    out = []
    pairs = (("--ink", "--paper", 4.5), ("--ink", "--surface", 4.5), ("--muted-text", "--paper", 4.5),
             ("--accent", "--paper", 3.0), ("--accent", "--primary", 3.0),
             ("--paper", "--primary", 4.5))
    for fg, bg, need in pairs:
        a = hex_rgb(fg if fg.startswith("#") else proj.colour(fg))
        b = hex_rgb(proj.colour(bg))
        if a and b and contrast(a, b) < need:
            out.append(f"deck-style colours: {fg} on {bg} has contrast {contrast(a, b):.1f}:1 (needs {need}:1); "
                       f"adjust brief/deck-style.json")
    return out


def write_tokens(text, css):
    m = TOKENS_RE.search(text)
    return None if not m else text[:m.start(2)] + css + text[m.end(2):]


# ---------- template ----------

class Template:
    def __init__(self, path):
        with open(path, encoding="utf-8-sig") as f:
            self.src = f.read()
        self.root = parse(self.src)
        self.slides = slides_of(self.root)
        if not self.slides:
            raise SystemExit(f'the template has no <section class="slide ...">: {path}')
        self.examples = {}
        for s in self.slides:
            self.examples.setdefault(layout_of(s), []).append(s)
        self.prefix = self.src[:self.slides[0].start].rstrip()
        while self.prefix.endswith("-->") and "<!--" in self.prefix:     # the first example's doc comment
            self.prefix = self.prefix[:self.prefix.rfind("<!--")].rstrip()
        self.prefix += "\n\n"
        self.suffix = self.src[self.slides[-1].end:]
        rows = [s.get("data-rows") for s in self.examples.get("table", []) if s.get("data-rows")]
        self.table_rows = int(rows[0]) if rows and rows[0].isdigit() else TABLE_ROWS

    def example(self, layout, variants=()):
        cands = self.examples.get(layout) or []
        if not cands:
            return None
        known = VARIANTS.get(layout, ())

        def score(s):
            cls = s.classes()
            return sum(v in cls for v in variants) - 0.1 * sum(c in known and c not in variants for c in cls)
        return max(cands, key=score).clone()


# ---------- page plan ----------

class Page:
    def __init__(self, kind, layout, pid, title, group, variants=(), covers=(), concept=None, part="", **data):
        self.kind, self.layout, self.pid, self.title, self.group = kind, layout, pid, title, group
        self.variants, self.covers, self.concept, self.part, self.data = tuple(variants), list(covers), concept, part, data


def covers_for(proj, kind, types=None):
    return [p["id"] for p in proj.points if kind in TYPE_PAGES.get(p["type"], ()) and (not types or p["type"] in types)]


def chunks(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)] or [[]]


def concept_title(L, c, fmt):
    return fmt.format(c.name if c and c.name else L["concept"].format(c.letter if c else "?"))


def text_units(s):
    """Width of s in CJK character widths (a Latin letter or digit is about 0.55)."""
    return sum(1.0 if ord(ch) >= 0x2E80 else 0.55 for ch in str(s))


def col_fractions(widths, n):
    fixed = [float(w.rstrip("%")) / 100 if w else None for w in widths] if widths else [None] * n
    free = [i for i, w in enumerate(fixed) if w is None]
    rest = max(0.0, 1 - sum(w for w in fixed if w))
    return [w if w is not None else rest / max(1, len(free)) for w in fixed]


def auto_widths(header, rows):
    """Column widths that follow the content: a one-character ID column stays narrow, long text gets room."""
    weights = []
    for j in range(len(header)):
        lens = [text_units(r[j]) for r in rows if j < len(r)] or [0]
        need = max(text_units(header[j]), 0.6 * sum(lens) / len(lens) + 0.4 * max(lens), 2)
        weights.append(need ** 0.6)
    fr = [max(0.05, w / sum(weights)) for w in weights]
    return [f"{100 * f / sum(fr):.0f}%" for f in fr]


def table_chunks(rows, cells_of, widths, max_rows=TABLE_ROWS):
    """Rows split into slides by their estimated height (18 px text, 28 px lines, 1760 px wide table)."""
    out, cur, h = [], [], 0
    for r in rows:
        cells = cells_of(r)
        fr = col_fractions(widths, len(cells))
        lines = max([1] + [math.ceil(text_units(c) / max(1.0, (1760 * f - 24) / 18)) for c, f in zip(cells, fr)])
        px = lines * 28 + 31
        if cur and (h + px > TABLE_HEIGHT or len(cur) >= max_rows):
            out.append(cur)
            cur, h = [], 0
        cur.append(r)
        h += px
    return out + [cur] if cur or not out else out


def response_widths(proj):
    return ["7%", "27%"] + [None] * len(proj.concepts) + ["8%"]


def plan_pages(proj, tpl):
    L, P = proj.L, []
    add = P.append
    lead = proj.lead
    add(Page("cover", "cover", "cover", "", 0, ("bleed",) if lead and lead.hero else ("split",)))
    add(Page("agenda", "agenda", "agenda", L["agenda"], 0))
    add(Page("facts", "facts", "facts", L["facts"], 1, covers=covers_for(proj, "facts")))
    def brief_cells(p):
        return [p["id"], "空间", p["text"], p["source"], "见第 00、00、00 页"]
    for i, part in enumerate(table_chunks(proj.points, brief_cells, BRIEF_WIDTHS)):
        add(Page("brief", "table", "brief" if i == 0 else f"brief-{i + 1}", L["brief"] + (L["cont"] if i else ""), 1,
                 rows=part))
    add(Page("insight", "statement", "insight", L["insight"], 2, covers=covers_for(proj, "insight")))
    add(Page("message", "cards", "message", L["message"], 2, ("n3",), covers=covers_for(proj, "message")))
    add(Page("overview", "overview", "overview", L["overview"], 3))
    for c in proj.concepts:
        add(Page("board", "board", f"{c.letter}-board", concept_title(L, c, "{}"), 3,
                 covers=covers_for(proj, "board"), concept=c))
        add(Page("front", "stage", f"{c.letter}-front", L["front"], 3, concept=c))
        add(Page("detail", "detail", f"{c.letter}-detail", concept_title(L, c, L["detail"]), 3,
                 covers=covers_for(proj, "detail"), concept=c))
    if proj.concepts:
        add(Page("compare", "compare", "compare", L["compare"], 3))
    add(Page("zones", "plan", "zones", L["zones"], 4, covers=covers_for(proj, "zones"), concept=lead))
    add(Page("materials", "facts", "materials", L["materials"], 4, covers=covers_for(proj, "materials"),
             concept=lead))
    for kind, layout, types in (("screens", "cards", ("screen", "product")), ("interaction", "flow", ("interactive",)),
                                ("hospitality", "cards", ("hospitality", "giveaway")),
                                ("graphic", "gallery", ("graphic",)), ("responses", "cards", ("other",))):
        pts = [p for p in proj.points if p["type"] in types]
        if not pts:
            continue
        per = 4 if layout == "gallery" else 6
        for i, part in enumerate(chunks(pts, per)):
            k = len(part)
            variants = (f"n{2 if k <= 2 else 3 if k == 3 else 4 if k == 4 else 6}",) if layout == "cards" else \
                (f"g{min(4, k)}",) if layout == "gallery" else ()
            add(Page(kind, layout, kind if i == 0 else f"{kind}-{i + 1}", L[kind] + (L["cont"] if i else ""), 4,
                     variants, covers=[p["id"] for p in part], concept=lead, points=part))
    add(Page("appendix", "divider", "appendix", L["appendix"], 5, part="appendix"))
    mx = 30 if len(proj.concepts) >= 3 else 50     # CJK budget of a response cell (see b_table)

    def resp_cells(p):
        return [p["id"], p["text"]] + ["中" * mx] * len(proj.concepts) + ["00, 00, 00"]
    for i, part in enumerate(table_chunks(proj.points, resp_cells, response_widths(proj))):
        add(Page("response", "table", "response" if i == 0 else f"response-{i + 1}",
                 L["response"] + (L["cont"] if i else ""), 5, part="appendix", rows=part))
    n = tpl.table_rows
    for kind, tbl in (("assumptions", table_with(proj.read("brief", "requirement-card.md"), r"^A\d+")),
                      ("claims", claims_table(proj)), ("geometry", None),
                      ("ideas", table_with(proj.read("brief", "ideas.md")))):
        if kind == "geometry":
            items = []
            for c in proj.concepts:
                items.append((c, c.plan, "plan"))
                items.append((c, c.massing[0] if c.massing else None, "massing"))
            for i, part in enumerate(chunks(items, 4)):
                add(Page("geometry", "gallery", "geometry" if i == 0 else f"geometry-{i + 1}",
                         L["geometry"] + (L["cont"] if i else ""), 5, (f"g{max(1, len(part))}",), part="appendix",
                         items=part))
            continue
        header, rows = tbl if tbl else (None, [])
        widths = auto_widths(header, rows) if header else None
        for i, part in enumerate(table_chunks(rows, lambda r: r, widths, n) if rows else [[]]):
            add(Page(kind, "table", kind if i == 0 else f"{kind}-{i + 1}", L[kind] + (L["cont"] if i else ""), 5,
                     part="appendix", header=header, rows=part, widths=widths))
    return P


# ---------- filling a cloned example ----------

class Ctx:
    def __init__(self, proj, tpl):
        self.proj, self.tpl, self.L, self.lang = proj, tpl, proj.L, proj.lang
        self.warnings, self.notes = [], []

    def budget(self, n):
        return int(round(n * EN_BUDGET)) if self.lang == "en" else n

    def fill(self, node, value, keep=()):
        if node is None:
            return
        node.set_text(keep_units(str(value)), keep)
        node.filled = True

    def todo(self, node, hint=None):
        if node is None:
            return
        node.set_text(f"TODO: {hint}" if hint else "TODO")
        node.filled = True

    def fit(self, node, value):
        """Text taken from the project: filled when it fits the slot's budget, else left as TODO with it as hint."""
        if node is None:
            return
        mx = node.get("data-max")
        if value and (not (mx or "").isdigit() or visible_len(value) <= int(mx)):
            self.fill(node, value)
        else:
            self.todo(node, value or None)

    def known(self, node, value, hint_key, hint=None):
        """A fact from the project (fitted to the budget), else TODO with the slot kind's hint."""
        if value:
            self.fit(node, value)
        else:
            self.todo(node, hint or hint_for(self.lang, hint_key))

    def tr(self, key, *args):
        v = self.L[key]
        return v.format(*args) if args else v


def hint_for(lang, name):
    n = (name or "").lower()
    n = re.sub(r"^[a-z]-", "", n)          # A-name -> name
    return next((h for k, h in HINTS[lang] if re.search(k, n)), None)


def slot_named(node, *keys, exclude=()):
    """The first content slot named like one of keys: exact (ignoring an "A-" prefix and digits), then substring."""
    slots = [(s, s.get("data-slot", "").lower()) for s in content_slots(node) if s.get("data-slot") not in exclude]
    for k in keys:
        for s, n in slots:
            base = re.sub(r"^[a-z]-", "", n)
            if k in (n, base, re.sub(r"\d+", "", base)):
                return s
    for k in keys:
        for s, n in slots:
            if k in n:
                return s
    return None


def media_of(n):
    return n.tag == "figure" or n.has_class("placeholder")


def shape(unit):
    names = tuple(re.sub(r"\d+", "#", re.sub(r"^[A-Z]-", "", s.get("data-slot", ""))) for s in slot_nodes(unit))
    return names, tuple("media" for n in [unit] + list(unit.iter()) if media_of(n))


def signature(n):
    return n.tag, tuple(sorted(c for c in n.classes() if c not in ("rec", "on", "active", "first", "last")))


def repeat_groups(root):
    """Units: element children of one container sharing one signature and one inner shape, at least two."""
    groups = []
    for el in [root] + list(root.iter()):
        if el.tag in ("tr", "colgroup"):
            continue
        sigs = {}
        for k in (c for c in el.children if c.is_el):
            sigs.setdefault(signature(k), []).append(k)
        if not sigs:
            continue
        units = max(sigs.values(), key=len)
        if len(units) < 2 or any(u.has_class("slide") for u in units):
            continue
        if len({shape(u) for u in units}) == 1 and shape(units[0]) != ((), ()):
            groups.append(units)
    return groups


def units_where(root, pred):
    return next((u for u in repeat_groups(root) if pred(u[0])), [])


def has_media(u):
    return any(media_of(n) for n in [u] + list(u.iter()))


def number_el(u):
    return [n for n in [u] + list(u.iter()) if n.get("data-slot") is None and any(c in NUM_CLASSES for c in n.classes())
            and re.fullmatch(r"\s*\d{1,2}\s*", n.text())]


def unit_letter(u):
    if u.get("data-concept"):
        return u.get("data-concept")
    for s in slot_nodes(u):
        m = re.match(r"^([A-Z])-", s.get("data-slot", ""))
        if m:
            return m.group(1)
    le = next((n for n in [u] + list(u.iter()) if n.has_class("letter")), None)
    t = le.text().strip() if le is not None else ""
    return t if re.fullmatch(r"[A-Z]", t) else None


def set_unit_letter(ctx, u, letter):
    old = unit_letter(u)
    if u.get("data-concept") is not None:
        u.set("data-concept", letter)
    for s in slot_nodes(u):
        name = s.get("data-slot")
        if old and name.startswith(old + "-"):
            s.set("data-slot", letter + name[len(old):])
    for le in [n for n in [u] + list(u.iter()) if n.has_class("letter")]:
        if le.get("data-slot") is not None:
            ctx.fill(le, letter)
        elif not any(c.is_el for c in le.children):
            le.set_text(letter)


def renumber(unit, old, new, names=True):
    """Advance a cloned unit's numbers: slot names (c1-title -> c4-title) when they are numbered, and number
    elements such as <span class="n">01</span>."""
    for s in slot_nodes(unit) if names else []:
        s.set("data-slot", re.sub(rf"(?<!\d){old}(?!\d)", str(new), s.get("data-slot"), count=1))
    for n in number_el(unit):
        t = n.text().strip()
        if int(t) == old:
            n.set_text(f"{new:0{len(t)}d}")


def fit_units(units, n, proto=None):
    """n units: existing ones kept in order, clones of the prototype added (numbers advanced), extras removed."""
    if not units:
        return []
    proto = proto or units[0]
    names = len({tuple(re.sub(r"^[A-Z]-", "", s.get("data-slot")) for s in slot_nodes(u)) for u in units}) > 1
    numbered = names or any(number_el(u) for u in units)   # A-r1, B-r1 differ by concept letter, not by number
    proto_i = units.index(proto) + 1
    parent, keep = units[0].parent, units[:n]
    gap = "\n"
    i0 = parent.children.index(units[0])
    if i0 > 0 and parent.children[i0 - 1].tag == "#text" and not parent.children[i0 - 1].raw.strip():
        gap = parent.children[i0 - 1].raw
    for extra in units[n:]:
        extra.remove()
    last = keep[-1] if keep else None
    while len(keep) < n:
        c = proto.clone()
        if numbered:
            renumber(c, proto_i, len(keep) + 1, names)
        if last is None:
            parent.append(c)
        else:
            parent.insert_after(last, c, gap)
        keep.append(c)
        last = c
    return keep


def set_count_class(sec, prefix, n):
    """The variant class that encodes a count (cards n3, gallery g2) follows the number of units."""
    sec.set_classes([c for c in sec.classes() if not re.fullmatch(rf"{prefix}\d", c)] + [f"{prefix}{n}"])


def is_render_path(proj, path):
    rel = os.path.relpath(path, proj.root).replace(os.sep, "/") if path else ""
    return bool(re.match(r"^concepts/[^/]+/renders/", rel))


def placeholder(what, fill=False):
    style = ' style="height:100%"' if fill else ""
    return element(f'<div class="placeholder" data-todo="{esc(what)}"{style}>{esc(what)}</div>')


def put_image(ctx, fig, path, missing):
    """Point a figure at path (its class follows the image: booth renders "render", anything else "pic"), or put a
    placeholder naming what is missing. The placeholder fills the figure, which keeps the layout's size and turns
    into figure.pic so no draft stamp sits on an empty panel."""
    if fig is None:
        return None
    if not (path and os.path.isfile(path)):
        if fig.tag != "figure":
            fig.set("data-todo", missing)
            fig.set_text(missing)
            return fig
        fig.set_classes(["pic"] + [c for c in fig.classes() if c not in ("render", "pic", "contain")])
        fig.set_inner([placeholder(missing, fill=True)])
        return fig
    if fig.tag != "figure":
        new = element('<figure class="pic"><img alt=""></figure>')
        fig.replace_with(new)
        fig = new
    img = fig.find(lambda n: n.tag == "img")
    if img is None:
        img = element('<img alt="">')
        fig.children.insert(0, img)
        img.parent = fig
    img.set("src", ctx.proj.rel(path))
    render = is_render_path(ctx.proj, path)
    cls = [c for c in fig.classes() if c not in ("render", "pic")]
    if not render and path.lower().endswith(("plan.png", "plan.svg")) or "massing" in os.path.basename(path):
        cls.append("contain")
    fig.set_classes((["render"] if render else ["pic"]) + cls)
    return fig


def media(node):
    return [n for n in node.iter() if media_of(n) and not any(media_of(a) for a in n.ancestors() if a is not node)]


def fill_media(ctx, node, items):
    """Figures and placeholders of node, in order, take (path, what-is-missing) items; extras keep the first item."""
    for i, m in enumerate(media(node)):
        if i < len(items):
            put_image(ctx, m, *items[i])
        elif items:
            put_image(ctx, m, *items[-1])


def hero(ctx, c):
    return (c.hero if c else None), ctx.tr("ph_hero", c.letter if c else "?")


def front(ctx, c, fallback=True):
    """The front view; pages that only need a picture of the concept fall back to the hero."""
    return ((c.front or (c.hero if fallback else None)) if c else None), ctx.tr("ph_front", c.letter if c else "?")


def plan_img(ctx, c):
    return (c.plan if c else None), ctx.tr("ph_plan", c.letter if c else "?")


def set_section(ctx, sec, page):
    known = VARIANTS.get(page.layout, ())
    keep = [c for c in sec.classes() if c not in ("slide", page.layout) and c not in known]
    sec.set_classes(["slide", page.layout] + [v for v in page.variants if v != "framed"] + keep)
    sec.set("data-id", page.pid)
    sec.set("data-covers", " ".join(page.covers) or None)
    per_concept = page.kind in ("board", "front", "detail")
    sec.set("data-concept", page.concept.letter if page.concept and per_concept else None)
    sec.set("data-part", page.part or None)
    style = ";".join(d.strip() for d in (sec.get("style") or "").split(";")
                     if d.strip() and not d.strip().startswith("--accent"))
    c = page.concept
    accent = c.accent if c and c.accent and (per_concept or page.kind in ("zones", "materials")) else None
    # the accent draws concept letters, numbers and rules: keep it legible on this page's own background
    dark = page.layout in ("stage", "divider") or sec.has_class("dark")
    bg = ctx.proj.colour("--primary" if page.layout == "divider" else "--ink-strong" if dark else "--paper")
    base = accent or (ctx.proj.colour("--accent") if dark else None)
    fixed = legible(base, bg) if base else None
    if fixed and fixed.lower() != base.lower():
        accent = fixed
        how = "lightened" if luminance(hex_rgb(fixed)) > luminance(hex_rgb(base)) else "darkened"
        ctx.notes.append(f"{page.pid}: accent {base} {how} to {fixed} so it reads on this page's background")
    if accent:
        style = (style + ";" if style else "") + f"--accent:{accent}"
    sec.set("style", style or None)


def fill_chrome(ctx, sec, page):
    """Page title, section number (.head .no or a no/sec slot), running header slot, logo."""
    per_concept = page.concept is not None and page.kind in ("board", "front", "detail")
    mark = page.concept.letter if per_concept else (f"{page.group:02d}" if page.group else "")
    for s in leaf_slots(sec):
        name = s.get("data-slot", "").lower()
        if name == "title" and page.title:
            ctx.fill(s, page.title)
        elif name in SEC_SLOTS and mark:
            ctx.fill(s, mark if page.layout != "divider" else f"{page.group:02d}")
        elif name in HEADER_SLOTS:
            ctx.fill(s, ctx.proj.style.get("header") or "")
    for n in sec.iter():
        if n.get("data-slot") is None and n.has_class("no") and any(
                a.has_class("head") or a.tag == "header" for a in n.ancestors()) and mark:
            n.set_text(mark)
    logo = logo_path(ctx.proj)
    for tile in sec.find_all(lambda n: any(c in ("logo-tile", "logo") for c in n.classes()) and n.tag != "img"):
        if logo:
            tile.set_inner([element(f'<img src="{esc(ctx.proj.rel(logo))}" alt="">')])
        else:
            tile.remove()
    for img in sec.find_all(lambda n: n.tag == "img" and n.has_class("logo")):
        if logo:
            img.set("src", ctx.proj.rel(logo))
        else:
            img.remove()


def fill_labels(ctx, sec):
    """lbl-* slots keep the template's Chinese label in zh decks and are translated in en decks."""
    for s in leaf_slots(sec):
        if not is_lbl(s) or s.filled:
            continue
        s.filled = True
        if ctx.lang == "zh":
            continue
        t = s.text().strip()
        parts = [LBL_EN.get(x.strip(), x.strip()) for x in t.split("·")]
        if t in LBL_EN:
            s.set_text(LBL_EN[t], keep=("small",))
        elif not any(re.search(r"[\u3400-\u9fff]", x) for x in parts):
            s.set_text(" · ".join(x for x in parts if x), keep=("small",))
        else:
            ctx.warnings.append(f"label {s.get('data-slot')} '{t}' has no English entry in LBL_EN; left as is")


def table_html(header, rows, widths=None, id_col=True):
    """rows: lists of cells; a cell is text, ("todo", slot, max, hint) or ("ref", target)."""
    out = []
    if widths:
        out.append("<colgroup>" + "".join(f'<col style="width:{w}">' if w else "<col>" for w in widths) + "</colgroup>")
    out.append("<thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in header) + "</tr></thead><tbody>")
    for r in rows:
        cells = []
        for j, c in enumerate(r):
            if isinstance(c, tuple) and c[0] == "todo":
                mx = f' data-max="{c[2]}"' if c[2] else ""
                cells.append(f'<td data-slot="{esc(c[1])}"{mx}>{esc("TODO: " + c[3] if c[3] else "TODO")}</td>')
            elif isinstance(c, tuple) and c[0] == "ref":
                style = ' data-ref-style="num"' if len(c) > 2 and c[2] == "num" else ""
                cells.append(f'<td><span data-ref="{esc(c[1])}"{style}>TODO</span></td>')
            else:
                cls = ' class="id"' if j == 0 and id_col else ""
                cells.append(f"<td{cls}>{esc(c)}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody>")
    return "\n".join(out)


def fill_table(ctx, sec, header, rows, widths=None, foot=None):
    tbl = sec.find(lambda n: n.tag == "table")
    if tbl is None:
        holder = sec.find(lambda n: n.has_class("body")) or sec
        tbl = element('<table class="tbl"></table>')
        holder.append(tbl)
    id_col = bool(rows) and all(isinstance(r[0], str) and REF_RE.match(r[0].strip()) for r in rows)
    tbl.set_inner(fragment(table_html(header, rows, widths, id_col)))
    fs = slot_named(sec, "foot", "note")
    if fs is not None:
        if foot:
            ctx.fill(fs, foot)
        else:
            fs.remove()


# -- builders: one per page kind; slots they leave alone become TODO (with a hint) afterwards --

def b_cover(ctx, sec, page):
    ctx.todo(slot_named(sec, "title"), {"zh": "提案标题：一句话说出这个展台", "en": "proposal title: the stand in a phrase"}[ctx.lang])
    fill_media(ctx, sec, [hero(ctx, ctx.proj.lead)])


def b_agenda(ctx, sec, page, pages):
    groups = []
    for p in pages:
        if p.group and p.group not in [g[0] for g in groups]:
            groups.append((p.group, p.pid, []))
        if p.group:
            title = re.sub(re.escape(ctx.L["cont"]) + "$", "", p.title).strip()
            if p.kind in ("board", "front", "detail"):
                title = ctx.tr("concept", p.concept.letter)
            g = next(g for g in groups if g[0] == p.group)
            if title and title not in g[2] and p.kind != "appendix":
                g[2].append(title)
    units = fit_units(units_where(sec, lambda u: content_slots(u)), len(groups))
    for u, (g, pid, titles) in zip(units, groups):
        for n in number_el(u):
            n.set_text(f"{g:02d}")
        pg = next((n for n in u.iter() if any(c in ("pg", "page") for c in n.classes())
                   or re.fullmatch(r"(page|pg)\d*", (n.get("data-slot") or "").lower())), None)
        if pg is not None:              # the page number: a page reference, refreshed by check and render
            pg.set("data-ref", pid)
            pg.set("data-ref-style", "num")
            pg.set_text("TODO")
            pg.filled = True
        no = slot_named(u, "no", "num", "n")
        if no is not None and re.fullmatch(r"(no|num|n)\d*", no.get("data-slot").lower()):
            ctx.fill(no, f"{g:02d}")
        slots = [s for s in content_slots(u) if not s.filled]
        if slots:
            ctx.fill(slots[0], ctx.L["groups"][g])
        if len(slots) > 1:
            mx = int(slots[1].get("data-max") or 40)
            sep = " · "
            text = ""
            for t in titles:
                cand = t if not text else text + sep + t
                if visible_len(cand) > mx:
                    break
                text = cand
            ctx.fill(slots[1], text)


def b_divider(ctx, sec, page):
    if page.kind == "appendix":
        ctx.fill(slot_named(sec, "sub", "lead", "body", "text"), ctx.L["appendix_sub"])
    fill_media(ctx, sec, [hero(ctx, ctx.proj.lead)])


def fill_kv(ctx, sec, rows, value_hint=None):
    units = fit_units(units_where(sec, lambda u: len(content_slots(u)) >= 2), max(len(rows), 1))
    for u, (k, v) in zip(units, rows):
        slots = content_slots(u)
        ks = slot_named(u, "key", "k", "dt", "label", "term") or (slots[0] if slots else None)
        vs = next((s for s in slots if s is not ks), None)
        ctx.fit(ks, k) if k else ctx.todo(ks, hint_for(ctx.lang, "title"))
        ctx.fit(vs, v) if v else ctx.todo(vs, value_hint)


def b_facts(ctx, sec, page):
    proj = ctx.proj
    if page.kind == "facts":
        rows = fact_rows(proj, ctx.lang)
        units = units_where(sec, lambda u: len(content_slots(u)) >= 2)
        rows = rows[:len(units) or 5] if rows else [("", "")]
        fill_kv(ctx, sec, rows)
        lead = proj.lead      # the stand's size shown with our own white model, never a tender or venue image
        model = (lead.massing[0] if lead and lead.massing else None) or (lead.plan if lead else None)
        fill_media(ctx, sec, [(model, ctx.L["ph_massing"].format(lead.letter if lead else "?"))])
    else:   # details & materials of the recommended concept
        hint = {"zh": "在哪里用、什么效果", "en": "where and how"}[ctx.lang]
        md = page.concept.md if page.concept else ""
        found = [md_value(md, *keys) for keys in MATERIAL_KEYS]      # from the concept's atmosphere section
        fill_kv(ctx, sec, [(k, v or "") for k, v in zip(ctx.L["material_keys"], found)], hint)
        fill_media(ctx, sec, [front(ctx, page.concept)])


def b_statement(ctx, sec, page):
    if page.kind == "insight":
        ctx.fill(slot_named(sec, "label", "kicker", "tag"), ctx.L["insight_label"])
        insight = md_value(ctx.proj.read("brief", "ideas.md"), "insight", "洞察")
        if insight:
            ctx.fit(slot_named(sec, "statement", "say", "text"), insight)
    fill_media(ctx, sec, [hero(ctx, ctx.proj.lead)])


def point_hint(ctx, p):
    t = p["text"] if len(p["text"]) <= 30 else p["text"][:29] + "…"
    return {"zh": f"回应 {p['id']}：{t}", "en": f"answer {p['id']}: {t}"}[ctx.lang]


def b_cards(ctx, sec, page):
    pts = page.data.get("points") or []
    n = max(2, len(pts)) if pts else 3
    units = fit_units(units_where(sec, lambda u: content_slots(u)), n)
    set_count_class(sec, "n", 2 if n <= 2 else 3 if n == 3 else 4 if n == 4 else 6)
    lead = slot_named(sec, "lead")
    for i, u in enumerate(units):
        slots = content_slots(u)
        k = slot_named(u, "k", "kicker")
        title = slot_named(u, "title", "head", "name") or next((s for s in slots if s is not k), None)
        body = next((s for s in slots if s not in (k, title)), None)
        if pts and i < len(pts):
            p = pts[i]
            ctx.fill(k, ctx.L["types"].get(p["type"], p["type"]))
            ctx.todo(title, point_hint(ctx, p))
            ctx.todo(body, {"zh": "怎样实现：位置、内容、规模", "en": "how: where, what, how big"}[ctx.lang])
        elif pts:       # a page answering one point still shows two cards: the second supports the first
            ctx.todo(k, ctx.L["extra_card"])
            ctx.todo(title, ctx.L["extra_card"])
        elif page.kind == "message":
            ctx.fill(k, ctx.tr("key_msg", i + 1))
            l2 = md_value(ctx.proj.read("brief", "content.md"), "L2 key messages", "L2", "key messages", "关键信息")
            ctx.todo(title, l2 or {"zh": "关键信息（L2），出自信息平台",
                                   "en": "key message (L2) from the message platform"}[ctx.lang])
            ctx.todo(body, {"zh": "依据：出自客户资料的内容", "en": "proof from the client's own material"}[ctx.lang])
    if page.kind == "message":
        l1 = md_value(ctx.proj.read("brief", "content.md"), "L1 headline options", "L1 headline", "L1", "主标题")
        ctx.todo(lead, l1 or {"zh": "主标题（L1），出自 content.md 的信息平台",
                              "en": "headline (L1) from content.md"}[ctx.lang])
    for u in units:
        fill_media(ctx, u, [hero(ctx, page.concept)])


def b_overview(ctx, sec, page):
    cs, lead = ctx.proj.concepts, ctx.proj.lead
    units = units_where(sec, has_media) or units_where(sec, lambda u: content_slots(u))
    if not cs:
        for u in units[1:]:
            u.remove()
        if units:
            units[0].replace_with(placeholder(ctx.L["ph_concepts"]))
        return
    plain = next((u for u in units if not u.has_class("rec")), units[0] if units else None)
    units = fit_units(units, len(cs), plain)
    for u, c in zip(units, cs):
        set_unit_letter(ctx, u, c.letter)
        u.set_classes([x for x in u.classes() if x != "rec"] + (["rec"] if c is lead else []))
        name = slot_named(u, "name", "title")
        ctx.known(name, c.name, "name")
        alt = slot_named(u, "alt", "name2", exclude=(name.get("data-slot") if name else "",))
        ctx.known(alt, c.name2, "alt")
        man = slot_named(u, "manifesto", "man", "line", "tagline")
        ctx.known(man, c.manifesto, "manifesto")
        ctx.known(slot_named(u, "idea", "para", "body", "text"), c.idea, "idea")
        fill_media(ctx, u, [hero(ctx, c)])


def b_board(ctx, sec, page):
    c = page.concept
    set_unit_letter(ctx, sec, c.letter)
    ctx.fill(slot_named(sec, "letter"), c.letter)
    name = slot_named(sec, "name")
    ctx.known(name, c.name, "name")
    alt = slot_named(sec, "name-alt", "alt", "name2", exclude=(name.get("data-slot") if name else "",))
    ctx.known(alt, c.name2, "alt")
    man = slot_named(sec, "manifesto", "man")
    ctx.known(man, c.manifesto, "manifesto")
    ctx.known(slot_named(sec, "para", "body", "idea", "text"), c.idea, "para",
              {"zh": "两三句：洞察，以及空间怎样表达它", "en": "the insight and how the space expresses it"}[ctx.lang])
    fill_media(ctx, sec, [hero(ctx, c)])


def b_stage(ctx, sec, page):
    c = page.concept or ctx.proj.lead
    if c:
        set_unit_letter(ctx, sec, c.letter)
        name = slot_named(sec, "name")
        ctx.known(name, c.name, "name")
    ctx.fill(slot_named(sec, "view"), ctx.L["front"])
    ctx.todo(slot_named(sec, "caption", "cap", "t"),
             {"zh": "这张图在看什么：从主通道看到的第一眼", "en": "what this view shows from the main aisle"}[ctx.lang])
    fill_media(ctx, sec, [front(ctx, c, fallback=False)])


def fill_swatches(ctx, sec, swatches):
    units = units_where(sec, lambda u: any("--c" in (n.get("style") or "") or n.has_class("swatch")
                                           for n in [u] + list(u.iter())))
    if not units:
        return
    if swatches:
        units = fit_units(units, min(len(swatches), len(units)))
    for i, u in enumerate(units):
        hexv, name = swatches[i] if i < len(swatches) else (None, None)
        ctx.known(next(iter(content_slots(u)), None), name, "sw1")
        for n in [u] + list(u.iter()):
            st = n.get("style") or ""
            if re.search(r"#[0-9A-Fa-f]{3,8}\b", st):
                n.set("style", re.sub(r"#[0-9A-Fa-f]{3,8}\b", hexv or "var(--tint)", st))
            if n.tag == "code" or (n.get("data-slot") is None and re.fullmatch(r"\s*#[0-9A-Fa-f]{3,8}\s*", n.text())
                                   and not any(c.is_el for c in n.children)):
                n.set_text(hexv or "TODO: #HEX")


def b_detail(ctx, sec, page):
    c = page.concept
    fill_swatches(ctx, sec, c.swatches if c else [])
    if c:
        for i, m in enumerate(c.moments[:4], 1):
            ctx.fit(slot_named(sec, f"m{i}"), m)
        ctx.known(slot_named(sec, "headline"), c.headline, "headline")
        for i, m in enumerate(c.messages[:3], 1):
            ctx.fit(slot_named(sec, f"msg{i}"), m)
        for key, value in (("atmos", c.atmos), ("sig", c.signature), ("sys", c.system), ("int", c.intensity),
                           ("note", c.note)):
            s = slot_named(sec, key)
            if value and s is not None and not s.filled:
                ctx.fit(s, value)
    fill_media(ctx, sec, [front(ctx, c)])


def b_plan(ctx, sec, page):
    c = page.concept
    fill_media(ctx, sec, [plan_img(ctx, c)])
    if c and c.name and page.kind == "zones":
        ctx.fill(slot_named(sec, "title"), f"{c.name} · {ctx.L['zones']}")
    ctx.fill(slot_named(sec, "note"), ctx.L["plan_note"])
    facts = geometry_facts(c, ctx.L)
    keys = units_where(sec, lambda u: any(is_lbl(s) for s in leaf_slots(u)) or "key" in " ".join(
        s.get("data-slot", "") for s in slot_nodes(u)))
    kinds = []
    for u in keys:
        lab = next((s for s in leaf_slots(u) if is_lbl(s) or "label" in s.get("data-slot", "")), None)
        t = lab.text() if lab is not None else ""
        kind = ("area" if re.search(r"面积|area", t, re.I) else "size" if re.search(r"长|宽|×|size|w ?x ?d", t, re.I)
                else "height" if re.search(r"高|height", t, re.I) else "open" if re.search(r"开口|open", t, re.I) else None)
        kinds.append((u, lab, kind))
    free = [k for k in ("area", "size", "height", "open", "limit") if k in facts and k not in [x[2] for x in kinds]]
    for u, lab, kind in kinds:
        if kind not in facts and free:
            kind = free.pop(0)
            if lab is not None:
                ctx.fill(lab, facts[kind][0])
        val = next((s for s in content_slots(u)), None)
        if kind in facts and val is not None:
            _, value, unit = facts[kind]
            small = val.find(lambda n: n.tag == "small")
            if small is not None:
                small.set_text(unit)
                ctx.fill(val, value, keep=("small",))
            else:
                ctx.fill(val, f"{value} {unit}".strip())
    zones = geometry_zones(c)[:ZONES_MAX]
    zu = units_where(sec, lambda u: number_el(u) and content_slots(u))
    if zu and zones:
        zu = fit_units(zu, len(zones))
        for u, z in zip(zu, zones):
            slots = content_slots(u)
            ctx.fit(slots[0], z)
            for s in slots[1:]:
                ctx.todo(s, {"zh": "这里做什么", "en": "what happens here"}[ctx.lang])


def b_compare(ctx, sec, page):
    cs, lead = ctx.proj.concepts, ctx.proj.lead
    tbl = sec.find(lambda n: n.tag == "table")
    if tbl is None:
        units = fit_units(units_where(sec, has_media) or units_where(sec, lambda u: content_slots(u)), len(cs))
        for u, c in zip(units, cs):
            set_unit_letter(ctx, u, c.letter)
            u.set_classes([x for x in u.classes() if x != "rec"] + (["rec"] if c is lead else []))
            fill_media(ctx, u, [hero(ctx, c)])
        return
    rows = tbl.find_all(lambda n: n.tag == "tr")
    first_body = next((r for r in rows if r.parent is not None and r.parent.tag != "thead"), None)
    label_col = first_body is not None and next((c for c in first_body.children if c.is_el), None) is not None and \
        next(c for c in first_body.children if c.is_el).tag == "th"
    lines = [[c for c in r.children if c.is_el and c.tag in ("td", "th")] for r in rows]
    cg = tbl.find(lambda n: n.tag == "colgroup")
    if cg is not None:
        lines.append([c for c in cg.children if c.is_el and c.tag == "col"])
    for cells in lines:
        data = cells[1:] if label_col else cells
        if not data:
            continue
        proto = next((c for c in data if not c.has_class("rec")), data[0])
        data = fit_units(data, len(cs), proto)
        for cell, c in zip(data, cs):
            cell.set_classes([x for x in cell.classes() if x != "rec"] + (["rec"] if c is lead else []))
            set_unit_letter(ctx, cell, c.letter)
            if cell.tag == "th":
                name = slot_named(cell, "name")
                ctx.known(name, c.name, "name")
                alt = slot_named(cell, "alt", exclude=(name.get("data-slot") if name else "",))
                ctx.known(alt, c.name2, "alt")


def b_flow(ctx, sec, page):
    pts = page.data.get("points") or []
    units = units_where(sec, lambda u: content_slots(u))
    units = fit_units(units, min(6, max(3, len(units))))
    if pts and units:
        ctx.todo(content_slots(units[0])[0], " · ".join(point_hint(ctx, p) for p in pts[:2]))
    ctx.todo(slot_named(sec, "lead"), {"zh": "这段互动想让观众做什么、带走什么",
                                       "en": "what visitors do and take away"}[ctx.lang])
    fill_media(ctx, sec, [front(ctx, page.concept)])


def b_gallery(ctx, sec, page):
    L = ctx.L
    if page.kind == "geometry":
        items = []
        for c, path, what in page.data.get("items") or []:
            key = "plan" if what == "plan" else "massing"
            items.append((path, ctx.tr(f"ph_{key}", c.letter), ctx.tr(f"cap_{key}", c.letter)))
        items = items or [(None, ctx.tr("ph_massing", "?"), None)]
    else:   # graphic design: one placeholder per graphic design point
        items = [(None, ctx.tr("ph_graphic", p["text"][:40]), None) for p in page.data.get("points") or []]
    units = units_where(sec, has_media)
    if not units:
        units = [m for m in media(sec)][:1]
    units = fit_units(units, len(items))
    set_count_class(sec, "g", max(1, min(4, len(units))))
    for u, (path, what, caption) in zip(units, items):
        m = [u] if media_of(u) else media(u)
        if m:
            put_image(ctx, m[0], path, what)
        cap = slot_named(u, "cap", "caption", "text", "label")
        if cap is not None:
            ctx.fill(cap, caption) if caption else ctx.todo(cap, hint_for(ctx.lang, "cap"))


def b_table(ctx, sec, page):
    L, proj = ctx.L, ctx.proj
    foot = L["foot"].get(page.kind)
    if page.kind == "brief":
        header = [L["col_id"], L["col_type"], L["col_point"], L["col_source"], L["col_where"]]
        rows = [[p["id"], L["types"].get(p["type"], p["type"]), p["text"], p["source"], ("ref", p["id"])]
                for p in page.data["rows"]]
        fill_table(ctx, sec, header, rows, BRIEF_WIDTHS, foot)
    elif page.kind == "response":
        mx = ctx.budget(30 if len(proj.concepts) >= 3 else 50)
        hint = {"zh": "怎样满足", "en": "how it meets it"}[ctx.lang]
        header = [L["col_id"], L["col_point"]] + [ctx.tr("col_concept", c.letter) for c in proj.concepts] + [L["col_page"]]
        rows = [[p["id"], p["text"]] + [("todo", f"{c.letter}-{p['id']}", mx, hint) for c in proj.concepts]
                + [("ref", p["id"], "num")] for p in page.data["rows"]]
        fill_table(ctx, sec, header, rows, response_widths(proj), foot)
    else:
        header, rows = page.data.get("header"), page.data.get("rows") or []
        if not header:
            tbl = sec.find(lambda n: n.tag == "table")
            ph = placeholder(ctx.tr("ph_table", page.kind))
            tbl.replace_with(ph) if tbl is not None else sec.append(ph)
            fs = slot_named(sec, "foot")
            if fs is not None:
                fs.remove()
            return
        rows = [(r + [""] * len(header))[:len(header)] for r in rows]
        fill_table(ctx, sec, header, rows, page.data.get("widths"), foot)


BUILDERS = {"cover": b_cover, "divider": b_divider, "statement": b_statement, "cards": b_cards, "facts": b_facts,
            "overview": b_overview, "board": b_board, "image": b_stage, "stage": b_stage, "plan": b_plan,
            "detail": b_detail, "compare": b_compare, "flow": b_flow, "gallery": b_gallery, "table": b_table}


def build_section(ctx, page, pages):
    sec = ctx.tpl.example(page.layout, page.variants)
    if sec is None:
        ctx.warnings.append(f"the template has no '{page.layout}' example; page {page.pid} is a bare stand-in")
        sec = element(f'<section class="slide {page.layout}"><header class="head"><h1 class="title" '
                      f'data-slot="title">TODO</h1></header><div class="body"><div class="placeholder" '
                      f'data-todo="template has no {page.layout} example">{page.layout}</div></div></section>')
    if ctx.lang == "en":      # the template's budgets are CJK budgets; Latin text runs about 1.8 letters per CJK
        for s in slot_nodes(sec):
            if (s.get("data-max") or "").isdigit():
                s.set("data-max", str(ctx.budget(int(s.get("data-max")))))
    set_section(ctx, sec, page)
    fill_chrome(ctx, sec, page)
    if page.layout == "agenda":
        b_agenda(ctx, sec, page, pages)
    else:
        BUILDERS.get(page.layout, lambda *a: None)(ctx, sec, page)
    fill_labels(ctx, sec)
    for s in leaf_slots(sec):
        if not s.filled:
            ctx.todo(s, hint_for(ctx.lang, s.get("data-slot")))
    return sec


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


def deck_lang(root):
    h = root.find(lambda n: n.tag == "html")
    return "en" if h is not None and (h.get("lang") or "").lower().startswith("en") else "zh"


def ref_text(lang, nums, style):
    if not nums:
        return "TODO"
    if style == "num":
        return ", ".join(f"{n:02d}" for n in nums)
    L = LABELS[lang]
    key = "see_pl" if len(nums) > 1 and "see_pl" in L else "see"
    return L[key].format(L["sep"].join(str(n) for n in nums))


def refresh_refs(root):
    lang = deck_lang(root)
    _, by_id, covers = page_map(root)
    changed, unresolved = 0, []
    for n in root.iter():
        target = n.get("data-ref")
        if target is None:
            continue
        nums = covers.get(target, [])[:3] or ([by_id[target]] if target in by_id else [])
        if not nums:
            unresolved.append(target)
        new = ref_text(lang, nums, n.get("data-ref-style"))
        if n.text() != new:
            n.set_text(new)
            changed += 1
    return changed, unresolved


# ---------- new / style ----------

def count_todos(root):
    """TODO texts on the slides (placeholders, scripts and styles excluded)."""
    n = 0
    for s in slides_of(root):
        for el in [s] + list(s.iter()):
            if el.tag in ("script", "style") or any(
                    a.has_class("placeholder") or a.tag in ("script", "style") for a in [el] + list(el.ancestors())
                    if a.is_el):
                continue
            n += sum(1 for c in el.children if c.tag == "#text" and re.search(r"\bTODO\b", c.raw))
    return n


def cmd_new(a):
    proj = Project(a.project, a.template, a.lang, a.lead)
    if not os.path.isfile(proj.template):
        sys.exit(f"template not found: {proj.template} (pass --template)")
    if os.path.isfile(proj.deck) and not a.force:
        sys.exit("pack/proposal.html already exists; use --force to rebuild it (the old one is kept as a backup)")
    tpl = Template(proj.template)
    if not proj.points:
        say("note: no design points found in brief/design-points.md (| ID | 类型/Type | 设计要点/Design point | 出处/Source |)")
    if not proj.concepts:
        say("note: no concepts found under concepts/")
    ctx = Ctx(proj, tpl)
    pages = plan_pages(proj, tpl)
    body = "\n\n".join(build_section(ctx, p, pages).html() for p in pages)
    doc = parse(tpl.prefix + body + "\n\n" + tpl.suffix)
    h = doc.find(lambda n: n.tag == "html")
    if h is not None:
        h.set("lang", "zh-CN" if proj.lang == "zh" else "en")
    title = doc.find(lambda n: n.tag == "title")
    if title is not None:
        title.set_text(proj.style.get("header") or proj.style.get("name") or "Proposal")
    refresh_refs(doc)
    text = write_tokens(doc.html(), build_tokens(proj, template_tokens(proj.template)))
    if text is None:
        say('warning: the template has no <style id="tokens"> block; deck-style.json not applied')
        text = doc.html()
    os.makedirs(proj.pack, exist_ok=True)
    if os.path.isfile(proj.deck):
        stamp, k = f"{datetime.datetime.now():%Y%m%d-%H%M}", 1
        bak = os.path.join(proj.pack, f"proposal.{stamp}.bak.html")
        while os.path.exists(bak):          # never overwrite an earlier backup made in the same minute
            k += 1
            bak = os.path.join(proj.pack, f"proposal.{stamp}-{k}.bak.html")
        shutil.copy2(proj.deck, bak)
        say(f"backup: pack/{os.path.basename(bak)}")
    with open(proj.deck, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    root = parse(text)
    phs = len(root.find_all(lambda n: n.has_class("placeholder")))
    tname = os.path.relpath(proj.template, SKILL_DIR) if proj.template == DEFAULT_TEMPLATE else proj.template
    say(f"wrote pack/proposal.html: {len(pages)} pages, {count_todos(root)} TODO texts, {phs} placeholders "
        f"(lang {proj.lang}, recommended {proj.lead.letter if proj.lead else '-'}, template {tname})")
    for i, p in enumerate(pages, 1):
        cov = f"  covers {' '.join(p.covers)}" if p.covers else ""
        say(f"  {i:2d}  {p.pid:<14} {p.layout:<9} {p.title}{cov}")
    for w in dict.fromkeys(ctx.warnings + colour_warnings(proj)):
        say(f"warning: {w}")
    for n_ in dict.fromkeys(ctx.notes):
        say(f"note: {n_}")
    uncovered = [p["id"] for p in proj.points if not any(p["id"] in pg.covers for pg in pages)]
    if uncovered:
        say(f"not covered by any page yet: {' '.join(uncovered)}")
    say("next: replace every TODO in pack/proposal.html, then python deck.py check")


def cmd_style(a):
    proj = Project(a.project, a.template)
    text = load_deck(proj)
    defaults = template_tokens(proj.template) if os.path.isfile(proj.template) else {}
    if not defaults:
        m = TOKENS_RE.search(text)
        defaults = parse_vars(m.group(2)) if m else {}
    new = write_tokens(text, build_tokens(proj, defaults))
    if new is None:
        sys.exit('pack/proposal.html has no <style id="tokens"> block')
    if new == text:
        say("tokens unchanged")
        return
    with open(proj.deck, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    say("rewrote the tokens block of pack/proposal.html from brief/deck-style.json")
    for w in colour_warnings(proj):
        say(f"warning: {w}")


# ---------- check ----------

def load_deck(proj):
    if not os.path.isfile(proj.deck):
        sys.exit("pack/proposal.html not found; run deck.py new first")
    with open(proj.deck, encoding="utf-8-sig") as f:
        return f.read()


def save_if_refs_changed(proj, text):
    root = parse(text)
    changed, unresolved = refresh_refs(root)
    if changed:
        text = root.html()
        with open(proj.deck, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        say(f"updated {changed} page reference(s)")
    return text, root, unresolved


def resolve_src(proj, src):
    s = html.unescape(src or "").strip()
    if not s or re.match(r"^(data:|https?:|//|#|about:|blob:)", s, re.I):
        return None
    return os.path.normpath(os.path.join(proj.pack, unquote(re.split(r"[?#]", s)[0])))


def slot_of(n):
    for a in [n] + list(n.ancestors()):
        if a.is_el and a.get("data-slot") is not None:
            return a.get("data-slot")
    return n.tag


NUM_TOKEN = re.compile(r"(?<![A-Za-z0-9.#_\-/])(\d+(?:,\d{3})*(?:\.\d+)?)\s*(%|万|亿|㎡|m²|m2\b|平方米|平米|米|m(?![A-Za-z]))?")
FULLWIDTH = str.maketrans("０１２３４５６７８９．％", "0123456789.%")


def norm_num(s):
    s = s.replace(",", "")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.lstrip("0") or "0"


def corpus_numbers(proj):
    texts = [proj.read("brief", os.path.basename(p)) for p in glob.glob(os.path.join(proj.brief, "*.md"))]
    texts.append(str(proj.style.get("header") or ""))
    nums = set()
    for c in proj.concepts:
        texts += [c.md, json.dumps(c.geometry, ensure_ascii=False)]
        texts += [v[1] for v in geometry_facts(c, LABELS["en"]).values()]
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
        for y in (x * 3.28084, x / 3.28084, x * 10.7639, x / 10.7639):   # m <-> ft, m² <-> ft²
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


def run_check(proj, text=None):
    text = text if text is not None else load_deck(proj)
    text, root, unresolved = save_if_refs_changed(proj, text)
    slides = slides_of(root)
    errors, warnings = [], []
    points = {p["id"]: p for p in proj.points}
    refs = {os.path.normcase(os.path.abspath(p)) for p in reference_images(proj)}
    m = TOKENS_RE.search(text)
    tokens = parse_vars(m.group(2)) if m else {}
    for var, key in (("--header", "header"), ("--stamp", "stamp")):
        if "TODO" in tokens.get(var, ""):
            errors.append(f"the {key} token is still TODO; set \"{key}\" in brief/deck-style.json, then deck.py style")
    ids, covered = {}, set()
    corpus = corpus_numbers(proj)
    for i, s in enumerate(slides, 1):
        lab = f"slide {i} {s.get('data-id') or '(no id)'}"
        pid = s.get("data-id")
        if not pid:
            errors.append(f"{lab}: no data-id")
        elif pid in ids:
            errors.append(f"{lab}: data-id '{pid}' is also used by slide {ids[pid]}")
        else:
            ids[pid] = i
        if not layout_of(s):
            warnings.append(f"{lab}: no known layout class ({' '.join(s.classes())})")
        for d in (s.get("data-covers") or "").split():
            covered.add(d)
            if points and d not in points:
                warnings.append(f"{lab}: data-covers names {d}, which is not in brief/design-points.md")
        for n in s.iter():
            srcs = [n.get("src")] if n.tag == "img" else []
            srcs += [x.group(1) for x in re.finditer(r"url\(\s*['\"]?([^'\")]+)", n.get("style") or "")]
            for src in srcs:
                path = resolve_src(proj, src)
                if path and not os.path.isfile(path):
                    errors.append(f"{lab}: image not found: {src}")
                elif path and refs and os.path.normcase(os.path.abspath(path)) in refs:
                    errors.append(f"{lab}: {src} is a reference image (listed in brief/style-cards.md); references go "
                                  f"to the image model only and are never shown in the proposal")
                elif path and not own_work(proj, path):
                    errors.append(f"{lab}: {src} is not the studio's own work for this project; the proposal shows only "
                                  f"renders, plans, massing and boards under concepts/ or pack/, and the client logo "
                                  f"named in deck-style.json")
            if n.tag == "img" and n.get("src"):
                path = resolve_src(proj, n.get("src"))
                if path and is_render_path(proj, path):
                    fig = next((x for x in n.ancestors() if x.tag == "figure"), None)
                    if fig is None or not fig.has_class("render"):
                        errors.append(f'{lab}: booth render {n.get("src")} is not inside <figure class="render"> '
                                      f"(it would miss the draft stamp)")
        todo = []
        for n in [s] + list(s.iter()):
            if any(a.has_class("placeholder") for a in [n] + list(n.ancestors()) if a.is_el):
                continue
            for c in n.children:
                if c.tag == "#text" and re.search(r"\bTODO\b", c.raw):
                    todo.append(slot_of(n) if n.get("data-ref") is None else f"page ref {n.get('data-ref')}")
        if todo:
            errors.append(f"{lab}: TODO x{len(todo)} ({', '.join(todo[:8])}{' …' if len(todo) > 8 else ''})")
        for n in slot_nodes(s):
            mx = n.get("data-max")
            t = n.text()
            if (mx or "").isdigit() and "TODO" not in t and visible_len(t) > int(mx):
                k = visible_len(t)
                errors.append(f"{lab}: {n.get('data-slot')} has {k} characters, budget {mx} (cut {k - int(mx)})")
        for n in s.find_all(lambda x: x.has_class("placeholder")):
            warnings.append(f"{lab}: placeholder – {n.get('data-todo') or n.text().strip()[:60]}")
        for shown, v in visible_numbers(s):
            if v not in corpus:
                warnings.append(f'{lab}: number "{shown}" not found in brief/*.md, concept.md or geometry.json')
    for d, p in points.items():
        if d not in covered:
            errors.append(f"design point {d} ({p['type']}: {p['text'][:50]}) is covered by no page; add {d} to the "
                          f"data-covers of the page that answers it")
    for t in sorted(set(unresolved)):
        if t not in points:
            warnings.append(f'page reference data-ref="{t}" points to no page')
    warnings += colour_warnings(proj)
    free = [i for i, s in enumerate(slides, 1) if layout_of(s) == "free"]
    if len(free) > 2:
        warnings.append(f"{len(free)} free slides ({', '.join(map(str, free))}); at most 2 – use a component instead")
    run = []
    for i, s in enumerate(slides + [None], 1):
        if s is not None and s.get("data-part") != "appendix" and not has_image(s):
            run.append(i)
            continue
        if len(run) > 3:
            warnings.append(f"slides {run[0]}–{run[-1]}: {len(run)} pages in a row without an image")
        run = []
    return slides, errors, warnings


def write_check(proj, slides, errors, warnings):
    lines = [f"deck.py check · {datetime.datetime.now():%Y-%m-%d %H:%M} · pack/proposal.html · {len(slides)} slides",
             f"RESULT: {'PASS' if not errors else 'FAIL'} – {len(errors)} errors, {len(warnings)} warnings", ""]
    if errors:
        lines += ["ERRORS"] + [f"  {e}" for e in errors] + [""]
    if warnings:
        lines += ["WARNINGS"] + [f"  {w}" for w in warnings] + [""]
    os.makedirs(proj.pack, exist_ok=True)
    with open(os.path.join(proj.pack, "check.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return lines


def cmd_check(a):
    proj = Project(a.project)
    slides, errors, warnings = run_check(proj)
    lines = write_check(proj, slides, errors, warnings)
    for line in lines[1:]:
        say(line)
    say("written to pack/check.txt")
    sys.exit(1 if errors else 0)


# ---------- render ----------

BROWSER_NAMES = ("chrome", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge",
                 "microsoft-edge", "microsoft-edge-stable", "brave-browser")


def browser_candidates():
    out = []
    if sys.platform.startswith("win"):
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                out += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                        os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                        os.path.join(base, "Chromium", "Application", "chrome.exe")]
    elif sys.platform == "darwin":
        for app in ("Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser"):
            out += [f"/Applications/{app}.app/Contents/MacOS/{app}",
                    os.path.expanduser(f"~/Applications/{app}.app/Contents/MacOS/{app}")]
    else:
        out += [f"/usr/bin/{n}" for n in BROWSER_NAMES] + ["/snap/bin/chromium", "/opt/google/chrome/chrome"]
    return out


def find_browser(arg=None):
    def ok(p):
        return (shutil.which(p) if p else None) or (p if p and os.path.isfile(p) else None)
    if arg:
        return ok(arg)
    for b in (os.environ.get("BROWSER") or "").split(os.pathsep):
        if b and re.search(r"chrom|edge|brave", os.path.basename(b), re.I) and ok(b):
            return ok(b)
    for n in BROWSER_NAMES:
        if shutil.which(n):
            return shutil.which(n)
    return next((p for p in browser_candidates() if os.path.isfile(p)), None)


def chrome(browser, args, budget, timeout=180):
    profile = tempfile.mkdtemp(prefix="deck-")
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", "--hide-scrollbars", "--allow-file-access-from-files",
           "--force-device-scale-factor=1", f"--virtual-time-budget={budget}", f"--user-data-dir={profile}"] + args
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, b"", b"timed out")
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def file_url(path, query=""):
    return pathlib.Path(path).resolve().as_uri() + query


MEASURE_JS = r"""<script id="deck-measure-script">
(function(){
  if(!/[?&]check=1/.test(location.search)) return;
  function clip(el, s){ for(var p=el.parentElement; p && p!==s; p=p.parentElement){ var cs=getComputedStyle(p);
    if(cs.overflowX!=='visible'||cs.overflowY!=='visible') return p; } return s; }
  function run(){
    var out=[];
    document.querySelectorAll('section.slide').forEach(function(s,i){
      var k=(s.getBoundingClientRect().width/1920)||1;
      s.querySelectorAll('[data-slot]').forEach(function(el){
        var cs=getComputedStyle(el), fs=parseFloat(cs.fontSize)||16, lh=parseFloat(cs.lineHeight)||fs*1.4;
        if(cs.display==='none') return;
        var v=0, h=0;
        if(cs.display!=='inline'){ v=el.scrollHeight-el.clientHeight; h=el.scrollWidth-el.clientWidth; }
        var c=clip(el,s), er=el.getBoundingClientRect(), cr=c.getBoundingClientRect();
        if(er.width>0||er.height>0){ v=Math.max(v,(er.bottom-cr.bottom)/k); h=Math.max(h,(er.right-cr.right)/k); }
        out.push({slide:i+1,id:s.getAttribute('data-id')||'',slot:el.getAttribute('data-slot'),v:Math.round(v),
                  h:Math.round(h),font_px:fs,line_px:lh,width_px:el.clientWidth||Math.round(er.width/k)});
      });
    });
    var pre=document.createElement('pre'); pre.id='deck-measure'; pre.style.display='none';
    pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
  }
  function go(){ (document.fonts&&document.fonts.ready?document.fonts.ready:Promise.resolve()).then(function(){ setTimeout(run,300); }); }
  if(document.readyState==='complete') go(); else window.addEventListener('load', go);
})();
</script>
"""


def pre_json(dom, pid):
    m = re.search(rf'<pre[^>]*\bid="{pid}"[^>]*>(.*?)</pre>', dom, re.S)
    try:
        return json.loads(html.unescape(m.group(1))) if m else None
    except ValueError:
        return None


def is_cjk_text(t):
    t = "".join(t.split())
    return bool(t) and sum("\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef" for ch in t) / len(t) > 0.3


def overflow_lines(proj, browser, budget):
    text = load_deck(proj)
    root = parse(text)
    slides = slides_of(root)
    i = text.lower().rfind("</body>")
    probe = os.path.join(proj.pack, ".proposal-measure.html")
    with open(probe, "w", encoding="utf-8", newline="\n") as f:
        f.write(text[:i] + MEASURE_JS + text[i:] if i >= 0 else text + MEASURE_JS)
    try:
        r = chrome(browser, ["--window-size=1920,1080", "--dump-dom", file_url(probe, "?check=1")], budget)
        dom = r.stdout.decode("utf-8", "replace")
    finally:
        try:
            os.remove(probe)
        except OSError:
            pass
    if not dom.strip():
        return None, "the browser returned no page"
    report = pre_json(dom, "overflow-report")
    measure = {(x["slide"], x["slot"]): x for x in pre_json(dom, "deck-measure") or []}
    source = "template report"
    if report is None:
        source = "deck.py measurement (the template wrote no #overflow-report)"
        report = [{"slide": x["slide"], "id": x["id"], "slot": x["slot"], "overflow_px": max(x["v"], x["h"])}
                  for x in measure.values() if max(x["v"], x["h"]) > 1]
    out, ignored = [], 0
    for e in report:
        px = int(e.get("overflow_px") or 0)
        idx = int(e.get("slide") or 0)
        mm = measure.get((idx, e.get("slot"))) or {}
        if px <= 1:
            continue
        line = mm.get("line_px") or (mm.get("font_px") or 22) * 1.5
        if px < max(6, 0.4 * line):     # glyphs poking out of a tight line box (display letters, titles): not text lost
            ignored += 1
            continue
        sec = slides[idx - 1] if 0 < idx <= len(slides) else None
        slot = next((s for s in slot_nodes(sec) if s.get("data-slot") == e.get("slot")), None) if sec else None
        cjk = is_cjk_text(slot.text()) if slot is not None else deck_lang(root) == "zh"
        fs = mm.get("font_px") or 22
        cw = fs if cjk else fs * 0.55
        if mm and mm.get("h", 0) > mm.get("v", 0):
            chars = math.ceil(px / cw)
        else:
            chars = math.ceil(px / (mm.get("line_px") or fs * 1.6) * max(1.0, (mm.get("width_px") or 600) / cw))
        out.append(f"slide {idx} {e.get('id') or ''} {e.get('slot')} overflows by {px} px "
                   f"(~{chars} {'字' if cjk else 'chars'})")
    if ignored:
        source += f"; {ignored} sub-line glyph overhang(s) ignored"
    return out, source


def contact_sheet(pngs, out):
    from PIL import Image, ImageDraw, ImageFont
    cols, tw, th, gap = 4, 480, 270, 24
    rows = math.ceil(len(pngs) / cols)
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * (th + gap) + gap), "#E9E7E3")
    draw = ImageDraw.Draw(sheet)
    font = None
    for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"):
        try:
            font = ImageFont.truetype(name, 22)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    for k, (n, p) in enumerate(pngs):
        x, y = gap + (k % cols) * (tw + gap), gap + (k // cols) * (th + gap)
        with Image.open(p) as im:
            sheet.paste(im.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        box = draw.textbbox((0, 0), str(n), font=font)
        draw.rectangle([x, y, x + box[2] - box[0] + 16, y + box[3] - box[1] + 12], fill="#26251F")
        draw.text((x + 8 - box[0], y + 6 - box[1]), str(n), fill="white", font=font)
    sheet.save(out)


def pdf_pages(path):
    try:
        with open(path, "rb") as f:
            return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", f.read()))
    except OSError:
        return 0


def no_browser(a):
    where = f"--browser {a.browser} not found" if a.browser else \
        "no Chrome or Edge found (tried --browser, BROWSER, PATH and the standard install folders)"
    say(f"{where}. Open pack/proposal.html in Chrome or Edge and print it to PDF (Save as PDF, margins none, "
        f"background graphics on), or pass --browser <path to chrome or msedge>.")


def cmd_render(a):
    proj = Project(a.project)
    text = load_deck(proj)
    slides, errors, warnings = run_check(proj, text)
    lines = write_check(proj, slides, errors, warnings)
    say(lines[1] + " (details in pack/check.txt)")
    pdf = os.path.join(proj.pack, "proposal.pdf")
    if errors:      # never leave a sendable PDF behind for a deck that failed the check
        if os.path.isfile(pdf):
            os.remove(pdf)
        say("render stopped: fix the errors in pack/check.txt first; no PDF is written for a deck that fails check")
        sys.exit(1)
    browser = find_browser(a.browser)
    if not browser:
        no_browser(a)
        sys.exit(1)
    say(f"browser: {browser}")
    n = len(slides)
    pdf = os.path.join(proj.pack, "proposal.pdf")
    if os.path.isfile(pdf):
        os.remove(pdf)
    r = chrome(browser, [f"--print-to-pdf={pdf}", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                         file_url(proj.deck)], a.budget)
    if not os.path.isfile(pdf):
        say(f"PDF export failed: {r.stderr.decode('utf-8', 'replace').strip()[-400:]}")
    else:
        pages = pdf_pages(pdf)
        say(f"pack/proposal.pdf: {pages or '?'} pages for {n} slides" + (
            "" if not pages or pages == n else " – the page count differs: a slide spills over (check print sizes)"))
    prev = os.path.join(proj.pack, "preview")
    os.makedirs(prev, exist_ok=True)
    for old in glob.glob(os.path.join(prev, "slide-*.png")):
        os.remove(old)

    def shot(i):
        out = os.path.join(prev, f"slide-{i:02d}.png")
        chrome(browser, [f"--screenshot={out}", "--window-size=1920,1080", file_url(proj.deck, f"?slide={i}")],
               a.budget, timeout=120)
        return out if os.path.isfile(out) else None

    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        shots = list(pool.map(shot, range(1, n + 1)))
    done = [(i, s) for i, s in enumerate(shots, 1) if s]
    missing = [str(i) for i, s in enumerate(shots, 1) if not s]
    say(f"pack/preview/: {len(done)} of {n} slide images" + (f" – missing {', '.join(missing)}" if missing else ""))
    if done:
        try:
            contact_sheet(done, os.path.join(prev, "contact.png"))
            say("pack/preview/contact.png: contact sheet")
        except ImportError:
            say("contact sheet skipped: Pillow is not installed (pip install pillow)")
    over, source = overflow_lines(proj, browser, a.budget)
    block = [f"RENDER · {datetime.datetime.now():%Y-%m-%d %H:%M} · pdf {'ok' if os.path.isfile(pdf) else 'missing'}"
             f" · {len(done)}/{n} previews"]
    if over is None:
        block.append(f"OVERFLOW: not measured – {source}")
    else:
        block.append(f"OVERFLOW: {len(over)} slot(s) – {source}")
        block += [f"  {x}" for x in over]
    for x in block[1:]:
        say(x)
    with open(os.path.join(proj.pack, "check.txt"), "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(block) + "\n")


# ---------- status ----------

def cmd_status(a):
    proj = Project(a.project)
    if not os.path.isfile(proj.deck):
        say(f"No deck yet (pack/proposal.html). The project has {len(proj.points)} design points and concepts "
            f"{', '.join(c.letter for c in proj.concepts) or 'none'}; run deck.py new.")
        return
    root = parse(load_deck(proj))
    slides = slides_of(root)
    phs = len(root.find_all(lambda n: n.has_class("placeholder")))
    t_html = os.path.getmtime(proj.deck)
    check = os.path.join(proj.pack, "check.txt")
    result, overflow = "not run", ""
    if os.path.isfile(check):
        with open(check, encoding="utf-8") as f:
            ct = f.read()
        m = re.search(r"^RESULT: (.+)$", ct, re.M)
        result = (m.group(1) if m else "unknown") + (" (older than the deck)" if os.path.getmtime(check) < t_html else "")
        o = re.findall(r"^OVERFLOW: (.+)$", ct, re.M)
        overflow = f"; overflow {o[-1].split(' – ')[0]}" if o else ""
    outs = []
    pdf = os.path.join(proj.pack, "proposal.pdf")
    if os.path.isfile(pdf):
        outs.append("proposal.pdf" + (" (older than the deck)" if os.path.getmtime(pdf) < t_html else ""))
    previews = glob.glob(os.path.join(proj.pack, "preview", "slide-*.png"))
    if previews:
        outs.append(f"{len(previews)} slide previews")
    if os.path.isfile(os.path.join(proj.pack, "preview", "contact.png")):
        outs.append("contact.png")
    layouts = {}
    for s in slides:
        layouts[layout_of(s) or "?"] = layouts.get(layout_of(s) or "?", 0) + 1
    say(f"pack/proposal.html has {len(slides)} pages ({', '.join(f'{v} {k}' for k, v in layouts.items())}), "
        f"{count_todos(root)} TODO texts and {phs} placeholders open; last check: {result}{overflow}; outputs: "
        f"{', '.join(outs) or 'none yet (run deck.py render)'}.")


# ---------- main ----------

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles choke on CJK and ·
    ap = argparse.ArgumentParser(description="Pitch deck: new, style, check, render, status")
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=".", help="the project folder (default: the current folder)")
    p = sub.add_parser("new", parents=[common], help="build pack/proposal.html from the template and the project")
    p.add_argument("--lang", choices=["zh", "en"], help="deck language (default: deck-style.json lang, else zh)")
    p.add_argument("--lead", help="the recommended concept's letter (default: the first)")
    p.add_argument("--template", help="template file (default: assets/deck/template.html of this skill)")
    p.add_argument("--force", action="store_true", help="rebuild an existing deck; the old one is kept as a backup")
    p = sub.add_parser("style", parents=[common], help="rewrite only the tokens block from brief/deck-style.json")
    p.add_argument("--template", help="template whose tokens are the defaults")
    sub.add_parser("check", parents=[common], help="check the deck; writes pack/check.txt, exit 1 on errors")
    p = sub.add_parser("render", parents=[common], help="PDF, slide previews, contact sheet, overflow check")
    p.add_argument("--browser", help="path to Chrome or Edge")
    p.add_argument("--jobs", type=int, default=4, help="parallel screenshots (default 4)")
    p.add_argument("--budget", type=int, default=8000, help="virtual time budget per page load in ms (default 8000)")
    sub.add_parser("status", parents=[common], help="one-paragraph summary")
    a = ap.parse_args(argv)
    {"new": cmd_new, "style": cmd_style, "check": cmd_check, "render": cmd_render, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
