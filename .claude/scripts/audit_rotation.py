#!/usr/bin/env python3
"""
audit_rotation.py — Audit-/Log-Rotation (BL-338 / batch_PL2 / PL-338-5, M3).

ZWECK (Gold-Contract A): audit.jsonl waechst unbegrenzt (5.45MB); ~10 Guards
scannen es RUECKWAERTS je Edit/Write = compounding Perf-Steuer. ROTATION ist ein
standalone Trim-Tool: ARCHIVIERT die AELTESTEN Zeilen nach `audit-{YYYY-MM}.jsonl`
und BEHAELT die letzten keep_recent Zeilen in audit.jsonl.

SICHERHEITS-KERN (NICHT verhandelbar): Rotation MUSS die Guard-Backwards-Scans
intakt lassen. Die juengsten Marker (SKILL_LOAD _idf/_sdf/_redeploy/_health/
stage-seam), nach denen die Guards rueckwaerts suchen, sind per Definition RECENT
-> bleiben in audit.jsonl -> Guards UNVERAENDERT funktionsfaehig. KEINE Guard-Datei
wird hier angefasst.

cwd-STABILITAETS-MANDAT (PL-336-4-Lehre, analog gc_budgets.py):
  find_audit_path() loest den Default __file__-RELATIV auf
  (Path(__file__).resolve().parent.parent / ".claude/audit/audit.jsonl"),
  NICHT cwd-relativ. So liefert der Default-Pfad aus JEDEM cwd identisch.

Archiv-Muster: verlustfreies Archiv mit MD5-/Kommentar-Header (analog
manifest_slim._write_archive). Der lossless-Test filtert Header via
startswith("{") -> nur die JSON-Zeilen zaehlen fuer die Vollstaendigkeit.

Aufruf:
  python3 .claude/scripts/audit_rotation.py [--keep=N] [--dry-run]
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# __file__-RELATIVER Default (cwd-INVARIANT) — der Kern von G_cwd.
# .../.claude/scripts/audit_rotation.py -> parent.parent == .../.claude
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_AUDIT_PATH = SCRIPT_DIR.parent / "audit" / "audit.jsonl"


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def find_audit_path() -> Path:
    """Default-Pfad `.claude/audit/audit.jsonl`, __file__-relativ (cwd-invariant)."""
    return DEFAULT_AUDIT_PATH


def _read_lines(path: Path) -> list[str]:
    """Zeilen ohne trailing-Newline; leere/fehlende Datei -> []."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return []
    return text.splitlines()


def _archive_month_label(archived_lines: list[str]) -> str:
    """YYYY-MM aus dem ts-Praefix der AELTESTEN zu archivierenden Zeile.

    Die Zeilen sind chronologisch (aeltest zuerst); ts steht als erstes Feld im
    JSON. Wir lesen das ts der ersten archivierten Zeile und schneiden auf YYYY-MM.
    Fallback (kein parsbares ts) -> "unknown".
    """
    for line in archived_lines:
        idx = line.find('"ts"')
        if idx == -1:
            continue
        # ... "ts": "2026-06-13T..." ... -> finde den Wert nach dem ersten ':'
        colon = line.find(":", idx)
        if colon == -1:
            continue
        rest = line[colon + 1:].lstrip()
        if rest.startswith('"'):
            value = rest[1:]
            end = value.find('"')
            if end != -1:
                ts = value[:end]
                if len(ts) >= 7:
                    return ts[:7]
    return "unknown"


def rotate_audit(audit_path, keep_recent: int = 2000, dry_run: bool = False) -> dict:
    """Archiviert die AELTESTEN Zeilen, behaelt die letzten keep_recent in audit.jsonl.

    - archiviert nach `audit-{YYYY-MM}.jsonl` (YYYY-MM aus dem ts der aeltesten
      archivierten Zeile); verlustfrei (archiv-JSON-Zeilen + behaltene == Original).
    - leer/fehlend ODER keep_recent >= total -> no-op {rotated_count:0, kept_count:total}.
    - dry_run -> kein Write, kein Archiv (nur Report mit archive_path-Vorschau=None).

    Returns {rotated_count, kept_count, archive_path}.
    """
    audit_path = Path(audit_path)
    lines = _read_lines(audit_path)
    total = len(lines)

    # no-op: leer/fehlend ODER nichts zu rotieren (keep_recent deckt alles ab).
    if total == 0 or keep_recent >= total:
        return {"rotated_count": 0, "kept_count": total, "archive_path": None}

    split = total - keep_recent
    archived_lines = lines[:split]   # aelteste -> Archiv
    kept_lines = lines[split:]       # juengste -> bleiben in audit.jsonl

    month = _archive_month_label(archived_lines)
    archive_path = audit_path.parent / f"audit-{month}.jsonl"

    if dry_run:
        return {
            "rotated_count": len(archived_lines),
            "kept_count": len(kept_lines),
            "archive_path": None,
        }

    # Verlustfreies Archiv mit MD5-/Kommentar-Header (analog manifest_slim).
    archived_body = "\n".join(archived_lines)
    head = (
        f"# Audit-Rotation Archiv {month} (BL-338 PL-338-5)\n"
        f"# verlustfreies Archiv der aeltesten Zeilen, MD5={_md5(archived_body)}\n"
    )
    archive_path.write_text(head + archived_body + "\n", encoding="utf-8")

    # audit.jsonl auf die behaltenen juengsten Zeilen trimmen.
    audit_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")

    return {
        "rotated_count": len(archived_lines),
        "kept_count": len(kept_lines),
        "archive_path": str(archive_path),
    }


def rotate_log(log_path, keep_recent: int = 2000, dry_run: bool = False) -> dict:
    """Zeilen-basierte Rotation fuer _guard_log.md / .hook_debug.log.

    Behaelt die juengsten keep_recent Zeilen, lagert den Rest in `{name}.archive`
    aus (verlustfrei). leer/fehlend ODER keep_recent >= total -> no-op.
    dry_run -> kein Write.

    Returns {rotated_count, kept_count, archive_path}.
    """
    log_path = Path(log_path)
    lines = _read_lines(log_path)
    total = len(lines)

    if total == 0 or keep_recent >= total:
        return {"rotated_count": 0, "kept_count": total, "archive_path": None}

    split = total - keep_recent
    archived_lines = lines[:split]
    kept_lines = lines[split:]

    archive_path = log_path.with_name(log_path.name + ".archive")

    if dry_run:
        return {
            "rotated_count": len(archived_lines),
            "kept_count": len(kept_lines),
            "archive_path": None,
        }

    archived_body = "\n".join(archived_lines)
    # Append-an-Archiv: aeltere Rotationen erhalten (verlustfrei ueber Laeufe).
    existing = ""
    if archive_path.exists():
        existing = archive_path.read_text(encoding="utf-8", errors="replace")
        if existing and not existing.endswith("\n"):
            existing += "\n"
    archive_path.write_text(existing + archived_body + "\n", encoding="utf-8")

    log_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")

    return {
        "rotated_count": len(archived_lines),
        "kept_count": len(kept_lines),
        "archive_path": str(archive_path),
    }


def main(argv: list[str]) -> int:
    keep = 2000
    dry_run = False
    for arg in argv[1:]:
        if arg.startswith("--keep="):
            try:
                keep = int(arg.split("=", 1)[1])
            except ValueError:
                print(f"ERROR: --keep erwartet eine Zahl, bekam {arg!r}", file=sys.stderr)
                return 1
        elif arg in ("--dry-run", "--dry_run"):
            dry_run = True

    audit_path = find_audit_path()
    res = rotate_audit(audit_path, keep_recent=keep, dry_run=dry_run)
    mode = "DRY-RUN" if dry_run else "ROTATE"
    print(f"[{mode}] {audit_path}")
    print(f"  rotated_count = {res['rotated_count']}")
    print(f"  kept_count    = {res['kept_count']}")
    print(f"  archive_path  = {res['archive_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
