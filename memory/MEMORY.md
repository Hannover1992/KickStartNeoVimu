# KickStartNeoVim Config Memory

## Projekt-Stand (2026-03-02)
- **Branch:** `develop` (Arbeits-Branch), `main` (stabiler Stand, Commit 523bbcc)
- **Analyse:** KOMPLETT — alle Artefakte in `.claude/analysis/` + `.claude/models/`
- **Nächster Schritt:** Implementierung auf `develop`

## Analyse-Ergebnisse (Kurzfassung)
- `init.lua`: 4541 Zeilen → 2900 shared / 350 Windows / 40 Linux / 30 is_windows Ternary
- 52x `powershell.exe` (intentional wegen VPN), 12x `is_windows` Variable
- User läuft Windows Neovim + WSL2 Neovim PARALLEL (beide Branches aktiv)
- Bug B-001: `project_root_windows` auf WSL2 → `\mnt\c\` statt `C:\`

## Ziel-Architektur (SPEC empfiehlt Variante A)
```
init.lua (15 Zeilen Dispatcher)
├── init_windows.lua (~50 Zeilen)
├── init_linux.lua (~40 Zeilen)
└── lua/shared/
    ├── platform.lua (~35 Zeilen)
    ├── project.lua (~120 Zeilen)
    ├── core.lua (~2700 Zeilen)
    └── keybindings/ (backend, frontend, git, docker, tests, clipboard)
lua/spec/ (Tests: project_spec.lua + platform_spec.lua)
```

## Lade-Reihenfolge (KRITISCH)
`platform.lua` → `project.detect()` → `core.lua` → `keybindings/`

## Migrations-Plan (6 Schritte)
1. Test-Infra setup
2. `lua/shared/platform.lua` anlegen
3. `lua/shared/project.lua` anlegen + Tests
4. `lua/shared/core.lua` anlegen
5. Keybinding-Module extrahieren (clipboard → git → frontend → backend → docker → tests)
6. Dispatcher finalisieren + CLAUDE.md aktualisieren

## Wichtige Artefakte
- `.claude/models/KickStartNeoVim_Model.md` — Architektur-Model v1.0
- `.claude/analysis/synthese/KickStartNeoVim-SPEC.md` — vollständige SPEC mit Lua-Code
- `.claude/analysis/synthese/KickStartNeoVim-GAP.md` — 20 GAPs, kritischer Pfad
- `.claude/Task.md` — Task-Definition
- `.claude/crumbs/KickStartNeoVim_crumbs.md` — Zeilen-Karte von init.lua

## Offene Entscheidung (F1)
Variante 4.1 (init.lua lädt direkt shared/) vs. 4.2 (init.lua → init_windows.lua / init_linux.lua)?
SPEC empfiehlt Variante A mit echten Entry-Points (Task.md-konform), aber Variante 4.1 ist einfacher.

## Deployment-Workflow
```powershell
# Windows
Copy-Item -Recurse -Force 'KickStartNeoVim\lua' '%LOCALAPPDATA%\nvim\lua'
Copy-Item -Force 'KickStartNeoVim\init.lua' '%LOCALAPPDATA%\nvim\init.lua'
```
```bash
# WSL2
cp -r /path/to/KickStartNeoVim/lua ~/.config/nvim/lua
cp /path/to/KickStartNeoVim/init.lua ~/.config/nvim/init.lua
```

## Git-Workflow
- NIEMALS auto-committen (CLAUDE.md Regel!)
- Arbeits-Branch: `develop`
- main = stabiler Stand

## Platform-Detection Pattern
```lua
local is_windows = vim.fn.has('win32') == 1  -- Zeile 200 in init.lua
```

## Test-Runner
```bash
nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"
```
