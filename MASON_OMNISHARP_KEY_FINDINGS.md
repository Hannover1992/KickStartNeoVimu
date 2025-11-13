# Mason & OmniSharp: Key Findings

## Research Summary (November 2025)

Based on research of Mason.nvim source code, GitHub issues, and nvim-lspconfig documentation.

---

## Key Question 1: Does Mason Set a Default cmd for omnisharp?

### Answer: NO

**nvim-lspconfig explicitly does NOT set a default cmd for OmniSharp.**

From the official nvim-lspconfig documentation:
> "omnisharp-roslyn doesn't have a cmd set by default because nvim-lspconfig does not make assumptions about your path."

**Implication:**
- Even though Mason installs OmniSharp, lspconfig needs YOU to specify the cmd path
- Without explicit cmd configuration, OmniSharp will not start
- **This is by design** - lspconfig can't know which version/platform you want

**What Mason Does:**
1. Downloads OmniSharp-Roslyn from GitHub
2. Extracts to `~/.local/share/nvim/mason/packages/omnisharp/`
3. Creates wrapper script: `~/.local/share/nvim/mason/bin/omnisharp`
4. Does NOT modify lspconfig defaults
5. Does NOT set any environment variables for OmniSharp

---

## Key Question 2: Mason Wrapper Script vs Direct DLL Call

### The Wrapper Script Approach (Mason Default)

```
~/.local/share/nvim/mason/bin/omnisharp (symlink)
    ↓
Calls: actual binary from packages directory
    ↓
OmniSharp starts
```

**Problems:**
- On Windows with spaces in username: **path quoting fails**
- Extra indirection makes debugging harder
- Platform-specific issues (especially on Windows)

**GitHub Issues:**
- Issue #455: "Omnisharp on Windows fails to run likely because of spaces in user name"
- Issue #701: Incomplete installation (extraction errors)
- Issue #38: "Omnisharp doesn't work on Windows" (mason-lspconfig)

### Direct DLL Call (Recommended)

```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '<solution-path>',
}
```

**Advantages:**
- Works reliably on Windows with spaces in usernames
- Direct execution, no wrapper indirection
- Clearer debugging (see full cmd in ps aux output)
- Matches official nvim-lspconfig documentation examples

**Why This Works:**
- `dotnet` runtime is typically in PATH
- DLL path is absolute (no path expansion issues)
- No wrapper script that could fail on special characters

---

## Key Question 3: Does mason-lspconfig Auto-Setup omnisharp?

### Answer: YES, but with caveats

**Mason-lspconfig has TWO mechanisms:**

### Mechanism 1: Handlers (lspconfig v1 style)

```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}
```

**How it works:**
1. For EVERY installed server, this handler runs
2. Looks up config in `servers[server_name]` table
3. Calls `lspconfig.omnisharp.setup()` with that config
4. **If `servers.omnisharp` exists and has cmd, it will be used**

**Critical Point:** The handler is smart - it uses whatever config you put in the `servers` table.

### Mechanism 2: automatic_enable (lspconfig v2 style)

```lua
require('mason-lspconfig').setup {
  automatic_enable = true,  -- Default
}
```

**What it does:**
1. Automatically calls `vim.lsp.enable(server_name)` for each installed server
2. BUT this only works if handlers are properly configured
3. If no setup is done, server won't start even with automatic_enable

**Implication:** `automatic_enable` alone is not enough - you still need proper setup!

---

## Key Question 4: How to Opt-Out of Mason's Auto-Configuration

### Option A: Skip Handler for omnisharp

```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Skip omnisharp
      end
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}

-- Then setup omnisharp manually LATER with your custom config
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', '/path/to/OmniSharp.dll' },
  -- custom settings
})
```

**Issue:** This requires setup to be called AFTER mason-lspconfig setup, and only works once.

### Option B: Use automatic_enable exclusion

```lua
require('mason-lspconfig').setup {
  automatic_enable = { exclude = { 'omnisharp' } },
  handlers = { ... },
}
```

**Effect:** Prevents automatic vim.lsp.enable() for omnisharp.

### Option C: Use the servers table correctly

```lua
local servers = {
  omnisharp = {
    cmd = { 'dotnet', '/path/to/OmniSharp.dll' },
    settings = { ... },
  },
  -- other servers...
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

**This is the cleanest approach** - the handler automatically picks up your full omnisharp config.

---

## Critical Discovery: on_new_config Function

### What nvim-lspconfig Does

The omnisharp config in nvim-lspconfig has an `on_new_config` function that:

1. **Takes your base cmd array**
2. **Appends hard-coded arguments:**
   - `-z`
   - `--hostPID <pid>`
   - `DotNet:enablePackageRestore=false`
   - `--encoding utf-8`
   - `--languageserver`

3. **Flattens your settings into command-line arguments:**
   ```
   settings = {
     RoslynExtensionsOptions = {
       EnableAnalyzersSupport = true,
     }
   }

   ↓

   RoslynExtensionsOptions:EnableAnalyzersSupport=true
   ```

### Result

Your final command becomes:

```
dotnet /path/to/OmniSharp.dll \
  -s /path/to/solution \
  -z --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 \
  --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
```

**This happens AUTOMATICALLY** - you don't need to manually convert settings to arguments!

---

## Critical Problem: Multiple setup() Calls

### The Issue

**`require('lspconfig').omnisharp.setup()` can only be called ONCE per Neovim session.**

### What Happens

```lua
-- Call 1: Handler calls setup
require('mason-lspconfig').setup {
  handlers = { function(server_name)
    require('lspconfig')[server_name].setup(servers[server_name])
  end }
}

-- Call 2: You try to override with explicit setup
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', '/custom/path/OmniSharp.dll' }
})
-- ❌ THIS IS IGNORED - Call 1's config is still used!
```

### Solution

**Ensure the handler has your correct config the first time:**

```lua
servers.omnisharp = {
  cmd = { 'dotnet', '/your/path/OmniSharp.dll', '-s', '/solution' },
  settings = { RoslynExtensionsOptions = { EnableAnalyzersSupport = true } },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

The handler picks it up automatically, setup() is called once with correct config!

---

## Verification Commands

### Check if configuration is loaded

```bash
# See actual running command
ps aux | grep omnisharp | grep -v grep

# Should show:
# dotnet /path/to/OmniSharp.dll -s /solution \
#   RoslynExtensionsOptions:EnableAnalyzersSupport=true \
#   ...
```

### Check in Neovim

```vim
" Check if attached and config loaded
:LspInfo

" Should show:
" cmd: { "dotnet", "/path/to/OmniSharp.dll", "-s", ... }
" settings: { RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... } }
```

### Clear Lua bytecode if changes don't take effect

```bash
rm -rf ~/.cache/nvim/luac/
```

---

## Summary

### What Mason Does
- Downloads and installs OmniSharp binary
- Creates wrapper script in `~/.local/share/nvim/mason/bin/`
- **Does NOT set cmd** - that's your job

### What nvim-lspconfig Does
- Provides omnisharp config structure
- **No default cmd** - you must provide it
- Has `on_new_config` that automatically flattens settings into command-line arguments

### What mason-lspconfig Does
- Provides handlers that run for each installed server
- Calls `lspconfig.omnisharp.setup()` with your `servers.omnisharp` config
- **Can only call setup() once** - gets it right the first time or has problems

### What YOU Must Do
1. **Define `servers.omnisharp` table** with:
   - `cmd` (required) - use direct DLL call via `dotnet`
   - `settings` (optional) - will be flattened to command-line args by on_new_config
2. **Let the handler call setup()** - don't call it twice
3. **Verify with `:LspInfo` and `ps aux`**

### Best Configuration

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', '<absolute-path-to-solution>',
      '-loglevel', 'Information',
    },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
        AnalyzeOpenDocumentsOnly = false,
      },
    },
  },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

This works because:
- Handler sees `servers.omnisharp` with full config
- Calls setup() exactly once with correct cmd and settings
- `on_new_config` handles flattening settings to command-line
- Everything works as designed!
