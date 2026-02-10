# DAP (Debug Adapter Protocol) - C# Debugging in Neovim

**Status:** ✅ Konfiguriert (nvim-dap + netcoredbg)
**Projekte:** DCSRE, CENCOCD
**Debugger:** netcoredbg (installiert via Mason)

---

## 🚀 Quick Start

```vim
" 1. Öffne C# Datei
nvim /path/to/Backend/Program.cs

" 2. Setze Breakpoint
<leader>xt

" 3. Starte Debug
<leader>xc

" 4. DAP UI öffnet automatisch
"    - Links: Scopes, Breakpoints, Stack, Watches
"    - Unten: REPL, Console
```

---

## 🎮 Keybindings (`<leader>x*`)

### Execution
| Key | Aktion | Beschreibung |
|-----|--------|--------------|
| `<leader>xc` | Continue | Debug starten / fortsetzen |
| `<leader>xr` | Restart | Debug neu starten |
| `<leader>xq` | Quit | Debug beenden |

### Stepping (Navigation)
| Key | Aktion | Beschreibung |
|-----|--------|--------------|
| `<leader>xi` | Step **I**nto | In Funktion reinspringen |
| `<leader>xo` | Step **O**ut | Aus Funktion rausspringen |
| `<leader>xj` | Step Over/**J**ump | Nächste Zeile (über Funktionen) |

### Breakpoints
| Key | Aktion | Beschreibung |
|-----|--------|--------------|
| `<leader>xt` | **T**oggle Breakpoint | Breakpoint setzen/entfernen |
| `<leader>xC` | **C**onditional Breakpoint | Breakpoint mit Bedingung (z.B. `i > 10`) |

### UI & Eval
| Key | Aktion | Beschreibung |
|-----|--------|--------------|
| `<leader>xw` | Debug **W**indow Toggle | DAP UI ein/aus |
| `<leader>xe` | **E**val | Expression evaluieren (Normal + Visual mode) |
| `<leader>xh` | **H**over | Variable unter Cursor anzeigen |

---

## 📦 Installierte Plugins

### Core
- **nvim-dap** (`mfussenegger/nvim-dap`)
  Debug Adapter Protocol für Neovim

- **nvim-dap-ui** (`rcarriga/nvim-dap-ui`)
  UI mit Panels (Scopes, Stack, Breakpoints, REPL)

- **nvim-dap-virtual-text** (`theHamsta/nvim-dap-virtual-text`)
  Zeigt Variablen-Werte inline im Code

### Debugger
- **netcoredbg** (installiert via Mason)
  C#/.NET Debugger (kompatibel mit VSCode Debug Protocol)

---

## 🔧 Setup & Installation

### 1. Plugin-Installation (automatisch)
Beim ersten Neovim-Start lädt Lazy.nvim alle Plugins automatisch.

```vim
" Falls nicht automatisch:
:Lazy sync
```

### 2. netcoredbg Installation (via Mason)
```vim
:Mason
" Suche: netcoredbg
" Drücke: i (install)
" Warte: ~1 Minute
" Drücke: q (quit)
```

**Prüfen ob installiert:**
```bash
which netcoredbg
# Sollte anzeigen: ~/.local/share/nvim/mason/bin/netcoredbg
```

---

## 🎯 Launch-Konfigurationen

### DCSRE WebHost
```lua
{
  type = 'coreclr',
  name = 'Launch - DCSRE WebHost',
  program = '<backend>/VDEK.DCSP.WebHost/bin/Debug/net8.0/VDEK.DCSP.WebHost.dll',
  cwd = '<backend>',
  stopAtEntry = false,
  console = 'integratedTerminal',
}
```

**Voraussetzung:** Projekt muss gebaut sein!
```bash
cd /path/to/DCSRE/Sources/Backend
dotnet build
```

### CENCOCD API
```lua
{
  type = 'coreclr',
  name = 'Launch - CENCOCD API',
  program = '.../CenCoCo.Core.API/bin/Debug/net8.0/CenCoCo.Core.API.dll',
  cwd = '.../CenCoCo.Core.API',
  stopAtEntry = false,
  console = 'integratedTerminal',
}
```

### Attach to Process
```lua
{
  type = 'coreclr',
  name = 'Attach - Process ID',
  request = 'attach',
  processId = require('dap.utils').pick_process,
}
```

**Usage:** Wähle aus laufenden .NET Prozessen.

---

## 🪟 DAP UI Layout

### Links (40 Zeichen breit)
- **Scopes** (25%) - Lokale Variablen, this, Parameter
- **Breakpoints** (25%) - Alle gesetzten Breakpoints
- **Stacks** (25%) - Call Stack (Funktionsaufrufe)
- **Watches** (25%) - Custom Watch-Expressions

### Unten (10 Zeilen hoch)
- **REPL** (50%) - C# Code live ausführen
- **Console** (50%) - Debug-Output, Logs

### Auto-Open/Close
- ✅ Öffnet automatisch bei Debug-Start (`dap.continue()`)
- ✅ Schließt automatisch bei Debug-Ende (`terminate()`, `exit`)

---

## 🔍 Breakpoint-Icons

| Icon | Bedeutung |
|------|-----------|
| 🔴 | Normaler Breakpoint |
| 🟡 | Conditional Breakpoint |
| ▶️ | Current Line (Debugger stopped here) |

---

## 🐛 Troubleshooting

### netcoredbg nicht gefunden
```bash
# Prüfen ob installiert
ls ~/.local/share/nvim/mason/packages/netcoredbg/

# Falls leer: Nochmal via Mason installieren
nvim
:Mason
# i auf netcoredbg
```

### DLL nicht gefunden beim Debug-Start
```bash
# Projekt muss gebaut sein!
cd /path/to/Backend
dotnet build

# Prüfe ob DLL existiert
ls bin/Debug/net8.0/*.dll
```

### DAP UI öffnet nicht
```vim
" Manuell öffnen:
<leader>xw

" Prüfen ob nvim-dap-ui installiert ist:
:Lazy
" Suche: nvim-dap-ui
" Sollte grün (installed) sein
```

### Breakpoint wird nicht getroffen
1. **Projekt gebaut?** `dotnet build`
2. **Richtige DLL?** Prüfe Launch-Config (`:lua print(vim.inspect(require('dap').configurations.cs))`)
3. **Debug-Build?** Prüfe ob `/Debug/` im Pfad (nicht `/Release/`)
4. **Code geändert?** Nach Änderung neu bauen!

### REPL funktioniert nicht
```vim
" REPL Panel fokussieren:
<leader>xw  " DAP UI öffnen
<C-w>j     " Zu unterem Panel springen
i          " Insert mode
# Dann C# Code eingeben (z.B. variableName)
```

---

## 📝 Typischer Debug-Workflow

### 1. Projekt bauen
```bash
cd /path/to/DCSRE/Sources/Backend
dotnet build
```

### 2. Neovim öffnen + Breakpoints setzen
```vim
nvim Backend/VDEK.DCSP.WebHost/Controllers/UserController.cs
# Gehe zu Zeile 42
42G
<leader>xt  " Breakpoint setzen (🔴 erscheint)
```

### 3. Debug starten
```vim
<leader>xc  " Continue/Start
# DAP UI öffnet automatisch
# Programm startet bis zum Breakpoint
```

### 4. Stepping
```vim
<leader>xj  " Step over (nächste Zeile)
<leader>xi  " Step into (in Funktion)
<leader>xo  " Step out (aus Funktion)
```

### 5. Variablen inspizieren
```vim
# Methode 1: Hover
# Cursor auf Variable
<leader>xh  " Zeigt Wert in Popup

# Methode 2: Scopes Panel (links)
# Alle lokalen Variablen sichtbar

# Methode 3: Eval
# Visual mode: Variable markieren
viw         " Word markieren
<leader>xe  " Evaluieren
```

### 6. REPL nutzen
```vim
# Im REPL Panel (unten)
i           " Insert mode
# Tippe: user.Name
<CR>        " Enter
# Output: "John Doe"
```

### 7. Conditional Breakpoint
```vim
# Zeile 42
42G
<leader>xC  " Conditional Breakpoint
# Input: user.Id == 123
<CR>
# Breakpoint wird nur getroffen wenn user.Id == 123
```

### 8. Debug beenden
```vim
<leader>xq  " Quit
# DAP UI schließt automatisch
```

---

## 💡 Pro Tips

### Watch Expressions
```vim
" Im Watches Panel:
:lua require('dap.ui.widgets').hover('user.Name')
```

### Multiple Breakpoints
```vim
" Alle Breakpoints anzeigen:
<leader>xw  " DAP UI öffnen
# Breakpoints Panel (links, 2. von oben)
```

### Remote Debugging (Docker)
```lua
-- In init.lua anpassen:
dap.configurations.cs = {
  {
    type = 'coreclr',
    name = 'Attach - Docker',
    request = 'attach',
    processId = function()
      return vim.fn.input('Process ID: ')
    end,
  },
}
```

### Logs anschauen
```vim
:lua require('dap').set_log_level('TRACE')
:e ~/.cache/nvim/dap.log
```

---

## 🔗 Weitere Ressourcen

- **nvim-dap Docs:** https://github.com/mfussenegger/nvim-dap
- **nvim-dap-ui Docs:** https://github.com/rcarriga/nvim-dap-ui
- **netcoredbg:** https://github.com/Samsung/netcoredbg
- **Debug Adapter Protocol:** https://microsoft.github.io/debug-adapter-protocol/

---

## 📋 Keybinding-Übersicht (Copy-Paste Ready)

```
Debug Execution
---------------
<leader>xc   Continue/Start
<leader>xr   Restart
<leader>xq   Quit/Terminate

Debug Stepping
--------------
<leader>xi   Step Into
<leader>xo   Step Out
<leader>xj   Step Over/Jump

Debug Breakpoints
-----------------
<leader>xt   Toggle Breakpoint
<leader>xC   Conditional Breakpoint

Debug UI
--------
<leader>xw   Window Toggle (DAP UI)
<leader>xe   Eval (Normal/Visual)
<leader>xh   Hover (eval under cursor)
```

---

**Viel Erfolg beim Debuggen! 🐛🔫**
