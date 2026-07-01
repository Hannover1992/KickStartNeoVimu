#!/usr/bin/env python3
"""
manifest_dedup.py — Deterministische Singleton-Section-Deduplizierung.

Backing-Skript fuer /_hook_workaround --op=manifest-dedup.
Ersetzt Ad-hoc-Improvisation (die auf cp1252/bash-Escaping scheitert).

Problem:
  guard_stab9 blockt Manifest-Writes wenn Singleton-Sections (## DF_BATCH_STATE,
  ## A_PIPELINE_STATE, ## IDF_PIPELINE_STATE etc.) mehrfach ohne disambiguierenden
  Suffix vorkommen (pre-existing dups aus alten Rounds).

Loesung:
  Behalte das LETZTE Vorkommen (= aktueller State, append-only-Manifest) als kanonisch.
  Suffixe alle FRUEHEREN Vorkommen mit ` (ARCHIV-{i}-{date})` → disambiguiert + erhalten.

Idempotenz:
  Sections die bereits einen Suffix-Marker `(...)` tragen werden NICHT erneut suffixed,
  AUSSER es gibt 2+ mit identischem Suffix (dann sekundaerer `(DUP-{i})`-Marker).

Encoding: IMMER UTF-8 (kein cp1252-Crash auf Windows).

Usage:
  py -3 manifest_dedup.py --manifest=PATH [--dry-run] [--apply]
  py -3 manifest_dedup.py --manifest=PATH --self-test
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Singleton-Sections: duerfen NUR 1x (ohne Suffix) vorkommen.
# BERATER_OUTPUTS.* + POST_SDF_PHASE_3_STATE etc. sind LEGITIM repeated → nicht hier.
SINGLETON_SECTIONS = [
    "BDF_PIPELINE_STATE",
    "DF_BATCH_STATE",
    "FACTORY_STATES",
    "BL_LIFECYCLE_STATE",
    "A_PIPELINE_STATE",
    "IDF_PIPELINE_STATE",
    "DF_PIPELINE_STATE",
]


def parse_headers(content):
    """Finde alle ## Section-Header mit Position + voller Zeile.

    Returns: list of (pos, full_header_line, section_base_name)
    """
    headers = []
    for m in re.finditer(r"^##\s+([^\n]+)$", content, re.MULTILINE):
        full = m.group(1).strip()
        # Base-Name = alles vor erstem " (" Suffix
        base = re.split(r"\s+\(", full, maxsplit=1)[0].strip()
        headers.append((m.start(), full, base))
    return headers


def find_dups(content):
    """Finde Singleton-Sections die mehrfach mit IDENTISCHEM full-header vorkommen.

    Returns: dict {full_header: [positions]} fuer alle die count > 1 haben
             UND deren base in SINGLETON_SECTIONS ist.
    """
    headers = parse_headers(content)
    by_full = {}
    for pos, full, base in headers:
        if base in SINGLETON_SECTIONS:
            by_full.setdefault(full, []).append(pos)
    return {full: positions for full, positions in by_full.items() if len(positions) > 1}


def dedup(content, dry_run=True):
    """Dedupliziere: behalte letztes Vorkommen, suffixe fruehere.

    Returns: (new_content, list_of_changes)
    """
    dups = find_dups(content)
    if not dups:
        return content, []

    date = datetime.now().strftime("%Y%m%d")
    changes = []

    # Sammle alle Edits (pos, old_header_line, new_header_line)
    # WICHTIG: rueckwaerts anwenden damit Positionen stabil bleiben
    edits = []
    for full, positions in dups.items():
        # positions sind sortiert (re.finditer Reihenfolge). Letztes = kanonisch behalten.
        canonical_pos = positions[-1]
        for i, pos in enumerate(positions[:-1]):  # alle ausser letztes
            old_line = f"## {full}"
            new_line = f"## {full} (ARCHIV-{i+1}-{date})"
            edits.append((pos, old_line, new_line))
            changes.append({
                "section": full,
                "pos": pos,
                "action": "suffixed",
                "new": f"{full} (ARCHIV-{i+1}-{date})",
                "canonical_kept_at": canonical_pos,
            })

    if dry_run:
        return content, changes

    # Apply rueckwaerts (hoechste pos zuerst)
    edits.sort(key=lambda e: e[0], reverse=True)
    new_content = content
    for pos, old_line, new_line in edits:
        # Ersetze exakt an dieser Position (Zeile beginnt bei pos)
        line_end = new_content.find("\n", pos)
        if line_end == -1:
            line_end = len(new_content)
        actual_line = new_content[pos:line_end]
        if actual_line.strip() == old_line.strip():
            new_content = new_content[:pos] + new_line + new_content[line_end:]

    return new_content, changes


def self_test():
    """Smoke-Test mit fake Manifest."""
    sample = """# Manifest

## A_PIPELINE_STATE
old state 1

## DF_BATCH_STATE
batch stuff

## A_PIPELINE_STATE
newer state 2

## IDF_PIPELINE_STATE (Round 11)
idf a

## IDF_PIPELINE_STATE (Round 11)
idf b duplicate suffix

## BERATER_OUTPUTS.foo
legit repeat 1

## BERATER_OUTPUTS.foo
legit repeat 2
"""
    dups = find_dups(sample)
    # Erwartung: A_PIPELINE_STATE (2x), IDF_PIPELINE_STATE (Round 11) (2x)
    # NICHT BERATER_OUTPUTS.foo (kein Singleton)
    expected_dup_headers = {"A_PIPELINE_STATE", "IDF_PIPELINE_STATE (Round 11)"}
    found = set(dups.keys())
    if found != expected_dup_headers:
        print(f"[SELF-TEST FAIL] dups mismatch: found={found}, expected={expected_dup_headers}")
        return 1

    new_content, changes = dedup(sample, dry_run=False)
    # Nach dedup: jede Singleton-Section nur noch 1x bare
    new_dups = find_dups(new_content)
    if new_dups:
        print(f"[SELF-TEST FAIL] nach dedup noch dups: {list(new_dups.keys())}")
        return 1
    # BERATER_OUTPUTS.foo muss unangetastet bleiben (2x)
    if new_content.count("## BERATER_OUTPUTS.foo") != 2:
        print("[SELF-TEST FAIL] BERATER_OUTPUTS.foo wurde faelschlich angetastet")
        return 1
    # Idempotenz: erneut dedup → keine weiteren Changes
    _, changes2 = dedup(new_content, dry_run=True)
    if changes2:
        print(f"[SELF-TEST FAIL] nicht idempotent: {len(changes2)} changes beim 2. Lauf")
        return 1

    print(f"[SELF-TEST PASS] {len(changes)} Sections dedupliziert, idempotent, BERATER unangetastet")
    return 0


def main(argv):
    p = argparse.ArgumentParser(description="manifest_dedup.py — Singleton-Section-Dedup")
    p.add_argument("--manifest", help="Pfad zur Manifest-Datei")
    p.add_argument("--dry-run", action="store_true", help="Zeige Changes ohne zu schreiben")
    p.add_argument("--apply", action="store_true", help="Schreibe Changes")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv[1:])

    if args.self_test:
        return self_test()

    if not args.manifest:
        print("[ERROR] --manifest erforderlich (oder --self-test)", file=sys.stderr)
        return 1

    path = Path(args.manifest)
    if not path.exists():
        print(f"[ERROR] Manifest nicht gefunden: {path}", file=sys.stderr)
        return 1

    content = path.read_text(encoding="utf-8", errors="replace")
    dry = not args.apply  # default dry-run ausser explizit --apply

    new_content, changes = dedup(content, dry_run=dry)

    print(f"=== manifest_dedup ({'DRY-RUN' if dry else 'APPLY'}) ===")
    print(f"Manifest: {path}")
    print(f"Dup-Sections gefunden: {len(changes)}")
    for c in changes:
        print(f"  [{c['action']}] '{c['section']}' @ {c['pos']} → '{c['new']}'")

    if not changes:
        print("GREEN — keine Singleton-Dups. Nichts zu tun.")
        return 0

    if dry:
        print("\nDRY-RUN — nichts geschrieben. Mit --apply ausfuehren.")
        return 0

    # Backup + write
    backup = path.with_suffix(path.suffix + f".bak_dedup_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    backup.write_text(content, encoding="utf-8")
    path.write_text(new_content, encoding="utf-8")
    print(f"\nAPPLIED. Backup: {backup.name}")
    print(f"{len(changes)} Sections dedupliziert.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
