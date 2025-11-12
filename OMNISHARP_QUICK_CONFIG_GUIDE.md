# OmniSharp Roslyn Analyzers - Quick Config Guide

## TL;DR - Copy-Paste Working Config

### For Kickstart.nvim / LazyVim Users

Add this to your `lspconfig` specification in `~/.config/nvim/init.lua`:

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
      EnableAnalyzersSupport = true,      -- This enables Roslyn analyzers
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,   -- false = all files, true = only open
    },
  },
})
```

### Create ~/.omnisharp/omnisharp.json

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

### Create /.editorconfig in Your Project

```ini
root = true

[*.cs]
# Enable var usage (Roslyn IDE0007)
csharp_style_var_for_built_in_types = true:suggestion
csharp_style_var_when_type_is_apparent = true:suggestion
csharp_style_var_elsewhere = true:suggestion

# StyleCop naming conventions
dotnet_naming_rule.interfaces_should_be_begins_with_i.severity = warning
dotnet_naming_rule.interfaces_should_be_begins_with_i.symbols = interface
dotnet_naming_rule.interfaces_should_be_begins_with_i.style = begins_with_i

dotnet_naming_symbols.interface.applicable_kinds = interface
dotnet_naming_symbols.interface.capitalization = pascal_case

dotnet_naming_style.begins_with_i.required_prefix = I
```

---

## Critical Settings Explained

### The Three Must-Have Settings

1. **`EnableAnalyzersSupport = true`**
   - Without this, NO analyzers run
   - This is the master switch

2. **`EnableEditorConfigSupport = true`**
   - Reads .editorconfig rules
   - Required for StyleCop/Roslyn rules

3. **`EnableImportCompletion = true`**
   - Shows unimported types in completions
   - Auto-adds using directives

### Performance Settings

| Setting | Value | When to Use |
|---------|-------|------------|
| `AnalyzeOpenDocumentsOnly` | false | Default - analyze all files |
| `AnalyzeOpenDocumentsOnly` | true | Large codebases (performance) |
| `LoadProjectsOnDemand` | false | Default - load all projects |
| `LoadProjectsOnDemand` | true | Huge solutions (slow startup) |

---

## Verification in 5 Steps

### 1. Check OmniSharp Installed
```bash
ls ~/.local/share/nvim/mason/bin/ | grep OmniSharp
# Should output: OmniSharp
```

### 2. Open Project in Neovim
```bash
nvim /path/to/your/Solution.sln
# or
nvim /path/to/any/File.cs
```

### 3. Check LSP Attached
```vim
:LspInfo
" Look for:
" Client: omnisharp
" Status: running (attached)
```

### 4. Create Test Issues
Open a C# file and add:
```csharp
// Unused variable (should warn)
var unusedVar = 42;

// Wrong naming (interface should start with I)
interface UserService { }

// Missing using directive
var json = JsonConvert.SerializeObject(obj);
```

### 5. Verify Warnings Appear
- Red underlines = errors
- Yellow underlines = warnings
- Blue underlines = info
- Run `:set signcolumn=yes` to see symbols in gutter

---

## The Settings Hierarchy (What Gets Applied)

```
1. Neovim LSP settings (highest priority)
   └─ settings table in omnisharp.setup()

2. ~/.omnisharp/omnisharp.json (global config)
   └─ applies to all projects

3. Project /.editorconfig (code style rules)
   └─ specific rules per file type

4. OmniSharp defaults (lowest priority)
   └─ built-in fallbacks
```

---

## Common Issues & Fixes

### No Warnings/Errors Showing

**Checklist:**
- [ ] `EnableAnalyzersSupport = true` in Neovim config
- [ ] `EnableEditorConfigSupport = true` in Neovim config
- [ ] `.editorconfig` exists in project root
- [ ] Ran `:LspRestart` after config change

**Fix:**
```bash
pkill -f omnisharp
# In Neovim: :LspRestart
```

### StyleCop Rules Ignored

**You need:**
1. StyleCop NuGet package in `.csproj`:
```xml
<PackageReference Include="StyleCop.Analyzers" Version="1.2.0-beta.556" />
```

2. `.editorconfig` with StyleCop rules

3. Run:
```bash
dotnet restore
```

### Roslyn IDE Rules Not Working

**Check:**
- `.editorconfig` has `[*.cs]` section
- Rule names are correct (csharp_style_var_*)
- Severity is set (suggestion/warning/error)

Example:
```ini
[*.cs]
csharp_style_var_for_built_in_types = true:suggestion
csharp_style_var_when_type_is_apparent = true:suggestion
```

### WSL2: LSP Works in Windows but Not WSL

**Fix:**
```bash
cd /path/to/project
dotnet restore --force-evaluate --no-cache
pkill -f omnisharp
# Then :LspRestart in Neovim
```

---

## Configuration Files Needed

### 1. ~/.config/nvim/init.lua (or plugin spec)
```
Purpose: Configure LSP connection to OmniSharp
Size: 20-30 lines
Contains: omnisharp.setup() with settings
Location: Your Neovim config directory
```

### 2. ~/.omnisharp/omnisharp.json
```
Purpose: Global OmniSharp settings
Size: 15-20 lines
Optional: But recommended
Location: ~/.omnisharp/omnisharp.json
```

### 3. /.editorconfig
```
Purpose: Code style rules for analyzers
Size: 30-100+ lines
Required: For rules to apply
Location: Project root
```

---

## Per-Setting Reference

### RoslynExtensionsOptions

```lua
RoslynExtensionsOptions = {
  -- Master switch for all analyzers
  EnableAnalyzersSupport = true,

  -- Show unimported types in completion + auto-add using
  EnableImportCompletion = true,

  -- Restrict analyzers to open files only (perf optimization)
  AnalyzeOpenDocumentsOnly = false,

  -- Enable decompilation (see compiled code)
  EnableDecompilationSupport = true,  -- optional
}
```

### FormattingOptions

```lua
FormattingOptions = {
  -- Read .editorconfig rules for code style
  EnableEditorConfigSupport = true,

  -- Auto-organize using directives
  OrganizeImports = true,
}
```

### MsBuild

```lua
MsBuild = {
  -- Load projects on-demand for large solutions
  LoadProjectsOnDemand = false,  -- true for huge repos
}
```

### Sdk

```lua
Sdk = {
  -- Include preview SDK versions
  IncludePrereleases = true,
}
```

---

## Recommended Values by Project Size

### Small Projects (< 10 files)
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  EnableImportCompletion = true,
  AnalyzeOpenDocumentsOnly = false,  -- Analyze everything
}
```

### Medium Projects (10-100 files)
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  EnableImportCompletion = true,
  AnalyzeOpenDocumentsOnly = false,  -- Still fast enough
}
```

### Large Projects (100+ files or slow)
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  EnableImportCompletion = true,
  AnalyzeOpenDocumentsOnly = true,   -- Only open files
}

MsBuild = {
  LoadProjectsOnDemand = true,        -- Only load when needed
}
```

---

## Testing Analyzers Work

### Step 1: Test Roslyn Built-in Rules

```csharp
// File: Test.cs
using System;

class Program
{
  void TestMethod()
  {
    // This should warn (var preference enabled)
    int x = 42;  // <- Yellow warning here

    // This should not warn
    var y = 42;  // <- No warning
  }
}
```

**Expected:** Yellow squiggle on `int x = 42;`

### Step 2: Test StyleCop Rules

```csharp
// File: StyleTest.cs

// Should warn: interface doesn't start with I
interface UserService { }  // <- Yellow warning
```

**Expected:** Yellow squiggle on `interface UserService`

### Step 3: Test Import Completion

```csharp
// File: ImportTest.cs

class Test
{
  void Method()
  {
    // Type JsonConvert without using statement
    JsonConvert.Serialize(obj);  // <- Red error

    // Hover: should offer auto-import
    // Run: <leader>ca (code action)
    // Select: Add using Newtonsoft.Json
  }
}
```

**Expected:** Error highlight, then auto-fix adds using statement

---

## Advanced: Global omnisharp.json Template

Create `~/.omnisharp/omnisharp.json`:

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

This applies to ALL projects using OmniSharp!

---

## Debugging: Check What's Happening

### 1. See Current Settings
```vim
:lua print(vim.inspect(require('lspconfig').omnisharp.settings))
```

### 2. Check OmniSharp Process
```bash
ps aux | grep -i omnisharp
# Should see: OmniSharp running with --languageserver flag
```

### 3. View OmniSharp Logs
```bash
# Logs location (if enabled)
~/.omnisharp/logs/
```

### 4. Test OmniSharp Directly
```bash
# Start OmniSharp manually
~/.local/share/nvim/mason/bin/OmniSharp \
  --languageserver \
  --hostPID $$ \
  --encoding utf-8

# Then open a .cs file in another terminal
# Should connect
```

---

## Summary: Four Files You Need

1. **~/.config/nvim/init.lua** - LSP setup
   - Contains: omnisharp.setup() with settings
   - Must have: EnableAnalyzersSupport = true

2. **~/.omnisharp/omnisharp.json** - Global config (optional but recommended)
   - Contains: Same settings as #1
   - Applies: To all projects

3. **/.editorconfig** - Code style rules
   - Contains: Roslyn and StyleCop rules
   - Location: Project root

4. **/.ruleset** - Disable specific rules (optional)
   - Contains: Disabled rules
   - Location: Project root

---

## One-Line Activation

If you only have Neovim configured:
- Analyzers WILL work with the minimal config above
- You do NOT need omnisharp.json
- You DO need .editorconfig with rules

---

**For complete configuration details, see:** `/OMNISHARP_ROSLYN_WORKING_CONFIGS.md`
