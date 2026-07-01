"""
test_model_truthatomic_gate_wiring.py — BL-243 AK-S4: Wiring-Test fuer Quality-Gate in _model.md finish.

Stellt sicher, dass der finish-Ablauf in `.claude/commands/_model.md` den Validator
`quality_model_wform.py` aufruft und das Gate ADVISORY / nicht-blockierend bleibt
(Backfill-Quieszenz-Prinzip: prose-Model backfill ist quiescence-gated).

RED today (wiring fehlt), GREEN nach AK-S4-Implementierung (advisory gate step in finish hinzugefuegt).
"""

import os
import re

# ---------------------------------------------------------------------------
# Hilfsfunktion: finish-Sektion aus _model.md isolieren
# ---------------------------------------------------------------------------

VALIDATOR_NAME = "quality_model_wform.py"
FINISH_HEADING = "## Ablauf: finish"


def _load_model_md() -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "commands", "_model.md")
    path = os.path.normpath(path)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _extract_finish_section(text: str) -> str:
    """Slice from '## Ablauf: finish' up to (but not including) the next top-level '## ' heading."""
    start = text.find(FINISH_HEADING)
    assert start != -1, f"'{FINISH_HEADING}' heading not found in _model.md"

    # Find next top-level heading AFTER the finish heading
    after_start = text.find("\n## ", start + len(FINISH_HEADING))
    if after_start == -1:
        return text[start:]
    return text[start:after_start]


# ---------------------------------------------------------------------------
# Test 1: finish-Ablauf referenziert den Validator
# ---------------------------------------------------------------------------

def test_finish_ablauf_references_validator():
    """
    The finish section MUST contain a reference to quality_model_wform.py
    so that the gate step is documented / invoked.
    GREEN: after a 'Phase X: Quality-Gate' or equivalent step referencing the validator is added.
    """
    text = _load_model_md()
    finish = _extract_finish_section(text)
    assert VALIDATOR_NAME in finish, (
        f"'{VALIDATOR_NAME}' not found in the finish section of _model.md.\n"
        f"AK-S4 wiring missing: finish ablauf must reference the quality gate validator."
    )


# ---------------------------------------------------------------------------
# Test 2: the gate within finish is advisory / non-blocking
# ---------------------------------------------------------------------------

ADVISORY_KEYWORDS = [
    "advisory",
    "warn",
    "non-blocking",
    "nicht-blockierend",
    "backfill",
    "quiescenz",
    "quiescence",
]


def test_finish_gate_is_advisory():
    """
    Near the validator reference inside the finish section, the text must indicate
    the gate is advisory/non-blocking (prose-Model backfill is quiescence-gated).
    Checks for at least one of: advisory, WARN, non-blocking, nicht-blockierend,
    backfill, quiescenz/quiescence.
    """
    text = _load_model_md()
    finish = _extract_finish_section(text)

    # Only check if validator is present (otherwise test_1 already fails)
    if VALIDATOR_NAME not in finish:
        return  # test_1 covers this; avoid double-failure noise

    finish_lower = finish.lower()
    found = any(kw.lower() in finish_lower for kw in ADVISORY_KEYWORDS)
    assert found, (
        f"The finish section references '{VALIDATOR_NAME}' but does not indicate "
        f"the gate is advisory/non-blocking.\n"
        f"Expected at least one of {ADVISORY_KEYWORDS} near the validator reference.\n"
        f"Rationale: prose-Model backfill is quiescence-gated; gate must WARN, not hard-fail."
    )


# ---------------------------------------------------------------------------
# Test 3: Truth-Atomic-First quality-criteria row references the validator
# ---------------------------------------------------------------------------

def test_truth_atomic_first_criterion_references_validator():
    """
    The 'Truth-Atomic-First' row in the Model-Qualitaetskriterien table
    (## Model-Qualitaetskriterien) must reference quality_model_wform.py
    so the criterion points at its mechanical check.
    """
    text = _load_model_md()
    # Find the quality criteria section
    qc_heading = "## Model-Qualitaetskriterien"
    qc_start = text.find(qc_heading)
    assert qc_start != -1, f"'{qc_heading}' heading not found in _model.md"

    # Slice to next top-level heading
    after_qc = text.find("\n## ", qc_start + len(qc_heading))
    qc_section = text[qc_start:after_qc] if after_qc != -1 else text[qc_start:]

    # Find the Truth-Atomic-First row (case-insensitive)
    tat_pattern = re.compile(r"truth.atomic.first", re.IGNORECASE)
    assert tat_pattern.search(qc_section), (
        "No 'Truth-Atomic-First' row found in Model-Qualitaetskriterien section."
    )

    # Check that quality_model_wform.py appears anywhere in _model.md
    # (the criterion row or its annotation must point to the validator)
    assert VALIDATOR_NAME in text, (
        f"'{VALIDATOR_NAME}' does not appear anywhere in _model.md.\n"
        f"The Truth-Atomic-First criterion must reference its mechanical check (the validator)."
    )

    # More specific: validator should appear in the quality-criteria section itself
    assert VALIDATOR_NAME in qc_section, (
        f"'{VALIDATOR_NAME}' not found in the Model-Qualitaetskriterien section.\n"
        f"The Truth-Atomic-First criterion row must reference '{VALIDATOR_NAME}' "
        f"so readers know where the mechanical enforcement lives."
    )
