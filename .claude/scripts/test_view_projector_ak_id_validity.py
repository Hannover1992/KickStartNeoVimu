"""TDD RED-phase: AK-id validity filter in gather_substrate.

Tests that non-digit, non-DoD AK ids (like AK-Liste) are excluded,
while real AKs with digits (AK-1, AK-F2, AK-CTX3) and DoD AKs are kept.

Spec note on AK-CTX-3 vs AK-CTX3:
  The current _AK_UNIFIED_RE captures (\\w+) which stops at '-', so
  'AK-CTX-3' is captured as id='CTX' (the '-3' is lost).  The spec format
  used here writes 'AK-CTX3' (no inner hyphen) so the regex captures 'CTX3'
  as a single token — a real multi-component id with a digit.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path

import pytest

from view_projector import gather_substrate


# NOTE: AK-Liste uses a ': ...' separator so the current _AK_UNIFIED_RE
# DOES match it and extracts id='Liste' (a non-digit, non-DoD id).
# The RED test asserts it must NOT appear; GREEN will add the filter.
#
# AK-CTX3 (no inner hyphen) is a legitimate multi-segment id with a digit;
# the regex captures the full 'CTX3' token in group(2).
SPEC_CONTENT = """\
# BL-600-x Spec

## Akzeptanzkriterien

### AK-Liste: der 12 SC (selbst aus Findings abgeleitet)
### AK-1 [Core] — Real first criterion (SC-01)
### AK-F2 — Real factored criterion
### AK-CTX3: Real context criterion
### AK-DoD — Definition of done criterion
"""


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """Create a synthetic vault with a BL-600-x spec file."""
    spec_dir = tmp_path / "Backlog" / "BL-600-x" / "3_Spec"
    spec_dir.mkdir(parents=True)
    spec_file = spec_dir / "BL-600-x_Spec.md"
    spec_file.write_text(SPEC_CONTENT, encoding="utf-8")
    return tmp_path


def _get_ids(vault: Path) -> list[str]:
    result = gather_substrate("BL-600", str(vault))
    return [a["id"] for a in result["aks"]]


def test_excludes_non_digit_header_id(vault: Path) -> None:
    """AK-Liste is a section header, NOT a real AK — must be excluded.

    RED: current code extracts AK-Liste because \\w+ matches 'Liste' and
    the line has a ':' separator, so _AK_UNIFIED_RE matches it.
    GREEN will add a digit-or-DoD guard to _parse_aks_from_text.
    """
    ids = _get_ids(vault)
    assert "AK-Liste" not in ids, (
        f"AK-Liste must NOT appear in extracted AKs, but got ids={ids}"
    )


def test_keeps_real_numeric_and_alpha_numeric_aks(vault: Path) -> None:
    """Real AKs that contain at least one digit must be kept."""
    ids = _get_ids(vault)
    assert "AK-1" in ids, f"AK-1 missing from ids={ids}"
    assert "AK-F2" in ids, f"AK-F2 missing from ids={ids}"
    assert "AK-CTX3" in ids, f"AK-CTX3 missing from ids={ids}"


def test_keeps_dod_ak(vault: Path) -> None:
    """AK-DoD is a Definition-of-Done criterion — must be kept even with no digit."""
    ids = _get_ids(vault)
    assert "AK-DoD" in ids, f"AK-DoD missing from ids={ids}"
