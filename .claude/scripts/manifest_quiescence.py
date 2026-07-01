#!/usr/bin/env python3
"""manifest_quiescence.py — BL-229 AK-E: Quiescenz-Gate vor destruktiven Manifest-Eingriffen.

Der 486-Incident (2026-05-30) bewies: ein State-Slim waehrend einer aktiven 2. Session
brach deren State-View → musste zurueckgerollt werden. User-Autorisierung ersetzt die
Quiescenz-Pruefung NICHT. Dieses Modul ist die Pre-Condition jedes destruktiven Manifest-Tools
(AK-A Slim, AK-B/C Auslagerung, AK-G Pilot).

Das LOCK-Primitiv existiert bereits (factory_lock.py BL-194 acquire_bl/is_bl_stale). Dieses
Modul ergaenzt die ZWEITE, orthogonale Quiescenz-Achse: ist das Manifest gerade in aktiver
Bearbeitung? Zwei Signale muessen BEIDE frei sein:
  1. LOCK-Signal:  keine aktive (non-stale) FREMDE BL-Lock (factory_lock.get_bl_lock_info).
  2. MTIME-Signal: Manifest-mtime stabil ueber ein Settle-Fenster (kein konkurrierender Write).

Usage:
  py -3 manifest_quiescence.py check BL-229 [--manifest=PATH] [--settle=2.0] [--worker-id=ID]
    exit 0 = QUIESCENT (safe), 1 = BUSY (destruktiver Eingriff VERBOTEN).
"""
import argparse
import sys
import time
from pathlib import Path

DEFAULT_SETTLE = 2.0


def _stat_mtime(path: Path):
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def evaluate_quiescence(lock_info, mtime_before, mtime_after, self_worker_id=None):
    """Reine Entscheidungsfunktion (test-bar ohne sleep/IO).

    -> (is_quiescent: bool, reason: str).
    lock_info: dict aus factory_lock.get_bl_lock_info (oder None wenn kein/stale Lock).
    """
    if mtime_before is None:
        return False, "manifest not found"
    if lock_info and lock_info.get("owner") and lock_info.get("owner") != self_worker_id:
        return False, f"foreign active lock held by {lock_info.get('owner')} (phase={lock_info.get('phase', '?')})"
    if mtime_before != mtime_after:
        return False, "manifest mtime changed during settle window (active concurrent write)"
    return True, "quiescent"


def is_manifest_quiescent(manifest_path, bl_id=None, settle_seconds=DEFAULT_SETTLE,
                          self_worker_id=None, vault_root=None):
    """Echte Quiescenz-Pruefung: stat -> settle -> stat + Lock-Check.

    -> (is_quiescent: bool, reason: str).
    """
    manifest_path = Path(manifest_path)
    mtime_before = _stat_mtime(manifest_path)
    if settle_seconds and settle_seconds > 0:
        time.sleep(settle_seconds)
    mtime_after = _stat_mtime(manifest_path)

    lock_info = None
    if bl_id:
        try:
            import factory_lock
            kwargs = {}
            if vault_root is not None:
                kwargs["vault_root"] = Path(vault_root)
            lock_info = factory_lock.get_bl_lock_info(bl_id, **kwargs)
        except Exception:
            lock_info = None  # Lock-Subsystem-Fehler darf die mtime-Achse nicht maskieren

    return evaluate_quiescence(lock_info, mtime_before, mtime_after, self_worker_id)


def require_quiescent(manifest_path, bl_id=None, **kw):
    """Hard-Gate fuer destruktive Tools: raise wenn nicht quiescent."""
    ok, reason = is_manifest_quiescent(manifest_path, bl_id=bl_id, **kw)
    if not ok:
        raise RuntimeError(
            f"[QUIESCENCE-GATE] BL-229 AK-E: destruktiver Manifest-Eingriff VERBOTEN — {reason}. "
            f"Lock halten (factory_lock acquire-bl) oder Quiescenz abwarten."
        )
    return True


def _cli():
    ap = argparse.ArgumentParser(description="BL-229 AK-E Manifest-Quiescenz-Gate")
    sub = ap.add_subparsers(dest="cmd")
    pc = sub.add_parser("check")
    pc.add_argument("bl_id")
    pc.add_argument("--manifest", default=None, help="Manifest-Pfad (default: via resolve_bl_path)")
    pc.add_argument("--settle", type=float, default=DEFAULT_SETTLE)
    pc.add_argument("--worker-id", default=None)
    pc.add_argument("--vault-root", default=None)
    args = ap.parse_args()

    if args.cmd != "check":
        ap.print_help()
        sys.exit(2)

    manifest = args.manifest
    if manifest is None:
        try:
            import resolve_bl_path
            folder = resolve_bl_path.resolve_bl_path(args.bl_id)
            manifest = str(Path(folder) / "_manifest.md")
        except Exception as e:
            print(f"BUSY: konnte Manifest-Pfad nicht aufloesen ({e})", file=sys.stderr)
            sys.exit(1)

    ok, reason = is_manifest_quiescent(
        manifest, bl_id=args.bl_id, settle_seconds=args.settle,
        self_worker_id=args.worker_id, vault_root=args.vault_root,
    )
    if ok:
        print(f"QUIESCENT: {args.bl_id} — {reason} (destruktiver Eingriff erlaubt)")
        sys.exit(0)
    print(f"BUSY: {args.bl_id} — {reason} (destruktiver Eingriff VERBOTEN)", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    _cli()
