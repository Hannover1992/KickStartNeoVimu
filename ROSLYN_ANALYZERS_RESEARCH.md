# Roslyn Analyzers: Comprehensive Research Documentation

Based on research of the official dotnet/roslyn repository and Microsoft documentation.

**Research Date**: 2025-11-13
**Sources**: dotnet/roslyn (GitHub), dotnet/roslyn-sdk, Microsoft Learn, OmniSharp documentation

---

## Executive Summary

Roslyn analyzers are code analysis tools built on the .NET Compiler Platform. They examine C# and Visual Basic code during design time and build time to identify issues related to style, quality, maintainability, design, and other concerns. Third-party analyzers like StyleCop.Analyzers integrate seamlessly into this ecosystem via NuGet packages and are automatically discovered and loaded by hosts (Visual Studio, OmniSharp, etc.).

---

## Part 1: What Are Roslyn Analyzers?

### Definition

Roslyn analyzers are specialized components that:

1. **Examine code structure and semantics** using Roslyn's compiler platform APIs
2. **Report diagnostics** (issues, warnings, suggestions) in source code
3. **Provide code fixes** through `CodeFixProvider` implementations
4. **Run continuously** as code is written (in IDE) or during build (CLI)

### Official Description

"Roslyn is the open-source implementation of both the C# and Visual Basic compilers with an API surface for building code analysis tools."

### Three Categories of Analyzers

#### 1. **Code Style Analyzers** (IDE prefix)
- Built into Visual Studio
- Enforce consistent coding style
- Examples: variable naming conventions, `var` vs explicit types, spacing
- Configurable through EditorConfig files or text editor options
- Enabled by default in IDE, disabled by default on build

#### 2. **Code Quality Analyzers** (CA prefix)
- Included in .NET 5.0+ SDK
- Enabled by default for .NET 5.0+ projects
- Check for security, performance, design, reliability issues
- Available via `Microsoft.CodeAnalysis.NetAnalyzers` NuGet package
- Spans 15+ categories: Interoperability, Performance, Reliability, Security, Usage, etc.

#### 3. **Third-Party External Analyzers**
- StyleCop.Analyzers (code style enforcement, e.g., SA11xx rules)
- Roslynator (general code improvements)
- Custom organizational analyzers
- Installed as NuGet packages or Visual Studio extensions
- Automatically discovered by the compiler and language servers

---

## Part 2: How Roslyn Analyzers Work

### 2.1 The Analysis Pipeline

```
Compilation → Analyzer Discovery → Initialization → Action Registration → Execution → Diagnostics
```

#### Step 1: Compilation Phase
- Compiler creates syntax trees and semantic model for all source files
- Compilation object passed to analyzers

#### Step 2: Analyzer Discovery
- Runtime discovers all `DiagnosticAnalyzer` implementations:
  - From referenced NuGet packages
  - From project references
  - From Visual Studio extensions
  - From language server configuration

#### Step 3: Initialization (per compilation)
- Each analyzer's `Initialize(AnalysisContext)` method called **once per compilation**
- Analyzer registers action callbacks for specific code elements
- Multiple `Initialize` calls in a session are allowed, but guaranteed once per compilation

#### Step 4: Action Registration & Execution
- Analyzer registers "action" callbacks for specific triggers:
  - **Syntax node actions**: Trigger when specific AST nodes are visited
  - **Symbol actions**: Trigger when specific symbols are analyzed
  - **Code block actions**: Trigger at method/property level
  - **Semantic model actions**: Trigger on entire file semantic model
  - **Compilation start/end actions**: Trigger at compilation boundaries
  - **Syntax tree actions**: Trigger on entire syntax tree

#### Step 5: Concurrency Model
- **No single analyzer's actions execute concurrently** (thread-safe by default)
  - Unless explicitly enabled: `AnalysisContext.EnableConcurrentExecution()`
- **Different analyzers CAN run concurrently** (framework handles synchronization)
- **Host implementations can optimize** by caching results if compilation effects are identical

#### Step 6: Diagnostic Reporting
- Each action reports `Diagnostic` objects containing:
  - Diagnostic ID (e.g., "SA1116", "IDE0001", "CA1000")
  - Location (file, line, column)
  - Message
  - Severity (Error, Warning, Suggestion, Silent, None, Default)
  - Additional metadata (tags, properties)

### 2.2 Action Execution Order

Analyzers follow strict hierarchical ordering:

```
Compilation Start Actions
  ├─ Symbol Start Actions
  │  ├─ Symbol Actions
  │  ├─ Semantic Model Actions
  │  ├─ Code Block Start Actions
  │  │  ├─ Syntax Node Actions (within block)
  │  │  ├─ Operation Actions (within block)
  │  │  └─ Code Block End Actions
  │  └─ Symbol End Actions
  └─ Compilation End Actions
```

**Key Guarantees:**
- Start actions execute before content actions
- Content actions execute before end actions
- Beyond this hierarchy, **no ordering guarantees** between different action types
- Enables parallelization while preventing race conditions

### 2.3 Three Analyzer Implementation Patterns

#### Pattern 1: Stateless Analyzers (Most Common)
```
Most analyzers fall into this category
- Analyze isolated code units
- No state tracking across actions
- Example: Check if variable names follow naming convention
- Simplest to write and test
```

#### Pattern 2: Stateful Analyzers
```
Track context across analyzer actions
- Maintain state in code block start actions
- Analyze state in code block end actions
- Example: Track which variables are used, report unused ones
- More powerful but require thread-safety consideration
- Use `CodeBlockStartedAnalyzer` pattern
```

#### Pattern 3: Compilation-Wide Analyzers
```
Perform whole-solution analysis
- Store data in compilation start actions
- Aggregate data during actions
- Analyze full results in compilation end actions
- Example: Ensure all public types have documentation
- Highest complexity but most powerful
- Use `CompilationStartedAnalyzer` pattern
```

### 2.4 Semantic Analysis Capabilities

Roslyn analyzers can access:

1. **Syntax Information**
   - Complete abstract syntax tree (AST)
   - Every token, trivia, and node preserved
   - Immutable tree structure (thread-safe)

2. **Semantic Information**
   - Symbol definitions and references
   - Type information and resolution
   - Method signatures and overload resolution
   - Inheritance hierarchies

3. **Additional Files**
   - EditorConfig files
   - Custom configuration files
   - XML/JSON metadata
   - `SimpleAdditionalFileAnalyzer` and `XmlAdditionalFileAnalyzer` patterns

---

## Part 3: Analyzer API Surface

### 3.1 Core Types

#### DiagnosticAnalyzer (Base Class)
```csharp
public abstract class DiagnosticAnalyzer
{
    // Required override
    public abstract void Initialize(AnalysisContext context);

    // Metadata about the analyzer
    public abstract ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; }
}
```

#### DiagnosticDescriptor (Metadata)
```csharp
public class DiagnosticDescriptor
{
    public string Id { get; }                    // e.g., "SA1116"
    public string Title { get; }                 // e.g., "Parameters should be on same line"
    public string Category { get; }              // e.g., "Spacing"
    public DiagnosticSeverity DefaultSeverity { get; }
    public string MessageFormat { get; }         // e.g., "Parameters must start on new line"
    public string Description { get; }
    public ImmutableHashSet<string> CustomTags { get; }
}
```

#### Diagnostic (Runtime Result)
```csharp
public class Diagnostic
{
    public DiagnosticDescriptor Descriptor { get; }
    public Location Location { get; }            // File, line, column
    public DiagnosticSeverity Severity { get; }
    public string Message { get; }
    public ImmutableDictionary<string, string?> Properties { get; }
}
```

#### DiagnosticSeverity (Enum)
```csharp
public enum DiagnosticSeverity
{
    Hidden = 0,       // Not visible, often for compiler internals
    Info = 1,         // Informational (light bulb, no underline)
    Warning = 2,      // Yellow underline
    Error = 3         // Red underline
}
```

#### AnalysisContext (Action Registration)
```csharp
public class AnalysisContext
{
    // Register for specific syntax node types
    void RegisterSyntaxNodeAction<TLanguageKindEnum>(
        Action<SyntaxNodeAnalysisContext> action,
        params TLanguageKindEnum[] syntaxKinds);

    // Register for symbol analysis
    void RegisterSymbolAction(
        Action<SymbolAnalysisContext> action,
        params SymbolKind[] symbolKinds);

    // Register for compilation-wide analysis
    void RegisterCompilationStartAction(
        Action<CompilationStartAnalysisContext> context);

    void RegisterCompilationEndAction(
        Action<CompilationAnalysisContext> context);

    // Register for semantic model analysis
    void RegisterSemanticModelAction(
        Action<SemanticModelAnalysisContext> context);

    // Register for code blocks (method bodies, property getters, etc.)
    void RegisterCodeBlockStartAction<TLanguageKindEnum>(
        Action<CodeBlockStartAnalysisContext<TLanguageKindEnum>> action);

    void RegisterCodeBlockEndAction(
        Action<CodeBlockAnalysisContext> action);

    // Enable concurrent execution (performance optimization)
    void EnableConcurrentExecution();
}
```

### 3.2 Context Types for Each Action

#### SyntaxNodeAnalysisContext
```csharp
public class SyntaxNodeAnalysisContext
{
    public SyntaxNode Node { get; }              // The AST node being analyzed
    public ImmutableArray<ISymbol> FilteredDeclarationSymbols { get; }
    public SemanticModel SemanticModel { get; }
    public Compilation Compilation { get; }
    public AnalyzerOptions Options { get; }

    public void ReportDiagnostic(Diagnostic diagnostic);
}
```

#### SymbolAnalysisContext
```csharp
public class SymbolAnalysisContext
{
    public ISymbol Symbol { get; }               // Symbol being analyzed
    public Compilation Compilation { get; }
    public AnalyzerOptions Options { get; }

    public void ReportDiagnostic(Diagnostic diagnostic);
}
```

#### CompilationStartAnalysisContext
```csharp
public class CompilationStartAnalysisContext
{
    public Compilation Compilation { get; }
    public AnalyzerOptions Options { get; }
    public ISymbol Compilation.GlobalNamespace { get; }

    // Register nested analyzers for this compilation
    public void RegisterSyntaxTreeAction(Action<SyntaxTreeAnalysisContext> action);
    public void RegisterSymbolAction(Action<SymbolAnalysisContext> action);
    // ... other registration methods
}
```

### 3.3 Analyzer Discovery Mechanism

**How Analyzers Are Found:**

1. **NuGet Package Scanning**
   - Compiler scans referenced NuGet packages
   - Looks for `Microsoft.CodeAnalysis.CSharp` analyzer attribute
   - Loads all types implementing `DiagnosticAnalyzer`

2. **Project References**
   - Compiler scans project references
   - Automatically discovers `DiagnosticAnalyzer` implementations

3. **Language Server Configuration**
   - LSP/OmniSharp reads `.csproj` properties:
     - `EnableNETAnalyzers` (default: true for .NET 5+)
     - `AnalysisMode` (None, Default, Minimum, Recommended, All)
     - `EnforceCodeStyleInBuild` (enable IDE rules on build)
   - LSP reads `omnisharp.json` settings:
     - `RoslynExtensionsOptions:EnableAnalyzersSupport`
     - `RoslynExtensionsOptions:EnableImportCompletion`
     - `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly`

4. **Reflection-Based Loading**
   - Runtime uses reflection to instantiate `DiagnosticAnalyzer` types
   - No registration file needed—discovered automatically

### 3.4 Code Fixer Integration

#### CodeFixProvider (Remediation)
```csharp
public abstract class CodeFixProvider
{
    // Diagnostics this provider can fix
    public abstract ImmutableArray<string> FixableDiagnosticIds { get; }

    // Compute fixes for a diagnostic
    public abstract Task RegisterCodeFixesAsync(
        CodeFixContext context);

    // Optional: FixAll provider for batch fixing
    public virtual CodeFixProvider GetFixAllProvider(CodeFixAllContext context)
    {
        return WellKnownFixAllProviders.BatchFixer;  // Default
    }
}
```

#### CodeFixContext
```csharp
public class CodeFixContext
{
    public Document Document { get; }            // Source file
    public TextSpan Span { get; }                // Affected span
    public ImmutableArray<Diagnostic> Diagnostics { get; }

    public void RegisterCodeFix(
        CodeAction action,
        ImmutableArray<Diagnostic> diagnostics);
}
```

#### CodeAction (User-Facing Fix)
```csharp
public abstract class CodeAction
{
    public string Title { get; }                 // "Remove unused using"
    public string EquivalenceKey { get; }        // For grouping in FixAll

    public abstract Task<Document> GetChangedDocumentAsync(
        CancellationToken cancellationToken);
}
```

### 3.5 Diagnostic Suppression API

#### DiagnosticSuppressor (Suppress False Positives)
```csharp
public abstract class DiagnosticSuppressor : DiagnosticAnalyzer
{
    public abstract ImmutableArray<SuppressionDescriptor> SupportedSuppressions { get; }

    public abstract void Initialize(AnalysisContext context);
}
```

**How Suppressors Work:**

1. Analyzer and compiler run first, produce diagnostics
2. **All suppressors run after**, receiving collection of diagnostics
3. Suppressors identify false positives in their context
4. Report `Suppression` objects linking diagnostic to `SuppressionDescriptor`
5. Multiple suppressors can suppress same diagnostic (results unioned)
6. End users can disable suppression via `/nowarn` or ruleset entries

**Example:** Unity development uses suppressors to suppress false "unused" warnings for Unity magic methods like `OnEnable()`.

---

## Part 4: Analyzer Lifecycle and Discovery

### 4.1 Compilation-Level Lifecycle

```
1. Compiler Creates Compilation
   ↓
2. Host Calls DiagnosticAnalyzer.Initialize(AnalysisContext)
   ↓
3. Analyzer Registers Action Callbacks
   ↓
4. Compiler Invokes Actions as Code Structures Encountered
   ├─ Syntax nodes walked
   ├─ Symbols resolved
   ├─ Code blocks analyzed
   └─ Semantic models processed
   ↓
5. Analyzer Reports Diagnostics
   ↓
6. Compiler Collects All Diagnostics
   ↓
7. Suppressors Run (Process Reported Diagnostics)
   ↓
8. Final Diagnostics Delivered to Host (IDE/LSP/Build System)
```

### 4.2 IDE-Level Lifecycle (OmniSharp/LSP)

```
1. File Opened in Editor
   ↓
2. LSP Server (OmniSharp) Loads Project
   ↓
3. Compilation Created for Project
   ↓
4. Analyzer Discovery Phase
   - Scan project .csproj for analyzer packages
   - Scan NuGet packages for DiagnosticAnalyzer types
   - Load configuration from:
     * omnisharp.json (RoslynExtensionsOptions)
     * .editorconfig
     * ruleset files
   ↓
5. Analyzers Instantiated and Initialized
   ↓
6. Analyzer Actions Registered
   ↓
7. For Each Code Change:
   - Parse updated syntax tree
   - Update semantic model
   - Run registered actions
   - Collect diagnostics
   - Send diagnostics to editor (LSP publishDiagnostics)
   ↓
8. Editor Displays Squiggles, Light Bulbs, etc.
```

### 4.3 Build-Time Lifecycle

```
1. dotnet build Invoked
   ↓
2. Project Loaded and Compiled
   ↓
3. Analyzer Discovery (same as IDE)
   - Read analyzer packages
   - Respect AnalysisMode, EnforceCodeStyleInBuild settings
   ↓
4. For Each File Compilation:
   - Run analyzers
   - Collect diagnostics
   - Optionally suppress based on #pragma, ruleset
   ↓
5. Report Results
   - Display in build output
   - Write to error list
   - Include in MSBuild log
   - May fail build if Error severity
```

---

## Part 5: How Third-Party Analyzers Integrate (StyleCop Example)

### 5.1 StyleCop.Analyzers Overview

**What is StyleCop?**
- Analyzes C# code for style violations (SA11xx, SA12xx, etc.)
- Highly configurable with EditorConfig
- Integrated into IDEs, build systems, and language servers automatically

**Integration Mechanism:**

```
1. Install NuGet Package: StyleCop.Analyzers (v1.1.118)
   ↓
2. Package Contains DiagnosticAnalyzer Types
   - StyleCopAnalyzers.StyleCopAnalyzer
   - Other rule-specific analyzers
   ↓
3. Compiler/LSP Discovers via Reflection
   - During project load, scans bin/Debug/.../analyzers/
   - Finds [ExportDiagnosticAnalyzer("CSharp")] attributes
   ↓
4. Analyzer Instances Created & Initialized
   - Each analyzer registers syntax node actions
   - Example: SA1116 registers action for ParameterListSyntax
   ↓
5. During Code Analysis:
   - Source code parsed
   - Actions triggered on relevant nodes
   - StyleCop rules checked
   - Diagnostics reported with SA11xx IDs
   ↓
6. Configuration via EditorConfig
   - .editorconfig files define rule severity
   - Example: dotnet_diagnostic.SA1116.severity = warning
   ↓
7. Displayed in IDE/LSP
   - Squiggles show violations
   - Light bulbs offer fixes (if CodeFixProvider implemented)
   - Messages shown on hover
```

### 5.2 Configuration Points for StyleCop

**1. Project File (.csproj)**
```xml
<PropertyGroup>
  <EnableNETAnalyzers>true</EnableNETAnalyzers>
  <AnalysisMode>All</AnalysisMode>
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
</PropertyGroup>
```

**2. .editorconfig**
```editorconfig
# StyleCop rules
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1117.severity = error
dotnet_diagnostic.SA1118.severity = silent
indent_style = space
indent_size = 4
```

**3. ruleset Files**
```xml
<?xml version="1.0" encoding="utf-8"?>
<RuleSet Name="My Custom Rules" ToolsVersion="16.0">
  <Rules AnalyzerId="StyleCop.CSharp.SpacingRules" RuleNamespace="StyleCop.CSharp.SpacingRules">
    <Rule Id="SA1116" Action="Warning" />
    <Rule Id="SA1117" Action="Error" />
  </Rules>
</RuleSet>
```

**4. omnisharp.json (For LSP Servers)**
```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  }
}
```

**5. Command Line (dotnet build)**
```bash
dotnet build /p:EnableNETAnalyzers=true /p:AnalysisMode=All
```

---

## Part 6: IDE and LSP Integration

### 6.1 How Analyzers Integrate with Visual Studio

```
Visual Studio
  ├─ Roslyn Workspace (in-memory representation of solution)
  │  ├─ Compilation (C# compilation)
  │  └─ Semantic Model (per file)
  │
  ├─ Analyzer Processor
  │  ├─ Discovers analyzers from NuGet packages
  │  ├─ Instantiates and initializes
  │  └─ Runs on background thread
  │
  ├─ Diagnostic Collector
  │  ├─ Receives diagnostics from analyzers
  │  └─ Merges with compiler diagnostics
  │
  └─ Editor Display
     ├─ Squiggles (colored underlines)
     ├─ Error List window
     ├─ Light Bulbs (code fix suggestions)
     └─ Hover information
```

### 6.2 How Analyzers Integrate with OmniSharp/LSP

```
OmniSharp (Language Server)
  ├─ Project Loader
  │  ├─ Loads .csproj files
  │  ├─ Scans analyzer NuGet packages
  │  └─ Creates Roslyn Compilation
  │
  ├─ Analyzer Service
  │  ├─ Discovers DiagnosticAnalyzer types
  │  ├─ Respects RoslynExtensionsOptions config:
  │  │  ├─ EnableAnalyzersSupport (default: true)
  │  │  ├─ EnableImportCompletion (default: true)
  │  │  └─ AnalyzeOpenDocumentsOnly (default: false)
  │  └─ Runs analyzers on compilation
  │
  ├─ Diagnostic Processor
  │  ├─ Collects diagnostics
  │  ├─ Filters based on configuration
  │  └─ Sends via LSP publishDiagnostics
  │
  └─ LSP Protocol
     ├─ textDocument/publishDiagnostics
     │  ├─ Sends list of Diagnostic objects to client
     │  ├─ Each diagnostic has:
     │  │  ├─ range (location in file)
     │  │  ├─ message (problem description)
     │  │  ├─ severity (1=Error, 2=Warning, 3=Info, 4=Hint)
     │  │  └─ code (diagnostic ID like "SA1116")
     │  │
     │  └─ Editor (Neovim/VS Code/etc.)
     │     ├─ Displays squiggles
     │     ├─ Shows in diagnostics list
     │     └─ Offers code fixes (via textDocument/codeAction)
```

### 6.3 Critical Configuration for OmniSharp

When `RoslynExtensionsOptions:EnableAnalyzersSupport=true`:
- OmniSharp **includes** analyzer diagnostics in LSP responses
- Without this, analyzer diagnostics are **not reported** to the editor
- Set via omnisharp.json or LSP initialization options

**Example omnisharp.json:**
```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  }
}
```

**Command-line equivalent:**
```bash
omnisharp -s /path/to/solution \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
```

**Verified in Process:**
When OmniSharp runs, check process arguments:
```bash
ps aux | grep omnisharp
# Should show:
# RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

---

## Part 7: Configuration Mechanisms

### 7.1 Configuration Hierarchy (Precedence)

```
Command Line Arguments (highest precedence)
  ↓
Environment Variables
  ↓
File: omnisharp.json (project root)
  ↓
File: .editorconfig (per file/folder)
  ↓
File: .ruleset (per project)
  ↓
Project File (.csproj properties)
  ↓
Default Analyzer Settings (lowest precedence)
```

### 7.2 EditorConfig Configuration

**File: `.editorconfig` (placed in project root or solution root)**

```editorconfig
# EditorConfig Rules (apply to all files)

# Code style (IDE rules)
csharp_prefer_braces = true:suggestion
csharp_indent_case_contents = true
indent_style = space
indent_size = 4

# Diagnostics severity
dotnet_diagnostic.IDE0001.severity = suggestion
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.CA1000.severity = warning

# StyleCop specific
dotnet_diagnostic.SA0100.severity = none          # Disable rule
dotnet_diagnostic.SA1101.severity = warning       # Enable rule
dotnet_diagnostic.SA1600.severity = silent        # Hidden but still checked
```

**Severity Levels:**
- `none` - Rule disabled
- `silent` - Checked but not displayed (internal compiler use)
- `suggestion` - Light blue underline (info level)
- `warning` - Yellow underline
- `error` - Red underline, blocks build

### 7.3 Ruleset File Configuration

**File: `MyRules.ruleset`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<RuleSet Name="My StyleCop Rules" ToolsVersion="16.0">
  <Localization ResourceAssembly="Microsoft.VisualStudio.CodeAnalysis.RuleSets.Strings.dll" ResourceBaseName="Microsoft.VisualStudio.CodeAnalysis.RuleSets.Strings.Localized">
    <Name Resource="MyStyleCopRules_Name" />
  </Localization>

  <!-- StyleCop Spacing Rules -->
  <Rules AnalyzerId="StyleCop.CSharp.SpacingRules" RuleNamespace="StyleCop.CSharp.SpacingRules">
    <Rule Id="SA1116" Action="Warning" />    <!-- Enable as warning -->
    <Rule Id="SA1117" Action="Error" />      <!-- Enable as error -->
    <Rule Id="SA1118" Action="None" />       <!-- Disable -->
  </Rules>

  <!-- Other analyzer rules -->
  <Rules AnalyzerId="Microsoft.CodeAnalysis.CSharp.NetAnalyzers" RuleNamespace="Microsoft.CodeAnalysis.CSharp.NetAnalyzers">
    <Rule Id="CA1000" Action="Warning" />
  </Rules>
</RuleSet>
```

**Reference in .csproj:**
```xml
<PropertyGroup>
  <CodeAnalysisRuleSet>MyRules.ruleset</CodeAnalysisRuleSet>
</PropertyGroup>
```

### 7.4 Project File Configuration

**File: `.csproj` (MSBuild properties)**

```xml
<PropertyGroup>
  <!-- Enable all analyzers -->
  <EnableNETAnalyzers>true</EnableNETAnalyzers>

  <!-- Analysis mode: None, Default, Minimum, Recommended, All -->
  <AnalysisMode>All</AnalysisMode>

  <!-- Enable code style rules during build (not just IDE) -->
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>

  <!-- Use specific ruleset -->
  <CodeAnalysisRuleSet>MyRules.ruleset</CodeAnalysisRuleSet>

  <!-- Analysis level: lock to specific SDK version -->
  <AnalysisLevel>6</AnalysisLevel>
</PropertyGroup>
```

**AnalysisMode Values:**
- `None` - No analyzers
- `Default` - Only recommended rules (safe by default)
- `Minimum` - Highest-value rules only
- `Recommended` - Recommended + extra rules
- `All` - All available rules

### 7.5 OmniSharp Configuration (omnisharp.json)

**File: `omnisharp.json` (project root or ~/.omnisharp/)**

```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
```

**Key Setting Explanations:**

| Setting | Values | Effect |
|---------|--------|--------|
| `EnableAnalyzersSupport` | true/false | Include StyleCop and other analyzers in diagnostics |
| `AnalyzeOpenDocumentsOnly` | true/false | If true, only analyze files open in editor (faster but incomplete) |
| `EnableImportCompletion` | true/false | Show import suggestions for unknown types |
| `EnableEditorConfigSupport` | true/false | Read .editorconfig files |
| `OrganizeImports` | true/false | Format using statements on save |

### 7.6 Suppressing Specific Diagnostics

**In Source Code (per file):**
```csharp
#pragma warning disable SA1116
public void MyMethod(
    int parameter1,
    int parameter2)  // Suppressed: parameters not on same line
{
}
#pragma warning restore SA1116
```

**Per Rule in .editorconfig:**
```editorconfig
dotnet_diagnostic.SA1116.severity = none  # Disable entirely
```

**Per Rule in ruleset:**
```xml
<Rule Id="SA1116" Action="None" />
```

**Command Line:**
```bash
dotnet build /p:NoWarn=SA1116;SA1117  # Suppress multiple rules
```

---

## Part 8: Analyzer Execution Lifecycle (Detailed)

### 8.1 When Analyzers Run

#### In IDE (OmniSharp/Visual Studio)
- **On file open** - Analyzers run on entire file
- **On file change** - Incrementally re-analyze changed regions
- **On file save** - Full re-analysis (if configured)
- **Continuous** - Background analysis while editing
- **On demand** - Via "Run Code Analysis" command

#### In Build (dotnet build)
- **On build** - Analyzers run during compilation
- **One-time** - Per file compilation
- **Can fail build** - If Error severity diagnostics found
- **Respects configuration** - AnalysisMode, EnforceCodeStyleInBuild

### 8.2 Analyzer Action Execution

**Example: StyleCop SA1116 (Parameters must be on same line)**

```
1. Compiler creates syntax tree for file

2. DiagnosticAnalyzer.Initialize() called with AnalysisContext

3. StyleCop analyzer registers:
   context.RegisterSyntaxNodeAction(
       action => CheckParameterFormatting(action),
       SyntaxKind.ParameterList)

4. Compiler encounters ParameterListSyntax node

5. CheckParameterFormatting() invoked with SyntaxNodeAnalysisContext

6. Analyzer examines parameter positions

7. If violation detected:
   context.ReportDiagnostic(Diagnostic.Create(
       descriptor: SA1116Descriptor,
       location: parameterNode.Location,
       messageArgs: new[] { "parameter", "same line" }))

8. Compiler collects diagnostic

9. After all analyzers complete, suppressors run

10. Final diagnostics sent to LSP client

11. Editor displays squiggles and suggestions
```

### 8.3 Performance Considerations

**Thread Safety:**
- Single analyzer actions are thread-safe by default (serialized)
- Enable concurrent execution for performance: `context.EnableConcurrentExecution()`
- Different analyzers run in parallel automatically

**Caching:**
- Compilation can be reused if nothing changed
- OmniSharp caches compilation between edits
- Only changed files re-analyzed (incremental analysis)

**Analysis Scope:**
- `AnalyzeOpenDocumentsOnly=false` - Analyze entire solution (slow but complete)
- `AnalyzeOpenDocumentsOnly=true` - Only analyze open files (fast but incomplete)

---

## Part 9: Summary Table - Analyzer Components

| Component | Purpose | Example |
|-----------|---------|---------|
| **DiagnosticAnalyzer** | Base class for all analyzers | StyleCopAnalyzer, CA1000Analyzer |
| **DiagnosticDescriptor** | Metadata about a rule | SA1116Descriptor (title, category, severity) |
| **Diagnostic** | Runtime violation found | SA1116 at line 42, column 5 |
| **AnalysisContext** | For registering actions | Initialize(AnalysisContext) |
| **SyntaxNodeAnalysisContext** | For analyzing syntax nodes | Passed to syntax node actions |
| **SymbolAnalysisContext** | For analyzing symbols | Passed to symbol actions |
| **CodeFixProvider** | Provides automated fixes | Fix "remove unused using" |
| **CodeAction** | User-facing fix suggestion | "Remove unused using statement" |
| **DiagnosticSuppressor** | Suppress false positives | Unity suppressor for magic methods |
| **SuppressionDescriptor** | Metadata for suppression | Suppress CA1000 in specific context |

---

## Part 10: Key Insights for LSP Integration

### Why StyleCop Warnings Don't Show in OmniSharp/Neovim

**Common Causes:**

1. **RoslynExtensionsOptions:EnableAnalyzersSupport = false**
   - Default in some configs
   - OmniSharp silently skips analyzer diagnostics
   - **Solution:** Set to true in omnisharp.json or command line

2. **AnalyzeOpenDocumentsOnly = true**
   - Only analyzes currently open files
   - May not fully load project solution
   - **Solution:** Set to false for complete analysis

3. **Project not properly loaded**
   - .csproj not parsed
   - NuGet packages not restored
   - **Solution:** Run `dotnet restore` before opening in editor

4. **StyleCop.Analyzers not in project**
   - Package referenced but not installed
   - **Solution:** Add to .csproj or install via NuGet

5. **Analyzer suppressed in EditorConfig**
   - Rule severity set to `none` or `silent`
   - **Solution:** Check .editorconfig for `dotnet_diagnostic.SAxxxx.severity`

### Verification Steps

1. **Check process command line:**
   ```bash
   ps aux | grep omnisharp
   # Should include: RoslynExtensionsOptions:EnableAnalyzersSupport=true
   ```

2. **Check LSP diagnostics in editor:**
   ```vim
   :LspInfo  " Should show RoslynExtensionsOptions in config
   ```

3. **Check editor configuration:**
   ```bash
   grep -r "RoslynExtensionsOptions" ~/.omnisharp/ ~/.config/nvim/
   ```

4. **Manual analyzer test:**
   ```bash
   dotnet build --no-restore /p:EnableNETAnalyzers=true
   # Should show SA11xx warnings in output
   ```

---

## Part 11: Resources and References

### Official Documentation
- **Roslyn Compiler Platform**: https://github.com/dotnet/roslyn
- **Roslyn SDK**: https://github.com/dotnet/roslyn-sdk
- **Microsoft Learn - Roslyn Analyzers**: https://learn.microsoft.com/dotnet/csharp/roslyn-sdk/
- **StyleCop.Analyzers**: https://github.com/StyleCop/StyleCop.Analyzers
- **OmniSharp**: https://github.com/OmniSharp/omnisharp-roslyn

### Key Documentation Files
- **Analyzer Actions Semantics.md** - Action execution model
- **Analyzer Samples.md** - Implementation examples
- **DiagnosticSuppressorDesign.md** - Suppression mechanism
- **FixAllProvider.md** - Batch fix implementation

### Learning Path
1. Understand syntax trees (Roslyn syntax analysis)
2. Learn semantic analysis (symbol and type information)
3. Study sample analyzers (stateless, stateful, compilation-wide)
4. Review diagnostic descriptors and severity levels
5. Explore code fixer and code action integration
6. Configure analyzers via EditorConfig, ruleset, omnisharp.json

---

## Conclusion

Roslyn analyzers are a sophisticated, well-designed system for static code analysis in the .NET ecosystem. They work through:

1. **Automatic discovery** via reflection from NuGet packages
2. **Action registration** during analyzer initialization
3. **AST/semantic traversal** calling registered actions
4. **Diagnostic reporting** with structured information
5. **Configuration** via multiple mechanisms (EditorConfig, ruleset, omnisharp.json)
6. **IDE/LSP integration** sending diagnostics via standard protocols

Third-party analyzers like StyleCop integrate seamlessly into this system. Enabling them in LSP servers like OmniSharp requires setting `RoslynExtensionsOptions:EnableAnalyzersSupport=true` and ensuring analyzer packages are referenced in the project.

The system is designed for extensibility, performance (concurrent execution), and maintainability (declarative action registration with guaranteed execution order).
