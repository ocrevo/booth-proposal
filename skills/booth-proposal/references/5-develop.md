# Step 5 – Develop: derived from the idea, fixed by numbers

Only the concepts the user selected (`brief/selection.json`, written by `gates.py select`) are developed. The plan follows the concept: start from where the hero must stand to be seen from the main aisle, then place everything else to support it. An idea only counts once it fits at its real size, so every selected concept gets a **geometry spec**, `concepts/<set>/<concept>/geometry.json`, the single source of truth for its dimensions; the check, the plan and the massing all read it. Dimensions live in the geometry, never in the render, which was only judged by eye. Commands run from the project folder; `scripts/` is this skill's scripts folder.

## Order

```
python scripts/booth_geometry.py check concepts/set-1/A/geometry.json
python scripts/draw_plan.py plan concepts/set-1/A/geometry.json concepts/set-1/A/plan
python scripts/booth_geometry.py massing concepts/set-1/A/geometry.json concepts/set-1/A/massing
python scripts/booth_geometry.py facts concepts/set-1/A/geometry.json
python scripts/gates.py concepts
```

1. `check` until it ends in `RESULT: PASS`; fix warnings on the visitor path.
2. `draw_plan.py plan` draws `plan.png`, `plan.svg` and `plan.json`; the title and subtitle carry only the concept name, size, open sides and highest point (`--units m` by default). Look at the image: no label may overlap another label or the stand edge; a label with no free spot is shown by its number and listed in a key. The proposal's plan page uses its zone numbers.
3. `massing` makes `massing-hero.png` and `massing-front.png`, a white scaled model with a person for scale. It is internal: show it to the user in this step as a size check; never an image-model input, never in the proposal.
4. `facts` prints size, highest point, zones, program served and missing as JSON. Take every size or count you write in the proposal from it.
5. `gates.py concepts` checks every selected concept and writes nothing; `python scripts/gates.py report concepts` is what the user sees: the geometry result and plan path per concept.

## Spatial strategies (a vocabulary, not a template)

Open stage (hero seen from every aisle; little storage), pass-through (visitors walk through or under the hero; clear entry, exit, headroom), shelter (a calmer inner space; needs depth), sequence (a story told in order; cramped in small booths), object in space (one sculpture to circle; needs depth).

Note the visitor path in one line: entry, hero, discovery, conversation, exit. Size the idea as in 3-ideas.md `## Rough sizing`.

## Geometry

The format is in the docstring of `scripts/booth_geometry.py`; read it before writing a spec. In short: x from the left wall as seen from the main aisle, y from the back wall toward the aisle, z up; sizes `w` (along x), `h` (along y), `height` (along z), in the RFP's unit (`"m"` or `"ft"`). Shapes: box, cylinder, frame, extrusion; kinds: hero, zone, furniture, overhead. `repeat` writes a row of identical pieces as one element, `group` several pieces as one. The spec records size, not form; `render_hint` says in words what an element stands for in the chosen render (`booth_geometry.py hints` lists them), never as prompt text.

From the frame, every spec carries:

- `max_height`, `width`, `depth` as in the booth, `height_zones` and `rigging_allowed` where the venue has them, and `walkway` and `headroom` where it states them (they win over the default thresholds, which a project may override in `brief/deck-style.json` `thresholds`).
- `required`: the program, the same words as `booth.program` in brief.json. Every element that serves a program item names it in `program`.
- `support` for every overhead, frame and extrusion element (`floor`, `wall`, `legs`, `columns` or `hung`).
- `accent`: the concept's own colour `#RRGGBB` for the plan; the `accent:` line in the concept's front matter wins over it.
- `envelope_override`, only when the stand deliberately differs from the booth in brief.json: `[{"field": "max_height", "value": 5.0, "reason": "…"}]`, value in the spec's unit, a reason that says why. Without a matching override and a non-blank reason, `gates.py concepts` fails.

## When a check fails

A failed check means the design changes, not just the numbers: change the design, update the spec, and render the changed design again (a fix, or a new hero when the size changes a lot; review and choose again, 4-renders.md), so image, plan and text show the same stand.

- `GEO-FIT` (error), one rule each: `footprint` outside the platform; `height` above `max_height`; `headroom` frame opening too low; `profile` extrusion past its span; `zone-height` above a `height_zones` limit; `overlap` two floor elements overlap (separate them, or mark an enclosing element `contains`); `rigging` hung where the venue forbids it (use legs, columns or a wall). Change the design.
- `GEO-PROGRAM` rule `program` (error): a `required` item has no element. Add one, or drop the item and record why.
- `GEO-ADVICE` (warning): `walkway`, `underside`, `support`, `rigging-unconfirmed`, `span`, `noheight`. Fix the ones on the visitor path.
- `G-GEO` (error, from `gates.py concepts`): `missing` or `invalid` geometry.json; `check` has errors; `envelope` width or depth differs from the booth, or height is above it, beyond `geometry_tol` (correct the spec, or add an `envelope_override`); `plan` files missing, or `stale` because the spec changed after the plan was drawn: run `draw_plan.py plan` again.

## Content map

Content belongs in the architecture, not on posters added to it. For each selected concept, on the final geometry, ask how the hero can carry the most important content (dates on a sequence of frames, a number built into the counter), then place the rest by level (3-ideas.md, `## What the booth says`): L1 where the hero and brand are seen from the aisle, L2 at the invitation zone, L3 on discovery surfaces 1.0 to 2.0 m above the floor, L4 on screens, takeaways and QR codes. Keep half the visible surfaces free of text; if the content does not fit, cut content, not space.

```
| Surface | Level | Copy (draft) | From | Note |
| Hero: <element> | L1 | … | C3, C7 | carved / printed / light |
```

The map goes in the concept's notes in `concept.md`; it is internal and never written into an image prompt (a render shows plain surfaces where words will go; the proposal calls such a surface design intent). Beside it, note for each hard requirement whether the concept meets it (met, partly, not); the response table is built from these notes.

## Creative director review (optional)

After developing the selected concepts, switch roles: a demanding creative director who is hard to impress. Write two or three blunt sentences per concept about what is weak, generic or unresolved, then score it from 1 to 5:

| Criterion | Question |
| --- | --- |
| Insight | True and specific about this client and audience, with its source, or worded as our view? |
| Idea | Understood in three seconds, remembered tomorrow? |
| Specificity | Does it pass the no-swap test? |
| Emotion | Does it make people feel something? |
| Coherence | Do form, light, material and graphics all serve the idea? |
| Freshness | Would it stand out among competent booths? |
| Message | Is it clear what the booth says, the hero carrying the main content and most surfaces free of text? |
| Fit | Does it work at real size, with headroom and walkways? (`gates.py concepts` must pass.) |
| Craft | Proportions, details, finishes: would a top studio sign it? |

Below 4 on Insight, Idea or Specificity: rebuild from a new insight, not patch; other criteria below 4 are revised, and a reshaped concept is rendered again. Write the result in the concept's notes in `concept.md` (never parsed); show the user one line per concept, scores only if asked. It never reaches the proposal. Empty words ("high-end", "cutting-edge", "immersive") without saying how fail Specificity. The render critique is in review.md.

## Without code

Write the spec anyway, check the dimension sums by hand, and use an ASCII plan: top row = back, bottom row = main aisle, one cell = 0.5 m or 2 ft, `#` closed wall, `.` open side, letters for zones, a legend underneath.
