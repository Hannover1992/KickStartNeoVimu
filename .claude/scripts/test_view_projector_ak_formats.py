"""RED-phase tests for view_projector.gather_substrate AK format gaps.

Two new formats currently MISSED by the narrow regex:
  1. Heading with tags + em-dash (no colon):
       ### AK-1 [CORE_AK | Core] — First criterion heals (SC-01)
  2. Plain bullet (no bold):
       - AK-1: redeploy chains health orchestrate

Regression: original ### AK-N: title colon-heading form must still work.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from view_projector import gather_substrate  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vault(tmp_path):
    """Return vault root Path; creates Backlog dir."""
    vault = tmp_path / "vault"
    (vault / "Backlog").mkdir(parents=True)
    return vault


# ---------------------------------------------------------------------------
# Test 1 — HEADING WITH TAGS + EM-DASH FORMAT (currently FAILING = RED)
# ---------------------------------------------------------------------------

def test_heading_tags_emdash_format_extracted(tmp_path):
    """### AK-1 [CORE_AK | Core] — First criterion heals (SC-01)
    Currently MISSED by _AK_HEADING_RE (requires a colon after the id).
    This test MUST FAIL against the current code.
    """
    vault = _make_vault(tmp_path)
    spec_dir = vault / "Backlog" / "BL-501-x" / "3_Spec"
    spec_dir.mkdir(parents=True)
    spec_file = spec_dir / "BL-501-x_Spec.md"
    spec_file.write_text(
        "# BL-501 Spec\n\n"
        "### AK-1 [CORE_AK | Core] — First criterion heals (SC-01)\n"
        "### AK-2 [CORE_AK | Core] — Second criterion done (SC-02)\n",
        encoding="utf-8",
    )

    result = gather_substrate("BL-501", str(vault))
    aks = result["aks"]

    # Must find at least 2 AKs
    assert len(aks) >= 2, (
        f"Expected >=2 AKs for em-dash heading format, got {len(aks)}: {aks}"
    )

    ids = [a["id"] for a in aks]
    assert "AK-1" in ids, f"AK-1 missing; found: {ids}"
    assert "AK-2" in ids, f"AK-2 missing; found: {ids}"

    # Title should be the part AFTER the em-dash, NOT include the bracket tag
    ak1 = next(a for a in aks if a["id"] == "AK-1")
    assert "First criterion heals" in ak1["title"], (
        f"AK-1 title should contain 'First criterion heals'; got: {ak1['title']!r}"
    )
    assert "[CORE_AK" not in ak1["title"], (
        f"AK-1 title must not include the bracket tag; got: {ak1['title']!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — PLAIN BULLET (no bold) FORMAT (currently FAILING = RED)
# ---------------------------------------------------------------------------

def test_plain_bullet_format_extracted(tmp_path):
    """- AK-1: redeploy chains health orchestrate
    Currently MISSED by all three patterns (none match plain-bullet-no-bold).
    Falls back to node file (no 3_Spec dir).
    This test MUST FAIL against the current code.
    """
    vault = _make_vault(tmp_path)
    # No 3_Spec dir — write a plain node file
    node_file = vault / "Backlog" / "BL-502-y.md"
    node_file.write_text(
        "# BL-502 Node\n\n"
        "- AK-1: redeploy chains health orchestrate\n"
        "- AK-2: guard mirror fourth instance\n"
        "- AK-3: placement matrix documented\n",
        encoding="utf-8",
    )

    result = gather_substrate("BL-502", str(vault))
    aks = result["aks"]

    assert len(aks) >= 3, (
        f"Expected >=3 AKs for plain-bullet format, got {len(aks)}: {aks}"
    )

    ids = [a["id"] for a in aks]
    assert "AK-1" in ids, f"AK-1 missing; found: {ids}"
    assert "AK-2" in ids, f"AK-2 missing; found: {ids}"
    assert "AK-3" in ids, f"AK-3 missing; found: {ids}"

    ak1 = next(a for a in aks if a["id"] == "AK-1")
    assert "redeploy chains health" in ak1["title"], (
        f"AK-1 title should contain 'redeploy chains health'; got: {ak1['title']!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — REGRESSION: original colon-heading format still works (PASS)
# ---------------------------------------------------------------------------

def test_original_colon_heading_still_works(tmp_path):
    """### AK-1: some title — this is the original supported format.
    Must continue to work after any fix to add the new formats.
    This test should PASS against the current code (regression guard).
    """
    vault = _make_vault(tmp_path)
    spec_dir = vault / "Backlog" / "BL-503-z" / "3_Spec"
    spec_dir.mkdir(parents=True)
    spec_file = spec_dir / "BL-503-z_Spec.md"
    spec_file.write_text(
        "# BL-503 Spec\n\n"
        "### AK-1: Original colon heading format\n"
        "### AK-2: Another original colon entry\n",
        encoding="utf-8",
    )

    result = gather_substrate("BL-503", str(vault))
    aks = result["aks"]

    assert len(aks) >= 2, (
        f"Expected >=2 AKs for original colon-heading format, got {len(aks)}: {aks}"
    )

    ids = [a["id"] for a in aks]
    assert "AK-1" in ids, f"AK-1 missing; found: {ids}"
    assert "AK-2" in ids, f"AK-2 missing; found: {ids}"

    ak1 = next(a for a in aks if a["id"] == "AK-1")
    assert "Original colon heading format" in ak1["title"], (
        f"AK-1 title wrong; got: {ak1['title']!r}"
    )
