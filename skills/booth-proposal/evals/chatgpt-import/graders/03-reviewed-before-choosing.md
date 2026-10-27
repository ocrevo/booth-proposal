---
type: llm
focus: trace
weight: 1
---

Every imported candidate is reviewed with `render.py review` before any `chosen:` line is written, and a render chosen for a concept has a current review of scope `full` and verdict `pass`; when none passes, the user is told and nothing failing is chosen.
