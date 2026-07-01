"""reindex_vault.py — BL-274 / batch_1 / M3 (Map-Reduce-Reindex-Orchestrator)

Orchestriert den vollstaendigen Vault-Reindex ueber die fertigen BL-242/BL-194-
Primitive (DRY, AK-1 / N6): MAP (cut_sections -> build_index je Sektion) ->
REDUCE (tree_merge_indexes baumartig, unter factory_lock) -> PERSIST
(serialize_index_json + committed Resume-Cursor) + CLEAN-STATE-Verifikation.

KEINE Primitive werden hier neu definiert — build_index / merge_vault_indexes /
serialize_index_json / cut_sections / _derive_map_slots / compute_coverage stammen
aus build_retrieval_index, acquire/release aus factory_lock (Re-Use per Identitaet).
"""

import json
import os
from pathlib import Path

import build_retrieval_index
import factory_lock

# Persistenz-Layout (identisch zu build_retrieval_index._build_and_persist).
_OUTPUT_SUBPATH = (".claude", "output", "retrieval_index")
_CURSOR_FILENAME = "_resume_cursor.json"

# Lock-Vertrag (AK-5 / SA-4): ein benannter, globaler REINDEX-Zweck.
_LOCK_SCOPE = "global"
_LOCK_PURPOSE = "REINDEX"
_LOCK_WORKER_ID = "reindex_vault"


def _out_dir(vault_root):
    """Persistenz-Verzeichnis fuer die maschinellen Indizes + den Resume-Cursor."""
    return os.path.join(vault_root, *_OUTPUT_SUBPATH)


def _cursor_path(out_dir):
    """Pfad des committed Sektions-Cursors (SA-6)."""
    return os.path.join(out_dir, _CURSOR_FILENAME)


def _section_key(section):
    """Stabiler, resume-fester Schluessel einer Sektion (Root-Liste -> str)."""
    return "|".join(str(root) for root in section)


def read_resume_cursor(out_dir):
    """AK-8 / SA-6: liest die committed Liste fertiger Sektions-Schluessel.

    Kein committed Cursor (Erst-Lauf) -> leere Liste (kein Crash).
    """
    cursor_file = _cursor_path(out_dir)
    if not os.path.exists(cursor_file):
        return []
    with open(cursor_file, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except (ValueError, OSError):
            return []
    return list(data) if isinstance(data, list) else []


def _write_resume_cursor(out_dir, section_keys):
    """Committed den Sektions-Cursor deterministisch (sort_keys via serialize)."""
    os.makedirs(out_dir, exist_ok=True)
    with open(_cursor_path(out_dir), "w", encoding="utf-8") as fh:
        fh.write(build_retrieval_index.serialize_index_json(sorted(section_keys)))


def _entry_identity(entry):
    """SA-2 Dedup-Key: die Eintrags-Identitaet (vollstaendiger, sortierter Inhalt).

    Verschachtelte Werte werden via JSON kanonisiert (hashbar + ordnungs-stabil).
    """
    return json.dumps(entry, sort_keys=True, default=str)


def tree_merge_indexes(part_indexes):
    """AK-4 + AK-6: baumartige (paarweise) Faltung der Teil-Indizes ueber
    merge_vault_indexes + Dedup ueber Eintrags-Identitaet.

    Baumartig statt seriell-akkumulativ: pro Runde werden NACHBAR-PAARE gemergt
    (Paar-von-Paaren), Tiefe ~ceil(log2 N). merge_vault_indexes konkateniert die
    Eintragslisten pro Key (dedupliziert selbst NICHT) -> der Dedup ueber die
    Eintrags-Identitaet erfolgt am Ende EINMAL ueber den gefalteten Index.
    """
    parts = [p for p in part_indexes if p is not None]
    if not parts:
        return {}

    # Baumartige Faltung: solange >1 Knoten, benachbarte Paare zusammenfuehren.
    level = list(parts)
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                merged = build_retrieval_index.merge_vault_indexes(
                    level[i], level[i + 1]
                )
            else:
                # Ungerader Rest wandert unveraendert eine Ebene hoch.
                merged = level[i]
            next_level.append(merged)
        level = next_level

    return _dedup_index(level[0])


def _dedup_index(index):
    """SA-2 (AK-6): pro Key Eintraege mit identischer Eintrags-Identitaet auf
    genau einen reduzieren; Erst-Vorkommen-Reihenfolge bleibt erhalten.
    """
    deduped = {}
    for key, entries in index.items():
        seen = set()
        kept = []
        for entry in entries:
            identity = _entry_identity(entry)
            if identity in seen:
                continue
            seen.add(identity)
            kept.append(entry)
        deduped[key] = kept
    return deduped


def _persist_index(out_dir, index):
    """PERSIST (AK-7): das finale keyword_index deterministisch als JSON ablegen
    (serialize_index_json sort_keys=True -> bit-identisch, _W_fetch-lesbar).
    """
    os.makedirs(out_dir, exist_ok=True)
    fpath = os.path.join(out_dir, "_keyword_index.json")
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(build_retrieval_index.serialize_index_json(index.get("keyword_index", {})))


def reindex_vault(vault_root, budget=1, resume=False):
    """AK-1: Map-Reduce-Reindex-Orchestrator.

    MAP: cut_sections(vault_root) -> build_index je Sektion (<=budget-1 parallele
    Slots via _derive_map_slots; B=1 -> seriell, heutiges Verhalten).
    REDUCE: tree_merge_indexes (baumartig) unter factory_lock (REINDEX-purpose/scope).
    PERSIST: serialize_index_json -> {vault}/.claude/output/retrieval_index/ +
    committed Resume-Cursor.

    resume=True: bereits persistierte (im Cursor committed) Sektionen werden NICHT
    neu gebaut (AK-8). Rueckgabe = das finale built-Index-Dict.
    """
    out_dir = _out_dir(vault_root)
    sections = build_retrieval_index.cut_sections([vault_root])

    # AK-3: parallele Map-Slots aus dem Budget (B=1 -> 0 -> seriell). Read-only
    # Politik-Ableitung; die tatsaechliche Slot-Verteilung bleibt heute seriell.
    _ = build_retrieval_index._derive_map_slots(budget)

    done_keys = set(read_resume_cursor(out_dir)) if resume else set()

    # --- MAP: je (noch nicht fertige) Sektion bauen ---
    # build_index liefert die D2-Form {keyword_index, edge_index, ...}; jede
    # innere Haelfte ist ein flaches {key: [entries]}-Dict (das merge_vault_indexes-
    # Eingabeformat). Der baumartige Merge faltet die keyword_index-Haelften.
    part_keyword_indexes = []
    completed_keys = set(done_keys)
    for section in sections:
        key = _section_key(section)
        if key in done_keys:
            # AK-8: persistierte Sektion NICHT neu bauen.
            continue
        built = build_retrieval_index.build_index(section)
        part_keyword_indexes.append(built.get("keyword_index", {}))
        completed_keys.add(key)

    # --- REDUCE: baumartiger Merge unter factory_lock (AK-5, single-writer) ---
    factory_lock.acquire(
        scope=_LOCK_SCOPE,
        purpose=_LOCK_PURPOSE,
        worker_id=_LOCK_WORKER_ID,
        vault_root=Path(vault_root),
    )
    try:
        merged_keyword = (
            tree_merge_indexes(part_keyword_indexes) if part_keyword_indexes else {}
        )
    finally:
        factory_lock.release(_LOCK_WORKER_ID, vault_root=Path(vault_root))

    # Finales built-Dict (D2-Form): die gefaltete keyword_index-Haelfte ist der
    # _W_fetch-Vertrag (AK-1 Rueckgabe-Shape).
    final_index = {"keyword_index": merged_keyword}

    # --- PERSIST: Index + committed Resume-Cursor (AK-7 / AK-8 / SA-6) ---
    _persist_index(out_dir, final_index)
    _write_resume_cursor(out_dir, completed_keys)

    return final_index


def verify_clean_state(index_files, vault_files):
    """AK-9/10/11: CLEAN-STATE-Verifikation.

    coverage_ok (AK-9): jeder Vault-Knoten ist im Index repraesentiert (missing leer)
      — DRY ueber compute_coverage-Logik (kein toter Vault-Knoten ohne Index-Eintrag).
    stale_evicted_ok (AK-10): jeder Index-Eintrags-Quellpfad existiert im aktuellen
      Vault-Walk (kein toter Index-Eintrag).
    clean_state (AK-11): coverage_ok UND stale_evicted_ok.
    """
    vault_set = set(vault_files)
    index_paths = {entry.get("path") for entry in index_files}

    missing = [p for p in vault_set if p not in index_paths]
    coverage_ok = not missing

    stale = [p for p in index_paths if p not in vault_set]
    stale_evicted_ok = not stale

    return {
        "coverage_ok": coverage_ok,
        "stale_evicted_ok": stale_evicted_ok,
        "clean_state": coverage_ok and stale_evicted_ok,
        "missing": sorted(missing),
        "stale": sorted(p for p in stale if p is not None),
    }
