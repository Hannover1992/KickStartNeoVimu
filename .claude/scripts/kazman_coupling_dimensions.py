#!/usr/bin/env python3
"""kazman_coupling_dimensions.py — BL-381 batch_3 (AK-6 code-Teil): mehrdimensionale Kopplung
soweit aus vorhandenem Substrat ableitbar, als GETRENNTE benannte Felder — read-only.

PROBLEM (W-AK6-2 / W-DOM-1 auf Kopplungs-Ebene): die Kopplung wird heute zu EINEM Skalar
kollabiert (`kopplung_roh` -> `k_kopplung`, _K_score.md:611). Ein einziger Skalar verschmilzt
strukturell verschiedene Kopplungs-Arten und verliert die Aktionierbarkeit ("welche ART von
Kopplung?"). AK-6 fuehrt die Dimensionen GETRENNT — soweit aus vorhandenem Substrat ableitbar.

ABLEITBARE DIMENSIONEN (Kazman, CMU/SEI-2020-TR-006):
  - structural (syntactic): Martin Ca/Ce -> Instabilitaet I = Ce/(Ca+Ce) je Komponente.
    Producer: kazman_screening_metrics.instability (batch_2). KEIN eigener Ca/Ce-Zaehler hier.
  - temporal + resource: Co-Commit-Coupling (Kazman: co-commit "reveals control, data, timing,
    and resource-based coupling"). Producer: kazman_kscore_axes.co_commit_axis (batch_1), 0-100.

NICHT batch_3 (dokumentierte Luecke, batch_4 / markdown): echte data-semantic + behavioral
Kopplung — ohne Laufzeit-Trace nicht ableitbar. Dieses Modul ERZWINGT sie NICHT als Pflichtfelder
und kollabiert die ableitbaren Dims NICHT in einen Sammel-Skalar (W-AK6-2-Constraint).

WIEDERVERWENDUNG (EIN Producer je Achse, kein Doppel): die Dims kommen 1:1 aus den batch_1/
batch_2-Producern. Dieses Modul ist reine ORCHESTRIERUNG (welche Substrat-Funktion -> welche
benannte Dimension), KEIN neuer Mess-Algorithmus.

GRANULARITAET (AK-3 / W-DOM-2): die Eingaben (DAG + file_degree) sind PRO SUB-BATCH zu uebergeben;
der Output ist ein per-Batch-Dict. KEIN globaler Repo-weiter Kopplungs-Skalar.

STRIKT READ-ONLY: reine Funktionen auf uebergebenen Daten. Kein git/subprocess, kein File-Write,
kein State-Mutieren (analog cochange_coupling.py / kazman_kscore_axes.py / kazman_screening_metrics.py).
"""
from __future__ import annotations

from kazman_kscore_axes import co_commit_axis
from kazman_screening_metrics import instability

# Benannte Dimensions-Schluessel — GETRENNT gefuehrt (kein Rueckkollaps, W-AK6-2). Diese Namen
# sind der Konsum-Vertrag fuer die per-Batch-Felder (metric_per_batch, AK-3).
COUPLING_STRUCTURAL_NAME = "coupling_structural"
COUPLING_TEMPORAL_RESOURCE_NAME = "coupling_temporal_resource"


def coupling_dimensions(adjacency: dict, file_degree: dict | None = None) -> dict:
    """Fuehrt die ableitbaren Kopplungs-Dimensionen als GETRENNTE benannte Felder zusammen —
    OHNE Rueckkollaps in einen einzigen Kopplungs-Skalar (W-AK6-2).

    Args:
      adjacency:   gerichtete {knoten: [nachbarn]}-Map (dependencyAnalyzer-DAG eines Sub-Batches)
                   -> structural-Dimension (Martin-Instabilitaet je Knoten).
      file_degree: {datei: co_change_grad}-Map (cochange_coupling.file_degree eines Sub-Batches)
                   -> temporal/resource-Dimension (co_commit_axis 0-100). None/{} -> {}.

    Returns:
      {
        "coupling_structural":        {knoten: instabilitaet 0..1},   # syntactic via Ca/Ce
        "coupling_temporal_resource": {datei: 0..100},                # co-commit (timing/resource)
      }
      Beide Dimensionen sind per-Sub-Batch (scope-relativ, W-DOM-2) und bleiben DISTINKT.
      data-semantic + behavioral sind bewusst NICHT enthalten (Luecke, batch_4).
    """
    return {
        COUPLING_STRUCTURAL_NAME: instability(adjacency),
        COUPLING_TEMPORAL_RESOURCE_NAME: co_commit_axis(file_degree or {}),
    }


__all__ = [
    "COUPLING_STRUCTURAL_NAME",
    "COUPLING_TEMPORAL_RESOURCE_NAME",
    "coupling_dimensions",
]
