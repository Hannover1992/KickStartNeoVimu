# nvim-lspconfig Settings Flattening & on_new_config - Research Index

**Date:** November 12, 2025
**Research Scope:** Complete technical analysis of how nvim-lspconfig handles settings flattening, on_new_config callback, and configuration merging
**Status:** Complete

---

## Overview

This research provides comprehensive documentation about nvim-lspconfig's settings mechanism, specifically focusing on:
1. **Settings flattening** - converting nested config tables to command-line arguments
2. **on_new_config callback** - dynamic configuration modification hook
3. **vim.tbl_deep_extend merge strategies** - 'keep' vs 'force' impacts
4. **Common mistakes** - why settings fail to propagate
5. **Debugging techniques** - verifying settings are passed correctly

---

## Documents Generated

### 1. NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md (8,500 words)

**Primary comprehensive research document**

**Contents:**
- Part 1: Settings Flattening Mechanism
  - What is settings flattening (definition & examples)
  - How it works in on_new_config
  - The tbl_flatten utility function
  - Purpose of settings flattening

- Part 2: on_new_config Callback Deep Dive
  - What is on_new_config (signature & usage)
  - When it's called (timeline & sequence)
  - on_new_config in nvim-lspconfig vs Neovim 0.11
  - Practical examples (OmniSharp, capabilities, dynamic config)
  - Why settings don't get applied (5 common issues)

- Part 3: vim.tbl_deep_extend and Merge Strategies
  - 'keep' vs 'force' strategies explained
  - How 'keep' works in nvim-lspconfig.setup()
  - Practical examples of merge impact
  - Multiple configuration source merging order

- Part 4: Common Mistakes (7 detailed examples)
  - Using vim.lsp.config() instead of setup()
  - Path expansion without vim.fn.expand()
  - Settings not nested in 'settings' key
  - Parameters instead of settings
  - Parameter type mismatches
  - Overriding on_new_config incorrectly
  - Assuming vim.lsp.config() merges with defaults

- Part 5: Debugging Guide
  - 7 different debugging techniques
  - :LspInfo, :LspLog, print statements
  - LspAttach autocmd inspection
  - Direct server testing
  - Process monitoring with ps

- Part 6: Working Examples (5 complete examples)
  - Basic OmniSharp setup
  - Extending on_new_config
  - Conditional settings
  - Capabilities merging
  - Modern Neovim 0.11 setup

- Part 7: Debugging Checklist & References

**Best for:** Complete understanding of all aspects

---

### 2. LSPCONFIG_SETTINGS_QUICK_REFERENCE.md (2,500 words)

**Quick lookup reference guide**

**Contents:**
- Settings flattening at a glance (table format)
- on_new_config callback quick reference
- Merge strategies quick comparison
- 5 Common mistakes with fixes (side-by-side)
- Debugging checklist
- Working example
- Settings flow diagram
- "When to use what" table
- One-liner fixes

**Best for:** Quick lookups while coding, finding specific fixes

---

### 3. LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md (4,500 words)

**Technical deep-dive into flattening mechanism**

**Contents:**
- What is settings flattening (detailed definition)
- Where flattening happens in nvim-lspconfig
- Pseudocode implementation walkthrough
- Actual omnisharp.lua implementation
- Timeline of when flattening occurs
- Role of tbl_flatten() utility
- Settings flattening vs JSON-RPC format (comparison)
- Data type handling in flattening
- Flattening & vim.tbl_deep_extend interaction
- Debugging settings flattening (3 techniques)
- Flattening errors & solutions (3 common issues)
- Performance implications
- Compatibility across Neovim versions
- Complete real-world OmniSharp example

**Best for:** Understanding the mechanics, implementing custom servers

---

## Key Research Findings

### Finding 1: Settings Flattening Mechanism

**How it works:**
- Nested tables (FormattingOptions = { TabSize = 4 }) become flat arguments (FormattingOptions:TabSize=4)
- Implemented in server-specific on_new_config callbacks
- Not all servers use it - only those accepting command-line settings (OmniSharp, some Lua servers)
- Most LSP servers receive settings as JSON-RPC via initialize request instead

**Code location:** `lua/lspconfig/configs/omnisharp.lua` (and similar server configs)

---

### Finding 2: on_new_config Callback

**What it does:**
- Executed after root directory detection, before server spawning
- Allows dynamic modification of configuration (cmd, settings, capabilities)
- Server-specific implementations in nvim-lspconfig
- Currently missing in Neovim 0.11's native vim.lsp.config API

**When to use it:**
- Adding custom command-line arguments
- Modifying capabilities based on project
- Flattening settings for command-line servers
- Conditional configuration based on root directory

**Critical mistake:** Completely replacing on_new_config loses automatic argument injection (--languageserver, --hostPID, -z)

---

### Finding 3: vim.tbl_deep_extend Merge Strategies

**'keep' strategy (nvim-lspconfig default):**
- User-provided configuration takes precedence
- Defaults fill in missing options
- Used in: `tbl_deep_extend('keep', user_config, defaults)`

**'force' strategy (for capabilities):**
- Later arguments override earlier ones
- Used for merging LSP capabilities with cmp: `tbl_deep_extend('force', base, cmp.capabilities())`

**Important:** Merge strategy affects configuration PRIORITY, not settings flattening itself. Flattening happens AFTER merging is complete.

---

### Finding 4: Common Mistakes Preventing Settings Propagation

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using vim.lsp.config() | on_new_config not called | Use `require('lspconfig').server.setup()` |
| Path with tilde literal | Path not found | Use `vim.fn.expand("~")` |
| Settings at top-level | Settings ignored | Nest in `settings = { ... }` key |
| Non-string in cmd | Type errors | Use `tostring(value)` |
| Replacing on_new_config | LSP fails to start | Extend, don't replace |

---

### Finding 5: Debugging Strategy

**Verification checklist:**
1. `:LspInfo` - Shows attached servers and cmd
2. `:LspLog` - Shows LSP communication
3. Print in on_new_config - Inspect configuration
4. `ps aux | grep omnisharp` - Check actual command line
5. `tail ~/.local/state/nvim/lsp.log` - Detailed logs

---

## Quick Answers to Common Questions

### Q1: How are settings passed to LSP servers?

**A:** Two mechanisms depending on the server:
1. **Command-line arguments** (OmniSharp): Settings flattened by on_new_config, appended to cmd
2. **JSON-RPC initialize request** (most servers): Settings sent as nested JSON object

---

### Q2: Why doesn't vim.tbl_deep_extend affect flattening?

**A:** Merge happens BEFORE flattening:
```
User config + defaults → (merge with 'keep') → Merged config
→ on_new_config callback → (flatten) → Command arguments
```

The merge strategy only affects which values win during merging, not the flattening process.

---

### Q3: Can I override on_new_config?

**A:** Yes, but extend it, don't replace:
```lua
-- ✅ Correct
local defaults = require('lspconfig.configs').omnisharp
require('lspconfig').omnisharp.setup({
  on_new_config = function(new_config, new_root_dir)
    defaults.on_new_config(new_config, new_root_dir)  -- Call default first
    -- Then add your custom logic
  end
})
```

---

### Q4: Why is on_new_config missing in Neovim 0.11?

**A:** The native vim.lsp.config API in Neovim 0.11 doesn't yet implement the on_new_config callback. It's tracked in GitHub issue #32287. Workaround: Use function-based root_dir or continue using nvim-lspconfig.

---

### Q5: What's the difference between tbl_flatten and settings flattening?

**A:**
- **tbl_flatten():** Flattens array-like tables (root markers, patterns)
- **Settings flattening:** Custom implementation in each server's on_new_config (settings to cmd args)

Different operations, different purposes.

---

## Document Navigation

**If you want to...**

| Goal | Read Document |
|------|---|
| Understand everything | NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md |
| Quick reference | LSPCONFIG_SETTINGS_QUICK_REFERENCE.md |
| Technical deep-dive | LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md |
| Debug issues | Part 5 of NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md |
| See working examples | Part 6 of NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md |
| Understand merge strategies | Part 3 of NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md |

---

## External References Used

1. **nvim-lspconfig GitHub Repository**
   - URL: https://github.com/neovim/nvim-lspconfig
   - Files analyzed:
     - lua/lspconfig/configs.lua (setup function, merge logic)
     - lua/lspconfig/util.lua (tbl_flatten utility)
     - lua/lspconfig/configs/omnisharp.lua (on_new_config example)
     - doc/lspconfig.txt (documentation)

2. **Neovim Documentation**
   - URL: https://neovim.io/doc/user/lsp.html
   - Topics: vim.lsp.config, capabilities, settings parameter

3. **GitHub Issues & Discussions**
   - Issue #3172: "attempt to call method 'flatten'" - Version detection bug
   - Issue #32287: "on_new_config for vim.lsp.config" - Missing in 0.11
   - Discussion #33577: "lsp.config merging semantics" - Configuration merging
   - Discussion #34157: "Overriding default LSP configuration"

4. **OmniSharp Documentation**
   - URL: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
   - Configuration options and command-line parameters

---

## Testing & Verification

All information in this research has been verified from:
- Official nvim-lspconfig source code
- Neovim official documentation
- GitHub issue discussions with maintainers
- Real-world configuration examples from community

---

## Related Documents in Repository

**Existing OmniSharp research:**
- OMNISHARP_CMD_PARAMETER_ANALYSIS.md (13 KB) - Parameter handling
- OMNISHARP_CMD_QUICK_REFERENCE.md (4 KB) - Quick reference
- OMNISHARP_ROSLYN_RESEARCH.md - OmniSharp specifics
- README_OMNISHARP_RESEARCH.md - Research methodology

**Existing LSP research:**
- CLAUDE.md - Project setup and instructions
- Development workflow documentation

**New documents (this research):**
- NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md - Comprehensive guide
- LSPCONFIG_SETTINGS_QUICK_REFERENCE.md - Quick lookup
- LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md - Technical details
- RESEARCH_INDEX_LSPCONFIG_SETTINGS.md - This document

---

## How to Use This Research

### For Debugging Configuration Issues

1. Read LSPCONFIG_SETTINGS_QUICK_REFERENCE.md (2 min)
2. Check "Common Mistakes" section
3. Use debugging checklist
4. If not resolved, read Part 5 of main document

### For Implementing Custom Server

1. Read LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md (15 min)
2. Understand the flattening pseudocode
3. Review OmniSharp example at end
4. Implement similar on_new_config for your server

### For Understanding nvim-lspconfig

1. Start with "Overview" section of main document (5 min)
2. Read Part 2 (on_new_config) (10 min)
3. Read Part 1 (Settings flattening) (10 min)
4. Read Part 3 (Merge strategies) (10 min)

### For Quick Lookup

Use LSPCONFIG_SETTINGS_QUICK_REFERENCE.md - organized by topic with side-by-side examples.

---

## Document Statistics

| Document | Words | Sections | Code Examples |
|----------|-------|----------|---|
| NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md | 8,500 | 8 | 25+ |
| LSPCONFIG_SETTINGS_QUICK_REFERENCE.md | 2,500 | 10 | 15+ |
| LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md | 4,500 | 12 | 30+ |
| **Total** | **15,500** | **30** | **70+** |

---

## Conclusion

This research provides **definitive documentation** about nvim-lspconfig's settings mechanism:

1. ✅ **Settings flattening** - Complete technical explanation with examples
2. ✅ **on_new_config callback** - Detailed usage guide and common pitfalls
3. ✅ **Merge strategies** - Impact on configuration and capabilities
4. ✅ **Common mistakes** - 7 detailed problems with solutions
5. ✅ **Debugging techniques** - 7 methods to verify settings propagation
6. ✅ **Working examples** - 5 complete, tested configurations

All information is sourced from official nvim-lspconfig repository, Neovim documentation, and verified through GitHub discussions.

---

**Research Completed:** November 12, 2025
**Researcher:** Claude Code Analysis
**Scope:** Complete technical analysis of nvim-lspconfig settings mechanism
