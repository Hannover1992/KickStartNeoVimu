"""
BL-438 RED-Tests: resolve_markdown_uncoverable(coverage_entry, metric_entry) -> bool
Neue Funktion in markdown_uncoverable_resolver.py (noch NICHT erstellt -> RED).
"""
import sys
import os

# Ensure the scripts directory is on the path for direct import
sys.path.insert(0, os.path.dirname(__file__))

from markdown_uncoverable_resolver import resolve_markdown_uncoverable


class TestResolveCoverageClass:
    """Test 1: coverage_class == 'markdown_target_uncoverable' -> True (BL-314-Pfad)."""

    def test_coverage_class_true(self):
        coverage_entry = {"coverage_class": "markdown_target_uncoverable"}
        metric_entry = {}
        assert resolve_markdown_uncoverable(coverage_entry, metric_entry) is True


class TestResolveBefund:
    """Test 2: markdown_uncoverable_befund == True -> True."""

    def test_befund_true(self):
        coverage_entry = {"coverage_class": "other_class", "markdown_uncoverable_befund": True}
        metric_entry = {}
        assert resolve_markdown_uncoverable(coverage_entry, metric_entry) is True


class TestResolveSpecialFlagsFallback:
    """Test 3: BL-438-FIX - special_flags-only-Signal wird gefangen."""

    def test_special_flags_fallback_true_markdown_uncoverable_class(self):
        # coverage_class leer, ABER metric special_flags enthaelt 'markdown_uncoverable_class'
        coverage_entry = {"coverage_class": None}
        metric_entry = {"special_flags": ["markdown_uncoverable_class"]}
        assert resolve_markdown_uncoverable(coverage_entry, metric_entry) is True

    def test_special_flags_fallback_true_markdown_uncoverable(self):
        # coverage_class fehlt, ABER metric special_flags enthaelt 'markdown_uncoverable'
        coverage_entry = {}
        metric_entry = {"special_flags": ["markdown_uncoverable"]}
        assert resolve_markdown_uncoverable(coverage_entry, metric_entry) is True


class TestResolveNoSignal:
    """Test 4: kein Signal in beiden -> False (kein false-positive)."""

    def test_no_signal_false(self):
        coverage_entry = {"coverage_class": "some_other_class", "markdown_uncoverable_befund": False}
        metric_entry = {"special_flags": ["some_other_flag"]}
        assert resolve_markdown_uncoverable(coverage_entry, metric_entry) is False

    def test_empty_dicts_false(self):
        coverage_entry = {}
        metric_entry = {}
        assert resolve_markdown_uncoverable(coverage_entry, metric_entry) is False


class TestResolveNoneTolerant:
    """Test 5: None-Toleranz - kein Crash bei None-Eingaben."""

    def test_both_none_false(self):
        assert resolve_markdown_uncoverable(None, None) is False

    def test_coverage_none_false(self):
        assert resolve_markdown_uncoverable(None, {"special_flags": []}) is False

    def test_metric_none_false(self):
        assert resolve_markdown_uncoverable({"coverage_class": None}, None) is False

    def test_coverage_none_metric_with_flag_true(self):
        # metric hat special_flag, coverage ist None -> True (fallback greift)
        assert resolve_markdown_uncoverable(None, {"special_flags": ["markdown_uncoverable_class"]}) is True
