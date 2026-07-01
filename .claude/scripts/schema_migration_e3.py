"""
schema_migration_e3.py — BL-486 batch_2 E3-FIX (POST-ROOT-2)

Backward-compat Read-Bridge fuer alte Manifeste OHNE `current_stage.epoch`.
Alte Manifeste (vor E3 erstellt) tragen kein epoch-Feld — `migrate_read`
ergaenzt es mit dem Schema-default (0), ohne hart zu brechen. So liest E4
(Optimistic-Lock) auch Legacy-State, ohne dass ein Hard-Migration-Schritt
noetig ist.

Patterns:
    PT-CMD-023 (Graceful Degradation): Manifest ohne epoch -> default-0 statt
        Hard-Break. Legacy-Felder (stage, batch_stages_original) bleiben erhalten.
    PT-CMD-007 (Idempotenz): epoch bereits da -> unveraendert; 2x migrate_read
        == 1x migrate_read (run-once-stabil).

Contract (Blueprint BL-486_batch2 §7 Item 1, Gold E3):
    migrate_read(manifest: dict) -> dict
        - fehlt current_stage.epoch -> setzt epoch = 0 (default, backward-compat)
        - epoch bereits da          -> unveraendert (idempotent, PT-CMD-007)
        - bricht NICHT hart bei Legacy-Manifest (Graceful, PT-CMD-023)
    needs_migration(manifest: dict) -> bool

Usage:
    from schema_migration_e3 import migrate_read, needs_migration
    if needs_migration(manifest):
        manifest = migrate_read(manifest)   # epoch=0 ergaenzt, Rest unangetastet
"""

from __future__ import annotations

import copy

from manifest_schema import MANIFEST_SCHEMA

# Schema-default fuer epoch (single source: MANIFEST_SCHEMA, kein Magic-Number).
_EPOCH_DEFAULT = MANIFEST_SCHEMA["current_stage"]["fields"]["epoch"]["default"]


def needs_migration(manifest: dict) -> bool:
    """True gdw. das Manifest noch kein current_stage.epoch traegt (Blueprint :207).

    Graceful: ein Manifest ohne current_stage gilt als migrationsbeduerftig
    (migrate_read laesst es dann unangetastet — kein Hard-Break).
    """
    current_stage = manifest.get("current_stage")
    if not isinstance(current_stage, dict):
        return True
    return "epoch" not in current_stage


def migrate_read(manifest: dict) -> dict:
    """Backward-compat Read-Bridge (Blueprint :205-206, Gold E3 :49/:50).

    Fehlt current_stage.epoch -> ergaenzt epoch = 0 (default). Idempotent
    (PT-CMD-007): epoch bereits da -> Manifest unveraendert zurueck. Bricht
    NICHT hart bei Legacy-Form ohne current_stage (PT-CMD-023, Graceful):
    in dem Fall wird das Manifest unveraendert durchgereicht.

    Gibt eine Kopie zurueck (kein Mutieren des Inputs).
    """
    if not needs_migration(manifest):
        # PT-CMD-007: epoch bereits da -> idempotent, unveraendert.
        return manifest

    migrated = copy.deepcopy(manifest)
    current_stage = migrated.get("current_stage")
    if not isinstance(current_stage, dict):
        # PT-CMD-023: Legacy ohne current_stage -> kein Hard-Break, nichts zu bridgen.
        return migrated

    current_stage["epoch"] = _EPOCH_DEFAULT
    return migrated
