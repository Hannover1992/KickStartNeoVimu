# /_I_verify

**Status:** v1.0
**Actor:** VERIFIER
**Zweck:** SPEC ↔ Test Mapping - Tests sind die Wahrheit, nicht der Code

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_verify {SLICE_NAME|global}                      |
+===============================================================+
|                                                                |
|  KERN-PRINZIP:                                                 |
|    Tests lesen = Stufe 1 (Wahrheit)                            |
|    Code lesen  = Stufe 2 (nur bei Unklarheit)                  |
|    Tests sind leichter zu lesen als Code.                      |
|    Tests enthalten Beispiel-Daten und echte Szenarien.         |
|    Tests SIND die Dokumentation der Implementierung.           |
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. .claude/analysis/_manifest.md                            |
|    2. .claude/CURRENT_SLICE.md (falls Mitose-Worktree)        |
|    3. .claude/specs/{NAME}_Spec.md                             |
|       → SOLL: AKs, Prozessschritte, Interfaces, Komponenten   |
|    4. .claude/Task.md                                          |
|       → Akzeptanzkriterien                                     |
|                                                                |
|  LIEST (Input) - PER SLICE:                                    |
|    5. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md            |
|       → Geplante Test-Liste                                    |
|    6. .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md       |
|       → Unit Test Ergebnisse                                   |
|    7. .claude/analysis/synthese/{NAME}-INTEGRATION-{SLICE}.md  |
|       → Integration Test Ergebnisse                            |
|    8. .claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md       |
|       → System Test Ergebnisse                                 |
|                                                                |
|  LIEST (Input) - DIE WAHRHEIT (Stufe 1):                      |
|    9. Codebase: *Tests*.cs (Unit Tests)                        |
|   10. Codebase: *IntegrationTests*.cs (Integration Tests)      |
|   11. Codebase: *E2E*.cs / *.feature (System/E2E Tests)       |
|       → Test-Methoden, Assertions, Beispiel-Strings            |
|       → DAS ist die Dokumentation des Codes                    |
|                                                                |
|  LIEST (Input) - NUR BEI UNKLARHEIT (Stufe 2):                |
|   12. Codebase: Production Code                                |
|       → Nur wenn Test-Bedeutung unklar                         |
|                                                                |
|  LIEST (Input) - GLOBAL MODUS:                                 |
|   13. Alle VERIFY-{SLICE}.md (vorherige Slice-Verifikationen)  |
|   14. .claude/analysis/synthese/{NAME}-ARCHITECT.md            |
|       → Slice-Liste + Abhaengigkeiten                          |
|   15. .claude/analysis/evidence/*.md (optional)               |
|       → constraint-Evidence = intentionale Abweichung von      |
|         Standard-Pattern (kein FALSE GAP melden)               |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. .claude/analysis/synthese/{NAME}-VERIFY-{SLICE}.md       |
|       oder: {NAME}-VERIFY.md (global)                          |
|    2. .claude/analysis/_manifest.md (aktualisieren)            |
|                                                                |
|  SCHREIBT (Output) - OPTIONAL:                                 |
|    .claude/_parking-lot.md (APPEND - entdeckte Test-Luecken)   |
|                                                                |
|  PIPELINE:                                                     |
|    Per Slice:                                                  |
|    [/_I_codeSystem] → [/_I_verify] → [SLICE VERIFIZIERT]      |
|                                                                |
|    Global (nach allen Slices):                                 |
|    [Alle Slices DONE] → [/_I_verify global] →                  |
|    [/_gap normal] → [/_model finish] → [Pre-PR]               |
|                                                                |
|  BEZIEHUNG ZU /_gap:                                           |
|    /_gap     = GAP-Code (SPEC vs Code/Model)                   |
|    /_I_verify = GAP-Test (SPEC vs Tests)                       |
|    BEIDE zusammen = vollstaendiges Bild                        |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**VERIFIER:** Mappt SPEC auf Tests. Entdeckt Test-Luecken auf allen Ebenen.

**TUT:** SPEC-Items extrahieren, Test-Dateien lesen (3 Schichten),
bidirektionales Mapping erstellen, Luecken identifizieren, Coverage quantifizieren.

**NICHT:** Code schreiben, Tests schreiben, Model updaten.
Code lesen NUR bei Unklarheit (Stufe 2).

**Eskalation:** Bei Coverage < 60% → Warnung. Bei fehlenden AK-Tests → Blocker.

---

## Zwei Modi

| Modus | Wann | Scope | Output |
|-------|------|-------|--------|
| **Slice** | Nach /_I_codeSystem | 1 Slice | VERIFY-{SLICE}.md |
| **Global** | Nach allen Slices | Gesamtes Feature | VERIFY.md |

---

## Schritt 0: Manifest + Modus

```
1. Lies _manifest.md → NAME, aktuelle Phase

2. Falls {SLICE_NAME} angegeben UND != "global":
   → Slice-Modus
   → Pruefe: SYSTEM-{SLICE}.md existiert mit status=final
   → Falls nicht: ABBRUCH "/_I_codeSystem {SLICE} muss zuerst abgeschlossen sein"

3. Falls "global":
   → Global-Modus
   → Pruefe: Alle Slices in ARCHITECT.md haben SYSTEM-*.md mit status=final
   → Falls nicht alle: WARNUNG "Slices {X,Y} noch nicht abgeschlossen"
   → Falls VERIFY-{SLICE}.md fuer abgeschlossene Slices vorhanden:
     → Nutze als Input (nicht nochmal Slice-Verify ausfuehren)

4. Falls CURRENT_SLICE.md existiert:
   → Slice-Modus mit Slice aus CURRENT_SLICE.md
```

---

## Schritt 1: SPEC-Dekomposition

```
Lies specs/{NAME}_Spec.md + Task.md und extrahiere ALLE verifizierbaren Items:

SPEC-ITEMS Tabelle aufbauen:

| ID | Typ | Beschreibung | Erwartete Schicht | Quelle |
|------|------|-------------|-------------------|--------|
| AK1 | Akzeptanzkriterium | {aus Task.md} | System | Task.md |
| P01 | Prozessschritt | {aus Spec §2} | Integration | Spec §2 |
| I01 | Interface | {aus Spec §3} | Integration | Spec §3 |
| D01 | DB-Schema | {aus Spec §5} | Unit+IT | Spec §5 |
| S01 | Security/Config | {aus Spec §9} | Unit+IT | Spec §9 |

SCHICHT-ZUORDNUNG (Erwartung):
  AKs                → primaer System/E2E Tests
  Prozessschritte    → primaer Integration Tests
  Interfaces         → Integration Tests
  Business Logic     → Unit Tests
  DB-Schema          → Unit + Integration Tests
  Security/Config    → alle Schichten moeglich
```

---

## Schritt 2: Test-Discovery (DIE WAHRHEIT)

### Stufe 1: Tests lesen (IMMER zuerst)

```
SCHICHT 1 - Unit Tests:
  Glob: Sources/Backend/**/*Tests*/**/*.cs (NICHT *IntegrationTests*)
  Fuer jeden relevanten Test:
    → Test-Methode Name (beschreibt Szenario)
    → Assertions (beschreibt Erwartung)
    → Arrange-Daten (Beispiel-Strings, Konfigurationswerte)
    → Mocks (zeigt Abhaengigkeiten und Boundaries)

SCHICHT 2 - Integration Tests:
  Glob: Sources/Backend/**/*IntegrationTests*/**/*.cs
  Fuer jeden relevanten Test:
    → Test-Setup (zeigt echte Infrastruktur)
    → HTTP-Calls / DB-Queries (zeigt echte Boundaries)
    → Beispiel-Daten (zeigt echte Szenarien)
    → Container-Setup (zeigt echte Umgebung)

SCHICHT 3 - System/E2E Tests:
  Glob: Sources/**/*E2E*/**/*.cs + Sources/**/*.feature
  Fuer jeden relevanten Test:
    → User Flow (Given/When/Then)
    → End-to-End Szenarien
```

### Stufe 2: Code lesen (NUR BEI UNKLARHEIT)

```
Falls ein Test nicht eindeutig einem SPEC-Item zuordenbar:
  → Production Code lesen um Kontext zu verstehen
  → DOKUMENTIERE im Report warum Stufe 2 noetig war
  → Ziel: Test-Bedeutung klaeren, NICHT Code analysieren
```

---

## Schritt 3: Bidirektionales Mapping

### Richtung 1: SPEC → Tests (Backward Verification)

```
Fuer JEDES SPEC-Item aus Schritt 1:
  → Finde Tests die dieses Item abdecken
  → Pruefe: Ist die erwartete Schicht abgedeckt?
  → Klassifiziere:

    COVERED:  Mindestens 1 Test in erwarteter Schicht
    PARTIAL:  Tests vorhanden, aber nicht in erwarteter Schicht
              (z.B. AK nur per Unit Test, kein System Test)
    MISSING:  Kein Test fuer dieses SPEC-Item
```

### Richtung 2: Tests → SPEC (Forward Verification)

```
Fuer JEDEN gefundenen Test:
  → Welchem SPEC-Item dient er?
  → Klassifiziere:

    MAPPED:  Test dient einem SPEC-Item (Primaer-Zweck)
    GUARD:   Regressions-Schutz (kein direktes SPEC-Item, aber wertvoll)
    ORPHAN:  Test ohne erkennbaren SPEC-Bezug (Waste?)
```

---

## Schritt 4: Coverage + Luecken

```
COVERAGE-MATRIX aufbauen:

| SPEC-Item | Beschreibung | Unit | Integration | System | Status |
|-----------|-------------|------|-------------|--------|--------|
| AK1 | {Beschr.} | - | IT3 | - | PARTIAL |
| P01 | {Beschr.} | - | IT1 | - | COVERED |
| D01 | {Beschr.} | T8,T9 | - | - | COVERED |

METRIKEN berechnen:
  SPEC-Items gesamt: {N}
  COVERED: {N} ({%})
  PARTIAL: {N} ({%})
  MISSING: {N} ({%})

  Tests gesamt: {N}
  MAPPED: {N} ({%})
  GUARD: {N} ({%})
  ORPHAN: {N} ({%})

GAP-TEST ITEMS (entdeckte Luecken):
  GT-01: {SPEC-Item} hat keinen {Schicht} Test → Empfehlung
  GT-02: ...

BLOCKER identifizieren:
  AK ohne JEDEN Test = BLOCKER fuer Pre-PR
  Kritischer Prozessschritt ohne IT = BLOCKER
```

---

## Schritt 5: VERIFY Report schreiben

### Per-Slice Output

Pfad: `.claude/analysis/synthese/{NAME}-VERIFY-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: verify
pipeline: implementation
status: final
spec_items_total: {N}
covered: {N}
partial: {N}
missing: {N}
coverage_percent: {N}
tests_mapped: {N}
tests_orphan: {N}
blocker: {N}
last_updated: {YYYY-MM-DD}
---

# Verify: {NAME} - {SLICE_NAME}

**Coverage:** {covered}/{total} ({%}) | **Partial:** {N} | **Missing:** {N}
**Tests:** {mapped} mapped, {orphan} orphan, {guard} guard
**Blocker:** {N}

## SPEC → Test Mapping

| SPEC-Item | Beschreibung | Unit | IT | System | Status |
|-----------|-------------|------|------|--------|--------|
| AK1 | ... | T1 | IT3 | - | PARTIAL |
| P01 | ... | - | IT1 | - | COVERED |

## Test → SPEC Mapping

| Test | Datei:Zeile | SPEC-Item | Typ |
|------|-------------|-----------|-----|
| SendFileAsync_Happy | Adapter:45 | P01, AK2 | MAPPED |
| RetryAsync_Transient | Adapter:123 | S01 | MAPPED |
| OldLegacyTest | Legacy:89 | - | GUARD |

## GAP-Test Items

| # | SPEC-Item | Fehlende Schicht | Empfehlung | Prio |
|---|-----------|------------------|------------|------|
| GT-01 | AK1 | System | E2E fuer Gesamtflow | HOCH |

## Zusammenfassung

{3-5 Saetze: Was gut abgedeckt, wo Luecken, Empfehlung}
```

### Global Output

Pfad: `.claude/analysis/synthese/{NAME}-VERIFY.md`

```markdown
---
name: {NAME}
phase: verify-global
pipeline: implementation
status: final
slices_verified: {N}
spec_items_total: {N}
covered: {N}
partial: {N}
missing: {N}
coverage_percent: {N}
blocker: {N}
last_updated: {YYYY-MM-DD}
---

# Verify Global: {NAME}

**Slices:** {N}/{N} verifiziert | **Coverage:** {%} | **Blocker:** {N}

## Slice-Uebersicht

| Slice | Items | Covered | Partial | Missing | Coverage |
|-------|-------|---------|---------|---------|----------|
| {S1} | {N} | {N} | {N} | {N} | {%} |
| **GESAMT** | **{N}** | **{N}** | **{N}** | **{N}** | **{%}** |

## Cross-Slice Analyse

{Ueberschneidungen, gemeinsame Tests, Luecken die nur global sichtbar sind}

## GAP-Test Gesamtliste

| # | Slice | SPEC-Item | Fehlende Schicht | Prio |
|---|-------|-----------|------------------|------|

## Blocker (MUSS vor Pre-PR)

{AKs ohne Tests, kritische Prozessschritte ohne Verification}

## Naechster Schritt

Falls BLOCKER > 0:
  → Zurueck zu /_I_codeAtomic / codeIntegration / codeSystem
Falls Coverage > 80% und BLOCKER = 0:
  → /_gap {NAME} normal (GAP-Code Re-Eval)
  → /_model {NAME} finish
  → Pre-PR
```

---

## Schritt 6: Manifest + Naechste Schritte

```
Manifest aktualisieren:
  PHASE: _I_verify {SLICE|global}
  VERIFY-COVERAGE: {%}
  GAP-TEST-ITEMS: {N}
  BLOCKER: {N}

Naechster Schritt:
  Falls Slice-Modus + Mitose-Worktree:
    → "WORKTREE VERIFIZIERT. Bereit fuer /_I_fanIn"

  Falls Slice-Modus + weitere Slices:
    → "/_I_codeAtomic {NEXT}" oder "/_I_verify {NEXT}" je nach Status

  Falls Slice-Modus + letzter Slice:
    → "/_I_verify global empfohlen"

  Falls Global-Modus + Blocker:
    → Blocker auflisten, zurueck in Pipeline

  Falls Global-Modus + kein Blocker:
    → "/_gap {NAME} normal (GAP-Code Re-Eval)"
    → "/_model {NAME} finish"
    → "Pre-PR wenn beides gruen"
```

---

## Beziehung zu /_gap (GAP-Code vs GAP-Test)

```
         SPEC (SOLL)
        /            \
       /              \
  /_gap              /_I_verify
  (GAP-Code)         (GAP-Test)
      |                   |
      v                   v
   CODE               TESTS
  "Stimmt der Code    "Sind alle SPEC-Items
   mit SPEC ueberein?" durch Tests belegt?"

/_gap     liest CODE und MODEL → findet Code-Luecken
/_I_verify liest TESTS         → findet Test-Luecken

BEIDE zusammen = vollstaendiges Bild vor Pre-PR
```

---

## Qualitaetskriterien

- Tests IMMER zuerst lesen (Stufe 1), Code NUR bei Unklarheit (Stufe 2)
- JEDES AK aus Task.md muss im Mapping erscheinen
- Bidirektional: SPEC→Tests UND Tests→SPEC
- Orphan-Tests dokumentieren (nicht loeschen, aber kennzeichnen)
- Guard-Tests als wertvoll anerkennen (Regressions-Schutz)
- Coverage quantifizierbar (Prozent, nicht subjektiv)
- Blocker klar definiert (AK ohne jeden Test = Blocker)
- Parking-Lot fuer entdeckte Luecken nutzen (APPEND)
- Manifest nach Verify aktuell
- KEINE Code-Aenderungen, KEINE Tests schreiben (nur analysieren)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_verify abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
