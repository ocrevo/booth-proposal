# Requirement card – template and rules

The requirement card is the single source of truth for what the client asked for. It works quietly in the background: precise here, brief in front of the user. It also holds the design brief, the human side of the RFP that the concepts are built on. It is an internal card: the proposal takes only the event facts from it (event, venue, dates, size, open sides, height limit) and never shows its IDs, sources, assumptions or deliverables.

It lives in `brief/requirement-card.md` and is reused across runs: a new run copies it instead of reading everything again, and updates it only when files or facts change (raising the version).

## Rules

- One requirement per row. If a sentence in the RFP asks for two things, make two rows.
- Copy numbers exactly as written (sizes, quantities, dates, heights). Do not round or convert in the requirement text; put conversions in brackets.
- Source = file name plus page, slide or section, e.g. `tender.pptx s.4` or `RFP.pdf p.7 §3.2`. Count slides and pages in file order, not by the numbers printed in the document's footer, which often differ (a cover slide is usually unnumbered); say once at the top which convention you use.
- When two parts of the RFP disagree (for example the event dates on one page and the show dates on another), record both with their sources and add an assumption that states which one you used and why. Never pick one silently. When the event has conference days and exhibition days, record both: the proposal's project page shows them apart.
- Hard requirement = the RFP states it must be done or provided (size, height limit, "at least one large screen", dates, deliverables). Soft requirement = theme, style, tone, preferences ("celebrate our 75 years", "use brand colours").
- If the RFP is ambiguous or silent, write the row anyway and add an assumption (A1, A2…) with your best guess. Do not stop to ask. Where the proposal uses an assumed fact (open sides, for example), it reads as a design setting: "暂按前、右两面开口" / "assumed for now: open front and right".
- IDs never clash between cards: R hard requirements, P soft requirements, A assumptions, DL deliverables (here), C content items (brief/content.md), D design points (brief/design-points.md).
- Every requirement that asks something of the design (theme, brand, content, products, screens, interaction, hospitality, giveaways, graphics, space) also becomes a row in brief/design-points.md, written in plain client language (references/proposal-deck.md, Inputs). The proposal answers those rows.
- Write in the user's language. Keep short original-language quotes in quotation marks where wording matters.

## Template

```
REQUIREMENT CARD · v1 · <project short name>

Project
- Event: <name, edition>            Source: <…>
- Organiser / host: <…>             Source: <…>
- Client (exhibitor): <…>           Source: <…>
- Venue: <name, address>            Source: <…>

Dates
- Build-up: <…>   Show: <…>   Dismantle: <…>      Source: <…>
- Conference: <…>   Exhibition: <…>   (only when the event has both)   Source: <…>

Booth
- Size: <W × D> (<area>)            Source: <…>
- Booth type: inline | corner | peninsula | island | unknown
- Open sides: <…>                    Source: <… | assumption A<n>>
- Max height: <…>                    Source: <…>
- Location in hall: <…>              Source: <…>

Hard requirements
| ID | Requirement | Source |
| R1 | … | … |

Design brief
- Audience: <who walks past and why they are at this event>
- What visitors should feel and remember: <…>
- Brand character: <three or four words, from the client's materials>
- Occasion and theme: <…>

Soft requirements (theme, style, tone)
| ID | Requirement | Source |
| P1 | … | … |

Deliverables requested by the RFP
| ID | Deliverable | Covered by this skill? |
| DL1 | Booth design concept | Yes – the proposal |
| DL2 | Graphic designs | Yes, as boards in pack/boards/ – or handled separately ("另行提交" in the response table) |
| DL3 | Itemised price | No – handled separately; never in the proposal |

Brand elements
- Logo files provided: yes/no (<file, slide>). The deck uses the official file, copied to brief/brand/ and named in brief/deck-style.json; if only a crop from a slide exists, request the file
- Brand colours: <names / values if given>
- Slogans or mandatory messages: <…>
- Imagery rules: <e.g. "do not use original product photos">

Materials provided by the client (the detailed content goes into the content inventory, references/content-strategy.md)
| Item | Where |

Assumptions (high impact first)
| ID | Question | Assumed | Basis | Impact if wrong |
| A1 | … | … | <evidence or reasoning> | high / medium / low |
```

## How to assume well

- Base each assumption on evidence in the files first (a floor plan, a photo, the client's materials), then on common practice for this booth size and event type.
- Choose the option that keeps the most doors open (for example, design for two open sides so a third can be added).
- Impact is high when a wrong guess would change the layout, the brand presentation or compliance with a hard requirement.

## Common assumptions worth making explicitly

- Which sides are open, and which aisle carries the main visitor flow
- Exact booth position on the floor plan
- Whether hanging signs or rigging are allowed, and the height limit for them
- Power capacity and where the supply comes in
- Storage room needed for giveaways, coffee supplies or staff belongings
- Whether the RFP's "graphic design" deliverables are separate from the booth graphics
