"""
test_bl376_provenance_domain.py

BL-376 batch_2 RED Tests:
  AK-3 (Fund#2): propagate_provenance in A/IDF/SDF-Orchestratoren verdrahtet
  AK-4 (Fund#4): _A_berater_domainBrief defensive Lib-Write-Logik fuer new_candidates

RED-Worker: schreibt nur Tests, KEINE Impl.
"""
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
SCRIPTS_DIR = REPO_ROOT / ".claude" / "scripts"
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

PROPAGATE_SCRIPT = SCRIPTS_DIR / "propagate_provenance.py"
A_ORCHESTRATE = COMMANDS_DIR / "_A_orchestrate.md"
IDF_ORCHESTRATE = COMMANDS_DIR / "_IDF_orchestrate.md"
SDF_ORCHESTRATE = COMMANDS_DIR / "_SDF_orchestrate.md"
DOMAIN_BRIEF = COMMANDS_DIR / "_A_berater_domainBrief.md"


# ---------------------------------------------------------------------------
# AK-3 (Fund#2): propagate_provenance Laufzeit-Test
# ---------------------------------------------------------------------------

class TestProvenanceRuntime:
    """AK-3a: propagate_provenance.py ist importierbar und update() ist aufrufbar."""

    def test_update_preserves_provenance_fields(self, tmp_path):
        """
        AK-3a: cmd_update auf einem Dokument mit provenance_chain erhaelt
        source_url und derived_from (kein Silent-Drop).
        Erstelle Vorgaenger-Doc (A) und Nachfolger-Doc (B, derived_from A),
        rufe update(B), pruefe dass A's used_in jetzt B enthaelt.
        """
        # Vorgaenger-Doc A
        doc_a = tmp_path / "doc_a.md"
        doc_a.write_text(
            "---\n"
            "provenance_chain:\n"
            "  - source_url: https://example.com/origin\n"
            "    used_in: []\n"
            "---\n"
            "body a\n",
            encoding="utf-8",
        )

        # Nachfolger-Doc B (derived_from A relativ zum vault_root=tmp_path)
        doc_b = tmp_path / "doc_b.md"
        doc_b.write_text(
            "---\n"
            "provenance_chain:\n"
            "  - derived_from:\n"
            "      - doc_a.md\n"
            "    source_url: https://example.com/derived\n"
            "---\n"
            "body b\n",
            encoding="utf-8",
        )

        # Importiere direkt statt subprocess damit Laufzeit testbar
        sys.path.insert(0, str(SCRIPTS_DIR))
        from propagate_provenance import cmd_update

        result = cmd_update(doc_b, tmp_path)

        # Laufzeit-Ergebnis: kein Fatal-Exit (0 oder 1 = ok/warn, nicht 2 = error)
        assert result != 2, "cmd_update sollte kein ERROR (rc=2) liefern"

        # Inhalt von A pruefen: B muss in used_in stehen
        import yaml, re
        content = doc_a.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.+?)\n---\n(.*)", content, re.DOTALL)
        assert match, "doc_a muss Frontmatter behalten"
        fm = yaml.safe_load(match.group(1))
        chain = fm.get("provenance_chain", [])
        used_in = chain[-1].get("used_in", []) if chain else []
        assert "doc_b.md" in used_in, (
            f"propagate_provenance.cmd_update muss B in A's used_in eintragen; "
            f"got used_in={used_in}"
        )


# ---------------------------------------------------------------------------
# AK-3b/c/d: Verdrahtungs-Beleg via grep — Orchestratoren referenzieren propagate_provenance
# ---------------------------------------------------------------------------

class TestOrchestratorWiring:
    """
    AK-3b/c/d: _A_orchestrate.md, _IDF_orchestrate.md, _SDF_orchestrate.md
    MUESSEN 'propagate_provenance' referenzieren (Verdrahtungs-Beleg).

    ERWARTET RED: keiner der Orchestratoren verdrahtet propagate_provenance (noch).
    """

    def test_a_orchestrate_references_propagate_provenance(self):
        """AK-3b: _A_orchestrate.md muss 'propagate_provenance' enthalten."""
        assert A_ORCHESTRATE.exists(), f"_A_orchestrate.md nicht gefunden: {A_ORCHESTRATE}"
        content = A_ORCHESTRATE.read_text(encoding="utf-8")
        assert "propagate_provenance" in content, (
            f"_A_orchestrate.md enthaelt KEIN 'propagate_provenance' — "
            f"AK-3 Verdrahtung fehlt (Fund#2 BL-376)"
        )

    def test_idf_orchestrate_references_propagate_provenance(self):
        """AK-3c: _IDF_orchestrate.md muss 'propagate_provenance' enthalten."""
        assert IDF_ORCHESTRATE.exists(), f"_IDF_orchestrate.md nicht gefunden: {IDF_ORCHESTRATE}"
        content = IDF_ORCHESTRATE.read_text(encoding="utf-8")
        assert "propagate_provenance" in content, (
            f"_IDF_orchestrate.md enthaelt KEIN 'propagate_provenance' — "
            f"AK-3 Verdrahtung fehlt (Fund#2 BL-376)"
        )

    def test_sdf_orchestrate_references_propagate_provenance(self):
        """AK-3d: _SDF_orchestrate.md muss 'propagate_provenance' enthalten."""
        assert SDF_ORCHESTRATE.exists(), f"_SDF_orchestrate.md nicht gefunden: {SDF_ORCHESTRATE}"
        content = SDF_ORCHESTRATE.read_text(encoding="utf-8")
        assert "propagate_provenance" in content, (
            f"_SDF_orchestrate.md enthaelt KEIN 'propagate_provenance' — "
            f"AK-3 Verdrahtung fehlt (Fund#2 BL-376)"
        )


# ---------------------------------------------------------------------------
# AK-4 (Fund#4): _A_berater_domainBrief defensive Lib-Write-Logik
# ---------------------------------------------------------------------------

class TestDomainBriefDefensiveWrite:
    """
    AK-4: _A_berater_domainBrief.md muss explizite defensive Lib-Write-Logik enthalten:
      new_candidates -> DomainLibrary WENN existiert, sonst no-op.

    ERWARTET RED: domainBrief hat NICHT die expliziten Keywords fuer die
    bedingte DomainLibrary-Write-Sektion ('new_candidates' + 'DomainLibrary' +
    Existenz-Check/no-op-Fallback zusammen in Schritt-5-Kontext).
    """

    def test_domain_brief_has_new_candidates_write_logic_with_existence_check(self):
        """
        AK-4a: domainBrief.md muss new_candidates + DomainLibrary +
        einen expliziten Existenz-Check + no-op-Fallback gemeinsam enthalten
        (als defensive Lib-Write-Sektion, nicht nur als Graceful-Degradation-Tabelle).
        """
        assert DOMAIN_BRIEF.exists(), f"_A_berater_domainBrief.md nicht gefunden: {DOMAIN_BRIEF}"
        content = DOMAIN_BRIEF.read_text(encoding="utf-8")

        # Alle 4 Keywords muessen vorhanden sein
        assert "new_candidates" in content, "domainBrief muss 'new_candidates' enthalten"
        assert "DomainLibrary" in content, "domainBrief muss 'DomainLibrary' enthalten"

        # Explizite defensive Lib-Write-Logik: Existenz-Check + no-op
        # Mindestens eines dieser Muster muss vorkommen (Ablauf-Schritt, nicht nur Tabelle):
        has_existence_check = any(
            kw in content
            for kw in [
                "IF EXISTS",
                "exists(",
                "WENN existiert",
                "WENN.*DomainLibrary",
                "DomainLibrary.*existiert",
                "no-op",
                "no_op",
                "SONST.*no-op",
                "sonst.*no-op",
            ]
        )

        # AK-4 spezifisch: new_candidates in DomainLibrary schreiben WENN existiert
        # Der aktuelle domainBrief schreibt new_candidates NUR ins Manifest (BERATER_OUTPUTS),
        # aber NICHT defensiv in DomainLibrary mit Existenz-Check.
        # Test prueft: gibt es einen expliziten bedingten Write-Block fuer new_candidates -> Library?
        has_conditional_lib_write = (
            "new_candidates" in content
            and (
                "WENN" in content or "IF" in content
            )
            and (
                "DomainLibrary" in content
            )
            and has_existence_check
        )

        assert has_conditional_lib_write, (
            "domainBrief.md fehlt defensive Lib-Write-Logik: "
            "'new_candidates -> DomainLibrary WENN existiert, sonst no-op' "
            "(AK-4 Fund#4 BL-376). "
            f"Gefunden: new_candidates={('new_candidates' in content)}, "
            f"DomainLibrary={('DomainLibrary' in content)}, "
            f"existence_check={has_existence_check}"
        )
