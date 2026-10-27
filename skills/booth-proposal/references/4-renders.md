# Concept renders

The render is what the client remembers, so it must hold the cover of a top studio's proposal. The image model is the strongest imagination in the process: give it the idea, the photos and the few facts that must hold, and let it design.

One view per concept, the hero: `candidates_per_concept` candidates, choose one, at most `fix_max` small fixes. `render.py front` exists but is outside the default flow. Renders follow the ideas, for every chosen idea of every set (`gates.py ideas --scaffold` makes the folders); only the concepts the user selects are developed further.

Run commands from the project folder; `scripts/` is this skill's scripts folder, called by its full path.

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

- No client name, product name or year; the model paints them, wrongly.
- The concept name without quotes.
- A screen is "a large screen", never a size.
- Outside Size, numbers are words: "three plinths".
- HEX only on Brand colours.
- No lists of materials, light, camera or things to avoid: a specification makes the picture stiff.
- English only, whatever the user's language.
- Drop "No ceiling and nothing hung from the hall ceiling." when the design hangs something.
- Without reference photos, drop the last two lines.
- Person-heights in metres ÷ 1.75; convert feet first (1 ft = 0.3048 m).
- The four fixed sentences word for word.

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

- Attach every photo of the concept's own set, `input/refs/<set>/`, with one `--ref` per photo, and nothing else. Lint refuses a photo from another set (L-REF).
- Never attach a render, a massing image or a plan.
- A set gives form, space and mood. Colours, logo and content always come from the client's own brand.
- References are never shown in the proposal, and the proposal never describes them.

## Lint

```
python scripts/render.py lint --mode hero --prompt concepts/set-1/A/prompts/hero.txt --concept set-1/A --ref input/refs/set-1/r01.jpg --ref input/refs/set-1/r02.jpg
python scripts/render.py lint --mode fix --add "Remove the hanging banner; nothing else changes."
```

Lint applies the stricter rules only to free text:

- In hero mode, free text is the Idea and Essentials blocks and any other line outside Brand colours, Size and the fixed sentences.
- In fix mode, it is the whole correction sentence.
- In front mode, it is every line that is not a fixed sentence.

| Code | Rule | Catches | Fix |
|---|---|---|---|
| L-BAN | `client` | a `client.names` or `protected_terms` entry, outside the fixed sentences | describe the thing: "a ticket kiosk" |
| L-BAN | `quote` | quote marks; an apostrophe not between letters (`visitors'`) | drop them; "the lounge for visitors" |
| L-BAN | `cjk` | any CJK character, on any line | English only |
| L-BAN | `digit` | a digit in free text | number words; sizes only in Size |
| L-BAN | `one-per` | "one per", "one for each", "each representing" | describe the form, not a symbolic count |
| L-BAN | `timeline` | timeline, milestone, founded, anniversary … | leave history to the proposal text |
| L-BAN | `logo-text` | "with the logo", "plaque to read", "brand name", "caption" … | keep the plain logo panel |
| L-BAN | `name-quoted` | the concept name on the Idea line carries a quote mark (an apostrophe between two letters is fine) | drop the quotes |
| L-BLOCKS | block name | Idea (with its `:`), Brand colours, Size (header + three lines) or Essentials missing | restore it from the template; headers start their line |
| L-REF | `set` | a ref outside the concept's stamped set | only `input/refs/<set>/`; after adding photos, `gates.py brief --stamp` |
| L-REF | `render` | a render passed as a ref | change a render with `fix` |
| L-WORDS | warn | more than `prompt_words_warn` (350) words | shorten; the call still runs |

These pass on purpose: HEX on the Brand colours line, ratios such as `2.6` in Size, number words ("three plinths"), and the fixed sentences while they stay exact. An edited fixed sentence is linted like any other line.

Lint runs before every paid call and in `--dry-run`. On an error, nothing is sent.

## Running the calls

```
python scripts/render.py hero --concept set-1/A --prompt concepts/set-1/A/prompts/hero.txt --ref input/refs/set-1/r01.jpg --ref input/refs/set-1/r02.jpg --dry-run
python scripts/render.py hero --concept set-1/A --prompt concepts/set-1/A/prompts/hero.txt --ref input/refs/set-1/r01.jpg --ref input/refs/set-1/r02.jpg
```

1. **Dry run** once first: lint, the request, the input images, the output names and where the key was found. It does not test the key.
2. **Cost.** Tell the user the count and time first: concepts × `candidates_per_concept` × `seconds_per_image` (`gates.py report ideas` prints it).
3. **Timing.** A 10-minute timeout, or run in the background. Sets run in parallel; show each set's board (`render.py sheet --set <set> --candidates`) when it is done. **Never start a second call for the same concept while one is running; files are numbered, so a duplicate costs money.**
4. **Results** land in `concepts/<set>/<concept>/renders/` as `hero-v<k>.png` with `.prompt.txt` and `.json`; never edit them. Look at every one.
5. Leave `--fidelity` out.
6. If both candidates fail review, one re-render round, after telling the user the cost.

## When a call fails

| What you see | What to do |
|---|---|
| exit 3, `R-API`, no key | Add `OPENAI_API_KEY=…` to `.env` in the project folder. The search goes upward and stops at a folder holding `.git` or at the home folder. Meanwhile, keep the prompts in `concepts/<set>/<concept>/prompts/hero.txt`, give the user the `--dry-run` lines, and bring images made elsewhere in with `render.py import`. |
| HTTP 401 | The key is wrong; replace it. |
| HTTP 403 or 404 | Retry once with `--model gpt-image-1`. |
| HTTP 400, content policy | Soften the wording once, lint again and retry. |
| HTTP 429 or 5xx | The script retries twice by itself, honouring `Retry-After` (capped at 120 s, else 20 s). If it still fails, retry once later. |

Carry on with the other concepts while one is stuck. A failed fix writes nothing, so its base stays the latest render.

## Choosing

1. Make tiles of the favoured candidate: `python scripts/render.py tiles concepts/set-1/A/renders/hero-v2.png`.
2. Review it as `review.md` describes, and record the review with `render.py review`. Use `--scope full` for the favoured candidate and `--scope whole` for the other.
3. Make the set's board: `python scripts/render.py sheet --set set-1 --candidates`.
4. In the concept.md front matter, write `chosen: renders/hero-v2.png`. Add a `blocked:` line for every file that must never be used.
5. Run `python scripts/gates.py renders`. It must pass.
6. Run `render.py sheet --set set-1 --chosen` for the parallel check, and `render.py sheet --chosen-all` for the overview.

**In `start` mode this is the only stop: show every set's candidate board and the overview, then wait for the user's `select` (`gates.py select`). In `step mode` stop after every step.**

## Fixing

```
python scripts/render.py fix --concept set-1/A --base concepts/set-1/A/renders/hero-v2.png --add "<one sentence>"
```

- One correction per call; the free-text rules apply. The fix becomes the next `hero-v<k>.png`.
- At most `fix_max` fixes in a chain (R-FIX-MAX); past that, take the other candidate or regenerate.
- Review every fix with `--scope full` before moving `chosen:` to it.
- A fix barely changes the scale of a stand: a size outside `size_tolerance` is regenerated, not fixed.
- `--base` must be a render of this concept (R-SOURCE): a reference can never be fixed into a render.

| Problem | Correction sentence |
|---|---|
| Too deep | The stand is only about [ratio in words] person-heights deep from the front edge to the back wall; bring the back wall forward and keep every design element. |
| Too wide | The platform is only about [ratio in words] person-heights wide; bring both side edges in and keep every design element. |
| Main form height | The top of [the main form] is about [ratio in words] times the height of a person; change its height only. |
| Extra structure | Remove the [ceiling / hanging banner / side room]; nothing else changes. |
| Wrong count | Show exactly [count in words] [items]; nothing else changes. |
| Painted marks (text, numbers, emblems, a drawn logo) | Clear the [place]: it becomes a plain [colour word] surface with nothing on it; nothing else changes. |
| Invented packs in product niches | The [niches] hold plain [colour word] blocks with nothing on them; nothing else changes. |

## Logo

The real logo goes on the plain panel of the chosen render. Use the official file, from `brief/brand/` or the deck-style `logo`:

```
python scripts/render.py logo concepts/set-1/A/renders/hero-v2.png --logo brief/brand/logo.png --quad "u1,v1 u2,v2 u3,v3 u4,v4"
```

- The quad is the panel's pixel corners: top-left, top-right, bottom-right, bottom-left. `--blend multiply` (default) suits a dark logo on a light panel, `normal` a light logo on a dark one.
- The output is the next render and inherits the base's review, plus a `composited_logo` mark.
- Without an official logo, keep the plain panel and tell the user.
- `render.py label` makes a stamped copy in `work/labelled/`; it is never used in the deck.

## Import

The same prompt and photos can go to another image tool:

1. Run the other tool with that prompt and those photos.
2. Bring each result in:

   ```
   python scripts/render.py import FILE --concept set-1/A --ref input/refs/set-1/r01.jpg --ref input/refs/set-1/r02.jpg --prompt concepts/set-1/A/prompts/hero.txt
   ```

3. Review the import like any render before it can be chosen.

A file with the same content as a reference photo or a client file is refused (R-SOURCE).
