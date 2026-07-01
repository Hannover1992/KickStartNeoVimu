#!/usr/bin/env python3
"""
dry_run_reporter.py — BL-460 B-3a GREEN-Phase.

AK-3-PL-1: Dry-Run-Report + write_gate_guard-Integration (dry-run-gate).

Erzeugt einen Dry-Run-Report (pro View: vorgeschlagene source_atoms + Score)
OHNE den Vault zu schreiben.

Reuse:
  - write_gate_guard.is_write_gated (B-1): dry-run-gate (PT-GEN-HookGuard-Mirror)
  - resolve_vault_root (DT-13): Vault-Root-Resolver

DT-5 exit codes: 0=report-created, 1=error, 2=usage-error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# DT-13: resolve_vault_root als Lead-Resolver
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from resolve_vault_root import resolve_vault_root as _resolve_vault_root
    _HAS_VAULT_RESOLVER = True
except ImportError:
    _HAS_VAULT_RESOLVER = False

# PT-GEN-HookGuard-Mirror: write_gate_guard.is_write_gated importieren (B-1)
# fail-open bei ImportError
try:
    from write_gate_guard import is_write_gated as _is_write_gated_import
    _HAS_WRITE_GATE = True

    def _is_write_gated_fn(vault_root=None):
        return _is_write_gated_import(vault_root)

except ImportError:
    _HAS_WRITE_GATE = False

    def _is_write_gated_fn(vault_root=None):
        # fail-open: kein Gate verfuegbar
        return (False, "write_gate_guard not available (fail-open)")


def dry_run(
    views: list[str],
    scorer,  # ScorerInterface: scorer(view_path, vault_root) -> list[dict]
    vault_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict:
    """
    Erzeugt einen Dry-Run-Report OHNE den Vault zu schreiben.

    ScorerInterface-Vertrag:
        scorer(view_path: str, vault_root: Path) -> list[dict]
        Jedes Element: {"atom_id": str, "score": float, "label": str}

    Integriert write_gate_guard.is_write_gated (B-1) als dry-run-gate.

    Args:
        views:       Liste von View-Pfaden
        scorer:      Callable (ScorerInterface), injiziert fuer Testbarkeit
        vault_root:  Vault-Root (None -> resolve_vault_root DT-13)
        output_path: Optionaler Pfad fuer JSON-Report-Ausgabe

    Returns:
        report_dict mit status, views, total_views, views_with_proposals, generated_at
    """
    # vault_root bestimmen
    if vault_root is None:
        if _HAS_VAULT_RESOLVER:
            try:
                vault_root = _resolve_vault_root()
            except Exception:
                vault_root = None
    vault_root_path = Path(vault_root) if vault_root is not None else None

    # write_gate_guard pruefen (dry-run-gate)
    warn_no_gate = False
    if _HAS_WRITE_GATE:
        gated, gate_reason = _is_write_gated_fn(vault_root_path)
    else:
        # fail-open: kein Gate
        gated = False
        gate_reason = "write_gate_guard not available (fail-open)"
        warn_no_gate = True

    overall_status = "BLOCKED" if gated else "ALLOW"
    blocked_reason = gate_reason if gated else None

    # Pro View: Scorer aufrufen, Report-Eintrag bauen
    view_entries = []
    views_with_proposals = 0

    for view_path in views:
        try:
            atoms = scorer(view_path, vault_root_path) if scorer is not None else []
        except Exception:
            atoms = []

        if atoms:
            views_with_proposals += 1
            entry_status = "ALLOW"
        else:
            entry_status = "NO_MATCH"

        view_entries.append({
            "path": view_path,
            "proposed_atoms": atoms,
            "status": entry_status,
        })

    report = {
        "status": overall_status,
        "blocked_reason": blocked_reason,
        "views": view_entries,
        "total_views": len(views),
        "views_with_proposals": views_with_proposals,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    if warn_no_gate:
        report["warn"] = "write_gate_guard not available — gate check skipped (fail-open)"

    # Optional: Report in Datei schreiben (output_path ist AUSSERHALB des Vault)
    if output_path is not None:
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)

    return report


def assert_dry_run_before_write(
    report_path: str | Path,
) -> tuple[bool, str]:
    """
    Dry-Run-Gate (AK-3): Blockiert --write wenn kein Dry-Run-Report vorhanden.

    Args:
        report_path: Pfad zum erwarteten Dry-Run-Report (JSON)

    Returns:
        (True,  "")           — Report existiert und parsebar (ALLOW --write)
        (False, reason_str)   — Report fehlt oder nicht parsebar (BLOCK --write)
    """
    p = Path(report_path)

    try:
        if not p.exists():
            return False, f"Dry-Run-Report fehlt: {report_path}"

        # Versuche JSON zu parsen
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)

        # Minimale Validierung: muss dict mit 'status' sein
        if not isinstance(data, dict):
            return False, f"Report ist kein JSON-Objekt: {report_path}"

        return True, ""

    except (json.JSONDecodeError, ValueError) as e:
        return False, f"Report JSON-Parse-Fehler: {e}"
    except (PermissionError, IOError, OSError) as e:
        return False, f"Report nicht lesbar: {e}"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. DT-5: exit 0=report-created, 1=error, 2=usage."""
    parser = argparse.ArgumentParser(
        description="Erstellt Dry-Run-Report fuer View->Atom-Referenzierung."
    )
    parser.add_argument("--vault-root", default=None, help="Vault-Root-Pfad")
    parser.add_argument(
        "--views-json",
        default=None,
        help="Pfad zu JSON-Datei mit Liste von View-Pfaden",
    )
    parser.add_argument("--output", default=None, help="Ausgabepfad fuer JSON-Report")
    parser.add_argument(
        "--scorer",
        default=None,
        help="Scorer als MODULE.FUNCTION (optional, default: stub-scorer)",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2

    # Views einlesen
    if args.views_json is not None:
        try:
            with open(args.views_json, encoding="utf-8") as fh:
                views = json.load(fh)
            if not isinstance(views, list):
                print("ERROR: views-json muss eine JSON-Liste sein", file=sys.stderr)
                return 2
        except (json.JSONDecodeError, IOError) as e:
            print(f"ERROR: views-json: {e}", file=sys.stderr)
            return 1
    else:
        views = []

    # Scorer bestimmen
    scorer_fn = None
    if args.scorer:
        try:
            module_name, func_name = args.scorer.rsplit(".", 1)
            import importlib
            mod = importlib.import_module(module_name)
            scorer_fn = getattr(mod, func_name)
        except Exception as e:
            print(f"ERROR: Scorer laden fehlgeschlagen: {e}", file=sys.stderr)
            return 1
    else:
        # Stub-Scorer (B-4 nicht vorhanden -> leere Proposals)
        def scorer_fn(view_path, vault_root):
            return []

    # Vault-Root bestimmen
    vault_root = args.vault_root
    if vault_root is None and _HAS_VAULT_RESOLVER:
        try:
            vault_root = _resolve_vault_root()
        except Exception:
            pass

    try:
        report = dry_run(
            views=views,
            scorer=scorer_fn,
            vault_root=vault_root,
            output_path=args.output,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Wenn kein --output: JSON auf stdout ausgeben
    if args.output is None:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Report geschrieben: {args.output} (status={report['status']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
