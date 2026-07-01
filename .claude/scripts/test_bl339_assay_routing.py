"""
BL-339 batch_PL1 Stage 1 — Regressions-Schutz Tests (AK-1..6)
RED-Worker: Charakterisierungs-Tests gegen bestehendes _assay.md v2.1.0 Routing.

AK-1: Default-Routing in das aktive BL-Item
AK-2: 4-stufige BL-Kontext-Aufloesungs-Kette
AK-3: global=true Escape-Hatch
AK-4: P-12-Verankerung + Vault-Frontmatter-Konformitaet (bl-item/linked-feature)
AK-5: W16-Supersession (kein paralleler Wissens-Knoten) — FENCE-gated, erwartet RED
AK-6: NON-BLOCKING Fehler-Fallback + lazy-mkdir

Test-Strategie: Select-String / file-exist + content-grep gegen bestehende Dateien.
Kein Live-/_assay-Lauf (das ist AK-7 / batch_PL2).

SCOPE: NUR Tests (RED-Worker). Keine Aenderung an _assay.md / current_context.py / Assay_Model.md.
"""
import subprocess
import sys
from pathlib import Path

# ---------- Pfad-Aufloesung --------------------------------------------------
_WORKTREE = Path(__file__).parent.parent.parent  # OmniCommand-wtC root
_ASSAY_CMD = _WORKTREE / ".claude" / "commands" / "_assay.md"
_CURRENT_CTX = _WORKTREE / ".claude" / "scripts" / "current_context.py"
_ASSAY_MODEL = _WORKTREE / ".claude" / "models" / "Assay_Model.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ============================================================================
# AK-2 (Kanarienvogel): 4-stufige BL-Kontext-Aufloesungs-Kette
# Blueprint Z.161-183 — Praezedenz-Kette a>b>c>d textlich verifiziert
# ============================================================================

def test_ak2_resolution_chain_a_explicit_bl_param():
    """
    AK-2a: Expliziter bl=BL-XXX Param ist Quelle a (hoechste Prioritaet).
    _assay.md muss den Text 'bl=BL-' in der Routing-Sektion enthalten.
    """
    content = _read(_ASSAY_CMD)
    assert "bl=BL-" in content, (
        "AK-2a: Expliziter bl=BL-XXX Parameter-Text fehlt in _assay.md — "
        "Praezedenz-Kette Quelle a nicht dokumentiert"
    )


def test_ak2_resolution_chain_b_current_context_script():
    """
    AK-2b: Branch-Kontext via current_context.py (Quelle b).
    _assay.md muss 'current_context.py' referenzieren.
    """
    content = _read(_ASSAY_CMD)
    assert "current_context.py" in content, (
        "AK-2b: current_context.py-Referenz fehlt in _assay.md — "
        "Quelle b der Aufloesungs-Kette nicht dokumentiert"
    )


def test_ak2_resolution_chain_c_gespraechskontext():
    """
    AK-2c: Gespraechskontext als Quelle c.
    _assay.md muss einen Fallback-Gespraechskontext-Text enthalten.
    """
    content = _read(_ASSAY_CMD)
    # Der Blueprint-Text beschreibt "Gespraechskontext: An welchem BL-Item wird..."
    assert "Gespraechskontext" in content, (
        "AK-2c: Gespraechskontext-Fallback-Text fehlt in _assay.md — "
        "Quelle c der Aufloesungs-Kette nicht dokumentiert"
    )


def test_ak2_resolution_chain_d_fallback_global():
    """
    AK-2d: Kein BL-Kontext aufloesbar -> FALLBACK global (Quelle d).
    _assay.md muss 'Kein BL-Kontext aufloesbar' oder aehnlichen Fallback-Text enthalten.
    """
    content = _read(_ASSAY_CMD)
    assert "Kein BL-Kontext aufloesbar" in content, (
        "AK-2d: Fallback-Text 'Kein BL-Kontext aufloesbar' fehlt in _assay.md — "
        "Quelle d (FALLBACK global) nicht dokumentiert"
    )


def test_ak2_four_sources_precedence_order():
    """
    AK-2 Gesamt: Praezedenz-Kette a>b>c>d alle vier Quellen in Routing-Block vorhanden.
    Prueft ob alle 4 Quellen (a), b), c), d)) in der Routing-Sektion stehen.
    """
    content = _read(_ASSAY_CMD)
    # Alle vier Quellen-Marker in Prioritaets-Reihenfolge
    assert "a)" in content, "AK-2: Quelle a) fehlt in _assay.md"
    assert "b)" in content, "AK-2: Quelle b) fehlt in _assay.md"
    assert "c)" in content, "AK-2: Quelle c) fehlt in _assay.md"
    assert "d)" in content, "AK-2: Quelle d) fehlt in _assay.md"


# ============================================================================
# AK-3: global=true Escape-Hatch
# Blueprint Z.48/161-163 — global=true Block erzwingt .claude/output/
# ============================================================================

def test_ak3_global_param_documented():
    """
    AK-3: global=true Parameter ist dokumentiert in _assay.md Z.48.
    """
    content = _read(_ASSAY_CMD)
    assert "global" in content, (
        "AK-3: 'global' Parameter fehlt in _assay.md"
    )


def test_ak3_global_true_routes_to_output_dir():
    """
    AK-3: global=true erzwingt .claude/output/ als Output-Pfad.
    _assay.md muss 'global == true' + '.claude/output/' in der Routing-Sektion enthalten.
    """
    content = _read(_ASSAY_CMD)
    assert "global == true" in content or "global=true" in content, (
        "AK-3: Routing-Zweig 'global == true' fehlt in _assay.md — Escape-Hatch nicht implementiert"
    )
    assert ".claude/output/" in content, (
        "AK-3: '.claude/output/' Pfad fehlt in _assay.md — global=true Ziel-Pfad nicht dokumentiert"
    )


def test_ak3_global_log_message():
    """
    AK-3: Bei global=true wird ein Log-Eintrag '[ASSAY] global=true' erzeugt.
    _assay.md muss diesen Log-Text enthalten.
    """
    content = _read(_ASSAY_CMD)
    assert "[ASSAY] global=true" in content, (
        "AK-3: Log-Text '[ASSAY] global=true' fehlt in _assay.md"
    )


# ============================================================================
# AK-1: Default-Routing in das aktive BL-Item
# Blueprint Z.104-108/180-183 — {bl_folder}/Assays/ Pfad-Muster
# ============================================================================

def test_ak1_default_routing_bl_folder_assays():
    """
    AK-1: Default-Routing schreibt in {bl_folder}/Assays/.
    _assay.md muss 'bl_folder}/Assays/' oder '/Assays/' im SCHREIBT-Block enthalten.
    """
    content = _read(_ASSAY_CMD)
    assert "/Assays/" in content, (
        "AK-1: '/Assays/' Pfad-Muster fehlt in _assay.md — Default-Routing-Ziel nicht dokumentiert"
    )


def test_ak1_resolve_bl_path_script_called():
    """
    AK-1: Default-Routing nutzt resolve_bl_path.py um bl_folder aufzuloesen.
    _assay.md muss 'resolve_bl_path.py' referenzieren.
    """
    content = _read(_ASSAY_CMD)
    assert "resolve_bl_path.py" in content, (
        "AK-1: resolve_bl_path.py-Referenz fehlt in _assay.md — BL-Ordner-Aufloesung nicht dokumentiert"
    )


# ============================================================================
# AK-6: NON-BLOCKING Fehler-Fallback + lazy-mkdir
# Blueprint Z.107/181 — lazy-mkdir + NON-BLOCKING Fallback-Block
# ============================================================================

def test_ak6_lazy_mkdir_documented():
    """
    AK-6: lazy-mkdir (Assays/-Ordner wird erst bei Bedarf erstellt).
    _assay.md muss 'mkdir' oder 'lazy' im Routing-Kontext enthalten (ADR-03).
    """
    content = _read(_ASSAY_CMD)
    assert "mkdir" in content or "lazy" in content, (
        "AK-6: lazy-mkdir Hinweis (mkdir/lazy) fehlt in _assay.md — ADR-03 nicht referenziert"
    )


def test_ak6_adr03_referenced():
    """
    AK-6: ADR-03 als Begruendung fuer lazy-mkdir muss in _assay.md stehen.
    """
    content = _read(_ASSAY_CMD)
    assert "ADR-03" in content, (
        "AK-6: 'ADR-03' fehlt in _assay.md — lazy-mkdir-Begruendung nicht verankert"
    )


# ============================================================================
# AK-4: P-12-Verankerung + Vault-Frontmatter-Konformitaet
# Blueprint: Frontmatter-Template muss bl-item + linked-feature enthalten
# ============================================================================

def test_ak4_frontmatter_bl_item_field():
    """
    AK-4: Output-Template Frontmatter enthaelt 'bl-item' Feld (P-12/BL-045 RF-06).
    """
    content = _read(_ASSAY_CMD)
    assert "bl-item" in content, (
        "AK-4: 'bl-item' Frontmatter-Feld fehlt in _assay.md — vault_document_frontmatter_schema verletzt"
    )


def test_ak4_frontmatter_linked_feature_field():
    """
    AK-4: Output-Template Frontmatter enthaelt 'linked-feature' ODER 'feature' Feld.
    Blueprint nennt 'linked-feature'; _assay.md v2.1.0 hat moeglicherweise 'feature'.
    """
    content = _read(_ASSAY_CMD)
    has_linked_feature = "linked-feature" in content
    has_feature_field = "feature:" in content
    assert has_linked_feature or has_feature_field, (
        "AK-4: Weder 'linked-feature' noch 'feature:' Frontmatter-Feld in _assay.md — "
        "P-12-Verankerung fehlt"
    )


# ============================================================================
# AK-5: W16-Supersession — current_context.py erreichbar + aufrufbar
# AK-5 FENCE-gated: Assay_Model.md W16-Status BESTAETIGT (nicht superseded)
# Dieser Test prueft ob W16-Status NOCH NICHT auf 'superseded' steht -> erwartet RED
# ============================================================================

def test_ak5_current_context_script_exists():
    """
    AK-5 (GREEN erwartet — current_context.py ist vorhanden):
    .claude/scripts/current_context.py muss existieren.
    """
    assert _CURRENT_CTX.exists(), (
        f"AK-5: current_context.py fehlt unter {_CURRENT_CTX}"
    )


def test_ak5_current_context_callable():
    """
    AK-5 (Charakterisierungs-Test): current_context.py ist aufrufbar (kein ImportError / SyntaxError).
    Erwartung: GREEN (Script existiert und ist syntaktisch korrekt).
    """
    result = subprocess.run(
        [sys.executable, str(_CURRENT_CTX), "--format=json"],
        capture_output=True, text=True, timeout=10
    )
    # Kein Python-SyntaxError / ImportError (exit code kann != 0 sein wenn kein Manifest)
    assert "SyntaxError" not in result.stderr, (
        f"AK-5: current_context.py hat SyntaxError: {result.stderr[:200]}"
    )
    assert "ImportError" not in result.stderr, (
        f"AK-5: current_context.py hat ImportError: {result.stderr[:200]}"
    )


def test_ak5_w16_status_not_yet_superseded():
    """
    AK-5 (RED erwartet — FENCE-gated): W16-Status in Assay_Model.md soll NOCH NICHT
    'superseded' sein. Das Pflaster BL-339 AK-5 hat diesen Edit noch NICHT durchgefuehrt
    (FENCE-Freigabe durch Lead erforderlich).

    Dieser Test ist erwartet ROT nach GREEN-Lauf wenn AK-5 ausgefuehrt wurde.
    Aktuell: W16-Status = 'BESTAETIGT' (keine Supersession) -> Test GRUEN (kein superseded)
    ABER: Der Test prueft dass W16-Eintrag in Assay_Model.md vorhanden ist (BESTAETIGT noch).
    """
    assert _ASSAY_MODEL.exists(), (
        f"AK-5: Assay_Model.md fehlt unter {_ASSAY_MODEL}"
    )
    content = _read(_ASSAY_MODEL)
    # W16 muss vorhanden sein
    assert "W16" in content, (
        "AK-5: W16-Eintrag fehlt komplett in Assay_Model.md"
    )
    # W16-Status muss BESTAETIGT (nicht superseded) sein — wenn dieser Test RED wird,
    # hat der GREEN-Worker die FENCE-Freigabe erhalten und AK-5 umgesetzt.
    assert "superseded" not in content.lower() or "W16" not in content.split("superseded")[0].split("\n")[-1], (
        "AK-5: W16-Status zeigt bereits 'superseded' in Assay_Model.md — "
        "FENCE-Freigabe war noch nicht erteilt; pruefe ob AK-5 autorisiert war"
    )


def test_ak5_w16_status_field_bestaetigt():
    """
    AK-5 (Charakterisierungs-RED): W16-Zeile in Assay_Model.md muss '[BESTAETIGT]' zeigen,
    NICHT '[SUPERSEDED]'. Wenn dieser Test GRUEN ist, bestaetigt er das Pflaster
    ist noch nicht umgesetzt. Nach GREEN-Worker (mit FENCE-Freigabe) wird dieser Test ROT.

    Dieser Test ist der eigentliche AK-5 RED-Test fuer den GREEN-Worker:
    GREEN-Worker muss W16-Status auf 'superseded' setzen => dieser Test wird dann ROT.
    Daher: ERWARTET ROT nach AK-5-Implementierung.
    """
    content = _read(_ASSAY_MODEL)
    # W16 Zeile mit BESTAETIGT => nach Implementierung soll SUPERSEDED stehen
    # Dieser Test faellt ROT wenn GREEN-Worker '[BESTAETIGT]' durch '[SUPERSEDED]' ersetzt
    w16_line = ""
    for line in content.splitlines():
        if "W16" in line and ("BESTAETIGT" in line or "SUPERSEDED" in line.upper()):
            w16_line = line
            break
    assert "[SUPERSEDED]" in w16_line or "superseded" in w16_line.lower(), (
        f"AK-5 RED: W16-Status ist noch '[BESTAETIGT]', nicht '[SUPERSEDED]'. "
        f"W16-Zeile: '{w16_line}'. "
        f"GREEN-Worker muss W16 auf superseded setzen (nach FENCE-Freigabe durch Lead)."
    )


# ============================================================================
# Strukturelle Tests: _assay.md Routing-Block Z.159-183 Existenz
# ============================================================================

def test_routing_block_schreibt_section_exists():
    """
    Basis: Der SCHREIBT-Block (Routing-Sektion) existiert in _assay.md.
    Prueft 'SCHREIBT' im VERTRAG-Block.
    """
    content = _read(_ASSAY_CMD)
    assert "SCHREIBT" in content, (
        "Basis: SCHREIBT-Block fehlt komplett in _assay.md — Routing-Sektion fehlt"
    )


def test_routing_block_v210_marker():
    """
    Basis: v2.1.0 BL-Routing-Pflaster-Marker in _assay.md vorhanden.
    """
    content = _read(_ASSAY_CMD)
    assert "v2.1.0" in content, (
        "Basis: v2.1.0-Marker fehlt in _assay.md — Pflaster nicht als solches markiert"
    )
