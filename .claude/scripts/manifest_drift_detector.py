# -*- coding: utf-8 -*-
"""
manifest_drift_detector.py — BL-454 Manifest-Drift-Detektor.

READ-ONLY Detektor: erkennt doppelte Bloecke und Split-Brain-Zustand
zwischen vault-root/_manifest.md und .claude/analysis/_manifest.md.

Funktionen:
  detect_duplicate_blocks(manifest_text) -> list[str]
  detect_split_brain(vault_root_manifest_text, stub_manifest_text) -> list[str]
  scan_manifest_drift(vault_root, read_vault_fn=None, read_stub_fn=None) -> dict
"""

import re
from pathlib import Path

# Regex: nur genau zwei '#' (nicht ###, ####, etc.), erstes Nicht-Leerzeichen-Token = Block-Name
_BLOCK_HEADER_RE = re.compile(r'^##\s+(\S+)', re.MULTILINE)


def _extract_block_names(manifest_text: str) -> list:
    """Extrahiert alle top-level ##-Block-Namen aus manifest_text."""
    if not manifest_text:
        return []
    return _BLOCK_HEADER_RE.findall(manifest_text)


def detect_duplicate_blocks(manifest_text: str) -> list:
    """
    Findet top-level ##-Block-Header die mehr als einmal vorkommen.

    Args:
        manifest_text: Vollstaendiger Manifest-Inhalt als String.

    Returns:
        Liste der duplizierten Block-Namen (dedupliziert).
        Sauberer Text -> [].
    """
    names = _extract_block_names(manifest_text)
    seen = set()
    duplicates = []
    for name in names:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    return duplicates


def detect_split_brain(vault_root_manifest_text: str, stub_manifest_text: str) -> list:
    """
    Findet Block-Namen die in BEIDEN Texten als top-level ##-Header existieren.

    Args:
        vault_root_manifest_text: Inhalt von {vault_root}/_manifest.md.
        stub_manifest_text: Inhalt von .claude/analysis/_manifest.md.

    Returns:
        Liste der Block-Namen die in beiden Texten vorhanden sind (Schnittmenge).
        Leerer/None-Stub -> [].
    """
    if not stub_manifest_text:
        return []
    vault_names = set(_extract_block_names(vault_root_manifest_text))
    stub_names = set(_extract_block_names(stub_manifest_text))
    intersection = vault_names & stub_names
    # Stabile Reihenfolge: vault-Reihenfolge beibehalten
    vault_ordered = _extract_block_names(vault_root_manifest_text)
    seen = set()
    result = []
    for name in vault_ordered:
        if name in intersection and name not in seen:
            result.append(name)
            seen.add(name)
    return result


def scan_manifest_drift(vault_root, read_vault_fn=None, read_stub_fn=None) -> dict:
    """
    Orchestriert Drift-Scan: liest vault-root/_manifest.md und
    .claude/analysis/_manifest.md, erkennt Dups + Split-Brain.

    Args:
        vault_root: Pfad zum Vault-Root (str oder Path).
        read_vault_fn: Optionale DI-Reader (path -> str). Default: realer Filesystem-Read.
        read_stub_fn:  Optionale DI-Reader (path -> str). Default: realer Filesystem-Read.

    Returns:
        dict mit:
          duplicate_blocks: list[str]
          split_brain_blocks: list[str]
    """
    vault_root = Path(vault_root)

    # Vault-Manifest-Pfad: {vault_root}/_manifest.md
    vault_manifest_path = vault_root / "_manifest.md"

    # Stub-Manifest-Pfad: .claude/analysis/_manifest.md
    # Ermittelt relativ zum Repo-Root (Nachbar von vault_root)
    repo_root = vault_root.parent
    stub_manifest_path = repo_root / ".claude" / "analysis" / "_manifest.md"

    def _default_read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return ""

    vault_text = read_vault_fn(vault_manifest_path) if read_vault_fn else _default_read(vault_manifest_path)
    stub_text = read_stub_fn(stub_manifest_path) if read_stub_fn else _default_read(stub_manifest_path)

    return {
        "duplicate_blocks": detect_duplicate_blocks(vault_text),
        "split_brain_blocks": detect_split_brain(vault_text, stub_text),
    }
