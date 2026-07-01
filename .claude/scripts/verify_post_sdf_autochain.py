#!/usr/bin/env python3
"""
BL-173 AK-5 — verify_post_sdf_autochain.py

Self-check script: prueft ob _SDF_orchestrate_post korrekt im audit-Trail
erscheint (Anti-Mega-Worker-Forensik).

USAGE: python verify_post_sdf_autochain.py [--audit=<path>]
DEFAULT: --audit=.claude/audit/audit.jsonl

EXIT CODES:
  0  alle AKs PASS (SKIP zaehlt nicht als FAIL)
  1  >=1 AK FAIL
  2  Audit-File nicht lesbar / kein einziger SKILL_LOAD-Event
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_events(audit_path: Path):
    """Load all JSON events from audit.jsonl. Returns (events, warnings)."""
    events = []
    warnings = []
    try:
        with open(audit_path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    events.append(obj)
                except json.JSONDecodeError as e:
                    warnings.append(f"Line {lineno}: invalid JSON ({e})")
    except OSError as e:
        return None, [f"Cannot open audit file: {e}"]
    return events, warnings


def skill_name_of(event: dict) -> str:
    """Return the canonical skill name for SKILL_LOAD or HANDOFF events."""
    ev = event.get("event", "")
    if ev == "SKILL_LOAD":
        return event.get("skill_name", "")
    if ev == "HANDOFF":
        return event.get("skill", "")
    return ""


def is_sdf_berater_event(event: dict) -> bool:
    """True if the event is a HANDOFF or SKILL_LOAD for any _SDF_berater_* skill."""
    ev = event.get("event", "")
    name = skill_name_of(event)
    return ev in ("HANDOFF", "SKILL_LOAD") and name.startswith("_SDF_berater_")


def parse_ts(ts_str: str) -> datetime | None:
    """Parse ISO 8601 timestamp robustly."""
    if not ts_str:
        return None
    try:
        # Python 3.7+ fromisoformat handles YYYY-MM-DDTHH:MM:SS
        return datetime.fromisoformat(ts_str)
    except ValueError:
        return None


def first_ts(events_for_skill: list) -> datetime | None:
    """Return earliest timestamp from a list of events."""
    dts = [parse_ts(e.get("ts", "")) for e in events_for_skill]
    dts = [d for d in dts if d is not None]
    return min(dts) if dts else None


# ---------------------------------------------------------------------------
# AK checks
# ---------------------------------------------------------------------------

def check_ak1(events: list) -> tuple[str, str]:
    """AK-1: Post-SDF Skill-Load existiert."""
    matches = [
        e for e in events
        if e.get("event") == "SKILL_LOAD"
        and e.get("skill_name") == "_SDF_orchestrate_post"
    ]
    if matches:
        ts = matches[0].get("ts", "?")
        return "PASS", f"Found {len(matches)} SKILL_LOAD event(s); first ts={ts}"
    return "FAIL", "No SKILL_LOAD event with skill_name='_SDF_orchestrate_post' found"


def check_ak2(events: list) -> tuple[str, str]:
    """AK-2: recalibrate-Berater wurde gerufen."""
    target = "_SDF_berater_recalibrate"
    matches = [
        e for e in events
        if (e.get("event") == "HANDOFF" and e.get("skill") == target)
        or (e.get("event") == "SKILL_LOAD" and e.get("skill_name") == target)
    ]
    if matches:
        return "PASS", f"Found {len(matches)} event(s) for {target}"
    return "FAIL", f"No HANDOFF/SKILL_LOAD event for {target}"


def check_ak3(events: list) -> tuple[str, str]:
    """AK-3: R1→R2→R3 Sequenz (recalibrate < postItem < statusTransition)."""
    beraters = {
        "_SDF_berater_recalibrate": [],
        "_SDF_berater_postItem": [],
        "_SDF_berater_statusTransition": [],
    }
    for e in events:
        ev = e.get("event", "")
        name = skill_name_of(e)
        if ev in ("HANDOFF", "SKILL_LOAD") and name in beraters:
            beraters[name].append(e)

    missing = [b for b, evts in beraters.items() if not evts]
    if missing:
        return "FAIL", f"Missing events for: {missing}"

    ts_r = first_ts(beraters["_SDF_berater_recalibrate"])
    ts_p = first_ts(beraters["_SDF_berater_postItem"])
    ts_s = first_ts(beraters["_SDF_berater_statusTransition"])

    if ts_r < ts_p < ts_s:
        return (
            "PASS",
            f"Sequence OK: recalibrate={ts_r.isoformat()} "
            f"< postItem={ts_p.isoformat()} "
            f"< statusTransition={ts_s.isoformat()}"
        )
    return (
        "FAIL",
        f"Wrong order — recalibrate={ts_r.isoformat() if ts_r else '?'}, "
        f"postItem={ts_p.isoformat() if ts_p else '?'}, "
        f"statusTransition={ts_s.isoformat() if ts_s else '?'}"
    )


def check_ak4(events: list) -> tuple[str, str]:
    """AK-4: loopDecision Phase-4 Event."""
    target = "_SDF_berater_loopDecision"
    matches = [
        e for e in events
        if skill_name_of(e) == target
        and e.get("event") in ("HANDOFF", "SKILL_LOAD")
    ]
    if matches:
        return "PASS", f"Found {len(matches)} event(s) for {target}"
    return "FAIL", f"No HANDOFF/SKILL_LOAD event for {target}"


def check_ak5(_events: list) -> tuple[str, str]:
    """AK-5: Self-Existence. Trivial PASS."""
    return "PASS", f"Script exists at {os.path.abspath(__file__)}"


def check_ak6(events: list) -> tuple[str, str]:
    """AK-6: Anti-Mega-Worker — Distinct-Berater-Count + ts_spread."""
    relevant = [e for e in events if is_sdf_berater_event(e)]

    if not relevant:
        return "FAIL", "No _SDF_berater_* events found (distinct_count=0, ts_spread=N/A)"

    distinct_names = set(skill_name_of(e) for e in relevant)
    distinct_count = len(distinct_names)

    timestamps = [parse_ts(e.get("ts", "")) for e in relevant]
    timestamps = [t for t in timestamps if t is not None]

    if len(timestamps) >= 2:
        ts_spread = (max(timestamps) - min(timestamps)).total_seconds()
    else:
        ts_spread = 0.0

    rationale = (
        f"distinct_count={distinct_count}, ts_spread={ts_spread:.1f}s, "
        f"distinct={sorted(distinct_names)}"
    )

    if distinct_count >= 3 and ts_spread >= 5.0:
        return "PASS", rationale
    return "FAIL", rationale


def check_ak7(_events: list) -> tuple[str, str]:
    """AK-7: PL-Item-Derivation-Linter."""
    script_dir = Path(__file__).parent
    linter_path = script_dir / "lint_pl_item_derivation.py"

    if not linter_path.exists():
        return "SKIP", "Linter not implemented (BL-174 pending)"

    python_exe = sys.executable
    result = subprocess.run(
        [python_exe, str(linter_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return "PASS", f"Linter returned 0 (OK)"

    stderr_snip = result.stderr.strip()[:300] if result.stderr else "(no stderr)"
    return "FAIL", f"Linter returned {result.returncode}: {stderr_snip}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="BL-173 AK-5: verify _SDF_orchestrate_post autochain in audit trail"
    )
    parser.add_argument(
        "--audit",
        default=".claude/audit/audit.jsonl",
        help="Path to audit.jsonl (default: .claude/audit/audit.jsonl)",
    )
    args = parser.parse_args()

    audit_path = Path(args.audit)
    if not audit_path.is_absolute():
        audit_path = Path.cwd() / audit_path

    events, warnings = load_events(audit_path)

    # Print parse warnings to stderr
    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    if events is None:
        print(f"ERROR: Could not read audit file: {audit_path}", file=sys.stderr)
        sys.exit(2)

    skill_load_events = [e for e in events if e.get("event") == "SKILL_LOAD"]
    if not skill_load_events:
        print("ERROR: Audit file contains no SKILL_LOAD events", file=sys.stderr)
        sys.exit(2)

    # Run all AK checks
    checks = [
        ("AK-1", check_ak1),
        ("AK-2", check_ak2),
        ("AK-3", check_ak3),
        ("AK-4", check_ak4),
        ("AK-5", check_ak5),
        ("AK-6", check_ak6),
        ("AK-7", check_ak7),
    ]

    results = []
    for ak_id, fn in checks:
        status, rationale = fn(events)
        results.append((ak_id, status, rationale))
        print(f"[{ak_id}] {status} — {rationale}")

    # Summary
    pass_count = sum(1 for _, s, _ in results if s == "PASS")
    fail_count = sum(1 for _, s, _ in results if s == "FAIL")
    skip_count = sum(1 for _, s, _ in results if s == "SKIP")
    print(f"\nSUMMARY: {pass_count} PASS, {fail_count} FAIL, {skip_count} SKIP")

    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
