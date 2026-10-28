# Architecture: tender

The default, used when brief.json names no architecture. It follows the tender: the brief recapped, the design answered clause by clause, one page saying what is submitted separately (execution, price), a response table. General rules: `references/6-proposal.md`.

Optional chapters are triggered only by the kinds of the brief's `clauses`, `deliverables` and `graphics` (1-brief.md). Without numbered clauses, pages and table follow the design points.

## Chapters

| Chapter | Required when | Holds |
| --- | --- | --- |
| `cover` | always | title, the lead render, client and event |
| `understanding` | always | project and event, the stand space (optionally `pack/site.svg`), the asks in plain words |
| `design` | always | the concepts (boards, plans, annotated views, compare when several), then pages per design clause, in clause order |
| `interaction` | kind `interaction` | what visitors do, the content, the route |
| `graphics` | `brief.json graphics` or kind `graphics` | one `graphic` page per requested graphic |
| `separate` | kind `execution` or `price` | the separate page |
| `appendix` | always | the response table, then the sign-off list |

`deck.py new` writes the chapters this brief requires (`gates.py architectures` lists them); a missing one is a D-STRUCT `chapter` error, one out of order a warning. A design clause may get its own card (`data-clause="2"` with a `data-ref`); its number may show, its `source` never; a mixed clause's card also points to the separate page.

## The separate page

`deck.py new` writes it (layout `statement:separate`): the labels title, the fixed sentence ("The schedule, on-site staffing and pricing are submitted separately.") and an item per clause (`n` and `title`, else text) and deliverable (`title`) of kind `execution` or `price`. Never write on it: one page, no other text, no figure (D-NUMBER `separate`; the listed clause numbers pass). Such a clause whose text has a digit needs a `title` without digits (G-BRIEF `title`). After a brief change, emit it again (`deck.py layouts --emit statement:separate --chapter separate`), set `data-id="separate"`, replace the old page.

## Graphics pages

After the graphics divider, one page per brief graphic: `deck.py layouts --emit graphic --graphic GR1` (`graphic:wide` when landscape) shows its chosen, reviewed render (4-renders.md, `## Graphics`). Write the kicker, headline and line over it and the notes beside it (where it hangs, what it says). A brief graphic without a page is a D-STRUCT `graphic` error.

## Response table

The appendix skeleton (layout `table`, role `response`; `--emit table --count N` for more rows). One row per clause (`data-clause="<n>"` on the `tr`) and per deliverable (`data-deliverable="DL1"`): clause number (a deliverable: its title) | our response in plain words | pages (`<span data-ref="<page-id>"></span>`). Execution and price rows point to the separate page (`data-ref="separate"`); a mixed clause (`["design", "execution"]`) to its design pages and the separate page. Up to 9 rows per slide; more go on a second response page, also `data-part="appendix"`. Then the sign-off page.

## Storyboard example

Nordvik Ferries, clauses 2 (design), 5 (interaction), 7 (execution), 8.1 (price), graphic GR1:

```
| page | chapter | role | purpose | image | covers |
| cover | cover | cover | the lounge in one image | set-1/A chosen | |
| understanding | understanding | divider | what the tender asks | | |
| design | design | divider | two concepts | | |
| a-board | | board | Concept A | set-1/A chosen | D1 |
| a-plan | | plan | A on the floor | set-1/A plan | D1 |
| interaction | interaction | divider | trying the app | | |
| app | | annotated | the app zone | set-1/A chosen | D2 |
| graphics | graphics | divider | the graphics | | |
| gr1 | | graphic | back wall panel | GR1 chosen | |
| separate | separate | text | items 7 and 8.1 | | |
| appendix | appendix | response | rows 2, 5, 7, 8.1 | | |
| claims | | signoff | flagged claims | | |
```
