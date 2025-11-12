# LSP OmniSharp C# Fix Documentation

## 📋 TL;DR - Quick Solution

**Problem**: StyleCop analyzer warnings not showing in Neovim despite OmniSharp LSP being attached.

**Root Cause**: `lspconfig.omnisharp.setup()` was being called twice - once by mason-lspconfig handler with default config, then again explicitly with custom config. Only the first call takes effect.

**Solution**: Remove explicit `omnisharp.setup()` call and let mason-lspconfig handler configure it using the `servers.omnisharp` table.

**Critical Files**:
- `/home/uczen/.config/nvim/init.lua` - OmniSharp configuration
- `~/.cache/nvim/luac/` - Clear this when debugging config issues

**Verification**:
```bash
ps aux | grep omnisharp | grep -v grep
# Should show: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

---

## ✅ FINAL SOLUTION - StyleCop Warnings Now Working! (2025-11-12 Evening)

**Status**: **RESOLVED!** ✅✅✅ Configuration is now loading correctly and OmniSharp is receiving all settings.

**User Confirmation**: "yes motherfuck es lafue jez" - IT WORKS! 🎉

### The Root Cause

The problem was that **calling `lspconfig.omnisharp.setup()` multiple times doesn't work** - only the first call takes effect. When we tried to configure OmniSharp explicitly AFTER mason-lspconfig setup, it was too late - the default configuration had already been registered.

### The Solution

**Remove the explicit setup after mason-lspconfig and let the handler configure OmniSharp normally.**

**File**: `/home/uczen/.config/nvim/init.lua` (lines 1030-1044)

```lua
require('mason-lspconfig').setup {
  ensure_installed = {},
  automatic_installation = false,
  handlers = {
    -- Default handler for ALL servers (including omnisharp)
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)  -- This now correctly configures omnisharp!
    end,
  },
}
-- NO explicit omnisharp setup after this - let the handler do its job!
```

### Verification

**ps aux output confirms ALL settings are applied:**
```bash
dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend ✅ \
  -loglevel Information ✅ \
  -z --hostPID 19758 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 --languageserver \
  Sdk:IncludePrereleases=true \
  RoslynExtensionsOptions:EnableImportCompletion=true ✅ \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false ✅ \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true ✅✅✅ \
  FormattingOptions:OrganizeImports=true ✅ \
  FormattingOptions:EnableEditorConfigSupport=true ✅
```

**All critical settings are present:**
- ✅ `-s /mnt/c/.../Backend` (solution path - OmniSharp loads the whole solution!)
- ✅ `-loglevel Information` (detailed logging)
- ✅ `RoslynExtensionsOptions:EnableAnalyzersSupport=true` (enables StyleCop!)
- ✅ `RoslynExtensionsOptions:EnableImportCompletion=true`
- ✅ `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false` (analyzes all files!)
- ✅ `FormattingOptions:EnableEditorConfigSupport=true`
- ✅ `FormattingOptions:OrganizeImports=true`

### What Was the Problem?

**Timeline of the bug:**
1. Initially, we had a conflicting handler that overwrote the cmd (FIXED - deleted it)
2. Then we tried to configure OmniSharp explicitly AFTER mason-lspconfig setup
3. But `lspconfig.setup()` can only be called once per server
4. Mason-lspconfig had already called it with default config, so our explicit setup had no effect
5. **Solution**: Remove the explicit setup and fix the mason-lspconfig handler to pass the correct config

### Final Configuration Summary

**OmniSharp configuration** (init.lua lines 934-978):
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
  },
  on_init = function(client, initialization_result)
    vim.notify('🔄 OmniSharp lädt Projekte...', vim.log.levels.INFO)
  end,
  on_attach = function(client, bufnr)
    vim.notify('✅ OmniSharp erfolgreich geladen!', vim.log.levels.INFO)
  end,
  handlers = { ... },
}
```

**Mason-lspconfig setup** (init.lua lines 1030-1044):
```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

**Key insight**: The handler correctly uses `servers[server_name]` which includes our full omnisharp config!

### Next Steps

1. **Restart Neovim** (make sure only ONE instance is running)
2. **Open a C# file**: `nvim /mnt/c/.../UserController.cs`
3. **Wait for OmniSharp to load** (should see notifications)
4. **Check for StyleCop warnings** at lines 56-57, 78-79, 110-111, 152-153, 190-191, 241-243
5. **Test LSP features**:
   - `gd` - Go to definition
   - `grr` - Find references
   - `K` - Hover documentation
   - `:LspInfo` - Verify configuration

### If StyleCop Warnings Still Don't Appear

Even with `EnableAnalyzersSupport=true`, OmniSharp might need additional configuration:
1. Check if `.editorconfig` is present in the Backend directory
2. Ensure StyleCop.Analyzers package is referenced in .csproj
3. Check OmniSharp logs: `~/.local/state/nvim/lsp.log`
4. Restart OmniSharp: `:LspRestart`

### Key Lessons Learned

1. **`lspconfig.setup()` can only be called once per server** - Second calls are ignored
2. **Mason-lspconfig handlers run automatically** - Don't skip them and manually setup after
3. **The `servers` table is accessible in handlers** - Use `servers[server_name]` to get full config
4. **Lua bytecode cache can cause stale configs** - Always clear `~/.cache/nvim/luac/` when debugging
5. **`on_new_config` automatically flattens settings** - No need to manually convert to command-line args
6. **Use `ps aux | grep omnisharp`** to verify actual command line - Most reliable way to debug

### Quick Troubleshooting Checklist

If OmniSharp settings aren't loading:
- [ ] Clear Lua cache: `rm -rf ~/.cache/nvim/luac/`
- [ ] Kill OmniSharp: `pkill -f omnisharp`
- [ ] Check init.lua: `servers.omnisharp.cmd` is correctly defined
- [ ] Verify NO second `omnisharp.setup()` call exists
- [ ] Restart Neovim
- [ ] Check process: `ps aux | grep omnisharp` should show all settings
- [ ] Check `:LspInfo` for correct configuration

---

## CURRENT ISSUE: StyleCop Analyzer Warnings Not Showing (2025-11-12)

### Problem Statement
StyleCop analyzer warnings (SA1116, SA1117, etc.) are NOT appearing in Neovim despite:
- StyleCop.Analyzers 1.1.118 installed in project
- Warnings visible in `dotnet build` output
- OmniSharp LSP attached and functional (can jump to definitions)
- Settings configured in init.lua

### Symptoms
1. `:LspInfo` shows `RoslynExtensionsOptions = {}` (EMPTY!)
2. Command line shows `cmd: { "OmniSharp", "-z", ... }` instead of expected `{ "dotnet", "/path/to/OmniSharp.dll", "-s", "/path/to/solution", ... }`
3. Missing parameters:
   - ❌ No `-s /mnt/c/.../Backend` (solution path)
   - ❌ No `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
   - ❌ Settings not converted to command-line args

### Root Cause Analysis

#### Investigation Results (10 Parallel Agents - 2025-11-12)

**Agent Research Findings:**
1. **nvim-lspconfig behavior**: The `on_new_config` function (in `~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`) should:
   - Take base `cmd` array
   - Append hard-coded args: `-z`, `--hostPID`, `DotNet:enablePackageRestore=false`, `--encoding`, `--languageserver`
   - Flatten `settings` table into command-line args like `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

2. **Configuration conflict discovered**: TWO conflicting OmniSharp setups found:
   - **Location 1** (lines 934-979): `servers.omnisharp` table with full config
   - **Location 2** (lines 1036-1048): `mason-lspconfig` special handler that OVERWRITES the cmd

3. **The handler problem** (lines 1036-1048):
```lua
omnisharp = function()
  local server = servers.omnisharp or {}
  server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
  server.cmd = {  -- ⚠️ OVERWRITES servers.omnisharp.cmd!
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '-loglevel', 'Information',
    '-z',
    '--languageserver'
  }
  require('lspconfig').omnisharp.setup(server)
end,
```
This handler:
- Took config from `servers.omnisharp`
- Then REPLACED the `cmd` field entirely
- Removed the `-s` parameter and solution path
- Settings were present but cmd was wrong

### Attempted Fixes

#### Fix 1: Removed Conflicting Handler ✅
**File**: `/home/uczen/.config/nvim/init.lua`
**Lines deleted**: 1036-1048 (the special omnisharp handler)
**Reason**: Let the default handler use `servers.omnisharp` config unchanged

#### Fix 2: Changed cmd to Direct DLL Call ✅
**Before**:
```lua
cmd = {
  vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
  '-s', vim.fn.expand('/mnt/c/.../Backend'),
  '-loglevel', 'Information',
  '-z',
  '--languageserver'
}
```

**After**:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', vim.fn.expand('/mnt/c/.../Backend'),
  '-loglevel', 'Information',
}
```

**Reason**:
- Mason's `OmniSharp` is a wrapper script that calls `dotnet OmniSharp.dll`
- Direct DLL call matches nvim-lspconfig documentation
- Removed duplicate `-z` and `--languageserver` (lspconfig adds these automatically)

#### Fix 3: Settings Configuration ✅
Settings remain in place:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    OrganizeImports = true,
  },
},
```

### SOLUTION FOUND ✅ (2025-11-12 Evening)

**Root cause identified**: Mason-lspconfig default handler wasn't using the `servers.omnisharp` configuration!

**The problem**:
1. **Lua bytecode cache** - Neovim was loading cached `init.luac` instead of updated `init.lua` ✅ FIXED
2. **Config not being picked up** - Even after clearing cache, mason-lspconfig's default handler wasn't using `servers.omnisharp` config
3. **ps aux verification** showed OmniSharp running without:
   - ❌ `-s /mnt/c/.../Backend` (solution path)
   - ❌ Settings flattened to command-line args
   - ❌ `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

**The real fix** (init.lua lines 1030-1058):
```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      -- Skip omnisharp - it will be configured explicitly after this setup
      if server_name == 'omnisharp' then
        return
      end
      -- ... default handler for other servers
    end,
  },
}

-- EXPLICIT OMNISHARP SETUP (after mason-lspconfig)
if servers.omnisharp then
  local omnisharp_config = vim.deepcopy(servers.omnisharp)
  omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
  require('lspconfig').omnisharp.setup(omnisharp_config)
  vim.notify('🔧 OmniSharp explicitly configured with custom cmd and settings', vim.log.levels.INFO)
end
```

**Why this works**:
- Mason-lspconfig default handler now **skips** omnisharp (returns early)
- OmniSharp is configured **explicitly** AFTER mason-lspconfig setup
- Direct call to `lspconfig.omnisharp.setup()` with our full config
- Ensures `cmd` and `settings` are used correctly
- The `on_new_config` function will then flatten settings into command-line args

**Cleanup steps done**:
```bash
# 1. Clear Lua bytecode cache
rm -rf ~/.cache/nvim/luac/

# 2. Kill all OmniSharp processes
pkill -f omnisharp

# 3. Clear swap files
rm -f ~/.local/state/nvim/swap/*.swp
```

**Verification test** (`/tmp/test_omnisharp_config2.lua`):
Confirmed that `on_new_config` will correctly flatten settings:
- ✅ `RoslynExtensionsOptions:EnableAnalyzersSupport=true` (position [16])
- ✅ `RoslynExtensionsOptions:EnableImportCompletion=true`
- ✅ `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false`
- ✅ `FormattingOptions:OrganizeImports=true`
- ✅ `FormattingOptions:EnableEditorConfigSupport=true`

### What Was Fixed

1. ✅ **Deleted conflicting handler** (old lines 1036-1048)
2. ✅ **Changed to direct DLL call** (`dotnet` + DLL path instead of wrapper)
3. ✅ **Cleared Lua bytecode cache** (was preventing config reload)
4. ✅ **Added explicit omnisharp setup** (mason-lspconfig handler now skips it)
5. ✅ **Killed all OmniSharp processes**
6. ✅ **Cleared swap files**

### Next Step: Test the Fix

**User must restart Neovim and verify**:
1. Exit Neovim: `:qa!`
2. Start Neovim and open a C# file:
   ```
   nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs
   ```
3. You should see notification: `🔧 OmniSharp explicitly configured with custom cmd and settings`
4. Run `:LspInfo` and verify:
   - cmd starts with `{ "dotnet", "/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", ... }`
   - RoslynExtensionsOptions shows `{ EnableAnalyzersSupport = true, ... }`
5. Run `ps aux | grep omnisharp` and verify command line includes `-s /mnt/c/.../Backend` and `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
6. Check if StyleCop warnings appear at lines 56-57, 78-79, 110-111, 152-153, 190-191, 241-243

---

### ⚠️ CRITICAL FINDING - Configuration Still Not Loading (2025-11-12 Evening Session 2)

**Status**: Despite all fixes applied above, **THE PROBLEM PERSISTS**.

#### Evidence from User Verification

User restarted Neovim and ran `:LspInfo`. Results show:

```
cmd: { "OmniSharp", "-z", "--hostPID", "12648", "DotNet:enablePackageRestore=false", "--encoding", "utf-8", "--languageserver" }
settings: {
  RoslynExtensionsOptions = {}   ← STILL EMPTY!
}
```

**Running process shows:**
```bash
dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -z --hostPID 12648 DotNet:enablePackageRestore=false --encoding utf-8 --languageserver
```

**Missing from both `:LspInfo` and running process:**
- ❌ `-s /mnt/c/.../Backend` (solution path)
- ❌ `-loglevel Information`
- ❌ `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
- ❌ `RoslynExtensionsOptions:EnableImportCompletion=true`
- ❌ `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false`
- ❌ `FormattingOptions:EnableEditorConfigSupport=true`
- ❌ `FormattingOptions:OrganizeImports=true`

#### What This Tells Us

**The cmd is completely wrong:**
- Shows `"OmniSharp"` (wrapper name) instead of `"dotnet"` + full DLL path
- This means the `servers.omnisharp.cmd` from init.lua is **NOT being used at all**

**The settings are empty:**
- `RoslynExtensionsOptions = {}` means settings are not being passed
- Even though `on_new_config` should flatten them, there's nothing to flatten

#### Deep Analysis Performed

**Files verified:**
1. ✅ `/home/uczen/.config/nvim/init.lua` (lines 934-952) - Configuration is correct:
   ```lua
   omnisharp = {
     cmd = {
       'dotnet',
       vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
       '-s', vim.fn.expand('/mnt/c/.../Backend'),
       '-loglevel', 'Information',
     },
     settings = {
       RoslynExtensionsOptions = {
         EnableAnalyzersSupport = true,
         EnableImportCompletion = true,
         AnalyzeOpenDocumentsOnly = false,
       },
       FormattingOptions = {
         EnableEditorConfigSupport = true,
         OrganizeImports = true,
       },
     },
   }
   ```

2. ✅ Special omnisharp handler is **not present** in init.lua (was deleted in previous fix)

3. ✅ Explicit omnisharp setup exists (lines 1030-1058):
   ```lua
   -- Mason-lspconfig setup with skip for omnisharp
   require('mason-lspconfig').setup {
     handlers = {
       function(server_name)
         if server_name == 'omnisharp' then
           return  -- Skip omnisharp
         end
         -- ... handle other servers
       end,
     },
   }

   -- EXPLICIT OMNISHARP SETUP
   if servers.omnisharp then
     local omnisharp_config = vim.deepcopy(servers.omnisharp)
     omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
     require('lspconfig').omnisharp.setup(omnisharp_config)
     vim.notify('🔧 OmniSharp explicitly configured with custom cmd and settings', vim.log.levels.INFO)
   end
   ```

4. ✅ Lua bytecode cache cleared (timestamps from Nov 12 19:25)

5. ✅ OmniSharp.dll exists at `/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll`

6. ✅ LSP logs show no configuration errors (only standard warnings)

#### Current Hypothesis: Configuration Loading Gap

**Possible root causes:**

1. **Timing Issue**: Perhaps the explicit setup runs, but then something **overrides** it later:
   - Maybe Mason automatically sets a default cmd after our setup
   - Maybe lspconfig's default_config takes precedence over user config
   - Maybe there's a lazy-loading race condition

2. **Path Evaluation Issue**: `vim.fn.stdpath('data')` might not evaluate correctly at setup time:
   - Expected: `/home/uczen/.local/share/nvim`
   - If it evaluates to empty, cmd would break

3. **Table Reference Issue**: The `servers.omnisharp` table might not be in scope when the explicit setup runs:
   - Maybe `servers` is defined in a different scope
   - Maybe `vim.deepcopy(servers.omnisharp)` returns nil

4. **Silent Failure**: The explicit setup might be failing silently:
   - No notification visible (user should have seen "🔧 OmniSharp explicitly configured...")
   - This suggests the `if servers.omnisharp then` block might not execute at all

#### Next Investigation Steps

**Verification commands to run in Neovim:**

```vim
" 1. Check if servers.omnisharp exists in scope
:lua print(vim.inspect(servers))

" 2. Check what stdpath returns
:lua print(vim.fn.stdpath('data'))

" 3. Check the actual lspconfig omnisharp config
:lua print(vim.inspect(require('lspconfig').omnisharp))

" 4. Check if notification was shown (in message history)
:messages

" 5. Force manual setup to test
:lua local cfg = vim.deepcopy(servers.omnisharp); cfg.capabilities = vim.lsp.protocol.make_client_capabilities(); require('lspconfig').omnisharp.setup(cfg)

" 6. Check Mason registry default cmd
:lua print(vim.inspect(require('mason-registry').get_package('omnisharp'):get_install_path()))
```

**Debugging approach:**

Add debug prints to init.lua explicit setup section:
```lua
-- EXPLICIT OMNISHARP SETUP (with debugging)
vim.notify('[DEBUG] Checking if servers.omnisharp exists...', vim.log.levels.WARN)
if servers.omnisharp then
  vim.notify('[DEBUG] servers.omnisharp found! Setting up...', vim.log.levels.WARN)
  vim.notify('[DEBUG] cmd = ' .. vim.inspect(servers.omnisharp.cmd), vim.log.levels.WARN)
  local omnisharp_config = vim.deepcopy(servers.omnisharp)
  omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
  require('lspconfig').omnisharp.setup(omnisharp_config)
  vim.notify('🔧 OmniSharp explicitly configured with custom cmd and settings', vim.log.levels.INFO)
else
  vim.notify('[DEBUG] servers.omnisharp NOT FOUND!', vim.log.levels.ERROR)
end
```

#### Most Likely Root Cause

Based on the evidence that **no notification was shown** and cmd is completely default, the most likely issue is:

**The `servers.omnisharp` variable is out of scope when the explicit setup runs.**

The `servers` table is defined earlier in init.lua (around line 880-952), but when the explicit setup code runs (lines 1030-1058), the `servers` variable might not be accessible because:
- It's in a different scope
- It's local to a different block
- It was already garbage collected

**This would explain:**
- Why `if servers.omnisharp then` silently fails (servers is nil)
- Why the notification never shows
- Why OmniSharp uses Mason's default cmd instead

#### Recommended Fix

Move the explicit setup code to **immediately after** the `servers` table definition, or ensure `servers` is in global scope:

```lua
-- Option 1: Move explicit setup right after servers definition
local servers = {
  -- ... all server definitions including omnisharp ...
}

-- IMMEDIATELY setup OmniSharp here (servers is in scope)
if servers.omnisharp then
  local omnisharp_config = vim.deepcopy(servers.omnisharp)
  omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
  require('lspconfig').omnisharp.setup(omnisharp_config)
  vim.notify('🔧 OmniSharp explicitly configured', vim.log.levels.INFO)
end

-- Later: mason-lspconfig setup (skipping omnisharp since we already set it up)
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Already configured above
      end
      -- ... handle other servers
    end,
  },
}
```

---

### Agent Research Documentation Created

10 agents researched the problem in parallel and created comprehensive documentation:
- `README_OMNISHARP_RESEARCH.md` - Navigation guide
- `RESEARCH_FINDINGS_SUMMARY.txt` - Detailed findings
- `OMNISHARP_CMD_PARAMETER_ANALYSIS.md` - Technical deep-dive
- `OMNISHARP_CMD_QUICK_REFERENCE.md` - Quick reference

Location: `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/`

### Known Good Configuration (from Agent Research)

According to nvim-lspconfig documentation:
```lua
require('lspconfig').omnisharp.setup {
  cmd = { "dotnet", "/path/to/omnisharp/OmniSharp.dll" },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = nil,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = nil,  -- nil means use OmniSharp default (true)
      EnableImportCompletion = nil,
      AnalyzeOpenDocumentsOnly = nil,
    },
  },
}
```

**Critical insight from lspconfig source code**:
- The `on_new_config` function at line 46-78 of `omnisharp.lua` is responsible for:
  1. Copying base cmd
  2. Appending hard-coded args
  3. Flattening settings into command-line args
  4. This SHOULD happen automatically, but isn't working

### Hypothesis: Why Config Not Loading

Possible causes:
1. **Mason-lspconfig automatic setup** may be running BEFORE our manual setup
2. **Binary path resolution** - `OmniSharp` wrapper script might be resolved by Mason differently
3. **Config merge order** - Maybe default_config overrides our config instead of vice versa
4. **Lazy-loading issue** - Config defined but not applied when LSP starts

### Verification Commands

```bash
# Check current config in running Neovim
:lua print(vim.inspect(require('lspconfig').omnisharp.cmd))

# Check Mason registry
:lua print(vim.inspect(require('mason-registry').get_package('omnisharp'):get_install_path()))

# Force LSP restart
:LspRestart

# Clear plugin cache
:Lazy clean
:Lazy sync

# Check if settings are being passed
tail -100 ~/.local/state/nvim/lsp.log | grep -i "RoslynExtensions\|EnableAnalyzers"
```

---

## Problem
OmniSharp LSP was not attaching to C# files in Neovim. Error message: "No LSP client attached"

## Root Causes
1. OmniSharp command path not properly configured
2. Multiple OmniSharp instances running simultaneously
3. Swap file conflicts preventing proper file access
4. OmniSharp not finding the solution file properly

## Solution Steps

### 1. Kill All Running OmniSharp Processes
```bash
pkill -f omnisharp
# Verify no processes running
ps aux | grep omnisharp | grep -v grep
```

### 2. Clean Swap Files
```bash
rm -f ~/.local/state/nvim/swap/*.swp
```

### 3. Fix OmniSharp Configuration in init.lua
Updated the OmniSharp configuration to use the correct Mason installation path:

```lua
omnisharp = {
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
  enable_import_completion = true,
  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.INFO)
    end,
  },
},
```

### 4. Verify Installation
```bash
# Check OmniSharp is installed via Mason
ls ~/.local/share/nvim/mason/bin/ | grep -i omni

# Test OmniSharp can start
~/.local/share/nvim/mason/bin/OmniSharp --version
```

### 5. Restart Neovim
1. Exit Neovim: `:qa!`
2. Open a C# file in your project
3. Check LSP status with `:LspInfo`
4. OmniSharp should now attach automatically

## Verification
- Run `:LspInfo` - should show OmniSharp as attached
- Test `gd` (Go to Definition) on a C# symbol
- Test `grr` (Find References) on a C# symbol
- Test `K` (Hover) for documentation

## Additional Notes
- OmniSharp automatically finds the solution file in parent directories
- No need to specify the solution file path in the command
- The LSP will load all projects in the solution (may take a moment for large solutions)

## WSL2 + Windows Cross-Filesystem Issue

### Problem
When working with projects on Windows filesystem (`/mnt/c/...`) in WSL2, if you compile/restore NuGet packages in Windows (PowerShell), the LSP in WSL will not work properly. This is because NuGet packages are cached differently between Windows and WSL.

### Solution
After compiling/restoring in Windows, run this command in WSL before opening Neovim:

```bash
dotnet restore --force-evaluate --no-cache
```

**What this does:**
- `--force-evaluate`: Forces re-evaluation of all dependencies
- `--no-cache`: Ignores the NuGet cache and downloads fresh packages

**When to use:**
- After building/restoring in Windows PowerShell
- When LSP suddenly stops working after switching between Windows and WSL
- After system reboot if you compiled in Windows before

**Alternative (quick alias):**
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
alias fixlsp='dotnet restore --force-evaluate --no-cache && pkill -f omnisharp'
```

Then just run `fixlsp` in your project directory.

---

# Git Workflow with Neogit and Diffview

## Overview
Neovim is configured with **Neogit** (Magit-like Git UI) and **Diffview** (powerful diff viewer) for a complete Git workflow inside Neovim.

## Installed Plugins
- **Neogit** (`NeogitOrg/neogit`) - Interactive Git UI
- **Diffview** (`sindrets/diffview.nvim`) - Advanced diff and merge tool
- **Gitsigns** (`lewis6991/gitsigns.nvim`) - Git decorations in gutter

## Key Bindings

### Neogit Commands
| Keybinding | Command | Description |
|------------|---------|-------------|
| `<leader>gg` | `:Neogit` | Open Neogit status (main Git UI) |
| `<leader>gc` | `:Neogit commit` | Open commit interface |
| `<leader>gp` | `:Neogit push` | Push changes |
| `<leader>gl` | `:Neogit pull` | Pull changes |

### Diffview Commands
| Keybinding | Command | Description |
|------------|---------|-------------|
| `<leader>gd` | `:DiffviewOpen` | Open diff view (all changes) |
| `<leader>gh` | `:DiffviewFileHistory %` | Show current file's Git history |
| `<leader>gD` | `:DiffviewClose` | Close diff view |

## Neogit Usage

### Opening Neogit
Press `<leader>gg` (Space + g + g) to open the Neogit status buffer.

### Neogit Keybindings
When in Neogit buffer:

| Key | Action |
|-----|--------|
| `Tab` | Toggle section (fold/unfold) |
| `s` | Stage/unstage file or hunk |
| `S` | Stage all |
| `u` | Unstage |
| `U` | Unstage all |
| `c` | Commit (opens commit buffer) |
| `p` | Push |
| `P` | Pull |
| `F` | Fetch |
| `b` | Branch operations (checkout, create, delete) |
| `l` | Open log view |
| `d` | Open diff for file under cursor |
| `=` | Toggle inline diff |
| `?` | Show help (all keybindings) |
| `q` | Close Neogit |

### Committing Changes
1. Press `<leader>gg` to open Neogit
2. Stage files with `s` (or stage all with `S`)
3. Press `c` then `c` to commit
4. Write commit message
5. Save and close (`:wq` or `ZZ`)
6. Press `p` then `p` to push

### Branch Operations
1. Press `<leader>gg` to open Neogit
2. Press `b` to open branch menu
3. Choose action:
   - `b` - Checkout branch (uses Telescope)
   - `c` - Create new branch
   - `r` - Rename branch
   - `d` - Delete branch

## Diffview Usage

### Compare Branches
```vim
:DiffviewOpen main..feature-branch
```
Shows all differences between `main` and `feature-branch`.

### Compare with HEAD
```vim
:DiffviewOpen HEAD~2
```
Shows changes in last 2 commits.

### View Uncommitted Changes
```vim
:DiffviewOpen
```
or `<leader>gd` - Shows all uncommitted changes.

### File History
```vim
:DiffviewFileHistory %
```
or `<leader>gh` - Shows Git history for current file.

### Diffview Navigation
When in Diffview:

| Key | Action |
|-----|--------|
| `]c` | Next conflict/change |
| `[c` | Previous conflict/change |
| `<Tab>` | Switch between diff panels |
| `gf` | Open file in new tab |
| `<leader>gD` | Close diffview |

## Typical Git Workflow

### Making Changes and Committing
1. Make your code changes in Neovim
2. Press `<leader>gg` to open Neogit
3. Review changes (press `Tab` to expand sections)
4. Stage files: `s` on individual files or `S` for all
5. Press `c` then `c` to commit
6. Write commit message, save (`:wq`)
7. Press `p` then `p` to push

### Reviewing Changes Before Commit
1. Press `<leader>gd` to see all changes in Diffview
2. Navigate through files
3. Press `<leader>gD` to close
4. Commit with `<leader>gc`

### Checking Branch Differences
```vim
:DiffviewOpen main..your-branch
```
Review all changes before merging.

### Resolving Merge Conflicts
1. After merge conflict occurs
2. Press `<leader>gd` to open Diffview
3. Diffview shows 3-way merge view
4. Edit conflicts in files
5. Save and stage resolved files in Neogit
6. Commit merge

## Advanced Diffview Commands

### Compare Specific Commits
```vim
:DiffviewOpen abc123..def456
```

### File History with Range
```vim
:DiffviewFileHistory --range=main..HEAD
```

### Close All Diffviews
```vim
:DiffviewClose
```
or `<leader>gD`

## Configuration Details

### Neogit Configuration
```lua
{
  integrations = {
    diffview = true,  -- Use Diffview for diffs
    telescope = true, -- Use Telescope for branch selection
  },
  use_telescope = true,
}
```

### Diffview Configuration
```lua
{
  enhanced_diff_hl = true, -- Better diff highlighting
  view = {
    default = {
      layout = 'diff2_horizontal',  -- Side-by-side diff
    },
    merge_tool = {
      layout = 'diff3_horizontal',  -- 3-way merge view
    },
  },
}
```

## Tips and Tricks

### Quick Status Check
- Just press `<leader>gg` - faster than `:!git status`

### Interactive Staging
- In Neogit, you can stage individual hunks (not just files)
- Navigate to file, press `Tab` to expand, then `s` on specific hunks

### History Navigation
- `<leader>gh` on any file shows its complete Git history
- Use `]c` and `[c` to jump between changes in diffs

### Integration with Telescope
- When selecting branches in Neogit, Telescope fuzzy finder is used
- Fast branch switching with fuzzy search

## Troubleshooting

### Neogit Not Opening
1. Ensure you're in a Git repository
2. Run `:Lazy` and check if Neogit is installed
3. Run `:Lazy sync` to update plugins

### Diffview Shows No Changes
- Make sure you have uncommitted changes or specify a valid comparison
- Try `:DiffviewOpen HEAD~1` to see last commit

### Performance Issues with Large Repos
- Diffview may be slow on very large diffs
- Consider using `:DiffviewFileHistory` for single files instead of full project diffs

## Related Commands

### Gitsigns (Inline Git Decorations)
Gitsigns shows `+`, `~`, `_` symbols in the gutter for added/changed/deleted lines.

- Signs appear automatically in the sign column
- Shows real-time Git diff status while editing

## Summary

You now have a complete Git workflow in Neovim:
- **Neogit** (`<leader>gg`) - For staging, committing, pushing, branching
- **Diffview** (`<leader>gd`) - For viewing diffs and file history
- **Gitsigns** - For inline change indicators

This setup provides a Git experience comparable to Magit (Emacs) or GitLens (VS Code), entirely within Neovim!

## Neogit - Detaillierte Workflows

### Grundlegende Navigation

**Neogit öffnen:**
```vim
<leader>gg    → Öffnet Neogit Status
```

**Im Neogit Buffer:**
| Taste | Aktion |
|-------|--------|
| `Tab` | Sektion auf/zuklappen (z.B. Unstaged changes) |
| `j/k` | Hoch/Runter navigieren |
| `?` | Hilfe anzeigen (alle Keybindings) |
| `q` | Neogit schließen |

### Staging und Unstaging

**Dateien stagen:**
- `s` - Stage Datei unter Cursor
- `S` - Stage alle Dateien
- `u` - Unstage Datei
- `U` - Unstage alle

**Einzelne Hunks stagen:**
1. `Tab` auf Datei → Zeigt einzelne Änderungsblöcke (Hunks)
2. Cursor auf gewünschten Hunk
3. `s` → Staged nur diesen Hunk (nicht ganze Datei!)
4. Andere Hunks bleiben unstaged

**Beispiel - Selective Staging:**
```
Unstaged changes (1)
▾ modified   UserController.cs          <- Tab drücken
    @@ -1,5 +1,4 @@                    <- Hunk 1 (imports)
    -using System.Threading.Tasks;
    +// imports removed

    @@ -304,4 +302,4 @@                 <- Hunk 2 (newline)
    -}
    +}
    // newline added
```
Cursor auf Hunk 1 → `s` → Nur Import-Änderungen werden gestaged!

### Commit Message Wiederverwendung

**Im Commit Buffer (nach `c c`):**
- `Alt+p` oder `<M-p>` - Vorherige Commit-Message laden
- `Alt+n` oder `<M-n>` - Nächste Commit-Message
- `Alt+r` oder `<M-r>` - Message zurücksetzen

**Workflow:**
1. `c c` → Commit Buffer öffnet
2. `Alt+p` → Lädt letzte Commit-Message
3. Message anpassen
4. `:wq` → Speichern

### Änderungen verwerfen (Discard)

**Ganze Datei verwerfen:**
1. Cursor auf Datei (in Unstaged changes)
2. `x` → Discard-Menü
3. `y` → Bestätigen
4. Änderungen werden verworfen!

**Einzelne Hunks verwerfen:**
1. `Tab` auf Datei → Hunks anzeigen
2. Cursor auf Hunk
3. `x` → Nur diesen Hunk verwerfen

### Branch-Operationen

**Branch-Menü öffnen:**
- `b` im Neogit Buffer → Branch-Menü

**Optionen:**
- `b` - Branch wechseln (mit Telescope fuzzy finder)
- `c` - Neuen Branch erstellen
- `r` - Branch umbenennen
- `d` - Branch löschen

### Push und Pull

**Im Neogit Buffer:**
- `p` dann `p` - Push to upstream
- `P` dann `p` - Pull from upstream
- `F` dann `a` - Fetch all

**Oder mit Keybindings:**
- `<leader>gp` - Neogit Push (direkt)
- `<leader>gl` - Neogit Pull (direkt)

### Diff anschauen

**Im Neogit Buffer:**
- `d` - Diff der Datei unter Cursor
- `=` - Inline diff toggle
- `<leader>gd` - Diffview für alle Änderungen öffnen

### Untracked Files

**Dateien zu Git hinzufügen:**
1. Cursor auf Datei in "Untracked files"
2. `s` → Staged (wird committed)

**Dateien ignorieren:**
- Füge zu `.gitignore` hinzu
- Oder zu `.git/info/exclude` (lokal, nicht committed)

### Log und History

**Im Neogit Buffer:**
- `l` - Log view öffnen
- Zeigt Commit-History
- `Enter` auf Commit → Zeigt Details

## Diffview - Navigation und Workflows

### Branch-Diff mit origin/develop

**Neues Feature - Branch vergleichen:**
```vim
<leader>gb    → Zeigt alle Unterschiede zwischen aktuellem Branch und origin/develop
```

**Was du siehst:**
- Links: File Panel mit allen geänderten Dateien
- Rechts: Side-by-side Diff der ausgewählten Datei

### Navigation in Diffview

**Zwischen Changes navigieren (innerhalb Datei):**
- `]c` - Nächste Change
- `[c` - Vorherige Change

**Zwischen Dateien wechseln:**
- `Tab` - Nächste Datei
- `Shift+Tab` - Vorherige Datei
- `j/k` im File Panel (links) - Durch Dateien navigieren
- `Enter` - Datei im Diff öffnen

**Weitere Befehle:**
- `gf` - Datei in neuem Tab öffnen
- `g?` - Hilfe anzeigen (alle Keybindings)
- `<leader>gD` - Diffview schließen

### Verschiedene Diff-Views

```vim
:DiffviewOpen                              → Uncommitted changes
:DiffviewOpen HEAD~2                       → Letzte 2 Commits
:DiffviewOpen origin/develop...HEAD        → Branch diff (<leader>gb)
:DiffviewOpen main..feature-branch         → Zwischen zwei Branches
:DiffviewFileHistory %                     → History der aktuellen Datei (<leader>gh)
:DiffviewClose                             → Diffview schließen (<leader>gD)
```

### Merge Conflicts

**Bei Merge-Konflikten:**
1. `<leader>gd` → Diffview öffnet automatisch 3-Way Merge View
2. Links: OURS (deine Version)
3. Mitte: BASE (gemeinsamer Vorfahr)
4. Rechts: THEIRS (ihre Version)
5. Datei bearbeiten, Konflikt-Marker entfernen (`<<<<<<<`, `=======`, `>>>>>>>`)
6. `:w` → Speichern
7. Zurück zu Neogit: `<leader>gg`
8. `s` auf Datei → Als gelöst markieren
9. `c c` → Merge-Commit

## Auto-Save

**Automatisches Speichern aktiviert:**
```lua
vim.o.autowrite = true       -- Speichert beim Buffer-Wechsel
vim.o.autowriteall = true    -- Speichert in mehr Situationen
```

**Wann wird gespeichert:**
- Beim Wechsel zu anderem Buffer
- Beim Verlassen von Neovim
- Beim Ausführen externer Befehle
- Bei Git-Operationen in Neogit

**Vorteil:** Änderungen sind immer gespeichert, bevor du sie in Git siehst!

## Diagnostics und Code Navigation

### Zu Warnungen navigieren

**Navigation:**
- `]d` - Nächste Diagnostic/Warning
- `[d` - Vorherige Diagnostic/Warning

**Details und Fixes:**
- `K` - Hover über Warnung (zeigt Details)
- `<leader>ca` - Code Actions (Quick Fix Optionen)
- `<leader>w` - Telescope Diagnostics (alle Warnungen im Projekt)

**Workflow - Warnung fixen:**
```
]d              → Zur nächsten Warnung
K               → Details anzeigen
<leader>ca      → Fix-Menü öffnet:
                  1. Remove unused import
                  2. Add missing await
                  etc.
Enter           → Fix auswählen
:w              → Speichern (mit format-on-save)
```

## Praktische Workflows

### Kompletter Feature-Branch Workflow

```
1. Feature entwickeln
2. <leader>gb           → Branch diff vs develop ansehen
3. <leader>gg           → Neogit öffnen
4. Tab auf Dateien      → Hunks anzeigen
5. s auf Hunks          → Selective staging
6. c c                  → Commit
7. Alt+p                → Vorherige Message laden
8. Message anpassen     → :wq
9. p p                  → Push
10. q                   → Neogit schließen
```

### Schneller Commit-Fix Workflow

```
1. Code ändern
2. <leader>gg           → Neogit
3. S                    → Stage all
4. c c                  → Commit
5. Message schreiben    → :wq
6. p p                  → Push
```

### Review vor Merge

```
1. <leader>gb           → Branch diff vs develop
2. ]c / [c              → Durch Changes navigieren
3. Tab                  → Durch Dateien wechseln
4. <leader>gD           → Schließen
5. Wenn OK: Merge       → In Neogit oder Terminal
```

## Tipps und Tricks

### Selective Staging für Clean Commits

Statt alles auf einmal zu committen:
1. Öffne Neogit
2. Tab auf Dateien → Zeigt Hunks
3. Stage nur zusammengehörige Hunks
4. Commit mit beschreibender Message
5. Wiederhole für andere Änderungen

**Vorteil:** Saubere, atomare Commits!

### Branch Diff vor Pull Request

Vor PR erstellen:
```
<leader>gb              → Siehst alle Änderungen vs develop
```
Reviewe alles, dann erst PR erstellen!

### Commit Message History nutzen

Bei ähnlichen Commits:
```
c c                     → Commit Buffer
Alt+p                   → Vorherige Message
                        → Ticket-Nummer bleibt gleich, nur Text ändern
```

### Quick Status Check

Schnell checken was geändert ist:
```
<leader>gg              → Schneller als git status im Terminal
Tab                     → Dateien aufklappen
q                       → Schließen
```

---

# Development Workflow - Backend & Frontend

## Overview
Unified keybinding schema for Backend (C#/.NET) and Frontend (Angular/TypeScript) development with consistent prefixes.

## Keybinding Schema

### Backend Commands (<leader>b...)

| Keybinding  | Command                                    | Description                        |
|-------------|--------------------------------------------|-------------------------------------|
| `<leader>br` | `dotnet run`                              | Backend Run (WebHost on localhost:5443) |
| `<leader>bs` | `dotnet restore --force-evaluate --no-cache` | Backend reStore (WSL2 NuGet fix) |
| `<leader>btu` | `dotnet test --no-restore --filter "..."` | Backend Test Unit (excludes DB/Storage/Docker) |
| `<leader>bti` | `dotnet test --no-restore`                | Backend Test Integration (all tests) |

**Backend Test Filters:**
- Unit tests exclude: `Category!=Database & Category!=Storage & Category!=Docker`
- Integration tests: all tests (no filter)
- Always use `--no-restore` to avoid NuGet timeout issues

### Frontend Commands (<leader>f...)

| Keybinding  | Command                    | Description                          |
|-------------|----------------------------|--------------------------------------|
| `<leader>fr` | `npm run start`           | Frontend Run (Angular on https://localhost:8443) |
| `<leader>fc` | `rm -rf node_modules && npm install` | Frontend Clean + reinstall |
| `<leader>ftu` | `npm test`               | Frontend Test Unit (Jest) |

**Important: PowerShell Requirement**

Frontend commands use PowerShell (not bash) because npm packages are behind VPN not accessible from WSL2 Linux:

```lua
cmd = 'powershell.exe -Command "cd C:\\Users\\Administrator\\...; npm start"'
```

When to use PowerShell:
- All Frontend operations (npm install, npm start, npm test)
- Reason: VPN-protected package registry not reachable from WSL2

### Test Commands (<leader>t...) - Neotest

| Keybinding  | Action                                    |
|-------------|-------------------------------------------|
| `<leader>tn` | [T]est [N]earest - Run test under cursor |
| `<leader>tf` | [T]est [F]ile - Run all tests in file    |
| `<leader>tl` | [T]est [L]ast - Repeat last test         |
| `<leader>ts` | [T]est [S]ummary - Open test sidebar     |
| `<leader>to` | [T]est [O]utput - Show test output       |
| `<leader>tp` | [T]est [P]anel - Toggle output panel     |
| `<leader>tx` | [T]est Stop - Stop running tests         |
| `<leader>w`  | [W]arnings/Diagnostics - Telescope list  |

## Neotest - Modern Test Runner

### Overview
Neotest provides inline test execution with visual feedback directly in your code.

### Installation
Installed adapters:
- **neotest-dotnet** - C# / .NET (xUnit, NUnit, MSTest)
- **neotest-jest** - TypeScript / Jest / Angular

### Visual Indicators

Tests show status icons in the sign column (gutter):
- ✅ - Test passed
- ❌ - Test failed
- ⏳ - Test running
- ⊘ - Test skipped

### Usage

**Running Tests:**
1. Open a test file (e.g., `UserServiceTests.cs` or `*.spec.ts`)
2. Place cursor on a test method
3. Press `<leader>tn` to run that specific test
4. See ✅ or ❌ icon appear in gutter

**Viewing Test Output:**
- `<leader>to` - Opens floating window with test output
- `<leader>tp` - Opens persistent panel at bottom
- `<leader>ts` - Opens test sidebar with tree view

**Test Sidebar (Summary):**
- Navigate: `j/k`
- Run test: `r` on test under cursor
- Jump to test: `Enter`
- Show output: `o`
- Close: `q` or `<leader>ts`

**Quick Iteration:**
1. Write code
2. `<leader>tn` - Run test
3. Test fails ❌
4. Fix code
5. `<leader>tl` - Run same test again (no navigation needed)
6. Test passes ✅

### Configuration

```lua
output = {
  enabled = true,
  open_on_run = 'short',  -- Auto-open only for fast tests (<1s)
}
```

To see output manually: Use `<leader>to`, `<leader>tp`, or `<leader>ts`

### Known Issues

**neotest-dotnet Sidebar Navigation:**
- Sidebar may not jump to test on `Enter` (known adapter issue)
- **Workaround:** Use `<leader>tn` directly in test files instead of sidebar
- **Alternative:** Use Toggleterm commands (`<leader>btu`/`<leader>bti`) for reliable test runs

## Dual Testing Approach

You have **two complementary ways** to run tests:

### 1. Neotest (Inline, Single Tests)
**Best for:**
- Running individual tests during development
- Quick feedback with visual icons
- Iterating on specific test cases

**Commands:** `<leader>tn`, `<leader>tf`, `<leader>tl`

### 2. Toggleterm (Full Test Runs)
**Best for:**
- Running entire test suites
- Full output visibility
- Guaranteed reliability (no adapter issues)

**Backend:** `<leader>btu` (unit), `<leader>bti` (integration)
**Frontend:** `<leader>ftu`

**Recommendation:** Use both! Neotest for focused work, Toggleterm for comprehensive runs.

## Code Formatting and Diagnostics

### Format on Save

**Enabled for all languages:**
- C# → OmniSharp LSP (EditorConfig + StyleCop rules)
- TypeScript/JavaScript → Prettier
- HTML/JSON/SCSS → Prettier

When you save a file (`:w`), it's automatically formatted according to project rules.

### Manual Formatting

- `<leader>f` - Format current file immediately (without saving)
- `:ConformInfo` - Show which formatters are active

### Diagnostics (Warnings/Errors)

**Inline Diagnostics:**
- Red/yellow underlines appear automatically
- Provided by LSP (OmniSharp for C#, TypeScript LSP for TS)

**Navigation:**
- `]d` - Next diagnostic
- `[d` - Previous diagnostic
- `K` - Hover to see details
- `<leader>ca` - Code Actions (Quick Fix)

**List View:**
- `<leader>w` - Telescope diagnostics (all warnings/errors in project)
- Shows file, line number, and preview
- Press `Enter` to jump to problem

**Typical Workflow:**
1. See red underline in code
2. Press `K` to see what's wrong
3. Press `<leader>ca` to see available fixes
4. Select fix → automatically applied
5. Save `:w` → formatted and fixed

### LSP Commands

| Keybinding   | Action                      |
|--------------|-----------------------------|
| `gd`         | Go to Definition            |
| `grr`        | Find References             |
| `gI`         | Go to Implementation        |
| `<leader>rn` | Rename Symbol               |
| `<leader>ca` | Code Actions (Quick Fix)    |
| `K`          | Hover Documentation         |
| `<leader>w`  | All Warnings/Diagnostics    |

## Style and Formatting Rules

### Frontend (Angular/TypeScript)

**Prettier (`.prettierrc`):**
- Single quotes (`'`)
- 120 character line width
- Strict HTML whitespace

**ESLint (`.eslintrc.json`):**
- Nx monorepo rules
- Module boundary enforcement
- Angular-specific rules

**Manual Format:**
```bash
# Via PowerShell (VPN requirement)
npx prettier --write "**/*.{ts,js,html,scss,json}"
npx eslint --fix .
```

### Backend (C#)

**EditorConfig + StyleCop:**
- PascalCase naming (`UserService`, `IUserService`)
- 4 spaces indentation
- German documentation
- Using directives outside namespace
- CRLF line endings

**ITSGrules.ruleset:**
- Security rules
- Disabled regions enforcement

**Manual Format:**
```bash
dotnet format VDEK.DCSP.sln
```

## Neovim 2025 Trends Summary

Based on research, the current setup includes these modern best practices:

**Already Implemented:**
- ✅ Lazy.nvim (modern plugin manager)
- ✅ Native LSP with Mason
- ✅ Tree-sitter (syntax understanding)
- ✅ Telescope (fuzzy finder)
- ✅ Neogit + Diffview (Git workflow)
- ✅ Toggleterm (terminal integration)
- ✅ Which-key (keybinding hints)
- ✅ Conform.nvim (formatting)
- ✅ Neotest (test runner)

**Trending in 2025:**
1. **AI/LLM Integration** - CopilotChat.nvim, codecompanion.nvim
2. **Neotest** - Test runner with inline UI ✅ (installed)
3. **nvim-dap** - Debugger with breakpoints (not yet installed)
4. **blink.cmp** - Modern completion engine
5. **C# specific** - csharp.nvim, easy-dotnet.nvim
6. **TypeScript specific** - typescript-tools.nvim

**Current Setup Status:** State-of-the-art for 2025! All essential plugins configured.

## Terminal Integration

### Toggleterm
Already configured with `<Ctrl-\>` to toggle terminal.

**Workflow:**
1. Start Backend: `<leader>br`
2. Hide terminal: `<Ctrl-\>` (keeps running in background)
3. Continue coding
4. Show terminal: `<Ctrl-\>` (to see output)
5. Stop Backend: `<Ctrl-c` in terminal

**Benefits:**
- Terminals run in background
- Toggle visibility without stopping processes
- Multiple terminals can run simultaneously

## Project Structure

**Repository:** `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE`

**Backend:** `Sources/Backend/` - C# / .NET solution
- WebHost: `VDEK.DCSP.WebHost` (runs on https://localhost:5443)
- Tests: `*.UnitTests`, `*.IntegrationTests`

**Frontend:** `Sources/Frontend/` - Angular 18 / TypeScript / Nx monorepo
- Runs on https://localhost:8443
- Requires PowerShell for npm operations (VPN)

## Tips and Troubleshooting

### Backend won't format?
→ Run `<leader>bs` (dotnet restore) first, then `:LspRestart`

### Frontend npm install fails?
→ Use `<leader>fc` (clean reinstall via PowerShell)

### Test icons not showing?
→ Restart Neovim after plugin changes

### Neotest sidebar won't jump to test?
→ Use `<leader>tn` directly in code, or use Toggleterm commands

### Want to see all warnings?
→ Press `<leader>w` for Telescope diagnostics list

### Terminal cluttered?
→ Press `<Ctrl-\>` to hide, work on code, press again to show

## Summary

This configuration provides a complete modern development environment:
- **Unified Keybindings** - Consistent schema (`b` = Backend, `f` = Frontend, `t` = Tests)
- **Dual Testing Approach** - Neotest for focused work, Toggleterm for full runs
- **Format on Save** - All languages automatically formatted
- **Inline Diagnostics** - See warnings/errors as you type
- **LSP Integration** - Go to definition, find references, code actions
- **Git Workflow** - Neogit for commits, Diffview for diffs
- **Terminal Integration** - Run services in background, toggle visibility
- **Modern Plugins** - State-of-the-art 2025 Neovim setup

The setup balances power-user features with approachability, using which-key hints to discover functionality.