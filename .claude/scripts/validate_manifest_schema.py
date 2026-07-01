#!/usr/bin/env python3
"""
validate_manifest_schema.py — Manifest-Schema-Validator (F10 Sanity-Dynamic 2026-05-08).

Aufgabe: Validiert _manifest.md Dateien (global ODER per-BL) auf Schema-Drift.
Geboren aus F10 (Sanity-Dynamic): /_backlog erzeugte doppelten ## A_PIPELINE_STATE
Block beim Update — selbst-repariert, aber Risiko-Pattern.

Checks:
  C1: Keine doppelten Section-Header (## SECTION_NAME)
  C2: Pflicht-Felder wenn vorhanden (BACKLOG_STATE.counter ist Integer)
  C3: GLOBAL_*-Felder konsistent zu _session_params.md (wenn beide gegeben)

Aufruf:
  python3 validate_manifest_schema.py {manifest.md} [{session_params.md}]
  -> exit 0 bei OK, exit 1 bei Findings (stderr)

  python3 validate_manifest_schema.py --vault {vault_root}
  -> Validiert vault_root/_manifest.md + alle Backlog/{slug}/_manifest.md
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# BL-333: migration_disposition-WARN-Haken (non-blocking, Follow zu A6). C1/C2/C3 unveraendert.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from resolve_format_version import check_migration_disposition_manifest
except ImportError:
    def check_migration_disposition_manifest(text):  # type: ignore
        return []


_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_GLOBAL_FIELD_RE = re.compile(r"^\*\*GLOBAL_(\w+):\*\*\s+(.+?)\s*$", re.MULTILINE)
_SESSION_FIELD_RE = re.compile(r"^\*\*(\w+):\*\*\s+(.+?)\s*$", re.MULTILINE)
_COUNTER_RE = re.compile(r"^-\s+counter:\s+(\d+)\s*$", re.MULTILINE)


def check_doppelte_sections(text: str) -> list[str]:
    """C1: Doppelte Section-Header finden."""
    sections = _SECTION_RE.findall(text)
    seen: dict[str, int] = {}
    findings: list[str] = []
    for s in sections:
        seen[s] = seen.get(s, 0) + 1
    for name, count in seen.items():
        if count > 1:
            findings.append(f"C1 DOPPEL-SECTION: '## {name}' erscheint {count}x (sollte 1x)")
    return findings


def check_counter_integer(text: str) -> list[str]:
    """C2: BACKLOG_STATE.counter muss Integer sein."""
    findings: list[str] = []
    matches = _COUNTER_RE.findall(text)
    for m in matches:
        try:
            int(m)
        except ValueError:
            findings.append(f"C2 COUNTER-NICHT-INT: counter='{m}' ist nicht Integer")
    return findings


def check_global_session_consistency(manifest_text: str, session_text: str) -> list[str]:
    """C3: GLOBAL_*-Felder im Manifest stimmen mit session_params.md ueberein."""
    findings: list[str] = []
    global_fields = dict(_GLOBAL_FIELD_RE.findall(manifest_text))
    session_fields = dict(_SESSION_FIELD_RE.findall(session_text))
    # Mapping: GLOBAL_DIFFICULTY -> difficulty (aus session_params.md)
    pairs = [
        ("DIFFICULTY", "difficulty"),
        ("CEILING", "ceiling"),
        ("FLOOR", "floor"),
        ("HIL", "HiL"),
        ("SLICING", "slicing"),
    ]
    for global_key, session_key in pairs:
        g = global_fields.get(global_key)
        s = session_fields.get(session_key)
        if g is not None and s is not None and g != s:
            findings.append(
                f"C3 GLOBAL-SESSION-DRIFT: GLOBAL_{global_key}='{g}' != session.{session_key}='{s}'"
            )
    return findings


def validate_manifest(manifest: Path, session_params: Path | None = None) -> list[str]:
    findings: list[str] = []
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"OPEN-FAIL: {manifest}: {exc}"]
    findings.extend(check_doppelte_sections(text))
    findings.extend(check_counter_integer(text))
    if session_params and session_params.is_file():
        try:
            sp_text = session_params.read_text(encoding="utf-8")
            findings.extend(check_global_session_consistency(text, sp_text))
        except OSError:
            pass
    # BL-333: WARN-Haken (non-blocking) — NICHT in `findings` (kein Hard-Block, C1/C2/C3 unveraendert).
    for warn in check_migration_disposition_manifest(text):
        print(f"  WARN (non-blocking) {manifest}: {warn}", file=sys.stderr)
    return findings


def main(argv: list[str]) -> int:
    if "--vault" in argv:
        idx = argv.index("--vault")
        if idx + 1 >= len(argv):
            print("ERROR: --vault braucht Pfad", file=sys.stderr)
            return 2
        vault_root = Path(argv[idx + 1])
        manifests: list[tuple[Path, Path | None]] = []
        global_manifest = vault_root / "_manifest.md"
        global_session = vault_root / "_session_params.md"
        if global_manifest.is_file():
            manifests.append((global_manifest, global_session if global_session.is_file() else None))
        # Pro-BL Manifest unter Backlog/*/_manifest.md (rekursiv max 2 Tiefen)
        for sub in vault_root.rglob("Backlog/*/_manifest.md"):
            manifests.append((sub, None))
        total_findings = 0
        for m, sp in manifests:
            f = validate_manifest(m, sp)
            if f:
                print(f"\n=== {m} ===", file=sys.stderr)
                for line in f:
                    print(f"  {line}", file=sys.stderr)
                total_findings += len(f)
            else:
                print(f"OK: {m}", file=sys.stderr)
        print(f"\nGesamt: {len(manifests)} Manifeste geprueft, {total_findings} Findings", file=sys.stderr)
        return 0 if total_findings == 0 else 1

    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    manifest = Path(argv[1])
    session = Path(argv[2]) if len(argv) > 2 else None
    findings = validate_manifest(manifest, session)
    if not findings:
        print(f"OK: {manifest}", file=sys.stderr)
        return 0
    print(f"FINDINGS in {manifest}:", file=sys.stderr)
    for f in findings:
        print(f"  {f}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
