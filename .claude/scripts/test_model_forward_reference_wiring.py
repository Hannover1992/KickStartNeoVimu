"""
RED test: P2-wiring — forward-reference step in _model.md finish section.

These tests MUST FAIL today (wiring absent) and pass once a real
forward-reference step is added to the finish section of _model.md.

Wiring GREEN will add:
  1. `view_forward_reference` call inside the finish section
  2. A gate/dry-run marker while BL-443 open (forward-garantie / auto-reference /
     auto-referenz / BL-443 / gated / dry-run / deferred-gated)
  3. A "Forward" or "vorwaerts" marker documenting the guarantee intent
"""

import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODEL_MD = os.path.join(_HERE, "..", "commands", "_model.md")


def _read_model() -> str:
    with open(_MODEL_MD, encoding="utf-8") as f:
        return f.read()


def _extract_finish_section(content: str) -> str:
    """Return the text between '## Ablauf: finish' and the next top-level '## '."""
    start_marker = "## Ablauf: finish"
    start_idx = content.find(start_marker)
    assert start_idx != -1, f"Marker '{start_marker}' not found in _model.md"

    # Find the next top-level heading after the start marker
    next_h2 = re.search(r"\n## [^#]", content[start_idx + len(start_marker):])
    if next_h2:
        end_idx = start_idx + len(start_marker) + next_h2.start()
    else:
        end_idx = len(content)

    return content[start_idx:end_idx]


# ---------------------------------------------------------------------------
# Test 1: finish section must reference the P2 module
# ---------------------------------------------------------------------------

def test_finish_section_references_view_forward_reference():
    """
    The finish section must invoke `view_forward_reference` (or
    `view_forward_reference_new_view`) — the P2 forward-garantie module.
    This is ABSENT today → RED.
    """
    content = _read_model()
    finish = _extract_finish_section(content)

    assert "view_forward_reference" in finish, (
        "FAIL (expected RED): finish section has no reference to "
        "'view_forward_reference'. "
        "GREEN: add a forward-reference step that calls "
        "view_forward_reference (dry-run/gated while BL-443 open)."
    )


# ---------------------------------------------------------------------------
# Test 2: finish section must carry a gate/deferred marker near the reference
# ---------------------------------------------------------------------------

def test_finish_section_has_gate_or_dryrun_marker_near_forward_ref():
    """
    Within the finish section, the forward-reference step must appear IN
    PROXIMITY to a gate/dry-run/deferred marker (within 400 characters of
    the `view_forward_reference` token).

    Accepted tokens (case-insensitive):
      forward-garantie, forward-reference, auto-referenz, BL-443, gated,
      dry-run, deferred-gated

    We search around each occurrence of 'view_forward_reference' in the
    finish section and require at least one gate token within +-400 chars.

    This is ABSENT today (no view_forward_reference at all) → RED.
    """
    content = _read_model()
    finish = _extract_finish_section(content)
    finish_lower = finish.lower()

    gate_tokens = [
        "forward-garantie",
        "forward-reference",
        "auto-referenz",
        "bl-443",
        "gated",
        "dry-run",
        "deferred-gated",
    ]

    # Find all occurrences of the function name in finish
    fn_token = "view_forward_reference"
    positions = [m.start() for m in re.finditer(fn_token, finish_lower)]

    assert positions, (
        "FAIL (expected RED): finish section has no 'view_forward_reference' "
        "occurrence — gate-proximity test cannot proceed. "
        "GREEN: add the forward-reference step with a gate/dry-run marker."
    )

    # For each occurrence, check +-400 char window for a gate token
    window = 400
    found_near = False
    for pos in positions:
        snippet = finish_lower[max(0, pos - window): pos + window]
        if any(tok in snippet for tok in gate_tokens):
            found_near = True
            break

    assert found_near, (
        "FAIL (expected RED): 'view_forward_reference' found in finish section "
        "but no gate/deferred marker within +-400 chars. "
        f"Gate tokens checked: {gate_tokens}. "
        "GREEN: mark the step with at least one gate token near the call."
    )


# ---------------------------------------------------------------------------
# Test 3: _model.md as a whole must signal the Forward-Garantie intent
# ---------------------------------------------------------------------------

def test_model_md_signals_forward_guarantee_intent():
    """
    The word 'Forward' or 'vorwaerts' (case-insensitive) must appear in
    _model.md to document the forward-reference as a self-maintaining
    behaviour guarantee. Currently absent → RED.

    Note: 'view_forward_reference' alone satisfies 'forward' in lowercase,
    but the intent here is a DOCUMENTED guarantee label, not merely the
    function name. We therefore require 'Forward' (capital F, explicit label)
    or 'vorwaerts'.
    """
    content = _read_model()

    has_forward_label = bool(re.search(r"Forward", content))
    has_vorwaerts = bool(re.search(r"vorwaerts", content, re.IGNORECASE))

    assert has_forward_label or has_vorwaerts, (
        "FAIL (expected RED): _model.md contains neither 'Forward' "
        "(capitalised guarantee label) nor 'vorwaerts'. "
        "GREEN: add a documented Forward-Garantie label in the finish section "
        "or the Qualitaetskriterien table."
    )
