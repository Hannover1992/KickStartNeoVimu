#!/usr/bin/env python3
"""test_idf_express_lane.py — Reader-Konformitaets-Test fuer die IDF-Express-Lane (BL-403 batch_2/AK-6).

ZWECK (AK-6): testbar machen, dass JEDER Express-Inline-Trivial-Vertrag in _IDF_orchestrate.md
die Pflicht-Felder traegt, die Downstream-Konsumenten (SDF-Outer-Loop / C3 modusEntscheidung /
idf-light-Gate / finalSummary / SDF-Post) TATSAECHLICH LESEN. Schema-Diff == 0 auf den
KONSUMIERTEN Feldern (nicht: alle Echt-Felder — nur die gelesenen).

PRINZIP: pro Skip-Berater
    inline_fields(_IDF_orchestrate.md express-Zweig)  ⊇  consumed_fields(live Consumer-Reads)
Fehlt ein konsumiertes Feld im Inline-Vertrag -> der Test ist ROT und nennt Berater+Feld.
Das ist der Zweck: er soll die 2a-ii-Schema-Luecken fangen. NICHT abschwaechen um gruen zu werden.

So benutzen: `py -3 -m pytest .claude/scripts/test_idf_express_lane.py -q`
ODER als Report: `py -3 .claude/scripts/test_idf_express_lane.py`  (druckt inline vs consumed je Berater).

QUELLEN (Single-Source — bei Aenderung der Inline-Vertraege/Consumer mitziehen):
  - Inline-Vertraege: _IDF_orchestrate.md  (express_provisional==true + express_gate=="EXPRESS"-Zweige)
  - Consumed-Set:     belegt pro Feld via CONSUMED[berater] (Consumer-Skill + Zeilen-Hinweis)
"""
from __future__ import annotations
import re, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_ROOT = SCRIPT_DIR.parent.parent
ORCH = REPO_ROOT / ".claude" / "commands" / "_IDF_orchestrate.md"


# ════════════════════════════ INLINE-VERTRAG-PARSER ════════════════════════════
# Jeder Inline-Vertrag ist eine "Schreibe/Set ... = {feld: ..., feld2: ...}"-Zeile im Orchestrator,
# markiert via last_berater:"X(idf-express-skip)" bzw. dem festen Slot-Namen. Wir extrahieren die
# Top-Level-Feld-Keys aus dem Objekt-Literal (dem ersten {...}-Block der Zeile).

def _read_orch() -> str:
    assert ORCH.exists(), f"Orchestrator nicht gefunden: {ORCH}"
    return ORCH.read_text(encoding="utf-8")


def _top_level_keys(obj_literal: str) -> set:
    """Extrahiert die Top-Level `key:`-Namen aus einem {...}-Objekt-Literal (verschachtelte {}/[] ignoriert)."""
    keys = set()
    depth = 0
    i = 0
    n = len(obj_literal)
    # nur INNERHALB des aeussersten {...}
    start = obj_literal.find("{")
    if start < 0:
        return keys
    i = start + 1
    token = ""
    expecting_key = True
    while i < n:
        c = obj_literal[i]
        if c in "{[":
            depth += 1
            expecting_key = False
            token = ""
        elif c in "}]":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0:
            if c == ":" and expecting_key:
                k = token.strip().strip('"').strip("'").strip()
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
                    keys.add(k)
                token = ""
                expecting_key = False
            elif c == ",":
                token = ""
                expecting_key = True
            else:
                token += c
        i += 1
    return keys


def _slot_name(line: str) -> str | None:
    """Der SLOT-Name eines Inline-Vertrags = letztes dotted Segment des LHS vor '='.
    Bsp: 'Schreibe DF_BATCH_STATE.batch_items_per_batch = {batch_1: ...}' -> 'batch_items_per_batch'
         'Set DF_BATCH_STATE.batch_type = "polish"' -> 'batch_type'."""
    m = re.match(r"\s*(?:Schreibe|Set)\s+([A-Za-z_][\w.]*?)\s*=", line)
    if not m:
        return None
    lhs = m.group(1)
    seg = lhs.split(".")[-1]
    return seg if re.fullmatch(r"[A-Za-z_]\w*", seg) else None


def _extract_inline_fields(orch: str, anchor_regexes: list[str]) -> set:
    """Sammelt die Vertrag-Felder aus allen Inline-Zeilen, die EINEN der Anker matchen.

    Pro Zeile zaehlen BEIDE Ebenen zum Feld-Set:
      (a) der SLOT-Name (dotted LHS vor '=') — z.B. batch_items_per_batch / batch_stages / batch_type;
          das ist das Feld, das der Downstream-Reader unter DF_BATCH_STATE.<SLOT> liest.
      (b) die INNEREN Top-Level-Keys des {...}-Objekts — z.B. bei BERATER_OUTPUTS_IDF.batchPlan =
          {batch_size, batch_items, ...} liest der Consumer diese inneren Keys.
    So wird 'batch_items_per_batch' (Slot) korrekt erfasst statt faelschlich nur 'batch_1' (innerer Key
    des Trivial-Maps) — und gleichzeitig die echten inneren Vertragsfelder. Spurious innere Keys wie
    'batch_1' sind harmlos: sie tauchen in keinem CONSUMED-Set auf.
    """
    fields = set()
    for line in orch.splitlines():
        for rx in anchor_regexes:
            if re.search(rx, line):
                slot = _slot_name(line)
                if slot:
                    fields.add(slot)
                if "{" in line:
                    fields |= _top_level_keys(line)
                break
    return fields


# Anker pro Skip-Berater: die Zeile(n) in _IDF_orchestrate.md, die seinen Inline-Vertrag schreiben.
# (Wir ankern auf den eindeutigen Slot + den (idf-express-skip)/(idf-light-skip)-Marker.)
INLINE_ANCHORS = {
    "validator": [
        r"Schreibe\s+BERATER_OUTPUTS_IDF\.validator\s*=.*idf-express-skip",
    ],
    "itemContext": [
        r"Schreibe\s+BERATER_OUTPUTS_IDF\.itemContext\s*=.*idf-express-skip",
    ],
    "plBewertung": [
        # per_pl_evaluation = {the_item: { <KONSUMIERTE Pro-Item-Felder> }}  -> wir wollen die INNEREN Item-Felder
        r"Schreibe\s+DF_BATCH_STATE\.per_pl_evaluation\s*=.*idf-express",  # fallback marker via Logge unten
    ],
    "bottleneckTrigger": [
        r"Schreibe\s+DF_BATCH_STATE\.bottleneck_queue\s*=",
    ],
    "batchPlan": [
        r"Schreibe\s+DF_BATCH_STATE\.batch_items_per_batch\s*=\s*\{batch_1",
        r"Set\s+DF_BATCH_STATE\.current_sub_batch_id\s*=\s*\"batch_1\"",
        r"Set\s+DF_BATCH_STATE\.batch_items\s*=\s*\[the_item\]",
        r"Set\s+DF_BATCH_STATE\.k_score_aggregate\s*=\s*fm_k",
        r"Set\s+DF_BATCH_STATE\.batch_type\s*=\s*\"polish\"",
        r"Schreibe\s+BERATER_OUTPUTS_IDF\.batchPlan\s*=.*idf-express-skip",
    ],
    "stagePlanner": [
        r"Schreibe\s+DF_BATCH_STATE\.batch_stages\s*=\s*\{batch_1:\s*\[1\]\}",
        r"Schreibe\s+DF_BATCH_STATE\.stage_begruendung_per_batch\s*=.*idf-express-skip",
    ],
    "metricPlanner": [
        r"Schreibe\s+DF_BATCH_STATE\.metric_per_batch\s*=\s*\{batch_1:.*express_inline",
    ],
    "parallelSuitability": [
        r"Schreibe\s+DF_BATCH_STATE\.parallel_suitability\s*=.*idf-express-skip",
        r"Schreibe\s+BERATER_OUTPUTS\.parallelSuitability\s*=.*idf-express-skip",
    ],
    "finalSummary": [
        r"Schreibe\s+_manifest\.md\s+IDF_FINAL_SUMMARY\s*=.*idf-express-skip",
        r"Schreibe\s+BERATER_OUTPUTS_IDF\.finalSummary\s*=.*idf-express-skip",
    ],
}

# plBewertung: der Vertrag ist `per_pl_evaluation = {the_item: { <Item-Felder> }}`. Die KONSUMIERTEN
# Felder liegen im INNEREN Item-Objekt (k_score/srs/...). Darum eine Spezial-Extraktion fuer den
# inneren Block (zweites {...}).
def _extract_plBewertung_item_fields(orch: str) -> set:
    for line in orch.splitlines():
        if re.search(r"Schreibe\s+DF_BATCH_STATE\.per_pl_evaluation\s*=", line) and "the_item:" in line:
            inner_start = line.find("the_item:")
            inner = line[inner_start:]
            br = inner.find("{")
            if br >= 0:
                return _top_level_keys(inner[br:])
    return set()


# metricPlanner: der Vertrag ist `metric_per_batch = {batch_1: { <Batch-Metrik-Felder> }}`. KONSUMIERTE
# Felder liegen im inneren Batch-Objekt. Spezial-Extraktion des inneren {...}.
def _extract_metric_batch_fields(orch: str) -> set:
    for line in orch.splitlines():
        if re.search(r"Schreibe\s+DF_BATCH_STATE\.metric_per_batch\s*=", line) and "express_inline" in line:
            m = re.search(r"\{batch_1:\s*(\{.*)", line)
            if m:
                return _top_level_keys(m.group(1))
    return set()


# finalSummary: IDF_FINAL_SUMMARY hat Top-Level (recommended_next/aggregate/batches/...) UND je-Batch
# ein Vektor-Objekt (es_vector) mit modus_hint/k_score_avg/... . Beide Ebenen werden konsumiert.
def _extract_finalSummary_fields(orch: str) -> tuple[set, set, set]:
    top, vector, aggregate = set(), set(), set()
    for line in orch.splitlines():
        if re.search(r"Schreibe\s+_manifest\.md\s+IDF_FINAL_SUMMARY\s*=", line):
            top = _top_level_keys(line)
            mv = re.search(r"batches:\s*\[(\{.*?\})\]\s*,\s*aggregate", line, re.S)
            if mv:
                vector = _top_level_keys(mv.group(1))
            ma = re.search(r"aggregate:\s*(\{.*?\})\s*,\s*recommended_next", line, re.S)
            if ma:
                aggregate = _top_level_keys(ma.group(1))
        # es_vector wird auf eigener Zeile gebaut (sequence_pos/modus_hint/...)
        if re.search(r"es_vector\s*=\s*\{", line):
            vector |= _top_level_keys(line[line.find("{"):])
    return top, vector, aggregate


def inline_fields_for(berater: str, orch: str) -> set:
    if berater == "plBewertung":
        return _extract_plBewertung_item_fields(orch)
    if berater == "metricPlanner":
        return _extract_metric_batch_fields(orch)
    if berater == "finalSummary":
        top, vector, aggregate = _extract_finalSummary_fields(orch)
        # Flach zusammenfuehren: Top + Vektor + Aggregate sind alle downstream-konsumiert.
        return top | vector | aggregate
    return _extract_inline_fields(orch, INLINE_ANCHORS[berater])


# ════════════════════════════ KONSUMIERTE-FELDER-SET (mit Beleg) ════════════════════════════
# Pro Berater: {feld: "Consumer + Beleg"}. NUR Felder die ein LIVE-Reader tatsaechlich liest.
# (Felder ohne live Reader — z.B. stage_concurrency_per_batch=BL-230-Scheduler deferred — sind NICHT
#  drin: der Test prueft KONSUM, nicht Voll-Schema. Das ist AK-6 woertlich: "nur die gelesenen".)
CONSUMED = {
    "validator": {
        "actionable_pl_items": "IDF idf-light-Gate (_IDF_orchestrate Z716: actionable_count = ... ?? |validator.actionable_pl_items|)",
        "pruning_recommendation": "_IDF_berater_batchPlanner Z183 (BERATER_OUTPUTS.validator.pruning_recommendation == SKIP_DOWNSTREAM)",
    },
    "itemContext": {
        # BL-405 (INV-MODUS-1-Bereinigung): itemContext liefert KEIN Modus-Override-Feld mehr.
        # Der frueher hier konsumierte Override (C3 single-item LEGACY) wurde aus C3 geschnitten —
        # C3 entscheidet den Modus jetzt ALLEIN aus k-score/srs/coverage. itemContext hat damit
        # KEIN downstream-konsumiertes Feld mehr ausser den Struktur-Feldern (items_total/blocked),
        # die kein Consumer als Modus-Eingang liest. Consumed-Set absichtlich leer.
    },
    "plBewertung": {  # innere per_pl_evaluation[item]-Felder
        "k_score": "C3 Z302 pl_k_score_avg-Override + IDF batchPlan Z783 + metricPlanner Z850 (per_pl_evaluation[item].k_score)",
        "srs": "_IDF_berater_bottleneckTrigger (liest per_pl_evaluation[item].srs) + finalSummary",
        "bottleneck": "_IDF_berater_bottleneckTrigger (per_pl_evaluation[item].bottleneck -> queue)",
        "intern": "_IDF_berater_bottleneckTrigger (intern -> SC/WP-Queue-Routing)",
        "ak": "_IDF_berater_finalSummary / plBewertung-Consumer (per_pl_evaluation[item].ak)",
    },
    "bottleneckTrigger": {
        "queue_for_sc": "C3 _SDF_berater_modusEntscheidung SCHRITT 2.5 (Bottleneck-Queue-Check) + finalSummary",
        "queue_for_wp": "C3 SCHRITT 2.5 (WP-Queue) + finalSummary",
    },
    "batchPlan": {
        # batchPlan verteilt seinen Vertrag auf DF_BATCH_STATE-Skalare + BERATER_OUTPUTS_IDF.batchPlan.
        "batch_items_per_batch": "SDF-Outer-Loop _SDF_orchestrate Z451/480/575 + C3 Z788/813 (Iteration der Sub-Batches)",
        "current_sub_batch_id": "SDF-Outer-Loop Z481/575 + C3 Z917 (metric_per_batch[current_sub_batch_id])",
        "batch_items": "SDF Single-Mode Z480/913 + C3 Z988 (DF_BATCH_STATE.batch_items[])",
        "k_score_aggregate": "C3 Z781/992 (k_score_aggregate Vorrang vor A_PIPELINE_STATE.k_score)",
        "batch_type": "C3 Z781 (batch_type)",
        "escalation_hint": "C3 Z781 (escalation_hint)",
    },
    "stagePlanner": {
        "batch_stages": "SDF-Outer-Loop _SDF_orchestrate Z537 + C3 Z374 (batch_stages[current_sub_batch_id]) + finalSummary Z1028",
    },
    "metricPlanner": {  # innere metric_per_batch[batch]-Felder
        "srs_max": "C3 Z287 (srs = batch_metric.srs_max, BL-172 INV-METRIC-2)",
        "k_score_avg": "C3 Z288 (k_score = batch_metric.k_score_avg)",
        "k_score_max": "C3 Z289/459/845 (k_score_max — TDD/Split-Decision)",
        "special_flags": "C3 Z301/839/466 (story_fallback_k_score / normalization_artifact IN special_flags)",
        "pl_k_score_avg": "C3 Z302 (BL-402 single-item Override: pl_k_score_avg)",
        "w_status_set": "C3 Z599 (batch_w_status_set = metric_per_batch[..].w_status_set; experiment_provable-Trigger)",
        "gap_status": "C3 Z615/734/811 (gap_status_dominant ?? gap_status -> Greenfield/M3-Boost)",
        "srs_source": "C3 Z634 (srs_source-Provenance)",
        "pl_bottleneck_ct": "_IDF_berater_finalSummary / recalibrate (pl_bottleneck_ct)",
    },
    "parallelSuitability": {
        "recommended_N": "BL-230 Wellen-Scheduler (parallel_suitability.recommended_N) + BERATER_OUTPUTS.parallelSuitability",
        "suitable": "BL-230 Scheduler (INV-PARALLEL-3: suitable = recommended_N>=2)",
        "conflict_islands": "BL-230 Scheduler (conflict_islands)",
        "format_version": "Schema-Vertrag (format_version Pflicht im parallel_suitability-Block)",
    },
    "finalSummary": {
        "recommended_next": "SDF-Post stale-handoff-recovery (IDF_FINAL_SUMMARY.recommended_next) + Operator",
        "batches": "SDF stale-handoff Z461 (IDF_FINAL_SUMMARY.batches -> batch_items_per_batch self-heal)",
        "aggregate": "PostBatch recalibrate (IDF_FINAL_SUMMARY.aggregate globale Metriken)",
        "modus_hint": "SDF Phase 1.1 modus_hint-Kontext (batches[*].modus_hint, INV-MODUS-1)",
        "stages": "SDF stale-handoff Z476 (batches[*].stages -> batch_stages self-heal)",
        "inv_modus_1_disclaimer": "INV-DISCLAIMER-1 PFLICHT (finalSummary-Vertrag)",
    },
}

# KEEP-Berater (AK-4): laufen IMMER REAL, duerfen NIE inline-gefaket werden.
KEEP_BERATER = {"modelSync", "testSearch"}
# Alle 9 Skip-Berater (AK-3-Matrix).
SKIP_BERATER = {"validator", "itemContext", "plBewertung", "bottleneckTrigger", "batchPlan",
                "stagePlanner", "metricPlanner", "parallelSuitability", "finalSummary"}


def compute_gaps(orch: str) -> dict:
    """Pro Berater: konsumierte Felder, die im Inline-Vertrag FEHLEN."""
    gaps = {}
    for berater, consumed in CONSUMED.items():
        inline = inline_fields_for(berater, orch)
        missing = {f: why for f, why in consumed.items() if f not in inline}
        if missing:
            gaps[berater] = {"missing": missing, "inline_has": sorted(inline)}
    return gaps


# ════════════════════════════ TESTS ════════════════════════════

def test_orchestrator_parsable():
    """Sanity: Orchestrator existiert und die 9 Inline-Vertraege sind ueberhaupt parsebar (nicht-leer)."""
    orch = _read_orch()
    for berater in SKIP_BERATER:
        fields = inline_fields_for(berater, orch)
        assert fields, (f"Inline-Vertrag fuer '{berater}' nicht gefunden/leer geparst — "
                        f"Anker in INLINE_ANCHORS stimmt nicht mehr mit _IDF_orchestrate.md ueberein.")


def test_express_inline_contracts_carry_consumed_fields():
    """KERN (AK-6): jeder Express-Inline-Vertrag ⊇ die downstream-KONSUMIERTEN Felder.

    Fehlt ein konsumiertes Feld -> FAIL mit Berater+Feld+Consumer-Beleg. Das faengt die 2a-ii-
    Schema-Luecken (z.B. metricPlanner.w_status_set/gap_status). NICHT abschwaechen.
    (BL-405: itemContext.forced-mode-Override-Feld wurde aus der Engine geschnitten — INV-MODUS-1.)
    """
    orch = _read_orch()
    gaps = compute_gaps(orch)
    if gaps:
        lines = ["Schema-Luecken (konsumiertes Feld FEHLT im Inline-Vertrag):"]
        for berater, info in sorted(gaps.items()):
            for field, why in sorted(info["missing"].items()):
                lines.append(f"  - {berater}.{field}  <- gelesen von: {why}")
            lines.append(f"      inline traegt aktuell: {info['inline_has']}")
        assert False, "\n".join(lines)


def test_keep_berater_not_skipped():
    """AK-4: modelSync (3.7) + testSearch (7.7) werden NIE inline-gefaket — kein (idf-express-skip)-Marker
    auf ihren Slots, und sie sind nicht in der Skip-Liste."""
    orch = _read_orch()
    for keep in KEEP_BERATER:
        # Es darf KEINEN BERATER_OUTPUTS(_IDF).{keep} = {...idf-express-skip...} Schreib-Vertrag geben.
        bad = re.search(rf"Schreibe\s+BERATER_OUTPUTS(_IDF)?\.{keep}\s*=.*idf-express-skip", orch)
        assert bad is None, f"KEEP-Berater '{keep}' hat einen idf-express-skip Inline-Vertrag — AK-4 verletzt!"
        assert keep not in SKIP_BERATER, f"KEEP-Berater '{keep}' steht faelschlich in SKIP_BERATER."
    # Positiv-Gegenprobe: 3.7 modelSync + 7.7 testSearch werden im EXPRESS-Pfad WEITER per Skill() gespawnt.
    assert re.search(r"Skill\(_IDF_berater_modelSync", orch), "modelSync-Spawn fehlt (KEEP muss real laufen)"
    assert re.search(r"Skill\(_IDF_berater_testSearch", orch), "testSearch-Spawn fehlt (KEEP muss real laufen)"
    # Und es gibt KEINEN express-Branch, der den modelSync/testSearch-Spawn ueberspringt.
    assert not re.search(r"IF\s+express_(provisional|gate).*\n[^\n]*modelSync", orch), \
        "Es existiert ein express-Branch der modelSync ueberspringt — AK-4 verletzt."


def test_keep_berater_run_before_gate():
    """AK-2/AK-4: testSearch (7.7) liegt VOR dem POST-7.7 TIER-2-Confirm-Gate; modelSync (3.7) ebenfalls
    davor. Beide liefern die Bestaetigungs-Daten (c5 covered / c6 harvest leer) — sie KOENNEN nicht
    inline sein, weil das Gate auf ihren Echt-Output wartet (Chicken-Egg)."""
    orch = _read_orch()
    pos_modelsync = orch.find("Skill(_IDF_berater_modelSync")
    pos_testsearch = orch.find("Skill(_IDF_berater_testSearch")
    pos_gate = orch.find("IDF-EXPRESS-LANE-GATE")  # POST-7.7 TIER-2 Confirm
    assert 0 < pos_modelsync < pos_gate, "modelSync-Spawn muss VOR dem TIER-2-Gate stehen (AK-2)."
    assert 0 < pos_testsearch < pos_gate, "testSearch-Spawn muss VOR dem TIER-2-Gate stehen (AK-2)."


def test_default_off_no_express():
    """AK-7/AK-8: idf_express_lane default=false; der GANZE Express-Pfad ist nur unter
    `IF idf_express_lane == true` erreichbar. Bei false bleibt express_provisional/express_gate
    auf dem Regression-Schutz-Default -> ELSE-Zweig spawnt JEDEN Berater normal."""
    orch = _read_orch()
    # Default-OFF Literal (BL-403 batch_3/AK-7: resolver-aware Quelle, weiterhin default-OFF).
    # Praezedenz: args.idf_express_lane ?? session_params_resolver(idf_express_lane) ?? false.
    # Der `?? false`-Schwanz bleibt der harte default-OFF-Garant (fehlt der Param ueberall -> false).
    assert re.search(
        r"idf_express_lane\s*=\s*\(args\.idf_express_lane\s*\?\?\s*"
        r"session_params_resolver\(idf_express_lane\)\s*\?\?\s*false\)",
        orch,
    ), "Default-OFF resolver-aware Quelle (args.idf_express_lane ?? session_params_resolver(idf_express_lane) ?? false) nicht gefunden."
    # express_provisional Start = false
    assert re.search(r"express_provisional\s*=\s*false", orch), "express_provisional-Default=false fehlt."
    # express_gate Start = "FULL"
    assert re.search(r'express_gate\s*=\s*"FULL"', orch), "express_gate-Default=FULL fehlt."
    # TIER-1: provisional nur unter IF idf_express_lane == true
    assert re.search(r"IF\s+idf_express_lane\s*==\s*true:", orch), "TIER-1-Guard (IF idf_express_lane==true) fehlt."
    # Jeder Inline-Vertrag haengt an `IF express_provisional == true` ODER `IF express_gate == \"EXPRESS\"`.
    for berater in SKIP_BERATER:
        for rx in (INLINE_ANCHORS.get(berater) or []):
            for ln_no, line in enumerate(orch.splitlines()):
                if re.search(rx, line):
                    # Suche rueckwaerts den naechsten umschliessenden IF-Guard.
                    ctx = "\n".join(orch.splitlines()[max(0, ln_no - 25):ln_no + 1])
                    assert ("express_provisional == true" in ctx) or ('express_gate == "EXPRESS"' in ctx), \
                        f"Inline-Vertrag '{berater}' nicht unter express-Guard (AK-8 Regression-Risiko): {line.strip()[:90]}"
                    break


def test_every_skip_berater_has_else_spawn():
    """AK-8: zu JEDEM Inline-Vertrag (Pre-7.7) gibt es einen ELSE-Zweig mit echtem Skill()-Spawn,
    damit default-OFF byte-identisch zum Status quo bleibt. (Pre-7.7-Berater 3.5..7.6.)"""
    orch = _read_orch()
    pre77 = {
        "validator": r"Skill\(_IDF_berater_validator",
        "itemContext": r"Skill\(_IDF_berater_itemContext",
        "plBewertung": r"Skill\(_IDF_berater_plBewertung",
        "bottleneckTrigger": r"Skill\(_IDF_berater_bottleneckTrigger",
        "batchPlan": r"Skill\(_IDF_berater_batchPlan",
        "stagePlanner": r"Skill\(_IDF_berater_stagePlanner",
        "metricPlanner": r"Skill\(_IDF_berater_metricPlanner",
    }
    for berater, rx in pre77.items():
        assert re.search(rx, orch), f"ELSE-Spawn Skill() fuer Pre-7.7-Berater '{berater}' fehlt (AK-8)."
    # Post-7.7 (7.8/8.0) ebenso ELSE-Spawn.
    assert re.search(r"Skill\(_IDF_berater_parallelSuitability", orch), "ELSE-Spawn parallelSuitability fehlt (AK-8)."
    assert re.search(r"Skill\(_IDF_berater_finalSummary", orch), "ELSE-Spawn finalSummary fehlt (AK-8)."


def _resolver():
    """Lazy-Import des session_params_resolver (cwd-robust: pytest collected aus Repo-Root,
    der Resolver liegt in .claude/scripts). Analog _geist5() in test_idf_light.py."""
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    import session_params_resolver as spr
    return spr


def _under_dial_guard(lines: list, idx: int) -> bool:
    """Strukturell (indent-basiert, edit-resistent statt fixe Fenstergroesse): ist die Zeile
    `lines[idx]` transitiv von einem `IF idf_express_lane == true:`-Block umschlossen?

    Walk rueckwaerts: fuer jede tiefere/gleich-eingerueckte vorausgehende Control-Zeile
    suchen wir die naechste STRENG geringer eingerueckte Zeile (= umschliessender Block-Header).
    Ist EINER der so durchlaufenen Block-Header `IF idf_express_lane == true:`, ist die Zeile
    unter dem Dial-Guard. Ein `ELSE:`/`ELSE IF` auf dem Dial-Indent, das einen Nicht-Dial-Zweig
    oeffnet, wuerde die Kette unterbrechen (return False)."""
    def indent(s: str) -> int:
        return len(s) - len(s.lstrip(" "))
    cur_indent = indent(lines[idx])
    j = idx - 1
    target = cur_indent
    while j >= 0:
        ln = lines[j]
        if ln.strip() == "" or not ln.strip():
            j -= 1
            continue
        ind = indent(ln)
        if ind < target:
            header = ln.strip()
            if header.startswith("IF idf_express_lane == true:"):
                return True
            # Ein umschliessender ELSE/ELSE-IF auf diesem Level oeffnet einen Nicht-Dial-Zweig
            # -> die Aktivierung haengt NICHT (nur) am Dial-true-Guard.
            if header.startswith("ELSE"):
                return False
            # weiter nach aussen (anderer IF/FOR/...): naechst-geringeren Indent suchen
            target = ind
        j -= 1
    return False


def test_default_off_equals_status_quo(tmp_path):
    """AK-8 (DEDIZIERT): default-OFF == Status-quo-Sequenz. Drei strukturelle Garantien
    in einem Test (Caller-Assertion batch_3-L2: bei idf_express_lane=false ist KEIN Express-
    Pfad erreichbar -> volle Berater-Spawn-Sequenz 3.5..8.0 identisch zum Status quo):

      (a) JEDER der 9 Skip-Berater (7 Pre-7.7 + 7.8 + 8.0) hat einen ELSE-Spawn-Zweig
          (kein Skip bei default-OFF) — die volle Sequenz bleibt intakt.
      (b) JEDE Express-Aktivierung (express_provisional/express_gate=EXPRESS) haengt
          STRUKTURELL an `idf_express_lane == true` — es gibt KEINEN anderen Aktivierungs-Pfad.
      (c) Der Resolver liefert idf_express_lane DEFAULT false (Framework-Stufe, ohne Override).
    """
    orch = _read_orch()

    # ── (a) Vollstaendige ELSE-Spawn-Abdeckung: alle 9 Skip-Berater spawnen real ──────────────
    # (test_every_skip_berater_has_else_spawn deckt (a) teils ab; hier explizit ALLE 9, damit
    #  "volle Sequenz 3.5..8.0 == Status quo" als eine Assertion festgehalten ist.)
    all_skip_spawns = {
        "validator":           r"Skill\(_IDF_berater_validator",
        "itemContext":         r"Skill\(_IDF_berater_itemContext",
        "plBewertung":         r"Skill\(_IDF_berater_plBewertung",
        "bottleneckTrigger":   r"Skill\(_IDF_berater_bottleneckTrigger",
        "batchPlan":           r"Skill\(_IDF_berater_batchPlan",
        "stagePlanner":        r"Skill\(_IDF_berater_stagePlanner",
        "metricPlanner":       r"Skill\(_IDF_berater_metricPlanner",
        "parallelSuitability": r"Skill\(_IDF_berater_parallelSuitability",
        "finalSummary":        r"Skill\(_IDF_berater_finalSummary",
    }
    for berater, rx in all_skip_spawns.items():
        assert re.search(rx, orch), (
            f"AK-8: ELSE-Spawn Skill() fuer Skip-Berater '{berater}' fehlt — "
            f"default-OFF wuerde NICHT die volle Status-quo-Sequenz spawnen."
        )

    # ── (b) Express-Aktivierung haengt STRUKTURELL an idf_express_lane == true ─────────────────
    # express_provisional wird NUR unter `IF idf_express_lane == true:` auf true gesetzt;
    # ausserhalb dieses Guards gibt es KEINE `express_provisional = true`-Zuweisung.
    lines = orch.splitlines()
    provisional_true_idx = [
        i for i, ln in enumerate(lines) if re.search(r"express_provisional\s*=\s*true", ln)
    ]
    assert provisional_true_idx, "express_provisional=true-Zuweisung nicht gefunden (Gate fehlt)."
    for i in provisional_true_idx:
        assert _under_dial_guard(lines, i), (
            f"AK-8(b): 'express_provisional = true' NICHT transitiv unter "
            f"`IF idf_express_lane == true` -> alternativer Aktivierungs-Pfad! Zeile: {lines[i].strip()[:90]}"
        )
    # express_gate=="EXPRESS" wird ebenfalls NUR unter dem idf_express_lane==true-Guard gesetzt.
    express_set_idx = [
        i for i, ln in enumerate(lines) if re.search(r'express_gate\s*=\s*"EXPRESS"', ln)
    ]
    assert express_set_idx, "express_gate=EXPRESS-Zuweisung nicht gefunden (TIER-2-Gate fehlt)."
    for i in express_set_idx:
        assert _under_dial_guard(lines, i), (
            f"AK-8(b): 'express_gate = \"EXPRESS\"' NICHT transitiv unter "
            f"`IF idf_express_lane == true` -> alternativer Aktivierungs-Pfad! Zeile: {lines[i].strip()[:90]}"
        )
    # Default-Start beider Flags ist der Regression-Schutz (false / FULL).
    assert re.search(r"express_provisional\s*=\s*false", orch), "express_provisional-Default=false fehlt (AK-8)."
    assert re.search(r'express_gate\s*=\s*"FULL"', orch), "express_gate-Default=FULL fehlt (AK-8)."

    # ── (c) Resolver liefert idf_express_lane DEFAULT false (Framework-Stufe, ohne Override) ───
    spr = _resolver()
    # Registrierung + Framework-Default
    assert "idf_express_lane" in spr.FRAMEWORK_DEFAULTS, "idf_express_lane fehlt in FRAMEWORK_DEFAULTS (AK-7)."
    assert spr.FRAMEWORK_DEFAULTS["idf_express_lane"]["value"] is False, \
        "idf_express_lane Framework-Default muss False sein (AK-7 default-OFF)."
    # Resolve ohne jeden Override (leerer Vault, kein BL-File) -> Framework-Stufe = False.
    empty_vault = tmp_path / "vault"
    empty_vault.mkdir()
    resolved = spr.resolve_param("idf_express_lane", bl_id=None, vault_root=str(empty_vault))
    assert resolved is False, (
        f"AK-7/AK-8: resolve_param('idf_express_lane') muss ohne Override False liefern "
        f"(default-OFF), erhalten: {resolved!r}."
    )
    # Coercion + Validierung (bool-like, analog motor_production_ready/parallel_mode).
    assert spr._coerce_value("idf_express_lane", "false") is False
    assert spr._coerce_value("idf_express_lane", "true") is True
    assert spr.validate_param("idf_express_lane", "false") is False
    assert spr.validate_param("idf_express_lane", "true") is True


def test_no_modus_write_in_inline_contracts():
    """INV-MODUS-1: kein Inline-Vertrag schreibt DF_BATCH_STATE.batch_modes oder modus (nur C3 darf).
    batch_mode_hints (ADVISORY) ist erlaubt."""
    orch = _read_orch()
    for line in orch.splitlines():
        if "idf-express-skip" in line or ("express_inline" in line):
            assert not re.search(r"\bbatch_modes\b", line), f"INV-MODUS-1: Inline-Vertrag schreibt batch_modes: {line.strip()[:90]}"
            assert not re.search(r"Set\s+DF_BATCH_STATE\.modus\b", line), f"INV-MODUS-1: Inline-Vertrag schreibt modus: {line.strip()[:90]}"


def test_no_haiku_in_express_path():
    """AK-12 (BL-403, feedback_haiku_verboten): im Express-Lane-Bereich von _IDF_orchestrate.md
    (TIER-1 Vorab-Gate + TIER-2 Confirm-Gate + KEEP-Berater-Spawns 3.7/7.7) darf KEIN
    Spawn mit model=haiku, general-haiku oder tier=haiku vorkommen.

    Der Express-Pfad einfuehrt KEINE haiku-Spawns: KEEP-Berater (modelSync/testSearch) laufen mit
    Spawn-Floor sonnet (Tier-Tabelle middle=sonnet, Status quo). Inline-Vertraege brauchen
    keinen Worker. 0 haiku-Treffer im Express-Bereich = PASS.
    """
    orch = _read_orch()
    # Express-Bereich: alles zwischen TIER-1-Vorab-Gate-Anker und Phase 7.8 (PARALLEL_SUITABILITY).
    # Ankerpunkte (textuell eindeutig):
    tier1_anchor = "IDF-EXPRESS-VORAB-GATE (TIER-1"
    end_anchor   = "Phase 7.8: PARALLEL_SUITABILITY"
    start_idx = orch.find(tier1_anchor)
    end_idx   = orch.find(end_anchor)
    assert start_idx > 0, f"TIER-1-Anker '{tier1_anchor}' nicht gefunden — Orchestrator-Struktur geaendert?"
    assert end_idx   > 0, f"End-Anker '{end_anchor}' nicht gefunden — Orchestrator-Struktur geaendert?"
    assert start_idx < end_idx, "TIER-1-Anker liegt nach End-Anker — unerwartete Reihenfolge."
    express_region = orch[start_idx:end_idx]

    # Nur nicht-Kommentar-Zeilen pruefen (Zeilen die mit '#' beginnen sind Doku-Kommentare
    # und duerfen 'haiku' als negatives Beispiel nennen — das ist der Scope-Cut-Kommentar AK-12).
    # Wir pruefen NUR Code-Zeilen (keine fuehrenden '#'-Zeilen) auf haiku-Spawn-Signaturen.
    code_lines = [ln for ln in express_region.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    code_only = "\n".join(code_lines)

    # Haiku-Spawn-Signaturen in Code-Zeilen (case-insensitive).
    haiku_patterns = [
        r"\bmodel\s*=\s*['\"]?haiku",
        r"\bgeneral-haiku\b",
        r"\btier\s*=\s*['\"]?haiku",
    ]
    hits = []
    for pat in haiku_patterns:
        for m in re.finditer(pat, code_only, re.IGNORECASE):
            line_no = code_only[:m.start()].count("\n") + 1
            hits.append(f"  haiku-Match '{m.group()}' (Pattern: {pat}) an Code-Zeile {line_no}: "
                        f"...{code_only[max(0,m.start()-40):m.end()+40].strip()[:100]}...")
    assert not hits, (
        "AK-12 FAIL: haiku-Spawn-Referenzen im Express-Lane-Code-Bereich gefunden "
        "(Spawn-Floor sonnet verletzt — feedback_haiku_verboten):\n" + "\n".join(hits)
    )


# ════════════════════════════ REPORT-MAIN ════════════════════════════
if __name__ == "__main__":
    orch = _read_orch()
    print("=== IDF-Express-Lane Reader-Konformitaet (inline-Vertrag >= konsumierte Felder) ===\n")
    gaps = compute_gaps(orch)
    for berater in sorted(SKIP_BERATER):
        inline = inline_fields_for(berater, orch)
        consumed = set(CONSUMED.get(berater, {}))
        missing = consumed - inline
        flag = "OK  " if not missing else "GAP "
        print(f"[{flag}] {berater:20s} inline={len(inline):2d} consumed={len(consumed):2d}"
              + (f"  FEHLT: {sorted(missing)}" if missing else ""))
    print()
    if gaps:
        print("--- SCHEMA-LUECKEN (Test-FAIL-Treiber, Input fuer Inline-Vertrag-Fix) ---")
        for berater, info in sorted(gaps.items()):
            for field, why in sorted(info["missing"].items()):
                print(f"  {berater}.{field}\n      gelesen von: {why}")
    else:
        print("Keine Luecken — alle konsumierten Felder werden inline getragen.")
    print(f"\nKEEP (immer real): {sorted(KEEP_BERATER)}")
