# Roslyn Diagnostic System - Comprehensive Research

**Document Date**: November 13, 2025
**Research Focus**: How Roslyn diagnostics work, flow through analyzers, and reach IDE/LSP clients
**Key Sources**: dotnet/roslyn, Microsoft Learn, OmniSharp documentation

---

## Table of Contents

1. [How Roslyn Diagnostics Work](#how-roslyn-diagnostics-work)
2. [Diagnostic Severity Levels](#diagnostic-severity-levels)
3. [Diagnostic Categories](#diagnostic-categories)
4. [Diagnostic Flow to LSP Clients](#diagnostic-flow-to-lsp-clients)
5. [Configuration Mechanisms](#configuration-mechanisms)
6. [Compiler vs Analyzer Diagnostics](#compiler-vs-analyzer-diagnostics)
7. [DiagnosticDescriptor and DiagnosticAnalyzer](#diagnosticdescriptor-and-diagnosticanalyzer)
8. [Diagnostic Suppressors](#diagnostic-suppressors)
9. [Real-World Examples](#real-world-examples)

---

## How Roslyn Diagnostics Work

### Core Architecture

Roslyn diagnostics represent code issues (errors, warnings, information) along with their locations in source code. The diagnostic system is built on the .NET Compiler Platform and provides:

- **Semantic Analysis**: Understanding code structure and meaning
- **Real-time Reporting**: Issues reported as code is written (in IDEs)
- **Configurable Severity**: Warnings can be treated as errors or hidden
- **Automated Fixes**: Code fixes bundled with diagnostics

### Diagnostic Lifecycle

```
1. Analyzer Registration (compilation/file/symbol/syntax node actions)
   ↓
2. Code Analysis (semantic/syntactic analysis)
   ↓
3. Diagnostic Detection (violation found)
   ↓
4. Diagnostic Creation (using DiagnosticDescriptor)
   ↓
5. Diagnostic Reporting (via context.ReportDiagnostic())
   ↓
6. Configuration Application (severity overrides)
   ↓
7. IDE/LSP Display (squiggles, error list, light bulb suggestions)
```

### Key Components

#### DiagnosticAnalyzer
- Abstract base class for custom analyzers
- Registers actions to analyze code (syntax trees, symbols, semantic models)
- Reports diagnostics when violations are found
- Does NOT share state between instances
- Can run concurrently when `EnableConcurrentExecution` is set

#### DiagnosticDescriptor
- Metadata template defining the diagnostic
- Contains: ID, Title, Message Format, Category, Description, Severity
- Acts as a blueprint for creating diagnostic instances
- Used for localization and configuration

#### Diagnostic (Result)
- Concrete instance of a reported issue
- Contains: ID, Severity, Location, Message, Properties
- Created by calling `Diagnostic.Create()` with a descriptor

### Action Execution Model

Roslyn ensures specific execution ordering for analyzer actions:

```
1. Compilation Start Actions → execute first
2. Symbol Start Actions → execute before symbol operations
3. [Other actions - any order]
4. Symbol End Actions → execute after symbol operations
5. Compilation End Actions → execute last
```

**Important Constraints:**
- No ordering guarantees except for start/end actions
- Framework may skip redundant invocations
- End actions NOT guaranteed for cancelled compilations
- Actions can be invoked concurrently (with explicit opt-in)

---

## Diagnostic Severity Levels

### DiagnosticSeverity Enum

Roslyn defines 4 severity levels (enum `DiagnosticSeverity`):

| Level | Enum Value | Meaning | IDE Behavior | Build Behavior |
|-------|-----------|---------|--------------|-----------------|
| **Error** | 0 | Critical issue, must fix | Red squiggle | Build fails (default) |
| **Warning** | 1 | Important issue, should fix | Yellow/green squiggle | Build succeeds (default) |
| **Info** | 2 | Informational (hidden by default) | Blue squiggle | Build succeeds |
| **Hidden** | 3 | Not shown (only in configuration) | No visual indicator | Silent |

### Warning Levels (WarningLevel)

Roslyn also supports numeric warning levels:

```csharp
DefaultWarningLevel = 4      // Standard warning priority
InfoAndHiddenWarningLevel = 1 // For info/hidden diagnostics
MaxWarningLevel = 9999        // Maximum priority value
```

### Default vs Effective Severity

- **DefaultSeverity**: Defined in DiagnosticDescriptor
- **EffectiveSeverity**: After configuration overrides applied
- **Overrides**: Configured via .editorconfig, rulesets, or MSBuild properties

### Configuration Examples

```editorconfig
# Set specific rule to error
dotnet_diagnostic.CA1822.severity = error

# Set entire category to warning
dotnet_analyzer_diagnostic.category-Performance.severity = warning

# Disable rule completely
dotnet_diagnostic.IDE0001.severity = none
```

---

## Diagnostic Categories

### 13 Official Code Analysis Categories

Diagnostics are organized into categories for bulk configuration:

1. **Design** - Framework design guideline adherence (CA1000-CA1070)
2. **Documentation** - XML documentation completeness (CA1303-CA1311)
3. **Globalization** - World-ready apps and libraries (CA1303-CA1311)
4. **Interoperability** - COM and platform portability (CA1300s)
5. **Maintainability** - Code maintainability concerns (CA1500-CA1599)
6. **Naming** - Naming convention compliance (CA1700-CA1727)
7. **Performance** - High-performance code patterns (CA1800-CA1877)
8. **Reliability** - Memory and threading correctness (CA2000-CA2265)
9. **Security** - Security vulnerability prevention (CA2000+, CA3000+, CA5000+)
10. **SingleFile** - Single-file application support (CA1400-CA1499)
11. **Style** - Code style consistency (IDE-prefixed rules: IDE0001-IDE0380)
12. **Usage** - Correct API usage patterns (CA1000-CA2000)
13. **Interoperability** - External interop concerns

### Bulk Configuration by Category

```editorconfig
# Set all performance rules to warning
dotnet_analyzer_diagnostic.category-Performance.severity = warning

# Set all naming rules to error
dotnet_analyzer_diagnostic.category-Naming.severity = error

# Disable all style rules
dotnet_analyzer_diagnostic.category-Style.severity = none
```

### Common Diagnostic ID Prefixes

| Prefix | Type | Example | Source |
|--------|------|---------|--------|
| **CS** | Compiler | CS0001, CS1001 | C# Compiler |
| **VB** | Compiler | VB1234 | VB Compiler |
| **CA** | Code Analysis/Quality | CA1822, CA2000 | .NET Analyzers |
| **IDE** | Code Style | IDE0001, IDE0021 | Visual Studio |
| **SA** | Style Analysis | SA1116, SA1400 | StyleCop |
| **SP** | Suppressor Info | SP0001 | Diagnostic Suppressors |

---

## Diagnostic Flow to LSP Clients

### OmniSharp Integration

OmniSharp acts as a language server that bridges Roslyn diagnostics to IDE clients via LSP:

```
Roslyn Compiler
    ↓
Analyzer Diagnostics + Compiler Diagnostics
    ↓
OmniSharp LSP Server
    ↓
LSP Diagnostic Message (PublishDiagnostics notification)
    ↓
IDE/Editor Client (Neovim, VS Code, etc.)
    ↓
Visual Display (squiggles, error list, status line)
```

### Diagnostic Reporting Flow

1. **Compilation Phase**:
   - Roslyn compiler runs syntax and semantic analysis
   - Compiler diagnostics (CS errors) generated
   - Registered analyzers execute their registered actions

2. **Analyzer Execution**:
   - Analyzers process syntax trees, symbols, semantic models
   - Call `context.ReportDiagnostic()` for violations
   - Diagnostics collected with locations and metadata

3. **Configuration Application**:
   - .editorconfig rules applied
   - Ruleset rules applied
   - Global analyzer config rules applied
   - Severity overrides computed (ErrorSeverity.Error → DefaultSeverity.Warning)

4. **LSP Transmission**:
   - OmniSharp packages diagnostics as LSP messages
   - `PublishDiagnostics` notification sent to client
   - Each diagnostic includes:
     - Range (line, column positions)
     - Message
     - Severity (converted to LSP levels)
     - Code (diagnostic ID)
     - Source (e.g., "omnisharp", "csharp")

5. **IDE Display**:
   - Squiggles rendered in editor
   - Error list populated
   - Light bulb (quick fix) suggestions shown
   - Status bar updated with error count

### LSP Diagnostic Severity Mapping

Roslyn DiagnosticSeverity maps to LSP DiagnosticSeverity:

| Roslyn Severity | LSP Value | IDE Display |
|-----------------|-----------|-------------|
| Error | 1 | Red squiggle |
| Warning | 2 | Yellow squiggle |
| Info | 3 | Blue squiggle |
| Hidden | 4 (custom) | Hidden |

### OmniSharp Configuration for Diagnostics

OmniSharp accepts configuration for:

- **RoslynExtensionsOptions**:
  - `EnableAnalyzersSupport`: Enable/disable Roslyn analyzers (true/false)
  - `EnableImportCompletion`: Show import suggestions (true/false)
  - `AnalyzeOpenDocumentsOnly`: Analyze only open files vs entire solution

- **FormattingOptions**:
  - `EnableEditorConfigSupport`: Honor .editorconfig settings
  - `OrganizeImports`: Auto-organize using/import statements

**Example Configuration**:
```lua
-- Neovim init.lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
    },
  },
}
```

---

## Configuration Mechanisms

### 1. EditorConfig Files (.editorconfig)

**Scope**: File and folder level
**Format**: INI-style with section headers

```editorconfig
# For C# files
[*.cs]

# Specific rule severity
dotnet_diagnostic.CA1822.severity = error
dotnet_diagnostic.IDE0001.severity = warning

# Category-level configuration
dotnet_analyzer_diagnostic.category-Performance.severity = warning
dotnet_analyzer_diagnostic.category-Naming.severity = error

# Disable entire categories
dotnet_analyzer_diagnostic.category-Style.severity = none
```

**Precedence**: Deeper paths override shallower ones

### 2. Global AnalyzerConfig Files (.globalconfig)

**Scope**: Project level, no section headers
**Format**: Key-value pairs with `is_global = true`

```ini
is_global = true
global_level = 1

# All rules in project
dotnet_diagnostic.CA1822.severity = error
dotnet_analyzer_diagnostic.category-Security.severity = error
```

**Precedence**: Higher `global_level` values take precedence

### 3. Ruleset Files (.ruleset)

**Status**: Deprecated in favor of .editorconfig/.globalconfig
**Still Supported**: For legacy projects

```xml
<?xml version="1.0" encoding="utf-8"?>
<RuleSet Name="SecurityRules" ToolsVersion="16.0">
  <Rules AnalyzerId="Microsoft.CodeAnalysis" RuleNamespace="Microsoft.CodeAnalysis.CSharp">
    <Rule Id="CA1822" Action="Error" />
    <Rule Id="CA2000" Action="Warning" />
  </Rules>
</RuleSet>
```

### 4. Suppressions in Code

**Pragma Directives**:
```csharp
#pragma warning disable CA1822
// code that violates CA1822
#pragma warning restore CA1822
```

**SuppressMessageAttribute**:
```csharp
[System.Diagnostics.CodeAnalysis.SuppressMessage(
    "Performance",
    "CA1822:MarkMembersAsStatic")]
public void MyMethod() { }
```

### 5. MSBuild Properties

**Project File Configuration**:
```xml
<PropertyGroup>
  <AnalysisMode>All</AnalysisMode>
  <AnalysisLevel>latest</AnalysisLevel>
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  <EnableNETAnalyzers>true</EnableNETAnalyzers>
</PropertyGroup>
```

**MSBuild Properties**:
- `AnalysisMode`: None, Default, Minimum, Recommended, All
- `AnalysisLevel`: Specific SDK version ("8.0") or "latest"
- `EnforceCodeStyleInBuild`: Enable style rules in builds
- `EnableNETAnalyzers`: Manual enable/disable

### 6. Command-Line Compiler Options

**Precedence**: Highest priority (overrides all file-based settings)

```bash
# Warning as error
dotnet build -p:TreatWarningsAsErrors=true

# Specific rule
dotnet build -p:WarningsNotAsErrors=CS1234
```

### Configuration Precedence (Highest to Lowest)

```
1. Command-line compiler options
2. EditorConfig entries (deeper paths win)
3. Global AnalyzerConfig entries (higher level wins)
4. MSBuild properties
5. DiagnosticDescriptor DefaultSeverity
```

---

## Compiler vs Analyzer Diagnostics

### Compiler Diagnostics (CS/VB codes)

**What**: Errors and warnings from language compilation process
**Examples**: CS0001 (access level), CS1001 (syntax error), CS0219 (unused variable)
**When**: Always run, cannot be disabled (mostly)
**Speed**: Fast, built into compiler
**Severity**: Controlled separately

**Key Characteristics**:
- Generated by Roslyn compiler frontend
- Syntax and semantic analysis violations
- Always enabled during compilation
- Cannot be suppressed except via pragmas

**Examples**:
- CS0103: Name not found
- CS0227: Cannot use ref/out on async method
- CS0619: Type/Member is obsolete

### Analyzer Diagnostics (CA/IDE/SA codes)

**What**: Code quality, style, and design issues
**Examples**: CA1822 (mark as static), IDE0001 (simplify names), SA1116 (parameter alignment)
**When**: Only when enabled
**Speed**: Slower, can be disabled for performance
**Severity**: Configurable

**Key Characteristics**:
- Generated by separate analysis passes (CompilerDiagnosticAnalyzer)
- Can be enabled/disabled via configuration
- Can be suppressed via configuration
- Extensible (third-party analyzers)

**Examples**:
- **Code Quality** (CA): Performance, Security, Design
- **Code Style** (IDE): Naming, formatting, language features
- **Third-party** (SA, etc): StyleCop, Roslynator

### Key Differences

| Aspect | Compiler | Analyzer |
|--------|----------|----------|
| **Prefix** | CS, VB | CA, IDE, SA, etc. |
| **Requirement** | Always enabled | Optional, configurable |
| **Source** | Built-in compiler | Separate analyzers |
| **Suppression** | Limited (pragmas only) | Full configuration support |
| **Performance** | Fast | Variable (can be slow) |
| **Customization** | None | Fully customizable |
| **Third-party** | No | Yes (StyleCop, Roslynator) |

### When Each Type Runs

```
Compilation:
1. Lexical analysis
2. Syntax analysis (generates CS syntax errors)
3. Semantic analysis (generates CS semantic errors)
4. Analyzer passes (generates CA/IDE/SA diagnostics)
5. Output diagnostics (combined list)
```

---

## DiagnosticDescriptor and DiagnosticAnalyzer

### DiagnosticDescriptor Structure

DiagnosticDescriptor defines the metadata for all diagnostics of a specific rule.

**Required Properties**:
```csharp
public DiagnosticDescriptor(
    string id,                          // "CA1822"
    LocalizableString title,            // "Mark members as static"
    LocalizableString messageFormat,    // "Method '{0}' can be static"
    string category,                    // "Performance"
    DiagnosticSeverity defaultSeverity, // Error, Warning, Info, Hidden
    bool isEnabledByDefault,            // true/false
    LocalizableString description = null,
    string helpLinkUri = null,
    params string[] customTags)
```

**Example**:
```csharp
private static readonly DiagnosticDescriptor Rule = new(
    id: "CA1822",
    title: "Mark members as static",
    messageFormat: "Member '{0}' does not access instance data and can be marked static",
    category: "Performance",
    defaultSeverity: DiagnosticSeverity.Warning,
    isEnabledByDefault: true,
    description: "Methods that do not access instance data should be static.",
    helpLinkUri: "https://docs.microsoft.com/dotnet/fundamentals/code-analysis/quality-rules/ca1822");
```

### DiagnosticAnalyzer Implementation

DiagnosticAnalyzer is the base class for custom analyzers.

**Core Methods**:
```csharp
public abstract class DiagnosticAnalyzer
{
    // Supported diagnostics this analyzer produces
    public abstract ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; }

    // Register analysis actions
    public abstract void Initialize(AnalysisContext context);
}
```

**Example Analyzer**:
```csharp
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public class ConstVariableAnalyzer : DiagnosticAnalyzer
{
    private static readonly DiagnosticDescriptor Rule = new(
        id: "CUSTOM001",
        title: "Variable can be const",
        messageFormat: "Variable '{0}' can be const",
        category: "Usage",
        defaultSeverity: DiagnosticSeverity.Info,
        isEnabledByDefault: true);

    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics =>
        ImmutableArray.Create(Rule);

    public override void Initialize(AnalysisContext context)
    {
        // Register to analyze variable declarations
        context.RegisterSyntaxNodeAction(AnalyzeVariableDeclaration,
            SyntaxKind.VariableDeclarator);
    }

    private void AnalyzeVariableDeclaration(SyntaxNodeAnalysisContext context)
    {
        var variable = (VariableDeclaratorSyntax)context.Node;

        // Perform analysis...
        if (/* should be const */)
        {
            // Report diagnostic
            context.ReportDiagnostic(
                Diagnostic.Create(Rule, variable.GetLocation(), variable.Identifier.Text));
        }
    }
}
```

### Registering Actions

Analyzers register different action types:

```csharp
// Syntax tree analysis
context.RegisterSyntaxTreeAction(action);

// Syntax node analysis (specific node kinds)
context.RegisterSyntaxNodeAction(action, nodeKinds);

// Symbol analysis
context.RegisterSymbolAction(action, symbols);

// Code block analysis
context.RegisterCodeBlockAction(action);

// Compilation start/end
context.RegisterCompilationStartAction(action);
context.RegisterCompilationEndAction(action);
```

---

## Diagnostic Suppressors

### Purpose

DiagnosticSuppressor enables platform/library authors to suppress false-positive diagnostics from compilers and analyzers in their specific context.

**Real-World Example**: Unity's `[SerializeField]` attribute suppresses CS0649 (field never assigned) warnings because Unity's serialization system assigns these fields at runtime.

### Suppressor Architecture

Suppressors run AFTER all compiler/analyzer diagnostics are computed, allowing them to:
1. Analyze complete semantic information
2. Detect context-specific patterns
3. Suppress false positives intelligently

```
Compilation
    ↓
Compiler Diagnostics (CS errors)
    ↓
Analyzer Diagnostics (CA/IDE rules)
    ↓
Diagnostic Suppressors (run here)
    ↓
Final Diagnostic List
```

### Eligibility for Suppression

Only suppressible diagnostics meet these criteria:

1. **Not an error**: DefaultSeverity ≠ DiagnosticSeverity.Error
2. **Configurable**: Not tagged with `WellKnownDiagnosticTags.NotConfigurable`
3. **Not already suppressed**: No pragma or SuppressMessageAttribute

### Implementing a Suppressor

```csharp
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public class UnitySerializeFieldSuppressor : DiagnosticSuppressor
{
    private static readonly SuppressionDescriptor Rule =
        new SuppressionDescriptor(
            id: "SP0001",
            suppressedDiagnosticId: "CS0649",
            justification: "Fields are assigned by Unity serialization");

    public override ImmutableArray<SuppressionDescriptor> SupportedSuppressions =>
        ImmutableArray.Create(Rule);

    public override void ReportSuppressions(SuppressionAnalysisContext context)
    {
        foreach (var diagnostic in context.ReportedDiagnostics)
        {
            if (diagnostic.Id != "CS0649") continue;

            // Check if field has [SerializeField] attribute
            var field = GetFieldForDiagnostic(context, diagnostic);
            if (field != null && HasSerializeFieldAttribute(field))
            {
                context.ReportSuppression(
                    Suppression.Create(Rule, diagnostic));
            }
        }
    }
}
```

### Suppression User Control

Users can:
- Disable suppressors via `/nowarn` switch
- Configure via ruleset files
- Audit suppressions via SP0001 info diagnostics

---

## Real-World Examples

### Example 1: StyleCop SA1116 (Parameters Not on Same Line)

**Diagnostic**:
- ID: SA1116
- Title: Parameters not on same line
- Category: Formatting
- DefaultSeverity: Warning

**Detection**:
```csharp
// Violates SA1116 - parameters on different lines
public void MyMethod(
    int parameter1,  // Line 2
    int parameter2)  // Line 3
{
}

// Correct - parameters on same line or each on own line
public void MyMethod(int parameter1, int parameter2) { }

public void MyMethod(
    int parameter1,
    int parameter2)
{
}
```

**Configuration** (.editorconfig):
```editorconfig
# Make StyleCop formatting rules errors in build
dotnet_diagnostic.SA1116.severity = error
dotnet_diagnostic.SA1117.severity = error
```

### Example 2: CA1822 (Mark Members as Static)

**Diagnostic**:
- ID: CA1822
- Title: Mark members as static
- Category: Performance
- DefaultSeverity: Warning (IDE), Suggestion (Build)

**Detection**:
```csharp
// Violates CA1822 - method doesn't use 'this'
public class UserService
{
    public string GetDefaultName()  // Flagged: can be static
    {
        return "Default User";
    }
}

// Correct - marked as static
public class UserService
{
    public static string GetDefaultName()
    {
        return "Default User";
    }
}
```

**Configuration**:
```editorconfig
# Performance rules
dotnet_analyzer_diagnostic.category-Performance.severity = warning

# Specific rule override
dotnet_diagnostic.CA1822.severity = silent  # Hide in build, show in IDE
```

### Example 3: OmniSharp Configuration for Neovim

**Full Configuration Chain**:

1. **init.lua Configuration**:
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/path/to/solution'),
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,      -- Enable all analyzers
      EnableImportCompletion = true,      -- Enable import suggestions
      AnalyzeOpenDocumentsOnly = false,   -- Analyze entire solution
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,   -- Honor .editorconfig
      OrganizeImports = true,             -- Auto-organize imports
    },
  },
}
```

2. **Project .editorconfig**:
```editorconfig
[*.cs]
# StyleCop formatting rules as errors in build
dotnet_diagnostic.SA1116.severity = error
dotnet_diagnostic.SA1117.severity = error
dotnet_diagnostic.SA1202.severity = error

# Performance as suggestions
dotnet_analyzer_diagnostic.category-Performance.severity = suggestion

# Security as errors
dotnet_analyzer_diagnostic.category-Security.severity = error
```

3. **Execution Flow**:
```
User opens C# file
    ↓
Neovim connects to OmniSharp LSP
    ↓
OmniSharp loads solution (with -s parameter)
    ↓
Roslyn compiles and analyzes code
    ↓
Compiler diagnostics generated (CS errors)
    ↓
Analyzers run (enabled by EnableAnalyzersSupport)
    ↓
.editorconfig applied (severity overrides)
    ↓
OmniSharp sends diagnostics to Neovim
    ↓
Neovim displays squiggles and in `:LspInfo`
```

4. **Diagnostics Displayed**:
- SA1116 violations → red (error)
- Performance violations → blue (suggestion)
- Security violations → red (error)
- CA1822 violations → yellow (warning)

---

## Summary

### Key Takeaways

1. **Roslyn Diagnostics Architecture**:
   - Compiler diagnostics (CS) + Analyzer diagnostics (CA/IDE/SA)
   - Reported through DiagnosticAnalyzer actions
   - Configured via DiagnosticDescriptor metadata
   - Flattened to LSP Diagnostic messages for IDE display

2. **Severity Levels** (4 levels):
   - Error (1) → Red squiggle, build fails
   - Warning (2) → Yellow squiggle, build succeeds
   - Info (3) → Blue squiggle, hidden by default
   - Hidden (4) → No display

3. **Diagnostic Categories** (13 types):
   - Design, Documentation, Globalization, Interoperability, Maintainability, Naming, Performance, Reliability, Security, SingleFile, Style, Usage, Interoperability

4. **Configuration Priority** (highest to lowest):
   - Command-line options
   - EditorConfig entries
   - Global analyzer config
   - MSBuild properties
   - DiagnosticDescriptor defaults

5. **LSP Flow**:
   - Roslyn → Analyzer diagnostics
   - OmniSharp → LSP translation
   - Client → Visual display (Neovim squiggles)

6. **Compiler vs Analyzer**:
   - **Compiler**: Always enabled, CS/VB codes, fast
   - **Analyzer**: Optional, CA/IDE/SA codes, configurable, slower

7. **Suppressors**:
   - Run after compilation/analysis
   - Suppress false positives
   - User-configurable

### For OmniSharp + Neovim Users

To see diagnostics like StyleCop warnings in Neovim:

1. **Configure OmniSharp** (init.lua):
   ```lua
   RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
   ```

2. **Configure .editorconfig** in project root:
   ```editorconfig
   [*.cs]
   dotnet_diagnostic.SA1116.severity = warning
   ```

3. **Configure MSBuild** (optional):
   ```xml
   <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
   <AnalysisMode>All</AnalysisMode>
   ```

4. **Restart OmniSharp**:
   ```vim
   :LspRestart
   ```

5. **Verify**:
   ```bash
   ps aux | grep omnisharp  # Check RoslynExtensionsOptions in command line
   ```

---

## References

- **dotnet/roslyn**: https://github.com/dotnet/roslyn
- **Microsoft Learn - Code Analysis**: https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/
- **Microsoft Learn - Quality Rules**: https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/
- **Microsoft Learn - Style Rules**: https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/style-rules/
- **Microsoft Learn - Configuration Files**: https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/configuration-files/
- **StyleCop.Analyzers**: https://github.com/DotNetAnalyzers/StyleCopAnalyzers
- **OmniSharp**: http://www.omnisharp.net/
- **Roslyn SDK Tutorial**: https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/tutorials/how-to-write-csharp-analyzer-code-fix

---

**Document Created**: 2025-11-13
**Last Updated**: 2025-11-13
**Status**: Complete
