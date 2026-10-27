"""Render docs (phase 1, S6): references/4-renders.md and the image part of references/review.md hold their anchors."""
import json
import os

import pytest

import common

REFS = os.path.join(common.SKILL_DIR, "references")
FIXED = json.loads(open(os.path.join(common.SKILL_DIR, "assets", "prompts", "fixed.json"), encoding="utf-8").read())

RENDERS_ANCHORS = ["--dry-run", "render.py lint", "Never start a second call", "401", "429", "Retry-After",
                   "| Problem | Correction sentence |", "render.py import", "render.py sheet", "--concept set-1/A",
                   "only stop"]
REVIEW_ANCHORS = list(common.MARK_TYPES) + ["--scope full", "premium", "render.py tiles", "sheet --set",
                                            "--reviewer self"]

CASES = ([pytest.param("4-renders.md", a, id=f"4-renders:{a}") for a in RENDERS_ANCHORS]
         + [pytest.param("4-renders.md", v, id=f"4-renders:fixed.{k}") for k, v in FIXED.items()]
         + [pytest.param("review.md", a, id=f"review:{a}") for a in REVIEW_ANCHORS])


@pytest.mark.parametrize("doc, anchor", CASES)
def test_docs_anchors(doc, anchor):
    with open(os.path.join(REFS, doc), encoding="utf-8") as f:
        text = f.read()
    assert anchor in text
