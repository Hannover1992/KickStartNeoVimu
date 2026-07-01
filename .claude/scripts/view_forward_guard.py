#!/usr/bin/env python3
"""
view_forward_guard.py — BL-480 View Forward-Garantie enforcer.

CHEAP write-path check: does a view have `source_atoms` + is it re-derivable
by view_projector. Fail-open.

Exposes:
    forward_status(view_path, vault_root) -> dict
    enforce(view_path, vault_root, *, mode="warn", atom_index=None, report_path=None) -> dict
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import view_node_predicate
import view_projector
import view_forward_reference   # call as view_forward_reference.forward_reference_view(...) so monkeypatch works


# ---------------------------------------------------------------------------
# forward_status
# ---------------------------------------------------------------------------

_SOURCE_ATOMS_LIST_RE = re.compile(
    r"(?m)^source_atoms:\s*$\n(?:\s*-\s+\S)",
)
_SOURCE_ATOMS_INLINE_RE = re.compile(
    r"(?m)^source_atoms:\s*\[.+\]",
)


def _has_source_atoms_in_frontmatter(text: str) -> bool:
    """Return True if the YAML frontmatter contains a non-empty source_atoms key."""
    # Extract frontmatter between first two ---
    parts = text.split("---", 2)
    if len(parts) < 3:
        # Try with only one closing ---
        if len(parts) == 2:
            frontmatter = parts[1]
        else:
            return False
    else:
        frontmatter = parts[1]

    # Check for list form: source_atoms:\n  - item
    if _SOURCE_ATOMS_LIST_RE.search(frontmatter):
        return True

    # Check for inline form: source_atoms: [item, ...]
    if _SOURCE_ATOMS_INLINE_RE.search(frontmatter):
        return True

    return False


def forward_status(view_path, vault_root) -> dict:
    """Return a status dict for a single view file.

    Keys: is_view, has_source_atoms, projector_derivable, status, reason.
    Fail-open: never raises.
    """
    try:
        is_view = view_node_predicate.is_view_node(str(view_path), str(vault_root))

        if not is_view:
            return {
                "is_view": False,
                "has_source_atoms": False,
                "projector_derivable": False,
                "status": "skip",
                "reason": "not a view node",
            }

        # --- has_source_atoms ---
        has_source_atoms = False
        try:
            raw = Path(view_path).read_bytes()
            if b"\x00" in raw:
                # null-byte-corrupt
                has_source_atoms = False
            else:
                text = raw.decode("utf-8", errors="replace")
                has_source_atoms = _has_source_atoms_in_frontmatter(text)
        except Exception:
            has_source_atoms = False

        # --- projector_derivable ---
        projector_derivable = False
        try:
            idy = view_projector.parse_view_identity(str(view_path), str(vault_root))
            if idy["bl"]:
                sub = view_projector.gather_substrate(idy["bl"], str(vault_root))
                projector_derivable = bool(sub["has_substrate"])
        except Exception:
            projector_derivable = False

        # --- status ---
        if not projector_derivable:
            status = "fragile"
            reason = "no derivable substrate — cannot be re-projected if lost"
        elif has_source_atoms:
            status = "ok"
            reason = "view has source_atoms and substrate is derivable"
        else:
            status = "needs_ref"
            reason = "substrate derivable but source_atoms reference missing"

        return {
            "is_view": True,
            "has_source_atoms": has_source_atoms,
            "projector_derivable": projector_derivable,
            "status": status,
            "reason": reason,
        }

    except Exception as exc:
        # fail-open
        try:
            is_view = view_node_predicate.is_view_node(str(view_path), str(vault_root))
        except Exception:
            is_view = False
        return {
            "is_view": is_view,
            "has_source_atoms": False,
            "projector_derivable": False,
            "status": "skip",
            "reason": f"error during forward_status: {exc}",
        }


# ---------------------------------------------------------------------------
# enforce
# ---------------------------------------------------------------------------

def enforce(view_path, vault_root, *, mode="warn", atom_index=None, report_path=None) -> dict:
    """Enforce forward-reference policy for a single view.

    Args:
        view_path:    Path to the view file.
        vault_root:   Vault root directory.
        mode:         "warn" (never writes) or "fix" (attempts to add source_atoms).
        atom_index:   Optional pre-built atom index for mode="fix".
        report_path:  Optional report path forwarded to forward_reference_view.

    Returns dict with keys: action, status, message.
    Fail-open: never raises.
    """
    try:
        st = forward_status(view_path, vault_root)
        status = st["status"]
        reason = st.get("reason", "")

        if mode == "warn":
            if status in {"needs_ref", "fragile"}:
                message = (
                    f"[FORWARD-GARANTIE] {view_path}: {status} — {reason}"
                )
                return {"action": "warn", "status": status, "message": message}
            else:
                return {"action": "noop", "status": status, "message": ""}

        elif mode == "fix":
            if status == "needs_ref":
                try:
                    r = view_forward_reference.forward_reference_view(
                        str(view_path),
                        str(vault_root),
                        atom_index=(atom_index or {}),
                        write=True,
                        gate_mode="target",
                        report_path=report_path,
                    )
                    if r.get("action") == "written":
                        action = "fixed"
                        message = f"[FORWARD-GARANTIE] {view_path}: source_atoms written"
                    else:
                        action = r.get("action", "attempted")
                        message = f"[FORWARD-GARANTIE] {view_path}: forward_reference_view returned action={action}"
                    return {"action": action, "status": status, "message": message}
                except Exception as exc:
                    return {
                        "action": "error",
                        "status": status,
                        "message": str(exc),
                    }

            elif status == "fragile":
                message = (
                    f"[FORWARD-GARANTIE] {view_path}: FRAGILE — "
                    "no substrate to derive from — never fabricate; "
                    "needs re-atomization (Lane-C) first"
                )
                return {"action": "cannot_fix", "status": status, "message": message}

            else:
                # "ok" or "skip"
                return {"action": "noop", "status": status, "message": ""}

        else:
            return {
                "action": "error",
                "status": "skip",
                "message": f"unknown mode: {mode!r}",
            }

    except Exception as exc:
        return {
            "action": "error",
            "status": "skip",
            "message": str(exc),
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="BL-480 view_forward_guard — check/enforce forward-reference on a view."
    )
    parser.add_argument("view_path", help="Path to the view .md file")
    parser.add_argument("vault_root", help="Vault root directory")
    parser.add_argument(
        "--mode",
        choices=["warn", "fix"],
        default="warn",
        help="warn (default, never writes) or fix (attempts to add source_atoms)",
    )
    args = parser.parse_args(argv)

    result = enforce(args.view_path, args.vault_root, mode=args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
