"""
manifest_schema.py — BL-486 batch_2 E3-FIX (POST-ROOT-2)

Typisiertes Manifest-Schema mit `current_stage.epoch` + `batch_stages_original`
als Pflichtfelder. `epoch` ist die Optimistic-Lock-Basis fuer E4 (atomarer
Elevation-Flush). Loest POST-ROOT-2 strukturell: kein stiller Stage-Fallback,
kein Stage-Skip — fehlt ein Pflichtfeld, wird Fail-Loud (PT-CMD-011) geworfen.

Gehoert NICHT zu `validate_manifest_schema.py` (regex/markdown-Validator) —
dies ist das typisierte dict-Schema, NEU daneben (Gold E3 Nicht-Ziel :105).

Patterns:
    PT-CMD-011 (Fail-Loud): validate() raised ValidationError statt still zu skippen.
    PT-CMD-023 (Graceful Degradation): epoch hat default=0 fuer backward-compat
        Read-Bridge (in schema_migration_e3.migrate_read genutzt).

Contract (Blueprint BL-486_batch2 §7 Item 1, Gold E3):
    MANIFEST_SCHEMA              — Schema-dict (current_stage.epoch + batch_stages_original required)
    class ValidationError        — Fail-Loud bei fehlendem Pflichtfeld
    validate(manifest) -> None   — raised ValidationError bei fehlendem bso ODER epoch
    current_stage_epoch(manifest) -> int   — Accessor
    bump_epoch(manifest) -> dict — epoch += 1 (von E4 genutzt; monoton steigend)

Usage:
    from manifest_schema import validate, current_stage_epoch, bump_epoch, ValidationError
    validate(manifest)                       # raises ValidationError oder return None
    e = current_stage_epoch(manifest)        # -> int
    manifest = bump_epoch(manifest)          # -> dict mit epoch+1
"""

from __future__ import annotations

import copy

# ─── Schema-Definition (Blueprint :183-194) ──────────────────────────────────
# Optimistic-Lock-Basis (epoch) fuer E4 (atomarer Elevation-Flush).
# batch_stages_original required=True => kein stiller Fallback / kein Stage-Skip.
MANIFEST_SCHEMA = {
    "current_stage": {
        "required": True,
        "fields": {
            "stage": {"type": int, "required": True},
            "epoch": {
                "type": int,
                "required": True,
                "default": 0,
                "doc": "monoton steigend (Inkrement ODER unix-ts); "
                       "Optimistic-Lock-Basis fuer E4",
            },
        },
    },
    "batch_stages_original": {
        "type": dict,
        "required": True,
        "doc": "kein stiller Fallback / kein Stage-Skip",
    },
}


class ValidationError(Exception):
    """Fail-Loud (PT-CMD-011): ein Pflichtfeld des Manifest-Schemas fehlt."""


def validate(manifest: dict) -> None:
    """Validiert ein Manifest gegen MANIFEST_SCHEMA.

    Raised ValidationError (Fail-Loud, PT-CMD-011) wenn:
      - `batch_stages_original` fehlt (kein stiller Fallback), ODER
      - `current_stage` fehlt, ODER
      - `current_stage.epoch` fehlt (nach Migration zwingend, Blueprint :199-200).

    Return None wenn das Manifest gueltig ist.
    """
    if "batch_stages_original" not in manifest:
        raise ValidationError(
            "batch_stages_original fehlt — kein stiller Fallback erlaubt (POST-ROOT-2)."
        )

    current_stage = manifest.get("current_stage")
    if current_stage is None:
        raise ValidationError("current_stage fehlt im Manifest.")

    if "epoch" not in current_stage:
        raise ValidationError(
            "current_stage.epoch fehlt — Optimistic-Lock-Basis fuer E4 zwingend "
            "(via schema_migration_e3.migrate_read auf default=0 bridgen)."
        )

    return None


def current_stage_epoch(manifest: dict) -> int:
    """Accessor (Blueprint :202): liest current_stage.epoch."""
    return manifest["current_stage"]["epoch"]


def bump_epoch(manifest: dict) -> dict:
    """Inkrementiert current_stage.epoch monoton (Blueprint :203; von E4 genutzt).

    Gibt eine Kopie zurueck (kein Mutieren des Inputs) — fuer mehrfaches Bumpen
    ueber persistierte Decisions hinweg sicher.
    """
    bumped = copy.deepcopy(manifest)
    bumped["current_stage"]["epoch"] = current_stage_epoch(manifest) + 1
    return bumped
