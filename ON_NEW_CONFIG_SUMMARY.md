# on_new_config Function: Executive Summary

**Date:** 2025-11-13
**Status:** Complete Technical Analysis
**Documents Created:** 3 comprehensive guides

---

## Direct Answers to Your Questions

### Question 1: What happens if new_config.cmd is nil?

**Answer:** It becomes an **empty array**, NOT nil.

```lua
new_config.cmd = { unpack(new_config.cmd or {}) }
-- If cmd is nil: { unpack({}) } → {}
-- Result: Empty array, NOT nil
```

**Consequence:**
- The command becomes: `[ "-z", "--hostPID", "12345", ..., "[settings]" ]`
- **No binary to execute** → OmniSharp process fails to start
- LSP never attaches
- Error message: "Failed to attach to LSP" or "Not Running" in `:LspInfo`

**Solution:** Always provide a cmd with the binary path.

---

### Question 2: Where does the "OmniSharp" wrapper cmd come from?

**Answer:** From the **default_config** section of `omnisharp.lua`.

```lua
-- Inside omnisharp.lua (lines 1-45):
return {
  default_config = {
    cmd = { "OmniSharp" },  -- ← This is the default
    -- ... other defaults ...
  },
}
```

**How it gets used:**

1. nvim-lspconfig loads `omnisharp.lua` and extracts `default_config`
2. User calls `require('lspconfig').omnisharp.setup(user_config)`
3. **Configuration merge:** `vim.tbl_deep_extend('force', default_config, user_config)`
4. **Result:** If user doesn't provide `cmd`, the default `{ "OmniSharp" }` is used

**Why this default exists:**
- nvim-lspconfig doesn't know where OmniSharp is installed on your system
- Different systems have different paths
- Users are expected to override with their own cmd

---

### Question 3: Does Mason inject a default cmd before on_new_config runs?

**Answer: NO.** Mason does **NOT** inject a default cmd.

**What Mason DOES:**
1. Downloads OmniSharp binary from GitHub releases
2. Installs it to: `~/.local/share/nvim/mason/packages/omnisharp/`
3. Creates symlink in: `~/.local/share/nvim/mason/bin/OmniSharp`
4. Adds `mason/bin/` to Neovim's PATH

**What Mason does NOT do:**
1. Override cmd configuration ✗
2. Inject environment variables ✗
3. Create wrapper scripts with settings ✗
4. Modify on_new_config function ✗

**Why users see "OmniSharp" in ps aux:**
- User config doesn't override cmd (uses default `{ "OmniSharp" }`)
- Shell finds "OmniSharp" in PATH (thanks to Mason adding it)
- The symlink points to the actual binary

**The Timeline:**
```
Mason installs binary → Adds to PATH
        ↓
nvim-lspconfig loads (reads default_config)
        ↓
User calls omnisharp.setup() without custom cmd
        ↓
Default cmd used: { "OmniSharp" }
        ↓
on_new_config appends hard-coded args
        ↓
Shell finds "OmniSharp" in PATH (courtesy of Mason)
        ↓
Process starts ✓
```

---

### Question 4: How to ensure user cmd is used instead of default?

**Answer:** Define cmd in the configuration table and ensure it's in scope when setup runs.

**Method 1: Define in servers table (RECOMMENDED)**

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/path/to/solution/Backend'),
      '-loglevel', 'Information',
    },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
      },
    },
  },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)  -- ✅ Uses servers.omnisharp.cmd
    end,
  },
}
```

**Method 2: Explicit setup (if servers out of scope)**

```lua
local omnisharp_config = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  settings = { ... },
}
omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
require('lspconfig').omnisharp.setup(omnisharp_config)  -- ✅ Direct setup
```

**Method 3: Override at setup time**

```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  settings = { ... },
})
```

**Verification:**

```vim
" In Neovim:
:LspInfo

" Look for the cmd line. Should show your custom cmd:
" ✅ CORRECT: cmd: { "dotnet", "/path/to/OmniSharp.dll", "-s", "/path/to/Backend", ... }
" ❌ WRONG: cmd: { "OmniSharp", "-z", "--hostPID", ... }
```

---

## The Critical Issue from CLAUDE.md

The documentation revealed a **scope problem**:

```lua
local servers = {  -- ← Local scope starts here
  omnisharp = { cmd = {...}, settings = {...} }
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name]  -- ✅ servers IN SCOPE
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
                    -- ← Local scope ends here

-- This doesn't work (outside scope):
if servers.omnisharp then  -- ❌ servers NOT IN SCOPE
  require('lspconfig').omnisharp.setup(servers.omnisharp)
end
```

**Solution:** Perform omnisharp setup **while `servers` is in scope**.

---

## on_new_config Function: What It Does

### Input
```lua
new_config = {
  cmd = { "dotnet", "/path/to/OmniSharp.dll" },
  settings = {
    RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
  },
  capabilities = { ... }
}
```

### Processing (6 steps)

1. **Copy cmd array** (ensure it's not nil)
   - `new_config.cmd = { unpack(new_config.cmd or {}) }`

2. **Append "-z"** (STDIN/STDOUT mode)
   - Adds: `"-z"`

3. **Append host PID** (parent process tracking)
   - Adds: `"--hostPID"`, `"12345"`

4. **Append package restore disable** (speed up)
   - Adds: `"DotNet:enablePackageRestore=false"`

5. **Append encoding and mode** (LSP standard)
   - Adds: `"--encoding"`, `"utf-8"`, `"--languageserver"`

6. **Flatten and append settings** (if provided)
   - Converts: `RoslynExtensionsOptions = { EnableAnalyzersSupport = true }`
   - To: `"RoslynExtensionsOptions:EnableAnalyzersSupport=true"`
   - Adds to cmd

7. **Disable workspace folders** (OmniSharp limitation)
   - Sets: `capabilities.workspace.workspaceFolders = false`

### Output

```lua
new_config.cmd = {
  "dotnet",
  "/path/to/OmniSharp.dll",
  "-z",
  "--hostPID",
  "12345",
  "DotNet:enablePackageRestore=false",
  "--encoding",
  "utf-8",
  "--languageserver",
  "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
}
-- This is what gets executed as the OmniSharp process
```

---

## Key Insights

### 1. User cmd is PRESERVED
- User's cmd is copied and kept at the start
- Hard-coded args are APPENDED, not prepended
- User's settings are converted and APPENDED
- Result: User's cmd forms the base, extensions are added

### 2. nil cmd becomes EMPTY array
```lua
if cmd == nil
  then cmd = {}  -- empty, not nil
       then add hard-coded args
       then cmd = ["-z", "--hostPID", ..., "[settings]"]
       then NO BINARY TO EXECUTE → FAILURE
```

### 3. Default cmd is just a NAME
```lua
default_config.cmd = { "OmniSharp" }
-- Just the binary name, no path
-- Relies on PATH to find it
-- Unreliable without Mason
-- Should be overridden with full path
```

### 4. Mason doesn't configure, only installs
```lua
Mason's job:
  1. Download binary
  2. Extract to ~/.local/share/nvim/mason/packages/
  3. Create symlinks
  4. Add to PATH

Mason does NOT:
  1. Touch cmd configuration
  2. Inject wrapper scripts
  3. Modify on_new_config
  4. Pass settings to OmniSharp
```

### 5. Settings MUST be nested
```lua
✅ CORRECT:
settings = {
  RoslynExtensionsOptions = {  -- Parent key
    EnableAnalyzersSupport = true,  -- Child property
  }
}
-- Flattens to: "RoslynExtensionsOptions:EnableAnalyzersSupport=true"

❌ WRONG:
settings = {
  EnableAnalyzersSupport = true,  -- No parent key
}
-- Flattens to: "EnableAnalyzersSupport=true"
-- OmniSharp ignores this (expects parent key prefix)
```

---

## Complete Flow (Schematic)

```
┌─────────────────────────────────────────────────────────────┐
│  Neovim starts                                              │
│  LSP attaches to C# file                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  on_new_config(new_config) called automatically             │
│  - new_config contains user's cmd and settings             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Copy cmd                                           │
│  new_config.cmd = { unpack(new_config.cmd or {}) }        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2-5: Append hard-coded args                          │
│  "-z", "--hostPID", "PID", "DotNet:...", "--encoding",    │
│  "utf-8", "--languageserver"                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 6: Flatten settings                                   │
│  RoslynExtensionsOptions:EnableAnalyzersSupport=true       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 7: Disable workspace folders                         │
│  capabilities.workspace.workspaceFolders = false           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Final cmd array ready                                      │
│  { "dotnet", "/path/to/OmniSharp.dll", "-z",             │
│    "--hostPID", "12345", ..., "[settings]" }             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  vim.fn.jobstart(final_cmd)                                │
│  Spawns OmniSharp process with these arguments             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  OmniSharp starts with all settings applied                │
│  LSP communication begins                                   │
│  Settings propagated through LSP protocol                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Debugging Checklist

```
If OmniSharp not working properly:

[ ] 1. Verify cmd is explicitly defined (not relying on default)
[ ] 2. Verify cmd starts with binary path: { "dotnet", "/path/to/OmniSharp.dll", ... }
[ ] 3. Run :LspInfo and check cmd field
[ ] 4. Verify settings are nested: settings.RoslynExtensionsOptions.EnableAnalyzersSupport
[ ] 5. Check no duplicate omnisharp.setup() calls
[ ] 6. Verify servers variable is in scope when setup runs
[ ] 7. Clear cache: rm -rf ~/.cache/nvim/luac/
[ ] 8. Kill old processes: pkill -f omnisharp
[ ] 9. Restart Neovim
[ ] 10. Check `:LspInfo` again for correct cmd and settings
```

---

## Reference Documents Created

1. **ON_NEW_CONFIG_DEEP_DIVE.md**
   - Detailed technical analysis of all 4 questions
   - Complete reference of on_new_config function
   - Debugging checklist

2. **ON_NEW_CONFIG_FLOW_DIAGRAM.txt**
   - Visual flowcharts of all scenarios
   - Step-by-step transformations
   - ASCII diagrams

3. **ON_NEW_CONFIG_SOURCE_ANNOTATED.md**
   - Full function with line-by-line annotations
   - flatten() function explained
   - Complete flow example
   - Key implementation details

---

## Summary

| Aspect | Answer |
|--------|--------|
| **If cmd is nil?** | Becomes empty array `{}`, process fails to start |
| **Where "OmniSharp" from?** | omnisharp.lua default_config |
| **Does Mason inject cmd?** | No, Mason only installs and adds to PATH |
| **How to use custom cmd?** | Define in servers table or explicit setup() while in scope |
| **How on_new_config works?** | Copies cmd, appends hard-coded args, flattens settings, returns modified config |
| **What gets executed?** | Flattened cmd array with user's base cmd + all LSP requirements + flattened settings |

---

## Files Referenced

- **Source:** `~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua` (lines 1-78)
- **Related Docs:**
  - OMNISHARP_SETTINGS_FLOW_ANALYSIS.md
  - OMNISHARP_CMD_PARAMETER_ANALYSIS.md
  - MASON_OMNISHARP_RESEARCH.md
  - CLAUDE.md (original project documentation)

---

**Status:** ✅ Complete Analysis
**Next Step:** Review the detailed documents and apply to your init.lua configuration
