"""
test_resolve_vault_stage.py — Tests fuer BL-392 batch_2 (AK-GLOB).

Der glob-faehige Stage-Slice-Resolver (`resolve_vault_stage.py`, Option B der
W-GLOB-2-Adjudikation): Schwester-Resolver zu `resolve_vault_meta` (das single-file
bleibt). Er kennt die Vault-Stage-Heimat `{VAULT}/Stage/stage_N_<name>/`, globt die
Stage-Verzeichnisse per Nummer und liefert pro Stage einen `StageHandle` mit:

  - `stage_dir`  (Path des aufgeloesten Stage-Verzeichnisses ODER None bei Legacy),
  - `number`     (Stage-Nummer),
  - `name`       (Postfix-Name, z.B. "integration"),
  - `slice_paths`(Map concern -> Pfad fuer die 8 kanonischen Slices),
  - `resolve_slice(name)` (Einzel-Slice-Zugriff, single unit of work).

Dual-Read-Fallback (W-VAULT-1): existiert KEIN Vault-Slice-Satz fuer eine Stage
(Migration noch nicht gelaufen), faellt der Resolver IN-MEMORY auf den Legacy-Monolith
`.claude/meta/implementation/stage_N.md` zurueck (analog resolve_vault_meta Tier-6) —
downgrade-sicher, kein Schreiben.

read-only: der Resolver mutiert keinen Vault/State.

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_resolve_vault_stage.py     (repo-root)
  py -3 -m pytest test_resolve_vault_stage.py                     (scripts-cwd)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from stage_slice_schema import CANONICAL_SLICES  # die 8 Slices = single source (batch_1)
from resolve_vault_stage import (
    StageHandle,
    resolve_slice,
    resolve_stage,
)


# ---------------------------------------------------------------------------
# Fixtures: ein Vault-Slice-Satz + ein Legacy-Monolith
# ---------------------------------------------------------------------------

_VAULT_SLICE_SET = {
    "_index": {"stufe": 3, "name": "integration"},
    "execute": {"testbefehl": "dotnet test --filter X", "testtyp": "integration"},
    "setup": {"commands": ["startup"], "timeout_min": 5},
    "teardown": {"commands": ["shutdown"], "always_run": True},
    "health_check": {"command": "docker info", "retries": 10},
    "resources": {"infrastruktur": "docker"},
    "concurrency_class": {"concurrency_class": "DEPENDS"},
    "exit_criteria": {"qg": "pass"},
}

# Ein realistischer Legacy-Monolith (Spiegel der IST-stage_3.md-Struktur, gekuerzt).
_LEGACY_MONOLITH_FM = {
    "stufe": 3,
    "name": "Integration",
    "fokus": "Technischer Durchstich",
    "testbefehl": "dotnet test --filter FullyQualifiedName~X",
    "test_projekte": ["VDEK.DCSP.IntegrationTests"],
    "testpfad": "Tests/Integration/",
    "fanout": "niedrig",
    "mocks_erlaubt": "nein",
    "blueprint_perspektive": "Scheinwerfer",
    "testtyp": "integration",
    "infrastruktur": "docker",
    "max_container_parallel": 8,
    "concurrency_class": "DEPENDS",
    "concurrency_depends_on": ["docker_integration_stack"],
    "setup": {"commands": ["docker-compose up -d"], "timeout_min": 5},
    "teardown": {"commands": ["docker-compose down -v"], "always_run": True},
    "health_check": {"command": "Test-NetConnection -Port 5433", "retries": 15},
    "exit_criteria": [{"blueprint_qg": "pass"}],
}


def _write_vault_stage(vault_root: Path, n: int, name: str, slice_set: dict) -> Path:
    """Lege `{vault_root}/Stage/stage_{n}_{name}/` mit {slice}.md-Dateien an."""
    import yaml

    stage_dir = vault_root / "Stage" / f"stage_{n}_{name}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    for slice_name, fm in slice_set.items():
        text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n# " + slice_name + "\n"
        (stage_dir / f"{slice_name}.md").write_text(text, encoding="utf-8")
    return stage_dir


def _write_legacy_monolith(project_root: Path, n: int, fm: dict) -> Path:
    """Lege den Legacy-Monolith `.claude/meta/implementation/stage_{n}.md` an."""
    import yaml

    meta_dir = project_root / ".claude" / "meta" / "implementation"
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = meta_dir / f"stage_{n}.md"
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n# Stage\n"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def env_guard():
    """Sichert/Restored CLAUDE_VAULT_ROOT + cwd (Tests pinnen den Vault via env)."""
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


# ---------------------------------------------------------------------------
# 1. Glob findet das Stage-Verzeichnis per Nummer + slice_paths-Map (8 Concerns)
# ---------------------------------------------------------------------------


def test_resolve_stage_globs_dir_by_number(tmp_path: Path, env_guard) -> None:
    """resolve_stage(3) findet stage_3_<name> per Postfix-Glob + traegt number/name/dir."""
    vault = tmp_path / "vault"
    _write_vault_stage(vault, 3, "integration", _VAULT_SLICE_SET)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    handle = resolve_stage(3)
    assert handle is not None
    assert handle.number == 3
    assert handle.name == "integration"
    assert handle.stage_dir == vault / "Stage" / "stage_3_integration"


def test_slice_paths_map_has_eight_concerns(tmp_path: Path, env_guard) -> None:
    """slice_paths deckt die 8 kanonischen Slices ab (Map concern -> Pfad)."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", _VAULT_SLICE_SET)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    handle = resolve_stage(3)
    assert handle is not None
    assert set(handle.slice_paths.keys()) == set(CANONICAL_SLICES)
    # Jeder Pfad zeigt auf {slice}.md im aufgeloesten Stage-Verzeichnis.
    assert handle.slice_paths["execute"] == stage_dir / "execute.md"


# ---------------------------------------------------------------------------
# 2. Einzel-Slice-Zugriff (single unit of work — TDD-Green ruft resolve_slice)
# ---------------------------------------------------------------------------


def test_resolve_slice_returns_execute_path(tmp_path: Path, env_guard) -> None:
    """resolve_slice(3, 'execute') liefert GENAU den execute.md-Pfad (TDD-Green-Slice)."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", _VAULT_SLICE_SET)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    p = resolve_slice(3, "execute")
    assert p == stage_dir / "execute.md"
    assert p.exists()


def test_handle_resolve_slice_method(tmp_path: Path, env_guard) -> None:
    """StageHandle.resolve_slice('setup') ist der Einzel-Slice-Zugriff auf dem Handle."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", _VAULT_SLICE_SET)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    handle = resolve_stage(3)
    assert handle.resolve_slice("setup") == stage_dir / "setup.md"


def test_resolve_slice_unknown_concern_is_none(tmp_path: Path, env_guard) -> None:
    """Ein Nicht-kanonischer Slice-Name -> None (fail-safe, kein Crash)."""
    vault = tmp_path / "vault"
    _write_vault_stage(vault, 3, "integration", _VAULT_SLICE_SET)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    assert resolve_slice(3, "does_not_exist") is None


# ---------------------------------------------------------------------------
# 3. Dual-Read-Fallback (W-VAULT-1): kein Vault-Slice-Satz -> Legacy-Monolith
# ---------------------------------------------------------------------------


def test_dual_read_falls_back_to_legacy_monolith(tmp_path: Path, env_guard) -> None:
    """Kein Vault-Slice-Verzeichnis -> in-memory StageHandle aus Legacy-Monolith."""
    vault = tmp_path / "empty_vault"  # KEIN Stage/-Verzeichnis
    vault.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "proj_OmniCommand"
    project.mkdir(parents=True, exist_ok=True)
    _write_legacy_monolith(project, 3, _LEGACY_MONOLITH_FM)

    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)
    os.chdir(project)  # Legacy-Walkup ab cwd (analog resolve_vault_meta Tier-6)

    handle = resolve_stage(3)
    assert handle is not None
    # In-Memory-Handle: kein echtes Stage-Verzeichnis (Legacy-Fallback-Signal).
    assert handle.stage_dir is None
    assert handle.number == 3
    # Slice-Views sind in-memory aus dem Monolith abgeleitet (kein None-Pfad noetig).
    assert handle.is_legacy is True


def test_dual_read_legacy_slice_view_carries_monolith_fields(tmp_path: Path, env_guard) -> None:
    """Der Legacy-Fallback liefert die Monolith-Felder als in-memory Slice-Views."""
    vault = tmp_path / "empty_vault"
    vault.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "proj_OmniCommand"
    project.mkdir(parents=True, exist_ok=True)
    _write_legacy_monolith(project, 3, _LEGACY_MONOLITH_FM)

    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)
    os.chdir(project)

    handle = resolve_stage(3)
    assert handle is not None
    # execute-View traegt den testbefehl aus dem Monolith.
    execute_view = handle.slice_view("execute")
    assert execute_view is not None
    assert execute_view.get("testbefehl") == _LEGACY_MONOLITH_FM["testbefehl"]
    # resources-View traegt infrastruktur=docker (Migrations-Quelle der resource-ids).
    resources_view = handle.slice_view("resources")
    assert resources_view.get("infrastruktur") == "docker"


# ---------------------------------------------------------------------------
# 4. Vault gewinnt VOR Legacy (Praezedenz, semantisch korrekt)
# ---------------------------------------------------------------------------


def test_vault_slice_set_wins_over_legacy(tmp_path: Path, env_guard) -> None:
    """Vault-Slice-Satz UND Legacy-Monolith da -> Vault gewinnt (echtes Verzeichnis)."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", _VAULT_SLICE_SET)
    project = tmp_path / "proj_OmniCommand"
    project.mkdir(parents=True, exist_ok=True)
    _write_legacy_monolith(project, 3, _LEGACY_MONOLITH_FM)

    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)
    os.chdir(project)

    handle = resolve_stage(3)
    assert handle is not None
    assert handle.is_legacy is False
    assert handle.stage_dir == stage_dir  # Vault-Verzeichnis, NICHT Legacy
    # Einzel-Slice zeigt auf den Vault-Pfad (nicht in-memory).
    assert handle.resolve_slice("execute") == stage_dir / "execute.md"


# ---------------------------------------------------------------------------
# 5. Fehlende Stage + fehlender Legacy -> sauberer None-Handle (fail-safe)
# ---------------------------------------------------------------------------


def test_missing_stage_and_legacy_returns_none(tmp_path: Path, env_guard) -> None:
    """Keine Vault-Slices UND kein Legacy-Monolith -> None (kein Crash, fail-safe)."""
    vault = tmp_path / "empty_vault"
    vault.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "proj_empty"
    project.mkdir(parents=True, exist_ok=True)

    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)
    os.chdir(project)

    assert resolve_stage(7) is None
    assert resolve_slice(7, "execute") is None


def test_missing_vault_root_dir_no_crash(tmp_path: Path, env_guard) -> None:
    """Vault-Root existiert gar nicht + kein Legacy -> None, kein Crash."""
    project = tmp_path / "proj_empty"
    project.mkdir(parents=True, exist_ok=True)
    os.environ["CLAUDE_VAULT_ROOT"] = str(tmp_path / "nope_does_not_exist")
    os.chdir(project)

    assert resolve_stage(3) is None


# ---------------------------------------------------------------------------
# Ambiguitaet: >1 Match fuer dieselbe Nummer -> Fehler (kein stiller Zufalls-Pick)
# ---------------------------------------------------------------------------


def test_ambiguous_stage_dirs_raise(tmp_path: Path, env_guard) -> None:
    """Zwei stage_3_*-Verzeichnisse -> Ambiguitaets-Fehler (genau-1-Match-Semantik)."""
    vault = tmp_path / "vault"
    _write_vault_stage(vault, 3, "integration", _VAULT_SLICE_SET)
    _write_vault_stage(vault, 3, "andersrum", _VAULT_SLICE_SET)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    with pytest.raises(ValueError):
        resolve_stage(3)


# ---------------------------------------------------------------------------
# read-only + Glob-Faehigkeit (Modul enthaelt echten Verzeichnis-Glob)
# ---------------------------------------------------------------------------


def test_module_has_real_glob() -> None:
    """Das Modul enthaelt einen echten Verzeichnis-Glob/iterdir (AK-GLOB Falsifikation)."""
    import resolve_vault_stage as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert (".glob(" in src) or (".iterdir(" in src), "resolve_vault_stage muss glob-faehig sein"


def test_resolve_does_not_create_anything(tmp_path: Path, env_guard) -> None:
    """read-only: ein resolve_stage-Aufruf legt nichts im Vault an (mutiert nicht)."""
    vault = tmp_path / "empty_vault"
    vault.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "proj_empty"
    project.mkdir(parents=True, exist_ok=True)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)
    os.chdir(project)

    before = set(p.name for p in vault.rglob("*"))
    resolve_stage(3)
    after = set(p.name for p in vault.rglob("*"))
    assert before == after  # nichts geschrieben


# ---------------------------------------------------------------------------
# StageHandle-Form
# ---------------------------------------------------------------------------


def test_stage_handle_shape(tmp_path: Path, env_guard) -> None:
    """StageHandle traegt number/name/stage_dir/slice_paths + resolve_slice/slice_view/is_legacy."""
    vault = tmp_path / "vault"
    _write_vault_stage(vault, 3, "integration", _VAULT_SLICE_SET)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    handle = resolve_stage(3)
    assert isinstance(handle, StageHandle)
    assert isinstance(handle.number, int)
    assert isinstance(handle.name, str)
    assert isinstance(handle.slice_paths, dict)
    assert callable(handle.resolve_slice)
    assert callable(handle.slice_view)
    assert isinstance(handle.is_legacy, bool)
