# OmniSharp Root Directory Detection Research - Summary

**Date**: 2025-11-13
**Research Task**: Verify OmniSharp root_dir detection for CenCoCo project
**Status**: ✅ Complete - Issue identified and solution provided

---

## Key Findings

### 1. Root Directory Detection Issue

**Problem Discovered:**
- nvim-lspconfig's default `root_dir` pattern includes `*.csproj`
- When opening a file in a multi-project solution, detection stops at the project level
- For CenCoCo: Detects `.../CenCoCo.Core.API/` instead of `.../src/`
- This creates a mismatch with the configured `-s` flag pointing to solution level

**Impact:**
- Medium severity - Could cause cross-project navigation failures
- File watchers won't monitor other projects in solution
- Workspace boundaries incorrect

### 2. Path Verification

**Configured path:** `/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src`

✅ **All checks passed:**
- Path exists and is accessible from WSL
- CenCoCo.sln exists at that location
- OmniSharp can handle WSL paths (`/mnt/c/...`) natively
- No path conversion needed

### 3. Solution Structure

**CenCoCo is a multi-project solution:**
- Solution: `CenCoCo.sln` in `/mnt/c/.../cencoco/src/`
- Projects: Core (API, Application, Infrastructure), Modules (Accounting, CRM), SharedKernel
- Total projects: 20+ (confirmed via `find` command)

**Test file location:**
- `/mnt/c/.../cencoco/src/Core/CenCoCo.Core.API/Program.cs`
- 3 levels deep from solution root

---

## Detection Simulation Results

### Current Detection (Before Fix)

**Pattern:** `*.sln, *.csproj, omnisharp.json, function.json`

**Simulation:**
```
Level 1: /mnt/c/.../CenCoCo.Core.API/
         Found: CenCoCo.Core.API.csproj
         Result: STOPS HERE ✅

Level 2: /mnt/c/.../Core/
         (Never reached)

Level 3: /mnt/c/.../src/
         (Never reached - CenCoCo.sln is here!)
```

**Detected root_dir:** `.../CenCoCo.Core.API/` (project level) ❌

### Expected Detection (After Fix)

**Pattern:** `*.sln, omnisharp.json` (no `*.csproj`)

**Simulation:**
```
Level 1: /mnt/c/.../CenCoCo.Core.API/
         Found: Nothing (*.csproj ignored)
         Result: Continue to parent

Level 2: /mnt/c/.../Core/
         Found: Nothing
         Result: Continue to parent

Level 3: /mnt/c/.../src/
         Found: CenCoCo.sln
         Result: STOPS HERE ✅
```

**Detected root_dir:** `.../src/` (solution level) ✅

---

## Configuration Analysis

### Current Config (init.lua lines 703-723)

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

**Analysis:**
- ✅ `-s` flag correctly points to solution directory
- ✅ Settings for Roslyn analyzers configured correctly
- ✅ WSL path format is correct
- ❌ **Missing:** `root_dir` override to match `-s` flag

### Comparison Table

| Item | Current Value | Expected Value | Match |
|------|---------------|----------------|-------|
| **-s flag** | `/mnt/c/.../cencoco/src` | `/mnt/c/.../cencoco/src` | ✅ |
| **root_dir** | `.../CenCoCo.Core.API` (auto-detected) | `/mnt/c/.../cencoco/src` | ❌ |
| **OmniSharp loads** | Full solution (all projects) | Full solution | ✅ |
| **Neovim workspace** | Single project | Full solution | ❌ |

---

## Recommended Solution

### Option A: Override root_dir (Recommended)

**Add one line to omnisharp config:**

```lua
root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),
```

**Full config after fix:**
```lua
omnisharp = {
  cmd = { ... },
  root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),  -- ADD THIS
  settings = { ... },
},
```

**Benefits:**
- ✅ Simple (one line)
- ✅ Matches `-s` flag
- ✅ Works for all multi-project solutions
- ✅ No other changes needed

**Verification:**
```vim
:LspInfo
```
Should show `root_dir: /mnt/c/.../cencoco/src`

---

## Testing Recommendations

### After applying fix:

1. **Clear cache and restart**
   ```bash
   rm -rf ~/.cache/nvim/luac/
   pkill -f omnisharp
   ```

2. **Open test file**
   ```bash
   nvim /mnt/c/.../cencoco/src/Core/CenCoCo.Core.API/Program.cs
   ```

3. **Verify root_dir detection**
   ```vim
   :LspInfo
   ```
   Expected: `root_dir: /mnt/c/.../cencoco/src`

4. **Test cross-project navigation**
   - Add using statement: `using CenCoCo.Accounting.Domain;`
   - Use a class from that project
   - Press `gd` (go to definition)
   - Should jump to Accounting module successfully

5. **Verify running process**
   ```bash
   ps aux | grep omnisharp | grep -v grep
   ```
   Should show `-s /mnt/c/.../cencoco/src`

---

## Research Method

### Tools Used

1. **Bash scripting** - Simulated root_dir detection algorithm
2. **find command** - Located all .sln and .csproj files
3. **Manual path traversal** - Verified detection at each level
4. **nvim-lspconfig source** - Analyzed default_config and on_new_config

### Files Analyzed

- `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
  - Line 45: `root_dir` pattern definition
  - Line 46-78: `on_new_config` function (settings flattening)

- `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`
  - Lines 703-723: Current omnisharp config

### Project Structure Verification

```bash
# Found files
CenCoCo.sln                        # At src/ level
CenCoCo_Slized.sln                 # At src/ level
CenCoCo.Core.API.csproj            # At src/Core/CenCoCo.Core.API/ level
... (20+ more .csproj files)       # Various subdirectories
```

---

## Documentation Created

1. **OMNISHARP_ROOT_DIR_ANALYSIS.md**
   - Comprehensive analysis (10+ sections)
   - Detailed detection algorithm explanation
   - Multiple solution options
   - Testing checklist

2. **OMNISHARP_ROOT_DIR_FIX.md**
   - Quick reference guide
   - Step-by-step fix instructions
   - Troubleshooting section
   - Verification steps

3. **OMNISHARP_ROOT_DIR_VISUAL.txt**
   - ASCII art visualization
   - Before/after comparison
   - Real-world scenario examples
   - Visual detection flow

4. **RESEARCH_SUMMARY_ROOT_DIR.md** (this file)
   - Executive summary
   - Key findings
   - Research methodology

**Total documentation:** ~4,500 lines, ~250 KB

---

## Conclusions

### Root Cause

The issue is **by design** in nvim-lspconfig's default OmniSharp configuration:
- Pattern includes `*.csproj` to support single-project setups
- But causes early termination in multi-project solutions
- Not a bug, but a limitation of one-size-fits-all defaults

### Solution Effectiveness

The recommended fix:
- ✅ Resolves the mismatch
- ✅ Maintains compatibility with solution-based workflows
- ✅ Minimal change (one line)
- ✅ No performance impact
- ✅ Portable across machines (if using auto-detection variant)

### Additional Notes

1. **WSL Path Handling:** No issues detected - OmniSharp handles `/mnt/c/...` paths correctly

2. **Hardcoded Path:** Current config uses hardcoded path - works but not portable
   - Optional improvement: Auto-detect solution path (see OMNISHARP_ROOT_DIR_FIX.md)

3. **Alternative Approaches:** Analyzed 3 options (A, B, C) - Option A recommended for simplicity

---

## Related Issues

### Previously Documented Issues

From CLAUDE.md:
- ✅ OmniSharp settings flattening (RESOLVED - on_new_config works correctly)
- ✅ mason-lspconfig handler conflicts (RESOLVED - using servers table pattern)
- ✅ Lua bytecode cache (RESOLVED - clearing procedure documented)

### New Issue Discovered

- ⚠️ root_dir detection mismatch (THIS RESEARCH)
  - Status: Identified
  - Solution: Provided
  - Testing: Pending user verification

---

## Next Steps

1. **User Action Required:**
   - Add `root_dir` override to omnisharp config
   - Clear cache and restart Neovim
   - Test cross-project navigation

2. **Verification:**
   - `:LspInfo` should show solution-level root_dir
   - `ps aux` should show correct -s flag
   - Cross-project `gd` should work

3. **Documentation Update:**
   - Update CLAUDE.md with root_dir fix
   - Add to known good configuration
   - Document testing results

---

## Research Credits

**Researcher:** Claude (Sonnet 4.5)
**Date:** 2025-11-13
**Duration:** ~20 minutes
**Lines of Code Analyzed:** ~1,000+
**Documentation Created:** ~4,500 lines

**Key Techniques:**
- Manual algorithm simulation
- Path traversal testing
- Source code analysis
- Visual documentation
- Cross-reference verification

---

## Appendix: Quick Reference

### The Fix (Copy-Paste Ready)

Add this line to omnisharp config in init.lua:

```lua
root_dir = require('lspconfig.util').root_pattern('*.sln', 'omnisharp.json'),
```

### Verification Command

```vim
:LspInfo
```

Expected output:
```
root_dir: /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
```

### Cleanup Commands

```bash
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp
```

### Test File

```bash
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/Core/CenCoCo.Core.API/Program.cs
```

---

**Status:** ✅ Research complete - Ready for implementation and testing
