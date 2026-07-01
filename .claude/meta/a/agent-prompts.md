# Agent-Prompts (A-Pipeline)

Referenz fuer `/_A_orchestrate` Phase 3 (Agent-Prompts) und Phase 4.1a (Puppet-Master-Orchestrierung).

## Fresh-Modus Agent-Prompt (pro Task)

```
Du bist ein Single-Command-Agent fuer die Analyse-Pipeline.
Agent-Name: a-{name}-{command}
Team: a-{name}

═══ DEIN AUFTRAG ═══

Genau 1 Command ausfuehren, dann fertig.

Command:     /{COMMAND} {NAME} {DIFFICULTY}
Task-ID:     {TASK_ID}
Projekt:     {PROJEKT_PFAD}

═══ SCHRITTE ═══

1. Lade den Command via Skill-Tool:
   Skill(skill="{COMMAND}", args="{NAME} {DIFFICULTY}")
   Beispiele:
     Skill(skill="_model", args="DCSRE-31 normal")
     Skill(skill="_analyse", args="DCSRE-31 normal")
     Skill(skill="_gap", args="DCSRE-31")
   WICHTIG: Nutze das Skill-Tool — NICHT die .md-Datei direkt lesen!
2. Fuehre den geladenen Skill vollstaendig aus.
3. TaskUpdate {TASK_ID} status=completed
4. SendMessage an "team-lead":
   "{COMMAND} {NAME}: [2-3 Saetze Summary]"

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- IMMER Skill-Tool verwenden — niemals .md-Datei manuell lesen als Ersatz
- NUR dieser eine Command, dann fertig
- Absolute Pfade fuer alles: {PROJEKT_PFAD}/...
```

## Wellen-Task-Vorlage: Explorer (Welle 1)

```
Subject: "[WORKER-MODE] {Command}: Welle 1 - Explorer E{NN} {fokus}"
ActiveForm: "Exploring {fokus}"
Description: |
  [WORKER-MODE] Welle 1: Explorer E{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}
  INPUT: .claude/crumbs/{NAME}_crumbs.md, Task.md
  OUTPUT: .claude/analysis/exploration/{NAME}-E{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=exploration, agent=E{NN}, status=final, primaerquelle_gelesen: true
  Aufgabe: Kartographiere den Fokus-Bereich. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

## Wellen-Task-Vorlage: Drafter (Welle 2)

```
Subject: "[WORKER-MODE] {Command}: Welle 2 - Drafter D{NN} {fokus}"
ActiveForm: "Drafting {fokus}"
Description: |
  [WORKER-MODE] Welle 2: Drafter D{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}

  # ═══ INV-SP-1 (RF-08, BL-016): Anti-Stille-Post Primaerquellen-Pflicht ═══
  # Explorer-Outputs sind WEGWEISER (drogowskaz), KEINE Faktenquelle.
  # Du MUSST Primaerquellen SELBST lesen und EIGENE Analyse machen.
  # Anti-Pattern: haiku beobachtet → sonnet interpretiert haiku → Fehler-Kaskade.
  # Qualitaets-Kaskaden-Regel: Jede Welle eigenstaendig an Primaerquellen.

  PRIMAERQUELLEN (PFLICHT-READ — eigene Analyse):
    .claude/crumbs/{NAME}_crumbs.md
    {VAULT}/Task.md
    .claude/models/{NAME}_Model.md (wenn vorhanden)
  KOMPASS (NUR Scope-Eingrenzung, NICHT als Faktenquelle):
    .claude/analysis/exploration/{NAME}-E*.md
  OUTPUT: .claude/analysis/drafts/{NAME}-{command}-D{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=drafts, agent=D{NN}, status=final, primaerquelle_gelesen: true
  Aufgabe: Tiefenanalyse des Fokus-Bereichs. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

## Wellen-Task-Vorlage: Synthese (Welle 3)

```
Subject: "[WORKER-MODE] {Command}: Welle 3 - Synthese"
ActiveForm: "Synthesizing {command} results"
Description: |
  [WORKER-MODE] Welle 3: Synthese fuer {NAME}

  # ═══ INV-SP-1 (RF-08, BL-016): Anti-Stille-Post Primaerquellen-Pflicht ═══
  # Drafts sind Inspiration, NICHT Faktenquelle.
  # Du MUSST JEDE Aussage an Primaerquellen verifizieren.
  # SD-Agents (Spec-Drafter) lesen Primaerquellen DIREKT (AK-08-04).
  # Bei IDD-Feature: Schwester-Implementierung ist der Vertrag — direkter Code-Vergleich (AK-08-05).

  PRIMAERQUELLEN (PFLICHT-READ — eigene Verifikation):
    .claude/crumbs/{NAME}_crumbs.md
    {VAULT}/Task.md
    .claude/models/{NAME}_Model.md (wenn vorhanden)
    exploration/{NAME}-E*.md (fuer Kontext)
  KOMPASS (NUR Inspiration, NICHT als Faktenquelle):
    .claude/analysis/drafts/{NAME}-{command}-D*.md
  OUTPUT: {final artifact} (z.B. models/{NAME}_Model.md oder analysis/synthese/{NAME}-SPEC.md)
  Frontmatter-Pflicht: wave=synthese, status=final, primaerquelle_gelesen: true
  Aufgabe: Synthetisiere alle Drafts zu finalem Artefakt. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

## Resync-Modus: modelMaintain Agent-Prompt

```
Du bist ein Single-Command-Agent fuer Model-Resync.
Agent-Name: a-{name}-modelMaintain
Team: a-{name}

═══ DEIN AUFTRAG ═══

Model aktualisieren basierend auf Code-Aenderungen seit letztem Sync.

Command:     /_SC_modelMaintain {NAME} {DIFFICULTY}
Task-ID:     {TASK_ID}
Projekt:     {PROJEKT_PFAD}

═══ RESYNC-KONTEXT ═══

Letzter Sync-Commit: {LAST_SYNC_COMMIT}
Aktueller Commit: {CURRENT_COMMIT}
Diff seit Model-Erstellung:
{DIFF_STAT}

WICHTIG: Lies den git diff um zu verstehen was sich geaendert hat.
Aktualisiere das Model mit den neuen Erkenntnissen:
- Neue W{n} fuer neue Code-Aenderungen
- GC fuer Annahmen die durch Code widerlegt wurden
- Kap. 6a aktualisieren

Falls KEIN OBSERVE-File existiert (out-of-cycle):
→ Nutze den git diff als Input STATT OBSERVE-File.
→ Der Diff IST deine Observation.

Nach Update: Setze Model-Frontmatter:
  last_sync_commit: {CURRENT_COMMIT}
  last_sync_date: {HEUTE}

═══ SCHRITTE ═══

1. Lade den Command via Skill-Tool:
   Skill(skill="_SC_modelMaintain", args="{NAME} {DIFFICULTY}")
   WICHTIG: Nutze das Skill-Tool — NICHT die .md-Datei direkt lesen!
2. Lies git diff {LAST_SYNC_COMMIT}..{CURRENT_COMMIT}
3. Fuehre modelMaintain aus (Diff als Input statt OBSERVE)
4. Update Model-Frontmatter (last_sync_commit)
5. TaskUpdate {TASK_ID} status=completed
6. SendMessage an "team-lead": Summary

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR dieser eine Command, dann fertig
```

## model_fuer() Hilfsfunktion

```
FUNKTION model_fuer(level):
  IF level == "opus":   RETURN "general-opus"
  IF level == "sonnet": RETURN "general-sonnet-4"
  IF level == "haiku":  RETURN "haiku"  # haiku → dedizierter haiku-Agent (analog _I_orchestrate)
```
