# Minimal OmniSharp Configuration - Quick Start Guide

## What is This?

This is a **30-line** OmniSharp LSP configuration for Neovim 0.11 with **zero plugins** required.

## Files Created

1. **minimal_omnisharp.lua** (30 lines)
   - Basic working config
   - Uses `settings = { ... }` table (settings sent via LSP initialization)
   - **Limitation**: Settings not converted to command-line args

2. **minimal_omnisharp_complete.lua** (120 lines with comments, ~40 lines code)
   - Complete working config
   - All settings added as command-line args
   - **Recommended**: Most compatible, no nvim-lspconfig needed

3. **MINIMAL_OMNISHARP_ANALYSIS.md**
   - Full technical breakdown
   - Comparison with current config
   - Migration options

## Quick Test (30 seconds)

### Step 1: Edit Solution Path

Open `minimal_omnisharp_complete.lua` and change line 30:

```lua
local solution_path = vim.fn.expand('/mnt/c/path/to/your/solution')
```

### Step 2: Kill Existing OmniSharp

```bash
pkill -f omnisharp
```

### Step 3: Test

```bash
nvim -u /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/minimal_omnisharp_complete.lua \
     /path/to/your/CSharpFile.cs
```

### Step 4: Verify

Inside Neovim:

```vim
:lua =vim.lsp.get_clients()
```

Should show `omnisharp` client.

Test keybinds:
- `gd` - Go to definition
- `K` - Hover documentation
- `]d` - Next diagnostic (StyleCop warnings should appear here!)

## What Makes This Work?

### Required Components (5 things)

1. **Neovim 0.11+** ✅ (you have 0.11.4)
   ```bash
   nvim --version  # NVIM v0.11.4
   ```

2. **OmniSharp.dll** ✅ (installed via Mason)
   ```bash
   ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
   ```

3. **.NET SDK** ✅ (required for `dotnet` command)
   ```bash
   dotnet --version  # Should show .NET version
   ```

4. **Solution path** ✅ (directory containing .sln file)
   ```
   -s /path/to/solution
   ```

5. **Enable analyzers** ✅ (for StyleCop warnings)
   ```
   RoslynExtensionsOptions:EnableAnalyzersSupport=true
   ```

### What's NOT Required

- ❌ Mason (just an installer, not runtime)
- ❌ mason-lspconfig (bridge plugin, unnecessary)
- ❌ nvim-lspconfig (convenience plugin, not needed)
- ❌ lazy.nvim (plugin manager, not needed)
- ❌ blink.cmp (completion, optional)
- ❌ conform.nvim (formatting, optional)

## Key Differences from Your Current Config

### Current Config (init.lua)

```lua
-- Lines 702-723: OmniSharp in servers table
omnisharp = {
  cmd = { 'dotnet', '...', '-s', '...', '-loglevel', 'Information' },
  settings = {
    RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... },
    FormattingOptions = { ... },
  },
}

-- Lines 745-783: Complex loop with mason-lspconfig
require('mason-lspconfig').setup { ... }
for server_name, server_config in pairs(servers) do
  if vim.fn.has('nvim-0.11') == 1 then
    vim.lsp.config(server_name, config)
    -- ... 20+ lines of logic
  else
    require('lspconfig')[server_name].setup(config)
  end
end
```

**Issues:**
- Relies on nvim-lspconfig's `on_new_config` to flatten settings
- Complex conditional for Neovim 0.10 vs 0.11
- Settings in `settings = { ... }` not guaranteed to become command-line args

### Minimal Config (minimal_omnisharp_complete.lua)

```lua
vim.lsp.config('omnisharp', {
  cmd = {
    'dotnet', '/path/to/OmniSharp.dll',
    '-s', '/path/to/solution',
    '-loglevel', 'Information',
    'RoslynExtensionsOptions:EnableAnalyzersSupport=true',  -- Direct arg!
    'FormattingOptions:EnableEditorConfigSupport=true',
    -- ... all settings as args
  },
  filetypes = { 'cs' },
  root_dir = vim.fs.root(0, { '*.sln', '*.csproj' }),
})

vim.api.nvim_create_autocmd('FileType', {
  pattern = 'cs',
  callback = function(ev)
    vim.lsp.enable('omnisharp', ev.buf)
  end,
})
```

**Benefits:**
- Direct command-line args (no flattening needed)
- No plugin dependencies
- Explicit and simple (30 lines)

## Understanding the Command-Line Args

OmniSharp accepts two types of arguments:

### 1. Standard Arguments (dash prefix)

```
-s /path/to/solution         # Solution/project path
-loglevel Information        # Logging level
-z                           # Zero-based line numbers
--hostPID 12345             # Parent process ID
--encoding utf-8            # Communication encoding
--languageserver            # Language server protocol mode
```

### 2. Configuration Arguments (Key=Value or Key:Subkey=Value)

```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
FormattingOptions:EnableEditorConfigSupport=true
FormattingOptions:OrganizeImports=true
Sdk:IncludePrereleases=true
DotNet:enablePackageRestore=false
```

**Critical insight:**
nvim-lspconfig's `on_new_config` converts this:

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  },
}
```

To this command-line arg:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

**Without nvim-lspconfig**, you must do this manually!

## Verification Checklist

After starting Neovim with the minimal config:

### 1. LSP Client is Running

```vim
:lua =vim.lsp.get_clients()
```

Expected:
```lua
{
  {
    id = 1,
    name = 'omnisharp',
    attached_buffers = { ... },
  }
}
```

### 2. OmniSharp Process is Correct

```bash
ps aux | grep omnisharp | grep -v grep
```

Expected to see:
```
dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /mnt/c/.../your/solution \
  -loglevel Information \
  -z --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  FormattingOptions:EnableEditorConfigSupport=true
```

### 3. Hover Works

Place cursor on a C# symbol, press `K`.

Expected: Floating window with documentation.

### 4. Go to Definition Works

Place cursor on a method call, press `gd`.

Expected: Jump to method definition.

### 5. Diagnostics Appear

Open a C# file with issues (or create violations).

Expected: Red/yellow underlines, signs in gutter.

Check:
```vim
:lua =vim.diagnostic.get(0)
```

Should show array of diagnostics including StyleCop warnings (SA11xx codes).

### 6. Logs Show Analyzer Loading

```bash
tail -f ~/.local/state/nvim/lsp.log | grep -i analyzer
```

Expected:
```
[INFO] Found analyzer: StyleCop.Analyzers
[INFO] Enabled analyzers: 123
```

## Troubleshooting

### Issue: "No LSP client attached"

**Check:**
```vim
:lua =vim.lsp.get_clients()
```

If empty:
1. Verify OmniSharp.dll path exists
2. Check `dotnet` is in PATH
3. Look at `:messages` for error

### Issue: No StyleCop Warnings

**Verify StyleCop is installed:**
```bash
grep StyleCop /path/to/your/project/*.csproj
```

Expected:
```xml
<PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
```

**Check .editorconfig exists:**
```bash
ls /path/to/solution/.editorconfig
```

**Check analyzer is loaded:**
```bash
tail ~/.local/state/nvim/lsp.log | grep -i stylecop
```

### Issue: OmniSharp Crashes

**Check logs:**
```bash
tail -100 ~/.local/state/nvim/lsp.log
```

**Common causes:**
- Solution path wrong (no .sln file)
- .NET SDK version mismatch
- Corrupted OmniSharp installation

**Solution:**
```bash
# Reinstall OmniSharp via Mason
nvim
:MasonUninstall omnisharp
:MasonInstall omnisharp
```

### Issue: Settings Not Applied

**Verify process has the args:**
```bash
ps aux | grep omnisharp | grep EnableAnalyzersSupport
```

If missing:
1. You're using `settings = { ... }` table (doesn't work without nvim-lspconfig)
2. Use `minimal_omnisharp_complete.lua` instead (has direct command-line args)

## Migration Path for Your Current Config

You have **3 options**:

### Option 1: Keep Everything (Recommended)

Your current config is working now. No need to change.

**Benefit**: Everything works, feature-complete.
**Drawback**: More complex than necessary.

### Option 2: Simplify OmniSharp Only

Keep all plugins, just simplify the server loop:

**Change**: Lines 754-783 in init.lua
**From**: Complex conditional with Neovim 0.10 fallback
**To**: Direct `vim.lsp.config()` call (remove fallback)

**Benefit**: Cleaner code, no old Neovim version support.
**Drawback**: Still depends on nvim-lspconfig for flattening.

### Option 3: Go Minimal (Not Recommended for Daily Use)

Replace entire LSP setup with minimal config.

**Benefit**: Understand exactly what's happening.
**Drawback**: Lose completion, formatting, other LSPs.

## Recommendation

**For learning**: Test `minimal_omnisharp_complete.lua` to understand the core requirements.

**For daily use**: Keep your current config (`init.lua`). It's working and provides many useful features.

**For future configs**: Start with minimal approach, add plugins as needed.

## Next Steps

1. ✅ Test minimal config (verify it works)
2. ✅ Read analysis document (understand differences)
3. ✅ Decide: keep current config or simplify?
4. ✅ If issues arise, you now have a 30-line reference config to compare against

## Summary

**What you created:**
- 30-line OmniSharp config with zero plugins
- Complete technical analysis
- Migration path documentation

**What you learned:**
- Mason is just an installer (not runtime dependency)
- nvim-lspconfig provides conveniences (not required)
- Settings flattening must be manual without nvim-lspconfig
- Neovim 0.11 native APIs are powerful and simple

**Key files:**
- `minimal_omnisharp_complete.lua` - Use this for testing
- `MINIMAL_OMNISHARP_ANALYSIS.md` - Read this for deep understanding
- `MINIMAL_OMNISHARP_QUICK_START.md` - This file (quick reference)

---

**End of Quick Start Guide**
