#!/usr/bin/env python3
"""BL-441 batch_1 Stage 1 — Enforcement + Owner-Gate Tests.

AK-2-PL-1: INV-FRESH-SESSION-1 muss in BEIDEN Skill-Dateien stehen:
  - .claude/commands/_goal_backlog.md
  - .claude/commands/_roadmap_backlog.md

AK-4-PL-1: Owner-Gate-Doc muss existieren:
  - {VAULT}/Backlog/BL-441-.../Owner_Gate_AK4_BL406_411_417.md
  Inhalt: BL-406, BL-411, BL-417, Owner (je als Substring)

Klasse: markdown_uncoverable_class / scenario-verify (existence + content grep).
RED-Worker schreibt NUR Tests — KEINE Implementierung (RED != GREEN, INV-BUILD-GRAIN).
"""
import sys
from pathlib import Path

# ── Pfad-Aufloesung ──────────────────────────────────────────────────────────
# Repo-Root: dieses Skript liegt in .claude/scripts/ -> 2 Ebenen hoch = repo-root
_SCRIPT_DIR = Path(__file__).parent.resolve()
_REPO_ROOT = _SCRIPT_DIR.parent.parent  # OmniCommand-wtA/

# Vault-Root via resolve_vault_root.py (robuste Aufloesung)
try:
    import subprocess as _sp
    _vault_result = _sp.run(
        [sys.executable, str(_SCRIPT_DIR / "resolve_vault_root.py")],
        capture_output=True, text=True, timeout=10
    )
    _VAULT_ROOT = Path(_vault_result.stdout.strip()) if _vault_result.returncode == 0 and _vault_result.stdout.strip() else None
except Exception:
    _VAULT_ROOT = None

# Fallback: bekannter Pfad (dokumentiert in MEMORY)
if not _VAULT_ROOT or not _VAULT_ROOT.exists():
    _VAULT_ROOT = Path(
        r"C:\Users\hanno\Documents\Work\Wissen\Berechtigung\OmniCommand\OmniCommand"
    )

_BL441_FOLDER = (
    _VAULT_ROOT
    / "Backlog"
    / "BL-441-loaded-session-pipeline-degradation-worker-rest-sendmessage-block"
)

# ── Konstanten ───────────────────────────────────────────────────────────────
GOAL_BACKLOG_MD = _REPO_ROOT / ".claude" / "commands" / "_goal_backlog.md"
ROADMAP_BACKLOG_MD = _REPO_ROOT / ".claude" / "commands" / "_roadmap_backlog.md"
OWNER_GATE_DOC = _BL441_FOLDER / "Owner_Gate_AK4_BL406_411_417.md"

INV_MARKER = "INV-FRESH-SESSION-1"


# ── Tests ────────────────────────────────────────────────────────────────────

def test_inv_fresh_session_in_goal_backlog():
    """AK-2-PL-1: INV-FRESH-SESSION-1 muss in _goal_backlog.md stehen.

    Prueft: Datei existiert UND enthaelt den Marker-String.
    Fehlschlag wenn: Datei fehlt ODER Marker nicht vorhanden.
    """
    assert GOAL_BACKLOG_MD.exists(), (
        f"_goal_backlog.md nicht gefunden: {GOAL_BACKLOG_MD}"
    )
    content = GOAL_BACKLOG_MD.read_text(encoding="utf-8")
    assert INV_MARKER in content, (
        f"'{INV_MARKER}' fehlt in {GOAL_BACKLOG_MD}. "
        f"AK-2-PL-1: INV-FRESH-SESSION-1 muss als Abschnitt/Marker eingetragen sein "
        f"(Bedingung: schwere Pipeline/30+ Worker; Aktion: frische Session vor schwerem BL-Start)."
    )


def test_inv_fresh_session_in_roadmap_backlog():
    """AK-2-PL-1: INV-FRESH-SESSION-1 muss in _roadmap_backlog.md stehen.

    Prueft: Datei existiert UND enthaelt den Marker-String.
    Fehlschlag wenn: Datei fehlt ODER Marker nicht vorhanden.
    """
    assert ROADMAP_BACKLOG_MD.exists(), (
        f"_roadmap_backlog.md nicht gefunden: {ROADMAP_BACKLOG_MD}"
    )
    content = ROADMAP_BACKLOG_MD.read_text(encoding="utf-8")
    assert INV_MARKER in content, (
        f"'{INV_MARKER}' fehlt in {ROADMAP_BACKLOG_MD}. "
        f"AK-2-PL-1: INV-FRESH-SESSION-1 muss als Abschnitt/Marker eingetragen sein "
        f"(Bedingung: schwere Pipeline/30+ Worker; Aktion: frische Session vor schwerem BL-Start)."
    )


def test_owner_gate_ak4_doc_exists():
    """AK-4-PL-1: Owner-Gate-Doc muss existieren und BL-406/411/417 + 'Owner' enthalten.

    Prueft:
      1. Datei existiert unter {VAULT}/Backlog/BL-441-.../Owner_Gate_AK4_BL406_411_417.md
      2. Inhalt enthaelt 'BL-406'
      3. Inhalt enthaelt 'BL-411'
      4. Inhalt enthaelt 'BL-417'
      5. Inhalt enthaelt 'Owner' (Owner-Gate-Kennzeichnung)
    Fehlschlag wenn: Datei fehlt ODER einer der Inhalt-Checks failt.
    """
    assert OWNER_GATE_DOC.exists(), (
        f"Owner-Gate-Doc fehlt: {OWNER_GATE_DOC}. "
        f"AK-4-PL-1: Optionen-Tabelle je BL-406/411/417 (nachziehen vs. accept) "
        f"+ HiL-Gate-Kennzeichnung + Entscheid-oder-Pending-Vermerk benoetigt."
    )
    content = OWNER_GATE_DOC.read_text(encoding="utf-8")
    for required_str in ("BL-406", "BL-411", "BL-417", "Owner"):
        assert required_str in content, (
            f"'{required_str}' fehlt in Owner-Gate-Doc {OWNER_GATE_DOC}. "
            f"Pflicht: Tabelle mit allen 3 BLs + Owner-Gate-Marker."
        )
