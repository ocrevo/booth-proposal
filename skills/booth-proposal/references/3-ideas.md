# Ideas

Step 3 turns the brief into ideas, set by set, inside the frame of 2-frame.md. None of this file goes into an image prompt.

## Reading a reference set

Each folder `input/refs/<set>/` is one set. Look at every photo; write one note per set as a section of `brief/set-notes.md` (internal):

- Describe only what is visible; if a photo is dark or blocked, say so.
- What makes it distinctive: form (a folded wall, a canopy), space (how visitors move), mood (light, finish, energy).
- Whose booth: what the brief or user says, else "unknown"; never guess from a logo.
- Never copy other companies' logos, text or signature pieces.
- Elevate: where a detail would look cheap in a render (a messy line of light), one line on a better execution that keeps the energy.
- Register: restrained, balanced or expressive, with evidence. A concept grown from an expressive set keeps its energy.

A set gives form, space and mood only. Every concept gets all photos of its own set (4-renders.md) and may evolve from them freely, made clearly more premium. No rule asks any concept to start elsewhere.

A phrase that would narrate a reference object ("last season's stand") goes into `brief.json` `do_not_mention` (1-brief.md).

## From insight to idea

Work in this order; starting from form produces decoration.

1. **Insight.** What must visitors feel and remember; what is true of this client only? One sentence in `insights[]` of `brief/ideas.json`, with `source` naming a line of the tender or the client's material, or worded as the studio's view ("We believe…") with `judgement: true`. A reference photo is never its source; a guess is never written as a fact.
2. **Idea.** The insight as an image people grasp in three seconds. One sentence, ideally named in two to four words.
3. **Experience.** At 10 m a landmark, at 3 m an invitation, inside discovery and conversation; the photo moment.
4. **Form.** The hero element that carries the idea; the layout follows the idea. Size it at once (below).
5. **Atmosphere.** Light, material, colour, sound, each chosen because it tells the idea.
6. **Graphics and content.** One headline, a few proof points, the brand placed with precision, key content carried by the hero. Words, names, years, numbers and the logo are set by us, never painted by the image model: renders leave those surfaces plain, the logo is composited (`render.py logo`), the copy is proposal text.
7. **Craft.** Proportions, joints, edges. One signature detail per concept (a counter floating on a reveal); it may appear in the prompt's Idea block, nothing more.

## Rough sizing

Size each idea while it is a sketch, against the budgets of 2-frame.md:

- **Repeats:** count × size × spacing must fit that dimension: six steps of 0.7 m need 4.2 m, not a 3 m depth.
- **Depth:** the layers one behind another must fit the depth (the depth budget of 2-frame.md).
- **Headroom** under anything people walk beneath: `headroom_m` (2.1 m by default). **Walkways:** at least `walkway_m` (0.9 m by default).
- **Height:** within `booth.max_height`; state the design height.

A gesture that needs a size the stand lacks is not an idea for it. Exact geometry follows in 5-develop.md.

## Booth types and territories

`booth_type` is what visitors do in the space, in plain words. Open examples: a gate you walk through, an object you walk around, a façade you face, a canopy you stand under, a room you step into. Chosen ideas of one set must differ in booth type, so the client chooses between genuinely different experiences.

Territories are a source of variety, not a rule:

| Territory | What leads | The feeling |
| --- | --- | --- |
| Architectural / sculptural | One bold built form | A monumental gesture you walk through or around |
| Light and atmosphere | Light, translucency, darkness, glow | A different mood from the hall |
| Material and craft | A meaningful material, worked with care | Something you want to touch |
| Graphic and typographic | Bold graphics, scale, colour fields | A booth that reads like a great poster |
| Media and interaction | Moving image or responsive surfaces as architecture | The space reacts to you |
| Nature and the organic | Living or organic forms | Calm, alive, human |

## Ideas per set

Per set, sketch five or six ideas, one line each with a rough size, varied by booth type and territory. Choose by Insight, Idea and Specificity (5-develop.md) and rough fit; two or three per set is usual. Rejected ideas get one line each (id, size, reason) in `brief/idea-notes.md`.

Write `brief/ideas.json`:

```json
{"schema": "ideas/1",
 "insights": [{"id": "I1", "text": "Island commuters judge a ferry line by how calm the crossing feels.",
               "source": "RFP §2.1", "judgement": false}],
 "sets": [{"set": "set-1", "ideas": [
   {"id": "A", "name": "Quiet Deck", "idea": "A low curved wall wraps a deck where visitors sit and watch the route film.",
    "booth_type": "a room you step into", "chosen": true}]}]}
```

- `sets[].set`: a set id stamped by `gates.py brief --stamp` (step 1; again after a set is added or its photos change), each set once.
- `ideas[].id` becomes the folder `concepts/<set>/<id>/`: a letter or digit first, then letters, digits, `_` or `-`, at most 16 characters, unique in its set. The concept key is `<set>/<id>`, e.g. `set-1/A`.
- `chosen: true` marks the ideas that get renders.

Run `python scripts/gates.py ideas --scaffold`: it creates `renders/` and an empty concept.md front matter for each chosen idea without a folder, then validates. G-IDEAS rules: `field` (missing or wrong type), `set` (not stamped, or listed twice), `id` (bad pattern or duplicate), `source` (insight without source and `judgement` not true), `same-type` (two chosen ideas of one set share a `booth_type`, compared lower-case), `folder` (chosen idea without a folder). G-REFS `stale`: the sets on disk differ from the stamp; run `gates.py brief --stamp`. Fix until `gates.py ideas` exits 0.

## What the booth says

A visitor reads a headline and a number. Choose the few things worth the walls from the content inventory (1-brief.md).

**Select.** Score each item 1–3 on *Distinctive* (only this client could say it), *Proof* (concrete, verifiable), *On idea*, *For this audience*, *Short*. A first, an only, a dated origin beat "committed to quality". Superlatives, comparisons and changeable numbers are claims with `flag: true` (1-brief.md); one wording per claim.

**Hierarchy.** The higher the level, the fewer the words; one idea per surface.

| Level | Read from | Job | Length |
| --- | --- | --- | --- |
| L1 Landmark | 10 m and more | Brand and one headline that carries the idea | About 3–8 words (4–12 Chinese characters) |
| L2 Invitation | 3–5 m | Proof points that make people step in | At most three short phrases or numbers with labels |
| L3 Discovery | 1–2 m, inside | Products, milestones, how things work | One topic per panel, 40–60 words |
| L4 Depth | In hand or on screen | Full stories, films, quizzes | Screens, print, QR codes, staff |

Long lists go to L3, L4 or a designed element. One primary language per level. Shorten the client's words but keep numbers and regulated claims exact; mark shortened lines "edited from C<n>" in the notes only.

**Message platform**, shared by all concepts, in `brief/content.md`:

```
Headline options (L1): three alternatives, each with the content items it draws on
Key messages (L2): the three strongest, each traced to content items
Discovery topics (L3) · Depth content (L4): screen, quiz, takeaways
Content to request from the client
```

The content map per selected concept follows in 5-develop.md.

## Principles

Guidance for concepts, never prompt text.

- **Use the constraint.** A shallow stand suggests a façade along the aisle; a tight program, a hero that is also the counter.
- **Specific, not generic.** Run the no-swap test: put a competitor's logo on it; if it still works, start again from the insight.
- **One hero** at full strength; everything else supports it quietly.
- **Coherence:** every material, light and graphic choice is explained by the idea.
- **Restraint serves the idea; it is not a style.** Richness, when called for, is committed to fully; minimalism by default is a cliché.
- **Light is a material:** washes, glows, darkness, colour lit from within; light that only outlines edges is decoration.
- **Materials with meaning**, chosen because they say something about the client.
- **Brand through form:** shape, light and material; the logo once, with confidence.
- **Heritage without nostalgia:** sequence, material, scale; never clip art or sepia collages.

## Clichés

Old: LED strips outlining edges, neon, RGB light, glowing halos; saturated gradients, lens flares, high-gloss plastic; several slogans, swooshing calligraphy, bevelled 3D lettering, the logo on every surface; dense text panels, photo collages, roll-ups, cluttered counters, random light boxes.

New, "tasteful": the interchangeable minimal booth (white walls, pale oak, terrazzo, a cove of light, nothing else); generic "premium" materials without a reason; abstract shapes or lines of light that could belong to any brand.

Use the list to shape ideas, not to strip renders: what the client loves in a set stays. Never write it into a prompt as an avoid list.

## Show and go on

`python scripts/gates.py report ideas` prints the idea board: insights, one table per set and the cost line (chosen concepts × `candidates_per_concept` images, minutes at `seconds_per_image` each). Show it in the user's language with the headline options.

`start`: show it and go straight on to step 4; development waits for the selection. `step mode`: stop here.
