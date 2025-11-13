# OmniSharp Roslyn Analyzers Configuration - Research Summary

**Research Date**: November 13, 2025
**Scope**: Complete investigation of OmniSharp LSP configuration in kickstart.nvim
**Status**: COMPLETE with 4 comprehensive guides created

---

## Documents Created

### 1. OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md
**Comprehensive technical deep-dive** (2500+ words)

Contents:
- The on_new_config function (heart of the system)
- How cmd configuration works
- All available RoslynExtensionsOptions settings
- Mason-lspconfig handler interaction
- Known issues and gotchas
- Step-by-step configuration guide
- Debugging commands and techniques

**Best for**: Understanding the entire system and how pieces fit together

### 2. OMNISHARP_IMPLEMENTATION_GUIDE.md
**Practical copy-paste implementation guide** (1500+ words)

Contents:
- 3-step quick start
- Understanding settings flow
- Essential settings explained
- Complete working template
- Troubleshooting quick reference
- Verification checklist
- Settings reference table
- JSON file alternative

**Best for**: Implementing the configuration and troubleshooting

### 3. OMNISHARP_GITHUB_ISSUES_REFERENCE.md
**Catalog of known issues and solutions** (2000+ words)

Contents:
- Critical issues (setup called twice, Mason setup twice, etc.)
- Configuration issues (wrong cmd format, case sensitivity)
- Roslyn-specific issues
- LSP configuration issues
- Debugging techniques
- Stack Overflow solutions
- Version-specific issues
- Common workarounds
- Quick reference table

**Best for**: Finding solutions to specific problems and understanding what can go wrong

### 4. RESEARCH_SUMMARY_OMNISHARP_ROSLYN.md
**This file** - Overview and quick navigation

---

## Key Findings Summary

### Finding 1: on_new_config Is Automatic and Critical

The `on_new_config` function in nvim-lspconfig/configs/omnisharp.lua is the KEY to understanding OmniSharp configuration:

```
Your Lua settings table
    ↓
on_new_config() runs automatically
    ↓
Settings flattened to command-line arguments
    ↓
OmniSharp executable receives all arguments
```

**You don't call on_new_config** - lspconfig invokes it when you call `setup()`.

### Finding 2: Only Call setup() Once

This is THE most critical finding:

- `lspconfig.omnisharp.setup()` can only be called ONCE per session
- Second calls are silently ignored
- If called twice, first call wins
- Handlers handle this for you - don't call setup() again after handlers

### Finding 3: Settings Flow

Your configuration → settings table → on_new_config flattens → command-line args

Example:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  }
}
```

Becomes:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

Appended to the cmd array and passed to OmniSharp.

### Finding 4: cmd Must Be Correct Format

**Correct**:
```lua
cmd = {
  'dotnet',
  '/path/to/OmniSharp.dll',
  '-s', '/path/to/solution',
}
```

**Wrong**:
- Just binary name without 'dotnet'
- Wrapper script directly
- Wrong path
- Missing -s flag (slower)

### Finding 5: Case Sensitivity Matters

**In Lua settings**: PascalCase
```lua
RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
```

**In JSON files**: camelCase
```json
{ "RoslynExtensionsOptions": { "enableAnalyzersSupport": true } }
```

### Finding 6: .editorconfig Requires StyleCop Package

For Roslyn analyzers to work:
1. Settings: `EnableAnalyzersSupport = true`
2. File: `.editorconfig` in solution root
3. Package: `StyleCop.Analyzers` in .csproj

Missing any of these means no warnings.

### Finding 7: Handler Does All the Work

```lua
handlers = {
  function(server_name)
    local server = servers[server_name] or {}
    require('lspconfig')[server_name].setup(server)  -- One call!
  end,
}
```

The handler:
1. Gets your config from `servers` table
2. Calls setup() once
3. on_new_config runs and flattens settings
4. Everything works

No need for explicit setup after handlers.

### Finding 8: Verify with ps aux

The most reliable verification:
```bash
ps aux | grep omnisharp
```

Should show:
- dotnet
- /path/to/OmniSharp.dll
- -s /path/to/solution
- RoslynExtensionsOptions:EnableAnalyzersSupport=true
- Your other settings as arguments

If you see this, configuration is correct.

---

## Critical Configuration Pattern

This pattern WORKS:

```lua
-- 1. Define servers configuration
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', '/path/to/solution',
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

-- 2. Set up handlers (no explicit omnisharp.setup() call!)
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

That's it. Everything else is handled automatically.

---

## Most Common Mistakes (And Why They Break)

| Mistake | Why It Breaks | Fix |
|---------|---------------|-----|
| Calling setup() twice | Second call ignored | One setup() only, in handler |
| Setup in wrong place | Settings not used | Put config in servers table |
| Wrong case in Lua | Settings not recognized | Use PascalCase |
| Missing 'dotnet' in cmd | OmniSharp won't start | Start with 'dotnet' in cmd array |
| Settings not nested in 'settings =' | Settings not passed to OmniSharp | Put settings in settings = { ... } table |
| Mason setup twice | Config conflicts | Setup only in dependency block |
| Checking :LspInfo for settings | Shows {} because settings flattened | Check ps aux instead |
| No .editorconfig file | Analyzers have nothing to check | Create .editorconfig in root |
| StyleCop not in .csproj | Analyzers not available | Add StyleCop.Analyzers package |

---

## How to Verify It's Working

**Step 1**: Check the process
```bash
ps aux | grep omnisharp | grep -v grep
```

Must include:
- ✓ `dotnet`
- ✓ `/OmniSharp.dll`
- ✓ `-s /path/to/solution`
- ✓ `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

**Step 2**: Check in Neovim
```vim
:LspInfo
```

Must show:
- ✓ OmniSharp attached
- ✓ Status: initialized

**Step 3**: Check for warnings
```vim
:lua vim.diagnostic.open_float()
```

Should show StyleCop warnings if .editorconfig defines rules.

---

## The on_new_config Algorithm (Pseudocode)

This is what happens automatically:

```pseudocode
when setup(config) is called:

  1. Copy cmd array to avoid modifying original
  2. Append hard-coded args:
     - '-z'
     - '--hostPID' <current_pid>
     - 'DotNet:enablePackageRestore=false'
     - '--encoding' 'utf-8'
     - '--languageserver'

  3. Flatten settings recursively:
     for each key, value in settings:
       if value is a table:
         recursively flatten and prepend key:
       else:
         append key=value

  4. Disable multi-workspace:
     set capabilities.workspace.workspaceFolders = false

  5. Launch OmniSharp with final cmd array
```

Result: All settings become command-line arguments automatically.

---

## Required OmniSharp Configuration for Roslyn Analyzers

Minimum to enable StyleCop warnings:

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- ESSENTIAL
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,  -- Recommended
  },
}
```

Recommended full config:

```lua
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
  Sdk = {
    IncludePrereleases = true,
  },
}
```

---

## Troubleshooting Decision Tree

```
Are analyzers showing up?
├─ YES → Configuration working! Debug specific analyzer rules
└─ NO →
   ├─ Does process show RoslynExtensionsOptions:EnableAnalyzersSupport=true?
   │  ├─ NO →
   │  │  ├─ Check: Is cmd correct? (must have dotnet, dll path, -s solution)
   │  │  ├─ Check: Are settings in servers.omnisharp.settings?
   │  │  ├─ Check: Is setup() called only once?
   │  │  └─ FIX: Correct cmd and settings location
   │  └─ YES →
   │     ├─ Check: Is .editorconfig in solution root?
   │     ├─ Check: Is StyleCop.Analyzers in .csproj?
   │     └─ FIX: Create .editorconfig and add package
   └─ Is OmniSharp attached at all?
      ├─ NO →
      │  ├─ Check: Is OmniSharp installed? (:Mason)
      │  ├─ Check: Is dotnet available? (dotnet --version)
      │  └─ FIX: Install OmniSharp and/or dotnet
      └─ YES → See above
```

---

## Research Sources

### Official Documentation
- **OmniSharp Configuration Options**: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- **nvim-lspconfig README**: https://github.com/neovim/nvim-lspconfig
- **Mason-lspconfig**: https://github.com/williamboman/mason-lspconfig.nvim

### GitHub Issues Researched
1. **kickstart.nvim #1297** - Mason setup called twice
2. **omnisharp-roslyn #909** - Multi-workspace handling
3. **nvim-lspconfig #4145** - EditorConfig not respected
4. **omnisharp-roslyn #2667** - Roslynator analyzer configuration
5. **omnisharp-roslyn #2573** - Import completion issues
6. **omnisharp-roslyn #2550** - InlayHints not working

### Stack Overflow & Articles
- Stack Exchange: "How to use OmniSharp C# LSP with Mason in nvim properly?"
- "Enabling Roslyn EditorConfig Support in Neovim" by aaronbos.dev
- Multiple Medium articles on Mason and LSP configuration

### Source Code Reviewed
- `nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua` (complete)
- `mason-lspconfig` handler patterns
- OmniSharp command-line argument parsing

---

## Quick Reference - Essential Settings

| Setting | Location | Type | Required? | Effect |
|---------|----------|------|-----------|--------|
| EnableAnalyzersSupport | RoslynExtensionsOptions | bool | YES | Enable Roslyn analyzers |
| EnableImportCompletion | RoslynExtensionsOptions | bool | NO | Suggest unimported types |
| AnalyzeOpenDocumentsOnly | RoslynExtensionsOptions | bool | NO | Faster but less complete |
| EnableEditorConfigSupport | FormattingOptions | bool | NO | Read .editorconfig |
| OrganizeImports | FormattingOptions | bool | NO | Sort using statements |
| LoadProjectsOnDemand | MsBuild | bool | NO | Load only open projects |
| IncludePrereleases | Sdk | bool | NO | Use preview SDK |

---

## Files to Check/Modify

1. **Your init.lua** (~680 lines)
   - Update `servers.omnisharp` configuration
   - Verify handler setup

2. **.editorconfig** (in your solution root)
   - Create if missing
   - Define StyleCop rules

3. **Your .csproj file**
   - Ensure StyleCop.Analyzers package is referenced
   - Rebuild if added

4. **omnisharp.json** (optional, ~/.omnisharp/)
   - Alternative to Lua configuration
   - Use camelCase instead of PascalCase

---

## Testing Checklist

After implementing configuration:

- [ ] `ps aux | grep omnisharp` shows correct arguments
- [ ] `:LspInfo` shows omnisharp as initialized
- [ ] Open a C# file with style violations
- [ ] Warnings appear in the diagnostics
- [ ] Hover over warning with `K` shows details
- [ ] `<leader>ca` shows available code actions
- [ ] Format on save works (`:w` reformats code)
- [ ] Go to definition works (`gd`)
- [ ] Find references works (`grr`)

---

## Performance Considerations

- **AnalyzeOpenDocumentsOnly = true**: Faster analysis, misses violations in unopened files
- **AnalyzeOpenDocumentsOnly = false**: Complete analysis, uses more CPU/memory
- **EnableImportCompletion = true**: First completion slower, subsequent faster
- **LoadProjectsOnDemand = true**: Faster startup for large solutions

Choose based on your needs.

---

## Summary

OmniSharp configuration in nvim-lspconfig is a three-part system:

1. **cmd**: How to start OmniSharp (must be: `{ 'dotnet', '/path/to/dll', '-s', '/path/to/solution' }`)
2. **settings**: What settings to pass (RoslynExtensionsOptions, FormattingOptions, etc.)
3. **on_new_config**: Automatically flattens settings to command-line arguments

The handler ensures `setup()` is called exactly once with your full configuration.

Verification: `ps aux | grep omnisharp` shows all settings as arguments.

**Most common mistake**: Calling setup() twice (only first call takes effect).

**Solution**: Put everything in the `servers` table and let the handler do the setup.

---

## Next Steps

1. **Read** OMNISHARP_IMPLEMENTATION_GUIDE.md for practical implementation
2. **Reference** OMNISHARP_GITHUB_ISSUES_REFERENCE.md when troubleshooting
3. **Study** OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md for deep understanding
4. **Implement** the 3-step quick start
5. **Verify** with the provided debugging commands
6. **Test** with the verification checklist

All configuration examples are ready to copy-paste and adapt to your setup.

