"""Shipped label files: same key tree, contract values, word-list rule."""
import json
import os
import re

import common

LABELS = os.path.join(common.SKILL_DIR, "assets", "labels")


def _load(lang):
    with open(os.path.join(LABELS, f"{lang}.json"), encoding="utf-8") as f:
        return json.load(f)


def _tree(d):
    return {k: _tree(v) if isinstance(v, dict) else None for k, v in d.items()}


def test_labels():
    zh, en = _load("zh"), _load("en")
    assert _tree(zh) == _tree(en)
    assert zh["lang"] == "zh" and en["lang"] == "en"
    assert "schema" not in zh and "schema" not in en
    for d in (zh, en):
        assert set(d["report"]) == {"brief", "ideas", "renders", "concepts", "pass", "fail", "none", "cost_line"}
        assert d["chrome"]["concept"].count("{}") == 1
        for fmt in d["ref_formats"].values():
            assert isinstance(fmt.format(3), str)
    assert zh["stamp"] == "\u521d\u7a3f \u2013 \u6982\u5ff5\u6548\u679c\u793a\u610f\uff0c\u4e0d\u7528\u4e8e\u65bd\u5de5"
    assert en["stamp"] == "Draft \u2013 concept visualization, not for construction"
    assert zh["budget_factor"] == 1.0 and en["budget_factor"] == 1.8


def test_word_list_rule():
    lists = ["reference_phrases", "evolution_words", "comparison_words", "todo_markers", "source_headers"]
    for lang in ("zh", "en"):
        d = _load(lang)
        for name in lists:
            for entry in d[name]:
                cjk = sum(1 for ch in entry if common.is_cjk(ch))
                words = re.findall(r"[A-Za-z][A-Za-z'-]*", entry)
                if name == "reference_phrases":
                    ok = cjk >= 2 or len(words) >= 2
                else:
                    ok = cjk >= 2 or any(len(w) >= 2 for w in words)
                assert ok, f"{lang}.{name}: {entry!r}"
                assert cjk != 1, f"{lang}.{name}: single CJK character {entry!r}"
