# KickStartNeoVim - Slice-Architektur

## Übersicht

Refactoring der monolithischen `init.lua` (4541 Zeilen) in ein modulares Lua-Modul-System.
Entscheidung: **Variante A** — echter Split mit `lua/shared/` (DRY, testbar, Task.md-konform).

**Ziel-Struktur:**
```
KickStartNeoVim/
├── init.lua                    # Dispatcher: ~15 Zeilen
├── init_windows.lua            # Windows Entry-Point: ~50 Zeilen
├── init_linux.lua              # Linux/WSL2 Entry-Point: ~40 Zeilen
└── lua/
    ├── shared/
    │   ├── platform.lua        # is_windows, Chrome-Pfade, open_url() — ~35 LOC
    │   ├── project.lua         # find_dcsre_root(), detect(), vim.g.* — ~120 LOC
    │   ├── core.lua            # vim.opt, Keymaps, Lazy-Bootstrap, Plugins — ~2700 LOC
    │   └── keybindings/
    │       ├── backend.lua     # rbw, rbs, rbb, rbt, rbW — ~180 LOC
    │       ├── frontend.lua    # rfr, rfb, rfi, rft, rfw — ~80 LOC
    │       ├── git.lua         # gg, gf, gD, gM, gdc, rp, rP, rc — ~120 LOC
    │       ├── docker.lua      # rDi, rDa, rDI — ~140 LOC
    │       ├── tests.lua       # rim, rid, reb, rei, reg, res — ~200 LOC
    │       └── clipboard.lua   # yp, yn, gyf, gyd — ~80 LOC
    └── spec/
        ├── smoke_spec.lua      # Neovim startet ohne Fehler — ~30 LOC
        ├── platform_spec.lua   # Tests für platform.lua — ~80 LOC
        └── project_spec.lua    # Tests für project.lua — ~150 LOC
```

---

## Dependency-Graph

| Slice | Welle | Abhängigkeit | Dateien |
|-------|-------|--------------|---------|
| S1_TestInfra | 1 | - | lua/spec/smoke_spec.lua, lua/spec/platform_spec.lua, lua/spec/project_spec.lua |
| S2_Platform | 1 | - | lua/shared/platform.lua |
| S3_Project | 1 | S2 (Laufzeit-Dep, kann parallel entwickelt werden) | lua/shared/project.lua |
| S4_Core | 2 | S2, S3 | lua/shared/core.lua |
| S5_Keybindings | 2 | S2, S3, S4 | lua/shared/keybindings/*.lua |
| S6_Dispatcher | 3 | S2–S5 | init.lua, init_windows.lua, init_linux.lua |

**Begründung Wellen-Aufteilung:**
- Welle 1: S1, S2, S3 haben keine gegenseitigen Hard-Dependencies (S3 `require`s S2 zur Laufzeit, aber kann parallel entwickelt und getestet werden, da S2 einfach ist)
- Welle 2: S4 und S5 benötigen S2 + S3 vollständig deployed und getestet
- Welle 3: S6 fasst alles zusammen, braucht alle vorherigen Slices

---

## Slices (Detail)

### S1_TestInfra
- **Welle:** 1
- **Abhängigkeit:** keine (Test-Framework plenary.nvim ist bereits als Plugin in init.lua)
- **Dateien:**
  - `lua/spec/smoke_spec.lua` — Basis-Test: Neovim startet ohne Fehler
  - `lua/spec/platform_spec.lua` — Tests für path conversions (reine String-Ops, kein Mock nötig)
  - `lua/spec/project_spec.lua` — Tests für find_dcsre_root + project detection (mock nötig)
- **Beschreibung:** Legt die gesamte Test-Infrastruktur an. Die Spec-Dateien werden parallel zu den entsprechenden Modulen geschrieben (S2→platform_spec, S3→project_spec). Smoke-Test wird als Basis-Validierung für ALLE nachfolgenden Schritte genutzt.
- **Test-Runner:**
  ```bash
  nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"
  ```
- **LOC:** ~260 (alle drei Spec-Dateien zusammen)

### S2_Platform
- **Welle:** 1
- **Abhängigkeit:** keine
- **Dateien:**
  - `lua/shared/platform.lua` — Neu anlegen
  - `init.lua` — Zeile 200 ersetzen durch `require('shared.platform')`
- **Beschreibung:** Extrahiert die Platform-Detection und plattformspezifische Konstanten. Kein Neovim-State nötig außer `vim.fn.has()` (sicher bei module-load-time). Enthält:
  - `M.is_windows = vim.fn.has('win32') == 1`
  - `M.chrome_path` (Windows vs. WSL2)
  - `M.chrome_cmd` (Shell-escaped Chrome-Pfad)
  - `M.open_url(url)` — xdg-open vs. PowerShell Start-Process
  - `M.to_windows_path(path)` — Forward-Slash → Backslash
  - `M.wsl_to_windows(wsl_path)` — /mnt/c/ → C:\
- **Risiko:** Gering
- **LOC:** ~35

### S3_Project
- **Welle:** 1
- **Abhängigkeit:** S2 zur Laufzeit (platform.is_windows, platform.wsl_to_windows)
- **Dateien:**
  - `lua/shared/project.lua` — Neu anlegen
  - `init.lua` — Zeilen 202–268 ersetzen durch `require('shared.project').detect()`
- **Beschreibung:** Extrahiert die Projekt-Detection (CENCOCD/DCSRE/UNKNOWN) und das Setzen aller `vim.g.project_*` Globals. Enthält Fix für Bug B-001 (project_root_windows auf WSL2 war fehlerhaft — nutzte `gsub('/', '\\')` statt `wsl_to_windows()`). Setzt:
  - `vim.g.project_name`, `vim.g.project_backend`, `vim.g.project_frontend`
  - `vim.g.project_webhost`, `vim.g.project_docker_root`
  - `vim.g.project_git_base`, `vim.g.project_root_windows`, `vim.g.project_root_wsl`
- **Risiko:** Mittel — `project.detect()` muss VOR `lazy.setup()` aufgerufen werden
- **LOC:** ~120

### S4_Core
- **Welle:** 2
- **Abhängigkeit:** S2 (platform.is_windows muss als lokale Variable verfügbar sein), S3 (vim.g.project_* muss gesetzt sein)
- **Dateien:**
  - `lua/shared/core.lua` — Neu anlegen (größter Schritt!)
  - `init.lua` — Zeilen 87–3034 (alles außer platform/project) durch `require('shared.core')` ersetzen
- **Beschreibung:** Der Kern-Slice. Enthält alles was NICHT plattform- oder projektspezifisch ist:
  - Zeilen 87–111: Globals & Leader
  - Zeilen 113–164: SwapExists + .claude Auto-Copy (behält inline `vim.fn.has`-Checks)
  - Zeilen 166–275: Terminal-Farbe, Welcome-Message
  - Zeilen 277–354: Vim-Options (vim.opt.*)
  - Zeilen 356–432: Standard-Keymaps + Autocommands
  - Zeilen 434–447: Lazy.nvim Bootstrap
  - Zeilen 449–3034: ALLE Plugin-Definitionen (lazy.setup)
  - Am Anfang: `local platform = require('shared.platform'); local is_windows = platform.is_windows`
- **Risiko:** Hoch (2700+ LOC Verschiebung) — Bootstrapping-Reihenfolge kritisch:
  1. `rtp:prepend(lazypath)` muss vor `require('lazy').setup()` stehen
  2. `is_windows` muss als lokale Variable in `core.lua` definiert sein, bevor `lazy.setup({...})` ausgeführt wird
  3. `vim.g.project_*` muss bereits durch `project.detect()` gesetzt sein
- **LOC:** ~2700

### S5_Keybindings
- **Welle:** 2
- **Abhängigkeit:** S2 (platform.is_windows), S3 (vim.g.project_*), S4 (toggleterm.terminal muss geladen sein)
- **Dateien:**
  - `lua/shared/keybindings/backend.lua` — `<leader>rb*` Commands
  - `lua/shared/keybindings/frontend.lua` — `<leader>rf*` Commands
  - `lua/shared/keybindings/git.lua` — `<leader>g*`, `<leader>rp`, `<leader>rP`, `<leader>rc`
  - `lua/shared/keybindings/docker.lua` — `<leader>rD*` Commands
  - `lua/shared/keybindings/tests.lua` — `<leader>ri*`, `<leader>re*`, Integration/E2E Tests
  - `lua/shared/keybindings/clipboard.lua` — `<leader>yp`, `<leader>yn`, `<leader>gyf`, `<leader>gyd`
  - `init.lua` — Zeilen 3036–4539 durch 6x `require('shared.keybindings.*')` ersetzen
- **Beschreibung:** Extrahiert alle Custom-Keybindings in separate thematische Module. Jedes Modul wird sequenziell extrahiert (Reihenfolge nach Risiko):
  1. clipboard.lua (~80 LOC, rein deklarativ, kein Terminal)
  2. git.lua (~120 LOC, Neogit + Diffview)
  3. frontend.lua (~80 LOC, hauptsächlich PowerShell-only Commands)
  4. backend.lua (~180 LOC, WIN+WSL Branch in rbw)
  5. docker.lua (~140 LOC, komplexe PowerShell-Scripts)
  6. tests.lua (~200 LOC, `set_xunit_threads` + `write_it_script` Helpers)
- **Risiko:** Hoch für einzelne Module (terminals mit Pfaden), insgesamt Mittel (sequentielle Extraktion)
- **LOC:** ~800 (alle 6 Module)

### S6_Dispatcher
- **Welle:** 3
- **Abhängigkeit:** S2–S5 vollständig
- **Dateien:**
  - `init.lua` — Final als ~15-Zeilen Dispatcher (oder Weiche auf init_windows/init_linux)
  - `init_windows.lua` — Windows-Native Entry-Point (~50 Zeilen)
  - `init_linux.lua` — WSL2/Linux Entry-Point (~40 Zeilen)
- **Beschreibung:** Fasst alles zusammen. Entscheidung E1 (Variante A) ist bereits getroffen: echte `init_windows.lua` + `init_linux.lua` Entry-Points (Task.md-konform). Der `init.lua` Dispatcher brancht via `vim.fn.has('win32')`.

  **init.lua (Dispatcher):**
  ```lua
  if vim.fn.has('win32') == 1 then
    require('init_windows')
  else
    require('init_linux')
  end
  ```

  **init_windows.lua / init_linux.lua:** Laden platform → project → core → keybindings (identisch, mit Platform-Assert zur Sicherheit).

- **Risiko:** Gering (alle Teile bereits getestet)
- **LOC:** ~105

---

## Wellen

### Welle 1 (parallel ausführbar)
- **S1_TestInfra** — Test-Framework Gerüst anlegen
- **S2_Platform** — platform.lua extrahieren (Quell-Zeile 200 + Chrome/URL-Helfer)
- **S3_Project** — project.lua extrahieren (Quell-Zeilen 202–268) + Bug B-001 Fix

**Rationale:** S1, S2, S3 können parallel entwickelt werden. S3 hat eine Laufzeit-Abhängigkeit auf S2, aber da S2 nur ~35 LOC ist und zuerst committed wird, ist das Risiko vernachlässigbar. S1 (Tests) wird parallel zu S2 und S3 entwickelt.

**Parallelisierung in der I-Pipeline:** S1 + S2 können gleichzeitig starten. S3 kann starten sobald S2 in init.lua integriert ist (da project_spec.lua die platform.lua mockt).

### Welle 2 (nach Welle 1)
- **S4_Core** — core.lua anlegen (größter, riskantester Schritt)
- **S5_Keybindings** — 6 Keybinding-Module extrahieren

**Rationale:** S4 und S5 setzen voraus, dass platform.lua und project.lua korrekt funktionieren und getestet sind. S5 kann erst beginnen wenn S4 vollständig ist (Keybindings brauchen toggleterm, gitsigns etc. aus core.lua).

**Sequenziell empfohlen:** S4 zuerst vollständig abschließen, dann S5 — da S5 auf geladenem toggleterm aufbaut.

### Welle 3 (nach Welle 2)
- **S6_Dispatcher** — init.lua finalisieren, init_windows.lua + init_linux.lua anlegen

---

## Test-Strategie

### Test-Framework
- **Framework:** plenary.nvim busted (bereits als Plugin in init.lua vorhanden)
- **Test-Runner:** `nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"`
- **Test-Verzeichnis:** `lua/spec/`

### Smoke-Test (Basis-Validierung nach JEDEM Schritt)
```bash
nvim --headless +q && echo "OK" || echo "FEHLER"
```
Dieser Test muss nach jedem Slice grün bleiben. Kein Schritt weiter wenn Smoke-Test rot.

### Unit-Tests (plenary busted)

#### lua/spec/smoke_spec.lua (~30 LOC)
- Neovim startet ohne Fehler (wird via headless getestet)
- Wird nach S1 erstellt, bleibt danach immer grün

#### lua/spec/platform_spec.lua (~80 LOC)
Testet **reine String-Operationen** (kein Mock nötig):
- `to_windows_path()`: Forward-Slash → Backslash
- `wsl_to_windows()`: /mnt/c/ → C:\, /mnt/d/ → D:\
- `is_windows` Konsistenz mit `vim.fn.has('win32')`

**Wann:** Parallel zu S2 (platform.lua entwickeln und testen in einem Schritt)

#### lua/spec/project_spec.lua (~150 LOC)
Testet mit Mocks:
- `find_dcsre_root()`: 5 Test-Cases (Standard, DCSRE_Azure Nested, nil, tief verschachtelt, Windows-Backslash)
- `project.detect()`: 7 Test-Cases (CENCOCD x3, DCSRE, UNKNOWN, git_base x2)

**Mock-Pattern:**
```lua
-- vim.fn.isdirectory mock
vim.fn.isdirectory = function(p) return mock_dirs[p] and 1 or 0 end
-- vim.fn.getcwd mock
vim.fn.getcwd = function() return '/fake/DCSRE/Sources/Backend' end
```

**Wann:** Parallel zu S3 (project.lua entwickeln und testen in einem Schritt)

### Manuelle Akzeptanztest-Checkliste (nach S5_Keybindings)

| Test | Erwartung |
|------|-----------|
| `<leader>rbw` im DCSRE-Ordner | Backend WebHost startet auf https://localhost:5443 |
| `<leader>rbw` im CENCOCD-Ordner | Backend API startet mit https launch profile |
| `<leader>rDi` (Docker UP) | DCSRE: docker-up.ps1, CENCOCD: docker compose up |
| `<leader>rim` | Integration Mock Tests starten |
| `<leader>gg` | Neogit öffnet sich |
| `<leader>rp` | Git push via PowerShell |
| `:LspInfo` auf .cs Datei | omnisharp attached |
| `:Lazy` | Alle Plugins ohne Error |

### Wo liegen Tests

```
lua/spec/
├── smoke_spec.lua       → S1_TestInfra (Welle 1)
├── platform_spec.lua    → S1_TestInfra + S2_Platform (Welle 1)
└── project_spec.lua     → S1_TestInfra + S3_Project (Welle 1)
```

**Was wird NICHT automatisch getestet** (nur manuell):
- Terminal-Commands (Betriebssystem-Calls)
- LSP-Attach-Callbacks (Neovim-State abhängig)
- VimEnter-Autocmds
- Keybinding-Funktionalität (toggleterm, gitsigns, etc.)

---

## Deployment-Anforderungen

Nach dem Refactoring muss das Deployment-Skript `lua/shared/` mitkopieren:

**Windows:**
```powershell
Copy-Item -Recurse -Force 'C:\...\KickStartNeoVim\lua' 'C:\Users\Administrator\AppData\Local\nvim\lua'
Copy-Item -Force 'C:\...\KickStartNeoVim\init.lua' 'C:\Users\Administrator\AppData\Local\nvim\init.lua'
Copy-Item -Force 'C:\...\KickStartNeoVim\init_windows.lua' 'C:\Users\Administrator\AppData\Local\nvim\init_windows.lua'
```

**WSL2:**
```bash
cp -r /path/to/KickStartNeoVim/lua ~/.config/nvim/lua
cp /path/to/KickStartNeoVim/init.lua ~/.config/nvim/init.lua
cp /path/to/KickStartNeoVim/init_linux.lua ~/.config/nvim/init_linux.lua
```

---

## Akzeptanzkriterien (aus SPEC übernommen)

| ID | Kriterium | Slice |
|----|-----------|-------|
| AC-01 | Windows Neovim startet: `nvim --headless +q` Exit-Code 0 | S6 |
| AC-02 | WSL2 Neovim startet: `nvim --headless +q` Exit-Code 0 | S6 |
| AC-03 | DCSRE-Detection: Welcome "Welcome to DCSRE!" | S3 |
| AC-04 | CENCOCD-Detection: Welcome "Welcome to CENCOCD!" | S3 |
| AC-05 | Alle plenary-Tests grün | S1–S3 |
| AC-06 | find_dcsre_root: min. 5 Test-Cases | S1+S3 |
| AC-07 | project.detect: min. 7 Test-Cases | S1+S3 |
| AC-08 | `<leader>rbw` Backend Server startet | S5 |
| AC-09 | `<leader>gg` öffnet Neogit | S5 |
| AC-10 | `<leader>rDi` Docker UP funktioniert | S5 |
| AC-11 | `<leader>rim` Integration Tests | S5 |
| AC-12 | `:Lazy` keine Errors | S4 |
| AC-13 | `:LspInfo` omnisharp attached | S4 |
| AC-14 | StyleCop Warnungen inline | S4 |
| AC-15 | Shared Code nur 1x: `grep -r "vim.opt.number" lua/` → 1 Treffer | S4 |
| AC-16 | CLAUDE.md Deployment-Anleitung aktualisiert | S6 |
| AC-17 | Bug B-001 (project_root_windows WSL2) gefixt | S3 |

---

## exit_report
status: final
query_status: skipped (empty collection)
slices_count: 6
wellen_count: 3
summary: "6 Slices in 3 Wellen. Welle 1: S1_TestInfra + S2_Platform + S3_Project (parallel). Welle 2: S4_Core (2700 LOC, höchstes Risiko) + S5_Keybindings (6 Module, sequenziell). Welle 3: S6_Dispatcher (init_windows.lua + init_linux.lua). Bug B-001 Fix in S3. Test-Coverage: plenary busted für platform + project, manuell für keybindings."
