#!/usr/bin/env python3
"""
RED-phase tests fuer truth_keyword_demerge.py (BL-xxx).

These tests MUST FAIL because truth_keyword_demerge.py does not exist yet.
All ModuleNotFoundError failures are expected RED signals.

Corruption shape (column-0 style, exact format from real atoms):
  keywords:
  - abgrenzung
  - analysieren
  - by: _R_orchestrate.W2
    kind: truth_edge
  - by: ModelBloat.W01
    kind: truth_edge
  referenced_by:
    - by: _R_orchestrate.W2
      kind: truth_edge

After demerge: keywords must be ONLY the string items; referenced_by, seq,
edges, text, body byte-identical.
"""
from __future__ import annotations

import re
import yaml
import pytest

from truth_keyword_demerge import (
    assert_keywords_type_pure,
    demerge_keywords_block,
    demerge,
    main,
)


# ---------------------------------------------------------------------------
# Shared fixture builders
# ---------------------------------------------------------------------------

CORRUPTED_COLUMN0 = (
    "---\n"
    "type: truth\n"
    "id: _R_orchestrate.W1\n"
    "local_id: W1\n"
    "text: 'W1 single line text'\n"
    "keywords:\n"
    "- abgrenzung\n"
    "- analysieren\n"
    "- by: _R_orchestrate.W2\n"
    "  kind: truth_edge\n"
    "- by: ModelBloat.W01\n"
    "  kind: truth_edge\n"
    "referenced_by:\n"
    "  - by: _R_orchestrate.W2\n"
    "    kind: truth_edge\n"
    "  - by: ModelBloat.W01\n"
    "    kind: truth_edge\n"
    "seq: 0\n"
    "edges:\n"
    "- rel: relates_to\n"
    "  ziel: _R_orchestrate.W2\n"
    "---\n"
    "body\n"
)

# Indented-style: list items at 2-space indent instead of column-0
CORRUPTED_INDENTED = (
    "---\n"
    "type: truth\n"
    "id: NS.X1\n"
    "local_id: X1\n"
    "text: 'X1 text'\n"
    "keywords:\n"
    "  - stringkw\n"
    "  - by: NS.X2\n"
    "    kind: truth_edge\n"
    "referenced_by:\n"
    "  - by: NS.X2\n"
    "    kind: truth_edge\n"
    "seq: 1\n"
    "edges: []\n"
    "---\n"
    "body x\n"
)

CLEAN_ATOM = (
    "---\n"
    "type: truth\n"
    "id: NS.Clean1\n"
    "local_id: Clean1\n"
    "text: 'clean atom'\n"
    "keywords:\n"
    "- alpha\n"
    "- beta\n"
    "referenced_by: []\n"
    "seq: 0\n"
    "edges: []\n"
    "---\n"
    "body clean\n"
)

MULTILINE_TEXT_CORRUPTED = (
    "---\n"
    "type: truth\n"
    "id: NS.ML1\n"
    "local_id: ML1\n"
    "text: |\n"
    "  Line one: core phrase intact.\n"
    "  Line two: more context.\n"
    "keywords:\n"
    "- kw1\n"
    "- by: NS.ML2\n"
    "  kind: truth_edge\n"
    "referenced_by:\n"
    "  - by: NS.ML2\n"
    "    kind: truth_edge\n"
    "seq: 2\n"
    "edges: []\n"
    "---\n"
    "body ml\n"
)

ALL_DICT_KEYWORDS = (
    "---\n"
    "type: truth\n"
    "id: NS.AllDict1\n"
    "local_id: AllDict1\n"
    "text: 'all dict kws'\n"
    "keywords:\n"
    "- by: NS.AD2\n"
    "  kind: truth_edge\n"
    "- by: NS.AD3\n"
    "  kind: truth_edge\n"
    "referenced_by:\n"
    "  - by: NS.AD2\n"
    "    kind: truth_edge\n"
    "  - by: NS.AD3\n"
    "    kind: truth_edge\n"
    "seq: 0\n"
    "edges: []\n"
    "---\n"
    "body ad\n"
)

NO_FRONTMATTER = "Just body text with no YAML frontmatter at all.\n"


def _extract_frontmatter(content: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert m is not None, f"No frontmatter found in:\n{content!r}"
    return m.group(1)


def _write_corrupted_atom(path, atom_id="NS.C1", extra_kw_dict=None):
    """Write a corrupted atom with one string keyword and one dict keyword."""
    ref_by_entry = f"  - by: NS.C2\n    kind: truth_edge\n"
    dict_kw = "- by: NS.C2\n  kind: truth_edge\n"
    extra_dict_block = ""
    extra_ref_block = ""
    if extra_kw_dict:
        by_val = extra_kw_dict["by"]
        extra_dict_block = f"- by: {by_val}\n  kind: truth_edge\n"
        extra_ref_block = f"  - by: {by_val}\n    kind: truth_edge\n"
    content = (
        "---\n"
        "type: truth\n"
        f"id: {atom_id}\n"
        "local_id: C1\n"
        "text: 'C1 text'\n"
        "keywords:\n"
        "- abgrenzung\n"
        + dict_kw
        + extra_dict_block
        + "referenced_by:\n"
        + ref_by_entry
        + extra_ref_block
        + "seq: 0\n"
        "edges: []\n"
        "---\n"
        "body\n"
    )
    path.write_text(content, encoding="utf-8")
    return content


def _write_clean_atom(path, atom_id="NS.Clean99"):
    content = (
        "---\n"
        "type: truth\n"
        f"id: {atom_id}\n"
        "local_id: C99\n"
        "text: 'clean'\n"
        "keywords:\n"
        "- only_strings\n"
        "referenced_by: []\n"
        "seq: 0\n"
        "edges: []\n"
        "---\n"
        "body clean\n"
    )
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# TestAssertKeywordsTypePure
# ---------------------------------------------------------------------------

class TestAssertKeywordsTypePure:
    def test_passes_on_all_strings(self):
        """All-string list -> no exception."""
        result = assert_keywords_type_pure(["alpha", "beta", "gamma"])
        assert result is None

    def test_passes_on_empty_list(self):
        """Empty list is pure (vacuously)."""
        result = assert_keywords_type_pure([])
        assert result is None

    def test_raises_on_dict_entry(self):
        """List containing a dict -> AssertionError, offender named."""
        offender = {"by": "_R_orchestrate.W2", "kind": "truth_edge"}
        with pytest.raises(AssertionError) as exc_info:
            assert_keywords_type_pure(["alpha", offender])
        # The error message must name the offender somehow
        msg = str(exc_info.value)
        assert "_R_orchestrate.W2" in msg or "truth_edge" in msg or "dict" in msg.lower(), (
            f"AssertionError does not name the offender. Got: {msg!r}"
        )

    def test_raises_names_all_offenders(self):
        """Multiple dict entries -> all offenders named in error."""
        off1 = {"by": "A.W1", "kind": "truth_edge"}
        off2 = {"by": "B.W2", "kind": "truth_edge"}
        with pytest.raises(AssertionError) as exc_info:
            assert_keywords_type_pure(["good", off1, off2])
        msg = str(exc_info.value)
        # At least one offender must be mentioned
        assert "A.W1" in msg or "B.W2" in msg or "dict" in msg.lower(), (
            f"AssertionError does not mention offenders. Got: {msg!r}"
        )

    def test_raises_on_list_with_only_dicts(self):
        """All dicts -> AssertionError."""
        with pytest.raises(AssertionError):
            assert_keywords_type_pure([
                {"by": "X.W1", "kind": "truth_edge"},
                {"by": "X.W2", "kind": "truth_edge"},
            ])


# ---------------------------------------------------------------------------
# TestDemergeKeywordsBlock
# ---------------------------------------------------------------------------

class TestDemergeKeywordsBlock:
    def test_drops_dicts_column0_style(self):
        """Column-0 style: '- by: X' at column 0, '  kind: Y' indented 2 -> removed.

        referenced_by's entries are INDENTED ('  - by:') and must survive, so we
        check that no COLUMN-0 dict-keyword line remains (keywords block only)."""
        result = demerge_keywords_block(CORRUPTED_COLUMN0)
        assert result is not None, "Expected non-None (content had dict keywords)"
        col0_by_lines = [ln for ln in result.splitlines() if ln.startswith("- by:")]
        assert col0_by_lines == [], (
            f"column-0 dict-keyword lines still present: {col0_by_lines!r}"
        )
        assert _no_kw_kind_lines(result), "keywords block still has a '  kind:' line"

    def test_drops_dicts_indented_style(self):
        """Indented style: '  - by: X' at 2-space indent, '    kind: Y' -> removed.

        Here keywords items AND referenced_by entries share the same indentation,
        so a raw string check is ambiguous; assert via parsed YAML that keywords is
        string-only while referenced_by stays intact."""
        result = demerge_keywords_block(CORRUPTED_INDENTED)
        assert result is not None, "Expected non-None (content had dict keywords)"
        parsed = yaml.safe_load(_extract_frontmatter(result))
        kw = parsed.get("keywords")
        assert kw == ["stringkw"], f"keywords not cleaned to string-only: {kw!r}"
        assert all(isinstance(x, str) for x in kw), f"keywords has non-str: {kw!r}"
        rb = parsed.get("referenced_by")
        assert rb and any(e.get("by") == "NS.X2" for e in rb), (
            f"referenced_by must stay intact (NS.X2): {rb!r}"
        )

    def test_keeps_string_keywords(self):
        """String keywords must survive demerge."""
        result = demerge_keywords_block(CORRUPTED_COLUMN0)
        assert result is not None
        assert "- abgrenzung" in result
        assert "- analysieren" in result

    def test_output_valid_yaml_keywords_string_list(self):
        """After demerge, frontmatter is valid YAML and keywords is a string-only list."""
        result = demerge_keywords_block(CORRUPTED_COLUMN0)
        assert result is not None
        fm = _extract_frontmatter(result)
        parsed = yaml.safe_load(fm)
        assert parsed is not None, "yaml.safe_load returned None after demerge"
        kw = parsed.get("keywords")
        assert isinstance(kw, list), f"keywords not a list: {kw!r}"
        assert all(isinstance(x, str) for x in kw), f"keywords contains non-str: {kw!r}"
        assert set(kw) == {"abgrenzung", "analysieren"}, (
            f"Unexpected keywords content: {kw!r}"
        )

    def test_referenced_by_block_fully_intact(self):
        """referenced_by block must survive completely unchanged."""
        result = demerge_keywords_block(CORRUPTED_COLUMN0)
        assert result is not None
        fm = _extract_frontmatter(result)
        parsed = yaml.safe_load(fm)
        rb = parsed.get("referenced_by")
        assert rb is not None, "referenced_by block missing after demerge"
        assert len(rb) == 2, f"referenced_by should have 2 entries, got {len(rb)}: {rb!r}"
        by_values = {entry["by"] for entry in rb}
        assert "_R_orchestrate.W2" in by_values, "referenced_by lost _R_orchestrate.W2 entry"
        assert "ModelBloat.W01" in by_values, "referenced_by lost ModelBloat.W01 entry"
        for entry in rb:
            assert entry.get("kind") == "truth_edge", (
                f"referenced_by entry missing kind: {entry!r}"
            )

    def test_seq_id_edges_text_intact(self):
        """seq, id, edges, text fields must survive demerge byte-identical."""
        result = demerge_keywords_block(CORRUPTED_COLUMN0)
        assert result is not None
        fm = _extract_frontmatter(result)
        parsed = yaml.safe_load(fm)
        assert parsed.get("seq") == 0, f"seq changed: {parsed.get('seq')!r}"
        assert parsed.get("id") == "_R_orchestrate.W1", f"id changed: {parsed.get('id')!r}"
        assert parsed.get("text") == "W1 single line text", (
            f"text changed: {parsed.get('text')!r}"
        )
        edges = parsed.get("edges")
        assert isinstance(edges, list) and len(edges) >= 1, f"edges changed: {edges!r}"
        assert edges[0].get("rel") == "relates_to", f"edges[0].rel changed: {edges[0]!r}"
        assert edges[0].get("ziel") == "_R_orchestrate.W2", (
            f"edges[0].ziel changed: {edges[0]!r}"
        )

    def test_multiline_text_preserved(self):
        """Multiline text: literal block scalar must survive demerge."""
        result = demerge_keywords_block(MULTILINE_TEXT_CORRUPTED)
        assert result is not None
        fm = _extract_frontmatter(result)
        parsed = yaml.safe_load(fm)
        text_val = parsed.get("text", "")
        assert "core phrase intact" in str(text_val), (
            f"multiline text not preserved. Got: {text_val!r}"
        )

    def test_byte_identical_except_dropped_lines(self):
        """Every original non-dict-keyword line is present in output in order;
        the '- by:' and '  kind:' dict keyword lines are absent."""
        content = CORRUPTED_COLUMN0
        result = demerge_keywords_block(content)
        assert result is not None

        # Lines that should be dropped (dict keyword entries in keywords block)
        dropped_patterns = [
            "- by: _R_orchestrate.W2",
            "- by: ModelBloat.W01",
        ]

        result_lines = result.splitlines()

        # Dropped lines must not appear in the keywords block
        for pattern in dropped_patterns:
            # The line must not appear among keyword-style entries
            # (referenced_by also has 'by:' entries but those are indented differently)
            matching_in_result = [
                ln for ln in result_lines
                if pattern.strip() == ln.strip() and not ln.startswith(" ")
            ]
            assert not matching_in_result, (
                f"Dict keyword line still present at column 0: {pattern!r}"
            )

        # Lines that must still be present
        must_be_present = [
            "type: truth",
            "id: _R_orchestrate.W1",
            "- abgrenzung",
            "- analysieren",
            "referenced_by:",
            "seq: 0",
            "body",
        ]
        for expected in must_be_present:
            found = any(expected in ln for ln in result_lines)
            assert found, f"Expected line not found in result: {expected!r}"

    def test_returns_none_on_clean_atom(self):
        """Clean atom (no dict keywords) -> None (no change needed)."""
        result = demerge_keywords_block(CLEAN_ATOM)
        assert result is None, (
            f"Expected None for clean atom, got modified content: {result!r}"
        )

    def test_idempotent_second_call_returns_none(self):
        """Applying demerge twice: second call returns None (already clean)."""
        first = demerge_keywords_block(CORRUPTED_COLUMN0)
        assert first is not None, "First call should return new content"
        second = demerge_keywords_block(first)
        assert second is None, (
            f"Second call should return None (idempotent), got: {second!r}"
        )

    def test_all_dict_keywords_becomes_empty_list(self):
        """Atom whose keywords are ALL dicts -> after demerge, keywords == []."""
        result = demerge_keywords_block(ALL_DICT_KEYWORDS)
        assert result is not None, "Expected non-None for all-dict-keyword atom"
        fm = _extract_frontmatter(result)
        parsed = yaml.safe_load(fm)
        kw = parsed.get("keywords")
        assert kw == [] or kw is None, (
            f"Expected empty keywords list, got: {kw!r}"
        )
        # Other fields intact
        assert parsed.get("id") == "NS.AllDict1", "id changed"
        assert parsed.get("seq") == 0, "seq changed"
        rb = parsed.get("referenced_by")
        assert rb is not None and len(rb) == 2, f"referenced_by changed: {rb!r}"

    def test_no_frontmatter_returns_none(self):
        """Content without YAML frontmatter -> None (nothing to do)."""
        result = demerge_keywords_block(NO_FRONTMATTER)
        assert result is None, (
            f"Expected None for content without frontmatter, got: {result!r}"
        )

    def test_string_only_keywords_indented_style_returns_none(self):
        """Indented-style atom that is already clean -> None."""
        clean_indented = (
            "---\n"
            "type: truth\n"
            "id: NS.CI1\n"
            "local_id: CI1\n"
            "text: 'clean indented'\n"
            "keywords:\n"
            "  - foo\n"
            "  - bar\n"
            "referenced_by: []\n"
            "seq: 0\n"
            "edges: []\n"
            "---\n"
            "body\n"
        )
        result = demerge_keywords_block(clean_indented)
        assert result is None, (
            f"Expected None for clean indented-style atom, got: {result!r}"
        )

    def test_body_after_frontmatter_byte_identical(self):
        """Body section (after closing ---) must be byte-identical."""
        result = demerge_keywords_block(CORRUPTED_COLUMN0)
        assert result is not None
        # Body is the text after the second '---\n'
        original_body = CORRUPTED_COLUMN0.split("---\n", 2)[2]
        result_body = result.split("---\n", 2)[2]
        assert result_body == original_body, (
            f"Body changed after demerge.\nOriginal: {original_body!r}\nResult: {result_body!r}"
        )


# ---------------------------------------------------------------------------
# TestDemergeDriver
# ---------------------------------------------------------------------------

class TestDemergeDriver:
    def test_dry_run_leaves_files_unchanged(self, tmp_path):
        """apply=False -> files unchanged on disk; would_update >= 1."""
        atom_path = tmp_path / "NS.C1.md"
        original = _write_corrupted_atom(atom_path)

        result = demerge(tmp_path, apply=False)

        assert result["would_update"] >= 1, (
            f"would_update should be >= 1. result={result!r}"
        )
        assert result["updated"] == 0, (
            f"updated should be 0 in dry-run. result={result!r}"
        )
        content_after = atom_path.read_text(encoding="utf-8")
        assert content_after == original, (
            "Dry-run must not modify files on disk."
        )

    def test_apply_cleans_files(self, tmp_path):
        """apply=True -> corrupted files are cleaned; updated >= 1."""
        atom_path = tmp_path / "NS.C1.md"
        _write_corrupted_atom(atom_path)

        result = demerge(tmp_path, apply=True)

        assert result["updated"] >= 1, (
            f"updated should be >= 1 after apply. result={result!r}"
        )
        content = atom_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(_extract_frontmatter(content))
        # keywords cleaned to string-only (dict entry removed)
        assert parsed["keywords"] == ["abgrenzung"], (
            f"keywords not cleaned to string-only: {parsed['keywords']!r}"
        )
        assert all(isinstance(x, str) for x in parsed["keywords"]), (
            f"keywords still has non-str entry: {parsed['keywords']!r}"
        )
        # referenced_by must remain intact (NS.C2 stays referenced — only keywords cleaned)
        assert any(e.get("by") == "NS.C2" for e in parsed["referenced_by"]), (
            f"referenced_by lost NS.C2 (must NOT be touched): {parsed['referenced_by']!r}"
        )

    def test_apply_output_is_valid_yaml(self, tmp_path):
        """After apply, every updated atom has valid YAML frontmatter."""
        atom_path = tmp_path / "NS.C1.md"
        _write_corrupted_atom(atom_path)

        demerge(tmp_path, apply=True)

        content = atom_path.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        parsed = yaml.safe_load(fm)
        assert parsed is not None, "yaml.safe_load returned None after driver apply"
        kw = parsed.get("keywords")
        assert isinstance(kw, list), f"keywords not a list: {kw!r}"
        assert all(isinstance(x, str) for x in kw), f"keywords contains non-str: {kw!r}"

    def test_backup_dir_copies_pre_state(self, tmp_path):
        """backup_dir -> PRE-apply bytes are backed up; backed_up == updated."""
        atom_path = tmp_path / "NS.C1.md"
        original_bytes = _write_corrupted_atom(atom_path).encode("utf-8")
        backup_dir = tmp_path / "backups"

        result = demerge(tmp_path, apply=True, backup_dir=backup_dir)

        assert result["backed_up"] == result["updated"], (
            f"backed_up ({result['backed_up']}) != updated ({result['updated']})"
        )
        assert result["backed_up"] >= 1, "backed_up should be >= 1"

        # Backup directory must exist and contain the pre-apply file
        assert backup_dir.exists(), "backup_dir was not created"
        backup_files = list(backup_dir.rglob("*.md"))
        assert len(backup_files) >= 1, "No backup files found in backup_dir"

        # Backup bytes must equal original pre-apply bytes
        backup_content = backup_files[0].read_bytes()
        assert backup_content == original_bytes, (
            "Backup file bytes do not match original pre-apply bytes."
        )

    def test_dropped_non_subset_reported(self, tmp_path):
        """A dict-keyword NOT in referenced_by -> appears in dropped_non_subset; still removed."""
        # Write atom with a dict-keyword that has a 'by' value NOT in referenced_by
        atom_path = tmp_path / "NS.C1.md"
        content = (
            "---\n"
            "type: truth\n"
            "id: NS.C1\n"
            "local_id: C1\n"
            "text: 'C1'\n"
            "keywords:\n"
            "- abgrenzung\n"
            "- by: NS.C2\n"
            "  kind: truth_edge\n"
            "- by: NS.ORPHAN\n"
            "  kind: truth_edge\n"
            "referenced_by:\n"
            "  - by: NS.C2\n"
            "    kind: truth_edge\n"
            "seq: 0\n"
            "edges: []\n"
            "---\n"
            "body\n"
        )
        atom_path.write_text(content, encoding="utf-8")

        result = demerge(tmp_path, apply=True)

        non_subset = result.get("dropped_non_subset", [])
        assert isinstance(non_subset, list), f"dropped_non_subset should be a list: {non_subset!r}"
        orphan_entries = [e for e in non_subset if e.get("by") == "NS.ORPHAN"]
        assert len(orphan_entries) >= 1, (
            f"NS.ORPHAN should appear in dropped_non_subset. Got: {non_subset!r}"
        )

        # Orphan must still be removed from keywords on disk
        disk_content = atom_path.read_text(encoding="utf-8")
        assert "NS.ORPHAN" not in disk_content or _orphan_not_in_keywords(disk_content), (
            "NS.ORPHAN dict entry was not removed from keywords block."
        )

    def test_second_apply_is_idempotent(self, tmp_path):
        """Second apply on already-clean files -> updated == 0."""
        atom_path = tmp_path / "NS.C1.md"
        _write_corrupted_atom(atom_path)

        demerge(tmp_path, apply=True)
        result2 = demerge(tmp_path, apply=True)

        assert result2["updated"] == 0, (
            f"Second apply should update 0 files (idempotent). Got updated={result2['updated']}"
        )

    def test_scanned_counts_all_md_files(self, tmp_path):
        """scanned should count all .md files in root (including clean ones)."""
        _write_corrupted_atom(tmp_path / "NS.C1.md")
        _write_clean_atom(tmp_path / "NS.Clean99.md")

        result = demerge(tmp_path, apply=False)

        assert result["scanned"] >= 2, (
            f"scanned should be >= 2. Got: {result['scanned']}"
        )

    def test_with_dict_keywords_counts_correctly(self, tmp_path):
        """with_dict_keywords must count only atoms that have dict entries in keywords."""
        _write_corrupted_atom(tmp_path / "NS.C1.md")
        _write_clean_atom(tmp_path / "NS.Clean99.md")

        result = demerge(tmp_path, apply=False)

        assert result["with_dict_keywords"] == 1, (
            f"with_dict_keywords should be 1. Got: {result['with_dict_keywords']}"
        )

    def test_dropped_total_counts_removed_dict_entries(self, tmp_path):
        """dropped_total counts total dict-keyword entries removed across all atoms."""
        # Atom with 2 dict keyword entries
        content = (
            "---\n"
            "type: truth\n"
            "id: NS.D1\n"
            "local_id: D1\n"
            "text: 'D1'\n"
            "keywords:\n"
            "- kw1\n"
            "- by: NS.D2\n"
            "  kind: truth_edge\n"
            "- by: NS.D3\n"
            "  kind: truth_edge\n"
            "referenced_by:\n"
            "  - by: NS.D2\n"
            "    kind: truth_edge\n"
            "  - by: NS.D3\n"
            "    kind: truth_edge\n"
            "seq: 0\n"
            "edges: []\n"
            "---\n"
            "body\n"
        )
        (tmp_path / "NS.D1.md").write_text(content, encoding="utf-8")

        result = demerge(tmp_path, apply=True)

        assert result["dropped_total"] >= 2, (
            f"dropped_total should be >= 2 (2 dict entries). Got: {result['dropped_total']}"
        )

    def test_became_empty_tracked(self, tmp_path):
        """became_empty counts atoms where keywords list becomes [] after demerge."""
        content = (
            "---\n"
            "type: truth\n"
            "id: NS.E1\n"
            "local_id: E1\n"
            "text: 'E1'\n"
            "keywords:\n"
            "- by: NS.E2\n"
            "  kind: truth_edge\n"
            "referenced_by:\n"
            "  - by: NS.E2\n"
            "    kind: truth_edge\n"
            "seq: 0\n"
            "edges: []\n"
            "---\n"
            "body\n"
        )
        (tmp_path / "NS.E1.md").write_text(content, encoding="utf-8")

        result = demerge(tmp_path, apply=True)

        assert result["became_empty"] >= 1, (
            f"became_empty should be >= 1 for atom with all-dict keywords. Got: {result!r}"
        )

    def test_result_has_all_required_keys(self, tmp_path):
        """demerge result dict must have all documented keys."""
        _write_corrupted_atom(tmp_path / "NS.C1.md")
        result = demerge(tmp_path, apply=False)

        required_int_keys = {
            "scanned", "with_dict_keywords", "would_update", "updated",
            "backed_up", "dropped_total", "became_empty",
        }
        for key in required_int_keys:
            assert key in result, f"Missing key in result: {key!r}"
            assert isinstance(result[key], int), (
                f"result[{key!r}] should be int, got {type(result[key]).__name__}"
            )
        assert "dropped_non_subset" in result, "Missing 'dropped_non_subset' list in result"
        assert isinstance(result["dropped_non_subset"], list), (
            f"dropped_non_subset should be a list, got {type(result['dropped_non_subset'])!r}"
        )


# ---------------------------------------------------------------------------
# TestMainCli
# ---------------------------------------------------------------------------

class TestMainCli:
    def test_main_dry_run_exits_zero(self, tmp_path):
        """main() with only root -> dry-run, exit 0."""
        _write_corrupted_atom(tmp_path / "NS.C1.md")
        exit_code = main([str(tmp_path)])
        assert exit_code == 0, f"main() dry-run should exit 0, got {exit_code}"

    def test_main_apply_cleans_and_exits_zero(self, tmp_path):
        """main() with --apply -> cleans files, exit 0."""
        atom_path = tmp_path / "NS.C1.md"
        _write_corrupted_atom(atom_path)
        exit_code = main([str(tmp_path), "--apply"])
        assert exit_code == 0, f"main() --apply should exit 0, got {exit_code}"
        content = atom_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(_extract_frontmatter(content))
        assert parsed["keywords"] == ["abgrenzung"], (
            f"keywords not cleaned after main --apply: {parsed['keywords']!r}"
        )
        # referenced_by must survive (only keywords block is cleaned)
        assert any(e.get("by") == "NS.C2" for e in parsed["referenced_by"]), (
            f"referenced_by lost NS.C2 after main --apply: {parsed['referenced_by']!r}"
        )

    def test_main_backup_dir_arg(self, tmp_path):
        """main() --backup-dir creates backup directory."""
        atom_path = tmp_path / "NS.C1.md"
        _write_corrupted_atom(atom_path)
        backup_dir = tmp_path / "bk"
        exit_code = main([str(tmp_path), "--apply", "--backup-dir", str(backup_dir)])
        assert exit_code == 0
        assert backup_dir.exists(), "backup_dir not created by main --backup-dir"


# ---------------------------------------------------------------------------
# Helper guards (private, not test functions)
# ---------------------------------------------------------------------------

def _no_kw_kind_lines(text: str) -> bool:
    """Check that '  kind: truth_edge' does NOT appear in the keywords block.
    It may legitimately appear inside referenced_by (at 4-space indent).
    Returns True if the keywords block is clean of 'kind:' dict-continuation lines.
    """
    # Rough heuristic: find the keywords block and check for '  kind:' at 2-space indent
    lines = text.splitlines()
    in_kw_block = False
    for ln in lines:
        if ln.strip() == "keywords:":
            in_kw_block = True
            continue
        if in_kw_block:
            # End of keywords block is a new top-level key (no leading space, has colon)
            if ln and not ln.startswith(" ") and not ln.startswith("-") and ":" in ln:
                in_kw_block = False
            elif ln.startswith("  kind:"):
                return False
    return True


def _orphan_not_in_keywords(disk_content: str) -> bool:
    """Return True if NS.ORPHAN does not appear as a keyword dict entry."""
    lines = disk_content.splitlines()
    in_kw_block = False
    for ln in lines:
        stripped = ln.strip()
        if stripped == "keywords:":
            in_kw_block = True
            continue
        if in_kw_block:
            if ln and not ln.startswith(" ") and not ln.startswith("-") and ":" in ln:
                in_kw_block = False
            elif "NS.ORPHAN" in ln:
                return False
    return True
