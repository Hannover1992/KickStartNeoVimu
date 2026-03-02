# Pre-PR Quality Gates - Hilfe & Uebersicht

Zeige die Uebersicht der Pre-PR Quality Gate (/_Pre_PR*) Commands.

## Aufruf

```
/_PrePR_help
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  PRE-PR QUALITY GATES (1 Orchestrator + 9 Gates)                       ║
║                                                                         ║
║  Automatische Code-Qualitaetspruefung VOR Pull Requests.               ║
║  Datei-Listen aus git diff develop...HEAD.                             ║
║  9 Sonnet-Workers PARALLEL (1 pro Gate, Team-basiert).                ║
║  Re-Run Modus: nur FAIL-Gates wiederholen.                             ║
║                                                                         ║
║  ═══ ORCHESTRATOR ═══                                                  ║
║                                                                         ║
║  /_Pre_PR_orchestrate                                                  ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  PRE-PR-ORCHESTRATOR (v2.0 - Team-basiert)                      │   ║
║  │  → Datei-Listen ermitteln (git diff develop...HEAD)              │   ║
║  │  → Team erstellen + 9 Gate-Workers PARALLEL spawnen             │   ║
║  │  → Build + Test Verification nach allen Gates                   │   ║
║  │  → Gesamt-Report mit PASS/FAIL/WARN pro Gate                    │   ║
║  │  → Re-Run Modus: nur FAIL-Gates wiederholen                     │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  ═══ 9 QUALITY GATES ═══                                              ║
║                                                                         ║
║  Gate 1: /_Pre_PR_Tests                                                ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Test-Klassen Quality Gate                                       │   ║
║  │  → Prueft Test-Klassen auf Konventionen                         │   ║
║  │  → Naming, Arrange-Act-Assert, Test-Isolation                   │   ║
║  │  → Auto-Fix fuer einfache Verstoesse                            │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  Gate 2: /_Pre_PR_Naming                                               ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Naming-Konventionen Quality Gate                                │   ║
║  │  → PascalCase, camelCase, SCREAMING_SNAKE pruefung              │   ║
║  │  → Klassen, Methoden, Properties, Felder, Konstanten            │   ║
║  │  → Scope: develop...HEAD (nur geaenderte Dateien)               │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  Gate 3: /_Pre_PR_Cleanup                                              ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Cleanup Quality Gate                                            │   ║
║  │  → Auskommentierter Code, TODOs, Debug-Reste                    │   ║
║  │  → Unused Usings, leere Methoden, tote Branches                 │   ║
║  │  → Scope: develop...HEAD (nur geaenderte Dateien)               │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  Gate 4: /_Pre_PR_Dokumentation                                        ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Dokumentation Quality Gate                                      │   ║
║  │  → XML-Dokumentation fuer oeffentliche APIs                     │   ║
║  │  → Markdown-Struktur in .md Dateien                              │   ║
║  │  → Umlaut-Konsistenz (echte Umlaute vs. Ausschreibungen)       │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  Gate 5: /_Pre_PR_Konstanten                                           ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Konstanten Quality Gate                                         │   ║
║  │  → Magic Strings und Magic Numbers finden                       │   ║
║  │  → Vorschlaege fuer Konstanten-Extraktion                       │   ║
║  │  → Bestehende Konstanten-Klassen beruecksichtigen               │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  Gate 6: /_Pre_PR_Logging                                              ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Logging Quality Gate                                            │   ║
║  │  → Logging-Konventionen im Branch-Diff                          │   ║
║  │  → ILogger-Injection, LogLevel-Korrektheit                      │   ║
║  │  → Structured Logging Patterns                                   │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  Gate 7: /_Pre_PR_Architektur                                          ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Architektur Quality Gate                                        │   ║
║  │  → Controller, Interfaces, Provider, Konfiguration, DI          │   ║
║  │  → Schicht-Trennung (Controller → Service → Repository)        │   ║
║  │  → Dependency Injection Patterns                                 │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  Gate 8: /_Pre_PR_Analyzer                                             ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Analyzer Quality Gate                                           │   ║
║  │  → Analyzer-Konfiguration in .csproj Dateien                    │   ║
║  │  → Prueft + repariert fehlende/falsche Analyzer-Einstellungen   │   ║
║  │  → TreatWarningsAsErrors, NoWarn-Regeln                         │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  Gate 9: /_Pre_PR_Migration                                            ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Migration Quality Gate                                          │   ║
║  │  → Entity Framework Migrationen pruefen                         │   ║
║  │  → Korrekte Down()-Implementierung                               │   ║
║  │  → Migrations-Integritaet + Reihenfolge                         │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  AUFRUF:                                                               ║
║                                                                         ║
║  /_Pre_PR_orchestrate      Alle 9 Gates PARALLEL (Team-basiert)        ║
║  /_Pre_PR_orchestrate      Re-Run: nur FAIL-Gates wiederholen          ║
║  /_Pre_PR_Tests            Einzelnes Gate ausfuehren                   ║
║  /_Pre_PR_Naming           Einzelnes Gate ausfuehren                   ║
║  ...                       (jedes Gate ist einzeln aufrufbar)          ║
║                                                                         ║
║  NACH DEM PR (manuell gefixt, nicht vom Gate gefunden):               ║
║                                                                         ║
║  /_PrePR_Update_Meta       Fund als neue Regel in Meta-Datei schreiben ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  → Raw Input (Text oder Pfad) → Klassifiziert welches Gate       │   ║
║  │  → Schreibt R{N+1} in .claude/meta/codeKonvention/{gate}.md     │   ║
║  │  → Naechster Pre-PR-Lauf prueft diese Regel automatisch          │   ║
║  │  → Kein Git. Nur Meta-Datei.                                     │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  POSITION IN DER PIPELINE:                                             ║
║                                                                         ║
║  /_I_verify global → /_gap → /_I_diffAudit → [/_Pre_PR_orchestrate] → PR
║                                           → /_PrePR_Update_Meta (Lernschleife)
║                                                                         ║
║  VORAUSSETZUNG: /_I_diffAudit abgeschlossen (Cleanup bereinigt)       ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

ARGUMENTS: $ARGUMENTS
