"""
test_schema_migration_e3.py — BL-486 batch_2 E3-FIX (POST-ROOT-2) — RED

Tests for schema_migration_e3.py — backward-compat Read-Bridge fuer alte
Manifeste OHNE epoch (PT-CMD-023 Graceful Degradation + PT-CMD-007 Idempotenz).

Contract (Blueprint §7 Item 1, Gold E3):
    migrate_read(manifest: dict) -> dict
        - fehlt current_stage.epoch  → setzt epoch = 0 (default, backward-compat)
        - epoch bereits da           → unveraendert (idempotent, PT-CMD-007)
        - bricht NICHT hart bei Legacy-Manifest (Graceful, PT-CMD-023)
    needs_migration(manifest: dict) -> bool

Gold E3 Exit-Kriterien abgedeckt:
    - migrate_read(legacy_manifest)["current_stage"]["epoch"] == 0      (Gold :49)
    - migrate_read(manifest_with_epoch) == manifest_with_epoch          (Gold :50, Idempotenz)

RED: schema_migration_e3.py existiert NICHT (greenfield) → ImportError = korrektes RED.
Run: py -3 -m pytest .claude/scripts/test_schema_migration_e3.py -q
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path so local imports work.
sys.path.insert(0, str(Path(__file__).parent))

# TARGET MODULE — does NOT exist yet (greenfield). Import FAILS → RED.
from schema_migration_e3 import (  # noqa: E402
    migrate_read,
    needs_migration,
)


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def legacy_manifest():
    """Altes Manifest OHNE epoch (vor E3 erstellt) — backward-compat Ziel."""
    return {
        "current_stage": {"stage": 3},
        "batch_stages_original": {"batch_1": [1, 3, 5]},
    }


@pytest.fixture
def manifest_with_epoch():
    """Manifest das bereits ein epoch traegt (schon migriert / neu)."""
    return {
        "current_stage": {"stage": 3, "epoch": 7},
        "batch_stages_original": {"batch_1": [1, 3, 5]},
    }


# ─── Tests (Gold E3) ──────────────────────────────────────────────────────────

def test_migrate_read_bridges_missing_epoch_to_default_zero(legacy_manifest):
    """Gold E3 :49 — altes Manifest OHNE epoch → migrate_read setzt default-epoch=0 (backward-compat)."""
    migrated = migrate_read(legacy_manifest)
    assert migrated["current_stage"]["epoch"] == 0


def test_migrate_read_preserves_existing_stage(legacy_manifest):
    """migrate_read laesst bestehende current_stage-Felder unangetastet (nur epoch ergaenzt)."""
    migrated = migrate_read(legacy_manifest)
    assert migrated["current_stage"]["stage"] == 3


def test_migrate_read_does_not_break_on_legacy(legacy_manifest):
    """Blueprint :213 — Legacy-Manifest → migrate_read bricht NICHT hart (Graceful, PT-CMD-023)."""
    migrated = migrate_read(legacy_manifest)
    assert "batch_stages_original" in migrated


def test_migrate_read_idempotent_when_epoch_present(manifest_with_epoch):
    """Gold E3 :50 — Manifest MIT epoch → migrate_read unveraendert (Idempotenz, PT-CMD-007)."""
    migrated = migrate_read(manifest_with_epoch)
    assert migrated == manifest_with_epoch


def test_migrate_read_idempotent_double_application(legacy_manifest):
    """PT-CMD-007 — 2x migrate_read == 1x migrate_read (run-once-stabil)."""
    once = migrate_read(legacy_manifest)
    twice = migrate_read(migrate_read(legacy_manifest))
    assert twice == once


def test_needs_migration_true_for_legacy(legacy_manifest):
    """Blueprint :207 — needs_migration() erkennt fehlendes epoch."""
    assert needs_migration(legacy_manifest) is True


def test_needs_migration_false_when_epoch_present(manifest_with_epoch):
    """needs_migration() ist False wenn epoch bereits vorhanden (kein Re-Run noetig)."""
    assert needs_migration(manifest_with_epoch) is False
