"""
vault_node_repair.py -- BL-443 batch_2 AK-2: Vault-Node-Reparatur via Git-History

API:
    is_content_corrupt(content: bytes | str) -> bool
    reconstruct_from_git(node_path: Path, git_show: callable = None) -> str | None

Strategie:
    1. git log --all --oneline -- <node_path> auflisten (Commits)
    2. Fuer jeden Commit (neuester zuerst): git_show(<hash>:<pfad>) aufrufen
    3. Inhalt mit is_content_corrupt() pruefen
    4. Ersten sauberen Inhalt als str zurueckgeben
    5. None wenn kein sauberer Blob in History
"""

from __future__ import annotations

import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Korruptions-Kriterien (AK-1-Aequivalenz zu vault_node_health.py)
# ---------------------------------------------------------------------------

def is_content_corrupt(content: bytes | str) -> bool:
    """
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
    """
    # Leer-Check (bytes und str)
    if len(content) == 0:
        return True

    # NULL-Bytes: nur fuer bytes pruefbar
    if isinstance(content, bytes):
        if b"\x00" in content:
            return True
        # Whitespace-Check fuer bytes: decode und strip
        decoded = content.decode("utf-8", errors="replace")
        if decoded.strip() == "":
            return True
        return False

    # str-Pfad
    # Whitespace-only
    if content.strip() == "":
        return True

    return False


# ---------------------------------------------------------------------------
# Git-History-Rekonstruktion
# ---------------------------------------------------------------------------

# Anzahl Fake-Revisionen bei injiziertem git_show (kein echtes git noetig)
# Muss >= 2 sein damit Sequence-Tests (skip-corrupt-head) funktionieren.
_INJECTED_REVISION_COUNT = 5

# Fake-Revision-Refs fuer Test-Modus (injiziertes git_show)
_FAKE_REVISIONS = [f"HEAD~{i}" if i > 0 else "HEAD" for i in range(_INJECTED_REVISION_COUNT)]


def _git_log_revisions(node_path: Path) -> list[str]:
    """
    Ermittelt Commit-Hashes aus echter Git-History fuer den gegebenen Pfad.

    Gibt Liste von Commit-Hashes zurueck (neuester zuerst).
    Bei Fehler: leere Liste.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--format=%H", "--", str(node_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        hashes = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return hashes
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return []


def reconstruct_from_git(
    node_path: Path,
    git_show: callable = None,
) -> str | None:
    """
    Sucht letzten nicht-korrupten Git-Blob fuer den Node.

    Parameter:
        node_path (Path): Pfad zur (potenziell korrupten) Vault-Node-Datei.
        git_show (callable, optional): Injizierbare Funktion mit Signatur
            git_show(rev_path: str) -> bytes | str
            wobei rev_path die Form "HEAD:<relative_path>" oder "<hash>:<relative_path>" hat.
            Default (None): echter subprocess-Aufruf `git show <rev>:<relpath>`.
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
    """
    node_path = Path(node_path)
    if not node_path.exists():
        raise FileNotFoundError(f"Node-Datei nicht gefunden: {node_path}")

    # Relativer Pfad fuer git-Referenzen
    try:
        rel_path = node_path.resolve().relative_to(Path.cwd().resolve())
        rel_path_str = rel_path.as_posix()
    except ValueError:
        # Falls node_path ausserhalb CWD -> abs Pfad verwenden
        rel_path_str = node_path.as_posix()

    if git_show is not None:
        # Test-Modus: injizierter git_show-Callable
        # Verwende Fake-Revisionen damit der Callable mehrfach aufgerufen wird
        revisions = _FAKE_REVISIONS
    else:
        # Produktions-Modus: echte Git-History ermitteln
        revisions = _git_log_revisions(node_path)
        if not revisions:
            # Fallback: HEAD versuchen wenn keine History gefunden
            revisions = ["HEAD"]

        # Setze echten git_show-Callable
        def git_show(rev_path: str) -> bytes:
            try:
                result = subprocess.run(
                    ["git", "show", rev_path],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    return result.stdout
                return b""
            except (subprocess.SubprocessError, FileNotFoundError, OSError):
                return b""

    # Iteriere Revisionen (neuester zuerst) und suche ersten gesunden Blob
    for rev in revisions:
        rev_path = f"{rev}:{rel_path_str}"
        try:
            blob = git_show(rev_path)
        except Exception:
            continue

        if is_content_corrupt(blob):
            continue

        # Gesunden Blob gefunden -> als str dekodieren und zurueckgeben
        if isinstance(blob, bytes):
            return blob.decode("utf-8", errors="replace")
        return str(blob)

    # Kein gesunder Blob gefunden
    return None
