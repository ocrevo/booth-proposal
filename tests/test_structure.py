"""Structure rules for the scripts (contract 7.1): no CJK, no removed names, shared API present."""
import ast
import re

import pytest

import common
import factory

SCRIPTS = factory.SCRIPTS
SKILL = SCRIPTS.parent

REMOVED_NAMES = {
    "load_concepts", "md_section", "md_value", "md_path", "md_bullets", "md_tables", "split_name",
    "palette_names", "first_paragraph", "first_sentence", "clean_say", "plan_pages", "build_section",
    "BUILDERS", "fact_rows", "claims_table", "geometry_facts", "reference_images", "load_points",
    "FACT_KEYS", "MATERIAL_KEYS", "HINTS", "LABELS", "LBL_EN", "TYPE_PAGES", "TYPES", "LAYOUTS",
    "VARIANTS", "DRAFT_NOTE", "DRAFT_NOTE_EN", "EN_BUDGET",
}
B_FUNC = re.compile(r"^b_[a-z]+$")

# Scripts not migrated yet: (test, file) -> phase that cleans it. Strict, so that phase removes the mark.
XFAIL = {}


def _params(kind):
    out = []
    for path in sorted(SCRIPTS.glob("*.py")):
        reason = XFAIL.get((kind, path.name))
        marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
        out.append(pytest.param(path, marks=marks, id=path.name))
    return out


def _module_names(tree):
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append((node.name, node.lineno, isinstance(node, ast.ClassDef)))
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        for t in targets:
            for sub in ast.walk(t):
                if isinstance(sub, ast.Name):
                    names.append((sub.id, node.lineno, False))
    return names


@pytest.mark.parametrize("path", _params("cjk"))
def test_no_cjk_in_scripts(path):
    text = path.read_text(encoding="utf-8")
    hits = [f"{n}:{col}" for n, line in enumerate(text.split("\n"), 1)
            for col, ch in enumerate(line, 1) if common.is_cjk(ch)]
    assert not hits, f"{path.name} has CJK characters at line:col " + ", ".join(hits[:20])


@pytest.mark.parametrize("path", _params("names") + [pytest.param(None, id="files")])
def test_no_removed_names(path):
    if path is None:
        assert not (SCRIPTS / "deck_build.py").exists()
        assert not list((SKILL / "assets").rglob("plan.json"))
        return
    text = path.read_text(encoding="utf-8")
    bad = []
    for name, line, is_class in _module_names(ast.parse(text)):
        if name in REMOVED_NAMES or (not is_class and B_FUNC.match(name)):
            bad.append(f"{name} (line {line})")
    if "layout_of(" in text:
        bad.append("layout_of(")
    assert not bad, f"{path.name}: " + ", ".join(bad)


EXPORTS_1A = (
    "SKILL_DIR _SET_ID_RE _CONCEPT_ID_RE _LEGACY_SET _IMAGE_EXTS DEFAULTS ROLES MARK_TYPES Finding InputError "
    "print_findings read_json read_json_opt write_json sha256_file sha256_text now_iso real inside Project "
    "find_project load_labels thresholds ConceptRef list_concepts concept_ref concept_of_path "
    "scan_reference_sets parse_front_matter read_front_matter unit_factor to_m is_cjk has_cjk cjk_ratio "
    "find_term hex_rgb luminance contrast legible").split()


def test_common_exports_1a():
    missing = [n for n in EXPORTS_1A if not hasattr(common, n)]
    assert not missing, missing
