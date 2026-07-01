#!/usr/bin/env python3
"""
Dynamic Context-Notify für Claude Code Stop/Notification Hooks.

Liest Git-Branch + Manifest-State und baut eine kompakte Notify-Nachricht.
Wird aus settings.json hooks aufgerufen — sei kreativ aber kompakt.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root (one above .claude)
MANIFEST = ROOT / ".claude" / "analysis" / "_manifest.md"


def short_branch():
    try:
        b = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
        # Trim feature/ prefix if present
        b = re.sub(r"^(feature|bugfix|hotfix)/", "", b)
        # Stripping suffixes like _Analyse
        return b[:30]
    except Exception:
        return "?"


def short_hash():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "?"


def manifest_state():
    """Liest aktuellen Pipeline-State aus dem Manifest. Format: PHASE/PHASE_DETAIL."""
    try:
        if not MANIFEST.exists():
            return "no-manifest"
        text = MANIFEST.read_text(encoding="utf-8", errors="ignore")

        # Active team
        active = re.search(r"^active_team:\s*\n\s*name:\s*(\S+)", text, re.M)
        active_team = active.group(1) if active else None

        # I/SDF/IDF/TDD pipeline state — nimm den lautesten "RUNNING" State
        for pattern, label in [
            (r"phase:\s*(\S+).*\n.*current_stage:\s*(\d+)", "I"),
            (r"sdf_status:\s*([A-Z_]+)", "SDF"),
            (r"idf_status:\s*([A-Z_]+)", "IDF"),
            (r"tdd_pipeline_mode:\s*([A-Z_]+)", "TDD"),
        ]:
            m = re.search(pattern, text)
            if m:
                if label == "I" and m.lastindex == 2:
                    return f"{label}:{m.group(1)}/S{m.group(2)}"
                return f"{label}:{m.group(1)}"

        # Fallback PHASE
        m = re.search(r"\*\*PHASE:\*\*\s*(\S+)", text)
        if m:
            return m.group(1)
        return "idle"
    except Exception:
        return "?"


def batch_items_short():
    """Aktuelle batch_items kompakt."""
    try:
        text = MANIFEST.read_text(encoding="utf-8", errors="ignore")
        # erste batch_items unter I_PIPELINE_STATE oder DF_BATCH_STATE
        m = re.search(r"\*\*batch_items:\*\*\s*\[([^\]]+)\]", text)
        if m:
            items = [x.strip() for x in m.group(1).split(",")]
            # Stripping prefix wie BL-125-PL-05 → PL-05
            items_short = [re.sub(r"^.*?-(PL-\d+|AK-\d+).*$", r"\1", x) for x in items]
            if len(items_short) <= 3:
                return "[" + " ".join(items_short) + "]"
            return f"[{items_short[0]}..{items_short[-1]} +{len(items_short)-2}]"
    except Exception:
        pass
    return ""


def main():
    branch = short_branch()[:20]
    state = manifest_state()
    msg = f"[{branch}] {state}"

    # Notify via PowerShell
    try:
        subprocess.run(
            ["powershell", "-Command", f"notify '{msg}'"],
            timeout=5, stderr=subprocess.DEVNULL
        )
    except Exception:
        # Fallback: print to stderr (zumindest sichtbar in hook-debug)
        print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
