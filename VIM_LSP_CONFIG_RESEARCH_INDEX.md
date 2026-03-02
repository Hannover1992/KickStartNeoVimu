# vim.lsp.config API Research - Documentation Index

**Research Date**: 2025-11-13
**Neovim Version**: 0.11.4
**Status**: COMPLETE ✅

---

## Documentation Overview

This research provides comprehensive documentation on Neovim 0.11's native `vim.lsp.config()` and `vim.lsp.enable()` API, including migration from nvim-lspconfig, mason-lspconfig v2.x compatibility, and OmniSharp-specific considerations.

**Total Documentation**: 3 files (~41 KB, ~550 lines)

---

## Files

### 1. VIM_LSP_CONFIG_RESEARCH_SUMMARY.md (11 KB)

**Purpose**: Executive summary and quick findings

**Contents**:
- Mission objectives and completion status
- Key findings and current init.lua status
- Complete working examples (4 patterns)
- Verification checklist
- Troubleshooting guide
- Recommendations
- Quick reference card

**Target Audience**: Developers who need quick answers

**Use Case**: "What's the current status? Do I need to change anything?"

**Key Takeaway**: Current init.lua is OPTIMAL - no changes needed!

---

### 2. VIM_LSP_CONFIG_QUICK_REFERENCE.md (6 KB)

**Purpose**: Quick lookup for API usage and common patterns

**Contents**:
- API signatures (vim.lsp.config, vim.lsp.enable)
- Common patterns (4 usage patterns)
- OmniSharp special case
- Mason-lspconfig v2.x integration
- Migration from lspconfig.setup()
- Verification commands
- Troubleshooting table
- Common mistakes

**Target Audience**: Developers writing LSP config code

**Use Case**: "How do I configure a server? What's the correct syntax?"

**Key Sections**:
- Pattern 1: Simple server setup
- Pattern 2: With FileType autocmd
- Pattern 3: Multiple servers
- Pattern 4: Hybrid (compatibility)

---

### 3. VIM_LSP_CONFIG_API_RESEARCH.md (24 KB)

**Purpose**: Comprehensive deep-dive documentation

**Contents** (12 sections):
1. Executive Summary
2. vim.lsp.config() API Documentation
3. vim.lsp.enable() API Documentation
4. Complete Working Examples (4 examples)
5. Mason-lspconfig Compatibility (v2.x migration)
6. FileType Autocmd + vim.lsp.enable() Pattern
7. Breaking Changes: lspconfig vs Native API
8. OmniSharp-Specific Considerations
9. Best Practices Summary
10. Verification Commands
11. Troubleshooting
12. Conclusion

**Target Audience**: Developers, maintainers, researchers

**Use Case**: "I need to understand everything about vim.lsp.config"

**Key Sections**:
- Section 2: Complete API documentation
- Section 5: Mason-lspconfig v2.x breaking changes
- Section 7: Deprecation timeline
- Section 8: OmniSharp settings flattening issue

---

## Quick Navigation

### I need to...

**...know if current config is correct**
→ Read: `VIM_LSP_CONFIG_RESEARCH_SUMMARY.md` (Section: "Key Findings")
→ Answer: YES, current init.lua is optimal!

**...configure a new server**
→ Read: `VIM_LSP_CONFIG_QUICK_REFERENCE.md` (Section: "Common Patterns")
→ Use: Pattern 2 (With FileType autocmd)

**...migrate from lspconfig.setup()**
→ Read: `VIM_LSP_CONFIG_QUICK_REFERENCE.md` (Section: "Migration from lspconfig.setup()")
→ Follow: Before/After examples

**...configure OmniSharp**
→ Read: `VIM_LSP_CONFIG_QUICK_REFERENCE.md` (Section: "OmniSharp (C#) - Special Case")
→ Use: `require('lspconfig').omnisharp.setup()` (NOT vim.lsp.config!)

**...understand mason-lspconfig v2.x changes**
→ Read: `VIM_LSP_CONFIG_API_RESEARCH.md` (Section 5: "Mason-lspconfig Compatibility")
→ Key: `handlers` removed, `automatic_enable` added

**...troubleshoot LSP issues**
→ Read: `VIM_LSP_CONFIG_RESEARCH_SUMMARY.md` (Section: "Troubleshooting Guide")
→ Check: Table of symptoms/solutions

**...understand deprecation timeline**
→ Read: `VIM_LSP_CONFIG_API_RESEARCH.md` (Section 7: "Breaking Changes")
→ Status: `require('lspconfig')` deprecated, plugin NOT deprecated

**...understand why OmniSharp is special**
→ Read: `VIM_LSP_CONFIG_API_RESEARCH.md` (Section 8: "OmniSharp-Specific Considerations")
→ Issue: Settings must be flattened to CLI args, vim.lsp.config() doesn't do this

---

## Key Research Findings

### 1. Current Configuration Status

**File**: `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`
**Lines**: 745-783
**Status**: OPTIMAL ✅

**Pattern Used**:
```lua
if vim.fn.has('nvim-0.11') == 1 then
  vim.lsp.config(server_name, config)
  vim.api.nvim_create_autocmd('FileType', {
    pattern = config.filetypes,
    callback = function(ev)
      vim.lsp.enable(server_name, ev.buf)
    end,
  })
else
  require('lspconfig')[server_name].setup(config)
end
```

**Why Optimal**:
- Uses native vim.lsp.config() on Neovim 0.11+
- Falls back to lspconfig.setup() for older versions
- Explicitly controls activation with FileType autocmd
- Passes buffer number to vim.lsp.enable()
- Compatible with mason-lspconfig v2.x

### 2. API Overview

**vim.lsp.config({name}, {cfg})**
- Define or customize LSP server configuration
- Available since Neovim 0.11.0
- Merges with configs from lsp/*.lua files

**vim.lsp.enable({name}, {enable})**
- Auto-start LSP based on filetypes/root_markers
- Available since Neovim 0.11.0
- Requires buffer number in FileType autocmd: `vim.lsp.enable(name, ev.buf)`

### 3. Mason-lspconfig v2.x

**Breaking Changes**:
- Removed: `handlers`, `automatic_installation`, `.setup_handlers()`
- Added: `automatic_enable` (default: true)

**Migration**:
- Old: Configure servers in handler callbacks
- New: Configure with vim.lsp.config(), let mason-lspconfig enable

**Current Approach**:
- Set `automatic_enable = false`
- Manually call vim.lsp.config() + vim.lsp.enable()
- Full control over server activation

### 4. OmniSharp Critical Information

**DO NOT use vim.lsp.config() for OmniSharp!**

**Issue**: Settings not flattened to CLI args
- Example: `settings.RoslynExtensionsOptions.EnableAnalyzersSupport = true`
- Should become: `RoslynExtensionsOptions:EnableAnalyzersSupport=true` (CLI arg)
- vim.lsp.config() does NOT do this transformation

**Solution**: Use lspconfig.setup()
```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '/solution' },
  settings = {
    RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
  }
})
```

**Why It Works**:
- lspconfig's `on_new_config` handler flattens settings
- All settings appear in process command line
- User confirmed: "yes motherfuck es lafue jez" (it works!)

### 5. Deprecation Timeline

**Deprecated**:
- `require('lspconfig')` module → Warnings now, errors in future, removed in v3.0.0
- `lspconfig[server].setup()` method → Being phased out

**NOT Deprecated**:
- nvim-lspconfig plugin → Still required (provides config data)
- Config files in lsp/*.lua → Read by vim.lsp.config()

---

## Verification Checklist

After configuring LSP:

- [ ] `:checkhealth vim.lsp` - Check LSP health
- [ ] `:LspInfo` - Verify client attached, check cmd and settings
- [ ] `ps aux | grep server` - Verify process command line
- [ ] `:lua print(vim.inspect(vim.lsp.config.server))` - Check config
- [ ] `:lua print(vim.inspect(vim.lsp.get_clients()))` - List clients
- [ ] `tail -f ~/.local/state/nvim/lsp.log` - Check logs
- [ ] Test LSP features (gd, grr, K)

**For OmniSharp specifically**:
- [ ] `ps aux | grep omnisharp | grep "EnableAnalyzersSupport=true"`
- [ ] Check StyleCop warnings appear in code
- [ ] Test go-to-definition, references, hover

---

## Common Issues and Solutions

| Issue | Diagnosis | File | Section |
|-------|-----------|------|---------|
| LSP not attaching | Missing FileType autocmd | Quick Reference | Troubleshooting |
| Settings not applied | OmniSharp needs lspconfig.setup() | API Research | Section 8 |
| Deprecation warnings | Using require('lspconfig') | API Research | Section 7 |
| Multiple LSP instances | Missing buffer number in enable() | Quick Reference | Common Mistakes |
| Auto-enable conflicts | mason-lspconfig automatic_enable=true | API Research | Section 5 |

---

## Recommendations

### For Current Setup

**NO ACTION REQUIRED** ✅

Current init.lua is already following best practices. Continue using:
- vim.lsp.config() for Neovim 0.11+
- lspconfig.setup() fallback for older versions
- Explicit FileType autocmd with buffer number
- automatic_enable = false for manual control

### For Future Migrations

When migrating other servers (NOT OmniSharp):
1. Replace lspconfig.setup() with vim.lsp.config()
2. Add FileType autocmd with vim.lsp.enable(name, ev.buf)
3. Keep nvim-lspconfig installed
4. Test thoroughly with :LspInfo and ps aux

### For OmniSharp

**NEVER migrate OmniSharp to pure vim.lsp.config()!**
- Keep using require('lspconfig').omnisharp.setup()
- lspconfig provides critical on_new_config handler
- User confirmed it works correctly

---

## Resources

### Official Documentation
- Neovim LSP: https://neovim.io/doc/user/lsp.html
- Neovim 0.11 News: https://neovim.io/doc/user/news-0.11.html
- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig
- mason-lspconfig: https://github.com/mason-org/mason-lspconfig.nvim

### Blog Posts
- What's New in Neovim 0.11: https://gpanders.com/blog/whats-new-in-neovim-0-11/
- Neovim LSP 0.11: https://davelage.com/posts/neovim-lsp-0.11/
- Native LSP Config: https://0xunicorn.com/neovim-native-lsp-config/
- Mason 2.0 Changes: https://kosu.me/blog/breaking-changes-in-mason-2-0-how-i-updated-my-neovim-lsp-config

### GitHub Discussions
- OmniSharp vim.lsp.config Issue: https://github.com/neovim/neovim/discussions/35175
- Mason Migration Guide: https://github.com/mason-org/mason.nvim/discussions/2023

---

## File Size Summary

```
VIM_LSP_CONFIG_API_RESEARCH.md        24 KB  (Deep-dive, 12 sections)
VIM_LSP_CONFIG_QUICK_REFERENCE.md      6 KB  (Quick lookup)
VIM_LSP_CONFIG_RESEARCH_SUMMARY.md    11 KB  (Executive summary)
VIM_LSP_CONFIG_RESEARCH_INDEX.md       8 KB  (This file)
─────────────────────────────────────────────
TOTAL                                 49 KB  (~750 lines)
```

---

## Quick Start Guide

**New to vim.lsp.config?**
1. Start with: `VIM_LSP_CONFIG_RESEARCH_SUMMARY.md`
2. Read: "Key Findings" section
3. Copy example: Pattern 2 (FileType autocmd)
4. Verify with: `:checkhealth vim.lsp`

**Migrating from lspconfig?**
1. Read: `VIM_LSP_CONFIG_QUICK_REFERENCE.md`
2. Section: "Migration from lspconfig.setup()"
3. Follow: Before/After example
4. Test each server individually

**Configuring OmniSharp?**
1. Read: `VIM_LSP_CONFIG_QUICK_REFERENCE.md`
2. Section: "OmniSharp (C#) - Special Case"
3. Use: lspconfig.setup() NOT vim.lsp.config()
4. Verify: `ps aux | grep omnisharp`

**Debugging LSP issues?**
1. Read: `VIM_LSP_CONFIG_RESEARCH_SUMMARY.md`
2. Section: "Troubleshooting Guide"
3. Check: Symptom/Solution table
4. Run: Verification commands

---

## Conclusion

This research confirms that **the current Neovim configuration is production-ready and requires no changes**. The hybrid approach using vim.lsp.config() with FileType autocmd provides optimal functionality for Neovim 0.11+ while maintaining backward compatibility.

**Key Takeaways**:
1. Current init.lua is OPTIMAL ✅
2. Use vim.lsp.config() for new servers (except OmniSharp)
3. Keep using lspconfig.setup() for OmniSharp
4. Always pass buffer number to vim.lsp.enable() in autocmds
5. nvim-lspconfig plugin is still required

**Status**: COMPLETE ✅
**Action Required**: None (current config is optimal)

---

**Documentation Index - End**
