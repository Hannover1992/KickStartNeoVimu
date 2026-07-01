#!/usr/bin/env python3
"""
test_hook_view_forward_reference.py — RED tests for hook_view_forward_reference.py

TDD RED Ring (BL-460 Lane-B, P2-cheap-enqueue hook contract).

NEW CONTRACT (P2-hook-cheap):
  handle_write_event(hook_data, vault_root=None) -> dict
  - Write/Edit on a view-node  -> _enqueue_pending(path, vault_root) ONLY (O(1), idempotent).
    Returns {"continue": True, "action": "enqueued", "view": path}.
    forward_reference_new_view must NOT be called.
  - Non-view path or non-Write/Edit tool -> {"continue": True, "action": "skip"}.
  - Any exception -> {"continue": True, "action": "error", ...}; NEVER continue:False.

Rationale (module comment): the live write-hook must be O(1) per write; heavy
forward-referencing (score_view + materialize) is done in BATCH by the P1 swarm /
a sweep that drains {vault}/_forward_ref_pending.md (gated on BL-443). The _model
finish Phase 1.6 keeps the direct (infrequent) heavy trigger.

RED-STATE: Tests in TestHandleWriteEvent + TestViewWriteEnqueueOnly fail against
the CURRENT (heavy) implementation which still calls forward_reference_new_view.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# ---------------------------------------------------------------------------
# Import under test
# ---------------------------------------------------------------------------
import hook_view_forward_reference as hvfr  # noqa: E402  (must be after sys.path.insert)


# ===========================================================================
# 1. is_view_node — True cases (each view type)  [UNCHANGED]
# ===========================================================================

class TestIsViewNodeTrueCases:
    """is_view_node must return True for every recognized view sub-type."""

    def test_backlog_model_md(self, tmp_path):
        """Backlog model file Backlog/<bl>/2_Model/<name>_Model.md is a view node."""
        vault = tmp_path / "vault"
        bl_dir = vault / "Backlog" / "BL-001" / "2_Model"
        bl_dir.mkdir(parents=True)
        f = bl_dir / "Something_Model.md"
        f.write_text("# model")
        assert hvfr.is_view_node(str(f), str(vault)) is True

    def test_arc42_md(self, tmp_path):
        """arc42 document Backlog/<bl>/arc42/<name>.md is a view node."""
        vault = tmp_path / "vault"
        arc_dir = vault / "Backlog" / "BL-002" / "arc42"
        arc_dir.mkdir(parents=True)
        f = arc_dir / "01_Einfuehrung.md"
        f.write_text("# arc42")
        assert hvfr.is_view_node(str(f), str(vault)) is True

    def test_parking_lot_md(self, tmp_path):
        """Parking-Lot file Backlog/<bl>/6_PL/<name>.md is a view node."""
        vault = tmp_path / "vault"
        pl_dir = vault / "Backlog" / "BL-003" / "6_PL"
        pl_dir.mkdir(parents=True)
        f = pl_dir / "PL_items.md"
        f.write_text("# pl")
        assert hvfr.is_view_node(str(f), str(vault)) is True

    def test_docs_md_nested(self, tmp_path):
        """Docs/**/*.md is a view node."""
        vault = tmp_path / "vault"
        docs_dir = vault / "Docs" / "Architecture"
        docs_dir.mkdir(parents=True)
        f = docs_dir / "overview.md"
        f.write_text("# docs")
        assert hvfr.is_view_node(str(f), str(vault)) is True

    def test_docs_md_toplevel(self, tmp_path):
        """Docs/*.md at top level is a view node."""
        vault = tmp_path / "vault"
        docs_dir = vault / "Docs"
        docs_dir.mkdir(parents=True)
        f = docs_dir / "README.md"
        f.write_text("# readme")
        assert hvfr.is_view_node(str(f), str(vault)) is True


# ===========================================================================
# 2. is_view_node — False cases (must NOT be view nodes)  [UNCHANGED]
# ===========================================================================

class TestIsViewNodeFalseCases:
    """is_view_node must return False for excluded paths."""

    def test_truth_atom_excluded(self, tmp_path):
        """Truth atoms under Backlog/<bl>/2_Model/truths/ are atoms, NOT views."""
        vault = tmp_path / "vault"
        truths_dir = vault / "Backlog" / "BL-001" / "2_Model" / "truths"
        truths_dir.mkdir(parents=True)
        f = truths_dir / "Atom_Foo.md"
        f.write_text("```C\n```")
        assert hvfr.is_view_node(str(f), str(vault)) is False

    def test_manifest_excluded(self, tmp_path):
        """_manifest.md files are always excluded."""
        vault = tmp_path / "vault"
        bl_dir = vault / "Backlog" / "BL-001" / "2_Model"
        bl_dir.mkdir(parents=True)
        f = bl_dir / "_manifest.md"
        f.write_text("# manifest")
        assert hvfr.is_view_node(str(f), str(vault)) is False

    def test_non_md_excluded(self, tmp_path):
        """Non-.md files are always excluded."""
        vault = tmp_path / "vault"
        bl_dir = vault / "Backlog" / "BL-001" / "2_Model"
        bl_dir.mkdir(parents=True)
        f = bl_dir / "Something_Model.json"
        f.write_text("{}")
        assert hvfr.is_view_node(str(f), str(vault)) is False

    def test_outside_vault_excluded(self, tmp_path):
        """Path outside vault_root is excluded."""
        vault = tmp_path / "vault"
        vault.mkdir()
        outside = tmp_path / "other" / "file.md"
        outside.parent.mkdir(parents=True)
        outside.write_text("# outside")
        assert hvfr.is_view_node(str(outside), str(vault)) is False

    def test_claude_dir_excluded(self, tmp_path):
        """.claude/ files are excluded (hook scripts are not views)."""
        vault = tmp_path / "vault"
        claude_dir = vault / ".claude" / "scripts"
        claude_dir.mkdir(parents=True)
        f = claude_dir / "some_guard.md"
        f.write_text("# guard doc")
        assert hvfr.is_view_node(str(f), str(vault)) is False

    def test_arbitrary_md_outside_view_dirs_excluded(self, tmp_path):
        """A random .md file not matching any view glob is excluded."""
        vault = tmp_path / "vault"
        other_dir = vault / "RandomDir"
        other_dir.mkdir(parents=True)
        f = other_dir / "notes.md"
        f.write_text("# notes")
        assert hvfr.is_view_node(str(f), str(vault)) is False


# ===========================================================================
# 3. handle_write_event — NEW cheap-enqueue contract
#    Write/Edit on a view-node -> _enqueue_pending ONLY, action="enqueued"
#    forward_reference_new_view must NOT be called
# ===========================================================================

class TestHandleWriteEvent:
    """handle_write_event must use cheap-enqueue contract: NO forward_reference call."""

    def _make_view(self, tmp_path):
        """Helper: create a minimal vault + view file."""
        vault = tmp_path / "vault"
        bl_dir = vault / "Backlog" / "BL-001" / "2_Model"
        bl_dir.mkdir(parents=True)
        view = bl_dir / "Spec_Model.md"
        view.write_text("# spec model")
        return vault, view

    def test_write_on_view_returns_enqueued_action(self, tmp_path, monkeypatch):
        """Write event on a view path returns action='enqueued' (cheap contract)."""
        vault, view = self._make_view(tmp_path)

        frf_calls = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert result["continue"] is True
        assert result["action"] == "enqueued", (
            f"Expected action='enqueued' (cheap contract), got {result['action']!r}"
        )

    def test_write_on_view_does_not_call_forward_reference_new_view(self, tmp_path, monkeypatch):
        """Write event on a view path must NOT call forward_reference_new_view (O(1) hook)."""
        vault, view = self._make_view(tmp_path)

        frf_calls = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(frf_calls) == 0, (
            f"forward_reference_new_view must NOT be called in cheap hook "
            f"(called {len(frf_calls)} time(s))"
        )

    def test_edit_on_view_returns_enqueued_action(self, tmp_path, monkeypatch):
        """Edit event on a view path also returns action='enqueued' (cheap contract)."""
        vault, view = self._make_view(tmp_path)

        frf_calls = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})

        hook_data = {"tool_name": "Edit", "tool_input": {"file_path": str(view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert result["continue"] is True
        assert result["action"] == "enqueued", (
            f"Expected action='enqueued' for Edit on view, got {result['action']!r}"
        )

    def test_edit_on_view_does_not_call_forward_reference_new_view(self, tmp_path, monkeypatch):
        """Edit event on a view path must NOT call forward_reference_new_view."""
        vault, view = self._make_view(tmp_path)

        frf_calls = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})

        hook_data = {"tool_name": "Edit", "tool_input": {"file_path": str(view)}}
        hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(frf_calls) == 0, (
            f"forward_reference_new_view must NOT be called for Edit in cheap hook "
            f"(called {len(frf_calls)} time(s))"
        )

    def test_write_on_view_calls_enqueue_pending(self, tmp_path, monkeypatch):
        """Write event on a view path calls _enqueue_pending with correct path."""
        vault, view = self._make_view(tmp_path)

        enqueued = []
        original_enqueue = hvfr._enqueue_pending

        def spy_enqueue(view_path, vault_root):
            enqueued.append(view_path)
            original_enqueue(view_path, vault_root)

        monkeypatch.setattr(hvfr, "_enqueue_pending", spy_enqueue)
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: {})

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(enqueued) == 1, f"_enqueue_pending must be called once, called {len(enqueued)}"
        assert enqueued[0] == str(view), f"Wrong path enqueued: {enqueued[0]!r}"

    def test_write_on_view_path_appears_in_queue_file(self, tmp_path, monkeypatch):
        """Write event on a view path results in path written to _forward_ref_pending.md."""
        vault, view = self._make_view(tmp_path)

        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: {})

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        hvfr.handle_write_event(hook_data, vault_root=str(vault))

        queue_file = vault / "_forward_ref_pending.md"
        assert queue_file.exists(), "_forward_ref_pending.md must be created after view Write"
        content = queue_file.read_text(encoding="utf-8")
        assert str(view) in content, (
            f"view path must appear in queue file. Queue content: {content!r}"
        )

    def test_write_on_view_result_contains_view_key(self, tmp_path, monkeypatch):
        """Result dict must include 'view' key with the path."""
        vault, view = self._make_view(tmp_path)

        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: {})

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert "view" in result, f"Result must contain 'view' key, got keys: {list(result.keys())}"
        assert result["view"] == str(view), (
            f"result['view'] must equal path, got {result['view']!r}"
        )

    def test_non_view_write_skipped(self, tmp_path, monkeypatch):
        """Write on a non-view path returns action=skip without calling forward_reference."""
        vault = tmp_path / "vault"
        vault.mkdir()
        non_view = vault / "RandomDir" / "notes.md"
        non_view.parent.mkdir(parents=True)
        non_view.write_text("# notes")

        frf_calls = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(non_view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(frf_calls) == 0, "forward_reference_new_view must NOT be called for non-view"
        assert result["continue"] is True
        assert result["action"] == "skip"

    def test_read_tool_skipped(self, tmp_path, monkeypatch):
        """Read tool events are always skipped (not a write operation)."""
        vault, view = self._make_view(tmp_path)
        frf_calls = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})

        hook_data = {"tool_name": "Read", "tool_input": {"file_path": str(view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(frf_calls) == 0
        assert result["continue"] is True
        assert result["action"] == "skip"

    def test_bash_tool_skipped(self, tmp_path, monkeypatch):
        """Bash tool events are always skipped."""
        vault, view = self._make_view(tmp_path)
        frf_calls = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})

        hook_data = {"tool_name": "Bash", "tool_input": {"command": "echo hi"}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(frf_calls) == 0
        assert result["continue"] is True
        assert result["action"] == "skip"


# ===========================================================================
# 4. View-Write enqueue-only contract (extended coverage)
# ===========================================================================

class TestViewWriteEnqueueOnly:
    """Comprehensive tests proving cheap-enqueue-only contract for all view types."""

    def test_arc42_view_write_enqueues_not_frf(self, tmp_path, monkeypatch):
        """arc42 view write: enqueue called, forward_reference_new_view NOT called."""
        vault = tmp_path / "vault"
        arc_dir = vault / "Backlog" / "BL-002" / "arc42"
        arc_dir.mkdir(parents=True)
        view = arc_dir / "01_Einfuehrung.md"
        view.write_text("# arc42")

        frf_calls = []
        enqueued = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})
        orig = hvfr._enqueue_pending
        monkeypatch.setattr(hvfr, "_enqueue_pending",
                            lambda vp, vr: enqueued.append(vp) or orig(vp, vr))

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(frf_calls) == 0, "forward_reference_new_view must NOT be called"
        assert len(enqueued) == 1, "_enqueue_pending must be called once"
        assert result["action"] == "enqueued"

    def test_pl_view_write_enqueues_not_frf(self, tmp_path, monkeypatch):
        """Parking-Lot view write: enqueue called, forward_reference_new_view NOT called."""
        vault = tmp_path / "vault"
        pl_dir = vault / "Backlog" / "BL-003" / "6_PL"
        pl_dir.mkdir(parents=True)
        view = pl_dir / "PL_items.md"
        view.write_text("# pl")

        frf_calls = []
        enqueued = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})
        orig = hvfr._enqueue_pending
        monkeypatch.setattr(hvfr, "_enqueue_pending",
                            lambda vp, vr: enqueued.append(vp) or orig(vp, vr))

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(frf_calls) == 0, "forward_reference_new_view must NOT be called"
        assert len(enqueued) == 1, "_enqueue_pending must be called once"
        assert result["action"] == "enqueued"

    def test_docs_view_write_enqueues_not_frf(self, tmp_path, monkeypatch):
        """Docs view write: enqueue called, forward_reference_new_view NOT called."""
        vault = tmp_path / "vault"
        docs_dir = vault / "Docs" / "Arch"
        docs_dir.mkdir(parents=True)
        view = docs_dir / "overview.md"
        view.write_text("# docs")

        frf_calls = []
        enqueued = []
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: frf_calls.append(a) or {})
        orig = hvfr._enqueue_pending
        monkeypatch.setattr(hvfr, "_enqueue_pending",
                            lambda vp, vr: enqueued.append(vp) or orig(vp, vr))

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert len(frf_calls) == 0, "forward_reference_new_view must NOT be called"
        assert len(enqueued) == 1, "_enqueue_pending must be called once"
        assert result["action"] == "enqueued"

    def test_view_write_idempotent_enqueue(self, tmp_path, monkeypatch):
        """Two Write events on same view path: queue file still has path exactly once."""
        vault = tmp_path / "vault"
        bl_dir = vault / "Backlog" / "BL-001" / "2_Model"
        bl_dir.mkdir(parents=True)
        view = bl_dir / "Spec_Model.md"
        view.write_text("# spec")

        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: {})

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        hvfr.handle_write_event(hook_data, vault_root=str(vault))
        hvfr.handle_write_event(hook_data, vault_root=str(vault))

        queue_file = vault / "_forward_ref_pending.md"
        content = queue_file.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() == str(view)]
        assert len(lines) == 1, (
            f"Path must appear exactly once after double Write (idempotent enqueue), "
            f"got {len(lines)}"
        )


# ===========================================================================
# 5. _enqueue_pending — idempotency and accumulation  [UNCHANGED semantics]
# ===========================================================================

class TestEnqueuePending:
    """_enqueue_pending writes path to {vault_root}/_forward_ref_pending.md idempotently."""

    def test_enqueue_pending_writes_to_queue_file(self, tmp_path):
        """_enqueue_pending writes the path to {vault_root}/_forward_ref_pending.md."""
        vault = tmp_path / "vault"
        vault.mkdir()
        view_path = str(vault / "some_view.md")

        hvfr._enqueue_pending(view_path, str(vault))

        queue_file = vault / "_forward_ref_pending.md"
        assert queue_file.exists(), "_forward_ref_pending.md must be created"
        content = queue_file.read_text(encoding="utf-8")
        assert view_path in content

    def test_enqueue_pending_idempotent(self, tmp_path):
        """Double enqueue of the same path results in only ONE line in the queue."""
        vault = tmp_path / "vault"
        vault.mkdir()
        view_path = str(vault / "duplicate_view.md")

        hvfr._enqueue_pending(view_path, str(vault))
        hvfr._enqueue_pending(view_path, str(vault))

        queue_file = vault / "_forward_ref_pending.md"
        content = queue_file.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() == view_path]
        assert len(lines) == 1, f"Path must appear exactly once after double enqueue, got {len(lines)}"

    def test_enqueue_pending_accumulates_different_paths(self, tmp_path):
        """Two different view paths both appear in the queue."""
        vault = tmp_path / "vault"
        vault.mkdir()
        path_a = str(vault / "view_a.md")
        path_b = str(vault / "view_b.md")

        hvfr._enqueue_pending(path_a, str(vault))
        hvfr._enqueue_pending(path_b, str(vault))

        queue_file = vault / "_forward_ref_pending.md"
        content = queue_file.read_text(encoding="utf-8")
        assert path_a in content
        assert path_b in content


# ===========================================================================
# 6. Fail-open guarantees  [UPDATED: no more forward_reference_new_view bomb]
# ===========================================================================

class TestFailOpen:
    """The hook must NEVER return continue:False and must never raise exceptions."""

    def test_malformed_hook_data_no_exception(self):
        """Completely malformed hook_data must not raise — return continue:True."""
        result = hvfr.handle_write_event({})
        assert result["continue"] is True

    def test_none_tool_input_no_exception(self):
        """hook_data with tool_name but no tool_input must not raise."""
        result = hvfr.handle_write_event({"tool_name": "Write"})
        assert result["continue"] is True

    def test_missing_file_path_no_exception(self):
        """hook_data with tool_input but no file_path must not raise."""
        result = hvfr.handle_write_event({"tool_name": "Write", "tool_input": {}})
        assert result["continue"] is True

    def test_result_never_continue_false_on_view_enqueue_error(self, tmp_path, monkeypatch):
        """Even if _enqueue_pending raises, hook returns continue:True."""
        vault = tmp_path / "vault"
        bl_dir = vault / "Backlog" / "BL-001" / "2_Model"
        bl_dir.mkdir(parents=True)
        view = bl_dir / "Spec_Model.md"
        view.write_text("# spec")

        def boom(view_path, vault_root):
            raise RuntimeError("simulated enqueue error")

        monkeypatch.setattr(hvfr, "_enqueue_pending", boom)
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: {})

        hook_data = {"tool_name": "Write", "tool_input": {"file_path": str(view)}}
        result = hvfr.handle_write_event(hook_data, vault_root=str(vault))

        assert result["continue"] is True, "fail-open: must return continue:True even on enqueue exception"
        assert result["action"] == "error"

    def test_result_never_false_regardless_of_input(self, tmp_path, monkeypatch):
        """No matter what hook_data is passed, continue must never be False."""
        monkeypatch.setattr(hvfr, "forward_reference_new_view",
                            lambda *a, **kw: {})
        payloads = [
            None,
            42,
            "string_payload",
            {},
            {"tool_name": "Write"},
            {"tool_name": "Write", "tool_input": {}},
            {"tool_name": "Write", "tool_input": {"file_path": "/nonexistent/path/model.md"}},
        ]
        for payload in payloads:
            try:
                result = hvfr.handle_write_event(payload)
            except Exception as exc:
                pytest.fail(f"handle_write_event raised on payload {payload!r}: {exc}")
            assert result.get("continue") is not False, \
                f"continue must never be False (got {result} for payload {payload!r})"


# ===========================================================================
# 7. CLI / main: stdin-JSON -> stdout-JSON, always exit 0  [UNCHANGED]
# ===========================================================================

class TestCLIMain:
    """CLI must read stdin-JSON, call handle_write_event, print JSON, exit 0."""

    HOOK_MODULE = SCRIPT_DIR / "hook_view_forward_reference.py"

    def _run_cli(self, stdin_data: dict) -> tuple[subprocess.CompletedProcess, dict]:
        proc = subprocess.run(
            [sys.executable, str(self.HOOK_MODULE)],
            input=json.dumps(stdin_data),
            capture_output=True,
            text=True,
        )
        out = {}
        if proc.stdout.strip():
            try:
                out = json.loads(proc.stdout.strip())
            except json.JSONDecodeError:
                pass
        return proc, out

    def test_cli_exit_0_on_valid_view_write(self, tmp_path):
        """CLI exits 0 for a Write on a valid view path (even if vault not real)."""
        hook_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "vault" / "Backlog" / "BL-001" / "2_Model" / "X_Model.md")}
        }
        proc, out = self._run_cli(hook_data)
        assert proc.returncode == 0, f"CLI must always exit 0, got {proc.returncode}\nstderr: {proc.stderr}"

    def test_cli_exit_0_on_non_view(self, tmp_path):
        """CLI exits 0 even for a non-view path (skip path)."""
        hook_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "random.txt")}
        }
        proc, out = self._run_cli(hook_data)
        assert proc.returncode == 0, f"CLI must always exit 0, got {proc.returncode}"

    def test_cli_exit_0_on_malformed_input(self):
        """CLI exits 0 even on completely malformed stdin (fail-open)."""
        proc = subprocess.run(
            [sys.executable, str(self.HOOK_MODULE)],
            input="not-valid-json{{{",
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"CLI must exit 0 on malformed stdin, got {proc.returncode}"

    def test_cli_outputs_json_with_continue_true(self, tmp_path):
        """CLI stdout must be valid JSON with continue:True."""
        hook_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": str(tmp_path / "something.md")}
        }
        proc, out = self._run_cli(hook_data)
        assert proc.returncode == 0
        assert out.get("continue") is True, f"continue must be True in CLI output, got {out}"

    def test_cli_empty_stdin_fail_open(self):
        """CLI exits 0 on empty stdin."""
        proc = subprocess.run(
            [sys.executable, str(self.HOOK_MODULE)],
            input="",
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"CLI must exit 0 on empty stdin, got {proc.returncode}"
