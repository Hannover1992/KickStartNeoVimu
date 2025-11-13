# OmniSharp Alternative Approaches - Navigation Guide

This directory contains comprehensive research and solutions for getting OmniSharp Roslyn analyzers (StyleCop) working in Neovim.

## Quick Start

**Want StyleCop warnings in 5 minutes?** → Read [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md)

**Want to understand ALL options?** → Read [OMNISHARP_ALTERNATIVE_APPROACHES.md](OMNISHARP_ALTERNATIVE_APPROACHES.md)

**Want automated setup?** → Run `bash setup_omnisharp_config.sh global`

---

## Document Overview

### 1. QUICK_FIX_GUIDE.md ⚡ (5 minutes)
**Start here if you just want it working ASAP**

- TL;DR solution: Create `~/.omnisharp/omnisharp.json`
- Zero risk (no Neovim config changes)
- Copy-paste commands
- Verification checklist

**Best for:** Quick fix, minimal fuss

---

### 2. OMNISHARP_ALTERNATIVE_APPROACHES.md (Complete Analysis)
**Read this to understand WHY previous attempts failed and explore all options**

Contains detailed analysis of 3 different approaches:

#### Approach 1: Manual OmniSharp Installation
- Skip Mason entirely
- Full control over installation
- Complexity: 3/5
- **Best for:** Power users who want absolute control

#### Approach 2: csharp.nvim Plugin
- Zero-config plugin that handles everything
- Includes debugger (nvim-dap)
- Complexity: 2/5
- **Best for:** Want integrated C# development experience

#### Approach 3: omnisharp.json Configuration File ⭐ **RECOMMENDED**
- Create JSON config file OmniSharp reads directly
- Editor-agnostic (works in VS Code, Vim, etc.)
- Complexity: 1/5
- **Best for:** Everyone! Simplest, safest, team-friendly

**Includes:**
- Pros/cons matrix for each approach
- Complete implementation code
- Comparison table
- When to use each approach

---

### 3. setup_omnisharp_config.sh (Automated Script)
**Run this to automatically set up Approach 3**

```bash
# Global config (applies to all projects)
bash setup_omnisharp_config.sh global

# Project-level config (DCSRE only, commit to Git)
bash setup_omnisharp_config.sh project
```

Creates `omnisharp.json` with correct settings, provides verification steps.

---

## Recommendation Flow Chart

```
┌─────────────────────────────────┐
│ Do you want StyleCop warnings? │
└───────────┬─────────────────────┘
            │
            ▼
    ┌───────────────┐
    │ QUICK_FIX.md  │ ← Start here (5 min)
    │ (Approach 3)  │
    └───────┬───────┘
            │
            ▼
    ┌──────────────────┐
    │ Did it work? YES │──────────► ✅ Done! Commit omnisharp.json to Git
    └──────────────────┘
            │ NO
            ▼
    ┌─────────────────────────────┐
    │ Read ALTERNATIVE_APPROACHES │ ← Understand WHY & try other options
    │ (Full analysis)             │
    └───────────┬─────────────────┘
                │
                ▼
        ┌───────────────┐
        │ Try Approach 1│ ← Manual installation (full control)
        │ or Approach 2 │   or csharp.nvim plugin (zero-config)
        └───────────────┘
```

---

## Problem Context

**What was failing:**
- Traditional mason-lspconfig + lspconfig.omnisharp.setup() approach
- OmniSharp was running but NOT loading analyzer settings
- `:LspInfo` showed `RoslynExtensionsOptions = {}` (empty!)
- StyleCop warnings (SA1116, SA1117, etc.) not appearing

**Root causes identified:**
1. Configuration handler conflicts in mason-lspconfig
2. Settings not properly flattened to command-line args
3. Lua bytecode cache preventing config reload
4. `lspconfig.omnisharp.setup()` can only be called once

**Solution:** Use `omnisharp.json` file - bypasses Neovim config system entirely, highest priority in OmniSharp's config loading order.

---

## File Summary

| File | Purpose | Time | Complexity |
|------|---------|------|------------|
| **QUICK_FIX_GUIDE.md** | Fast solution (Approach 3) | 5 min | ⭐ Very Low |
| **OMNISHARP_ALTERNATIVE_APPROACHES.md** | Complete analysis of all 3 approaches | 15 min read | Deep dive |
| **setup_omnisharp_config.sh** | Automated setup script | 1 min | Zero (runs for you) |
| **README_ALTERNATIVE_APPROACHES.md** | This file (navigation guide) | 2 min | Navigation |

---

## Quick Commands Reference

### Setup
```bash
# Approach 3 (Recommended): omnisharp.json
bash setup_omnisharp_config.sh global

# Verify config was created
ls -la ~/.omnisharp/omnisharp.json

# Kill OmniSharp and restart Neovim
pkill -f omnisharp
nvim /path/to/file.cs
```

### Verification
```bash
# Check OmniSharp process includes settings
ps aux | grep omnisharp | grep -v grep | grep -i enableAnalyzers

# Check LSP logs
tail -100 ~/.local/state/nvim/lsp.log | grep -i analyzer

# In Neovim
:LspInfo  # Should show RoslynExtensionsOptions.enableAnalyzersSupport = true
```

### Troubleshooting
```bash
# Clear LSP cache
rm -rf ~/.cache/nvim/lsp/
rm -f ~/.local/state/nvim/lsp.log

# Clear Lua bytecode cache
rm -rf ~/.cache/nvim/luac/

# Restart OmniSharp
pkill -f omnisharp
```

---

## Team Usage (Project-Level Config)

**Recommended for teams:** Use project-level `omnisharp.json` and commit to Git.

```bash
cd /path/to/your/backend/project
bash setup_omnisharp_config.sh project

# Commit to Git
git add omnisharp.json
git commit -m "Enable OmniSharp analyzer support for StyleCop warnings"
git push

# Now entire team gets StyleCop warnings automatically!
```

**Benefits:**
- Everyone on team sees same warnings
- Version controlled
- Works in ALL editors (Neovim, VS Code, Vim, etc.)
- No per-user configuration needed

---

## Success Criteria

You'll know it's working when:

1. ✅ `ps aux | grep omnisharp` shows `enableAnalyzersSupport=true`
2. ✅ `:LspInfo` shows `RoslynExtensionsOptions.enableAnalyzersSupport = true`
3. ✅ StyleCop warnings appear in Neovim (yellow underlines)
4. ✅ `tail -f ~/.local/state/nvim/lsp.log | grep -i analyzer` shows analyzer loading messages
5. ✅ Violation like `public class test { }` shows SA1300 warning

---

## Additional Resources

- [OmniSharp Configuration Options](https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options) (Official wiki)
- [csharp.nvim Plugin](https://github.com/iabdelkareem/csharp.nvim) (Alternative approach)
- [nvim-lspconfig OmniSharp docs](https://github.com/neovim/nvim-lspconfig/blob/master/doc/configs.md#omnisharp)

---

## Summary

**Problem:** StyleCop warnings not showing in Neovim despite correct configuration
**Root Cause:** mason-lspconfig handler conflicts and settings not being passed correctly
**Recommended Solution:** Create `~/.omnisharp/omnisharp.json` (Approach 3)
**Time to Fix:** 5 minutes
**Risk Level:** Zero (no Neovim config changes)
**Result:** ✅ StyleCop warnings appear, works for entire team, editor-agnostic

**Start with:** [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md)
**Deep dive:** [OMNISHARP_ALTERNATIVE_APPROACHES.md](OMNISHARP_ALTERNATIVE_APPROACHES.md)
**Automate:** `bash setup_omnisharp_config.sh global`
