#!/usr/bin/env python3
"""pl_effort_split.py — BL-304 AK-1/AK-2 (Heterogenitaets-Split nach Aufwands-Klasse).

Rein + deterministisch + idempotent + None-tolerant: partitioniert eine PL-Item-Menge
nach k_score in einen trivial-Bucket (k<threshold) und einen rigorous-Bucket (k>=threshold).

PROBLEM (der KERN von BL-304, Live-Fall DCSRE-486 batch_PL23):
`_SDF_berater_modusEntscheidung` M1-MULTI-Lane (Z428-443) verlangt `k_score_max < 15`.
EIN schweres Item (k>=15) im Batch -> k_max>=15 -> M1-MULTI faellt aus -> der GANZE
heterogene Batch wird M2, auch wenn 10/11 Items trivial sind. BL-279 splittet erst bei
k_max>=80 — die Luecke [15,80) hat KEINEN Split, also wird die triviale Mehrheit vom
schwersten Item nach M2 mitgerissen (batch_PL23: k_avg=12.5, 1x M-sized T2076 -> ganz M2).

FIX-RICHTUNG: Der Split passiert UPSTREAM in IDF (preventiv, wo per-Item-k lebt), NICHT
in modusEntscheidung. Der Modus-Gate bleibt BYTE-IDENTISCH (INV-MODUS-1 / INV-VEHIKEL-2:
modusEntscheidung ist RED-Zone). Wenn homogene Batches ankommen, feuert der UNVERAENDERTE
k_max<15-Gate korrekt fuer die triviale Mehrheit.

threshold=15 ist KEIN neuer Magic-Number — es ist EXAKT die existierende M1-MULTI-Decke
(`_SDF_berater_modusEntscheidung` Z429: `k_score_max < 15`). Die Grenze ist STRIKT <,
darum gehoert k==15 in den rigorous-Bucket (>=threshold).

Kanonischer Effort-Split — zitiert von den Batch-Formations-Beratern
(_IDF_berater_clustering Phase 5 als Homogenisierungs-Dimension, _IDF_berater_batchPlanner
Phase 7 respektiert die Sub-Batches) als gemeinsame, einheitliche Naht (EINE Wahrheit,
wie pl_defer_filter fuer AK-3). Komponiert MIT dem AK-3-Defer-Filter: der Effort-Split
laeuft auf den schon defer-gefilterten aktiven Items.

None-k_score-Behandlung (Design-Entscheidung):
  Items OHNE k_score (None / Feld fehlt) -> KONSERVATIV in den rigorous-Bucket.
  Begruendung: k_score unbekannt = "Aufwand NICHT als trivial bewiesen". Sie als trivial
  zu behandeln waere Ueber-Optimismus (ein schweres Item rutscht faelschlich in M1-Skelett).
  is_heterogeneous zaehlt None NICHT als triviale Teilmenge (None ist nicht k<threshold)
  und None inflationiert k_max NICHT -> ein Batch nur aus None-Items ist homogen-rigorous.

Kontrakt:
- split_by_effort_class(items, threshold=15) -> {"trivial": [...], "rigorous": [...]}
- is_heterogeneous(items, threshold=15)       -> bool

WICHTIG: reine Partition — Items werden NICHT mutiert, NICHT kopiert. Die Bucket-Listen
enthalten dieselben Objekte (Identitaet erhalten), nur neu verteilt + reihenfolgestabil.
"""

# Die Default-Decke = die EXISTIERENDE M1-MULTI-Grenze (_SDF_berater_modusEntscheidung
# Z429: `k_score_max < 15`). KEIN neuer/abweichender Wert.
DEFAULT_EFFORT_THRESHOLD = 15


def _k_score(item):
    """Liest k_score defensiv aus einem Item-dict. None gdw. fehlend ODER explizit None.

    Nicht-numerische k_score-Werte (Fehl-Eingabe) -> None (konservativ -> rigorous),
    statt einen TypeError im Vergleich auszuloesen.
    """
    if not isinstance(item, dict):
        return None
    k = item.get("k_score")
    if isinstance(k, bool):  # bool ist Subtyp von int — als kein-k_score behandeln
        return None
    if isinstance(k, (int, float)):
        return k
    return None


def split_by_effort_class(items, threshold=DEFAULT_EFFORT_THRESHOLD):
    """Partitioniert Items nach k_score in trivial- (k<threshold) + rigorous-Bucket (k>=threshold).

    - Items ohne k_score (None / Feld fehlt) -> rigorous (konservativ, s. Modul-Docstring).
    - None-Eintraege in der Liste werden defensiv verworfen.
    - Reihenfolge-stabil innerhalb jedes Buckets (Partition, kein Sort).
    - Idempotent: split(split(x)["trivial"])["trivial"] == split(x)["trivial"].
    - Items werden NICHT mutiert/kopiert (Identitaet erhalten).

    Returns: {"trivial": [...], "rigorous": [...]}
    """
    result = {"trivial": [], "rigorous": []}
    if not items:
        return result
    for item in items:
        if item is None:
            continue
        k = _k_score(item)
        # k is None -> konservativ rigorous (Aufwand nicht als trivial bewiesen).
        if k is not None and k < threshold:
            result["trivial"].append(item)
        else:
            result["rigorous"].append(item)
    return result


def is_heterogeneous(items, threshold=DEFAULT_EFFORT_THRESHOLD):
    """True gdw. der Batch effort-heterogen ist: ein schweres Item reisst Triviale mit.

    Heterogen == k_max>=threshold UND es existiert ein Item mit k<threshold (eine triviale
    Teilmenge, die ohne Split vom schwersten Item nach M2 mitgerissen wuerde — genau die
    [15,80)-Luecke). Homogene Batches (alle <threshold ODER alle >=threshold/None) -> False
    (kein unnoetiger Split).

    None-k_score-Items zaehlen NICHT als triviale Teilmenge und inflationieren k_max NICHT.
    """
    if not items:
        return False
    ks = [_k_score(i) for i in items if i is not None]
    known = [k for k in ks if k is not None]
    if not known:
        return False  # nur None-Items: homogen-rigorous, nichts wird mitgerissen
    has_heavy = max(known) >= threshold
    has_trivial = any(k < threshold for k in known)
    return has_heavy and has_trivial
