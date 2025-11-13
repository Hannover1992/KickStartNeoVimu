# Mason-lspconfig + OmniSharp Implementation Guide

## Step-by-Step: From Theory to Working Configuration

---

## STEP 1: Understand the Handler Execution Timeline

### What Happens When You Start Neovim

```
User opens Neovim
  ↓
Lazy.nvim loads plugins (in order of dependencies)
  ├─ Mason is loaded first (dependency of lspconfig)
  │  └─ Mason reads installed packages
  ├─ nvim-lspconfig is loaded
  │  └─ Registers all LSP server configurations
  └─ mason-lspconfig is loaded
     └─ Ready to bridge Mason + lspconfig
  ↓
Your init.lua runs
  ├─ Defines servers = { omnisharp = { ... }, }
  └─ Calls require('mason-lspconfig').setup { handlers = {...} }
  ↓
Mason-lspconfig setup() runs
  ├─ Gets list of installed servers from Mason
  ├─ For EACH server:
  │  ├─ server_name = 'omnisharp'
  │  ├─ Calls handler function(server_name)
  │  ├─ Handler looks up servers['omnisharp']
  │  └─ Handler calls lspconfig.omnisharp.setup(servers.omnisharp)
  │     ├─ lspconfig registers the client
  │     ├─ Calls on_new_config() function
  │     ├─ on_new_config() flattens settings
  │     └─ LSP client starts with final cmd
  │
  └─ (other servers handled similarly)
  ↓
setup() completes (handlers have already run)
  ↓
Neovim is ready
```

**KEY POINT**: Handler runs DURING setup(), not after!

---

## STEP 2: Prepare Your Configuration

### What You Need BEFORE Writing Code

1. **OmniSharp installed via Mason**
   ```bash
   # Verify in Neovim
   :Mason
   # Search for omnisharp, should show installed ✓
   ```

2. **Path to OmniSharp DLL**
   ```bash
   ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
   # Should exist and be executable
   ```

3. **Solution file path**
   ```bash
   # For DCSRE project, it's:
   /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
   # Note: Path should end WITHOUT /VDEK.DCSP.sln
   ```

4. **Decision: One handler or many?**
   - Use **default handler** if you only need basic config
   - Use **named handler** if you need special behavior for omnisharp

---

## STEP 3: Write the Configuration (Default Handler)

### Location
File: `~/.config/nvim/init.lua` (or your LSP config section)

### Code Template
```lua
-- =====================================================
-- STEP 3.1: Import required modules at top
-- =====================================================
local lspconfig = require('lspconfig')
local capabilities = require('blink.cmp').get_lsp_capabilities()  -- or your completion engine


-- =====================================================
-- STEP 3.2: Define servers table with OmniSharp
-- =====================================================
local servers = {
  omnisharp = {
    -- CRITICAL: Override the default cmd to use direct DLL path
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s',  -- Solution flag
      '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
      '-loglevel', 'Information',
    },

    -- CRITICAL: Settings MUST be nested 2 levels deep
    settings = {
      -- Parent key: RoslynExtensionsOptions
      RoslynExtensionsOptions = {
        -- Child keys: PascalCase
        EnableAnalyzersSupport = true,       -- Enables StyleCop warnings!
        EnableImportCompletion = true,
        AnalyzeOpenDocumentsOnly = false,
      },
      -- Parent key: FormattingOptions
      FormattingOptions = {
        -- Child keys: PascalCase
        EnableEditorConfigSupport = true,
        OrganizeImports = true,
      },
    },

    -- Optional: Callbacks for logging
    on_init = function(client, initialization_result)
      vim.notify('OmniSharp initializing...', vim.log.levels.INFO)
    end,
    on_attach = function(client, bufnr)
      vim.notify('OmniSharp attached!', vim.log.levels.INFO)
    end,
  },

  -- Add other servers here if needed
  lua_ls = {
    settings = {
      Lua = {
        completion = { callSnippet = 'Replace' },
      },
    },
  },
}


-- =====================================================
-- STEP 3.3: Ensure installed and get tool paths
-- =====================================================
local ensure_installed = vim.tbl_keys(servers or {})
vim.list_extend(ensure_installed, {
  'stylua',  -- Lua formatter
})
require('mason-tool-installer').setup { ensure_installed = ensure_installed }


-- =====================================================
-- STEP 3.4: Setup mason-lspconfig with DEFAULT handler
-- =====================================================
require('mason-lspconfig').setup {
  -- Don't auto-install, we manage in mason-tool-installer
  ensure_installed = {},
  automatic_installation = false,

  -- CRITICAL: The handler function
  handlers = {
    -- This function runs for EVERY server that Mason knows about
    function(server_name)
      -- Look up config for this server
      local server = servers[server_name] or {}

      -- Add capabilities (from blink.cmp or completion engine)
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})

      -- SETUP HAPPENS HERE: lspconfig.omnisharp.setup(server)
      -- This calls on_new_config() internally
      require('lspconfig')[server_name].setup(server)
    end,
  },
}

-- =====================================================
-- STEP 3.5: IMPORTANT - Do NOT call setup() again!
-- =====================================================
-- The handler already called setup() for every server
-- Including omnisharp!
-- Do NOT do this:
--   require('lspconfig').omnisharp.setup(servers.omnisharp)
-- That would call setup() twice, which breaks things!
```

### What This Does

1. **Defines servers table** with complete OmniSharp config
2. **Overrides cmd** to use direct DLL path (not Mason wrapper)
3. **Sets settings** with correct nested structure
4. **Sets up mason-lspconfig** with default handler
5. **Handler runs** during setup() and calls setup() for each server
6. **on_new_config()** is called internally, flattens settings into cmd
7. **OmniSharp starts** with all settings applied

---

## STEP 4: Verify the Configuration

### Test 1: Configuration Loads
```vim
" In Neovim, run:
:LspInfo

" Look for omnisharp section. Should show:
" cmd: { "dotnet", "/path/to/OmniSharp.dll", "-s", "/path/to/Backend", "-loglevel", "Information" }
" settings: { RoslynExtensionsOptions = {...}, FormattingOptions = {...} }
```

### Test 2: Check Process Command Line
```bash
# In terminal, run:
ps aux | grep omnisharp | grep -v grep

# Should show:
# dotnet /path/to/OmniSharp.dll -s /mnt/c/.../Backend -loglevel Information -z \
#   --hostPID 12345 DotNet:enablePackageRestore=false --encoding utf-8 --languageserver \
#   RoslynExtensionsOptions:EnableAnalyzersSupport=true \
#   RoslynExtensionsOptions:EnableImportCompletion=true \
#   FormattingOptions:EnableEditorConfigSupport=true
```

### Test 3: Open C# File
```bash
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs
```

In Neovim:
```vim
:LspInfo                    " Should show omnisharp attached
gd                          " Go to definition
grr                         " Find references
K                           " Hover documentation
:LspRestart                 " Restart if needed
```

### Test 4: Check for StyleCop Warnings
In the C# file, look for red/yellow underlines (warnings/errors).
If StyleCop warnings appear (SA1116, SA1117, etc.), configuration is working!

---

## STEP 5: Troubleshooting

### Problem: OmniSharp doesn't appear in `:LspInfo`

**Check 1: Is omnisharp installed?**
```bash
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
# Must exist
```

**Check 2: Is DLL path correct?**
```vim
:echo vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll'
# Verify path exists
```

**Check 3: Can dotnet run it?**
```bash
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll --version
# Should print version, not error
```

### Problem: OmniSharp attaches but no warnings appear

**Check 1: Settings in `:LspInfo`**
```vim
:LspInfo
" Look at omnisharp settings
" Should show RoslynExtensionsOptions: { EnableAnalyzersSupport = true }
```

**Check 2: Process shows settings?**
```bash
ps aux | grep omnisharp | grep EnableAnalyzersSupport
# Should show the setting in command line
```

**Check 3: Solution file found?**
- Check if `-s /path/to/Backend` is correct in cmd
- Check if Backend directory has .csproj or .sln files
- OmniSharp needs to find the solution

**Check 4: StyleCop installed in project?**
```bash
cd /path/to/Backend
# Check .csproj for StyleCop.Analyzers package
grep -i "stylecop" *.csproj
```

### Problem: Settings are empty in `:LspInfo`

**Most Likely Cause**: Settings not nested correctly

❌ **WRONG:**
```lua
settings = {
  EnableAnalyzersSupport = true,  -- No parent key!
}
```

✅ **CORRECT:**
```lua
settings = {
  RoslynExtensionsOptions = {     -- Parent key required
    EnableAnalyzersSupport = true,
  },
}
```

### Problem: Handler not running

**Check 1: Is `setup()` being called?**
```lua
-- Add this before mason-lspconfig.setup():
vim.notify('About to setup mason-lspconfig', vim.log.levels.INFO)

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      vim.notify('Handler called for: ' .. server_name, vim.log.levels.INFO)
      -- ...
    end,
  },
}

vim.notify('Finished setup', vim.log.levels.INFO)
```

**Check 2: Is servers table accessible?**
```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      vim.notify('servers.' .. server_name .. ' = ' .. vim.inspect(servers[server_name]), vim.log.levels.WARN)
      -- If shows nil, servers table not in scope!
      require('lspconfig')[server_name].setup(servers[server_name])
    end,
  },
}
```

---

## STEP 6: Alternative: Named Handler (If Needed)

### When to Use Named Handler

- Default handler isn't working
- Need different behavior for omnisharp vs other servers
- Want to be extra explicit

### Code
```lua
require('mason-lspconfig').setup {
  handlers = {
    -- Default handler for most servers
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Skip, will handle below
      end
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,

    -- Special handler JUST for omnisharp
    omnisharp = function()
      local server = servers.omnisharp or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig').omnisharp.setup(server)
    end,
  },
}
```

**Important**: Both handlers run during `setup()`, this is fine!

---

## STEP 7: Minimal Test Configuration

### Simplest Possible Config (for testing)

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s',
      '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
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
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}
```

This is the MINIMUM needed to work!

---

## Checklist: Before You Commit

- [ ] Settings are nested (RoslynExtensionsOptions → EnableAnalyzersSupport)
- [ ] cmd uses full DLL path (not just 'omnisharp')
- [ ] Solution path is in cmd (-s flag)
- [ ] Handler function is inside mason-lspconfig.setup()
- [ ] No setup() call AFTER mason-lspconfig.setup()
- [ ] All key names are PascalCase
- [ ] Tested with `:LspInfo`
- [ ] Tested with `ps aux | grep omnisharp`
- [ ] Tested opening C# file

---

## Summary

**The Working Pattern:**
1. Define servers table with OmniSharp config
2. Override cmd (use full DLL path)
3. Set settings (nested 2 levels)
4. Create handler function
5. Call mason-lspconfig.setup() with handler
6. Handler calls setup() for each server
7. on_new_config() flattens settings
8. Done!

**Don't Do:**
- Call setup() after mason-lspconfig.setup()
- Use flat settings
- Use snake_case keys
- Skip the cmd override
- Call setup() twice

---

## Quick Links

- Handler research: `MASON_LSPCONFIG_HANDLER_RESEARCH.md`
- Quick reference: `MASON_LSPCONFIG_QUICK_REFERENCE.md`
- OmniSharp settings guide: `OMNISHARP_LSP_SETTINGS_GUIDE.md`
- Action plan: `MASON_OMNISHARP_ACTION_PLAN.md`
