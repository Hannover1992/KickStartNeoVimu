#!/usr/bin/env python3
"""
BLManifestLock — Cross-Platform Lock-File Mechanik fuer BL-Manifest.

BL-151 RF-VDD-7 / AK-C-3 / AK-C-9 / AK-C-10 — Phantom-Done auf real implementiert
(NEW-K1 Audit 9, 2026-05-02).

Verwendung als Context-Manager:

    from bl_manifest_lock import BLManifestLock

    with BLManifestLock(bl_folder, timeout=10.0):
        # exklusiver Zugriff auf {bl_folder}/_manifest.md
        ...

Cross-Platform:
  - Linux/Mac: fcntl.flock(LOCK_EX | LOCK_NB)
  - Windows:   msvcrt.locking(LK_NBLCK)

Aufruf-CLI fuer Tests:
    python3 bl_manifest_lock.py --acquire <bl_folder> [--timeout 10] [--release]
    python3 bl_manifest_lock.py --test-roundtrip <bl_folder>

OQ-BL151-1: msvcrt Concurrent-Write-Verhalten unter Windows nicht final
verifiziert (kein Windows-Test-System verfuegbar). Linux/Mac via fcntl
ist robust getestet.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_IS_WINDOWS = sys.platform.startswith("win")


class LockTimeoutError(TimeoutError):
    """Wird geworfen wenn Lock nicht innerhalb timeout erworben werden kann."""


class BLManifestLock:
    """Cross-Platform Lock fuer {bl_folder}/_manifest.lock.

    BL-113b-Pattern: Lock-File pro BL-Folder, separate von _manifest.md.
    Nicht-blockierend mit Timeout (Default 10s).
    """

    def __init__(self, bl_folder: str | Path, timeout: float = 10.0,
                 retry_interval: float = 0.1):
        self.bl_folder = Path(bl_folder)
        self.lock_path = self.bl_folder / "_manifest.lock"
        self.timeout = timeout
        self.retry_interval = retry_interval
        self._fh = None  # File-Handle
        self._acquired = False

    def __enter__(self) -> "BLManifestLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    def acquire(self) -> None:
        """Erwerbe Lock. Wartet bis timeout, sonst LockTimeoutError."""
        if self._acquired:
            return  # idempotent
        self.bl_folder.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+", encoding='utf-8')
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self._lock_fh(self._fh)
                self._acquired = True
                # Schreibe Owner-Info zu Debug-Zwecken
                self._fh.seek(0)
                self._fh.truncate()
                self._fh.write(f"pid={os.getpid()} ts={time.time():.0f}\n")
                self._fh.flush()
                return
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    self._fh.close()
                    self._fh = None
                    raise LockTimeoutError(
                        f"Lock {self.lock_path} nicht erwerbbar nach {self.timeout}s"
                    )
                time.sleep(self.retry_interval)

    def release(self) -> None:
        if not self._acquired or self._fh is None:
            return
        try:
            self._unlock_fh(self._fh)
        finally:
            self._fh.close()
            self._fh = None
            self._acquired = False
            # Lock-Datei bleibt bestehen (truncate-on-acquire reicht).

    @staticmethod
    def _lock_fh(fh) -> None:
        if _IS_WINDOWS:
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock_fh(fh) -> None:
        if _IS_WINDOWS:
            import msvcrt
            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _cli_test_roundtrip(folder: Path) -> int:
    """Acquire+Release 3x — kein Deadlock pruefen (AK-C-9 Verifikation)."""
    for i in range(3):
        with BLManifestLock(folder, timeout=2.0):
            print(f"[{i+1}/3] Lock acquired on {folder}/_manifest.lock")
    print("OK: 3x Roundtrip ohne Deadlock.")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="BLManifestLock CLI fuer Tests")
    p.add_argument("--acquire", metavar="BL_FOLDER",
                   help="Lock erwerben (haelt bis EOT auf STDIN)")
    p.add_argument("--test-roundtrip", metavar="BL_FOLDER",
                   help="3x acquire+release Test")
    p.add_argument("--timeout", type=float, default=10.0)
    args = p.parse_args(argv[1:])

    if args.test_roundtrip:
        return _cli_test_roundtrip(Path(args.test_roundtrip))

    if args.acquire:
        with BLManifestLock(args.acquire, timeout=args.timeout):
            print(f"Lock erworben: {args.acquire}/_manifest.lock")
            print("Warte auf STDIN-EOT zum Release...")
            try:
                sys.stdin.read()
            except KeyboardInterrupt:
                pass
        print("Lock released.")
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
