# Research Summary: OmniSharp + Kickstart.nvim Architecture

**Date**: 2025-11-13
**Research Question**: What is the CORRECT way to add custom LSP server (OmniSharp) configuration to kickstart.nvim?
**Status**: DEFINITIVE ANSWER FOUND ✅

---

## TL;DR - The Answer

**The kickstart.nvim architecture is CORRECT. Just add omnisharp to the `servers` table with custom `cmd` and `settings`, and the default handler will pick it up automatically.**

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/path/to/solution'),
      '-loglevel', 'Information',
    },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
      },
    },
  },
}
```

That's it. No special handler. No explicit setup after mason-lspconfig. Just the servers table.

---

## Why lua_ls Works But OmniSharp Doesn't (The Key Difference)

### lua_ls Configuration

**Works out of the box**:
```lua
lua_ls = {
  settings = {
    Lua = { completion = { callSnippet = 'Replace' } },
  },
}
```

**Why**: nvim-lspconfig has a **default cmd** for lua_ls:
- Mason installs `lua-language-server` to `~/.local/share/nvim/mason/bin/`
- nvim-lspconfig automatically finds it via PATH
- You only need to customize settings

### OmniSharp Configuration

**Fails without explicit cmd**:
```lua
omnisharp = {
  settings = { RoslynExtensionsOptions = { EnableAnalyzersSupport = true } },
}
```

**Why it fails**:
- nvim-lspconfig has **NO default cmd** for OmniSharp
- From lspconfig docs: "omnisharp-roslyn doesn't have a cmd set because nvim-lspconfig does not make assumptions about your path"
- You MUST provide `cmd = { 'dotnet', '/path/to/OmniSharp.dll' }`
- You SHOULD provide solution path: `'-s', '/path/to/solution'`

**Root cause**: OmniSharp installation paths vary widely (system-wide, Mason, manual), so lspconfig can't assume where the binary is.

---

## How the Kickstart.nvim LSP Architecture Works

### 1. The Servers Table (Declarative Configuration)

```lua
local servers = {
  -- Server with defaults
  lua_ls = {
    settings = { ... },
  },

  -- Server with custom cmd
  omnisharp = {
    cmd = { 'dotnet', '/path/to/OmniSharp.dll', ... },
    settings = { ... },
  },
}
```

**Purpose**: Centralized configuration for ALL LSP servers.

### 2. The Mason-lspconfig Default Handler

```lua
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

**What it does**:
1. For EVERY server Mason manages (including omnisharp)
2. Look up `servers[server_name]` (retrieves your config)
3. Merge capabilities (for completion, snippets, etc.)
4. Call `lspconfig[server_name].setup(server)` ONCE

**Key mechanism**: `servers[server_name]` returns the ENTIRE table, including `cmd`, `settings`, `on_attach`, etc.

### 3. The nvim-lspconfig on_new_config Function

**Source**: `nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`

```lua
on_new_config = function(new_config, _)
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- Append hard-coded arguments
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- Flatten settings into command-line arguments
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

  if new_config.settings then
    vim.list_extend(new_config.cmd, flatten(new_config.settings))
  end
end
```

**What it does**:
1. Takes your base `cmd` array
2. Appends OmniSharp-required arguments (`-z`, `--hostPID`, etc.)
3. **Flattens nested settings** into command-line format:
   - `RoslynExtensionsOptions.EnableAnalyzersSupport = true` becomes
   - `RoslynExtensionsOptions:EnableAnalyzersSupport=true` (CLI argument)

**When it runs**: Automatically when `lspconfig.omnisharp.setup()` is called.

---

## The Complete Flow

```
1. User defines servers.omnisharp table
   ↓
2. Mason-lspconfig handler runs for 'omnisharp'
   ↓
3. Handler retrieves servers.omnisharp (includes cmd + settings)
   ↓
4. Handler merges capabilities
   ↓
5. Handler calls lspconfig.omnisharp.setup(server)
   ↓
6. lspconfig's on_new_config runs (automatic)
   ↓
7. on_new_config appends -z, --hostPID, etc.
   ↓
8. on_new_config flattens settings to CLI args
   ↓
9. Final cmd executed:
   dotnet /path/to/OmniSharp.dll \
     -s /path/to/solution \
     -loglevel Information \
     -z --hostPID 12345 \
     DotNet:enablePackageRestore=false \
     --encoding utf-8 --languageserver \
     RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

---

## What Was Wrong in CLAUDE.md

### Problem 1: Conflicting Special Handler

**User had this** (WRONG):
```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      -- default handler
    end,
    omnisharp = function()
      local server = servers.omnisharp or {}
      server.cmd = {  -- ⚠️ OVERWRITES servers.omnisharp.cmd!
        vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
        '-loglevel', 'Information',
        '-z',
        '--languageserver'
      }
      require('lspconfig').omnisharp.setup(server)
    end,
  },
}
```

**Why it's wrong**:
- Retrieved `servers.omnisharp` config
- Then **REPLACED** the `cmd` field entirely
- Used Mason wrapper script instead of `dotnet + DLL`
- Removed solution path (`-s`)
- Included `-z` and `--languageserver` (duplicated by on_new_config)

### Problem 2: Lua Bytecode Cache

**Issue**: Neovim was loading cached `~/.cache/nvim/luac/init.luac` instead of updated `init.lua`.

**Fix**: `rm -rf ~/.cache/nvim/luac/`

### Problem 3: Explicit Setup After mason-lspconfig

**User tried this** (WRONG):
```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Skip omnisharp
      end
      -- ... handle other servers
    end,
  },
}

-- EXPLICIT OMNISHARP SETUP
if servers.omnisharp then
  local omnisharp_config = vim.deepcopy(servers.omnisharp)
  omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
  require('lspconfig').omnisharp.setup(omnisharp_config)
end
```

**Why it failed**:
- `lspconfig.setup()` can only be called ONCE per server
- If mason-lspconfig handler calls it, second call is ignored
- If handler skips it, explicit setup should work BUT...
- **Scope issue**: `if servers.omnisharp then` evaluated to `false`
- `servers` variable was not accessible at that point in the code

**Evidence**: User never saw the notification `🔧 OmniSharp explicitly configured...`

### Problem 4: Scope Visibility

**Root cause**: The `servers` table was defined in a different scope than where the explicit setup ran.

**Example of scope issue**:
```lua
do
  local servers = { ... }  -- Local to this block
end

-- Later in the code...
if servers.omnisharp then  -- ❌ servers is out of scope!
  -- This block never executes
end
```

---

## The CORRECT Implementation

### Option 1: Use Default Handler (RECOMMENDED)

**Just add to servers table**:
```lua
local servers = {
  lua_ls = { settings = { ... } },

  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/mnt/c/.../Backend'),
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
```

**That's it!** The default handler automatically:
1. Retrieves `servers.omnisharp`
2. Merges capabilities
3. Calls `lspconfig.omnisharp.setup()`
4. `on_new_config` flattens settings

### Option 2: Direct Setup (For Non-Mason Scenarios)

**Only if you want to skip mason-lspconfig**:
```lua
require('lspconfig').omnisharp.setup {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/.../Backend'),
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
  capabilities = require('blink.cmp').get_lsp_capabilities(),
}
```

**When to use**:
- OmniSharp not installed via Mason
- You want full control over initialization
- You're managing LSP servers manually

---

## Common Mistakes

### 1. Using Mason Wrapper Instead of dotnet + DLL

❌ **WRONG**:
```lua
cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') }
```

✅ **RIGHT**:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
}
```

### 2. Including `-z` and `--languageserver` in cmd

❌ **WRONG**:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z',  -- Don't include!
  '--languageserver'  -- Don't include!
}
```

✅ **RIGHT**:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '/path/to/solution',
  '-loglevel', 'Information',
}
```

**Why**: `on_new_config` automatically adds `-z` and `--languageserver`.

### 3. Forgetting Solution Path

❌ **WRONG**:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
}
```

✅ **RIGHT**:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', vim.fn.expand('/mnt/c/.../Backend'),
}
```

**Why**: Without `-s`, OmniSharp only loads current project, not entire solution. Breaks cross-project references.

### 4. Calling lspconfig.setup() Multiple Times

❌ **WRONG**:
```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}

-- Second setup is IGNORED!
require('lspconfig').omnisharp.setup { ... }
```

✅ **RIGHT**: Pick ONE approach (servers table OR explicit setup).

### 5. Scope Issues with servers Table

❌ **WRONG**:
```lua
do
  local servers = { ... }  -- Local to this block
end

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name]  -- ❌ Out of scope!
    end,
  },
}
```

✅ **RIGHT**:
```lua
local servers = { ... }  -- Same scope as mason-lspconfig

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name]  -- ✅ Accessible!
    end,
  },
}
```

---

## Verification

### 1. Check :LspInfo

```vim
:LspInfo
```

**Expected**:
```
cmd: { "dotnet", "/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", "/mnt/c/.../Backend", "-loglevel", "Information", "-z", "--hostPID", "12345", "DotNet:enablePackageRestore=false", "--encoding", "utf-8", "--languageserver", "RoslynExtensionsOptions:EnableAnalyzersSupport=true", ... }
```

**Key checks**:
- ✅ Starts with `"dotnet"`
- ✅ Has DLL path
- ✅ Has `-s` and solution path
- ✅ Has flattened settings: `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

### 2. Check Running Process

```bash
ps aux | grep omnisharp | grep -v grep
```

**Expected**:
```
dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /mnt/c/.../Backend \
  -loglevel Information \
  -z --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
  FormattingOptions:EnableEditorConfigSupport=true \
  FormattingOptions:OrganizeImports=true
```

### 3. Test LSP Features

```vim
grd  " Go to definition
grr  " Find references
K    " Hover documentation
gra  " Code actions
```

### 4. Check for StyleCop Warnings

Open a C# file and verify diagnostics appear (red underlines, warning messages).

---

## Research Findings Summary

### Key Insights

1. **Kickstart.nvim LSP architecture is elegant and correct**
   - Declarative servers table
   - Single default handler for all servers
   - Capabilities merged automatically

2. **OmniSharp is different from other LSPs**
   - No default cmd in nvim-lspconfig
   - Requires explicit cmd and solution path
   - Settings flattened to CLI args by on_new_config

3. **on_new_config is the magic**
   - Automatically appends required arguments
   - Flattens nested settings recursively
   - Converts Lua tables to command-line format

4. **lspconfig.setup() can only be called once**
   - Second calls are silently ignored
   - Choose either handler-based or explicit setup
   - Don't mix both approaches

5. **Scope matters**
   - servers table must be accessible when handlers run
   - Lua local variables have block scope
   - Keep servers and mason-lspconfig setup in same scope

### Why CLAUDE.md "Solution" Failed

1. **Conflicting handlers** overwrote custom cmd
2. **Lua bytecode cache** prevented config reload
3. **Scope issues** made servers.omnisharp inaccessible
4. **Multiple setup() calls** caused silent failures

### The Real Solution

**Add omnisharp to servers table. Let default handler do its job. That's it.**

---

## Code Examples from Working Configurations

### From Vi Stack Exchange

**Working pattern**:
```lua
local servers = {
  omnisharp = {},
  lua_ls = {
    settings = {
      Lua = {
        workspace = { checkThirdParty = false },
        telemetry = { enable = false },
      },
    },
  },
}

mason_lspconfig.setup_handlers {
  function(server_name)
    require('lspconfig')[server_name].setup {
      capabilities = capabilities,
      on_attach = on_attach,
      settings = servers[server_name],
      filetypes = (servers[server_name] or {}).filetypes,
    }
  end,
}
```

**Note**: This example has `omnisharp = {}` (empty), which uses lspconfig defaults. For custom cmd, you need to provide it.

### From nvim-lspconfig Documentation

**Recommended pattern**:
```lua
require('lspconfig').omnisharp.setup {
  cmd = { "dotnet", "/path/to/omnisharp/OmniSharp.dll" },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = nil,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = nil,
      EnableImportCompletion = nil,
      AnalyzeOpenDocumentsOnly = nil,
    },
  },
}
```

**Note**: `nil` values mean "use OmniSharp default" (usually `true` for analyzers).

---

## References

- [nvim-lspconfig omnisharp.lua](https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua) - Source code for on_new_config
- [kickstart.nvim issue #991](https://github.com/nvim-lua/kickstart.nvim/issues/991) - Configuring LSPs without mason-lspconfig
- [Vi Stack Exchange: OmniSharp with Mason](https://vi.stackexchange.com/questions/43830/how-to-use-omnisharp-c-lsp-with-mason-in-nvim-properly) - Working example
- [CLAUDE.md](./CLAUDE.md) - Historical debugging journey
- [KICKSTART_OMNISHARP_ARCHITECTURE_ANALYSIS.md](./KICKSTART_OMNISHARP_ARCHITECTURE_ANALYSIS.md) - Deep dive

---

## Final Answer

**Q: What is the CORRECT way to add OmniSharp to kickstart.nvim?**

**A: Add it to the `servers` table with explicit `cmd` and `settings`. The default mason-lspconfig handler will automatically configure it. No special handler needed. No explicit setup after mason-lspconfig.**

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/path/to/solution'),
      '-loglevel', 'Information',
    },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
      },
    },
  },
}
```

**That's the entire solution.**

---

**Status**: Research complete. Solution validated through code analysis, documentation review, and community examples.

**Last Updated**: 2025-11-13
