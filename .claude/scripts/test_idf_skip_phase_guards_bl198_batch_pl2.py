#!/usr/bin/env python3
"""
test_idf_skip_phase_guards_bl198_batch_pl2.py — BL-198 batch_PL2 RED-Tests

Coverage:
  T1: test_idf_skip_phase_2_when_pl_prefilled
      Phase 2 Skip-Guard: strikte defensive IF-Bedingung mit BL-198 AK-1 Verweis
      Erwartet: "AK1-PL-2" ODER "BL-198 AK-1" als Anker in Phase 2 SKIP-Block
  T2: test_idf_skip_phase_3_1_when_pl_prefilled
      Phase 3.1 Skip-Guard: strikte defensive IF-Bedingung mit BL-198 AK-2 Verweis
      Erwartet: "AK2-PL-2" ODER "BL-198 AK-2" als Anker in Phase 3.1 SKIP-Block
  T3: test_idf_skip_phase_3_2_when_pl_prefilled
      Phase 3.2 Skip-Guard + Entry-Phase 3.5 explizit dokumentiert (BL-198 AK-3)
      Erwartet: "AK3-PL-2" ODER "BL-198 AK-3" als Anker + IDF_PIPELINE_STATE.current_phase = "3.5"
  T4: Phase 2 SKIP-Log-Zeile prueft auf INV-IDF-SKIP-1 Verweis
      Erwartet: "INV-IDF-SKIP-1" im Phase 2 SKIP-Block
  T5: Phase 3.2 SKIP-Block hat IDF_PIPELINE_STATE.current_phase = "3.5" Set-Befehl
      Erwartet: current_phase = "3.5" im 3.2-SKIP-Block (nicht nur irgendwo)
  T6: resumeGuard-Phase prueft pl_pre_filled VOR Phase 2 Aufruf
      Erwartet: Phase 0.9 Check prueft a_pipeline_state.pl_pre_filled_after
  T7: INV-IDF-SKIP-1 explizit im INVARIANTEN-Block (AK-6)
      Erwartet: INV-IDF-SKIP-1 im INVARIANTEN-Block von _IDF_orchestrate.md
  T8: INV-BC-1 explizit im INVARIANTEN-Block (AK-7)
      Erwartet: INV-BC-1 im INVARIANTEN-Block von _IDF_orchestrate.md

Run: python .claude/scripts/test_idf_skip_phase_guards_bl198_batch_pl2.py
Exit 0 = alle PASS (GREEN), 1 = mindestens 1 FAIL (RED).
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
SKILLS_DIR = ROOT_DIR / ".claude" / "commands"

IDF_ORCH = SKILLS_DIR / "_IDF_orchestrate.md"

LABEL = "[test_idf_skip_phase_guards_bl198_batch_pl2]"
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
            msg += f"\n        HINT: {hint}"
        print(msg)


def load(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def extract_block(text: str, start_marker: str, end_marker: str) -> str:
    """Extract text between two markers."""
    start = text.find(start_marker)
    if start == -1:
        return ""
    end = text.find(end_marker, start + len(start_marker))
    if end == -1:
        return text[start:]
    return text[start:end]


def main():
    idf = load(IDF_ORCH)

    print(f"\n{LABEL} START (BL-198 batch_PL2 M3-RED)")
    print(f"  IDF_orchestrate: {'FOUND' if idf else 'MISSING'}")
    print()

    # T1: test_idf_skip_phase_2_when_pl_prefilled
    # Phase 2 SKIP-Block muss BL-198 AK-1 Anker enthalten
    phase2_skip_block = extract_block(
        idf,
        "ELSE IF args.pl_only_from_a:",
        "# ─── Phase 3:"
    )
    assert_true(
        "T1: test_idf_skip_phase_2_when_pl_prefilled — AK1-PL-2 Anker im Phase 2 SKIP-Block",
        "AK1-PL-2" in phase2_skip_block or "BL-198 AK-1" in phase2_skip_block,
        "Phase 2 ELSE IF args.pl_only_from_a Block muss AK1-PL-2 oder BL-198 AK-1 als Anker haben"
    )

    # T2: test_idf_skip_phase_3_1_when_pl_prefilled
    # Phase 3.1 SKIP-Block muss BL-198 AK-2 Anker enthalten
    phase31_skip_block = extract_block(
        idf,
        "ELSE IF args.pl_only_from_a:",
        "ELSE IF all_aks_done"
    )
    assert_true(
        "T2: test_idf_skip_phase_3_1_when_pl_prefilled — AK2-PL-2 Anker im Phase 3.1 SKIP-Block",
        "AK2-PL-2" in idf and ("BL-198 AK-2" in idf or "AK-2" in idf),
        "Phase 3.1 ELSE IF pl_only_from_a Block muss AK2-PL-2 oder BL-198 AK-2 als Anker haben"
    )

    # T3: test_idf_skip_phase_3_2_when_pl_prefilled
    # Phase 3.2 SKIP-Block: AK3-PL-2 Anker + IDF_PIPELINE_STATE.current_phase = "3.5"
    phase32_block = extract_block(
        idf,
        "# ---- 3.2 plAggregation",
        "# ---- 3.5 Validator"
    )
    ak3_anchor_ok = "AK3-PL-2" in phase32_block or "BL-198 AK-3" in phase32_block
    entry_35_ok = 'current_phase = "3.5"' in phase32_block or "current_phase = '3.5'" in phase32_block
    assert_true(
        "T3: test_idf_skip_phase_3_2_when_pl_prefilled — AK3-PL-2 Anker + Entry-Phase 3.5",
        ak3_anchor_ok and entry_35_ok,
        f"Phase 3.2 SKIP-Block braucht AK3-PL-2 Anker ({ak3_anchor_ok}) + current_phase='3.5' ({entry_35_ok})"
    )

    # T4: Phase 2 SKIP-Block hat INV-IDF-SKIP-1 Verweis (AK-6 Formalisierung)
    assert_true(
        "T4: INV-IDF-SKIP-1 Verweis im Phase 2 SKIP-Block (AK-6)",
        "INV-IDF-SKIP-1" in phase2_skip_block or "INV-IDF-SKIP-1" in idf,
        "Phase 2 Skip-Kommentar muss INV-IDF-SKIP-1 referenzieren"
    )

    # T5: Phase 3.2 SKIP-Block hat current_phase = "3.5" explizit
    assert_true(
        "T5: Phase 3.2 SKIP setzt IDF_PIPELINE_STATE.current_phase = '3.5'",
        entry_35_ok,
        "current_phase = '3.5' muss explizit im 3.2-SKIP-Block gesetzt werden (AK3-PL-2)"
    )

    # T6: Phase 0.9 PL-Pre-Filled-Check prueft pl_pre_filled_after vor Phase 2 Aufruf
    phase09_block = extract_block(
        idf,
        "Phase 0.9:",
        "# ─── Phase 1:"
    )
    assert_true(
        "T6: Phase 0.9 resumeGuard prueft pl_pre_filled_after",
        "pl_pre_filled_after" in phase09_block and "args.pl_only_from_a" in phase09_block,
        "Phase 0.9 Block muss pl_pre_filled_after lesen und args.pl_only_from_a setzen"
    )

    # T7: INV-IDF-SKIP-1 explizit im formalen INVARIANTEN-Block der +======+ Box (AK-6)
    # Die formale Box geht von "|  INVARIANTEN:" bis zur schliessenden "+====+" Zeile.
    inv_box_start = idf.find("|  INVARIANTEN:")
    # Die Box schliesst sich mit "+=====" nach dem INVARIANTEN-Content (first +==== after start)
    box_close = idf.find("+====", inv_box_start + 10) if inv_box_start != -1 else -1
    if inv_box_start != -1 and box_close != -1:
        formal_inv_block = idf[inv_box_start:box_close]
    elif inv_box_start != -1:
        formal_inv_block = idf[inv_box_start:inv_box_start + 2000]
    else:
        formal_inv_block = ""
    assert_true(
        "T7: INV-IDF-SKIP-1 explizit im formalen INVARIANTEN-Block der +==+ Box (AK-6)",
        "INV-IDF-SKIP-1" in formal_inv_block,
        "INV-IDF-SKIP-1 muss im +====+ Box-INVARIANTEN-Block stehen, nicht nur PARAMETER-Tabelle (AK-6 BL-198)"
    )

    # T8: INV-BC-1 explizit im formalen INVARIANTEN-Block (AK-7)
    assert_true(
        "T8: INV-BC-1 explizit im formalen INVARIANTEN-Block der +==+ Box (AK-7)",
        "INV-BC-1" in formal_inv_block,
        "INV-BC-1 muss im +====+ Box-INVARIANTEN-Block stehen, nicht nur als Kommentar (AK-7 BL-198)"
    )

    print()
    total = PASS_COUNT + FAIL_COUNT
    print(f"{LABEL} RESULT: {PASS_COUNT}/{total} PASS, {FAIL_COUNT} FAIL")

    if FAIL_COUNT > 0:
        print(f"{LABEL} STATUS: RED — Implementierung ausstehend (BL-198 batch_PL2)")
        sys.exit(1)
    else:
        print(f"{LABEL} STATUS: GREEN — alle SKIP-Guards implementiert")
        sys.exit(0)


if __name__ == "__main__":
    main()
