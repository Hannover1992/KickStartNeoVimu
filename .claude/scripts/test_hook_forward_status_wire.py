"""
test_hook_forward_status_wire.py — RED-phase tests for BL-480 forward-garantie wire
into hook_view_forward_reference.handle_write_event.

RED contract:
  test_hook_reports_forward_status_needs_ref  → MUST FAIL (hook doesn't emit
      forward_status / forward_warning keys yet)

PASS-NOW contracts (regression guards):
  test_hook_nonview_no_forward_status  → enqueue skipped for non-view, no forward_warning
  test_hook_still_enqueues             → existing enqueue behavior preserved after green wire

Vault layout (BL-300-x):
  Backlog/BL-300-x/2_Model/BL-300-x_Model.md   <- view node (type:model, NO source_atoms)
  Backlog/BL-300-x/2_Model/truths/W1.md          <- truth-atom  => gather_substrate.has_substrate=True
                                                     => forward_status returns "needs_ref"
  Backlog/BL-300-x/_manifest.md                   <- non-view (_manifest.md exclusion)
"""
from __future__ import annotations

import os
import sys

import pytest

# Make scripts/ importable when running from repo root or this directory.
sys.path.insert(0, os.path.dirname(__file__))

from hook_view_forward_reference import handle_write_event  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_vault(tmp_path):
    """Build a minimal synthetic vault under tmp_path/Vault."""
    vault = tmp_path / "Vault"

    # View node: BL-300-x Model WITHOUT source_atoms
    _write(
        vault / "Backlog" / "BL-300-x" / "2_Model" / "BL-300-x_Model.md",
        "---\ntype: model\n---\n\n# Model BL-300-x\n",
    )

    # Truth-atom: makes gather_substrate.has_substrate True -> projector_derivable=True
    # Together with no source_atoms -> forward_status = "needs_ref"
    _write(
        vault / "Backlog" / "BL-300-x" / "2_Model" / "truths" / "W1.md",
        "# W1\nAtomic truth for BL-300-x.\n",
    )

    # Non-view: _manifest.md (excluded by is_view_node)
    _write(
        vault / "Backlog" / "BL-300-x" / "_manifest.md",
        "---\ntype: manifest\n---\n",
    )

    return vault


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def vault(tmp_path):
    return _build_vault(tmp_path)


@pytest.fixture()
def bl300_model(vault):
    return str(vault / "Backlog" / "BL-300-x" / "2_Model" / "BL-300-x_Model.md")


@pytest.fixture()
def bl300_manifest(vault):
    return str(vault / "Backlog" / "BL-300-x" / "_manifest.md")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHookForwardStatusWire:

    def test_hook_reports_forward_status_needs_ref(self, vault, bl300_model):
        """
        RED TEST — MUST FAIL against current code.

        When handle_write_event is called with a view-node path that has no
        source_atoms but does have a derivable substrate (truth-atom W1.md),
        the returned dict MUST include:
          - result["continue"] is True         (always-true invariant)
          - result["action"] == "enqueued"     (existing enqueue contract)
          - result["forward_status"] == "needs_ref"   <- NEW key (RED)
          - result["forward_warning"] is a non-empty string              <- NEW key (RED)

        Current hook does NOT emit forward_status / forward_warning.
        These assertions fail until GREEN phase wires view_forward_guard.forward_status.
        """
        hook_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": bl300_model},
        }

        result = handle_write_event(hook_data, vault_root=str(vault))

        # Always-true invariant (must never break)
        assert result["continue"] is True

        # Existing contract (must still hold after green wire)
        assert result["action"] == "enqueued"

        # NEW keys — these are the RED assertions that will fail on current code
        assert result.get("forward_status") == "needs_ref", (
            "forward_status key missing or wrong — hook does not yet call "
            "view_forward_guard.forward_status()"
        )
        fwd_warn = result.get("forward_warning")
        assert fwd_warn and len(fwd_warn) > 0, (
            "forward_warning key missing or empty — hook must emit a LOUD warning "
            "string when forward_status in {'needs_ref','fragile'}"
        )

    def test_hook_nonview_no_forward_status(self, vault, bl300_manifest):
        """
        Non-view path (_manifest.md) -> action=="skip", no forward_warning.

        This reflects CURRENT behavior and should PASS now (regression guard).
        After green wire it must still pass: non-views must not incur forward_status overhead.
        """
        hook_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": bl300_manifest},
        }

        result = handle_write_event(hook_data, vault_root=str(vault))

        assert result["continue"] is True
        assert result["action"] == "skip"

        # forward_warning must NOT be present (or forward_status must be absent / "skip")
        assert "forward_warning" not in result, (
            "Non-view writes must not produce a forward_warning"
        )
        fs = result.get("forward_status")
        assert fs is None or fs == "skip", (
            f"Non-view forward_status must be absent or 'skip', got {fs!r}"
        )

    def test_hook_still_enqueues(self, vault, bl300_model):
        """
        Regression: the existing enqueue behavior (writing view path to
        _forward_ref_pending.md) must be preserved after the green wire.

        This should PASS now (enqueue contract already exists) and must
        continue to pass after the forward_status wire is added.
        """
        hook_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": bl300_model},
        }

        handle_write_event(hook_data, vault_root=str(vault))

        pending_file = vault / "_forward_ref_pending.md"
        assert pending_file.exists(), "_forward_ref_pending.md was not created"

        content = pending_file.read_text(encoding="utf-8")
        assert bl300_model in content, (
            f"View path not found in pending queue.\n"
            f"  expected: {bl300_model!r}\n"
            f"  file content: {content!r}"
        )
