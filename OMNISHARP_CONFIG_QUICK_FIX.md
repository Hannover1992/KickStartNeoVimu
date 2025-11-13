# OmniSharp Configuration Quick Fix Guide

## TL;DR - The Problem

When you configure OmniSharp in the `servers` table and pass it to mason-lspconfig's default handler, **your configuration is ignored** because mason-lspconfig v2.0+ automatically calls `vim.lsp.enable()` which pre-configures the server with Mason's default wrapper cmd.

## The Fix (One of Two Options)

### Option 1: Skip OmniSharp in Default Handler (Recommended)

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/path/to/your/solution'),
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
  -- ... other servers
}

require('mason-lspconfig').setup {
  handlers = {
    -- Default handler for all servers EXCEPT omnisharp
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Skip - we'll configure it manually
      end
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}

-- Explicit OmniSharp setup AFTER mason-lspconfig
if servers.omnisharp then
  local omnisharp_config = vim.deepcopy(servers.omnisharp)
  omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
  require('lspconfig').omnisharp.setup(omnisharp_config)
end
```

### Option 2: Disable automatic_enable Globally

```lua
require('mason-lspconfig').setup {
  automatic_enable = false,  -- Disable vim.lsp.enable() for ALL servers
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

**Trade-off:** This disables automatic enabling for ALL servers, so you must configure every server explicitly.

## Verification

### 1. Check `:LspInfo` in Neovim

**Before fix:**
```
Client: omnisharp (id: 1)
  cmd: { "OmniSharp", "-z", "--hostPID", "12648", ... }
  settings: {
    RoslynExtensionsOptions = {}  ← EMPTY!
  }
```

**After fix:**
```
Client: omnisharp (id: 1)
  cmd: { "dotnet", "/home/.../.../OmniSharp.dll", "-s", "/mnt/c/.../Backend", "-loglevel", "Information", ... }
  settings: {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false
    }
  }
```

### 2. Check Running Process

```bash
ps aux | grep omnisharp | grep -v grep
```

**Before fix:**
```
dotnet /.../OmniSharp.dll -z --hostPID 12648 ...
```
- ❌ No `-s` (solution path)
- ❌ No `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

**After fix:**
```
dotnet /.../OmniSharp.dll -s /mnt/c/.../Backend -loglevel Information -z --hostPID 19758 ... RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
```
- ✅ `-s /mnt/c/.../Backend` present
- ✅ `RoslynExtensionsOptions:EnableAnalyzersSupport=true` present

## Common Pitfalls

### 1. Lua Bytecode Cache

**Problem:** Neovim caches compiled Lua files. Changes to init.lua may not apply.

**Fix:**
```bash
rm -rf ~/.cache/nvim/luac/
```

### 2. Multiple OmniSharp Processes

**Problem:** Old OmniSharp processes with old configuration still running.

**Fix:**
```bash
pkill -f omnisharp
```

### 3. Calling setup() Twice

**Problem:** `lspconfig[server].setup()` can only be called once per server. Second calls are ignored.

**Fix:** Use the skip pattern (Option 1 above) to ensure setup is only called once.

### 4. Settings with nil Values

**Problem:** nvim-lspconfig's default_config has settings like `EnableAnalyzersSupport = nil`. nil values don't get flattened into command-line args.

**Fix:** Explicitly set to `true` or `false` in your config:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- NOT nil!
  },
}
```

## Why This Happens

1. **mason-lspconfig v2.0+ (May 2025)** introduced `automatic_enable = true` by default
2. **`vim.lsp.enable()`** pre-configures servers BEFORE your handler runs
3. **OmniSharp gets default cmd** from Mason's wrapper: `~/.local/share/nvim/mason/bin/OmniSharp`
4. **Your handler's setup() call is ignored** because server is already configured
5. **Settings stay empty** because default_config uses `nil` values

## When to Use Each Option

| Scenario | Recommended Option |
|----------|-------------------|
| Only OmniSharp needs custom config | **Option 1** (Skip in handler) |
| Multiple servers need custom config | **Option 1** (Skip those servers) |
| All servers need custom config | **Option 2** (Disable automatic_enable) |
| Using Neovim 0.11+ | Consider migrating to `vim.lsp.config()` |

## Additional Resources

- Full analysis: `MASON_LSPCONFIG_OMNISHARP_ANALYSIS.md`
- Project documentation: `CLAUDE.md`
- nvim-lspconfig omnisharp.lua: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
