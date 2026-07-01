"""
BL-205 AK-8 — compute_srs Edge-Case Tests.
Validates INV-SRS-1..4 and all status weight assignments.
"""
import pytest


SRS_WEIGHT = {
    "BESTAETIGT":         0.0,
    "BESTAETIGT-DB":      0.0,
    "STABLE":             0.0,
    "AKTIV (BESTAETIGT)": 0.0,
    "RESOLVED":           0.0,
    "RESOLVED-DB":        0.0,
    "CLOSED":             0.0,
    "TENTATIV":           1.0,
    "HYPOTHESE":          1.0,
    "OFFEN":              1.0,
}

INTERN_PREFIXES = ("Repo:", "Crumbs:", "Assays:", "W_fetch:")
EXTERN_PREFIXES = ("Wiki:", "URL:", "Stakeholder:", "Industry-Standard:")


class WRef:
    def __init__(self, id, status, source="Repo: unknown"):
        self.id = id
        self.status = status
        self.source = source


def compute_srs(w_refs):
    w_refs_active = [w for w in w_refs if w.status != "RETRACTED"]
    if len(w_refs_active) == 0:
        return {"srs": 100, "flag": "no_truth_refs", "breakdown": []}
    if any(w.status not in SRS_WEIGHT and w.status != "RETRACTED" for w in w_refs):
        raise ValueError(f"INV-SRS-1: Unknown status in w_refs")
    unsicher_sum = sum(SRS_WEIGHT[w.status] for w in w_refs_active)
    srs = round((unsicher_sum / len(w_refs_active)) * 100, 1)
    return {
        "srs": srs,
        "flag": None,
        "breakdown": [{"id": w.id, "status": w.status, "weight": SRS_WEIGHT[w.status]}
                      for w in w_refs_active],
    }


def compute_bottleneck_signal(w_refs):
    w_refs_active = [w for w in w_refs if w.status != "RETRACTED"]
    unsicher_intern = sum(
        1 for w in w_refs_active
        if SRS_WEIGHT.get(w.status, 0.0) == 1.0
        and any(w.source.startswith(p) for p in INTERN_PREFIXES)
    )
    unsicher_extern = sum(
        1 for w in w_refs_active
        if SRS_WEIGHT.get(w.status, 0.0) == 1.0
        and not any(w.source.startswith(p) for p in INTERN_PREFIXES)
    )
    if unsicher_extern > 0:
        return "WP"
    elif unsicher_intern > 0:
        return "SC"
    return None


class TestComputeSrsEdgeCases:

    def test_no_truth_refs_returns_100(self):
        """INV-SRS-3: empty w_refs → srs=100, flag=no_truth_refs."""
        result = compute_srs([])
        assert result["srs"] == 100
        assert result["flag"] == "no_truth_refs"
        assert result["breakdown"] == []

    def test_all_bestaetigt_returns_0(self):
        """All confirmed refs → SRS=0."""
        refs = [WRef("W1", "BESTAETIGT"), WRef("W2", "BESTAETIGT-DB"), WRef("W3", "STABLE")]
        result = compute_srs(refs)
        assert result["srs"] == 0.0
        assert result["flag"] is None

    def test_all_open_returns_100(self):
        """All uncertain refs → SRS=100."""
        refs = [WRef("W1", "TENTATIV"), WRef("W2", "HYPOTHESE"), WRef("W3", "OFFEN")]
        result = compute_srs(refs)
        assert result["srs"] == 100.0
        assert result["flag"] is None

    def test_retracted_excluded_from_denominator(self):
        """INV-SRS-2: RETRACTED does not count in denominator."""
        refs = [WRef("W-RETR", "RETRACTED"), WRef("W-OK", "BESTAETIGT")]
        result = compute_srs(refs)
        assert len(result["breakdown"]) == 1
        assert result["breakdown"][0]["id"] == "W-OK"
        assert result["srs"] == 0.0

    def test_only_retracted_triggers_no_truth_refs(self):
        """INV-SRS-2 + INV-SRS-3: all RETRACTED → w_refs_active=[] → srs=100."""
        refs = [WRef("W1", "RETRACTED"), WRef("W2", "RETRACTED")]
        result = compute_srs(refs)
        assert result["srs"] == 100
        assert result["flag"] == "no_truth_refs"

    def test_mixed_bestaetigt_and_tentativ(self):
        """50% uncertain → SRS=50."""
        refs = [WRef("W1", "BESTAETIGT"), WRef("W2", "TENTATIV")]
        result = compute_srs(refs)
        assert result["srs"] == 50.0

    def test_dcsre_486_global_srs(self):
        """AK-10 fixture: w_total=59, w_offen=2 → SRS≈3.4 (BL-205 Spec S-6)."""
        refs = (
            [WRef(f"W-S{i}", "BESTAETIGT") for i in range(57)]
            + [WRef("W-O1", "TENTATIV"), WRef("W-O2", "HYPOTHESE")]
        )
        result = compute_srs(refs)
        assert result["srs"] == pytest.approx(3.4, abs=0.05)

    def test_status_transition_srs_drops(self):
        """After TENTATIV→CLOSED: SRS drops from 50 to 0."""
        refs_before = [WRef("W1", "BESTAETIGT"), WRef("W2", "TENTATIV")]
        refs_after = [WRef("W1", "BESTAETIGT"), WRef("W2", "CLOSED")]
        assert compute_srs(refs_before)["srs"] == 50.0
        assert compute_srs(refs_after)["srs"] == 0.0

    def test_inv_srs_1_unknown_status_raises(self):
        """INV-SRS-1: unknown status value must raise ValueError."""
        refs = [WRef("W1", "UNKNOWN_STATUS")]
        with pytest.raises(ValueError, match="INV-SRS-1"):
            compute_srs(refs)

    def test_all_secure_status_values_map_to_zero(self):
        """Every secure status must yield weight 0.0."""
        secure = ["BESTAETIGT", "BESTAETIGT-DB", "STABLE", "AKTIV (BESTAETIGT)",
                  "RESOLVED", "RESOLVED-DB", "CLOSED"]
        for status in secure:
            assert SRS_WEIGHT[status] == 0.0, f"{status} should be 0.0"

    def test_all_uncertain_status_values_map_to_one(self):
        """Every uncertain status must yield weight 1.0."""
        uncertain = ["TENTATIV", "HYPOTHESE", "OFFEN"]
        for status in uncertain:
            assert SRS_WEIGHT[status] == 1.0, f"{status} should be 1.0"

    def test_rounding_to_one_decimal(self):
        """SRS is rounded to 1 decimal place."""
        refs = [WRef(f"W{i}", "BESTAETIGT") for i in range(3)] + [WRef("W3", "OFFEN")]
        result = compute_srs(refs)
        assert result["srs"] == 25.0

    def test_breakdown_excludes_retracted(self):
        """breakdown[] contains only active (non-RETRACTED) refs."""
        refs = [WRef("W-R", "RETRACTED"), WRef("W-A", "OFFEN"), WRef("W-B", "BESTAETIGT")]
        result = compute_srs(refs)
        ids = [b["id"] for b in result["breakdown"]]
        assert "W-R" not in ids
        assert "W-A" in ids
        assert "W-B" in ids

    def test_akfree_evaluation(self):
        """T-AKFREE (BL-312 AK-7): SRS-Bewertung ist AK-FREI. Ein Item, dessen SRS
        rein aus model_refs/W{n}-status (WRef-Objekte) kommt, OHNE jegliches ak_ref-Feld,
        liefert valides srs (kein KeyError, kein ak-Gating). Dokumentiert AK-7 als
        bereits-AK-frei: WRef traegt nur (id, status, source) — kein ak_ref noetig."""
        refs = [WRef("W1", "BESTAETIGT"), WRef("W2", "OFFEN")]
        assert not any(hasattr(w, "ak_ref") for w in refs), \
            "WRef ist AK-frei: kein ak_ref-Feld (Basis ist PL<->W-Ref/model_refs)"
        result = compute_srs(refs)
        assert result["srs"] == 50.0, \
            f"AK-frei: srs rein aus W{{n}}-status, erwartet 50.0, war {result['srs']!r}"
        assert result["flag"] is None, \
            f"valide Bewertung (kein no_truth_refs/kein ak-Gating), war flag={result['flag']!r}"


class TestBottleneckSignal:

    def test_no_unsicher_returns_null(self):
        """SRS=0 → bottleneck_signal=null."""
        refs = [WRef("W1", "BESTAETIGT", "Repo: svc.py")]
        assert compute_bottleneck_signal(refs) is None

    def test_intern_unsicher_returns_sc(self):
        """Unsicher + INTERN source → bottleneck_signal=SC."""
        refs = [WRef("W1", "OFFEN", "Repo: legacy.py")]
        assert compute_bottleneck_signal(refs) == "SC"

    def test_extern_unsicher_returns_wp(self):
        """Unsicher + EXTERN source → bottleneck_signal=WP."""
        refs = [WRef("W1", "TENTATIV", "Wiki: Confluence#spec")]
        assert compute_bottleneck_signal(refs) == "WP"

    def test_extern_dominates_over_intern(self):
        """Mixed INTERN+EXTERN unsicher → WP (EXTERN dominates)."""
        refs = [
            WRef("W1", "OFFEN", "Repo: svc.py"),
            WRef("W2", "HYPOTHESE", "URL: https://example.com"),
        ]
        assert compute_bottleneck_signal(refs) == "WP"

    def test_retracted_not_counted_for_signal(self):
        """RETRACTED excluded from bottleneck signal computation."""
        refs = [
            WRef("W1", "RETRACTED", "Wiki: spec"),
            WRef("W2", "BESTAETIGT", "Repo: svc.py"),
        ]
        assert compute_bottleneck_signal(refs) is None
