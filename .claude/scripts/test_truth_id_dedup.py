#!/usr/bin/env python3
"""
RED-phase tests for truth_id_dedup.py.

These tests MUST FAIL because truth_id_dedup.py does not exist yet.
All ModuleNotFoundError failures are expected RED signals.

Collision shape: two truth atoms share the same global id {namespace}.{local_id}.
Canonical copy: path contains the namespace string.
Stray copy: path does NOT contain the namespace string.
Fix: keep canonical, delete stray(s).
"""
from __future__ import annotations

import os
import pytest

from truth_id_dedup import (
    find_collisions,
    canonical_path,
    dedup,
    main,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _truth_atom(atom_id: str, local_id: str, extra: str = "") -> str:
    """Minimal valid truth atom frontmatter + body."""
    return (
        "---\n"
        "type: truth\n"
        f"id: {atom_id}\n"
        f"local_id: {local_id}\n"
        "text: 'test atom'\n"
        + (extra + "\n" if extra else "")
        + "---\n"
        "body\n"
    )


def _non_truth_atom(atom_id: str) -> str:
    """A file that is NOT type:truth (should be ignored by find_collisions)."""
    return (
        "---\n"
        "type: pattern\n"
        f"id: {atom_id}\n"
        "text: 'not a truth'\n"
        "---\n"
        "body\n"
    )


def _write(path, content: str) -> None:
    """Write content to path, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. find_collisions
# ---------------------------------------------------------------------------

class TestFindCollisions:
    def test_finds_collision_two_files_same_id(self, tmp_path):
        """Two truth files sharing the same id -> collision reported."""
        # canonical: path contains namespace 'NS'
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        # stray: path does NOT contain namespace 'NS'
        stray = tmp_path / "truths" / "W1.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, _truth_atom("NS.W1", "W1"))

        result = find_collisions(tmp_path)

        assert "NS.W1" in result, f"Expected collision for NS.W1, got: {result}"
        paths = result["NS.W1"]
        assert len(paths) == 2, f"Expected 2 paths for NS.W1, got: {paths!r}"

    def test_ignores_unique_id(self, tmp_path):
        """Id present in only one truth file -> NOT in collision result."""
        single = tmp_path / "truths" / "W2.md"
        _write(single, _truth_atom("NS.W2", "W2"))

        result = find_collisions(tmp_path)

        assert "NS.W2" not in result, f"Unique id NS.W2 should not appear: {result}"

    def test_ignores_non_truth_files(self, tmp_path):
        """File with type != 'truth' must be ignored; no false collision reported."""
        truth_file = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W3.md"
        non_truth = tmp_path / "truths" / "W3.md"
        _write(truth_file, _truth_atom("NS.W3", "W3"))
        _write(non_truth, _non_truth_atom("NS.W3"))

        result = find_collisions(tmp_path)

        assert "NS.W3" not in result, (
            f"NS.W3 should not be a collision (stray is non-truth): {result}"
        )

    def test_returned_paths_are_relative(self, tmp_path):
        """Paths in collision result must be relative strings (not absolute)."""
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, _truth_atom("NS.W1", "W1"))

        result = find_collisions(tmp_path)
        paths = result["NS.W1"]

        for p in paths:
            assert isinstance(p, str), f"Path should be str, got {type(p)}: {p!r}"
            assert not os.path.isabs(p), f"Path should be relative, got: {p!r}"

    def test_empty_root_returns_empty(self, tmp_path):
        """No truth atoms -> no collisions."""
        result = find_collisions(tmp_path)
        assert result == {}, f"Empty root should return empty dict, got: {result}"

    def test_multiple_collisions_all_reported(self, tmp_path):
        """Multiple colliding ids all appear in result."""
        for wid in ["W10", "W11"]:
            ns = "Alpha"
            atom_id = f"{ns}.{wid}"
            canonical = tmp_path / f"_meta_truths/{ns}_Model/truths/{wid}.md"
            stray = tmp_path / f"truths/{wid}.md"
            _write(canonical, _truth_atom(atom_id, wid))
            _write(stray, _truth_atom(atom_id, wid))

        result = find_collisions(tmp_path)

        assert "Alpha.W10" in result, f"Alpha.W10 missing from collisions: {result}"
        assert "Alpha.W11" in result, f"Alpha.W11 missing from collisions: {result}"

    def test_non_colliding_ids_absent_from_result(self, tmp_path):
        """Only the colliding id appears; unique ids are absent."""
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        unique = tmp_path / "truths" / "W99.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, _truth_atom("NS.W1", "W1"))
        _write(unique, _truth_atom("NS.W99", "W99"))

        result = find_collisions(tmp_path)

        assert "NS.W1" in result, "NS.W1 must be in collisions"
        assert "NS.W99" not in result, "NS.W99 (unique) must NOT be in collisions"


# ---------------------------------------------------------------------------
# 2. canonical_path
# ---------------------------------------------------------------------------

class TestCanonicalPath:
    def test_returns_path_containing_namespace(self):
        """canonical_path returns the one path whose components contain the namespace."""
        paths = [
            "_meta_truths/NS_Model/truths/W1.md",
            "truths/W1.md",
        ]
        result = canonical_path("NS.W1", paths)
        assert result == "_meta_truths/NS_Model/truths/W1.md", (
            f"Expected canonical path, got: {result!r}"
        )

    def test_returns_none_when_no_path_contains_namespace(self):
        """No path contains namespace -> None (cannot determine canonical)."""
        paths = [
            "a/W1.md",
            "b/W1.md",
        ]
        result = canonical_path("NS.W1", paths)
        assert result is None, f"Expected None when no path contains NS, got: {result!r}"

    def test_returns_none_when_multiple_paths_contain_namespace(self):
        """More than one path contains namespace -> None (ambiguous)."""
        paths = [
            "_meta_truths/NS_Model/truths/W1.md",
            "another/NS/truths/W1.md",
        ]
        result = canonical_path("NS.W1", paths)
        assert result is None, (
            f"Expected None when >1 path contains NS (ambiguous), got: {result!r}"
        )

    def test_real_world_layout_sprint_monitor(self):
        """Real-world layout: OmniCommand_SprintMonitor namespace match."""
        paths = [
            "_meta_truths/OmniCommand_SprintMonitor_Model/truths/W185.md",
            "Models/truths/W185.md",
        ]
        result = canonical_path("OmniCommand_SprintMonitor.W185", paths)
        assert result == "_meta_truths/OmniCommand_SprintMonitor_Model/truths/W185.md", (
            f"Wrong canonical path returned: {result!r}"
        )

    def test_underscore_namespace_match(self):
        """Namespace with underscores (I_MetaPattern) is matched correctly."""
        paths = [
            "_meta_truths/I_MetaPattern_Model/truths/W1.md",
            "truths/W1.md",
        ]
        result = canonical_path("I_MetaPattern.W1", paths)
        assert result == "_meta_truths/I_MetaPattern_Model/truths/W1.md", (
            f"Expected I_MetaPattern canonical path, got: {result!r}"
        )

    def test_namespace_extracted_as_part_before_last_dot(self):
        """Namespace is the part before the last '.': 'A.B.C' -> namespace 'A.B'."""
        paths = [
            "some/A.B_Model/truths/C.md",
            "other/truths/C.md",
        ]
        result = canonical_path("A.B.C", paths)
        # namespace is 'A.B'; path "some/A.B_Model/truths/C.md" contains 'A.B'
        assert result == "some/A.B_Model/truths/C.md", (
            f"Expected path containing 'A.B', got: {result!r}"
        )


# ---------------------------------------------------------------------------
# 3. dedup dry-run (apply=False)
# ---------------------------------------------------------------------------

class TestDedupDryRun:
    def _setup_collision(self, tmp_path):
        """Create a canonical + stray file sharing NS.W1."""
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, _truth_atom("NS.W1", "W1"))
        return canonical, stray

    def test_dry_run_deletes_nothing(self, tmp_path):
        """apply=False -> both files still exist after dedup."""
        canonical, stray = self._setup_collision(tmp_path)

        dedup(tmp_path, apply=False)

        assert canonical.exists(), "Canonical must still exist after dry-run"
        assert stray.exists(), "Stray must still exist after dry-run"

    def test_dry_run_deleted_is_zero(self, tmp_path):
        """apply=False -> result['deleted'] == 0."""
        self._setup_collision(tmp_path)

        result = dedup(tmp_path, apply=False)

        assert result["deleted"] == 0, (
            f"deleted should be 0 in dry-run, got: {result['deleted']}"
        )

    def test_dry_run_reports_collisions(self, tmp_path):
        """apply=False -> result['collisions'] >= 1."""
        self._setup_collision(tmp_path)

        result = dedup(tmp_path, apply=False)

        assert result["collisions"] >= 1, (
            f"collisions should be >= 1, got: {result['collisions']}"
        )

    def test_dry_run_reports_resolved(self, tmp_path):
        """apply=False -> result['resolved'] >= 1 (one resolvable collision)."""
        self._setup_collision(tmp_path)

        result = dedup(tmp_path, apply=False)

        assert result["resolved"] >= 1, (
            f"resolved should be >= 1 for one resolvable collision, got: {result['resolved']}"
        )

    def test_dry_run_result_has_required_int_keys(self, tmp_path):
        """dedup result must contain all documented int keys."""
        self._setup_collision(tmp_path)

        result = dedup(tmp_path, apply=False)

        int_keys = {"collisions", "resolved", "deleted", "backed_up", "ambiguous"}
        for key in int_keys:
            assert key in result, f"Missing int key: {key!r}"
            assert isinstance(result[key], int), (
                f"result[{key!r}] should be int, got {type(result[key]).__name__}"
            )

    def test_dry_run_result_has_ambiguous_ids_list(self, tmp_path):
        """dedup result must contain 'ambiguous_ids' as a list."""
        self._setup_collision(tmp_path)

        result = dedup(tmp_path, apply=False)

        assert "ambiguous_ids" in result, "Missing 'ambiguous_ids' list key"
        assert isinstance(result["ambiguous_ids"], list), (
            f"ambiguous_ids should be a list, got {type(result['ambiguous_ids'])!r}"
        )

    def test_dry_run_backed_up_is_zero(self, tmp_path):
        """apply=False -> no backups made, backed_up == 0."""
        self._setup_collision(tmp_path)

        result = dedup(tmp_path, apply=False)

        assert result["backed_up"] == 0, (
            f"backed_up should be 0 in dry-run, got: {result['backed_up']}"
        )


# ---------------------------------------------------------------------------
# 4. dedup apply=True
# ---------------------------------------------------------------------------

class TestDedupApply:
    def _setup_collision(self, tmp_path):
        """Canonical: path contains NS. Stray: path does NOT contain NS."""
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, _truth_atom("NS.W1", "W1"))
        return canonical, stray

    def test_apply_deletes_stray(self, tmp_path):
        """apply=True -> stray file (path not containing namespace) is deleted."""
        canonical, stray = self._setup_collision(tmp_path)

        dedup(tmp_path, apply=True)

        assert not stray.exists(), "Stray must be deleted after apply=True"

    def test_apply_keeps_canonical(self, tmp_path):
        """apply=True -> canonical file (path containing namespace) is kept."""
        canonical, stray = self._setup_collision(tmp_path)

        dedup(tmp_path, apply=True)

        assert canonical.exists(), "Canonical must be kept after apply=True"

    def test_apply_resolves_all_collisions(self, tmp_path):
        """After apply=True, find_collisions returns empty."""
        self._setup_collision(tmp_path)

        dedup(tmp_path, apply=True)
        after = find_collisions(tmp_path)

        assert after == {}, (
            f"After apply=True, find_collisions should return empty. Got: {after}"
        )

    def test_apply_deleted_count_equals_stray_count(self, tmp_path):
        """result['deleted'] == number of stray files removed."""
        self._setup_collision(tmp_path)

        result = dedup(tmp_path, apply=True)

        assert result["deleted"] == 1, (
            f"deleted should be 1 (one stray removed), got: {result['deleted']}"
        )

    def test_apply_resolved_nonzero(self, tmp_path):
        """result['resolved'] counts collisions that were successfully resolved."""
        self._setup_collision(tmp_path)

        result = dedup(tmp_path, apply=True)

        assert result["resolved"] >= 1, (
            f"resolved should be >= 1 after apply, got: {result['resolved']}"
        )

    def test_apply_canonical_content_unchanged(self, tmp_path):
        """Canonical file content must be byte-identical after apply."""
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        canon_content = _truth_atom("NS.W1", "W1", extra="content_hash: canon123")
        _write(canonical, canon_content)
        _write(stray, _truth_atom("NS.W1", "W1"))

        dedup(tmp_path, apply=True)

        assert canonical.read_text(encoding="utf-8") == canon_content, (
            "Canonical file content must not be modified by dedup"
        )


# ---------------------------------------------------------------------------
# 5. dedup apply=True + backup_dir
# ---------------------------------------------------------------------------

class TestDedupBackup:
    def _setup_collision(self, tmp_path):
        """Return canonical, stray paths + stray content string."""
        stray_content = _truth_atom("NS.W1", "W1", extra="content_hash: stray456")
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, stray_content)
        return canonical, stray, stray_content

    def test_backup_dir_is_created(self, tmp_path):
        """backup_dir is created when backup_dir is provided."""
        self._setup_collision(tmp_path)
        backup_dir = tmp_path / "backup"

        dedup(tmp_path, apply=True, backup_dir=backup_dir)

        assert backup_dir.exists(), "backup_dir must be created"

    def test_backup_dir_contains_deleted_stray(self, tmp_path):
        """backup_dir contains at least one .md file after apply."""
        self._setup_collision(tmp_path)
        backup_dir = tmp_path / "backup"

        dedup(tmp_path, apply=True, backup_dir=backup_dir)

        backup_files = list(backup_dir.rglob("*.md"))
        assert len(backup_files) >= 1, f"No backup files found in backup_dir: {backup_dir}"

    def test_backup_bytes_match_stray_original(self, tmp_path):
        """Backed-up file bytes must equal the stray's original content."""
        canonical, stray, stray_content = self._setup_collision(tmp_path)
        original_bytes = stray_content.encode("utf-8")
        backup_dir = tmp_path / "backup"

        dedup(tmp_path, apply=True, backup_dir=backup_dir)

        backup_files = list(backup_dir.rglob("*.md"))
        assert len(backup_files) >= 1, "No backup files found"
        backup_content = backup_files[0].read_bytes()
        assert backup_content == original_bytes, (
            "Backup file bytes do not match stray original bytes."
        )

    def test_backed_up_equals_deleted(self, tmp_path):
        """result['backed_up'] == result['deleted'] when backup_dir provided."""
        self._setup_collision(tmp_path)
        backup_dir = tmp_path / "backup"

        result = dedup(tmp_path, apply=True, backup_dir=backup_dir)

        assert result["backed_up"] == result["deleted"], (
            f"backed_up ({result['backed_up']}) != deleted ({result['deleted']})"
        )
        assert result["backed_up"] >= 1, "backed_up should be >= 1"

    def test_backup_preserves_relative_path(self, tmp_path):
        """Backup preserves stray's relative path under backup_dir."""
        self._setup_collision(tmp_path)
        backup_dir = tmp_path / "backup"

        dedup(tmp_path, apply=True, backup_dir=backup_dir)

        # stray was at truths/W1.md -> backup at backup_dir/truths/W1.md
        expected = backup_dir / "truths" / "W1.md"
        assert expected.exists(), (
            f"Expected backup at {expected}, backup_dir contents: "
            f"{list(backup_dir.rglob('*'))}"
        )

    def test_no_backup_dir_backed_up_zero(self, tmp_path):
        """Without backup_dir, backed_up == 0."""
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, _truth_atom("NS.W1", "W1"))

        result = dedup(tmp_path, apply=True)

        assert result["backed_up"] == 0, (
            f"Without backup_dir, backed_up should be 0, got: {result['backed_up']}"
        )


# ---------------------------------------------------------------------------
# 6. Ambiguous case
# ---------------------------------------------------------------------------

class TestDedupAmbiguous:
    def _setup_ambiguous(self, tmp_path):
        """Both copies in paths that do NOT contain the namespace 'NS'."""
        file_a = tmp_path / "a" / "W1.md"
        file_b = tmp_path / "b" / "W1.md"
        _write(file_a, _truth_atom("NS.W1", "W1"))
        _write(file_b, _truth_atom("NS.W1", "W1"))
        return file_a, file_b

    def test_ambiguous_does_not_delete_either_file(self, tmp_path):
        """When no path contains namespace, NEITHER file is deleted."""
        file_a, file_b = self._setup_ambiguous(tmp_path)

        dedup(tmp_path, apply=True)

        assert file_a.exists(), "file_a must not be deleted (ambiguous)"
        assert file_b.exists(), "file_b must not be deleted (ambiguous)"

    def test_ambiguous_count_nonzero(self, tmp_path):
        """result['ambiguous'] >= 1 for an ambiguous collision."""
        self._setup_ambiguous(tmp_path)

        result = dedup(tmp_path, apply=True)

        assert result["ambiguous"] >= 1, (
            f"ambiguous should be >= 1, got: {result['ambiguous']}"
        )

    def test_ambiguous_id_in_ambiguous_ids_list(self, tmp_path):
        """The ambiguous id appears in result['ambiguous_ids']."""
        self._setup_ambiguous(tmp_path)

        result = dedup(tmp_path, apply=True)

        assert "NS.W1" in result["ambiguous_ids"], (
            f"NS.W1 should appear in ambiguous_ids: {result['ambiguous_ids']}"
        )

    def test_ambiguous_deleted_zero(self, tmp_path):
        """Fully ambiguous collision -> deleted == 0 (nothing removed)."""
        self._setup_ambiguous(tmp_path)

        result = dedup(tmp_path, apply=True)

        assert result["deleted"] == 0, (
            f"deleted should be 0 for fully ambiguous case, got: {result['deleted']}"
        )

    def test_mixed_resolvable_and_ambiguous(self, tmp_path):
        """One resolvable + one ambiguous collision -> correct independent counts."""
        # Resolvable: NS.W1 with one path containing 'NS'
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, _truth_atom("NS.W1", "W1"))
        # Ambiguous: Other.W2 in two non-namespace paths
        file_a = tmp_path / "x" / "W2.md"
        file_b = tmp_path / "y" / "W2.md"
        _write(file_a, _truth_atom("Other.W2", "W2"))
        _write(file_b, _truth_atom("Other.W2", "W2"))

        result = dedup(tmp_path, apply=True)

        assert result["deleted"] >= 1, "At least one stray should be deleted (resolvable)"
        assert result["ambiguous"] >= 1, "At least one collision should be ambiguous"
        assert "Other.W2" in result["ambiguous_ids"], "Other.W2 should be in ambiguous_ids"
        # Ambiguous files must still exist
        assert file_a.exists(), "Ambiguous file_a must not be deleted"
        assert file_b.exists(), "Ambiguous file_b must not be deleted"


# ---------------------------------------------------------------------------
# 7. main CLI
# ---------------------------------------------------------------------------

class TestMainCli:
    def _setup_collision(self, tmp_path):
        canonical = tmp_path / "_meta_truths" / "NS_Model" / "truths" / "W1.md"
        stray = tmp_path / "truths" / "W1.md"
        _write(canonical, _truth_atom("NS.W1", "W1"))
        _write(stray, _truth_atom("NS.W1", "W1"))
        return canonical, stray

    def test_main_dry_run_exits_zero(self, tmp_path):
        """main([root]) dry-run -> exit 0."""
        self._setup_collision(tmp_path)
        exit_code = main([str(tmp_path)])
        assert exit_code == 0, f"main dry-run should exit 0, got {exit_code}"

    def test_main_dry_run_deletes_nothing(self, tmp_path):
        """main([root]) dry-run -> both files still exist on disk."""
        canonical, stray = self._setup_collision(tmp_path)
        main([str(tmp_path)])
        assert canonical.exists(), "Canonical must survive main dry-run"
        assert stray.exists(), "Stray must survive main dry-run"

    def test_main_apply_exits_zero(self, tmp_path):
        """main([root, '--apply']) -> exit 0."""
        self._setup_collision(tmp_path)
        exit_code = main([str(tmp_path), "--apply"])
        assert exit_code == 0, f"main --apply should exit 0, got {exit_code}"

    def test_main_apply_resolves_collision(self, tmp_path):
        """main([root, '--apply']) -> stray deleted, find_collisions empty."""
        canonical, stray = self._setup_collision(tmp_path)
        main([str(tmp_path), "--apply"])
        assert not stray.exists(), "Stray must be deleted after main --apply"
        assert canonical.exists(), "Canonical must survive main --apply"
        assert find_collisions(tmp_path) == {}, (
            "find_collisions should return empty after main --apply"
        )

    def test_main_invalid_root_exits_two(self, tmp_path):
        """main([nonexistent_path]) -> exit 2 (root not a dir)."""
        nonexistent = str(tmp_path / "no_such_dir")
        exit_code = main([nonexistent])
        assert exit_code == 2, f"Expected exit 2 for invalid root, got {exit_code}"

    def test_main_backup_dir_arg(self, tmp_path):
        """main([root, '--apply', '--backup-dir', bdir]) -> creates backup_dir."""
        self._setup_collision(tmp_path)
        backup_dir = tmp_path / "bk"
        exit_code = main([str(tmp_path), "--apply", "--backup-dir", str(backup_dir)])
        assert exit_code == 0, f"main with --backup-dir should exit 0, got {exit_code}"
        assert backup_dir.exists(), "backup_dir must be created by main --backup-dir"

    def test_main_ambiguous_warns_to_stderr(self, tmp_path, capsys):
        """When ambiguous_ids non-empty, main prints WARNING to stderr."""
        file_a = tmp_path / "a" / "W1.md"
        file_b = tmp_path / "b" / "W1.md"
        _write(file_a, _truth_atom("NS.W1", "W1"))
        _write(file_b, _truth_atom("NS.W1", "W1"))

        main([str(tmp_path), "--apply"])
        captured = capsys.readouterr()

        assert "WARNING" in captured.err or "warning" in captured.err.lower(), (
            f"Expected WARNING in stderr for ambiguous_ids, got: {captured.err!r}"
        )
