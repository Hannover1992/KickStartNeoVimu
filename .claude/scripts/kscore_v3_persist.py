"""kscore_v3_persist.py — BL-311 batch_2: Stage 4 Schema-3.0-Dual-Write.

Serialisiert die Stage-3-Scoring- + Stage-2-Topologie-Ergebnisse zu K-SCORE.md
im Schema 3.0 = Schema 2.0 Felder + NEU overlap_edges, contention_per_item, k_min.

EINGABE (immer Parameter — nie aus git/FS gelesen):
  - scored_items / aggregate_scores: aus Stage 3 (kscore_v3_scoring).
  - topology_summary: aus Stage 2 (kscore_v3_topology) — liefert overlap_edges +
    contention_per_item.
  - schema2_compat_fields: bestehende Schema-2.0-Frontmatter (Dual-Write-Quelle).
  - bl_id / batch_id / output_path: Identitaet + Ziel-Pfad.

AUSGABE: build_schema_3_document -> Dokument-String (File-IO-entkoppelt, testbar);
  write_schema_3 -> schreibt diesen String nach output_path (einziger Seiteneffekt).

STAGE: Stage 4 (Persist) — Ende der K-Score-v3-Pipeline.

INV / Dual-Write (BL-266-Lehre): alle Schema-2.0-Felder bleiben erhalten, neue
  3.0-Felder werden ausschliesslich additiv angefuegt (Kanarienvogel K-6).

AK-15 Solo-Pfad-Weiche: should_use_v3_full entscheidet ob v3-Full-Orchestrate
  oder Solo-Pfad-2.0 (N-Schwelle + k-Verdacht-Flag).
"""
from __future__ import annotations

import json
from typing import Optional


def should_use_v3_full(
    item_count: int,
    k_verdacht: bool = False,
    n_schwelle: int = 3,
) -> bool:
    """Weiche Solo-Pfad vs. v3-Full-Orchestrate (AK-15, W-PRIN-5).

    v3-Full wenn: item_count >= n_schwelle ODER k_verdacht==True.
    Solo-Pfad (Schema 2.0) wenn: item_count < n_schwelle AND k_verdacht==False.
    """
    return k_verdacht or item_count >= n_schwelle


def build_schema_3_document(
    scored_items: list[dict],
    aggregate_scores: dict,
    topology_summary: dict,
    schema2_compat_fields: dict,
    bl_id: str,
    batch_id: str,
    session_params: Optional[dict] = None,
) -> str:
    """Baut den Schema-3.0-Dokument-String (YAML-Frontmatter + Markdown-Body).

    Testbar ohne File-IO (String-Resultat direkt assertierbar).
    write_schema_3 ruft build_schema_3_document + schreibt die Datei.

    Dual-Write-Invariante (BL-266): alle schema2_compat_fields passieren
    unveraendert in den Output.
    """
    # --- YAML-Frontmatter aufbauen ---
    lines = ["---"]

    # Schema-2.0-Compat-Felder zuerst (Dual-Write-Invariante BL-266) — unveraendert.
    for key, value in schema2_compat_fields.items():
        lines.append(f"{key}: {value}")

    # Schema-3.0-Felder additiv
    lines.append("schema_version_v3: '3.0'")
    lines.append(f"bl_id: {bl_id}")
    lines.append(f"batch_id: {batch_id}")

    # k_min (load-bearing BL-304)
    k_min = aggregate_scores.get("k_min", 0.0)
    lines.append(f"k_min: {k_min}")

    # overlap_edges (aus topology_summary)
    overlap_graph = topology_summary.get("overlap_graph", {})
    overlap_edges = overlap_graph.get("edges", [])
    overlap_edges_json = json.dumps(overlap_edges, ensure_ascii=False)
    lines.append(f"overlap_edges: {overlap_edges_json}")

    # contention_per_item (aus topology_summary)
    contention = topology_summary.get("contention", {})
    contention_json = json.dumps(contention, ensure_ascii=False)
    lines.append(f"contention_per_item: {contention_json}")

    lines.append("---")
    lines.append("")

    # --- Markdown-Body ---
    lines.append(f"# K-SCORE Schema 3.0 — {bl_id} / {batch_id}")
    lines.append("")
    lines.append("## Aggregate Scores")
    lines.append("")
    lines.append(f"- k_max: {aggregate_scores.get('k_max', 0.0)}")
    lines.append(f"- k_avg: {aggregate_scores.get('k_avg', 0.0)}")
    lines.append(f"- k_min: {k_min}")
    lines.append(f"- item_count: {aggregate_scores.get('item_count', 0)}")
    lines.append("")

    if scored_items:
        lines.append("## Per-Item Scores")
        lines.append("")
        for item in scored_items:
            item_id = item.get("item_id", "?")
            k_final = item.get("k_final", 0.0)
            lines.append(f"- {item_id}: k_final={k_final}")
        lines.append("")

    lines.append("## Topology")
    lines.append("")
    lines.append(f"Overlap edges: {len(overlap_edges)}")
    lines.append("")

    return "\n".join(lines)


def write_schema_3(
    output_path: str,
    scored_items: list[dict],
    aggregate_scores: dict,
    topology_summary: dict,
    schema2_compat_fields: dict,
    bl_id: str,
    batch_id: str,
    session_params: Optional[dict] = None,
) -> None:
    """Schreibt K-SCORE.md Schema 3.0 als Dual-Felder-Datei.

    Schema-3.0-Felder (additiv zu 2.0):
      - overlap_edges: list[dict]
      - contention_per_item: dict[str,float]
      - k_min: float

    Dual-Write-Invariante (BL-266): alle schema2_compat_fields passieren
    unveraendert in den Output.
    """
    doc_str = build_schema_3_document(
        scored_items=scored_items,
        aggregate_scores=aggregate_scores,
        topology_summary=topology_summary,
        schema2_compat_fields=schema2_compat_fields,
        bl_id=bl_id,
        batch_id=batch_id,
        session_params=session_params,
    )
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(doc_str)
