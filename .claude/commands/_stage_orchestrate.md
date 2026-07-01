# /_stage_orchestrate — Commit-Normierung + Security Gate

```yaml
status: active
version: 2.0.0
created: 2026-02-28
updated: 2026-03-04
op: StageOrchestrate
phase: Post-FanIn
type: orchestration
chain_position: post-I-fanIn
team_based: true
hil_capable: true
dark_factory_capable: true
```

---

```
+===============================================================+
| VERTRAG: /_stage_orchestrate v2.0                             |
+===============================================================+
|                                                               |
| ROLLEN:                                                       |
|   TEAM LEAD (TL) = Richtlinie + Quality Gate                 |
|     - Liest Kontext (Manifest, git status)                   |
|     - Spawnt Stage-Worker                                     |
|     - Begleitet Worker als Dialog-Partner                    |
|     - KEINE direkten git-Operationen                         |
|     - Schreibt Report + Manifest nach Abschluss              |
|                                                               |
|   STAGE-WORKER = Staging + Grouping + Commit                 |
|     - Analysiert pending Aenderungen (git status/diff)       |
|     - Gruppiert Dateien nach Kohaesion                       |
|     - Arbeitet mit Hunks (git add -p) wenn noetig            |
|     - Formuliert normkonforme Commit-Messages                |
|     - Fragt TL via SendMessage VOR jedem Commit              |
|     - Committet NUR nach TL-Freigabe                         |
|     - Prueft eigene Messages gegen stage.md Normen           |
|                                                               |
| TL LIEST (Phase 1):                                          |
|   {VAULT}/_manifest.md   (NAME, hil, commit_freeze [AK-2])   |
|   git status --short              (pending Aenderungen)       |
|   git log BASE_BRANCH...HEAD      (bestehende Commits)       |
|                                                               |
| STAGE-WORKER LIEST:                                          |
|   .claude/commands/stage.md       (Normen-Tabellen)          |
|   git diff / git status           (Aenderungen analysieren)  |
|                                                               |
| TL SCHREIBT (Phase 3):                                       |
|   {VAULT}/_manifest.md              (Pattern A: State-Einzeiler|
|                                    stage_gate_status, ...)   |
|   {VAULT}/_manifest_protokoll.md    (SCHREIBT NICHT:         |
|                                    Pattern A, kein Protokoll)|
|   .claude/analysis/findings/      (stage-{NAME}-{TS}.md)    |
|                                                               |
| PRUEFT NICHT:                                                 |
|   .claude/commands/*.md           (K-R4)                     |
|   .claude/analysis/*.md           (interne OmniCommand-Docs) |
|                                                               |
| PIPELINE:                                                     |
|   [/_I_fanIn] → [/_stage_orchestrate] → [/_AC_orchestrate]   |
+===============================================================+
```

---

## Aufruf

```
/_stage_orchestrate
```

(Kein Parameter — liest GLOBAL_MODUS aus Manifest)

---

## Aufruf-Modi (BL-009)

Stage wird in zwei verschiedenen Kontexten aufgerufen:

| Modus | Aufrufer | Wann | Scope | Beschreibung |
|-------|----------|------|-------|-------------|
| **SDF-Modus** | SDF (Phase 2.5) | Nach jedem Item (GAP=0% + [x]) | Pro Item | SDF ruft stage per Skill() nach Batch-Item-Completion. Kleiner Commit pro Item. SDF bleibt Lifecycle-Owner. |
| **Standalone-Modus** | I_orchestrate (Nachphase) | Nach I-Pipeline core-scope | Pro Feature | I ruft stage selbst in Schritt 10 der Nachphase. Kein SDF-Kontext. Gesamter Feature-Branch wird gestaged. |

**Verhalten identisch:** In beiden Modi fuehrt stage die gleichen Phasen (SCOPE, PRUEFUNG, KORREKTUR, OUTPUT) aus.
Der Unterschied liegt ausschliesslich im Aufrufer und im Commit-Scope (1 Item vs. gesamter Branch).

---

## Rollen-Trennung (PFLICHT)

```
╔══════════════════════════════════════════════════╗
║  TEAM LEAD (TL)          STAGE-WORKER            ║
╠══════════════════════════════════════════════════╣
║  Liest Kontext           Liest git status/diff   ║
║  Spawnt Worker           Gruppiert Änderungen    ║
║  Empfängt Vorschläge     Formuliert Commit-Msg   ║
║  Quality Gate (Dialog)   Fragt TL VOR Commit     ║
║  Approved → Worker       Committet nach Freigabe ║
║  Schreibt Report         Meldet Fertig an TL     ║
╚══════════════════════════════════════════════════╝

REGEL: TL führt KEINE git-Operationen aus.
       Worker committet NIEMALS ohne TL-Freigabe.
```

---

## Phase 1: SCOPE — Kontext ermitteln (TL)

**Zweck:** Manifest lesen, Commit-Scope bestimmen, Pruef-Grundlage schaffen.

### Schritt 1.1: Manifest lesen

```bash
# Manifest-Pfad:
# {VAULT}/_manifest.md
```

Aus Manifest extrahieren:
- `NAME`: Feature-Name fuer Artefakt-Naming
- `BASE_BRANCH`: Merge-Basis-Branch (nach FanIn gesetzt — OQ-2: Hypothese, Manifest-Feld nach FanIn)
- `hil` (Session-Params, BL-174-Resolver): **DIE HiL-Quelle** — `hil=off` ⇒ Dark-Factory-Pfad (autonom, KEIN Go-Gate). PFLASTER 2026-06-11 (BL-295 AK-5): vorher war GLOBAL_MODUS der HiL-Proxy — falsch gekoppelt (PL-S2-06: BDF/Modus und HiL sind ORTHOGONAL) UND lückenhaft (nur small_dark_factory wurde erkannt; big_dark_factory fiel in den HiL-Zweig → Live-Bug DCSRE-1944 2026-06-11: „Go für den Stage-3-Commit?" trotz hil=off). GLOBAL_MODUS wird NICHT mehr für HiL gelesen.

**Fallback BASE_BRANCH:**
```bash
# Falls Manifest-Feld fehlt:
git merge-base HEAD develop
# Dann: git log $(git merge-base HEAD develop)...HEAD --oneline --no-merges
```

### Schritt 1.1b: Commit-Freeze-Gate (BL-299 AK-2 VERTRAG — gate-kritisch, KONDITIONAL)

**Zweck:** Ein aktives Commit-/PR-/Push-Verbot respektieren. In Freeze wird NICHT
committet — stattdessen sauberer Handover. Formalisiert die Annahme, die der Motor
(`dispatch_implement.js` runStageCommit-Prompt) bisher nur als Prosa-Instruktion trug
(„lies das Manifest auf ein Commit-Verbot") — jetzt deterministischer Vertrags-Schritt,
gleich ob via Motor-Workflow ODER direktem `Skill(_stage_orchestrate)` aufgerufen.

**Freeze-Signal lesen (kanonisches Feld + Prosa-Fallback):**
```bash
# Manifest: {VAULT}/_manifest.md
```
- **Kanonisch (strukturiert):** `DF_BATCH_STATE.commit_freeze` —
  `{active: bool, reason: <string>, scope: commit|push|pr (default commit)}`.
  `active: true` ⇒ Freeze aktiv.
- **Prosa-Fallback (Bestands-Form):** eine Manifest-Direktive wie
  „KEIN develop-Merge/Push/PR ohne Freigabe" (486-Manifest-Form 2026-06-09) wird als
  `commit_freeze.active=true, scope=push` erkannt, solange das strukturierte Feld fehlt.
- **Default (Feld fehlt UND keine Prosa-Direktive):** `commit_freeze.active=false` ⇒
  normaler Commit-Pfad (Happy-Path unverändert — die Gate ist KONDITIONAL, nie unbedingt).

**Gate-Verhalten:**
```
IF commit_freeze.active == true AND commit_freeze.scope deckt 'commit':
   # KEIN Commit. Sauberer Handover statt Auto-Commit.
   OUTPUT: "STAGE_COMMIT stage={stage}: frozen ({reason}) — kein Commit, Handover.
            Working-Tree-Stand + Diff an Lead uebergeben; Commit/Push macht der User
            nach Freigabe."
   → Phase 2/3 (Pruefung/Commit) SKIPPEN, sauber RETURN (kein Fehler, kein false-GREEN).
ELIF commit_freeze.active == true AND scope NUR push/pr (nicht commit):
   # Lokaler Commit erlaubt, aber NIE Push/PR/Merge (macht ohnehin der User).
   → normaler Commit-Pfad; Push/PR-Schritte bleiben dem User vorbehalten (Hinweis im Output).
ELSE:
   → normaler Commit-Pfad (Schritt 1.2 ff).
```

**Invariante INV-STAGE-FREEZE-1 (BL-299 AK-2):** Bei aktivem `commit_freeze` (Feld ODER
Prosa-Direktive) committet `_stage_orchestrate` NIE unbedingt — Freeze ⇒ Handover statt
Commit. Die Gate ist KONDITIONAL: ohne Freeze-Signal ist der Commit-Pfad unverändert.
Orthogonal zu `hil` (hil=off heisst autonom; Freeze heisst „auch autonom NICHT committen").

### Schritt 1.2: Commit-Liste erstellen

```bash
git log {BASE_BRANCH}...HEAD --oneline --no-merges
```

Ergebnis: Geordnete Liste mit HASH + erster Zeile der Message.

Fuer vollstaendige Messages pro Commit:
```bash
git show {HASH} --format="%B" -s
```

### Schritt 1.3: K-R4 Geheimhaltungs-Filter

**WICHTIG:** Nur Produkt-Commits pruefen. Commits die AUSSCHLIESSLICH `.claude/` Dateien aendern werden UEBERSPRUNGEN.

```bash
# Pro Commit: Pruefen ob Produkt-Dateien geaendert wurden
git diff-tree --no-commit-id --name-only -r {HASH} | grep -v "^\.claude/"
```

- Falls der Commit NUR `.claude/` Dateien aendert → SKIP (internes OmniCommand, nicht pruefen)
- Falls der Commit mindestens 1 Produkt-Datei aendert → PRUEFEN

### Schritt 1.4: Scope-Bestaetigung

Team Lead zeigt:
```
stage_orchestrate: {N} Produkt-Commits seit {BASE_BRANCH} gefunden.
Uebersprungen: {M} OmniCommand-interne Commits (.claude/ only).
Pruefe Normen...
```

---

## Phase 2: PRUEFUNG — Normen-Check + Security Gate

**Zweck:** Jeden Commit gegen `/stage.md` Normen und Security-Verbote pruefen.

### Schritt 2.1: Vollstaendige Messages laden

Fuer jeden Produkt-Commit aus Schritt 1.2 (nach K-R4 Filter):

```bash
git show {HASH} --format="%B" -s
```

Ergebnis pro Commit: `{HASH, FULL_MESSAGE, FIRST_LINE, REMAINING_LINES}`

### Schritt 2.2: Normen-Pruefung pro Commit

Fuer jeden Commit die folgenden Pruefungen ausfuehren. Jeder Verstoss wird mit Typ und Schwere protokolliert.

**Pruefung 1 — Format-Check (KRITISCH):**
```
Pruef-Pattern: ^[A-Z0-9_-]+: .+
Regel: Erste Zeile muss dem Format "$branch: $Title" entsprechen.
Verstoss wenn: Erste Zeile matcht NICHT das Pattern.
```

**Pruefung 2 — Laengen-Check (KRITISCH):**
```
Regel: Commit-Message darf nur EINE Zeile enthalten (nach Trim).
Verstoss wenn: Message enthaelt mehr als 1 nicht-leere Zeile.
```

**Pruefung 3 — Description-Check (MITTEL):**
```
Regel: Kein Description-Block nach der Titel-Zeile.
Verstoss wenn: Nach der ersten Leerzeile folgen weitere Zeilen mit Inhalt
               (ausgenommen: Co-Authored-By Trailer — diese werden separat geprueft).
```

**Pruefung 4 — Separator-Check (MITTEL):**
```
Pruef-Pattern: ^---
Regel: Kein "---" Separator nach der Titel-Zeile.
Verstoss wenn: Irgendeine Zeile nach Zeile 1 beginnt mit "---".
```

### Schritt 2.3: Security Gate (KRITISCH — dauerhaft, alle Modi)

**KANONISCHE QUELLE (BL-295 AK-3):** Die Leak-Patterns leben jetzt in `.claude/scripts/leak_patterns.py` (`scan_message()`) — Single-Source, geteilt mit dem git commit-msg-Hook `commit_msg_leak_guard.py` (AK-2, defense-in-depth, faengt auch manuelle Commits unabhaengig vom Skill-Pfad). Dieser Gate (Pruefung 1-5 unten) + der Hook DUERFEN NICHT driften — bei Pattern-Aenderung `leak_patterns.py` editieren.

Fuer jeden Commit die GESAMTE Message (inkl. Trailer) pruefen:

**Security-Pruefung 1 — Co-Authored-By Trailer:**
```
Pattern (case-insensitive): co-authored-by:
Verstoss wenn: Irgendeine Zeile matcht (case-insensitive).
Reaktion: Zeile muss entfernt werden.
```

**Security-Pruefung 2 — Co-Author Variante:**
```
Pattern (case-insensitive): co-author:
Verstoss wenn: Irgendeine Zeile matcht (case-insensitive).
Reaktion: Zeile muss entfernt werden.
```

**Security-Pruefung 3 — Anthropic-Erwaehnung:**
```
Pattern (case-insensitive): anthropic
Verstoss wenn: Das Wort "anthropic" kommt in der Message vor (case-insensitive).
Reaktion: Manuell pruefen — Zeile entfernen oder Message umschreiben.
```

**Security-Pruefung 4 — Claude als Co-Author:**
```
Pattern (case-insensitive): claude (im Trailer-Kontext, d.h. in Co-Authored-By Zeilen)
Verstoss wenn: "claude" erscheint in einer Trailer-Zeile (case-insensitive).
Reaktion: Zeile muss entfernt werden.
```

**Security-Pruefung 5 — Prozess-Cross-Referenzen (ANTI-PATTERN):**
```
Patterns (case-insensitive):
  - Gr\.\d+              → PR-Gruppen-Referenz (Gr.2, Gr.5, etc.)
  - PR-Gruppe            → Prozess-Bezeichnung
  - PR-Review            → Prozess-Bezeichnung
  - PL-Item              → Parking-Lot-Referenz
  - BDF|SDF|IDF          → Factory-Interna
  - BL-\d+               → Backlog-Item-Referenz
  - Parking.Lot          → Prozess-Artefakt
  - mode=answer          → Command-Parameter
  - Handschuh.Wechsel    → Prozess-Pattern
  - Wellen               → Architektur-Interna
  - K-Score              → Metrik-Interna
  - _[A-Z]_orchestrate   → Command-Referenz
  - /_\w+                → Slash-Command-Referenz

Verstoss wenn: Prozess-interne Bezeichnungen in der Commit-Message erscheinen.
  Diese verraten den internen AI-Workflow in der git-History.
  AUSNAHME: Branch-Name darf Ticket-ID enthalten (DCSRE-98 = OK).

Reaktion: Message umschreiben — nur fachlichen Inhalt behalten.
  FALSCH: "DCSRE-98: Service-Methode (PR-Review Gr.2, PL-Item CODE_CHANGE)"
  RICHTIG: "DCSRE-98: Service ReadByIdWithFullIncludes als eigene Methode"
```

**Zusammengefasster Pruef-Befehl (zur Schnell-Erkennung):**
```bash
git show {HASH} --format="%B" -s | grep -i -E "co-authored-by:|co-author:|anthropic|claude|Gr\.[0-9]|PR-Gruppe|PR-Review|PL-Item|BDF|SDF|IDF|BL-[0-9]|Parking.Lot|mode=answer|Handschuh|Wellen|K-Score|/_\w+"
```

**Security-Pruefung 6 — Process-Internal Markdown FILES (NEU 2026-05-11 BL-NEW-40):**
```
Pruefe ob Commit Process-Internal Markdown-Files ENTHAELT:

git show {HASH} --name-only --format= | grep -E "(^|/)(4_Blueprint|Crumbs|6_PL|2_Model|3_Spec|5_Gap|3_Audit|Implementation/sc-cycle)/.*\.md$|S[0-9]+-.*\.md$|R[0-9]+-COMPLETE\.md$|TDD-.*\.md$|GOLD-.*\.md$|PATTERN-S[0-9]+\.md$|TESTSEARCH-S[0-9]+\.md$|ARCHCONFORMANCE-S[0-9]+\.md$|REQCHECK-S[0-9]+\.md$|VERIFY-S[0-9]+\.md$|cron-audit\.md$|S1-cleanCodeArchitect.*\.md$|HANDOFF.*\.md$|OBSERVE.*\.md$|HYPOTHESE.*\.md$|QUALITYGATE.*\.md$"

Verstoss wenn: Markdown-Files unter diesen Pfaden/Pattern erscheinen.
  Diese sind BUSINESS-GEHEIMNIS (Process-Internals):
  - 4_Blueprint/   → Architekt-Outputs, Slice-Plans, Pattern-Zuweisung
  - Crumbs/        → Findings-Krumen, Round-Erkenntnisse
  - 6_PL/          → Parking-Lot (interne Findings)
  - 2_Model/       → Wissens-Modelle, W{n}-Strukturen
  - 3_Spec/        → Spezifikationen (oft Process-detailliert)
  - 5_Gap/         → Gap-Analysen (Process-State)
  - 3_Audit/       → Audit-Trail (Process-Events)
  - S{N}-*.md      → Stage-spezifische Sidecars (TDD-INIT, GOLDDEFINE, CLEANCODESLICE etc.)
  - R{N}-COMPLETE.md → Ring-Completion-Marker
  - HANDOFF/OBSERVE/HYPOTHESE/QUALITYGATE → SC-Cycle-Internals

Reaktion: Commit ZURUECKGEROLLT — Files muessen entfernt werden bevor neu committed.
  Workflow-Path-Correction:
    1. git reset --soft HEAD~1   (Commit ruecknehmen, Files in Staging)
    2. git reset HEAD <process-markdown-files>   (Files unstagen)
    3. mv {leaked-files} {VAULT}/{BL}/{matching-vault-path}/   (in Vault verschieben)
    4. git commit --no-verify   (neu, ohne Process-Markdowns)
  
  BL-NEW-40 Beweis-Spur: dc51ef513 (DCSRE-486 batch_2) enthielt 4_Blueprint/S1-R9-COMPLETE.md
  → CRITICAL Business-Geheimnis-Leakage. User-Direktive: "kein Markdown das Process-
  Internals verraet — Betriebsgeheimnis."
```

**Zusammengefasster Pruef-Befehl (erweitert mit Pruefung 6):**
```bash
# Message-Check (Pruefungen 1-5):
git show {HASH} --format="%B" -s | grep -i -E "co-authored-by:|co-author:|anthropic|claude|Gr\.[0-9]|PR-Gruppe|PR-Review|PL-Item|BDF|SDF|IDF|BL-[0-9]|Parking.Lot|mode=answer|Handschuh|Wellen|K-Score|/_\w+"

# File-Path-Check (Pruefung 6 NEU):
git show {HASH} --name-only --format= | grep -E "(^|/)(4_Blueprint|Crumbs|6_PL|2_Model|3_Spec|5_Gap|3_Audit)/.*\.md$|S[0-9]+-.*\.md$|R[0-9]+-COMPLETE\.md$|TDD-.*\.md$|cron-audit\.md$"
```

### Schritt 2.4: Verstoesse-Aggregation

Pro Commit wird eine Verstoesse-Liste erstellt:

```
VERSTOSS_LISTE = [
  { hash: "abc1234", typ: "FORMAT", schwere: "KRITISCH", details: "Fehlende Branch-Prefix" },
  { hash: "abc1234", typ: "CO_AUTHOR", schwere: "KRITISCH", details: "Co-Authored-By: Claude..." },
  ...
]
```

**Zusammenfassung nach Phase 2:**
```
PRUEF_ERGEBNIS:
  commits_gesamt: N
  commits_clean: X (keine Verstoesse)
  commits_mit_verstoessen: Y
  kritisch_count: K (Anzahl KRITISCH-Verstoesse)
  mittel_count: M (Anzahl MITTEL-Verstoesse)
  security_violations: S (Anzahl Security-Gate-Verstoesse)
```

Falls `commits_mit_verstoessen == 0` → Status PASS, direkt zu Phase 4 (OUTPUT).
Falls `commits_mit_verstoessen > 0` → weiter zu Phase 3 (KORREKTUR).

---

## Phase 3: KORREKTUR — HiL oder Dark Factory

**Zweck:** Identifizierte Verstoesse korrigieren (manuell oder autonom).

**Voraussetzung:** `commits_mit_verstoessen > 0` aus Phase 2.

### Schritt 3.0: Sicherheits-Backup

Vor jeglicher git-History-Aenderung:

```bash
# Backup-Tag erstellen (fuer Rollback bei Problemen)
git tag backup-pre-stage-$(date +%Y%m%dT%H%M%S)
```

### Schritt 3.1: Modus-Erkennung

**PFLASTER 2026-06-11 (BL-295 AK-5, Live-Bug DCSRE-1944):** HiL-Quelle ist der `hil`-Param
(Session-Params via BL-174-Resolver: `py -3 .claude/scripts/session_params_resolver.py resolve
--param=hil --bl-id={BL_ID}`; Fallback {VAULT}/_session_params.md **HiL:**). GLOBAL_MODUS ist
KEIN HiL-Proxy mehr (PL-S2-06-Entkopplung; alter Check erkannte zudem nur small_dark_factory —
big_dark_factory fiel fälschlich in den HiL-Zweig → „Go?"-Gate trotz hil=off).

```
hil_param = resolve(hil)   # off | cycle | phase | manual
IF hil_param == "off":
    → Dark Factory Modus (Schritt 3.3) — autonom, KEIN Go-Gate, KEIN User-Confirm
ELSE:
    → HiL-Modus (Schritt 3.2)
```

Sicherheitsnetz (unverändert, /_param-HiL-Semantik): irrecoverable Errors / Gate-FAIL-Blocker
eskalieren IMMER an den User — das ist Blocker-HiL, kein Confirm-Gate.

### Schritt 3.2: HiL-Modus (Normal — User-Bestaetigung erforderlich)

Fuer JEDEN Commit mit Verstoessen:

**Anzeige:**
```
VERSTOSS in Commit {HASH_SHORT}:
  Message: "{FIRST_LINE}"
  Verstoesse:
    - [{SCHWERE}] {TYP}: {DETAILS}
    - [{SCHWERE}] {TYP}: {DETAILS}
```

**User-Frage:** "Commit korrigieren? (ja/nein/abbruch)"

**Bei `ja`:**
1. Korrektur-Vorschlag generieren:
   - Security-Verstoesse: Betroffene Zeilen (Co-Authored-By, Anthropic) entfernen
   - Format-Verstoesse: Message in `$branch: $Title` Format korrigieren
   - Laengen-Verstoesse: Auf eine Zeile kuerzen
2. Korrektur-Vorschlag dem User zeigen
3. User bestaetigt → Korrektur durchfuehren (siehe Schritt 3.4)

**Bei `nein`:**
- Commit bleibt unveraendert
- Verstoss wird in Report protokolliert
- `stage_gate_status = FAIL`

**Bei `abbruch`:**
- Command stoppt sofort
- Kein Manifest-Update, kein Report
- Backup-Tag bleibt bestehen fuer Analyse

### Schritt 3.3: Dark Factory Modus (Autonom — kein HiL)

Fuer JEDEN Commit mit Verstoessen — automatisch korrigieren:

1. **Security-Korrektur (hoechste Prioritaet):**
   - Alle Zeilen mit Co-Authored-By / Co-Author / Anthropic / Claude entfernen
   - Nur die erste Zeile (Titel) behalten, alle Trailer entfernen

2. **Format-Korrektur:**
   - Falls Format nicht `$branch: $Title`: Versuche Branch-Name aus aktuellem Branch zu extrahieren
   - Neue Message: `{BRANCH_NAME}: {ORIGINAL_TITLE}` (ohne Trailer)

3. **Laengen-Korrektur:**
   - Falls mehrere Zeilen: Nur erste Zeile behalten (nach Trim)

4. Korrektur durchfuehren (siehe Schritt 3.4)

### Schritt 3.4: Korrektur-Ausfuehrung (ADR-1: Option C — Rebase-Script)

**Fall A — Nur der letzte Commit betroffen:**
```bash
git commit --amend --message "{KORRIGIERTE_MESSAGE}"
```

**Fall B — Mehrere Commits betroffen (non-interaktives Rebase):**

Fuer jeden betroffenen Commit ein Rebase durchfuehren. Strategie:

```bash
# Schritt 1: Backup verifizieren
git tag | grep backup-pre-stage

# Schritt 2: Non-interaktives Rebase mit exec
# Pro betroffenen Commit wird ein reword ausgefuehrt
GIT_SEQUENCE_EDITOR="sed -i 's/^pick {HASH_SHORT}/reword {HASH_SHORT}/'" git rebase -i {BASE_BRANCH}

# Alternative (falls GIT_SEQUENCE_EDITOR Probleme macht):
# Sequenzielles Amend per git rebase --exec
git rebase {BASE_BRANCH} --exec 'if [ "$(git rev-parse HEAD)" = "{FULL_HASH}" ]; then git commit --amend --message "{KORRIGIERTE_MESSAGE}"; fi'
```

**Bei Rebase-Konflikt:**
```
WARNUNG: Rebase-Konflikt bei Commit {HASH}.
Automatische Korrektur nicht moeglich.
→ stage_gate_status = FAIL
→ HiL anfordern: "Bitte manuell korrigieren"
→ git rebase --abort (Zuruecksetzen)
→ Backup-Tag verfuegbar: backup-pre-stage-{TS}
```

### Schritt 3.5: Korrektur-Zaehlung

```
KORREKTUR_ERGEBNIS:
  korrigiert: N (Anzahl erfolgreich korrigierter Commits)
  uebersprungen: M (User sagte "nein" im HiL-Modus)
  fehlgeschlagen: F (Rebase-Konflikte)
  status: CORRECTED (wenn N > 0 und F == 0)
         FAIL (wenn F > 0 oder M > 0)
```

---

## Phase 4: OUTPUT — Report + Manifest

**Zweck:** Ergebnisse dokumentieren, Pipeline-Uebergabe vorbereiten.

### Schritt 4.1: Gesamtstatus bestimmen

```
IF commits_mit_verstoessen == 0:
    STATUS = "PASS"
ELIF korrigiert > 0 AND fehlgeschlagen == 0 AND uebersprungen == 0:
    STATUS = "CORRECTED"
ELSE:
    STATUS = "FAIL"
```

### Schritt 4.2: Report schreiben

Datei: `.claude/analysis/findings/stage-{NAME}-{TS}.md`

Wobei:
- `{NAME}` = Feature-Name aus Manifest
- `{TS}` = ISO-Timestamp (z.B. `20260228T143022`)

**Report-Template:**
```markdown
# Stage Gate Report: {NAME}

**Datum:** {ISO_DATE}
**Status:** {STATUS}
**Modus:** {MODUS} (normal / small_dark_factory)
**BASE_BRANCH:** {BASE_BRANCH}

---

## Zusammenfassung

| Metrik | Wert |
|--------|------|
| Commits geprueft | {N} |
| Commits clean | {CLEAN} |
| Commits mit Verstoessen | {VIOLATIONS} |
| Korrekturen durchgefuehrt | {CORRECTED} |
| Security-Verstoesse | {SECURITY} |

## Geprueft: Alle Commits

| # | Hash | Message | Status |
|---|------|---------|--------|
| 1 | abc1234 | DCSRE-1189: ... | CLEAN |
| 2 | def5678 | DCSRE-1189: ... | VERSTOSS: CO_AUTHOR |

## Verstoesse (Details)

| # | Hash | Typ | Schwere | Details |
|---|------|-----|---------|---------|
| 1 | def5678 | CO_AUTHOR | KRITISCH | Co-Authored-By: Claude... |

## Korrekturen (vorher/nachher)

| # | Hash | Vorher | Nachher |
|---|------|--------|---------|
| 1 | def5678 | "msg mit Co-Author" | "msg ohne Co-Author" |
```

### Schritt 4.2b: Findings Rotation (Cleanup-Hook, CaseStudy MV-2a)

Stage-findings aelter als der aktuelle Run werden geloescht (git hat alle Commits):

```
STAGE_FILES = Glob("findings/stage-{NAME}-*.md")
IF COUNT(STAGE_FILES) <= 2:
  → SKIP (nichts zu rotieren)

SORTIERT = STAGE_FILES lexikographisch sortiert (TS im Namen garantiert Chronologie)
ZU_LOESCHEN = SORTIERT[0..COUNT-2]  # alle ausser den 2 neuesten

IF COUNT(ZU_LOESCHEN) > 10:
  → HiL: "{COUNT} alte Stage-findings gefunden. Loeschen? (j/n)"

Loesche ZU_LOESCHEN
Log: "Stage-Rotation: {COUNT(ZU_LOESCHEN)} alte Findings geloescht, {2} behalten"
```

**Sicherheit:** 0 Risiko — git hat alle Commits. Lexikographische Sortierung funktioniert
weil Timestamp-Format YYYYMMDDTHHMMSS chronologische Ordnung garantiert.

### Schritt 4.3: Manifest updaten

In `{VAULT}/_manifest.md` folgende Felder setzen/aktualisieren:

```
**stage_gate_status:** {STATUS}
**stage_corrections:** {N}
**stage_security:** {SECURITY_STATUS}
**stage_report:** .claude/analysis/findings/stage-{NAME}-{TS}.md
**stash_date:** {ISO_TIMESTAMP}
```

**MANIFEST = NUR REFERENZ, KEIN PROTOKOLL:**
- `{STATUS}` = exakt PASS, CORRECTED oder FAIL (KEINE Klammerzusaetze, KEIN Freitext)
- `{N}` = exakt eine Zahl (KEINE Commit-Hashes, KEINE Beschreibungen)
- `{SECURITY_STATUS}` = exakt PASS oder FAIL (KEINE Zahlen, KEINE Details)
- ALLE Details (welche Commits, welche Verstoesse, welche Korrekturen) gehoeren AUSSCHLIESSLICH in den Report unter `stage_report`
- Manifest-Felder sind maschinenlesbar — ein Downstream-Command muss `stage_gate_status == "PASS"` pruefen koennen ohne Freitext zu parsen

### Schritt 4.4: Abschluss-Meldung

```
stage_orchestrate ABGESCHLOSSEN:
  Status: {STATUS}
  Commits geprueft: {N}
  Korrekturen: {CORRECTED}
  Report: .claude/analysis/findings/stage-{NAME}-{TS}.md

  Naechster Schritt: /_AC_orchestrate
```

Falls STATUS == FAIL:
```
WARNUNG: stage_gate_status = FAIL.
/_AC_orchestrate wird diesen Status pruefen.
Bitte manuell korrigieren oder mit FAIL fortfahren.
```

---

## Skalierung — Worker-Spawn (optional, bei vielen Commits)

### Schwellenwert

```
IF Anzahl Produkt-Commits <= 10:
    → Team Lead prueft ALLE Commits selbst (kein Worker-Spawn)
IF Anzahl Produkt-Commits > 10:
    → Worker-Spawn: Commits in Batches aufteilen
```

### Worker-Architektur (ADR-2)

```
ACTOR: TEAM LEAD (stage_orchestrate)
WORKERS: 1 haiku-Agent pro Commit-Batch (KURZLEBIG_PROMPT)
BATCH_SIZE: 5 Commits pro Worker
```

### KURZLEBIG_PROMPT Template (fuer Commit-Batch-Pruefung)

```
Du pruefst {BATCH_SIZE} Commits gegen Commit-Message-Normen.

NORMEN (aus /stage.md):
| Norm | Regel | Schwere | Pruef-Pattern |
| Format | $branch: $Title | KRITISCH | ^[A-Z0-9_-]+: .+ |
| Laenge | Nur EINE Zeile | KRITISCH | Anzahl Zeilen == 1 |
| Co-Worker | Kein Co-Authored-By | KRITISCH | (?i)co-authored-by |
| Anthropic | Keine Erwaehnung | KRITISCH | (?i)anthropic |
| Claude | Kein Claude als Co-Author | KRITISCH | (?i)claude |
| Description | Kein Description-Block | MITTEL | Zeilen > 1 nach Leerzeile |
| Separator | Kein --- nach Titel | MITTEL | ^--- nach Zeile 1 |

COMMITS ZU PRUEFEN:
{COMMIT_BATCH}

AUSGABE-FORMAT (exakt):
ERGEBNIS:
- {HASH}: CLEAN
- {HASH}: VERSTOSS [{SCHWERE}] {TYP}: {DETAILS}

WICHTIG:
- Pruefe case-insensitive
- KEIN Commit ueberspringen
- Nur PRODUKT-Commits (keine .claude/ Pfade erwaehnen)
```

### Worker-Spawn-Ablauf

```
1. Team Lead teilt Commits in Batches (max 5 pro Batch)
2. Pro Batch: 1 haiku-Worker spawnen (Agent tool, run_in_background: true)
3. Warten auf alle Worker-Ergebnisse
4. Team Lead konsolidiert alle Verstoesse-Listen
5. Weiter mit Phase 3 (KORREKTUR) basierend auf konsolidierter Liste
```

---

## GLOBALE PARAMETER (/_param Override)

Lies `{VAULT}/_manifest.md` und suche nach GLOBAL_* Feldern.
Falls gesetzt, ueberschreiben sie die lokalen Parameter-Defaults:

| Quelle | Wirkung |
|---|---|
| `_session_params.md` | difficulty steuert Worker-Spawn (easy=kein Worker). ceiling/floor nicht direkt verwendet. |

**Modus-Bestimmung (PFLASTER 2026-06-11, BL-295 AK-5 — hil-Param ist die Quelle, NICHT GLOBAL_MODUS):**
```
hil_param = resolve(hil)            # Session-Params/BL-174-Resolver: off|cycle|phase|manual
IF hil_param == "off":
    modus = "dark_factory"          # autonom — kein Go-Gate (gilt fuer small UND big_dark_factory)
    hil = false
ELSE:
    modus = "normal"
    hil = true
# ALT (BUG, ersetzt): IF GLOBAL_MODUS == "small_dark_factory" -> dark_factory ELSE hil=true
# -> big_dark_factory fiel in ELSE -> User-Confirm trotz hil=off (Live DCSRE-1944 2026-06-11).
```

---

## ADR-Dokumentation

### ADR-1: Rebase-Strategie — Option C (Rebase-Script)

**Kontext:** Mehrere Commits muessen nicht-interaktiv umgeschrieben werden.
**Entscheidung:** Option C (GIT_SEQUENCE_EDITOR + git rebase -i) als Praeferenz.
**Begruendung:**
- Keine externen Abhaengigkeiten (vs. Option A: git filter-repo)
- Nicht deprecated (vs. Option B: git filter-branch, deprecated ab Git 2.36)
- Native git-Loesung
**Fallback:** Option D (git commit --amend) fuer einzelnen letzten Commit.

### ADR-2: Team-Architektur — 1 Worker pro Commit-Batch

**Kontext:** Bei vielen Commits (>10) wird die Pruefung parallelisiert.
**Entscheidung:** haiku-Workers fuer Normen-Pruefung, Team Lead fuer git-Operationen.
**Begruendung:**
- AC_orchestrate Pattern etabliert (KURZLEBIG_PROMPT Workers)
- Team Lead bleibt fuer git-Operationen zustaendig (Rebase, Amend)
- Workers pruefen nur, aendern nicht

### ADR-3: /stage.md als separates Normen-Dokument

**Kontext:** Normen koennen inline im Command oder extern definiert werden.
**Entscheidung:** `/stage.md` als separates maschinenlesbares Dokument.
**Begruendung:**
- Normen aendern sich unabhaengig vom Orchestrator
- Kann auch direkt von Menschen gelesen werden (Doku-Funktion)
- Entspricht OmniCommand-Pattern (stage.md, _param.md als separate Commands)

---

## Geheimhaltungs-Filter (K-R4)

**Kritische Regel:** OmniCommand-Existenz darf NICHT in git-History erscheinen.

1. **Pruef-Scope:** Nur Produkt-Commits (Feature-Branch Commits). `.claude/` Commits werden uebersprungen.
2. **Korrektur-Messages:** Korrigierte Commit-Messages duerfen KEINE OmniCommand-Pfade enthalten (`.claude/`, `/_stage_orchestrate`, etc.)
3. **Report-Pfade:** Reports liegen in `.claude/analysis/findings/` — diese Pfade werden NICHT in Commit-Messages geschrieben.
4. **Worker-Prompts:** KURZLEBIG_PROMPT erwaehnt KEINE internen Pfade oder OmniCommand-Begriffe.
