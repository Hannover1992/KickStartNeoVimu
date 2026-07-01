# /_DiffReduce — Diff-Reduktion & Daseinsberechtigung

```yaml
status: active
version: 2.0.0
created: 2026-03-11
updated: 2026-03-12
op: DiffReduce
phase: Post-Stage
type: orchestration
chain_position: post-stage-pre-AC
difficulty_scaling: true
team_based: true
```

---

```
+======================================================================+
| VERTRAG: /_DiffReduce                                                |
+======================================================================+
|                                                                        |
| KERN-FRAGE:                                                            |
|   "Jede Aenderung ist boese."                                         |
|   Haette man das Feature mit WENIGER Diff erreichen koennen?          |
|   Jede geaenderte Zeile muss ihre Daseinsberechtigung nachweisen.     |
|                                                                        |
| DREI PRUEF-DIMENSIONEN:                                                |
|   1. ARTEFAKT: Ist das ein Ueberbleibsel des Entwicklungsprozesses?   |
|      (Exploration, Debug, Hin-und-Her, auskommentiert, defensiv)       |
|   2. ANSATZ: Haette man dasselbe Ziel einfacher erreichen koennen?    |
|      (Weniger Dateien, weniger Abstraktionen, bestehende Patterns)     |
|   3. KAUSALITAET: Existiert der GRUND fuer diese Aenderung noch?      |
|      (Commit-History: eingefuehrt wegen X, X spaeter revertet?)       |
|                                                                        |
| DREI MODI:                                                             |
|   [default]      = Statischer Diff-Sweep (SPUR-1..8 + F-1..F-4)      |
|   --fullScan     = Chronologische Commit-Archaeologie (Kausalketten)  |
|   --analyse FILE = Fokussierte Git-Archaeologie einer Stelle          |
|   (+ --theoretic = READ-ONLY Variante, kombinierbar mit allen Modi)   |
|                                                                        |
| UNTERSCHIED ZU ANDEREN COMMANDS:                                       |
|   /_R_orchestrate = "Ist der Code ARCHITEKTONISCH korrekt?"           |
|   /_AC_orchestrate = "Ist der Code ARCHITEKTUR-konform?"              |
|   /_I_diffAudit   = "Trackt jede Zeile zu einem W{n}/AK?" (spaet)    |
|   /_DiffReduce    = "BRAUCHEN wir diese Aenderung?" (frueh)           |
|   /_DiffReduce    = "Ist das ABSOLUT noetig? Aligned mit Spec?        |
|                      Haetten wir das mit weniger umgesetzt?"           |
|                                                                        |
| LIEST — Vault-First (BL-050):                                         |
|   {VAULT}/_manifest.md        (NAME, Phase, Kontext)         |
|   git diff develop...HEAD              (Gesamt-Diff des Branches)     |
|   git log develop...HEAD --oneline     (Commit-Anzahl als Signal)     |
|   PRIMAER: {VAULT}/.../Spec/{NAME}_Spec.md  (Anforderungen, AK)      |
|     FALLBACK: .claude/specs/{NAME}_Spec.md                            |
|   {VAULT}/Task.md                      (User Story, Aufgabenziel)     |
|                                                                        |
| SCHREIBT:                                                              |
|   {VAULT}/_manifest.md        (dr_*-Felder, NUR Referenz)   |
|   .claude/analysis/findings/{NAME}-DR-SUMMARY-{TS}.md (Report)       |
|                                                                        |
| AUSGABEN DURCH WORKER:                                                 |
|   .claude/analysis/findings/{NAME}-DR-{BEREICH}-{TS}.md              |
|     (pro Bereich 1 Finding-Report, via Explorer-Worker)               |
|   .claude/analysis/drafts/{NAME}-DR-D{NN}.md                         |
|     (pro Analyst 1 Tiefenanalyse, via Analyst-Worker)                 |
|                                                                        |
| HAUPTPRODUKT:                                                          |
|   {NAME}-DR-SUMMARY-{TS}.md + Manifest dr_*-Felder                   |
|   (Reduktions-Plan: NOTWENDIG / FRAGLICH / REVERT pro Aenderung)     |
|                                                                        |
| PIPELINE:                                                              |
|   [/_stage_orchestrate] → [/_DiffReduce] → [/_AC_orchestrate]         |
+======================================================================+
```

---

## Aufruf

```
/_DiffReduce [name] [difficulty] [ceiling] [floor] [--theoretic] [--fullScan] [--analyse FILE]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `name` | (PFLICHT) | String | Feature-Name (Artefakt-Naming) |
| `difficulty` | normal | easy, normal, hard | Parallelisierung |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell |
| `--theoretic` | (optional) | Flag | READ-ONLY: NUR Analyse + Report, KEIN Code anfassen |
| `--fullScan` | (optional) | Flag | Chronologische Commit-Archaeologie (Kausalketten) |
| `--analyse` | (optional) | FILE/PATTERN | Fokussierte Git-Archaeologie einer Stelle |

**Modi-Kombination:**
- `--theoretic` ist kombinierbar mit `--fullScan` und `--analyse`
- `--fullScan` und `--analyse` sind NICHT kombinierbar (entweder breit oder fokussiert)
- Ohne `--fullScan`/`--analyse`: Default-Modus (statischer Diff-Sweep)

**--theoretic Modus (READ-ONLY, kombinierbar):**
- Fuehrt die komplette Analyse durch
- Schreibt Report + Manifest-Felder (dr_*)
- ABER: Bietet KEIN "AUFRAEUMEN" an — nur WEITER, REVIEW, SKIP
- KEIN git add, KEIN git commit, KEIN Edit, KEIN Write auf Produkt-Dateien
- NUR .claude/ Dateien werden geschrieben (Report, Manifest)
- Ideal fuer: Pre-PR Einschaetzung, "Was KOENNTE man reduzieren?"

**Beispiele:**
```
# === DEFAULT-MODUS (statischer Diff-Sweep) ===
/_DiffReduce DCSRE-882                          → normal, mit AUFRAEUMEN-Option
/_DiffReduce DCSRE-882 hard opus haiku          → 5 Explorer, 3 Analysten, 1 Opus Synthese
/_DiffReduce QuickFix easy haiku haiku          → TL-only
/_DiffReduce DCSRE-882 normal --theoretic       → Analyse-Only, kein Code anfassen

# === FULLSCAN-MODUS (Commit-Archaeologie) ===
/_DiffReduce DCSRE-882 normal --fullScan        → Chronologisch alle Commits tracen
/_DiffReduce DCSRE-882 hard opus --fullScan     → Tiefe Analyse mit Opus-Synthese
/_DiffReduce DCSRE-882 easy --fullScan --theoretic → Schneller Scan, nur Report

# === ANALYSE-MODUS (fokussierte Git-Archaeologie) ===
/_DiffReduce DCSRE-882 --analyse VDEK.DCSP.Application.csproj
/_DiffReduce DCSRE-882 --analyse "InternalsVisibleTo"
/_DiffReduce DCSRE-882 --analyse DicImportService.cs:230-240
/_DiffReduce DCSRE-882 --analyse "*.csproj" --theoretic
```

---

## Modi-Uebersicht

```
╔══════════════════════════════════════════════════════════════════════╗
║  WANN WELCHER MODUS?                                                ║
║                                                                      ║
║  DEFAULT         "Schnell den Diff durchscannen"                    ║
║  (kein Flag)     → Statisch: SPUR-1..8 + F-1..F-4 pro Datei        ║
║                  → Gut fuer: Standard-PR-Vorbereitung               ║
║                                                                      ║
║  --fullScan      "Warum ist jede Aenderung da?"                     ║
║                  → Chronologisch: Commit fuer Commit, Kausalketten  ║
║                  → Erkennt: Verwaiste Artefakte (SPUR-8)            ║
║                  → Erkennt: Gekoppelte Aenderungen (Revert-Gruppen) ║
║                  → Gut fuer: Lange Entwicklung, viele Kurskorrekturen║
║                                                                      ║
║  --analyse FILE  "Diese Stelle scheint unnoetig"                    ║
║                  → Fokussiert: Git-Archaeologie einer Stelle        ║
║                  → Zeigt: Kausalkette (wann, warum, durch wen)      ║
║                  → Zeigt: Gekoppelte Aenderungen zum Mit-Reverten   ║
║                  → Gut fuer: Verdaechtige Stellen gezielt klaeren   ║
║                                                                      ║
║  TIEFE-VERGLEICH:                                                    ║
║    Default    = Oberflaechenscan (Diff lesen)                       ║
║    --fullScan = Tiefenscan (Git-History lesen)                      ║
║    --analyse  = Chirurgisch (eine Stelle, volle Archaeologie)       ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Skalierung — 3-Wellen

| Schwierigkeit | Explorer (W1) | Analyst (W2) | Synthese (W3) |
|---|---|---|---|
| **hard** | 5 {floor} PARALLEL | 3 {middle} PARALLEL | 1 {ceiling} |
| **normal** | 3 {floor} PARALLEL | 2 {middle} PARALLEL | 1 {ceiling} |
| **easy** | TL-only (kein Spawn) | [uebersprungen] | [uebersprungen] |

**Modell-Zuordnung:**
- ceiling=opus:   floor=haiku, middle=sonnet, ceiling=opus
- ceiling=sonnet: floor=haiku, middle=haiku,  ceiling=sonnet
- ceiling=haiku:  floor=haiku, middle=haiku,  ceiling=haiku

---

## GLOBALE PARAMETER (/_param Override)

```
params = lies("_session_params.md")
difficulty = params.difficulty
ceiling    = min(ceiling, params.ceiling)
floor      = max(floor, params.floor)
Validierung: ceiling >= floor (sonst ceiling = floor + Warning)
middle = sonnet wenn ceiling=opus, sonnet wenn ceiling=sonnet, haiku wenn ceiling=haiku
```

---

## PHASE 1: SCOPE (Team Lead, kein Agent-Spawn)

**Zweck:** Diff laden, Anforderungen verstehen, Bereiche definieren.

### 1.1 Kontext laden

```bash
# 1. Diff-Statistik (Umfang erkennen)
git diff develop...HEAD --stat
git diff develop...HEAD --name-only

# 2. Commit-Anzahl (Hin-und-Her-Signal)
git log develop...HEAD --oneline --no-merges | wc -l

# 3. Anforderungen laden
#    → SPEC (Akzeptanzkriterien)
#    → Task.md (User Story / Aufgabenziel)
```

**Hin-und-Her-Signal:**
```
IF commits > dateien * 2:
  → WARNUNG: Commit/Datei-Ratio > 2 = Hinweis auf Hin-und-Her-Entwicklung
  → Hoehere Wahrscheinlichkeit fuer Artefakte
```

### 1.2 Anforderungs-Extrakt

Aus SPEC + Task.md extrahieren:
```
ZIEL = "Was wollen wir erreichen?" (1-3 Saetze)
AK_LISTE = [AK-1, AK-2, ...] (messbare Kriterien)
SCOPE_FILES = [erwartete Dateien basierend auf AK]
```

### 1.3 Diff in Bereiche aufteilen

Geaenderte Dateien in logische Bereiche gruppieren:

```
BEREICH_TYPEN:
  FEATURE-CORE    → Business Logic (Services, Providers, Domain)
  FEATURE-INFRA   → DI, Config, .csproj, Startup
  TEST            → Unit, Integration, E2E
  MIGRATION       → DB-Migrationen, Schema
  MAPPING         → DTOs, Mapper, Profiles
  CONTROLLER      → API-Endpoints
  SONSTIG         → Alles andere
```

### 1.4 Scope-Bestaetigung

```
DiffReduce: {N} Dateien geaendert, +{A}/-{R} Zeilen
Commits: {C} (Ratio: {C/N} pro Datei)
Anforderungen: {K} AKs aus SPEC
Bereiche: {B} aktive Bereiche
```

---

## PHASE 2: ANALYSE (Wellen)

### Phase 2a: Welle 1 — Explorer (Bereich-Scanner, {floor})

Pro aktivem Bereich 1 Explorer-Worker spawnen (bei normal/hard).

```
Agent tool:
  name: "dr-{name}-{BEREICH}"
  subagent_type: "general-purpose"
  model: "{floor}"
  mode: "bypassPermissions"
  run_in_background: true
  prompt: [KURZLEBIG_PROMPT_EXPLORER, siehe unten]
```

Explorer prueft jede Datei in seinem Bereich auf:

**DIMENSION 1 — ARTEFAKT-CHECK (7 Spuren):**

| Spur | Was | Signal | Typisch revertbar? |
|------|-----|--------|-------------------|
| SPUR-1 | Auskommentierter Code | `//`, `/* */` ohne Erklaerung | JA |
| SPUR-2 | Debug-Logging | `Console.Write`, `Debug.Log`, temporaere Logs | JA |
| SPUR-3 | Defensive Checks | Null-Checks fuer nie-null Werte | MEISTENS |
| SPUR-4 | Doppelt-angefasst | Datei in 2+ Commits geaendert, fruehere subsumiert | PRUEFEN |
| SPUR-5 | Explorations-Reste | Klassen/Methoden erstellt aber nie genutzt | JA |
| SPUR-6 | Ueberschuessige Imports | Using-Statements fuer nicht verwendete Typen | JA |
| SPUR-7 | Whitespace/Formatting | Nur Einrueckung/Leerzeilen geaendert | JA |
| SPUR-8 | Verwaiste Artefakte | Aenderung im selben Commit wie revertetes Feature, ueberlebte den Revert | PRUEFEN |

**DIMENSION 2 — ANSATZ-CHECK (4 Fragen):**

| Frage | Pruefung |
|-------|----------|
| F-1: Neue Datei noetig? | Haette eine BESTEHENDE Datei erweitert werden koennen statt eine neue zu erstellen? |
| F-2: Neue Abstraktion noetig? | Interface/Basisklasse eingefuehrt — wird sie an mehr als 1 Stelle genutzt? Falls nein: Premature Abstraction. |
| F-3: Config-Explosion? | Neue Config-Werte — koennte man Defaults nutzen statt explizite Config? |
| F-4: Symmetrie-Zwang? | Aenderung NUR gemacht "weil andere Stellen das auch so haben"? Pattern-Konsistenz ist kein Selbstzweck wenn es den Diff aufblaeht. |

**Explorer-Output:** `.claude/analysis/findings/{NAME}-DR-{BEREICH}-{TS}.md`

### Phase 2b: Welle 2 — Analyst (Tiefenanalyse, {middle})

Nach Abschluss ALLER Explorer:

```
Agent tool:
  name: "dr-{name}-analyst-D{NN}"
  subagent_type: "general-purpose"
  model: "{middle}"
  mode: "bypassPermissions"
  run_in_background: true
  prompt: [KURZLEBIG_PROMPT_ANALYST, siehe unten]
```

Analysten nehmen Explorer-Findings als Kompass, verifizieren an Primaerquellen:
- Cross-Bereich-Abhaengigkeiten erkennen (Datei in Bereich A referenziert Datei in Bereich B)
- ANSATZ-Alternative formulieren (konkreter Vorschlag: "Statt X haette Y gereicht")
- Risiko-Bewertung: Was passiert wenn man die Aenderung revertet?

**Analyst-Output:** `.claude/analysis/drafts/{NAME}-DR-D{NN}.md`

### Phase 2c: Welle 3 — Synthese ({ceiling})

Nach Abschluss ALLER Analysten:

```
Agent tool:
  name: "dr-{name}-synthese"
  subagent_type: "general-purpose"
  model: "{ceiling}"
  mode: "bypassPermissions"
  run_in_background: false    # blockierend
  prompt: [KURZLEBIG_PROMPT_SYNTHESE, siehe unten]
```

---

## PHASE 3: OUTPUT (Team Lead direkt)

### 3.1 Summary lesen + Manifest updaten

Manifest-Felder (NUR Referenz, KEIN Protokoll):

```
dr_status: {CLEAN|FINDINGS|BLOCKER}
dr_files_total: {N}
dr_lines_total: {+A/-R}
dr_revert_candidates: {N}
dr_fraglich_count: {N}
dr_reduction_potential: {N}%
dr_summary_report: .claude/analysis/findings/{NAME}-DR-SUMMARY-{TS}.md
dr_run_date: {HEUTE}
```

**MANIFEST = NUR REFERENZ, KEIN PROTOKOLL:**
- `dr_status` = exakt CLEAN, FINDINGS oder BLOCKER
- `dr_revert_candidates` = exakt eine Zahl
- `dr_reduction_potential` = exakt eine Zahl mit %
- ALLE Details → Summary-Report

### 3.2 HiL-Meldung

```
AskUserQuestion:
  "{NAME} - DiffReduce-Ergebnis

  Diff: {N} Dateien, +{A}/-{R} Zeilen
  Commits: {C} (Ratio: {R} pro Datei)
  Status: {dr_status}

  REVERT-Kandidaten: {dr_revert_candidates}
  FRAGLICH: {dr_fraglich_count}
  Reduktions-Potenzial: {dr_reduction_potential}%

  Report: .claude/analysis/findings/{NAME}-DR-SUMMARY-{TS}.md

  Naechster Schritt?"

  Optionen (Standard-Modus):
    WEITER     → Zur Kenntnis genommen, weiter zu /_AC_orchestrate
    AUFRAEUMEN → REVERT-Kandidaten jetzt entfernen (sicherste zuerst)
    REVIEW     → Report lesen, einzeln entscheiden
    SKIP       → DiffReduce-Ergebnisse ignorieren, direkt zu AC

  Optionen (--theoretic Modus, READ-ONLY):
    WEITER     → Zur Kenntnis genommen, weiter zu /_AC_orchestrate
    REVIEW     → Report lesen (NUR lesen, kein AUFRAEUMEN moeglich)
    SKIP       → DiffReduce-Ergebnisse ignorieren, direkt zu AC
    (KEIN AUFRAEUMEN — theoretic = reine Analyse)
```

### 3.3 Bei AUFRAEUMEN

Cleanup-Reihenfolge (sicherste zuerst):
```
1. Whitespace/Formatting (SPUR-7) → risikofrei
2. Unused Imports (SPUR-6) → risikofrei
3. Auskommentierter Code (SPUR-1) → risikofrei
4. Debug-Logging (SPUR-2) → niedrig
5. Explorations-Reste (SPUR-5) → mittel (Tests pruefen!)
6. Defensive Checks (SPUR-3) → mittel (Tests pruefen!)
7. Doppelt-angefasste Stellen (SPUR-4) → HOCH (genau pruefen!)
8. Verwaiste Artefakte (SPUR-8) → HOCH (Kausalkette verifizieren!)
9. ANSATZ-Alternativen (F-1..F-4) → HOCH (User-Entscheidung!)

Nach JEDEM Block: Build + Tests laufen lassen!
GRUEN → weiter | ROT → Revert des Reverts
```

---

## KURZLEBIG_PROMPT: Explorer (Welle 1, {floor})

```
Du bist ein DiffReduce-Explorer fuer Diff-Reduktion.
Agent-Name: dr-{name}-{BEREICH}

═══ DEIN AUFTRAG ═══

Bereich scannen: Jede Aenderung auf Daseinsberechtigung pruefen.

Bereich:         {BEREICH}
Dateien:         {DATEI_LISTE}
Task-ID:         {TASK_ID}
Projekt:         {PROJEKT_PFAD}

═══ KONTEXT ═══

Feature-Ziel:    {ZIEL}
AK-Liste:        {AK_LISTE}
Commits total:   {COMMIT_COUNT} (Ratio: {RATIO} pro Datei)

═══ SCHRITTE ═══

1. Pro Datei: git diff develop...HEAD -- {DATEI}

2. ARTEFAKT-CHECK (Dimension 1):
   Pruefe auf 7 Spuren:
   SPUR-1: Auskommentierter Code (//,/* */ ohne Erklaerung)
   SPUR-2: Debug-Logging (Console.Write, Debug.Log, temporaer)
   SPUR-3: Defensive Checks (Null-Checks fuer nie-null Werte)
   SPUR-4: Doppelt-angefasst (in 2+ Commits, fruehere subsumiert?)
   SPUR-5: Explorations-Reste (erstellt aber nie genutzt)
   SPUR-6: Ueberschuessige Imports (Using fuer nicht verwendete Typen)
   SPUR-7: Whitespace/Formatting (nur Einrueckung/Leerzeilen)
   SPUR-8: Verwaiste Artefakte (im selben Commit wie revertetes Feature eingefuehrt,
           ueberlebte den Revert — git log noetig fuer Erkennung)

3. ANSATZ-CHECK (Dimension 2):
   F-1: Neue Datei noetig? (Bestehende erweiterbar?)
   F-2: Neue Abstraktion noetig? (Nur 1 Nutzer = premature)
   F-3: Config-Explosion? (Defaults moeglich?)
   F-4: Symmetrie-Zwang? (Pattern-Konsistenz als Selbstzweck?)

4. Kategorisierung pro Datei/Hunk:
   NOTWENDIG → Trackt zu AK, wird gebraucht
   FRAGLICH  → Unklar, User muss entscheiden
   REVERT    → Kein AK-Bezug, Artefakt oder unnoetig

5. Schreibe Finding-Report:
   {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-DR-{BEREICH}-{TS}.md
   Frontmatter: bereich, dateien_count, notwendig_count,
                fraglich_count, revert_count

6. SendMessage an "team-lead":
   "DR-{BEREICH}: {N} Dateien geprueft.
    NOTWENDIG: {n1}, FRAGLICH: {n2}, REVERT: {n3}"

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen
- NUR dieser Bereich-Scan, dann fertig
- Absolute Pfade: {PROJEKT_PFAD}/...
- Im Zweifel: FRAGLICH (nicht REVERT)
```

---

## KURZLEBIG_PROMPT: Analyst (Welle 2, {middle})

```
Du bist ein DiffReduce-Analyst fuer Tiefenanalyse.
Agent-Name: dr-{name}-analyst-D{NN}

═══ DEIN AUFTRAG ═══

Explorer-Findings vertiefen: Alternativen formulieren, Risiken bewerten.

Zugeordnete Bereiche: {BEREICH_LIST}
Task-ID:               {TASK_ID}
Projekt:               {PROJEKT_PFAD}
Findings:              {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-DR-*-{TS}.md

═══ KONTEXT ═══

Feature-Ziel: {ZIEL}
AK-Liste:     {AK_LISTE}

═══ SCHRITTE ═══

# SP-FIX: Stille-Post-Schutz (Explorer-Findings nur als Kompass)
1. Lies Explorer-Findings (NUR als Kompass)
   STILLE-POST-SCHUTZ: Verifiziere JEDES Finding am ORIGINAL-CODE.
   Gehe SELBST an die Code-Dateien.

2. Fuer jedes FRAGLICH/REVERT-Finding:
   a) Code SELBST lesen und verstehen
   b) Abhaengigkeits-Graph: Wird diese Aenderung von ANDERER Aenderung benoetigt?
   c) Risiko-Bewertung: Was passiert bei Revert? (Tests? Kompilierung? Runtime?)
   d) Fuer ANSATZ-Findings (F-1..F-4): Konkreten Alternativ-Vorschlag formulieren
      "Statt X (Y Zeilen) haette Z gereicht (N Zeilen)"

3. Cross-Bereich-Abhaengigkeiten:
   - Datei A (Bereich CORE) referenziert Datei B (Bereich DTO)?
   - Revert von A macht B kaputt?
   → Abhaengigkeitskette dokumentieren

4. Severity-Neubewertung:
   - Explorer sagt REVERT, aber Abhaengigkeit existiert → FRAGLICH
   - Explorer sagt FRAGLICH, aber klar unnoetig → REVERT

5. Schreibe Analyst-Report:
   {PROJEKT_PFAD}/.claude/analysis/drafts/{NAME}-DR-D{NN}.md
   Frontmatter: bereiche, findings_analysiert, alternativen_vorgeschlagen,
                abhaengigkeiten_gefunden, primaerquelle_gelesen: true

6. SendMessage an "team-lead":
   "DR-Analyst D{NN}: {N} Findings analysiert.
    Alternativen: {M}. Abhaengigkeiten: {K}."

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen
- NUR diese Analyse, dann fertig
```

---

## KURZLEBIG_PROMPT: Synthese (Welle 3, {ceiling})

```
Du bist der DiffReduce-Synthese-Agent.
Agent-Name: dr-{name}-synthese

═══ DEIN AUFTRAG ═══

Alle Bereichs-Findings + Analysten-Reports konsolidieren.
Finales Urteil pro Aenderung. Reduktions-Plan erstellen.

Task-ID: {TASK_ID}
Projekt: {PROJEKT_PFAD}

═══ INPUT ═══

# SP-FIX: Stille-Post-Schutz
Explorer-Findings: {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-DR-*-{TS}.md
Analyst-Reports:   {PROJEKT_PFAD}/.claude/analysis/drafts/{NAME}-DR-D*.md
(Beides NUR als Kompass — verifiziere an Primaerquellen wenn unklar)

Feature-Ziel: {ZIEL}
AK-Liste:     {AK_LISTE}

═══ SCHRITTE ═══

1. ALLE Explorer-Findings + Analyst-Reports lesen

2. Konflikte aufloesen:
   - Gleiche Datei, unterschiedliche Bewertung → tiefere Analyse gewinnt
   - Abhaengigkeitsketten beachten: REVERT nur wenn GANZE Kette revertbar

3. Finale Kategorisierung pro Datei/Hunk:
   NOTWENDIG → Begruendung (welcher AK, welche Abhaengigkeit)
   FRAGLICH  → Kontext (warum unklar, was User entscheiden muss)
   REVERT    → Begruendung (welche Spur, welches Risiko)

4. Reduktions-Statistik berechnen:
   - REVERT-Zeilen summieren → Reduktions-Potenzial
   - FRAGLICH-Zeilen separat → maximales Potenzial

5. Summary-Report schreiben:
   {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-DR-SUMMARY-{TS}.md

   FORMAT:
   ---
   dr_status: {CLEAN|FINDINGS|BLOCKER}
   dr_files_total: {N}
   dr_lines_total: "+{A}/-{R}"
   dr_notwendig_count: {N}
   dr_fraglich_count: {N}
   dr_revert_count: {N}
   dr_reduction_potential: "{N}%"
   primaerquelle_gelesen: true
   ---

   ## Zusammenfassung

   | Kategorie | Dateien | Zeilen | Anteil |
   |-----------|---------|--------|--------|
   | NOTWENDIG | {n1} | {z1} | {p1}% |
   | FRAGLICH | {n2} | {z2} | {p2}% |
   | REVERT | {n3} | {z3} | {p3}% |

   ## NOTWENDIG (behalten)

   | # | Datei | Aenderung | AK/Begruendung |
   |---|-------|-----------|----------------|

   ## FRAGLICH (User entscheidet)

   | # | Datei | Aenderung | Verdacht | Empfehlung |
   |---|-------|-----------|----------|------------|

   ## REVERT-KANDIDATEN

   | # | Datei | Aenderung | Spur/Frage | Begruendung |
   |---|-------|-----------|------------|-------------|

   ## ANSATZ-ALTERNATIVEN (Dimension 2)

   | # | Aktuelle Loesung | Alternative | Einsparung |
   |---|-----------------|-------------|------------|

   ## Cleanup-Plan (Reihenfolge)

   1. SPUR-7 (Whitespace) → risikofrei
   2. SPUR-6 (Imports) → risikofrei
   3. SPUR-1 (Auskommentiert) → risikofrei
   4. SPUR-2 (Debug-Logging) → niedrig
   5. SPUR-5 (Explorations-Reste) → mittel
   6. SPUR-3 (Defensive Checks) → mittel
   7. SPUR-4 (Doppelt-angefasst) → HOCH
   8. SPUR-8 (Verwaiste Artefakte) → HOCH (Kausalkette!)
   9. F-1..F-4 (Ansatz-Alternativen) → HOCH (User!)

6. SendMessage an "team-lead":
   "DR-Synthese {NAME}: {N} Dateien analysiert.
    NOTWENDIG: {n1}, FRAGLICH: {n2}, REVERT: {n3}.
    Reduktions-Potenzial: {p}%."

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen
- NUR diese Synthese, dann fertig
```

---

## KURZLEBIG_PROMPT_EASY: TL-Direkt-Scan (easy, kein Sub-Agent)

```
TL fuehrt DiffReduce direkt durch (easy=TL-only, kein Sub-Agent-Spawn).

1. git diff develop...HEAD --stat laden
2. Pro Datei: Artefakt-Check (SPUR-1..7) + Ansatz-Check (F-1..F-4)
3. Kategorisierung: NOTWENDIG / FRAGLICH / REVERT
4. Summary-Report schreiben (kompakt)
5. Manifest-Felder direkt setzen

Wellen 1, 2, 3 werden uebersprungen.
```

---

## ═══════════════════════════════════════════════════════════════
## MODUS: --fullScan (Kausale Commit-Archaeologie)
## ═══════════════════════════════════════════════════════════════

```
KERN-IDEE:
  Nicht den Diff STATISCH lesen, sondern die GESCHICHTE verstehen.
  Jeder Commit hatte einen Grund. Existiert der Grund noch?

  Case Study (InternalsVisibleTo, DCSRE-882):
    Commit A: JSON-Sidecar + InternalsVisibleTo (zusammen eingefuehrt)
    Commit B: ParseDatenArt public → internal (Folge-Commit)
    Commit C: Kurskorrektur — JSON-Sidecar REVERTET
    Ergebnis: InternalsVisibleTo + internal ueberlebten den Revert
    → Verwaistes Artefakt (SPUR-8): Grund existiert nicht mehr

WANN --fullScan?
  - Viele Commits (>15) auf dem Branch
  - Bekannte Kurskorrekturen / Richtungswechsel waehrend Entwicklung
  - Commit/Datei-Ratio > 2 (Hinweis auf Hin-und-Her)
  - Default-Modus hat FRAGLICH-Items gefunden, User will tiefer graben
```

### FS-1: Kontext laden

```
1. Spec/Model lesen → Feature-Ziel + AKs verstehen
   → Was SOLLTE am Ende stehen?

2. git log develop...HEAD --oneline --no-merges --reverse
   → Chronologische Commit-Liste (aelteste zuerst)

3. git log develop...HEAD --oneline --no-merges | wc -l
   → Commit-Anzahl (>15 = lohnend fuer fullScan)

4. Commit-Messages scannen nach Signalwoertern:
   "revert", "rueckbau", "kurskorrektur", "korrigiert",
   "fix", "cleanup", "entfernt", "nicht mehr", "doch nicht"
   → Markieren als KORREKTUR/REVERT-Commits
```

### FS-2: Commit-Ketten identifizieren

```
Pro Commit auf dem Branch:
  git show {HASH} --stat    → welche Dateien
  git show {HASH} -s --format="%s"  → Message (Intent)

Commits in KETTEN-TYPEN klassifizieren:

  EINFUEHRUNG  → Fuehrt neue Dateien/Methoden/Config ein
  ERWEITERUNG  → Baut auf vorherigem Commit auf
  KORREKTUR    → Aendert etwas aus fruherem Commit (teilweise)
  REVERT       → Macht früheren Commit (komplett) rueckgaengig
  UEBERLEBEND  → Seiteneffekt eines Commits ueberlebte dessen Revert

Ketten-Erkennung:
  1. Dateien pro Commit auflisten
  2. Commits gruppieren die GLEICHE Dateien beruehren
  3. Message-Analyse: "revert" / "kurskorrektur" → REVERT-Commit identifizieren
  4. Pruefen: Was wurde im REVERT-Commit NICHT zurueckgebaut?
     → Dateien die im Einfuehrungs-Commit UND im finalen Diff sind,
       aber NICHT im Revert-Commit beruehrt wurden = SPUR-8 Kandidaten
```

### FS-3: Verwaiste Artefakte erkennen (SPUR-8)

```
ALGORITHMUS:

Fuer jeden identifizierten REVERT-Commit R:
  1. Original-Commit O finden (den R revertet/korrigiert)
  2. O_DATEIEN = Dateien in Commit O (git show O --name-only)
  3. R_DATEIEN = Dateien in Commit R (git show R --name-only)
  4. NICHT_BERUEHRT = O_DATEIEN \ R_DATEIEN (Mengendifferenz)
  5. Fuer jede Datei in NICHT_BERUEHRT:
     → Ist sie im finalen Diff (develop...HEAD)?
     → Wenn ja: SPUR-8 KANDIDAT
     → Verifizieren: git diff develop...HEAD -- {DATEI}
        Zeigt die Aenderung noch Spuren von Commit O?

AUSGABE pro SPUR-8 Kandidat:
  "SPUR-8: {DATEI}
   Eingefuehrt in: {COMMIT_O} ({MESSAGE_O})
   Zusammen mit:   {ANDERE_DATEIEN_IN_O}
   Revertet durch: {COMMIT_R} ({MESSAGE_R})
   ABER: {DATEI} wurde in {COMMIT_R} NICHT beruehrt
   → Verwaistes Artefakt: Grund fuer Aenderung existiert nicht mehr"
```

### FS-4: Gekoppelte Aenderungen (Cross-File-Paare)

```
Aenderungen existieren selten allein. Muster erkennen:

KOPPLUNGS-TYPEN:
  K-1: .csproj + .cs     → Config-Aenderung + Code-Aenderung
  K-2: Interface + Impl   → Vertragsaenderung + Implementierung
  K-3: DTO + Mapper       → Datenstruktur + Transformation
  K-4: Config + Consumer  → Konfiguration + Code der sie liest
  K-5: Migration + Entity → DB-Schema + Domain-Model

REGEL: Wenn EIN Teil eines Paares revertbar ist,
       pruefen ob das GANZE Paar revertbar ist.

Case Study: InternalsVisibleTo (.csproj) + internal ParseDatenArt (.cs)
  → Paar K-1. Beide zusammen eingefuehrt, Grund revertet.
  → BEIDE zusammen reverten (nicht nur eins).
```

### FS-5: FullScan-Report

```
Zusaetzlich zum Standard-Report (NOTWENDIG/FRAGLICH/REVERT):

## Commit-Ketten-Analyse

  | Kette | Commits | Typ | Status |
  |-------|---------|-----|--------|
  | K1: JSON-Sidecar | a0a608→...→kurskorrektur | REVERTET | Artefakte pruefen |
  | K2: DIC-Adapter   | 174c0b→...→20a0b69      | AKTIV    | OK |

## Verwaiste Artefakte (SPUR-8)

  | # | Datei | Original-Commit | Revert-Commit | Aenderung |
  |---|-------|-----------------|---------------|-----------|
  | 1 | .csproj | a0a608c (Sidecar) | kurskorr. | InternalsVisibleTo |
  | 2 | Service.cs | 1d83363 | - | internal statt public |

## Gekoppelte Revert-Gruppen

  | Gruppe | Dateien | Zusammen reverten? |
  |--------|---------|-------------------|
  | G1 | .csproj + Service.cs | JA (K-1 Paar, selber Grund) |

## Kausalketten-Diagramm (kompakt)

  Commit a0a608c (Sidecar) ──┬── .csproj: +InternalsVisibleTo
                              ├── Service.cs: public→internal
                              └── [Sidecar-Code]
                                     │
  Commit kurskorr. (Revert) ────── [Sidecar-Code] ENTFERNT
                                     │
  NICHT beruehrt: .csproj, Service.cs → VERWAIST
```

### KURZLEBIG_PROMPT: FullScan-Worker ({middle})

```
Du bist ein DiffReduce-FullScan-Worker fuer Commit-Archaeologie.
Agent-Name: dr-{name}-fullscan-D{NN}

═══ DEIN AUFTRAG ═══

Commit-Ketten in deiner zugewiesenen Gruppe analysieren.
Verwaiste Artefakte und gekoppelte Aenderungen identifizieren.

Zugewiesene Commit-Gruppe: {COMMIT_RANGE}
Task-ID:                   {TASK_ID}
Projekt:                   {PROJEKT_PFAD}

═══ KONTEXT ═══

Feature-Ziel:     {ZIEL}
REVERT-Commits:   {REVERT_COMMIT_LIST} (bereits identifiziert)
Gesamt-Commits:   {TOTAL_COMMITS}

═══ SCHRITTE ═══

1. Pro Commit in deiner Gruppe:
   git show {HASH} --stat       → Dateien
   git show {HASH} -s --format="%s"  → Message/Intent

2. Fuer REVERT-Commits in deiner Gruppe:
   a) Original-Commit identifizieren (was wurde revertet?)
   b) Dateien-Vergleich: Original vs Revert
   c) NICHT beruehrte Dateien = SPUR-8 Kandidaten
   d) Verifizieren am finalen Diff: git diff develop...HEAD -- {DATEI}

3. Kopplungen erkennen:
   - Dateien die im selben Commit geaendert wurden = potentielles Paar
   - Paar-Typen: K-1 bis K-5 (csproj+cs, interface+impl, etc.)

4. Pro Fund: Kausalkette dokumentieren
   "Commit X fuehrte Y ein weil Z → Commit W revertete Z → Y ueberlebte"

5. Report schreiben:
   {PROJEKT_PFAD}/.claude/analysis/drafts/{NAME}-DR-FS-D{NN}.md

6. SendMessage an "team-lead":
   "DR-FullScan D{NN}: {N} Commits analysiert.
    SPUR-8 Kandidaten: {M}. Kopplungen: {K}."

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen
- git show/log/diff LESEN ist erlaubt (READ-ONLY)
- NUR diese Analyse, dann fertig
```

---

## ═══════════════════════════════════════════════════════════════
## MODUS: --analyse FILE (Fokussierte Git-Archaeologie)
## ═══════════════════════════════════════════════════════════════

```
KERN-IDEE:
  User zeigt auf eine Stelle: "Das scheint unnoetig."
  DiffReduce traced die KOMPLETTE Geschichte dieser Aenderung.
  Wie ein Detektiv: Wann eingefuehrt? Warum? Existiert der Grund noch?
  Welche anderen Aenderungen haengen dran?

WANN --analyse?
  - User sieht etwas Verdaechtiges beim Code-Review
  - /_R_orchestrate oder /_AC_orchestrate hat etwas geflaggt
  - Default-Modus zeigt FRAGLICH, User will Kausalkette verstehen
  - "Warum ist das internal? Das war doch public..."

INTERAKTIV:
  --analyse ist ein DIALOG. Der TL praesentiert die Kausalkette
  und fragt den User: "Soll ich das zurueckbauen?"
```

### AN-1: Target bestimmen

```
Aufruf-Varianten:
  /_DiffReduce DCSRE-882 --analyse VDEK.DCSP.Application.csproj
  /_DiffReduce DCSRE-882 --analyse "InternalsVisibleTo"
  /_DiffReduce DCSRE-882 --analyse DicImportService.cs:230-240
  /_DiffReduce DCSRE-882 --analyse "*.csproj"

Target-Aufloesung:
  1. Ist es ein Dateipfad? → git diff develop...HEAD -- {FILE}
  2. Ist es ein Pattern?   → git diff develop...HEAD -- {PATTERN}
  3. Ist es ein String?    → git log develop...HEAD -S "{STRING}" --oneline
  4. Ist es Datei:Zeilen?  → git diff develop...HEAD -- {FILE}, dann Zeilen filtern

Ergebnis: TARGET_FILES = [Liste betroffener Dateien]
          TARGET_STRING = String/Pattern (falls -S Suche)
```

### AN-2: Git-Archaeologie

```
Pro TARGET_FILE:

1. Alle Commits die die Datei beruehren:
   git log develop...HEAD --oneline -- {FILE}

2. Falls TARGET_STRING:
   git log develop...HEAD -S "{STRING}" --oneline
   → Zeigt Commits die den String EINFUEHREN oder ENTFERNEN

3. Pro gefundenem Commit:
   a) git show {HASH} -s --format="%H %s"  → Hash + Message
   b) git show {HASH} --stat               → Gesamter Commit-Scope
   c) git show {HASH} -- {FILE}            → Aenderung in dieser Datei
   d) ANDERE Dateien im selben Commit       → Gekoppelte Aenderungen?

4. Chronologie aufbauen:
   [Commit 1] → [Commit 2] → ... → [HEAD]
   Pro Commit: Was wurde geaendert? Warum? (Message = Intent)
```

### AN-3: Kausalkette rekonstruieren

```
AUSGABE-FORMAT (dem User praesentieren):

═══ KAUSALKETTE: {TARGET} ═══

┌─ {HASH_1} ({DATE_1}): "{MESSAGE_1}"
│  Fuehrte ein: {WAS_EINGEFUEHRT}
│  Zusammen mit: {ANDERE_DATEIEN_IM_COMMIT}
│  Grund: {INTENT_AUS_MESSAGE}
│
├─ {HASH_2} ({DATE_2}): "{MESSAGE_2}"
│  Aenderte: {WAS_GEAENDERT} (von X auf Y)
│  Grund: {INTENT}
│
└─ {HASH_3} ({DATE_3}): "{MESSAGE_3}"
   REVERT: Entfernte {ANDERE_DATEIEN_AUS_HASH_1}
   ABER: {TARGET} wurde NICHT beruehrt
   → Status: VERWAIST (Grund existiert nicht mehr)

═══ GEKOPPELTE AENDERUNGEN ═══

Folgende Aenderungen wurden im selben Commit ({HASH_1}) eingefuehrt
und sollten ZUSAMMEN bewertet werden:

  1. {DATEI_A}: {AENDERUNG_A}  → Status: {REVERTET/AKTIV}
  2. {DATEI_B}: {AENDERUNG_B}  → Status: {REVERTET/AKTIV}
  3. {DATEI_C}: {AENDERUNG_C}  → Status: {UEBERLEBT/VERWAIST}

═══ EMPFEHLUNG ═══

{EMPFEHLUNG}: {BEGRUENDUNG}
Revert-Gruppe: {DATEIEN_DIE_ZUSAMMEN_REVERTET_WERDEN_SOLLTEN}
```

### AN-4: Dialog mit User

```
AskUserQuestion:
  "[Kausalkette wie oben]

  Empfehlung: {EMPFEHLUNG}

  Optionen:
    REVERT  → Aenderung(en) zurueckbauen (gekoppelt)
    BEHALTEN → Ist beabsichtigt, kein Revert
    WEITER  → Naechstes Target analysieren (bei Pattern/Multi-File)
    FERTIG  → Analyse beenden"

Bei REVERT:
  → Alle gekoppelten Aenderungen als Gruppe reverten
  → Build + Tests laufen lassen
  → GRUEN: Revert bestaetigt
  → ROT: Revert des Reverts, Item als NOTWENDIG markieren

Bei --theoretic + --analyse:
  → Kein REVERT anbieten, nur BEHALTEN/WEITER/FERTIG
  → Report schreiben mit Empfehlungen
```

### AN-5: Analyse-Report

```
Output: .claude/analysis/findings/{NAME}-DR-ANALYSE-{TARGET_SHORT}-{TS}.md

Frontmatter:
  target: {TARGET}
  commits_analysiert: {N}
  kausalketten: {K}
  spur8_kandidaten: {M}
  gekoppelte_gruppen: {G}
  empfehlung: {REVERT|BEHALTEN|FRAGLICH}
```

### KURZLEBIG_PROMPT: Analyse-Worker ({middle})

```
Du bist ein DiffReduce-Analyse-Worker fuer fokussierte Git-Archaeologie.
Agent-Name: dr-{name}-analyse

═══ DEIN AUFTRAG ═══

Eine spezifische Stelle im Diff forensisch untersuchen.
Kausalkette rekonstruieren: Wann, warum, durch wen eingefuehrt?

Target:   {TARGET}
Task-ID:  {TASK_ID}
Projekt:  {PROJEKT_PFAD}

═══ KONTEXT ═══

Feature-Ziel: {ZIEL}

═══ SCHRITTE ═══

1. Target aufloesen:
   - Dateipfad? → git diff develop...HEAD -- {FILE}
   - String?    → git log develop...HEAD -S "{STRING}" --oneline
   - Pattern?   → git diff develop...HEAD -- {PATTERN}

2. Alle beruehrenden Commits chronologisch auflisten:
   git log develop...HEAD --oneline --reverse -- {FILE}

3. Pro Commit:
   a) git show {HASH} -s --format="%H %ai %s"
   b) git show {HASH} --stat  (gesamter Scope)
   c) git show {HASH} -- {FILE}  (Diff fuer diese Datei)
   d) Andere Dateien im Commit → Gekoppelte Aenderungen

4. Kausalkette aufbauen:
   EINFUEHRUNG → AENDERUNG → REVERT? → UEBERLEBEND?

5. SPUR-8 Pruefung:
   - Wurde der GRUND fuer die Aenderung revertet?
   - Ueberlebte die Aenderung den Revert?
   - Gibt es gekoppelte Aenderungen die MIT-revertet werden sollten?

6. Revert-Gruppe identifizieren:
   - Alle Dateien die zum selben Grund gehoeren
   - Alle muessen ZUSAMMEN revertet werden (oder gar nicht)

7. Report schreiben:
   {PROJEKT_PFAD}/.claude/analysis/findings/{NAME}-DR-ANALYSE-{TARGET_SHORT}-{TS}.md
   Mit: Kausalkette (formatiert), Empfehlung, Revert-Gruppe

8. SendMessage an "team-lead":
   "DR-Analyse {TARGET}: {N} Commits, {K} Kausalketten.
    Empfehlung: {EMPFEHLUNG}. Revert-Gruppe: {G} Dateien."

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen
- git show/log/diff LESEN ist erlaubt (READ-ONLY)
- NUR diese Analyse, dann fertig
```

---

## ═══════════════════════════════════════════════════════════════
## CASE STUDY: InternalsVisibleTo (Referenz-Beispiel fuer SPUR-8)
## ═══════════════════════════════════════════════════════════════

```
KONTEXT: DCSRE-882, Branch feature/DCSRE-882_MetaDaten_Analyse

COMMIT-KETTE:
  a0a608c80 — "DCSRE-882: JSON-Sidecar mit 10 EM0012-Metadatenfeldern"
    → Fuehrte ein: InternalsVisibleTo in .csproj
    → Fuehrte ein: Sidecar-Code in DicImportService
    → ZUSAMMEN im selben Commit

  1d833637e — "DCSRE-882: Inline-Kommentare ergaenzt und XML-Docs bereinigt"
    → Aenderte: ParseDatenArt von public → internal
    → Folge-Aenderung (internal wegen InternalsVisibleTo)

  [Kurskorrektur v6.0] — Revert
    → ENTFERNTE: JSON-Sidecar-Code
    → NICHT BERUEHRT: .csproj (InternalsVisibleTo), DicImportService (internal)

ERGEBNIS:
  InternalsVisibleTo in .csproj → VERWAIST (SPUR-8)
  ParseDatenArt internal → VERWAIST (SPUR-8)
  Beide bilden Revert-Gruppe K-1 (.csproj + .cs)

LOESUNG:
  Option A: ParseDatenArt zurueck auf public + InternalsVisibleTo entfernen
  → 2 Dateien, 6 Zeilen weniger im Diff
  → Tests weiterhin GRUEN (ParseDatenArt war vorher public)

LEARNINGS:
  1. Statischer Diff-Scan sieht NUR "InternalsVisibleTo ist da"
  2. Git-History-Scan sieht "eingefuehrt mit Sidecar, Sidecar revertet"
  3. Ohne History: kein Beweis fuer "verwaist"
  4. Cross-File-Kopplung: .csproj allein reverten reicht NICHT
```

---

## Fehlerbehandlung

| Fehler | Aktion |
|--------|--------|
| develop nicht erreichbar | Fallback: git merge-base HEAD origin/develop |
| SPEC fehlt | Degraded: nur ARTEFAKT-CHECK (Dimension 1), kein ANSATZ-CHECK |
| Task.md fehlt | Degraded: AK-Liste aus SPEC extrahieren, ZIEL aus Branch-Name ableiten |
| 0 geaenderte Dateien | CLEAN melden, kein Spawn |
| Explorer crashed | Team Lead spawnt neuen Worker (einmalig) |
| Synthese crashed | Team Lead schreibt Summary manuell |

---

## Lifecycle-Integration

```
╔══════════════════════════════════════════════════════════════╗
║  WO LEBT /_DiffReduce IM GESAMTBILD?                        ║
║                                                              ║
║  Post-Implementation Pipeline:                               ║
║                                                              ║
║  /_I_fanIn                                                   ║
║      ↓                                                       ║
║  /_stage_orchestrate   (Commits normieren, Security Gate)    ║
║      ↓                                                       ║
║  /_DiffReduce          (Diff minimieren, Daseinsberechtigung)║
║      ↓                                                       ║
║  /_AC_orchestrate      (Architektur-Konformitaet pruefen)    ║
║      ↓                                                       ║
║  /_gap                 (IST vs SOLL Delta)                   ║
║      ↓                                                       ║
║  /_I_diffAudit         (Tiefes Traceability-Mapping)         ║
║      ↓                                                       ║
║  /_Pre_PR              (9 Quality Gates parallel)            ║
║      ↓                                                       ║
║  PR erstellen                                                ║
║                                                              ║
║  EINORDNUNG:                                                 ║
║  DiffReduce = ERST aufräumen (weniger Diff)                  ║
║  AC = DANN Architektur prüfen (am reduzierten Diff)          ║
║  diffAudit = SPAETER tiefes Traceability (am finalen Diff)   ║
║                                                              ║
║  BEZIEHUNG ZU /_I_diffAudit:                                 ║
║  DiffReduce frueh (grob, Reduktion) → diffAudit spaet (tief)║
║  DiffReduce entfernt Noise → diffAudit hat weniger zu tun    ║
║  DiffReduce: "Brauchen wir das?"                             ║
║  diffAudit:  "Trackt das zu einem W{n}?"                     ║
╚══════════════════════════════════════════════════════════════╝
```

---

## QUICK-START

**Standard-Aufruf (Default-Modus):**
```
1. /_stage_orchestrate (Commits normiert)
2. /_DiffReduce DCSRE-882
3. Report lesen: REVERT-Kandidaten pruefen
4. AUFRAEUMEN → sicherste zuerst entfernen
5. /_AC_orchestrate (am schlanken Diff)
```

**Tiefe Analyse (FullScan-Modus):**
```
1. /_DiffReduce DCSRE-882 normal --fullScan
2. Commit-Ketten + Verwaiste Artefakte im Report
3. Revert-Gruppen (gekoppelte Dateien) zusammen reverten
4. Build + Tests nach jedem Revert-Block
```

**Verdaechtige Stelle untersuchen (Analyse-Modus):**
```
1. /_DiffReduce DCSRE-882 --analyse "InternalsVisibleTo"
2. Kausalkette lesen: Wann eingefuehrt? Warum? Grund noch da?
3. REVERT / BEHALTEN entscheiden
4. Gekoppelte Aenderungen automatisch mit-reverten
```

**Schnell-Check:**
```
/_DiffReduce DCSRE-882 easy
→ TL scannt Diff direkt, kein Worker-Spawn
→ Ergebnis in 1-2 Minuten
```

---

ARGUMENTS: $ARGUMENTS
