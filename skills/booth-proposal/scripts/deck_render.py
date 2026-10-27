"""Browser, render, measurement, export and status (deck.py calls the cmd_* functions).

Moved from the old deck.py (phase 3, sub-task A): browser lookup, MEASURE_JS, overflow parsing, contact sheet, PDF
page count. cmd_render, cmd_export and cmd_status are the commands deck.py render, export and status.
Pure ASCII: non-ASCII characters are written as unicode escapes.
"""
from __future__ import annotations

import concurrent.futures
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

import common
import deck_check
import deck_html
from deck_html import slides_of, slot_nodes

# ---------- browser ----------

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
    var imgs=[];
    document.querySelectorAll('section.slide').forEach(function(s,i){
      s.querySelectorAll('img').forEach(function(im){
        if(!im.naturalWidth||!im.clientWidth||!im.clientHeight) return;
        for(var a=im;a&&a!==s;a=a.parentElement){ if(String(a.className).indexOf('logo')>=0) return; }
        var fx=im.clientWidth/im.naturalWidth, fy=im.clientHeight/im.naturalHeight;
        var f=getComputedStyle(im).objectFit==='contain'?Math.min(fx,fy):Math.max(fx,fy);
        imgs.push({slide:i+1,id:s.getAttribute('data-id')||'',src:im.getAttribute('src'),factor:Math.round(f*100)/100});
      });
    });
    var p2=document.createElement('pre'); p2.id='deck-images'; p2.style.display='none';
    p2.textContent=JSON.stringify(imgs); document.body.appendChild(p2);
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

def overflow_entries(dom, root, default_cjk=False):
    """Overflowing slots from a --dump-dom of the measured deck: (entries | None, source).
    entries = [{"page", "page_id", "slot", "px", "chars"}], None when the browser returned no page.
    root = the parsed deck; default_cjk = the chars unit when the slot text is empty."""
    slides = slides_of(root)
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
        cjk = common.cjk_ratio(slot.text()) > 0.3 if slot is not None else default_cjk
        fs = mm.get("font_px") or 22
        cw = fs if cjk else fs * 0.55
        if mm and mm.get("h", 0) > mm.get("v", 0):
            chars = math.ceil(px / cw)
        else:
            chars = math.ceil(px / (mm.get("line_px") or fs * 1.6) * max(1.0, (mm.get("width_px") or 600) / cw))
        out.append({"page": idx, "page_id": e.get("id") or "", "slot": e.get("slot"), "px": px, "chars": chars})
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




# ---------- render ----------

DEFAULT_BUDGET = 8000          # virtual time budget (ms) of one page load; deck.py render --budget overrides it


def measure(project, deck_text, browser, budget):
    """Overflow and upscale of the deck, measured in a temp probe copy (never in pack/).
    Returns (overflow | None, upscale, source); overflow None = not measured."""
    root = deck_html.parse(deck_text)
    work = tempfile.mkdtemp(prefix="deck-measure-")
    try:
        probe = os.path.join(work, "proposal.html")
        base = '<base href="' + pathlib.Path(project.path("pack")).resolve().as_uri() + '/">'
        text = deck_text
        m = re.search(r"<head\b[^>]*>", text, re.I)
        text = text[:m.end()] + base + text[m.end():] if m else base + text
        i = text.lower().rfind("</body>")
        text = text[:i] + MEASURE_JS + text[i:] if i >= 0 else text + MEASURE_JS
        with open(probe, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        r = chrome(browser, ["--window-size=1920,1080", "--dump-dom", file_url(probe, "?check=1")], budget)
        dom = r.stdout.decode("utf-8", "replace")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    overflow, source = overflow_entries(dom, root, common.cjk_ratio(root.text()) > 0.3)
    upscale = []
    if overflow is not None:
        slides = slides_of(root)
        for e in pre_json(dom, "deck-images") or []:
            if not isinstance(e, dict) or not isinstance(e.get("factor"), (int, float)) or e["factor"] <= 1.0:
                continue
            n = int(e.get("slide") or 0)
            pid = e.get("id") or (slides[n - 1].get("data-id") if 0 < n <= len(slides) else "") or ""
            upscale.append({"page": n, "page_id": pid, "src": e.get("src") or "", "factor": e["factor"]})
    return overflow, upscale, source


def _counts(findings):
    return tuple(sum(1 for f in findings if f.level == lv) for lv in ("error", "warn", "pending"))


def cmd_render(project, browser_arg, jobs, budget) -> int:
    text = deck_html.read_deck(project)
    if text is None:
        print("error: no pack/proposal.html; run deck.py new", file=sys.stderr)
        return 2
    root = deck_html.parse(text)
    changed = deck_html.refresh_refs(root, project, common.read_json_opt(project.path("work", "deck-review.json")))
    if changed:
        text = root.html()
        deck_html.write_deck(project, text)
        print(f"updated {changed} page reference(s)")
    res = deck_check.run_check(project, text, render_json=False)
    e, w, p = _counts(res.findings)
    print(f"check: {e} errors, {w} warnings, {p} pending (deck.py check for details)")
    browser = find_browser(browser_arg)
    if not browser:
        print("no Chrome or Edge found; pass --browser <path>, or open pack/proposal.html in Chrome and print to PDF "
              "(margins none, background graphics on)")
        return 3
    print(f"browser: {browser}")
    n = res.slides
    os.makedirs(project.path("work"), exist_ok=True)
    pdf = project.path("work", "proposal-draft.pdf")
    if os.path.isfile(pdf):
        os.remove(pdf)
    r = chrome(browser, [f"--print-to-pdf={pdf}", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                         file_url(deck_html.deck_path(project))], budget)
    if os.path.isfile(pdf):
        pages = pdf_pages(pdf)
        print(f"work/proposal-draft.pdf: {pages or '?'} pages for {n} slides" + (
            "" if not pages or pages == n else " \u2013 the page count differs: a slide spills over (check print sizes)"))
    else:
        pages = 0
        print(f"PDF export failed: {r.stderr.decode('utf-8', 'replace').strip()[-400:]}")
    prev = project.path("work", "preview")
    os.makedirs(prev, exist_ok=True)
    for old in glob.glob(os.path.join(prev, "slide-*.png")):
        os.remove(old)

    def shot(i):
        out = os.path.join(prev, f"slide-{i:02d}.png")
        chrome(browser, [f"--screenshot={out}", "--window-size=1920,1080",
                         file_url(deck_html.deck_path(project), f"?slide={i}")], budget, timeout=120)
        return out if os.path.isfile(out) else None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        shots = list(pool.map(shot, range(1, n + 1)))
    done = [(i, s) for i, s in enumerate(shots, 1) if s]
    missing = [str(i) for i, s in enumerate(shots, 1) if not s]
    print(f"work/preview/: {len(done)} of {n} slide images" + (f" \u2013 missing {', '.join(missing)}" if missing else ""))
    if done:
        try:
            contact_sheet(done, project.path("work", "contact.png"))
            print("work/contact.png: contact sheet")
        except ImportError:
            print("contact sheet skipped: Pillow is not installed (pip install pillow)")
    overflow, upscale, source = measure(project, text, browser, budget)
    th = project.thresholds
    if overflow is None:
        print(f"overflow: not measured \u2013 {source}")
    else:
        print(f"overflow: {len(overflow)} slot(s) \u2013 {source}")
        for x in overflow:
            print(f"  page {x['page']} {x['page_id']} {x['slot']}: overflow by {x['px']} px (~{x['chars']} chars)")
        for x in upscale:
            if x["factor"] > th["upscale_max"]:
                print(f"  page {x['page']} {x['page_id']}: image enlarged {x['factor']:g} times (max {th['upscale_max']:g})")
    common.write_json(project.path("work", "render.json"), {
        "schema": "render/1", "deck_sha256": common.sha256_text(text), "rendered_at": common.now_iso(),
        "browser": browser, "slides": n, "pdf_pages": pages, "previews": len(done),
        "measured": overflow is not None, "overflow": overflow or [], "upscale": upscale})
    return 3 if not os.path.isfile(pdf) or not done or overflow is None else 0


# ---------- export ----------

def _x(code, message, page=None, page_id=None, where="pack/proposal.html"):
    return common.Finding(code, "error", where, message, page, page_id)


def _decided_keep(record) -> set:
    pass1 = record.get("pass1") if isinstance(record.get("pass1"), dict) else {}
    keep = set()
    for it in pass1.get("pending") if isinstance(pass1.get("pending"), list) else []:
        if isinstance(it, dict) and it.get("decision") == "keep":
            keep.add((it.get("code"), it.get("page_id"), str(it.get("text") or "").casefold()))
    return keep


def cmd_export(project, browser_arg) -> int:
    text = deck_html.read_deck(project)
    if text is None:
        print("error: no pack/proposal.html; run deck.py new", file=sys.stderr)
        return 2
    # work/render.json is judged by X-RENDER below, so the check leaves it out (its overflow would be reported twice)
    res = deck_check.run_check(project, text, render_json=False)
    out = []
    errors = [f for f in res.findings if f.level == "error"]
    if errors:
        codes = list(dict.fromkeys(f.code for f in errors))[:5]
        out.append(_x("X-CHECK", f"errors: the check found {len(errors)} error(s) ({', '.join(codes)}); "
                                 f"run deck.py check"))
    # render
    rj_path = project.path("work", "render.json")
    rj = common.read_json(rj_path, "render/1") if os.path.isfile(rj_path) else None
    if rj is None:
        out.append(_x("X-RENDER", "missing: no work/render.json; run deck.py render", where="work/render.json"))
    else:
        if rj.get("measured") is not True:
            out.append(_x("X-RENDER", "unmeasured: the last render did not measure overflow; run deck.py render",
                          where="work/render.json"))
        if rj.get("deck_sha256") != res.deck_sha256:
            out.append(_x("X-RENDER", "stale: the deck changed after the last render; run deck.py render",
                          where="work/render.json"))
        elif isinstance(rj.get("overflow"), list):
            for e in rj["overflow"]:
                if isinstance(e, dict):
                    page = e.get("page") if isinstance(e.get("page"), int) else None
                    pid = e.get("page_id") if isinstance(e.get("page_id"), str) and e.get("page_id") else None
                    out.append(_x("X-RENDER", f"overflow: slot {e.get('slot')} overflows by {e.get('px')} px "
                                              f"(~{e.get('chars')} chars)", page, pid,
                                  f"page {page} {pid} {e.get('slot')}"))
    # review
    record = deck_check.read_record(project)
    if record is None:
        out.append(_x("X-REVIEW", "missing: no work/deck-review.json; review the deck (references/review.md), then "
                                  "run deck.py review --record", where="work/deck-review.json"))
    else:
        pages = record.get("pages") if isinstance(record.get("pages"), dict) else {}
        cur = deck_check.page_hashes(project, res.root, deck_check.Images(project))
        number = {s.get("data-id"): n for n, s in enumerate(slides_of(res.root), 1) if s.get("data-id")}
        for pid, h in cur.items():
            where = f"page {number[pid]} {pid}"
            was = pages.get(pid)
            if pid not in pages:
                out.append(_x("X-REVIEW", "page: the page has no entry in the review; run deck.py text --diff, "
                                          "review it, deck.py review --record", number[pid], pid, where))
            elif not isinstance(was, dict) or was.get("text_sha256") != h["text_sha256"] \
                    or list(was.get("image_sha256s") or []) != h["image_sha256s"]:
                out.append(_x("X-REVIEW", "stale: the text or images changed after the review; run deck.py text "
                                          "--diff, review the changed pages, deck.py review --record",
                              number[pid], pid, where))
        pass2 = record.get("pass2") if isinstance(record.get("pass2"), dict) else {}
        for it in pass2.get("findings") if isinstance(pass2.get("findings"), list) else []:
            if isinstance(it, dict) and it.get("resolved") is not True:
                pid = it.get("page_id") if isinstance(it.get("page_id"), str) else None
                out.append(_x("X-REVIEW", f"open: a pass-2 finding ({it.get('kind')}) is not resolved",
                              number.get(pid), pid, f"page {number.get(pid)} {pid}"))
        keep = _decided_keep(record)
        for f in res.pending:
            code, pid, word = deck_check.pending_key(f)
            if (code, pid, word.casefold()) not in keep:
                out.append(_x("X-REVIEW", f'pending: "{word}" has no keep decision in the review; run deck.py review '
                                          "--record", f.page, f.page_id, f.where))
    if out:
        common.print_findings(out)
        return 1
    # PDF
    browser = find_browser(browser_arg)
    if not browser:
        common.print_findings([_x("X-PDF", "browser: no Chrome or Edge found; pass --browser <path>")])
        return 3
    tmp = tempfile.mkdtemp(prefix="deck-export-")
    try:
        pdf = os.path.join(tmp, "proposal.pdf")
        chrome(browser, [f"--print-to-pdf={pdf}", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                         file_url(deck_html.deck_path(project))], DEFAULT_BUDGET)
        pages = pdf_pages(pdf) if os.path.isfile(pdf) else 0
        if not os.path.isfile(pdf) or pages != res.slides:
            what = "no PDF was written" if not os.path.isfile(pdf) else \
                f"the PDF has {pages} pages for {res.slides} slides"
            common.print_findings([_x("X-PDF", f"pages: {what}")])
            return 3
        dest = project.path("pack", "proposal.pdf")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(pdf, dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"pack/proposal.pdf: {pages} pages")
    return 0


# ---------- status ----------

def _read_opt(path, schema):
    if not os.path.isfile(path):
        return None
    try:
        return common.read_json(path, schema)
    except common.InputError:
        return None


def cmd_status(project) -> int:
    text = deck_html.read_deck(project)
    if text is None:
        print("No deck yet; run deck.py new.")
        return 0
    sha = common.sha256_text(text)
    root = deck_html.parse(text)
    parts = [f"pack/proposal.html: {len(slides_of(root))} slides"]
    sel = project.selection
    if sel and sel.get("selected"):
        display = sel.get("display") if isinstance(sel.get("display"), dict) else {}
        items = []
        for key in sel["selected"]:
            tag = [display[key]] if key in display else []
            if key == sel.get("lead"):
                tag.append("lead")
            items.append(f"{key} ({', '.join(tag)})" if tag else key)
        parts.append("selection: " + ", ".join(items))
    else:
        parts.append("no selection")
    ck = _read_opt(project.path("work", "check.json"), "check/1")
    if ck is None:
        parts.append("check: not run")
    else:
        c = ck.get("counts") if isinstance(ck.get("counts"), dict) else {}
        parts.append(f"check: {c.get('error', 0)} errors, {c.get('warn', 0)} warnings, {c.get('pending', 0)} pending "
                     f"({'current' if ck.get('deck_sha256') == sha else 'stale'})")
    rj = _read_opt(project.path("work", "render.json"), "render/1")
    if rj is None:
        parts.append("render: not run")
    else:
        over = rj.get("overflow") if isinstance(rj.get("overflow"), list) else []
        parts.append(f"render: {'current' if rj.get('deck_sha256') == sha else 'stale'}, {len(over)} overflow"
                     + ("" if rj.get("measured") is True else " (not measured)"))
    rec = _read_opt(project.path("work", "deck-review.json"), "deck-review/1")
    if rec is None:
        parts.append("review: none")
    else:
        old = rec.get("pages") if isinstance(rec.get("pages"), dict) else {}
        cur = deck_check.page_hashes(project, root, deck_check.Images(project))
        moved = 0
        for pid, h in cur.items():
            was = old.get(pid)
            if not isinstance(was, dict) or was.get("text_sha256") != h["text_sha256"] \
                    or list(was.get("image_sha256s") or []) != h["image_sha256s"]:
                moved += 1
        moved += sum(1 for pid in old if pid not in cur)
        parts.append(f"review: recorded {rec.get('recorded_at')}, {moved} pages changed since")
    pdf = project.path("pack", "proposal.pdf")
    if os.path.isfile(pdf):
        newer = os.path.getmtime(pdf) >= os.path.getmtime(deck_html.deck_path(project))
        parts.append("export: pack/proposal.pdf " + ("newer" if newer else "older") + " than the deck")
    else:
        parts.append("export: none")
    print("; ".join(parts) + ".")
    return 0
