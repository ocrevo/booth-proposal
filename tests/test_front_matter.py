"""concept.md front matter: parse_front_matter and read_front_matter."""
import pytest

import common

FULL = ("\ufeff---\nchosen: renders/hero-v3.png\nblocked: renders/hero-v1.png\n"
        "blocked: \"renders/hero-v2.png\"\n# note\n\naccent: #1F5FAE\n---\nnotes")
FULL_DICT = {"chosen": "renders/hero-v3.png", "blocked": ["renders/hero-v1.png", "renders/hero-v2.png"],
             "accent": "#1F5FAE"}
EMPTY = {"chosen": None, "blocked": [], "accent": None}


@pytest.mark.parametrize("case", [
    "full", "full_crlf", "old_chosen_line",
    "no_closing", "unknown_key", "two_chosen", "bad_accent", "no_colon", "empty_value",
])
def test_parse(case):
    if case in ("full", "full_crlf"):
        text = FULL.replace("\n", "\r\n") if case == "full_crlf" else FULL
        fm, body, findings = common.parse_front_matter(text)
        assert fm == FULL_DICT and body == "notes" and findings == []
    elif case == "old_chosen_line":
        text = "Notes\nchosen: renders/hero-v2.png\n"
        fm, body, findings = common.parse_front_matter(text)
        assert fm == EMPTY and body == text and findings == []
    else:
        text = {
            "no_closing": "---\nchosen: renders/x.png\n",
            "unknown_key": "---\nlead: yes\n---\n",
            "two_chosen": "---\nchosen: renders/a.png\nchosen: renders/b.png\n---\n",
            "bad_accent": "---\naccent: #12345\n---\n",
            "no_colon": "---\nchosen renders/x.png\n---\n",
            "empty_value": "---\nchosen:\n---\n",
        }[case]
        _, _, findings = common.parse_front_matter(text)
        assert len(findings) == 1
        assert findings[0].code == "G-FM" and findings[0].level == "error"


@pytest.mark.parametrize("value,expect_error", [
    ("../../set-2/A/renders/hero-v1.png", True),
    ("renders/hero-v9.png", True),
    ("/abs.png", True),
    ("renders/hero-v2.png", False),
    (None, False),          # concept without concept.md
])
def test_read_paths(project, value, expect_error):
    concept_md = project / "concepts" / "set-1" / "A" / "concept.md"
    concept = common.concept_ref(common.find_project(str(project)), "set-1/A")
    if value is None:
        concept_md.unlink()
        assert common.read_front_matter(concept) == (EMPTY, [])
        return
    concept_md.write_text(f"---\nchosen: {value}\n---\n", encoding="utf-8", newline="\n")
    fm, findings = common.read_front_matter(concept)
    if expect_error:
        assert [f.code for f in findings] == ["G-FM"]
        assert findings[0].where == "concepts/set-1/A/concept.md:2"
        assert fm["chosen"] is None
    else:
        assert findings == [] and fm["chosen"] == "renders/hero-v2.png"
