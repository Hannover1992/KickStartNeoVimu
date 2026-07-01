"""
test_wikilink_materializer_source_atoms.py — RED-Worker BL-460 B-3b Stage 1

Tests for NEW functions in wikilink_materializer.py (AK-4 Write-Side Extension).
These functions do NOT exist yet — all tests MUST FAIL (RED state).

Target functions (not yet implemented):
  - is_source_atom_planted(existing_atoms, atom_id) -> bool
  - write_source_atoms(view_path, atom_ids, vault_root, *, report_path=None) -> tuple[bool, str]
  - _rebuild_frontmatter_with_source_atoms(raw_fm, new_source_atoms) -> str

Conventions:
  - pytest, test_-prefix (NC-6)
  - tmp_path fixtures only — NEVER real vault
  - sys.path.insert for local script import (mirrors existing test_wikilink_materializer.py)
  - Blueprint: 4_Blueprint/S1/blueprint_b3b.md
  - Gold criteria: G4-1..G4-10
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Mirror existing test convention: insert scripts dir so imports resolve
sys.path.insert(0, str(Path(__file__).parent))


# ===========================================================================
# Helpers
# ===========================================================================

def _make_view_file(tmp_path: Path, content: str, name: str = "view.md") -> Path:
    """Create a temp view .md file with given content."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _make_dry_run_report(tmp_path: Path, name: str = "dry_run_report.json") -> Path:
    """Create a minimal valid dry-run JSON report."""
    p = tmp_path / name
    p.write_text(json.dumps({"status": "ok", "views": []}), encoding="utf-8")
    return p


# ===========================================================================
# T-ISP: is_source_atom_planted
# ===========================================================================

class TestIsSourceAtomPlanted:
    """Tests for is_source_atom_planted — must all FAIL (RED) since function absent."""

    def test_isp_1_str_form_present_returns_true(self):
        """T-ISP-1: atom in str-form already in list -> True."""
        from wikilink_materializer import is_source_atom_planted  # type: ignore[import]

        result = is_source_atom_planted(["NS-A.W7", "NS-B.W3"], "NS-A.W7")
        assert result is True

    def test_isp_2_str_form_absent_returns_false(self):
        """T-ISP-2: atom not in list -> False."""
        from wikilink_materializer import is_source_atom_planted  # type: ignore[import]

        result = is_source_atom_planted(["NS-A.W7"], "NS-B.W3")
        assert result is False

    def test_isp_3_dict_form_present_returns_true(self):
        """T-ISP-3: atom in dict-form (atom_id key) -> True."""
        from wikilink_materializer import is_source_atom_planted  # type: ignore[import]

        result = is_source_atom_planted([{"atom_id": "NS-A.W7", "extra": "x"}], "NS-A.W7")
        assert result is True

    def test_isp_4_empty_list_returns_false_no_crash(self):
        """T-ISP-4: empty list -> False, no crash."""
        from wikilink_materializer import is_source_atom_planted  # type: ignore[import]

        result = is_source_atom_planted([], "NS-A.W7")
        assert result is False

    def test_isp_5_none_entries_ignored_no_crash(self):
        """T-ISP-5: None entries in list -> ignored, no crash, still finds target."""
        from wikilink_materializer import is_source_atom_planted  # type: ignore[import]

        result = is_source_atom_planted([None, "NS-A.W7"], "NS-A.W7")
        assert result is True

    def test_isp_5b_none_entries_only_returns_false(self):
        """T-ISP-5b: list of Nones -> False, no crash."""
        from wikilink_materializer import is_source_atom_planted  # type: ignore[import]

        result = is_source_atom_planted([None, None], "NS-A.W7")
        assert result is False

    def test_isp_6_heterogeneous_list_str_dict_none(self):
        """T-ISP-6: heterogeneous list (str + dict + None) -> correct answer, no crash."""
        from wikilink_materializer import is_source_atom_planted  # type: ignore[import]

        mixed = [None, "NS-B.W3", {"atom_id": "NS-C.W1"}, "NS-A.W7"]
        assert is_source_atom_planted(mixed, "NS-A.W7") is True
        assert is_source_atom_planted(mixed, "NS-C.W1") is True
        assert is_source_atom_planted(mixed, "NS-B.W3") is True
        assert is_source_atom_planted(mixed, "NS-X.W9") is False

    def test_isp_6b_dict_form_wrong_key_not_matched(self):
        """T-ISP-6b: dict without atom_id key -> not matched (no false positive)."""
        from wikilink_materializer import is_source_atom_planted  # type: ignore[import]

        # dict with different key should NOT match
        result = is_source_atom_planted([{"ziel": "NS-A.W7"}], "NS-A.W7")
        assert result is False


# ===========================================================================
# T-WSA: write_source_atoms — core write + idempotency
# ===========================================================================

class TestWriteSourceAtoms:
    """Tests for write_source_atoms — must all FAIL (RED) since function absent."""

    # -----------------------------------------------------------------------
    # G4-1: Frontmatter gets source_atoms written
    # -----------------------------------------------------------------------

    def test_wsa_1_first_call_writes_frontmatter_and_body(self, tmp_path):
        """T-WSA-1 / G4-1+G4-2: first call -> (True, 'changed'), frontmatter+body updated."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, (
            "---\ntype: model\ntitle: Test View\n---\n\n# Content\n\nSome text.\n"
        ))
        vault_root = tmp_path

        changed, reason = write_source_atoms(view, ["NS-A.W7"], vault_root)

        assert changed is True, f"Expected changed=True, got {changed!r}"
        assert reason == "changed", f"Expected reason='changed', got {reason!r}"

        content = view.read_text(encoding="utf-8")
        assert "source_atoms:" in content, "source_atoms: key missing from frontmatter"
        assert "NS-A.W7" in content, "atom_id missing from frontmatter"
        # G4-2: body wikilink appended
        assert "[[NS-A.W7" in content or "[[" in content, "wikilink missing from body"

    # -----------------------------------------------------------------------
    # G4-3 (KERN-GOLD): double-run no duplicate
    # -----------------------------------------------------------------------

    def test_wsa_2_double_run_idempotent_no_duplicate(self, tmp_path):
        """T-WSA-2 / G4-3 KERN-GOLD: second call with same atom_ids -> (False, 'already_present'), no duplicate."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, (
            "---\ntype: model\ntitle: Idempotency Test\n---\n\n# Content\n"
        ))
        vault_root = tmp_path

        # First call — write
        changed1, reason1 = write_source_atoms(view, ["NS-A.W7"], vault_root)
        assert changed1 is True

        content_after_first = view.read_text(encoding="utf-8")

        # Second call — MUST be idempotent
        changed2, reason2 = write_source_atoms(view, ["NS-A.W7"], vault_root)
        assert changed2 is False, f"Second call returned changed=True — duplicate written!"
        assert reason2 == "already_present", f"Expected 'already_present', got {reason2!r}"

        content_after_second = view.read_text(encoding="utf-8")

        # File content must be byte-identical after second call
        assert content_after_first == content_after_second, (
            "File changed on second call — idempotency violated!"
        )

        # Explicit duplicate count: atom_id must appear exactly once in source_atoms block
        # Count occurrences of the atom in the frontmatter section
        fm_end = content_after_second.find("\n---", 3)
        frontmatter_section = content_after_second[:fm_end] if fm_end != -1 else content_after_second
        count_in_fm = frontmatter_section.count("NS-A.W7")
        assert count_in_fm == 1, (
            f"NS-A.W7 appears {count_in_fm} times in frontmatter — duplicate detected!"
        )

    def test_wsa_3_multiple_atoms_first_all_written_second_no_change(self, tmp_path):
        """T-WSA-3: multiple atoms — first call writes all; second call no change."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, (
            "---\ntype: model\n---\n\n# Multi-atom test\n"
        ))
        vault_root = tmp_path
        atom_ids = ["NS-A.W1", "NS-B.W2", "NS-C.W3"]

        changed1, _ = write_source_atoms(view, atom_ids, vault_root)
        assert changed1 is True

        content_after_1 = view.read_text(encoding="utf-8")

        # All atoms must be present
        for aid in atom_ids:
            assert aid in content_after_1, f"{aid} missing after first call"

        changed2, reason2 = write_source_atoms(view, atom_ids, vault_root)
        assert changed2 is False
        assert reason2 == "already_present"
        assert view.read_text(encoding="utf-8") == content_after_1

    def test_wsa_4_partial_new_atoms_only_new_added(self, tmp_path):
        """T-WSA-4: 2 existing + 1 new -> (True, 'changed'), only new added, no duplicates."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        # Pre-populate with 2 atoms
        view = _make_view_file(tmp_path, (
            "---\ntype: model\nsource_atoms:\n  - NS-A.W1\n  - NS-B.W2\n---\n\n# Content\n"
        ))
        vault_root = tmp_path

        changed, reason = write_source_atoms(view, ["NS-A.W1", "NS-B.W2", "NS-C.W3"], vault_root)
        assert changed is True, "Expected changed=True when 1 new atom added"

        content = view.read_text(encoding="utf-8")
        # NS-C.W3 must be present
        assert "NS-C.W3" in content, "New atom NS-C.W3 missing"
        # No duplicates
        fm_end = content.find("\n---", 3)
        fm_section = content[:fm_end] if fm_end != -1 else content
        assert fm_section.count("NS-A.W1") == 1, "NS-A.W1 duplicated in frontmatter"
        assert fm_section.count("NS-B.W2") == 1, "NS-B.W2 duplicated in frontmatter"

    def test_wsa_5_other_frontmatter_fields_preserved(self, tmp_path):
        """T-WSA-5 / G4-4: existing frontmatter fields byte-preserved after write."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, (
            "---\ntype: model\ntitle: My View\nauthor: test-author\n---\n\n# Content\n"
        ))
        vault_root = tmp_path

        write_source_atoms(view, ["NS-A.W7"], vault_root)
        content = view.read_text(encoding="utf-8")

        assert "type: model" in content, "type field lost"
        assert "title: My View" in content, "title field lost"
        assert "author: test-author" in content, "author field lost"

    def test_wsa_6_empty_atom_ids_returns_already_present(self, tmp_path):
        """T-WSA-6: atom_ids=[] -> (False, 'already_present'), no crash, no change."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        original_content = "---\ntype: model\n---\n\n# Content\n"
        view = _make_view_file(tmp_path, original_content)
        vault_root = tmp_path

        changed, reason = write_source_atoms(view, [], vault_root)
        assert changed is False
        assert reason == "already_present"
        assert view.read_text(encoding="utf-8") == original_content


# ===========================================================================
# T-GATE: write_source_atoms — Write-Gate integration
# ===========================================================================

class TestWriteSourceAtomsGate:
    """Gate-related tests for write_source_atoms — must all FAIL (RED)."""

    def test_gate_1_write_gated_returns_blocked(self, tmp_path):
        """T-GATE-1 / G4-5: is_write_gated returns (True, reason) -> (False, 'BLOCKED: ...')."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        vault_root = tmp_path
        original = view.read_text(encoding="utf-8")

        with patch("wikilink_materializer.write_gate_guard") as mock_gate:
            mock_gate.is_write_gated.return_value = (True, "N corrupt")
            changed, reason = write_source_atoms(view, ["NS-A.W7"], vault_root)

        assert changed is False
        assert "BLOCKED" in reason, f"Expected BLOCKED in reason, got {reason!r}"
        assert "N corrupt" in reason, f"Expected gate reason in message, got {reason!r}"
        assert view.read_text(encoding="utf-8") == original, "File changed despite gate block"

    def test_gate_2_write_allowed_proceeds(self, tmp_path):
        """T-GATE-2: is_write_gated returns (False, 'clean') -> write proceeds."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        vault_root = tmp_path

        with patch("wikilink_materializer.write_gate_guard") as mock_gate:
            mock_gate.is_write_gated.return_value = (False, "clean")
            changed, reason = write_source_atoms(view, ["NS-A.W7"], vault_root)

        assert changed is True
        content = view.read_text(encoding="utf-8")
        assert "NS-A.W7" in content

    def test_gate_3_dry_run_report_missing_blocks(self, tmp_path):
        """T-GATE-3 / G4-6: report_path given but missing -> (False, 'BLOCKED: no dry-run ...')."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        vault_root = tmp_path
        missing_report = tmp_path / "nonexistent_report.json"
        original = view.read_text(encoding="utf-8")

        changed, reason = write_source_atoms(view, ["NS-A.W7"], vault_root, report_path=missing_report)

        assert changed is False
        assert "BLOCKED" in reason, f"Expected BLOCKED, got {reason!r}"
        assert view.read_text(encoding="utf-8") == original, "File changed despite missing report"

    def test_gate_4_valid_report_allows_write(self, tmp_path):
        """T-GATE-4: valid dry-run report present + report_path given -> write proceeds."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        vault_root = tmp_path
        report = _make_dry_run_report(tmp_path)

        changed, reason = write_source_atoms(view, ["NS-A.W7"], vault_root, report_path=report)

        assert changed is True
        assert "NS-A.W7" in view.read_text(encoding="utf-8")

    def test_gate_5_write_gate_guard_import_error_fail_open(self, tmp_path):
        """T-GATE-5: write_gate_guard not importable -> fail-open, no crash, write proceeds."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        vault_root = tmp_path

        # Simulate ImportError by removing the module from sys.modules and blocking re-import
        import importlib
        saved = sys.modules.pop("write_gate_guard", None)
        try:
            with patch.dict("sys.modules", {"write_gate_guard": None}):
                # Should not raise — fail-open means write still proceeds
                changed, reason = write_source_atoms(view, ["NS-A.W7"], vault_root)
                # fail-open: no exception, write proceeds (changed=True) or at minimum no crash
                # exact behavior: no Exception raised
        finally:
            if saved is not None:
                sys.modules["write_gate_guard"] = saved

    def test_gate_6_dry_run_reporter_import_error_fail_open(self, tmp_path):
        """T-GATE-6: dry_run_reporter not importable -> fail-open, no crash."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        vault_root = tmp_path
        report = _make_dry_run_report(tmp_path)

        saved = sys.modules.pop("dry_run_reporter", None)
        try:
            with patch.dict("sys.modules", {"dry_run_reporter": None}):
                # fail-open: no exception raised even with ImportError on dry_run_reporter
                changed, reason = write_source_atoms(view, ["NS-A.W7"], vault_root, report_path=report)
        finally:
            if saved is not None:
                sys.modules["dry_run_reporter"] = saved

    def test_gate_7_report_path_none_skips_dry_run_gate(self, tmp_path):
        """T-GATE-7: report_path=None -> dry-run gate SKIPPED, write proceeds."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        vault_root = tmp_path

        # report_path=None (default) must NOT block
        changed, reason = write_source_atoms(view, ["NS-A.W7"], vault_root, report_path=None)

        assert changed is True, f"Expected changed=True with report_path=None, got {changed!r}"
        assert "NS-A.W7" in view.read_text(encoding="utf-8")


# ===========================================================================
# T-RFM: _rebuild_frontmatter_with_source_atoms
# ===========================================================================

class TestRebuildFrontmatterWithSourceAtoms:
    """Tests for _rebuild_frontmatter_with_source_atoms — must all FAIL (RED)."""

    def test_rfm_1_no_existing_source_atoms_appended(self):
        """T-RFM-1: no source_atoms field -> appended before closing ---."""
        from wikilink_materializer import _rebuild_frontmatter_with_source_atoms  # type: ignore[import]

        raw_fm = "---\ntype: model\ntitle: My View\n---"
        result = _rebuild_frontmatter_with_source_atoms(raw_fm, ["NS-A.W7"])

        assert "source_atoms:" in result, "source_atoms: key not appended"
        assert "NS-A.W7" in result, "atom_id missing from rebuilt frontmatter"
        assert result.endswith("---") or result.endswith("---\n"), "closing --- missing"
        # Other fields preserved
        assert "type: model" in result, "type field lost"
        assert "title: My View" in result, "title field lost"

    def test_rfm_2_existing_source_atoms_replaced(self):
        """T-RFM-2: existing source_atoms block replaced with new list, no duplicates."""
        from wikilink_materializer import _rebuild_frontmatter_with_source_atoms  # type: ignore[import]

        raw_fm = "---\ntype: model\nsource_atoms:\n  - NS-OLD.W1\n---"
        result = _rebuild_frontmatter_with_source_atoms(raw_fm, ["NS-A.W7", "NS-B.W3"])

        assert "NS-A.W7" in result, "new atom missing"
        assert "NS-B.W3" in result, "new atom missing"
        # Old value should be gone
        assert "NS-OLD.W1" not in result, "old atom still present after replacement"
        assert result.count("source_atoms:") == 1, "source_atoms: duplicated"

    def test_rfm_3_other_fields_byte_preserved(self):
        """T-RFM-3 / G4-4: other frontmatter fields preserved byte-for-byte."""
        from wikilink_materializer import _rebuild_frontmatter_with_source_atoms  # type: ignore[import]

        raw_fm = "---\ntype: model\ntitle: Exact Preserve\nauthor: me\ncustom: value\n---"
        result = _rebuild_frontmatter_with_source_atoms(raw_fm, ["NS-A.W7"])

        assert "type: model" in result
        assert "title: Exact Preserve" in result
        assert "author: me" in result
        assert "custom: value" in result

    def test_rfm_4_empty_new_atoms_no_crash(self):
        """T-RFM-4: empty new_source_atoms -> no crash, result still valid frontmatter."""
        from wikilink_materializer import _rebuild_frontmatter_with_source_atoms  # type: ignore[import]

        raw_fm = "---\ntype: model\n---"
        # Must not raise
        result = _rebuild_frontmatter_with_source_atoms(raw_fm, [])
        assert result is not None
        assert "type: model" in result

    def test_rfm_5_multiple_atoms_all_written(self):
        """T-RFM-5: 3 atoms -> all present in rebuilt frontmatter as list items."""
        from wikilink_materializer import _rebuild_frontmatter_with_source_atoms  # type: ignore[import]

        raw_fm = "---\ntype: model\n---"
        atoms = ["NS-A.W1", "NS-B.W2", "NS-C.W3"]
        result = _rebuild_frontmatter_with_source_atoms(raw_fm, atoms)

        for atom in atoms:
            assert atom in result, f"{atom} missing from rebuilt frontmatter"


# ===========================================================================
# T-CLI: CLI extension backward-compat + new flags
# ===========================================================================

class TestCliExtension:
    """CLI tests — must all FAIL (RED) since new args not yet implemented."""

    def _run_cli(self, argv: list[str]) -> int:
        from wikilink_materializer import main  # type: ignore[import]
        return main(argv)

    def test_cli_1_dry_run_source_atoms_mode_no_write_exit_0(self, tmp_path):
        """T-CLI-1: --dry-run --source-atoms-mode -> no writes, exit 0."""
        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        original = view.read_text(encoding="utf-8")

        exit_code = self._run_cli([
            "--vault", str(tmp_path),
            "--dry-run",
            "--source-atoms-mode",
        ])

        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        assert view.read_text(encoding="utf-8") == original, "Dry-run must not write"

    def test_cli_2_write_source_atoms_mode_with_clean_gate_writes(self, tmp_path):
        """T-CLI-2: --write --source-atoms-mode + gate mock (clean) -> files written, exit 0."""
        view = _make_view_file(tmp_path, (
            "---\ntype: model\nsource_atoms_mode_trigger: yes\n---\n\n# Content\n"
        ))

        with patch("wikilink_materializer.write_gate_guard") as mock_gate:
            mock_gate.is_write_gated.return_value = (False, "clean")
            exit_code = self._run_cli([
                "--vault", str(tmp_path),
                "--write",
                "--source-atoms-mode",
            ])

        assert exit_code == 0, f"Expected exit 0, got {exit_code}"

    def test_cli_3_write_source_atoms_mode_with_blocked_gate_exit_1(self, tmp_path):
        """T-CLI-3 / G4-8: --write --source-atoms-mode + gated -> no writes, exit 1."""
        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        original = view.read_text(encoding="utf-8")

        with patch("wikilink_materializer.write_gate_guard") as mock_gate:
            mock_gate.is_write_gated.return_value = (True, "corrupt nodes")
            exit_code = self._run_cli([
                "--vault", str(tmp_path),
                "--write",
                "--source-atoms-mode",
            ])

        assert exit_code == 1, f"Expected exit 1 (gated), got {exit_code}"
        assert view.read_text(encoding="utf-8") == original, "File written despite gate block"

    def test_cli_4_existing_dry_run_without_source_atoms_mode_unchanged(self, tmp_path):
        """T-CLI-4 / G4-9: existing --dry-run without --source-atoms-mode -> backward compat."""
        view = _make_view_file(tmp_path, "---\ntype: model\n---\n\n# Content\n")
        original = view.read_text(encoding="utf-8")

        exit_code = self._run_cli([
            "--vault", str(tmp_path),
            "--dry-run",
        ])

        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        # Existing dry-run path must not break
        assert view.read_text(encoding="utf-8") == original


# ===========================================================================
# T-NOFM: write_source_atoms — NO-clean-frontmatter REFUSAL (BL-491 AC-1 / F-2)
# ===========================================================================
#
# RED-phase (BL-491 AC-1, ARTIFACT 2): these target the CURRENT un-hardened
# wikilink_materializer and MUST FAIL now. They reproduce the F-2 corruption:
# _split_raw_frontmatter(content) returns raw_fm=="" whenever content does NOT
# literally start with "---" (leading BOM OR a no-frontmatter view). The
# un-hardened write_source_atoms then feeds raw_fm=="" into
# _rebuild_frontmatter_with_source_atoms, which emits a BARE source_atoms: block
# (no --- delimiters) and prepends it at byte 0 -> corruption.
#
# After GREEN hardening: write_source_atoms must REFUSE (return (False, reason)
# with reason.startswith("error: no clean frontmatter")) and leave the file
# byte-identical on disk.

class TestWriteSourceAtomsNoFrontmatterRefusal:
    """write_source_atoms must refuse to prepend when there is no clean
    `---` frontmatter (no-frontmatter view OR leading-BOM view). RED until
    the GREEN worker adds the choke-point guard."""

    def test_wsa_nofm_1_no_frontmatter_view_refused_file_unchanged(self, tmp_path):
        """T-NOFM-1 / F-2: no-frontmatter view ("# Heading\\n\\nbody text\\n") with a
        non-empty atom_ids list MUST be refused (no bare source_atoms block
        prepended) and the file MUST be byte-identical to the original."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        view = _make_view_file(tmp_path, "# Heading\n\nbody text\n")
        vault_root = tmp_path
        original_bytes = view.read_bytes()

        changed, reason = write_source_atoms(view, ["NS-A.W1"], vault_root)

        assert changed is False, (
            f"Expected refusal (changed=False) on a no-frontmatter view, got {changed!r}"
        )
        assert reason.startswith("error: no clean frontmatter"), (
            f"Expected reason to start with 'error: no clean frontmatter', got {reason!r}"
        )
        # F-2 corruption guard: file must be byte-identical (NO prepended block).
        assert view.read_bytes() == original_bytes, (
            "File on disk was modified — F-2 corruption (bare source_atoms block prepended)!"
        )

    def test_wsa_nofm_2_bom_then_frontmatter_view_refused_file_unchanged(self, tmp_path):
        """T-NOFM-2 / Shape A: a BOM-then-`---` view (leading U+FEFF) makes
        _split_raw_frontmatter return raw_fm=="" -> MUST also be refused and the
        file MUST be byte-identical to the original."""
        from wikilink_materializer import write_source_atoms  # type: ignore[import]

        # Leading U+FEFF BOM, then real frontmatter. encoded as UTF-8 (EF BB BF ...).
        view = _make_view_file(tmp_path, "﻿---\ntype: model\n---\n\nbody\n")
        vault_root = tmp_path
        original_bytes = view.read_bytes()
        # Sanity: the file really does begin with a UTF-8 BOM on disk.
        assert original_bytes.startswith(b"\xef\xbb\xbf"), "test setup: BOM not written to disk"

        changed, reason = write_source_atoms(view, ["NS-A.W1"], vault_root)

        assert changed is False, (
            f"Expected refusal (changed=False) on a BOM-prefixed view, got {changed!r}"
        )
        assert reason.startswith("error: no clean frontmatter"), (
            f"Expected reason to start with 'error: no clean frontmatter', got {reason!r}"
        )
        assert view.read_bytes() == original_bytes, (
            "File on disk was modified — BOM-prefixed view must be left byte-identical!"
        )


# ===========================================================================
# T-RFMGUARD: _rebuild_frontmatter_with_source_atoms — structural guard
# ===========================================================================
#
# RED-phase (BL-491 AC-1, ARTIFACT 2, defense-in-depth): the rebuild helper must
# raise ValueError when raw_fm does NOT start with "---", so the bare-block
# prepend else-path that produced the corruption is structurally unreachable.
# Un-hardened code returns a bare block instead of raising -> these FAIL now.

class TestRebuildFrontmatterRejectsNonFrontmatter:
    """_rebuild_frontmatter_with_source_atoms must reject raw_fm that does not
    start with `---`. RED until the GREEN worker adds the ValueError guard."""

    def test_rfmguard_1_empty_raw_fm_raises_value_error(self):
        """T-RFMGUARD-1: empty raw_fm -> ValueError (no bare-block emission)."""
        from wikilink_materializer import _rebuild_frontmatter_with_source_atoms  # type: ignore[import]

        with pytest.raises(ValueError):
            _rebuild_frontmatter_with_source_atoms("", ["NS-A.W1"])

    def test_rfmguard_2_non_frontmatter_raw_fm_raises_value_error(self):
        """T-RFMGUARD-2: raw_fm that doesn't start with --- -> ValueError."""
        from wikilink_materializer import _rebuild_frontmatter_with_source_atoms  # type: ignore[import]

        with pytest.raises(ValueError):
            _rebuild_frontmatter_with_source_atoms("# not frontmatter\n", ["NS-A.W1"])
