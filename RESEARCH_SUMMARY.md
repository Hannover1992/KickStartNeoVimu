# Mason-lspconfig OmniSharp Configuration Research Summary

## Research Question

**Why does mason-lspconfig provide a DEFAULT cmd for omnisharp even when the user hasn't defined one, and how does this interact with user-provided configs?**

## Answer

Mason-lspconfig v2.0+ (May 2025) introduced `automatic_enable = true` by default, which calls `vim.lsp.enable()` for all Mason-installed servers. This pre-configures servers BEFORE user handlers run, causing user configurations to be ignored.

## Key Findings

### 1. The Configuration Merge Order

```
┌─────────────────────────────────────────────────────┐
│ 1. nvim-lspconfig default_config                   │
│    - cmd = nil                                       │
│    - settings with nil values                        │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 2. mason-lspconfig automatic_enable (NEW in v2.0+) │
│    - Calls vim.lsp.enable('omnisharp')              │
│    - Resolves cmd to Mason wrapper                  │
│    - cmd = { "OmniSharp", "-z", ... }               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 3. User handler runs (TOO LATE!)                   │
│    - Calls lspconfig.omnisharp.setup(user_config)   │
│    - ❌ IGNORED - server already configured         │
└─────────────────────────────────────────────────────┘
```

### 2. Where Default cmd Comes From

**Mason wrapper script:**
- Path: `~/.local/share/nvim/mason/bin/OmniSharp`
- Type: Shell script that calls `dotnet OmniSharp.dll`
- Added to $PATH by Mason

**When vim.lsp.enable() runs:**
1. Looks for `omnisharp` on $PATH
2. Finds Mason's wrapper
3. Sets cmd to `{ "OmniSharp" }`
4. nvim-lspconfig's `on_new_config` appends args: `-z`, `--hostPID`, etc.

### 3. Why User Settings Are Empty

**nvim-lspconfig's on_new_config flattens settings:**

```lua
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
```

**But:** This only works if settings are passed. When `vim.lsp.enable()` pre-configures OmniSharp, it uses default_config with nil values:

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = nil,  -- nil doesn't flatten!
  EnableImportCompletion = nil,
  AnalyzeOpenDocumentsOnly = nil,
}
```

**Result:** `:LspInfo` shows `RoslynExtensionsOptions = {}`

### 4. Why lspconfig.setup() Can Only Be Called Once

From nvim-lspconfig source (not explicitly documented):
- First call to `lspconfig[server].setup()` registers the config
- Subsequent calls are **silently ignored**
- No error, no warning - just doesn't apply

**This is the root cause of the problem!**

## The Solution

### Option 1: Skip in Handler (Recommended)

```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Skip - prevent vim.lsp.enable()
      end
      -- ... configure other servers
    end,
  },
}

-- Explicit setup AFTER mason-lspconfig
if servers.omnisharp then
  require('lspconfig').omnisharp.setup(servers.omnisharp)
end
```

### Option 2: Disable automatic_enable

```lua
require('mason-lspconfig').setup {
  automatic_enable = false,  -- Disable for ALL servers
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}
```

## Source Code Evidence

### nvim-lspconfig omnisharp.lua (lines 46-78)

```lua
on_new_config = function(new_config, _)
  -- Get the initially configured value of `cmd`
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- Append hard-coded command arguments
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- Flatten settings into command-line args
  if new_config.settings then
    vim.list_extend(new_config.cmd, flatten(new_config.settings))
  end
end
```

**Critical insight:** `on_new_config` receives `new_config.cmd` as input. If `vim.lsp.enable()` already set it to Mason's wrapper, user's cmd is never used.

### mason-lspconfig v2.0 Breaking Changes (May 2025)

From release notes:
- **Removed:** `handlers` setting and `setup_handlers()` function
- **New:** `automatic_enable = true` (default) - calls `vim.lsp.enable()` for Mason-installed servers
- **New API:** Uses Neovim 0.11's native `vim.lsp.config()` instead of lspconfig.setup()

**Impact:** User handlers still exist, but `vim.lsp.enable()` runs BEFORE them.

## Timeline of the Bug

1. **User defines servers.omnisharp** with custom cmd and settings ✅
2. **mason-lspconfig.setup() runs** with default handler ✅
3. **automatic_enable kicks in** → calls `vim.lsp.enable('omnisharp')` ❌
4. **vim.lsp.enable() resolves cmd** → finds Mason wrapper on $PATH ❌
5. **vim.lsp.enable() calls lspconfig.omnisharp.setup()** with default cmd ❌
6. **User handler runs** → calls lspconfig.omnisharp.setup(user_config) ❌
7. **Second setup() call is ignored** → user config never applied ❌
8. **Result:** OmniSharp uses Mason wrapper, no user settings

## Verification Commands

### Check `:LspInfo` Output

**Before fix:**
```
cmd: { "OmniSharp", "-z", "--hostPID", "12648", ... }
settings: { RoslynExtensionsOptions = {} }
```

**After fix:**
```
cmd: { "dotnet", "/.../OmniSharp.dll", "-s", "/.../Backend", "-loglevel", "Information", ... }
settings: { RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... } }
```

### Check Running Process

```bash
ps aux | grep omnisharp | grep -v grep
```

**Before fix:**
```
dotnet /.../OmniSharp.dll -z --hostPID 12648 DotNet:enablePackageRestore=false ...
```

**After fix:**
```
dotnet /.../OmniSharp.dll -s /mnt/c/.../Backend -loglevel Information -z --hostPID 19758 ... RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
```

## Key Lessons

1. **mason-lspconfig v2.0+ changed behavior** - `automatic_enable = true` by default
2. **vim.lsp.enable() pre-configures servers** - Runs before user handlers
3. **lspconfig.setup() only works once** - Second calls silently ignored
4. **Default cmd comes from Mason's $PATH** - Wrapper script, not user config
5. **nil settings don't flatten** - Must explicitly set `true`/`false`

## Documentation Gaps

These issues are NOT clearly documented:
- ❌ mason-lspconfig v2.0 breaking change impact on user handlers
- ❌ lspconfig.setup() can only be called once (silent failure)
- ❌ automatic_enable interaction with custom handlers
- ❌ How vim.lsp.enable() resolves cmd (uses $PATH, not user config)

## Recommendations

For OmniSharp and other servers needing custom config:
1. **Use Option 1** (skip in handler) for specific servers
2. **Or use Option 2** (disable automatic_enable) for all servers
3. **Clear Lua cache** when debugging: `rm -rf ~/.cache/nvim/luac/`
4. **Verify with ps aux** to ensure cmd is correct

## Files Generated

- `MASON_LSPCONFIG_OMNISHARP_ANALYSIS.md` - Full technical analysis
- `OMNISHARP_CONFIG_QUICK_FIX.md` - Quick fix guide
- `RESEARCH_SUMMARY.md` - This file (executive summary)

## References

- nvim-lspconfig omnisharp.lua: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
- mason-lspconfig v2.0 release: https://github.com/williamboman/mason-lspconfig.nvim/releases
- Neovim 0.11 vim.lsp.config docs: https://neovim.io/doc/user/lsp.html
- CLAUDE.md: Full debugging session documentation

---

**Research completed:** November 13, 2025  
**Neovim version:** 0.11+  
**mason-lspconfig version:** 2.0+  
**Status:** ✅ Root cause identified and solution verified
