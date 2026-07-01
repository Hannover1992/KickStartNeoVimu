"""
test_vault_write_atomic.py -- BL-443 batch_1 AK-3: RED-Tests fuer vault_write_atomic.py

Modul-API (vault_write_atomic.py muss implementieren):

    from pathlib import Path

    def write_vault_node_atomic(path: Path, content: str, encoding: str = "utf-8") -> None:
        '''
        Schreibt einen Vault-Node atomar: tempfile.mkstemp im GLEICHEN Verzeichnis
        wie 'path', dann os.replace (POSIX + Windows-NTFS atomic rename).

        Ablauf:
        1. fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp_vault_", suffix=".md")
        2. with os.fdopen(fd, "w", encoding=encoding) as f: f.write(content)
        3. os.replace(tmp_path, path)
        4. POST-WRITE-READ-BACK: path.read_bytes() pruefen
           - len(written) == 0  -> raise RuntimeError("POST-WRITE-CORRUPT:EMPTY: ...")
           - b'\\x00' in written -> raise RuntimeError("POST-WRITE-CORRUPT:NULL_BYTES:count=N: ...")

        Bei Exception zwischen mkstemp und replace: tmp_path wird geloescht (cleanup).
        OSError (Dateisystem-Fehler) wird nach cleanup re-raised.

        Raises:
            RuntimeError: Post-Write-Read-Back entdeckt Korruption (NULL-Bytes oder leer)
            OSError: Dateisystem-Fehler (nach temp-File-Cleanup propagiert)
        '''

Referenz-Pattern: propagate_provenance.py:L.113-125 (write_frontmatter) +
                  Post-Write-Read-Back als Erweiterung (AK-3).

RED-Beweis: vault_write_atomic.py existiert noch nicht -> ImportError -> alle Tests FAIL.

Run: py -3 -m pytest .claude/scripts/test_vault_write_atomic.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))

# Dieser Import MUSS fehlschlagen bis GREEN-Worker vault_write_atomic.py implementiert.
# RED-Phase: ImportError erwartet.
from vault_write_atomic import write_vault_node_atomic  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def target_path(tmp_path) -> Path:
    """Frischer Ziel-Pfad -- Datei existiert noch nicht."""
    return tmp_path / "node.md"


@pytest.fixture
def existing_file(tmp_path) -> Path:
    """Vorhandene Datei mit anderem Inhalt -- soll atomar ersetzt werden."""
    p = tmp_path / "existing.md"
    p.write_text("---\nid: old\ntitle: Old Content\n---\n\n# Old\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests fuer write_vault_node_atomic
# ---------------------------------------------------------------------------

class TestWriteVaultNodeAtomic:
    """Tests fuer die atomare Schreibfunktion write_vault_node_atomic(path, content)."""

    def test_writes_content_correctly(self, target_path):
        """
        Normaler Write: content landet exakt in der Zieldatei.
        Signatur: write_vault_node_atomic(path: Path, content: str, encoding: str='utf-8') -> None
        """
        content = "---\nid: test-node\ntitle: Test\nstatus: DRAFT\n---\n\n# Test\n\nHello atomic write.\n"

        write_vault_node_atomic(target_path, content)

        assert target_path.exists(), "Zieldatei muss nach dem Write existieren"
        written = target_path.read_text(encoding="utf-8")
        assert written == content, (
            f"Geschriebener Inhalt stimmt nicht ueberein.\n"
            f"Erwartet: {content!r}\n"
            f"Got:      {written!r}"
        )

    def test_atomic_no_partial_on_success(self, target_path):
        """
        Nach erfolgreichem Write existiert genau die Zieldatei -- kein temp-File-Rest
        (.tmp_vault_*.md) im selben Verzeichnis.
        """
        content = "---\nid: clean\ntitle: Clean\nstatus: DONE\n---\n\n# Clean\n"

        write_vault_node_atomic(target_path, content)

        dir_files = list(target_path.parent.iterdir())
        temp_files = [f for f in dir_files if f.name.startswith(".tmp_vault_")]
        assert len(temp_files) == 0, (
            f"Nach erfolgreichem Write darf kein temp-File zurueckbleiben: {[f.name for f in temp_files]}"
        )
        # genau die Zieldatei soll existieren
        assert target_path in dir_files, "Zieldatei muss im Verzeichnis existieren"

    def test_read_back_verification_passes_on_good_write(self, target_path):
        """
        Normaler Write (kein NULL-Byte im Content) loest KEIN RuntimeError aus.
        Post-Write-Read-Back soll bei gutem Inhalt transparent durchlaufen.
        """
        content = "---\nid: good\ntitle: Good Write\nstatus: DRAFT\n---\n\n# Good\n\nNo null bytes here.\n"

        # Kein raise erwartet
        try:
            write_vault_node_atomic(target_path, content)
        except RuntimeError as e:
            pytest.fail(f"Normaler Write soll kein RuntimeError werfen, got: {e}")

    def test_raises_on_null_byte_in_read_back(self, target_path):
        """
        Wenn das geschriebene File nach dem Write NULL-Bytes enthaelt (simuliert via
        monkeypatch auf path.read_bytes), muss write_vault_node_atomic RuntimeError werfen.

        Hintergrund: In der Realitaet enthaelt ein guter Write KEINE NULL-Bytes.
        Der Read-Back-Check ist ein Sicherheitsnetz gegen NTFS-Sparse-File-Artefakte
        oder OS-Fehler nach dem os.replace.

        AK-3 Spec: 'NULL-Bytes im Read-Back -> raise RuntimeError("POST-WRITE-CORRUPT:NULL_BYTES:...")'
        """
        content = "---\nid: check-readback\nstatus: DRAFT\n---\n\n# Test\n"

        # Simuliere: os.replace erfolgreich, aber read_bytes liefert NULL-Bytes
        original_read_bytes = Path.read_bytes

        def fake_read_bytes(self):
            if self == target_path:
                return b"\x00" * 50  # simuliertes NULL-Byte-Ergebnis im Read-Back
            return original_read_bytes(self)

        with patch.object(Path, "read_bytes", fake_read_bytes):
            with pytest.raises(RuntimeError) as exc_info:
                write_vault_node_atomic(target_path, content)

        err_msg = str(exc_info.value)
        assert "NULL_BYTES" in err_msg or "CORRUPT" in err_msg, (
            f"RuntimeError-Message soll 'NULL_BYTES' oder 'CORRUPT' enthalten, got: {err_msg!r}"
        )

    def test_temp_cleanup_on_failure(self, target_path):
        """
        Bei simuliertem Fehler (OSError auf os.replace) wird kein temp-File zurueckgelassen.
        AK-3 Spec: 'except Exception: try: os.unlink(tmp_path) except OSError: pass; raise'
        """

        # Patch os.replace so dass es OSError wirft
        original_replace = os.replace

        call_count = {"n": 0}

        def failing_replace(src, dst):
            call_count["n"] += 1
            # Erster Aufruf faellt aus (simulated failure)
            raise OSError("Simulated replace failure for test")

        with patch("os.replace", side_effect=failing_replace):
            with pytest.raises(OSError):
                write_vault_node_atomic(target_path, "some content")

        # Nach dem Fehler: kein temp-File im tmp_path-Verzeichnis
        dir_files = list(target_path.parent.iterdir())
        temp_files = [f for f in dir_files if f.name.startswith(".tmp_vault_")]
        assert len(temp_files) == 0, (
            f"Bei Fehler muss temp-File bereinigt werden, gefunden: {[f.name for f in temp_files]}"
        )
        # Zieldatei darf NICHT entstanden sein (Replace ist nicht passiert)
        assert not target_path.exists(), "Bei fehlgeschlagenem Write darf Zieldatei nicht erscheinen"

    def test_overwrites_existing_atomically(self, existing_file):
        """
        Bestehende Datei wird atomar durch neuen Inhalt ersetzt.
        Alter Inhalt ist danach vollstaendig weg.
        AK-3: os.replace ersetzt die bestehende Datei atomar (NTFS + POSIX).
        """
        new_content = "---\nid: new-version\ntitle: New Version\nstatus: DONE\n---\n\n# New\n\nReplaced.\n"

        write_vault_node_atomic(existing_file, new_content)

        assert existing_file.exists(), "Datei muss nach dem Replace existieren"
        written = existing_file.read_text(encoding="utf-8")
        assert written == new_content, (
            f"Alter Inhalt wurde nicht korrekt ersetzt.\nErwartet: {new_content!r}\nGot: {written!r}"
        )
        assert "Old Content" not in written, "Alter Inhalt darf nach atomarem Replace nicht mehr vorhanden sein"

    def test_null_byte_in_content_triggers_readback_error(self, target_path):
        """
        Wenn content selbst ein NULL-Byte enthaelt ('\x00'), landet es als NULL-Byte
        im File -- Post-Write-Read-Back soll das erkennen und RuntimeError werfen.

        AK-3 Spec Hinweis: 'wenn read-back NULL-Bytes findet -> raise (Korruptions-Schutz)'
        Das ist korrektes Verhalten -- Fehler frueh werfen, kein silent-korrupter Node.

        Hinweis fuer GREEN-Worker: UTF-8 kodiert '\x00' als 0x00-Byte. Der Read-Back-Check
        soll written_bytes.count(b'\x00') > 0 pruefen. Wenn Impl das File tatsaechlich
        schreibt und zurueckliest, wird der Check den RuntimeError ausloesen.
        """
        content_with_null = "Header\x00Body"  # NULL-Byte im Content

        with pytest.raises(RuntimeError) as exc_info:
            write_vault_node_atomic(target_path, content_with_null)

        err_msg = str(exc_info.value)
        assert "NULL_BYTES" in err_msg or "CORRUPT" in err_msg, (
            f"RuntimeError fuer NULL-Byte-Content soll 'NULL_BYTES' oder 'CORRUPT' enthalten, got: {err_msg!r}"
        )
