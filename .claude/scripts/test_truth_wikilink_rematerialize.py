"""
test_truth_wikilink_rematerialize.py — RED tests for BL-451 AC-2a

Tests for truth_wikilink_rematerialize.py (does NOT exist yet -> RED/ModuleNotFoundError).
Verifies: build_id_path_map + rematerialize behaviour.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

# This import MUST fail (ModuleNotFoundError) until GREEN builds the module.
from truth_wikilink_rematerialize import build_id_path_map, rematerialize  # noqa: E402


# ─── Helper ───────────────────────────────────────────────────────────────────

def make_truth_atom(
    directory: Path,
    filename: str,
    atom_id: str,
    local_id: str,
    edges: list[dict] | None = None,
    stale_section: str | None = None,
    extra_body: str = "",
    extra_fm: str = "",
) -> Path:
    """Write a truth-type atom .md file and return its path.

    Args:
        directory:     Parent directory to place the file in.
        filename:      File name (e.g. "A1.md").
        atom_id:       Full atom id (e.g. "NS.A1").
        local_id:      Local id (e.g. "A1").
        edges:         List of edge dicts; None -> omit edges: key entirely.
        stale_section: If given, appended as the ## Verwandte Wahrheiten section.
        extra_body:    Extra body text inserted BEFORE the stale section.
        extra_fm:      Extra frontmatter lines (YAML, without leading/trailing ---).
    """
    directory.mkdir(parents=True, exist_ok=True)

    # Build edges YAML block
    if edges is None:
        edges_block = ""
    elif len(edges) == 0:
        edges_block = "edges: []\n"
    else:
        lines = ["edges:"]
        for e in edges:
            first = True
            for k, v in e.items():
                prefix = "  - " if first else "    "
                lines.append(f"{prefix}{k}: {v}")
                first = False
        edges_block = "\n".join(lines) + "\n"

    extra_fm_block = (extra_fm.strip() + "\n") if extra_fm.strip() else ""

    frontmatter = (
        "---\n"
        f"type: truth\n"
        f"id: {atom_id}\n"
        f"local_id: {local_id}\n"
        f"{edges_block}"
        f"{extra_fm_block}"
        "---\n"
    )

    body = extra_body
    if stale_section is not None:
        body += stale_section

    path = directory / filename
    path.write_text(frontmatter + body, encoding="utf-8")
    return path


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestBuildIdPathMap:
    """Smoke-tests for build_id_path_map."""

    def test_finds_truth_atoms(self, tmp_path: Path) -> None:
        make_truth_atom(tmp_path, "A1.md", "NS.A1", "A1")
        make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1")

        result = build_id_path_map(tmp_path)

        assert "NS.A1" in result
        assert "NS.B1" in result

    def test_ignores_non_truth_atoms(self, tmp_path: Path) -> None:
        # Write a non-truth atom (type: view)
        p = tmp_path / "V1.md"
        p.write_text("---\ntype: view\nid: NS.V1\n---\n", encoding="utf-8")

        result = build_id_path_map(tmp_path)

        assert "NS.V1" not in result

    def test_path_values_are_absolute(self, tmp_path: Path) -> None:
        make_truth_atom(tmp_path, "A1.md", "NS.A1", "A1")

        result = build_id_path_map(tmp_path)

        assert result["NS.A1"].is_absolute()


class TestReplacesStaleSection:
    """test_replaces_stale_section: stale body-section is replaced with correct link."""

    def test_replaces_stale_section(self, tmp_path: Path) -> None:
        atom_b = make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1", edges=None)

        stale = "## Verwandte Wahrheiten\n- Verwandt: [[Backlog.W9|W9]]\n"
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.B1"}],
            stale_section=stale,
        )

        result = rematerialize(tmp_path, apply=True)

        content = atom_a.read_text(encoding="utf-8")
        # Old stale link must be gone
        assert "Backlog.W9" not in content
        # New link must point to B1.md (path-form)
        assert "B1.md" in content
        assert "## Verwandte Wahrheiten" in content

    def test_link_is_path_form(self, tmp_path: Path) -> None:
        """The link target (before |) is a relative path to B's .md, not the id."""
        atom_b = make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1", edges=None)
        stale = "## Verwandte Wahrheiten\n- Verwandt: [[Backlog.W9|W9]]\n"
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.B1"}],
            stale_section=stale,
        )

        rematerialize(tmp_path, apply=True)

        content = atom_a.read_text(encoding="utf-8")
        # Extract the first [[...]] in the section
        import re
        section_start = content.index("## Verwandte Wahrheiten")
        section = content[section_start:]
        m = re.search(r"\[\[([^\]|]+)\|", section)
        assert m is not None, "No wikilink found in section"
        link_target = m.group(1)
        # Must be a relative path containing "/" and ending with ".md"
        assert "/" in link_target or link_target.endswith(".md"), (
            f"Expected path-form link target, got: {link_target!r}"
        )
        assert link_target.endswith(".md"), (
            f"Expected .md suffix in link target, got: {link_target!r}"
        )
        # Must NOT be the bare id form
        assert link_target != "NS.B1"


def _extract_body(content: str) -> str:
    """Extract the body of a truth atom (everything after the closing frontmatter ---)."""
    # Content starts with --- frontmatter --- body.
    # Split on the second occurrence of \n---\n (or end of "---\n" at position 3+).
    # Strategy: find the first --- at pos 0, then find the next ---\n after that.
    if not content.startswith("---"):
        return content
    # Find the closing --- of frontmatter
    close_pos = content.find("\n---\n", 3)
    if close_pos == -1:
        # Try --- at end of file
        close_pos = content.find("\n---", 3)
        if close_pos == -1:
            return content
        return content[close_pos + 4:]
    return content[close_pos + 5:]  # skip \n---\n (5 chars)


def _get_verwandte_section(body: str) -> str:
    """Return the text of the ## Verwandte Wahrheiten section (until next ## or EOF)."""
    import re
    m = re.search(r"^## Verwandte Wahrheiten\s*$(.*?)(?=^##|\Z)", body, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(0)
    return ""


class TestDanglingEdgeSkipped:
    """test_dangling_edge_skipped: unresolvable ziel produces no body link."""

    def test_dangling_edge_skipped(self, tmp_path: Path) -> None:
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.NICHTDA"}],
        )

        rematerialize(tmp_path, apply=True)

        content = atom_a.read_text(encoding="utf-8")
        body = _extract_body(content)
        section = _get_verwandte_section(body)

        # The ## Verwandte Wahrheiten section in the BODY must contain NO
        # "- Verwandt:" line that references the dangling target.
        # (Frontmatter may still contain NS.NICHTDA in edges: — that is OK.)
        import re
        verwandt_lines = [
            line for line in section.splitlines()
            if re.match(r"\s*-\s*Verwandt:", line)
        ]
        dangling_links = [l for l in verwandt_lines if "NS.NICHTDA" in l]
        assert dangling_links == [], (
            f"Body section must not link dangling target NS.NICHTDA, "
            f"but found: {dangling_links!r}"
        )

    def test_dangling_produces_no_section(self, tmp_path: Path) -> None:
        """If all edges are dangling, no ## Verwandte Wahrheiten header in the BODY."""
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.GHOST"}],
        )

        rematerialize(tmp_path, apply=True)

        content = atom_a.read_text(encoding="utf-8")
        body = _extract_body(content)
        assert "## Verwandte Wahrheiten" not in body, (
            f"Body must not contain section header when all edges are dangling.\n"
            f"Body was:\n{body!r}"
        )


class TestOrphanSectionRemoved:
    """test_orphan_section_removed: stale section with empty/dangling edges is removed from BODY."""

    def test_orphan_section_removed_empty_edges(self, tmp_path: Path) -> None:
        stale = "\n## Verwandte Wahrheiten\n- Verwandt: [[OldLink|OL]]\n"
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[],  # empty edges list
            stale_section=stale,
        )

        rematerialize(tmp_path, apply=True)

        content = atom_a.read_text(encoding="utf-8")
        body = _extract_body(content)
        assert "## Verwandte Wahrheiten" not in body, (
            f"Body must not contain section header when edges are empty.\n"
            f"Body was:\n{body!r}"
        )

    def test_orphan_section_removed_dangling_only(self, tmp_path: Path) -> None:
        stale = "\n## Verwandte Wahrheiten\n- Verwandt: [[OldLink|OL]]\n"
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.GHOST"}],  # dangling only
            stale_section=stale,
        )

        rematerialize(tmp_path, apply=True)

        content = atom_a.read_text(encoding="utf-8")
        body = _extract_body(content)
        assert "## Verwandte Wahrheiten" not in body, (
            f"Body must not contain section header when all edges are dangling.\n"
            f"Body was:\n{body!r}"
        )


class TestFrontmatterByteIdentical:
    """test_frontmatter_byte_identical: rematerialize NEVER touches frontmatter."""

    def test_frontmatter_byte_identical(self, tmp_path: Path) -> None:
        """Frontmatter block (incl. both --- delimiters) must be byte-identical before/after.

        Fixture has a dangling edge in the frontmatter `edges:` list AND a
        multi-line `text:` field to ensure even complex frontmatter is left alone.
        """
        atom_b = make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1", edges=None)

        # edges contains one resolvable + one dangling target
        edges = [{"ziel": "NS.B1"}, {"ziel": "NS.DANGLING"}]
        # multi-line extra_fm to stress-test frontmatter preservation
        extra_fm = "text: |\n  Line one of the multi-line text.\n  Line two here."
        stale = "## Verwandte Wahrheiten\n- Verwandt: [[Stale.Link|SL]]\n"
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=edges,
            stale_section=stale,
            extra_fm=extra_fm,
        )

        original_content = atom_a.read_text(encoding="utf-8")
        # Extract frontmatter block: everything from start through closing ---\n
        # The file starts with "---\n...\n---\n".  Split on "\n---\n" once (maxsplit=1)
        # to separate frontmatter from body.
        split_marker = "\n---\n"
        split_pos = original_content.find(split_marker, 3)
        assert split_pos != -1, "Test fixture must have closing frontmatter ---"
        original_fm = original_content[: split_pos + len(split_marker)]

        rematerialize(tmp_path, apply=True)

        new_content = atom_a.read_text(encoding="utf-8")
        new_split_pos = new_content.find(split_marker, 3)
        assert new_split_pos != -1, "After rematerialize, file must still have closing ---"
        new_fm = new_content[: new_split_pos + len(split_marker)]

        assert new_fm == original_fm, (
            "Frontmatter must be byte-identical after rematerialize.\n"
            f"BEFORE:\n{original_fm!r}\n\nAFTER:\n{new_fm!r}"
        )

        # Sanity: the dangling edge must still be in the frontmatter (not stripped)
        assert "NS.DANGLING" in new_fm, (
            "Dangling edge must remain in frontmatter (BL-479 scope, not ours)."
        )

        # Sanity: the body section must NOT link to the dangling target
        new_body = new_content[new_split_pos + len(split_marker):]
        new_section = _get_verwandte_section(new_body)
        assert "NS.DANGLING" not in new_section, (
            f"Body section must not link dangling target, but section was:\n{new_section!r}"
        )


class TestDryRun:
    """test_dry_run_no_write: apply=False must not change files."""

    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        atom_b = make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1", edges=None)
        stale = "## Verwandte Wahrheiten\n- Verwandt: [[Backlog.W9|W9]]\n"
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.B1"}],
            stale_section=stale,
        )

        original_a = atom_a.read_text(encoding="utf-8")
        mtime_before = atom_a.stat().st_mtime

        result = rematerialize(tmp_path, apply=False)

        # File content must be unchanged
        assert atom_a.read_text(encoding="utf-8") == original_a
        # Mtime must not have changed
        assert atom_a.stat().st_mtime == mtime_before
        # updated must be 0, would_update > 0
        assert result["updated"] == 0
        assert result["would_update"] > 0

    def test_dry_run_counts_are_accurate(self, tmp_path: Path) -> None:
        atom_b = make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1", edges=None)
        make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.B1"}],
        )

        result = rematerialize(tmp_path, apply=False)

        assert result["would_update"] >= 1
        assert result["updated"] == 0


class TestIdempotent:
    """test_idempotent: second apply has updated==0."""

    def test_idempotent(self, tmp_path: Path) -> None:
        atom_b = make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1", edges=None)
        stale = "## Verwandte Wahrheiten\n- Verwandt: [[Backlog.W9|W9]]\n"
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.B1"}],
            stale_section=stale,
        )

        result1 = rematerialize(tmp_path, apply=True)
        assert result1["updated"] >= 1

        result2 = rematerialize(tmp_path, apply=True)
        assert result2["updated"] == 0


class TestPreservesFrontmatterAndBodyAbove:
    """test_preserves_frontmatter_and_body_above: frontmatter + body before section untouched."""

    def test_preserves_frontmatter_and_body_above(self, tmp_path: Path) -> None:
        atom_b = make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1", edges=None)

        # Extra body text BEFORE the wikilink section
        extra_body = "\nHere is some important body text.\nSecond line of body.\n\n"
        stale = "## Verwandte Wahrheiten\n- Verwandt: [[Backlog.W9|W9]]\n"
        atom_a = make_truth_atom(
            tmp_path,
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.B1"}],
            stale_section=stale,
            extra_body=extra_body,
            extra_fm="text: some frontmatter value",
        )

        # Capture the original frontmatter exactly
        original_content = atom_a.read_text(encoding="utf-8")
        # Split at first --- after opening ---
        parts = original_content.split("---", 2)
        original_fm_raw = "---" + parts[1] + "---"

        rematerialize(tmp_path, apply=True)

        new_content = atom_a.read_text(encoding="utf-8")
        new_parts = new_content.split("---", 2)
        new_fm_raw = "---" + new_parts[1] + "---"

        # Frontmatter must be byte-identical
        assert new_fm_raw == original_fm_raw, (
            f"Frontmatter changed!\nBefore: {original_fm_raw!r}\nAfter:  {new_fm_raw!r}"
        )

        # Body text before the section must still be present
        assert "Here is some important body text." in new_content
        assert "Second line of body." in new_content

        # Section must now contain path-form link to B1.md, not old stale link
        assert "Backlog.W9" not in new_content
        assert "B1.md" in new_content


class TestBackup:
    """test_backup: backup_dir+apply copies changed files."""

    def test_backup(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        atom_b = make_truth_atom(tmp_path / "atoms", "B1.md", "NS.B1", "B1", edges=None)
        stale = "## Verwandte Wahrheiten\n- Verwandt: [[Backlog.W9|W9]]\n"
        atom_a = make_truth_atom(
            tmp_path / "atoms",
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.B1"}],
            stale_section=stale,
        )

        result = rematerialize(tmp_path / "atoms", apply=True, backup_dir=backup_dir)

        assert result["updated"] >= 1
        assert result["backed_up"] == result["updated"]

        # At least one backup file must exist
        backed_up_files = list(backup_dir.rglob("*.md"))
        assert len(backed_up_files) >= 1, f"Expected backup files, found none in {backup_dir}"

    def test_backup_not_created_on_dry_run(self, tmp_path: Path) -> None:
        """Backup files must NOT be created during dry-run (apply=False)."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        atom_b = make_truth_atom(tmp_path / "atoms", "B1.md", "NS.B1", "B1", edges=None)
        stale = "## Verwandte Wahrheiten\n- Verwandt: [[Backlog.W9|W9]]\n"
        atom_a = make_truth_atom(
            tmp_path / "atoms",
            "A1.md",
            "NS.A1",
            "A1",
            edges=[{"ziel": "NS.B1"}],
            stale_section=stale,
        )

        result = rematerialize(tmp_path / "atoms", apply=False, backup_dir=backup_dir)

        assert result["backed_up"] == 0
        backed_up_files = list(backup_dir.rglob("*.md"))
        assert len(backed_up_files) == 0


class TestReturnCounts:
    """Verify the return dict always contains all expected keys with int values."""

    def test_return_dict_keys_present(self, tmp_path: Path) -> None:
        result = rematerialize(tmp_path, apply=False)

        expected_keys = {"scanned", "with_edges", "would_update", "updated", "backed_up"}
        assert expected_keys == set(result.keys()), (
            f"Missing or extra keys: got {set(result.keys())}"
        )

    def test_return_dict_values_are_ints(self, tmp_path: Path) -> None:
        result = rematerialize(tmp_path, apply=False)

        for k, v in result.items():
            assert isinstance(v, int), f"Key {k!r} has non-int value: {v!r}"

    def test_scanned_counts_all_truth_atoms(self, tmp_path: Path) -> None:
        make_truth_atom(tmp_path, "A1.md", "NS.A1", "A1", edges=None)
        make_truth_atom(tmp_path, "B1.md", "NS.B1", "B1", edges=None)

        result = rematerialize(tmp_path, apply=False)

        assert result["scanned"] >= 2
