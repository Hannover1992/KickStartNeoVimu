# OmniSharp LSP with Roslyn Analyzers - Research Index

**Comprehensive Research Project**: How to properly configure OmniSharp LSP in kickstart.nvim
**Completion Date**: November 13, 2025
**Total Research Materials**: 4 comprehensive documents

---

## Navigation Guide

Start here to find what you need:

### If you're... then read...

**Just want it working?**
→ Start with: **OMNISHARP_IMPLEMENTATION_GUIDE.md** (Section: Quick Start 3-Step)

**Implementing the configuration?**
→ Use: **OMNISHARP_IMPLEMENTATION_GUIDE.md** (entire document)

**Troubleshooting a problem?**
→ Check: **OMNISHARP_GITHUB_ISSUES_REFERENCE.md** (troubleshooting section + issue catalog)

**Understanding how it all works?**
→ Read: **OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md** (complete technical guide)

**Getting overview of findings?**
→ See: **RESEARCH_SUMMARY_OMNISHARP_ROSLYN.md** (this summary + quick reference)

---

## Document Overview

### 1. OMNISHARP_IMPLEMENTATION_GUIDE.md
**Practical, hands-on implementation guide**

**Length**: ~1,500 words
**Format**: Copy-paste code + explanations
**Best for**: Getting configuration working

**Sections**:
- Quick Start (3 steps)
- Understanding settings flow
- Essential settings explained
- Complete configuration template
- Troubleshooting quick guide
- Settings reference table
- JSON file alternative
- Verification checklist

**Key code examples**: 12 complete working examples

---

### 2. OMNISHARP_GITHUB_ISSUES_REFERENCE.md
**Catalog of known issues with solutions**

**Length**: ~2,000 words
**Format**: Issue + cause + solution format
**Best for**: Debugging specific problems

**Contents**:
- Critical issues (setup called twice, Mason setup twice, etc.)
- Configuration issues (wrong cmd, case sensitivity)
- Roslyn-specific issues
- LSP configuration issues
- Debugging techniques
- Stack Overflow solutions
- Version-specific issues
- Common workarounds
- Quick reference table (12 issues)

**Most useful for**: Finding the exact problem and solution

---

### 3. OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md
**Comprehensive technical research**

**Length**: ~2,500 words
**Format**: Deep technical explanation with source code
**Best for**: Understanding the complete system

**Sections**:
- Executive summary (what you need to know)
- on_new_config function (heart of the system)
- cmd configuration (how to start OmniSharp)
- Settings configuration (all available options)
- Mason-lspconfig handler interaction
- Known issues and gotchas
- Step-by-step configuration guide (12 steps)
- Debugging commands
- Complete working example
- Common mistakes checklist
- References and sources

**Most useful for**: Getting deep understanding before implementing

---

### 4. RESEARCH_SUMMARY_OMNISHARP_ROSLYN.md
**Overview and quick reference**

**Length**: ~1,500 words
**Format**: Summary + quick reference tables
**Best for**: Getting the big picture

**Sections**:
- Key findings (8 critical discoveries)
- Critical configuration pattern
- Most common mistakes table
- How to verify it's working
- on_new_config algorithm (pseudocode)
- Required configuration
- Troubleshooting decision tree
- Quick reference table
- Testing checklist
- Summary

**Most useful for**: Understanding what's important

---

## Quick Lookup

### Finding Answers to Specific Questions

**Q: What is on_new_config?**
→ OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 1)

**Q: Why aren't my settings being applied?**
→ OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Issue 2: Mason setup twice)
→ OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Issue 1: setup() called twice)

**Q: What should cmd look like?**
→ OMNISHARP_IMPLEMENTATION_GUIDE.md (Understanding settings flow)
→ OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 2: cmd configuration)

**Q: Which settings do I actually need?**
→ OMNISHARP_IMPLEMENTATION_GUIDE.md (Essential settings explained)
→ OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 3: Settings configuration)

**Q: How do mason-lspconfig handlers work?**
→ OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 4: Handler interaction)
→ OMNISHARP_IMPLEMENTATION_GUIDE.md (Step 2)

**Q: Analyzers still not showing. What's wrong?**
→ RESEARCH_SUMMARY_OMNISHARP_ROSLYN.md (Troubleshooting decision tree)
→ OMNISHARP_IMPLEMENTATION_GUIDE.md (Troubleshooting quick guide)

**Q: Are my settings actually being used?**
→ OMNISHARP_IMPLEMENTATION_GUIDE.md (Verification checklist)
→ OMNISHARP_IMPLEMENTATION_GUIDE.md (Debugging: Check what's executing)

**Q: What version of OmniSharp/Neovim is needed?**
→ OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Version-specific issues)

**Q: Is there an example I can copy?**
→ OMNISHARP_IMPLEMENTATION_GUIDE.md (Complete configuration template)
→ OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 8: Complete working example)

---

## Key Findings at a Glance

### Finding 1: setup() Can Only Be Called Once
Only the first call to `lspconfig.omnisharp.setup()` takes effect. Subsequent calls are silently ignored. This is why handler-based configuration is essential.

**Where to learn more**:
- OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 4)
- OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Issue 1)

### Finding 2: on_new_config Flattens Settings Automatically
The settings table is automatically converted to command-line arguments by on_new_config, which runs when you call setup().

**Where to learn more**:
- OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 1)
- OMNISHARP_IMPLEMENTATION_GUIDE.md (Understanding settings flow)

### Finding 3: cmd Must Be Exactly Right
The cmd array must start with 'dotnet' and the full path to OmniSharp.dll. Using the wrapper script or wrong format causes failures.

**Where to learn more**:
- OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 2)
- OMNISHARP_IMPLEMENTATION_GUIDE.md (Understanding settings flow)

### Finding 4: Settings Use PascalCase in Lua
In Lua configuration, use `EnableAnalyzersSupport` not `enableAnalyzersSupport`. This is opposite to JSON files.

**Where to learn more**:
- OMNISHARP_IMPLEMENTATION_GUIDE.md (Understanding settings flow)
- OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Issue 7: Case sensitivity)

### Finding 5: Verify with ps aux, Not :LspInfo
Settings don't show in `:LspInfo` - they're flattened to command-line arguments. Use `ps aux | grep omnisharp` to verify.

**Where to learn more**:
- OMNISHARP_IMPLEMENTATION_GUIDE.md (Debugging section)
- OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Issue 5: Settings empty in :LspInfo)

### Finding 6: .editorconfig Required for Analyzer Rules
Roslyn analyzers need StyleCop.Analyzers package AND .editorconfig file with rules to enforce.

**Where to learn more**:
- OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Issue 4: .editorconfig not respected)
- OMNISHARP_IMPLEMENTATION_GUIDE.md (Troubleshooting)

### Finding 7: Handler Does All the Work
The mason-lspconfig handler automatically calls setup() with your servers config. No need for explicit setup() calls.

**Where to learn more**:
- OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 4)
- OMNISHARP_IMPLEMENTATION_GUIDE.md (Step 2)

### Finding 8: Mason Setup Should Only Happen Once
Mason.nvim configuration should happen only in the plugin dependency block, not again in the config function.

**Where to learn more**:
- OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Issue 2: Mason setup called twice)
- OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Part 5)

---

## Reading Recommendations by Experience Level

### For Beginners
1. Start with: OMNISHARP_IMPLEMENTATION_GUIDE.md (Quick Start section)
2. Then: RESEARCH_SUMMARY_OMNISHARP_ROSLYN.md (Overview)
3. Copy the template configuration
4. Use: OMNISHARP_IMPLEMENTATION_GUIDE.md (Troubleshooting) if needed

Estimated time: 30 minutes to working configuration

### For Intermediate Users
1. Read: OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (Parts 1-4)
2. Reference: OMNISHARP_IMPLEMENTATION_GUIDE.md for code
3. Debug with: OMNISHARP_GITHUB_ISSUES_REFERENCE.md if needed

Estimated time: 1-2 hours for complete understanding

### For Advanced Users
1. Read: OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md (entire, with source code analysis)
2. Study: OMNISHARP_GITHUB_ISSUES_REFERENCE.md (all issues and causes)
3. Reference: RESEARCH_SUMMARY_OMNISHARP_ROSLYN.md (for missing pieces)

Estimated time: 2-3 hours for expert-level understanding

---

## Most Common Implementation Patterns

### Pattern 1: Kickstart.nvim Default (Minimal)
```lua
local servers = {
  omnisharp = {
    cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll' },
    settings = {
      RoslynExtensionsOptions = { EnableAnalyzersSupport = true },
    },
  },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}
```

**Reference**: OMNISHARP_IMPLEMENTATION_GUIDE.md (Step 1)

### Pattern 2: Full Configuration (Recommended)
Includes solution path, logging, and all recommended settings.

**Reference**: OMNISHARP_IMPLEMENTATION_GUIDE.md (Complete configuration template)

### Pattern 3: Using omnisharp.json File
Alternative configuration method using JSON file instead of Lua.

**Reference**: OMNISHARP_IMPLEMENTATION_GUIDE.md (JSON file alternative)

### Pattern 4: WSL2 with Windows Path
Handling Windows filesystem paths in WSL2 Neovim.

**Reference**: OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Root directory detection)

---

## Essential Command Reference

### Verification Commands

```bash
# Check OmniSharp process and arguments
ps aux | grep omnisharp | grep -v grep

# Clear cache and restart
rm -rf ~/.cache/nvim/luac/ && pkill -f omnisharp

# View OmniSharp logs
tail -100 ~/.local/state/nvim/lsp.log

# Check if OmniSharp is installed
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

# Check if dotnet is available
dotnet --version
```

**Reference**: OMNISHARP_IMPLEMENTATION_GUIDE.md (Verification checklist)

### Neovim Commands

```vim
" Show LSP info
:LspInfo

" Show diagnostics
:lua vim.diagnostic.open_float()

" Restart OmniSharp
:LspRestart

" Open Mason (install OmniSharp)
:Mason

" View message history
:messages
```

**Reference**: OMNISHARP_IMPLEMENTATION_GUIDE.md (Verification checklist)

---

## Troubleshooting Quick Links

| Problem | Solution Location |
|---------|-------------------|
| Analyzers not showing | OMNISHARP_IMPLEMENTATION_GUIDE.md → Troubleshooting |
| Settings show empty in :LspInfo | OMNISHARP_GITHUB_ISSUES_REFERENCE.md → Issue 5 |
| OmniSharp won't start | OMNISHARP_IMPLEMENTATION_GUIDE.md → Troubleshooting |
| Settings appear twice | OMNISHARP_GITHUB_ISSUES_REFERENCE.md → Issue 1 |
| .editorconfig ignored | OMNISHARP_GITHUB_ISSUES_REFERENCE.md → Issue 4 |
| cmd format confusion | OMNISHARP_GITHUB_ISSUES_REFERENCE.md → Issue 6 |
| Case sensitivity issues | OMNISHARP_GITHUB_ISSUES_REFERENCE.md → Issue 7 |
| Mason configuration conflict | OMNISHARP_GITHUB_ISSUES_REFERENCE.md → Issue 2 |

---

## Configuration Checklist

Before implementation, ensure you have:
- [ ] Neovim 0.9+ (0.10+ recommended)
- [ ] kickstart.nvim cloned and in use
- [ ] mason.nvim installed
- [ ] OmniSharp installed via Mason
- [ ] .NET SDK installed
- [ ] C# project with solution file (.sln)
- [ ] StyleCop.Analyzers package (for analyzers)
- [ ] .editorconfig file in solution root (for rules)

**Reference**: OMNISHARP_IMPLEMENTATION_GUIDE.md (Quick Start Step 1)

---

## Source Material Statistics

### Research Conducted
- 8+ GitHub issues analyzed
- 5+ Stack Overflow posts reviewed
- 3+ technical blog articles studied
- Complete nvim-lspconfig source code reviewed
- OmniSharp configuration wiki studied
- Mason and Mason-lspconfig documentation reviewed

### Key Sources
1. **nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua** - Source code analysis
2. **OmniSharp/omnisharp-roslyn wiki** - Configuration options
3. **GitHub Issues** - kickstart.nvim #1297, omnisharp-roslyn #909, #2550, #2667, #2573
4. **Stack Overflow** - Real-world implementation patterns
5. **Dev community blogs** - Practical guides and workarounds

---

## Document Maintenance

### Last Updated
November 13, 2025

### Scope
Complete research on OmniSharp LSP configuration in kickstart.nvim

### Coverage
- ✅ on_new_config function
- ✅ cmd configuration patterns
- ✅ Settings options (all major ones)
- ✅ Mason-lspconfig handlers
- ✅ Known issues (8+ documented)
- ✅ Implementation guides
- ✅ Troubleshooting techniques
- ✅ GitHub issues analysis
- ✅ Code examples (15+ complete examples)

### Not Covered (Out of Scope)
- Other LSP servers (focus is OmniSharp)
- Neovim development/internals
- C# language specifics
- Project-specific .editorconfig rules

---

## Quick Reference Summary

**Essential Files to Edit**:
1. Your `~/.config/nvim/init.lua` (servers.omnisharp table)
2. `.editorconfig` in your solution root
3. `.csproj` file (ensure StyleCop.Analyzers is referenced)

**Most Important Settings**:
1. cmd: `{ 'dotnet', '/path/to/OmniSharp.dll', '-s', '/path/to/solution' }`
2. RoslynExtensionsOptions: `{ EnableAnalyzersSupport = true }`
3. FormattingOptions: `{ EnableEditorConfigSupport = true }`

**Most Important Concept**:
Settings → on_new_config (automatic) → command-line arguments → OmniSharp

**Most Important Verification**:
`ps aux | grep omnisharp` shows all your settings as arguments

---

## Getting Help

If you're stuck after reading all documents:

1. **Check**: OMNISHARP_GITHUB_ISSUES_REFERENCE.md (Issue table at end)
2. **Search**: For your specific error message or symptom
3. **Debug**: Using commands from OMNISHARP_IMPLEMENTATION_GUIDE.md
4. **Verify**: With checklist from RESEARCH_SUMMARY_OMNISHARP_ROSLYN.md

**Still stuck?**
- Check OmniSharp logs: `~/.local/state/nvim/lsp.log`
- Check process arguments: `ps aux | grep omnisharp`
- Clear cache: `rm -rf ~/.cache/nvim/luac/`
- Restart: Kill OmniSharp and restart Neovim

---

## Summary

Four comprehensive documents covering:
- **Technical deep-dive** (Research.md)
- **Practical implementation** (Guide.md)
- **Known issues** (Issues.md)
- **Quick overview** (Summary.md)

Everything needed to understand and configure OmniSharp LSP with Roslyn Analyzers in kickstart.nvim.

Start with OMNISHARP_IMPLEMENTATION_GUIDE.md for quick implementation.
Use others for reference and deeper understanding.

