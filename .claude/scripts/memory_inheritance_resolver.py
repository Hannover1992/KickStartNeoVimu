#!/usr/bin/env python3
"""
memory_inheritance_resolver.py — Memory-Slot Inheritance Resolver (BL-158 AK-1..AK-5)

Loest auf, welche Memory-Files in welchem Worktree-Kontext sichtbar sind.
Implementiert die 1-Ebene-Inheritance-Walk-Regel (Q1=A) und die 3-Bucket-Scope-Konvention
(Q2=A) aus BL-158.

Inheritance-Regel (AK-1):
  Worktree-Slot → direkter Eltern-Slot per Pfad-Prefix (1 Hop max) → global default

3-Bucket-Scopes (AK-2):
  global   → vererbt zu Kind-Slots (z.B. HiL-Policy, PR-Policy)
  project  → nicht vererbt (z.B. StyleCop, Naming)
  worktree → nicht vererbt (z.B. Stage-Marker, Sprint-State)

CLI:
  python memory_inheritance_resolver.py resolve <worktree-id>
  python memory_inheritance_resolver.py check-conflict <worktree-id>
  python memory_inheritance_resolver.py report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

import yaml  # type: ignore[import]  # pyyaml

# Pfad zum claude/projects/-Verzeichnis
_PROJECTS_ROOT = Path.home() / ".claude" / "projects"
_GLOBAL_MEMORY = Path.home() / ".claude" / "global-memory"


class MemoryFile(NamedTuple):
    path: Path
    name: str
    inheritance_scope: str  # global | project | worktree
    overridable: bool
    priority: int
    deprecated: bool | str  # False oder "YYYY-MM-DD"
    type_: str  # feedback | project | reference | user


class ResolvedContext(NamedTuple):
    worktree_slot: str
    own_files: list[MemoryFile]
    inherited_files: list[MemoryFile]  # nur global-scope vom Eltern-Slot
    global_files: list[MemoryFile]
    parent_slot: str | None


def _encode_path_to_slot(path: Path) -> str:
    """Konvertiert absoluten Pfad in Claude-Slot-Bezeichner (Pfad-Encoding)."""
    s = str(path).replace(":", "").replace("/", "-").replace("\\", "-")
    # Doppelte Bindestriche normalisieren
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def _slot_to_memory_dir(slot_id: str) -> Path:
    """Gibt Pfad zum Memory-Verzeichnis eines Slots zurueck."""
    return _PROJECTS_ROOT / slot_id / "memory"


def _read_frontmatter(file: Path) -> dict:
    """Liest YAML-Frontmatter aus einem Memory-File."""
    try:
        content = file.read_text(encoding="utf-8")
    except OSError:
        return {}

    if not content.startswith("---"):
        return {}

    end = content.find("\n---", 3)
    if end == -1:
        return {}

    try:
        return yaml.safe_load(content[3:end]) or {}
    except Exception:
        return {}


def _parse_memory_file(file: Path) -> MemoryFile | None:
    """Parst ein Memory-File und extrahiert Schema-Felder."""
    fm = _read_frontmatter(file)
    if not fm:
        return None

    return MemoryFile(
        path=file,
        name=fm.get("name", file.stem),
        # Standard-Scope bei fehlenden Schema-Feldern ist project (AK-2, R5)
        inheritance_scope=fm.get("inheritance_scope", "project"),
        overridable=bool(fm.get("overridable", True)),
        priority=int(fm.get("priority", 5)),
        deprecated=fm.get("deprecated", False),
        type_=fm.get("type", "project"),
    )


def _load_slot_files(memory_dir: Path) -> list[MemoryFile]:
    """Laedt alle Memory-Files aus einem Slot-Verzeichnis."""
    if not memory_dir.is_dir():
        return []

    files = []
    for f in memory_dir.glob("*.md"):
        if f.name == "MEMORY.md":
            continue
        mf = _parse_memory_file(f)
        if mf is not None:
            files.append(mf)
    return files


def _find_parent_slot(slot_id: str) -> str | None:
    """
    Bestimmt den direkten Eltern-Slot via Pfad-Prefix-Match (1 Hop, AK-1).

    Slots sind Pfad-kodiert: C--Users-Admin-DCSRE-486 → parent: C--Users-Admin-DCSRE
    """
    all_slots = [d.name for d in _PROJECTS_ROOT.iterdir() if d.is_dir()]

    # Separatoren im Slot-Namen sind Bindestriche (aus Path-Encoding)
    # Eltern-Kandidat = laengster gemeinsamer Prefix mit mindestens einem Segment weniger
    candidates = []
    for candidate in all_slots:
        if candidate == slot_id:
            continue
        if slot_id.startswith(candidate + "-"):
            candidates.append(candidate)

    if not candidates:
        return None

    # Laengsten (spezifischsten) Match nehmen
    return max(candidates, key=len)


def resolve(worktree_slot: str) -> ResolvedContext:
    """
    Hauptfunktion: Loest Memory-Kontext fuer einen Worktree-Slot auf.

    Inheritance-Walk (AK-1 + AK-4):
      1. Eigener Slot: alle Scopes sichtbar
      2. Eltern-Slot:  nur global-scope Files sichtbar (1 Hop)
      3. Global default (~/.claude/global-memory/): alle Files sichtbar
    """
    own_dir = _slot_to_memory_dir(worktree_slot)
    own_files = _load_slot_files(own_dir)

    parent_slot = _find_parent_slot(worktree_slot)
    inherited_files: list[MemoryFile] = []

    if parent_slot:
        parent_dir = _slot_to_memory_dir(parent_slot)
        parent_files = _load_slot_files(parent_dir)
        # Nur global-scope Files vererben (AK-4 Inheritance-Matrix)
        inherited_files = [f for f in parent_files if f.inheritance_scope == "global"]

    global_files = _load_slot_files(_GLOBAL_MEMORY)

    return ResolvedContext(
        worktree_slot=worktree_slot,
        own_files=own_files,
        inherited_files=inherited_files,
        global_files=global_files,
        parent_slot=parent_slot,
    )


def check_conflict(worktree_slot: str) -> list[dict]:
    """
    Prueft auf Konflikte: gleicher Memory-Key in mehreren Quellen.

    Gibt Liste von Konflikt-Eintraegen zurueck:
    {key, sources: [slot_name], winner: "own|parent|global", reason}
    """
    ctx = resolve(worktree_slot)
    conflicts = []

    all_by_name: dict[str, list[tuple[str, MemoryFile]]] = {}

    for mf in ctx.own_files:
        all_by_name.setdefault(mf.name, []).append(("own", mf))
    for mf in ctx.inherited_files:
        all_by_name.setdefault(mf.name, []).append(("parent", mf))
    for mf in ctx.global_files:
        all_by_name.setdefault(mf.name, []).append(("global", mf))

    for key, sources in all_by_name.items():
        if len(sources) < 2:
            continue

        # Prioritaet: own > parent > global, dann priority-Wert (1 = hoeher)
        source_order = {"own": 0, "parent": 1, "global": 2}
        best = min(sources, key=lambda x: (source_order[x[0]], x[1].priority))
        winner_source, winner_file = best

        conflicts.append({
            "key": key,
            "sources": [s for s, _ in sources],
            "winner": winner_source,
            "winner_priority": winner_file.priority,
            "winner_scope": winner_file.inheritance_scope,
        })

    return conflicts


def report() -> None:
    """Gibt tabellarischen Bericht aller Slots mit Inheritance-Chain aus."""
    if not _PROJECTS_ROOT.is_dir():
        print(f"ERROR: ~/.claude/projects/ nicht gefunden: {_PROJECTS_ROOT}", file=sys.stderr)
        sys.exit(1)

    slots = sorted(d.name for d in _PROJECTS_ROOT.iterdir() if d.is_dir())
    print(f"Memory-Topology Report — {_PROJECTS_ROOT}")
    print(f"Slots total: {len(slots)}")
    print()

    for slot in slots:
        mem_dir = _slot_to_memory_dir(slot)
        files = list(mem_dir.glob("*.md")) if mem_dir.is_dir() else []
        size_kb = sum(f.stat().st_size for f in files) // 1024 if files else 0
        parent = _find_parent_slot(slot)
        parent_str = f"parent: {parent}" if parent else "parent: none (root)"

        conflicts = check_conflict(slot)
        conflict_str = f"CONFLICTS: {len(conflicts)}" if conflicts else "OK"

        print(f"  [{slot}]")
        print(f"    Files: {len(files)} | Size: {size_kb}K | {parent_str} | {conflict_str}")

    print()
    # Symlink-Check (.claude/ Ordner)
    claude_dir = Path.home() / ".claude"
    if claude_dir.is_symlink():
        print("WARNUNG: ~/.claude/ ist ein Symlink — echter Ordner benoetigt fuer Memory-Isolation")
    else:
        print("Symlink-Check: ~/.claude/ echter Ordner OK")

    # Pre-Run-Check: bl_id + vault_root
    _prerun_check()


def _prerun_check() -> None:
    """Prueft ob bl_id und vault_root gesetzt sind (BLOCKER bei leer)."""
    import os

    bl_id = os.environ.get("CLAUDE_BL_ID", "")
    vault_root = os.environ.get("CLAUDE_VAULT_ROOT", "")

    if not bl_id or not vault_root:
        missing = []
        if not bl_id:
            missing.append("CLAUDE_BL_ID")
        if not vault_root:
            missing.append("CLAUDE_VAULT_ROOT")
        print(f"Pre-Run-Check: BLOCKER — fehlende ENV-Vars: {', '.join(missing)}", file=sys.stderr)
        # Kein sys.exit hier — nur Warnung, da als Library-Funktion verwendbar
    else:
        print(f"Pre-Run-Check: bl_id={bl_id} vault_root={vault_root} OK")


def _print_resolved(ctx: ResolvedContext) -> None:
    """Gibt aufgeloesten Memory-Kontext als strukturierten Text aus."""
    print(f"Resolved context for slot: {ctx.worktree_slot}")
    print(f"Parent slot: {ctx.parent_slot or 'none (root)'}")
    print()

    print(f"Own files ({len(ctx.own_files)}):")
    for mf in sorted(ctx.own_files, key=lambda m: m.priority):
        deprecated_str = f" [DEPRECATED: {mf.deprecated}]" if mf.deprecated else ""
        print(f"  {mf.name} — scope={mf.inheritance_scope} priority={mf.priority}{deprecated_str}")

    print()
    print(f"Inherited from parent ({len(ctx.inherited_files)}, global-scope only):")
    for mf in sorted(ctx.inherited_files, key=lambda m: m.priority):
        print(f"  {mf.name} — priority={mf.priority}")

    print()
    print(f"Global default ({len(ctx.global_files)}):")
    for mf in sorted(ctx.global_files, key=lambda m: m.priority):
        print(f"  {mf.name} — priority={mf.priority}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="BL-158 Memory Inheritance Resolver")
    sub = parser.add_subparsers(dest="cmd")

    p_resolve = sub.add_parser("resolve", help="Memory-Kontext fuer einen Slot aufloesen")
    p_resolve.add_argument("worktree_slot", help="Slot-ID (Pfad-kodiert)")

    p_conflict = sub.add_parser("check-conflict", help="Konflikte in einem Slot pruefen")
    p_conflict.add_argument("worktree_slot", help="Slot-ID (Pfad-kodiert)")

    sub.add_parser("report", help="Alle Slots tabellarisch auflisten")

    args = parser.parse_args(argv)

    if args.cmd == "resolve":
        ctx = resolve(args.worktree_slot)
        _print_resolved(ctx)
        return 0

    if args.cmd == "check-conflict":
        conflicts = check_conflict(args.worktree_slot)
        if not conflicts:
            print(f"Keine Konflikte in Slot: {args.worktree_slot}")
            return 0
        print(f"Konflikte in Slot {args.worktree_slot} ({len(conflicts)}):")
        for c in conflicts:
            print(f"  {c['key']}: sources={c['sources']} winner={c['winner']}")
        return 0

    if args.cmd == "report":
        report()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
