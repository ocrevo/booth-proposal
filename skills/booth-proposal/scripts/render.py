"""Booth renders: make concept renders with an image model, lint prompts, place a logo and stamp the draft label.

Renders are concept visualisations, not construction drawings. A concept is addressed as --concept <set>/<concept>;
its renders go to concepts/<set>/<concept>/renders/ and are never overwritten: new files are numbered after the
highest <view>-v<k>.<ext> already there. A graphic the brief asks for (brief.json graphics) is addressed as
--graphic GR1; its artwork goes to graphics/GR1/renders/graphic-v<k>.<ext> the same way. The image model never
paints text, digits or logos: the text goes over the artwork in the deck, the logo is placed with render.py logo. Every image gets three files beside it: <name>.prompt.txt (the exact
prompt sent), <name>.json (sidecar v2: mode, inputs with hashes, outputs, prompt hash, lint result, request record)
and, later, <name>.review.json. Lint runs before every paid call; errors stop the call.

Usage:
  python render.py lint  --mode hero|fix|front|graphic (--prompt FILE | --add SENTENCE) [--concept KEY | --graphic GR]
                         [--area top|bottom|left|right] [--ref F ...] [--json]
  python render.py hero  --concept KEY --prompt FILE [--ref F ...] [--n N]
                         -> hero-v<k>.png, one per candidate; --ref (repeatable) attaches the concept's own
                            reference photos; the call goes to the edit endpoint with --ref, else to generation
  python render.py graphic --graphic GR --prompt FILE --area top|bottom|left|right [--ref F ...] [--candidates N]
                         -> graphics/GR/renders/graphic-v<k>.png, one per candidate; the brief ratio of the graphic
                            gives the size; --area is where the artwork stays empty for the text; --ref (only the
                            product photos of that graphic in brief.json) goes to the edit endpoint
  python render.py fix   (--concept KEY | --graphic GR) --base IMG --add "one correction sentence" [--prompt FILE]
                         [--view V]   -> <view>-v<k>.png, the base render with that one change
  python render.py front --concept KEY --base IMG --prompt FILE
                         -> front-v<k>.png, the front view edited from a render of the concept
  python render.py import FILE (--concept KEY [--view hero] | --graphic GR --area A) [--ref F ...] [--prompt FILE]
                         -> copies an image made elsewhere to the next <view>-v<k>.<ext>; a file with the content of a
                            reference or client file is refused
  python render.py review IMG --reviewer subagent|self|user --verdict pass|fail --premium yes|no
                         (--size-json JSON|FILE for a concept render | --text-area yes|no for a graphic)
                         --marks-json JSON|FILE|- [--scope full|whole] [--notes TEXT]
                         -> <name>.review.json; prints the computed verdict, exit 1 when it is fail
  python render.py logo  IMG --logo FILE --quad "u1,v1 u2,v2 u3,v3 u4,v4" [--blend multiply|normal]
                         -> the next <view>-v<k>.png with the official logo on the panel (blend normal is the
                            default on a graphic); carries the base's review over
  python render.py label IMG --title TEXT [--out PATH]
                         -> a stamped copy (default work/labelled/<name>-label.png) for showing, never for the deck
  python render.py tiles IMG [--grid 3x2]
                         -> work/tiles/<set>/<concept>/<name>/r<R>c<C>.png, 8 % overlap, for the review
                            (a graphic: work/tiles/graphics/<GR>/<name>/; a tall image turns the default grid)
  python render.py sheet --set SET --candidates | --set SET --chosen | --chosen-all | --graphics
                         -> work/sheets/<SET>-candidates.png, <SET>-chosen.png, chosen-all.png or graphics.png,
                            captioned with the concept or graphic id, the file and its review state

Options for hero, graphic, fix and front:
  --project P           the project folder (default .), which must hold brief/
  --model gpt-image-2   --size 1536x1024 (graphic: from its ratio)   --quality high
  --fidelity high|low   sends input_fidelity with any call that has input images; if the model rejects it, the call
                        is retried once without it
  --dry-run             lint, then print the endpoint, fields, input images, prompt head and output names; no call
  --provider openai     PROVIDERS holds each provider's endpoints; only OpenAI's request format is implemented

The API key comes from the environment (OPENAI_API_KEY) or from a .env file in the project folder or a parent
(a line OPENAI_API_KEY=... or openai_key=..., any case); the search stops after a folder holding .git or the home
folder. It is never printed, logged or written. 429, 500, 502 and 503 are retried twice, waiting the server's
Retry-After (at most 120 s), else 20 s. Exit codes: 0 done, 1 lint or source errors, 2 bad invocation or input,
3 no key or the API failed.
HTTP uses the standard library only; import, label and logo need Pillow (logo also numpy).
"""
import argparse
import base64
import json
import math
import mimetypes
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import NamedTuple

import common

PROVIDERS = {
    "openai": {
        "generate": "https://api.openai.com/v1/images/generations",   # JSON body, no input image
        "edit": "https://api.openai.com/v1/images/edits",             # multipart form, input images as image[]
        "image_field": "image[]",
        "model": "gpt-image-2",
        "key_env": "OPENAI_API_KEY",
        "key_names": ("OPENAI_API_KEY", "openai_key"),               # accepted in a .env file, any case
    },
}
RETRY_CODES = (429, 500, 502, 503)
RETRIES = 2          # extra attempts for the codes above
BACKOFF_S = 20
RETRY_AFTER_CAP_S = 120   # the longest Retry-After we honour
TIMEOUT_S = 600      # one high-quality image can take two minutes; n images take longer

FIX_PROMPT = ("Edit this photograph of an exhibition stand. Keep the design, materials, light, camera and people; "
              "change only what this correction asks for: {add}")
FIX_BRIEF = "\n\nOriginal brief for reference:\n{brief}"
GRAPHIC_FIX_PROMPT = ("Edit this flat graphic artwork. Keep the composition, style, colours and the empty area for the "
                      "text; change only what this correction asks for: {add}")
GRAPHIC_SIZES = (("1024x1536", 2 / 3), ("1024x1024", 1.0), ("1536x1024", 3 / 2))   # supported sizes, w/h


class ApiError(Exception):
    """No API key, or the HTTP call failed (code R-API). main() prints it and exits 3."""

    def __init__(self, code, where, message):
        super().__init__(message)
        self.code = code
        self.where = where


# ---------- API key ----------

def key_from_env_file(path, names):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            name, eq, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            if eq and value and name.strip().lower() in [n.lower() for n in names]:
                return value
    return None


def find_key(provider, start):
    """Return (key, where it was found) or (None, None). Only the place is ever shown, never the key.
    Order: the environment variable, then <folder>/.env from start upward. The search stops after a folder that
    holds .git or is the home folder (its own .env is still read), or at the drive root."""
    p = PROVIDERS[provider]
    if os.environ.get(p["key_env"], "").strip():
        return os.environ[p["key_env"]].strip(), "the environment"
    home = common.real(os.path.expanduser("~"))
    folder = os.path.abspath(start)
    while True:
        path = os.path.join(folder, ".env")
        if os.path.isfile(path):
            key = key_from_env_file(path, p["key_names"])
            if key:
                return key, path
        if os.path.exists(os.path.join(folder, ".git")) or common.real(folder) == home:
            return None, None
        parent = os.path.dirname(folder)
        if parent == folder:
            return None, None
        folder = parent


def retry_wait(headers):
    """Seconds to wait before a retry: a numeric Retry-After (at most RETRY_AFTER_CAP_S), else BACKOFF_S."""
    try:
        raw = headers.get("Retry-After") if headers is not None else None
    except AttributeError:
        raw = None
    if raw is not None:
        try:
            value = float(str(raw).strip())
        except ValueError:
            value = None
        if value is not None and value >= 0:
            return float(min(value, RETRY_AFTER_CAP_S))
    return float(BACKOFF_S)


def missing_key(provider, project):
    p = PROVIDERS[provider]
    names = " or ".join(f"{n}=<your key>" for n in p["key_names"])
    return (f"No API key found. Either set the environment variable {p['key_env']}, or add a line {names} "
            f"to a .env file in the project folder ({project.root}) or one of its parents "
            f"(the search stops at a folder with .git and at your home folder).")


# ---------- request ----------

def next_names(out_dir, view, n, ext=".png"):
    """Paths for n new images, numbered after the highest <view>-v<k> of any image extension in out_dir."""
    pat = re.compile(rf"{re.escape(view)}-v(\d+)\.(?:png|jpe?g|webp)", re.IGNORECASE)
    files = os.listdir(out_dir) if os.path.isdir(out_dir) else []
    k = max((int(m.group(1)) for f in files if (m := pat.fullmatch(f))), default=0)
    return [os.path.join(out_dir, f"{view}-v{k + i}{ext}") for i in range(1, n + 1)]


def check_view(view):
    if not re.fullmatch(r"[\w.-]+", view):
        raise UsageError(f"--view must be a plain name such as hero or front, not {view!r}")


def view_of_base(base):
    """The view a fix keeps: the base file's own name (front-v1.png -> front), else hero."""
    m = re.fullmatch(r"(.+)-v\d+", os.path.splitext(os.path.basename(base))[0])
    return m.group(1) if m else "hero"


def size_for_ratio(ratio):
    """The supported request size whose width/height is nearest to a brief ratio such as 2:3 (in log space)."""
    value = common.ratio_value(ratio)
    if value is None:
        raise common.InputError("C-INPUT", "brief/brief.json graphics", f"ratio {ratio!r} must look like 2:3")
    return min(GRAPHIC_SIZES, key=lambda s: abs(math.log(value / s[1])))[0]


def fields_of(owner, *, area=None, ratio=None, base_sidecar=None):
    """The sidecar keys that name the owner of a render: a concept, or a graphic with its area and ratio (copied
    from the base sidecar when there is one)."""
    if not common.is_graphic(owner):
        return {"set": owner.set, "concept": owner.id}
    if base_sidecar is not None:
        area, ratio = base_sidecar.get("area"), base_sidecar.get("ratio")
    return {"set": None, "concept": None, "kind": "graphic", "graphic": owner.id, "area": area, "ratio": ratio}


def ensure_graphic_md(graphic):
    """Create graphics/<GR>/graphic.md (empty front matter: nothing chosen yet) when it is missing."""
    md, _ = common.owner_md(graphic)
    if not os.path.isfile(md):
        os.makedirs(graphic.dir, exist_ok=True)
        with open(md, "w", encoding="utf-8", newline="\n") as f:
            f.write("---\n---\nNotes.\n")


def require_graphics(project):
    """The architecture of the project; C-INPUT when it shows no graphics."""
    arch = common.architecture_for(project)
    if "graphic" not in arch["allowed_kinds"]:
        raise common.InputError(
            "C-INPUT", "brief/brief.json proposal.architecture",
            f"the {arch['id']} architecture shows no graphics (allowed_kinds {', '.join(arch['allowed_kinds'])}); "
            "choose an architecture that does or drop brief.json graphics")
    return arch


def build_request(a, prompt, images, n):
    """(endpoint, fields) for an API mode; nothing is sent here."""
    prov = PROVIDERS[a.provider]
    fields = {"model": a.model or prov["model"], "prompt": prompt, "size": a.size, "quality": a.quality, "n": n}
    if a.fidelity and images:
        fields["input_fidelity"] = a.fidelity
    elif a.fidelity:
        print("note: --fidelity applies to calls with input images; this call has none, so it is not sent")
    return prov["edit" if images else "generate"], fields


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
    for name, path in files:
        mime = mimetypes.guess_type(path)[0] or "image/png"
        with open(path, "rb") as f:
            data = f.read()
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                 f'filename="{os.path.basename(path)}"\r\nContent-Type: {mime}\r\n\r\n').encode()
        body += data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def send(url, key, fields, images, image_field):
    if images:
        body, ctype = multipart(fields, [(image_field, p) for p in images])
    else:
        body, ctype = json.dumps(fields).encode(), "application/json"
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.load(r)


def server_error(e, key):
    """The server's own error message (never the request), with the key masked in case it is echoed."""
    raw = e.read().decode("utf-8", "replace")
    try:
        err = json.loads(raw)["error"]
        text = err["message"] + (f" [{err['code']}]" if err.get("code") else "")
    except (ValueError, KeyError, TypeError):
        text = raw.strip() or e.reason
    return text.replace(key, "***")[:1500], raw


def call(url, key, fields, images, image_field):
    """POST with the retry rules; return (response, seconds, fields actually sent). Raises ApiError R-API."""
    fields, retries = dict(fields), RETRIES
    while True:
        t0 = time.time()
        try:
            return send(url, key, fields, images, image_field), time.time() - t0, fields
        except urllib.error.HTTPError as e:
            msg, raw = server_error(e, key)
            if e.code == 400 and "input_fidelity" in fields and "input_fidelity" in msg + raw:
                print(f"HTTP 400: {msg}\nretrying once without input_fidelity")
                del fields["input_fidelity"]
                continue
            if e.code in RETRY_CODES and retries:
                retries -= 1
                wait = retry_wait(e.headers)
                print(f"HTTP {e.code}: {msg}; retrying in {wait:g} s")
                time.sleep(wait)
                continue
            raise ApiError("R-API", url, f"HTTP {e.code}: {msg}") from None
        except OSError as e:   # no connection, DNS, timeout (URLError is an OSError)
            raise ApiError("R-API", url, f"request failed: {getattr(e, 'reason', e)}") from None


def save(project, owner_fields, mode, res, names, sent, inputs, seconds, lint, meta=None):
    """Write each returned image with its .prompt.txt and sidecar v2; return the image paths.
    owner_fields: fields_of(...), the sidecar keys that name the concept or graphic.
    inputs: [{role, path, sha256}] built before the call. lint: the lint_status record. meta: provider, endpoint."""
    meta = meta or {}
    data = res.get("data") or []
    if not data:
        raise ApiError("R-API", meta.get("endpoint", ""), "the server answered without an image")
    os.makedirs(os.path.dirname(os.path.abspath(names[0])), exist_ok=True)
    usage = res.get("usage", {})
    saved = []
    for path, item in zip(names, data):
        if item.get("b64_json"):
            blob = base64.b64decode(item["b64_json"])
        else:
            with urllib.request.urlopen(item["url"], timeout=TIMEOUT_S) as r:
                blob = r.read()
        with open(path, "wb") as f:
            f.write(blob)
        stem = os.path.splitext(path)[0]
        with open(stem + ".prompt.txt", "w", encoding="utf-8", newline="") as f:   # newline="": the hash must match
            f.write(sent["prompt"])
        api = {"provider": meta.get("provider"), "endpoint": meta.get("endpoint"), "model": sent["model"],
               "size": sent["size"], "quality": sent["quality"], "n": len(names), "usage": usage,
               "seconds": round(seconds, 1)}
        if sent.get("input_fidelity"):
            api["input_fidelity"] = sent["input_fidelity"]
        if item.get("revised_prompt"):
            api["revised_prompt"] = item["revised_prompt"]
        common.write_sidecar(path, {
            "tool": "render.py", "mode": mode, **owner_fields, "inputs": inputs,
            "prompt_sha256": common.sha256_text(sent["prompt"]), "lint": lint, "api": api})
        print(f"saved {project.rel(path)} in {seconds:.0f}s · model {sent['model']} · usage {json.dumps(usage)}")
        saved.append(path)
    if len(data) < len(names):
        print(f"note: asked for {len(names)} images, the server returned {len(data)}")
    return saved


def dry_run(project, mode, a, url, fields, images, inputs, names, findings):
    """Print what a real call would send and save; returns the exit code (1 when a finding is an error)."""
    prompt = fields["prompt"]
    print(f"DRY RUN · {mode} · {a.provider} · nothing is sent")
    print(f"POST {url}  ({'multipart form' if images else 'JSON'})")
    for k, v in fields.items():
        if k != "prompt":
            print(f"  {k}: {v}")
    if inputs:
        for item in inputs:
            print(f"  {item['role']}: {item['path']}")
    else:
        print("  input images: none")
    head = prompt[:200].replace("\r", "").replace("\n", " / ")
    print(f"  prompt: {len(prompt)} characters: {head}{' ...' if len(prompt) > 200 else ''}")
    _, where = find_key(a.provider, project.root)
    print(f"API key: found in {where} (not shown)" if where else "API key: NOT FOUND, a real run would stop here")
    for p in names:
        print(f"would save {project.rel(p)} (+ .prompt.txt, .json)")
    return common.print_findings(findings)


def where_of(project, path):
    """A prompt path as shown in findings: project-relative inside the project, else as given."""
    absolute = os.path.abspath(path)
    return project.rel(absolute) if common.inside(project.root, absolute) else path


def check_base(project, concept, image, mode=None):
    """(chain, findings) for the render that fix, front, logo or label start from: it must be a render of this
    concept (or graphic) with a valid base chain (R-SOURCE). A v1 step ends the chain with a C-LEGACY warning. With
    mode fix, a chain that already holds fix_max fixes adds an R-FIX-MAX warning."""
    rel = project.rel(image)
    if not os.path.isfile(image):
        return [], [common.Finding("R-SOURCE", "error", rel, f"chain: {rel} not found")]
    if not common.inside(os.path.join(concept.dir, "renders"), image):
        if common.owner_of_path(project, image) is None:
            msg = "chain: not a render of any concept"
        else:
            msg = f"chain: {rel} is not a render of {concept.key}"
        return [], [common.Finding("R-SOURCE", "error", rel, msg)]
    chain, finding = common.trace_base_chain(project, image)
    if finding is not None:
        return chain, [finding]
    findings = []
    if common.sidecar_version(common.read_sidecar(project.path(chain[-1]))) == 1:
        findings.append(common.Finding("C-LEGACY", "warn", chain[-1],
                                       "legacy: the base chain ends at an image with an old sidecar"))
    if mode == "fix":
        fixes = sum(1 for step in chain if (common.read_sidecar(project.path(step)) or {}).get("mode") == "fix")
        if fixes >= project.thresholds["fix_max"]:
            findings.append(common.Finding(
                "R-FIX-MAX", "warn", rel,
                f"fix-max: the base chain already has {fixes} fixes (fix_max {project.thresholds['fix_max']}); "
                "a new hero may serve better"))
    return chain, findings


def cmd_generate(a):
    """hero, fix and front: lint, then (unless --dry-run) one paid call; returns the exit code."""
    mode = a.cmd
    project = common.find_project(a.project)
    graphic = bool(getattr(a, "graphic", None))
    if graphic:
        require_graphics(project)
        concept = common.graphic_ref(project, a.graphic)
        if a.view:
            raise UsageError("--view is not used with --graphic")
    else:
        concept = common.concept_ref(project, a.concept)
        a.size = a.size or "1536x1024"
    renders = os.path.join(concept.dir, "renders")
    n = 1
    if mode == "hero":
        n = a.n if a.n is not None else int(project.thresholds["candidates_per_concept"])
        if not 1 <= n <= 10:
            raise UsageError("--n must be between 1 and 10")
    view, text, extra = mode, None, None
    if mode == "fix":
        add = a.add.strip()
        if not add:
            raise UsageError("--add is empty")
        view = a.view or view_of_base(a.base)
        prompt = (GRAPHIC_FIX_PROMPT if graphic else FIX_PROMPT).format(add=add)
        if a.prompt:
            extra = read_prompt_file(a.prompt)
            prompt += FIX_BRIEF.format(brief=extra.strip())
    else:
        text = read_prompt_file(a.prompt)
        prompt = text.strip()
    check_view(view)
    base_findings, lint_findings, inputs, images, base_sc = [], [], [], [], None
    if mode == "hero":
        images = list(a.ref or [])
        for ref in images:
            if not os.path.isfile(ref):
                raise UsageError(f"reference image not found: {ref}")
        inputs = [{"role": "ref", "path": project.rel(os.path.abspath(ref)), "sha256": common.sha256_file(ref)}
                  for ref in images]
        lint_findings = lint_prompt(project, "hero", text, where_of(project, a.prompt), concept=concept, refs=images)
    else:
        _, base_findings = check_base(project, concept, a.base, mode)
        if not any(f.level == "error" for f in base_findings):
            images = [a.base]
            inputs = [{"role": "base", "path": project.rel(os.path.abspath(a.base)),
                       "sha256": common.sha256_file(a.base)}]
            base_sc = common.read_sidecar(a.base)
        if mode == "front":
            lint_findings = lint_prompt(project, "front", text, where_of(project, a.prompt), concept=concept)
        elif graphic:
            lint_findings = lint_prompt(project, "fix", a.add, "--add")
            if extra is not None:
                lint_findings += lint_prompt(project, "graphic", extra, where_of(project, a.prompt), graphic=concept,
                                             area=(base_sc or {}).get("area"))
        else:
            lint_findings = lint_prompt(project, "fix", a.add, "--add", concept=concept)
            if extra is not None:
                lint_findings += lint_prompt(project, "hero", extra, where_of(project, a.prompt), concept=concept)
    findings = base_findings + lint_findings
    if a.dry_run and any(f.level == "error" for f in base_findings):
        common.print_findings(findings)       # no request block: it would show a call without its base image
        return 1
    if graphic:       # a fix of a graphic keeps the ratio the base was made for
        ratio = (base_sc or {}).get("ratio")
        if common.ratio_value(ratio) is None:
            ratio = (common.graphic_item(project.brief, concept.id) or {}).get("ratio")
        a.size = a.size or size_for_ratio(ratio)
    url, fields = build_request(a, prompt, images, n)
    names = next_names(renders, view, n)
    if a.dry_run:
        return dry_run(project, mode, a, url, fields, images, inputs, names, findings)
    if findings and common.print_findings(findings):
        return 1
    key, _ = find_key(a.provider, project.root)
    if not key:
        raise ApiError("R-API", PROVIDERS[a.provider]["key_env"], missing_key(a.provider, project))
    print(f"{mode}: {len(names)} image(s) from {url} · model {fields['model']} · {a.size} · {a.quality}")
    res, seconds, sent = call(url, key, fields, images, PROVIDERS[a.provider]["image_field"])
    saved = save(project, fields_of(concept, base_sidecar=base_sc), mode, res, names, sent, inputs, seconds,
                 lint_status(lint_findings), {"provider": a.provider, "endpoint": url})
    return 0 if saved else 1


def cmd_graphic(a):
    """graphic: lint, then (unless --dry-run) one paid call for the artwork of a brief graphic; returns the exit code."""
    project = common.find_project(a.project)
    require_graphics(project)
    g = common.graphic_ref(project, a.graphic)
    ratio = (common.graphic_item(project.brief, g.id) or {}).get("ratio")
    if common.ratio_value(ratio) is None:
        raise common.InputError("C-INPUT", "brief/brief.json graphics", f"{g.id} has no usable ratio; run gates.py brief")
    n = a.candidates if a.candidates is not None else int(project.thresholds["candidates_per_concept"])
    if not 1 <= n <= 10:
        raise UsageError("--candidates must be between 1 and 10")
    text = read_prompt_file(a.prompt)
    prompt = text.strip()
    refs = list(a.ref or [])
    for ref in refs:
        if not os.path.isfile(ref):
            raise UsageError(f"reference image not found: {ref}")
    inputs = [{"role": "ref", "path": project.rel(os.path.abspath(ref)), "sha256": common.sha256_file(ref)}
              for ref in refs]
    findings = lint_prompt(project, "graphic", text, where_of(project, a.prompt), graphic=g, refs=refs, area=a.area)
    a.size = a.size or size_for_ratio(ratio)
    url, fields = build_request(a, prompt, refs, n)
    names = next_names(os.path.join(g.dir, "renders"), "graphic", n)
    if a.dry_run:
        return dry_run(project, "graphic", a, url, fields, refs, inputs, names, findings)
    if findings and common.print_findings(findings):
        return 1
    key, _ = find_key(a.provider, project.root)
    if not key:
        raise ApiError("R-API", PROVIDERS[a.provider]["key_env"], missing_key(a.provider, project))
    print(f"graphic: {len(names)} image(s) from {url} \u00b7 model {fields['model']} \u00b7 {a.size} \u00b7 {a.quality}")
    res, seconds, sent = call(url, key, fields, refs, PROVIDERS[a.provider]["image_field"])
    saved = save(project, fields_of(g, area=a.area, ratio=ratio), "graphic", res, names, sent, inputs, seconds,
                 lint_status(findings), {"provider": a.provider, "endpoint": url})
    ensure_graphic_md(g)
    return 0 if saved else 1


# ---------- label and logo (Pillow) ----------

def save_image(im, out, alpha):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if not alpha or out.lower().endswith((".jpg", ".jpeg")):
        im = im.convert("RGB")
    im.save(out)


def label(image, text, out, font_path=None):
    """Stamp text on a semi-transparent dark strip in the bottom-right corner. font_path None = Pillow's own font."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(image)
    W, H = im.size

    def font_at(size):
        if font_path:
            return ImageFont.truetype(font_path, size)
        try:
            return ImageFont.load_default(size)      # Pillow >= 10.1 with FreeType
        except TypeError:
            return ImageFont.load_default()

    size = max(12, round(W / 90))
    font = font_at(size)
    if not font_path:                                # Pillow's own fonts have no en dash; the bitmap one only Latin-1
        text = text.replace("\u2013", "-")
        if not isinstance(font, ImageFont.FreeTypeFont):
            text = text.encode("latin-1", "replace").decode("latin-1")
    l, t, r, b = font.getbbox(text)
    if r - l > 0.9 * W:                              # a long title on a small image: shrink to fit
        size = max(8, int(size * 0.9 * W / (r - l)))
        font = font_at(size)
        l, t, r, b = font.getbbox(text)
    padx, pady = round(size * 0.9), round(size * 0.6)
    x0, y0 = W - (r - l) - 2 * padx, H - (b - t) - 2 * pady
    strip = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    d.rectangle([x0, y0, W, H], fill=(16, 18, 22, 165))
    d.text((x0 + padx - l, y0 + pady - t), text, font=font, fill=(255, 255, 255, 240))
    alpha = "A" in im.getbands() or "transparency" in im.info
    save_image(Image.alpha_composite(im.convert("RGBA"), strip), out, alpha)


def parse_quad(text):
    try:
        pts = [tuple(float(v) for v in p.split(",")) for p in text.replace(";", " ").split()]
    except ValueError:
        pts = []
    if len(pts) != 4 or any(len(p) != 2 for p in pts):
        raise UsageError('--quad needs four pixel corners "u1,v1 u2,v2 u3,v3 u4,v4": '
                         "the logo's top-left, top-right, bottom-right, bottom-left")
    return pts


def perspective_coeffs(dst, src):
    """The 8 coefficients of Pillow's PERSPECTIVE transform, which maps each output point (dst) back to the input
    (src): u = (a x + b y + c) / (g x + h y + 1), v = (d x + e y + f) / (g x + h y + 1)."""
    import numpy as np
    A, rhs = [], []
    for (x, y), (u, v) in zip(dst, src):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        rhs += [u, v]
    try:
        return np.linalg.solve(np.array(A, float), np.array(rhs, float)).tolist()
    except np.linalg.LinAlgError:
        raise UsageError("--quad is degenerate: three corners lie on one line") from None


def place_logo(image, logo_path, quad, out, blend="multiply", ss=4):
    """Warp the logo onto the quad and blend it in. The warp runs at ss times the resolution inside the quad's
    bounding box and is then averaged down, so the edges are anti-aliased."""
    import numpy as np
    from PIL import Image
    im = Image.open(image)
    logo = Image.open(logo_path).convert("RGBA").convert("RGBa")   # premultiplied: no dark fringe at the edges
    # shrink a large logo first: the transform samples, it does not average
    tw = max(math.dist(quad[0], quad[1]), math.dist(quad[3], quad[2])) * ss
    th = max(math.dist(quad[0], quad[3]), math.dist(quad[1], quad[2])) * ss
    if logo.width > tw or logo.height > th:
        logo = logo.resize((max(1, round(min(logo.width, tw))), max(1, round(min(logo.height, th)))), Image.LANCZOS)
    x0, y0 = math.floor(min(p[0] for p in quad)), math.floor(min(p[1] for p in quad))
    bw, bh = math.ceil(max(p[0] for p in quad)) - x0, math.ceil(max(p[1] for p in quad)) - y0
    dst = [((x - x0) * ss, (y - y0) * ss) for x, y in quad]
    src = [(0, 0), (logo.width, 0), (logo.width, logo.height), (0, logo.height)]
    patch = logo.transform((bw * ss, bh * ss), Image.PERSPECTIVE, perspective_coeffs(dst, src), Image.BICUBIC)
    layer = Image.new("RGBa", im.size, (0, 0, 0, 0))
    layer.paste(patch.resize((bw, bh), Image.BOX), (x0, y0))
    lg = np.asarray(layer.convert("RGBA"), np.float32)
    base = np.asarray(im.convert("RGB"), np.float32)
    a = lg[..., 3:4] / 255
    over = base * lg[..., :3] / 255 if blend == "multiply" else lg[..., :3]
    res = Image.fromarray(np.clip(base * (1 - a) + over * a + 0.5, 0, 255).astype(np.uint8), "RGB")
    alpha = "A" in im.getbands()
    if alpha:
        res.putalpha(im.getchannel("A"))
    save_image(res, out, alpha)


# ---------- lint ----------

FIXED_PATH = os.path.join(common.SKILL_DIR, "assets", "prompts", "fixed.json")
LINT_PATH = os.path.join(common.SKILL_DIR, "assets", "prompts", "lint.json")
QUOTES = "\"\u201c\u201d\u00ab\u00bb\u300c\u300d\u300e\u300f`"
APOSTROPHES = "'\u2018\u2019"


def quote_char(text):
    """The first quote mark in text, or "": a QUOTES char, or an APOSTROPHES char not between two letters."""
    for i, ch in enumerate(text):
        if ch in QUOTES or (ch in APOSTROPHES and not (0 < i < len(text) - 1 and text[i - 1].isalpha()
                                                       and text[i + 1].isalpha())):
            return ch
    return ""


HEADERS = (("idea", ("Idea \u2013", "Idea -")), ("colours", ("Brand colours:", "Brand colors:")),
           ("size", ("Size:",)), ("essentials", ("Essentials:",)))
GRAPHIC_HEADERS = (("graphic", ("Graphic \u2013", "Graphic -")), ("colours", ("Brand colours:", "Brand colors:")),
                   ("composition", ("Composition:",)), ("subject", ("Subject:",)))
FIXED_KEYS = ("reference", "logo_panel", "no_lettering", "do_not_copy", "graphic_no_text", "graphic_text_area",
              "graphic_ref")
LINT_MODES = ("hero", "fix", "front", "graphic")
GRAPHIC_PAINT_BLOCKS = ("graphic", "subject")      # the blocks that describe what is painted (not the empty area)
FREE_BLOCKS = {"hero": ("idea", "essentials", "other"), "graphic": ("graphic", "composition", "subject", "other")}


class UsageError(Exception):
    """A bad invocation without a contract code; main() turns it into ap.error (exit 2)."""


class PromptLine(NamedTuple):
    no: int
    text: str
    block: str   # idea|colours|size|essentials|fixed|blank|other (graphic prompts: graphic|composition|subject)


def load_prompt_data():
    """(fixed sentences, lint word lists); a missing or invalid file is C-INPUT."""
    fixed = common.read_json(FIXED_PATH)
    for key in FIXED_KEYS:
        if not isinstance(fixed.get(key), str) or not fixed[key].strip():
            raise common.InputError("C-INPUT", FIXED_PATH, f"{key}: expected a non-empty string")
    data = common.read_json(LINT_PATH)
    for key in ("timeline_words", "logo_text_phrases", "one_per_patterns", "text_area_words", "graphic_text_phrases",
                "area_filled_words"):
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            raise common.InputError("C-INPUT", LINT_PATH, f"{key}: expected a list of non-empty strings")
    areas = data.get("area_words")
    if not isinstance(areas, dict) or sorted(areas) != sorted(common.GRAPHIC_AREAS):
        raise common.InputError("C-INPUT", LINT_PATH,
                                f"area_words: expected an object with the keys {', '.join(common.GRAPHIC_AREAS)}")
    for key, value in areas.items():
        if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
            raise common.InputError("C-INPUT", LINT_PATH, f"area_words.{key}: expected a list of non-empty strings")
    for pattern in data["one_per_patterns"]:
        try:
            re.compile(pattern)
        except re.error as e:
            raise common.InputError("C-INPUT", LINT_PATH, f"one_per_patterns: bad regex {pattern!r}: {e}") from None
    return fixed, data


def collapse(s):
    return " ".join(s.split())


def _header_of(stripped, headers=HEADERS):
    """(block name, prefix) when the stripped line starts with a block header, else (None, None)."""
    for name, prefixes in headers:
        for prefix in prefixes:
            if stripped.startswith(prefix):
                return name, prefix
    return None, None


def _scan(text, fixed):
    """Classify every line and note which blocks are present: (list[PromptLine], info)."""
    fixed_lines = {collapse(v) for v in fixed.values() if isinstance(v, str)}
    info = {"idea": None, "colours": False, "size": False, "essentials": False}   # idea: (no, stripped, prefix)
    out = []
    current = None       # an open idea or essentials block
    size_left = 0        # non-blank lines still to take into the Size block
    for no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            out.append(PromptLine(no, line, "blank"))
            current = None
            continue
        is_fixed = collapse(line) in fixed_lines
        header, prefix = (None, None) if is_fixed else _header_of(stripped)
        if size_left and header is None:
            out.append(PromptLine(no, line, "fixed" if is_fixed else "size"))
            size_left -= 1
            if not size_left:
                info["size"] = True
            continue
        size_left = 0     # a header among the Size lines ends the block early: Size stays incomplete
        if is_fixed:
            out.append(PromptLine(no, line, "fixed"))
        elif header == "idea":
            current = "idea"
            if info["idea"] is None:
                info["idea"] = (no, stripped, prefix)
            out.append(PromptLine(no, line, "idea"))
        elif header == "colours":
            current = None
            info["colours"] = True
            out.append(PromptLine(no, line, "colours"))
        elif header == "size":
            current = None
            size_left = 3
            out.append(PromptLine(no, line, "size"))
        elif header == "essentials":
            current = "essentials"
            info["essentials"] = True
            out.append(PromptLine(no, line, "essentials"))
        else:
            out.append(PromptLine(no, line, current or "other"))
    return out, info


def _scan_graphic(text, fixed):
    """Classify every line of a graphic prompt: (list[PromptLine], info). A blank line ends an open block; a fixed
    line does not. The Graphic, Composition and Subject headers open a block that runs to the next blank line or
    header (text after the colon belongs to it); the colours header is one line."""
    by_text = {collapse(v): k for k, v in fixed.items() if isinstance(v, str)}
    info = {"graphic": None, "colours": False, "composition": False, "subject": False, "fixed": set()}
    out = []
    current = None
    for no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            out.append(PromptLine(no, line, "blank"))
            current = None
            continue
        key = by_text.get(collapse(line))
        if key is not None:
            info["fixed"].add(key)
            out.append(PromptLine(no, line, "fixed"))
            continue
        header, prefix = _header_of(stripped, GRAPHIC_HEADERS)
        if header == "colours":
            current = None
            info["colours"] = True
            out.append(PromptLine(no, line, "colours"))
        elif header is not None:
            current = header
            if header == "graphic":
                if info["graphic"] is None:
                    info["graphic"] = (no, stripped, prefix)
            else:
                info[header] = True
            out.append(PromptLine(no, line, header))
        else:
            out.append(PromptLine(no, line, current or "other"))
    return out, info


def classify(text, fixed):
    return _scan(text, fixed)[0]


def _ban(where, message, no=None):
    return common.Finding("L-BAN", "error", f"{where}:{no}" if no else where, message)


def lint_prompt(project, mode, text, where, *, concept=None, refs=(), graphic=None, area=None):
    """Lint one prompt text; returns findings (no files, no network). where: project-relative prompt path or --add.
    graphic and area (the side the artwork keeps empty) belong to mode graphic."""
    if mode not in LINT_MODES:
        raise ValueError(f"unknown lint mode {mode!r}")
    fixed, data = load_prompt_data()
    if mode == "graphic":
        lines, info = _scan_graphic(text, fixed)
    else:
        lines, info = _scan(text, fixed)
    if mode not in ("hero", "graphic"):   # fix and front texts have no blocks: every non-fixed line is free text
        lines = [pl if pl.block in ("fixed", "blank") else pl._replace(block="other") for pl in lines]
    free = FREE_BLOCKS.get(mode, FREE_BLOCKS["hero"])
    client = project.brief.get("client") if isinstance(project.brief.get("client"), dict) else {}
    terms = []
    for term in list(client.get("names") or []) + list(project.brief.get("protected_terms") or []):
        if isinstance(term, str) and term.strip() and term not in terms:
            terms.append(term)
    one_per = [re.compile(p, re.I) for p in data["one_per_patterns"]]
    out = []
    for pl in lines:
        if pl.block == "blank":
            continue
        line = pl.text
        # corner brackets are CJK-range characters but belong to the quote rule: they are not counted twice
        cjk = [c for c in line if c not in QUOTES and common.is_cjk(c)]
        if cjk:
            ch = cjk[0]
            out.append(_ban(where, f"cjk: a CJK character (U+{ord(ch):04X}) in the prompt; write English only", pl.no))
        if pl.block == "fixed":
            continue
        for term in terms:
            if common.find_term(term, line):
                out.append(_ban(where, f'client: "{term}" is a client or protected name; leave it out', pl.no))
        ch = quote_char(line)
        if ch:
            out.append(_ban(where, f"quote: a quote mark ({ch}) in a free-text block", pl.no))
        if pl.block not in free:
            continue
        m = re.search(r"\S*[0-9]\S*", line)
        if m:
            out.append(_ban(where, f'digit: "{m.group(0)}" in free text; write numbers as words', pl.no))
        for rx in one_per:
            m = rx.search(line)
            if m:
                out.append(_ban(where, f'one-per: "{m.group(0)}" asks for one object per fact', pl.no))
        flat = collapse(line)
        for word in data["timeline_words"]:
            if common.find_term(word, flat):
                out.append(_ban(where, f'timeline: "{word}" asks for a timeline or dates', pl.no))
        for phrase in data["logo_text_phrases"]:
            if common.find_term(phrase, flat):
                out.append(_ban(where, f'logo-text: "{phrase}" asks the image model to paint a logo or text', pl.no))
        if mode == "graphic" and pl.block in GRAPHIC_PAINT_BLOCKS:
            for phrase in data["graphic_text_phrases"]:
                if common.find_term(phrase, flat):
                    out.append(_ban(where, f'graphic-text: "{phrase}" asks the image model to paint text; the text '
                                           "goes over the artwork in the deck (the Composition block may say the "
                                           "area is for the title)", pl.no))
    if mode == "hero":
        idea_ok = False
        if info["idea"]:
            no, stripped, prefix = info["idea"]
            name, colon, _ = stripped[len(prefix):].partition(":")
            idea_ok = bool(colon)
            if colon and quote_char(name):
                out.append(_ban(where, "name-quoted: the concept name in the Idea line carries a quote mark", no))
        missing = []
        if not idea_ok:
            missing.append(("idea", 'no line "Idea - <name>: <idea>" (the colon after the name is required)'))
        if not info["colours"]:
            missing.append(("colours", 'no "Brand colours:" line'))
        if not info["size"]:
            missing.append(("size", 'no "Size:" line followed by three non-empty lines'))
        if not info["essentials"]:
            missing.append(("essentials", 'no "Essentials:" block'))
        out += [common.Finding("L-BLOCKS", "error", where, f"{name}: {msg}") for name, msg in missing]
        out += _lint_refs(project, concept, refs)
    if mode == "graphic":
        out += _lint_graphic(project, where, info, lines, data, area, refs, graphic)
    words = len(text.split())
    if words > project.thresholds["prompt_words_warn"]:
        out.append(common.Finding("L-WORDS", "warn", where,
                                  f"{words} words (guide {project.thresholds['prompt_words_warn']})"))
    return out


def _lint_graphic(project, where, info, lines, data, area, refs, graphic):
    """L-BLOCKS and L-REF findings of a graphic prompt (the per-line bans are made by lint_prompt)."""
    out = []
    missing = []
    name_ok = False
    if info["graphic"]:
        no, stripped, prefix = info["graphic"]
        name, colon, _ = stripped[len(prefix):].partition(":")
        name_ok = bool(colon)
        if colon and quote_char(name):
            out.append(_ban(where, "name-quoted: the graphic name in the Graphic line carries a quote mark", no))
    if not name_ok:
        missing.append(("graphic", 'no line "Graphic - <name>: <what it is for>" (the colon after the name is '
                                   "required)"))
    if not info["colours"]:
        missing.append(("colours", 'no "Brand colours:" line'))
    if not info["composition"]:
        missing.append(("composition", 'no "Composition:" block'))
    words = data["area_words"][area] if area else [w for k in common.GRAPHIC_AREAS for w in data["area_words"][k]]
    reserved = any(any(common.find_term(t, pl.text) for t in data["text_area_words"])
                   and any(common.find_term(w, pl.text) for w in words)
                   and not any(common.find_term(w, pl.text) for w in data["area_filled_words"])
                   for pl in lines if pl.block == "composition")
    if not reserved:
        place = f"the {area}" if area else "a named place"
        missing.append(("text-area", f"the Composition block does not reserve the empty area for the text at "
                                     f'{place} (for example "the upper third is kept empty"; a line that says the subject fills or covers '
                                     "it does not count)"))
    if not info["subject"]:
        missing.append(("subject", 'no "Subject:" block'))
    sentences = (("no-text", "graphic_no_text", True, ""), ("area-sentence", "graphic_text_area", True, ""),
                 ("ref-sentence", "graphic_ref", bool(refs), " (photos are attached)"))
    for name, key, needed, note in sentences:
        if needed and key not in info["fixed"]:
            missing.append((name, f"the fixed sentence {key} of assets/prompts/fixed.json is missing{note}"))
    out += [common.Finding("L-BLOCKS", "error", where, f"{name}: {msg}") for name, msg in missing]
    return out + _lint_refs(project, None, refs, graphic)


def _lint_refs(project, concept, refs, graphic=None):
    out = []
    stamped = None
    if concept is not None and refs:
        block = project.brief.get("references")
        for entry in (block.get("sets") if isinstance(block, dict) else None) or []:
            if isinstance(entry, dict) and entry.get("id") == concept.set:
                stamped = {common.real(project.path(f["path"])) for f in entry.get("files") or []
                           if isinstance(f, dict) and isinstance(f.get("path"), str)}
    concepts_dir = project.path("concepts")
    graphics_dir = project.path(common.GRAPHICS_FOLDER)
    own = None
    if graphic is not None:
        own = {common.real(project.path(*r.split("/"))) for r in
               (common.graphic_item(project.brief, graphic.id) or {}).get("refs") or [] if isinstance(r, str)}
    for ref in refs:
        path = os.path.abspath(ref)
        shown = project.rel(path)
        if own is not None and common.real(path) not in own:
            out.append(common.Finding("L-REF", "error", shown,
                                      f"graphic: not a file of the refs of {graphic.id} in brief.json"))
        if concept is not None and (stamped is None or common.real(path) not in stamped):
            out.append(common.Finding(
                "L-REF", "error", shown,
                f"set: not a file of the stamped reference set {concept.set}"
                + ("" if stamped is not None else "; the set is not stamped, run gates.py brief --stamp")))
        for folder, what in ((concepts_dir, "concept"), (graphics_dir, "graphic")):
            if common.inside(folder, path) and os.path.isfile(common.sidecar_path(path)):
                out.append(common.Finding("L-REF", "error", shown,
                                          f"render: a render of a {what} is never a reference photo"))
    return out


def lint_status(findings):
    """The sidecar lint record: {"status": "fail"|"warn"|"pass", "codes": [...]}; None when there was no prompt."""
    if findings is None:
        return None
    status = "fail" if any(f.level == "error" for f in findings) else \
        "warn" if any(f.level == "warn" for f in findings) else "pass"
    return {"status": status, "codes": sorted({f.code for f in findings})}


def read_prompt_file(path):
    if not os.path.isfile(path):
        raise UsageError(f"prompt file not found: {path}")
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    if not text.strip():
        raise UsageError(f"prompt file is empty: {path}")
    return text


def cmd_lint(a):
    project = common.find_project(a.project)
    if a.add is not None and a.mode != "fix":
        raise UsageError("--add goes only with --mode fix")
    if a.concept and a.graphic:
        raise UsageError("give --concept or --graphic, not both")
    if a.ref and not (a.concept or a.graphic):
        raise UsageError("--ref needs --concept or --graphic")
    if a.area and a.mode != "graphic":
        raise UsageError("--area goes only with --mode graphic")
    if a.concept and a.mode == "graphic":
        raise UsageError("--concept does not go with --mode graphic; use --graphic")
    if a.graphic and a.mode != "graphic":
        raise UsageError("--graphic goes only with --mode graphic")
    concept = common.concept_ref(project, a.concept) if a.concept else None
    graphic = common.graphic_ref(project, a.graphic) if a.graphic else None
    if a.add is not None:
        if not a.add.strip():
            raise UsageError("--add is empty")
        text, where = a.add, "--add"
    else:
        text = read_prompt_file(a.prompt)
        path = os.path.abspath(a.prompt)
        where = project.rel(path) if common.inside(project.root, path) else a.prompt
    findings = lint_prompt(project, a.mode, text, where, concept=concept, refs=a.ref or (), graphic=graphic,
                           area=a.area)
    return common.print_findings(findings, as_json=a.json)


# ---------- import ----------

IMPORT_EXT = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}


def image_ext(path):
    """The extension an imported file gets (.png, .jpg or .webp), from its real format; anything else is C-INPUT."""
    from PIL import Image
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:       # verify() leaves the file unusable: reopen
            fmt = im.format
            im.load()
    except Exception as e:                 # Pillow raises OSError, SyntaxError, ValueError ... for broken files
        raise common.InputError("C-INPUT", path, f"not a readable png, jpg or webp image ({e})") from None
    if fmt not in IMPORT_EXT:
        raise common.InputError("C-INPUT", path, f"image format {fmt} is not png, jpg or webp")
    return IMPORT_EXT[fmt]


def cmd_import(a):
    """Copy an image made elsewhere into the renders/ of a concept or graphic with a sidecar; returns the exit code."""
    project = common.find_project(a.project)
    graphic = bool(a.graphic)
    if graphic:
        if a.view is not None:
            raise UsageError("--view is not used with --graphic (its images are named graphic-v<k>)")
        if not a.area:
            raise UsageError("--area is required with --graphic (the side the artwork keeps empty for the text)")
        require_graphics(project)
        concept = common.graphic_ref(project, a.graphic)
        view = "graphic"
    else:
        if a.area:
            raise UsageError("--area goes only with --graphic")
        concept = common.concept_ref(project, a.concept)
        view = a.view or "hero"
        check_view(view)
    src = os.path.abspath(a.file)
    if not os.path.isfile(src):
        raise common.InputError("C-INPUT", a.file, "file not found")
    ext = image_ext(src)
    forbidden = common.forbidden_hashes(project)
    digest = common.sha256_file(src)
    if digest in forbidden:
        return common.print_findings([common.Finding("R-SOURCE", "error", project.rel(src),
                                                     f"forbidden: same content as {forbidden[digest]}")])
    refs = list(a.ref or [])
    for ref in refs:
        if not os.path.isfile(ref):
            raise UsageError(f"reference image not found: {ref}")
    inputs = [{"role": "ref", "path": project.rel(os.path.abspath(ref)), "sha256": common.sha256_file(ref)}
              for ref in refs]
    sent, lint = None, None
    if a.prompt:
        text = read_prompt_file(a.prompt)
        if graphic:
            findings = lint_prompt(project, "graphic", text, where_of(project, a.prompt), graphic=concept, refs=refs,
                                   area=a.area)
        else:
            findings = lint_prompt(project, "hero", text, where_of(project, a.prompt), concept=concept, refs=refs)
        print("lint (an import is not blocked by it):")
        common.print_findings(findings)
        sent, lint = text.strip(), lint_status(findings)
    renders = os.path.join(concept.dir, "renders")
    dest = next_names(renders, view, 1, ext)[0]
    os.makedirs(renders, exist_ok=True)
    shutil.copyfile(src, dest)
    if sent is not None:
        with open(os.path.splitext(dest)[0] + ".prompt.txt", "w", encoding="utf-8", newline="") as f:
            f.write(sent)
    owner = fields_of(concept, area=a.area, ratio=(common.graphic_item(project.brief, concept.id) or {}).get("ratio")) \
        if graphic else fields_of(concept)
    common.write_sidecar(dest, {
        "tool": "render.py", "mode": "import", **owner, "inputs": inputs,
        "prompt_sha256": common.sha256_text(sent) if sent is not None else None, "lint": lint, "api": None})
    if graphic:
        ensure_graphic_md(concept)
    print(f"imported {project.rel(dest)}; review it before choosing (render.py review)")
    return 0


# ---------- review ----------

SCOPES = ("full", "whole")
MARK_KEYS = ("type", "where", "note")
TILE_RE = re.compile(r"r\d+c\d+")
DIMS = (("w", "width"), ("d", "depth"), ("h", "max_height"))   # review key, brief.booth key


def load_json_arg(value, what):
    """A JSON value given inline, as the path of a file, or as - for stdin. Failure is C-INPUT."""
    try:
        if value == "-":
            text = sys.stdin.read()
        elif os.path.isfile(value):
            with open(value, encoding="utf-8-sig") as f:
                text = f.read()
        else:
            text = value
    except (OSError, ValueError) as e:
        raise common.InputError("C-INPUT", what, f"cannot read {value!r}: {e}") from None
    try:
        return json.loads(text)
    except ValueError as e:
        raise common.InputError("C-INPUT", what, f"not valid JSON: {e}") from None


def parse_marks(value):
    data = load_json_arg(value, "--marks-json")
    if not isinstance(data, list):
        raise common.InputError("C-INPUT", "--marks-json", "expected a list of {type, where, note} objects")
    marks = []
    for i, m in enumerate(data):
        where = f"marks[{i}]"
        if not isinstance(m, dict):
            raise common.InputError("C-INPUT", where, "expected an object with type, where and note")
        for key in MARK_KEYS:
            if not isinstance(m.get(key), str):
                raise common.InputError("C-INPUT", f"{where}.{key}", "expected a string")
        extra = sorted(set(m) - set(MARK_KEYS))
        if extra:
            raise common.InputError("C-INPUT", f"{where}.{extra[0]}", "unknown key; a mark has type, where and note")
        if m["type"] not in common.MARK_TYPES:
            raise common.InputError("C-INPUT", f"{where}.type",
                                    f"unknown mark type {m['type']!r}; one of {', '.join(common.MARK_TYPES)}")
        if m["where"] != "whole" and not TILE_RE.fullmatch(m["where"]):
            raise common.InputError("C-INPUT", f"{where}.where", 'expected a tile name such as r1c3, or "whole"')
        marks.append({key: m[key] for key in MARK_KEYS})
    return marks


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _dims(data, what):
    if not isinstance(data, dict):
        raise common.InputError("C-INPUT", what, "expected an object with w, d and h")
    for key, _ in DIMS:
        if not _positive(data.get(key)):
            raise common.InputError("C-INPUT", f"{what}.{key}", "expected a number above 0 (in person-heights)")
    return {key: data[key] for key, _ in DIMS}


def expected_dims(project):
    """The booth in person-heights: metres of width, depth and max_height divided by person_height_m."""
    booth = project.brief.get("booth")
    where = "brief/brief.json booth"
    if not isinstance(booth, dict):
        raise common.InputError("C-INPUT", where, "no booth; give size.expected or add booth to brief.json")
    if booth.get("unit") not in ("m", "ft"):
        raise common.InputError("C-INPUT", f"{where}.unit", 'expected "m" or "ft"')
    out = {}
    for key, name in DIMS:
        if not _positive(booth.get(name)):
            raise common.InputError("C-INPUT", f"{where}.{name}", "expected a number above 0")
        out[key] = round(common.to_m(booth[name], booth["unit"]) / project.thresholds["person_height_m"], 3)
    return out


def parse_size(project, value):
    """The review size block: expected, observed, deviation and within (C 2.5)."""
    data = load_json_arg(value, "--size-json")
    if not isinstance(data, dict):
        raise common.InputError("C-INPUT", "--size-json", 'expected an object like {"observed": {"w": 4.5, ...}}')
    observed = _dims(data.get("observed"), "--size-json observed")
    expected = _dims(data["expected"], "--size-json expected") if data.get("expected") is not None \
        else expected_dims(project)
    # w and d: two-sided, abs(obs-exp)/exp. h: signed (obs-exp)/exp, and only a stand ABOVE the cap counts
    # (booth.max_height is a cap, so a lower stand is fine).
    deviation = {key: round((observed[key] - expected[key]) / expected[key], 3) if key == "h"
                 else round(abs(observed[key] - expected[key]) / expected[key], 3) for key, _ in DIMS}
    tol = project.thresholds["size_tolerance"]
    return {"expected": expected, "observed": observed, "deviation": deviation,
            "within": not size_off(deviation, tol)}


def size_off(deviation, tol):
    """The dimensions outside tolerance: w and d two-sided, h only when above (signed deviation > tol)."""
    return [key for key, _ in DIMS if deviation[key] > tol]


def logo_mark_allowed(project, image):
    """A composited_logo mark counts only on a render made by render.py logo with a current, official logo file."""
    sc = common.read_sidecar(image)
    if common.sidecar_version(sc) != 2 or sc.get("mode") != "logo":
        return False
    logos = [i for i in sc.get("inputs") or [] if isinstance(i, dict) and i.get("role") == "logo"]
    if len(logos) != 1 or not isinstance(logos[0].get("path"), str):
        return False
    try:
        current = common.sha256_file(project.path(logos[0]["path"]))
    except OSError:
        return False
    return current == logos[0].get("sha256") and current in common.logo_hashes(project) \
        and current not in common.forbidden_hashes(project)


def compute_verdict(project, image, review):
    """(pass|fail, reasons): pass iff the reviewer said pass, no fail-class mark, size within and premium. A graphic
    has no size gate; its pseudo_text fails (it is read up close) and its text area must be clean and usable."""
    reasons = []
    tol = project.thresholds["size_tolerance"]
    graphic = review.get("kind") == "graphic"
    if review.get("reviewer_verdict") != "pass":
        reasons.append("the reviewer's verdict is fail")
    allowed = None
    for m in review.get("marks") or []:
        kind = common.MARK_TYPES.get(m["type"])
        if kind == "fail":
            reasons.append(f"{m['type']} at {m['where']}")
        elif kind == "allow":
            if allowed is None:
                allowed = logo_mark_allowed(project, image)
            if not allowed:
                reasons.append(f"{m['type']} at {m['where']} is not allowed here, so it counts as logo_like")
        elif graphic and m["type"] == "pseudo_text":
            reasons.append(f"pseudo_text at {m['where']} (a graphic is read up close)")
    if graphic:
        if review.get("text_area") is not True:
            reasons.append("the empty area for the text is not clean and usable")
    else:
        size = review.get("size") or {}
        if not size.get("within"):
            over = [f"{key} off by {size['deviation'][key]}" for key in size_off(size["deviation"], tol)]
            reasons.append(f"size outside {tol:g} ({', '.join(over)})")
    if not review.get("premium"):
        reasons.append("not premium")
    return ("fail" if reasons else "pass"), reasons


def verdict_line(verdict, reasons):
    return f"verdict: {verdict} ({'; '.join(reasons)})" if reasons else f"verdict: {verdict}"


def cmd_review(a):
    """Record a review of one image; returns 0 for pass, 1 for fail."""
    project = common.find_project(a.project)
    image = os.path.abspath(a.image)
    if not os.path.isfile(image):
        raise common.InputError("C-INPUT", a.image, "image not found")
    rel = project.rel(image)
    sc = common.read_sidecar(image)
    version = common.sidecar_version(sc)
    findings = []
    set_id = concept_id = gid = None
    if version == 2 and sc.get("kind") == "graphic" and isinstance(sc.get("graphic"), str):
        gid = sc["graphic"]
    elif version == 2 and isinstance(sc.get("set"), str) and isinstance(sc.get("concept"), str):
        set_id, concept_id = sc["set"], sc["concept"]
    else:
        c = common.owner_of_path(project, image)
        if c is None or not common.inside(os.path.join(c.dir, "renders"), image):
            raise common.InputError("C-INPUT", rel, "not an image in a concept's renders/ folder")
        if common.is_graphic(c):
            gid = c.id
        else:
            set_id, concept_id = c.set, c.id
    if gid is not None:
        if a.size_json is not None:
            raise UsageError("a graphic has no size gate; leave out --size-json")
        if a.text_area is None:
            raise UsageError("--text-area yes|no is required for a graphic")
    else:
        if a.size_json is None:
            raise UsageError("--size-json is required for a concept render")
        if a.text_area is not None:
            raise UsageError("--text-area is only for graphics")
    if version == 1:
        findings.append(common.Finding("C-LEGACY", "warn", rel, "legacy: the image has an old sidecar"))
    marks = parse_marks(a.marks_json)
    size = None if gid is not None else parse_size(project, a.size_json)
    review = {"schema": "review/1", "image": os.path.basename(image), "sha256": common.sha256_file(image),
              "set": set_id, "concept": concept_id, "scope": a.scope, "marks": marks, "size": size,
              "premium": a.premium == "yes", "reviewer_verdict": a.verdict, "verdict": None,
              "reviewer": a.reviewer, "notes": a.notes or "", "inherited_from": None,
              "reviewed_at": common.now_iso()}
    if gid is not None:
        review.update({"kind": "graphic", "graphic": gid, "text_area": a.text_area == "yes"})
    verdict, reasons = compute_verdict(project, image, review)
    review["verdict"] = verdict
    common.write_json(common.review_path(image), review)
    print(verdict_line(verdict, reasons))
    if verdict == "fail":
        findings.append(common.Finding("R-REVIEW", "error", rel, f"verdict: fail ({'; '.join(reasons)})"))
    return common.print_findings(findings) if findings else 0


# ---------- logo and label ----------

def base_render(project, image):
    """(concept or graphic, findings) for the render that logo and label start from: it must pass the base chain."""
    absolute = os.path.abspath(image)
    concept = common.owner_of_path(project, absolute)
    if concept is None:
        return None, [common.Finding("R-SOURCE", "error", project.rel(absolute),
                                     "chain: not a render of any concept")]
    return concept, check_base(project, concept, absolute)[1]


def stamped_hashes(project):
    """The sha256 of every file of every stamped reference set."""
    refs = project.brief.get("references")
    out = set()
    for entry in (refs.get("sets") if isinstance(refs, dict) else None) or []:
        for f in (entry.get("files") if isinstance(entry, dict) else None) or []:
            if isinstance(f, dict) and isinstance(f.get("sha256"), str):
                out.add(f["sha256"])
    return out


def logo_findings(project, logo):
    """R-SOURCE findings for a logo file: it must be the deck-style logo or lie directly in brief/brand/, and must
    not be a copy of a reference photo."""
    out = []
    style_logo = project.style.get("logo")
    official = common.real(os.path.dirname(logo)) == common.real(project.path("brief", "brand"))
    if isinstance(style_logo, str) and style_logo:
        official = official or common.real(logo) == common.real(os.path.join(project.path("brief"), style_logo))
    shown = project.rel(logo)
    if not official:
        out.append(common.Finding("R-SOURCE", "error", shown,
                                  "logo-source: the logo must be the deck-style logo or a file in brief/brand/"))
    if common.sha256_file(logo) in stamped_hashes(project):
        out.append(common.Finding("R-SOURCE", "error", shown,
                                  "logo-ref: this file has the content of a reference photo"))
    return out


def cmd_logo(a):
    """Warp the official logo onto a panel of a render; returns the exit code."""
    project = common.find_project(a.project)
    quad = parse_quad(a.quad)
    if not os.path.isfile(a.logo):
        raise UsageError(f"logo not found: {a.logo}")
    concept, findings = base_render(project, a.image)
    logo = os.path.abspath(a.logo)
    if not any(f.level == "error" for f in findings):
        findings += logo_findings(project, logo)
    if any(f.level == "error" for f in findings):
        return common.print_findings(findings)
    image = os.path.abspath(a.image)
    renders = os.path.join(concept.dir, "renders")
    out = next_names(renders, view_of_base(image), 1)[0]
    place_logo(image, logo, quad, out, a.blend or ("normal" if common.is_graphic(concept) else "multiply"))
    common.write_sidecar(out, {
        "tool": "render.py", "mode": "logo", **fields_of(concept, base_sidecar=common.read_sidecar(image)),
        "inputs": [{"role": "base", "path": project.rel(image), "sha256": common.sha256_file(image)},
                   {"role": "logo", "path": project.rel(logo), "sha256": common.sha256_file(logo)}],
        "prompt_sha256": None, "lint": None, "api": None})
    print(f"saved {project.rel(out)}")
    base_review = common.read_review(image)
    if base_review is not None and base_review.get("sha256") == common.sha256_file(image):
        review = dict(base_review)
        review.update({"image": os.path.basename(out), "sha256": common.sha256_file(out),
                       **({} if common.is_graphic(concept) else {"set": concept.set, "concept": concept.id}),
                       "marks": list(base_review.get("marks") or []) + [
                           {"type": "composited_logo", "where": "whole", "note": project.rel(logo)}],
                       "inherited_from": {"image": os.path.basename(image), "sha256": base_review["sha256"]},
                       "reviewed_at": common.now_iso()})
        review["verdict"], reasons = compute_verdict(project, out, review)
        common.write_json(common.review_path(out), review)
        print(f"review carried over from {os.path.basename(image)}; {verdict_line(review['verdict'], reasons)}")
    else:
        print("no current review on the base; review the output with render.py review")
    if findings:
        common.print_findings(findings)
    return 0


def stamp_text(project, title):
    """The line stamped on a labelled copy: the title, then the deck-style stamp, else the labels stamp."""
    stamp = project.style.get("stamp")
    if not isinstance(stamp, str) or not stamp.strip():
        stamp = project.labels.get("stamp")
    if not isinstance(stamp, str) or not stamp.strip():
        raise common.InputError("C-INPUT", f"assets/labels/{project.lang}.json", "no stamp text")
    title = title.strip()
    return f"{title}  ·  {stamp.strip()}" if title else stamp.strip()


def cmd_label(a):
    """Stamp a copy of a render for showing the user; the copy is never usable in the deck."""
    project = common.find_project(a.project)
    concept, findings = base_render(project, a.image)
    if any(f.level == "error" for f in findings):
        return common.print_findings(findings)
    image = os.path.abspath(a.image)
    text = stamp_text(project, a.title)
    cjk = common.has_cjk(text)
    font = common.find_font(cjk)
    if cjk and font is None:
        raise UsageError("no font with CJK characters found on this machine for the stamp text")
    stem = os.path.splitext(os.path.basename(image))[0]
    out = os.path.abspath(a.out) if a.out else project.path("work", "labelled", f"{stem}-label.png")
    if common.real(out) == common.real(image):
        raise UsageError("--out must not be the image itself")
    label(image, text, out, font)
    common.write_sidecar(out, {
        "tool": "render.py", "mode": "label", **fields_of(concept, base_sidecar=common.read_sidecar(image)),
        "inputs": [{"role": "base", "path": project.rel(image), "sha256": common.sha256_file(image)}],
        "prompt_sha256": None, "lint": None, "api": None})
    print(f"saved {project.rel(out)}")
    if findings:
        common.print_findings(findings)
    return 0


# ---------- tiles and sheet ----------

TILE_OVERLAP = 0.08
SHEET_CELL_W = 768
SHEET_GUTTER = 16
SHEET_CAPTION_H = 40
SHEET_TITLE_H = 48


def parse_grid(text):
    """(columns, rows) from 'CxR', each 1-6; anything else is a usage error."""
    m = re.fullmatch(r"(\d+)x(\d+)", str(text))
    if not m or not all(1 <= int(g) <= 6 for g in m.groups()):
        raise UsageError(f"--grid must look like 3x2 (columns x rows, each 1-6), not {text!r}")
    return int(m.group(1)), int(m.group(2))


def tile_boxes(size, cols, rows):
    """{(r, c): box} for a W x H image: equal cells grown by 8 % on every side, clipped to the image."""
    W, H = size
    cw, ch = W / cols, H / rows
    ox, oy = TILE_OVERLAP * cw, TILE_OVERLAP * ch
    return {(r, c): (max(0, round(c * cw - ox)), max(0, round(r * ch - oy)),
                     min(W, round((c + 1) * cw + ox)), min(H, round((r + 1) * ch + oy)))
            for r in range(rows) for c in range(cols)}


def cmd_tiles(a):
    """Cut a render into overlapping tiles for the review; returns the exit code."""
    from PIL import Image
    project = common.find_project(a.project)
    cols, rows = parse_grid(a.grid if a.grid else project.thresholds["tiles_grid"])
    image = os.path.abspath(a.image)
    if not os.path.isfile(image):
        raise common.InputError("C-INPUT", a.image, "file not found")
    concept = common.owner_of_path(project, image)
    if concept is None or not common.inside(os.path.join(concept.dir, "renders"), image):
        raise common.InputError("C-INPUT", project.rel(image), "not a render of any concept")
    try:
        with Image.open(image) as im:
            im.load()
            if not a.grid and im.height > im.width:       # a tall image: the default grid turns with it
                cols, rows = rows, cols
            boxes = tile_boxes(im.size, cols, rows)
            stem = os.path.splitext(os.path.basename(image))[0]
            if common.is_graphic(concept):
                folder = project.path("work", "tiles", common.GRAPHICS_FOLDER, concept.id, stem)
            else:
                folder = project.path("work", "tiles", concept.set, concept.id, stem)
            os.makedirs(folder, exist_ok=True)
            for name in os.listdir(folder):
                if re.fullmatch(r"r\d+c\d+\.png", name):
                    os.remove(os.path.join(folder, name))
            for (r, c), box in boxes.items():
                path = os.path.join(folder, f"r{r + 1}c{c + 1}.png")
                im.crop(box).save(path)
                print(project.rel(path))
    except OSError as e:
        raise common.InputError("C-INPUT", project.rel(image), f"not a readable image ({e})") from None
    return 0


def renders_of(concept):
    """The candidate images of a concept or graphic (sidecar mode hero or graphic, or import), by view and
    version."""
    folder = os.path.join(concept.dir, "renders")
    try:
        listing = os.listdir(folder)
    except OSError:
        return []
    out = []
    for name in listing:
        m = re.fullmatch(r"(.+)-v(\d+)\.(?:png|jpe?g|webp)", name, re.I)
        if not m:
            continue
        side = common.read_sidecar(os.path.join(folder, name))
        if side is not None and side.get("mode") in common._ROOT_MODES[common.is_graphic(concept)]:
            out.append((m.group(1), int(m.group(2)), os.path.join(folder, name)))
    return [path for _, _, path in sorted(out)]


def review_state(image):
    """pass full, pass whole, fail, stale review or no review."""
    review = common.read_review(image)
    if review is None:
        return "no review"
    if review.get("sha256") != common.sha256_file(image):
        return "stale review"
    if review.get("verdict") != "pass":
        return "fail"
    return "pass full" if review.get("scope") == "full" else "pass whole"


def draw_text(draw, xy, text, size, fill):
    """Text in a font that has its characters (common.find_font), else Pillow's own font."""
    from PIL import ImageFont
    path = common.find_font(common.has_cjk(text))
    try:
        font = ImageFont.truetype(path, size) if path else ImageFont.load_default(size)
    except (OSError, TypeError):
        font = ImageFont.load_default()
    if not isinstance(font, ImageFont.FreeTypeFont):      # the bitmap font only has Latin-1
        text = text.replace("·", "-").encode("latin-1", "replace").decode("latin-1")
    draw.text(xy, text, font=font, fill=fill)


def make_sheet(title, rows, out):
    """rows: lists of (image path | None, caption). White board, title band, a caption band under every row."""
    from PIL import Image, ImageDraw
    cells = []
    for row in rows:
        line = []
        for path, caption in row:
            if path is None:
                line.append((None, caption, SHEET_CELL_W * 2 // 3))
                continue
            with Image.open(path) as im:
                im = im.convert("RGB")
                h = max(1, round(im.height * SHEET_CELL_W / im.width))
                line.append((im.resize((SHEET_CELL_W, h), Image.LANCZOS), caption, h))
        cells.append(line)
    width = SHEET_GUTTER + max([len(r) for r in cells] + [1]) * (SHEET_CELL_W + SHEET_GUTTER)
    height = SHEET_TITLE_H + sum(max([h for _, _, h in r] + [0]) + SHEET_CAPTION_H + SHEET_GUTTER for r in cells)
    board = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(board)
    draw_text(d, (SHEET_GUTTER, 10), title, 28, (20, 20, 20))
    y = SHEET_TITLE_H
    for line in cells:
        row_h = max([h for _, _, h in line] + [0])
        for i, (im, caption, h) in enumerate(line):
            x = SHEET_GUTTER + i * (SHEET_CELL_W + SHEET_GUTTER)
            if im is None:
                d.rectangle([x, y, x + SHEET_CELL_W - 1, y + h - 1], fill=(200, 200, 200))
            else:
                board.paste(im, (x, y))
            draw_text(d, (x, y + row_h + 8), caption, 22, (20, 20, 20))
        y += row_h + SHEET_CAPTION_H + SHEET_GUTTER
    os.makedirs(os.path.dirname(out), exist_ok=True)
    board.save(out)


def chosen_cell(concept, findings, qualified=False):
    """(image path | None, caption) for the concept's chosen render; front matter findings are collected.
    The caption starts with the concept id, or with <set>/<id> when qualified (the overview of all sets)."""
    fm, fs = common.read_front_matter(concept)
    findings += fs
    label = f"{concept.set}/{concept.id}" if qualified else concept.id
    chosen = None if any(f.level == "error" for f in fs) else fm.get("chosen")
    if not chosen:
        return None, f"{label} · no chosen"
    path = os.path.join(concept.dir, chosen)
    return path, f"{label} · {os.path.basename(path)} · {review_state(path)}"


def graphic_rows(project, findings):
    """One row per brief graphic, in brief order: its candidates plus the chosen render when that is not one."""
    rows = []
    for item in common.graphics_of(project.brief):
        if not isinstance(item.get("id"), str) or not common.GRAPHIC_ID_RE.fullmatch(item["id"]):
            continue
        g = common.graphic_ref(project, item["id"])
        fm, fs = common.read_front_matter(g)
        findings += fs
        chosen = None if any(f.level == "error" for f in fs) or not fm.get("chosen") \
            else os.path.join(g.dir, fm["chosen"])
        images = list(renders_of(g))
        if chosen and os.path.isfile(chosen) and common.real(chosen) not in [common.real(p) for p in images]:
            images.append(chosen)
        row = [(p, f"{g.id} \u00b7 {os.path.basename(p)} \u00b7 {review_state(p)}"
                + (" \u00b7 chosen" if chosen and common.real(p) == common.real(chosen) else "")) for p in images]
        rows.append(row or [(None, f"{g.id} \u00b7 no candidates")])
    return rows


def cmd_sheet(a):
    """Write a candidate board, a set's chosen row, the overview of all chosen renders or the graphics board."""
    project = common.find_project(a.project)
    findings = []
    if a.graphics:
        rows = graphic_rows(project, findings)
        if not rows:
            raise common.InputError("C-INPUT", "brief/brief.json graphics", "no graphics in brief.json")
        out = project.path("work", "sheets", "graphics.png")
        make_sheet(common.GRAPHICS_FOLDER, rows, out)
        if findings:
            common.print_findings(findings)
        print(project.rel(out))
        return 0
    concepts = common.list_concepts(project)
    if a.chosen_all:
        by_set = {}
        for c in concepts:
            by_set.setdefault(c.set, []).append(c)
        if not by_set:
            raise common.InputError("C-INPUT", "concepts", "no concept folders")
        rows = [[chosen_cell(c, findings, qualified=True) for c in by_set[sid]] for sid in sorted(by_set)]
        out, title = project.path("work", "sheets", "chosen-all.png"), "chosen"
    else:
        if not a.set:
            raise UsageError("--set is required with --candidates and --chosen")
        mine = [c for c in concepts if c.set == a.set]
        if not mine:
            raise common.InputError("C-INPUT", a.set, "unknown set: no concept folders under concepts/" + a.set)
        if a.candidates:
            rows = []
            for c in mine:
                row = [(p, f"{c.id} · {os.path.basename(p)} · {review_state(p)}") for p in renders_of(c)]
                rows.append(row or [(None, f"{c.id} · no candidates")])
            out, title = project.path("work", "sheets", f"{a.set}-candidates.png"), f"{a.set} candidates"
        else:
            rows = [[chosen_cell(c, findings) for c in mine]]
            out, title = project.path("work", "sheets", f"{a.set}-chosen.png"), f"{a.set} chosen"
    make_sheet(title, rows, out)
    if findings:
        common.print_findings(findings)
    print(project.rel(out))
    return 0


def _report(e, code_width=18):
    print(f"{'ERROR':<7} {e.code:<{code_width}} {e.where}: {e}", file=sys.stderr)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles choke on · and CJK
    ap = argparse.ArgumentParser(description="Booth renders: lint, hero, graphic, fix, front, import, review, logo, "
                                             "label, tiles, sheet")
    sub = ap.add_subparsers(dest="cmd", required=True)
    api = argparse.ArgumentParser(add_help=False)
    api.add_argument("--project", default=".", help="the project folder (holds brief/)")
    api.add_argument("--model", help=f"default {PROVIDERS['openai']['model']}")
    api.add_argument("--size", help="default 1536x1024; a graphic: the supported size nearest to its ratio")
    api.add_argument("--quality", default="high")
    api.add_argument("--fidelity", choices=["high", "low"], help="input_fidelity for edits; sent only when given")
    api.add_argument("--provider", choices=list(PROVIDERS), default="openai")
    api.add_argument("--dry-run", action="store_true", help="lint, print the request and output names, send nothing")
    parsers = {}
    p = parsers["hero"] = sub.add_parser("hero", parents=[api], help="candidates from a short prompt and the "
                                                                    "concept's own reference photos")
    p.add_argument("--concept", required=True, help="<set>/<concept>; the renders go to its renders/ folder")
    p.add_argument("--prompt", required=True)
    p.add_argument("--ref", action="append", help="a reference photo of the concept's own set (repeatable); "
                                                  "with --ref the call goes to the edit endpoint")
    p.add_argument("--n", type=int, help="images per call, 1-10 (default: candidates_per_concept)")
    p = parsers["graphic"] = sub.add_parser("graphic", parents=[api], help="candidates of a requested graphic from a "
                                                                          "prompt (and the product photos of the brief)")
    p.add_argument("--graphic", required=True, help="a graphic id of brief.json graphics, e.g. GR1")
    p.add_argument("--prompt", required=True)
    p.add_argument("--area", required=True, choices=list(common.GRAPHIC_AREAS),
                   help="the side where the artwork stays empty for the text")
    p.add_argument("--ref", action="append", help="a product photo of this graphic in brief.json (repeatable); "
                                                  "with --ref the call goes to the edit endpoint")
    p.add_argument("--candidates", type=int, help="images per call, 1-10 (default: candidates_per_concept)")
    p = parsers["front"] = sub.add_parser("front", parents=[api], help="edit the front view from a render")
    p.add_argument("--concept", required=True, help="<set>/<concept>; the renders go to its renders/ folder")
    p.add_argument("--prompt", required=True)
    p.add_argument("--base", required=True, help="a render of the concept to start from")
    p = parsers["fix"] = sub.add_parser("fix", parents=[api], help="apply one correction to a render")
    who = p.add_mutually_exclusive_group(required=True)
    who.add_argument("--concept", help="<set>/<concept>; the renders go to its renders/ folder")
    who.add_argument("--graphic", help="a graphic id of brief.json graphics")
    p.add_argument("--base", required=True, help="the render to correct")
    p.add_argument("--add", required=True, help="the correction, one sentence")
    p.add_argument("--prompt", help="the original hero prompt, appended for reference")
    p.add_argument("--view", help="output name stem; default: the base file's view, else hero")
    proj = argparse.ArgumentParser(add_help=False)
    proj.add_argument("--project", default=".", help="the project folder (holds brief/)")
    p = parsers["import"] = sub.add_parser("import", parents=[proj],
                                           help="copy an image made elsewhere into a concept's or graphic's renders/")
    p.add_argument("file", help="png, jpg or webp image")
    who = p.add_mutually_exclusive_group(required=True)
    who.add_argument("--concept", help="<set>/<concept>")
    who.add_argument("--graphic", help="a graphic id of brief.json graphics")
    p.add_argument("--area", choices=list(common.GRAPHIC_AREAS),
                   help="graphic: the side where the artwork stays empty for the text (required with --graphic)")
    p.add_argument("--view", help="output name stem (default hero; not with --graphic)")
    p.add_argument("--ref", action="append", help="a reference photo that was attached (repeatable); recorded only")
    p.add_argument("--prompt", help="the prompt that was used; linted and recorded, never blocks")
    p = parsers["review"] = sub.add_parser("review", parents=[proj], help="record a review of one image")
    p.add_argument("image")
    p.add_argument("--reviewer", required=True, choices=["subagent", "self", "user"])
    p.add_argument("--verdict", required=True, choices=["pass", "fail"], help="the reviewer's own verdict")
    p.add_argument("--premium", required=True, choices=["yes", "no"])
    p.add_argument("--size-json",
                   help='a concept render: JSON, a file or -: {"expected": {"w","d","h"}, "observed": {"w","d","h"}}, '
                        "in person-heights; expected defaults to the booth")
    p.add_argument("--text-area", choices=["yes", "no"],
                   help="a graphic: is the area kept empty for the text clean and usable?")
    p.add_argument("--marks-json", required=True,
                   help='JSON, a file or -: [{"type": "pseudo_text", "where": "r1c3", "note": "..."}]; [] is allowed')
    p.add_argument("--scope", choices=list(SCOPES), default="whole", help="full = whole image and every tile")
    p.add_argument("--notes")
    p = parsers["logo"] = sub.add_parser("logo", parents=[proj], help="warp the official logo onto a panel")
    p.add_argument("image", help="a render of a concept")
    p.add_argument("--logo", required=True, help="the deck-style logo or a file in brief/brand/")
    p.add_argument("--quad", required=True,
                   help='"u1,v1 u2,v2 u3,v3 u4,v4": top-left, top-right, bottom-right, bottom-left')
    p.add_argument("--blend", choices=["multiply", "normal"], help="default multiply; normal on a graphic")
    p = parsers["label"] = sub.add_parser("label", parents=[proj], help="stamp a copy of a render for showing")
    p.add_argument("image", help="a render of a concept")
    p.add_argument("--title", required=True)
    p.add_argument("--out", help="default work/labelled/<name>-label.png in the project")
    p = parsers["tiles"] = sub.add_parser("tiles", parents=[proj], help="cut a render into overlapping tiles")
    p.add_argument("image", help="a render of a concept")
    p.add_argument("--grid", help="columns x rows, e.g. 3x2 (default: thresholds tiles_grid)")
    p = parsers["sheet"] = sub.add_parser("sheet", parents=[proj], help="a board of candidates or chosen renders")
    p.add_argument("--set", help="a reference set id (with --candidates or --chosen)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--candidates", action="store_true", help="one row per concept, every candidate")
    mode.add_argument("--chosen", action="store_true", help="one row with the set's chosen renders")
    mode.add_argument("--chosen-all", action="store_true", help="one row per set with its chosen renders")
    mode.add_argument("--graphics", action="store_true", help="one row per brief graphic with its candidates")
    lint_parser = parsers["lint"] = sub.add_parser(
        "lint", help="check a prompt against the prompt rules; no network, no files")
    lint_parser.add_argument("--project", default=".")
    lint_parser.add_argument("--mode", required=True, choices=list(LINT_MODES))
    src = lint_parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt", help="prompt file")
    src.add_argument("--add", help="a fix correction sentence (only with --mode fix)")
    lint_parser.add_argument("--concept", help="<set>/<concept>")
    lint_parser.add_argument("--graphic", help="with --mode graphic: a graphic id of brief.json graphics (for --ref)")
    lint_parser.add_argument("--area", choices=list(common.GRAPHIC_AREAS), help="with --mode graphic: the empty side")
    lint_parser.add_argument("--ref", action="append",
                             help="a reference photo (repeatable; needs --concept or --graphic)")
    lint_parser.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    handlers = {"lint": cmd_lint, "hero": cmd_generate, "graphic": cmd_graphic, "fix": cmd_generate,
                "front": cmd_generate,
                "tiles": cmd_tiles, "sheet": cmd_sheet, "import": cmd_import, "review": cmd_review, "logo": cmd_logo, "label": cmd_label}
    try:
        return handlers[a.cmd](a)
    except common.InputError as e:
        _report(e)
        return 2
    except ApiError as e:
        _report(e)
        return 3
    except UsageError as e:
        parsers[a.cmd].error(str(e))


if __name__ == "__main__":
    sys.exit(main())
