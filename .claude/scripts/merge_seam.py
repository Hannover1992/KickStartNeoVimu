#!/usr/bin/env python3
"""
merge_seam.py — BL-425 batch_1: Merge-Seam Utility (default-OFF, kein --force).

Stellt folgende Kernfunktionen bereit:
  - mergeable_check: git merge-tree Dry-Run + git status Verdikt (CLEAN/CONFLICT/DIRTY)
  - merge_exec: ff-bevorzugter Merge (NIE --force/-f)
  - conflict_to_pl: PL-Draft bei CONFLICT/DIRTY (fail-loud bei leerer files-Liste)
  - do_merge_if_clean: Aufruf-Guard — ruft merge_exec NUR bei CLEAN-Verdikt
  - is_ff_safe: prueft ob ref Vorfahre von new_tip ist (BL-490)
  - advance_ref_ff_safe: bewegt ref FF-sicher auf new_tip (BL-490)

Aufruf-Schema:
  mergeable_check(current_branch, merge_target, run=subprocess.run) -> "CLEAN"|"CONFLICT"|"DIRTY"
  merge_exec(current_branch, merge_target, run=subprocess.run) -> dict
  conflict_to_pl(verdict, files, target) -> dict
  do_merge_if_clean(verdict, current_branch, merge_target, merge_exec_fn=merge_exec) -> dict|None
  is_ff_safe(ref, new_tip, run=subprocess.run) -> bool
  advance_ref_ff_safe(ref, new_tip, run=subprocess.run) -> dict
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

_CONFLICT_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")


def _default_run(cmd: List[str], **kwargs: Any) -> Any:
    """Standard subprocess.run Wrapper (capture_output=True, text=True)."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


# ---------------------------------------------------------------------------
# mergeable_check — Dry-Run Verdikt
# ---------------------------------------------------------------------------

def mergeable_check(
    current_branch: str,
    merge_target: str,
    *,
    run: Optional[Callable[..., Any]] = None,
) -> str:
    """Bestimmt ob ein Merge sauber durchfuehrbar ist (Dry-Run, kein echter Merge).

    Ablauf:
      1. git status --porcelain pruefen: nicht-leere Ausgabe -> "DIRTY"
      2. git merge-tree HEAD <merge_target> ausfuehren:
         - Konflikt-Marker in Ausgabe -> "CONFLICT"
         - sonst -> "CLEAN"

    Args:
        current_branch: Aktueller Branch-Name (info, wird nicht aktiv genutzt).
        merge_target:   Ziel-Branch fuer den Merge (z.B. "develop").
        run:            Inject-Punkt fuer Tests (ersetzt subprocess.run).

    Returns:
        "CLEAN" | "CONFLICT" | "DIRTY"
    """
    _run = run if run is not None else _default_run

    # Schritt 1: Working-Tree sauber?
    status_result = _run(["git", "status", "--porcelain"])
    if status_result.stdout and status_result.stdout.strip():
        return "DIRTY"

    # Schritt 2: merge-tree Dry-Run
    merge_tree_result = _run(["git", "merge-tree", "HEAD", merge_target])
    output = merge_tree_result.stdout or ""
    for marker in _CONFLICT_MARKERS:
        if marker in output:
            return "CONFLICT"

    return "CLEAN"


# ---------------------------------------------------------------------------
# merge_exec — Tatsaechlicher Merge (ff-bevorzugt, NIE --force/-f)
# ---------------------------------------------------------------------------

def merge_exec(
    current_branch: str,
    merge_target: str,
    *,
    run: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Fuehrt einen ff-bevorzugten Merge durch. NIEMALS --force oder -f.

    Args:
        current_branch: Aktueller Branch (info).
        merge_target:   Ziel-Branch (z.B. "develop").
        run:            Inject-Punkt fuer Tests.

    Returns:
        dict mit status, returncode, stdout, stderr.
    """
    _run = run if run is not None else _default_run

    cmd = ["git", "merge", "--ff", merge_target]
    result = _run(cmd)

    return {
        "status": "merged" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stdout": result.stdout or "",
        "stderr": getattr(result, "stderr", "") or "",
        "merge_target": merge_target,
    }


# ---------------------------------------------------------------------------
# do_merge_if_clean — Aufruf-Guard (AK-5)
# ---------------------------------------------------------------------------

def do_merge_if_clean(
    verdict: str,
    current_branch: str,
    merge_target: str,
    *,
    merge_exec_fn: Optional[Callable[..., Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Aufruf-Guard: fuehrt merge_exec_fn NUR bei CLEAN-Verdikt aus.

    Bei CONFLICT oder DIRTY: No-Op (kein Merge, kein Fehler).

    Args:
        verdict:        Ergebnis von mergeable_check ("CLEAN"|"CONFLICT"|"DIRTY").
        current_branch: Aktueller Branch.
        merge_target:   Ziel-Branch.
        merge_exec_fn:  Inject-Punkt fuer merge_exec (Default: merge_exec).

    Returns:
        merge_exec-Ergebnis bei CLEAN, sonst None.
    """
    if verdict != "CLEAN":
        return None

    _fn = merge_exec_fn if merge_exec_fn is not None else merge_exec
    return _fn(current_branch, merge_target)


# ---------------------------------------------------------------------------
# conflict_to_pl — PL-Draft bei CONFLICT/DIRTY (fail-loud)
# ---------------------------------------------------------------------------

def conflict_to_pl(
    verdict: str,
    files: List[str],
    target: str,
) -> Dict[str, Any]:
    """Erzeugt einen PL-Item-Draft bei Merge-Konflikt oder Dirty-State.

    fail-loud: leere files-Liste wirft ValueError (kein None, kein leerer Dict).

    Args:
        verdict:  "CONFLICT" oder "DIRTY".
        files:    Liste der Konflikt-Dateien (nicht leer!).
        target:   Merge-Ziel-Branch.

    Returns:
        dict mit conflict_files, merge_target, hold=True, verdict.

    Raises:
        ValueError: wenn files leer ist.
    """
    if not files:
        raise ValueError(
            f"conflict_to_pl: files darf nicht leer sein (fail-loud). "
            f"verdict={verdict!r}, target={target!r}"
        )

    return {
        "conflict_files": files,
        "merge_target": target,
        "hold": True,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# is_ff_safe — FF-Ancestor-Pruefung (BL-490)
# ---------------------------------------------------------------------------

def is_ff_safe(
    ref: str,
    new_tip: str,
    *,
    run: Optional[Callable[..., Any]] = None,
) -> bool:
    """Prueft ob ref ein Vorfahre von new_tip ist (FF-sicher).

    Fuehrt exakt einen git-Aufruf aus:
      git merge-base --is-ancestor <ref> <new_tip>
    returncode == 0 bedeutet ref ist Vorfahre -> True (FF-sicher).
    Jeder andere returncode -> False (nicht FF-sicher).

    Args:
        ref:     Branch-/Ref-Name der bewegt werden soll.
        new_tip: Ziel-Ref (neuer Tip).
        run:     Inject-Punkt fuer Tests (ersetzt subprocess.run).

    Returns:
        True wenn ref Vorfahre von new_tip ist, sonst False.
    """
    _run = run if run is not None else _default_run
    result = _run(["git", "merge-base", "--is-ancestor", ref, new_tip])
    return result.returncode == 0


# ---------------------------------------------------------------------------
# advance_ref_ff_safe — FF-sicheres Branch-Vorbewegen (BL-490)
# ---------------------------------------------------------------------------

def advance_ref_ff_safe(
    ref: str,
    new_tip: str,
    *,
    run: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Bewegt ref FF-sicher auf new_tip (via git branch -f), oder verweigert bei non-FF.

    Ablauf:
      1. is_ff_safe(ref, new_tip) pruefen.
      2. FF-sicher: git branch -f <ref> <new_tip> ausfuehren.
         -> {"status": "advanced"|"failed", "ref": ref, "new_tip": new_tip,
             "returncode": <rc>, "stdout": ..., "stderr": ...}
      3. nicht FF-sicher: KEIN branch-Befehl ausgefuehrt.
         -> {"status": "refused", "reason": "non_ff", "ref": ref, "new_tip": new_tip,
             "hint": <str mit 'merge' und ref-Namen>}

    Args:
        ref:     Branch-Name der bewegt werden soll.
        new_tip: Ziel-Ref (neuer Tip).
        run:     Inject-Punkt fuer Tests.

    Returns:
        dict mit status und weiteren Feldern (siehe Ablauf).
    """
    _run = run if run is not None else _default_run

    if is_ff_safe(ref, new_tip, run=_run):
        cmd = ["git", "branch", "-f", ref, new_tip]
        result = _run(cmd)
        return {
            "status": "advanced" if result.returncode == 0 else "failed",
            "ref": ref,
            "new_tip": new_tip,
            "returncode": result.returncode,
            "stdout": result.stdout or "",
            "stderr": getattr(result, "stderr", "") or "",
        }
    else:
        hint = (
            f"'{ref}' hat Commits, die nicht in '{new_tip}' sind — "
            f"'git branch -f {ref} {new_tip}' wuerde sie verwaisen. "
            f"Nutze 'git merge {new_tip}' (oder merge_seam) statt -f."
        )
        return {
            "status": "refused",
            "reason": "non_ff",
            "ref": ref,
            "new_tip": new_tip,
            "hint": hint,
        }


# ---------------------------------------------------------------------------
# CLI — AK-2: advance Subcommand (BL-490)
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """CLI-Einstiegspunkt fuer merge_seam.py.

    Subcommands:
      advance --ref <ref> --to <new_tip>
        Ruft advance_ref_ff_safe(ref, new_tip) auf, gibt JSON auf stdout aus.
        Exit-Codes: advanced -> 0, refused -> 2, failed -> 1.

    Returns:
        Exit-Code als int.
    """
    parser = argparse.ArgumentParser(
        prog="merge_seam",
        description="Merge-Seam Utility (BL-425/BL-490)",
    )
    subparsers = parser.add_subparsers(dest="command")

    advance_parser = subparsers.add_parser(
        "advance",
        help="Bewegt einen Ref FF-sicher auf einen neuen Tip.",
    )
    advance_parser.add_argument(
        "--ref",
        required=True,
        help="Branch-/Ref-Name der bewegt werden soll.",
    )
    advance_parser.add_argument(
        "--to",
        required=True,
        dest="new_tip",
        help="Ziel-Ref (neuer Tip).",
    )

    args = parser.parse_args(argv)

    if args.command == "advance":
        result = advance_ref_ff_safe(args.ref, args.new_tip)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        status = result.get("status")
        if status == "advanced":
            return 0
        elif status == "refused":
            return 2
        else:
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
