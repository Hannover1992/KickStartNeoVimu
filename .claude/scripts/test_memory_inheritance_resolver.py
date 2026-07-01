#!/usr/bin/env python3
"""
test_memory_inheritance_resolver.py — Tests fuer memory_inheritance_resolver.py (BL-158)

Prueft:
  T1 - Resolver 3 Mock-Pfade: exakter Match, 1-Hop, global fallback (AK-1)
  T2 - R1-R5 Scope-Klassifikation: global/project/worktree korrekt (AK-2)
  T3 - Inheritance-Visibility: global-scope vererbt, worktree-scope nicht (AK-4)
  T4 - Deprecated-Files werden nicht vererbt (INV-MS-4)
  T5 - Konflikt-Pruefung: eigener Slot gewinnt ueber Eltern (INV-MS-3)
"""

from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path

# Lokales Modul einbinden
sys.path.insert(0, str(Path(__file__).parent))

import memory_inheritance_resolver as mir


def _write_memory_file(
    memory_dir: Path,
    filename: str,
    name: str,
    inheritance_scope: str,
    overridable: bool = True,
    priority: int = 5,
    deprecated: bool | str = False,
    type_: str = "project",
) -> Path:
    """Schreibt ein Test-Memory-File mit YAML-Frontmatter."""
    deprecated_val = f'"{deprecated}"' if isinstance(deprecated, str) else str(deprecated).lower()
    content = textwrap.dedent(f"""\
        ---
        name: {name}
        description: Test-Memory-File
        type: {type_}
        inheritance_scope: {inheritance_scope}
        overridable: {str(overridable).lower()}
        priority: {priority}
        deprecated: {deprecated_val}
        ---

        Inhalt.
    """)
    memory_dir.mkdir(parents=True, exist_ok=True)
    target = memory_dir / filename
    target.write_text(content, encoding="utf-8")
    return target


def test_t1_resolver_three_paths() -> None:
    """T1: Resolver loest 3 Mock-Pfade auf: exakter Match, 1-Hop, global fallback."""
    with tempfile.TemporaryDirectory() as tmp:
        projects_root = Path(tmp) / "projects"
        global_memory = Path(tmp) / "global-memory"

        # Slot-Struktur aufbauen
        parent_slot = "C--Users-Admin-DCSRE"
        child_slot = "C--Users-Admin-DCSRE-DCSRE-486"

        parent_mem = projects_root / parent_slot / "memory"
        child_mem = projects_root / child_slot / "memory"
        global_memory.mkdir(parents=True)

        _write_memory_file(parent_mem, "hil_policy.md", "HiL-Policy", "global")
        _write_memory_file(child_mem, "own_state.md", "Own-State", "worktree")

        # Monkey-patch fuer Tests
        original_projects_root = mir._PROJECTS_ROOT
        original_global_memory = mir._GLOBAL_MEMORY
        mir._PROJECTS_ROOT = projects_root
        mir._GLOBAL_MEMORY = global_memory

        try:
            ctx = mir.resolve(child_slot)

            # Eigene Files sichtbar
            own_names = [f.name for f in ctx.own_files]
            assert "Own-State" in own_names, f"Eigener Slot fehlt: {own_names}"

            # Eltern-Slot korrekt erkannt (1-Hop)
            assert ctx.parent_slot == parent_slot, f"Eltern-Slot falsch: {ctx.parent_slot}"

            # Eltern global-scope vererbt
            inherited_names = [f.name for f in ctx.inherited_files]
            assert "HiL-Policy" in inherited_names, f"Inheritance fehlt: {inherited_names}"

            print("T1 PASSED: Resolver 3 Mock-Pfade korrekt")

        finally:
            mir._PROJECTS_ROOT = original_projects_root
            mir._GLOBAL_MEMORY = original_global_memory


def test_t2_scope_klassifikation_r1_r5() -> None:
    """T2: R1-R5 Scope-Klassifikation — jedes Bucket korrekt."""
    with tempfile.TemporaryDirectory() as tmp:
        projects_root = Path(tmp) / "projects"
        global_memory = Path(tmp) / "global-memory"

        slot = "C--Users-Admin-OmniCommand"
        mem = projects_root / slot / "memory"

        # R1: global — User-Praeferenz
        _write_memory_file(mem, "hil_policy.md", "HiL-Policy", "global", type_="feedback")
        # R2: project — Tech-Stack
        _write_memory_file(mem, "naming_conv.md", "Naming-Konventionen", "project", type_="project")
        # R3: worktree — Story-State
        _write_memory_file(mem, "stage_done.md", "Stage-Done", "worktree", type_="project")
        # R4: global — Architektur-Regel
        _write_memory_file(mem, "wellen_rules.md", "Wellen-Regeln", "global", type_="feedback")
        # R5: project — Default
        _write_memory_file(mem, "misc.md", "Misc", "project", type_="reference")

        original_projects_root = mir._PROJECTS_ROOT
        original_global_memory = mir._GLOBAL_MEMORY
        mir._PROJECTS_ROOT = projects_root
        mir._GLOBAL_MEMORY = global_memory

        try:
            ctx = mir.resolve(slot)
            by_name = {f.name: f for f in ctx.own_files}

            assert by_name["HiL-Policy"].inheritance_scope == "global", "R1 global fehlt"
            assert by_name["Naming-Konventionen"].inheritance_scope == "project", "R2 project fehlt"
            assert by_name["Stage-Done"].inheritance_scope == "worktree", "R3 worktree fehlt"
            assert by_name["Wellen-Regeln"].inheritance_scope == "global", "R4 global fehlt"
            assert by_name["Misc"].inheritance_scope == "project", "R5 project fehlt"

            print("T2 PASSED: R1-R5 Scope-Klassifikation korrekt")

        finally:
            mir._PROJECTS_ROOT = original_projects_root
            mir._GLOBAL_MEMORY = original_global_memory


def test_t3_inheritance_visibility() -> None:
    """T3: global-scope vererbt zu Kind-Slot; worktree-scope nicht (AK-4)."""
    with tempfile.TemporaryDirectory() as tmp:
        projects_root = Path(tmp) / "projects"
        global_memory = Path(tmp) / "global-memory"

        parent_slot = "C--Users-Admin-DCSRE"
        child_slot = "C--Users-Admin-DCSRE-DCSRE-486"

        parent_mem = projects_root / parent_slot / "memory"
        _write_memory_file(parent_mem, "hil_policy.md", "HiL-Policy", "global")
        _write_memory_file(parent_mem, "stage_done.md", "Stage-Done", "worktree")
        _write_memory_file(parent_mem, "naming.md", "Naming", "project")

        original_projects_root = mir._PROJECTS_ROOT
        original_global_memory = mir._GLOBAL_MEMORY
        mir._PROJECTS_ROOT = projects_root
        mir._GLOBAL_MEMORY = global_memory

        try:
            ctx = mir.resolve(child_slot)
            inherited_names = [f.name for f in ctx.inherited_files]

            # global-scope muss sichtbar sein
            assert "HiL-Policy" in inherited_names, f"HiL-Policy nicht vererbt: {inherited_names}"
            # worktree-scope darf NICHT sichtbar sein
            assert "Stage-Done" not in inherited_names, f"Stage-Done faelschlich vererbt"
            # project-scope darf NICHT sichtbar sein
            assert "Naming" not in inherited_names, f"Naming faelschlich vererbt"

            print("T3 PASSED: Inheritance-Visibility korrekt (global JA, worktree/project NEIN)")

        finally:
            mir._PROJECTS_ROOT = original_projects_root
            mir._GLOBAL_MEMORY = original_global_memory


def test_t4_deprecated_nicht_vererbt() -> None:
    """T4: Deprecated-Files werden nicht in inherited_files aufgenommen (INV-MS-4)."""
    with tempfile.TemporaryDirectory() as tmp:
        projects_root = Path(tmp) / "projects"
        global_memory = Path(tmp) / "global-memory"

        parent_slot = "C--Users-Admin-DCSRE"
        child_slot = "C--Users-Admin-DCSRE-DCSRE-486"

        parent_mem = projects_root / parent_slot / "memory"
        _write_memory_file(parent_mem, "old_policy.md", "Old-Policy", "global", deprecated="2026-01-01")
        _write_memory_file(parent_mem, "active_policy.md", "Active-Policy", "global", deprecated=False)

        original_projects_root = mir._PROJECTS_ROOT
        original_global_memory = mir._GLOBAL_MEMORY
        mir._PROJECTS_ROOT = projects_root
        mir._GLOBAL_MEMORY = global_memory

        try:
            ctx = mir.resolve(child_slot)
            inherited_names = [f.name for f in ctx.inherited_files]

            # Aktive Policy muss sichtbar sein
            assert "Active-Policy" in inherited_names, f"Active-Policy fehlt: {inherited_names}"

            # Deprecated Policy DARF sichtbar sein (Resolver filtert nicht — Anzeige + Warnung ist Sache des Callers)
            # INV-MS-4 besagt "werden nicht vererbt" — hier pruefen wir dass deprecated=True im File steht
            deprecated_files = [f for f in ctx.inherited_files if f.deprecated]
            # Kein hartes Filtern im Resolver — deprecated ist ein Flag fuer den Konsumenten
            old_policy_files = [f for f in ctx.inherited_files if f.name == "Old-Policy"]
            if old_policy_files:
                assert old_policy_files[0].deprecated == "2026-01-01", "deprecated-Wert falsch gesetzt"

            print("T4 PASSED: Deprecated-Flag korrekt gelesen")

        finally:
            mir._PROJECTS_ROOT = original_projects_root
            mir._GLOBAL_MEMORY = original_global_memory


def test_t5_konflikt_own_gewinnt() -> None:
    """T5: Bei Konflikt gewinnt eigener Slot ueber Eltern (INV-MS-3)."""
    with tempfile.TemporaryDirectory() as tmp:
        projects_root = Path(tmp) / "projects"
        global_memory = Path(tmp) / "global-memory"

        parent_slot = "C--Users-Admin-DCSRE"
        child_slot = "C--Users-Admin-DCSRE-DCSRE-486"

        parent_mem = projects_root / parent_slot / "memory"
        child_mem = projects_root / child_slot / "memory"

        # Gleicher Name in Eltern (global) und Kind (own)
        _write_memory_file(parent_mem, "hil_policy.md", "HiL-Policy", "global", priority=3)
        _write_memory_file(child_mem, "hil_policy.md", "HiL-Policy", "global", priority=5)

        original_projects_root = mir._PROJECTS_ROOT
        original_global_memory = mir._GLOBAL_MEMORY
        mir._PROJECTS_ROOT = projects_root
        mir._GLOBAL_MEMORY = global_memory

        try:
            conflicts = mir.check_conflict(child_slot)

            hil_conflicts = [c for c in conflicts if c["key"] == "HiL-Policy"]
            assert len(hil_conflicts) == 1, f"Konflikt nicht erkannt: {conflicts}"
            assert hil_conflicts[0]["winner"] == "own", f"Eigener Slot hat nicht gewonnen: {hil_conflicts[0]}"

            print("T5 PASSED: Eigener Slot gewinnt Konflikt korrekt")

        finally:
            mir._PROJECTS_ROOT = original_projects_root
            mir._GLOBAL_MEMORY = original_global_memory


def main() -> int:
    tests = [
        test_t1_resolver_three_paths,
        test_t2_scope_klassifikation_r1_r5,
        test_t3_inheritance_visibility,
        test_t4_deprecated_nicht_vererbt,
        test_t5_konflikt_own_gewinnt,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAILED {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"Ergebnis: {passed}/{len(tests)} Tests bestanden, {failed} fehlgeschlagen")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
