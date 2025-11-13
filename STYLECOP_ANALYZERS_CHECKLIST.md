# StyleCop.Analyzers Integration Checklist for OmniSharp

## Overview

StyleCop.Analyzers is a Roslyn analyzer package that enforces coding standards and conventions in C# projects. To display StyleCop warnings in Neovim via OmniSharp LSP, multiple components must be configured correctly:

1. **StyleCop.Analyzers NuGet package** in .csproj files
2. **stylecop.json configuration file** for rule settings
3. **.editorconfig file** for rule severity levels
4. **OmniSharp LSP settings** in Neovim to enable analyzer support
5. **Project structure** properly configured

---

## CRITICAL REQUIREMENT #1: StyleCop.Analyzers Package in .csproj

### Is it required?
**YES - ABSOLUTELY REQUIRED**

StyleCop.Analyzers must be referenced in every .csproj file where you want warnings to appear.

### How to verify:

**File**: `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/VDEK.DCSP.WebApi.csproj`

```xml
<ItemGroup>
  <PackageReference Include="StyleCop.Analyzers" Version="1.1.118">
    <PrivateAssets>all</PrivateAssets>
    <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
  </PackageReference>
</ItemGroup>
```

### Status in DCSRE Project:
✅ **FOUND** - The WebApi project has StyleCop.Analyzers 1.1.118 properly referenced

### What each attribute does:

| Attribute | Value | Purpose |
|-----------|-------|---------|
| `PrivateAssets` | `all` | Prevents this package from being passed to dependent projects |
| `IncludeAssets` | `runtime; build; native; contentfiles; analyzers; buildtransitive` | Includes the analyzer in the build process (critical!) |

### If package is missing:

Add to every .csproj file that should have StyleCop warnings:

```xml
<ItemGroup>
  <PackageReference Include="StyleCop.Analyzers" Version="1.1.118">
    <PrivateAssets>all</PrivateAssets>
    <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
  </PackageReference>
</ItemGroup>
```

Then run:
```bash
dotnet restore
```

---

## CRITICAL REQUIREMENT #2: stylecop.json Configuration File

### Is it required?
**YES - REQUIRED for enabling analyzer rules**

Without stylecop.json, StyleCop warnings are disabled by default (treats all rules as "hidden").

### How to verify:

**File**: `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/stylecop.json`

```json
{
  "$schema": "https://raw.githubusercontent.com/DotNetAnalyzers/StyleCopAnalyzers/master/StyleCop.Analyzers/StyleCop.Analyzers/Settings/stylecop.schema.json",
  "settings": {
    "documentationRules": {
      "companyName": "ITSG",
      "documentationCulture": "de-DE"
    },
    "orderingRules": {
      "usingDirectivesPlacement": "outsideNamespace"
    }
  }
}
```

### Status in DCSRE Project:
✅ **FOUND** - Located at `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/`

### What stylecop.json controls:

This file configures StyleCop rule behavior:
- **documentationRules**: XML documentation requirements
- **orderingRules**: Using directives placement, member ordering
- **namingRules**: Naming conventions (PascalCase, camelCase, etc.)
- **indentationRules**: Indentation style

### Critical: Must be linked in .csproj

Each .csproj file must reference stylecop.json as an **AdditionalFile**:

```xml
<ItemGroup>
  <AdditionalFiles Include="..\stylecop.json" Link="stylecop.json" />
</ItemGroup>
```

### Status in DCSRE:
✅ **FOUND** - Example from VDEK.DCSP.WebApi.csproj:
```xml
<ItemGroup>
  <AdditionalFiles Include="..\stylecop.json" Link="stylecop.json" />
</ItemGroup>
```

### If stylecop.json is missing:

Create at solution root (`/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/stylecop.json`):

```json
{
  "$schema": "https://raw.githubusercontent.com/DotNetAnalyzers/StyleCopAnalyzers/master/StyleCop.Analyzers/StyleCop.Analyzers/Settings/stylecop.schema.json",
  "settings": {
    "documentationRules": {
      "companyName": "Your Company",
      "documentationCulture": "en-US"
    },
    "orderingRules": {
      "usingDirectivesPlacement": "outsideNamespace"
    }
  }
}
```

---

## CRITICAL REQUIREMENT #3: .editorconfig File

### Is it required?
**CONDITIONALLY REQUIRED** - Recommended for controlling rule severity levels

The .editorconfig file sets the severity (error/warning/suggestion/none) for individual StyleCop rules.

### How to verify:

**File**: `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/.editorconfig`

```editorconfig
[*.cs]
# StyleCop rule severity settings
dotnet_diagnostic.SA1009.severity = none
dotnet_diagnostic.SA1413.severity = none
dotnet_diagnostic.SA1309.severity = none
# ... more rules
```

### Status in DCSRE Project:
✅ **FOUND** - File exists with naming rules and some StyleCop diagnostics disabled

### What .editorconfig controls:

For each StyleCop rule (SA1000, SA1001, etc.), you can set:

```editorconfig
[*.cs]
# Enable rule as error
dotnet_diagnostic.SA1116.severity = error

# Enable rule as warning
dotnet_diagnostic.SA1117.severity = warning

# Enable rule as suggestion (blue squiggle)
dotnet_diagnostic.SA1118.severity = suggestion

# Disable rule
dotnet_diagnostic.SA1119.severity = none
```

### Common StyleCop Rules and their codes:

**Documentation Rules (SA1600-SA1699)**
- SA1600: Elements should be documented
- SA1601: Partial elements should be documented
- SA1602: Enumeration items should be documented

**Ordering Rules (SA1200-SA1299)**
- SA1208: System using directives before other using directives
- SA1209: Using alias directives should be placed after other using directives
- SA1210: Using directives should be ordered alphabetically

**Naming Rules (SA1300-SA1399)**
- SA1309: Field names should not begin with underscore
- SA1310: Field names should not contain underscore
- SA1311: Static field names should begin with uppercase letter

**Spacing Rules (SA1000-SA1099)**
- SA1005: Single line comments should begin with single space
- SA1009: Closing parenthesis should not be preceded by space
- SA1013: Closing brace should be preceded by space

**Maintainability Rules (SA1400-SA1499)**
- SA1413: Use trailing comma in multi-line initializers
- SA1414: Tuple type parameters should have consistent naming

### If .editorconfig is missing:

Create at solution root with minimal settings:

```editorconfig
root = true

[*.cs]
# Enable most StyleCop rules
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1117.severity = warning
dotnet_diagnostic.SA1118.severity = warning

# Disable specific rules if needed
dotnet_diagnostic.SA1309.severity = none
```

---

## CRITICAL REQUIREMENT #4: OmniSharp LSP Configuration in Neovim

### Is it required?
**YES - REQUIRED to display StyleCop warnings in editor**

Even if StyleCop.Analyzers is installed and configured, OmniSharp must be told to analyze the code and report diagnostics.

### Current Neovim Configuration:

The current `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua` is a **minimal Kickstart config** without LSP configuration.

### What needs to be configured:

OmniSharp must receive these settings via the LSP client:

```lua
local omnisharp_config = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
    '-loglevel', 'Information',
  },

  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,           -- CRITICAL: Enable Roslyn analyzers
      EnableImportCompletion = true,           -- Enable auto-import suggestions
      AnalyzeOpenDocumentsOnly = false,        -- Analyze ALL files, not just open ones
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,        -- Support .editorconfig files
      OrganizeImports = true,                  -- Auto-organize imports
    },
  },
}
```

### Key OmniSharp Settings Explained:

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `EnableAnalyzersSupport` | boolean | false | **MUST BE TRUE** - Enables Roslyn analyzer diagnostics (StyleCop, etc.) |
| `EnableImportCompletion` | boolean | false | Suggests namespace imports in autocomplete |
| `AnalyzeOpenDocumentsOnly` | boolean | true | If true, only analyzes currently open files (faster but misses errors in closed files) |
| `EnableEditorConfigSupport` | boolean | false | Respects .editorconfig rules |
| `OrganizeImports` | boolean | false | Auto-removes unused imports when formatting |

### CRITICAL: `EnableAnalyzersSupport = true`

**Without this setting, NO StyleCop warnings will appear** in the editor, even if the package is installed and configured correctly.

### Status in DCSRE:

**NOT YET CONFIGURED** in Neovim init.lua - The current configuration is a minimal Kickstart setup.

---

## CRITICAL REQUIREMENT #5: Proper .csproj Project Structure

### Is it required?
**YES - For OmniSharp to find and analyze the projects**

OmniSharp needs a valid solution file (.sln) or project file (.csproj) to load the projects.

### How to verify:

**Files to check**:
```bash
# Solution file
/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/*.sln

# Project files
/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/**/*.csproj
```

### Status in DCSRE:

✅ **FOUND** - Valid project structure with:
- Multiple .csproj files (22 projects found)
- Proper target framework (net8.0)
- StyleCop.Analyzers referenced in WebApi projects

### What OmniSharp needs:

1. A valid C# project structure
2. At least one .sln or .csproj file
3. All dependencies resolvable (NuGet packages available)
4. Valid .csproj syntax

If OmniSharp cannot load projects:
```bash
# Clear NuGet cache
rm -rf ~/.nuget/packages/stylecop.analyzers

# Restore solution
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet restore --force-evaluate --no-cache
```

---

## VERIFICATION CHECKLIST

### Quick Verification Steps:

```bash
# 1. Check StyleCop.Analyzers package is installed
grep -r "StyleCop.Analyzers" /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/*.csproj

# 2. Verify stylecop.json exists
test -f /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/stylecop.json && echo "✓ stylecop.json found"

# 3. Verify .editorconfig exists
test -f /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/.editorconfig && echo "✓ .editorconfig found"

# 4. Build the project to verify StyleCop warnings appear
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet build | grep "SA[0-9]"  # Should show StyleCop warnings like SA1116, SA1117

# 5. Check if OmniSharp is running
ps aux | grep omnisharp | grep -v grep
```

### Expected Output from `dotnet build`:

```
VDEK.DCSP.WebApi/Controllers/UserController.cs(56,56): warning SA1116: Split parameters should start on line after declaration [/mnt/c/.../VDEK.DCSP.WebApi.csproj]
VDEK.DCSP.WebApi/Controllers/UserController.cs(78,56): warning SA1117: Parameters should be on same line or separate lines [/mnt/c/.../VDEK.DCSP.WebApi.csproj]
```

---

## COMPLETE CHECKLIST FOR STYLECOP WARNINGS IN NEOVIM

### Requirement 1: StyleCop.Analyzers Package
- [ ] StyleCop.Analyzers 1.1.118 referenced in .csproj file
- [ ] `PrivateAssets` set to `all`
- [ ] `IncludeAssets` includes `analyzers`
- [ ] Run `dotnet restore` after adding

**Status**: ✅ COMPLETE in DCSRE

---

### Requirement 2: stylecop.json Configuration
- [ ] stylecop.json exists in project root
- [ ] Contains valid JSON schema reference
- [ ] Defines `documentationRules` (at minimum)
- [ ] Linked in .csproj as `<AdditionalFiles Include="stylecop.json" />`

**Status**: ✅ COMPLETE in DCSRE

---

### Requirement 3: .editorconfig Rule Severity
- [ ] .editorconfig file exists in project root
- [ ] Contains `[*.cs]` section
- [ ] Has `root = true` at top
- [ ] Defines severity for StyleCop rules (SA1116, SA1117, etc.)
  - Use `dotnet_diagnostic.SA1116.severity = warning` format

**Status**: ✅ COMPLETE in DCSRE

---

### Requirement 4: OmniSharp LSP Configuration
- [ ] Neovim has LSP client configured (nvim-lspconfig)
- [ ] OmniSharp server configured with:
  - [ ] `cmd` pointing to correct DLL path
  - [ ] `settings.RoslynExtensionsOptions.EnableAnalyzersSupport = true` ← **CRITICAL**
  - [ ] `settings.RoslynExtensionsOptions.AnalyzeOpenDocumentsOnly = false`
  - [ ] `settings.FormattingOptions.EnableEditorConfigSupport = true`
- [ ] OmniSharp restarted after config change

**Status**: ❌ NOT YET CONFIGURED in Neovim

---

### Requirement 5: Project Structure
- [ ] Valid .sln or .csproj files present
- [ ] All NuGet packages restorable
- [ ] No compilation errors preventing analysis
- [ ] Solution path correctly pointed to in OmniSharp cmd

**Status**: ✅ COMPLETE in DCSRE

---

### Requirement 6: Verification
- [ ] `dotnet build` shows StyleCop warnings (SA1116, SA1117, etc.)
- [ ] Neovim can open C# files from project
- [ ] `ps aux | grep omnisharp` shows running process
- [ ] `:LspInfo` in Neovim shows OmniSharp connected
- [ ] Diagnostics panel shows StyleCop warnings (SA codes)

**Status**: ⏳ PENDING - Requires Neovim LSP configuration

---

## TROUBLESHOOTING GUIDE

### Problem: No StyleCop warnings appear in editor

**Step 1: Verify build warnings**
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet build 2>&1 | grep "SA"
```
If no "SA" warnings appear, the project configuration is wrong (not the editor issue).

**Step 2: Verify OmniSharp is running**
```bash
ps aux | grep omnisharp | grep -v grep
```
If not running, check if Neovim LSP is configured and `:LspStart omnisharp` works.

**Step 3: Check EnableAnalyzersSupport setting**
```vim
:lua print(vim.inspect(vim.lsp.get_clients()[1].config.settings))
```
Should show: `RoslynExtensionsOptions = { EnableAnalyzersSupport = true }`

**Step 4: Verify solution path**
```bash
ps aux | grep omnisharp | grep -o "\-s [^ ]*"
```
Should show: `-s /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend`

**Step 5: Restart OmniSharp**
```bash
pkill -f omnisharp
# Then reopen C# file in Neovim or :LspRestart
```

### Problem: "StyleCop.Analyzers package not found"

```bash
# Clear cache and restore
rm -rf ~/.nuget/packages/stylecop.analyzers
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet restore --force-evaluate --no-cache
```

### Problem: stylecop.json ignored by OmniSharp

**Cause**: AdditionalFiles not linked in .csproj

**Fix**: Add to every .csproj file:
```xml
<ItemGroup>
  <AdditionalFiles Include="..\stylecop.json" Link="stylecop.json" />
</ItemGroup>
```

### Problem: Rules appear in build but not in editor

**Most likely cause**: `EnableAnalyzersSupport` not set to `true` in Neovim config

**Verify**:
```vim
:lua print(vim.lsp.get_clients()[1].config.settings.RoslynExtensionsOptions.EnableAnalyzersSupport)
```

Should print: `true`

If `false` or `nil`, OmniSharp analyzers are disabled and no warnings will appear.

---

## EXAMPLE: Full Working Configuration

### .csproj File (VDEK.DCSP.WebApi.csproj)

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <CodeAnalysisRuleSet>..\ITSGrules.ruleset</CodeAnalysisRuleSet>
  </PropertyGroup>

  <ItemGroup>
    <AdditionalFiles Include="..\stylecop.json" Link="stylecop.json" />
  </ItemGroup>

  <ItemGroup>
    <PackageReference Include="StyleCop.Analyzers" Version="1.1.118">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
    </PackageReference>
  </ItemGroup>
</Project>
```

### stylecop.json (Backend Root)

```json
{
  "$schema": "https://raw.githubusercontent.com/DotNetAnalyzers/StyleCopAnalyzers/master/StyleCop.Analyzers/StyleCop.Analyzers/Settings/stylecop.schema.json",
  "settings": {
    "documentationRules": {
      "companyName": "ITSG",
      "documentationCulture": "de-DE"
    },
    "orderingRules": {
      "usingDirectivesPlacement": "outsideNamespace"
    }
  }
}
```

### .editorconfig (Backend Root)

```editorconfig
root = true

[*.cs]
# StyleCop rule severity
dotnet_diagnostic.SA1116.severity = warning  # Split parameters
dotnet_diagnostic.SA1117.severity = warning  # Parameters on same line
dotnet_diagnostic.SA1309.severity = none     # Field names underscore

# Other rules...
```

### Neovim init.lua (LSP Configuration)

```lua
require('lspconfig').omnisharp.setup({
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,          -- ← CRITICAL
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
  },
  on_attach = function(client, bufnr)
    -- Your keybindings here
  end,
  capabilities = require('cmp_nvim_lsp').default_capabilities(),
})
```

---

## SUMMARY

### The 5 Essential Components:

1. **StyleCop.Analyzers NuGet Package** (in .csproj)
   - Required for any StyleCop warnings to exist
   - Must have `PrivateAssets=all` and `IncludeAssets` including `analyzers`

2. **stylecop.json Configuration File** (at solution root)
   - Enables/configures StyleCop rules
   - Must be referenced as `<AdditionalFiles>` in .csproj

3. **.editorconfig Rule Severity** (at solution root)
   - Controls whether rules show as error/warning/suggestion/none
   - OmniSharp respects these settings if `EnableEditorConfigSupport=true`

4. **OmniSharp LSP Configuration** (in Neovim init.lua)
   - Enables analyzer reporting: `EnableAnalyzersSupport=true`
   - Specifies solution path with `-s` flag
   - Disables `AnalyzeOpenDocumentsOnly` to analyze all files

5. **Valid Project Structure** (solution with .csproj files)
   - Must be restorable with `dotnet restore`
   - Must compile without major errors

### Current Status in DCSRE:

✅ Components 1-3, 5 are **COMPLETE**
❌ Component 4 needs **Neovim LSP configuration**

Once OmniSharp is configured in Neovim with `EnableAnalyzersSupport=true`, StyleCop warnings should appear immediately in the editor.

---

## NEXT STEPS

1. **Configure OmniSharp in Neovim** with `EnableAnalyzersSupport=true`
2. **Restart OmniSharp** after config change
3. **Open a C# file** from the Backend project
4. **Wait for OmniSharp to load** (check `:LspInfo`)
5. **Verify warnings appear** (should show SA1116, SA1117, etc.)
6. **Troubleshoot if needed** using the guide above

See `LSP_CONFIGURATION_EXAMPLES.lua` for detailed Neovim LSP configuration examples.
