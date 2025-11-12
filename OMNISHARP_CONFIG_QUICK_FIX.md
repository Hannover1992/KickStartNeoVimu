# OmniSharp Configuration Quick Fix

## TL;DR - Copy-Paste Solution

Replace your current `omnisharp` configuration in `init.lua` with this:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll')
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.INFO)
    end,
  },
},
```

## Why This Works

### What Changed

| Old (Wrong) | New (Correct) | Reason |
|-------------|---------------|--------|
| `cmd = { '~/.local/.../bin/OmniSharp' }` | `cmd = { 'dotnet', '~/.../OmniSharp.dll' }` | Direct invocation is cleaner |
| `enable_roslyn_analyzers = true` | `settings = { RoslynExtensionsOptions = { EnableAnalyzersSupport = true } }` | Correct LSP setting name |
| `organize_imports_on_format = true` | *(removed)* | Not an OmniSharp setting |
| `enable_import_completion = true` | *(removed)* | Not an OmniSharp setting |
| `handlers = { ... }` | `handlers = { ... }` | ✅ Kept (optional logging) |

## Step-by-Step Fix

### 1. Find Your OmniSharp Config
Open `init.lua` and search for `omnisharp`:
```vim
/omnisharp
```

Should find something like this around line 1050-1060:
```lua
omnisharp = {
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  enable_roslyn_analyzers = true,
  -- ... etc
},
```

### 2. Replace Entire Block
Delete the current `omnisharp = { ... },` block and paste the corrected version:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll')
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.INFO)
    end,
  },
},
```

### 3. Save and Restart
```vim
:w                  " Save init.lua
:qa!                " Quit Neovim
```

### 4. Test in C# Project
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
nvim VDEK.DCSP.WebHost/Controllers/UserController.cs
```

### 5. Verify LSP Attached
```vim
:LspInfo
```

Should show:
```
Client: omnisharp (id: 1, bufnr: [1])
  root_dir: /mnt/c/.../DCSRE/Sources/Backend
  ...
```

### 6. Test Features
- `gd` on a method → Go to Definition ✅
- `K` on a class → Hover Documentation ✅
- `<leader>ca` → Code Actions ✅
- `grr` on a symbol → Find References ✅

## Troubleshooting

### If OmniSharp Still Doesn't Attach

**1. Kill existing processes:**
```bash
pkill -f omnisharp
```

**2. Clean NuGet cache (WSL2 cross-filesystem issue):**
```bash
cd /mnt/c/.../DCSRE/Sources/Backend
dotnet restore --force-evaluate --no-cache
```

**3. Restart Neovim:**
```bash
nvim VDEK.DCSP.WebHost/Controllers/UserController.cs
```

**4. Check logs:**
```vim
:LspLog
```

### If DLL Path Doesn't Exist

**Install OmniSharp via Mason:**
```vim
:Mason
# Navigate to omnisharp
# Press 'i' to install
# Wait for installation
# Restart Neovim
```

**Verify installation:**
```bash
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
```

### If dotnet Not Found

**Install .NET SDK:**
- Windows: https://dotnet.microsoft.com/download
- WSL2: `sudo apt install dotnet-sdk-9.0`

**Verify:**
```bash
dotnet --version
```

## What You Removed (and Why It's OK)

### `enable_roslyn_analyzers = true`
**Why removed:** This is NOT a valid OmniSharp LSP setting. The correct setting is:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- This is the real setting
  },
}
```

### `organize_imports_on_format = true`
**Why removed:** This is NOT an OmniSharp setting. Import organization is handled by:
- EditorConfig rules in your project
- StyleCop analyzers
- Format-on-save (already configured with conform.nvim)

### `enable_import_completion = true`
**Why removed:** This is NOT an OmniSharp setting. Import completion is automatically provided by:
- OmniSharp's built-in completion engine
- nvim-cmp integration

**Bottom line:** These settings did nothing. Removing them doesn't reduce functionality.

## What You Kept (and Why)

### `handlers['window/logMessage']`
**Kept because:** Optional but useful for debugging. Shows OmniSharp log messages in Neovim notifications.

**Example output:**
```
[OmniSharp] Loaded project: VDEK.DCSP.WebHost
[OmniSharp] Found 42 references
```

**To disable:** Simply remove the `handlers` section.

## Expected Behavior After Fix

### When Opening C# File

1. **Status line shows:** `OmniSharp` (LSP client name)
2. **`:LspInfo` shows:** Client attached with correct root_dir
3. **Diagnostics appear:** Red/yellow underlines for errors/warnings
4. **Completion works:** Start typing → suggestions appear
5. **Navigation works:** `gd`, `grr`, `K` all function correctly

### First Load (May Take 10-30 Seconds)

OmniSharp needs to:
- Find solution file (`.sln`)
- Load all projects
- Restore NuGet packages (if needed)
- Build Roslyn workspace
- Enable analyzers

**Be patient!** Subsequent loads are much faster (cached).

## Verification Checklist

After applying the fix, verify:

- [ ] `:LspInfo` shows `omnisharp` attached
- [ ] `gd` on a method jumps to definition
- [ ] `K` on a class shows documentation
- [ ] `<leader>ca` shows code actions
- [ ] `grr` on a symbol finds references
- [ ] Diagnostics appear (red/yellow underlines)
- [ ] Auto-completion works (start typing)
- [ ] Format on save works (`:w` formats code)

## Summary

**Problem:** OmniSharp configuration used incorrect cmd format and invalid settings.

**Solution:** Use direct `dotnet` + DLL invocation with correct LSP settings structure.

**Result:** OmniSharp attaches properly, all LSP features work.

**Files:**
- Configuration to apply: (copy-paste block above)
- Test script: `test_omnisharp_config.lua`
- Full explanation: `TEST_OMNISHARP_EXPLANATION.md`
- Test results: `TEST_RESULTS.md`
- Research details: `OMNISHARP_CMD_PARAMETER_ANALYSIS.md`

**Time to fix:** < 5 minutes (edit, save, restart, test)

---

*Based on Phase 1 research findings and verified with minimal configuration test.*
