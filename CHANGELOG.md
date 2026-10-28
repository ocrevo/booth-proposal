# Changelog

## 0.6.0 – 2026-10-28

- Reference sets and free selection: references live in `input/refs/<set>/`, each set gets its own candidate concepts, and the user chooses which concepts to develop with `gates.py select`. `start` stops once, after the candidate boards and the overview, to wait for that choice; `step mode` stops after every step.
- `brief.json` is the single source for the brief and frame; `scripts/gates.py` (brief, frame, ideas, select, renders, concepts, report) checks each stage with one error code per kind of problem, grouped in families.
- Hero render only: two candidates per concept, one chosen; corrections are limited by the `fix_max` threshold. Front and detail views are no longer part of the default flow.
- Free, short prompts, with `render.py lint` checking the prompt before any call.
- Image review with typed marks, a size gate and a premium gate (`render.py review`, `render.py sheet`); the logo is composited from the real file (`render.py logo`) and inherits the review of its base image.
- Sidecar v2 with a base chain; `render.py import` brings in an image made in ChatGPT or Claude.ai and records where it came from.
- The proposal is a single HTML file: `deck.py layouts --emit` gives the building blocks, `check` is read-only, `render` measures overflow and upscale, two review passes are recorded with `review --record`, and `export` is gated.
- `pack/` holds only `proposal.html`, `proposal.pdf` and `site.svg`; every other generated file goes to `work/`.
- Geometry: error and warning codes, a `facts` command, the envelope check with a reasoned override, and argparse-based `draw_plan.py`.
- Thresholds and report labels are named values; the labels live in `assets/labels/`.
- Docs reorganised into one reference per step (`1-brief.md`, `2-frame.md`, `3-ideas.md`, `4-renders.md`, `5-develop.md`, `6-proposal.md`) plus `review.md`; the README is rewritten in Chinese.
- New: tests for docs, scripts and release; rewritten evals with fictional inputs; the client-term scanner `tools/scan_client_terms.py`; the eval grader `tools/eval_grade.py`; the deterministic build `tools/build_dist.py` (the `dist/` file is byte-identical across builds and leaves out `evals/`).
- Removed: the page generators and the fixed page plan, scraping of `concept.md` text, style-card and design-points parsing, the rule that at least one concept must not come from the references, the intensity and supporting-system tables, massing images in the proposal, `pack/check.txt`, `pack/preview/`, and the worked example.
- `docs/proposal-strategies.md`: how international exhibition and brand-experience agencies structure a proposal, with a comparison against this skill's outline.
- README: the proposal outline and the layouts available for each page role.
- The client-term scanner also scans `docs/`.
- `docs/proposal-architectures.md`: a second, tender-response proposal architecture next to the design-showcase one, with a three-way comparison (current skill, a tender's structure, international practice).

## 0.5.0 – 2026-10-26

- New order: Brief → Frame → Ideas → Visualise → Develop → Pitch pack. Fast start: View 1 renders come right after the three ideas are chosen, within minutes; geometry, plan, content map and concept text follow and stay true to the chosen image. If the geometry check fails, the design changes and is re-rendered.
- The brief and frame cards live in `brief/` and are reused: a new run copies them instead of redoing them.
- References are the starting point: the reference image files – the client's own booths and anything they like – are attached to every View 1 call (`render.py hero --ref`), never replaced by a description. When the client's own booth is among them, at least two of the three concepts grow out of its signature structure, each pushed in a different direction and made clearly more premium; the third may break away. The style card is now a short note on what makes the references the client's own, not a filter, and records the client's register so an expressive client is not shown three restrained concepts.
- The three concepts must clearly differ; the design territories are a source of variety, no longer a rule that they come from three different territories.
- Short View 1 prompts (about 150–250 words): the idea and its hero, brand colours, a three-line size block in person-heights, the program in one line, the logo, no ceiling or hanging, a few visitors, one line on what to keep from the references. The long prompts with camera, light recipes, material lists, layout coordinates and avoid lists, and the fixed-geometry block, are gone: they made the pictures stiff. Art direction (including the cliché list) guides the concepts, not the prompts.
- No massing image is sent to the image model any more: a massing base capped its imagination at the level of a white box. Massing images are appendix documentation only.
- Size is checked on the output: two View 1 candidates per concept, one chosen and checked by eye with the people as the scale; details fixed by editing the image with one correction sentence, or regenerated when the size is clearly wrong (more than about 20 %, or the hero off the platform). View 2 is an edit of the chosen View 1.
- New `scripts/render.py`: hero (generated from the prompt; with `--ref` it goes to the edit endpoint), front (edited from the chosen hero), fix, label (draft stamp) and logo (perspective placement of a real logo file). OpenAI Images API, default `gpt-image-2`, 1536 × 1024, quality high; key from `OPENAI_API_KEY` or a `.env` line `OPENAI_API_KEY=` / `openai_key=`; `--dry-run`; every image saved with its exact prompt (`.prompt.txt`) and a log (`.json`).
- Art direction for the concept text: supporting systems by territory, intensity (restrained, balanced, expressive), one signature detail; the render critique asks first whether it looks premium and at least as good as the client's references, then whether the idea reads and the size is right.
- New test case `reference-first` (a fictional previous stand): every View 1 call carries `--ref`, at least two concepts evolve the stand's signature structure, one short reference line in each prompt.
- `booth_geometry.py`: the massing view is drawn with a real camera (no more back wall painted over the hero), `--views` and `--size` (default 1536 × 1024), for the appendix only; `group` for compound elements (a ridge of many slices is checked as one piece), `axis: "y"` for extrusions, `render_hint` and the `hints` command, `layer` and `camera`; `problems()` returns errors and warnings for reuse.

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
