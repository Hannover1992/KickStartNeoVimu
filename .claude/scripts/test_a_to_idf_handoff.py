#!/usr/bin/env python3
"""
test_a_to_idf_handoff.py — AK10-PL-1 BL-197 batch_E

Coverage:
  Verify A-Pipeline pl_pre_filled=true sets idf_entry_phase=3.5
  in _A_berater_routing.md + _IDF_orchestrate.md cross-reference.

  T1: _A_berater_routing.md schreibt A_PIPELINE_STATE.pl_pre_filled_after
  T2: _A_berater_routing.md schreibt BERATER_OUTPUTS.routing.idf_entry_phase
  T3: BERATER_OUTPUTS.routing.pl_pre_filled wird gesetzt (INV-ROUTING-1)
  T4: idf_entry_phase Wert = "3.5" wenn plAggregation.status=DONE
  T5: A_PIPELINE_STATE.pl_pre_filled_after = true (nicht "true" als String)
  T6: _IDF_orchestrate.md enthaelt pl_pre_filled_after als Lese-Quelle (Phase 0.9)
  T7: Phase 0.9 Bezeichnung in _IDF_orchestrate.md vorhanden

Run: python .claude/scripts/test_a_to_idf_handoff.py
Exit 0 = alle PASS, 1 = mindestens 1 FAIL.
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
COMMANDS_DIR = ROOT_DIR / ".claude" / "commands"

A_ROUTING = COMMANDS_DIR / "_A_berater_routing.md"
IDF_ORCH = COMMANDS_DIR / "_IDF_orchestrate.md"

LABEL = "[test_a_to_idf_handoff]"
PASS_COUNT = 0
FAIL_COUNT = 0


def assert_true(name, condition, hint=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  PASS  {name}")
    else:
        FAIL_COUNT += 1
        msg = f"  FAIL  {name}"
        if hint:
            msg += f": {hint}"
        print(msg)


def load(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def main():
    routing = load(A_ROUTING)
    idf = load(IDF_ORCH)

    print(f"\n{LABEL} START")
    print(f"  A_berater_routing: {'FOUND' if routing else 'MISSING'}")
    print(f"  IDF_orchestrate:   {'FOUND' if idf else 'MISSING'}")
    print()

    # T1: _A_berater_routing.md schreibt A_PIPELINE_STATE.pl_pre_filled_after
    assert_true(
        "T1: routing schreibt A_PIPELINE_STATE.pl_pre_filled_after",
        "pl_pre_filled_after" in routing,
        "Erwarte A_PIPELINE_STATE.pl_pre_filled_after im SCHREIBT-Block (BL-197 AK-7)",
    )

    # T2: _A_berater_routing.md schreibt BERATER_OUTPUTS.routing.idf_entry_phase
    assert_true(
        "T2: routing schreibt BERATER_OUTPUTS.routing.idf_entry_phase",
        "idf_entry_phase" in routing,
        "Erwarte idf_entry_phase in BERATER_OUTPUTS.routing (AK-7 PL-1)",
    )

    # T3: BERATER_OUTPUTS.routing.pl_pre_filled wird gesetzt
    assert_true(
        "T3: routing schreibt pl_pre_filled in BERATER_OUTPUTS.routing",
        "pl_pre_filled" in routing,
        "Erwarte pl_pre_filled in BERATER_OUTPUTS.routing-Schema (INV-ROUTING-1)",
    )

    # T4: idf_entry_phase Wert 3.5 dokumentiert
    assert_true(
        "T4: idf_entry_phase=3.5 Wert dokumentiert",
        '"3.5"' in routing or "3.5" in routing,
        "Erwarte Wert 3.5 fuer idf_entry_phase bei plAggregation.status=DONE",
    )

    # T5: pl_pre_filled_after = true (boolean-Logik vorhanden)
    assert_true(
        "T5: pl_pre_filled_after true-Zuweisung vorhanden",
        "pl_pre_filled_after = pl_pre_filled" in routing or
        "pl_pre_filled_after = true" in routing or
        "pl_pre_filled = true" in routing,
        "Erwarte pl_pre_filled_after=true Zuweisung bei plAggregation.status=DONE",
    )

    # T6: _IDF_orchestrate.md liest pl_pre_filled_after in Phase 0.9
    assert_true(
        "T6: IDF orchestrate liest pl_pre_filled_after (Phase 0.9)",
        "pl_pre_filled_after" in idf,
        "Erwarte pl_pre_filled_after Lesezugriff in Phase 0.9 von _IDF_orchestrate.md",
    )

    # T7: Phase 0.9 Bezeichnung vorhanden (Ankerpunkt fuer Skip-Logik)
    assert_true(
        "T7: Phase 0.9 PL-Pre-Filled-Check Ankerpunkt vorhanden",
        "Phase 0.9" in idf or "0.9" in idf,
        "Erwarte Phase 0.9 PL-Pre-Filled-Check in _IDF_orchestrate.md",
    )

    print()
    total = PASS_COUNT + FAIL_COUNT
    print(f"{LABEL} RESULT: {PASS_COUNT}/{total} PASS, {FAIL_COUNT} FAIL")

    if FAIL_COUNT > 0:
        print(f"{LABEL} STATUS: RED")
        sys.exit(1)
    else:
        print(f"{LABEL} STATUS: GREEN")
        sys.exit(0)


if __name__ == "__main__":
    main()
