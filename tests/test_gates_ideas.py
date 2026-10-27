"""gates.py ideas: validation rules and --scaffold."""
import copy

import pytest

import common


def _ideas(root):
    return common.read_json(str(root / "brief" / "ideas.json"))


def _save_ideas(root, data):
    common.write_json(str(root / "brief" / "ideas.json"), data)


def _idea(data, set_id, idea_id):
    entry = next(e for e in data["sets"] if e["set"] == set_id)
    return next(i for i in entry["ideas"] if i["id"] == idea_id)


def _drop_references(root):
    brief = common.read_json(str(root / "brief" / "brief.json"))
    del brief["references"]
    common.write_json(str(root / "brief" / "brief.json"), brief)


def _unknown_set(d):
    d["sets"][0]["set"] = "set-9"


def _dup_set(d):
    d["sets"].append(copy.deepcopy(d["sets"][0]))


def _same_type(d):
    _idea(d, "set-1", "B")["booth_type"] = "A Gate  you walk through"


def _same_type_other_set(d):
    _idea(d, "set-2", "A")["booth_type"] = "a gate you walk through"


def _insight_blank(d):
    d["insights"][0]["source"] = ""


def _insight_judgement(d):
    d["insights"][0]["source"] = ""
    d["insights"][0]["judgement"] = True


def _idea_id_space(d):
    _idea(d, "set-1", "B")["id"] = "A B"


def _idea_id_dup(d):
    _idea(d, "set-1", "B")["id"] = "A"


def _insight_id(d):
    d["insights"][0]["id"] = "X1"


def _chosen_str(d):
    _idea(d, "set-1", "A")["chosen"] = "yes"


# case -> (mutation, expected rule or None for "passes", expected count of that rule or None)
IDEAS_CASES = {
    "full": (None, None),
    "unknown_set": (_unknown_set, "set"),
    "dup_set": (_dup_set, "set"),
    "same_type": (_same_type, "same-type"),
    "same_type_across_sets": (_same_type_other_set, None),
    "insight_no_source": (_insight_blank, "source"),
    "insight_judgement": (_insight_judgement, None),
    "idea_id_space": (_idea_id_space, "id"),
    "idea_id_dup": (_idea_id_dup, "id"),
    "insight_id": (_insight_id, "id"),
    "chosen_str": (_chosen_str, "field"),
    "no_references": ("refs", "set"),
}


@pytest.mark.parametrize("case", list(IDEAS_CASES))
def test_ideas(make_project, run_gates, has, case):
    root = make_project(renders=False)
    mutate, rule = IDEAS_CASES[case]
    if mutate == "refs":
        _drop_references(root)
    elif mutate:
        data = _ideas(root)
        mutate(data)
        _save_ideas(root, data)
    code, out, err = run_gates(root, "ideas")
    if rule is None:
        assert code == 0 and "RESULT: PASS" in out, out + err
        return
    assert code == 1, out + err
    assert has(out, "G-IDEAS", rule), out
    if case == "no_references":
        assert len(has(out, "G-IDEAS", "set")) == 2
        assert has(out, "G-REFS", "stale")


def test_scaffold(make_project, run_gates, has):
    root = make_project(scaffold=False, renders=False)
    code, out, _ = run_gates(root, "ideas")
    assert code == 1 and len(has(out, "G-IDEAS", "folder")) == 4, out
    assert not (root / "concepts").exists()
    code, out, err = run_gates(root, "ideas", "--scaffold")
    assert code == 0, out + err
    for key in ("set-1/A", "set-1/B", "set-2/A", "set-2/B"):
        folder = root / "concepts" / key
        assert (folder / "renders").is_dir()
        assert (folder / "concept.md").read_bytes() == b"---\n---\n"
    assert not (root / "concepts" / "set-1" / "C").exists()

    keep = make_project(scaffold=False, renders=False)
    note = keep / "concepts" / "set-1" / "A" / "concept.md"
    note.parent.mkdir(parents=True)
    note.write_bytes(b"keep these bytes\n")
    code, out, err = run_gates(keep, "ideas", "--scaffold")
    assert code == 0, out + err
    assert note.read_bytes() == b"keep these bytes\n"
    assert (keep / "concepts" / "set-1" / "B" / "renders").is_dir()

    legacy = make_project(legacy=True, scaffold=False, renders=False)
    data = _ideas(legacy)
    data["sets"][0]["ideas"].append({"id": "C", "name": "Pier", "idea": "A long jetty",
                                     "booth_type": "a facade you face", "chosen": True})
    _save_ideas(legacy, data)
    code, out, err = run_gates(legacy, "ideas", "--scaffold")
    assert code == 0, out + err
    assert (legacy / "concepts" / "_legacy" / "C" / "renders").is_dir()
