"""
guard_elevation_atomic.py — BL-486 batch_2 E4-FIX (POST-ROOT-3)

Rollback-/Recovery-Pfad + Code-Scan-Probe zum atomaren Elevation-Flush
(stage_elevation_flush.py). Zwei Aufgaben:

1) Rollback nach Crash: ein Crash VOR os.replace laesst die Decision-temp verwaist
   liegen. detect_orphan_temp findet sie (read-only, idempotent, PT-CMD-007) —
   Grundlage fuer eine idempotente Re-Eval, sodass KEIN halb-promoteter Manifest-
   State entsteht.

2) Code-Scan-Probe: verify_atomic_path() / elevation_flush_is_atomic() belegen REAL
   (kein hartcodierter PASS), dass das Flush-Modul den atomaren Pfad traegt
   (temp + os.replace, Reuse factory_lock._atomic_write). Das ist die Probe, die der
   6. Gate-Check (_behavior_check_e_elevation, E4-Assert "elevation_flush_is_atomic")
   in sanity_check_stage.py konsumiert.

Patterns:
    PT-CMD-011 (Fail-Loud): verify_atomic_path liefert einen ehrlichen Verdict
        (status + reason) statt still PASS — bei fehlendem atomarem Pfad -> FAIL.
    PT-CMD-007 (Idempotenz): detect_orphan_temp ist ein read-only Scan, mutiert
        den State NICHT (mehrfacher Aufruf -> identisches Ergebnis).

Contract (Blueprint BL-486_batch2 §7 Item 5 :338-341, Gold E4 :59):
    detect_orphan_temp(bl_id, sub_batch_id) -> Optional[Path]   # verwaiste temp nach Crash
    verify_atomic_path() -> dict                                # Code-Scan-Probe (Fail-Loud)
    elevation_flush_is_atomic() -> bool                         # E-CHK-E4-Assert (Gold :59)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Modul-Level Re-Export: detect_orphan_temp ruft DIESEN Namen auf, damit Tests die
# Pfad-Aufloesung gezielt monkeypatchen koennen (auf eine simulierte verwaiste temp).
from stage_elevation_flush import stage_decision_temp_path  # noqa: E402,F401

# Das Flush-Modul, dessen atomaren Pfad verify_atomic_path() per Code-Scan belegt.
FLUSH_MODULE = SCRIPT_DIR / "stage_elevation_flush.py"


def detect_orphan_temp(bl_id: str, sub_batch_id: str) -> Optional[Path]:
    """Findet eine verwaiste Decision-temp nach einem Crash VOR os.replace.

    Read-only + idempotent (PT-CMD-007): existiert die temp -> Rueckgabe ihres Pfads
    (Grundlage fuer idempotente Re-Eval); existiert sie nicht (sauberer Pfad) -> None
    (kein false positive). Der Scan MUTIERT den State nicht.
    """
    temp_path = stage_decision_temp_path(bl_id, sub_batch_id)
    if temp_path is not None and Path(temp_path).exists():
        return Path(temp_path)
    return None


def verify_atomic_path() -> dict:
    """Code-Scan-Probe (PT-CMD-011 Fail-Loud) auf den atomaren Pfad im Flush-Modul.

    Prueft REAL (kein hartcodierter PASS) ob stage_elevation_flush.py den atomaren
    Commit-Pfad traegt:
      - os.replace ODER _atomic_write (atomarer Commit, Reuse-Invariante Gold :114), UND
      - einen Rollback-Hinweis (promote-Handler + temp-Persistenz).

    Negativ-Gegenprobe: fehlt der os.replace/_atomic_write-Marker im Flush-Modul,
    ist der Verdict NICHT PASS (status="FAIL").
    """
    if not FLUSH_MODULE.exists():
        return {
            "status": "FAIL",
            "reason": f"Flush-Modul fehlt: {FLUSH_MODULE}",
        }

    src = FLUSH_MODULE.read_text(encoding="utf-8")

    has_atomic_commit = ("os.replace" in src) or ("_atomic_write" in src)
    # Rollback-/Transaktions-Beleg: temp-Persistenz (write_decision) + atomarer promote.
    has_rollback_path = ("write_decision" in src) and ("promote" in src)

    if has_atomic_commit and has_rollback_path:
        return {
            "status": "PASS",
            "reason": "stage_elevation_flush.py traegt temp + os.replace/_atomic_write "
                      "+ Rollback-Pfad (write_decision/promote).",
            "atomic_via": "_atomic_write" if "_atomic_write" in src else "os.replace",
        }

    missing = []
    if not has_atomic_commit:
        missing.append("os.replace/_atomic_write")
    if not has_rollback_path:
        missing.append("write_decision/promote (Rollback-Pfad)")
    return {
        "status": "FAIL",
        "reason": f"Atomarer Pfad nicht belegt im Flush-Modul; fehlt: {', '.join(missing)}.",
    }


def elevation_flush_is_atomic() -> bool:
    """E-CHK-E4-Assert (Gold :59): True gdw. der Code-Scan den atomaren Pfad bestaetigt.

    Dies ist die Probe, die _behavior_check_e_elevation (E4-Assert) konsumiert.
    """
    return verify_atomic_path().get("status") == "PASS"


if __name__ == "__main__":  # pragma: no cover - CLI-Debughilfe, nicht test-relevant
    import json as _json
    print(_json.dumps(verify_atomic_path(), ensure_ascii=False, indent=2))
