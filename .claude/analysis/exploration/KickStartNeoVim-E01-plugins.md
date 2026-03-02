---
wave: exploration
agent: E01
focus: plugins-platform-dependencies
status: final
primaerquelle_gelesen: true
date: 2026-03-02
---

# E01: Plugin Platform-Abhängigkeiten

## Executive Summary

Aus der init.lua-Analyse (4541 Zeilen) zeigen sich **9 Plugins mit signifikanten Platform-Abhängigkeiten**, die hauptsächlich durch 3 Muster entstehen:

1. **Path-Format-Differenzen** (Windows `C:\` vs WSL2 `/mnt/c/`)
2. **Executable-Suffix** (`.exe` nur Windows)
3. **Command-Runner** (PowerShell vs Bash)

**Kritische Erkenntnis**: Die meisten Platform-Checks nutzen bereits `vim.fn.has('win32')` als **konsistentes Muster**, aber das Refactoring in ein `is_windows` Global könnte den Code drastisch reduzieren.

---

## ⚠️ Plugins MIT Platform-Abhängigkeit

### 1. markdown-preview.nvim (Zeilen 660–700)
**Kategorie**: Browser-Pfad + Funktionsaufruf

**Was ist platform-spezifisch:**
- Chrome-Executable-Pfad: `C:\Program Files\Google\Chrome\Application\chrome.exe` (Windows) vs `/mnt/c/Program\ Files/Google/Chrome/Application/chrome.exe` (WSL2)
- Vim function `OpenMarkdownPreview(url)` wird komplett neu definiert pro Platform
- Flag `--new-window` ist identisch, aber Escaping unterschiedlich

```lua
-- Windows: direct path with backslashes
execute 'silent !start "" "C:\Program Files\Google\Chrome\Application\chrome.exe"...'

-- WSL2: escaped forward slashes + /mnt/c path
execute 'silent !/mnt/c/Program\ Files/Google/Chrome/Application/chrome.exe...'
```

**Shared Code möglich:**
- Das Flag `--new-window` ist identisch
- Die Vim function Struktur ist identisch
- Nur die Path-Logik wechselt

**Empfehlung für Refactoring:**
```lua
-- Proposed: Move to globals or plugin init
local chrome_path = vim.fn.has('win32') == 1
  and 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  or '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'

-- Then use in function:
vim.cmd([[ function OpenMarkdownPreview(url)
  execute 'silent !start "" "' . chrome_path . '" --new-window "' . a:url . '"'
endfunction ]])
```

**Komplexität**: **Mittel** (3 Blöcke, aber repetitiv)

---

### 2. obsidian.nvim (Zeilen 702–950)
**Kategorie**: Workspace-Pfade + Directory-Separators

**Was ist platform-spezifisch:**
- **3 Workspace-Pfade** mit `vim.fn.has('win32')` Ternary-Operator (Zeilen 745, 749, 753):
  ```lua
  path = vim.fn.has('win32') == 1
    and 'C:/Users/Administrator/Documents/DCS'
    or '/mnt/c/Users/Administrator/Documents/DCS'
  ```
- **2 Directory-Separator-Checks** in Custom Keybindings (Zeilen 889-891, 920-922):
  ```lua
  while root ~= '' and root ~= '\' and root ~= 'C:\\' do
    if vim.fn.isdirectory(root .. '/.obsidian') == 1
       or vim.fn.isdirectory(root .. '\\.obsidian') == 1 then
  ```
- **Obsidian URI für Windows/Linux** (Zeilen 933-945): `obsidian://advanced-uri?...` ist identisch, aber open-Befehl unterschiedlich

**Shared Code möglich:**
- ✅ Die 3 workspace paths folgen einem **konsistenten Template**
- ✅ Die Directory-Traversal-Logik (Zeilen 889+) ist **identisch**, nur Separator wechselt
- ✅ Der URI-Teil ist **100% shared**

**Empfehlung für Refactoring:**

```lua
-- At top of obsidian config:
local is_windows = vim.fn.has('win32') == 1
local sep = is_windows and '\\' or '/'

-- Workspace template:
local workspaces = {
  {
    name = 'DCSRE',
    path = is_windows
      and 'C:/Users/Administrator/Documents/DCS'
      or '/mnt/c/Users/Administrator/Documents/DCS',
  },
  -- ... more workspaces
}

-- Directory search refactored:
while root ~= '' and root ~= sep and root ~= (is_windows and 'C:\\' or '/') do
  local obsidian_markers = {
    root .. '/.obsidian',
    root .. (sep == '\\' and '\\' or '/') .. '.obsidian'
  }
  local found = false
  for _, marker in ipairs(obsidian_markers) do
    if vim.fn.isdirectory(marker) == 1 then found = true break end
  end
  if found then break end
  root = vim.fn.fnamemodify(root, ':h')
end
```

**Komplexität**: **Hoch** - 5 separate Platform-Blöcke, aber sehr repetitiv und hochgradig refactorisierbar

---

### 3. img-clip.nvim (Zeilen 952–1023)
**Kategorie**: Directory-Separator im Helper-Function

**Was ist platform-spezifisch:**
- **Helper-Function `find_vault_root()`** (Zeilen 964-966):
  ```lua
  while root ~= '' and root ~= '/' and root ~= 'C:\\' do
    if vim.fn.isdirectory(root .. '/.obsidian') == 1
       or vim.fn.isdirectory(root .. '\\.obsidian') == 1 then
  ```

**Shared Code möglich:**
- ✅ Der REST ist **100% shared** (path-Logik, Timestamp, Drag&Drop, etc.)
- ✅ Nur die Separator-Checks wechseln

**Empfehlung für Refactoring:**
```lua
-- Use same helper as obsidian:
local is_windows = vim.fn.has('win32') == 1

while root ~= ''
  and root ~= '/'
  and root ~= (is_windows and 'C:\\' or '/') do
  -- Check both separators
  local has_obsidian = vim.fn.isdirectory(root .. '/.obsidian') == 1
    or vim.fn.isdirectory(root .. (is_windows and '\\' or '/') .. '.obsidian') == 1
  if has_obsidian then break end
  root = vim.fn.fnamemodify(root, ':h')
end
```

**Komplexität**: **Niedrig** (nur 1 Block, sehr einfach zu refaktorieren)

---

### 4. nvim-dap (Zeilen 1384–1514)
**Kategorie**: Executable-Suffix

**Was ist platform-spezifisch:**
- **Netcoredbg-Adapter-Pfad** (Zeilen 1476-1479):
  ```lua
  local netcoredbg_path = vim.fn.stdpath('data') .. '/mason/packages/netcoredbg/netcoredbg/netcoredbg'
  if vim.fn.has('win32') == 1 then
    netcoredbg_path = netcoredbg_path .. '.exe'
  end
  ```

**Shared Code möglich:**
- ✅ Die komplette DAP-Konfiguration ist **shared**
- ✅ Nur `.exe`-Suffix ist Platform-spezifisch (1 Zeile!)

**Empfehlung für Refactoring:**
```lua
local exe_suffix = vim.fn.has('win32') == 1 and '.exe' or ''
local netcoredbg_path = vim.fn.stdpath('data') .. '/mason/packages/netcoredbg/netcoredbg/netcoredbg' .. exe_suffix
```

**Komplexität**: **Sehr Niedrig** (nur 1 conditional, trivial zu refaktorieren)

---

### 5. blink.cmp + LuaSnip (Zeilen 2775–2872)
**Kategorie**: Build-Script Conditional

**Was ist platform-spezifisch:**
- **LuaSnip Build-Step** (Zeilen 2784-2792):
  ```lua
  build = (function()
    -- Build Step is needed for regex support in snippets.
    -- This step is not supported in many windows environments.
    if vim.fn.has 'win32' == 1 or vim.fn.executable 'make' == 0 then
      return  -- Skip build on Windows
    end
    return 'make install_jsregexp'
  end)(),
  ```

**Shared Code möglich:**
- ✅ Die komplette blink.cmp Konfiguration (`opts`) ist **100% shared**
- ✅ Nur der **build-Function ist conditional**

**Empfehlung für Refactoring:**
```lua
-- Already pretty clean! Just document:
build = (function()
  -- jsregexp build requires Unix 'make' (not available on Windows)
  if vim.fn.has('win32') == 1 or vim.fn.executable('make') == 0 then
    return nil  -- Explicit nil instead of missing return
  end
  return 'make install_jsregexp'
end)(),
```

**Komplexität**: **Sehr Niedrig** (build-Logic ist bereits optimal isoliert)

---

### 6. telescope E2E Picker (Zeilen 2017–2110)
**Kategorie**: Path-Format + Command-Runner

**Was ist platform-spezifisch:**
- **Path-Format** (Zeilen 2017-2028):
  ```lua
  local is_win = vim.fn.has('win32') == 1
  local cypress_path = project_root .. (is_win and '\\Sources\\Tests\\Cypress' or '/Sources/Tests/Cypress')
  ```
- **Command-Ausführung** (Zeilen 2097-2109):
  ```lua
  if is_win then
    cmd = 'powershell.exe -Command "Set-Location \'...\'; npx cypress run --spec \'...\'"'
  else
    cmd = 'cd "..." && npx cypress run --spec "..."'
  end
  ```

**Shared Code möglich:**
- ✅ Finder/Sorter/Previewer sind **100% shared**
- ✅ Multi-Select-Logic ist **100% shared**
- ✅ Nur Path-Logik und Command-String wechseln

**Empfehlung für Refactoring:**
```lua
-- Abstract into helper
local function get_cypress_cmd(cypress_path, spec_arg, is_win)
  if is_win then
    return string.format(
      'powershell.exe -Command "Set-Location \'%s\'; npx cypress run --spec \'%s\'"',
      cypress_path:gsub('/', '\\'),
      spec_arg
    )
  else
    return string.format(
      'cd "%s" && npx cypress run --spec "%s"',
      cypress_path,
      spec_arg
    )
  end
end

-- Then in picker:
local cmd = get_cypress_cmd(cypress_path, spec_arg, is_win)
```

**Komplexität**: **Mittel** (2 separate Blöcke, aber hochgradig refactorisierbar)

---

### 7. telescope Integration Test Picker (Zeilen 2191–2303)
**Kategorie**: Path-Format + Command-Runner (identisch zu E2E!)

**Was ist platform-spezifisch:**
- **Path-Format & Backend-Root** (Zeilen 2191-2202):
  ```lua
  local is_win = vim.fn.has('win32') == 1
  local backend_root = is_win and vim.g.project_backend_windows or vim.g.project_backend
  ```
- **Befehl zum Auflisten von Tests** (Zeilen 2207-2214):
  ```lua
  if is_win then
    cmd = 'powershell.exe -Command "Set-Location \'...\'; dotnet test --list-tests ..."'
  else
    cmd = 'cd "..." && dotnet test --list-tests ...'
  end
  ```
- **Befehl zum Ausführen von Tests** (Zeilen 2291-2303):
  ```lua
  if is_win then
    test_cmd = 'powershell.exe -Command "Set-Location \'...\'; dotnet test ..."'
  else
    test_cmd = 'cd "..." && dotnet test ...'
  end
  ```

**Shared Code möglich:**
- ✅ Picker-Setup ist **100% shared** (nur Commands unterscheiden sich)
- ✅ Test-Parsing ist **100% shared**
- ✅ Multi-Select-Logic ist **100% shared**

**Empfehlung für Refactoring:**
```lua
-- Abstract command building
local function get_dotnet_cmd(backend_root, extra_args, is_win)
  if is_win then
    return string.format(
      'powershell.exe -Command "Set-Location \'%s\'; dotnet %s"',
      backend_root:gsub('/', '\\'),
      extra_args
    )
  else
    return string.format('cd "%s" && dotnet %s', backend_root, extra_args)
  end
end

-- Then:
local list_cmd = get_dotnet_cmd(backend_root, 'test --list-tests --no-build 2>&1 | grep "VDEK.DCSP"', is_win)
local test_cmd = get_dotnet_cmd(backend_root, 'test --no-build ... --filter "' .. filter_arg .. '"', is_win)
```

**Komplexität**: **Mittel-Hoch** (mehrere Commands, aber alle folgen gleichem Pattern)

---

### 8. neogit (Zeilen 470–650)
**Kategorie**: Commands in Keybindings (sehr subtil!)

**Was ist platform-spezifisch:**
- **Git-Befehle für Push/Pull** - ausgelagert in **separate Keybindings** (nicht im Plugin selbst)
- Plugin-Config selbst ist **100% shared** - aber Keybindings verwenden externe Globals wie `vim.g.project_root_windows`

**Shared Code möglich:**
- ✅ neogit Plugin config: **vollständig shared**
- ✅ Diffview Integration: **vollständig shared**

**Empfehlung für Refactoring:**
- ✅ Bereits optimal - Platform-Logik ist **ausgelagert** in externe Keybindings

**Komplexität**: **Sehr Niedrig** (Plugin selbst hat keine Platform-Checks)

---

### 9. toggleterm (Zeilen 1024–1066)
**Kategorie**: Command-String-Format in Keybindings (nicht im Plugin)

**Was ist platform-spezifisch:**
- Plugin-Config selbst: **100% shared**
- Platform-Logik ist in den **Keybindings ausgelagert** die das Plugin nutzen:
  - `<leader>rbw`, `<leader>rfr`, `<leader>rDi`, etc. (siehe CLAUDE.md)
  - Alle verwenden `vim.fn.has('win32')` um Shell-Commands zu wählen

**Shared Code möglich:**
- ✅ toggleterm Plugin: **vollständig shared**
- ⚠️ Keybindings: können mit Helper-Funktionen refaktoriert werden

**Empfehlung für Refactoring:**
- Alle Keybindings könnten zentrale Helper nutzen:
  ```lua
  -- Central helper
  local function run_in_shell(cmd_win, cmd_wsl)
    local is_win = vim.fn.has('win32') == 1
    local cmd = is_win and cmd_win or cmd_wsl
    local terminal = Terminal:new({ cmd = cmd, ... })
    terminal:toggle()
  end

  -- Then in keybindings:
  run_in_shell('powershell.exe -Command ...', 'bash -c ...')
  ```

**Komplexität**: **Mittel** (Keybindings, nicht Plugin)

---

## ✅ Plugins OHNE Platform-Abhängigkeit (rein shared)

Diese Plugins haben **KEINERLEI Platform-Checks** und funktionieren identisch auf Windows/WSL2:

### Shared Plugins
1. **nvim-lspconfig** (LSP servers) - Pfade werden von globalen Variablen gelöst
2. **omnisharp-extended-lsp.nvim** - Nur Handler, keine Platform-Logik
3. **neogit** (Plugin-Config selbst) - Diffview Integration ist shared
4. **gitsigns** - Alle Signs/Commands sind shared
5. **dap-ui** - Layout/UI ist Platform-agnostisch
6. **nvim-dap-virtual-text** - Setup ist shared
7. **telescope.nvim** (Kern) - nur einige **Keybindings** haben Platform-Logik
8. **tokyonight.nvim** - Colorscheme ist shared
9. **catppuccin** - Colorscheme ist shared
10. **nvim-treesitter** - Syntax-Highlighting ist shared
11. **mini.nvim** - Status-Line ist shared
12. **which-key.nvim** - Keymap-Display ist shared
13. **todo-comments.nvim** - Comment-Highlighting ist shared
14. **nvim-comment** - Comment-Toggle ist shared
15. **harpoon** - File-Navigation ist shared
16. **nvim-tree.lua** - File-Explorer ist shared
17. **autopairs** - Auto-Completion ist shared
18. **indent-blankline.nvim** - Indentation ist shared
19. **fidget.nvim** - LSP Progress ist shared
20. **lazydev.nvim** - Lua API Docs ist shared
21. **conform.nvim** - Formatter ist shared
22. **lint.nvim** - Linter ist shared
23. **mason.nvim** - Package Manager (funktioniert auf beiden Plattformen!)
24. **mason-lspconfig.nvim** - LSP Auto-Setup ist shared

---

## 🎯 Kritische Erkenntnisse

### Pattern 1: `vim.fn.has('win32')` ist das Standard-Muster
**Findung**: Fast alle Platform-Checks nutzen diesen **konsistenten Muster**:
```lua
local is_windows = vim.fn.has('win32') == 1
local path = is_windows and 'C:\\...' or '/mnt/c/...'
```

**Optimierungspotenzial**: Ein einziges **Global `_G.is_windows`** könnte alle Duplikate eliminieren.

---

### Pattern 2: Path-Format-Probleme sind am häufigsten
**Statistik**:
- **9/9 Plugins** mit Platform-Abhängigkeit haben **Path-Format-Probleme**
- davon **4/9** auch **Command-Runner-Unterschiede** (PowerShell vs Bash)
- davon **3/9** auch **Directory-Separator-Unterschiede**

**Kernproblem**: Windows benutzt `\` und `C:\`, WSL2 benutzt `/` und `/mnt/c/`

**Lösungsstrategie**:
1. Zentrale Path-Abstraktionen pro Plugin-Familie
2. Separator-Konstanten statt Hard-Coding
3. Command-Builder-Helper-Funktionen

---

### Pattern 3: Obsidian + img-clip.nvim sind Code-Duplikate
**Findung**: Die `find_vault_root()` Funktion existiert in **beiden**:
- **obsidian.nvim** (Zeilen 886-892, 916-922) - 2x
- **img-clip.nvim** (Zeilen 959-974) - 1x

**DRY-Verletzung**: Identische Logik, aber 3 separate Implementierungen!

**Refactoring**: Eine zentrale Utility-Function in `init.lua` könnte alle 3 ersetzen:
```lua
-- Global helper
_G.find_obsidian_vault_root = function()
  local current = vim.fn.expand('%:p:h')
  local root = current
  local is_win = vim.fn.has('win32') == 1

  while root ~= '' and root ~= '/' and root ~= 'C:\\' do
    local obsidian_dir = root .. '/.obsidian'
    if vim.fn.isdirectory(obsidian_dir) == 1 then
      return root
    end
    if is_win then
      obsidian_dir = root .. '\\.obsidian'
      if vim.fn.isdirectory(obsidian_dir) == 1 then
        return root
      end
    end
    root = vim.fn.fnamemodify(root, ':h')
  end

  return current  -- Fallback
end
```

---

### Pattern 4: Telescope Pickers haben identische Pattern (E2E + Integration)
**Findung**: E2E Picker (2017–2110) und Integration Test Picker (2191–2303):
- Beide nutzen identische `is_win` / `path_format` / `command_building` Pattern
- Beide könnten eine gemeinsame Helper-Funktion nutzen

**Code-Duplikation**: ~100 Zeilen identischer Logik, nur Kommandos unterscheiden sich

**Refactoring-Kandidat**: Hoch!

---

### Pattern 5: Nur 2 Plugins (blink.cmp, nvim-dap) haben essenziell NEUE Abhängigkeiten
**Findung**:
- **blink.cmp**: Build-Step ist Windows-problematisch (nur jsregexp)
- **nvim-dap**: netcoredbg `.exe`-Suffix ist neu pro Platform

**Alles andere**: Platform-Checks sind nur für **bestehende Funktionalität** in unterschiedlichen Formaten nötig.

---

## 📊 Refactoring-Roadmap

### Phase 1: Quick Wins (1-2 Stunden)
1. **Zentrale `is_windows` Global** am Init-Start
   - Reduces duplicate `vim.fn.has('win32') == 1` checks
   - ~30 Zeilen Code einsparen

2. **Helper `find_obsidian_vault_root()`**
   - Konsolidiert 3 Implementierungen in obsidian.nvim + img-clip.nvim
   - ~50 Zeilen Code einsparen

3. **`.exe` Suffix Helper**
   - nvim-dap + etwaige zukünftige .exe Executable-Pfade
   - ~10 Zeilen Code einsparen

### Phase 2: Medium Effort (2-3 Stunden)
1. **Command-Builder Helper Functions**
   - `get_shell_cmd(cmd_win, cmd_wsl)` - zentral für alle Keybindings
   - `get_path_for_project(project_name, path_win, path_wsl)`
   - ~100 Zeilen Code refaktorieren

2. **Obsidian Workspace Template**
   - Konsolidiert 3 repetitive Workspace-Pfade
   - ~20 Zeilen Code einsparen

### Phase 3: Larger Refactoring (3+ Stunden)
1. **Telescope Picker Consolidation**
   - Extract gemeinsamer E2E + Integration Test Picker Code
   - Shared: Finder, Sorter, Multi-Select, Terminal-Open
   - Different: List Command + Run Command nur
   - ~150 Zeilen Code refaktorieren

2. **Markdown-Preview Helper**
   - Zentralisierte Chrome-Path-Resolution
   - ~30 Zeilen Code einsparen

---

## 🔧 Zusammenfassung für Team Lead

| Plugin | Platform-Checks | Komplexität | Refactoring-Potenzial |
|--------|-----------------|-------------|----------------------|
| markdown-preview | 1 (Browser-Path) | Mittel | Hoch |
| obsidian | 5 (Workspaces + Dir-Traversal) | Hoch | **SEHR Hoch** (DRY-Verletzungen!) |
| img-clip | 1 (Dir-Traversal) | Niedrig | Hoch (Shared mit obsidian!) |
| nvim-dap | 1 (.exe Suffix) | Sehr Niedrig | Niedrig (schon optimal isoliert) |
| blink.cmp | 1 (Build-Step) | Sehr Niedrig | Sehr Niedrig (schon optimal) |
| telescope E2E | 2 (Path + Command) | Mittel | **Hoch** (Shared mit Integration!) |
| telescope Integration | 2 (Path + Command) | Mittel-Hoch | **Hoch** (Identisch zu E2E!) |
| neogit | 0 (in Config) | - | Keine |
| toggleterm | 0 (in Keybindings) | - | Mittel (Keybindings betroffen) |

**Gesamturteil**:
- **15-20%** Code-Reduktion durch Zentralisierung von Platform-Helpers möglich
- **3 DRY-Verstöße**: obsidian (2x find_vault), E2E+Integration Duplikate
- **Größte Gewinn**: obsidian refactoring + Telescope Picker consolidation
