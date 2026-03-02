---
wave: exploration
agent: E03
focus: shared-module-design
status: final
primaerquelle_gelesen: true
---

# E03: Shared Module Design

## Executive Summary

Die init.lua hat drei konzeptionelle Schichten:
1. **Shared Core** (Zeilen 87–432): Leader, Settings, Standard-Keymaps, Lazy.nvim Bootstrap
2. **Project Detection** (Zeilen 194–275): Projekt + Plattform-basierte Pfad-Konfiguration
3. **Custom Keybindings** (Zeilen 3036–4539): Projekt-spezifische Terminal-Commands

**Empfohlene Modul-Struktur:**
```
lua/shared/
├── core.lua          # Lazy bootstrap, vim.o.*, standard keymaps
├── project.lua       # Projekt-Detection, Pfad-Setup
├── constants.lua     # Chrome-Pfade, URLs, statische Werte
└── platform.lua      # is_windows Variable + Helpers
```

---

## 1. Modul-Grenzziehung

### lua/shared/core.lua – SHARED, plattformunabhängig

**Inhalt (Zeilen aus init.lua):**

| Block | Zeilen | Beschreibung |
|-------|--------|-------------|
| Leader + globals | 87–111 | `vim.g.mapleader`, `have_nerd_font`, notification toggle |
| SwapExists Autocmd | 113–120 | E325 Swap-Fehler ignorieren (Diffview, Obsidian, Telescope) |
| Terminal BG Reset | 188–192 | VimLeave: `io.write('\027]104\027\\')` |
| Lazy.nvim Bootstrap | 434–447 | `git clone lazy.nvim` wenn nicht vorhanden |
| vim.o.* Settings | 277–354 | Alle Optionen: number, scrolloff, mouse, clipboard, etc. |
| Basic Keymaps | 356–432 | Esc→nohlsearch, C-h/j/k/l, C-d/u, leader-q/bd, etc. |
| Auto-save InsertLeave | 373–381 | InsertLeave autocmd + silent update |
| TextYankPost | 426–432 | Highlight yank |

**Keine Abhängigkeiten:** Diese Blöcke sind **vollständig plattformunabhängig**, kein `is_windows`, keine Pfad-Konversionen.

**API:** Keine – diese werden direkt am Anfang von `init.lua` geladen.

```lua
-- In init.lua oder init_windows.lua:
require('shared.core')  -- Setzt alle vim.o.*, keymaps, autocmds
```

---

### lua/shared/platform.lua – SHARED, aber mit Plattform-Erkennungs-Helpers

**Inhalt:**

```lua
-- M.is_windows: Central platform detection
M.is_windows = vim.fn.has('win32') == 1

-- M.get_chrome_path(): Platform-aware Chrome executable
-- Returns: string (C:\Program Files\... oder /mnt/c/Program Files/...)

-- M.normalize_path(path): Cross-platform path handling
-- Converts backslash to forward slash
-- Returns: normalized string

-- M.get_mason_path(package): Safe mason package executable path
-- Returns: string with .exe suffix on Windows
```

**Nutzer:**
- `lua/shared/project.lua` (braucht `is_windows` für Ternary-Operatoren)
- `init_windows.lua` + `init_linux.lua` (beide laden das)
- Plugins wie Markdown Preview, Obsidian, DAP

**Beispiel:**
```lua
local platform = require('shared.platform')
if platform.is_windows then
  local chrome = platform.get_chrome_path()
  -- returns: C:\Program Files\Google\Chrome\...
end
```

---

### lua/shared/project.lua – SHARED mit projekt-spezifischem Output

**Eingaben:**
- `cwd` (current working directory)
- `is_windows` (von platform.lua)

**Ausgabe: projektconfig Table**

```lua
local M = {}

-- M.detect_project(cwd, is_windows)
-- Returns: {
--   name: string ('DCSRE' | 'CENCOCD' | 'UNKNOWN'),
--   backend: string (Unix-Format /mnt/c/... oder C:/...),
--   backend_windows: string (Windows-Backslash-Format C:\...),
--   frontend: string,
--   webhost: string,
--   docker_root: string (Forward-Slash, will be converted to backslash in PowerShell),
--   docker_root_windows: string (Backslash-Format),
--   git_base: string ('origin/develop' | 'origin/main'),
--   launch_profile: string ('WebHost' | 'https'),
--   root_windows: string (Backslash, für PowerShell-Commands),
--   root_wsl: string (WSL-Format /mnt/c/...),
--   tfs_commit_url: string | nil,
--   pr_url: string | nil,
-- }

-- M.find_dcsre_root(path)
-- Moves find_dcsre_root() from Zeilen 203–227

return M
```

**Nutzer:**
```lua
local project = require('shared.project')
local platform = require('shared.platform')

-- In init.lua Top Level:
local cwd = vim.fn.getcwd()
local config = project.detect_project(cwd, platform.is_windows)

-- Dann alle config Variablen in vim.g setzen:
vim.g.project_name = config.name
vim.g.project_backend = config.backend
-- ... etc
```

---

### lua/shared/constants.lua – Statische Werte

**Inhalt:**

```lua
local M = {}

-- Chrome paths (mit Plattform-Unterschied resolved durch platform.lua)
M.CHROME_PATH_WINDOWS = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
M.CHROME_PATH_WSL = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'

-- Obsidian Workspace Paths (Hard-coded, werden in init_windows.lua / init_linux.lua unterschiedlich genutzt)
M.OBSIDIAN_WORKSPACES = {
  DCSRE = { -- wird via platform.is_windows unterschiedlich gemappt
    win = 'C:/Users/Administrator/Documents/Work/Code2/DCSRE/obsidian-vault',
    wsl = '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/obsidian-vault',
  },
  -- ... etc
}

-- Azure DevOps URLs (projektunabhängig)
M.TFS_URLS = {
  DCSRE_COMMIT = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/commit/%s',
  -- ... etc
}

return M
```

---

### init_windows.lua und init_linux.lua – PLATFORM-SPEZIFISCH

Diese beiden Dateien sind **unterschiedlich**, aber **sehr dünn**:

```lua
-- init_windows.lua (Windows Native Neovim)
========================================

-- Leader + mapleader (Zeile 90)
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- Shared Core (Zeilen 87–432)
require('shared.core')

-- Platform detection
local platform = require('shared.platform')
assert(platform.is_windows, 'init_windows.lua requires Windows!')

-- Project detection (Zeilen 194–275)
local project = require('shared.project')
local cwd = vim.fn.getcwd()
local config = project.detect_project(cwd, platform.is_windows)
vim.g.project_name = config.name
vim.g.project_backend = config.backend
vim.g.project_backend_windows = config.backend_windows
-- ... alle vim.g.project_* Variablen setzen

-- .claude Auto-Copy + Terminal BG (Zeilen 122–192)
-- → Diese sind shared (kein Platform-Check intern)
require('shared.autocmds')

-- Lazy.nvim + Plugins (Zeilen 449–3034)
require('shared.plugins')

-- Projekt-spezifische Keybindings (Zeilen 3036–4539)
-- WICHTIG: Nutzen vim.g.project_* Variablen
-- → Diese sind SHARED (funktionieren identisch)
require('shared.keybindings')
```

```lua
-- init_linux.lua (WSL2 Neovim)
================================
-- Identisch wie init_windows.lua!
-- Der Unterschied ist nur in platform.is_windows (false), alles andere wird automatisch angepasst.
```

**Warum sind sie identisch?**
- Die Projekt-Pfade werden von `project.detect_project()` bereits für beide Plattformen korrekt gesetzt
- Die Terminal-Commands (powershell vs bash) werden in den Keybindings per `if is_windows` unterschieden
- `vim.g.project_root_windows` wird **immer** als Backslash-Pfad gesetzt, auch auf WSL2 (für PowerShell-Aufrufe)

---

## 2. API-Design für project.lua

### Detaillierte Modul-Struktur

```lua
-- lua/shared/project.lua
local M = {}

--- Find DCSRE root directory dynamically.
--- Looks for folder containing "Sources" subdirectory.
---
--- @param path string Current working directory (normalized to /)
--- @return string | nil Root directory of DCSRE project, or nil if not found
local function find_dcsre_root(path)
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
    -- Also check for nested DCSRE folder with Sources (e.g., DCSRE_Azure/DCSRE/Sources)
    local nested = check_path .. '/DCSRE'
    if vim.fn.isdirectory(nested .. '/Sources') == 1 then
      return nested
    end
    check_path = check_path:match('(.+)/[^/]+$')
  end
  return nil
end

--- Detect which project we're in and configure paths accordingly.
---
--- @param cwd string Current working directory
--- @param is_windows boolean Platform detection result
--- @return table Project configuration table with keys:
---   - name: 'DCSRE' | 'CENCOCD' | 'UNKNOWN'
---   - backend: Unix-style path (C:/ or /mnt/c/)
---   - backend_windows: Windows Backslash path (C:\...)
---   - frontend: Unix-style path
---   - webhost: Unix-style path
---   - docker_root: Unix-style path
---   - docker_root_windows: Windows Backslash path
---   - git_base: 'origin/develop' | 'origin/main'
---   - launch_profile: 'WebHost' | 'https'
---   - root_windows: Windows Backslash path (for PowerShell)
---   - root_wsl: WSL path (/mnt/c/...)
---   - tfs_commit_url: string | nil
---   - pr_url: string | nil
function M.detect_project(cwd, is_windows)
  local config = {
    name = 'UNKNOWN',
    backend = '',
    backend_windows = '',
    frontend = '',
    webhost = '',
    docker_root = '',
    docker_root_windows = '',
    git_base = 'origin/main',
    launch_profile = 'https',
    root_windows = '',
    root_wsl = '',
    tfs_commit_url = nil,
    pr_url = nil,
  }

  if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
    -- CENCOCD project
    config.name = 'CENCOCD'
    local base_win = 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src'
    local base_wsl = '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src'

    config.backend = is_windows and (base_win .. '/Core/CenCoCo.Core.API') or (base_wsl .. '/Core/CenCoCo.Core.API')
    config.backend_windows = base_win:gsub('/', '\\') .. '\\Core\\CenCoCo.Core.API'
    config.frontend = is_windows and (base_win .. '/Core/CenCoCo.Core.Blazor') or (base_wsl .. '/Core/CenCoCo.Core.Blazor')
    config.webhost = config.backend
    config.docker_root = is_windows and base_win or base_wsl
    config.docker_root_windows = base_win:gsub('/', '\\')
    config.git_base = 'origin/main'
    config.launch_profile = 'https'
    config.root_windows = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco'
    config.root_wsl = base_wsl
    config.tfs_commit_url = nil
    config.pr_url = nil

  elseif cwd:match('DCSRE') then
    -- DCSRE project - find root dynamically
    local dcsre_root = find_dcsre_root(cwd)
    if dcsre_root then
      config.name = 'DCSRE'
      config.backend = dcsre_root .. '/Sources/Backend'
      config.backend_windows = dcsre_root:gsub('/', '\\') .. '\\Sources\\Backend'
      config.frontend = dcsre_root .. '/Sources/Frontend'
      config.webhost = dcsre_root .. '/Sources/Backend/VDEK.DCSP.WebHost'
      config.docker_root = dcsre_root .. '/Sources'
      config.docker_root_windows = dcsre_root:gsub('/', '\\') .. '\\Sources'
      config.git_base = 'origin/develop'
      config.launch_profile = 'WebHost'
      config.root_windows = dcsre_root:gsub('/', '\\')
      config.root_wsl = dcsre_root:gsub('C:', '/mnt/c')
      config.tfs_commit_url = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/commit/%s'
      config.pr_url = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/pullrequest/%s?path=%s'
    end
  end

  return config
end

M.find_dcsre_root = find_dcsre_root

return M
```

---

## 3. Kritische Designentscheidungen

### Decision 1: vim.g.project_root_windows **immer** mit Backslash, auch auf WSL2

```lua
-- Auf WSL2:
vim.g.project_root_windows = '/path/in/wsl':gsub('C:', '/mnt/c') -- FALSCH!

-- Richtig:
local dcsre_root = find_dcsre_root(cwd)  -- Format: /mnt/c/... oder C:/...
vim.g.project_root_windows = dcsre_root:gsub('/', '\\')  -- IMMER Backslash!
```

**Grund:** Die Keybindings rufen `powershell.exe -Command "cd '...; ..."` auf, auch von WSL2 aus. PowerShell erwartet Windows-Pfade mit Backslash.

### Decision 2: normalize_path standardisiert auf Forward-Slash intern

```lua
-- find_dcsre_root erwartet: normalized (forward-slash)
-- Project-Detection macht: .gsub('\\', '/') am Anfang
local dcsre_root = find_dcsre_root(cwd:gsub('\\', '/'))
```

### Decision 3: is_windows wird EINMAL am Start geprüft, nicht überall

```lua
-- Nicht so:
if vim.fn.has('win32') == 1 then
  -- ...
end

-- Sondern so:
local platform = require('shared.platform')
if platform.is_windows then
  -- ...
end
```

### Decision 4: project.lua kennt **nichts** von Plugins

`project.lua` gibt nur Pfade und Projekt-Namen zurück. Es lädt **keine** Plugins, startet **keine** Autocmds, setzt **keine** Keybindings.

---

## 4. Wie nutzen init_windows.lua / init_linux.lua die shared Module?

### init_windows.lua (Windows Native Neovim)

```lua
--[[
    Windows Native Neovim Configuration
    Uses shared modules for core, projects, and keybindings
]]

-- [[ Leader Keys ]]
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- [[ Shared Core Setup ]]
-- Sets vim.o.* options, basic keymaps, autocmds
-- Platform-independent, runs on both Windows and WSL2
require('shared.core')

-- [[ Platform Detection ]]
local platform = require('shared.platform')
-- On Windows: platform.is_windows = true
-- On WSL2: platform.is_windows = false (but we're in init_windows.lua, so we know it's Windows)

-- [[ Project Detection ]]
local project = require('shared.project')
local cwd = vim.fn.getcwd()
local config = project.detect_project(cwd, platform.is_windows)

-- Set all project globals
vim.g.project_name = config.name
vim.g.project_backend = config.backend
vim.g.project_backend_windows = config.backend_windows
vim.g.project_frontend = config.frontend
vim.g.project_webhost = config.webhost
vim.g.project_docker_root = config.docker_root
vim.g.project_docker_root_windows = config.docker_root_windows
vim.g.project_git_base = config.git_base
vim.g.project_launch_profile = config.launch_profile
vim.g.project_root_windows = config.root_windows
vim.g.project_root_wsl = config.root_wsl
vim.g.project_tfs_commit_url = config.tfs_commit_url
vim.g.project_pr_url = config.pr_url

-- Welcome message
vim.api.nvim_create_autocmd('VimEnter', {
  callback = function()
    vim.notify('Welcome to ' .. vim.g.project_name .. '!', vim.log.levels.INFO)
  end,
})

-- [[ Custom Autocmds (Platform-aware) ]]
-- .claude Auto-Copy (supports Win32 + WSL2 paths)
-- Terminal background color
require('shared.autocmds')

-- [[ Lazy.nvim Bootstrap and Plugin Setup ]]
-- All plugins are defined in shared/plugins.lua
require('shared.plugins')

-- [[ Custom Keybindings ]]
-- Project-specific commands that use vim.g.project_* variables
-- These handle both platform.is_windows paths and powershell.exe calls
require('shared.keybindings')
```

### init_linux.lua (WSL2 Neovim)

**Identisch zu init_windows.lua!**

Der einzige Unterschied: Der User startet Neovim von WSL2 aus, also ist `vim.fn.getcwd()` ein WSL2-Pfad (`/mnt/c/...`).
Aber `platform.is_windows = false`, also wählen die Keybindings automatisch die Linux-Branches.

```lua
-- init_linux.lua ist identisch mit init_windows.lua
-- Der Unterschied liegt in platform.is_windows und vim.fn.getcwd(), nicht in der Logik
```

---

## 5. Warum funktioniert das?

### Szenario 1: Windows Native Neovim

```
User startet: nvim C:/Users/.../DCSRE/Sources/Backend/Program.cs
├─ platform.is_windows = true
├─ vim.fn.getcwd() = C:/Users/.../DCSRE/Sources (Windows-Format)
├─ project.detect_project() findet: /Sources/Backend → DCSRE-Root OK ✓
├─ vim.g.project_root_windows = C:\Users\...\DCSRE (Backslash)
└─ Keybindings:
   └─ <leader>rbw
      └─ if is_windows then: powershell.exe -Command "cd 'C:\...\'; dotnet run ..."
      └─ cd-Befehl funktioniert in PowerShell ✓
```

### Szenario 2: WSL2 Neovim (auf Windows-Filesystem)

```
User startet: nvim /mnt/c/Users/.../DCSRE/Sources/Backend/Program.cs
├─ platform.is_windows = false (weil vim.fn.has('win32') == 0 in WSL)
├─ vim.fn.getcwd() = /mnt/c/Users/.../DCSRE/Sources (WSL-Format)
├─ project.detect_project() findet: /mnt/c/... → DCSRE-Root OK ✓
├─ vim.g.project_root_windows = C:\Users\...\DCSRE (wir konvertieren manuell!)
└─ Keybindings:
   └─ <leader>rbw
      └─ if is_windows then: false!
      └─ else: cd /mnt/c/Users/.../DCSRE && dotnet run ...
      └─ cd-Befehl funktioniert in WSL2-Bash ✓
      └─ dotnet funktioniert auf Windows-Filesystem via /mnt/c ✓
```

**Trick:** `vim.g.project_root_windows` wird **absichtlich** als Backslash-Pfad gesetzt, auch auf WSL2!

```lua
-- On WSL2, project.lua does:
local dcsre_root = find_dcsre_root(cwd)  -- e.g., /mnt/c/Users/.../DCSRE
vim.g.project_root_windows = dcsre_root:gsub('/', '\\')  -- Convert to C:\Users\...\DCSRE
```

Das wird nur von PowerShell-Commands genutzt (die sowieso **nicht** von WSL2-Bash laufen).

---

## 6. Modul-Abhängigkeiten

```
init_windows.lua / init_linux.lua
├─ shared/core.lua (NO DEPS)
├─ shared/platform.lua (NO DEPS)
├─ shared/project.lua
│  └─ shared/platform.lua
├─ shared/autocmds.lua (EXTENDS)
│  └─ shared/platform.lua
├─ shared/plugins.lua (EXTENDS)
│  └─ various vim.g.* variables from project detection
└─ shared/keybindings.lua (EXTENDS)
   └─ various vim.g.* variables from project detection
```

---

## 7. Verschiebungsplan

Folgende Blöcke werden **moved** in die shared Module:

### → lua/shared/core.lua
- Zeilen 87–111: Leader, notifications
- Zeilen 113–120: SwapExists
- Zeilen 277–354: vim.o.*
- Zeilen 356–432: Basic keymaps + autocmds

### → lua/shared/platform.lua (NEW)
```lua
M.is_windows = vim.fn.has('win32') == 1
M.get_chrome_path() → depends on is_windows
M.get_mason_path(package) → adds .exe on Windows
M.normalize_path(path) → backslash to forward-slash
```

### → lua/shared/project.lua
- Zeilen 203–227: find_dcsre_root()
- Zeilen 229–268: Projekt-Detection Logic

### → lua/shared/autocmds.lua (NEW)
- Zeilen 122–164: .claude Auto-Copy (with platform check inside)
- Zeilen 166–185: Terminal background color
- Zeilen 188–192: VimLeave terminal reset

### → lua/shared/plugins.lua (MOVE)
- Zeilen 434–447: Lazy.nvim bootstrap
- Zeilen 449–3034: Alle Plugin-Definitionen

### → lua/shared/keybindings.lua (MOVE + SPLIT)
- Zeilen 3036–4539: Alle project-spezifischen Keybindings

---

## 8. Risiken und Mitigationen

### Risk 1: `vim.g.project_root_windows` ist mehrdeutig

**Was ist das?**
- Auf Windows: Aktuelle Weg des Projekts mit Backslash
- Auf WSL2: Konvertierter Pfad (C:\Users\...) für PowerShell-Aufrufe, NICHT der aktuelle Weg

**Mitigation:**
- Umbenennen zu `vim.g.project_root_for_powershell` wäre klarer, aber bricht bestehende Keybindings
- **Statt dessen:** Dokumentation in project.lua sehr deutlich machen

```lua
-- DOKUMENTATION in project.lua:
-- vim.g.project_root_windows ALWAYS has backslash separators (C:\...\...)
-- This is used for PowerShell commands, even on WSL2!
-- It is NOT the current working directory, but a path suitable for Windows .NET tools.
```

### Risk 2: `find_dcsre_root()` könnte auf nested structures fehlschlagen

**Mitigation:** Existiert bereits (Zeilen 220–222: nested DCSRE folder check).

### Risk 3: Platform-Variablen sind global (vim.g), nicht lokal

**Grund:** Keybindings müssen Zugriff auf alle project_* Variablen haben.

**Mitigation:** Das ist OK – Neovim-Konvention, vim.g ist ideal für Config-Werte.

---

## 9. Testbarkeit

Die neuen Module sind sehr testbar:

```lua
-- lua/spec/shared/project_spec.lua

describe('shared.project', function()
  describe('find_dcsre_root', function()
    it('should find DCSRE root from /mnt/c/work/DCSRE/Sources/Backend', function()
      local project = require('shared.project')
      local root = project.find_dcsre_root('/mnt/c/work/DCSRE/Sources/Backend')
      assert.are.equal('/mnt/c/work/DCSRE', root)
    end)

    it('should find nested DCSRE_Azure/DCSRE/Sources', function()
      local project = require('shared.project')
      local root = project.find_dcsre_root('/mnt/c/work/DCSRE_Azure/DCSRE/Sources')
      assert.are.equal('/mnt/c/work/DCSRE_Azure/DCSRE', root)
    end)
  end)

  describe('detect_project', function()
    it('should detect CENCOCD project', function()
      local project = require('shared.project')
      local config = project.detect_project('/mnt/c/Users/Admin/Documents/Work/Kluger/cencoco/src', false)
      assert.are.equal('CENCOCD', config.name)
    end)

    it('should detect DCSRE project with dynamic root', function()
      local project = require('shared.project')
      local config = project.detect_project('/mnt/c/work/DCSRE/Sources/Backend', false)
      assert.are.equal('DCSRE', config.name)
      assert.is_not_nil(config.backend)
    end)
  end)
end)
```

---

## 10. Konkrete Beispiele: Wie nutzen Keybindings die shared Module?

### Example 1: <leader>rbw (Run Backend WebHost)

**Vorher (init.lua):**
```lua
vim.keymap.set('n', '<leader>rbw', function()
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    if is_windows then
      cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; dotnet run ..."'
    else
      cmd = 'cd \'' .. vim.g.project_backend .. '\' && dotnet run ...'
    end
  else  -- DCSRE
    if is_windows then
      cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; ...'
    else
      cmd = 'cd \'' .. vim.g.project_backend .. '\' && ...'
    end
  end
  -- ... execute cmd
end, { desc = '[R]un [B]ackend [W]ebhost' })
```

**Nachher (shared/keybindings.lua):**
```lua
local platform = require('shared.platform')

vim.keymap.set('n', '<leader>rbw', function()
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    if platform.is_windows then
      cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; dotnet run ..."'
    else
      cmd = 'cd \'' .. vim.g.project_backend .. '\' && dotnet run ...'
    end
  else  -- DCSRE
    -- ... same logic
  end
  -- ... execute cmd
end, { desc = '[R]un [B]ackend [W]ebhost' })
```

**Unterschied:** `is_windows` lokal definieren via `require('shared.platform')` statt global.

### Example 2: Obsidian Workspace Detection

**Vorher (init.lua):**
```lua
local obsidian = require('obsidian')
obsidian.setup({
  workspaces = {
    {
      name = 'DCSRE',
      path = vim.fn.has('win32') == 1 and 'C:/Users/.../DCSRE/obsidian-vault'
             or '/mnt/c/Users/.../DCSRE/obsidian-vault',
    },
    -- ... mehr workspaces
  }
})
```

**Nachher (shared/plugins.lua):**
```lua
local platform = require('shared.platform')

local obsidian = require('obsidian')
obsidian.setup({
  workspaces = {
    {
      name = 'DCSRE',
      path = platform.is_windows and 'C:/Users/.../DCSRE/obsidian-vault'
             or '/mnt/c/Users/.../DCSRE/obsidian-vault',
    },
    -- ...
  }
})
```

---

## Zusammenfassung

**Modul-Struktur:**

```
lua/shared/
├── core.lua                  [NO DEPS] Lazy bootstrap, vim.o.*, keymaps
├── platform.lua              [NO DEPS] is_windows, get_chrome_path()
├── project.lua               [→ platform] find_dcsre_root(), detect_project()
├── constants.lua             [NO DEPS] URLs, Chrome-Pfade (optional, aber clean)
├── autocmds.lua              [→ platform] .claude, terminal bg
├── plugins.lua               [→ project] Lazy.setup() + alle Plugins
└── keybindings.lua           [→ platform] Projekt-spezifische Commands
```

**init_windows.lua / init_linux.lua:**
```lua
require('shared.core')
require('shared.platform')
local config = require('shared.project').detect_project(vim.fn.getcwd(), platform.is_windows)
-- Set vim.g.project_* from config
require('shared.autocmds')
require('shared.plugins')
require('shared.keybindings')
```

**Vorteil:**
- ✅ Minimales Duplication zwischen init_windows.lua und init_linux.lua
- ✅ Klare Separation: Shared Code ist wirklich shared
- ✅ Testbar: project.lua hat keine UI-Dependencies
- ✅ Wartbar: Platform-Checks sind zentralisiert in platform.lua
- ✅ Erweiterbar: Neue Projekte einfach in project.lua hinzufügbar

