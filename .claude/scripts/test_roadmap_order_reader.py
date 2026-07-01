#!/usr/bin/env python3
"""
test_roadmap_order_reader.py — BL-430 AK-4: ROADMAP-ORDER Reader-Verifikation

Bestätigt dass parse_roadmap_order() aus roadmap_status.py:
  1. Einen ROADMAP-ORDER:START..END Block korrekt und deterministisch parst.
  2. Die BL-IDs in der exakten Reihenfolge des Blocks liefert.
  3. Prose-BL-IDs außerhalb des Blocks ignoriert (kuratiert vs. noise).
  4. Keine Duplikate zurückgibt (1. Vorkommen gewinnt).

AK-4 = Reuse-Befund: parse_roadmap_order IST der Item-Quellen-Reader —
kein Doppel-Code nötig. Kein separater Wrapper next_bl_from_roadmap
ist required, weil roadmap_status() + next_command_for_bl() die
Roadmap-Navigation bereits deterministisch abdecken.

Run: py -3 -m pytest .claude/scripts/test_roadmap_order_reader.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import roadmap_status aus scripts-Verzeichnis
_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

import roadmap_status as rs


# ──────────────────────────────────────────────────────────────────────
# Fixture: kuratierter ROADMAP-ORDER Block mit 3 BLs in definierter Reihenfolge
# ──────────────────────────────────────────────────────────────────────

_FIXTURE_WITH_ORDER_BLOCK = """\
# ROADMAP

Dieser Abschnitt hat Prosa-Erwaehnungen von BL-999 und BL-888 die NICHT
in den Reader eingehen duerfen — die kuratierte Reihenfolge steht im Block.

ROADMAP-ORDER:START
BL-430
BL-431
BL-432
ROADMAP-ORDER:END

Nach dem Block koennte BL-777 erwaehnt werden — auch ignoriert.
"""

_FIXTURE_WITHOUT_ORDER_BLOCK = """\
# ROADMAP (kein kuratierter Block)

Phase 1: BL-430, dann BL-431
Phase 2: BL-432
BL-430 erneut erwaehnt (Duplikat soll entfernt werden).
"""

_FIXTURE_EMPTY = ""

_FIXTURE_ONLY_BLOCK = """\
ROADMAP-ORDER:START
BL-100
BL-200
BL-300
ROADMAP-ORDER:END
"""


# ──────────────────────────────────────────────────────────────────────
# AK-4 Tests (pytest-kompatibel)
# ──────────────────────────────────────────────────────────────────────

def test_ak4_order_block_parst_korrekte_reihenfolge():
    """AK-4 Kern: Fixture mit ROADMAP-ORDER Block liefert exakte geordnete BL-Liste."""
    result = rs.parse_roadmap_order(_FIXTURE_WITH_ORDER_BLOCK)
    assert result == ["BL-430", "BL-431", "BL-432"], (
        f"Erwartete geordnete Liste ['BL-430','BL-431','BL-432'], got {result!r}"
    )


def test_ak4_prose_bl_ids_ausserhalb_block_ignoriert():
    """AK-4: BL-IDs in Prosa (BL-999, BL-888, BL-777) werden ignoriert wenn Block vorhanden."""
    result = rs.parse_roadmap_order(_FIXTURE_WITH_ORDER_BLOCK)
    assert "BL-999" not in result, "BL-999 (Prosa vor Block) darf nicht in Ergebnis sein"
    assert "BL-888" not in result, "BL-888 (Prosa vor Block) darf nicht in Ergebnis sein"
    assert "BL-777" not in result, "BL-777 (Prosa nach Block) darf nicht in Ergebnis sein"


def test_ak4_deterministisch_gleiche_eingabe_gleiche_ausgabe():
    """AK-4 Determinismus: Identische Eingabe liefert immer identische Ausgabe (kein Zufalls-Sorting)."""
    result_1 = rs.parse_roadmap_order(_FIXTURE_WITH_ORDER_BLOCK)
    result_2 = rs.parse_roadmap_order(_FIXTURE_WITH_ORDER_BLOCK)
    assert result_1 == result_2, (
        f"Nicht deterministisch: 1. Call={result_1!r}, 2. Call={result_2!r}"
    )


def test_ak4_leere_eingabe_liefert_leere_liste():
    """AK-4 Edge Case: leeres Dokument -> leere Liste."""
    result = rs.parse_roadmap_order(_FIXTURE_EMPTY)
    assert result == [], f"Leere Eingabe soll [] liefern, got {result!r}"


def test_ak4_ohne_order_block_parst_prosa_deduped():
    """AK-4 Fallback: Kein ORDER-Block -> parst ganze Prosa, dedupliziert (1. Vorkommen gewinnt)."""
    result = rs.parse_roadmap_order(_FIXTURE_WITHOUT_ORDER_BLOCK)
    # BL-430 darf nur einmal vorkommen (Duplikat entfernt)
    assert result.count("BL-430") == 1, (
        f"Duplikat BL-430 soll entfernt werden, got count={result.count('BL-430')} in {result!r}"
    )
    # Reihenfolge: BL-430 vor BL-431 vor BL-432
    assert result == ["BL-430", "BL-431", "BL-432"], (
        f"Erwartete ['BL-430','BL-431','BL-432'] aus Prosa, got {result!r}"
    )


def test_ak4_only_block_drei_bls():
    """AK-4: Dokument mit nur ORDER-Block (keine Prosa) liefert die 3 BLs korrekt."""
    result = rs.parse_roadmap_order(_FIXTURE_ONLY_BLOCK)
    assert result == ["BL-100", "BL-200", "BL-300"], (
        f"Erwartete ['BL-100','BL-200','BL-300'], got {result!r}"
    )


# ──────────────────────────────────────────────────────────────────────
# AK-4 Wrapper-Check: next_bl_from_roadmap nötig?
# ──────────────────────────────────────────────────────────────────────

def test_ak4_kein_wrapper_noetig_reuse_bestaetigt():
    """AK-4 Reuse-Check: parse_roadmap_order liefert direkt die nächste BL via [0].
    Kein separater Wrapper next_bl_from_roadmap erforderlich.
    roadmap_status() + next_command_for_bl() decken Navigation deterministisch ab.
    """
    result = rs.parse_roadmap_order(_FIXTURE_ONLY_BLOCK)
    # Das erste Element ist die nächste BL in Build-Reihenfolge
    next_bl = result[0] if result else None
    assert next_bl == "BL-100", (
        f"Naechste BL aus ORDER-Block erwartet BL-100, got {next_bl!r}"
    )
    # Bestätigt: kein Wrapper nötig, direkte Reuse via result[0]


# ──────────────────────────────────────────────────────────────────────
# Standalone-Runner (analog test_a_routing_targets.py)
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess
    import sys as _sys
    result = subprocess.run(
        [_sys.executable, "-m", "pytest", __file__, "-v"],
        cwd=str(_SCRIPT_DIR.parent.parent),
    )
    _sys.exit(result.returncode)
