# Mason & OmniSharp Research - Complete Documentation

## Overview

This directory contains comprehensive research on how Mason.nvim, mason-lspconfig, and nvim-lspconfig work together to configure OmniSharp for Neovim C# development.

**Research Date:** November 2025
**Scope:** Mason GitHub repository, GitHub issues (#38, #455, #701, #1280, #1651, #1974), Stack Exchange, official documentation
**Purpose:** Understanding OmniSharp configuration, Mason defaults, and proper setup patterns

---

## Quick Navigation

### Start Here

1. **[RESEARCH_SUMMARY.txt](./RESEARCH_SUMMARY.txt)** - Executive summary of all findings (11KB)
   - Key findings answered directly
   - Architecture flow
   - Recommended configuration
   - Common mistakes

2. **[MASON_OMNISHARP_KEY_FINDINGS.md](./MASON_OMNISHARP_KEY_FINDINGS.md)** - Critical technical insights (9.3KB)
   - Direct answers to core questions
   - on_new_config function behavior
   - Multiple setup() calls issue
   - Verification commands

### Implementation Guides

3. **[MASON_OMNISHARP_INIT_LUA_GUIDE.md](./MASON_OMNISHARP_INIT_LUA_GUIDE.md)** - How to configure your init.lua (12KB)
   - Step-by-step configuration
   - DCSRE project specific settings
   - Troubleshooting guide
   - Common mistakes to avoid

### Detailed Research

4. **[MASON_OMNISHARP_RESEARCH.md](./MASON_OMNISHARP_RESEARCH.md)** - Comprehensive deep-dive (18KB)
   - Installation architecture
   - Settings propagation flow
   - Known issues (GitHub #701, #1974, #38, #1280, #1651, #455)
   - Best practices checklist
   - Platform-specific guidance

---

## Key Questions Answered

### 1. Does Mason set a default cmd when it installs omnisharp?

**Answer:** NO

- nvim-lspconfig explicitly does NOT set a default cmd for OmniSharp
- Official quote: "omnisharp-roslyn doesn't have a cmd set by default because nvim-lspconfig does not make assumptions about your path"
- You MUST provide the cmd configuration yourself

**See:** RESEARCH_SUMMARY.txt → KEY FINDINGS section 1

---

### 2. What is the Mason OmniSharp wrapper script vs direct DLL call?

**Wrapper Script (Mason's default):**
- Located at: `~/.local/share/nvim/mason/bin/omnisharp`
- Extra subprocess indirection
- Fails on Windows with spaces in usernames (GitHub Issue #455)
- Platform-specific compatibility issues

**Direct DLL Call (Recommended):**
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
}
```
- Direct execution via dotnet runtime
- Works reliably on Windows with spaces in usernames
- Matches official nvim-lspconfig examples
- Clearer debugging (full command visible in ps aux)

**See:** MASON_OMNISHARP_KEY_FINDINGS.md → Key Question 2

---

### 3. Does mason-lspconfig automatically setup omnisharp if installed?

**Answer:** YES, with caveats

**Default Handler Behavior:**
- Runs for EVERY installed server automatically
- Looks up server config in `servers[server_name]` table
- Calls `lspconfig.omnisharp.setup()` with that config
- Works correctly IF `servers.omnisharp` is properly defined

**Automatic Enable (v2.0+):**
- `automatic_enable = true` calls `vim.lsp.enable()`
- But still requires proper handler setup
- Can exclude: `automatic_enable = { exclude = { 'omnisharp' } }`

**See:** MASON_OMNISHARP_KEY_FINDINGS.md → Key Question 3

---

### 4. How to opt-out of mason's auto-configuration

**Option A: Skip in handler**
- Return early for omnisharp in handler
- Call setup() manually afterwards
- Problem: setup() can only be called once

**Option B: Use automatic_enable exclusion**
- Prevents vim.lsp.enable() for omnisharp
- Still need manual handler or setup

**Option C: Use servers table correctly (RECOMMENDED)**
- Define `servers.omnisharp` with full config
- Handler picks it up automatically
- No double setup() calls
- Clean and reliable

**See:** MASON_OMNISHARP_KEY_FINDINGS.md → Key Question 4

---

## Critical Technical Discoveries

### Discovery 1: on_new_config Function

nvim-lspconfig's omnisharp config has an `on_new_config` function that:

1. Takes your base cmd array
2. Appends hard-coded arguments (-z, --hostPID, --encoding, --languageserver)
3. **FLATTENS settings into command-line arguments**

Example:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  }
}
```

Becomes: `RoslynExtensionsOptions:EnableAnalyzersSupport=true` appended to cmd

**Result:** You don't manually convert settings to arguments - it's automatic!

**See:** MASON_OMNISHARP_KEY_FINDINGS.md → Critical Discovery: on_new_config

---

### Discovery 2: Multiple setup() Calls Problem

**Critical Issue:** `require('lspconfig').omnisharp.setup()` can only be called ONCE

```lua
-- Call 1: Handler calls setup (from mason-lspconfig)
require('mason-lspconfig').setup {
  handlers = { function(server_name)
    require('lspconfig')[server_name].setup(servers[server_name])
  end }
}

-- Call 2: You try to override with explicit setup
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', '/custom/path/OmniSharp.dll' }
})
-- ❌ THIS IS IGNORED - Call 1's config is still used!
```

**Solution:** Ensure handler has correct config the first time

**See:** MASON_OMNISHARP_KEY_FINDINGS.md → Critical Problem: Multiple setup() Calls

---

## Recommended Configuration for DCSRE Project

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
      '-loglevel', 'Information',
    },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
        EnableImportCompletion = true,
        AnalyzeOpenDocumentsOnly = false,
      },
      FormattingOptions = {
        EnableEditorConfigSupport = true,
        OrganizeImports = true,
      },
    },
  },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

Add to servers table in init.lua, let handler call setup() - done!

**See:** MASON_OMNISHARP_INIT_LUA_GUIDE.md → Configuration Template

---

## Known Issues & Solutions

| Issue | GitHub | Symptom | Solution |
|-------|--------|---------|----------|
| Incomplete Installation | #701 | Only 3 files extracted | Manual installation from releases |
| Case Sensitivity | #1974 | Binary 'OmniSharp' vs 'omnisharp' | Use Mason v2.0.0+ or override cmd |
| Windows Spaces | #455 | Wrapper fails with spaces in path | Use direct DLL call |
| omnisharp-mono | #1280 | Startup script not generated | Use omnisharp (Roslyn) instead |
| Windows Compat | #38 | OmniSharp doesn't work natively | Use WSL2 or csharp.nvim |
| M1/M2 Mac | #1651 | Installs x64 on ARM64 | Use csharp.nvim or manual setup |

**See:** MASON_OMNISHARP_RESEARCH.md → Known Issues with Mason + OmniSharp

---

## Verification Methods

### Check 1: LSP Info
```vim
:LspInfo
```
Should show:
- `omnisharp (attached) (initialized)`
- cmd starts with `"dotnet"` and includes your settings
- settings show `RoslynExtensionsOptions`, `FormattingOptions`

### Check 2: Running Process
```bash
ps aux | grep omnisharp | grep -v grep
```
Should show full command with:
- `-s <solution-path>`
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
- `FormattingOptions:EnableEditorConfigSupport=true`

### Check 3: Test Features
```vim
K          " Hover documentation
gd         " Go to definition
grr        " Find references
<leader>ca " Code actions
```

**See:** RESEARCH_SUMMARY.txt → VERIFICATION METHODS

---

## Common Mistakes to Avoid

### ❌ Don't Call setup() Twice
```lua
-- In handler
require('lspconfig').omnisharp.setup(servers.omnisharp)

-- Then later - IGNORED!
require('lspconfig').omnisharp.setup({...})
```

### ✅ Do Put Everything in servers.omnisharp
```lua
servers.omnisharp = {
  cmd = {...},
  settings = {...},
}
-- Handler calls setup once with full config
```

---

### ❌ Don't Use Wrapper Script on Windows with Spaces
```lua
cmd = { vim.fn.stdpath('data') .. '/mason/bin/omnisharp' }
```

### ✅ Do Use Direct DLL Call
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
}
```

---

### ❌ Don't Use Tilde for Path Expansion
```lua
'-s', '~/path/to/solution',
```

### ✅ Do Use Absolute Paths
```lua
'-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
```

**See:** RESEARCH_SUMMARY.txt → COMMON MISTAKES

---

## Document Organization

### Entry Points (Pick One Based on Your Need)

- **Quick Summary:** RESEARCH_SUMMARY.txt (11KB, 5-10 min read)
- **Key Findings:** MASON_OMNISHARP_KEY_FINDINGS.md (9.3KB, 10 min read)
- **Practical Setup:** MASON_OMNISHARP_INIT_LUA_GUIDE.md (12KB, 15 min read)
- **Deep Dive:** MASON_OMNISHARP_RESEARCH.md (18KB, 30 min read)

### Complete Document List

**Primary Documents (November 2025 Research):**
- RESEARCH_SUMMARY.txt
- MASON_OMNISHARP_KEY_FINDINGS.md
- MASON_OMNISHARP_INIT_LUA_GUIDE.md
- MASON_OMNISHARP_RESEARCH.md

**Supporting Documents (From Agent Research):**
- MASON_OMNISHARP_ACTION_PLAN.md
- MASON_RESEARCH_COMPLETION_REPORT.txt
- MASON_LSPCONFIG_* (multiple documents with detailed analysis)

**Legacy Documentation:**
- CLAUDE.md (Original StyleCop issue and solutions)

---

## Architecture Overview

```
Neovim Start
    ↓
Load init.lua (define servers.omnisharp with cmd and settings)
    ↓
Load mason-lspconfig plugin
    ↓
require('mason-lspconfig').setup({ handlers = {...} })
    ↓
For EACH installed server:
    - Handler runs
    - Gets servers[server_name] config
    - Calls require('lspconfig')[server_name].setup(config)
    ↓
For omnisharp specifically:
    - Handler gets servers.omnisharp
    - Calls require('lspconfig').omnisharp.setup(servers.omnisharp)
    - on_new_config flattens settings to command-line args
    - OmniSharp process starts with full configuration
    ↓
When you open C# file:
    - LSP client connects to OmniSharp
    - All features work (formatting, diagnostics, completion)
```

---

## Key References

**Official Repositories:**
- Mason.nvim: https://github.com/mason-org/mason.nvim
- mason-lspconfig: https://github.com/williamboman/mason-lspconfig.nvim
- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig
- OmniSharp-Roslyn: https://github.com/OmniSharp/omnisharp-roslyn

**Community Resources:**
- Stack Exchange: https://vi.stackexchange.com/questions/43830
- Neovim Discourse: https://neovim.discourse.group/
- csharp.nvim: https://github.com/iabdelkareem/csharp.nvim (alternative)

---

## Conclusion

**Key Insights:**

1. Mason installs the binary but doesn't configure cmd (nvim-lspconfig design)
2. Direct DLL call is more reliable than wrapper script
3. mason-lspconfig handlers automatically apply your configuration
4. on_new_config automatically flattens settings to command-line arguments
5. Proper configuration prevents issues - follows the documented pattern

**Recommended Approach:**
- Define `servers.omnisharp` with cmd and settings
- Use direct DLL call via `dotnet` + DLL path
- Let mason-lspconfig handler call `setup()` once
- Verify with `:LspInfo` and `ps aux`
- All features work automatically

The configuration is robust when settings are properly applied through the handler without duplicate `setup()` calls or wrapper script indirection.

---

## Next Steps

1. **Read RESEARCH_SUMMARY.txt** (5-10 min) for executive summary
2. **Read MASON_OMNISHARP_INIT_LUA_GUIDE.md** (15 min) for step-by-step setup
3. **Add omnisharp to your servers table** in init.lua
4. **Install via Mason:** `:Mason` → find omnisharp → press 'i'
5. **Test:** Open a C# file and check `:LspInfo`
6. **Verify:** Run `ps aux | grep omnisharp` to confirm settings are applied
7. **Troubleshoot** using MASON_OMNISHARP_RESEARCH.md if needed

---

**Questions?** Refer to the appropriate document:
- "How do I...?" → MASON_OMNISHARP_INIT_LUA_GUIDE.md
- "Why does...?" → MASON_OMNISHARP_RESEARCH.md
- "What is...?" → MASON_OMNISHARP_KEY_FINDINGS.md
- "Quick summary?" → RESEARCH_SUMMARY.txt
