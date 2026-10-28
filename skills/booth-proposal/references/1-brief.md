# Step 1 – Brief

The brief is what the client asked for, in a form the gates can read. The data lives in `brief/brief.json`; the reading notes (`brief/*.md`) are free text for you and are never parsed.

## Steps

1. Give every file a role (assume the likeliest when unclear). Client material (RFP, brand guide, logos, product photos) stays in `input/`; reference photos go in `input/refs/<set>/`.
2. Read the RFP and every client file completely, including text inside images (render small print larger). Images extracted from documents go in `brief/media/` (never shown); official logo files in `brief/brand/`.
3. Write the notes below and `brief/brief.json`. Notes cite items by id (`D3`, `C2`, `A1`) and never copy them; a new run reuses them and updates only what changed.
4. When two parts of the files disagree (event dates on one page, show dates on another), record both with their sources and add an assumption naming both and saying which you used. Never pick one silently.
5. Run `python scripts/gates.py brief --stamp`.

## brief.json

| Field | Type | Req | Notes |
|---|---|---|---|
| `schema` | `"brief/2"` | yes | |
| `lang` | string | yes | selects `assets/labels/<lang>.json` |
| `client.names` | string[] ≥1 | yes | every name the client goes by |
| `protected_terms` | string[] | yes (may be `[]`) | product / programme names; never in prompts |
| `do_not_mention` | string[] | yes (may be `[]`) | phrases pointing at a reference object itself ("last season's stand"); entries ≥2 characters |
| `booth` | object | step 2 | `unit` `"m"`\|`"ft"`; `width`, `depth`, `max_height` > 0 in `unit`; `open_sides` ⊆ `front back left right`; `source` string; optional `rigging_allowed` bool\|null (null = not confirmed), `program` string[] (same words as geometry `required`) |
| `design_points[]` | `{id, type, text, source}` | yes | `id` `^D\d+$`; `source` non-empty |
| `claims[]` | `{id, text, flag, source, keys?}` | yes (may be `[]`) | `id` `^C\d+$`; `flag` true = needs client sign-off; `keys` extra match phrases (each ≥2 characters) |
| `assumptions[]` | `{id, text, impact}` | no | `id` `^A\d+$`; `impact` `"high"`\|`"low"` |
| `proposal.architecture` | string | no | from `gates.py architectures`; default `tender` |
| `clauses[]` | `{n, title?, text, source, kind, points?}` | no | below |
| `deliverables[]` | `{id, title, kind, source, points?}` | no | `id` `^DL\d+$` |
| `graphics[]` | `{id, title, purpose, ratio, refs?, content?}` | no | `id` `^GR\d+$` |
| `references` | `{sets: [{id, dir, files: [{path, sha256}]}], stamped_at}` | code | `gates.py brief --stamp` only; sets sorted by id, files by path |

```json
{"schema": "brief/2", "lang": "en", "client": {"names": ["Nordvik Ferries", "Nordvik"]},
 "protected_terms": ["Tidewater Pass"], "do_not_mention": ["last season's stand"],
 "booth": {"unit": "m", "width": 8, "depth": 6, "max_height": 4.5, "open_sides": ["front", "right"], "source": "RFP §3.2"},
 "design_points": [{"id": "D1", "type": "space", "text": "Open, walk-in stand", "source": "RFP §2.1"}],
 "claims": [{"id": "C1", "text": "14 hybrid vessels in service", "flag": true, "source": "Fleet brochure p.4"}]}
```

- `design_points`: one row for each thing the client expects the design to answer (theme, brand, content, products, screens, hospitality, giveaways, space). `type` is a free word. `text` is plain client language, shown in the proposal as written ("Celebrate 75 years of the brand", not "Theme req. per s.4"); id and `source` stay internal. `source` is a file name plus page or section (`tender.pptx s.4`), counted in file order, not by footer numbers.
- `do_not_mention` holds only phrases that point at a reference object itself. The concept's own design words never go there.
- `client.names` and `protected_terms` are refused in prompts (`L-BAN`); `do_not_mention` entries are refused on proposal pages (`D-TXT-REFERENCE`).
- Never write `references` by hand: it holds file hashes, and a hand edit makes `G-REFS` report it stale.
- `booth.unit` is the RFP's unit. Notes give the other system in brackets: 6 m × 3 m (19.7 × 9.8 ft). Copy numbers exactly as written.

## Clauses, deliverables and graphics

The tender architecture builds chapters, the separate page and the response table from these (arch-tender.md).

- `clauses[]`: one per numbered requirement. `n`: the tender's own number as a string (`"2"`, `"8.1"`, `"3a"`), unique; it may show. `text` in plain words; `source`. `kind`: `design`, `interaction`, `graphics`, `material`, `hospitality`, `execution`, `price` or `other`, or a list for a mixed clause (`["design", "execution"]`). `points`: the design points it asks for. `title`, optional, no digits; needed when a separately submitted clause's text has a digit (the separate page lists the title, else the text).
- `deliverables[]`: unnumbered "the proposal must contain" items: `id` `DL1`…, `title` (no digits), `kind`, `source`, optional `points`.
- `graphics[]`: each graphic the tender asks the studio to design (a wall panel): `title`, `purpose`, `ratio` (`2:3`, `16:9`); `refs`, product photos in `input/` to redraw from, never shown; `content`, the claim ids its words may use. Made in `graphics/<id>/` (4-renders.md).
- Put every design point in the `points` of a clause or deliverable (else warning `coverage`).

```json
"clauses": [{"n": "7", "title": "Build schedule", "text": "Build schedule in 3 phases", "source": "Tender p.4 item 7", "kind": "execution"}],
"graphics": [{"id": "GR1", "title": "Fleet story", "purpose": "Back wall panel", "ratio": "2:3", "refs": ["input/product.png"], "content": ["C2"]}]
```

## Requirement notes

`brief/requirement-card.md`: what the client asked, one requirement per row with its source; free notes, never parsed. Hard = the RFP says it must be done or provided (size, height, dates, deliverables); soft = theme, style, tone. Cite brief.json and ideas.json items by id; anything else by its source text. Cover: project (event, organiser, client, venue), dates (conference and exhibition days apart), booth, hard and soft requirements, the design brief (audience, what visitors should feel and remember, brand character in three or four words), deliverables, brand (logo files, colours, mandatory messages). Write in the user's language, with short original quotes where wording matters.

## Venue notes

`brief/venue-card.md` collects the physical and regulatory limits, mostly from the venue's exhibitor manual. Without the manual, assume a sensible value for each missing item and record it as an assumption marked "check exhibitor manual"; never state a venue rule from general knowledge as confirmed.

Look for: booth types and their rules (wall height near aisles and neighbours); height limits for structures, graphics and hanging signs; rigging; fire-retardant certification; electrical deadlines; food and beverage rules; audio and screen limits; build and dismantle times; floor load and fixing. The card is reused across runs: update it only when a manual or a confirmed answer arrives. These feed `brief.json booth` (`max_height`, `rigging_allowed`) and, in step 5, each geometry spec (`height_zones`, `walkway`, `headroom`).

## Content inventory

Content is design material: the most distinctive facts often inspire the insight. Extract every candidate from every client file, wording exact; mark anything uncertain "verify spelling". `brief/content.md` holds the inventory as notes, `| C-id | Type | Text (verbatim) | Source | Flags |`, ids matching `brief.json claims[]`.

- Types: proof, story, product, brand line, entity, action, mandatory. Flags: `number`, `superlative`, `comparative`, `regulated`, `dated`, `verify`, `verify spelling`, `needs translation`.
- Anything `superlative`, `comparative`, `regulated`, `dated` or `verify`, and any number that can change, may be used but becomes a claim with `flag: true`: exact wording, `source`, and `keys` for other ways a page may say it. The check finds a claim by its numbers (at least `claim_min_digits` digits) and its `keys` (`D-CLAIM`).
- Never add facts that are not in the files; content the client has not supplied goes in the notes as "to request from the client".

Selection and hierarchy are step 3 (3-ideas.md).

## Assumptions

If the files are ambiguous or silent, record the best guess in `brief.json assumptions[]` and carry on; do not stop to ask. Base it on evidence first, then on common practice, and choose the option that keeps most doors open (design for two open sides so a third can be added). `impact` is `high` when a wrong guess would change the layout, the brand presentation or compliance with a hard requirement. Worth stating: open sides, main aisle, rigging, power, storage. The proposal words an assumption as a design setting: "assumed for now: open front and right".

## Truth

- Facts come from the files and the user, each with an id and a source; everything you fill in is an assumption, never a fact.
- Every line of booth copy traces to the client's own content. Never invent facts, numbers or claims.
- Claims with `flag: true` carry the sign-off tag wherever the proposal uses them (`data-claim`, see 6-proposal.md).

## Check and show

```
python scripts/gates.py brief --stamp
python scripts/gates.py report brief
```

`--stamp` rewrites `references` from the folders on disk, then the gate checks the file. Exit 1 on:

- `G-BRIEF`: a required field missing or invalid (`field`), an id duplicated or off its pattern (`id`), an item without `source` (`source`), a `do_not_mention` entry under two characters (`dnm`), no `assets/labels/<lang>.json` (`labels`); an unknown architecture in brief.json or deck-style (`architecture`, listing the known ones); a clause number off the pattern or repeated (`clause-n`); an unknown kind (`clause-kind`); an unknown design point (`points`); a title with a digit, or missing (`title`); a `ratio` not like `2:3` (`ratio`); a ref that is no file in `input/` (`graphic-ref`); an unknown claim (`content`). Warning `coverage`: a design point in no clause or deliverable (clause architectures only).
- `G-REFS`: an invalid set name, an empty set folder, or `stale`: the stamped sets differ from the disk. Run `--stamp` again after any change to `input/refs/`.

`C-LEGACY` warns when there is no `input/refs/` (SKILL.md, `## Reference sets`).

`gates.py report brief` prints the design points, the high-impact assumptions and the claims awaiting sign-off; add one line on the assumption that could change the design most.
