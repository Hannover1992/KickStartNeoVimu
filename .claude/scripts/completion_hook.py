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

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

def _lock_shared(f):
    if _HAS_FCNTL:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)

def _lock_exclusive(f):
    if _HAS_FCNTL:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

def _unlock(f):
    if _HAS_FCNTL:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

# Root-Ordner bestimmen (wo .claude/ liegt)
SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent  # .claude/scripts -> .claude -> root
STATE_FILE = ROOT_DIR / ".pipeline_state.json"
LOG_FILE = ROOT_DIR / ".hook_debug.log"

def atomic_write_state(status):
    """Atomisches Schreiben des Status mit File Locking"""

    # Lese aktuellen State (oder erstelle neuen)
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            _lock_shared(f)
            try:
                state = json.load(f)
            finally:
                _unlock(f)
    else:
        state = {"status": "idle", "current_phase": 0}

    # Update Status
    state["status"] = status
    state["timestamp"] = datetime.now().isoformat()

    # Atomisches Schreiben mit File Lock
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        _lock_exclusive(f)
        try:
            json.dump(state, f, indent=2)
            f.flush()
        finally:
            _unlock(f)

def main():
    try:
        # Lese Hook Input
        hook_data = json.loads(sys.stdin.read())

        # Nur auf "Stop" Event reagieren
        if hook_data.get("hook_event_name") == "Stop":
            # ATOMISCH: Setze "completed" Flag
            atomic_write_state("completed")

            # Log für Debugging
            with open(LOG_FILE, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] ✅ Completion flag set (Root: {ROOT_DIR})\n")

        # Erfolg zurückmelden
        print(json.dumps({"continue": True}))

    except Exception as e:
        # Fehler loggen aber Hook nicht blockieren
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"[{datetime.now()}] ❌ Error: {e}\n")
        print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
