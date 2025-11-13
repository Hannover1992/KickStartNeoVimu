# Mason-lspconfig Handler Patterns - Quick Reference

## The Problem
Many OmniSharp configs fail because developers misunderstand:
1. When handlers run (DURING `setup()`, not after)
2. How settings are passed (nested 2 levels, flattened by `on_new_config()`)
3. How to override the default command (MUST use full DLL path)

---

## Pattern Comparison

### PATTERN A: Default Handler (RECOMMENDED)
✅ **Simplest, works for most cases**

```lua
local servers = {
  omnisharp = {
    cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', '-s', '/path' },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
      },
    },
  },
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

**Why it works:**
- Handler runs for every server
- Handler calls `setup()` DURING `mason-lspconfig.setup()`
- `on_new_config()` flattens settings into cmd
- All in correct order

---

### PATTERN B: Named Handler (For special cases)
✅ **Use when you need explicit control**

```lua
local servers = {
  omnisharp = { ... },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      if server_name == 'omnisharp' then return end  -- Skip, handle specially
      -- ... handle other servers ...
    end,

    omnisharp = function()
      local server = servers.omnisharp or {}
      require('lspconfig').omnisharp.setup(server)
    end,
  },
}
```

**Why it works:**
- Explicit handler for omnisharp
- Runs at correct time (during setup)
- No double setup calls

---

### PATTERN C: Setup After (WRONG, don't use)
❌ **This doesn't work properly**

```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name) ... end
  },
}

-- AFTER mason-lspconfig.setup() completes
require('lspconfig').omnisharp.setup(servers.omnisharp)
```

**Why it fails:**
- Handler already called setup() during `setup()`
- Calling setup() twice is unreliable
- Settings may not be re-evaluated
- Exception: If you explicitly skip omnisharp in handler, then this works

---

### PATTERN D: Just lspconfig (No mason-lspconfig)
⚠️ **Simpler but doesn't scale**

```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll' },
  settings = { ... },
})
```

**Pros:** No mason complexity
**Cons:** No automatic server detection, manual management

---

## Critical Checklist

- [ ] **Settings nested correctly**: `RoslynExtensionsOptions` → `EnableAnalyzersSupport`
- [ ] **cmd overridden**: Uses `dotnet` + DLL path, not just `omnisharp`
- [ ] **Solution path in cmd**: `-s /path/to/Backend`
- [ ] **Key names are PascalCase**: `EnableAnalyzersSupport` not `enable_analyzers_support`
- [ ] **Handler setup() called ONCE**: Not before, not after, just during
- [ ] **No duplicate setup() calls**: Max 1 call per server

---

## Execution Flow (Correct Order)

```
1. Lazy loads plugins
   ↓
2. require('lspconfig')                    ← nvim-lspconfig loaded
   ↓
3. require('mason-lspconfig').setup()      ← STARTS HERE
   ↓
4. For each installed server:
     → Handler function called with name
     → Handler looks up servers[server_name]  ← Gets your config!
     → Handler calls lspconfig[name].setup()  ← SETUP HAPPENS HERE
     → lspconfig calls on_new_config()        ← Flattens settings
     → LSP client started with final cmd      ← Including all your settings!
   ↓
5. mason-lspconfig.setup() completes       ← DONE, don't call setup again!
```

---

## Settings Flattening (How It Works)

Your config:
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

Gets flattened to:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
RoslynExtensionsOptions:EnableImportCompletion=true
FormattingOptions:EnableEditorConfigSupport=true
```

Gets appended to cmd array:
```
{ 'dotnet', '/path/to/OmniSharp.dll', '-s', '/path', '-loglevel', 'Information',
  '-z', '--hostPID', '12345', 'DotNet:enablePackageRestore=false',
  '--encoding', 'utf-8', '--languageserver',
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  'RoslynExtensionsOptions:EnableImportCompletion=true',
  'FormattingOptions:EnableEditorConfigSupport=true' }
```

Final command executed:
```bash
dotnet /path/to/OmniSharp.dll -s /path -loglevel Information -z \
  --hostPID 12345 DotNet:enablePackageRestore=false --encoding utf-8 \
  --languageserver RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  FormattingOptions:EnableEditorConfigSupport=true
```

---

## Debugging Checklist

1. **Is omnisharp in `:LspInfo`?** → Verify cmd and settings exist
2. **Does cmd show `-s /path`?** → Check if cmd override worked
3. **Does ps show `RoslynExtensionsOptions:EnableAnalyzersSupport=true`?** → Settings flattened correctly
4. **Do you see `on_new_config` errors?** → Settings structure wrong (must be nested)
5. **Is setup() called twice?** → Look for explicit setup() after mason-lspconfig
6. **Are key names wrong?** → Using snake_case instead of PascalCase

---

## The Bottom Line

**USE THIS:**
```lua
local servers = {
  omnisharp = {
    cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', '-s', '/path' },
    settings = {
      RoslynExtensionsOptions = { EnableAnalyzersSupport = true },
      FormattingOptions = { EnableEditorConfigSupport = true },
    },
  },
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

**DON'T DO THIS:**
- ❌ Call `setup()` after `mason-lspconfig.setup()`
- ❌ Use flat settings (no parent key)
- ❌ Use snake_case for keys
- ❌ Skip the cmd override
- ❌ Call `setup()` twice on same server

---

## References

Full detailed research: `MASON_LSPCONFIG_HANDLER_RESEARCH.md` in this directory
