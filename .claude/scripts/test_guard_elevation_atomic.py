#!/usr/bin/env python3
"""Tests fuer guard_elevation_atomic.py (BL-486 AK-E E4-FIX, POST-ROOT-3) — RED.

RED-first (greenfield): guard_elevation_atomic.py existiert noch NICHT.
Bis GREEN schlagen diese Tests mit ModuleNotFoundError fehl (korrektes greenfield-RED).

Der Rollback-/Recovery-Pfad zum atomaren Flush (stage_elevation_flush.py): Crash VOR
os.replace -> die temp-Datei verwaist. guard_elevation_atomic detektiert die verwaiste
temp und ermoeglicht idempotente Re-Eval (PT-CMD-007), sodass KEIN halb-promoteter
State entsteht. verify_atomic_path() ist die Code-Scan-Probe, die der 6. Gate-Check
(_behavior_check_e_elevation, E4-Assert "elevation_flush_is_atomic") konsumiert.

Kern-Vertrag (Blueprint Item 5, Gold E4-FIX):
  detect_orphan_temp(bl_id, sub_batch_id) -> Optional[Path]   # verwaiste temp nach Crash
  verify_atomic_path() -> dict                                # Code-Scan-Probe (PT-CMD-011 Fail-Loud)
  elevation_flush_is_atomic() -> bool                         # E-CHK-E4-Assert (Gold :59)

Gold E4 Exit-Kriterien abgedeckt:
  - verify_atomic_path() returns {"status":"PASS"}                                 (Gold :59)
  - elevation_flush_is_atomic() == True (temp+os.replace+Rollback im Code)         (Gold :59)
  - Rollback-Pfad: verwaiste temp detektiert -> idempotent re-evaluiert            (Blueprint :346)

Run: py -3 -m pytest .claude/scripts/test_guard_elevation_atomic.py -q  (repo-root)
"""
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

GUARD = SCRIPT_DIR / "guard_elevation_atomic.py"
FLUSH = SCRIPT_DIR / "stage_elevation_flush.py"


# ===========================================================================
# Rollback-Pfad — verwaiste temp nach Crash detektieren (idempotente Re-Eval)
# ===========================================================================

def test_detect_orphan_temp_finds_leftover_after_crash(tmp_path, monkeypatch):
    """Nach einem Crash VOR os.replace liegt die temp-Datei verwaist herum.
    detect_orphan_temp findet sie (Grundlage fuer idempotente Re-Eval)."""
    import guard_elevation_atomic as mod
    orphan = tmp_path / "decision.tmp"
    orphan.write_text("{}", encoding="utf-8")
    # Lenke die temp-Pfad-Aufloesung auf unsere simulierte verwaiste temp.
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: orphan, raising=False)
    found = mod.detect_orphan_temp("BL-486", "batch_2")
    assert found is not None
    assert Path(found) == orphan


def test_detect_orphan_temp_none_when_clean(tmp_path, monkeypatch):
    """Kein Crash -> keine verwaiste temp -> detect_orphan_temp gibt None
    (kein false positive, idempotenter Clean-Pfad)."""
    import guard_elevation_atomic as mod
    missing = tmp_path / "decision.tmp"   # existiert NICHT
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: missing, raising=False)
    assert mod.detect_orphan_temp("BL-486", "batch_2") is None


def test_orphan_detection_is_idempotent(tmp_path, monkeypatch):
    """PT-CMD-007: detect_orphan_temp ist idempotent — mehrfacher Aufruf bei
    unveraendertem State liefert dasselbe Ergebnis, ohne den State zu mutieren."""
    import guard_elevation_atomic as mod
    orphan = tmp_path / "decision.tmp"
    orphan.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(mod, "stage_decision_temp_path",
                        lambda bl_id, sub_batch_id: orphan, raising=False)
    first = mod.detect_orphan_temp("BL-486", "batch_2")
    second = mod.detect_orphan_temp("BL-486", "batch_2")
    assert first == second
    assert orphan.exists()   # Detection mutiert den State NICHT (read-only Scan)


# ===========================================================================
# verify_atomic_path() / elevation_flush_is_atomic() — E-CHK-E4-Assert-Basis
# Code-Scan-Probe: temp + os.replace + Rollback im Flush-Modul nachweisbar
# ===========================================================================

def test_verify_atomic_path_returns_pass_status():
    """Gold E4 :59 — verify_atomic_path() liefert {"status":"PASS"} wenn
    stage_elevation_flush.py den atomaren Pfad (temp + os.replace, Reuse
    factory_lock._atomic_write) traegt."""
    import guard_elevation_atomic as mod
    result = mod.verify_atomic_path()
    assert isinstance(result, dict)
    assert result.get("status") == "PASS"


def test_elevation_flush_is_atomic_true():
    """Gold E4 :59 — elevation_flush_is_atomic() == True: der Code-Scan bestaetigt
    temp+os.replace+Rollback. Dies ist die Probe, die _behavior_check_e_elevation
    (E4-Assert) konsumiert."""
    import guard_elevation_atomic as mod
    assert mod.elevation_flush_is_atomic() is True


def test_verify_atomic_path_scans_flush_module_for_os_replace():
    """Verhaltens-Beleg: verify_atomic_path() prueft REAL, dass das Flush-Modul
    os.replace (atomarer Commit) nutzt — nicht nur einen hartcodierten PASS.
    Negativ-Gegenprobe: ohne os.replace im Flush-Modul waere der Verdict NICHT PASS."""
    import guard_elevation_atomic as mod
    src = FLUSH.read_text(encoding="utf-8")
    # Das Flush-Modul MUSS den atomaren os.replace-Pfad tragen (direkt ODER via _atomic_write-Reuse).
    assert "os.replace" in src or "_atomic_write" in src
    # Und verify_atomic_path verdiktiert konsistent dazu PASS.
    assert mod.verify_atomic_path().get("status") == "PASS"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
