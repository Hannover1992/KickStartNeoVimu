---
wave: exploration
agent: E05
focus: refactoring-strategy
status: final
primaerquelle_gelesen: true
date: 2026-03-02
---

# E05: Refactoring-Strategie & Migrationsplan

## 1. Dependency-Graph (Lade-Reihenfolge)

### Kritische Erkenntnisse

Die `init.lua` hat eine **stark voneinander abhängige Struktur**. Der Lade-Graph sieht so aus:

```
┌─ Globals (mapleader, nerd_font) [Zeilen 87–111]
│  └─ Platform-Detection (is_windows) [Zeile 200]
│     └─ Projekt-Detection (vim.g.project_*) [Zeilen 229–275]
│        └─ Lazy.nvim Bootstrap [Zeilen 434–447]
│           └─ Plugin-Setup (lazy.setup) [Zeilen 449–3034]
│              ├─ OmniSharp-extended handlers [Zeile 2380]
│              ├─ Markdown-Preview (Chrome-Pfad abhängig) [Zeile 680]
│              ├─ Obsidian (Workspace-Pfade abhängig) [Zeile 745]
│              └─ DAP (netcoredbg.exe abhängig) [Zeile 1477]
│                 └─ Vim Options (vim.o.*) [Zeilen 277–354]
│                    └─ Basic Keymaps [Zeilen 356–432]
│                       └─ Custom Keybindings [Zeilen 3036–4539]
│                          ├─ Toggleterm Backend (WIN: powershell, LINUX: bash) [Zeile 3039+]
│                          ├─ Telescope E2E Picker (is_win ternary) [Zeile 2017]
│                          └─ Telescope Integration Picker (backend_root) [Zeile 2191]
```

### Lade-Reihenfolge (ABSOLUT)

1. **Globals** (`vim.g.mapleader`, `vim.g.have_nerd_font`, `vim.g.notifications_enabled`)
2. **Platform-Detection** (`is_windows = vim.fn.has('win32') == 1`)
3. **Projekt-Detection** (`vim.g.project_name`, `vim.g.project_backend`, Pfade)
4. **Vim-Options** (`vim.o.*`)
5. **Basic Keymaps** (Standard-Keybindings)
6. **Lazy.nvim Bootstrap** (Installation falls nötig)
7. **Plugin-Setup** (`lazy.setup()` mit allen Configs)
8. **Custom Keybindings** (projekt-spezifische Commands)

**Warum so streng?**
- `is_windows` wird von **25+ Stellen** referenziert
- `vim.g.project_*` wird von **allen toggleterm Commands** benötigt
- `lazy.setup()` benötigt **alles davor** initialisiert
- Keybindings brauchen **alle Plugins loaded**

---

## 2. Dispatcher-Strategie

### Option A: `vim.cmd('source')` (Empfehlung ✅)

```lua
-- init.lua (5 Zeilen!)
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

if vim.fn.has('win32') == 1 then
  vim.cmd.source(vim.fn.stdpath('config') .. '/init_windows.lua')
else
  vim.cmd.source(vim.fn.stdpath('config') .. '/init_linux.lua')
end
```

**Vorteile:**
- ✅ Einfachste Syntax (`source` ist Vim-native)
- ✅ Keine Pfad-Komplexität (verwendet `stdpath('config')`)
- ✅ Beide Files erhalten **vollen Scope** (wie jetzt)
- ✅ Keine Modul-Registrierungen nötig
- ✅ Schnellste Ausführung

**Nachteile:**
- ❌ Beide Files müssen je **alles vollständig** enthalten (kein Code-Sharing möglich)
- ❌ Shared Code wird **2x kopiert**

### Option B: `require()` mit shared Modulen

```lua
-- init.lua
if vim.fn.has('win32') == 1 then
  require('init_windows')
else
  require('init_linux')
end
```

```lua
-- init_windows.lua & init_linux.lua
local shared_core = require('shared.core')
local shared_project = require('shared.project')
-- ...
```

**Vorteile:**
- ✅ Code-Sharing möglich
- ✅ `shared/` Modules können unabhängig getestet werden
- ✅ Saubere Modul-Architektur

**Nachteile:**
- ❌ Komplexere Pfad-Logik (`lua/` Packages)
- ❌ `require()` braucht exakte Modul-Namen
- ❌ Lazy.nvim braucht speziale Config für User-Plugins

---

### EMPFEHLUNG: **Hybrid-Strategie**

```
init.lua
├── Globals (mapleader, nerd_font)
├── Platform Detection (is_windows)
├── Projekt-Detection (shared via require)
├── vim.cmd.source() → init_windows.lua ODER init_linux.lua
│  └── Lädt ALLES plattformspezifisch (inklusive shared Module)
└── (wird danach nicht mehr ausgeführt)
```

**Warum Hybrid?**
- ✅ init.lua bleibt **minimal & zuverlässig** (nur 8 Zeilen)
- ✅ init_windows.lua & init_linux.lua sind **vollständig unabhängig**
- ✅ Projekt-Detection kann via `require('shared.project')` geteilt werden
- ✅ Lazy.nvim & Plugins laufen im Scope der jeweiligen init_*.lua

**Konkreter Aufbau:**

```
init.lua (Minimal Dispatcher)
├── require('shared.project')  # Bestimmt is_windows, project_name
└── vim.cmd.source() → init_windows.lua oder init_linux.lua
    ├── Globals (vim.g.*)
    ├── Vim-Options
    ├── Basic Keymaps
    ├── Lazy.nvim Bootstrap
    ├── lazy.setup({})
    └── Custom Keybindings (toggleterm, telescope picker, etc.)
```

---

## 3. Step-by-Step Migrations-Plan

### Übersicht (8 Schritte)

| Schritt | Aufgabe | Zeilen | Komplexität | Risiko | Testbar? | Dauer | Branch |
|---------|---------|--------|-------------|--------|----------|-------|--------|
| 1 | Shared-Module-Struktur & Tests aufsetzen | 0 | Klein | Niedrig | Ja | 30min | feat/E01-test-infra |
| 2 | `shared/project.lua` extrahieren + Tests | ~50 | Klein | Niedrig | Ja | 1h | feat/E02-project |
| 3 | `shared/core.lua` (Vim-Options, Keymaps) | ~200 | Mittel | Mittel | Ja | 1.5h | feat/E03-core |
| 4 | `shared/keybindings/` (git, docker, tests) | ~400 | Mittel | Mittel | Ja | 2h | feat/E04-kb |
| 5 | `init_windows.lua` (Windows + toggleterm) | ~2200 | Groß | Hoch | Ja (manuell) | 1.5h | feat/E05-windows |
| 6 | `init_linux.lua` (WSL2 + toggleterm) | ~2200 | Groß | Hoch | Ja (manuell) | 1.5h | feat/E06-linux |
| 7 | Minimal `init.lua` (Dispatcher) | ~10 | Klein | Niedrig | Ja | 15min | feat/E07-dispatcher |
| 8 | Cleanup & Dokumentation | ~100 | Klein | Niedrig | Ja | 1h | feat/E08-cleanup |

**Gesamtdauer:** ~9 Stunden über mehrere Sessions

---

### Detaillierte Schritte

#### **Schritt 1: Test-Infrastruktur aufsetzen** (30 min)

**Ziel:** Lua-Testumgebung kann Tests ausführen (noch KEINE Inhalte)

**Aufgaben:**
- [ ] Erstelle `/lua/spec/project_spec.lua` (leere Test-Datei)
- [ ] Erstelle `/lua/shared/project.lua` (leeres Modul)
- [ ] Konfiguriere Test-Runner in `CLAUDE.md` (oder README)
- [ ] Test-Runner Befehl: `nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"`

**Kritische Tests (noch nicht geschrieben):**
```lua
describe('shared.project', function()
  it('detects CENCOCD project', function() end)
  it('detects DCSRE project', function() end)
  it('returns correct paths on Windows', function() end)
  it('returns correct paths on Linux', function() end)
end)
```

**Testbar nach Schritt?** ✅ Ja (Test-Suite lädt, Tests sind noch `pending`)

**Risiko:** Niedrig (nur Struktur, keine echte Logik)

**Manuelles Testen:**
```bash
cd /path/to/KickStartNeoVim
nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"
# Output: 0 passed, 0 failed (all pending)
```

---

#### **Schritt 2: `shared/project.lua` + Tests** (1h)

**Ziel:** Projekt-Detection zentral, mit Unit-Tests

**Aufgaben:**
- [ ] Extrahiere Lines 202–275 → `lua/shared/project.lua`
  - Funktion `find_dcsre_root()` (Zeile 202–227)
  - Projekt-Detection-Logik (Zeile 229–275)
- [ ] Schreibe Unit-Tests in `/lua/spec/project_spec.lua`
  - Test: `detects CENCOCD project when cwd contains /Kluger/cencoco`
  - Test: `detects DCSRE project when cwd contains /Code2/DCSRE`
  - Test: `sets vim.g.project_name correctly`
  - Test: `builds correct backend path on Windows`
  - Test: `builds correct backend path on Linux`
- [ ] Module exportiert: `return { initialize = function() ... end }`
- [ ] `init.lua` (alt) weiterhin funktioniert (keine breaking changes)

**Kritische Modul-Schnittstelle:**
```lua
-- lua/shared/project.lua
local M = {}

function M.initialize()
  -- Setzt is_windows, vim.g.project_name, vim.g.project_*
  -- Gibt auch is_windows zurück für Dispatcher-Logik
end

return M
```

**Testbar nach Schritt?** ✅ Ja
- Test-Suite lädt `shared/project.lua`
- Tests validieren Projekt-Detection-Logik
- `init.lua` lädt weiterhin normal (fallback möglich)

**Manuelles Testen:**
```vim
" In Neovim (normal init.lua)
:echo vim.g.project_name  " Sollte CENCOCD oder DCSRE sein
:LspInfo                  " Sollte noch funktionieren
<leader>rbw               " Sollte noch funktionieren
```

**Risiko:** Niedrig (project.lua ist isoliert, Tests können break-fast erkennen)

---

#### **Schritt 3: `shared/core.lua` (Vim-Options + Basic Keymaps)** (1.5h)

**Ziel:** Gemeinsame Vim-Einstellungen & Standard-Keybindings zentral

**Aufgaben:**
- [ ] Extrahiere Lines 277–354 (Vim-Options) → `lua/shared/core.lua`
- [ ] Extrahiere Lines 356–432 (Basic Keymaps) → `lua/shared/core.lua`
- [ ] Schreibe Sanity-Tests:
  - Test: `vim.o.number ist true`
  - Test: `vim.o.tabstop ist 2`
  - Test: `keymaps sind registriert`
- [ ] `init.lua` (alt) weiterhin funktioniert

**Modul-Schnittstelle:**
```lua
-- lua/shared/core.lua
local M = {}

function M.setup_vim_options()
  vim.o.number = true
  vim.o.relativenumber = true
  -- ... alle 277–354 Zeilen
end

function M.setup_keymaps()
  -- ... alle 356–432 Zeilen
  local map = vim.keymap.set
  map('n', 'j', 'gj', { noremap = true })
  -- ...
end

return M
```

**Testbar nach Schritt?** ✅ Ja
- Tests validieren `vim.o.*` Optionen
- Manuell: Standard-Keymaps (`j`, `k`, etc.) testen

**Manuelles Testen:**
```vim
" In Neovim
:set number?       " Sollte 'number' sein
:set tabstop?      " Sollte 2 sein
j                  " Sollte "gj" mappen (ein Schritt)
```

**Risiko:** Mittel (wenn vim.o.* Werte falsch, brechen viele Dinge)
- **Mitigation:** Tests für critical options (number, tabstop, expandtab)

---

#### **Schritt 4: `shared/keybindings/*` (git, docker, tests)** (2h)

**Ziel:** Projekt-unabhängige Keybindings modular

**Aufgaben:**
- [ ] Extrahiere Git-Keybindings (ab Zeile 3173) → `lua/shared/keybindings/git.lua`
  - `<leader>gg`, `<leader>gf`, `<leader>gD`, etc.
  - Unabhängig von `vim.g.project_*`
- [ ] Extrahiere Docker-Keybindings (ab Zeile 3260) → `lua/shared/keybindings/docker.lua`
  - `<leader>rDi`, `<leader>rDa`, `<leader>rDI`
  - Benutzt `vim.g.project_backend` (abhängig von project.lua)
- [ ] Extrahiere Test-Keybindings (ab Zeile 2017) → `lua/shared/keybindings/tests.lua`
  - E2E Picker, Integration Test Picker
  - Benutzt `is_windows`, `vim.g.project_backend`
- [ ] Schreibe Dummy-Tests (kein functional test nötig, nur load-test)

**Struktur:**
```
lua/shared/keybindings/
├── git.lua         # Neogit, Diffview, TFS
├── docker.lua      # Docker Compose, Profile management
└── tests.lua       # E2E, Integration, Unit test pickers
```

**Modul-Schnittstelle:**
```lua
-- lua/shared/keybindings/git.lua
local M = {}

function M.setup()
  local map = vim.keymap.set
  map('n', '<leader>gg', '<cmd>Neogit<cr>', { desc = '[G]it [G]ui' })
  -- ...
end

return M
```

**Testbar nach Schritt?** ✅ Ja (load-only)
- Teste: `require('shared.keybindings.git')` lädt ohne Fehler
- Manuell: `<leader>gg` öffnet Neogit

**Risiko:** Niedrig (reine Keybinding-Definitionen)

---

#### **Schritt 5: `init_windows.lua` (Windows-native)** (1.5h)

**Ziel:** Vollständige Windows-Neovim Config, alle toggleterm & Obsidian Pfade Windows-Stil

**Aufgaben:**
- [ ] Erstelle `init_windows.lua` als **Kopie** von `init.lua` (aktuell)
- [ ] **ENTFERNE** alle WSL-Spezifika:
  - Zeile 131–163: Behalte nur Windows-Branch
  - Zeile 235–243: Behalte nur Windows-Paths
  - Zeile 680–694: Behalte nur Windows Chrome-Pfad
  - Zeile 745–754: Behalte nur Windows Workspace-Pfade
  - Zeile 858–863: Behalte nur Windows Browser-Start
  - Zeile 934: Behalte nur Windows Graph-View
  - Zeile 2017–2110: E2E Picker: nur powershell.exe Branch
  - Zeile 2191–2303: Integration Picker: nur powershell.exe Branch
  - Zeile 3039–3051: Watch Backend: Keep as-is (powershell)
  - Zeile 3067–3092: Backend WebHost: nur Windows-Branch
  - Zeile 3095–3109: Backend Setup: Keep as-is (powershell)
  - Zeile 3112–3122: Backend Build: Keep as-is (powershell)
- [ ] Refaktor toggleterm Commands aus Zeile 3036+ für Windows-Pfade:
  - `cwd` Parameter: `C:\Users\...` (backslash)
  - Project-Paths: `vim.g.project_backend` (bereits gesetzt)
- [ ] **Integriere** `shared/project.lua`:
  ```lua
  require('shared.project').initialize()
  ```
- [ ] **Integriere** `shared/core.lua`:
  ```lua
  require('shared.core').setup_vim_options()
  require('shared.core').setup_keymaps()
  ```
- [ ] **Integriere** `shared/keybindings/*`:
  ```lua
  require('shared.keybindings.git').setup()
  require('shared.keybindings.docker').setup()
  require('shared.keybindings.tests').setup()
  ```

**Zeilen-Verteilung init_windows.lua (~2200 Zeilen):**
- Lines 1–280: Globals, Platform-Detection, Projekt-Detection, Vim-Options
- Lines 281–432: Basic Keymaps (oder aus shared.core)
- Lines 433–447: Lazy.nvim Bootstrap
- Lines 448–3034: lazy.setup() (alle Plugins, nur Windows-Branches)
- Lines 3035–4539: Custom Keybindings (oder teils aus shared/keybindings)

**Testbar nach Schritt?** ✅ Ja (manuell auf Windows)
- [ ] Starte Neovim nativ auf Windows
- [ ] `<leader>rbw` startet WebHost (PowerShell-Command)
- [ ] `<leader>rDi` startet Docker-Compose (PowerShell)
- [ ] `:LspInfo` zeigt OmniSharp attached
- [ ] `<leader>gg` öffnet Neogit
- [ ] `:Obsidian` Commands funktionieren

**Manuelles Testen (Windows):**
```powershell
# In Windows PowerShell
cd C:\Users\Administrator\AppData\Local\nvim
copy C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init_windows.lua .\init.lua
nvim C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init.lua
# Teste alle Keybindings
```

**Risiko:** Hoch (großes File, viele Pfad-Änderungen)
- **Mitigation:** Nur Windows-Branch copy-paste, Rest entfernen; Checklist vor Commit

---

#### **Schritt 6: `init_linux.lua` (WSL2-spezifisch)** (1.5h)

**Ziel:** WSL2-Neovim Config, alle Pfade `/mnt/c/`, bash commands

**Aufgaben:**
- [ ] Erstelle `init_linux.lua` als **Kopie** von `init.lua` (aktuell)
- [ ] **ENTFERNE** alle Windows-Spezifika
  - Behalte nur WSL-Branches in allen Conditionals
  - `/mnt/c/` Pfade statt `C:/`
- [ ] **Refaktor** toggleterm Commands für bash:
  - `cwd` Parameter: `/mnt/c/Users/...`
  - Bash Commands statt PowerShell
- [ ] **Integriere** shared Module (wie in Schritt 5)
- [ ] **Wichtig:** Zeile 3039–3051 (Watch Backend) braucht **neuen Linux-Branch**
  ```lua
  -- NEU für Linux:
  elseif vim.g.project_name == 'DCSRE' then
    cmd = 'cd ' .. vim.g.project_backend .. ' && dotnet watch run ...'
  end
  ```

**Zeilen-Verteilung init_linux.lua (~2200 Zeilen):** Identisch zu init_windows.lua

**Testbar nach Schritt?** ✅ Ja (manuell in WSL2)
- [ ] Starte Neovim in WSL2
- [ ] `<leader>rbw` startet WebHost (bash-Command)
- [ ] `<leader>rDi` startet Docker (bash: `docker compose up`)
- [ ] `:LspInfo` zeigt OmniSharp attached (vom Windows-Projekt!)
- [ ] `<leader>gg` öffnet Neogit
- [ ] `:Obsidian` nutzt `/mnt/c/` Pfade

**Manuelles Testen (WSL2):**
```bash
# In WSL2
cp /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init_linux.lua ~/.config/nvim/init.lua
nvim /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua
# Teste alle Keybindings
```

**Risiko:** Hoch (wie Schritt 5, aber für Linux)

---

#### **Schritt 7: Minimal `init.lua` (Dispatcher)** (15 min)

**Ziel:** `init.lua` wird Dispatcher, lädt je nach Plattform richtig init

**Aufgaben:**
- [ ] Ersetze `init.lua` mit ~10 Zeilen:

```lua
-- ~/.config/nvim/init.lua - Dispatcher for Windows/Linux
-- Minimal kickstart: Sets globals, loads platform-specific config

-- Global settings (independent of platform)
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '
vim.g.have_nerd_font = false
vim.g.notifications_enabled = true

-- Load platform-specific configuration
if vim.fn.has('win32') == 1 then
  vim.cmd.source(vim.fn.stdpath('config') .. '/init_windows.lua')
else
  vim.cmd.source(vim.fn.stdpath('config') .. '/init_linux.lua')
end
```

**Testbar nach Schritt?** ✅ Ja (sofort)
- [ ] Starte Neovim auf Windows → lädt init_windows.lua ✅
- [ ] Starte Neovim auf WSL2 → lädt init_linux.lua ✅
- [ ] Beide Versionen starten fehlerfrei

**Risiko:** Niedrig (nur Dispatcher, beide init_*.lua existieren bereits)

---

#### **Schritt 8: Cleanup & Dokumentation** (1h)

**Aufgaben:**
- [ ] Lösche alt `init.lua` Backup (oder verschiebe zu `old_settings/`)
- [ ] Aktualisiere `CLAUDE.md`:
  ```markdown
  ### 2. IMMER POWERSHELL FÜR FILE OPERATIONS

  **Config-Dateien kopieren:**
  ```powershell
  # Windows Neovim (mit neuem Dispatcher):
  Copy-Item -Force 'C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init_windows.lua' 'C:\Users\Administrator\AppData\Local\nvim\init_windows.lua'
  Copy-Item -Force 'C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init_linux.lua' 'C:\Users\Administrator\AppData\Local\nvim\init_linux.lua'
  Copy-Item -Force 'C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init.lua' 'C:\Users\Administrator\AppData\Local\nvim\init.lua'

  # WSL2 Neovim:
  wsl.exe bash -c "cp /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init_windows.lua ~/.config/nvim/init_windows.lua && cp /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init_linux.lua ~/.config/nvim/init_linux.lua && cp /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua ~/.config/nvim/init.lua"
  ```
  ```
- [ ] Schreibe README für neue Struktur:
  ```markdown
  ## Dateistruktur nach Refactoring

  - `init.lua` - Dispatcher (Platform-Detection, lädt init_windows oder init_linux)
  - `init_windows.lua` - Windows-native Neovim config
  - `init_linux.lua` - WSL2/Linux Neovim config
  - `lua/shared/` - Gemeinsame Module
    - `project.lua` - Projekt-Detection
    - `core.lua` - Vim-Options, Basic Keymaps
    - `keybindings/git.lua` - Git-Keybindings
    - `keybindings/docker.lua` - Docker-Keybindings
    - `keybindings/tests.lua` - Test-Picker
  - `lua/spec/` - Unit-Tests (plenary busted)
  ```
- [ ] Cleanup alte Dateien:
  - `old_settings/init.lua.bak` (alte monolithische Version)
- [ ] Final Verification Checklist:
  - [ ] Windows Neovim startet mit `init_windows.lua` ✅
  - [ ] WSL2 Neovim startet mit `init_linux.lua` ✅
  - [ ] Alle Keybindings funktionieren auf Windows ✅
  - [ ] Alle Keybindings funktionieren auf WSL2 ✅
  - [ ] `lua/spec/` Tests laufen: `PlenaryBustedDirectory` ✅
  - [ ] Keine Code-Duplikate in shared/ ✅
  - [ ] Keine Regression vs. ursprüngliche init.lua ✅

**Risiko:** Niedrig (nur Dokumentation & Cleanup)

---

## 4. Rollback-Strategie

### Git-Strategie

**Alle Schritte laufen auf Feature-Branches:**

```
main (stabil, original init.lua)
├── feat/E01-test-infra
│   └── Adds lua/spec/, lua/shared/project.lua (skeleton)
├── feat/E02-project (basiert auf E01)
│   └── Implements shared/project.lua mit Unit-Tests
├── feat/E03-core (basiert auf E02)
│   └── Adds shared/core.lua
├── feat/E04-kb (basiert auf E03)
│   └── Adds lua/shared/keybindings/*
├── feat/E05-windows (basiert auf E04)
│   └── Adds init_windows.lua
├── feat/E06-linux (basiert auf E05)
│   └── Adds init_linux.lua
├── feat/E07-dispatcher (basiert auf E06)
│   └── Replaces init.lua mit minimal Dispatcher
└── feat/E08-cleanup (basiert auf E07)
    └── Documentation, Cleanup, Tests passing
```

**Jede Feature-Branch:**
- Ist **linear abhängig** von der vorherigen (E02 braucht E01, etc.)
- Hat **einen klaren Scope** (in Schritt-Tabelle definiert)
- Hat **nachweisbare Tests/Verifikation**

### Rollback im Fehlerfall

**Szenario:** E05 (init_windows.lua) bricht Windows-Neovim

```bash
# Schneller Rollback zu letztem stabilen Punkt (z.B. E04)
git checkout feat/E04-kb
# Oder zu main:
git checkout main
```

**Im `develop` Branch arbeiten:**
```bash
# Feature-Branches erstellen & mergen
git checkout -b feat/E05-windows develop

# Nach Verifikation:
git commit -m "feat: init_windows.lua extracted"
git push origin feat/E05-windows

# PR auf develop (nicht main!), dann:
git checkout develop
git merge feat/E05-windows
```

**Nur nach allen 8 Schritten:**
```bash
git checkout main
git merge develop  # oder PR auf main
```

### Manuelles Rollback (Neovim selbst kaputt)

```bash
# Stelle alte init.lua wieder her
git checkout main -- init.lua

# oder manuell:
rm ~/.config/nvim/init.lua
cp /path/to/backup/init.lua ~/.config/nvim/init.lua
```

---

## 5. Kritische Risiken und Mitigationen

| Risiko | Ursache | Impact | Wahrscheinlichkeit | Mitigation |
|--------|--------|--------|-------------------|------------|
| **Lazy-loading Reihenfolge bricht** | `is_windows` wird zu spät evaluiert (nach lazy.setup) | Plugins haben `is_windows` nil | Mittel | `is_windows` wird in Schritt 2 (shared/project.lua) **VOR lazy.setup** evaluiert; Unit-Tests prüfen `is_windows` wert |
| **toggleterm Pfade falsch** | Windows vs. Linux `cwd` unterschiedlich | Backend startet im falschen Pfad | Hoch | Jede toggleterm Config wird **manuell getestet** nach Schritt 5 (Windows) & 6 (Linux); Checklist in Task.md |
| **Obsidian Workspace-Pfade broken** | Windows `C:/` vs Linux `/mnt/c/` Mixed | `:Obsidian` Commands funktionieren nicht | Mittel | Obsidian-Block bleibt **in init_*.lua Spezifika**; wird mit `:Obsidian` Command manuell geprüft |
| **DAP netcoredbg `.exe` suffix falsch** | Linux braucht NO `.exe`, Windows braucht `.exe` | DAP bricht beim Debugging | Mittel | netcoredbg-Logik bleibt in init_*.lua; wird in `<leader>dib` Keybinding geprüft |
| **Markdown-Preview Chrome-Pfad falsch** | Windows `C:\Program Files` vs Linux `/mnt/c/Program Files` | Preview öffnet sich nicht | Niedrig | Chrome-Pfade sind **bereits korrekt** in Zeile 680; Tests testen `<leader>mp` |
| **Modul-Require Pfade falsch** | `require()` sucht in falschen Paths | Module laden nicht | Niedrig | Lua `package.path` wird von Neovim gesetzt; Tests in Schritt 1 validieren `require('shared.project')` |
| **Projekt-Detection lädt zu spät** | `shared/project.lua` wird nach lazy.setup geladen | `vim.g.project_backend` ist nil in Plugins | Hoch | `shared/project.lua` wird **VOR lazy.setup** geladen (in init_*.lua) |
| **Tests laufen nicht** | plenary/busted nicht installed | Tests crashen | Niedrig | plenary ist bereits Plugin (Zeile 2328); Tests benötigen nur `:PlenaryBustedDirectory` |

### Konkrete Mitigations-Checklisten

#### Für Schritt 5 (init_windows.lua):

```
Windows Verification Checklist:
[ ] Neovim startet ohne Fehler
    nvim C:/path/to/file.lua

[ ] Globals gesetzt:
    :echo vim.g.mapleader          " Sollte ' ' sein
    :echo vim.g.project_name       " Sollte CENCOCD oder DCSRE sein

[ ] Vim-Options gesetzt:
    :set number?                   " Sollte 'number' sein
    :set tabstop?                  " Sollte 2 sein

[ ] Keybindings funktionieren:
    <leader>gg                     " Öffnet Neogit
    <leader>rbw                    " Startet Backend WebHost
    <leader>rDi                    " Startet Docker UP

[ ] Backend startet im richtigen Pfad:
    <leader>rbw
    " Terminal sollte PowerShell-Befehl zeigen
    " Backend-Service sollte starten

[ ] LSP funktioniert:
    :LspInfo                       " Zeigt OmniSharp attached
    " Öffne .cs Datei, teste <leader>gd (Go to Definition)
```

#### Für Schritt 6 (init_linux.lua):

```
Linux/WSL2 Verification Checklist:
[ ] Neovim startet ohne Fehler
    nvim /mnt/c/path/to/file.lua

[ ] Globals gesetzt:
    :echo vim.g.project_name       " Sollte CENCOCD oder DCSRE sein

[ ] Keybindings funktionieren:
    <leader>gg                     " Öffnet Neogit
    <leader>rbw                    " Startet Backend WebHost (bash)

[ ] Backend startet:
    <leader>rbw
    " Terminal sollte bash-Befehl zeigen
    " Backend-Service sollte starten

[ ] Docker funktioniert:
    <leader>rDi                    " Startet docker compose up
    " Docker-Container sollten starten

[ ] Obsidian Workspace geladen:
    :Obsidian
    " Sollte WSL Paths nutzen (/mnt/c/Users/...)
```

---

## 6. Was zuerst auf Linux testen

**Priorisiert nach Risiko:**

1. **Projekt-Detection** (Schritt 2)
   - DCSRE Auto-Detection funktioniert?
   - CENCOCD Auto-Detection funktioniert?
   - Backend-Pfade stimmen?

2. **toggleterm Backend Commands** (Schritt 6)
   - `<leader>rbw` startet WebHost im WSL2 Terminal?
   - `<leader>rbs` (Migrations) funktioniert?
   - Pfade sind korrekt (no Windows backslash)?

3. **Docker Commands** (Schritt 6)
   - `<leader>rDi` startet `docker compose up`?
   - `<leader>rDI` startet `docker compose down`?
   - (nur relevant wenn Docker auf WSL2 läuft)

4. **Obsidian Workspace** (Schritt 6)
   - `:Obsidian` zeigt WSL Workspace?
   - `/mnt/c/` Pfade sind richtig?

5. **E2E Telescope Picker** (Schritt 4/6)
   - E2E Picker startet `bash` Command (nicht PowerShell)?
   - Cypress Config-Pfad stimmt?

6. **OmniSharp + LSP** (alle Schritte)
   - `:LspInfo` zeigt OmniSharp attached?
   - `gd` (Go to Definition) funktioniert?
   - StyleCop warnings erscheinen?

---

## 7. Windows COPY-Befehl (CLAUDE.md Update)

**Nach Refactoring:**

```powershell
# Copy ALLE init Files zu Neovim Config

# Für Windows Neovim:
Copy-Item -Force 'C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init.lua' 'C:\Users\Administrator\AppData\Local\nvim\init.lua'
Copy-Item -Force 'C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init_windows.lua' 'C:\Users\Administrator\AppData\Local\nvim\init_windows.lua'
Copy-Item -Force 'C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init_linux.lua' 'C:\Users\Administrator\AppData\Local\nvim\init_linux.lua'

# Für WSL2 Neovim:
wsl.exe bash -c "cp /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua ~/.config/nvim/init.lua && cp /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init_windows.lua ~/.config/nvim/init_windows.lua && cp /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init_linux.lua ~/.config/nvim/init_linux.lua"
```

**Warum 3 Dateien?**
- `init.lua` = Dispatcher (lädt init_windows oder init_linux)
- `init_windows.lua` = Windows Neovim Config
- `init_linux.lua` = WSL2 Neovim Config

---

## Zusammenfassung

### Empfohlener Aufbau (nach allen 8 Schritten)

```
~/.config/nvim/
├── init.lua                    # ✨ Minimal Dispatcher (10 Zeilen)
├── init_windows.lua            # Windows-native config (~2200 Zeilen)
├── init_linux.lua              # WSL2 config (~2200 Zeilen)
└── lua/
    ├── spec/
    │   └── project_spec.lua    # Unit-Tests
    └── shared/
        ├── project.lua         # Projekt-Detection (tested)
        ├── core.lua            # Vim-Options, Basic Keymaps
        └── keybindings/
            ├── git.lua         # Git Keybindings
            ├── docker.lua      # Docker Keybindings
            └── tests.lua       # Test-Pickers
```

### Komplexität pro Schritt

- **Schritte 1–2:** Klein (Test-Infra, project.lua) → **Niedrig Risiko**
- **Schritte 3–4:** Mittel (shared modules) → **Mittel Risiko**
- **Schritte 5–6:** Groß (init_*.lua) → **Hoch Risiko**
- **Schritte 7–8:** Klein (Dispatcher, Cleanup) → **Niedrig Risiko**

### Rollback jederzeit möglich

Jeder Schritt hat unabhängige Feature-Branch → schneller Rollback zu main möglich.

### Tests validieren Kritisches

- `shared/project.lua` Unit-Tests: Projekt-Detection
- `lua/spec/` Integration: Lazy.nvim + Plugins laden
- Manuell: toggleterm Commands, Obsidian, DAP, Keybindings

---

**Status:** ✅ Strategie-Dokument FINAL
**Empfehlung:** Starte mit Schritt 1 (Test-Infra) in kommender Session
**Nächster Agent:** E06+ (Implementation nach Approval)
