#!/usr/bin/env python3
"""BL-348: Backlog-Index-Honesty-Verifier (AK-4 Drift=0 Gate, reusable Engine-Health-Asset).

Prueft den _backlog_index.md gegen Drift=0:
  - AK-1: Status-Spalte (cells[3]) IN kanonischem Vokabular (Node-Frontmatter = Wahrheit).
  - AK-2: jede BL-Daten-Zeile hat exakt die Schema-Spaltenzahl (keine eingebetteten Pipes -> Spalten-Shift).
  - AK-3: keine doppelten BL-IDs (ID-Kollisionen).

Exit 0 = Drift=0 (GREEN), Exit 1 = Violations (RED). --json fuer Maschinen-Output.
Aufruf: python backlog_index_honesty.py --index {vault}/_backlog_index.md [--json]
"""
import argparse
import json
import re
import sys

CANONICAL_STATUS = {
    "DONE", "DRAFT", "SUPERSEDED", "DECOMPOSED", "IN_PROGRESS",
    "READY", "PLANNED", "GATED", "dormant", "ARCHIVED_ID_REUSED",
    "DEPRECATED", "HOLD",  # BL-348/BL-442: legit Lifecycle-Stati (von Lane-A/C genutzt 2026-06-20).
    # HINWEIS BL-442 GAP-3: der shared _backlog_index.md ist von 3 Lanes concurrent beschrieben ->
    # Rest-Drift (z.B. "DONE (done)"-Format anderer Lanes) ist NICHT von einer Lane allein heilbar;
    # braucht single-writer/Vokabular-Kanon der Koordinations-Schicht (BL-442). Verifier = Detektor.
}
BL_ROW_RE = re.compile(r"^\|\s*(BL-\d+)\s*\|")


def parse_rows(text):
    """Liefert (lineno, bl_id, cells[]) je BL-Datenzeile (Pipe-getrennt, Rand-Leerzellen entfernt)."""
    rows = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not BL_ROW_RE.match(line):
            continue
        # Split an Pipes; fuehrendes/abschliessendes leeres Feld droppen
        parts = line.split("|")
        if parts and parts[0].strip() == "":
            parts = parts[1:]
        if parts and parts[-1].strip() == "":
            parts = parts[:-1]
        cells = [c.strip() for c in parts]
        rows.append((lineno, cells[0] if cells else "", cells))
    return rows


def check(index_path):
    text = open(index_path, encoding="utf-8").read()
    rows = parse_rows(text)
    # BL-348: ZWEI legitime Formate koexistieren — 6-col (alt: BL|Titel|Status|Pfad|created|updated)
    # und 8-col (neu: + priority + reifegrad). Status ist in BEIDEN cells[2]. "malformed" = Spaltenzahl
    # WEDER 6 NOCH 8 (echter Pipe-Shift, z.B. BL-327=9). Format-Evolution ist KEINE Malformation.
    VALID_COLS = {6, 8}
    schema_cols = "6|8 (mixed legit)"

    violations = {"non_canonical_status": [], "malformed_rows": [], "id_collisions": []}
    seen = {}
    for lineno, bl_id, cells in rows:
        if len(cells) not in VALID_COLS:
            violations["malformed_rows"].append(
                {"line": lineno, "bl": bl_id, "cols": len(cells), "expected": "6 or 8"}
            )
            continue  # Spalten-Shift -> Status-Check unzuverlaessig
        # AK-1 Status-Spalte = cells[2] in beiden Formaten
        status = cells[2] if len(cells) > 2 else ""
        if status not in CANONICAL_STATUS:
            violations["non_canonical_status"].append(
                {"line": lineno, "bl": bl_id, "status": status}
            )
        # AK-3 ID-Kollision
        seen.setdefault(bl_id, []).append(lineno)
    for bl_id, lines in seen.items():
        if len(lines) > 1:
            violations["id_collisions"].append({"bl": bl_id, "lines": lines})

    total = sum(len(v) for v in violations.values())
    return schema_cols, violations, total


def main():
    ap = argparse.ArgumentParser(description="Backlog-Index-Honesty-Verifier (BL-348 AK-4)")
    ap.add_argument("--index", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    schema_cols, violations, total = check(args.index)
    if args.json:
        print(json.dumps({"schema_cols": schema_cols, "total": total, "violations": violations}, indent=2))
    else:
        print(f"Schema-Spalten: {schema_cols}")
        for k, v in violations.items():
            print(f"{k}: {len(v)}")
            for item in v[:30]:
                print(f"   {item}")
        print(f"TOTAL Violations: {total} -> {'GREEN (Drift=0)' if total == 0 else 'RED'}")
    sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
