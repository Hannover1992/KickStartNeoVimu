"""
test_stage_slice_schema.py — Tests fuer BL-392 batch_1 (AK-SLICE-SCHEMA).

Der globale Stage-Slice-Schema-Validator prueft einen 8-Slice-Satz einer Stage
(`_index`/`execute`/`setup`/`teardown`/`health_check`/`resources`/
`concurrency_class`/`exit_criteria`):

  - Pflicht IMMER: _index + execute + exit_criteria.
  - Pflicht WENN resources.infrastruktur NICHT in {none, skip}: setup + teardown
    + health_check (Spiegel von tdd_stages_ready.stage_needs_infra).
  - skip-Sentinel ("skip"/"none") ist KONFORM (nicht missing); ein LEERER Slice
    (Datei da, aber Concern-Feld weder gesetzt noch skip/none) ist BLOCK mit
    korrektivem Recovery-Hint (verschaerft tdd_stages_ready._is_missing:
    key-missing/null = Defekt, explizit-skip = OK).
  - Eingabe: Verzeichnis mit NN.md-Slices ODER ein dict (Slice-Name -> fm-dict).
  - Ausgabe: {valid, missing_slices, errors}.

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_stage_slice_schema.py     (repo-root)
  py -3 -m pytest test_stage_slice_schema.py                     (scripts-cwd)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from stage_slice_schema import (
    ALWAYS_REQUIRED_SLICES,
    CANONICAL_SLICES,
    DECLARATION_SLICES,
    INFRA_CONDITIONAL_SLICES,
    SLICE_CONCERN_FIELD,
    SliceSchemaResult,
    slice_needs_infra,
    validate_slice_dict,
    validate_slice_set,
)

# ---------------------------------------------------------------------------
# Fixtures: ein 8-Slice-Set als dict (Slice-Name -> Frontmatter-dict)
# ---------------------------------------------------------------------------

# Vollstaendiger Infra-Stage-Slice-Satz (alle 8 Slices belegt, infra=docker).
_INFRA_SLICE_SET = {
    "_index": {"stufe": 3, "name": "integration", "slice_map": {}},
    "execute": {"testbefehl": "dotnet test", "testtyp": "integration"},
    "setup": {"commands": ["startup"], "timeout_min": 5, "idempotent": True},
    "teardown": {"commands": ["shutdown"], "always_run": True},
    "health_check": {"command": "docker info", "retries": 10, "interval_sec": 5},
    "resources": {"infrastruktur": "docker", "teilbar": "unteilbar"},
    "concurrency_class": {"concurrency_class": "isolated", "depends_on": ["docker_stack"]},
    "exit_criteria": {"qg": "pass", "tests_gruen": "ja"},
}

# Nicht-Infra-Stage (Unit-Test): setup/teardown/health_check sind skip-Sentinel.
_NONE_SLICE_SET = {
    "_index": {"stufe": 1, "name": "atomic", "slice_map": {}},
    "execute": {"testbefehl": "pytest tests/unit/", "testtyp": "unit"},
    "setup": {"skip": True},
    "teardown": {"skip": True},
    "health_check": {"skip": True},
    "resources": {"infrastruktur": "none", "teilbar": "teilbar"},
    "concurrency_class": {"concurrency_class": "parallel"},
    "exit_criteria": {"qg": "pass", "tests_gruen": "ja"},
}


def _write_slice_set(base: Path, slice_set: dict) -> Path:
    """Schreibe einen Slice-Satz als NN.md-Dateien (slice_name.md) in ein Verzeichnis."""
    import yaml

    base.mkdir(parents=True, exist_ok=True)
    for name, fm in slice_set.items():
        text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n# " + name + "\n"
        (base / f"{name}.md").write_text(text, encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# Strukturelle Konstanten — Regressions-Wachen
# ---------------------------------------------------------------------------


def test_canonical_slices_are_eight() -> None:
    """Genau 8 kanonische Slices (W-AK-MON: Monitor in execute, KEIN 9.)."""
    assert len(CANONICAL_SLICES) == 8
    assert set(CANONICAL_SLICES) == {
        "_index",
        "execute",
        "setup",
        "teardown",
        "health_check",
        "resources",
        "concurrency_class",
        "exit_criteria",
    }


def test_always_required_three() -> None:
    """_index + execute + exit_criteria immer Pflicht."""
    assert set(ALWAYS_REQUIRED_SLICES) == {"_index", "execute", "exit_criteria"}


def test_infra_conditional_three() -> None:
    """setup + teardown + health_check sind infra-konditional (Spiegel INFRA_REQUIRED_SECTIONS)."""
    assert set(INFRA_CONDITIONAL_SLICES) == {"setup", "teardown", "health_check"}


def test_declaration_two() -> None:
    """resources + concurrency_class sind Deklarations-Slices."""
    assert set(DECLARATION_SLICES) == {"resources", "concurrency_class"}


# ---------------------------------------------------------------------------
# slice_needs_infra — Spiegel von tdd_stages_ready.stage_needs_infra
# ---------------------------------------------------------------------------


def test_needs_infra_true_for_docker() -> None:
    assert slice_needs_infra({"infrastruktur": "docker"}) is True


def test_needs_infra_false_for_none() -> None:
    assert slice_needs_infra({"infrastruktur": "none"}) is False


def test_needs_infra_false_for_skip() -> None:
    """skip-Sentinel auf der resources-infrastruktur == keine Infra-Pflicht (BL-392-Naht)."""
    assert slice_needs_infra({"infrastruktur": "skip"}) is False


def test_needs_infra_false_for_missing_key() -> None:
    """Kein infrastruktur-Feld == none-Default (Abwaertskompat)."""
    assert slice_needs_infra({}) is False


# ---------------------------------------------------------------------------
# validate_slice_dict: PASS-Faelle
# ---------------------------------------------------------------------------


def test_infra_complete_dict_valid() -> None:
    """Vollstaendiger 8-Slice-Infra-Satz -> valid."""
    res = validate_slice_dict(_INFRA_SLICE_SET)
    assert res.valid is True
    assert res.missing_slices == []
    assert res.errors == []


def test_none_stage_skip_slices_valid() -> None:
    """Nicht-Infra-Stage mit setup/teardown/health_check=skip -> valid (skip ist konform)."""
    res = validate_slice_dict(_NONE_SLICE_SET)
    assert res.valid is True
    assert res.missing_slices == []


# ---------------------------------------------------------------------------
# validate_slice_dict: BLOCK-Faelle
# ---------------------------------------------------------------------------


def test_missing_mandatory_slice_invalid() -> None:
    """Fehlender Pflicht-Slice (execute) -> invalid + in missing_slices."""
    s = dict(_INFRA_SLICE_SET)
    del s["execute"]
    res = validate_slice_dict(s)
    assert res.valid is False
    assert "execute" in res.missing_slices


def test_missing_index_invalid() -> None:
    """Fehlender _index-Slice -> invalid."""
    s = dict(_NONE_SLICE_SET)
    del s["_index"]
    res = validate_slice_dict(s)
    assert res.valid is False
    assert "_index" in res.missing_slices


def test_missing_exit_criteria_invalid() -> None:
    """Fehlender exit_criteria-Slice -> invalid."""
    s = dict(_NONE_SLICE_SET)
    del s["exit_criteria"]
    res = validate_slice_dict(s)
    assert res.valid is False
    assert "exit_criteria" in res.missing_slices


def test_infra_stage_missing_setup_invalid() -> None:
    """Infra-Stage (infrastruktur=docker) OHNE setup-Slice -> invalid + Recovery-Hint."""
    s = dict(_INFRA_SLICE_SET)
    del s["setup"]
    res = validate_slice_dict(s)
    assert res.valid is False
    assert "setup" in res.missing_slices
    # Korrektiver Recovery-Hint (feedback_corrective_enforcement): konkreter Pfad.
    setup_errs = [e for e in res.errors if e.slice == "setup"]
    assert len(setup_errs) == 1
    hint = setup_errs[0].recovery_hint
    assert hint is not None
    assert "setup" in hint
    assert "infrastruktur" in hint


def test_empty_slice_blocks() -> None:
    """Leerer Slice (Datei da, Concern weder gesetzt noch skip/none) -> BLOCK + Hint."""
    s = dict(_INFRA_SLICE_SET)
    s["execute"] = {}  # leer: kein testbefehl, kein skip/none
    res = validate_slice_dict(s)
    assert res.valid is False
    exec_errs = [e for e in res.errors if e.slice == "execute"]
    assert len(exec_errs) == 1
    assert exec_errs[0].recovery_hint is not None
    # Leer-Slice ist NICHT "missing" (Datei/Key da), sondern ein Empty-Defekt.
    assert "execute" not in res.missing_slices


def test_skip_sentinel_not_empty() -> None:
    """Ein skip-Sentinel-Slice ist KONFORM, wird NICHT als leer geblockt."""
    s = dict(_INFRA_SLICE_SET)
    s["resources"] = {"infrastruktur": "none"}  # none -> keine Infra
    s["setup"] = {"skip": True}
    s["teardown"] = {"none": True}
    s["health_check"] = {"skip": "skip"}
    res = validate_slice_dict(s)
    assert res.valid is True


def test_infra_stage_empty_setup_blocks_not_missing() -> None:
    """Infra-Stage mit LEEREM setup-Slice (da, aber leer) -> BLOCK als Empty, nicht Missing."""
    s = dict(_INFRA_SLICE_SET)
    s["setup"] = {}  # da, aber leer (kein commands, kein skip)
    res = validate_slice_dict(s)
    assert res.valid is False
    setup_errs = [e for e in res.errors if e.slice == "setup"]
    assert len(setup_errs) == 1
    assert "setup" not in res.missing_slices  # da, also nicht missing
    assert setup_errs[0].recovery_hint is not None


def test_skip_on_index_blocks() -> None:
    """skip auf _index (Identitaets-Anker) -> BLOCK: Always-Required darf nicht geskippt werden."""
    s = dict(_NONE_SLICE_SET)
    s["_index"] = {"skip": True}
    res = validate_slice_dict(s)
    assert res.valid is False
    idx_errs = [e for e in res.errors if e.slice == "_index"]
    assert len(idx_errs) == 1
    # Hint sagt klar: nicht skippbar.
    assert "Pflicht" in idx_errs[0].recovery_hint
    assert "_index" not in res.missing_slices  # da, also Empty-Defekt nicht Missing


def test_skip_on_execute_blocks() -> None:
    """skip auf execute (Ausfuehrungs-Anker) -> BLOCK: kein echter Testbefehl = nicht konform."""
    s = dict(_NONE_SLICE_SET)
    s["execute"] = {"skip": True}
    res = validate_slice_dict(s)
    assert res.valid is False
    assert any(e.slice == "execute" for e in res.errors)


def test_skip_on_exit_criteria_blocks() -> None:
    """skip auf exit_criteria (Abnahme-Anker) -> BLOCK."""
    s = dict(_NONE_SLICE_SET)
    s["exit_criteria"] = {"skip": True}
    res = validate_slice_dict(s)
    assert res.valid is False
    assert any(e.slice == "exit_criteria" for e in res.errors)


def test_empty_resources_declaration_blocks() -> None:
    """Leerer resources-Deklarations-Slice (infrastruktur fehlt, kein skip) -> Empty-BLOCK.

    Auch ohne Infra-Pflicht: resources ist Deklarations-Slice und muss seinen
    Concern (infrastruktur) tragen oder skip/none deklarieren.
    """
    s = dict(_NONE_SLICE_SET)
    s["resources"] = {}  # leer: kein infrastruktur, kein skip
    res = validate_slice_dict(s)
    assert res.valid is False
    assert any(e.slice == "resources" for e in res.errors)


def test_skip_resources_declaration_conform() -> None:
    """resources als explizites skip/none -> konform (Deklarations-Slice, nicht Always-Required)."""
    s = dict(_NONE_SLICE_SET)
    s["resources"] = {"none": True}
    res = validate_slice_dict(s)
    assert res.valid is True


# ---------------------------------------------------------------------------
# validate_slice_set: Verzeichnis-Eingang
# ---------------------------------------------------------------------------


def test_validate_dir_complete_infra(tmp_path: Path) -> None:
    """Verzeichnis mit vollstaendigem Infra-Slice-Satz -> valid."""
    d = _write_slice_set(tmp_path / "stage_3_integration", _INFRA_SLICE_SET)
    res = validate_slice_set(d)
    assert res.valid is True
    assert res.missing_slices == []


def test_validate_dir_missing_slice_file(tmp_path: Path) -> None:
    """Verzeichnis ohne execute.md-Datei -> invalid + execute in missing_slices."""
    d = _write_slice_set(tmp_path / "stage_3_integration", _INFRA_SLICE_SET)
    (d / "execute.md").unlink()
    res = validate_slice_set(d)
    assert res.valid is False
    assert "execute" in res.missing_slices


def test_validate_dir_none_stage_skip(tmp_path: Path) -> None:
    """Verzeichnis mit skip-Slices (Nicht-Infra) -> valid."""
    d = _write_slice_set(tmp_path / "stage_1_atomic", _NONE_SLICE_SET)
    res = validate_slice_set(d)
    assert res.valid is True


def test_validate_dir_missing_directory(tmp_path: Path) -> None:
    """Nicht-existentes Verzeichnis -> invalid (alle Pflicht-Slices missing), kein Crash."""
    res = validate_slice_set(tmp_path / "does_not_exist")
    assert res.valid is False
    # Mindestens die 3 Always-Required fehlen.
    for must in ("_index", "execute", "exit_criteria"):
        assert must in res.missing_slices


# ---------------------------------------------------------------------------
# Ergebnis-Form
# ---------------------------------------------------------------------------


def test_result_shape() -> None:
    """SliceSchemaResult traegt valid/missing_slices/errors (Ausgabe-Vertrag)."""
    res = validate_slice_dict(_INFRA_SLICE_SET)
    assert isinstance(res, SliceSchemaResult)
    assert isinstance(res.valid, bool)
    assert isinstance(res.missing_slices, list)
    assert isinstance(res.errors, list)


def test_slice_concern_field_map_covers_all() -> None:
    """SLICE_CONCERN_FIELD deckt jeden kanonischen Slice ab (Leer-Erkennung)."""
    for slice_name in CANONICAL_SLICES:
        assert slice_name in SLICE_CONCERN_FIELD
