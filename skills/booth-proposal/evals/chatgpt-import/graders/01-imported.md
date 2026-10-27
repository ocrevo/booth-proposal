---
type: llm
focus: trace
weight: 1
---

set-1-A-1.png, set-1-A-2.png and set-1-B-1.png are each brought in with `render.py import` and the `--concept` their file name names (set-1/A or set-1/B), so each lands as a hero-v<k> render with a sidecar of mode `import`; no image is copied into renders/ by hand.
