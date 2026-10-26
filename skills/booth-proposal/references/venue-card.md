# Venue card – template and checklist

The venue card collects the physical and regulatory limits the design must respect. Most of these come from the venue's exhibitor manual (sometimes called technical guidelines or service manual), not from the client's RFP. If the user has not uploaded it, assume a sensible value for each missing item, record it as an assumption (continuing the A-numbers from the requirement card) and phrase it so the user can check it with the organiser.

Never state a venue rule from general knowledge as if it were confirmed. Rules differ by venue, country and show, so anything not in the files is an assumption marked "check exhibitor manual".

## Template

```
VENUE CARD · v1 · <venue / show>

| Item | Value | Source |
| Build-up window | … | … |
| Dismantle window | … | … |
| Max build height (structure) | … | … |
| Max height for hanging signs / rigging | … | … |
| Rigging / hanging points allowed | yes / no / unknown | … |
| Two-storey structures allowed | yes / no / unknown | … |
| Electrical supply | … | … |
| Floor type and load limit | … | … |
| Fire safety: material certification required | … | … |
| Neighbouring booths / back walls | … | … |
| Labour rules (e.g. union jurisdiction at some US venues) | … | … |
| Food and drink service rules (coffee, catering) | … | … |
| Sound level limits (screens, audio) | … | … |

Assumptions to check with the organiser
| ID | Question | Assumed | Basis | Impact if wrong |
```

These items feed the frame card and every geometry spec: height limits and zones go to `max_height` and `height_zones`, rigging to `rigging_allowed`, and any stated minimum walkway or headroom to `walkway` and `headroom`.

The card lives in `brief/venue-card.md` and is reused across runs: a new run copies it and updates it only when a manual or a confirmed answer arrives.

## Checklist of what to look for in a venue manual

- Booth types and the rules for each (inline, corner, peninsula, island), including how high walls may be near the aisle and near neighbours
- Height limits for structures, graphics and hanging signs
- Rigging rules and who is allowed to install it
- Fire-retardant certification for fabrics, wood and other materials
- Electrical ordering deadlines and connection rules
- Food and beverage rules, especially for serving coffee or snacks
- Audio volume limits and screen placement rules
- Build-up and dismantle times, and who may work on the stand during them
- Floor load limits and whether the hall floor may be drilled or taped
