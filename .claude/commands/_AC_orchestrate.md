# /_AC_orchestrate - Architecture Correctness Analyse

```yaml
status: active
version: 1.0.0
created: 2026-02-27
updated: 2026-02-27
op: ArchitectureCorrectness
phase: Post-Implementation
type: orchestration
chain_position: post-I
difficulty_scaling: true
team_based: true
changelog: |
  v1.0: MVP. 4-Phasen-Flow (SCOPE-FAN_OUT, FAN_OUT, FAN_IN, OUTPUT).
        Konsumiert be-*.md (5 Schichten, 20 AK-Regeln).
        KURZLEBIG_PROMPT fuer AC-Worker + FAN_IN-Agent.
        Manifest-Integration (ac_*-Felder).
        Skalierung easy/normal/hard.
```

---

```
+======================================================================+
| VERTRAG: /_AC_orchestrate                                             |
+======================================================================+
|                                                                        |
| LIEST:                                                                 |
|   .claude/analysis/_manifest.md             (NAME, Phase, Kontext)    |
|   .claude/meta/architekturKonventionen/be-*.md  (5 Schicht-Dateien)  |
|   git diff / git status                     (geaenderte Dateien)      |
|   (optional) .claude/meta/codeKonvention/architektur.md              |
|                                                                        |
| SCHREIBT:                                                              |
|   .claude/analysis/_manifest.md             (ac_*-Felder Update)     |
|                                                                        |
| AUSGABEN DURCH WORKER:                                                 |
|   .claude/analysis/findings/{NAME}-AC-{SCHICHT}-{TS}.md              |
|     (pro aktive Schicht 1 Finding-Report, via AC-Worker)              |
|   .claude/analysis/findings/{NAME}-AC-SUMMARY-{TS}.md                |
|     (konsolidierter Gesamt-Report, via FAN_IN-Agent)                  |
|                                                                        |
| HAUPTPRODUKT:                                                          |
|   {NAME}-AC-SUMMARY-{TS}.md + Manifest ac_*-Felder                   |
|   (Zentrale AC-Befund-Liste fuer IMPLEMENT-Entscheidung)              |
+======================================================================+
```

---

## Aufruf

```
/_AC_orchestrate [name] [scope] [difficulty] [ceiling] [floor]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `name` | (PFLICHT) | String | Feature-Name (Artefakt-Naming) |
| `scope` | diff | diff, full | diff = git-geaenderte Dateien; full = gesamte Codebase |
| `difficulty` | normal | easy, normal, hard | Parallelisierung der AC-Worker |
| `ceiling` | sonnet | haiku, sonnet, opus | Modell fuer FAN_IN/OUTPUT |
| `floor` | haiku | haiku, sonnet | Modell fuer FAN_OUT Worker |

**Beispiele:**
```
/_AC_orchestrate DCSRE-93                           → diff, normal, sonnet, haiku
/_AC_orchestrate DCSRE-93 full hard opus haiku      → full scan, alle 5 Schichten
/_AC_orchestrate QuickCheck diff easy haiku haiku    → 1 Agent, alles haiku
```

---

## Skalierung — 3-Wellen-9-5-1

| Schwierigkeit | Explorer (W1) | Drafter (W2) | Synthese (W3) |
|---|---|---|---|
| **hard** | 5 AC-Worker {floor} PARALLEL | 3 Befund-Analysten {middle} PARALLEL | 1x FAN_IN {ceiling} |
| **normal** | 3 AC-Worker {floor} PARALLEL | 2 Befund-Analysten {middle} PARALLEL | 1x FAN_IN {ceiling} |
| **easy** | TL-only (kein Sub-Agent) | [uebersprungen] | [uebersprungen] |

(easy=TL-only ist Budget-effizient und ausreichend fuer kleine Aenderungen)

**Modell-Zuordnung (nach GLOBAL_CEILING):**
- ceiling=opus:   floor=haiku, middle=sonnet, ceiling=opus
- ceiling=sonnet: floor=haiku, middle=haiku,  ceiling=sonnet
- ceiling=haiku:  floor=haiku, middle=haiku,  ceiling=haiku

**Wellen-Prinzip:** Alle Worker einer Welle laufen PARALLEL (run_in_background: true).
Welle 2 (Drafter) startet erst nach Abschluss ALLER Welle-1-Worker.
Welle 3 (Synthese) startet erst nach Abschluss ALLER Welle-2-Worker.

**Priorisierung bei normal (3 aus 5 Schichten fuer Explorer):**
Top-3 aktive Schichten nach Datei-Anzahl in SCOPE_BUCKET.
Ties: niedrigerer ac-layer = hoehere Prioritaet.
Drafter (W2) folgt der Schicht-Aufteilung der Explorer.

---

## GLOBALE PARAMETER (/_param Override)

Lies `.claude/analysis/_manifest.md` und suche nach GLOBAL_* Feldern.
Falls gesetzt, ueberschreiben sie die lokalen Parameter-Defaults:

| Manifest-Feld | Wirkung |
|---|---|
| `GLOBAL_DIFFICULTY` | Ueberschreibt lokalen `difficulty` Default |
| `GLOBAL_CEILING` | Kappt lokales ceiling: `effektiv = min(lokal, GLOBAL_CEILING)` |
| `GLOBAL_FLOOR` | Hebt lokalen floor an: `effektiv = max(lokal, GLOBAL_FLOOR)` |

**Berechnung:**
Hierarchie: opus=3, sonnet=2, haiku=1
IF GLOBAL_DIFFICULTY gesetzt UND != "(nicht gesetzt)": difficulty = GLOBAL_DIFFICULTY
IF GLOBAL_CEILING gesetzt UND != "(nicht gesetzt)":    ceiling = min(ceiling, GLOBAL_CEILING)
IF GLOBAL_FLOOR gesetzt UND != "(nicht gesetzt)":      floor = max(floor, GLOBAL_FLOOR)
Validierung: ceiling >= floor (sonst ceiling = floor + Warning ausgeben)
middle = sonnet wenn ceiling=opus, haiku wenn ceiling=sonnet, haiku wenn ceiling=haiku

**Falls KEINE GLOBAL_* Felder gesetzt:** Lokale Defaults gelten unveraendert.

---

## PHASE 1: SCOPE-FAN_OUT (Team Lead, kein Agent-Spawn)

**Zweck:** Scope definieren — welche Dateien, welche Schicht.

### 1.1 Scope ermitteln

```bash
# scope=diff (Default):
git diff HEAD~1..HEAD --name-only → {CHANGED_FILES}

# scope=full:
find . -name "*.cs" -not -path "*/obj/*" -not -path "*/bin/*" → {ALL_CS_FILES}
```

### 1.2 Schicht-Erkennung (3-Stufen-Heuristik)

Fuer jede Datei die Schicht bestimmen:

```
STUFE 1 (Dateipfad — Prioritaet HOCH, Confidence 95%):
  Lade be-*.md `dateipfad-pattern` aus YAML-Frontmatter:
  BE-CORE:  **/Services/**/*Service.cs, **/Providers/**/*Provider.cs, **/Domain/**/*Extensions.cs
  BE-DTO:   **/DTOs/**/*Dto.cs, **/DTOs/**/*ReadDto.cs, **/DTOs/**/*WriteDto.cs
  BE-MAP:   **/Mappers/**/*Mapper.cs, **/Mappers/**/*Profile.cs, **/*MappingProfile.cs
  BE-CONT:  **/Controllers/**/*Controller.cs
  BE-MID:   **/Middleware/**/*.cs, **/Interceptors/**/*.cs, **/Filters/**/*.cs
  Mehrfach-Match → primaere Schicht nach ac-layer (niedrigster Wert)

STUFE 2 (Datei-Suffix — Prioritaet MITTEL, Confidence 70%):
  Nur wenn Stufe 1 kein Match.
  *Service.cs/*Provider.cs → BE-CORE | *Dto.cs → BE-DTO
  *Mapper.cs/*Profile.cs → BE-MAP | *Controller.cs → BE-CONT
  *Middleware.cs/*Filter.cs → BE-MID

STUFE 3 (Namespace — Prioritaet NIEDRIG, Confidence 60%):
  Nur wenn Stufe 1+2 kein Match. Lese be-*.md `namespace-indikatoren`:
  VDEK.DCSP.Domain/Application.* → BE-CORE | *.Dto/Common.Dto → BE-DTO
  *.Mapping → BE-MAP | VDEK.DCSP.WebApi.* (ohne Middleware) → BE-CONT
  *.WebApi.Middleware/Filters → BE-MID

FALLBACK: Kein Match → UNCLASSIFIED (notieren, nicht analysiert)
```

### 1.3 Scope-Buckets + Skalierung

```
SCOPE_BUCKET = {
  "BE-CORE": [dateien...], "BE-DTO": [...], "BE-MAP": [...],
  "BE-CONT": [...], "BE-MID": [...], "UNCLASSIFIED": [...]
}

Aktive Schichten = Schichten mit >= 1 Datei im Bucket.

IF difficulty == easy:   → TL-only (kein Sub-Agent-Spawn, TL fuehrt KURZLEBIG_PROMPT_AC_EASY direkt aus)
IF difficulty == normal: → Min(3, len(aktive_schichten)) AC-Worker PARALLEL (Welle 1)
IF difficulty == hard:   → Min(5, len(aktive_schichten)) AC-Worker PARALLEL (Welle 1)

Fallback 0 aktive Schichten:
  → CLEAN-Status melden, kein Agent-Spawn, ac_findings_count=0, ac_status="CLEAN"
```

---

## PHASE 2: Welle 1 (Explorer) — Schicht-Scanner auf {floor} (FAN_OUT, PARALLEL)

**Zweck:** Pro aktive Schicht: Code-Dateien gegen AK-Regeln pruefen, Finding-Report schreiben.

Nach Schwierigkeit:
- **easy:** [Uebersprungen — TL fuehrt AC-Scan direkt als TL-only durch, siehe KURZLEBIG_PROMPT_AC_EASY]
- **normal:** 3 AC-Worker parallel {floor}
- **hard:** 5 AC-Worker parallel {floor}

Team Lead spawnt pro aktive Schicht 1 AC-Worker (nur bei normal/hard):

```
Task tool:
  name: "ac-{name}-{SCHICHT}"
  subagent_type: "general-purpose"
  model: "{floor}"
  team_name: "ac-{name}"
  mode: "bypassPermissions"
  run_in_background: true              # ALLE FAN_OUT-Worker parallel
  prompt: [AC-WORKER KURZLEBIG_PROMPT, siehe unten]
```

**Finding-Report:** `.claude/analysis/findings/{NAME}-AC-{SCHICHT}-{TS}.md`
Frontmatter: schicht, datei_count, findings_count, blocker_count.
Body: BLOCKER-Sektion, WARNUNGEN-Sektion, Statistik.
Finding-Format: siehe KURZLEBIG_PROMPT unten (F-{NN} Block).

---

## PHASE 2b: Welle 2 (Drafter) — Befund-Analysten auf {middle} — nur bei normal/hard

**Zweck:** Nach FAN_OUT, vor FAN_IN: Drafter analysieren die Schicht-Befunde tiefer.
Befund-Analyse ist kognitive Arbeit (Violations verstehen, Abhaengigkeiten erkennen, Severity repriorisieren).

**Trigger:** Nach Abschluss ALLER Welle-1-Explorer (TaskUpdate status=completed von allen W1-Agents).

| difficulty | Drafter-Count | Modell | Ausfuehrung |
|---|---|---|---|
| easy | 0 | — | Uebersprungen (TL-only) |
| normal | 2 {middle} | sonnet wenn ceiling=opus, haiku sonst | PARALLEL |
| hard | 3 {middle} | sonnet wenn ceiling=opus, haiku sonst | PARALLEL |

**Drafter-Aufteilung nach Schicht (normal: 2 Drafter, hard: 3 Drafter):**
- Drafter 1: BE-CORE + BE-DTO Befunde
- Drafter 2: BE-MAP + BE-CONT Befunde
- Drafter 3: BE-MID Befunde (nur bei hard)

Team Lead spawnt pro Drafter 1 Befund-Analysten:

```
Task tool:
  name: "ac-{name}-drafter-D{NN}"
  subagent_type: "general-purpose"
  model: "{middle}"
  team_name: "ac-{name}"
  mode: "bypassPermissions"
  run_in_background: true              # ALLE Drafter parallel
  prompt: [KURZLEBIG_PROMPT_AC_DRAFTER, siehe unten]
```

**Drafter-Output:** `.claude/analysis/drafts/{NAME}-AC-Drafter-D{NN}.md`
Frontmatter: assigned_schichten, findings_analysiert, dependencies_gefunden, severity_aenderungen, primaerquelle_gelesen: true.
Body: Annotierte Findings mit Kontext, Abhaengigkeiten, Severity-Neubewertung.

---

## PHASE 3: Welle 3 (Synthese) — FAN_IN-Konsolidierung auf {ceiling}

**Zweck:** Alle Explorer-Findings + Drafter-Annotationen zusammenfuehren, Summary schreiben.

**Trigger:** Nach Abschluss ALLER Welle-2-Drafter (oder direkt nach PHASE 1 bei easy=TL-only).

Team Lead spawnt nach Abschluss aller Drafter (oder nach PHASE 1 bei easy):

```
Task tool:
  name: "ac-{name}-fanin"
  subagent_type: "general-purpose"
  model: "{ceiling}"
  team_name: "ac-{name}"
  mode: "bypassPermissions"
  run_in_background: false             # blockierend (Team Lead wartet)
  prompt: [FAN_IN KURZLEBIG_PROMPT, siehe unten]
```

**Summary-Report:** `.claude/analysis/findings/{NAME}-AC-SUMMARY-{TS}.md`
Frontmatter: ac_findings_count, ac_blocker_count, ac_status, ac_findings_by_layer (pro Schicht).
Body: Executive Summary, BLOCKER-Tabelle, WARNUNGEN-Tabelle, Schicht-Coverage.
ac_status: CLEAN (0 Findings) | FINDINGS (>0, kein BLOCKER) | BLOCKER (>=1 BLOCKER).

---

## PHASE 4: OUTPUT (Team Lead direkt)

**Zweck:** Manifest aktualisieren, HiL-Meldung.

### 4.1 Summary-Report lesen

Team Lead liest `.claude/analysis/findings/{NAME}-AC-SUMMARY-{TS}.md`
und extrahiert Frontmatter-Felder.

### 4.2 Manifest aktualisieren

```yaml
ac_run_date: "{HEUTE}"
ac_scope: "{diff|full}"
ac_scope_files: {N}
ac_findings_count: {N}
ac_findings_by_layer:
  BE-CORE: {n}
  BE-DTO: {n}
  BE-MAP: {n}
  BE-CONT: {n}
  BE-MID: {n}
ac_blocker_count: {N}
ac_blocker_items: [{item1}, ...]
ac_status: "{CLEAN|FINDINGS|BLOCKER}"
```

### 4.3 HiL-Meldung

```
AskUserQuestion:
  "{NAME} - AC-Ergebnis

  Analysierte Dateien: {N}
  Aktive Schichten: {aktive_schichten}
  Findings gesamt: {ac_findings_count}
  BLOCKER: {ac_blocker_count}
  Status: {ac_status}

  {Falls BLOCKER:}
  ACHTUNG: {N} BLOCKER muessen vor Merge geloest werden.
  Siehe: .claude/analysis/findings/{NAME}-AC-SUMMARY-{TS}.md

  Naechster Schritt?"

  Optionen:
    WEITER  → Findings zur Kenntnis genommen, fortfahren
    FIXEN   → BLOCKER/WARNUNGEN jetzt beheben (neuer I-Zyklus)
    DEFER   → Findings als PL-Items parken
```

---

## KURZLEBIG_PROMPT_AC_EASY: TL-Direkt-Scan (easy-Modus, kein Sub-Agent)

```
Du bist Team Lead und fuehrst den AC-Scan direkt durch (easy=TL-only, kein Sub-Agent-Spawn).

Scope-Bucket: {SCOPE_BUCKET}
Aktive Schichten: {ACTIVE_LAYERS}
Projekt: {PROJEKT_PFAD}

SCHRITTE:
1. Lies alle relevanten Konventions-Dateien (be-*.md) fuer aktive Schichten
2. Pruefe alle Regeln gegen die Code-Dateien in {SCOPE_BUCKET}
3. Katalogisiere Findings:
   - BLOCKER: Schwerwiegende Verletzung (muss behoben werden)
   - WARNUNG: Konventions-Verletzung (sollte behoben werden)
   - INFO: Best-Practice-Abweichung
4. Setze Manifest-Felder direkt:
   ac_status: [CLEAN|FINDINGS|BLOCKER]
   ac_findings_count: {N}
   ac_blocker_count: {N}
   ac_findings_by_layer: {je Schicht}
5. Schreibe kompakten Summary-Report:
   Pfad: {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-AC-SUMMARY-{TS}.md

REGELN:
- Kein Sub-Agent-Spawn (TL-only ist Budget-effizient und ausreichend fuer kleine Aenderungen)
- Wellen 1, 2 und 3 (FAN_OUT/Drafter/FAN_IN) werden uebersprungen
- Manifest-Felder werden direkt vom TL gesetzt
```

---

## KURZLEBIG_PROMPT: AC-Worker (Phase 2 — Welle 1 Explorer)

```
Du bist ein AC-Worker fuer den Architecture Correctness Check.
Agent-Name: ac-{name}-{SCHICHT}
Team: ac-{name}

═══ DEIN AUFTRAG ═══

Genau 1 Schicht-Scan ausfuehren, dann fertig.

Schicht:           {SCHICHT}
Konventions-Datei: .claude/meta/architekturKonventionen/be-{schicht_lower}.md
Zu pruefende Dateien:
{DATEI_LISTE}
Task-ID:           {TASK_ID}
Projekt:           {PROJEKT_PFAD}

═══ SCHRITTE ═══

1. Lies Konventions-Datei: be-{schicht_lower}.md
   - YAML-Frontmatter: schicht, dateipfad-pattern, ac-layer
   - Aggregierte Regeln: AK-{SCHICHT}-1..N (Severity + Auto-Fix)

2. Pruefe jede Datei gegen alle AK-{SCHICHT}-N Regeln:
   - BLOCKER: Regel verletzt → sofort notieren
   - WARNUNG: Regel verletzt → notieren mit Kontext
   - INFO: Best-Practice-Abweichung → notieren wenn eindeutig
   - Kein Finding: Regel eingehalten (NICHT dokumentieren)

3. Schreibe Finding-Report:
   Pfad: {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-AC-{SCHICHT}-{TS}.md
   Format: Frontmatter (findings_count, blocker_count) + Findings nach Severity

4. TaskUpdate {TASK_ID} status=completed

5. SendMessage an "team-lead":
   "AC-{SCHICHT} {NAME}: {findings_count} Findings ({blocker_count} BLOCKER).
    Geprueft: {datei_count} Dateien, {regel_count} Regeln."

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR dieser eine Schicht-Scan, dann fertig
- Absolute Pfade: {PROJEKT_PFAD}/...
- Datei nicht lesbar → UNREADABLE-Finding, weiter

═══ FINDING-FORMAT ═══

### F-{NN} ({REGEL_CODE} {SEVERITY})
- **Datei:** {relativer_pfad}
- **Zeile:** {N}
- **Regel:** {kurze Beschreibung aus be-*.md}
- **Befund:** {was genau gefunden, Code-Snippet}
- **Fix:** {konkreter Fix-Vorschlag}
```

---

## KURZLEBIG_PROMPT: FAN_IN-Agent (Phase 3)

```
Du bist ein AC-FAN_IN-Agent fuer den Architecture Correctness Check.
Agent-Name: ac-{name}-fanin
Team: ac-{name}

═══ DEIN AUFTRAG ═══

Alle Schicht-Finding-Reports konsolidieren und Summary schreiben.

Task-ID:  {TASK_ID}
Projekt:  {PROJEKT_PFAD}
Findings: {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-AC-*-{TS}.md

═══ SCHRITTE ═══

# SP-FIX-6: Stille-Post-Schutz (Drafter-Reports nur als Kompass)
1. Lies ALLE Drafter-Report-Dateien (NUR als Kompass)
   Pfade: {PROJEKT_PFAD}/.claude/analysis/drafts/{NAME}-AC-Drafter-D*.md
   STILLE-POST-SCHUTZ: Drafter-Reports sind Hinweise, KEINE Faktenquelle.
   Gehe SELBST an die Original-Befunde und Code-Dateien:
   - Verifiziere JEDE Drafter-Interpretation gegen Explorer-Findings
     Pfade: {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-AC-*-{TS}.md
   - Erkenne Abhaengigkeiten zwischen Schicht-Befunden SELBST
   - Schreibe Summary basierend auf DIREKTER Befund-Analyse, nicht auf Drafter-Zusammenfassung

2. Konsolidiere:
   - Zaehle Findings pro Schicht und gesamt
   - Isoliere BLOCKER in eigener Liste
   - ac_status = CLEAN (0 Findings) | FINDINGS (>0, kein BLOCKER) | BLOCKER (>=1)

3. Schreibe Summary-Report:
   Pfad: {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-AC-SUMMARY-{TS}.md
   Frontmatter-Pflicht: ac_findings_count, ac_blocker_count, ac_status,
                        ac_findings_by_layer, primaerquelle_gelesen: true

4. TaskUpdate {TASK_ID} status=completed
5. SendMessage an "team-lead":
   "FAN_IN {NAME}: {ac_findings_count} Findings ({ac_blocker_count} BLOCKER).
    Status: {ac_status}."

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR diese Konsolidierung, dann fertig
```

---

## KURZLEBIG_PROMPT_AC_DRAFTER: Befund-Analyst (Phase 2b — Welle 2, {middle})

```
Du bist ein AC-Drafter-Worker fuer den Architecture Correctness Check.
Agent-Name: ac-{name}-drafter-D{NN}
Team: ac-{name}

DEIN AUFTRAG:

Befund-Analyse fuer zugeordnete Schichten, dann fertig.

Zugeordnete Schichten: {SCHICHT_LIST}
  (Drafter 1: BE-CORE + BE-DTO | Drafter 2: BE-MAP + BE-CONT | Drafter 3: BE-MID)
Task-ID:    {TASK_ID}
Projekt:    {PROJEKT_PFAD}
Findings:   {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-AC-{SCHICHT}-{TS}.md

SCHRITTE:

# SP-FIX-5: Stille-Post-Schutz (Findings nur als Kompass)
1. Lies Finding-Reports (NUR als Kompass) deiner zugeordneten Schichten
   Pfade: {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-AC-{SCHICHT}-*.md
   STILLE-POST-SCHUTZ: Findings sind Hinweise, KEINE Faktenquelle. Gehe SELBST an die Code-Dateien:
   - Verifiziere JEDEN Finding gegen ORIGINAL-QUELLE (Code)
   - Finde neue Findings, die Explorer uebersehen hat
   - Repriorisiere basierend auf DIREKTER Code-Analyse

2. Verstehe Violation-Kontext:
   - Nicht nur "Regel X verletzt", sondern "warum?" und "wie schlimm?"
   - Was ist der Root Cause der Violation?

3. Erkenne Abhaengigkeiten zwischen Schichten:
   - Z.B.: BE-CORE Breaking Change → wirkt sich auf BE-DTO aus?
   - Z.B.: BE-MAP Fehler → kommt aus fehlender BE-CORE Abstraktion?

4. Repriorisiere Severity wenn noetig:
   - 2 LOW-Findings mit gleicher Root Cause → MEDIUM?
   - HIGH + direkter BLOCKER-Charakter → BLOCKER?

5. Schreibe Drafter-Report:
   Pfad: {PROJEKT_PFAD}/.claude/analysis/drafts/{NAME}-AC-Drafter-D{NN}.md
   Format:
   - Frontmatter: assigned_schichten, findings_analysiert, dependencies_gefunden, primaerquelle_gelesen: true
   - Body: Annotierte Findings mit Kontext + ggf. Severity-Neubewertung

6. TaskUpdate {TASK_ID} status=completed

7. SendMessage an "team-lead":
   "AC-Drafter D{NN} {NAME}: {N} Findings analysiert aus {SCHICHT_LIST}.
    Abhaengigkeiten: {M}. Severity-Aenderungen: {K}."

REGELN:

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen
- NUR diese Befund-Analyse, dann fertig
- Absolute Pfade: {PROJEKT_PFAD}/...
- Modell: {middle} (sonnet wenn ceiling=opus, haiku sonst)
```

---

## Schicht-Regel-Inventar (aus be-*.md)

| Schicht | Regeln | BLOCKERs | WARNUNGs | Typischer Befund |
|---------|--------|----------|----------|-----------------|
| BE-CORE | 5 | 1 (AK-CORE-1) | 4 | DbContext direkt injiziert, AddScoped statt AddSingleton |
| BE-DTO | 4 | 1 (AK-DTO-3) | 2 | Business-Logik im DTO, Dateiname != Klassenname |
| BE-MAP | 3 | 0 | 3 | Domain-Logik im Mapper, fehlende ForMember |
| BE-CONT | 5 | 0 | 4 | AK-CONT-5 Import-Verletzung, fehlende ApiControllerBase |
| BE-MID | 3 | 0 | 3 | Business-Logik in Middleware, falscher DI-Lifetime |
| **TOTAL** | **20** | **2** | **16** | |

---

## Fehlerbehandlung

| Fehler | Aktion |
|--------|--------|
| be-{SCHICHT}.md nicht lesbar | Worker meldet UNREADABLE-Finding, weiter |
| Datei in SCOPE_BUCKET geloescht | Finding ignorieren, weiter |
| AC-Worker crashed | Team Lead spawnt neuen Worker (einmalig) |
| FAN_IN-Agent crashed | Team Lead macht FAN_IN manuell |
| git diff nicht verfuegbar | Fallback: scope=full, User-HiL |
| 0 geaenderte Dateien (diff) | CLEAN melden, kein Spawn |
| UNCLASSIFIED-Dateien | Notieren in Summary, kein BLOCKER |

---

## Lifecycle-Integration

**Einsatz:** Nach /_I_orchestrate (post-I, pre-merge), manuell, oder in _finish.
**AC = STRUKTURELL** (Schicht-Grenzen, Pattern-Einhaltung).
**Pre-PR = SEMANTISCH** (Naming, Kommentare, Formatierung). Kein Ersatz fuereinander.

---

ARGUMENTS: $ARGUMENTS
