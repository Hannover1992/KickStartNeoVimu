#!/usr/bin/env python3
"""
test_budget_watch.py — BL-338 / batch_PL3 / PL-338-7 (Budget-Watch, DETECTOR-ONLY, M3)

RED-Test-Host fuer budget_watch.py: Binaer-/grosse Artefakte (Screenshots,
Presentations, PDFs) sind BY-DESIGN gross — der Budget-Watch ist ein reiner
DETEKTOR fuers Reporting: er weist die GROESSE aus und flaggt over_budget gegen
gc_budgets (falls fuer den Typ ein Budget existiert), HEILT aber NICHTS.

KERN-INVARIANTE (PL-338-7 §read-only): watch_budget veraendert/loescht KEINE Datei.
Der Test verifiziert das hart: Bytes ALLER gescannten Dateien sind nach watch_budget
unveraendert (kein versehentlicher Heiler/Slim).

Greenfield: budget_watch.py existiert NOCH NICHT -> `import budget_watch` schlaegt fehl
-> ImportError = RED fuer alle Gold-Tests. Bewusst KEIN try/except: der Import-Fehler
IST der RED-Beweis (1:1-Analog zu den Schwester-Tests).

Isolation: KEIN Vault-IO. tmp_path-Root, monkeypatch auf das Budget statt echte
Registry-Aufloesung.

Gold-Map (PL-338-7 §Gold-Definition):
  G7a watch_listet_dateien_mit_size_und_flag
  G7b over_budget_flag_korrekt              (size > budget -> True, sonst False)
  G7c read_only_invariante                  (KEINE Datei veraendert/geloescht nach watch)
  G7d kein_budget_kein_crash                (Typ ohne Budget -> over_budget False, kein Crash)
"""
import hashlib
from pathlib import Path

import pytest


# Greenfield-Modul: existiert noch nicht -> ImportError = RED fuer alle Tests.
import budget_watch as bw


def _md5_bytes(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def _make_binary_root(tmp_path: Path):
    """Synthetischer Root mit grossen + kleinen Binaer-Artefakten.

    Returns (root, {name: bytes}) — Snapshot fuer die read-only-Invariante.
    """
    root = tmp_path / "evidence"
    root.mkdir()
    files = {
        "screenshot_gross.png": b"\x89PNG\r\n" + b"A" * 5000,   # gross
        "screenshot_klein.png": b"\x89PNG\r\n" + b"B" * 10,     # klein
        "slides.pptx": b"PK\x03\x04" + b"C" * 8000,             # gross
    }
    for name, data in files.items():
        (root / name).write_bytes(data)
    return root, files


def _pin_budget(monkeypatch, budget):
    """resolve_budget (im budget_watch-Modulnamespace) auf einen festen Wert pinnen.

    budget=None simuliert 'kein Budget fuer diesen Typ'.
    """
    monkeypatch.setattr(bw, "resolve_budget", lambda typ: budget)


# ---------------------------------------------------------------------------
# Ring 0 (Detection-Report) — G7a / G7b
# ---------------------------------------------------------------------------

def test_watch_listet_dateien_mit_size_und_flag(tmp_path, monkeypatch):
    """G7a: watch_budget liefert je Datei einen Report mit path/size_bytes/budget/over_budget."""
    root, files = _make_binary_root(tmp_path)
    _pin_budget(monkeypatch, 1000)  # Budget 1000 -> grosse Dateien drueber

    report = bw.watch_budget(str(root))

    assert isinstance(report, list) and report, "watch_budget liefert nicht-leere Liste"
    by_name = {Path(r["path"]).name: r for r in report}
    # Pflicht-Felder pro Eintrag.
    for r in report:
        assert "path" in r and "size_bytes" in r
        assert "budget" in r and "over_budget" in r
    # Groessen plausibel.
    assert by_name["screenshot_gross.png"]["size_bytes"] == len(files["screenshot_gross.png"])


def test_over_budget_flag_korrekt(tmp_path, monkeypatch):
    """G7b: over_budget==True nur fuer Dateien ueber dem Budget, sonst False."""
    root, files = _make_binary_root(tmp_path)
    _pin_budget(monkeypatch, 1000)

    report = bw.watch_budget(str(root))
    by_name = {Path(r["path"]).name: r for r in report}

    assert by_name["screenshot_gross.png"]["over_budget"] is True   # 5000+ > 1000
    assert by_name["slides.pptx"]["over_budget"] is True            # 8000+ > 1000
    assert by_name["screenshot_klein.png"]["over_budget"] is False  # ~16 < 1000


# ---------------------------------------------------------------------------
# Ring 1 (read-only-Invariante — OBERSTER Kanarienvogel) — G7c
# ---------------------------------------------------------------------------

def test_read_only_invariante(tmp_path, monkeypatch):
    """G7c: watch_budget veraendert/loescht KEINE Datei (Detector-only, kein Heiler).

    Bytes ALLER gescannten Dateien sind nach watch_budget identisch zum Snapshot davor.
    Das ist die definierende Invariante von PL-338-7 (binary by-design, nur reporten).
    """
    root, files = _make_binary_root(tmp_path)
    _pin_budget(monkeypatch, 1000)

    before = {p.name: _md5_bytes(p.read_bytes()) for p in root.iterdir()}
    before_count = len(list(root.iterdir()))

    bw.watch_budget(str(root))

    after = {p.name: _md5_bytes(p.read_bytes()) for p in root.iterdir()}
    after_count = len(list(root.iterdir()))

    assert after_count == before_count, "watch_budget hat Dateien geloescht/erzeugt (kein Heiler!)"
    assert after == before, f"watch_budget hat Datei-Inhalte veraendert: {before} -> {after}"


# ---------------------------------------------------------------------------
# Ring 2 (Resilienz) — G7d
# ---------------------------------------------------------------------------

def test_kein_budget_kein_crash(tmp_path, monkeypatch):
    """G7d: Typ ohne Budget (resolve_budget->None) -> over_budget False, KEIN Crash."""
    root, files = _make_binary_root(tmp_path)
    _pin_budget(monkeypatch, None)  # kein Budget fuer diesen Typ

    report = bw.watch_budget(str(root), typ="gibt_es_nicht")

    assert isinstance(report, list) and report
    for r in report:
        # Ohne Budget kann nie over_budget sein (manifest/gc_budgets Dual-Read-Resilienz).
        assert r["over_budget"] is False
        # size weiterhin gemeldet (Detektion bleibt nuetzlich).
        assert r["size_bytes"] >= 0
