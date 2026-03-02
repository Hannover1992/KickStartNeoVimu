# vim.lsp.config() Quick Reference - Neovim 0.11+

**Last Updated**: 2025-11-13

---

## API Quick Reference

### vim.lsp.config()
```lua
vim.lsp.config({name}, {cfg})
```
**Purpose**: Define or customize LSP server configuration

**Key Fields**:
- `cmd` - Command to start server (string[] or function)
- `filetypes` - File types to attach to (string[])
- `root_markers` - Files to identify project root (string[])
- `settings` - Server-specific settings (table)
- `capabilities` - LSP capabilities overrides (table)
- `on_attach` - Callback when attached (function)

### vim.lsp.enable()
```lua
vim.lsp.enable({name}, {enable})
```
**Purpose**: Enable/disable LSP server auto-start

**Parameters**:
- `name` - Server name(s) (string or string[])
- `enable` - true/nil to enable, false to disable (boolean?)

---

## Common Patterns

### Pattern 1: Simple Server Setup
```lua
vim.lsp.config('lua_ls', {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
  root_markers = { '.git' }
})
vim.lsp.enable('lua_ls')
```

### Pattern 2: With FileType Autocmd (Explicit Control)
```lua
vim.lsp.config('lua_ls', {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
})

vim.api.nvim_create_autocmd('FileType', {
  pattern = { 'lua' },
  callback = function(ev)
    vim.lsp.enable('lua_ls', ev.buf)  -- Pass buffer number!
  end,
})
```

### Pattern 3: Multiple Servers (Iteration)
```lua
local servers = {
  { "lua_ls", { settings = { Lua = { runtime = { version = 'LuaJIT' } } } } },
  { "pyright" },
  { "clangd", { init_options = { fallbackFlags = { '--std=c23' } } } },
}

for _, server in pairs(servers) do
  local name, config = server[1], server[2]
  if config then
    vim.lsp.config(name, config)
  end
  vim.lsp.enable(name)
end
```

### Pattern 4: Hybrid (Compatibility with Old Neovim)
```lua
local config = { cmd = {...}, filetypes = {...} }

if vim.fn.has('nvim-0.11') == 1 then
  -- New API
  vim.lsp.config('lua_ls', config)
  vim.lsp.enable('lua_ls')
else
  -- Old API
  require('lspconfig').lua_ls.setup(config)
end
```

---

## OmniSharp (C#) - Special Case

**RECOMMENDED: Use lspconfig.setup() for OmniSharp**
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
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
  },
})
```

**Why not vim.lsp.config()?**
- OmniSharp requires settings flattened to CLI args
- lspconfig's `on_new_config` handles this automatically
- Pure vim.lsp.config() has known issues with OmniSharp settings

---

## Mason-lspconfig v2.x Integration

### Automatic Enable (Default)
```lua
require('mason-lspconfig').setup({
  automatic_enable = true,  -- Mason calls vim.lsp.enable() for you
})

vim.lsp.config('lua_ls', {
  settings = { ... }  -- Just configure, mason-lspconfig enables
})
```

### Manual Control (Recommended for Custom Configs)
```lua
require('mason-lspconfig').setup({
  automatic_enable = false,  -- You control when servers enable
})

vim.lsp.config('lua_ls', { ... })
vim.lsp.enable('lua_ls')  -- YOU call enable
```

### Exclude Specific Servers
```lua
require('mason-lspconfig').setup({
  automatic_enable = {
    exclude = { 'omnisharp', 'rust_analyzer' }
  }
})
```

---

## Migration from lspconfig.setup()

**Old (deprecated but still works):**
```lua
require('lspconfig').lua_ls.setup({
  cmd = { 'lua-language-server' },
  settings = { Lua = { ... } }
})
```

**New (Neovim 0.11+):**
```lua
vim.lsp.config('lua_ls', {
  cmd = { 'lua-language-server' },
  settings = { Lua = { ... } }
})
vim.lsp.enable('lua_ls')
```

**What's deprecated:**
- ❌ `require('lspconfig')` module (will be removed in v3.0.0)
- ❌ `lspconfig[server].setup()` method

**What's NOT deprecated:**
- ✅ nvim-lspconfig plugin (provides config data)
- ✅ lspconfig's server configs in `lsp/*.lua`

---

## Verification Commands

```vim
" Check LSP health
:checkhealth vim.lsp

" Check attached clients
:LspInfo

" Check config registration
:lua print(vim.inspect(vim.lsp.config.lua_ls))

" Check running clients
:lua print(vim.inspect(vim.lsp.get_clients()))

" Check process (OmniSharp)
:!ps aux | grep omnisharp
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| LSP not attaching | Check `:LspInfo`, verify FileType autocmd, ensure root_markers exist |
| Settings not applied | For OmniSharp: use lspconfig.setup(), check `ps aux` for CLI args |
| Deprecation warnings | Migrate to vim.lsp.config() + vim.lsp.enable() |
| mason-lspconfig conflicts | Set `automatic_enable = false` |
| Multiple instances | Check `:lua print(vim.inspect(vim.lsp.get_clients()))` |

---

## Resources

- **Docs**: `:help vim.lsp.config` `:help vim.lsp.enable`
- **Online**: https://neovim.io/doc/user/lsp.html
- **nvim-lspconfig**: https://github.com/neovim/nvim-lspconfig
- **mason-lspconfig**: https://github.com/mason-org/mason-lspconfig.nvim

---

## Common Mistakes

❌ **Forgetting buffer number in autocmd:**
```lua
callback = function(ev)
  vim.lsp.enable('lua_ls')  -- WRONG! Missing ev.buf
end
```

✅ **Correct:**
```lua
callback = function(ev)
  vim.lsp.enable('lua_ls', ev.buf)  -- RIGHT!
end
```

---

❌ **Using vim.lsp.config for OmniSharp:**
```lua
vim.lsp.config('omnisharp', {
  settings = { RoslynExtensionsOptions = { ... } }  -- Won't work!
})
```

✅ **Correct:**
```lua
require('lspconfig').omnisharp.setup({
  settings = { RoslynExtensionsOptions = { ... } }  -- Works!
})
```

---

❌ **Removing nvim-lspconfig plugin:**
```lua
-- Thinking vim.lsp.config replaces nvim-lspconfig
-- WRONG! You still need the plugin for config data
```

✅ **Correct:**
```lua
-- Keep nvim-lspconfig installed
-- It provides default configs for vim.lsp.config to read
```

---

**End of Quick Reference**
