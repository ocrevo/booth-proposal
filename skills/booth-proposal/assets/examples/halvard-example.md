# Worked example – Halvard Instruments at LabWorld Europe 2027

> FICTIONAL EXAMPLE. The client, the event and every fact are invented (see halvard-rfp.md). It shows the expected depth and order of the work; it is not a template to copy.

Files next to this one: halvard-rfp.md (the brief), halvard-geometry-A.json (geometry spec of concept A), halvard-plan-A.png, halvard-massing-A-hero.png and halvard-massing-A-front.png (appendix only).

Order of the work: Brief → Frame → Ideas → Visualise (fast start) → Develop → Pitch pack.

---

## Part 1 – The work in order (the cards are shown to the user only on `show` and in the appendix)

### Requirement card (excerpt)

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | 6 m × 4 m corner stand, open on the front and right aisles | §3 |
| R2 | Maximum height 4.5 m | §3 |
| R3 | No hanging structures | §3 |
| R4 | Display the A75 balance, the PX-8 pipetting system and the LH-400 liquid handler | §4.2 |
| R5 | At least one 75-inch screen | §4.3 |
| R6 | Demonstration bench for live pipetting demos | §4.4 |
| R7 | Seated meeting area for four | §4.5 |
| R8 | Coffee bar throughout the show | §4.6 |
| R9 | Lockable storage of at least 1.5 m² | §4.7 |
| R10 | Four staff on the stand | §4.8 |
| R11 | Follow the Halvard brand guidelines | §4.9 |
| P1 | Theme: 75 years of Halvard precision | §4.1 |

Deliverables: D1 concept, renderings and plan (covered) · D2 graphic concept (partly: content map) · D3 build schedule and D4 itemised price (not covered, handled separately).

| ID | Assumption | Basis | Impact |
| --- | --- | --- | --- |
| A1 | The front aisle is the main aisle | The RFP names two aisles but not which is busier | High |
| A2 | Brand colours Halvard Green #0F4D3A and white, geometric sans-serif | Guidelines are mentioned but not attached; values taken from §1 | High |
| A3 | Coffee is made on the stand with a water tank | No water connection mentioned | Medium |

### Frame card

```
FRAME · v1 · Halvard · LabWorld Europe 2027
Footprint: 6 × 4 m (24 m²), corner, open front + right, main aisle front (A1)
Height: max 4.5 m · no height zones · rigging not allowed (R3)
Program (tier 2)
| Item     | From | Size used                  | Space around        |
| storage  | R9   | 1.8 × 1.0 m (1.8 m²)       | door on the front   |
| screen   | R5   | 75" (1.66 × 0.93 m)        | viewing 1.5 m       |
| products | R4   | vitrine 3.0 × 0.6 m        | 0.9 m to view       |
| demo     | R6   | bench 1.6 × 0.7 m          | staff + 2 visitors  |
| meeting  | R7   | table 1.0 m + 4 chairs     | about 2.2 × 2.2 m   |
| coffee   | R8   | counter 0.6 × 1.2 m        | queue on the aisle  |
| staff    | R10  | 4 people, about 1 m² each  | —                   |
Area budget: about 15 of 24 m² (63 %) → no room for a separate hero; the hero must live on a wall or carry a function
Depth budget: back hero 0.3 + viewing 1.0 + vitrine 0.6 + walkway 1.1 + bench 0.7 + 0.3 = 4.0 m → fits exactly
Brand rules (tier 3): Halvard Green and white; geometric sans-serif; claims C2 and C3 need sign-off
Design freedom: hero form, materials, which wall carries the hero
```

### Content (excerpt)

| ID | Type | Text | Source | Flags |
| --- | --- | --- | --- | --- |
| C1 | story | Founded in 1952 as a two-person workshop making laboratory balances | §1 | number |
| C2 | proof | 1981: the first fully automated pipetting robot in Europe | §1 | superlative |
| C3 | proof | Instruments in daily use in more than 40 countries | §1 | number · dated |
| C4 | proof | Every balance is calibrated by hand before it leaves the factory | §1 | — |
| C5 | brand line | "Precision you can trust." | §1 | — |

Message platform: headline options "75 years of precision you can trust" (C1, C5), "Calibrated by hand since 1952" (edited from C1, C4), "One standard since 1952" (edited from C1). Key messages: 1952 (C1) · Europe's first automated pipetting robot, 1981 (C2) · in labs in 40+ countries (C3). Sign-off: C2, C3.

### Ideas considered

| Idea | Territory | Result |
| --- | --- | --- |
| Seventy-Five: 75 fins rising in one even curve | Architectural | Chosen (A) |
| The Calibration Room: a calm, glowing translucent room | Light and atmosphere | Chosen (B) |
| Green Stone: honed green stone worked like an instrument | Material and craft | Chosen (C) |
| A giant balance sculpture | Architectural | Rejected: the product as a prop is literal and seen at every fair |
| A photo timeline wall | Graphic | Rejected: a nostalgic collage, on the cliché list |
| A robot-arm show | Media | Rejected: fails the no-swap test; every automation brand does it |

No reference images came with this RFP, so there is no style card and the prompts have no reference line. Had the client sent photos of its previous stand, they would be attached to every View 1 call, and at least two of the three concepts would grow out of that stand's signature structure.

### Visualise (fast start, right after the three ideas)

View 1 prompt for concept A, in English, about 180 words:

```
A stunning, high-end exhibition stand design visualization for Halvard Instruments, a maker of laboratory balances, pipetting systems and liquid handlers since 1952, at LabWorld Europe 2027.

Idea – "Seventy-Five": 75 slender aluminium fins, one for every year since 1952, stand in a row in front of a Halvard-green back wall. Their heights rise in one perfectly even curve from the left to the right – seventy-five years, one line of precision.

Make it look premium and memorable. Brand colours: Halvard Green #0F4D3A and white.
Size – keep it exactly:
- One 6 m × 4 m platform, about 3.4 person-heights wide and 2.3 person-heights deep.
- The whole stand, the fins included, stands on that platform; nothing stands outside it. Open at the front and the right side.
- The tallest element, the last fin, is 4.2 m, about 2.4 times a person.
Essentials: a storage room with a 75-inch screen, a long vitrine with three instruments, a demo bench facing the aisle, a coffee counter, a meeting table for four. The letters "HALVARD" once; no other text. No ceiling, no overhead frame, nothing hung from the hall ceiling. A few visitors for scale, one standing at the front edge.
```

```
python scripts/render.py hero --prompt concepts/A/prompts/hero.txt --out-dir concepts/A/renders --n 2
```

The two images are candidates; choose the one that looks most premium and shows the curve most clearly. Check it by eye with the people as the scale: front edge about 3.4 person-heights, front edge to back wall about 2.3, the tallest fin about 2.4 times a person; open on the front and right; vitrine, bench, counter, table and screen present; nothing hung, no extra room; only "HALVARD" legible. If the stand is drawn a little too deep, fix it with one sentence:

```
python scripts/render.py fix --base concepts/A/renders/hero-v2.png --add "The stand is only 4 m deep, about 2.3 person-heights from the front edge to the back wall; bring the back wall forward and keep every design element." --out-dir concepts/A/renders
```

If it is clearly too big (more than about 20 %) or the fins stand off the platform, take the other candidate or regenerate instead. View 2 is an edit of the chosen View 1:

```
The same exhibition stand as in this image, same design, materials, colours and light, every element in the same place, seen from the front: from the main aisle, nearly straight on, the whole 6 m width visible with some hall on both sides. A few visitors for scale. No other changes.
```

```
python scripts/render.py front --prompt concepts/A/prompts/front.txt --base concepts/A/renders/hero-v3.png --out-dir concepts/A/renders
python scripts/render.py label concepts/A/renders/hero-v3.png  --title "A · Seventy-Five" --out concepts/A/A-1-hero.png
python scripts/render.py label concepts/A/renders/front-v1.png --title "A · Seventy-Five" --out concepts/A/A-2-front.png
```

### Develop (after the renders)

1. Geometry spec (halvard-geometry-A.json): the fins are one `repeat` row (75 pieces at 0.056 m, 1.2 m rising to 4.2 m, left to right as in the chosen image), the program in `required`, `rigging_allowed: false`. `booth_geometry.py check` → PASS (appendix).
2. Plan (halvard-plan-A.png) and the two massing images for the appendix; they are never sent to the image model.
3. Content map, then the concept text, written to match the chosen image.
4. Creative director critique. Had the check failed, the design would change and View 1 and View 2 would be rendered again.

---

## Part 2 – What the user sees after `start`

Read the RFP; 6 assumptions, 2 of them high impact: the front is the main aisle, and the brand colours come from the RFP because the guidelines were not attached. All three concepts pass the geometry check.

**Insight.** Scientists do not buy instruments; they buy results they never have to doubt. Halvard's 75 years are 75 years of not being doubted.

## A · Seventy-Five
**Seventy-five years, one line of precision.**

**The idea.** Seventy-five slender aluminium fins, one for every year since 1952, stand along the back wall. Their heights rise in one perfectly even curve, from 1.2 m to 4.2 m: a measurement made visible, and the shape of a company that never stopped climbing.

**The experience.**
- At 10 m: a precise, rising curve of light and shadow above the hall.
- At 3 m: each fin carries a tiny engraved year; the 1981 fin is marked.
- Inside: the three instruments rest in a long vitrine in front of the curve; the demo bench faces the aisle; the meeting table sits quietly beside the storage block.
- Photo moment: standing beside the tallest fin, 2027.

**What it says.** "75 years of precision you can trust." · 1952 · Europe's first automated pipetting robot, 1981 · in labs in 40+ countries.

**Atmosphere.** Brushed aluminium fins over a matte Halvard-green wall; white solid-surface vitrine, bench and counter; light grazing the fins from below so the curve glows. Halvard Green #0F4D3A · white #F7F7F4 · brushed aluminium #C8CACC · 3500 K.

**Signature detail.** Each fin stands on a 1 cm shadow gap and carries its year laser-engraved at eye height. **Supporting system** (architectural): pale grey microcement floor, steel-framed chairs with grey leather seats at a honed stone table, white solid-surface vitrine, bench and counter. **Intensity:** restrained – one material, one colour, one gesture.

Plan: halvard-plan-A.png · Renders: A-1-hero.png, A-2-front.png (not included in this example)

**Creative director's note.** Clear, ownable and calm. The risk: fins can read as an ordinary slatted wall, so the even curve and the engraved years must be crisp.

## B · The Calibration Room
**Where nothing is left to chance.**

**The idea.** In a laboratory, the calmest room is the one where measurements are made. A translucent room of tensioned white fabric, lit from within, stands in the stand like a clean room drawn in light, with the meeting table inside. Outside it, the three instruments stand on dark green plinths, each in its own precise pool of light.

**The experience.**
- At 10 m: one softly glowing white volume in a dark green stand.
- At 3 m: the instruments, each lit like a specimen.
- Inside: a quiet table in diffuse white light; the noise of the hall seems to drop.
- Photo moment: a visitor's silhouette seen through the glowing wall.

**What it says.** "Precision you can trust." · Calibrated by hand since 1952 · in labs in 40+ countries.

**Atmosphere.** Glowing white fabric against dark Halvard-green floor and plinths; warm 3000 K pools on the instruments. **Signature detail:** the fabric is stretched on a frame so thin it disappears, the room's corners perfectly sharp. **Supporting system** (light and atmosphere): dark green resin floor, low chairs upholstered in grey wool, a counter that glows like the room. **Intensity:** expressive – a dark stand and one glowing volume.

**Creative director's note.** The strongest atmosphere. The risk: it is the hardest to build in four days, and the room must never read as a tent.

## C · Green Stone
**Made by hand, measured to the microgram.**

**The idea.** Halvard calibrates every balance by hand. The stand is made the same way: every surface people touch is honed Halvard-green stone, worked like an instrument, with the instruments set into it like jewels.

**The experience.**
- At 10 m: a calm, monolithic landscape of green stone volumes.
- At 3 m: each instrument set into its own stone plinth, with one engraved line beside it.
- Inside: a stone counter and a stone table, cool to the touch.
- Photo moment: a hand resting on the stone beside the A75 balance.

**What it says.** "Precision you can trust." · Every balance calibrated by hand · 1952.

**Atmosphere.** Honed green stone with fine pale veins, a warm limestone floor, warm 3000 K pools that show the stone's texture. **Signature detail:** the single engraved line on each plinth is filled with brushed brass. **Supporting system** (material and craft): limestone floor, solid walnut stools, a counter cut from the same stone. **Intensity:** balanced – one rich material, quiet everywhere else.

**Creative director's note.** The most tactile and ownable. The risk: weight – check the floor load, or use a stone veneer on a light core.

| | A · Seventy-Five | B · Calibration Room | C · Green Stone |
| --- | --- | --- | --- |
| Idea | 75 years as one rising measurement | Precision as a calm, controlled space | Craft you can touch |
| Feeling | Confident, clear | Quiet, focused | Warm, crafted |
| Starting point | Architectural territory | Light and atmosphere territory | Material and craft territory |
| Best for a client who wants… | One clear, confident statement | A calm place to talk | Quality you can touch |
| Main risk | Reads as a slatted wall | Build time | Weight |

---

## Appendix (excerpt)

**Geometry check, concept A**

```
GEOMETRY CHECK · A · Seventy-Five · 6 × 4, max height 4.5
Floor elements cover 7.7 of 24.0 (32%); walkway 0.90, headroom 2.10 m
RESULT: PASS
```

Massing: halvard-massing-A-hero.png, halvard-massing-A-front.png. Render size check: front edge about 3.4 person-heights, depth about 2.3, tallest fin about 2.4; one fix for depth.

**How concept A meets the brief**

| ID | Requirement | How | Status |
| --- | --- | --- | --- |
| R1 | 6 × 4 m, open front and right | Geometry spec 6 × 4, open sides front and right | Met |
| R2 | Max 4.5 m | Tallest fin 4.2 m | Met |
| R3 | No hanging | Every element stands on the floor | Met |
| R4 | Three instruments | Vitrine 3.0 × 0.6 m | Met |
| R5 | 75" screen | On the front of the storage block | Met |
| R6 | Demo bench | 1.6 × 0.7 m facing the main aisle | Met |
| R7 | Meeting for four | Round table 1.0 m with four chairs | Met |
| R8 | Coffee bar | Counter on the right aisle | Met |
| R9 | Storage ≥ 1.5 m² | 1.8 m², lockable | Met |
| R10 | Four staff | Demo bench, coffee, meeting, floating | Met |
| R11 | Brand guidelines | Colours and type per A2; to confirm with the guidelines | Partly met – guidelines not received |
