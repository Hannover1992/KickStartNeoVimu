#!/usr/bin/env python3
"""
migrate_to_worktree_aware.py — Migration Single → Multi-Worktree (BL-172 AK-6).

Liest existierende _session_params.md und kopiert nach
_session_params_{namespace}.md fuer den aktuellen Worktree.

Optionen:
  --dry-run    Zeigt was getan wuerde ohne zu schreiben
  --rollback   Loescht worktree-spezifische Dateien (Rueckkehr zu Single-Modus)
  --rollback-tag  Datum-Tag fuer Backup-Dateien (default: YYYY-MM-DD heute)

CLI:
  py -3 migrate_to_worktree_aware.py migrate --vault-root="..."
  py -3 migrate_to_worktree_aware.py migrate --vault-root="..." --dry-run
  py -3 migrate_to_worktree_aware.py rollback --vault-root="..." --rollback-tag=2026-05-19
  py -3 migrate_to_worktree_aware.py status --vault-root="..."
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Optional

_SCRIPT_DIR = Path(__file__).parent.absolute()

# ── Namespace-Helper ──────────────────────────────────────────────────────────

def _get_namespace(worktree_id: Optional[str] = None) -> Optional[str]:
    sys.path.insert(0, str(_SCRIPT_DIR))
    from worktree_aware_params import get_worktree_namespace
    return get_worktree_namespace(worktree_id)


# ── Migration-Core ─────────────────────────────────────────────────────────────

def migrate(
    vault_root: Path,
    worktree_id: Optional[str] = None,
    dry_run: bool = False,
    rollback_tag: Optional[str] = None,
) -> dict:
    """Migriert _session_params.md → _session_params_{namespace}.md.

    Args:
        vault_root: Pfad zum Vault-Root.
        worktree_id: Optionale explizite Worktree-ID (None = auto-detect).
        dry_run: Wenn True, keine Dateien schreiben.
        rollback_tag: Datum-Tag fuer Backup (default: heute).

    Returns:
        Dictionary mit keys: status, source, target, namespace, backed_up, dry_run.
    """
    namespace = _get_namespace(worktree_id)
    if namespace is None:
        return {
            "status": "SKIP",
            "reason": "Kein Namespace ermittelbar — Single-Worktree-Modus bleibt aktiv",
            "dry_run": dry_run,
        }

    source = vault_root / "_session_params.md"
    target = vault_root / f"_session_params_{namespace}.md"
    tag = rollback_tag or date.today().isoformat()
    backup = vault_root / f"_session_params.md.backup_{tag}"

    result: dict = {
        "status": "DRY_RUN" if dry_run else "DONE",
        "source": str(source),
        "target": str(target),
        "namespace": namespace,
        "backed_up": None,
        "dry_run": dry_run,
    }

    if not source.exists():
        result["status"] = "SKIP"
        result["reason"] = f"Quell-Datei {source} existiert nicht"
        return result

    if target.exists():
        result["status"] = "SKIP"
        result["reason"] = f"Ziel-Datei {target} existiert bereits — keine Migration noetig"
        return result

    if dry_run:
        result["would_backup"] = str(backup)
        return result

    # Backup der Original-Datei anlegen
    shutil.copy2(str(source), str(backup))
    result["backed_up"] = str(backup)

    # Inhalt mit Worktree-Header schreiben
    original_content = source.read_text(encoding="utf-8")
    header = (
        f"# Schema: worktree-namespace={namespace} (BL-172 Migration {tag})\n"
        f"# Migriert von _session_params.md am {tag}\n"
        f"# Rollback: loeschen dieser Datei → Single-Worktree-Modus aktiv\n\n"
    )
    target.write_text(header + original_content, encoding="utf-8")

    return result


def rollback(
    vault_root: Path,
    rollback_tag: str,
    worktree_id: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Rollback: Loescht worktree-spezifische Datei, stellt Backup wieder her.

    Args:
        vault_root: Pfad zum Vault-Root.
        rollback_tag: Datum-Tag des Backups das wiederhergestellt werden soll.
        worktree_id: Optionale explizite Worktree-ID.
        dry_run: Wenn True, keine Dateien veraendern.

    Returns:
        Dictionary mit keys: status, namespace, deleted, restored, dry_run.
    """
    namespace = _get_namespace(worktree_id)
    if namespace is None:
        return {
            "status": "SKIP",
            "reason": "Kein Namespace → kein Rollback noetig",
            "dry_run": dry_run,
        }

    worktree_file = vault_root / f"_session_params_{namespace}.md"
    backup_file = vault_root / f"_session_params.md.backup_{rollback_tag}"
    original_file = vault_root / "_session_params.md"

    result: dict = {
        "status": "DRY_RUN" if dry_run else "DONE",
        "namespace": namespace,
        "deleted": None,
        "restored": None,
        "dry_run": dry_run,
    }

    if dry_run:
        result["would_delete"] = str(worktree_file) if worktree_file.exists() else None
        result["would_restore"] = str(backup_file) if backup_file.exists() else None
        return result

    if worktree_file.exists():
        worktree_file.unlink()
        result["deleted"] = str(worktree_file)

    if backup_file.exists():
        shutil.copy2(str(backup_file), str(original_file))
        result["restored"] = str(original_file)
    else:
        result["status"] = "WARN"
        result["reason"] = f"Backup {backup_file} nicht gefunden"

    return result


def status(vault_root: Path) -> dict:
    """Zeigt den aktuellen Migrations-Status des Vaults.

    Returns:
        Dictionary mit keys: mode, namespace, worktree_files, base_file_exists.
    """
    namespace = _get_namespace()
    mode = "multi" if namespace is not None else "single"

    base_file = vault_root / "_session_params.md"
    worktree_files = []
    if vault_root.exists():
        for p in sorted(vault_root.glob("_session_params_*.md")):
            ns = p.stem[len("_session_params_"):]
            worktree_files.append({"namespace": ns, "path": str(p), "size": p.stat().st_size})

    return {
        "mode": mode,
        "namespace": namespace,
        "base_file_exists": base_file.exists(),
        "base_file": str(base_file),
        "worktree_files": worktree_files,
        "worktree_file_count": len(worktree_files),
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cmd_migrate(args: argparse.Namespace) -> int:
    vault_root = Path(args.vault_root)
    result = migrate(
        vault_root=vault_root,
        worktree_id=getattr(args, "worktree_id", None),
        dry_run=args.dry_run,
        rollback_tag=getattr(args, "rollback_tag", None),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in ("DONE", "DRY_RUN", "SKIP") else 1


def _cmd_rollback(args: argparse.Namespace) -> int:
    vault_root = Path(args.vault_root)
    result = rollback(
        vault_root=vault_root,
        rollback_tag=args.rollback_tag,
        worktree_id=getattr(args, "worktree_id", None),
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in ("DONE", "DRY_RUN", "SKIP") else 1


def _cmd_status(args: argparse.Namespace) -> int:
    vault_root = Path(args.vault_root)
    result = status(vault_root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Migration Single → Multi-Worktree Session-Params (BL-172 AK-6)"
    )
    subparsers = parser.add_subparsers(dest="command")

    migrate_p = subparsers.add_parser("migrate", help="Migriert _session_params.md")
    migrate_p.add_argument("--vault-root", required=True, help="Pfad zum Vault-Root")
    migrate_p.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nicht schreiben")
    migrate_p.add_argument("--rollback-tag", default=None, help="Backup-Datum-Tag (YYYY-MM-DD)")
    migrate_p.add_argument("--worktree-id", default=None, dest="worktree_id")

    rollback_p = subparsers.add_parser("rollback", help="Rollback auf Single-Worktree-Modus")
    rollback_p.add_argument("--vault-root", required=True, help="Pfad zum Vault-Root")
    rollback_p.add_argument("--rollback-tag", required=True, help="Datum-Tag des Backups")
    rollback_p.add_argument("--dry-run", action="store_true")
    rollback_p.add_argument("--worktree-id", default=None, dest="worktree_id")

    status_p = subparsers.add_parser("status", help="Zeigt Migrations-Status")
    status_p.add_argument("--vault-root", required=True, help="Pfad zum Vault-Root")

    args = parser.parse_args(argv[1:])

    if args.command == "migrate":
        return _cmd_migrate(args)
    elif args.command == "rollback":
        return _cmd_rollback(args)
    elif args.command == "status":
        return _cmd_status(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
