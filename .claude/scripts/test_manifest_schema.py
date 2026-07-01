"""
test_manifest_schema.py — BL-486 batch_2 E3-FIX (POST-ROOT-2) — RED

Tests for manifest_schema.py — typisiertes Manifest-Schema mit epoch +
batch_stages_original required (Optimistic-Lock-Basis fuer E4).

Contract (Blueprint §7 Item 1, Gold E3):
    MANIFEST_SCHEMA = {
        "current_stage": {"required": True,
            "fields": {"stage": {"type": int, "required": True},
                       "epoch": {"type": int, "required": True, "default": 0}}},
        "batch_stages_original": {"type": dict, "required": True},
    }
    validate(manifest: dict) -> None          # raises ValidationError bei fehlendem
                                              # batch_stages_original ODER current_stage.epoch
    class ValidationError(Exception): ...
    current_stage_epoch(manifest: dict) -> int
    bump_epoch(manifest: dict) -> dict        # epoch += 1 (von E4 genutzt)

Gold E3 Exit-Kriterien abgedeckt:
    - "epoch" in MANIFEST_SCHEMA["current_stage"]                       (Gold :46)
    - batch_stages_original required is True                            (Gold :47)
    - validate(manifest_ohne_bso) raises ValidationError               (Gold :48)
    - bump_epoch inkrementiert epoch                                    (Blueprint :203)

RED: manifest_schema.py existiert NICHT → ImportError = korrektes RED.
Run: py -3 -m pytest .claude/scripts/test_manifest_schema.py -q
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path so local imports work.
sys.path.insert(0, str(Path(__file__).parent))

# TARGET MODULE — does NOT exist yet (greenfield). Import FAILS → RED.
from manifest_schema import (  # noqa: E402
    MANIFEST_SCHEMA,
    ValidationError,
    validate,
    current_stage_epoch,
    bump_epoch,
)


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def valid_manifest():
    """Gueltiges, vollstaendig typisiertes Manifest-dict."""
    return {
        "current_stage": {"stage": 1, "epoch": 0},
        "batch_stages_original": {"batch_1": [1, 3, 5]},
    }


@pytest.fixture
def manifest_ohne_bso():
    """Manifest OHNE batch_stages_original (kein stiller Fallback erlaubt)."""
    return {
        "current_stage": {"stage": 1, "epoch": 0},
    }


@pytest.fixture
def manifest_ohne_epoch():
    """Manifest dessen current_stage KEIN epoch traegt (Legacy-Form)."""
    return {
        "current_stage": {"stage": 1},
        "batch_stages_original": {"batch_1": [1, 3, 5]},
    }


# ─── Tests (Gold E3) ──────────────────────────────────────────────────────────

def test_schema_current_stage_has_epoch_field():
    """Gold E3 :46 — 'epoch' ist Feld im current_stage-Schema."""
    assert "epoch" in MANIFEST_SCHEMA["current_stage"]["fields"]
    assert MANIFEST_SCHEMA["current_stage"]["fields"]["epoch"]["type"] is int
    assert MANIFEST_SCHEMA["current_stage"]["fields"]["epoch"]["required"] is True


def test_schema_batch_stages_original_required():
    """Gold E3 :47 — batch_stages_original ist required=True (kein stiller Fallback)."""
    assert MANIFEST_SCHEMA["batch_stages_original"]["required"] is True


def test_validate_raises_when_batch_stages_original_missing(manifest_ohne_bso):
    """Gold E3 :48 — Manifest ohne batch_stages_original → ValidationError (Fail-Loud, PT-CMD-011)."""
    with pytest.raises(ValidationError):
        validate(manifest_ohne_bso)


def test_validate_raises_when_epoch_missing(manifest_ohne_epoch):
    """Blueprint :199-200 — Manifest ohne current_stage.epoch (nach Migration) → ValidationError."""
    with pytest.raises(ValidationError):
        validate(manifest_ohne_epoch)


def test_validate_accepts_valid_manifest(valid_manifest):
    """validate() akzeptiert ein gueltiges Manifest (raises NICHT, return None)."""
    assert validate(valid_manifest) is None


def test_current_stage_epoch_accessor(valid_manifest):
    """Blueprint :202 — current_stage_epoch() liest den epoch-Wert."""
    assert current_stage_epoch(valid_manifest) == 0


def test_bump_epoch_increments(valid_manifest):
    """Blueprint :203 — bump_epoch() inkrementiert epoch monoton (von E4 genutzt)."""
    bumped = bump_epoch(valid_manifest)
    assert current_stage_epoch(bumped) == 1


def test_bump_epoch_twice_increments_by_two(valid_manifest):
    """bump_epoch() ist monoton steigend ueber mehrere Aufrufe."""
    once = bump_epoch(valid_manifest)
    twice = bump_epoch(once)
    assert current_stage_epoch(twice) == 2
