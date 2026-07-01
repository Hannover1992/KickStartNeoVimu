#!/usr/bin/env python3
"""Tests fuer pl_defer_filter.py (BL-304 AK-3 — Defer-Marker-Guard beim Batch-Schnitt).

TDD Stage 1 (Atomic), Modus M3. Spiegel-Stil von test_deferral_materialize.py
(standalone __main__-Runner + pytest-kompatibel).

PROBLEM (Live-Fall DCSRE-486 batch_PL23): ein als `[~] DEFER 2026-06-09b — eigener
Chip-Delegate-Batch` markiertes PL-Item blieb beim Batch-Schnitt im aktiven Batch ->
inflationierte k_max -> erzwang M2 fuer alle 11 Items (statt M1-MULTI fuer die trivialen).

KONTRAKT (rein, deterministisch — KEIN State, KEIN IO):
- parse_pl_line(line) -> {marker, defer, text}  (None fuer Nicht-Item-Zeilen)
- is_defer_marked(item) -> bool                  (True NUR bei eindeutigem Defer)
- filter_active_batch_items(items) -> list       (Defer-Items raus, NICHT geloescht)

KONSERVATIV (Anti-Ueber-Filter): NUR eindeutige Defer-Marker filtern.
  Defer = Status-Marker `[~]` UND/ODER `DEFER`-Token im Text.
  `[ ]` (offen) und `[x]` (done) werden NICHT vom Defer-Filter angefasst —
  die ECHTE Filter-Entscheidung "welche Marker sind aktiv-batch-faehig" bleibt
  beim Caller (clustering/sequencePlanner/batchPlanner-Skill). AK-3 entfernt
  AUSSCHLIESSLICH die Defer-Inseln.

RED-Beweis: pl_defer_filter.py existiert NOCH NICHT -> ImportError -> die drei
Referenzen bleiben None -> jeder Test failt loud. Das IST RED.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Import-tolerant: solange pl_defer_filter.py fehlt (RED-Phase) bleiben die
# Referenzen None und jeder Test failt mit klarer Meldung statt CollectError.
try:
    from pl_defer_filter import parse_pl_line as _PARSE
    from pl_defer_filter import is_defer_marked as _IS_DEFER
    from pl_defer_filter import filter_active_batch_items as _FILTER
    _IMPORT_ERR = None
except ImportError as e:  # RED: Modul existiert noch nicht
    _PARSE = None
    _IS_DEFER = None
    _FILTER = None
    _IMPORT_ERR = e


def _require_import():
    assert _PARSE is not None and _IS_DEFER is not None and _FILTER is not None, (
        f"pl_defer_filter.py nicht importierbar (RED erwartet vor GREEN): {_IMPORT_ERR}"
    )


# --- T1: Tilde-Marker-Zeile wird als defer erkannt ---------------------------
def test_parse_tilde_marker():
    _require_import()
    item = _PARSE("- [~] DEFER 2026-06-09b — eigener Chip-Delegate-Batch")
    assert item is not None, "Tilde-Item-Zeile muss geparst werden, nicht None"
    assert item["marker"] == "~", f"marker erwartet '~', war {item['marker']!r}"
    assert item["defer"] is True, "Tilde + DEFER-Token -> defer=True"


# --- T2: offenes [ ]-Item ohne DEFER ist KEIN defer (kein Ueber-Filter) ------
def test_parse_open_item_not_defer():
    _require_import()
    item = _PARSE("- [ ] **T2077 — triviales Item**")
    assert item is not None, "offene Item-Zeile muss geparst werden"
    assert item["marker"] == " ", f"marker erwartet ' ' (offen), war {item['marker']!r}"
    assert item["defer"] is False, "[ ] ohne DEFER-Token darf NICHT als defer gelten"


# --- T3: DEFER-Token im offenen Item (ohne [~]) zaehlt auch als defer --------
def test_defer_token_in_open_item():
    _require_import()
    # Konservativ aber explizit: das DEFER-Token signalisiert Defer auch ohne [~].
    item = _PARSE("- [ ] T2080 — DEFER: eigener Batch noetig")
    assert item is not None
    assert item["defer"] is True, "DEFER-Token im Text -> defer=True (auch bei [ ])"


# --- T4: is_defer_marked auf geparstem Item ----------------------------------
def test_is_defer_marked_predicate():
    _require_import()
    defer_item = _PARSE("- [~] DEFER 2026-06-09b — eigener Chip-Delegate-Batch")
    normal_item = _PARSE("- [ ] **T2077**")
    done_item = _PARSE("- [x] **T2050 erledigt**")
    assert _IS_DEFER(defer_item) is True
    assert _IS_DEFER(normal_item) is False, "offenes Item ist NICHT defer"
    assert _IS_DEFER(done_item) is False, "done [x] ist NICHT defer (orthogonal)"


# --- T5: KERN-FALL — defer-Item raus, normale bleiben (DCSRE-486 T2076) ------
def test_filter_excludes_defer_keeps_normal():
    _require_import()
    raw = [
        "- [ ] **T2070 — trivial A**",
        "- [ ] **T2071 — trivial B**",
        "- [~] DEFER 2026-06-09b — T2076 eigener Chip-Delegate-Batch",
        "- [ ] **T2072 — trivial C**",
    ]
    items = [_PARSE(line) for line in raw]
    active = _FILTER(items)
    texts = [i["text"] for i in active]
    assert len(active) == 3, f"3 normale Items erwartet aktiv, waren {len(active)}"
    assert not any("T2076" in t for t in texts), (
        "defer-markiertes T2076 darf NICHT in der aktiven Auswahl sein"
    )
    assert any("T2070" in t for t in texts), "trivial A muss aktiv bleiben"
    assert any("T2072" in t for t in texts), "trivial C muss aktiv bleiben"


# --- T6: kein Ueber-Filter — reine [ ]/[x]-Menge bleibt unangetastet ---------
def test_filter_no_overfilter_without_defer():
    _require_import()
    raw = [
        "- [ ] **A**",
        "- [x] **B done**",
        "- [ ] **C**",
    ]
    items = [_PARSE(line) for line in raw]
    active = _FILTER(items)
    assert len(active) == 3, (
        f"ohne Defer-Marker darf NICHTS gefiltert werden, waren {len(active)}/3"
    )


# --- T7: Nicht-Item-Zeilen (Header/Legende/leer) -> None, robust -------------
def test_parse_non_item_lines_none():
    _require_import()
    assert _PARSE("## Parking Lot") is None
    assert _PARSE("") is None
    assert _PARSE("- [ ] Offen") is not None  # Legenden-aehnlich aber valide Checkbox
    # filter muss None-Eintraege tolerieren (defensiv)
    mixed = [None, _PARSE("- [~] DEFER X"), _PARSE("- [ ] **Y**"), None]
    active = _FILTER(mixed)
    assert all(i is not None for i in active), "filter darf keine None durchlassen"
    assert len(active) == 1, f"nur 1 aktives normales Item erwartet, war {len(active)}"


# --- T8: Idempotenz — 2x filtern = gleicher Output ---------------------------
def test_filter_idempotent():
    _require_import()
    items = [_PARSE("- [~] DEFER A"), _PARSE("- [ ] **B**")]
    once = _FILTER(items)
    twice = _FILTER(once)
    assert once == twice, "filter muss idempotent sein (2x = 1x)"


if __name__ == "__main__":
    tests = [
        test_parse_tilde_marker,
        test_parse_open_item_not_defer,
        test_defer_token_in_open_item,
        test_is_defer_marked_predicate,
        test_filter_excludes_defer_keeps_normal,
        test_filter_no_overfilter_without_defer,
        test_parse_non_item_lines_none,
        test_filter_idempotent,
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
