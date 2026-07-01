"""
sdf_last_item_detect.py — BL-429 batch_1

3-Wege-Routing fuer SDF Loop-Ende-Erkennung.

INV-MODUS-1: Diese Funktion schreibt KEINEN 'modus'- oder 'batch_modes'-Key
in den Rueckgabe-Dict. Modus-Entscheidung ist ausschliesslich Aufgabe von
_SDF_berater_modusEntscheidung (BL-165).

Prioritaet: WEG1 (ROLLBACK) > WEG3 (TERMINATE) > WEG2 (RE-BATCH)
"""


def classify_route(
    idf_items: list,
    batch_done: list,
    completed_sub_batches: list,
    open_pl_deferred: list,
    stage_orphans: list,
) -> dict:
    """
    Bestimmt den SDF-Loop-Routing-Pfad nach BL-429 AK-4/5/6.

    Args:
        idf_items: Alle Items aus dem IDF-Scope (autoritativ).
        batch_done: Items, die als abgeschlossen gelten.
        completed_sub_batches: Abgeschlossene Sub-Batches (fuer kuenftige Erweiterungen).
        open_pl_deferred: Items im PL-Deferred-Status (offen, noch nicht erledigt).
        stage_orphans: Items, die im Stage haengen (unverarbeitet, keine Sub-Batch-Zuordnung).

    Returns:
        Dict mit Keys: weg (1|2|3), decision_token, is_last, reason.
        KEIN modus- oder batch_modes-Key (INV-MODUS-1).
    """
    idf_set = set(idf_items)
    done_set = set(batch_done)

    # Neue Orphans: open_pl_deferred-Items die NICHT in idf_items sind
    new_orphan_pl = [item for item in open_pl_deferred if item not in idf_set]

    # WEG1 (ROLLBACK): hoechste Prioritaet
    # Ausgeloest durch stage_orphans ODER echte neue PL-Orphans (nicht in idf_items)
    if stage_orphans or new_orphan_pl:
        return {
            "weg": 1,
            "decision_token": "ROLLBACK",
            "is_last": False,
            "reason": (
                "stage_orphans vorhanden" if stage_orphans
                else "open_pl_deferred enthaelt Items ausserhalb idf_items (neue Orphans)"
            ),
        }

    # is_last: alle idf_items erledigt, keine offenen Deferrals, keine Orphans
    is_last = (idf_set == done_set) and not open_pl_deferred and not stage_orphans

    # WEG3 (TERMINATE): alle erledigt, keine Probleme
    if is_last:
        return {
            "weg": 3,
            "decision_token": "TERMINATE",
            "is_last": True,
            "reason": "Alle idf_items abgeschlossen, keine offenen Deferrals oder Orphans.",
        }

    # WEG2 (RE-BATCH): Items noch offen oder bekannte Deferrals (in idf_items) offen
    return {
        "weg": 2,
        "decision_token": "RE-BATCH",
        "is_last": False,
        "reason": (
            "Noch nicht alle idf_items in batch_done, oder bekannte Deferrals offen."
        ),
    }
