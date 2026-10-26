# Spatial plan and geometry – derived from the idea, locked by numbers

The plan follows the concept: start from where the hero must stand to be seen from the main aisle, then place everything else to support it. But an idea only counts once it fits at its real size. Image models do not respect dimensions written in words, so every concept gets a **geometry spec**: one JSON file that is the single source of truth for its dimensions. The plan drawing, the geometry check and the massing images that lock the renders are all made from it. The frame card (references/frame.md) supplies its limits and its required program.

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

The full format is in the docstring of scripts/booth_geometry.py. In short: x from the left wall as seen from the main aisle, y from the back wall toward the aisle, z up from the floor, sizes w (along x), h (along y) and height (along z), in the RFP's unit (`"unit": "m"` or `"ft"`). Shapes: box, cylinder, frame (a portal) and extrusion (a curved or stepped surface given by a profile, for shells, canopies, vaults and steps). Kinds: hero, zone, furniture, overhead, structure.

From the frame card, every spec carries: `max_height`, any `height_zones`, `rigging_allowed`, the venue's `walkway` and `headroom` if stated, and `required` (the program). Every element that serves a program item names it in `program`; every overhead, frame or extrusion element states its `support`. The check then proves the concept holds the whole program, respects every height rule, and does not hang anything the venue forbids.

Then run, in this order:

1. `python scripts/booth_geometry.py check spec.json` – must end in `RESULT: PASS`. An error means the design does not fit: change the design (not the numbers in the prompt) and run it again. Read the warnings and fix the ones that matter (narrow passages on the main visitor path).
2. `python scripts/draw_plan.py spec.json plan` – the plan drawing for the pitch.
3. `python scripts/booth_geometry.py massing spec.json massing` – two white massing images (`massing-hero.png`, `massing-front.png`) from the cameras of View 1 and View 2, with a 1.75 m person for scale. They become the geometry reference for the renders.

Only when no code can run: write the spec anyway, do the check by hand (list each dimension sum), and use an ASCII plan (top row = back, bottom row = main aisle, one cell = 0.5 m or 2 ft, `#` closed wall, `.` open side, letters for zones, legend underneath).

## The plan record (appendix and changes)

```
PLAN <A/B/C> · v1 · Concept: <name> · Strategy: <…>
Built from: Requirement v<n>, assumptions <IDs> · Geometry spec: <file>, check PASS on <date>
Hero: <element, position, size, height>
Visitor path: <entry → hero → discovery → conversation → exit>
| Zone | Position (x, y) | Size (w × h × height) | Serves |
```
