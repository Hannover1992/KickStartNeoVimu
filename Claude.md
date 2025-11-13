# ✅ OmniSharp StyleCop Warnings - WORKING SOLUTION

**Date**: 2025-11-13
**Status**: ✅ **VERIFIED WORKING**
**Neovim Version**: v0.11.4

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
- [x] Works with Neovim 0.11.4 ✅
- [x] Configuration is simple and maintainable ✅

---

## Files in This Repository

- **init.lua** - Fresh kickstart.nvim with minimal OmniSharp config
- **omnisharp.json** - OmniSharp settings (copy to `~/.omnisharp/`)
- **Claude.md** - This documentation (working solution only)
- **SETUP_COMPLETE.md** - Detailed verification documentation

---

**This is the working solution! 🎉**

Last verified: 2025-11-13
Neovim version: v0.11.4
OmniSharp version: 1.39.14
