"""
BL-450 batch_2 -- _extraction_orchestrate.py
Vault-agnostischer 5-Stufen-Orchestrator CLI-Dispatcher.

INV-EO-1: Kein hardcoded Vault-Pfad.
INV-EO-2: Stufe 4 nur mit --confirm-cutover (sonst exit 1).
INV-EO-3: Reiner Dispatcher, keine Migrations-Logik.
INV-EO-4: --vault required (argparse), kein Default.
INV-EO-5: subprocess.run weitergeben --vault als Pflicht-Parameter.
"""

import argparse
import pathlib
import subprocess
import sys

# ---------------------------------------------------------------------------
# Konstanten / Exit-Codes
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERROR = 1          # Vault-/Gate-/Laufzeitfehler
EXIT_UNKNOWN_MODE = 2   # unbekannter Modus (analog argparse-choices-Fehler)

_SCRIPTS_DIR = pathlib.Path(__file__).parent


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def resolve_vault_root(path_str: str) -> pathlib.Path:
    """Validiert --vault Parameter. Gibt Path zurueck oder wirft Exception."""
    p = pathlib.Path(path_str)
    if not p.exists() or not p.is_dir():
        print(f"ERROR: --vault Pfad existiert nicht oder ist kein Verzeichnis: {path_str}", file=sys.stderr)
        raise FileNotFoundError(f"Vault-Pfad nicht gefunden: {path_str}")
    return p


def _py() -> str:
    """Python-Interpreter (sys.executable fuer konsistente Umgebung)."""
    return sys.executable


def _run_script(script_name: str, vault: pathlib.Path, extra_args=None,
                dry_run: bool = False) -> int:
    """
    DRY-Helper: ruft ein Sub-Script via subprocess.run mit einheitlicher
    Argument-Konvention auf (--vault PFLICHT, INV-EO-5).

    extra_args: zusaetzliche Script-spezifische Argumente (z.B. --mode global, --confirm).
    dry_run:    haengt --dry-run an, wenn True.
    """
    cmd = [_py(), str(_SCRIPTS_DIR / script_name), "--vault", str(vault)]
    if extra_args:
        cmd.extend(extra_args)
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd)
    return result.returncode


# ---------------------------------------------------------------------------
# Stufen-Dispatch-Funktionen
# ---------------------------------------------------------------------------

def run_stage1_analyse(vault: pathlib.Path, dry_run: bool) -> int:
    """Stufe 1: truth_migrate_orchestrator.py --mode global."""
    return _run_script("truth_migrate_orchestrator.py", vault,
                       extra_args=["--mode", "global"], dry_run=dry_run)


def run_stage2_prep(vault: pathlib.Path, dry_run: bool) -> int:
    """Stufe 2: truth_normalize.py."""
    return _run_script("truth_normalize.py", vault, dry_run=dry_run)


def run_stage3_probe(vault: pathlib.Path, dry_run: bool) -> int:
    """Stufe 3: truth_gate_check.py (laeuft selbst immer im --dry-run-Pruefmodus)."""
    return _run_script("truth_gate_check.py", vault,
                       extra_args=["--dry-run"], dry_run=dry_run)


def run_stage4_extract(vault: pathlib.Path, confirm_cutover: bool) -> int:
    """Stufe 4: truth_pilot_cutover.py -- NUR wenn confirm_cutover=True (INV-EO-2 GATE)."""
    if not confirm_cutover:
        print("ERROR: Stufe 4 (Cutover) erfordert --confirm-cutover (INV-EO-2).", file=sys.stderr)
        return EXIT_ERROR
    return _run_script("truth_pilot_cutover.py", vault, extra_args=["--confirm"])


def run_stage5_edges(vault: pathlib.Path, dry_run: bool, idempotent: bool) -> int:
    """Stufe 5: keyword_edge_writer.main() (direkter Import, batch_1-Script)."""
    import keyword_edge_writer
    argv = ["--vault", str(vault)]
    if dry_run:
        argv.append("--dry-run")
    if idempotent:
        argv.append("--idempotent")
    return keyword_edge_writer.main(argv)


# ---------------------------------------------------------------------------
# Modi-Dispatch
# ---------------------------------------------------------------------------

def _run_sequence(stages) -> int:
    """
    Fuehrt eine Folge von Stufen-Callables (jeweils () -> int) der Reihe nach aus.
    Short-Circuit: bricht beim ersten Nicht-Null-Exit ab und gibt ihn zurueck.
    """
    for stage in stages:
        rc = stage()
        if rc != EXIT_OK:
            return rc
    return EXIT_OK


def _require_cutover_confirm(mode: str, confirm_cutover: bool) -> bool:
    """
    INV-EO-2-Gate auf Modus-Ebene: cutover-behaftete Modi (extract/full) duerfen
    nur mit --confirm-cutover laufen. Gibt True zurueck wenn freigegeben, sonst
    False (mit Fehlermeldung). Defense-in-depth zu run_stage4_extract.
    """
    if not confirm_cutover:
        print(f"ERROR: mode={mode} erfordert --confirm-cutover (INV-EO-2).", file=sys.stderr)
        return False
    return True


def dispatch_mode(
    mode: str,
    vault: pathlib.Path,
    dry_run: bool,
    confirm_cutover: bool,
    idempotent: bool,
) -> int:
    """Router fuer 5 Modi -- reiner Dispatcher (INV-EO-3)."""
    # Wiederverwendbare Stufen-Closures (capture aktuelle Parameter).
    stage1 = lambda: run_stage1_analyse(vault, dry_run)
    stage2 = lambda: run_stage2_prep(vault, dry_run)
    stage3 = lambda: run_stage3_probe(vault, dry_run)
    stage4 = lambda: run_stage4_extract(vault, confirm_cutover)
    stage5 = lambda: run_stage5_edges(vault, dry_run, idempotent)

    if mode == "analyse":
        return _run_sequence([stage1])

    if mode == "probe":
        return _run_sequence([stage1, stage2, stage3])

    if mode == "extract":
        if not _require_cutover_confirm(mode, confirm_cutover):
            return EXIT_ERROR
        return _run_sequence([stage1, stage2, stage3, stage4])

    if mode == "edges":
        return _run_sequence([stage5])

    if mode == "full":
        if not _require_cutover_confirm(mode, confirm_cutover):
            return EXIT_ERROR
        return _run_sequence([stage1, stage2, stage3, stage4, stage5])

    print(f"ERROR: Unbekannter Modus: {mode}", file=sys.stderr)
    return EXIT_UNKNOWN_MODE


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="BL-450 5-Stufen-Orchestrator CLI-Dispatcher (vault-agnostisch)."
    )
    parser.add_argument(
        "--vault",
        required=True,
        metavar="PATH",
        help="Pfad zum Vault-Root-Verzeichnis (required, INV-EO-4).",
    )
    parser.add_argument(
        "--mode",
        required=False,
        default="analyse",
        choices=["analyse", "probe", "extract", "edges", "full"],
        help="Modus: analyse|probe|extract|edges|full.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Dry-Run: kein echtes Schreiben, Flag wird an Sub-Scripts weitergeleitet.",
    )
    parser.add_argument(
        "--confirm-cutover",
        action="store_true",
        default=False,
        help="Stufe-4-Gate: Explizites Bestaetigungsflag fuer Cutover (INV-EO-2).",
    )
    parser.add_argument(
        "--idempotent",
        action="store_true",
        default=True,
        help="Idempotenz-Flag fuer Stufe 5 (keyword_edge_writer).",
    )

    args = parser.parse_args(argv)

    # Vault validieren (exit != 0 bei Fehler)
    try:
        vault = resolve_vault_root(args.vault)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR

    return dispatch_mode(
        mode=args.mode,
        vault=vault,
        dry_run=args.dry_run,
        confirm_cutover=args.confirm_cutover,
        idempotent=args.idempotent,
    )


if __name__ == "__main__":
    sys.exit(main())
