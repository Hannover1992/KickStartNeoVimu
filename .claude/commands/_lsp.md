# /_lsp — LSP-Nutzungs-Helper & Agent-Reminder

**Status:** NEU v1.0 (2026-04-23)
**Typ:** Utility + Enforcement-Hinweis
**Zweck:** Agents daran erinnern, **vor** Code-Aenderungen das LSP-Tool zu nutzen — verhindert teures "Hin-und-Her" durch unvollstaendige Scope-Analyse.

---

## Motivation

User-Beobachtung (2026-04-23): Agents machen haeufig Code-Aenderungen ohne vorher Dependencies/Referenzen zu pruefen. Folge: nachtraegliche Fixes, Compile-Fehler, vergessene Caller, verpasste Test-Updates. Die Iterationen werden teuer (Context + Zeit).

**Regel:** LSP ist das schnellste Werkzeug fuer **vollstaendige Scope-Erfassung** vor einer Aenderung. Billiger als spaetere Korrekturen.

---

## Wann /_lsp nutzen (Pflicht-Checkpoints)

| Situation | LSP-Operation | Grund |
|-----------|---------------|-------|
| Methode/Feld umbenennen | `findReferences` | Alle Caller finden |
| Return-Typ aendern | `findReferences` | Alle Consumer (Tests, Wrapper) erfassen |
| Interface-Methode hinzufuegen/entfernen | `findReferences` + `findImplementations` | Alle Implementierer |
| Symbol suchen wo definiert | `workspaceSymbol` | Statt Grep |
| Vor Refactor (egal welcher) | `findReferences` auf Hauptsymbol | Scope voll durchdenken |
| Vor TDD-Green (Code schreiben) | `findReferences` auf betroffene Symbole | Blueprint-Scope validieren |
| In /_I_orchestrate M1 | Immer | Single-Agent muss volle Sorgfalt |

---

## Kurzreferenz LSP-Operationen

```
LSP(operation: "findReferences",       symbol: "<Name>", in: "<abs-Pfad-zur-Definition>")
LSP(operation: "findImplementations",  symbol: "<Interface>", in: "<abs-Pfad>")
LSP(operation: "workspaceSymbol",      query: "<Teilname>")
LSP(operation: "documentSymbol",       file:  "<abs-Pfad>")
LSP(operation: "hover",                symbol: "<Name>", in: "<abs-Pfad>")
LSP(operation: "definition",           symbol: "<Name>", in: "<abs-Pfad>")
```

Tool-Schema vor Nutzung via `ToolSearch("select:LSP", 1)` laden, falls deferred.

---

## Verknuepfung mit TDD/I-Pipeline (PL-Item HOCH, geparkt)

Wenn die Refactoring der Agent-Commands passiert (siehe PL 2026-04-23), werden folgende Agents an /_lsp erinnert:

- `_TDD_red.md` — vor Test-Schreiben: LSP-Scope-Check
- `_TDD_green.md` — vor Code-Schreiben: LSP-Scope-Check
- `_TDD_refactorCode.md` — Pflicht
- `_TDD_refactorTests.md` — Pflicht
- `_I_orchestrate.md` M1-Block — Pflicht (Single-Agent = volle Schichten)

Bis Refactoring erfolgt: manuell darauf verweisen, wenn Agent ohne Scope-Check loslegt.

---

## Anti-Pattern: "Hin und Her"

**Falsch:**
```
Agent: Fix X in Datei A
→ Compile-Fehler in Datei B (vergessen)
→ Fix B
→ Test-Fehler in Datei C (vergessen)
→ Fix C
→ ...
```

**Richtig:**
```
Agent: LSP findReferences auf X → 5 Files gefunden (A,B,C,D,E)
→ Plan: alle 5 konsistent aendern
→ 1 Commit, alles GREEN
```

---

## Mini-Beispiel (Session 2026-04-23)

User wollte PUT-Return-Typ BO → ReadDto aendern. Erster Instinkt: "2 Zeilen fix". LSP-Check ergab: 3 Files (Controller + 2 Test-Files), Mapping existiert bereits. Scope klar **vor** Start, keine Rueckschlaege.

---

## Siehe auch

- `_parking-lot.md` — PL-Item "TDD Red/Green/Refactor + I_orchestrate M1: Scope/LSP/Meta/Pattern Enforcement" (2026-04-23)
- `.claude/meta/implementation/stage_3.md`
- `.claude/pileOfMud/TDD_RedGreenRefactor_ScopeDenken_Destilliert_2026-04-23.md`
