#!/usr/bin/env python3
"""
hook_view_forward_reference.py — P2 PostToolUse Write/Edit hook (BL-460 Lane-B).

O(1) per write: this hook ENQUEUES view-node writes to {vault}/_forward_ref_pending.md.
The heavy forward-referencing (score_view + materialize, gated on BL-443) is done in
BATCH by the P1 swarm / a sweep draining the queue.
(The _model finish Phase 1.6 keeps the direct heavy trigger for finished Models.)

Fires on every Write/Edit tool call.  If the target file is a view node
(Model .md, arc42 .md, Parking-Lot .md, Docs .md) the hook calls
_enqueue_pending(path, vault_root) ONLY — cheap and idempotent.

Patterns (from scope_guard.py DT-4/DT-5):
    DT-4: stdin-JSON hook mode
    DT-5: exit 0 ALWAYS (fail-open — a forward-ref hook must never break a write)

Exposed API (tested by test_hook_view_forward_reference.py):
    is_view_node(path, vault_root) -> bool
    forward_reference_new_view   — imported from view_forward_reference (patchable, NOT called by handle_write_event)
    handle_write_event(hook_data, vault_root=None) -> dict
    _enqueue_pending(view_path, vault_root)
    main()
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# ---------------------------------------------------------------------------
# Import from view_forward_reference — bound at module level so tests can
# monkeypatch hvfr.forward_reference_new_view directly.
# ---------------------------------------------------------------------------
from view_forward_reference import forward_reference_new_view  # noqa: E402


# ---------------------------------------------------------------------------
# is_view_node — re-exported from the canonical SSoT module
# ---------------------------------------------------------------------------
# The predicate now lives in view_node_predicate.py (shared by swarm P1 + hook P2).
# We re-export it here so that existing callers (handle_write_event, tests that do
# `hvfr.is_view_node` or monkeypatch `hook_view_forward_reference.is_view_node`)
# continue to work unchanged.
from view_node_predicate import is_view_node  # noqa: F401, E402


# ---------------------------------------------------------------------------
# _enqueue_pending
# ---------------------------------------------------------------------------

def _enqueue_pending(view_path: str, vault_root: str) -> None:
    """Append view_path to {vault_root}/_forward_ref_pending.md idempotently."""
    try:
        queue_file = Path(vault_root) / "_forward_ref_pending.md"
        # Read existing lines
        existing: set[str] = set()
        if queue_file.exists():
            content = queue_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                stripped = line.strip()
                if stripped:
                    existing.add(stripped)

        # Idempotent: only add if not already present
        if view_path not in existing:
            with queue_file.open("a", encoding="utf-8") as fh:
                fh.write(view_path + "\n")
    except Exception:
        pass  # fail-open — pending enqueue must not raise


# ---------------------------------------------------------------------------
# handle_write_event
# ---------------------------------------------------------------------------

def handle_write_event(hook_data, vault_root: str | None = None) -> dict:
    """Process a Write/Edit hook event.

    On Write/Edit to a view-node: calls _enqueue_pending(path, vault_root) ONLY (O(1),
    idempotent). Returns {"continue": True, "action": "enqueued", "view": path}.
    forward_reference_new_view is NOT called.

    Non-view / non-Write-Edit: returns {"continue": True, "action": "skip"}.

    Fail-open: any exception (incl. _enqueue_pending failing) ->
    {"continue": True, "action": "error", "reason": str(e)}; NEVER continue:False.
    """
    try:
        if not isinstance(hook_data, dict):
            return {"continue": True, "action": "skip"}

        tool_name = hook_data.get("tool_name", "")
        if tool_name not in ("Write", "Edit"):
            return {"continue": True, "action": "skip"}

        tool_input = hook_data.get("tool_input")
        if not isinstance(tool_input, dict):
            return {"continue": True, "action": "skip"}

        file_path = tool_input.get("file_path")
        if not file_path:
            return {"continue": True, "action": "skip"}

        # Resolve vault_root if not supplied
        effective_vault = vault_root
        if effective_vault is None:
            effective_vault = hook_data.get("vault_root")
        if effective_vault is None:
            try:
                from resolve_vault_root import resolve_vault_root as _resolve
                effective_vault = _resolve()
            except Exception:
                pass
        if effective_vault is None:
            effective_vault = os.environ.get("VAULT_ROOT", "")

        if not is_view_node(file_path, effective_vault or ""):
            return {"continue": True, "action": "skip"}

        # It's a view node — enqueue ONLY (cheap, O(1)); no heavy forward-ref call
        _enqueue_pending(file_path, effective_vault or "")
        result = {"continue": True, "action": "enqueued", "view": file_path}

        # Compute forward-garantie status cheaply + fail-open
        try:
            import view_forward_guard
            st = view_forward_guard.forward_status(file_path, effective_vault or "")
            result["forward_status"] = st.get("status")
            if st.get("status") in ("needs_ref", "fragile"):
                result["forward_warning"] = f"[FORWARD-GARANTIE] {file_path}: {st.get('status')} — {st.get('reason', '')}"
        except Exception:
            pass  # fail-open — never block a write over the forward-garantie check

        return result

    except Exception as exc:
        return {"continue": True, "action": "error", "reason": str(exc)}


# ---------------------------------------------------------------------------
# main — CLI hook entry point (DT-4 stdin-JSON, DT-5 exit 0 always)
# ---------------------------------------------------------------------------

def main() -> None:
    """Read stdin-JSON, call handle_write_event, print JSON result, exit 0."""
    hook_data = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            hook_data = json.loads(raw)
    except Exception:
        hook_data = {}

    try:
        result = handle_write_event(hook_data)
    except Exception as exc:
        result = {"continue": True, "action": "error", "reason": str(exc)}

    # Ensure continue is always True in output
    result["continue"] = True

    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
