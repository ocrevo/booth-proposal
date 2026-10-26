# Concept renders – two views, art-directed

Each concept gets two images of the same booth. They are what the client remembers, so they must look like a top studio's visualisation: one idea, a strong hero element, real materials, designed light, a calm and confident composition. Read references/art-direction.md before writing a prompt.

## The two views

- **View 1 – the hero image, eye level, three-quarter.** Camera at about 1.6 m (5 ft 3 in), in the main aisle near the open corner, looking diagonally into the booth. The hero dominates the picture, while the whole stand, its edges and both open sides stay visible so its real size can be read. 35 mm lens feel, verticals kept vertical.
- **View 2 – front view.** Same eye level, on the booth's centre line in the main aisle, facing the front straight on, the full width visible with a little hall on each side. One-point perspective, calm near-symmetrical framing.

Make every view a separate image of one concept. Never combine concepts in one image, and never ask for a presentation board, collage, title or caption.

## Locking the geometry

Image models do not obey dimensions written as words; they obey pictures much better. So the renders are built on the massing images from scripts/booth_geometry.py (references/layout-card.md):

- View 1: attach `massing-hero.png` as the geometry reference.
- View 2: attach `massing-front.png` as the geometry reference and the finished View 1 as the style reference.
- Every prompt opens with the fixed-geometry block below, before any atmosphere or style.

Even so, a render only shows design intent. Dimensions are governed by the geometry spec and its check, never by the image; say so under the images.

## How to write a prompt that looks designed

Image models fill every gap with the average trade-show booth. Within the locked geometry:

1. **Lead with atmosphere and idea, not inventory.** Describe the feeling and the hero the way a designer talks about it: form, material, light. A list of zones produces a literal, crowded picture; the massing image already carries the layout.
2. **Show only what serves the image.** Describe the hero and at most three supporting elements; the rest is in the massing image and the plan.
3. **Name precise materials and light,** then the photography, then the clichés to avoid.

## Prompt language and text

Write prompts in English whatever language the user uses: image models follow English most reliably. Give the user a one-line summary in their language.

Image models garble text, especially non-Latin scripts. Keep on-image text to the client's Latin-letter name and at most one short headline from the message platform. Surfaces that carry copy in the content map appear as clean panels or, where the copy is part of the architecture (engraved dates, names on a wall), as fine abstract lettering that is not meant to be read. The designer applies the real copy from the content map. Say so under the images.

## Fixed-geometry block (opens every prompt)

```
FIXED GEOMETRY – follow exactly; it overrides everything below.
Use the attached white massing model as the exact geometry, proportions, positions and camera. Keep every element where it is and at the size shown; add only materials, colour, light, graphics and people.
Stand: exactly [W] m wide × [D] m deep, open on [sides]; nothing extends beyond this footprint – no extra depth, no rear room, nothing in the aisle.
Tallest element: [H] m. Scale: people about 1.75 m tall, counter [counter height] m, tables 0.75 m.
If something does not fit, simplify it; never enlarge the stand or shrink furniture to implausible sizes.
One photograph of this one stand only: no collage, no presentation board, no captions.
```

Without a massing image (no code can run), replace the second line with the positions and sizes of the hero and the main elements from the geometry spec, in metres from the left wall and from the back wall.

## View 1 template

```
[Fixed-geometry block]
[One sentence of atmosphere: what it feels like to stand in front of this booth.]
Award-level exhibition design for [client, sector] at a trade fair: concept "[name]" – [idea in one sentence].
Hero: [the hero described as a designer would: form, material, finish, how light behaves on it].
Supporting, kept quiet: [up to three elements, one short phrase each].
Palette: [colours with HEX and where]. Materials: [materials with finishes]. Light: [light concept, colour temperature].
Brand: [one clean panel for the logo; Latin name only if confirmed]; no other text.
Camera: as in the massing image – eye level 1.6 m in the main aisle at the [left/right] front corner, three-quarter view, 35 mm, verticals corrected; the hero dominates, the whole stand and both open sides visible.
Photography: editorial architectural photography, soft natural-looking light, true-to-life materials, subtle depth of field, two or three visitors in motion for scale.
Setting: calm neutral exhibition hall, no other brands visible.
Avoid: LED strip outlines, neon, RGB light, gradients, lens flare, glowing text, high-gloss plastic, multiple slogans, decorative swooshes, roll-up banners, clutter, generic white-and-oak minimalism, fisheye distortion, cartoon or game-engine look.
```

## View 2 template (attach massing-front.png and the finished View 1)

```
[Fixed-geometry block, referring to the attached front massing image]
Same exhibition stand as in the attached View 1: keep the hero, every material, colour and light, and all elements in the same positions.
Camera: as in the front massing image – eye level about 1.6 m, in the main aisle on the stand's centre line, facing the front straight on, one-point perspective, full width visible with a margin of hall on both sides.
Elements to keep visible: [hero], [brand panel], [counter], [up to three more].
Same editorial architectural photography and light. Do not add, remove or move anything.
```

## After rendering

**Consistency** between the two views:

| Check | Pass / Fail | Note |
| --- | --- | --- |
| Footprint, heights and positions match the massing image (compare against the 1.75 m person) | | |
| Hero element: same form, material, scale and position in both views | | |
| Palette and materials | | |
| Light character | | |
| Brand panel position | | |
| Counter and other named elements in the same places | | |
| Open sides, as far as each view shows them | | |
| Nothing added that is not in the concept | | |

**Design quality:** run the creative director critique from art-direction.md on each image. Ask in particular: does the hero read instantly, does it look like real materials and designed light, and is it free of every cliché?

**Retry rules:** regenerate only the failing view with one sentence naming the fix ("the canopy must glow evenly from within; remove the bright edge lines"). At most three attempts per view; then show the best pair and say what still falls short. If View 1 fails, fix it before making View 2.

## Without an image tool

Give a prompt pack per concept: the two massing images, the View 1 prompt, the View 2 prompt, the instruction "generate View 1 with massing-hero.png attached; then View 2 with massing-front.png and View 1 attached", and the checks for the user to run.
