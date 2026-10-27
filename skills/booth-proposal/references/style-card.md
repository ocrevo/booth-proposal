# Style card – template and rules

A style card is a short note on what a reference booth tells you about the client's taste: what makes it theirs, what they love, the finish they expect, the energy they are used to. It is a note for the designer, not a filter.

**References are inputs, never content.** The reference images go to the image model with every View 1 prompt (references/image-prompts.md) and to the designer. They are never shown, quoted or described in the proposal or any deliverable, and neither is this card. The card never replaces the images and is not written into the prompt. Nothing the client likes in them is turned into a rule against it. The prompt takes only one line from it: what to keep and evolve, and what not to copy.

Where a reference's execution can be done better, the Elevate line suggests how, but the concept keeps what the client loves – the brightness, the glow, the brand colour, the scale – unless the idea needs something else.

## Rules

- Look at every reference image yourself. Describe only what is visible. If a photo is dark or partly blocked, say so instead of guessing.
- Name what makes it the client's own: its signature structure (a folded wall, a canopy, a sculptural counter), its colours, its light, its brand presence.
- Give colours as approximate HEX values and name where each is used. Mark them "≈" because colours in photos shift with lighting.
- Several photos of the same booth make one card; different booths make different cards.
- Whose booth: write what the brief or the user says. If nobody says, write "unknown". The card does not guess from a logo in the photo.
- A concept may evolve what the card names under Keep and evolve, pushed in its own direction and made clearly more premium. The three concepts stay clearly different: at least one starts from somewhere else (references/art-direction.md).
- Do not copy, from any reference: other companies' logos and wordmarks, slogans and text, posters and roll-up banners, and another company's signature pieces or exact layout. The user may move items between Keep and Do not copy.
- **Do-not-mention:** list the words that would narrate this reference in the proposal: what people call the stand or its signature piece, and phrases like "last year's stand" in the deck's language. `deck.py check` refuses any slide text that contains one of them. Write the terms on that one line, separated by commas.
- Without references there is no style card: the design territories in art-direction.md suggest each concept's design language.
- Add an Elevate line only where an execution detail would look cheap in a render (a messy cable of light, a crowded wall of text); keep the intent and the energy.
- List the reference files to attach to the View 1 prompts.
- Judge the client's register from the references: **restrained** (few materials, quiet light, little text), **balanced**, or **expressive** (strong colour, bold graphics, light effects, slogans). It sets how far the concepts may go: an expressive client shown three restrained concepts will find them "too plain", so concepts that evolve a reference keep its energy (colour, scale, brand presence) while their execution is elevated. Record the risk in the critique.

## Template

```
STYLE CARD S1 · v1 · Source: <file names>
Whose booth: <the client's own (as the brief says) | another company | unknown>

What makes it theirs: <the 2–4 signature elements: structure, colours, light, brand presence>
What the client probably loves: <the intent worth keeping>
Register: <restrained | balanced | expressive> – <one line of evidence>
Colours: <role – name ≈ HEX – where it appears>, …

Keep and evolve: <what a concept may grow from, e.g. the folded light wall, the warm glow>
Do not copy: <…>
Elevate: <reference does> → <elevated execution>, e.g. LED strips outline the wall → one continuous cove of indirect light behind a matte fold
Do-not-mention: <term>, <term>, … (e.g. 旧展台, 去年的展台, last year's stand, the green wall)

Attach to View 1 prompts: <file names>
```
