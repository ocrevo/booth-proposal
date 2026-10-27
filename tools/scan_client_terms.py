#!/usr/bin/env python3
"""Scan tracked sources for client terms. Terms come from untracked sources only:
output/client-terms.txt (or --terms FILE) and output/*/brief/brief.json (client.names, protected_terms,
do_not_mention). Output: one line per hit '<path>:<line>: <term>', then a RESULT line.
Exit 0 no hits, 1 hits, 2 no terms, a bad argument, a missing --paths entry or a corrupt zip."""
import argparse
import glob
import os
import sys
import zipfile

ROOT_DEFAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DEFAULT, "skills", "booth-proposal", "scripts"))
import common  # noqa: E402

DEFAULT_PATHS = ["skills", "tests", "tools", "README.md", "CHANGELOG.md", ".claude-plugin", "dist"]
SKIP_ANYWHERE = {".git", "__pycache__", "node_modules"}
SKIP_TOP = {"input", "output"}          # skipped only as the first path component below the root
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".html", ".svg", ".css", ".js", ".sh", ".toml",
                 ".cfg"}
ZIP_SUFFIXES = {".skill", ".zip"}
MIN_TERM = 2


def _suffix(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def _decode(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    return text[1:] if text.startswith("\ufeff") else text


def read_terms_file(path: str) -> list[str]:
    with open(path, "rb") as f:
        text = _decode(f.read())
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def read_brief_terms(root: str) -> list[str]:
    out: list[str] = []
    for path in sorted(glob.glob(os.path.join(root, "output", "*", "brief", "brief.json"))):
        try:
            data = common.read_json_opt(path)
        except Exception:  # noqa: BLE001 - skip files that fail
            continue
        if not isinstance(data, dict):
            continue
        client = data.get("client")
        names = client.get("names") if isinstance(client, dict) else None
        for value in (names, data.get("protected_terms"), data.get("do_not_mention")):
            if isinstance(value, list):
                out.extend(v for v in value if isinstance(v, str))
    return out


def clean_terms(raw: list[str]) -> list[str]:
    seen, out = set(), []
    for t in raw:
        t = t.strip()
        if len(t) < MIN_TERM or t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append(t)
    return out


def scan_text(text: str, shown: str, terms: list[str]) -> list[str]:
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for term in terms:
            for _ in common.find_term(term, line, case=False):
                hits.append(f"{shown}:{n}: {term}")
    return hits


class ScanError(Exception):
    """A --paths entry that does not exist or a zip that cannot be read: exit 2."""


def _skipped(rel_parts: list[str]) -> bool:
    return any(part in SKIP_ANYWHERE for part in rel_parts) or (bool(rel_parts) and rel_parts[0] in SKIP_TOP)


def iter_files(root: str, paths: list[str], skip_abs: set[str], strict: bool = True):
    for p in paths:
        full = os.path.normpath(os.path.join(root, p))
        if os.path.isfile(full):
            candidates = [full]
        elif os.path.isdir(full):
            candidates = []
            for dirpath, dirnames, filenames in os.walk(full):
                here = os.path.relpath(dirpath, root).replace(os.sep, "/").split("/")
                dirnames[:] = sorted(d for d in dirnames if not _skipped(here + [d]))
                candidates.extend(os.path.join(dirpath, f) for f in sorted(filenames))
        elif strict:
            raise ScanError(f"--paths entry not found: {p}")
        else:
            continue
        for f in candidates:
            rel = os.path.relpath(f, root).replace(os.sep, "/")
            if _skipped(rel.split("/")):
                continue
            if os.path.basename(f) == ".env" or os.path.normcase(os.path.abspath(f)) in skip_abs:
                continue
            yield f, rel


def scan(root: str, paths: list[str], terms: list[str], skip_abs: set[str], strict: bool = True) -> list[str]:
    hits: list[str] = []
    for f, rel in iter_files(root, paths, skip_abs, strict):
        suf = _suffix(f)
        if suf in TEXT_SUFFIXES:
            with open(f, "rb") as fh:
                hits.extend(scan_text(_decode(fh.read()), rel, terms))
        elif suf in ZIP_SUFFIXES:
            try:
                with zipfile.ZipFile(f) as z:
                    for info in sorted(z.infolist(), key=lambda i: i.filename):
                        if info.is_dir() or _suffix(info.filename) not in TEXT_SUFFIXES:
                            continue
                        hits.extend(scan_text(_decode(z.read(info)), f"{rel}!{info.filename}", terms))
            except (zipfile.BadZipFile, OSError) as e:
                raise ScanError(f"cannot read zip {rel}: {e}") from e
    return hits


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=ROOT_DEFAULT, help="repo root (default: the folder above tools/)")
    ap.add_argument("--terms", nargs="*", default=None, help="word list file(s), UTF-8, one term per line")
    ap.add_argument("--paths", nargs="*", default=None, help=f"default: {' '.join(DEFAULT_PATHS)}")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"bad argument: --root {args.root} is not a folder", file=sys.stderr)
        return 2
    term_files = args.terms
    if term_files is None:
        default = os.path.join(root, "output", "client-terms.txt")
        term_files = [default] if os.path.exists(default) else []
    raw: list[str] = []
    for tf in term_files:
        if not os.path.isfile(tf):
            print(f"bad argument: terms file not found: {tf}", file=sys.stderr)
            return 2
        raw.extend(read_terms_file(tf))
    raw.extend(read_brief_terms(root))
    terms = clean_terms(raw)
    if not terms:
        print("no client terms: create output/client-terms.txt or a brief.json under output/", file=sys.stderr)
        return 2
    skip_abs = {os.path.normcase(os.path.abspath(tf)) for tf in term_files}
    try:
        if args.paths:
            hits = scan(root, args.paths, terms, skip_abs)
        else:
            hits = scan(root, DEFAULT_PATHS, terms, skip_abs, strict=False)    # a default path may not exist yet
    except ScanError as e:
        print(f"bad argument: {e}", file=sys.stderr)
        return 2
    for h in hits:
        print(h)
    if hits:
        print(f"RESULT: FAIL \u2013 {len(hits)} hits")
        return 1
    print("RESULT: PASS \u2013 0 hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
