"""
view_forward_reference.py — P2 Forward-Garantie (BL-460 Lane-B)

This is the unit a write-time hook calls so new views auto-reference their atoms.
Execution is write-gated (BL-443) until vault healed.

Exposes:
    forward_reference_view(view_path, vault_root, *, atom_index, conf_threshold=0.70,
                           write=False, report_path=None) -> dict
    forward_reference_new_view(view_path, vault_root, write=False) -> dict  (real-path helper)

DT-5 exit codes:
    0  = success (dry-run or written)
    2  = deferred-gated (write gated)
    1  = unexpected error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import referenz_ableiter
import wikilink_materializer
import write_gate_guard

# Module-level patchable names — tests patch these via patch.object on this module
score_view = referenz_ableiter.score_view
build_atom_index_from_vault = referenz_ableiter.build_atom_index_from_vault
is_write_gated = write_gate_guard.is_write_gated
write_source_atoms = wikilink_materializer.write_source_atoms


def forward_reference_view(
    view_path: str,
    vault_root: str,
    *,
    atom_index,
    conf_threshold: float = 0.70,
    write: bool = False,
    report_path=None,
    gate_mode: str = "vault",
) -> dict:
    """Compute or execute forward-reference for a single view.

    Args:
        view_path:       Absolute path to the view .md file.
        vault_root:      Vault root directory.
        atom_index:      Pre-built inverted index {keyword: [entries]}.
                         None or {} -> no scoring -> n_proposed=0.
        conf_threshold:  Confidence threshold passed to score_view (default 0.70).
        write:           False -> dry-run only; True -> attempt write (gate-checked).
        report_path:     Optional path to prior dry-run JSON report for write_source_atoms.

    Returns:
        dict with keys: view, proposed_atoms, n_proposed, action, reason
    """
    # Normalize atom_index: None -> {} (score_view handles {} -> [])
    effective_index = atom_index if atom_index is not None else {}

    # Score view — returns [] on empty index or unreadable view
    raw_scores = score_view(
        view_path,
        vault_root,
        atom_index=effective_index,
        conf_threshold=conf_threshold,
    )

    # AK-CTX-2 hairball-prevention: only sub_threshold==False (above threshold)
    proposed_atoms = [
        entry["atom_id"]
        for entry in raw_scores
        if not entry.get("sub_threshold", True)
    ]

    base = {
        "view": str(view_path),
        "proposed_atoms": proposed_atoms,
        "n_proposed": len(proposed_atoms),
    }

    # --- dry-run path ---
    if not write:
        return {
            **base,
            "action": "dry-run",
            "reason": f"{len(proposed_atoms)} atoms proposed; no write (dry-run mode)",
        }

    # --- write path: check gate first ---
    if gate_mode == "target":
        # Per-target mode: check TARGET file for null bytes instead of vault-wide gate
        try:
            if Path(view_path).exists() and Path(view_path).read_bytes().count(0) > 0:
                return {**base, "action": "deferred-gated", "reason": f"target corrupt (null bytes): {view_path}"}
        except Exception:
            pass
    else:
        # Default vault mode: vault-wide write gate
        gated, gate_reason = is_write_gated(vault_root)
        if gated:
            return {
                **base,
                "action": "deferred-gated",
                "reason": gate_reason,
            }

    # --- write path: vault clean -> delegate to write_source_atoms ---
    changed, wsa_reason = write_source_atoms(
        Path(view_path),
        proposed_atoms,
        Path(vault_root),
        report_path=report_path,
        gate_mode=gate_mode,
    )

    if changed:
        reason = f"written {len(proposed_atoms)} atom refs to view"
    else:
        reason = f"idempotent — no change needed (already_present): {wsa_reason}"

    return {
        **base,
        "action": "written",
        "reason": reason,
    }


def forward_reference_new_view(
    view_path: str,
    vault_root: str,
    write: bool = False,
) -> dict:
    """Real-path helper: builds atom_index from vault then calls forward_reference_view.

    Use this from hooks/CLI when no pre-built index is available.
    Separate from the injected unit path so tests can patch independently.
    """
    atom_index = build_atom_index_from_vault(vault_root)
    return forward_reference_view(
        view_path,
        vault_root,
        atom_index=atom_index,
        write=write,
    )


# ---------------------------------------------------------------------------
# CLI (thin wrapper, default dry-run; --write is gate-checked)
# ---------------------------------------------------------------------------

def _cli(argv=None):
    parser = argparse.ArgumentParser(
        description="P2 Forward-Garantie: propose or write atom refs for a view (BL-460)"
    )
    parser.add_argument("view_path", help="Absolute path to the view .md file")
    parser.add_argument("vault_root", help="Vault root directory")
    parser.add_argument(
        "--write",
        action="store_true",
        default=False,
        help="Attempt to write (write-gated by BL-443 until vault healed)",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Optional path to prior dry-run JSON report",
    )
    args = parser.parse_args(argv)

    result = forward_reference_new_view(
        args.view_path,
        args.vault_root,
        write=args.write,
    )

    action = result.get("action", "unknown")
    print(f"action:         {action}")
    print(f"view:           {result.get('view')}")
    print(f"n_proposed:     {result.get('n_proposed')}")
    print(f"proposed_atoms: {result.get('proposed_atoms')}")
    print(f"reason:         {result.get('reason')}")

    # DT-5 exit codes
    if action == "deferred-gated":
        sys.exit(2)
    elif action in ("dry-run", "written"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    _cli()
