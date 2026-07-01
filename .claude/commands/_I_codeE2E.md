---
type: building-block
---

# /_I_codeE2E

**Status:** v1.1 (BL-065: Vault-First DirectWrite, Hybrid-Marker ersetzt)
**Actor:** E2E-TESTER
**Zweck:** E2E Akzeptanztests aus Customer-Perspektive (Batch: 1 Test pro Aufruf)

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_codeE2E {SLICE_NAME}                             |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. {VAULT}/_manifest.md                            |
|    2. .claude/CURRENT_SLICE.md (falls Mitose-Worktree)        |
|    3. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md            |
|       → E2E Test-Liste (E2E1, E2E2, ...)                     |
|       → User Journeys (vollstaendige Workflows)               |
|    4. .claude/analysis/synthese/{NAME}-FULLSYSTEM-{SLICE}.md   |
|       → VORAUSSETZUNG: status=final (alle FSTs gruen)         |
|    5. .claude/analysis/synthese/{NAME}-E2E-{SLICE}.md          |
|       → RESUME: Falls vorhanden, lies status + done Tests     |
|    6. {VAULT}/Task.md                                          |
|       → Akzeptanzkriterien (E2E validiert diese DIREKT!)      |
|    7. .claude/meta/implementation/stage_5.md                   |
|       → Stufen-Metadaten (Infrastruktur, Constraints)         |
|    8. Codebase (Production Code, E2E-Test-Suite)              |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    9. {META}/implementation/e2e.md                       |
|       → Framework-Konfiguration (Cypress/Playwright/etc.)     |
|       → Falls fehlt: Framework aus stage_5.md oder Codebase   |
|   10. {META}/implementation/routing.md                   |
|       → API-Route-Naming                                       |
|   11. {META}/implementation/auth.md                      |
|       → Auth-Flows fuer E2E                                    |
|   12. {META}/implementation/testing.md                   |
|       → Test-Pattern, Data-Builder                             |
|       → Falls fehlt: WARN + CONTINUE (kein ABORT)             |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. Code: E2E Tests (Framework lt. e2e.md oder stage_5.md)  |
|    2. Vault-First (BL-065)                                     |
|       Implementation-Logs werden DIREKT in den Vault geschrieben:|
|       {VAULT}/Backlog/{BL_SLUG}/Implementation/{NAME}-E2E-{SLICE}.md |
|       Status (partial/final) wird im FRONTMATTER der Log-Datei |
|       kodiert, NICHT ueber Pfad-Unterschied.                   |
|       Pre-Flight-Check (verbindlich, RF-06):                   |
|       mkdir -p {VAULT}/Backlog/{BL_SLUG}/Implementation/ |
|       if [ $? -ne 0 ] || [ -z "$DCS_VAULT_ROOT" ]; then       |
|         log_error "Vault unreachable: ..."                     |
|         exit 1                                                 |
|       fi                                                       |
|       Schreibpfad: {VAULT}/Backlog/{BL_SLUG}/Implementation/{NAME}-E2E-{SLICE}.md |
|       Frontmatter: status: partial|final (Feld, nicht Pfad).  |
|       INKREMENTELL (status=partial): lokal zwischenspeichern   |
|       .claude/analysis/synthese/{NAME}-E2E-{SLICE}.md          |
|       → status: partial (N/M) oder final (M/M)               |
|    3. {VAULT}/_manifest.md (nach JEDEM E2E update)   |
|                                                                |
|  SCHREIBT (Output) - OPTIONAL:                                 |
|    {VAULT_ROOT}/Libraries/PatternLibrary/_index.md  (VAULT-ONLY, INV-PL-VAULT-1)                       |
|    {VAULT}/_parking-lot.md (APPEND bei Findings)     |
|                                                                |
|  MCP: mcp__cleancoder__query() NUR bei Unsicherheit           |
|    MIN-Modus: max 1 Query, limit=1                            |
|                                                                |
|  PFLICHT-HiL-CHECK:                                            |
|    VOR dem ersten E2E-Test: HiL-Bestaetigung einholen         |
|    "E2E-Tests starten. Framework: {framework}. Fortfahren?"   |
|    Grund: E2E ist teuerste Stufe, Framework muss korrekt sein |
|                                                                |
|  BATCH-MODUS:                                                  |
|    Bearbeite 1 Test pro Aufruf, dann STOPPE.                  |
|    E2E Tests sind am teuersten → kleinste Batches.            |
|    Resume liest E2E.md → weiss wo weitermachen.               |
|                                                                |
|  PIPELINE:                                                     |
|    [/_I_codeFullSystem] → [/_I_codeE2E] →                     |
|    [/_I_verify] → [FEATURE VERIFIZIERT]                        |
|                                                                |
|  VORAUSSETZUNG:                                                |
|    FULLSYSTEM-{SLICE}.md existiert mit status=final           |
|    (alle Unit + Integration + System + FullSystem Tests gruen)|
|                                                                |
|  ERGEBNIS:                                                     |
|    E2E-{SLICE}.md (status=partial oder final)                 |
|    partial → User ruft erneut auf                             |
|    final   → Abnahme-Sequenz starten                         |
|                                                                |
|  ABNAHME-SEQUENZ (nach status=final):                          |
|    → Pattern-Konsolidierung (experimental → PROVEN)           |
|    → /_AC_orchestrate (architektonische Abnahme)              |
|    → /_Pre_PR_orchestrate (prePR)                             |
|    → Manual HiL Abnahme                                        |
|    → /_R_orchestrate (Uncle Bob Review)                       |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**E2E-TESTER:** E2E Akzeptanztests aus Customer-Perspektive.

**TUT:** E2E Tests schreiben die Akzeptanzkriterien DIREKT validieren,
vollstaendige User Journeys testen, Framework lt. e2e.md/stage_5.md nutzen,
Abnahme-Sequenz referenzieren nach Abschluss.

**NICHT:** Unit Tests, Integration Tests, System Tests, Business Logic aendern.

**Eskalation:** Bei 5+ RGR ohne Fortschritt → /_SC_observe

---

## Schritt 0: Resume-Check + Voraussetzungen

### 0.1 Mitose-Check

```
Falls .claude/CURRENT_SLICE.md existiert:
  → {SLICE_NAME} aus CURRENT_SLICE.md verwenden
  → NUR an diesem Slice arbeiten
```

### 0.2 FullSystem-Phase pruefen

```
Lies FULLSYSTEM-{SLICE}.md → Pruefe Frontmatter: status
  → Falls status != final:
      ABBRUCH: "/_I_codeFullSystem {SLICE} muss zuerst abgeschlossen werden"
  → Falls status = final: OK, weiter
```

### 0.3 Resume-Check

```
Falls .claude/analysis/synthese/{NAME}-E2E-{SLICE}.md existiert:
  → Lies Frontmatter: status, tests_done, tests_total, next_test
  → Falls status=final:
      AUSGABE: "E2E Phase bereits abgeschlossen."
      → STOP
  → Falls status=partial:
      AUSGABE: "Resume: {tests_done}/{tests_total} E2E-Tests fertig."
      AUSGABE: "Starte bei {next_test}."
      → Setze fort
Falls NICHT existiert:
  → Neuer Start bei E2E1
```

### 0.4 Framework-Erkennung

```
1. Lies {META}/implementation/e2e.md (falls vorhanden)
   → Framework, Config, Selektoren
2. Falls NICHT vorhanden:
   → Lies stage_5.md → testbefehl
   → Falls testbefehl == "TBD":
       → Suche in Codebase: package.json (cypress/playwright),
         *.spec.ts, cypress.config.*, playwright.config.*
       → Falls gefunden: Framework ableiten
       → Falls NICHT gefunden:
           HiL: "Kein E2E-Framework erkannt. Bitte angeben:
                 (1) Cypress  (2) Playwright  (3) Anderes  (4) SKIP E2E"
```

### 0.5 PFLICHT-HiL-Check (NUR beim ersten Aufruf, kein Resume)

```
Falls NICHT Resume (status != partial):
  HiL: "E2E-Tests starten.
        Framework: {erkanntes_framework}
        Stufe: 5 (E2E Akzeptanztests)
        Batch-Size: 1 Test pro Aufruf
        Fortfahren? [JA] [NEIN] [FRAMEWORK AENDERN]"
  → Falls NEIN: STOP
  → Falls FRAMEWORK AENDERN: Framework neu setzen, dann weiter
```

### 0.6 Standard-Inputs

1. Lies `plans/{NAME}-{SLICE}-PLAN.md` → E2E-Liste, User Journeys
2. Lies `Task.md` → Akzeptanzkriterien (E2E validiert diese DIREKT)
3. Lies `FULLSYSTEM-{SLICE}.md` → Gesamtsystem-Test-Ergebnisse
4. Lies `stage_5.md` → Infrastruktur-Anforderungen
5. Lies `_pattern-library.md` (falls vorhanden)
6. Bestimme BATCH_SIZE: 1 (E2E Tests sind am teuersten)

---

### 0.7 Optional-Input: Implementation Meta

Fuer relevante Topics laden (falls Datei existiert):

| Topic | Prioritaet | Wann laden |
|-------|-----------|------------|
| `e2e.md` | KRITISCH | Framework, Config, Selektoren |
| `routing.md` | HOCH | Tests mit HTTP-Calls |
| `auth.md` | HOCH | Tests mit Auth-Flows |
| `testing.md` | MITTEL | Test-Pattern, Data-Builder |

Falls Datei nicht existiert:
  - WARN: "`{META}/implementation/{topic}.md` nicht gefunden — weiter ohne"
  - CONTINUE (kein ABORT)

Bei RESUME (status=partial): Meta-Dateien erneut lesen — kein Cache.

---

## Schritt 1: AK-Mapping (beim ersten Aufruf)

Nur beim ERSTEN Aufruf (kein Resume). Mappe AK → E2E Tests:

| AK# | Akzeptanzkriterium (aus Task.md) | E2E Test | User Journey |
|-----|----------------------------------|----------|-------------|
| AK1 | {User kann X tun} | E2E1 | {Vollstaendiger Flow} |
| AK2 | {System zeigt Y an} | E2E2 | {Vollstaendiger Flow} |

Jedes AK MUSS durch mindestens 1 E2E-Test abgedeckt sein.
E2E-Tests sind die DIREKTE Validierung der Akzeptanzkriterien.

---

## Schritt 2: RGR-Loop (Batch-Modus)

### Fuer den naechsten BATCH_SIZE E2E aus der offenen Liste:

**RED:**
1. E2E aus PLAN.md nehmen
2. User Journey definieren (Given/When/Then — Customer-Perspektive)
3. Erwartung: Akzeptanzkriterium DIREKT validieren
4. Echtes System — keine Mocks, keine Isolation (lt. stage_5.md)
5. Test MUSS fehlschlagen

**GREEN:**
1. MINIMALE Anpassung: Testdaten seeden, Config, Wiring
2. NUR Config, KEINE neue Business Logic
3. Falls Code fehlt → ZURUECK zu fruehere Phase
4. ALLE Tests (Unit + Integration + System + FullSystem + E2E) MUESSEN gruen bleiben

**REFACTOR:**
1. Page Objects extrahieren (UI-Interaktionen kapseln)
2. Test-Data Builder Pattern anwenden
3. Step Definitions wiederverwenden
4. Stabile Selektoren (data-testid statt CSS)
5. ALLE Tests MUESSEN gruen bleiben

**CHECKPOINT (nach JEDEM gruenen E2E):**
1. Manifest aktualisieren
2. E2E-{SLICE}.md aktualisieren (inkrementell)

### Batch-Ende

```
Falls ALLE E2E-Tests aus PLAN.md fertig:
  → AK-Abdeckungs-Check: Alle AK durch E2E-Tests abgedeckt?
  → Integritaets-Check: Alle Tests aller Stufen gruen?
  → E2E.md mit status=final schreiben
  → AUSGABE: "E2E Phase abgeschlossen ({M}/{M} Tests)."
  → AUSGABE: "Alle Akzeptanzkriterien durch E2E validiert."
  → AUSGABE: "Abnahme-Sequenz: Pattern-Konsolidierung → AC → Pre_PR → HiL → Review"

Falls noch E2E-Tests offen:
  → E2E.md mit status=partial schreiben
  → AUSGABE: "{done}/{total} E2E-Tests fertig."
  → AUSGABE: "Naechster Batch: /_I_codeE2E {SLICE}"
```

---

## Schritt 3: MCP + Stagnation

| Situation | Query |
|-----------|-------|
| E2E-Framework-Unsicherheit | "e2e testing with {framework} for {scenario}" |
| Selektor-Problem | "stable selectors for {framework}" |
| Async-Timing | "async wait strategies {framework}" |
| Stuck (>3 Versuche) | "getting unstuck in e2e test {problem}" |

Stagnation: >= 4 RGR ohne Fortschritt → MCP, >= 5 → /_SC_observe

---

## Output-Format: E2E-{SLICE}.md (INKREMENTELL)

**Pfad:** `.claude/analysis/synthese/{NAME}-E2E-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: e2e
pipeline: implementation
status: partial
tests_total: 3
tests_done: 1
next_test: E2E2
batch_size: 1
batches_completed: 1
framework: {cypress|playwright|other}
last_updated: {YYYY-MM-DD}
---

# E2E: {NAME} - {SLICE_NAME}

**Tests:** {done}/{total} | **Status:** partial | **Batches:** {N}
**Framework:** {framework}
**Atomic:** ABGESCHLOSSEN ({N} Unit Tests gruen)
**Integration:** ABGESCHLOSSEN ({N} ITs gruen)
**System:** ABGESCHLOSSEN ({N} STs gruen)
**FullSystem:** ABGESCHLOSSEN ({N} FSTs gruen)

## Akzeptanzkriterien-Mapping

| AK# | Akzeptanzkriterium | E2E Test | User Journey | Status |
|-----|-------------------|----------|-------------|--------|
| AK1 | {Beschreibung} | E2E1 | {Journey} | GRUEN |
| AK2 | {Beschreibung} | E2E2 | {Journey} | OFFEN |

## Test-Ergebnisse

| # | Test | User Journey | Status | RGR | AK |
|---|------|-------------|--------|-----|----|
| E2E1 | {Name} | {Journey} | GRUEN | 1 | AK1 |
| E2E2 | {Name} | {Journey} | OFFEN | - | AK2 |

## RGR-Protokoll

### Batch 1 (E2E1)
- E2E1: RED weil {X} → GREEN: {Config} → REFACTOR {Z}

## Naechster Batch

E2E2 (/_I_codeE2E {SLICE_NAME})
```

Wenn status=final: Ersetze "Naechster Batch" durch:
```markdown
## Abnahme-Sequenz

Alle Akzeptanzkriterien durch E2E validiert.
{SLICE_NAME} E2E ist ABGESCHLOSSEN.

Naechste Schritte:
1. Pattern-Konsolidierung (experimental → PROVEN)
2. /_AC_orchestrate (architektonische Abnahme)
3. /_Pre_PR_orchestrate (prePR)
4. Manual HiL Abnahme
5. /_R_orchestrate (Uncle Bob Review)
```

---

## Manifest-Update (nach JEDEM gruenen E2E)

```markdown
**PHASE:** _I_codeE2E {SLICE_NAME}
**PIPELINE:** Implementation
**UNIT TESTS:** {N}/{N} gruen
**INTEGRATION TESTS:** {N}/{N} gruen
**SYSTEM TESTS:** {N}/{N} gruen
**FULLSYSTEM TESTS:** {N}/{N} gruen
**E2E TESTS:** {done}/{total}
**AKZEPTANZKRITERIEN:** {abgedeckt}/{gesamt}
**STATUS:** partial | final
**NAECHSTER TEST:** E2E{done+1}: {Name}
**BATCH:** {N} von geschaetzt {ceil(total/batch_size)}
```

---

## Qualitaetskriterien

- TDD Drei Gesetze einhalten (auch bei E2E!)
- RED vor GREEN vor REFACTOR (Reihenfolge!)
- NUR Config in GREEN (KEINE neue Business Logic!)
- ALLE Tests gruen nach jedem Schritt (alle 5 Stufen)
- Jedes AK hat mindestens 1 E2E-Test
- E2E-Tests validieren Akzeptanzkriterien DIREKT
- Keine Mocks — echtes System lt. stage_5.md
- Stabile Selektoren (data-testid statt CSS)
- Framework-agnostisch — Framework lt. e2e.md oder stage_5.md
- Manifest + E2E.md nach JEDEM E2E aktuell (inkrementell!)
- Batch-Limit einhalten (1 E2E, dann STOP)
- Bei Stagnation eskalieren
- PFLICHT-HiL vor erstem E2E-Test

---

## exit_report (PFLICHT - VOR NOTIFY)

**IMMER schreiben** — egal ob status=partial oder status=final.
Schreibe diesen Block ans Ende der E2E-{SLICE}.md Synthese-Datei (APPEND):

```yaml
exit_report:
  status: partial|final
  blocked_items: []          # E2E-Tests die nicht bearbeitet werden konnten
  block_reason: ""           # Warum blockiert (z.B. "Framework nicht konfiguriert")
  recommended_strategy: ""   # Empfehlung fuer naechsten Batch
  context_health: ""         # low|medium|high
  findings: []               # Erkenntnisse ausserhalb des Scope
```

**Regeln:**
- `findings` NIEMALS leer lassen wenn Erkenntnisse vorhanden
- `context_health: low` wenn Kontext-Limit Grund fuer partial war
- `block_reason` bei `status: final` leer lassen ("")
- Falls `findings` nicht leer: APPEND an `{VAULT}/_parking-lot.md`

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (exit_report geschrieben, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_codeE2E abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
