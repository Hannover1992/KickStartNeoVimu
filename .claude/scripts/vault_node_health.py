"""
vault_node_health.py -- BL-443 batch_1 AK-1: Vault-Node-Health-Scanner

API:
    scan_vault_node(path: Path) -> NodeHealthResult | None
    scan_vault_backlog(backlog_dir: Path) -> list[NodeHealthResult]

Scan-Reihenfolge (Prioritaet): NULL_BYTES > EMPTY > WHITESPACE_FLOOD > NO_FRONTMATTER
"""

from __future__ import annotations

import sys
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
    detail: str


def scan_vault_node(path: Path) -> NodeHealthResult | None:
    """
    Prueft einen einzelnen Node. Gibt None zurueck wenn gesund.

    Scan-Reihenfolge (Prioritaet): NULL_BYTES > EMPTY > WHITESPACE_FLOOD > NO_FRONTMATTER
    - NULL_BYTES: raw bytes enthalten \\x00 -> CORRUPT
    - EMPTY: 0 Bytes -> CORRUPT
    - WHITESPACE_FLOOD: nur Whitespace nach decode -> CORRUPT
    - NO_FRONTMATTER: .md ohne ---frontmatter -> WARN
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    # Prioritaet 1: NULL_BYTES (auch wenn leer und NULL, NULL hat Vorrang)
    null_count = raw.count(b"\x00")
    if null_count > 0:
        total = len(raw)
        pct = (null_count / total * 100) if total > 0 else 100.0
        return NodeHealthResult(
            path=path,
            kind="NULL_BYTES",
            severity="CORRUPT",
            detail=f"count={null_count},pct={pct:.1f}%",
        )

    # Prioritaet 2: EMPTY (0 Bytes)
    if len(raw) == 0:
        return NodeHealthResult(
            path=path,
            kind="EMPTY",
            severity="CORRUPT",
            detail="size=0",
        )

    # Prioritaet 3: WHITESPACE_FLOOD (nur Whitespace)
    decoded = raw.decode("utf-8", errors="replace")
    if decoded.strip() == "":
        return NodeHealthResult(
            path=path,
            kind="WHITESPACE_FLOOD",
            severity="CORRUPT",
            detail=f"size={len(raw)},all_whitespace=true",
        )

    # Prioritaet 4: NO_FRONTMATTER (nur fuer .md Dateien)
    if path.suffix.lower() == ".md":
        if not decoded.lstrip().startswith("---"):
            return NodeHealthResult(
                path=path,
                kind="NO_FRONTMATTER",
                severity="WARN",
                detail="no_yaml_frontmatter",
            )

    return None


def scan_vault_backlog(backlog_dir: Path) -> list[NodeHealthResult]:
    """
    Scannt alle *.md-Files in backlog_dir (flat + eine Ebene Subdirs, NICHT vollstaendig rekursiv).
    Gibt Liste aller kranken Nodes zurueck (leer = alles gesund).
    Directories werden ignoriert (nur is_file() + suffix=='.md').
    """
    results: list[NodeHealthResult] = []

    if not backlog_dir.is_dir():
        return results

    for entry in backlog_dir.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".md":
            r = scan_vault_node(entry)
            if r is not None:
                results.append(r)

    return results


# ---------------------------------------------------------------------------
# Optional CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Vault-Node-Health-Scanner (BL-443)")
    parser.add_argument("path", nargs="?", help="Pfad zu Node-Datei oder Backlog-Verzeichnis")
    args = parser.parse_args()

    if not args.path:
        parser.print_help()
        sys.exit(0)

    p = Path(args.path)
    if p.is_dir():
        results = scan_vault_backlog(p)
        if not results:
            print("Alle Nodes gesund.")
        else:
            for r in results:
                print(f"[{r.severity}] {r.kind}: {r.path} ({r.detail})")
    elif p.is_file():
        result = scan_vault_node(p)
        if result is None:
            print(f"Gesund: {p}")
        else:
            print(f"[{result.severity}] {result.kind}: {p} ({result.detail})")
    else:
        print(f"Pfad nicht gefunden: {p}")
        sys.exit(1)


if __name__ == "__main__":
    _main()
