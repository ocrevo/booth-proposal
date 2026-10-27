# Proposal – design first, a short appendix last

The proposal reads like a studio pitch, not a compliance report. The client meets the idea and the image first, and sees how the booth answers each design point. It is a design showcase: everything else stays in the internal cards. references/proposal-deck.md gives the exact page plan and how `deck.py` builds, checks and exports it.

## The proposal, in order

1. Cover, agenda.
2. The project: event facts and a site diagram (our own drawing of the footprint, the open sides and the aisle).
3. What the brief asks, in plain language, each point with the pages that answer it.
4. The insight, with its source; what the booth says.
5. The concepts: an overview, then per concept its board, front view (if there is one) and detail page; then the comparison.
6. The lead concept, developed: zones and flow, materials, screens and products, interaction, hospitality and branded items, graphic design (only with real boards).
7. The appendix, at most three pages.

## Per concept

```
[View 1 – the hero image, full width]

<Concept name>
<Manifesto: one line, the feeling in words>

The idea          <two or three sentences: the insight and how the space expresses it>
The experience    At 10 m … · At 3 m … · Inside … · The photo moment …
What it says      Headline: <L1> · Key messages: <L2, at most three>
Atmosphere        <material, colour and light in one or two sentences; a short palette line with HEX>
                  Signature detail · Supporting system · Intensity (references/art-direction.md), one line each

[View 2 – the front view, only if a usable one exists]

Why choose it     <the strengths in one or two lines – never the risks>
Draft – concept visualization, not for construction.
```

The lead concept's plan opens its zones page; every concept's plan is in the appendix.

## Comparison, after the concepts

| | A | B | C |
| --- | --- | --- | --- |
| Idea (创意) | | | |
| Feeling (感受) | | | |
| Strongest image (最强的画面) | | | |
| For a client who wants… (适合想要…的客户) | | | |
| Next step (深化方向) | | | |

No "starting point" row and no "main risk" row. Open points become next steps, worded as how the design will be developed.

## Appendix – at most three pages

1. **Design-point responses**: `| Design point (plain language) | A | B | C | Pages |`. No IDs, no source citations. A point the proposal does not show (graphic designs without boards) reads "另行提交" / "submitted separately".
2. **Claims for client confirmation**: only the claims actually used on the slides, in plain wording, each with its page numbers.
3. **Dimension check**: the plans of all concepts (massing images allowed here, and only here), each captioned with its size and open sides. No PASS, no file paths.

## Internal cards stay internal

These live in brief/ and concepts/. The user sees them with `show`; they never go into the proposal:
- the requirement card with its requirements, deliverables and assumptions;
- the frame card;
- compliance per concept against the hard requirements;
- the content inventory, the content maps and the full sign-off list;
- the geometry check results and the render checks;
- the creative director's critique, scores and risks;
- items to verify with the venue or builder (structure, rigging, power, fire, food service);
- the ideas considered and rejected; the "built from" lines;
- the style cards and the references.

## What may be shown

Only this project's own work: the chosen renders (hero, front and detail views made by render.py, none blocked), the plans, the site diagram, our boards, massing in the appendix, and the client's logo file. Never a reference image (previous booths, other companies' stands, renders anyone likes, tender illustrations) and never a file from input/ or brief/media/.

## Never narrate references

References are inputs, never content. No sentence describes a reference or the road from it ("an upgrade of the old stand", "like the previous stand", "starting from that structure", "how it relates to the reference"). Each concept is presented on its own merit.

## Writing

- Short, vivid sentences. Concrete nouns over adjectives: "a wall of clear glass tubes catching the light" rather than "an innovative, premium display".
- Describe what the chosen images show: text, images and plan present the same stand. Names and counts match the image (a concept called "three bands" shows three bands); positions and clearances match geometry.json ("centred" means centred there). Content that is designed but not in the image is "设计意图" / "design intent".
- Take the manifesto from concept.md as written; cut only to fit, keeping its meaning.
- An assumption reads as a design setting: "暂按前、右两面开口" / "assumed for now: open front and right".
- A claim that needs sign-off carries its tag ("需客户确认" / "to be confirmed") wherever it appears. Use one wording per claim throughout.
- No IDs, citations, file names, check results or notes to ourselves anywhere, appendix included.
- In a Chinese deck: no English second names unless the client is bilingual, metric units only.
