#!/usr/bin/env python3
"""
test_sidecar_ttl.py — BL-338 / batch_PL3 / PL-338-6 (Blueprint/Sidecar-TTL, M3)

RED-Test-Host fuer sidecar_ttl.py: nach Story-DONE die transienten Sidecar-Artefakte
(Blueprint_*.md / *Blueprint*-Dirs / BERATER_OUTPUTS-Sidecar-Dateien) archivieren bzw.
prunen — aber NUR wenn die Story wirklich done ist (story_done=True) UND aelter als die
TTL (ttl_days). Verlustfrei: vor Delete wird archiviert (lossless), Security-Pruefung-6-
konform (kein Delete eines noch lebenden Working-Set).

Greenfield: sidecar_ttl.py existiert NOCH NICHT -> `import sidecar_ttl` schlaegt fehl ->
ImportError = RED fuer alle Gold-Tests. Bewusst KEIN try/except: der Import-Fehler IST
der RED-Beweis (1:1-Analog zu test_gc_budgets.py / test_gc_slim_general.py).

Isolation: KEIN Vault-IO. tmp_path als bl_folder, kuenstliche mtime via os.utime fuer
den TTL-Respekt.

Gold-Map (PL-338-6 §Gold-Definition):
  G6a find_sidecars_matcht_patterns     (Blueprint_*.md / *Blueprint*-Dir / BERATER_OUTPUTS*)
  G6b prune_nur_bei_story_done          (story_done=False -> No-Op)
  G6c ttl_respekt_frisch_bleibt         (juenger als ttl_days bleibt)
  G6d prune_archiviert_dann_pruned      (alte Sidecars bei story_done=True; lossless)
  G6e dry_run_kein_delete               (Report ohne Aenderung am Dateisystem)
"""
import os
import time
from pathlib import Path

import pytest


# Greenfield-Modul: existiert noch nicht -> ImportError = RED fuer alle Tests.
import sidecar_ttl as st


def _set_age_days(path: Path, days: float):
    """mtime der Datei/des Dirs auf 'days' Tage in die Vergangenheit setzen."""
    past = time.time() - days * 86400
    os.utime(path, (past, past))


def _make_bl_folder(tmp_path: Path) -> Path:
    """Synthetischer BL-Folder mit Sidecars + einer Nicht-Sidecar-Datei."""
    bl = tmp_path / "BL-338-demo"
    bl.mkdir()
    # Sidecars (sollen von find_sidecars matchen):
    (bl / "Blueprint_batch_PL3.md").write_text("blueprint inhalt", encoding="utf-8")
    sidecar_dir = bl / "Blueprint_outputs"
    sidecar_dir.mkdir()
    (sidecar_dir / "stage1.md").write_text("stage 1", encoding="utf-8")
    (bl / "BERATER_OUTPUTS_modusEntscheidung.md").write_text("berater out", encoding="utf-8")
    # Nicht-Sidecar (Working-Set — darf NIE matchen/geprunt werden):
    (bl / "_manifest.md").write_text("manifest", encoding="utf-8")
    (bl / "3_Spec").mkdir()
    (bl / "3_Spec" / "BL-338_Spec.md").write_text("spec", encoding="utf-8")
    return bl


# ---------------------------------------------------------------------------
# Ring 0 (Detection) — G6a
# ---------------------------------------------------------------------------

def test_find_sidecars_matcht_patterns(tmp_path):
    """G6a: find_sidecars findet Blueprint_*.md, *Blueprint*-Dirs, BERATER_OUTPUTS*-Dateien."""
    bl = _make_bl_folder(tmp_path)

    found = st.find_sidecars(str(bl))
    found_names = {Path(p).name for p in found}

    assert "Blueprint_batch_PL3.md" in found_names
    assert "Blueprint_outputs" in found_names
    assert "BERATER_OUTPUTS_modusEntscheidung.md" in found_names
    # Working-Set-Dateien sind KEINE Sidecars.
    assert "_manifest.md" not in found_names
    assert "BL-338_Spec.md" not in found_names


# ---------------------------------------------------------------------------
# Ring 1 (Story-Done-Gate) — G6b
# ---------------------------------------------------------------------------

def test_prune_nur_bei_story_done(tmp_path):
    """G6b: story_done=False -> No-Op (nichts archiviert/pruned), Sidecars unangetastet."""
    bl = _make_bl_folder(tmp_path)
    # alle Sidecars alt machen, damit nur das story_done-Gate entscheidet
    for p in bl.rglob("*"):
        _set_age_days(p, 999)

    result = st.prune_sidecars(str(bl), story_done=False, ttl_days=30)

    assert result["archived"] == 0 or result["archived"] == []
    assert result["pruned"] == 0 or result["pruned"] == []
    # Sidecars existieren noch.
    assert (bl / "Blueprint_batch_PL3.md").exists()
    assert (bl / "BERATER_OUTPUTS_modusEntscheidung.md").exists()


# ---------------------------------------------------------------------------
# Ring 2 (TTL-Respekt) — G6c
# ---------------------------------------------------------------------------

def test_ttl_respekt_frisch_bleibt(tmp_path):
    """G6c: frische Sidecars (juenger als ttl_days) bleiben auch bei story_done=True."""
    bl = _make_bl_folder(tmp_path)
    # Sidecars frisch (0 Tage) -> innerhalb der TTL -> bleiben.
    for p in bl.rglob("*"):
        _set_age_days(p, 0)

    result = st.prune_sidecars(str(bl), story_done=True, ttl_days=30)

    # frisch -> nichts gepruned; Sidecars existieren noch.
    assert (bl / "Blueprint_batch_PL3.md").exists()
    assert (bl / "BERATER_OUTPUTS_modusEntscheidung.md").exists()
    pruned = result["pruned"]
    pruned_n = pruned if isinstance(pruned, int) else len(pruned)
    assert pruned_n == 0, "frische Sidecars duerfen nicht gepruned werden"


# ---------------------------------------------------------------------------
# Ring 3 (Prune + Lossless) — G6d
# ---------------------------------------------------------------------------

def test_prune_archiviert_dann_pruned(tmp_path):
    """G6d: alte Sidecars bei story_done=True -> archiviert (lossless) DANN pruned."""
    bl = _make_bl_folder(tmp_path)
    # alt genug, dass die TTL ueberschritten ist
    for p in bl.rglob("*"):
        _set_age_days(p, 60)

    result = st.prune_sidecars(str(bl), story_done=True, ttl_days=30)

    archived = result["archived"]
    archived_n = archived if isinstance(archived, int) else len(archived)
    pruned = result["pruned"]
    pruned_n = pruned if isinstance(pruned, int) else len(pruned)
    assert archived_n >= 1, "alte Sidecars muessen vor Delete archiviert werden (lossless)"
    assert pruned_n >= 1, "alte Sidecars muessen nach Archiv geprunt werden"
    # Working-Set bleibt unangetastet.
    assert (bl / "_manifest.md").exists()
    assert (bl / "3_Spec" / "BL-338_Spec.md").exists()


# ---------------------------------------------------------------------------
# Ring 4 (Dry-Run) — G6e
# ---------------------------------------------------------------------------

def test_dry_run_kein_delete(tmp_path):
    """G6e: dry_run=True -> Report ohne Aenderung; alle Sidecars existieren noch."""
    bl = _make_bl_folder(tmp_path)
    for p in bl.rglob("*"):
        _set_age_days(p, 60)

    result = st.prune_sidecars(str(bl), story_done=True, ttl_days=30, dry_run=True)

    # Report meldet, was gepruned WUERDE, loescht aber nichts.
    assert (bl / "Blueprint_batch_PL3.md").exists()
    assert (bl / "Blueprint_outputs").exists()
    assert (bl / "BERATER_OUTPUTS_modusEntscheidung.md").exists()
    # Report-Form: dict mit den 3 Schluesseln.
    assert "archived" in result and "pruned" in result and "skipped" in result
