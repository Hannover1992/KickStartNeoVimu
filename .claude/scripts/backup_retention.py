#!/usr/bin/env python3
"""
backup_retention.py — Backup-/History-Retention (BL-338 / batch_PL2 / PL-338-4, M3).

ZWECK (Gold-Contract B): Heiler legen Backups (.bak_*, _manifest_history,
_manifest_pre_*, RECOVERY) und niemand prunt -> Heiler-als-Bloat-Produzent
(486-Empirie: 12 Backup-Leichen / 4.5MB). Dieses Modul liefert eine Backup-
Registry + Retention-Policy (keep_n juengste pro family, MD5-Dupe-Prune,
TTL-Ablauf) mit lossless-vor-Prune-Schutz (MD5-Verify gegen Out-of-Band-Tampering).

cwd-STABILITAETS-MANDAT (PL-336-4-Lehre, analog gc_budgets.py):
  Default-Registry/Root-Pfade werden __file__-RELATIV aufgeloest
  (SCRIPT_DIR.parent.parent / ...), NICHT cwd-relativ.

API:
  - register_backup(registry_path, family, backup_path, erzeugt_von, ttl, md5, ts=None)
  - read_registry(registry_path) -> list[dict]
  - prune_backups(registry_path, family, keep_n=2, dry_run=False) -> dict
  - find_backups(root, glob_pattern=None) -> list (unregistrierte Backup-Dateien)

Aufruf:
  python3 .claude/scripts/backup_retention.py find [ROOT]
  python3 .claude/scripts/backup_retention.py prune {family} [--keep=N] [--dry-run]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# __file__-RELATIVER Default (cwd-INVARIANT) — der Kern von G_cwd.
# .../.claude/scripts/backup_retention.py -> parent.parent == .../.claude
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REGISTRY_PATH = SCRIPT_DIR.parent / "audit" / "backup_registry.jsonl"

# Backup-Naming-Substrings (find_backups-Default-Glob). Eine Datei ist ein Backup,
# wenn ihr Name eines dieser Muster traegt; explizite Nicht-Backups werden ignoriert.
_BACKUP_MARKERS = (".bak", "_manifest_history", "_manifest_pre_", "RECOVERY")
_NOT_BACKUPS = ("_manifest.md", "spec.md")

_TS_FMT = "%Y-%m-%dT%H:%M:%S"


def _md5_file(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _now_ts() -> str:
    return datetime.now().strftime(_TS_FMT)


def find_default_registry() -> Path:
    """Default-Registry-Pfad, __file__-relativ (cwd-invariant)."""
    return DEFAULT_REGISTRY_PATH


# ── Registry I/O ─────────────────────────────────────────────────────────────

def register_backup(registry_path, family: str, backup_path: str, erzeugt_von: str,
                    ttl: str, md5: str, ts: str | None = None) -> dict:
    """Schreibt einen Backup-Eintrag {family, path, erzeugt_von, ttl, md5, ts} (JSONL).

    ts default = now (ISO ohne Mikrosekunden), aber optional ueberschreibbar fuer
    determinierte Ordnung in Tests. Returns den geschriebenen Eintrag.
    """
    registry_path = Path(registry_path)
    entry = {
        "family": family,
        "path": str(backup_path),
        "erzeugt_von": erzeugt_von,
        "ttl": ttl,
        "md5": md5,
        "ts": ts if ts is not None else _now_ts(),
    }
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_registry(registry_path) -> list[dict]:
    """Liest alle Eintraege; fehlende/leere Registry -> []. Defekte Zeilen werden
    uebersprungen (Dual-Read-Resilienz, kein Crash)."""
    registry_path = Path(registry_path)
    if not registry_path.exists():
        return []
    out: list[dict] = []
    for raw in registry_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _write_registry(registry_path: Path, entries: list[dict]) -> None:
    """Registry ueberschreiben (nach Prune)."""
    body = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
    registry_path.write_text((body + "\n") if body else "", encoding="utf-8")


# ── TTL ──────────────────────────────────────────────────────────────────────

def _parse_ttl(ttl: str) -> timedelta | None:
    """Parst `Nd`/`Nh`/`Nm` -> timedelta. Unbekannt/leer -> None (kein Ablauf)."""
    if not ttl:
        return None
    ttl = str(ttl).strip().lower()
    try:
        if ttl.endswith("d"):
            return timedelta(days=int(ttl[:-1]))
        if ttl.endswith("h"):
            return timedelta(hours=int(ttl[:-1]))
        if ttl.endswith("m"):
            return timedelta(minutes=int(ttl[:-1]))
        # nackte Zahl -> Tage interpretieren.
        return timedelta(days=int(ttl))
    except ValueError:
        return None


def _is_expired(entry: dict, now: datetime) -> bool:
    """True, wenn ts + ttl < now. Unparsbares ts/ttl -> nicht abgelaufen (fail-safe)."""
    delta = _parse_ttl(entry.get("ttl", ""))
    if delta is None:
        return False
    try:
        created = datetime.strptime(str(entry.get("ts", "")), _TS_FMT)
    except (ValueError, TypeError):
        return False
    return created + delta < now


# ── Prune ────────────────────────────────────────────────────────────────────

def prune_backups(registry_path, family: str, keep_n: int = 2,
                  dry_run: bool = False) -> dict:
    """Behaelt die keep_n JUENGSTEN Backups pro family; prunt die uebrigen nach Policy.

    Prune-Reihenfolge fuer die NICHT-behaltenen (aelteren) Eintraege:
      1. MD5-Duplikat (gleicher Inhalts-MD5 wie ein anderer Eintrag der family) -> prune.
      2. TTL abgelaufen (ts + ttl < now) -> prune.
    lossless-vor-Prune: ein Eintrag, dessen Datei aktuell vom registrierten md5
    ABWEICHT (out-of-band geaendert), wird NICHT geloescht -> md5_mismatch++.
    dry_run -> kein Delete / keine Registry-Aenderung, aber Report.

    Returns {kept, pruned, dupes_removed, md5_mismatch, expired}.
    """
    registry_path = Path(registry_path)
    entries = read_registry(registry_path)
    now = datetime.now()

    fam = [e for e in entries if e.get("family") == family]
    others = [e for e in entries if e.get("family") != family]

    # juengste zuerst (ts-sortiert, absteigend). Stabiler Tie-Break ueber path.
    fam_sorted = sorted(fam, key=lambda e: (str(e.get("ts", "")), str(e.get("path", ""))),
                        reverse=True)

    keep_n = max(0, int(keep_n))
    keepers = fam_sorted[:keep_n]
    candidates = fam_sorted[keep_n:]

    # MD5-Set der behaltenen + bereits-verarbeiteten -> Dupe-Erkennung.
    seen_md5 = {e.get("md5") for e in keepers if e.get("md5")}

    kept_entries: list[dict] = list(keepers)
    pruned = 0
    dupes_removed = 0
    expired = 0
    md5_mismatch = 0

    for e in candidates:
        path = Path(str(e.get("path", "")))
        reg_md5 = e.get("md5")

        # lossless-vor-Prune: aktueller Datei-MD5 muss zum registrierten passen.
        if path.exists():
            try:
                actual_md5 = _md5_file(path)
            except OSError:
                actual_md5 = None
            if actual_md5 is not None and reg_md5 and actual_md5 != reg_md5:
                # Out-of-Band geaendert -> NICHT loeschen (Safety), Eintrag behalten.
                md5_mismatch += 1
                kept_entries.append(e)
                continue

        # Base-Policy: alles jenseits der keep_n juengsten wird gepruned (Retention).
        # is_dupe / is_expired sind nur Kategorisierungen des WARUM fuer den Report.
        is_dupe = bool(reg_md5) and reg_md5 in seen_md5
        is_expired_e = _is_expired(e, now)

        if is_dupe:
            dupes_removed += 1
        if is_expired_e:
            expired += 1
        pruned += 1
        if not dry_run and path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        # Eintrag faellt aus der Registry (nicht in kept_entries).
        if reg_md5:
            seen_md5.add(reg_md5)

    if not dry_run:
        # Registry neu schreiben: andere Familien + behaltene dieser family.
        _write_registry(registry_path, others + kept_entries)

    return {
        "kept": len(keepers),
        "pruned": pruned,
        "dupes_removed": dupes_removed,
        "expired": expired,
        "md5_mismatch": md5_mismatch,
    }


# ── Discovery ────────────────────────────────────────────────────────────────

def find_backups(root, glob_pattern: str | None = None) -> list:
    """Listet (unregistrierte) Backup-Dateien unter root.

    glob_pattern=None -> Default-Marker (.bak* / _manifest_history* /
    _manifest_pre_* / RECOVERY*), ignoriert _manifest.md / spec.md. Mit
    explizitem glob_pattern wird stattdessen dieses Muster verwendet.
    """
    root = Path(root)
    if not root.exists():
        return []

    if glob_pattern is not None:
        return sorted(str(p) for p in root.rglob(glob_pattern) if p.is_file())

    out: list[str] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name
        if name in _NOT_BACKUPS:
            continue
        if any(marker in name for marker in _BACKUP_MARKERS):
            out.append(str(p))
    return sorted(out)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: backup_retention.py {find|prune} ...", file=sys.stderr)
        return 1

    cmd = argv[1]
    if cmd == "find":
        root = argv[2] if len(argv) > 2 else str(SCRIPT_DIR.parent.parent)
        for f in find_backups(root):
            print(f)
        return 0

    if cmd == "prune":
        if len(argv) < 3:
            print("usage: backup_retention.py prune {family} [--keep=N] [--dry-run]",
                  file=sys.stderr)
            return 1
        family = argv[2]
        keep_n = 2
        dry_run = False
        for arg in argv[3:]:
            if arg.startswith("--keep="):
                try:
                    keep_n = int(arg.split("=", 1)[1])
                except ValueError:
                    print(f"ERROR: --keep erwartet eine Zahl, bekam {arg!r}", file=sys.stderr)
                    return 1
            elif arg in ("--dry-run", "--dry_run"):
                dry_run = True
        res = prune_backups(find_default_registry(), family, keep_n=keep_n, dry_run=dry_run)
        mode = "DRY-RUN" if dry_run else "PRUNE"
        print(f"[{mode}] family={family}")
        for k in ("kept", "pruned", "dupes_removed", "expired", "md5_mismatch"):
            print(f"  {k} = {res[k]}")
        return 0

    print(f"ERROR: unbekanntes Kommando {cmd!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
