#!/usr/bin/env python3
"""
test_audit_rotation.py — GOLD-RED fuer audit_rotation.py (BL-338 PL-338-5).

ZWECK (Gold-Contract A): audit.jsonl waechst unbegrenzt (5.45MB); ~10 Guards
scannen es RUECKWAERTS je Edit/Write = compounding Perf-Steuer. ROTATION ist ein
standalone Trim-Tool: ARCHIVIERT die AELTESTEN Zeilen nach `audit-{YYYY-MM}.jsonl`
(ts-Praefix der Zeilen) und BEHAELT die letzten N Zeilen in audit.jsonl.

SICHERHEITS-KERN (NICHT verhandelbar): Rotation MUSS die Guard-Backwards-Scans
intakt lassen. Die juengsten Marker (SKILL_LOAD _idf/_sdf/_redeploy/_health/
stage-seam), nach denen die Guards rueckwaerts suchen, sind per Definition RECENT
-> bleiben in audit.jsonl -> Guards UNVERAENDERT funktionsfaehig. Der KERN-Test
GUARD-SCAN-PRESERVE deckt genau das ab (KEINE Guard-Edits in diesem Batch noetig).

GREEN-API (audit_rotation.py, __file__-relativ / cwd-invariant):
  - find_audit_path() / Default `.claude/audit/audit.jsonl`.
  - rotate_audit(audit_path, keep_recent=2000, dry_run=False)
        -> dict {rotated_count, kept_count, archive_path}. lossless (archiv+rest
           == original, MD5-verifizierbar). dry_run -> kein Write.
  - rotate_log(log_path, keep_recent=...) -> analog fuer _guard_log.md / .hook_debug.log.

Greenfield-Import `import audit_rotation as ar` ist RED bis das Modul existiert.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

# Greenfield-Import -> RED bis audit_rotation.py existiert (GREEN-Phase).
import audit_rotation as ar


# ── Helfer ───────────────────────────────────────────────────────────────────

def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _audit_line(ts: str, event: str, skill: str = "") -> str:
    obj = {"ts": ts, "event": event}
    if skill:
        obj["skill"] = skill
    return json.dumps(obj)


def _write_jsonl(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scan_backwards_for(path: Path, needle: str):
    """Simuliert den Guard-Backwards-Scan: juengste->aelteste, finde den Marker.

    Spiegelt sdf_ran_since_idf()-Stil aus guard_idf_sdf_handoff.py (read_text +
    rueckwaerts ueber die Zeilen). Returns die Zeilen-Position (von hinten) oder -1.
    """
    if not path.exists():
        return -1
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if needle in lines[i]:
            return i
    return -1


@pytest.fixture
def synthetic_audit(tmp_path):
    """50 chronologische audit-Zeilen; juengster Eintrag = SKILL_LOAD _redeploy."""
    lines = [_audit_line(f"2026-06-13T10:{i:02d}:00", "STATE_WRITE") for i in range(48)]
    lines.append(_audit_line("2026-06-13T10:48:00", "SKILL_LOAD", "_idf_orchestrate"))
    lines.append(_audit_line("2026-06-13T10:49:00", "SKILL_LOAD", "_redeploy"))
    p = tmp_path / ".claude" / "audit" / "audit.jsonl"
    _write_jsonl(p, lines)
    return p


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_find_audit_path_default_is_claude_relative():
    """find_audit_path() liefert den .claude/audit/audit.jsonl-Default (cwd-invariant)."""
    p = ar.find_audit_path()
    assert str(p).replace("\\", "/").endswith(".claude/audit/audit.jsonl")


def test_rotate_keeps_exactly_keep_recent_lines(synthetic_audit):
    """rotate_audit(keep_recent=N) behaelt genau N juengste Zeilen in audit.jsonl."""
    res = ar.rotate_audit(synthetic_audit, keep_recent=10)
    kept = synthetic_audit.read_text(encoding="utf-8").splitlines()
    assert res["kept_count"] == 10
    assert len(kept) == 10
    assert res["rotated_count"] == 40


def test_rotate_archives_oldest_lines(synthetic_audit):
    """Der Rest (aelteste Zeilen) landet im YYYY-MM-Archiv, nicht in audit.jsonl."""
    res = ar.rotate_audit(synthetic_audit, keep_recent=10)
    archive = Path(res["archive_path"])
    assert archive.exists()
    archived = archive.read_text(encoding="utf-8").splitlines()
    # die aelteste Original-Zeile ist archiviert, NICHT mehr in audit.jsonl
    assert any('"10:00:00"'.strip('"') in l or "10:00:00" in l for l in archived)
    kept = synthetic_audit.read_text(encoding="utf-8")
    assert "10:00:00" not in kept


def test_guard_scan_preserve_recent_marker(synthetic_audit):
    """KERN-Test (Sicherheits-Kern): nach rotate bleibt der juengste SKILL_LOAD
    _redeploy in audit.jsonl -> der Guard-Backwards-Scan findet ihn weiter.

    Das ist der Beweis, dass KEINE Guard-Edits noetig sind: die Marker, nach denen
    die Guards suchen, sind per Definition RECENT und ueberleben das Trim.
    """
    ar.rotate_audit(synthetic_audit, keep_recent=10)
    # Inline-Backwards-Scan (Guard-Stil) auf der GETRIMMTEN Datei:
    pos = _scan_backwards_for(synthetic_audit, "_redeploy")
    assert pos != -1, "juengster _redeploy-Marker nach Rotation NICHT mehr scanbar"
    # auch der _idf_orchestrate-Marker (vorletzte Zeile) ueberlebt
    assert _scan_backwards_for(synthetic_audit, "_idf_orchestrate") != -1


def test_rotate_lossless_md5(synthetic_audit):
    """lossless: archivierte Zeilen + behaltene Zeilen == Original (Reihenfolge + Vollst.)."""
    original = synthetic_audit.read_text(encoding="utf-8")
    original_lines = original.splitlines()
    res = ar.rotate_audit(synthetic_audit, keep_recent=10)
    archived = Path(res["archive_path"]).read_text(encoding="utf-8").splitlines()
    # Archiv-Inhalt kann einen Kommentar-/MD5-Header tragen -> nur die JSON-Zeilen zaehlen.
    archived_json = [l for l in archived if l.strip().startswith("{")]
    kept = synthetic_audit.read_text(encoding="utf-8").splitlines()
    recombined = archived_json + kept
    assert recombined == original_lines
    assert _md5("\n".join(recombined)) == _md5("\n".join(original_lines))


def test_rotate_dry_run_writes_nothing(synthetic_audit):
    """dry_run=True veraendert weder audit.jsonl noch legt ein Archiv an."""
    before = synthetic_audit.read_text(encoding="utf-8")
    res = ar.rotate_audit(synthetic_audit, keep_recent=10, dry_run=True)
    assert synthetic_audit.read_text(encoding="utf-8") == before
    if res.get("archive_path"):
        assert not Path(res["archive_path"]).exists()


def test_rotate_empty_or_missing_is_noop(tmp_path):
    """leere/fehlende audit -> no-op, kein Crash (kept/rotated == 0)."""
    missing = tmp_path / ".claude" / "audit" / "audit.jsonl"
    res = ar.rotate_audit(missing, keep_recent=10)
    assert res["rotated_count"] == 0
    assert res["kept_count"] == 0

    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    res2 = ar.rotate_audit(empty, keep_recent=10)
    assert res2["rotated_count"] == 0
    assert res2["kept_count"] == 0


def test_rotate_keep_more_than_total_is_noop(synthetic_audit):
    """keep_recent >= Zeilenzahl -> nichts rotiert (alles bleibt)."""
    before = synthetic_audit.read_text(encoding="utf-8")
    res = ar.rotate_audit(synthetic_audit, keep_recent=10_000)
    assert res["rotated_count"] == 0
    assert synthetic_audit.read_text(encoding="utf-8") == before


def test_rotate_log_trims_guard_log(tmp_path):
    """rotate_log analog fuer _guard_log.md / .hook_debug.log: behaelt die juengsten
    Zeilen, lagert den Rest aus, lossless."""
    log = tmp_path / "_guard_log.md"
    lines = [f"- [2026-06-13 10:{i:02d}] **GUARD** entry {i}" for i in range(30)]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = ar.rotate_log(log, keep_recent=5)
    kept = log.read_text(encoding="utf-8").splitlines()
    assert res["kept_count"] == 5
    assert len(kept) == 5
    # juengste Zeile (entry 29) ueberlebt
    assert any("entry 29" in l for l in kept)


def test_rotate_log_dry_run_writes_nothing(tmp_path):
    """rotate_log dry_run -> kein Write."""
    log = tmp_path / ".hook_debug.log"
    log.write_text("\n".join(f"line {i}" for i in range(20)) + "\n", encoding="utf-8")
    before = log.read_text(encoding="utf-8")
    ar.rotate_log(log, keep_recent=5, dry_run=True)
    assert log.read_text(encoding="utf-8") == before
