"""
test_schwarm_decomposer_view_node_ssot.py — RED-phase TDD (BL-460)

SSoT equivalence tests: schwarm_decomposer.decompose_views() corpus MUST equal
the set of paths for which hook_view_forward_reference.is_view_node() returns True.

Current state: FAILING (RED) — decompose_views uses over-broad globs
("Backlog/*/*.md") and never consults is_view_node, so _manifest.md, Task.md,
BL-node files, PRAESENTATION files, truths/ atoms, and .claude/ files are
wrongly included in the corpus.

These tests MUST fail against the current schwarm_decomposer.py implementation.
"""

from __future__ import annotations

import os
import sys

# Import from the scripts directory (this file lives there too)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from pathlib import Path

from schwarm_decomposer import decompose_views
from hook_view_forward_reference import is_view_node


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flatten(slices: list[list[str]]) -> list[str]:
    """Flatten a list-of-lists into a single list."""
    result = []
    for s in slices:
        result.extend(s)
    return result


def _norm(p: str) -> str:
    """Normalize a path for comparison (case-insensitive on Windows)."""
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


# ---------------------------------------------------------------------------
# Fixture: synthetic vault
# ---------------------------------------------------------------------------

@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """Build a synthetic vault with a representative mix of view and non-view files."""

    def _write(rel: str, content: str = "") -> Path:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content if content else f"# {p.name}\n\nPlaceholder content for {rel}.\n", encoding="utf-8")
        return p

    # --- VIEW files (MUST be included) ---
    # Backlog/<bl>/2_Model/<name>_Model.md
    _write(
        "Backlog/BL-001-foo/2_Model/BL-001-foo_Model.md",
        "# BL-001-foo Model\n\nsource_atoms: []\nThis is the Model view.\n",
    )
    # Backlog/<bl>/arc42/<name>.md
    _write(
        "Backlog/BL-001-foo/arc42/01_intro.md",
        "# arc42 Introduction\n\nArchitecture context for BL-001-foo.\n",
    )
    # Backlog/<bl>/6_PL/<name>.md
    _write(
        "Backlog/BL-001-foo/6_PL/BL-001-foo-parking-lot.md",
        "# Parking Lot\n\nOpen items for BL-001-foo.\n",
    )
    # Docs/**/*.md at vault top
    _write(
        "Docs/guide.md",
        "# Guide\n\nTop-level documentation guide.\n",
    )
    _write(
        "Docs/sub/deep.md",
        "# Deep Doc\n\nNested documentation file.\n",
    )

    # --- NON-VIEW files (MUST be excluded) ---
    # _manifest.md
    _write(
        "Backlog/BL-001-foo/_manifest.md",
        "# Manifest\n\nstatus: active\nbatch_status: READY\n",
    )
    # _manifest_protokoll.md
    _write(
        "Backlog/BL-001-foo/_manifest_protokoll.md",
        "# Manifest Protokoll\n\nProtokoll entries go here.\n",
    )
    # Task.md
    _write(
        "Backlog/BL-001-foo/Task.md",
        "# Task\n\nTask description for BL-001-foo.\n",
    )
    # 1_Task.md
    _write(
        "Backlog/BL-001-foo/1_Task.md",
        "# 1_Task\n\nInitial task file for BL-001-foo.\n",
    )
    # BL-node file: Backlog/<bl>/<bl>.md
    _write(
        "Backlog/BL-001-foo/BL-001-foo.md",
        "# BL-001-foo\n\nBacklog item node file.\n",
    )
    # PRAESENTATION file
    _write(
        "Backlog/BL-001-foo/PRAESENTATION-x.md",
        "# Praesentation\n\nPresentation content for BL-001-foo.\n",
    )
    # truths/ atom (under 2_Model)
    _write(
        "Backlog/BL-001-foo/2_Model/truths/W001.md",
        "# W001\n\nAtom truth file. Not a view.\n",
    )
    # .claude/ file (must be excluded)
    _write(
        ".claude/something.md",
        "# Claude internal\n\nInternal harness file.\n",
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Tests — all MUST FAIL against current decompose_views (RED)
# ---------------------------------------------------------------------------

def test_excludes_manifest_files(vault: Path) -> None:
    """decompose_views must NOT include _manifest.md or _manifest_protokoll.md."""
    corpus = _flatten(decompose_views(str(vault), 1))
    basenames = [os.path.basename(p) for p in corpus]
    assert "_manifest.md" not in basenames, (
        "_manifest.md must be excluded from view corpus but was found"
    )
    assert "_manifest_protokoll.md" not in basenames, (
        "_manifest_protokoll.md must be excluded from view corpus but was found"
    )


def test_excludes_task_files(vault: Path) -> None:
    """decompose_views must NOT include Task.md or 1_Task.md."""
    corpus = _flatten(decompose_views(str(vault), 1))
    basenames = [os.path.basename(p) for p in corpus]
    assert "Task.md" not in basenames, (
        "Task.md must be excluded from view corpus but was found"
    )
    assert "1_Task.md" not in basenames, (
        "1_Task.md must be excluded from view corpus but was found"
    )


def test_excludes_bl_node_and_presentation(vault: Path) -> None:
    """decompose_views must NOT include the BL-node file or PRAESENTATION files."""
    corpus = _flatten(decompose_views(str(vault), 1))
    basenames = [os.path.basename(p) for p in corpus]
    assert "BL-001-foo.md" not in basenames, (
        "BL-001-foo.md (BL-node) must be excluded from view corpus but was found"
    )
    assert "PRAESENTATION-x.md" not in basenames, (
        "PRAESENTATION-x.md must be excluded from view corpus but was found"
    )


def test_excludes_truths_atoms(vault: Path) -> None:
    """decompose_views must NOT include truths/ atom files."""
    corpus = _flatten(decompose_views(str(vault), 1))
    # Check by normalized path: no path with 'truths' separator should appear
    truths_in_corpus = [
        p for p in corpus
        if "truths" in Path(p).parts
    ]
    assert len(truths_in_corpus) == 0, (
        f"truths/ atoms must be excluded but found: {truths_in_corpus}"
    )


def test_excludes_dot_claude(vault: Path) -> None:
    """decompose_views must NOT include any file under .claude/."""
    corpus = _flatten(decompose_views(str(vault), 1))
    dot_claude_entries = [
        p for p in corpus
        if ".claude" in Path(p).parts
    ]
    assert len(dot_claude_entries) == 0, (
        f"Nothing under .claude/ must be in corpus but found: {dot_claude_entries}"
    )


def test_includes_model_arc42_pl(vault: Path) -> None:
    """decompose_views MUST include Model, arc42, and 6_PL view files."""
    corpus_normed = {_norm(p) for p in _flatten(decompose_views(str(vault), 1))}

    model_path = _norm(str(vault / "Backlog/BL-001-foo/2_Model/BL-001-foo_Model.md"))
    arc42_path = _norm(str(vault / "Backlog/BL-001-foo/arc42/01_intro.md"))
    pl_path = _norm(str(vault / "Backlog/BL-001-foo/6_PL/BL-001-foo-parking-lot.md"))

    assert model_path in corpus_normed, (
        "Backlog/BL-001-foo/2_Model/BL-001-foo_Model.md must be in corpus"
    )
    assert arc42_path in corpus_normed, (
        "Backlog/BL-001-foo/arc42/01_intro.md must be in corpus"
    )
    assert pl_path in corpus_normed, (
        "Backlog/BL-001-foo/6_PL/BL-001-foo-parking-lot.md must be in corpus"
    )


def test_includes_vault_top_docs(vault: Path) -> None:
    """decompose_views MUST include Docs/guide.md and Docs/sub/deep.md."""
    corpus_normed = {_norm(p) for p in _flatten(decompose_views(str(vault), 1))}

    guide_path = _norm(str(vault / "Docs/guide.md"))
    deep_path = _norm(str(vault / "Docs/sub/deep.md"))

    assert guide_path in corpus_normed, (
        "Docs/guide.md must be in corpus"
    )
    assert deep_path in corpus_normed, (
        "Docs/sub/deep.md must be in corpus"
    )


def test_corpus_equals_is_view_node_set(vault: Path) -> None:
    """
    Keystone SSoT equivalence test:
    decompose_views corpus must exactly equal { p | is_view_node(p, vault) }.

    This is the definitive RED test: current decompose_views over-includes files
    that is_view_node rejects (manifests, task files, BL-nodes, truths/ atoms, etc.)
    """
    # Expected: all .md files in vault for which is_view_node returns True
    expected = {
        _norm(str(p))
        for p in vault.rglob("*.md")
        if is_view_node(str(p), str(vault))
    }

    # Actual: what decompose_views currently returns
    actual = {
        _norm(v)
        for v in _flatten(decompose_views(str(vault), 1))
    }

    assert actual == expected, (
        f"decompose_views corpus does not match is_view_node set.\n"
        f"  Extra (over-included, not view nodes): {actual - expected}\n"
        f"  Missing (view nodes not in corpus):    {expected - actual}"
    )


def test_disjoint_and_complete_preserved(vault: Path) -> None:
    """
    With n_slices=3: slices must be pairwise disjoint AND their union must
    equal the n_slices=1 corpus. The existing partition guarantee must hold
    after any filtering fix is applied.

    Note: this test verifies the partition INVARIANT independent of the
    SSoT fix. It should PASS even now (partition logic is correct already),
    but is included to ensure the fix doesn't break partitioning.
    """
    corpus_1 = set(_norm(p) for p in _flatten(decompose_views(str(vault), 1)))
    slices_3 = decompose_views(str(vault), 3)

    # Pairwise disjoint
    for i in range(len(slices_3)):
        for j in range(i + 1, len(slices_3)):
            set_i = {_norm(p) for p in slices_3[i]}
            set_j = {_norm(p) for p in slices_3[j]}
            overlap = set_i & set_j
            assert len(overlap) == 0, (
                f"Slices {i} and {j} overlap: {overlap}"
            )

    # Union equals n_slices=1 corpus
    union_3 = {_norm(p) for p in _flatten(slices_3)}
    assert union_3 == corpus_1, (
        f"Union of 3 slices != 1-slice corpus.\n"
        f"  Extra in union: {union_3 - corpus_1}\n"
        f"  Missing from union: {corpus_1 - union_3}"
    )
