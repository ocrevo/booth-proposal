# Review

## Image review

A render reaches the proposal only after a reviewer has looked at it without knowing what it was meant to be. Code records the answer, works out the size deviation and computes the verdict.

### When

- Review every candidate with `--scope whole`: the whole image.
- Review with `--scope full` the candidate you mean to choose, and every fix or import that may be chosen. A full review covers the whole image and then every tile.
- Only a current review with `full` scope and a `pass` verdict lets a render be chosen (G-REVIEW). A review is current while the image is unchanged; after any change, review the image again.

### What the reviewer gets

Make the tiles first: `python scripts/render.py tiles concepts/set-1/A/renders/hero-v2.png`. With the default 3x2 grid, they go to `work/tiles/set-1/A/hero-v2/` as `r1c1.png` … `r2c3.png`.

**The reviewer gets** the image and its tiles, the booth's width, depth and height (metres and person-heights), the open sides and the function list, `brief.booth.program`.

**The reviewer never gets** the prompt, the concept name or text, or the reference photos.

**Who reviews:** a fresh subagent. When no subagent is available, review in a new turn yourself, record it with `--reviewer self`, and tell the user. When the user reviews the image, record their answer with `--reviewer user`.

### Reviewer brief

Fill the brackets from brief.json, and pass the brief to the reviewer as it stands:

```
You are reviewing one concept render of an exhibition stand for a design proposal. You see only the image and its tiles. You do not know the brief, the prompt or the idea; do not guess them.
Booth: [W] m wide, [D] m deep, at most [H] m high. One person is about [person_height_m] m, so the platform should read about [w] person-heights wide and [d] deep, and nothing should rise above about [h] person-heights. Open sides: [sides]. Functions that should be visible: [program].
1. Marks. Look at the whole image, then at every tile. List every mark, with a type from this list only: legible_text, number, name, logo_like, emblem, pseudo_text_legible, pseudo_text, venue_background. Use pseudo_text_legible when a viewer of the whole image at slide size would read it as letters or characters; pseudo_text when it only reads as texture. A blurred hall sign behind the stand is venue_background. For each mark give where (a tile name such as r1c2, or whole) and a short note.
2. Size. With the people as the scale, estimate the stand's width, its depth and the height of its tallest element, in person-heights, to one decimal.
3. Premium. Would this image hold the cover of a top studio's proposal? Answer yes or no, then one sentence. Ask yourself: Is one main form carried fully while everything else stays quiet? Are the functions folded into the main form rather than scattered as furniture? Is the plain logo panel the only place a brand would go? Is the light restrained rather than every edge lit? Is the counter clear? Does it avoid the interchangeable minimal look, white walls, pale wood and a cove of light that could belong to any brand?
4. Verdict. pass or fail, and two sentences on why.
Answer only with JSON: {"marks": [{"type": "", "where": "", "note": ""}], "observed": {"w": 0.0, "d": 0.0, "h": 0.0}, "premium": "yes", "verdict": "pass", "notes": ""}
```

### Recording

Record the answer as it came back:

```
python scripts/render.py review concepts/set-1/A/renders/hero-v2.png --reviewer subagent --verdict pass --premium yes --scope full --size-json '{"observed": {"w": 4.4, "d": 3.3, "h": 2.5}}' --marks-json '[{"type": "pseudo_text", "where": "r1c3", "note": "soft texture on the counter front"}]' --notes "One calm gate; the lounge reads clearly."
```

`marks` goes to `--marks-json` (inline JSON, a file, or `-` for stdin; `[]` when none), `observed` to `--size-json '{"observed": {...}}'`, and `premium`, `verdict`, `notes` to the flags of the same name. When `expected` is left out, code takes it from the booth in brief.json, divided by `person_height_m`.

Code writes `<stem>.review.json` next to the image, with the deviation, `within` and the verdict: `pass` only when the reviewer said pass and the three hard gates below hold. The script prints the verdict; on a fail it exits 1 with R-REVIEW and still writes the file.

| Mark type | Class | Effect |
|---|---|---|
| `legible_text` | fail | verdict fail |
| `number` | fail | verdict fail |
| `name` | fail | verdict fail |
| `logo_like` | fail | verdict fail |
| `emblem` | fail | verdict fail |
| `pseudo_text_legible` | fail | verdict fail |
| `pseudo_text` | record | none |
| `venue_background` | record | none |
| `composited_logo` | allow | none, only on the output of `render.py logo` with an official logo file; anywhere else it counts as `logo_like` |

The output of `render.py logo` inherits the base's review plus a `composited_logo` mark; review it again only when the composite covered more than the plain panel.

### Three hard gates

1. **Clean image.** No fail-class mark.
2. **True size.** Width and depth each within `size_tolerance` (about 20 %) of the booth, above or below; height not above the booth height by more than `size_tolerance` (the booth height is a cap, so a lower stand is fine).
3. **Premium.** The reviewer answers yes.

**Between passing candidates,** take the one whose idea reads most clearly, that is more premium, and that differs more from the set's other concepts.

**If none of the candidates passes:** tell the user what one more round costs, then make one new round. If that fails too, offer the closest candidate and say what is off. A render that has not passed cannot be chosen.

## Premium questions

Item 3 of the reviewer brief. They are for review only, never for prompts.

## Side by side

After choosing, run `python scripts/render.py sheet --set <set> --chosen`: the set's chosen renders side by side. No two may share the same counter, seating and back wall, or the same outline; if two read as the same stand, push the weaker idea further and render it again. Show the row to the user.

## Proposal review

### When

Once every page is filled:

1. `python scripts/deck.py check`, then `python scripts/deck.py render`. Fix until render reports zero overflow.
2. Pass 1, then Pass 2 (below), then `python scripts/deck.py review --record work/deck-review.input.json`.
3. `python scripts/deck.py export`. When check now reports D-REF `stale`, run `deck.py render` first: coverage quotes decide which pages a design-point reference names.

Export refuses while check has errors, the render is missing, stale or shows overflow, or the record is missing, stale, holds an unresolved pass-2 finding or a pending word without `keep`.

The record holds a hash of each page's `deck.py text` block and of its images. Layout-only edits, such as a class or a style, keep the record. After a text or image change, run `python scripts/deck.py text --diff`: it lists the pages `ADDED`, `REMOVED` and `CHANGED` since the record and prints only those. Review them again in both passes; a changed page loses its recorded items, coverage quotes and pending decisions included.

### Pass 1

Cold read, text only. The reviewer reads the deck as the client will. They get only:
- the output of `python scripts/deck.py text`;
- the design points as `id: text` lines, without sources;
- the pending findings of `deck.py check` as code, page and word, for example `D-TXT-PENDING b-board "builds on"`.

They never get the images, the brief, the references or the notes.

Their answer fills four lists in `pass1`:
- `unexplained`: a reference or comparison with nothing earlier in the deck to point to ("as before", "the familiar arch"). Each item is `{page_id, quote, action}`, with `action` `rewritten` or `kept`.
- `internal_notes`: working notes, IDs, file names, anything meant for the team. Same shape.
- `coverage`: one item per design point, `{point, page_id, quote}`, the quote copied verbatim from that page's text block.
- `pending`: one item per pending finding, `{code, page_id, text, decision, note}`, with `text` the word as check prints it. `narrates_reference`: the word tells the story of a reference or an earlier stand; rewrite the page so the word is gone. `keep`: brand language. Example: "延续品牌蓝" → `keep`; "延续上一届的造型" → `narrates_reference`.

### Pass 2

Images against words. The reviewer gets `work/contact.png`, each placed render's `.review.json`, the output of `deck.py text`, and `python scripts/booth_geometry.py facts concepts/<set>/<concept>/geometry.json` for each selected concept.

They check that the words describe what is visible (what the image does not show is worded as design intent); counts, names and positions match the image and the facts; titles are claims, not labels; the cover uses the strongest image; adjacent pages differ in layout; each page has one hero.

Their answer fills `pass2.findings`, each `{page_id, kind, note, resolved}`. `kind` is one of `mismatch`, `design_intent`, `title_is_label`, `cover`, `adjacent_layout`, `other`. Fix what you can and set `resolved` to `true`; an item left `false` blocks export.

### Recording

Write both answers to `work/deck-review.input.json`:

```json
{
  "pass1": {
    "reviewer": "subagent",
    "unexplained": [{"page_id": "b-board", "quote": "As before, the lounge faces the aisle.", "action": "rewritten"}],
    "internal_notes": [],
    "coverage": [
      {"point": "D1", "page_id": "a-board", "quote": "A deck you walk onto from two sides."},
      {"point": "D2", "page_id": "b-annotated", "quote": "Tidewater Pass holders check in at the bow counter."}
    ],
    "pending": [{"code": "D-TXT-PENDING", "page_id": "b-board", "text": "builds on", "decision": "keep",
                 "note": "Nordvik Ferries harbour blue: brand language."}]
  },
  "pass2": {
    "reviewer": "subagent",
    "findings": [
      {"page_id": "a-board", "kind": "mismatch", "note": "Text said four kiosks; image and facts show three.", "resolved": true}
    ]
  }
}
```

Then run `python scripts/deck.py review --record work/deck-review.input.json`.

- **Exit 2** (`C-INPUT`): the input does not match the shape. The message gives the JSON path.
- **Exit 1**: nothing was written. Each `error:` line is a coverage quote not found on its page, a pending word without a decision, or a page that still contains a word decided `narrates_reference`. Fix the input or the page and record again.
- **Exit 0**: code writes `work/deck-review.json`, stamped with every page's hashes and the time. Only code writes hashes and times.

Recording again merges: an old item stays while its page is unchanged and no new item of the same list names that page. An input may therefore hold only `pass2`.

### Without a subagent

Run pass 1 yourself in a fresh turn, with only its inputs. Do not re-open the references. Record it with `"reviewer": "self"` and tell the user the cold read was not independent.

### What the user sees

Show the pass-2 findings with `work/contact.png`: for each, the page, what was wrong and whether it is resolved.
