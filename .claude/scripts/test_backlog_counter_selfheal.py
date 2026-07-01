"""
test_backlog_counter_selfheal.py — Self-Heal-Floor fuer BL-475

Tests fuer:
  1. backlog_counter_lock.scan_max_existing_bl(vault_root) -> int
  2. allocate_next_bl_id(..., floor_provider=None) — neuer optionaler kw-Param

Contract:
    scan_max_existing_bl(vault_root) -> int
        Scannt nach hoechster BL-Nummer aus drei Quellen:
          a) Ordner-Eintraege in {vault_root}/Backlog/ matching BL-(\\d+)
          b) Zeilen in {vault_root}/_backlog_index.md matching BL-(\\d+)
          c) Zeilen in {vault_root}/_backlog_index_done.md matching BL-(\\d+)
        Gibt 0 zurueck wenn keine BL-Nummern gefunden / Quellen fehlen.
        Fehlende Dateien/Ordner robust ignorieren (kein Crash).

    allocate_next_bl_id(..., floor_provider=None) -> int
        Unter dem Lock:
          base = max(read_counter(), floor_provider() if floor_provider else 0)
          new = base + 1
          write_counter(new)
          return new

Run: py -3 -m pytest .claude/scripts/test_backlog_counter_selfheal.py -v
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path so local imports work.
sys.path.insert(0, str(Path(__file__).parent))

from backlog_counter_lock import allocate_next_bl_id, scan_max_existing_bl  # noqa: E402


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_vault(tmp_path):
    """Isolated vault root for each test."""
    return tmp_path


@pytest.fixture
def counter_store():
    """Shared mutable counter with DI read/write closures (NO own locking).

    Same DI pattern as test_backlog_counter_lock.py.
    """
    store = {"value": 0}

    def read():
        return store["value"]

    def write(new_val):
        store["value"] = new_val

    return store, read, write


# ─── T_selfheal_floor_heals_behind ───────────────────────────────────────────

def test_selfheal_floor_heals_behind(tmp_vault, counter_store):
    """T_selfheal_floor_heals_behind: counter stored=450, floor_provider->476
    -> allocate returns 477 AND write_counter was called with 477.

    Beweist: faellt NICHT hinter real-max (Self-Heal-Floor greift).
    """
    store, read, write = counter_store
    store["value"] = 450

    result = allocate_next_bl_id(
        tmp_vault,
        read_counter=read,
        write_counter=write,
        floor_provider=lambda: 476,
    )

    assert result == 477, (
        f"Expected 477 (floor=476 wins over counter=450), got {result}"
    )
    assert store["value"] == 477, (
        f"Expected store==477 after write_counter(477), got {store['value']}"
    )


# ─── T_selfheal_counter_ahead_wins ───────────────────────────────────────────

def test_selfheal_counter_ahead_wins(tmp_vault, counter_store):
    """T_selfheal_counter_ahead_wins: stored=500, floor_provider->476
    -> result must be 501 (counter legitim voraus, monoton, kein Rueckwaerts).
    """
    store, read, write = counter_store
    store["value"] = 500

    result = allocate_next_bl_id(
        tmp_vault,
        read_counter=read,
        write_counter=write,
        floor_provider=lambda: 476,
    )

    assert result == 501, (
        f"Expected 501 (counter=500 wins over floor=476), got {result}"
    )
    assert store["value"] == 501, (
        f"Expected store==501, got {store['value']}"
    )


# ─── T_floor_none_is_legacy ───────────────────────────────────────────────────

def test_floor_none_is_legacy(tmp_vault, counter_store):
    """T_floor_none_is_legacy: ohne floor_provider, stored=41 -> 42.

    Regression: Default-Verhalten (floor_provider=None) bleibt byte-identisch
    zum Altverhalten (new = cur + 1).
    """
    store, read, write = counter_store
    store["value"] = 41

    result = allocate_next_bl_id(
        tmp_vault,
        read_counter=read,
        write_counter=write,
        # floor_provider absichtlich weggelassen (Default=None)
    )

    assert result == 42, (
        f"Expected 42 (legacy default, no floor_provider), got {result}"
    )
    assert store["value"] == 42, (
        f"Expected store==42, got {store['value']}"
    )


# ─── T_scan_max_folders ───────────────────────────────────────────────────────

def test_scan_max_folders(tmp_vault):
    """T_scan_max_folders: lege BL-Ordner an, scan_max_existing_bl gibt hoechste Nr.

    Legt an:
      {tmp_vault}/Backlog/BL-001-some-title/
      {tmp_vault}/Backlog/BL-042-another-title/
    Erwartet: scan_max_existing_bl(tmp_vault) == 42
    """
    backlog_dir = tmp_vault / "Backlog"
    backlog_dir.mkdir()
    (backlog_dir / "BL-001-some-title").mkdir()
    (backlog_dir / "BL-042-another-title").mkdir()

    result = scan_max_existing_bl(tmp_vault)

    assert result == 42, (
        f"Expected 42 from folders BL-001 and BL-042, got {result}"
    )


# ─── T_scan_max_includes_done_index ──────────────────────────────────────────

def test_scan_max_includes_done_index(tmp_vault):
    """T_scan_max_includes_done_index: _backlog_index_done.md mit BL-099 enthalten.

    Schreibt {tmp_vault}/_backlog_index_done.md mit Zeile die BL-099 enthaelt
    plus optional einen kleineren Backlog-Ordner (BL-005).
    Erwartet: scan_max_existing_bl(tmp_vault) == 99
    """
    # Erstelle Backlog-Ordner mit kleinerer Nummer
    backlog_dir = tmp_vault / "Backlog"
    backlog_dir.mkdir()
    (backlog_dir / "BL-005-old-item").mkdir()

    # Schreibe done-Index mit BL-099
    done_index = tmp_vault / "_backlog_index_done.md"
    done_index.write_text(
        "# Done Index\n\n"
        "- [x] BL-099 Some completed backlog item\n"
        "- [x] BL-003 Even older item\n",
        encoding="utf-8",
    )

    result = scan_max_existing_bl(tmp_vault)

    assert result == 99, (
        f"Expected 99 (from _backlog_index_done.md BL-099 > folder BL-005), got {result}"
    )


# ─── T_scan_missing_sources_robust ───────────────────────────────────────────

def test_scan_missing_sources_robust(tmp_vault):
    """T_scan_missing_sources_robust: leerer Vault -> scan_max_existing_bl == 0.

    Leerer tmp_vault (keine Backlog/, keine Index-Dateien).
    Erwartet: 0 (kein Crash, robust gegen fehlende Quellen).
    """
    # tmp_vault ist leer (kein Backlog/, keine _backlog_index*.md)
    result = scan_max_existing_bl(tmp_vault)

    assert result == 0, (
        f"Expected 0 for empty vault (no sources), got {result}"
    )
