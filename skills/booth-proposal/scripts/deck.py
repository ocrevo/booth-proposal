"""Proposal deck CLI: pack/proposal.html is the single source; this script never writes pages except as listed.

  new      shell with head, style#tokens, style#design, viewer and the skeleton pages of the architecture (--template, --force)
  style    rewrite only style#tokens from brief/deck-style.json and the labels (--template)
  layouts  catalogue of the template; --emit LAYOUT[:VARIANT] [--count N] [--chapter ID] prints a fragment to paste
  check    read-only check of the deck (--json writes work/check.json)
  render   refresh page references, draft PDF, previews, contact sheet, overflow and upscale (work/)
  text     page text blocks (--diff: pages changed since the recorded review)
  review   --record FILE validates and stamps a review into work/deck-review.json
  export   gate (check, render, review) then pack/proposal.pdf;  status  one-paragraph summary
Every command takes --project (default: the current folder). Exit 0 done, 1 errors, 2 bad input, 3 external failure.
"""
from __future__ import annotations

import argparse
import sys

import common
import deck_check
import deck_html
import deck_render


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Proposal deck: new, style, layouts, check, render, text, review, "
                                             "export, status")
    sub = ap.add_subparsers(dest="cmd", required=True)
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--project", default=".", help="the project folder (default: the current folder)")
    p = sub.add_parser("new", parents=[base], help="write the pack/proposal.html shell with the architecture skeleton")
    p.add_argument("--template", help="template file (default: assets/deck/template.html of this skill)")
    p.add_argument("--force", action="store_true", help="replace an existing deck (the old one goes to work/backup/)")
    p = sub.add_parser("style", parents=[base], help="rewrite only the tokens block")
    p.add_argument("--template", help="template whose tokens are the defaults")
    p = sub.add_parser("layouts", parents=[base], help="catalogue of the template, or one fragment with --emit")
    p.add_argument("--emit", metavar="LAYOUT[:VARIANT]", help="print the HTML fragment of this example")
    p.add_argument("--count", type=int, help="repeat the repeat unit N times (needs --emit)")
    p.add_argument("--chapter", metavar="ID", help="set data-chapter on the fragment (needs --emit)")
    p = sub.add_parser("check", parents=[base], help="check the deck; read-only")
    p.add_argument("--json", action="store_true",
                   help="print the findings as JSON instead of the text report, then write work/check.json")
    p = sub.add_parser("render", parents=[base], help="draft PDF, previews, contact sheet, overflow and upscale")
    p.add_argument("--browser", help="path to Chrome or Edge")
    p.add_argument("--jobs", type=int, default=4, help="parallel screenshots (default 4)")
    p.add_argument("--budget", type=int, default=8000, help="virtual time budget per page load in ms (default 8000)")
    p = sub.add_parser("text", parents=[base], help="text of every slide")
    p.add_argument("--diff", action="store_true", help="only the pages changed since the recorded review")
    p = sub.add_parser("review", parents=[base], help="record a deck review")
    p.add_argument("--record", required=True, metavar="FILE", help="work/deck-review.input.json")
    p = sub.add_parser("export", parents=[base], help="gate, then pack/proposal.pdf")
    p.add_argument("--browser", help="path to Chrome or Edge")
    sub.add_parser("status", parents=[base], help="one-paragraph summary")
    return ap


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.cmd == "layouts":
        if args.count is not None and args.emit is None:
            ap.error("--count needs --emit")
        if args.count is not None and args.count < 1:
            ap.error("--count must be at least 1")
        if args.chapter is not None and args.emit is None:
            ap.error("--chapter needs --emit")
    try:
        project = common.find_project(args.project)
        if args.cmd == "new":
            return deck_html.cmd_new(project, args.template, args.force)
        if args.cmd == "style":
            return deck_html.cmd_style(project, args.template)
        if args.cmd == "layouts":
            return deck_html.cmd_layouts(project, args.emit, args.count, args.chapter)
        if args.cmd == "check":
            return deck_check.cmd_check(project, args.json)
        if args.cmd == "render":
            return deck_render.cmd_render(project, args.browser, args.jobs, args.budget)
        if args.cmd == "text":
            return deck_check.cmd_text(project, args.diff)
        if args.cmd == "review":
            return deck_check.cmd_review_record(project, args.record)
        if args.cmd == "export":
            return deck_render.cmd_export(project, args.browser)
        return deck_render.cmd_status(project)
    except common.InputError as e:
        print(f"ERROR   {e.code} {e.where}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
