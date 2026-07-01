#!/usr/bin/env python3
"""BL-065 AK-11/AK-16: Backlog-Index-Konsistenz nach BL-065 DONE.

Verifiziert:
1. Task.md hat parent_phase: BL-045 Phase 2b
2. BL-045-mapping.md existiert im 5_Gap/
3. BL-045-mapping.md hat >= 10 E{n}-Eintraege (Mapping-Tabelle)
"""
import sys
import re
from pathlib import Path

# BL-225 AK-C: Vault-Root dynamisch aufloesen (vorher hardcoded /home/uczen-Linux-Pfad -> broken auf Windows).
def _resolve_vault_root() -> str:
    import subprocess
    try:
        r = Path(__file__).parent / "resolve_vault_root.py"
        if r.is_file():
            p = subprocess.run([sys.executable, str(r)], capture_output=True, text=True, timeout=5)
            if p.returncode == 0 and p.stdout.strip():
                return p.stdout.strip()
    except Exception:
        pass
    # Fallback: kanonischer Windows-Pfad (resolve_vault_root ist primaer; kein Linux-Legacy noetig auf Windows).
    return "C:/Users/Administrator/Documents/OmniCommand"

VAULT_ROOT = _resolve_vault_root()
TASK_MD = f"{VAULT_ROOT}/Backlog/BL-065-directwrite-completion/1_Task/Task.md"
MAPPING_MD = f"{VAULT_ROOT}/Backlog/BL-065-directwrite-completion/5_Gap/BL-045-mapping.md"


def main():
    failures = 0

    # Test 1: Task.md hat parent_phase
    if not Path(TASK_MD).exists():
        print(f"FAIL 1: {TASK_MD} not found")
        failures += 1
    else:
        content = Path(TASK_MD).read_text(encoding='utf-8')
        if "parent_phase: BL-045 Phase 2b" in content:
            print(f"PASS 1: Task.md has parent_phase")
        else:
            print(f"FAIL 1: Task.md missing parent_phase: BL-045 Phase 2b")
            failures += 1

    # Test 2: BL-045-mapping.md existiert
    if not Path(MAPPING_MD).exists():
        print(f"FAIL 2: BL-045-mapping.md missing")
        failures += 1
    else:
        content = Path(MAPPING_MD).read_text(encoding='utf-8')
        # Mindestens 10 Mapping-Eintraege (E1..E10)
        e_count = len(re.findall(r'\| E\d+', content))
        if e_count >= 10:
            print(f"PASS 2: BL-045-mapping.md has {e_count} E{{n}} entries")
        else:
            print(f"FAIL 2: BL-045-mapping.md only {e_count} entries (expected >= 10)")
            failures += 1

    # Test 3: Task.md hat status DONE
    if Path(TASK_MD).exists():
        content = Path(TASK_MD).read_text(encoding='utf-8')
        if "status: DONE" in content:
            print(f"PASS 3: Task.md has status: DONE")
        else:
            print(f"FAIL 3: Task.md missing status: DONE")
            failures += 1

    # Test 4: Task.md hat Rollback-Section mit konkreten SHAs
    if Path(TASK_MD).exists():
        content = Path(TASK_MD).read_text(encoding='utf-8')
        required_shas = ["9356ff6", "8df780a", "ef57621", "ab25efe", "04cc123"]
        missing = [sha for sha in required_shas if sha not in content]
        if not missing:
            print(f"PASS 4: Task.md Rollback section has all 5 concrete commit SHAs")
        else:
            print(f"FAIL 4: Task.md missing SHAs: {missing}")
            failures += 1

    if failures:
        print(f"\nFAIL: {failures} errors")
        sys.exit(1)
    print(f"\nPASS: 4/4 — Task.md + BL-045-mapping.md consistent")
    sys.exit(0)


if __name__ == "__main__":
    main()
