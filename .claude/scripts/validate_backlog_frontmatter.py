#!/usr/bin/env python3
"""
validate_backlog_frontmatter.py  —  BL-306 AK-3 (Schema-Normierung / Drift-Report)

Prueft die Frontmatter aller flachen Backlog/BL-*.md-Knoten gegen den Minimal-Vertrag:
  PFLICHT: id, title, status, reifegrad, created
  DRIFT:   `bl_id:` statt `id:` (285/295/287-Erbe) — beide vorhanden ok, NUR bl_id = Drift.

Read-only Report (kein Auto-Fix — Fixes sind deliberate, da Frontmatter-Edits inhaltlich sind).
  python validate_backlog_frontmatter.py
"""
import re
import glob
import os
import sys

# BL-333: migration_disposition-WARN-Haken (non-blocking, additiv zu REQUIRED).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from resolve_format_version import check_migration_disposition
except ImportError:
    def check_migration_disposition(fm):  # type: ignore
        return []

BL_DIR = r"C:/Users/Administrator/Documents/OmniCommand/Backlog"
REQUIRED = ["id", "title", "status", "reifegrad", "created"]


def frontmatter(path):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---", txt, re.DOTALL)
    if not m:
        return None
    fm = {}
    for ln in m.group(1).splitlines():
        km = re.match(r"^([a-zA-Z_][\w-]*):", ln)
        if km:
            fm[km.group(1)] = ln.split(":", 1)[1].strip()
    return fm


def main():
    files = sorted(glob.glob(os.path.join(BL_DIR, "BL-*.md")))
    miss_id, bl_id_drift, miss_fields, no_fm = [], [], [], []
    md_warn = []  # BL-333: migration_disposition fehlt (WARN, non-blocking)
    for fp in files:
        name = os.path.basename(fp)
        fm = frontmatter(fp)
        if fm is None:
            no_fm.append(name)
            continue
        if "id" not in fm:
            (bl_id_drift if "bl_id" in fm else miss_id).append(name)
        missing = [k for k in REQUIRED if k not in fm and not (k == "id" and "bl_id" in fm)]
        if missing:
            miss_fields.append((name, missing))
        # BL-333: WARN-Haken — additiv, NIE blockierend (REQUIRED unveraendert).
        if check_migration_disposition(fm):
            md_warn.append(name)

    print(f"=== BL-306 AK-3 Frontmatter-Schema-Report ({len(files)} Dateien) ===")
    print(f"ohne Frontmatter           : {len(no_fm)} {no_fm}")
    print(f"id/bl_id-Drift (nur bl_id) : {len(bl_id_drift)} {bl_id_drift}")
    print(f"weder id noch bl_id        : {len(miss_id)} {miss_id}")
    print(f"Pflichtfeld-Luecken        : {len(miss_fields)}")
    for name, missing in miss_fields[:25]:
        print(f"   {name}: fehlt {missing}")
    if len(miss_fields) > 25:
        print(f"   ... +{len(miss_fields) - 25} weitere")
    # BL-333: WARN — migration_disposition fehlt (non-blocking, exit bleibt unveraendert).
    print(f"WARN migration_disposition : {len(md_warn)} (fehlt; non-blocking)")
    clean = len(files) - len(no_fm) - len(bl_id_drift) - len(miss_id) - len(set(n for n, _ in miss_fields))
    print(f"\n~sauber (Heuristik): {clean}/{len(files)}")


if __name__ == "__main__":
    main()
