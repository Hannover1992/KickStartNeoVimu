# LSP Specification Research - Document Index

This directory contains comprehensive research on the Language Server Protocol (LSP) specification for configuring language servers, with a focus on OmniSharp.

## Document Overview

### 1. **LSP_QUICK_REFERENCE.md** (5.1 KB)
**Start here for a fast answer!**

Quick lookup card with the essential information:
- One-minute overview of the three configuration mechanisms
- When to use what
- OmniSharp template
- Common mistakes
- Timing reference

**Best for:** Getting a quick answer, memorizing the key concepts

---

### 2. **LSP_RESEARCH_SUMMARY.md** (15 KB)
**Executive summary with key findings**

Comprehensive summary of research findings:
- Executive summary of LSP mechanisms
- Key findings about timing and application
- Official LSP specification details
- Alternative configuration methods
- OmniSharp-specific guidance
- Common misconceptions
- Troubleshooting guide

**Best for:** Understanding the big picture, finding answers to specific questions

---

### 3. **LSP_SPECIFICATION_RESEARCH.md** (16 KB)
**Deep dive into official LSP specification**

Complete technical details from the LSP 3.17 specification:
- InitializeParams and initializationOptions field specification
- workspace/didChangeConfiguration notification details
- Command-line arguments vs initialization options
- Complete timeline of when settings are applied
- All alternative methods to pass settings
- Official specification links and references
- OmniSharp-specific settings
- Type definitions and interfaces

**Best for:** Technical implementation, understanding the specification in detail

---

### 4. **LSP_SETTINGS_TIMING_DIAGRAM.md** (31 KB)
**Visual timing and flow diagrams**

ASCII diagrams showing:
- Complete LSP initialization sequence (6 phases)
- Settings application timeline
- Three paths to configuration (illustrated)
- Decision tree for choosing configuration method
- Complete working examples
- Summary table of timing

**Best for:** Visual learners, understanding timing relationships

---

### 5. **OMNISHARP_LSP_SETTINGS_GUIDE.md** (18 KB)
**OmniSharp-specific implementation guide**

Practical guide for configuring OmniSharp:
- Official configuration structure (all three layers)
- OmniSharp LSP settings reference
  - Analyzer settings
  - Formatting settings
  - Completion settings
  - Logging settings
  - Reference code lens
- Command-line arguments vs settings
- Complete working example
- Minimal configuration
- Debugging configuration issues
- How settings flow in practice

**Best for:** Implementing OmniSharp configuration, solving configuration problems

---

### 6. **LSP_SETTINGS_DEBUGGING_GUIDE.md** (8.7 KB)
**Quick debugging reference**

Troubleshooting guide for configuration issues:
- How settings are passed to servers
- Verification steps
- Common issues and solutions
- Logging and inspection
- Testing specific features

**Best for:** Fixing configuration problems, verifying settings are applied

---

## How to Use This Research

### If you have 1 minute:
→ Read **LSP_QUICK_REFERENCE.md**

### If you have 5 minutes:
→ Read **LSP_RESEARCH_SUMMARY.md** (first 3 sections)

### If you want to implement OmniSharp:
→ Read **OMNISHARP_LSP_SETTINGS_GUIDE.md** and **LSP_QUICK_REFERENCE.md**

### If you need to debug a problem:
→ Read **LSP_SETTINGS_DEBUGGING_GUIDE.md**

### If you want complete technical details:
→ Read **LSP_SPECIFICATION_RESEARCH.md**

### If you're a visual learner:
→ Read **LSP_SETTINGS_TIMING_DIAGRAM.md**

### If you want everything:
→ Read all documents in order:
1. LSP_QUICK_REFERENCE.md
2. LSP_RESEARCH_SUMMARY.md
3. LSP_SETTINGS_TIMING_DIAGRAM.md
4. LSP_SPECIFICATION_RESEARCH.md
5. OMNISHARP_LSP_SETTINGS_GUIDE.md
6. LSP_SETTINGS_DEBUGGING_GUIDE.md

---

## Key Concepts (TL;DR)

### The Three Configuration Layers

**Layer 1: Process Control (`cmd`)**
- When: T0 (when spawning the server process)
- Example: `cmd = { 'omnisharp', '--stdio' }`
- Changeable: No
- Purpose: How the server is started

**Layer 2: Initialization (`init_options`)**
- When: T2 (during initialize request)
- Example: `init_options = { ... }`
- Changeable: No (one-time only)
- Purpose: Server startup parameters

**Layer 3: Runtime Configuration (`settings`)**
- When: T5+ (after initialized notification)
- Example: `settings = { omnisharp = { ... } }`
- Changeable: Yes (via workspace/didChangeConfiguration)
- Purpose: Dynamic server configuration

### The Timeline

```
T0: Server spawns        → cmd args applied
T2: Initialize request   → initializationOptions sent
T2.5: Server processes   → initializationOptions applied
T4: Initialized event    → Server ready for RPC
T5: didChangeConfig      → settings sent
T5.5: Server processes   → settings applied
T6+: Normal operation    → All configurations active
```

### Official LSP Specification
- **Latest:** https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- **InitializeParams:** Initialize Request section
- **workspace/didChangeConfiguration:** Workspace Features section

---

## Quick Answer Reference

### "How do I configure OmniSharp?"

```lua
lspconfig.omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'), '--stdio' },
  settings = {
    omnisharp = {
      enableRoslynAnalyzers = true,
      organizeImportsOnFormat = true,
      enableImportCompletion = true,
    }
  }
})
```

### "Where do I put my settings?"

In the `settings` field, under `omnisharp` key.

### "Can I change settings without restarting?"

Yes, if they're in `settings` (not `init_options`).

### "What's the difference between init_options and settings?"

- `init_options` → sent once during initialization
- `settings` → sent after server is ready, can be updated

### "Are my settings being applied?"

Check:
1. `:LspInfo` - verify OmniSharp is attached
2. `:!tail -f ~/.local/state/nvim/lsp.log` - check for didChangeConfiguration

### "Why doesn't my configuration work?"

Most likely causes:
1. Using `init_options` for dynamic settings (should use `settings`)
2. Putting settings in `cmd` (should use `settings`)
3. Using wrong key names (check OmniSharp documentation)
4. Server not attached (run `:LspInfo`)

---

## Key Findings from Research

1. **LSP spec clearly defines three mechanisms** - cmd, initializationOptions, and workspace/didChangeConfiguration

2. **Settings are NOT sent during initialization** - They're sent via workspace/didChangeConfiguration after the initialized notification

3. **Timing is critical** - Different configuration mechanisms apply at different times in the LSP lifecycle

4. **workspace/didChangeConfiguration is the primary method** for runtime configuration in LSP

5. **Each server defines its own setting structure** - No universal standard, must check server documentation

6. **Command-line args are for process control only** - Not for server configuration

7. **init_options are one-time only** - Use settings for dynamic configuration

8. **Most servers support pulling configuration** via workspace/configuration requests

---

## Research Sources

### Official LSP Specification
- LSP 3.17: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- LSP 3.18: https://github.com/Microsoft/language-server-protocol/blob/gh-pages/_specifications/lsp/3.18/specification.md

### Type Definitions
- Rust (lsp_types): https://docs.rs/lsp-types/latest/lsp_types/struct.InitializeParams.html
- Java (LSP4j): https://javadoc.io/static/org.eclipse.lsp4j/org.eclipse.lsp4j/0.12.0/org/eclipse/lsp4j/InitializeParams.html

### Implementation Guides
- Neovim: https://neovim.io/doc/user/lsp.html
- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig
- VSCode: https://code.visualstudio.com/api/language-extensions/language-server-extension-guide

---

## Document Statistics

| Document | Size | Focus | Level |
|----------|------|-------|-------|
| LSP_QUICK_REFERENCE.md | 5.1 KB | Key concepts | Beginner |
| LSP_RESEARCH_SUMMARY.md | 15 KB | Executive summary | Beginner-Intermediate |
| LSP_SETTINGS_TIMING_DIAGRAM.md | 31 KB | Visual explanation | Intermediate |
| LSP_SPECIFICATION_RESEARCH.md | 16 KB | Technical details | Advanced |
| OMNISHARP_LSP_SETTINGS_GUIDE.md | 18 KB | OmniSharp-specific | Intermediate |
| LSP_SETTINGS_DEBUGGING_GUIDE.md | 8.7 KB | Troubleshooting | Intermediate |
| **Total** | **~94 KB** | Comprehensive research | All levels |

---

## What This Research Covers

✅ Official LSP 3.17 specification
✅ InitializeParams and settings field
✅ workspace/didChangeConfiguration notification
✅ Command-line args vs initialization options
✅ Timing of settings application
✅ Alternative configuration methods
✅ Links to official specifications
✅ OmniSharp-specific guidance
✅ Practical examples
✅ Debugging and verification
✅ Visual timing diagrams
✅ Common mistakes and misconceptions

## What This Research Does NOT Cover

- Language server implementation details
- Server-specific configuration (except OmniSharp)
- Neovim plugin architecture
- LSP features beyond configuration (like diagnostics, completion, etc.)

---

## Next Steps

1. **Understand the concepts** - Read one of the first three documents
2. **Implement your configuration** - Use OMNISHARP_LSP_SETTINGS_GUIDE.md
3. **Verify it works** - Use LSP_SETTINGS_DEBUGGING_GUIDE.md
4. **Debug if needed** - Refer back to appropriate sections

---

## Questions Answered by This Research

- What is the official LSP mechanism for passing settings?
- How are settings sent to language servers?
- When do settings take effect?
- What's the difference between cmd, init_options, and settings?
- Can I change settings without restarting the server?
- How do I configure OmniSharp correctly?
- Where can I find the official LSP specification?
- How do I debug configuration issues?
- What are common mistakes in LSP configuration?
- How does the LSP initialization sequence work?

---

## Related Documents in Repository

- **CLAUDE.md** - Project instructions and workflow documentation
- **OMNISHARP_CMD_PARAMETER_ANALYSIS.md** - OmniSharp command-line parameter analysis
- **OMNISHARP_CMD_QUICK_REFERENCE.md** - OmniSharp command reference
- **README_OMNISHARP_RESEARCH.md** - OmniSharp research overview

---

## Feedback and Updates

This research was conducted on November 12, 2025, based on:
- LSP Specification 3.17
- Official Microsoft LSP documentation
- Neovim LSP documentation
- nvim-lspconfig implementation

The core concepts remain stable across LSP versions, but always check the official specification at:
https://microsoft.github.io/language-server-protocol/

---

Last Updated: November 12, 2025
Research Focus: LSP Settings Specification
Target Application: OmniSharp in Neovim

