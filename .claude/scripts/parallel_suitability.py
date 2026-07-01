"""parallel_suitability.py — BL-342 Stufe-1 Parallel-Suitability-Producer (Plan-Zeit).

Deterministischer, ERKLAERBARER Producer fuer den IDF->SDF-Contract (BL-353 Phase 1a,
Roadmap Phase C). Aus den Sub-Batches (je `ziel_dateien` + optional `change_type`):
  - conflict_matrix(): pairwise ziel_dateien-Ueberlappung (AK-1/AK-2) — WELCHE Datei
    teilt ein Paar (kein Black-Box-Score). Stufe-1-Praediktor (BL-316: Datei-Disjunktheit
    = 0-Lost-Update-Bedingung).
  - suitability_for_batches(): aggregat — Konflikt-Insel-Zahl (zusammenhaengende
    Sub-Batches via geteilte Dateien) als Plan-Zeit-Parallelitaets-Mass, build_share-
    gedaempft (AK-6: add/assert=build vs modify=review). NICHT shatter (das ist commit-
    level, gehoert in die Mess-Forensik CaseStudies/, nicht den Plan-Zeit-Producer).

WICHTIG (ehrliche Granularitaets-Grenze): Plan-Zeit kennt nur DATEIEN (ziel_dateien),
nicht Zeilen-Regionen. Daher = FILE-level Konflikt (Stufe-1). Region-level (zwei Worker
disjunkte Regionen DERSELBEN Datei) braucht den Slice-Plan + den Region-Lock
(stage_resource_registry.acquire_region) zur LAUF-Zeit — der Scheduler ANDet beide Achsen.
Stufe-2 (Small-World, semantischer Konflikt trotz Datei-Disjunktheit) = BL-297-C2 (gated, BL-361).

Konsument (Wellen-Scheduler, BL-230 Phase C): bei fehlendem Feld konservativ seriell (fail-safe).
"""
import itertools
from collections import Counter
from typing import Dict, List, Tuple, Optional, Any

FORMAT_VERSION = "1.0"


def conflict_matrix(sub_batches: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Pairwise ziel_dateien-Konflikt (AK-1/AK-2): {(id_a,id_b): {status, files[]}}.

    status='overlap' wenn die Paare GEMEINSAME ziel_dateien haben (die genannt werden —
    erklaerbar), sonst 'disjoint'. Deterministisch (sortierte Datei-Liste)."""
    m: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for a, b in itertools.combinations(sub_batches, 2):
        shared = sorted(set(a.get("ziel_dateien", [])) & set(b.get("ziel_dateien", [])))
        m[(a["id"], b["id"])] = {"status": "overlap" if shared else "disjoint", "files": shared}
    return m


def _file_islands(sub_batches: List[Dict[str, Any]]) -> List[int]:
    """Connected components of sub-batches that share >=1 ziel_datei (Union-Find).
    Returns component sizes desc. 1 Insel = alles gekoppelt; k Inseln = k parallel-Spuren."""
    n = len(sub_batches)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    fmap: Dict[str, List[int]] = {}
    for i, b in enumerate(sub_batches):
        for f in b.get("ziel_dateien", []):
            fmap.setdefault(f, []).append(i)
    for idxs in fmap.values():
        for j in range(1, len(idxs)):
            union(idxs[0], idxs[j])
    comp = Counter(find(i) for i in range(n))
    return sorted(comp.values(), reverse=True)


def suitability_for_batches(sub_batches: List[Dict[str, Any]], n_cap: int = 4) -> Dict[str, Any]:
    """Aggregat-Parallel-Suitability fuer eine Sub-Batch-Menge (Plan-Zeit, file-level).

    Konflikt-Insel-Zahl = Plan-Zeit-Parallelitaets-Mass; build_share (AK-6) daempft
    review-dominierte Mengen (Struktur-Cuttability != Wanduhr-ROI). recommended_N ist
    n_cap-begrenzt (modest; mehr Spuren brauchen Region-/fine-cut = BL-361). Deterministisch.
    """
    n = len(sub_batches)
    matrix = conflict_matrix(sub_batches)
    bt = sum(1 for b in sub_batches if b.get("change_type") in ("add", "assert"))
    rt = sum(1 for b in sub_batches if b.get("change_type") == "modify")
    build_share = (bt / (bt + rt)) if (bt + rt) else None
    bs_round = round(build_share, 3) if build_share is not None else None

    if n <= 1:
        return {"story_type": "trivial", "conflict_islands": n, "largest_island": n,
                "build_share": bs_round, "recommended_N": 1, "suitable": False,
                "reason": "<=1 Sub-Batch — nichts zu parallelisieren", "matrix": matrix}

    isl = _file_islands(sub_batches)
    n_islands = len(isl)
    largest = isl[0]

    if n_islands == 1:
        story, rec_n = "coupled", 1
        reason = "alle Sub-Batches teilen Dateien (1 Konflikt-Insel) -> seriell"
    else:
        rec_n = min(n_islands, n_cap)
        if build_share is not None and build_share < 0.40:
            rec_n = min(rec_n, max(n_islands // 2, 1))
            story = "review-dominiert"
            reason = (f"{n_islands} Konflikt-Inseln ABER build_share={build_share:.0%} niedrig "
                      f"(review-dominiert) -> N gedaempft auf {rec_n} (Cuttability != Wanduhr-ROI)")
        else:
            story = "build-parallel"
            bs = f", build_share={build_share:.0%}" if build_share is not None else ""
            reason = f"{n_islands} disjunkte Konflikt-Inseln{bs} -> N={rec_n}"

    return {"story_type": story, "conflict_islands": n_islands, "largest_island": largest,
            "build_share": bs_round, "recommended_N": rec_n, "suitable": rec_n >= 2,
            "reason": reason, "matrix": matrix}
