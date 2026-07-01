#!/usr/bin/env python3
"""BL-065 AK-12 / INV-03: FREE_MODE ist die EINZIGE markierte .claude/-Ausnahme.

Tests:
1. bl_slug=None → Pfad unter .claude/analysis/drafts/, free_mode=True
2. bl_slug='BL-TEST' → Pfad unter Vault, free_mode=False
3. Unknown key → KeyError
4. DCS_VAULT_ROOT unset + bl_slug gesetzt → EnvironmentError
5. DCS_VAULT_ROOT unset + bl_slug=None → funktioniert (FREE_MODE nicht DCS-abhaengig)
"""
import os
import sys
from pathlib import Path

# Importiere Resolver
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))
from guard_state_file_protection import resolve_artifact_path

def main():
    tests_run = 0
    tests_passed = 0

    # Test 1: FREE_MODE (bl_slug=None)
    tests_run += 1
    path, free = resolve_artifact_path("model", bl_slug=None)
    if ".claude/analysis/drafts/" in path and free is True:
        print("PASS 1: FREE_MODE returns drafts/ path + free=True")
        tests_passed += 1
    else:
        print(f"FAIL 1: FREE_MODE → path={path}, free={free}")

    # Test 2: BL-Mode (bl_slug gesetzt)
    tests_run += 1
    os.environ["DCS_VAULT_ROOT"] = "/tmp/test_vault"
    try:
        path, free = resolve_artifact_path("model", bl_slug="BL-TEST")
        if "Backlog/BL-TEST/2_Model" in path and free is False:
            print("PASS 2: BL-Mode returns Vault path + free=False")
            tests_passed += 1
        else:
            print(f"FAIL 2: BL-Mode → path={path}, free={free}")
    finally:
        del os.environ["DCS_VAULT_ROOT"]

    # Test 3: Unknown key
    tests_run += 1
    try:
        resolve_artifact_path("nonexistent_key", bl_slug=None)
        # None-Fall: kein Error, zaehlt nicht als Fail
        # Teste mit bl_slug gesetzt
        os.environ["DCS_VAULT_ROOT"] = "/tmp/test_vault"
        try:
            resolve_artifact_path("nonexistent_key", bl_slug="BL-TEST")
            print("FAIL 3: Unknown key should raise KeyError")
        except KeyError:
            print("PASS 3: Unknown key raises KeyError")
            tests_passed += 1
        finally:
            del os.environ["DCS_VAULT_ROOT"]
    except Exception as e:
        print(f"FAIL 3: Unexpected exception: {e}")

    # Test 4: DCS_VAULT_ROOT unset + bl_slug gesetzt
    tests_run += 1
    if "DCS_VAULT_ROOT" in os.environ:
        del os.environ["DCS_VAULT_ROOT"]
    try:
        resolve_artifact_path("model", bl_slug="BL-TEST")
        print("FAIL 4: Missing DCS_VAULT_ROOT should raise EnvironmentError")
    except EnvironmentError:
        print("PASS 4: Missing DCS_VAULT_ROOT raises EnvironmentError")
        tests_passed += 1

    # Test 5: DCS_VAULT_ROOT unset + bl_slug=None (FREE_MODE)
    tests_run += 1
    path, free = resolve_artifact_path("model", bl_slug=None)
    if free is True and ".claude/analysis/drafts/" in path:
        print("PASS 5: FREE_MODE works without DCS_VAULT_ROOT")
        tests_passed += 1
    else:
        print(f"FAIL 5: FREE_MODE without DCS_VAULT_ROOT → path={path}, free={free}")

    print(f"\n{tests_passed}/{tests_run} tests passed")
    sys.exit(0 if tests_passed == tests_run else 1)

if __name__ == "__main__":
    main()
