# Mason + OmniSharp Documentation Index

## Overview

This folder now contains comprehensive research on Mason's OmniSharp installation and its impact on settings propagation in Neovim. The research was conducted in November 2025 and includes official documentation, GitHub issue analysis, and practical implementation guidance.

---

## Document Structure

### 1. Quick Start Guide

**File:** `MASON_RESEARCH_SUMMARY.txt`
**Size:** ~9 KB
**Read Time:** 5 minutes

**Best for:** Getting a quick overview, 10,000 ft view
**Contains:**
- Executive summary of findings
- Settings propagation verification (WORKS CORRECTLY)
- Known issues with solutions
- Best practices checklist
- Recommended installation method
- Documentation links

**Start here if:** You want the essentials without deep details

---

### 2. Detailed Technical Research

**File:** `MASON_OMNISHARP_RESEARCH.md`
**Size:** ~18 KB
**Read Time:** 20-25 minutes

**Best for:** Understanding the underlying architecture and all nuances
**Contains:**
- How Mason installs OmniSharp (directory structure, symlinks, PATH handling)
- Wrapper script behavior (important: there aren't any custom wrappers)
- Settings propagation flow (LSP protocol, not environment variables)
- All known issues with detailed analysis
  - Issue #701: Incomplete Installation
  - Issue #1974: Case Sensitivity
  - Root directory detection
  - Platform-specific issues
- How settings are affected (and what can prevent them)
- Best practices with complete configuration examples
- Alternative: csharp.nvim plugin comparison
- Complete documentation references

**Start here if:** You want comprehensive understanding of the system

---

### 3. Implementation Guide

**File:** `MASON_OMNISHARP_ACTION_PLAN.md`
**Size:** ~15 KB
**Read Time:** 15-20 minutes

**Best for:** Hands-on implementation and troubleshooting
**Contains:**
- Step-by-step installation instructions
- Pre-installation verification checklist
- Configuration code for init.lua
- Fixes for common issues:
  - Incomplete installation (manual workaround)
  - Case sensitivity mismatch (3 solutions)
  - Root directory problems
  - WSL2 NuGet cache issues
- Post-installation verification tests
- Debugging procedures
- DCSRE project-specific configuration
- Quick troubleshooting table
- Summary checklist

**Start here if:** You want to implement or fix issues

---

## Key Findings Summary

### Does Mason's Installation Method Affect Settings Propagation?

**Answer: NO - Settings propagation WORKS CORRECTLY**

**Why:**
1. Mason uses symlinks, NOT custom wrapper scripts
2. No "settings translation layer" exists
3. Settings flow directly through LSP protocol (not environment variables)
4. The binary installation method is irrelevant to settings communication

**What DOES Affect Settings:**
- LSP failing to start (binary not found)
- Root directory not detected (.sln file not found)
- Incomplete installations (rare, fixable)
- WSL2 NuGet cache issues (not Mason-related)

### Known Mason + OmniSharp Issues

| Issue | Severity | Status | Workaround |
|-------|----------|--------|-----------|
| Incomplete Installation (#701) | High | Open | Manual installation |
| Case Sensitivity (#1974) | High | Fixed in v2.0+ | Rename binary or update Mason |
| Root Directory Detection | Medium | Config issue | Explicitly set root_dir |
| omnisharp-mono broken (#1280) | High | Open | Use omnisharp (Roslyn) instead |
| Windows native incompatibility | Medium | Unfixable | Use WSL2 |
| M1/M2 Mac architecture (#1651) | Medium | Consider csharp.nvim | Plugin handles it automatically |

### Recommended Approach

**Best Setup:**
1. Mason v2.0.0+ (fixes case sensitivity)
2. OmniSharp package (Roslyn, not mono)
3. Explicit root_dir configuration in lspconfig
4. WSL2 for best compatibility (Linux, not Windows native)

**Alternative if Issues Persist:**
- Use csharp.nvim plugin instead (auto-handles OmniSharp)

---

## Document Navigation Guide

### I want to...

**...understand if Mason affects settings?**
→ Read MASON_RESEARCH_SUMMARY.txt (sections 2, 3)

**...implement OmniSharp from scratch?**
→ Read MASON_OMNISHARP_ACTION_PLAN.md (sections 1-3)

**...fix a broken installation?**
→ Read MASON_OMNISHARP_ACTION_PLAN.md (section 4)

**...understand the complete architecture?**
→ Read MASON_OMNISHARP_RESEARCH.md (all sections)

**...understand settings flow?**
→ Read MASON_OMNISHARP_RESEARCH.md (section 4)

**...debug LSP issues?**
→ Read MASON_OMNISHARP_ACTION_PLAN.md (section 5)

**...see all issues and workarounds?**
→ Read MASON_OMNISHARP_RESEARCH.md (section 3)

**...find documentation links?**
→ Read MASON_RESEARCH_SUMMARY.txt (section 6)

**...get DCSRE-specific advice?**
→ Read MASON_OMNISHARP_ACTION_PLAN.md (sections 6-7)

---

## Key Documentation Links

### Official

- **Mason.nvim GitHub:** https://github.com/mason-org/mason.nvim
- **nvim-lspconfig:** https://github.com/neovim/nvim-lspconfig
- **OmniSharp-Roslyn:** https://github.com/OmniSharp/omnisharp-roslyn
- **csharp.nvim (Alternative):** https://github.com/iabdelkareem/csharp.nvim

### Known Issues Tracked

- **Issue #701 (Incomplete Installation):** https://github.com/mason-org/mason.nvim/issues/701
- **Issue #1974 (Case Sensitivity):** https://github.com/mason-org/mason.nvim/issues/1974
- **Issue #1280 (omnisharp-mono):** https://github.com/mason-org/mason.nvim/issues/1280
- **Issue #38 (Windows):** https://github.com/mason-org/mason-lspconfig.nvim/issues/38

### Community

- **Vi Stack Exchange:** https://vi.stackexchange.com/questions/43830
- **Dev.to Mason Guide:** https://dev.to/ralphsebastian/masonnvim-the-ultimate-guide-to-managing-your-neovim-tooling-4520

---

## Quick Reference: Settings Propagation Flow

```
Neovim init.lua
    ↓
require('lspconfig').omnisharp.setup({
  cmd = "...",           ← Mason handles this
  settings = {...}       ← Settings separate from binary
})
    ↓
nvim-lspconfig (reads config)
    ↓
Launches binary via cmd path (from Mason symlink)
    ↓
Settings sent via LSP JSON-RPC protocol
    ↓
OmniSharp receives and applies settings
    ↓
Mason's installation method: NO IMPACT
```

**Critical Point:** Mason handles the BINARY PATH. Settings flow through LSP protocol independently. They never mix.

---

## Checklist: Before Implementation

- [ ] Read MASON_RESEARCH_SUMMARY.txt (quick overview)
- [ ] Check your Mason version: `:Mason` in Neovim
- [ ] Check existing OmniSharp: `ls ~/.local/share/nvim/mason/packages/omnisharp/`
- [ ] Understand your project's .sln location
- [ ] Decide: Mason setup OR csharp.nvim plugin?
- [ ] Plan: Update Mason if v1.x? Install OmniSharp? Configure root_dir?

---

## Troubleshooting Quick Links

### Installation Failed
→ MASON_OMNISHARP_ACTION_PLAN.md, Section 4 (Issue A)

### OmniSharp Not Attaching
→ MASON_OMNISHARP_ACTION_PLAN.md, Section 5 (Debugging)

### Binary Case Sensitivity
→ MASON_OMNISHARP_ACTION_PLAN.md, Section 4 (Issue B)

### No Intellisense Despite LSP Attached
→ MASON_OMNISHARP_ACTION_PLAN.md, Section 4 (Issue C)

### Settings Not Taking Effect
→ MASON_OMNISHARP_RESEARCH.md, Section 4

### WSL2 Specific Issues
→ MASON_OMNISHARP_ACTION_PLAN.md, Section 4 (Issue D)

### Platform-Specific (Windows/Mac)
→ MASON_OMNISHARP_RESEARCH.md, Section 3

---

## Research Metadata

**Research Date:** November 12, 2025
**Scope:** Mason's OmniSharp installation and settings propagation
**Sources:**
- GitHub Mason.nvim repository and issues
- GitHub OmniSharp-Roslyn repository
- nvim-lspconfig documentation
- Mason community discussions
- Stack Exchange Vim community

**Key Finding:** Mason's installation method does NOT negatively affect settings propagation. Issues are installation-related, not settings-related.

**Recommendation:** Use Mason v2.0+ with explicit root_dir configuration. Settings will propagate correctly.

---

## Version History

**Document Set Version:** 1.0
**Last Updated:** November 12, 2025
**Created For:** DCSRE Neovim LSP Setup

---

## Related Documentation in Repository

- **CLAUDE.md** - Main Neovim setup documentation
- **LSP_SPECIFICATION_RESEARCH.md** - LSP protocol details
- **OMNISHARP_ROSLYN_RESEARCH.md** - OmniSharp server details
- **OMNISHARP_CONFIG_REFERENCE.md** - Configuration options

---

## Next Steps

1. **Read:** Start with MASON_RESEARCH_SUMMARY.txt (5 min)
2. **Decide:** Use Mason or csharp.nvim?
3. **Implement:** Follow MASON_OMNISHARP_ACTION_PLAN.md
4. **Verify:** Use section 5 checklist
5. **Debug:** Use troubleshooting table if needed
6. **Deep Dive:** Refer to MASON_OMNISHARP_RESEARCH.md for specific questions

---

## Contact/Questions

For questions about:
- **Mason:** See GitHub issues at https://github.com/mason-org/mason.nvim/issues
- **OmniSharp:** See GitHub discussions at https://github.com/OmniSharp/omnisharp-roslyn
- **Neovim LSP:** See Neovim Discourse at https://neovim.discourse.group/
- **This Research:** Check source links in MASON_OMNISHARP_RESEARCH.md

---

**Document Prepared:** November 12, 2025
**Purpose:** Enable confident implementation of Mason-installed OmniSharp with proper understanding of settings propagation
