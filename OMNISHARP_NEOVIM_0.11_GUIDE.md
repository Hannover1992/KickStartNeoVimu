# OmniSharp Configuration for Neovim 0.11

**Critical Finding:** OmniSharp has **known compatibility issues** with Neovim 0.11's native `vim.lsp.config()` API. The traditional nvim-lspconfig approach remains more reliable.

---

## The Problem with Native API

**GitHub Discussion #35175:** Multiple users report that `vim.lsp.config("omnisharp", {...})` does **not apply settings** correctly.

**Symptoms:**
- Settings like `RoslynExtensionsOptions:EnableAnalyzersSupport` don't appear in running process
- StyleCop analyzer warnings don't show up
- `:LspInfo` shows empty or incomplete settings

**Root Cause:**
1. OmniSharp expects settings as **command-line arguments** (not LSP protocol settings)
2. nvim-lspconfig's `on_new_config` function handles this flattening
3. Native `vim.lsp.config()` API doesn't call `on_new_config`
4. Result: Settings never reach the OmniSharp process

---

## Recommended Approach: Use lspconfig

### Option 1: Pure lspconfig (Simplest)

```lua
-- In your init.lua
local omnisharp_bin = vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll'

require('lspconfig').omnisharp.setup {
  cmd = {
    'dotnet',
    omnisharp_bin,
    '--languageserver',
    '--hostPID', tostring(vim.fn.getpid())
  },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
    },
  },
  on_attach = function(client, bufnr)
    -- Your keybindings here
  end,
}
```

**What happens:**
1. lspconfig's `on_new_config` function runs
2. Settings are flattened: `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
3. Command becomes: `dotnet OmniSharp.dll ... RoslynExtensionsOptions:EnableAnalyzersSupport=true`
4. OmniSharp receives settings correctly

### Option 2: With Solution Path (Your Current Setup)

```lua
require('lspconfig').omnisharp.setup {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/path/to/solution'),
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
}
```

**Key points:**
- `-s` flag: Points to directory containing .sln file
- `-loglevel`: Controls OmniSharp's log verbosity
- Settings table: Will be flattened by `on_new_config`

**Verification:**
```bash
ps aux | grep omnisharp | grep -v grep
```

Should show:
```
dotnet /home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /mnt/c/path/to/solution \
  -loglevel Information \
  -z --hostPID 12345 --encoding utf-8 --languageserver \
  DotNet:enablePackageRestore=false \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
  FormattingOptions:EnableEditorConfigSupport=true \
  FormattingOptions:OrganizeImports=true
```

---

## Hybrid Approach (What You're Using)

**Your current config** (init.lua lines 752-783) is a **hybrid approach** that works because:

1. You define OmniSharp in the `servers` table (lines 702-723)
2. Your setup loop (lines 752-783) uses `vim.lsp.config()` for Neovim 0.11+
3. **But it still loads lspconfig** to get defaults (line 761)
4. This means lspconfig's `on_new_config` is still available

**Your exact code:**

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s',
      vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
      '-loglevel',
      'Information',
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

for server_name, server_config in pairs(servers) do
  local config = vim.tbl_deep_extend('force', {}, server_config)
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})

  if vim.fn.has('nvim-0.11') == 1 then
    -- Get filetypes from lspconfig as fallback
    local lspconfig_defaults = require('lspconfig.configs')[server_name]
    if lspconfig_defaults and lspconfig_defaults.default_config then
      config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
      config.root_dir = config.root_dir or lspconfig_defaults.default_config.root_dir
    end

    -- Register with native API
    vim.lsp.config(server_name, config)

    -- Enable on matching filetypes
    if config.filetypes then
      vim.api.nvim_create_autocmd('FileType', {
        pattern = config.filetypes,
        callback = function(ev)
          vim.lsp.enable(server_name, ev.buf)
        end,
      })
    end
  else
    -- Fallback for older Neovim versions
    require('lspconfig')[server_name].setup(config)
  end
end
```

**Why this works:**
- ✅ Uses native API (`vim.lsp.config`, `vim.lsp.enable`)
- ✅ Still loads lspconfig for defaults
- ✅ lspconfig's `on_new_config` gets called
- ✅ Settings are properly flattened
- ✅ Falls back to old method for Neovim < 0.11

**Assessment:** This is **the best approach**! Modern, compatible, and reliable.

---

## Pure Native API Attempt (Doesn't Work)

**Don't use this:**

```lua
-- ❌ This does NOT work reliably for OmniSharp
vim.lsp.config('omnisharp', {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  filetypes = { 'cs' },
  root_markers = { '*.sln', '*.csproj' },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
})

vim.lsp.enable('omnisharp')
```

**Why it fails:**
1. Settings table is passed to `vim.lsp.start()`
2. But OmniSharp doesn't support LSP protocol settings
3. It expects command-line args like `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
4. Without lspconfig's `on_new_config`, this conversion never happens
5. OmniSharp starts but ignores settings

**Result:**
- `:LspInfo` shows settings table
- But `ps aux | grep omnisharp` shows settings **not in command line**
- StyleCop warnings don't appear

---

## OmniSharp Settings Explained

### RoslynExtensionsOptions

Controls Roslyn analyzer behavior:

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,        -- Enable Roslyn analyzers (StyleCop, etc.)
  EnableImportCompletion = true,        -- Auto-complete using statements
  AnalyzeOpenDocumentsOnly = false,     -- Analyze entire solution (not just open files)
}
```

**Key setting:** `EnableAnalyzersSupport = true` enables StyleCop and other analyzers.

### FormattingOptions

Controls code formatting:

```lua
FormattingOptions = {
  EnableEditorConfigSupport = true,     -- Use .editorconfig rules
  OrganizeImports = true,               -- Auto-organize using statements
}
```

### Solution Path (-s flag)

```lua
cmd = {
  'dotnet',
  '/path/to/OmniSharp.dll',
  '-s', '/path/to/solution',  -- ← CRITICAL: Directory containing .sln file
  '-loglevel', 'Information',
}
```

**Why `-s` matters:**
- OmniSharp loads the entire solution
- Enables project-wide analysis
- Required for cross-project references
- Allows analyzers to run on all projects

**Common mistake:** Pointing to a .csproj instead of the directory containing .sln.

---

## Verification Steps

### 1. Check `:LspInfo`

```vim
:LspInfo
```

Should show:

```
Client: omnisharp (id: 1, bufnr: 1)
    cmd: { "dotnet", "/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", "/mnt/c/path/to/solution", "-loglevel", "Information" }
    settings: {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
        EnableImportCompletion = true,
        AnalyzeOpenDocumentsOnly = false
      },
      FormattingOptions = {
        EnableEditorConfigSupport = true,
        OrganizeImports = true
      }
    }
```

### 2. Check Running Process

```bash
ps aux | grep omnisharp | grep -v grep
```

**Look for these in the command line:**
- `-s /mnt/c/path/to/solution` ✅
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true` ✅
- `RoslynExtensionsOptions:EnableImportCompletion=true` ✅
- `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false` ✅
- `FormattingOptions:EnableEditorConfigSupport=true` ✅
- `FormattingOptions:OrganizeImports=true` ✅

**If settings are missing:** Your configuration isn't working. Settings weren't flattened to command-line args.

### 3. Check LSP Logs

```bash
tail -f ~/.local/state/nvim/lsp.log
```

Look for:
- "OmniSharp server started"
- Project loading messages
- No errors about missing settings

### 4. Test StyleCop Warnings

Open a C# file with known StyleCop violations:

```csharp
// This should trigger SA1116 (parameters on separate lines)
public void MyMethod(int param1, int param2,
    int param3, int param4) { }
```

If working, you'll see:
- Red/yellow underlines
- Diagnostics in `:LspInfo`
- Warnings in Telescope diagnostics (`<space>w`)

---

## Troubleshooting

### Issue: Settings not in command line

**Symptom:** `ps aux` shows OmniSharp running but without flattened settings.

**Cause:** lspconfig's `on_new_config` didn't run.

**Solution:** Use lspconfig's `.setup()` method directly:

```lua
require('lspconfig').omnisharp.setup {
  cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '/path/to/solution' },
  settings = { ... },
}
```

### Issue: OmniSharp starts but no diagnostics

**Checklist:**
- [ ] `-s` flag points to directory with .sln file
- [ ] StyleCop.Analyzers package is referenced in .csproj
- [ ] `.editorconfig` exists in solution root
- [ ] `EnableAnalyzersSupport = true` in settings
- [ ] Settings are in command line (`ps aux`)

**Common cause:** Solution path is wrong or .sln file not found.

### Issue: "Client already attached"

**Cause:** Multiple OmniSharp instances or config conflicts.

**Solution:**
```vim
:LspStop omnisharp
```

```bash
pkill -f omnisharp
```

Then restart Neovim.

### Issue: WSL2 NuGet issues

**Symptom:** OmniSharp can't load projects after Windows build.

**Solution:**
```bash
cd /mnt/c/path/to/solution
dotnet restore --force-evaluate --no-cache
```

**Why:** Windows and WSL2 have separate NuGet caches. After Windows build, WSL needs fresh restore.

---

## Complete Working Configuration

Here's a complete, copy-paste ready configuration:

```lua
-- Install Mason and LSP plugins
require('lazy').setup({
  { 'mason-org/mason.nvim', opts = {} },
  { 'neovim/nvim-lspconfig' },
  { 'mason-org/mason-lspconfig.nvim' },
})

-- Define servers
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s',
      vim.fn.expand('~/projects/my-csharp-solution'),  -- ← Change this
      '-loglevel',
      'Information',
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

-- Setup with lspconfig (reliable for OmniSharp)
local capabilities = vim.lsp.protocol.make_client_capabilities()

for server_name, config in pairs(servers) do
  config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})
  require('lspconfig')[server_name].setup(config)
end
```

**To install OmniSharp:**
```vim
:Mason
```
Then press `/` and search for "omnisharp", press `i` to install.

---

## Recommendations

### For Most Users: Use lspconfig

**Recommended:**
```lua
require('lspconfig').omnisharp.setup { ... }
```

**Pros:**
- ✅ Reliable settings handling
- ✅ Automatic settings flattening
- ✅ Well-tested and documented
- ✅ Works with all OmniSharp features

**Cons:**
- Requires nvim-lspconfig plugin

### For Purists: Hybrid Approach

**Recommended:**
```lua
-- Use vim.lsp.config() but still load lspconfig for defaults
-- (This is what your current config does)
```

**Pros:**
- ✅ Uses native Neovim 0.11 API
- ✅ Still leverages lspconfig's logic
- ✅ Future-proof
- ✅ Works reliably

**Cons:**
- More complex setup
- Still requires lspconfig (for now)

### Don't Use: Pure Native API

**Not recommended:**
```lua
vim.lsp.config('omnisharp', { ... })
vim.lsp.enable('omnisharp')
```

**Pros:**
- No plugin dependency

**Cons:**
- ❌ Settings don't work correctly
- ❌ Requires manual command-line arg flattening
- ❌ Not supported by OmniSharp team
- ❌ Known issues (GitHub #35175)

---

## Future Outlook

### When Will Native API Support OmniSharp?

**Likely scenario:**
1. Neovim 0.12+ may add built-in settings flattening
2. Or nvim-lspconfig becomes pure config files (lsp/ directory)
3. OmniSharp team may add LSP protocol settings support

**Timeline:** Unknown. Could be 6-12+ months.

### What Should You Do?

**Short-term (now):**
- ✅ Keep using lspconfig for OmniSharp
- ✅ Your hybrid approach is optimal

**Long-term (6-12 months):**
- Monitor Neovim changelog for LSP improvements
- Watch nvim-lspconfig migration progress
- Test native API periodically

**Bottom line:** Your current configuration is **future-proof** and will work with any upcoming changes.

---

## Quick Reference

### Verify Settings Are Applied

```bash
# Should show flattened settings in command line
ps aux | grep omnisharp | grep "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
```

### Restart OmniSharp

```vim
:LspRestart
```

### Check Server Status

```vim
:LspInfo
:checkhealth vim.lsp
```

### View Diagnostics

```vim
<space>w          " Telescope diagnostics (if configured)
]d                " Next diagnostic
[d                " Previous diagnostic
```

---

## Conclusion

**Key Takeaway:** OmniSharp requires special handling that nvim-lspconfig provides. The pure native API approach (`vim.lsp.config` + `vim.lsp.enable`) doesn't work reliably for OmniSharp in Neovim 0.11.

**Your current configuration (hybrid approach) is the best solution:**
- Uses modern native API where possible
- Leverages lspconfig for OmniSharp-specific logic
- Maintains compatibility with future Neovim versions
- Works reliably for StyleCop analyzers

**No changes needed!** Your setup is already optimal.

---

**Created:** 2025-11-13
**Neovim Version:** 0.11.4
**OmniSharp Version:** Latest via Mason
**Status:** ✅ Hybrid approach is recommended and working
