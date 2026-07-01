#!/usr/bin/env python3
"""
test_worktree_hook_router.py — Tests fuer worktree_hook_router.py (BL-172 AK-4).

Testet:
  - Namespace-scoped Hook-Filterung
  - Globale Hooks immer relevant
  - Single-Worktree-Fallback (alle Hooks relevant)
  - Payload-Namespace-Matching
  - Batch-Routing
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

from worktree_hook_router import (
    is_hook_relevant,
    route_hook,
    route_hooks_batch,
    route_hook_event,
    _NAMESPACE_SCOPED_HOOKS,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _mock_namespace(ns):
    """Patch get_worktree_namespace to return a fixed value."""
    return patch("worktree_hook_router._get_namespace", return_value=ns)


# ── Tests: Globale Hooks ───────────────────────────────────────────────────────

class TestGlobalHooks:
    def test_conflict_check_always_relevant(self):
        with _mock_namespace("feature_bdf-2026-05-14"):
            relevant, reason = is_hook_relevant("conflict_check")
        assert relevant is True
        assert "global" in reason.lower()

    def test_vault_health_always_relevant(self):
        with _mock_namespace("some_worktree"):
            relevant, reason = is_hook_relevant("vault_health")
        assert relevant is True

    def test_global_hook_relevant_even_with_foreign_payload(self):
        with _mock_namespace("wt_a"):
            relevant, _ = is_hook_relevant(
                "conflict_check",
                payload={"worktree_id": "wt_b"}
            )
        assert relevant is True


# ── Tests: Single-Worktree-Modus ──────────────────────────────────────────────

class TestSingleWorktreeMode:
    def test_all_scoped_hooks_relevant_in_single_mode(self):
        with _mock_namespace(None):
            relevant, reason = is_hook_relevant("session_params_write")
        assert relevant is True
        assert "single" in reason.lower()

    def test_audit_hook_relevant_in_single_mode(self):
        with _mock_namespace(None):
            relevant, _ = is_hook_relevant("audit_hook", {"namespace": "some_ns"})
        assert relevant is True


# ── Tests: Namespace-scoped Hooks ─────────────────────────────────────────────

class TestNamespaceScopedHooks:
    def test_matching_namespace_in_payload_is_relevant(self):
        with _mock_namespace("feature_bdf"):
            relevant, reason = is_hook_relevant(
                "session_params_write",
                payload={"worktree_id": "feature_bdf"},
            )
        assert relevant is True
        assert "ueberein" in reason.lower()

    def test_mismatching_namespace_is_skipped(self):
        with _mock_namespace("wt_a"):
            relevant, reason = is_hook_relevant(
                "session_params_write",
                payload={"worktree_id": "wt_b"},
            )
        assert relevant is False
        assert "mismatch" in reason.lower()

    def test_no_payload_namespace_means_relevant(self):
        with _mock_namespace("wt_a"):
            relevant, reason = is_hook_relevant(
                "session_params_write",
                payload={},
            )
        assert relevant is True
        assert "kein Payload" in reason

    def test_slash_namespace_normalized(self):
        """feature/bdf wird normalisiert zu feature_bdf."""
        with _mock_namespace("feature_bdf"):
            relevant, _ = is_hook_relevant(
                "param_change",
                payload={"worktree_id": "feature/bdf"},
            )
        assert relevant is True

    def test_unknown_hook_defaults_to_relevant(self):
        with _mock_namespace("wt_x"):
            relevant, reason = is_hook_relevant("totally_unknown_hook")
        assert relevant is True
        assert "unbekannter" in reason.lower()


# ── Tests: route_hook ─────────────────────────────────────────────────────────

class TestRouteHook:
    def test_route_hook_returns_dict_with_expected_keys(self):
        with _mock_namespace("wt_test"):
            result = route_hook("session_params_write", {})
        assert set(result.keys()) >= {"hook", "relevant", "reason", "namespace", "mode"}

    def test_route_hook_multi_mode_detected(self):
        with _mock_namespace("feature_bdf"):
            result = route_hook("session_params_write")
        assert result["mode"] == "multi"
        assert result["namespace"] == "feature_bdf"

    def test_route_hook_single_mode_detected(self):
        with _mock_namespace(None):
            result = route_hook("session_params_write")
        assert result["mode"] == "single"
        assert result["namespace"] is None


# ── Tests: Batch-Routing ──────────────────────────────────────────────────────

class TestBatchRouting:
    def test_batch_routing_mixed_relevance(self):
        hooks = [
            {"hook": "conflict_check"},
            {"hook": "session_params_write", "payload": {"worktree_id": "wt_b"}},
            {"hook": "session_params_write", "payload": {"worktree_id": "wt_a"}},
        ]
        with _mock_namespace("wt_a"):
            results = route_hooks_batch(hooks)

        assert len(results) == 3
        assert results[0]["relevant"] is True   # global
        assert results[1]["relevant"] is False  # foreign namespace
        assert results[2]["relevant"] is True   # own namespace


# ── BL-317 SB-4: geist/stab Registry-Erweiterung ─────────────────────────────

# Die echten Pipeline-Guards die das Manifest CWD-relativ loesen (Findings AK-1):
# geist5/6/9, stab10, step_adherence_reminder. Logische Hook-Namen = Script-Basename.
_GEIST_STAB_HOOKS = [
    "guard_geist5_idf_to_sdf",
    "guard_geist6_sdf_internal",
    "guard_geist9_post_sdf",
    "guard_stab10_skill_args",
    "guard_step_adherence_reminder",
]


class TestGeistStabRegistry:
    """AK-1: geist/stab muessen in _NAMESPACE_SCOPED_HOOKS registriert sein,
    damit der Router sie in Multi-Worktree auf ihren Namespace scoped."""

    def test_geist_stab_hooks_in_registry(self):
        for h in _GEIST_STAB_HOOKS:
            assert h in _NAMESPACE_SCOPED_HOOKS, f"{h} fehlt in _NAMESPACE_SCOPED_HOOKS"

    def test_geist_stab_relevant_in_single_worktree(self):
        """(a) Single-Worktree (namespace==None) → geist/stab laufen (Pass-Through Z88-89)."""
        for h in _GEIST_STAB_HOOKS:
            with _mock_namespace(None):
                relevant, reason = is_hook_relevant(h)
            assert relevant is True, f"{h} muss in Single-Worktree relevant sein"
            assert "single" in reason.lower()

    def test_geist_stab_scoped_in_multi_worktree_foreign_namespace(self):
        """(b) Multi-Worktree, fremder Namespace im Payload → geist/stab NICHT relevant (scoped)."""
        for h in _GEIST_STAB_HOOKS:
            with _mock_namespace("wt_a"):
                relevant, reason = is_hook_relevant(h, payload={"worktree_id": "wt_b"})
            assert relevant is False, f"{h} muss bei fremdem Namespace skippen"
            assert "mismatch" in reason.lower()

    def test_geist_stab_relevant_in_multi_worktree_own_namespace(self):
        """Multi-Worktree, eigener Namespace → geist/stab laufen."""
        for h in _GEIST_STAB_HOOKS:
            with _mock_namespace("wt_a"):
                relevant, _ = is_hook_relevant(h, payload={"worktree_id": "wt_a"})
            assert relevant is True


# ── BL-317 SB-4: route_hook_event (settings.json-Einhaengung, fail-open) ──────

class TestRouteHookEvent:
    """AK-1: route_hook_event ist der settings.json-Entrypoint. Liest ein
    Claude-Code-PreToolUse-Event (dict) und gibt (continue_flag, payload) zurueck.
    INV-G3-1: fail-open — Crash/kaputter-Input → continue=True (NIE Block)."""

    def test_single_worktree_always_continue(self):
        """(a) Single-Worktree (namespace==None) → ALLE Hooks continue=True (bit-identisch)."""
        with _mock_namespace(None):
            cont, _ = route_hook_event(
                {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}}
            )
        assert cont is True

    def test_broken_event_fails_open(self):
        """(c) Kaputter Input (None/kein dict) → fail-open continue=True, kein Block."""
        with _mock_namespace("wt_a"):
            cont, _ = route_hook_event(None)
        assert cont is True

    def test_namespace_resolution_crash_fails_open(self):
        """(c) Router-Crash (Namespace-Resolution wirft) → fail-open continue=True."""
        with patch(
            "worktree_hook_router._get_namespace",
            side_effect=RuntimeError("boom"),
        ):
            cont, _ = route_hook_event(
                {"tool_name": "Skill", "tool_input": {}}
            )
        assert cont is True

    def test_event_never_returns_continue_false(self):
        """INV-G3-1: route_hook_event darf NIE continue=False liefern (nur skip via continue=True)."""
        with _mock_namespace("wt_a"):
            cont_foreign, _ = route_hook_event(
                {
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "x.py"},
                    "worktree_id": "wt_b",
                }
            )
        # Auch bei fremdem Namespace: NIE Block (continue bleibt True).
        assert cont_foreign is True

    def test_single_worktree_payload_namespace_carried(self):
        """payload-Rueckgabe enthaelt Routing-Diagnostik (mode/relevant)."""
        with _mock_namespace(None):
            _, payload = route_hook_event(
                {"tool_name": "Read", "tool_input": {}}
            )
        assert payload["mode"] == "single"
        assert payload["relevant"] is True
