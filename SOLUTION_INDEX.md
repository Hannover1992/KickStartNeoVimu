# OmniSharp StyleCop Solution - Complete Documentation Index

**Research Completed:** November 12, 2025
**Problem:** StyleCop warnings not appearing in Neovim, RoslynExtensionsOptions showing as empty
**Status:** ✅ Root cause identified, solution provided

---

## Quick Start (Choose Your Path)

### I Just Want to Fix It (5 minutes)
Read: **`QUICK_FIX_GUIDE.md`**
- Copy/paste the fixed config
- Run 4 commands
- Restart Neovim
- Done!

### I Want to Understand What's Wrong
Read: **`PROBLEM_SOLUTION_DIAGRAM.md`**
- Visual diagrams of problem vs solution
- Flow charts showing configuration paths
- Before/after comparisons
- Why omnisharp.json is better

### I Need Complete Implementation Details
Read: **`FINAL_SOLUTION.md`**
- Full root cause analysis
- Step-by-step fix procedures
- Verification checklist
- Troubleshooting guide
- Fallback options

---

## Document Overview

### 1. QUICK_FIX_GUIDE.md (4 KB)
**Best for:** Getting it working ASAP

**Contents:**
- 5-minute fix procedure
- Exact code to copy/paste
- Verification steps
- Basic troubleshooting

**Use when:** You trust the solution and just want it to work.

---

### 2. PROBLEM_SOLUTION_DIAGRAM.md (19 KB)
**Best for:** Understanding the problem visually

**Contents:**
- ASCII diagrams showing problem flow
- Before/after configuration comparison
- Root cause chain visualization
- Configuration flow charts
- Testing procedures

**Use when:** You want to understand WHY it was broken and HOW the fix works.

---

### 3. FINAL_SOLUTION.md (19 KB)
**Best for:** Complete implementation and troubleshooting

**Contents:**
- **Section 1:** Why RoslynExtensionsOptions shows empty
- **Section 2:** Why StyleCop warnings don't appear
- **Section 3:** Exact fix steps (Solution A & B)
- **Section 4:** Pre-restart checklist
- **Section 5:** Restart procedure
- **Section 6:** Post-restart verification
- **Section 7:** Troubleshooting guide
- **Section 8:** Fallback plans
- **Section 9:** Root causes summary
- **Section 10:** Expected timeline
- **Section 11:** Key takeaways
- **Section 12:** References

**Use when:** You need comprehensive details or encounter issues during implementation.

---

## Background Research Documents

These documents were created during Phase 1 (Haiku) and Phase 2 (Sonnet) research:

### nvim-lspconfig Research
- `OMNISHARP_CMD_PARAMETER_ANALYSIS.md` - How cmd parameters are handled
- `OMNISHARP_CMD_QUICK_REFERENCE.md` - Quick reference for cmd issues
- `RESEARCH_FINDINGS_SUMMARY.txt` - Complete research findings

### Settings Flattening Research
- `NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md` - How settings become cmd args
- `LSPCONFIG_SETTINGS_QUICK_REFERENCE.md` - Quick reference
- `LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md` - Deep technical analysis

### LSP Client Research
- `NEOVIM_LSP_CLIENT_RESEARCH.md` - How Neovim LSP client works
- `LSP_SPECIFICATION_RESEARCH.md` - LSP protocol details
- `LSP_RESEARCH_SUMMARY.md` - Summary of LSP findings

### OmniSharp Configuration Research
- `OMNISHARP_ROSLYN_RESEARCH.md` - OmniSharp configuration options
- `OMNISHARP_ROSLYN_WORKING_CONFIGS.md` - Working configuration examples
- `OMNISHARP_LSP_SETTINGS_GUIDE.md` - Complete settings guide

### Mason and Installation
- `MASON_OMNISHARP_RESEARCH.md` - Mason OmniSharp installation
- `MASON_OMNISHARP_ACTION_PLAN.md` - Installation procedures

---

## The Problem (Summary)

### Issue 1: Empty RoslynExtensionsOptions in :LspInfo

**Root Cause:**
nvim-lspconfig's `on_new_config` callback flattens the `settings` table into command-line arguments:

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true
  }
}
```

Becomes:
```bash
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

OmniSharp doesn't parse this correctly from cmd args. The settings table is consumed during flattening, so `:LspInfo` shows it as empty.

### Issue 2: Missing StyleCop Warnings

**Root Cause:**
Three compounding factors:

1. **Invalid `-s` parameter:** Points to directory instead of .sln file
   - OmniSharp can't find solution properly
   - Projects not fully loaded
   - Analyzers not initialized

2. **Settings not applied:** Because of flattening issue (see Issue 1)
   - RoslynExtensionsOptions not recognized
   - EnableAnalyzersSupport not active
   - StyleCop never enabled

3. **WSL2 NuGet cache:** If packages restored in Windows
   - Analyzer DLLs not accessible from WSL
   - StyleCop.Analyzers.dll not found

---

## The Solution (Summary)

### Fix 1: Remove Settings from init.lua

Delete the `settings` table from omnisharp config. Use `omnisharp.json` file instead.

**Why this works:**
- OmniSharp reads JSON file directly from disk
- No flattening, no parsing issues
- Settings properly applied

### Fix 2: Remove `-s` Parameter

Let nvim-lspconfig's `root_dir` auto-detection find the solution file.

**Why this works:**
- `root_dir` uses pattern matching to find .sln files
- OmniSharp spawns with correct working directory
- Solution found and loaded properly

### Fix 3: Clear NuGet Cache in WSL

Run `dotnet restore --force-evaluate --no-cache` in WSL.

**Why this works:**
- Forces re-download of packages in WSL environment
- Analyzer DLLs accessible from WSL OmniSharp process
- StyleCop.Analyzers available

---

## Implementation Path

```
1. Read QUICK_FIX_GUIDE.md
   ↓
2. Edit init.lua (remove -s and settings)
   ↓
3. Run dotnet restore in WSL
   ↓
4. Kill OmniSharp processes
   ↓
5. Clear cache files
   ↓
6. Restart Neovim
   ↓
7. Verify with :LspInfo
   ↓
8. Test StyleCop warning
   ↓
9. Success! ✓

   If problems occur at step 7-8:
   ↓
   Read FINAL_SOLUTION.md Section 7 (Troubleshooting)
```

---

## Verification Checklist

After implementing the fix, verify:

- [ ] `:LspInfo` shows RoslynExtensionsOptions with populated values (not empty `{}`)
- [ ] StyleCop warning appears on lowercase class name within 30 seconds
- [ ] `:Telescope diagnostics` shows StyleCop warnings
- [ ] `:LspLog` shows "Successfully loaded" messages for all projects
- [ ] `:LspLog` shows "analyzer" or "StyleCop" mentions

If all checked: **Success!**

If any fail: See `FINAL_SOLUTION.md` Section 7.

---

## Expected Timeline

After implementing fix:

| Time | Event |
|------|-------|
| T+0s | Neovim starts, OmniSharp spawns |
| T+5s | OmniSharp discovers solution file |
| T+10s | Projects loaded, analyzers initialized |
| T+15s | First diagnostics appear |
| T+30s | All StyleCop warnings visible |

If nothing after 60s → Check `:LspLog` for errors.

---

## Quick Reference Commands

### Neovim
```vim
:LspInfo              " Check configuration
:LspLog               " View LSP logs
:Telescope diagnostics " List all warnings
```

### Bash
```bash
# Kill OmniSharp
pkill -f omnisharp

# Check if running
ps aux | grep omnisharp

# Clear cache
rm -f ~/.local/state/nvim/lsp.log
rm -f ~/.local/state/nvim/swap/*.swp

# Fix NuGet (WSL2)
cd /mnt/c/.../Backend
dotnet restore --force-evaluate --no-cache

# Watch logs
tail -f ~/.local/state/nvim/lsp.log
```

---

## Key Insights

### 1. nvim-lspconfig Flattens Settings
- Settings are converted to cmd arguments
- Not sent via LSP `initialize` message
- OmniSharp doesn't parse them reliably

### 2. omnisharp.json is Better
- Native OmniSharp format
- Read directly from disk
- No flattening, no parsing issues
- Always reliable

### 3. Don't Use `-s` Parameter
- nvim-lspconfig uses `root_dir` pattern detection
- Manually adding `-s` creates conflicts
- Let auto-detection work

### 4. WSL2 Requires Special Handling
- NuGet packages restored in Windows not accessible from WSL
- Must run `dotnet restore` in WSL after Windows builds
- Analyzer DLLs must be in WSL cache

---

## Related Files in Your Project

### Configuration Files
- **init.lua:** `/home/uczen/.config/nvim/init.lua`
- **omnisharp.json:** `/mnt/c/.../Backend/omnisharp.json`
- **.editorconfig:** `/mnt/c/.../Backend/.editorconfig`
- **ITSGrules.ruleset:** `/mnt/c/.../Backend/ITSGrules.ruleset`

### Solution Files
- **Solution:** `/mnt/c/.../Backend/VDEK.DCSP.sln`
- **Projects:** `/mnt/c/.../Backend/VDEK.DCSP.*/`

### StyleCop Configuration
- **stylecop.json:** `/mnt/c/.../Backend/stylecop.json`
- **Package reference:** In each .csproj file (StyleCop.Analyzers 1.1.118)

---

## Support and References

### Official Documentation
- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig
- OmniSharp: https://github.com/OmniSharp/omnisharp-roslyn
- Roslyn Analyzers: https://learn.microsoft.com/en-us/visualstudio/code-quality/roslyn-analyzers-overview

### Your Documentation
- CLAUDE.md: Your project-specific notes and workflows
- All research documents in this directory

### Troubleshooting Resources
- `FINAL_SOLUTION.md` Section 7: Complete troubleshooting guide
- `QUICK_FIX_GUIDE.md`: Common issues and quick fixes

---

## Document Reading Order

### For Quick Implementation
1. `QUICK_FIX_GUIDE.md`
2. `PROBLEM_SOLUTION_DIAGRAM.md` (optional, for understanding)

### For Deep Understanding
1. `PROBLEM_SOLUTION_DIAGRAM.md`
2. `FINAL_SOLUTION.md`
3. Background research documents (optional)

### For Troubleshooting
1. `FINAL_SOLUTION.md` Section 7
2. `QUICK_FIX_GUIDE.md` troubleshooting section
3. `:LspLog` and `:LspInfo` output

---

## Success Criteria

Configuration is considered **successfully fixed** when:

1. `:LspInfo` shows populated RoslynExtensionsOptions
2. StyleCop warnings appear in code
3. `:Telescope diagnostics` lists StyleCop warnings
4. `:LspLog` shows successful project loads
5. Test violation (lowercase class name) triggers warning

---

## Next Steps

1. **Implement the fix:** Follow `QUICK_FIX_GUIDE.md`
2. **Verify it works:** Use checklist above
3. **If issues occur:** Consult `FINAL_SOLUTION.md` Section 7
4. **Update CLAUDE.md:** Document your experience (optional)

---

**This concludes the complete solution documentation. Good luck!**
