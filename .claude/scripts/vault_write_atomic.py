"""
vault_write_atomic.py -- BL-443 batch_1 AK-3: Atomarer Vault-Node-Writer

API:
    write_vault_node_atomic(path: Path, content: str, encoding: str = "utf-8") -> None

Ablauf:
    1. tempfile.mkstemp(dir=path.parent, prefix=".tmp_vault_", suffix=".md")
    2. write content via os.fdopen
    3. os.replace(tmp, path) -- atomic auf POSIX + Windows-NTFS
    4. Post-Write-Read-Back: pruefen auf NULL-Bytes / leer
    Bei Fehler: temp-File cleanup, dann re-raise

Raises:
    RuntimeError: Post-Write-Read-Back entdeckt Korruption
    OSError: Dateisystem-Fehler (nach temp-File-Cleanup propagiert)

Referenz: propagate_provenance.py:L113-125 + Post-Write-Read-Back als Erweiterung (AK-3)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_vault_node_atomic(
    path: Path,
    content: str,
    encoding: str = "utf-8",
) -> None:
    """
    Schreibt einen Vault-Node atomar.

    1. tempfile.mkstemp im GLEICHEN Verzeichnis wie 'path'
    2. write content via os.fdopen
    3. flush + fsync
    4. os.replace(tmp_path, path)  -- atomic rename
    5. Post-Write-Read-Back: path.read_bytes() pruefen
       - leer (len==0)       -> raise RuntimeError("POST-WRITE-CORRUPT:EMPTY: ...")
       - NULL-Bytes vorhanden -> raise RuntimeError("POST-WRITE-CORRUPT:NULL_BYTES:count=N: ...")
    Bei Exception: temp-File loeschen (cleanup), dann re-raise
    """
    fd, tmp_path_str = tempfile.mkstemp(
        dir=path.parent,
        prefix=".tmp_vault_",
        suffix=".md",
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno() if hasattr(f, "fileno") else fd)
        os.replace(tmp_path_str, str(path))
    except Exception:
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        raise

    # Post-Write-Read-Back
    written_bytes = path.read_bytes()

    if len(written_bytes) == 0:
        raise RuntimeError(
            f"POST-WRITE-CORRUPT:EMPTY: {path} -- geschriebenes File ist leer nach os.replace"
        )

    null_count = written_bytes.count(b"\x00")
    if null_count > 0:
        raise RuntimeError(
            f"POST-WRITE-CORRUPT:NULL_BYTES:count={null_count}: {path} -- NULL-Bytes im geschriebenen File"
        )
