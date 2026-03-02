# KickStartNeoVim — Ziel-Architektur-Spezifikation

**Version**: 1.0
**Datum**: 2026-03-02
**Status**: Final
**Basis**: KickStartNeoVim_Model.md (verifiziert), Task.md, init.lua Spot-Checks

---

## 1. Architektur-Entscheidung: Variante A vs. Variante B

### Variante B — Minimal-Dispatcher (abgelehnt)

```
init.lua       (10-Zeilen Dispatcher)
init_windows.lua  (≈ aktuelle init.lua minus Linux-Code, ~4300 Zeilen)
init_linux.lua    (≈ aktuelle init.lua minus Windows-Code, ~4100 Zeilen)
```

**Wie es funktioniert:**
`init.lua` brancht per `vim.fn.has('win32')` auf eine der zwei Dateien. Jede Datei ist eine fast-vollständige Kopie der aktuellen init.lua — mit den plattformfremden Branches entfernt.

**Pro:**
- Minimaler Aufwand beim initialen Split
- Keine neuen Konzepte (require, Module)
- Jede Plattform-Datei ist eigenständig lesbar

**Contra:**
- ~4000 Zeilen Code-Duplikation bleibt bestehen
- Änderungen an Plugins, LSP, Keybindings müssen ZWEIMAL gemacht werden
- Kein DRY — zukünftige Pflege kostet doppelt so viel
- Nicht testbar (find_dcsre_root bleibt als Closure, nicht als Funktion in einem Modul)
- Verstößt gegen das eigentliche Ziel der Task.md: `lua/shared/core.lua`

---

### Variante A — Echter Split mit shared/ (empfohlen)

```
init.lua              (~15 Zeilen Dispatcher)
init_windows.lua      (~50 Zeilen Windows-Entry-Point)
init_linux.lua        (~40 Zeilen Linux-Entry-Point)
lua/shared/
  platform.lua        (~35 Zeilen)
  project.lua         (~120 Zeilen)
  core.lua            (~2700 Zeilen)
  keybindings/
    backend.lua       (~180 Zeilen)
    frontend.lua      (~80 Zeilen)
    git.lua           (~120 Zeilen)
    docker.lua        (~140 Zeilen)
    tests.lua         (~200 Zeilen)
    clipboard.lua     (~80 Zeilen)
lua/spec/
  project_spec.lua    (~150 Zeilen Tests)
  platform_spec.lua   (~80 Zeilen Tests)
```

**Pro:**
- DRY: ~2900 Zeilen shared Code existiert nur einmal
- Testbar: `find_dcsre_root`, Projekt-Detection, Pfad-Konversionen als echte Module testbar
- Skalierbar: neues Feature → nur eine Datei ändern
- Task.md-konform: exakt das geforderte SOLL-Schema

**Contra:**
- Mehr Aufwand beim initialen Refactoring (~8-9h)
- `require()` muss korrekt zur Laufzeit auflösen (Deployment-Aspekt, siehe Abschnitt 6.1)

**Empfehlung: Variante A.**

### Warum Variante A trotz "beide Branches sind aktiv"?

Die Tatsache, dass User Windows-Neovim UND WSL2-Neovim parallel nutzt, spricht *für* Variante A:
- Beide Instanzen laden `lua/shared/core.lua` — kein Risiko dass Plugin-Updates nur in einer Datei landen
- `platform.is_windows` wird zur Laufzeit korrekt evaluiert (Windows-Neovim = true, WSL2 = false)
- Keybinding-Module entscheiden per `platform.is_windows`, welchen Befehl sie senden — das ist dasselbe Runtime-Branching wie heute, nur sauber isoliert

Bei Variante B müsste der User nach jedem neuen Keybinding in *beiden* Dateien editieren. Das ist nicht praktikabel.

---

## 2. Ziel-Dateistruktur (Variante A — konkret)

```
KickStartNeoVim/
├── init.lua                    # Dispatcher: ~15 Zeilen
├── init_windows.lua            # Windows Entry-Point: ~50 Zeilen
├── init_linux.lua              # Linux/WSL2 Entry-Point: ~40 Zeilen
│
└── lua/
    ├── shared/
    │   ├── platform.lua        # is_windows, Chrome-Pfade, open_url() — ~35 Zeilen
    │   ├── project.lua         # find_dcsre_root(), detect(), vim.g.* setzen — ~120 Zeilen
    │   ├── core.lua            # vim.opt, Keymaps, Lazy-Bootstrap, alle Plugins — ~2700 Zeilen
    │   └── keybindings/
    │       ├── init.lua        # Lade-Aggregator (require all sub-modules) — ~20 Zeilen
    │       ├── backend.lua     # rbw, rbs, rbb, rbt, rbW — ~180 Zeilen
    │       ├── frontend.lua    # rfr, rfb, rfi, rft, rfw — ~80 Zeilen
    │       ├── git.lua         # gg, gf, gD, gM, gdc, rp, rP, rc — ~120 Zeilen
    │       ├── docker.lua      # rDi, rDa, rDI, rdr, rdr — ~140 Zeilen
    │       ├── tests.lua       # rim, rid, reb, rei, reg, res, reo — ~200 Zeilen
    │       └── clipboard.lua   # yp, yn, gyf, gyd, yP — ~80 Zeilen
    │
    └── spec/
        ├── project_spec.lua    # Tests für project.lua — ~150 Zeilen
        └── platform_spec.lua   # Tests für platform.lua Hilfsfunktionen — ~80 Zeilen
```

**Zeilenschätzungen basieren auf:**
- `core.lua`: IST-Zeilen 277–3034 = ~2757 Zeilen (verifiziert via Model Kap. 1.3)
- `keybindings/`: IST-Zeilen 3036–4539 = ~1503 Zeilen, aufgeteilt auf 6 Module
- `platform.lua` + `project.lua`: IST-Zeilen 194–268 = 75 Zeilen + Extraktion aus Plugins

**Was ist NICHT in `shared/core.lua`:**
- Platform-Detection (→ `platform.lua`)
- Projekt-Detection (→ `project.lua`)
- Projekt-spezifische Terminal-Keybindings (→ `keybindings/`)

**Was bleibt in `core.lua` trotz platform-spezifischem Inhalt:**
- Obsidian Workspace-Pfade (Zeilen 745–754): Inline `vim.fn.has('win32')` bleiben, da Plugin-opts lazy evaluiert werden — kein separates Modul nötig
- DAP `.exe`-Suffix (Zeile 1477): Bleibt inline als `if platform.is_windows then`
- LuaSnip build (Zeile 2788): Bleibt inline als `if platform.is_windows then`
- Markdown-Preview Chrome-Pfad (Zeilen 680–694): Wird `platform.chrome_path` verwenden

---

## 3. Modul-APIs (konkret mit Lua-Code)

### 3.1 lua/shared/platform.lua

```lua
-- lua/shared/platform.lua
-- Plattform-Erkennung und systemabhängige Konstanten.
-- Keine Neovim-State-Abhängigkeiten außer vim.fn.has (sicher bei module load time).

local M = {}

-- Plattform-Flag: true auf Windows Neovim, false auf WSL2/Linux Neovim
M.is_windows = vim.fn.has('win32') == 1

-- Chrome executable path (für Markdown-Preview und URL-öffnen)
-- Verifiziert: Zeilen 680–694 (Markdown Preview) und 858–863 (Obsidian Follow Link)
M.chrome_path = M.is_windows
  and 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  or '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'

-- Chrome-Aufruf als Shell-Kommando (inkl. Anführungszeichen für Leerzeichen im Pfad)
M.chrome_cmd = M.is_windows
  and '"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"'
  or '"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"'

-- URL in System-Browser öffnen
-- Verifiziert: Zeilen 858–863 (Obsidian), 934 (Graph View), 4436 (TFS)
---@param url string
function M.open_url(url)
  if M.is_windows then
    vim.fn.system('powershell.exe -Command "Start-Process \'' .. url .. '\'"')
  else
    vim.fn.system('xdg-open "' .. url .. '"')
  end
end

-- Pfad-Utility: Forward-Slashes → Backslashes (für PowerShell-Aufrufe)
---@param path string
---@return string
function M.to_windows_path(path)
  return path:gsub('/', '\\')
end

-- Pfad-Utility: WSL-Pfad → Windows-Pfad
-- /mnt/c/foo → C:\foo
-- Hinweis: Nur nötig wenn path von WSL stammt (z.B. project_root_wsl → windows)
---@param wsl_path string
---@return string
function M.wsl_to_windows(wsl_path)
  return wsl_path:gsub('^/mnt/(%a)/', function(drive)
    return drive:upper() .. ':\\'
  end):gsub('/', '\\')
end

return M
```

### 3.2 lua/shared/project.lua

```lua
-- lua/shared/project.lua
-- Projekt-Erkennung (CENCOCD / DCSRE / UNKNOWN) und Setzen von vim.g.project_*
-- Basiert auf IST-Code Zeilen 202–268 (verifiziert via Spot-Check)

local M = {}
local platform = require('shared.platform')

-- Findet den DCSRE-Root-Ordner ausgehend von einem Pfad.
-- Sucht aufwärts nach einem Ordner der "Sources" enthält.
-- Verifiziert: init.lua Zeilen 203–227
---@param path string  Startpfad (z.B. cwd), Forward- oder Backslash
---@return string|nil  Normalisierter Pfad (Forward-Slashes) oder nil
function M.find_dcsre_root(path)
  path = path:gsub('\\', '/')

  -- Strategie 1: Pattern-Match auf .../DCSRE.../Sources/...
  local root = path:match('(.*/DCSRE[^/]*)/Sources')
  if root and vim.fn.isdirectory(root .. '/Sources') == 1 then
    return root
  end

  -- Strategie 2: Aufwärts suchen
  local check_path = path
  while check_path and #check_path > 3 do
    if vim.fn.isdirectory(check_path .. '/Sources') == 1 then
      return check_path
    end
    local nested = check_path .. '/DCSRE'
    if vim.fn.isdirectory(nested .. '/Sources') == 1 then
      return nested
    end
    check_path = check_path:match('(.+)/[^/]+$')
  end
  return nil
end

-- Erkennt das aktuelle Projekt und setzt alle vim.g.project_* Globals.
-- Muss VOR lazy.setup() aufgerufen werden!
-- Verifiziert: init.lua Zeilen 229–268
function M.detect()
  local cwd = vim.fn.getcwd()
  vim.g.project_name = 'UNKNOWN'

  if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
    -- CENCOCD Projekt
    vim.g.project_name = 'CENCOCD'
    local base = platform.is_windows
      and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco'
      or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco'
    vim.g.project_backend         = base .. '/src/Core/CenCoCo.Core.API'
    vim.g.project_frontend        = base .. '/src/Core/CenCoCo.Core.Blazor'
    vim.g.project_webhost         = base .. '/src/Core/CenCoCo.Core.API'
    vim.g.project_docker_root     = base .. '/src'
    vim.g.project_docker_root_windows = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco\\src'
    vim.g.project_git_base        = 'origin/main'
    vim.g.project_launch_profile  = 'https'
    vim.g.project_root_windows    = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco'
    vim.g.project_root_wsl        = '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco'
    vim.g.project_tfs_commit_url  = nil
    vim.g.project_pr_url          = nil

  elseif cwd:match('DCSRE') then
    -- DCSRE Projekt — Root dynamisch finden
    local dcsre_root = M.find_dcsre_root(cwd)
    if dcsre_root then
      vim.g.project_name            = 'DCSRE'
      vim.g.project_backend         = dcsre_root .. '/Sources/Backend'
      vim.g.project_backend_windows = platform.to_windows_path(dcsre_root) .. '\\Sources\\Backend'
      vim.g.project_frontend        = dcsre_root .. '/Sources/Frontend'
      vim.g.project_webhost         = dcsre_root .. '/Sources/Backend/VDEK.DCSP.WebHost'
      vim.g.project_docker_root     = dcsre_root .. '/Sources'
      vim.g.project_docker_root_windows = platform.to_windows_path(dcsre_root) .. '\\Sources'
      vim.g.project_git_base        = 'origin/develop'
      vim.g.project_launch_profile  = 'WebHost'
      vim.g.project_root_windows    = platform.to_windows_path(dcsre_root)
      vim.g.project_root_wsl        = dcsre_root:gsub('C:', '/mnt/c')
      vim.g.project_tfs_commit_url  = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/commit/%s'
      vim.g.project_pr_url          = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/pullrequest/%s?path=%s'
    end
  end
end

return M
```

**Rückgabewert von `M.detect()`**: kein Rückgabewert — setzt vim.g.* als Side-Effect.
Das ist bewusst, da `vim.g.*` der Kommunikationskanal zu allen nachfolgenden Modulen ist.

### 3.3 lua/shared/core.lua (Struktur-Übersicht)

`core.lua` wird nicht als API-Modul konzipiert, sondern als Side-Effect-Datei (wird via `require` oder `dofile` ausgeführt und registriert alles in Neovim).

```lua
-- lua/shared/core.lua
-- Enthält: vim.opt Settings, Standard-Keymaps, Lazy-Bootstrap, alle Plugin-Definitionen.
-- Voraussetzungen (müssen VOR require('shared.core') stehen):
--   - require('shared.platform') wurde ausgeführt (für is_windows in Plugin-Specs)
--   - require('shared.project').detect() wurde aufgerufen (für vim.g.project_*)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Lokale Variable für Closure-Zugriff in Plugin-Specs

-- [[ Vim-Optionen ]] (IST: Zeilen 277–354)
vim.opt.number = true
-- ... alle vim.opt.* Settings ...

-- [[ Standard-Keymaps + Autocommands ]] (IST: Zeilen 356–432)
vim.keymap.set('n', '<Esc>', '<cmd>nohlsearch<CR>')
-- ...

-- [[ Lazy.nvim Bootstrap ]] (IST: Zeilen 434–447)
local lazypath = vim.fn.stdpath 'data' .. '/lazy/lazy.nvim'
-- ...
vim.opt.rtp:prepend(lazypath)

-- [[ Plugin-Definitionen ]] (IST: Zeilen 449–3034)
require('lazy').setup({
  -- Alle Plugins mit ihren opts ...
  -- is_windows verfügbar als lokale Variable (Closure)
  -- vim.g.project_* verfügbar als globale Variablen
}, {})
```

### 3.4 Keybinding-Modul-Struktur (exemplarisch backend.lua)

```lua
-- lua/shared/keybindings/backend.lua
-- Backend-Keybindings: <leader>rb* Commands
-- Abhängigkeiten: vim.g.project_*, require('shared.platform')

local platform = require('shared.platform')

-- <leader>rbw — Run Backend WebHost
vim.keymap.set('n', '<leader>rbw', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    if platform.is_windows then
      cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; dotnet run --launch-profile https"'
    else
      cmd = 'cd ' .. vim.g.project_webhost .. ' && dotnet run --launch-profile https'
    end
  else
    if platform.is_windows then
      cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; ...'
    else
      cmd = 'cd ' .. vim.g.project_webhost .. ' && ASPNETCORE_URLS=... dotnet run --no-restore'
    end
  end
  -- ... Terminal:new(...):toggle() ...
end, { desc = '[R]un [B]ackend [W]ebhost' })

-- ... weitere <leader>rb* Keybindings ...
```

---

## 4. Dispatcher init.lua (finaler Code)

### 4.1 Variante: Simpler Dispatcher (ohne init_windows/init_linux)

```lua
-- init.lua  (Dispatcher) — ~15 Zeilen
-- Lade-Reihenfolge ist kritisch: platform → project → core → keybindings

-- 1. Plattform-Konstanten (keine Deps)
local platform = require('shared.platform')

-- 2. Projekt erkennen und vim.g.project_* setzen (dep: platform)
require('shared.project').detect()

-- 3. Kern-Konfiguration (Plugins, LSP, vim.opt — dep: platform + vim.g.project_*)
require('shared.core')

-- 4. Projekt-Keybindings (dep: platform + vim.g.project_* + core/toggleterm)
require('shared.keybindings.backend')
require('shared.keybindings.frontend')
require('shared.keybindings.git')
require('shared.keybindings.docker')
require('shared.keybindings.tests')
require('shared.keybindings.clipboard')

-- vim: ts=2 sts=2 sw=2 et
```

### 4.2 Variante: Mit init_windows.lua / init_linux.lua (Task.md-konform)

**init.lua (Dispatcher):**
```lua
-- init.lua  — Wählt den plattformspezifischen Entry-Point
if vim.fn.has('win32') == 1 then
  require('init_windows')
else
  require('init_linux')
end
```

**init_windows.lua:**
```lua
-- init_windows.lua  — Windows-Native Entry-Point
-- Für: Windows Neovim (C:\Users\...\AppData\Local\nvim\)

local platform = require('shared.platform')
assert(platform.is_windows, 'init_windows.lua wurde auf nicht-Windows geladen!')

require('shared.project').detect()
require('shared.core')

-- Windows-spezifische Overrides (falls nötig)
-- z.B.: PowerShell-spezifische Keybindings die es auf Linux nicht gibt

require('shared.keybindings.backend')
require('shared.keybindings.frontend')
require('shared.keybindings.git')
require('shared.keybindings.docker')
require('shared.keybindings.tests')
require('shared.keybindings.clipboard')
```

**init_linux.lua:**
```lua
-- init_linux.lua  — WSL2/Linux Entry-Point
-- Für: Neovim in WSL2 (~/.config/nvim/)

local platform = require('shared.platform')
assert(not platform.is_windows, 'init_linux.lua wurde auf Windows geladen!')

require('shared.project').detect()
require('shared.core')

require('shared.keybindings.backend')
require('shared.keybindings.frontend')
require('shared.keybindings.git')
require('shared.keybindings.docker')
require('shared.keybindings.tests')
require('shared.keybindings.clipboard')
```

### 4.3 `vim.cmd('source')` vs `require()` für den Dispatcher

**`require()`** ist die idiomatischere Lua-Lösung:
- Caching: Neovim cached `require()` Aufrufe — kein doppeltes Laden
- Saubere Fehler: Stack-Trace zeigt welches Modul fehlschlug
- Standardkonvention: Alle anderen Neovim-Plugins nutzen `require()`

**`vim.cmd('source')`** würde funktionieren, hat aber Nachteile:
- Kein Caching
- Pfad-Angabe als String (fehleranfällig auf Windows vs. Unix)
- Vermischt Vimscript mit Lua-Konzepten

**Empfehlung: `require()` für alle Modul-Ladevorgänge.**

**Wichtiger Hinweis zur Deployment-Situation:**
`require('shared.platform')` setzt voraus, dass `lua/shared/` im Neovim `runtimepath` liegt. Bei der aktuellen Deploy-Methode (Copy von init.lua nach `AppData\Local\nvim\`) muss sichergestellt werden, dass auch `lua/shared/` mitkopiert wird:

```powershell
# Windows: Deployment-Skript (zu ergänzen in CLAUDE.md)
Copy-Item -Recurse -Force 'C:\...\KickStartNeoVim\lua' 'C:\Users\Administrator\AppData\Local\nvim\lua'
Copy-Item -Force 'C:\...\KickStartNeoVim\init.lua' 'C:\Users\Administrator\AppData\Local\nvim\init.lua'
```

```bash
# WSL2: Deployment-Skript
cp -r /path/to/KickStartNeoVim/lua ~/.config/nvim/lua
cp /path/to/KickStartNeoVim/init.lua ~/.config/nvim/init.lua
```

---

## 5. Test-Spezifikation

### 5.1 Verzeichnis-Struktur

```
KickStartNeoVim/
└── lua/
    └── spec/
        ├── project_spec.lua    # Tests für shared/project.lua
        └── platform_spec.lua   # Tests für shared/platform.lua
```

### 5.2 Test-Runner Command

```bash
nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"
```

**Dependency**: plenary.nvim (bereits als Plugin in init.lua vorhanden, Zeile ca. 2925 via mini.nvim oder direkt).

### 5.3 Was gemockt werden muss

| Funktion | Warum | Wie |
|----------|-------|-----|
| `vim.fn.isdirectory` | `find_dcsre_root` ruft sie auf | `vim.fn.isdirectory = function(p) return mock_dirs[p] and 1 or 0 end` |
| `vim.fn.getcwd` | Projekt-Detection liest cwd | `vim.fn.getcwd = function() return '/fake/DCSRE/Sources' end` |
| `vim.fn.has` | Platform-Detection | `vim.fn.has = function(what) return what == 'win32' and 1 or 0 end` |

**Wichtig**: Mocks müssen nach jedem Test-Block restored werden (Lua hat kein automatisches Mock-Reset).

### 5.4 lua/spec/project_spec.lua (vollständige Spec)

```lua
-- lua/spec/project_spec.lua
local project = require('shared.project')

-- Hilfsfunktion: vim.fn.isdirectory mock
local function mock_dirs(dirs)
  local orig = vim.fn.isdirectory
  vim.fn.isdirectory = function(p) return dirs[p] and 1 or 0 end
  return function() vim.fn.isdirectory = orig end  -- cleanup
end

describe('find_dcsre_root', function()
  it('extrahiert Root aus .../DCSRE/Sources/Backend', function()
    local cleanup = mock_dirs({ ['/work/DCSRE/Sources'] = true })
    local result = project.find_dcsre_root('/work/DCSRE/Sources/Backend/MyProject')
    assert.are.equal('/work/DCSRE', result)
    cleanup()
  end)

  it('behandelt DCSRE_Azure/DCSRE/Sources Verschachtelung', function()
    local cleanup = mock_dirs({ ['/work/DCSRE_Azure/DCSRE/Sources'] = true })
    local result = project.find_dcsre_root('/work/DCSRE_Azure/DCSRE/Sources/Backend')
    assert.are.equal('/work/DCSRE_Azure/DCSRE', result)
    cleanup()
  end)

  it('gibt nil zurück wenn kein Sources-Ordner gefunden', function()
    local cleanup = mock_dirs({})
    local result = project.find_dcsre_root('/work/SomethingElse/foo')
    assert.is_nil(result)
    cleanup()
  end)

  it('sucht aufwärts durch verschachtelte Verzeichnisse', function()
    local cleanup = mock_dirs({ ['/work/DCSRE/Sources'] = true })
    local result = project.find_dcsre_root('/work/DCSRE/Sources/Backend/A/B/C/D')
    assert.are.equal('/work/DCSRE', result)
    cleanup()
  end)

  it('normalisiert Windows-Backslash-Pfade korrekt', function()
    local cleanup = mock_dirs({ ['C:/Users/work/DCSRE/Sources'] = true })
    local result = project.find_dcsre_root('C:\\Users\\work\\DCSRE\\Sources\\Backend')
    assert.are.equal('C:/Users/work/DCSRE', result)
    cleanup()
  end)
end)

describe('project detection', function()
  local orig_getcwd = vim.fn.getcwd

  after_each(function()
    vim.fn.getcwd = orig_getcwd
    vim.g.project_name = 'UNKNOWN'
  end)

  it('erkennt CENCOCD aus "Kluger" im cwd', function()
    vim.fn.getcwd = function() return '/home/user/Kluger/cencoco/src' end
    project.detect()
    assert.are.equal('CENCOCD', vim.g.project_name)
  end)

  it('erkennt CENCOCD aus "cencoco" im cwd', function()
    vim.fn.getcwd = function() return '/home/user/projects/cencoco/src' end
    project.detect()
    assert.are.equal('CENCOCD', vim.g.project_name)
  end)

  it('erkennt CENCOCD aus "CENCOCD" im cwd', function()
    vim.fn.getcwd = function() return 'C:/Work/CENCOCD/src' end
    project.detect()
    assert.are.equal('CENCOCD', vim.g.project_name)
  end)

  it('erkennt DCSRE aus "DCSRE" im cwd', function()
    local cleanup = mock_dirs({ ['/work/DCSRE/Sources'] = true })
    vim.fn.getcwd = function() return '/work/DCSRE/Sources/Backend' end
    project.detect()
    assert.are.equal('DCSRE', vim.g.project_name)
    cleanup()
  end)

  it('setzt UNKNOWN wenn kein Projekt erkannt', function()
    vim.fn.getcwd = function() return '/home/user/SomethingElse' end
    project.detect()
    assert.are.equal('UNKNOWN', vim.g.project_name)
  end)

  it('setzt korrektes project_git_base für CENCOCD', function()
    vim.fn.getcwd = function() return '/work/Kluger/cencoco' end
    project.detect()
    assert.are.equal('origin/main', vim.g.project_git_base)
  end)

  it('setzt korrektes project_git_base für DCSRE', function()
    local cleanup = mock_dirs({ ['/work/DCSRE/Sources'] = true })
    vim.fn.getcwd = function() return '/work/DCSRE/Sources/Backend' end
    project.detect()
    assert.are.equal('origin/develop', vim.g.project_git_base)
    cleanup()
  end)
end)
```

### 5.5 lua/spec/platform_spec.lua (vollständige Spec)

```lua
-- lua/spec/platform_spec.lua

describe('path conversions', function()
  -- Diese Tests brauchen KEIN Mock (reine String-Operationen)
  local platform = require('shared.platform')

  it('to_windows_path: Forward-Slash → Backslash', function()
    assert.are.equal('C:\\Users\\foo\\bar', platform.to_windows_path('C:/Users/foo/bar'))
  end)

  it('wsl_to_windows: /mnt/c/ → C:\\', function()
    assert.are.equal('C:\\Users\\foo', platform.wsl_to_windows('/mnt/c/Users/foo'))
  end)

  it('wsl_to_windows: /mnt/d/ → D:\\', function()
    assert.are.equal('D:\\Work\\project', platform.wsl_to_windows('/mnt/d/Work/project'))
  end)
end)

describe('platform detection', function()
  -- Achtung: is_windows wird bei module load evaluiert!
  -- Diese Tests prüfen nur, dass der Wert konsistent mit vim.fn.has ist.
  local platform = require('shared.platform')

  it('is_windows entspricht vim.fn.has("win32")', function()
    local expected = vim.fn.has('win32') == 1
    assert.are.equal(expected, platform.is_windows)
  end)
end)
```

**Hinweis zu `is_windows` Tests**: Da Lua-Module gecacht werden und `is_windows` bei `require()` evaluiert wird, kann man `platform.is_windows` nicht zur Laufzeit per Mock ändern. Die Tests oben validieren daher nur Konsistenz, nicht Windows/Linux-Simulation. Für Cross-Platform-Tests der Projekt-Detection ist das `vim.fn.getcwd` Mock ausreichend.

---

## 6. Migrations-Plan (validierte Reihenfolge)

### Schritt 0: Vorbereitung

```bash
# Im KickStartNeoVim Repository:
mkdir -p lua/shared/keybindings
mkdir -p lua/spec
```

Smoke-Test hinzufügen (wird in jedem Schritt als Baseline verwendet):
- Neovim startet ohne Fehler: `nvim --headless +q`
- Alle Plugins laden: `:Lazy` zeigt kein "Error"
- Welcome-Message erscheint beim Start

### Schritt 1: lua/shared/platform.lua anlegen

**Quell-Zeilen**: 680–694 (Chrome-Pfad), 858–863 (open_url), 934 (xdg-open vs start)
**Aktion**:
1. `lua/shared/platform.lua` anlegen (Code aus Abschnitt 3.1)
2. `init.lua`: Zeile 200 ersetzen durch `local platform = require('shared.platform'); local is_windows = platform.is_windows`
3. Smoke-Test: Neovim startet, `is_windows` wird korrekt gesetzt

**Risiko**: Gering — `platform.lua` hat keine Neovim-State-Abhängigkeiten.

### Schritt 2: lua/shared/project.lua anlegen

**Quell-Zeilen**: 202–268 (inkl. `find_dcsre_root`)
**Aktion**:
1. `lua/shared/project.lua` anlegen (Code aus Abschnitt 3.2)
2. In `init.lua`: Zeilen 202–268 durch `require('shared.project').detect()` ersetzen
3. Tests schreiben: `lua/spec/project_spec.lua` (Spec aus Abschnitt 5.4)
4. Tests ausführen: `nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"`
5. Smoke-Test: Neovim in DCSRE-Verzeichnis öffnen, Welcome-Message: "Welcome to DCSRE!"

**Risiko**: Mittel — `vim.g.project_*` muss vor `lazy.setup()` gesetzt sein. Sicherstellung: `project.detect()` steht VOR `require('shared.core')`.

### Schritt 3: lua/shared/core.lua anlegen

**Quell-Zeilen**: 113–164 (Auto-Copy), 270–3034 (vim.opt, Keymaps, Lazy, Plugins)
**Aktion**:
1. `lua/shared/core.lua` anlegen — Zeilen 113–3034 hineinkopieren
2. Am Anfang von `core.lua`: `local platform = require('shared.platform'); local is_windows = platform.is_windows` einfügen
3. In `init.lua`: Zeilen 113–3034 durch `require('shared.core')` ersetzen
4. Smoke-Test: `:Lazy` funktioniert, `:LspInfo` zeigt OmniSharp, alle Plugins geladen

**Risiko**: Hoch (größter Schritt) — Bootstrapping-Reihenfolge kritisch:
- `core.lua` enthält `vim.opt.rtp:prepend(lazypath)` (IST: Zeile 447) — MUSS vor `require('lazy').setup()` stehen
- `is_windows` muss als lokale Variable in `core.lua` definiert sein, BEVOR `lazy.setup({...})` ausgeführt wird

### Schritt 4: Keybinding-Module extrahieren (sequenziell, ein Modul pro Iteration)

**Quell-Zeilen**: 3036–4539
**Reihenfolge** (von "geringstem Risiko" zu "höchstem"):
1. `clipboard.lua` (~80 LOC, keine Terminal-Commands, rein deklarativ)
2. `git.lua` (~120 LOC, Neogit + Diffview, PowerShell-Commands für Push/Pull)
3. `frontend.lua` (~80 LOC, PowerShell-only Commands)
4. `backend.lua` (~180 LOC, WIN+WSL-Branch in rbw, sonst PowerShell-only)
5. `docker.lua` (~140 LOC, komplexe PowerShell-Scripts)
6. `tests.lua` (~200 LOC, `set_xunit_threads` + `write_it_script` Helper-Funktionen)

**Nach jedem Modul**:
1. Entsprechende Zeilen aus `init.lua` entfernen
2. `require('shared.keybindings.MODUL')` am Ende von `init.lua` hinzufügen
3. Alle betroffenen `<leader>?*` Keybindings manuell testen

### Schritt 5: Dispatcher init.lua fertigstellen

**Aktion**: `init.lua` enthält jetzt nur noch den Dispatcher-Code (Abschnitt 4.1 oder 4.2).

**Entscheidung (an User zu klären)**: Brauchen wir `init_windows.lua` + `init_linux.lua`?
- **Ja**: Schritt 5b ausführen (Entry-Points anlegen, Dispatcher auf require('init_windows/linux') umstellen)
- **Nein**: Dispatcher bleibt als einfaches `init.lua` (Abschnitt 4.1)

### Schritt 6: Tests finalisieren + Deployment-Skript aktualisieren

1. `lua/spec/platform_spec.lua` fertigschreiben (Spec aus Abschnitt 5.5)
2. CLAUDE.md aktualisieren: Deploy-Schritte erweitern um `lua/shared/` Copy
3. End-to-End Test: Frische WSL2-Instanz, DCSRE-Verzeichnis, alle `<leader>r*` Keybindings prüfen

---

## 7. Bug-Dokumentation

### Bug B-001: project_root_windows auf WSL2 (DCSRE)

**Fundstelle**: `init.lua` Zeile 259 [Spot-Check verifiziert]
```lua
vim.g.project_root_windows = dcsre_root:gsub('/', '\\')
```

**Was passiert auf WSL2:**
- `cwd` auf WSL2: `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend`
- `find_dcsre_root(cwd)` normalisiert zu Forward-Slashes und gibt zurück: `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE`
- `dcsre_root:gsub('/', '\\')` → `\mnt\c\Users\Administrator\Documents\Work\Code2\DCSRE`
- **Das ist ein ungültiger Windows-Pfad!** PowerShell erwartet `C:\Users\...` nicht `\mnt\c\...`

**Was passiert auf Windows:**
- `cwd` auf Windows: `C:\Users\Administrator\Documents\Work\Code2\DCSRE\Sources\Backend`
- `find_dcsre_root(cwd)` normalisiert zu: `C:/Users/Administrator/Documents/Work/Code2/DCSRE`
- `dcsre_root:gsub('/', '\\')` → `C:\Users\Administrator\Documents\Work\Code2\DCSRE`
- **Korrekt!**

**Warum funktioniert es trotzdem auf WSL2?**
`project_root_wsl` (Zeile 260) wird korrekt gesetzt. Viele Keybindings die von WSL2 aus aufgerufen werden, nutzen `vim.g.project_backend` (Forward-Slashes) statt `project_root_windows`. Die Git-Keybindings (`<leader>rp`, `<leader>rP`) nutzen `project_root_windows` direkt — dort ist der Bug sichtbar wenn von WSL2 aus git push aufgerufen wird.

**Fix für project.lua (Schritt 2 des Migrations-Plans):**
```lua
-- Korrekte Implementierung in shared/project.lua:
if platform.is_windows then
  -- Windows: dcsre_root ist bereits "C:/..." → gsub('/', '\\') korrekt
  vim.g.project_root_windows = platform.to_windows_path(dcsre_root)
else
  -- WSL2: dcsre_root ist "/mnt/c/..." → erst zu Windows-Pfad konvertieren
  vim.g.project_root_windows = platform.wsl_to_windows(dcsre_root)
end
```

**Impact**: Niedrig im IST-Zustand (Git Push/Pull auf WSL2 via PowerShell schlägt fehl), wird beim Refactoring automatisch gefixt.

---

## 8. Akzeptanzkriterien

Diese Kriterien entsprechen direkt der Task.md und sind konkret prüfbar:

```
Funktionalität
☐ AC-01: Windows Neovim startet ohne Fehler mit neuer Dateistruktur
          Test: nvim --headless +q auf Windows, Exit-Code = 0
☐ AC-02: WSL2 Neovim startet ohne Fehler mit neuer Dateistruktur
          Test: nvim --headless +q auf WSL2, Exit-Code = 0
☐ AC-03: Projekt-Detection funktioniert auf beiden Plattformen
          Test: In DCSRE-Verzeichnis öffnen → Welcome-Message: "Welcome to DCSRE!"
☐ AC-04: Projekt-Detection CENCOCD funktioniert
          Test: In Kluger/cencoco öffnen → "Welcome to CENCOCD!"

Tests
☐ AC-05: Alle plenary-Tests laufen durch (keine Failures):
          nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"
☐ AC-06: find_dcsre_root Tests: min. 5 Cases (Standard, Nested, nil, Tief, Backslash)
☐ AC-07: Projekt-Detection Tests: min. 7 Cases (CENCOCD x3, DCSRE, UNKNOWN, git_base x2)

Keybindings
☐ AC-08: <leader>rbw startet Backend-Server (DCSRE + CENCOCD, Windows + WSL2)
☐ AC-09: <leader>gg öffnet Neogit
☐ AC-10: <leader>rDi startet Docker-Infrastruktur (projekt-spezifisch)
☐ AC-11: <leader>rim führt Integration Tests aus

Plugins + LSP
☐ AC-12: :Lazy zeigt alle Plugins ohne Errors
☐ AC-13: :LspInfo zeigt omnisharp attached auf .cs Dateien
☐ AC-14: StyleCop Warnungen erscheinen inline

Kein Duplikat
☐ AC-15: shared Code (vim.opt, Plugin-Definitionen, LSP-Config) ist nur EINMAL vorhanden
          Prüfung: grep -r "vim.opt.number" lua/ → genau 1 Treffer

Deployment
☐ AC-16: Deployment-Anleitung in CLAUDE.md aktualisiert (lua/shared/ Copy-Schritt)
☐ AC-17: Bug B-001 (project_root_windows auf WSL2) ist gefixt
```

---

## 9. Offene Fragen (an User zu klären)

**F1**: Soll Schritt 5 (Variante 4.2) umgesetzt werden, also echte `init_windows.lua` + `init_linux.lua` Entry-Points?
- Task.md sagt explizit Ja
- Praktischer Nutzen: derzeit gering, da alle Keybindings Runtime-Branching per `platform.is_windows` machen

**F2**: Soll `old_settings/init_windows.lua` gelöscht werden um Verwirrung zu vermeiden?
- CLAUDE.md sagt: veraltet, nicht nutzen
- Empfehlung: Löschen nach erfolgreichem Migrations-Abschluss

**F3**: Soll Bug B-001 als separater Fix-Commit ODER als Teil des Refactorings gefixt werden?
- Empfehlung: Teil des Refactorings (Schritt 2 des Plans)

---

*Dokument-Ende*
