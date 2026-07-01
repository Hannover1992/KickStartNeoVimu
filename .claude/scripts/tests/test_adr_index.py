"""test_adr_index.py — Failing Tests fuer BL-244 sub_batch_2: adr_index.py

RED-Phase (TDD): adr_index.py existiert noch NICHT.
Alle Tests in dieser Datei muessen mit ImportError / ModuleNotFoundError fehlschlagen.

Test-Faelle gemaess Blueprint 4_Blueprint/sub_batch_2/blueprint.md Abschnitt 5a:
  TC-PARSE-1..4   (parse_adr_frontmatter)
  TC-SCAN-1..4    (scan_adr_directory)
  TC-RENDER-1..3  (render_index)
  TC-IDEM-1..3    (write_index_idempotent)
  TC-E2E-1..3     (main / integration)
  TC-SCHEMA-1..5  (ID-Schema + Status-Whitelist + Vault-Fixtures)

Gesamt: 16 Test-Faelle (plus Schema-Fixture-Tests).

WICHTIG (INV-BUILD-GRAIN): Keine Implementierungs-Logik von adr_index.py hier.
Die Implementierung erfolgt durch einen separaten GREEN-Worker.
"""
import re
import sys
from pathlib import Path

import pytest

# Greenfield-Import — adr_index existiert noch NICHT.
# Dieser Import loest den RED-Zustand aus (ImportError / ModuleNotFoundError).
import adr_index  # noqa: E402  # type: ignore[import]

# ---------------------------------------------------------------------------
# Vault-Konstanten fuer Integrations-Tests (TC-SCHEMA-3/4 auf echten Vault-Dateien)
# ---------------------------------------------------------------------------
VAULT_ROOT = Path("C:/Users/hanno/Documents/Work/Wissen/Berechtigung/OmniCommand/OmniCommand")
ADR_DIR_VAULT = VAULT_ROOT / "Libraries" / "ADR"
TEMPLATE_MD = ADR_DIR_VAULT / "TEMPLATE.md"
ADR_DOMAIN_MD = ADR_DIR_VAULT / "ADR-domain-single-source.md"


# ===========================================================================
# Kategorie: frontmatter-parse (parse_adr_frontmatter)
# ===========================================================================


class TestParseAdrFrontmatter:
    """TC-PARSE-1..4: parse_adr_frontmatter — isolierte Parser-Tests."""

    def test_tc_parse_1_pflichtfelder_vollstaendiges_frontmatter(self, tmp_path):
        """TC-PARSE-1 (T-S2-01 analog): Vollstaendiges kanonisches Frontmatter wird korrekt geparst.

        Gegeben: ADR-Datei mit vollstaendigem kanonischem Frontmatter (type:adr, adr_nr, status, bl-item).
        Wenn:    parse_adr_frontmatter(path) aufgerufen.
        Dann:    dict['type'] == 'adr', dict['adr_nr'] == 'BL-244-ADR-001', kein Exception.
        """
        adr_file = tmp_path / "BL-244-ADR-001.md"
        adr_file.write_text(
            "---\n"
            "type: adr\n"
            "adr_nr: BL-244-ADR-001\n"
            "title: Test-ADR\n"
            "status: DRAFT\n"
            "bl-item: BL-244\n"
            "created: 2026-06-22\n"
            "tags:\n"
            "  - bl/BL-244\n"
            "  - type/adr\n"
            "---\n"
            "\n"
            "# Test ADR body\n",
            encoding="utf-8",
        )

        result = adr_index.parse_adr_frontmatter(adr_file)

        assert result is not None
        assert result["type"] == "adr"
        assert result["adr_nr"] == "BL-244-ADR-001"
        assert result["status"] == "DRAFT"
        assert result["bl-item"] == "BL-244"

    def test_tc_parse_2_keine_frontmatter_gibt_none(self, tmp_path):
        """TC-PARSE-2: Markdown-Datei ohne --- Trenner gibt None zurueck.

        Gegeben: Datei ohne YAML-Frontmatter-Block (reiner Markdown-Body).
        Wenn:    parse_adr_frontmatter(path) aufgerufen.
        Dann:    Rueckgabe ist None (kein Exception).
        """
        plain_md = tmp_path / "no_frontmatter.md"
        plain_md.write_text(
            "# Nur ein Titel\n\nKein Frontmatter hier.\n",
            encoding="utf-8",
        )

        result = adr_index.parse_adr_frontmatter(plain_md)

        assert result is None

    def test_tc_parse_3_frontmatter_ohne_type_adr(self, tmp_path):
        """TC-PARSE-3: CONVENTION.md-Fixture mit Frontmatter ohne type:adr gibt dict != adr.

        Gegeben: Datei mit Frontmatter, aber type != 'adr' (type:convention).
        Wenn:    parse_adr_frontmatter(path) aufgerufen.
        Dann:    result ist dict mit type != 'adr' — kein Exception.
        """
        convention_file = tmp_path / "CONVENTION.md"
        convention_file.write_text(
            "---\n"
            "type: convention\n"
            "title: ADR-Konvention\n"
            "---\n"
            "\n"
            "# ADR Konvention\n",
            encoding="utf-8",
        )

        result = adr_index.parse_adr_frontmatter(convention_file)

        assert result is not None
        assert result.get("type") != "adr"

    def test_tc_parse_4_leerer_frontmatter_block_kein_exception(self, tmp_path):
        """TC-PARSE-4: Leerer Frontmatter-Block (---\n---\n) gibt leer dict oder None — kein Exception.

        Gegeben: Datei mit leerem YAML-Block zwischen --- Trennern.
        Wenn:    parse_adr_frontmatter(path) aufgerufen.
        Dann:    Rueckgabe ist {} oder None (beide akzeptabel), kein Exception.
        """
        empty_fm = tmp_path / "empty_frontmatter.md"
        empty_fm.write_text(
            "---\n---\n\n# Body\n",
            encoding="utf-8",
        )

        result = adr_index.parse_adr_frontmatter(empty_fm)

        # Beide Varianten akzeptabel (implementierungsabhaengig)
        assert result is None or result == {}


# ===========================================================================
# Kategorie: scan + skip-non-adr (scan_adr_directory)
# ===========================================================================


class TestScanAdrDirectory:
    """TC-SCAN-1..4: scan_adr_directory — Directory-Scan-Logik."""

    def _write_adr(self, directory: Path, filename: str, adr_nr: str, status: str = "DRAFT") -> Path:
        """Hilfsmethode: schreibt eine minimale ADR-Datei."""
        path = directory / filename
        path.write_text(
            f"---\ntype: adr\nadr_nr: {adr_nr}\ntitle: Test {adr_nr}\nstatus: {status}\nbl-item: BL-001\ncreated: 2026-06-22\ntags: []\n---\n\n# Body\n",
            encoding="utf-8",
        )
        return path

    def test_tc_scan_1_drei_adrs_plus_convention_gibt_drei_dicts(self, tmp_path):
        """TC-SCAN-1 (T-S3-01): 3 ADR-Fixtures + 1 CONVENTION.md -> 3 dicts.

        Gegeben: Verzeichnis mit adr1.md, adr2.md, adr3.md (type:adr) + CONVENTION.md (kein type:adr).
        Wenn:    scan_adr_directory(adr_dir) aufgerufen.
        Dann:    len(result) == 3, alle dicts haben type=='adr', CONVENTION.md nicht enthalten.
        """
        adr_dir = tmp_path / "ADR"
        adr_dir.mkdir()

        self._write_adr(adr_dir, "adr1.md", "BL-001-ADR-001")
        self._write_adr(adr_dir, "adr2.md", "BL-002-ADR-001")
        self._write_adr(adr_dir, "adr3.md", "BL-003-ADR-001")

        convention = adr_dir / "CONVENTION.md"
        convention.write_text(
            "---\ntype: convention\ntitle: ADR-Konvention\n---\n\n# Konvention\n",
            encoding="utf-8",
        )

        result = adr_index.scan_adr_directory(adr_dir)

        assert len(result) == 3
        for item in result:
            assert item["type"] == "adr"
        adr_nrs = {item["adr_nr"] for item in result}
        assert "BL-001-ADR-001" in adr_nrs
        assert "BL-002-ADR-001" in adr_nrs
        assert "BL-003-ADR-001" in adr_nrs

    def test_tc_scan_2_template_und_index_werden_uebersprungen(self, tmp_path):
        """TC-SCAN-2: TEMPLATE.md + _index.md werden korrekt uebersprungen.

        Gegeben: ADR-Dir mit 1 echten ADR + TEMPLATE.md + _index.md (doc_type:library-index).
        Wenn:    scan_adr_directory(adr_dir) aufgerufen.
        Dann:    len(result) == 1 (nur die echte ADR).
        """
        adr_dir = tmp_path / "ADR"
        adr_dir.mkdir()

        self._write_adr(adr_dir, "BL-244-ADR-001.md", "BL-244-ADR-001")

        template = adr_dir / "TEMPLATE.md"
        template.write_text(
            "---\ntype: template\ntitle: ADR Template\n---\n\n# Template\n",
            encoding="utf-8",
        )

        index_md = adr_dir / "_index.md"
        index_md.write_text(
            "---\ndoc_type: library-index\ngenerated_at: 2026-06-22T00:00:00\nadr_count: 1\n---\n\n| adr_nr | title |\n|--------|-------|\n",
            encoding="utf-8",
        )

        result = adr_index.scan_adr_directory(adr_dir)

        assert len(result) == 1
        assert result[0]["adr_nr"] == "BL-244-ADR-001"

    def test_tc_scan_3_migrierte_adr_domain_single_source_wird_erfasst(self, tmp_path):
        """TC-SCAN-3: Migrierte ADR-domain-single-source.md (type:adr, adr_nr:BL-254-ADR-001) wird erfasst.

        Gegeben: ADR-Dir mit Fixture fuer ADR-domain-single-source.md mit type:adr.
        Wenn:    scan_adr_directory(adr_dir) aufgerufen.
        Dann:    result enthaelt dict mit adr_nr == 'BL-254-ADR-001' und status == 'ACCEPTED'.
        """
        adr_dir = tmp_path / "ADR"
        adr_dir.mkdir()

        migrated = adr_dir / "ADR-domain-single-source.md"
        migrated.write_text(
            "---\n"
            "type: adr\n"
            "adr_nr: BL-254-ADR-001\n"
            "title: Domain Single Source\n"
            "status: ACCEPTED\n"
            "bl-item: BL-254\n"
            "created: 2026-06-01\n"
            "tags: []\n"
            "---\n"
            "\n"
            "# ADR Body\n",
            encoding="utf-8",
        )

        result = adr_index.scan_adr_directory(adr_dir)

        assert len(result) == 1
        assert result[0]["adr_nr"] == "BL-254-ADR-001"
        assert result[0]["status"] == "ACCEPTED"

    def test_tc_scan_4_leeres_verzeichnis_gibt_leere_liste(self, tmp_path):
        """TC-SCAN-4: Leeres Verzeichnis -> leere Liste.

        Gegeben: Leeres tmp_path-Verzeichnis (keine Dateien).
        Wenn:    scan_adr_directory(empty_dir) aufgerufen.
        Dann:    result == [].
        """
        empty_dir = tmp_path / "empty_adr"
        empty_dir.mkdir()

        result = adr_index.scan_adr_directory(empty_dir)

        assert result == []


# ===========================================================================
# Kategorie: index-render (render_index)
# ===========================================================================


class TestRenderIndex:
    """TC-RENDER-1..3: render_index — Tabellen-Render-Logik."""

    def _make_adr_dict(self, adr_nr: str, title: str = "Test", status: str = "DRAFT",
                       bl_item: str = "BL-001", created: str = "2026-06-22",
                       tags: list | None = None) -> dict:
        """Hilfsmethode: minimales ADR-Dict."""
        return {
            "adr_nr": adr_nr,
            "title": title,
            "status": status,
            "bl-item": bl_item,
            "created": created,
            "tags": tags or [],
        }

    def test_tc_render_1_output_enthaelt_tabellenheader_und_n_zeilen(self):
        """TC-RENDER-1 (T-S3-02): Output enthaelt Tabellen-Header + N Daten-Zeilen + adr_count im Frontmatter.

        Gegeben: Liste von 2 ADR-Dicts + generated_at.
        Wenn:    render_index(adrs, generated_at) aufgerufen.
        Dann:    result enthaelt Tabellen-Header-Zeile mit 'adr_nr', 'title', 'status'.
                 result enthaelt genau 2 Daten-Zeilen (Pipe-getrennt).
                 result enthaelt 'adr_count: 2' im Frontmatter-Block.
        """
        adrs = [
            self._make_adr_dict("BL-001-ADR-001", "Erste ADR"),
            self._make_adr_dict("BL-002-ADR-001", "Zweite ADR"),
        ]
        generated_at = "2026-06-22T00:00:00"

        result = adr_index.render_index(adrs, generated_at)

        assert "| adr_nr |" in result
        assert "| title |" in result
        assert "| status |" in result
        assert "adr_count: 2" in result
        # 2 Daten-Zeilen (Pipe-getrennte Zeilen die NICHT der Header oder Separator sind)
        data_lines = [
            line for line in result.splitlines()
            if line.strip().startswith("|") and "adr_nr" not in line and "---" not in line
        ]
        assert len(data_lines) == 2

    def test_tc_render_2_leere_liste_adr_count_0(self):
        """TC-RENDER-2: Leere ADR-Liste -> adr_count: 0 im Frontmatter + Header vorhanden + keine Daten-Zeilen.

        Gegeben: adrs = [], generated_at = '2026-06-22T00:00:00'.
        Wenn:    render_index(adrs, generated_at) aufgerufen.
        Dann:    'adr_count: 0' im Output, Tabellen-Header vorhanden, keine Daten-Zeilen.
        """
        result = adr_index.render_index([], "2026-06-22T00:00:00")

        assert "adr_count: 0" in result
        assert "| adr_nr |" in result
        data_lines = [
            line for line in result.splitlines()
            if line.strip().startswith("|") and "adr_nr" not in line and "---" not in line
        ]
        assert len(data_lines) == 0

    def test_tc_render_3_tags_liste_wird_korrekt_serialisiert(self):
        """TC-RENDER-3: Tags-Liste wird kommasepariert in der Tabellen-Zeile serialisiert.

        Gegeben: ADR-Dict mit tags: ['bl/BL-244', 'type/adr'].
        Wenn:    render_index([adr_dict], ...) aufgerufen.
        Dann:    Tabellen-Zeile enthaelt 'bl/BL-244' und 'type/adr' (kommasepariert oder aequivalent).
        """
        adr_dict = self._make_adr_dict(
            "BL-244-ADR-001",
            tags=["bl/BL-244", "type/adr"],
        )

        result = adr_index.render_index([adr_dict], "2026-06-22T00:00:00")

        assert "bl/BL-244" in result
        assert "type/adr" in result


# ===========================================================================
# Kategorie: idempotenz (write_index_idempotent)
# ===========================================================================


class TestWriteIndexIdempotent:
    """TC-IDEM-1..3: write_index_idempotent — Hash-basierter idempotenter Schreiber."""

    def test_tc_idem_1_identischer_content_gibt_false(self, tmp_path):
        """TC-IDEM-1 (T-S3-03a): Identischer Content -> kein Write (return False).

        Gegeben: output_path existiert mit Content X.
        Wenn:    write_index_idempotent(X, output_path) erneut aufgerufen.
        Dann:    Rueckgabe False, Datei-Inhalt unveraendert.
        """
        output_path = tmp_path / "_index.md"
        content = "---\ndoc_type: library-index\nadr_count: 1\n---\n\n| adr_nr | title |\n|--------|-------|\n| BL-001-ADR-001 | Test |\n"
        output_path.write_text(content, encoding="utf-8")

        result = adr_index.write_index_idempotent(content, output_path)

        assert result is False
        assert output_path.read_text(encoding="utf-8") == content

    def test_tc_idem_2_geaenderter_content_gibt_true(self, tmp_path):
        """TC-IDEM-2 (T-S3-03b): Geaenderter Content -> Write (return True).

        Gegeben: output_path existiert mit Content X.
        Wenn:    write_index_idempotent(X + ' geaendert', output_path) aufgerufen.
        Dann:    Rueckgabe True, Datei-Inhalt aktualisiert.
        """
        output_path = tmp_path / "_index.md"
        original = "---\ndoc_type: library-index\nadr_count: 1\n---\n\n| adr_nr | title |\n|--------|-------|\n| BL-001-ADR-001 | Alt |\n"
        output_path.write_text(original, encoding="utf-8")

        new_content = "---\ndoc_type: library-index\nadr_count: 2\n---\n\n| adr_nr | title |\n|--------|-------|\n| BL-001-ADR-001 | Alt |\n| BL-002-ADR-001 | Neu |\n"
        result = adr_index.write_index_idempotent(new_content, output_path)

        assert result is True
        assert output_path.read_text(encoding="utf-8") == new_content

    def test_tc_idem_3_datei_existiert_nicht_schreibt_und_gibt_true(self, tmp_path):
        """TC-IDEM-3: Datei existiert nicht -> Write (return True), Datei neu angelegt.

        Gegeben: output_path existiert nicht.
        Wenn:    write_index_idempotent(content, output_path) aufgerufen.
        Dann:    Rueckgabe True, Datei wird neu angelegt mit korrektem Inhalt.
        """
        output_path = tmp_path / "new_index.md"
        content = "---\ndoc_type: library-index\nadr_count: 0\n---\n\n| adr_nr | title |\n|--------|-------|\n"

        assert not output_path.exists()

        result = adr_index.write_index_idempotent(content, output_path)

        assert result is True
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == content


# ===========================================================================
# Kategorie: end-to-end / Integration (main)
# ===========================================================================


class TestE2E:
    """TC-E2E-1..3: main() und vollstaendiger Scan->Render->Write-Ablauf."""

    def _write_adr(self, directory: Path, filename: str, adr_nr: str, status: str = "DRAFT") -> Path:
        path = directory / filename
        path.write_text(
            f"---\ntype: adr\nadr_nr: {adr_nr}\ntitle: ADR {adr_nr}\nstatus: {status}\nbl-item: BL-001\ncreated: 2026-06-22\ntags: []\n---\n\n# Body\n",
            encoding="utf-8",
        )
        return path

    def test_tc_e2e_1_main_generiert_korrekten_index(self, tmp_path):
        """TC-E2E-1 (T-S3-04): main() auf tmp_path-Fixture -> _index.md korrekt.

        Gegeben: tmp_path/Libraries/ADR/ mit 2 ADR-Fixtures + CONVENTION.md.
        Wenn:    main() mit --adr-dir und --output Argumenten aufgerufen.
        Dann:    _index.md existiert mit 2 Daten-Zeilen und adr_count: 2.
        """
        adr_dir = tmp_path / "Libraries" / "ADR"
        adr_dir.mkdir(parents=True)

        self._write_adr(adr_dir, "BL-001-ADR-001.md", "BL-001-ADR-001")
        self._write_adr(adr_dir, "BL-002-ADR-001.md", "BL-002-ADR-001")

        convention = adr_dir / "CONVENTION.md"
        convention.write_text(
            "---\ntype: convention\ntitle: Konvention\n---\n\n# Konvention\n",
            encoding="utf-8",
        )

        output_path = tmp_path / "_index.md"

        # main() muss --adr-dir und --output CLI-Parameter unterstuetzen
        sys.argv = [
            "adr_index.py",
            "--adr-dir", str(adr_dir),
            "--output", str(output_path),
        ]
        adr_index.main()

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "adr_count: 2" in content
        data_lines = [
            line for line in content.splitlines()
            if line.strip().startswith("|") and "adr_nr" not in line and "---" not in line
        ]
        assert len(data_lines) == 2

    def test_tc_e2e_2_zweiter_aufruf_ohne_aenderungen_idempotent(self, tmp_path):
        """TC-E2E-2: Zweiter Aufruf ohne Aenderungen -> identischer Output (Idempotenz E2E).

        Gegeben: TC-E2E-1 wurde ausgefuehrt (_index.md existiert).
        Wenn:    main() erneut mit gleichen Argumenten aufgerufen.
        Dann:    _index.md Inhalt byte-identisch zum vorherigen Aufruf.
        """
        adr_dir = tmp_path / "Libraries" / "ADR"
        adr_dir.mkdir(parents=True)

        self._write_adr(adr_dir, "BL-001-ADR-001.md", "BL-001-ADR-001")

        output_path = tmp_path / "_index.md"

        # Erster Aufruf
        sys.argv = [
            "adr_index.py",
            "--adr-dir", str(adr_dir),
            "--output", str(output_path),
        ]
        adr_index.main()
        content_first = output_path.read_text(encoding="utf-8")

        # Zweiter Aufruf — ohne ADR-Aenderungen
        adr_index.main()
        content_second = output_path.read_text(encoding="utf-8")

        assert content_first == content_second

    def test_tc_e2e_3_duplikat_adr_nr_kein_crash(self, tmp_path):
        """TC-E2E-3 (T-S1-02 analog): Duplikat-adr_nr-Scan wirft keinen Exception.

        Gegeben: 2 ADR-Fixtures mit identischem adr_nr-Wert 'BL-001-ADR-001'.
        Wenn:    scan_adr_directory(adr_dir) aufgerufen.
        Dann:    result enthaelt 1 oder 2 Eintraege (kein Exception; Scanner toleriert Duplikate).
        """
        adr_dir = tmp_path / "ADR"
        adr_dir.mkdir()

        adr1 = adr_dir / "adr_a.md"
        adr1.write_text(
            "---\ntype: adr\nadr_nr: BL-001-ADR-001\ntitle: Erste Kopie\nstatus: DRAFT\nbl-item: BL-001\ncreated: 2026-06-22\ntags: []\n---\n",
            encoding="utf-8",
        )
        adr2 = adr_dir / "adr_b.md"
        adr2.write_text(
            "---\ntype: adr\nadr_nr: BL-001-ADR-001\ntitle: Zweite Kopie\nstatus: DRAFT\nbl-item: BL-001\ncreated: 2026-06-22\ntags: []\n---\n",
            encoding="utf-8",
        )

        # Kein Exception erwartet; 1 oder 2 Eintraege akzeptabel
        result = adr_index.scan_adr_directory(adr_dir)
        assert len(result) in (1, 2)


# ===========================================================================
# Kategorie: ID-Schema-Validierung (TC-SCHEMA-1..5)
# ===========================================================================


class TestSchemaValidation:
    """TC-SCHEMA-1..5: adr_nr-Regex, Status-Whitelist, Vault-Fixtures."""

    ADR_NR_REGEX = r"^BL-\d+-ADR-\d{3}$"

    def test_tc_schema_1_adr_nr_regex_valid_und_invalid(self):
        """TC-SCHEMA-1 (T-S1-01): adr_nr Regex matcht korrekte Werte + lehnt fehlerhafte ab.

        adr_index.py muss das Regex r'^BL-\\d+-ADR-\\d{3}$' verwenden (oder aequivalent).
        """
        # Gueltige adr_nr-Werte
        valid = ["BL-244-ADR-001", "BL-1-ADR-001", "BL-254-ADR-001", "BL-100-ADR-999"]
        for val in valid:
            assert re.match(self.ADR_NR_REGEX, val), f"Expected match for: {val}"

        # Ungueltige adr_nr-Werte
        invalid = ["ADR-001", "BL-244-ADR-1", "BL-244_ADR_001", "BL244-ADR-001", "BL-244-ADR-0001"]
        for val in invalid:
            assert not re.match(self.ADR_NR_REGEX, val), f"Expected no match for: {val}"

        # adr_index.py muss ADR_NR_REGEX oder aequivalente Konstante/Funktion exportieren
        # Wir testen hier, dass das Modul das Regex korrekt definiert hat.
        # Wenn adr_index.ADR_NR_REGEX nicht existiert, schlaegt dieser Test fehl (RED).
        assert hasattr(adr_index, "ADR_NR_REGEX") or hasattr(adr_index, "validate_adr_nr"), \
            "adr_index muss ADR_NR_REGEX Konstante oder validate_adr_nr Funktion exportieren"

    def test_tc_schema_2_status_whitelist(self):
        """TC-SCHEMA-2 (T-S2-02): Status-Whitelist — gueltige Status kein Fehler, ungueltige -> False/Exception.

        adr_index.py muss STATUS_WHITELIST oder validate_adr_status exportieren.
        """
        valid_statuses = ["DRAFT", "ACCEPTED", "SUPERSEDED", "RETIRED"]
        invalid_statuses = ["INVALID", "draft", "accepted", "IN_PROGRESS"]

        # validate_adr_status oder STATUS_WHITELIST muss im Modul vorhanden sein
        if hasattr(adr_index, "validate_adr_status"):
            for s in valid_statuses:
                assert adr_index.validate_adr_status(s) is True, f"Expected valid: {s}"
            for s in invalid_statuses:
                assert adr_index.validate_adr_status(s) is False, f"Expected invalid: {s}"
        elif hasattr(adr_index, "STATUS_WHITELIST"):
            for s in valid_statuses:
                assert s in adr_index.STATUS_WHITELIST, f"Expected in whitelist: {s}"
            for s in invalid_statuses:
                assert s not in adr_index.STATUS_WHITELIST, f"Expected not in whitelist: {s}"
        else:
            pytest.fail(
                "adr_index muss STATUS_WHITELIST Konstante oder validate_adr_status Funktion exportieren"
            )

    @pytest.mark.integration
    def test_tc_schema_3_template_md_besteht_schema_validator(self):
        """TC-SCHEMA-3 (T-S2-03): Libraries/ADR/TEMPLATE.md (sub_batch_1) besteht Schema-Validierung.

        Voraussetzung: sub_batch_1 DONE (TEMPLATE.md existiert im Vault).
        Wenn: parse_adr_frontmatter(TEMPLATE.md) aufgerufen.
        Dann: kein Exception, result ist dict (type:adr vorhanden als Platzhalter oder korrekt gesetzt).
        """
        if not TEMPLATE_MD.exists():
            pytest.skip(f"sub_batch_1 nicht abgeschlossen: {TEMPLATE_MD} fehlt")

        result = adr_index.parse_adr_frontmatter(TEMPLATE_MD)

        # TEMPLATE.md darf kein None ergeben (muss Frontmatter haben)
        assert result is not None, "TEMPLATE.md muss YAML-Frontmatter haben"
        # type-Feld muss vorhanden sein (als Platzhalter "{BL-ID}-ADR-{NNN}" oder korrekt)
        # Akzeptabel: jeder nicht-None Wert fuer type
        assert "type" in result or "adr_nr" in result, \
            "TEMPLATE.md Frontmatter muss mindestens type oder adr_nr enthalten"

    @pytest.mark.integration
    def test_tc_schema_4_migrierte_adr_domain_single_source_vault(self):
        """TC-SCHEMA-4 (T-S2-04): Vault Libraries/ADR/ADR-domain-single-source.md (sub_batch_1 migriert).

        Voraussetzung: sub_batch_1 DONE (ADR-domain-single-source.md migriert).
        Wenn: parse_adr_frontmatter(ADR_DOMAIN_MD) aufgerufen.
        Dann: result['type'] == 'adr', result['adr_nr'] == 'BL-254-ADR-001', kein 'doc_type'.
        """
        if not ADR_DOMAIN_MD.exists():
            pytest.skip(f"sub_batch_1 nicht abgeschlossen: {ADR_DOMAIN_MD} fehlt")

        result = adr_index.parse_adr_frontmatter(ADR_DOMAIN_MD)

        assert result is not None, "ADR-domain-single-source.md muss Frontmatter haben"
        assert result.get("type") == "adr", f"type muss 'adr' sein, got: {result.get('type')}"
        assert result.get("adr_nr") == "BL-254-ADR-001", f"adr_nr muss 'BL-254-ADR-001' sein, got: {result.get('adr_nr')}"
        assert "doc_type" not in result, "Legacy-Feld 'doc_type' muss entfernt sein (sub_batch_1 Migration)"

    def test_tc_schema_5_boundaries_presentation_nicht_als_adr_klassifiziert(self, tmp_path):
        """TC-SCHEMA-5 (T-S5-01): Boundaries-Praesentation-Fixture mit type:boundaries-presentation.

        Wenn: Typ-Check auf result['type'] != 'adr'.
        Dann: True — Boundaries-Praesentation wird NICHT als ADR klassifiziert.
              scan_adr_directory wuerde diese Datei korrekt ueberspringen.
        """
        adr_dir = tmp_path / "ADR"
        adr_dir.mkdir()

        boundaries_file = adr_dir / "Boundaries-Presentation.md"
        boundaries_file.write_text(
            "---\n"
            "type: boundaries-presentation\n"
            "title: Architektur-Grenzen Praesentation\n"
            "created: 2026-06-22\n"
            "---\n"
            "\n"
            "# Boundaries Praesentation\n",
            encoding="utf-8",
        )

        # Test 1: parse_adr_frontmatter gibt dict mit type != 'adr'
        result = adr_index.parse_adr_frontmatter(boundaries_file)
        assert result is not None
        assert result.get("type") != "adr", \
            "boundaries-presentation darf nicht als 'adr' klassifiziert werden"

        # Test 2: scan_adr_directory ueberspringt die Datei (leere Liste)
        scan_result = adr_index.scan_adr_directory(adr_dir)
        assert len(scan_result) == 0, \
            "scan_adr_directory muss boundaries-presentation ueberspringen (kein type:adr)"
