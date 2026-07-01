"""
test_vault_node_repair.py -- BL-443 batch_2 AK-2: RED-Tests fuer vault_node_repair.py

Modul-API (vault_node_repair.py muss implementieren):

    from pathlib import Path

    def reconstruct_from_git(
        node_path: Path,
        git_show: callable = None,
    ) -> str | None:
        '''
        Sucht letzten nicht-korrupten Git-Blob fuer den Node.

        Parameter:
            node_path (Path): Pfad zur (potenziell korrupten) Vault-Node-Datei.
            git_show (callable, optional): Injizierbare Funktion mit Signatur
                git_show(rev_path: str) -> bytes | str
                wobei rev_path die Form "HEAD:<relative_path>" oder "<hash>:<relative_path>" hat.
                Default (None): echtes subprocess-Aufruf `git show HEAD:<path>`.
                Fuer Tests IMMER injizieren -- kein echtes git-Repo benoetigt.

        Strategie:
            1. git log --all --oneline -- <node_path> auflisten (Commits)
            2. Fuer jeden Commit (neuester zuerst): git_show(<hash>:<pfad>) aufrufen
            3. Inhalt mit is_content_corrupt() pruefen
            4. Ersten sauberen Inhalt als str zurueckgeben
            5. None wenn kein sauberer Blob in History

        Returns:
            str: rekonstruierter Inhalt des ersten nicht-korrupten Blobs
            None: kein sauberer Blob gefunden (alle korrupt oder keine History)

        Raises:
            FileNotFoundError: wenn node_path nicht existiert
        '''

    def is_content_corrupt(content: bytes | str) -> bool:
        '''
        Prueft ob ein Blob-Inhalt als korrupt gilt.

        Regeln (entsprechend vault_node_health.py Scan-Kriterien):
            - NULL-Bytes: isinstance(content, bytes) and b'\\x00' in content -> True
            - Leer: len(content) == 0 -> True
            - Nur Whitespace: content.decode('utf-8', errors='replace').strip() == '' -> True
            - Sonst: False (gesund)

        Parameter:
            content (bytes | str): Rohe Blob-Daten aus git show oder string-Inhalt.

        Returns:
            bool: True wenn korrupt, False wenn gesund.
        '''

RED-Beweis: vault_node_repair.py existiert noch nicht -> ImportError -> alle Tests FAIL.

API-Design-Entscheidungen:
    - git_show als Callable injizierbar (kein echtes git-Repo fuer Tests noetig)
    - git_show(rev_path: str) -> bytes | str
    - reconstruct_from_git gibt str zurueck (dekodierter Inhalt), None wenn nichts gefunden
    - is_content_corrupt operiert auf bytes oder str (beide Varianten unterstuetzt)

Run: py -3 -m pytest .claude/scripts/test_vault_node_repair.py -q
"""

import sys
from pathlib import Path
from typing import Callable

import pytest

sys.path.insert(0, str(Path(__file__).parent))

# Dieser Import MUSS fehlschlagen bis GREEN-Worker vault_node_repair.py implementiert.
# RED-Phase: ImportError erwartet.
from vault_node_repair import reconstruct_from_git, is_content_corrupt  # noqa: E402


# ---------------------------------------------------------------------------
# Hilfsfunktionen fuer Fake-git_show-Callables
# ---------------------------------------------------------------------------

def _make_git_show_sequence(*blobs) -> Callable[[str], bytes]:
    """
    Erstellt einen git_show-Stub der die uebergebenen Blobs der Reihe nach zurueckgibt.

    Erster Aufruf -> blobs[0], zweiter -> blobs[1], etc.
    Nach dem letzten blob -> letzter Wert wiederholt (safe fuer zu viele Aufrufe).

    blobs: bytes oder str (str wird zu bytes kodiert fuer Einheitlichkeit)
    """
    blob_list = list(blobs)
    call_count = [0]

    def git_show_stub(rev_path: str) -> bytes:
        idx = min(call_count[0], len(blob_list) - 1)
        call_count[0] += 1
        blob = blob_list[idx]
        if isinstance(blob, str):
            return blob.encode("utf-8")
        return blob

    return git_show_stub


def _make_git_show_fixed(blob) -> Callable[[str], bytes]:
    """git_show-Stub der immer denselben Blob zurueckgibt."""
    def git_show_stub(rev_path: str) -> bytes:
        if isinstance(blob, str):
            return blob.encode("utf-8")
        return blob
    return git_show_stub


def _make_git_show_tracking() -> tuple[Callable[[str], bytes], list]:
    """
    git_show-Stub der alle aufgerufenen rev_paths trackt.
    Returns (stub, calls_list) wobei calls_list mit jedem Aufruf befuellt wird.
    """
    calls = []
    content = b"---\nid: BL-test\ntitle: Test\nstatus: DONE\n---\n\n# Test\n"

    def git_show_stub(rev_path: str) -> bytes:
        calls.append(rev_path)
        return content

    return git_show_stub, calls


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HEALTHY_CONTENT = "---\nid: BL-test\ntitle: Test Node\nstatus: DRAFT\n---\n\n# Test\n\nGesunder Inhalt.\n"
CORRUPT_NULL = b"\x00" * 5910
CORRUPT_EMPTY = b""
CORRUPT_WHITESPACE = b"\n   \t  \n   \n"


@pytest.fixture
def existing_node(tmp_path) -> Path:
    """Existierende (aber korrupte) Node-Datei -- repraesentiert einen echten korrupten Node."""
    p = tmp_path / "BL-285.md"
    p.write_bytes(CORRUPT_NULL)
    return p


@pytest.fixture
def healthy_node(tmp_path) -> Path:
    """Existierende gesunde Node-Datei fuer Baseline-Tests."""
    p = tmp_path / "BL-healthy.md"
    p.write_text(HEALTHY_CONTENT, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests fuer reconstruct_from_git
# ---------------------------------------------------------------------------

class TestReconstructFromGit:
    """Tests fuer reconstruct_from_git(node_path, git_show=...) mit injizierten Stubs."""

    def test_reconstructs_healthy_head_content(self, existing_node):
        """
        git_show liefert gesunden HEAD-Inhalt -> reconstruct gibt ihn als str zurueck.

        Szenario: Der HEAD-Blob ist sauber (kein NULL, kein leer, kein ws-only).
        reconstruct_from_git soll diesen Inhalt direkt zurueckgeben ohne Umweg.

        AK-2 Spec: "Ersten sauberen Blob zurueckgeben".
        """
        git_show = _make_git_show_fixed(HEALTHY_CONTENT)

        result = reconstruct_from_git(existing_node, git_show=git_show)

        assert result is not None, (
            "reconstruct_from_git muss gesunden HEAD-Inhalt zurueckgeben (nicht None)"
        )
        assert isinstance(result, str), (
            f"reconstruct_from_git muss str zurueckgeben, got {type(result)}"
        )
        assert "id: BL-test" in result, (
            f"Rekonstruierter Inhalt soll den gesunden Blob-Text enthalten, got: {result[:100]!r}"
        )

    def test_skips_corrupt_head_uses_older(self, existing_node):
        """
        HEAD-Blob ist korrupt (NULL-Bytes), zweiter Blob ist gesund -> gibt den gesunden zurueck.

        Szenario: git_show liefert bei 1. Aufruf NULL-Bytes (HEAD korrupt),
        bei 2. Aufruf sauberen Content (aeltere Revision).
        reconstruct_from_git muss HEAD ueberspringen und den aelteren gesunden Blob nehmen.

        AK-2 Spec: "NULL-Bytes pruefen; aeltere Revision versuchen".
        """
        git_show = _make_git_show_sequence(CORRUPT_NULL, HEALTHY_CONTENT)

        result = reconstruct_from_git(existing_node, git_show=git_show)

        assert result is not None, (
            "reconstruct_from_git muss auf aeltere Revision fallback wenn HEAD korrupt"
        )
        assert isinstance(result, str), f"Erwartet str, got {type(result)}"
        assert result.strip() != "", "Rekonstruierter Inhalt darf nicht leer/ws-only sein"
        assert "id: BL-test" in result, (
            f"Soll gesunden aelteren Blob zurueckgeben, got: {result[:100]!r}"
        )

    def test_returns_none_when_all_corrupt(self, existing_node):
        """
        Alle verfuegbaren Blobs sind korrupt -> None.

        Szenario: git_show liefert immer NULL-Bytes (alle Revisionen korrupt).
        reconstruct_from_git soll None zurueckgeben (kein sauberer Blob gefunden).

        AK-2 Spec: "None wenn kein sauberer Blob in Git-History".
        """
        git_show = _make_git_show_fixed(CORRUPT_NULL)

        result = reconstruct_from_git(existing_node, git_show=git_show)

        assert result is None, (
            f"Wenn alle Blobs korrupt sind muss None zurueckgegeben werden, got: {result!r}"
        )

    def test_uses_injected_git_show_callable(self, existing_node):
        """
        reconstruct_from_git ruft den injizierten git_show-Callable auf -- kein echtes git.

        Verifiziert: der injizierte Callable wird tatsaechlich benutzt (kein subprocess.run
        auf git im Hintergrund wenn git_show injiziert ist).

        Dieses Testdesign stellt sicher dass die DI (Dependency Injection) funktioniert
        und die Funktion NICHT am Callable vorbei echtes git aufruft.
        """
        git_show, tracked_calls = _make_git_show_tracking()

        result = reconstruct_from_git(existing_node, git_show=git_show)

        assert len(tracked_calls) >= 1, (
            "reconstruct_from_git muss den injizierten git_show-Callable mindestens einmal aufrufen. "
            f"Tatsaechliche Aufrufe: {len(tracked_calls)}"
        )
        assert result is not None, "Tracking-Stub liefert gesunden Inhalt -> muss str zurueckgeben"

    def test_empty_blob_treated_as_corrupt(self, existing_node):
        """
        git_show liefert leeren Blob (0 Bytes) -> als korrupt behandeln, naechste Revision versuchen.

        EMPTY ist laut AK-1 / vault_node_health ein CORRUPT-Signal.
        reconstruct_from_git muss leere Blobs ueberspringen wie NULL-Byte-Blobs.
        """
        git_show = _make_git_show_sequence(CORRUPT_EMPTY, HEALTHY_CONTENT)

        result = reconstruct_from_git(existing_node, git_show=git_show)

        assert result is not None, (
            "Leerer HEAD-Blob soll uebersprungen werden; gesunder aelterer Blob soll zurueckgegeben werden"
        )
        assert result.strip() != "", "Ergebnis darf nicht leer/ws-only sein"


# ---------------------------------------------------------------------------
# Tests fuer is_content_corrupt
# ---------------------------------------------------------------------------

class TestIsContentCorrupt:
    """Tests fuer den is_content_corrupt(content) Helper."""

    def test_corrupt_detection_null_byte(self):
        """
        Bytes mit \\x00 -> is_content_corrupt gibt True zurueck.

        AK-1-Aequivalenz: NULL_BYTES ist CORRUPT.
        Repraesentiert den realen Korruptions-Typ der 12 noch-defekten Nodes.
        """
        assert is_content_corrupt(b"\x00" * 5910) is True, (
            "NULL-Byte-Inhalt muss als korrupt erkannt werden"
        )
        assert is_content_corrupt(b"ok header\x00rest") is True, (
            "Einzelnes NULL-Byte im Inhalt muss als korrupt erkannt werden"
        )

    def test_corrupt_detection_empty(self):
        """
        Leerer bytes-Blob -> is_content_corrupt gibt True zurueck.

        AK-1-Aequivalenz: EMPTY ist CORRUPT.
        """
        assert is_content_corrupt(b"") is True, (
            "Leerer Blob muss als korrupt erkannt werden"
        )
        assert is_content_corrupt("") is True, (
            "Leerer String muss als korrupt erkannt werden"
        )

    def test_corrupt_detection_whitespace_only(self):
        """
        Nur-Whitespace-Inhalt (Spaces, Newlines, Tabs) -> is_content_corrupt gibt True zurueck.

        AK-1-Aequivalenz: WHITESPACE_FLOOD ist CORRUPT.
        """
        assert is_content_corrupt(b"\n   \t  \n   \n") is True, (
            "Whitespace-only Bytes muss als korrupt erkannt werden"
        )
        assert is_content_corrupt("  \n\t  \n") is True, (
            "Whitespace-only String muss als korrupt erkannt werden"
        )

    def test_healthy_content_not_corrupt(self):
        """
        Gesunder YAML-Frontmatter-Inhalt -> is_content_corrupt gibt False zurueck.

        Positivtest: echter Vault-Node-Inhalt darf NICHT als korrupt gelten.
        """
        assert is_content_corrupt(HEALTHY_CONTENT) is False, (
            f"Gesunder Inhalt darf nicht als korrupt erkannt werden: {HEALTHY_CONTENT[:50]!r}"
        )
        assert is_content_corrupt(HEALTHY_CONTENT.encode("utf-8")) is False, (
            "Gesunder Inhalt als bytes darf nicht als korrupt erkannt werden"
        )
