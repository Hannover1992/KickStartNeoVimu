#!/usr/bin/env python3
"""Tests fuer guard_geist9_wave_conformance.py (BL-230 SB-3b — AK-G7-KONFORM).

RED-Worker (TDD-RED, BL-230-SB-3b, Stage 1). NUR FAILING TESTS — KEIN Produktiv-Code.

Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (SB-3b CODE-TEIL).
SOLL (AK-G7-KONFORM): eine reine N-Report-Konformitaets-Gate-Funktion
  wave_conformance_gate(reports) (geist9-Familie / neue reine Funktion), die ueber
  eine LISTE von N Batch-Reports iteriert. Jeder Report MUSS alle 4 Phase-3.x-Outputs
  tragen (recalibrate/postItem/statusTransition/modelSync; modelSync-SKIP nur mit
  reason). Verletzung in IRGENDEINEM der N -> Gate-FAIL (fail-loud, ALL-konjunktiv).
  Inventur pro batch_id. N=1 == heutiger geist9 (Null-Regression — die bestehenden
  test_guard_geist9_post_sdf.py-Tests bleiben gruen).

IST: es existiert KEINE N-Report-Validierungs-Funktion (grep wave_conformance_gate /
  waveConformanceGate im Repo = 0). guard_geist9_post_sdf.py prueft GENAU EINEN
  Manifest-Report. -> alle Tests hier FAILEN (RED), bis der GREEN-Worker das Modul
  guard_geist9_wave_conformance.py mit wave_conformance_gate(reports) anlegt.

Muster gefolgt: test_guard_geist9_post_sdf.py (REQUIRED_BERATER 4-Phase-3-Outputs,
  modelSync-SKIP+reason Z167-173). Aufbau: Report = dict mit batch_id + den 4 Outputs.

Run: py -3 -m pytest .claude/scripts/test_guard_geist9_wave_conformance.py -q
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _gate():
    """Resolver fuer die N-Report-Gate-Funktion (greenfield -> ImportError = RED).

    GREEN-Worker legt guard_geist9_wave_conformance.py mit wave_conformance_gate(reports)
    an. Bis dahin: Import schlaegt fehl -> jeder Test, der _gate() ruft, FAILT (RED).
    """
    import guard_geist9_wave_conformance as mod
    return mod.wave_conformance_gate


def _report(batch_id, recalibrate=True, postItem=True, statusTransition=True,
            modelSync=True, modelSync_skip=False, modelSync_skip_reason=None):
    """Einen Batch-Report konstruieren (batch-id-gekeyt, 4 Phase-3.x-Outputs).

    Default: vollstaendig konform. Einzelne Outputs via False entfernbar.
    modelSync_skip=True + reason -> legitimer SKIP (Z167-173-Logik, == konform).
    modelSync_skip=True ohne reason -> nicht-konform (missing modelSync_skip_reason).
    """
    r = {"batch_id": batch_id, "BERATER_OUTPUTS": {}}
    if recalibrate:
        r["BERATER_OUTPUTS"]["recalibrate"] = {"exit_code": 0}
    if postItem:
        r["BERATER_OUTPUTS"]["postItem"] = {"exit_code": 0}
    if statusTransition:
        r["BERATER_OUTPUTS"]["statusTransition"] = {"exit_code": 0}
    if modelSync_skip:
        r["BERATER_OUTPUTS"]["modelSync"] = "SKIP"
        if modelSync_skip_reason is not None:
            r["modelSync_skip_reason"] = modelSync_skip_reason
    elif modelSync:
        r["BERATER_OUTPUTS"]["modelSync"] = {"exit_code": 0}
    return r


def _is_pass(result):
    """Gate-Ergebnis normalisieren: PASS == continue/True/'continue'/'PASS'."""
    if isinstance(result, dict):
        if "ok" in result:
            return result["ok"] is True
        if "passed" in result:
            return result["passed"] is True
        if "continue" in result:
            return result["continue"] is True
        if "result" in result:
            return result["result"] in (True, "PASS", "continue")
    return result in (True, "PASS", "continue")


def _divergent_ids(result):
    """Die vom Gate genannten divergenten batch_ids extrahieren (Befund)."""
    if isinstance(result, dict):
        for key in ("divergent_batch_ids", "divergent", "failed_batch_ids",
                    "violations", "non_conformant"):
            if key in result:
                v = result[key]
                if isinstance(v, dict):
                    return set(v.keys())
                return set(v)
    return set()


def _inventory_ids(result):
    """Die Inventur-Menge der geprueften batch_ids extrahieren."""
    if isinstance(result, dict):
        for key in ("inventory", "checked_batch_ids", "inspected", "batch_ids"):
            if key in result:
                v = result[key]
                if isinstance(v, dict):
                    return set(v.keys())
                return set(v)
    return set()


# ===========================================================================
# CODE-TEIL Exit-Kriterium 1: reine N-Report-Validierungs-Funktion existiert +
#   nimmt eine LISTE von N Reports (nicht einen Single-Report); bei N>1 werden
#   ALLE N geprueft (nicht nur erster/letzter).
# ===========================================================================
def test_wave_gate_function_exists_and_takes_list():
    gate = _gate()  # ImportError = RED (greenfield)
    assert callable(gate)
    # Nimmt eine LISTE (nicht einen Single-Report-dict): 3 konforme Reports -> PASS.
    result = gate([_report("sbA"), _report("sbB"), _report("sbC")])
    assert _is_pass(result), "3 konforme Reports muessen PASS liefern"


def test_wave_gate_checks_all_n_not_only_first():
    # EC-G7-2: divergent ist der LETZTE (Index 2) — wuerde ein "nur-erster"-Scan
    # uebersehen. ALL-konjunktiv -> FAIL.
    gate = _gate()
    reports = [_report("sb1"), _report("sb2"), _report("sb3", recalibrate=False)]
    result = gate(reports)
    assert not _is_pass(result), "divergenter LETZTER Report muss das Gate kippen (nicht nur erster geprueft)"


# ===========================================================================
# CODE-TEIL Exit-Kriterium 2: jeder Report MUSS alle 4 Phase-3.x-Outputs tragen
#   (recalibrate/postItem/statusTransition/modelSync). EIN fehlender -> nicht-konform.
#   modelSync:SKIP+reason -> konform (Z169-173-Logik wiederverwendet).
# ===========================================================================
def test_single_report_all_4_present_is_conformant():
    gate = _gate()
    assert _is_pass(gate([_report("sb1")])), "Report mit allen 4 Outputs muss konform sein"


def test_report_missing_one_output_is_non_conformant():
    gate = _gate()
    # EC-G7-2: postItem fehlt -> nicht-konform.
    assert not _is_pass(gate([_report("sb1", postItem=False)])), "fehlender postItem -> Gate FAIL"


def test_modelsync_skip_with_reason_is_conformant():
    # EC-G7-4: modelSync:SKIP mit reason == legitim (Z169-173) -> konform, NICHT FAIL.
    gate = _gate()
    r = _report("sb1", modelSync=False, modelSync_skip=True,
                modelSync_skip_reason="twin-mirror pattern, no new model")
    assert _is_pass(gate([r])), "modelSync:SKIP+reason muss konform sein (legitimer Skip)"


def test_modelsync_skip_without_reason_is_non_conformant():
    # EC-G7-5: modelSync fehlt OHNE SKIP-reason -> nicht-konform (named missing modelSync).
    gate = _gate()
    r = _report("sb1", modelSync=False, modelSync_skip=True, modelSync_skip_reason=None)
    assert not _is_pass(gate([r])), "modelSync:SKIP OHNE reason -> Gate FAIL"


# ===========================================================================
# CODE-TEIL Exit-Kriterium 3: Verletzung in IRGENDEINEM der N -> Gate-FAIL
#   (fail-loud, ALL-konjunktiv); ALLE N konform -> PASS. Der Befund listet die
#   divergente(n) batch_id(s).
# ===========================================================================
def test_all_conformant_passes():
    # EC-G7-1: N=3, alle konform -> PASS.
    gate = _gate()
    assert _is_pass(gate([_report("sb1"), _report("sb2"), _report("sb3")]))


def test_one_divergent_of_n_fails_and_names_batch_id():
    # EC-G7-2: N=3, 1 divergent (Phase-3 fehlt) -> FAIL + nennt die divergente batch_id.
    gate = _gate()
    reports = [_report("sb1"), _report("sb2", statusTransition=False), _report("sb3")]
    result = gate(reports)
    assert not _is_pass(result), "1 divergenter von N muss FAIL liefern (ALL-konjunktiv)"
    assert "sb2" in _divergent_ids(result), "Befund muss die divergente batch_id sb2 nennen"


# ===========================================================================
# CODE-TEIL Exit-Kriterium 4: Inventur pro batch_id — die Menge der geprueften
#   batch_ids == Menge der eingegebenen Reports (kein Report uebersprungen).
# ===========================================================================
def test_inventory_covers_all_input_batch_ids():
    gate = _gate()
    reports = [_report("sbX"), _report("sbY"), _report("sbZ")]
    result = gate(reports)
    assert _inventory_ids(result) == {"sbX", "sbY", "sbZ"}, "Inventur muss alle eingegebenen batch_ids abdecken"


# ===========================================================================
# CODE-TEIL Exit-Kriterium 5 (N=1 == heute): bei N=1 verhaelt sich das Gate exakt
#   wie der heutige Single-Report-geist9. (Die bestehenden geist9-Single-Report-Tests
#   bleiben gruen — Kanarienvogel; hier zusaetzlich N=1-Aequivalenz direkt.)
# ===========================================================================
def test_n1_conformant_passes_like_geist9():
    # EC-G7-6 / KOM-G7-3: 1 konformer Report -> PASS (== geist9 continue=True).
    gate = _gate()
    assert _is_pass(gate([_report("solo")]))


def test_n1_non_conformant_fails_like_geist9():
    # EC-G7-6: 1 nicht-konformer Report -> FAIL (== geist9 block bei missing recalibrate).
    gate = _gate()
    assert not _is_pass(gate([_report("solo", recalibrate=False)]))


# ===========================================================================
# Edge-Cases EC-G7-7 (1 toter Batch) + EC-G7-8 (leere Liste).
# ===========================================================================
def test_dead_batch_not_counted_as_missing_phase3():
    # EC-G7-7: 1 toter Batch (None/leer) in der Welle — das Gate prueft nur die
    # LEBENDEN Reports (filter(Boolean)/liveSortedIds-Konsistenz, SB-2/SB-3a).
    # Der tote Eintrag wird NICHT als "fehlende Phase-3" gewertet -> Gate bleibt PASS,
    # solange alle lebenden konform sind.
    gate = _gate()
    reports = [_report("sb1"), None, _report("sb3")]
    result = gate(reports)
    assert _is_pass(result), "toter Batch (None) darf nicht als fehlende Phase-3 gewertet werden"
    assert "sb3" in _inventory_ids(result) and "sb1" in _inventory_ids(result)


def test_empty_report_list_is_defined_noop():
    # EC-G7-8: leere Report-Liste ([]) -> definierter Default (PASS-No-Op), kein Crash.
    gate = _gate()
    result = gate([])
    assert _is_pass(result), "leere Report-Liste muss definierter PASS-No-Op sein (kein Crash)"


# ===========================================================================
# KOMMUTATIVITAET (3 Kriterien) — das Gate ist eine reine Mengen-Pruefung ueber N
#   Reports -> reihenfolge-/permutations-invariant (ALL-konjunktiv).
# ===========================================================================
def test_kom_g7_1_permutation_invariance():
    # KOM-G7-1: gate([rA,rB,rC]) == gate([rC,rA,rB]) (gleiche Menge, permutierte
    # Reihenfolge -> identisches PASS/FAIL + identische divergente-batch_id-Menge).
    gate = _gate()
    rA = _report("rA")
    rB = _report("rB", postItem=False)  # divergent
    rC = _report("rC")
    res1 = gate([rA, rB, rC])
    res2 = gate([rC, rA, rB])
    assert _is_pass(res1) == _is_pass(res2), "PASS/FAIL muss permutations-invariant sein"
    assert _divergent_ids(res1) == _divergent_ids(res2), "divergente-id-Menge muss permutations-invariant sein"
    assert "rB" in _divergent_ids(res1)


def test_kom_g7_2_all_conjunctive_position_irrelevant():
    # KOM-G7-2: EIN divergenter Report kippt das Gate unabhaengig von seiner Position
    # (Index 0, Mitte, Ende -> in allen drei Faellen FAIL).
    gate = _gate()
    bad = lambda bid: _report(bid, recalibrate=False)
    ok = lambda bid: _report(bid)
    first = gate([bad("d"), ok("a"), ok("b")])
    middle = gate([ok("a"), bad("d"), ok("b")])
    last = gate([ok("a"), ok("b"), bad("d")])
    assert not _is_pass(first), "divergent an Position 0 muss FAIL liefern"
    assert not _is_pass(middle), "divergent in der Mitte muss FAIL liefern"
    assert not _is_pass(last), "divergent am Ende muss FAIL liefern"


def test_kom_g7_3_n1_idempotence():
    # KOM-G7-3 (Idempotenz / N=1): 1-elementige Report-Liste == heutiges Single-Report-
    # Verhalten. gate([r]) PASS gdw. der heutige geist9 fuer r PASS gibt.
    gate = _gate()
    # konformer Single -> PASS (geist9 continue=True)
    assert _is_pass(gate([_report("r")]))
    # nicht-konformer Single -> FAIL (geist9 block) — die N->1-Reduktion ist idempotent
    assert not _is_pass(gate([_report("r", modelSync=False)]))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = errored = 0
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
            errored += 1
    print(f"\n=== {passed} passed / {failed} failed / {errored} errored (of {len(tests)}) ===")
    sys.exit(0 if failed == 0 and errored == 0 else 1)
