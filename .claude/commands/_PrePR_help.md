---
type: satellite
---

# Pre-PR Quality Gates - Hilfe & Uebersicht

Zeige die Uebersicht der Pre-PR Quality Gate (/_Pre_PR*) Commands.

## Aufruf

```
/_PrePR_help
```

---

## POSITION IN DER PIPELINE-REISE (3er-Doppel-Sicht, NEU 2026-05-24)

> **Cross-Reference:** Vollstaendige Reise + Geister-Tabelle: `/_help` TEIL 10
> Methodik: `.claude/INSTRUCTION_full_scan_2026-05-24.md`

**Wo sitzt /_Pre_PR_orchestrate in der Gesamt-Reise?**

```
/_BDF_orchestrate EMPTY-Handler (alle Items DONE, testRun_done=true)
                                  │
                                  ▼
                              ★G#9 → /_PostBatch_orchestrate
                                          │
                                          │ Tests + Commit
                                          ▼
                              ★G#10 → /_Pre_PR_orchestrate (9 Quality Gates PARALLEL)
                                          │
                                          │ Build + Test + Battle-Test + Self-Test
                                          ▼
                              ★G#11 → /_BDF_orchestrate (Loop next BL)
                                       oder Terminal-Exit (alle BLs DONE)
```

**3er-Doppel-Fenster:**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `/_PostBatch_orchestrate`        | POSTBATCH_PIPELINE_STATE.batch_done + BDF_NEXT_TRIGGER |
| [N  ]    | `/_Pre_PR_orchestrate`           | LIEST + SCHREIBT (Quality-Reports + Auto-Fixes) |
| [N+1]    | `/_BDF_orchestrate` Phase 2      | BACKLOG_STATE + naechster Item-Pick |

**Geister-Beteiligung:**

- **Input-Geist G#10:** `/_PostBatch → /_Pre_PR_orchestrate` (nach Test + Commit GREEN)
- **Intra-Geister (9 Gates PARALLEL):** alle Gate-Worker in 1 Message gespawnt — kein sequenzieller Sub-Geist zwischen ihnen, nur ein JOIN am Ende
- **Output-Geist G#11:** `/_Pre_PR → /_BDF (Loop next BL)` — **⚠ BL-NEW Finding T86 CRITICAL-3:** H11 Auto-Loop derzeit BROKEN

**Modi-Variation:**

- **execute (Default):** Auto-Fix + Build + Test (Phase 4-5)
- **report (--prePr=report):** Read-only Scan → Presentation → interaktive Queue → Auto-Learn Meta (Phase 4-7)

**Step-Anzahl im 1-Pipeline-Durchlauf:**

- Phase 0a/0/0b → Phase 1/2 → 9 Gates parallel → Phase 3/3.5 → 4/4b/4c/4d → 5/5a/5b/6/7
- 0 eigene Berater (alle Logik in Sub-Commands)
- 9 Quality-Gate-Skills: `_Pre_PR_Tests`, `_Pre_PR_Naming`, `_Pre_PR_Cleanup`, `_Pre_PR_Dokumentation`, `_Pre_PR_Konstanten`, `_Pre_PR_Logging`, `_Pre_PR_Architektur`, `_Pre_PR_Analyzer`, `_Pre_PR_Migration`
- Phase 4d SkillLoadSelfTest (BL-159) — Mega-Agent-Detection via audit.jsonl
- Phase 4c Pattern-Battle-Test (BL-NEW-7?) — DRAFT-Pattern → PROMOTED bei 9-Gate-Pass

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
