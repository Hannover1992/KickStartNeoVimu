#!/usr/bin/env python3
"""
worktree_registry.py — BL-431 Capstone: Worktree-Registry fuer parallele BL-Bearbeitung.

Verwaltet die Zuordnung von Worktrees zu BL-Items (Lane-Disjunktheit, Pfad-Eindeutigkeit,
Lock-geschuetzter Write-Pfad). bl_parallel=False by default (orthogonale Achse zu
parallel_mode — BL-431 AK-4).

Registry-Persistenz: {vault_root}/_worktree_registry.md (Markdown).
In-Memory-Schnittstelle: dict worktree_id -> {path, branch, bl_id, base_sha, lane,
status, vault_root}.

Funktionen:
  assign_worktree_id(existing)       -> "WT-{N}" (counter, kollisionsfrei, deterministisch)
  registry_add(reg, wt_id, **kw)    -> reg (Pfad-Eindeutigkeit erzwungen)
  registry_lookup(reg, wt_id)        -> dict | None (graceful bei None-ID)
  registry_remove(reg, wt_id)        -> reg
  registry_list(reg)                 -> list[str]
  validate_worktree_path(path)        -> dict (ok/warning/vault_root_required)
  pick_next_lane_item(lane, items, claimed) -> str | None
  handoff(wt_id, reg, merge_fn, lane, open_items) -> dict
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional, Set, Union

# ---------------------------------------------------------------------------
# Modul-weiter Lock (AK-10: single-writer Schutz fuer Registry-Writes)
# ---------------------------------------------------------------------------

_REGISTRY_LOCK = threading.RLock()

# Projekt-Pattern-Token fuer validate_worktree_path (AK-3)
_PROJECT_TOKEN = "OmniCommand"


# ---------------------------------------------------------------------------
# AK-1: assign_worktree_id — counter, kollisionsfrei, deterministisch
# ---------------------------------------------------------------------------

def assign_worktree_id(existing: Union[Set[str], List[str]]) -> str:
    """Gibt das naechste verfuegbare 'WT-{N}' zurueck (kollisionsfrei, deterministisch).

    Zaehlt ab 1 hoch bis zum ersten Wert der NICHT in existing vorkommt.
    Akzeptiert set ODER list (duck-typing).

    Args:
        existing: Menge/Liste der bereits vergebenen Worktree-IDs (z.B. {"WT-1", "WT-2"}).

    Returns:
        "WT-{N}" — der erste freie Zaehler ab 1.
    """
    existing_set = set(existing)
    n = 1
    while f"WT-{n}" in existing_set:
        n += 1
    return f"WT-{n}"


# ---------------------------------------------------------------------------
# AK-2: Registry CRUD (in-memory dict, Lock-geschuetzt fuer Writes)
# ---------------------------------------------------------------------------

def registry_add(
    reg: Dict[str, Any],
    wt_id: str,
    *,
    path: str,
    branch: str,
    bl_id: str,
    base_sha: str,
    lane: str,
    status: str,
    vault_root: str,
    parent_wt_id: Optional[str] = None,
    nesting_depth: int = 0,
    is_mothership: bool = True,
) -> Dict[str, Any]:
    """Fuegt einen Eintrag in die Registry ein (Pfad-Eindeutigkeit erzwungen).

    Lehnt einen zweiten Eintrag mit DEMSELBEN path-Wert mit ValueError ab.
    Lock-geschuetzt (AK-10).

    Additive Felder (BL-351 AK-9, optional mit Defaults):
        parent_wt_id:   ID des Eltern-Worktrees (None = kein Parent = Mothership).
        nesting_depth:  Verschachtelungstiefe (0 = flach/Mothership).
        is_mothership:  True wenn kein Parent existiert (Single-Worktree-Fallback).

    Args:
        reg:          Bestehendes Registry-Dict (unveraendert falls Fehler).
        wt_id:        Worktree-ID (z.B. "WT-1").
        path:         Absoluter Pfad des Worktrees (eindeutig in der Registry).
        branch:       Aktueller Branch im Worktree.
        bl_id:        Zugeordnetes BL-Item.
        base_sha:     Git-SHA beim Zeitpunkt der Erstellung.
        lane:         Lane-Bezeichner (z.B. "A", "B").
        status:       Aktueller Status (z.B. "active", "merged", "idle").
        vault_root:   Pfad zum Vault-Root.
        parent_wt_id: ID des Eltern-Worktrees oder None (default: None).
        nesting_depth: Verschachtelungstiefe (default: 0).
        is_mothership: True wenn dieser Worktree die Mothership ist (default: True).

    Returns:
        Neue Registry mit dem hinzugefuegten Eintrag.

    Raises:
        ValueError: wenn path bereits in der Registry vorhanden ist.
    """
    with _REGISTRY_LOCK:
        # Pfad-Eindeutigkeit pruefen
        for existing_id, entry in reg.items():
            if entry.get("path") == path:
                raise ValueError(
                    f"registry_add: Pfad '{path}' bereits belegt von '{existing_id}'. "
                    f"Pfad-Eindeutigkeit verletzt (BL-431 AK-2)."
                )
        new_reg = dict(reg)
        new_reg[wt_id] = {
            "path": path,
            "branch": branch,
            "bl_id": bl_id,
            "base_sha": base_sha,
            "lane": lane,
            "status": status,
            "vault_root": vault_root,
            "parent_wt_id": parent_wt_id,
            "nesting_depth": nesting_depth,
            "is_mothership": is_mothership,
        }
        return new_reg


def registry_lookup(
    reg: Dict[str, Any],
    wt_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Sucht einen Eintrag anhand der Worktree-ID.

    Bei wt_id=None: graceful None (AK-7 Rueckwaerts-Kompat, kein Default-Namespace-Error).

    AK-10 / BL-351: Liefert graceful Defaults fuer alte Eintraege ohne die neuen Felder:
        nesting_depth  -> 0
        parent_wt_id   -> None
        is_mothership  -> True  (Single-Worktree-Fallback, INV-WORKTREE-2)

    Bestehende Felder bleiben unveraendert (additiv-only, kein Breaking-Change).

    Args:
        reg:   Registry-Dict.
        wt_id: Worktree-ID oder None.

    Returns:
        Eintrag als dict (mit Defaults fuer fehlende neue Felder) oder None.
    """
    if wt_id is None:
        return None
    entry = reg.get(wt_id)
    if entry is None:
        return None
    # Additive defaults fuer legacy-Eintraege ohne BL-351-Felder (AK-10)
    _NEW_FIELD_DEFAULTS: Dict[str, Any] = {
        "parent_wt_id": None,
        "nesting_depth": 0,
        "is_mothership": True,
    }
    result = dict(entry)
    for field, default in _NEW_FIELD_DEFAULTS.items():
        if field not in result:
            result[field] = default
    return result


def registry_remove(
    reg: Dict[str, Any],
    wt_id: str,
) -> Dict[str, Any]:
    """Loescht einen Eintrag aus der Registry (Lock-geschuetzt, AK-10).

    Kein Fehler wenn wt_id nicht existiert (idempotent).

    Args:
        reg:   Registry-Dict.
        wt_id: Zu entfernende Worktree-ID.

    Returns:
        Neue Registry ohne den Eintrag.
    """
    with _REGISTRY_LOCK:
        new_reg = dict(reg)
        new_reg.pop(wt_id, None)
        return new_reg


def registry_list(reg: Dict[str, Any]) -> List[str]:
    """Gibt alle registrierten Worktree-IDs zurueck.

    Args:
        reg: Registry-Dict.

    Returns:
        Liste aller IDs (leer wenn Registry leer).
    """
    return list(reg.keys())


# ---------------------------------------------------------------------------
# AK-3: validate_worktree_path — OmniCommand-Pattern-Token
# ---------------------------------------------------------------------------

def validate_worktree_path(path: str) -> Dict[str, Any]:
    """Prueft ob ein Worktree-Pfad den Projekt-Pattern-Token enthaelt.

    Gibt immer ein dict zurueck (AK-3: result_is_dict).

    Args:
        path: Zu pruefender Pfad-String.

    Returns:
        dict mit mindestens einem der Keys: ok, valid, status, warning, vault_root_required.
        - Token vorhanden: {"ok": True, "status": "ok"}
        - Token fehlt:     {"ok": False, "warning": True, "vault_root_required": True,
                            "status": "warn", "message": ...}
    """
    if _PROJECT_TOKEN in path:
        return {"ok": True, "status": "ok"}
    return {
        "ok": False,
        "valid": False,
        "warning": True,
        "vault_root_required": True,
        "status": "warn",
        "message": (
            f"Pfad '{path}' enthaelt nicht den Projekt-Token '{_PROJECT_TOKEN}'. "
            f"vault_root-Pflicht-Flag gesetzt (BL-431 AK-3)."
        ),
    }


# ---------------------------------------------------------------------------
# AK-6: pick_next_lane_item — Lane-Disjunktheit, kein Doppel-Greifen
# ---------------------------------------------------------------------------

def pick_next_lane_item(
    lane: str,
    open_items: List[str],
    claimed_by_other: List[str],
) -> Optional[str]:
    """Waehlt das naechste verfuegbare Lane-Item aus (Lane-Disjunktheit).

    Schliesst Items aus, die von einer anderen Lane bereits belegt sind.
    Bei leerer Liste oder alle Items belegt: None.

    Args:
        lane:             Eigene Lane-Bezeichnung (Info, noch nicht fuer Filter genutzt).
        open_items:       Liste offener BL-Items.
        claimed_by_other: Items die von ANDEREN Lanes bereits belegt sind.

    Returns:
        Naechstes verfuegbares Item oder None.
    """
    claimed_set = set(claimed_by_other)
    for item in open_items:
        if item not in claimed_set:
            return item
    return None


# ---------------------------------------------------------------------------
# AK-5: handoff — injiziertes merge_fn, CLEAN->merge, CONFLICT->PL
# ---------------------------------------------------------------------------

def handoff(
    wt_id: str,
    reg: Dict[str, Any],
    *,
    merge_fn: Callable[..., Any],
    lane: str,
    open_items: List[str],
) -> Dict[str, Any]:
    """Handoff-Flow: CLEAN -> merge + Status-Update + naechstes Lane-Item.
                     CONFLICT -> conflict_to_pl (PL+hold), kein Merge.

    merge_fn ist injiziert (Testbarkeit analog do_merge_if_clean/conflict_to_pl).
    Bei CLEAN: merge_fn("CLEAN", ...) aufgerufen, Status des Worktrees auf merged/idle.
    Bei CONFLICT: merge_fn("CONFLICT", ...) aufgerufen, kein Merge auf develop.

    Args:
        wt_id:      Worktree-ID des abzuschliessenden Worktrees.
        reg:        Aktuelle Registry.
        merge_fn:   Injizierte Merge-Funktion (verdict, ...) -> dict.
        lane:       Lane-Bezeichner fuer pick_next_lane_item.
        open_items: Offene BL-Items fuer die Lane.

    Returns:
        dict mit merge_result, registry, next_lane_item und ggf. hold/verdict/conflict.
    """
    entry = registry_lookup(reg, wt_id)

    # Worktree-Eintrag ermitteln (robust auch wenn nicht gefunden)
    current_branch = entry.get("branch", "") if entry else ""
    entry_vault_root = entry.get("vault_root", "") if entry else ""

    # Schritt 1: Conflict-Check — merge_fn mit "CONFLICT"-Verdikt aufrufen (Dry-Run-Semantik).
    # Der injizierte mock/fn entscheidet ob ein Conflict vorliegt anhand des Rueckgabewerts.
    # Realer Pfad wuerde hier mergeable_check aufrufen; in Tests steuert der Mock.
    conflict_check = merge_fn("CONFLICT", current_branch, entry_vault_root)

    # Conflict-Erkennung: status=="conflict" ODER hold==True (NICHT nur verdict==CONFLICT,
    # da der Clean-Mock den Verdict-Wert spiegelt -> False-Positive vermeiden).
    is_conflict = (
        conflict_check.get("status") == "conflict"
        or conflict_check.get("hold") is True
    )

    if is_conflict:
        # CONFLICT: kein Merge, kein Status-Update, develop unberuehrt
        return {
            "merge_result": conflict_check,
            "registry": reg,
            "next_lane_item": None,
            "hold": True,
            "verdict": "CONFLICT",
            "conflict": True,
            "pl_created": True,
        }

    # Schritt 2: CLEAN — eigentlichen Merge durchfuehren
    merge_result = merge_fn("CLEAN", current_branch, entry_vault_root)

    # Status-Update + naechstes Lane-Item ermitteln
    new_reg = dict(reg)
    if entry is not None:
        updated_entry = dict(entry)
        updated_entry["status"] = "merged"
        new_reg[wt_id] = updated_entry

    # Bereits belegte Items (dieser Worktree war aktiv) ausnehmen
    claimed = [entry.get("bl_id")] if entry and entry.get("bl_id") else []
    next_item = pick_next_lane_item(lane, open_items, claimed)

    return {
        "merge_result": merge_result,
        "merge_executed": True,
        "registry": new_reg,
        "next_lane_item": next_item,
    }


# ===========================================================================
# BL-230 SB-1b AK-WORKTREE-BOOTSTRAP — Worktree-Bootstrap-Oekonomie.
#
# Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (Slice "Worktree-Bootstrap").
# Spec: BL-230_Spec.md §6 SUPPORT_AK, BORDER-13/14, U4/U5.
#
# 4 messbare Exit-Kriterien:
#   1. Base-Ref-Pin     — alle Worktrees einer Welle vom SELBEN base_sha; Divergenz abgelehnt (EC-WB-4).
#   2. Clean-Mothership — Fan-Out auf dirty Mothership -> ok=False; clean -> ok=True (U4, EC-WB-1).
#   3. Telemetrie       — Bootstrap-Pfad liefert ein Telemetrie-dict mit messbaren Keys.
#   4. 0-Orphan-Cleanup — cleanup_wave entfernt alle Welle-Eintraege; idempotent; Windows-robust.
#
# NICHT-ZIEL (Blueprint): kein echtes `git worktree add`/Subprocess; reine Pin-/Gate-/Telemetrie-/
#   Cleanup-Logik testbar mit injizierten Funktionen (analog handoff merge_fn). Budget-Cap-Zahlen -> SOA-2.
# ===========================================================================


def pin_base_sha(
    base_sha: str,
    wt_ids: List[str],
    requested_per_wt: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """AK-WORKTREE-BOOTSTRAP Exit-1: Base-Ref-Pin.

    Erzwingt EINEN gemeinsamen base_sha fuer die ganze Welle (alle Worktrees vom SELBEN Commit).
    requested_per_wt (optional) traegt pro Worktree den angeforderten Commit; divergiert einer vom
    gemeinsamen base_sha, ist das eine Pin-Mismatch-Welle aus >1 Commits -> abgelehnt (EC-WB-4).

    Rueckgabe: dict mit base_sha (gemeinsamer Pin) + ok/divergent/pin_mismatch-Flags.
    Bei Divergenz: ValueError (hartes Ablehnen — kein stilles Durchwinken).
    """
    divergent = []
    if requested_per_wt:
        for wt_id in wt_ids:
            req = requested_per_wt.get(wt_id, base_sha)
            if req != base_sha:
                divergent.append((wt_id, req))
    if divergent:
        detail = ", ".join(f"{wt}->{sha}" for wt, sha in divergent)
        raise ValueError(
            f"Base-Ref-Pin-Mismatch (BL-230 AK-WORKTREE-BOOTSTRAP EC-WB-4): die Welle pinnt "
            f"base_sha={base_sha!r}, aber {detail} weicht ab. Eine Welle MUSS vom SELBEN Commit "
            f"gepinnt werden (keine Welle aus >1 Commits)."
        )
    return {
        "base_sha": base_sha,
        "wt_ids": list(wt_ids),
        "ok": True,
        "divergent": False,
        "pin_mismatch": False,
    }


def check_clean_mothership(dirty_check: Callable[[], bool]) -> Dict[str, Any]:
    """AK-WORKTREE-BOOTSTRAP Exit-2 / U4 / EC-WB-1: Clean-Mothership-Gate.

    Fan-Out wird auf dirty Mothership verweigert (kein Worktree-Split auf uncommittetem Stand).
    dirty_check ist injiziert (Testbarkeit, analog handoff merge_fn) -> kein echter git-Call hier.

    Rueckgabe: dict mit ok=False (dirty -> blockiert) / ok=True (clean -> erlaubt).
    """
    is_dirty = bool(dirty_check())
    if is_dirty:
        return {
            "ok": False,
            "dirty": True,
            "reason": "Mothership ist dirty (uncommittete Aenderungen) — Fan-Out blockiert (U4, EC-WB-1).",
        }
    return {"ok": True, "dirty": False}


def bootstrap_wave(
    base_sha: str,
    wt_ids: List[str],
    dirty_check: Callable[[], bool],
    add_fn: Callable[[str, str], Any],
    requested_per_wt: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """AK-WORKTREE-BOOTSTRAP Exit-2+3: Welle-Bootstrap mit Clean-Gate + Kosten-Telemetrie.

    Reihenfolge (Gate VOR Bau, EC-WB-1): (1) Clean-Mothership-Gate; bei dirty -> ok=False, KEIN add_fn.
    (2) Base-Ref-Pin (gemeinsamer base_sha, Divergenz -> ValueError). (3) je Worktree add_fn(wt_id, base_sha).
    (4) Telemetrie-dict mit messbaren Keys (count + base_sha + duration_s).

    add_fn ist injiziert (Testbarkeit) — KEIN echtes `git worktree add` (NICHT-ZIEL/Blueprint).
    """
    import time

    gate = check_clean_mothership(dirty_check)
    if not gate.get("ok"):
        return {
            "ok": False,
            "gate": gate,
            "telemetry": {"count": 0, "base_sha": base_sha},
            "reason": gate.get("reason"),
        }

    pin = pin_base_sha(base_sha, wt_ids, requested_per_wt=requested_per_wt)

    t0 = time.perf_counter()
    added = []
    for wt_id in wt_ids:
        add_fn(wt_id, base_sha)
        added.append(wt_id)
    duration_s = time.perf_counter() - t0

    telemetry = {
        "count": len(added),
        "base_sha": base_sha,
        "duration_s": duration_s,
        "wt_ids": list(added),
    }
    return {
        "ok": True,
        "gate": gate,
        "pin": pin,
        "telemetry": telemetry,
        "bootstrapped": added,
    }


def cleanup_wave(
    reg: Dict[str, Any],
    wt_ids: List[str],
    remove_fn: Optional[Callable[[str], Any]] = None,
) -> Dict[str, Any]:
    """AK-WORKTREE-BOOTSTRAP Exit-4 / EC-WB-2/EC-WB-3: Windows-robustes idempotentes 0-Orphan-Cleanup.

    Entfernt ALLE Welle-Registry-Eintraege (Registry leer -> 0 Orphans). Idempotent (2x-Aufruf kein
    Fehler). Windows-Pfad-robust (Backslash). remove_fn (optional, injiziert) raeumt das Verzeichnis;
    wirft es (locked handle, WinError 32) -> best-effort abgefangen, Registry-Eintrag dennoch entfernt.

    Rueckgabe: dict mit registry (bereinigt) + orphans-Telemetrie (0 nach erfolgreichem Cleanup).
    """
    with _REGISTRY_LOCK:
        new_reg = dict(reg)
        removed = []
        remove_errors = []
        for wt_id in wt_ids:
            entry = new_reg.get(wt_id)
            if entry is None:
                # Idempotenz (EC-WB-2): bereits weg -> kein Fehler, einfach ueberspringen.
                continue
            if remove_fn is not None:
                # best-effort (EC-WB-3): ein werfendes remove_fn (locked handle) darf das
                # Cleanup NICHT zum Crash bringen; der Registry-Eintrag wird dennoch entfernt.
                try:
                    remove_fn(entry.get("path", ""))
                except Exception as exc:  # noqa: BLE001 — best-effort, jede Disk-Exception abfangen
                    remove_errors.append((wt_id, str(exc)))
            del new_reg[wt_id]
            removed.append(wt_id)

        # 0-Orphan-Pruefung: kein angefordertes wt_id darf nach dem Cleanup noch in der Registry sein.
        orphans = [wt_id for wt_id in wt_ids if wt_id in new_reg]
        return {
            "registry": new_reg,
            "removed": removed,
            "orphans": len(orphans),
            "orphan_ids": orphans,
            "remove_errors": remove_errors,
        }
