#!/usr/bin/env python3
"""kazman_screening_metrics.py — BL-381 batch_2 (AK-1): read-only SCREENING-grade
Decoupling Level (DL) + Propagation Cost (PC) aus VORHANDENER Struktur.

Kazman/MacCormack (CMU/SEI-2020-TR-006, "Architecture Quality Metrics"):
  - Propagation Cost (PC): der Anteil des Systems, den eine Aenderung an einer
    durchschnittlichen Komponente erreichen kann — operationalisiert als Dichte der
    transitiven Erreichbarkeits-(Visibility-)Matrix. Hohe PC = enges, propagierendes
    Design; niedrige PC = lokale Aenderungen.
  - Decoupling Level (DL): der Grad, zu dem ein System in unabhaengig aenderbare Teile
    zerfaellt. Wenige/flache Abhaengigkeiten => hoch entkoppelt; dichte/tiefe => niedrig.

SCREENING-GRADE (Spec Sec 0 — DSM-FORK ADJUDIZIERT): DL/PC werden aus einer BEREITS
VORHANDENEN Abhaengigkeits-/Adjazenz-Struktur abgeleitet — NICHT aus einer neu gebauten
file-level Design-Structure-Matrix (das waere Over-Engineering fuer eine Screening-Schicht,
AK-5: der Score ist Screening, kein Urteil). Es gibt hier KEINEN Import-/AST-Parser, KEINE
statische Import-/Aufruf-Analyse. Die Adjazenz kommt aus zwei vorhandenen Quellen:

  1. `_IDF_berater_dependencyAnalyzer` (DAG): `nodes[]`/`edges[]` als
     {knoten: [nachbarn]}-Map (PL-Item-/Schichten-Topologie, design-time verfuegbar).
  2. `cochange_coupling.cochange_pairs` (Co-Change-DSM-PROXY): symmetrische Datei-Paare
     -> ungerichtete Adjazenz via `adjacency_from_pairs` (empirische Kopplungs-Naehe).

Zusaetzlich liefert `instability` das per-Komponente Martin-Ca/Ce-Vorzeichen
(I = Ce/(Ca+Ce), Afferent/Efferent Coupling) als screening-grade Kopplungs-Indikator.

Alle Skalar-Werte sind auf 0-100 normalisiert (K-Skala-Constraint, W-CON-1). Die
Schwellen-DEFINITION (was rot/gelb/gruen) ist NICHT BL-381-Scope (an BL-311/312 delegiert).

DL/PC bleiben strukturell GETRENNTE Achsen vom historischen Co-Commit-Signal (W-AK1-3):
DL/PC sehen Design-Komplexitaet (auch ohne Historie), Co-Commit sieht nicht-strukturelle
Schuld. Dieses Modul rechnet NUR die strukturellen Achsen.

STRIKT READ-ONLY: reine, deterministische Funktionen auf uebergebenen Daten. Kein
git/subprocess, kein File-Write, kein State-Mutieren (analog cochange_coupling.py /
kazman_kscore_axes.py). Die Datenquelle (DAG bzw. cochange_pairs) wird UEBERGEBEN.

SEAM: teilt die Co-Change-Datenquelle mit kazman_kscore_axes (AK-2) und BL-342/BL-415 —
EIN Producer (`cochange_coupling.py`), mehrere Konsumenten. Kein zweites Co-Change-Skript.
"""
from __future__ import annotations

from collections import Counter, deque

# Benannte Achsen-Schluessel (DISTINKT vom historischen co_commit_coupling, W-AK1-3).
DECOUPLING_LEVEL_NAME = "decoupling_level"
PROPAGATION_COST_NAME = "propagation_cost"


def _normalize_adjacency(adjacency: dict) -> dict:
    """Bringt eine Adjazenz-Map in eine vollstaendige {knoten: set(nachbarn)}-Form.

    Robustheit fuer DAG-`edges[]`: ein Kanten-Ziel, das selbst kein eigener Schluessel
    ist (z.B. ein nicht separat gelistetes Blatt), wird als Knoten aufgenommen. Selbst-
    Schleifen (knoten -> knoten) werden verworfen (kein Propagations-Beitrag ueber sich
    selbst). Reine Lese-Transformation — die Eingabe wird nicht mutiert.
    """
    out: dict = {}
    for node, neighbors in adjacency.items():
        out.setdefault(node, set())
        for nb in neighbors or ():
            if nb == node:
                continue  # Selbst-Schleife: kein transitiver Beitrag
            out[node].add(nb)
            out.setdefault(nb, set())  # dangling target wird eigener Knoten
    return out


def _reachable_count(adj: dict, start) -> int:
    """Anzahl der vom `start` aus transitiv erreichbaren ANDEREN Knoten (BFS; ohne start
    selbst). Operationalisiert eine Zeile der off-diagonalen Visibility-Matrix."""
    seen = {start}
    q: deque = deque()
    for nb in adj.get(start, ()):
        if nb not in seen:
            seen.add(nb)
            q.append(nb)
    while q:
        cur = q.popleft()
        for nb in adj.get(cur, ()):
            if nb not in seen:
                seen.add(nb)
                q.append(nb)
    return len(seen) - 1  # start selbst nicht mitzaehlen


def propagation_cost(adjacency: dict, scale: float = 100.0) -> float:
    """Screening-grade Propagation Cost (0..scale, default 0-100).

    PC = (Summe ueber alle Knoten der transitiv erreichbaren ANDEREN Knoten) /
         (N * (N-1))  — die Dichte der off-diagonalen Visibility-Matrix
    (MacCormack/Kazman). Anteil des Systems, den eine durchschnittliche Aenderung
    erreichen kann.

    Grenzwerte:
      - leerer / 1-Knoten-Graph: 0.0 (nichts zu propagieren).
      - voll entkoppelt (keine Kante): 0.0.
      - voll vermascht (jeder erreicht jeden): scale.

    Monoton in Kanten (mehr/transitiv tiefere Kanten => groessere oder gleiche Reach-Summe).
    Deterministisch; reine Funktion (mutiert nichts).
    """
    adj = _normalize_adjacency(adjacency)
    n = len(adj)
    if n < 2:
        return 0.0
    total_reach = sum(_reachable_count(adj, node) for node in adj)
    denom = n * (n - 1)
    return round(total_reach / denom * scale, 1)


def decoupling_level(adjacency: dict, scale: float = 100.0) -> float:
    """Screening-grade Decoupling Level (0..scale, default 0-100).

    DL ist das screening-grade KOMPLEMENT der Propagation Cost: ein System, dessen
    Aenderungen weit propagieren (hohe PC), ist gering entkoppelt; ein System mit nur
    lokalen Aenderungen (niedrige PC) ist hoch entkoppelt. Auf derselben Adjazenz gilt
    DL = scale - PC. Das ist die methodisch sparsamste DL-Approximation fuer einen
    Screening-Layer (Spec Sec 0): kein eigener DSM-Cluster-Algorithmus, sondern die
    Entkopplungs-Lesart derselben Erreichbarkeits-Dichte.

    Grenzwerte:
      - leerer / voll entkoppelter Graph: scale (maximal entkoppelt).
      - voll vermascht: 0.0 (minimal entkoppelt).

    Monoton FALLEND in Kanten (mehr Kopplung => weniger Entkopplung).
    """
    return round(scale - propagation_cost(adjacency, scale=scale), 1)


def instability(adjacency: dict) -> dict:
    """Martin-Instabilitaet je Knoten: I = Ce / (Ca + Ce), im Bereich [0,1].

    Screening-grade Kopplungs-VORZEICHEN (kein 0-100-Score, sondern die klassische
    Martin-Metrik als Indikator):
      - Ce (efferent, out-degree): auf wie viele andere zeigt der Knoten (Abhaengigkeiten).
      - Ca (afferent, in-degree): wie viele andere zeigen auf ihn (Verantwortung).
      - I = 1 reiner Source (nur efferent: maximal instabil); I = 0 reiner Sink
        (nur afferent: maximal stabil).
      - isolierter Knoten (Ca = Ce = 0): I = 0.0 definiert (keine Division durch 0;
        Martin-Konvention: ohne ausgehende Abhaengigkeit ist der Knoten nicht instabil).

    Gerichtet ausgewertet (Selbst-Schleifen verworfen). Reine Funktion.
    """
    adj = _normalize_adjacency(adjacency)
    ce: Counter = Counter()  # efferent / out-degree
    ca: Counter = Counter()  # afferent / in-degree
    for node, neighbors in adj.items():
        ce[node] += len(neighbors)
        for nb in neighbors:
            ca[nb] += 1
    out: dict = {}
    for node in adj:
        e = ce[node]
        a = ca[node]
        out[node] = 0.0 if (e + a) == 0 else round(e / (a + e), 4)
    return out


def adjacency_from_pairs(pairs: Counter | dict) -> dict:
    """Baut eine UNGERICHTETE Adjazenz aus `cochange_coupling.cochange_pairs` (DSM-PROXY).

    Co-Change ist symmetrisch: ein Paar (a, b) bedeutet a~b UND b~a. Die Paar-COUNTS
    (Kopplungs-Staerke) werden fuer die screening-grade Erreichbarkeit NICHT gewichtet —
    es zaehlt die Existenz der Kopplungs-Kante (eine Aenderung kann propagieren, sobald
    eine Co-Change-Relation besteht). Das haelt PC/DL als reine Topologie-Masse robust
    gegen Count-Rauschen (W-AK1-1: PL-/Co-Change-Ebene ist grob).

    -> {knoten: [nachbarn]} (Listen, deterministisch sortiert fuer reproduzierbaren Output).
    Damit speist der cochange_coupling-Output direkt propagation_cost/decoupling_level.
    """
    adj: dict = {}
    for (a, b) in pairs:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return {node: sorted(neighbors) for node, neighbors in adj.items()}


def screening_metrics(adjacency: dict, scale: float = 100.0) -> dict:
    """Buendelt die beiden screening-grade Achsen als getrennte benannte 0-100-Felder —
    der Konsum-Vertrag fuer den K-Score-Produzenten (DL/PC docken als per-Batch-Felder an,
    AK-3). DL/PC bleiben GETRENNT (kein Rueckkollaps in einen Skalar, W-AK1-3 / W-DOM-1).

    -> {"decoupling_level": 0-100, "propagation_cost": 0-100}
    """
    return {
        DECOUPLING_LEVEL_NAME: decoupling_level(adjacency, scale=scale),
        PROPAGATION_COST_NAME: propagation_cost(adjacency, scale=scale),
    }


__all__ = [
    "DECOUPLING_LEVEL_NAME",
    "PROPAGATION_COST_NAME",
    "propagation_cost",
    "decoupling_level",
    "instability",
    "adjacency_from_pairs",
    "screening_metrics",
]
