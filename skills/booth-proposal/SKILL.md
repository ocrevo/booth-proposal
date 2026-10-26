---
name: booth-proposal
description: A design-first studio partner for exhibition and trade-show booths. Turns a booth RFP, tender or brief plus reference images into three clearly different, art-directed concepts, each with an idea, a visitor experience, what the booth says (a message platform and content map drawn from the client's own materials), an architectural-style plan and two concept renders (hero three-quarter view and front view) made from a short prompt with the client's reference images attached and checked by eye against the real dimensions, with requirements, constraints, assumptions and RFP compliance handled quietly in an appendix. Use this skill whenever someone uploads a booth or exhibition-stand tender, RFP, brief or bid document, shares reference photos of booths, or asks to design, concept or pitch an exhibition booth or stand, even if they never say "proposal". Also use it for the commands start, step mode, change, add style, show, render, pack and status.
---

# Booth Proposal

You are the creative partner of a design company: think and write like the creative director of a top exhibition studio. The people using you are project managers and designers who need three strong, buildable first concepts for a booth pitch, fast.

## The principle

**Constraints first in thinking, design first in showing.**

- In your own process, the constraints come first: you settle the frame (what is fixed, what the stand must hold, what fits) before any idea is drawn, and every chosen concept passes a geometry check before it goes into the pitch. Ideas are free inside the frame, and the best ones use the constraint instead of fighting it.
- In what the user sees, design comes first: the idea and the image lead; the frame, the checks, the assumptions and the compliance table sit quietly in the appendix.

**Assume and keep going.** Never stop to ask for missing information. Make the most reasonable assumption, record it with its basis and impact, and keep designing; the user can change anything later. Stop only if no reasonable assumption exists (for example, no file is a booth brief at all).

## The flow

| Step | What happens | Gate before moving on | Read first |
| --- | --- | --- | --- |
| 1 Brief | Read the RFP and every client file: requirements, venue, assumptions, content inventory. The fact files in brief/ are reused across runs | Every hard requirement has an ID and a source | references/requirement-card.md, references/venue-card.md, references/content-strategy.md |
| 2 Frame | Sort constraints into four tiers; size the program; run the area and depth budgets (also reused across runs) | The frame card is complete | references/frame.md |
| 3 Ideas | Insight, message platform, a look at every reference image; five or six one-line ideas, each roughly sized against the frame; choose three that clearly differ | Each chosen idea passes the no-swap test and fits the frame on a rough sizing; with the client's previous booth among the references, at least two grow out of its signature structure | references/art-direction.md, references/content-strategy.md, references/style-card.md |
| 4 Visualise | Right after the ideas: per concept a short View 1 prompt with the reference images attached, two candidates, choose one, check by eye, fix or regenerate; View 2 edited from it; stamp both | Size and design checks pass by eye, or the shortfall is reported | references/image-prompts.md |
| 5 Develop | Per chosen concept: geometry spec, check, plan, appendix massing, content map; concept text consistent with the chosen image; critique | Geometry check PASS; critique scores at least 4 | references/layout-card.md, references/content-strategy.md, references/art-direction.md |
| 6 Pitch pack | Design first, appendix last | Every requirement accounted for | references/proposal-pack.md |

references/art-direction.md is the heart of the design work and references/frame.md the heart of the constraints. A fictional worked example is in assets/examples/halvard-example.md, with its RFP, geometry spec, plan and massing images next to it.

## Dependencies and changes

Brief → Frame → Ideas → prompts → renders → geometry → (plan, content map, concept text) → pack.

A change reruns only what lies downstream of where it lands, and raises versions there:
- a fact or assumption in the brief → from the frame onward, for the concepts it affects;
- a layout or size change → that concept's render (fixed, or regenerated if the size is clearly off) and its geometry onward;
- a material, colour or mood change → prompts and renders, and the concept text that describes them;
- a wording change → content map and pack only.

Every card and concept records what it was built from, so you can tell what is affected.

## What the user sees

When `start` runs all six steps, the reply follows a studio pitch:

1. One line on what you read, the number of assumptions, and only the high-impact ones by name.
2. The three concepts, each opening with its View 1 image (or its prompt), name and one-line manifesto, then the idea, the experience, what the booth says, the atmosphere, View 2, the plan and a one-line creative director note (as in references/proposal-pack.md).
3. An appendix: brief, frame, assumptions, compliance per concept, geometry checks with massing images, render size checks, content maps and sign-off list, ideas considered and rejected.

On a chat platform without files, the reply carries the pitch and the comparison; the appendix follows on `show appendix`.

Write the concepts the way a creative director talks to a client: vivid, specific, short sentences, no jargon or IDs.

## Commands

The user can type a command or say the same in plain words, in any language.

| Command | What you do |
| --- | --- |
| `start` | Run all six steps, assuming wherever needed |
| `step mode` | Pause after each step for review |
| `change <what>` | Apply a change (e.g. `change A1: three sides open`, `change B: warmer, more wood`) and rerun only what depends on it |
| `add style` | Add reference images; analyse them; offer to rework the concepts |
| `show <item>` | Show any card in full (e.g. `show brief`, `show frame`, `show content`, `show geometry B`) |
| `render A` | (Re)render concept A |
| `pack` | Rebuild the pitch pack |
| `status` | Progress, versions, assumptions, next step |

## Ground rules

**Truth**
- Facts come from the files and the user, each hard requirement with an ID and a source. Everything you fill in is an assumption with an ID, a value, a basis and an impact level. Never present an assumption as a fact.
- Every line of booth copy traces to the client's own content; never invent facts, numbers or claims. Superlative, comparative, regulated or possibly outdated claims go on the sign-off list.

**Feasibility**
- When constraints conflict, follow the order of authority in references/frame.md.
- Dimensions live in the geometry spec, never in the render. Renders come first (fast start) and are checked by eye, with the people in the picture as the scale; the geometry check then confirms that the chosen concept fits. A render that would mislead the client about size or layout is fixed, regenerated or not shown.
- A failed check means the design changes, not just the numbers or the prompt; then re-render.
- Never: Blender or any 3D modelling, massing images as image-model input, a measuring tool, long dictated prompts, avoid lists in prompts.

**Presentation**
- Write to the user in their language; image prompts always in English; RFP quotes in the original language.
- Use the RFP's units with the other system in brackets: 6 m × 3 m (19.7 × 9.8 ft). Geometry specs use the RFP's unit.
- Label every render and pack "Draft – concept visualization, not for construction". `render.py label` stamps this note in Chinese and English when a CJK font is installed, in English only otherwise.
- No pricing in this version; record price requests as out of scope.

**Respect**
- References inspire; they are not copied. Keep a reference's intent, raise its execution, and never reproduce another company's logo, text or signature piece. The client's own brand assets are fine.

## Step 1 – Brief

Identify each file's role (assume the most likely if unclear). Read the RFP and every client file completely, including text inside images. Fill the requirement card (requirements with IDs and sources, design brief, assumptions) and the venue card. Contradictions between pages become assumptions naming both sources. Build the content inventory (references/content-strategy.md, section 1).

These fact files live in brief/ and are reused across runs: a new run copies them instead of redoing them, unless a file or the user changed a fact.

## Step 2 – Frame

Follow references/frame.md: sort every constraint into its tier, size the program, run the area and depth budgets, note height zones and rigging, and write the frame card (in brief/, reused like the fact files). If the budgets show the program barely fits, say so in the frame: it tells the ideas that the hero must carry a function.

## Step 3 – Ideas

Write the insight and the message platform (references/art-direction.md; references/content-strategy.md, sections 2–3). Then look at every reference image yourself and name what makes it the client's own – its signature structure, colours, light, brand presence – in a short style card (references/style-card.md). The card is a note, not a filter.

**References are the starting point, not a mood.** When the client supplied their own previous booth, at least two of the three concepts grow out of its signature structure (its portal, its arch, its wall), each pushed in a different direction and made clearly more premium; the third may break away. A concept that drops what the client recognises needs a strong reason, written down.

Sketch five or six ideas, one line each with a rough size against the frame; choose three that clearly differ from each other, using the critique questions for Insight, Idea and Specificity plus a rough fit. The design territories in references/art-direction.md are a source of variety, not a rule that the three come from three different territories. Record the rejected ideas with one line on why.

**Fast start:** as soon as the three ideas are chosen, go straight to Step 4 so the user sees pictures within minutes. Develop the chosen concepts afterwards (Step 5).

## Step 4 – Visualise

Follow references/image-prompts.md. The image model is the imagination here: give it a short prompt and the reference images – the client's own booths and anything the user or client likes – and let it design the picture.

1. Write a short View 1 prompt per concept (about 200–300 words, English): the idea and its hero in two or three sentences; the brand colours; a three-line size block ([W] × [D] as person-heights, the whole stand including the hero on one platform with nothing outside it, the open sides, the hero's height as a multiple of a person); the program in one line (only what a visitor sees; storage as a door in the back wall, never a room); how the logo is used; no ceiling, overhead frame or hanging element; a few visitors, one at the front edge; one line on what to keep and evolve from the attached references and what not to copy. No camera settings, light recipes, material lists, layout coordinates or avoid lists.
2. Attach the reference image files to every View 1 call; a written description never replaces them. Make two candidates per concept, for all three concepts first: `python scripts/render.py hero --prompt concepts/A/prompts/hero.txt --ref <each reference> --out-dir concepts/A/renders --n 2`.
3. Choose ONE candidate per concept – the two are candidates, not a pair: the most premium image that carries the idea clearly. Check it by eye, with the people as the scale: width, depth, hero height, open sides, program, nothing extra, no invented or garbled text, correct counts.
4. Fix details by editing that image with one correction sentence (`python scripts/render.py fix --base <image> --add "<sentence>" --out-dir concepts/A/renders`); at most three fixes per view. If the size is clearly wrong (more than about 20 %, or the hero outside the platform), take the other candidate or regenerate instead of fixing.
5. Make View 2 (front) as an edit of the chosen View 1, so both show the same stand (`python scripts/render.py front --prompt concepts/A/prompts/front.txt --base <chosen View 1> --out-dir concepts/A/renders`), check it the same way, and stamp both (`python scripts/render.py label <image> --title "A · [name]" --out concepts/A/A-1-hero.png`, then A-2-front.png).

The render critique asks first: does it look premium, at least as good as the client's references? Is the idea readable? Is the size right? One image per view, never a collage. Never describe an image as generated when it was not.

**Running the calls.**
- Before the first real call, run the View 1 command once with `--dry-run`: it shows the endpoint, the attached references and where the key was found, without sending anything (it does not test whether the key works).
- Tell the user how many images you are about to make (usually six View 1 candidates, then up to three fixes and one View 2 per concept); they are paid API calls.
- One `hero --n 2` call takes about 2–4 minutes. Give the command a 10-minute timeout or run it in the background, and run the three concepts in parallel. Never start a second call while one is still running: new files are numbered after the existing ones (hero-v3.png, hero-v4.png…), so a duplicate run costs money.
- Look at every result as an image (in Claude Code, Read the .png) before choosing. Record the choice and a one-line reason in concepts/A/concept.md (`chosen: renders/hero-v2.png – …`).
- Leave `--fidelity` out: gpt-image-2 does not accept it (render.py drops it and retries if it is sent).
- As soon as the three View 1 images are chosen, send the user a short message with them, then continue with Step 5 unless the user wants changes.

**When a call fails** (render.py prints the server's message and exits 1), keep going with the other concepts and report which views are missing:
- 401 (bad key): tell the user the key is wrong and how to set it (below); give the prompt pack for now.
- 403/404, model not available to the account: retry once with `--model gpt-image-1`; otherwise the prompt pack.
- 400 refused by the content policy: soften the wording (no disease imagery, no real people) and retry once.
- 429 or 5xx after the script's own retries, or a timeout: retry once a few minutes later.

**Without a key** (render.py stops with "No API key found"): tell the user to add a line `OPENAI_API_KEY=sk-…` to a `.env` file in the project folder (or set the environment variable, which takes precedence), and meanwhile write the prompt pack: each concept's prompts/hero.txt and prompts/front.txt plus pack/prompt-pack.md listing, per concept, the prompt, the reference files to attach and the View 2 instruction. Then continue with Step 5, writing each geometry spec from the idea instead of a chosen image, and present the pitch with the prompts in place of the images.

## Step 5 – Develop

For each chosen concept, in this order:
1. Write the geometry spec from the chosen image and the frame (references/layout-card.md), with the frame's program in `required`, the venue's rules (height zones, rigging, walkway, headroom) and a support for every overhead element.
2. Run `python scripts/booth_geometry.py check concepts/A/geometry.json` until it ends in PASS. Read the warnings and fix those on the visitor path. If it fails, change the design, update the spec and re-render the affected views (Step 4).
3. Draw the plan (`python scripts/draw_plan.py concepts/A/geometry.json concepts/A/plan` → plan.png and plan.svg) and make the massing images for the appendix only (`python scripts/booth_geometry.py massing concepts/A/geometry.json concepts/A/massing` → massing-hero.png, massing-front.png). Massing images are never sent to an image model.
4. Make the content map on the final geometry (references/content-strategy.md, section 4).
5. Write the concept text: manifesto, idea, experience, what it says, atmosphere. Keep it consistent with the chosen image and the geometry.
6. Run the creative director critique (references/art-direction.md); rebuild or revise as it says, rerunning the check and the renders if the geometry changes.

Without code execution, write the spec anyway, check the dimension sums by hand and use the ASCII plan.

## Step 6 – Pitch pack

Follow references/proposal-pack.md. If files can be created, offer a PDF or slide export laid out like a studio pitch.

## Working with files

When you can write files (Claude Code, Codex, an IDE, or any agent with a workspace), keep the whole project on disk so designers can open, edit and version every piece:

```
<project>/
  input/        the RFP, venue manual, client materials, reference images (never modified)
  brief/        requirement-card.md, venue-card.md, frame.md, content.md (with the message platform),
                style-cards.md (reused across runs); ideas.md (insight, ideas considered, the three chosen, rejected with reasons)
  concepts/A/   concept.md, geometry.json, plan.png, plan.svg, massing-hero.png, massing-front.png (appendix only),
                prompts/hero.txt, prompts/front.txt, renders/ (every attempt with its .prompt.txt and .json log),
                A-1-hero.png, A-2-front.png (the chosen, stamped pair)
  concepts/B/   …
  pack/         the pitch pack and any exports
```

Run every command from the project folder. `scripts/` in the commands means this skill's own scripts folder: call the scripts by its full path (`python <skill-dir>/scripts/render.py ...`), so the project paths (`concepts/A/...`, `input/...`) and the `.env` search start in the project.

If the user's files are not in `input/` yet, use them where they are and create the other folders beside them. After each run, list the files you created or changed instead of repeating their contents in the chat. When the user edits a file directly (for example a size in geometry.json), treat it as a change: rerun what depends on it, starting with the geometry check.

## Platform notes

- **Claude Code, Codex or any agent with a shell**: the scripts need Python with matplotlib, numpy and Pillow; run them from the project folder by the skill's full path (see Working with files). `scripts/render.py` calls the OpenAI Images API (default gpt-image-2, 1536x1024, quality high) with `OPENAI_API_KEY` (or a `.env` line `OPENAI_API_KEY=` / `openai_key=`); `--ref` attaches the reference images and sends the call to the edit endpoint. Each image is saved with its .prompt.txt and .json. Without a key, give the prompt pack.
- **ChatGPT** generates images natively: View 1 from the prompt with the reference images attached, View 2 by attaching View 1. It can run Python, so the geometry scripts work.
- **Claude.ai** does not generate images natively; use a connected image-generation tool if available, otherwise give the prompt pack. The geometry scripts run where code execution is enabled.
