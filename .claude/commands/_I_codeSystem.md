# /_I_codeSystem

**Status:** v4.1 (exit_report Pflichtblock + Parking-Lot Aktivierung — PN-1 I-ExitReport)
**Actor:** SYSTEM-TESTER
**Zweck:** System/E2E Tests via Red-Green-Refactor (Batch: 1-2 Tests pro Aufruf)

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_codeSystem {SLICE_NAME}                          |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. .claude/analysis/_manifest.md                            |
|    2. .claude/CURRENT_SLICE.md (falls Mitose-Worktree)        |
|    3. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md            |
|       → System Test-Liste (ST1, ST2, ...)                     |
|       → E2E-Szenarien (User Flows)                            |
|    4. .claude/analysis/synthese/{NAME}-INTEGRATION-{SLICE}.md  |
|       → VORAUSSETZUNG: status=final (alle ITs gruen)          |
|    5. .claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md       |
|       → RESUME: Falls vorhanden, lies status + done Tests     |
|    6. .claude/Task.md                                          |
|       → Akzeptanzkriterien (System Tests validieren diese!)   |
|    7. Codebase (Production Code, Konfiguration, E2E Tests)    |
|                                                                |
|  LIEST (Input) - OPTIONAL bei Code-Generierung:               |
|    8. .claude/meta/implementation/routing.md                   |
|       → API-Route-Naming, Versioning, snake_case              |
|       → KRITISCH: Verhindert 404-Fehler in E2E-Tests          |
|    9. .claude/meta/implementation/auth.md                      |
|       → JWT, Bearer Token, [Authorize]-Attribute              |
|   10. .claude/meta/implementation/error-handling.md            |
|       → Exception-Mapping, Error-Response-Format              |
|   11. .claude/meta/implementation/testing.md                   |
|       → E2E-Test-Pattern, Data-Builder                        |
|       → Falls fehlt: WARN + CONTINUE (kein ABORT)             |
|       → Lesen VOR Schritt 2 (E2E Test-Strategie)             |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. Code: System/E2E Tests + System-Konfiguration           |
|    2. .claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md       |
|       → INKREMENTELL: Nach JEDEM gruenen ST aktualisieren     |
|       → status: partial (N/M) oder final (M/M)               |
|    3. .claude/analysis/_manifest.md (nach JEDEM ST update)    |
|                                                                |
|  SCHREIBT (Output) - OPTIONAL:                                 |
|    .claude/patterns/_pattern-library.md                       |
|    .claude/analysis/_parking-lot.md (APPEND bei Findings)     |
|                                                                |
|  MCP: mcp__cleancoder__query() NUR bei E2E-Unsicherheit       |
|    MIN-Modus: max 1 Query, limit=1                            |
|                                                                |
|  BATCH-MODUS:                                                  |
|    Bearbeite 1-2 Tests pro Aufruf, dann STOPPE.              |
|    E2E Tests sind am komplexesten → kleinste Batches.        |
|    Resume liest SYSTEM.md → weiss wo weitermachen.            |
|                                                                |
|  PIPELINE:                                                     |
|    [/_I_codeIntegration] → [/_I_codeSystem] →                 |
|    [/_I_verify] → [SLICE VERIFIZIERT]                          |
|                                                                |
|  VORAUSSETZUNG:                                                |
|    INTEGRATION-{SLICE}.md existiert mit status=final          |
|    (alle Unit + Integration Tests gruen)                      |
|                                                                |
|  ERGEBNIS:                                                     |
|    SYSTEM-{SLICE}.md (status=partial oder final)              |
|    partial → User ruft erneut auf                             |
|    final   → Slice ABGESCHLOSSEN                              |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**SYSTEM-TESTER:** System/E2E Tests via TDD + Slice-Abschluss.

**TUT:** E2E Tests schreiben, Akzeptanzkriterien validieren, System-Konfiguration
anpassen (Feature Toggles, Routing, Testdaten), Slice als ABGESCHLOSSEN erklaeren.

**NICHT:** Unit Tests, Integration Tests, Business Logic aendern (NUR Config!).

**Eskalation:** Bei 5+ RGR ohne Fortschritt → /_SC_observe

---

## Schritt 0: Resume-Check + Voraussetzungen

### 0.1 Mitose-Check

```
Falls .claude/CURRENT_SLICE.md existiert:
  → {SLICE_NAME} aus CURRENT_SLICE.md verwenden
  → NUR an diesem Slice arbeiten
```

### 0.2 Integration-Phase pruefen

```
Lies INTEGRATION-{SLICE}.md → Pruefe Frontmatter: status
  → Falls status != final:
      ABBRUCH: "/_I_codeIntegration {SLICE} muss zuerst abgeschlossen werden"
  → Falls status = final: OK, weiter
```

### 0.3 Resume-Check (NEU v4.0)

```
Falls .claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md existiert:
  → Lies Frontmatter: status, tests_done, tests_total, next_test
  → Falls status=final:
      AUSGABE: "SYSTEM Phase bereits abgeschlossen."
      AUSGABE: "Slice {SLICE} ist ABGESCHLOSSEN."
      → STOP
  → Falls status=partial:
      AUSGABE: "Resume: {tests_done}/{tests_total} STs fertig."
      AUSGABE: "Starte bei {next_test}."
      → Setze fort
Falls NICHT existiert:
  → Neuer Start bei ST1
```

### 0.4 Standard-Inputs

1. Lies `plans/{NAME}-{SLICE}-PLAN.md` → ST-Liste, E2E-Szenarien
2. Lies `Task.md` → Akzeptanzkriterien
3. Lies `INTEGRATION-{SLICE}.md` → Boundary-Entscheidungen
4. Lies `_pattern-library.md` (falls vorhanden)
5. Bestimme BATCH_SIZE: 1-2 (E2E Tests sind am komplexesten)

---

### 0.5 Optional-Input: Implementation Meta

Fuer relevante Topics laden (falls Datei existiert):

| Topic | Prioritaet | Wann laden |
|-------|-----------|------------|
| `routing.md` | KRITISCH — immer | Alle E2E-Tests mit HTTP-Calls |
| `auth.md` | HOCH | E2E-Tests mit Auth-Flows (Login, Token, geschuetzte Endpoints) |
| `testing.md` | MITTEL | E2E-Test-Klassen-Struktur, Data-Builder |
| `error-handling.md` | MITTEL | E2E-Tests die Fehlerszenarien validieren (4xx, 5xx) |

Falls Datei nicht existiert:
  - WARN: "⚠️ `.claude/meta/implementation/{topic}.md` nicht gefunden — weiter ohne"
  - SUGGEST: "Empfehlung: `/_I_updateMeta` kann Regeln hinzufuegen (nach manuellem Fund)"
  - CONTINUE (kein ABORT)

Falls Datei vorhanden: Regeln R1..Rn extrahieren und als Vorgaben VOR E2E Test-Strategie nutzen.
Beim Schreiben referenzieren: `// routing.md R1: Plural-Routes angewendet`

WICHTIG fuer routing.md — verhindert DCSRE-93-Klasse Fehler:
  - routing.md R1 erzwingt: Plural + lowercase + /api/v1/ Prefix
  - KORREKT: `/api/v1/pflegeeinrichtungen/42` (gruent sofort)
  - FALSCH ohne routing.md: `/api/v1/Pflegeeinrichtung/42` (404 → manueller Fix noetig)

Bei RESUME (status=partial): Meta-Dateien erneut lesen — kein Cache. Meta kann via `/_I_updateMeta` aktualisiert worden sein.

---

## Schritt 1: Akzeptanzkriterien-Mapping (beim ersten Aufruf)

Nur beim ERSTEN Aufruf (kein Resume). Mappe AK → Tests:

| AK# | Akzeptanzkriterium (aus Task.md) | System Test | Typ |
|-----|----------------------------------|------------|-----|
| AK1 | {User kann X tun} | ST1 | E2E |
| AK2 | {System zeigt Y an} | ST2 | E2E |
| AK3 | {Fehlerfall Z} | IT2+T5 | Abgedeckt (Unit+IT) |

Luecken-Analyse: Jedes AK braucht mindestens 1 Test (beliebige Ebene).

---

## Schritt 2: E2E Test-Strategie

| Typ | Framework | Wann |
|-----|-----------|------|
| **Cypress E2E** | Cypress + Cucumber | FE + BE zusammen |
| **API System** | HTTP Client | Nur BE |
| **.NET System** | xUnit + TestServer | BE ohne FE |

**Prinzip:** Wenige, wertvolle Tests. Nicht Business Logic duplizieren
(ist in Unit Tests). Nur "sind die Teile verbunden?" pruefen.

**Stabile Selektoren:** data-testid statt CSS-Klassen.

---

## Schritt 3: RGR-Loop (Batch-Modus)

### Fuer die naechsten BATCH_SIZE STs aus der offenen Liste:

**RED:**
1. ST aus PLAN.md nehmen
2. User-Flow definieren (Given/When/Then oder Arrange-Act-Assert)
3. Erwartung: Akzeptanzkriterium validieren
4. Test MUSS fehlschlagen (typisch: Route nicht erreichbar, Feature nicht sichtbar)

**GREEN:**
1. MINIMALE System-Konfiguration: Feature Toggle, Routing, Testdaten seeden
2. NUR Config, KEINE neue Business Logic (existiert aus Atomic + Integration)
3. Falls Code fehlt → ZURUECK zu fruehere Phase
4. ALLE Tests (Unit + Integration + System) MUESSEN gruen bleiben

**REFACTOR:**
1. Page Objects extrahieren (UI-Interaktionen kapseln)
2. Step Definitions wiederverwenden
3. Test-Data Builder Pattern
4. ALLE Tests (Unit + Integration + System) MUESSEN gruen bleiben

**CHECKPOINT (nach JEDEM gruenen ST):**
1. Manifest aktualisieren
2. SYSTEM-{SLICE}.md aktualisieren (inkrementell)

### Batch-Ende

```
Falls ALLE STs aus PLAN.md fertig:
  → Akzeptanzkriterien-Check: Alle AK durch Tests abgedeckt?
  → Integritaets-Check: Alle Unit + Integration + System Tests gruen?
  → SYSTEM.md mit status=final schreiben
  → Slice-Abschluss (siehe Schritt 5)

Falls noch STs offen:
  → SYSTEM.md mit status=partial schreiben
  → AUSGABE: "{done}/{total} STs fertig."
  → AUSGABE: "Naechster Batch: /_I_codeSystem {SLICE}"
```

---

## Schritt 4: MCP + Stagnation

| Situation | Query |
|-----------|-------|
| E2E-Unsicherheit | "system testing strategy for {scenario}" |
| Timing-Problem | "async testing for {framework}" |
| Umgebungs-Problem | "test environment for {stack}" |
| Stuck (>3 Versuche) | "getting unstuck in E2E test {problem}" |

Stagnation: >= 4 RGR ohne Fortschritt → MCP, >= 5 → /_SC_observe

---

## Schritt 5: Slice-Abschluss (nur bei status=final)

### 5.1 Checkliste

```
Unit Tests:        {N}/{N} GRUEN
Integration Tests: {N}/{N} GRUEN
System Tests:      {N}/{N} GRUEN
Akzeptanzkriterien: Alle durch Tests abgedeckt
```

### 5.2 Naechster Schritt

```
→ /_I_verify {SLICE_NAME} (SPEC ↔ Test Mapping)

Falls Mitose-Modus (CURRENT_SLICE.md existiert):
  → Nach Verify: WORKTREE VERIFIZIERT
  → Manuell: Branch mergen in Haupt-Feature-Branch

Falls weitere Slices im ARCHITECT.md:
  → /_I_cleanCodeSlice {NAECHSTER_SLICE}

Falls ALLE Slices abgeschlossen:
  → /_I_verify global (Feature-weites SPEC ↔ Test Mapping)
  → /_gap Re-Evaluation, /_model finish, Pre-PR
```

---

## Output-Format: SYSTEM-{SLICE}.md (INKREMENTELL)

**Pfad:** `.claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: system
pipeline: implementation
status: partial
tests_total: 4
tests_done: 1
next_test: ST2
batch_size: 2
batches_completed: 1
last_updated: {YYYY-MM-DD}
---

# System: {NAME} - {SLICE_NAME}

**Tests:** {done}/{total} | **Status:** partial | **Batches:** {N}
**Atomic:** ABGESCHLOSSEN ({N} Unit Tests gruen)
**Integration:** ABGESCHLOSSEN ({N} ITs gruen)

## Akzeptanzkriterien-Mapping

| AK# | Akzeptanzkriterium | Test(s) | Ebene | Status |
|-----|-------------------|---------|-------|--------|
| AK1 | {Beschreibung} | ST1 | System | GRUEN |
| AK2 | {Beschreibung} | ST2, IT1 | System+IT | OFFEN |
| AK3 | {Beschreibung} | T3, T4 | Unit | GRUEN |

## Test-Ergebnisse

| # | Test | Szenario | Status | RGR | AK |
|---|------|----------|--------|-----|----|
| ST1 | {Name} | {E2E Flow} | GRUEN | 1 | AK1 |
| ST2 | {Name} | {E2E Flow} | OFFEN | - | AK2 |

## RGR-Protokoll

### Batch 1 (ST1)
- ST1: RED weil {X} → GREEN: {Config} → REFACTOR {Z}

## Naechster Batch

ST2-ST3 (/_I_codeSystem {SLICE_NAME})
```

Wenn status=final: Ersetze "Naechster Batch" durch:
```markdown
## Slice-Abschluss

Unit Tests: {N} | Integration Tests: {N} | System Tests: {N}
Akzeptanzkriterien: Alle abgedeckt.
{SLICE_NAME} ist ABGESCHLOSSEN.

## Naechster Schritt
/_I_verify {SLICE_NAME} → dann /_I_cleanCodeSlice {NAECHSTER_SLICE} ODER /_I_verify global
```

---

## Manifest-Update (nach JEDEM gruenen ST)

```markdown
**PHASE:** _I_codeSystem {SLICE_NAME}
**PIPELINE:** Implementation
**UNIT TESTS:** {N}/{N} gruen (aus Atomic)
**INTEGRATION TESTS:** {N}/{N} gruen (aus Integration)
**SYSTEM TESTS:** {done}/{total}
**AKZEPTANZKRITERIEN:** {abgedeckt}/{gesamt}
**STATUS:** partial | final
**NAECHSTER TEST:** ST{done+1}: {Name}
**BATCH:** {N} von geschaetzt {ceil(total/batch_size)}
```

Bei status=final zusaetzlich:
```markdown
**SLICE STATUS:** ABGESCHLOSSEN
**NAECHSTER SCHRITT:** /_I_cleanCodeSlice {NEXT} ODER Feature KOMPLETT
```

---

## Qualitaetskriterien

- TDD Drei Gesetze strikt einhalten (auch bei E2E Tests!)
- RED vor GREEN vor REFACTOR (Reihenfolge!)
- NUR Konfiguration in GREEN (KEINE neue Business Logic!)
- ALLE Tests gruen nach jedem Schritt (Unit + Integration + System)
- Jedes AK hat mindestens 1 Test (beliebige Ebene)
- Wenige, wertvolle E2E Tests (nicht Business Logic duplizieren)
- Stabile Selektoren (data-testid statt CSS)
- Manifest + SYSTEM.md nach JEDEM ST aktuell (inkrementell!)
- Batch-Limit einhalten (1-2 STs, dann STOP)
- Bei Stagnation eskalieren

---

## exit_report (PFLICHT - VOR NOTIFY)

**IMMER schreiben** — egal ob status=partial oder status=final.
Schreibe diesen Block ans Ende der SYSTEM-{SLICE}.md Synthese-Datei (APPEND):

```yaml
exit_report:
  status: partial|final
  blocked_items: []          # STs die nicht bearbeitet werden konnten
  block_reason: ""           # Warum blockiert (z.B. "Kontext-Limit", "AK-Luecke")
  recommended_strategy: ""   # Empfehlung fuer naechsten Batch (z.B. "Resume ab ST2")
  context_health: ""         # low|medium|high — wie viel Kontext war noch verfuegbar
  findings: []               # Erkenntnisse ausserhalb des Scope (W{n}-Kandidaten)
```

**Regeln:**
- `findings` NIEMALS leer lassen wenn Erkenntnisse vorhanden — diese werden Parking-Lot-Kandidaten
- `context_health: low` wenn Kontext-Limit Grund fuer partial war
- `block_reason` bei `status: final` leer lassen ("")
- Falls `findings` nicht leer: APPEND an `.claude/analysis/_parking-lot.md`

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (exit_report geschrieben, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_codeSystem abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
