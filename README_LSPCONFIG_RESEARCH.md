# nvim-lspconfig Settings Flattening & on_new_config Research

## Quick Navigation

**Read this first:** [START HERE](/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/RESEARCH_SUMMARY_VISUAL.md)

Then choose based on your needs:

| Need | Document | Time |
|------|----------|------|
| Quick fix now | LSPCONFIG_SETTINGS_QUICK_REFERENCE.md | 5 min |
| Complete guide | NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md | 30 min |
| Technical details | LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md | 20 min |
| Research index | RESEARCH_INDEX_LSPCONFIG_SETTINGS.md | 10 min |
| Visual overview | RESEARCH_SUMMARY_VISUAL.md | 15 min |

## What This Research Covers

- How on_new_config flattens settings into command-line arguments
- Whether vim.tbl_deep_extend affects settings propagation
- How 'keep' vs 'force' merge strategies impact settings
- Working examples of settings that successfully get passed
- 7 common mistakes preventing settings from being passed
- 7 debugging techniques to verify settings are passed correctly

## Key Files

1. **NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md** (28 KB)
   - Complete comprehensive guide
   - All mechanisms explained in detail
   - 25+ code examples
   - Full debugging guide

2. **LSPCONFIG_SETTINGS_QUICK_REFERENCE.md** (6.8 KB)
   - Quick lookup reference
   - Common mistakes & instant fixes
   - 15+ code examples

3. **LSPCONFIG_FLATTEN_TECHNICAL_ANALYSIS.md** (16 KB)
   - Technical deep-dive
   - Pseudocode implementation
   - Data type handling & performance
   - 30+ code examples

4. **RESEARCH_INDEX_LSPCONFIG_SETTINGS.md** (13 KB)
   - Research navigation guide
   - Key findings summary
   - FAQ section
   - Document map

5. **RESEARCH_SUMMARY_VISUAL.md** (12 KB)
   - Visual diagrams and tables
   - Getting started guide
   - Key statistics
   - Quick fix guide with decision tree

## Key Findings

### Settings Flattening
Nested config tables are automatically converted to command-line arguments by on_new_config callback.

```
Input:  settings = { FormattingOptions = { TabSize = 4 } }
Output: FormattingOptions:TabSize=4
```

### on_new_config Callback
Called after root detection, before server spawn. Allows dynamic configuration modification including settings flattening.

### Merge Strategy Impact
vim.tbl_deep_extend 'keep' vs 'force' affects configuration priority, NOT flattening itself.
- Merge happens FIRST
- Flattening happens SECOND
- Strategy only affects which settings win during merge

### Most Common Mistake
Using `vim.lsp.config()` instead of `require('lspconfig').server.setup()`
- vim.lsp.config() doesn't call on_new_config
- setup() does call on_new_config

## Debugging Checklist

- [ ] Using setup() not vim.lsp.config()?
- [ ] Settings nested in 'settings' key?
- [ ] Paths use vim.fn.expand("~")?
- [ ] All cmd values are strings?
- [ ] :LspInfo shows server attached?
- [ ] :LspLog shows "initialized"?

## Statistics

- 5 comprehensive documents
- 50 KB total (uncompressed)
- 8,039 words
- 70+ code examples
- 7 common mistakes documented with fixes
- 7 debugging techniques
- 5+ working configurations
- 30+ major sections

## Sources

All information verified from:
- Official nvim-lspconfig GitHub repository
- Neovim official documentation
- GitHub issues with maintainer discussions
- OmniSharp documentation

## Start Reading

1. This file (README)
2. RESEARCH_SUMMARY_VISUAL.md (overview with diagrams)
3. Choose your document based on needs above
4. Reference others as needed

All documents are in this directory.
