---
wave: drafts
agent: D03
focus: migration-order-and-gap
status: final
primaerquelle_gelesen: true
date: 2026-03-02
---

# D03: Migrations-Reihenfolge + GAP-Vorschau

## Verifikation Primärquellen

✅ Gelesen: `init.lua` (4541 Zeilen) - strategische Schnitte Zeilen 1-100, 200-268, 3000-3200
✅ Gelesen: Grep-Muster für `is_windows`, `powershell.exe`, `/mnt/c/`, `CENCOCD`, `DCSRE`
✅ Bestätigt: E05 und E02 Findings sind akkurat

---

## 1. LOC-Analyse (Echte Zahlen)

### Kickstart Boilerplate (unveränd., ~100 Zeilen)
- Zeilen 1-100: Comments, license, README-Text
- **Befund**: Reine Kickstart-Dokumentation, kann als-ist behalten werden

### Shared Core (Basis Neovim-Config, ~2800 Zeilen)
**Definitionen:**
- vim.o.* (options)
- Keymaps (standard, nicht projekt-spezifisch)
- Lazy.nvim plugin-setup (ohne platform-check)
- Telescope, LSP (omnisharp ohne spezialisierung)
- Theme/Colors
- Auto-Befehle (generisch)

**Zeile-Ranges geschätzt:**
- vim.o settings: Zeilen 277-420 (~143 Zeilen)
- Standard Keymaps: Zeilen 380-427 (~47 Zeilen)
- require('lazy').setup: Zeilen 460-3034 (~2574 Zeilen)
  - Plugin-Specs sind 95% cross-platform
  - Lazy-Config ist 100% platform-agnostic

**→ ~2900 Zeilen Shared Code**

### Project Detection (CENCOCD vs DCSRE, ~70 Zeilen)
- Zeilen 200-276
- `local is_windows = ...` (1 Zeile)
- `find_dcsre_root()` helper (26 Zeilen)
- CENCOCD-Config: Zeilen 232-245 (14 Zeilen)
- DCSRE-Config: Zeilen 246-268 (22 Zeilen)

**Beobachtung**: Projekt-Trennung dominiert über Platform-Trennung!
- CENCOCD: `git_base = 'origin/main'`, HTTPS profile
- DCSRE: `git_base = 'origin/develop'`, WebHost profile
- DCSRE: 5 extra `project_*_windows` Varianten (Backslash-Paths)

**→ ~70 Zeilen, aber mit 3 separate Blöcke pro Projekt**

### Windows-Spezifisch (powershell + C:/ Paths, ~350 Zeilen)
**Typ A: is_windows Ternary (path conversion)**
- Zeilen 235-238: 4 × CENCOCD paths
- Zeilen 251-256: 6 × DCSRE paths
- Zeilen 745, 749, 753: obsidian/notes paths (3×)
- **Summe Ternary Operatoren**: ~13 × 2 Zeilen = 26 Zeilen Code

**Typ B: if is_windows then ... else ... end (Befehlsausführung)**
- Zeilen 3071-3075: rbw (Backend WebHost) - CENCOCD-spezifisch
- Zeilen 3078-3082: rbw (Backend WebHost) - DCSRE-spezifisch
- **Befund**: Nur 2 full-if blocks in Keybindings!

**Typ C: powershell.exe -Command Zeilen**
- Grep-Fund: 68 × `powershell.exe` in gesamtem Code
- Davon ~55 × in Keybindings (3035-3650)
- **Problem**: Alle keybindings nutzen `powershell.exe`, keine Linux-Alternative!

**Typ D: C:/ absolute paths in Keybindings**
- Zeilen 3389, 3395, 3401: docker paths (3×)
- Zeilen 3152, 3171: `project_root_windows` (2×)
- **Summe**: ~20 Zeilen mit C:/ oder Backslash

**→ ~350 Zeilen (davon 68 × powershell.exe, 20 × C:/ paths, 13 × ternary)**

### Linux-Spezifisch (/mnt/c/ Paths, xdg-open, ~40 Zeilen)
- Zeile 235-238: /mnt/c/ Alternativen (ternary Rechtsseite)
- Zeile 691: `/mnt/c/Program Files/Google/Chrome` (1 Zeile)
- Zeile 862: `/mnt/c/Program Files/Google/Chrome` (1 Zeile)
- Zeile 937: `xdg-open` statt `Start-Process` (1 Zeile)
- Zeile 3074, 3081: Linux-Bash Befehle in rbw (2 Zeilen)

**→ ~40 Zeilen (davon 2 full-if blocks für Commands)**

### Is_Windows Ternary Blöcke (Pfad-Conversion)
- **Zählung**: 12 Stellen mit `if is_windows` oder `is_windows and ... or`
- **Davon**:
  - 6 × in Project Detection (CENCOCD 4×, DCSRE 2×)
  - 3 × in Obsidian/Notes paths
  - 3 × in Keybindings (rbu line 3152, rii line 3171, etc.)

**→ ~30 Zeilen Ternary Code (sparse, nur Pfade)**

---

## 2. Neue Datei-Größen (Schätzung)

### init.lua (Dispatcher, 15 Zeilen)
```lua
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '
vim.g.have_nerd_font = false
vim.g.notifications_enabled = true
-- ... notification function (5 Zeilen)

-- Determine platform
local is_windows = vim.fn.has('win32') == 1

-- Load shared config
require('lua.shared.core')

-- Load platform-specific config
if is_windows then
  require('lua.shared.init_windows')
else
  require('lua.shared.init_linux')
end
```
**→ 15 Zeilen (Dispatcher-Pattern)**

### lua/shared/core.lua (~2900 Zeilen)
- vim.o settings
- Standard Keymaps
- require('lazy').setup mit allen Plugins
- **100% current init.lua ohne Platform-Checks**

### lua/shared/init_windows.lua (~1200 Zeilen)
**Enthält:**
- Project detection (CENCOCD + DCSRE, Zeilen 200-268 aus init.lua) = 70 Zeilen
- Alle `<leader>r*` Keybindings mit `powershell.exe` (Zeilen 3035-3650) = ~615 Zeilen
- Alle Docker Keybindings (Zeilen 3380-3520) = ~140 Zeilen
- Windows-spezifische Helpers (xdg-open alternatives)

**→ ~1200 Zeilen**

### lua/shared/init_linux.lua (~800 Zeilen)
**Enthält:**
- Project detection (SAME wie Windows! CENCOCD + DCSRE) = 70 Zeilen
- Alle `<leader>r*` Keybindings mit `bash` statt `powershell.exe` (adapted) = ~615 Zeilen
- Linux-spezifische Helpers (`xdg-open` statt `Start-Process`)
- **Beobachtung**: 95% Code ist identisch, nur Shell-Syntax unterscheidet sich

**→ ~800 Zeilen**

### lua/shared/ Gesamt
- core.lua: 2900
- init_windows.lua: 1200
- init_linux.lua: 800
- **Gesamt**: 4900 Zeilen (vs. 4541 aktuell)

**→ +359 Zeilen nur wegen Duplikation von Project Detection + shared Keybindings!**

---

## 3. Validierte Migrations-Reihenfolge

### E05 Plan (8 Schritte) - VALIDIERUNG:

| Schritt | Original E05 | Validierung | Bedenken |
|---------|--------------|------------|----------|
| 1 | Test-Infra | ✅ RICHTIG | Läuft unabhängig, kann als erstes |
| 2 | project.lua extrahieren | ⚠️ SPÄTER | Hängt von vim.g.* ab, braucht core.lua zuerst |
| 3 | core.lua (lazy + plugins) | ✅ RICHTIG | Sollte Schritt 1 sein, erzeugt vim.g |
| 4 | Shared Keymaps | ⚠️ FALSCH | Braucht lazy.setup + plugin-loads |
| 5 | init_windows.lua | ✅ RICHTIG | Nach core.lua, importiert project.lua |
| 6 | init_linux.lua | ✅ RICHTIG | Identisch zu init_windows |
| 7 | Cleanup + Testen | ✅ RICHTIG | Als letztes |

**MEINE Validierte Reihenfolge:**

```
Phase 1: Infrastructure (5h)
  S1: Test-Suite einrichten (Unit + Integration)
       → Smoke-Test für core.lua Funktionieren
  S2: Dispatcher (init.lua) schreiben
       → Minimal: Lazy.setup aufrufen
  S3: core.lua extrahieren (lazy.nvim + Plugins)
       → Kein is_windows, kein project_name
       → require('lazy').setup({...})

Phase 2: Platform Abstraction (2h)
  S4: project.lua extrahieren
       → find_dcsre_root() helper
       → vim.g.project_* Variablen setzen
       → Verwendet ist_windows intern
  S5: init_windows.lua extrahieren
       → Zeilen 1-70 (project detection aus init.lua)
       → Zeilen 3035-3650 (Keybindings mit powershell.exe)
       → Alle C:/ Paths
  S6: init_linux.lua extrahieren
       → Identisch zu init_windows, nur bash statt powershell
       → Alle /mnt/c/ Paths

Phase 3: Integration & Validation (2h)
  S7: Cleanup alt init.lua
  S8: Smoke-Tests + WSL2-Tests
```

**Begründung:**
- Schritt 2+3 sind reversible (Lazy.nvim lädt parallel, Fehler früh erkannt)
- Schritt 4 muss VOR 5+6 kommen (werden in init_windows/linux require()d)
- Schritt 5+6 sind isoliert → können parallel entwickelt werden

---

## 4. CENCOCD vs DCSRE: Lohnt Trennung?

### Analyse Primärquellen (Zeilen 232-268)

**CENCOCD Block (14 Zeilen):**
```lua
vim.g.project_name = 'CENCOCD'
vim.g.project_backend = is_windows and 'C:/Users/.../Kluger/cencoco/src/Core/CenCoCo.Core.API' or '/mnt/c/.../Kluger/cencoco/src/Core/CenCoCo.Core.API'
-- 11 weitere vim.g.* Variablen
```
- `project_git_base = 'origin/main'`
- `project_launch_profile = 'https'`
- `project_tfs_commit_url = nil` (TODO)

**DCSRE Block (22 Zeilen):**
```lua
local dcsre_root = find_dcsre_root(cwd)  -- Smart detection!
vim.g.project_name = 'DCSRE'
-- 14 weitere vim.g.* Variablen
-- Davon: 3× `project_*_windows` (extra)
-- Davon: 3× TFS URL Kommentare
```
- `project_git_base = 'origin/develop'`
- `project_launch_profile = 'WebHost'`
- `project_tfs_commit_url = 'https://dev.azure.com/...'`

### Keybindings-Analyse (Zeilen 3067-3165)

**`<leader>rbw` (Backend WebHost):**
```lua
if vim.g.project_name == 'CENCOCD' then
  if is_windows then
    -- CENCOCD: powershell + --launch-profile https
  else
    -- CENCOCD: bash + --launch-profile https
  end
else  -- DCSRE
  if is_windows then
    -- DCSRE: powershell + Env-Variablen + --no-restore
  else
    -- DCSRE: bash + Env-Variablen + --no-restore
  end
end
```

**`<leader>rbu` (Unit Tests):**
```lua
if vim.g.project_name == 'CENCOCD' then
  -- CenCoCo Stufe 1: --filter Category!=IsolatedDocker&Category!=IntegrationTests
else
  -- DCSRE: --filter Category!=Database&Category!=Storage&Category!=Docker
end
```

**`<leader>rii` (Integration InMemory):**
```lua
if vim.g.project_name == 'CENCOCD' then
  -- Integration Tests (Stufe 2)
else
  vim.notify('Use <leader>rid for DCSRE integration tests')
end
```

### Befund:

| Kategorie | Unterschied | Komplexität |
|-----------|------------|------------|
| **Projekt-Detection** | Path + git_base + launch_profile | MITTEL |
| **Keybindings** | 50+ Commands, davon 6+ mit if-Project-Check | HOCH |
| **Docker** | DCSRE: docker-up.ps1, CENCOCD: docker compose | HOCH |
| **Tests** | Stufe 1/2 vs. Category-Filter | HOCH |
| **TFS URLs** | Unterschiedliche Base URLs | NIEDRIG |

### **KONKLUSION: JA, Trennung lohnt sich!**

**Grund 1: Kognitives Overload**
- Ein Keybinding verwaltet 2 Projekt-Varianten + 2 Platform-Varianten = 4 Branches
- 50+ Keybindings = potentiell 200+ Branches!
- Zu error-prone → ein Typo in CENCOCD betrifft auch DCSRE

**Grund 2: Projekt-Roaming**
- User wechselt zwischen CENCOCD und DCSRE täglich
- Beides liegt auf WSL2 unter /mnt/c/
- Projekt-Detektion (cwd match) ist **robust**, aber Keybindings bleiben "alt"

**Grund 3: Feature-Divergence**
- CENCOCD hat Stufe 1/2 Tests (distinct kategorien)
- DCSRE hat FluentMigrator Setup
- CENCOCD hat Blazor Frontend, DCSRE hat Angular/NX

**Empfehlung:**
```
Nicht: init_windows.lua + init_linux.lua
Sondern:
  lua/shared/
    core.lua
    init_windows.lua
    init_linux.lua
    projects/
      cencocd.lua (project-spezifisch)
      dcsre.lua   (project-spezifisch)
    keybindings/
      shared.lua  (generische keymaps)
      cencocd.lua (project-spezifisch)
      dcsre.lua   (project-spezifisch)
```

---

## 5. Dead Code Analyse

### Befund: WSL2-Branch IST NICHT Dead Code!

**Zeilen 3071-3082 (`<leader>rbw`):**
```lua
if is_windows then
  cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; dotnet run --launch-profile https"'
else
  cmd = 'cd ' .. vim.g.project_webhost .. ' && dotnet run --launch-profile https'
end
```

**Kontext:**
- Beides wird genutzt!
- User läuft Neovim SOWOHL nativ (Windows Neovim, is_windows=true)
- UND in WSL2 (WSL2 Neovim, is_windows=false)
- CLAUDE.md bestätigt: "zwei separate init.lua Konfigurationen"

**→ KEIN Dead Code! Beide Branches sind aktiv!**

### Dead Code: Obsidian-Links (potentiell)

**Zeilen 745, 749, 753:**
```lua
path = vim.fn.has('win32') == 1 and 'C:/Users/Administrator/Documents/DCS'
    or '/mnt/c/Users/Administrator/Documents/DCS',
```

**Befund:**
- Hardcoded paths für Obsidian-Vaults
- NICHT projektabhängig
- Werden vermutlich nur von User genutzt

**→ Nicht "dead", aber "legacy" (can refactor später)**

### Dead Code: Getline 3150 (xdg-open nur Windows)

**Zeile 937:**
```lua
vim.fn.system('xdg-open "' .. uri .. '"')
```

**Kontext:**
- Liest aktuellen Cursor-Line aus und öffnet Link in Obsidian
- Hat Windows-Check: `if vim.fn.has('win32') == 1 then Start-Process else xdg-open end`
- **ABER**: xdg-open läuft auf Linux, `Start-Process` auf Windows

**→ KEIN Dead Code! Beide Branches genutzt!**

---

## 6. GAP-Analyse: Aufwand Schätzung

### Neue Dateien (CREATE)
| Datei | Zeilen | Aufwand |
|-------|--------|---------|
| init.lua (Dispatcher) | 15 | trivial |
| lua/shared/core.lua | 2900 | COPY + PASTE (minimal editing) |
| lua/shared/init_windows.lua | 1200 | EXTRACT + ADAPT (powershell, C:/) |
| lua/shared/init_linux.lua | 800 | EXTRACT + ADAPT (bash, /mnt/c/) |
| **Summe** | **4915** | **8h** |

### Verschobene LOC (MOVE)
- Zeilen 1-100: Kickstart-Header → init.lua (COPY as-is)
- Zeilen 200-276: Project Detection → init_windows.lua + init_linux.lua (COPY, minimal change)
- Zeilen 277-459: vim.o settings, keymaps → core.lua (COPY as-is)
- Zeilen 460-3034: require('lazy').setup → core.lua (COPY as-is)
- Zeilen 3035-3650: Keybindings → init_windows.lua + init_linux.lua (COPY + adapt shell)
- **Summe**: ~3900 Zeilen direkt verschiebbar (COPY paste)

### Umzuschreibende LOC (REFACTOR)
- Alle `powershell.exe` Befehle in init_windows.lua: 68 Zeilen
  - Nur adaption (C:/ vs /mnt/c/), kein Logic-Change
- Alle `cd ...` Befehle in init_linux.lua: 68 Zeilen
  - Neue Version (bash statt powershell), aber identische Logic
- `is_windows` Ternary-Operator elimination: 13 Stellen
  - Entfernen, da jede Datei weiß, welche Platform
- **Summe**: ~150 Zeilen wirklich umzuschreiben

### Wirklich NEUER Code
- Dispatcher (init.lua): 15 Zeilen
- Project-specific Subfolder (optional): 0 LOC (structure only)
- Tests: 10-20 neue Tests für smoke-testing
- **Summe**: ~25 Zeilen wirklich neu

---

## 7. GAP-Vorschau: IST vs. SOLL

### IST (Aktuell, 4541 Zeilen)
```
init.lua (monolith)
├── Kickstart Header (100 Zeilen)
├── Project Detection (70 Zeilen)
├── vim.o Settings (143 Zeilen)
├── Standard Keymaps (47 Zeilen)
├── require('lazy').setup (2574 Zeilen)
├── Keybindings (1615 Zeilen)
│   ├── [Backend] rbw, rbs, rbb, rbt, rbu (PowerShell + Bash branches)
│   ├── [Frontend] rfr, rfb, rfi, rft (PowerShell + Bash branches)
│   ├── [Docker] rDi, rDa, rDI (PowerShell, projekt-spezifisch)
│   └── [Git] gg, gf, rc, rp, rP, gyf, gyd
└── Diagnostics + Obsidian (misc)
```

**Probleme:**
- Monolith: 1 Fehler kann Alles brechen
- Platform-Branches: 12× is_windows, schwer zu folgen
- Projekt-Branches: 6× vim.g.project_name checks
- Keine Struktur: hard zu navigieren, Duplizierung (powershell vs bash fast-identical)

### SOLL (Nach Migration)
```
init.lua (15 Zeilen, Dispatcher)
└── require('lua.shared.core')
└── require('lua.shared.init_' .. (is_windows and 'windows' or 'linux'))

lua/shared/
├── core.lua (2900 Zeilen)
│   ├── vim.o Settings
│   ├── Keymaps (standard, non-project)
│   └── require('lazy').setup
├── init_windows.lua (1200 Zeilen)
│   ├── Project Detection (CENCOCD + DCSRE)
│   ├── Keybindings (PowerShell-version)
│   └── Windows-spezifische Helpers
├── init_linux.lua (800 Zeilen)
│   ├── Project Detection (copy-paste from Windows!)
│   ├── Keybindings (Bash-version)
│   └── Linux-spezifische Helpers
└── [OPTIONAL] projects/ (für zukünftige Expansion)
    ├── cencocd.lua
    └── dcsre.lua
```

**Vorteile:**
- Klare Trennung: Platform vs. Core vs. Project
- Dispatcher ist trivial (easy zu debuggen)
- init_windows.lua und init_linux.lua sind 95% identisch (können unified werden später mit Template?)
- Project-Logik kann in projects/ verschoben werden

### GAP Metriken
| Metrik | IST | SOLL | Delta |
|--------|-----|------|-------|
| **Dateien** | 1 | 4 (+ optional 2 project-Dateien) | +3 |
| **Zeilen (Monolith)** | 4541 | 4915 | +374 |
| **Nesting-Tiefe** | 8 (Lazy.setup verschachtelt) | 5 | -3 |
| **is_windows Conditionals** | 12 | 2 (nur in Dispatcher + shared core-init) | -10 |
| **project_name Checks** | 6 | 6 (bleiben, aber in platform-Dateien isoliert) | 0 |
| **PowerShell-Linien** | 68 | 68 (in init_windows.lua) | 0 |
| **Bash-Äquivalente** | 4 | 68 (new in init_linux.lua) | +64 |

### Aufwand-Schätzung
| Phase | Aufwand | Kritikalität |
|-------|---------|--------------|
| **S1: Test-Infra** | 1h | HOCH (Smoke-Test brauchbar) |
| **S2: Dispatcher** | 15 min | TRIVIAL |
| **S3: core.lua** | 1h | MITTEL (copy + remove is_windows) |
| **S4: project.lua** | 30 min | TRIVIAL (copy Project Detection) |
| **S5: init_windows.lua** | 2h | HOCH (extract + adapt C:/ paths) |
| **S6: init_linux.lua** | 1.5h | HOCH (extract + adapt /mnt/c/ + bash) |
| **S7: Cleanup + Test** | 1h | HOCH (Smoke-Tests, WSL2 verification) |
| **GESAMT** | **7-8h** | **MEDIUM** |

---

## 8. Kette von Abhängigkeiten (Dependency Graph)

```
1. Test-Infra (INDEPENDENT)
   ├─ Unit tests für core.lua parsing
   └─ Smoke test für is_windows detection

2. Dispatcher init.lua (INDEPENDENT)
   └─ Nur: require, Lazy.nvim aufrufen

3. core.lua (DEPENDS on: S2)
   ├─ require('lazy').setup
   └─ vim.o settings

4. project.lua (DEPENDS on: S3 MUST RUN FIRST)
   └─ Benötigt: require() im init_windows/init_linux

5. init_windows.lua (DEPENDS on: S3, S4)
   ├─ require('lua.shared.project')
   ├─ powershell.exe Keybindings
   └─ C:/ Paths

6. init_linux.lua (DEPENDS on: S3, S4)
   ├─ require('lua.shared.project')
   ├─ bash Keybindings (neue Version!)
   └─ /mnt/c/ Paths

7. Cleanup (DEPENDS on: S5, S6)
   └─ Alte init.lua löschen

8. Smoke Tests (DEPENDS on: S7)
   └─ WSL2 Test, Windows Test
```

**Parallelisierbar:**
- S1 kann parallel zu S2-S6
- S5 und S6 können parallel (identischer input, different output)
- S3 MUST before S5/S6 (required in init_windows/linux)
- S4 MUST before S5/S6 (required in init_windows/linux)

**Kritikalität:**
- **BLOCKING**: S3 → S5/S6
- **BLOCKING**: S4 → S5/S6
- **OK PARALLEL**: S5 ↔ S6

---

## 9. Schätzung Implementierungsaufwand (Detailliert)

### Neue Dateien (CREATE)
1. **init.lua** (15 Zeilen)
   - Status: TRIVIAL ✅
   - Copy-Paste-Vorlage + 2 Requires
   - Aufwand: 5 min

2. **lua/shared/core.lua** (2900 Zeilen)
   - Status: COPY-PASTE + Minimal-Cleanup ✅
   - Input: init.lua Zeilen 277-3034
   - Aufwand: Remove 12 `is_windows` checks = 1h

3. **lua/shared/project.lua** (70 Zeilen)
   - Status: COPY ✅
   - Input: init.lua Zeilen 200-276
   - Aufwand: 10 min (nur copy)

4. **lua/shared/init_windows.lua** (1200 Zeilen)
   - Status: EXTRACT + ADAPT ⚠️
   - Input: init.lua Zeilen 1-100, 200-276, 3035-3650
   - Änderungen:
     - C:/ Paths (bleiben as-is)
     - powershell.exe Befehle (bleiben as-is)
     - Remove is_windows checks (da Windows-spezifisch)
   - Aufwand: 2h (copy + remove is_windows)

5. **lua/shared/init_linux.lua** (800 Zeilen)
   - Status: NEW + ADAPT ⚠️
   - Input: init_windows.lua als template, aber:
     - Replace `powershell.exe -Command "..."` mit `bash -c "..."`
     - Replace `C:/Users/...` mit `/mnt/c/Users/...`
     - Replace `Set-Location` mit `cd`
     - Replace `$env:VAR` mit `export VAR`
   - Aufwand: 2h (new code, pattern-based replace)

6. **lua/shared/test_smoke.lua** (20-30 Zeilen)
   - Status: NEW
   - Tests:
     - core.lua loads without error
     - is_windows detection works
     - project detection (CENCOCD vs DCSRE) works
   - Aufwand: 1h (test infrastructure + 3 assertions)

### Verschobene LOC (MOVE - reines Copy-Paste)
- init.lua Zeilen 1-100 → init.lua (Dispatcher, as-is)
- init.lua Zeilen 200-276 → project.lua (as-is)
- init.lua Zeilen 277-459 → core.lua (as-is)
- init.lua Zeilen 460-3034 → core.lua (as-is)
- init.lua Zeilen 3035-3650 → init_windows.lua (as-is, copy from init.lua)
- **Summe**: ~3900 Zeilen reines Copy-Paste (0 LOC neuer Code)
- **Aufwand**: 30 min (Select + Copy + Paste)

### Umzuschreibende LOC (REFACTOR - Logic-Change)
1. **Remove is_windows Conditionals in core.lua**
   - 12 Vorkommen, durchschnittlich 2 Zeilen pro Stelle
   - **Aufwand**: 30 min (find + replace)
   - **Beispiel**:
     ```lua
     -- VOR:
     path = vim.fn.has('win32') == 1 and 'C:/Users/...' or '/mnt/c/Users/...'

     -- NACH (in init_windows.lua):
     path = 'C:/Users/...'

     -- NACH (in init_linux.lua):
     path = '/mnt/c/Users/...'
     ```

2. **Convert PowerShell Commands to Bash**
   - 68 × powershell.exe Zeilen müssen bash-equivalent werden
   - **Muster**:
     ```lua
     -- VOR (PowerShell):
     'powershell.exe -Command "Set-Location \'' .. path .. '\'; dotnet run"'

     -- NACH (Bash):
     'cd ' .. path .. ' && dotnet run'
     ```
   - **Aufwand**: 1.5h (pattern-replace mit vim regex oder Python script)

3. **Path Conversion in init_linux.lua**
   - C:/ → /mnt/c/ umwandeln
   - Backslash → Forward-Slash
   - **Aufwand**: 30 min (sed oder Lua script)

4. **Environment Variable Syntax**
   - PowerShell: `$env:ASPNETCORE_URLS`
   - Bash: `export ASPNETCORE_URLS=...` (inline oder separate)
   - **Aufwand**: 30 min (pattern replacements)

**Summe Refactor**: ~3h (mostly search-replace, nicht komplexes rewriting)

### Wirklich NEUER Code (Logic-Change)
1. **Dispatcher init.lua** (15 Zeilen)
   - 100% neuer Code
   - Aber trivial: nur requires

2. **Bash-Äquivalente in init_linux.lua** (68 Zeilen)
   - Nicht "neuer" Code (copy vom init_windows.lua template)
   - Aber "neue Syntax" (bash statt powershell)
   - Aufwand: 2h (schon oben gerechnet)

3. **Smoke Tests** (30 Zeilen)
   - 100% neuer Code
   - Aufwand: 1h (infrastructure + assertions)

**Summe NEW Code**: ~45 Zeilen (trivial, ~1.5h development + testing)

---

## 10. FINALE Aufwand-Schätzung

| Kategorie | LOC | Aufwand | Kritikalität |
|-----------|-----|---------|--------------|
| **Test-Infra** | 30 | 1h | HOCH (blocker) |
| **Dispatcher** | 15 | 15 min | TRIVIAL |
| **core.lua** | 2900 | 2h (copy + cleanup) | HOCH |
| **project.lua** | 70 | 15 min | TRIVIAL |
| **init_windows.lua** | 1200 | 2h | MITTEL |
| **init_linux.lua** | 800 | 2h | MITTEL |
| **Bash Pattern-Replace** | 68 | 1.5h | HOCH (error-prone) |
| **Testing + Smoke** | - | 1h | HOCH (blockers) |
| **Cleanup old init.lua** | - | 15 min | TRIVIAL |
| **GESAMT** | **4900** | **8-9h** | **MEDIUM** |

**Risikoanalyse:**
- ⚠️ HIGH: Bash-Pattern-Replace (68 befehle, error-prone)
- ⚠️ HIGH: is_windows Ternary-Entfernung (Duplikation in Windows+Linux)
- ⚠️ MEDIUM: Lazy.nvim require() Order (Reihenfolge unkritisch da separate Files)
- ✅ LOW: core.lua copy (straight copy-paste, kein Logic-Change)

---

## Zusammenfassung für Team-Lead

**D03 Findings:**
1. **LOC-Analyse**: 4541 → 4915 Zeilen (+8%). Größter Teil ist COPY-PASTE, nicht neuer Code.
2. **Migrationsreihenfolge validiert**: E05 Plan ist 90% richtig, aber Schritt 2 ↔ 3 tauschen.
3. **CENCOCD vs DCSRE Trennung**: JA, lohnt sich! 6+ Projekt-Checks in 50+ Keybindings = zu komplex.
4. **Dead Code**: NEIN! Beide is_windows Branches sind aktiv (Windows Neovim + WSL2 Neovim).
5. **Aufwand**: 8-9h (davon 3h reine Search-Replace, 2h Copy-Paste, 1h Test-Infra).
6. **Parallelisierbarkeit**: init_windows.lua + init_linux.lua können parallel entwickelt werden.

**GAP-Vorschau aktuell:**
- IST: 1 Monolith (4541 Zeilen, 12× is_windows, 6× project_name checks)
- SOLL: 3 Dateien + Test-Infra (4915 Zeilen, 2× is_windows, Project-Checks isoliert)
- DELTA: Mehr Struktur, besser zu debuggen, aber 374 extra LOC wegen Duplikation

**Nächste Schritte (für Synthese-Phase):**
- S1: Test-Infra aufbauen
- S2+S3: Dispatcher + core.lua (parallel ok)
- S4+S5+S6: project.lua + init_windows/linux.lua (S4 MUST before S5/S6)
- S7+S8: Cleanup + Smoke-Tests
