# OmniSharp Root Directory Fix - Quick Reference

**Date**: 2025-11-13
**Issue**: root_dir mismatch between detected path and configured -s flag
**Severity**: Medium - Could cause cross-project navigation issues

---

## TL;DR

**Problem:** OmniSharp loads full solution but Neovim thinks workspace is only one project.

**Fix:** Add one line to omnisharp config in init.lua

**Line to add:**
```lua
root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),
```

---

## What's Wrong

**Current behavior:**
- When you open `Program.cs` in CenCoCo.Core.API project
- nvim-lspconfig detects root as: `.../CenCoCo.Core.API` (project level)
- Because it finds `CenCoCo.Core.API.csproj` first
- But OmniSharp is configured to load: `.../src` (solution level)
- Result: **Mismatch!**

**Why it matters:**
- Cross-project "go to definition" might fail
- File watchers won't monitor other projects
- Workspace boundaries are wrong

---

## The Fix

### Location
**File:** `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`
**Lines:** Around 703-723 (omnisharp config)

### Before
```lua
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
```

### After
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s',
    vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
    '-loglevel',
    'Information',
  },
  root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),  -- ADD THIS LINE
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
```

---

## Apply the Fix

### Step 1: Edit init.lua
```bash
nvim /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua
```

Navigate to line ~708 (after cmd table, before settings table).

Add:
```lua
root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),
```

Save: `:w`

### Step 2: Clear Cache and Restart
```bash
# Clear Lua bytecode cache
rm -rf ~/.cache/nvim/luac/

# Kill OmniSharp process
pkill -f omnisharp

# Exit Neovim
:qa!

# Reopen Neovim with a C# file
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/Core/CenCoCo.Core.API/Program.cs
```

---

## Verify the Fix

### Check 1: LspInfo
```vim
:LspInfo
```

**Expected:**
```
root_dir: /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
```

**Not:** `.../CenCoCo.Core.API`

### Check 2: Running Process
```bash
ps aux | grep omnisharp | grep -v grep
```

**Expected:**
```
-s /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
```

Should see the full solution path.

### Check 3: Cross-Project Navigation

1. Open `Program.cs`
2. Add a using statement for another project:
   ```csharp
   using CenCoCo.Accounting.Domain;
   ```
3. Use a class from that project
4. Press `gd` (go to definition)
5. **Should jump to the Accounting project** (not show error)

---

## What This Does

**Before fix:**
- nvim-lspconfig searches for: `*.sln`, `*.csproj`, `omnisharp.json`, `function.json`
- Finds `CenCoCo.Core.API.csproj` first (project level)
- Stops there → root_dir = `.../CenCoCo.Core.API`

**After fix:**
- nvim-lspconfig searches for: `*.sln`, `omnisharp.json` only
- Skips `CenCoCo.Core.API.csproj` (not in pattern)
- Continues to parent directories
- Finds `CenCoCo.sln` → root_dir = `.../src`

**Result:** root_dir matches -s flag (both point to solution directory)

---

## Troubleshooting

### Fix didn't work?

**Symptom:** `:LspInfo` still shows `.../CenCoCo.Core.API` as root_dir

**Possible causes:**
1. Cache not cleared
   ```bash
   rm -rf ~/.cache/nvim/luac/
   ```

2. OmniSharp still running
   ```bash
   pkill -f omnisharp
   ```

3. Syntax error in init.lua
   ```vim
   :messages
   ```
   Check for Lua errors

4. Line not in correct location
   - Should be inside `omnisharp = { ... }` table
   - Before or after `settings` table (doesn't matter)
   - NOT inside `cmd` or `settings` tables

### Cross-project navigation still fails?

**Possible causes:**
1. OmniSharp hasn't loaded the full solution yet (wait 10-30 seconds)
2. NuGet restore needed:
   ```bash
   cd /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
   dotnet restore --force-evaluate --no-cache
   ```
3. Project not in solution:
   ```bash
   dotnet sln list
   ```
   Verify all projects are included

---

## Why This Matters for CenCoCo

**CenCoCo Solution Structure:**
```
src/
├── CenCoCo.sln                    ← Solution file (references all projects)
├── Core/
│   ├── CenCoCo.Core.API
│   ├── CenCoCo.Core.Application
│   └── CenCoCo.Core.Infrastructure
├── Modules/
│   ├── Accounting/
│   │   ├── CenCoCo.Accounting.API
│   │   ├── CenCoCo.Accounting.Application
│   │   └── CenCoCo.Accounting.Domain
│   └── CRM/
│       ├── CenCoCo.CRM.Api
│       └── CenCoCo.CRM.Application
└── SharedKernel/
```

**Without fix:**
- root_dir = `.../Core.API` (only one project)
- OmniSharp loads all projects (because of -s flag)
- But Neovim doesn't know about other projects
- Cross-module navigation might fail

**With fix:**
- root_dir = `.../src` (all projects)
- OmniSharp loads all projects (because of -s flag)
- Neovim knows about all projects
- Cross-module navigation works correctly

---

## Alternative: Auto-Detect Solution Path (Optional)

If you want the configuration to work on any machine (not hardcoded):

```lua
omnisharp = {
  root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),
  cmd = function()
    local util = require('lspconfig.util')
    local root = util.root_pattern('*.sln', 'omnisharp.json')(vim.api.nvim_buf_get_name(0))
    return {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s',
      root or vim.fn.getcwd(),
      '-loglevel',
      'Information',
    }
  end,
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
```

**Benefits:**
- Works on any machine
- No hardcoded paths

**Drawbacks:**
- More complex
- Needs testing

**Recommendation:** Stick with simple fix first, add auto-detection later if needed.

---

## Summary

| Item | Before | After |
|------|--------|-------|
| root_dir pattern | `*.sln`, `*.csproj`, ... | `*.sln`, `omnisharp.json` only |
| Detected root_dir | `.../CenCoCo.Core.API` | `.../src` |
| Matches -s flag? | ❌ No | ✅ Yes |
| Cross-project nav | ⚠️ Might fail | ✅ Works |
| Lines changed | 0 | 1 |

**Action:** Add `root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),` to omnisharp config.

**Verification:** `:LspInfo` should show root_dir as `.../src` (solution directory).

---

## Full Documentation

For detailed analysis, see: `OMNISHARP_ROOT_DIR_ANALYSIS.md`
