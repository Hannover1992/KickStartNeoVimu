#!/usr/bin/env python3
"""
test_workflow_zones.py — BL-330: Tests fuer die maschinenlesbare Determinismus-Karte
(workflow_zones.py): Zonen-Registry (activity -> {green,yellow,red}) + Vehikel-Resolver.

RED-Beweis: workflow_zones.py existiert noch nicht -> ImportError/Fehl bis GREEN.

Kern-Invariante (load-bearing Sicherheit): resolve_vehicle gibt fuer eine ROTE Zone
NIE "workflow" zurueck — in KEINEM Modus. Kognitiv bleibt strukturell altmodisch.
"""
from __future__ import annotations

import pytest

from workflow_zones import (
    ZONE_REGISTRY,
    VALID_ZONES,
    VALID_VEHICLES,
    zone_of,
    resolve_vehicle,
    vehicle_for,
)


# ---------------------------------------------------------------------------
# resolve_vehicle(zone, mode) — die 3-Modi-Matrix
# ---------------------------------------------------------------------------

def test_resolve_vehicle_false_all_worker() -> None:
    """workflow=false => ALLES altmodisch (worker), egal welche Zone."""
    for zone in ("green", "yellow", "red"):
        assert resolve_vehicle(zone, "false") == "worker"


def test_resolve_vehicle_normal() -> None:
    """workflow=normal => gruen als Workflow; gelb + rot bleiben Worker."""
    assert resolve_vehicle("green", "normal") == "workflow"
    assert resolve_vehicle("yellow", "normal") == "worker"
    assert resolve_vehicle("red", "normal") == "worker"


def test_resolve_vehicle_fast() -> None:
    """workflow=fast => gruen als Workflow, gelb als advisory (Workflow rechnet,
    Lead/Berater bestaetigt); rot bleibt Worker."""
    assert resolve_vehicle("green", "fast") == "workflow"
    assert resolve_vehicle("yellow", "fast") == "advisory"
    assert resolve_vehicle("red", "fast") == "worker"


def test_red_never_workflow_invariant() -> None:
    """KERN-SICHERHEIT (BL-330): eine ROTE Aktivitaet wird in KEINEM Modus zu
    'workflow' aufgeloest. Kognitiv ist strukturell nicht workflow-faehig."""
    for mode in ("false", "normal", "fast", "garbage", ""):
        v = resolve_vehicle("red", mode)
        assert v != "workflow", f"red darf nie workflow werden (mode={mode!r} -> {v!r})"
        assert v == "worker"


def test_resolve_vehicle_unknown_mode_failsafe() -> None:
    """Unbekannter/leerer Modus => fail-safe worker (nie versehentlich Workflow)."""
    assert resolve_vehicle("green", "voll-automatik") == "worker"
    assert resolve_vehicle("green", None) == "worker"


# ---------------------------------------------------------------------------
# zone_of(activity) — Registry-Lookup
# ---------------------------------------------------------------------------

def test_zone_of_known_activities() -> None:
    """Stichproben gegen die Karte: Berater/Steps in der richtigen Zone."""
    # gruen (hart-deterministisch)
    assert zone_of("_A_berater_plAggregation") == "green"
    assert zone_of("_IDF_berater_clustering") == "green"
    assert zone_of("_SDF_berater_statusTransition") == "green"
    assert zone_of("_TDD_setup") == "green"
    # gelb (advisory)
    assert zone_of("_IDF_berater_metricPlanner") == "yellow"
    assert zone_of("_IDF_berater_testSearch") == "yellow"
    assert zone_of("_I_blueprintQG") == "yellow"
    # rot (kognitiv)
    assert zone_of("_SDF_berater_modusEntscheidung") == "red"
    assert zone_of("_A_berater_specParse") == "red"
    assert zone_of("_TDD_red") == "red"
    assert zone_of("_TDD_check") == "red"
    assert zone_of("_I_goldDefine") == "red"


def test_zone_of_guard_prefix_is_green() -> None:
    """Alle guards/Hooks sind hart-deterministisch (Karte §3.4) — Praefix-Regel."""
    assert zone_of("guard_a_idf_handoff") == "green"
    assert zone_of("guard_irgendein_neuer_guard") == "green"  # Praefix-Regel, auch unbekannte


def test_zone_of_unknown_is_red_failsafe() -> None:
    """Unbekannte Aktivitaet => konservativ ROT (fail-safe: nie versehentlich als
    Workflow geroutet — 'gebaut ist nicht load-bearing', unklassifiziert = altmodisch)."""
    assert zone_of("voellig_unbekannte_aktivitaet_xyz") == "red"
    assert zone_of("") == "red"
    assert zone_of(None) == "red"


def test_zone_of_case_insensitive() -> None:
    """Lookup ist case-insensitiv + whitespace-tolerant."""
    assert zone_of("  _TDD_RED  ") == "red"
    assert zone_of("_idf_berater_clustering") == "green"


# ---------------------------------------------------------------------------
# Registry-Integritaet
# ---------------------------------------------------------------------------

def test_registry_zones_all_valid() -> None:
    """Jede Registry-Zone ist in {green,yellow,red}."""
    for activity, zone in ZONE_REGISTRY.items():
        assert zone in VALID_ZONES, f"{activity}: ungueltige Zone {zone!r}"


def test_registry_spans_all_three_zones() -> None:
    """Die Registry deckt alle 3 Zonen ab (keine leere Klasse)."""
    zones = set(ZONE_REGISTRY.values())
    assert {"green", "yellow", "red"} <= zones


def test_registry_has_substantive_coverage() -> None:
    """Die Karte hat 104 Komponenten — die Registry deckt die dispatchbaren
    Kern-Aktivitaeten ab (Sanity-Mindestgroesse, kein leeres Scaffold)."""
    assert len(ZONE_REGISTRY) >= 40


# ---------------------------------------------------------------------------
# vehicle_for(activity, mode) — End-to-End-Bequemlichkeit
# ---------------------------------------------------------------------------

def test_vehicle_for_end_to_end() -> None:
    """vehicle_for kombiniert zone_of + resolve_vehicle."""
    # gruener Berater im normal-Modus -> Workflow
    assert vehicle_for("_IDF_berater_clustering", "normal") == "workflow"
    # roter TDD-Step in fast -> trotzdem Worker (rot nie workflow)
    assert vehicle_for("_TDD_red", "fast") == "worker"
    # gelber Berater in fast -> advisory
    assert vehicle_for("_IDF_berater_metricPlanner", "fast") == "advisory"
    # gelber Berater in normal -> Worker
    assert vehicle_for("_IDF_berater_metricPlanner", "normal") == "worker"
    # unbekannt -> rot -> immer Worker
    assert vehicle_for("voellig_unbekannt", "fast") == "worker"


def test_no_red_activity_ever_resolves_workflow_sweep() -> None:
    """SWEEP-Garantie: KEINE rote Aktivitaet der Registry loest in IRGENDEINEM
    Modus zu 'workflow' auf (strukturelle Absicherung ueber die ganze Karte)."""
    red_activities = [a for a, z in ZONE_REGISTRY.items() if z == "red"]
    assert red_activities, "Registry sollte rote Aktivitaeten enthalten"
    for activity in red_activities:
        for mode in ("false", "normal", "fast"):
            assert vehicle_for(activity, mode) != "workflow", (
                f"INVARIANT-VERLETZUNG: {activity} (rot) -> workflow bei mode={mode}"
            )


def test_valid_vehicles_set() -> None:
    """Die Vehikel-Domaene ist genau {workflow, advisory, worker}."""
    assert VALID_VEHICLES == {"workflow", "advisory", "worker"}


# ---------------------------------------------------------------------------
# BL-330 Verify-Fixes (Regression-Locks aus dem adversarischen Verify-Lauf)
# ---------------------------------------------------------------------------

def test_t_orchestrate_is_green() -> None:
    """Verify HIGH-Fix: _T_orchestrate (verify-only Dispatch, Karte §3.3 hart-det) ist
    green und wird ab normal als Workflow geroutet (vorher Fail-Safe-red verschluckt)."""
    assert zone_of("_T_orchestrate") == "green"
    assert vehicle_for("_T_orchestrate", "normal") == "workflow"


def test_recalibrate_patternbrief_downgraded_yellow() -> None:
    """Verify MEDIUM-Fix: recalibrate (Truth-Chain via _SC_modelMaintain/_K_score) +
    patternBrief (brief_summary-Halluzinations-Seam) sind konservativ yellow —
    in normal worker, in fast advisory (nie autonom als Workflow geschrieben)."""
    for act in ("_SDF_berater_recalibrate", "_SDF_berater_patternBrief"):
        assert zone_of(act) == "yellow", f"{act} sollte yellow sein"
        assert vehicle_for(act, "normal") == "worker"
        assert vehicle_for(act, "fast") == "advisory"


def test_nonprefix_hooks_are_green() -> None:
    """Verify MEDIUM-Fix: die 3 nicht-guard_-praefigierten Hooks sind explizit green
    (Karte §3.4 14/14 hart-det)."""
    for hook in ("commit_msg_leak_guard", "worktree_hook_router", "process_audit_stop_hook"):
        assert zone_of(hook) == "green", f"{hook} sollte green sein"


def test_recheck_completion_green_were_failsafe_red() -> None:
    """BL-330 Recheck (User-Challenge 'check weiter / A sieht gruenlicher aus'): die
    peripheren Bookkeeping-/Graph-/Setup-Berater waren NUR Fail-Safe-rot (unregistriert),
    nicht kognitiv. Jetzt explizit GREEN -> @normal Workflow."""
    green_now = [
        "_A_berater_modusErkennung", "_A_berater_discovery", "_A_berater_iddContext",
        "_A_berater_metadatenAggregation", "_A_berater_gitTracking", "_A_berater_stateMaintain",
        "_A_postRoute", "_IDF_berater_resumeGuard", "_IDF_berater_init", "_IDF_berater_validator",
        "_IDF_berater_dependencyAnalyzer", "_IDF_berater_sequencePlanner",
        "_SDF_berater_resumeGuard", "_SDF_berater_analyse", "_SDF_berater_batchPlanner",
        "_SDF_berater_garbageCollection", "_SDF_berater_stateMaintain", "_srs_compute",
    ]
    for a in green_now:
        assert zone_of(a) == "green", f"{a} sollte green sein (war Fail-Safe-rot)"
        assert vehicle_for(a, "normal") == "workflow", f"{a} @normal sollte workflow sein"


def test_recheck_completion_yellow() -> None:
    """BL-330 Recheck: 1-Seam-Berater (Scope-/Relevanz-/Schaetz-Urteil) = yellow."""
    for a in ["_W_fetch", "_git_analyse", "_K_score", "_IDF_berater_stagePlanner",
              "_IDF_berater_finalSummary", "_SDF_berater_stageElevation",
              "_SDF_berater_architecturalBrief", "_IDF_berater_akExtraktion"]:
        assert zone_of(a) == "yellow", f"{a} sollte yellow sein"
        assert vehicle_for(a, "normal") == "worker"
        assert vehicle_for(a, "fast") == "advisory"


def test_recheck_completion_red_explicit_and_invariant() -> None:
    """BL-330 Recheck: die echten Urteils-/Wahrheits-/Intent-Seams bleiben rot — jetzt
    EXPLIZIT dokumentiert (statt zufaellig fail-safe). rot-never-Invariante haelt."""
    red_now = [
        "_IDF_berater_modelSync", "_IDF_berater_plBewertung", "_IDF_berater_specParse",
        "dispatch_findings", "_model", "_spec", "_taskDefinition",
        "_A_berater_findingsReview", "_A_berater_domainBrief",
    ]
    for a in red_now:
        assert zone_of(a) == "red", f"{a} sollte (explizit) red sein"
        for mode in ("false", "normal", "fast"):
            assert vehicle_for(a, mode) == "worker", f"{a} darf nie workflow werden"


def test_recheck_a_tail_is_a_real_chain() -> None:
    """BL-330 Recheck-Kern: das A-Pipeline-ENDE plAggregation->metadatenAggregation->
    gitTracking->stateMaintain ist eine echte konsekutive GRUENE Kette (len-4) — die
    erste Ketten-Karte hatte sie durch Fail-Safe-rot kuenstlich zerhackt (User-Riecher)."""
    a_tail = ["_A_berater_plAggregation", "_A_berater_metadatenAggregation",
              "_A_berater_gitTracking", "_A_berater_stateMaintain"]
    for a in a_tail:
        assert vehicle_for(a, "normal") == "workflow", f"A-Tail-Glied {a} sollte @normal workflow sein"


def test_resolve_vehicle_zone_arg_normalized_failsafe() -> None:
    """Verify LOW-Hardening: ein nicht-kanonischer zone-Arg ('RED'/'Red'/' red ') leakt
    NIE zu workflow — entweder als rot erkannt (worker) oder Fail-Safe worker."""
    for bad_red in ("RED", "Red", " red ", "red\t"):
        assert resolve_vehicle(bad_red, "fast") == "worker"
        assert resolve_vehicle(bad_red, "normal") == "worker"
    # mis-cased green wird korrekt normalisiert (kein Regress der gruenen Funktion)
    assert resolve_vehicle("GREEN", "normal") == "workflow"


# ---------------------------------------------------------------------------
# BL-373 (2026-06-16): Implement-Motor-Workflow als gruene, aber Gate-D-gelockte Aktivitaet
# ---------------------------------------------------------------------------

def test_dispatch_implement_motor_green_but_gate_d_locked() -> None:
    """BL-373: der Implement-Motor (dispatch_implement) ist strukturell deterministisch = GREEN
    (1 Step=1 agent, BL-222) und wird ab normal/fast als 'workflow' geroutet. Der TEMPORALE
    Gate-D-Lock (motor_production_ready) liegt NICHT in der Zonen-Karte, sondern am SDF-Aufruf
    (motor_allowed = gate_d_passed AND vehicle==workflow) — die Karte sagt nur 'workflow-faehig'.
    workflow=false (Dial off / Default) → altmodisch (worker)."""
    assert zone_of("dispatch_implement") == "green"
    assert vehicle_for("dispatch_implement", "false") == "worker"
    assert vehicle_for("dispatch_implement", "normal") == "workflow"
    assert vehicle_for("dispatch_implement", "fast") == "workflow"
