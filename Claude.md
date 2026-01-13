# ✅ OmniSharp StyleCop Warnings - WORKING SOLUTION

**Date**: 2025-11-13
**Status**: ✅ **VERIFIED WORKING**
**Neovim Version**: v0.11.4

---

## ⚠️ WICHTIGE REGEL FÜR CLAUDE

**NIEMALS AUTOMATISCH COMMITTEN!**

Workflow:
1. ✅ Änderungen machen (Edit, Write, etc.)
2. ✅ User testen lassen
3. ❌ **NICHT** automatisch committen!
4. ⏳ Warten auf User-Feedback ("ok commit", "alles klar commit", "gut so")
5. ✅ **NUR DANN** committen

**Begründung**: Claude kann nicht wissen ob die Änderungen funktionieren! Der User muss zuerst in Neovim testen, bevor ein Commit gemacht wird.

**Beispiel FALSCH:**
```
Claude: *macht Änderung*
Claude: *committed automatisch* ❌ FALSCH!
```

**Beispiel RICHTIG:**
```
Claude: *macht Änderung*
Claude: "Fertig! Teste bitte ob es funktioniert."
User: "ok alles gut commit"
Claude: *committed* ✅ RICHTIG!
```

---

## 🚀 QUICK START - Nach Neustart / Neue Maschine

**Du hast dieses Repo bereits geclont und willst es einfach nur verwenden?**

```bash
# 1. ⚠️ WICHTIG: Restore NuGet packages ZUERST! (WSL2/Cross-filesystem)
cd /mnt/c/path/to/your/csharp/project/Backend
dotnet restore --force-evaluate --no-cache
# Warte bis alle Projekte restored sind! (z.B. "Restored 20 projects")
# Ohne diesen Schritt sieht OmniSharp KEINE NuGet packages!

# 2. Copy init.lua to Neovim config directory
cd /path/to/KickStartNeoVim
cp init.lua ~/.config/nvim/init.lua

# 3. Copy omnisharp.json to home directory
mkdir -p ~/.omnisharp
cp omnisharp.json ~/.omnisharp/

# 4. Start Neovim (Lazy.nvim will auto-install plugins)
nvim

# 5. Wait for plugin installation (~1-2 minutes)
# 6. Install OmniSharp via Mason
:Mason
# Search for "omnisharp", press 'i' to install, then 'q' to close

# 7. Open a C# file and test
nvim /mnt/c/path/to/your/project/Backend/YourProject/Program.cs
:LspInfo   # Should show omnisharp attached
```

**That's it!** ✅ StyleCop warnings + Go to Definition should work!

⚠️ **CRITICAL**: Step 1 (dotnet restore) ist ABSOLUT NOTWENDIG! Ohne diesen Schritt werden keine Warnings angezeigt!

---

## Problem

StyleCop analyzer warnings (SA1505, SA1508, etc.) were not appearing in Neovim, despite:
- OmniSharp LSP attached and functional
- Warnings visible in `dotnet build` output
- Go to Definition working

## Solution (4 Steps)

### 1. Install omnisharp-extended Plugin

**File**: `~/.config/nvim/init.lua` - Add to plugin list (around line 248):

```lua
require('lazy').setup({
  -- ... other plugins ...

  -- OmniSharp Extended - Handles metadata/decompiled source navigation
  -- Fixes "Cursor position outside buffer" errors when using gd on framework symbols
  {
    'Hoffs/omnisharp-extended-lsp.nvim',
    ft = 'cs', -- Load only for C# files
  },

  -- ... more plugins ...
})
```

### 2. Configure OmniSharp with Extended Handlers

**File**: `~/.config/nvim/init.lua` - In the `servers` table (around line 730):

```lua
servers = {
  -- ... other servers ...

  -- OmniSharp C# LSP - Use defaults (will be configured via omnisharp.json)
  omnisharp = {
    handlers = {
      ['textDocument/definition'] = require('omnisharp_extended').definition_handler,
      ['textDocument/typeDefinition'] = require('omnisharp_extended').type_definition_handler,
      ['textDocument/references'] = require('omnisharp_extended').references_handler,
      ['textDocument/implementation'] = require('omnisharp_extended').implementation_handler,
    },
  },
}
```

**This fixes the "Cursor position outside buffer" error when using `gd` (go to definition) on .NET Framework symbols!**

### 2b. Enable Auto-Format on Save (Optional but Recommended)

**File**: `~/.config/nvim/init.lua` - Inside the `LspAttach` autocmd, in the OmniSharp section (around line 585-610):

This is **already configured** in the init.lua! The auto-format on save is added inside the OmniSharp-specific block:

```lua
if vim.lsp.get_client_by_id(event.data.client_id).name == 'omnisharp' then
  -- ... omnisharp-extended keybindings ...

  -- Auto-format C# files on save using OmniSharp
  -- Uses .editorconfig settings automatically (configured in omnisharp.json)
  vim.api.nvim_create_autocmd('BufWritePre', {
    buffer = event.buf,
    callback = function()
      vim.lsp.buf.format({ async = false })
    end,
  })
end
```

**What this does:**
- Automatically formats your C# code when you save (`:w`)
- Uses your `.editorconfig` files for formatting rules
- Respects `stylecop.json` and `.ruleset` files in your project
- Only applies to C# files (not other languages)

**Benefits:**
- ✅ Consistent code style across your team
- ✅ No manual formatting needed
- ✅ Fixes StyleCop warnings automatically on save
- ✅ Uses your project's existing style configuration

### 3. Create omnisharp.json

**File**: `~/.omnisharp/omnisharp.json`

```bash
mkdir -p ~/.omnisharp
```

Create the file with these contents:

```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
```

### 4. Restart Neovim

```bash
# Kill any running OmniSharp processes
pkill -f omnisharp

# Start Neovim with a C# file
nvim /path/to/your/project/Program.cs
```

**Done!** StyleCop warnings should now appear inline AND Go to Definition works perfectly! ✅

---

## Why This Works

### The Key Insight

OmniSharp **automatically reads** `~/.omnisharp/omnisharp.json` on startup! This is OmniSharp's **native configuration file** - no Neovim LSP settings conversion needed.

### What We Tried (and Why It Failed)

❌ **Approach 1**: Custom `cmd` with pre-flattened settings
- Problem: lspconfig's default cmd overrides our custom cmd

❌ **Approach 2**: Settings in init.lua's `servers.omnisharp.settings`
- Problem: nvim-lspconfig's `on_new_config` doesn't reliably flatten settings to CLI args

❌ **Approach 3**: Neovim 0.11's new `vim.lsp.config()` API
- Problem: Over-complicated, requires filetypes/root_markers, unnecessary

✅ **Working Solution**: `omnisharp = {}` + `omnisharp.json`
- OmniSharp reads its native config file automatically
- nvim-lspconfig handles all defaults (filetypes, root_dir, cmd)
- Zero complexity, maximum reliability

---

## Verification

### Check OmniSharp is Attached

```vim
:LspInfo
```

Should show:
```
vim.lsp: Active Clients ~
- Client: omnisharp (id: 1, bufnr: [1])
  filetypes: cs, vb
  root_dir: /path/to/your/project
```

### Check Running Process

```bash
ps aux | grep omnisharp | grep -v grep
```

Should show OmniSharp running with `dotnet OmniSharp.dll`.

### Check StyleCop Warnings Appear

Open a C# file with StyleCop violations. You should see inline warnings like:
- SA1505: Opening braces should not be followed by blank line
- SA1508: Closing braces should not be preceded by blank line
- SA1116, SA1117: Parameter placement warnings

---

## Fresh Setup (New Machine)

If starting from scratch:

### 1. Install Neovim 0.11+

```bash
# Check version
nvim --version  # Should be v0.11.0 or newer
```

### 2. Install kickstart.nvim

```bash
# Backup old config
mv ~/.config/nvim ~/.config/nvim.backup

# Clone kickstart.nvim
git clone https://github.com/nvim-lua/kickstart.nvim.git ~/.config/nvim

# Start Neovim (installs plugins automatically)
nvim
```

Wait for Lazy.nvim to install all plugins (~1 minute).

### 3. Add OmniSharp to init.lua

Edit `~/.config/nvim/init.lua`, find the `servers = {` table (around line 680-700), and add:

```lua
servers = {
  -- ... existing servers like lua_ls, pyright, etc. ...

  -- OmniSharp C# LSP
  omnisharp = {},
}
```

### 4. Install OmniSharp via Mason

```vim
:Mason
```

Search for "omnisharp", press `i` to install.

### 5. Create omnisharp.json

```bash
mkdir -p ~/.omnisharp
cat > ~/.omnisharp/omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
EOF
```

### 6. Test with C# Project

```bash
cd /path/to/your/csharp/project
dotnet restore --force-evaluate --no-cache  # Important for WSL2!
nvim Program.cs
```

In Neovim:
```vim
:LspInfo   " Should show omnisharp attached
```

StyleCop warnings should appear inline! ✅

---

## Troubleshooting

### No warnings appearing?

1. **Check omnisharp.json exists and is valid**:
   ```bash
   cat ~/.omnisharp/omnisharp.json
   ```

2. **Check StyleCop.Analyzers is installed in project**:
   ```bash
   grep -r "StyleCop.Analyzers" *.csproj
   ```

   If not installed, add to your .csproj:
   ```xml
   <ItemGroup>
     <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
   </ItemGroup>
   ```

3. **Restart OmniSharp**:
   ```vim
   :LspRestart
   ```

4. **Check LSP logs**:
   ```bash
   tail -100 ~/.local/state/nvim/lsp.log | grep -i "roslyn\|analyzer"
   ```

### WSL2 + Windows Cross-Filesystem Issue

If working on `/mnt/c/...` (Windows filesystem from WSL2), and you compiled in Windows:

```bash
cd /mnt/c/path/to/project
dotnet restore --force-evaluate --no-cache
```

This fixes NuGet package cache issues between Windows and WSL2.

### OmniSharp Not Attaching

1. **Check OmniSharp is installed via Mason**:
   ```bash
   ls ~/.local/share/nvim/mason/packages/omnisharp/
   ```

2. **Check init.lua has omnisharp = {}**:
   ```bash
   grep -A 2 "omnisharp" ~/.config/nvim/init.lua
   ```

3. **Clear cache and restart**:
   ```bash
   rm -rf ~/.cache/nvim/
   pkill -f omnisharp
   nvim your-file.cs
   ```

---

## Known Issues

### ✅ Cursor Position Error - FIXED!

**This error is now FIXED** by using omnisharp-extended-lsp.nvim handlers (Step 1 in solution)!

The error used to be:
```
Error executing vim.schedule lua callback:
...lua/vim/lsp/util.lua:951: Cursor position outside buffer
```

**Solution**: The omnisharp-extended plugin properly handles decompiled .NET Framework sources and metadata files. Go to Definition (`gd`) now works perfectly without errors!

### Deprecation Warning (Can Be Ignored)

```
The `require('lspconfig')` "framework" is deprecated
```

**You can ignore this!** The warning is about lspconfig's **internal implementation**, not your usage. nvim-lspconfig is fully compatible with Neovim 0.11 - you can continue using it normally.

---

## Key Lessons Learned

1. **Don't fight the defaults** - Empty `omnisharp = {}` works better than any custom override
2. **Use native config files** - `omnisharp.json` is more reliable than LSP settings
3. **Keep it simple** - The simplest solution is often the best
4. **Trust nvim-lspconfig** - It knows the correct filetypes, root_dir, and cmd
5. **WSL2 caveat** - Always `dotnet restore --force-evaluate --no-cache` after Windows builds

---

## Success Criteria

- [x] StyleCop warnings appear inline in Neovim ✅
- [x] Go to definition works (`gd`) - even to .NET Framework decompiled sources! ✅
- [x] No "Cursor position outside buffer" errors ✅
- [x] LSP client attaches automatically to .cs files ✅
- [x] Auto-format on save uses .editorconfig, stylecop.json, and .ruleset files ✅
- [x] Works with Neovim 0.11.4 ✅
- [x] Configuration is simple and maintainable ✅

---

## Files in This Repository

- **init.lua** - Fresh kickstart.nvim with minimal OmniSharp config
- **omnisharp.json** - OmniSharp settings (copy to `~/.omnisharp/`)
- **Claude.md** - This documentation (working solution only)
- **SETUP_COMPLETE.md** - Detailed verification documentation

---

## 🔧 TROUBLESHOOTING - Nach Neustart funktioniert es nicht?

### Checklist wenn OmniSharp nicht funktioniert:

```bash
# 1. Sind die Files am richtigen Ort?
ls ~/.config/nvim/init.lua        # Sollte existieren
ls ~/.omnisharp/omnisharp.json    # Sollte existieren

# 2. Ist OmniSharp via Mason installiert?
ls ~/.local/share/nvim/mason/packages/omnisharp/

# 3. Ist omnisharp-extended Plugin installiert?
ls ~/.local/share/nvim/lazy/omnisharp-extended-lsp.nvim/

# 4. Cache clearen und neu starten
rm -rf ~/.cache/nvim/
pkill -f omnisharp
nvim your-file.cs
```

### Wenn Plugins nicht installiert sind:

```vim
" In Neovim:
:Lazy sync          " Installiert alle Plugins neu
:Mason              " Öffnet Mason, dann 'omnisharp' suchen und 'i' drücken
```

### Wenn NuGet Packages fehlen (WSL2):

```bash
cd /mnt/c/path/to/your/project
dotnet restore --force-evaluate --no-cache
```

### Debug Commands:

```vim
:LspInfo            " Zeigt ob OmniSharp attached ist
:Lazy               " Zeigt installierte Plugins
:Mason              " Zeigt installierte LSP servers
:checkhealth        " Prüft gesamte Neovim setup
```

### Wenn ALLES fehlschlägt - Nuclear Option:

```bash
# Komplett von vorne (löscht alle Neovim Daten!)
rm -rf ~/.config/nvim ~/.local/share/nvim ~/.local/state/nvim ~/.cache/nvim

# Dann von QUICK START folgen (oben)
cd /path/to/KickStartNeoVim
cp init.lua ~/.config/nvim/init.lua
# ... etc
```

---

## 🎯 Additional Features Configured

### Neogit - Git UI

**Installed**: `NeogitOrg/neogit` with `diffview.nvim`

**Keybinding**: `<leader>gg` - Open Neogit UI

**Usage**:
- `?` - Show help
- `s` - Stage file/hunk
- `u` - Unstage
- `c` - Commit
- `P` - Push
- `F` - Pull
- `q` - Quit

### Telescope Diagnostics Filtering

**New Keybindings**:
- `<leader>sd` - Search all [D]iagnostics (Errors + Warnings + Hints)
- `<leader>sW` - Search [W]arnings only (StyleCop, etc.)
- `<leader>sE` - Search [E]rrors only

**Why useful**: Quickly filter only StyleCop warnings without seeing errors/hints!

### Lazy Plugin Manager

**Command**: `:Lazy`

**In Lazy window**:
- `I` - Install new plugins
- `U` - Update all plugins
- `X` - Clean unused plugins
- `S` - Sync (clean + update)
- `?` - Help
- `q` - Quit

### Markdown Preview with Mermaid Support

**Installed**: `iamcco/markdown-preview.nvim` (7,540+ GitHub stars, industry standard)

**Keybinding**: `<leader>mp` - Toggle Markdown Preview

**Features**:
- ✅ Browser-based live preview with synchronized scrolling
- ✅ **Full Mermaid diagram support** (flowcharts, sequence, Gantt, etc.)
- ✅ PlantUML, Chart.js, Graphviz DOT diagrams
- ✅ KaTeX math equations
- ✅ GitHub-flavored markdown rendering
- ✅ Auto-updates on file changes
- ✅ Dark/light theme support

**Usage**:
1. Open any `.md` file
2. Press `<leader>mp` to toggle preview
3. Browser opens with live preview
4. Edit file - preview updates automatically
5. Press `<leader>mp` again to close

**Requirements**:
- Node.js and npm (install: `sudo apt install nodejs npm`)
- First-time setup: `cd ~/.local/share/nvim/lazy/markdown-preview.nvim/app && npm install`

**Why this plugin**: Most popular markdown preview solution in the Neovim ecosystem, default in LazyVim, NvChad, and AstroNvim distributions.

---

## 🎮 Keybindings Reference (DCSRE Project)

### Backend Operations (Bash/WSL2)

These commands run in WSL2/Bash for normal development workflow:

**`<leader>rbw`** - **[R]un [B]ackend [W]ebhost**
- Starts the ASP.NET Core WebHost API server
- Runs on: `https://localhost:5443` (Swagger UI available at `/swagger`)
- Project: `VDEK.DCSP.WebHost`
- Environment: Development mode with auto-loaded environment variables
- Uses: `dotnet run --no-restore`
- Terminal: Opens in horizontal split via toggleterm

**`<leader>rbs`** - **[R]un [B]ackend [S]etup (Migrations)**
- Executes FluentMigrator database migrations
- Creates/updates database schema
- Project: `VDEK.DCSP.Setup`
- Uses: `dotnet run --project VDEK.DCSP.Setup`
- Terminal: Opens in horizontal split via toggleterm

**Path**: `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/`

---

### Frontend Operations (Bash/WSL2)

These commands run in WSL2/Bash for frontend development:

**`<leader>rfr`** - **[R]un [F]ront [R]un (dev server)**
- Starts the Angular/NX development server
- Runs on: `https://localhost:8443` (with SSL certificates)
- Project: `app-standalone` (NX monorepo app)
- Uses: `npm start` (which runs `nx serve app-standalone`)
- Terminal: Opens in horizontal split via toggleterm

**`<leader>rfb`** - **[R]un [F]ront [B]uild (production)**
- Builds the Angular app for production
- Creates optimized distribution in `dist/` folder
- Project: `app-standalone`
- Uses: `npm run build` (which runs `npx nx build app-standalone`)
- Terminal: Opens in horizontal split via toggleterm

**`<leader>rfi`** - **[R]un [F]ront [I]nstall (npm install)**
- Installs/reinstalls all npm dependencies
- Useful after git pulls or when package.json changes
- Uses: `npm install`
- Terminal: Opens in horizontal split via toggleterm

**`<leader>rft`** - **[R]un [F]ront [T]est (jest)**
- Executes Jest unit tests
- Runs tests for all frontend apps and libraries
- Uses: `npm test` (which runs `npx nx run-many --all --target=test`)
- Terminal: Opens in horizontal split via toggleterm

**Path**: `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Frontend/`

---

### Git Operations (PowerShell/Windows - VPN Access)

**⚠️ IMPORTANT**: These commands run via PowerShell/Windows because VPN is **only accessible through the Windows system**. Git push/pull fail in WSL2/Linux due to network restrictions.

**`<leader>rp`** - **[R]un [P]ush (DCSRE)**
- Pushes commits to DCSRE remote repository
- Uses: `powershell.exe -Command "git push"`
- Path: `C:\Users\Administrator\Documents\Work\Code2\DCSRE`
- Terminal: Opens in horizontal split with `pause` (keeps window open to see errors)

**`<leader>rP`** - **[R]un [P]ull (DCSRE)**
- Pulls latest changes from DCSRE remote repository
- Uses: `powershell.exe -Command "git pull"`
- Path: `C:\Users\Administrator\Documents\Work\Code2\DCSRE`
- Terminal: Opens in horizontal split with `pause`

**Why PowerShell?** The VPN connection required for DCSRE git operations is only available through the Windows network stack, not through WSL2. All other development tasks (building, running, testing) work normally in WSL2.

---

### TFS/Git Operations

**`<leader>rc`** - **[R]un [C]ommit (open in TFS browser)**
- Opens the commit hash from clipboard in Azure DevOps TFS browser
- Pre-requisite: Copy commit hash to clipboard (e.g., via `yy` in Neogit commit view)
- Opens in Chrome: `https://tfs.itsg.de/tfs/ITSGCollection/DCS_Pflege/_git/DCSRE/commit/{hash}`
- Works in both WSL2 and Windows versions

**`<leader>gg`** - **Open Neogit UI**
- Interactive git interface for staging, committing, viewing diffs
- See "Neogit - Git UI" section above for usage

**`<leader>gf`** - **[G]it [F]ile history (diff)**
- Opens Diffview with complete commit history for the current file
- Shows all commits that modified this file with diffs
- Navigate with `[c` / `]c` (previous/next commit)
- Close with `<leader>gdc`

**`<leader>gD`** - **[G]it [D]iff vs develop**
- Opens Diffview comparing current branch with `origin/develop`
- Shows all changed files in a diff panel
- For DCSRE project workflow

**`<leader>gM`** - **[G]it diff vs [M]ain**
- Opens Diffview comparing current branch with `origin/main`
- For CENCOCD project workflow

**`<leader>gdc`** - **[G]it [D]iff [C]lose**
- Closes all Diffview panels

---

### Clipboard Operations

**`<leader>yp`** - **[Y]ank [P]ath (relative)**
- Copies the relative file path from project root
- Example: `Sources/Backend/VDEK.DCSP.WebHost/Program.cs`
- Useful for sharing file locations in documentation or tickets

**`<leader>yn`** - **[Y]ank [N]ame (filename only)**
- Copies only the filename without path
- Example: `Program.cs`
- Useful for quick file references

---

### Dual Configuration (WSL2 vs Windows)

This repository contains **two separate init.lua configurations**:

1. **`init.lua`** (WSL2/Linux - Primary)
   - Location: `~/.config/nvim/init.lua`
   - Uses WSL2 paths: `/mnt/c/Users/...`
   - Git operations via PowerShell (VPN requirement)
   - Backend operations via Bash (normal dev workflow)

2. **`init_windows.lua`** (Windows Native)
   - Location: `%LOCALAPPDATA%\nvim\init.lua` → `C:\Users\Administrator\AppData\Local\nvim\init.lua`
   - Uses Windows paths: `C:\Users\...`
   - All operations via PowerShell
   - For use when running Neovim natively in Windows PowerShell/CMD

**To use Windows version:**
```powershell
# Windows PowerShell
cd C:\Users\Administrator\Documents\Projekt\KickStartNeoVim
Copy-Item init_windows.lua $env:LOCALAPPDATA\nvim\init.lua
```

**Check config path in Neovim:**
```vim
:echo stdpath('config')
```

**Why two configs?** Cross-filesystem operations between WSL2 and Windows can cause path resolution issues. Separate configs ensure reliable operation in each environment.

---

## 🎮 CENCOCD Project Keybindings

**Auto-Detection**: Keybindings automatically adapt when working in the CENCOCD/Kluger project folder!

### Backend (CENCOCD)

**`<leader>rbw`** - **[R]un [B]ackend [W]ebhost**
- Starts the ASP.NET Core API server with `https` launch profile
- Project: `CenCoCo.Core.API`
- Path: `/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API`

### Frontend (CENCOCD - Blazor)

**`<leader>rfw`** - **[R]un [F]rontend [W]eb (Blazor)**
- Starts the Blazor WebAssembly frontend
- Project: `CenCoCo.Core.Blazor`
- Path: `/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.Blazor`

### Docker Operations (Projekt-spezifisch!)

**`<leader>rDi`** - **[R]un [D]ocker [I]nfrastructure UP** (capital D!)

| Projekt | Befehl |
|---------|--------|
| DCSRE | `.\docker-up.ps1 -EnvFile .env.noproxy -Profile dev-backend -SkipTests` |
| CENCOCD | `docker compose up -d` |

**`<leader>rDa`** - **[R]un [D]ocker [A]ll** (DCSRE only!)

| Projekt | Befehl |
|---------|--------|
| DCSRE | `.\docker-up.ps1 -EnvFile .env.noproxy -Profile all -SkipTests` |

**`<leader>rDI`** - **[R]un [D]ocker [I]nfrastructure DOWN** (capital D and I!)

| Projekt | Befehl |
|---------|--------|
| DCSRE | `docker compose -p dcsp down -v` |
| CENCOCD | `docker compose down -v` |

**Pfade:**
- DCSRE: `C:\Users\Administrator\Documents\Work\Code2\DCSRE\Sources`
- CENCOCD: `C:\Users\Administrator\Documents\Work\Kluger\cencoco\src`

**⚠️ Note**: The `D` is capital to avoid conflict with `<leader>rd` (diagnostics).

---

## 🔍 Search Terminals Feature

**`<leader>st`** - **[S]earch [T]erminals**
- Opens Telescope picker with all named terminals
- Shows terminal status: ● (open/visible) or ○ (hidden/background)
- Press `<Enter>` to toggle/open terminal
- Press `<C-d>` to close/kill terminal

**Named Terminals**:
| ID | Name | Description |
|----|------|-------------|
| 1 | Default | Standard terminal |
| 10 | Backend | Generic backend work |
| 11 | Frontend Dev | Generic frontend work |
| 20 | Backend WebHost | DCSRE/CENCOCD API server |
| 21 | Frontend | DCSRE Angular/NX server |
| 22 | Docker Infra | CENCOCD Docker services |
| 30 | E2E Playwright | Playwright tests |
| 31 | E2E Headed | Headed browser tests |
| 32 | Cypress UI | Cypress test runner |

---

## 🔇 Diagnostic Filter (Personal)

A personal diagnostic filter is configured in init.lua to hide specific Roslyn/OmniSharp warnings **only in Neovim** (doesn't affect team via .editorconfig).

**Location**: init.lua, search for `ignored_diagnostics`

**How to use**:
```lua
local ignored_diagnostics = {
  -- Uncomment any code you want to hide:
  -- 'IDE0008',  -- Use explicit type instead of 'var'
  -- 'IDE0058',  -- Expression value is never used
  -- 'CA1707',   -- Identifiers should not contain underscores
  -- 'CA1822',   -- Mark members as static
  -- 'SA1600',   -- Elements should be documented
}
```

**Benefits**:
- Personal preference, doesn't affect colleagues
- Team still sees all warnings in Rider/VS
- Can be different per machine (WSL vs Windows)

---

## 🔑 Quick Keybindings Cheat Sheet

```
Git & TFS
---------
<leader>gg   → Open Neogit UI
<leader>gf   → Git File history (diff for current file)
<leader>gD   → Git Diff vs develop
<leader>gM   → Git diff vs Main
<leader>gdc  → Git Diff Close (all panels)
<leader>rc   → Open commit in TFS browser (from clipboard)
<leader>rp   → Git Push (DCSRE - PowerShell/VPN)
<leader>rP   → Git Pull (DCSRE - PowerShell/VPN)

Backend (WSL2)
--------------
<leader>rbw  → Run Backend WebHost (https://localhost:5443/swagger)
<leader>rbs  → Run Backend Setup (Migrations)

Frontend (WSL2 - DCSRE)
-----------------------
<leader>rfr  → Run Frontend dev server (Angular/NX - https://localhost:8443)
<leader>rfb  → Run Frontend Build (production)
<leader>rfi  → Run Frontend Install (npm install)
<leader>rft  → Run Frontend Test (jest)

Frontend (WSL2 - CENCOCD)
-------------------------
<leader>rfw  → Run Frontend Web (Blazor)

Docker (Projekt-spezifisch!)
---------------------------
<leader>rDi  → Docker UP (DCSRE: -Profile dev-backend, CENCOCD: docker compose up)
<leader>rDa  → Docker ALL (DCSRE only: -Profile all)
<leader>rDI  → Docker DOWN (DCSRE: -p dcsp down -v, CENCOCD: down -v)

Terminals
---------
<leader>st   → Search Terminals (Telescope picker)

Clipboard
---------
<leader>yp   → Yank relative path
<leader>yn   → Yank filename only

Diagnostics
-----------
<leader>sd   → Search all Diagnostics
<leader>sW   → Search Warnings only (StyleCop)
<leader>sE   → Search Errors only

Markdown
--------
<leader>mp   → Markdown Preview (Browser with Mermaid support)
```

---

**This is the working solution! 🎉**

Last verified: 2025-12-12
Neovim version: v0.11.4
OmniSharp version: 1.39.14
