# Architecture: showcase

A design narrative, only on request (`proposal.architecture: "showcase"`): the client meets the idea and the image first, then sees how the stand answers each design point. No clause or deliverable rows are checked, no separate page. Images: renders, plans, the logo, `pack/site.svg`; a graphic is refused (D-IMG-FORBIDDEN `kind`), so brief graphics are not made. No chapter is required: `deck.py new` writes only the cover. General rules: `references/6-proposal.md`.

## Storyboard

Chapters, all optional, in this order (`data-chapter` on each first page): `cover`, `project`, `brief`, `insight`, `overview`, `concepts`, `compare`, `lead`, `appendix`.

Suggested pages, not a rule (12–16 body pages as a guide): cover, agenda; the project (event facts, optionally a site diagram you draw as `pack/site.svg`: footprint, open sides dashed, main aisle, no concept element); what the brief asks (each point in plain language with its page reference); the insight and what the booth says; overview; the concepts; compare; the lead developed (`annotated`, then `materials`, `interaction` or `text` pages); appendix.

```
| page | chapter | role | purpose | image | covers |
| asks | brief | response | the design points in plain words | | |
| a-board | concepts | board | Concept A in one image | set-1/A chosen | D1, D4 |
| compare | compare | compare | why choose each | | |
```

## Per concept

Every slide of a concept carries `data-concept` = its display letter.
- **Board** (`board`), required per selected concept: the chosen render in `figure.render`, name, one-line manifesto, the idea in a short paragraph.
- **Detail** (`text`, layout `detail`): the experience (10 m, 3 m, inside, photo moment), headline and up to three messages, atmosphere.
- **Plan** (`plan`): the plan in `figure.pic.contain`, key facts, zones numbered as on the plan.
- The lead also gets an **annotated** page: its render in `figure.render.annotated` with `.pin` callouts.

Accent: `style="--accent:#HEX"` on the concept's sections, from front matter `accent`, else `geometry.json` `accent`, else deck-style.

## Compare

One `compare` page; per concept only why choose it (strengths) and the next step (an open risk becomes work we will do). Class `rec` on the lead's column and its overview card draws the "recommended" tag.

## Appendix

At most `appendix_pages_max` slides (3), each `data-part="appendix"`:
1. **Response table** (`response`, layout `table`): design point in plain words | each concept | pages (`data-ref`). No IDs, no citations; a point not shown reads "submitted separately".
2. **Sign-off list** (`signoff`): only the flagged claims used, in plain wording, each in a cell with `data-claim="Cn"` and its pages via `data-ref="<page-id>"`.

Plans sit in the concept chapters; massing never appears.
