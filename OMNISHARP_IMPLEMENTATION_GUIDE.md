# OmniSharp LSP Implementation Guide - Quick Reference

**Purpose**: Practical implementation guide with copy-paste-ready code examples
**Target**: kickstart.nvim users configuring OmniSharp with Roslyn Analyzers

---

## Quick Start: 3-Step Implementation

### Step 1: Copy This into your servers table (lines ~673)

```lua
local servers = {
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
      MsBuild = {
        LoadProjectsOnDemand = nil,
      },
      Sdk = {
        IncludePrereleases = true,
      },
    },
  },

  lua_ls = {
    settings = {
      Lua = {
        completion = {
          callSnippet = 'Replace',
        },
      },
    },
  },
}
```

**Key points:**
- Replace the solution path with your actual path
- Use PascalCase for all setting names
- All Lua values (true/false/nil) are lowercase
- The `cmd` is what actually starts OmniSharp

### Step 2: Make sure mason-lspconfig looks like this (lines ~722-735)

```lua
require('mason-lspconfig').setup {
  ensure_installed = {},
  automatic_installation = false,
  handlers = {
    -- This DEFAULT handler applies to ALL servers, including omnisharp
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

**CRITICAL:**
- No special `omnisharp = function()` handler!
- Let the default handler use your `servers.omnisharp` config
- The handler calls `lspconfig.omnisharp.setup()` exactly once

### Step 3: Test It

```bash
# Clear cache
rm -rf ~/.cache/nvim/luac/

# Kill any old OmniSharp
pkill -f omnisharp

# Start Neovim
nvim
```

Open a C# file and check:
```vim
:LspInfo
```

Then verify the process:
```bash
ps aux | grep omnisharp | grep -v grep
```

Should include:
- `dotnet`
- `/mason/packages/omnisharp/libexec/OmniSharp.dll`
- `-s /path/to/your/solution`
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

---

## Understanding the Settings Flow

### What You Write (init.lua)
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  },
}
```

### What Gets Flattened (by on_new_config)
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

### What Gets Executed (actual cmd)
```bash
dotnet /path/to/OmniSharp.dll \
  -s /path/to/solution \
  -z \
  --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 \
  --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true  # <-- Your setting!
```

---

## Essential Settings Explained

### To Enable Roslyn Analyzers (StyleCop, etc.)

**Minimum required:**
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
}
```

**Full recommended:**
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,           -- Required for most features
  EnableImportCompletion = true,           -- Show unimported types in completion
  AnalyzeOpenDocumentsOnly = false,        -- Analyze all files, not just open ones
}
```

### To Use .editorconfig Rules

**Minimum:**
```lua
FormattingOptions = {
  EnableEditorConfigSupport = true,
}
```

**Recommended (includes import organization):**
```lua
FormattingOptions = {
  EnableEditorConfigSupport = true,
  OrganizeImports = true,
}
```

### To Speed Up Large Solutions

```lua
MsBuild = {
  LoadProjectsOnDemand = true,   -- Only load projects for open files
}
```

---

## Troubleshooting Quick Guide

### Problem: Analyzers Still Not Showing

**Check 1:** Is OmniSharp running with the right command?
```bash
ps aux | grep omnisharp | grep -v grep
```

Look for `RoslynExtensionsOptions:EnableAnalyzersSupport=true` in the output.

If NOT there:
- [ ] Check your cmd in servers.omnisharp (is it correct?)
- [ ] Check your settings table (nested correctly?)
- [ ] Verify no second `omnisharp.setup()` call exists
- [ ] Restart Neovim

**Check 2:** Do you have .editorconfig?

StyleCop rules are read from `.editorconfig`. Without it, no violations to show.

```bash
# Check if .editorconfig exists
ls /path/to/your/solution/.editorconfig

# If not, create a minimal one
cat > .editorconfig << 'EOF'
root = true

[*.cs]
indent_style = space
indent_size = 4
EOF
```

**Check 3:** Does your project reference StyleCop.Analyzers?

```bash
# Check the .csproj file
grep -i "StyleCop" /path/to/your/project.csproj
```

If missing, add it:
```xml
<ItemGroup>
  <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
</ItemGroup>
```

Then rebuild the solution.

### Problem: Settings Show as Empty in :LspInfo

**Cause:** Settings are flattened into cmd args, not displayed separately in :LspInfo

**Solution:** Check the process instead:
```bash
ps aux | grep omnisharp
```

Settings will appear as arguments like `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

### Problem: OmniSharp Won't Start

**Check:** Is OmniSharp installed?
```bash
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
```

If missing, install it in Neovim:
```vim
:Mason
" Find omnisharp and press 'i' to install
```

**Check:** Is dotnet available?
```bash
dotnet --version
```

If missing, install .NET SDK for your OS.

### Problem: Solution Path Not Found

**Cause:** cmd doesn't include `-s` flag or path is wrong

**Fix:** Add or correct the `-s` flag:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', vim.fn.expand('/YOUR/ACTUAL/SOLUTION/PATH'),  -- FIX THIS!
  '-loglevel', 'Information',
}
```

**Verify the path:**
```bash
# Should show .sln or .csproj files
ls /YOUR/ACTUAL/SOLUTION/PATH/
```

### Problem: Settings Appear Twice (Duplicated)

**Cause:** lspconfig.omnisharp.setup() called twice

**Fix:** Search your init.lua for all occurrences:
```bash
grep -n "omnisharp.setup" ~/.config/nvim/init.lua
```

Should only have ONE call (inside the handler). Delete any others.

---

## Complete Configuration Template

Use this as a starting point:

```lua
-- Plugin spec for nvim-lspconfig
{
  'neovim/nvim-lspconfig',
  dependencies = {
    { 'williamboman/mason.nvim', config = true },
    'williamboman/mason-lspconfig.nvim',
    'WhoIsSethDaniel/mason-tool-installer.nvim',
  },
  config = function()
    local lspconfig = require 'lspconfig'

    -- Ensure LSP capabilities are properly configured
    local capabilities = vim.lsp.protocol.make_client_capabilities()
    capabilities = require('blink.cmp').get_lsp_capabilities(capabilities)

    -- Define your server configurations
    local servers = {
      omnisharp = {
        -- ============ CMD CONFIGURATION ============
        cmd = {
          'dotnet',
          vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
          '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
          '-loglevel', 'Information',
        },

        -- ============ SETTINGS CONFIGURATION ============
        settings = {
          -- Roslyn Analyzers (StyleCop, FxCop, etc.)
          RoslynExtensionsOptions = {
            EnableAnalyzersSupport = true,
            EnableImportCompletion = true,
            AnalyzeOpenDocumentsOnly = false,
          },

          -- Code Formatting
          FormattingOptions = {
            EnableEditorConfigSupport = true,
            OrganizeImports = true,
          },

          -- MSBuild Project Loading
          MsBuild = {
            LoadProjectsOnDemand = nil,
          },

          -- SDK Options
          Sdk = {
            IncludePrereleases = true,
          },
        },

        -- ============ CUSTOM HANDLERS (OPTIONAL) ============
        handlers = {
          ['window/logMessage'] = function(err, result, ctx, config)
            if result.type <= 2 then  -- Only show errors/warnings, not info
              vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.WARN)
            end
          end,
        },

        -- ============ LIFECYCLE HOOKS (OPTIONAL) ============
        on_init = function(client, initialization_result)
          vim.notify('🔄 OmniSharp initializing...', vim.log.levels.INFO)
        end,

        on_attach = function(client, bufnr)
          vim.notify('✅ OmniSharp ready!', vim.log.levels.INFO)
        end,
      },

      -- Other servers...
      lua_ls = {
        settings = {
          Lua = {
            completion = { callSnippet = 'Replace' },
          },
        },
      },
    }

    -- Ensure tools are installed
    local ensure_installed = vim.tbl_keys(servers or {})
    vim.list_extend(ensure_installed, { 'stylua' })
    require('mason-tool-installer').setup { ensure_installed = ensure_installed }

    -- Configure LSP servers
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
  end,
}
```

---

## The on_new_config Function Explained

This runs automatically when you call `lspconfig.omnisharp.setup()`:

```lua
on_new_config = function(new_config, _)
  -- 1. Make a copy of cmd so we don't modify the original
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- 2. Append hard-coded OmniSharp arguments
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- 3. Flatten settings table into command-line arguments
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

  -- 4. Disable multi-workspace (OmniSharp limitation)
  new_config.capabilities = vim.deepcopy(new_config.capabilities)
  new_config.capabilities.workspace.workspaceFolders = false
end,
```

**This happens automatically** - you don't need to call it. It's invoked by lspconfig when you call `setup()`.

---

## Verification Checklist

After implementation, verify everything:

### In Neovim

```vim
" Show LSP status
:LspInfo

" Show all diagnostics/warnings
:lua vim.diagnostic.open_float()

" Navigate warnings
]d         " Next diagnostic
[d         " Previous diagnostic

" Code actions
<leader>ca " Show quick fixes

" Go to definition
gd         " Jump to definition
grr        " Find all references
```

### In Terminal

```bash
# Check OmniSharp is running with correct args
ps aux | grep omnisharp | grep -v grep

# Must include:
# - dotnet
# - /path/to/OmniSharp.dll
# - -s /path/to/solution
# - RoslynExtensionsOptions:EnableAnalyzersSupport=true

# Check OmniSharp logs
cat ~/.local/state/nvim/lsp.log | tail -50

# Clear cache if needed
rm -rf ~/.cache/nvim/luac/
```

---

## Settings Reference Table

### All Available RoslynExtensionsOptions

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| EnableAnalyzersSupport | bool | nil | Enable Roslyn analyzers |
| EnableImportCompletion | bool | nil | Suggest unimported types |
| AnalyzeOpenDocumentsOnly | bool | nil | Speed up by analyzing only open files |
| documentAnalysisTimeoutMs | number | 30000 | Timeout for analysis per file |
| enableDecompilationSupport | bool | true | Enable ILSpy decompilation |
| diagnosticWorkersThreadCount | number | 75% cores | Parallel analysis threads |
| locationPaths | array | nil | Custom analyzer DLL locations |

### All Available FormattingOptions

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| EnableEditorConfigSupport | bool | true | Read .editorconfig files |
| OrganizeImports | bool | nil | Sort using statements |
| TabSize | number | 4 | Tab width |
| IndentationSize | number | 4 | Indent width |
| NewLineChars | string | OS default | Line ending style |
| And 40+ more spacing/brace options | various | nil | Fine-grained formatting |

### MsBuild Options

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| LoadProjectsOnDemand | bool | nil | Load only open file projects |

### Sdk Options

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| IncludePrereleases | bool | true | Use preview SDK versions |

---

## JSON File Alternative

If you prefer `~/.omnisharp/omnisharp.json` instead of Lua config:

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,
    "organizeImports": true
  },
  "MsBuild": {
    "loadProjectsOnDemand": null
  },
  "Sdk": {
    "includePrereleases": true
  }
}
```

**Note:** Use camelCase in JSON, PascalCase in Lua!

---

## Why This Configuration Works

1. **cmd defines WHAT to run**: `dotnet /path/to/OmniSharp.dll` with solution path
2. **settings define HOW to run it**: RoslynExtensionsOptions, FormattingOptions, etc.
3. **on_new_config flattens settings**: Converts Lua tables to command-line arguments
4. **Handler calls setup() once**: Uses servers.omnisharp config to initialize
5. **OmniSharp receives everything**: All your settings as command arguments

The flow:
```
Your Lua config
    ↓
servers.omnisharp table
    ↓
mason-lspconfig handler
    ↓
lspconfig.omnisharp.setup()
    ↓
on_new_config() runs (flattens settings)
    ↓
OmniSharp executable launched with all args
```

---

## Debugging: Check What's Actually Executing

The most reliable way to verify your configuration:

```bash
# In a terminal, while Neovim is running with a C# file open:
ps aux | grep -i omnisharp | grep -v grep
```

Expected output includes:
```
dotnet /home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /path/to/solution \
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

If you don't see your settings as arguments, the cmd or settings configuration is wrong.

