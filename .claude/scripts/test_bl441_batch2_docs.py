#!/usr/bin/env python3
"""BL-441 batch_2 Stage 1 — Markdown-Doc-Deliverable Tests.

AK-1-PL-1: Diagnose-Doku muss existieren und folgende Woerter enthalten:
  - "W7" (Hook-Bezeichnung)
  - "W8" (Hook-Bezeichnung)
  - "W6" (Hook-Bezeichnung)
  - "SendMessage" (Block-Erklaerung)
  - "Verdikt" (explizites Verdikt-Kapitel)
  Datei: {VAULT}/Backlog/BL-441-.../Diagnose_AK1_StopHook_Verdikt.md

AK-3-PL-1: Vehikel-Befund-Doku muss existieren und folgende Woerter enthalten:
  - "dispatch_implement" (Workflow-Name)
  - "Cron" (Vehikel-Option)
  - "PLAIN" (Vehikel-Typ)
  - "Befund" (Befund-Kapitel / Tauglichkeits-Befund)
  Datei: {VAULT}/Backlog/BL-441-.../Vehikel_Befund_AK3_dispatch_implement.md

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
DIAGNOSE_AK1_DOC = _BL441_FOLDER / "Diagnose_AK1_StopHook_Verdikt.md"
VEHIKEL_BEFUND_AK3_DOC = _BL441_FOLDER / "Vehikel_Befund_AK3_dispatch_implement.md"


# ── Tests ────────────────────────────────────────────────────────────────────

def test_diagnose_ak1_doc_exists_and_content():
    """AK-1-PL-1: Diagnose-Doku muss existieren + W7/W8/W6/SendMessage/Verdikt enthalten.

    Prueft:
      1. Datei existiert unter {VAULT}/Backlog/BL-441-.../Diagnose_AK1_StopHook_Verdikt.md
      2. Inhalt enthaelt woertlich "W7"
      3. Inhalt enthaelt woertlich "W8"
      4. Inhalt enthaelt woertlich "W6"
      5. Inhalt enthaelt woertlich "SendMessage"
      6. Inhalt enthaelt woertlich "Verdikt"
    Fehlschlag wenn: Datei fehlt ODER einer der Inhalt-Checks failt.
    """
    assert DIAGNOSE_AK1_DOC.exists(), (
        f"Diagnose-Doku fehlt: {DIAGNOSE_AK1_DOC}. "
        f"AK-1-PL-1: Stop-Hook-Diagnose mit W7-vs-W8-Verdikt + SendMessage-Block-Erklaerung "
        f"muss als Markdown-Doc im BL-441-Folder abgelegt sein."
    )
    content = DIAGNOSE_AK1_DOC.read_text(encoding="utf-8")
    for required_str in ("W7", "W8", "W6", "SendMessage", "Verdikt"):
        assert required_str in content, (
            f"'{required_str}' fehlt in Diagnose-Doku {DIAGNOSE_AK1_DOC}. "
            f"Pflicht: explizites W7-vs-W8-Verdikt + SendMessage-Block-Erklaerung "
            f"+ W6-Kontext (alle drei Hook-Bezeichnungen muessen vorkommen)."
        )


def test_vehikel_befund_ak3_doc_exists_and_content():
    """AK-3-PL-1: Vehikel-Befund-Doku muss existieren + dispatch_implement/Cron/PLAIN/Befund enthalten.

    Prueft:
      1. Datei existiert unter {VAULT}/Backlog/BL-441-.../Vehikel_Befund_AK3_dispatch_implement.md
      2. Inhalt enthaelt woertlich "dispatch_implement"
      3. Inhalt enthaelt woertlich "Cron"
      4. Inhalt enthaelt woertlich "PLAIN"
      5. Inhalt enthaelt woertlich "Befund"
    Fehlschlag wenn: Datei fehlt ODER einer der Inhalt-Checks failt.
    """
    assert VEHIKEL_BEFUND_AK3_DOC.exists(), (
        f"Vehikel-Befund-Doku fehlt: {VEHIKEL_BEFUND_AK3_DOC}. "
        f"AK-3-PL-1: Tauglichkeits-Befund + Entscheid fuer dispatch_implement-Workflow "
        f"muss als Markdown-Doc im BL-441-Folder abgelegt sein."
    )
    content = VEHIKEL_BEFUND_AK3_DOC.read_text(encoding="utf-8")
    for required_str in ("dispatch_implement", "Cron", "PLAIN", "Befund"):
        assert required_str in content, (
            f"'{required_str}' fehlt in Vehikel-Befund-Doku {VEHIKEL_BEFUND_AK3_DOC}. "
            f"Pflicht: Tauglichkeits-Befund (dispatch_implement + Cron-Option + PLAIN-Typ + "
            f"Befund-Kapitel mit Entscheid)."
        )
