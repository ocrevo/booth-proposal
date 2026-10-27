---
type: llm
focus: trace
weight: 1
---

Step 6 ran in order: brief/deck-style.json (lang zh, the logo copied to brief/brand/) and brief/design-points.md exist; `deck.py new` built pack/proposal.html; every TODO was filled; `deck.py check` ended in PASS with no errors; `deck.py render` wrote pack/proposal.pdf after that check, so the PDF is newer than the HTML and has one page per slide. Any `new --force` backup is in work/deck-backups/, not in pack/. The reply tells the user to send only pack/proposal.pdf, never the project folder, a zip of it or the HTML.
