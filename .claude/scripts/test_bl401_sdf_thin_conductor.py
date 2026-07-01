#!/usr/bin/env python3
"""
TDD RED Tests fuer BL-401 batch_1 — _SDF_orchestrate SRP-Refactor (Thin-Conductor).

Abgedeckte AKs:
  AK-1  Conductor-Kern-Anker auffindbar (Schutz-Zaun — aktuell gruen, muss gruen bleiben)
  AK-2  LOC < 350 (aktuell RED: 1218 LOC)
  AK-3  INV-MODUS-1 Single-Writer unangetastet (Schutz-Zaun — aktuell gruen)
  AK-4  4 meta/sdf-Dateien existieren + nicht-leer (RED: param-setup/outer-loop/modus-dispatch fehlen)
  AK-5  Referenz-Integritaet: jede Auslager-Datei wird im Conductor referenziert (RED: neue fehlen)
  AK-6  Keine dangling refs: jede Conductor-Referenz zeigt auf existierende Datei
  AK-7  Skill-Call-Set-Erhalt (Schutz-Zaun — aktuell gruen, muss gruen bleiben)
  AK-8  INV-Leitplanken-Anker vorhanden (Schutz-Zaun — aktuell gruen, muss gruen bleiben)
  AK-9  Datum-Stempel-Heuristik: IST 60+ Treffer, Schwelle < 15 (RED)

GREEN-Worker muss:
  - _SDF_orchestrate.md auf <= 350 LOC entkernen (AK-2)
  - 3 neue meta/sdf-Dateien erzeugen: param-setup.md, outer-loop-doctrine.md,
    modus-dispatch-reference.md (AK-4)
  - Conductor-Referenzen auf alle 4 meta/sdf-Dateien setzen (AK-5)
  - Alle Schutz-Zaun-Anker (AK-1/3/7/8) erhalten

test-runner:
  cd C:/Users/hanno/RiderProjects/OmniCommand
  PYTHONIOENCODING=utf-8 py -3 -m pytest .claude/scripts/test_bl401_sdf_thin_conductor.py -v
"""

import os
import re
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Pfade
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent.parent  # OmniCommand/
CONDUCTOR = REPO_ROOT / ".claude" / "commands" / "_SDF_orchestrate.md"
# {META} resolves to .claude/meta (state-machine.md liegt dort, nicht in .claude/commands/meta/)
META_SDF = REPO_ROOT / ".claude" / "meta" / "sdf"

# ─────────────────────────────────────────────────────────────────────────────
# SOLL-Konstanten (extrahiert aus dem 1218-LOC-Conductor, 2026-06-20)
# Schutz-Zaun fuer GREEN: diese Anker MUESSEN nach dem Refactor erhalten bleiben.
# ─────────────────────────────────────────────────────────────────────────────

# AK-1: Kern-Phasen-Anker — strukturelle Logik-Anker im Conductor
REQUIRED_PHASE_ANCHORS = [
    "PHASE 0",
    "OUTER-LOOP",
    "VEHIKEL-GATE",
    "STALE-HANDOFF-RECOVERY",
    "modusEntscheidung",
    "SWITCH modus",
    '"M1"',
    '"M2"',
    '"M3"',
    '"M4"',
    '"M5"',
    '"M6"',
    '"M7"',
    '"M8"',
    '"M9"',
    "loop_decision",
    "PHASE FINAL",
    "TeamDelete",
]

# AK-3: INV-MODUS-1 Single-Writer — Pre-Check-Anker
REQUIRED_MODUS_ANCHORS = [
    "_SDF_berater_modusEntscheidung",
    "INV-MODUS-PRE-WRITE-1",
]

# AK-7: Live-Pfad Skill-Calls (extrahiert aus 1218-LOC-Conductor, 2026-06-20)
# SOLL-Liste: alle ausfuehrbaren Skill-Calls die der IST-Conductor macht.
# GREEN muss beweisen dass er ALLE erhalt.
#
# Format-Hinweis: der Conductor nutzt zwei Schreibweisen:
#   Skill(skill="_X_orchestrate", ...) — fuer Berater mit Keyword-Args
#   Skill(_X_orchestrate, args="...") — fuer direkte Inline-Calls
#   Skill(_X_orchestrate, ...) — ohne args-keyword
# Wir pruefen den gemeinsamen Prefix (ohne Args-Klammer) damit beide Varianten matchen.
#
# Nicht aufgenommen:
#   _SDF_berater_executionDispatch — nur als DEPRECATED-Kommentar (keine Live-Zeile)
REQUIRED_SKILL_CALLS = [
    "_SDF_berater_modusEntscheidung",   # Skill(_SDF_berater_modusEntscheidung, ...)
    "_SDF_berater_patternBrief",         # Skill(_SDF_berater_patternBrief, ...)
    "_SDF_berater_architecturalBrief",   # Skill(_SDF_berater_architecturalBrief, ...)
    "_SDF_berater_analyse",              # Skill(skill="_SDF_berater_analyse", ...)
    "_SDF_berater_testRun",              # Skill(skill="_SDF_berater_testRun", ...)
    "dispatch_implement",                # Workflow(name="dispatch_implement", ...)
    "_I_orchestrate",                    # Skill(_I_orchestrate, ...)
    "_SC_orchestrate",                   # Skill(_SC_orchestrate, ...)
    "_T_orchestrate",                    # Skill(_T_orchestrate, ...)
    "_smoothing",                        # Skill(_smoothing, ...)
    "_presentation",                     # Skill(_presentation, ...)
    "_WP_orchestrate",                   # Skill(_WP_orchestrate, ...)
    "_IDF_orchestrate",                  # Skill(skill="_IDF_orchestrate", ...)
    "_SDF_orchestrate",                  # Skill(skill="_SDF_orchestrate", --resume) RE-BATCH
]

# AK-8: INV-Invarianten-Leitplanken
REQUIRED_INV_ANCHORS = [
    "INV-PM-1",
    "INV-AO-CALLER",
    "INV-HW-1",
    "INV-MODUS-1",
    "INV-MOTOR-1",
    "INV-MOTOR-2",
    "INV-DISPATCH-INLINE-1",
    "INV-DISPATCH-INLINE-2",
    "ANTI-PATTERN",
]

# AK-4/5/6: Auslager-Dateien (GREEN muss 3 neue erzeugen; state-machine.md existiert schon)
META_SDF_FILES = [
    "state-machine.md",
    "param-setup.md",
    "outer-loop-doctrine.md",
    "modus-dispatch-reference.md",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_conductor() -> str:
    assert CONDUCTOR.exists(), f"Conductor nicht gefunden: {CONDUCTOR}"
    return CONDUCTOR.read_text(encoding="utf-8")


def _conductor_lines() -> list:
    return _read_conductor().splitlines()


# ─────────────────────────────────────────────────────────────────────────────
# AK-1: Conductor-Kern-Anker vorhanden (Schutz-Zaun)
# Aktuell GRUEN — muss nach Refactor gruen bleiben.
# ─────────────────────────────────────────────────────────────────────────────

def test_ak1_core_anchors_present():
    """AK-1 Schutz-Zaun: alle Kern-Phasen-Anker im Conductor auffindbar."""
    content = _read_conductor()
    missing = [anchor for anchor in REQUIRED_PHASE_ANCHORS if anchor not in content]
    assert missing == [], (
        f"AK-1 FAIL: {len(missing)} Kern-Anker fehlen im Conductor:\n"
        + "\n".join(f"  - {a}" for a in missing)
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-2: LOC unter Schwelle (aktuell RED: 1218 LOC)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak2_conductor_loc_under_350():
    """AK-2 RED: _SDF_orchestrate.md muss <= 350 Zeilen haben. IST: 1218."""
    lines = _conductor_lines()
    loc = len(lines)
    assert loc <= 350, (
        f"AK-2 FAIL: Conductor hat {loc} LOC — Ziel ist <= 350. "
        f"GREEN-Worker muss auf Thin-Conductor entkernen."
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-3: INV-MODUS-1 Single-Writer unangetastet (Schutz-Zaun)
# Aktuell GRUEN — muss nach Refactor gruen bleiben.
# ─────────────────────────────────────────────────────────────────────────────

def test_ak3_modus_single_writer_anchors():
    """AK-3 Schutz-Zaun: _SDF_berater_modusEntscheidung + INV-MODUS-PRE-WRITE-1 im Conductor."""
    content = _read_conductor()
    missing = [anchor for anchor in REQUIRED_MODUS_ANCHORS if anchor not in content]
    assert missing == [], (
        f"AK-3 FAIL: INV-MODUS-1 Anker fehlen:\n"
        + "\n".join(f"  - {a}" for a in missing)
    )


def test_ak3_no_direct_modus_write():
    """AK-3 Schutz-Zaun: Kein direkter DF_BATCH_STATE.modus = Direkt-Write im Conductor
    ausserhalb des modusEntscheidung-Gate-Kommentars."""
    content = _read_conductor()
    # Suche nach direkten Schreib-Zeilen (nicht Kommentar-Zeilen und nicht 'wird gesetzt'-Doku)
    # Pattern: 'DF_BATCH_STATE.modus = ' (Zuweisung), nicht 'modus wird gesetzt' (Doku-Zeile)
    direct_writes = []
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        # Erlaube Kommentare und Doku-Zeilen
        if stripped.startswith("#") or stripped.startswith(">") or stripped.startswith("//"):
            continue
        # Erlaube 'wird gesetzt' Doku-Zeilen
        if "wird gesetzt" in stripped:
            continue
        # Erlaube Markdown-Listenpunkte (Doku-Zeilen wie '- C3 gibt ...')
        if stripped.startswith("-") or stripped.startswith("*"):
            continue
        # Flagge direkte Zuweisungen: 'DF_BATCH_STATE.modus =' oder 'DF_BATCH_STATE.modus='
        if re.search(r"DF_BATCH_STATE\.modus\s*=\s*", stripped):
            direct_writes.append((i, stripped[:100]))
    assert direct_writes == [], (
        f"AK-3 FAIL: Direkte modus-Writes ausserhalb Gate-Gate:\n"
        + "\n".join(f"  L{ln}: {txt}" for ln, txt in direct_writes)
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-4: meta/sdf-Dateien existieren + nicht-leer (aktuell RED)
# state-machine.md existiert; param-setup.md, outer-loop-doctrine.md,
# modus-dispatch-reference.md sind NEU (fehlen → RED)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak4_meta_sdf_files_exist_and_nonempty():
    """AK-4 RED: alle 4 meta/sdf-Dateien muessen existieren und nicht-leer sein."""
    missing_or_empty = []
    for fname in META_SDF_FILES:
        fpath = META_SDF / fname
        if not fpath.exists():
            missing_or_empty.append(f"FEHLT: {fpath}")
        elif fpath.stat().st_size == 0:
            missing_or_empty.append(f"LEER: {fpath}")
    assert missing_or_empty == [], (
        f"AK-4 FAIL: {len(missing_or_empty)} meta/sdf-Dateien fehlen oder leer:\n"
        + "\n".join(f"  - {e}" for e in missing_or_empty)
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-5: Referenz-Integritaet — jede Auslager-Datei referenziert im Conductor (RED)
# Neue Dateien (param-setup/outer-loop-doctrine/modus-dispatch-reference) fehlen
# noch nicht im Conductor -> RED
# ─────────────────────────────────────────────────────────────────────────────

def test_ak5_all_meta_sdf_referenced_in_conductor():
    """AK-5 RED: jede meta/sdf-Auslager-Datei muss im Conductor referenziert sein."""
    content = _read_conductor()
    not_referenced = []
    for fname in META_SDF_FILES:
        basename = fname  # z.B. 'param-setup.md'
        # Suche nach 'sdf/{basename}' im Conductor (Referenz-Muster)
        if f"sdf/{basename}" not in content:
            not_referenced.append(fname)
    assert not_referenced == [], (
        f"AK-5 FAIL: {len(not_referenced)} meta/sdf-Dateien ohne Referenz im Conductor:\n"
        + "\n".join(f"  - sdf/{f}" for f in not_referenced)
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-6: Keine dangling refs — jede Conductor-Referenz zeigt auf existierende Datei
# state-machine.md existiert bereits; Test ist aktuell gruen solange die neuen
# Referenzen noch nicht im Conductor stehen. Nach GREEN wird AK-6 die neuen
# Referenzen auf existierende Dateien pruefen (beide gruens muessen halten).
# ─────────────────────────────────────────────────────────────────────────────

def test_ak6_no_dangling_meta_sdf_refs():
    """AK-6: jede 'sdf/X'-Referenz im Conductor zeigt auf existierende Datei."""
    content = _read_conductor()
    # Extrahiere alle 'sdf/{dateiname}'-Pattern aus dem Conductor
    refs = re.findall(r"sdf/([^\s\"')\]]+\.md)", content)
    dangling = []
    for ref in refs:
        fpath = META_SDF / ref
        if not fpath.exists():
            dangling.append(ref)
    assert dangling == [], (
        f"AK-6 FAIL: {len(dangling)} dangling refs im Conductor (Datei fehlt):\n"
        + "\n".join(f"  - sdf/{r} → {META_SDF / r}" for r in dangling)
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-7: Skill-Call-Set-Erhalt (Schutz-Zaun)
# Aktuell GRUEN — muss nach Refactor gruen bleiben.
# ─────────────────────────────────────────────────────────────────────────────

def test_ak7_skill_calls_preserved():
    """AK-7 Schutz-Zaun: alle Live-Pfad-Skill-Calls aus IST-Conductor muss GREEN erhalten.
    Prueft Skill-Namen als Substrings (format-unabhaengig — beide Schreibweisen matchen)."""
    content = _read_conductor()
    missing = [call for call in REQUIRED_SKILL_CALLS if call not in content]
    assert missing == [], (
        f"AK-7 FAIL: {len(missing)} Skill-Calls im Conductor verschwunden:\n"
        + "\n".join(f"  - {c}" for c in missing)
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-8: INV-Invarianten-Leitplanken erhalten (Schutz-Zaun)
# Aktuell GRUEN — muss nach Refactor gruen bleiben.
# ─────────────────────────────────────────────────────────────────────────────

def test_ak8_inv_guardrails_present():
    """AK-8 Schutz-Zaun: alle INV-Anker + ANTI-PATTERN im Conductor vorhanden."""
    content = _read_conductor()
    missing = [anchor for anchor in REQUIRED_INV_ANCHORS if anchor not in content]
    assert missing == [], (
        f"AK-8 FAIL: {len(missing)} INV-Anker fehlen im Conductor:\n"
        + "\n".join(f"  - {a}" for a in missing)
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-9: Historie-Entfernung (Heuristik — grobe Schwelle, RED)
# IST-Conductor hat ~60+ Datum-Stempel-Treffer; Schwelle < 15
# ─────────────────────────────────────────────────────────────────────────────

def test_ak9_history_reduced_heuristic():
    """AK-9 RED (Heuristik): Datum-Stempel-Count muss nach Refactor < 15 sein.
    IST-Stand hat 60+ Treffer (datierte Revisions-Narrative)."""
    content = _read_conductor()
    date_stamps = re.findall(r"20\d{2}-\d{2}-\d{2}", content)
    count = len(date_stamps)
    assert count < 15, (
        f"AK-9 FAIL: {count} Datum-Stempel im Conductor (Schwelle: < 15). "
        f"GREEN muss datierte Revisions-Narrative entfernen/auslagern."
    )
