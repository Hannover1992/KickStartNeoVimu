"""
test_vault_node_health.py -- BL-443 batch_1 AK-1: RED-Tests fuer vault_node_health.py

Modul-API (vault_node_health.py muss implementieren):

    from dataclasses import dataclass
    from pathlib import Path
    from typing import Literal

    Severity = Literal["CORRUPT", "WARN"]
    Kind = Literal["NULL_BYTES", "EMPTY", "WHITESPACE_FLOOD", "NO_FRONTMATTER"]

    @dataclass
    class NodeHealthResult:
        path: Path
        kind: Kind
        severity: Severity
        detail: str  # z.B. "count=5910,pct=100.0%"

    def scan_vault_node(path: Path) -> NodeHealthResult | None:
        '''
        Prueft einen einzelnen Node. Gibt None zurueck wenn gesund.
        NULL_BYTES / EMPTY / WHITESPACE_FLOOD -> severity=CORRUPT.
        NO_FRONTMATTER -> severity=WARN.
        Scan-Reihenfolge (Prioritaet): NULL_BYTES > EMPTY > WHITESPACE_FLOOD > NO_FRONTMATTER.
        '''

    def scan_vault_backlog(backlog_dir: Path) -> list[NodeHealthResult]:
        '''
        Scannt alle *.md-Files in backlog_dir (nur flat + eine Ebene Subdirs, NICHT vollstaendig rekursiv).
        Gibt Liste aller kranken Nodes zurueck (leer = alles gesund).
        Directories werden ignoriert (nur is_file() + suffix=='.md').
        '''

Raises: kein public raise — OSError beim Lesen wird zu NodeHealthResult(kind=READ_ERROR) oder
        still ignoriert (Impl-Entscheidung des GREEN-Workers, Tests pruefen das nicht).

RED-Beweis: vault_node_health.py existiert noch nicht -> ImportError -> alle Tests FAIL.

Run: py -3 -m pytest .claude/scripts/test_vault_node_health.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

# Dieser Import MUSS fehlschlagen bis GREEN-Worker vault_node_health.py implementiert.
# RED-Phase: ImportError erwartet.
from vault_node_health import scan_vault_node, scan_vault_backlog, NodeHealthResult  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def null_byte_file(tmp_path) -> Path:
    """5910-Byte-File, alle 0x00 -- exakt wie die 12 bekannten korrupten Nodes."""
    p = tmp_path / "BL-285.md"
    p.write_bytes(b"\x00" * 5910)
    return p


@pytest.fixture
def empty_file(tmp_path) -> Path:
    """0-Byte-File."""
    p = tmp_path / "BL-empty.md"
    p.write_bytes(b"")
    return p


@pytest.fixture
def whitespace_flood_file(tmp_path) -> Path:
    """Datei nur aus Spaces, Newlines und Tabs -- kein sichtbarer Inhalt."""
    p = tmp_path / "BL-ws.md"
    p.write_text("\n   \t  \n   \n\t\t   \n", encoding="utf-8")
    return p


@pytest.fixture
def healthy_file(tmp_path) -> Path:
    """Valider YAML-Frontmatter + Body -- soll als gesund gelten."""
    p = tmp_path / "BL-healthy.md"
    content = "---\nid: BL-healthy\ntitle: Healthy Node\nstatus: DRAFT\n---\n\n# Healthy\n\nThis node is fine.\n"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def no_frontmatter_file(tmp_path) -> Path:
    """Valider Text aber kein '---'-Frontmatter-Block."""
    p = tmp_path / "BL-nofm.md"
    p.write_text("# No Frontmatter Here\n\nJust plain text without YAML block.\n", encoding="utf-8")
    return p


@pytest.fixture
def mixed_backlog_dir(tmp_path) -> Path:
    """
    Verzeichnis mit 2 CORRUPT-Files (null_byte + whitespace_flood) + 1 gesundem File.
    Zusaetzlich: ein Unterverzeichnis (Dir-Sibling) der Typ-BL-142-Situation.
    """
    # korrupt: null bytes
    (tmp_path / "BL-corrupt-null.md").write_bytes(b"\x00" * 100)
    # korrupt: whitespace flood
    (tmp_path / "BL-corrupt-ws.md").write_text("\n  \t  \n", encoding="utf-8")
    # gesund
    healthy_content = "---\nid: BL-ok\ntitle: OK\nstatus: DONE\n---\n\n# OK\n"
    (tmp_path / "BL-ok.md").write_text(healthy_content, encoding="utf-8")
    # Dir-Sibling (Verzeichnis mit gleichem Stamm) -- soll NICHT als Korruption gelistet werden
    dir_sibling = tmp_path / "BL-dir-sibling"
    dir_sibling.mkdir()
    (dir_sibling / "3_Spec").mkdir()
    (dir_sibling / "3_Spec" / "spec.md").write_text("---\nid: x\n---\n# spec\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests fuer scan_vault_node
# ---------------------------------------------------------------------------

class TestScanVaultNode:
    """Tests fuer die Einzeldatei-Prueffunktion scan_vault_node(path)."""

    def test_detects_null_byte_node(self, null_byte_file):
        """
        Datei mit ausschliesslich NULL-Bytes -> kind=NULL_BYTES, severity=CORRUPT.
        AK-1 Spec-Kriterium: raw.count(b'\\x00') > 0 -> NULL_BYTES/CORRUPT.
        """
        result = scan_vault_node(null_byte_file)

        assert result is not None, "NULL-Byte-Node muss als korrupt erkannt werden (nicht None)"
        assert result.kind == "NULL_BYTES", f"Erwartet kind=NULL_BYTES, got {result.kind!r}"
        assert result.severity == "CORRUPT", f"Erwartet severity=CORRUPT, got {result.severity!r}"
        assert result.path == null_byte_file, "result.path muss dem Eingabepfad entsprechen"

    def test_detects_empty_node(self, empty_file):
        """
        0-Byte-Datei -> kind=EMPTY, severity=CORRUPT.
        AK-1 Spec-Kriterium: len(raw) == 0 -> EMPTY/CORRUPT.
        """
        result = scan_vault_node(empty_file)

        assert result is not None, "Leere Datei muss als korrupt erkannt werden"
        assert result.kind == "EMPTY", f"Erwartet kind=EMPTY, got {result.kind!r}"
        assert result.severity == "CORRUPT", f"Erwartet severity=CORRUPT, got {result.severity!r}"

    def test_detects_whitespace_flood(self, whitespace_flood_file):
        """
        Datei nur aus Spaces/Newlines/Tabs -> kind=WHITESPACE_FLOOD, severity=CORRUPT.
        AK-1 Spec-Kriterium: raw.decode('utf-8', errors='replace').strip() == '' -> WHITESPACE_FLOOD/CORRUPT.
        """
        result = scan_vault_node(whitespace_flood_file)

        assert result is not None, "Whitespace-Flood-Node muss als korrupt erkannt werden"
        assert result.kind == "WHITESPACE_FLOOD", f"Erwartet kind=WHITESPACE_FLOOD, got {result.kind!r}"
        assert result.severity == "CORRUPT", f"Erwartet severity=CORRUPT, got {result.severity!r}"

    def test_healthy_node_not_flagged(self, healthy_file):
        """
        Normale .md mit YAML-Frontmatter + Inhalt -> scan_vault_node gibt None zurueck (gesund).
        """
        result = scan_vault_node(healthy_file)

        assert result is None, (
            f"Gesunder Node darf NICHT geflagt werden, aber bekam: {result}"
        )

    def test_warn_no_frontmatter(self, no_frontmatter_file):
        """
        Text-Datei ohne '---'-Frontmatter -> kind=NO_FRONTMATTER, severity=WARN.
        WARN ist kein CORRUPT -- nur Hinweis, kein Block.
        AK-1 Spec: not stripped.startswith('---') -> NO_FRONTMATTER/WARN.
        """
        result = scan_vault_node(no_frontmatter_file)

        assert result is not None, "Node ohne Frontmatter soll als WARN gelistet werden"
        assert result.kind == "NO_FRONTMATTER", f"Erwartet kind=NO_FRONTMATTER, got {result.kind!r}"
        assert result.severity == "WARN", f"Erwartet severity=WARN (kein CORRUPT), got {result.severity!r}"

    def test_severity_field_present_on_all_results(self, null_byte_file, empty_file, whitespace_flood_file, no_frontmatter_file):
        """
        Jedes NodeHealthResult hat ein severity-Feld (kein AttributeError, kein None).
        AK-1 Spec: NodeHealthResult.severity ist Pflichtfeld.
        """
        files = [null_byte_file, empty_file, whitespace_flood_file, no_frontmatter_file]
        for f in files:
            result = scan_vault_node(f)
            assert result is not None, f"Datei {f.name} soll ein Ergebnis liefern"
            assert hasattr(result, "severity"), f"NodeHealthResult muss severity-Feld haben"
            assert result.severity is not None, "severity darf nicht None sein"
            assert result.severity in ("CORRUPT", "WARN"), (
                f"severity muss 'CORRUPT' oder 'WARN' sein, got {result.severity!r}"
            )

    def test_detail_field_present_on_result(self, null_byte_file):
        """
        NodeHealthResult.detail enthaelt lesbare Zusatzinfo (nicht leer).
        Fuer NULL_BYTES soll detail 'count=' und 'pct=' enthalten (Spec-Format).
        """
        result = scan_vault_node(null_byte_file)

        assert result is not None
        assert hasattr(result, "detail"), "NodeHealthResult muss detail-Feld haben"
        assert isinstance(result.detail, str), "detail muss ein String sein"
        # Fuer NULL_BYTES: "count=5910,pct=100.0%" laut Spec
        assert "count=" in result.detail, (
            f"detail fuer NULL_BYTES soll 'count=' enthalten, got {result.detail!r}"
        )


# ---------------------------------------------------------------------------
# Tests fuer scan_vault_backlog
# ---------------------------------------------------------------------------

class TestScanVaultBacklog:
    """Tests fuer die Verzeichnis-Scan-Funktion scan_vault_backlog(backlog_dir)."""

    def test_scan_returns_all_corrupt(self, mixed_backlog_dir):
        """
        Mix-Verzeichnis mit 2 korrupten + 1 gesunder Datei ->
        len(results) == 2 (nur die korrupten), gesunde nicht enthalten.
        AK-1 Spec: scan_vault_backlog gibt Liste aller kranken Nodes zurueck.
        """
        results = scan_vault_backlog(mixed_backlog_dir)

        assert isinstance(results, list), "scan_vault_backlog muss eine Liste zurueckgeben"
        corrupt_results = [r for r in results if r.severity == "CORRUPT"]
        assert len(corrupt_results) == 2, (
            f"Erwartet 2 CORRUPT-Ergebnisse, got {len(corrupt_results)}: "
            f"{[r.path.name for r in corrupt_results]}"
        )

    def test_healthy_not_in_scan_results(self, mixed_backlog_dir):
        """
        Gesunde .md-Datei (valider Frontmatter + Inhalt) darf NICHT in scan_vault_backlog-Ergebnis erscheinen.
        """
        results = scan_vault_backlog(mixed_backlog_dir)

        healthy_paths = [r for r in results if r.path.name == "BL-ok.md"]
        assert len(healthy_paths) == 0, (
            "BL-ok.md (gesunder Node) darf nicht in Ergebnissen erscheinen"
        )

    def test_dir_sibling_not_flagged_as_corrupt(self, mixed_backlog_dir):
        """
        Verzeichnisse (Dir-Siblings wie BL-142/307 in der Realitaet) werden NICHT als korrupt gelistet.
        scan_vault_backlog prueft nur is_file() + suffix=='.md'.
        OQ-3 Edge Case: Dir-Sibling-Struktur ist kein Fehler.
        """
        results = scan_vault_backlog(mixed_backlog_dir)

        # kein Result darf ein Verzeichnis sein
        for r in results:
            assert r.path.is_file(), (
                f"scan_vault_backlog darf keine Verzeichnisse listen: {r.path}"
            )

    def test_empty_dir_returns_empty_list(self, tmp_path):
        """
        Leeres Verzeichnis -> leere Liste (kein Fehler, kein None).
        """
        results = scan_vault_backlog(tmp_path)

        assert results == [], f"Leeres Verzeichnis soll [] liefern, got {results}"

    def test_scan_result_paths_are_file_objects(self, mixed_backlog_dir):
        """
        Jedes NodeHealthResult.path ist ein pathlib.Path-Objekt.
        """
        results = scan_vault_backlog(mixed_backlog_dir)

        for r in results:
            assert isinstance(r.path, Path), (
                f"NodeHealthResult.path muss pathlib.Path sein, got {type(r.path)}"
            )
