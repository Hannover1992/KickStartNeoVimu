# Mason-lspconfig Research Index

## Overview
Complete research on mason-lspconfig handler execution order, how it interacts with lspconfig.omnisharp, and working configuration patterns (2024-2025).

---

## Documents in This Research

### 1. **MASON_LSPCONFIG_HANDLER_RESEARCH.md** (488 lines)
**The Complete Technical Reference**

Contains:
- Critical order of execution with timeline
- 4 different handler patterns with detailed explanations
- How `on_new_config()` flattens settings
- Settings structure requirements (MUST be nested 2 levels)
- Debugging strategies and verification commands
- Working configuration template
- Common mistakes and why they fail
- References to source code repositories

**Read this if:** You need to understand exactly how everything works

**Key sections:**
- Order of Execution (timeline)
- Pattern 1-4 (Default handler, Named handler, Explicit after, Just lspconfig)
- Critical: Default cmd provided by Mason
- Critical: Settings vs Command-line arguments
- Debugging verification checklist
- Working configuration template

---

### 2. **MASON_LSPCONFIG_QUICK_REFERENCE.md** (170 lines)
**Visual Quick Lookup Guide**

Contains:
- Side-by-side pattern comparison
- Color-coded checkmarks for what works/what doesn't
- Execution flow diagram
- Settings flattening example with actual values
- Critical checklist
- Debugging checklist

**Read this if:** You need a quick reminder or visual reference

**Best for:** After-hours browsing, quick glance at patterns

---

### 3. **MASON_LSPCONFIG_IMPLEMENTATION_GUIDE.md** (400+ lines)
**Step-by-Step Implementation**

Contains:
- Step 1: Understanding the handler execution timeline
- Step 2: Prepare your configuration (what you need)
- Step 3: Write the configuration (complete code template)
- Step 4: Verify the configuration (4 tests)
- Step 5: Troubleshooting (9 common problems with solutions)
- Step 6: Alternative named handler pattern
- Step 7: Minimal test configuration
- Checklist before committing

**Read this if:** You're implementing this for your project

**Best for:** Implementation, troubleshooting, step-by-step guidance

---

## Quick Navigation

### If you want to...

**...understand WHY something works:**
→ Read **MASON_LSPCONFIG_HANDLER_RESEARCH.md** (detailed explanations)

**...quickly check a pattern:**
→ Read **MASON_LSPCONFIG_QUICK_REFERENCE.md** (visual, concise)

**...implement this from scratch:**
→ Follow **MASON_LSPCONFIG_IMPLEMENTATION_GUIDE.md** (step-by-step)

**...debug why your config isn't working:**
→ Go to **IMPLEMENTATION_GUIDE.md** Section 5 (Troubleshooting)

---

## The Core Issue (Why Research Was Needed)

### The Problem
Many OmniSharp configurations fail because developers misunderstand:

1. **When handlers run** - They run DURING `mason-lspconfig.setup()`, not after
2. **How settings are passed** - Through recursive flattening into command-line args
3. **Settings structure** - MUST be nested 2 levels deep (RoslynExtensionsOptions → EnableAnalyzersSupport)
4. **Command override** - MUST use full DLL path, not Mason's wrapper script
5. **Setup order** - Settings flattening happens in `on_new_config()` which is called during setup

### The Research
This research investigated:
- Mason-lspconfig source code and handler execution
- nvim-lspconfig omnisharp configuration and `on_new_config()` function
- Settings flattening mechanism (recursive `flatten()` function)
- Order of execution for handlers
- Working patterns from community (2024-2025)
- Common mistakes and why they fail

---

## Key Findings Summary

### 1. Handler Execution Order
```
Mason-lspconfig.setup() called
  ↓
For each server:
  → Handler function called
  → Handler calls lspconfig[server].setup()
  → on_new_config() called
  → Settings flattened
  → LSP client started
```
**Critical**: Handler runs DURING setup(), not before/after

### 2. Settings Flattening
Input:
```lua
settings = {
  RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
}
```

Output:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

Appended to cmd array and executed.

### 3. Four Valid Patterns
1. **Default handler** (best, simplest) - Single function for all servers
2. **Named handler** (explicit) - Special handler just for omnisharp
3. **Setup after** (only if handler skips) - Call setup() explicitly
4. **No mason-lspconfig** (minimal) - Use just lspconfig directly

### 4. Three Critical Requirements
1. **Override cmd** - Use full DLL path, not wrapper
2. **Nest settings** - 2 levels deep (Parent → Child)
3. **Use PascalCase** - EnableAnalyzersSupport not enable_analyzers_support

---

## The Working Pattern (TL;DR)

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', '/path/to/Backend',
    },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
      },
      FormattingOptions = {
        EnableEditorConfigSupport = true,
      },
    },
  },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

That's it! Everything else is details and error handling.

---

## Verification Commands

### Check if configuration is working
```bash
# 1. Is omnisharp in :LspInfo?
nvim -c ":LspInfo"

# 2. Does process show settings?
ps aux | grep omnisharp | grep -v grep

# 3. Can OmniSharp run?
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll --version
```

---

## Related Documentation

### In This Project
- `CLAUDE.md` - Original LSP OmniSharp fix documentation
- `MASON_OMNISHARP_RESEARCH.md` - Mason installation details
- `OMNISHARP_LSP_SETTINGS_GUIDE.md` - Settings reference
- `ANALYSIS_COMPLETE_SUMMARY.md` - on_new_config() analysis
- `MASON_OMNISHARP_ACTION_PLAN.md` - Installation action plan

### External References
- Mason-lspconfig: https://github.com/WhoIsSethDaniel/mason-lspconfig.nvim
- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig
- OmniSharp: https://github.com/OmniSharp/omnisharp-roslyn

---

## Research Methodology

This research was compiled by:
1. Analyzing nvim-lspconfig source code (omnisharp.lua)
2. Analyzing mason-lspconfig source code
3. Testing handler execution order
4. Verifying settings flattening mechanism
5. Collecting working configurations from 2024-2025
6. Identifying common failure patterns
7. Creating reproducible test cases
8. Documenting with complete code examples

---

## Document Statistics

| Document | Lines | Content |
|----------|-------|---------|
| HANDLER_RESEARCH.md | 488 | Technical deep-dive |
| QUICK_REFERENCE.md | 170 | Visual patterns |
| IMPLEMENTATION_GUIDE.md | 400+ | Step-by-step |
| This INDEX | 280+ | Navigation & overview |
| **TOTAL** | **1,300+** | Complete reference |

---

## How to Use This Research

### For Quick Learning
1. Read **QUICK_REFERENCE.md** (10 minutes)
2. Skim the patterns section
3. Look at the working template

### For Implementation
1. Read **IMPLEMENTATION_GUIDE.md** Step 1-3
2. Copy the configuration template
3. Follow Step 4-7 for verification
4. Use Step 5 troubleshooting if needed

### For Deep Understanding
1. Start with **QUICK_REFERENCE.md** (visual overview)
2. Read **HANDLER_RESEARCH.md** (complete details)
3. Study the execution flow diagram
4. Review the common mistakes section
5. Reference the external sources

### For Troubleshooting
1. Go to **IMPLEMENTATION_GUIDE.md** Section 5
2. Match your symptoms to a problem
3. Follow the solution steps
4. If not in Step 5, check **HANDLER_RESEARCH.md** debugging section

---

## Final Note

This research represents the current state-of-the-art understanding of mason-lspconfig handlers and OmniSharp integration as of 2024-2025. The patterns have been tested and verified to work correctly. Common mistakes have been documented based on actual implementation issues.

The core insight is: **Handlers run DURING setup(), settings are flattened by on_new_config(), and the cmd must be overridden to include the solution path and custom arguments.**

---

**Last Updated:** 2025-11-13
**Applicable Versions:** Neovim 0.9+, Mason 2.0+, nvim-lspconfig latest, OmniSharp 1.39+
