#!/usr/bin/env python3
"""test_idf_light.py — Dry-Run-Harness fuer IDF-light (2026-06-01).

Prueft die IDF-LIGHT-Logik (aus _IDF_orchestrate.md IDF-LIGHT-GATE) deterministisch:
  1. Modus-Entscheidung: actionable_count -> {ultralight | light | full} (+ --full Override).
  2. Skip-Matrix pro Modus (welche Organisations-Berater fallen weg).
  3. INVARIANTE: die ESSENZIELLEN Berater (inkl. testSearch) laufen IMMER.
  4. Trivial-Output-Schemata (clustering/sequence/dependency) sind downstream-lesbar.
  5. INTEGRATION: geist5 (IDF->SDF-Contract) PASST in jedem Modus (super-light/light/normal).

So benutzen: `py -3 -m pytest .claude/scripts/test_idf_light.py -q`
ODER als Report:  `py -3 .claude/scripts/test_idf_light.py`  (druckt die 3-Modi-Tabelle).

WICHTIG: Dieser Test SPIEGELT die IDF-LIGHT-GATE-Logik aus _IDF_orchestrate.md. Bei Aenderung
der Schwellen dort MUSS idf_light_mode() hier mitgezogen werden (Single-Source-Disziplin).
"""
from __future__ import annotations
import os, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()

# ── Spiegel der IDF-LIGHT-GATE-Entscheidung (_IDF_orchestrate.md nach Phase 3.8e) ──
ESSENTIAL = {"validator", "batchPlan", "stagePlanner", "metricPlanner", "testSearch", "finalSummary"}
ORGANIZATIONAL = {"clustering", "dependencyAnalyzer", "sequencePlanner"}

def idf_light_mode(actionable_count: int, full_override: bool = False) -> str:
    if full_override:
        return "full"
    if actionable_count == 1:
        return "ultralight"
    if actionable_count <= 3:
        return "light"
    return "full"

def skipped_phases(mode: str) -> set:
    if mode == "ultralight":
        return {"clustering", "dependencyAnalyzer", "sequencePlanner"}
    if mode == "light":
        return {"clustering"}
    return set()  # full

def ran_phases(mode: str) -> set:
    return (ESSENTIAL | ORGANIZATIONAL) - skipped_phases(mode)

# ── Trivial-Output-Schemata (was der Orchestrator bei Skip schreibt) ──
def trivial_clustering(items): return {"clusters": [{"id": "C-1", "items": items}], "cluster_aggregates": [{"cluster_id": "C-1", "items_count": len(items), "k_score_mean": None}], "mitose_signal": False, "last_berater": "clustering(idf-light-skip)"}
def trivial_sequence(items):   return {"ordered_items": items, "topology_pass": True, "total_items": len(items), "last_berater": "sequencePlanner(idf-light-skip)"}
def trivial_dependency(items): return {"nodes": items, "edges": [], "cycles": [], "mermaid_text": "graph TD", "file_refs_total": 0, "last_berater": "dependencyAnalyzer(idf-light-skip)"}

# ── geist5-Integration: simuliertes Manifest pro Modus ──
def sim_manifest(mode: str, batch_key="batch_oz") -> str:
    """Manifest mit den 4 Contract-Feldern die IDF-light's essenzielle Berater liefern."""
    return (
        "## IDF_PIPELINE_STATE\n"
        "idf_status: IDF_DONE\n"
        f"idf_light_mode: {mode}\n\n"
        "## DF_BATCH_STATE\n"
        "batch_items_per_batch:\n"
        f"  {batch_key}: [PL-FE-OZ-TRISTATE-REVERT]\n"
        "batch_mode_hints:\n"
        f"  {batch_key}: {{hint: M3, coverage_verdict: partial}}\n"
        "batch_stages:\n"
        f"  {batch_key}: [1]\n"
    )

def _geist5():
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    import guard_geist5_idf_to_sdf as g5
    return g5

# ════════════════════════════ TESTS ════════════════════════════

def test_mode_decision():
    assert idf_light_mode(0) == "ultralight" or idf_light_mode(0) == "light"  # 0 ist Edge (kein Batch) — egal, kein <=0-Pfad
    assert idf_light_mode(1) == "ultralight"
    assert idf_light_mode(2) == "light"
    assert idf_light_mode(3) == "light"
    assert idf_light_mode(4) == "full"
    assert idf_light_mode(8) == "full"

def test_full_override():
    assert idf_light_mode(1, full_override=True) == "full"
    assert idf_light_mode(3, full_override=True) == "full"

def test_essential_never_skipped():
    for mode in ("ultralight", "light", "full"):
        assert ESSENTIAL & skipped_phases(mode) == set(), f"{mode} skippt einen essenziellen Berater!"

def test_testsearch_always_runs():
    # Die Nicht-Verhandelbare: testSearch (Coverage->Modus) laeuft in JEDEM Modus.
    for mode in ("ultralight", "light", "full"):
        assert "testSearch" in ran_phases(mode)

def test_skip_matrix():
    assert skipped_phases("ultralight") == {"clustering", "dependencyAnalyzer", "sequencePlanner"}
    assert skipped_phases("light") == {"clustering"}
    assert skipped_phases("full") == set()

def test_trivial_output_schemas():
    items = ["PL-A"]
    # Downstream batchPlan liest .clusters / .ordered_items / .nodes — Keys muessen da sein.
    assert "clusters" in trivial_clustering(items) and trivial_clustering(items)["clusters"][0]["items"] == items
    assert trivial_sequence(items)["ordered_items"] == items and trivial_sequence(items)["topology_pass"] is True
    assert trivial_dependency(items)["nodes"] == items and trivial_dependency(items)["cycles"] == []

def test_geist5_passes_every_mode():
    """INTEGRATION: geist5 IDF->SDF-Contract PASST in super-light/light/normal."""
    g5 = _geist5()
    for mode in ("ultralight", "light", "full"):
        content = sim_manifest(mode)
        violations = g5.run_contract_checks(content)
        assert violations == [], f"geist5 blockt IDF-light Modus '{mode}': {violations}"

def test_geist5_still_blocks_broken_handoff():
    """Gegenprobe: ohne die Contract-Felder blockt geist5 weiter (Schutz intakt)."""
    g5 = _geist5()
    broken = "## IDF_PIPELINE_STATE\nidf_status: AK_PER_PL\n## DF_BATCH_STATE\n(leer)\n"
    violations = g5.run_contract_checks(broken)
    assert len(violations) >= 1, "geist5 sollte gebrochenen Handoff weiter blocken"


# ════════════════════════════ REPORT-MAIN ════════════════════════════
if __name__ == "__main__":
    g5 = _geist5()
    print("=== IDF-light Dry-Run-Check (super-light / light / normal) ===\n")
    print("%-12s %-9s %-44s %-18s %s" % ("Items", "Modus", "geskippt (Organisation)", "testSearch", "geist5"))
    print("-" * 100)
    for n in (1, 2, 3, 5, 8):
        mode = idf_light_mode(n)
        skip = ", ".join(sorted(skipped_phases(mode))) or "(nichts)"
        ts = "laeuft" if "testSearch" in ran_phases(mode) else "FEHLT!"
        viol = g5.run_contract_checks(sim_manifest(mode))
        g5ok = "PASS" if viol == [] else ("BLOCK: " + "; ".join(viol))
        print("%-12s %-9s %-44s %-18s %s" % (n, mode, skip[:44], ts, g5ok))
    print("\n--full Override: actionable=1 -> %s (Voll-IDF erzwungen)" % idf_light_mode(1, full_override=True))
    print("\nEssentiell (laeuft IMMER): " + ", ".join(sorted(ESSENTIAL)))
