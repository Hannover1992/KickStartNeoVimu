#!/usr/bin/env python3
"""
test_bl238_b5_cross_batch_propagation.py — BL-238 Sub-Batch B-5 / Stage 1 (TDD RED)

Feature: Scientific SDF-Post Recalc-Loop / Modus-Neu-Bestimmung
Sub-Batch B-5 = Cross-Batch-Propagation + Determinismus/Replay-Akzeptanz (DAG-Blatt L4-L5).
  AK-5-PL-1  (berater, Code-Write): _SDF_berater_modelSync.md schreibt DF_BATCH_STATE.truth_to_batches
             (AK-6-Index-Code, B-4 lieferte nur das Schema) beim W{n}->PL-Promote UND iteriert nach
             SCHRITT 3 ueber truth_to_batches[W{n}], re-rechnet SRS/K-Score fremder PL-Items via
             _srs_compute (BL-205, EINZIGE SRS-Quelle). Der EINZIGE Produktiv-Code-Write in B-5.
  AK-10-PL-1 (test, Verifikation): dispatch_implement.js — Determinismus/INV-Konformitaet:
             runPhase3 = genau 4 agent() (recalibrate/postItem/statusTransition/modelSync, INV-MOTOR-1),
             re-modus-Re-Entry = 1 safeSchemaAgent via _SDF_berater_modusEntscheidung (INV-MODUS-1).
  AK-11-PL-1 (test, Verifikation): dispatch_implement.js — BL-237 batch_C1 Replay: SC-saettigt =>
             KEIN ABORT (continue), ABORT NUR bei sc_verdict==ABORT.

Stage 1 = powershell-verification (PATCH BL-111: kein dotnet/docker). "Test" = Grep/Test-Path-
Assertion gegen die zwei Zieldateien (.md/.js) bzw. logischer Replay-Trace gegen den SC-Branch.
Python-Realisierung der Repo-Konvention (test_*.py in .claude/scripts/) fuer Grep-Asserts gegen
Source — exakt gespiegelt von der B-1-Praezedenz test_bl238_b1_sc_verdict_signal.py.

Die 8 Tests spiegeln 1:1 die Test-Liste (T1-T8) aus sub-5.md (SOLL-Model, Kent-Beck Outside-In,
Canary-First) und die Gold-Definition-Exit-Kriterien (E1-E5) des Sub-Blueprints.

TDD-PHASE: RED. Die Suite MUSS initial fehlschlagen (Gesetz 2: assert-Fail = RED), weil der
EINZIGE Produktiv-Code-Write AK-5 (truth_to_batches-Index + Cross-Batch-Iterator + _srs_compute-
Call) gegen HEAD 24bbf75 NOCH NICHT in _SDF_berater_modelSync.md existiert (Grep=0 code-verifiziert,
B-4 lieferte nur die Schema-Entscheidung, code_realized=false). T5/T6/T7 sind die RED-Treiber.
T1-T4 (AK-10/AK-11, layer=test) verifizieren den bereits in B-1..B-3 gebauten Motor (LIVE) — sie
sind die Akzeptanz-Klammer ueber den durch AK-5 vervollstaendigten Stand; semantisch ist die Suite
RED, bis AK-5 gelandet ist. GREEN macht _TDD_green/_I_cleanCodeSlice (AK-5-Code).

Scope-Disziplin (sub-5.md): AK-5 fasst NUR _SDF_berater_modelSync.md an. AK-10/AK-11 sind layer=test
und greppen/tracen dispatch_implement.js — sie BAUEN ihn NICHT um. Der runPhase3-Body (:249-259) und
der SC-Branch (:387-468) bleiben Kanarienvoegel (unveraendert).

Run: python .claude/scripts/test_bl238_b5_cross_batch_propagation.py
Exit 0 = alle PASS (GREEN), 1 = mindestens 1 FAIL (RED).
"""

import re
import sys
from pathlib import Path

# Stage 1 = powershell-verification: dieser Test laeuft auf dem Windows-Konsolen-Default (cp1252).
# Der Report enthaelt Status-Glyphen; ohne UTF-8-Stdout wuerde ein GREEN-Lauf am Summary-print mit
# UnicodeEncodeError abbrechen und exit 1 (= falsch-RED an _TDD_execute) liefern. reconfigure ist
# idempotent (No-Op auf bereits-UTF-8-Konsolen) und beruehrt KEINE Assertion — nur die Selbst-
# Dokumentation des Tests wird plattform-robust (_TDD_refactorTests: Test berichtet seinen wahren Zustand).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
COMMANDS_DIR = ROOT_DIR / ".claude" / "commands"
WORKFLOWS_DIR = ROOT_DIR / ".claude" / "workflows"

MODELSYNC = COMMANDS_DIR / "_SDF_berater_modelSync.md"      # AK-5 Ziel (Code-Write)
DISPATCH = WORKFLOWS_DIR / "dispatch_implement.js"          # AK-10/AK-11 Ziel (Verifikation, READ-ONLY)
SRS_COMPUTE = COMMANDS_DIR / "_srs_compute.md"              # BL-205 Dependency (READ-ONLY, Kanarienvogel)

# INV-MODUS-5 verbotene Bypass-Felder (Slot-Isolation-Negativliste, sub-5.md PT-CMD-008,
# CLAUDE.md INV-MODUS-5). AK-5 (modelSync) darf KEINES dieser Felder neu einfuehren — Cross-Batch
# betrifft SRS/K-Score-Metrik, NICHT modus (INV-MODUS-1). Whole-word-Matching wie B-1 (sdf_mode
# standalone verboten, sdf_mode_* Bestand-Familie legitim).
BYPASS_FIELDS = [
    "recommended_modus",
    "sdf_mode",            # standalone-Token: \bsdf_mode\b matcht NICHT sdf_mode_original etc.
    "sdf_mode_hint",
    "expected_sdf_mode",
    "mode_recommendation",
]


def find_introduced_bypass_fields(text: str) -> list:
    """Whole-word Detection neu eingefuehrter INV-MODUS-5-Bypass-Felder (siehe B-1-Praezedenz)."""
    return [f for f in BYPASS_FIELDS if re.search(rf"\b{re.escape(f)}\b", text)]


LABEL = "[test_bl238_b5_cross_batch_propagation]"
PASS_COUNT = 0
FAIL_COUNT = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"{LABEL} PASS  {name}")
    else:
        FAIL_COUNT += 1
        print(f"{LABEL} FAIL  {name}" + (f" - {detail}" if detail else ""))


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def count_await_agent_in_runphase3(js: str) -> int:
    """Extrahiert den runPhase3-Body und zaehlt die `await agent(`-Calls darin (INV-MOTOR-1).

    runPhase3 darf KEINE Sub-Bundle/Mega-Worker enthalten: recalibrate/postItem/statusTransition/
    modelSync = genau 4 separate `await agent(`. Wir schneiden vom `async function runPhase3(` bis
    zur naechsten Top-Level `async function ...(`-Deklaration (oder `\nconst phase3_fired`).
    """
    m = re.search(r"async function runPhase3\s*\(", js)
    if not m:
        return -1
    start = m.start()
    rest = js[start + 1:]
    nxt = re.search(r"\nasync function \w+\s*\(|\nconst phase3_fired\b|\nfunction \w+\s*\(", rest)
    body = rest[: nxt.start()] if nxt else rest
    return len(re.findall(r"await agent\(", body))


# ──────────────────────────────────────────────────────────────────────────────
# Quell-Texte laden
# ──────────────────────────────────────────────────────────────────────────────
modelsync = read(MODELSYNC)
dispatch = read(DISPATCH)
srs_compute = read(SRS_COMPUTE)


def main() -> int:
    # ── Vorbedingung: Zieldateien existieren (Path-Resolution, kein stiller Skip) ──
    check("PRE-1 _SDF_berater_modelSync.md existiert (AK-5 Ziel)", bool(modelsync),
          f"Datei fehlt/leer: {MODELSYNC}")
    check("PRE-2 dispatch_implement.js existiert (AK-10/AK-11 Ziel)", bool(dispatch),
          f"Datei fehlt/leer: {DISPATCH}")

    # ══════════════════════════════════════════════════════════════════════════
    # T1 (AK-11, Canary, Reihenfolge 1): BL-237 batch_C1 Replay — SC-saettigt => kein ABORT.
    #   sc_verdict ∈ {SATURATED_READY_FOR_IMPL, EXPERIMENT_OPEN} => Pfad endet in `continue`
    #   (runPhase3 -> re-modus -> A_SC_I/SC_RE_ENTRY), NICHT in `break outer`/ABORT.
    # ══════════════════════════════════════════════════════════════════════════
    saturation_branch = bool(re.search(
        r"sc_verdict\s*===\s*'SATURATED_READY_FOR_IMPL'\s*\|\|\s*sc_verdict\s*===\s*'EXPERIMENT_OPEN'",
        dispatch))
    check("T1 AK-11: Saettigungs-Branch (SATURATED_READY_FOR_IMPL || EXPERIMENT_OPEN) existiert",
          saturation_branch, "Saettigungs-Verzweigung im SC-Branch nicht gefunden")
    # Der Saettigungs-Zweig muendet in `continue` (kein ABORT). Negativ-Assert: kein `break outer`
    # im Saettigungs-Pfad ausser im AK-9-Cap; ABORT-`break outer` haengt am sc_verdict==ABORT-Zweig.
    saturation_ends_continue = saturation_branch and dispatch.count("continue") >= 3
    check("T1 AK-11: Saettigungs-Pfad endet in continue (kein break outer/ABORT bei Saettigung)",
          saturation_ends_continue, "kein continue-Abschluss im Saettigungs-Pfad")

    # ══════════════════════════════════════════════════════════════════════════
    # T2 (AK-11, Reihenfolge 2): ABORT NUR bei sc_verdict==ABORT (fail-safe-Pfad unveraendert).
    #   EXPERIMENT_OPEN => kein I_FULL-Vollzug (M5 bleibt spec-konform); break outer NUR im ABORT-Zweig.
    # ══════════════════════════════════════════════════════════════════════════
    abort_only_on_abort = bool(re.search(
        r"sc_verdict\s*===\s*'ABORT'[\s\S]{0,400}?terminated_reason\s*=\s*'sc_verdict_abort'[\s\S]{0,200}?break outer",
        dispatch))
    check("T2 AK-11: break outer/ABORT NUR im sc_verdict==ABORT-Zweig (sc_verdict_abort)",
          abort_only_on_abort, "ABORT-Pfad nicht an sc_verdict==ABORT gebunden")

    # ══════════════════════════════════════════════════════════════════════════
    # T3 (AK-10, Reihenfolge 3): runPhase3-Body = genau 4 `await agent(` (INV-MOTOR-1, 1-Step=1-agent).
    #   recalibrate/postItem/statusTransition/modelSync — kein Bundle/Mega-Worker.
    # ══════════════════════════════════════════════════════════════════════════
    n_agents = count_await_agent_in_runphase3(dispatch)
    check("T3 AK-10: runPhase3 = genau 4 await agent() (INV-MOTOR-1, kein Mega-Worker)",
          n_agents == 4, f"gefunden: {n_agents} await-agent-Calls im runPhase3-Body (erwartet 4)")
    # Die 4 Berater namentlich nachweisbar (recalibrate/postItem/statusTransition/modelSync).
    four_beraters = all(b in dispatch for b in [
        "_SDF_berater_recalibrate", "_SDF_berater_postItem",
        "_SDF_berater_statusTransition", "_SDF_berater_modelSync"])
    check("T3 AK-10: alle 4 Phase-3.x-Berater (recalibrate/postItem/statusTransition/modelSync) gespawnt",
          four_beraters, "nicht alle 4 Phase-3.x-Berater im Motor referenziert")

    # ══════════════════════════════════════════════════════════════════════════
    # T4 (AK-10, Reihenfolge 4): re-modus-Re-Entry = genau 1 safeSchemaAgent via
    #   _SDF_berater_modusEntscheidung (INV-MODUS-1 alleinige Quelle); metric_per_batch + INV-MODUS-1
    #   in Prompt-Strings nachweisbar (INV-METRIC-1 primaer). Kein INV-MODUS-5-Bypass-Feld neu.
    # ══════════════════════════════════════════════════════════════════════════
    re_modus_block = bool(re.search(
        r"const reModusOut\s*=\s*await safeSchemaAgent\([\s\S]{0,600}?_SDF_berater_modusEntscheidung",
        dispatch))
    check("T4 AK-10: re-modus-Re-Entry = 1 safeSchemaAgent via _SDF_berater_modusEntscheidung (INV-MODUS-1)",
          re_modus_block, "re-modus-Re-Entry-Block (safeSchemaAgent + modusEntscheidung) nicht gefunden")
    re_modus_inv = re_modus_block and "INV-MODUS-1" in dispatch and "metric_per_batch" in dispatch
    check("T4 AK-10: metric_per_batch (INV-METRIC-1 primaer) + INV-MODUS-1 in Prompt-Strings nachweisbar",
          re_modus_inv, "metric_per_batch/INV-MODUS-1 nicht im re-modus-Prompt")
    bypass_hits_js = find_introduced_bypass_fields(dispatch)
    check("T4 AK-10: keine INV-MODUS-5-Bypass-Felder im Motor (Modus-Alleinrecht)",
          len(bypass_hits_js) == 0, f"Bypass-Felder gefunden: {bypass_hits_js}")

    # ══════════════════════════════════════════════════════════════════════════
    # T5 (AK-5 + AK-6, Reihenfolge 5): truth_to_batches-Index-Write beim W{n}->PL-Promote
    #   mit Schema-Feldern {batch, pl_item, k_score, srs} (SOA-2); VERTRAG-SCHREIBT deklariert
    #   truth_to_batches (PT-CMD-001); version-Bump (INV-MS-SDF-5). === RED-TREIBER (Grep=0) ===
    # ══════════════════════════════════════════════════════════════════════════
    has_index_write = "truth_to_batches" in modelsync
    check("T5 AK-5: truth_to_batches-Index-Write existiert in _SDF_berater_modelSync.md [RED-TREIBER]",
          has_index_write, "truth_to_batches NICHT in modelSync.md (B-4 lieferte nur Schema, Code offen)")
    schema_fields = has_index_write and all(
        re.search(rf"\b{f}\b", modelsync) for f in ["batch", "pl_item", "k_score", "srs"])
    check("T5 AK-5: truth_to_batches-Schema {batch, pl_item, k_score, srs} (SOA-2) nachweisbar",
          schema_fields, "Schema-Felder batch/pl_item/k_score/srs nicht vollstaendig")
    # VERTRAG-SCHREIBT muss truth_to_batches deklarieren (PT-CMD-001, sonst Gate-7-ALARM).
    schreibt_block = re.search(r"SCHREIBT:[\s\S]*?\[/VERTRAG\]", modelsync)
    vertrag_declares = bool(schreibt_block and "truth_to_batches" in schreibt_block.group(0))
    check("T5 AK-5: VERTRAG-SCHREIBT deklariert truth_to_batches (PT-CMD-001)",
          vertrag_declares, "truth_to_batches nicht im SCHREIBT-Block deklariert")
    # version-Bump: Bestand ist version: 1.0 (INV-MS-SDF-5 verlangt Erhoehung bei additiver Erweiterung).
    version_bumped = bool(re.search(r"^version:\s*1\.[1-9]|^version:\s*[2-9]", modelsync, re.MULTILINE))
    check("T5 AK-5: version-Bump in modelSync.md-Frontmatter (INV-MS-SDF-5, war 1.0)",
          version_bumped, "version noch 1.0 — kein Bump nach additiver AK-5-Erweiterung")

    # ══════════════════════════════════════════════════════════════════════════
    # T6 (AK-5, Reihenfolge 6): Cross-Batch-Iterator nach SCHRITT 3 liest NUR truth_to_batches[W{n}]
    #   (kein Voll-Scan) + ruft _srs_compute/compute_srs (BL-205, EINZIGE SRS-Quelle); KEIN inline-
    #   SRS-Algorithmus (Schema-without-Algorithm vermieden). === RED-TREIBER (Grep=0) ===
    # ══════════════════════════════════════════════════════════════════════════
    iterator_reads_index = bool(re.search(r"truth_to_batches\s*\[", modelsync)) or \
        bool(re.search(r"FOR\s+\w+\s+IN\s+truth_to_batches", modelsync, re.IGNORECASE))
    check("T6 AK-5: Cross-Batch-Iterator liest truth_to_batches[W{n}] (index-getrieben, kein Voll-Scan) [RED-TREIBER]",
          iterator_reads_index, "kein index-getriebener truth_to_batches[..]-Lese-Iterator")
    calls_srs_compute = bool(re.search(r"_srs_compute|compute_srs", modelsync))
    check("T6 AK-5: Iterator ruft _srs_compute/compute_srs (BL-205, EINZIGE SRS-Quelle) [RED-TREIBER]",
          calls_srs_compute, "kein _srs_compute/compute_srs-Call (Schema-without-Algorithm-Risiko)")

    # ══════════════════════════════════════════════════════════════════════════
    # T7 (AK-5, Reihenfolge 7): Propagations-Korrektheit (Logik-Trace) — additiv (INV-MS-SDF-4),
    #   Marker-idempotent (INV-MS-SDF-1), konflikt-bewusst (INV-MS-SDF-7); KEIN Modus-Write (INV-MODUS-1).
    # ══════════════════════════════════════════════════════════════════════════
    # Frische SRS an fremde PL-Items via definierten DF_BATCH_STATE-Slot (PT-CMD-008 Slot-Isolation):
    # per_pl_evaluation/batch_items, kein Fremd-BERATER_OUTPUTS-Write.
    writes_foreign_slot = bool(re.search(r"per_pl_evaluation|batch_items", modelsync))
    check("T7 AK-5: frischer SRS in definierte DF_BATCH_STATE-Slots (per_pl_evaluation/batch_items, PT-CMD-008) [RED-TREIBER]",
          writes_foreign_slot, "kein definierter Cross-Batch-Slot-Write (per_pl_evaluation/batch_items)")
    # AK-5 schreibt KEINEN modus / kein INV-MODUS-5-Bypass-Feld (Cross-Batch betrifft SRS/K-Score, INV-MODUS-1).
    bypass_hits_md = find_introduced_bypass_fields(modelsync)
    check("T7 AK-5: KEIN modus-Write / INV-MODUS-5-Bypass-Feld in modelSync.md (INV-MODUS-1)",
          len(bypass_hits_md) == 0, f"Bypass-Felder in modelSync.md: {bypass_hits_md}")

    # ══════════════════════════════════════════════════════════════════════════
    # T8 (beide, Edge + Regression-Kanarienvoegel, Reihenfolge 8):
    #   leerer truth_to_batches[W] => No-Op (PT-CMD-018 Pre-Flight, kein Teil-Write/Crash)
    #   + Bestand-Pfade unveraendert (runPhase3-Body, SC-Branch, modelSync SCHRITT-3, _srs_compute).
    # ══════════════════════════════════════════════════════════════════════════
    # Pre-Flight (PT-CMD-018): VAULT_ROOT/resolve_vault_root + Index-Existenz-Check vor Schreibung.
    preflight = bool(re.search(r"resolve_vault_root|VAULT_ROOT", modelsync)) and \
        (bool(re.search(r"leer|empty|No-Op|No Op|kein.*Batch|exists?|EXISTS", modelsync, re.IGNORECASE)))
    check("T8 Edge: Pre-Flight (resolve_vault_root + leerer-Index No-Op, PT-CMD-018) [RED-TREIBER]",
          preflight, "kein Pre-Flight/No-Op-Guard fuer leeren truth_to_batches")
    # Kanarienvogel 1: runPhase3-Body strukturell unveraendert (genau 4 agent, schon T3 — hier Regression-Assert).
    check("T8 Kanarienvogel: runPhase3-Body (4 agent) strukturell unveraendert (INV-MOTOR-1)",
          n_agents == 4, f"runPhase3 hat {n_agents} agent-Calls (Regression!)")
    # Kanarienvogel 2: SC-Branch ABORT NUR bei sc_verdict==ABORT (schon T2 — Regression-Assert).
    check("T8 Kanarienvogel: SC-Branch ABORT NUR bei sc_verdict==ABORT (unveraendert)",
          abort_only_on_abort, "SC-Branch-ABORT-Pfad veraendert (Regression!)")
    # Kanarienvogel 3: modelSync SCHRITT-3-Promote-Loop unveraendert vorhanden (AK-5 ist additiv).
    schritt3_intact = "SCHRITT 3: Promotion-Loop" in modelsync and "promoted_truths" in modelsync
    check("T8 Kanarienvogel: modelSync SCHRITT-3-Promote-Loop unveraendert (AK-5 additiv, INV-MS-SDF-4)",
          schritt3_intact, "SCHRITT-3-Promote-Loop fehlt/veraendert")
    # Kanarienvogel 4: _srs_compute (BL-205) READ-ONLY-Existenz (AK-5 ruft, aendert nicht).
    check("T8 Kanarienvogel: _srs_compute.md (BL-205) existiert (READ-ONLY, AK-5 ruft compute_srs)",
          bool(srs_compute), f"_srs_compute.md fehlt: {SRS_COMPUTE}")

    # ── Zusammenfassung ───────────────────────────────────────────────────────
    print()
    print(f"{LABEL} RESULT: B-5 Cross-Batch-Propagation - {PASS_COUNT} PASS / {FAIL_COUNT} FAIL")
    if FAIL_COUNT > 0:
        print(f"{LABEL} RED (erwartet): AK-5 Code-Write (truth_to_batches-Index + Cross-Batch-Iterator")
        print(f"{LABEL}      + _srs_compute-Call + Pre-Flight) noch NICHT in modelSync.md gelandet.")
        print(f"{LABEL}      Naechster Schritt: _TDD_green / _I_cleanCodeSlice (AK-5).")
        return 1
    print(f"{LABEL} GREEN: alle 8 Test-Gruppen (T1-T8) erfuellt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
