#!/usr/bin/env python3
"""
test_truth_backref_column0_strip.py -- RED tests for column-0 strip bug (BL-489).

Bug: _strip_existing_referenced_by only skips INDENTED continuation lines after
referenced_by:.  When the block was previously written by keyword_edge_writer via
yaml.dump, the - by: items start at COLUMN 0 (no indent).  The inner while loop
exits immediately, leaving those items in the line list.  _insert_referenced_by
then treats them as continuation of the preceding keywords: section, and they are
absorbed into keywords on re-parse -> {by, kind} dict leakage.

RED: tests 1, 3, 4, 5 are expected to FAIL against the current implementation.
     test 2 is a regression guard that should PASS already (indented form).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

# Ensure scripts dir is on sys.path so bare module imports resolve.
_SCRIPTS = Path(__file__).parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import truth_backref_materialize
import truth_edge_backref
from truth_keyword_demerge import assert_keywords_type_pure


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_fm(content: str) -> dict:
    """yaml.safe_load the frontmatter from a full atom content string."""
    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert m, "No YAML frontmatter found in content"
    return yaml.safe_load(m.group(1)) or {}


def _write_atom(path: Path, fm: str, body: str = "Some body text.\n") -> None:
    """Write a truth atom file with --- delimiters."""
    path.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")


def _read_fm(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    return _parse_fm(content)


# ---------------------------------------------------------------------------
# Test 1: Unit -- _strip_existing_referenced_by removes column-0 block sequence
# ---------------------------------------------------------------------------

def test_strip_removes_column0_block_sequence():
    """RED: column-0 '- by:' items survive _strip_existing_referenced_by.

    yaml.dump renders referenced_by as a COLUMN-0 block sequence:
        referenced_by:
        - by: NS.A1
          kind: truth_edge

    The inner while loop only skips lines that startswith(' ') or startswith('\\t').
    Since '- by: NS.A1' is at column 0, the loop exits after the header and the
    - by: / kind: items are left in the output.
    """
    fm_text = (
        "type: truth\n"
        "id: NS.B1\n"
        "local_id: B1\n"
        "keywords:\n"
        "- alpha\n"
        "- beta\n"
        "referenced_by:\n"
        "- by: NS.A1\n"
        "  kind: truth_edge\n"
        "- by: NS.C9\n"
        "  kind: truth_edge\n"
        "seq: 0"
    )
    lines = fm_text.split("\n")
    result = truth_backref_materialize._strip_existing_referenced_by(lines)
    result_text = "\n".join(result)

    # These must survive the strip
    assert "keywords:" in result_text, "keywords: line disappeared"
    assert "- alpha" in result_text, "- alpha disappeared"
    assert "- beta" in result_text, "- beta disappeared"
    assert "seq: 0" in result_text, "seq: 0 disappeared"

    # These must NOT survive -- the whole referenced_by block (header + items)
    assert "referenced_by:" not in result_text, (
        "referenced_by: header survived strip"
    )
    assert "- by:" not in result_text, (
        f"column-0 '- by:' items survived strip -- bug reproduced: {result_text!r}"
    )
    assert "kind: truth_edge" not in result_text, (
        f"'kind: truth_edge' survived strip: {result_text!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: Unit -- _strip_existing_referenced_by removes INDENTED form
# ---------------------------------------------------------------------------

def test_strip_removes_indented_block_sequence():
    """Regression guard (expected GREEN): indented referenced_by is fully removed.

    When the block uses 2-space-indented items (the format _render_referenced_by
    produces), the inner while loop correctly skips them.
    """
    fm_text = (
        "type: truth\n"
        "id: NS.B1\n"
        "local_id: B1\n"
        "keywords:\n"
        "- alpha\n"
        "- beta\n"
        "referenced_by:\n"
        "  - by: NS.A1\n"
        "    kind: truth_edge\n"
        "  - by: NS.C9\n"
        "    kind: truth_edge\n"
        "seq: 0"
    )
    lines = fm_text.split("\n")
    result = truth_backref_materialize._strip_existing_referenced_by(lines)
    result_text = "\n".join(result)

    assert "keywords:" in result_text
    assert "- alpha" in result_text
    assert "- beta" in result_text
    assert "seq: 0" in result_text

    assert "referenced_by:" not in result_text, (
        "referenced_by: header survived strip (indented form)"
    )
    assert "- by:" not in result_text, (
        f"indented '- by:' survived strip: {result_text!r}"
    )
    assert "kind: truth_edge" not in result_text, (
        f"'kind: truth_edge' survived strip (indented): {result_text!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: Integration via _build_new_content
# ---------------------------------------------------------------------------

def test_build_new_content_no_keyword_corruption():
    """RED: _build_new_content leaks column-0 referenced_by items into keywords.

    Column-0 '- by: NS.OLD' survives strip -> gets absorbed into the keywords:
    section by _insert_referenced_by (which counts column-0 '- foo' as a
    continuation of the preceding list) -> keywords contains dict entries on
    yaml.safe_load of the result.
    """
    # Full atom content with column-0 keywords list + column-0 referenced_by
    # (yaml.dump style, as written by keyword_edge_writer)
    content = (
        "---\n"
        "type: truth\n"
        "id: NS.B1\n"
        "local_id: B1\n"
        "keywords:\n"
        "- alpha\n"
        "- beta\n"
        "referenced_by:\n"
        "- by: NS.OLD\n"
        "  kind: truth_edge\n"
        "seq: 0\n"
        "edges: []\n"
        "---\n"
        "Some body text.\n"
    )

    rb = [{"by": "NS.A1", "kind": "truth_edge"}]
    new_content = truth_backref_materialize._build_new_content(content, rb)
    assert new_content is not None, "_build_new_content returned None (no frontmatter)"

    fm_data = _parse_fm(new_content)
    kw = fm_data.get("keywords", [])

    # Must be exactly the original strings -- no dict leakage
    assert kw == ["alpha", "beta"], (
        f"keywords corrupted by column-0 strip bug: {kw!r} "
        f"(expected ['alpha', 'beta'])"
    )
    assert_keywords_type_pure(kw)  # raises AssertionError if any non-str

    # Sanity: referenced_by should contain exactly the new entry
    rb_out = fm_data.get("referenced_by", [])
    assert isinstance(rb_out, list), f"referenced_by not a list: {rb_out!r}"
    assert len(rb_out) == 1, (
        f"Expected 1 referenced_by entry, got {len(rb_out)}: {rb_out!r}"
    )
    assert rb_out[0].get("by") == "NS.A1", (
        f"referenced_by entry has wrong 'by': {rb_out[0]!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: Integration via materialize_edges (real cascade repro)
# ---------------------------------------------------------------------------

def test_materialize_edges_no_keyword_corruption(tmp_path):
    """RED: materialize_edges -> _build_new_content leaks column-0 referenced_by
    items into keywords when atom B already has a yaml.dump-style referenced_by
    block at column 0.

    This is the full BL-489 corruption class repro via the real call chain:
    materialize_edges -> _build_new_content -> _strip_existing_referenced_by
    -> _insert_referenced_by
    """
    # Atom A: has an edge pointing to B
    a_fm = (
        "type: truth\n"
        "id: NS.A1\n"
        "local_id: A1\n"
        "keywords:\n"
        "- source\n"
        "edges:\n"
        "- rel: relates_to\n"
        "  ziel: NS.B1\n"
        "seq: 0"
    )
    _write_atom(tmp_path / "atom_a.md", a_fm)

    # Atom B: already has a COLUMN-0 referenced_by block (stale, yaml.dump style)
    # plus column-0 string keywords list
    b_fm = (
        "type: truth\n"
        "id: NS.B1\n"
        "local_id: B1\n"
        "keywords:\n"
        "- alpha\n"
        "- beta\n"
        "referenced_by:\n"
        "- by: NS.OLD\n"
        "  kind: truth_edge\n"
        "seq: 0\n"
        "edges: []"
    )
    _write_atom(tmp_path / "atom_b.md", b_fm)

    result = truth_edge_backref.materialize_edges(tmp_path, apply=True)
    assert result["updated"] >= 1, (
        f"Expected at least 1 updated file, got {result} -- "
        f"fixture may not have triggered materialize"
    )

    fm_b = _read_fm(tmp_path / "atom_b.md")
    kw = fm_b.get("keywords", [])

    # RED: this will fail because {by, kind} dicts leaked into keywords
    assert_keywords_type_pure(kw)
    assert kw == ["alpha", "beta"], (
        f"keywords corrupted after materialize_edges: {kw!r} "
        f"(column-0 referenced_by items absorbed into keywords list)"
    )


# ---------------------------------------------------------------------------
# Test 5: Idempotency
# ---------------------------------------------------------------------------

def test_materialize_edges_idempotent_keywords(tmp_path):
    """RED: second materialize_edges run must not accumulate dict-keyword entries.

    If the first run already leaked dicts into keywords, the second run must
    not add more.  Additionally, keywords must still be type-pure after both
    runs -- which they will NOT be if the first run corrupted them.
    """
    a_fm = (
        "type: truth\n"
        "id: NS.A1\n"
        "local_id: A1\n"
        "keywords:\n"
        "- source\n"
        "edges:\n"
        "- rel: relates_to\n"
        "  ziel: NS.B1\n"
        "seq: 0"
    )
    _write_atom(tmp_path / "atom_a.md", a_fm)

    b_fm = (
        "type: truth\n"
        "id: NS.B1\n"
        "local_id: B1\n"
        "keywords:\n"
        "- alpha\n"
        "- beta\n"
        "referenced_by:\n"
        "- by: NS.OLD\n"
        "  kind: truth_edge\n"
        "seq: 0\n"
        "edges: []"
    )
    _write_atom(tmp_path / "atom_b.md", b_fm)

    # Run 1
    truth_edge_backref.materialize_edges(tmp_path, apply=True)
    # Run 2
    truth_edge_backref.materialize_edges(tmp_path, apply=True)

    fm_b = _read_fm(tmp_path / "atom_b.md")
    kw = fm_b.get("keywords", [])

    # RED: keywords will still have the dict entries that leaked in during run 1
    assert_keywords_type_pure(kw)
    assert kw == ["alpha", "beta"], (
        f"keywords corrupted / accumulated after 2 runs: {kw!r}"
    )
