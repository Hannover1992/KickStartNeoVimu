#!/usr/bin/env python3
"""guard_geist9_wave_conformance.py — N-Report Prozess-Konformitaets-Gate (BL-230 SB-3b, AK-G7-KONFORM).

Der heutige geist9 (`guard_geist9_post_sdf.py`) prueft Prozess-Konformitaet gegen GENAU EINEN
Batch-Report (die 4 Phase-3.x-Outputs `recalibrate/postItem/statusTransition/modelSync`; modelSync:SKIP
nur mit reason). Bei der parallelen Welle liefert der Fan-In N konsolidierte Batch-Reports (jeder der N
parallelen Batches hat seine eigenen Phase-3.x-Outputs). Das G7-Gate muss JEDEN der N validieren.

`wave_conformance_gate(reports)` ist die reine N-Report-Funktion:
  - nimmt eine LISTE von N Batch-Reports (kein Single-Report)
  - filter(None) fuer tote/leere Batches (1 toter Batch != Welle tot, konsistent SB-2/SB-3a)
  - pro lebendem Report: alle 4 Phase-3.x-Outputs vorhanden? (modelSync:SKIP+reason == konform,
    SKIP-ohne-reason == nicht-konform — Z167-173-Logik von guard_geist9_post_sdf.py wiederverwendet)
  - ALL-konjunktiv: Verletzung in IRGENDEINEM der N -> Gate-FAIL (fail-loud). PASS nur wenn ALLE konform.
  - permutations-invariant (reine Mengen-Pruefung, KOM-G7-1/2); N=1 == heutiger geist9 (KOM-G7-3, Null-Reg).
  - leere Liste -> definierter PASS-No-Op.

Rueckgabe (flexibles Schema): dict mit
  ok                 : True (PASS) / False (FAIL)
  divergent_batch_ids: Liste der nicht-konformen batch_id(s) (Befund)
  inventory          : dict batch_id -> {"conformant": bool, "missing": [..]} (Inventur pro batch_id)

Run: py -3 -m pytest .claude/scripts/test_guard_geist9_wave_conformance.py -q
"""

# Die 4 Phase-3.x-Pflicht-Outputs (analog REQUIRED_BERATER in guard_geist9_post_sdf.py).
REQUIRED_PHASE3_OUTPUTS = ("recalibrate", "postItem", "statusTransition", "modelSync")


def _report_batch_id(report):
    """Die batch_id eines Reports robust extrahieren (Fallback: stabiler Platzhalter)."""
    bid = report.get("batch_id")
    if bid is None:
        bid = report.get("id") or report.get("sub_batch")
    return bid


def _inspect_report(report):
    """Einen einzelnen lebenden Report inspizieren.

    Liefert (batch_id, conformant, missing). Wiederverwendet die Z167-173-Logik von
    guard_geist9_post_sdf.py: modelSync:SKIP+reason == konform, SKIP-ohne-reason == nicht-konform.
    """
    batch_id = _report_batch_id(report)
    outputs = report.get("BERATER_OUTPUTS", {}) or {}

    missing = [label for label in REQUIRED_PHASE3_OUTPUTS if label not in outputs]

    # Special: modelSync SKIP ohne reason (Z167-173). modelSync:SKIP IST vorhanden (nicht in missing),
    # aber ohne reason ist es nicht-konform -> named missing modelSync_skip_reason.
    modelsync_val = outputs.get("modelSync")
    is_skip = isinstance(modelsync_val, str) and modelsync_val.upper() == "SKIP"
    if is_skip:
        has_reason = (
            report.get("modelSync_skip_reason") is not None
            or report.get("skip_reason") is not None
        )
        # modelSync war via "SKIP" gesetzt -> es ist NICHT in `missing`. Bewerte den Skip:
        if has_reason:
            # legitimer Skip -> konform (modelSync bleibt aus missing).
            pass
        else:
            # SKIP ohne reason -> nicht-konform.
            missing.append("modelSync_skip_reason")

    return batch_id, (len(missing) == 0), missing


def wave_conformance_gate(reports):
    """N-Report Prozess-Konformitaets-Gate (ALL-konjunktiv, permutations-invariant, fail-loud).

    Args:
        reports: Liste von N Batch-Reports (dicts mit batch_id + BERATER_OUTPUTS). None-Eintraege
                 (tote Batches) werden via filter(None) ignoriert.

    Returns:
        dict {ok, divergent_batch_ids, inventory}. ok=True gdw. ALLE lebenden Reports konform sind.
        Leere/komplett tote Liste -> PASS-No-Op.
    """
    live = [r for r in (reports or []) if r]  # filter(None) — tote/leere Batches raus.

    inventory = {}
    divergent = []
    for report in live:
        batch_id, conformant, missing = _inspect_report(report)
        inventory[batch_id] = {"conformant": conformant, "missing": missing}
        if not conformant:
            divergent.append(batch_id)

    return {
        "ok": len(divergent) == 0,
        "divergent_batch_ids": divergent,
        "inventory": inventory,
    }
