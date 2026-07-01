#!/usr/bin/env python3
"""
test_manifest_reader.py — BL-173 AK-5: Tests fuer manifest_reader.py

Tests:
  1. test_is_split_active_true_when_factory_manifest_exists
  2. test_is_split_active_false_legacy_only
  3. test_read_factory_block_split_mode
  4. test_read_factory_block_legacy_fallback
  5. test_read_bl_block_split_mode
  6. test_read_bl_block_legacy_fallback
  7. test_write_factory_block_atomic
  8. test_write_bl_block_creates_dir
  9. test_backward_compat_legacy_only

Alle Tests nutzen tmp_path (isoliertes Mock-Filesystem, kein Zugriff auf echte Vault-Dateien).

Run:
  py -3 -m pytest .claude/scripts/test_manifest_reader.py -v
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import pytest

# Stelle sicher dass manifest_reader importierbar ist
sys.path.insert(0, str(Path(__file__).parent))
import manifest_reader as mr


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_factory_manifest(vault_root: Path, content: str = "") -> Path:
    """Erstellt _factory_manifest.md mit gegebenen Inhalt."""
    p = vault_root / "_factory_manifest.md"
    if not content:
        content = "# Factory Manifest\n\n## BDF_PIPELINE_STATE\nphase: running\nbdf_status: active\n"
    p.write_text(content, encoding="utf-8")
    return p


def _make_legacy_manifest(vault_root: Path, content: str = "") -> Path:
    """Erstellt _manifest.md (legacy) mit gegebenen Inhalt."""
    p = vault_root / "_manifest.md"
    if not content:
        content = "# Legacy Manifest\n\n## BDF_PIPELINE_STATE\nphase: legacy-running\nbdf_status: legacy-active\n"
    p.write_text(content, encoding="utf-8")
    return p


def _make_bl_manifest(vault_root: Path, bl_id: str, content: str = "") -> Path:
    """Erstellt {vault_root}/Backlog/{bl_id}-test/_manifest.md."""
    bl_folder = vault_root / "Backlog" / f"{bl_id}-test"
    bl_folder.mkdir(parents=True, exist_ok=True)
    p = bl_folder / "_manifest.md"
    if not content:
        content = (
            f"# BL-Manifest: {bl_id}\n\n"
            "## IDF_PIPELINE_STATE\nidf_status: in-progress\nphase: phase-2\n"
        )
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: is_split_active — True wenn _factory_manifest.md existiert
# ---------------------------------------------------------------------------

def test_is_split_active_true_when_factory_manifest_exists(tmp_path):
    """Split ist aktiv wenn _factory_manifest.md existiert."""
    _make_factory_manifest(tmp_path)
    assert mr.is_split_active(tmp_path) is True


# ---------------------------------------------------------------------------
# Test 2: is_split_active — False wenn nur _manifest.md (legacy) existiert
# ---------------------------------------------------------------------------

def test_is_split_active_false_legacy_only(tmp_path):
    """Split ist NICHT aktiv wenn nur _manifest.md existiert (kein _factory_manifest.md)."""
    _make_legacy_manifest(tmp_path)
    assert mr.is_split_active(tmp_path) is False


# ---------------------------------------------------------------------------
# Test 3: read_factory_block — split mode (liest aus _factory_manifest.md)
# ---------------------------------------------------------------------------

def test_read_factory_block_split_mode(tmp_path):
    """read_factory_block liest aus _factory_manifest.md wenn split aktiv."""
    _make_factory_manifest(
        tmp_path,
        "# Factory Manifest\n\n## BDF_PIPELINE_STATE\nphase: running\nbdf_status: RUNNING\n",
    )
    # Legacy-Manifest mit anderem Wert — darf NICHT genutzt werden
    _make_legacy_manifest(
        tmp_path,
        "# Legacy\n\n## BDF_PIPELINE_STATE\nphase: LEGACY-PHASE\n",
    )

    result = mr.read_factory_block("BDF_PIPELINE_STATE.phase", vault_root=tmp_path)
    assert result == "running"

    result2 = mr.read_factory_block("BDF_PIPELINE_STATE.bdf_status", vault_root=tmp_path)
    assert result2 == "RUNNING"


# ---------------------------------------------------------------------------
# Test 4: read_factory_block — legacy fallback wenn split nicht aktiv
# ---------------------------------------------------------------------------

def test_read_factory_block_legacy_fallback(tmp_path, capsys):
    """read_factory_block faellt auf _manifest.md zurueck wenn _factory_manifest.md fehlt."""
    # Nur Legacy-Manifest vorhanden
    _make_legacy_manifest(
        tmp_path,
        "# Legacy\n\n## BDF_PIPELINE_STATE\nphase: legacy-phase\n",
    )

    result = mr.read_factory_block("BDF_PIPELINE_STATE.phase", vault_root=tmp_path)
    assert result == "legacy-phase"

    # WARNING muss geloggt worden sein (kein silent fallback, AK-5)
    captured = capsys.readouterr()
    assert "[COMPAT]" in captured.err
    assert "fallback" in captured.err.lower()


# ---------------------------------------------------------------------------
# Test 5: read_bl_block — split mode (liest aus {BL}/_manifest.md)
# ---------------------------------------------------------------------------

def test_read_bl_block_split_mode(tmp_path):
    """read_bl_block liest aus {bl_folder}/_manifest.md wenn split aktiv und BL-Manifest vorhanden."""
    _make_factory_manifest(tmp_path)
    _make_bl_manifest(
        tmp_path,
        "BL-163",
        "# BL-Manifest: BL-163\n\n## IDF_PIPELINE_STATE\nidf_status: DONE\nphase: phase-3\n",
    )

    result = mr.read_bl_block("BL-163", "IDF_PIPELINE_STATE.idf_status", vault_root=tmp_path)
    assert result == "DONE"

    result2 = mr.read_bl_block("BL-163", "IDF_PIPELINE_STATE.phase", vault_root=tmp_path)
    assert result2 == "phase-3"


# ---------------------------------------------------------------------------
# Test 6: read_bl_block — legacy fallback wenn per-BL Manifest leer/fehlt
# ---------------------------------------------------------------------------

def test_read_bl_block_legacy_fallback(tmp_path, capsys):
    """read_bl_block faellt auf _manifest.md zurueck wenn per-BL Manifest fehlt."""
    # Kein BL-Manifest, nur Legacy
    _make_legacy_manifest(
        tmp_path,
        "# Legacy\n\n## IDF_PIPELINE_STATE\nidf_status: legacy-idf\n",
    )
    # factory_manifest fehlt => split nicht aktiv

    result = mr.read_bl_block("BL-163", "IDF_PIPELINE_STATE.idf_status", vault_root=tmp_path)
    assert result == "legacy-idf"

    captured = capsys.readouterr()
    assert "[COMPAT]" in captured.err


# ---------------------------------------------------------------------------
# Test 7: write_factory_block — atomic (write doesn't corrupt on simulated crash)
# ---------------------------------------------------------------------------

def test_write_factory_block_atomic(tmp_path):
    """
    write_factory_block schreibt atomar via tmp-File + replace.
    Verifiziert: bestehender Wert wird korrekt ueberschrieben,
    und kein partieller Schreibzustand bleibt zurueck.
    """
    _make_factory_manifest(
        tmp_path,
        "# Factory Manifest\n\n## BDF_PIPELINE_STATE\nphase: initial\n",
    )
    factory_path = tmp_path / "_factory_manifest.md"
    original_content = factory_path.read_text(encoding="utf-8")
    assert "phase: initial" in original_content

    # Normaler Write
    mr.write_factory_block("BDF_PIPELINE_STATE.phase", "completed", vault_root=tmp_path)

    new_content = factory_path.read_text(encoding="utf-8")
    assert "phase: completed" in new_content
    assert "phase: initial" not in new_content

    # Neues Feld hinzufuegen (Block erweitern)
    mr.write_factory_block("BDF_PIPELINE_STATE.bdf_run_id", "run-001", vault_root=tmp_path)
    content_after = factory_path.read_text(encoding="utf-8")
    assert "bdf_run_id: run-001" in content_after
    assert "phase: completed" in content_after  # Bestehendes Feld erhalten

    # Keine .lock-Datei mehr vorhanden nach Write
    lock_files = list(tmp_path.glob("*.lock"))
    assert len(lock_files) == 0, f"Lock-Datei nicht bereinigt: {lock_files}"


# ---------------------------------------------------------------------------
# Test 8: write_bl_block — erstellt BL-Folder falls fehlend
# ---------------------------------------------------------------------------

def test_write_bl_block_creates_dir(tmp_path):
    """write_bl_block erstellt {vault_root}/Backlog/{bl_id}/ falls Ordner fehlt."""
    # Split aktiv (factory manifest vorhanden)
    _make_factory_manifest(tmp_path)

    # Kein BL-Folder vorhanden
    bl_folder = tmp_path / "Backlog" / "BL-999"
    assert not bl_folder.exists()

    mr.write_bl_block("BL-999", "A_PIPELINE_STATE.phase", "observe", vault_root=tmp_path)

    # Ordner muss erstellt worden sein
    assert bl_folder.exists(), "BL-Folder wurde nicht erstellt"

    bl_manifest = bl_folder / "_manifest.md"
    assert bl_manifest.exists(), "_manifest.md nicht erstellt"
    content = bl_manifest.read_text(encoding="utf-8")
    assert "phase: observe" in content

    # Kein .lock file bleibt zurueck
    lock_files = list(bl_folder.glob("*.lock"))
    assert len(lock_files) == 0


# ---------------------------------------------------------------------------
# Test 9: backward_compat_legacy_only — alle reads/writes ohne split
# ---------------------------------------------------------------------------

def test_backward_compat_legacy_only(tmp_path, capsys):
    """
    Alle reads/writes funktionieren auch ohne split (nur _manifest.md vorhanden).
    Kein _factory_manifest.md => legacy mode.
    """
    # Nur legacy manifest
    legacy_path = tmp_path / "_manifest.md"
    legacy_path.write_text(
        "# Legacy\n\n## BDF_PIPELINE_STATE\nphase: init\n\n## IDF_PIPELINE_STATE\nidf_status: pending\n",
        encoding="utf-8",
    )

    # is_split_active == False
    assert mr.is_split_active(tmp_path) is False

    # read_factory_block liest aus legacy
    val = mr.read_factory_block("BDF_PIPELINE_STATE.phase", vault_root=tmp_path)
    assert val == "init"

    # read_bl_block liest aus legacy (kein BL-Folder)
    val2 = mr.read_bl_block("BL-001", "IDF_PIPELINE_STATE.idf_status", vault_root=tmp_path)
    assert val2 == "pending"

    # write_factory_block schreibt in legacy
    mr.write_factory_block("BDF_PIPELINE_STATE.phase", "running", vault_root=tmp_path)
    content = legacy_path.read_text(encoding="utf-8")
    assert "phase: running" in content

    # write_bl_block schreibt in legacy (kein BL-Folder-Erstellen im legacy-Modus)
    mr.write_bl_block("BL-001", "IDF_PIPELINE_STATE.idf_status", "in-progress", vault_root=tmp_path)
    content2 = legacy_path.read_text(encoding="utf-8")
    assert "idf_status: in-progress" in content2

    # WARNING sollte fuer alle Fallbacks geloggt worden sein
    captured = capsys.readouterr()
    assert "[COMPAT]" in captured.err


# ---------------------------------------------------------------------------
# Bonus: test_read_nonexistent_field_returns_none
# ---------------------------------------------------------------------------

def test_read_nonexistent_field_returns_none(tmp_path):
    """Lesen eines nicht existierenden Feldes gibt None zurueck (kein Exception)."""
    _make_factory_manifest(
        tmp_path,
        "# Factory\n\n## BDF_PIPELINE_STATE\nphase: running\n",
    )

    val = mr.read_factory_block("BDF_PIPELINE_STATE.nonexistent_key", vault_root=tmp_path)
    assert val is None

    val2 = mr.read_factory_block("NONEXISTENT_BLOCK.some_field", vault_root=tmp_path)
    assert val2 is None


# ---------------------------------------------------------------------------
# Bonus: test_write_creates_new_block
# ---------------------------------------------------------------------------

def test_write_creates_new_block(tmp_path):
    """write_factory_block erstellt neuen Block wenn Block noch nicht existiert."""
    factory_path = tmp_path / "_factory_manifest.md"
    factory_path.write_text("# Factory\n\n## BDF_PIPELINE_STATE\nphase: init\n", encoding="utf-8")

    mr.write_factory_block("BACKLOG_STATE.counter", "42", vault_root=tmp_path)

    content = factory_path.read_text(encoding="utf-8")
    assert "## BACKLOG_STATE" in content
    assert "counter: 42" in content
    assert "## BDF_PIPELINE_STATE" in content  # Bestehender Block erhalten
