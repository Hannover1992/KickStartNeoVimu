"""test_bl408_stage_lifecycle.py — BL-408 RED conformance test.

Ring 1, Iteration 1:
  test_i_orchestrate_has_bl408_lifecycle_section — RED (missing BL-408 explicit section)
  test_tdd_setup_acquires_resources              — characterization GREEN
  test_tdd_teardown_releases_and_finally         — characterization GREEN
  test_lifecycle_reads_bl392_schema             — characterization GREEN
"""

import re
from pathlib import Path

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

I_ORCHESTRATE = COMMANDS_DIR / "_I_orchestrate.md"
TDD_SETUP = COMMANDS_DIR / "_TDD_setup.md"
TDD_TEARDOWN = COMMANDS_DIR / "_TDD_teardown.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────
# RED test — fails now (BL-408 lifecycle section absent)
# ─────────────────────────────────────────────────────────

def test_i_orchestrate_has_bl408_lifecycle_section():
    """_I_orchestrate.md MUST contain an explicit consolidating BL-408
    Stage-Lifecycle contract section that references:
      - "BL-408"
      - "Stage-Lifecycle" OR "Lifecycle"
      - "setup" AND "teardown"
      - "acquire" OR "release"
      - "finally"
    This section is absent today -> RED.
    """
    text = _read(I_ORCHESTRATE)

    has_bl408 = "BL-408" in text
    has_lifecycle = bool(re.search(r"Stage.Lifecycle|Lifecycle", text, re.IGNORECASE))
    has_setup = "setup" in text
    has_teardown = "teardown" in text
    has_acquire_or_release = bool(re.search(r"\bacquire\b|\brelease\b", text, re.IGNORECASE))
    has_finally = "finally" in text.lower()

    # All six conditions must be satisfied IN COMBINATION within a dedicated BL-408 section.
    # A dedicated section means BL-408 is explicitly referenced alongside the lifecycle terms.
    # Currently BL-408 does not appear in _I_orchestrate.md at all -> assertion fails -> RED.
    assert has_bl408, (
        "_I_orchestrate.md does not reference 'BL-408'. "
        "A consolidating Stage-Lifecycle-Vertrags-Sektion for BL-408 is missing."
    )
    assert has_lifecycle, (
        "_I_orchestrate.md lacks a 'Stage-Lifecycle' / 'Lifecycle' section heading (BL-408)."
    )
    assert has_setup and has_teardown, (
        "_I_orchestrate.md BL-408 section must reference both 'setup' and 'teardown'."
    )
    assert has_acquire_or_release, (
        "_I_orchestrate.md BL-408 section must reference 'acquire' or 'release'."
    )
    assert has_finally, (
        "_I_orchestrate.md BL-408 section must reference 'finally' (INV-TEARDOWN-3 finally-Semantik)."
    )


# ─────────────────────────────────────────────────────────
# Characterization tests — should be GREEN (wiring exists)
# ─────────────────────────────────────────────────────────

def test_tdd_setup_acquires_resources():
    """_TDD_setup.md references acquire (INV-SETUP-9 / acquire_all / resource-acquire).
    This wiring already exists -> characterization test, expected GREEN.
    """
    text = _read(TDD_SETUP)
    assert re.search(r"\bacquire\b", text, re.IGNORECASE), (
        "_TDD_setup.md does not contain 'acquire' (INV-SETUP-9 acquire_all). "
        "The resource-acquire wiring is missing."
    )


def test_tdd_teardown_releases_and_finally():
    """_TDD_teardown.md references 'release' (resources_released) and 'finally'
    (INV-TEARDOWN-3 always-run semantics). Expected GREEN — wiring exists.
    """
    text = _read(TDD_TEARDOWN)
    assert re.search(r"\brelease\b", text, re.IGNORECASE), (
        "_TDD_teardown.md does not contain 'release' (resources_released / INV-TEARDOWN-3)."
    )
    assert "finally" in text.lower(), (
        "_TDD_teardown.md does not reference 'finally' / always-run semantics (INV-TEARDOWN-3)."
    )


def test_lifecycle_reads_bl392_schema():
    """_TDD_setup.md references resolve_vault_stage (BL-392 dual-read schema).
    Expected GREEN — the resolver reference is already present.
    """
    text = _read(TDD_SETUP)
    assert "resolve_vault_stage" in text, (
        "_TDD_setup.md does not reference 'resolve_vault_stage' (BL-392 dual-read). "
        "The schema wiring is absent."
    )
