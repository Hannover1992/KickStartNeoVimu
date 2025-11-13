# OmniSharp LSP with Roslyn Analyzers - Comprehensive Research

**Last Updated**: November 13, 2025
**Research Focus**: How to properly configure OmniSharp LSP with Roslyn Analyzers in kickstart.nvim
**Status**: Complete investigation with source code analysis

## Executive Summary

OmniSharp LSP configuration with Roslyn Analyzers requires careful coordination between:
1. The `cmd` array (how to start OmniSharp)
2. The `settings` table (configuration options)
3. The `on_new_config` function in nvim-lspconfig (which flattens settings to command-line arguments)
4. Mason-lspconfig handlers (which call `lspconfig.setup()`)

The most common issues stem from:
- Calling `lspconfig.setup()` multiple times (only the first call takes effect)
- Incorrect cmd format (needs to be `{ "dotnet", "/path/to/OmniSharp.dll", "-s", "/path/to/solution", ... }`)
- Settings not being flattened into command-line arguments
- Configuration override by mason-lspconfig default handlers

---

## Part 1: The on_new_config Function - Heart of the System

### What is on_new_config?

The `on_new_config` function in `/usr/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua` is responsible for transforming your Lua configuration into OmniSharp command-line arguments.

**Source Code** (lines 46-78 in omnisharp.lua):
```lua
on_new_config = function(new_config, _)
  -- Get the initially configured value of `cmd`
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- Append hard-coded command arguments
  table.insert(new_config.cmd, '-z') -- https://github.com/OmniSharp/omnisharp-vscode/pull/4300
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- Append configuration-dependent command arguments
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

  -- Disable the handling of multiple workspaces in a single instance
  new_config.capabilities = vim.deepcopy(new_config.capabilities)
  new_config.capabilities.workspace.workspaceFolders = false -- https://github.com/OmniSharp/omnisharp-roslyn/issues/909
end,
```

### How It Works - Step by Step

**Step 1: Copy the cmd array**
```lua
new_config.cmd = { unpack(new_config.cmd or {}) }
```
This creates a fresh copy of your `cmd` table to avoid modifying the original.

**Step 2: Append hard-coded arguments**
The function ALWAYS adds these arguments:
- `-z` (from OmniSharp-VSCode PR #4300, prevents some issues)
- `--hostPID <pid>` (tells OmniSharp about its parent process)
- `DotNet:enablePackageRestore=false` (prevents automatic NuGet restore)
- `--encoding utf-8` (character encoding)
- `--languageserver` (tells OmniSharp we're using it as an LSP)

**Step 3: Flatten the settings table**
This is the CRITICAL part. The `flatten()` function recursively converts nested Lua tables into command-line arguments:

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
  },
}
```

Gets transformed into:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
FormattingOptions:EnableEditorConfigSupport=true
```

And appended to the cmd array!

**Step 4: Disable multi-workspace handling**
Sets `capabilities.workspace.workspaceFolders = false` to work around OmniSharp issue #909.

### Critical Insight: When Does on_new_config Run?

The `on_new_config` function runs **automatically** when you call `require('lspconfig').omnisharp.setup(config)`.

**It is NOT a separate function you call** - it's a callback that lspconfig invokes.

---

## Part 2: The cmd Configuration

### What cmd Should Look Like

The `cmd` must be an array starting with how to invoke OmniSharp:

**Option 1: Direct dotnet call (RECOMMENDED)**
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', vim.fn.expand('/path/to/solution/directory'),
  '-loglevel', 'Information',
}
```

**Option 2: Using the wrapper script**
```lua
cmd = {
  vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
  '-s', vim.fn.expand('/path/to/solution/directory'),
}
```

**Option 3: Full path to OmniSharp executable**
```lua
cmd = {
  vim.fn.expand('~/.omnisharp/omnisharp'),
  '-s', vim.fn.expand('/path/to/solution/directory'),
}
```

### Why Specify -s (Solution Path)?

The `-s` flag tells OmniSharp which solution to load:
- Without it: OmniSharp searches parent directories for `*.sln` or `*.csproj`
- With it: OmniSharp loads the solution immediately
- This can significantly speed up initialization

### What Happens After on_new_config Runs

If you start with:
```lua
cmd = {
  'dotnet',
  '/path/to/OmniSharp.dll',
  '-s', '/path/to/solution',
  '-loglevel', 'Information',
}
```

After `on_new_config`, it becomes:
```lua
cmd = {
  'dotnet',
  '/path/to/OmniSharp.dll',
  '-s', '/path/to/solution',
  '-loglevel', 'Information',
  '-z',
  '--hostPID', '12345',
  'DotNet:enablePackageRestore=false',
  '--encoding', 'utf-8',
  '--languageserver',
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  'RoslynExtensionsOptions:EnableImportCompletion=true',
  'RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false',
  'FormattingOptions:EnableEditorConfigSupport=true',
  'FormattingOptions:OrganizeImports=true',
}
```

This is what actually gets executed!

---

## Part 3: Settings Configuration

### Available Settings

From the OmniSharp Configuration Options wiki:

#### RoslynExtensionsOptions
These control analyzer behavior:

| Setting | Type | Default | Effect |
|---------|------|---------|--------|
| `EnableAnalyzersSupport` | boolean | `nil` | Enable/disable Roslyn analyzers (required for most features) |
| `EnableImportCompletion` | boolean | `nil` | Show unimported types in completion |
| `AnalyzeOpenDocumentsOnly` | boolean | `nil` | Only analyze currently open files (faster, less complete) |
| `documentAnalysisTimeoutMs` | number | 30000 | Analysis timeout per file |
| `enableDecompilationSupport` | boolean | true | Enable ILSpy decompilation |
| `diagnosticWorkersThreadCount` | number | 75% of cores | Parallel analysis threads |
| `locationPaths` | array | nil | Custom analyzer/refactoring DLL locations |

#### FormattingOptions
These control code formatting:

| Setting | Type | Default | Effect |
|---------|------|---------|--------|
| `EnableEditorConfigSupport` | boolean | true | Read `.editorconfig` files |
| `OrganizeImports` | boolean | nil | Sort using statements |
| `TabSize` | number | 4 | Spaces per tab |
| `IndentationSize` | number | 4 | Indentation width |
| Many spacing/brace options | various | nil | Fine-grained formatting control |

#### MsBuild
| Setting | Type | Default | Effect |
|---------|------|---------|--------|
| `LoadProjectsOnDemand` | boolean | nil | Only load open files' projects (faster for large solutions) |

#### Sdk
| Setting | Type | Default | Effect |
|---------|------|---------|--------|
| `IncludePrereleases` | boolean | true | Include preview SDK versions |

### Lua Table Syntax (PascalCase)

In nvim-lspconfig Lua configuration, use PascalCase:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,      -- PascalCase!
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,   -- PascalCase!
    OrganizeImports = true,
  },
}
```

### JSON File Syntax (camelCase)

If using `~/.omnisharp/omnisharp.json`, use camelCase:
```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,     -- camelCase!
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,  -- camelCase!
    "organizeImports": true
  }
}
```

### Why nil vs true

In nvim-lspconfig, `nil` means "don't set this, use OmniSharp's default". Explicitly setting to `true` or `false` forces the value.

**Default Config** (from omnisharp.lua):
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = nil,        -- nil = use OmniSharp's internal default
  EnableImportCompletion = nil,
  AnalyzeOpenDocumentsOnly = nil,
}
```

---

## Part 4: Mason-lspconfig Handler Interaction

### How Handlers Work

When you do:
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

The handler function is called **for each installed LSP server**. For OmniSharp, it:
1. Gets the config from `servers['omnisharp']`
2. Merges capabilities
3. Calls `require('lspconfig').omnisharp.setup(server)` with that config

### Critical Issue: Only First Setup Takes Effect

**This is the KEY finding from the CLAUDE.md documentation:**

You can only call `lspconfig.omnisharp.setup()` ONCE per session. If you call it twice:
1. First call: Registers the config, on_new_config runs, server starts with that config
2. Second call: Silently ignored! lspconfig sees it's already been set up

### The Common Mistake

Configuration that breaks:
```lua
-- Define servers table
local servers = {
  omnisharp = { cmd = {...}, settings = {...} },
}

-- Mason-lspconfig calls lspconfig.omnisharp.setup() - FIRST CALL
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      require('lspconfig')[server_name].setup(server)  -- First call for omnisharp
    end,
  },
}

-- Then you try to configure it again - SECOND CALL
require('lspconfig').omnisharp.setup({
  cmd = {...},  -- THIS IS IGNORED!
  settings = {...},  -- THIS IS IGNORED!
})
```

The second setup call does nothing!

### The Solution

Let the handler do the setup. Your `servers` table configuration is used by the handler:

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
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)  -- Uses servers.omnisharp config above
    end,
  },
}
-- No second setup() call!
```

The handler will:
1. Get `servers['omnisharp']` config
2. Call `lspconfig.omnisharp.setup()` with that full config
3. `on_new_config` runs and flattens your settings into cmd arguments
4. OmniSharp starts with all your configuration

---

## Part 5: Known Issues and Gotchas

### Issue 1: Mason Setup Called Twice

From GitHub issue `kickstart.nvim#1297`:

**Problem**: Mason is configured as a dependency of nvim-lspconfig AND explicitly set up separately, causing conflicts.

**Symptom**: Configuration options are ignored, paths get duplicated in PATH variable

**Solution**: Configure Mason only in the dependency block, not separately:
```lua
{
  'neovim/nvim-lspconfig',
  dependencies = {
    { 'williamboman/mason.nvim', config = true },
    'williamboman/mason-lspconfig.nvim',
  },
  config = function()
    -- Do NOT call require('mason').setup() here!

    -- Only configure mason-lspconfig
    require('mason-lspconfig').setup { ... }
  end,
}
```

### Issue 2: on_new_config Disables Multi-Workspace

From OmniSharp issue #909:

The `on_new_config` function sets:
```lua
new_config.capabilities.workspace.workspaceFolders = false
```

This is intentional - OmniSharp Roslyn doesn't handle multiple workspaces well in a single instance.

### Issue 3: .editorconfig Not Respected

Even with `EnableEditorConfigSupport = true`, OmniSharp may not pick up `.editorconfig` rules if:
1. The .editorconfig file is not in the solution root
2. It doesn't define the rules you expect
3. OmniSharp hasn't been restarted since adding the file

**Solution**: Ensure `.editorconfig` is in the solution root and restart OmniSharp with `:LspRestart`

### Issue 4: Settings Empty in :LspInfo

**Symptom**: `:LspInfo` shows `settings: {}`

**Likely Cause**: Settings were defined but cmd wasn't set properly, so on_new_config isn't being called

**Diagnosis**:
```bash
ps aux | grep omnisharp
```

Check if the process command includes your settings as arguments. If not, cmd is probably wrong.

### Issue 5: vim.lsp.config() Doesn't Work for OmniSharp

The new `vim.lsp.config()` API (Neovim 0.11+) doesn't work reliably with OmniSharp yet. Use the traditional `lspconfig.omnisharp.setup()` approach instead.

---

## Part 6: Step-by-Step Configuration Guide

### Step 1: Define Your omnisharp Configuration

In your `init.lua`, inside the nvim-lspconfig setup:

```lua
local servers = {
  omnisharp = {
    -- HOW TO START OMNISHARP
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
      '-loglevel', 'Information',
    },

    -- WHAT SETTINGS TO PASS
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,      -- CRITICAL: Enable analyzers!
        EnableImportCompletion = true,
        AnalyzeOpenDocumentsOnly = false,   -- Analyze all files, not just open ones
      },
      FormattingOptions = {
        EnableEditorConfigSupport = true,
        OrganizeImports = true,
      },
    },

    -- OPTIONAL: Custom handlers for specific message types
    handlers = {
      ['window/logMessage'] = function(err, result, ctx, config)
        if result.type <= 2 then  -- Only show errors and warnings
          vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.WARN)
        end
      end,
    },
  },
}
```

### Step 2: Configure Mason-lspconfig to Use Your Config

Right after your servers table, configure the handler:

```lua
require('mason-lspconfig').setup {
  ensure_installed = {},
  automatic_installation = false,
  handlers = {
    -- Default handler for all servers
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

**Do NOT add a special omnisharp handler here!** The default handler will use your `servers.omnisharp` config.

### Step 3: Verify the Configuration

Check that OmniSharp is running with correct arguments:

```bash
ps aux | grep omnisharp | grep -v grep
```

You should see:
- `dotnet` (not just `OmniSharp`)
- `/path/to/OmniSharp.dll`
- `-s /path/to/solution`
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
- Other settings as command-line arguments

### Step 4: Test in Neovim

```bash
# Clear any cached configuration
rm -rf ~/.cache/nvim/luac/

# Kill any running OmniSharp processes
pkill -f omnisharp

# Start Neovim
nvim /path/to/your/solution/UserController.cs
```

Check LSP status:
```vim
:LspInfo
```

Should show OmniSharp with all your configuration.

---

## Part 7: Debugging Commands

### Check if Settings Are Being Flattened

The most reliable way to verify configuration:

```bash
ps aux | grep omnisharp | grep -v grep
```

Look for these in the output:
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true` ✓
- `RoslynExtensionsOptions:EnableImportCompletion=true` ✓
- `FormattingOptions:EnableEditorConfigSupport=true` ✓

If missing, your settings are not being flattened. Likely cause: cmd is wrong or setup not called with settings.

### Check Configuration in Neovim

```vim
" Show LSP information
:LspInfo

" Check the cmd array
:lua print(vim.inspect(require('lspconfig').omnisharp.cmd))

" Check settings
:lua print(vim.inspect(require('lspconfig').omnisharp.settings))

" Check if on_new_config ran
:messages
" Look for your on_attach/on_init notifications
```

### Check OmniSharp Logs

OmniSharp writes logs to:
```bash
cat ~/.local/state/nvim/lsp.log | grep -i omnisharp
```

Look for initialization messages and any errors.

### Clear Cache and Restart

```bash
# Clear Lua bytecode cache
rm -rf ~/.cache/nvim/luac/

# Kill running OmniSharp
pkill -f omnisharp

# Clear swap files
rm -f ~/.local/state/nvim/swap/*.swp

# Restart Neovim
nvim
```

---

## Part 8: Complete Working Example

Here's a complete, minimal example that works:

```lua
-- Inside nvim-lspconfig setup
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', '/path/to/your/solution',
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

  -- Other servers...
  lua_ls = { ... },
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

This configuration will:
1. Start OmniSharp with the direct DLL call
2. Load your solution immediately
3. Enable Roslyn analyzers
4. Read .editorconfig for formatting
5. Organize imports on format

---

## Part 9: Common Mistakes Checklist

- [ ] **Don't** call `lspconfig.omnisharp.setup()` twice
- [ ] **Don't** specify a special handler for omnisharp if using default handler
- [ ] **Don't** forget the `-s` flag if you want fast startup
- [ ] **Don't** use the wrapper script directly; use `dotnet` + DLL path
- [ ] **Don't** use lowercase `enableAnalyzersSupport` in Lua (use PascalCase)
- [ ] **Don't** forget that settings must be in the `settings` table
- [ ] **Don't** set up Mason in both dependency and config blocks
- [ ] **Don't** expect settings to show in `:LspInfo` - check `ps aux` instead

---

## Part 10: References and Sources

### Official Documentation
- **OmniSharp Configuration Options**: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- **nvim-lspconfig omnisharp**: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
- **Mason-lspconfig**: https://github.com/williamboman/mason-lspconfig.nvim

### GitHub Issues
- **Issue #1297 (kickstart.nvim)**: Mason setup called twice
- **Issue #909 (OmniSharp)**: Multi-workspace handling issue
- **Issue #4300 (OmniSharp-VSCode)**: -z flag reasoning

### Articles and Tutorials
- **Enabling Roslyn EditorConfig Support**: https://aaronbos.dev/posts/dotnet-roslyn-editorconfig-neovim
- **Stack Exchange: OmniSharp with Mason**: https://vi.stackexchange.com/questions/43830/how-to-use-omnisharp-c-lsp-with-mason-in-nvim-properly

### Key nvim-lspconfig Source Code
The `on_new_config` function at lines 46-78 in `omnisharp.lua` is the heart of settings processing.

---

## Summary

To properly configure OmniSharp with Roslyn Analyzers in kickstart.nvim:

1. **Define cmd correctly** in `servers.omnisharp.cmd` with direct DLL path and solution path
2. **Define settings** in `servers.omnisharp.settings` with PascalCase keys
3. **Let the handler set it up** - don't call setup() twice
4. **Verify with ps aux** - most reliable way to check if configuration is applied
5. **Check process arguments** for flattened settings like `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

The on_new_config function automatically flattens your settings table into command-line arguments that OmniSharp understands.

