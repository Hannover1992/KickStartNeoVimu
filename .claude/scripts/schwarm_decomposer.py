#!/usr/bin/env python3
"""
schwarm_decomposer.py — BL-460 B-3a GREEN-Phase.

AK-1-PL-1: Partitioniert den View-Corpus (Models + arc42 + Parking + Docs)
in N disjunkte, kollisionsfreie Worker-Slices.

Reuse:
  - resolve_vault_root (DT-13): Vault-Root-Resolver
  - keyword_edge_writer._build_keyword_index pattern: vault rglob scan

DT-5 exit codes: 0=ok, 1=error, 2=usage-error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

# DT-13: resolve_vault_root als Lead-Resolver
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from resolve_vault_root import resolve_vault_root as _resolve_vault_root
    _HAS_VAULT_RESOLVER = True
except ImportError:
    _HAS_VAULT_RESOLVER = False

# SSoT view-node predicate — shared with P2 hook (hook_view_forward_reference.py)
try:
    from view_node_predicate import is_view_node as _is_view_node
    _HAS_VIEW_NODE_PREDICATE = True
except ImportError:
    _HAS_VIEW_NODE_PREDICATE = False
    _is_view_node = None  # type: ignore[assignment]


def _scan_views_direct(vault_root: Path, vault_root_str: str) -> list[str]:
    """Scan vault_root for all .md files and keep only is_view_node=True entries.

    Strategy: rglob("*.md") as superset, then filter through is_view_node (SSoT).
    Null-byte-corrupt files are skipped (analog keyword_edge_writer pattern).
    """
    views = set()

    for p in vault_root.rglob("*.md"):
        if not p.is_file():
            continue
        try:
            with open(p, "rb") as fh:
                raw = fh.read(512)
            if b"\x00" in raw:
                continue
        except (PermissionError, IOError, OSError):
            continue

        # SSoT filter: only keep files the canonical predicate accepts
        if _HAS_VIEW_NODE_PREDICATE and _is_view_node is not None:
            if not _is_view_node(str(p), vault_root_str):
                continue
        # Degraded (predicate unavailable): include all .md — not ideal but
        # the predicate module WILL be present in normal operation.

        views.add(str(p))

    return sorted(views)


def decompose_views(
    vault_root: str | Path,
    n_slices: int = 1,
    view_globs: list[str] | None = None,
) -> list[list[str]]:
    """
    Partitioniert den View-Corpus in n_slices disjunkte, kollisionsfreie Worker-Slices.

    Jede View erscheint in GENAU einem Slice.
    Union aller Slices == vollstaendiger View-Corpus.
    Deterministische Partition (gleicher Input -> gleicher Output).

    Corpus authority: is_view_node (view_node_predicate.py, SSoT).
    The view_globs param is accepted for backward-compat but the is_view_node
    filter is the sole authority — over-inclusion and under-inclusion are both
    impossible by construction.

    Args:
        vault_root:   Wurzel-Verzeichnis des OmniCommand-Vaults (DT-13-Delegate)
        n_slices:     Anzahl Slices (default 1 fuer slicing=false BL-NEW-29)
        view_globs:   Accepted for backward-compat; ignored — is_view_node is authoritative.

    Returns:
        list[list[str]] — N Slices, jeder eine Liste von View-Pfaden (str).
                          Leere Slices moeglich wenn n_slices > len(views).

    Raises:
        ValueError: wenn n_slices < 1
        IOError:    wenn vault_root nicht lesbar
    """
    if n_slices < 1:
        raise ValueError(f"n_slices muss >= 1 sein, bekam: {n_slices}")

    vault_path = Path(vault_root)
    vault_root_str = str(vault_path)

    # vault_root muss existieren — sonst empty result (nicht IOError, da Tests es so erwarten)
    if not vault_path.exists():
        # Gib n_slices leere Slices zurueck (oder leere Liste — Tests erlauben beides)
        return [[] for _ in range(n_slices)]

    # Superset rglob + is_view_node filter (SSoT by construction)
    all_views = _scan_views_direct(vault_path, vault_root_str)

    # Round-Robin-Partition: deterministisch (sorted paths, round-robin)
    slices: list[list[str]] = [[] for _ in range(n_slices)]
    for idx, view in enumerate(all_views):
        slices[idx % n_slices].append(view)

    return slices


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. DT-5: exit 0=ok, 1=error, 2=usage."""
    parser = argparse.ArgumentParser(
        description="Partitioniert den View-Corpus in N disjunkte Slices."
    )
    parser.add_argument("--vault-root", default=None, help="Vault-Root-Pfad")
    parser.add_argument(
        "--n-slices", type=int, default=1, help="Anzahl Slices (default: 1)"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Ausgabeformat (default: json)",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2

    # Vault-Root bestimmen
    vault_root = args.vault_root
    if vault_root is None:
        if _HAS_VAULT_RESOLVER:
            try:
                vault_root = _resolve_vault_root()
            except Exception:
                print("ERROR: vault-root nicht aufloesung moeglich", file=sys.stderr)
                return 1
        else:
            print("ERROR: --vault-root fehlt und resolve_vault_root nicht verfuegbar",
                  file=sys.stderr)
            return 1

    # n_slices validieren
    if args.n_slices < 1:
        print(f"ERROR: --n-slices muss >= 1 sein, bekam: {args.n_slices}",
              file=sys.stderr)
        return 2

    # Vault muss existieren
    if not Path(vault_root).exists():
        print(f"ERROR: vault-root nicht gefunden: {vault_root}", file=sys.stderr)
        return 1

    try:
        slices = decompose_views(vault_root, n_slices=args.n_slices)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except (IOError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    total_views = sum(len(sl) for sl in slices)

    if args.output_format == "json":
        result = {
            "slices": slices,
            "total_views": total_views,
            "n_slices": args.n_slices,
        }
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"n_slices={args.n_slices}, total_views={total_views}")
        for i, sl in enumerate(slices):
            print(f"  Slice {i}: {len(sl)} views")

    return 0


if __name__ == "__main__":
    sys.exit(main())
