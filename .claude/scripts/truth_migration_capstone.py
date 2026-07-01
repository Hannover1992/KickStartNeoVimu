#!/usr/bin/env python3
"""BL-483 Capstone Migration Orchestrator.

Chains all migration stages (0-8) with per-stage gates + rollback.
INV-CAPSTONE-5: does NOT modify atom-writer tools — calls them only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# StageResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    stage_id: int
    name: str
    status: str
    gate_ok: bool
    # Stage 1 (atomize) fields
    write_scope: Optional[int] = None
    quarantine_refused: Optional[int] = None
    content_loss: Optional[int] = None
    quarantine_count: Optional[int] = None
    # Stage 3 (edge quality) fields
    dangling_count: Optional[int] = None
    max_edges_per_atom: Optional[int] = None
    # Stage 4 (backref) fields
    updated: Optional[int] = None
    # Stage 8 (BL-484) fields
    exit_code: Optional[int] = None


# ---------------------------------------------------------------------------
# Stage Registry
# ---------------------------------------------------------------------------

STAGES: Dict[int, Dict[str, Any]] = {
    0: {"name": "preflight_and_backup",   "tool": "truth_gate_check.py"},
    1: {"name": "atomize",                "tool": "truth_pilot_cutover.py"},
    2: {"name": "edges",                  "tool": "keyword_edge_writer.py"},
    3: {"name": "edge_quality_gate",      "tool": "keyword_edge_writer.py --dry-run"},
    4: {"name": "backref_inversion",      "tool": "truth_edge_backref.py"},
    5: {"name": "wikilinks",              "tool": "wikilink_materializer.py"},
    6: {"name": "edge_index",             "tool": "build_retrieval_index.py"},
    7: {"name": "views",                  "tool": "view_projector.py"},
    8: {"name": "post_gate_bl484",        "tool": "truth_capstone_gate.py"},
}

# ---------------------------------------------------------------------------
# Gate functions
# ---------------------------------------------------------------------------

def _gate_default(sr: StageResult) -> bool:
    """Fallback gate: trust gate_ok field."""
    return bool(sr.gate_ok)


def _gate_atomize(sr: StageResult) -> bool:
    """Stage 1: content_loss==0 AND quarantine_refused==quarantine_count."""
    content_ok = (sr.content_loss if sr.content_loss is not None else 0) == 0
    refused = sr.quarantine_refused if sr.quarantine_refused is not None else 0
    total = sr.quarantine_count if sr.quarantine_count is not None else 0
    quarantine_ok = refused == total
    return content_ok and quarantine_ok


def _gate_edge_quality(sr: StageResult) -> bool:
    """Stage 3: dangling_count==0 AND max_edges_per_atom<=15 (BL-455 cap)."""
    dangling = sr.dangling_count if sr.dangling_count is not None else 0
    dangling_ok = dangling == 0
    cap_ok = (sr.max_edges_per_atom is not None) and (sr.max_edges_per_atom <= 15)
    return dangling_ok and cap_ok


def _gate_backref(sr: StageResult) -> bool:
    """Stage 4: updated >= 0 (type safety) and gate_ok."""
    if sr.updated is not None and sr.updated < 0:
        return False
    return bool(sr.gate_ok)


def _gate_stage7(sr: StageResult) -> bool:
    """Stage 7 (views): no_substrate outcome is non-fatal (T2g spec).

    T2g: derivable=True OR reason=no_substrate → OK; silently-wrong derivation → FAIL.
    gate_ok is set by run_stage based on per-view tool exit code; a no_substrate
    verdict exits 0, so gate passes. Only genuine derivation failures exit non-zero.
    """
    return bool(sr.gate_ok)


def _gate_stage8(sr: StageResult) -> bool:
    """Stage 8 (BL-484): exit_code==0."""
    if sr.exit_code is not None:
        return sr.exit_code == 0
    return bool(sr.gate_ok)


GATE_CHECKS: Dict[int, Callable[[StageResult], bool]] = {
    0: _gate_default,
    1: _gate_atomize,
    2: _gate_default,
    3: _gate_edge_quality,
    4: _gate_backref,
    5: _gate_default,
    6: _gate_default,
    7: _gate_stage7,
    8: _gate_stage8,
}

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

_current_state: str = "INIT"


def set_state(state: str) -> None:
    """State-machine transition sink. Tests patch this to observe transitions."""
    global _current_state
    _current_state = state
    print(f"[STATE] -> {state}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def rollback(backup_tag: str, vault_root: Path) -> None:
    """Restore vault to pre-migration state using git tag created in Stage 0c."""
    print(
        f"[ROLLBACK] Restoring vault {vault_root} from backup tag: {backup_tag}",
        file=sys.stderr,
    )
    try:
        subprocess.run(
            ["git", "-C", str(vault_root), "checkout", backup_tag, "--", "."],
            check=False,
        )
    except Exception as exc:
        print(
            f"[ROLLBACK] git restore failed ({exc}). Manual restore from tag '{backup_tag}' required.",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Per-stage command builder (real paths; tests always mock run_stage)
# ---------------------------------------------------------------------------

_SCRIPTS = Path(__file__).parent


def _discover_views(vault: Path) -> List[Path]:
    """Discover parking-lot view files for view_projector.py.

    Only /6_PL/*-parking-lot.md files are recognised by view_projector.
    Model.md and root-level backups must NOT be discovered.
    """
    return sorted(Path(vault).glob("Backlog/**/6_PL/*-parking-lot.md"))


def _build_stage_cmd(
    stage_id: int,
    vault: Path,
    repo_models: Path,
    dry_run: bool,
    backup_tag: str,
    out_dir: Path,
) -> list:
    """Build subprocess argv for a stage.

    Returns List[str] for stages 0-6, 8.
    Returns List[List[str]] (one cmd per view) for stage 7.
    Returns [] for stage 7 when no views are discovered.
    """
    py = [sys.executable]

    if stage_id == 0:
        # Preflight + backup combined
        return py + [
            str(_SCRIPTS / "truth_gate_check.py"),
            "--vault", str(vault),
            "--repo-models", str(repo_models),
            "--jobs", "4",
            "--out", str(out_dir / "stage0_gate.json"),
        ]
    if stage_id == 1:
        cmd = py + [
            str(_SCRIPTS / "truth_pilot_cutover.py"),
            "--vault", str(vault),
            "--repo-models", str(repo_models),
            "--out", str(out_dir / "stage1_atomize.json"),
        ]
        if not dry_run:
            cmd.append("--confirm")
        return cmd
    if stage_id == 2:
        return py + [
            str(_SCRIPTS / "keyword_edge_writer.py"),
            "--vault", str(vault),
            "--idempotent", "--replace",
        ] + (["--dry-run"] if dry_run else [])
    if stage_id == 3:
        return py + [
            str(_SCRIPTS / "keyword_edge_writer.py"),
            "--vault", str(vault),
            "--dry-run",
        ]
    if stage_id == 4:
        # truth_edge_backref has NO --dry-run flag; dry-run = absence of --apply
        backup_dir = out_dir / "backref_backup"
        cmd4 = py + [str(_SCRIPTS / "truth_edge_backref.py"), str(vault), "--backup-dir", str(backup_dir)]
        if not dry_run:
            cmd4.append("--apply")
        return cmd4
    if stage_id == 5:
        # wikilink_materializer supports --dry-run; write mode uses --write (no --dry-run)
        cmd5 = py + [
            str(_SCRIPTS / "wikilink_materializer.py"),
            "--vault", str(vault),
            "--source-atoms-mode",
            "--report", str(out_dir / "stage5_wikilinks.json"),
        ]
        if dry_run:
            cmd5.append("--dry-run")
        else:
            cmd5.append("--write")
        return cmd5
    if stage_id == 6:
        return py + [
            str(_SCRIPTS / "build_retrieval_index.py"),
            "build",
            "--vault", str(vault),
        ]
    if stage_id == 7:
        # Fan-out: one command per discovered view (<view_path> <vault_root> [--write])
        views = _discover_views(vault)
        if not views:
            return []  # no views discovered — stage is a no-op
        flags = ["--write"] if not dry_run else []
        return [
            py + [str(_SCRIPTS / "view_projector.py"), str(v), str(vault)] + flags
            for v in views
        ]
    if stage_id == 8:
        return py + [
            str(_SCRIPTS / "truth_capstone_gate.py"),
            "--vault", str(vault),
            "--out", str(out_dir / "stage8_bl484_gate.json"),
        ]
    return []


def _parse_stage_output(stage_id: int, stdout: str) -> Dict[str, Any]:
    """Best-effort JSON parse of tool stdout for StageResult fields."""
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


# ---------------------------------------------------------------------------
# run_stage — per-stage dispatcher (mocked in all tests)
# ---------------------------------------------------------------------------

def run_stage(
    stage_id: int,
    cmd_or_fn: Any,
    *,
    gate_fn: Callable[[StageResult], bool],
    **kwargs: Any,
) -> StageResult:
    """Run one stage via subprocess or callable; build StageResult; evaluate gate.

    Tests monkeypatch this function at module level via patch.object(cap, 'run_stage').
    """
    stage_name = STAGES.get(stage_id, {}).get("name", f"stage_{stage_id}")

    if callable(cmd_or_fn):
        try:
            raw = cmd_or_fn(**kwargs)
            if isinstance(raw, StageResult):
                return raw
            exit_code = 0
            stdout = ""
        except FileNotFoundError:
            raise
        except Exception as exc:
            print(f"[Stage {stage_id}] callable error: {exc}", file=sys.stderr)
            return StageResult(
                stage_id=stage_id, name=stage_name, status="fail", gate_ok=False, exit_code=1
            )
    else:
        cmd = cmd_or_fn if isinstance(cmd_or_fn, list) else list(cmd_or_fn)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            exit_code = proc.returncode
            stdout = proc.stdout or ""
            if exit_code != 0:
                print(
                    f"[Stage {stage_id}] failed (exit {exit_code}): {proc.stderr}",
                    file=sys.stderr,
                )
                return StageResult(
                    stage_id=stage_id,
                    name=stage_name,
                    status="fail",
                    gate_ok=False,
                    exit_code=exit_code,
                )
        except FileNotFoundError:
            if stage_id == 8:
                raise
            print(f"[Stage {stage_id}] tool not found in path", file=sys.stderr)
            return StageResult(
                stage_id=stage_id, name=stage_name, status="fail", gate_ok=False, exit_code=127
            )
        except Exception as exc:
            print(f"[Stage {stage_id}] subprocess error: {exc}", file=sys.stderr)
            return StageResult(
                stage_id=stage_id, name=stage_name, status="fail", gate_ok=False, exit_code=1
            )

    # Parse output and build StageResult
    data = _parse_stage_output(stage_id, stdout)
    sr = StageResult(
        stage_id=stage_id,
        name=stage_name,
        status="ok",
        gate_ok=True,
        exit_code=exit_code,
        write_scope=data.get("write_scope"),
        quarantine_refused=data.get("quarantine_refused"),
        content_loss=data.get("content_loss"),
        quarantine_count=data.get("quarantine_count"),
        dangling_count=data.get("dangling_count"),
        max_edges_per_atom=data.get("max_edges_per_atom"),
        updated=data.get("updated"),
    )
    sr.gate_ok = gate_fn(sr)
    return sr


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def _result_to_dict(r: StageResult) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "stage_id": r.stage_id,
        "name": r.name,
        "status": r.status,
        "gate_ok": r.gate_ok,
    }
    for fname in (
        "write_scope", "quarantine_refused", "content_loss", "quarantine_count",
        "dangling_count", "max_edges_per_atom", "updated", "exit_code",
    ):
        val = getattr(r, fname, None)
        if val is not None:
            d[fname] = val
    return d


def _write_report(
    out: Optional[Path],
    vault: Path,
    run_ts: str,
    results: List[StageResult],
    overall_ok: bool,
    **extra: Any,
) -> None:
    report: Dict[str, Any] = {
        "vault": str(vault),
        "run_ts": run_ts,
        "stages": [_result_to_dict(r) for r in results],
        "overall_ok": overall_ok,
    }
    report.update(extra)
    if out is not None:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main run() orchestrator
# ---------------------------------------------------------------------------

def run(
    vault: Any,
    repo_models: Any,
    dry_run: bool = True,
    force_go: bool = False,
    stage_from: int = 0,
    stage_to: int = 8,
    out: Optional[Any] = None,
) -> None:
    """Run the capstone migration pipeline.

    WRITE-FENCE: if dry_run is False and force_go is False, prompt for 'GO'.
    Gate failure: set_state('ROLLBACK'); if not dry_run call rollback(); sys.exit(2).
    Stage 8 FileNotFoundError: WARNING + continue, no rollback, overall_ok from 0-7.
    Success: set_state('DONE'); write report; sys.exit(0).
    """
    vault = Path(vault)
    repo_models = Path(repo_models)
    out_path = Path(out) if out is not None else None
    run_ts = datetime.now(timezone.utc).isoformat()

    # WRITE-FENCE — must happen BEFORE any stage
    if not dry_run and not force_go:
        response = input("Type GO to proceed with vault writes: ")
        if response != "GO":
            sys.exit(3)

    # Backup tag generated up front (used in rollback even if stage 0 fails)
    backup_tag = (
        "migration-capstone-backup-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    )
    out_dir = vault / ".claude" / "output" / "capstone"
    out_dir.mkdir(parents=True, exist_ok=True)

    results: List[StageResult] = []

    for stage_id in range(stage_from, stage_to + 1):
        if stage_id not in STAGES:
            continue

        gate_fn = GATE_CHECKS.get(stage_id, _gate_default)
        cmd = _build_stage_cmd(stage_id, vault, repo_models, dry_run, backup_tag, out_dir)

        # ------------------------------------------------------------------
        # Stage 8: INV-CAPSTONE-4 — interface only, no rollback if missing
        # ------------------------------------------------------------------
        if stage_id == 8:
            try:
                result = run_stage(stage_id, cmd, gate_fn=gate_fn, vault=vault, dry_run=dry_run)
                results.append(result)
                if not result.gate_ok:
                    set_state("ROLLBACK")
                    if not dry_run:
                        rollback(backup_tag, vault)
                    _write_report(out_path, vault, run_ts, results, False)
                    sys.exit(2)
            except FileNotFoundError:
                print(
                    "WARNING: Stage 8 (BL-484 post-gate) tool not available — skipping.",
                    file=sys.stderr,
                )
            continue

        # ------------------------------------------------------------------
        # Stage 7: fan-out over discovered views, aggregate into one result
        # ------------------------------------------------------------------
        if stage_id == 7:
            raw_cmds = cmd  # List[List[str]] or []
            if not raw_cmds:
                # No views discovered — stage is a no-op, gate passes
                result = StageResult(
                    stage_id=7, name=STAGES[7]["name"], status="ok", gate_ok=True
                )
            elif isinstance(raw_cmds[0], list):
                # Fan-out: one run_stage call per view
                agg_ok = True
                for per_view_cmd in raw_cmds:
                    r = run_stage(
                        stage_id, per_view_cmd, gate_fn=gate_fn,
                        vault=vault, dry_run=dry_run,
                    )
                    if not r.gate_ok:
                        agg_ok = False
                result = StageResult(
                    stage_id=7,
                    name=STAGES[7]["name"],
                    status="ok" if agg_ok else "fail",
                    gate_ok=agg_ok,
                )
            else:
                # Backward-compat: single flat command list
                result = run_stage(stage_id, raw_cmds, gate_fn=gate_fn, vault=vault, dry_run=dry_run)
            results.append(result)
            gate_ok = result.gate_ok
            if not gate_ok:
                set_state("ROLLBACK")
                if not dry_run:
                    rollback(backup_tag, vault)
                _write_report(out_path, vault, run_ts, results, False)
                sys.exit(2)
            continue

        # ------------------------------------------------------------------
        # Stages 0-6: run + gate check (trust gate_ok as set by run_stage)
        # ------------------------------------------------------------------
        result = run_stage(stage_id, cmd, gate_fn=gate_fn, vault=vault, dry_run=dry_run)
        results.append(result)

        gate_ok = result.gate_ok
        if not gate_ok:
            set_state("ROLLBACK")
            if not dry_run:
                rollback(backup_tag, vault)

            extra: Dict[str, Any] = {}
            if stage_id == 0:
                extra["aborted_at"] = "PREFLIGHT_CHECK"
                extra["gate_fail"] = "truth_gate_check"

            _write_report(out_path, vault, run_ts, results, False, **extra)
            sys.exit(2)

        # After stage 0, create the git backup tag (non-dry-run)
        if stage_id == 0 and not dry_run:
            try:
                subprocess.run(
                    ["git", "-C", str(vault), "tag", backup_tag],
                    check=False,
                )
            except Exception:
                pass  # filesystem fallback noted in rollback

    # ------------------------------------------------------------------
    # All stages in range passed
    # ------------------------------------------------------------------
    set_state("DONE")
    # overall_ok reflects stages 0-7 only (stage 8 is interface-only)
    stages_07 = [r for r in results if r.stage_id <= 7]
    overall_ok = all(r.gate_ok for r in stages_07)
    _write_report(out_path, vault, run_ts, results, overall_ok)
    sys.exit(0)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: List[str]) -> None:
    """Parse argv list and dispatch to run(). Parses the passed list, NOT sys.argv."""
    parser = argparse.ArgumentParser(
        prog="truth_migration_capstone",
        description="BL-483 Capstone Migration Orchestrator",
    )
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Execute migration pipeline")
    run_p.add_argument("--vault", required=True, help="Path to vault root")
    run_p.add_argument("--repo-models", default=".", help="Path to repo models dir")
    run_p.add_argument(
        "--write",
        action="store_true",
        default=False,
        help="Execute writes (default: dry-run)",
    )
    run_p.add_argument(
        "--force-go",
        action="store_true",
        default=False,
        help="Skip interactive GO prompt (CI/automation use)",
    )
    run_p.add_argument("--stage-from", type=int, default=0, help="Start from stage N")
    run_p.add_argument("--stage-to", type=int, default=8, help="Stop after stage N")
    run_p.add_argument("--out", default=None, help="Write JSON report to this path")

    args = parser.parse_args(argv)

    if args.command == "run":
        run(
            vault=Path(args.vault),
            repo_models=Path(args.repo_models),
            dry_run=not args.write,
            force_go=args.force_go,
            stage_from=args.stage_from,
            stage_to=args.stage_to,
            out=Path(args.out) if args.out else None,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
