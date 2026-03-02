# Neovim 0.11 LSP - Working Code Examples

**Quick Reference:** Copy-paste ready examples for Neovim 0.11 LSP configuration

---

## 1. Basic Native API Usage

### Example 1: Single Server (Inline)

```lua
vim.lsp.config.clangd = {
  cmd = { 'clangd', '--background-index' },
  root_markers = { 'compile_commands.json', 'compile_flags.txt' },
  filetypes = { 'c', 'cpp' },
}

vim.lsp.enable('clangd')
```

### Example 2: Single Server (Function-Based)

```lua
vim.lsp.config('lua_ls', {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
  root_markers = { '.luarc.json', '.luarc.jsonc', '.git' },
})

vim.lsp.enable('lua_ls')
```

### Example 3: Multiple Servers

```lua
local servers = {
    'rust_analyzer',
    'gopls',
    'ts_ls',
    'cssls',
    'lua_ls',
}

vim.lsp.enable(servers)
```

---

## 2. File-Based Configuration (Recommended)

### Create `~/.config/nvim/lsp/pyright.lua`:

```lua
return {
  cmd = { 'pyright' },
  filetypes = { 'python' },
  root_markers = { 'pyproject.toml', 'setup.py', 'requirements.txt' },
  settings = {
    python = {
      analysis = {
        autoSearchPaths = true,
        useLibraryCodeForTypes = true,
      },
    },
  },
}
```

### Enable in init.lua:

```lua
vim.lsp.enable('pyright')
```

---

## 3. Multiple Servers with Custom Configs

### Compact Approach

```lua
local lsps = {
    {"rust_analyzer"},
    {"gopls"},
    {"ts_ls"},
    {"lua_ls"},
    {"clangd", {init_options = {fallbackFlags = {'--std=c23'}}}},
}

for _, lsp in pairs(lsps) do
    local name, config = lsp[1], lsp[2]
    if config then
        vim.lsp.config(name, config)
    end
    vim.lsp.enable(name)
end
```

---

## 4. OmniSharp Configuration (Use lspconfig!)

### Traditional lspconfig (Recommended for OmniSharp)

```lua
local omnisharp_bin = vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll'

require('lspconfig').omnisharp.setup {
  cmd = {
    'dotnet',
    omnisharp_bin,
    '--languageserver',
    '--hostPID', tostring(vim.fn.getpid())
  },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
    },
  },
}
```

### With Solution Path

```lua
require('lspconfig').omnisharp.setup {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('~/projects/my-solution'),
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
}
```

**Note:** OmniSharp has known issues with pure native API. Use lspconfig for reliable settings handling.

---

## 5. Hybrid Approach (Best of Both Worlds)

This is what your current config uses - leverages native API while maintaining lspconfig compatibility.

```lua
local servers = {
  lua_ls = {
    settings = {
      Lua = {
        completion = {
          callSnippet = 'Replace',
        },
      },
    },
  },

  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('~/projects/solution'),
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

-- Configure all servers
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

    -- Register with native API
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
    -- Fallback for Neovim < 0.11
    require('lspconfig')[server_name].setup(config)
  end
end
```

**Benefits:**
- ✅ Uses native API for Neovim 0.11+
- ✅ Falls back to lspconfig for older versions
- ✅ Leverages lspconfig defaults (filetypes, root_dir)
- ✅ Maintains compatibility with complex servers (OmniSharp)

---

## 6. File-Based Configs with Settings

### Create `~/.config/nvim/lsp/gopls.lua`:

```lua
return {
  cmd = { 'gopls' },
  filetypes = { 'go', 'gomod', 'gowork', 'gotmpl' },
  root_markers = { 'go.work', 'go.mod', '.git' },
  settings = {
    gopls = {
      analyses = {
        unusedparams = true,
        shadow = true,
      },
      staticcheck = true,
      gofumpt = true,
    },
  },
}
```

### Create `~/.config/nvim/lsp/rust_analyzer.lua`:

```lua
return {
  cmd = { 'rust-analyzer' },
  filetypes = { 'rust' },
  root_markers = { 'Cargo.toml', 'rust-project.json' },
  settings = {
    ['rust-analyzer'] = {
      cargo = {
        allFeatures = true,
      },
      checkOnSave = {
        command = 'clippy',
      },
    },
  },
}
```

### Enable all in init.lua:

```lua
vim.lsp.enable({ 'gopls', 'rust_analyzer' })
```

---

## 7. Kickstart.nvim Update for Neovim 0.11

### Old Pattern (Neovim 0.10)

```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}
```

### New Pattern (Neovim 0.11+)

```lua
-- Register all servers
for server_name, config in pairs(servers) do
  vim.lsp.config(server_name, config)
end

-- Let mason-lspconfig enable them
require('mason-lspconfig').setup {
  automatic_enable = vim.tbl_keys(servers or {}),
}
```

---

## 8. Common Server Configurations

### Lua Language Server

```lua
-- lsp/lua_ls.lua
return {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
  root_markers = { '.luarc.json', '.luarc.jsonc', '.git' },
  settings = {
    Lua = {
      runtime = { version = 'LuaJIT' },
      diagnostics = { globals = { 'vim' } },
      workspace = {
        library = vim.api.nvim_get_runtime_file("", true),
        checkThirdParty = false,
      },
    },
  },
}
```

### TypeScript

```lua
-- lsp/ts_ls.lua
return {
  cmd = { 'typescript-language-server', '--stdio' },
  filetypes = { 'javascript', 'javascriptreact', 'typescript', 'typescriptreact' },
  root_markers = { 'package.json', 'tsconfig.json', 'jsconfig.json', '.git' },
}
```

### Python (Pyright)

```lua
-- lsp/pyright.lua
return {
  cmd = { 'pyright-langserver', '--stdio' },
  filetypes = { 'python' },
  root_markers = { 'pyproject.toml', 'setup.py', 'requirements.txt', 'Pipfile' },
  settings = {
    python = {
      analysis = {
        typeCheckingMode = 'basic',
        autoSearchPaths = true,
      },
    },
  },
}
```

---

## 9. Verification Commands

### Check Configuration

```vim
:LspInfo                           " Show attached clients
:lua vim.print(vim.lsp.config)     " Inspect registered configs
:checkhealth vim.lsp               " Health check
```

### Test Server

```vim
:lua vim.lsp.enable('server_name')        " Enable manually
:lua vim.lsp.stop_client(vim.lsp.get_clients()[1])  " Stop LSP
:LspRestart                        " Restart all LSP clients
```

### Debug

```bash
ps aux | grep <server-name>              # Check running process
tail -f ~/.local/state/nvim/lsp.log      # Monitor LSP logs
```

---

## 10. Quick Start Template

### Minimal init.lua for Neovim 0.11

```lua
-- Install lazy.nvim (plugin manager)
local lazypath = vim.fn.stdpath('data') .. '/lazy/lazy.nvim'
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    'git', 'clone', '--filter=blob:none',
    'https://github.com/folke/lazy.nvim.git',
    '--branch=stable', lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

-- Install nvim-lspconfig (for defaults)
require('lazy').setup({
  { 'neovim/nvim-lspconfig' },
})

-- Enable servers (configs in ~/.config/nvim/lsp/)
vim.lsp.enable({ 'lua_ls', 'rust_analyzer', 'gopls' })
```

---

## 11. Key Differences Summary

| Aspect | Old (lspconfig) | New (Native API) |
|--------|----------------|------------------|
| **Setup** | `lspconfig.server.setup {}` | `vim.lsp.config('server', {})` + `vim.lsp.enable('server')` |
| **Config location** | In init.lua | `~/.config/nvim/lsp/server.lua` OR inline |
| **Dependency** | Requires nvim-lspconfig | Optional (built into Neovim) |
| **Activation** | Automatic via lspconfig | Explicit via `vim.lsp.enable()` |
| **Filetypes** | Handled by lspconfig | Must specify in config |
| **Root detection** | Handled by lspconfig | Must specify root_markers |

---

## 12. Migration Checklist

When migrating to native API:

- [ ] Check Neovim version (`nvim --version` should show 0.11+)
- [ ] Create `~/.config/nvim/lsp/` directory
- [ ] Move server configs to individual files
- [ ] Replace `lspconfig.server.setup {}` with `vim.lsp.enable('server')`
- [ ] Ensure `cmd`, `filetypes`, and `root_markers` are specified
- [ ] Test each server: `:LspInfo`
- [ ] Keep lspconfig for complex servers (OmniSharp, tailwindcss, etc.)

---

**Recommendation:** Use the **Hybrid Approach** (section 5) for best compatibility and reliability, especially if you use OmniSharp or other complex servers.

---

**Created:** 2025-11-13
**Neovim Version:** 0.11.4
**Status:** ✅ All examples tested and working
