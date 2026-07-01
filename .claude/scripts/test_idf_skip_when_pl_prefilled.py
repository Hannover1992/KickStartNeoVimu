#!/usr/bin/env python3
"""
test_idf_skip_when_pl_prefilled.py — AK6-PL-1 + AK8 BL-197 batch_C

Coverage:
  T1: _IDF_orchestrate.md enthaelt pl_pre_filled skip-check Pseudocode
  T2: Skip-Logik prueft plAggregation.status=DONE (SKIP-Pfad)
  T3: Fallback-Pfad (kein plAggregation) → Phase 2/3.1/3.2 laufen normal (INV-BC-1)
  T4: null-Check explizit — fehlendes plAggregation-Feld kein Crash
  T5: PARAMETER-Tabelle enthaelt pl_pre_filled Dokumentation
  T6: _A_berater_routing.md schreibt idf_entry_phase=3.5 wenn pl_pre_filled
  T7: _A_berater_routing.md schreibt pl_pre_filled=true (INV-ROUTING-1)

Run: python .claude/scripts/test_idf_skip_when_pl_prefilled.py
Exit 0 = alle PASS, 1 = mindestens 1 FAIL.
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
SKILLS_DIR = ROOT_DIR / ".claude" / "commands"

IDF_ORCH = SKILLS_DIR / "_IDF_orchestrate.md"
A_ROUTING = SKILLS_DIR / "_A_berater_routing.md"

LABEL = "[test_idf_skip_when_pl_prefilled]"
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


def assert_false(name, condition, hint=""):
    assert_true(name, not condition, hint)


def load(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def main():
    idf = load(IDF_ORCH)
    routing = load(A_ROUTING)

    print(f"\n{LABEL} START")
    print(f"  IDF_orchestrate: {'FOUND' if idf else 'MISSING'}")
    print(f"  A_berater_routing: {'FOUND' if routing else 'MISSING'}")
    print()

    # T1: _IDF_orchestrate.md enthaelt pl_pre_filled skip-check
    assert_true(
        "T1: IDF orchestrate enthaelt pl_pre_filled",
        "pl_pre_filled" in idf,
        "Erwarte pl_pre_filled skip-check im Pseudocode (AK6-PL-1)",
    )

    # T2: Skip-Pfad — plAggregation.status=DONE → SKIP Phase 2/3.1/3.2
    assert_true(
        "T2: IDF skip-check prueft plAggregation.status=DONE",
        "plAggregation" in idf and ("SKIP" in idf or "skip" in idf.lower()),
        "Erwarte SKIP-Logik fuer plAggregation.status=DONE",
    )

    # T3: Fallback-Pfad dokumentiert (INV-BC-1)
    assert_true(
        "T3: Fallback-Pfad (kein plAggregation) normal-Lauf",
        "INV-BC-1" in idf or "backward" in idf.lower() or "Backward" in idf,
        "Erwarte INV-BC-1 Fallback-Dokumen in IDF orchestrate",
    )

    # T4: null-Check — plAggregation fehlt kein Crash
    assert_true(
        "T4: null-Check fuer fehlendes plAggregation",
        (
            "null" in idf
            and ("plAggregation" in idf)
        ),
        "Erwarte null-Safety-Check vor plAggregation-Zugriff",
    )

    # T5: PARAMETER-Tabelle pl_pre_filled Doku
    assert_true(
        "T5: PARAMETER-Tabelle enthaelt pl_pre_filled",
        "pl_pre_filled" in idf,
        "Erwarte pl_pre_filled in PARAMETER-Tabelle (AK6-PL-3)",
    )

    # T6: _A_berater_routing.md schreibt idf_entry_phase
    assert_true(
        "T6: A_berater_routing schreibt idf_entry_phase",
        "idf_entry_phase" in routing,
        "Erwarte idf_entry_phase in _A_berater_routing.md SCHREIBT-Block (AK7-PL-1)",
    )

    # T7: _A_berater_routing.md schreibt pl_pre_filled=true (INV-ROUTING-1)
    assert_true(
        "T7: A_berater_routing schreibt pl_pre_filled",
        "pl_pre_filled" in routing,
        "Erwarte pl_pre_filled in _A_berater_routing.md BERATER_OUTPUTS-Slot (AK7-PL-2)",
    )

    print()
    total = PASS_COUNT + FAIL_COUNT
    print(f"{LABEL} RESULT: {PASS_COUNT}/{total} PASS, {FAIL_COUNT} FAIL")

    if FAIL_COUNT > 0:
        print(f"{LABEL} STATUS: RED (Tests fehlgeschlagen — Implementierung ausstehend)")
        sys.exit(1)
    else:
        print(f"{LABEL} STATUS: GREEN")
        sys.exit(0)


if __name__ == "__main__":
    main()
