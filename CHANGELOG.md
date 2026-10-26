# Changelog

## 0.5.0 – 2026-10-26

- References are the starting point: the client's own booth photos are attached as images to every hero call (never replaced by a description), and at least two concepts grow out of its signature structure. Fast start: the first renders come right after the three ideas are chosen.
- Renders: the image model is the imagination. View 1 prompts are short (the idea, the hero, brand colours, a three-line size block, the program) and the reference images – the client's booths and anything they like – are attached to every call (`render.py hero --ref`). Long prompts that dictated camera, light, materials and avoid lists, and style cards that filtered the references into rules, made the pictures stiff and are gone; art-direction's cliché list now guides ideas, not renders.
- No massing image is attached to an image prompt any more: a massing base capped the image model's imagination at the level of a white box.
- Size moves from the input to the output: every render is checked by eye against the spec, with the people as the scale, and fixed by editing the image itself (correction sentences for too deep, too tall, extra structure, wrong count, invented text…).
- New `scripts/render.py`: hero (generated), front (edited from the chosen hero), fix, label (draft stamp) and logo (perspective placement of a real logo file); OpenAI Images API, key from `OPENAI_API_KEY` or `.env`, every image saved with its exact prompt and a log.
- Art direction for the concept text: supporting systems by territory, intensity (restrained, balanced, expressive), one signature detail; the render critique asks first whether it looks premium and at least as good as the client's references.
- Style card records the client's register, so an expressive client is not shown three restrained concepts.
- `booth_geometry.py`: the massing view is drawn with a real camera (no more back wall painted over the hero), at 1536 × 1024, for the appendix only; `group` for compound elements (a ridge of many slices is checked as one piece), `axis: "y"` for extrusions, `render_hint` and the `hints` command; `problems()` returns errors and warnings for reuse.

## 0.4.0 – 2026-10-26

- Six-step flow: Brief → Frame → Ideas → Develop → Visualise → Pitch pack. Constraints first in thinking, design first in showing.
- New frame step: four tiers of constraint with an order of authority, program sizes, area and depth budgets.
- Ideas: five or six quick ideas across design territories, three chosen; rejected ideas kept for the appendix.
- Concept text is written after the geometry check, so words always match the layout.
- Geometry check: feet and metres, height zones (line-of-sight rules), rigging and supports, structural span warnings, required program items, frame legs as obstacles, repeated elements (`repeat`).
- Working-with-files mode for Claude Code, Codex and other agents with a workspace.
- Fictional worked example (Halvard Instruments) and fictional test cases.

## 0.3.0

- Geometry spec as the single source of truth; geometry check gate; massing images as render references; fixed-geometry block in every prompt; one image per view.
- Content strategy: inventory, selection, hierarchy by viewing distance, content maps, sign-off list.
- Design-first rewrite: insight, design territories, no-swap test, creative director critique, architectural plan drawings.

## 0.2.0

- Assume and keep going instead of asking; assumptions with basis and impact.
- Art direction standard, cliché list, Elevate field for references; second view changed to a front view.

## 0.1.0

- First version: requirement, venue, style, layout cards; two views per concept; compliance matrix.
