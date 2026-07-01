"""
test_view_node_library.py — RED-phase TDD (BL-460 Library extension).

Tests for is_view_node covering the Libraries/ view-type that is currently
MISSING from the predicate. The rule GREEN will implement:

  A path is a Library view-node (is_view_node==True) IFF:
    - first path segment (case-insensitive) == "libraries"
    - ends in .md
    - NOT infrastructure, where infrastructure = ANY of:
        basename (lowercase) in {_index.md, readme.md, template.md,
            convention.md, frontmatter-schema.md, crossref_index.md}
        basename (lowercase) endswith _template.md
        any path segment (lowercase) == _drafts

INCLUDE tests (assert True)  — currently return False → genuine RED.
EXCLUDE tests (assert False) — currently return False already (no Library
    branch), so they PASS now; GREEN must keep them False with precision.
REGRESSION True/False        — pin existing non-Library behaviour.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from view_node_predicate import is_view_node


def _make(tmp_path, rel_path: str, content: str = "# placeholder\n") -> tuple[str, str]:
    """Create vault_root/rel_path, return (abs_file_path, vault_root_str)."""
    vault = tmp_path
    target = vault / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return str(target), str(vault)


# ---------------------------------------------------------------------------
# INCLUDE group — currently return False, MUST FAIL in RED phase (genuine RED)
# ---------------------------------------------------------------------------

def test_include_library_adr_decision(tmp_path):
    """Libraries/ADR/ADR-domain-single-source.md — ADR decision knowledge-view."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/ADR/ADR-domain-single-source.md",
    )
    assert is_view_node(file_path, vault), (
        "Expected is_view_node==True for Libraries/ADR/ADR-domain-single-source.md"
    )


def test_include_library_semantic_project_berater(tmp_path):
    """Libraries/SemanticLibrary/_project/BERATER/domain-terms.md — domain-terms knowledge-view.

    _project is an allowed segment — only _drafts is excluded.
    """
    file_path, vault = _make(
        tmp_path,
        "Libraries/SemanticLibrary/_project/BERATER/domain-terms.md",
    )
    assert is_view_node(file_path, vault), (
        "Expected is_view_node==True for Libraries/SemanticLibrary/_project/BERATER/domain-terms.md"
    )


def test_include_library_semantic_global_glossary(tmp_path):
    """Libraries/SemanticLibrary/_global/domain-glossary.md — global domain glossary."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/SemanticLibrary/_global/domain-glossary.md",
    )
    assert is_view_node(file_path, vault), (
        "Expected is_view_node==True for Libraries/SemanticLibrary/_global/domain-glossary.md"
    )


def test_include_library_pattern_generic_entry(tmp_path):
    """Libraries/PatternLibrary/_generic/PT-GEN-LeadFollow.md — pattern entry."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/PatternLibrary/_generic/PT-GEN-LeadFollow.md",
    )
    assert is_view_node(file_path, vault), (
        "Expected is_view_node==True for Libraries/PatternLibrary/_generic/PT-GEN-LeadFollow.md"
    )


def test_include_library_top_level_doc(tmp_path):
    """Libraries/domain-vs-wnode-abgrenzung.md — top-level Library knowledge doc."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/domain-vs-wnode-abgrenzung.md",
    )
    assert is_view_node(file_path, vault), (
        "Expected is_view_node==True for Libraries/domain-vs-wnode-abgrenzung.md"
    )


# ---------------------------------------------------------------------------
# EXCLUDE group — must remain False (infrastructure files inside Libraries/)
# Currently False (no Library branch exists); GREEN must keep them False.
# ---------------------------------------------------------------------------

def test_exclude_library_index(tmp_path):
    """Libraries/_index.md — infrastructure index, must be False."""
    file_path, vault = _make(tmp_path, "Libraries/_index.md")
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Libraries/_index.md"
    )


def test_exclude_library_crossref_index(tmp_path):
    """Libraries/CrossRef_Index.md — crossref_index infrastructure, must be False."""
    file_path, vault = _make(tmp_path, "Libraries/CrossRef_Index.md")
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Libraries/CrossRef_Index.md"
    )


def test_exclude_library_adr_convention(tmp_path):
    """Libraries/ADR/CONVENTION.md — convention infrastructure, must be False."""
    file_path, vault = _make(tmp_path, "Libraries/ADR/CONVENTION.md")
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Libraries/ADR/CONVENTION.md"
    )


def test_exclude_library_adr_template(tmp_path):
    """Libraries/ADR/TEMPLATE.md — template infrastructure, must be False."""
    file_path, vault = _make(tmp_path, "Libraries/ADR/TEMPLATE.md")
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Libraries/ADR/TEMPLATE.md"
    )


def test_exclude_library_pattern_endswith_template(tmp_path):
    """Libraries/PatternLibrary/_generic/ApplicationTrail_TEMPLATE.md — endswith _template.md."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/PatternLibrary/_generic/ApplicationTrail_TEMPLATE.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for *_TEMPLATE.md (endswith _template.md)"
    )


def test_exclude_library_pattern_readme(tmp_path):
    """Libraries/PatternLibrary/_generic/README.md — readme infrastructure."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/PatternLibrary/_generic/README.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Libraries/.../README.md"
    )


def test_exclude_library_frontmatter_schema(tmp_path):
    """Libraries/PatternLibrary/_generic/frontmatter-schema.md — schema infrastructure."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/PatternLibrary/_generic/frontmatter-schema.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Libraries/.../frontmatter-schema.md"
    )


def test_exclude_library_drafts_file(tmp_path):
    """Libraries/PatternLibrary/_drafts/some-draft.md — under _drafts segment."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/PatternLibrary/_drafts/some-draft.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Libraries/.../_drafts/... path"
    )


def test_exclude_library_semantic_readme(tmp_path):
    """Libraries/SemanticLibrary/_global/README.md — readme infrastructure."""
    file_path, vault = _make(
        tmp_path,
        "Libraries/SemanticLibrary/_global/README.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Libraries/SemanticLibrary/_global/README.md"
    )


# ---------------------------------------------------------------------------
# REGRESSION True — existing non-Library patterns must still return True
# ---------------------------------------------------------------------------

def test_regression_true_2_model(tmp_path):
    """Backlog/<bl>/2_Model/<name>_Model.md — existing canonical path."""
    file_path, vault = _make(tmp_path, "Backlog/BL-060-x/2_Model/Foo_Model.md")
    assert is_view_node(file_path, vault), (
        "REGRESSION: Backlog/<bl>/2_Model/<name>_Model.md must remain True"
    )


def test_regression_true_legacy_model_folder(tmp_path):
    """Backlog/<bl>/Model/<name>_Model.md — legacy Model folder."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-041-x/Model/Legacy_Model.md",
    )
    assert is_view_node(file_path, vault), (
        "REGRESSION: Backlog/<bl>/Model/<name>_Model.md (legacy) must remain True"
    )


def test_regression_true_vault_top_models(tmp_path):
    """Models/Some_Model.md — vault-top Models/ dir."""
    file_path, vault = _make(tmp_path, "Models/Some_Model.md")
    assert is_view_node(file_path, vault), (
        "REGRESSION: Models/<name>_Model.md must remain True"
    )


def test_regression_true_arc42(tmp_path):
    """Backlog/<bl>/arc42/<name>.md — existing canonical path."""
    file_path, vault = _make(tmp_path, "Backlog/BL-060-x/arc42/01_intro.md")
    assert is_view_node(file_path, vault), (
        "REGRESSION: Backlog/<bl>/arc42/<name>.md must remain True"
    )


# ---------------------------------------------------------------------------
# REGRESSION False — existing exclusions must still hold
# ---------------------------------------------------------------------------

def test_regression_false_truths(tmp_path):
    """Backlog/<bl>/2_Model/truths/W1.md — atom, must remain False."""
    file_path, vault = _make(tmp_path, "Backlog/BL-060-x/2_Model/truths/W1.md")
    assert not is_view_node(file_path, vault), (
        "REGRESSION: Backlog/<bl>/2_Model/truths/*.md must remain False"
    )


def test_regression_false_manifest(tmp_path):
    """Backlog/<bl>/_manifest.md — must remain False."""
    file_path, vault = _make(tmp_path, "Backlog/BL-060-x/_manifest.md")
    assert not is_view_node(file_path, vault), (
        "REGRESSION: _manifest.md must remain False"
    )
