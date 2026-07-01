#!/usr/bin/env python3
"""Tests fuer BL-254 batch_2 AK-S3.2 + AK-S3.3.

AK-S3.2 (T1-T4): is_domain_term_write Guard — domain/factoring TERM-Writes werden
                  geblockt (fail-loud ValueError). PATTERN-Writes bleiben erlaubt.
AK-S3.3 (T5-T7): _SL_conformance.md Lesepfad-Verifikation — domain-terms.md ist
                  kanonische Quelle; DomainLibrary/ ist KEINE Term-Quelle.

T1-T4: RED (is_domain_term_write existiert noch nicht -> ImportError/AttributeError)
T5:    Regressions-PIN GRUEN (scope=domain Pattern-Write via add_arch unberuehrt)
T6/T7: GRUEN (Behavior _SL_conformance.md bereits korrekt)

RED-Worker: KEIN Impl-Code. Separater GREEN-Worker implementiert is_domain_term_write.
"""
import sys
from pathlib import Path

import pytest

COMMANDS_DIR = Path(__file__).resolve().parents[1] / "commands"

# ──────────────────────────────────────────────────────────────────────────────
# _read_cmd: bestehendes Hilfsmuster aus test_pattern_library.py (REUSE)
# ──────────────────────────────────────────────────────────────────────────────

def _read_cmd(name: str) -> str:
    return (COMMANDS_DIR / name).read_text(encoding="utf-8")


# ── AK-S3.2: is_domain_term_write Praedikat ──────────────────────────────────
# T1-T4 werden ROT: `is_domain_term_write` existiert noch nicht in pattern_library.py
# -> ImportError hebt alle vier Tests als ERROR/FAIL.

import pattern_library as pl  # noqa: E402  (import nach Hilfsfunktion, analog test_pattern_library.py)


# T1 — Guard-Praedikat True: scope=domain + target=terms -> TERM-Intent erkannt
def test_is_domain_term_write_true_domain_terms():
    # scope=domain UND target=terms -> True (Term-Intent auf Domain-Achse, nicht erlaubt)
    assert pl.is_domain_term_write("domain", "terms") is True


# T2 — Guard-Praedikat True: scope=factoring + target=naming -> auch TERM-Intent
def test_is_domain_term_write_true_factoring_naming():
    # scope=factoring UND target=naming -> True (Naming gehoert SemanticLibrary)
    assert pl.is_domain_term_write("factoring", "naming") is True


# T3 — Guard-Praedikat False: scope=semantic -> IMMER kanonisch, nie Guard-Pfad
def test_is_domain_term_write_false_for_semantic_scope():
    # scope=semantic ist der kanonische Term-Pfad -> False (kein Guard noetig)
    assert pl.is_domain_term_write("semantic", "terms") is False


# T4 — Guard-Pfad False: scope=domain OHNE Term-target -> legitimer Pattern-Write
def test_is_domain_term_write_false_domain_no_term_target():
    # scope=domain + target=None -> Fachregel-PATTERN-Write, erlaubt -> False
    assert pl.is_domain_term_write("domain", None) is False


# T5 — REGRESSIONS-PIN (soll GRUEN bleiben): add_arch scope=domain Pattern-Write unberuehrt
def test_add_arch_scope_domain_pattern_still_works(tmp_path):
    """scope=domain fuer Fachregel-PATTERNS (DOM-ID) darf NICHT durch den Guard brechen.

    Bestehendes Verhalten (5 gruene Tests in test_pattern_library.py haengen daran)
    muss unveraendert bleiben (BL-254 Option b: nur TERME stilllegen, PATTERNS okay).
    """
    # Minimal-Setup: DomainLibrary-Ordner anlegen (analog _seed_layer, scope=domain)
    lib_dir = tmp_path / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN"
    lib_dir.mkdir(parents=True, exist_ok=True)

    # add_arch mit scope=domain und KEINEM term-target muss eine DOM-ID anlegen OHNE ValueError
    # Signatur: add_arch(layer, name, ..., scope=..., vault_root=...)
    result = pl.add_arch(
        layer="BE-DOMAIN",
        name="Fachregel-Muster XYZ",
        description="Testbeschreibung fuer Regressions-PIN",
        scope="domain",
        vault_root=tmp_path,
    )
    # Hauptaussage: kein ValueError + Tuple (id, path, dedup_warn) zurueckgegeben
    assert result is not None
    dom_id = result[0] if isinstance(result, tuple) else str(result)
    assert "DOM-" in dom_id, f"Erwartete DOM-ID, bekam: {dom_id}"


# ── AK-S3.3: _SL_conformance.md Lesepfad-Verifikation ───────────────────────
# T6/T7 koennen bereits GRUEN sein (Behavior schon korrekt laut Blueprint-Befund)
# Zweck: Regressions-Verriegelung — falls jemand DomainLibrary als Term-Quelle einbaut,
#         schlaegt T7 an. T6 verriegelt den kanonischen Lesepfad.

# T6 — positiv: _SL_conformance.md liest SemanticLibrary/domain-terms.md (kanonisch)
def test_sl_conformance_reads_domain_terms_canonical():
    """Verriegelung: _SL_conformance.md muss domain-terms.md als Quelle benennen.

    Anker: L46 (VERTRAG-LIEST) + L168 (Worker-Prompt-Vorlage) in _SL_conformance.md.
    BL-254 Option B: SemanticLibrary/_project/{LAYER}/domain-terms.md ist Single-Source.
    """
    text = _read_cmd("_SL_conformance.md")
    # Kanonischer Lesepfad muss in der Datei stehen (Platzhalter-Form ist ok)
    assert "domain-terms.md" in text, (
        "_SL_conformance.md referenziert domain-terms.md nicht — Single-Source verletzt"
    )
    assert "SemanticLibrary" in text, (
        "_SL_conformance.md referenziert SemanticLibrary nicht — kanonischer Pfad fehlt"
    )


# T7 — negativ: _SL_conformance.md nutzt DomainLibrary NICHT als Domaenen-TERM-Quelle
def test_sl_conformance_does_not_read_domainlibrary_as_term_source():
    """Verriegelung: _SL_conformance.md darf DomainLibrary/ NICHT als Term-Lesequelle nennen.

    BL-254 AK-S3.3: KEIN zweiter Lesepfad fuer Terme ueber DomainLibrary/.
    INV-DB-2 (domainBrief liest DomainLibrary fuer PATTERNS non-blocking) ist
    kein Widerspruch — dieser Test prueft _SL_conformance, nicht domainBrief.
    """
    text = _read_cmd("_SL_conformance.md")
    # _SL_conformance darf DomainLibrary nicht als Term-Lesequelle im LIEST-Block haben.
    # Konservativ: "Libraries/DomainLibrary/" im VERTRAG-LIEST-Kontext pruefen.
    # Aktuell 0 Treffer erwartet (Blueprint-Befund: 0 Referenzen auf DomainLibrary als Term-Quelle).
    assert "Libraries/DomainLibrary/" not in text, (
        "_SL_conformance.md referenziert DomainLibrary/ als Lesepfad — Single-Source verletzt "
        "(Terme sollen AUSSCHLIESSLICH aus SemanticLibrary/domain-terms.md gelesen werden)"
    )


# ── AK-S3.2: Integrations-Tests — Guard-Enforcement am add_arch-Pfad (BL-254 batch_2 Iter-2) ──
# T8/T9: Luecke aus Iter-1: is_domain_term_write() existiert als Praedikat (T1-T4 GRUEN nach GREEN),
# aber add_arch() ruft ihn NICHT auf — ein domain-TERM-Write via add_arch geht ungeblockt durch.
# T8 MUSS ROT sein: Enforcement fehlt. T9 ist Regressions-PIN: Fachregel-PATTERN bleibt erlaubt.

# T8 — ENFORCEMENT ROT: add_arch(scope="domain", target="terms") muss ValueError raisen
def test_add_arch_domain_term_write_raises_value_error(tmp_path):
    """AK-S3.2-Enforcement: add_arch mit scope=domain + target='terms' MUSS ValueError raisen.

    BL-254 Single-Source-Guard: Domaenen-TERME gehoeren ausschliesslich in
    SemanticLibrary/domain-terms.md. Ein scope=domain-Write mit Term-Intent (target in
    {terms, naming, glossary}) auf DomainLibrary ist verboten (is_domain_term_write-Guard).

    AKTUELL (ohne Impl-Fix): add_arch akzeptiert kein target-Argument und ruft den Guard
    is_domain_term_write() nie auf — kein ValueError wird geworfen -> TEST FAELLT (ROT).
    Nach GREEN-Fix: add_arch(scope=domain, target='terms') raised ValueError mit Hinweis
    auf SemanticLibrary/domain-terms.md als kanonische Quelle.
    """
    lib_dir = tmp_path / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN"
    lib_dir.mkdir(parents=True, exist_ok=True)

    # add_arch mit scope=domain + target=terms -> MUSS ValueError raisen (Guard greift)
    # Signatur nach Fix: add_arch(layer, name, ..., scope=..., target=..., vault_root=...)
    with pytest.raises(ValueError, match="domain-terms.md"):
        pl.add_arch(
            layer="BE-DOMAIN",
            name="ZEVSP-Begriff",
            description="Fachlicher Domaenenbegriff",
            scope="domain",
            target="terms",   # Term-Intent: Guard muss ValueError raisen
            vault_root=tmp_path,
        )


# T9 — REGRESSIONS-PIN (soll GRUEN sein/bleiben): add_arch(scope=domain) ohne Term-target
def test_add_arch_domain_pattern_no_target_no_error(tmp_path):
    """AK-S3.2 Regressions-PIN: add_arch(scope=domain) OHNE term-target raised keinen ValueError.

    scope=domain ist fuer Fachregel-PATTERNS (W-DOM-3) weiterhin erlaubt. Der Guard
    is_domain_term_write(scope='domain', target=None) gibt False zurueck (T4-Verhalten).
    Kein ValueError — weder jetzt (vor Fix) noch nach GREEN-Fix.

    target wird NICHT explizit uebergeben: nach Fix ist target=None der Default (kein Term-Intent).
    Dieser Test soll sowohl vor als auch nach dem GREEN-Fix GRUEN bleiben (Regressions-PIN).
    """
    lib_dir = tmp_path / "Libraries" / "DomainLibrary" / "_project" / "BE-DOMAIN"
    lib_dir.mkdir(parents=True, exist_ok=True)

    # add_arch mit scope=domain + KEIN target (Default: None, kein Term-Intent) -> KEIN ValueError
    # target wird nicht uebergeben: nach Fix ist Default=None (Guard greift nicht)
    result = pl.add_arch(
        layer="BE-DOMAIN",
        name="Fachregel-Aggregat-Muster",
        description="Fachliches Pattern (kein Term), Guard greift NICHT",
        scope="domain",
        vault_root=tmp_path,
    )
    # Hauptaussage: kein ValueError + DOM-ID zurueckgegeben
    assert result is not None
    dom_id = result[0] if isinstance(result, tuple) else str(result)
    assert "DOM-" in dom_id, f"Erwartete DOM-ID, bekam: {dom_id}"
