#!/usr/bin/env python3
"""Tests fuer deferral_materialize.py (BL-323 AK-1 Emit + AK-4 Generalisierung).

TDD Stage 1 (Atomic), Modus M3. Spiegel-Stil von test_guard_idf_sdf_handoff.py
(standalone __main__-Runner + pytest-kompatibel).

deferral_materialize.py MATERIALISIERT beim Defer ein getrenntes, re-surfacing
Folge-PL-Item statt eines Prosa-Markers (machine-not-context: die Engine emittiert).
Generisch fuer Stage-Defer (AK-1) UND AK/Gate-Defer (AK-4) — SELBE Funktion.

Contract:
- materialize_deferral(defer_ctx) -> pl_item  (rein, deterministisch, idempotente id)
- write_deferral_pl(pl_item, pl_master_path)  (append-if-not-present by id, kein Doppel)

RED-Ring 1 (T1 stage_defer_materializes): Stage-Context -> valides PL-Item.
RED-Ring 2 (T2 ak_defer_materializes, AK-4): kind="ak"-Context -> deferred-ak PL-Item.
RED-Ring 3 (T3 idempotent_id): 2x materialize gleicher ctx -> identische id.
RED-Ring 4 (T4 write_dedup): write_deferral_pl 2x -> genau 1 Eintrag.
RED-Ring 5 (T5 missing_field_raises): ctx ohne defer_trigger -> ValueError.

RED-Beweis: deferral_materialize.py existiert NOCH NICHT -> ImportError ->
_MATERIALIZE/_WRITE bleiben None -> jeder Test failt loud. Das IST RED.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Import-tolerant: solange deferral_materialize.py fehlt (RED-Phase) bleiben die
# Referenzen None und jeder Test failt mit klarer Meldung statt CollectError.
try:
    from deferral_materialize import materialize_deferral as _MATERIALIZE
    from deferral_materialize import write_deferral_pl as _WRITE
    _IMPORT_ERR = None
except ImportError as e:  # RED: Modul existiert noch nicht
    _MATERIALIZE = None
    _WRITE = None
    _IMPORT_ERR = e


def _require_import():
    assert _MATERIALIZE is not None and _WRITE is not None, (
        f"deferral_materialize.py nicht importierbar (RED erwartet vor GREEN): {_IMPORT_ERR}"
    )


def _stage_ctx():
    return {
        "kind": "stage",
        "bl_id": "BL-X",
        "batch": "SB-foo",
        "deferred_stages": [3],
        "defer_reason": "dependency",
        "defer_trigger": "PL7 done AND docker_up",
        "verify": "Stage-3 Integration",
    }


def _ak_ctx():
    return {
        "kind": "ak",
        "bl_id": "BL-229",
        "deferred_ak": "AK-G",
        "defer_reason": "gate",
        "defer_trigger": "AK-D armed",
        "verify": "Gate-Beleg AK-G",
    }


def test_stage_defer_materializes():
    """T1: Stage-Defer-Context -> valides PL-Item mit allen Pflichtfeldern,
    status=deferred, re_surface=true, resurface_trigger==defer_trigger."""
    _require_import()
    ctx = _stage_ctx()
    pl = _MATERIALIZE(ctx)
    assert isinstance(pl, dict), f"pl_item muss dict sein, war {type(pl)}"
    assert pl.get("id"), "pl_item braucht eine (nicht-leere) id"
    assert pl.get("typ") == "deferred-stage", \
        f"typ erwartet 'deferred-stage', war {pl.get('typ')!r}"
    assert pl.get("deferred_stages") == [3], \
        f"deferred_stages erwartet [3], war {pl.get('deferred_stages')!r}"
    assert pl.get("defer_reason") == "dependency", \
        f"defer_reason erwartet 'dependency', war {pl.get('defer_reason')!r}"
    assert pl.get("defer_trigger") == "PL7 done AND docker_up", \
        f"defer_trigger uebernommen erwartet, war {pl.get('defer_trigger')!r}"
    assert pl.get("verify") == "Stage-3 Integration", \
        f"verify uebernommen erwartet, war {pl.get('verify')!r}"
    assert pl.get("status") == "deferred", \
        f"status erwartet 'deferred', war {pl.get('status')!r}"
    assert pl.get("re_surface") is True, \
        f"re_surface erwartet True, war {pl.get('re_surface')!r}"
    assert pl.get("resurface_trigger") == ctx["defer_trigger"], \
        f"resurface_trigger muss == defer_trigger sein, war {pl.get('resurface_trigger')!r}"


def test_ak_defer_materializes():
    """T2 (AK-4): kind='ak'-Context -> valides PL-Item mit deferred_ak,
    typ='deferred-ak'. SELBE Funktion, generalisiert."""
    _require_import()
    ctx = _ak_ctx()
    pl = _MATERIALIZE(ctx)
    assert isinstance(pl, dict), f"pl_item muss dict sein, war {type(pl)}"
    assert pl.get("id"), "pl_item braucht eine (nicht-leere) id"
    assert pl.get("typ") == "deferred-ak", \
        f"typ erwartet 'deferred-ak', war {pl.get('typ')!r}"
    assert pl.get("deferred_ak") == "AK-G", \
        f"deferred_ak erwartet 'AK-G', war {pl.get('deferred_ak')!r}"
    assert pl.get("status") == "deferred", \
        f"status erwartet 'deferred', war {pl.get('status')!r}"
    assert pl.get("re_surface") is True, \
        f"re_surface erwartet True, war {pl.get('re_surface')!r}"
    assert pl.get("resurface_trigger") == ctx["defer_trigger"], \
        f"resurface_trigger muss == defer_trigger sein, war {pl.get('resurface_trigger')!r}"


def test_idempotent_id():
    """T3: 2x materialize(gleicher ctx) -> identische id (deterministisch,
    kein Doppel-Item)."""
    _require_import()
    ctx = _stage_ctx()
    pl_a = _MATERIALIZE(ctx)
    pl_b = _MATERIALIZE(_stage_ctx())
    assert pl_a.get("id") == pl_b.get("id"), \
        f"id muss bei gleichem ctx identisch sein: {pl_a.get('id')!r} != {pl_b.get('id')!r}"


def test_write_dedup():
    """T4: write_deferral_pl 2x in temp-PL-Master -> genau 1 Eintrag mit der id
    (append-if-not-present, kein Doppel)."""
    _require_import()
    pl = _MATERIALIZE(_stage_ctx())
    pl_id = pl["id"]
    with tempfile.NamedTemporaryFile(mode="w", suffix="_PL_master.md", delete=False, encoding="utf-8") as mf:
        mf.write("# PL Master\n")
        master_path = mf.name
    try:
        _WRITE(pl, master_path)
        _WRITE(pl, master_path)
        text = Path(master_path).read_text(encoding="utf-8")
        count = text.count(pl_id)
        assert count == 1, \
            f"genau 1 Eintrag mit id erwartet (append-if-not-present), war {count} (id={pl_id!r})"
    finally:
        Path(master_path).unlink(missing_ok=True)


def test_missing_field_raises():
    """T5: defer_ctx ohne defer_trigger -> ValueError mit klarer Meldung."""
    _require_import()
    ctx = _stage_ctx()
    del ctx["defer_trigger"]
    raised = False
    try:
        _MATERIALIZE(ctx)
    except ValueError:
        raised = True
    assert raised, "fehlendes defer_trigger muss ValueError ausloesen"


if __name__ == "__main__":
    tests = [
        test_stage_defer_materializes,
        test_ak_defer_materializes,
        test_idempotent_id,
        test_write_dedup,
        test_missing_field_raises,
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
