#!/usr/bin/env python3
"""Tests fuer pl_effort_split.py (BL-304 AK-1/AK-2/AK-4 — Heterogenitaets-Split nach Aufwands-Klasse).

TDD Stage 1 (Atomic), Modus M3. Spiegel-Stil von test_pl_defer_filter.py (AK-3) —
standalone __main__-Runner + pytest-kompatibel.

PROBLEM (Live-Fall DCSRE-486 batch_PL23, der KERN von BL-304):
`_SDF_berater_modusEntscheidung` M1-MULTI-Lane (Z428-443) verlangt `k_score_max < 15`.
EIN schweres Item (k>=15) im Batch -> k_max>=15 -> M1-MULTI faellt aus -> der GANZE
heterogene Batch wird M2, auch wenn 10/11 Items trivial sind. BL-279 splittet erst bei
k_max>=80. Die Luecke [15,80) hat KEINEN Split -> triviale Mehrheit wird vom schwersten
Item nach M2 mitgerissen. batch_PL23: k_avg=12.5, 1x M-sized T2076 (k>=15) -> ganzer M2.

FIX-RICHTUNG (Lead-Vorgabe): Split UPSTREAM in IDF (preventiv, wo per-Item-k lebt),
NICHT in modusEntscheidung. Homogene Batches ankommen lassen -> der UNVERAENDERTE
k_max<15-Gate feuert dann korrekt fuer die triviale Mehrheit. threshold=15 = die
EXISTIERENDE M1-MULTI-Decke (KEIN neuer Magic-Number).

KONTRAKT (rein, deterministisch, idempotent, None-tolerant — KEIN State, KEIN IO):
- split_by_effort_class(items, threshold=15) -> {"trivial": [...], "rigorous": [...]}
    partitioniert nach k_score: trivial-Bucket (k<threshold), rigorous-Bucket (k>=threshold).
- is_heterogeneous(items, threshold=15) -> bool
    True gdw. k_max>=threshold UND ES GIBT ein Item mit k<threshold (eine triviale
    Teilmenge existiert, die vom Schweren mitgerissen wuerde).

None-k_score-Behandlung (Design-Entscheidung, dokumentiert):
  Items OHNE k_score (k_score is None / fehlt) -> KONSERVATIV in den rigorous-Bucket.
  Begruendung: k_score unbekannt = "Aufwand nicht als trivial bewiesen". Sie als trivial
  zu behandeln waere das Ueber-Optimismus-Risiko (ein schweres Item rutscht faelschlich
  in M1-Skelett). is_heterogeneous zaehlt None NICHT als "trivial vorhanden" (None ist
  nicht k<threshold) und NICHT als "k_max>=threshold" (None inflationiert k_max nicht).
  -> ein Batch NUR aus None-Items ist homogen-rigorous (kein Split).

RED-Beweis: pl_effort_split.py existiert NOCH NICHT -> ImportError -> die Referenzen
bleiben None -> jeder Test failt loud. Das IST RED.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Import-tolerant: solange pl_effort_split.py fehlt (RED-Phase) bleiben die
# Referenzen None und jeder Test failt mit klarer Meldung statt CollectError.
try:
    from pl_effort_split import split_by_effort_class as _SPLIT
    from pl_effort_split import is_heterogeneous as _IS_HETERO
    _IMPORT_ERR = None
except ImportError as e:  # RED: Modul existiert noch nicht
    _SPLIT = None
    _IS_HETERO = None
    _IMPORT_ERR = e


def _require_import():
    assert _SPLIT is not None and _IS_HETERO is not None, (
        f"pl_effort_split.py nicht importierbar (RED erwartet vor GREEN): {_IMPORT_ERR}"
    )


def _item(item_id, k):
    """Mini-Helfer: ein PL-Item-dict mit k_score (k=None -> Feld vorhanden aber None)."""
    return {"id": item_id, "k_score": k}


def _kmax(items):
    ks = [i.get("k_score") for i in items if i.get("k_score") is not None]
    return max(ks) if ks else None


# --- T1: KERN-FALL (DCSRE-486 T2076) — 10 trivial + 1 heavy -> Split ----------
def test_core_t2076_split_trivial_from_heavy():
    _require_import()
    # 10 Items k<15 + 1 Item k=20 (das M-sized T2076). batch_PL23-Signatur.
    items = [_item(f"T207{i}", 10) for i in range(10)] + [_item("T2076", 20)]
    buckets = _SPLIT(items)
    assert len(buckets["trivial"]) == 10, (
        f"10 triviale Items erwartet im trivial-Bucket, waren {len(buckets['trivial'])}"
    )
    assert len(buckets["rigorous"]) == 1, (
        f"1 heavy Item erwartet im rigorous-Bucket, waren {len(buckets['rigorous'])}"
    )
    # Das ENTSCHEIDENDE: der trivial-Bucket hat k_max<15 -> M1-MULTI-faehig.
    assert _kmax(buckets["trivial"]) < 15, (
        "trivial-Bucket MUSS k_max<15 haben (M1-MULTI-Gate Z429 feuert) — sonst Fix wirkungslos"
    )
    # Das schwere Item ist isoliert -> bekommt seinen eigenen (M2/M3-)Bogen.
    assert buckets["rigorous"][0]["id"] == "T2076"


# --- T2: [15,80)-Gap-Fall — k_max=20, Mehrheit<15 -> triviale Mehrheit gerettet -
def test_15_80_gap_majority_rescued():
    _require_import()
    # Genau die Luecke die BL-279 (split-at-80) NICHT abdeckt: k_max=20 < 80.
    items = [_item("a", 5), _item("b", 8), _item("c", 12), _item("d", 20)]
    assert _kmax(items) == 20 and _kmax(items) < 80, "Vorbedingung: in der [15,80)-Luecke"
    buckets = _SPLIT(items)
    assert len(buckets["trivial"]) == 3, "die 3 trivialen (<15) gerettet"
    assert _kmax(buckets["trivial"]) < 15, "geretteter trivial-Bucket bleibt M1-MULTI-faehig"
    assert len(buckets["rigorous"]) == 1, "nur das k=20-Item im rigorous-Bucket"


# --- T3: AK-4 — homogen-trivial (alle k<15) -> 1 Bucket, NICHT gesplittet ------
def test_homogeneous_trivial_no_split_stays_m1():
    _require_import()
    # AK-4-Verify: ein bereits homogen-trivialer Batch darf NICHT zerlegt werden
    # (kein unnoetiger Split) und bleibt damit als ganzer M1-MULTI-faehig.
    items = [_item("a", 3), _item("b", 9), _item("c", 14)]
    assert _IS_HETERO(items) is False, "homogen-trivial ist NICHT heterogen"
    buckets = _SPLIT(items)
    assert len(buckets["trivial"]) == 3, "alle 3 bleiben zusammen im trivial-Bucket"
    assert buckets["rigorous"] == [], "kein rigorous-Bucket bei homogen-trivial"
    assert _kmax(buckets["trivial"]) < 15, "bleibt als ganzer M1-MULTI-faehig (k_max<15)"


# --- T4: homogen-heavy (alle k>=15) -> 1 Bucket (rigorous), kein Split ---------
def test_homogeneous_heavy_single_bucket():
    _require_import()
    items = [_item("a", 15), _item("b", 40), _item("c", 90)]
    assert _IS_HETERO(items) is False, "homogen-heavy ist NICHT heterogen (keine triviale Teilmenge)"
    buckets = _SPLIT(items)
    assert buckets["trivial"] == [], "kein trivial-Bucket bei homogen-heavy"
    assert len(buckets["rigorous"]) == 3, "alle 3 im rigorous-Bucket"


# --- T5: is_heterogeneous-Praedikat-Faelle ------------------------------------
def test_is_heterogeneous_predicate_cases():
    _require_import()
    # heterogen: k_max>=15 UND eine triviale Teilmenge (<15) existiert
    assert _IS_HETERO([_item("a", 5), _item("b", 20)]) is True
    # NICHT heterogen: k_max>=15 aber KEINE triviale Teilmenge (alle >=15)
    assert _IS_HETERO([_item("a", 15), _item("b", 20)]) is False
    # NICHT heterogen: triviale existieren aber k_max<15 (nichts reisst mit)
    assert _IS_HETERO([_item("a", 5), _item("b", 14)]) is False
    # Grenzwert: k=15 ist rigorous (>=threshold), k=14 trivial -> heterogen
    assert _IS_HETERO([_item("a", 14), _item("b", 15)]) is True


# --- T6: threshold-Boundary — k==threshold ist rigorous (>=), nicht trivial ----
def test_threshold_boundary_inclusive_rigorous():
    _require_import()
    # k_score_max < 15 ist der M1-MULTI-Gate (strikt <). Also: k==15 -> rigorous.
    buckets = _SPLIT([_item("eq", 15), _item("lo", 14)])
    assert [i["id"] for i in buckets["rigorous"]] == ["eq"], "k==15 gehoert in rigorous (>=threshold)"
    assert [i["id"] for i in buckets["trivial"]] == ["lo"], "k==14 gehoert in trivial (<threshold)"


# --- T7: None-k_score — konservativ rigorous, zaehlt nicht als trivial ---------
def test_none_kscore_conservative_rigorous():
    _require_import()
    # Item ohne k_score (None) -> konservativ rigorous (nicht als trivial durchwinken).
    buckets = _SPLIT([_item("known", 5), _item("unknown", None)])
    assert "unknown" in [i["id"] for i in buckets["rigorous"]], (
        "None-k_score-Item MUSS konservativ in rigorous (Aufwand nicht als trivial bewiesen)"
    )
    assert [i["id"] for i in buckets["trivial"]] == ["known"]
    # Batch NUR aus None-Items: homogen-rigorous, NICHT heterogen (kein trivial vorhanden,
    # None inflationiert k_max nicht).
    only_none = [_item("x", None), _item("y", None)]
    assert _IS_HETERO(only_none) is False, "nur-None-Batch ist NICHT heterogen"
    nb = _SPLIT(only_none)
    assert len(nb["rigorous"]) == 2 and nb["trivial"] == []
    # None + trivial + heavy: heterogen (trivial existiert, heavy existiert);
    # None landet konservativ bei rigorous neben dem Heavy.
    mix = [_item("t", 5), _item("h", 30), _item("n", None)]
    assert _IS_HETERO(mix) is True
    mb = _SPLIT(mix)
    assert [i["id"] for i in mb["trivial"]] == ["t"]
    assert set(i["id"] for i in mb["rigorous"]) == {"h", "n"}


# --- T8: missing k_score field (Key fehlt ganz) == None-Behandlung ------------
def test_missing_kscore_field_treated_as_none():
    _require_import()
    items = [{"id": "no_field"}, _item("trivial", 5)]
    buckets = _SPLIT(items)
    assert "no_field" in [i["id"] for i in buckets["rigorous"]], (
        "fehlendes k_score-Feld == None -> konservativ rigorous"
    )
    assert [i["id"] for i in buckets["trivial"]] == ["trivial"]


# --- T9: leere/None-Eingabe — robust ------------------------------------------
def test_empty_and_none_input():
    _require_import()
    assert _SPLIT([]) == {"trivial": [], "rigorous": []}
    assert _SPLIT(None) == {"trivial": [], "rigorous": []}
    assert _IS_HETERO([]) is False
    assert _IS_HETERO(None) is False
    # None-Eintraege in der Liste werden defensiv verworfen
    buckets = _SPLIT([None, _item("a", 5), None, _item("b", 20)])
    assert [i["id"] for i in buckets["trivial"]] == ["a"]
    assert [i["id"] for i in buckets["rigorous"]] == ["b"]


# --- T10: Idempotenz — Split auf trivial-Bucket == trivial-Bucket -------------
def test_idempotent_split():
    _require_import()
    items = [_item("a", 5), _item("b", 8), _item("c", 20)]
    buckets = _SPLIT(items)
    # Split des trivial-Buckets erneut -> alles bleibt trivial (kein heavy mehr drin).
    re_trivial = _SPLIT(buckets["trivial"])
    assert re_trivial["trivial"] == buckets["trivial"], "trivial-Bucket ist split-stabil"
    assert re_trivial["rigorous"] == [], "kein heavy mehr im trivial-Bucket"
    # Split des rigorous-Buckets erneut -> alles bleibt rigorous.
    re_rigorous = _SPLIT(buckets["rigorous"])
    assert re_rigorous["rigorous"] == buckets["rigorous"], "rigorous-Bucket ist split-stabil"
    assert re_rigorous["trivial"] == []


# --- T11: Custom threshold (Parameter-Durchgriff, aber default=15 = M1-Decke) --
def test_custom_threshold_passthrough():
    _require_import()
    # default ist 15; explizites threshold respektiert (z.B. anderer Aufwands-Schnitt).
    items = [_item("a", 5), _item("b", 25)]
    # default 15: a trivial, b rigorous
    d = _SPLIT(items)
    assert [i["id"] for i in d["trivial"]] == ["a"]
    # threshold=30: BEIDE trivial (homogen) -> kein Split-Bedarf
    t30 = _SPLIT(items, threshold=30)
    assert len(t30["trivial"]) == 2 and t30["rigorous"] == []
    assert _IS_HETERO(items, threshold=30) is False


# --- T12: Erhalt der Item-Identitaet — Split mutiert Items NICHT ---------------
def test_split_does_not_mutate_items():
    _require_import()
    a = _item("a", 5)
    b = _item("b", 20)
    items = [a, b]
    buckets = _SPLIT(items)
    # Original-Items unveraendert (gleiche dicts, gleiche Felder)
    assert a == {"id": "a", "k_score": 5}
    assert b == {"id": "b", "k_score": 20}
    # Die Buckets enthalten dieselben Objekte (keine Kopie noetig — reine Partition)
    assert buckets["trivial"][0] is a
    assert buckets["rigorous"][0] is b


if __name__ == "__main__":
    tests = [
        test_core_t2076_split_trivial_from_heavy,
        test_15_80_gap_majority_rescued,
        test_homogeneous_trivial_no_split_stays_m1,
        test_homogeneous_heavy_single_bucket,
        test_is_heterogeneous_predicate_cases,
        test_threshold_boundary_inclusive_rigorous,
        test_none_kscore_conservative_rigorous,
        test_missing_kscore_field_treated_as_none,
        test_empty_and_none_input,
        test_idempotent_split,
        test_custom_threshold_passthrough,
        test_split_does_not_mutate_items,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed+failed} ===")
    sys.exit(0 if failed == 0 else 1)
