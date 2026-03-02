# OmniSharp Root Directory Detection Analysis for CenCoCo Project

**Date**: 2025-11-13
**Status**: ⚠️ ISSUE IDENTIFIED - root_dir mismatch detected

---

## Executive Summary

The current OmniSharp configuration for the CenCoCo project has a **root_dir detection mismatch** that could cause issues with workspace management and cross-project references.

**The Problem:**
- **Configured `-s` flag**: `/mnt/c/.../cencoco/src` (solution level) ✅ CORRECT
- **Detected `root_dir`**: `/mnt/c/.../cencoco/src/Core/CenCoCo.Core.API` (project level) ❌ WRONG

**Impact:** OmniSharp loads the full solution but Neovim thinks the workspace is only one project.

**Recommendation:** Add `root_dir` override to force solution-level detection.

---

## Project Structure

```
/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/
└── src/                                    ← Should be ROOT
    ├── CenCoCo.sln                        ← Solution file HERE
    ├── CenCoCo_Slized.sln
    ├── Core/
    │   └── CenCoCo.Core.API/              ← Currently detected as ROOT
    │       ├── CenCoCo.Core.API.csproj    ← Found first, stops here!
    │       └── Program.cs                 ← Test file location
    ├── Modules/
    │   ├── Accounting/
    │   └── CRM/
    └── SharedKernel/
```

---

## Root Directory Detection Algorithm

### How nvim-lspconfig Detects Root

From `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua` (line 45):

```lua
root_dir = util.root_pattern('*.sln', '*.csproj', 'omnisharp.json', 'function.json'),
```

**Detection Process:**
1. Start at file location: `.../CenCoCo.Core.API/Program.cs`
2. Check current directory for ANY pattern match
3. If found, STOP and return that directory as root
4. If not found, move to parent directory and repeat

**Patterns checked (in no particular priority):**
- `*.sln` - Solution file
- `*.csproj` - C# project file
- `omnisharp.json` - OmniSharp config
- `function.json` - Azure Functions config

### Detection Test Results

**Starting point:** `/mnt/c/.../cencoco/src/Core/CenCoCo.Core.API/Program.cs`

| Level | Directory | Files Found | Result |
|-------|-----------|-------------|--------|
| 1 | `.../CenCoCo.Core.API` | `CenCoCo.Core.API.csproj` | ✅ **STOPS HERE** |
| 2 | `.../Core` | (none) | ❌ Never reached |
| 3 | `.../src` | `CenCoCo.sln`, `CenCoCo_Slized.sln` | ❌ Never reached |

**Result:** `root_dir` = `.../CenCoCo.Core.API` (project level)

**Expected:** `root_dir` = `.../src` (solution level)

---

## Current Configuration (init.lua lines 703-723)

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

**What's Configured:**
- ✅ `-s` flag correctly points to `.../src` (solution directory)
- ✅ Settings for Roslyn analyzers configured
- ❌ **Missing:** `root_dir` override

---

## The Problem Explained

### Two Path Concepts in OmniSharp

OmniSharp uses TWO different path concepts that should normally match:

#### 1. Solution Path (`-s` flag)

**Purpose:** Tells OmniSharp which solution to load
**Current value:** `/mnt/c/.../cencoco/src`
**What it does:**
- Loads `CenCoCo.sln` from that directory
- Loads ALL projects referenced in the solution
- Enables cross-project references and navigation
- Used for compilation, analyzers, and IntelliSense

**Status:** ✅ CORRECT

#### 2. Root Directory (`root_dir` in lspconfig)

**Purpose:** Tells Neovim where the workspace root is
**Current value:** `/mnt/c/.../CenCoCo.Core.API` (auto-detected)
**What it does:**
- Determines workspace boundaries
- Used for relative path resolution in diagnostics
- Used for file watchers and change detection
- Defines LSP server scope

**Status:** ❌ WRONG (should be `.../src`)

### Why This Mismatch Matters

When `-s` flag and `root_dir` don't match:

| Issue | Impact | Severity |
|-------|--------|----------|
| **Cross-project navigation** | LSP might not recognize files in other projects | Medium |
| **Diagnostics paths** | File paths in errors might be wrong or confusing | Low |
| **Workspace management** | Neovim thinks workspace is smaller than it is | Medium |
| **File watchers** | Changes in other projects might not trigger updates | High |
| **Go to definition** | Jumping to code in other projects might fail | High |

**Real-world scenario:**
```csharp
// In CenCoCo.Core.API/Program.cs
using CenCoCo.Accounting.Domain;  // Reference to different project

// User presses 'gd' (go to definition) on AccountingContext
// Might fail or show error because Neovim thinks workspace is only Core.API
// Even though OmniSharp loaded the full solution!
```

---

## WSL Path Compatibility

### Path Verification

**Configured path:** `/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src`

| Check | Result |
|-------|--------|
| Path exists | ✅ YES |
| CenCoCo.sln exists | ✅ YES |
| Readable from WSL | ✅ YES |

### OmniSharp WSL Compatibility

OmniSharp.dll (running via `dotnet` in WSL) can handle:
- ✅ WSL paths (`/mnt/c/...`)
- ✅ Windows paths (`C:\...`)
- ✅ Mixed path separators

**No path conversion needed** - the configured path works correctly.

### Path Expansion

```lua
vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src')
```

`vim.fn.expand()` expands:
- `~` (home directory)
- Environment variables (`$VAR`)

Since the path is already absolute and has no variables, **expansion does nothing** - the path is passed as-is to OmniSharp.

---

## Solution Options

### Option A: Override root_dir (Recommended)

**Description:** Force root_dir detection to only look for `*.sln` files, ignoring `*.csproj`.

**Implementation:**
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
  root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),
  -- ^ Added: Only look for solution files, not project files
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
- ✅ Matches `-s` flag path
- ✅ Simple one-line addition
- ✅ Works for all multi-project solutions
- ✅ No need to change hardcoded path

**Drawbacks:**
- ⚠️ Might fail for solutions without `.sln` file (rare)

---

### Option B: Prioritize .sln but Fallback to .csproj

**Description:** Check for solution first, fallback to project if no solution found.

**Implementation:**
```lua
omnisharp = {
  cmd = { ... },
  root_dir = function(fname)
    local util = require('lspconfig.util')
    -- Try solution level first
    local sln_root = util.root_pattern('*.sln', 'omnisharp.json')(fname)
    if sln_root then
      return sln_root
    end
    -- Fallback to project level
    return util.root_pattern('*.csproj')(fname)
  end,
  settings = { ... },
},
```

**Benefits:**
- ✅ Prioritizes solution-level detection
- ✅ Still works for single-project setups
- ✅ More robust for edge cases

**Drawbacks:**
- ⚠️ More complex
- ⚠️ Fallback might still cause mismatch if project is outside solution

---

### Option C: Don't Override (Not Recommended)

**Description:** Keep current configuration, let root_dir detect project level.

**Why it might work:**
- OmniSharp still loads full solution (because of `-s` flag)
- Cross-project references might still work

**Why it's not recommended:**
- ❌ Workspace boundaries are wrong
- ❌ File watchers won't monitor other projects
- ❌ Confusing for debugging
- ❌ Potential issues with relative paths

---

## Recommended Fix

### Add root_dir Override to init.lua

**Location:** `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`
**Lines:** 703-723 (omnisharp config)

**Add this line:**
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
  root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),  -- Add this line
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

**After making this change:**
1. Clear cache: `rm -rf ~/.cache/nvim/luac/`
2. Kill OmniSharp: `pkill -f omnisharp`
3. Restart Neovim: `:qa!` and reopen

**Verify with:**
```vim
:LspInfo
```

Should show:
```
root_dir: /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
```

---

## Additional Improvements (Optional)

### Make Configuration Portable

**Problem:** Hardcoded path won't work on different machines.

**Solution:** Auto-detect solution from current working directory:

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
- ✅ Works on any machine
- ✅ No hardcoded paths
- ✅ Automatically finds solution

**Drawbacks:**
- ⚠️ More complex
- ⚠️ Might fail if opened from wrong directory

---

## Testing Checklist

After applying the fix:

- [ ] Restart Neovim and open `Program.cs`
- [ ] Run `:LspInfo` and verify root_dir is `.../src`
- [ ] Check running process: `ps aux | grep omnisharp` shows `-s /mnt/c/.../src`
- [ ] Test cross-project navigation:
  - [ ] Open file in Core.API project
  - [ ] Use a class from Accounting module
  - [ ] Press `gd` (go to definition)
  - [ ] Should jump to Accounting module successfully
- [ ] Test diagnostics:
  - [ ] Create an error (e.g., undefined variable)
  - [ ] Check if file path in diagnostic is correct
- [ ] Test file watching:
  - [ ] Modify a file in different project (outside WSL)
  - [ ] OmniSharp should detect the change

---

## Summary

| Item | Current State | Recommended State |
|------|---------------|-------------------|
| `-s` flag in cmd | `/mnt/c/.../cencoco/src` | ✅ No change needed |
| `root_dir` detection | Auto: `.../CenCoCo.Core.API` | Override: `.../src` |
| WSL path compatibility | ✅ Working correctly | ✅ No change needed |
| Configuration portability | ❌ Hardcoded path | ⚠️ Optional improvement |

**Action Required:** Add `root_dir` override to omnisharp config (one line change).

**Expected Result:** `root_dir` will match `-s` flag, both pointing to solution directory.

**Testing:** Verify with `:LspInfo` and test cross-project navigation.

---

## References

- **nvim-lspconfig omnisharp.lua**: `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
- **init.lua omnisharp config**: `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua` (lines 703-723)
- **CenCoCo solution**: `/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/CenCoCo.sln`
- **Test file**: `/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/Core/CenCoCo.Core.API/Program.cs`
