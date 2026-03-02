# OmniSharp LSP Configuration - Complete Research Findings

**Date**: 2025-11-13
**Research Method**: 10 Parallel Sonnet Agents
**Status**: ✅ ROOT CAUSE IDENTIFIED

---

## 🎯 THE PROBLEM (Executive Summary)

**OmniSharp process runs** but **Neovim LSP client never attaches** because:

1. ❌ **Duplicate FileType autocmds** (lspconfig + manual)
2. ❌ **Custom `on_new_config` breaks settings flattening**
3. ❌ **NuGet packages not restored** (WSL2 cross-filesystem issue)

---

## 🔍 ROOT CAUSE #1: Duplicate FileType Autocmds

**Location**: `/home/uczen/.config/nvim/init.lua` lines 781-793

**Problem**:
```lua
-- Line 779: lspconfig.setup() ALREADY creates FileType autocmd
require('lspconfig')[server_name].setup(config)

-- Lines 781-793: DUPLICATE autocmd (WRONG!)
vim.api.nvim_create_autocmd('FileType', {
  pattern = require('lspconfig.configs')[server_name].filetypes or {},
  callback = function(args)
    local server = lspconfig[server_name]
    if server and server.manager then
      server.manager.try_add(args.buf)  -- Wrong method call syntax!
    end
  end,
})
```

**Evidence from `:autocmd FileType cs`:**
```
lspconfig  FileType
cs<Lua 227: ~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs.lua:83>

FileType
cs<Lua 229: ~/.config/nvim/init.lua:785>
```

**Why this breaks:**
- Two autocmds compete for same FileType event
- Manual autocmd has wrong call signature (missing parameters)
- Causes race conditions and conflicts

**FIX**: Delete lines 781-793. lspconfig handles this automatically.

---

## 🔍 ROOT CAUSE #2: on_new_config Override

**Location**: `/home/uczen/.config/nvim/init.lua` lines 710-726

**Problem**:
```lua
omnisharp = {
  on_new_config = function(new_config, new_root_dir)
    -- Sets custom cmd
    new_config.cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '...', '-loglevel', 'Information' }

    -- Tries to call original on_new_config
    local omnisharp_config = require('lspconfig.configs').omnisharp
    if omnisharp_config and omnisharp_config.default_config and omnisharp_config.default_config.on_new_config then
      omnisharp_config.default_config.on_new_config(new_config, new_root_dir)  -- ← DOESN'T WORK
    end
  end,
}
```

**Why this breaks:**
- When `lspconfig.setup()` is called, user's `on_new_config` **REPLACES** default `on_new_config`
- When user's function tries to call `default_config.on_new_config`, it's already been replaced!
- **Result**: Settings flattening never happens
- **Evidence**: `:LspInfo` shows `RoslynExtensionsOptions = {}` (empty!)

**Execution flow**:
1. User config has `on_new_config` function
2. `lspconfig.setup()` merges configs, user's function REPLACES default
3. When LSP starts, user's `on_new_config` runs
4. Tries to call original but finds itself (circular reference) or nothing
5. Settings never flattened to CLI args

**FIX**: Remove `on_new_config` override entirely. Just provide `cmd` and `settings` - lspconfig handles the rest.

---

## 🔍 ROOT CAUSE #3: NuGet Packages Not Restored

**Evidence from `~/.local/state/nvim/lsp.log`:**
```
[ERROR] "Package AWSSDK.S3, version 3.7.415.2 was not found"
[ERROR] "Package Microsoft.EntityFrameworkCore.Analyzers, version 8.0.11 was not found"
[ERROR] "OmniSharp.MSBuild.ProjectManager: Attempted to update project that is not loaded: CenCoCo.Core.API.csproj"
```

**702 occurrences** of:
```
"Tried to send request or notification before initialization was completed and will be sent later"
```

**Problem**:
- WSL2 + Windows cross-filesystem issue
- NuGet packages restored in Windows aren't visible to WSL
- OmniSharp can't load projects without packages
- OmniSharp never completes LSP initialization handshake
- Neovim can't attach because OmniSharp never responds to `initialize` request

**FIX**:
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
dotnet restore --force-evaluate --no-cache
```

---

## ✅ THE COMPLETE SOLUTION

### Step 1: Simplify OmniSharp Configuration

**File**: `/home/uczen/.config/nvim/init.lua`

**REMOVE lines 708-726** (on_new_config override):
```lua
-- DELETE THIS:
on_new_config = function(new_config, new_root_dir)
  ...
end,
```

**REMOVE lines 781-793** (duplicate autocmd):
```lua
-- DELETE THIS:
vim.api.nvim_create_autocmd('FileType', {
  ...
})
```

**KEEP this (simplified config)**:
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
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
},
```

**KEEP this (simple setup loop)**:
```lua
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  require('lspconfig')[server_name].setup(config)
  -- That's it! lspconfig handles everything automatically.
end
```

### Step 2: Fix NuGet Packages

```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
dotnet restore --force-evaluate --no-cache
```

**Expected output**: `Restore succeeded with 6 warning(s) in 2.7s`

### Step 3: Clean Up and Test

```bash
# Kill OmniSharp
pkill -f omnisharp

# Clear cache
rm -rf ~/.cache/nvim/luac/

# Start Neovim
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/Core/CenCoCo.Core.API/Program.cs
```

### Step 4: Verify

**In Neovim `:LspInfo`:**
```
vim.lsp: Active Clients ~
- Client: omnisharp (id: 1)
  cmd: { "dotnet", "/path/to/OmniSharp.dll", "-s", "/path/to/solution", "-loglevel", "Information", "-z", "--hostPID", "12345", "RoslynExtensionsOptions:EnableAnalyzersSupport=true", ... }
  settings: {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  ← NOT EMPTY!
      ...
    }
  }
```

**In bash:**
```bash
ps aux | grep omnisharp | grep -v grep
# Should show: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

---

## 📊 KEY INSIGHTS FROM RESEARCH

### Insight #1: How lspconfig.setup() Works

**From nvim-lspconfig source analysis:**
1. `lspconfig.setup(config)` **AUTOMATICALLY** creates FileType autocmd
2. Autocmd calls `manager:try_add(bufnr)` when matching filetype opens
3. `manager:try_add()` finds root_dir, calls `make_config()`
4. `make_config()` calls `on_new_config` to transform settings
5. Finally calls `vim.lsp.start()` to launch client

**Takeaway**: Don't try to manually recreate what lspconfig already does!

### Insight #2: mason-lspconfig v2.x Changes

**v2.0.0 (May 2025) removed handlers completely.**

**Old v1.x approach (DOESN'T WORK in v2.x)**:
```lua
require('mason-lspconfig').setup {
  handlers = {
    omnisharp = function() ... end,  -- ← REMOVED in v2.x
  },
}
```

**New v2.x approach**:
```lua
require('mason-lspconfig').setup {
  automatic_enable = false,  -- Disable auto-enable to use custom configs
}

for server_name, config in pairs(servers) do
  require('lspconfig')[server_name].setup(config)
  -- Optional: vim.lsp.enable(server_name) if automatic_enable = false
end
```

### Insight #3: Settings Flattening

**OmniSharp expects CLI args, not JSON config:**
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true  ← CLI format
```

**lspconfig's default `on_new_config` flattens automatically:**
```lua
-- Input (Lua table):
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  }
}

-- Output (CLI args appended to cmd):
cmd = { ..., "RoslynExtensionsOptions:EnableAnalyzersSupport=true" }
```

**DON'T override `on_new_config` unless you fully understand it!**

### Insight #4: lua_ls Works, omnisharp Doesn't

**lua_ls config (SIMPLE)**:
```lua
lua_ls = {
  settings = { Lua = { ... } },  -- Just settings
}
```

**omnisharp config (COMPLEX)**:
```lua
omnisharp = {
  cmd = { ... },                 -- Custom cmd
  on_new_config = function...    -- Override (BREAKS IT!)
  settings = { ... },
}
```

**Lesson**: Keep it simple! lua_ls works because it doesn't fight lspconfig.

---

## 📁 RESEARCH DOCUMENTS CREATED

All findings documented in detail:

1. **`OMNISHARP_LSPCONFIG_COMPLETE_ANALYSIS.md`** - nvim-lspconfig internals
2. **`MASON_LSPCONFIG_V2_BEHAVIOR.md`** - v2.x changes and solutions
3. **`NEOVIM_0.11_LSP_CLIENT_LIFECYCLE_REPORT.md`** - vim.lsp API comparison
4. **`OMNISHARP_MANAGER_MECHANISM.md`** - manager.try_add() deep dive
5. **`OMNISHARP_ON_NEW_CONFIG_ANALYSIS.md`** - Execution flow and timing
6. **`FILETYPE_AUTOCMD_RESEARCH.md`** - Duplicate autocmd problem
7. **`ROOT_DIR_ANALYSIS_REPORT.md`** - root_dir detection (working correctly)
8. **`WORKING_VS_BROKEN_CONFIGS.md`** - lua_ls vs omnisharp comparison
9. **`LSP_LOG_ANALYSIS.md`** - Log file analysis and NuGet issue
10. **`MINIMAL_REPRODUCTION_TESTS.md`** - Test suite to isolate problem

**Total research output**: ~200KB of documentation

---

## ⚡ QUICK FIX SUMMARY

**3 changes required**:

1. **Delete lines 708-726** (`on_new_config` override)
2. **Delete lines 781-793** (duplicate FileType autocmd)
3. **Run `dotnet restore --force-evaluate --no-cache`**

**Result**: OmniSharp will attach with correct settings.

---

## 🎓 LESSONS LEARNED

1. **Trust lspconfig** - It already handles FileType autocmds
2. **Don't override `on_new_config`** - Unless you re-implement flattening
3. **Keep configs simple** - Declarative > Imperative
4. **WSL2 + Windows NuGet** - Always restore with `--force-evaluate --no-cache`
5. **mason-lspconfig v2.x** - handlers removed, use direct setup instead
6. **Settings flattening is critical** - OmniSharp requires CLI args

---

## 🚀 IMPLEMENTATION STATUS

- ✅ Root causes identified
- ✅ Solution designed
- ✅ Documentation created
- ⏳ **NEXT**: Apply fixes to init.lua
- ⏳ **THEN**: Test and verify

**Estimated time to fix**: 5 minutes (delete 2 blocks, run 1 command)

---

## 📞 SUPPORT RESOURCES

**If issues persist after applying fixes:**

1. Check minimal test: `/tmp/run_omnisharp_tests.sh`
2. Read detailed docs in `/tmp/` directory
3. Verify NuGet restore succeeded: `dotnet build CenCoCo.sln`
4. Check LSP logs: `tail -f ~/.local/state/nvim/lsp.log`
5. Verify process: `ps aux | grep omnisharp`

---

**End of Research Findings**
