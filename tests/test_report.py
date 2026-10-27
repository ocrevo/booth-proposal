"""gates.py report brief|ideas."""
import pytest

import common


@pytest.mark.parametrize("case", ["brief_zh", "brief_en", "ideas_en", "out_file", "unknown_lang", "renders"])
def test_report(make_project, run_gates, tmp_path, case):
    if case in ("brief_zh", "brief_en"):
        lang = case.split("_")[1]
        root = make_project(lang=lang, renders=False)
        code, out, err = run_gates(root, "report", "brief")
        assert code == 0, out + err
        title = common.load_labels(lang)["report"]["brief"]
        assert out.startswith("# " + title)
        for row in ("| D1 |", "| D2 |", "| A2 |", "| C1 |"):
            assert row in out, row
        for row in ("| A1 |", "| C2 |"):
            assert row not in out, row
    elif case == "ideas_en":
        root = make_project(renders=False)
        code, out, err = run_gates(root, "report", "ideas")
        assert code == 0, out + err
        assert "4 concepts × 2 candidates = 8 images, about 14 min" in out
    elif case == "out_file":
        root = make_project(renders=False)
        target = tmp_path / "out" / "r.md"
        code, out, err = run_gates(root, "report", "ideas", "--out", str(target))
        assert code == 0, out + err
        assert out.startswith("wrote ")
        text = target.read_text(encoding="utf-8")
        assert text.startswith("# ") and "## set-1" in text
    elif case == "unknown_lang":
        root = make_project(renders=False)
        brief = common.read_json(str(root / "brief" / "brief.json"))
        brief["lang"] = "xx"
        common.write_json(str(root / "brief" / "brief.json"), brief)
        code, out, err = run_gates(root, "report", "brief")
        assert code == 2 and "C-INPUT" in err
    elif case == "renders":
        root = make_project(renders=False)
        code, out, err = run_gates(root, "report", "renders")
        assert code == 2
