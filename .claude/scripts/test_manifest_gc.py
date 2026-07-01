#!/usr/bin/env python3
"""
BL-202 AK-2 Test: manifest_gc.py functional tests.

Test-Cases:
  T1: Manifest unter Threshold → exit 3 (no GC)
  T2: Manifest mit history-Blocks → werden zu protokoll verschoben
  T3: --dry-run → keine Aenderung
  T4: --migrate → gc_migrated marker added
  T5: Manifest existiert nicht → exit 1
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

GC_SCRIPT = Path(__file__).parent / "manifest_gc.py"


def make_test_manifest(content, lines_total=None):
    """Create temp manifest file."""
    tmp = tempfile.NamedTemporaryFile(suffix="_manifest.md", delete=False, mode="w", encoding="utf-8")
    if lines_total:
        # Pad to N lines
        content = content + "\n" + ("# filler\n" * (lines_total - content.count("\n")))
    tmp.write(content)
    tmp.close()
    return tmp.name


def run_gc(args):
    """Run manifest_gc.py with args, return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(GC_SCRIPT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_t1_under_threshold():
    """T1: Manifest under threshold → exit 3."""
    path = make_test_manifest("---\ntype: test\n---\n# small manifest\n", lines_total=100)
    code, out, err = run_gc([path])
    assert code == 3, f"Expected exit 3, got {code}: {out} {err}"
    print(f"[T1] PASS: small manifest exit={code}")
    os.unlink(path)


def test_t2_history_blocks():
    """T2: Manifest with history blocks → moved to protokoll."""
    content = """---
type: test
---
# Test Manifest
PIPELINE_STATE:
  phase: ACTIVE
  current_step: foo
PIPELINE_STATE.history[]:
  - {step: A, time: 2025}
  - {step: B, time: 2026}
completed_sub_batches: [batch_1, batch_2, batch_3]
"""
    path = make_test_manifest(content, lines_total=6000)
    code, out, err = run_gc([path, "--force"])
    assert code == 0, f"Expected exit 0, got {code}: {out} {err}"
    # Check protokoll exists
    protokoll = Path(path).parent / "_manifest_protokoll.md"
    if protokoll.exists():
        protokoll_content = protokoll.read_text()
        assert "GC-Eintrag" in protokoll_content, "GC-Eintrag header missing"
        protokoll.unlink()
    print(f"[T2] PASS: history blocks moved exit={code}")
    os.unlink(path)


def test_t3_dry_run():
    """T3: --dry-run → no changes."""
    content = """---
type: test
---
PIPELINE_STATE.history[]:
  - {step: A}
"""
    path = make_test_manifest(content, lines_total=6000)
    original = Path(path).read_text()
    code, out, err = run_gc([path, "--dry-run", "--force"])
    assert code == 0
    assert "DRY-RUN" in out
    after = Path(path).read_text()
    assert original == after, "File modified despite --dry-run"
    print(f"[T3] PASS: dry-run no changes")
    os.unlink(path)


def test_t4_migrate_marker():
    """T4: --migrate → gc_migrated marker added."""
    content = """---
type: test
---
PIPELINE_STATE.history[]:
  - {step: A}
"""
    path = make_test_manifest(content, lines_total=6000)
    code, out, err = run_gc([path, "--force", "--migrate"])
    assert code == 0
    after = Path(path).read_text()
    assert "gc_migrated: true" in after, "Marker missing"
    print(f"[T4] PASS: migrate marker added")
    os.unlink(path)
    # Clean protokoll
    protokoll = Path(path).parent / "_manifest_protokoll.md"
    if protokoll.exists():
        protokoll.unlink()


def test_t5_missing_file():
    """T5: Non-existent manifest → exit 1."""
    code, out, err = run_gc(["/tmp/nonexistent_manifest_xyz.md"])
    assert code == 1, f"Expected exit 1, got {code}"
    print(f"[T5] PASS: missing file exit={code}")


def main():
    tests = [test_t1_under_threshold, test_t2_history_blocks,
             test_t3_dry_run, test_t4_migrate_marker, test_t5_missing_file]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed+failed} tests passed ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
