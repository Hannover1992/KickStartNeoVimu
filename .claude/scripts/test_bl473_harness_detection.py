"""
BL-473 RED-Tests: has_grep_harness + resolve_markdown_uncoverable (Harness-Detektion, behavioral M3-TDD).

RED-Hebel (muessen jetzt FAILEN):
- has_grep_harness existiert nicht -> ImportError beim Versuch, sie zu importieren.
- resolve_markdown_uncoverable hat nur 2 Positionsparameter -> target_files/scripts_dir kwargs -> TypeError.

Kanarienvoegel / Regression-Floors (muessen jetzt SCHON PASSEN):
- test_backward_compat_none_default: 2-arg-Aufruf identisch zu IST (True/False).
- test_no_harness_doku_stays_uncoverable: Doku-.md OHNE Harness -> True (auch mit neuen Params, aber kwargs failen RED).
"""
import sys
import os
import pytest

# Ensure the scripts directory is on the path for direct import (spiegelt test_bl438-Konvention)
sys.path.insert(0, os.path.dirname(__file__))

# Import der bestehenden Funktion (immer verfuegbar, Kanarienvogel-Basis)
from markdown_uncoverable_resolver import resolve_markdown_uncoverable

# Import von has_grep_harness — diese Funktion existiert noch NICHT.
# ImportError / AttributeError faengt alle RED-Hebel die darauf basieren.
try:
    from markdown_uncoverable_resolver import has_grep_harness
    _HAS_GREP_HARNESS_AVAILABLE = True
except (ImportError, AttributeError):
    _HAS_GREP_HARNESS_AVAILABLE = False
    has_grep_harness = None  # Platzhalter damit Tests explizit failen


# ---------------------------------------------------------------------------
# Hilfsfunktion: schreibt eine fake test_*.py-Datei in tmp_path
# ---------------------------------------------------------------------------

def _write_fake_harness(tmp_path, filename, content):
    """Schreibt filename in tmp_path mit gegebenem Inhalt."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# RED-Hebel: has_grep_harness Content-Match
# ---------------------------------------------------------------------------

class TestHasGrepHarnessContentMatch:
    """AK-1a: has_grep_harness("_I_orchestrate", tmp) -> True wenn Content referenziert."""

    def test_has_grep_harness_content_match(self, tmp_path):
        """RED-HEBEL: has_grep_harness nicht verfuegbar -> FAIL (ImportError-Konsequenz)."""
        if not _HAS_GREP_HARNESS_AVAILABLE:
            pytest.fail("has_grep_harness ist nicht in markdown_uncoverable_resolver importierbar (RED erwartet)")
        _write_fake_harness(tmp_path, "test_fake_bl473.py",
                            "# referenziert _I_orchestrate als Ziel\nassert resolve('_I_orchestrate') is not None\n")
        result = has_grep_harness("_I_orchestrate", str(tmp_path))
        assert result is True, f"Erwartet True (Content-Match), got {result!r}"


class TestHasGrepHarnessNoMatch:
    """AK-1b: has_grep_harness("nur_doku_konzept", tmp) -> False (kein test_*.py referenziert)."""

    def test_has_grep_harness_no_match(self, tmp_path):
        """RED-HEBEL: has_grep_harness nicht verfuegbar -> FAIL."""
        if not _HAS_GREP_HARNESS_AVAILABLE:
            pytest.fail("has_grep_harness ist nicht in markdown_uncoverable_resolver importierbar (RED erwartet)")
        _write_fake_harness(tmp_path, "test_other.py",
                            "# referenziert NUR andere Konzepte, nicht nur_doku_konzept\nassert True\n")
        result = has_grep_harness("nur_doku_konzept", str(tmp_path))
        assert result is False, f"Erwartet False (kein Match), got {result!r}"


class TestHasGrepHarnessMdSuffixNormalized:
    """AK-1c: _I_orchestrate.md == _I_orchestrate (beide matchen Content)."""

    def test_has_grep_harness_md_suffix_normalized(self, tmp_path):
        """RED-HEBEL: has_grep_harness nicht verfuegbar -> FAIL."""
        if not _HAS_GREP_HARNESS_AVAILABLE:
            pytest.fail("has_grep_harness ist nicht in markdown_uncoverable_resolver importierbar (RED erwartet)")
        _write_fake_harness(tmp_path, "test_harness_x.py",
                            "# Testfall fuer _I_orchestrate-Logik\npass\n")
        result_with_md = has_grep_harness("_I_orchestrate.md", str(tmp_path))
        result_without_md = has_grep_harness("_I_orchestrate", str(tmp_path))
        assert result_with_md == result_without_md, (
            f"Normalisierung fehlgeschlagen: mit .md={result_with_md!r}, ohne={result_without_md!r}"
        )
        assert result_with_md is True, f"Erwartet True fuer beide Varianten, got {result_with_md!r}"


class TestScriptsDirNoneTolerant:
    """AK-3c: has_grep_harness("x", None) -> False (kein Crash)."""

    def test_scripts_dir_none_tolerant(self):
        """RED-HEBEL: has_grep_harness nicht verfuegbar -> FAIL."""
        if not _HAS_GREP_HARNESS_AVAILABLE:
            pytest.fail("has_grep_harness ist nicht in markdown_uncoverable_resolver importierbar (RED erwartet)")
        result = has_grep_harness("x", None)
        assert result is False, f"Erwartet False bei scripts_dir=None, got {result!r}"


# ---------------------------------------------------------------------------
# RED-Hebel: resolve_markdown_uncoverable mit neuen kwargs
# ---------------------------------------------------------------------------

class TestHarnessPresentMdTargetReturnsTestable:
    """AK-1d: Harness-present + .md-Target -> resolver False (Harness dominiert)."""

    def test_harness_present_md_target_returns_testable(self, tmp_path):
        """RED-HEBEL: kwargs target_files/scripts_dir noch nicht vorhanden -> TypeError."""
        _write_fake_harness(tmp_path, "test_bl464_i_state_machine.py",
                            "# Harness referenziert _I_orchestrate vielfach\n"
                            "# _I_orchestrate wird hier getestet\npass\n")
        coverage_entry = {"coverage_class": "markdown_target_uncoverable"}
        metric_entry = {}
        # Dieser Aufruf wirft TypeError (unbekannte kwargs) -> RED
        result = resolve_markdown_uncoverable(
            coverage_entry,
            metric_entry,
            target_files=["_I_orchestrate.md"],
            scripts_dir=str(tmp_path),
        )
        assert result is False, (
            f"Erwartet False (Harness dominiert), got {result!r}"
        )


class TestDeterminismNCallsIdentical:
    """AK-2a: 10x derselbe Call mit Harness -> alle False (deterministisch)."""

    def test_determinism_n_calls_identical(self, tmp_path):
        """RED-HEBEL: kwargs fehlen -> TypeError."""
        _write_fake_harness(tmp_path, "test_det_harness.py",
                            "# referenziert _I_orchestrate\npass\n")
        coverage_entry = {"coverage_class": "markdown_target_uncoverable"}
        metric_entry = {}
        results = [
            resolve_markdown_uncoverable(
                coverage_entry,
                metric_entry,
                target_files=["_I_orchestrate.md"],
                scripts_dir=str(tmp_path),
            )
            for _ in range(10)
        ]
        unique = set(results)
        assert len(unique) == 1, f"Nicht deterministisch: {unique!r}"
        assert all(r is False for r in results), f"Erwartete alle False, got {results!r}"


class TestHarnessDominatesBothSignalOrte:
    """AK-2b/2c: Harness dominiert BEIDE Signal-Orte (coverage_class UND befund)."""

    def test_harness_dominates_coverage_class_signal(self, tmp_path):
        """RED-HEBEL: kwargs fehlen -> TypeError."""
        _write_fake_harness(tmp_path, "test_harness_dom_cc.py",
                            "# referenziert _I_orchestrate\npass\n")
        result = resolve_markdown_uncoverable(
            {"coverage_class": "markdown_target_uncoverable"},
            {},
            target_files=["_I_orchestrate.md"],
            scripts_dir=str(tmp_path),
        )
        assert result is False, (
            f"Harness muss coverage_class-Signal dominieren, got {result!r}"
        )

    def test_harness_dominates_befund_signal(self, tmp_path):
        """RED-HEBEL: kwargs fehlen -> TypeError."""
        _write_fake_harness(tmp_path, "test_harness_dom_befund.py",
                            "# referenziert _I_orchestrate\npass\n")
        result = resolve_markdown_uncoverable(
            {"markdown_uncoverable_befund": True},
            {"special_flags": ["markdown_uncoverable"]},
            target_files=["_I_orchestrate.md"],
            scripts_dir=str(tmp_path),
        )
        assert result is False, (
            f"Harness muss befund+special_flags-Signal dominieren, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Kanarienvoegel / Regression-Floors (muessen JETZT SCHON passen)
# ---------------------------------------------------------------------------

class TestBackwardCompatNoneDefault:
    """AK-3b: 2-arg-Aufruf (ohne neue kwargs) byte-identisch zum IST-Verhalten."""

    def test_backward_compat_coverage_class_true(self):
        """FLOOR (heute GREEN): markdown_target_uncoverable -> True (2-arg)."""
        coverage_entry = {"coverage_class": "markdown_target_uncoverable"}
        metric_entry = {}
        assert resolve_markdown_uncoverable(coverage_entry, metric_entry) is True

    def test_backward_compat_no_signal_false(self):
        """FLOOR (heute GREEN): kein Signal -> False (2-arg)."""
        coverage_entry = {}
        metric_entry = {}
        assert resolve_markdown_uncoverable(coverage_entry, metric_entry) is False

    def test_backward_compat_none_args_false(self):
        """FLOOR (heute GREEN): beide None -> False (2-arg)."""
        assert resolve_markdown_uncoverable(None, None) is False

    def test_backward_compat_special_flags_true(self):
        """FLOOR (heute GREEN): special_flags markdown_uncoverable -> True (2-arg)."""
        assert resolve_markdown_uncoverable(
            {},
            {"special_flags": ["markdown_uncoverable"]}
        ) is True


class TestNoHarnessDokuMdStaysUncoverable:
    """AK-3a: .md-Target OHNE Harness + coverage_class -> resolver True (M2 bleibt).

    Hinweis: dieser Test verwendet die neuen kwargs (target_files/scripts_dir).
    Mit dem IST-Stand wird er wegen TypeError failen -> RED-Hebel.
    Nach GREEN-Bau: scripts_dir ohne passenden Test-Inhalt -> 5-Signal-Kaskade aktiv -> True.
    """

    def test_no_harness_doku_stays_uncoverable(self, tmp_path):
        """RED-HEBEL (heute: TypeError wegen kwargs) / GREEN-Ziel: True (M2 bleibt)."""
        # tmp_path enthaelt KEIN test_*.py mit Referenz auf pure_doc
        coverage_entry = {"coverage_class": "markdown_target_uncoverable"}
        metric_entry = {}
        result = resolve_markdown_uncoverable(
            coverage_entry,
            metric_entry,
            target_files=["pure_doc.md"],
            scripts_dir=str(tmp_path),
        )
        assert result is True, (
            f"Doku-.md ohne Harness muss True/M2 liefern, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Optionaler Integrations-Test gegen echte .claude/scripts
# ---------------------------------------------------------------------------

class TestIntegrationRealScripts:
    """Integration: echte .claude/scripts-Verzeichnis enthaelt test_bl464/465 -> Harness fuer _I_orchestrate vorhanden."""

    def test_real_scripts_i_orchestrate_has_harness(self):
        """Integrations-Assertion: echte test_bl464_*/test_bl465_* referenzieren _I_orchestrate im Content."""
        if not _HAS_GREP_HARNESS_AVAILABLE:
            pytest.fail("has_grep_harness nicht verfuegbar (RED erwartet)")
        real_scripts = os.path.dirname(__file__)
        result = has_grep_harness("_I_orchestrate", real_scripts)
        assert result is True, (
            f"Erwartet True (test_bl464/465 referenzieren _I_orchestrate im Content), got {result!r}"
        )
