# /_SC_qualityGate

**Status:** NEU v2.3 (QW-3 T6 + QW-4 absolute W{n}-Schwellenwert, ersetzt _analyse Sektion B Quality-Checks)
**Actor:** QUALITY-GATE
**Zweck:** Quality Gates prüfen, BSD triggern

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_SC_qualityGate {NAME} [easy|normal|hard]                     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. _manifest.md                                                       ║
║    2. models/{NAME}_Model.md (AKTUALISIERT von _SC_modelMaintain)       ║
║    3. synthese/{NAME}-OBSERVE{CYCLE}.md (Findings Kontext)              ║
║    4. synthese/{NAME}-ERGEBNIS*.md (falls Folge-Zyklus, SRS-Trend)      ║
║    5. models/{NAME}_Model-Topologie.md (falls Split aktiv)              ║
║    6. synthese/{NAME}-GAP.md (falls vorhanden)                         ║
║       ◄── NEU v3.0: GAP% fuer Feature-Abschluss-Erkennung            ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║      synthese/{NAME}-QUALITYGATE{CYCLE}.md                               ║
║      → Battle-Royale-Bewertung (SRS-Trend, Anti-Pattern)               ║
║      → Kohaesion-Check (W{n}/TC, Split-Trigger)                        ║
║      → Feature-Abschluss-Erkennung (v2.1)                               ║
║      → Blind-Spot-Trigger (T1-T6, optional)                             ║
║      → Stagnations-Bewertung (Schwellen, Massnahme)                    ║
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

## Gate 3: Feature-Abschluss-Erkennung (v2.1)

### W{n} Coverage pro Teilproblem

| Teilproblem | W{n} Coverage | Status |
|-------------|---------------|--------|
| User-Login | 95% | ✅ ABGESCHLOSSEN |
| Token-Refresh | 90% | ✅ ABGESCHLOSSEN |
| Role-Assignment | 60% | 🔄 IN ARBEIT |

**Feature-Status:** 🔄 IN ARBEIT (85% Gesamt-Coverage)

**Empfehlung:** 1-2 weitere Zyklen bis Feature-Abschluss

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
| 3: Feature-Abschluss | 🔄 85% | 1-2 Zyklen bis Abschluss |
| 4: BSD-Trigger (T1-T5) | ⚠ T4 | Canary Probe optional |
| 4: BSD-T6 Quelle-Verif. | ✅ OK | Alle Quellen tracked |
| 5: Stagnation | ✅ OK | Weitermachen (1.5 < 3.0) |

**Gesamt-Bewertung:** ✅ GATES BESTANDEN - Hypothese kann aufgestellt werden

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
