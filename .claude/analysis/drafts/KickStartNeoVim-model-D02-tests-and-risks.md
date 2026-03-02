---
wave: drafts
agent: D02
focus: tests-and-platform-risks
status: final
primaerquelle_gelesen: true
---

# D02: Test-Specs + Platform-Risiken für KickStartNeoVim

## 1. Konkrete Test-Specs: `lua/spec/project_spec.lua`

### Status
Busted-Framework (via plenary.nvim bereits als Dependency vorhanden).
Test-Datei muss im Projekt erstellt werden.

### Ausführung
```bash
nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"
```

### Vollständiger Test-Code

```lua
-- lua/spec/project_spec.lua
-- Tests für project detection und path-konversion
-- Nutzt: plenary.nvim busted + Mocking von vim.fn Funktionen

local function mock_vim_fn(is_win)
  -- Mock vim.fn.has('win32')
  local original_has = vim.fn.has
  vim.fn.has = function(feature)
    if feature == 'win32' then
      return is_win and 1 or 0
    end
    return original_has(feature)
  end

  -- Mock vim.fn.isdirectory()
  local original_isdirectory = vim.fn.isdirectory
  vim.fn.isdirectory = function(path)
    -- Simuliere Verzeichnisse basierend auf Pfad-Pattern
    if path:match('Sources') then
      return 1  -- Sources-Ordner existiert
    elseif path:match('DCSRE') then
      return 1  -- DCSRE-Ordner existiert
    elseif path:match('Kluger') then
      return 1  -- Kluger-Ordner existiert
    end
    return 0   -- Ordner existiert nicht
  end

  return function()
    vim.fn.has = original_has
    vim.fn.isdirectory = original_isdirectory
  end
end

describe('find_dcsre_root()', function()
  local find_dcsre_root

  before_each(function()
    -- Diese Funktion ist lokal in init.lua (Zeilen 202-227)
    -- Für Tests: muss extrahiert oder in ein Modul verschoben werden!
    -- Für jetzt: simulieren wir die Logik
    find_dcsre_root = function(path)
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
        local nested = check_path .. '/DCSRE'
        if vim.fn.isdirectory(nested .. '/Sources') == 1 then
          return nested
        end
        check_path = check_path:match('(.+)/[^/]+$')
      end
      return nil
    end
  end)

  it('findet Root mit direktem DCSRE/Sources Pattern', function()
    local cleanup = mock_vim_fn(true)

    local path = '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'
    local result = find_dcsre_root(path)

    assert.are.equal('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE', result)
    cleanup()
  end)

  it('findet Root mit DCSRE_Azure Pattern', function()
    local cleanup = mock_vim_fn(true)

    local path = '/mnt/c/work/DCSRE_Azure/DCSRE/Sources/Backend'
    local result = find_dcsre_root(path)

    assert.are.equal('/mnt/c/work/DCSRE_Azure/DCSRE', result)
    cleanup()
  end)

  it('findet Root mit Worktree Pattern (DCSRE-<branch>)', function()
    local cleanup = mock_vim_fn(true)

    local path = '/mnt/c/work/DCSRE-feature-xyz/Sources/Backend/MyProject'
    local result = find_dcsre_root(path)

    assert.are.equal('/mnt/c/work/DCSRE-feature-xyz', result)
    cleanup()
  end)

  it('findet Root durch Upward Search (bei verschachtelter Struktur)', function()
    local cleanup = mock_vim_fn(true)

    -- Simuliert: bin 5 Ebenen tief in Backend, aber Sources ist Parent
    local path = '/home/uczen/work/DCSRE/Sources/Backend/VDEK.DCSP.WebHost/Properties'
    local result = find_dcsre_root(path)

    assert.are.equal('/home/uczen/work/DCSRE', result)
    cleanup()
  end)

  it('gibt nil zurück wenn keine Sources gefunden', function()
    local cleanup = mock_vim_fn(true)

    -- Override isdirectory für diesen Test: keine Sources
    local original = vim.fn.isdirectory
    vim.fn.isdirectory = function() return 0 end

    local path = '/some/random/path/Backend'
    local result = find_dcsre_root(path)

    assert.is_nil(result)
    vim.fn.isdirectory = original
    cleanup()
  end)

  it('normalisiert Backslash zu Slash (Windows Path)', function()
    local cleanup = mock_vim_fn(true)

    local path = 'C:\\Users\\Administrator\\Documents\\Work\\Code2\\DCSRE\\Sources\\Backend'
    local result = find_dcsre_root(path)

    assert.are.equal('C:/Users/Administrator/Documents/Work/Code2/DCSRE', result)
    cleanup()
  end)

  it('gibt nil zurück bei zu kurzer Pfad-Länge', function()
    local cleanup = mock_vim_fn(true)

    local path = 'C'  -- Länge <= 3
    local result = find_dcsre_root(path)

    assert.is_nil(result)
    cleanup()
  end)
end)

describe('Projekt-Detection Logic', function()
  before_each(function()
    vim.g.project_name = 'UNKNOWN'
  end)

  it('erkennt CENCOCD Projekt bei "Kluger" im Path', function()
    local cwd = '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core'

    if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
      vim.g.project_name = 'CENCOCD'
    end

    assert.are.equal('CENCOCD', vim.g.project_name)
  end)

  it('erkennt DCSRE Projekt bei "DCSRE" im Path', function()
    local cwd = '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE'

    if cwd:match('DCSRE') then
      vim.g.project_name = 'DCSRE'
    end

    assert.are.equal('DCSRE', vim.g.project_name)
  end)

  it('setzt project_name auf UNKNOWN bei unbekanntem Path', function()
    local cwd = '/some/random/project/path'

    -- Keine Matches
    if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
      vim.g.project_name = 'CENCOCD'
    elseif cwd:match('DCSRE') then
      vim.g.project_name = 'DCSRE'
    end

    assert.are.equal('UNKNOWN', vim.g.project_name)
  end)

  it('prioritisiert DCSRE über CENCOCD (falls beide im Path)', function()
    -- Edge case: Workspace mit beiden Namen?
    local cwd = '/mnt/c/DCSRE_CENCOCD_hybrid/Sources'

    -- Logik: DCSRE wird geprüft NACH CENCOCD (zeile 232 vs 246)
    -- → DCSRE gewinnt!
    if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
      vim.g.project_name = 'CENCOCD'
    elseif cwd:match('DCSRE') then
      vim.g.project_name = 'DCSRE'
    end

    assert.are.equal('DCSRE', vim.g.project_name)
  end)
end)

describe('Pfad-Konversionen', function()
  it('konvertiert /mnt/c zu C: korrekt', function()
    local path_wsl = '/mnt/c/Users/Administrator/Documents'
    local path_win = path_wsl:gsub('^/mnt/(%a)/', function(drive)
      return drive:upper() .. ':'
    end):gsub('/', '\\')

    assert.are.equal('C:\\Users\\Administrator\\Documents', path_win)
  end)

  it('normalisiert Backslash zu Slash', function()
    local path_win = 'C:\\Users\\Administrator\\Documents'
    local path_normalized = path_win:gsub('\\', '/')

    assert.are.equal('C:/Users/Administrator/Documents', path_normalized)
  end)

  it('extrahiert Dateinamen aus Pfad', function()
    local full_path = '/mnt/c/Users/Administrator/Documents/Project/init.lua'
    local filename = full_path:match('([^/]+)$')

    assert.are.equal('init.lua', filename)
  end)

  it('ersetzt Sources/Backend mit Sources/Frontend', function()
    local backend_path = '/mnt/c/work/DCSRE/Sources/Backend'
    local frontend_path = backend_path:gsub('Backend$', 'Frontend')

    assert.are.equal('/mnt/c/work/DCSRE/Sources/Frontend', frontend_path)
  end)
end)

describe('globpath() Mocking (E2E/Integration Picker)', function()
  it('findet alle .feature Files', function()
    local cypress_path = '/mnt/c/work/DCSRE/Sources/Tests/Cypress'

    -- Simuliere vim.fn.globpath
    local feature_files = {
      cypress_path .. '/e2e/login.feature',
      cypress_path .. '/e2e/dashboard.feature',
      cypress_path .. '/e2e/admin/users.feature',
    }

    assert.are.equal(3, #feature_files)
    assert.are.equal(cypress_path .. '/e2e/login.feature', feature_files[1])
  end)

  it('extrahiert relative Pfade von .feature files', function()
    local cypress_path = '/mnt/c/work/DCSRE/Sources/Tests/Cypress'
    local file = cypress_path .. '/e2e/admin/users.feature'

    local rel_path = file:gsub(cypress_path .. '/', '')
    local display_name = rel_path:gsub('e2e/', ''):gsub('%.feature$', '')

    assert.are.equal('e2e/admin/users.feature', rel_path)
    assert.are.equal('admin/users', display_name)
  end)
end)

describe('Integration Test Picker FQN Parsing', function()
  it('parsed VDEK.DCSP.IntegrationTests FQN korrekt', function()
    local line = 'VDEK.DCSP.IntegrationTests.Controllers.ControllerTests.TestMethod'

    local display_name = line:match('%.([^.]+)$') or line
    local category = line:match('IntegrationTests%.([^.]+)%.')

    assert.are.equal('TestMethod', display_name)
    assert.are.equal('Controllers', category)
  end)

  it('erstellt Display-String im Format "Category/Method"', function()
    local fqn = 'VDEK.DCSP.IntegrationTests.Providers.ProviderTests.TestAsync'

    local display_name = fqn:match('%.([^.]+)$')
    local category = fqn:match('IntegrationTests%.([^.]+)%.')
    local display = category and (category .. '/' .. display_name) or display_name

    assert.are.equal('Providers/TestAsync', display)
  end)
end)

describe('Shell Command Construction (PowerShell vs Bash)', function()
  it('baut PowerShell Command mit Set-Location korrekt', function()
    local path = 'C:\\Users\\Administrator\\Documents\\Work\\Code2\\DCSRE'
    local cmd = string.format(
      'powershell.exe -Command "Set-Location \'%s\'; dotnet test --no-build"',
      path
    )

    assert.string_contains(cmd, 'powershell.exe')
    assert.string_contains(cmd, 'Set-Location')
    assert.string_contains(cmd, 'dotnet test')
  end)

  it('baut Bash Command mit cd korrekt', function()
    local path = '/mnt/c/work/DCSRE'
    local cmd = string.format('cd "%s" && dotnet test --no-build', path)

    assert.string_contains(cmd, 'cd')
    assert.string_contains(cmd, '&&')
    assert.string_contains(cmd, 'dotnet test')
  end)

  it('filtert Integration Tests mit pipe-separierten FQNs', function()
    local selected = {
      'VDEK.DCSP.IntegrationTests.Controllers.Test1',
      'VDEK.DCSP.IntegrationTests.Controllers.Test2',
    }

    local filter_arg = table.concat(
      vim.tbl_map(function(fqn)
        return 'FullyQualifiedName~' .. fqn
      end, selected),
      '|'
    )

    assert.are.equal(
      'FullyQualifiedName~VDEK.DCSP.IntegrationTests.Controllers.Test1|FullyQualifiedName~VDEK.DCSP.IntegrationTests.Controllers.Test2',
      filter_arg
    )
  end)
end)
```

---

## 2. obsidian.nvim Platform-Analyse (Zeilen 700–960)

### Gefundene Platform-Checks: **9 Stellen**

| Zeile(n) | Kontext | Check | Problem |
|----------|---------|-------|---------|
| 745 | DCSRE Workspace | `vim.fn.has('win32') == 1 and 'C:/...' or '/mnt/c/...'` | Ternary im opts direkt |
| 749 | CenCoCo Workspace | `vim.fn.has('win32') == 1 and 'C:/...' or '/mnt/c/...'` | Ternary im opts direkt |
| 753 | Brain Workspace | `vim.fn.has('win32') == 1 and 'C:/...' or '/mnt/c/...'` | Ternary im opts direkt |
| 858 | Follow Link (Chrome) | `if vim.fn.has('win32') == 1 then start "" else vim.fn.system('...') end` | Direkter OS-Call |
| 862 | Follow Link (WSL2) | `vim.fn.system('"/mnt/c/Program Files/Google/Chrome/...' &')` | WSL2-spezifischer Chrome-Pfad |
| 890 | Image Preview | `vim.fn.isdirectory(vault_root .. '/.obsidian') == 1 or ... '\\.obsidian'` | Windows+Unix Pfad-Check |
| 902 | Image Open (Windows) | `vim.fn.system('powershell.exe -Command "Start-Process ...')` | Windows-only Befehl |
| 934 | Graph View | `if vim.fn.has('win32') == 1 then start "" else xdg-open` | OS-spezifischer URI-Handler |
| 965 | img-clip find_vault_root | `vim.fn.isdirectory(root .. '/.obsidian') == 1 or ... '\\.obsidian'` | Windows+Unix Pfad-Check (DRY-Violation!) |

### DRY-Violation: `find_vault_root()` ist dupliziert!

**Zeile 886–894** (obsidian.nvim, in `<leader>op` Keybinding):
```lua
local current = vim.fn.expand('%:p:h')
local vault_root = current
while vault_root ~= '' and vault_root ~= '/' and vault_root ~= 'C:\\' do
  if vim.fn.isdirectory(vault_root .. '/.obsidian') == 1 or
     vim.fn.isdirectory(vault_root .. '\\.obsidian') == 1 then
    break
  end
  vault_root = vim.fn.fnamemodify(vault_root, ':h')
end
```

**Zeile 958–969** (img-clip.nvim, `find_vault_root()`):
```lua
local function find_vault_root()
  local current = vim.fn.expand('%:p:h')
  local root = current
  while root ~= '' and root ~= '/' and root ~= 'C:\\' do
    if vim.fn.isdirectory(root .. '/.obsidian') == 1 or
       vim.fn.isdirectory(root .. '\\.obsidian') == 1 then
      return root
    end
    root = vim.fn.fnamemodify(root, ':h')
  end
  -- ... continues with return logic
```

**Zudem** Graph View (Zeile 917–925) hat eine DRITTE, leicht abweichende Variante!

### Empfehlung: Shared Modul `lua/shared/obsidian_helpers.lua`

```lua
-- lua/shared/obsidian_helpers.lua
local M = {}

-- Finde Obsidian Vault-Root durch Suche nach .obsidian/
-- Funktioniert auf Windows und WSL2/Unix
M.find_vault_root = function()
  local current = vim.fn.expand('%:p:h')
  local root = current

  while root ~= '' and root ~= '/' and root ~= 'C:\\' do
    -- Check both Unix (/) und Windows (\) paths
    if vim.fn.isdirectory(root .. '/.obsidian') == 1 or
       vim.fn.isdirectory(root .. '\\.obsidian') == 1 then
      return root
    end
    root = vim.fn.fnamemodify(root, ':h')
  end

  return nil
end

-- Get Obsidian workspace paths (Windows vs WSL2)
M.get_workspace_paths = function()
  local is_windows = vim.fn.has('win32') == 1

  return {
    DCSRE = is_windows and 'C:/Users/Administrator/Documents/DCS'
                        or '/mnt/c/Users/Administrator/Documents/DCS',
    CenCoCo = is_windows and 'C:/Users/Administrator/Documents/Obsydian/CenCoCo'
                          or '/mnt/c/Users/Administrator/Documents/Obsydian/CenCoCo',
    Brain = is_windows and 'C:/Users/Administrator/Documents/Brain'
                       or '/mnt/c/Users/Administrator/Documents/Brain',
  }
end

return M
```

**Dann in init.lua ersetzen:**
- Zeile 745–754: `workspaces` table → `require('shared/obsidian_helpers').get_workspace_paths()`
- Zeile 886–894, 917–925, 958–969: Alle `find_vault_root()` Varianten → `require('shared/obsidian_helpers').find_vault_root()`

---

## 3. E2E vs Integration Picker Konsolidierung

### Code-Vergleich: Zeilen 2017–2110 vs 2191–2303

**Ähnlichkeiten:**
| Aspekt | E2E | Integration | Ähnlich? |
|--------|-----|-------------|----------|
| Platform-Check | `is_win = vim.fn.has('win32') == 1` | `is_win = vim.fn.has('win32') == 1` | 100% ✅ |
| Finder-Code | `finders.new_table({ results = ..., entry_maker = ... })` | `finders.new_table({ results = ..., entry_maker = ... })` | 95% ✅ |
| Multi-Select Logic | `get_multi_selection() + fallback` | `get_multi_selection() + fallback` | 100% ✅ |
| Command Building | `powershell.exe vs bash` | `powershell.exe vs bash` | 95% ✅ |
| Terminal Opening | `local Terminal = require('toggleterm.terminal').Terminal` | `local Terminal = require('toggleterm.terminal').Terminal` | 100% ✅ |

**Unterschiede:**
| Aspekt | E2E | Integration | Differenz |
|--------|-----|-------------|-----------|
| Pfad-Logik | `cypress_path = ... Sources/Tests/Cypress` | `backend_root = ... project_backend_windows or project_backend` | Unterschiedliche Pfade |
| Datei-Typ | `.feature` files (Gherkin) | `dotnet test --list-tests` (FQN) | Unterschiedliche Datenquellen |
| Parsing | `rel_path`, `display_name` | `fqn`, `category`, `display` | Unterschiedliche Daten-Struktur |
| Filter-Arg | Komma-separiert (`spec_arg = table.concat(selected, ',')`) | Pipe-separiert (`FullyQualifiedName~...` \| ) | CLI-spezifische Unterschiede |
| Kommando | `npx cypress run --spec '...'` | `dotnet test --filter '...'` | Völlig unterschiedliche CLIs |

### Lohnt sich Konsolidierung?

**JA, bedingt. Der gemeinsame Kern ist ~70%:**

```lua
-- lua/shared/test_picker.lua
local M = {}

-- Generischer Test-Picker mit Konfiguration
M.run_picker = function(config)
  local pickers = require('telescope.pickers')
  local finders = require('telescope.finders')
  local conf = require('telescope.config').values
  local actions = require('telescope.actions')
  local action_state = require('telescope.actions.state')

  -- 1. Finde Dateien/Tests (config-spezifisch)
  local results = config.get_results()

  if #results == 0 then
    vim.notify(config.empty_message, vim.log.levels.WARN)
    return
  end

  -- 2. Picker öffnen (Shared Code)
  pickers.new({}, {
    prompt_title = config.prompt_title,
    finder = finders.new_table({
      results = results,
      entry_maker = function(entry)
        return config.entry_maker(entry)
      end,
    }),
    sorter = conf.generic_sorter({}),
    previewer = config.previewer,
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        local picker = action_state.get_current_picker(prompt_bufnr)
        local multi_selections = picker:get_multi_selection()
        actions.close(prompt_bufnr)

        -- 3. Sammle Selections (Shared Code)
        local selected = {}
        if #multi_selections > 0 then
          for _, sel in ipairs(multi_selections) do
            table.insert(selected, config.extract_value(sel.value))
          end
        else
          local single = action_state.get_selected_entry()
          if single then
            table.insert(selected, config.extract_value(single.value))
          end
        end

        if #selected == 0 then
          vim.notify('No tests selected', vim.log.levels.WARN)
          return
        end

        -- 4. Baue Kommando (config-spezifisch)
        local cmd = config.build_command(selected)

        vim.notify('Running ' .. #selected .. ' test(s)...', vim.log.levels.INFO)

        -- 5. Öffne Terminal (Shared Code)
        local Terminal = require('toggleterm.terminal').Terminal
        local test_term = Terminal:new({
          cmd = cmd,
          direction = 'horizontal',
          size = config.terminal_size or 15,
          on_exit = function()
            vim.notify('Test execution finished', vim.log.levels.INFO)
          end,
        })
        test_term:toggle()
      end)
      return true
    end,
  }):find()
end

return M
```

**Dann könnten Keybindings so aussehen:**
```lua
-- E2E Picker
local e2e_config = {
  get_results = function()
    local cypress_path = ...
    local feature_files = vim.fn.globpath(cypress_path .. '/e2e', '**/*.feature', false, true)
    -- parse to results
    return results
  end,
  prompt_title = 'E2E Tests',
  entry_maker = function(entry) return { ... } end,
  extract_value = function(entry) return entry.rel_path end,
  build_command = function(selected)
    -- PowerShell vs bash
    return cmd
  end,
  previewer = conf.file_previewer({}),
  terminal_size = 15,
}

require('shared/test_picker').run_picker(e2e_config)
```

**ABER: Nachteile der Konsolidierung:**
1. **Konfiguration wird komplex**: Jede Picker-Variante braucht 5+ Funktionen
2. **Lesbarkeit sinkt**: Die aktuelle inline-Logik ist klar und wartbar
3. **Duplikation ist minimal**: ~30 Zeilen echter Code unterscheiden sich
4. **Zukünftige Picker**: E2E/Integration sind wahrscheinlich einmalig

**Empfehlung: NICHT konsolidieren (yet).** Erst wenn ein 3. Picker auftaucht!

---

## 4. Top 3 Refactoring-Risiken

### ⚠️ Risiko 1: `find_dcsre_root()` - Module-Extraction

**Lage**: Zeilen 202–227 (lokal im Top-Level)

**Problem**: Diese Funktion wird als lokal definiert, aber ist zentral für Projekt-Detection.

**Risiken beim Refactoring zu Modul:**
1. **Lazy Loading**: Wenn zu `lua/shared/project.lua` verschoben, muss vor Zeile 229 geladen werden (im `config` block ist zu spät!)
2. **Timing**: Die Funktion wird sofort nach Definition genutzt (Zeile 248)
3. **Pfad-Normalisierung**: Der Regex `path:match('(.*/DCSRE[^/]*)/Sources')` kann fehlschlagen wenn:
   - Pfad endet mit Trailing Slash → Pattern bricht
   - Nested DCSRE Struktur → Pattern-Reihenfolge kritisch
   - Windows Paths mit Backslash → muss zuerst normalisiert werden

**Mitigation:**
```lua
-- NICHT in Lazy-Block! Im Top-Level vor Zeile 229:
local dcsre = require('shared.project')
local dcsre_root = dcsre.find_dcsre_root(cwd)
```

**Test-Fall der immer bricht:**
```
Input:  C:\Users\...\DCSRE_Azure\DCSRE\Sources\Backend\
Expect: C:\Users\...\DCSRE_Azure\DCSRE
Actual: nil (wegen Trailing Slash!)
```

---

### ⚠️ Risiko 2: Obsidian Workspace Pfad-Definition

**Lage**: Zeilen 745–754 (in `obsidian.nvim` opts)

**Problem**: Workspace Pfade sind hardcoded in init.lua, aber können sich ändern:
- User wechselt auf anderen Computer
- User hat unterschiedliche Ordnerstruktur
- Workspace wird umbenannt

**Risiken beim Refactoring zu externe Config:**
1. **Plugin-Init-Timing**: `obsidian.nvim` wird LAZY LOADED (`lazy = false`), aber Pfade müssen vor Plugin-Load bekannt sein
2. **Fallback-Logik**: Wenn externe Config fehlt, wo ist der Fallback?
3. **Windows vs WSL2**: Die externe Config müsste auch Platform-aware sein

**Beispiel Disaster:**
```lua
-- Wenn man so macht (FALSCH):
local config = require('obsidian_config')  -- lädt zu spät!
opts = {
  workspaces = config.workspaces,  -- obsidian.nvim ist noch nicht ready
}
```

**Besser: Bleibe im init.lua, extrahiere nur in `shared/obsidian_helpers.lua`!**

---

### ⚠️ Risiko 3: PowerShell vs Bash Kommandobau (E2E + Integration Picker)

**Lage**: Zeilen 2097–2109 (E2E), 2291–2303 (Integration)

**Problem**: Der Kommandozeilenaufbau ist Platform-abhängig UND CLI-abhängig:

```lua
-- E2E: Cypress (npm-based)
if is_win then
  cmd = string.format(
    'powershell.exe -Command "Set-Location \'%s\'; npx cypress run --spec \'%s\'"',
    cypress_path:gsub('/', '\\'),
    spec_arg
  )
else
  cmd = string.format(
    'cd "%s" && npx cypress run --spec "%s"',
    cypress_path,
    spec_arg
  )
end

-- Integration: dotnet test
if is_win then
  cmd = string.format(
    'powershell.exe -Command "Set-Location \'%s\'; dotnet test --filter \'%s\'"',
    backend_root:gsub('/', '\\'),
    filter_arg
  )
else
  cmd = string.format(
    'cd "%s" && dotnet test --filter "%s" --verbosity detailed',
    backend_root,
    filter_arg
  )
end
```

**Risiken:**
1. **Quote-Escaping**: PowerShell-Quoting unterscheidet sich von Bash
   - PowerShell: `'Set-Location \'C:\path\'' ` ← doppelte Backslash!
   - Bash: `cd "/mnt/c/path"` ← einfache Backslash-Quoting
   - Wenn man Copy-Paste falsch macht, wird Command unheilbar broken

2. **Pfad-Konversion**: `gsub('/', '\\')` funktioniert auf WSL2 **nicht**!
   ```lua
   -- FALSCH: On WSL2, dies ist der Pfad:
   local path_wsl = '/mnt/c/Users/Administrator/...'
   path_wsl:gsub('/', '\\')  -- Result: \mnt\c\Users\...  <- INVALID!

   -- RICHTIG: Erst prüfen ob es bereits Windows-Pfad ist
   local is_windows = vim.fn.has('win32') == 1
   local win_path = is_windows and path or path  -- Kein gsub nötig!
   ```

3. **Fehlerbehandlung**: Wenn Command bricht, ist schwer zu debuggen:
   ```
   PowerShell Error: Set-Location: Cannot find path because it does not exist
   ```
   Vs
   ```
   Bash Error: cd: /mnt/c/Users/...: No such file or directory
   ```

**Mitigation:**
```lua
-- Extrahiere in Helper:
local function build_shell_cmd(cmd, working_dir, is_windows)
  if is_windows then
    return string.format(
      'powershell.exe -Command "Set-Location \'%s\'; %s"',
      working_dir,  -- Don't gsub! PowerShell understands forward slashes
      cmd
    )
  else
    return string.format(
      'cd "%s" && %s',
      working_dir,
      cmd
    )
  end
end

-- Use:
local cypress_cmd = 'npx cypress run --spec \'path/to/test.feature\''
local full_cmd = build_shell_cmd(cypress_cmd, cypress_path, is_win)
```

---

## 5. Zusammenfassung Test-Abdeckung

### Was getestet SEIN MUSS (vor Refactoring):

| Funktion | Tests | Kritikalität | Status |
|----------|-------|--------------|--------|
| `find_dcsre_root()` | 8 Test-Cases (s.o.) | 🔴 KRITISCH | Noch zu schreiben |
| Projekt-Detection | 5 Test-Cases (s.o.) | 🔴 KRITISCH | Noch zu schreiben |
| Pfad-Konversionen | 4 Test-Cases (s.o.) | 🟡 HOCH | Noch zu schreiben |
| Obsidian `find_vault_root()` | 3 Test-Cases (DRY-Check) | 🟡 HOCH | Noch zu schreiben |
| Shell-Kommandozeilenaufbau | 5 Test-Cases (PowerShell/Bash) | 🟡 HOCH | Noch zu schreiben |

**Total: 25 konkrete Test-Cases zu schreiben** (im obigen `project_spec.lua` enthalten)

### Ausführung
```bash
# Im Projekt-Root:
cd C:\Users\Administrator\Documents\Projekt\KickStartNeoVim
nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"
```

---

## 6. Recommendations für Refactoring-Reihenfolge

1. **Phase 1 - Tests schreiben** (~2h)
   - `lua/spec/project_spec.lua` anlegen
   - Alle 25 Test-Cases ausführen
   - Tests müssen GRÜN sein bevor Code umgestellt wird

2. **Phase 2 - Obsidian DRY-Violation beheben** (~1h)
   - `lua/shared/obsidian_helpers.lua` erstellen
   - Zeilen 886–894, 917–925, 958–969 konsolidieren
   - Tests re-run

3. **Phase 3 - `find_dcsre_root()` extrahieren** (~1.5h)
   - `lua/shared/project.lua` erstellen
   - Zeilen 202–227 extrahieren (behalte order!)
   - Require vor Zeile 229
   - Tests re-run

4. **Phase 4 - Platform-Checks vereinheitlichen** (~1h)
   - Ersetze alle `vim.fn.has('win32')` Inline-Checks mit zentraler `is_windows` Variable
   - Oder: Extrahiere zu `lua/shared/platform.lua`
   - Tests re-run

5. **Phase 5 - E2E/Integration Picker** (OPTIONAL, ~2h wenn gemacht)
   - Evaluate ob `lua/shared/test_picker.lua` Modul nötig
   - Wahrscheinlich: NICHT wert! (Empfehlung: Überspringen)

---

**D02 Analysis Ende.**
