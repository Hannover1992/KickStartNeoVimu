"""
BL-165 AK-10 PL-10-01 — Modus-Naming Test Suite (Tests 1-5).
Regression guard for Modus-Entscheidungs-System naming conflicts.
"""
import re
import pytest


# ---------------------------------------------------------------------------
# Fixtures — manifest snippets representing pipeline states
# ---------------------------------------------------------------------------

@pytest.fixture
def manifest_post_a():
    """Post-A-Pipeline manifest: modus field must NOT be present."""
    return """
DF_BATCH_STATE:
  pipeline_route: "IDF+SDF"
  routing_decision: "proceed"
  aggregat_score: 80
"""


@pytest.fixture
def manifest_post_idf():
    """Post-IDF manifest: batch_items + k_score_aggregate present, modus absent."""
    return """
DF_BATCH_STATE:
  pipeline_route: "IDF+SDF"
  routing_decision: "proceed"
  batch_items: [PL-1-01, PL-1-02, PL-4-01]
  k_score_aggregate: 60
  srs_aggregate: 40
  batch_type: feature
"""


@pytest.fixture
def manifest_post_sdf_phase_1_1():
    """Post-SDF Phase 1.1 manifest: modus + modus_begruendung + modus_set_by present."""
    return """
SDF_PIPELINE_STATE:
  modus: M3
  modus_set_by: "_SDF_berater_modusEntscheidung"
  modus_begruendung: "Aus k_score=60 + srs=40 + batch_type=feature -> M3"
"""


@pytest.fixture
def kscore_output_clean():
    """K-Score output that contains NO mode recommendation."""
    return """
# K-Score BL-165

k_aufwand: 60
k_kopplung: 55
k_fragilitaet: 70
k_score: 62
k_label: HIGH
lsp_evidence: []
"""


@pytest.fixture
def kscore_output_with_recommendation():
    """K-Score output that illegally contains a mode recommendation."""
    return """
# K-Score BL-165

k_score: 62
Empfehlung M3 basierend auf k_score
"""


@pytest.fixture
def idf_batchplan_output_clean():
    """IDF batchPlan output with NO recommended_modus or sdf_mode_hint."""
    return """
batch_items: [PL-1-01, PL-2-01]
k_score_aggregate: 60
srs_aggregate: 40
batch_type: feature
escalation_hint: SONNET_OK
"""


@pytest.fixture
def idf_batchplan_output_with_hint():
    """IDF batchPlan output that illegally contains recommended_modus."""
    return """
batch_items: [PL-1-01]
recommended_modus: M3
sdf_mode_hint: M3
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestModusNaming:

    def test_1_manifest_modus_post_a(self, manifest_post_a):
        """After A-Pipeline: DF_BATCH_STATE.modus field must NOT be present."""
        # modus field is not allowed — routing_decision is the correct field
        assert "routing_decision" in manifest_post_a, "routing_decision must be present"
        # modus: M{N} pattern must NOT appear (only routing values like proceed/refine/defer allowed)
        modus_pattern = re.compile(r"modus\s*:\s*M[1-9]")
        assert not modus_pattern.search(manifest_post_a), \
            "Post-A manifest must not contain DF_BATCH_STATE.modus = M{N}"

    def test_2_manifest_aggregates_post_idf(self, manifest_post_idf):
        """After IDF: batch_items + k_score_aggregate + srs_aggregate + batch_type present, modus absent."""
        assert "batch_items" in manifest_post_idf, "batch_items must be present post-IDF"
        assert "k_score_aggregate" in manifest_post_idf, "k_score_aggregate must be present post-IDF"
        assert "srs_aggregate" in manifest_post_idf, "srs_aggregate must be present post-IDF"
        assert "batch_type" in manifest_post_idf, "batch_type must be present post-IDF"
        # modus M{N} must NOT appear post-IDF
        modus_pattern = re.compile(r"\bmodus\s*:\s*M[1-9]")
        assert not modus_pattern.search(manifest_post_idf), \
            "Post-IDF manifest must not contain modus = M{N}"

    def test_3_sdf_phase_1_1_pflicht(self, manifest_post_sdf_phase_1_1):
        """After SDF Phase 1.1: modus, modus_begruendung, modus_set_by must be present."""
        assert re.search(r"modus\s*:\s*M[1-9]", manifest_post_sdf_phase_1_1), \
            "modus = M{N} must be set after SDF Phase 1.1"
        assert "modus_begruendung" in manifest_post_sdf_phase_1_1, \
            "modus_begruendung must be present after SDF Phase 1.1"
        assert '_SDF_berater_modusEntscheidung' in manifest_post_sdf_phase_1_1, \
            "modus_set_by must reference _SDF_berater_modusEntscheidung"

    def test_4_kscore_no_recommendation(self, kscore_output_clean, kscore_output_with_recommendation):
        """K-Score output must NOT contain mode recommendation patterns."""
        forbidden_patterns = [
            re.compile(r"Empfehlung\s+M[1-9]", re.IGNORECASE),
            re.compile(r"SDF-Empfehlung", re.IGNORECASE),
            re.compile(r"recommended_modus"),
            re.compile(r"sdf_mode_hint"),
        ]

        # Clean output must pass all checks
        for pat in forbidden_patterns:
            assert not pat.search(kscore_output_clean), \
                f"Clean K-Score output must not match {pat.pattern}"

        # Output with recommendation must trigger at least one pattern (validate fixtures)
        matched = any(pat.search(kscore_output_with_recommendation) for pat in forbidden_patterns)
        assert matched, "Fixture with recommendation must be detected by at least one pattern"

    def test_5_idf_batchplan_no_modus_hint(self, idf_batchplan_output_clean, idf_batchplan_output_with_hint):
        """IDF batchPlan output must NOT contain recommended_modus or sdf_mode_hint."""
        forbidden_keys = ["recommended_modus", "sdf_mode_hint"]

        # Clean output must have none of the forbidden keys
        for key in forbidden_keys:
            assert key not in idf_batchplan_output_clean, \
                f"Clean IDF batchPlan output must not contain '{key}'"

        # Output with hints must be detected (validate fixtures)
        detected = any(key in idf_batchplan_output_with_hint for key in forbidden_keys)
        assert detected, "Fixture with hints must contain at least one forbidden key"
