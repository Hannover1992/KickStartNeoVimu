#!/usr/bin/env python3
"""Tests fuer stage_elevation_flush.py (BL-486 AK-E E4-FIX, POST-ROOT-3) — RED.

RED-first (greenfield): stage_elevation_flush.py existiert noch NICHT.
Bis GREEN schlagen diese Tests mit ModuleNotFoundError fehl (korrektes greenfield-RED).

Schliesst POST-ROOT-3 (nicht-atomare Elevation): die Berater-Entscheidung
(elev.next_action / elev.next_stage, dispatch_implement.js:852-861) wird NICHT
direkt ins Manifest geschrieben, sondern in eine temp-Datei; der Post-SDF-Handler
promotet sie via os.replace ATOMAR (Reuse factory_lock._atomic_write:154-167).
Crash vor os.replace -> temp verwaist, Manifest UNVERAENDERT -> idempotente Re-Eval.

Kern-Vertrag (Blueprint Item 5, Gold E4-FIX):
  stage_decision_temp_path(bl_id, sub_batch_id) -> Path
  write_decision(decision: dict, *, bl_id, sub_batch_id) -> Path   # Pre-Flight (PT-CMD-018)
  promote(temp_path: Path, manifest_path: Path) -> None            # Reuse _atomic_write (temp->os.replace)
  epoch_guard(manifest, decision) -> bool                          # Optimistic-Lock gegen E3-epoch

Gold E4 Exit-Kriterien abgedeckt:
  - Crash zwischen write_decision + promote -> Manifest unmodifiziert (kein Halb-State)  (Gold :58)
  - elevation_flush_is_atomic() == True (temp+os.replace+Reuse _atomic_write)            (Gold :59)
  - Normalpfad: Entscheidung -> temp -> os.replace -> Manifest promoted                  (Blueprint :347)
  - epoch_guard: Optimistic-Lock gegen E3-epoch (stale -> Re-Eval)                        (Blueprint :337)

REUSE-Invariante (Gold E4 Nicht-Ziel :114): KEIN Primitiv-Neubau — promote() ruft das
bestehende factory_lock._atomic_write AUF (temp+os.replace+partial-write-cleanup).

Run: py -3 -m pytest .claude/scripts/test_stage_elevation_flush.py -q  (repo-root)
"""
import json
import os
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
# Add scripts dir to path so local imports (manifest_schema etc.) work.
sys.path.insert(0, str(SCRIPT_DIR))

FLUSH = SCRIPT_DIR / "stage_elevation_flush.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def decision():
    """Eine Stage-Elevation-Entscheidung (Spiegel von elev.next_action/next_stage,
    dispatch_implement.js:852-861) — das, was E4 in temp persistiert."""
    return {
        "next_action": "ELEVATE",
        "from_stage": 1,
        "next_stage": 3,
        "sub_batch_id": "batch_2",
        "epoch": 0,           # epoch zum Entscheidungs-Zeitpunkt (Optimistic-Lock-Basis, E3)
    }


@pytest.fixture
def manifest():
    """Gueltiges typisiertes Manifest (E3-Schema: current_stage.epoch + bso)."""
    return {
        "current_stage": {"stage": 1, "epoch": 0},
        "batch_stages_original": {"batch_2": [1, 3, 5, 6, 7]},
    }


@pytest.fixture
def manifest_path(tmp_path, manifest):
    """Persistiertes Manifest als Datei (das os.replace-Ziel beim promote)."""
    p = tmp_path / "_manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


# ===========================================================================
# ASSERTION (elevation_flush_is_atomic) — Normalpfad: temp -> os.replace -> promoted
# ===========================================================================

def test_temp_path_is_distinct_from_manifest(tmp_path):
    """write_decision schreibt eine TEMP-Datei (NICHT direkt ins Manifest):
    der temp-Pfad ist verschieden vom Manifest-Pfad (Decision-Execution-Split)."""
    import stage_elevation_flush as mod
    temp = mod.stage_decision_temp_path("BL-486", "batch_2")
    assert temp != (tmp_path / "_manifest.json")
    assert ".tmp" in str(temp) or "temp" in str(temp).lower() or "decision" in str(temp).lower()


def test_write_decision_creates_temp_only(decision, manifest_path, tmp_path, monkeypatch):
    """write_decision legt NUR die temp-Datei an; das Manifest bleibt unangetastet
    (die Entscheidung ist noch NICHT promoted)."""
    import stage_elevation_flush as mod
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: tmp_path / "decision.tmp")
    before = manifest_path.read_text(encoding="utf-8")
    temp = mod.write_decision(decision, bl_id="BL-486", sub_batch_id="batch_2")
    assert Path(temp).exists()                                  # temp da
    assert manifest_path.read_text(encoding="utf-8") == before  # Manifest UNVERAENDERT


def test_promote_makes_state_fully_promoted(decision, manifest_path, tmp_path, monkeypatch):
    """ASSERTION elevation_flush_is_atomic: nach erfolgreichem promote ist der State
    VOLLSTAENDIG promoted (Manifest traegt jetzt die Entscheidung) — kein partial."""
    import stage_elevation_flush as mod
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: tmp_path / "decision.tmp")
    temp = mod.write_decision(decision, bl_id="BL-486", sub_batch_id="batch_2")
    mod.promote(Path(temp), manifest_path)
    promoted = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Vollstaendig promoted: das Ziel-Manifest spiegelt die Entscheidung (next_stage=3)
    assert promoted["next_stage"] == 3 or promoted.get("current_stage", {}).get("stage") == 3
    # temp ist nach os.replace KEINE eigenstaendige Datei mehr (verbraucht/umbenannt)
    assert not Path(temp).exists()


def test_promote_reuses_atomic_write_via_os_replace(decision, manifest_path, tmp_path, monkeypatch):
    """REUSE-Invariante (Gold E4 :114): promote nutzt einen os.replace-basierten
    atomaren Write (factory_lock._atomic_write) — NICHT direktes open(manifest,'w').
    Beweis: os.replace wird waehrend promote() AUFGERUFEN."""
    import stage_elevation_flush as mod
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: tmp_path / "decision.tmp")
    temp = mod.write_decision(decision, bl_id="BL-486", sub_batch_id="batch_2")

    calls = {"n": 0}
    real_replace = os.replace

    def _spy_replace(src, dst):
        calls["n"] += 1
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _spy_replace)
    mod.promote(Path(temp), manifest_path)
    assert calls["n"] >= 1, "promote muss os.replace (atomarer Commit) verwenden, kein direktes open-write"


# ===========================================================================
# ASSERTION (Crash-Rollback) — LOAD-BEARING (W18 POST-ROOT-3)
# Crash zwischen write_decision + promote -> KEIN Halb-State; Re-Run idempotent
# ===========================================================================

def test_crash_before_os_replace_leaves_manifest_unchanged(decision, manifest_path, tmp_path, monkeypatch):
    """LOAD-BEARING (Gold E4 :58): Crash-Simulation — os.replace raised MITTEN im
    promote (zwischen temp-write und atomarem Commit) -> das Manifest bleibt
    UNVERAENDERT (kein halb-geschriebener Ziel-State, kein korrupter Halb-State)."""
    import stage_elevation_flush as mod
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: tmp_path / "decision.tmp")
    temp = mod.write_decision(decision, bl_id="BL-486", sub_batch_id="batch_2")
    before = manifest_path.read_text(encoding="utf-8")

    def _boom(src, dst):
        raise OSError("simulated crash between temp-write and os.replace")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(Exception):
        mod.promote(Path(temp), manifest_path)

    # Kein Halb-State: das Manifest ist Byte-fuer-Byte unveraendert.
    assert manifest_path.read_text(encoding="utf-8") == before
    # Und es ist weiterhin valides JSON (nicht korrupt halb-geschrieben).
    json.loads(manifest_path.read_text(encoding="utf-8"))


def test_crash_then_reeval_is_idempotent(decision, manifest_path, tmp_path, monkeypatch):
    """LOAD-BEARING (Gold E4 :58, PT-CMD-007): nach einem Crash vor os.replace fuehrt
    ein erneuter (jetzt erfolgreicher) promote-Lauf zum KONSISTENTEN Ziel-State —
    die Entscheidung wird idempotent re-evaluiert, kein doppelter/partieller Effekt."""
    import stage_elevation_flush as mod
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: tmp_path / "decision.tmp")

    # 1) Erster Versuch crasht in os.replace.
    temp1 = mod.write_decision(decision, bl_id="BL-486", sub_batch_id="batch_2")

    def _boom(src, dst):
        raise OSError("simulated crash")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(Exception):
        mod.promote(Path(temp1), manifest_path)

    # 2) Re-Eval: os.replace wieder funktionsfaehig, Entscheidung erneut flushen+promoten.
    monkeypatch.undo()
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: tmp_path / "decision.tmp")
    temp2 = mod.write_decision(decision, bl_id="BL-486", sub_batch_id="batch_2")
    mod.promote(Path(temp2), manifest_path)

    promoted = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Genau EIN konsistenter Ziel-State (idempotent: Re-Run == Single-Run-Effekt).
    assert promoted["next_stage"] == 3 or promoted.get("current_stage", {}).get("stage") == 3


# ===========================================================================
# epoch_guard — Optimistic-Lock gegen E3-epoch (stale -> Re-Eval)
# ===========================================================================

def test_epoch_guard_passes_when_epoch_unchanged(manifest, decision):
    """epoch_guard True gdw. der epoch im Manifest UNVERAENDERT ist seit der
    Entscheidung (decision.epoch == manifest.current_stage.epoch) -> promote erlaubt."""
    import stage_elevation_flush as mod
    assert mod.epoch_guard(manifest, decision) is True


def test_epoch_guard_blocks_on_stale_epoch(manifest, decision):
    """epoch_guard False wenn der Manifest-epoch sich seit der Entscheidung erhoeht
    hat (konkurrierender Flush) -> Optimistic-Lock-Konflikt, promote MUSS abbrechen
    und re-evaluieren (kein blinder Overwrite eines neueren States)."""
    import stage_elevation_flush as mod
    # Manifest wurde zwischenzeitlich von einem anderen Flush gebumpt (epoch 0 -> 1).
    manifest["current_stage"]["epoch"] = 1
    assert mod.epoch_guard(manifest, decision) is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
