"""parallel_suitability_producer.py — BL-342 Phase-7.8 Compute-Bridge (Plan-Zeit).

Deterministischer Compute-Driver fuer die IDF-Phase 7.8 (_IDF_berater_parallelSuitability).
Komponiert die zwei Substrat-Kernels zum KANONISCHEN, SERIALISIERBAREN
`DF_BATCH_STATE.parallel_suitability`-Block:
  sub_batch_targets.build_sub_batches  (file_index -> ziel_dateien je Sub-Batch)
  parallel_suitability.suitability_for_batches  (Konflikt-Inseln + build_share-Daempfung)

ARCHITEKTUR (machine-not-context, konsistent mit den Beratern): die Manifest-I/O
(Markdown-Bloecke lesen/schreiben) bleibt WORKER-seitig — manifest_reader liefert nur
Block-TEXT, kein nested-YAML, und schreibt nur key:value. Diese Bruecke macht NUR die
BERECHNUNG deterministisch: der Worker extrahiert `batch_items_per_batch` (DF_BATCH_STATE)
+ `file_index` (BERATER_OUTPUTS.dependencyAnalyzer), pipet sie als JSON hier rein, bekommt
den fertigen Block als JSON raus und schreibt ihn via Edit additiv ins DF_BATCH_STATE.

CLI:  echo '{"batch_items_per_batch": {...}, "file_index": {...}}' | py -3 parallel_suitability_producer.py
      -> stdout = JSON des parallel_suitability-Blocks. Optionales "change_type_map".

KANONISCHER Block (story-level ueber ALLE Sub-Batches — der Producer nimmt die ganze
Liste, liefert EINEN Verdict; per-batch waere irrefuehrend): {format_version, story_type,
conflict_islands, largest_island, build_share, recommended_N, suitable, reason,
ziel_dateien_per_batch, matrix[]}. matrix = Liste von {pair:[a,b], status, files}
(KEINE tuple-keys -> JSON/YAML-serialisierbar).

Konsument (Wellen-Scheduler, BL-230 Phase C): bei fehlendem Feld konservativ seriell.
"""
import json
import sys
from typing import Dict, List, Optional, Any

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import sub_batch_targets as sbt
import parallel_suitability as ps

FORMAT_VERSION = ps.FORMAT_VERSION


def _find_resource_conflicts(
    batch_ids: List[str],
    batch_stages: Dict[str, List[int]],
    resources_per_stage: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Ermittle geteilte unteilbare Ressourcen zwischen Sub-Batch-Paaren.

    Gibt eine Liste von {resource_id, divisibility, batches} zurueck — eine Eintrag
    pro konflikt-verursachender unteilbarer Ressource (AK-3a). Leere Liste wenn keine
    Konflikte vorhanden. Default-Divisibility bei fehlendem Eintrag = 'unteilbar' (AK-6)."""
    # Baue Map: batch_id -> set of unteilbare resource_ids (aus ihren Stages)
    batch_unteilbar: Dict[str, set] = {}
    for batch_id in batch_ids:
        stages = batch_stages.get(batch_id, [])
        unteilbar_res: set = set()
        for stage_nr in stages:
            stage_info = resources_per_stage.get(stage_nr, {})
            resource_ids = stage_info.get("resource_ids", [])
            divisibility_map = stage_info.get("divisibility", {})
            for rid in resource_ids:
                # Default-Divisibility = 'unteilbar' wenn kein Eintrag (AK-6 / T-c2)
                div = divisibility_map.get(rid, "unteilbar")
                if div == "unteilbar":
                    unteilbar_res.add(rid)
        batch_unteilbar[batch_id] = unteilbar_res

    # Suche geteilte unteilbare Ressourcen: akkumuliere pro resource_id welche Batches betroffen
    resource_to_batches: Dict[str, List[str]] = {}
    for batch_id, res_set in batch_unteilbar.items():
        for rid in res_set:
            resource_to_batches.setdefault(rid, []).append(batch_id)

    conflicts = []
    for rid, batches in resource_to_batches.items():
        if len(batches) >= 2:
            conflicts.append({
                "resource_id": rid,
                "divisibility": "unteilbar",
                "batches": sorted(batches),
            })
    return conflicts


def produce_block(
    batch_items_per_batch: Optional[Dict[str, Any]],
    file_index: Optional[Dict[str, Any]],
    change_type_map: Optional[Dict[str, str]] = None,
    n_cap: int = 4,
    batch_stages: Optional[Dict[str, List[int]]] = None,
    resources_per_stage: Optional[Dict[int, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Kanonischer, serialisierbarer DF_BATCH_STATE.parallel_suitability-Block.

    Deterministisch. None-tolerant (leere Inputs -> Trivial-Block recommended_N=1).

    Optionale Parameter batch_stages + resources_per_stage aktivieren Post-Processing
    fuer Resource-Divisibilitaets-Konflikte (BL-415 AK-2/AK-3):
      batch_stages: {batch_id: [stage_nr, ...]} — welche Stages ein Batch belegt
      resources_per_stage: {stage_nr: {resource_ids: [...], divisibility: {res_id: str}}}
    Ohne diese Parameter: unveraendertes Verhalten (Backward-Compat, kein resource_conflicts-Key).
    Default-Divisibility bei fehlendem divisibility-Eintrag = 'unteilbar' (AK-6 / T-c2)."""
    sub_batches = sbt.build_sub_batches(batch_items_per_batch, file_index, change_type_map)
    res = ps.suitability_for_batches(sub_batches, n_cap=n_cap)
    # tuple-keys (id_a,id_b) -> serialisierbare Liste (AK-2: erklaerbar, welche Datei teilt das Paar)
    matrix = [
        {"pair": [a, b], "status": v["status"], "files": v["files"]}
        for (a, b), v in res["matrix"].items()
    ]

    recommended_N = res["recommended_N"]

    # Post-Processing: Resource-Divisibilitaet (BL-415) — NUR wenn batch_stages uebergeben
    if batch_stages is not None:
        effective_resources = resources_per_stage or {}
        batch_ids = list((batch_items_per_batch or {}).keys())
        resource_conflicts = _find_resource_conflicts(batch_ids, batch_stages, effective_resources)

        # Baue Menge konfligierender Batch-Paare aus Resource-Conflicts
        conflicting_pairs: set = set()
        for rc in resource_conflicts:
            batches = rc["batches"]
            for i in range(len(batches)):
                for j in range(i + 1, len(batches)):
                    conflicting_pairs.add((batches[i], batches[j]))
                    conflicting_pairs.add((batches[j], batches[i]))

        # Aktualisiere matrix: 'disjoint' -> 'resource_conflict' wenn Paar konfligiert.
        # overlap DOMINIERT resource_conflict (T-c1): 'overlap' bleibt unveraendert.
        updated_matrix = []
        conflict_edges = 0
        for entry in matrix:
            pair_key = (entry["pair"][0], entry["pair"][1])
            pair_key_rev = (entry["pair"][1], entry["pair"][0])
            if entry["status"] == "disjoint" and (pair_key in conflicting_pairs or pair_key_rev in conflicting_pairs):
                updated_matrix.append({"pair": entry["pair"], "status": "resource_conflict", "files": entry["files"]})
                conflict_edges += 1
            else:
                updated_matrix.append(entry)
        matrix = updated_matrix

        # Reduziere recommended_N: resource_conflict-Kanten koppeln Paare -> weniger Parallelitaet
        if conflict_edges > 0:
            # Zaehle echte disjoint-Paare (ohne jegliche Konflikte)
            true_disjoint = sum(1 for e in matrix if e["status"] == "disjoint")
            # recommended_N = max(1, conflict_islands aus file-Sicht - Anzahl resource_conflict-Paare)
            # Konservativ: wenn es resource_conflict-Kanten gibt, reduziere um 1 pro Konflikt-Kante
            recommended_N = max(1, res["recommended_N"] - conflict_edges)

        blk = {
            "format_version": FORMAT_VERSION,
            "story_type": res["story_type"],
            "conflict_islands": res["conflict_islands"],
            "largest_island": res["largest_island"],
            "build_share": res["build_share"],
            "recommended_N": recommended_N,
            "suitable": res["suitable"],
            "reason": res["reason"],
            "ziel_dateien_per_batch": sbt.ziel_dateien_per_batch(batch_items_per_batch, file_index),
            "matrix": matrix,
            "resource_conflicts": resource_conflicts,
        }
    else:
        blk = {
            "format_version": FORMAT_VERSION,
            "story_type": res["story_type"],
            "conflict_islands": res["conflict_islands"],
            "largest_island": res["largest_island"],
            "build_share": res["build_share"],
            "recommended_N": recommended_N,
            "suitable": res["suitable"],
            "reason": res["reason"],
            "ziel_dateien_per_batch": sbt.ziel_dateien_per_batch(batch_items_per_batch, file_index),
            "matrix": matrix,
        }

    return blk


def main(argv: Optional[List[str]] = None) -> int:
    """CLI-Bruecke: JSON von stdin -> parallel_suitability-Block als JSON auf stdout.

    Input-Keys: batch_items_per_batch (PFLICHT), file_index (PFLICHT),
    change_type_map (optional), n_cap (optional, default 4)."""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        sys.stderr.write(f"[parallel_suitability_producer] invalid JSON stdin: {e}\n")
        return 2
    blk = produce_block(
        payload.get("batch_items_per_batch"),
        payload.get("file_index"),
        payload.get("change_type_map"),
        payload.get("n_cap", 4),
    )
    sys.stdout.write(json.dumps(blk, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
