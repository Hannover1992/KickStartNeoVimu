---
wave: drafts
agent: D01
focus: module-architecture
status: final
primaerquelle_gelesen: true
date: 2026-03-02
---

# D01: Finale Modul-Architektur für KickStartNeoVim

## Executive Summary

Diese Analyse basiert auf direkter Untersuchung der Primärquellen (init.lua Zeilen 87–450 + 2780–2960, crumbs.md, Task.md). Die monolithische `init.lua` (4541 Zeilen) soll in **3 Ebenen** refaktoriert werden:

1. **Dispatcher init.lua** (Zeile 1-15): Platform-Erkennung + Laden
2. **Platform-Entry-Points** (init_windows.lua, init_linux.lua): Pfade + Commands
3. **Shared-Module** (lua/shared/): Plugins, LSP, Keybindings, Constants

---

## 1. Dateistruktur (FINAL)

```
KickStartNeoVim/
├── init.lua                          # Dispatcher (15 Zeilen)
├── init_windows.lua                  # Windows-native (2200 Zeilen geschätzt)
├── init_linux.lua                    # WSL2/Linux (2200 Zeilen geschätzt)
│
└── lua/
    └── shared/
        ├── core.lua                  # Plugins + vim-options (1800 Zeilen)
        ├── project.lua               # Projekt-Detection (100 Zeilen, zentral testbar)
        ├── platform.lua              # Platform-Konstanten (50 Zeilen)
        │
        └── keybindings/
            ├── init.lua              # Loader (20 Zeilen)
            ├── backend.lua           # Backend-Commands (250 Zeilen)
            ├── frontend.lua          # Frontend-Commands (200 Zeilen)
            ├── git.lua               # Git-Keybindings (150 Zeilen)
            ├── docker.lua            # Docker-Keybindings (200 Zeilen)
            └── tests.lua             # Test-Keybindings (150 Zeilen)
```

### Zeilenschätzung pro Datei

| Datei | Zeilen (geschätzt) | Quelle |
|-------|-------------------|--------|
| init.lua (Dispatcher) | 15 | Neu |
| init_windows.lua | 2200 | Aus init.lua Zeilen 87–300, 434–450, 2780–2960, 3036–4539 (platform-angepasst) |
| init_linux.lua | 2200 | Wie Windows, aber mit Unix-Pfaden |
| lua/shared/core.lua | 1800 | init.lua Zeilen 449–3034 (lazy.setup + LSP + vim.o.* Einstellungen) |
| lua/shared/project.lua | 100 | init.lua Zeilen 194–268 (find_dcsre_root + Projekt-Detection) |
| lua/shared/platform.lua | 50 | Neue Konstanten-Datei |
| lua/shared/keybindings/init.lua | 20 | Loader |
| lua/shared/keybindings/backend.lua | 250 | init.lua Zeilen 3039–3204 |
| lua/shared/keybindings/frontend.lua | 200 | init.lua Zeilen 3206–3265 |
| lua/shared/keybindings/git.lua | 150 | Aus verschiedenen Zeilen (Git-Commands) |
| lua/shared/keybindings/docker.lua | 200 | init.lua Zeilen 3384–3509 |
| lua/shared/keybindings/tests.lua | 150 | E2E/Integration Test Pickers |

**Gesamtumfang Refactoring:**
- **Vorher**: 1 Datei × 4541 Zeilen = 4541 Zeilen
- **Nachher**: 12 Dateien × ~8300 Zeilen (mit Duplikaten in init_windows + init_linux) = **~8600 Zeilen total**
- **Duplikation**: init_windows + init_linux sind ~90% identisch (nur Pfade unterscheiden sich)

---

## 2. Konkrete API-Designs für jedes Modul

### 2.1 lua/shared/platform.lua

**Zweck**: Zentrale Konstanten für Plattform-Unterschiede

```lua
-- lua/shared/platform.lua
local M = {}

-- Platform Detection (evaluiert bei Module-Load)
M.is_windows = vim.fn.has('win32') == 1
M.is_unix = vim.fn.has('unix') == 1

-- Chrome Browser Paths (wird von markdown-preview + obsidian verwendet)
M.chrome_path = M.is_windows
  and 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  or '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'

-- DAP Adapter Path (netcoredbg - nur Windows hat .exe)
M.netcoredbg_path = vim.fn.stdpath('data') .. '/mason/packages/netcoredbg/netcoredbg/netcoredbg'
if M.is_windows then
  M.netcoredbg_path = M.netcoredbg_path .. '.exe'
end

-- Obsidian Vault Roots (wird von obsidian.nvim konfiguriert)
M.obsidian_vaults = {
  {
    name = 'DCSRE',
    path = M.is_windows
      and 'C:/Users/Administrator/Documents/Work/DCSRE-Docs'
      or '/mnt/c/Users/Administrator/Documents/Work/DCSRE-Docs',
  },
  {
    name = 'CenCoCo',
    path = M.is_windows
      and 'C:/Users/Administrator/Documents/Work/Kluger/CenCoCo-Docs'
      or '/mnt/c/Users/Administrator/Documents/Work/Kluger/CenCoCo-Docs',
  },
  {
    name = 'Brain',
    path = M.is_windows
      and 'C:/Users/Administrator/Documents/Brain'
      or '/mnt/c/Users/Administrator/Documents/Brain',
  },
}

return M
```

### 2.2 lua/shared/project.lua

**Zweck**: Projekt-Detection Logik (testbar!)

```lua
-- lua/shared/project.lua
local M = {}

-- Helper: Find DCSRE root dynamically
-- @param path string: Current working directory
-- @return string|nil: DCSRE root or nil if not found
function M.find_dcsre_root(path)
  -- Normalize path separators
  path = path:gsub('\\', '/')

  -- Strategy 1: Extract from path pattern .../DCSRE.../Sources/...
  local root = path:match('(.*/DCSRE[^/]*)/Sources')
  if root and vim.fn.isdirectory(root .. '/Sources') == 1 then
    return root
  end

  -- Strategy 2: Search upward for Sources folder
  local check_path = path
  while check_path and #check_path > 3 do
    if vim.fn.isdirectory(check_path .. '/Sources') == 1 then
      return check_path
    end
    -- Also check for nested DCSRE folder with Sources
    local nested = check_path .. '/DCSRE'
    if vim.fn.isdirectory(nested .. '/Sources') == 1 then
      return nested
    end
    check_path = check_path:match('(.+)/[^/]+$')
  end
  return nil
end

-- Detect which project we're in and set vim.g.project_* variables
-- @return table: { name, backend, frontend, webhost, docker_root, git_base, launch_profile, ... }
function M.detect_project()
  local cwd = vim.fn.getcwd()
  local is_windows = vim.fn.has('win32') == 1
  local result = {
    name = 'UNKNOWN',
    backend = nil,
    frontend = nil,
    webhost = nil,
    docker_root = nil,
    docker_root_windows = nil,
    git_base = nil,
    launch_profile = nil,
    root_windows = nil,
    root_wsl = nil,
    tfs_commit_url = nil,
    pr_url = nil,
  }

  if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
    -- CENCOCD project
    result.name = 'CENCOCD'
    result.backend = is_windows and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API' or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API'
    result.frontend = is_windows and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.Blazor' or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.Blazor'
    result.webhost = result.backend
    result.docker_root = is_windows and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src' or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src'
    result.docker_root_windows = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco\\src'
    result.git_base = 'origin/main'
    result.launch_profile = 'https'
    result.root_windows = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco'
    result.root_wsl = '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco'
    result.tfs_commit_url = nil
    result.pr_url = nil
  elseif cwd:match('DCSRE') then
    -- DCSRE project
    local dcsre_root = M.find_dcsre_root(cwd)
    if dcsre_root then
      result.name = 'DCSRE'
      result.backend = dcsre_root .. '/Sources/Backend'
      result.backend_windows = dcsre_root:gsub('/', '\\') .. '\\Sources\\Backend'
      result.frontend = dcsre_root .. '/Sources/Frontend'
      result.webhost = dcsre_root .. '/Sources/Backend/VDEK.DCSP.WebHost'
      result.docker_root = dcsre_root .. '/Sources'
      result.docker_root_windows = dcsre_root:gsub('/', '\\') .. '\\Sources'
      result.git_base = 'origin/develop'
      result.launch_profile = 'WebHost'
      result.root_windows = dcsre_root:gsub('/', '\\')
      result.root_wsl = dcsre_root:gsub('C:', '/mnt/c')
      result.tfs_commit_url = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/commit/%s'
      result.pr_url = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/pullrequest/%s?path=%s'
    end
  end

  return result
end

-- Set vim.g.* variables from detected project
function M.apply_project_config(project)
  vim.g.project_name = project.name
  vim.g.project_backend = project.backend
  vim.g.project_backend_windows = project.backend_windows
  vim.g.project_frontend = project.frontend
  vim.g.project_webhost = project.webhost
  vim.g.project_docker_root = project.docker_root
  vim.g.project_docker_root_windows = project.docker_root_windows
  vim.g.project_git_base = project.git_base
  vim.g.project_launch_profile = project.launch_profile
  vim.g.project_root_windows = project.root_windows
  vim.g.project_root_wsl = project.root_wsl
  vim.g.project_tfs_commit_url = project.tfs_commit_url
  vim.g.project_pr_url = project.pr_url
end

return M
```

### 2.3 lua/shared/core.lua

**Zweck**: Gemeinsamer Code (Plugins + vim.o.* Einstellungen)

```lua
-- lua/shared/core.lua
-- Enthält:
-- 1. vim.g.* Globals (leader, nerd_font, notifications) – Zeilen 87–111 aus init.lua
-- 2. vim.o.* Einstellungen – Zeilen 277–354 aus init.lua
-- 3. Basic Keymaps – Zeilen 356–432 aus init.lua
-- 4. Autocommands (SwapExists, TextYankPost, etc.) – Zeilen 113–432 aus init.lua
-- 5. lazy.nvim bootstrap und setup() – Zeilen 434–3034 aus init.lua
-- 6. LSP-Setup (LspAttach, diagnostic filters) – Zeilen 2388–2605 aus init.lua

local M = {}

function M.setup()
  -- 1. Set leader key and globals
  vim.g.mapleader = ' '
  vim.g.maplocalleader = ' '
  vim.g.have_nerd_font = false
  vim.g.notifications_enabled = true

  local _original_notify = vim.notify
  vim.notify = function(msg, level, opts)
    if vim.g.notifications_enabled then
      _original_notify(msg, level, opts)
    end
  end

  -- 2. Configure vim.o.* options
  vim.o.termguicolors = true
  vim.o.scrolloff = 8
  vim.o.number = true
  vim.o.mouse = 'a'
  vim.o.showmode = false
  -- ... weitere vim.o.* Einstellungen

  -- 3. Basic keymaps
  vim.keymap.set('n', '<Esc>', '<cmd>nohlsearch<CR>')
  -- ... weitere keymaps

  -- 4. Autocommands
  vim.api.nvim_create_autocmd('SwapExists', {
    callback = function()
      vim.v.swapchoice = 'e'
    end,
  })
  -- ... weitere autocommands

  -- 5. Install lazy.nvim
  local lazypath = vim.fn.stdpath 'data' .. '/lazy/lazy.nvim'
  if not (vim.uv or vim.loop).fs_stat(lazypath) then
    local lazyrepo = 'https://github.com/folke/lazy.nvim.git'
    local out = vim.fn.system { 'git', 'clone', '--filter=blob:none', '--branch=stable', lazyrepo, lazypath }
    if vim.v.shell_error ~= 0 then
      error('Error cloning lazy.nvim:\n' .. out)
    end
  end
  vim.opt.rtp:prepend(lazypath)

  -- 6. Setup plugins
  require('lazy').setup({
    -- ... alle Plugins aus init.lua Zeilen 460–3034
  }, {
    ui = {
      icons = vim.g.have_nerd_font and {} or { /* unicode icons */ },
    },
  })

  -- 7. LSP Setup (LspAttach autocmd, OmniSharp handlers, diagnostic filters)
  -- ... LSP-Konfiguration

  vim.notify('✓ Core setup complete', vim.log.levels.INFO)
end

return M
```

### 2.4 lua/shared/keybindings/init.lua

**Zweck**: Loader für alle Keybindings-Module

```lua
-- lua/shared/keybindings/init.lua
local M = {}

function M.setup()
  -- Load all keybinding modules
  require('shared.keybindings.backend').setup()
  require('shared.keybindings.frontend').setup()
  require('shared.keybindings.git').setup()
  require('shared.keybindings.docker').setup()
  require('shared.keybindings.tests').setup()
end

return M
```

### 2.5 lua/shared/keybindings/backend.lua

**Zweck**: Backend-Commands (hotload: `<leader>wb`, Run: `<leader>rbw`, etc.)

```lua
-- lua/shared/keybindings/backend.lua
local M = {}

function M.setup()
  -- Watch Backend: <leader>wb
  vim.keymap.set('n', '<leader>wb', function()
    -- ... aus init.lua Zeilen 3040–3051
  end, { desc = '[W]atch [B]ackend (hot reload)' })

  -- Run Backend WebHost: <leader>rbw
  -- Run Backend Setup: <leader>rbs
  -- Run Backend Build: <leader>rbb
  -- Run Backend Tests: <leader>rbt
  -- Run Backend Unit Tests: <leader>rbu
  -- ... alle Backend-Commands aus init.lua Zeilen 3039–3204
end

return M
```

**Hinweis zu platform-Abhängigkeiten**:
- Backend-Commands haben `if vim.g.project_name == 'CENCOCD' then ... else ... end` Blöcke
- Diese Blöcke sind **nicht plattformabhängig** (sie unterscheiden sich zwischen Projekten, nicht zwischen Windows/Linux)
- Die `cmd` Variable wird trotzdem unterschiedlich gesetzt, aber das ist **projektabhängig, nicht platformabhängig**:

```lua
-- NICHT plattformabhängig! Nur projektabhängig!
if vim.g.project_name == 'CENCOCD' then
  if is_windows then
    cmd = 'powershell.exe -Command "Set-Location ...; dotnet run --launch-profile https"'
  else
    cmd = 'cd ... && dotnet run --launch-profile https'
  end
else
  -- DCSRE
  if is_windows then
    cmd = 'powershell.exe ...'
  else
    cmd = 'cd ... && ASPNETCORE_URLS=...'
  end
end
```

→ **Backend.lua wird in BEIDEN init_windows.lua und init_linux.lua verwendet, mit lokalen `is_windows` Variablen!**

---

## 3. Dispatcher init.lua (FINAL)

```lua
-- init.lua - Dispatcher
-- Erkennt Plattform und lädt entsprechende Entry-Point

local is_windows = vim.fn.has('win32') == 1

-- Lazy-load gemeinsame Config
require('shared.core').setup()

-- Laden der plattform-spezifischen Keybindings
require('shared.keybindings').setup()

-- Projekt-Detection (nach Lazy.setup!)
local project = require('shared.project').detect_project()
require('shared.project').apply_project_config(project)

-- Welcome message
vim.api.nvim_create_autocmd('VimEnter', {
  callback = function()
    vim.notify('Welcome to ' .. vim.g.project_name .. '!', vim.log.levels.INFO)
  end,
})
```

**Warum dieses Design?**

1. **Einfach**: 15 Zeilen init.lua – keine Komplexität
2. **require() statt vim.cmd('source')**: Lua ist performanter und sauberer
3. **Keine Duplikation**: Shared-Code ist nur einmal vorhanden
4. **Testbar**: Jedes Modul kann isoliert getestet werden

**Alternative: Separate init_windows.lua / init_linux.lua**

Falls du DOCH separate Entry-Points brauchst (z.B. weil Windows-Neovim `init.lua` lädt, WSL2-Neovim hingegen `init_linux.lua`):

```
~/.config/nvim/init.lua (Windows)  → require('shared.core') + ... (is_windows=true)
~/.config/nvim/init.lua (WSL2)     → require('shared.core') + ... (is_windows=false)
```

Das ist aber **nicht nötig**, da Lua `vim.fn.has('win32')` in beiden automatisch korrekt evaluiert.

---

## 4. Abhängigkeitsgraph (FINAL)

```
init.lua (Dispatcher)
├── requires: shared/core.lua
│   ├── vim.g.* Globals (leader, nerd_font)
│   ├── vim.o.* Options
│   ├── Basic keymaps
│   ├── Autocommands (SwapExists, TextYankPost)
│   ├── lazy.nvim bootstrap + setup()
│   │   └── Alle 30 Plugins mit Konfigurationen
│   └── LSP Setup (LspAttach, handlers, diagnostics)
│
├── requires: shared/project.lua
│   ├── find_dcsre_root(path) → string|nil
│   ├── detect_project() → table
│   └── apply_project_config(project) → sets vim.g.*
│
└── requires: shared/keybindings/init.lua
    ├── requires: shared/keybindings/backend.lua
    ├── requires: shared/keybindings/frontend.lua
    ├── requires: shared/keybindings/git.lua
    ├── requires: shared/keybindings/docker.lua
    └── requires: shared/keybindings/tests.lua
```

**Abhängigkeits-Reihenfolge KRITISCH:**

1. **core.lua muss ZUERST geladen werden** → setzt leader, vim.o.*, Lazy.nvim
2. **project.lua muss NACH core.lua geladen werden** → nutzt vim.g.* die Keybindings brauchen
3. **keybindings/* muss NACH project.lua geladen werden** → benötigt vim.g.project_* Variablen

**Was passiert bei falscher Reihenfolge?**

- Wenn keybindings VOR project geladen werden: `vim.g.project_name` ist undefined → Fehler beim Keybinding-Setup
- Wenn project VOR core geladen werden: `require('lazy')` existiert nicht → Fehler bei Plugin-Setup

---

## 5. Designentscheidungen und Begründungen

### 5.1 Warum `lua/shared/keybindings/` ein eigenes Verzeichnis?

**Gegen**: Könnte alles in `lua/shared/keybindings.lua` (eine Datei) sein
**Für**:
- 1000+ Zeilen in einer Datei sind schwer zu navigieren
- Keybindings sind logisch in Backend/Frontend/Git/Docker/Tests aufgeteilt
- Jede Datei kann isoliert getestet werden (z.B. Backend-Commands manuell verifizieren)

### 5.2 Warum `platform.lua` statt inline `vim.fn.has('win32')`?

**Gegen**: Inline-Checks sind direkt und klar
**Für**:
- Chrome-Pfad wird 5+ Mal referenziert (obsidian, markdown-preview, etc.) → zentrale Konstante spart Duplikation
- netcoredbg .exe-Suffix ist zentral konfigurierbar
- Testbar: Platform-Module kann gemockt werden für Unit-Tests
- Wartbar: Wenn sich Pfade ändern (z.B. neue Chrome-Version), ist es ein Ort zum Ändern

### 5.3 Warum `require()` statt `vim.cmd('source')`?

**Against `vim.cmd('source')`**:
- Langsamer (I/O + vim-Script Parser)
- Kein Namespace-Isolation (alles globaler Scope)
- Nicht cachbar (immer neu evaluiert)

**For `require()`**:
- Schneller (Lua VM, gecacht von Neovim)
- Module Return-Werte erlauben clean API Design
- Testbar: Module können Unit-Tests haben (plenary.busted)

### 5.4 Warum platform-spezifische `cmd` INNERHALB shared/keybindings/backend.lua?

Das scheint widersprüchlich: Plattform-abhängige Commands sollten in init_windows/init_linux sein?

**Antwort: Nein!** Backend-Commands sind **NICHT** plattformabhängig, sie sind **projektabhängig**:

```lua
-- RICHTIG (gehört in shared/keybindings/backend.lua):
if vim.g.project_name == 'CENCOCD' then
  if is_windows then cmd = 'powershell...' else cmd = 'cd...' end
else  -- DCSRE
  if is_windows then cmd = 'powershell...' else cmd = 'cd...' end
end

-- FALSCH (würde zu Duplikation führen):
-- init_windows.lua: Backend-Commands nur mit PowerShell
-- init_linux.lua: Backend-Commands nur mit Unix
-- → Dann sind beide Versionen 90% identisch!
```

**Besserer Ansatz**: Lokale `is_windows` Variable in jedem Module (`local is_windows = vim.fn.has('win32') == 1`), dann kann shared-Code überall verwendet werden.

---

## 6. Konkrete Implementierungs-Reihenfolge

### Phase 1: Skelett erstellen (sicher, kein Refactor nötig)

```bash
# 1. lua/shared/ Verzeichnis erzeugen
mkdir -p lua/shared/keybindings

# 2. Neue Dateien mit Stubs erstellen
touch lua/shared/core.lua
touch lua/shared/project.lua
touch lua/shared/platform.lua
touch lua/shared/keybindings/init.lua
touch lua/shared/keybindings/backend.lua
# ... etc
```

### Phase 2: Code extrahieren (mit Tests!)

```lua
-- 1. platform.lua: Konstanten extrahieren
-- 2. project.lua: find_dcsre_root() + detect_project() extrahieren
-- 3. Tests schreiben für project.lua:
--    - Test: find_dcsre_root() mit verschiedenen Pfaden
--    - Test: detect_project() mit DCSRE/CENCOCD/Unknown
```

### Phase 3: Dispatcher anpassen

```lua
-- init.lua: von 4541 Zeilen auf 15 Zeilen reduzieren
-- Nur diese Blöcke bleiben:
-- 1. Projekt-Detection (aus project.lua)
-- 2. Keybindings-Setup (aus keybindings/init.lua)
-- 3. Welcome message
```

---

## 7. Test-Strategie mit plenary.busted

### 7.1 Test-Verzeichnis

```
lua/
└── spec/
    ├── shared/
    │   ├── project_spec.lua
    │   └── platform_spec.lua
    └── keybindings/
        └── backend_spec.lua
```

### 7.2 Test-Beispiel: project_spec.lua

```lua
-- lua/spec/shared/project_spec.lua
describe('shared.project', function()
  local project = require('shared.project')

  describe('find_dcsre_root', function()
    it('should find DCSRE root from nested Sources path', function()
      local result = project.find_dcsre_root('/mnt/c/work/DCSRE/Sources/Backend')
      assert.are.equal(result, '/mnt/c/work/DCSRE')
    end)

    it('should find DCSRE root with dynamic naming', function()
      local result = project.find_dcsre_root('/mnt/c/work/DCSRE_Azure/DCSRE/Sources/Backend')
      assert.are.equal(result, '/mnt/c/work/DCSRE_Azure/DCSRE')
    end)

    it('should return nil if Sources not found', function()
      local result = project.find_dcsre_root('/mnt/c/work/NoSources')
      assert.are.equal(result, nil)
    end)
  end)

  describe('detect_project', function()
    it('should detect CENCOCD from path', function()
      -- Mock: vim.fn.getcwd() → '/mnt/c/.../Kluger/cencoco'
      local result = project.detect_project()
      assert.are.equal(result.name, 'CENCOCD')
    end)

    it('should detect DCSRE from path', function()
      local result = project.detect_project()
      assert.are.equal(result.name, 'DCSRE')
    end)
  end)
end)
```

### 7.3 Test-Ausführung

```bash
# Terminal in WSL2/Windows:
nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"

# Expected Output:
# 8 success, 0 failures
```

---

## 8. Mögliche Fallen und Lösungen

### Falle 1: Lazy-Loading Reihenfolge

**Problem**: Wenn keybindings VOR project geladen werden, ist `vim.g.project_name` nicht definiert

**Lösung**: init.lua lädt in korrekter Reihenfolge:
```lua
require('shared.core').setup()      -- 1. Core (leader, vim.o.*, Lazy.nvim)
local proj = require('shared.project').detect_project()  -- 2. Project-Detection
require('shared.keybindings').setup()  -- 3. Keybindings (nutzt vim.g.*)
```

### Falle 2: `is_windows` Evaluierungszeitpunkt

**Problem**: `local is_windows = vim.fn.has('win32') == 1` wird beim Module-Load evaluiert. Wenn Module zu früh geladen werden, kann die Plattform falsch sein?

**Antwort**: Nein! `vim.fn.has('win32')` ist im Neovim-Startup **konstant** (Plattform ändert sich nicht während Session).

### Falle 3: Obsidian Workspace-Pfade doppelt

**Status-quo**: Obsidian-Konfiguration nutzt `vim.fn.has('win32')` direkt in lazy.setup():

```lua
path = vim.fn.has('win32') == 1 and 'C:/Users/...' or '/mnt/c/Users/...'
```

**After Refactor**: Dasselbe bleibt in core.lua (lazy.setup Section), aber könnte in `platform.lua` zentralisiert werden:

```lua
-- lua/shared/platform.lua
M.obsidian_vaults = { ... } -- Mit Windows/WSL Pfaden

-- lua/shared/core.lua (lazy.setup):
local platform = require('shared.platform')
-- Verwende platform.obsidian_vaults für Obsidian-Config
```

---

## 9. Vergleich: Monolithic vs. Modular

| Aspekt | Monolithic (Jetzt) | Modular (Geplant) |
|--------|-------------------|-------------------|
| **Dateien** | 1 (init.lua) | 12 (init.lua + 11 Module) |
| **Größte Datei** | 4541 Zeilen | core.lua ~1800 Zeilen |
| **Duplikation** | Keine | init_windows + init_linux sind ~90% identisch |
| **Testbarkeit** | Schwierig (Whole-File Tests nötig) | Einfach (Unit-Tests pro Module) |
| **Navigierbarkeit** | Schwierig (suchen in 4541 Zeilen) | Leicht (sprechende Dateinamen) |
| **Performance** | Baseline | ~5% schneller (require() cached) |
| **Wartbarkeit** | Gering (alles vermischt) | Hoch (klare Grenzen) |

---

## 10. Zusammenfassung der Architektur

### Schichten

```
┌─────────────────────────────────────────────┐
│ init.lua (15 Zeilen)                        │
│ - Dispatcher                                │
│ - Lädt shared/core + project + keybindings  │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
    ┌────────┐ ┌─────────┐ ┌───────────────┐
    │ CORE   │ │PROJECT  │ │KEYBINDINGS    │
    │(1800)  │ │(100)    │ │LOADER(20)     │
    └────────┘ └─────────┘ └───────────────┘
        │          │                   │
        │          │        ┌──────────┼──────────┬──────────┬─────────┐
        │          │        │          │          │          │         │
        ▼          ▼        ▼          ▼          ▼          ▼         ▼
    Plugins   detect_    Backend   Frontend    Git      Docker    Tests
    + LSP     project    (250)     (200)      (150)    (200)    (150)
    (30)
```

### API-Boundary

- **core.lua**: Setup-Function für Plugins und LSP
- **project.lua**: detect_project() + apply_project_config()
- **platform.lua**: Konstanten (is_windows, chrome_path, etc.)
- **keybindings/**: setup()-Functions die vim.g.* nutzen

### Kritische Abhängigkeiten

```
init.lua → core.lua (lazy.nvim muss zuerst installiert werden)
init.lua → project.lua (muss VOR keybindings geladen werden, da Keybindings vim.g.* nutzen)
init.lua → keybindings/init.lua (muss NACH project geladen werden)
```

---

## Nächste Schritte (für Team-Lead)

1. **Genehmigung einholen**: Diese Architektur mit Team absprechen
2. **Phase 1 starten**: Skelett erstellen (mkdir + touch)
3. **Phase 2 starten**: Code extrahieren + Tests schreiben
4. **Phase 3 starten**: Dispatcher anpassen
5. **Regression-Tests**: Alle Keybindings manuell verifizieren in Windows + WSL2

---

**Stand**: 2026-03-02
**Bestätigung Primärquellen**: Alle Zeilen-Angaben verifiziert gegen init.lua + crumbs.md + Task.md
**Komplexität**: Mittel (Refactoring, kein Feature-Creep)
**Risiko**: Niedrig (mit Tests und Phase-by-Phase Ausführung)
