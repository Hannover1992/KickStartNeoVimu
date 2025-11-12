# nvim-lspconfig Settings Flattening Research - Visual Summary

**Date:** November 12, 2025
**Total Research:** 8,039 words across 4 documents
**Code Examples:** 70+ working examples

---

## What Was Researched

```
nvim-lspconfig Settings Flattening & on_new_config
├── Settings Flattening Mechanism
│   ├── What is flattening?
│   ├── How does it work?
│   ├── Where does it happen?
│   └── Why is it needed?
├── on_new_config Callback
│   ├── What is it?
│   ├── When is it called?
│   ├── How do you use it?
│   └── Common mistakes
├── vim.tbl_deep_extend Merge Strategies
│   ├── 'keep' vs 'force'
│   ├── Impact on configuration
│   └── Merge order
├── Settings Propagation Issues
│   ├── 7 common mistakes
│   ├── Why settings fail
│   └── How to debug
└── Debugging & Verification
    ├── 7 debugging techniques
    ├── Working examples
    └── Verification checklist
```

---

## Key Findings at a Glance

### 1. Settings Flattening

```
Nested Table (Lua)          Command-Line Arguments
─────────────────          ─────────────────────
settings = {               FormattingOptions:TabSize=4
  FormattingOptions = {    FormattingOptions:UseSpaces=true
    TabSize = 4,           MsBuild:IncludePrereleases=true
    UseSpaces = true,
  },
  MsBuild = {
    IncludePrereleases = true,
  }
}
```

**When:** In on_new_config callback
**Where:** lua/lspconfig/configs/omnisharp.lua (and similar)
**For:** Servers that accept settings as CLI args (OmniSharp, some Lua servers)
**For:** Most other servers send settings as JSON via LSP initialize request

---

### 2. on_new_config Callback

```
Timeline of LSP Startup
───────────────────────

t=0: setup() called
     Configuration stored

t=N: C# file opened
     ├─ root_dir detected
     ├─ Config instance created
     ├─ on_new_config CALLED ← Settings flattened here
     ├─ Command modified
     └─ Process spawned with flattened args
```

**Signature:**
```lua
on_new_config = function(new_config, new_root_dir)
  -- Modify new_config here
  -- Changes affect what gets passed to LSP server
end
```

---

### 3. Merge Strategy Impact

```
Configuration Sources and Merge Order
─────────────────────────────────────

Default Config
   ↓
vim.tbl_deep_extend('keep', user_config, defaults)
   ├─ User values take priority (because 'keep' strategy)
   └─ Defaults fill missing options
   ↓
Merged Config
   ↓
on_new_config callback (flattens merged settings)
   ↓
Final Command Arguments
```

**'keep' strategy:** User config wins (nvim-lspconfig default)
**'force' strategy:** Later values override (for capabilities merging)

---

### 4. Most Common Mistake

```
WRONG: Using vim.lsp.config()
───────────────────────────

vim.lsp.config('omnisharp', { ... })
         ↓
   on_new_config NOT CALLED
         ↓
   Settings not flattened
         ↓
   LSP doesn't get settings


RIGHT: Using require('lspconfig').omnisharp.setup()
──────────────────────────────────────────────────

require('lspconfig').omnisharp.setup({ ... })
         ↓
   on_new_config IS CALLED
         ↓
   Settings flattened
         ↓
   LSP receives settings
```

---

## The 7 Most Critical Mistakes

| # | Mistake | Issue | Fix |
|---|---------|-------|-----|
| 1 | Using vim.lsp.config() | on_new_config not called | Use setup() |
| 2 | Path with tilde literal | Path not expanded | Use vim.fn.expand("~") |
| 3 | Settings at top level | Settings lost | Nest in settings = {} |
| 4 | Numbers in cmd array | Type mismatch | Use tostring() |
| 5 | Replacing on_new_config | Loses hard-coded args | Extend, don't replace |
| 6 | Parameters instead of settings | Settings ignored | Use settings table |
| 7 | Assuming 0.11 vim.lsp.config merges | Incomplete config | Use nvim-lspconfig |

---

## Debugging Decision Tree

```
LSP not attaching?
├─ YES → :LspInfo shows server attached?
│   ├─ NO  → Check :LspLog for errors
│   └─ YES → Check if cmd is correct
│
└─ NO (LSP attached but settings don't work)
   └─ Settings in correct key?
      ├─ NO  → Move to settings = { ... }
      └─ YES → Check on_new_config
         ├─ Print new_config.settings
         ├─ Check :LspLog for flattening
         ├─ Run ps aux | grep omnisharp
         └─ Verify final cmd
```

---

## Settings Flow Visualization

```
User writes in init.lua:
┌──────────────────────────────────────┐
│ require('lspconfig').omnisharp.setup({│
│   cmd = { 'dotnet', '...' },         │
│   settings = {                       │
│     FormattingOptions = {            │
│       TabSize = 4                    │
│     }                                │
│   }                                  │
│ })                                   │
└──────────────────────────────────────┘
         ↓
Configuration stored in memory
         ↓
When C# file opens, nvim-lspconfig calls:
┌──────────────────────────────────────┐
│ on_new_config(new_config, root_dir) {│
│   // Flatten settings into cmd       │
│   new_config.cmd.append(             │
│     'FormattingOptions:TabSize=4'    │
│   )                                  │
│ }                                    │
└──────────────────────────────────────┘
         ↓
Modified config passed to vim.fn.jobstart()
         ↓
Final command executed:
dotnet ... --languageserver ... FormattingOptions:TabSize=4
         ↓
OmniSharp process receives all arguments
```

---

## Quick Fix Guide

**Problem: LSP not attaching**
```lua
-- Check if using right setup method
require('lspconfig').omnisharp.setup({})  ← Right
vim.lsp.config('omnisharp', {})           ← Wrong
```

**Problem: Settings ignored**
```lua
-- Check if settings are nested
settings = {                  ← Right
  FormattingOptions = { ... }
}

FormattingOptions = { ... }   ← Wrong (top level)
```

**Problem: Path not found**
```lua
-- Check if path is expanded
vim.fn.expand("~/.../bin")    ← Right
"~/.../bin"                   ← Wrong (literal tilde)
```

**Problem: OmniSharp fails to start**
```lua
-- Check if cmd values are strings
{ 'omnisharp', '--hostPID', tostring(pid) }   ← Right
{ 'omnisharp', '--hostPID', pid }             ← Wrong (number)
```

---

## Document Overview

### 1. NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md (28 KB)

**Comprehensive guide with:**
- Complete explanation of all mechanisms
- 7 common mistakes with detailed analysis
- 5 working examples
- Step-by-step debugging guide
- 25+ code examples

**Best for:** Complete understanding, reference material

---

### 2. LSPCONFIG_SETTINGS_QUICK_REFERENCE.md (6.8 KB)

**Quick lookup with:**
- Settings flattening at a glance
- Callback reference
- Mistake/fix side-by-side
- One-liner fixes
- 15+ code examples

**Best for:** While coding, quick fixes

---

### 3. LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md (16 KB)

**Technical deep-dive with:**
- Pseudocode implementation
- Data type handling
- Performance analysis
- Version compatibility
- Real-world OmniSharp example
- 30+ code examples

**Best for:** Understanding mechanics, custom implementations

---

### 4. RESEARCH_INDEX_LSPCONFIG_SETTINGS.md (13 KB)

**Research index with:**
- Document navigation guide
- Key findings summary
- FAQ section
- External references
- Testing methodology

**Best for:** Finding what you need, research overview

---

## How to Get Started

### If you have 5 minutes:
Read: LSPCONFIG_SETTINGS_QUICK_REFERENCE.md

### If you have 15 minutes:
1. Read overview above
2. Skim NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md Part 1-3
3. Check "Common Mistakes" section

### If you have 30 minutes:
1. Read NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md (all parts)
2. Review debugging examples
3. Try one of the working examples

### If you're debugging an issue:
1. Check "7 Most Critical Mistakes" above
2. Run debugging checklist
3. Follow decision tree
4. Read relevant section in main document

---

## Key Statistics

- **Total words:** 8,039
- **Total code examples:** 70+
- **Documents:** 4 (comprehensive, quick ref, technical, index)
- **Common mistakes documented:** 7
- **Debugging techniques:** 7
- **Merge strategies compared:** 2 (keep vs force)
- **Working examples:** 5+
- **Sources:** 4 (nvim-lspconfig repo, Neovim docs, GitHub issues, OmniSharp wiki)

---

## Core Concepts Explained

### Settings Flattening
Converting nested config tables to command-line arguments. Example: `{Option = {Sub = true}}` becomes `Option:Sub=true`.

### on_new_config
Callback executed after root detection, before server spawn. Allows dynamic configuration modification including flattening.

### Merge Strategy
How configurations are combined (user + defaults). 'keep' = user wins, 'force' = later wins.

### Propagation
How settings reach the LSP server. Usually either: flattened to cmd args OR sent as JSON via LSP initialize.

---

## Tools for Verification

```vim
:LspInfo              " Shows attached servers and cmd
:LspLog               " Shows LSP communication
:messages             " Shows notifications
```

```bash
ps aux | grep omnisharp       " See actual command line
tail ~/.local/state/nvim/lsp.log  " Detailed logs
```

```lua
-- In on_new_config:
vim.notify('Settings: ' .. vim.inspect(new_config.settings))
vim.notify('Cmd: ' .. vim.inspect(new_config.cmd))
```

---

## Research Methodology

Sources verified:
- Official nvim-lspconfig GitHub repository (lua/lspconfig/*)
- Neovim official documentation (https://neovim.io/doc/user/lsp.html)
- GitHub issues with maintainer discussions (#3172, #32287, #33577)
- OmniSharp configuration documentation

Techniques used:
- Source code analysis
- Documentation reading
- Issue discussion review
- Real-world example verification

---

## References

**Main Research Documents:**
- `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md`
- `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/LSPCONFIG_SETTINGS_QUICK_REFERENCE.md`
- `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md`
- `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/RESEARCH_INDEX_LSPCONFIG_SETTINGS.md`

**External Resources:**
- https://github.com/neovim/nvim-lspconfig
- https://neovim.io/doc/user/lsp.html
- https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options

---

## Next Steps

1. **Read** the appropriate document based on your needs (see "How to Get Started")
2. **Check** your configuration against the 7 common mistakes
3. **Debug** using the provided techniques
4. **Verify** settings are passed using :LspInfo, :LspLog, or print statements
5. **Reference** these documents when implementing custom servers

---

**Complete Research Package Created:** November 12, 2025
**All documents located in:** `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/`

Start with LSPCONFIG_SETTINGS_QUICK_REFERENCE.md for immediate help, or NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md for complete understanding.
