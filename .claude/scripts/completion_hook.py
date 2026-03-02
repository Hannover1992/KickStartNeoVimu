#!/usr/bin/env python3
"""
Claude Code Hook - Atomic Completion Flag Setter
Setzt am Ende jeder Phase ATOMISCH den "completed" Flag
Arbeitet mit Root-Ordner (wo .claude/ liegt) für State-Files
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import fcntl

# Root-Ordner bestimmen (wo .claude/ liegt)
SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent  # .claude/scripts -> .claude -> root
STATE_FILE = ROOT_DIR / ".pipeline_state.json"
LOG_FILE = ROOT_DIR / ".hook_debug.log"

def atomic_write_state(status):
    """Atomisches Schreiben des Status mit File Locking"""

    # Lese aktuellen State (oder erstelle neuen)
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            # File Lock für atomaren Read
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                state = json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    else:
        state = {"status": "idle", "current_phase": 0}

    # Update Status
    state["status"] = status
    state["timestamp"] = datetime.now().isoformat()

    # Atomisches Schreiben mit File Lock
    with open(STATE_FILE, 'w') as f:
        # Exclusive Lock während Schreibvorgang
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(state, f, indent=2)
            f.flush()  # Force write to disk
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def main():
    try:
        # Lese Hook Input
        hook_data = json.loads(sys.stdin.read())

        # Nur auf "Stop" Event reagieren
        if hook_data.get("hook_event_name") == "Stop":
            # ATOMISCH: Setze "completed" Flag
            atomic_write_state("completed")

            # Log für Debugging
            with open(LOG_FILE, "a") as log:
                log.write(f"[{datetime.now()}] ✅ Completion flag set (Root: {ROOT_DIR})\n")

        # Erfolg zurückmelden
        print(json.dumps({"continue": True}))

    except Exception as e:
        # Fehler loggen aber Hook nicht blockieren
        with open(LOG_FILE, "a") as log:
            log.write(f"[{datetime.now()}] ❌ Error: {e}\n")
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
