---
status: active
version: 1.0.0
created: 2026-04-13
op: ReleasePress
type: satellite
coldstart: true
---

# /_releasePress — Claude Code Release Notes Analyse & Briefing

```
╔══════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_releasePress                                                ║
╠══════════════════════════════════════════════════════════════════════════╣
║  LIEST:    GitHub Releases (anthropics/claude-code)                    ║
║  SCHREIBT: .claude/output/releasePress-{VERSION}.md                    ║
║  TOOLS:    WebFetch, WebSearch, Write                                  ║
║  COLDSTART: ja — keine Vorbedingungen                                  ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_releasePress                       → neueste Version
/_releasePress latest                → neueste Version
/_releasePress v2.1.104              → spezifische Version
/_releasePress v2.1.98 v2.1.104     → Range (von...bis)
/_releasePress last-3                → letzte 3 Releases
/_releasePress seit-letztem          → seit letzter /_releasePress Ausfuehrung
```

**$ARGUMENTS:** Version oder Range (siehe oben)

---

## Schritt 1: Release Notes holen

### 1a: Version bestimmen

| Eingabe | Aktion |
|---------|--------|
| leer / `latest` | Neueste Version von GitHub |
| `v2.1.104` | Genau diese Version |
| `v2.1.98 v2.1.104` | Alle Versionen von v2.1.98 bis v2.1.104 |
| `last-3` / `last-5` | Letzte N Releases |
| `seit-letztem` | Lies `.claude/output/releasePress-LATEST.md` → letzte Version → alles danach |

### 1b: GitHub API abrufen

```
WebFetch: https://api.github.com/repos/anthropics/claude-code/releases
```

Falls API-Limit: Fallback auf WebSearch mit `site:github.com anthropics/claude-code releases`.

Extrahiere pro Release:
- `tag_name` (Version)
- `published_at` (Datum)
- `body` (Release Notes Markdown)

---

## Schritt 2: Kategorisierung

Fuer JEDE Aenderung in den Release Notes, kategorisiere:

| Kategorie | Icon | Beschreibung |
|-----------|------|--------------|
| **FEATURE** | + | Neue Funktionalitaet |
| **FIX** | x | Bug-Fix |
| **SECURITY** | ! | Sicherheits-Fix |
| **PERF** | ^ | Performance-Verbesserung |
| **DX** | ~ | Developer Experience (UX, Fehlermeldungen, Hints) |
| **BREAKING** | !! | Breaking Change oder Entfernung |
| **INFRA** | # | Interne Aenderung (CI, Deps, Refactoring) |

Erkennungsregeln:
- "Added" → FEATURE
- "Fixed" → FIX
- "vulnerability" / "injection" / "bypass" → SECURITY
- "Improved performance" / "faster" / "speed" → PERF
- "Improved" (sonstiges) → DX
- "Removed" / "Changed default" → BREAKING
- "chore" / "Update CHANGELOG" → INFRA (SKIP in Output)

---

## Schritt 3: Relevanz-Bewertung fuer OmniCommand

Bewerte jede Aenderung auf Relevanz fuer unseren Workflow:

| Relevanz | Kriterium |
|----------|-----------|
| **HOCH** | Betrifft: Agent/Subagent, Hooks, Permissions, MCP, Skills, Plugins, Worktrees, /resume, SDK |
| **MITTEL** | Betrifft: Bash Tool, Edit/Write, Grep/Glob, UI/UX, Keybindings |
| **NIEDRIG** | Betrifft: Login/Auth, Cloud/Remote, Provider-spezifisch (Bedrock/Vertex), VSCode-only |
| **SKIP** | Changelog bumps, reine Versionsnummer-Commits |

---

## Schritt 4: Impact-Analyse

Fuer JEDE Aenderung mit Relevanz HOCH:

1. **Was aendert sich fuer uns?** (1-2 Saetze, konkret bezogen auf OmniCommand-Pipeline)
2. **Muessen wir etwas anpassen?** (Ja/Nein + was genau)
3. **Koennen wir etwas Neues nutzen?** (Ja/Nein + wie)

Beispiele:
- "Fixed subagents not inheriting MCP tools" → HOCH: Unsere BDF-Agents mit CleanCoder MCP profitieren
- "Added /team-onboarding" → MITTEL: Koennte fuer neue Teammitglieder nuetzlich sein
- "Fixed Bedrock SigV4" → NIEDRIG: Wir nutzen kein Bedrock

---

## Schritt 5: Briefing generieren

### 5a: Terminal-Output (immer)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  RELEASE PRESS — Claude Code {VERSION(EN)}                                  ║
║  Datum: {RELEASE_DATE}                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

=== FUER UNS RELEVANT (HOCH) ===

  + [FEATURE] /team-onboarding Command
    → Koennte fuer Onboarding neuer Kollegen nuetzlich sein

  x [FIX] Subagents erben jetzt MCP Tools von dynamisch injizierten Servern
    → BETRIFFT UNS: BDF/SDF Agents mit CleanCoder MCP
    → ACTION: Testen ob CleanCoder-Tools in Sub-Agents verfuegbar sind

  x [FIX] Sub-Agents in isolierten Worktrees: Read/Edit Access Fix
    → BETRIFFT UNS: /_I_codeAtomic mit Worktree-Isolation

  ! [SECURITY] Command Injection in POSIX which Fallback gefixt
    → Kein Action noetig, automatisch gefixt mit Update

=== MITTEL ===

  ~ [DX] Rate-Limit Retry zeigt jetzt welches Limit + wann Reset
    → Bessere Diagnostik bei langen BDF-Sessions

  ^ [PERF] Write Tool Diff 60% schneller bei grossen Dateien
    → Gut fuer unsere 500+ Zeilen Commands

=== STATISTIK ===

  FEATURES:  3
  FIXES:    24
  SECURITY:  1
  PERF:      2
  DX:        8
  BREAKING:  1
  GESAMT:   39
```

### 5b: Datei schreiben

Schreibe `.claude/output/releasePress-{VERSION}.md` mit:

```markdown
---
version: {VERSION}
date: {RELEASE_DATE}
analyzed: {TODAY}
relevant_high: {COUNT}
relevant_medium: {COUNT}
---

# Release Press: Claude Code {VERSION}

## Fuer uns relevant (HOCH)
[Details wie Terminal-Output, aber ausfuehrlicher]

## Mittel
[...]

## Niedrig (Kurzform)
[Einzeiler pro Item]

## Action Items
- [ ] {Konkrete Aktionen die wir ausfuehren sollten}

## Vollstaendige Release Notes
[Original-Text als Referenz]
```

---

## Schritt 6: LATEST-Marker aktualisieren

Schreibe/ueberschreibe `.claude/output/releasePress-LATEST.md`:

```markdown
---
last_version: {VERSION}
last_date: {TODAY}
---
Letzte analysierte Version: {VERSION} ({RELEASE_DATE})
```

Dies ermoeglicht `/_releasePress seit-letztem`.

---

## Fehler-Handling

| Fehler | Reaktion |
|--------|----------|
| GitHub API nicht erreichbar | WebSearch Fallback |
| Version nicht gefunden | "Version {X} nicht gefunden. Verfuegbar: {letzte 5}" |
| Keine Release Notes im Body | "Release {X} hat keine Details (nur Changelog bump)" → SKIP |
| Rate Limit | Warten + Retry (max 3x) |

---

## Hinweise

```
HINWEISE:
  - Release Notes kommen von https://github.com/anthropics/claude-code/releases
  - Relevanz-Bewertung ist OmniCommand-spezifisch (Agent, MCP, Hooks, Skills)
  - SECURITY-Items immer als HOCH eingestuft
  - BREAKING-Items immer als HOCH eingestuft
  - Action Items sind Vorschlaege — User entscheidet ob/wann
  - "seit-letztem" funktioniert nur wenn vorher /_releasePress gelaufen ist
```
