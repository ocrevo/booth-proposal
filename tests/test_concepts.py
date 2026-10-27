"""Concept folders: list_concepts, concept_of_path, concept_ref."""
import pytest

import common


def test_list_concepts(project):
    (project / "concepts" / "set-1" / "notes").mkdir()
    (project / "concepts" / "readme.txt").write_text("x", encoding="utf-8")
    bad = project / "concepts" / "bad name" / "X"
    bad.mkdir(parents=True)
    (bad / "concept.md").write_text("---\n---\n", encoding="utf-8")
    p = common.find_project(str(project))
    found = common.list_concepts(p)
    assert [c.key for c in found] == ["set-1/A", "set-1/B", "set-2/A", "set-2/B"]
    by_key = {c.key: c for c in found}
    assert by_key["set-1/A"].dir != by_key["set-2/A"].dir
    assert by_key["set-2/B"].set == "set-2" and by_key["set-2/B"].id == "B"
    hero = project / "concepts" / "set-2" / "B" / "renders" / "hero-v1.png"
    assert common.concept_of_path(p, str(hero)).key == "set-2/B"
    assert common.concept_of_path(p, str(project / "input" / "refs" / "set-1" / "r01.png")) is None


@pytest.mark.parametrize("key,ok", [
    ("set-1/A", True),
    ("set-1/Z", False),
    ("A", False),
    ("set-1/A/x", False),
    ("set-1\\A", False),
])
def test_concept_ref(project, key, ok):
    p = common.find_project(str(project))
    if ok:
        assert common.concept_ref(p, key).key == key
    else:
        with pytest.raises(common.InputError) as ei:
            common.concept_ref(p, key)
        assert ei.value.code == "C-INPUT"
