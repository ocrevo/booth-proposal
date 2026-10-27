# Step 2 – Frame: constraints first in thinking

Constraints are settled before any idea is drawn; ideas are then free inside them. The frame works underneath the concepts; the user sees the booth in three lines. Commands run from the project folder; `scripts/` is this skill's scripts folder.

## Four tiers of constraint

| Tier | What | How it is handled |
| --- | --- | --- |
| 1 Hard | Rules the stand cannot break | Enforced by the geometry check and the response table. A breach means redesign. |
| 2 Program | What the stand must hold and do, with real sizes | Sized from the table below, placed in every concept, checked through `required` and `program` in the geometry spec. |
| 3 Brand and content | What the client owns and requires | Respected in every concept; interpretation allowed, contradiction not. |
| 4 Aspiration | What inspires | Interpreted freely. |

**Order of authority** when two things conflict: tier 1, 2, 3, 4, then the designer's own preference. A beautiful idea that breaks a tier-1 rule is changed; a reference the client loves yields to their brand guidelines. Record every such decision in the frame notes. Choices the brief leaves open ("double or triple open", any height up to the limit) are design freedom; say which option each concept chose.

## Program sizes (rules of thumb)

Typical values to start from; suppliers confirm them. Use feet where the brief uses feet.

| Element | Typical size | Space it needs around it |
| --- | --- | --- |
| Reception or info counter | 1.2–2.0 m long, 0.5–0.6 m deep, 1.0–1.1 m high | 0.7–0.9 m behind for staff |
| Coffee service | Counter 1.5–2.0 m with machine and cups; water (tank or supply), waste, often a dedicated power circuit | Staff space behind; queue space in front |
| Storage | About 1 m² lockable in small stands; more for catering or giveaways. Under-counter storage can suffice for small quantities restocked daily | Door swing or access side |
| Large screen | 65": 1.44 × 0.81 m · 75": 1.66 × 0.93 m · 86": 1.90 × 1.07 m; centre about 1.6–1.9 m high | Viewing distance in front |
| Touch kiosk | About 0.6 × 0.4 m footprint, 1.8–2.0 m high | 0.8–1.0 m clear in front |
| Seated lounge | Table 0.6–0.8 m with 2–3 chairs: about 2.0 × 2.0 m in total | Access from one side |
| High table | 0.6–0.8 m diameter, 1.05–1.1 m high | About 1.2 m diameter zone |
| Product plinth or niche | Plinth 0.4–0.6 m square, 0.9–1.1 m high; niche centre 1.2–1.6 m high | 0.8 m to view |
| Staff | About 1 m² standing zone per person | — |
| Main walkway | 0.9 m minimum (3 ft); about 1.2 m for two people passing | — |
| Headroom | 2.1 m minimum (7 ft) under anything people walk beneath, unless the venue states more | — |

Sizes serve the budgets and the geometry spec; outside the Size lines they never go into a prompt as numbers (`L-BAN` `digit`).

## Two budgets to run before ideation

**Area budget.** Add up the program's footprints with the space each needs around it and compare with the floor area. Above about 60–65 % of the floor there is no room for a separate hero: the hero must carry a function (the counter becomes the sculpture), or the program shrinks, recorded as an assumption.

**Depth budget** (the shallow direction). List what sits one behind another, for example back display 0.3 + viewing 0.8 + furniture 0.8 + walkway 0.9 + counter 0.6 = 3.4 m. If the sum exceeds the depth, some elements move to the side, combine or go. Do this before any concept.

## Height zones and rigging

- Many shows limit heights by zone (line-of-sight rules allow less height at the front than at the back wall). `brief.json booth` has no zone field: write zones in the frame notes, and in step 5 into each geometry spec as `height_zones`. Without the exhibitor manual, record an assumption.
- Hanging structures need venue approval. `booth.rigging_allowed` is `true`, `false`, or `null` for not confirmed. If rigging is not confirmed, every element stands on the floor or the stand's own structure, and the geometry spec says how each overhead element is supported.

## Frame notes

Write them in step 2, before ideation, in `brief/frame.md` (notes, never parsed; reused across runs). The booth itself is data: `brief.json booth` with `booth.program`, the list of program words that becomes `required` in every geometry spec and is the function list the image reviewer receives.

```
Main aisle and open sides (with the assumption) · Height zones (with the source)
Program (tier 2): | Item | From (quote the source text) | Size used | Space around | Notes |
Services: power, water, data
Area budget: needs <x> of <y> m² (<z> %) → <room for a separate hero / hero must carry a function>
Depth budget: <layers> = <sum> of <depth> → <fits / what moves to the side>
Brand rules (tier 3) · Design freedom (choices the brief leaves open)
```

The program table gives the Essentials block of each hero prompt (4-renders.md) and `booth.program`, so the geometry check can prove each concept holds it all.

## Check and show

```
python scripts/gates.py frame
```

It checks the `booth` block only (`unit`, positive `width`, `depth`, `max_height`, valid `open_sides`, a `source`, `rigging_allowed` true, false or null, `program` a list of strings). A problem is `G-BRIEF`, rule `booth:`, exit 1. The budgets are your work.

Show the user the booth in three lines: size and height, open sides, rigging (allowed, not allowed or not confirmed). If the budgets show the program barely fits, add one line: the hero must carry a function. Then go on to the ideas (3-ideas.md) unless in `step mode`.
