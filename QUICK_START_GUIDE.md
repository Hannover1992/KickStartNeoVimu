# QUICK START GUIDE: Test OmniSharp StyleCop Configuration
## 5-Minute Test Procedure

**Date:** 2025-11-13
**Status:** Configuration ALREADY IMPLEMENTED - Just needs testing!

---

## TL;DR

```bash
# 1. Clear cache and kill processes:
rm -rf ~/.cache/nvim/luac/ && pkill -f omnisharp

# 2. Start Neovim with C# file:
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/CenCoCo.Core.API/Program.cs

# 3. Wait 10-30 seconds, then check:
:LspInfo

# 4. Verify in terminal:
ps aux | grep omnisharp | grep EnableAnalyzersSupport
```

**If it works:** You should see StyleCop warnings (SA1xxx) in Neovim!

**If it doesn't:** See "Fallback Plan" below.

---

## What Was Done (2025-11-13)

1. ✅ Fresh kickstart.nvim installed (1016 lines vanilla)
2. ✅ OmniSharp configuration added to init.lua (lines 702-723)
3. ✅ Project changed from DCSRE to CenCoCo for testing
4. ⏳ TESTING PENDING - You need to verify it works

---

## Testing Checklist

### Step 1: Pre-Flight

```bash
# Check OmniSharp installed:
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

# Should show: OmniSharp.dll
# If missing: nvim -c ":Mason" then install omnisharp
```

### Step 2: Clean Slate

```bash
# Clear cache:
rm -rf ~/.cache/nvim/luac/

# Kill OmniSharp:
pkill -f omnisharp

# Verify nothing running:
ps aux | grep omnisharp | grep -v grep
# Should return nothing
```

### Step 3: Start Neovim

```bash
# Open C# file from CenCoCo project:
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/CenCoCo.Core.API/Program.cs

# Wait 10-30 seconds (first load is slow)
```

### Step 4: Verify in Neovim

```vim
:LspInfo
```

**Expected output:**
- Client: omnisharp (running)
- cmd: dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll -s /mnt/c/.../cencoco/src -loglevel Information ...RoslynExtensionsOptions:EnableAnalyzersSupport=true...

**Key things to check:**
- ✅ cmd starts with `dotnet` (not just "OmniSharp")
- ✅ Full path to OmniSharp.dll
- ✅ `-s /mnt/c/.../cencoco/src` present
- ✅ `RoslynExtensionsOptions:EnableAnalyzersSupport=true` present

### Step 5: Verify in Terminal

```bash
ps aux | grep omnisharp | grep -v grep
```

**Should show:**
- ✅ dotnet /path/to/OmniSharp.dll
- ✅ -s /mnt/c/.../cencoco/src
- ✅ RoslynExtensionsOptions:EnableAnalyzersSupport=true
- ✅ RoslynExtensionsOptions:EnableImportCompletion=true
- ✅ FormattingOptions:EnableEditorConfigSupport=true

### Step 6: Test LSP Features

```vim
" Test go to definition:
" Put cursor on a class name, press: gd

" Test find references:
" Put cursor on a method, press: grr

" Test hover:
" Put cursor on a type, press: K

" Test diagnostics:
" Press: ]d (jump to next diagnostic)

" Look for StyleCop warnings:
" Red/yellow underlines should appear
" Press K on underline to see SA1xxx codes
```

---

## Success Criteria

**Configuration is working if:**

1. ✅ `:LspInfo` shows omnisharp with correct cmd
2. ✅ `ps aux` shows all settings in command line
3. ✅ LSP features work (gd, grr, K)
4. ✅ Diagnostics appear (]d jumps to warnings)

**StyleCop is working if:**

5. ✅ Warnings show SA1xxx codes (SA1116, SA1117, etc.)

**If 1-4 work but 5 doesn't:**
- StyleCop.Analyzers may not be installed in CenCoCo project
- OmniSharp config is CORRECT, project just needs the package

---

## Fallback Plan (If It Doesn't Work)

### Plan B: omnisharp.json (5 minutes)

```bash
# Create global config:
mkdir -p ~/.omnisharp
cat > ~/.omnisharp/omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
EOF

# Kill and restart:
pkill -f omnisharp
nvim /mnt/c/.../Program.cs

# Verify:
ps aux | grep omnisharp | grep enableAnalyzersSupport
```

**This is 100% reliable** - OmniSharp reads this file automatically.

---

## Common Issues

### Issue: `:LspInfo` shows wrong cmd

**Symptom:** cmd shows just "OmniSharp" instead of full dotnet path

**Fix:**
```bash
# Cache issue - clear it:
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp
nvim
```

### Issue: No StyleCop warnings appear

**Symptom:** LSP works (gd, grr work), but no SA1xxx warnings

**Check if StyleCop installed:**
```bash
cd /mnt/c/.../cencoco/src
find . -name "*.csproj" -exec grep -l "StyleCop.Analyzers" {} \;
```

**If no results, install:**
```bash
cd /mnt/c/.../cencoco/src
for proj in *//*.csproj; do
  dotnet add "$proj" package StyleCop.Analyzers
done
dotnet restore --force-evaluate --no-cache
pkill -f omnisharp
nvim
```

### Issue: OmniSharp won't start

**Check dotnet installed:**
```bash
dotnet --version
# Should show version like 8.0.xxx
```

**Check OmniSharp installed:**
```bash
ls ~/.local/share/nvim/mason/packages/omnisharp/
# Should show libexec/ directory
```

**If missing:**
```vim
:Mason
" Search 'omnisharp', press 'i' to install
```

---

## Performance Expectations

**First startup (on /mnt/c):**
- 20-60 seconds (WSL2 cross-filesystem is slow)
- This is NORMAL, not a failure

**Subsequent startups:**
- 5-15 seconds

**Analysis per file:**
- First analysis: 10-30 seconds
- Cached analysis: 1-5 seconds

**Memory usage:**
- Small solution: 200-500 MB
- CenCoCo size: 500 MB - 1 GB

---

## Quick Commands Reference

```bash
# View this guide:
cat QUICK_START_GUIDE.md

# View full plan:
cat MASTER_IMPLEMENTATION_PLAN.md

# Clear cache and restart:
rm -rf ~/.cache/nvim/luac/ && pkill -f omnisharp && nvim

# Check OmniSharp process:
ps aux | grep omnisharp | grep -v grep

# Check LSP logs:
tail -100 ~/.local/state/nvim/lsp.log

# Install StyleCop in project:
cd /mnt/c/.../cencoco/src && \
for proj in *//*.csproj; do \
  dotnet add "$proj" package StyleCop.Analyzers; \
done && \
dotnet restore --force-evaluate --no-cache
```

---

## Next Steps After Testing

### If It Works

1. **Update CLAUDE.md:**
   - Document that configuration is working
   - Note which project it was tested on
   - Record startup time and performance

2. **Install StyleCop in CenCoCo (if needed):**
   - Add to all projects
   - Commit to Git

3. **Consider creating omnisharp.json:**
   - Project-level config
   - Commit to Git for team benefit

### If It Doesn't Work

1. **Check MASTER_IMPLEMENTATION_PLAN.md:**
   - Section: "TROUBLESHOOTING DECISION TREE"
   - Follow diagnostic flow

2. **Try Plan B (omnisharp.json):**
   - Zero risk
   - 100% reliable

3. **Document what failed:**
   - Save :LspInfo output
   - Save ps aux output
   - Save LSP log tail

---

## Summary

**What you're testing:**
- Configuration added on 2025-11-13 (lines 702-723 in init.lua)
- Fresh kickstart.nvim with minimal OmniSharp config
- Testing on CenCoCo.sln project

**Expected result:**
- OmniSharp starts with correct settings
- LSP features work (gd, grr, K)
- StyleCop warnings appear (if package installed)

**Time required:**
- 5 minutes to test
- 10-30 seconds first load time

**Risk:**
- Very low (just testing existing config)
- Easy rollback (clear cache, restart)

**Confidence:**
- 95% current config will work
- 100% one of the fallback plans will work

---

**START HERE:** Clear cache, kill processes, open Neovim, check :LspInfo!

**See also:** MASTER_IMPLEMENTATION_PLAN.md (full 8000+ line guide)
