# Spatial plan and geometry – derived from the idea, fixed by numbers

The plan follows the concept: start from where the hero must stand to be seen from the main aisle, then place everything else to support it. But an idea only counts once it fits at its real size, so every concept gets a **geometry spec**: one JSON file that is the single source of truth for its dimensions. The geometry check, the plan drawing and the appendix massing images all read it. The frame card (references/frame.md) supplies its limits and its required program.

The spec is written in Develop, after the renders: it takes the design of the chosen View 1 and fixes it at its real size. The renders are never generated from the spec; they were checked by eye, with the people as the scale (references/image-prompts.md). If the check fails, the design changes and is rendered again (a fix or a new View 1, then View 2 made again from it and both re-stamped), so image, plan and text always show the same stand.

## Spatial strategies (a vocabulary, not a template)

| Strategy | Use when the idea needs… | Watch out |
| --- | --- | --- |
| Open stage | Maximum visibility; the hero seen from every aisle | Little storage and few walls |
| Pass-through | Visitors to walk through or under the hero | Clear entry, exit and headroom |
| Shelter | A protected, calmer inner space (meetings, hospitality) | Depth for both shelter and display |
| Sequence | A story told in order (history, process) | Can feel cramped in small booths |
| Object in space | One sculptural object the space revolves around | Shallow inline booths leave no room to circle it |

## Size the idea before drawing it

The area and depth budgets in the frame card come first (references/frame.md). Then put numbers on the idea itself while it is still a sketch:

- **Repeated elements:** count × size × spacing, along a stated direction, must fit that dimension of the footprint. Six steps of 0.7 m in the depth direction need 4.2 m and cannot fit a 3 m deep booth; run them along the width, or use fewer or shallower steps.
- **Depth budget:** in shallow booths, add up what sits one behind another (back display + walkway + furniture + walkway + counter). If the sum exceeds the depth, move an element to the side or drop it.
- **Headroom:** anything people walk under keeps at least about 2.1 m clear.
- **Walkways:** keep main passages about 0.9 m or wider; check local accessibility rules.
- **Height:** the tallest point stays within the brief's limit; state the design height you chose.

## The geometry spec

The full format is in the docstring of scripts/booth_geometry.py. In short: x from the left wall as seen from the main aisle, y from the back wall toward the aisle, z up from the floor, sizes w (along x), h (along y) and height (along z), in the RFP's unit (`"unit": "m"` or `"ft"`). Shapes: box, cylinder, frame (a portal) and extrusion (a curved or stepped surface given by a `profile` along `axis` "x" or "y", for shells, canopies, vaults, ribbons and steps). Kinds: hero, zone, furniture, overhead (any other word, such as brand, is treated as a plain element). `repeat` writes a row of identical pieces (fins, steps, columns) as one element.

The spec records size, not form. A ridge, a ribbon or a field of discs is written as the boxes or profile that bound it; `group` makes several pieces one compound element for the check, and `render_hint` says in words what the pieces stand for – the form seen in the chosen render – so the plan, the massing and the render can be read together (`python scripts/booth_geometry.py hints spec.json` lists them). It is a note, not a prompt.

From the frame card, every spec carries: `max_height`, any `height_zones`, `rigging_allowed`, the venue's `walkway` and `headroom` if stated, and `required` (the program). Every element that serves a program item names it in `program`; every overhead, frame or extrusion element states its `support`. The check then proves the concept holds the whole program, respects every height rule, and does not hang anything the venue forbids.

Then run, in this order:

1. `python scripts/booth_geometry.py check spec.json` – must end in `RESULT: PASS`. An error means the design does not fit: change the design, not just the numbers, run the check again, and render the changed design again (`render.py fix`, or a new View 1 if the size changes a lot), then make View 2 again from the new View 1 (`render.py front`) and re-stamp both (`render.py label`). Read the warnings and fix the ones that matter (narrow passages on the main visitor path).
2. `python scripts/draw_plan.py spec.json plan` – the plan drawing for the pitch (`plan.png` and `plan.svg`).
3. `python scripts/booth_geometry.py massing spec.json massing` – two white massing images (`massing-hero.png`, `massing-front.png`) with a 1.75 m person for scale, for the appendix only. They document the sizes; they are never sent to an image model.

Only when no code can run: write the spec anyway, do the check by hand (list each dimension sum), and use an ASCII plan (top row = back, bottom row = main aisle, one cell = 0.5 m or 2 ft, `#` closed wall, `.` open side, letters for zones, legend underneath).

## The plan record (appendix and changes)

```
PLAN <A/B/C> · v1 · Concept: <name> · Strategy: <…>
Built from: Requirement v<n>, assumptions <IDs>, chosen render <file> · Geometry spec: <file>, check PASS on <date>
Hero: <element, position, size, height>
Visitor path: <entry → hero → discovery → conversation → exit>
| Zone | Position (x, y) | Size (w × h × height) | Serves |
```
