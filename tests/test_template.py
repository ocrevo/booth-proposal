"""Template v2 rules (phase 3 step 3): one parametrised test, one case per rule."""
import re

import pytest

import common
import deck_html

SRC = open(deck_html.DEFAULT_TEMPLATE, encoding="utf-8-sig").read()
ROOT = deck_html.parse(SRC)
EXAMPLES = deck_html.slides_of(ROOT)


def _layout(sec):
    cls = sec.classes()
    return cls[1] if len(cls) > 1 else "", ".".join(cls[2:])


def _slot_names(node):
    return [s.get("data-slot") for s in deck_html.leaf_slots(node)]


def _no_cjk():
    assert not common.has_cjk(SRC)


def _no_removed():
    names = [s.get("data-slot") for s in deck_html.slot_nodes(ROOT)]
    assert not [n for n in names if n in ("sig", "sys", "int", "note")]
    assert not [n for n in names if n.startswith("lbl-")]
    assert not [n for n in ROOT.iter() if n.tag == "blockquote" and n.has_class("note")]
    for word in ("covers-tag", "data-show-covers", "data-covers"):
        assert word not in SRC, word


def _roles():
    for sec in EXAMPLES:
        roles = (sec.get("data-roles") or "").split()
        assert roles, sec.get("data-id")
        assert set(roles) <= set(common.ROLES), (sec.get("data-id"), roles)


def _one_repeat():
    for sec in EXAMPLES:
        groups = {n.get("data-repeat") for n in sec.iter() if n.get("data-repeat") is not None}
        assert len(groups) <= 1, (sec.get("data-id"), groups)


def _todo():
    for sec in EXAMPLES:
        for s in deck_html.leaf_slots(sec):
            assert s.text().strip().startswith("TODO"), (sec.get("data-id"), s.get("data-slot"))


def _palette():
    m = re.search(r":where\(:root\)\s*\{(.*?)\}", SRC, re.S)
    assert m
    block = m.group(1)
    for _key, var in deck_html.COLOR_VARS:
        assert not re.search(re.escape(var) + r"\s*:", block), var


def _components():
    have = {_layout(sec) for sec in EXAMPLES}
    for want in [("gallery", f"g{k}") for k in range(1, 5)] + [("annotated", "")]:
        assert want in have, want


def _compare():
    sec = next(s for s in EXAMPLES if _layout(s)[0] == "compare")
    unit = next(n for n in sec.iter() if n.get("data-repeat") is not None)
    assert _slot_names(unit) == ["c1-name", "c1-why-k", "c1-why", "c1-next-k", "c1-next"]


CASES = {
    "no-cjk": _no_cjk, "no-removed": _no_removed, "roles": _roles, "one-repeat": _one_repeat, "todo": _todo,
    "palette": _palette, "components": _components, "compare": _compare,
}


@pytest.mark.parametrize("rule", list(CASES))
def test_template(rule):
    CASES[rule]()
