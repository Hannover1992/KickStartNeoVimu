#!/usr/bin/env python3
"""
test_inv_idf_skip_formal_bl198_batch_pl4.py — BL-198 batch_PL4 RED-Tests

Coverage (SRS=25, M3 TDD):
  T1 (AK6-PL-1): INV-IDF-SKIP-1 Pre-Condition formal: "pl_pre_filled=true -> MUSS SKIP" explizit
  T2 (AK6-PL-2): INV-IDF-SKIP-1 Anti-Pattern: "Phase 2 trotz pl_pre_filled=true -> VIOLATION" dokumentiert
  T3 (AK7-PL-1): INV-BC-1 Pre-Condition formal: "pl_pre_filled=false ODER null -> MUSS full Phase 2/3.1/3.2"
  T4 (AK7-PL-2): INV-BC-1 Anti-Pattern: "SKIP trotz pl_pre_filled=false -> VIOLATION" dokumentiert

Run: python .claude/scripts/test_inv_idf_skip_formal_bl198_batch_pl4.py
Exit 0 = alle PASS (GREEN), 1 = mindestens 1 FAIL (RED).
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
SKILLS_DIR = ROOT_DIR / ".claude" / "commands"

IDF_ORCH = SKILLS_DIR / "_IDF_orchestrate.md"

LABEL = "[test_inv_idf_skip_formal_bl198_batch_pl4]"
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
    start = text.find(start_marker)
    if start == -1:
        return ""
    end = text.find(end_marker, start + len(start_marker))
    if end == -1:
        return text[start:]
    return text[start:end]


def main():
    idf = load(IDF_ORCH)

    print(f"\n{LABEL} START (BL-198 batch_PL4 M3-RED)")
    print(f"  IDF_orchestrate: {'FOUND' if idf else 'MISSING'}")
    print()

    # Extract formal INVARIANTEN box (between |  INVARIANTEN: and closing +====+)
    inv_box_start = idf.find("|  INVARIANTEN:")
    box_close = idf.find("+====", inv_box_start + 10) if inv_box_start != -1 else -1
    if inv_box_start != -1 and box_close != -1:
        formal_inv_block = idf[inv_box_start:box_close]
    elif inv_box_start != -1:
        formal_inv_block = idf[inv_box_start:inv_box_start + 3000]
    else:
        formal_inv_block = ""

    # Extract INV-IDF-SKIP-1 section from formal block.
    # INV-IDF-SKIP-1 itself references "INV-BC-1" inline (Backward-Compat).
    # Use "INV-BC-1 (BL-198 AK-7)" as end marker to get the full skip1 definition
    # including AK6-PL-1/AK6-PL-2 additions that come after the inline reference.
    skip1_section = extract_block(formal_inv_block, "INV-IDF-SKIP-1", "INV-BC-1 (BL-198 AK-7)")
    # Extract INV-BC-1 section from formal block (its definition start)
    bc1_section = extract_block(formal_inv_block, "INV-BC-1 (BL-198 AK-7)", "+====")

    # T1 (AK6-PL-1): INV-IDF-SKIP-1 Pre-Condition formal definition
    # Must state: Pre-Condition (pl_pre_filled=true) -> MUSS SKIP (or equivalent)
    # Acceptable anchors: "AK6-PL-1", or Pre-Condition + MUSS SKIP + pl_pre_filled
    t1_ok = (
        "AK6-PL-1" in skip1_section
        or (
            ("Pre-Condition" in skip1_section or "pre_condition" in skip1_section.lower())
            and ("MUSS SKIP" in skip1_section or "SKIP" in skip1_section)
            and "pl_pre_filled" in skip1_section
        )
    )
    assert_true(
        "T1 (AK6-PL-1): INV-IDF-SKIP-1 Pre-Condition formal (pl_pre_filled=true -> MUSS SKIP)",
        t1_ok,
        "INV-IDF-SKIP-1 im INVARIANTEN-Block muss 'Pre-Condition: pl_pre_filled=true -> MUSS SKIP' oder AK6-PL-1 Anker enthalten"
    )

    # T2 (AK6-PL-2): INV-IDF-SKIP-1 Anti-Pattern documented
    # Must state: Phase 2 trotz pl_pre_filled=true -> VIOLATION (or equivalent)
    # Acceptable anchors: "AK6-PL-2", "VIOLATION" or "Anti-Pattern" in skip1_section
    t2_ok = (
        "AK6-PL-2" in skip1_section
        or (
            ("VIOLATION" in skip1_section or "Anti-Pattern" in skip1_section or "anti-pattern" in skip1_section.lower())
            and "pl_pre_filled" in skip1_section
        )
    )
    assert_true(
        "T2 (AK6-PL-2): INV-IDF-SKIP-1 Anti-Pattern (Phase 2 trotz pl_pre_filled=true -> VIOLATION)",
        t2_ok,
        "INV-IDF-SKIP-1 im INVARIANTEN-Block muss Anti-Pattern/VIOLATION Doku oder AK6-PL-2 Anker enthalten"
    )

    # T3 (AK7-PL-1): INV-BC-1 Pre-Condition formal definition
    # Must state: pl_pre_filled=false ODER null -> MUSS full Phase 2/3.1/3.2
    # Acceptable anchors: "AK7-PL-1", "Pre-Condition" + "false" + "MUSS" near INV-BC-1
    t3_ok = (
        "AK7-PL-1" in bc1_section
        or (
            ("Pre-Condition" in bc1_section or "pre_condition" in bc1_section.lower())
            and ("false" in bc1_section or "null" in bc1_section)
            and ("MUSS" in bc1_section or "full" in bc1_section.lower() or "Phase 2" in bc1_section)
        )
    )
    assert_true(
        "T3 (AK7-PL-1): INV-BC-1 Pre-Condition formal (pl_pre_filled=false/null -> MUSS full Phase 2/3.1/3.2)",
        t3_ok,
        "INV-BC-1 im INVARIANTEN-Block muss 'Pre-Condition: pl_pre_filled=false ODER null -> MUSS full Phase 2/3.1/3.2' oder AK7-PL-1 Anker enthalten"
    )

    # T4 (AK7-PL-2): INV-BC-1 Anti-Pattern documented
    # Must state: SKIP trotz pl_pre_filled=false -> VIOLATION (or equivalent)
    # Acceptable anchors: "AK7-PL-2", "VIOLATION" or "Anti-Pattern" near INV-BC-1
    t4_ok = (
        "AK7-PL-2" in bc1_section
        or (
            ("VIOLATION" in bc1_section or "Anti-Pattern" in bc1_section or "anti-pattern" in bc1_section.lower())
            and ("false" in bc1_section or "null" in bc1_section)
        )
    )
    assert_true(
        "T4 (AK7-PL-2): INV-BC-1 Anti-Pattern (SKIP trotz pl_pre_filled=false -> VIOLATION)",
        t4_ok,
        "INV-BC-1 im INVARIANTEN-Block muss Anti-Pattern/VIOLATION Doku oder AK7-PL-2 Anker enthalten"
    )

    print()
    total = PASS_COUNT + FAIL_COUNT
    print(f"{LABEL} RESULT: {PASS_COUNT}/{total} PASS, {FAIL_COUNT} FAIL")

    if FAIL_COUNT > 0:
        print(f"{LABEL} STATUS: RED — Implementierung ausstehend (BL-198 batch_PL4)")
        sys.exit(1)
    else:
        print(f"{LABEL} STATUS: GREEN — alle formalen Invarianten-Definitionen implementiert")
        sys.exit(0)


if __name__ == "__main__":
    main()
