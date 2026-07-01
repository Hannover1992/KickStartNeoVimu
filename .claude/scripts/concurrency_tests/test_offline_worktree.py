#!/usr/bin/env python3
"""test_offline_worktree.py -- AK7-PL-5: Offline-Worktree-Test (BL-193 Stage 3).

Verifikation: resolve_vault_meta.resolve_meta() liefert Ergebnis via meta-cache
wenn Vault nicht erreichbar. Test-Setup nutzt meta_snapshot.py als Fixture.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
META_SNAPSHOT = str(SCRIPTS_DIR / "meta_snapshot.py")
RESOLVE_META = str(SCRIPTS_DIR / "resolve_vault_meta.py")

PASS = 0
FAIL = 0
original_cwd = str(Path.cwd())


def assert_eq(label: str, actual, expected) -> None:
    global PASS, FAIL
    if actual == expected:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label}")
        print(f"        expected: {expected!r}")
        print(f"        actual:   {actual!r}")
        FAIL += 1


def assert_true(label: str, value: bool) -> None:
    global PASS, FAIL
    if value:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label} -- expected True, got False")
        FAIL += 1


def assert_none(label: str, value) -> None:
    global PASS, FAIL
    if value is None:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label} -- expected None, got {value!r}")
        FAIL += 1


def _run_snapshot(args: list[str], vault_root: str, cwd: str):
    env = {**os.environ, "CLAUDE_VAULT_ROOT": vault_root}
    return subprocess.run(
        [sys.executable, META_SNAPSHOT, *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )


def _run_resolve(rel_path: str, vault_root: str, cwd: str):
    env = {**os.environ, "CLAUDE_VAULT_ROOT": vault_root}
    return subprocess.run(
        [sys.executable, RESOLVE_META, rel_path],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )


def main() -> None:
    global PASS, FAIL
    # ---------------------------------------------------------------------------
    # Test 1: Fail Path (RED-first: einfachster Fall)
    # Kein Vault, kein meta-cache → resolve_meta gibt None zurueck (exitcode 2)
    # ---------------------------------------------------------------------------
    print("\n[Test 1] test_offline_worktree_fails_without_cache (Fail Path)")
    tmpproj1 = tempfile.mkdtemp(prefix="proj_offline_t1_OmniCommand_")
    try:
        (Path(tmpproj1) / ".claude").mkdir()
        # Kein meta-cache erstellt, kein erreichbarer Vault
        result1 = _run_resolve("implementation/stage_1.md", "/nonexistent_vault_xyz", tmpproj1)
        assert_eq(
            "Vault FAIL + kein meta-cache -> exitcode 2",
            result1.returncode,
            2,
        )
        assert_true(
            "stderr enthaelt NOT_FOUND oder meta-snapshot",
            "NOT_FOUND" in result1.stderr or "meta" in result1.stderr.lower(),
        )
    finally:
        shutil.rmtree(tmpproj1, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 2: Happy Path (GOLD — AK7-PL-5 Haupt-Kriterium)
    # meta-cache via meta_snapshot.py befuellt, Vault danach offline → Treffer
    # ---------------------------------------------------------------------------
    print("\n[Test 2] test_offline_worktree_reads_meta_from_cache (Happy Path = GOLD)")
    tmpvault2 = tempfile.mkdtemp(prefix="vault_offline_t2_")
    tmpproj2 = tempfile.mkdtemp(prefix="proj_offline_t2_OmniCommand_")
    try:
        # Setup: Vault-Stub mit einer Datei in Universal/
        uni2 = Path(tmpvault2) / "Meta" / "Universal"
        uni2.mkdir(parents=True)
        (uni2 / "stage_1.md").write_text(
            "# stage_1 stub\nstatus: active\n", encoding="utf-8"
        )
        (Path(tmpproj2) / ".claude").mkdir()

        # Snapshot erstellen (Vault online)
        snap2 = _run_snapshot([], vault_root=str(tmpvault2), cwd=tmpproj2)
        assert_eq("Snapshot exitcode == 0", snap2.returncode, 0)

        meta_cache = Path(tmpproj2) / ".claude" / "meta-cache"
        assert_true("meta-cache Verzeichnis existiert nach Snapshot", meta_cache.exists())

        # Vault jetzt offline simulieren → resolve_meta via meta-cache
        result2 = _run_resolve("stage_1.md", "/nonexistent_vault_xyz", tmpproj2)
        assert_eq(
            "Vault offline + meta-cache vorhanden -> exitcode 0 (GOLD)",
            result2.returncode,
            0,
        )
        assert_true(
            "Ergebnis-Pfad enthaelt meta-cache",
            "meta-cache" in result2.stdout or "meta_cache" in result2.stdout,
        )
    finally:
        shutil.rmtree(tmpvault2, ignore_errors=True)
        shutil.rmtree(tmpproj2, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print(f"\n{'='*40}")
    print(f"Results: {PASS} PASS, {FAIL} FAIL")
    if FAIL == 0:
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
