"""
stage_elevation_flush.py — BL-486 batch_2 E4-FIX (POST-ROOT-3)

Atomare Transaktions-Grenze um den Stage-Elevation Decision-Execution-Split
(dispatch_implement.js:852-877). Die Berater-Entscheidung (elev.next_action /
elev.next_stage) wird NICHT direkt ins Manifest geschrieben, sondern erst in eine
**temp-Datei** persistiert (write_decision); der Post-SDF-Handler promotet sie
ATOMAR via os.replace (promote -> Reuse factory_lock._atomic_write:154-167).

Crash vor os.replace -> temp verwaist, Manifest Byte-fuer-Byte unveraendert ->
idempotente Re-Evaluierung (guard_elevation_atomic.detect_orphan_temp). Damit
entsteht KEIN halb-promoteter Manifest-State (POST-ROOT-3 strukturell geschlossen).

REUSE-Invariante (Gold E4 Nicht-Ziel :114): KEIN os.replace-Primitiv-Neubau —
promote() ruft factory_lock._atomic_write AUF (temp + os.replace + partial-write-
cleanup). E4 ist der Elevation-spezifische Handler + Optimistic-Lock DARUM, nicht
das Primitiv selbst.

Patterns:
    PT-CMD-018 (Pre-Flight/temp-write): write_decision prueft Target-Dir/Schreibbarkeit
        BEVOR die temp angelegt wird (Fail-Loud statt Halb-Write).
    PT-CMD-011 (Fail-Loud): promote/epoch-Konflikt brechen laut ab statt still zu skippen.
    PT-CMD-007 (Idempotenz): Re-Eval nach Crash fuehrt zum selben Ziel-State (Single-Run-Effekt).

Contract (Blueprint BL-486_batch2 §7 Item 5 :331-337, Gold E4 :58-59):
    stage_decision_temp_path(bl_id, sub_batch_id) -> Path
    write_decision(decision: dict, *, bl_id, sub_batch_id) -> Path   # Pre-Flight -> temp
    promote(temp_path: Path, manifest_path: Path) -> None            # Reuse _atomic_write (temp->os.replace)
    epoch_guard(manifest: dict, decision: dict) -> bool              # Optimistic-Lock gegen E3-epoch
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Local-dir Imports (manifest_schema / factory_lock liegen im selben scripts/-Verzeichnis).
SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# REUSE (Gold E4 :114): das bestehende atomare os.replace-Primitiv — NICHT neu bauen.
from factory_lock import _atomic_write  # noqa: E402
# E3-Substrat: Optimistic-Lock-Basis (epoch) + monotoner Bump.
from manifest_schema import bump_epoch, current_stage_epoch  # noqa: E402


class ElevationFlushError(Exception):
    """Fail-Loud (PT-CMD-011): Pre-Flight- oder Optimistic-Lock-Konflikt beim Flush."""


def stage_decision_temp_path(bl_id: str, sub_batch_id: str) -> Path:
    """Pfad der temp-Datei, in die die Elevation-Entscheidung persistiert wird.

    DISTINCT vom Manifest-Pfad (Decision-Execution-Split): die Entscheidung lebt
    bis zum atomaren promote in einer eigenen ``.tmp``-Datei. Der Name traegt
    ``decision`` + ``.tmp`` (Blueprint :333).
    """
    safe_bl = str(bl_id).replace("/", "_")
    safe_sb = str(sub_batch_id).replace("/", "_")
    return SCRIPT_DIR / f".stage_elevation_decision_{safe_bl}_{safe_sb}.tmp"


def write_decision(decision: dict, *, bl_id: str, sub_batch_id: str) -> Path:
    """Pre-Flight (PT-CMD-018) -> schreibt die Entscheidung in die temp-Datei.

    Schreibt AUSSCHLIESSLICH die temp-Datei; das Manifest wird NICHT angefasst —
    die Entscheidung ist erst nach promote() wirksam (Decision-Execution-Split).

    Pre-Flight (PT-CMD-018): Target-Dir vorhanden + schreibbar BEVOR geschrieben wird
    (Fail-Loud statt korruptem Halb-Write).
    """
    temp_path = stage_decision_temp_path(bl_id, sub_batch_id)
    target_dir = temp_path.parent

    # Pre-Flight: Ziel-Verzeichnis muss existieren und schreibbar sein.
    if not target_dir.exists():
        raise ElevationFlushError(
            f"Pre-Flight (PT-CMD-018): Target-Dir fehlt: {target_dir}"
        )
    if not os.access(str(target_dir), os.W_OK):
        raise ElevationFlushError(
            f"Pre-Flight (PT-CMD-018): Target-Dir nicht schreibbar: {target_dir}"
        )

    payload = json.dumps(decision, ensure_ascii=False, indent=2)
    # temp direkt schreiben (NICHT _atomic_write — das ist fuer den finalen Manifest-Commit).
    temp_path.write_text(payload, encoding="utf-8")
    return temp_path


def epoch_guard(manifest: dict, decision: dict) -> bool:
    """Optimistic-Lock gegen den E3-``epoch`` (Blueprint :337).

    True gdw. der Manifest-``current_stage.epoch`` UNVERAENDERT ist seit der
    Entscheidung (``decision.epoch == manifest.current_stage.epoch``) -> promote erlaubt.
    False bei stale epoch (ein konkurrierender Flush hat zwischenzeitlich gebumpt) ->
    der promote MUSS abbrechen + re-evaluieren (kein blinder Overwrite eines neueren States).
    """
    decision_epoch = decision.get("epoch")
    if decision_epoch is None:
        # Keine Lock-Basis in der Entscheidung -> kein Optimistic-Lock moeglich.
        return False
    return current_stage_epoch(manifest) == decision_epoch


def _merge_decision_into_manifest(manifest: dict, decision: dict) -> dict:
    """Baut den promoteten Ziel-Manifest-State aus der Entscheidung (rein funktional).

    Idempotent (PT-CMD-007): bei gleichem Input -> gleicher Ziel-State. Der epoch wird
    monoton gebumpt (bump_epoch, E3) — der promote ist die einzige Stelle, die den
    Stage-Cursor weiterzieht.
    """
    promoted = bump_epoch(manifest)  # deep-copy + epoch += 1 (kein In-Place-Mutate des Inputs)
    next_stage = decision.get("next_stage")
    promoted["next_action"] = decision.get("next_action")
    promoted["next_stage"] = next_stage
    if next_stage is not None:
        promoted.setdefault("current_stage", {})["stage"] = next_stage
    return promoted


def promote(temp_path: Path, manifest_path: Path) -> None:
    """Promotet die persistierte Entscheidung ATOMAR ins Manifest (Reuse _atomic_write).

    Ablauf (Transaktions-Grenze):
      1. Entscheidung aus der temp-Datei lesen + aktuelles Manifest lesen.
      2. Optimistic-Lock (epoch_guard) — stale -> Fail-Loud-Abbruch (kein blinder Overwrite).
      3. Ziel-Manifest bauen (Merge + bump_epoch).
      4. ATOMAR committen via factory_lock._atomic_write (interner temp + os.replace).
         Crash in os.replace -> _atomic_write raised, Manifest BLEIBT unveraendert.
      5. Erst NACH erfolgreichem Commit die Decision-temp aufraeumen (sonst bleibt sie
         verwaist liegen -> detect_orphan_temp ermoeglicht idempotente Re-Eval).
    """
    temp_path = Path(temp_path)
    manifest_path = Path(manifest_path)

    decision = json.loads(temp_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Optimistic-Lock (PT-CMD-011 Fail-Loud): stale epoch -> Abbruch, kein Overwrite.
    if not epoch_guard(manifest, decision):
        raise ElevationFlushError(
            "Optimistic-Lock-Konflikt: Manifest-epoch hat sich seit der Entscheidung "
            f"geaendert (decision.epoch={decision.get('epoch')}, "
            f"manifest.epoch={manifest.get('current_stage', {}).get('epoch')}). "
            "Re-Eval noetig — kein blinder Overwrite."
        )

    promoted = _merge_decision_into_manifest(manifest, decision)
    content = json.dumps(promoted, ensure_ascii=False, indent=2)

    # ATOMARER COMMIT — Reuse des bestehenden Primitivs (temp + os.replace + cleanup).
    # Crash hier (os.replace raised) -> _atomic_write wirft, Manifest BLEIBT unveraendert,
    # die Decision-temp wird NICHT geloescht (verwaist -> idempotente Re-Eval).
    _atomic_write(manifest_path, content)

    # Commit erfolgreich -> Decision-temp ist verbraucht, aufraeumen (idempotent).
    try:
        temp_path.unlink()
    except OSError:
        pass


if __name__ == "__main__":  # pragma: no cover - CLI-Debughilfe, nicht test-relevant
    print("stage_elevation_flush: atomarer Elevation-Flush (temp -> os.replace via _atomic_write).")
