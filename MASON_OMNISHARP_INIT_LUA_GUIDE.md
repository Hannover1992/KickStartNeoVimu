# Mason & OmniSharp init.lua Configuration Guide

## How to Apply the Research to Your init.lua

Based on the CLAUDE.md documentation and research findings, here's how to properly configure OmniSharp with Mason in your init.lua.

---

## Current State Analysis

### What's in init.lua

According to CLAUDE.md, your current configuration has:
1. Line 673: `local servers = { ... }`
2. Line 722-735: mason-lspconfig setup with handlers

### What's Missing

**No OmniSharp configuration!** The `servers` table doesn't have an `omnisharp` entry.

---

## Step 1: Add OmniSharp to servers Table

**Location:** Find the `local servers = {` line (around line 673)

**Add this inside the servers table:**

```lua
local servers = {
  -- ... other servers ...

  omnisharp = {
    -- Use direct DLL call (avoids wrapper script issues on Windows)
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
      '-loglevel', 'Information',
    },

    -- Settings are automatically flattened to command-line args by on_new_config
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

    -- Optional: Add handlers for better UX
    on_init = function(client, initialization_result)
      vim.notify('Loading OmniSharp projects...', vim.log.levels.INFO)
    end,

    on_attach = function(client, bufnr)
      vim.notify('OmniSharp ready!', vim.log.levels.INFO)
    end,
  },

  -- ... rest of servers ...
}
```

**Key Points:**
1. `cmd` uses direct `dotnet` + DLL path (avoids wrapper issues)
2. Solution path is absolute (not using `~` which doesn't expand in all contexts)
3. Settings will be automatically converted to command-line arguments by nvim-lspconfig's `on_new_config` function
4. `on_init` and `on_attach` callbacks are optional but provide feedback

---

## Step 2: Verify mason-lspconfig Handler

**Location:** Line 722-735

**Your current setup should look like:**

```lua
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

**This handler works correctly because:**
1. It runs for each installed server (including omnisharp if installed via Mason)
2. It looks up the server config in the `servers` table: `servers[server_name]`
3. For OmniSharp, it will find `servers.omnisharp` (added in Step 1)
4. It calls `require('lspconfig').omnisharp.setup(server)` with your full configuration
5. `setup()` is called exactly ONCE - no conflicts!

**No changes needed here!** The handler is already correctly structured.

---

## Step 3: Install OmniSharp via Mason

Open Neovim and run:

```vim
:Mason
" Find 'omnisharp'
" Press 'i' to install
" Wait for completion
```

Verify installation:

```bash
ls ~/.local/share/nvim/mason/packages/omnisharp/
# Should show: libexec/, bin/, mason-receipt.json, etc.

ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/ | grep -i omnisharp
# Should show: OmniSharp.dll
```

---

## Step 4: Test the Configuration

### Open a C# file

```bash
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs
```

### Verify in Neovim

```vim
" Check LSP status
:LspInfo

" Should show:
" • omnisharp (attached) (initialized)
"   Language ID: c# (filetype: cs)
"   cmd: { "dotnet", "/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", "/mnt/c/.../Backend", "-loglevel", "Information" }
"   settings: {
"     FormattingOptions = { ... },
"     RoslynExtensionsOptions = { ... }
"   }
```

### Check running process

```bash
ps aux | grep omnisharp | grep -v grep

# Should show full command like:
# dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
#   -s /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend \
#   -loglevel Information \
#   -z --hostPID 12345 \
#   DotNet:enablePackageRestore=false \
#   --encoding utf-8 \
#   --languageserver \
#   RoslynExtensionsOptions:EnableAnalyzersSupport=true \
#   RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
#   FormattingOptions:EnableEditorConfigSupport=true \
#   FormattingOptions:OrganizeImports=true
```

All your settings are there! ✅

### Test LSP features

```vim
" Hover documentation
K

" Go to definition
gd

" Find references
grr

" Code actions (format, quick fix)
<leader>ca

" Diagnostics
<leader>w
```

---

## Step 5: Troubleshooting

### If OmniSharp doesn't attach

**Check 1: Clear Lua bytecode cache**

```bash
rm -rf ~/.cache/nvim/luac/
```

Then restart Neovim.

**Check 2: Kill existing OmniSharp processes**

```bash
pkill -f omnisharp
```

Then open a C# file again.

**Check 3: Verify Mason installation**

```bash
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
# Should exist and be readable
```

**Check 4: Test OmniSharp directly**

```bash
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll --version
# Should show version without errors
```

**Check 5: Look at LSP log**

```vim
:LspLog
" Look for omnisharp initialization messages
" Check for error messages
```

### If settings aren't applied

**Check 1: Verify settings in :LspInfo**

```vim
:LspInfo
" Look at the 'settings:' section
" Should show RoslynExtensionsOptions and FormattingOptions
```

**Check 2: Verify in running process**

```bash
ps aux | grep omnisharp | grep -v grep
# Check if EnableAnalyzersSupport=true appears in the command
# Check if FormatOptions:EnableEditorConfigSupport=true appears
```

**Check 3: Solution path issue**

If you see `-s` but no path after it, the path expansion failed:

```lua
-- DON'T use this:
'-s', '~/path/to/solution',  -- Tilde doesn't expand!

-- DO use this:
'-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
```

**Check 4: Solution path doesn't exist**

```bash
ls /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/
# Should show .sln or .csproj files
```

---

## Configuration Template for Your Project

Here's the exact configuration for your DCSRE project:

```lua
local servers = {
  -- [other servers...]

  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
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

  -- [continue with other servers...]
}
```

Just add this to your existing `servers` table - the handler will automatically pick it up!

---

## How It All Works Together

### Step-by-Step Flow

1. **Neovim starts**
   - Loads init.lua
   - Lazy.nvim loads plugins
   - mason-lspconfig plugin loads

2. **Mason-lspconfig setup is called**
   ```lua
   require('mason-lspconfig').setup { handlers = { ... } }
   ```

3. **For each installed server (including omnisharp), handler runs**
   ```lua
   function(server_name)  -- server_name = 'omnisharp'
     local server = servers[server_name] or {}  -- Gets servers.omnisharp config
     require('lspconfig')[server_name].setup(server)  -- Calls setup once!
   end
   ```

4. **OmniSharp setup is called with your config**
   - cmd is used to start the process
   - settings are passed to on_new_config
   - on_new_config flattens them to command-line args
   - OmniSharp starts with all your settings applied

5. **When you open a C# file**
   - LSP client connects to OmniSharp
   - Your features (formatting, diagnostics, completions) work
   - You see `:LspInfo` shows omnisharp attached

### Why This Works

- **Mason** installs the binary to a known location
- **nvim-lspconfig** provides the default configuration structure
- **Your `servers.omnisharp` table** provides the cmd and settings
- **Handler** calls setup() exactly once with complete configuration
- **on_new_config** automatically handles argument flattening

No double setup calls, no conflicting configurations, clean and simple!

---

## Reference: What Each File Does

| File | Purpose | Handles omnisharp? |
|------|---------|------------------|
| **init.lua** | Your Neovim config | YES - defines servers.omnisharp |
| **mason.nvim** | Binary package manager | Installs to ~/.local/share/nvim/mason/packages/omnisharp/ |
| **nvim-lspconfig** | LSP configuration | Provides setup() function and on_new_config for omnisharp |
| **mason-lspconfig** | Mason + lspconfig integration | Runs handlers to call lspconfig setup() |

The flow is:
```
Your init.lua (defines servers.omnisharp)
    ↓
mason-lspconfig handler
    ↓
nvim-lspconfig.setup() (reads your config)
    ↓
OmniSharp process starts with your cmd and settings
```

---

## Quick Checklist

- [ ] Added omnisharp to servers table in init.lua (with cmd and settings)
- [ ] mason-lspconfig handler is correctly structured (it already is)
- [ ] Installed omnisharp via :Mason
- [ ] Verified OmniSharp.dll exists at ~/.local/share/nvim/mason/packages/omnisharp/libexec/
- [ ] Restarted Neovim
- [ ] Opened a C# file
- [ ] Ran `:LspInfo` and verified omnisharp is attached
- [ ] Checked running process with `ps aux | grep omnisharp`
- [ ] Tested features: hover (K), go to definition (gd), references (grr)

---

## Common Mistakes to Avoid

❌ **Don't call setup() twice:**
```lua
-- In handler
require('lspconfig').omnisharp.setup(servers.omnisharp)

-- Then later in config
require('lspconfig').omnisharp.setup({...})  -- IGNORED!
```

✅ **Do put everything in servers.omnisharp:**
```lua
servers.omnisharp = {
  cmd = {...},
  settings = {...},
}
-- Handler calls setup once with full config
```

---

❌ **Don't use wrapper script path on Windows with spaces:**
```lua
cmd = { vim.fn.stdpath('data') .. '/mason/bin/omnisharp' }
```

✅ **Do use direct DLL call:**
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
}
```

---

❌ **Don't use tilde for path expansion:**
```lua
'-s', '~/path/to/solution',
```

✅ **Do use absolute paths:**
```lua
'-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
```

---

## Next Steps

1. **Add omnisharp to servers table** (Step 1)
2. **Install via Mason** (Step 3)
3. **Test configuration** (Step 4)
4. **Enable StyleCop warnings** (See CLAUDE.md)
5. **Configure other tools** (Neotest, Toggleterm, etc. - already documented)

That's it! OmniSharp will be fully integrated with Mason and work correctly with all your settings.
