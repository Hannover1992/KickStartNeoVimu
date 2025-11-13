# Why This OmniSharp Config Works (And Others Failed)

## The Working Pattern

```lua
-- In init.lua, around line 673:
local servers = {
  lua_ls = { ... },

  omnisharp = {
    cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', '-s', '/path/to/solution', '-loglevel', 'Information' },
    settings = {
      RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... },
      FormattingOptions = { EnableEditorConfigSupport = true, ... },
    },
  },
}

-- Later, mason-lspconfig (line 722-735):
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)  -- ✅ Automatically calls omnisharp.setup() with full config
    end,
  },
}
```

**Why this works:**
1. Config is in `servers` table
2. Handler reads `servers[server_name]` (gets your omnisharp config)
3. Handler calls `lspconfig.omnisharp.setup(server)` with your config
4. nvim-lspconfig's `on_new_config` automatically flattens settings to command-line args

## Failed Approach 1: Manual Setup After mason-lspconfig

```lua
-- ❌ DOES NOT WORK
require('mason-lspconfig').setup {
  handlers = { ... }  -- Default handler already calls omnisharp.setup() here
}

-- This runs AFTER, but setup() can only be called once!
require('lspconfig').omnisharp.setup {
  cmd = { ... },
  settings = { ... },
}
-- ❌ This call is IGNORED because omnisharp was already setup above
```

**Why it fails:**
- lspconfig.setup() can only be called **once** per server
- mason-lspconfig already called it (with default config)
- Your explicit call is silently ignored
- Result: Default cmd and empty settings

**Evidence from CLAUDE.md:**
> "The problem was that calling lspconfig.omnisharp.setup() multiple times doesn't work - only the first call takes effect."

## Failed Approach 2: Special Handler That Overwrites cmd

```lua
-- ❌ DOES NOT WORK
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      -- Default handler for all servers
    end,

    omnisharp = function()
      local server = servers.omnisharp or {}
      server.capabilities = ...
      server.cmd = { 'OmniSharp', '-z', '--languageserver' }  -- ❌ Overwrites your cmd!
      require('lspconfig').omnisharp.setup(server)
    end,
  },
}
```

**Why it fails:**
- The special handler REPLACES your carefully crafted `cmd`
- Missing `-s` (solution path)
- Settings exist but cmd is wrong
- nvim-lspconfig flattens settings, but without solution path, analyzers don't work properly

**Evidence from CLAUDE.md:**
> "The handler problem (lines 1036-1048): [...] This handler took config from servers.omnisharp, then REPLACED the cmd field entirely, removed the -s parameter and solution path."

## Failed Approach 3: Using Mason Wrapper Script

```lua
-- ❌ DOES NOT WORK RELIABLY
omnisharp = {
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),  -- ❌ Wrapper script
    '-s', '/path/to/solution',
    '-loglevel', 'Information',
  },
}
```

**Why it fails:**
- Mason's `OmniSharp` is a shell wrapper around `dotnet OmniSharp.dll`
- The wrapper may not pass all args correctly
- nvim-lspconfig's `on_new_config` expects to manipulate the cmd array directly
- Direct DLL call is more reliable

**Recommended:**
```lua
-- ✅ WORKS
cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', ... }
```

## Failed Approach 4: omnisharp.json Global Config

```json
// ~/.omnisharp/omnisharp.json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  }
}
```

**Why it's not ideal:**
- Global config affects ALL projects
- Hard to version control
- Not transparent (hidden in home directory)
- Can conflict with per-project settings
- Kickstart.nvim philosophy: "understand every line of your config"

**Recommended:**
- Use inline settings in init.lua (visible, version-controlled, project-specific)

## How nvim-lspconfig Flattens Settings

**nvim-lspconfig's omnisharp on_new_config (automatic):**
```lua
-- This happens automatically - you don't need to do anything!
local function flatten(tbl)
  local ret = {}
  for k, v in pairs(tbl) do
    if type(v) == 'table' then
      for _, pair in ipairs(flatten(v)) do
        ret[#ret + 1] = k .. ':' .. pair  -- Nested: "RoslynExtensionsOptions:EnableAnalyzersSupport"
      end
    else
      ret[#ret + 1] = k .. '=' .. vim.inspect(v)  -- Scalar: "loglevel=Information"
    end
  end
  return ret
end

vim.list_extend(new_config.cmd, flatten(new_config.settings))
```

**Your config:**
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  },
}
```

**Becomes:**
```bash
dotnet OmniSharp.dll -s /path -loglevel Information \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true  # ← Automatically appended!
```

## Key Insights from Research

### From GitHub Discussions (2024-2025)

**Working pattern found across multiple sources:**
1. Direct DLL call: `dotnet /path/to/OmniSharp.dll`
2. Solution path: `-s /path/to/solution` (critical for analyzers)
3. Settings in nested table: `RoslynExtensionsOptions = { ... }`
4. Let lspconfig flatten: Don't manually convert to command-line args

**From nvim-lspconfig source (omnisharp.lua):**
- `on_new_config` automatically adds: `-z`, `--hostPID`, `--encoding utf-8`, `--languageserver`
- You only need to provide: base cmd, solution path, loglevel, settings
- Don't duplicate hard-coded args (lspconfig adds them)

**From OmniSharp docs:**
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true` enables Roslyn analyzers
- Requires StyleCop.Analyzers NuGet package in project
- May take 10-30 seconds to analyze solution on first load

## Verification Checklist

**After adding config, verify:**

1. **:LspInfo shows correct cmd:**
   ```
   cmd: { "dotnet", "/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", "/mnt/c/.../Backend", "-loglevel", "Information", "-z", "--hostPID", "12345", "DotNet:enablePackageRestore=false", "--encoding", "utf-8", "--languageserver", "RoslynExtensionsOptions:EnableAnalyzersSupport=true", ... }
   ```

2. **ps aux shows all settings:**
   ```bash
   $ ps aux | grep omnisharp
   dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
     -s /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend \
     -loglevel Information \
     -z --hostPID 19758 DotNet:enablePackageRestore=false --encoding utf-8 --languageserver \
     RoslynExtensionsOptions:EnableAnalyzersSupport=true \
     RoslynExtensionsOptions:EnableImportCompletion=true \
     RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
     FormattingOptions:EnableEditorConfigSupport=true \
     FormattingOptions:OrganizeImports=true
   ```

3. **StyleCop warnings appear:**
   - Open C# file with known issues
   - Wait 10-20 seconds
   - See diagnostic warnings in sign column

## Summary: The Minimal Working Pattern

**Just 3 steps:**
1. Add omnisharp to `servers` table (with cmd and settings)
2. Let mason-lspconfig handler call setup automatically
3. nvim-lspconfig flattens settings to command-line args

**Total code: ~15 lines in servers table. No explicit setup. No special handlers. No global config files.**

**This works because:**
- Follows kickstart.nvim's design pattern
- Leverages nvim-lspconfig's built-in settings flattening
- One setup call (automatic, from handler)
- All config in one place (servers table)

**This is the pattern used in the working config documented in CLAUDE.md as "RESOLVED! ✅✅✅"**
