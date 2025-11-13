# Mason-lspconfig OmniSharp Configuration Fix - START HERE

## What Is This?

This document provides the **definitive answer** to why mason-lspconfig overrides user OmniSharp configurations and how to fix it.

## Quick Navigation

### 1. For Users Who Just Want The Fix
→ **[OMNISHARP_CONFIG_QUICK_FIX.md](./OMNISHARP_CONFIG_QUICK_FIX.md)**
- Copy-paste solution (2 options)
- Verification commands
- Common pitfalls and fixes

**Time to fix:** 5 minutes

### 2. For Developers Who Want to Understand Why
→ **[MASON_LSPCONFIG_OMNISHARP_ANALYSIS.md](./MASON_LSPCONFIG_OMNISHARP_ANALYSIS.md)**
- Root cause analysis
- Configuration merge order
- Source code evidence
- Timeline of the bug

**Reading time:** 15 minutes

### 3. For Researchers
→ **[RESEARCH_SUMMARY.md](./RESEARCH_SUMMARY.md)**
- Research question and answer
- Key findings with diagrams
- Source code references
- Documentation gaps identified

**Reading time:** 10 minutes

## The Problem (One Sentence)

Mason-lspconfig v2.0+ (May 2025) calls `vim.lsp.enable()` automatically BEFORE user handlers run, pre-configuring OmniSharp with Mason's default wrapper cmd, causing user configurations to be silently ignored.

## The Solution (One Code Block)

### Option 1: Skip OmniSharp in Handler (Recommended)

```lua
require('mason-lspconfig').setup {
  handlers = {
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

## Verification

Run in Neovim:
```vim
:LspInfo
```

**Before fix:**
```
cmd: { "OmniSharp", "-z", "--hostPID", "12648", ... }
settings: { RoslynExtensionsOptions = {} }  ← EMPTY!
```

**After fix:**
```
cmd: { "dotnet", "/.../OmniSharp.dll", "-s", "/.../Backend", ... }
settings: { RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... } }  ← FILLED!
```

## Why This Matters

Without the fix:
- ❌ StyleCop analyzer warnings don't appear
- ❌ User cmd ignored (Mason wrapper used instead)
- ❌ User settings ignored (all nil values)
- ❌ Silent failure (no errors, just doesn't work)

With the fix:
- ✅ All LSP settings applied correctly
- ✅ Analyzer support enabled
- ✅ User cmd and settings respected
- ✅ Full control over configuration

## Key Insight

**lspconfig[server].setup() can only be called once per server.**

When mason-lspconfig's `vim.lsp.enable()` calls it first (with default config), your handler's call is silently ignored.

**Solution:** Skip the server in the handler, configure it explicitly afterwards.

## Files Overview

| File | Purpose | Audience |
|------|---------|----------|
| **OMNISHARP_CONFIG_QUICK_FIX.md** | Copy-paste solution | Users |
| **MASON_LSPCONFIG_OMNISHARP_ANALYSIS.md** | Technical deep-dive | Developers |
| **RESEARCH_SUMMARY.md** | Research findings | Researchers |
| **START_HERE_MASON_LSPCONFIG_FIX.md** | This file (navigation) | Everyone |

## Related Issues

This fix applies to:
- ✅ OmniSharp not showing StyleCop warnings
- ✅ User cmd being ignored (Mason wrapper used)
- ✅ Settings showing as empty in `:LspInfo`
- ✅ Solution path (-s) not being passed
- ✅ RoslynExtensionsOptions:EnableAnalyzersSupport=true not working

## Breaking Changes Timeline

- **May 2025:** mason-lspconfig v2.0 released
- **New:** `automatic_enable = true` by default
- **Impact:** User handlers run AFTER `vim.lsp.enable()`
- **Result:** User configs ignored (silent failure)

## Alternative Solutions

### Option 2: Disable automatic_enable Globally

```lua
require('mason-lspconfig').setup {
  automatic_enable = false,  -- Disable for ALL servers
  handlers = { ... },
}
```

**Trade-off:** Must configure ALL servers explicitly.

**When to use:**
- If you want full control over all servers
- If you have custom configs for many servers

## Additional Resources

### Official Documentation
- nvim-lspconfig omnisharp.lua: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
- mason-lspconfig v2.0 release: https://github.com/williamboman/mason-lspconfig.nvim/releases
- Neovim 0.11 vim.lsp.config: https://neovim.io/doc/user/lsp.html

### Project Documentation
- **CLAUDE.md:** Full debugging session (lines 1-1058)
- Contains complete chronological debugging history
- Shows multiple attempted fixes and their outcomes
- Final solution documented at lines 1030-1058

## Credits

**Research date:** November 13, 2025  
**Neovim version:** 0.11+  
**mason-lspconfig version:** 2.0+  
**Status:** ✅ Root cause identified and solution verified

---

**Next step:** Read [OMNISHARP_CONFIG_QUICK_FIX.md](./OMNISHARP_CONFIG_QUICK_FIX.md) for the copy-paste solution.
