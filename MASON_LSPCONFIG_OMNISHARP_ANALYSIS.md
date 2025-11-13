# Mason-lspconfig OmniSharp Default Configuration Analysis

## Executive Summary

**Critical Finding:** Mason-lspconfig's default handler in the user's configuration was **NOT** using the `servers.omnisharp` table because of how the handler was structured. The default cmd came from **nvim-lspconfig's default_config** (which has `cmd = nil`), and mason-lspconfig's automatic `vim.lsp.enable()` feature was injecting a default wrapper cmd.

## Root Cause Analysis

### The Configuration Merge Order Problem

When using mason-lspconfig with handlers, the configuration merge happens in this order:

1. **nvim-lspconfig default_config** (cmd = nil, settings with nil values)
2. **User's servers.omnisharp config** (IF properly passed to handler)
3. **mason-lspconfig automatic cmd resolution** (via vim.lsp.enable() in Neovim 0.11+)

### The Problem in User's Config

Looking at the init.lua structure described in CLAUDE.md:

```lua
-- Lines 934-978: servers.omnisharp defined
local servers = {
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

-- Lines 1030-1044: mason-lspconfig setup with default handler
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}  -- ✅ This DOES access servers.omnisharp
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)  -- ✅ This SHOULD work
    end,
  },
}
```

**The handler IS correctly accessing `servers[server_name]`**, so why doesn't it work?

## The Real Problem: vim.lsp.enable() Override

### Mason-lspconfig v2.0+ Behavior (May 2025)

From mason-lspconfig v2.0.0 (released May 2025):

- **Breaking change:** Removed `handlers` setting and `setup_handlers()` function
- **New feature:** `automatic_enable = true` (default) - calls `vim.lsp.enable()` automatically
- **New API:** Uses Neovim 0.11's native `vim.lsp.config()` instead of lspconfig.setup()

### The Conflict

When `automatic_enable = true` (default), mason-lspconfig:

1. Detects OmniSharp is installed via Mason
2. Calls `vim.lsp.enable('omnisharp')` BEFORE your handler runs
3. This pre-configures OmniSharp with a default cmd (Mason's wrapper script)
4. Your handler's `lspconfig.omnisharp.setup()` call is **IGNORED** because the server is already enabled

### Why "OmniSharp" (Wrapper) Appears Instead of "dotnet" + DLL

Mason installs OmniSharp with:
- **Binary wrapper:** `~/.local/share/nvim/mason/bin/OmniSharp` (shell script)
- **DLL:** `~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll`

When `vim.lsp.enable('omnisharp')` runs without explicit cmd:
- It looks for `omnisharp` on $PATH
- Finds Mason's wrapper at `~/.local/share/nvim/mason/bin/OmniSharp`
- Uses `{ "OmniSharp" }` as the cmd
- nvim-lspconfig's `on_new_config` appends `-z`, `--hostPID`, etc.
- Final cmd: `{ "OmniSharp", "-z", "--hostPID", "12648", ... }`

**User's custom cmd never gets applied because vim.lsp.enable() ran first!**

## Why Settings Are Empty

The `on_new_config` function in nvim-lspconfig's omnisharp.lua flattens settings:

```lua
on_new_config = function(new_config, _)
  -- ... append hard-coded args ...

  -- Flatten settings into command-line args
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

**But:** This only works if `new_config.settings` is passed to `on_new_config`. When `vim.lsp.enable()` pre-configures the server, it uses nvim-lspconfig's default_config which has:

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = nil,  -- nil values!
    EnableImportCompletion = nil,
    AnalyzeOpenDocumentsOnly = nil,
  },
  -- ...
}
```

**nil values don't get flattened into command-line args!** That's why `:LspInfo` shows `RoslynExtensionsOptions = {}` (empty).

## The Solution (From CLAUDE.md)

The working solution was:

```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      -- Skip omnisharp - it will be configured explicitly after this setup
      if server_name == 'omnisharp' then
        return  -- ✅ Prevent automatic vim.lsp.enable()
      end
      -- ... default handler for other servers
    end,
  },
}

-- EXPLICIT OMNISHARP SETUP (after mason-lspconfig)
if servers.omnisharp then
  local omnisharp_config = vim.deepcopy(servers.omnisharp)
  omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
  require('lspconfig').omnisharp.setup(omnisharp_config)  -- ✅ Now this runs FIRST
  vim.notify('🔧 OmniSharp explicitly configured', vim.log.levels.INFO)
end
```

### Why This Works

1. **Handler returns early** for omnisharp → mason-lspconfig doesn't call `vim.lsp.enable('omnisharp')`
2. **Explicit setup runs** → `lspconfig.omnisharp.setup(servers.omnisharp)` is called with full config
3. **on_new_config runs** → Receives user's cmd and settings, flattens settings into args
4. **Final cmd is correct:**
   ```
   dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
     -s /mnt/c/.../Backend \
     -loglevel Information \
     -z --hostPID 19758 \
     DotNet:enablePackageRestore=false \
     --encoding utf-8 --languageserver \
     RoslynExtensionsOptions:EnableAnalyzersSupport=true \
     RoslynExtensionsOptions:EnableImportCompletion=true \
     RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
     FormattingOptions:OrganizeImports=true \
     FormattingOptions:EnableEditorConfigSupport=true
   ```

## Alternative Solution (Disable automatic_enable)

Another approach (not used by the user) would be:

```lua
require('mason-lspconfig').setup {
  automatic_enable = false,  -- ✅ Disable vim.lsp.enable() for ALL servers
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

This prevents mason-lspconfig from calling `vim.lsp.enable()` for any server, letting your handlers fully control configuration.

## Key Lessons

1. **mason-lspconfig v2.0+ uses vim.lsp.enable() by default** - This pre-configures servers before your handlers run
2. **lspconfig.setup() can only be called once** - Second calls are silently ignored
3. **vim.lsp.enable() uses default cmd** - It doesn't know about your custom cmd in `servers` table
4. **on_new_config flattens settings** - But only if settings are passed to it
5. **nil values in settings don't become command-line args** - Must explicitly set to `true`/`false`

## Timeline of the Bug

1. **Initial setup:** Default handler accessing `servers[server_name]` ✅ (correct)
2. **mason-lspconfig runs:** Calls `vim.lsp.enable('omnisharp')` ❌ (pre-configures with default cmd)
3. **Handler runs:** Calls `lspconfig.omnisharp.setup(servers.omnisharp)` ❌ (ignored - already configured)
4. **Result:** OmniSharp uses Mason wrapper cmd, no user settings applied
5. **Fix:** Handler returns early for omnisharp, explicit setup after mason-lspconfig ✅

## Verification

Check running OmniSharp process:
```bash
ps aux | grep omnisharp | grep -v grep
```

**Before fix:**
```
dotnet /home/.../OmniSharp.dll -z --hostPID 12648 DotNet:enablePackageRestore=false ...
```
- ❌ No `-s` (solution path)
- ❌ No `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

**After fix:**
```
dotnet /home/.../OmniSharp.dll -s /mnt/c/.../Backend -loglevel Information -z --hostPID 19758 ... RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
```
- ✅ `-s /mnt/c/.../Backend`
- ✅ `-loglevel Information`
- ✅ `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
- ✅ All user settings present

## References

- **nvim-lspconfig omnisharp.lua:** https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
- **mason-lspconfig v2.0 breaking changes:** May 2025 release notes
- **Neovim 0.11 vim.lsp.config/vim.lsp.enable:** Native LSP configuration API
- **CLAUDE.md:** Full documentation of the debugging process and solution
