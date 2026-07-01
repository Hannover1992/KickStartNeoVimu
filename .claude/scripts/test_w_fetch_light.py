#!/usr/bin/env python3
"""Tests fuer w_fetch_light.py (BL-312 AK-8, SB-srseval Stage 1, Modus M3).

TDD RED-Phase (INV-PM-1). Spiegel-Stil von test_deferral_materialize.py /
test_guard_idf_sdf_handoff.py (import-tolerant + standalone __main__-Runner +
pytest-kompatibel).

w_fetch_light.py ist der VORGELAGERTE Anknuepfungs-Schritt vor der SRS-Formel:
late PL-Items ohne w_refs werden ERST an Model-W{n}-Knoten geknuepft, damit sie
nicht faelschlich in die srs=100/no_truth_refs-Falle laufen (Kollaps vermieden).
Die srs-FORMEL selbst wird NICHT angefasst — W_fetch-light ist vorgelagert.

Contract (Blueprint SB-srseval S1):
- match_item_to_model(item_text, model_w_nodes, threshold=0.5) -> list[dict]
  Pro W{n}-Node (id, status, title) fuzzy_match_score (Token-Overlap, 0.0-1.0);
  Treffer >= threshold -> w_ref {id, status, score, source:"W_fetch-light"}.
  Sortiert nach score desc, leer wenn kein Treffer >= threshold (degraded, kein Crash).
  Rein, deterministisch (kein FS-Write, kein Python-hash-Nichtdeterminismus).

RED-Ring 1 (T-MATCH): Item + Model mit passendem W{n} -> mind. W3 (hoechster score),
  w_ref hat {id, status, score>=0.5, source}.
RED-Ring 2 (T-NOMATCH): voellig unrelated Item -> leer (degraded, kein Crash).
RED-Ring 3 (T-COLLAPSE-AVOID, Kern-Wert): late Item OHNE w_refs + Model mit Match ->
  match fuellt w_refs -> lokale SRS-Mini-Nachbildung -> srs != 100 (Kollaps vermieden).
  KONTRAST: dasselbe Item OHNE W_fetch-light (leere w_refs) -> srs == 100 (no_truth_refs).
RED-Ring 4 (T-DETERMINISTIC): 2x match(gleicher Input) -> identisches Ergebnis.

RED-Beweis: w_fetch_light.py existiert NOCH NICHT -> ImportError -> _MATCH bleibt
None -> jeder Test failt loud. Das IST RED.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Import-tolerant: solange w_fetch_light.py fehlt (RED-Phase) bleibt die Referenz
# None und jeder Test failt mit klarer Meldung statt CollectError.
try:
    from w_fetch_light import match_item_to_model as _MATCH
    _IMPORT_ERR = None
except ImportError as e:  # RED: Modul existiert noch nicht
    _MATCH = None
    _IMPORT_ERR = e


def _require_import():
    assert _MATCH is not None, (
        f"w_fetch_light.py nicht importierbar (RED erwartet vor GREEN): {_IMPORT_ERR}"
    )


def _model_nodes():
    return [
        {"id": "W3", "status": "OFFEN", "title": "Dispatcher routet Batch an Worker"},
        {"id": "W5", "status": "BESTAETIGT", "title": "Commit-Seam normiert Message"},
    ]


# --- lokale SRS-Mini-Nachbildung (NUR fuer T-COLLAPSE-AVOID; keine Formel-Abhaengigkeit
#     vom Sibling-Modul, kein Eingriff in die echte srs-Formel) -----------------------
_SRS_UNSICHER = {"TENTATIV", "HYPOTHESE", "OFFEN"}


def _mini_srs(w_refs):
    """Nachbildung der echten srs-Formel inkl. FLAG (mirror test_srs_compute):
    Leere w_refs -> {srs:100, flag:'no_truth_refs', breakdown:[]} (DER BUG).
    Sonst -> {srs: Anteil-unsicher*100, flag:None, breakdown: refs} (gekoppelt;
    srs spiegelt den ECHTEN status-Mix — all-OFFEN=100 ist KORREKT, kein Bug)."""
    if not w_refs:
        return {"srs": 100, "flag": "no_truth_refs", "breakdown": []}
    unsicher = sum(1 for w in w_refs if w["status"] in _SRS_UNSICHER)
    srs = round((unsicher / len(w_refs)) * 100, 1)
    return {"srs": srs, "flag": None, "breakdown": list(w_refs)}


def test_match_item_to_model():
    """T-MATCH: item_text matcht W3 (Dispatcher/Routing/Batch/Worker) am staerksten;
    w_ref hat {id, status, score>=0.5, source}."""
    _require_import()
    item_text = "Batch-Routing zum Worker im Dispatcher"
    refs = _MATCH(item_text, _model_nodes(), threshold=0.5)
    assert isinstance(refs, list), f"Rueckgabe muss list sein, war {type(refs)}"
    assert len(refs) >= 1, f"mind. 1 Treffer erwartet (W3), war {len(refs)}: {refs!r}"
    ids = [r["id"] for r in refs]
    assert "W3" in ids, f"W3 (hoechster score) muss matchen, war {ids!r}"
    # W3 ist der staerkste Treffer -> steht vorn (sortiert nach score desc)
    top = refs[0]
    assert top["id"] == "W3", f"hoechster score erwartet W3, war {top['id']!r}"
    assert top["status"] == "OFFEN", f"status uebernommen erwartet 'OFFEN', war {top['status']!r}"
    assert top["score"] >= 0.5, f"score>=0.5 (>=threshold) erwartet, war {top['score']!r}"
    assert top["source"] == "W_fetch-light", \
        f"source erwartet 'W_fetch-light', war {top.get('source')!r}"


def test_nomatch_returns_empty():
    """T-NOMATCH: voellig unrelated item -> leer (kein Treffer >= threshold),
    degraded, KEIN Crash."""
    _require_import()
    refs = _MATCH("voellig unrelated xyzzy quux", _model_nodes(), threshold=0.5)
    assert isinstance(refs, list), f"Rueckgabe muss list sein, war {type(refs)}"
    assert refs == [], f"kein Treffer >= threshold erwartet (leer), war {refs!r}"


def test_collapse_avoid():
    """T-COLLAPSE-AVOID (Kern-Wert, BL-312-Lead-Korrektur): W_fetch-light hebt ein late
    Item von 'blind' (no_truth_refs-FLAG, breakdown leer = DER BUG) auf 'an-seine-
    Wahrheiten-gekoppelt' (flag=None, breakdown non-empty). Die Kollaps-Vermeidung ist
    das CLEAREN des no_truth_refs-FLAGS — NICHT ein erzwungener srs-Wert != 100.
    Genuine all-OFFEN bleibt KORREKT srs=100 (BL-255 AK-S3: 'blind' != 'unsicher').
    Plus Dilutions-Schutz: nur die relevante W3 koppelt, NICHT die unverwandte W5."""
    _require_import()
    item_text = "Batch-Routing zum Worker im Dispatcher"

    # OHNE W_fetch-light: late Item ohne w_refs -> no_truth_refs-FLAG (der Bug)
    ohne = _mini_srs([])
    assert ohne["flag"] == "no_truth_refs", \
        f"KONTRAST: leere w_refs -> no_truth_refs-FLAG erwartet, war {ohne!r}"
    assert ohne["breakdown"] == [], f"breakdown leer erwartet, war {ohne['breakdown']!r}"

    # MIT W_fetch-light: an W3 gekoppelt -> no_truth_refs-FLAG GECLEARED + breakdown non-empty.
    # srs=100 ist hier KORREKT (W3 OFFEN, genuine Unsicherheit) — NICHT mehr der Bug.
    refs = _MATCH(item_text, _model_nodes(), threshold=0.5)
    assert len(refs) >= 1, f"W_fetch-light muss late Item an W{{n}} knuepfen, war {refs!r}"
    mit = _mini_srs(refs)
    assert mit["flag"] != "no_truth_refs", \
        f"MIT W_fetch-light: no_truth_refs-FLAG muss gecleared sein, war {mit!r}"
    assert mit["breakdown"], f"breakdown muss non-empty sein (gekoppelt), war {mit!r}"
    # Dilutions-Schutz: unverwandte W5 (sub-threshold) darf NICHT mit-angeknuepft werden
    ids = [w["id"] for w in refs]
    assert "W5" not in ids, \
        f"unverwandte W5 (sub-threshold) darf NICHT koppeln (Dilutions-Schutz), war {ids!r}"


def test_matched_status_flows_through():
    """T-STATUS-FLOW (BL-312-Lead-Korrektur): der srs spiegelt den ECHTEN status der
    GEKOPPELTEN Wahrheit (nicht diluted). Ein Item, das an die BESTAETIGT-Wahrheit (W5)
    koppelt, bekommt niedrigen srs (0) — Beweis dass W_fetch-light den korrekten status
    durchreicht statt durch unverwandte Knoten zu verfaelschen."""
    _require_import()
    refs = _MATCH("Commit-Seam normiert die Message", _model_nodes(), threshold=0.5)
    assert len(refs) >= 1 and refs[0]["id"] == "W5", \
        f"Item muss an W5 (BESTAETIGT) koppeln, war {refs!r}"
    assert "W3" not in [w["id"] for w in refs], \
        f"unverwandte W3 darf NICHT koppeln (Dilutions-Schutz), war {refs!r}"
    mit = _mini_srs(refs)
    assert mit["srs"] == 0.0, f"BESTAETIGT-Kopplung -> srs=0 erwartet, war {mit!r}"
    assert mit["flag"] != "no_truth_refs", f"kein no_truth_refs (gekoppelt), war {mit!r}"


def test_deterministic():
    """T-DETERMINISTIC: 2x match(gleicher Input) -> identisches Ergebnis
    (kein Python-hash-Nichtdeterminismus, stabil sortiert)."""
    _require_import()
    item_text = "Batch-Routing zum Worker im Dispatcher"
    a = _MATCH(item_text, _model_nodes(), threshold=0.5)
    b = _MATCH(item_text, _model_nodes(), threshold=0.5)
    assert a == b, f"match muss deterministisch sein: {a!r} != {b!r}"


if __name__ == "__main__":
    tests = [
        test_match_item_to_model,
        test_nomatch_returns_empty,
        test_collapse_avoid,
        test_matched_status_flows_through,
        test_deterministic,
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
