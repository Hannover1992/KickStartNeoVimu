# nvim-lspconfig Settings Flattening Deep Dive
## Complete Source Code Analysis of OmniSharp on_new_config

**Date**: 2025-11-13
**Analysis Method**: Complete source code review + execution flow tracing
**Target**: Understanding why custom `on_new_config` breaks settings flattening
**Neovim Version**: 0.11.4 (uses `vim.lsp.config` API)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Source Code Analysis](#source-code-analysis)
3. [Settings Flattening Algorithm](#settings-flattening-algorithm)
4. [Why Custom on_new_config Fails](#why-custom-on_new_config-fails)
5. [Neovim 0.11 vs 0.10 Differences](#neovim-011-vs-010-differences)
6. [Correct Solutions](#correct-solutions)
7. [Test Cases](#test-cases)
8. [Verification Commands](#verification-commands)

---

## Executive Summary

**THE PROBLEM**: Your init.lua uses Neovim 0.11's `vim.lsp.config` API which **BYPASSES nvim-lspconfig's `on_new_config` entirely**.

**KEY FINDING**:
- In Neovim 0.11, `vim.lsp.config()` does **NOT** call nvim-lspconfig's `on_new_config` function
- The settings flattening code exists in lspconfig but is **NEVER EXECUTED** when using the new API
- Result: Settings stay as Lua tables and OmniSharp never receives them as CLI args

**ROOT CAUSE**: Lines 759-778 in init.lua use `vim.lsp.config()` which is a **native Neovim API** that doesn't run lspconfig's transformation functions.

**SOLUTION**: Use the fallback path (line 781) that calls `lspconfig[server_name].setup(config)` - this properly executes `on_new_config`.

---

## Source Code Analysis

### 1. nvim-lspconfig's OmniSharp on_new_config

**File**: `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`

**Lines 46-78** (Complete implementation):

```lua
on_new_config = function(new_config, _)
  -- STEP 1: Copy the base cmd array
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- STEP 2: Append hard-coded OmniSharp arguments
  table.insert(new_config.cmd, '-z') -- Enables stdio mode
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- STEP 3: Flatten settings table to command-line arguments
  local function flatten(tbl)
    local ret = {}
    for k, v in pairs(tbl) do
      if type(v) == 'table' then
        -- RECURSIVE: Nested tables use ':' separator
        for _, pair in ipairs(flatten(v)) do
          ret[#ret + 1] = k .. ':' .. pair
        end
      else
        -- LEAF VALUES: Use '=' separator with vim.inspect()
        ret[#ret + 1] = k .. '=' .. vim.inspect(v)
      end
    end
    return ret
  end

  -- STEP 4: Apply flattening if settings exist
  if new_config.settings then
    vim.list_extend(new_config.cmd, flatten(new_config.settings))
  end

  -- STEP 5: Disable workspace folders (OmniSharp limitation)
  new_config.capabilities = vim.deepcopy(new_config.capabilities)
  new_config.capabilities.workspace.workspaceFolders = false
end,
```

**Critical insights:**

1. **`unpack(new_config.cmd or {})`**: Creates a COPY of cmd array (doesn't mutate original)
2. **Hard-coded args**: Always appended regardless of user config
3. **Flatten function**: Recursive - handles nested tables like `RoslynExtensionsOptions.EnableAnalyzersSupport`
4. **vim.inspect(v)**: Converts Lua values to strings (true → "true", false → "false", nil → "nil")
5. **Separator rules**:
   - Nested tables: `ParentKey:ChildKey=value`
   - Leaf values: `Key=value`

---

### 2. How lspconfig.setup() Calls on_new_config

**File**: `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs.lua`

**Lines 177-190** (make_config function):

```lua
local make_config = function(root_dir)
  local new_config = tbl_deep_extend('keep', vim.empty_dict(), config)
  new_config.capabilities = tbl_deep_extend('keep', new_config.capabilities, {
    workspace = { configuration = true },
  })

  -- CRITICAL: Calls default_config.on_new_config first
  if config_def.on_new_config then
    pcall(config_def.on_new_config, new_config, root_dir)
  end

  -- THEN: Calls user's on_new_config (if provided)
  if config.on_new_config then
    pcall(config.on_new_config, new_config, root_dir)
  end

  -- ... rest of setup
end
```

**Execution order:**
1. **config_def.on_new_config** (lspconfig's default) runs FIRST
2. **config.on_new_config** (user's override) runs SECOND
3. If user provides `on_new_config`, it receives a `new_config` already transformed by default function

**Key insight**: User's `on_new_config` can **ADD** to what default did, but if user REPLACES cmd entirely, default's work is lost!

---

## Settings Flattening Algorithm

### Input (Lua Table)

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
  Sdk = {
    IncludePrereleases = true,
  },
}
```

### Flattening Process

**Step 1**: Start with `RoslynExtensionsOptions` table
```lua
k = "RoslynExtensionsOptions"
v = { EnableAnalyzersSupport = true, EnableImportCompletion = true, ... }
type(v) == 'table' -- TRUE: Recurse
```

**Step 2**: Recurse into nested table
```lua
-- First nested key:
k = "EnableAnalyzersSupport"
v = true
type(v) ~= 'table' -- TRUE: Leaf value
ret[#ret + 1] = "EnableAnalyzersSupport" .. '=' .. vim.inspect(true)
-- Result: "EnableAnalyzersSupport=true"
```

**Step 3**: Return to parent level
```lua
pair = "EnableAnalyzersSupport=true"
ret[#ret + 1] = "RoslynExtensionsOptions" .. ':' .. pair
-- Result: "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
```

### Complete Output (Command-line Args)

```bash
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
FormattingOptions:EnableEditorConfigSupport=true
FormattingOptions:OrganizeImports=true
Sdk:IncludePrereleases=true
```

### Final cmd Array

**After on_new_config completes:**

```lua
cmd = {
  -- User's base cmd:
  'dotnet',
  '/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '/mnt/c/.../cencoco/src',
  '-loglevel', 'Information',

  -- lspconfig's hard-coded args:
  '-z',
  '--hostPID', '12345',
  'DotNet:enablePackageRestore=false',
  '--encoding', 'utf-8',
  '--languageserver',

  -- Flattened settings:
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  'RoslynExtensionsOptions:EnableImportCompletion=true',
  'RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false',
  'FormattingOptions:EnableEditorConfigSupport=true',
  'FormattingOptions:OrganizeImports=true',
  'Sdk:IncludePrereleases=true',
}
```

---

## Why Custom on_new_config Fails

### SCENARIO 1: Replacing on_new_config (Previous Attempt)

**User config (init.lua lines 708-726 - now removed)**:

```lua
omnisharp = {
  cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '...', '-loglevel', 'Information' },
  settings = { RoslynExtensionsOptions = { EnableAnalyzersSupport = true } },

  on_new_config = function(new_config, new_root_dir)
    -- User tries to set custom cmd
    new_config.cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '...', '-loglevel', 'Information' }

    -- User tries to call original on_new_config
    local omnisharp_config = require('lspconfig.configs').omnisharp
    if omnisharp_config and omnisharp_config.default_config and omnisharp_config.default_config.on_new_config then
      omnisharp_config.default_config.on_new_config(new_config, new_root_dir)
    end
  end,
}
```

**What happens:**

1. `lspconfig.setup()` is called with this config
2. `make_config()` runs:
   ```lua
   -- Tries to call config_def.on_new_config (default)
   if config_def.on_new_config then
     pcall(config_def.on_new_config, new_config, root_dir)
   end
   ```
3. But `config_def` now CONTAINS the merged user config!
4. So it calls user's `on_new_config` which:
   - Sets cmd to user's version
   - Tries to call `default_config.on_new_config` from the registry
   - But the registry has already been modified by the merge!
5. Result: Default on_new_config may not run, or runs with wrong state

**Why the manual call fails:**
- `require('lspconfig.configs').omnisharp` returns the **already merged** config
- Not the original default config
- The `on_new_config` function reference might point to user's own function (circular!)

---

### SCENARIO 2: Using vim.lsp.config (Current Issue)

**Current init.lua (lines 759-778)**:

```lua
if vim.fn.has('nvim-0.11') == 1 then
  -- Get filetypes from lspconfig as fallback
  local lspconfig_defaults = require('lspconfig.configs')[server_name]
  if lspconfig_defaults and lspconfig_defaults.default_config then
    config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
    config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir
  end

  -- Register with new API
  vim.lsp.config(server_name, config)

  -- Enable on matching filetypes
  if config.filetypes then
    vim.api.nvim_create_autocmd('FileType', {
      pattern = config.filetypes,
      callback = function(ev)
        vim.lsp.enable(server_name, ev.buf)
      end,
    })
  end
end
```

**CRITICAL PROBLEM**:

`vim.lsp.config()` is a **NATIVE Neovim 0.11 API** that:
- Does **NOT** call nvim-lspconfig's `on_new_config`
- Directly registers the config with Neovim's LSP subsystem
- Expects cmd to be fully formed (no transformations)

**Result**:
- User's `config.cmd` is used AS-IS
- User's `config.settings` is used AS-IS (stays as Lua table)
- No flattening occurs
- OmniSharp receives settings as JSON (doesn't understand it)
- Settings are ignored → Analyzers never enabled

---

## Neovim 0.11 vs 0.10 Differences

### Neovim 0.10 and Earlier

**LSP Setup Path:**
```
User calls lspconfig.setup(config)
  → lspconfig validates config
  → lspconfig calls make_config(root_dir)
    → make_config calls on_new_config
      → on_new_config flattens settings
    → make_config calls vim.lsp.start(final_config)
```

**Key**: lspconfig is the orchestrator, controls entire lifecycle.

---

### Neovim 0.11 with vim.lsp.config

**New LSP Setup Path:**
```
User calls vim.lsp.config(name, config)
  → Neovim stores config in internal registry
  → When FileType matches:
    → Neovim calls vim.lsp.enable(name, bufnr)
      → Neovim retrieves config from registry
      → Neovim calls vim.lsp.start_client(config)
```

**Key**: Neovim owns lifecycle, lspconfig is bypassed!

---

### What Gets Lost in 0.11

When using `vim.lsp.config()`:

1. ❌ **No on_new_config execution** - Settings never flattened
2. ❌ **No cmd transformation** - Hard-coded args never appended
3. ❌ **No capability merging** - Default capabilities not added
4. ⚠️ **root_dir must be pre-computed** - No lazy evaluation

**User must manually do what lspconfig did automatically:**
- Flatten settings to CLI args
- Append hard-coded OmniSharp args
- Merge capabilities
- Compute root_dir upfront

---

## Correct Solutions

### Solution 1: Use lspconfig.setup() (Recommended)

**Replace lines 759-778 with:**

```lua
-- REMOVE the if vim.fn.has('nvim-0.11') == 1 block entirely
-- Use the fallback path for ALL Neovim versions:

for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  -- Use lspconfig for ALL servers (works on 0.10 and 0.11)
  require('lspconfig')[server_name].setup(config)
end
```

**Why this works:**
- ✅ lspconfig's `on_new_config` runs automatically
- ✅ Settings are properly flattened
- ✅ Hard-coded OmniSharp args appended
- ✅ Works on Neovim 0.10 and 0.11
- ✅ nvim-lspconfig handles Neovim version differences internally

**Verification:**
```vim
:lua print(vim.inspect(require('lspconfig').omnisharp.manager.config.cmd))
-- Should show FULL cmd with flattened settings
```

---

### Solution 2: Manual Flattening with vim.lsp.config

**If you MUST use vim.lsp.config (not recommended):**

```lua
if vim.fn.has('nvim-0.11') == 1 then
  -- MANUALLY flatten settings before passing to vim.lsp.config
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

  -- Copy config and transform it
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  -- MANUALLY append hard-coded OmniSharp args
  if server_name == 'omnisharp' then
    table.insert(config.cmd, '-z')
    vim.list_extend(config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
    table.insert(config.cmd, 'DotNet:enablePackageRestore=false')
    vim.list_extend(config.cmd, { '--encoding', 'utf-8' })
    table.insert(config.cmd, '--languageserver')

    -- Flatten and append settings
    if config.settings then
      vim.list_extend(config.cmd, flatten_settings(config.settings))
      config.settings = nil -- Remove settings after flattening
    end

    -- Disable workspace folders
    config.capabilities = vim.deepcopy(config.capabilities)
    config.capabilities.workspace.workspaceFolders = false
  end

  -- Get filetypes/root_dir from lspconfig
  local lspconfig_defaults = require('lspconfig.configs')[server_name]
  if lspconfig_defaults and lspconfig_defaults.default_config then
    config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
    config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir
  end

  vim.lsp.config(server_name, config)

  if config.filetypes then
    vim.api.nvim_create_autocmd('FileType', {
      pattern = config.filetypes,
      callback = function(ev)
        vim.lsp.enable(server_name, ev.buf)
      end,
    })
  end
end
```

**Why this is NOT recommended:**
- ❌ You're re-implementing what lspconfig already does
- ❌ Must manually handle every server's quirks
- ❌ Harder to maintain
- ❌ Duplicates lspconfig code
- ✅ Only benefit: Direct use of Neovim 0.11 API (marginal)

---

### Solution 3: Hybrid Approach

**Use lspconfig for complex servers, vim.lsp.config for simple ones:**

```lua
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  -- Servers that need lspconfig's on_new_config
  local needs_lspconfig = {
    omnisharp = true,  -- Needs settings flattening
    -- Add other servers with complex on_new_config here
  }

  if needs_lspconfig[server_name] then
    -- Use lspconfig for complex servers
    require('lspconfig')[server_name].setup(config)
  elseif vim.fn.has('nvim-0.11') == 1 then
    -- Use new API for simple servers
    local lspconfig_defaults = require('lspconfig.configs')[server_name]
    if lspconfig_defaults and lspconfig_defaults.default_config then
      config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
      config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir
    end

    vim.lsp.config(server_name, config)

    if config.filetypes then
      vim.api.nvim_create_autocmd('FileType', {
        pattern = config.filetypes,
        callback = function(ev)
          vim.lsp.enable(server_name, ev.buf)
        end,
      })
    end
  else
    -- Fallback to lspconfig for older Neovim
    require('lspconfig')[server_name].setup(config)
  end
end
```

**Best of both worlds:**
- ✅ OmniSharp uses lspconfig (gets settings flattening)
- ✅ Simple servers can use new API if desired
- ⚠️ More complex but flexible

---

## Test Cases

### Test 1: Verify Settings Flattening

**Setup:**
```lua
omnisharp = {
  cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll' },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
}

require('lspconfig').omnisharp.setup(omnisharp)
```

**Expected cmd after on_new_config:**
```lua
{
  'dotnet',
  '/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z',
  '--hostPID', '12345',
  'DotNet:enablePackageRestore=false',
  '--encoding', 'utf-8',
  '--languageserver',
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
}
```

**Verification:**
```vim
:lua print(vim.inspect(require('lspconfig').omnisharp.manager.config.cmd))
```

---

### Test 2: Verify Process Arguments

**After OmniSharp starts:**

```bash
ps aux | grep omnisharp | grep -v grep
```

**Expected output:**
```
dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -z \
  --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 \
  --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
  FormattingOptions:EnableEditorConfigSupport=true \
  FormattingOptions:OrganizeImports=true \
  Sdk:IncludePrereleases=true
```

**If missing**: Settings weren't flattened.

---

### Test 3: Verify :LspInfo Output

**In Neovim:**
```vim
:LspInfo
```

**Expected settings section:**
```
settings: {
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    OrganizeImports = true
  },
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false
  },
  Sdk = {
    IncludePrereleases = true
  }
}
```

**NOT:**
```
settings: {
  RoslynExtensionsOptions = {}   ← EMPTY = BROKEN
}
```

---

### Test 4: Minimal Reproduction

**Create `/tmp/test_omnisharp_flatten.lua`:**

```lua
-- Test settings flattening in isolation
local function flatten(tbl)
  local ret = {}
  for k, v in pairs(tbl) do
    if type(v) == 'table' then
      for _, pair in ipairs(flatten(v)) do
        ret[#ret + 1] = k .. ':' .. pair
      end
    else
      ret[#ret + 1] = k .. '=' .. vim.inspect(v)
    end
  end
  return ret
end

local settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    OrganizeImports = true,
  },
}

local flattened = flatten(settings)
print(vim.inspect(flattened))
```

**Run:**
```bash
nvim -l /tmp/test_omnisharp_flatten.lua
```

**Expected output:**
```lua
{
  "RoslynExtensionsOptions:EnableAnalyzersSupport=true",
  "RoslynExtensionsOptions:EnableImportCompletion=true",
  "RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false",
  "FormattingOptions:EnableEditorConfigSupport=true",
  "FormattingOptions:OrganizeImports=true"
}
```

---

## Verification Commands

### 1. Check LSP Client Configuration

```vim
:lua print(vim.inspect(vim.lsp.get_clients({ name = 'omnisharp' })[1].config))
```

**Look for:**
- `cmd`: Should have flattened settings as last elements
- `settings`: Should have full nested structure

---

### 2. Check lspconfig Manager State

```vim
:lua print(vim.inspect(require('lspconfig').omnisharp.manager.config))
```

**Look for:**
- `cmd`: Should show transformed command
- Indicates if lspconfig's setup ran

---

### 3. Check Running Process

```bash
ps aux | grep omnisharp | grep -v grep | tr ' ' '\n' | grep -E 'Roslyn|Formatting|Sdk'
```

**Should show:**
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
FormattingOptions:EnableEditorConfigSupport=true
FormattingOptions:OrganizeImports=true
Sdk:IncludePrereleases=true
```

---

### 4. Check LSP Logs

```bash
tail -100 ~/.local/state/nvim/lsp.log | grep -i "roslyn\|analyzer"
```

**If flattening worked:**
```
[INFO] OmniSharp loading Roslyn analyzers...
[INFO] StyleCop analyzer loaded
```

**If flattening failed:**
```
(No mentions of analyzers or "RoslynExtensionsOptions")
```

---

### 5. Test in Fresh Neovim Instance

```bash
# Kill all OmniSharp processes
pkill -f omnisharp

# Clear cache
rm -rf ~/.cache/nvim/luac/

# Start with minimal config test
nvim -u /tmp/minimal_omnisharp.lua /path/to/file.cs
```

**Minimal test config:**
```lua
-- /tmp/minimal_omnisharp.lua
local lazypath = vim.fn.stdpath('data') .. '/lazy/lazy.nvim'
vim.opt.rtp:prepend(lazypath)

require('lazy').setup({
  'neovim/nvim-lspconfig',
})

local capabilities = vim.lsp.protocol.make_client_capabilities()

require('lspconfig').omnisharp.setup {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
  capabilities = capabilities,
}
```

**Check if it works:**
```vim
:LspInfo
:lua print(vim.inspect(vim.lsp.get_clients()[1].config.cmd))
```

---

## Summary and Recommendations

### Key Findings

1. **nvim-lspconfig's on_new_config is sophisticated**
   - Flattens Lua tables to CLI args
   - Appends hard-coded OmniSharp args
   - Handles capabilities and workspace folders

2. **Neovim 0.11's vim.lsp.config bypasses lspconfig**
   - No on_new_config execution
   - User must manually flatten settings
   - Only worth using for simple servers

3. **Current init.lua has the wrong approach**
   - Uses vim.lsp.config for ALL servers including OmniSharp
   - Settings never flattened
   - OmniSharp receives Lua tables (invalid)

### Recommended Solution

**Replace lines 754-783 with:**

```lua
-- Configure ALL servers using lspconfig (works on 0.10 and 0.11)
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  require('lspconfig')[server_name].setup(config)
end
```

**Why:**
- ✅ Simple and correct
- ✅ lspconfig handles all transformations
- ✅ Works on Neovim 0.10 and 0.11
- ✅ No manual flattening needed
- ✅ No duplicate FileType autocmds
- ✅ Settings properly converted to CLI args

### What NOT to Do

1. ❌ Don't provide custom `on_new_config` unless you fully re-implement flattening
2. ❌ Don't use `vim.lsp.config` for servers with complex on_new_config (like OmniSharp)
3. ❌ Don't manually create FileType autocmds - lspconfig does this
4. ❌ Don't try to call `default_config.on_new_config` manually - it won't work

### Final Verification Checklist

After applying fix:

- [ ] Clear cache: `rm -rf ~/.cache/nvim/luac/`
- [ ] Kill OmniSharp: `pkill -f omnisharp`
- [ ] Restore NuGet: `dotnet restore --force-evaluate --no-cache`
- [ ] Start Neovim: `nvim /path/to/file.cs`
- [ ] Check `:LspInfo` - settings should NOT be empty
- [ ] Check process: `ps aux | grep RoslynExtensionsOptions`
- [ ] Verify diagnostics appear in code

---

**End of Deep Dive Analysis**
