# nvim-lspconfig Settings & on_new_config - Quick Reference

**TL;DR:** Settings are automatically flattened by `on_new_config` callbacks into command-line arguments. Use `setup()` not `vim.lsp.config()`, nest settings properly, and use `vim.fn.expand()` for paths.

---

## 1. Settings Flattening - At a Glance

| Input | Output |
|-------|--------|
| `settings = { FormattingOptions = { TabSize = 4 } }` | Command arg: `FormattingOptions:TabSize=4` |
| `settings = { MsBuild = { Prerelease = true } }` | Command arg: `MsBuild:Prerelease=true` |

**How it works:**
1. User provides `settings` table
2. `on_new_config` callback flattens nested keys with colons
3. Flattened settings become command-line arguments
4. Final cmd passed to LSP server

---

## 2. on_new_config Callback - When & How

### When it's Called
```
Open C# file → Detect root_dir → Call on_new_config → Spawn LSP server
```

### What You Can Do
```lua
on_new_config = function(new_config, new_root_dir)
  -- Modify cmd array
  table.insert(new_config.cmd, '--my-arg')

  -- Modify settings
  new_config.settings = { ... }

  -- Modify capabilities
  new_config.capabilities.workspace.workspaceFolders = false
end
```

### Important: Modify new_config In-Place
```lua
-- ✅ Correct
new_config.settings.MyOption = true

-- ❌ Wrong (changes lost)
local settings = new_config.settings
settings.MyOption = true
```

---

## 3. Merge Strategies Quick Comparison

```lua
-- 'keep' strategy (nvim-lspconfig default)
local merged = vim.tbl_deep_extend('keep', user_config, defaults)
-- Result: User config wins, defaults fill in gaps

-- 'force' strategy (for capabilities)
local merged = vim.tbl_deep_extend('force', base, cmp_capabilities)
-- Result: Later arguments override earlier ones
```

**Use:**
- `'keep'` when merging with defaults (user takes precedence)
- `'force'` when merging capabilities (cmp overrides base)

---

## 4. Common Mistakes & Fixes

### Mistake 1: Wrong Setup Method
```lua
-- ❌ Wrong - on_new_config not called
vim.lsp.config('omnisharp', { settings = { ... } })

-- ✅ Right - on_new_config IS called
require('lspconfig').omnisharp.setup({ settings = { ... } })
```

### Mistake 2: Path Not Expanded
```lua
-- ❌ Wrong - Tilde is literal string
cmd = { "~/.local/share/nvim/mason/bin/OmniSharp" }

-- ✅ Right - Tilde is expanded
cmd = { vim.fn.expand("~/.local/share/nvim/mason/bin/OmniSharp") }
```

### Mistake 3: Settings at Top Level
```lua
-- ❌ Wrong - Settings lost
require('lspconfig').omnisharp.setup({
  TabSize = 4,
  EnableEditor = true,
})

-- ✅ Right - Settings nested
require('lspconfig').omnisharp.setup({
  settings = {
    FormattingOptions = { TabSize = 4 },
    SomeOption = true,
  }
})
```

### Mistake 4: Non-String in cmd
```lua
-- ❌ Wrong - Number not converted
cmd = { 'omnisharp', '--hostPID', vim.fn.getpid() }

-- ✅ Right - Converted to string
cmd = { 'omnisharp', '--hostPID', tostring(vim.fn.getpid()) }
```

### Mistake 5: Replacing on_new_config Entirely
```lua
-- ❌ Wrong - Loses automatic argument injection
require('lspconfig').omnisharp.setup({
  on_new_config = function(new_config, _)
    new_config.cmd = { 'omnisharp' }  -- Lost --languageserver, --hostPID, etc!
  end
})

-- ✅ Right - Extend existing behavior
local omnisharp_config = require('lspconfig.configs').omnisharp
require('lspconfig').omnisharp.setup({
  on_new_config = function(new_config, new_root_dir)
    omnisharp_config.on_new_config(new_config, new_root_dir)  -- Default first
    table.insert(new_config.cmd, '--my-custom-arg')           -- Then customize
  end
})
```

---

## 5. Debugging Checklist

**Settings not applied?**

- [ ] Using `setup()` not `vim.lsp.config()`?
- [ ] Settings nested in `settings` key?
- [ ] Paths use `vim.fn.expand("~")`?
- [ ] All cmd values are strings?
- [ ] :LspInfo shows server attached?
- [ ] :LspLog shows "initialized"?

**Quick test:**
```vim
:LspInfo              " Shows attached servers and cmd
:LspLog               " Shows LSP communication logs
:messages             " Shows notifications
```

---

## 6. Working Example

```lua
require('lspconfig').omnisharp.setup({
  -- Must be absolute path or use vim.fn.expand()
  cmd = {
    'dotnet',
    vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll')
  },

  -- Settings MUST be in 'settings' key, nested
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      TabSize = 4,
    },
    MsBuild = {
      IncludePrereleases = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },

  -- Optional: Custom on_new_config modifications
  on_new_config = function(new_config, new_root_dir)
    -- Default behavior is handled automatically
    -- You can add custom logic here if needed
    if vim.fn.filereadable(new_root_dir .. '/DEBUG') then
      table.insert(new_config.cmd, '--debug')
    end
  end,
})
```

---

## 7. How Settings Flow Through the System

```
User Configuration (init.lua)
    ↓
Merge with defaults (vim.tbl_deep_extend 'keep')
    ↓
on_new_config callback
    ├─ Flatten settings → command arguments
    ├─ Modify cmd array
    └─ Modify capabilities
    ↓
Final cmd passed to spawn process
    ↓
LSP Server receives settings
```

---

## 8. When to Use What

| Scenario | Solution |
|----------|----------|
| Changing settings options | Modify `settings` table |
| Adding LSP arguments | Add in `on_new_config` to `cmd` array |
| Changing server capabilities | Modify `new_config.capabilities` in `on_new_config` |
| Conditional setup | Use `on_new_config` with logic based on `new_root_dir` |
| Merging with cmp completion | Use `vim.tbl_deep_extend('force', base, cmp.capabilities())` |

---

## 9. Neovim 0.11 Note

**on_new_config Status:** Currently missing in native `vim.lsp.config()` API

**Options:**
1. Continue using nvim-lspconfig for servers that need `on_new_config`
2. Use function-based `root_dir` for dynamic configuration
3. Wait for implementation in Neovim core

```lua
-- Workaround: dynamic root_dir
root_dir = function(fname)
  -- Can perform custom logic here
  -- More flexible than just returning a path
end
```

---

## 10. One-Liner Fixes

| Problem | Fix |
|---------|-----|
| "No LSP attached" | Use `require('lspconfig').server.setup()` not `vim.lsp.config()` |
| "Settings ignored" | Move to `settings = { ... }` key |
| "Path not found" | Change `"~/.../bin"` to `vim.fn.expand("~/.../bin")` |
| "Duplicate arguments" | Remove manual `--languageserver` etc, let `on_new_config` add them |
| "Type error in cmd" | Wrap numbers with `tostring()` |

---

## References

- **Full Research:** `/NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md`
- **GitHub:** https://github.com/neovim/nvim-lspconfig
- **OmniSharp Config:** `lua/lspconfig/configs/omnisharp.lua`

---

**Last Updated:** November 12, 2025
