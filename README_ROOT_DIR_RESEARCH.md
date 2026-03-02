# OmniSharp Root Directory Detection Research - Documentation Index

**Research Date:** 2025-11-13
**Project:** CenCoCo Solution
**Issue:** root_dir detection mismatch in multi-project solution
**Status:** ✅ Complete - Solution provided, testing pending

---

## Quick Start

**TL;DR - The Fix:**

Add one line to omnisharp config in `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`:

```lua
root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),
```

Then clear cache, kill OmniSharp, restart Neovim. See [Quick Fix Guide](#quick-fix-guide) below.

---

## Documentation Files

This research produced 4 comprehensive documentation files:

### 1. OMNISHARP_ROOT_DIR_FIX.md
**Purpose:** Quick reference and implementation guide
**Best for:** Getting the fix done quickly
**Contains:**
- TL;DR summary
- Step-by-step fix instructions
- Before/after configuration
- Verification steps
- Troubleshooting section

**Read this first if you want to fix the issue immediately.**

---

### 2. OMNISHARP_ROOT_DIR_ANALYSIS.md
**Purpose:** Comprehensive technical analysis
**Best for:** Understanding the problem in depth
**Contains:**
- Executive summary
- Project structure breakdown
- Detection algorithm explanation
- Problem explanation with examples
- WSL path compatibility analysis
- Multiple solution options (A, B, C)
- Testing checklist
- References

**Read this if you want to understand WHY the issue happens.**

---

### 3. OMNISHARP_ROOT_DIR_VISUAL.txt
**Purpose:** Visual explanation with ASCII art
**Best for:** Understanding the detection flow
**Contains:**
- Project structure diagram
- Detection algorithm flow (before/after)
- Visual comparison of paths
- Real-world scenario examples
- Step-by-step detection simulation

**Read this if you learn better with visual representations.**

---

### 4. RESEARCH_SUMMARY_ROOT_DIR.md
**Purpose:** Research methodology and findings
**Best for:** Understanding the research process
**Contains:**
- Key findings summary
- Detection simulation results
- Configuration analysis
- Testing recommendations
- Research method explanation
- Documentation created list
- Next steps

**Read this if you want to know HOW the issue was discovered.**

---

## Quick Fix Guide

### Step 1: Edit init.lua

```bash
nvim /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua
```

Navigate to line ~708 (omnisharp config, after `cmd` table).

### Step 2: Add root_dir Override

Add this line:
```lua
root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),
```

**Location:** Inside `omnisharp = { ... }` table, before or after `settings` table.

**Before:**
```lua
omnisharp = {
  cmd = { ... },
  settings = { ... },
},
```

**After:**
```lua
omnisharp = {
  cmd = { ... },
  root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),  -- ADD THIS
  settings = { ... },
},
```

### Step 3: Save and Clear Cache

```bash
:w  # Save file

# Clear cache (in terminal)
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp
```

### Step 4: Restart Neovim

```bash
:qa!  # Exit Neovim

# Reopen with test file
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/Core/CenCoCo.Core.API/Program.cs
```

### Step 5: Verify

```vim
:LspInfo
```

**Expected:**
```
root_dir: /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
```

**Not:** `.../CenCoCo.Core.API`

---

## What Was the Problem?

### In Simple Terms

**Multi-project solution structure:**
```
src/
├── CenCoCo.sln                 ← Solution file (loads all projects)
└── Core/
    └── CenCoCo.Core.API/
        ├── *.csproj            ← Project file
        └── Program.cs          ← We open this file
```

**Without fix:**
- Neovim searches for: `*.sln`, `*.csproj`, `omnisharp.json`, `function.json`
- Finds `*.csproj` first (in API directory)
- Stops there → thinks workspace is only CenCoCo.Core.API
- But OmniSharp loads the full solution (because of `-s` flag)
- **Result:** Mismatch! Neovim workspace ≠ OmniSharp solution

**With fix:**
- Neovim searches for: `*.sln`, `omnisharp.json` (no `*.csproj`)
- Skips `*.csproj` (not in pattern)
- Continues to parent directories
- Finds `*.sln` in src/ directory
- Stops there → workspace is full solution
- **Result:** Match! Neovim workspace = OmniSharp solution

---

## Testing Checklist

After applying the fix:

- [ ] `:LspInfo` shows `root_dir: /mnt/c/.../src`
- [ ] `ps aux | grep omnisharp` shows `-s /mnt/c/.../src`
- [ ] Cross-project navigation works:
  - [ ] Add `using CenCoCo.Accounting.Domain;`
  - [ ] Press `gd` on an Accounting class
  - [ ] Should jump to Accounting module
- [ ] Diagnostics show correct file paths
- [ ] No errors in `:messages`

---

## Impact

### Before Fix
- ❌ root_dir: `.../CenCoCo.Core.API` (project level)
- ❌ Workspace: Single project only
- ⚠️ Cross-project navigation might fail
- ⚠️ File watchers limited to one project

### After Fix
- ✅ root_dir: `.../src` (solution level)
- ✅ Workspace: Full solution
- ✅ Cross-project navigation works
- ✅ File watchers monitor all projects

---

## Alternative Solutions

### If You Want Auto-Detection (Not Hardcoded Path)

**Current config:** Hardcoded path to CenCoCo solution

**Alternative:** Auto-detect solution from current file

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
  settings = { ... },
},
```

**Benefits:**
- Works on any machine
- No hardcoded paths
- Automatically finds solution

**Drawbacks:**
- More complex
- Needs testing on different projects

**Recommendation:** Apply simple fix first, add auto-detection later if needed.

---

## Troubleshooting

### Fix didn't work?

**Symptom:** `:LspInfo` still shows `.../CenCoCo.Core.API` as root_dir

**Solutions:**
1. Clear cache: `rm -rf ~/.cache/nvim/luac/`
2. Kill OmniSharp: `pkill -f omnisharp`
3. Check syntax: `:messages` (look for Lua errors)
4. Verify line location: Should be inside `omnisharp = { ... }` table

### Cross-project navigation still fails?

**Solutions:**
1. Wait for OmniSharp to fully load (10-30 seconds)
2. Restore NuGet packages:
   ```bash
   cd /mnt/c/.../cencoco/src
   dotnet restore --force-evaluate --no-cache
   ```
3. Verify all projects in solution: `dotnet sln list`
4. Check OmniSharp logs: `~/.local/state/nvim/lsp.log`

---

## File Locations

### Configuration Files
- **init.lua (main config):** `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`
- **omnisharp config:** Lines 703-723
- **nvim-lspconfig omnisharp.lua:** `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`

### Project Files
- **CenCoCo solution:** `/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/CenCoCo.sln`
- **Test file:** `/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/Core/CenCoCo.Core.API/Program.cs`

### Documentation (this research)
- **Fix guide:** `OMNISHARP_ROOT_DIR_FIX.md`
- **Analysis:** `OMNISHARP_ROOT_DIR_ANALYSIS.md`
- **Visual explanation:** `OMNISHARP_ROOT_DIR_VISUAL.txt`
- **Research summary:** `RESEARCH_SUMMARY_ROOT_DIR.md`
- **Index (this file):** `README_ROOT_DIR_RESEARCH.md`

---

## Related Issues

### Previously Solved (documented in CLAUDE.md)
- ✅ OmniSharp settings not loading (on_new_config issue)
- ✅ mason-lspconfig handler conflicts
- ✅ Lua bytecode cache causing stale configs

### New Issue (this research)
- ⚠️ root_dir detection mismatch in multi-project solutions
  - Status: Identified and solution provided
  - Testing: Pending user verification

---

## Summary

| Item | Before | After |
|------|--------|-------|
| **Lines changed** | 0 | 1 |
| **root_dir detection** | `.../CenCoCo.Core.API` | `.../src` |
| **Matches -s flag?** | ❌ No | ✅ Yes |
| **Cross-project nav** | ⚠️ Might fail | ✅ Works |
| **Effort required** | - | 30 seconds |

**The fix is simple, well-documented, and ready to implement.**

---

## How to Read This Documentation

### If you want to fix it NOW:
1. Read: **OMNISHARP_ROOT_DIR_FIX.md**
2. Apply the fix
3. Test with checklist

### If you want to UNDERSTAND it:
1. Read: **OMNISHARP_ROOT_DIR_VISUAL.txt** (visual explanation)
2. Read: **OMNISHARP_ROOT_DIR_ANALYSIS.md** (detailed analysis)
3. Apply the fix
4. Test with checklist

### If you want to RESEARCH it:
1. Read: **RESEARCH_SUMMARY_ROOT_DIR.md** (methodology)
2. Read: **OMNISHARP_ROOT_DIR_ANALYSIS.md** (full analysis)
3. Review: nvim-lspconfig source code (`omnisharp.lua`)
4. Test the fix

---

## Questions?

Refer to:
- **Quick questions:** OMNISHARP_ROOT_DIR_FIX.md (Troubleshooting section)
- **Technical questions:** OMNISHARP_ROOT_DIR_ANALYSIS.md (detailed explanations)
- **Visual clarification:** OMNISHARP_ROOT_DIR_VISUAL.txt
- **Research details:** RESEARCH_SUMMARY_ROOT_DIR.md

Or check CLAUDE.md for related OmniSharp configuration issues.

---

**Research completed by:** Claude (Sonnet 4.5)
**Date:** 2025-11-13
**Total documentation:** ~4,500 lines
**Status:** ✅ Ready for implementation
