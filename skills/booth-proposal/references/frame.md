# The frame – constraints first in thinking

Great design comes from working with constraints, not around them. So constraints are settled before any idea is drawn: they define the playing field, and ideas are then free inside it. The user never has to read this; it works underneath the concepts and appears only in the appendix.

**Constraints first in thinking, design first in showing.**

## Four tiers of constraint

| Tier | What | Examples | How it is handled |
| --- | --- | --- | --- |
| 1 Hard | Rules the stand cannot break | Footprint, height limits (including height zones), open sides, venue safety (headroom, walkways, fire, rigging), RFP must-haves, dates | Enforced by the geometry check and the compliance table. A breach means redesign. |
| 2 Program | What the stand must hold and do, with real sizes | Screen, counter, coffee service, storage, seating, products, kiosk, staff, services (power, water, data) | Sized from the table below, placed in every concept, checked through `required` and `program` in the geometry spec. |
| 3 Brand and content | What the client owns and requires | Brand guidelines (colours, fonts, logo rules), mandatory messages, imagery rules, claims needing approval | Respected in every concept; creative interpretation allowed, contradiction not. |
| 4 Aspiration | What inspires | Theme, references the client likes, the insight, the design territories | Interpreted freely. |

**Order of authority** when two things conflict: tier 1, then 2, then 3, then 4, then the designer's own preference. A beautiful idea that breaks a tier-1 rule is changed; a reference the client loves that conflicts with their brand guidelines yields to the guidelines. Record every such decision in the appendix.

Some items look like constraints but are choices the brief leaves open (for example "double or triple open" or any height up to the limit). Treat them as design freedom, and say which option each concept chose.

## Program sizes (rules of thumb)

Typical values to start from; the designer and suppliers confirm them. Use feet where the brief uses feet.

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

## Two budgets to run before ideation

**Area budget.** Add up the program's footprints including the space each needs around it, and compare with the floor area. If the program takes more than about 60–65 % of the floor, there is no room for a separate hero: the hero must carry a function (the counter becomes the sculpture, the screen sits inside the hero wall), or the program shrinks, recorded as an assumption.

**Depth budget** (the shallow direction). List what sits one behind another, for example back display 0.3 + viewing 0.8 + furniture 0.8 + walkway 0.9 + counter 0.6 = 3.4 m. If the sum exceeds the depth, some elements move to the side, combine or go. Do this before any concept, so every idea starts from what is possible.

## Height zones and rigging

- Many shows limit heights by zone. For example, many US shows follow line-of-sight guidelines for inline booths, with a lower limit in the front part of the booth than at the back wall. Put any such rule into `height_zones` in the geometry spec; when the exhibitor manual is missing, record the assumption.
- Hanging structures need venue approval. If rigging is not confirmed, every element must stand on the floor or the stand's own structure, and the geometry spec says how each overhead element is supported.

## The frame card

Write this in step 2, before ideation. The user sees it only on `show frame` and in the appendix. It lives in `brief/frame.md` with the other fact cards and is reused across runs: a new run copies it instead of redoing it, and changes only what a changed fact affects.

```
FRAME · v1 · <project>
Footprint: <W × D> (<area>), <booth type>, open sides: <allowed options and the assumption>, main aisle: <side>
Height: max <H>; height zones: <none / list>; rigging: <allowed / not allowed / not confirmed>
Program (tier 2)
| Item | From | Size used | Space around | Notes |
| screen | R6 | 75" (1.66 × 0.93 m) | viewing 1.5 m | wall-mounted |
Services: power <…>, water <…>, data <…>
Area budget: program needs <x> of <y> m² (<z> %) → <room for a separate hero / hero must carry a function>
Depth budget: <layers> = <sum> of <depth> → <fits / what must move to the side>
Brand rules (tier 3): <colours, fonts, logo rules, imagery rules>
Design freedom: <choices the brief leaves open>
```

The program table also gives the one-line program in each View 1 prompt (references/image-prompts.md), and the `required` list in every geometry spec, so the check proves each concept holds the whole program.
