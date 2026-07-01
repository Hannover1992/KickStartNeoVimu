"""Tests fuer kazman_screening_metrics.py (BL-381 batch_2 — AK-1, read-only). Lead-verify aus Repo-Root.

AK-1: ein NEUES read-only Modul berechnet SCREENING-grade Decoupling Level (DL) +
      Propagation Cost (PC), beide 0-100 (W-CON-1), aus einer VORHANDENEN Abhaengigkeits-/
      Adjazenz-Struktur (dependencyAnalyzer-DAG ODER cochange_pairs als DSM-Proxy). KEINE
      neue file-level Design-Structure-Matrix, KEIN Import-/AST-Parser (Spec Sec 0 = DSM-Fork).

Semantik (Behavior-Review-Anker):
  - PC = transitive Erreichbarkeit / Systemgroesse (MacCormack/Kazman): Anteil des Systems,
    den eine Aenderung im Mittel erreichen kann. Stern-Hub hat hohe PC; disjunkte Komponenten
    niedrige; Kette dazwischen. Monoton in Kanten.
  - DL = Grad der Entkopplung: viele/tiefe Abhaengigkeiten => niedrig; wenige/flache => hoch.
    DL ist grob das Gegenstueck zu PC (entkoppelt <-> billig propagierend).
"""
import re

import kazman_screening_metrics as ksm


# --- Bausteine: Adjazenz-Eingabe ------------------------------------------------------

# Voll entkoppelt: 3 isolierte Knoten, keine Kante.
_DECOUPLED = {"a": [], "b": [], "c": []}

# Voll vermascht (gerichteter Vollgraph ohne Selbst-Schleife): jeder -> jeder andere.
_MESHED = {"a": ["b", "c"], "b": ["a", "c"], "c": ["a", "b"]}

# Stern: ein Hub zeigt auf alle Blaetter (Hub erreicht alles -> hohe PC).
_STAR = {"hub": ["l1", "l2", "l3", "l4"], "l1": [], "l2": [], "l3": [], "l4": []}

# Kette: a -> b -> c -> d (transitive Erreichbarkeit, aber dünn).
_CHAIN = {"a": ["b"], "b": ["c"], "c": ["d"], "d": []}

# Zwei disjunkte Paare: Erreichbarkeit bleibt lokal (kleine PC).
_DISJOINT = {"a": ["b"], "b": [], "c": ["d"], "d": []}


# --- AK-1: Propagation Cost -----------------------------------------------------------


def test_pc_in_0_100_range():
    """PC ist auf [0,100] normalisiert (K-Skala-Constraint W-CON-1)."""
    for adj in (_DECOUPLED, _MESHED, _STAR, _CHAIN, _DISJOINT):
        pc = ksm.propagation_cost(adj)
        assert 0.0 <= pc <= 100.0, "PC ausserhalb [0,100]: %r fuer %r" % (pc, adj)


def test_pc_decoupled_is_zero():
    """Keine Kanten -> keine Aenderung propagiert ueber den Knoten selbst hinaus -> PC ~ 0."""
    assert ksm.propagation_cost(_DECOUPLED) == 0.0


def test_pc_meshed_is_max():
    """Voll vermascht -> jede Aenderung erreicht das ganze System -> PC = 100."""
    assert ksm.propagation_cost(_MESHED) == 100.0


def test_pc_star_high_but_not_full():
    """Behavior-Review (Stern): der Hub erreicht alle 4 Blaetter, aber die Blaetter erreichen
    nichts. PC ist deutlich > 0, aber < 100 (nicht voll vermascht)."""
    pc = ksm.propagation_cost(_STAR)
    assert 0.0 < pc < 100.0
    # 5 Knoten: erreichbare Paare = nur Hub->{4 Blaetter} = 4 von 5*4=20 gerichteten Paaren = 20%.
    assert pc == 20.0


def test_pc_chain_counts_transitive_reach():
    """Behavior-Review (Kette a->b->c->d): transitive Erreichbarkeit zaehlt, nicht nur
    direkte Kanten. a erreicht b,c,d (3); b erreicht c,d (2); c erreicht d (1); d nichts (0).
    Summe 6 von 4*3=12 gerichteten Paaren = 50%."""
    assert ksm.propagation_cost(_CHAIN) == 50.0


def test_pc_disjoint_is_small():
    """Disjunkte Komponenten halten Propagation lokal: 2 erreichbare Paare (a->b, c->d) von
    4*3=12 = ~16.7%. Kleiner als Kette/Stern."""
    pc = ksm.propagation_cost(_DISJOINT)
    assert pc < ksm.propagation_cost(_CHAIN)
    assert round(pc, 1) == 16.7


def test_pc_monotonic_in_edges():
    """Monotonie: mehr Kanten => hoehere (oder gleiche) PC. Wir fuegen schrittweise Kanten
    zu denselben Knoten hinzu."""
    n0 = {"a": [], "b": [], "c": []}
    n1 = {"a": ["b"], "b": [], "c": []}
    n2 = {"a": ["b"], "b": ["c"], "c": []}
    n3 = {"a": ["b", "c"], "b": ["c"], "c": []}
    pcs = [ksm.propagation_cost(g) for g in (n0, n1, n2, n3)]
    assert pcs == sorted(pcs), "PC nicht monoton steigend in Kanten: %r" % pcs
    assert pcs[0] == 0.0


# --- AK-1: Decoupling Level -----------------------------------------------------------


def test_dl_in_0_100_range():
    """DL ist auf [0,100] normalisiert (K-Skala-Constraint W-CON-1)."""
    for adj in (_DECOUPLED, _MESHED, _STAR, _CHAIN, _DISJOINT):
        dl = ksm.decoupling_level(adj)
        assert 0.0 <= dl <= 100.0, "DL ausserhalb [0,100]: %r fuer %r" % (dl, adj)


def test_dl_decoupled_is_max():
    """Voll entkoppelt (keine Kanten) -> maximale Entkopplung -> DL = 100."""
    assert ksm.decoupling_level(_DECOUPLED) == 100.0


def test_dl_meshed_is_min():
    """Voll vermascht -> minimale Entkopplung -> DL = 0."""
    assert ksm.decoupling_level(_MESHED) == 0.0


def test_dl_decreases_with_more_coupling():
    """Behavior-Review: mehr Kopplung (mehr/tiefere Erreichbarkeit) => niedrigeres DL.
    Entkoppelt > disjunkt > Kette > vermascht."""
    dl_dec = ksm.decoupling_level(_DECOUPLED)
    dl_dis = ksm.decoupling_level(_DISJOINT)
    dl_chain = ksm.decoupling_level(_CHAIN)
    dl_mesh = ksm.decoupling_level(_MESHED)
    assert dl_dec > dl_dis > dl_chain > dl_mesh


def test_dl_is_inverse_complement_of_pc():
    """DL und PC sind grobe Gegenstuecke: ein hoch-propagierendes System ist niedrig
    entkoppelt. Auf denselben Graphen gilt DL ~ 100 - PC (screening-grade Komplement)."""
    for adj in (_DECOUPLED, _MESHED, _STAR, _CHAIN, _DISJOINT):
        dl = ksm.decoupling_level(adj)
        pc = ksm.propagation_cost(adj)
        assert abs(dl - (100.0 - pc)) < 1e-9, "DL nicht Komplement von PC bei %r" % adj


# --- Martin Ca/Ce/Instabilitaet (screening-grade Kopplungs-Vorzeichen) ---------------


def test_instability_per_node_in_0_1():
    """Martin-Instabilitaet I = Ce/(Ca+Ce) je Knoten, im Bereich [0,1]."""
    inst = ksm.instability(_CHAIN)
    assert set(inst.keys()) == {"a", "b", "c", "d"}
    for v in inst.values():
        assert 0.0 <= v <= 1.0


def test_instability_pure_source_is_one():
    """Reiner Source (nur efferent, kein afferent: zeigt auf andere, niemand zeigt drauf)
    ist maximal instabil I=1. In der Kette ist 'a' so ein reiner Source."""
    inst = ksm.instability(_CHAIN)
    assert inst["a"] == 1.0


def test_instability_pure_sink_is_zero():
    """Reiner Sink (nur afferent: alle zeigen drauf, er zeigt auf niemand) ist maximal
    stabil I=0. In der Kette ist 'd' so ein reiner Sink."""
    inst = ksm.instability(_CHAIN)
    assert inst["d"] == 0.0


def test_instability_isolated_node_defined():
    """Ein isolierter Knoten (Ca=Ce=0) hat eine definierte Instabilitaet (keine
    Division durch 0)."""
    inst = ksm.instability(_DECOUPLED)
    for v in inst.values():
        assert 0.0 <= v <= 1.0


# --- DSM-Proxy aus Co-Change-Paaren (cochange_coupling-Seam) -------------------------


def test_adjacency_from_pairs_builds_undirected_neighbors():
    """Behavior-Review (Seam): cochange_pairs (DSM-Proxy) -> Adjazenz. Ein Paar (a,b)
    erzeugt eine UNGERICHTETE Nachbarschaft (a~b und b~a), weil Co-Change symmetrisch ist."""
    from collections import Counter
    pairs = Counter({("a", "b"): 3, ("b", "c"): 1})
    adj = ksm.adjacency_from_pairs(pairs)
    assert set(adj["a"]) == {"b"}
    assert set(adj["b"]) == {"a", "c"}
    assert set(adj["c"]) == {"b"}


def test_adjacency_from_pairs_feeds_pc():
    """Die aus Co-Change abgeleitete Adjazenz speist PC: 3 verbundene Knoten (a-b-c)
    ergeben transitive Voll-Erreichbarkeit (ungerichtet symmetrisch) -> PC = 100."""
    from collections import Counter
    pairs = Counter({("a", "b"): 1, ("b", "c"): 1})
    adj = ksm.adjacency_from_pairs(pairs)
    assert ksm.propagation_cost(adj) == 100.0


# --- Bundle + Normalisierungs-Grenzen ------------------------------------------------


def test_screening_metrics_bundles_both_named_0_100():
    """screening_metrics() liefert beide Achsen als getrennte benannte 0-100-Felder."""
    m = ksm.screening_metrics(_STAR)
    assert set(m.keys()) >= {"decoupling_level", "propagation_cost"}
    assert 0.0 <= m["decoupling_level"] <= 100.0
    assert 0.0 <= m["propagation_cost"] <= 100.0


def test_empty_graph_is_safe():
    """Leerer/trivialer Graph: kein Crash, definierte Grenzwerte (PC=0, DL=100)."""
    assert ksm.propagation_cost({}) == 0.0
    assert ksm.decoupling_level({}) == 100.0
    assert ksm.instability({}) == {}
    m = ksm.screening_metrics({})
    assert m["propagation_cost"] == 0.0
    assert m["decoupling_level"] == 100.0


def test_single_node_graph_is_safe():
    """Ein einzelner Knoten ohne Kante: PC=0 (nichts zu propagieren), DL=100 (maximal
    entkoppelt)."""
    assert ksm.propagation_cost({"solo": []}) == 0.0
    assert ksm.decoupling_level({"solo": []}) == 100.0


def test_dangling_target_is_treated_as_node():
    """Robustheit: ein Kanten-Ziel, das selbst kein eigener Schluessel ist, wird als Knoten
    behandelt (haeufig bei DAG-edges[], die Blaetter nicht separat listen)."""
    adj = {"a": ["b"]}  # 'b' fehlt als Key
    pc = ksm.propagation_cost(adj)
    # 2 Knoten {a,b}, 1 erreichbares Paar (a->b) von 2*1=2 = 50%.
    assert pc == 50.0


# --- AK-1: Screening-Grade-Garantie (KEIN Import-/AST-Parser, KEINE file-level DSM) ---


def test_module_is_read_only_and_screening_grade():
    """Screening-Grade-Garantie (Spec Sec 0, DSM-Fork): das Modul baut KEINE echte
    file-level Design-Structure-Matrix und fuehrt KEINE statische Import-/AST-Analyse durch.
    Ausserdem read-only: kein subprocess, kein File-Write. Wir pruefen die EXECUTABLE Quelle
    (ohne Modul-Docstring, der diese Begriffe nur beschreibend nennt)."""
    import ast
    import inspect
    src = inspect.getsource(ksm)
    tree = ast.parse(src)
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)):
        tree.body = tree.body[1:]
    code = ast.unparse(tree)
    # Read-only-Garantie.
    assert "subprocess" not in code
    assert ".write_text(" not in code
    assert ".write(" not in code
    assert not re.search(r"(?<![A-Za-z0-9_])open\s*\(", code)
    # Screening-Grade: KEIN Import-/AST-Parser (keine statische Import-Analyse).
    assert "import ast" not in code
    assert "importlib" not in code
    assert "ast.parse" not in code
