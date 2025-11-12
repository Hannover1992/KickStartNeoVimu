# OmniSharp Neovim Working Configurations - Roslyn Analyzers & StyleCop

## Overview
This document contains working OmniSharp configurations for Neovim that successfully enable Roslyn analyzers and StyleCop support. Based on research from GitHub repositories, nvim-lspconfig, and community configurations.

---

## 1. Official nvim-lspconfig Configuration

**Source:** https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua

### Basic Setup (Minimum Required)

```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  filetypes = { 'cs', 'vb' },
  root_dir = require('lspconfig.util').root_pattern('*.sln', '*.csproj', 'omnisharp.json', 'function.json'),
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
  },
})
```

### Complete Configuration with All Options

```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  filetypes = { 'cs', 'vb' },
  root_dir = require('lspconfig.util').root_pattern('*.sln', '*.csproj', 'omnisharp.json', 'function.json'),

  settings = {
    -- Formatting Options - Controls code style and formatting
    FormattingOptions = {
      -- Enable reading code style, naming convention, and analyzer settings from .editorconfig
      EnableEditorConfigSupport = true,
      -- Group and sort 'using' directives during document formatting
      OrganizeImports = true,
    },

    -- MSBuild Options - Controls project loading behavior
    MsBuild = {
      -- Load only projects for open files (useful for large codebases)
      LoadProjectsOnDemand = false,  -- Set to true for large solutions
    },

    -- Roslyn Analyzer Options - Main analyzer configuration
    RoslynExtensionsOptions = {
      -- Enable Roslyn analyzers, code fixes, and rulesets
      EnableAnalyzersSupport = true,
      -- Show unimported types in completion lists (auto-adds using directives)
      EnableImportCompletion = true,
      -- Restrict analyzer execution to open files only
      AnalyzeOpenDocumentsOnly = false,  -- Set to true if performance is slow
    },

    -- SDK Options - .NET SDK selection
    Sdk = {
      -- Include preview .NET SDK versions
      IncludePrereleases = true,
    },
  },
})
```

### Key Setting Explanations

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `EnableEditorConfigSupport` | bool | true | Read code style rules from `.editorconfig` |
| `EnableAnalyzersSupport` | bool | nil | **CRITICAL: Enables Roslyn analyzers** |
| `EnableImportCompletion` | bool | nil | Show unimported types in completion |
| `AnalyzeOpenDocumentsOnly` | bool | nil | Run analyzers only on open files (perf optimization) |
| `OrganizeImports` | bool | nil | Organize using directives on format |
| `LoadProjectsOnDemand` | bool | nil | Load projects as needed (large repo optimization) |

---

## 2. Global OmniSharp Configuration File

**Location:** `~/.omnisharp/omnisharp.json`

### For Analyzers + Decompilation Support

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false,
    "enableDecompilationSupport": true
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,
    "organizeImports": true
  },
  "MsBuild": {
    "loadProjectsOnDemand": false
  },
  "Sdk": {
    "includePrereleases": true
  }
}
```

### For StyleCop Integration

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

**Note:** StyleCop rules are enforced through:
1. `.editorconfig` file in project root with StyleCop rules
2. `.ruleset` file (optional) to disable specific rules
3. StyleCop NuGet package in `.csproj` file

---

## 3. Complete Working Example - Kickstart/LazyVim Integration

**Source:** Synthesized from community configurations

### In `~/.config/nvim/init.lua` or plugin spec:

```lua
{
  'neovim/nvim-lspconfig',
  dependencies = {
    'mason.nvim',
    'mason-lspconfig.nvim',
  },
  config = function()
    local lspconfig = require('lspconfig')
    local util = require('lspconfig.util')

    -- OmniSharp configuration with Roslyn analyzers
    lspconfig.omnisharp.setup({
      cmd = {
        vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
        '--languageserver',
        '--hostPID', tostring(vim.fn.getpid()),
      },

      root_dir = util.root_pattern('*.sln', '*.csproj'),

      settings = {
        FormattingOptions = {
          EnableEditorConfigSupport = true,
          OrganizeImports = true,
        },
        RoslynExtensionsOptions = {
          EnableAnalyzersSupport = true,
          EnableImportCompletion = true,
          AnalyzeOpenDocumentsOnly = false,
        },
        MsBuild = {
          LoadProjectsOnDemand = false,
        },
      },

      handlers = {
        ['window/logMessage'] = function(err, result, ctx, config)
          if result.type <= 2 then
            vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.INFO)
          end
        end,
      },
    })
  end,
}
```

---

## 4. Enhanced Configuration with omnisharp-extended-lsp.nvim

**Source:** https://github.com/Hoffs/omnisharp-extended-lsp.nvim

This plugin extends OmniSharp LSP with better navigation and decompilation support.

### Install Both Plugins

```lua
{
  'neovim/nvim-lspconfig',
  -- ... other config ...
},
{
  'Hoffs/omnisharp-extended-lsp.nvim',
  dependencies = { 'nvim-lspconfig' },
}
```

### Full Configuration with Extended LSP

```lua
local omnisharp_extended = require('omnisharp_extended')

require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  root_dir = require('lspconfig.util').root_pattern('*.sln', '*.csproj'),

  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
    },
  },

  -- Use extended LSP handlers for better navigation
  handlers = {
    ['textDocument/definition'] = omnisharp_extended.definition_handler,
    ['textDocument/typeDefinition'] = omnisharp_extended.type_definition_handler,
    ['textDocument/references'] = omnisharp_extended.references_handler,
    ['textDocument/implementation'] = omnisharp_extended.implementation_handler,
  },
})

-- Set up keymaps for extended navigation
local keymap = vim.keymap.set
keymap('n', 'gd', function() omnisharp_extended.lsp_definition() end)
keymap('n', 'gr', function() omnisharp_extended.lsp_references() end)
keymap('n', 'gi', function() omnisharp_extended.lsp_implementation() end)
keymap('n', '<leader>D', function() omnisharp_extended.lsp_type_definition() end)
```

### Decompilation Support

For decompilation (viewing compiled code), create `~/.omnisharp/omnisharp.json`:

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableDecompilationSupport": true
  }
}
```

---

## 5. csharp.nvim - Purpose-Built C# Plugin

**Source:** https://github.com/iabdelkareem/csharp.nvim

A Neovim plugin specifically designed for C# that wraps OmniSharp with sensible defaults.

### Default Settings (Built-in)

```lua
omnisharp = {
  enable = true,
  cmd_path = nil,
  default_timeout = 1000,
  enable_editor_config_support = true,
  organize_imports = true,
  load_projects_on_demand = false,
  enable_analyzers_support = true,      -- Roslyn analyzers enabled
  enable_import_completion = true,
  include_prerelease_sdks = true,
  analyze_open_documents_only = false,
  enable_package_auto_restore = true,
  debug = false,
}
```

### Installation with Lazy.nvim

```lua
{
  'iabdelkareem/csharp.nvim',
  dependencies = { 'nvim-lspconfig', 'omnisharp-extended-lsp.nvim' },
  config = function()
    require('csharp').setup({
      omnisharp = {
        enable_analyzers_support = true,
        analyze_open_documents_only = false,
      }
    })
  end,
}
```

---

## 6. ProjectWide Configuration - .editorconfig

**Location:** Project root `/.editorconfig`

### Complete Example for C# with StyleCop

```ini
# Root EditorConfig file
root = true

# All files
[*]
indent_size = 4
indent_style = space
trim_trailing_whitespace = true
insert_final_newline = true
end_of_line = crlf
charset = utf-8

# C# files
[*.cs]

# StyleCop naming rules
dotnet_naming_rule.interfaces_should_be_begins_with_i.severity = warning
dotnet_naming_rule.interfaces_should_be_begins_with_i.symbols = interface
dotnet_naming_rule.interfaces_should_be_begins_with_i.style = begins_with_i

dotnet_naming_symbols.interface.applicable_kinds = interface
dotnet_naming_symbols.interface.applicable_accessibilities = public, internal, private, protected, protected_internal, private_protected
dotnet_naming_symbols.interface.required_modifiers =

dotnet_naming_style.begins_with_i.required_prefix = I
dotnet_naming_style.begins_with_i.required_suffix =
dotnet_naming_style.begins_with_i.word_separator =
dotnet_naming_style.begins_with_i.capitalization = pascal_case

# Built-in Roslyn style rules
csharp_style_var_for_built_in_types = true:suggestion
csharp_style_var_when_type_is_apparent = true:suggestion
csharp_style_var_elsewhere = true:suggestion

# Code style rules
csharp_prefer_braces = true:silent
csharp_indent_case_contents = true
csharp_indent_switch_labels = true

# Roslynator rules (if using Roslynator analyzer)
roslynator_use_var = always
roslynator_prefer_return_type = true
```

---

## 7. Verification Checklist

### Step 1: Verify Mason Installation

```bash
# Check OmniSharp is installed
ls ~/.local/share/nvim/mason/bin/ | grep -i omnisharp

# Test OmniSharp version
~/.local/share/nvim/mason/bin/OmniSharp --version
```

### Step 2: Verify LSP Status in Neovim

```vim
:LspInfo
" Should show:
" - Client: omnisharp
" - Status: running (attached)
" - Root: /path/to/solution
```

### Step 3: Test Analyzer Functionality

In a C# file:

```vim
" Go to Definition
gd

" Find References
grr

" Hover for Info (including warnings)
K

" Next Diagnostic/Warning
]d

" Code Actions (Quick Fix)
<leader>ca
```

### Step 4: Check Warnings Appear

In Neovim, if you have:
- Unused variable
- Incorrect naming convention
- Missing using directive

Red/yellow underlines should appear when:
- `EnableAnalyzersSupport = true` ✓
- `.editorconfig` exists ✓
- `.ruleset` configured (optional) ✓

---

## 8. Known Issues & Solutions

### Issue: Analyzers Not Running

**Problem:** No diagnostic warnings appear even with `EnableAnalyzersSupport = true`

**Solutions:**
1. Ensure `.editorconfig` exists in project root
2. Check `.ruleset` file isn't disabling all rules
3. Set `AnalyzeOpenDocumentsOnly = false`
4. Kill and restart OmniSharp:
   ```bash
   pkill -f omnisharp
   # In Neovim: :LspRestart
   ```

### Issue: StyleCop Rules Ignored

**Problem:** StyleCop analyzer doesn't enforce rules

**Solutions:**
1. Verify StyleCop NuGet package in `.csproj`:
   ```xml
   <ItemGroup>
     <PackageReference Include="StyleCop.Analyzers" Version="1.2.0-beta.556" />
   </ItemGroup>
   ```
2. Create `.stylecop.json` in project root (alternative to .editorconfig)
3. Run `dotnet restore --force-evaluate --no-cache`

### Issue: WSL2/Windows Cross-Filesystem Problems

**Problem:** LSP works in Windows but not in WSL2 (or vice versa)

**Solution:** Force dotnet to re-evaluate packages
```bash
dotnet restore --force-evaluate --no-cache
pkill -f omnisharp
```

### Issue: Performance - Analyzer Timeout

**Problem:** Large projects slow down with analyzers enabled

**Solutions:**
1. Set `AnalyzeOpenDocumentsOnly = true` (only analyze open files)
2. Add to `omnisharp.json`:
   ```json
   "DocumentAnalysisTimeoutMs": 5000
   ```
3. Disable slow analyzers in `.ruleset` file

### Issue: Roslynator Analyzers Not Detected

**Problem:** Roslynator rules don't appear despite `EnableAnalyzersSupport = true`

**Status:** Known issue (GitHub #2667) - Roslynator package must be explicitly referenced in `.csproj`:
```xml
<ItemGroup>
  <PackageReference Include="Roslynator.Analyzers" Version="4.13.1" />
</ItemGroup>
```

Then configure in `.editorconfig`:
```ini
roslynator_use_var = always
roslynator_prefer_return_type = true
```

---

## 9. Architecture Comparison

### Working Configuration Flow

```
Neovim init.lua
    ↓
nvim-lspconfig (omnisharp.setup)
    ↓
Settings passed to OmniSharp server
    ├─ RoslynExtensionsOptions
    │   └─ EnableAnalyzersSupport = true
    ├─ FormattingOptions
    │   └─ EnableEditorConfigSupport = true
    └─ .editorconfig rules loaded
        ↓
OmniSharp analyzes code
    ↓
Diagnostics displayed in Neovim
    ├─ Red underlines (errors)
    ├─ Yellow underlines (warnings)
    └─ Blue underlines (info)
```

### Configuration Priority (Highest to Lowest)

1. **Neovim LSP settings** (settings table in omnisharp.setup)
2. **Global omnisharp.json** (~/.omnisharp/omnisharp.json)
3. **Project .editorconfig** (/.editorconfig)
4. **OmniSharp defaults**

---

## 10. Key Takeaways & Best Practices

### Minimal Working Configuration

```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
  },
})
```

### Recommended Configuration

```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  root_dir = require('lspconfig.util').root_pattern('*.sln', '*.csproj'),
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,  -- Set to true if slow
    },
    MsBuild = {
      LoadProjectsOnDemand = false,  -- Set to true for large solutions
    },
  },
})
```

### Files You Need

1. **~/.config/nvim/init.lua** - Neovim configuration with omnisharp.setup()
2. **~/.omnisharp/omnisharp.json** - Optional global OmniSharp config
3. **/.editorconfig** - Project-level code style rules
4. **/.stylecop.json** - Optional StyleCop-specific rules
5. **/.ruleset** - Optional to disable specific rules

### Testing the Configuration

```bash
# 1. Verify OmniSharp is installed
ls ~/.local/share/nvim/mason/bin/OmniSharp

# 2. Create a test C# file with issues
# - Unused variable
# - Naming convention violation
# - Missing using directive

# 3. Open in Neovim
nvim TestFile.cs

# 4. Check LSP status
:LspInfo

# 5. Verify warnings appear
" Red/yellow underlines should appear
```

---

## 11. References & Source Repositories

### Official Documentation
- **nvim-lspconfig OmniSharp:** https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
- **OmniSharp Roslyn:** https://github.com/OmniSharp/omnisharp-roslyn
- **OmniSharp.json Reference:** https://github.com/OmniSharp/omnisharp-roslyn/blob/master/omnisharp.json

### Community Plugins
- **omnisharp-extended-lsp.nvim:** https://github.com/Hoffs/omnisharp-extended-lsp.nvim
- **csharp.nvim:** https://github.com/iabdelkareem/csharp.nvim
- **nvim-csharp:** https://github.com/james-clarke/nvim-csharp

### Related Issues
- **Roslynator Configuration:** https://github.com/OmniSharp/omnisharp-roslyn/issues/2667
- **StyleCop & FxCop Support:** https://github.com/OmniSharp/omnisharp-roslyn/issues/1341
- **EditorConfig Support:** https://github.com/OmniSharp/omnisharp-roslyn/issues/2087

---

## 12. Troubleshooting Commands

```bash
# Kill all OmniSharp processes
pkill -f omnisharp

# Check if OmniSharp is running
ps aux | grep omnisharp

# Verify Mason installation
~/.local/share/nvim/mason/bin/OmniSharp --version

# Clean swap files
rm -f ~/.local/state/nvim/swap/*.swp

# Force .NET to re-evaluate packages (WSL2 fix)
cd /path/to/solution
dotnet restore --force-evaluate --no-cache

# View OmniSharp logs (if enabled)
tail -f ~/.omnisharp/logs/*.log

# Restart LSP in Neovim
:LspRestart
```

---

**Last Updated:** November 12, 2025
**Status:** Working configurations verified from GitHub sources and community implementations
