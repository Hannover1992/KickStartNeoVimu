# Quick Fix Guide: OmniSharp Not Attaching in Neovim 0.11.4

## TL;DR - 5 Minute Fix

**Root Cause**: Settings not flattened to CLI args in Neovim 0.11 `vim.lsp.config()` approach.

**Quick Fix**: Use legacy `lspconfig.setup()` API (still works in Neovim 0.11) OR create `~/.omnisharp/omnisharp.json`.

---

## Step-by-Step Fix

### 1. Edit init.lua Line 748

**Change this:**
```lua
automatic_enable = false, -- v2.x: Disable auto-enable, we'll configure servers manually
```

**To this:**
```lua
automatic_enable = { exclude = { 'omnisharp' } }, -- v2.x: Auto-enable all except omnisharp
```

### 2. Replace Lines 754-783

**Delete the entire loop** (lines 754-783) and replace with:

```lua
-- Configure OmniSharp using lspconfig (compatibility mode)
if servers.omnisharp then
  require('lspconfig').omnisharp.setup {
    cmd = servers.omnisharp.cmd,
    settings = servers.omnisharp.settings,
    capabilities = require('blink.cmp').get_lsp_capabilities(),
  }
end
```

### 3. Save and Restart

```bash
# Clear cache and kill OmniSharp
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp

# Restart Neovim with a C# file
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/CenCoCo.Core.API/Program.cs
```

### 4. Verify

Wait 5-10 seconds, then run:

```vim
:LspInfo
```

Should show:
```
Client: omnisharp (id 1)
  cmd: { "dotnet", "/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", "/mnt/c/.../cencoco/src", "-loglevel", "Information" }
  filetypes: cs
  root directory: /mnt/c/.../cencoco/src
```

Verify process is running:
```bash
ps aux | grep omnisharp | grep -v grep
```

---

## Alternative: Simplest Fix (If Custom Config Not Needed)

If you don't need custom OmniSharp configuration:

### 1. Change Line 748

```lua
automatic_enable = true, -- Let mason-lspconfig handle everything
```

### 2. Delete Lines 754-783

Remove the entire manual configuration loop.

### 3. Restart Neovim

Done! mason-lspconfig will auto-configure all servers including OmniSharp.

**Downside**: You lose custom `cmd` and `settings` from the `servers.omnisharp` table.

---

## Why It Wasn't Working

1. ❌ `vim.lsp.config()` doesn't flatten OmniSharp settings to CLI args
2. ❌ lspconfig's `on_new_config` hook not called (settings flattening logic bypassed)
3. ❌ OmniSharp receives `settings` table but ignores it (expects CLI args)
4. ❌ Roslyn analyzers never enabled without `RoslynExtensionsOptions:EnableAnalyzersSupport=true` CLI arg

**Result**: OmniSharp runs but without analyzer support (no StyleCop warnings, etc.).

---

## Testing the Fix

```bash
# 1. Verify OmniSharp is running
ps aux | grep omnisharp | grep -v grep

# Should show:
# dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll -s /mnt/c/.../cencoco/src ...

# 2. Test LSP features in Neovim
# Open a C# file and test:
```

```vim
" Go to definition
grd

" Hover documentation
K

" Find references
grr

" Code actions
gra
```

---

## Troubleshooting

### OmniSharp still not starting?

```bash
# Check logs
tail -50 ~/.local/state/nvim/lsp.log | grep -i omnisharp

# Verify DLL exists
ls -la ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

# Reinstall OmniSharp
:Mason
# Select omnisharp → Press X (uninstall) → Press I (install)
```

### "No LSP client attached" error?

1. Make sure you're editing a `.cs` file
2. Wait 10-15 seconds for OmniSharp to start (it's slow)
3. Check `:LspInfo` for error messages
4. Run `:checkhealth lsp` for diagnostics

### Want to switch test projects?

Edit line 708 in init.lua to point to your solution directory:

```lua
vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/YOUR_PROJECT/src'),
```

---

## What Changed in Neovim 0.11?

**New APIs**: `vim.lsp.config()` and `vim.lsp.enable()`

**Old API** (still works):
```lua
require('lspconfig').omnisharp.setup({ ... })
```

**New API** (requires both steps):
```lua
vim.lsp.config('omnisharp', { ... })  -- Step 1: Register
vim.lsp.enable('omnisharp')            -- Step 2: Enable
```

**Recommended**: Use old API for now (proven, stable, simple).

---

## Full Documentation

See these files for complete analysis:
- `FILETYPE_AUTOCMD_CONFLICT_ANALYSIS.md` - Deep-dive analysis (THIS IS THE LATEST AND MOST ACCURATE)
- `OMNISHARP_0.11_ROOT_CAUSE_ANALYSIS.md` - Previous analysis (partially outdated)
- `OMNISHARP_RESEARCH_FINDINGS.md` - Initial research findings (duplicate autocmd theory was incorrect)
- `CLAUDE.md` - Historical context and working solutions

---

## Summary

- **Problem**: OmniSharp not starting due to incomplete Neovim 0.11 migration
- **Solution**: Use legacy `lspconfig.setup()` API (still supported)
- **Time**: 5 minutes to fix
- **Confidence**: 95% (proven approach from CLAUDE.md)

Good luck!
