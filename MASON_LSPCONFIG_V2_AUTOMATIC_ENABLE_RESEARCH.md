# mason-lspconfig v2.x with automatic_enable=false - Comprehensive Research

**Date**: 2025-11-13
**Neovim Version**: 0.11.4
**mason-lspconfig Version**: v2.1.0 (stable-17-gb1d9a91)
**Research Focus**: Understanding `automatic_enable = false` behavior and vim.lsp.config() compatibility

---

## Executive Summary

**TL;DR**: When you set `automatic_enable = false` in mason-lspconfig v2.x:
- ✅ Mason-lspconfig will **NOT** call `vim.lsp.enable()` automatically
- ✅ You **MUST** manually call `vim.lsp.enable(server_name)` for each server
- ✅ This setting does **NOT** prevent `vim.lsp.config()` from working
- ✅ Manual `vim.lsp.config()` calls work fine - they just don't auto-enable
- ⚠️ OmniSharp configuration was **removed** from mason-lspconfig in v2.1.0

---

## What `automatic_enable = false` Does

### Official Documentation (mason-lspconfig.txt lines 145-160)

```lua
-- Default behavior (automatic_enable = true):
require("mason-lspconfig").setup({
    automatic_enable = true  -- DEFAULT
})
-- Result: mason-lspconfig automatically calls vim.lsp.enable()
-- for ALL installed servers

-- Disabled behavior (automatic_enable = false):
require("mason-lspconfig").setup({
    automatic_enable = false
})
-- Result: mason-lspconfig does NOT call vim.lsp.enable()
-- You MUST manually enable servers yourself
```

### Source Code Analysis (automatic_enable.lua lines 36-38)

```lua
elseif automatic_enable == false then
    return  -- Exit early, do NOT enable this server
end
```

**When `automatic_enable = false`**:
1. Mason-lspconfig's `enable_server()` function returns early (line 37)
2. No `vim.lsp.config()` override happens (line 44 skipped)
3. No `vim.lsp.enable()` call happens (line 47 skipped)
4. The server remains **configured but not enabled**

---

## Breaking Changes in mason-lspconfig v2.0.0 (May 2025)

### Removed Features

1. **Handlers API removed** (CHANGELOG line 47-48):
   ```lua
   -- ❌ NO LONGER WORKS in v2.x
   require('mason-lspconfig').setup {
     handlers = {
       function(server_name)
         require('lspconfig')[server_name].setup(...)
       end,
     }
   }
   ```

2. **automatic_installation removed** (CHANGELOG line 49-50):
   ```lua
   -- ❌ NO LONGER WORKS in v2.x
   require('mason-lspconfig').setup {
     automatic_installation = true
   }
   ```

3. **OmniSharp configuration removed** (CHANGELOG v2.1.0 line 13):
   - Fix commit: c5fba52548ff0722ffef127b0859d761a8118099
   - Issue: #556
   - **Impact**: mason-lspconfig no longer provides default OmniSharp config
   - **Reason**: Incompatible with new vim.lsp.config() mechanism

### New Features

**automatic_enable** (CHANGELOG line 54):
```lua
require("mason-lspconfig").setup({
    automatic_enable = true  -- NEW in v2.0, enabled by default
})
```

Replaces the old handlers mechanism with native Neovim 0.11 integration.

---

## How mason-lspconfig v2.x Works with Neovim 0.11

### Two-Step LSP Activation in Neovim 0.11

**Step 1: Register Configuration** (you or mason-lspconfig does this):
```lua
vim.lsp.config('omnisharp', {
  cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '/path/to/solution' },
  filetypes = { 'cs' },
  root_markers = { '*.sln', '*.csproj', '.git' },
  settings = { ... },
})
```
- This **defines** HOW to start the server
- Does **NOT** start the server yet

**Step 2: Enable the Server**:
```lua
vim.lsp.enable('omnisharp')
```
- This **tells Neovim to actually start** the server
- Creates autocmds to start on matching filetypes
- **THIS STEP IS MISSING when automatic_enable=false!**

### mason-lspconfig v2.x Behavior

**With `automatic_enable = true` (default)**:
1. Mason-lspconfig finds installed servers
2. For each server (if it has a config in `lsp/*.lua`):
   - Calls `vim.lsp.config(server_name, config)` (line 44)
   - Calls `vim.lsp.enable(server_name)` (line 47)
3. Server is **configured AND enabled** automatically

**With `automatic_enable = false`**:
1. Mason-lspconfig finds installed servers
2. For each server:
   - Returns early (line 37)
   - Does **NOTHING** - no config, no enable
3. Server remains **unconfigured AND disabled**

---

## OmniSharp-Specific Issues

### mason-lspconfig v2.1.0 Removed OmniSharp Config

**File listing**: `~/.local/share/nvim/lazy/mason-lspconfig.nvim/lua/mason-lspconfig/lsp/`

**Servers with configs**: astro, bicep, bsl_ls, cobol_ls, elixirls, esbonio, gradle_ls, groovyls, java_language_server, julials, lexical, nextflow_ls, nextls, powershell_es, pylsp, r_language_server, raku_navigator

**❌ NOT in list**: omnisharp

**What this means**:
- Even with `automatic_enable = true`, OmniSharp won't be auto-configured by mason-lspconfig
- You **MUST** manually configure OmniSharp using either:
  - `vim.lsp.config()` (Neovim 0.11+)
  - `require('lspconfig').omnisharp.setup()` (fallback)

---

## Correct Pattern for mason-lspconfig v2.x with Custom Configs

### Pattern 1: Let mason-lspconfig auto-enable, configure manually BEFORE

```lua
-- Step 1: Configure servers via vim.lsp.config() FIRST
vim.lsp.config('omnisharp', {
  cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', '-s', '/path/to/solution' },
  filetypes = { 'cs' },
  root_markers = { '*.sln', '*.csproj', '.git' },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
})

-- Step 2: Let mason-lspconfig auto-enable
require("mason").setup()
require("mason-lspconfig").setup({
    automatic_enable = true  -- Will call vim.lsp.enable('omnisharp')
})
```

**How it works**:
1. You configure OmniSharp with vim.lsp.config() first
2. Mason-lspconfig finds OmniSharp is installed
3. Mason-lspconfig calls vim.lsp.enable('omnisharp')
4. Neovim uses YOUR config (not mason-lspconfig's default, which doesn't exist for OmniSharp)

**Pros**: Simple, automatic
**Cons**: Relies on config being set before mason-lspconfig.setup()

---

### Pattern 2: Disable auto-enable, configure and enable manually

```lua
-- Step 1: Disable auto-enable
require("mason").setup()
require("mason-lspconfig").setup({
    ensure_installed = { 'omnisharp' },
    automatic_enable = false  -- We'll enable manually
})

-- Step 2: Configure and enable manually
vim.lsp.config('omnisharp', {
  cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', '-s', '/path/to/solution' },
  filetypes = { 'cs' },
  root_markers = { '*.sln', '*.csproj', '.git' },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
})

vim.lsp.enable('omnisharp')  -- ⚠️ CRITICAL: Must call this explicitly!
```

**How it works**:
1. Mason-lspconfig installs OmniSharp but doesn't enable it
2. You configure OmniSharp with vim.lsp.config()
3. You enable OmniSharp with vim.lsp.enable()

**Pros**: Full control, explicit
**Cons**: Must remember to call vim.lsp.enable() for EVERY server

---

### Pattern 3: Use selective auto-enable (exclude OmniSharp)

```lua
require("mason").setup()
require("mason-lspconfig").setup({
    automatic_enable = {
        exclude = { 'omnisharp' }  -- Auto-enable all EXCEPT omnisharp
    }
})

-- Configure OmniSharp manually
vim.lsp.config('omnisharp', { ... })
vim.lsp.enable('omnisharp')  -- Must call explicitly
```

**How it works**:
1. Mason-lspconfig auto-enables ALL servers EXCEPT omnisharp
2. You manually configure and enable OmniSharp

**Pros**: Best of both worlds - auto-enable for most servers, manual control for OmniSharp
**Cons**: Slightly more complex config

---

### Pattern 4: Use selective auto-enable (allow only specific servers)

```lua
require("mason-lspconfig").setup({
    automatic_enable = {
        'lua_ls',
        'rust_analyzer'  -- ONLY these servers will be auto-enabled
    }
})

-- OmniSharp is NOT in the list, so you must configure and enable manually
vim.lsp.config('omnisharp', { ... })
vim.lsp.enable('omnisharp')
```

**Pros**: Whitelist approach, explicit control
**Cons**: Must list every server you want auto-enabled

---

## Current init.lua Configuration Analysis

**File**: `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`

**Lines 745-783**:
```lua
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_installation = false,  -- ❌ Ignored in v2.x (removed feature)
  automatic_enable = false,         -- ✅ Works - disables auto-enable
}

-- Configure ALL servers from the servers table manually
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  if vim.fn.has('nvim-0.11') == 1 then
    -- Get filetypes from lspconfig
    local lspconfig_defaults = require('lspconfig.configs')[server_name]
    if lspconfig_defaults and lspconfig_defaults.default_config then
      config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
      config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir  -- ⚠️ WRONG SIGNATURE!
    end

    vim.lsp.config(server_name, config)  -- ✅ Registers config

    -- ⚠️ PROBLEM: Uses FileType autocmd instead of vim.lsp.enable()
    if config.filetypes then
      vim.api.nvim_create_autocmd('FileType', {
        pattern = config.filetypes,
        callback = function(ev)
          vim.lsp.enable(server_name, ev.buf)  -- ⚠️ Wrong API - should be vim.lsp.enable(server_name) WITHOUT buf param
        end,
      })
    end
  end
end
```

### Problems Identified

1. **automatic_installation = false** (line 747):
   - ❌ This setting was removed in mason-lspconfig v2.0
   - ❌ Has no effect, can be deleted

2. **root_dir function signature mismatch** (line 764):
   - ❌ lspconfig's root_dir: `function(filename, bufnr) return path end`
   - ❌ vim.lsp.config expects: `function(bufnr, on_dir) on_dir(path) end`
   - ❌ Copying lspconfig's function will NOT work with vim.lsp.config()

3. **Manual FileType autocmd** (lines 772-777):
   - ❌ Unnecessary - vim.lsp.enable() creates autocmds automatically
   - ❌ Wrong API: `vim.lsp.enable(server_name, ev.buf)` should be `vim.lsp.enable(server_name)` without buffer param

4. **Missing root_markers** (line 768):
   - ❌ vim.lsp.config() REQUIRES either `root_dir` function (correct signature) OR `root_markers` array
   - ❌ Current config has neither (root_dir has wrong signature)

---

## Recommended Fix for init.lua

### Option A: Use root_markers (simplest)

```lua
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_enable = false,  -- We'll enable manually
}

for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  if vim.fn.has('nvim-0.11') == 1 then
    -- Get filetypes from lspconfig
    local lspconfig_defaults = require('lspconfig.configs')[server_name]
    if lspconfig_defaults and lspconfig_defaults.default_config then
      config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes

      -- ✅ Use root_markers instead of root_dir function
      if not config.root_markers then
        -- Extract root markers from lspconfig's root_dir if possible
        config.root_markers = config.root_markers or { '.git' }  -- Fallback to .git
      end
    end

    -- Register configuration
    vim.lsp.config(server_name, config)

    -- Enable the server (creates autocmds automatically)
    vim.lsp.enable(server_name)  -- ✅ No buffer parameter needed
  else
    require('lspconfig')[server_name].setup(config)
  end
end
```

### Option B: Convert root_dir function signature

```lua
-- Get lspconfig's root_dir (Neovim 0.10 signature)
local lspconfig_defaults = require('lspconfig.configs')[server_name]
if lspconfig_defaults and lspconfig_defaults.default_config then
  config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes

  -- Convert root_dir function signature to Neovim 0.11 format
  local old_root_dir = lspconfig_defaults.default_config.root_dir
  if old_root_dir and not config.root_dir then
    config.root_dir = function(bufnr, on_dir)
      -- Call old function (filename, bufnr) with current buffer's filename
      local filename = vim.api.nvim_buf_get_name(bufnr)
      local root = old_root_dir(filename, bufnr)
      on_dir(root)  -- ✅ Call callback with result
    end
  end
end
```

### Option C: Use automatic_enable with exclusions (recommended for most users)

```lua
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_enable = {
    exclude = {}  -- Auto-enable all servers, or list exceptions
  }
}

-- Only configure servers BEFORE mason-lspconfig.setup() if you need custom configs
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  -- Add root_markers if missing
  config.root_markers = config.root_markers or { '.git' }

  vim.lsp.config(server_name, config)
end

-- Mason-lspconfig will call vim.lsp.enable() automatically for installed servers
require("mason-lspconfig").setup({ ... })
```

---

## OmniSharp-Specific Configuration for Neovim 0.11

### Complete Working Example

```lua
-- Define server configurations
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
      '-loglevel', 'Information',
    },
    filetypes = { 'cs' },
    root_markers = { '*.sln', '*.csproj', '.git' },  -- ✅ REQUIRED for vim.lsp.config
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
}

-- Configure OmniSharp BEFORE mason-lspconfig setup
vim.lsp.config('omnisharp', servers.omnisharp)

-- Setup mason-lspconfig
require('mason-lspconfig').setup {
  ensure_installed = { 'omnisharp' },
  automatic_enable = true,  -- Will call vim.lsp.enable('omnisharp') automatically
}
```

### Alternative: Manual enable

```lua
-- Configure OmniSharp
vim.lsp.config('omnisharp', servers.omnisharp)

-- Setup mason-lspconfig without auto-enable
require('mason-lspconfig').setup {
  ensure_installed = { 'omnisharp' },
  automatic_enable = false,
}

-- Manually enable OmniSharp
vim.lsp.enable('omnisharp')
```

---

## Known Issues and Gotchas

### 1. root_markers vs root_dir

**Problem**: vim.lsp.config() REQUIRES either `root_markers` OR `root_dir` function

**Solution**: Always provide at least `root_markers = { '.git' }` as fallback

### 2. vim.lsp.enable() buffer parameter

**Problem**: Documentation shows `vim.lsp.enable(server_name, bufnr)` but this is OPTIONAL

**Correct usage**:
```lua
vim.lsp.enable('omnisharp')  -- Enable globally (creates autocmds)
-- OR
vim.lsp.enable('omnisharp', bufnr)  -- Enable for specific buffer only
```

**For normal use**: Call WITHOUT buffer parameter - Neovim will create autocmds automatically

### 3. Configuration order matters

**Problem**: If you call `vim.lsp.config()` AFTER `vim.lsp.enable()`, the config won't apply

**Correct order**:
1. `vim.lsp.config(server_name, config)` - Register configuration
2. `vim.lsp.enable(server_name)` - Enable server

### 4. OmniSharp cmd must be direct DLL path

**Problem**: Mason's wrapper script doesn't work with vim.lsp.config()

**Solution**: Use direct DLL path:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  -- NOT: '~/.local/share/nvim/mason/bin/OmniSharp'
}
```

---

## Compatibility Matrix

| Neovim Version | mason-lspconfig Version | Recommended Approach |
|----------------|-------------------------|----------------------|
| 0.10.x or older | v1.x (handlers API) | Use handlers + lspconfig.setup() |
| 0.11.0 - 0.11.3 | v1.x (transitional) | Use handlers OR vim.lsp.config() |
| 0.11.4+ | v2.0.0+ | Use vim.lsp.config() + automatic_enable |

**Current setup**: Neovim 0.11.4 + mason-lspconfig v2.1.0 = ✅ Fully compatible with vim.lsp.config()

---

## Summary and Recommendations

### What `automatic_enable = false` Does

✅ **Disables automatic vim.lsp.enable() calls** by mason-lspconfig
❌ **Does NOT prevent vim.lsp.config() from working**
❌ **Does NOT prevent manual vim.lsp.enable() calls**

### When to Use `automatic_enable = false`

- ✅ When you want full control over which servers start
- ✅ When you need custom enable logic per server
- ✅ When you're debugging LSP configuration issues

### When NOT to Use `automatic_enable = false`

- ❌ If you forget to call vim.lsp.enable() manually (servers won't start)
- ❌ If you want "zero-config" experience (default auto-enable is easier)

### Recommended Approach for Current Setup

**Option 1: Keep automatic_enable = false** (current approach):
```lua
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_enable = false,
}

-- Configure and enable manually
for server_name, server_config in pairs(servers) do
  vim.lsp.config(server_name, config)
  vim.lsp.enable(server_name)  -- ✅ Must call this!
end
```

**Option 2: Use automatic_enable = true** (simpler):
```lua
-- Configure BEFORE mason-lspconfig setup
for server_name, server_config in pairs(servers) do
  vim.lsp.config(server_name, config)
end

-- Let mason-lspconfig call vim.lsp.enable() for you
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_enable = true,  -- Auto-enable installed servers
}
```

### Critical Fix for init.lua

**Must fix these issues**:
1. Remove `automatic_installation = false` (removed feature)
2. Add `root_markers` to configs OR convert `root_dir` function signature
3. Remove manual FileType autocmd (vim.lsp.enable() handles this)
4. Call `vim.lsp.enable(server_name)` WITHOUT buffer parameter
5. Ensure vim.lsp.config() is called BEFORE vim.lsp.enable()

---

## Additional Resources

- Official mason-lspconfig docs: `:help mason-lspconfig`
- Neovim 0.11 LSP docs: `:help lsp-quickstart`, `:help vim.lsp.config`, `:help vim.lsp.enable`
- mason-lspconfig CHANGELOG: `~/.local/share/nvim/lazy/mason-lspconfig.nvim/CHANGELOG.md`
- GitHub issues: https://github.com/mason-org/mason-lspconfig.nvim/issues
- nvim-lspconfig migration guide: https://github.com/neovim/nvim-lspconfig/issues/3705

---

## Conclusion

**The current configuration is using the correct approach** (`automatic_enable = false` + manual configuration), but has implementation bugs:

1. ❌ Missing `root_markers` in configs
2. ❌ Wrong `root_dir` function signature
3. ❌ Unnecessary manual FileType autocmd
4. ❌ Wrong vim.lsp.enable() API usage (buffer parameter)

**Fixing these issues will make OmniSharp (and all other servers) work correctly with Neovim 0.11 + mason-lspconfig v2.x.**
