# Proposal

The proposal shows design: the idea and the image first, then how the stand answers the brief. `pack/proposal.html` is the single source: 16:9 slides (1920 × 1080 px) from `assets/deck/template.html`, exported to `pack/proposal.pdf`. You write every page; the deck commands check, measure and export. Only selected concepts (`brief/selection.json`) appear.

These rules hold for every architecture. The chapters come from it (`brief.json proposal.architecture`, else deck-style `thresholds.architecture`, else `tender`): read `references/arch-tender.md` or `references/arch-showcase.md` too.

## Inputs

- `brief/brief.json`: `lang` (labels, budgets); `design_points` (page references); `clauses`, `deliverables`, `graphics`; flagged `claims`; `do_not_mention`; IDs and `source` texts, which must never show.
- `brief/selection.json` (from `gates.py select`): `selected`, `lead`, display letters.
- concept.md and graphic.md front matter: `chosen`, `blocked`, (concept) `accent`. Notes are not parsed, but D-NUMBER accepts numbers in concept notes.
- A selected concept's `geometry.json` and `plan.svg`/`plan.png`; `brief/brand/`, the official logo files.
- `brief/deck-style.json` (no `schema` key): `header` (running header and HTML title: client · event · "stand design proposal"); `stamp` (draft note on renders; default the labels `stamp`); `logo` (path relative to `brief/`, placed on the cover by `deck.py new`; never a photo crop or a reference file); `fonts.sans`; `colors` (any of `paper surface tint line muted muted_text ink ink_strong primary primary_alt accent brand_extra warn`, `#HEX` from the brand guide; leave out what you do not know); `thresholds` (`appendix_pages_max`, `image_reuse_max`, `upscale_max`, `architecture`, …).

## Storyboard

Before any HTML, write `deck/storyboard.md`, one row per page:

```
| page | chapter | role | purpose | image | covers |
| a-board | design | board | Concept A in one image | set-1/A chosen | D1, D4 |
| a-plan | | plan | how A works on the floor | set-1/A plan | D2 |
```

`page` becomes the slide's `data-id` (`[a-z0-9][a-z0-9-]*`, unique), `chapter` its `data-chapter` (on a chapter's first page; the chapter runs to the next one), `role` its `data-role` (`cover agenda divider overview board compare annotated plan materials interaction response signoff text graphic`), `covers` its `data-covers`: the design points the page really answers, a note for the page references, never shown. The architecture file has a full example.

Coverage is proven by the Pass 1 quotes (review.md), not by `data-covers`.

## What never goes in

- Engineering drawings, schedule, staffing or price figures, venue technical items; a tender names them on its separate page only.
- Internal working: IDs (`D`, `C`, `A`, `I`, `GR`, `DL`), citations, `source` texts, file names, paths, set names, TODO, PASS/FAIL, notes to ourselves, assumptions or ideas tables, the critique and its risks. A tender's own clause numbers (`2`, `8.1`) may show.
- References in any form (SKILL.md `## Reference sets`): no reference photo, no file from `input/` or `brief/media/`, no word about one.
- Massing, labelled copies, unchosen or unreviewed renders and graphics, unselected concepts, remote images.

## Template

**Fixed:** tokens, type, grid, page chrome and each layout's markup; never edit `style#tokens`, `style#design` or `script#viewer` by hand; no inline sizes, colours or positions. **Free:** layout per page, order, repeat units, every word, the image and its crop (`style="object-position:50% 30%"`), accents, the `free` layout (sparingly).

- `deck.py new`: head, tokens, `html lang`, logo, the cover and a skeleton page per required chapter (`data-id` = `data-chapter` = its id); it prints the optional ones. An existing deck → exit 1; `deck.py new --force` first moves it to `work/backup/proposal.<time>.html` (copy your text back).
- `deck.py style` rewrites tokens after deck-style edits. `deck.py layouts` lists each layout's roles, repeat unit, image kinds, slot budgets (`data-max`), chapters.
- `deck.py layouts --emit LAYOUT[:VARIANT] --count N`: one slide with the layout's first role, empty `data-id`, `data-covers` and `src`, N repeat units. `--chapter ID` makes it open that chapter. Paste it after the last slide, before `script#viewer`; set `data-id`, `data-covers`, `data-concept`, each `src`, every slot. Switch `data-role` to another listed role when the page has that job (`facts` as `materials`).

- `figure.render`: one render `img`, stamped by CSS; `src` = the concept's `chosen`, relative to `pack/`: `../concepts/set-1/A/renders/hero-v3.png`.
- `figure.pic` (`.contain` letterboxes): plans and the site diagram.
- `figure.render.annotated`: one render plus `.pin` callouts (`data-x`, `data-y` in percent). A `materials` or `interaction` page shows a render only this way.
- `figure.graphic`: a chosen graphic, text over its empty area, on a `graphic` page; `--emit graphic --graphic GR1` fills `src`, `data-ratio`, `data-area`. `data-tone`: `dark` (default) or `light`.
- `data-auto` text comes from the labels and the brief (`new`, `--emit`); never edit it.
- No `figure` in a `figure`, no `.placeholder`; an unfilled slot reads "TODO".
- Never type page numbers: `data-ref="D3"` (first three pages answering D3) or `data-ref="<page-id>"`, `data-ref-style="num"` for a bare number; `deck.py render` writes them.
- `data-clause="8.1"` (a clause `n`) or `data-deliverable="DL2"` on a table row or a card names the brief item it answers, with a `data-ref` inside; checked only where the architecture answers by clauses.
- A flagged claim sits in an element with `data-claim="C2"`; CSS draws the tag.
- Keep words in slots: `deck.py text` and the review read only slots, plus `data-auto` text as `[auto]` lines.

## The loop

1. `deck/storyboard.md`; 2. `deck.py new`; 3. `deck.py layouts --emit` per page, paste; 4. write every slot.
5. `deck.py check` (read-only; `deck.py check --json` also writes `work/check.json` for `status`). Fix every error; read warnings and pending items.
6. `deck.py render`: refreshes page references, prints check counts (it renders even with errors), writes `work/proposal-draft.pdf`, `work/preview/slide-NN.png`, `work/contact.png` and `work/render.json` (overflow, upscale). Look at the contact sheet, then each overflowing page, every board and graphic page at full size for crops cutting the hero, text hard to read, empty bands, repeated pages, text contradicting the image.
7. Repeat 5–6 until no errors and zero overflow; after at most three fix rounds, report what is still open to the user, never on a slide.
8. Pass 1 and Pass 2 (review.md), then `deck.py review --record work/deck-review.input.json`; if `deck.py check` then reports D-REF `stale` (page references moved), run `deck.py render` again.
9. `deck.py export`.

After a later change: `deck.py text --diff`, review those pages, record, export.

## Check codes

`deck.py check` exits 0 (no errors), 1 (errors), 2 (unusable input, an unknown architecture included). E error (blocks export), W warning, P pending (decided in Pass 1). Messages start with the rule.

| Code | Lvl | Rules | What to do |
| --- | --- | --- | --- |
| D-IMG-URL | E | `scheme`: `data:`, `http(s):`, `//`, another scheme or a `<base>`; `missing`: empty URL or no file; `outside`: outside the project | a project file, relative to `pack/` |
| D-IMG-FORBIDDEN | E | `forbidden`: content of a reference, `input/` or `brief/media/` file or a graphic's product photo; `logo-ref`: logo equals a reference; `kind`: a kind the architecture does not allow (showcase: graphic), or not a render, plan, logo, graphic or `pack/site.svg`; `massing`; `label`: a `render.py label` copy | remove; logo from `brief/brand/` |
| D-IMG-RENDER | E | `sidecar`: missing or hash differs; broken base chain; `review`: no current `full` pass; `unselected`; `not-chosen`; `blocked`; plan `stale`: other geometry.json; graphic `kind`: no graphic sidecar, `unlisted`, `stale`: another ratio | the chosen, reviewed image; redraw |
| D-PLACE | E | `figure`: render not an `img` in `figure.render`, graphic not in `figure.graphic`; `hero`: render on `materials`/`interaction` outside `figure.render.annotated`; `role`: graphic off a `graphic` page; `area`, `ratio`: differ from the graphic's `--area` or brief ratio | move it; emit with `--graphic` |
| D-STRUCT | E | `id`: `data-id` missing, duplicate or malformed; `role`: unknown; `cover`: none; `board`: selected concept without its board; `nest`; `placeholder`; `graphic`: a graphic page without one, a brief graphic without a page; `tone`: not `dark` or `light` | fix the markup |
| D-STRUCT | E, W | `chapter`: unknown, pages before the first, a required one missing (E), out of order (W); `separate`: more than one page, the fixed sentence missing, other text, a wrong or missing item; `clause`, `deliverable`: unknown item, no `data-ref`, two table rows or none, a separate item not pointing to the separate page; `points`: a design point in no clause or deliverable (W) | the architecture file |
| D-REF | E | `target`: empty, unknown, or a point no page covers yet; `stale`: text differs from the computed text | fix target or `data-covers`; `deck.py render` |
| D-TXT-INTERNAL | E | `todo`: TODO, TBD, PASS, FAIL …; `id`: a brief or ideas ID; `set`: set name; `file`: file name or project path; `source`: a brief `source` text; `source-col`: source column header; also the `--header`, `--stamp` tokens | rewrite as client text |
| D-TXT-REFERENCE | E | `dnm`: a `do_not_mention` phrase; `phrase`: a labels reference phrase ("previous stand") | rewrite on the concept's own merit |
| D-TXT-PENDING | P | `evolution` ("builds on"), `comparison` ("than before") word | Pass 1: `keep` (brand language) or `narrates_reference` (rewrite) |
| D-CLAIM | E | `untagged`: flagged claim (its numbers or `keys`) without `data-claim`; `signoff`: no `signoff` page carries it | tag it; list it |
| D-NUMBER | W, E | a number (two or more digits, or with a unit) not in brief.json, ideas.json, the header, or a selected concept's concept.md, geometry.json, facts (W); `separate`: a figure on the separate page other than its clause numbers (E) | correct it; remove it |
| D-LAYOUT | W | `max`: slot over `data-max`; `imageless`: over `imageless_run_max` body pages without an image; `appendix`: over `appendix_pages_max`; `upscale`: over `upscale_max` (measured); `legibility`: text on a graphic below 3:1 contrast | cut; add an image; merge; larger file; other `data-tone` |
| D-REUSE | W | one image on over `image_reuse_max` counted pages (not cover, overview, board, compare, nor the lead's render on `annotated`) | a plan or another page design |
| D-OVERFLOW | E | measured overflow in `work/render.json` of this deck | cut text or change layout |
| X-CHECK | E | `errors` in the check | `deck.py check` |
| X-RENDER | E | `missing`, `unmeasured`, `stale`, `overflow` | `deck.py render`, fix overflow |
| X-REVIEW | E | `missing`; `page` without entry; `stale` text or images; `open` Pass 2 finding; `pending` word without `keep` | review.md, `deck.py text --diff`, record |
| X-PDF | E, exit 3 | `browser`: no Chrome or Edge; `pages`: no PDF or page count ≠ slides | `--browser PATH`; fix the spilling slide |

The check also reports G-SELECT (no selection: `gates.py select`), C-LEGACY (a v1 sidecar) and C-INPUT (exit 2).

## Writing

- Short, vivid sentences, concrete nouns: "a wall of clear glass tubes catching the light", not "an innovative, premium display". "Immersive" or "cutting-edge" must name the material, light or form that does the work.
- Describe what the chosen render shows; names and counts match the image, positions match geometry.json. Designed content not in the image is "design intent".
- Text over a graphic is short: a kicker, a headline, one line, drawing on the claims its `content` names.
- One unit system per deck; a Chinese deck is metric only, without English second names unless the client is bilingual.

## Rules

- No placeholders: a page without its image uses a text layout or goes; never a stock photo, another concept's render or the hero again.
- Every word is HTML. `figure.render` stamps renders; `render.py label` is for loose images only.
- A proper name over budget: raise that slot's `data-max`; render confirms the fit.
- To pick up a changed template, new concepts, another lead, another architecture, a new design point or a blocked render, run `deck.py new --force` and copy your text back from `work/backup/`.

## Sharing

Send only `pack/proposal.pdf`, after `deck.py status` says it is newer than the deck; never the folder, a zip or the HTML.

Without a browser (exit 3, X-PDF): clear the check, review what you can, hand over `pack/proposal.html` for the user to print from Chrome or Edge to `pack/proposal.pdf` (margins none, background graphics on); say which gates did not run.

## Commands

| Command | Does | Exit |
| --- | --- | --- |
| `deck.py new [--template T] [--force]` | shell with the cover and the required chapters | 0, 1, 2 |
| `deck.py style [--template T]` | tokens only | 0, 2 |
| `deck.py layouts [--emit LAYOUT[:VARIANT]] [--count N] [--chapter ID] [--graphic GR]` | catalogue or one fragment | 0, 2 |
| `deck.py check [--json]` | findings, read-only | 0, 1, 2 |
| `deck.py render [--browser PATH] [--jobs 4] [--budget 8000]` | previews, measurement | 0, 2, 3 |
| `deck.py text [--diff]` | slide text blocks | 0, 2 |
| `deck.py review --record FILE` | stamps `work/deck-review.json` | 0, 1, 2 |
| `deck.py export [--browser PATH]` | gates, then `pack/proposal.pdf` | 0, 1, 3 |
| `deck.py status` | one-paragraph summary | 0 |
