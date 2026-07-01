#!/usr/bin/env python3
"""
disjunktheit_validator.py — BL-460 B-3a GREEN-Phase.

AK-1-PL-1: Pre-Build-Gate, behauptet Slice-Disjunktheit ueber einen Vollscan.

Prueft:
  1. Kein View-Pfad erscheint in zwei Slices (Duplikats-Check via Set-Intersection)
  2. Union aller Slices == full_corpus (Luecken-Check)

DT-5 exit codes: 0=disjoint/PASS, 1=violation/FAIL, 2=usage-error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def validate_disjoint(
    slices: list[list[str]],
    full_corpus: list[str],
) -> tuple[bool, str]:
    """
    Pre-Build-Gate: Behauptet Slice-Disjunktheit ueber einen Vollscan.

    Prueft:
    1. Kein View-Pfad erscheint in zwei Slices (Duplikats-Check via Set-Intersection)
    2. Union aller Slices == full_corpus (Luecken-Check)

    Args:
        slices:       Ausgabe von decompose_views()
        full_corpus:  Vollstaendige Liste aller View-Pfade (Referenz)

    Returns:
        (True,  "")           — disjoint + vollstaendig (PASS)
        (False, reason_str)   — Violation mit Beschreibung (FAIL)

    Hinweis:
        Pfad-Normierung (os.path.normcase) VOR Set-Operationen (Windows-Pfade).
    """
    # Pfad-Normierung fuer Windows/Unix
    def _norm(p: str) -> str:
        return os.path.normcase(os.path.normpath(p))

    # Normierte Corpus-Menge
    norm_corpus = {_norm(p) for p in full_corpus}
    # Rueck-Mapping: normierter Pfad -> original (fuer Fehlermeldungen)
    corpus_orig: dict[str, str] = {_norm(p): p for p in full_corpus}

    # Union aller Slices aufbauen + Duplikat-Check
    seen: dict[str, int] = {}  # normierter Pfad -> Slice-Index des ersten Vorkommens
    union: set[str] = set()

    for slice_idx, sl in enumerate(slices):
        for view in sl:
            norm_v = _norm(view)
            if norm_v in seen:
                # Duplikat gefunden
                reason = (
                    f"Duplicate view in slices {seen[norm_v]} and {slice_idx}: {view}"
                )
                return False, reason
            seen[norm_v] = slice_idx
            union.add(norm_v)

    # Luecken-Check: union muss == norm_corpus sein
    missing = norm_corpus - union
    if missing:
        # Fehlender Pfad: nimm einen aus missing
        missing_norm = next(iter(missing))
        missing_orig = corpus_orig.get(missing_norm, missing_norm)
        reason = f"View missing from all slices: {missing_orig}"
        return False, reason

    # Extra-Check: union darf nicht groesser als norm_corpus sein
    extra = union - norm_corpus
    if extra:
        # Extra View in Slice der nicht im Corpus ist
        extra_norm = next(iter(extra))
        # Finde den originalen Pfad aus den Slices
        extra_orig = extra_norm
        for sl in slices:
            for view in sl:
                if _norm(view) == extra_norm:
                    extra_orig = view
                    break
        reason = f"View in slice but not in corpus: {extra_orig}"
        return False, reason

    return True, ""


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. DT-5: exit 0=PASS, 1=FAIL/violation, 2=usage."""
    parser = argparse.ArgumentParser(
        description="Validiert Slice-Disjunktheit (Pre-Build-Gate)."
    )
    parser.add_argument(
        "--stdin-json",
        default=None,
        help='JSON-String: {"slices": [[...], ...], "full_corpus": [...]}',
    )
    parser.add_argument(
        "--slices-json",
        default=None,
        help="Pfad zu JSON-Datei mit Slices",
    )
    parser.add_argument(
        "--corpus-json",
        default=None,
        help="Pfad zu JSON-Datei mit full_corpus",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2

    # Input bestimmen
    slices = None
    full_corpus = None

    if args.stdin_json is not None:
        try:
            payload = json.loads(args.stdin_json)
            slices = payload.get("slices", [])
            full_corpus = payload.get("full_corpus", [])
        except (json.JSONDecodeError, ValueError) as e:
            print(f"ERROR: JSON-Parse-Fehler: {e}", file=sys.stderr)
            return 2

    elif args.slices_json is not None:
        try:
            with open(args.slices_json, encoding="utf-8") as fh:
                slices = json.load(fh)
        except (json.JSONDecodeError, IOError) as e:
            print(f"ERROR: slices-json: {e}", file=sys.stderr)
            return 2

        if args.corpus_json is not None:
            try:
                with open(args.corpus_json, encoding="utf-8") as fh:
                    full_corpus = json.load(fh)
            except (json.JSONDecodeError, IOError) as e:
                print(f"ERROR: corpus-json: {e}", file=sys.stderr)
                return 2
        else:
            full_corpus = []

    else:
        # Kein Input — Usage-Fehler
        print("ERROR: --stdin-json oder --slices-json fehlt", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 2

    ok, reason = validate_disjoint(slices, full_corpus)

    if ok:
        n_slices = len(slices)
        total_views = sum(len(sl) for sl in slices)
        print(f"PASS: Disjointness validated: {n_slices} slices, {total_views} views")
        return 0
    else:
        print(f"VIOLATION: {reason}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
