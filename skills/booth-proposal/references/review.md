# Review

The deck review follows in phase 3.

## Image review

A render reaches the proposal only after a reviewer has looked at it without knowing what it was meant to be. Code records the answer, works out the size deviation and computes the verdict.

### When

- Review every candidate with `--scope whole`: the whole image.
- Review with `--scope full` the candidate you mean to choose, and every fix or import that may be chosen. A full review covers the whole image and then every tile.
- Only a current review with `full` scope and a `pass` verdict lets a render be chosen (G-REVIEW). A review is current while the image is unchanged; after any change, review the image again.

### What the reviewer gets

Make the tiles first: `python scripts/render.py tiles concepts/set-1/A/renders/hero-v2.png`. With the default 3x2 grid, they go to `work/tiles/set-1/A/hero-v2/` as `r1c1.png` … `r2c3.png`.

**The reviewer gets:**
- the image;
- its tiles;
- the booth's width, depth and height, in metres and in person-heights;
- the open sides;
- the function list, `brief.booth.program`.

**The reviewer never gets** the prompt, the concept name or text, or the reference photos.

**Who reviews:** a fresh subagent. When no subagent is available, review in a new turn yourself, record it with `--reviewer self`, and tell the user.

### Reviewer brief

Fill the brackets from brief.json, and pass the brief to the reviewer as it stands:

```
You are reviewing one concept render of an exhibition stand for a design proposal. You see only the image and its tiles. You do not know the brief, the prompt or the idea; do not guess them.
Booth: [W] m wide, [D] m deep, at most [H] m high. One person is about [person_height_m] m, so the platform should read about [w] person-heights wide and [d] deep, and nothing should rise above about [h] person-heights. Open sides: [sides]. Functions that should be visible: [program].
1. Marks. Look at the whole image, then at every tile. List every mark, with a type from this list only: legible_text, number, name, logo_like, emblem, pseudo_text_legible, pseudo_text, venue_background. Use pseudo_text_legible when a viewer of the whole image at slide size would read it as letters or characters; pseudo_text when it only reads as texture. A blurred hall sign behind the stand is venue_background. For each mark give where (a tile name such as r1c2, or whole) and a short note.
2. Size. With the people as the scale, estimate the stand's width, its depth and the height of its tallest element, in person-heights, to one decimal.
3. Premium. Would this image hold the cover of a top studio's proposal? Answer yes or no, then one sentence. Ask yourself: Is one main form carried fully while everything else stays quiet? Are the functions folded into the main form rather than scattered as furniture? Is the plain logo panel the only place a brand would go? Is the light restrained rather than every edge lit? Is the counter clear?
4. Verdict. pass or fail, and two sentences on why.
Answer only with JSON: {"marks": [{"type": "", "where": "", "note": ""}], "observed": {"w": 0.0, "d": 0.0, "h": 0.0}, "premium": "yes", "verdict": "pass", "notes": ""}
```

### Recording

Record the answer as it came back:

```
python scripts/render.py review concepts/set-1/A/renders/hero-v2.png --reviewer subagent --verdict pass --premium yes --scope full --size-json '{"observed": {"w": 4.4, "d": 3.3, "h": 2.5}}' --marks-json '[{"type": "pseudo_text", "where": "r1c3", "note": "soft texture on the counter front"}]' --notes "One calm gate; the lounge reads clearly."
```

How the answer maps onto the command:

| Answer field | Flag |
|---|---|
| `marks` | `--marks-json` (inline JSON, a file, or `-` for stdin; `[]` when there are none) |
| `observed` | `--size-json '{"observed": {...}}'` |
| `premium` | `--premium` |
| `verdict` | `--verdict` |
| `notes` | `--notes` |

When `expected` is left out, code takes it from the booth in brief.json, divided by `person_height_m`.

Code then writes `<stem>.review.json` next to the image, with the deviation, `within` and the verdict. The verdict is `pass` only when all four of these hold:
- the reviewer said pass;
- there is no fail-class mark;
- the size is within tolerance (width and depth either way, height only when above the cap);
- the image is premium.

The script prints that verdict. On a fail it exits 1 with R-REVIEW, and still writes the file.

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

The output of `render.py logo` inherits the base's review, with an added `composited_logo` mark. Review it again only when the composite covered more than the plain panel.

### Three hard gates

1. **Clean image.** No fail-class mark.
2. **True size.** Width and depth each within `size_tolerance` (about 20 %) of the booth, above or below; height not above the booth height by more than `size_tolerance` (the booth height is a cap, so a lower stand is fine).
3. **Premium.** The reviewer answers yes.

**Between two passing candidates,** take the one where:
- the idea reads most clearly;
- the image is more premium;
- the stand differs more from the set's other concepts.

**If both candidates fail:**
1. Tell the user what one more round costs, then make one new round.
2. If that round fails too, offer the closest candidate and say what is off.
3. A render that has not passed cannot be chosen until it passes.

### Parallel check per set

After choosing, run `python scripts/render.py sheet --set <set> --chosen`. It lays the set's chosen renders side by side.

- No two chosen renders of one set may share the same counter, seating and back wall.
- If two read as the same stand, push the weaker idea further and render it again.
- Show the row to the user.
