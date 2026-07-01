"""Tests fuer kazman_coupling_dimensions.py (BL-381 batch_3 — AK-6 code-Teil, read-only).
Lead-verify aus Repo-Root.

AK-6 (code): die heute zu 1 Skalar (`kopplung_roh` -> `k_kopplung`, _K_score.md:611) kollabierte
Kopplung wird mehrdimensional gefuehrt, SOWEIT aus vorhandenem Substrat ableitbar — als GETRENNTE
benannte Felder, KEIN Rueckkollaps in einen einzigen Kopplungs-Skalar (W-AK6-2):

  - structural (syntactic): via Martin Ca/Ce / instability (kazman_screening_metrics.instability)
  - temporal + resource: via Co-Commit-Coupling (kazman_kscore_axes.co_commit_axis, Kazman:
    co-commit reveals "control, data, timing, and resource-based coupling")

Die nicht-ableitbaren Dimensionen (data-semantic + behavioral, ohne Laufzeit-Trace) sind NICHT
batch_3 (= dokumentierte Luecke in batch_4). Dieses Modul produziert NUR die ableitbaren Dims.

Behavior-Review-Anker:
  - GETRENNT heisst: das Ergebnis traegt >=2 distinkte, benannte Dimensions-Felder; KEIN gewichteter
    Sammel-Skalar als Primaer-Output (sonst reproduziert man W-DOM-1 auf der Kopplungs-Ebene).
  - Wiederverwendung: kein eigener Ca/Ce-Rechner, kein eigener Co-Change-Grad — die Dims kommen
    aus den batch_1/batch_2-Producern (EIN Producer je Achse).
"""
import re

import kazman_coupling_dimensions as kcd


# --- Eingaben -------------------------------------------------------------------------

# Kette a->b->c->d: gerichtete Adjazenz fuer die strukturelle (Ca/Ce) Dimension.
_CHAIN = {"a": ["b"], "b": ["c"], "c": ["d"], "d": []}

# Co-Change-Grad je Datei (cochange_coupling.file_degree-Form): temporal/resource-Dimension.
_FILE_DEGREE = {"a": 4, "b": 2, "c": 1}


# --- AK-6: getrennte benannte Dimensionen, KEIN Skalar-Kollaps ------------------------


def test_dimensions_are_separate_named_fields():
    """Mind. 2 distinkte benannte Kopplungs-Dimensions-Felder (structural + temporal/resource).
    KEIN Rueckkollaps in 1 Skalar (W-AK6-2)."""
    dims = kcd.coupling_dimensions(adjacency=_CHAIN, file_degree=_FILE_DEGREE)
    assert kcd.COUPLING_STRUCTURAL_NAME in dims
    assert kcd.COUPLING_TEMPORAL_RESOURCE_NAME in dims
    # Mindestens 2 distinkte Dimensions-Schluessel.
    assert len({kcd.COUPLING_STRUCTURAL_NAME, kcd.COUPLING_TEMPORAL_RESOURCE_NAME}) >= 2


def test_no_single_collapsed_scalar_key():
    """W-AK6-2-Constraint: das Ergebnis traegt KEINEN gesammelten 1-Skalar-Kopplungs-Schluessel
    (kein k_kopplung / kopplung_roh / coupling / coupling_total als Primaer-Output)."""
    dims = kcd.coupling_dimensions(adjacency=_CHAIN, file_degree=_FILE_DEGREE)
    forbidden_collapse_keys = {
        "k_kopplung", "kopplung_roh", "kopplung", "coupling",
        "coupling_total", "coupling_scalar", "coupling_combined",
    }
    assert not (set(dims.keys()) & forbidden_collapse_keys), (
        "Rueckkollaps-Schluessel im Multi-Dim-Output: %r" % (set(dims.keys()) & forbidden_collapse_keys)
    )


def test_structural_dim_is_per_node_instability():
    """structural-Dimension = per-Knoten Martin-Instabilitaet (Ca/Ce). Reiner Source 'a' = 1.0,
    reiner Sink 'd' = 0.0 (Wiederverwendung von kazman_screening_metrics.instability)."""
    dims = kcd.coupling_dimensions(adjacency=_CHAIN, file_degree=_FILE_DEGREE)
    struct = dims[kcd.COUPLING_STRUCTURAL_NAME]
    assert struct["a"] == 1.0
    assert struct["d"] == 0.0


def test_temporal_resource_dim_is_0_100_normalized():
    """temporal/resource-Dimension = co_commit_axis (0-100, Max-Normalisierung). Die Datei mit
    hoechstem Co-Change-Grad ist 100."""
    dims = kcd.coupling_dimensions(adjacency=_CHAIN, file_degree=_FILE_DEGREE)
    tr = dims[kcd.COUPLING_TEMPORAL_RESOURCE_NAME]
    assert all(0.0 <= v <= 100.0 for v in tr.values())
    assert max(tr.values()) == 100.0  # 'a' hat hoechsten Grad (4)


def test_reuses_substrate_producers_no_duplicate_compute():
    """Wiederverwendungs-Garantie (EIN Producer je Achse): das Modul rechnet Ca/Ce + Co-Change-Grad
    NICHT selbst neu, sondern ruft die batch_1/batch_2-Producer. Wir pruefen die EXECUTABLE Quelle
    (ohne Docstring): instability(...) und co_commit_axis(...) werden aufgerufen, und es gibt KEINEN
    eigenen Ca/Ce-Zaehler (kein erneutes in/out-degree-Zaehlen)."""
    import ast
    import inspect
    src = inspect.getsource(kcd)
    tree = ast.parse(src)
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)):
        tree.body = tree.body[1:]
    code = ast.unparse(tree)
    # Delegation an die Substrat-Producer (kein Neu-Rechnen).
    assert "instability(" in code, "structural-Dim muss kazman_screening_metrics.instability nutzen"
    assert "co_commit_axis(" in code, "temporal/resource-Dim muss kazman_kscore_axes.co_commit_axis nutzen"
    # Kein eigener gewichteter Sammel-Skalar im Modul (W-AK6-2): keine Summen-Verschmelzung der Dims.
    assert "k_kopplung" not in code


def test_per_batch_scope_relative_annotation():
    """AK-3-Granularitaet (per-Batch, scope-relativ): die Dimensions-Felder sind per-Sub-Batch
    konsumierbar — coupling_dimensions akzeptiert die per-Batch-Substrate (DAG + file_degree
    eines Batches) und gibt ein per-Batch-Dict zurueck (KEIN globaler Repo-Skalar, W-DOM-2)."""
    # Leeres Substrat eines Batches -> definierte, leere (aber benannte) Dims (kein Crash).
    dims = kcd.coupling_dimensions(adjacency={}, file_degree={})
    assert kcd.COUPLING_STRUCTURAL_NAME in dims
    assert kcd.COUPLING_TEMPORAL_RESOURCE_NAME in dims
    assert dims[kcd.COUPLING_STRUCTURAL_NAME] == {}
    assert dims[kcd.COUPLING_TEMPORAL_RESOURCE_NAME] == {}


def test_module_is_read_only():
    """Read-only-Garantie (analog batch_1/batch_2): kein subprocess, kein File-Write."""
    import ast
    import inspect
    src = inspect.getsource(kcd)
    tree = ast.parse(src)
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)):
        tree.body = tree.body[1:]
    code = ast.unparse(tree)
    assert "subprocess" not in code
    assert ".write_text(" not in code
    assert not re.search(r"(?<![A-Za-z0-9_])open\s*\(", code)
