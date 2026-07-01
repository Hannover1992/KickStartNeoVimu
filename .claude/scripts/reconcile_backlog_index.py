#!/usr/bin/env python3
"""
reconcile_backlog_index.py  —  BL-306 AK-4 (Backlog-Index Single-Source Reconcile)

Heilt den Dual-Index-Split-Brain (BL-306):
  KANON   = Root-Index  C:/Users/Administrator/Documents/OmniCommand/_backlog_index.md
  ROGUE   = Backlog/-Index  C:/Users/Administrator/Documents/OmniCommand/Backlog/_backlog_index.md (Merge-SOURCE)

Die zwei Indizes divergieren (Root: Historie 001-230, 6/8-Spalten gemischt; Backlog/: 125 + 184-306,
6-Spalten). Dieses Script UNIONiert beide BL-Zeilen NACH BL-ID in den Root-Index — idempotent, mit
Konflikt-Report. Bei --apply: Backup beider Dateien (.bak-{ts}) + Schreiben Root + Tombstone der Backlog/-Datei.

Dry-run (Default): NUR Delta-Report, KEINE Schreib-Operation.
Apply:             python reconcile_backlog_index.py --apply --ts 2026-06-10

Konflikt-Aufloesung (beide Indizes haben dieselbe BL-ID):
  Status-Rang DONE/SUPERSEDED/DECOMPOSED > IN_PROGRESS/GATED/dormant > DRAFT/PLANNED gewinnt;
  bei gleichem Rang die Zeile mit dem juengeren updated-Datum (sonst Backlog/, da aktiver gepflegt).
  ALLE Konflikte werden im Report gelistet (kein stilles Ueberschreiben).

KEINE externen Dependencies (stdlib only). BL-306 Klasse ① Engine/Script bootstrap-direkt.
"""
import re
import sys
import os
import shutil

# BL-333: format_version-Stamp (Writer=Follow, Wert via Loader-Call). Loader-fehlt -> kein Crash.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from resolve_format_version import resolve_format_version
except ImportError:
    def resolve_format_version(typ):  # type: ignore
        return None

ROOT = r"C:/Users/Administrator/Documents/OmniCommand/_backlog_index.md"
ROGUE = r"C:/Users/Administrator/Documents/OmniCommand/Backlog/_backlog_index.md"

BL_ROW = re.compile(r"^\|\s*(BL-\d+)\s*\|")
# Status-Rang: hoeher = "weiter im Lifecycle" gewinnt bei Konflikt.
STATUS_RANK = {
    "DONE": 5, "SUPERSEDED": 5, "DECOMPOSED": 5, "ABSORBED_INTO_BL-151": 5,
    "IN_PROGRESS": 3, "GATED": 3, "dormant": 3, "FREEZE": 2,
    "DRAFT": 1, "PLANNED": 1,
}
UPDATED_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")


def parse_index(path):
    """Liefert {bl_id: raw_line} + die Zeilen-Reihenfolge + den Nicht-Tabellen-Kopf/Fuss."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    rows = {}
    for ln in lines:
        m = BL_ROW.match(ln)
        if m:
            rows[m.group(1)] = ln.rstrip()
    return rows, lines


def bl_num(bl_id):
    m = re.search(r"BL-(\d+)", bl_id)
    return int(m.group(1)) if m else 0


def status_of(row):
    # 3. Pipe-Spalte ist der Status.
    cols = [c.strip() for c in row.split("|")]
    # cols[0] = '' (vor erstem |), cols[1]=BL-ID, cols[2]=Title, cols[3]=Status
    return cols[3] if len(cols) > 3 else ""


def status_rank(row):
    st = status_of(row)
    for key, rk in STATUS_RANK.items():
        if st.startswith(key):
            return rk
    return 1


def latest_date(row):
    ds = UPDATED_RE.findall(row)
    return max(ds) if ds else "0000-00-00"


def choose(bl_id, root_row, rogue_row):
    """Konflikt-Aufloesung. Liefert (gewinner_row, quelle, begruendung)."""
    rr, gr = status_rank(root_row), status_rank(rogue_row)
    if rr != gr:
        return (root_row, "root", f"Status-Rang root({rr})>rogue({gr})") if rr > gr \
            else (rogue_row, "rogue", f"Status-Rang rogue({gr})>root({rr})")
    dr, dg = latest_date(root_row), latest_date(rogue_row)
    if dr != dg:
        return (root_row, "root", f"juenger {dr}>{dg}") if dr > dg \
            else (rogue_row, "rogue", f"juenger {dg}>{dr}")
    return rogue_row, "rogue", "gleichrangig -> aktiver Backlog/-Index"


def main():
    apply = "--apply" in sys.argv
    ts = "manual"
    if "--ts" in sys.argv:
        ts = sys.argv[sys.argv.index("--ts") + 1]

    root_rows, root_lines = parse_index(ROOT)
    rogue_rows, rogue_lines = parse_index(ROGUE)

    all_ids = set(root_rows) | set(rogue_rows)
    only_root = sorted(set(root_rows) - set(rogue_rows), key=bl_num)
    only_rogue = sorted(set(rogue_rows) - set(root_rows), key=bl_num)
    both = sorted(set(root_rows) & set(rogue_rows), key=bl_num)

    conflicts = []
    unified = {}
    for bid in all_ids:
        if bid in root_rows and bid in rogue_rows:
            win, src, why = choose(bid, root_rows[bid], rogue_rows[bid])
            unified[bid] = win
            if status_of(root_rows[bid]) != status_of(rogue_rows[bid]):
                conflicts.append((bid, status_of(root_rows[bid]), status_of(rogue_rows[bid]), src, why))
        else:
            unified[bid] = root_rows.get(bid) or rogue_rows[bid]

    print("=== BL-306 Reconcile-Report (Backlog-Index Union -> Root-Kanon) ===")
    print(f"Root-Index  : {len(root_rows)} BL-Zeilen")
    print(f"Backlog/-Idx: {len(rogue_rows)} BL-Zeilen")
    print(f"Union       : {len(unified)} BL-Zeilen")
    print(f"nur in Root (Historie, Backlog/ fehlt): {len(only_root)} -> {only_root[:12]}{'...' if len(only_root) > 12 else ''}")
    print(f"nur in Backlog/ (Root fehlt, =Drift):   {len(only_rogue)} -> {only_rogue}")
    print(f"in beiden                              : {len(both)}")
    print(f"STATUS-KONFLIKTE (beide, verschiedener Status): {len(conflicts)}")
    for bid, rs, gs, src, why in sorted(conflicts, key=lambda x: bl_num(x[0])):
        print(f"   {bid}: root='{rs}' rogue='{gs}' -> waehle {src} ({why})")

    if not apply:
        print("\n[DRY-RUN] keine Schreib-Operation. Mit --apply --ts {DATUM} ausfuehren (Backup automatisch).")
        return 0

    # --- APPLY: Backup -> Root neu schreiben (Frontmatter+Header behalten, Tabellen-Body ersetzen) -> Tombstone Rogue ---
    shutil.copy2(ROOT, ROOT + f".bak-{ts}")
    shutil.copy2(ROGUE, ROGUE + f".bak-{ts}")
    print(f"\n[APPLY] Backups: {ROOT}.bak-{ts} + {ROGUE}.bak-{ts}")

    # Root-Datei: alle Nicht-BL-Zeilen behalten, BL-Zeilen-Block durch die unionierte, BL-num-sortierte Liste ersetzen.
    # Frontmatter backlog_counter auf den hoechsten BL-num heben (Root war stale, Backlog/ trug den echten Counter).
    max_num = max(bl_num(b) for b in unified) if unified else 0
    out, inserted = [], False
    body = [unified[b] for b in sorted(unified, key=bl_num)]
    has_format_version = any(re.match(r"^format_version:", ln) for ln in root_lines)
    for ln in root_lines:
        if BL_ROW.match(ln):
            if not inserted:
                out.extend(body)
                inserted = True
            # alte BL-Zeile droppen (durch Union ersetzt)
        elif re.match(r"^backlog_counter:\s*\d+", ln):
            out.append(f"backlog_counter: {max_num}")
            print(f"[APPLY] backlog_counter -> {max_num} (war stale).")
        elif re.match(r"^backlog_last_update:", ln):
            out.append(f"backlog_last_update: '{ts}'")
            # BL-333: format_version additiv stempeln (Writer=Follow). Fehlt -> 1 Zeile;
            # vorhanden -> kein Duplikat (idempotent). Loader-fehlt (None) -> Stamp weglassen.
            if not has_format_version:
                _fv = resolve_format_version("backlog_index")
                if _fv is not None:
                    out.append(f"format_version: {_fv}")
        else:
            out.append(ln)
    if not inserted:
        out.extend(body)
    with open(ROOT, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"[APPLY] Root-Index geschrieben: {len(body)} BL-Zeilen (Kanon).")

    # Rogue -> Tombstone-Pointer.
    tomb = (
        "---\n"
        "type: backlog-index-tombstone\n"
        f"tombstoned: {ts}\n"
        "canon: C:/Users/Administrator/Documents/OmniCommand/_backlog_index.md\n"
        "---\n\n"
        "# TOMBSTONE — Diese Datei ist NICHT mehr der Kanon (BL-306)\n\n"
        "Der kanonische Backlog-Index ist der **Root-Index**:\n"
        "`C:/Users/Administrator/Documents/OmniCommand/_backlog_index.md`\n\n"
        "Diese Backlog/-Datei war eine Rogue-Akkumulation aus Bypass-Hand-Writes (Single-Writer `/_backlog` "
        "umgangen). Ihr Inhalt wurde via `reconcile_backlog_index.py --apply` in den Root-Index unioniert. "
        "NEUE BL-Items NUR via `/_backlog` (schreibt nach Root). Pre-Tombstone-Snapshot: "
        f"`_backlog_index.md.bak-{ts}`.\n"
    )
    with open(ROGUE, "w", encoding="utf-8") as f:
        f.write(tomb)
    print(f"[APPLY] Backlog/-Index -> Tombstone-Pointer auf Root.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
