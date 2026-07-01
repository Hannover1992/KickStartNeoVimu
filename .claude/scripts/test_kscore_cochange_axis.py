"""Tests fuer kazman_kscore_axes.py (BL-381 batch_1 — AK-2 + AK-4). Lead-verify aus Repo-Root.

AK-2: co_commit_coupling als EIGENE, benannte Fragilitaets-Achse (0-100 normalisiert),
      semantisch ein Co-Change-GRAD (file_degree = Summe der Paar-Counts), NICHT ein
      blosser Commit-Count und NICHT der schwache aenderungs_risiko-Proxy.
AK-4: K-Score-begleitender eval_finding-Record traegt risk_class + cost/benefit durch
      REUSE von RISK_CLASS_ENUM + check_eval_finding_block (KEIN neues Enum).
"""
import re

import cochange_coupling as cc
import kazman_kscore_axes as kk
import quality_model_wform as qmw


# --- AK-2: co_commit_coupling-Achse ---------------------------------------------------

_LOG = """===h1
a.py
b.py
===h2
a.py
b.py
c.py
===h3
a.py
c.py
"""


def _degree_from_log(text):
    return cc.file_degree(cc.cochange_pairs(cc.parse_git_log(text)))


def test_co_commit_axis_returns_per_file_0_100():
    """Pro Datei ein co_commit_coupling-Wert im Bereich [0,100]."""
    deg = _degree_from_log(_LOG)
    axis = kk.co_commit_axis(deg)
    assert set(axis.keys()) == {"a.py", "b.py", "c.py"}
    for v in axis.values():
        assert 0.0 <= v <= 100.0


def test_co_commit_axis_top_file_is_100():
    """Die Datei mit hoechstem Co-Change-Grad normalisiert auf 100 (Max-Normalisierung,
    konsistent mit der K-Skala 0-100, W-CON-1). a.py hat Grad 4 (hoechster)."""
    deg = _degree_from_log(_LOG)  # a=4, b=3, c=3
    axis = kk.co_commit_axis(deg)
    assert axis["a.py"] == 100.0
    # b/c (Grad 3) liegen proportional darunter (3/4*100 = 75.0).
    assert axis["b.py"] == 75.0
    assert axis["c.py"] == 75.0


def test_co_commit_axis_is_degree_not_commit_count():
    """SEMANTIK-Guard (Behavior-Review): die Achse ist ein Co-Change-GRAD (Paar-Kopplung),
    NICHT die Datei-Change-Frequenz (aenderungs_risiko). Eine Datei, die OFT allein
    committet wird (hohe Change-Frequenz) aber NIE mit anderen zusammen, hat Co-Change-Grad
    0 -> Achse 0. Genau hier unterscheidet sich co_commit_coupling von aenderungs_risiko."""
    # solo.py: 5 Einzel-Commits (hohe Change-Frequenz), nie gepaart.
    commits = [["solo.py"]] * 5 + [["x.py", "y.py"]]
    deg = cc.file_degree(cc.cochange_pairs(commits))
    axis = kk.co_commit_axis(deg)
    assert "solo.py" not in axis  # kein Paar -> kein Co-Change-Grad
    # x/y sind gepaart -> tragen die Achse.
    assert axis["x.py"] == 100.0


def test_co_commit_axis_empty_is_empty():
    """Kein Co-Change-Signal (leerer Grad) -> leere Achse, kein Crash, keine Division durch 0."""
    assert kk.co_commit_axis(cc.Counter()) == {}


def test_co_commit_axis_single_file_is_100():
    """Ein einziger gekoppelter Knoten normalisiert auf 100 (er IST das Maximum)."""
    from collections import Counter
    axis = kk.co_commit_axis(Counter({"only.py": 7}))
    assert axis == {"only.py": 100.0}


def test_co_commit_axis_monotonic_in_degree():
    """Hoeherer Co-Change-Grad => hoehere (oder gleiche) Achse (Monotonie)."""
    from collections import Counter
    axis = kk.co_commit_axis(Counter({"low.py": 1, "mid.py": 5, "high.py": 10}))
    assert axis["low.py"] < axis["mid.py"] < axis["high.py"]
    assert axis["high.py"] == 100.0


def test_co_commit_axis_distinct_field_name():
    """Die Achse traegt den benannten Schluessel `co_commit_coupling`, getrennt von
    `aenderungs_risiko` (W-AK2-2: keine Summen-Verschmelzung)."""
    assert kk.CO_COMMIT_AXIS_NAME == "co_commit_coupling"
    assert kk.CO_COMMIT_AXIS_NAME != "aenderungs_risiko"


def test_axis_record_carries_both_named_axes_separately():
    """fragility_axes() liefert beide Achsen als GETRENNTE benannte Felder — Beweis, dass
    co_commit_coupling NICHT in aenderungs_risiko addiert wird (W-AK2-2-Adjudikation)."""
    deg = _degree_from_log(_LOG)
    rec = kk.fragility_axes(file_degree=deg, aenderungs_risiko={"a.py": 0.6})
    assert "co_commit_coupling" in rec
    assert "aenderungs_risiko" in rec
    assert rec["co_commit_coupling"]["a.py"] == 100.0
    assert rec["aenderungs_risiko"]["a.py"] == 0.6


# --- AK-4: risk_class + cost/benefit via Library-Reuse --------------------------------


def test_risk_finding_reuses_enum_no_new_enum():
    """KEIN neues Enum: die Achse referenziert qmw.RISK_CLASS_ENUM direkt (Reuse-Nachweis)."""
    assert kk.RISK_CLASS_ENUM is qmw.RISK_CLASS_ENUM
    assert kk.RISK_CLASS_ENUM == {"Omission", "Commission", "Realization", "Managerial"}


def test_risk_finding_valid_passes_library_validator():
    """Ein wohlgeformter K-Score-eval_finding-Record besteht check_eval_finding_block
    (exit-aequivalent: leere missing-Liste). risk_class IN Enum, cost/benefit nicht-leer."""
    rec = kk.kscore_risk_finding(
        bl_slug="BL-381", idx=1, ref_node="AK-2",
        risk_class="Realization", severity="mittel",
        befund="K-Score hoch durch co_commit_coupling=100 an AK-2",
        cost="Achse als Konflikt-Praediktor in Sequenz beachten (mittel)",
        benefit="frueh-Warnung verborgener Kopplung vor Parallel-Bearbeitung",
        suggested_action="AK-2 isoliert sequenzieren",
    )
    block = kk.render_eval_finding_block(rec)
    missing = qmw.check_eval_finding_block(block)
    assert missing == [], "Library-Validator-Verletzungen: %r" % missing


def test_risk_finding_record_is_design_eval_kind():
    """Der K-Score-Befund dockt als eval_kind=design_eval an (W-AK4-3-Adjudikation)."""
    rec = kk.kscore_risk_finding(
        bl_slug="BL-381", idx=2, ref_node="AK-1",
        risk_class="Commission", severity="hoch", befund="x",
        cost="c", benefit="b", suggested_action="a",
    )
    assert rec["eval_kind"] == "design_eval"
    assert rec["ref_node"] == "AK-1"


def test_risk_finding_rejects_free_string_risk_class():
    """Freier String statt Kazman-Klasse -> ValueError (Enum erzwungen, kein Bypass)."""
    import pytest
    with pytest.raises(ValueError):
        kk.kscore_risk_finding(
            bl_slug="BL-381", idx=3, ref_node="AK-1",
            risk_class="Critical", severity="hoch", befund="x",
            cost="c", benefit="b", suggested_action="a",
        )


def test_risk_finding_rejects_empty_cost_benefit():
    """Leeres cost/benefit -> ValueError (Aktionierbarkeits-Pflicht, EVAL_FINDING_NONEMPTY_FIELDS)."""
    import pytest
    with pytest.raises(ValueError):
        kk.kscore_risk_finding(
            bl_slug="BL-381", idx=4, ref_node="AK-1",
            risk_class="Omission", severity="hoch", befund="x",
            cost="   ", benefit="b", suggested_action="a",
        )


def test_render_block_with_free_string_is_caught_by_library():
    """Doppelte Absicherung: selbst wenn man den Validator direkt mit einer freien
    risk_class fuettert, faengt die Library sie (kein eigenes, abweichendes Enum)."""
    bad = kk.render_eval_finding_block({
        "finding_id": "BL-381.EF-9", "eval_kind": "design_eval", "ref_node": "AK-1",
        "risk_class": "Bogus", "severity": "hoch", "befund": "x",
        "cost": "c", "benefit": "b", "suggested_action": "a", "status": "offen",
        "metric": "k_score", "threshold": "<=66",
    })
    missing = qmw.check_eval_finding_block(bad)
    assert any("risk_class(invalid:Bogus)" in m for m in missing)


def test_module_is_read_only_no_subprocess_no_write():
    """Substrat-Garantie: das Modul mutiert keinen State (kein subprocess-Aufruf, kein
    File-Write, kein Path.write). Reine Ableitungs-Funktionen auf uebergebenen Daten
    (analog cochange_coupling.py read-only). Wir pruefen die EXECUTABLE Quelle (ohne
    Modul-Docstring, der die read-only-Garantie in Prosa beschreibt)."""
    import ast
    import inspect
    src = inspect.getsource(kk)
    tree = ast.parse(src)
    # Modul-Docstring entfernen (er nennt 'subprocess'/'File-Write' nur beschreibend).
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)):
        tree.body = tree.body[1:]
    code = ast.unparse(tree)
    # Keine State-mutierenden Aufrufe / Importe in der ausfuehrbaren Quelle.
    assert "subprocess" not in code
    assert ".write_text(" not in code
    assert ".write(" not in code
    # 'open(' als echter Aufruf (built-in file open) — nicht als Teil eines Bezeichners.
    assert not re.search(r"(?<![A-Za-z0-9_])open\s*\(", code)
    # Keine Achsen-Funktion ruft das Git-/Report-Producer-Modul auf (Datenquelle wird
    # uebergeben, nicht selbst geholt) — die Achse bleibt eine reine Transformation.
    assert "_git_log" not in code
