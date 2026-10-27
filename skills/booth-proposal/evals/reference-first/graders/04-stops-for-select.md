---
type: llm
focus: trace
weight: 1
---

After the set's candidate board (`render.py sheet --set ref-prev --candidates`) and the overview (`render.py sheet --chosen-all`), the run stops and asks the user to select concepts. It does not run `gates.py select`, writes no brief/selection.json, and starts no step 5 or 6 work (no geometry.json, plan or proposal).
