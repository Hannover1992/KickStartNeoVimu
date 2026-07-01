#!/usr/bin/env python3
"""Tests fuer guard_stage_elevation_audit.py (BL-486 AK-E E2-FIX, Option B).

RED-first (greenfield): guard_stage_elevation_audit.py existiert noch NICHT.
Bis GREEN schlagen diese Tests mit ModuleNotFoundError fehl (korrektes greenfield-RED).

Schliesst W15 (off-the-books-Elevation): ein Stufen-Inkrement (current_stage bump /
completed_stages append / ELEVATE-Event) OHNE vorausgehendes _SDF_orchestrate_post
SKILL_LOAD im audit.jsonl -> Detektor faengt (WARN/FAIL, Fail-Loud PT-CMD-011).

Schablone: geist9b post_phase_ran_since_i_pipeline (audit.jsonl-Rueckwaerts-Scan,
guard_geist9b_sdf_post_inline.py:75-107).

INV-STAGE-CHANNEL-1: das Modul liest NUR audit.jsonl (+ ggf. manifest read-only),
schreibt/aendert _stage.md NICHT (Option B, KEIN Option-A-Bookkeeping-Write).

Kern-Vertrag (Blueprint Item 4, Gold E2-FIX):
  stage_increment_has_preceding_post(audit_lines: list[str]) -> tuple[bool, list]
    Rueckwaerts-Scan; True gdw. JEDES stage_increment/ELEVATE-Event ein preceding
    _SDF_orchestrate_post hat. (Spiegel von post_phase_ran_since_i_pipeline.)
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_stage_elevation_audit.py"


def _to_lines(events):
    """Audit-Events -> jsonl-Zeilen (eine Zeile pro Event), wie audit.jsonl sie traegt."""
    return [json.dumps(ev) for ev in events]


# ---------------------------------------------------------------------------
# Audit-Fixtures (synthetic audit.jsonl mit / ohne preceding _SDF_orchestrate_post)
# ---------------------------------------------------------------------------

# OFF-THE-BOOKS: Stufen-Inkrement OHNE vorausgehendes _SDF_orchestrate_post.
AUDIT_OFF_THE_BOOKS = _to_lines([
    {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
    {"event": "STAGE_INCREMENT", "from_stage": 1, "to_stage": 3},
])

# LEGITIM: Stufen-Inkrement MIT vorausgehendem _SDF_orchestrate_post.
AUDIT_WITH_PRECEDING_POST = _to_lines([
    {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
    {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    {"event": "STAGE_INCREMENT", "from_stage": 1, "to_stage": 3},
])


# ===========================================================================
# ASSERTION 1 — faengt off-the-books-Elevation (Fail-Loud)
# ===========================================================================

def test_stage_increment_without_preceding_post_detected():
    """ASSERTION 1: Stufen-Inkrement OHNE preceding _SDF_orchestrate_post
    -> stage_increment_has_preceding_post() == False (Verstoss erkannt)."""
    import guard_stage_elevation_audit as mod
    ok, offenders = mod.stage_increment_has_preceding_post(AUDIT_OFF_THE_BOOKS)
    assert ok is False
    assert offenders  # die verletzenden Inkremente werden benannt (Fail-Loud)


# ===========================================================================
# ASSERTION 2 — kein false-FAIL bei legitimem Inkrement
# ===========================================================================

def test_stage_increment_with_preceding_post_ok():
    """ASSERTION 2: Stufen-Inkrement MIT preceding _SDF_orchestrate_post
    -> stage_increment_has_preceding_post() == True (kein false positive)."""
    import guard_stage_elevation_audit as mod
    ok, offenders = mod.stage_increment_has_preceding_post(AUDIT_WITH_PRECEDING_POST)
    assert ok is True
    assert not offenders


# ===========================================================================
# CLI/Hook-Verhalten — Fail-Loud-Exit (PT-CMD-011) als Verhaltens-Beleg
# ===========================================================================

def _run_guard_cli(audit_lines):
    """Fuehrt das Guard-Modul als Hook/CLI aus mit synthetic audit.jsonl via
    OMNI_STAGE_ELEVATION_AUDIT-Override. Returns geparstes stdout-JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False,
                                     encoding="utf-8") as f:
        for line in audit_lines:
            f.write(line + "\n")
        audit_path = f.name
    env = os.environ.copy()
    env["OMNI_STAGE_ELEVATION_AUDIT"] = audit_path
    try:
        proc = subprocess.run([sys.executable, str(GUARD)], input="{}",
                              capture_output=True, text=True, env=env)
    finally:
        Path(audit_path).unlink(missing_ok=True)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_cli_off_the_books_warn_or_fail():
    """ASSERTION 1 (CLI-Ebene): off-the-books-Inkrement -> WARN/FAIL gemeldet
    (continue:false ODER message mit Verstoss-Hinweis)."""
    r = _run_guard_cli(AUDIT_OFF_THE_BOOKS)
    assert r.get("continue") is False or r.get("message")


def test_cli_legit_increment_clean():
    """ASSERTION 2 (CLI-Ebene): legitimes Inkrement -> kein Block (continue:true)."""
    r = _run_guard_cli(AUDIT_WITH_PRECEDING_POST)
    assert r.get("continue") is True


# ===========================================================================
# INV-STAGE-CHANNEL-1 — Modul taste _stage.md NICHT an (Option B, read-only)
# ===========================================================================

def test_module_does_not_write_stage_md():
    """INV-STAGE-CHANNEL-1: das Guard-Modul scannt audit.jsonl read-only und
    enthaelt KEINEN Write/Open-write-Pfad auf _stage.md (Option B, nicht Option A)."""
    src = GUARD.read_text(encoding="utf-8")
    assert "_stage.md" not in src, (
        "INV-STAGE-CHANNEL-1-Bruch: Modul referenziert _stage.md "
        "(Option A waere Invarianten-Bruch; nur Option B = audit.jsonl-Scan erlaubt)."
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
