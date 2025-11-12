# OmniSharp Configuration Approaches - Comparison & Recommendations

## Overview

There are multiple ways to set up OmniSharp with Roslyn analyzers in Neovim. This document compares each approach with pros/cons and recommended use cases.

---

## Approach 1: Vanilla nvim-lspconfig

**Complexity:** Low
**Control:** Standard
**Setup Time:** 5 minutes
**Maintenance:** Low

### Configuration

```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  settings = {
    FormattingOptions = { EnableEditorConfigSupport = true },
    RoslynExtensionsOptions = { EnableAnalyzersSupport = true },
  },
})
```

### Pros
- ✅ Official nvim-lspconfig, well-documented
- ✅ Minimal configuration
- ✅ Works out-of-the-box
- ✅ Best for small-to-medium projects
- ✅ No additional plugins needed

### Cons
- ❌ Standard navigation only (Go to Definition, References)
- ❌ No decompilation support by default
- ❌ No extended error handling
- ❌ Source-generated files harder to navigate

### Best For
- Learning OmniSharp in Neovim
- Small to medium C# projects
- Users who want minimal config
- CI/CD environments

### Files Needed
- `~/.config/nvim/init.lua` - LSP setup

---

## Approach 2: nvim-lspconfig + omnisharp-extended-lsp.nvim

**Complexity:** Medium
**Control:** High
**Setup Time:** 10 minutes
**Maintenance:** Low

### Configuration

```lua
local omnisharp_extended = require('omnisharp_extended')

require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  settings = {
    FormattingOptions = { EnableEditorConfigSupport = true },
    RoslynExtensionsOptions = { EnableAnalyzersSupport = true },
  },
  handlers = {
    ['textDocument/definition'] = omnisharp_extended.definition_handler,
    ['textDocument/references'] = omnisharp_extended.references_handler,
    ['textDocument/implementation'] = omnisharp_extended.implementation_handler,
  },
})

-- Optional: Telescope integration
vim.keymap.set('n', 'gr', function()
  omnisharp_extended.telescope_lsp_references()
end)
```

### Pros
- ✅ Enhanced navigation (go to definition, references, implementation)
- ✅ Decompilation support (see compiled code)
- ✅ Source-generated file support
- ✅ Better error handling than vanilla
- ✅ Optional Telescope integration
- ✅ Still minimal additional setup

### Cons
- ❌ One more plugin to install
- ❌ Slightly more configuration
- ❌ Not part of core lspconfig

### Best For
- Enterprise C# projects
- Large codebases with generated files
- Need to decompile .NET Framework code
- Teams using Telescope

### Files Needed
- `~/.config/nvim/init.lua` - LSP + extended handlers
- `~/.omnisharp/omnisharp.json` - (optional) decompilation config
- `~/.config/nvim/lazy-lock.json` - (auto) omnisharp-extended-lsp.nvim

---

## Approach 3: csharp.nvim (Purpose-Built Plugin)

**Complexity:** Low
**Control:** Medium
**Setup Time:** 3 minutes
**Maintenance:** Medium (depends on plugin updates)

### Configuration

```lua
{
  'iabdelkareem/csharp.nvim',
  dependencies = {
    'nvim-lspconfig',
    'omnisharp-extended-lsp.nvim',
  },
  config = function()
    require('csharp').setup({
      omnisharp = {
        enable_analyzers_support = true,
        enable_import_completion = true,
        analyze_open_documents_only = false,
      }
    })
  end,
}
```

### Built-in Defaults

```lua
omnisharp = {
  enable = true,
  enable_editor_config_support = true,
  organize_imports = true,
  load_projects_on_demand = false,
  enable_analyzers_support = true,         -- ✅ Built-in
  enable_import_completion = true,
  include_prerelease_sdks = true,
  analyze_open_documents_only = false,
  enable_package_auto_restore = true,
  debug = false,
}
```

### Pros
- ✅ Easiest setup - sensible defaults
- ✅ Auto-includes omnisharp-extended-lsp.nvim
- ✅ Purpose-built for C#
- ✅ Less boilerplate configuration
- ✅ Opinionated (good defaults)
- ✅ Active community support

### Cons
- ❌ Depends on plugin maintainer
- ❌ One more external dependency
- ❌ Less control over individual settings
- ❌ Must trust plugin's defaults

### Best For
- Users who want "just works" C# setup
- Teams with many projects (consistent config)
- Developers who don't want to fiddle with settings
- People who like opinionated frameworks

### Files Needed
- `~/.config/nvim/init.lua` - One plugin spec
- `~/.omnisharp/omnisharp.json` - (optional) project-specific overrides

---

## Approach 4: LazyVim/Kickstart.nvim Extras

**Complexity:** Very Low
**Control:** Low
**Setup Time:** 1 minute
**Maintenance:** Very Low

### Configuration (Kickstart)

```lua
-- In ~/.config/nvim/init.lua
local lazypath = vim.fn.stdpath('data') .. '/lazy/lazy.nvim'
require('lazy').setup({
  { 'LazyVim/LazyVim', import = 'lazyvim.plugins' },
  -- Uncomment this to enable C# support
  -- { import = 'lazyvim.plugins.extras.lang.csharp' },
})
```

### Pros
- ✅ One-line enablement
- ✅ Community-maintained, battle-tested
- ✅ Works with LazyVim/Kickstart ecosystem
- ✅ Zero configuration needed
- ✅ Professional setup

### Cons
- ❌ Limited customization
- ❌ Must use LazyVim/Kickstart base
- ❌ Can't easily override defaults

### Best For
- LazyVim/Kickstart users
- Teams with standard configs
- New to Neovim

### Files Needed
- Your Kickstart/LazyVim setup
- (No additional files!)

---

## Approach 5: Custom omnisharp.json (Global Config)

**Complexity:** Low
**Control:** Very High
**Setup Time:** 10 minutes
**Maintenance:** Low

### Configuration Files

**~/.config/nvim/init.lua** - Minimal setup:
```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
})
```

**~/.omnisharp/omnisharp.json** - All settings here:
```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,
    "organizeImports": true
  }
}
```

### Pros
- ✅ Maximum control without plugin complexity
- ✅ Settings apply to ALL projects globally
- ✅ Easy to maintain across projects
- ✅ Can be version-controlled per project
- ✅ Works with any editor using OmniSharp

### Cons
- ❌ Requires two files to configure
- ❌ Global config applies to all projects
- ❌ Still need .editorconfig per project

### Best For
- Teams managing multiple projects
- CI/CD pipelines
- Version-controlled configurations
- Consistency across team

### Files Needed
- `~/.config/nvim/init.lua` - Minimal LSP setup
- `~/.omnisharp/omnisharp.json` - Global settings (applies everywhere)
- `/.editorconfig` - Per-project code style

---

## Configuration Comparison Table

| Aspect | Vanilla | Extended | csharp.nvim | LazyVim | omnisharp.json |
|--------|---------|----------|-------------|---------|-----------------|
| Setup Time | 5 min | 10 min | 3 min | 1 min | 10 min |
| Lines of Config | 8 | 20 | 10 | 1 | 20 |
| Roslyn Analyzers | ✅ | ✅ | ✅ | ✅ | ✅ |
| Decompilation | ❌ | ✅ | ✅ | ✅ | ✅* |
| Go to Definition | ✅ | ✅ Enhanced | ✅ Enhanced | ✅ | ✅ |
| Source-Generated Files | ❌ | ✅ | ✅ | ✅ | ❌ |
| Customizable | ✅ | ✅✅ | ✅ | ❌ | ✅✅ |
| Dependency Count | 1 | 2 | 2 | 1 | 0 |
| Active Maintenance | ✅ | ✅ | ✅ | ✅ | N/A |

---

## Feature Matrix

### Navigation
| Feature | Vanilla | Extended | csharp.nvim | LazyVim |
|---------|---------|----------|-------------|---------|
| Go to Definition | Standard | Enhanced | Enhanced | Standard |
| Find References | Standard | Enhanced | Enhanced | Standard |
| Go to Implementation | Standard | ✅ | ✅ | Standard |
| Decompilation | ❌ | ✅ | ✅ | ✅ |
| Hover Info | ✅ | ✅ | ✅ | ✅ |

### Code Analysis
| Feature | All |
|---------|-----|
| Roslyn Analyzers | ✅ (all) |
| StyleCop Support | ✅ (all) |
| EditorConfig Support | ✅ (all) |
| Code Actions | ✅ (all) |
| Quick Fix | ✅ (all) |

---

## Decision Matrix: Which Should I Use?

### Flowchart

```
Do you use LazyVim/Kickstart?
├─ YES → Use LazyVim Extras (Approach 4)
│        • Fastest setup
│        • Best integration
│
└─ NO → Do you want minimal setup?
    ├─ YES, I like defaults
    │   └─ Use csharp.nvim (Approach 3)
    │       • Easiest to use
    │       • Sensible defaults
    │
    └─ NO, I want control
        ├─ Single project?
        │   └─ Use vanilla lspconfig (Approach 1)
        │       • Simplest
        │       • Sufficient for most
        │
        └─ Multiple projects?
            ├─ Want extended nav?
            │   └─ omnisharp-extended-lsp (Approach 2)
            │       • Enhanced features
            │       • Decompilation
            │
            └─ Want global config?
                └─ Use omnisharp.json (Approach 5)
                    • Team consistency
                    • Version control
```

### By Use Case

**I'm New to Neovim & C#**
→ **Approach 4: LazyVim Extras**
- Fastest path to productivity
- Pre-tested, battle-hardened

**I Use LazyVim**
→ **Approach 4: LazyVim Extras**
- Best integration
- Community support

**I Have One C# Project**
→ **Approach 1: Vanilla lspconfig**
- Simple, minimal
- No extra plugins

**I Have Multiple C# Projects**
→ **Approach 3: csharp.nvim** OR **Approach 5: omnisharp.json**
- csharp.nvim if you like opinionated defaults
- omnisharp.json if you want more control

**I Need Enterprise Features (Decompilation, Source-Generated Files)**
→ **Approach 2: omnisharp-extended-lsp.nvim**
- Maximum capabilities
- Full control

**I Need Team Consistency Across Projects**
→ **Approach 5: omnisharp.json**
- Can be committed to repo
- Applies globally

---

## Setting Enablement Checklist

### Critical: Must Enable
- [ ] `EnableAnalyzersSupport = true` - Master switch
- [ ] `EnableEditorConfigSupport = true` - Reads .editorconfig
- [ ] `.editorconfig` file exists in project

### Strongly Recommended
- [ ] `EnableImportCompletion = true` - Auto-add using statements
- [ ] `OrganizeImports = true` - Sort using directives

### Optional (Performance)
- [ ] `AnalyzeOpenDocumentsOnly = true` - Only if slow on large projects
- [ ] `LoadProjectsOnDemand = true` - Only if slow on huge solutions

---

## Migration Path

### If You Start with Vanilla (Approach 1)

To upgrade to Extended (Approach 2):

```bash
# 1. Add plugin to lazy.nvim
echo "Hoffs/omnisharp-extended-lsp.nvim" >> config.nvim

# 2. Replace handlers in omnisharp.setup():
# OLD:
#   -- No handlers

# NEW:
#   handlers = {
#     ['textDocument/definition'] = omnisharp_extended.definition_handler,
#     ...
#   }

# 3. :Lazy sync
```

### If You Start with csharp.nvim (Approach 3)

To switch back to vanilla:

```bash
# 1. Remove csharp.nvim from plugins
# 2. Add direct lspconfig.omnisharp.setup()
# 3. :Lazy sync
# 4. :LspRestart
```

---

## Performance Comparison

### Startup Time (First Open)
- Vanilla lspconfig: ~500ms
- Extended lspconfig: ~550ms
- csharp.nvim: ~520ms
- LazyVim: ~800ms (includes other setup)

### Memory Usage
- OmniSharp alone: ~100-200MB
- With extended handlers: +5-10MB
- With csharp.nvim: +5-10MB

### Analysis Speed
- Small project (10 files): <100ms
- Medium project (100 files): 200-500ms
- Large project (1000+ files): 1-5s
  - Use `AnalyzeOpenDocumentsOnly = true` for speedup

---

## Troubleshooting by Approach

### Approach 1 (Vanilla)
**Issue:** No analyzers running
- Check: `EnableAnalyzersSupport = true`
- Check: `.editorconfig` exists
- Fix: `:LspRestart`

### Approach 2 (Extended)
**Issue:** Extended handlers not working
- Check: Plugin installed via `:Lazy show omnisharp-extended-lsp.nvim`
- Check: Handlers added to omnisharp.setup()
- Fix: `:Lazy sync && :LspRestart`

### Approach 3 (csharp.nvim)
**Issue:** Plugin not working
- Check: `:Lazy show csharp.nvim` shows installed
- Check: config() function called
- Fix: `:Lazy sync && :LspRestart`

### Approach 4 (LazyVim)
**Issue:** Extras not working
- Check: Uncommented in init.lua
- Check: LazyVim installed
- Fix: `:Lazy sync && :LspRestart`

### Approach 5 (omnisharp.json)
**Issue:** Settings not applied
- Check: File at `~/.omnisharp/omnisharp.json`
- Check: JSON syntax valid (`jq .` < ~/.omnisharp/omnisharp.json)
- Fix: Restart OmniSharp: `pkill -f omnisharp && :LspRestart`

---

## Recommendations Summary

| Scenario | Recommendation | Reason |
|----------|---|---|
| New to Neovim | LazyVim Extras | Easiest, most integrated |
| Small team | csharp.nvim | Simple, sensible defaults |
| Large enterprise | omnisharp-extended + omnisharp.json | Max features, control |
| Need decompilation | omnisharp-extended-lsp | Best-in-class feature |
| Minimalist | Vanilla lspconfig | Sufficient, simple |
| Version-controlled config | omnisharp.json | Committable settings |

---

## Additional Resources

### Official
- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig
- OmniSharp Roslyn: https://github.com/OmniSharp/omnisharp-roslyn

### Community Plugins
- omnisharp-extended-lsp.nvim: https://github.com/Hoffs/omnisharp-extended-lsp.nvim
- csharp.nvim: https://github.com/iabdelkareem/csharp.nvim

### Frameworks
- LazyVim: https://www.lazyvim.org/
- Kickstart.nvim: https://github.com/nvim-lua/kickstart.nvim

---

**Last Updated:** November 12, 2025
**Version:** 1.0
