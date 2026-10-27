# Proposal deck – the client proposal (Step 6)

The proposal is `pack/proposal.html`: one HTML file of 16:9 slides (1920 × 1080 px each), built by `scripts/deck.py` from the design system in `assets/deck/template.html`, and exported to `pack/proposal.pdf`. references/proposal-pack.md says what goes in; this file says how deck.py builds, checks and exports it.

It is a client-facing design showcase. It holds the ideas, the renders, the visitor experience, what the booth says, the plan, the atmosphere and the answer to the brief. It never holds:
- engineering or construction drawings, a schedule, staffing, pricing or venue technical items;
- internal working: IDs (D1, A3, C22, R12), tender citations ("s.4 ②"), file names and paths, TODO, "待出图 / 待修图 / 待补充 / 待出稿", PASS or FAIL, notes to ourselves, raw internal tables, the critique or its risks;
- references, shown or described.

Everything client-specific comes from the project folder at run time. Nothing in the skill names a client.

## Inputs

- `brief/deck-style.json` – the look. Keys: `lang` (`zh` or `en`, the user's language), `header` (running header: client · event · "booth design proposal"), `stamp` (the draft note on every render; in a zh deck Chinese only: "初稿 – 概念效果示意，不用于施工"), `logo` (path under brief/), `fonts.sans`, and `colors` with any of `paper surface tint line muted muted_text ink ink_strong primary primary_alt accent brand_extra warn`. Take the colours from the client's brand guide; leave out what you do not know (neutral defaults apply). If the file is missing, write it first. Example (fictional): `{"lang":"en","header":"Halvard Instruments · LabWorld Europe 2027 · Stand design proposal","stamp":"Draft – concept visualization, not for construction","logo":"brand/halvard-logo.svg","colors":{"primary":"#0F4D3A","accent":"#B8862F","paper":"#FFFFFF"}}`.
- The logo: the client's official logo file (vector if they supplied one), listed under "Logo files provided" in the requirement card and kept in `brief/brand/`. Never a crop of a photo or a reference. A crop from a tender page is a stopgap: put the logo file on the list of content to request.
- `brief/design-points.md` – one table `| ID | Type | Design point | Source |` (Chinese headers 编号 / 类型 / 设计要点 / 出处 also work). IDs D1, D2…; type is one of `space theme brand content product screen interactive hospitality giveaway graphic other`. One row for each thing the client expects the design to answer: every requirement that asks something of the design. Write the Design point column in plain client language, because it is shown as written ("Celebrate 75 years of the brand", not "Theme req. per s.4"). The ID and the Source stay internal and are never shown.
- `brief/requirement-card.md` – the event facts for the project page: event, venue, dates (conference days and exhibition days apart when the card has both), stand size, open sides (and whether they are an assumption), height limit.
- `brief/content.md` – the message platform and the claims with their flags (references/content-strategy.md).
- `brief/style-cards.md` – only for its `Do-not-mention:` lines, which `check` adds to its lint.
- `concepts/<L>/concept.md`, as the skill writes it:
  - `chosen: renders/hero-vN.png – reason`; optional `front: renders/front-vN.png` and `detail: renders/detail-vN.png`;
  - any number of `blocked: renders/<file> – reason` lines; deck.py never places a blocked file;
  - the title `# A · Name`; a second-language name only in a bilingual deck;
  - the manifesto as the bold line under the title;
  - sections for the idea, the experience (four bullets: 10 m, 3 m, inside, photo moment), what it says, the atmosphere (colours with #HEX), `为什么值得选 / Why choose it` (strengths only) and `深化方向 / Next step`;
  - an optional `accent: #HEX` line for the concept's own accent colour.
  The internal critique, its risks and the compliance table stay in concept.md and never reach the deck.
- A **usable render** is a file under `concepts/<L>/renders/` made by render.py (its `.json` sidecar beside it) and not blocked.
- `concepts/<L>/plan.png` or `plan.svg`, `massing-*.png` (appendix only) and `geometry.json` (the site diagram and the zone numbers).
- `pack/boards/` – boards we made for this project: graphic designs (`graphic-*.png|svg`), an interaction storyboard (`interaction-*.png|svg`).

deck.py reads no other table: the assumptions and the ideas considered are never put in the deck.

## Page plan

`deck.py new` builds this skeleton. The design-point types in brief/design-points.md decide the conditional pages; the agenda follows the pages that exist.

1. **Cover** – the lead concept's usable hero, full bleed. Without one: the split cover with the site diagram.
2. **Agenda** – the groups, with descriptions built only from the titles of pages that exist.
3. **Project** – event, venue, dates (conference days and exhibition days apart when the requirement card has both), stand size, open sides (worded as a design setting, "暂按…" / "assumed for now: …", when they are an assumption), height limit. Beside them, the site diagram deck.py draws into `pack/site.svg` from the frame and geometry: the footprint W × D, open sides dashed, the main-aisle arrow, dimension lines and a height-limit note. No concept element appears on it.
4. **What the brief asks** – the design points in plain language as cards, with no IDs and no source citations. Each card ends with "见第 X 页" / "see p. X", listing every page that answers it. It runs onto a second page only when needed.
5. **Insight** – one statement, with a source line naming the tender or client material (never a reference). An insight that is the studio's view is worded as such ("我们认为…" / "We believe…").
6. **What the booth says** – message cards from the message platform. A claim that needs sign-off carries the small tag "需客户确认" / "to be confirmed" (`data-claim`).
7. **Overview** – the concepts side by side, the recommended one tagged.
8. **Per concept**:
   - board – the chosen usable hero;
   - front (stage) – only if a usable front render exists; never a placeholder page;
   - detail – the experience moments, what it says, the atmosphere and "为什么值得选" / "Why choose it" (strengths only, no risks).
9. **Compare** – rows: 创意 / 感受 / 最强的画面 / 适合想要…的客户 / 深化方向 (Idea / Feeling / Strongest image / For a client who wants… / Next step). No starting point, no risks.
10. **The lead concept, developed** (`--lead`, else the first):
    - zones & flow – the plan, with zone numbers that match the plan's legend;
    - materials – a usable detail render if one exists, else the text-only variant; never the hero again;
    - screens & products – when the brief has points of those types;
    - interaction – a flow; an image only if an interaction board or render exists, else text-only;
    - hospitality & branded items – when the brief has points of those types;
    - graphic design – only if boards exist in `pack/boards/`. Otherwise there is no page, and the response table says "另行提交" / "submitted separately".
11. **Appendix**, at most three pages:
    - design-point responses: a table, point in plain language | A | B | C | pages. No IDs, no citations;
    - claims needing client confirmation: built from the claims actually used on the slides, in plain wording, with their page numbers;
    - dimension check: the plans of all concepts (massing images are allowed here, and only here), captioned with size and open sides; no PASS, no paths.

**Never generated:** an assumptions table, an ideas-considered table, a references page, venue or tender images, placeholder pages.

Design-point types decide which pages answer each point (`data-covers` on the page lists the IDs as an attribute; they never show as text):

| Type | Answered on |
| --- | --- |
| space | project; zones & flow |
| theme | insight; every concept board |
| brand | every concept board; materials |
| content | what the booth says; every detail page |
| product | screens & products; zones & flow |
| screen | screens & products |
| interactive | interaction |
| hospitality | hospitality & branded items; zones & flow |
| giveaway | hospitality & branded items |
| graphic | graphic design (only with boards in pack/boards/; else "另行提交" in the response table) |
| other | no page of its own: put its ID in `data-covers` of the page that really answers it |

The "what the brief asks" page and the response table list every point but cover none, so the coverage check means something. Every design point must be covered by at least one page, unless it is a graphic point marked "另行提交".

## What the proposal may show

Only our own work for this project, and the client's logo:
- chosen usable renders: hero, front and detail views made by render.py, each with its `.json` sidecar, none blocked;
- the plans (`concepts/<L>/plan.png|svg`) and the site diagram deck.py draws (`pack/site.svg`);
- boards in `pack/boards/`;
- massing images (`concepts/<L>/massing-*.png`), in the appendix only;
- the client's logo file named in brief/deck-style.json.

It never shows a reference image (the client's previous booth, booths or renders anyone likes, other companies' work, tender illustrations, stock photos), any file from `input/` or `brief/media/` or a copy of one, a venue image, or a data: or remote image. References go to the image model and the designer only.

`check` enforces this. It scans every URL-bearing attribute (src, srcset, href, xlink:href, data, poster…), every `<style>` block and style attribute, and the tokens block. It resolves every path with realpath and rejects data:, http(s): and // sources. It compares every image's content (hash) with every file in input/ and brief/media/. The logo named in deck-style.json is the one exception.

## Never narrate references

References are inputs, never content. No text describes a reference or the road from it: "the same stand as last year, made deeper", "starting from that structure", "an upgrade of the old stand", "like the previous stand", "how it relates to the reference", "starting point: the client's booth". Each concept is described on its own merit: idea, experience, what it says, atmosphere.

`check` refuses these terms anywhere in the deck, appendix included: 旧展台, 老展台, 旧门框, 老门框, 那道门框, 参考图, 参考照片, previous stand, reference image. It also refuses every term on a `Do-not-mention:` line in brief/style-cards.md.

## Showcase and explanation pages

- **Showcase pages** let the image or one sentence lead, with few words: cover, divider, statement, overview, board, image, stage.
- **Explanation pages** organise facts so a reviewer can scan them: agenda, facts, cards, plan, detail, compare, flow, gallery, table.

**Fixed by the template:** the colour tokens, type scale, spacing, grid, page chrome (running header, page number, draft stamp, "recommended" tag, "to be confirmed" tag) and the markup of each component. Do not add CSS, inline font sizes, colours or positions.

**Free for you:**
- Which component and variant each page uses; adding, removing and reordering pages within the page plan.
- Which usable image a page shows, and its crop: `style="object-position:50% 30%"` on the img.
- Every word on every page.
- A concept's own accent on that concept's pages: `style="--accent:#HEX"` on the section (deck.py sets it from `accent:` in concept.md and adjusts it if it is too faint on its page).
- At most two `free` pages, for a composition no component gives.

To change a page's component, copy that component's example section from template.html, keep its classes and slot structure, give it a unique `data-id`, carry over `data-covers` and `data-concept`, and move the words and the image across. Never keep the template's example image: `check` rejects data: images. Repeated units (cards, zones, steps, rows, swatches) may be deleted or duplicated with the next slot number. Never patch the structure by hand (nested figures, leftover attributes): change the inputs and run `new --force`.

## Component catalogue

Budgets are the template's `data-max` values and count Chinese characters. In an English deck deck.py has already multiplied them by 1.8 (letters and spaces). The `data-max` in the deck is the budget that `check` enforces. A page title in the header bar has a budget of 22 (26 on tables).

| Component | Purpose | Slots and budgets | Variants |
| --- | --- | --- | --- |
| cover | first page: the title on the lead render | eyebrow 30 · title 18 · subtitle 36 (split 40) · meta 40 · logo tile | bleed (render fills the page), split (text left, render or site diagram right) |
| agenda | contents, up to 7 groups | item 12 · description 30 · page number automatic | – |
| divider | section opener on the primary colour | number · title 12 · sub 40 | split (render on the right half) |
| statement | one big sentence: insight, idea, promise | label 12 · statement 48 (`<b>` on a key phrase) · source 50 | – |
| cards | 2–6 points side by side | lead 60 · kicker 12 · card title 14 · body 80 | n2 (title 18, body 120), n3, n4 (title 10, body 60), n6 (kicker 12, title 12, body 44, no lead) |
| facts | key–value facts beside an image, or text only | lead 50 · key 6 · value 28 · up to 7 rows (5 with a lead) | with image, text-only |
| overview | all concepts side by side, one column each (2–4) | name 8 · second name 24 · manifesto 22 · idea 60 | class `rec` on the recommended column |
| board | a concept's main page: render and idea | name 8 · second name 30 · manifesto 30 · paragraph 100 | framed (whole render), bleed (render to the page edge, cropped), mirror (render left) |
| image | full-bleed render | caption 30 | – |
| stage | render on a dark page with a caption column | name 10 · view 16 · caption 70 | – |
| plan | plan drawing, three key figures, numbered zones | key figure (number + unit) · zone 8 · zone note 16 · up to 8 zones · note 60 | – |
| detail | four moments, what it says, palette, why choose it | moment 40 · headline 16 · message 22 (×3) · swatch name 6 (×4, HEX shown) · atmosphere 44 · signature, system, intensity 14 · why choose it 60 | – |
| compare | concepts × five rows, recommended column marked | name 8 · second name 24 · row label 6 · cell 36 | class `rec` on the recommended column's cells |
| flow | 3–6 numbered steps | lead 60 · step title 10 · step text 44 (30 with six steps) | with an image below (only a real one), text-only |
| gallery | 1–4 images with captions | caption 30 (g1: 80) | g1, g2, g3, g4 |
| table | appendix tables; continues on the next slide with "(cont.)" | cells as set in the deck (e.g. 40 / 60) · foot 80 | column widths via `col style="width:N%"` |
| free | own composition on a 12 × 6 grid | `col-N span-N row-N rows-N`, text classes `t-*`, colours `c-*` / `bg-*` (tokens only) | at most 2 per deck |

Slots named `lbl-*` are fixed labels (translated automatically in an English deck); rewrite one only when the page says something else.

## The loop

1. **New.** From the project folder: `python <skill-dir>/scripts/deck.py new --lead <letter>`. Choose the lead from the critique scores and say why in one line. deck.py fills what the project holds (event facts, design points, message platform, usable renders, plans, concept texts), draws pack/site.svg and lists every page with its covers.
2. **Fill every TODO** in `pack/proposal.html`:
   - `TODO: hint` asks for new writing; `TODO: <project text>` is project text over budget: cut it, keep its meaning.
   - Write to the budget. Short beats full; aim near the budget on detail pages, or the page shows a gap in the middle.
   - Every line of copy traces to brief/content.md or concept.md; never invent facts, numbers or claims. Numbers must appear in brief/*.md, concept.md or geometry.json.
   - Describe what the chosen images actually show; text, images and plan present the same stand. Content that is designed but not in the image is "设计意图" / "design intent".
   - Put a sign-off claim in an element with `data-claim="C<n>"` (the content ID, as an attribute only); the tag shows automatically. Use one wording per claim throughout.
   - Write like the creative director: concrete nouns, short sentences, no IDs, citations, file names or notes to ourselves anywhere, appendix included.
3. **Check:** `deck.py check`. Fix every error, read every warning (below).
4. **Render:** `deck.py render`. It refuses while check has errors. Otherwise it writes the PDF, rebuilds `pack/preview/` (`slide-NN.png` and `contact.png`) and adds the overflow check to `pack/check.txt` ("slide 9 A-board para overflows by 64 px").
5. **Look.** Read contact.png, then every slide named in the overflow lines and every showcase page at full size. Look for overflow, crops that cut the hero, empty bands, a page that repeats another, text that contradicts the image.
6. **Fix** and go back to step 3. At most three rounds; then report what is still open to the user, never on a slide.

## Check

`deck.py check` writes `pack/check.txt` and exits 1 on errors. `render` refuses to export while there are errors.

**Errors**
- Image provenance: any image that is not on the list in "What the proposal may show" (all URL-bearing attributes, style blocks and the tokens block scanned; realpath; data:, http(s): and // rejected; hash compared with input/ and brief/media/).
- A blocked render placed.
- A massing image outside the appendix.
- A hero render reused on the materials or interaction page.
- Text lint, outside and inside the appendix:
  - internal IDs `\b[DRACP]\d{1,2}\b`; "s.4"-style citations (`s\.\d`);
  - file names and paths (.png, .jpg, .json, .md, `renders/`, `concepts/`);
  - TODO; 待出图, 待修图, 待补充, 待出稿, 待确认图; PASS, FAIL;
  - reference narration (the terms in "Never narrate references" and the style card's `Do-not-mention:` terms).
- A design point no page covers; a page reference that does not list every answering page; agenda text that names no existing page; a sign-off claim used without its tag.
- Missing image files; a booth render outside `figure.render`; a slot over its `data-max`; duplicate or missing `data-id`.

**Warnings**
- One image file on more than 2 pages other than the cover, overview and board.
- English working notes in a zh deck.
- proposal.pdf older than proposal.html (also in `status`).
- Numbers in slide text found in no brief/*.md, concept.md or geometry.json; more than 3 pages in a row without an image (appendix excluded); colour pairs with too little contrast.

## Rules

- Never edit the `<style id="tokens">` block by hand. Change brief/deck-style.json and run `deck.py style`. Never edit `style#design` or `script#viewer`.
- Booth renders always sit in `figure.render`, which draws the draft stamp. Use the unstamped render from `concepts/<L>/renders/`, not the already stamped `A-1-hero.png` (it would carry two stamps). Plans, the site diagram, massing and boards go in `figure.pic.contain`.
- No text inside generated images: never ask the image model for a slide, title, label, diagram, name, year, number or the logo. Every word on a page is HTML.
- No placeholders in the proposal. A page whose image is missing uses its text-only variant or is left out. Never fill a gap with a stock photo, another concept's render, the hero again or a made-up figure.
- Do not type page numbers: `data-ref` elements (agenda, "见第 X 页", response tables, the claims list) are filled and refreshed by `check` and `render`.
- Keep `data-id` unique and `data-covers` on the page that really answers each point.
- In a zh deck, leave out a concept's English second name unless the client is bilingual, and use metric only.
- When a proper name (a concept or product name) cannot be cut to its budget, raise that one slot's `data-max` to its length and let `render`'s overflow check confirm it fits.
- `style` changes only the tokens. To pick up a changed template, new concepts, another lead, a new design point or a blocked render, run `new --force`: the old deck is kept as `work/deck-backups/proposal.<time>.html`, never in pack/; copy your written text back from it.
- For an internal review, `<html data-show-covers>` prints each page's design-point IDs at its foot; remove it before rendering for the client.
- pack/ holds only proposal.html, proposal.pdf, check.txt, preview/, site.svg and boards/. Backups, review screenshots and files from other projects go to work/.

## Sharing

Send only `pack/proposal.pdf` (one 16:9 page per slide), after `status` confirms it is newer than proposal.html. Never send the project folder, a zip of it, or proposal.html with its linked files: the folder holds the tender, the references and the internal cards. In a browser, `?slide=N` shows one slide at full size, for internal viewing.

## Without a browser

`check` needs no browser. `render` looks for Chrome or Edge (`--browser`, the BROWSER variable, PATH, the standard install folders); without one it says so. Then, once check passes: open `pack/proposal.html` in Chrome or Edge, print to PDF (Save as PDF, margins none, background graphics on) as `pack/proposal.pdf`, and open `proposal.html?check=1` to see the overflow report at the bottom of the page. Without any file access, give the proposal as text, following references/proposal-pack.md.

## Commands

- `python <skill-dir>/scripts/deck.py new [--lang zh|en] [--lead B] [--force]` – build the skeleton from the project; with `--force` the old deck goes to work/deck-backups/.
- `python <skill-dir>/scripts/deck.py style` – rewrite only the colour, font, header and stamp tokens from brief/deck-style.json.
- `python <skill-dir>/scripts/deck.py check` – errors and warnings into pack/check.txt; exit 1 on errors.
- `python <skill-dir>/scripts/deck.py render [--browser PATH] [--jobs 4]` – refuses on errors; otherwise the PDF, a rebuilt preview folder, the contact sheet and the overflow check.
- `python <skill-dir>/scripts/deck.py status` – pages, open TODOs, last check, outputs, and a warning when proposal.pdf is older than proposal.html.
- All commands take `--project <folder>`; the default is the current folder.
