---
wave: exploration
agent: E02
focus: keybinding-architecture
status: final
primaerquelle_gelesen: true
---

# E02: Keybinding Architektur – Detaillierte Analyse

## Executive Summary

Die Keybinding-Logik (3036–4539) ist **streng nach funktionalen Gruppen organisiert**, jedoch mit erheblichen **Platform-spezifischen Unterschieden** in Terminal-Commands. Die Aufteilung in separate Dateien ist möglich und empfohlen, erfordert aber:

1. **Shared Basis**: Alle Commands haben identical Struktur (vim.keymap.set → Terminal → notify)
2. **Platform-Code**: Fast alle Terminal-Commands nutzen `powershell.exe` (auch von WSL2!)
3. **Projekt-Awareness**: Many Commands erkennen CENCOCD vs DCSRE und passen sich an
4. **kritische Pfad-Variablen**: `vim.g.project_*_windows` und `vim.g.project_*` müssen verfügbar sein

---

## Keybinding-Gruppen und Zuordnung

| Gruppe | Zeilen | Commands | Anzahl | Platform | Komplexität | Empfohlene Datei |
|--------|--------|----------|--------|----------|-------------|-----------------|
| **Backend** | 3067–3205 | rbw, rbs, rbb, rbt, rbu | 5 | shared+is_windows | **mittel** | `backend.lua` |
| **Frontend** | 3207–3265 | rfw, rfb, rft, rfi | 4 | shared+is_windows | **mittel** | `frontend.lua` |
| **E2E Tests** | 3276–3380 | reb, rei, reg, res, reo | 5 | **nur powershell** | **hoch** | `tests.lua` |
| **Docker** | 3384–3509 | rDi, rDa, rDr, rDR, rdf, rdF, rdb, rdB | 8 | shared+is_windows | **mittel** | `docker.lua` |
| **Integration Tests** | 3722–3900 | rim, rid, riC, riF, rif, ris | 6 | **komplexe Helpers** | **sehr hoch** | `tests.lua` (sub-gruppe) |
| **Git/TFS** | 4326–4494 | gyf, gyd, rc, rp, rP | 5 | **nur powershell** | **mittel** | `git.lua` |
| **Yank/Clipboard** | 4057–4219 | yp, yP, yn, dy, yd, yD, yww, ywW, yc, yi | 10 | **shared** | **niedrig** | `clipboard.lua` |
| **Watch Commands** | 3040–3064 | wb, bt | 2 | **nur powershell** | **niedrig** | `backend.lua` |

---

## Pro-Gruppe Analyse

### 1. Backend Keybindings (Zeilen 3067–3205)

**Commands**: `<leader>rbw`, `<leader>rbs`, `<leader>rbb`, `<leader>rbt`, `<leader>rbu`

**Struktur**:
```lua
vim.keymap.set('n', '<leader>rbw', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    if is_windows then
      cmd = 'powershell.exe -Command "..."'
    else
      cmd = 'cd ... && dotnet run ...'  -- WSL2 Branch
    end
  else  -- DCSRE
    if is_windows then
      cmd = 'powershell.exe -Command "..."'
    else
      cmd = 'cd ... && ASPNETCORE_URLS=... dotnet run ...'
    end
  end
  local webhost = Terminal:new({ cmd = cmd, ... })
  webhost:toggle()
end)
```

**Platform-Strategie**:
- ✅ **rbw** (WebHost): Hat BEIDE Windows + WSL2 Branches! → **kann shared sein**
- ❌ **rbs** (Setup): NUR powershell! → Aber: DCSRE-only → kann shared sein
- ❌ **rbb** (Build): NUR powershell! → kann shared sein
- ❌ **rbt** (Tests): NUR powershell! → kann shared sein
- ⚠️ **rbu** (Unit Tests): Projekt-aware (CENCOCD vs DCSRE) + nur powershell → kann shared sein

**Erkenntnisse**:
- `rbw` ist das **einzige Command mit echtem WSL2-Support** (Env-Variablen statt powershell)
- Andere Commands sind ALLE powershell-only (aber das ist absichtlich: vom WSL2 aus wird PowerShell aufgerufen!)
- **Shared mit is_windows**: JA, aber für manche Commands ist der else-Block dead code (nie erreicht von WSL2)

**Empfehlungen für Refactoring**:
```lua
-- backend.lua kann die is_windows-Logik BEHALTEN
-- Aber kennzeichnen: is_windows=true immer powershell, is_windows=false selten getestet
-- Kritisch: vim.g.project_backend, vim.g.project_webhost müssen geladen sein
```

---

### 2. Frontend Keybindings (Zeilen 3207–3265)

**Commands**: `<leader>rfw`, `<leader>rfb`, `<leader>rft`, `<leader>rfi`

**Struktur**:
```lua
if vim.g.project_name == 'CENCOCD' then
  cmd = 'powershell.exe -Command "Set-Location ...; dotnet run"'
else
  cmd = 'powershell.exe -Command "Set-Location ...; npm start"'
end
```

**Platform-Strategie**:
- ✅ **rfw**: Projekt-aware (CENCOCD dotnet vs DCSRE npm) → kann shared sein
- ❌ **rfb**: projekt-aware (CENCOCD docker compose build vs DCSRE npm run build) → NUR powershell
- ❌ **rft**: Immer `npm test` via powershell → kann shared sein
- ❌ **rfi**: Immer `npm install` via powershell → kann shared sein

**Erkenntnisse**:
- Alle Command nutzen **nur powershell.exe**, kein WSL2-Branch
- CENCOCD vs DCSRE Unterscheidung ist wichtig (rfb ist sehr unterschiedlich!)
- Frontend-Pfad über `vim.g.project_frontend` ermittelt

**Empfehlung**:
```lua
-- frontend.lua sollte project-aware bleiben, aber PowerShell nur
-- Kritisch: vim.g.project_frontend (gut definiert in Projekt-Detection)
```

---

### 3. E2E Test Keybindings (Zeilen 3276–3380)

**Commands**: `<leader>reb`, `<leader>rei`, `<leader>reg`, `<leader>res`, `<leader>reo`

**Helper**: `get_cypress_path_windows()` (Zeile 3268)

**Struktur**:
```lua
local cypress_path = get_cypress_path_windows()
if not cypress_path then
  vim.notify('Could not determine Cypress path', vim.log.levels.ERROR)
  return
end
local Terminal = require('toggleterm.terminal').Terminal
local cmd = "powershell.exe -Command \"cd '" .. cypress_path .. "'; npm run cypress:run:gesamtsystemtest\""
```

**Platform-Strategie**:
- ❌ **ALLE E2E Commands**: NUR powershell! Kein WSL2-Branch!
- ❌ **DCSRE-only**: Alle Commands überprüfen `vim.g.project_name ~= 'DCSRE'`
- ⚠️ **cypress_path Helper**: Sucht `/Sources/Tests/Cypress` relativ zu `vim.g.project_root_windows`

**Erkenntnisse**:
- E2E ist DCSRE-only → alle Commands können schnell aus CENCOCD aussteigen
- Cypress-Pfad ist Backslash-basiert (Windows) → funktioniert aber auch von WSL2 aus
- npm-Scripts sind projekt-spezifisch (`cypress:run:gesamtsystemtest`, `cypress:open:systemtest`, etc.)

**Empfehlung**:
```lua
-- tests.lua sollte E2E als eigene Sub-Gruppe haben
-- Helper: get_cypress_path_windows() kann STATISCH in tests.lua definiert werden
-- DCSRE-Check am Anfang jeder Funktion ist akzeptabel
```

---

### 4. Docker Keybindings (Zeilen 3384–3509)

**Commands**: `<leader>rDi`, `<leader>rDa`, `<leader>rDr`, `<leader>rDR`, `<leader>rdf`, `<leader>rdF`, `<leader>rdb`, `<leader>rdB`

**Struktur**:
```lua
if vim.g.project_name == 'DCSRE' then
  cmd = 'powershell.exe -ExecutionPolicy Bypass -Command "Set-Location \''
    .. vim.g.project_docker_root_windows .. '\'; .\\docker-up.ps1 ..."'
else
  cmd = 'powershell.exe -Command "Set-Location \''
    .. vim.g.project_docker_root .. '\'; docker compose up -d"'
end
```

**Platform-Strategie**:
- ❌ **ALLE Docker Commands**: NUR powershell!
- ⚠️ **DCSRE vs CENCOCD**: Sehr unterschiedlich!
  - DCSRE: Komplexes `docker-up.ps1`-Script mit Parametern, Notifications, Env-Files
  - CENCOCD: Einfaches `docker compose up -d`
- ⚠️ **Pfad-Unterschiede**: DCSRE nutzt `vim.g.project_docker_root_windows` (Backslash!), CENCOCD nutzt `vim.g.project_docker_root`

**Erkenntnisse**:
- Docker-Infrastruktur ist so unterschiedlich, dass ein **if/else pro Command** notwendig ist
- ExecutionPolicy Bypass nur bei DCSRE-PowerShell-Scripts notwendig
- CENCOCD Docker ist deutlich einfacher

**Empfehlung**:
```lua
-- docker.lua sollte project-aware sein
-- DCSRE und CENCOCD sollten separate Blöcke haben (oder Helper-Functions)
-- Kritisch: vim.g.project_docker_root_windows, vim.g.project_docker_root
```

---

### 5. Integration Test Keybindings (Zeilen 3511–3900)

**Commands**: `<leader>rim`, `<leader>rid`, `<leader>riC`, `<leader>riF`, `<leader>rif`, `<leader>ris`

**Helper-Functions**:
- `set_xunit_threads(threads)` (Zeile 3512) – ✅ Sehr komplex! Modifiziert JSON-Datei
- `write_it_script(filter, label, extra_flags)` (Zeile 3539) – ✅ Erzeugt PowerShell-Script
- `parse_trx_results()` (Zeile 3615) – ✅ Parst XML/TRX-Datei
- `run_integration_tests(filter, label, threads, terminal_id)` (Zeile 3588) – ✅ Wrapper
- `telescope_test_picker(title, test_list)` (Zeile 3645) – ✅ Telescope-Integration

**Platform-Strategie**:
- ❌ **DCSRE-ONLY**: Alle Integration-Test-Commands sind für DCSRE
- ⚠️ **CENCOCD-Teilweise**: `<leader>rid` hat einen CENCOCD-Branch (Stufe 3 IsolatedDocker)
- ❌ **Sehr komplex**: xunit.runner.json Modifikation, TRX-Parsing, PowerShell-Script-Generierung

**Erkenntnisse**:
- Dieses ist die **komplexeste Keybinding-Gruppe**
- `set_xunit_threads()` ist nicht portabel (Windows-spezifisches JSON-File mit Backslash-Pfad)
- `write_it_script()` generiert echte PowerShell-Skripte mit Formatierung
- TRX-Parsing via PowerShell (`[xml]$r = Get-Content ...`)
- Telescope-Integration ist elegant aber nur für DCSRE definiert

**Empfehlung**:
```lua
-- tests.lua sollte Integration Tests als SEPARATE Sub-Gruppe haben
-- Diese Helpers MÜSSEN mit in die Datei:
--   - set_xunit_threads()
--   - write_it_script()
--   - parse_trx_results()
--   - run_integration_tests()
--   - telescope_test_picker()
-- DCSRE-Check ist notwendig!
-- Kritisch: vim.g.project_backend_windows, TEMP-Pfade
```

---

### 6. Git/TFS Keybindings (Zeilen 4326–4494)

**Commands**: `<leader>gyf`, `<leader>gyd`, `<leader>rc`, `<leader>rp`, `<leader>rP`

**Struktur**:
```lua
-- <leader>gyf: Git Yank File diff
vim.keymap.set('n', '<leader>gyf', function()
  local file = vim.fn.expand('%:.')
  local base_ref = vim.g.project_git_base  -- 'origin/develop' or 'origin/main'
  local diff = vim.fn.system('git diff ' .. base_ref .. '...HEAD -- "' .. file .. '"')
  vim.fn.setreg('+', diff)
end)

-- <leader>gyd: Git Yank entire branch Diff
vim.keymap.set('n', '<leader>gyd', function()
  local diff = vim.fn.system('git diff ' .. vim.g.project_git_base .. '...HEAD')
  vim.fn.setreg('+', diff)
end)

-- <leader>rc: Open commit in TFS
vim.keymap.set('n', '<leader>rc', function()
  local hash = vim.fn.getreg('+')
  local url = vim.g.project_tfs_commit_url:gsub('{hash}', hash)
  local cmd = 'powershell.exe -Command "Start-Process \'chrome.exe\' \'' .. url .. '\'"'
  vim.fn.system(cmd)
end)

-- <leader>rp, <leader>rP: Git push/pull
vim.keymap.set('n', '<leader>rp', function()
  local cmd = 'powershell.exe -Command "cd ' .. vim.g.project_root_windows .. '; git push; pause"'
  local Terminal = require('toggleterm.terminal').Terminal
  local push = Terminal:new({ cmd = cmd, ... })
  push:toggle()
end)
```

**Platform-Strategie**:
- ✅ **gyf, gyd**: Plattform-unabhängig (nur `git diff` via vim.fn.system) → **shared!**
- ❌ **rc**: Öffnet Chrome via PowerShell → NUR Windows/PowerShell
- ❌ **rp, rP**: Push/Pull via PowerShell → NUR Windows/PowerShell (VPN-Anforderung!)

**Erkenntnisse**:
- `git diff` Commands können **identisch shared** sein!
- TFS/Git Push benötigt PowerShell wegen VPN
- `vim.g.project_git_base` wird automatisch erkannt (CENCOCD='main', DCSRE='develop')
- `vim.g.project_tfs_commit_url` ist projekt-spezifisch

**Empfehlung**:
```lua
-- git.lua kann aufgeteilt werden:
--   1. Shared Part: gyf, gyd (reine git commands)
--   2. Windows Part: rc, rp, rP (PowerShell + Chrome)
-- Aber: Bei Unified init.lua einfach ist_windows-Check
```

---

### 7. Yank/Clipboard Keybindings (Zeilen 4057–4219)

**Commands**: `<leader>yp`, `<leader>yP`, `<leader>yn`, `<leader>dy`, `<leader>yd`, `<leader>yD`, `<leader>yww`, `<leader>ywW`, `<leader>yc`, `<leader>yi`

**Struktur**:
```lua
-- <leader>yp: Copy relative filepath (Windows format)
vim.keymap.set('n', '<leader>yp', function()
  local filepath = vim.fn.expand('%')
  filepath = filepath:gsub('/', '\\')  -- Zu Windows umwandeln
  vim.fn.setreg('+', filepath)
end)

-- <leader>yP: Copy absolute Windows path
vim.keymap.set('n', '<leader>yP', function()
  local filepath = vim.fn.expand('%:p')
  filepath = filepath:gsub('^/mnt/(%a)/', function(drive)
    return drive:upper() .. ':\\'
  end)
  filepath = filepath:gsub('/', '\\')
  vim.fn.setreg('+', filepath)
end)

-- <leader>yd: Copy diagnostic (path:line msg)
-- <leader>yc: Copy git diff for current file
-- <leader>yi: Copy all diagnostics
```

**Platform-Strategie**:
- ✅ **ALLE**: Plattform-unabhängig (oder haben bereits is_windows-Logik) → **100% shared!**
- ⚠️ **yp, yP**: Explizite Windows-Format-Konvertierung → aber das ist **gewollt**!
- ✅ **yc, yi, yd**: reine Vim-Buffer/Diagnostic-Operationen → **shared**

**Erkenntnisse**:
- Diese Gruppe ist am **einfachsten zu refaktorieren**!
- Alle Commands sind **100% shared** (keine PowerShell, keine Projekt-Logik)
- Windows-Format-Konvertierung ist absichtlich (für Clipboard-Integration mit Windows-Tools)

**Empfehlung**:
```lua
-- clipboard.lua: Sehr clean, kann als-is extrahiert werden
-- Keine Dependencies außer vim.fn, vim.diagnostic
-- Kann auch in kleinerere Dateien aufgeteilt werden, aber nicht notwendig
```

---

### 8. Watch Commands (Zeilen 3040–3064)

**Commands**: `<leader>wb`, `<leader>bt`

**Struktur**:
```lua
vim.keymap.set('n', '<leader>wb', function()
  local cmd = 'powershell.exe -Command "Set-Location \''
    .. vim.g.project_webhost .. '\'; dotnet watch run' .. profile_arg .. '"'
  local watch = Terminal:new({ cmd = cmd, ... })
  watch:toggle()
end)
```

**Platform-Strategie**:
- ❌ **BEIDE**: NUR powershell! Kein WSL2-Branch!
- ⚠️ **wb**: Nutzt `vim.g.project_launch_profile` (optional)
- ⚠️ **bt**: Hardcoded `dotnet watch test` (keine Logik)

**Erkenntnisse**:
- Diese sind **sehr einfach**, können mit Backend zusammen gehen
- Keine Projekt-Logik notwendig

**Empfehlung**:
```lua
-- backend.lua kann diese mit aufnehmen
-- Oder in separate "watch.lua", aber nicht notwendig
```

---

## Kritische Erkenntnisse

### 1. **Fast ALLE Commands nutzen powershell.exe**

Selbst von WSL2 aus werden Terminal-Commands via PowerShell ausgeführt. Das ist gewollt wegen:
- VPN-Zugänglichkeit (Git Push/Pull)
- Projekt-Konsistenz (alle Devs nutzen die gleichen Pfade)
- Windows-Tools (Docker Desktop, Chrome)

→ **Refaktorierungs-Implikation**: `is_windows` in keybindings nicht nötig, ABER:
- Commands können in shared Datei sein
- Pfad-Variablen müssen für powershell.exe optimiert sein (Backslash!)

### 2. **vim.g.project_* Variablen sind KRITISCH**

Folgende Variablen MÜSSEN vor keybindings.lua geladen sein:
- `vim.g.project_name` (DCSRE oder CENCOCD)
- `vim.g.project_backend`, `vim.g.project_backend_windows`
- `vim.g.project_frontend`
- `vim.g.project_webhost`
- `vim.g.project_docker_root`, `vim.g.project_docker_root_windows`
- `vim.g.project_git_base` (develop oder main)
- `vim.g.project_tfs_commit_url`
- `vim.g.project_launch_profile`

**Architektur-Problem**: Diese werden in init.lua Zeilen 229–268 gesetzt (vor keybindings!)
→ Bei Modularisierung müssen diese WEITERHIN vor keybindings/init.lua geladen werden!

### 3. **Integration Tests sind EXTREMST komplex**

Die Helpers (`set_xunit_threads`, `write_it_script`, `parse_trx_results`) sind:
- Windows-spezifisch (JSON-Modifikation, TRX-Parsing)
- PowerShell-abhängig (Script-Generierung)
- Projekt-spezifisch (DCSRE-only)
- Über 200 Zeilen Code

→ Diese **können nicht einfach in keybindings/tests.lua extrahiert werden**, sondern brauchen eigenes Modul (z.B. `lua/shared/integrationtests.lua`)

### 4. **CENCOCD vs DCSRE Unterschiede sind größer als gedacht**

| Feature | DCSRE | CENCOCD |
|---------|-------|---------|
| Backend Lang | C# (dotnet) | C# (Blazor WebAssembly) |
| Frontend | Angular + NX (npm) | Blazor (dotnet) |
| Docker | Komplex (PowerShell script + Env-Files) | Einfach (docker compose) |
| Integration Tests | Ja (xunit, TRX) | Nein (nur category filter) |
| E2E Tests | Ja (Cypress) | Nein |
| Git Base | origin/develop | origin/main |

→ **Refaktorierungsansatz**: Nicht nach Platform (Windows/WSL2), sondern nach **Projekt** (DCSRE/CENCOCD) strukturieren!

### 5. **WSL2-Branch ist SELTEN wirklich vorhanden**

Beispiele von "WSL2-Unterstützung":
- `rbw` (WebHost): ✅ **Echter WSL2-Branch mit Env-Variablen**
- Alle anderen Backend/Frontend/Docker/Test Commands: ❌ **NUR PowerShell, kein WSL2-Branch**

→ **Realität**: Der WSL2-Pfad in vielen Commands ist **dead code**, der nie getestet wird!
→ **Empfehlung**: Beim Refactoring klare Markierung setzen, welche Commands wirklich WSL2-ready sind

---

## Empfehlung: Datei-Struktur für keybindings/

### Option A: Nach Funktionalität (EMPFOHLEN)

```
lua/shared/keybindings/
├── init.lua                 # Main entry: require() alle anderen
├── backend.lua              # rbw, rbs, rbb, rbt, rbu + wb, bt
├── frontend.lua             # rfw, rfb, rft, rfi
├── docker.lua               # rDi, rDa, rDr, rDR, rdf, rdF, rdb, rdB
├── tests.lua                # E2E (reb, rei, reg, res, reo) + Integration (rim, rid, riC, riF, rif, ris)
├── git.lua                  # gyf, gyd, rc, rp, rP
├── clipboard.lua            # yp, yP, yn, dy, yd, yD, yww, ywW, yc, yi
├── integrationtests.lua     # Helpers: set_xunit_threads, write_it_script, parse_trx_results, run_integration_tests
└── helpers.lua              # get_cypress_path_windows, git_diff_to_quickfix, etc.
```

### Option B: Nach Plattform (NICHT EMPFOHLEN)

→ Wäre zu komplex, da vieles cross-platform ist. Nicht sinnvoll!

### Option C: Nach Projekt (TEILWEISE SINNVOLL)

```
lua/shared/keybindings/
├── shared.lua               # Alles Projekt-unabhängige (yank, git diff, etc.)
├── dcsre.lua                # DCSRE-spezifisch (Integration, E2E, Docker PowerShell-Script)
└── cencocd.lua              # CENCOCD-spezifisch (Blazor, einfaches Docker)
```

→ **Nicht empfohlen**: Würde Code-Duplikation führen (Backend für beide Projekte ähnlich)

---

## Konkrete Empfehlungen für Refactoring

### 1. **Abhängigkeits-Reihenfolge in init.lua**

```lua
-- Zeile 229–268 (BLEIBEN WIE IST)
-- Projekt-Detection + vim.g.project_* Variablen setzen

-- Zeile 277–354 (BLEIBEN WIE IST)
-- Vim-Options

-- Zeile 356–432 (BLEIBEN WIE IST)
-- Basic Keymaps

-- Neue Struktur für Custom Keybindings (Zeile 3036+):
require('shared.keybindings')  -- <- NEW: Lädt alle keybindings

-- Zeile 4540 (BLEIBT)
-- Modeline
```

### 2. **keybindings/init.lua Struktur**

```lua
-- lua/shared/keybindings/init.lua
local is_windows = vim.fn.has('win32') == 1  -- Wird auch hier geladen!

-- Import alle Submodule
require('shared.keybindings.backend')
require('shared.keybindings.frontend')
require('shared.keybindings.docker')
require('shared.keybindings.tests')
require('shared.keybindings.git')
require('shared.keybindings.clipboard')

-- Helpers sind optional public (z.B. für Tests)
_G.keybinding_helpers = require('shared.keybindings.helpers')
```

### 3. **Critical Path: Integration Tests Module**

```lua
-- lua/shared/integrationtests.lua (NICHT in keybindings/)
-- Dieser Module muss VOR keybindings/tests.lua geladen werden!

local M = {}

function M.set_xunit_threads(threads)
  -- ... komplexe Implementierung ...
end

function M.write_it_script(filter, label, extra_flags)
  -- ... komplexe Implementierung ...
end

-- ... weitere Helpers ...

return M
```

```lua
-- lua/shared/keybindings/tests.lua
local IT = require('shared.integrationtests')

vim.keymap.set('n', '<leader>rim', function()
  vim.ui.input({ prompt = 'Parallel threads (default 38): ' }, function(input)
    if input == nil then return end
    local threads = tonumber(input) or 38
    IT.run_integration_tests(...)
  end)
end)
```

### 4. **Platform-Check: Unified Approach**

```lua
-- lua/shared/keybindings/backend.lua
local is_windows = vim.fn.has('win32') == 1

vim.keymap.set('n', '<leader>rbw', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd

  if vim.g.project_name == 'CENCOCD' then
    -- CENCOCD Logic
    cmd = is_windows and
      'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; ..."' or
      'cd ' .. vim.g.project_webhost .. ' && dotnet run --launch-profile https'
  else
    -- DCSRE Logic
    cmd = is_windows and
      'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; ..."' or
      'cd ' .. vim.g.project_webhost .. ' && ASPNETCORE_URLS=... dotnet run'
  end

  local webhost = Terminal:new({ cmd = cmd, direction = 'horizontal', close_on_exit = false })
  webhost:toggle()
end, { desc = '...' })
```

→ **ist_windows** wird in JEDEM Keybindings-File geladen (oder centralized), nicht dupliziert!

---

## Zusammenfassung: Sharing-Matrix

| Datei | Kann Shared sein | Grund | Abhängigkeiten |
|-------|-----------------|-------|-----------------|
| `backend.lua` | ⚠️ **Ja, mit is_windows** | Eine rbw hat WSL2, andere nicht | vim.g.project_* |
| `frontend.lua` | ⚠️ **Ja, mit is_windows** | rfw projekt-aware; andere nur powershell | vim.g.project_* |
| `docker.lua` | ⚠️ **Ja, mit is_windows + project-aware** | DCSRE vs CENCOCD Unterschied |vim.g.project_docker_root* |
| `tests.lua` (E2E) | ⚠️ **Ja** | DCSRE-only, kein WSL2-Branch | get_cypress_path_windows() |
| `tests.lua` (Integration) | ❌ **Bedingt (mit Helpers)** | set_xunit_threads() ist Windows-only, aber logisch kann es shared sein | integrationtests.lua Module |
| `git.lua` | ✅ **Ja (teilweise)** | gyf/gyd shared, rc/rp/rP nur powershell | vim.g.project_git_base, project_tfs_commit_url |
| `clipboard.lua` | ✅ **Ja, 100%** | Keine Abhängigkeiten außer vim.fn | Keine! |

---

## Letzte Warnung: Dead Code in WSL2

Mehrere Commands haben `is_windows` Check mit `else`-Branch, der von WSL2 aus **niemals getestet** wird, weil:
1. Im WSL2 wird `powershell.exe` aus Bash heraus aufgerufen
2. Das funktioniert, aber der `is_windows=false` Branch wird nicht erreicht
3. Der Code ist wahrscheinlich **obsolet/bitrot**

**Beispiel**: `<leader>rbb` (Backend Build)
```lua
cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; dotnet build"'
-- Kein else-Branch! Nur powershell!
```

→ Beim Refactoring sollten solche Commands klar dokumentiert werden: **"Nur Windows/PowerShell"**
