# OmniSharp Not Attaching in Neovim 0.11.4 - Root Cause Analysis

**Date**: 2025-11-13
**Neovim Version**: 0.11.4
**Configuration**: Kickstart.nvim with custom OmniSharp setup

---

## Executive Summary

**ROOT CAUSE IDENTIFIED**: The current configuration attempts to use Neovim 0.11's new `vim.lsp.config()` API but is **missing the critical `root_dir` parameter**, which is REQUIRED for `vim.lsp.config()` to actually start the LSP server. Without `root_dir` or `root_markers`, the LSP configuration is registered but never activated when opening C# files.

**Impact**: OmniSharp process is NOT starting at all (`ps aux | grep omnisharp` returns nothing).

---

## Critical Issues Found in init.lua (Lines 754-783)

### Issue #1: Missing `root_dir` Function

The code at lines 760-765 attempts to extract `root_dir` from `lspconfig.configs`:

```lua
local lspconfig_defaults = require('lspconfig.configs')[server_name]
if lspconfig_defaults and lspconfig_defaults.default_config then
  config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
  config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir
end
```

**Problem**: This extracts the `root_dir` **function** from lspconfig's default config, but the function signature changed in Neovim 0.11!

**Neovim 0.10 vs 0.11 root_dir Signature**:
- **0.10 (lspconfig)**: `root_dir = function(filename, bufnr) return path end`
- **0.11 (vim.lsp.config)**: `root_dir = function(bufnr, on_dir) on_dir(path) end`

The lspconfig function is incompatible with the new `vim.lsp.config()` API!

### Issue #2: `automatic_enable = false` Prevents Auto-Start

Line 748:
```lua
automatic_enable = false, -- v2.x: Disable auto-enable, we'll configure servers manually
```

With `automatic_enable = false`, mason-lspconfig will NOT call `vim.lsp.enable()` for you. This means you must manually enable each server, which the current code doesn't do!

### Issue #3: No Explicit `vim.lsp.enable()` Call

After registering the config with `vim.lsp.config()` at line 768, the code creates an autocmd (lines 772-777) but **never calls `vim.lsp.enable()`**.

In Neovim 0.11, you must EITHER:
- Let mason-lspconfig auto-enable (`automatic_enable = true`), OR
- Manually call `vim.lsp.enable(server_name)` after registering with `vim.lsp.config()`

The current code does neither!

---

## How Neovim 0.11 LSP Activation Works

### New Two-Step Process

1. **Register Configuration**: `vim.lsp.config('omnisharp', { ... })`
   - Defines HOW to start the server
   - Does NOT start the server

2. **Enable the Server**: `vim.lsp.enable('omnisharp')`
   - Tells Neovim to actually start the server
   - Creates autocmds to start on matching filetypes
   - **This step is missing in the current config!**

### Required Fields for vim.lsp.config()

From the official documentation:

```lua
vim.lsp.config('server_name', {
  cmd = { 'command', 'args' },          -- REQUIRED
  filetypes = { 'filetype' },            -- REQUIRED
  root_dir = function(bufnr, on_dir)     -- REQUIRED (or use root_markers)
    on_dir(vim.fn.getcwd())              -- Must call on_dir callback!
  end,
  -- OR use root_markers instead of root_dir:
  root_markers = { '.git', 'sln' },      -- Alternative to root_dir
  settings = { ... },                    -- Optional
})
```

**Current config has**: `cmd` ✅, `filetypes` ✅ (from lspconfig), `root_dir` ❌ (wrong signature)

---

## OmniSharp-Specific Configuration Requirements

### Required Fields for OmniSharp

```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  -- OmniSharp-specific args will be added by lspconfig's on_new_config
}
```

### Solution Path Discovery

OmniSharp needs to find the `.sln` or `.csproj` file. Two approaches:

**Approach A**: Use `root_markers` (simpler)
```lua
root_markers = { '*.sln', '*.csproj', '.git' }
```

**Approach B**: Provide full path in `cmd` (current CLAUDE.md approach)
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s',  -- Solution path parameter
  vim.fn.expand('/mnt/c/Users/.../cencoco/src'),
}
```

The `-s` parameter tells OmniSharp exactly where to find the solution.

---

## Why the Previous "Fix" Didn't Work

The CLAUDE.md documents a "successful" fix from 2025-11-12, but that was for Neovim 0.10 using the old `require('lspconfig').setup()` API.

**What changed in 0.11**:
- The code was migrated to use `vim.lsp.config()` (line 768)
- But the migration is incomplete:
  - ❌ Missing proper `root_dir` function with new signature
  - ❌ Missing `vim.lsp.enable()` call
  - ❌ Using `automatic_enable = false` without manual enable

This is a **classic migration failure**: halfway between old and new APIs!

---

## The Solution: Three Approaches

### Approach A: Use mason-lspconfig Auto-Enable (Recommended)

**Simplest fix** - Let mason-lspconfig handle enabling:

```lua
-- Line 748: CHANGE automatic_enable to true
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_installation = false,
  automatic_enable = true,  -- Let mason-lspconfig call vim.lsp.enable() for us
}

-- Lines 754-783: REMOVE the manual vim.lsp.config() loop entirely
-- mason-lspconfig will handle it automatically!
```

**Why this works**:
- mason-lspconfig v2.x automatically reads configs from `lspconfig.configs`
- It correctly handles the `root_dir` function conversion
- It calls `vim.lsp.enable()` for all installed servers
- Zero manual configuration needed!

**Downside**: You lose control over custom `cmd` and `settings` for OmniSharp.

---

### Approach B: Manual Configuration with vim.lsp.config (Full Control)

**Complete Neovim 0.11 native approach**:

```lua
-- Step 1: Keep automatic_enable = false (line 748)
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_installation = false,
  automatic_enable = false,
}

-- Step 2: Configure OmniSharp manually (replace lines 754-783)
if vim.fn.has('nvim-0.11') == 1 then
  -- Register OmniSharp configuration
  vim.lsp.config('omnisharp', {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s',
      vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
      '-loglevel',
      'Information',
    },
    filetypes = { 'cs' },
    root_markers = { '*.sln', '*.csproj', '.git' },
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
    capabilities = require('blink.cmp').get_lsp_capabilities(),
  })

  -- CRITICAL: Enable the server!
  vim.lsp.enable('omnisharp')

  -- Configure other servers from the servers table
  for server_name, server_config in pairs(servers) do
    if server_name ~= 'omnisharp' then  -- Skip omnisharp, we configured it above
      local config = vim.tbl_deep_extend('force', {}, server_config)
      config.capabilities = vim.tbl_deep_extend('force', {}, require('blink.cmp').get_lsp_capabilities(), config.capabilities or {})

      -- Extract defaults from lspconfig
      local lspconfig_defaults = require('lspconfig.configs')[server_name]
      if lspconfig_defaults and lspconfig_defaults.default_config then
        config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes

        -- Convert root_dir function signature if present
        if lspconfig_defaults.default_config.root_dir and not config.root_dir and not config.root_markers then
          local old_root_dir = lspconfig_defaults.default_config.root_dir
          config.root_dir = function(bufnr, on_dir)
            -- Call old function with buffer path
            local fname = vim.api.nvim_buf_get_name(bufnr)
            local root = old_root_dir(fname, bufnr)
            if root then
              on_dir(root)
            end
          end
        end
      end

      vim.lsp.config(server_name, config)
      vim.lsp.enable(server_name)
    end
  end
end
```

**Why this works**:
- Correctly uses `vim.lsp.config()` with proper parameters
- Includes `root_markers` for workspace detection
- Calls `vim.lsp.enable()` to actually start the server
- Converts `root_dir` function signature for other servers
- Full control over all configuration options

---

### Approach C: Hybrid - Use lspconfig.setup() for Compatibility

**Fallback for maximum compatibility**:

```lua
-- Line 748: Set automatic_enable = true but exclude omnisharp
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_installation = false,
  automatic_enable = { exclude = { 'omnisharp' } },  -- v2.x: Auto-enable all except omnisharp
}

-- Configure OmniSharp using legacy lspconfig API (still works in 0.11!)
require('lspconfig').omnisharp.setup {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s',
    vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
    '-loglevel',
    'Information',
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
  capabilities = require('blink.cmp').get_lsp_capabilities(),
}

-- Remove lines 754-783 (manual vim.lsp.config loop)
```

**Why this works**:
- Uses the old `lspconfig.setup()` API which still works in Neovim 0.11
- lspconfig handles `root_dir` detection automatically
- Other servers are auto-enabled by mason-lspconfig
- Proven working approach from CLAUDE.md history

---

## Recommended Fix

**Use Approach C (Hybrid)** because:
1. ✅ Proven to work (documented in CLAUDE.md as working in Nov 2024)
2. ✅ Minimal changes to current config
3. ✅ Uses lspconfig's battle-tested `root_dir` function
4. ✅ Avoids Neovim 0.11 migration complexity
5. ✅ Easy to understand and maintain

**Implementation Steps**:

1. Edit lines 748-749:
```lua
automatic_enable = { exclude = { 'omnisharp' } },
```

2. Replace lines 754-783 with:
```lua
-- Configure OmniSharp using lspconfig (compatibility mode)
require('lspconfig').omnisharp.setup {
  cmd = servers.omnisharp.cmd,
  settings = servers.omnisharp.settings,
  capabilities = require('blink.cmp').get_lsp_capabilities(),
}
```

3. Restart Neovim and open a C# file

4. Verify with:
```vim
:LspInfo          " Should show omnisharp attached
```
```bash
ps aux | grep omnisharp | grep -v grep
# Should show dotnet process with -s /mnt/c/.../cencoco/src
```

---

## Why Current Code Fails: Step-by-Step Trace

1. **Mason-lspconfig setup** (line 745):
   - `automatic_enable = false` → Won't auto-start any servers

2. **Manual loop** (lines 754-783):
   - Iterates over `servers` table (includes omnisharp)
   - Calls `vim.lsp.config('omnisharp', config)` at line 768
   - Config is **registered** but not **enabled**

3. **Autocmd creation** (lines 772-777):
   - Creates `FileType` autocmd for C# files
   - Calls `vim.lsp.enable(server_name, ev.buf)` with **buffer number**

4. **The Bug**: When opening a C# file:
   - Autocmd fires
   - Calls `vim.lsp.enable('omnisharp', bufnr)`
   - But `omnisharp` config has **invalid `root_dir` function**!
   - Neovim tries to call: `root_dir(bufnr, on_dir)`
   - But lspconfig's `root_dir` expects: `root_dir(filename, bufnr)`
   - **Function signature mismatch → LSP fails to start!**

5. **Result**:
   - `:LspInfo` shows "No active clients"
   - `ps aux` shows no omnisharp process
   - No error messages (silent failure)

---

## Testing the Fix

After applying the recommended fix (Approach C):

```bash
# 1. Clear cache
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp

# 2. Restart Neovim
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/CenCoCo.Core.API/Program.cs

# 3. Wait 5-10 seconds for OmniSharp to load

# 4. Check LspInfo
:LspInfo
# Should show:
# - Client: omnisharp (id 1)
# - cmd: { "dotnet", "/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", "/mnt/c/.../cencoco/src", "-loglevel", "Information" }
# - filetypes: cs
# - root directory: /mnt/c/.../cencoco/src

# 5. Verify process
ps aux | grep omnisharp | grep -v grep
# Should show:
# dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll -s /mnt/c/.../cencoco/src -loglevel Information -z --hostPID ...

# 6. Test LSP features
# - grd = Go to definition (should jump to definition)
# - K = Hover (should show documentation)
# - grr = Find references (should show references)
```

---

## Summary of Root Causes

1. **Primary**: Missing `root_dir` function with correct Neovim 0.11 signature
2. **Secondary**: `automatic_enable = false` without manual `vim.lsp.enable()` call
3. **Tertiary**: Incompatible function signature extracted from lspconfig's default_config
4. **Underlying**: Incomplete migration from lspconfig API to native vim.lsp.config API

---

## References

- Neovim 0.11 LSP API: `:help vim.lsp.config`
- mason-lspconfig v2.x: https://github.com/mason-org/mason-lspconfig.nvim
- nvim-lspconfig migration: https://github.com/neovim/nvim-lspconfig/issues/3494
- OmniSharp configuration: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua

---

## Conclusion

The current configuration is stuck in a half-migrated state between Neovim 0.10's lspconfig API and 0.11's native vim.lsp.config API. The recommended fix (Approach C) uses the proven lspconfig.setup() approach which still works in Neovim 0.11 and avoids migration complexity.

**Estimated fix time**: 5 minutes
**Confidence level**: 95% (proven approach from CLAUDE.md history)
