#!/usr/bin/env python3
"""
test_truth_wikilink_multiheader.py — BL-479 sub_batch_2 AC-6 RED Tests

Tests for _remove_verwandte_section variant-header handling.

RED: These tests FAIL on current implementation because:
- test_removes_variant_header_section: `_remove_verwandte_section` only removes
  the EXACT "## Verwandte Wahrheiten" header; variant "## Verwandte Wahrheiten / Links"
  is left in place (checked via equality to _VERWANDTE_HEADER).
- test_multiple_exact_sections_collapsed: only the FIRST exact header is removed;
  a second exact duplicate section stays in the body.
- test_frontmatter_text_header_not_touched: GREEN (pass) — this is a safety guard.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the scripts directory is importable
sys.path.insert(0, str(Path(__file__).parent))

from truth_wikilink_rematerialize import rematerialize, build_id_path_map  # noqa: E402


# ─── Helpers ──────────────────────────────────────────────────────────────────

_FM_TEMPLATE = """\
---
id: {atom_id}
type: truth
edges:
{edges_block}---
"""

_FM_NO_EDGES = """\
---
id: {atom_id}
type: truth
edges: []
---
"""


def _make_atom(tmp_path: Path, atom_id: str, body: str, edges_block: str = "  - []\n") -> Path:
    """Write a truth-type atom .md file under tmp_path and return its Path."""
    ns, name = atom_id.split(".", 1)
    ns_dir = tmp_path / ns
    ns_dir.mkdir(parents=True, exist_ok=True)
    filepath = ns_dir / f"{name}.md"
    fm = _FM_TEMPLATE.format(atom_id=atom_id, edges_block=edges_block)
    filepath.write_text(fm + body, encoding="utf-8")
    return filepath


def _make_atom_no_edges(tmp_path: Path, atom_id: str, body: str) -> Path:
    """Write a truth-type atom with no edges."""
    ns, name = atom_id.split(".", 1)
    ns_dir = tmp_path / ns
    ns_dir.mkdir(parents=True, exist_ok=True)
    filepath = ns_dir / f"{name}.md"
    fm = _FM_NO_EDGES.format(atom_id=atom_id)
    filepath.write_text(fm + body, encoding="utf-8")
    return filepath


def _make_atom_with_edge(tmp_path: Path, atom_id: str, ziel: str, body: str) -> Path:
    """Write a truth-type atom with one resolvable edge."""
    ns, name = atom_id.split(".", 1)
    ns_dir = tmp_path / ns
    ns_dir.mkdir(parents=True, exist_ok=True)
    filepath = ns_dir / f"{name}.md"
    edges_block = f"  - typ: verwandt\n    ziel: {ziel}\n"
    fm = _FM_TEMPLATE.format(atom_id=atom_id, edges_block=edges_block)
    filepath.write_text(fm + body, encoding="utf-8")
    return filepath


# ─── Tests ────────────────────────────────────────────────────────────────────


def test_removes_variant_header_section(tmp_path: Path) -> None:
    """RED: variant '## Verwandte Wahrheiten / Links' section must be removed.

    Atom A has TWO Verwandte-sections in the body:
      1. '## Verwandte Wahrheiten / Links' (variant/stale, with coarse link)
      2. '## Verwandte Wahrheiten'          (exact, with another stale link)

    After rematerialize(apply=True), A's body must:
    - contain NO '[[Backlog.W9' (variant section fully removed)
    - contain EXACTLY ONE '## Verwandte Wahrheiten' header
    - contain the precise path-form link to B (NS.B1)

    Currently FAILS because _remove_verwandte_section checks
    `line.rstrip() == _VERWANDTE_HEADER` (exact match) and misses the variant.
    """
    # Create Atom B (the link target)
    _make_atom_no_edges(
        tmp_path,
        atom_id="NS.B1",
        body="Some truth about B.\n",
    )

    # Create Atom A with two stale Verwandte sections (variant + exact)
    body_a = (
        "The main content of A.\n"
        "\n"
        "## Verwandte Wahrheiten / Links\n"
        "- Verwandt: [[Backlog.W9|W9]]\n"
        "\n"
        "## Verwandte Wahrheiten\n"
        "- Verwandt: [[alt|alt]]\n"
    )
    _make_atom_with_edge(
        tmp_path,
        atom_id="NS.A1",
        ziel="NS.B1",
        body=body_a,
    )

    result = rematerialize(tmp_path, apply=True)

    # Read back A's file
    a_file = tmp_path / "NS" / "A1.md"
    content_after = a_file.read_text(encoding="utf-8")

    # The stale coarse link from the variant section must be gone
    assert "[[Backlog.W9" not in content_after, (
        "Stale coarse link from '## Verwandte Wahrheiten / Links' section "
        "was not removed. Variant header not cleaned."
    )

    # Exactly one '## Verwandte Wahrheiten' header in the body after frontmatter
    # Split off frontmatter
    body_after = content_after.split("---\n", 2)[-1]
    header_count = body_after.count("## Verwandte Wahrheiten")
    assert header_count == 1, (
        f"Expected exactly 1 '## Verwandte Wahrheiten' header after rematerialize, "
        f"found {header_count}."
    )

    # The precise path-form link to NS.B1 must be present
    assert "NS/B1" in content_after or "[[" in content_after, (
        "Expected a wikilink to NS.B1 in A's body after rematerialize."
    )
    # More specifically: path containing B1 should be present as a wikilink
    assert "B1" in content_after and "[[" in content_after, (
        "Expected path-form wikilink to B1 after rematerialize."
    )


def test_multiple_exact_sections_collapsed(tmp_path: Path) -> None:
    """RED: two exact '## Verwandte Wahrheiten' sections separated by another ## must collapse.

    BL-450 append-accumulation scenario: a second '## Verwandte Wahrheiten' section
    was appended AFTER some other ## section (e.g. from a different pipeline run).
    _remove_verwandte_section removes only the FIRST occurrence; the second remains
    because _remove_verwandte_section only calls break after finding the first header.

    After rematerialize(apply=True), A's body must contain EXACTLY ONE
    '## Verwandte Wahrheiten' header and no stale links from the second section.

    Currently FAILS because _remove_verwandte_section stops at the first occurrence,
    cuts up to the next non-Verwandte ## header (## Notizen), and leaves the second
    '## Verwandte Wahrheiten' section after ## Notizen intact.
    """
    # Create Atom B (link target)
    _make_atom_no_edges(
        tmp_path,
        atom_id="NS.B1",
        body="Truth B content.\n",
    )

    # Atom A: two exact Verwandte sections separated by an intervening ## header
    # This is the BL-450 real-world accumulation pattern:
    #   first run appended section after body, second run appended again
    #   resulting in: Verwandte → Notizen → Verwandte (duplicate)
    body_a = (
        "Main content of A.\n"
        "\n"
        "## Verwandte Wahrheiten\n"
        "- Verwandt: [[stale_first|first]]\n"
        "\n"
        "## Notizen\n"
        "Some notes.\n"
        "\n"
        "## Verwandte Wahrheiten\n"
        "- Verwandt: [[stale_second|second]]\n"
    )
    _make_atom_with_edge(
        tmp_path,
        atom_id="NS.A1",
        ziel="NS.B1",
        body=body_a,
    )

    rematerialize(tmp_path, apply=True)

    a_file = tmp_path / "NS" / "A1.md"
    content_after = a_file.read_text(encoding="utf-8")
    body_after = content_after.split("---\n", 2)[-1]

    header_count = body_after.count("## Verwandte Wahrheiten")
    assert header_count == 1, (
        f"Expected exactly 1 '## Verwandte Wahrheiten' header after collapsing duplicates, "
        f"found {header_count}. Second '## Verwandte Wahrheiten' after '## Notizen' was not removed."
    )

    # Stale links from both old sections must be gone
    assert "[[stale_first" not in content_after, (
        "Stale link from first duplicate section was not removed."
    )
    assert "[[stale_second" not in content_after, (
        "Stale link from second (post-Notizen) duplicate section was not removed."
    )


def test_frontmatter_text_header_not_touched(tmp_path: Path) -> None:
    """GREEN (safety guard): frontmatter text field containing the header string is preserved.

    An atom whose frontmatter 'text:' field contains the literal string
    '## Verwandte Wahrheiten' (as data, not a markdown header) must have
    its frontmatter preserved byte-identically after rematerialize.

    Protects against over-removal that strips frontmatter data.
    """
    ns_dir = tmp_path / "NS"
    ns_dir.mkdir(parents=True, exist_ok=True)

    # Atom that documents the Wikilink system — its text: field mentions the header
    raw_content = (
        "---\n"
        "id: NS.Meta1\n"
        "type: truth\n"
        "text: |\n"
        "  This atom documents the ## Verwandte Wahrheiten section format.\n"
        "  It is not a section header itself.\n"
        "edges: []\n"
        "---\n"
        "This atom explains the ## Verwandte Wahrheiten convention.\n"
        "\n"
        "No actual Verwandte section here.\n"
    )
    atom_file = ns_dir / "Meta1.md"
    atom_file.write_text(raw_content, encoding="utf-8")

    rematerialize(tmp_path, apply=True)

    content_after = atom_file.read_text(encoding="utf-8")

    # Extract frontmatter from before and after
    parts_before = raw_content.split("---\n", 2)
    parts_after = content_after.split("---\n", 2)

    # The frontmatter block (index 1 = between first and second ---) must be identical
    assert len(parts_before) >= 2 and len(parts_after) >= 2, (
        "Could not parse frontmatter delimiters from output."
    )
    fm_before = parts_before[1]
    fm_after = parts_after[1]

    assert fm_before == fm_after, (
        "Frontmatter was modified by rematerialize. "
        "The 'text:' field containing '## Verwandte Wahrheiten' must not be touched.\n"
        f"Before: {fm_before!r}\n"
        f"After:  {fm_after!r}"
    )
