"""
test_schwarm_decomposer.py — BL-460 B-3a RED-Phase (Stage 1 unit, M3).

Tests fuer schwarm_decomposer.decompose_views(vault_root, n_slices):
  - returns N slices; every view in EXACTLY one slice (disjoint)
  - union == full corpus (completeness)
  - deterministic (same input -> same partition)
  - handles n_slices > view_count, n_slices=1, empty corpus gracefully
  - CLI exit codes (0/1/2)

GOLD-Kriterien (Blueprint G1-1..G1-8):
  G1-1: union == set(full_corpus)
  G1-2: no view in two slices (pairwise disjoint)
  G1-3: deterministic (2x same input -> same partition)
  G1-4: n_slices=1 -> 1 slice containing all views
  G1-6: CLI exit 0 on success
  G1-7: manual overlap -> validate_disjoint returns (False, reason naming the view)
  G1-8: missing view -> validate_disjoint returns (False, reason)

RED-STATE: schwarm_decomposer.py existiert NICHT -> alle Tests schlagen mit ModuleNotFoundError fehl.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

import schwarm_decomposer  # noqa: E402  (RED: Modul existiert noch nicht)


# ---------------------------------------------------------------------------
# Fixture-Hilfsfunktionen
# ---------------------------------------------------------------------------

def _make_vault_with_views(tmp_path, n_views=6):
    """Erstellt einen minimalen Vault mit n Views als .md-Dateien unter Models-Pfad."""
    vault = tmp_path / "vault"
    models_dir = vault / "Backlog" / "BL-001" / "2_Model"
    models_dir.mkdir(parents=True)
    for i in range(n_views):
        (models_dir / f"View_{i:03d}_Model.md").write_text(
            f"# View {i}\nsome content\n", encoding="utf-8"
        )
    return vault


# ---------------------------------------------------------------------------
# K (Kern): n_slices=1 -> 1 Slice, alle Views drin
# ---------------------------------------------------------------------------

def test_n_slices_1_returns_single_slice_with_all_views(tmp_path):
    """
    K (G1-4): decompose_views mit n_slices=1 gibt genau 1 Slice zurueck,
    der alle Views enthaelt.
    """
    vault = _make_vault_with_views(tmp_path, n_views=5)

    result = schwarm_decomposer.decompose_views(str(vault), n_slices=1)

    assert len(result) == 1
    assert len(result[0]) == 5


def test_n_slices_3_returns_three_slices(tmp_path):
    """
    K: decompose_views mit n_slices=3 gibt genau 3 Slices zurueck.
    """
    vault = _make_vault_with_views(tmp_path, n_views=9)

    result = schwarm_decomposer.decompose_views(str(vault), n_slices=3)

    assert len(result) == 3


def test_union_of_slices_equals_full_corpus(tmp_path):
    """
    K (G1-1): Die Vereinigung aller Slices == alle Views im Vault (completeness).
    """
    vault = _make_vault_with_views(tmp_path, n_views=6)

    result = schwarm_decomposer.decompose_views(str(vault), n_slices=3)

    union = set()
    for sl in result:
        union.update(sl)

    # Hole den vollen Corpus direkt aus dem Vault zur Verifikation
    full_corpus = set()
    for f in (vault / "Backlog" / "BL-001" / "2_Model").rglob("*.md"):
        full_corpus.add(str(f))

    assert union == full_corpus


def test_each_view_in_exactly_one_slice(tmp_path):
    """
    K (G1-2): Jede View erscheint in GENAU einem Slice — keine Duplikate, keine Luecken.
    """
    vault = _make_vault_with_views(tmp_path, n_views=9)

    result = schwarm_decomposer.decompose_views(str(vault), n_slices=3)

    # Alle Views aus allen Slices sammeln
    all_views_flat = [v for sl in result for v in sl]

    # Keine Duplikate
    assert len(all_views_flat) == len(set(all_views_flat)), \
        f"Duplicate views found across slices: {len(all_views_flat)} total vs {len(set(all_views_flat))} unique"


def test_pairwise_disjoint_slices(tmp_path):
    """
    K (G1-2): Paarweise Schnittmenge aller Slices ist leer (vollstaendig disjunkt).
    """
    vault = _make_vault_with_views(tmp_path, n_views=9)

    result = schwarm_decomposer.decompose_views(str(vault), n_slices=3)

    slice_sets = [set(sl) for sl in result]
    for i in range(len(slice_sets)):
        for j in range(i + 1, len(slice_sets)):
            intersection = slice_sets[i] & slice_sets[j]
            assert len(intersection) == 0, \
                f"Slices {i} and {j} share views: {intersection}"


# ---------------------------------------------------------------------------
# K (Kern): Determinismus
# ---------------------------------------------------------------------------

def test_deterministic_same_input_same_partition(tmp_path):
    """
    K (G1-3): Zweimaliger Aufruf mit gleichem Input liefert identische Partition.
    """
    vault = _make_vault_with_views(tmp_path, n_views=12)

    result_1 = schwarm_decomposer.decompose_views(str(vault), n_slices=4)
    result_2 = schwarm_decomposer.decompose_views(str(vault), n_slices=4)

    # Slices normieren (innere Listen sortieren) fuer Vergleich
    normalized_1 = [sorted(sl) for sl in result_1]
    normalized_2 = [sorted(sl) for sl in result_2]

    assert normalized_1 == normalized_2, \
        "Non-deterministic: two runs with same input produced different partitions"


# ---------------------------------------------------------------------------
# B (Boundary): n_slices > len(views)
# ---------------------------------------------------------------------------

def test_n_slices_greater_than_view_count_no_crash(tmp_path):
    """
    B: n_slices > Anzahl Views → manche Slices leer, kein Crash.
    """
    vault = _make_vault_with_views(tmp_path, n_views=3)

    result = schwarm_decomposer.decompose_views(str(vault), n_slices=10)

    # Muss genau n_slices Elemente haben (manche davon leer)
    assert len(result) == 10
    # Alle Views muessen in irgendeinem Slice sein
    all_views = [v for sl in result for v in sl]
    assert len(all_views) == 3


def test_empty_corpus_returns_n_empty_slices(tmp_path):
    """
    B: Leerer Vault (0 Views) → N leere Slices, kein Crash.
    """
    vault = tmp_path / "empty_vault"
    vault.mkdir()

    result = schwarm_decomposer.decompose_views(str(vault), n_slices=3)

    # Muss 3 leere Slices zurueckgeben (oder 0 Slices — kein Crash)
    assert isinstance(result, list)
    total_views = sum(len(sl) for sl in result)
    assert total_views == 0


# ---------------------------------------------------------------------------
# A (Ausnahme): Fehlerbehandlung
# ---------------------------------------------------------------------------

def test_n_slices_zero_raises_value_error(tmp_path):
    """
    A: n_slices=0 → ValueError (guard — ungueltige Partition).
    """
    vault = _make_vault_with_views(tmp_path, n_views=3)

    try:
        schwarm_decomposer.decompose_views(str(vault), n_slices=0)
        raise AssertionError("Expected ValueError fuer n_slices=0 wurde nicht geworfen")
    except ValueError:
        pass  # erwartet


def test_n_slices_negative_raises_value_error(tmp_path):
    """
    A: n_slices=-1 → ValueError.
    """
    vault = _make_vault_with_views(tmp_path, n_views=3)

    try:
        schwarm_decomposer.decompose_views(str(vault), n_slices=-1)
        raise AssertionError("Expected ValueError fuer n_slices=-1 wurde nicht geworfen")
    except ValueError:
        pass  # erwartet


def test_nonexistent_vault_root_raises_or_empty(tmp_path):
    """
    A: vault_root existiert nicht → IOError propagiert ODER sauberes empty-result (kein Crash).
    """
    fake_vault = str(tmp_path / "does_not_exist")

    try:
        result = schwarm_decomposer.decompose_views(fake_vault, n_slices=1)
        # Wenn kein Fehler: muss leere Liste sein
        assert isinstance(result, list)
        total = sum(len(sl) for sl in result)
        assert total == 0
    except (IOError, OSError):
        pass  # auch erlaubt


# ---------------------------------------------------------------------------
# CLI exit codes via main([...]) — DT-5-Konvention
# ---------------------------------------------------------------------------

def test_cli_exit_0_on_success(tmp_path):
    """
    CLI main([...]) gibt 0 zurueck bei erfolgreicher Dekomposition.
    """
    vault = _make_vault_with_views(tmp_path, n_views=4)

    exit_code = schwarm_decomposer.main(
        ["--vault-root", str(vault), "--n-slices", "2"]
    )

    assert exit_code == 0


def test_cli_exit_1_on_error(tmp_path):
    """
    CLI main([...]) gibt 1 zurueck bei Fehler (nicht lesbarer Vault o.ae.).
    """
    # Nicht-existenter Vault sollte exit 1 produzieren
    fake_vault = str(tmp_path / "not_here")

    exit_code = schwarm_decomposer.main(
        ["--vault-root", fake_vault, "--n-slices", "2"]
    )

    # Exit 1 bei Fehler
    assert exit_code == 1


def test_cli_exit_2_for_usage_error():
    """
    CLI main([...]) gibt 2 zurueck bei Usage-Fehler (fehlende/ungueltige Args).
    """
    try:
        exit_code = schwarm_decomposer.main(["--n-slices", "abc"])
        assert exit_code == 2
    except SystemExit as e:
        assert e.code == 2


def test_cli_stdout_json_on_success(tmp_path, capsys):
    """
    CLI gibt JSON mit 'slices'-Key auf stdout bei erfolgreicher Dekomposition.
    """
    vault = _make_vault_with_views(tmp_path, n_views=4)

    schwarm_decomposer.main(
        ["--vault-root", str(vault), "--n-slices", "2"]
    )

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "slices" in output
    assert isinstance(output["slices"], list)
    assert len(output["slices"]) == 2
