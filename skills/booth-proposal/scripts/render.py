"""Booth renders: make concept renders with an image model, then place a logo and stamp the draft label.

Renders are concept visualisations, not construction drawings. The hero view (View 1) comes from a short prompt
with the reference image files attached (--ref; then the call goes to the edit endpoint, without --ref to the
generation endpoint); ask for two candidates and choose one. The front view (View 2) and every fix are edits of
the chosen render, so the design, materials and light carry over. Massing images are never sent here.
Each saved image gets two sidecars: <name>.prompt.txt (the exact prompt sent) and <name>.json (mode, model, size,
quality, input images, usage from the response, seconds, timestamp). Existing renders are never overwritten: new
files are numbered after the highest <view>-v<k>.png already in the output folder.

Usage:
  python render.py hero  --prompt hero.txt --out-dir concepts/A/renders [--n 2] [--ref ref1.jpg --ref ref2.jpg]
                         -> hero-v<k>.png, one per candidate; --ref (repeatable) attaches the reference images
                            (the client's booths, images they like), which no written description replaces
  python render.py front --prompt front.txt --base concepts/A/renders/hero-v2.png --out-dir concepts/A/renders
                         -> front-v<k>.png, the front view edited from the chosen hero render
  python render.py fix   --base renders/hero-v2.png --add "one correction sentence" --out-dir renders
                         [--view hero] [--prompt hero.txt]
                         -> <view>-v<k>.png, the base render with that one change; the view defaults to the base
                            file's own name (front-v1.png -> front), else hero. For details; a clearly wrong size
                            (more than about 20 %, or the hero off the platform) needs a new hero instead
  python render.py label render.png --title "A · The Ribbon" --out final.png
                         -> a dark strip at the bottom right: "<title>  ·  初稿 – 概念效果示意，不用于施工 /
                            Draft – concept visualization, not for construction"
  python render.py logo  render.png --logo logo.png --quad "u1,v1 u2,v2 u3,v3 u4,v4" --out out.png [--blend normal]
                         -> the logo warped onto a panel; the four pixel corners are the logo's top-left, top-right,
                            bottom-right and bottom-left. multiply (default) lets the panel's light and shadow show
                            through a dark logo on a light panel; normal pastes it as is (light logo on a dark panel)

Options for hero, front and fix:
  --model gpt-image-2   --size 1536x1024   --quality high   --n 1 (images per call, 1-10)
  --fidelity high|low   sends input_fidelity with any call that has input images (front, fix, hero with --ref); if
                        the model rejects it, the call is retried once without it. hero without --ref does not send it.
  --dry-run             print the endpoint, fields, input images, prompt and output names; no network call
  --provider openai     PROVIDERS holds each provider's endpoints; only OpenAI's request format is implemented

The API key comes from the environment (OPENAI_API_KEY) or from a .env file in the current folder or a parent
(a line OPENAI_API_KEY=... or openai_key=..., any case). It is never printed, logged or written.
429, 500, 502 and 503 are retried twice, 20 s apart; any other error prints the server's message and exits 1.
HTTP uses the standard library only; label and logo need Pillow (logo also numpy).
"""
import argparse
import base64
import datetime
import glob
import json
import math
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

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
TIMEOUT_S = 600      # one high-quality image can take two minutes; n images take longer

FIX_PROMPT = ("Edit this photograph of an exhibition stand. Keep the design, materials, light, camera and people; "
              "change only what this correction asks for: {add}")
FIX_BRIEF = "\n\nOriginal brief for reference:\n{brief}"
DRAFT_NOTE = "初稿 – 概念效果示意，不用于施工 / Draft – concept visualization, not for construction"
DRAFT_NOTE_EN = "Draft – concept visualization, not for construction"
CJK_FONTS = ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "/System/Library/Fonts/PingFang.ttc",
             "/usr/share/fonts/**/NotoSansCJK*.ttc"]


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


def find_key(provider):
    """Return (key, where it was found) or (None, None). Only the place is ever shown, never the key."""
    p = PROVIDERS[provider]
    if os.environ.get(p["key_env"], "").strip():
        return os.environ[p["key_env"]].strip(), "the environment"
    folder = os.path.abspath(os.getcwd())
    while True:
        path = os.path.join(folder, ".env")
        if os.path.isfile(path):
            key = key_from_env_file(path, p["key_names"])
            if key:
                return key, path
        parent = os.path.dirname(folder)
        if parent == folder:
            return None, None
        folder = parent


def missing_key(provider):
    p = PROVIDERS[provider]
    names = " or ".join(f"{n}=<your key>" for n in p["key_names"])
    return (f"No API key found. Either set the environment variable {p['key_env']}, or add a line {names} "
            f"to a .env file in the current folder ({os.getcwd()}) or one of its parents.")


# ---------- request ----------

def read_text(path, what):
    if not os.path.isfile(path):
        sys.exit(f"{what} not found: {path}")
    with open(path, encoding="utf-8-sig") as f:
        text = f.read().strip()
    if not text:
        sys.exit(f"{what} is empty: {path}")
    return text


def next_names(out_dir, view, n):
    """Paths for n new images, numbered after the highest <view>-v<k>.png already in out_dir."""
    pat = re.compile(rf"{re.escape(view)}-v(\d+)\.png", re.IGNORECASE)
    files = os.listdir(out_dir) if os.path.isdir(out_dir) else []
    k = max((int(m.group(1)) for f in files if (m := pat.fullmatch(f))), default=0)
    return [os.path.join(out_dir, f"{view}-v{k + i}.png") for i in range(1, n + 1)]


def view_of(a):
    """The output name stem: hero and front by mode; for fix, --view, else the base file's own view."""
    if a.cmd != "fix":
        return a.cmd
    if a.view:
        return a.view
    m = re.fullmatch(r"(.+)-v\d+", os.path.splitext(os.path.basename(a.base))[0])
    return m.group(1) if m else "hero"


def build(a):
    """Return (endpoint, fields, input images) for an API mode; nothing is sent here."""
    prov = PROVIDERS[a.provider]
    if a.cmd == "fix":
        if not a.add.strip():
            sys.exit("--add needs the correction, one sentence")
        prompt = FIX_PROMPT.format(add=a.add.strip())
        if a.prompt:
            prompt += FIX_BRIEF.format(brief=read_text(a.prompt, "prompt file"))
    else:
        prompt = read_text(a.prompt, "prompt file")
    images = [a.base] if a.cmd in ("front", "fix") else []
    images += getattr(a, "ref", None) or []      # reference photos the model sees alongside the prompt
    for p in images:
        if not os.path.isfile(p):
            sys.exit(f"base image not found: {p}")
    fields = {"model": a.model or prov["model"], "prompt": prompt, "size": a.size, "quality": a.quality, "n": a.n}
    if a.fidelity and images:
        fields["input_fidelity"] = a.fidelity
    elif a.fidelity:
        print("note: --fidelity applies to edits (front, fix) only; a generation has no input image, so it is not sent")
    return prov["edit" if images else "generate"], fields, images


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
    """POST with the retry rules; return (response, seconds, fields actually sent). Exits 1 on failure."""
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
                print(f"HTTP {e.code}: {msg}\nretrying in {BACKOFF_S} s")
                time.sleep(BACKOFF_S)
                continue
            sys.exit(f"HTTP {e.code}: {msg}")
        except OSError as e:   # no connection, DNS, timeout (URLError is an OSError)
            sys.exit(f"request failed: {getattr(e, 'reason', e)}")


def save(res, names, sent, meta, seconds):
    """Write each returned image with its .prompt.txt and .json sidecars."""
    data = res.get("data") or []
    if not data:
        sys.exit("the server answered without an image")
    os.makedirs(os.path.dirname(os.path.abspath(names[0])), exist_ok=True)
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    usage = res.get("usage", {})
    for path, item in zip(names, data):
        if item.get("b64_json"):
            blob = base64.b64decode(item["b64_json"])
        else:
            with urllib.request.urlopen(item["url"], timeout=TIMEOUT_S) as r:
                blob = r.read()
        with open(path, "wb") as f:
            f.write(blob)
        stem = os.path.splitext(path)[0]
        with open(stem + ".prompt.txt", "w", encoding="utf-8") as f:
            f.write(sent["prompt"])
        info = dict(meta, image=os.path.basename(path), input_fidelity=sent.get("input_fidelity"),
                    usage=usage, seconds=round(seconds, 1), timestamp=stamp)
        if item.get("revised_prompt"):
            info["revised_prompt"] = item["revised_prompt"]
        with open(stem + ".json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print(f"saved {path} in {seconds:.0f}s · model {sent['model']} · usage {json.dumps(usage)}")
    if len(data) < len(names):
        print(f"note: asked for {len(names)} images, the server returned {len(data)}")


def dry_run(a, url, fields, images, names):
    prompt = fields["prompt"]
    print(f"DRY RUN · {a.cmd} · {a.provider} · nothing is sent")
    print(f"POST {url}  ({'multipart form' if images else 'JSON'})")
    for k, v in fields.items():
        if k != "prompt":
            print(f"  {k}: {v}")
    if images:
        print(f"  {PROVIDERS[a.provider]['image_field']}: " + ", ".join(images))
    else:
        print("  input images: none")
    head = prompt[:200].replace("\n", " ⏎ ")
    print(f"  prompt: {len(prompt)} characters: {head}{' …' if len(prompt) > 200 else ''}")
    _, where = find_key(a.provider)
    print(f"API key: found in {where} (not shown)" if where else "API key: NOT FOUND, a real run would stop here")
    for p in names:
        print(f"would save {p} (+ .prompt.txt, .json)")


def generate(a):
    if not 1 <= a.n <= 10:
        sys.exit("--n must be between 1 and 10")
    url, fields, images = build(a)
    view = view_of(a)
    if not re.fullmatch(r"[\w.-]+", view):
        sys.exit(f"--view must be a plain name such as hero or front, not {view!r}")
    names = next_names(a.out_dir, view, a.n)
    if a.dry_run:
        dry_run(a, url, fields, images, names)
        return
    key, _ = find_key(a.provider)
    if not key:
        sys.exit(missing_key(a.provider))
    print(f"{a.cmd}: {len(names)} image(s) from {url} · model {fields['model']} · {a.size} · {a.quality}")
    res, seconds, sent = call(url, key, fields, images, PROVIDERS[a.provider]["image_field"])
    meta = dict(mode=a.cmd, provider=a.provider, endpoint=url, model=sent["model"], size=a.size, quality=a.quality,
                n=a.n, input_images=images, prompt_file=a.prompt)
    if a.cmd == "fix":
        meta["correction"] = a.add.strip()
    save(res, names, sent, meta, seconds)


# ---------- label and logo (Pillow) ----------

def find_cjk_font(fonts=CJK_FONTS):
    for pattern in fonts:
        for path in sorted(glob.glob(pattern, recursive=True)):
            if os.path.isfile(path):
                return path
    return None


def save_image(im, out, alpha):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if not alpha or out.lower().endswith((".jpg", ".jpeg")):
        im = im.convert("RGB")
    im.save(out)
    print(f"saved {out}")


def label(image, title, out, fonts=CJK_FONTS):
    """Stamp the draft note on a semi-transparent dark strip in the bottom-right corner."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(image)
    W, H = im.size
    path = find_cjk_font(fonts)
    note = DRAFT_NOTE if path else DRAFT_NOTE_EN
    text = f"{title}  ·  {note}" if title else note

    def font_at(size):
        if path:
            return ImageFont.truetype(path, size)
        try:
            return ImageFont.load_default(size)      # Pillow >= 10.1 with FreeType
        except TypeError:
            return ImageFont.load_default()

    size = max(12, round(W / 90))
    font = font_at(size)
    if not path:                                     # Pillow's own fonts have no en dash; the bitmap one only Latin-1
        print("no CJK font found; stamping the English note only")
        text = text.replace("–", "-")
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
        sys.exit('--quad needs four pixel corners "u1,v1 u2,v2 u3,v3 u4,v4": '
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
        sys.exit("--quad is degenerate: three corners lie on one line")


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


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles choke on · and CJK
    ap = argparse.ArgumentParser(description="Booth renders: hero, front, fix, label, logo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    api = argparse.ArgumentParser(add_help=False)
    api.add_argument("--out-dir", required=True, help="folder for the renders and their sidecars")
    api.add_argument("--model", help=f"default {PROVIDERS['openai']['model']}")
    api.add_argument("--size", default="1536x1024")
    api.add_argument("--quality", default="high")
    api.add_argument("--n", type=int, default=1, help="images per call, 1-10")
    api.add_argument("--fidelity", choices=["high", "low"], help="input_fidelity for edits; sent only when given")
    api.add_argument("--provider", choices=list(PROVIDERS), default="openai")
    api.add_argument("--dry-run", action="store_true", help="print the request and output names, send nothing")
    p = sub.add_parser("hero", parents=[api], help="View 1 candidates from a short prompt and the reference images")
    p.add_argument("--prompt", required=True)
    p.add_argument("--ref", action="append", help="a reference photo the model sees (repeatable): the client's booths, "
                                                  "images they like; with --ref the call goes to the edit endpoint")
    p = sub.add_parser("front", parents=[api], help="View 2: edit the front view from the chosen hero render")
    p.add_argument("--prompt", required=True)
    p.add_argument("--base", required=True, help="the chosen hero render to start from")
    p = sub.add_parser("fix", parents=[api], help="apply one correction to a render")
    p.add_argument("--base", required=True, help="the render to correct")
    p.add_argument("--add", required=True, help="the correction, one sentence")
    p.add_argument("--prompt", help="the original View 1 prompt, appended for reference")
    p.add_argument("--view", help="output name stem; default: the base file's view, else hero")
    p = sub.add_parser("label", help="stamp the draft note")
    p.add_argument("image")
    p.add_argument("--title", default="")
    p.add_argument("--out", required=True)
    p = sub.add_parser("logo", help="warp a logo onto a panel")
    p.add_argument("image")
    p.add_argument("--logo", required=True)
    p.add_argument("--quad", required=True, help='"u1,v1 u2,v2 u3,v3 u4,v4": top-left, top-right, bottom-right, bottom-left')
    p.add_argument("--blend", choices=["multiply", "normal"], default="multiply")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd in ("label", "logo") and not os.path.isfile(a.image):
        sys.exit(f"image not found: {a.image}")
    if a.cmd == "label":
        label(a.image, a.title.strip(), a.out)
    elif a.cmd == "logo":
        if not os.path.isfile(a.logo):
            sys.exit(f"logo not found: {a.logo}")
        place_logo(a.image, a.logo, parse_quad(a.quad), a.out, a.blend)
    else:
        generate(a)


if __name__ == "__main__":
    main()
