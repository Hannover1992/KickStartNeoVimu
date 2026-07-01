#!/usr/bin/env python3
"""
workflow_zones.py — BL-330: Die Determinismus-Karte als MASCHINENLESBARE Config.

Die "selbst-erfuellende Prophezeiung" (User 2026-06-12): die Karte ist nicht nur ein
Dokument, sondern eine ausfuehrbare Registry, die zusammen mit dem `workflow`-Dial
(session_params_resolver.py) entscheidet, ob eine Pipeline-Aktivitaet als WORKFLOW
laeuft oder altmodisch mit einem WORKER.

Quelle: Konzepte/Determinismus-Karte_Zonen-Dial_BL-330_2026-06-12.md (104 Komponenten,
6 Schichten, aus 2 read-only Klassifikations-Workflows).

ZONEN:
  green  (hart-deterministisch) — kein Korrektheits-Seam. Workflow PROFITIERT.
  yellow (hybrid)               — EIN eingebetteter Urteils-Seam. Workflow rechnet,
                                   Lead/Berater bestaetigt (advisory).
  red    (kognitiv)             — traegt GREEN-Klarheits-/Wahrheits-/Intent-Urteil.
                                   MUSS altmodisch (Worker). NIE Workflow.

3-MODI-DIAL (workflow-Param):
  false  -> alles Worker (altmodisch)
  normal -> green=workflow ; yellow,red=worker
  fast   -> green=workflow ; yellow=advisory ; red=worker

KERN-INVARIANTE (load-bearing): resolve_vehicle gibt fuer ROT NIE "workflow" zurueck —
in keinem Modus. Unbekannte Aktivitaet -> ROT (fail-safe: unklassifiziert = altmodisch).

CLI:
  py -3 workflow_zones.py vehicle --activity=_TDD_red --mode=normal
  py -3 workflow_zones.py zone --activity=_IDF_berater_clustering
  py -3 workflow_zones.py dump   (gesamte Registry als JSON)
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from typing import Dict, Optional, Set

VALID_ZONES: Set[str] = {"green", "yellow", "red"}
VALID_VEHICLES: Set[str] = {"workflow", "advisory", "worker"}
VALID_MODES: Set[str] = {"false", "normal", "fast"}

# ---------------------------------------------------------------------------
# DIE REGISTRY — activity -> zone  (transkribiert aus der Determinismus-Karte)
# Keys sind die DISPATCHBAREN Aktivitaeten (Skill-/Berater-/TDD-Step-/Tool-Namen)
# plus dokumentierende motor:/orchestrator:-Eintraege fuer Vollstaendigkeit.
# ---------------------------------------------------------------------------

ZONE_REGISTRY: Dict[str, str] = {
    # ===== BERATER (Karte §3.2) =====
    # gruen — kein Reasoning / reine Regel/Aggregat/Lookup
    "_a_berater_plaggregation": "green",
    "_sdf_berater_loopdecision": "green",
    "_sdf_berater_postitem": "green",
    "_sdf_berater_statustransition": "green",
    "_idf_berater_clustering": "green",
    # BL-330 Verify-Downgrade (medium): Math gruen, ABER Wrapper um truth-/halluzinations-
    # behaftete Sub-Calls -> konservativ advisory (Dispatch-Granularitaet, kein Split moeglich).
    "_sdf_berater_recalibrate": "yellow",   # triggert inline _SC_modelMaintain/_K_score (Truth-Chain -> C3-Input)
    "_sdf_berater_patternbrief": "yellow",  # brief_summary-Synthese = dok. Halluzinations-Klasse (haiku->sonnet Tier-Bump, DCSRE-486)
    # gelb — mechanischer Rahmen + EIN Urteils-Seam (advisory)
    "_a_berater_akextraktion": "yellow",
    "_a_berater_routing": "yellow",
    "_idf_berater_metricplanner": "yellow",
    "_idf_berater_testsearch": "yellow",
    # rot — Urteils-/Wahrheits-/Intent-Seam
    "_sdf_berater_modusentscheidung": "red",
    "_sdf_berater_modelsync": "red",
    "_idf_berater_batchplan": "red",
    "_a_berater_specparse": "red",

    # ===== I-PIPELINE STEPS (Karte §3.6) =====
    "_i_requirementcheck": "yellow",
    "_i_patternlibrary": "yellow",
    "_i_testsearch": "yellow",
    "_i_blueprintqg": "yellow",
    "_i_fanin": "yellow",
    "_i_cleancodearchitect": "red",
    "_i_golddefine": "red",
    "_i_cleancodeslice": "red",
    "_i_verify": "red",

    # ===== TDD-SCHLEIFE (Karte §3.6) =====
    # gruen — Infrastruktur (kein Urteil)
    "_tdd_setup": "green",
    "_tdd_teardown": "green",
    "_tdd_monitor": "green",
    # gelb — Lauf + RED-Diagnose / Konfig-Wizard
    "_tdd_execute": "yellow",
    "_tdd_init": "yellow",
    # rot — der URTEILS-KERN (RED-Design / GREEN-Klarheit / GOLD)
    "_tdd_red": "red",
    "_tdd_green": "red",
    "_tdd_refactorcode": "red",
    "_tdd_refactortests": "red",
    "_tdd_check": "red",

    # ===== ORCHESTRATOREN — dispatchbare Bewerter/Conformance (Karte §3.3) =====
    # (Die Orchestrator-RUEMPFE sind Motor-Territorium; hier nur die als Sub-Schritt
    #  dispatchbaren Bewertungs-Laeufe.)
    "_ac_orchestrate": "yellow",
    "_bl_orchestrate": "yellow",
    "_t_orchestrate": "green",   # BL-330 Verify-Fix (high): verify-only Dispatch (Karte §3.3 hart-det)

    # ===== NICHT-guard_-praefigierte Hooks (Karte §3.4) — explizit, da Praefix-Regel sie nicht faengt =====
    "commit_msg_leak_guard": "green",
    "worktree_hook_router": "green",
    "process_audit_stop_hook": "green",

    # ===== TOOLS (Karte §3.5) — alle hart-deterministisch =====
    "factory_lock": "green",
    "vault_lock": "green",
    "session_params_resolver": "green",
    "resolve_bl_path": "green",
    "current_context": "green",
    "audit_fanin": "green",
    "manifest_reader": "green",
    "write_surface": "green",
    "worktree_aware_params": "green",
    "leak_patterns": "green",
    "project_coordinator": "green",
    "process_audit": "green",
    "bdf_bl_dependency_analyzer": "green",
    "bdf_bl_clustering": "green",
    "build_retrieval_index": "green",
    "pattern_library": "green",
    "quality_auto_fix": "green",

    # ===== MOTOR-INTERNE MECHANIKEN (Karte §3.1) — dokumentierend =====
    "motor:step_skeleton": "green",
    "motor:dispatch_1agent": "green",
    "motor:barrier_dial_read": "green",
    "motor:idempotenz_guards": "green",
    "motor:partial_failure_fanin": "green",
    "motor:phase3_trigger": "green",
    "motor:runstagecommit": "green",
    "motor:loopdecision_return": "green",
    "motor:safeschemaagent": "green",
    "motor:resume_preflight": "yellow",
    "motor:sc_path_dispatch": "yellow",
    "motor:modusentscheidung_call": "red",
    "motor:tdd_loop_kern": "red",
    "motor:stageelevation": "yellow",

    # ===== BL-373 (2026-06-16): der Implement-Motor-WORKFLOW als dispatchbare Aktivitaet =====
    # dispatch_implement = der deterministische Implement-Motor (BL-222): 1 Step = 1 agent →
    # Mega-Worker strukturell unmoeglich → strukturell hart-deterministisch = GREEN.
    # ⚠ GREEN heisst NICHT "vor Gate-D fahrbar": der Motor traegt einen ZUSAETZLICHEN TEMPORALEN
    # Lock (gate_d_passed / session-param motor_production_ready, default false) an seiner EINZIGEN
    # Aufruf-Stelle (_SDF_orchestrate OUTER-LOOP: motor_allowed = gate_d_passed AND vehicle==workflow).
    # Vor Gate-D ist gate_d_passed=false → der Motor laeuft NIE, obwohl die Karte ihn green nennt.
    # Zone = STRUKTUR (deterministisch); Gate = VERTRAUEN (stabilisiert). Beide muessen halten.
    "dispatch_implement": "green",

    # ===== BL-378 (2026-06-16): arc42-Doku-Render — read-only Projektion auf W{n}, NON-BLOCKING =====
    # User-Direktive: "wunderbar parallel ... in einem Workflow ... fuehr das konsequent durch". arc42-Render
    # baut KEINE Wahrheit, faellt KEIN Korrektheits-/Intent-Urteil MIT KONSEQUENZ (non-blocking Doku ueber
    # frozen snapshot) -> GREEN. Der file-isolierte Sektions-Fan-Out laeuft als dispatch_arc42-Workflow
    # (1 Step=1 agent, race-frei). NICHT der pre-Gate-D-verbotene dispatch_implement-Build-Motor (anderer Zweck).
    # INV-VEHIKEL-6b: alle 13 Berater EXPLIZIT registriert, damit der Fail-Safe (rot) die gruene Render-Kette
    # nicht kuenstlich zerhackt + Workflow-Faehigkeit blockiert.
    "dispatch_arc42": "green",
    "_arc42_berater_einfuehrung": "green",
    "_arc42_berater_randbedingungen": "green",
    "_arc42_berater_kontext": "green",
    "_arc42_berater_loesungsstrategie": "green",
    "_arc42_berater_bausteinsicht": "green",
    "_arc42_berater_laufzeitsicht": "green",
    "_arc42_berater_verteilung": "green",
    "_arc42_berater_querschnitt": "green",
    "_arc42_berater_datenmodell": "green",
    "_arc42_berater_entscheidungen": "green",
    "_arc42_berater_qualitaet": "green",
    "_arc42_berater_risiken": "green",
    "_arc42_berater_glossar": "green",

    # ===== ORCHESTRATOR-SPINE vs KERN (Karte §3.3) — dokumentierend =====
    "_a_orchestrate:wissensbau": "red",
    "_i_orchestrate:tdd_kern": "red",
    "_sc_orchestrate:sc_verdict": "red",
    "_sdf_orchestrate_post:stageelevation": "yellow",
    "_stage_orchestrate:commit_msg_norm": "yellow",
    "_backlog:wahrheiten_routing": "yellow",

    # ===== BL-330 RECHECK-COMPLETION (wf ketten-recheck-unregistriert, 2026-06-12) =====
    # User-Challenge 'check weiter / A sieht gruenlicher aus' BESTAETIGT: ~40 deterministische
    # Berater waren NUR Fail-Safe-rot (unregistriert), nicht kognitiv. Der Fail-Safe ist sicher,
    # aber UNTER-routet (zerhackt korrekt-gruene Ketten kuenstlich). Jetzt explizit klassifiziert.
    # Wahre laengste Ketten dadurch: SDF Pre-Plan len-7, SDF Post-Bookkeeping len-7, IDF-Start len-5,
    # A-Ende len-4 (NICHT len-3 wie die erste Karte meldete = Mess-Artefakt).
    # --- GREEN (deterministisch: Aggregation/Bookkeeping/git-ops/State-IO/Graph/Schwellen) ---
    "_a_berater_moduserkennung": "green",
    "_a_berater_discovery": "green",
    "_a_berater_iddcontext": "green",
    "_a_berater_metadatenaggregation": "green",
    "_a_berater_gittracking": "green",
    "_a_berater_statemaintain": "green",
    "_a_postroute": "green",
    "_idf_berater_teamsetup": "green",
    "_idf_berater_loopcheck": "green",
    "_idf_berater_resumeguard": "green",
    "_idf_berater_init": "green",
    "_idf_berater_validator": "green",
    "_idf_berater_dependencyanalyzer": "green",
    "_idf_berater_sequenceplanner": "green",
    "_idf_berater_bottlenecktrigger": "green",
    "_idf_berater_plaggregation": "green",
    "_sdf_berater_resumeguard": "green",
    "_sdf_berater_itemcontext": "green",
    "_sdf_berater_analyse": "green",            # behavior-reviewed: 'Batch-Size-Eval' = feste Schwelle LOC>200/>2-HIGH, kein Urteil
    "_sdf_berater_executiondispatch": "green",
    "_sdf_berater_garbagecollection": "green",
    "_sdf_berater_validator": "green",
    "_sdf_berater_statemaintain": "green",
    "_sdf_berater_dependencyanalyzer": "green",
    "_sdf_berater_sequenceplanner": "green",
    "_sdf_berater_batchplanner": "green",
    "_sdf_berater_batchende": "green",
    "_sdf_berater_orphan_scan": "green",
    "_sdf_berater_post_sc_pl_resync": "green",
    "_srs_compute": "green",
    # --- YELLOW (mechanischer Rahmen + EIN eingebetteter Urteils-/Schaetz-/Relevanz-Seam) ---
    "_w_fetch": "yellow",                       # Relevanz-Bewertung RELEVANT/GRENZWERTIG + Synonym-Disambig
    "_git_analyse": "yellow",                   # IN-SCOPE/OUT-OF-SCOPE-Drift-Urteil
    "_k_score": "yellow",                       # basis_gewicht-Schaetz-Seam speist die Formel (sonst Schwellen-Mathe)
    "_idf_berater_itemcontext": "yellow",
    "_idf_berater_stageplanner": "yellow",
    "_idf_berater_finalsummary": "yellow",
    "_idf_berater_metric_derivation": "yellow",
    "_idf_berater_akextraktion": "yellow",
    "_sdf_berater_architecturalbrief": "yellow",
    "_sdf_berater_stageelevation": "yellow",    # next_action-Urteil (GREEN/PARTIAL/RED->ELEVATE/RETRY) = 1 Seam
    # --- RED (echte Urteils-/Wahrheits-/Intent-Seams — jetzt EXPLIZIT dokumentiert statt zufaellig fail-safe) ---
    "_idf_berater_modelsync": "red",            # Truth-Promote/Confirm-Kollaps
    "_idf_berater_plbewertung": "red",          # SRS-Saettigung/Bottleneck-Urteil
    "_idf_berater_specparse": "red",
    "dispatch_findings": "red",                 # det. Motor-SCHALE, aber Substanz-Kern = Findings-Intent/CORE-Wahrheit (opus)
    "_model": "red",                            # Model/W{n}-Wahrheits-Wissensbau
    "_spec": "red",                             # Ziel-Architektur/SOLL-Wissensbau
    "_taskdefinition": "red",                   # Crumbs->Foundation-Wissensbau
    "_a_berater_findingsreview": "red",         # Findings-Verdikt (welche ueberleben)
    "_a_berater_domainbrief": "red",            # semantischer Domaenen-Match/Contradiction (opus)

    # ===== BL-383 batch_PL4 (2026-06-19): Szenario-Eval-Gate — SELBST-KONSISTENZ-ZONIERUNG =====
    # AK-8 / W-INV-3 / W-PRC-3: Das Eval-Gate ist Anti-false-GREEN (die INV-VEHIKEL-false-GREEN-
    # Lehre von der TDD-/Code-Ebene auf die ARCHITEKTUR-Bewertung gehoben). Sein eigener
    # qualitativer URTEILS-KERN MUSS darum eine ROTE Zone sein (INV-VEHIKEL-2) — ein per Workflow
    # durchgewinktes Eval-Gate waere die ironische Selbst-Verletzung der Doktrin, die es durchsetzt.
    # INV-VEHIKEL-6b: EXPLIZIT rot registriert (nicht nur Fail-Safe), damit die Selbst-Konsistenz
    # bewusst + dokumentiert ist. rot-never-Invariante traegt: in KEINEM Modus Workflow.
    "_eval_berater_realizationverify": "red",   # Realization-Suitability-Verify (AK-3: passt das Pattern? Kazman-Urteil)
    "_eval_berater_designeval_urteil": "red",   # qualitatives Design-Eval-Urteil (AK-1 rein-qualitativer Pfad)
    "_eval_berater_drifturteil": "red",         # semantische ADR-Drift-Widerspruchs-Erkennung (AK-2)
    # GEGENSTUECK (W-LOC-4): der DETERMINISTISCHE Gate-Script-Anteil (eval_finding-Schema-Validitaet,
    # risk_class-Enum, Existenz-/Zaehl-/ID-Checks, metric_component-SOLL/IST-Vergleich) ist gruen-faehig
    # (analog quality_model_wform.py). Nur der Urteils-Kern ist rot — die Zonierung schneidet entlang
    # der INV-VEHIKEL-Zonen, NICHT das ganze Gate rot. (Konsum-per-ID/eval_id_consume = read-only
    # Schema-Lookup = ebenfalls deterministisch unter diesem Script-Anteil.)
    "eval_gate_script": "green",
}

# Praefix-Regel: ALLE guards sind hart-deterministisch (Karte §3.4, 14/14 gruen).
# Auch noch-nicht-registrierte guard_-Hooks werden so korrekt gruen klassifiziert.
# ZUKUNFTS-HAZARD (BL-330 Verify medium): die Regel ist offen — ein kuenftiger Guard mit
# LLM-/Intent-Seam (z.B. "guard_intent_check") wuerde stillschweigend gruen. REGEL: ein
# urteils-tragender Guard MUSS explizit als "red" in ZONE_REGISTRY stehen — der Registry-
# Lookup laeuft VOR der Praefix-Regel und ueberschreibt sie. Kein aktuelles Leck.
_GREEN_PREFIXES = ("guard_",)


# ---------------------------------------------------------------------------
# zone_of / resolve_vehicle / vehicle_for
# ---------------------------------------------------------------------------

def _norm(activity: Optional[str]) -> str:
    return (activity or "").strip().lower()


def zone_of(activity: Optional[str]) -> str:
    """Registry-Lookup. Liefert {green,yellow,red}.

    Reihenfolge: explizite Registry > Green-Praefix-Regel (guard_*) > FAIL-SAFE rot.
    Unbekannt/leer/None -> 'red' (unklassifiziert = altmodisch, nie versehentlich Workflow).
    """
    key = _norm(activity)
    if not key:
        return "red"
    if key in ZONE_REGISTRY:
        return ZONE_REGISTRY[key]
    for pref in _GREEN_PREFIXES:
        if key.startswith(pref):
            return "green"
    return "red"


def resolve_vehicle(zone: str, mode: Optional[str]) -> str:
    """Die 3-Modi-Matrix. Liefert {workflow,advisory,worker}.

    KERN-INVARIANTE: zone=='red' -> IMMER 'worker' (jeder Modus). Kognitiv ist
    strukturell nicht workflow-faehig. Unbekannter Modus -> fail-safe 'worker'.
    """
    # BL-330 Verify-Hardening (low): zone-arg normalisieren (symmetrisch zu mode), damit die
    # rot-Invariante auch fuer Nicht-kanonische Caller haelt (nicht nur ueber zone_of()).
    z = _norm(zone)
    # INVARIANTE zuerst: rot ist nie workflow, egal welcher Modus.
    if z == "red":
        return "worker"
    m = _norm(mode)
    if m == "normal":
        return "workflow" if z == "green" else "worker"
    if m == "fast":
        if z == "green":
            return "workflow"
        if z == "yellow":
            return "advisory"
        return "worker"
    # "false" und alles Unbekannte: fail-safe altmodisch.
    return "worker"


def vehicle_for(activity: Optional[str], mode: Optional[str]) -> str:
    """Bequemlichkeit: zone_of(activity) -> resolve_vehicle(zone, mode)."""
    return resolve_vehicle(zone_of(activity), mode)


def zone_advisory(activity: Optional[str], mode: str = "false") -> dict:
    """BL-330 AK-3: Advisory-only Fahrzeug-Empfehlung fuer einen Berater-Kontext.

    Nutzt die bestehende resolve_vehicle/zone_of-Logik und verpackt das Ergebnis
    als strukturiertes Advisory-Objekt. Entscheidet NIE — empfiehlt nur (analog INV-MODUS-1).

    Args:
        activity: Aktivitaets-Name (Skill/Berater/TDD-Step). None/unbekannt -> fail-safe rot.
        mode:     Workflow-Dial-Param: "false" | "normal" | "fast". Default "false".

    Returns:
        dict mit 6 Pflicht-Keys:
          activity           - uebergebener activity-Wert (raw, nicht normalisiert)
          zone               - "red" | "yellow" | "green"
          recommended_vehicle - "worker" | "advisory" | "workflow"
          motor_faehig       - True NUR wenn recommended_vehicle == "workflow"
          advisory_only      - IMMER True (Berater schlaegt vor, entscheidet nie)
          rationale          - non-empty str mit Erklaerung

    Fail-safe: unbekannte/None activity -> rot/worker, motor_faehig=False, advisory_only=True.
    """
    zone = zone_of(activity)
    vehicle = resolve_vehicle(zone, mode)
    motor_faehig: bool = (vehicle == "workflow")

    # Rationale-Aufbau: erklaert zone + motor_faehig-Schluss
    if not activity:
        rationale = (
            "Keine Activity angegeben — fail-safe rot (unklassifiziert = altmodisch). "
            "Motor-Faehigkeit erfordert gruene Zone + Workflow-Dial (normal|fast)."
        )
    elif zone_of(activity) == "red" and _norm(activity) not in ZONE_REGISTRY:
        # Unbekannte Activity (fail-safe-rot)
        rationale = (
            f"Activity '{activity}' nicht in ZONE_REGISTRY — fail-safe rot. "
            "Unklassifiziert = altmodisch (INV-VEHIKEL-2: rot ist NIE motor-faehig)."
        )
    elif zone == "red":
        rationale = (
            f"Activity '{activity}' ist zone=red (kognitiv/Urteils-Seam). "
            "Rote Zone traegt GREEN-Klarheits-/Wahrheits-/Intent-Urteil — "
            "MUSS altmodisch (Worker). NIE Workflow (INV-VEHIKEL-2)."
        )
    elif zone == "yellow":
        if vehicle == "advisory":
            rationale = (
                f"Activity '{activity}' ist zone=yellow (hybrid) @ mode={mode}. "
                "Ein eingebetteter Urteils-Seam — Workflow rechnet, Lead/Berater bestaetigt. "
                "mode=fast -> advisory (kein vollstaendiger Motor-Dispatch)."
            )
        else:
            rationale = (
                f"Activity '{activity}' ist zone=yellow (hybrid) @ mode={mode}. "
                "mode=false|normal -> Worker (yellow nur bei mode=fast advisory-faehig)."
            )
    else:
        # zone == "green"
        if motor_faehig:
            rationale = (
                f"Activity '{activity}' ist zone=green (hart-deterministisch) @ mode={mode}. "
                "Kein Korrektheits-Seam — Workflow PROFITIERT. "
                "motor_faehig=True: recommended_vehicle=workflow."
            )
        else:
            rationale = (
                f"Activity '{activity}' ist zone=green @ mode={mode} (false). "
                "Dial=false -> alles Worker (altmodisch), unabhaengig von Zone. "
                "motor_faehig=False weil mode=false."
            )

    return {
        "activity": activity,
        "zone": zone,
        "recommended_vehicle": vehicle,
        "motor_faehig": motor_faehig,
        "advisory_only": True,
        "rationale": rationale,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _configure_utf8_stdout() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except AttributeError:
            pass


def main() -> None:
    _configure_utf8_stdout()
    parser = argparse.ArgumentParser(description="BL-330: Determinismus-Karte als Config")
    sub = parser.add_subparsers(dest="command", required=True)

    p_v = sub.add_parser("vehicle", help="Vehikel fuer eine Aktivitaet + Modus")
    p_v.add_argument("--activity", required=True)
    p_v.add_argument("--mode", required=True, help="false|normal|fast")
    p_v.add_argument("--json", action="store_true")

    p_z = sub.add_parser("zone", help="Zone einer Aktivitaet")
    p_z.add_argument("--activity", required=True)
    p_z.add_argument("--json", action="store_true")

    sub.add_parser("dump", help="Gesamte Registry als JSON")

    args = parser.parse_args()

    if args.command == "vehicle":
        zone = zone_of(args.activity)
        veh = resolve_vehicle(zone, args.mode)
        if getattr(args, "json", False):
            print(json.dumps({"activity": args.activity, "zone": zone,
                              "mode": args.mode, "vehicle": veh}))
        else:
            print(f"{args.activity} [{zone}] @ {args.mode} -> {veh}")
    elif args.command == "zone":
        zone = zone_of(args.activity)
        if getattr(args, "json", False):
            print(json.dumps({"activity": args.activity, "zone": zone}))
        else:
            print(f"{args.activity} -> {zone}")
    elif args.command == "dump":
        print(json.dumps(ZONE_REGISTRY, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
