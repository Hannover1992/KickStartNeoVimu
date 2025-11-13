# Mason-lspconfig + OmniSharp: Comprehensive Research
## Handler Order, Execution Flow, and Working Patterns (2024-2025)

---

## CRITICAL: Order of Execution

### Timeline
```
1. Lazy.nvim loads plugins
   ↓
2. Mason installs itself (in init.lua dependencies)
   ↓
3. nvim-lspconfig is loaded
   ↓
4. mason-lspconfig is loaded
   ↓
5. mason-lspconfig.setup() is called
   ↓
6. For EACH server returned by Mason:
   → Handler function is called with server_name
   → Handler should call lspconfig[server_name].setup(config)
   ↓
7. lspconfig[server_name].setup() initializes the LSP client
   → Calls on_new_config() (if defined)
   → Starts the LSP server process
```

**Critical Point**: The handler runs DURING `mason-lspconfig.setup()` setup, not after!

---

## PATTERN 1: Default Handler (Applies to All Servers)

### Code
```lua
require('mason-lspconfig').setup {
  ensure_installed = {},
  automatic_installation = false,
  handlers = {
    -- This function runs for EVERY server that Mason manages
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

### How It Works

1. mason-lspconfig iterates through all installed LSP servers
2. For EACH server, it calls the handler function with the server name
3. Handler looks up config in `servers` table
4. Handler calls `lspconfig.omnisharp.setup(servers.omnisharp)`
5. **Automatically applies the `on_new_config()` function** from lspconfig

### Execution Flow for OmniSharp
```
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      -- server_name = 'omnisharp'
      local server = servers['omnisharp']  -- Gets full config including cmd, settings
      require('lspconfig')['omnisharp'].setup(server)
      -- This internally calls on_new_config() which:
      -- 1. Copies cmd array
      -- 2. Appends hard-coded args (-z, --hostPID, etc)
      -- 3. Flattens settings into cmd array
      -- 4. Builds final command array
    end,
  },
}
```

---

## PATTERN 2: Server-Specific Handler (OmniSharp Only)

### Why Use It

- Default handler doesn't work (settings not being passed)
- Need special behavior just for OmniSharp
- Want explicit control over setup order

### Code
```lua
require('mason-lspconfig').setup {
  handlers = {
    -- Handle most servers with default behavior
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Skip, will handle explicitly below
      end
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
    
    -- Handle OmniSharp specially
    omnisharp = function()
      local server = servers.omnisharp or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig').omnisharp.setup(server)
    end,
  },
}
```

### How It Works

1. Default handler (function) runs for all servers EXCEPT 'omnisharp'
2. Returns early when server_name == 'omnisharp' (skips setup)
3. Named handler `omnisharp = function()` is called explicitly
4. Both approaches are valid; named handler is clearer if different config needed

---

## PATTERN 3: Explicit Setup AFTER Mason-lspconfig (WRONG)

### DON'T DO THIS
```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      if server_name == 'omnisharp' then return end
      -- ... handle other servers
    end,
  },
}

-- AFTER mason-lspconfig setup completes
require('lspconfig').omnisharp.setup(servers.omnisharp)
```

### Why This Doesn't Work (Usually)

- The handler already called `setup()` for other servers
- Calling `setup()` twice on same server is unreliable
- Some internals only initialize on first call
- Settings may not be re-evaluated

### Exception: When It DOES Work

If you explicitly skip OmniSharp in the handler (return early):

```lua
handlers = {
  function(server_name)
    if server_name == 'omnisharp' then return end  -- ← MUST skip
    -- ... handle others
  end,
}

-- NOW safe to call explicitly
require('lspconfig').omnisharp.setup(servers.omnisharp)
```

---

## PATTERN 4: No Mason-lspconfig, Just lspconfig (Minimal)

### Code
```lua
-- Skip mason-lspconfig entirely
-- Just use lspconfig directly

local lspconfig = require('lspconfig')

lspconfig.omnisharp.setup({
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
    },
  },
})
```

### Pros/Cons

**Pros:**
- No mason-lspconfig complexity
- Complete control over config
- Simpler to debug

**Cons:**
- Must manually manage installation
- No automatic server detection
- Scales poorly with many servers

---

## CRITICAL: Default `cmd` Provided by Mason

### Mason's Default Command for OmniSharp

If you don't specify `cmd`, Mason defaults to:

```lua
cmd = { 'omnisharp' }  -- or sometimes 'OmniSharp' depending on version
```

This expects the binary to be in PATH. Since Mason adds `~/.local/share/nvim/mason/bin/` to PATH, it resolves to:

```bash
~/.local/share/nvim/mason/bin/omnisharp
```

Which is a symlink to:

```bash
~/.local/share/nvim/mason/packages/omnisharp/bin/OmniSharp
```

### The Problem

The default `cmd` doesn't include:
- Solution file path (`-s`)
- Log level (`-loglevel`)
- Any custom settings

### The Solution

**ALWAYS override `cmd` explicitly** to use direct DLL path:

```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '/path/to/solution',  -- ADD THIS
  '-loglevel', 'Information',  -- ADD THIS
}
```

This allows `on_new_config()` to append settings correctly.

---

## CRITICAL: Settings vs Command-Line Arguments

### How Settings Get Passed

```
User Config (init.lua)
  ↓
servers.omnisharp.settings = { RoslynExtensionsOptions = { ... } }
  ↓
Handler passes servers.omnisharp to lspconfig.omnisharp.setup()
  ↓
lspconfig calls on_new_config() function
  ↓
on_new_config() has recursive flatten() function (lines 58-70)
  ↓
flatten() converts nested tables to command-line args:
  RoslynExtensionsOptions:EnableAnalyzersSupport=true
  ↓
Args appended to cmd array
  ↓
Final command array passed to LSP client
  ↓
LSP client executes: dotnet OmniSharp.dll [all args]
```

### The Settings Structure MUST BE Nested

**CORRECT** (2-level nesting):
```lua
settings = {
  RoslynExtensionsOptions = {      -- Parent key (REQUIRED)
    EnableAnalyzersSupport = true,  -- Child key
    EnableImportCompletion = true,
  },
}
```

Flattens to:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
```

**WRONG** (flat):
```lua
settings = {
  EnableAnalyzersSupport = true,    -- No parent key (BREAKS)
  EnableImportCompletion = true,
}
```

Flattens to:
```
EnableAnalyzersSupport=true
EnableImportCompletion=true
```
OmniSharp ignores these (wrong format)!

---

## Debugging: How to Verify Settings Are Passed

### Check 1: `:LspInfo` in Neovim
```vim
:LspInfo
" Look for omnisharp section
" Check if 'settings' table shows RoslynExtensionsOptions and values
```

### Check 2: Process Command Line
```bash
ps aux | grep omnisharp | grep -v grep
# Check if command line includes:
# - dotnet
# - /path/to/OmniSharp.dll
# - RoslynExtensionsOptions:EnableAnalyzersSupport=true
# - FormattingOptions:EnableEditorConfigSupport=true
```

### Check 3: LSP Log
```vim
:LspLog
" Look for omnisharp initialization
" Check for settings in debug output
```

### Check 4: OmniSharp Logs
```bash
tail -100 ~/.local/state/nvim/lsp.log | grep -i "RoslynExtensions\|EnableAnalyzers"
```

---

## WORKING CONFIGURATION TEMPLATE (2024-2025)

### Complete Pattern That Works

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', '/path/to/Backend',  -- Solution path
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

require('mason-lspconfig').setup {
  ensure_installed = {},
  automatic_installation = false,
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

### Why This Works

1. ✅ `servers.omnisharp` has complete config (cmd, settings)
2. ✅ Default handler runs for omnisharp
3. ✅ Handler calls `lspconfig.omnisharp.setup(servers.omnisharp)`
4. ✅ Settings are present and properly nested
5. ✅ `on_new_config()` flattens settings into cmd
6. ✅ Final command includes solution path and all settings

---

## Common Mistakes

### Mistake 1: Wrong Settings Location

```lua
-- WRONG: Not nested under parent key
settings = {
  EnableAnalyzersSupport = true,    -- No parent!
}

-- CORRECT: Nested under parent key
settings = {
  RoslynExtensionsOptions = {       -- Parent key
    EnableAnalyzersSupport = true,
  },
}
```

### Mistake 2: Not Overriding cmd

```lua
-- WRONG: Uses Mason default, loses solution path
omnisharp = {
  settings = { ... },
  -- No cmd override!
}

-- CORRECT: Explicitly override cmd
omnisharp = {
  cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', '-s', '/path' },
  settings = { ... },
}
```

### Mistake 3: Calling setup() Twice

```lua
-- WRONG: setup() called twice
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name])
    end,
  },
}

-- Then later:
require('lspconfig').omnisharp.setup(servers.omnisharp)  -- ← Second call


-- CORRECT: setup() called once by handler
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name])
      -- Done! Don't call setup() again
    end,
  },
}
```

### Mistake 4: Wrong Key Names (snake_case instead of PascalCase)

```lua
-- WRONG: snake_case (old API, deprecated)
settings = {
  RoslynExtensionsOptions = {
    enable_analyzers_support = true,  -- Should be PascalCase!
  },
}

-- CORRECT: PascalCase
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,    -- Correct!
  },
}
```

---

## Key Insights for 2024-2025

1. **Handler runs DURING setup(), not after** - Don't try to setup after handler completes
2. **Settings MUST be nested 2 levels deep** - RoslynExtensionsOptions → EnableAnalyzersSupport
3. **Must override cmd with full DLL path** - Don't rely on Mason's wrapper script
4. **on_new_config() automatically flattens settings** - No manual conversion needed
5. **Named handlers (omnisharp = function()) are clearer for special cases**
6. **Default handler works fine if config is correct** - Simpler than special cases

---

## References

- Mason-lspconfig source: https://github.com/WhoIsSethDaniel/mason-lspconfig.nvim
- nvim-lspconfig omnisharp: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
- OmniSharp documentation: https://github.com/OmniSharp/omnisharp-roslyn

