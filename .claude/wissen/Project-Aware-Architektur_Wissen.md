# Wissen: Project-Aware-Architektur

**Version:** 1.0
**Datum:** 2026-03-14
**Model-Kontext:** KickStartNeoVim_Model.md v2.0
**Methodik:** Feynman-Methode (easy — direkte Codebase-Analyse)
**Zielgruppe:** Entwickler die am KickStartNeoVim-System arbeiten

---

## 1. Einfuehrung — Warum dieses Wissen?

Zwei Projekte (DCSRE + CenCoCo) teilen sich eine einzige Neovim-Konfiguration.
Dieselbe Taste (`<leader>rbw`) startet auf DCSRE einen ASP.NET WebHost mit
custom URLs, auf CenCoCo einen `dotnet run --launch-profile https`. Dieselbe
Taste (`<leader>rDi`) fuehrt auf DCSRE ein PowerShell-Script `docker-up.ps1`
aus, auf CenCoCo ein simples `docker compose up -d`.

Das System erkennt beim Start automatisch in welchem Projekt man arbeitet und
konfiguriert alle Keybindings, Pfade und Befehle entsprechend.

---

## 2. Das Problem

```
Ein Entwickler arbeitet an DCSRE und CenCoCo.
Beide Projekte haben:
  - Unterschiedliche Backend-Pfade
  - Unterschiedliche Frontend-Technologien (Angular vs. Blazor)
  - Unterschiedliche Docker-Orchestrierung (docker-up.ps1 vs. docker compose)
  - Unterschiedliche Test-Infrastruktur (Cypress vs. Playwright)
  - Unterschiedliche Git-Base-Branches (origin/develop vs. origin/main)

Problem: Wie kann EINE Neovim-Config BEIDE Projekte bedienen,
ohne dass der Entwickler manuell umschalten muss?
```

---

## 3. Kern-Architektur: Die 4-Schichten-Kette

```
Schicht 1: Platform-Dispatcher     init.lua (~40 LOC)
                |
Schicht 2: Platform-Detection      lua/shared/platform.lua
                |
Schicht 3: Project-Detection       lua/shared/project.lua
                |
Schicht 4: Project-aware Code      lua/shared/keybindings/*.lua
                                   lua/shared/core.lua
                                   lua/shared/claude_sync.lua
```

### Lade-Reihenfolge (KRITISCH — darf NICHT geaendert werden)

```
platform.lua → project.detect() → core.lua → keybindings/*
```

Jede Schicht haengt von der vorherigen ab. `core.lua` braucht `vim.g.project_*`
fuer Plugin-Konfigurationen. Keybindings brauchen `vim.g.project_*` fuer
Pfade und Befehle.

---

## 4. Schicht 1: Platform-Dispatcher (init.lua)

**Datei:** `init.lua` (~40 Zeilen)

```lua
if vim.fn.has('win32') == 1 then
  require('init_windows')   -- lua/init_windows.lua
else
  require('init_linux')     -- lua/init_linux.lua
end
```

**Was passiert:** Neovim laeuft auf zwei Plattformen (Windows Native + WSL2/Linux).
Der Dispatcher waehlt den richtigen Entry-Point. Beide Entry-Points laden
identische Module in identischer Reihenfolge — der Unterschied ist minimal
(Windows hat `claude_sync`, Linux hat Bug B-001 Fix-Kommentar).

**Warum zwei Entry-Points statt einem?**
- `assert()` in jedem Entry-Point faengt falsche Plattform ab
- Saubere Trennung: Windows-spezifische Initialisierung (claude_sync) nur in init_windows.lua
- Zukunftssicher: plattformspezifische Unterschiede koennen wachsen

---

## 5. Schicht 2: Platform-Detection (platform.lua)

**Datei:** `lua/shared/platform.lua` (~50 LOC)

```lua
local M = {}
M.is_windows = vim.fn.has('win32') == 1
M.chrome_path = M.is_windows
  and 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  or '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
function M.open_url(url) ... end
function M.to_windows_path(path) ... end      -- '/' → '\\'
function M.wsl_to_windows(wsl_path) ... end   -- '/mnt/c/' → 'C:\\'
return M
```

**Was platform.lua liefert:**
| Export | Typ | Zweck |
|--------|------|-------|
| `is_windows` | boolean | Plattform-Flag fuer alle Branching-Entscheidungen |
| `chrome_path` | string | Chrome-Pfad fuer Markdown-Preview, URL-Oeffnen |
| `chrome_cmd` | string | Shell-escaped Chrome-Aufruf |
| `open_url(url)` | function | Plattform-agnostisches URL-Oeffnen |
| `to_windows_path(path)` | function | Forward → Backslash (fuer PowerShell) |
| `wsl_to_windows(path)` | function | WSL-Pfad → Windows-Pfad (/mnt/c/ → C:\\) |

**Feynman-Kern:** platform.lua ist das "Woerterbuch" zwischen den Welten.
Alle Module die plattform-abhaengig sind, fragen hier nach statt selbst
`vim.fn.has('win32')` zu pruefen.

---

## 6. Schicht 3: Project-Detection (project.lua)

**Datei:** `lua/shared/project.lua` (~93 LOC)

### 6.1 Der Erkennungs-Mechanismus

```lua
function M.detect()
  local cwd = vim.fn.getcwd()

  if cwd:match('Kluger') or cwd:match('CENCOCD')
     or cwd:match('CenCoCo') or cwd:match('cencoco') then
    vim.g.project_name = 'CENCOCD'
    -- ... setze CenCoCo-spezifische Pfade ...

  elseif cwd:match('DCSRE') then
    vim.g.project_name = 'DCSRE'
    -- ... setze DCSRE-spezifische Pfade ...

  else
    vim.g.project_name = 'UNKNOWN'
  end
end
```

**Feynman-Kern:** project.lua schaut sich an WO du Neovim geoeffnet hast.
Der Ordnername verraet das Projekt. Das ist wie ein Autoschluessel der erkennt
in welchem Auto er steckt — und dann Sitz, Spiegel und Radio automatisch
auf den richtigen Fahrer einstellt.

### 6.2 Die vim.g.project_* Globals

Nach `project.detect()` sind folgende Globals gesetzt:

| Global | DCSRE | CENCOCD |
|--------|-------|---------|
| `project_name` | `'DCSRE'` | `'CENCOCD'` |
| `project_backend` | `.../DCSRE/Sources/Backend` | `.../cencoco/src/Core/CenCoCo.Core.API` |
| `project_frontend` | `.../DCSRE/Sources/Frontend` | `.../cencoco/src/Core/CenCoCo.Core.Blazor` |
| `project_webhost` | `.../Backend/VDEK.DCSP.WebHost` | `.../Core/CenCoCo.Core.API` |
| `project_docker_root` | `.../DCSRE/Sources` | `.../cencoco/src` |
| `project_docker_root_windows` | `...\DCSRE\Sources` (Backslash) | `...\cencoco\src` (Backslash) |
| `project_git_base` | `'origin/develop'` | `'origin/main'` |
| `project_root_windows` | `...\DCSRE` (Backslash) | `...\cencoco` (Backslash) |
| `project_root_wsl` | `/mnt/c/.../DCSRE` | `/mnt/c/.../cencoco` |
| `project_launch_profile` | `'WebHost'` | `'https'` |
| `project_tfs_commit_url` | Azure DevOps URL Pattern | `nil` |
| `project_backend_windows` | `...\Sources\Backend` (nur DCSRE) | nicht gesetzt |

**Warum zwei Pfad-Varianten (forward/backslash)?**
- Forward-Slash-Pfade: Fuer WSL2/Linux `dotnet`/`npm` Befehle
- Backslash-Pfade (`_windows`): Fuer PowerShell-Befehle die Windows-Pfade brauchen
- DCSRE hat `find_dcsre_root()` das dynamisch den Root findet (Worktree-Support!)

### 6.3 DCSRE Root-Finding (Worktree-aware)

```lua
function M.find_dcsre_root(path)
  -- Strategie 1: Pattern-Match "DCSRE.../Sources"
  local root = path:match('(.*/DCSRE[^/]*)/Sources')
  if root then return root end

  -- Strategie 2: Aufwaerts suchen nach "Sources"-Ordner
  while check_path and #check_path > 3 do
    if vim.fn.isdirectory(check_path .. '/Sources') == 1 then
      return check_path
    end
    check_path = check_path:match('(.+)/[^/]+$')
  end
end
```

**Warum dynamisch?** DCSRE wird in Git-Worktrees gearbeitet. Der Pfad kann
`DCSRE_Azure/DCSRE-882_MetaDaten/Sources/Backend` sein — der Root ist
`DCSRE_Azure/DCSRE-882_MetaDaten`, nicht ein fester Pfad.

---

## 7. Schicht 4: Project-aware Keybindings

### 7.1 Die drei Branching-Patterns

**Pattern A: Komplett verschiedene Befehle**

```lua
-- docker.lua: <leader>rDi
if vim.g.project_name == 'DCSRE' then
  cmd = 'powershell.exe ... docker-up.ps1 -Profile dev-backend ...'
else
  cmd = 'powershell.exe ... docker compose up -d'
end
```

Gleiche Taste, voellig anderer Befehl. DCSRE braucht ein PowerShell-Script
mit Parametern, CenCoCo braucht nur `docker compose`.

**Pattern B: Gleiche Struktur, andere Pfade/Parameter**

```lua
-- backend.lua: <leader>rbw
if vim.g.project_name == 'CENCOCD' then
  cmd = '... dotnet run --launch-profile https'
else
  cmd = '... ASPNETCORE_URLS=https://localhost:5443 dotnet run --no-restore'
end
```

Beide starten dotnet, aber mit unterschiedlichen Parametern.

**Pattern C: Projekt-exklusiv**

```lua
-- tests.lua: <leader>rim
if vim.g.project_name ~= 'DCSRE' then
  vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
  return
end
```

Manche Befehle existieren nur fuer ein Projekt. Auf dem anderen
zeigen sie eine Warnung.

### 7.2 Die Keybinding-Module

| Modul | Datei | Keybindings | Project-aware? |
|-------|-------|-------------|----------------|
| Backend | `backend.lua` | rbw, rbs, rbb, rbt, rbu, rbp, rbP, rbR | Ja (rbw, rbu) |
| Frontend | `frontend.lua` | rfw, rfb, rft, rfi | Ja (rfw, rfb) |
| Docker | `docker.lua` | rDi, rDa, rDr, rDR, rDp | Ja (alle) |
| Tests | `tests.lua` | rT1-5, rTR, rTF, rTS, rim, rid, riR, riC | Ja (alle rT*, rid) |
| Git | `git.lua` | rc, rp, rP, gg, gf, gD, gM, gyd, gyf | Ja (gD/gM, gyf/gyd) |
| Clipboard | `clipboard.lua` | yp, yn, yd, gyf, gyd | Teilweise |

### 7.3 Terminal-ID Schema

Jeder Befehl oeffnet ein benanntes Terminal mit fester ID:

| ID-Range | Bereich | Beispiele |
|----------|---------|-----------|
| 1 | Default | Standard-Terminal |
| 10-11 | Generic Backend/Frontend | Freie Nutzung |
| 20-24 | Laufende Services | 20=WebHost, 21=Frontend, 22=Docker |
| 30-32 | E2E (DCSRE) | 30=Playwright, 31=Headed, 32=Cypress |
| 40-44 | Integration Tests (DEPRECATED ri*) | 40=Mock, 41=DB, 42=Picker, 43=Clean, 44=Build |
| 50-57 | Test-Stufen (rT*) | 50-54=rT1-5, 55=rTB, 56=rTF-rerun, 57=rTR |

---

## 8. Claude-Sync: Projekt-spezifische .claude Configs

**Datei:** `lua/shared/claude_sync.lua`

### 8.1 Das Problem

AgentsArchive hat projektspezifische `.claude`-Konfigurationen:
```
AgentsArchive/
├── .claude_DCSRE/       ← DCSRE-spezifische Commands, Patterns, Models
└── .claude_CenCoCo/     ← CenCoCo-spezifische Commands, Patterns, Models
```

Diese muessen in den jeweiligen Projekt-Root als `.claude/` erscheinen.

### 8.2 Die Routing-Tabelle

```lua
local ROUTING = {
  DCSRE   = ARCHIVE_BASE .. '\\.claude_DCSRE',
  CENCOCD = ARCHIVE_BASE .. '\\.claude_CenCoCo',
}
```

### 8.3 Der Sync-Mechanismus

```
Neovim Start
    |
    v
project.detect()  →  vim.g.project_name = 'DCSRE'
    |
    v (300ms defer)
claude_sync.sync()
    |
    v
ROUTING['DCSRE'] = AgentsArchive\.claude_DCSRE
    |
    v
robocopy AgentsArchive\.claude_DCSRE → DCSRE-Root\.claude
  /E    = Unterverzeichnisse
  /XO   = Aeltere nicht ueberschreiben
  /NJH /NJS /NFL /NDL = Stille Ausgabe
  /R:0  = Kein Retry
    |
    v
DCSRE\.claude/ hat jetzt alle Commands, Models, etc.
```

**Feynman-Kern:** Das ist wie ein Postbote der weiss welche Zeitung in
welchen Briefkasten gehoert. DCSRE bekommt die DCSRE-Zeitung, CenCoCo
bekommt die CenCoCo-Zeitung. Beide werden aus dem gleichen Verlag
(AgentsArchive) verschickt.

### 8.4 Manueller Sync

`<leader>rca` → `claude_sync.sync_with_notify()` — Sync mit Feedback-Notification.

---

## 9. Datenfluss-Diagramm (Komplett)

```
+--------------------+
| Neovim startet     |
+--------+-----------+
         |
         v
+--------+-----------+
| init.lua           |
| vim.fn.has('win32')|-----> init_windows.lua ODER init_linux.lua
+--------+-----------+
         |
         v
+--------+-----------+
| platform.lua       |
| is_windows = true  |
| chrome_path = ...  |
+--------+-----------+
         |
         v
+--------+-----------+
| project.detect()   |
| cwd:match('DCSRE') |-----> vim.g.project_name = 'DCSRE'
| OR cwd:match(...)  |       vim.g.project_backend = '...'
+--------+-----------+       vim.g.project_frontend = '...'
         |                   vim.g.project_git_base = 'origin/develop'
         |                   ... (12+ Globals)
         v
+--------+-----------+
| claude_sync.sync() |-----> robocopy AgentsArchive\.claude_DCSRE → .claude
| (300ms deferred)   |
+--------+-----------+
         |
         v
+--------+-----------+
| core.lua           |
| vim.opt, Plugins   |       Plugin-opts nutzen vim.g.project_*
| lazy.setup({...})  |       z.B. Obsidian Workspaces, DAP netcoredbg
+--------+-----------+
         |
         v
+--------+-----------+       +-----> backend.lua:  rbw → DCSRE/CenCoCo Befehl
| keybindings/*.lua  |       |-----> frontend.lua: rfw → Angular/Blazor Befehl
| if project == X    |-------+-----> docker.lua:   rDi → docker-up.ps1/compose
| then cmd_X         |       |-----> tests.lua:    rT* → Stufen 1-5 pro Projekt
| else cmd_Y         |       |-----> git.lua:      gD/gM → develop/main
+--------------------+       +-----> clipboard.lua
```

---

## 10. Haeufige Fehler & Missverstaendnisse

| Missverstaendnis | Realitaet |
|------------------|-----------|
| "project.detect() liest eine Config-Datei" | Nein — es matched nur den cwd-String gegen bekannte Muster |
| "Man muss beim Start das Projekt waehlen" | Nein — cwd-basierte Automatik, kein Prompt |
| "Die Pfade sind hardcoded pro Maschine" | Ja, aktuell schon — die Pfade sind auf Administrator's Maschine fixiert |
| "claude_sync kopiert bei jedem Start alles" | Nein — `/XO` ueberspringt bereits vorhandene neuere Dateien |
| "rT* und ri* teilen sich den TRX-Speicher" | Nein — rT* nutzt `rt-latest.trx`, ri* nutzt `it-latest.trx` |
| "project_backend_windows existiert fuer CenCoCo" | Nein — nur DCSRE hat dieses Global |

---

## 11. Wie man ein drittes Projekt hinzufuegt

1. **project.lua:** Neuen `elseif cwd:match('NeuesProjekt')` Block
2. **vim.g.project_\*:** Alle relevanten Pfad-Globals setzen
3. **claude_sync.lua:** `ROUTING['NEUESPROJEKT'] = ARCHIVE_BASE .. '\\.claude_NeuesProjekt'`
4. **keybindings/*.lua:** In jedem `if project_name == 'DCSRE'` Block einen `elseif` ergaenzen
5. **AgentsArchive:** `.claude_NeuesProjekt/` Ordner anlegen

---

## 12. Glossar

| Begriff | Erklaerung | Feynman-Version |
|---------|------------|-----------------|
| Platform-Dispatcher | init.lua: Waehlt Entry-Point basierend auf Betriebssystem | "Weiche im Gleis: Windows-Zug links, Linux-Zug rechts" |
| project.detect() | Funktion die cwd analysiert und vim.g.project_* setzt | "Autoschluessel der erkennt in welchem Auto er steckt" |
| vim.g.project_* | Globale Variablen mit Projekt-Pfaden und -Namen | "Namensschilder am Arbeitsplatz" |
| claude_sync | Kopiert .claude-Config vom Archiv ins Projekt | "Postbote der die richtige Zeitung in den richtigen Briefkasten wirft" |
| rT* | Test-Stufen-System (1-5 pro Projekt) | "Lichtkegelbreite: Laser → Flutlicht" |
| TRX | Test Results XML — .NET Testergebnis-Format | "Zeugnis nach der Pruefung" |

---

## 13. Quellen

| Typ | Datei | Inhalt |
|-----|-------|--------|
| Code | `init.lua` | Platform-Dispatcher (~40 LOC) |
| Code | `lua/shared/platform.lua` | Platform-Detection + Utilities (~50 LOC) |
| Code | `lua/shared/project.lua` | Project-Detection + vim.g.project_* (~93 LOC) |
| Code | `lua/shared/claude_sync.lua` | AgentsArchive → Projekt .claude Sync (~100 LOC) |
| Code | `lua/init_windows.lua` | Windows Entry-Point (platform→project→core→keybindings) |
| Code | `lua/init_linux.lua` | Linux Entry-Point (identische Lade-Reihenfolge) |
| Code | `lua/shared/keybindings/backend.lua` | rbw, rbs, rbb, rbt, rbu (project-aware) |
| Code | `lua/shared/keybindings/frontend.lua` | rfw, rfb, rft, rfi (project-aware) |
| Code | `lua/shared/keybindings/docker.lua` | rDi, rDa, rDr, rDR, rDp (project-aware) |
| Code | `lua/shared/keybindings/tests.lua` | rT1-5, rTR, rTF, rTS + DEPRECATED ri* |
| Model | `.claude/models/KickStartNeoVim_Model.md` | Architektur-Model v2.0 (W1-W8) |
