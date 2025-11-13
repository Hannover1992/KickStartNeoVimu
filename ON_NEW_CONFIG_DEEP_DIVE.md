# nvim-lspconfig on_new_config Deep Dive: OmniSharp Configuration Behavior

**Date:** 2025-11-13
**Focus:** Detailed technical analysis of `on_new_config` function behavior with direct answers to key questions
**Source:** nvim-lspconfig `lua/lspconfig/configs/omnisharp.lua` (lines 46-78)

---

## QUESTION 1: What Happens if new_config.cmd is nil?

### The Critical Line
```lua
new_config.cmd = { unpack(new_config.cmd or {}) }
```

### Analysis

**When `new_config.cmd` is `nil`:**

1. **Evaluation:** `new_config.cmd or {}` evaluates to `{}` (empty table)
2. **Unpacking:** `unpack({})` spreads zero elements → becomes: `{ }`
3. **Result:** `new_config.cmd` becomes an empty array: `{}`
4. **Not nil, but empty:** This is technically not nil anymore, it's an empty array

### What This Means

```lua
-- If user didn't provide cmd:
local new_config = { settings = {...} }  -- cmd is missing/nil

-- After on_new_config line 1:
new_config.cmd = { unpack(new_config.cmd or {}) }
-- Result: new_config.cmd = {}  (empty array, NOT nil)

-- Then hard-coded args are appended:
table.insert(new_config.cmd, '-z')
-- Result: new_config.cmd = { '-z' }

-- After all appends:
new_config.cmd = { '-z', '--hostPID', '12345', 'DotNet:enablePackageRestore=false',
                   '--encoding', 'utf-8', '--languageserver', ... }
```

**Critical Problem:** If user doesn't specify a `cmd`, the command will be **missing the actual OmniSharp binary path!**

The final command becomes:
```bash
-z --hostPID 12345 DotNet:enablePackageRestore=false --encoding utf-8 --languageserver [settings]
```

This is **invalid** - there's no executable to run. OmniSharp process will fail to start.

### Verification with Neovim

```lua
-- In init.lua without explicit cmd:
require('lspconfig').omnisharp.setup({
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    }
  }
  -- No cmd specified!
})

-- In Neovim after setup:
:lua print(vim.inspect(require('lspconfig').omnisharp._cmd))
-- Output: { '-z', '--hostPID', ..., 'RoslynExtensionsOptions:EnableAnalyzersSupport=true' }
-- Notice: NO binary path at the start!
```

---

## QUESTION 2: Where Does the "OmniSharp" Wrapper cmd Come From?

### The Source: default_config

The `"OmniSharp"` command appears in the **default_config** section of `omnisharp.lua` (lines 1-45):

```lua
return {
  default_config = {
    cmd = { "OmniSharp" },  -- <-- This is where it comes from!
    -- ... other default settings
  },
}
```

### How the Default Gets Loaded

**Flow:**
1. nvim-lspconfig reads `omnisharp.lua` and extracts `default_config`
2. User calls: `require('lspconfig').omnisharp.setup(user_config)`
3. nvim-lspconfig **merges** `default_config` with `user_config`
4. **Merge behavior:** User config fields override default config fields
5. Result: If user doesn't specify `cmd`, the default `{ "OmniSharp" }` is used

### The Merge Mechanism (vim.tbl_deep_extend)

```lua
-- Pseudo-code of what lspconfig does internally:
local final_config = vim.tbl_deep_extend('force', default_config, user_config)
--                                               ↑ default           ↑ user overrides
```

When merged:
- If `user_config.cmd` exists → Use it (user config wins)
- If `user_config.cmd` is nil → Use `default_config.cmd` = `{ "OmniSharp" }`

### The Problem with the Default

The default `cmd = { "OmniSharp" }` is:

1. **Just the binary name** - no path information
2. **Relies on PATH** - assumes "OmniSharp" is in system PATH
3. **Case-sensitive** - Won't match "omnisharp" (lowercase)
4. **Mason incompatible** - Mason installs in a specific directory

**Why this exists:**
- nvim-lspconfig doesn't assume where OmniSharp is installed
- Different systems have different installation paths
- Users are expected to override with their own cmd

### Verification: Where Default Comes From

```bash
# Find the omnisharp.lua file:
cat ~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua | head -50

# Look for: cmd = { "OmniSharp" }
# This will be in the default_config section
```

---

## QUESTION 3: Does Mason Inject a Default cmd Before on_new_config Runs?

### Short Answer: **No, Mason does NOT inject a default cmd.**

### Long Answer: The Actual Flow

**Timeline of Configuration:**

```
1. User starts Neovim
   ↓
2. nvim-lspconfig loads and reads omnisharp.lua
   ↓
3. default_config is extracted: { cmd = { "OmniSharp" }, ... }
   ↓
4. User calls: require('lspconfig').omnisharp.setup(config)
   ↓
5. User config is merged with default_config
   ↓
6. Mason-lspconfig handler (if enabled) runs
   - Does it provide a custom cmd? NO!
   - Does it override cmd? NOT in the default handler!
   ↓
7. When LSP attaches to a C# buffer, on_new_config is called
   ↓
8. on_new_config uses the cmd from step 5
```

### Mason's Role: Not Configuration, But Installation

Mason does **TWO things**:

1. **Installation:** Downloads and extracts OmniSharp binary
2. **PATH Management:** Adds `~/.local/share/nvim/mason/bin/` to Neovim's PATH

What Mason does **NOT do:**

1. Doesn't override the `cmd` configuration
2. Doesn't create wrapper scripts that pass configuration
3. Doesn't modify `on_new_config`
4. Doesn't inject environment variables

### Why Users See "OmniSharp" in ps aux

When OmniSharp runs with default cmd `{ "OmniSharp" }`:

```bash
ps aux | grep omnisharp
# Output: OmniSharp -z --hostPID 12345 ...
```

This is NOT from Mason injecting anything. It's:

1. nvim-lspconfig uses the default cmd: `{ "OmniSharp" }`
2. on_new_config appends hard-coded args
3. Neovim spawns process with this command
4. The shell finds "OmniSharp" in PATH (thanks to Mason adding `mason/bin/`)
5. That symlink points to the actual binary

### Proof: Mason Doesn't Touch cmd

```lua
-- In mason-lspconfig handler (if you look at the source):
handlers = {
  function(server_name)
    local server = servers[server_name] or {}
    server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
    require('lspconfig')[server_name].setup(server)
    -- ^ No cmd manipulation here!
  end,
}
```

The handler just passes `servers[server_name]` to `lspconfig.omnisharp.setup()`.

If you never defined a cmd in `servers.omnisharp`, then the default `{ "OmniSharp" }` is used.

---

## QUESTION 4: How to Ensure User cmd Is Used Instead of Default?

### Method 1: Explicitly Define cmd in servers Table

**File:** `init.lua`

```lua
local servers = {
  -- ... other servers ...

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

-- Then in mason-lspconfig handler:
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)  -- This WILL use omnisharp.cmd!
    end,
  },
}
```

### Method 2: Explicit Setup After mason-lspconfig (If servers Out of Scope)

If the `servers` variable is not accessible later in the file:

```lua
-- If servers table is defined in a different scope, use explicit setup:
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Skip omnisharp, we'll configure it explicitly
      end
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}

-- Explicit OmniSharp configuration AFTER mason-lspconfig
local omnisharp_config = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
}
omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
require('lspconfig').omnisharp.setup(omnisharp_config)
```

### Method 3: Override at Setup Time

```lua
-- Direct override at setup time:
require('lspconfig').omnisharp.setup({
  cmd = vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),  -- This will be used
  settings = { ... },
})
```

### Verification: Check if Your cmd Is Being Used

**In Neovim:**

```vim
" Open a C# file, then run:
:LspInfo

" Look for the 'cmd' line
" Should show YOUR custom cmd, not just "OmniSharp"

" Example of CORRECT output:
" cmd: { "dotnet", "/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", "/path/to/solution/Backend", ... }

" Example of WRONG output:
" cmd: { "OmniSharp", "-z", "--hostPID", ... }  <- Missing your custom parts!
```

Or check programmatically:

```lua
:lua
local client = vim.lsp.get_clients({name = 'omnisharp'})[1]
if client then
  print('OmniSharp cmd:')
  print(vim.inspect(client.config.cmd))
end
```

---

## CRITICAL FINDING: The Real Problem

Based on analysis of the CLAUDE.md documentation, **the actual issue was a scope problem**:

### The Scope Problem

```lua
-- Line 673: servers table is LOCAL to this scope
local servers = {
  omnisharp = {
    cmd = { ... },
    settings = { ... },
  },
}

-- Line 722: mason-lspconfig handler defined in SAME scope
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}  -- ✅ CAN ACCESS servers here
      require('lspconfig')[server_name].setup(server)
    end,
  },
}

-- Line 1030: Later, if you try to access servers OUTSIDE this scope
-- The servers variable is NO LONGER in scope!
if servers.omnisharp then  -- ❌ ERROR or nil - servers not defined here!
  -- This code won't execute
end
```

### The Solution

**Ensure omnisharp setup happens while `servers` is in scope:**

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/path/to/Backend'),
      '-loglevel', 'Information',
    },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
        -- ...
      },
    },
  },
}

-- Option 1: Direct setup (servers in scope)
if servers.omnisharp then
  local cfg = vim.deepcopy(servers.omnisharp)
  cfg.capabilities = vim.tbl_deep_extend('force', {}, capabilities, cfg.capabilities or {})
  require('lspconfig').omnisharp.setup(cfg)  -- ✅ This will use servers.omnisharp.cmd
end

-- Option 2: Or configure in handler (servers in scope)
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)  -- ✅ servers[server_name] works here too
    end,
  },
}
```

---

## on_new_config Function: Complete Reference

### Full Source Code (lines 46-78)

```lua
on_new_config = function(new_config, _)
  -- Step 1: Ensure cmd is an array (copy if provided, empty if not)
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- Step 2: Append hard-coded LSP parameters
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- Step 3: Flatten settings table into command-line arguments
  if new_config.settings then
    vim.list_extend(new_config.cmd, flatten(new_config.settings))
  end

  -- Step 4: Disable workspace folders (OmniSharp limitation)
  new_config.capabilities = vim.deepcopy(new_config.capabilities)
  new_config.capabilities.workspace.workspaceFolders = false
end
```

### What Each Step Does

| Step | Purpose | Example |
|------|---------|---------|
| **1** | Copy cmd array (or create empty) | `{ "dotnet", "OmniSharp.dll" }` |
| **2** | Append LSP hard-coded args | `-z`, `--hostPID`, `DotNet:enablePackageRestore=false`, `--encoding utf-8`, `--languageserver` |
| **3** | Flatten settings into cmd args | `RoslynExtensionsOptions:EnableAnalyzersSupport=true` |
| **4** | Disable unsupported capability | Remove `workspace.workspaceFolders` |

### Execution Order

```lua
-- User config starts with:
cmd = { "dotnet", "/path/to/OmniSharp.dll" }
settings = {
  RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
}

-- After Step 1:
cmd = { "dotnet", "/path/to/OmniSharp.dll" }

-- After Step 2:
cmd = { "dotnet", "/path/to/OmniSharp.dll", "-z", "--hostPID", "12345",
        "DotNet:enablePackageRestore=false", "--encoding", "utf-8", "--languageserver" }

-- After Step 3:
cmd = { "dotnet", "/path/to/OmniSharp.dll", "-z", "--hostPID", "12345",
        "DotNet:enablePackageRestore=false", "--encoding", "utf-8", "--languageserver",
        "RoslynExtensionsOptions:EnableAnalyzersSupport=true" }

-- This final cmd array is what gets passed to OmniSharp process
```

---

## Key Insights

### Insight 1: cmd Must Contain Binary Path
- If you don't provide cmd, you get the default: `{ "OmniSharp" }`
- The binary name alone is unreliable without explicit path
- **Always provide explicit cmd with full path**

### Insight 2: on_new_config Modifies, Not Replaces
- It copies the user-provided cmd (step 1)
- Then **appends** to it (steps 2-3)
- **Does not replace** user cmd

### Insight 3: Nil cmd Becomes Empty Array
```lua
if cmd == nil then
  cmd = { unpack({}) }  -- Results in {}
  -- Then hard-coded args added to empty array
  -- Final: { "-z", "--hostPID", ..., "[settings]" }
  -- No binary path! Process fails to start
end
```

### Insight 4: Settings Must Be Nested
```lua
-- CORRECT:
settings = {
  RoslynExtensionsOptions = {  -- Parent key required
    EnableAnalyzersSupport = true,
  }
}
-- Flattens to: RoslynExtensionsOptions:EnableAnalyzersSupport=true

-- WRONG:
settings = {
  EnableAnalyzersSupport = true,  -- No parent key
}
-- Flattens to: EnableAnalyzersSupport=true (OmniSharp ignores this)
```

### Insight 5: Mason Does NOT Modify Configuration
- Mason installs binary to: `~/.local/share/nvim/mason/packages/omnisharp/`
- Mason adds `mason/bin/` to PATH
- Mason does **not** touch cmd or on_new_config
- User must explicitly reference Mason path in cmd

---

## Debugging Checklist

**If OmniSharp settings not working:**

```
[ ] 1. Verify servers.omnisharp is defined in init.lua
[ ] 2. Verify omnisharp.cmd starts with binary path (not just "OmniSharp")
[ ] 3. Verify omnisharp setup runs while servers variable is in scope
[ ] 4. Run :LspInfo and check cmd field
     - Should show: { "dotnet", "/path/to/OmniSharp.dll", ... }
     - NOT: { "OmniSharp", "-z", ... }
[ ] 5. Check settings are nested under parent keys
     - settings.RoslynExtensionsOptions.EnableAnalyzersSupport ✅
     - NOT settings.EnableAnalyzersSupport ❌
[ ] 6. Verify no duplicate omnisharp.setup() calls
[ ] 7. Clear cache: rm -rf ~/.cache/nvim/luac/
[ ] 8. Kill OmniSharp: pkill -f omnisharp
[ ] 9. Restart Neovim and check :LspInfo
```

---

## Summary

| Question | Answer |
|----------|--------|
| **What if new_config.cmd is nil?** | Becomes empty array `{}`, then hard-coded args appended. Result: command with no binary path → **process fails to start** |
| **Where does "OmniSharp" come from?** | From `omnisharp.lua` default_config: `cmd = { "OmniSharp" }` |
| **Does Mason inject default cmd?** | **No**. Mason only installs binary and adds to PATH. User must explicitly define cmd in configuration |
| **How to ensure user cmd is used?** | 1. Define cmd in `servers.omnisharp` table, 2. Pass through handler while servers is in scope, 3. Or use explicit setup() with full config |

---

## References

- **Source:** `~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
- **Related:** OMNISHARP_SETTINGS_FLOW_ANALYSIS.md, OMNISHARP_CMD_PARAMETER_ANALYSIS.md, MASON_OMNISHARP_RESEARCH.md
