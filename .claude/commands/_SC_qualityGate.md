---
type: building-block
depends_on:
  - _SC_modelMaintain
feeds_into:
  - _SC_hypothese
related:
  - _SC_ergebnis
---

# /_SC_qualityGate

**Status:** NEU v2.4 (QW-3 T6 + QW-4 absolute W{n}-Schwellenwert, ersetzt _analyse Sektion B Quality-Checks)
**Changelog:** v2.4 (2026-04-25): BL-142 Caller-Migration — complexity_* -> aggregat_*
**Actor:** QUALITY-GATE
**Zweck:** Quality Gates prüfen, BSD triggern

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_SC_qualityGate {NAME} [easy|normal|hard]                     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT (BL-050 Vault-First):                           ║
║    1. _manifest.md                                                       ║
║    2. {VAULT}/.../Model/{NAME}_Model.md (AKTUALISIERT von modelMaintain)║
║       FALLBACK: .claude/models/{NAME}_Model.md                          ║
║    3. synthese/{NAME}-OBSERVE{CYCLE}.md (Findings Kontext)              ║
║    4. synthese/{NAME}-ERGEBNIS*.md (falls Folge-Zyklus, SRS-Trend)      ║
║    5. {VAULT}/.../Model/{NAME}_Model-Topologie.md (falls Split aktiv)  ║
║       FALLBACK: .claude/models/{NAME}_Model-Topologie.md               ║
║    6. {VAULT}/.../Gap/{NAME}-GAP.md (falls vorhanden)                  ║
║       FALLBACK: .claude/analysis/synthese/{NAME}-GAP.md                ║
║       ◄── NEU v3.0: GAP% fuer Feature-Abschluss-Erkennung            ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║      PRIMAER: {VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-QUALITYGATE{CYCLE}.md ║
║      FALLBACK: .claude/analysis/synthese/{NAME}-QUALITYGATE{CYCLE}.md   ║
║      → Battle-Royale-Bewertung (SRS-Trend, Anti-Pattern)               ║
║      → Kohaesion-Check (W{n}/TC, Split-Trigger)                        ║
║      → Feature-Abschluss-Erkennung (v2.1)                               ║
║      → Blind-Spot-Trigger (T1-T6, optional)                             ║
║      → Stagnations-Bewertung (Schwellen, Massnahme)                    ║
║      → Gate 8: Spec-Eskalation (EP-2, EP-4, Z3: P3 RF-11..RF-15)     ║
║                                                                          ║
║  SCHREIBT (Output) - OPTIONAL:                                           ║
║    _parking-lot.md (APPEND, falls Incidental Findings)                  ║
║                                                                          ║
║  ACTOR: QUALITY-GATE                                                     ║
║    Prueft Quality-Gates: Feature-Abschluss, Kohaesion, BSD, Stagnation.║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **QUALITY-GATE** Actor hat eine einzige Verantwortung:

**Quality Gates prüfen und Eskalationen triggern**

Was der Quality-Gate **TUT**:
- ✅ Battle-Royale bewerten (SRS-Trend, Anti-Patterns R-AP1..R-AP5)
- ✅ Kohäsion prüfen (W{n}/TC, Split-Trigger)
- ✅ Feature-Abschluss erkennen (90%+ W{n} coverage)
- ✅ Blind-Spot-Detection triggern (T1-T5 Muster)
- ✅ T6 Quelle-Verifikation prüfen (W{n}-Quellen git-tracked?, W94)
- ✅ Stagnation bewerten (Schwellen, ABORT-Empfehlung)
- ✅ Eskalations-Hierarchie orchestrieren

Was der Quality-Gate **NICHT TUT**:
- ❌ Findings sammeln (→ _SC_observe)
- ❌ Model updaten (→ _SC_modelMaintain)
- ❌ Hypothesen aufstellen (→ _SC_hypothese)
- ❌ BSD selbst ausführen (→ _blindspotDetection)

---

## Chain-Position

```
OBSERVE{N} → MODEL-MAINTAIN → **QUALITYGATE{N}** → HYPOTHESEN
```

**Prev:** MODEL (nach _SC_modelMaintain Update)
**Next:** HYPOTHESEN

---

## Output-Format: QUALITYGATE{CYCLE}.md

```markdown
# Quality Gate: {NAME} (Cycle {N})

## Gate 1: Battle-Royale-Bewertung

### SRS-Score Entwicklung

| Zyklus | SRS | Δ | Trend | Bewertung |
|--------|-----|---|-------|-----------|
| 1 | 125.0 | - | - | Baseline |
| 2 | 98.5 | -26.5 | ↓ STARK | ✅ Fortschritt |
| 3 | 92.0 | -6.5 | ↓ SCHWACH | ⚠ Leichter Fortschritt |
| 4 | 91.5 | -0.5 | → STAGNATION | ❌ Kein Fortschritt |

**Bewertung:** {STARK|SCHWACH|KEINE}

**Anti-Pattern-Check:**
- R-AP1 (Wachsende Offene Bereiche): ❌ NICHT DETEKTIERT
- R-AP2 (Explodierende W{n} ohne Reduktion): ❌ NICHT DETEKTIERT
- R-AP3 (Stagnierender SRS): ⚠ WARN (4 Zyklen ohne starken Fortschritt)
- R-AP4 (Implodierendes Model): ❌ NICHT DETEKTIERT
- R-AP5 (Zyklischer Fokus ohne Abschluss): ❌ NICHT DETEKTIERT

**Empfehlung:** {Weitermachen | Battle-Royale intensivieren | Re-Expansion}

---

## Gate 2: Kohäsions-Check

### W{n} pro Technologie-Concern

| TC | W{n} Anzahl | Status | Split-Trigger |
|----|-------------|--------|---------------|
| Authentication | 18 | FOKUS | ⚠ >15 (PFLICHT-SPLIT) |
| Storage | 8 | OFFEN | ✅ OK |
| Logging | 4 | OFFEN | ✅ OK |

**Gesamt:** 30 W{n}

**Absoluter Schwellenwert (W95) — PFLICHT, IMMER prüfen (unabhängig von TC-Verteilung):**
- ✅ ≤ 50 W{n}: Normal
- ⚠ > 50 W{n}: WARN — Model-Split-Analyse empfohlen (TC-Verteilung prüfen, was treibt das Wachstum?)
- ❌ > 80 W{n}: FAIL — Model-Split PFLICHT (Feature zu gross fuer einen einzelnen Zyklus, Debloat PFLICHT)
- ⚠ 14+ neue W{n} in einem Zyklus: Themen-Explosion-Check (was treibt das Wachstum? ADR-Cooling prüfen!)

**Split-Trigger:**
- ✅ >15 W{n}/TC (Authentication)
- ⚠ >30 W{n} gesamt
- ❌ R-AP4 nicht aktiv

**Empfehlung:** Model-Split PFLICHT (bereits ausgeführt von _SC_modelMaintain)

---

## Gate 3: Feature-Abschluss-Erkennung (v2.2)

### W{n} Coverage pro Teilproblem

| Teilproblem | W{n} Coverage | Status |
|-------------|---------------|--------|
| User-Login | 95% | ✅ ABGESCHLOSSEN |
| Token-Refresh | 90% | ✅ ABGESCHLOSSEN |
| Role-Assignment | 60% | 🔄 IN ARBEIT |

### PL-BLOCKER (Einpflaster, 2026-04-20 — CaseStudy BL-125)

**Zweck:** Verhindert False-Positive "DONE" wenn offene Parking-Lot Items existieren.
Zukuenftige Vollausbau-Vision: `GAP = f(offene_PL_Items, K-Score-Gewichtung)`.
Einpflaster: nur VETO-Schicht, keine GAP-Neudefinition.

**Voraussetzung (IDF-Abhaengigkeit, BL-076):**
```
IF IDF_PIPELINE_STATE.ak_plan.status != "DONE":
  Logge: "[PL-BLOCKER] IDF noch nicht gelaufen — PL-VETO nicht anwendbar (pre-IDF)."
  pl_blocker = false
  pl_open_count_feature = null
  → SKIP PL-BLOCKER Check (nur W{n}-Coverage greift)
```

**Post-IDF-Logik:**
```
1. Lies {VAULT}/_parking-lot.md
2. Filtere offene Items fuer aktuelles Feature {NAME}:
   - Items mit "[ ]" Marker (NICHT [x], [~], [?], [!])
   - Items mit Feature-Tag ODER Feature-Name-Match (case-insensitive)
   - AUSSCHLIESSEN: Items mit [STATUS: IN_ARBEIT] ABER anderes Feature
3. Zaehle: pl_open_count_feature

IF pl_open_count_feature > 0:
  pl_blocker = true
  feature_status = "🔄 IN ARBEIT (PL-BLOCKER: {pl_open_count_feature} offene Items)"
  done_signal = false
  Logge: "[PL-BLOCKER] {pl_open_count_feature} offene PL-Items fuer {NAME} → Feature NICHT abgeschlossen."
ELSE:
  pl_blocker = false
  # Normales Gate-3-Ergebnis aus W{n}-Coverage greift unveraendert.
```

**Status-Regel (Einpflaster):**
- PL leer (oder pre-IDF) + W{n}-Coverage >= 90% → ABGESCHLOSSEN (wie bisher)
- PL nicht leer (post-IDF) → IN ARBEIT (unabhaengig von W{n}-Coverage!)
- Begruendung: Offene PL-Items = Vertragspflichten (Spec erweitert via IDF/SPEC-PROMOTE).
  Feature-DONE ohne PL-Check wuerde diese ignorieren → Pipeline faehrt fest.

**Manifest-Schreibung:**
```
Schreibe in QUALITYGATE{CYCLE}.md Frontmatter:
  pl_blocker: {true|false}
  pl_open_count_feature: {N|null}
  pl_blocker_skipped_reason: "{pre-IDF|null}"
```

### Zusammenfassung Gate 3

| Sub-Check | Ergebnis | Gewicht |
|-----------|----------|---------|
| W{n} Coverage Gesamt | {X}% | Primaer |
| PL-Blocker (post-IDF) | {true|false|SKIP} | **VETO wenn true** |

**Feature-Status:** {Berechnet aus W{n}-Coverage UND PL-Blocker}
  - pl_blocker=true → IMMER "🔄 IN ARBEIT" (PL-VETO schlaegt W{n}-Coverage)
  - pl_blocker=false → Status aus W{n}-Coverage
  - pl_blocker=SKIP (pre-IDF) → Status aus W{n}-Coverage (Legacy-Verhalten)

**Empfehlung:**
- pl_blocker=true → "Offene PL-Items abarbeiten (SDF/BDF), danach erneut pruefen"
- pl_blocker=false + Coverage < 90% → "1-2 weitere Zyklen bis Feature-Abschluss"
- pl_blocker=false + Coverage >= 90% → "Bereit fuer DONE-Entscheidung"

---

## Gate 4: Blind-Spot-Detection Trigger

### T1-T5 Muster-Check

| Muster | Detektiert? | Details |
|--------|-------------|---------|
| T1: Isolierter Fokus | ❌ | Cross-Cutting-Schutz aktiv |
| T2: Divergierende Teilmodelle | ❌ | Alle TCs konsistent |
| T3: Unerwartete Widerlegungen | ❌ | Keine Widerlegungen außerhalb Fokus |
| T4: Steigende Komplexität außerhalb Fokus | ⚠ | Storage-TC zeigt leichte Zunahme |
| T5: Systematische Vermeidung | ❌ | Keine Vermeidungsmuster |
| T6: Quelle-Verifikation | {❌ OK \| ⚠ WARN} | W{n} mit Code-Referenzen: alle git-tracked? Untracked → `[QUELLE-UNVERIFIZIERT]` |

**T6 Quelle-Verifikation (W94) — PFLICHT bei jeder W{n} mit Code-Referenzen:**
Fuer jede W{n} die konkrete Artefakte (Dateipfade, Klassen, Methoden) referenziert:
Sind diese Artefakte git-tracked (NICHT `??` in `git status`)? Falls untracked:
→ W{n} mit `[QUELLE-UNVERIFIZIERT]` markieren.
→ BSD-Warnung ausgeben.
→ ADR auf dieser W{n} VERBOTEN bis Quelle committed.
→ Zweite Sicherheitsstufe hinter G-UNTRACKED aus `_SC_observe` (Defense-in-Depth).

**T6-Schwere:** WARN (eine unverifizierte Quelle) | FAIL (mehrere unverifizierte Quellen oder ADR bereits geschrieben)

**Empfehlung:** ⚠ Canary Probe für Storage-TC (T4 leicht aktiv)

**BSD-Trigger:** T1-T5 OPTIONAL (nicht PFLICHT, aber empfohlen) | T6 PFLICHT wenn Untracked detektiert

---

## Gate 5: Stagnations-Bewertung

### Fortschritts-Zähler

**Aktueller Zähler:** 1.5
**Letzter starker Fortschritt:** Zyklus 2 (SRS -26.5)
**Letzter schwacher Fortschritt:** Zyklus 3 (SRS -6.5)

**Schwellen:**
- ✅ <3.0: Normal
- ⚠ ≥3.0: WARNUNG
- ❌ ≥5.0: PFLICHT-Maßnahme
- 🛑 ≥7.0: ABORT

**Bewertung:** ✅ Normal (1.5 < 3.0)

**Empfehlung:** Weitermachen

---

## Gate 6: Mode-Switch-Recommendation (W262/W250) — (Z4: RF-29, RF-30)

> **Hybrid-Architektur (W251, ADR-02):** qualityGate BERECHNET hier nur die Empfehlung und schreibt sie in QUALITYGATE{N}.md.
> _SC_orchestrate Phase 3.2 LIEST die Empfehlung und handelt (Auto-Switch oder HiL).
> qualityGate trifft KEINE Modus-Entscheidung selbst.

### Voraussetzung

```
IF cycle_nr < 2 AND NOT gate6_forced:
  → Gate 6 = SKIP (zu frueh, kein Trend-Vergleich moeglich)
  → mode_switch_recommendation = NONE
  → Konfidenz = none
  → LOG: "Gate 6: SKIP (Zyklus 1, kein Trend)"
  → STOPP (weiter mit Eskalations-Hierarchie)
```

### Idempotenz-Guard (RF-09, AK-M5)

```
# NE-1: sc_mode kann FULL (Z983) oder FULL_SYMBIOSE (Z984) sein
Lies Manifest: SC_PIPELINE_STATE.sc_mode → CURRENT_MODE
IF CURRENT_MODE IN ["FULL_SYMBIOSE", "FULL"]:
  mode_switch_recommendation = "NONE"
  Konfidenz = "none"
  LOG: "Gate-6: IDEMPOTENZ — sc_mode ist bereits {CURRENT_MODE}, kein Mode-Switch noetig"
  → SKIP (GOTO Gate-6-Ende)
```

### AGGREGAT ODER-Trigger (RF-08, eigenstaendig VOR SRS-Logik)

```
# AGGREGAT als eigenstaendiges ODER-Signal (W10 BESTAETIGT)
# Wird VOR der SRS-Formel geprueft — bei Match direkt GOTO Gate-6-Ende
# W26-Fix: STABLE HIGH = einmal geswitcht, kein Rauschen mehr. NUR RISING triggert.
IF aggregat_current == HIGH AND aggregat_trend == RISING:
  mode_switch_recommendation = "FULL_SYMBIOSE"
  Konfidenz = "moderate"
  LOG: "Gate-6: FULL_SYMBIOSE empfohlen (AGGREGAT ODER-Trigger) — aggregat_current={aggregat_current}, aggregat_trend={aggregat_trend}"
  → GOTO Gate-6-Ende (SRS-Logik wird NICHT mehr geprueft)
```

### Metriken-Check

| Metrik | Ist-Wert | Schwelle | Status |
|--------|----------|----------|--------|
| SRS (absolut) | {SRS aus _manifest.md SRS-Verlauf} | > 85 | {PASS/FAIL} |
| stagnation | {stagnation aus Gate 5} | >= 2.5 (FULL) / >= 2.0 (INLINE) | {PASS/FAIL} |
| d1_loc_debt | {aus HYPOTHESE{N}.md Frontmatter, falls vorhanden, sonst n/a} | > 200 | {PASS/FAIL/n/a} |

> **KONSISTENZ-CONSTRAINT (RF-AM-010):** SRS-Schwellen 85 (FULL_SYMBIOSE) und 60 (INLINE)
> sind die Quelle der Wahrheit fuer die gesamte AufwandsMetrik-Architektur.
> 2D-Matrix in _A_orchestrate Phase 4.2 und DONE_SCHWELLE in _SC_orchestrate Z725 muessen
> konsistent mit diesen Werten bleiben. Aenderungen hier erfordern synchrone Anpassung dort.
> Referenz: OmniCommand_AufwandsMetrik-SPEC.md AK-S2, RF-AM-010.

### W262 Formel (revidiert, W252)

```
# VOLLSTAENDIGE FORMEL (d1_loc_debt vorhanden und > 200):
IF SRS > 85 AND stagnation >= 2.5 AND d1_loc_debt > 200:
  mode_switch_recommendation = "FULL_SYMBIOSE"
  Konfidenz = "high"
  LOG: "Gate-6: FULL SYMBIOSE empfohlen (hohe Konfidenz) — SRS={SRS}, Stagnation={stag}, d1_loc_debt={debt}"

# REDUZIERTE FORMEL (d1_loc_debt nicht vorhanden oder <= 200):
ELIF SRS > 85 AND stagnation >= 2.5:
  mode_switch_recommendation = "FULL_SYMBIOSE"
  Konfidenz = "moderate"
  LOG: "Gate-6: FULL SYMBIOSE empfohlen (moderate Konfidenz) — SRS={SRS}, Stagnation={stag}, d1_loc_debt=n/a"

# INLINE-EMPFEHLUNG:
ELIF SRS > 60 AND stagnation >= 2.0 AND stagnation < 2.5:
  mode_switch_recommendation = "INLINE"
  Konfidenz = "moderate"
  LOG: "Gate-6: INLINE empfohlen (moderate Konfidenz) — SRS={SRS}, Stagnation={stag}"

# KEIN WECHSEL:
ELSE:
  mode_switch_recommendation = "NONE"
  Konfidenz = "none"
  LOG: "Gate-6: Kein Mode-Switch (SRS={SRS}, Stagnation={stag})"
```

### Empfehlung

```
mode_switch_recommendation: {FULL_SYMBIOSE | INLINE | NONE}
Konfidenz: {high | moderate | none}
```

> Manifest: Schreibe `mode_switch_recommendation` NICHT ins Manifest (nur in QUALITYGATE{N}.md).
> Phase 3.2 liest QUALITYGATE{N}.md und entscheidet (ADR-02 Hybrid-Architektur).

---

## Gate 7: Contract Audit (KontextManagement v1.0)

> **Zweck:** SOLL/IST-Vergleich der VERTRAG-Bloecke aller im Zyklus verwendeten Commands.
> Prueft ob deklarierte LIEST/SCHREIBT-Sektionen mit tatsaechlichem Verhalten uebereinstimmen.
> Orthogonal zu Gate 1-6 (Groessen-Achse vs Vertragstreue-Achse).

### Voraussetzung

```
Gates 1-6: BESTANDEN (Gate 7 wird NUR ausgefuehrt wenn Gates 1-6 PASS)
```

### Algorithmus

```
SCHRITT 1: Zyklus-Commands ermitteln
  → Lies Manifest SC_PIPELINE_STATE.aktive_agent_ids
  → Extrahiere Command-Namen aus Agent-IDs (z.B. "sc-x-observe" → _SC_observe)
  → Ergaenze: _SC_orchestrate (immer aktiv als Meta-Command)

SCHRITT 2: Fuer jeden Command im Zyklus
  → Lies VERTRAG-Block (LIEST + SCHREIBT Sektionen)
  → Vergleiche deklarierte Dateien mit tatsaechlich beobachteten Zugriffen
  → Klassifiziere Abweichungen:

  WENN Datei gelesen aber NICHT in LIEST deklariert:
    → LIEST-Bruch → Schwere: WARNING (Kontext-Verschwendung)

  WENN Datei geschrieben aber NICHT in SCHREIBT deklariert:
    → SCHREIBT-Bruch → Schwere: ALARM (Daten-Korruption moeglich)
    → HiL-Pflicht (Gate blockiert bis Team Lead entscheidet)

  WENN VERTRAG-Block fehlt komplett:
    → WARNING: "Kein VERTRAG-Block vorhanden"

SCHRITT 3: Report erstellen
  → Gate 7 Sektion in QUALITYGATE{N}.md schreiben
  → Gesamt-Status berechnen:
    - PASS: 0 ALARM, 0 WARNING
    - WARN: 0 ALARM, N WARNING (non-blocking)
    - FAIL: N ALARM (blocking → HiL-Entscheid)
```

### Bekannte Vertragsbrueche (Seed-Katalog)

| ID | Command | Bruch-Typ | Schwere | Beschreibung |
|----|---------|-----------|---------|-------------|
| VB-1 | _Pre_PR_orchestrate | LIEST-Bruch | WARNING | _manifest.md gelesen, nicht im VERTRAG |
| VB-2 | _Pre_PR_orchestrate | SCHREIBT-Bruch | NIEDRIG | Task/Team-Effekte nicht deklariert |
| VB-3 | _SC_ergebnis | SCHREIBT-Bruch | NIEDRIG | DS{NN}-Dateien nur in Untersektion |
| VB-4 | _SC_ergebnis | KOORDINATION | WARNING | Kein Crash-Recovery fuer W1→W2 |
| VB-5 | _model | LIEST-Bedingung | NIEDRIG | OBSERVE-Dateien deklariert aber nicht referenziert |
| KF-1 | KURZLEBIG_PROMPT | SCHREIBT-Bruch | ALARM | Schreibt Model-Datei ohne Deklaration |

### Output-Format (Sektion in QUALITYGATE{N}.md)

```markdown
## Gate 7: Contract Audit

| Command | Bruch-Typ | Schwere | Beschreibung | Empfehlung |
|---------|-----------|---------|-------------|-----------|
| {command} | LIEST-Bruch | WARNING | {datei} gelesen, nicht im VERTRAG | VERTRAG-Update empfohlen |
| {command} | SCHREIBT-Bruch | ALARM | Schreibt {datei} ohne Deklaration | HiL-Entscheid: VERTRAG korrigieren |

**Gesamt-Status Gate 7:** {PASS (0 ALARM) | WARN (N WARNING) | FAIL (N ALARM → HiL)}
```

### Eskalation bei ALARM

```
WENN Gate 7 = FAIL (mindestens 1 ALARM):
  → Gate blockiert
  → HiL-Entscheid erforderlich
  → Optionen fuer Team Lead:
    a) VERTRAG-Block korrigieren (Command-Datei updaten)
    b) DEFER: Vertragsbruch dokumentieren, weiter zum naechsten Zyklus
    c) ABORT: Feature pausieren bis VERTRAG-Bloecke konsistent
```

---

## Gate 8: Spec-Abweichungs-Eskalation (Z4: P3, RF-11..RF-16)

> **Zweck:** ERKENNT und ESKALIERT Spec-Abweichungen. Aendert NIEMALS die Spec autonom.
> Gate 8 ist ein Fruehwarnsystem — es zeigt dem Menschen Probleme auf,
> ueberschreibt aber weder GAP% noch die Spec selbst.

### Voraussetzung

```
Gates 1-7: BESTANDEN (Gate 8 wird NUR ausgefuehrt wenn Gates 1-7 PASS)
Skip-Bedingung: cycle_nr < 3 → Gate 8 = SKIP (zu wenig Daten)
spec_basis_changed-Bedingung (RF-16): WENN manifest.spec_basis_changed == true
  UND cycles_since_spec_change < 2:
    → Gate 8 = SKIP (Spec gerade geaendert, 2 Zyklen Abkuehlung)
    → LOG: "Gate 8: SKIP (spec_basis_changed, Abkuehlphase {cycles_since_spec_change}/2)"
```

### Erkennungspunkte (EP)

```
EP-1: Spec-Hypothese-Widerspruch / GAP-Stagnation (RF-12)
  Pruefe: GAP-Delta ueber letzte 2 Zyklen + verify_status aus next_cycle_context
  Benoetigt: 2 Vorgaenger-QUALITYGATE-Dokumente + next_cycle_context

  WENN cycle_nr < 4 ODER keine 2 Vorgaenger-QUALITYGATE vorhanden:
    → EP-1 = SKIP (zu wenig Trend-Daten)

  SONST:
    gap_current = synthese/{NAME}-GAP.md aktueller GAP%
    gap_prev = synthese/{NAME}-QUALITYGATE{N-2}.md Gate-3 GAP%
    gap_delta = gap_current - gap_prev
    verify = SC_PIPELINE_STATE.next_cycle_context.verify_status

    WENN gap_delta > -2.0 UND verify == "done":
      → EP-1 aktiv (WARN): "GAP-Stagnation ({gap_delta}%) trotz verify_status=done"
      Schwere: GROSS (HiL HARD BREAK auch bei HiL=off)
      Interpretation: Spec-Annahmen stimmen moeglicherweise nicht —
        Implementation passt (verify=done), aber GAP bewegt sich nicht
    WENN gap_delta > -2.0 UND verify == "partial":
      → EP-1 aktiv (WARN): "GAP-Stagnation ({gap_delta}%), verify=partial"
    SONST:
      → EP-1 = PASS

  ZUSAETZLICH pruefe HYPOTHESEN{N}.md:
    WENN IC-Findings explizit Spec-Annahmen widersprechen
      (Marker: "Spec-Annahme X ist nicht umsetzbar" ODER "widerlegt Spec"):
      → EP-1 aktiv (WARN hochstufen zu FAIL wenn gap_delta auch stagniert)

  Quelle: synthese/{NAME}-GAP.md, synthese/{NAME}-QUALITYGATE{N-1}.md,
          synthese/{NAME}-QUALITYGATE{N-2}.md, SC_PIPELINE_STATE.next_cycle_context,
          synthese/{NAME}-HYPOTHESEN{N}.md

EP-2: Implementation-Widerspruch (RF-13)
  Pruefe: DIVERGENT-Score-Anteil in GAP.md
  WENN DIVERGENT-Anteil > 40% am Gesamt-GAP-Score:
    → EP-2 aktiv (WARN)
  WENN DIVERGENT-Anteil > 60%:
    → EP-2 aktiv (FAIL direkt)
  SONST:
    → EP-2 = PASS
  Quelle: synthese/{NAME}-GAP.md (DIVERGENT-Kategorie zaehlen)

EP-3: Post-I Spec-Realitaetscheck (RF-14)
  Pruefe: i_core_result Rueckmeldungen via next_cycle_context
  Benoetigt: SC_PIPELINE_STATE.next_cycle_context (P2-Infrastruktur)

  WENN next_cycle_context nicht vorhanden ODER kein I-Lauf stattgefunden:
    → EP-3 = SKIP (Hinweis: "next_cycle_context nicht verfuegbar oder kein I-Lauf")

  SONST:
    verify = SC_PIPELINE_STATE.next_cycle_context.verify_status
    sc_rec = SC_PIPELINE_STATE.next_cycle_context.sc_recommendations_triggered
    slices_total = manifest.SC_PIPELINE_STATE.slices (falls vorhanden, sonst 0)
    slices_done = len(SC_PIPELINE_STATE.next_cycle_context.unimplemented_slices)
    slices_completed_pct = ((slices_total - slices_done) / slices_total) * 100

    WENN verify == "failed" UND slices_completed_pct >= 80:
      → EP-3 aktiv (FAIL direkt)
      Schwere: GROSS (HiL HARD BREAK auch bei HiL=off)
      Interpretation: Implementation weitgehend vollstaendig (>=80% Slices done),
        aber Verifikation gescheitert — Spec-Annahmen koennten falsch sein
    WENN sc_rec == true:
      reason = SC_PIPELINE_STATE.next_cycle_context.next_focus_override
      → EP-3 aktiv (WARN): "sc_recommendations.triggered: {reason}"
    WENN verify == "failed" UND slices_completed_pct < 80:
      → EP-3 = PASS (Verifikation failed weil Slices unvollstaendig — kein Spec-Problem)
    SONST:
      → EP-3 = PASS

  Quelle: SC_PIPELINE_STATE.next_cycle_context (verify_status, sc_recommendations_triggered,
          unimplemented_slices)

EP-4: Widerlegungs-Marker auf Spec-W{n} (RF-15)
  Pruefe: W{n} mit Status DIREKT_WIDERSPRUCHLICH und Spec-Verknuepfung
  FUER JEDE W{n} in Model.md:
    IF status == "DIREKT_WIDERSPRUCHLICH" OR status == "WIDERLEGT":
      IF W{n} hat Marker "Quelle: SPEC" OR "rf-ref:" OR Spec-RF-Referenz:
        → widerlegte_spec_wn += 1
  WENN widerlegte_spec_wn >= 3:
    → EP-4 aktiv (FAIL direkt)
  WENN widerlegte_spec_wn >= 1:
    → EP-4 aktiv (WARN)
  SONST:
    → EP-4 = PASS
  Quelle: models/{NAME}_Model.md (W{n}-Status + Verknuepfungen)
```

### Spec-Confidence-Aggregation (RF-16)

```
# Schritt 1: EP-Ergebnisse sammeln
ep_results = [EP-1, EP-2, EP-3, EP-4]  # jeweils PASS, WARN, FAIL, oder SKIP

# Schritt 2: SKIP-Behandlung
active_eps = [ep for ep in ep_results if ep.status != "SKIP"]
skipped_eps = [ep for ep in ep_results if ep.status == "SKIP"]

# Schritt 3: Confidence-Aggregation
fail_count = count(ep.status == "FAIL" for ep in active_eps)
warn_count = count(ep.status == "WARN" for ep in active_eps)

WENN fail_count >= 1:
  → confidence = FAIL
  → Schwere: GROSS (HiL HARD BREAK auch bei HiL=off)
  → Sammelbericht: Liste aller FAIL-EPs mit Details
  → WICHTIG: ERKENNEN + ESKALIEREN, NIEMALS Spec autonom aendern!

WENN warn_count >= 1 UND fail_count == 0:
  → confidence = WARN
  → Sammelbericht: Liste aller WARN-EPs mit Details
  → Empfehlung: Beobachten, naechster Zyklus entscheidet

WENN fail_count == 0 UND warn_count == 0:
  → confidence = PASS
  → Alle aktiven EPs bestanden

# Schritt 4: SKIP-Hinweis (wenn active_eps < 4)
WENN len(skipped_eps) > 0:
  → Hinweis: "{N} EPs uebersprungen: {skipped_ep_names} — Confidence basiert auf {len(active_eps)}/4 EPs"

# Schritt 5: spec_basis_changed Handling (RF-16 Post-Review)
WENN manifest.spec_basis_changed == true:
  → Circuit-Breaker-Schwellen zuruecksetzen (Stagnation auf 0)
  → Trennlinie in GAP-Trend-Tabelle einfuegen
  → Gate 8 SKIP fuer naechste 2 Zyklen (Abkuehlphase)
  → LOG: "Gate 8: spec_basis_changed — Schwellen-Reset, 2-Zyklen-Abkuehlung"
```

### Status-Berechnung

```
PASS: confidence == PASS (0 aktive EPs mit WARN/FAIL)
WARN: confidence == WARN (mindestens 1 EP WARN, kein FAIL — Sammelbericht)
FAIL: confidence == FAIL (mindestens 1 EP mit FAIL)

AUCH BEI HiL=off: Spec-Abweichung FAIL = IMMER HiL (wie BLOCKER)
System schlaegt NICHT vor wie Spec geaendert werden soll — das entscheidet der Mensch.
NIEMALS Spec autonom aendern — Gate 8 ERKENNT und ESKALIERT nur.
```

### Bei FAIL: HiL-Entscheid

```
WENN Gate 8 = FAIL:
  → Gate blockiert
  → HiL-Entscheid erforderlich (AUCH bei HiL=off)
  → Optionen fuer Team Lead:
    a) /_spec {NAME} normal aufrufen (Spec-Review)
    b) DEFER: Abweichung dokumentieren, weiter zum naechsten Zyklus
    c) ABORT: Feature pausieren bis Spec konsistent
  → System schlaegt NICHT vor welche Option — Mensch entscheidet
  → Nach Spec-Review: spec_basis_changed im Manifest setzen (RF-16)
```

### Output-Format (Sektion in QUALITYGATE{N}.md)

```markdown
## Gate 8: Spec-Abweichungs-Eskalation

| EP | Bedingung | Status | Details |
|----|-----------|--------|---------|
| EP-1 | GAP-Stagnation + Hypothese-Widerspruch | {SKIP/PASS/WARN/FAIL} | GAP-Delta: {X}%, verify: {status}, Hypothese-Widerspruch: {ja/nein} |
| EP-2 | DIVERGENT >40% | {PASS/WARN/FAIL} | DIVERGENT-Anteil: {X}% |
| EP-3 | Post-I Spec-Realitaetscheck | {SKIP/PASS/WARN/FAIL} | verify: {status}, slices: {X}%, sc_rec: {triggered/nicht} |
| EP-4 | Widerlegungs-Marker | {PASS/WARN/FAIL} | {N} widerlegte Spec-W{n} |

**Spec-Confidence:** {PASS | WARN (Sammelbericht) | FAIL → HiL HARD BREAK}
**Aktive EPs:** {N}/4 (uebersprungen: {skipped_names})
**Gesamt-Status Gate 8:** {SKIP (cycle<3 oder spec_basis_changed) | PASS | WARN | FAIL → HiL}
```

---

## Eskalations-Hierarchie (Kap. 2.7)

**Aktive Eskalation:** KEINE

**Hierarchie:**
1. P1 ABORT (≥7.0 Stagnation) → NICHT AKTIV
2. P2 Re-Expansion (≥5.0 Stagnation) → NICHT AKTIV
3. P3 Battle-Royale (Scope-Reduktion) → AKTIV
4. P4 Model-Split (>15 W{n}/TC) → AUSGEFÜHRT
5. P5 BSD (T1-T5 Muster) → OPTIONAL (T4 leicht)
6. P6 BSD-T6 (Untracked Quellen) → PFLICHT wenn Untracked detektiert

**Nächste Massnahme:** Canary Probe für Storage-TC (optional)

---

## Zusammenfassung

| Gate | Status | Empfehlung |
|------|--------|------------|
| 1: Battle-Royale | ⚠ SCHWACH | Weitermachen, BR intensivieren |
| 2: Kohäsion (Ratio) | ✅ OK | Split ausgeführt |
| 2: Kohäsion (W95 absolut) | ✅ 30 ≤ 50 | Normal |
| 3: Feature-Abschluss (W{n}) | 🔄 85% | 1-2 Zyklen bis Abschluss |
| 3: PL-Blocker (Einpflaster) | {true/false/SKIP} | **VETO wenn true** (offene PL-Items) |
| 4: BSD-Trigger (T1-T5) | ⚠ T4 | Canary Probe optional |
| 4: BSD-T6 Quelle-Verif. | ✅ OK | Alle Quellen tracked |
| 5: Stagnation | ✅ OK | Weitermachen (1.5 < 3.0) |
| 6: Mode-Switch | {Empfehlung} | {FULL_SYMBIOSE / INLINE / NONE} |
| 7: Contract Audit | {PASS/WARN/FAIL} | {0 ALARM / N WARNING / N ALARM → HiL} |
| 8: Spec-Eskalation | {SKIP/PASS/WARN/FAIL} | Confidence: {PASS/WARN/FAIL}, {N}/4 EPs aktiv |

**Gesamt-Bewertung (Einpflaster-Regel, 2026-04-20):**
- **pl_blocker == true** → GATES NICHT BESTANDEN. Kein DONE-Signal. Hypothese MUSS SC_NEEDS_IMPL=true setzen.
- pl_blocker == false ODER SKIP → Normale Auswertung der uebrigen Gates.
- Begruendung: PL-Items sind Vertragspflichten (post-IDF). Feature-DONE ohne PL-Leere = Prozess-Verletzung.

**Gesamt-Bewertung (Legacy):** ✅ GATES BESTANDEN - Hypothese kann aufgestellt werden

**Empfohlene Nächste Schritte:**
1. /_SC_hypothese (Hauptpfad)
2. Optional: /_blindspotDetection für Storage-TC (T4-Muster)
```

---

## Parking Lot Integration

Falls während Quality-Gate-Check Incidental Tasks auffallen:

**Beispiel:**
"Gate 2 zeigt, dass Logging-TC nur 4 W{n} hat - evtl. Structured Logging einführen?"

→ Schreibe in `_parking-lot.md`:

```markdown
## 2026-02-03 - Von /_SC_qualityGate (Cycle 4)

- [ ] **Structured Logging evaluieren**
  - **Beschreibung:** Logging-TC hat nur 4 W{n}, Structured Logging könnte verbessern
  - **Grund:** Quality-Gate Kohäsions-Check
  - **Priorität:** NIEDRIG
  - **TC-Nähe:** Logging
  - **Quelle:** Gate 2 (Kohäsions-Check)
```

---

## Kompakt-Sicherheit

Nach Command-Abschluss:
- State: QUALITYGATE{CYCLE}.md geschrieben
- Resume: _SC_hypothese kann QUALITYGATE.md lesen

---

## Obsidian-Tags

```yaml
tags:
  - type/qualitygate
  - op/{FEATURE}
  - topic/Quality-Assurance
  - topic/Battle-Royale
cycle: {N}
chain-position: qualitygate
prev: [[{NAME}-OBSERVE{N}]]
next: [[{NAME}-HYPOTHESEN]]
```

---

## Siehe auch

- [[SC_modelMaintain]] - Vorheriger Schritt (liefert updated Model)
- [[SC_hypothese]] - Nächster Schritt (nutzt Quality-Gate-Ergebnisse)
- [[_blindspotDetection]] - Optional getriggert bei T1-T5
- [[_architecturalBoundaries]] - Optional getriggert bei Feature-Zerlegung
- [[_analyse]] - LEGACY Command (<v2.2)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_SC_qualityGate abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
