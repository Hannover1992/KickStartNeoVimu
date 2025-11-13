# OmniSharp Settings Flattening - Technical Deep Dive

**Date:** 2025-11-13
**Focus:** How nvim-lspconfig flattens OmniSharp settings to command-line arguments
**Audience:** Developers debugging LSP configuration issues

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [The Flatten Function - Complete Technical Explanation](#the-flatten-function)
3. [The on_new_config Function - LSP Startup Hook](#the-on_new_config-function)
4. [Settings to Command-Line Transformation](#settings-transformation)
5. [Timing Diagram - When on_new_config Runs](#timing-diagram)
6. [Why RoslynExtensionsOptions Might Be Empty](#why-empty)
7. [Common Pitfalls and Solutions](#pitfalls)
8. [LSP Startup Sequence with Detailed Timing](#lsp-sequence)

---

## Executive Summary

nvim-lspconfig uses a special `on_new_config` callback function in the OmniSharp configuration that:

1. **Is called BEFORE the OmniSharp process starts** (T0.5 - initialization phase)
2. **Takes the `settings` table from your Lua config** (nested structure)
3. **Recursively flattens it** using a local `flatten()` function
4. **Converts to colon-delimited command-line arguments** (e.g., `RoslynExtensionsOptions:EnableAnalyzersSupport=true`)
5. **Appends these to the `cmd` array** before spawning the process

**Result:** When OmniSharp starts, it receives your settings as command-line arguments, not via LSP `initializationOptions`.

---

## The Flatten Function - Complete Technical Explanation

### Source Location
File: `~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
Lines: ~58-70 (within `on_new_config` function)

### Complete Source Code

```lua
local function flatten(tbl)
  local ret = {}
  for k, v in pairs(tbl) do
    if type(v) == 'table' then
      -- Recursively flatten nested tables
      for _, pair in ipairs(flatten(v)) do
        -- Prepend parent key with colon separator
        ret[#ret + 1] = k .. ':' .. pair
      end
    else
      -- Scalar values: format as key=value
      ret[#ret + 1] = k .. '=' .. vim.inspect(v)
    end
  end
  return ret
end
```

### How It Works - Step by Step

#### Step 1: Input Processing

The function receives a Lua table:
```lua
{
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = false,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
  }
}
```

#### Step 2: Iteration Loop

For each key-value pair in the table:
```lua
for k, v in pairs(tbl) do
```

- `k` = current key (e.g., `"RoslynExtensionsOptions"`)
- `v` = current value (e.g., a table with nested settings)

#### Step 3: Type Checking

**IF value is a table:**
```lua
if type(v) == 'table' then
  for _, pair in ipairs(flatten(v)) do
    ret[#ret + 1] = k .. ':' .. pair
  end
end
```

This performs **recursive flattening**:
- Calls `flatten(v)` on the nested table
- Gets back an array of formatted strings
- Prepends current key with `:` separator
- Appends to result

**ELSE (value is scalar):**
```lua
else
  ret[#ret + 1] = k .. '=' .. vim.inspect(v)
end
```

Uses `vim.inspect()` to convert values to strings:
- `true` → `"true"`
- `false` → `"false"`
- `42` → `"42"`
- Strings already quoted

#### Step 4: Return Value

Returns an array of formatted argument strings.

### Example Walkthrough

**Input:**
```lua
{
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = false,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
  }
}
```

**Iteration 1: Process `RoslynExtensionsOptions`**
- `k = "RoslynExtensionsOptions"`
- `v = {EnableAnalyzersSupport = true, EnableImportCompletion = false}`
- Type is table → recursive call

**Recursive Call on EnableAnalyzersSupport/EnableImportCompletion**
- Returns: `["EnableAnalyzersSupport=true", "EnableImportCompletion=false"]`

**Prepend parent key:**
- `"RoslynExtensionsOptions" .. ':' .. "EnableAnalyzersSupport=true"` = `"RoslynExtensionsOptions:EnableAnalyzersSupport=true"`
- `"RoslynExtensionsOptions" .. ':' .. "EnableImportCompletion=false"` = `"RoslynExtensionsOptions:EnableImportCompletion=false"`

**Iteration 2: Process `FormattingOptions`**
- Similar process yields: `"FormattingOptions:EnableEditorConfigSupport=true"`

**Final Output:**
```lua
{
  "RoslynExtensionsOptions:EnableAnalyzersSupport=true",
  "RoslynExtensionsOptions:EnableImportCompletion=false",
  "FormattingOptions:EnableEditorConfigSupport=true",
}
```

### Key Behaviors

#### Nil Values Are Skipped

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = nil,  -- This key won't appear in output
  }
}
```

**Output:**
```lua
{
  "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
  -- EnableImportCompletion NOT included
}
```

**Why?** In Lua, `nil` values are NOT included in `pairs()` iteration.

#### Handling Boolean Values

The `vim.inspect()` function converts Lua booleans to string representation:

```lua
vim.inspect(true)   -- Returns: "true"  (string)
vim.inspect(false)  -- Returns: "false" (string)
vim.inspect(42)     -- Returns: "42"    (string)
```

So the command-line argument becomes: `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

#### Arbitrary Nesting Depth

The recursive algorithm handles any nesting level:

```lua
settings = {
  RoslynExtensionsOptions = {
    InlayHints = {
      EnableForParameters = true,
    }
  }
}
```

**Process:**
1. Iterate `RoslynExtensionsOptions` → table → recurse
2. Iterate `InlayHints` → table → recurse
3. Iterate `EnableForParameters` → boolean → format as `EnableForParameters=true`
4. Backtrack: prepend `InlayHints` → `InlayHints:EnableForParameters=true`
5. Backtrack: prepend `RoslynExtensionsOptions` → `RoslynExtensionsOptions:InlayHints:EnableForParameters=true`

**Output:**
```lua
{
  "RoslynExtensionsOptions:InlayHints:EnableForParameters=true"
}
```

---

## The on_new_config Function - LSP Startup Hook

### Source Location
File: `~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
Lines: ~46-78

### Complete Source Code

```lua
on_new_config = function(new_config, _)
  -- Step 1: Copy the base cmd array (don't modify original)
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- Step 2: Append hard-coded LSP/OmniSharp arguments
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- Step 3: Flatten and append user settings
  if new_config.settings then
    vim.list_extend(new_config.cmd, flatten(new_config.settings))
  end

  -- Step 4: Disable workspace folder capabilities
  -- (OmniSharp doesn't support workspace folders)
  new_config.capabilities = vim.deepcopy(new_config.capabilities)
  new_config.capabilities.workspace.workspaceFolders = false
end
```

### Function Purpose

This callback is called by nvim-lspconfig at the INITIALIZATION phase (T0.5) to transform the configuration object before spawning the OmniSharp process.

### Step-by-Step Execution

#### Step 1: Copy Base Command

```lua
new_config.cmd = { unpack(new_config.cmd or {}) }
```

- **`unpack()`** - Converts the cmd table to multiple return values
- **Wrapped in `{}`** - Reconstructs as new table
- **Why?** Prevents modifying the original config table

**Example:**
```lua
-- Input
cmd = { 'dotnet', '/path/to/OmniSharp.dll' }

-- After unpack and repack
cmd = { 'dotnet', '/path/to/OmniSharp.dll' }  -- Same content, new table
```

#### Step 2: Append Hard-Coded Arguments

Four operations add required LSP/OmniSharp arguments:

**2a. Add `-z` (suppress console output in LSP mode)**
```lua
table.insert(new_config.cmd, '-z')
-- cmd now = { ..., '-z' }
```

**2b. Add Host PID (tells OmniSharp to exit if parent Neovim exits)**
```lua
vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
-- cmd now = { ..., '-z', '--hostPID', '12345' }
```

**2c. Add Package Restore Disable (avoid slow NuGet operations)**
```lua
table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
-- cmd now = { ..., '-z', '--hostPID', '12345', 'DotNet:enablePackageRestore=false' }
```

**2d. Add Encoding and LSP Mode**
```lua
vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
table.insert(new_config.cmd, '--languageserver')
-- cmd now = { ..., '--encoding', 'utf-8', '--languageserver' }
```

#### Step 3: Flatten and Append Settings

```lua
if new_config.settings then
  vim.list_extend(new_config.cmd, flatten(new_config.settings))
end
```

- **Checks if settings exist** - Only process if non-nil
- **Calls `flatten()`** - Converts nested table to command-line args
- **Appends to cmd** - Adds all flattened arguments

**Critical Point:** This is where your `settings` table becomes command-line arguments!

#### Step 4: Disable Workspace Folders

```lua
new_config.capabilities = vim.deepcopy(new_config.capabilities)
new_config.capabilities.workspace.workspaceFolders = false
```

- OmniSharp doesn't support LSP workspace folders feature
- This prevents Neovim from trying to use it

### Complete Example

**Input Configuration:**
```lua
{
  cmd = { 'dotnet', '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll' },
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
    }
  }
}
```

**After on_new_config Processing:**
```lua
{
  cmd = {
    -- Step 1: Original cmd
    'dotnet',
    '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',

    -- Step 2: Hard-coded arguments
    '-z',
    '--hostPID', '19758',
    'DotNet:enablePackageRestore=false',
    '--encoding', 'utf-8',
    '--languageserver',

    -- Step 3: Flattened settings
    'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
    'RoslynExtensionsOptions:EnableImportCompletion=true',
    'RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false',
    'FormattingOptions:EnableEditorConfigSupport=true',
    'FormattingOptions:OrganizeImports=true',
    'Sdk:IncludePrereleases=true',
  },
  settings = {
    -- UNCHANGED - settings table is preserved
    RoslynExtensionsOptions = { ... },
    FormattingOptions = { ... },
    Sdk = { ... }
  },
  capabilities = {
    -- Modified to disable workspace folders
    workspace = {
      workspaceFolders = false,  -- OmniSharp doesn't support this
    }
  }
}
```

---

## Settings to Command-Line Transformation

### The Transformation Pipeline

```
Lua Config File          nvim-lspconfig            OmniSharp Process
──────────────────      ──────────────            ──────────────────

init.lua
  └─ servers = {
       omnisharp = {
         settings = {    ┌─ on_new_config()
           ROS... = {    │   1. Copy cmd
             Enable... ──┼─► 2. Append hard-coded args
           }           │   3. Flatten settings
         }             │   4. Append flattened args
       }               │   5. Return modified config
     }                 │
                       └──→ Spawn Process
                             with cmd array

                               Command line args:
                               ├─ -z
                               ├─ --hostPID 12345
                               ├─ DotNet:enablePackageRestore=false
                               ├─ --encoding utf-8
                               ├─ --languageserver
                               ├─ RoslynExtensionsOptions:Enable...=true
                               └─ FormattingOptions:Enable...=true
                                    │
                                    └─► OmniSharp
                                        Parses CLI args
                                        Applies settings
                                        Loads analyzers
```

### Actual Examples

#### Example 1: Basic Analyzer Enable

**Config:**
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  }
}
```

**Command-line argument generated:**
```bash
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

**What OmniSharp receives:**
```bash
dotnet /path/to/OmniSharp.dll \
  -z \
  --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 \
  --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

**Result:** Roslyn analyzers enabled ✓

#### Example 2: Multiple Settings

**Config:**
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
  }
}
```

**Command-line arguments:**
```bash
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
FormattingOptions:EnableEditorConfigSupport=true
FormattingOptions:OrganizeImports=true
```

**Full command:**
```bash
dotnet /path/to/OmniSharp.dll \
  -z \
  --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 \
  --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
  FormattingOptions:EnableEditorConfigSupport=true \
  FormattingOptions:OrganizeImports=true
```

#### Example 3: Nil Values (Skipped)

**Config:**
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = nil,     -- Skipped
    AnalyzeOpenDocumentsOnly = false,
  }
}
```

**Command-line arguments:**
```bash
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
```

Note: `EnableImportCompletion` is NOT included because its value is `nil`.

---

## Timing Diagram - When on_new_config Runs

### Complete LSP Startup Sequence with Timing

```
USER RESTARTS NEOVIM
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ T0: Neovim starts                                             │
│     - Loads init.lua                                          │
│     - Registers LSP servers via require('lspconfig').*setup() │
│     - on_new_config callback registered (not called yet)     │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
USER OPENS C# FILE: :e UserController.cs
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ T1: LSP Attachment Decision                                   │
│     - Neovim checks: "Is this file type handled by any LSP?"  │
│     - Finds: omnisharp (cmd matches '*.cs' filetype)         │
│     - Decides: Attach LSP to this buffer                     │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ T0.5: ⭐️ on_new_config CALLED                                │
│                                                               │
│  FOR FIRST TIME FOR THIS LSP SERVER INSTANCE                │
│                                                               │
│  new_config = {                                              │
│    cmd = [user config],                                      │
│    settings = [user config],                                │
│    ...                                                        │
│  }                                                            │
│                                                               │
│  Steps:                                                       │
│  1. Copy cmd → { unpack(new_config.cmd) }                   │
│  2. Append hard-coded args (-z, --hostPID, etc.)           │
│  3. Flatten settings → RoslynExtensionsOptions:Enable...    │
│  4. Append to cmd                                            │
│  5. Modify capabilities (disable workspace folders)          │
│  6. Return modified new_config                              │
│                                                               │
│  new_config.cmd now contains ALL arguments                  │
│  READY TO SPAWN PROCESS                                     │
│                                                               │
│ ⚠️  CRITICAL: This is the ONLY time on_new_config runs!    │
│              Changes to settings after this won't apply!    │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ T1: Spawn OmniSharp Process                                   │
│                                                               │
│ vim.fn.jobstart({                                            │
│   'dotnet',                                                   │
│   '/path/to/OmniSharp.dll',                                 │
│   '-z',                                                       │
│   '--hostPID', '12345',                                      │
│   'DotNet:enablePackageRestore=false',                      │
│   '--encoding', 'utf-8',                                     │
│   '--languageserver',                                        │
│   'RoslynExtensionsOptions:EnableAnalyzersSupport=true',   │
│   'RoslynExtensionsOptions:EnableImportCompletion=true',   │
│   ...                                                         │
│ })                                                            │
│                                                               │
│ OmniSharp child process starts                               │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ T2: LSP Initialize Request (ONE-TIME)                        │
│                                                               │
│ Neovim → OmniSharp:                                          │
│ {                                                             │
│   "jsonrpc": "2.0",                                          │
│   "id": 1,                                                    │
│   "method": "initialize",                                     │
│   "params": {                                                │
│     "processId": 12345,                                       │
│     "rootUri": "file:///mnt/c/.../Backend",                │
│     "capabilities": { ... },                                 │
│     "initializationOptions": {}  ← OmniSharp ignores this   │
│   }                                                           │
│ }                                                             │
│                                                               │
│ OmniSharp parses command-line arguments from process start    │
│ Command-line args OVERRIDE any initializationOptions!       │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ T2.5: OmniSharp Loads Configuration                          │
│                                                               │
│ OmniSharp Merge Order (lowest to highest priority):          │
│ 1. Hardcoded defaults                                         │
│ 2. ~/.omnisharp/omnisharp.json (global)                     │
│ 3. ~/project/omnisharp.json (project-level)                 │
│ 4. Environment variables (OMNISHARP_RoslynExtensions...)    │
│ 5. Command-line arguments (HIGHEST - from on_new_config)   │
│                                                               │
│ RESULT: All RoslynExtensionsOptions:... args are applied!   │
│ Analyzers loaded and ready to run                           │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ T3: Initialize Response                                       │
│                                                               │
│ OmniSharp → Neovim:                                          │
│ {                                                             │
│   "jsonrpc": "2.0",                                          │
│   "id": 1,                                                    │
│   "result": {                                                │
│     "capabilities": { ... }                                  │
│   }                                                           │
│ }                                                             │
│                                                               │
│ OmniSharp is now initialized and ready for requests          │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ T5+: Runtime Phase (Dynamic Configuration via LSP)           │
│                                                               │
│ IF user changes settings in init.lua and runs :LspRestart:  │
│                                                               │
│ (1) on_new_config is called AGAIN with new config           │
│ (2) Old OmniSharp process is killed                         │
│ (3) New OmniSharp process spawned with updated command      │
│ (4) Settings are now applied!                               │
│                                                               │
│ BUT: Simply changing init.lua without :LspRestart doesn't  │
│      apply settings because on_new_config already ran!      │
└───────────────────────────────────────────────────────────────┘
```

### Key Timing Insights

| Time | Event | Process State | Settings Applied? |
|------|-------|---------------|--------------------|
| T0 | Neovim loads init.lua | Not started | No |
| T0.5 | **on_new_config called** | **Cmd array built** | **Yes - flattened to CLI** |
| T1 | OmniSharp spawned | Starting | Yes - via command-line args |
| T2 | LSP Initialize request | Initializing | Yes - CLI args override |
| T2.5 | OmniSharp loads config | Loading | Yes - applied to process |
| T3+ | Normal operation | Running | No changes unless :LspRestart |

---

## Why RoslynExtensionsOptions Might Be Empty

When you run `:LspInfo` after opening a C# file, it might show:

```
RoslynExtensionsOptions = {}
```

This appears empty even though you configured it. Here's why and how to debug it:

### Root Causes Analysis

#### Cause 1: Settings Table Not in Scope During on_new_config

**Scenario:** The `servers.omnisharp` table is defined in your config, but when `on_new_config` runs, the `servers` variable is not accessible.

**Why This Happens:**
```lua
-- In init.lua
local servers = {
  omnisharp = {
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
      }
    }
  }
}

-- Later: Mason setup
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      -- At this point, servers is in scope ✓
      local server = servers[server_name]
      require('lspconfig')[server_name].setup(server)
    end
  }
}
```

If the handler runs at module load time but `servers` is in a different scope, it might be nil.

**Debug Check:**
```lua
-- Add this to your handler
function(server_name)
  if server_name == 'omnisharp' then
    if servers.omnisharp then
      vim.notify('servers.omnisharp exists!', vim.log.levels.INFO)
    else
      vim.notify('ERROR: servers.omnisharp is nil!', vim.log.levels.ERROR)
    end
  end
  -- ... rest of handler
end
```

#### Cause 2: Settings Passed But on_new_config Not Called

**Scenario:** Your settings are defined, but `on_new_config` callback wasn't invoked.

**Why:** If OmniSharp is already running from a previous session, Neovim might reuse the existing process instead of spawning a new one.

**Solution:** Kill existing process before restarting Neovim:
```bash
pkill -f omnisharp
```

#### Cause 3: Settings in Wrong Location

**Wrong (root level):**
```lua
omnisharp = {
  enableAnalyzersSupport = true,  -- ❌ Wrong location!
}
```

**Correct (nested in settings):**
```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  -- ✓ Correct
    }
  }
}
```

The `on_new_config` function looks for `new_config.settings`, not root-level properties.

#### Cause 4: Using Deprecated Configuration

**Deprecated (old OmniSharp LSP config):**
```lua
enable_roslyn_analyzers = true,  -- ❌ Deprecated
```

**Current (as of April 2024):**
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- ✓ Current
  }
}
```

The old root-level flags are no longer processed.

### Debugging the Empty RoslynExtensionsOptions

#### Debug Check 1: Verify Settings in Config

```vim
:lua print(vim.inspect(servers.omnisharp.settings))
```

Should print your full settings table.

#### Debug Check 2: Check Active Client Configuration

```vim
:lua print(vim.inspect(vim.lsp.get_clients({ name = 'omnisharp' })[1].config.settings))
```

Shows what the LSP client is actually using.

#### Debug Check 3: Verify Process Command

```bash
ps aux | grep omnisharp | grep -v grep
```

Look for flattened settings in the command line:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

If NOT present, settings were not flattened.

#### Debug Check 4: Check LSP Log

```bash
tail -100 ~/.local/state/nvim/lsp.log | grep -i "RoslynExtensions"
```

Should show the settings being passed to OmniSharp.

### Visual Debugging: When on_new_config Runs

Add debug output to see if and when it's called:

```lua
-- In your omnisharp config in init.lua
omnisharp = {
  settings = { ... },

  -- Add temporary debug callback
  on_init = function(client)
    vim.notify('OmniSharp on_init called!', vim.log.levels.INFO)
  end,

  on_attach = function(client, bufnr)
    vim.notify('OmniSharp on_attach called!', vim.log.levels.INFO)
    -- This runs AFTER on_new_config and initialization
  end,
}
```

**Expected timeline in notifications:**
1. See `"OmniSharp on_init called!"` (after on_new_config)
2. See `"OmniSharp on_attach called!"` (after full initialization)

If you don't see these, LSP never attached.

---

## Common Pitfalls and Solutions

### Pitfall 1: Calling setup() Multiple Times

**Wrong:**
```lua
-- First call (via mason-lspconfig handler)
require('lspconfig').omnisharp.setup(config1)

-- Later: Second call (explicit)
require('lspconfig').omnisharp.setup(config2)  -- ❌ Too late! First call already registered
```

**Solution:** Let mason-lspconfig handler configure it, OR use explicit handler:
```lua
require('mason-lspconfig').setup {
  handlers = {
    omnisharp = function()
      require('lspconfig').omnisharp.setup(config)  -- ✓ Explicit, controlled call
    end
  }
}
```

### Pitfall 2: Boolean Values as Strings

**Wrong:**
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = "true",  -- ❌ String, not boolean
  }
}
```

**Correct:**
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- ✓ Boolean
  }
}
```

The `vim.inspect()` function will convert it to the string `"true"`, but semantically it's clearer to use actual booleans.

### Pitfall 3: Changing Settings Without Restarting LSP

**Doesn't work:**
```vim
" Edit init.lua to add new settings
:edit ~/.config/nvim/init.lua
" Add EnableImportCompletion = true
:w
" Back to C# file
:edit UserController.cs
" Settings not applied! on_new_config already ran
```

**Correct:**
```vim
:edit ~/.config/nvim/init.lua
" Add EnableImportCompletion = true
:w
:LspRestart  " ← REQUIRED! This calls on_new_config again
" Now settings applied
```

### Pitfall 4: Mixing Command-Line Args with Settings

**Wrong:**
```lua
omnisharp = {
  cmd = {
    'dotnet',
    '/path/to/OmniSharp.dll',
    'RoslynExtensionsOptions:EnableAnalyzersSupport=true'  -- ❌ Settings in cmd!
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  -- ❌ Duplicated in settings
    }
  }
}
```

**Correct:**
```lua
omnisharp = {
  cmd = {
    'dotnet',
    '/path/to/OmniSharp.dll',
    '-s', vim.fn.expand('/path/to/solution')  -- ✓ Only solution path in cmd
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  -- ✓ Settings in settings table
    }
  }
}
```

The `on_new_config` function will automatically flatten and append the settings.

### Pitfall 5: Expecting Dynamic Updates Without Restart

**Wrong expectation:**
```lua
-- User is editing init.lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  }
}

-- At T0.5: on_new_config already ran with old config
-- Changing the Lua file doesn't re-trigger on_new_config
```

**Correct understanding:**

`on_new_config` runs when:
1. Neovim starts (T0.5)
2. First C# file opened and LSP attaches (T0.5 per buffer)
3. `:LspRestart` is run by user (intentional restart)
4. LSP client intentionally reloads (rare)

It does NOT re-run when you edit init.lua unless you `:source` it and :LspRestart.

---

## LSP Startup Sequence with Detailed Timing

### Complete Message Flow Diagram

```
TIME  NEOVIM                                    OMNISHARP
─────────────────────────────────────────────────────────────────────────────

T0    User: :e UserController.cs
      Neovim: File opened, check LSP handlers

T0.25 Neovim: Found omnisharp handler for *.cs
      Neovim: Call on_new_config(new_config, _)

      ┌─ on_new_config executes:
      ├─ Copies cmd array
      ├─ Appends -z, --hostPID, DotNet:..., --encoding, --languageserver
      ├─ Flattens settings to command-line args
      ├─ Modifies capabilities
      └─ Returns modified config

T0.5  Neovim: vim.fn.jobstart(cmd_with_all_args)  ──→ OmniSharp process spawned
                                                      Parses command-line args
                                                      Loads analyzers from config

T1    Neovim: Send initialize request
      {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
          "processId": 12345,
          "rootUri": "file://...",
          "capabilities": {...},
          "initializationOptions": {}  ← IGNORED by OmniSharp
        }
      } ────────────────────────────────────→ OmniSharp reads command-line
                                              Merges configuration
                                              Initializes server

T2    Neovim: Wait for initialize response

                                              OmniSharp: Building response...
                                              Applying RoslynExtensionsOptions
                                              Loading project files
                                              Starting analyzer

T2.5                                          OmniSharp: Send initialize response
      {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
          "capabilities": {
            "diagnosticProvider": true,
            "definitionProvider": true,
            ...
          }
        }
      } ←─────────────────────────────────────

T3    Neovim: Send initialized notification
      {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
      } ────────────────────────────────────→ OmniSharp ready for requests

T4    Neovim: Open document (textDocument/didOpen)
      {
        "method": "textDocument/didOpen",
        "params": {
          "textDocument": {
            "uri": "file:///path/to/UserController.cs",
            "languageId": "csharp",
            "version": 1,
            "text": "..."
          }
        }
      } ────────────────────────────────────→ OmniSharp analyzes file
                                              Reports diagnostics

T4.5                                          OmniSharp: Send diagnostic
      {
        "method": "textDocument/publishDiagnostics",
        "params": {
          "uri": "file:///path/to/UserController.cs",
          "diagnostics": [
            {
              "range": {...},
              "severity": 2,
              "message": "Indentation inconsistency...",
              "code": "SA1116"  ← StyleCop warning!
            }
          ]
        }
      } ←─────────────────────────────────────

T5+   Neovim: Display warnings in buffer
      User sees red squiggles for StyleCop issues

      Neovim: Continue normal LSP communication
      - User types code → didChange → diagnostics updated
      - User asks for completion → completion/resolve
      - User hovers → hover response
      - etc.
```

### Key Observations

1. **on_new_config called at T0.25** - Before any LSP communication
2. **Command flattening happens once** - During on_new_config, never repeated
3. **Settings passed as CLI args** - Not via LSP initializationOptions
4. **initialize response shows capabilities** - Diagnostic capability present if configured
5. **diagnostics published at T4.5+** - After file analyzed with settings applied

---

## Summary: Why Settings Appear Empty and How to Fix

### The Root Issue

When you see `:LspInfo` showing:
```
RoslynExtensionsOptions = {}
```

It doesn't mean settings weren't applied - it means the settings table in the info display is empty. **But command-line arguments (where settings were actually flattened) are not shown in :LspInfo output.**

### Proof Settings Were Applied

Check the actual process:
```bash
ps aux | grep omnisharp | head -1
```

Look for:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

If present, settings ARE applied despite :LspInfo showing them as empty.

### The Real Display Issue

`:LspInfo` shows:
- Server capabilities
- Settings table as it appears in config
- Status info

But it does NOT show:
- The flattened command-line arguments
- What was actually passed to the process

### Correct Way to Verify Settings

```bash
# 1. Check running process
ps aux | grep omnisharp | grep -v grep

# 2. Should contain flattened settings
# Example output:
# ... RoslynExtensionsOptions:EnableAnalyzersSupport=true ...

# 3. If present: Settings ARE applied
# If missing: Settings were NOT flattened (debugging needed)
```

### When on_new_config Truly Doesn't Run

Scenarios where settings truly aren't applied:

1. **OmniSharp process already running from before**
   - Kill: `pkill -f omnisharp`
   - Restart Neovim

2. **Lua error in config** prevents registration
   - Check: `:messages` for errors
   - Fix syntax

3. **servers.omnisharp variable out of scope**
   - Check: `servers` defined at module level
   - Not in function-local scope

4. **Typos in setting names**
   - Must match OmniSharp expectations exactly
   - PascalCase required (not snake_case)

### Proper Debugging Flow

```lua
-- 1. Verify config loads
:lua print(vim.inspect(servers.omnisharp.settings))
-- Shows your full settings table

-- 2. Check if on_new_config processed it
:lua print(vim.inspect(vim.lsp.get_clients({name='omnisharp'})[1].cmd))
-- Should show flattened args in cmd array

-- 3. Verify process received them
:terminal
$ ps aux | grep omnisharp | grep -v grep
-- Should show RoslynExtensionsOptions:... in command line

-- 4. Check OmniSharp logs
$ tail ~/.local/state/nvim/lsp.log | grep -i RoslynExtensions
-- Should show settings applied
```

---

## References

1. **nvim-lspconfig Source**
   - File: `lua/lspconfig/server_configurations/omnisharp.lua`
   - on_new_config: Lines ~46-78
   - flatten function: Lines ~58-70

2. **OmniSharp Configuration**
   - GitHub: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration

3. **LSP Specification 3.17**
   - https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/

4. **Related Neovim LSP Docs**
   - https://neovim.io/doc/user/lsp.html

---

**Document Completed:** 2025-11-13
**Comprehensive Coverage:** on_new_config execution timing, flatten() recursive algorithm, settings transformation pipeline, debugging guides
