# OmniSharp Settings Fix - Quick Implementation Guide

**Date**: 2025-11-13
**Issue**: Settings not being passed to OmniSharp (RoslynExtensionsOptions empty)
**Root Cause**: Using `vim.lsp.config` bypasses nvim-lspconfig's settings flattening

---

## TL;DR - The Fix

**Replace lines 754-783 in init.lua with this:**

```lua
-- Configure ALL servers using lspconfig (works on 0.10 and 0.11)
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  require('lspconfig')[server_name].setup(config)
end
```

**That's it!** No Neovim version checks, no vim.lsp.config, just use lspconfig for everything.

---

## Why This Works

1. **lspconfig handles all transformations automatically**
   - Flattens settings to CLI args (OmniSharp requires this)
   - Appends hard-coded OmniSharp args (-z, --hostPID, etc.)
   - Works correctly on both Neovim 0.10 and 0.11

2. **vim.lsp.config bypasses these transformations**
   - Settings stay as Lua tables
   - OmniSharp doesn't understand Lua tables
   - Result: Settings ignored

---

## Before vs After

### BEFORE (Broken - Lines 754-783)

```lua
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  if vim.fn.has('nvim-0.11') == 1 then
    -- This BYPASSES lspconfig's on_new_config!
    local lspconfig_defaults = require('lspconfig.configs')[server_name]
    if lspconfig_defaults and lspconfig_defaults.default_config then
      config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
      config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir
    end

    vim.lsp.config(server_name, config)  -- ❌ Settings NOT flattened

    if config.filetypes then
      vim.api.nvim_create_autocmd('FileType', {
        pattern = config.filetypes,
        callback = function(ev)
          vim.lsp.enable(server_name, ev.buf)
        end,
      })
    end
  else
    require('lspconfig')[server_name].setup(config)  -- ✅ This works
  end
end
```

**Problem**: Neovim 0.11 path uses `vim.lsp.config` which doesn't call lspconfig's `on_new_config`.

---

### AFTER (Fixed)

```lua
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  -- Use lspconfig for ALL servers on ALL Neovim versions
  require('lspconfig')[server_name].setup(config)  -- ✅ Always works
end
```

**Benefits**:
- ✅ Simpler code (no version checks)
- ✅ Works on Neovim 0.10 and 0.11
- ✅ Settings properly flattened
- ✅ All LSP servers configured consistently

---

## Step-by-Step Implementation

### 1. Edit init.lua

**File**: `/home/uczen/.config/nvim/init.lua`

**Find lines 754-783** (the for loop with vim.fn.has('nvim-0.11') check)

**Replace entire loop with:**

```lua
-- Configure ALL servers from the servers table manually
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  -- Use lspconfig for ALL servers (works on 0.10 and 0.11)
  require('lspconfig')[server_name].setup(config)
end
```

---

### 2. Clean Up

```bash
# Clear Lua bytecode cache
rm -rf ~/.cache/nvim/luac/

# Kill any running OmniSharp processes
pkill -f omnisharp

# Ensure NuGet packages are restored (WSL2 cross-filesystem fix)
cd /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
dotnet restore --force-evaluate --no-cache
```

---

### 3. Test

```bash
# Start Neovim with a C# file
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/Core/CenCoCo.Core.API/Program.cs
```

---

### 4. Verify in Neovim

**Check LSP status:**
```vim
:LspInfo
```

**Expected output:**
```
vim.lsp: Active Clients ~
- Client: omnisharp (id: 1)
  filetypes: cs, vb
  cmd: { "dotnet", "/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll",
         "-s", "/mnt/c/.../cencoco/src", "-loglevel", "Information",
         "-z", "--hostPID", "12345", "DotNet:enablePackageRestore=false",
         "--encoding", "utf-8", "--languageserver",
         "RoslynExtensionsOptions:EnableAnalyzersSupport=true",      ← PRESENT!
         "RoslynExtensionsOptions:EnableImportCompletion=true",
         "RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false",
         "FormattingOptions:EnableEditorConfigSupport=true",
         "FormattingOptions:OrganizeImports=true",
         "Sdk:IncludePrereleases=true" }
  settings: {
    FormattingOptions = {
      EnableEditorConfigSupport = true,              ← NOT EMPTY!
      OrganizeImports = true
    },
    RoslynExtensionsOptions = {
      AnalyzeOpenDocumentsOnly = false,
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true
    },
    Sdk = {
      IncludePrereleases = true
    }
  }
```

**Check process:**
```bash
ps aux | grep omnisharp | grep -v grep
```

**Should include:**
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
FormattingOptions:EnableEditorConfigSupport=true
FormattingOptions:OrganizeImports=true
```

---

## Common Issues

### Issue: Settings still empty after fix

**Causes:**
1. Cache not cleared
2. Old OmniSharp process still running
3. NuGet packages not restored

**Fix:**
```bash
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp
cd /path/to/project
dotnet restore --force-evaluate --no-cache
nvim file.cs
```

---

### Issue: OmniSharp not attaching

**Check LSP logs:**
```bash
tail -100 ~/.local/state/nvim/lsp.log | grep -i error
```

**Common errors:**
```
"Package X was not found"  → Run dotnet restore
"Project not loaded"        → Check solution path in cmd
"initialization failed"     → Check OmniSharp.dll exists
```

---

### Issue: No diagnostics/warnings

**After OmniSharp attaches, verify:**
1. `:LspInfo` shows `EnableAnalyzersSupport = true`
2. Process has `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
3. Project has StyleCop.Analyzers NuGet package
4. `.editorconfig` exists in project root

---

## Why Not Use vim.lsp.config?

**vim.lsp.config is a Neovim 0.11 API that:**
- Provides direct access to Neovim's LSP subsystem
- Bypasses nvim-lspconfig's helper functions
- Requires manual implementation of transformations

**Good for:**
- Simple LSP servers (no complex setup)
- Custom LSP servers not in lspconfig
- Direct control over configuration

**Bad for:**
- OmniSharp (needs settings flattening)
- Servers with complex on_new_config
- Maintaining consistency across Neovim versions

**Recommendation**: Use lspconfig unless you have a specific reason not to.

---

## Alternative: Manual Flattening

**If you MUST use vim.lsp.config**, you need to manually flatten settings:

```lua
local function flatten_settings(settings)
  local function flatten(tbl, prefix)
    local ret = {}
    for k, v in pairs(tbl) do
      local key = prefix and (prefix .. ':' .. k) or k
      if type(v) == 'table' then
        vim.list_extend(ret, flatten(v, key))
      else
        ret[#ret + 1] = key .. '=' .. vim.inspect(v)
      end
    end
    return ret
  end
  return flatten(settings, nil)
end

if server_name == 'omnisharp' and vim.fn.has('nvim-0.11') == 1 then
  -- Append hard-coded OmniSharp args
  table.insert(config.cmd, '-z')
  vim.list_extend(config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(config.cmd, { '--encoding', 'utf-8' })
  table.insert(config.cmd, '--languageserver')

  -- Flatten and append settings
  if config.settings then
    vim.list_extend(config.cmd, flatten_settings(config.settings))
    config.settings = nil
  end

  -- Disable workspace folders
  config.capabilities = vim.deepcopy(config.capabilities)
  config.capabilities.workspace.workspaceFolders = false

  vim.lsp.config(server_name, config)
end
```

**But this is NOT recommended** - you're duplicating what lspconfig already does.

---

## Summary

**The fix is simple:**

1. Replace the `for` loop (lines 754-783) with the simplified version
2. Use `lspconfig.setup()` for ALL servers on ALL Neovim versions
3. Let lspconfig handle transformations automatically

**Benefits:**

- ✅ Simpler code (17 lines → 5 lines)
- ✅ Settings properly flattened
- ✅ Works on all Neovim versions
- ✅ Consistent behavior across all LSP servers
- ✅ No manual transformation needed

**Time to implement:** 2 minutes

**Time saved debugging:** Infinite

---

**End of Quick Guide**
