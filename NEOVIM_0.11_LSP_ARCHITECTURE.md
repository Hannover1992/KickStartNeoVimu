# Neovim 0.11 LSP Architecture: Old vs New API

**Date**: 2025-11-13
**Purpose**: Visual guide to understand the transition from lspconfig to native vim.lsp API

---

## Architecture Comparison

### Old Way: lspconfig (Neovim < 0.11)

```
┌─────────────────────────────────────────────────────────────────┐
│ User calls: require('lspconfig').omnisharp.setup({ ... })      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ lspconfig/configs.lua: __newindex()                             │
│ - Creates augroup 'lspconfig'                                   │
│ - Merges user config with default_config                        │
│ - IF autostart == true THEN:                                    │
│     ├─ Creates FileType autocmd for configured filetypes        │
│     └─ Callback: M.manager:try_add(bufnr)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ User opens file (e.g., Program.cs)                              │
│ Neovim fires: FileType event, pattern = 'cs'                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Autocmd callback executes: manager:try_add(bufnr)               │
│ - Validates buffer                                               │
│ - Finds root_dir (via root_dir function)                        │
│ - Calls make_config(root_dir)                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ make_config(root_dir)                                           │
│ - Clones user config                                            │
│ - Calls on_new_config(new_config, root_dir)  ← CRITICAL STEP   │
│   ├─ OmniSharp-specific: Flattens settings to CLI args         │
│   │   settings.RoslynExtensionsOptions.EnableAnalyzersSupport  │
│   │   → cmd: "RoslynExtensionsOptions:EnableAnalyzersSupport=true" │
│   └─ Returns transformed config                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ manager:add(root_dir, single_file, bufnr)                       │
│ - Calls vim.lsp.start(new_config)                               │
│ - OmniSharp process launched with FLATTENED settings in cmd     │
│ - Example cmd:                                                   │
│   { "dotnet", "/path/OmniSharp.dll", "-s", "/solution",        │
│     "RoslynExtensionsOptions:EnableAnalyzersSupport=true",     │
│     "FormattingOptions:OrganizeImports=true", ... }            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                    ✅ OmniSharp running with analyzers enabled
```

**Key Components:**
1. ✅ Automatic FileType autocmd creation
2. ✅ Manager system handles lifecycle
3. ✅ `on_new_config` transforms settings
4. ✅ Settings flattened to CLI args

---

### New Way: vim.lsp.config() (Neovim 0.11+)

```
┌─────────────────────────────────────────────────────────────────┐
│ User calls: vim.lsp.config('omnisharp', { ... })                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Neovim LSP Registry                                             │
│ - Stores config under name 'omnisharp'                          │
│ - Does NOT create autocmds                                      │
│ - Does NOT start server                                         │
│ - Does NOT call any hooks                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                    ⚠️ Config registered but INACTIVE

                            │
┌───────────────────────────┴─────────────────────────────────────┐
│ User MUST manually create FileType autocmd:                     │
│   vim.api.nvim_create_autocmd('FileType', {                     │
│     pattern = { 'cs' },                                          │
│     callback = function(ev)                                     │
│       vim.lsp.enable('omnisharp', ev.buf)  ← REQUIRED STEP      │
│     end,                                                         │
│   })                                                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ User opens file (e.g., Program.cs)                              │
│ Neovim fires: FileType event, pattern = 'cs'                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Autocmd callback executes: vim.lsp.enable('omnisharp', bufnr)  │
│ - Looks up config from registry                                 │
│ - Calls vim.lsp.start(config)                                   │
│ - ⚠️ NO on_new_config called                                    │
│ - ⚠️ Settings NOT flattened                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ vim.lsp.start() launches OmniSharp                              │
│ - Uses cmd AS-IS from config                                    │
│ - Example cmd:                                                   │
│   { "dotnet", "/path/OmniSharp.dll", "-s", "/solution",        │
│     "-loglevel", "Information" }                                │
│ - Settings table passed but IGNORED by OmniSharp                │
│ - ❌ RoslynExtensionsOptions:EnableAnalyzersSupport=true MISSING│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
               ❌ OmniSharp running WITHOUT analyzers enabled
```

**Key Differences:**
1. ❌ NO automatic FileType autocmd
2. ❌ NO manager system
3. ❌ NO `on_new_config` transformation
4. ❌ Settings NOT flattened to CLI args

---

## Problem Illustration: Settings Handling

### lspconfig Approach (WORKS)

```lua
-- User config
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
  },
  FormattingOptions = {
    OrganizeImports = true,
  },
}

-- After on_new_config transformation:
cmd = {
  "dotnet", "/path/OmniSharp.dll",
  "-s", "/solution",
  "-loglevel", "Information",
  -- ✅ Flattened settings appended:
  "RoslynExtensionsOptions:EnableAnalyzersSupport=true",
  "RoslynExtensionsOptions:EnableImportCompletion=true",
  "FormattingOptions:OrganizeImports=true",
}

-- OmniSharp receives settings via CLI args ✅
```

### vim.lsp.config() Approach (BROKEN)

```lua
-- User config
cmd = {
  "dotnet", "/path/OmniSharp.dll",
  "-s", "/solution",
  "-loglevel", "Information",
  -- ❌ No flattened settings
}

settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
  },
  FormattingOptions = {
    OrganizeImports = true,
  },
}

-- Passed to vim.lsp.start() AS-IS
-- OmniSharp launches with cmd only
-- Settings table ignored ❌
```

---

## Solution Options

### Option 1: Revert to lspconfig (Recommended)

**Pros:**
- Proven, stable, works out-of-box
- Automatic settings flattening
- Automatic autocmd creation
- Backward compatible

**Cons:**
- Doesn't use Neovim 0.11 native API
- Extra dependency (nvim-lspconfig plugin)

**Code:**
```lua
-- Remove vim.lsp.config() approach
-- Use this instead:
require('lspconfig').omnisharp.setup {
  cmd = { ... },
  settings = { ... },
}
```

### Option 2: Manual Settings Flattening

**Pros:**
- Uses native Neovim 0.11 API
- No external dependencies

**Cons:**
- Verbose, error-prone
- Must manually maintain CLI args

**Code:**
```lua
vim.lsp.config('omnisharp', {
  cmd = {
    'dotnet', '/path/OmniSharp.dll',
    '-s', '/solution',
    '-loglevel', 'Information',
    -- Manually flatten settings:
    'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
    'RoslynExtensionsOptions:EnableImportCompletion=true',
    'RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false',
    'FormattingOptions:EnableEditorConfigSupport=true',
    'FormattingOptions:OrganizeImports=true',
  },
  filetypes = { 'cs' },
})

vim.api.nvim_create_autocmd('FileType', {
  pattern = 'cs',
  callback = function(ev)
    vim.lsp.enable('omnisharp', ev.buf)
  end,
})
```

### Option 3: Use omnisharp.json Config File

**Pros:**
- Clean separation of concerns
- Standard OmniSharp configuration location
- Works with all editors (VS Code, Rider, Vim, Emacs)
- Simple Neovim config

**Cons:**
- Settings not in init.lua
- System-wide config (not project-specific)

**Code:**

**Step 1: Create `~/.omnisharp/omnisharp.json`:**
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

**Step 2: Minimal init.lua config:**
```lua
vim.lsp.config('omnisharp', {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/path/to/solution'),
    '-loglevel', 'Information',
    -- No settings needed - OmniSharp reads from ~/.omnisharp/omnisharp.json
  },
  filetypes = { 'cs' },
})

vim.api.nvim_create_autocmd('FileType', {
  pattern = 'cs',
  callback = function(ev)
    vim.lsp.enable('omnisharp', ev.buf)
  end,
})
```

---

## Comparison Table

| Feature | lspconfig | vim.lsp.config() | omnisharp.json |
|---------|-----------|------------------|----------------|
| Setup complexity | Low | Medium | Low |
| Settings handling | Automatic | Manual | Automatic |
| Maintainability | Easy | Hard | Easy |
| Neovim 0.11 native | No | Yes | Yes |
| Works with other editors | No | No | Yes |
| Project-specific config | Yes | Yes | No (system-wide) |
| Recommended for OmniSharp | ✅ Yes | ❌ No | ✅ Yes |

---

## Migration Path

### From lspconfig to vim.lsp.config()

**If you need to migrate** (not recommended for OmniSharp):

**Step 1: Add manual settings flattening**
```lua
local function flatten_omnisharp_settings(config)
  local cmd = vim.deepcopy(config.cmd)
  for section, options in pairs(config.settings or {}) do
    for key, value in pairs(options) do
      table.insert(cmd, string.format('%s:%s=%s', section, key, tostring(value)))
    end
  end
  return cmd
end
```

**Step 2: Apply before vim.lsp.config()**
```lua
local omnisharp_config = {
  cmd = { ... },
  settings = { ... },
  filetypes = { 'cs' },
}

omnisharp_config.cmd = flatten_omnisharp_settings(omnisharp_config)
vim.lsp.config('omnisharp', omnisharp_config)
```

**Step 3: Create autocmd**
```lua
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'cs',
  callback = function(ev)
    vim.lsp.enable('omnisharp', ev.buf)
  end,
})
```

---

## Best Practices

### For OmniSharp specifically:

1. **Use lspconfig** until Neovim 0.12+ has better OmniSharp support
2. **OR use omnisharp.json** for clean separation
3. **Avoid manual CLI arg construction** (error-prone)

### For other LSP servers (lua_ls, pyright, etc.):

1. **Native vim.lsp.config()** works fine (they use JSON config, not CLI args)
2. **Transition gradually** as Neovim 0.11+ matures

### General guidelines:

1. **Understand the API** you're using
2. **Test incrementally** (start minimal, add complexity)
3. **Check process cmd line** (`ps aux | grep omnisharp`) to verify
4. **Read LSP logs** (`~/.local/state/nvim/lsp.log`) for errors

---

## Common Pitfalls

### Pitfall 1: Assuming vim.lsp.config() == lspconfig.setup()

**They are NOT equivalent!**

| lspconfig.setup() | vim.lsp.config() |
|-------------------|------------------|
| Creates autocmds | Does NOT |
| Transforms settings | Does NOT |
| Starts server | Does NOT |
| Auto-detects root | Does NOT |

**Solution**: Understand the differences before migrating.

### Pitfall 2: Missing vim.lsp.enable() Call

**Symptom**: Config registered but LSP never starts.

**Cause**: `vim.lsp.config()` only registers, doesn't enable.

**Solution**: Always call `vim.lsp.enable()` in FileType autocmd.

### Pitfall 3: Settings Table Ignored

**Symptom**: Settings in config but not applied.

**Cause**: OmniSharp expects CLI args, not JSON.

**Solution**: Flatten settings to cmd OR use omnisharp.json.

### Pitfall 4: Wrong root_dir Signature

**Symptom**: root_dir function errors.

**Old signature (lspconfig)**:
```lua
root_dir = function(filename, bufnr)
  return vim.fs.dirname(vim.fs.find('.git', { path = filename, upward = true })[1])
end
```

**New signature (vim.lsp.config())**:
```lua
root_dir = function(client, bufnr)
  local filename = vim.api.nvim_buf_get_name(bufnr)
  return vim.fs.dirname(vim.fs.find('.git', { path = filename, upward = true })[1])
end
```

**Note**: Parameters changed from `(filename, bufnr)` to `(client, bufnr)`.

---

## Debugging Checklist

### When OmniSharp doesn't attach:

- [ ] Check Neovim version: `nvim --version`
- [ ] Check which API is used: `vim.lsp.config()` or `lspconfig.setup()`
- [ ] List autocmds: `:autocmd FileType cs`
- [ ] Check LSP info: `:LspInfo`
- [ ] Verify process: `ps aux | grep omnisharp`
- [ ] Check logs: `tail -f ~/.local/state/nvim/lsp.log`
- [ ] Verify settings flattened: Look for `RoslynExtensionsOptions:EnableAnalyzersSupport=true` in `ps` output

### When Settings Don't Work:

- [ ] Using lspconfig? (settings auto-flatten) ✅
- [ ] Using vim.lsp.config? (settings NOT flattened) ❌
- [ ] Settings in cmd as CLI args? ✅
- [ ] omnisharp.json exists? ✅

---

## Conclusion

**For OmniSharp in Neovim 0.11.4:**

1. **Best approach**: Use lspconfig (proven, stable)
2. **Alternative**: Use omnisharp.json (clean, standard)
3. **Avoid**: Manual vim.lsp.config() with settings flattening (complex, error-prone)

**General advice:**

The Neovim 0.11 LSP API is powerful but requires more manual setup. For servers with complex configurations like OmniSharp, stick with lspconfig until native support improves.

---

**Related Documents:**
- `FILETYPE_AUTOCMD_CONFLICT_ANALYSIS.md` - Complete root cause analysis
- `QUICK_FIX_GUIDE.md` - Step-by-step fix instructions
- `CLAUDE.md` - Historical context and working solutions

---

**End of Architecture Guide**
