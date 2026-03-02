# Crumbs: KickStartNeoVim

## Platform-Detection

```lua
-- Zeile 200
local is_windows = vim.fn.has('win32') == 1
```

Diese Variable wird **früh** (vor der Lazy.setup) gesetzt und überall im File referenziert.
Sie ist lokal im Top-Level-Scope – kein Modul, kein require.

Zusätzliche inline-Checks (nicht via `is_windows` Variable):
- `vim.fn.has('win32') == 1` (Markdown-Preview: Zeilen 680–694)
- `vim.fn.has('win32') == 1` (DAP netcoredbg path: Zeile 1477)
- `vim.fn.has('win32') == 1` (Obsidian workspace paths: Zeilen 745–754)
- `vim.fn.has('win32') == 1` (Obsidian open image: Zeile 858–863)
- `vim.fn.has('win32') == 1` (Obsidian graph view: Zeile 934)
- `vim.fn.has('unix') == 1` (Markdown PDF export: Zeilen 4257–4316)
- `local is_win = vim.fn.has('win32') == 1` (E2E picker: Zeile 2017)
- `local is_win = vim.fn.has('win32') == 1` (Integration Test Picker: Zeile 2191)

---

## Datei-Struktur (Zeilen-Bereiche)

| Sektion | Start | Ende | Beschreibung |
|---------|-------|------|--------------|
| Kickstart Header | 1 | 85 | Großer Kommentar-Block |
| Globals | 87 | 111 | mapleader, have_nerd_font, notifications-toggle |
| SwapExists Autocmd | 113 | 120 | Swap-Datei-Konflikte ignorieren |
| .claude Auto-Copy | 122 | 164 | VimEnter: aus AgentsArchive kopieren (WIN+WSL) |
| Terminal-Hintergrundfarbe | 166 | 192 | Projekt-spezifische Farbe |
| Platform-Detection | 194 | 200 | `is_windows` Variable |
| find_dcsre_root() | 202 | 227 | Helper: DCSRE-Root dynamisch finden |
| Projekt-Detection | 229 | 275 | CENCOCD / DCSRE globals setzen |
| Vim-Options | 277 | 354 | Alle vim.o.* Einstellungen |
| Basic Keymaps | 356 | 432 | Standard Keymaps + Autocommands |
| Lazy.nvim Bootstrap | 434 | 447 | Lazy.nvim Installation |
| Lazy.setup() – Plugins | 449 | 3034 | Alle Plugin-Definitionen |
| Custom Keybindings | 3036 | 4539 | Projekt-Commands |
| Modeline | 4540 | 4541 | `vim: ts=2 sts=2 sw=2 et` |

### Plugin-Unterstruktur (innerhalb lazy.setup):

| Plugin | Start-Zeile (ca.) | Besonderheit |
|--------|-------------------|--------------|
| guess-indent | 462 | Shared |
| omnisharp-extended | 464 | C#-only |
| sonarqube.nvim | 471 | Env-var gesteuert, C#-only |
| neogit + diffview | 492 | Keybindings ab Zeile 502 |
| markdown-preview | 660 | WIN/WSL Chrome-Pfad-Unterschied! |
| obsidian.nvim | 702 | WIN/WSL Workspace-Pfade! |
| img-clip.nvim | 952 | Vault-Root Suche (Cross-Platform) |
| toggleterm | 1024 | Shared |
| vim-dadbod-ui | 1040 | Shared (Env-Vars für DB connections) |
| neotest | 1176 | Shared (dotnet + jest adapter) |
| undotree | 1237 | Shared |
| neo-tree | 1245 | Shared |
| aerial | 1307 | Shared |
| twilight | 1330 | Shared |
| zen-mode | 1340 | Shared |
| nvim-notify | 1362 | Shared |
| nvim-dap + dapui | 1384 | Zeile 1477: `.exe` nur auf Windows! |
| gitsigns | 1538 | Shared (reiche Keybindings) |
| which-key | 1709 | Shared |
| telescope | 1769 | E2E/Integration Picker: WIN/WSL! |
| lazydev | 2328 | Shared (lua LSP) |
| nvim-lspconfig + mason | 2341 | OmniSharp-extended handlers |
| conform | 2732 | Shared |
| blink.cmp | 2775 | LuaSnip build: WIN unterschied! Zeile 2788 |
| tokyonight | 2874 | Shared |
| catppuccin | 2890 | Shared |
| todo-comments | 2922 | Shared |
| mini.nvim | 2925 | Shared |
| nvim-treesitter | 2962 | Shared |

---

## Platform-spezifische Blöcke (ALLE is_windows / powershell / /mnt/c/ Stellen)

### Zeile 131–163: .claude Auto-Copy
```lua
-- Drei Archive-Pfade: Windows C:/, Git Bash /c/, WSL /mnt/c/
if vim.fn.has('win32') == 1 then
  vim.fn.system('powershell.exe -Command "Copy-Item ..."')
else
  vim.fn.system({ 'cp', '-r', archive_dir, claude_dir })
end
```

### Zeile 235–243: CENCOCD Projekt-Pfade
```lua
vim.g.project_backend = is_windows and 'C:/Users/...' or '/mnt/c/Users/...'
-- 6 verschiedene Pfad-Variablen mit is_windows Ternary
```

### Zeile 251–260: DCSRE Projekt-Pfade
```lua
vim.g.project_backend = dcsre_root .. '/Sources/Backend'  -- Shared (bereits normalisiert)
vim.g.project_root_windows = dcsre_root:gsub('/', '\\')  -- Nur Windows
vim.g.project_root_wsl = dcsre_root:gsub('C:', '/mnt/c') -- Nur WSL
```

### Zeile 680–694: Markdown Preview Chrome-Browser
```lua
if vim.fn.has('win32') == 1 then
  -- Windows: C:\Program Files\Google\Chrome\...
else
  -- WSL: /mnt/c/Program Files/Google/Chrome/...
end
```

### Zeile 745–754: Obsidian Workspaces
```lua
path = vim.fn.has('win32') == 1 and 'C:/Users/...' or '/mnt/c/Users/...'
-- 3 Workspaces: DCSRE, CenCoCo, Brain
```

### Zeile 858–863: Obsidian Follow Link (URL öffnen)
```lua
if vim.fn.has('win32') == 1 then
  vim.fn.system('start "" "C:\\Program Files\\Google\\Chrome\\..."')
else
  vim.fn.system('"/mnt/c/Program Files/Google/Chrome/..." &')
end
```

### Zeile 934: Obsidian Graph View
```lua
if vim.fn.has('win32') == 1 then
  vim.fn.system('start "" "' .. uri .. '"')
else
  vim.fn.system('xdg-open "' .. uri .. '"')
end
```

### Zeile 1477–1479: DAP netcoredbg Pfad
```lua
local netcoredbg_path = vim.fn.stdpath('data') .. '/mason/packages/netcoredbg/netcoredbg/netcoredbg'
if vim.fn.has('win32') == 1 then
  netcoredbg_path = netcoredbg_path .. '.exe'
end
```

### Zeile 2017–2110: E2E Test Picker (Telescope)
```lua
local is_win = vim.fn.has('win32') == 1
-- Cypress-Pfad: is_win and Windows-Backslash or Unix-Slash
-- cmd: powershell.exe vs bash
```

### Zeile 2191–2303: Integration Test Picker
```lua
local is_win = vim.fn.has('win32') == 1
local backend_root = is_win and vim.g.project_backend_windows or vim.g.project_backend
-- cmd: powershell.exe vs bash
```

### Zeile 2788: LuaSnip Build
```lua
if vim.fn.has 'win32' == 1 or vim.fn.executable 'make' == 0 then
  return  -- Kein make install_jsregexp auf Windows
end
```

### Zeile 3039–3051: Watch Backend
```lua
cmd = 'powershell.exe -Command "Set-Location ...; dotnet watch run ..."'
-- NUR Windows-Command! Kein Linux-Branch!
```

### Zeile 3067–3092: Run Backend WebHost
```lua
if vim.g.project_name == 'CENCOCD' then
  if is_windows then
    cmd = 'powershell.exe -Command ...'
  else
    cmd = 'cd ... && dotnet run ...'
  end
else  -- DCSRE
  if is_windows then
    cmd = 'powershell.exe ...'
  else
    cmd = 'cd ... && ASPNETCORE_URLS=...'
  end
end
```

### Zeile 3095–3109: Run Backend Setup
```lua
cmd = 'powershell.exe -Command "Set-Location ...; dotnet run ..."'
-- NUR powershell! Kein Linux-Branch!
```

### Zeile 3112–3122: Run Backend Build
```lua
cmd = 'powershell.exe -Command "Set-Location ...; dotnet build"'
-- NUR powershell!
```

### Zeile 3125–3144: Run Backend Tests
```lua
cmd = 'powershell.exe -Command "Set-Location ...; dotnet test ..."'
-- NUR powershell!
```

### Zeile 3147–3165: Run Backend Unit Tests
```lua
if vim.g.project_name == 'CENCOCD' then
  local sln = vim.g.project_root_windows .. '\\src\\CenCoCo.sln'
  cmd = "powershell.exe -Command \"dotnet test '" .. sln .. "' ...\""
else  -- DCSRE
  cmd = "powershell.exe -Command \"Set-Location '" .. vim.g.project_backend .. "'; ...\""
end
```

### Zeile 3207–3223: Run Frontend Web
```lua
if vim.g.project_name == 'CENCOCD' then
  cmd = 'powershell.exe -Command "Set-Location ...; dotnet run ..."'
else
  cmd = 'powershell.exe -Command "Set-Location ...; npm start"'
end
-- NUR powershell! Kein Linux-Branch!
```

### Zeile 3267–3380: E2E Keybindings (alle via powershell.exe)
```
<leader>reb, <leader>rei, <leader>reg, <leader>res, <leader>reo
```
Alle verwenden `powershell.exe -Command "cd '...'; ..."`.
Kein Linux-Branch vorhanden!

### Zeile 3384–3509: Docker Keybindings
```lua
-- rDi, rDa, rDr, rDR, rdf, rdF, rdb, rdB
-- Alle via powershell.exe
-- DCSRE: vim.g.project_docker_root_windows (Backslash-Pfade!)
-- CENCOCD: vim.g.project_docker_root (Forward-Slash möglich)
```

### Zeile 3511–3533: set_xunit_threads()
```lua
local xunit_file = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests\\xunit.runner.json'
-- Benutzt Windows-Backslash-Pfad explizit!
```

### Zeile 3539–3584: write_it_script()
```lua
local temp = os.getenv('TEMP') or os.getenv('TMP') or 'C:\\Users\\Administrator\\...'
-- Windows TEMP Variable! PowerShell-Script-Inhalt!
```

### Zeile 4057–4082: Yank Path Keybindings
```lua
-- <leader>yp: gsub('/', '\\') → immer Windows-Format
-- <leader>yP: '/mnt/c/' → 'C:\\' Konversion
-- <leader>ypw: WIN/WSL unterschiedlich
```

### Zeile 4254–4322: Markdown PDF Export
```lua
if vim.fn.has('unix') == 1 then
  chrome_path = '/mnt/c/Program Files/Google/Chrome/...'
else
  chrome_path = 'C:\\Program Files\\Google\\Chrome\\...'
end
-- PDF-Pfad-Konversion: /mnt/c → C:\
-- explorer.exe vs start ""
```

### Zeile 4436: TFS Browser öffnen
```lua
local cmd = 'powershell.exe -Command "Start-Process \'chrome.exe\' ..."'
-- Immer PowerShell!
```

### Zeile 4467: PR in Azure DevOps öffnen
```lua
local cmd = 'powershell.exe -Command "Start-Process \'C:\\Program Files\\Google\\Chrome\\...'"'
```

### Zeile 4473–4494: Git Push/Pull
```lua
cmd = 'powershell.exe -Command "cd ' .. vim.g.project_root_windows .. '; git push; pause"'
-- Immer PowerShell + Windows-Pfad!
```

### Zeile 4524–4538: .claude Setup Script
```lua
local win_path = git_root:gsub('^/mnt/(%a)/', function(drive) ... end):gsub('/', '\\')
-- WSL-zu-Windows-Pfad-Konversion, dann powershell.exe
```

---

## Shared Code (definitiv plattform-unabhängig)

- Zeilen 87–111: Leader, nerd_font, notification-toggle
- Zeilen 113–120: SwapExists autocmd
- Zeilen 277–354: Alle vim.o.* Settings
- Zeilen 356–432: Standard-Keymaps (hjkl, C-d/u, leader-q, etc.)
- Plugin-Configs: gitsigns, which-key, telescope (setup/defaults), lazydev, lspconfig, conform, blink.cmp, tokyonight, catppuccin, todo-comments, mini, treesitter
- LSP: LspAttach Autocmd (Zeilen 2388–2520), OmniSharp handlers (Zeilen 2438–2466)
- Diagnostic Filter (Zeilen 2522–2605)

---

## Test-Framework

### Status: Noch nichts vorhanden

Geplante Test-Infrastruktur:
- Framework: **plenary.nvim busted** (bereits als Dependency vorhanden via plenary.nvim)
- Test-Verzeichnis: `lua/spec/`
- Ausführung: `nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"`

### Was getestet werden soll:

1. **`find_dcsre_root()`** (Zeilen 202–227)
   - Input: `/mnt/c/work/DCSRE_Azure/DCSRE/Sources/Backend`
   - Expected: `/mnt/c/work/DCSRE_Azure/DCSRE`
   - Rand-Fälle: keine Sources, tief verschachtelter Pfad

2. **Projekt-Detection Logic** (Zeilen 229–268)
   - CENCOCD: Pfad enthält 'Kluger' → project_name == 'CENCOCD'
   - DCSRE: Pfad enthält 'DCSRE' → project_name == 'DCSRE'
   - Unknown: project_name == 'UNKNOWN'

3. **Platform-Pfad-Konversionen**
   - `/mnt/c/foo` → `C:\foo` (yP, rsc)
   - `C:\foo` → `C:/foo` (normalisierung)

---

## Schlüssel-Erkenntnisse

### 1. Fast alle Terminal-Commands nutzen powershell.exe
Die Mehrheit der `<leader>r*` Keybindings ruft `powershell.exe` auf – auch von WSL2 aus!
Das ist gewollt: VPN-Zugänglichkeit erfordert Windows-Kontext.
→ **Kein Linux-Branch** in vielen Keybindings vorhanden.
→ Beim Refactoring: diese Commands können in beiden Configs identisch sein (shared), aber Pfade müssen angepasst werden.

### 2. vim.g.project_root_windows ist kritisch
Viele Keybindings nutzen `vim.g.project_root_windows` mit Backslash-Pfaden.
Diese Variable wird in Zeilen 239/242/259 gesetzt.
→ Auf echtem Windows: `vim.g.project_root_windows` = `C:\Users\...` (ohne /mnt/c)
→ Auf WSL2: `vim.g.project_root_windows` = `C:\Users\...` (wird explizit so gesetzt für PowerShell-Aufrufe)

### 3. Obsidian Workspace-Pfade sind doppelt definiert
Für jeden Workspace gibt es einen Windows-Pfad UND einen WSL-Pfad via `vim.fn.has('win32')`.
→ Diese müssen beim Refactoring in platform-spezifische Blöcke.

### 4. Das DAP .exe-Suffix ist der einzige wirklich kritische OS-Unterschied in Plugins
```lua
if vim.fn.has('win32') == 1 then
  netcoredbg_path = netcoredbg_path .. '.exe'
end
```
Dieser Block muss erhalten bleiben.

### 5. Chrome-Pfade sind OS-spezifisch
- Windows: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- WSL2: `/mnt/c/Program Files/Google/Chrome/Application/chrome.exe`
→ Sollte in eine Konstante extrahiert werden.

### 6. Integration Test Infrastructure nutzt Windows TEMP
`os.getenv('TEMP')` = Windows TEMP Variable.
Von WSL2 aus funktioniert das auch (Windows TEMP ist in WSL sichtbar).
→ Kann shared bleiben.

### 7. LuaSnip build-Step ist auf Windows disabled
```lua
if vim.fn.has 'win32' == 1 or vim.fn.executable 'make' == 0 then return end
return 'make install_jsregexp'
```
→ Muss in der Platform-spezifischen Konfiguration oder als Shared-Block mit Check bleiben.

### 8. `is_windows` vs inline `vim.fn.has('win32')`
Manche Stellen nutzen die Variable, andere inline-Checks.
→ Beim Refactoring vereinheitlichen: Immer `is_windows` Variable nutzen.

### 9. Projekt-Detection läuft auf cwd basierend
```lua
local cwd = vim.fn.getcwd()
if cwd:match('Kluger') or cwd:match('CENCOCD') ...
```
→ Funktioniert identisch auf Windows und WSL2 (cwd-Format unterschiedlich, aber Pattern-Match auf String-Inhalt reicht).

### 10. Keine `init_windows.lua` mehr (veraltet in old_settings/)
CLAUDE.md sagt explizit: `init_windows.lua` ist veraltet!
→ Beim Refactoring: Die neue `init_windows.lua` ist NICHT die alte aus `old_settings/`.
