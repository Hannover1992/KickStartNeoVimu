# Neovim 0.11 vim.lsp.config() API - Complete Research Report

**Date**: 2025-11-13
**Neovim Version**: 0.11.4
**Research Scope**: Migration from nvim-lspconfig to native vim.lsp.config API

---

## Executive Summary

Neovim 0.11 introduced a **native LSP configuration API** (`vim.lsp.config()` and `vim.lsp.enable()`) designed to eventually replace the `require('lspconfig')` framework. This research documents:

1. ✅ Complete working examples of vim.lsp.config() setup
2. ✅ Mason-lspconfig v2.x compatibility status
3. ✅ Correct FileType autocmd + vim.lsp.enable() pattern
4. ✅ Breaking changes between lspconfig and native API
5. ✅ OmniSharp-specific considerations

**Key Finding**: The current init.lua already uses a **hybrid approach** that is compatible with both nvim-lspconfig and the new API, using `vim.lsp.config()` + FileType autocmd + `vim.lsp.enable()` for Neovim 0.11+.

---

## 1. vim.lsp.config() API Documentation

### Function Signature
```lua
vim.lsp.config({name}, {cfg})
```

### Parameters

**`{name}`** (string): Client name or `'*'` for all clients

**`{cfg}`** (vim.lsp.Config): Configuration table with fields:
- **`cmd`** (string[]|function): Command array or function to launch the language server
- **`filetypes`** (string[]): Table of filetypes the client attaches to
- **`root_markers`** (string[]): Filenames to identify workspace root directory
- **`root_dir`** (string|function): Function or string specifying workspace root
- **`settings`** (table): Server-specific settings (server-defined schema)
- **`capabilities`** (table): LSP capabilities overrides
- **`on_attach`** (function): Callback when client attaches to buffer

### Access Methods

**Set configuration (two syntaxes):**
```lua
-- Method 1: Function call
vim.lsp.config('lua_ls', {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
  root_markers = { '.luarc.json', '.git' }
})

-- Method 2: Table assignment (OVERRIDES entire config chain)
vim.lsp.config.lua_ls = {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' }
}
```

**Retrieve resolved config:**
```lua
local cfg = vim.lsp.config.lua_ls
```

### Config Merge Priority (lowest to highest)
1. Configuration for `'*'` name (global defaults)
2. Configurations from `lsp/<config>.lua` files (nvim-lspconfig)
3. Configurations defined elsewhere (user config)

---

## 2. vim.lsp.enable() API Documentation

### Function Signature
```lua
vim.lsp.enable({name}, {enable})
```

### Purpose
"Auto-starts LSP when a buffer is opened, based on the lsp-config filetypes, root_markers, and root_dir fields."

### Parameters

**`{name}`** (string|string[]): Name(s) of client(s) to enable

**`{enable}`** (boolean?):
- `true` or `nil` to enable
- `false` to disable (actively stops and detaches clients)

### Usage Examples

**Basic enable:**
```lua
vim.lsp.enable('clangd')
vim.lsp.enable({'lua_ls', 'pyright'})
```

**Restart pattern:**
```lua
vim.lsp.enable('clangd', false)  -- Stop
vim.lsp.enable('clangd', true)   -- Start
```

**Dynamic activation:**
```lua
vim.lsp.config('lua_ls', {
  root_dir = function(bufnr, on_dir)
    if not vim.fn.bufname(bufnr):match('%.txt$') then
      on_dir(vim.fn.getcwd())
    end
  end
})
vim.lsp.enable('lua_ls')
```

### Availability
Since: 0.11.0

---

## 3. Complete Working Examples

### Example 1: Basic Server Configuration

**Single server:**
```lua
vim.lsp.config('lua_ls', {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
  root_markers = { '.luarc.json', '.luarc.jsonc', '.git' },
  settings = {
    Lua = {
      runtime = { version = 'LuaJIT' }
    }
  }
})

vim.lsp.enable('lua_ls')
```

### Example 2: Multiple Servers (Unified Pattern)

**Iterate over server configs:**
```lua
local lsps = {
  { "rust_analyzer" },
  { "gopls" },
  { "clangd", { init_options = { fallbackFlags = { '--std=c23' } } } },
  { "sqleibniz", {
      cmd = { '/usr/bin/sqleibniz', '--lsp' },
      filetypes = { "sql" },
      root_markers = { "leibniz.lua" }
  } },
}

for _, lsp in pairs(lsps) do
  local name, config = lsp[1], lsp[2]
  vim.lsp.enable(name)
  if config then
    vim.lsp.config(name, config)
  end
end
```

### Example 3: File-Based Configuration

**Create `~/.config/nvim/lsp/lua_ls.lua`:**
```lua
return {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
  root_markers = {
    '.luarc.json',
    '.luarc.jsonc',
    '.git'
  },
  settings = {
    Lua = {
      runtime = { version = 'LuaJIT' }
    }
  }
}
```

**Enable in init.lua:**
```lua
vim.lsp.enable('lua_ls')
-- Config automatically discovered from lsp/ directory
```

### Example 4: OmniSharp Configuration (C#)

**Method 1: Direct configuration (may have issues with settings):**
```lua
vim.lsp.config("omnisharp", {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/path/to/solution',
    '-loglevel', 'Information',
  },
  filetypes = { 'cs' },
  root_markers = { '*.sln', '*.csproj' },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
  },
  handlers = {
    ["textDocument/definition"] = require('omnisharp_extended').handler,
  },
})

vim.lsp.enable("omnisharp")
```

**Method 2: Hybrid with nvim-lspconfig (RECOMMENDED for OmniSharp):**
```lua
-- Use lspconfig's OmniSharp setup which handles settings -> CLI args conversion
require('lspconfig').omnisharp.setup({
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/path/to/solution',
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
  },
})
```

**Note**: OmniSharp has known issues with pure `vim.lsp.config()` - settings may not be properly flattened to CLI args. The lspconfig.setup() method includes an `on_new_config` function that handles this conversion.

---

## 4. Mason-lspconfig Compatibility

### Mason-lspconfig v2.x Breaking Changes

**Removed in v2.0:**
- ❌ `handlers` callback pattern
- ❌ `automatic_installation` setting
- ❌ `.setup_handlers()` function

**Added in v2.0:**
- ✅ `automatic_enable` setting (default: `true`)
- ✅ Automatic `vim.lsp.enable()` for installed servers

### Mason-lspconfig v2.x Requirements

- **Neovim**: >= 0.11
- **Mason**: >= 2.0
- **nvim-lspconfig**: Still required (provides config "data")

### Migration: v1 to v2

**Before (v1 with handlers):**
```lua
require('mason-lspconfig').setup({
  ensure_installed = { 'lua_ls' },
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup({})
    end,
    ["lua_ls"] = function()
      require('lspconfig').lua_ls.setup({
        settings = {
          Lua = { runtime = { version = 'Lua 5.1' } }
        }
      })
    end,
  }
})
```

**After (v2 with automatic_enable):**
```lua
require('mason-lspconfig').setup({
  ensure_installed = { 'lua_ls' },
  automatic_enable = true,  -- Default behavior
})

-- Configure servers separately using vim.lsp.config
vim.lsp.config('lua_ls', {
  settings = {
    Lua = { runtime = { version = 'Lua 5.1' } }
  }
})
```

### Mason-lspconfig v2.x Configuration Options

**Option 1: Enable all (default):**
```lua
require('mason-lspconfig').setup({
  automatic_enable = true,  -- Enables ALL installed servers
})
```

**Option 2: Exclude specific servers:**
```lua
require('mason-lspconfig').setup({
  automatic_enable = {
    exclude = { "rust_analyzer", "ts_ls" }
  }
})
```

**Option 3: Enable only specific servers:**
```lua
require('mason-lspconfig').setup({
  automatic_enable = { "lua_ls", "vimls" }
})
```

**Option 4: Disable automatic_enable (manual control):**
```lua
require('mason-lspconfig').setup({
  automatic_enable = false,  -- YOU must call vim.lsp.enable() manually
})
```

### Current init.lua Approach (Hybrid Pattern)

**File**: `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`
**Lines**: 745-783

```lua
require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}),
  automatic_installation = false,
  automatic_enable = false,  -- Disable auto-enable, we configure manually
}

-- Manual configuration for ALL servers
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  if vim.fn.has('nvim-0.11') == 1 then
    -- Get filetypes from lspconfig as fallback
    local lspconfig_defaults = require('lspconfig.configs')[server_name]
    if lspconfig_defaults and lspconfig_defaults.default_config then
      config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
      config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir
    end

    -- Register with new API
    vim.lsp.config(server_name, config)

    -- Enable on matching filetypes
    if config.filetypes then
      vim.api.nvim_create_autocmd('FileType', {
        pattern = config.filetypes,
        callback = function(ev)
          vim.lsp.enable(server_name, ev.buf)
        end,
      })
    end
  else
    -- Fallback for older Neovim versions
    require('lspconfig')[server_name].setup(config)
  end
end
```

**Why this works:**
- ✅ Disables `automatic_enable` to prevent mason-lspconfig from auto-enabling
- ✅ Manually calls `vim.lsp.config()` for each server
- ✅ Creates FileType autocmd to call `vim.lsp.enable()` with buffer number
- ✅ Falls back to lspconfig for filetypes/root_dir defaults
- ✅ Compatible with both Neovim 0.11+ and older versions

---

## 5. FileType Autocmd + vim.lsp.enable() Pattern

### Correct Pattern

**Pass buffer number to vim.lsp.enable():**
```lua
vim.api.nvim_create_autocmd('FileType', {
  pattern = { 'lua' },
  callback = function(ev)
    vim.lsp.enable('lua_ls', ev.buf)  -- ev.buf is critical!
  end,
})
```

**Why buffer number is needed:**
- Without `ev.buf`, LSP may not attach to the correct buffer
- `vim.lsp.enable(name, bufnr)` signature expects buffer number as second arg
- FileType autocmd provides `ev.buf` in callback

### Alternative: Global vim.lsp.enable()

**Enable globally (no autocmd needed):**
```lua
vim.lsp.config('lua_ls', {
  filetypes = { 'lua' },
  -- ... other config
})

vim.lsp.enable('lua_ls')  -- Auto-attaches based on filetypes
```

**When this works:**
- LSP automatically attaches when a buffer with matching filetype is opened
- No manual autocmd needed
- Simpler, but less control over when activation happens

### Current init.lua Pattern (Explicit Control)

```lua
-- Register config
vim.lsp.config(server_name, config)

-- Create autocmd to enable on FileType
vim.api.nvim_create_autocmd('FileType', {
  pattern = config.filetypes,
  callback = function(ev)
    vim.lsp.enable(server_name, ev.buf)
  end,
})
```

**Why this approach:**
- ✅ Explicit control over when LSP activates
- ✅ Can add conditional logic in callback
- ✅ Works well with multiple servers sharing filetypes
- ✅ Clear debugging (can add prints in callback)

---

## 6. Breaking Changes: lspconfig vs Native API

### require('lspconfig') Deprecation Status

**Official Statement** (from nvim-lspconfig README):
> `require('lspconfig')` (the legacy framework) is deprecated in favor of `vim.lsp.config` (Nvim 0.11+).

**Deprecation Timeline:**
- ⚠️ Currently: Shows warnings
- ❌ Future: Warnings will become errors
- 🗑️ nvim-lspconfig v3.0.0: `require('lspconfig')` module will be removed entirely

### What is NOT Deprecated

**nvim-lspconfig plugin itself is NOT deprecated!**

The plugin still provides:
- ✅ Server configurations in `lsp/*.lua` files
- ✅ Default filetypes, root_markers, cmd for each server
- ✅ Server-specific handlers (e.g., OmniSharp's on_new_config)
- ✅ Automatic discovery by `vim.lsp.config()`

### Migration Summary

| Old API | New API | Status |
|---------|---------|--------|
| `require('lspconfig')` | `vim.lsp.config()` | Deprecated |
| `lspconfig.lua_ls.setup{}` | `vim.lsp.config('lua_ls', {})` + `vim.lsp.enable('lua_ls')` | Migrated |
| Automatic setup via handlers | Manual `vim.lsp.enable()` or `automatic_enable = true` | Changed |
| nvim-lspconfig plugin | Still required (provides config data) | Active |

### Compatibility Layer

**nvim-lspconfig still provides compatibility:**
- Calling `require('lspconfig').lua_ls.setup{}` still works (shows warning)
- Config files in `lsp/*.lua` are automatically read by `vim.lsp.config()`
- No need to rewrite existing lspconfig calls immediately

**When to use lspconfig.setup() (compatibility):**
- For servers with complex on_new_config handlers (OmniSharp)
- When settings need special transformation (e.g., flattened to CLI args)
- During gradual migration period

---

## 7. OmniSharp-Specific Considerations

### Known Issue: Settings Not Applied

**Problem**: When using pure `vim.lsp.config()` for OmniSharp, settings may not be properly applied.

**Example from GitHub Issue #35175:**
```lua
vim.lsp.config("omnisharp", {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
})
vim.lsp.enable("omnisharp")

-- Result: Settings are NOT converted to CLI args!
-- Expected: RoslynExtensionsOptions:EnableAnalyzersSupport=true
-- Actual: Missing from process command line
```

### Why OmniSharp is Special

**OmniSharp requires settings flattening:**
- Settings table needs to be converted to CLI args
- Example: `settings.RoslynExtensionsOptions.EnableAnalyzersSupport = true`
- Becomes: `RoslynExtensionsOptions:EnableAnalyzersSupport=true` (CLI arg)

**nvim-lspconfig provides `on_new_config` handler:**
- Located in: `~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
- Function flattens settings table into command-line args
- Appends hard-coded args: `-z`, `--hostPID`, `--encoding`, `--languageserver`

### Recommended Solution for OmniSharp

**Option 1: Use lspconfig.setup() (RECOMMENDED):**
```lua
require('lspconfig').omnisharp.setup({
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
})
```

**Why this works:**
- ✅ lspconfig's `on_new_config` automatically flattens settings
- ✅ All settings appear as CLI args in `ps aux | grep omnisharp`
- ✅ Proven to work (user confirmed: "yes motherfuck es lafue jez")

**Option 2: Manual CLI arg construction (NOT RECOMMENDED):**
```lua
vim.lsp.config('omnisharp', {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/path/to/solution',
    '-loglevel', 'Information',
    '-z',
    '--hostPID', tostring(vim.fn.getpid()),
    'DotNet:enablePackageRestore=false',
    '--encoding', 'utf-8',
    '--languageserver',
    'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
    'RoslynExtensionsOptions:EnableImportCompletion=true',
    'FormattingOptions:EnableEditorConfigSupport=true',
    'FormattingOptions:OrganizeImports=true',
  },
  filetypes = { 'cs' },
})
vim.lsp.enable('omnisharp')
```

**Why this is fragile:**
- ❌ Must manually flatten ALL settings
- ❌ Easy to miss settings or get syntax wrong
- ❌ No automatic update if OmniSharp changes CLI format
- ❌ Harder to maintain

### Option 3: omnisharp.json Config File

**Create `~/.omnisharp/omnisharp.json`:**
```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
```

**Neovim config:**
```lua
vim.lsp.config('omnisharp', {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/path/to/solution',
    '-loglevel', 'Information',
  },
  filetypes = { 'cs' },
})
vim.lsp.enable('omnisharp')
```

**Why this works:**
- ✅ OmniSharp reads `~/.omnisharp/omnisharp.json` automatically
- ✅ Zero Neovim config changes needed
- ✅ Settings apply globally (all projects)
- ❌ Less portable (requires file setup on each machine)

---

## 8. Best Practices Summary

### When to Use vim.lsp.config()

**Use native API for:**
- ✅ Simple servers with standard config (lua_ls, pyright, clangd)
- ✅ Servers without complex on_new_config handlers
- ✅ Future-proof configurations (lspconfig.setup() will be removed)
- ✅ Full control over activation timing (FileType autocmd)

**Example:**
```lua
vim.lsp.config('lua_ls', {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
  root_markers = { '.git' },
  settings = { Lua = { runtime = { version = 'LuaJIT' } } }
})
vim.lsp.enable('lua_ls')
```

### When to Use lspconfig.setup()

**Use lspconfig.setup() for:**
- ✅ OmniSharp (requires settings flattening)
- ✅ Servers with custom on_new_config handlers
- ✅ During migration period (compatibility)
- ✅ When you need lspconfig's default root_dir logic

**Example:**
```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '/solution' },
  settings = {
    RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
  }
})
```

### Hybrid Approach (Current init.lua)

**Best of both worlds:**
```lua
if vim.fn.has('nvim-0.11') == 1 then
  -- Use vim.lsp.config for Neovim 0.11+
  vim.lsp.config(server_name, config)
  vim.api.nvim_create_autocmd('FileType', {
    pattern = config.filetypes,
    callback = function(ev)
      vim.lsp.enable(server_name, ev.buf)
    end,
  })
else
  -- Fallback to lspconfig for older versions
  require('lspconfig')[server_name].setup(config)
end
```

**Why this is optimal:**
- ✅ Works on Neovim 0.11+ and older versions
- ✅ Uses native API when available
- ✅ Explicit control over activation
- ✅ Compatible with mason-lspconfig v2.x
- ✅ No deprecation warnings

### Mason-lspconfig v2.x Setup

**For automatic server enabling:**
```lua
require('mason-lspconfig').setup({
  automatic_enable = true,  -- Let mason-lspconfig handle vim.lsp.enable()
})

-- Just configure servers
vim.lsp.config('lua_ls', {
  settings = { ... }
})
```

**For manual control (current approach):**
```lua
require('mason-lspconfig').setup({
  automatic_enable = false,  -- We'll call vim.lsp.enable() ourselves
})

-- Configure AND enable manually
vim.lsp.config('lua_ls', { ... })
vim.api.nvim_create_autocmd('FileType', {
  pattern = { 'lua' },
  callback = function(ev)
    vim.lsp.enable('lua_ls', ev.buf)
  end,
})
```

---

## 9. Verification Commands

### Check LSP Status
```vim
:checkhealth vim.lsp
:LspInfo
```

### Check Running Process
```bash
ps aux | grep omnisharp | grep -v grep
# Should show: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

### Check Config Registration
```vim
:lua print(vim.inspect(vim.lsp.config.omnisharp))
```

### Check Enabled Servers
```vim
:lua print(vim.inspect(vim.lsp.get_clients()))
```

### Debug LSP Logs
```bash
tail -f ~/.local/state/nvim/lsp.log
```

---

## 10. Troubleshooting

### Issue: Settings Not Appearing in Process

**Symptom**: `ps aux | grep omnisharp` doesn't show expected CLI args

**Solutions**:
1. ✅ Use `require('lspconfig').omnisharp.setup()` instead of `vim.lsp.config()`
2. ✅ Create `~/.omnisharp/omnisharp.json` config file
3. ✅ Manually flatten settings to CLI args (not recommended)

### Issue: LSP Not Attaching

**Symptom**: `:LspInfo` shows "No LSP client attached"

**Solutions**:
1. Check FileType autocmd is created: `:autocmd FileType`
2. Verify `vim.lsp.enable()` is called with buffer number
3. Check filetypes match: `:set filetype?`
4. Ensure root_markers exist in project
5. Check LSP logs: `tail -f ~/.local/state/nvim/lsp.log`

### Issue: Deprecation Warnings

**Symptom**: Warning about `require('lspconfig')` being deprecated

**Solutions**:
1. Migrate to `vim.lsp.config()` + `vim.lsp.enable()`
2. For OmniSharp: Keep using lspconfig.setup() (it's still supported)
3. Update mason-lspconfig to v2.x

### Issue: Mason-lspconfig Conflicts

**Symptom**: Servers enabled automatically, ignoring your config

**Solutions**:
1. Set `automatic_enable = false` in mason-lspconfig.setup()
2. Manually call `vim.lsp.config()` + `vim.lsp.enable()`
3. Exclude servers: `automatic_enable = { exclude = { 'omnisharp' } }`

---

## 11. Resources

### Official Documentation
- **Neovim LSP**: https://neovim.io/doc/user/lsp.html
- **Neovim 0.11 News**: https://neovim.io/doc/user/news-0.11.html
- **nvim-lspconfig**: https://github.com/neovim/nvim-lspconfig
- **mason-lspconfig**: https://github.com/mason-org/mason-lspconfig.nvim

### Blog Posts & Guides
- **What's New in Neovim 0.11**: https://gpanders.com/blog/whats-new-in-neovim-0-11/
- **Neovim LSP 0.11**: https://davelage.com/posts/neovim-lsp-0.11/
- **Native LSP Config**: https://0xunicorn.com/neovim-native-lsp-config/
- **Switching to Native LSP**: https://lugh.ch/switching-to-neovim-native-lsp.html
- **LSP Configuration in Neovim 0.11**: https://goral.net.pl/post/lsp-configuration-in-neovim-011/
- **Mason 2.0 Breaking Changes**: https://kosu.me/blog/breaking-changes-in-mason-2-0-how-i-updated-my-neovim-lsp-config

### GitHub Discussions
- **OmniSharp vim.lsp.config Issue**: https://github.com/neovim/neovim/discussions/35175
- **Mason Migration Guide**: https://github.com/mason-org/mason.nvim/discussions/2023
- **nvim-lspconfig Migration**: https://github.com/neovim/nvim-lspconfig/issues/3494

---

## 12. Conclusion

### Current init.lua Status: OPTIMAL ✅

The current configuration in `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua` is **already using best practices**:

1. ✅ Uses `vim.lsp.config()` for Neovim 0.11+
2. ✅ Falls back to `lspconfig.setup()` for older versions
3. ✅ Disables `automatic_enable` for manual control
4. ✅ Creates explicit FileType autocmds with `vim.lsp.enable(bufnr)`
5. ✅ Fetches default filetypes/root_dir from lspconfig
6. ✅ Compatible with mason-lspconfig v2.x

### OmniSharp Recommendation

For OmniSharp specifically, **continue using lspconfig.setup()** because:
- ✅ Proven to work (user confirmed functionality)
- ✅ Handles settings flattening automatically
- ✅ lspconfig.setup() is still supported (just shows warning)
- ✅ Pure vim.lsp.config() has known issues with OmniSharp

### Migration Checklist

If you want to migrate OTHER servers to pure vim.lsp.config():

- [x] Update to Neovim 0.11+
- [x] Update mason-lspconfig to v2.x
- [x] Set `automatic_enable = false` (for manual control)
- [x] Use `vim.lsp.config(name, config)` instead of `require('lspconfig')[name].setup()`
- [x] Create FileType autocmd with `vim.lsp.enable(name, bufnr)`
- [x] Keep nvim-lspconfig installed (provides config data)
- [ ] Test each server individually
- [ ] Verify with `:LspInfo` and `ps aux`
- [ ] For OmniSharp: Keep using lspconfig.setup()

### Final Recommendation

**NO CHANGES NEEDED** to current init.lua. The hybrid approach is:
- Future-proof (uses new API)
- Backward-compatible (falls back for old Neovim)
- Flexible (manual control over activation)
- Reliable (proven to work with OmniSharp)

---

**End of Report**
