# MODE-RECOMMENDATION Algorithmus (v3.1)

Referenz fuer `/_A_orchestrate` Phase 4.2 (Nach letztem Task — Gap-Analyse).

**v3.1 (BL-017 RF-12):** META-Commands Sonderbehandlung (AK-12-05) hinzugefuegt.
META + MEDIUM + NIEDRIG SRS → SC-FULL (nicht I-STANDALONE). Begruendung: hohe Kopplung bei
Command-Aenderungen (F028), Kaskadeneffekte. GAP_PERCENT explizit NICHT entscheidungsrelevant (AK-12-01).

## Inputs und Definitionen

```
# WICHTIG: GAP_PERCENT ist nach A-Pipeline IMMER ~100% (nichts implementiert).
# GAP wird NUR informativ angezeigt, NICHT fuer die Entscheidung verwendet.
# Stattdessen: 2D-Matrix (COMPLEXITY x SRS_RANGE).

SPEC_EXISTS     = Spec-Datei vorhanden UND nicht leer
MODEL_EXISTS    = Model-Datei vorhanden UND nicht leer

COMPLEXITY      = Primaer aus K-Score (wenn /_K_score gelaufen ist):
  k_score = A_PIPELINE_STATE.k_score  # Numerisch 0-100 (aus /_K_score)
  IF k_score vorhanden:
    LOW:    k_score in [0, 33]    # Geringe Komplexitaet
    MEDIUM: k_score in (33, 66]   # Moderate Komplexitaet
    HIGH:   k_score in (66, 100]  # Hohe Komplexitaet
  ELSE:
    # FALLBACK: Label aus Spec-Metriken (Legacy, wenn K-Score nicht verfuegbar)
    LOW:    <= 3 RFs, <= 5 ACs, <= 2 Epics
    MEDIUM: 4-8 RFs, 6-15 ACs, 3-5 Epics
    HIGH:   > 8 RFs, > 15 ACs, > 5 Epics

# KONSISTENZ (RF-AM-010): COMPLEXITY-Stufen korrespondieren mit 2D-Matrix-Zeilen
# (Q1-Q3=LOW, Q4-Q6=MEDIUM, Q7-Q9=HIGH).
# SRS-Schwellen der 2D-Matrix (20/60/85) sind identisch zu _SC_qualityGate.md Gate-6.
# Diese Werte duerfen NUR synchron geaendert werden (Konsistenz-Constraint AK-S2).

MODEL_MATURITY  = Aus Model-Frontmatter (w_confirmed / w_total):
  HIGH:   >= 70% BESTAETIGT
  MEDIUM: 40-70% BESTAETIGT
  LOW:    < 40% BESTAETIGT (oder Model fehlt)

RF_COUNT        = Anzahl Requirements aus Spec

# Informativ (wird angezeigt, NICHT fuer Entscheidung):
GAP_PERCENT     = Gap-Analyse Ergebnis (0-100%)

UNREIFE_TYP     = Aus A_PIPELINE_STATE.unreife_typ:
  # ab v2.0: kann auto-gesetzt sein durch Phase 4.1c Keyword-Scan
  # v2.0: Phase 4.1c setzt unreife_typ_kandidat im Model-Frontmatter
  # mode-recommendation liest A_PIPELINE_STATE.unreife_typ (gesetzt in Phase 4.3 nach User-Wahl)
  EXTERN:   Externes Wissen fehlt, kein Code/Test loest das Problem
  INTERN:   Typ-A-Unreife (Experimente, Code loest Problem)
  null:     nicht gesetzt (v1.0 Default — kein WP-Trigger in diesem Lauf)

FREIHEITSGRADE  = Aus A_PIPELINE_STATE.freiheitsgrade:
  true:  Mehrere valide Loesungswege existieren
  false: Eine klare Loesung (kein WP-Bedarf)
  null:  nicht gesetzt
```

## SRS-Berechnung (ad-hoc, VOR SC-Zyklus)

```
# Quellen: Spec-Frontmatter + Model-Frontmatter (w_open)
# D1 = offene Hypothesen (TBD/offen/ungeklaert in Spec, Gewicht 3)
# D2 = w_open aus Model-Frontmatter (Gewicht 1)
# D3 = fehlende Beispiele in Spec (Gewicht 0.5, default 0 wenn nicht lesbar)
# D4 = BLOCKING/ungeloeste Abhaengigkeiten in Spec (Gewicht 5)

IF SPEC_EXISTS AND MODEL_EXISTS:
  SRS = (D1*3) + (D2*1) + (D3*0.5) + (D4*5)
  SRS_AVAILABLE = true
  IF SRS < 20:
    SRS_RANGE = "NIEDRIG"
  ELIF SRS <= 60:
    SRS_RANGE = "AKTIV"
  ELSE:
    SRS_RANGE = "HOCH"
ELSE:
  SRS_AVAILABLE = false
```

## 2D-Matrix (COMPLEXITY x SRS_RANGE) — 9 Zellen

```
# WP-RESEARCH SONDERFALL — MUSS VOR ALLEN ANDEREN CHECKS STEHEN (ADR-1: M9 orthogonal zur Matrix)
# Begruendung: MODEL_MATURITY=LOW allein → Z.74 (SC-ANALYSE). 3-AND-Konjunktion ist SPEZIFISCHER.
# Ohne diese Position: Typ-B-Unreife wird faelschlich zu SC-ANALYSE geroutet (R5 HOCHRISIKO).
# v2.0: Phase 4.1c liefert unreife_typ_kandidat als Empfehlung (Keyword-Heuristik).
#   Automatischer Trigger (FREIHEITSGRADE) erst v2.5 — in v2.0 entscheidet User weiterhin.
IF MODEL_MATURITY == "LOW"
   AND UNREIFE_TYP == "EXTERN"
   AND FREIHEITSGRADE == true:
  RECOMMENDATION = "WP-RESEARCH"
  REASON = "Typ-B-Unreife: externes Wissen fehlt → Whitepaper recherchieren"
  SC_ARGS = ""
  I_ARGS = ""

# ═══ RF-12: META-COMMANDS SONDERBEHANDLUNG (AK-12-05) ═══
# OmniCommand-Kontext (META): Commands/Pipelines/Orchestratoren aendern.
# MEDIUM x NIEDRIG SRS → SC-FULL (nicht I-STANDALONE), weil META-Aenderungen
# hohe Kopplung haben (F028: "Kopplung extrem hoch") und Kaskadeneffekte auslösen.
# Erkennung: Model-Pfad enthaelt "OmniCommand" ODER Task.md referenziert .claude/commands/
IS_META_COMMAND = (
  ".claude/commands/" IN MODEL_PATH OR
  ".claude/commands/" IN TASK_MD_CONTENT OR
  "OmniCommand" IN NAME OR
  A_PIPELINE_STATE.is_meta_command == true
)

IF IS_META_COMMAND AND SRS_RANGE == "NIEDRIG" AND COMPLEXITY == "MEDIUM":
  RECOMMENDATION = "SC-FULL"
  REASON = "META-Command + MEDIUM Komplexitaet + niedrig SRS → SC-FULL (hohe Kopplung, Kaskadeneffekte, AK-12-05)"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor}"
  I_ARGS = ""
  Logge: "[MODE-REC] META-SONDERFALL: MEDIUM x NIEDRIG → SC-FULL (nicht I-STANDALONE, AK-12-05)"
# ═══ ENDE RF-12 META-SONDERFALL ═══

IF NOT SRS_AVAILABLE OR NOT SPEC_EXISTS OR NOT MODEL_EXISTS:
  RECOMMENDATION = "SC-ANALYSE"
  REASON = "Wissensbasis unvollstaendig (Spec oder Model fehlt) → Exploration noetig"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor} --mode=analyse"
  I_ARGS = ""

ELIF MODEL_MATURITY == "LOW":
  RECOMMENDATION = "SC-ANALYSE"
  REASON = "Model zu unklar (<40% bestaetigt) → Wissensbasis-Exploration noetig"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor} --mode=analyse"
  I_ARGS = ""

ELIF SRS_RANGE == "NIEDRIG" AND COMPLEXITY == "LOW":
  # Q1: Klein + klar verstanden
  RECOMMENDATION = "I-STANDALONE"
  REASON = "SRS niedrig + LOW Komplexitaet → direkte Implementierung, kein SC-Overhead"
  SC_ARGS = ""
  I_ARGS = "{NAME}"

ELIF SRS_RANGE == "NIEDRIG" AND COMPLEXITY == "MEDIUM":
  # Q2: Gut verstanden, nicht trivial — SC-FULL SYMBIOSE (RF-CS-010, W12)
  RECOMMENDATION = "SC-FULL SYMBIOSE"
  REASON = "SRS niedrig + MEDIUM Komplexitaet → SC-FULL SYMBIOSE: I-Phase als worker-mode eingebettet, kein zweiter separater Durchlauf noetig"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor}"
  I_ARGS = ""
  # SYMBIOSE: SC-Orchestrator ruft I-Pipeline via --worker-mode auf (kein eigenes Team, SC-Team wiederverwendet)

ELIF SRS_RANGE == "NIEDRIG" AND COMPLEXITY == "HIGH":
  # Q3: Gross, aber verstanden → Slicing empfohlen
  RECOMMENDATION = "SC-FULL"
  REASON = "SRS niedrig + HIGH Komplexitaet → SC-FULL wegen Umfang, Slicing empfohlen, kein TDD-Overhead"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor}"
  I_ARGS = ""
  Logge: "[MODE-REC] Q3: SC-FULL, Slicing empfohlen"

ELIF SRS_RANGE == "AKTIV" AND COMPLEXITY == "LOW":
  # Q4: Aktive Forschung, kleiner Umfang
  RECOMMENDATION = "SC-INLINE"
  REASON = "SRS aktiv + LOW Komplexitaet → SC-INLINE: Forschung ohne Volleinsatz"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor} -I"
  I_ARGS = ""

ELIF SRS_RANGE == "AKTIV" AND COMPLEXITY == "MEDIUM":
  # Q5: Aktive Forschung + mittlere Groesse
  RECOMMENDATION = "SC-FULL"
  REASON = "SRS aktiv + MEDIUM Komplexitaet → SC-FULL fuer Tiefe, noch kein TDD"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor}"
  I_ARGS = ""

ELIF SRS_RANGE == "AKTIV" AND COMPLEXITY == "HIGH":
  # Q6: Gross + aktive Forschung → Auto-TDD
  RECOMMENDATION = "SC-FULL"
  REASON = "SRS aktiv + HIGH Komplexitaet → SC-FULL + TDD gegen Regression waehrend Exploration"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor}"
  I_ARGS = ""
  AUTO_TDD_PENDING = true
  Logge: "[MODE-REC] Q6: SC-FULL + tdd=true wird nach ACCEPT gesetzt"

ELIF SRS_RANGE == "HOCH" AND COMPLEXITY == "LOW":
  # Q7: Klein, aber sehr unsicher
  RECOMMENDATION = "SC-ANALYSE"
  REASON = "SRS hoch + LOW Komplexitaet → Hypothesen-Klaerung vor Implementierung"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor} --mode=analyse"
  I_ARGS = ""

ELIF SRS_RANGE == "HOCH" AND COMPLEXITY == "MEDIUM":
  # Q8: Mittlere Groesse + hohe Unsicherheit
  RECOMMENDATION = "SC-FULL"
  REASON = "SRS hoch + MEDIUM Komplexitaet → SC-FULL + TDD als Sicherheitsnetz"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor}"
  I_ARGS = ""
  AUTO_TDD_PENDING = true
  Logge: "[MODE-REC] Q8: SC-FULL + tdd=true wird nach ACCEPT gesetzt"

ELIF SRS_RANGE == "HOCH" AND COMPLEXITY == "HIGH":
  # Q9: Groesstes Risikoprofil (vgl. DCSRE-98 SRS=115)
  RECOMMENDATION = "SC-FULL"
  REASON = "SRS hoch + HIGH Komplexitaet → maximales Risikoprofil, alles einsetzen"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor}"
  I_ARGS = ""
  AUTO_TDD_PENDING = true
  DIFFICULTY_HINT = "hard"
  Logge: "[MODE-REC] Q9: SC-FULL + tdd=true + difficulty=hard empfohlen"

ELSE:
  # Sonstiger Fallback (unerwartete Kombination)
  RECOMMENDATION = "SC-INLINE"
  REASON = "Unerwartete Kombination → SC-INLINE als sicherer Default"
  SC_ARGS = "{NAME} {difficulty} {ceiling} {floor} -I"
  I_ARGS = ""
```

## 2D-Matrix Kurzuebersicht

| SRS \ Complexity | LOW | MEDIUM | HIGH |
|-----------------|-----|--------|------|
| NIEDRIG (<20) | Q1: I-STANDALONE | Q2: SC-FULL SYMBIOSE | Q3: SC-FULL |
| AKTIV (20-60) | Q4: SC-INLINE | Q5: SC-FULL | Q6: SC-FULL+TDD |
| HOCH (>60) | Q7: SC-ANALYSE | Q8: SC-FULL+TDD | Q9: SC-FULL+TDD+hard |

**Sonderfaelle (VOR Matrix, Reihenfolge = Prioritaet):**
- META-Command + MEDIUM + NIEDRIG SRS → SC-FULL (AK-12-05, RF-12, v3.1)
- MODEL_MATURITY=LOW AND UNREIFE_TYP=EXTERN AND FREIHEITSGRADE=true → WP-RESEARCH
- Wissensbasis unvollstaendig → SC-ANALYSE
- MODEL_MATURITY=LOW (<40%) → SC-ANALYSE

**Primaere Signale (AK-12-02, RF-12):**
- Complexity (aus K-Score oder Spec-Metriken)
- Model Maturity (W{n}-Status, BESTAETIGT vs OFFEN)
- Offene Fragen (SRS-Berechnung: D1, D2, D3, D4)
- NICHT: GAP_PERCENT (AK-12-01 — nach A-Pipeline IMMER ~100%, nur informativ)

## COMPLEXITY_STATE initialisieren (nach MODE-RECOMMENDATION)

```
Manifest-Write (COMPLEXITY_STATE):
  complexity_current: {COMPLEXITY}          # LOW/MEDIUM/HIGH aus Phase 4.2
  complexity_prev: null                     # erster Lauf, kein Vorgaenger
  complexity_trend: STABLE                  # W23-Fix: INITIAL ist kein gueltiger Enum-Wert
  complexity_switch_recommendation: NONE    # kein Wechsel empfohlen
  complexity_changed_at_cycle: 0            # noch kein Checkpoint durchlaufen
  complexity_auto_tdd_activated: {AUTO_TDD_PENDING == true}  # true wenn HIGH Complexity (CF-12)
  complexity_auto_tdd_pending: false        # W22 Zwei-Schritt-Pattern: pending bis Checkpoint

Logge: "[COMPLEXITY_STATE] Initialisiert: {COMPLEXITY}, trend=STABLE"
```

## SC-FULL SYMBIOSE Definition (RF-CS-010, W12)

```
# SYMBIOSE = SC-Zyklus + I-Pipeline in einem Durchlauf.
# SC-Orchestrator ruft I-Pipeline via --worker-mode auf (kein eigenes Team, SC-Team wiederverwendet).
# I-Pipeline laeuft als scope_mode=core (Schritte 0-8, kein Pre-PR, kein Push).
# Nach I-Pipeline-Completion: SC POST-CYCLE (model maintain + gap + push_global).
#
# Wann SC-FULL SYMBIOSE waehlen:
#   - Q2: SRS niedrig + MEDIUM Komplexitaet → direkte Implementierung sinnvoll, aber SC-Kontext noetig
#   - Unterschied zu SC-FULL: SYMBIOSE spart separaten I-Aufruf (I laeuft direkt im SC-Kontext)
#   - Unterschied zu SC-INLINE: FULL statt INLINE → Blueprint + Architect + Slicing aktiv
#
# Pipeline-Aufruf (SC-Orchestrator nach ERGEBNIS-Phase):
#   Skill(skill="_I_orchestrate", args="{NAME} --worker-mode")
#   pipeline_mode = "SC_SYMBIOSE_I_ACTIVE" (in Manifest vor dem Aufruf setzen)
```
