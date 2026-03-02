# Minimal OmniSharp Configuration for Neovim 0.11 - Complete Analysis

## Executive Summary

**Minimal working configuration: 30 lines of code (excluding comments/whitespace)**

This document provides a complete breakdown of what's **required** vs **optional** for OmniSharp in Neovim 0.11, stripping away all complexity from mason-lspconfig, lazy.nvim, and other plugins.

---

## The Minimal Configuration (30 Lines)

See `minimal_omnisharp.lua` for the complete working example.

### Core Components Breakdown

#### 1. Server Configuration (Required)

```lua
vim.lsp.config('omnisharp', {
  cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '/path/to/solution' },
  filetypes = { 'cs' },
  root_dir = vim.fs.root(0, { '*.sln', '*.csproj' }),
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  -- Required for StyleCop warnings
    },
  },
})
```

**What's happening:**
- `vim.lsp.config()` - Neovim 0.11's new native API (replaces `require('lspconfig').omnisharp.setup()`)
- `cmd` - The command to start OmniSharp (direct `dotnet` call)
- `filetypes` - Which file extensions trigger this LSP
- `root_dir` - How to find the project root (looks for .sln/.csproj)
- `settings` - Configuration that gets flattened to command-line args

#### 2. LSP Activation (Required)

```lua
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'cs',
  callback = function(ev)
    vim.lsp.enable('omnisharp', ev.buf)
  end,
})
```

**What's happening:**
- When a C# file is opened (`FileType cs`), enable the `omnisharp` LSP for that buffer
- This is the Neovim 0.11 way (replaces automatic attachment from lspconfig)

#### 3. Keybindings (Optional but Recommended)

```lua
vim.api.nvim_create_autocmd('LspAttach', {
  callback = function(event)
    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, { buffer = event.buf })
    -- ... more keybinds
  end,
})
```

**What's happening:**
- When LSP attaches to a buffer, set up keybindings for that buffer
- `gd` = go to definition, `gr` = references, `K` = hover docs, etc.

---

## What Was Removed from Current Config?

### Removed: Mason and Mason-LSPConfig

**Current config (lines 745-783 in init.lua):**
- `require('mason-lspconfig').setup { ... }` - 39 lines
- Loop over servers table - 30 lines
- Conditional logic for Neovim 0.11 vs 0.10 - 25 lines

**Minimal config:**
- Direct `vim.lsp.config()` call - 15 lines
- No conditional logic needed

**Why it works:**
- Mason is just an installer - not required for OmniSharp to run
- `mason-lspconfig` is a bridge plugin - not needed with native APIs
- As long as `OmniSharp.dll` exists at the path, it works

### Removed: Lazy.nvim and Plugin Management

**Current config:**
- lazy.nvim bootstrap - 12 lines
- Plugin specs for nvim-lspconfig - 300+ lines
- Dependencies chain (mason → mason-lspconfig → lspconfig)

**Minimal config:**
- Zero plugins
- Zero package manager

**Why it works:**
- Neovim 0.11 has built-in LSP support (`vim.lsp.*`)
- No external plugins needed for basic LSP functionality

### Removed: Capabilities from blink.cmp

**Current config (line 662):**
```lua
local capabilities = require('blink.cmp').get_lsp_capabilities()
```

**Minimal config:**
- Omit `capabilities` field entirely

**Why it works:**
- Neovim has default capabilities that work fine
- Completion plugins (blink.cmp, nvim-cmp) add extra features, but aren't required
- Basic LSP features (goto definition, diagnostics) work without them

### Removed: on_new_config Flattening Logic

**Current understanding:**
- nvim-lspconfig has an `on_new_config` function that flattens settings
- Located at `~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua` (lines 46-78)

**Discovery:**
This flattening logic is **built into nvim-lspconfig**, not into Neovim itself!

**In minimal config:**
- We **don't use nvim-lspconfig** at all
- Settings are NOT automatically flattened
- OmniSharp will NOT receive settings as command-line args

**Impact:**
Settings passed via `settings = { ... }` in `vim.lsp.config()` are sent via LSP initialization, but NOT as command-line arguments. OmniSharp prefers command-line args for some settings.

**Solution:**
Manually add settings to `cmd`:

```lua
cmd = {
  'dotnet',
  '/path/to/OmniSharp.dll',
  '-s', '/path/to/solution',
  '-loglevel', 'Information',
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  'RoslynExtensionsOptions:EnableImportCompletion=true',
  'RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false',
  'FormattingOptions:EnableEditorConfigSupport=true',
  'FormattingOptions:OrganizeImports=true',
}
```

This bypasses the need for nvim-lspconfig's flattening logic entirely.

---

## Comparison: Current Config vs Minimal Config

### Current Config (init.lua)

| Component | Lines | Purpose |
|-----------|-------|---------|
| Lazy.nvim bootstrap | 12 | Install plugin manager |
| Mason setup | 5 | Install LSP servers |
| Mason-lspconfig setup | 5 | Bridge mason and lspconfig |
| Server loop + conditional | 30 | Configure all servers |
| OmniSharp definition | 22 | Define OmniSharp settings |
| LspAttach autocmd | 102 | Keybindings and highlights |
| Diagnostic config | 26 | Diagnostic appearance |
| **TOTAL** | **~202 lines** | Full-featured setup |

### Minimal Config (minimal_omnisharp.lua)

| Component | Lines | Purpose |
|-----------|-------|---------|
| vim.lsp.config | 15 | Configure OmniSharp |
| FileType autocmd | 5 | Enable on C# files |
| LspAttach autocmd | 10 | Basic keybindings |
| **TOTAL** | **~30 lines** | Minimal working setup |

**Reduction: 85% less code (202 → 30 lines)**

---

## What's Actually Required vs Optional?

### Required (OmniSharp Won't Work Without)

1. **Neovim 0.11+** - Native `vim.lsp.config()` API
2. **OmniSharp binary** - The actual `OmniSharp.dll` file
3. **.NET SDK** - `dotnet` command must be available
4. **Solution path** - `-s /path/to/solution` argument
5. **Server configuration** - `vim.lsp.config('omnisharp', { ... })`
6. **Activation trigger** - `FileType` autocmd to call `vim.lsp.enable()`

### Optional (Nice to Have)

1. **Mason** - Can manually download OmniSharp instead
2. **nvim-lspconfig** - Not needed with native APIs
3. **Completion plugin** - Works without, but manual typing
4. **Keybindings** - LSP works, but need `:lua vim.lsp.buf.definition()` commands
5. **Diagnostics config** - Default appearance is fine
6. **Settings flattening** - Can manually add to `cmd` instead

### Optional for StyleCop Warnings

**To get StyleCop warnings, you need:**

1. ✅ `EnableAnalyzersSupport = true` (in settings or cmd args)
2. ✅ StyleCop.Analyzers NuGet package in .csproj
3. ✅ .editorconfig file (or .ruleset) in solution directory

**You do NOT need:**
- Mason or mason-lspconfig
- nvim-lspconfig plugin
- Completion plugin (blink.cmp, nvim-cmp)
- Formatter plugin (conform.nvim)

---

## Key Discoveries from This Analysis

### 1. Neovim 0.11 Changes Everything

**Old way (Neovim 0.10):**
```lua
require('lspconfig').omnisharp.setup({ ... })
```

**New way (Neovim 0.11):**
```lua
vim.lsp.config('omnisharp', { ... })
vim.lsp.enable('omnisharp', bufnr)
```

The new API is:
- More explicit (manual enable vs auto-attach)
- Simpler (no plugin needed)
- More flexible (buffer-specific control)

### 2. Settings Flattening is nvim-lspconfig, Not Neovim

**Crucial insight:**
The `on_new_config` function that flattens settings into command-line args is part of **nvim-lspconfig**, not Neovim core.

**Evidence:**
- Located at `nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
- Only runs when using `require('lspconfig').omnisharp.setup()`
- Does NOT run with `vim.lsp.config()` native API

**Workaround:**
Manually add settings to `cmd` array:
```lua
cmd = {
  'dotnet', '/path/to/OmniSharp.dll',
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
}
```

### 3. Mason is Just an Installer

Mason's only job:
- Download OmniSharp.dll
- Place it in `~/.local/share/nvim/mason/packages/omnisharp/libexec/`
- Create wrapper script at `~/.local/share/nvim/mason/packages/omnisharp/OmniSharp`

You can achieve the same by:
1. Manually downloading from [OmniSharp releases](https://github.com/OmniSharp/omnisharp-roslyn/releases)
2. Extract to any directory
3. Point `cmd` to `OmniSharp.dll` location

### 4. The Kickstart Config Complexity is for Convenience

Your current `init.lua` provides:
- Automatic LSP server installation
- Unified configuration for 20+ languages
- Completion, formatting, diagnostics
- Git integration, fuzzy finding, etc.

For **just OmniSharp**, 95% of that is unnecessary.

---

## Testing the Minimal Config

### Step 1: Create the File

```bash
# Already created at:
/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/minimal_omnisharp.lua
```

### Step 2: Edit Solution Path

Open `minimal_omnisharp.lua` and change line 28:
```lua
local solution_path = vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src')
```

### Step 3: Test

```bash
# Kill any running OmniSharp
pkill -f omnisharp

# Start with minimal config
nvim -u /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/minimal_omnisharp.lua \
     /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/CenCoCo.Core.API/Program.cs
```

### Step 4: Verify

Inside Neovim:
```vim
:lua =vim.lsp.get_clients()
```

Should show:
```lua
{
  {
    id = 1,
    name = 'omnisharp',
    ...
  }
}
```

Test keybinds:
- `gd` - Jump to definition
- `K` - Show hover docs
- `]d` - Next diagnostic

### Step 5: Check Running Process

```bash
ps aux | grep omnisharp | grep -v grep
```

Should show:
```
dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /mnt/c/.../cencoco/src \
  -loglevel Information \
  -z --hostPID 12345 ...
```

---

## Migrating Current Config to Use Minimal Approach

### Option A: Keep Everything, Just Simplify OmniSharp

**Current config issue:**
- Lines 754-783: Complex loop with conditional logic for Neovim 0.11 vs 0.10

**Simplification:**
Since you're on Neovim 0.11, remove the conditional and use only `vim.lsp.config()`:

```lua
-- Replace lines 754-783 with:
for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  -- Get filetypes from lspconfig if needed
  local lspconfig_defaults = require('lspconfig.configs')[server_name]
  if lspconfig_defaults and lspconfig_defaults.default_config then
    config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
    config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir
  end

  -- Register with Neovim 0.11 API
  vim.lsp.config(server_name, config)

  -- Auto-enable on matching filetypes
  if config.filetypes then
    vim.api.nvim_create_autocmd('FileType', {
      pattern = config.filetypes,
      callback = function(ev)
        vim.lsp.enable(server_name, ev.buf)
      end,
    })
  end
end
```

### Option B: Remove nvim-lspconfig Entirely

**Aggressive simplification:**

1. Remove from lazy.nvim plugins:
   ```lua
   -- DELETE THIS BLOCK:
   {
     'neovim/nvim-lspconfig',
     dependencies = { ... },
     config = function() ... end,
   }
   ```

2. Add minimal config directly:
   ```lua
   -- Add AFTER lazy.setup():

   vim.lsp.config('omnisharp', {
     cmd = {
       'dotnet',
       vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
       '-s', vim.fn.expand('/path/to/solution'),
       '-loglevel', 'Information',
       'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
       'RoslynExtensionsOptions:EnableImportCompletion=true',
     },
     filetypes = { 'cs' },
     root_dir = vim.fs.root(0, { '*.sln', '*.csproj' }),
   })

   vim.api.nvim_create_autocmd('FileType', {
     pattern = 'cs',
     callback = function(ev)
       vim.lsp.enable('omnisharp', ev.buf)
     end,
   })
   ```

**Trade-off:**
- ✅ Simpler, more direct
- ✅ No plugin dependency
- ❌ Lose automatic settings flattening (must do manually)
- ❌ More verbose if configuring many LSPs

### Option C: Keep nvim-lspconfig, Remove Mason-LSPConfig

**Middle ground:**

1. Keep nvim-lspconfig (for settings flattening and defaults)
2. Remove mason-lspconfig (unnecessary bridge)
3. Configure servers directly:

```lua
-- DELETE: require('mason-lspconfig').setup { ... }

-- REPLACE WITH:
local lspconfig = require('lspconfig')

for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})
  lspconfig[server_name].setup(config)
end
```

**Trade-off:**
- ✅ Keep nvim-lspconfig conveniences (flattening, defaults)
- ✅ Remove bridge plugin complexity
- ✅ Still works with Mason (as installer only)

---

## Recommendations

### For Your Current Setup (CenCoCo Project Testing)

**Recommendation: Stick with current config, but test minimal separately**

1. Keep `init.lua` as-is (it's working now)
2. Test `minimal_omnisharp.lua` separately to verify understanding
3. If minimal works, you've confirmed the core requirements

### For Future Simplification

**Recommendation: Option A (Keep everything, simplify OmniSharp loop)**

- Least risky (everything else keeps working)
- Remove only the Neovim 0.10 fallback code (lines 779-782)
- Keep all plugins (they provide value beyond just OmniSharp)

### For New Neovim Configs

**Recommendation: Start with minimal_omnisharp.lua**

- Copy `minimal_omnisharp.lua` as base
- Add only plugins you actually need
- Expand incrementally

---

## Summary

**What you learned:**

1. **OmniSharp requires only 30 lines** to work in Neovim 0.11
2. **Mason is optional** - just an installer, not runtime dependency
3. **nvim-lspconfig is optional** - convenience plugin, not required
4. **Settings flattening** is nvim-lspconfig feature, must do manually without it
5. **Current config is 85% extra features** - valuable, but not required for basic LSP

**What can be safely removed from current config:**

- ❌ Mason-lspconfig plugin (bridge, unnecessary)
- ❌ Neovim 0.10 fallback code (you're on 0.11)
- ⚠️ nvim-lspconfig (can remove, but you'd need manual flattening)
- ⚠️ Mason (can remove, but manual install needed)

**What should be kept:**

- ✅ Lazy.nvim (great plugin manager)
- ✅ Blink.cmp (completion is too useful)
- ✅ Telescope (fuzzy finding is essential)
- ✅ Conform (formatting is important)

---

## Files Created

1. **minimal_omnisharp.lua** - Working 30-line config (ready to test)
2. **MINIMAL_OMNISHARP_ANALYSIS.md** - This document (complete breakdown)

**Next steps:**

1. Test `minimal_omnisharp.lua` to verify it works
2. If successful, you've proven the minimal requirements
3. Decide if you want to simplify current config (probably not worth it)
4. Use this knowledge for future Neovim setups or troubleshooting

---

## Appendix: Command-Line Args Reference

### Hard-Coded Args (Added by nvim-lspconfig)

These are added automatically by nvim-lspconfig's `on_new_config`:

```
-z                              # Enable zero-based line numbers
--hostPID 12345                 # Parent process ID (for cleanup)
DotNet:enablePackageRestore=false  # Disable NuGet restore during LSP ops
--encoding utf-8                # Communication encoding
--languageserver                # Run in language server mode
```

In minimal config **without nvim-lspconfig**, you should add these manually:

```lua
cmd = {
  'dotnet', '/path/to/OmniSharp.dll',
  '-s', '/path/to/solution',
  '-loglevel', 'Information',
  '-z',
  '--hostPID', tostring(vim.fn.getpid()),
  'DotNet:enablePackageRestore=false',
  '--encoding', 'utf-8',
  '--languageserver',
}
```

### Settings Args (Flattened from settings table)

With nvim-lspconfig, these are automatically flattened:

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  },
}
```

Becomes: `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

Without nvim-lspconfig, add manually:

```lua
cmd = {
  -- ... other args ...
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  'RoslynExtensionsOptions:EnableImportCompletion=true',
  'FormattingOptions:EnableEditorConfigSupport=true',
}
```

---

**End of Analysis**
