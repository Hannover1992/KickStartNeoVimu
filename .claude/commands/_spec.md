---
type: building-block
depends_on:
  - _model
feeds_into:
  - _gap
  - _I_orchestrate
related:
  - _taskDefinition
---

# Spezifikation: Ziel-Architektur & Anforderungen

Du erstellst die Spezifikation (SPEC) - das Leuchtfeuer fuer die Ziel-Architektur.
SPEC beschreibt WIE ES SEIN SOLL. Model beschreibt WIE ES IST.
SPEC aendert sich selten, Model aendert sich staendig.

**Status:** v3.2 (BL-065 Vault-First DirectWrite: Pre-Flight mkdir + Fail-fast, kein stiller Fallback)
**Actor:** SPEZIFIKATEUR
**Zweck:** Ziel-Architektur und Anforderungen aus Kruemmeln extrahieren

## Aufruf

```
/_spec {NAME} [easy|normal|hard]
```

- **NAME** (Pflicht): Eindeutiger Name (identisch mit /_taskDefinition und /_model)
- **Schwierigkeit** (Optional): Default `hard` bei Erstinitialisierung, `normal` bei Review

---

## VERTRAG (Pflicht-I/O)

```
+===============================================================+
|  COMMAND: /_spec {NAME} [easy|normal|hard]                     |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. {VAULT}/_manifest.md (falls vorhanden)          |
|    2. .claude/crumbs/{NAME}_crumbs.md                          |
|       --> Primaere Quelle: Kruemmel mit Architektur-Detail     |
|    2b. .claude/crumbs/{NAME}_wp_crumbs.md (BL-043, optional)   |
|       --> WP-Crumbs: Learnings aus Paper-Pipeline (DIREKT)     |
|       --> AK-04-03: Anti-Stille-Post — nicht via Model-Filter  |
|    3. {VAULT}/Task.md                                          |
|       --> Akzeptanzkriterien, Scope-Grenzen                    |
|    4. .claude/pileOfMud/* (ergaenzend, falls Crumbs duenn)     |
|       --> Architektur-Diagramme, Confluence-Exports, RFCs      |
|    5. User-Input (Architekten-Vorgaben, muendliche Spec)       |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    6. {VAULT}/.../Model/{NAME}_Model.md (falls vorhanden)      |
|       FALLBACK: .claude/models/{NAME}_Model.md                 |
|       --> IST-Zustand als Kontext (Gap-Bewusstsein)            |
|    7. Codebase (via Glob/Grep/Read)                            |
|       --> Bestehende Interfaces, Namenskonventionen             |
|    8. MCP Clean Code (Uncle Bob Queries)                       |
|       --> Architektur-Patterns, Clean Architecture Guidance    |
|                                                                |
|  SCHREIBT (Output) - abhaengig von Worker-Rolle:               |
|    Spec-Drafter D{NN}:                                         |
|      .claude/analysis/drafts/{NAME}-spec-D{NN}-{fokus}.md     |
|    Spec-Synthesist (BL-065 Vault-First DirectWrite):            |
|      # BL-065 Vault-First: Write direkt in Vault (RF-06, INV-VFC-4) |
|      vault_path = "{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md" |
|      # Pre-Flight mkdir + Fail-fast (BL-065 AK-10, INV-VFC-4)  |
|      mkdir -p {VAULT}/Backlog/{BL_SLUG}/3_Spec/    |
|      IF mkdir fehlschlaegt ODER DCS_VAULT_ROOT leer:            |
|        log_error "Vault unreachable: {vault_path}"             |
|        exit 1  # KEIN stiller Fallback (INV-VFC-2)             |
|      Schreibe {vault_path}                                      |
|      Vault-Pfad via vault-routing.json (5-stufig)              |
|                                                                |
|    # ═══ RF-05 UPDATE-GUARD (BL-050 Vault-First) ═══          |
|    # Bei Re-Synthese: created BEWAHREN, version+1,             |
|    #   updated=HEUTE                                           |
|    # Bei Erstanlage: created=HEUTE, version=1.0                |
|    vault_ziel = aufgeloester Vault-Pfad (PRIMAER oder          |
|                 FALLBACK)                                       |
|    IF DATEI_EXISTIERT(vault_ziel):                              |
|      bestehende_fm = LIES_FRONTMATTER(vault_ziel)              |
|      neue_version = bestehende_fm.version + 1                  |
|      bewahre_created = bestehende_fm.created  # NIE            |
|                        ueberschreiben                          |
|      updated = {HEUTE}                                         |
|    ELSE:                                                        |
|      neue_version = 1.0                                         |
|      bewahre_created = {HEUTE}                                  |
|      updated = {HEUTE}                                          |
|    # Schreibe Frontmatter mit bewahre_created,                 |
|    #   neue_version, updated                                   |
|                                                                |
|    Manifest (IMMER):                                           |
|      {VAULT}/_manifest.md (aktualisieren)             |
|                                                                |
|  SCHREIBT (Output) - OPTIONAL:                                 |
|    {VAULT}/_parking-lot.md (APPEND, Incidental Findings)       |
|                                                                |
|  MCP INTEGRATION (OPTIONAL, Uncle Bob Clean Code):             |
|    - mcp__cleancoder__query() fuer Architektur-Guidance        |
|    - Query Topics:                                             |
|      * "clean architecture for {domain description}"           |
|      * "interface design for {component type}"                 |
|      * "dependency inversion for {boundary}"                   |
|                                                                |
|  MCP-BREMSE:                                                   |
|    +-----------------------------------------------------+     |
|    |  easy:   MIN-Modus    --> max 1 Query,  limit=1     |     |
|    |  normal: MIDDLE-Modus --> max 3 Queries, limit=3    |     |
|    |  hard:   MAX-Modus    --> max 5 Queries, limit=5    |     |
|    |                                                     |     |
|    |  Modi:  min=1Q/1R  middle=3Q/3R  max=5Q/5R        |     |
|    +-----------------------------------------------------+     |
|                                                                |
|  PRE-CYCLE POSITION:                                           |
|    [/_taskDefinition] --> [/_spec] --> [/_model] --> Zyklus     |
|                                                                |
|  COMPACT-SICHER:                                               |
|    Spec-Datei ueberlebt /compact.                              |
|    /_model, /_SC_observe, /_I_cleanCodeArchitect lesen von     |
|    Disk.                                                       |
|                                                                |
|  ACTOR: SPEZIFIKATEUR                                          |
|    Extrahiert Ziel-Architektur aus Kruemmeln/Vorgaben.         |
|    KEINE Code-Aenderungen, KEINE Tests.                        |
|    KEINE IST-Zustand-Analyse (das macht /_model).              |
+===============================================================+
```

---

## SOURCE-PROVENANCE-PROPAGATION (BL-160 AK-5)

**INV-PROV-PROP-3:** Jeder Output-Datei MUSS source_provenance + provenance_chain Frontmatter-Block enthalten.

**Pattern:**
1. Lies Vorgaenger-Output (crumbs, Task.md). Extrahiere predecessor.source_provenance + predecessor.provenance_chain.
2. Bei Output-Schreibung ({NAME}_Spec.md):
   - source_provenance: kopiere von predecessor (gleiche Source-URL/PageId)
   - provenance_chain: haenge neuen Layer-Eintrag an (layer=3, artifact=spec_pfad, role="spec", timestamp=ISO, derived_from=[predecessor_pfad])
3. Bei mehreren Predecessors: provenance_chain.derived_from sammelt alle Vorgaenger.
4. Wenn predecessor.source_provenance FEHLT (legacy): setze source_provenance={source: "legacy_pre_BL-160", source_kind: "legacy", fetched_at: ISO_NOW}.

**Helper:** Verwende `.claude/scripts/propagate_provenance.py update <output_path>` nach Output-Schreibung — autoupdate predecessor.used_in (Hebb-bidir).

**role-Mapping fuer diesen Skill:** `"spec"`

---

## Verantwortlichkeit

Der **SPEZIFIKATEUR** Actor hat eine einzige Verantwortung:

**Ziel-Architektur und Anforderungen definieren (WIE ES SEIN SOLL)**

Was der Spezifikateur **TUT**:
- Kruemmel nach Architektur-Vorgaben durchsuchen
- Ziel-Klassen, Ziel-Interfaces, Ziel-Endpoints extrahieren
- Nicht-funktionale Anforderungen (NFR) sammeln
- Namenskonventionen und Patterns aus Vorgaben ableiten
- Akzeptanzkriterien in testbare Spezifikationen umwandeln
- Architektur-Diagramme (Mermaid) aus Kruemmeln erstellen
- Uncle Bob MCP befragen fuer Architektur-Guidance

Was der Spezifikateur **NICHT TUT**:
- IST-Zustand analysieren (das macht /_model)
- Code schreiben (das macht /_I_codeAtomic)
- Hypothesen aufstellen (das macht /_SC_hypothese)
- Model aktualisieren (das macht /_SC_modelMaintain)

---

## SPEC vs MODEL: Zwei Seiten einer Medaille

```
SPEC (/_spec)                      MODEL (/_model)
+---------------------------+      +---------------------------+
| WIE ES SEIN SOLL          |      | WIE ES IST               |
|                           |      |                           |
| - Ziel-Architektur        |      | - IST-Architektur         |
| - Erwartete Klassen       |      | - Vorhandene Klassen (W{n})|
| - Soll-Interfaces         |      | - Gefundene Interfaces    |
| - NFR (Performance, etc.) |      | - Gemessene Performance   |
| - Namenskonventionen      |      | - Beobachtete Patterns    |
| - Akzeptanzkriterien      |      | - Test-Ergebnisse         |
|                           |      |                           |
| Aendert sich SELTEN       |      | Aendert sich STAENDIG     |
| Quelle: Architekt/Crumbs  |      | Quelle: Codebase/Analyse  |
| Geschrieben: 1x am Anfang |      | Geschrieben: Jeder Zyklus |
+---------------------------+      +---------------------------+
         |                                    |
         +-----------> GAP-ANALYSE <----------+
                   (Was fehlt noch?)
```

**Kernprinzip:** SPEC ist das Leuchtfeuer. MODEL ist die Landkarte.
Die Distanz zwischen beiden ist die verbleibende Arbeit.

---

## Pipeline-Position

```
TASKDEFINITION --> **SPEC** --> MODEL --> Zyklus / Pipeline
                     |
                     v
               {NAME}_Spec.md
               (Ziel-Architektur)
```

**Prev:** /_taskDefinition (Task.md + Crumbs erstellt)
**Next:** /_model → dann /_gap (nutzt SPEC fuer Delta-Analyse)

**Wann ausfuehren:**
- NACH /_taskDefinition (Crumbs muessen existieren)
- VOR /_model (SPEC informiert die Model-Erstellung)
- OPTIONAL: Nur wenn Crumbs Architektur-Detail enthalten
- Wenn keine High-Detail-Crumbs vorhanden → direkt zu /_model

---

## Wann ist SPEC sinnvoll?

| Situation | SPEC noetig? |
|-----------|-------------|
| Crumbs enthalten Architektur-Diagramme | JA |
| Crumbs enthalten Klassen-/Interface-Vorgaben | JA |
| Crumbs enthalten NFR (Performance, Security) | JA |
| Architect hat muendliche Vorgaben gemacht | JA |
| Crumbs sind nur User Stories ohne Technik | NEIN → direkt /_model |
| Greenfield ohne Vorgaben | NEIN → direkt /_model |
| Bug-Fix ohne Architektur-Aenderung | NEIN → direkt /_model |

---

## Schritt 0: Manifest + Inputs lesen

**IMMER als Erstes:**

1. Lies `{VAULT}/_manifest.md` falls vorhanden
   - Ermittle aktuellen {NAME}
   - Lies **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab
2. Lies `{VAULT}/Task.md`
   - Akzeptanzkriterien → werden zu testbaren Spezifikationen
   - Scope-Grenzen → begrenzen die SPEC
3. Lies `.claude/crumbs/{NAME}_crumbs.md`
   - Suche nach Architektur-Vorgaben, Klassen-Definitionen, Interface-Beschreibungen
   - Identifiziere Mermaid-Diagramme mit Ziel-Architektur
   - Extrahiere NFR (Performance, Skalierbarkeit, Security)
3b. Lies `.claude/crumbs/{NAME}_wp_crumbs.md` falls vorhanden (BL-043 AK-04-03)
   - WP-Crumbs DIREKT lesen (Anti-Stille-Post INV-SP-1: nicht via Model-Filter)
   - Falls vorhanden: `INFO: WP-Crumbs geladen als Spec-Primaerquelle fuer {NAME}`
   - Falls nicht vorhanden: Kein Fehler (Graceful Degradation)
4. Falls `.claude/models/{NAME}_Model.md` existiert:
   - Lies als KONTEXT (IST-Zustand)
   - Nutze fuer Gap-Bewusstsein (was existiert bereits?)
5. Pruefe pileOfMud auf ergaenzende Architektur-Dokumente

---

## Schritt 1: Uncle Bob MCP Queries (optional)

### Query 1: Architektur-Pattern

```python
mcp__cleancoder__query(
    "clean architecture for {DOMAIN_DESCRIPTION},
     interface design, dependency inversion,
     component responsibilities"
)
```

**Ergebnis:** Architektur-Empfehlungen fuer die Ziel-Architektur

### Query 2: Namenskonventionen (bei Unsicherheit)

```python
mcp__cleancoder__query(
    "naming conventions for {COMPONENT_TYPE},
     clean code naming, intention-revealing names"
)
```

---

## Schritt 2: Ziel-Architektur extrahieren

### 2.1 Kruemmel-Analyse

Pro Kruemmel-Sektion:
1. Enthaelt Architektur-Information? → Extrahieren
2. Enthaelt Klassen-/Interface-Vorgaben? → In SPEC-Format uebersetzen
3. Enthaelt NFR? → Strukturiert dokumentieren
4. Enthaelt Sequenz-/Datenfluss-Diagramme? → In Mermaid uebertragen

### 2.2 Kategorisierung

| Kategorie | Beschreibung | Beispiel |
|-----------|-------------|---------|
| **ARCH** | Architektur-Entscheidungen | "3-Layer mit DI" |
| **COMP** | Erwartete Komponenten/Klassen | "UserService, IUserRepository" |
| **IFACE** | Erwartete Interfaces | "IFileImporter mit ImportAsync()" |
| **ENDPT** | Erwartete API-Endpoints | "POST /api/users" |
| **NFR** | Nicht-funktionale Anforderungen | "Response < 200ms" |
| **CONV** | Namenskonventionen | "{Entity}Controller, I{Service}" |
| **DATA** | Datenmodell-Vorgaben | "User hat Email, Name, Role" |
| **SEC** | Security-Anforderungen | "JWT Auth, Role-Based Access" |

### 2.3 Priorisierungs-Labels (Pflicht pro AK)

| Label | Definition | Test-Pflicht | Beispiel |
|-------|-----------|-------------|---------|
| **Core** | Zentral fuer Feature-Funktion, Kernlogik | JA (Unit+Integration) | "Service muss X berechnen" |
| **Border** | Randbereich, Streuung, Hilfs-Funktion | OPTIONAL (nur Unit) | "Logging-Format einheitlich" |
| **YAGNI** | Bewusst NICHT implementiert, mit Begruendung | NEIN | "Caching nicht noetig weil..." |

**Zuordnungs-Regeln:**
- Jeder AK bekommt GENAU EIN Label
- YAGNI erfordert IMMER eine Begruendung (1 Satz)
- Im Zweifel: Core (konservativ)

---

## Worker-Vertrag: Spec-Drafter (Architektur-Extraktion)

### Drafter-Auftrag

```
Du bist Drafter D{NN} fuer die Spezifikations-Extraktion von "{NAME}".

INPUT - LIES ZUERST DIESE DATEIEN:
  1. .claude/crumbs/{NAME}_crumbs.md
  1b. .claude/crumbs/{NAME}_wp_crumbs.md (BL-043 AK-04-03: WP-Crumbs, falls vorhanden)
     → DIREKT lesen (Anti-Stille-Post INV-SP-1) — nicht via Model-Filter
  2. {VAULT}/Task.md

AUFTRAG: {Fokus-Beschreibung}

SCHREIB-PFLICHT:
Du MUSST deine Findings in folgende Datei schreiben:
  .claude/analysis/drafts/{NAME}-spec-D{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  name: {NAME}
  phase: spec
  wave: drafts
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  agent: D{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  reads: crumbs/{NAME}_crumbs.md, Task.md
  status: final
  ---

  # Spec-Extraktion D{NN}: {Fokus-Titel}

  ## Gelesene Inputs
  - CRUMBS: {Anzahl Sektionen}, {Architektur-Dichte}
  - TASK: {Akzeptanzkriterien Anzahl}

  ## Extrahierte Architektur-Vorgaben
  | # | Kategorie | Vorgabe | Quelle (Crumb-Sektion) |
  |---|-----------|---------|------------------------|

  ## Erwartete Komponenten
  | Komponente | Typ | Layer | Beschreibung |
  |-----------|-----|-------|-------------|

  ## Erwartete Interfaces
  | Interface | Methoden | Zweck |
  |-----------|----------|-------|

  ## NFR (Nicht-funktionale Anforderungen)
  | NFR | Metrik | Grenzwert | Quelle |
  |-----|--------|-----------|--------|

  ## Offene Fragen
  {Was ist in den Kruemmeln NICHT abgedeckt?}

  ## Zusammenfassung
  {5-10 Saetze}

WICHTIG:
- EXTRAHIERE aus Kruemmeln, ERFINDE NICHT
- Wenn Kruemmel vage sind: Als "UNKLAR" markieren, nicht raten
- Quelle IMMER angeben (welche Crumb-Sektion)
- KEINE IST-Zustand-Analyse (das macht /_model)
```

### Drafter-Fokus-Bereiche

| Agent | Fokus | Aufgabe |
|-------|-------|---------|
| D01 | architektur | Architektur-Patterns, Layer, Boundaries |
| D02 | komponenten | Klassen, Interfaces, Endpoints, Datenmodell |
| D03 | qualitaet | NFR, Security, Namenskonventionen, Constraints |
| D04-D05 | (bei hard) | Tiefere Analyse, Edge Cases, Abhaengigkeiten |

---

## Worker-Vertrag: Spec-Synthese

### Worker-Vertrag PHASE 4 SPEC — STRENGE Variante (RF-SPEC-LIVE-2026-05-08, BL-161 Vorbote)

**Status:** PFLICHT-Worker-Vertrag fuer A-Pipeline Phase 4 spec seit 2026-05-08.

**Live-Validierung:** DCSRE-486 Phase 4 Spec — 14 AKs, 12 DoD, 56 Edges, 2 Spec-Open-
Assumptions mit Risk+Mitigation, 1 Synthese-Pass mit 144k Tokens / 1 tool use, Auto-
Confirm-Modus (AKs via Phase 0.5.2 schon user-bestaetigt). Worker-W7-Disziplin: Stirb-
nach-Durchlauf eingehalten trotz Task-Queue-Re-Trigger.

**Begruendung:** Quick-Win VOR BL-161 (Vault-Quality-System voll implementiert). Pflicht-
Frontmatter + Pflicht-Body + Auto-Confirm-Logik muessen direkt im Worker-Vertrag stehen.
Operator hat das bisher als ~250-Zeilen-Spawn-Prompt manuell geschrieben. Spar mehr als
1h pro Story-Pipeline.

#### AUTO-CONFIRM-LOGIK (NEU 2026-05-08)

```
IF Phase 0.5.2 findingsReview hat user_confirmed=true:
  AKs sind bereits user-bestaetigt → SKIP zweiten Review-Loop
  IF AK-Liste in Spec.md identisch mit AK-Liste aus Phase 0.5.2:
    → spec_loop_iterations = 1, auto_confirmed=true
  ELSE:
    → Force Review-Loop (AKs haben sich veraendert)
ELSE:
  Standard Review-Loop (AK-Review per Parallel-Assay → /_question pro AK)
```

#### PFLICHT-FRONTMATTER (15+ Felder strikt)

```yaml
---
type: spec
feature: {NAME}
bl-item: {BL_ID}
created: {DATE}
updated: {DATE}
status: complete | partial
phase: A-4-spec
ak_count: {N}              # kanonische User-Story-AKs
dod_count: {M}             # Definition of Done Items (Checkbox-Liste)
template_ref: {Schwester-BL-ID} | null
sources:
  - 2_Model/{NAME}_Model.md
  - 1_Task/{NAME}_Task.md
  - Findings_Assays_Konsolidiert_{date}.md
  - W_fetch/W_fetch_{date}.md
auto_confirmed: true | false
auto_confirm_rationale: "{Begruendung wenn auto_confirmed=true}"
spec_open_assumptions:
  - {ID-1}: {Beschreibung}
  - {ID-2}: {Beschreibung}
edges_count: {EC}
tags: [bl/{BL_ID}, type/spec, pipeline/A-4, scope/{SCOPE}, ...]
---
```

#### PFLICHT-BODY (11 Sektionen, Reihenfolge fix)

1. **Executive Summary** — 1 Absatz: Was, Scope, Pattern, Implementierungs-Delta
2. **Akzeptanzkriterien** (AK-1..AK-N kanonisch + AK-CTX-1..AK-CTX-K Backend-Aspekte)
3. **Architektur** (Komponenten-Stack-Diagramm + Endpoint-Vertrag mit HTTP-Status-Matrix)
4. **Implementierungs-Vorgaben** (zu bauen — DTOs, Validators, Mappers, Services, Controllers)
5. **Datenmodell** (kanonisch aus Code-Inspektion + Implementierungs-Delta)
6. **Tests (DoD)** (Unit + Integration + Tested-by aus User-Story)
7. **Annahmen** (Spec-explizit dokumentiert pro W-OPEN mit Risk + Mitigation)
8. **Out-of-Scope** (uebernommen aus Task.md)
9. **Dependencies** (andere BLs/Storys + externe Quellen)
10. **Definition of Done** (Checkbox-Liste, Implementations-Schritte)
11. **Edges-Manifest (User-Direktive — KRITISCH)** (analog Model Sektion 8)

Pro AK Pflicht-Felder:
- `Beschreibung:` aus User-Story uebernommen
- `Backend-Mapping:` welche Layer/Komponente macht's
- `W{n}-Edge:` `[[2_Model#W-AK-{N}]]`
- `Test-Strategy:` Unit / Integration / Controller-E2E
- `Status:` confirmed | open | tentative | widerlegt   # widerlegt NEU (BL-255 AK-1, 2026-06-10 —
  analoger Lifecycle zum W{n}-Automaten; transitioniert NACH Impl+Abnahme durch
  `_SDF_berater_modelSync` SCHRITT 3.5c, NIE zur Spec-Schreibzeit)

Optionale AK-Lifecycle-Felder (BL-255 AK-1, 2026-06-10 — geschrieben AUSSCHLIESSLICH von
`_SDF_berater_modelSync` SCHRITT 3.5c beim Confirm-Kollaps, nicht beim Spec-Schreiben):
- `confirmed_by:` abnahme_verdikt | experiment | user_hil
  (Whitelist-SINGLE-SOURCE: `_srs_compute.md` INV-SRS-6 — keine Kopie pflegen)
- `confirmed_at:` ISO-Date
- `verify_ref:` Pfad zum verify_report (Pflicht-Evidenz bei `abnahme_verdikt`)
- `gap_reason:` Begruendung bei GAP-Verdikt (AK bleibt/wird open, KEINE Widerlegung)

#### ANNAHMEN-SEKTION (PFLICHT, Sektion 7) — Risk + Mitigation pro W-OPEN

Pro Annahme:
- **Annahme:** {Was wird angenommen}
- **Risiko:** {Was passiert bei Falsch-Annahme}
- **Mitigation:** {Was tun wenn z.B. EM003-Konsultation Annahme widerlegt}
- **Quelle:** `[[2_Model#W-OPEN-{N}]]`

#### EDGES-MANIFEST (PFLICHT, Sektion 11) — 11 Edge-Typen (analog Model)

Tabelle ueber ALLE Wiki-Link-Edges. Verwendet die 11 Edge-Typen aus `_model.md`:
`code-grounded`, `derives-from`, `template-pattern`, `wiki-link`, `external-source`,
`rule-from`, `self-ref`, `closes`, `tentative`, `external-pending`, `template-anchor`.

Mindest-Edge-Count: `(ak_count + dod_count) * 1.5` (jede AK + DoD-Item braucht ≥1 Quelle).

#### REGELN (W7-Constraint)

- **KEIN Sub-Agent-Spawning** durch Worker
- **Vault-First Pfade:** `{bl_folder}/3_Spec/`, NICHT `.claude/analysis/`
- **Auto-Confirm respektieren:** KEIN `/_question` Skill-Aufruf wenn `auto_confirmed=true`
- **Edges-Pflicht** analog Model (RF-MODEL-EDGES)
- **Stirb-nach-Durchlauf:** kein Re-Run trotz Task-Queue-Trigger (DCSRE-486 W7-Disziplin)

#### MANIFEST-UPDATE (PFLICHT, Append)

`{bl_folder}/_manifest.md` → BERATER_OUTPUTS Sektion APPEND `### spec`:
```yaml
### spec
- status: DONE
- timestamp: {DATE}
- output_path: 3_Spec/{NAME}_Spec.md
- ak_count: {N}
- dod_count: {M}
- spec_loop_iterations: {1 wenn auto_confirmed, sonst N}
- spec_open_assumptions_count: {K}
- edges_count: {EC}
- next_consumer: phase-4k-kscore
- last_berater: spec
```

A_PIPELINE_STATE Update:
- `spec_link: "3_Spec/{NAME}_Spec.md"`

---

### Voraussetzung

Lies ALLE Dateien in `.claude/analysis/drafts/{NAME}-spec-D*.md`

### Dein Auftrag

1. Lies alle Draft-Reports
2. Konsolidiere Architektur-Vorgaben (Deduplizierung)
3. Erstelle Ziel-Architektur-Diagramm (Mermaid)
4. Strukturiere in SPEC-Format (siehe Output-Format)
5. Markiere UNKLARE Vorgaben explizit
6. Schreibe `{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md` (BL-065 Vault-First, Pre-Flight mkdir + Fail-fast)

### Schritt 2.5: Iterative AK-Generation mit CORE_AK/SUPPORT_AK/EDGE_AK + Plateau (RF-IE-003)

AKs werden iterativ extrahiert (nicht Single-Pass). Jede Runde liest
Crumbs + Task.md + bisherige AKs und extrahiert weitere. Kategorisierung
analog zu Findings: CORE_AK/SUPPORT_AK/EDGE_AK. Plateau auf CORE_AKs.

```
# ============================================================
# INVARIANTE (RF-IE-004): HARD LIMIT = 3 Runden (Safety-Stop)
#   WP-Research: AKs sind kompakter als Findings.
#   3 Runden sind ausreichend fuer AK-Extraktion (75% nach R2, Markov-Modell).
#   Stopp-Entscheidung NICHT dem LLM ueberlassen (ICLR 2024 Huang et al.).
#   Dieses Limit soll normalerweise NICHT erreicht werden (Plateau stoppt frueher).
# ============================================================
AK_HARD_LIMIT = 3
AK_PLATEAU_EPSILON = 0     # Strenger als Findings: NEW_CORE_AKS <= 0 = Plateau
AK_PLATEAU_N = 1            # Aufeinanderfolgende Runden mit NEW_CORE_AKS <= EPSILON
ak_core_plateau_count = 0   # Externer Zaehler

ak_runde = 0
alle_aks = []

WHILE ak_runde < AK_HARD_LIMIT AND (ak_runde < 1 OR ak_core_plateau_count < AK_PLATEAU_N):
  ak_runde += 1

  # Jede Runde liest Primaerquellen DIREKT (Stille-Post-Schutz):
  #   - Crumbs/{NAME}_crumbs.md + {NAME}_findings_crumbs.md
  #   - Crumbs/{NAME}_wp_crumbs.md (BL-043 AK-04-03: WP-Crumbs, falls vorhanden)
  #   - Task.md (Akzeptanzkriterien)
  #   - Bisherige AKs (Deduplizierung im Prompt)
  wp_crumbs = {NAME}_wp_crumbs.md IF DATEI EXISTIERT ELSE null  # BL-043 AK-04-03
  neue_aks = extrahiere_aks(
    crumbs={NAME}_crumbs.md,
    findings_crumbs={NAME}_findings_crumbs.md,
    wp_crumbs=wp_crumbs,                                        # BL-043 AK-04-03
    task=Task.md,
    bisherige_aks=alle_aks
  )

  # Kategorisiere jeden AK (3-stufig):
  #   CORE_AK    = zentral fuer Feature-Funktion, Kernlogik (Test-Pflicht: Unit+Integration)
  #   SUPPORT_AK = unterstuetzt CORE, gibt Kontext (Test-Pflicht: optional, nur Unit)
  #   EDGE_AK    = Randbereich, nice-to-have (Test-Pflicht: NEIN)
  FUER JEDEN ak IN neue_aks:
    ak.kategorie = CORE_AK | SUPPORT_AK | EDGE_AK

  # Plateau-Check auf CORE_AKs (strenger als Findings: EPSILON=0)
  core_ak_delta = |neue_aks.filter(kategorie == CORE_AK)|
  IF core_ak_delta <= AK_PLATEAU_EPSILON:
    ak_core_plateau_count += 1
  ELSE:
    ak_core_plateau_count = 0

  # ALLE AKs behalten (CORE + SUPPORT + EDGE)
  alle_aks.extend(neue_aks)

  support_ak_count = |neue_aks.filter(kategorie == SUPPORT_AK)|
  edge_ak_count = |neue_aks.filter(kategorie == EDGE_AK)|
  Logge: "[SPEC-AK] Runde {ak_runde}: {core_ak_delta} CORE_AK, {support_ak_count} SUPPORT_AK, {edge_ak_count} EDGE_AK, Plateau {ak_core_plateau_count}/{AK_PLATEAU_N}"

# Abschluss-Log
IF ak_runde >= AK_HARD_LIMIT:
  Logge: "[SPEC-AK] HARD LIMIT ({AK_HARD_LIMIT}) erreicht — {|alle_aks|} AKs"
ELSE:
  Logge: "[SPEC-AK] Plateau nach {ak_runde} Runden: {|alle_aks.filter(k==CORE_AK)|} CORE_AK, {|alle_aks.filter(k==SUPPORT_AK)|} SUPPORT_AK, {|alle_aks.filter(k==EDGE_AK)|} EDGE_AK"

# AKs in Spec-Datei schreiben
Schreibe in Frontmatter: `plateau_reached: true, ak_durchgaenge: {ak_runde}`
```

**Kompatibilitaet:** Die bestehenden Labels Core/Border/YAGNI (Schritt 2.3) bleiben
als Test-Pflicht-Labels erhalten. CORE_AK/SUPPORT_AK/EDGE_AK sind die ITERATIONS-Kategorie
(bestimmt Plateau). Mapping: CORE_AK → Core (Test-Pflicht JA), SUPPORT_AK → Border
(Test-Pflicht OPTIONAL), EDGE_AK → YAGNI (Test-Pflicht NEIN).

---

## Output-Format: {NAME}_Spec.md

**Pfad:** `{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md` (BL-065 Vault-First)

```markdown
---
name: {NAME}
type: spec
feature: {NAME}
bl-item: {BL_ID}
phase: spec
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: Hauptagent
date: {YYYY-MM-DD}
created: {bewahre_created}
updated: {updated}
reads: crumbs/{NAME}_crumbs.md, Task.md
status: final
version: {neue_version}
tags:
  - bl/{BL_ID}
  - type/spec
  - pipeline/pre-cycle
  - feature/{FEATURE-SLUG}
  - topic/Architecture
  - topic/Specification
keywords: [{Feature-spezifische Schlagwoerter}]
---

# Spezifikation: {NAME}

**Feature:** {Beschreibung aus Task.md}
**Datum:** {YYYY-MM-DD}
**Version:** 1.0

## 1. Ziel-Architektur

### Architektur-Typ
{Clean Architecture / Layered / Hexagonal / ...}

### Architektur-Diagramm

```mermaid
graph TD
    {Mermaid-Diagramm der Ziel-Architektur}
```

### Architektur-Entscheidungen

| # | Entscheidung | Begruendung | Quelle |
|---|-------------|-------------|--------|
| A1 | {Entscheidung} | {Warum} | {Crumb-Sektion} |

## 2. Erwartete Komponenten

### Backend

| # | Komponente | Typ | Layer | Beschreibung |
|---|-----------|-----|-------|-------------|
| C1 | {KlassenName} | Service/Controller/Repository | {Layer} | {Beschreibung} |

### Frontend

| # | Komponente | Typ | Beschreibung |
|---|-----------|-----|-------------|
| C{n} | {KomponentenName} | Component/Service/Model | {Beschreibung} |

### Datenbank

| # | Entity | Felder | Beschreibung |
|---|--------|--------|-------------|
| C{n} | {EntityName} | {Key Fields} | {Beschreibung} |

## 3. Erwartete Interfaces

| # | Interface | Methoden | Zweck | Layer-Boundary |
|---|-----------|----------|-------|---------------|
| I1 | I{ServiceName} | {Method1}, {Method2} | {Zweck} | {z.B. Service->Repository} |

## 4. Erwartete API-Endpoints

| # | Methode | Pfad | Request | Response | Beschreibung |
|---|---------|------|---------|----------|-------------|
| E1 | {GET/POST/...} | {/api/...} | {Body/Params} | {Response-Typ} | {Beschreibung} |

## 5. Nicht-funktionale Anforderungen (NFR)

| # | Kategorie | Anforderung | Metrik | Grenzwert |
|---|-----------|-------------|--------|-----------|
| N1 | Performance | {Beschreibung} | {z.B. Response Time} | {z.B. < 200ms} |
| N2 | Security | {Beschreibung} | {Metrik} | {Grenzwert} |

## 6. Namenskonventionen

| Typ | Konvention | Beispiel |
|-----|-----------|---------|
| Controller | {Entity}Controller | UserController |
| Service | {Entity}Service / I{Entity}Service | UserService / IUserService |
| Repository | {Entity}Repository / I{Entity}Repository | UserRepository |
| DTO | {Entity}Dto / {Entity}ResponseDto | UserDto |
| Component | {feature}-{type}.component.ts | user-detail.component.ts |

## 7. Datenfluss (Sequenz)

```mermaid
sequenceDiagram
    {Mermaid-Sequenzdiagramm des Haupt-Datenflusses}
```

## 8. Akzeptanzkriterien (Testbar)

| # | AK | Testbare Formulierung | Typ | Label |
|---|----|--------------------|-----|-------|
| AK1 | {aus Task.md} | Given {X} When {Y} Then {Z} | {Unit/Integration/E2E} | {Core/Border/YAGNI} |

## 9. Offene Fragen / Unklarheiten

| # | Frage | Kontext | Kritikalitaet |
|---|-------|---------|--------------|
| Q1 | {Was ist unklar?} | {Wo kam es her?} | HOCH/MITTEL/NIEDRIG |

## 10. Zusammenfassung

{3-5 Saetze: Was soll gebaut werden? Welche Architektur? Welche Kern-Interfaces?}

Naechster Schritt: /_model {NAME} → dann /_gap {NAME} (Delta: SPEC vs IST)
```

---

## Wer liest die SPEC?

| Command | Wie SPEC gelesen wird |
|---------|----------------------|
| **/_model** | Kontext: SOLL als Referenz beim IST-Aufbau |
| **/_gap** | **PRIMAER**: Delta-Analyse SPEC (SOLL) vs MODEL (IST) → Was fehlt? |
| **/_SC_observe** | Fokus-Orientierung: Welche SPEC-Komponenten beobachten? |
| **/_I_cleanCodeArchitect** | Slice-Dekomposition: SPEC als Architektur-Vorgabe |
| **/_I_codeAtomic** | **NICHT** (nur in Finish-Phase als Validierung) |
| **/_SC_qualityGate** | Feature-Abschluss: Alle SPEC-Komponenten implementiert? |

---

## SPEC-Pflege (selten)

SPEC aendert sich NUR bei:
1. Architekt aendert Vorgaben
2. Neue Anforderungen kommen hinzu
3. NFR werden angepasst

**Bei Aenderung:** Neue Version (`version: 1.1`), Aenderungs-Log im Dokument.
**SPEC wird NICHT bei jedem Zyklus aktualisiert** (im Gegensatz zu Model).

---

## Ablauf: Easy

```
             +------------------+
SYNTHESE     |  DU, Hauptagent  |  --LIEST--> CRUMBS + TASK + pileOfMud
             |                  |  --SCHREIBT--> specs/{NAME}_Spec.md
             +------------------+
```

Keine Drafts noetig. Direkte Extraktion und Strukturierung.

---

## Qualitaetskriterien

- Jede Vorgabe hat eine **Quelle** (Crumb-Sektion oder User-Input)
- UNKLARE Vorgaben sind als "UNKLAR" markiert (nicht geraten!)
- Mindestens 1 Architektur-Diagramm (Mermaid)
- Alle Akzeptanzkriterien aus Task.md in testbarer Form
- Namenskonventionen dokumentiert (falls in Kruemmeln vorhanden)
- SPEC enthaelt KEINE IST-Zustand-Analyse (das macht /_model)
- SPEC enthaelt KEINEN Code (das machen die I_ Phasen)

---

## Dateisystem-Erweiterung

```
.claude/
+-- Task.md                        <-- Aufgaben-Definition
+-- specs/                         <-- NEU: Spezifikationen
|   +-- {NAME}_Spec.md            <-- Ziel-Architektur (SOLL)
+-- models/                        <-- Persistente Models
|   +-- {NAME}_Model.md           <-- IST-Zustand
+-- crumbs/                        <-- Strukturierte Kruemmel
|   +-- {NAME}_crumbs.md
+-- analysis/
    +-- drafts/
    |   +-- {NAME}-spec-D*.md      <-- NEU: Spec-Drafts
    +-- ...
```

---

## Manifest-Update nach Abschluss

```markdown
**PHASE:** _spec abgeschlossen
**NAECHSTER SCHRITT:** /_model {NAME}

### Spec - {Datum}
- [x] {VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md (v{VERSION})
- [x] Architektur-Vorgaben: {N} extrahiert
- [x] Erwartete Komponenten: {N} (BE: {n}, FE: {n}, DB: {n})
- [x] Interfaces: {N}
- [x] Endpoints: {N}
- [x] NFR: {N}
- [x] Offene Fragen: {N}
```

---

## Kompakt-Sicherheit

Nach Command-Abschluss:
- State: {NAME}_Spec.md geschrieben
- Resume: /_model kann Spec.md lesen

---

## Obsidian-Tags

```yaml
tags:
  - type/spec
  - pipeline/pre-cycle
  - feature/{FEATURE-SLUG}
  - topic/Architecture
  - topic/Specification
pipeline-position: spec
prev: [[_taskDefinition]]
next: [[_model]]
```

---

## Siehe auch

- [[_taskDefinition]] - Vorheriger Schritt (Crumbs erstellen)
- [[_model]] - Naechster Schritt (IST-Zustand aufbauen)
- [[gap]] - Gap-Analyse: Delta SPEC (SOLL) vs MODEL (IST)
- [[I_cleanCodeArchitect]] - Nutzt GAP + SPEC fuer Slice-Dekomposition
- [[SC_observe]] - Nutzt GAP fuer gerichtete Observation

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_spec abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
