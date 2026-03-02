# Task: KickStartNeoVim Refactoring

## Ziel

Die monolithische `init.lua` (4541 Zeilen) aufteilen in:
- `init_windows.lua` – Windows-native (PowerShell, Windows-Pfade, `C:/`-Pfade)
- `init_linux.lua` – WSL2/Linux (Unix-Pfade, `/mnt/c/`-Pfade, bash-Commands)
- `lua/shared/core.lua` – Gemeinsamer Code (Plugins, LSP, Keybindings ohne Plattform-Bezug)

Ergänzt durch Lua-Testabdeckung (plenary.nvim busted framework) für die kritischen Hilfsfunktionen.

---

## IST-Zustand

**Datei:** `init.lua` – 4541 Zeilen, eine einzige Datei

**Grobstruktur (Zeilen-Bereiche):**

| Bereich | Zeilen | Beschreibung |
|---------|--------|--------------|
| Header/Kommentar | 1–85 | Kickstart-Intro-Text |
| Globals & Leader | 87–111 | mapleader, nerd_font, notifications |
| Swap-Handling | 113–120 | SwapExists autocmd |
| .claude Auto-Copy | 122–164 | VimEnter: kopiert .claude aus AgentsArchive (WIN+WSL) |
| Terminal-Hintergrundfarbe | 166–192 | Projekt-spezifische Farbe (DCSRE/CENCOCD/Private) |
| Platform-Detection | 194–200 | `is_windows = vim.fn.has('win32') == 1` |
| Projekt-Detection | 202–268 | CENCOCD / DCSRE Pfad-Setup (Win+Linux) |
| Welcome-Message | 270–275 | VimEnter Notify |
| Vim-Options | 277–354 | Alle vim.o.* Einstellungen |
| Basic Keymaps | 356–432 | Standard-Neovim Keybindings |
| Lazy.nvim Bootstrap | 434–447 | lazy.nvim Installation |
| Plugin-Setup (lazy.setup) | 449–3034 | Alle Plugins |
| Custom Keybindings | 3036–4539 | Projekt-Commands, Git, Backend, Frontend, Docker etc. |
| Modeline | 4540–4541 | `vim: ts=2 sts=2 sw=2 et` |

**Plugin-Liste:**
- guess-indent, omnisharp-extended, sonarqube, neogit+diffview, markdown-preview, obsidian, img-clip, toggleterm, vim-dadbod-ui, neotest, undotree, neo-tree, aerial, twilight, zen-mode, nvim-notify, nvim-dap+dapui, gitsigns, which-key, telescope, lazydev, nvim-lspconfig+mason, conform, blink.cmp, tokyonight, catppuccin, todo-comments, mini.nvim, nvim-treesitter

---

## SOLL-Zustand

```
KickStartNeoVim/
├── init.lua                    # Verteiler: lädt je nach Plattform init_windows oder init_linux
├── init_windows.lua            # Windows-native Entry-Point
├── init_linux.lua              # WSL2/Linux Entry-Point
└── lua/
    └── shared/
        ├── core.lua            # Gemeinsam: Plugins, LSP, vim-options, Standard-Keybindings
        ├── project.lua         # Projekt-Detection (is_windows-abhängig, aber zentral testbar)
        └── keybindings/
            ├── backend.lua     # Backend-Commands (plattformabhängig)
            ├── frontend.lua    # Frontend-Commands (plattformabhängig)
            ├── git.lua         # Git-Keybindings
            ├── docker.lua      # Docker-Keybindings
            └── tests.lua       # Test-Keybindings (Integration, E2E, Unit)
```

**Trennung des plattform-spezifischen Codes:**
- Windows-spezifisch: `powershell.exe` Commands, `C:/`-Pfade, `start ""` Aufrufe
- Linux-spezifisch: `/mnt/c/`-Pfade, `xdg-open`, Chrome-Pfad `/mnt/c/Program Files/...`
- Shared: Plugin-Konfiguration, LSP-Setup, Vim-Options, Standard-Keybindings

---

## Akzeptanzkriterien

1. **Funktionalität erhalten**: Alle bestehenden Keybindings und Plugins funktionieren nach Refactoring identisch
2. **Windows-native läuft**: `init_windows.lua` funktioniert in Windows Neovim ohne WSL
3. **WSL2 läuft**: `init_linux.lua` funktioniert in WSL2 Neovim
4. **Tests vorhanden**: `lua/spec/` enthält Tests für `project.lua` und `shared/core.lua` (busted framework)
5. **Tests laufen durch**: `nvim --headless -c "PlenaryBustedDirectory lua/spec/ {sequential=true}" -c "q"`
6. **Keine Regression**: Alle Keybindings (`<leader>rbw`, `<leader>rfw`, etc.) funktionieren
7. **Kein Code-Duplikat**: Shared-Code ist nur einmal vorhanden

---

## Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Lazy-loading Reihenfolge bricht | Mittel | Hoch | Step-by-Step: erst aufteilen, dann testen |
| `is_windows` zu früh/spät evaluiert | Mittel | Mittel | Platform-Detection zuerst in shared/core.lua |
| Obsidian.nvim Workspace-Pfade falsch | Niedrig | Mittel | `vim.fn.has('win32')` Checks bleiben im Config-Block |
| toggleterm Commands mit falschen Pfaden | Hoch | Hoch | Jedes Terminal-Command nach Split manuell testen |
| DAP adapter Pfad-Problem (netcoredbg .exe) | Mittel | Mittel | `.exe` Suffix-Logic bleibt in Platform-Block |

---

## Scope

### IN-Scope
- Aufteilen von `init.lua` in `init_windows.lua` / `init_linux.lua` / `lua/shared/`
- Testabdeckung für `project.lua` (Projekt-Detection-Logik)
- Testabdeckung für Platform-Detection-Hilfsfunktionen
- Dokumentation der neuen Dateistruktur

### OUT-of-Scope
- Änderung von Funktionalität (nur Refactoring, kein Feature-Creep)
- Neue Plugins hinzufügen
- Bestehende Keybindings umbenennen
- Migration von `omnisharp.json` oder anderen externen Config-Dateien
- CI/CD oder automatisierte Tests außerhalb von plenary busted
