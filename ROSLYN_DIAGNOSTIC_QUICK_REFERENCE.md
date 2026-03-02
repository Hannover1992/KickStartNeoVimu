# Roslyn Diagnostic System - Quick Reference

**Fast lookup guide for diagnostic concepts, configuration, and troubleshooting**

---

## Diagnostic Severity Levels

```
Error    → Red squiggle,   build fails
Warning  → Yellow squiggle, build succeeds
Info     → Blue squiggle,   hidden by default
Hidden   → No display,      configuration only
```

---

## Diagnostic ID Prefixes

```
CS/VB    Compiler errors          (CS0001, VB1234)
CA       Code quality rules       (CA1822, CA2000)
IDE      Code style rules         (IDE0001, IDE0021)
SA       StyleCop violations      (SA1116, SA1400)
SP       Suppressor info          (SP0001)
```

---

## Configuration Quick Syntax

### Set Specific Rule
```editorconfig
dotnet_diagnostic.CA1822.severity = error
dotnet_diagnostic.SA1116.severity = warning
```

### Set Entire Category
```editorconfig
dotnet_analyzer_diagnostic.category-Performance.severity = warning
dotnet_analyzer_diagnostic.category-Security.severity = error
dotnet_analyzer_diagnostic.category-Style.severity = none
```

### Categories Available
```
Design, Documentation, Globalization, Interoperability, Maintainability,
Naming, Performance, Reliability, Security, SingleFile, Style, Usage
```

---

## Configuration File Priority

1. Command-line (`dotnet build -p:...`)
2. EditorConfig (closer to file = higher priority)
3. Global analyzer config (.globalconfig)
4. MSBuild properties (.csproj)
5. DiagnosticDescriptor defaults (in code)

---

## File Locations

```
Project .editorconfig     → File-level, folder-level configuration
Solution .editorconfig    → Project-level defaults
.globalconfig            → Global project settings (is_global = true)
.ruleset                 → Legacy configuration (deprecated)
.csproj                  → MSBuild properties
code files              → Pragma directives (#pragma warning disable)
```

---

## Quick Suppression Methods

### In Code (Line-level)
```csharp
#pragma warning disable CA1822
public void MyMethod() { }
#pragma warning restore CA1822
```

### In Code (Method-level)
```csharp
[SuppressMessage("Performance", "CA1822")]
public void MyMethod() { }
```

### In Configuration (Project-wide)
```editorconfig
dotnet_diagnostic.CA1822.severity = none
```

---

## Compiler vs Analyzer

| Aspect | Compiler | Analyzer |
|--------|----------|----------|
| ID Prefix | CS/VB | CA/IDE/SA |
| Always Enabled | Yes | No |
| Suppressible | Limited | Full |
| Speed | Fast | Variable |
| Examples | Syntax errors, type errors | Style, performance, design |

---

## OmniSharp + Neovim Configuration

### Enable Analyzers in init.lua
```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,    -- Enable analyzers
      AnalyzeOpenDocumentsOnly = false, -- Analyze entire solution
      EnableImportCompletion = true,    -- Import suggestions
    },
  },
}
```

### Add to Project .editorconfig
```editorconfig
[*.cs]
# StyleCop violations as errors
dotnet_diagnostic.SA1116.severity = error
dotnet_diagnostic.SA1202.severity = error

# Performance warnings
dotnet_analyzer_diagnostic.category-Performance.severity = warning

# Security errors
dotnet_analyzer_diagnostic.category-Security.severity = error
```

### Verify in Neovim
```vim
:LspInfo          " Check RoslynExtensionsOptions in config
:LspRestart       " Restart if configuration changed
```

### Verify in Terminal
```bash
# Check OmniSharp is receiving all settings
ps aux | grep omnisharp

# Should show:
# RoslynExtensionsOptions:EnableAnalyzersSupport=true
# RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
# (and all other settings as CLI arguments)
```

---

## Common Diagnostic Rules

### StyleCop (SA codes)
```
SA1116  - Parameters not on same line
SA1117  - Parameters not aligned
SA1201  - Elements ordered incorrectly
SA1202  - Elements must be ordered by access level
SA1400  - Missing XML comment
SA1600  - Missing XML comment on public type
```

### Code Quality (CA codes)
```
CA1001  - Types that own disposable fields should be disposable
CA1822  - Mark members as static
CA1826  - Use property instead of Linq Enumerable
CA2000  - Dispose objects before losing scope
CA2213  - Disposable fields should be disposed
```

### Code Style (IDE codes)
```
IDE0001 - Simplify names
IDE0007 - Use 'var' instead of explicit type
IDE0021 - Use expression body for methods
IDE0028 - Use collection initializer
IDE0300 - Use collection expression
```

---

## Troubleshooting

### Diagnostics Not Showing in Neovim

**Check 1**: Analyzer support enabled
```vim
" Check init.lua configuration
:lua print(vim.inspect(require('lspconfig').omnisharp))
" Should show: RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
```

**Check 2**: Clear cache and restart
```bash
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp
# Restart Neovim
```

**Check 3**: .editorconfig exists and has rules
```bash
ls -la /path/to/project/.editorconfig
# Check content has dotnet_diagnostic rules
```

**Check 4**: Verify rule is not disabled
```bash
grep -r "severity = none" .editorconfig
# If found, either remove or set to warning/error
```

### Rule Severity Not Applying

**Check 1**: .editorconfig is in correct location
```bash
# File should be in project root or parent directories
cat .editorconfig | grep "CA1822\|SA1116"
```

**Check 2**: Syntax is correct
```editorconfig
# Correct syntax
dotnet_diagnostic.CA1822.severity = warning

# Common mistakes
dotnet_diagnostic.CA1822.severity = Warning      # ❌ (capitalized)
dotnet_diagnostic.CA1822.severity = warn         # ❌ (short form)
dotnet_diagnostic.CA1822.severity = 2            # ❌ (numeric)
```

**Check 3**: No conflicting configuration
```bash
# Check for competing settings in .globalconfig, .csproj, or ruleset
grep "CA1822" .globalconfig 2>/dev/null
grep "CA1822" .csproj 2>/dev/null
grep "CA1822" **/*.ruleset 2>/dev/null
```

### Performance Issue (Compilation Slow)

**Disable specific slow analyzers**:
```editorconfig
# Disable entire category temporarily
dotnet_analyzer_diagnostic.category-Performance.severity = none

# Or disable specific rules
dotnet_diagnostic.CA1806.severity = none
```

**Check analyzer performance**:
```bash
# See which analyzers are slow
msbuild /v:d /p:reportanalyzer=true Project.csproj
```

---

## Diagnostic Descriptor Template

For custom analyzer development:

```csharp
private static readonly DiagnosticDescriptor Rule = new(
    id: "CUSTOM001",
    title: "Rule Title",
    messageFormat: "Message with placeholder '{0}'",
    category: "Usage",
    defaultSeverity: DiagnosticSeverity.Warning,
    isEnabledByDefault: true,
    description: "Detailed explanation of the rule");
```

**Category Options**:
- Design, Documentation, Globalization, Interoperability, Maintainability
- Naming, Performance, Reliability, Security, SingleFile, Style, Usage

**Severity Options**:
- DiagnosticSeverity.Error
- DiagnosticSeverity.Warning
- DiagnosticSeverity.Info
- DiagnosticSeverity.Hidden

---

## LSP Diagnostic Message Flow

```
DiagnosticAnalyzer
    ↓ Reports violation via context.ReportDiagnostic()
Diagnostic Object
    ↓ Contains: ID, Severity, Location, Message
Configuration Applied
    ↓ .editorconfig/ruleset overrides severity
OmniSharp LSP Server
    ↓ Converts to LSP DiagnosticMessage
Client (Neovim)
    ↓ Displays as: squiggles, error list, status line
User Sees: Yellow/red underline in editor
```

---

## Batch Operations

### Apply Rule to All Files
```editorconfig
# Automatically applied when this .editorconfig file exists
[*.cs]
dotnet_diagnostic.CA1822.severity = error
```

### Global Project Setting
```ini
# .globalconfig file (is_global = true required)
is_global = true
global_level = 1

dotnet_analyzer_diagnostic.category-Performance.severity = warning
```

### MSBuild Property (Legacy)
```xml
<!-- Project.csproj -->
<PropertyGroup>
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  <AnalysisMode>All</AnalysisMode>
  <AnalysisLevel>latest</AnalysisLevel>
</PropertyGroup>
```

---

## Real-World Example: StyleCop Setup

**Goal**: Enforce StyleCop formatting rules in build, warn on code quality issues

**.editorconfig**:
```editorconfig
[*.cs]

# Strict formatting rules (errors in build)
dotnet_diagnostic.SA1116.severity = error      # Parameters aligned
dotnet_diagnostic.SA1117.severity = error      # Parameters same line
dotnet_diagnostic.SA1202.severity = error      # Ordering
dotnet_diagnostic.SA1600.severity = error      # Documentation

# Code quality warnings (visible, not errors)
dotnet_analyzer_diagnostic.category-Performance.severity = warning
dotnet_analyzer_diagnostic.category-Naming.severity = warning

# Disable style rules that conflict with your preferences
dotnet_diagnostic.IDE0005.severity = none      # Unused import
```

**MSBuild** (.csproj):
```xml
<PropertyGroup>
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  <AnalysisMode>Recommended</AnalysisMode>
</PropertyGroup>

<ItemGroup>
  <PackageReference Include="StyleCop.Analyzers" Version="1.2.0-beta.435" />
</ItemGroup>
```

**Result**:
- `dotnet build` fails if StyleCop (SA) rules violated
- Code quality (CA) violations show as warnings
- `:LspRestart` in Neovim shows diagnostics inline

---

## Additional Resources

- **Microsoft Learn**: https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/
- **Roslyn Repo**: https://github.com/dotnet/roslyn
- **StyleCop**: https://github.com/DotNetAnalyzers/StyleCopAnalyzers
- **OmniSharp**: http://www.omnisharp.net/

---

**Last Updated**: 2025-11-13
**Status**: Quick Reference Complete
