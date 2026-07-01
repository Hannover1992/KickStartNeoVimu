#!/usr/bin/env python3
"""
test_gc_slim_general.py — BL-338 / batch_PL3 / PL-338-2 (Slim-Generalisierung, M3)

RED-Test-Host fuer gc_slim_general.py: verallgemeinert den BL-229-manifest_slim-Kern
(Map -> Split -> Verify, 3-Gates, MD5-lossless) von "Manifest-Rounds" auf eine
TYP-PARAMETRISIERTE Familien-/Done-Definition je Langzeit-Artefakt:
  - backlog_index : DONE-Eintraege archivierbar, offene behalten
  - parking_lot   : abgehakte [x]-Items archivierbar, [ ] behalten
  - model         : alte/superseded-Bloecke archivierbar, Working-Set behalten

Wiederverwendung statt Re-Invent (PL-338-2 §Reuse): dieselben Verify-/MD5-Prinzipien
wie manifest_slim (Import ODER analoge Helfer); Budget via gc_budgets.resolve_budget.

Greenfield: gc_slim_general.py existiert NOCH NICHT -> `import gc_slim_general`
schlaegt fehl -> ImportError = RED fuer alle Gold-Tests. Bewusst KEIN try/except:
der Import-Fehler IST der RED-Beweis (1:1-Analog zu test_gc_budgets.py).

Isolation: KEIN Vault-IO. tmp_path fuer synthetische Artefakte, monkeypatch auf
das Budget (resolve_budget) statt echte Registry-Aufloesung.

cwd-STABILITAETS-MANDAT (PL-336-4-Lehre): slim_artifact loest Pfade NIE cwd-relativ
auf; alle Hilfs-Resolver __file__-relativ. Hier wird das indirekt geschuetzt, da der
Test tmp_path-ABSOLUTE Pfade uebergibt — slim_artifact darf den uebergebenen path
1:1 verwenden, NIE cwd-relativ re-interpretieren.

Gold-Map (PL-338-2 §Gold-Definition):
  G2a index_over_budget_done_archiviert_offen_behalten (+ lossless)
  G2b parking_lot_abgehakt_archiviert_offen_behalten
  G2c dry_run_kein_write
  G2d unter_budget_no_op
  G2e unbekannter_typ_safe (no-op/None, kein Crash)
  G2f lossless_md5_gate (kept+archived == Original-Inhalt, MD5-verifiziert)
  G2g model_alte_bloecke_archiviert_working_set_behalten
"""
import hashlib
import textwrap
from pathlib import Path

import pytest


# Greenfield-Modul: existiert noch nicht -> ImportError = RED fuer alle Tests.
# Bewusst KEIN try/except: der Import-Fehler IST der RED-Beweis fuer den Slim-Ring.
import gc_slim_general as gs


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _pin_budget(monkeypatch, budget):
    """resolve_budget auf einen festen Wert pinnen (kein Vault-/Registry-IO).

    budget=None simuliert 'unbekannter Typ / fehlende Registry' (G2e).
    """
    monkeypatch.setattr(gs, "resolve_budget", lambda typ: budget)


# ── Synthetische Artefakte ──

# backlog_index: 2 DONE-Eintraege (archivierbar) + 2 offene (Working-Set behalten).
INDEX_DONE_OPEN = textwrap.dedent(
    """\
    # Backlog-Index

    - [x] BL-100 — Alt-Feature (DONE)
    - [x] BL-101 — Alt-Feature 2 (DONE)
    - [ ] BL-200 — Offen A
    - [ ] BL-201 — Offen B
    """
)

# parking_lot: 2 abgehakte [x]-Items + 2 offene [ ]-Items.
PL_CHECKED_OPEN = textwrap.dedent(
    """\
    # Parking-Lot BL-338

    - [x] PL-1 — erledigt
    - [x] PL-2 — erledigt
    - [ ] PL-3 — offen
    - [ ] PL-4 — offen
    """
)

# model: alte/superseded-Bloecke + Working-Set (analog manifest-Rounds).
MODEL_OLD_CURRENT = textwrap.dedent(
    """\
    # Model BL-338

    ## W-1 (superseded, 2026-05-01)
    behauptung: alt
    status: superseded

    ## W-1 (current, 2026-06-13)
    behauptung: aktuell
    status: active

    ## AK-1
    kriterium: invariant
    """
)


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Ring 0 (backlog_index) — G2a / G2f
# ---------------------------------------------------------------------------

def test_index_over_budget_done_archiviert_offen_behalten(tmp_path, monkeypatch):
    """G2a: over-budget backlog_index -> DONE archiviert, offen behalten, over_budget=True."""
    path = _write(tmp_path, "backlog_index.md", INDEX_DONE_OPEN)
    # Budget winzig -> Artefakt liegt drueber -> Slim greift.
    _pin_budget(monkeypatch, 10)

    result = gs.slim_artifact(str(path), "backlog_index")

    assert result["over_budget"] is True
    kept = path.read_text(encoding="utf-8")
    # Offene Eintraege bleiben, DONE wird ausgelagert.
    assert "BL-200" in kept and "BL-201" in kept
    assert "BL-100" not in kept and "BL-101" not in kept
    # Senke existiert + enthaelt die DONE-Eintraege.
    assert result["archive_path"] is not None
    archived = Path(result["archive_path"]).read_text(encoding="utf-8")
    assert "BL-100" in archived and "BL-101" in archived
    assert result["lossless"] is True


def test_lossless_md5_gate(tmp_path, monkeypatch):
    """G2f: kept + archived rekonstruiert den Original-Inhalt (MD5-Gate GREEN).

    lossless == True bedeutet: keine nicht-leere Original-Zeile geht verloren —
    jede ist entweder im behaltenen Working-Set ODER im Archiv (manifest_slim-Prinzip).
    """
    original = INDEX_DONE_OPEN
    path = _write(tmp_path, "backlog_index.md", original)
    _pin_budget(monkeypatch, 10)

    result = gs.slim_artifact(str(path), "backlog_index")

    kept = path.read_text(encoding="utf-8")
    archived = Path(result["archive_path"]).read_text(encoding="utf-8")
    orig_lines = set(l for l in original.splitlines() if l.strip())
    seen = set(l for l in kept.splitlines() if l.strip()) | set(
        l for l in archived.splitlines() if l.strip()
    )
    missing = orig_lines - seen
    assert not missing, f"lossless verletzt: {missing!r} weder in kept noch archived"
    assert result["lossless"] is True


# ---------------------------------------------------------------------------
# Ring 1 (parking_lot) — G2b
# ---------------------------------------------------------------------------

def test_parking_lot_abgehakt_archiviert_offen_behalten(tmp_path, monkeypatch):
    """G2b: parking_lot mit [x]+[ ] -> [x] archiviert, [ ] behalten, lossless."""
    path = _write(tmp_path, "BL-338-parking-lot.md", PL_CHECKED_OPEN)
    _pin_budget(monkeypatch, 10)

    result = gs.slim_artifact(str(path), "parking_lot")

    assert result["over_budget"] is True
    kept = path.read_text(encoding="utf-8")
    assert "PL-3" in kept and "PL-4" in kept       # [ ] offen bleibt
    assert "PL-1" not in kept and "PL-2" not in kept  # [x] abgehakt ausgelagert
    archived = Path(result["archive_path"]).read_text(encoding="utf-8")
    assert "PL-1" in archived and "PL-2" in archived
    assert result["lossless"] is True


# ---------------------------------------------------------------------------
# Ring 2 (model) — G2g
# ---------------------------------------------------------------------------

def test_model_alte_bloecke_archiviert_working_set_behalten(tmp_path, monkeypatch):
    """G2g: model mit superseded + current -> superseded archiviert, Working-Set behalten."""
    path = _write(tmp_path, "model.md", MODEL_OLD_CURRENT)
    _pin_budget(monkeypatch, 10)

    result = gs.slim_artifact(str(path), "model")

    assert result["over_budget"] is True
    kept = path.read_text(encoding="utf-8")
    # Der aktuelle/active Block + invariante AK bleiben.
    assert "aktuell" in kept
    assert "AK-1" in kept
    # Der superseded Block wandert ins Archiv (kein Datenverlust).
    archived = Path(result["archive_path"]).read_text(encoding="utf-8")
    assert "superseded" in archived
    assert result["lossless"] is True


# ---------------------------------------------------------------------------
# Ring 3 (Resilienz) — G2c / G2d / G2e
# ---------------------------------------------------------------------------

def test_dry_run_kein_write(tmp_path, monkeypatch):
    """G2c: dry_run=True -> kein Byte am Original veraendert, keine Senke geschrieben."""
    path = _write(tmp_path, "backlog_index.md", INDEX_DONE_OPEN)
    _pin_budget(monkeypatch, 10)
    before = path.read_bytes()
    before_md5 = _md5(INDEX_DONE_OPEN)

    result = gs.slim_artifact(str(path), "backlog_index", dry_run=True)

    # Original unveraendert.
    assert path.read_bytes() == before
    assert _md5(path.read_text(encoding="utf-8")) == before_md5
    # dry_run schreibt keine persistente Senke.
    ap = result.get("archive_path")
    if ap is not None:
        assert not Path(ap).exists(), "dry_run hat eine Archiv-Datei geschrieben"


def test_unter_budget_no_op(tmp_path, monkeypatch):
    """G2d: unter Budget -> No-Op {over_budget: False}, Original unangetastet."""
    path = _write(tmp_path, "backlog_index.md", INDEX_DONE_OPEN)
    # Riesiges Budget -> Artefakt liegt darunter -> kein Slim.
    _pin_budget(monkeypatch, 10_000_000)
    before = path.read_bytes()

    result = gs.slim_artifact(str(path), "backlog_index")

    assert result["over_budget"] is False
    assert path.read_bytes() == before, "unter Budget darf nichts verschieben"


def test_unbekannter_typ_safe(tmp_path, monkeypatch):
    """G2e: unbekannter Typ (budget None) -> safe No-Op, KEIN Crash, Original unangetastet."""
    path = _write(tmp_path, "irgendwas.md", INDEX_DONE_OPEN)
    _pin_budget(monkeypatch, None)  # unbekannter Typ -> kein Budget
    before = path.read_bytes()

    # Darf NICHT werfen — safe-Sentinel statt Crash (manifest_slim Dual-Read-Resilienz).
    result = gs.slim_artifact(str(path), "gibt_es_nicht")

    assert result["over_budget"] is False
    assert path.read_bytes() == before
