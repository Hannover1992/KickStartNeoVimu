# nvim-lspconfig Settings Flattening - Technical Deep Dive

**Date:** November 12, 2025
**Purpose:** Detailed technical analysis of how settings are flattened and passed to LSP servers
**Target Audience:** Developers debugging LSP configuration or implementing custom servers

---

## 1. What is Settings Flattening?

Settings flattening is the **conversion of nested Lua table structures into flat command-line parameters** that can be passed directly to an executable.

### Example

**Input (Nested Table):**
```lua
settings = {
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    TabSize = 4,
    UseTabs = false,
  },
  MsBuild = {
    IncludePrereleases = true,
    LoadProjectsOnDemand = false,
  },
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
    EnableTypeInfoDocumentation = false,
  }
}
```

**Output (Flattened Arguments):**
```bash
FormattingOptions:EnableEditorConfigSupport=true
FormattingOptions:TabSize=4
FormattingOptions:UseTabs=false
MsBuild:IncludePrereleases=true
MsBuild:LoadProjectsOnDemand=false
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
RoslynExtensionsOptions:EnableTypeInfoDocumentation=false
```

**How they appear in the command:**
```bash
dotnet OmniSharp.dll --languageserver \
  FormattingOptions:EnableEditorConfigSupport=true \
  FormattingOptions:TabSize=4 \
  MsBuild:IncludePrereleases=true \
  ...
```

---

## 2. Where Flattening Happens in nvim-lspconfig

### 2.1 The Implementation Location

Flattening happens in the **server-specific `on_new_config` callback**, typically in:
- `lua/lspconfig/configs/omnisharp.lua` (for OmniSharp)
- `lua/lspconfig/configs/[server_name].lua` (for other servers)

Not all servers use flattening - it's specific to servers that accept settings as command-line arguments.

### 2.2 The Flattening Process (Pseudocode)

```lua
local function flatten_settings(settings, prefix)
  local result = {}

  for key, value in pairs(settings) do
    local full_key = prefix and (prefix .. ':' .. key) or key

    if type(value) == 'table' then
      -- Recursively flatten nested tables
      local nested = flatten_settings(value, full_key)
      for _, arg in ipairs(nested) do
        table.insert(result, arg)
      end
    else
      -- Convert to string argument
      table.insert(result, full_key .. '=' .. tostring(value))
    end
  end

  return result
end
```

### 2.3 Actual Implementation in omnisharp.lua

The actual nvim-lspconfig implementation in `omnisharp.lua`:

```lua
local function flatten_table(tbl, parent_key)
  local lines = {}
  for k, v in pairs(tbl) do
    local key = parent_key and parent_key .. ':' .. k or k
    if type(v) == 'table' then
      -- Recursively process nested tables
      for _, line in ipairs(flatten_table(v, key)) do
        table.insert(lines, line)
      end
    else
      -- Add key=value pair
      table.insert(lines, key .. '=' .. tostring(v))
    end
  end
  return lines
end

on_new_config = function(new_config, _)
  new_config.cmd = { unpack(new_config.cmd or {}) }

  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  -- ... more hard-coded args ...

  -- Flatten settings into cmd
  if new_config.settings then
    local flattened = flatten_table(new_config.settings)
    for _, arg in ipairs(flattened) do
      table.insert(new_config.cmd, arg)
    end
  end
end
```

---

## 3. When Does Flattening Occur?

### Timeline

```
t=0: User calls require('lspconfig').omnisharp.setup({ ... })
     Configuration stored in memory

t=N: C# file opened in Neovim
     |
     ├─ LSP framework detects file is for omnisharp
     ├─ Calls root_dir function to find project root
     ├─ Creates NEW configuration instance (deep copy)
     └─ **Calls on_new_config callback** ← FLATTENING HAPPENS HERE
        │
        ├─ Flatten settings table into arguments
        ├─ Append hard-coded arguments
        └─ Return modified new_config
     │
     ├─ Pass modified cmd to vim.fn.jobstart()
     └─ OmniSharp process spawned with flattened arguments
```

### Key Point: Fresh Copy for Each Root Directory

If you open files in multiple project directories, `on_new_config` is called **separately for each root directory**:

```
Project A/main.cs → on_new_config called → Server instance A launched
Project B/main.cs → on_new_config called → Server instance B launched
```

Each instance has its own flattened settings based on that project's root directory.

---

## 4. The Role of tbl_flatten() Utility

### What It Does

The `tbl_flatten()` utility in `lua/lspconfig/util.lua` flattens **array-like tables**, not settings objects:

```lua
function M.tbl_flatten(t)
  --- @diagnostic disable-next-line:deprecated
  return nvim_eleven and vim.iter(t):flatten(math.huge):totable() or vim.tbl_flatten(t)
end
```

### Example of What It Flattens

```lua
-- Input: Array with nested arrays
local input = { 'a', { 'b', { 'c', 'd' } }, 'e' }

-- Output
local output = { 'a', 'b', 'c', 'd', 'e' }
```

### Use Cases in nvim-lspconfig

1. **Root marker pattern flattening:**
```lua
-- Pattern matching for finding project root
local root_markers = flatten({
  '*.sln',
  '*.csproj',
  { 'omnisharp.json', 'function.json' }
})
-- Result: { '*.sln', '*.csproj', 'omnisharp.json', 'function.json' }
```

2. **Merging root detection patterns:**
```lua
local combined_patterns = tbl_flatten({
  default_patterns,
  custom_patterns
})
```

### Important Distinction

- **tbl_flatten():** For array-like tables (root markers, patterns)
- **Settings flattening:** Custom implementation in each server's on_new_config (for settings)

These are **different operations** - don't confuse them.

---

## 5. Settings Flattening vs JSON-RPC Format

### Two Different Mechanisms

#### Type 1: Command-Line Argument Format (OmniSharp)

Settings are **flattened into command-line arguments**:

```lua
settings = {
  Option1 = { SubOption = true }
}

-- Becomes:
-- Option1:SubOption=true  (as cmd argument)
```

**When used:** Servers that accept settings as CLI arguments
- OmniSharp (C#)
- Some Lua servers
- Custom language servers

#### Type 2: JSON-RPC Format (Most LSP Servers)

Settings are **sent as nested JSON object** in `initialize` request:

```lua
settings = {
  Option1 = { SubOption = true }
}

-- Becomes JSON:
{
  "initializationOptions": {
    "Option1": {
      "SubOption": true
    }
  }
}
```

**When used:** Standard LSP servers
- rust-analyzer
- pyright
- typescript-language-server
- Most others

---

## 6. Data Type Handling in Flattening

### Type Conversion Rules

```lua
settings = {
  BoolValue = true,        -- "BoolValue=true"
  NumericValue = 42,       -- "NumericValue=42"
  StringValue = "hello",   -- "StringValue=hello"
  NilValue = nil,          -- Skipped/not included
  TableValue = {},         -- Recursively flattened or skipped
}
```

### Falsy Values

```lua
-- Important: false is NOT nil
BoolFalse = false      -- "BoolFalse=false"  (INCLUDED)
NilValue = nil         -- (SKIPPED)

-- But in nvim-lspconfig, you might use:
OrganizeImports = nil  -- Explicitly set to nil (ignored)
```

### Complex Data Types

**Arrays in settings:**
```lua
-- ❌ Not typically supported
settings = {
  Paths = { '/path1', '/path2' }  -- How to flatten?
}

-- Flattening would produce: Paths=[object Object]
-- Usually not what you want
```

**Solution:** Most servers don't support arrays in settings. Use flat structure:
```lua
-- ✅ Instead
settings = {
  PrimaryPath = '/path1',
  SecondaryPath = '/path2',
}
```

---

## 7. Flattening and vim.tbl_deep_extend Interaction

### The Merge Happens BEFORE Flattening

```
User Configuration
    ↓
vim.tbl_deep_extend('keep', user_settings, defaults) ← MERGE
    ↓
Merged Settings Table
    ↓
on_new_config callback
    ├─ Settings are already merged
    └─ Flatten the merged result ← FLATTEN
    ↓
Final Command Arguments
```

### Example

```lua
-- Defaults from nvim-lspconfig
local defaults = {
  settings = {
    FormattingOptions = { TabSize = 2 },
    MsBuild = { LoadOnDemand = true }
  }
}

-- User configuration
local user_config = {
  settings = {
    FormattingOptions = { TabSize = 4 }
    -- MsBuild not specified
  }
}

-- Step 1: Merge (keep strategy)
local merged = vim.tbl_deep_extend('keep', user_config, defaults)
-- Result: {
--   settings = {
--     FormattingOptions = { TabSize = 4 },  -- From user
--     MsBuild = { LoadOnDemand = true }     -- From defaults
--   }
-- }

-- Step 2: Flatten (in on_new_config)
-- FormattingOptions:TabSize=4
-- MsBuild:LoadOnDemand=true
```

### Merge Strategy Impact

```lua
-- If using 'force' instead of 'keep':
local merged = vim.tbl_deep_extend('force', user_config, defaults)
-- Result: defaults completely override user config ❌

-- This is why nvim-lspconfig uses 'keep':
-- User settings are preserved, defaults fill gaps
```

---

## 8. Debugging Settings Flattening

### Debug Technique 1: Intercept on_new_config

```lua
require('lspconfig').omnisharp.setup({
  settings = { ... },

  on_new_config = function(new_config, new_root_dir)
    -- Print the settings BEFORE flattening
    vim.notify('Settings before flattening: ' .. vim.inspect(new_config.settings))

    -- Print the cmd AFTER flattening
    vim.notify('Cmd after flattening: ' .. vim.inspect(new_config.cmd))
  end
})
```

### Debug Technique 2: Check Process Arguments

```bash
# While Neovim is running
ps aux | grep omnisharp | grep -v grep

# Output shows actual command line with flattened arguments:
# dotnet /path/to/omnisharp.dll --languageserver --hostPID 12345
#   FormattingOptions:EnableEditorConfigSupport=true
#   MsBuild:IncludePrereleases=true
```

### Debug Technique 3: LSP Logs

```lua
-- Enable debug logging
vim.lsp.set_log_level('debug')
```

Then check:
```bash
tail -f ~/.local/state/nvim/lsp.log | grep -i "initialize"
```

Look for the `initialize` request which shows what settings were sent.

---

## 9. Flattening Errors and Solutions

### Error 1: Settings Not Appearing in Command

**Symptom:** `on_new_config` shows settings in `new_config.settings`, but they don't appear in cmd

**Cause:** Flattening code has a bug or wasn't implemented

**Solution:** Check that `on_new_config` actually flattens:
```lua
on_new_config = function(new_config, _)
  if new_config.settings then
    for k, v in pairs(new_config.settings) do
      -- Manually verify flattening is happening
      table.insert(new_config.cmd, k .. '=<value>')
    end
  end
end
```

### Error 2: Invalid Flattening Format

**Symptom:** LSP server rejects the flattened arguments

**Cause:** Format doesn't match what server expects

**Examples of format variations:**
```bash
# Format 1: Colon separator
FormattingOptions:TabSize=4

# Format 2: Underscore separator
FormattingOptions_TabSize=4

# Format 3: Nested brackets
FormattingOptions[TabSize]=4

# Format 4: Dot separator
FormattingOptions.TabSize=4
```

**Solution:** Check server documentation for expected format. OmniSharp uses **colon separator**.

### Error 3: Special Characters in Values

**Symptom:** Flattened argument is malformed

**Example:**
```lua
settings = {
  Path = "/my path/with spaces"  -- Space in path!
}

-- Flattened:
-- Path=/my path/with spaces  -- Ambiguous!
```

**Solution:** Server-specific - may need quoting or escaping:
```bash
# Might need:
Path="/my path/with spaces"
Path='my path/with spaces'
Path=/my\ path/with\ spaces
```

---

## 10. Performance Implications

### Flattening Overhead

For typical settings (5-10 nested key-value pairs):
- **Overhead:** Negligible (< 1ms)
- **Memory impact:** Minimal

For large settings objects (100+ pairs):
- **Overhead:** Still negligible
- **Process startup:** Might add a few milliseconds

### Optimization Considerations

1. **Avoid large nested structures:** Keep nesting to 2-3 levels
2. **Don't include unnecessary settings:** Only set what you need
3. **Use nil for defaults:** Set option to nil to skip it

```lua
-- ✅ Good
settings = {
  Option1 = true,
  Option2 = nil,  -- Skipped
}

-- ❌ Wasteful
settings = {
  Option1 = true,
  Option2 = false,
  Option3 = false,
  Option4 = false,
  ... (many more false values)
}
```

---

## 11. Compatibility Across Neovim Versions

### Flattening Implementation Status

| Neovim Version | tbl_flatten() | Settings Flattening | on_new_config |
|---|---|---|---|
| 0.7 | ✅ vim.tbl_flatten | ✅ Works | ✅ Works |
| 0.8 | ✅ vim.tbl_flatten | ✅ Works | ✅ Works |
| 0.9 | ✅ vim.tbl_flatten | ✅ Works | ✅ Works |
| 0.10 | ✅ vim.tbl_flatten | ✅ Works | ✅ Works |
| 0.11 | ✅ vim.iter().flatten() | ✅ Works | ❌ Missing* |

*on_new_config missing in native vim.lsp.config API but available via nvim-lspconfig

### Version Detection in nvim-lspconfig

```lua
local nvim_eleven = vim.fn.has 'nvim-0.11' == 1

function M.tbl_flatten(t)
  return nvim_eleven and vim.iter(t):flatten(math.huge):totable() or vim.tbl_flatten(t)
end
```

This ensures compatibility across versions.

---

## 12. Real-World Example: OmniSharp Flattening

### Complete Flow

```lua
-- User configuration
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll') },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = nil,
    },
    MsBuild = {
      IncludePrereleases = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
  }
})

-- When C# file opens, on_new_config is called:

on_new_config = function(new_config, new_root_dir)
  -- 1. Start with user cmd
  new_config.cmd = { 'dotnet', '.../OmniSharp.dll' }

  -- 2. Append hard-coded args
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- 3. Flatten settings into cmd
  local settings = new_config.settings or {}
  for parent_key, parent_value in pairs(settings) do
    for child_key, child_value in pairs(parent_value) do
      if child_value ~= nil then
        local flattened = parent_key .. ':' .. child_key .. '=' .. tostring(child_value)
        table.insert(new_config.cmd, flattened)
      end
    end
  end

  -- Final cmd:
  -- { 'dotnet', '.../OmniSharp.dll',
  --   '-z',
  --   '--hostPID', '12345',
  --   'DotNet:enablePackageRestore=false',
  --   '--encoding', 'utf-8',
  --   '--languageserver',
  --   'FormattingOptions:EnableEditorConfigSupport=true',
  --   'MsBuild:IncludePrereleases=true',
  --   'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  --   'RoslynExtensionsOptions:EnableImportCompletion=true'
  -- }
end

-- Passed to vim.fn.jobstart():
dotnet .../OmniSharp.dll \
  -z \
  --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 \
  --languageserver \
  FormattingOptions:EnableEditorConfigSupport=true \
  MsBuild:IncludePrereleases=true \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true
```

---

## Summary

1. **Settings flattening converts nested tables to command-line arguments**
2. **Happens in on_new_config callback**, server-specific implementation
3. **Not all servers use it** - only those accepting settings as CLI args
4. **Occurs AFTER merge** - merged settings are flattened, not defaults
5. **vim.tbl_deep_extend strategy doesn't affect flattening**, only configuration merging
6. **Debugging requires process inspection or log analysis**
7. **Performance is negligible** for typical configuration sizes
8. **Compatible across Neovim versions** via version-aware implementations

---

**Document Generated:** November 12, 2025
