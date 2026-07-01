#!/usr/bin/env python3
"""
guard_pc_invariants.py — BL-194-N11: Invarianten-Checks fuer Parallel-Coordination (PC)

Implementiert INV-PC-7 (worker_id Pflicht im parallelen Modus) und
INV-PC-12 (kein Doppel-Build eines bereits abgeschlossenen BL).

Hinweis: Die 12 Invarianten des superseded dispatch_plan/master-lock-Designs
(BL-175 Pre-194-Umbau) sind NICHT enthalten — nur die im worktree-lane-Modell
(BL-194, BL-431) ueberlebenden Invarianten INV-PC-7 und INV-PC-12.

BL-194: BL-Level Parallelism Coordination
INV-PC-7: Im parallelen Modus (parallelism_budget>1) MUSS jeder Audit-Eintrag
          ein nicht-leeres worker_id-Feld tragen.
INV-PC-12: Ein BL darf nicht gebaut werden, wenn es bereits in completed_bls ist
           (Doppel-Build-Schutz).
"""

from __future__ import annotations

from typing import Optional


def check_inv_pc_7(entry: dict, parallelism_budget) -> list:
    """BL-194-N11, INV-PC-7: Prueft ob worker_id im parallelen Modus gesetzt ist.

    parallel (budget>1) UND kein nicht-leeres entry["worker_id"] -> ["INV-PC-7 ...worker_id..."].
    budget<=1 -> [] (FP-frei fuer serielle Laeufe).
    parallel + worker_id vorhanden -> [].

    Args:
        entry: Audit-Eintrag-Dict.
        parallelism_budget: Anzahl paralleler Worker (int oder str; None -> 0).

    Returns:
        Liste mit Violation-Strings (leer = kein Verstoss).
    """
    try:
        budget = int(parallelism_budget) if parallelism_budget is not None else 0
    except (ValueError, TypeError):
        budget = 0

    if budget <= 1:
        return []

    # Parallelmodus: worker_id muss gesetzt und nicht-leer sein
    worker_id = entry.get("worker_id", "")
    if not worker_id:
        return [
            "INV-PC-7: Parallelmodus (parallelism_budget>1) erfordert nicht-leeres "
            "worker_id-Feld im Audit-Eintrag — fehlt oder leer."
        ]
    return []


def check_inv_pc_12(bl_id: str, completed_bls) -> list:
    """BL-194-N11, INV-PC-12: Prueft ob bl_id bereits in completed_bls (Doppel-Build).

    bl_id in completed_bls (getrimmt) -> ["INV-PC-12 ...Doppel-Build..."].
    sonst -> [].

    Args:
        bl_id: Zu pruefende BL-ID.
        completed_bls: Iterable bereits abgeschlossener BL-IDs (None oder leer = kein Check).

    Returns:
        Liste mit Violation-Strings (leer = kein Verstoss).
    """
    if not completed_bls:
        return []

    stripped_id = bl_id.strip()
    completed_set = {c.strip() for c in completed_bls}

    if stripped_id in completed_set:
        return [
            f"INV-PC-12: {stripped_id} ist bereits in completed_bls — "
            "Doppel-Build verhindert. BL wurde bereits abgeschlossen."
        ]
    return []
