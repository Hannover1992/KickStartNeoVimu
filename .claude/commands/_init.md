# /_init - Neues Projekt mit OmniCommand-Infrastruktur bootstrappen

```yaml
status: active
version: 1.0.0
created: 2026-02-21
type: command
chain_position: standalone
team_based: false
changelog: |
  v1.0: Initialer Entwurf. Bash-Script Wrapper.
        Kopiert Toolbox (Commands, Agents, Scripts, Patterns).
        Blank Manifest + Parking-Lot. Kein State-Ballast.
```

---

```
+======================================================================+
| COMMAND: /_init [PATH]                                                |
+======================================================================+
|                                                                        |
| ACTOR: DU (die ausfuehrende Claude-Instanz, KEIN Team)               |
|                                                                        |
| ZWECK: Neues Projekt mit OmniCommand-Infrastruktur bootstrappen.      |
|        Kopiert die TOOLBOX (.claude/commands, agents, scripts, etc.)  |
|        aber NICHT den State (models, synthese, wissen, Task.md).      |
|        Das neue Projekt startet mit leerem Manifest (PHASE=READY)    |
|        und leerem Parking-Lot.                                        |
|                                                                        |
| AUFRUF:                                                                |
|   /_init /pfad/zum/neuen/projekt                                      |
|   /_init  (ohne PATH → fragt nach)                                    |
|                                                                        |
| WAS WIRD KOPIERT (Infra/Toolbox):                                     |
|   .claude/commands/       (alle Commands)                              |
|   .claude/agents/         (Agent-Definitionen)                         |
|   .claude/scripts/        (Bash/PS1 Scripts)                           |
|   .claude/config/         (Konfiguration)                              |
|   .claude/patterns/       (Pattern-Library)                            |
|   .claude/tools/          (Tools)                                      |
|   .claude/reference/      (Referenz-Dokumente)                         |
|   .claude/meta/           (Meta-Konventionen)                          |
|   .claude/settings.local.json                                          |
|                                                                        |
| WAS WIRD BLANK ERSTELLT:                                               |
|   .claude/analysis/_manifest.md    (PHASE=READY, kein Feature)        |
|   .claude/analysis/_parking-lot.md (leer)                              |
|                                                                        |
| WAS WIRD NICHT KOPIERT (State):                                        |
|   .claude/models/*.md              (Feature-spezifisch)                |
|   .claude/wissen/*.md              (Feature-spezifisch)                |
|   .claude/crumbs/*.md              (Feature-spezifisch)                |
|   .claude/analysis/synthese/*      (Feature-spezifisch)                |
|   .claude/analysis/exploration/*   (Feature-spezifisch)                |
|   .claude/analysis/drafts/*        (Feature-spezifisch)                |
|   .claude/Task*.md                 (Feature-spezifisch)                |
|   .claude/pileOfMud/*              (Feature-spezifisch)                |
|   .claude/output/*                 (Feature-spezifisch)                |
+======================================================================+
```

---

## Ablauf

### Schritt 1: PATH bestimmen

Falls PATH als Argument gegeben → verwende ihn.
Falls KEIN PATH gegeben:

```
AskUserQuestion:
  header: "Projekt-Pfad"
  question: "Wohin soll das neue Projekt initialisiert werden?
    (Absoluter Pfad zum Zielverzeichnis)"
  options:
    - label: "Eingeben"
      description: "Pfad manuell eingeben"
  multiSelect: false
```

### Schritt 2: Script ausfuehren

```bash
bash .claude/scripts/initialize.sh {PATH}
```

### Schritt 3: Ergebnis melden

```
AUSGABE:
  "═══════════════════════════════════════════════════════
   Neues Projekt initialisiert: {PATH}
   ═══════════════════════════════════════════════════════

   Kopiert:  {N} Dateien (Toolbox)
   Blank:    Manifest (READY) + Parking-Lot (leer)
   Leer:     models/, wissen/, crumbs/, synthese/, ...

   Naechste Schritte:
     cd {PATH}
     /_A_orchestrate {FEATURE}    → neues Feature analysieren
     /_SC_orchestrate {FEATURE}   → Forschungszyklus starten
   ═══════════════════════════════════════════════════════"
```

---

ARGUMENTS: $ARGUMENTS
