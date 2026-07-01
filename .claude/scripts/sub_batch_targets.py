"""sub_batch_targets.py — BL-342 Phase-1a Naht: ziel_dateien-Surfacing (Plan-Zeit).

Step 1 der IDF-Phase-7.8-Verdrahtung. Leitet aus dem REALEN dependencyAnalyzer-Output
die `ziel_dateien` pro Sub-Batch ab — der Plan-Zeit-Input fuer
`parallel_suitability.suitability_for_batches`.

QUELLE (Szenario-verifiziert gegen echtes 486-Manifest, NICHT geglaubt):
  - `batch_items_per_batch`  = DF_BATCH_STATE  : {batch_id: [item_id, ...]}   (Phase 7 batchPlan)
  - `file_index`             = BERATER_OUTPUTS.dependencyAnalyzer.file_index :
        INVERTIERTER Index {datei_pfad: [item_id, ...]} (Datei -> Items die sie beruehren).
        Das ist die KANONISCHE, single-writer per-Item-Pfadquelle (dependencyAnalyzer
        baut darauf seine soft_file_proximity-Edges). `dateien_geplant` existiert im
        echten Manifest NICHT (0 Treffer); `gatherSignals.file_refs` (PT-Harvest) hat
        andere Item-IDs und ist NICHT der Batch-Plan-Input.

ANSATZ: pro Sub-Batch die Menge der Dateien, deren file_index-Item-Liste die Batch-Items
schneidet (= file_index invertieren, auf die Batch-Items skopiert), dedup + sortiert.
Deterministisch + erklaerbar (welche Datei kommt von welchem Item-Overlap). Best-effort:
Batch-Items ohne file_index-Eintrag tragen nichts bei (kein Crash, kein Fabrizieren).

change_type: hat im aktuellen Pipeline-Output KEINE etablierte Quelle (dependencyAnalyzer/
plAggregation liefern KEIN add/assert/modify; batch_mode_hints=M2/M3 ist Mode, nicht
change_type). Darum DEFAULT None (kein Fabrizieren) -> der Producer laesst build_share=None
(AK-6-Daempfung inert bis eine echte change_type-Quelle existiert; Folge-BL). Ein optionaler
`change_type_map` erlaubt spaeter eine echte Quelle ohne API-Bruch.
"""
from typing import Dict, List, Optional, Any


def ziel_dateien_per_batch(
    batch_items_per_batch: Optional[Dict[str, Any]],
    file_index: Optional[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """{batch_id: sorted(set(dateien deren file_index-Items die Batch-Items schneiden))}.

    Invertiert den file_index (datei -> items) auf die Items je Sub-Batch. Deterministisch,
    dedup + sortiert. None-tolerant (None/leer -> {} bzw. [])."""
    out: Dict[str, List[str]] = {}
    fidx = file_index or {}
    for batch_id, items in (batch_items_per_batch or {}).items():
        item_set = set(items or [])
        files = sorted(
            f for f, its in fidx.items() if item_set & set(its or [])
        )
        out[batch_id] = files
    return out


def build_sub_batches(
    batch_items_per_batch: Optional[Dict[str, Any]],
    file_index: Optional[Dict[str, Any]],
    change_type_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Producer-ready Liste [{id, ziel_dateien, change_type}] fuer suitability_for_batches.

    Reihenfolge = Iterations-Reihenfolge von batch_items_per_batch (deterministisch in
    Py3.7+ Insert-Order). change_type aus change_type_map oder None (kein Fabrizieren)."""
    zdpb = ziel_dateien_per_batch(batch_items_per_batch, file_index)
    ctm = change_type_map or {}
    return [
        {"id": bid, "ziel_dateien": zdpb.get(bid, []), "change_type": ctm.get(bid)}
        for bid in (batch_items_per_batch or {})
    ]
