#!/usr/bin/env python3
"""
Team-Lifecycle-Helper (BL-164 AK-1..AK-6).

Verwaltet Team-Shutdown mit Timeout, Force-Skip fuer stuck Workers,
Manifest-Tracking und Audit-Events fuer Pipeline-Stage-Transitionen.

Option A: Pro Stage eigenes Team (TeamDelete + Neu-Erstellung bei Handschuh-Wechsel).
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
AUDIT_DIR = ROOT_DIR / ".claude" / "audit"
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"
TEAMS_DIR = Path.home() / ".claude" / "teams"

# Exit-Codes
EXIT_CLEAN = 0
EXIT_FORCE_SKIPPED = 1
EXIT_FATAL = 2

# Standard-Timeout fuer Worker-Shutdown-Requests (Sekunden)
DEFAULT_SHUTDOWN_TIMEOUT_SEC = 120


def _now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _read_team_config(team_name: str) -> Optional[dict]:
    """Liest Team-Konfiguration aus ~/.claude/teams/{team_name}/config.json."""
    config_path = TEAMS_DIR / team_name / "config.json"
    if not config_path.exists():
        return None
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_team_config(team_name: str, config: dict) -> bool:
    """Schreibt Team-Konfiguration zurueck."""
    config_path = TEAMS_DIR / team_name / "config.json"
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def audit_team_lifecycle(event_type: str, **kwargs) -> None:
    """
    Schreibt strukturierten audit.jsonl-Eintrag (BL-159 AK-6 6-Feld-Format).

    Pflichtfelder: ts, event, tool, target, reason, guard
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": _now_ts(),
        "event": event_type,
        "tool": kwargs.get("tool", "TeamLifecycle"),
        "target": kwargs.get("target", ""),
        "reason": kwargs.get("reason", ""),
        "guard": "team_lifecycle_helper.py",
    }
    # Optionale Felder
    if "caller_context" in kwargs:
        entry["caller_context"] = kwargs["caller_context"]
    if "inputs" in kwargs:
        raw_inputs = kwargs["inputs"]
        # INV-ROLL-5: Werte > 200 Zeichen kuerzen, sensible Felder redacten
        sensitive_keys = {"key", "secret", "password", "token", "credential"}
        entry["inputs"] = {
            k: "<redacted>" if any(s in k.lower() for s in sensitive_keys)
            else ("<truncated>" if isinstance(v, str) and len(v) > 200 else v)
            for k, v in raw_inputs.items()
        }
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"[WARN] Audit-Write fehlgeschlagen: {exc}", file=sys.stderr)


def get_stuck_workers(team_name: str) -> list[str]:
    """
    Liest Team-Konfiguration und gibt Liste unresponsiver Worker zurueck.

    Ein Worker gilt als stuck wenn er kein ACK auf shutdown_request gesendet hat.
    Da diese Funktion synchron laeuft, prueft sie den `ack_received`-Flag im
    Team-Manifest (gesetzt von force_skip_worker nach Timeout).
    """
    config = _read_team_config(team_name)
    if config is None:
        return []
    stuck: list[str] = []
    for worker in config.get("workers", []):
        if worker.get("stuck", False):
            stuck.append(worker.get("name", worker.get("id", "unknown")))
    return stuck


def force_skip_worker(team_name: str, worker_name: str, reason: str) -> bool:
    """
    Entfernt Worker-Eintrag aus Team-Konfiguration und schreibt WORKER_SHUTDOWN_TIMEOUT.

    Der OS-Prozess des Workers laeuft weiter — kein Force-Kill (nicht idiomatisch).
    """
    config = _read_team_config(team_name)
    if config is None:
        print(f"[ERROR] Team-Config nicht gefunden: {team_name}", file=sys.stderr)
        return False

    workers_before = config.get("workers", [])
    config["workers"] = [
        w for w in workers_before
        if w.get("name", w.get("id", "")) != worker_name
    ]
    removed = len(workers_before) - len(config.get("workers", []))

    if removed == 0:
        print(f"[WARN] Worker '{worker_name}' nicht in Team '{team_name}' gefunden.")

    _write_team_config(team_name, config)

    audit_team_lifecycle(
        "WORKER_SHUTDOWN_TIMEOUT",
        tool="TeamLifecycle",
        target=f"{team_name}/{worker_name}",
        reason=f"WORKER_SHUTDOWN_TIMEOUT: {reason}",
        inputs={"team": team_name, "worker": worker_name},
    )
    print(
        f"[TEAM_SHUTDOWN] WARN worker {worker_name} stuck — Force-Skip applied"
        f" (team={team_name})"
    )
    return True


def cleanup_team(team_name: str, shutdown_timeout_sec: int = DEFAULT_SHUTDOWN_TIMEOUT_SEC) -> int:
    """
    Sendet shutdown_request an alle Worker, wartet mit Timeout, force-skipped stuck Worker.

    Rueckgabe-Exit-Code:
      0 = alles sauber
      1 = mind. ein Worker per Force-Skip entfernt
      2 = fataler Fehler (config unlesbar)
    """
    config = _read_team_config(team_name)
    if config is None:
        print(f"[ERROR] Team '{team_name}' nicht gefunden oder config.json unlesbar.", file=sys.stderr)
        audit_team_lifecycle(
            "TEAM_DELETE_FAILED",
            tool="TeamLifecycle",
            target=team_name,
            reason=f"TEAM_DELETE_FAILED: config.json nicht lesbar",
        )
        return EXIT_FATAL

    workers = config.get("workers", [])
    print(f"[TEAM_LIFECYCLE] cleanup_team '{team_name}' — {len(workers)} Worker, Timeout={shutdown_timeout_sec}s")

    if not workers:
        audit_team_lifecycle(
            "TEAM_DELETED",
            tool="TeamLifecycle",
            target=team_name,
            reason="TEAM_DELETED: Kein Worker aktiv — sauberes Loeschen",
        )
        print(f"[TEAM_LIFECYCLE] Team '{team_name}' sauber aufgeloest (0 Worker).")
        return EXIT_CLEAN

    # Simuliere shutdown_request an jeden Worker (in echter Implementierung via TeamAPI)
    pending_workers = [w.get("name", w.get("id", "unknown")) for w in workers]
    print(f"[TEAM_LIFECYCLE] shutdown_request -> {pending_workers}")

    # Warte mit Polling bis Timeout oder alle ACKs
    deadline = time.time() + shutdown_timeout_sec
    poll_interval = 5  # Sekunden zwischen Checks

    # In einer realen Implementierung wuerden hier ACK-Callbacks abgewartet.
    # Da wir keinen Live-ACK-Mechanismus haben, gehen wir nach Timeout zu Force-Skip.
    acked: list[str] = []
    stuck: list[str] = []

    while time.time() < deadline and pending_workers:
        # Pruefe aktuellen ACK-Status aus Team-Config
        current_config = _read_team_config(team_name)
        if current_config is None:
            break
        for w in current_config.get("workers", []):
            name = w.get("name", w.get("id", "unknown"))
            if w.get("ack_shutdown", False) and name in pending_workers:
                acked.append(name)
                pending_workers.remove(name)
                print(f"[TEAM_LIFECYCLE] ACK von Worker '{name}'")
        if pending_workers:
            time.sleep(poll_interval)

    # Verbleibende = stuck
    stuck = list(pending_workers)
    had_force_skip = False

    for worker_name in stuck:
        print(
            f"[TEAM_SHUTDOWN] WARN worker {worker_name} stuck nach {shutdown_timeout_sec}s "
            f"— Force-Skip applied"
        )
        force_skip_worker(
            team_name,
            worker_name,
            f"Kein ACK nach {shutdown_timeout_sec}s shutdown_request",
        )
        had_force_skip = True

    audit_team_lifecycle(
        "TEAM_DELETED",
        tool="TeamLifecycle",
        target=team_name,
        reason=(
            f"TEAM_DELETED: {len(acked)} sauber, {len(stuck)} force-skipped"
        ),
        inputs={
            "team": team_name,
            "acked_workers": acked,
            "force_skipped_workers": stuck,
            "shutdown_timeout_sec": shutdown_timeout_sec,
        },
    )
    print(
        f"[TEAM_LIFECYCLE] Team '{team_name}' aufgeloest: "
        f"{len(acked)} ACK, {len(stuck)} Force-Skip."
    )
    return EXIT_FORCE_SKIPPED if had_force_skip else EXIT_CLEAN


def register_team_transition(
    from_stage: str,
    to_stage: str,
    manifest_path: str,
) -> bool:
    """
    Schreibt TEAM_LIFECYCLE-Block in Manifest und TEAM_TRANSITION-Audit-Event.

    Erwartet YAML-Frontmatter-kompatibles Manifest. Fuegt TEAM_LIFECYCLE-Sektion
    am Ende ein wenn nicht vorhanden, oder aktualisiert team_history[].
    """
    manifest = Path(manifest_path)
    if not manifest.exists():
        print(f"[ERROR] Manifest nicht gefunden: {manifest_path}", file=sys.stderr)
        return False

    content = manifest.read_text(encoding="utf-8")
    ts = _now_ts()

    transition_entry = (
        f"  - {{ stage: {to_stage}, from: {from_stage}, "
        f"transition_ts: {ts} }}"
    )

    if "TEAM_LIFECYCLE:" not in content:
        # Erste Transition — Block anfuegen
        lifecycle_block = (
            f"\n\n## TEAM_LIFECYCLE\n\n"
            f"```yaml\n"
            f"TEAM_LIFECYCLE:\n"
            f"  current_team: null\n"
            f"  team_history:\n"
            f"{transition_entry}\n"
            f"  total_stuck_workers: 0\n"
            f"  stuck_workers_history: []\n"
            f"```\n"
        )
        content += lifecycle_block
    else:
        # Bestehenden Block aktualisieren — team_history erweitern
        import re
        history_match = re.search(r"(  team_history:\n)((?:  - \{[^\n]+\}\n)*)", content)
        if history_match:
            new_history = history_match.group(1) + history_match.group(2) + transition_entry + "\n"
            content = content[:history_match.start()] + new_history + content[history_match.end():]
        else:
            content += f"\n{transition_entry}\n"

    try:
        manifest.write_text(content, encoding="utf-8")
    except OSError as exc:
        print(f"[ERROR] Manifest-Write fehlgeschlagen: {exc}", file=sys.stderr)
        return False

    audit_team_lifecycle(
        "TEAM_TRANSITION",
        tool="TeamLifecycle",
        target=manifest_path,
        reason=f"TEAM_TRANSITION: {from_stage} -> {to_stage}",
        inputs={"from_stage": from_stage, "to_stage": to_stage, "manifest": manifest_path},
    )
    print(f"[TEAM_LIFECYCLE] Transition {from_stage} -> {to_stage} in Manifest registriert.")
    return True


def _cmd_cleanup(args: argparse.Namespace) -> int:
    return cleanup_team(args.team_name, shutdown_timeout_sec=args.timeout)


def _cmd_status(args: argparse.Namespace) -> int:
    config = _read_team_config(args.team_name)
    if config is None:
        print(f"Team '{args.team_name}': nicht gefunden")
        return EXIT_FATAL
    workers = config.get("workers", [])
    stuck = get_stuck_workers(args.team_name)
    print(f"Team '{args.team_name}':")
    print(f"  Workers gesamt: {len(workers)}")
    print(f"  Stuck Workers:  {len(stuck)} {stuck}")
    for w in workers:
        name = w.get("name", w.get("id", "unknown"))
        ack = w.get("ack_shutdown", False)
        flag = "[STUCK]" if name in stuck else ("[ACK]" if ack else "[pending]")
        print(f"    - {name} {flag}")
    return EXIT_CLEAN


def _cmd_history(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest_path)
    if not manifest.exists():
        print(f"Manifest nicht gefunden: {args.manifest_path}", file=sys.stderr)
        return EXIT_FATAL
    content = manifest.read_text(encoding="utf-8")
    import re
    block_match = re.search(r"## TEAM_LIFECYCLE\n\n```yaml\n(.*?)```", content, re.DOTALL)
    if not block_match:
        print("Kein TEAM_LIFECYCLE-Block im Manifest gefunden.")
        return EXIT_CLEAN
    print("=== TEAM_LIFECYCLE ===")
    print(block_match.group(1).strip())
    return EXIT_CLEAN


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="team_lifecycle_helper",
        description="BL-164 Team-Lifecycle-Helper — Verwaltet Team-Shutdown und Stage-Transitionen.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # cleanup <team_name> [--timeout N]
    p_cleanup = subparsers.add_parser("cleanup", help="Team sauber aufloesen (mit Timeout + Force-Skip)")
    p_cleanup.add_argument("team_name", help="Name des Teams (z.B. 'a-DCSRE-486')")
    p_cleanup.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_SHUTDOWN_TIMEOUT_SEC,
        help=f"Shutdown-Timeout in Sekunden (Default: {DEFAULT_SHUTDOWN_TIMEOUT_SEC})",
    )

    # status <team_name>
    p_status = subparsers.add_parser("status", help="Aktuellen Status eines Teams anzeigen")
    p_status.add_argument("team_name", help="Name des Teams")

    # history <manifest_path>
    p_history = subparsers.add_parser("history", help="TEAM_LIFECYCLE-History aus Manifest lesen")
    p_history.add_argument("manifest_path", help="Pfad zum _manifest.md")

    args = parser.parse_args()

    dispatch = {
        "cleanup": _cmd_cleanup,
        "status": _cmd_status,
        "history": _cmd_history,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
