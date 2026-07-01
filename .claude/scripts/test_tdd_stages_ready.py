"""
test_tdd_stages_ready.py — Tests fuer AK-3 G-TDD-STAGES-READY (BL-329 batch_2).

Das Gate prueft pro stage_N.md:
  - 11 Basis-Pflichtfelder (stufe..exit_criteria) — unveraendert (BL-033).
  - FUER Infra-Stages (infrastruktur != "none"): zusaetzlich 3 Infra-Sektionen
    setup / teardown / health_check (11 -> 14). Fehlt eine -> BLOCK mit
    korrektivem Recovery-Hint (feedback_corrective_enforcement).
  - Stages mit infrastruktur=none: KEINE Infra-Pflichtfelder (unveraendert).

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_tdd_stages_ready.py     (repo-root)
  py -3 -m pytest test_tdd_stages_ready.py                     (scripts-cwd)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from tdd_stages_ready import (
    BASE_REQUIRED_FIELDS,
    INFRA_REQUIRED_SECTIONS,
    check_stage_file,
    gate_stages_ready,
    stage_needs_infra,
)

# ---------------------------------------------------------------------------
# Fixtures: stage_N.md Bauer
# ---------------------------------------------------------------------------

_BASE_FRONTMATTER = {
    "stufe": 1,
    "name": "Atomic",
    "fokus": "Isolierte Inseln",
    "testbefehl": "pytest tests/unit/ -v",
    "test_projekte": ["tests/unit/"],
    "testpfad": "tests/unit/",
    "fanout": "hoch",
    "mocks_erlaubt": "ja",
    "blueprint_perspektive": "Laserpointer",
    "testtyp": "unit",
    "exit_criteria": ["blueprint_qg: pass", "stufen_tests_gruen: ja"],
}

_INFRA_SECTIONS = {
    "setup": {
        "commands": ["docker-compose up -d"],
        "timeout_min": 5,
        "idempotent": True,
    },
    "teardown": {
        "commands": ["docker-compose down"],
        "timeout_min": 2,
        "always_run": True,
    },
    "health_check": {
        "command": "curl -sk https://localhost:5443/health",
        "retries": 10,
        "interval_sec": 5,
    },
}


def _write_stage(path: Path, frontmatter: dict, body: str = "# Stage\n") -> Path:
    """Schreibe eine stage_N.md mit YAML-Frontmatter."""
    import yaml

    text = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True) + "---\n\n" + body
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture()
def stage_none(tmp_path: Path) -> Path:
    """infrastruktur=none-Stage mit 11 Basis-Feldern (kein Infra noetig)."""
    fm = dict(_BASE_FRONTMATTER)
    fm["infrastruktur"] = "none"
    return _write_stage(tmp_path / "stage_1.md", fm)


@pytest.fixture()
def stage_none_implicit(tmp_path: Path) -> Path:
    """Stage OHNE infrastruktur-Feld (== none-Default) — Abwaertskompat (Bestands-stage_1.md)."""
    fm = dict(_BASE_FRONTMATTER)  # kein infrastruktur-Key
    return _write_stage(tmp_path / "stage_1.md", fm)


@pytest.fixture()
def stage_infra_complete(tmp_path: Path) -> Path:
    """infrastruktur=docker-Stage MIT setup/teardown/health_check (14 Felder)."""
    fm = dict(_BASE_FRONTMATTER)
    fm["stufe"] = 3
    fm["infrastruktur"] = "docker"
    fm.update(_INFRA_SECTIONS)
    return _write_stage(tmp_path / "stage_3.md", fm)


@pytest.fixture()
def stage_infra_missing_setup(tmp_path: Path) -> Path:
    """infrastruktur=docker-Stage OHNE setup-Sektion -> BLOCK."""
    fm = dict(_BASE_FRONTMATTER)
    fm["stufe"] = 3
    fm["infrastruktur"] = "docker"
    fm["teardown"] = _INFRA_SECTIONS["teardown"]
    fm["health_check"] = _INFRA_SECTIONS["health_check"]
    # setup fehlt absichtlich
    return _write_stage(tmp_path / "stage_3.md", fm)


@pytest.fixture()
def stage_infra_missing_health(tmp_path: Path) -> Path:
    """infrastruktur=real-system-Stage OHNE health_check -> BLOCK."""
    fm = dict(_BASE_FRONTMATTER)
    fm["stufe"] = 6
    fm["infrastruktur"] = "real-system"
    fm["setup"] = _INFRA_SECTIONS["setup"]
    fm["teardown"] = _INFRA_SECTIONS["teardown"]
    # health_check fehlt absichtlich
    return _write_stage(tmp_path / "stage_6.md", fm)


@pytest.fixture()
def stage_base_missing_field(tmp_path: Path) -> Path:
    """Stage der ein BASIS-Pflichtfeld vermissen laesst (testbefehl) -> BLOCK."""
    fm = dict(_BASE_FRONTMATTER)
    del fm["testbefehl"]
    fm["infrastruktur"] = "none"
    return _write_stage(tmp_path / "stage_1.md", fm)


# ---------------------------------------------------------------------------
# stage_needs_infra
# ---------------------------------------------------------------------------


def test_needs_infra_true_for_docker() -> None:
    assert stage_needs_infra({"infrastruktur": "docker"}) is True


def test_needs_infra_true_for_real_system() -> None:
    assert stage_needs_infra({"infrastruktur": "real-system"}) is True


def test_needs_infra_false_for_none() -> None:
    assert stage_needs_infra({"infrastruktur": "none"}) is False


def test_needs_infra_false_for_missing_key() -> None:
    """Kein infrastruktur-Feld == none-Default (Abwaertskompat) -> kein Infra."""
    assert stage_needs_infra({}) is False


# ---------------------------------------------------------------------------
# check_stage_file: PASS-Faelle
# ---------------------------------------------------------------------------


def test_none_stage_passes(stage_none: Path) -> None:
    """infrastruktur=none + 11 Basis-Felder -> PASS (keine Infra-Pflicht)."""
    res = check_stage_file(stage_none)
    assert res.ok is True
    assert res.findings == []


def test_none_implicit_stage_passes(stage_none_implicit: Path) -> None:
    """Bestands-Stage OHNE infrastruktur-Key -> PASS (kein Bruch fuer alte stage_1.md)."""
    res = check_stage_file(stage_none_implicit)
    assert res.ok is True


def test_infra_complete_passes(stage_infra_complete: Path) -> None:
    """infrastruktur=docker + setup/teardown/health_check -> PASS."""
    res = check_stage_file(stage_infra_complete)
    assert res.ok is True
    assert res.findings == []


# ---------------------------------------------------------------------------
# check_stage_file: BLOCK-Faelle (korrektiver Recovery-Hint)
# ---------------------------------------------------------------------------


def test_infra_missing_setup_blocks(stage_infra_missing_setup: Path) -> None:
    """Infra-Stage ohne setup -> BLOCK + Recovery-Hint nennt setup.commands."""
    res = check_stage_file(stage_infra_missing_setup)
    assert res.ok is False
    setup_findings = [f for f in res.findings if f.field == "setup"]
    assert len(setup_findings) == 1
    hint = setup_findings[0].recovery_hint
    assert hint is not None
    # Korrektiv: der Hint MUSS einen konkreten Reparatur-Pfad nennen (nicht nur "fehlt").
    assert "setup-Sektion ergaenzen" in hint
    assert "setup.commands" in hint
    assert "health_check" in hint
    assert "teardown.commands" in hint
    assert "stage_3.md" in hint


def test_infra_missing_health_blocks(stage_infra_missing_health: Path) -> None:
    """Infra-Stage ohne health_check -> BLOCK + Recovery-Hint."""
    res = check_stage_file(stage_infra_missing_health)
    assert res.ok is False
    hc_findings = [f for f in res.findings if f.field == "health_check"]
    assert len(hc_findings) == 1
    assert hc_findings[0].recovery_hint is not None
    assert "stage_6.md" in hc_findings[0].recovery_hint


def test_base_missing_field_blocks(stage_base_missing_field: Path) -> None:
    """Fehlendes BASIS-Feld (testbefehl) -> BLOCK (unveraendertes Verhalten BL-033)."""
    res = check_stage_file(stage_base_missing_field)
    assert res.ok is False
    assert any(f.field == "testbefehl" for f in res.findings)


def test_none_stage_no_infra_demands(stage_none: Path) -> None:
    """infrastruktur=none-Stage wird NICHT auf setup/teardown/health_check geprueft."""
    res = check_stage_file(stage_none)
    infra_findings = [f for f in res.findings if f.field in INFRA_REQUIRED_SECTIONS]
    assert infra_findings == []


# ---------------------------------------------------------------------------
# gate_stages_ready: Mehr-Stage-Aggregat
# ---------------------------------------------------------------------------


def test_gate_all_pass(tmp_path: Path) -> None:
    """Mehrere valide Stages (none + complete-infra) -> PASS-Aggregat (ok=True)."""
    none_fm = dict(_BASE_FRONTMATTER)
    none_fm["infrastruktur"] = "none"
    _write_stage(tmp_path / "stage_1.md", none_fm)
    infra_fm = dict(_BASE_FRONTMATTER)
    infra_fm["stufe"] = 3
    infra_fm["infrastruktur"] = "docker"
    infra_fm.update(_INFRA_SECTIONS)
    _write_stage(tmp_path / "stage_3.md", infra_fm)

    res = gate_stages_ready(tmp_path, [1, 3])
    assert res.ok is True
    assert res.exit_code == 0


def test_gate_blocks_on_one_infra_gap(tmp_path: Path) -> None:
    """Eine Infra-Stage mit fehlendem setup -> Aggregat BLOCK (ok=False, exit 2)."""
    none_fm = dict(_BASE_FRONTMATTER)
    none_fm["infrastruktur"] = "none"
    _write_stage(tmp_path / "stage_1.md", none_fm)
    bad_fm = dict(_BASE_FRONTMATTER)
    bad_fm["stufe"] = 3
    bad_fm["infrastruktur"] = "docker"
    bad_fm["teardown"] = _INFRA_SECTIONS["teardown"]
    bad_fm["health_check"] = _INFRA_SECTIONS["health_check"]
    _write_stage(tmp_path / "stage_3.md", bad_fm)

    res = gate_stages_ready(tmp_path, [1, 3])
    assert res.ok is False
    assert res.exit_code == 2
    assert any(f.field == "setup" for f in res.all_findings())


def test_gate_missing_file_blocks(tmp_path: Path) -> None:
    """Fehlende stage-Datei -> BLOCK mit Recovery-Hint (/_TDD_init)."""
    res = gate_stages_ready(tmp_path, [1])
    assert res.ok is False
    miss = [f for f in res.all_findings() if "existiert nicht" in f.message or "missing" in f.message.lower()]
    assert miss
    assert any("_TDD_init" in (f.recovery_hint or "") for f in res.all_findings())


def test_base_required_fields_count() -> None:
    """Regressions-Wache: genau 11 Basis-Pflichtfelder (BL-033)."""
    assert len(BASE_REQUIRED_FIELDS) == 11


def test_infra_required_sections_count() -> None:
    """Regressions-Wache: genau 3 Infra-Sektionen (11 -> 14)."""
    assert len(INFRA_REQUIRED_SECTIONS) == 3
    assert set(INFRA_REQUIRED_SECTIONS) == {"setup", "teardown", "health_check"}


# ---------------------------------------------------------------------------
# BL-392 AK-CONSUMER-REWRITE: Gate-Resolution VIA resolve_vault_stage (Dual-Read)
# ---------------------------------------------------------------------------
# Behavior-preserving: bei nicht-migrierter Stage faellt der Resolver auf den
# Legacy-Monolith im --target-dir zurueck -> die heutige 11+3-Monolith-Validierung
# bleibt unveraendert. Bei migrierter Stage (Vault-Slice-Satz) validiert das Gate
# den 8-Slice-Satz via stage_slice_schema (AK-SLICE-SCHEMA-Nachfolger).

import os  # noqa: E402


@pytest.fixture
def env_guard_tdd():
    """Sichert/Restored CLAUDE_VAULT_ROOT + cwd (Resolver-Tests pinnen Vault via env)."""
    _orig_env = os.environ.get("CLAUDE_VAULT_ROOT")
    _orig_cwd = str(Path.cwd())
    try:
        yield
    finally:
        if _orig_env is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig_env
        os.chdir(_orig_cwd)


def _write_vault_slice_set(vault: Path, n: int, name: str, slice_set: dict) -> Path:
    """Lege `{vault}/Stage/stage_{n}_{name}/` mit {slice}.md-Dateien an."""
    import yaml

    stage_dir = vault / "Stage" / f"stage_{n}_{name}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    for slice_name, fm in slice_set.items():
        text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n# " + slice_name + "\n"
        (stage_dir / f"{slice_name}.md").write_text(text, encoding="utf-8")
    return stage_dir


def test_tdd_stages_ready_imports_resolver() -> None:
    """tdd_stages_ready nutzt resolve_vault_stage (Stage-Resolution NICHT mehr direkt)."""
    import inspect

    import tdd_stages_ready as mod

    src = inspect.getsource(mod)
    assert "resolve_vault_stage" in src, \
        "tdd_stages_ready muss resolve_vault_stage nutzen (kein direkter target_dir/stage_N.md-Read)"


def test_gate_legacy_fallback_passes_like_today(tmp_path: Path, env_guard_tdd) -> None:
    """Dual-Read-Fallback: kein Vault-Slice -> Legacy-Monolith im --target-dir, identisch PASS.

    Exakt das heutige Verhalten: valide Monolith-stage_N.md im --target-dir -> PASS.
    """
    vault = tmp_path / "empty_vault"
    vault.mkdir()
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)  # KEIN Stage/ -> Legacy

    target = tmp_path / "meta"
    target.mkdir()
    none_fm = dict(_BASE_FRONTMATTER)
    none_fm["infrastruktur"] = "none"
    _write_stage(target / "stage_1.md", none_fm)

    res = gate_stages_ready(target, [1])
    assert res.ok is True
    assert res.exit_code == 0


def test_gate_legacy_fallback_blocks_like_today(tmp_path: Path, env_guard_tdd) -> None:
    """Dual-Read-Fallback: Infra-Monolith ohne setup im --target-dir -> BLOCK, wie heute."""
    vault = tmp_path / "empty_vault"
    vault.mkdir()
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    target = tmp_path / "meta"
    target.mkdir()
    bad_fm = dict(_BASE_FRONTMATTER)
    bad_fm["stufe"] = 3
    bad_fm["infrastruktur"] = "docker"
    bad_fm["teardown"] = _INFRA_SECTIONS["teardown"]
    bad_fm["health_check"] = _INFRA_SECTIONS["health_check"]
    # setup fehlt
    _write_stage(target / "stage_3.md", bad_fm)

    res = gate_stages_ready(target, [3])
    assert res.ok is False
    assert res.exit_code == 2
    assert any(f.field == "setup" for f in res.all_findings())


def test_gate_validates_vault_slice_set_when_migrated(tmp_path: Path, env_guard_tdd) -> None:
    """Migrierte Stage: vollstaendiger Vault-Slice-Satz -> PASS (via Slice-Validator)."""
    vault = tmp_path / "vault"
    _write_vault_slice_set(vault, 3, "integration", {
        "_index": {"stufe": 3, "name": "integration"},
        "execute": {"testbefehl": "dotnet test --filter X"},
        "setup": {"commands": ["docker up"]},
        "teardown": {"commands": ["docker down"]},
        "health_check": {"command": "docker info"},
        "resources": {"infrastruktur": "docker"},
        "concurrency_class": {"concurrency_class": "DEPENDS"},
        "exit_criteria": {"qg": "pass"},
    })
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    # target_dir egal — Vault gewinnt (Praezedenz).
    res = gate_stages_ready(tmp_path / "nonexistent_meta", [3])
    assert res.ok is True
    assert res.exit_code == 0


def test_gate_blocks_incomplete_vault_slice_set(tmp_path: Path, env_guard_tdd) -> None:
    """Migrierte Infra-Stage OHNE setup-Slice -> BLOCK (Slice-Validator meldet missing)."""
    vault = tmp_path / "vault"
    # setup-Slice fehlt; resources.infrastruktur=docker -> setup ist Pflicht.
    _write_vault_slice_set(vault, 3, "integration", {
        "_index": {"stufe": 3, "name": "integration"},
        "execute": {"testbefehl": "dotnet test --filter X"},
        "teardown": {"commands": ["docker down"]},
        "health_check": {"command": "docker info"},
        "resources": {"infrastruktur": "docker"},
        "concurrency_class": {"concurrency_class": "DEPENDS"},
        "exit_criteria": {"qg": "pass"},
    })
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    res = gate_stages_ready(tmp_path / "nonexistent_meta", [3])
    assert res.ok is False
    assert res.exit_code == 2
