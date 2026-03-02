---
wave: exploration
agent: E04
focus: test-infrastructure
status: final
primaerquelle_gelesen: true
---

# E04: Test-Infrastruktur für KickStartNeoVim

## 1. plenary.nvim busted - Framework Basics

### Was ist plenary.nvim busted?

**plenary.nvim** implementiert ein Busted-kompatibles Test-Framework, das speziell für Neovim-Plugins optimiert ist. Im Gegensatz zu reinem Busted hat man Zugriff auf die `vim`-Namespace und kann so Tests schreiben, die auf Neovim-spezifische Funktionen zugreifen.

**Vorteile gegenüber standalone busted:**
- ✅ Zugriff auf `vim.*` Funktionen (vim.fn, vim.api, etc.)
- ✅ Tests laufen in echten Neovim-Instanzen (headless)
- ✅ Integriert mit luassert für mocks/stubs/spies
- ✅ Keine komplexen Setup-Prozeduren nötig

### Syntax-Grundlagen

```lua
-- Standard Test-Struktur
describe('Modul-Name', function()
  it('sollte X machen', function()
    assert.are.same(actual, expected)
  end)

  it('sollte Y werfen', function()
    assert.has.error(function()
      -- Code, der einen Fehler wirft
    end)
  end)
end)
```

### Assertions (luassert)

```lua
-- Gleichheit
assert.are.same(a, b)       -- a == b (strict)
assert.are.equal(a, b)      -- a == b
assert.is.truthy(value)     -- truthy check
assert.is.falsy(value)      -- falsy check

-- Fehlerbehandlung
assert.has.error(function() ... end)
assert.has.error(function() ... end, 'Error message')

-- Collections
assert.are.same({1,2,3}, {1,2,3})
assert.contains({1,2,3}, 1)
```

---

## 2. Test-Kandidaten aus init.lua

### Test 1: `find_dcsre_root()` (Zeilen 202-227)

**Implementierung:**
```lua
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
    -- Also check for nested DCSRE folder with Sources
    local nested = check_path .. '/DCSRE'
    if vim.fn.isdirectory(nested .. '/Sources') == 1 then
      return nested
    end
    check_path = check_path:match('(.+)/[^/]+$')
  end
  return nil
end
```

**Warum testbar?**
- ✅ Reine String-Funktion (Regex-Matching)
- ✅ Strategy 1 benötigt KEINE vim.fn Calls (nur String-Operations)
- ✅ Strategy 2 nutzt vim.fn.isdirectory() - **MOCKBAR** via luassert spies

**Test-Cases:**

```lua
describe('find_dcsre_root()', function()

  -- Strategy 1: Path Pattern Matching (KEIN Mock nötig!)
  it('extracts DCSRE root from path pattern /DCSRE/Sources/...', function()
    local input = '/mnt/c/work/DCSRE_Azure/DCSRE/Sources/Backend/Project'
    local result = find_dcsre_root(input)
    assert.are.same(result, '/mnt/c/work/DCSRE_Azure/DCSRE')
  end)

  it('normalizes Windows backslashes to forward slashes', function()
    local input = 'C:\\work\\DCSRE\\Sources\\Backend'
    local result = find_dcsre_root(input)
    -- Strategy 1 sollte matchen
    assert.are.same(result, 'C:/work/DCSRE')
  end)

  it('handles DCSRE with suffixes (DCSRE_Azure, DCSRE_Dev)', function()
    local input = '/work/DCSRE_Azure/Sources/Backend'
    local result = find_dcsre_root(input)
    assert.are.same(result, '/work/DCSRE_Azure')
  end)

  -- Rand-Fälle (ohne vim.fn.isdirectory Check)
  it('returns nil wenn kein DCSRE Pattern und zu kurzer Pfad', function()
    local input = '/a/b'
    local result = find_dcsre_root(input)
    -- Kann Strategy 1 nicht matchen, Strategy 2 findet keine Sources
    assert.is_nil(result)
  end)

  it('handles path mit nur DCSRE ohne Sources-Suffix', function()
    -- /DCSRE ohne /Sources davor
    local input = '/work/DCSRE/Backend'
    local result = find_dcsre_root(input)
    -- Pattern sollte NICHT matchen (braucht /Sources)
    assert.is_nil(result)
  end)

  -- Mit Mock: vim.fn.isdirectory
  it('[MOCK] finds DCSRE when searching upward', function()
    local spy_isdirectory = require('luassert').spy(vim.fn, 'isdirectory')

    -- Mock: /work/Sources existiert
    function vim.fn.isdirectory(path)
      return (path == '/work/Sources') and 1 or 0
    end

    local input = '/work/DCSRE/Backend/Project'
    local result = find_dcsre_root(input)
    assert.are.same(result, '/work')

    -- Cleanup
    vim.fn.isdirectory = original_isdirectory
  end)
end)
```

**Mock-Strategie:**
```lua
-- Vor Test:
local original_isdirectory = vim.fn.isdirectory

-- In Test:
function vim.fn.isdirectory(path)
  local mocked_dirs = {
    ['/mnt/c/work/DCSRE/Sources'] = 1,
    ['/mnt/c/work/DCSRE'] = 1,
  }
  return mocked_dirs[path] or 0
end

-- Nach Test:
vim.fn.isdirectory = original_isdirectory
```

---

### Test 2: Projekt-Detection Logic (Zeilen 229-268)

**Was wird getestet:**
- cwd-Pattern-Matching (Kluger → CENCOCD, DCSRE → DCSRE, sonst UNKNOWN)
- Dass die richtigen vim.g.* Variablen gesetzt werden
- Pfad-Konversionen (is_windows)

**Code:**
```lua
-- Detect project and set paths dynamically
vim.g.project_name = 'UNKNOWN'

if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
  vim.g.project_name = 'CENCOCD'
  vim.g.project_backend = is_windows and 'C:/Users/...' or '/mnt/c/Users/...'
  -- ... 6 weitere vim.g.* Variablen
elseif cwd:match('DCSRE') then
  local dcsre_root = find_dcsre_root(cwd)
  if dcsre_root then
    vim.g.project_name = 'DCSRE'
    vim.g.project_backend = dcsre_root .. '/Sources/Backend'
    -- ... weitere Variablen
  end
end
```

**Herausforderung:**
- ❌ Diese Logik manipuliert vim.g.* (globale Variablen)
- ❌ Sie ist in init.lua mit anderen Commands verflochten
- ✅ **ABER:** Kann in ein Modul `lua/utils/project.lua` extrahiert werden!

**Extrahierte Test-Struktur:**

```lua
-- lua/utils/project.lua (NEU - extrahiert)
local M = {}

function M.detect_project(cwd, is_windows)
  -- Rückgabe: {name, backend, frontend, ...}
  -- KEINE vim.g.* Manipulationen hier!

  if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
    return {
      name = 'CENCOCD',
      backend = is_windows and 'C:/Users/...' or '/mnt/c/Users/...',
      -- ...
    }
  elseif cwd:match('DCSRE') then
    -- ...
  end

  return { name = 'UNKNOWN' }
end

return M
```

**Test-Cases:**

```lua
describe('project.detect_project()', function()
  it('detects CENCOCD from cwd', function()
    local result = require('utils.project').detect_project(
      '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco',
      false  -- is_windows=false (WSL)
    )
    assert.are.same(result.name, 'CENCOCD')
    assert.are.same(result.backend:match('/mnt/c/'), '/mnt/c/')
  end)

  it('detects CENCOCD on Windows', function()
    local result = require('utils.project').detect_project(
      'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco',
      true  -- is_windows=true
    )
    assert.are.same(result.name, 'CENCOCD')
    assert.are.same(result.backend:match('^C:'), 'C:')
  end)

  it('detects DCSRE from cwd', function()
    local result = require('utils.project').detect_project(
      '/mnt/c/work/DCSRE/Sources',
      false
    )
    assert.are.same(result.name, 'DCSRE')
  end)

  it('returns UNKNOWN for unknown project', function()
    local result = require('utils.project').detect_project(
      '/mnt/c/some/random/path',
      false
    )
    assert.are.same(result.name, 'UNKNOWN')
  end)
end)
```

---

### Test 3: Pfad-Konversionen (String-Utils)

**Funktionen zum Extrahieren:**
```lua
-- Aus init.lua Zeilen 4257-4322 (Markdown PDF Export):
-- /mnt/c/Users/... → C:\Users\...
-- C:/ → C:/

-- Aus init.lua Zeilen 4524-4538 (.claude Setup):
-- WSL-zu-Windows-Konversion
```

**Extrahiertes Modul `lua/utils/path.lua`:**

```lua
local M = {}

function M.to_windows_path(wsl_path)
  -- /mnt/c/Users/... → C:\Users\...
  return wsl_path:gsub('^/mnt/(%a)/', function(drive)
    return drive:upper() .. ':'
  end):gsub('/', '\\')
end

function M.to_unix_path(windows_path)
  -- C:\Users\... → /mnt/c/Users/...
  return windows_path:gsub('^([A-Za-z]):', function(drive)
    return '/mnt/' .. drive:lower()
  end):gsub('\\', '/')
end

function M.normalize_path(path)
  -- Alle \ in / konvertieren
  return path:gsub('\\', '/')
end

return M
```

**Test-Cases:**

```lua
describe('path utils', function()
  local path = require('utils.path')

  it('converts WSL path to Windows path', function()
    local result = path.to_windows_path('/mnt/c/Users/Administrator/Documents')
    assert.are.same(result, 'C:\\Users\\Administrator\\Documents')
  end)

  it('converts Windows path to WSL path', function()
    local result = path.to_unix_path('C:\\Users\\Administrator\\Documents')
    assert.are.same(result, '/mnt/c/Users/Administrator/Documents')
  end)

  it('normalizes backslashes to forward slashes', function()
    local result = path.normalize_path('C:\\Users\\Administrator\\file.lua')
    assert.are.same(result, 'C:/Users/Administrator/file.lua')
  end)

  it('handles drive letter case (D: vs d:)', function()
    local result = path.to_unix_path('D:\\Data\\file.txt')
    assert.are.same(result, '/mnt/d/Data/file.txt')
  end)
end)
```

---

## 3. Was NICHT testbar ist

### ❌ Terminal-Commands (toggleterm)

Alle `<leader>r*` Keybindings mit `toggleterm.exec()`:
```lua
vim.fn.system('powershell.exe -Command "..."')
```
**Grund:** Benötigt echte Terminal/Process-Ausführung. Unit-Test unmöglich.

**Alternativ:**
- ✅ Command-String als Funktion extrahieren (testbar)
- ✅ Integration-Tests mit Mock-Shell (aufwändig)

### ❌ Plugin-Loading (lazy.nvim)

```lua
require('lazy').setup({...})
```
**Grund:** lazy.nvim lädt Plugins, das braucht komplexes Setup.

### ❌ VimEnter Autocmds

```lua
vim.api.nvim_create_autocmd('VimEnter', {
  callback = function()
    vim.notify('Welcome to ' .. vim.g.project_name .. '!')
  end,
})
```
**Grund:** Autocmds triggern bei echtem Neovim-Start, nicht in Unit-Tests.

### ❌ Keybindings mit komplexer Logik

```lua
vim.keymap.set('n', '<leader>mp', ...function...)
```
**Grund:** Braucht echte Neovim-UI zum Testen.

---

## 4. Test-Datei-Struktur

### Vorgeschlagene Ordner-Struktur

```
C:/Users/Administrator/Documents/Projekt/KickStartNeoVim/
├── lua/
│   ├── utils/
│   │   ├── project.lua      (NEUE: Projekt-Detection Logic)
│   │   ├── path.lua         (NEUE: Pfad-Konversionen)
│   │   └── commands.lua     (OPTIONAL: Command-Builder)
│   └── spec/
│       ├── utils/
│       │   ├── project_spec.lua
│       │   ├── path_spec.lua
│       │   └── commands_spec.lua
│       └── integration/
│           ├── init_spec.lua    (OPTIONAL: Init-Globale testen)
│           └── keybindings_spec.lua  (OPTIONAL: Keybinding-Syntax validieren)
├── .busted              (Busted-Konfiguration)
├── init.lua             (Hauptconfig - referenziert lua/utils/*)
└── .claude/analysis/
    └── exploration/
        └── KickStartNeoVim-E04-test-infrastructure.md (DIESE DATEI)
```

### .busted Konfiguration

```lua
-- .busted
return {
  _all = {
    busted = 'lua',
    ffi = true,
    exclude = { '.*lua/lazy/.*' },  -- Lazy plugins ausschließen
  },
  default = {
    verbose = true,
    sequential = false,
  },
  headless = {
    verbose = false,
    sequential = true,
  },
}
```

### package.path Setup (in spec-Dateien)

```lua
-- lua/spec/utils/project_spec.lua
local plenary_path = require('plenary.path')
package.path = package.path .. ';' .. plenary_path:new(vim.fn.stdpath('config')):joinpath('lua', '?.lua'):absolute()

local project = require('utils.project')
```

---

## 5. Test-Runner Commands

### Einzelne Test-Datei

```bash
# Aus Neovim:
:PlenaryTestFile lua/spec/utils/project_spec.lua

# Headless (automatisiert):
nvim --headless -c "PlenaryTestFile lua/spec/utils/project_spec.lua" -c "q"
```

### Ganzes Test-Verzeichnis

```bash
# Headless, sequenziell (für CI/CD):
nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"

# Parallel (schneller):
nvim --headless -c "PlenaryBustedDirectory lua/spec/" -c "q"
```

### In init.lua (Keybinding hinzufügen)

```lua
vim.keymap.set('n', '<leader>tt', function()
  require('plenary.test_harness').test_directory('lua/spec/', {sequential=true})
end, { desc = '[T]est all [T]ests' })

vim.keymap.set('n', '<leader>tf', function()
  require('plenary.test_harness').test_file(vim.fn.expand('%'))
end, { desc = '[T]est [F]ile (current)' })
```

---

## 6. Kritische Herausforderungen

### Challenge 1: vim.fn.isdirectory() Mocking

**Problem:**
- `find_dcsre_root()` nutzt `vim.fn.isdirectory()`
- Auf Test-Maschine müssen Test-Verzeichnisse NOT existieren

**Lösung: Spy + Mock**
```lua
-- Vor Test speichern
local original_isdirectory = vim.fn.isdirectory

-- Im Test
vim.fn.isdirectory = function(path)
  local mock_dirs = {
    ['/test/DCSRE/Sources'] = 1,
    ['/test/Sources'] = 1,
  }
  return mock_dirs[path] or 0
end

-- Nach Test wiederherstellen
vim.fn.isdirectory = original_isdirectory
```

### Challenge 2: Globale vim.g Variablen in init.lua

**Problem:**
- init.lua setzt vim.g.project_name direkt in top-level
- Tests können diese nicht isolieren
- init.lua wird beim Test-Start geladen

**Lösung: Separation of Concerns**
1. Verschiebe Detection-Logik in `lua/utils/project.lua`
2. init.lua wird zu:
   ```lua
   local project = require('utils.project')
   local config = project.detect_project(vim.fn.getcwd(), vim.fn.has('win32') == 1)
   vim.g.project_name = config.name
   vim.g.project_backend = config.backend
   -- ...
   ```
3. Jetzt ist `project.lua` pure, testbar

### Challenge 3: Test-Performance

**Problem:**
- Jeder Test startet eine neue Neovim-Instanz (langsam)
- 50+ Tests = mehrere Sekunden

**Lösungen:**
1. **Unit-Tests klein halten** → 10-20 Pro Test-Datei
2. **Sequenzielle Ausführung** nur für CI → In Entwicklung parallel
3. **Mocks nutzen** statt echte vim.fn Calls

---

## 7. Praktisches Beispiel: Erste Test-Datei

### Modul: lua/utils/project.lua

```lua
local M = {}

function M.detect_project(cwd, is_windows)
  -- Pure function: Input → Output
  -- KEINE vim.g.* Manipulationen!

  if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
    return {
      name = 'CENCOCD',
      backend = is_windows
        and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API'
        or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API',
      git_base = 'origin/main',
    }
  elseif cwd:match('DCSRE') then
    -- find_dcsre_root wird hier verwendet
    return {
      name = 'DCSRE',
      backend = '...',
      git_base = 'origin/develop',
    }
  end

  return { name = 'UNKNOWN' }
end

return M
```

### Test: lua/spec/utils/project_spec.lua

```lua
describe('project.detect_project()', function()
  local project = require('utils.project')

  it('detects CENCOCD on WSL', function()
    local result = project.detect_project(
      '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco',
      false
    )
    assert.are.same(result.name, 'CENCOCD')
    assert.is_true(result.backend:match('^/mnt/c/') ~= nil)
  end)

  it('detects CENCOCD on Windows', function()
    local result = project.detect_project(
      'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco',
      true
    )
    assert.are.same(result.name, 'CENCOCD')
    assert.is_true(result.backend:match('^C:') ~= nil)
  end)

  it('detects DCSRE', function()
    local result = project.detect_project(
      '/mnt/c/work/DCSRE/Sources/Backend',
      false
    )
    assert.are.same(result.name, 'DCSRE')
    assert.are.same(result.git_base, 'origin/develop')
  end)

  it('returns UNKNOWN for random paths', function()
    local result = project.detect_project('/random/path', false)
    assert.are.same(result.name, 'UNKNOWN')
  end)
end)
```

---

## 8. Implementation Roadmap

### Phase 1: Setup (Tag 1)
- [ ] .busted Konfiguration erstellen
- [ ] lua/utils/ Ordner erstellen
- [ ] lua/spec/ Ordner erstellen
- [ ] Erstes Test-Modul: `lua/utils/path.lua` + Tests

### Phase 2: Extraktion (Tag 2-3)
- [ ] `lua/utils/project.lua` extrahieren
- [ ] Tests für project-Detection schreiben
- [ ] `lua/utils/commands.lua` für Command-Strings

### Phase 3: Integration (Tag 4)
- [ ] init.lua anpassen (referenziert neue Modules)
- [ ] Tests im init.lua einbinden (Keybindings)
- [ ] CI/CD Pipeline (GitHub Actions?) aufsetzen

### Phase 4: Dokumentation (Tag 5)
- [ ] README in lua/spec/README.md
- [ ] Contributing Guide
- [ ] Test Coverage Report

---

## 9. Quellen & Referenzen

- [plenary.nvim GitHub](https://github.com/nvim-lua/plenary.nvim) - Test-Framework
- [plenary TESTS_README](https://github.com/nvim-lua/plenary.nvim/blob/master/TESTS_README.md) - Offizielle Dokumentation
- [Testing Neovim LSP Plugins](https://zignar.net/2022/10/26/testing-neovim-lsp-plugins/) - Praktisches Guide
- [mrcjkb.dev - Test Neovim with luarocks](https://mrcjkb.dev/posts/2023-06-06-luarocks-test.html) - Advanced Setup

---

## Zusammenfassung

**Testbar:**
- ✅ `find_dcsre_root()` - Pure String-Funktion
- ✅ Projekt-Detection - Kann extrahiert werden
- ✅ Pfad-Konversionen - Simple String-Operations
- ✅ Command-Builder - Pure Functions

**Nicht testbar:**
- ❌ Terminal-Execution
- ❌ Plugin-Loading
- ❌ Autocmd-Triggering
- ❌ Keybindings mit UI

**Framework:** plenary.nvim busted
**Test-Format:** lua/spec/*_spec.lua
**Runner:** `PlenaryBustedDirectory` / `PlenaryTestFile`

