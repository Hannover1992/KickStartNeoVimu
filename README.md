# OmniSharp + StyleCop Warnings in Neovim 0.11

✅ **VERIFIED WORKING** - StyleCop warnings + Go to Definition mit OmniSharp in Neovim 0.11.4

---

## ⚡ Quick Start (3 Minuten)

```bash
# 1. ⚠️ KRITISCH: NuGet packages restoren! (OHNE DIESEN SCHRITT GEHT NICHTS!)
cd /mnt/c/path/to/your/csharp/project/Backend
dotnet restore --force-evaluate --no-cache
# Warte bis ALLE Projekte restored sind!

# 2. Config Files kopieren
cd /path/to/KickStartNeoVim
cp init.lua ~/.config/nvim/init.lua
mkdir -p ~/.omnisharp
cp omnisharp.json ~/.omnisharp/

# 3. Neovim starten und OmniSharp installieren
nvim
:Mason  # 'omnisharp' suchen, 'i' drücken zum installieren

# 4. C# File öffnen
nvim /mnt/c/path/to/your/project/Program.cs
```

**Fertig!** ✅ StyleCop warnings + Go to Definition funktionieren!

---

## 🚨 WICHTIG: `dotnet restore` ist ZWINGEND erforderlich!

**Problem**: Wenn du in **WSL2** arbeitest und auf `/mnt/c/...` (Windows filesystem) zugreifst, hat OmniSharp **kein Zugriff auf NuGet packages** die in Windows restored wurden!

**Lösung**: IMMER `dotnet restore --force-evaluate --no-cache` in WSL2 ausführen!

**Wie du weißt dass es funktioniert hat:**
```bash
ps aux | grep dotnet
```
Du solltest **mehrere** `dotnet` Prozesse sehen - einen für jedes Projekt in deiner Solution!

**Ohne diesen Schritt:**
- ❌ Keine StyleCop warnings
- ❌ OmniSharp kann Projekte nicht laden
- ❌ Keine Roslyn analyzers

**Mit diesem Schritt:**
- ✅ StyleCop warnings erscheinen inline
- ✅ Go to Definition funktioniert perfekt
- ✅ OmniSharp attached automatisch

---

## Was ist in diesem Repo?

### `init.lua`
Fresh **kickstart.nvim** Setup mit:
- OmniSharp LSP config (minimal - nur handlers!)
- **omnisharp-extended-lsp.nvim** plugin (fixt "Cursor position outside buffer" errors)
- Mason + Mason-LSPConfig für automatische Installation

### `omnisharp.json`
OmniSharp's **native config file** mit:
- `EnableAnalyzersSupport = true` - **KRITISCH für StyleCop warnings!**
- `EnableImportCompletion = true`
- `AnalyzeOpenDocumentsOnly = false`

Wird automatisch von OmniSharp gelesen aus `~/.omnisharp/omnisharp.json`

### `Claude.md`
Komplette Dokumentation:
- Schritt-für-Schritt Anleitung
- Erklärung warum es funktioniert
- Troubleshooting Guide
- Fresh Setup für neue Maschinen

---

## Troubleshooting

### Keine Warnings?

1. **Hast du `dotnet restore` ausgeführt?** (Siehe oben!)
2. **Ist OmniSharp attached?**
   ```vim
   :LspInfo
   ```
3. **Ist omnisharp-extended Plugin installiert?**
   ```bash
   ls ~/.local/share/nvim/lazy/omnisharp-extended-lsp.nvim/
   ```
4. **Cache clearen und neu starten:**
   ```bash
   rm -rf ~/.cache/nvim/
   pkill -f omnisharp
   nvim your-file.cs
   ```

### "Cursor position outside buffer" Error?

Das ist jetzt **GEFIXT** durch `omnisharp-extended-lsp.nvim` handlers! Wenn du den Error noch siehst:

1. Check dass das Plugin installiert ist: `:Lazy`
2. Check dass die handlers in `init.lua` konfiguriert sind (Zeile 732-737)

### OmniSharp attached aber keine warnings?

**99% sicher: `dotnet restore` fehlt!**

```bash
cd /mnt/c/path/to/your/project/Backend
dotnet restore --force-evaluate --no-cache
```

**Dann:**
```vim
:LspRestart
```

---

## System Requirements

- **Neovim**: v0.11.0 oder neuer
- **.NET SDK**: 6.0 oder neuer
- **OS**: Linux/WSL2 (tested on WSL2 Ubuntu)
- **Mason**: Automatisch installiert via kickstart.nvim
- **OmniSharp**: 1.39.14+ (installiert via Mason)

---

## Files in diesem Repo

```
.
├── init.lua              # Neovim config (kickstart.nvim base)
├── omnisharp.json        # OmniSharp settings (copy to ~/.omnisharp/)
├── Claude.md             # Detaillierte Dokumentation
├── README.md             # Diese Datei (Quick Start)
└── SETUP_COMPLETE.md     # Verification log
```

---

## Credits

- **kickstart.nvim**: Base configuration
- **OmniSharp**: C# Language Server
- **omnisharp-extended-lsp.nvim**: Fixes decompiled source navigation
- **Mason**: LSP installer
- **nvim-lspconfig**: LSP configurations

---

## License

Public Domain / Unlicense - Use freely!

---

**Last verified**: 2025-11-13
**Neovim version**: v0.11.4
**OmniSharp version**: 1.39.14

✅ **100% WORKING** - StyleCop warnings + Go to Definition + No errors!
