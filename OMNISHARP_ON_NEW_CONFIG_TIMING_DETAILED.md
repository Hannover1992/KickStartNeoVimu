# on_new_config - Detailed Timing Analysis

**Focus:** Exactly when on_new_config runs relative to LSP lifecycle and OmniSharp startup

---

## The Three Questions Answered

### Question 1: How does the flatten() function work?

**Answer:** Recursive table traversal with colon-delimited key concatenation

```lua
Algorithm:
  For each key-value pair in table:
    If value is table:
      Recursively flatten it
      Prepend current key with ':' separator
    Else (scalar):
      Format as key=value
    Append to result array
  Return array of formatted strings

Example:
Input:  { RoslynExtensionsOptions = { EnableAnalyzersSupport = true } }
Output: ["RoslynExtensionsOptions:EnableAnalyzersSupport=true"]

Key points:
- Handles arbitrary nesting depth
- nil values skipped (not in pairs() iteration)
- Recursive: processes one level at a time
- Prepends parent key when returning from recursion
```

**Complete Source Code:**
```lua
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
```

---

### Question 2: What format does OmniSharp expect for settings on command line?

**Answer:** Colon-delimited configuration: `ParentKey:ChildKey=value`

#### OmniSharp's Configuration Parsing

When OmniSharp starts, it parses command-line arguments looking for specific patterns:

```bash
# Format 1: Key-value pairs with colons
RoslynExtensionsOptions:EnableAnalyzersSupport=true
FormattingOptions:EnableEditorConfigSupport=true
Sdk:IncludePrereleases=true

# Format 2: Simple key-value pairs
DotNet:enablePackageRestore=false
--hostPID 12345

# Format 3: Flags
-z
--languageserver
--stdio
```

#### How OmniSharp Parses Them

```
1. Parse command-line arguments
2. For each argument:
   - If contains ':' → nested setting
     Split on ':' → ParentKey = EnableAnalyzersSupport, Value = true
   - If contains '=' → key-value
     Split on '=' → Key and Value
   - If matches flag → enable feature (-z, --languageserver)

3. Build configuration object:
   config.RoslynExtensionsOptions = {
     EnableAnalyzersSupport = true,
     ... (other settings)
   }

4. Merge with omnisharp.json and defaults
   (command-line args have highest priority)
```

#### Expected Format Details

**PascalCase Required:**
```
✓ RoslynExtensionsOptions:EnableAnalyzersSupport=true
✗ RoslynExtensionsOptions:enable_analyzers_support=true
✗ RoslynExtensionsOptions:enableAnalyzersSupport=true
```

**Boolean Values as Strings:**
```
✓ EnableAnalyzersSupport=true      (true as string)
✓ EnableAnalyzersSupport=false     (false as string)
✗ EnableAnalyzersSupport=True      (capital T doesn't work)
✗ EnableAnalyzersSupport=1         (OmniSharp expects true/false)
```

**Integer Values:**
```
✓ DocumentAnalysisTimeoutMs=30000
✓ DiagnosticWorkersThreadCount=4

Converted by vim.inspect():
30000 → "30000"
4     → "4"
```

---

### Question 3: Why might RoslynExtensionsOptions be empty in :LspInfo but present in config?

**Answer:** :LspInfo displays the settings table AS CONFIGURED, not as applied

#### Root Causes

**Cause 1: Confusing Display (Most Common)**

```
What :LspInfo shows:
  RoslynExtensionsOptions = {}

Why it shows this:
  It displays the settings table in its current form
  After on_new_config flattens to CLI args, the settings table
  itself hasn't changed - it still exists in the config

What this actually means:
  Nothing is wrong! The settings are applied as command-line args.
  :LspInfo just doesn't show the flattened form.

Verification:
  $ ps aux | grep omnisharp | grep EnableAnalyzersSupport
  If you see: RoslynExtensionsOptions:EnableAnalyzersSupport=true
  THEN: Settings ARE applied ✓
```

**Cause 2: Settings Table Actually Empty**

```lua
-- Wrong
omnisharp = {
  settings = {}  -- ← Empty! No nested tables
}

-- Right
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    }
  }
}
```

**Verification:**
```vim
:lua print(vim.inspect(servers.omnisharp.settings))
" If shows: {} → Problem confirmed
" If shows: {RoslynExtensionsOptions={...}} → Settings present
```

**Cause 3: servers.omnisharp Out of Scope**

```lua
-- Problematic: servers in local scope
local function setup_lsp()
  local servers = {
    omnisharp = {
      settings = { ... }
    }
  }
  require('lspconfig').omnisharp.setup(servers.omnisharp)
  -- servers variable dies here
end
setup_lsp()

-- Later: if on_new_config is called, servers is gone
-- Result: on_new_config can't access settings

-- Fix: servers should be module-level
local servers = {
  omnisharp = {
    settings = { ... }
  }
}
require('lspconfig').omnisharp.setup(servers.omnisharp)
-- servers stays in scope for entire module lifetime
```

**Cause 4: Multiple setup() Calls**

```lua
-- Wrong
require('lspconfig').omnisharp.setup(config1)  -- First call wins
require('lspconfig').omnisharp.setup(config2)  -- Second call ignored!

-- Right: Mason-lspconfig handler
require('mason-lspconfig').setup {
  handlers = {
    omnisharp = function()
      require('lspconfig').omnisharp.setup(config)  -- Single, controlled call
    end
  }
}
```

**Cause 5: Old Process Still Running**

```bash
# If old OmniSharp still running
ps aux | grep omnisharp | grep -v grep
# Shows: old process with old settings

# Fix: Kill before restarting
pkill -f omnisharp
# Then restart Neovim
nvim
# New process spawned with new settings
```

---

### Question 4: Does on_new_config run before or after the server starts?

**Answer:** BEFORE the server spawns, and EXACTLY ONCE per LSP instance

#### Precise Timing Diagram

```
TIME  PHASE                          STATE                  on_new_config Called?
────────────────────────────────────────────────────────────────────────────────

T0    Neovim startup
      - Load init.lua
      - Register LSP servers          Configuration loaded    NO
      - on_new_config registered      not called yet

T0.2  User opens file
      - User: :e UserController.cs
      - File type detected: csharp    Neovim detecting LSP    NO

T0.25 LSP selection
      - Check: Is there LSP for csharp?
      - Found: omnisharp              Evaluating attachment  NO

T0.5  🔴 on_new_config CALLED        ⭐️ CRITICAL MOMENT   YES!
      ├─ new_config = {
      │   cmd: [...],
      │   settings: {...}
      │ }
      │
      ├─ Step 1: Copy cmd
      ├─ Step 2: Append hard-coded args
      ├─ Step 3: Flatten settings
      ├─ Step 4: Append flattened args
      ├─ Step 5: Modify capabilities
      └─ Return modified config
                                      cmd array complete    DONE

T0.6  🟢 Process spawn
      - vim.fn.jobstart(cmd_array)
      - OmniSharp process spawned
      with ALL settings in arguments  OmniSharp starting    (Already done)

T0.7  OmniSharp initialization
      - Parse command-line args
      - Load configuration
      - Apply RoslynExtensionsOptions  OmniSharp loading     (Already done)
      - Enable analyzers
      - Start analysis engine

T1    LSP Initialize request
      - Neovim sends initialize msg
      - Include rootUri, capabilities  Handshake            (Already done)

T2    LSP Initialize response
      - OmniSharp sends capabilities
      - Server ready signal

T3    LSP Initialized notification
      - Neovim sends initialized msg
      - Server can now handle requests

T4+   Normal operation
      - Document opened
      - Diagnostics published
      - Analyzer warnings appear       Fullly operational    (Settings applied)

────────────────────────────────────────────────────────────────────────────────

KEY INSIGHT:

  ╔═══════════════════════════════════════════════════════════════╗
  ║ on_new_config runs at T0.5 (PRE-SPAWN)                       ║
  ║                                                               ║
  ║ This is BEFORE OmniSharp process even starts                 ║
  ║                                                               ║
  ║ Settings are embedded in command-line arguments              ║
  ║ NOT sent via LSP protocol after initialization               ║
  ║                                                               ║
  ║ This is why:                                                  ║
  ║ - Settings cannot be changed without :LspRestart             ║
  ║ - Changing init.lua doesn't apply new settings               ║
  ║ - Process must be re-spawned to use new settings             ║
  ╚═══════════════════════════════════════════════════════════════╝
```

#### When on_new_config Runs AGAIN

on_new_config is called again only in these scenarios:

```
Scenario 1: User runs :LspRestart
  :LspRestart
  ├─ Kill old OmniSharp process
  └─ Respawn with current config
      └─ on_new_config called again with current settings ✓

Scenario 2: Open C# file in new Neovim window
  vim file2.cs
  ├─ Different Neovim instance
  ├─ Loads init.lua
  └─ on_new_config called for new LSP instance ✓

Scenario 3: Source init.lua and :LspRestart
  :source ~/.config/nvim/init.lua  (reload config)
  :LspRestart                        (respawn LSP)
  └─ on_new_config called with reloaded config ✓

When on_new_config does NOT run again:
  ✗ Changing init.lua without :source or :LspRestart
  ✗ Opening another C# file in same window (uses same LSP)
  ✗ Just reloading the module without restarting LSP
```

---

## Complete Timing Sequence with Lua Call Stack

### Initialization Sequence

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Neovim starts: nvim UserController.cs                            │
│                                                                     │
│ Call stack:
│   nvim
│   └─ load init.lua
│      └─ require('lspconfig').omnisharp.setup(config)
│         └─ lspconfig registers omnisharp config
│            └─ on_new_config callback registered (closure)
│               ├─ 'config' captured (your init.lua config)
│               └─ Waits for LSP attachment
│
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 2. File opened: Neovim detects csharp filetype                      │
│                                                                     │
│ Event: FileType auto command triggered
│   nvim_autocommands
│   └─ Check: Is LSP available for csharp?
│      └─ Found: omnisharp
│         └─ Decide: Attach LSP
│
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 3. ⭐️ on_new_config called ⭐️                                      │
│                                                                     │
│ Call stack:
│   nvim_lsp.start_client()
│   └─ on_new_config(new_config, _)  ← YOUR CALLBACK
│      ├─ Copy cmd:
│      │  new_config.cmd = { unpack(new_config.cmd) }
│      │
│      ├─ Append hard-coded args:
│      │  table.insert(new_config.cmd, '-z')
│      │  vim.list_extend(new_config.cmd, {'--hostPID', '12345'})
│      │  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
│      │  vim.list_extend(new_config.cmd, {'--encoding', 'utf-8'})
│      │  table.insert(new_config.cmd, '--languageserver')
│      │
│      ├─ Flatten settings:
│      │  if new_config.settings then
│      │    flattened = flatten(new_config.settings)  ← FLATTEN CALLED
│      │    vim.list_extend(new_config.cmd, flattened)
│      │  end
│      │
│      │  flatten() function:
│      │  └─ Recursively walks nested tables
│      │     └─ Prepends parent keys with ':'
│      │        └─ Returns array like:
│      │           ["RoslynExtensionsOptions:EnableAnalyzersSupport=true", ...]
│      │
│      ├─ Modify capabilities:
│      │  new_config.capabilities = vim.deepcopy(new_config.capabilities)
│      │  new_config.capabilities.workspace.workspaceFolders = false
│      │
│      └─ Return modified new_config
│
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 4. Process spawning with complete command line                      │
│                                                                     │
│ vim.fn.jobstart(new_config.cmd)
│ └─ Spawn: dotnet /path/to/OmniSharp.dll -z --hostPID 12345 ... ┐
│                                                                  │
│    ┌─────────────────────────────────────────────────────────────┘
│    │
│    └─► OmniSharp child process
│        ├─ Parse command-line arguments
│        ├─ Load default config
│        ├─ Load omnisharp.json (if exists)
│        ├─ Apply command-line overrides (HIGHEST PRIORITY)
│        │  ├─ RoslynExtensionsOptions:EnableAnalyzersSupport=true
│        │  ├─ FormattingOptions:EnableEditorConfigSupport=true
│        │  └─ ... other settings
│        ├─ Initialize Roslyn analyzers
│        └─ Ready for LSP communication
│
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 5. LSP handshake                                                    │
│                                                                     │
│ Neovim ────────────────────────► OmniSharp
│         initialize request (JSON-RPC 2.0)
│         {
│           id: 1,
│           method: "initialize",
│           params: {
│             processId: 12345,
│             rootUri: "file://...",
│             capabilities: {...},
│             initializationOptions: {}  ← IGNORED
│           }
│         }
│
│ Neovim ◄────────────────────────── OmniSharp
│         initialize response
│         {
│           id: 1,
│           result: { capabilities: {...} }
│         }
│
│ Neovim ────────────────────────► OmniSharp
│         initialized notification (no response)
│
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 6. Server ready - diagnostics published                            │
│                                                                     │
│ Neovim ◄────────────────────────── OmniSharp
│         textDocument/didOpen
│         ↓
│         textDocument/publishDiagnostics
│         ├─ Analyzer warnings visible ✓
│         ├─ StyleCop warnings showing ✓
│         └─ Settings applied ✓
│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Settings Persistence and Immutability

### Why Settings Can't Change Without Restart

```
The critical fact:

on_new_config runs ONCE per LSP instance
  └─ Settings flattened to command-line arguments
     └─ Arguments passed to process spawn
        └─ Process reads arguments and loads config
           └─ Process never re-reads command line
              └─ Changes to init.lua don't matter
                 └─ Settings are frozen until process restarts
```

### Example Timeline

```
User Scenario:

T0:   Open Neovim, edit init.lua:
      settings = {
        RoslynExtensionsOptions = {
          EnableAnalyzersSupport = true,
        }
      }

T0.5: on_new_config called
      └─ Flattens to: RoslynExtensionsOptions:EnableAnalyzersSupport=true
      └─ Spawns process with this setting ✓

T1:   Process running with analyzer support ✓

T10:  User edits init.lua:
      settings = {
        RoslynExtensionsOptions = {
          EnableAnalyzersSupport = false,  ← Changed!
        }
      }

T11:  User saves init.lua
      on_new_config does NOT run ✗
      Settings still: EnableAnalyzersSupport=true ✗
      Process doesn't reload command line ✗

T12:  User remembers: need to restart LSP!
      :LspRestart
      on_new_config called AGAIN ✓
      └─ Flattens to: RoslynExtensionsOptions:EnableAnalyzersSupport=false
      └─ Spawns NEW process with new setting ✓

T13:  New process running with analyzer support disabled ✓
```

---

## Summary: on_new_config Timing

| Aspect | Answer |
|--------|--------|
| **When does it run?** | T0.5 - Before OmniSharp process spawns, on LSP attachment to first C# buffer |
| **How many times per session?** | Once per LSP instance (usually once per Neovim window) |
| **What does it do?** | Flattens settings table to command-line arguments |
| **Can settings change after?** | No - they're embedded in process command line |
| **How to apply new settings?** | `:LspRestart` (kills and respawns with new settings) |
| **Is it called before initialize?** | Yes - before ANY LSP communication |
| **Are settings in initializationOptions?** | No - passed as command-line arguments instead |
| **Is on_new_config in LSP spec?** | No - nvim-lspconfig extension specific to Neovim |

---

## Verification - Prove Settings Were Applied

### One-Liner Check

```bash
ps aux | grep omnisharp | grep -v grep | grep -o "RoslynExtensionsOptions:[^[:space:]]*"
# If shows: RoslynExtensionsOptions:EnableAnalyzersSupport=true
# Then: Settings ARE applied ✓
```

### Complete Verification Script

```bash
#!/bin/bash
echo "Checking OmniSharp Settings Application"
echo "========================================"
echo

echo "1. Is OmniSharp running?"
if ps aux | grep -q "[o]mnisharp"; then
    echo "   ✓ OmniSharp process found"
else
    echo "   ✗ OmniSharp not running"
    echo "   → Open a C# file in Neovim to start it"
    exit 1
fi
echo

echo "2. Check command line arguments:"
OMNISHARP_CMD=$(ps aux | grep "[o]mnisharp" | head -1)
echo "   Command: $OMNISHARP_CMD"
echo

echo "3. Look for flattened settings:"
if echo "$OMNISHARP_CMD" | grep -q "RoslynExtensionsOptions:"; then
    echo "   ✓ Settings flattened to command-line"
    echo "   Settings found:"
    echo "$OMNISHARP_CMD" | grep -o "RoslynExtensionsOptions:[^[:space:]]*" | sed 's/^/      /'
else
    echo "   ✗ No flattened settings found"
    echo "   → Check if settings table is defined"
    echo "   → Check if on_new_config was called"
fi
echo

echo "4. Check if analyzer support enabled:"
if echo "$OMNISHARP_CMD" | grep -q "EnableAnalyzersSupport=true"; then
    echo "   ✓ Roslyn analyzers ENABLED"
else
    echo "   ✗ Roslyn analyzers not visible"
fi
```

---

**Analysis Complete:** on_new_config timing fully documented with technical precision.
