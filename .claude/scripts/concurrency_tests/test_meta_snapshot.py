#!/usr/bin/env python3
"""test_meta_snapshot.py -- Tests fuer meta_snapshot.py (BL-193 AK7-PL-1+PL-2, NC-6)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
META_SNAPSHOT = str(SCRIPTS_DIR / "meta_snapshot.py")

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


def _run(args: list[str], env: dict | None = None, cwd: str | None = None):
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, META_SNAPSHOT, *args],
        capture_output=True,
        text=True,
        env=merged,
        cwd=cwd or original_cwd,
    )


def main() -> None:
    global PASS, FAIL
    # ---------------------------------------------------------------------------
    # Test 1: --dry-run exitcode 0 (AK7-PL-1)
    # ---------------------------------------------------------------------------
    print("\n[Test 1] test_meta_snapshot_dry_run_exitcode_0")
    tmpdir1 = tempfile.mkdtemp(prefix="vault_t1_")
    try:
        (Path(tmpdir1) / "Meta" / "Universal").mkdir(parents=True)
        (Path(tmpdir1) / "Meta" / "Universal" / "sample.md").write_text("test", encoding="utf-8")
        result1 = _run(["--dry-run"], env={"CLAUDE_VAULT_ROOT": tmpdir1})
        assert_eq("--dry-run exitcode == 0", result1.returncode, 0)
        assert_true("--dry-run output contains file count", "1" in result1.stdout)
    finally:
        shutil.rmtree(tmpdir1, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 2: snapshot creates manifest (AK7-PL-1)
    # ---------------------------------------------------------------------------
    print("\n[Test 2] test_meta_snapshot_creates_manifest")
    tmpvault2 = tempfile.mkdtemp(prefix="vault_t2_")
    tmpproj2 = tempfile.mkdtemp(prefix="proj_t2_OmniCommand_")
    try:
        uni2 = Path(tmpvault2) / "Meta" / "Universal"
        uni2.mkdir(parents=True)
        (uni2 / "sample.md").write_text("content", encoding="utf-8")
        (Path(tmpproj2) / ".claude").mkdir()
        result2 = _run([], env={"CLAUDE_VAULT_ROOT": tmpvault2}, cwd=tmpproj2)
        assert_eq("snapshot exitcode == 0", result2.returncode, 0)
        manifest_path = Path(tmpproj2) / ".claude" / "meta-cache" / ".snapshot_manifest.json"
        assert_true("manifest file exists", manifest_path.exists())
        if manifest_path.exists():
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert_true("manifest has file_count", "file_count" in m)
            assert_true("manifest has created_at", "created_at" in m)
            assert_true("manifest has source_vault_path", "source_vault_path" in m)
            assert_true("manifest has files dict", isinstance(m.get("files"), dict))
            assert_true("file_count >= 1", m.get("file_count", 0) >= 1)
    finally:
        shutil.rmtree(tmpvault2, ignore_errors=True)
        shutil.rmtree(tmpproj2, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 3: --validate on fresh snapshot exitcode 0 (AK7-PL-2)
    # ---------------------------------------------------------------------------
    print("\n[Test 3] test_meta_snapshot_sha256_validate_ok")
    tmpvault3 = tempfile.mkdtemp(prefix="vault_t3_")
    tmpproj3 = tempfile.mkdtemp(prefix="proj_t3_OmniCommand_")
    try:
        uni3 = Path(tmpvault3) / "Meta" / "Universal"
        uni3.mkdir(parents=True)
        (uni3 / "file.md").write_text("hello", encoding="utf-8")
        (Path(tmpproj3) / ".claude").mkdir()
        _run([], env={"CLAUDE_VAULT_ROOT": tmpvault3}, cwd=tmpproj3)
        result3 = _run(["--validate"], env={"CLAUDE_VAULT_ROOT": tmpvault3}, cwd=tmpproj3)
        assert_eq("--validate exitcode == 0 on fresh snapshot", result3.returncode, 0)
        assert_true("--validate output contains 'konsistent'", "konsistent" in result3.stdout)
    finally:
        shutil.rmtree(tmpvault3, ignore_errors=True)
        shutil.rmtree(tmpproj3, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 4: --validate mismatch -> WARN but exitcode 0 (AK7-PL-2)
    # ---------------------------------------------------------------------------
    print("\n[Test 4] test_meta_snapshot_sha256_mismatch_warn_no_crash")
    tmpvault4 = tempfile.mkdtemp(prefix="vault_t4_")
    tmpproj4 = tempfile.mkdtemp(prefix="proj_t4_OmniCommand_")
    try:
        uni4 = Path(tmpvault4) / "Meta" / "Universal"
        uni4.mkdir(parents=True)
        (uni4 / "file.md").write_text("original", encoding="utf-8")
        (Path(tmpproj4) / ".claude").mkdir()
        _run([], env={"CLAUDE_VAULT_ROOT": tmpvault4}, cwd=tmpproj4)
        # Tamper with the cached file
        cache_file = Path(tmpproj4) / ".claude" / "meta-cache" / "Universal" / "file.md"
        if cache_file.exists():
            cache_file.write_text("modified", encoding="utf-8")
        result4 = _run(["--validate"], env={"CLAUDE_VAULT_ROOT": tmpvault4}, cwd=tmpproj4)
        assert_eq("--validate with mismatch exitcode == 0 (graceful)", result4.returncode, 0)
        assert_true("--validate outputs WARN on mismatch", "WARN" in result4.stdout or "MISMATCH" in result4.stdout)
    finally:
        shutil.rmtree(tmpvault4, ignore_errors=True)
        shutil.rmtree(tmpproj4, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 5: Vault not reachable -> exitcode 2 (PT-CMD-011)
    # ---------------------------------------------------------------------------
    print("\n[Test 5] test_meta_snapshot_vault_not_reachable_exitcode_2")
    result5 = _run([], env={"CLAUDE_VAULT_ROOT": "/nonexistent/path/that/does/not/exist_xyz"})
    assert_eq("vault not reachable -> exitcode 2", result5.returncode, 2)

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
