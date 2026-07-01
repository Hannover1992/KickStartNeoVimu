"""
test_disjunktheit_validator.py — BL-460 B-3a RED-Phase (Stage 1 unit, M3).

Tests fuer disjunktheit_validator.validate_disjoint(slices, full_corpus):
  - disjoint+complete slices -> (True, "")
  - a view in two slices -> (False, reason naming the overlap)
  - a view missing from all slices (union != corpus) -> (False, reason)
  - CLI exit 0 disjoint / 1 violation / 2 usage

GOLD-Kriterien (Blueprint G1-5..G1-8):
  G1-5: validate_disjoint(decompose_output, corpus) -> (True, "")
  G1-6: CLI exit 0 bei disjunkter Validierung
  G1-7: Duplikat (View in 2 Slices) -> (False, reason naming the view path)
  G1-8: Luecke (View fehlt) -> (False, reason)

RED-STATE: disjunktheit_validator.py existiert NICHT -> alle Tests schlagen mit ModuleNotFoundError fehl.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

import disjunktheit_validator  # noqa: E402  (RED: Modul existiert noch nicht)


# ---------------------------------------------------------------------------
# K (Kern): disjunkte + vollstaendige Slices -> (True, "")
# ---------------------------------------------------------------------------

def test_disjoint_complete_slices_returns_true(tmp_path):
    """
    K (G1-5): Disjunkte Slices die den vollen Corpus abdecken -> (True, "").
    """
    view_a = str(tmp_path / "view_a.md")
    view_b = str(tmp_path / "view_b.md")
    view_c = str(tmp_path / "view_c.md")
    view_d = str(tmp_path / "view_d.md")

    slices = [[view_a, view_b], [view_c, view_d]]
    full_corpus = [view_a, view_b, view_c, view_d]

    ok, reason = disjunktheit_validator.validate_disjoint(slices, full_corpus)

    assert ok is True
    assert reason == ""


def test_single_slice_equals_corpus_returns_true(tmp_path):
    """
    B: 1 Slice = ganzer Corpus -> (True, "").
    """
    views = [str(tmp_path / f"view_{i}.md") for i in range(5)]
    slices = [views[:]]
    full_corpus = views[:]

    ok, reason = disjunktheit_validator.validate_disjoint(slices, full_corpus)

    assert ok is True
    assert reason == ""


def test_empty_slices_empty_corpus_returns_true():
    """
    B: Leere Slices + leerer Corpus -> (True, "") — kein Crash.
    """
    ok, reason = disjunktheit_validator.validate_disjoint([], [])

    assert ok is True
    assert reason == ""


def test_three_slices_disjoint_returns_true(tmp_path):
    """
    K: 3 disjunkte Slices -> (True, "").
    """
    views = [str(tmp_path / f"v{i}.md") for i in range(9)]
    slices = [views[0:3], views[3:6], views[6:9]]
    full_corpus = views[:]

    ok, reason = disjunktheit_validator.validate_disjoint(slices, full_corpus)

    assert ok is True
    assert reason == ""


# ---------------------------------------------------------------------------
# K (Kern): View in zwei Slices -> (False, reason naming the view)
# ---------------------------------------------------------------------------

def test_duplicate_view_in_two_slices_returns_false(tmp_path):
    """
    K (G1-7): Ein View-Pfad erscheint in zwei Slices -> (False, reason).
    reason muss den betroffenen Pfad nennen.
    """
    duplicate_view = str(tmp_path / "duplicate.md")
    view_b = str(tmp_path / "view_b.md")
    view_c = str(tmp_path / "view_c.md")

    # duplicate_view erscheint in BEIDEN Slices
    slices = [[duplicate_view, view_b], [duplicate_view, view_c]]
    full_corpus = [duplicate_view, view_b, view_c]

    ok, reason = disjunktheit_validator.validate_disjoint(slices, full_corpus)

    assert ok is False
    assert reason != ""
    # reason muss den konkreten doppelten Pfad nennen
    assert "duplicate.md" in reason or duplicate_view in reason


def test_multiple_duplicates_reason_mentions_overlap(tmp_path):
    """
    K: Mehrere Duplikate -> (False, reason) — reason beschreibt die Ueberschneidung.
    """
    v1 = str(tmp_path / "v1.md")
    v2 = str(tmp_path / "v2.md")
    v3 = str(tmp_path / "v3.md")

    # v1 und v2 beide in Slice 0 UND Slice 1
    slices = [[v1, v2, v3], [v1, v2]]
    full_corpus = [v1, v2, v3]

    ok, reason = disjunktheit_validator.validate_disjoint(slices, full_corpus)

    assert ok is False
    assert reason != ""


# ---------------------------------------------------------------------------
# K (Kern): View fehlt in allen Slices -> (False, reason)
# ---------------------------------------------------------------------------

def test_missing_view_from_all_slices_returns_false(tmp_path):
    """
    K (G1-8): Ein View ist im Corpus aber in keinem Slice -> (False, reason).
    """
    view_a = str(tmp_path / "view_a.md")
    view_b = str(tmp_path / "view_b.md")
    missing_view = str(tmp_path / "missing.md")

    # missing_view ist im Corpus aber fehlt in den Slices
    slices = [[view_a, view_b]]
    full_corpus = [view_a, view_b, missing_view]

    ok, reason = disjunktheit_validator.validate_disjoint(slices, full_corpus)

    assert ok is False
    assert reason != ""
    # reason sollte den fehlenden Pfad erwaehnen
    assert "missing.md" in reason or missing_view in reason


def test_extra_view_in_slices_not_in_corpus_returns_false(tmp_path):
    """
    K: Ein View ist in einem Slice aber NICHT im Corpus -> (False, reason).
    Union > Corpus = Violation.
    """
    view_a = str(tmp_path / "view_a.md")
    extra_view = str(tmp_path / "extra.md")

    # extra_view ist in Slice aber nicht im Corpus
    slices = [[view_a, extra_view]]
    full_corpus = [view_a]

    ok, reason = disjunktheit_validator.validate_disjoint(slices, full_corpus)

    assert ok is False
    assert reason != ""


# ---------------------------------------------------------------------------
# A (Ausnahme): Pfad-Normierung (Windows/Unix)
# ---------------------------------------------------------------------------

def test_path_normalization_handles_mixed_separators(tmp_path):
    """
    A: Gemischte Pfad-Separatoren (Windows vs Unix) werden korrekt normiert.
    validate_disjoint erkennt view_a/forward als identisch mit view_a\backslash.
    """
    # Erstelle Pfade mit verschiedenen Separatoren
    base = str(tmp_path)
    # Normierung via os.path.normcase sollte Unterschiede ausgleichen
    view_forward = base + "/view.md"
    view_backward = base + "\\view.md"

    # Wenn view_forward und view_backward dasselbe Dateisystem-Objekt sind,
    # muss validate_disjoint eine Violation erkennen (Duplikat nach Normierung)
    if os.path.normcase(view_forward) == os.path.normcase(view_backward):
        slices = [[view_forward], [view_backward]]
        full_corpus = [view_forward]  # nur einer davon im Corpus

        ok, reason = disjunktheit_validator.validate_disjoint(slices, full_corpus)
        # Nach Normierung: Duplikat erkannt -> FAIL
        assert ok is False
    else:
        # Auf POSIX: Backslash ist valider Dateiname, kein normcase-Effekt
        # Test ist plattformabhaengig — skip ist OK, kein Assertion-Fehler
        pass


# ---------------------------------------------------------------------------
# CLI exit codes via main([...]) — DT-5-Konvention
# ---------------------------------------------------------------------------

def test_cli_exit_0_for_disjoint_input(tmp_path, capsys):
    """
    K (G1-6): CLI main([...]) gibt 0 zurueck bei disjunkten + vollstaendigen Slices.
    """
    v1 = str(tmp_path / "v1.md")
    v2 = str(tmp_path / "v2.md")

    slices_input = [[v1], [v2]]
    corpus = [v1, v2]

    payload = json.dumps({"slices": slices_input, "full_corpus": corpus})

    # Stdin-Modus via --stdin-json Argument
    exit_code = disjunktheit_validator.main(["--stdin-json", payload])

    assert exit_code == 0


def test_cli_exit_1_for_violation(tmp_path):
    """
    CLI main([...]) gibt 1 zurueck bei Verletzung (Duplikat).
    """
    v1 = str(tmp_path / "v1.md")
    v2 = str(tmp_path / "v2.md")

    # v1 in beiden Slices
    slices_input = [[v1, v2], [v1]]
    corpus = [v1, v2]

    payload = json.dumps({"slices": slices_input, "full_corpus": corpus})

    exit_code = disjunktheit_validator.main(["--stdin-json", payload])

    assert exit_code == 1


def test_cli_exit_2_for_usage_error():
    """
    CLI main([...]) gibt 2 zurueck bei Usage-Fehler (keine Args, kein Stdin).
    """
    try:
        exit_code = disjunktheit_validator.main(["--invalid-flag-xyz"])
        assert exit_code == 2
    except SystemExit as e:
        assert e.code == 2


def test_cli_stdout_pass_message_for_disjoint(tmp_path, capsys):
    """
    CLI gibt PASS-Meldung auf stdout bei disjunkter Eingabe.
    """
    v1 = str(tmp_path / "a.md")
    v2 = str(tmp_path / "b.md")

    payload = json.dumps({"slices": [[v1], [v2]], "full_corpus": [v1, v2]})

    disjunktheit_validator.main(["--stdin-json", payload])

    captured = capsys.readouterr()
    # Stdout muss PASS-Aussage enthalten
    assert "PASS" in captured.out or "disjoint" in captured.out.lower() or \
           ("valid" in captured.out.lower())


def test_cli_stdout_fail_message_for_violation(tmp_path, capsys):
    """
    CLI gibt VIOLATION/FAIL-Meldung auf stdout bei Verletzung.
    """
    v1 = str(tmp_path / "dup.md")

    # v1 in beiden Slices
    payload = json.dumps({"slices": [[v1], [v1]], "full_corpus": [v1]})

    disjunktheit_validator.main(["--stdin-json", payload])

    captured = capsys.readouterr()
    assert "VIOLATION" in captured.out or "FAIL" in captured.out or \
           "violation" in captured.out.lower()
