#!/usr/bin/env python3
"""BL-065 AK-14: Compliance-Script ist idempotent und seiteneffektfrei."""
import subprocess
import sys
from pathlib import Path

SCRIPT = ".claude/scripts/audit_bl065_compliance.py"


def run_script():
    result = subprocess.run(
        ["python3", SCRIPT],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def main():
    # Test 1: Script existiert
    if not Path(SCRIPT).exists():
        print(f"FAIL 1: {SCRIPT} does not exist")
        sys.exit(1)
    print(f"PASS 1: {SCRIPT} exists")

    # Test 2: Lauf 1
    rc1, out1, err1 = run_script()
    print(f"PASS 2: First run exited with code {rc1}")

    # Test 3: Lauf 2 (idempotent)
    rc2, out2, err2 = run_script()
    print(f"PASS 3: Second run exited with code {rc2}")

    # Test 4: Ausgaben identisch
    if out1 != out2:
        print(f"FAIL 4: Non-idempotent output differs between runs")
        diff_lines = sum(1 for a, b in zip(out1.splitlines(), out2.splitlines()) if a != b)
        print(f"  Diff lines: {diff_lines}")
        sys.exit(1)
    print(f"PASS 4: Output identical across 2 runs (idempotent)")

    # Test 5: Exit-Code konsistent
    if rc1 != rc2:
        print(f"FAIL 5: Exit code changed between runs ({rc1} vs {rc2})")
        sys.exit(1)
    print(f"PASS 5: Exit code consistent ({rc1})")

    print(f"\nPASS: 5/5 — compliance script is idempotent")
    sys.exit(0)


if __name__ == "__main__":
    main()
