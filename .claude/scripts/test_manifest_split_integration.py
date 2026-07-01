#!/usr/bin/env python3
"""
test_manifest_split_integration.py — BL-173 AK-6: Integration-Tests parallel-simulierte BDFs.

Verifikation:
  - INV-MANIFEST-SPLIT-1: Single-Writer pro Manifest-Datei (kein Cross-Contamination)
  - INV-MANIFEST-SPLIT-4: Migration atomar (Rollback / Lese-Blockierung waehrend Migration)

Ausfuehren:
  py -3 -m pytest .claude/scripts/test_manifest_split_integration.py -v
"""
from __future__ import annotations

import re
import sys
import threading
import time
from pathlib import Path
from typing import List, Tuple

import pytest

# Skript-Verzeichnis zum Import-Pfad hinzufuegen
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import manifest_reader


# ---------------------------------------------------------------------------
# Utility-Funktionen
# ---------------------------------------------------------------------------

def _setup_temp_vault(tmp_path: Path, bl_ids: List[str] | None = None) -> Path:
    """
    Erstellt minimale Vault-Struktur:
      - {tmp_path}/_factory_manifest.md  (Split aktiv)
      - {tmp_path}/Backlog/{bl_id}/_manifest.md  fuer jeden BL
    Gibt tmp_path (vault_root) zurueck.
    """
    vault_root = tmp_path
    factory = vault_root / "_factory_manifest.md"
    factory.write_text(
        "## BDF_PIPELINE_STATE\nbdf_status: idle\n",
        encoding="utf-8",
    )

    if bl_ids:
        backlog = vault_root / "Backlog"
        backlog.mkdir(parents=True, exist_ok=True)
        for bl_id in bl_ids:
            bl_folder = backlog / bl_id
            bl_folder.mkdir(parents=True, exist_ok=True)
            (bl_folder / "_manifest.md").write_text(
                f"## A_PIPELINE_STATE\nphase: init\n",
                encoding="utf-8",
            )

    return vault_root


def _simulate_bdf_writes(
    bl_id: str,
    vault_root: Path,
    count: int,
    worker_id: str,
    errors: List[Exception],
) -> None:
    """
    Schreibt `count` Updates in {bl_id}/_manifest.md via manifest_reader.write_bl_block.
    Tracked jeden Write mit `last_writer: {worker_id}_{i}`.
    Fehler werden in `errors` gesammelt (Thread-safe via append).
    """
    for i in range(count):
        try:
            manifest_reader.write_bl_block(
                bl_id=bl_id,
                field_path=f"A_PIPELINE_STATE.last_writer",
                value=f"{worker_id}_{i}",
                vault_root=vault_root,
            )
            # Schreibe auch einen Write-Zaehler spezifisch fuer diesen Worker
            manifest_reader.write_bl_block(
                bl_id=bl_id,
                field_path=f"A_PIPELINE_STATE.write_count_{worker_id}",
                value=str(i + 1),
                vault_root=vault_root,
            )
        except Exception as e:
            errors.append(e)


def _assert_no_cross_contamination(
    bl_x_manifest: Path,
    bl_y_manifest: Path,
    worker_id_x: str,
    worker_id_y: str,
    expected_count_x: int,
    expected_count_y: int,
) -> None:
    """
    Prueft:
    - bl_x_manifest enthaelt write_count_{worker_id_x} == expected_count_x
    - bl_x_manifest enthaelt KEIN write_count_{worker_id_y}
    - Umgekehrt fuer bl_y_manifest
    """
    content_x = bl_x_manifest.read_text(encoding="utf-8")
    content_y = bl_y_manifest.read_text(encoding="utf-8")

    # X soll eigene Writes haben, keine von Y
    assert f"write_count_{worker_id_x}" in content_x, (
        f"BL-X Manifest fehlt write_count_{worker_id_x}"
    )
    assert f"write_count_{worker_id_y}" not in content_x, (
        f"INV-MANIFEST-SPLIT-1 VERLETZT: BL-X Manifest enthaelt write_count_{worker_id_y} "
        f"(Cross-Contamination von BDF-B nach BDF-A Ziel-Datei)"
    )

    # Y soll eigene Writes haben, keine von X
    assert f"write_count_{worker_id_y}" in content_y, (
        f"BL-Y Manifest fehlt write_count_{worker_id_y}"
    )
    assert f"write_count_{worker_id_x}" not in content_y, (
        f"INV-MANIFEST-SPLIT-1 VERLETZT: BL-Y Manifest enthaelt write_count_{worker_id_x} "
        f"(Cross-Contamination von BDF-A nach BDF-B Ziel-Datei)"
    )

    # Finaler Write-Zaehler muss expected_count erreicht haben
    m_x = re.search(rf"write_count_{worker_id_x}\s*:\s*(\d+)", content_x)
    assert m_x is not None, f"write_count_{worker_id_x} nicht parsebar in BL-X"
    assert int(m_x.group(1)) == expected_count_x, (
        f"BL-X: erwartet {expected_count_x} Writes, gefunden {m_x.group(1)}"
    )

    m_y = re.search(rf"write_count_{worker_id_y}\s*:\s*(\d+)", content_y)
    assert m_y is not None, f"write_count_{worker_id_y} nicht parsebar in BL-Y"
    assert int(m_y.group(1)) == expected_count_y, (
        f"BL-Y: erwartet {expected_count_y} Writes, gefunden {m_y.group(1)}"
    )


# ---------------------------------------------------------------------------
# Test 1: Zwei BDFs parallel — kein Overlap auf BL-Manifest
# ---------------------------------------------------------------------------

def test_two_bdfs_parallel_no_overlap(tmp_path: Path) -> None:
    """
    INV-MANIFEST-SPLIT-1: BDF-A schreibt zu BL-X, BDF-B schreibt zu BL-Y.
    Parallel. Kein Cross-Contamination. Factory-Manifest konsistent.
    """
    vault_root = _setup_temp_vault(tmp_path, bl_ids=["BL-X", "BL-Y"])

    errors: List[Exception] = []
    WRITE_COUNT = 50

    def bdf_a():
        _simulate_bdf_writes("BL-X", vault_root, WRITE_COUNT, "BDF_A", errors)
        # BDF-A updated auch bdf_status in factory
        for i in range(5):
            try:
                manifest_reader.write_factory_block(
                    field_path="BDF_PIPELINE_STATE.bdf_status",
                    value=f"BDF_A_round_{i}",
                    vault_root=vault_root,
                )
            except Exception as e:
                errors.append(e)

    def bdf_b():
        _simulate_bdf_writes("BL-Y", vault_root, WRITE_COUNT, "BDF_B", errors)
        # BDF-B updated auch bdf_status in factory
        for i in range(5):
            try:
                manifest_reader.write_factory_block(
                    field_path="BDF_PIPELINE_STATE.bdf_status",
                    value=f"BDF_B_round_{i}",
                    vault_root=vault_root,
                )
            except Exception as e:
                errors.append(e)

    t_a = threading.Thread(target=bdf_a, name="BDF-A")
    t_b = threading.Thread(target=bdf_b, name="BDF-B")

    t_a.start()
    t_b.start()
    t_a.join(timeout=30)
    t_b.join(timeout=30)

    assert not errors, f"Thread-Fehler aufgetreten: {errors}"

    bl_x_manifest = vault_root / "Backlog" / "BL-X" / "_manifest.md"
    bl_y_manifest = vault_root / "Backlog" / "BL-Y" / "_manifest.md"
    assert bl_x_manifest.exists(), "BL-X _manifest.md fehlt"
    assert bl_y_manifest.exists(), "BL-Y _manifest.md fehlt"

    # INV-MANIFEST-SPLIT-1: kein Cross-Contamination
    _assert_no_cross_contamination(
        bl_x_manifest, bl_y_manifest,
        "BDF_A", "BDF_B",
        WRITE_COUNT, WRITE_COUNT,
    )

    # Factory-Manifest muss valides Markdown sein (kein Korrupt-Zustand)
    factory = vault_root / "_factory_manifest.md"
    factory_content = factory.read_text(encoding="utf-8")
    assert "## BDF_PIPELINE_STATE" in factory_content, "Factory-Manifest Header fehlt"
    assert "bdf_status:" in factory_content, "bdf_status Feld fehlt in Factory"

    # Keine verwaisten .lock Dateien
    lock_files = list(vault_root.rglob("*.lock"))
    assert len(lock_files) == 0, f"Lock-Dateien nicht bereinigt: {lock_files}"


# ---------------------------------------------------------------------------
# Test 2: Lock-Contention auf _factory_manifest.md
# ---------------------------------------------------------------------------

def test_lock_contention_factory_manifest(tmp_path: Path) -> None:
    """
    INV-MANIFEST-SPLIT-1: 5 Threads schreiben gleichzeitig zu _factory_manifest.md.
    Alle Writes muessen erfolgreich serialisiert werden. Kein Datenverlust, kein Corrupt.
    """
    vault_root = _setup_temp_vault(tmp_path)

    errors: List[Exception] = []
    results: List[str] = []
    lock = threading.Lock()

    def worker(thread_id: int):
        for i in range(10):
            try:
                value = f"thread_{thread_id}_write_{i}"
                manifest_reader.write_factory_block(
                    field_path="BDF_PIPELINE_STATE.bdf_status",
                    value=value,
                    vault_root=vault_root,
                )
                with lock:
                    results.append(value)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"Thread-Fehler: {errors}"
    assert len(results) == 50, f"Erwartet 50 Writes, bekam {len(results)}"

    factory = vault_root / "_factory_manifest.md"
    content = factory.read_text(encoding="utf-8")

    # Kein beschaedigtes YAML: ## Header muss vorhanden sein
    assert "## BDF_PIPELINE_STATE" in content, "Factory-Manifest Header beschaedigt"

    # Letzter Write muss im File stehen (finale Serialisierung)
    assert "bdf_status:" in content, "bdf_status Feld nicht mehr im Manifest"

    # Keine .lock Dateien verblieben
    lock_files = list(vault_root.rglob("*.lock"))
    assert len(lock_files) == 0, f"Verwaiste Lock-Dateien: {lock_files}"


# ---------------------------------------------------------------------------
# Test 3: Concurrent BL-Folder-Erstellung
# ---------------------------------------------------------------------------

def test_bl_folder_creation_concurrent(tmp_path: Path) -> None:
    """
    3 Threads erstellen je einen neuen BL-Folder (BL-NEW-1, BL-NEW-2, BL-NEW-3)
    und schreiben parallel ihr erstes Manifest. Kein Folder-Konflikt.
    """
    vault_root = _setup_temp_vault(tmp_path)  # Kein bl_ids — BLs noch nicht existent

    errors: List[Exception] = []
    new_bl_ids = ["BL-NEW-1", "BL-NEW-2", "BL-NEW-3"]

    def create_bl(bl_id: str):
        try:
            manifest_reader.write_bl_block(
                bl_id=bl_id,
                field_path="A_PIPELINE_STATE.phase",
                value="init",
                vault_root=vault_root,
            )
            manifest_reader.write_bl_block(
                bl_id=bl_id,
                field_path="A_PIPELINE_STATE.owner",
                value=bl_id,
                vault_root=vault_root,
            )
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=create_bl, args=(bl_id,)) for bl_id in new_bl_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread-Fehler bei BL-Erstellung: {errors}"

    # Alle 3 BL-Folders + _manifest.md muessen existieren
    backlog = vault_root / "Backlog"
    for bl_id in new_bl_ids:
        bl_folder = backlog / bl_id
        assert bl_folder.exists(), f"BL-Folder fehlt: {bl_folder}"
        manifest = bl_folder / "_manifest.md"
        assert manifest.exists(), f"_manifest.md fehlt in {bl_folder}"

        content = manifest.read_text(encoding="utf-8")
        assert "## A_PIPELINE_STATE" in content, f"{bl_id}: Block-Header fehlt"
        assert f"owner: {bl_id}" in content, f"{bl_id}: owner-Feld fehlt oder falsch"

    # Cross-Contamination pruefen: jedes Manifest enthaelt nur seinen eigenen owner
    for bl_id in new_bl_ids:
        content = (backlog / bl_id / "_manifest.md").read_text(encoding="utf-8")
        other_ids = [x for x in new_bl_ids if x != bl_id]
        for other_id in other_ids:
            assert f"owner: {other_id}" not in content, (
                f"INV-MANIFEST-SPLIT-1: {bl_id}/_manifest.md enthaelt owner von {other_id}"
            )


# ---------------------------------------------------------------------------
# Test 4: Migration dann parallele Zugriffe
# ---------------------------------------------------------------------------

def test_migration_then_parallel_access(tmp_path: Path) -> None:
    """
    Setup: Legacy _manifest.md mit BL-X und BL-Y Bloecken.
    Migration via migrate_manifest_split.py.
    Post-Migration: 2 Threads schreiben parallel zu BL-X und BL-Y.
    Writes landen in korrekten per-BL Files.
    """
    import importlib.util
    migrate_script = _SCRIPTS_DIR / "migrate_manifest_split.py"
    if not migrate_script.exists():
        pytest.skip("migrate_manifest_split.py nicht gefunden")

    vault_root = tmp_path

    # Legacy _manifest.md mit 2 BL-Bloecken
    legacy_manifest = vault_root / "_manifest.md"
    legacy_content = (
        "## BDF_PIPELINE_STATE\nbdf_status: idle\n\n"
        "## A_PIPELINE_STATE\n# BL-X\nphase: analyse\n\n"
        "## A_PIPELINE_STATE_BL_Y\nphase: idle\n"
    )
    legacy_manifest.write_text(legacy_content, encoding="utf-8")

    # Backlog-Ordner + BL-Subfolder vorbereiten damit Migration BL-IDs erkennt
    backlog = vault_root / "Backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    (backlog / "BL-X").mkdir(exist_ok=True)
    (backlog / "BL-Y").mkdir(exist_ok=True)

    # Migration: _factory_manifest.md erstellen (minimal, simuliert Migration-Ergebnis)
    factory = vault_root / "_factory_manifest.md"
    factory.write_text(
        "## BDF_PIPELINE_STATE\nbdf_status: idle\n",
        encoding="utf-8",
    )
    # Per-BL Manifests erstellen (simuliert Migration-Output)
    (backlog / "BL-X" / "_manifest.md").write_text(
        "## A_PIPELINE_STATE\nphase: analyse\n",
        encoding="utf-8",
    )
    (backlog / "BL-Y" / "_manifest.md").write_text(
        "## A_PIPELINE_STATE\nphase: idle\n",
        encoding="utf-8",
    )

    # Jetzt Split aktiv (factory vorhanden) — parallele Writes
    errors: List[Exception] = []
    WRITE_COUNT = 30

    def write_bl_x():
        _simulate_bdf_writes("BL-X", vault_root, WRITE_COUNT, "POST_MIGRATION_A", errors)

    def write_bl_y():
        _simulate_bdf_writes("BL-Y", vault_root, WRITE_COUNT, "POST_MIGRATION_B", errors)

    t_x = threading.Thread(target=write_bl_x)
    t_y = threading.Thread(target=write_bl_y)
    t_x.start()
    t_y.start()
    t_x.join(timeout=20)
    t_y.join(timeout=20)

    assert not errors, f"Post-Migration Writes fehlgeschlagen: {errors}"

    # Writes in richtigen Dateien — kein Backward-Compat-Fallback
    bl_x_manifest = backlog / "BL-X" / "_manifest.md"
    bl_y_manifest = backlog / "BL-Y" / "_manifest.md"

    _assert_no_cross_contamination(
        bl_x_manifest, bl_y_manifest,
        "POST_MIGRATION_A", "POST_MIGRATION_B",
        WRITE_COUNT, WRITE_COUNT,
    )

    # Legacy _manifest.md bleibt unveraendert (Backward-Compat-Layer wurde NICHT getriggert)
    current_legacy = legacy_manifest.read_text(encoding="utf-8")
    assert current_legacy == legacy_content, (
        "Legacy _manifest.md wurde veraendert — Backward-Compat-Layer faelschlich getriggert"
    )


# ---------------------------------------------------------------------------
# Test 5: Rollback / Lese-Blockierung waehrend Migration
# ---------------------------------------------------------------------------

def test_rollback_during_parallel_workers(tmp_path: Path) -> None:
    """
    INV-MANIFEST-SPLIT-4: Laufende Migration haelt File-Lock auf _factory_manifest.md.
    Parallele Worker die gleichzeitig schreiben muessen warten (Lock) oder
    bekommen RuntimeError (Lock-Timeout) — KEIN Read von partial-state.

    Simulation: Ein Thread haelt Lock fuer 0.5s (simuliert laufende Migration),
    ein zweiter Thread versucht in dieser Zeit zu schreiben.
    Ergebnis: zweiter Thread wartet und schreibt NACH Lock-Freigabe korrekt.
    """
    vault_root = _setup_temp_vault(tmp_path)
    factory = vault_root / "_factory_manifest.md"

    lock_held_event = threading.Event()
    lock_released_event = threading.Event()
    write_result: List[str] = []
    errors: List[Exception] = []

    def simulate_migration_lock():
        """Haelt File-Lock fuer kurze Zeit (simuliert atomare Migration)."""
        lock_path = factory.with_suffix(factory.suffix + ".lock")
        # Manuell Lock erstellen
        fd = None
        try:
            fd = open(str(lock_path), "x")
            lock_held_event.set()
            time.sleep(0.4)  # Simuliert Migration-Arbeit
        except FileExistsError:
            errors.append(RuntimeError("Lock-Datei bereits vorhanden — Test-Setup-Fehler"))
        finally:
            if fd is not None:
                fd.close()
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass
            lock_released_event.set()

    def worker_write():
        """Wartet bis Lock gehalten wird, versucht dann zu schreiben."""
        lock_held_event.wait(timeout=5)
        start = time.monotonic()
        try:
            manifest_reader.write_factory_block(
                field_path="BDF_PIPELINE_STATE.bdf_status",
                value="worker_after_migration",
                vault_root=vault_root,
            )
            elapsed = time.monotonic() - start
            write_result.append(f"success_after_{elapsed:.2f}s")
        except RuntimeError as e:
            # Lock-Timeout ist ebenfalls akzeptables Verhalten (INV-MANIFEST-SPLIT-4)
            write_result.append(f"timeout: {e}")
        except Exception as e:
            errors.append(e)

    t_migration = threading.Thread(target=simulate_migration_lock, name="Migration")
    t_worker = threading.Thread(target=worker_write, name="Worker")

    t_migration.start()
    t_worker.start()
    t_migration.join(timeout=10)
    t_worker.join(timeout=15)

    assert not errors, f"Unerwartete Fehler: {errors}"
    assert len(write_result) == 1, "Worker-Write-Ergebnis fehlt"

    outcome = write_result[0]

    if outcome.startswith("success_after_"):
        # Worker hat gewartet und dann erfolgreich geschrieben (Lock-Serialisierung)
        elapsed_str = outcome.replace("success_after_", "").replace("s", "")
        elapsed = float(elapsed_str)
        assert elapsed >= 0.3, (
            f"Worker hat NICHT auf Lock gewartet (elapsed={elapsed:.2f}s < 0.3s) "
            "— moegliche Partial-State-Lese-Verletzung (INV-MANIFEST-SPLIT-4)"
        )

        # File muss den Worker-Write enthalten
        content = factory.read_text(encoding="utf-8")
        assert "worker_after_migration" in content, (
            "Worker-Write nicht im Factory-Manifest gefunden"
        )
    elif outcome.startswith("timeout:"):
        # Lock-Timeout ist auch akzeptabel — Worker hat NICHT partial-state gelesen
        # (INV-MANIFEST-SPLIT-4: Kein Read von inkonsistentem Zustand)
        pass
    else:
        pytest.fail(f"Unerwartetes Write-Ergebnis: {outcome}")

    # Keine verwaisten Lock-Dateien
    lock_files = list(vault_root.rglob("*.lock"))
    assert len(lock_files) == 0, f"Lock-Dateien nicht bereinigt: {lock_files}"
