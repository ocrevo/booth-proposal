# Concept renders

The render is what the client remembers: it must hold the cover of a top studio's proposal. The image model is the strongest imagination in the process: give it the idea, the photos and the few facts that must hold, and let it design.

One view per concept, the hero: `candidates_per_concept` candidates, choose one, at most `fix_max` small fixes. Render every chosen idea of every set (`gates.py ideas --scaffold` makes the folders); only the concepts the user selects are developed further. Run commands from the project folder; `scripts/` is this skill's scripts folder.

## Prompt template

Write the prompt to `concepts/<set>/<concept>/prompts/hero.txt`, in this shape:

```
Idea – [concept name, no quotes]: [the idea and its main form in two or three sentences: what visitors do in it, and which functions the main form carries].

Brand colours: [colour words with #RRGGBB, e.g. deep navy #0B3D5C, signal yellow #F2B705, white]

Size:
- One platform about [W in m / 1.75] person-heights wide and [D in m / 1.75] person-heights deep; the whole stand, the main form included, stands on it and nothing stands outside it.
- Open at [the open sides]; the other sides are closed.
- The tallest element, [the main form], is about [H in m / 1.75] times the height of a person.

Essentials: [which functions the main form carries, then what else a visitor sees, in words: a large screen, product displays, a counter, seating, storage as a door in the back wall]. No ceiling and nothing hung from the hall ceiling. A few visitors for scale, one at the front edge.
One plain panel in a brand colour is left empty for the logo, which is added later.
No lettering, numbers, names, emblems or logos anywhere; screens, product labels and signs are plain.

The attached photos are references for form, space and mood only. Carry their design language into a new stand that is clearly more premium and refined, in the brand colours above.
Do not copy any logo, lettering, slogan, poster or other brand from the photos, or anything from neighbouring stands.
```

Rules:

- No client name, product name, year or quote marks (the model paints names, wrongly); the concept name without quotes; English only.
- A screen is "a large screen", never a size. Outside Size, numbers are words ("three plinths"); HEX only on Brand colours.
- No lists of materials, light, camera or things to avoid: a specification makes the picture stiff.
- Drop "No ceiling and nothing hung from the hall ceiling." when the design hangs something.
- Without reference photos, drop the last two lines.
- Person-heights in metres ÷ 1.75; convert feet first (1 ft = 0.3048 m).
- The four fixed sentences word for word; they are kept in `assets/prompts/fixed.json` (reference, logo panel, no lettering, do not copy).

Example for Ostara Coffee: a 6 m × 4.4 m stand, at most 4 m high, open at the front and the left side.

```
Idea – Roasting Hall: a single long vaulted canopy of ribs that visitors walk under, from the aisle to a tasting bar at the back; the canopy carries the screen, and the bar grows out of its last rib.

Brand colours: espresso brown #3B2418, crema #E9D8B4, white

Size:
- One platform about three and a half person-heights wide and two and a half person-heights deep; the whole stand, the canopy included, stands on it and nothing stands outside it.
- Open at the front and the left side; the other sides are closed.
- The tallest element, the canopy, is about 2.3 times the height of a person.

Essentials: the canopy carries the tasting bar and a large screen; three plain product plinths, a few stools, storage as a door in the back wall. No ceiling and nothing hung from the hall ceiling. A few visitors for scale, one at the front edge.
One plain panel in a brand colour is left empty for the logo, which is added later.
No lettering, numbers, names, emblems or logos anywhere; screens, product labels and signs are plain.

The attached photos are references for form, space and mood only. Carry their design language into a new stand that is clearly more premium and refined, in the brand colours above.
Do not copy any logo, lettering, slogan, poster or other brand from the photos, or anything from neighbouring stands.
```

## Prompt rules

- Attach every photo of the concept's own set, `input/refs/<set>/`, one `--ref` per photo, and nothing else: lint refuses another set's photo, a render, a massing image or a plan (L-REF).
- A set gives form, space and mood; colours, logo and content are the client's.

## Lint

```
python scripts/render.py lint --mode hero --prompt concepts/set-1/A/prompts/hero.txt --concept set-1/A --ref input/refs/set-1/r01.jpg --ref input/refs/set-1/r02.jpg
python scripts/render.py lint --mode fix --add "Remove the hanging banner; nothing else changes."
```

The stricter rules apply only to free text: in hero mode the Idea and Essentials blocks and any line outside Brand colours, Size and the fixed sentences; in fix mode the whole correction sentence; in front mode every line that is not a fixed sentence.

| Code | Rule | Catches | Fix |
|---|---|---|---|
| L-BAN | `client` | a `client.names` or `protected_terms` entry | describe the thing: "a ticket kiosk" |
| L-BAN | `quote` | quote marks; an apostrophe not between letters (`visitors'`) | drop them |
| L-BAN | `cjk` | any CJK character, on any line | English only |
| L-BAN | `digit` | a digit in free text | number words; sizes only in Size |
| L-BAN | `one-per` | "one per", "one for each", "each representing" | describe the form, not a symbolic count |
| L-BAN | `timeline` | timeline, milestone, founded, anniversary … | history is proposal text |
| L-BAN | `logo-text` | "with the logo", "plaque to read", "brand name", "caption" … | keep the plain logo panel |
| L-BAN | `name-quoted` | a quote mark in the concept name on the Idea line | drop the quotes |
| L-BLOCKS | block name | Idea (with its `:`), Brand colours, Size (header + three lines) or Essentials missing | restore it from the template |
| L-REF | `set` | a ref outside the concept's stamped set | only `input/refs/<set>/`; after adding photos, `gates.py brief --stamp` |
| L-REF | `render` | a render passed as a ref | change a render with `fix` |
| L-WORDS | warn | more than `prompt_words_warn` (350) words | shorten; the call still runs |

These pass on purpose: HEX on the Brand colours line, ratios such as `2.6` in Size, number words, and the fixed sentences while they stay exact (an edited one is linted like any other line).

Lint runs before every paid call and in `--dry-run`. On an error, nothing is sent.

## Running the calls

```
python scripts/render.py hero --concept set-1/A --prompt concepts/set-1/A/prompts/hero.txt --ref input/refs/set-1/r01.jpg --ref input/refs/set-1/r02.jpg --dry-run
python scripts/render.py hero --concept set-1/A --prompt concepts/set-1/A/prompts/hero.txt --ref input/refs/set-1/r01.jpg --ref input/refs/set-1/r02.jpg
```

1. **Dry run** once first: lint, the request, the input images, the output names and where the key was found (it does not test the key).
2. **Cost.** Tell the user the count and time first (`## Budget`).
3. **Timing.** A 10-minute timeout, or run in the background. Sets run in parallel; show each set's board (`render.py sheet --set <set> --candidates`) when it is done. **Never start a second call for the same concept while one is running; files are numbered, so a duplicate costs money.**
4. **Results** land in `concepts/<set>/<concept>/renders/` as `hero-v<k>.png` with `.prompt.txt` and `.json`; never edit them. Look at every image.
5. Leave `--fidelity` out. If none of the candidates passes review, one re-render round (review.md), after telling the user the cost.

## When a call fails

| What you see | What to do |
|---|---|
| exit 3, `R-API`, no key | See `## Without a key`. |
| HTTP 401 | The key is wrong; replace it. |
| HTTP 403 or 404 | Retry once with `--model gpt-image-1`. |
| HTTP 400, content policy | Soften the wording once, lint again and retry. |
| HTTP 429, 500, 502 or 503 | The script retries twice by itself, waiting `Retry-After` (at most 120 s; else 20 s). If it still fails, retry once later. Any other 5xx is an error at once. |

Carry on with other concepts while one is stuck. A failed fix writes nothing.

## Choosing

1. Make tiles of the favoured candidate: `python scripts/render.py tiles concepts/set-1/A/renders/hero-v2.png`.
2. Review as `review.md` describes, recorded with `render.py review`: `--scope full` for the favoured candidate, `--scope whole` for the others.
3. Make the set's board: `python scripts/render.py sheet --set set-1 --candidates`.
4. In the concept.md front matter, write `chosen: renders/hero-v2.png`. Add a `blocked:` line for every file that must never be used.
5. Run `python scripts/gates.py renders`. It must pass: a chosen render needs its sidecar, a valid base chain, an own-set reference chain (`G-RENDER`) and a current passing `full` review (`G-REVIEW`); bad front matter is `G-FM`.
6. Run `render.py sheet --set set-1 --chosen` (side by side, review.md) and `render.py sheet --chosen-all` (the overview).

The only stop of `start`: SKILL.md `## Start and step mode`.

## Fixing

```
python scripts/render.py fix --concept set-1/A --base concepts/set-1/A/renders/hero-v2.png --add "<one sentence>"
```

- One correction per call; the free-text rules apply. The fix becomes the next `hero-v<k>.png`; review it with `--scope full` before moving `chosen:` to it.
- At most `fix_max` fixes in a chain (R-FIX-MAX); past that, take the other candidate or regenerate.
- A fix barely changes scale: a size outside `size_tolerance` is regenerated, not fixed.
- `--base` must be a render of this concept (R-SOURCE).

| Problem | Correction sentence |
|---|---|
| Too deep | The stand is only about [ratio in words] person-heights deep from the front edge to the back wall; bring the back wall forward and keep every design element. |
| Too wide | The platform is only about [ratio in words] person-heights wide; bring both side edges in and keep every design element. |
| Main form height | The top of [the main form] is about [ratio in words] times the height of a person; change its height only. |
| Extra structure | Remove the [ceiling / hanging banner / side room]; nothing else changes. |
| Wrong count | Show exactly [count in words] [items]; nothing else changes. |
| Painted marks (text, numbers, emblems, a drawn logo) | Clear the [place]: it becomes a plain [colour word] surface with nothing on it; nothing else changes. |
| Invented packs in product niches | The [niches] hold plain [colour word] blocks with nothing on them; nothing else changes. |

## Blocked renders

A render that still shows wrong text or facts (invented names, wrong years, a redrawn logo) after its fixes, or whose fix could not run, is blocked. Add to the concept.md front matter, one path per line:

```
blocked: renders/hero-v2.png
```

The reason goes in the free notes. A blocked file is never placed, not even for now: `gates.py renders` refuses it as chosen (`G-RENDER`), and so does the proposal check. Choose another candidate or regenerate, then move `chosen:`; keep the `blocked:` line.

## Logo

The real logo goes on the plain panel of the chosen render. Use the official file, from `brief/brand/` or the deck-style `logo`:

```
python scripts/render.py logo concepts/set-1/A/renders/hero-v2.png --logo brief/brand/logo.png --quad "u1,v1 u2,v2 u3,v3 u4,v4"
```

- The quad is the panel's pixel corners, clockwise from top-left. `--blend multiply` (default) suits a dark logo on a light panel, `normal` a light one on a dark panel.
- The output is the next render; it inherits the base's review plus a `composited_logo` mark (review.md).
- `R-SOURCE` when the logo is neither the deck-style `logo` nor a file in `brief/brand/`, or when it is a copy of a reference photo.
- Without an official logo, keep the plain panel and tell the user.

## Import

The same prompt and photos can go to another image tool. Bring each result in; it needs the same review:

```
python scripts/render.py import FILE --concept set-1/A --ref input/refs/set-1/r01.jpg --ref input/refs/set-1/r02.jpg --prompt concepts/set-1/A/prompts/hero.txt
```

- A file with the same content as a reference photo or a client file is refused (`R-SOURCE`); a file that is not png, jpg, jpeg or webp is refused (`C-INPUT`).
- Never describe an image as generated when it was not: say where each image came from.

## Without a key

`render.py` stops with `R-API` (exit 3) and "No API key found". Tell the user to add `OPENAI_API_KEY=sk-…` to a `.env` file in the project folder or a parent (the search stops at a folder holding `.git`, or at home), or to set the environment variable, which wins.

Meanwhile keep the prompts in `prompts/hero.txt`, give the user the `--dry-run` lines and the photos to attach, and bring in images made elsewhere with `render.py import`. With no render at all there is nothing to select: `start` ends after this step with the prompt files, the dry-run lines and the import instructions (SKILL.md, `## Start and step mode`).

## Defaults

`render.py hero` and `fix` use model `gpt-image-2`, size `1536x1024` and quality `high` (`--model`, `--size`, `--quality` override them). The key is read from the environment variable `OPENAI_API_KEY`, else from a line `OPENAI_API_KEY=` or `openai_key=` (any case) in a `.env` file (`## Without a key`).

## Known habits of image models

- A grid of glowing circles becomes a wall of light bulbs; say what the light passes through.
- Counted things (six leaves, three niches) come out with the wrong count; check and fix.
- Calligraphy and long Chinese text become invented characters; ask for plain surfaces.
- A logo seen in a reference is redrawn, often wrongly; ask for the plain panel and composite the real file.
- Product niches fill with invented bottles and labels; ask for plain blocks or empty lit niches.
- A stand drawn too deep is the commonest size error.

## Budget

Chosen ideas × `candidates_per_concept` images, each about `seconds_per_image` seconds, plus up to `fix_max` fixes per concept. `python scripts/gates.py report ideas` prints the count and minutes; tell the user before the first call, since every image is paid.

## Optional commands

Outside the default flow.

```
python scripts/render.py front --concept set-1/A --base concepts/set-1/A/renders/hero-v2.png --prompt concepts/set-1/A/prompts/front.txt
python scripts/render.py label concepts/set-1/A/renders/hero-v2.png --title "Roasting Hall"
```

`front` edits a render into a front view (linted in front mode; review it like any render). `label` makes a stamped copy in `work/labelled/`, never used in the proposal.
