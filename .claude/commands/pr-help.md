---
type: satellite
---

PR-Workflow Hilfe anzeigen.

Zeige folgende Uebersicht:

```
╔══════════════════════════════════════════════════════════════════╗
║                     PR-WORKFLOW UEBERSICHT                       ║
╚══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────┐
│                         WORKFLOW                                 │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │  PR ERSTELLT │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐     ┌─────────────────┐
    │  /pr-init    │────▶│  /pr-planning   │
    │  (TFS holen) │     │ (3-Wellen)      │
    └──────────────┘     │ Haiku->Sonnet   │
                         │ ->Opus+Notify   │
                         └────────┬────────┘
                                  │
           ┌──────────────────────┘
           │
           ▼
    ╔══════════════╗
    ║  /pr-status  ║◀────────────────────────────┐
    ║  Was tun?    ║                             │
    ╚══════┬═══════╝                             │
           │                                     │
           ▼                                     │
    ┌──────────────┐                             │
    │  /pr-work N  │                             │
    │  (Details)   │                             │
    └──────┬───────┘                             │
           │                                     │
           ▼                                     │
    ┌──────────────┐                             │
    │ Code aendern │                             │
    │   + Commit   │                             │
    └──────┬───────┘                             │
           │                                     │
           ▼                                     │
    ┌──────────────┐                             │
    │/pr-work-done │                             │
    │  (Commits)   │                             │
    └──────┬───────┘                             │
           │                                     │
           ▼                                     │
    ┌──────────────┐                             │
    │  /pr-link N  │  Commits im Browser         │
    │  (Antwort-   │  + Antwort-Text generiert   │
    │   Text)      │                             │
    └──────┬───────┘                             │
           │                                     │
           ▼                                     │
    ┌──────────────┐                             │
    │/pr-findings N│  PR-Kommentare im Browser   │
    └──────┬───────┘                             │
           │                                     │
           ▼                                     │
    ┌──────────────┐                             │
    │ TFS: Antwort │  Manuell: Text einfuegen    │
    │ einfuegen    │                             │
    └──────┬───────┘                             │
           │                                     │
           ▼                                     │
    ┌──────────────┐     ┌─────────────────┐     │
    │  /pr-sync    │────▶│   Kategorien    │─────┘
    │  (Update)    │     │   aktualisiert  │
    └──────────────┘     └─────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    KURZREFERENZ (pro Gruppe)                     │
└─────────────────────────────────────────────────────────────────┘

  /pr-work N → Code + /stage → /pr-work-done hash1,hash2 →
  /pr-link N → /pr-findings N → [TFS Antwort] → /pr-sync


┌─────────────────────────────────────────────────────────────────┐
│                     KATEGORIEN (in /pr-status)                   │
└─────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────┐
    │  AKTION ERFORDERLICH                                    │
    │  ════════════════════                                   │
    │  Reviewer hat geantwortet                               │
    │  → Du musst reagieren (Code oder Antwort)               │
    └─────────────────────────────────────────────────────────┘
                              │
                              ▼ (nach Antwort + /pr-sync)
    ┌─────────────────────────────────────────────────────────┐
    │  WARTET AUF REVIEWER                                    │
    │  ════════════════════                                   │
    │  Du hast zuletzt geantwortet                            │
    │  → Ball liegt beim Reviewer, abwarten                   │
    └─────────────────────────────────────────────────────────┘
                              │
                              ▼ (Reviewer akzeptiert)
    ┌─────────────────────────────────────────────────────────┐
    │  ABGESCHLOSSEN                                          │
    │  ══════════════                                         │
    │  Keine Aktion noetig                                    │
    └─────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    ALLE COMMANDS (15)                            │
└─────────────────────────────────────────────────────────────────┘

HAUPTCOMMANDS:
──────────────
  /pr-status            Uebersicht: Was muss ich tun? + Aufwand
  /pr-work <nr>         Gruppe bearbeiten (Details anzeigen)
  /pr-sync              TFS-Status aktualisieren + Fortschritt
  /pr-help              Diese Hilfe anzeigen

SETUP & ANALYSE:
────────────────
  /pr-init <id>         Rohe Daten von TFS holen
  /pr-planning [nrs]    3-Wellen-Analyse (Haiku->Sonnet->Opus)
                        Ohne nrs: Alle offenen Gruppen
                        Mit nrs: Nur bestimmte (z.B. /pr-planning 2,4)

DETAILS & BROWSER:
──────────────────
  /pr-overview <nrs>    Detaillierte Planning-Ergebnisse anzeigen
                        (z.B. /pr-overview 2 oder /pr-overview 2,4,11)
  /pr-plan <nr>         Nur Details einer Gruppe anzeigen
  /pr-findings <nr>     Alle Threads einer Gruppe im Browser
  /pr-open <ids>        Einzelne Thread-IDs im Browser
                        (z.B. /pr-open 121074,121075)
  /pr-link <nr>         Commit-URLs anzeigen (zum Kopieren)

ARBEIT ABSCHLIESSEN:
────────────────────
  /pr-work-done <hashes>
                        Commits zuordnen + Gruppe abschliessen
                        (z.B. /pr-work-done abc123,def456)

COMMITS & STATUS:
─────────────────
  /pr-commit <nr>       Commit erstellen + mit Gruppe verknuepfen
  /pr-add-commit <nr>   Existierenden Commit verknuepfen
  /pr-set-status <nr> <status>
                        Status manuell setzen
                        (pending/waiting/done/wontfix)


┌─────────────────────────────────────────────────────────────────┐
│                         DATEIEN                                  │
└─────────────────────────────────────────────────────────────────┘

  .claude/analysis/pr-{id}-raw.json    Rohe TFS-Daten
  .claude/analysis/pr-{id}-state.json  Gruppierung + Status
  .claude/scripts/pr/*.ps1             PowerShell-Skripte

```
