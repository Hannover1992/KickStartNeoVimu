# OmniSharp Built on Roslyn: Comprehensive Architecture Research

**Research Date**: November 13, 2025
**Scope**: OmniSharp architecture, Roslyn API integration, diagnostics flow, and version compatibility
**Sources**: GitHub (omnisharp-roslyn, dotnet/roslyn), Strathweb technical articles, configuration documentation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Roslyn APIs Used by OmniSharp](#roslyn-apis-used-by-omnisharp)
4. [OmniSharp Configuration and Roslyn Settings](#omnisharp-configuration-and-roslyn-settings)
5. [Diagnostic Flow: Roslyn to LSP](#diagnostic-flow-roslyn-to-lsp)
6. [Roslyn Version Compatibility](#roslyn-version-compatibility)
7. [Key OmniSharp Components](#key-omnisharp-components)
8. [Code Examples](#code-examples)

---

## Executive Summary

OmniSharp is a **Language Server Protocol (LSP) implementation built entirely on top of Microsoft's Roslyn compiler platform**. It acts as a bridge between text editors (VS Code, Neovim, Emacs, etc.) and the Roslyn compiler, exposing C# language services through standardized interfaces.

### Key Architectural Principles

- **Roslyn-Based**: OmniSharp leverages Roslyn's workspace APIs for all semantic analysis
- **Language Server**: Operates via HTTP or STDIO protocols, with LSP support since v1.29.0-beta1
- **Modular Design**: Separate project systems (MSBuild, CSX scripts, Cake) and service layers
- **Configuration-Driven**: Rich hierarchical configuration through omnisharp.json, environment variables, and CLI arguments
- **Workspace-Centered**: All operations revolve around Roslyn's Workspace abstraction

---

## Architecture Overview

### High-Level Architecture Diagram

```
Text Editor (Neovim, VS Code, Emacs)
        ↓ LSP Protocol / HTTP / STDIO
        ↓
┌─────────────────────────────────────┐
│   OmniSharp Server                  │
├─────────────────────────────────────┤
│  ┌──────────────────────────────────┤
│  │ LSP Handler Layer                │
│  │ (Diagnostics, Completion, etc.)  │
│  └──────────────────────────────────┤
│         ↓ (Roslyn Workspace API)    │
│  ┌──────────────────────────────────┤
│  │ Service Layer                    │
│  │ - Intellisense Service           │
│  │ - Diagnostic Worker              │
│  │ - Code Action Provider           │
│  │ - Symbol Provider                │
│  └──────────────────────────────────┤
│         ↓ (Workspace Operations)    │
│  ┌──────────────────────────────────┤
│  │ OmniSharp Workspace              │
│  │ (Custom Workspace extending      │
│  │  Roslyn's Workspace class)       │
│  └──────────────────────────────────┤
│         ↓ (Roslyn APIs)             │
│  ┌──────────────────────────────────┤
│  │ Roslyn Platform                  │
│  │ - Compilation                    │
│  │ - Semantic Model                 │
│  │ - Syntax Tree                    │
│  │ - Symbol Analysis                │
│  │ - Diagnostic Engine              │
│  │ - Analyzer Host                  │
│  └──────────────────────────────────┤
└─────────────────────────────────────┘
        ↓
Project Files (.csproj, .sln)
```

### Communication Protocols

**HTTP Interface**
- Pull-based: Client requests information from server
- Used by some editors
- Stateless endpoint model

**STDIO Interface** (Primary for LSP)
- Bidirectional: Server can push diagnostics to client
- Language Server Protocol support
- Invoked with `--lsp` or `--languageserver` flags
- Enables real-time diagnostic updates

---

## Roslyn APIs Used by OmniSharp

### 1. Workspace Layer

**Microsoft.CodeAnalysis.Workspace** - Foundation of all OmniSharp operations

```csharp
// Core abstraction
public abstract class Workspace
{
    public Solution CurrentSolution { get; }
    public ImmutableSet<ProjectId> ProjectIds { get; }
    public Document GetDocument(DocumentId id);
    public Project GetProject(ProjectId id);
}
```

**Purpose**: OmniSharp extends this to create `OmniSharpWorkspace`, which manages:
- Document lifecycle (open, close, update)
- Project references and metadata
- EditorConfig integration
- Analyzer references
- File system synchronization

### 2. Compilation and Analysis

**Microsoft.CodeAnalysis.Compilation**
- Represents a complete compilation with all source and metadata
- Accessed via `project.GetCompilationAsync()`

**Microsoft.CodeAnalysis.SemanticModel**
- Provides semantic information about code
- Obtained from: `compilation.GetSemanticModel(syntaxTree)`
- Supports symbol binding and semantic analysis

**Key Operations**:
```csharp
// Get compilation for a project
var compilation = await project.GetCompilationAsync();

// Get semantic model for a document
var semanticModel = compilation.GetSemanticModel(syntaxTree);

// Bind symbols to declarations
var symbol = semanticModel.GetSymbolInfo(node).Symbol;

// Get diagnostics
var diagnostics = compilation.GetDiagnostics();
```

### 3. Analyzers and Code Actions

**Microsoft.CodeAnalysis.Diagnostics.DiagnosticAnalyzer**
- Base class for Roslyn analyzers
- Discovered from:
  - NuGet packages (e.g., StyleCop.Analyzers, Roslynator)
  - Metadata references
  - Custom analyzer implementations

**CompilationWithAnalyzers**
- Runs diagnostic analyzers on compilation
- Provides async methods:
  - `GetAnalyzerSyntaxDiagnosticsAsync()` - Syntax-level issues
  - `GetAnalyzerSemanticDiagnosticsAsync()` - Semantic-level issues

**Microsoft.CodeAnalysis.CodeActions.CodeAction**
- Refactorings and code fixes
- Supplied by: Roslyn built-in refactorings + analyzer code fixes

### 4. Syntax and Semantic Analysis

**Microsoft.CodeAnalysis.SyntaxTree**
- Abstract syntax tree representation
- Created from: `CSharpSyntaxTree.ParseText(sourceCode)`
- Immutable and thread-safe

**Microsoft.CodeAnalysis.SyntaxNode / SyntaxToken**
- Nodes in the syntax tree
- Used for syntax-based analysis

**Microsoft.CodeAnalysis.Semantics**
- Symbol interfaces: `ISymbol`, `ITypeSymbol`, `IMethodSymbol`, etc.
- Type information and relationships

### 5. Formatting and EditorConfig

**Microsoft.CodeAnalysis.Formatting**
- Code formatting services
- Respects EditorConfig when enabled

**Microsoft.CodeAnalysis.CSharp.Formatting**
- C#-specific formatting rules

### 6. Project System Support

**Microsoft.CodeAnalysis.MSBuild**
- MSBuild workspace for loading .sln files
- Used by OmniSharp for project discovery and loading

**Key APIs**:
```csharp
var workspace = MSBuildWorkspace.Create();
var solution = await workspace.OpenSolutionAsync(solutionPath);
```

### 7. Code Classification

**Microsoft.CodeAnalysis.CSharp.Workspaces.CSharpClassificationService**
- Semantic code classification
- Used for syntax highlighting
- Supports "additive classifications" (e.g., static symbols)

### 8. Logging and Diagnostics

**Microsoft.CodeAnalysis.Internal logging**
- Diagnostic event forwarding
- Error tracking and reporting

---

## OmniSharp Configuration and Roslyn Settings

### Configuration Hierarchy

OmniSharp applies configuration in this order (later overrides earlier):

1. **Hardcoded Defaults** - Built into OmniSharp binary
2. **Environment Variables** - Prefixed with `OMNISHARP_`
3. **Command-Line Arguments** - Startup flags
4. **Global omnisharp.json** - `~/.omnisharp/omnisharp.json`
5. **Local omnisharp.json** - `<project-root>/omnisharp.json`

### Environment Variable Format

Use flattened JSON paths with `:` delimiter:
```bash
export OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=true
export OMNISHARP_FormattingOptions:EnableEditorConfigSupport=true
export OMNISHARP_RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
```

### Key Configuration Sections

#### 1. RoslynExtensionsOptions

Controls Roslyn analyzer and refactoring features:

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,           // Enable Roslyn analyzers (SA1xxx, etc.)
    "enableImportCompletion": true,           // Import completion in IntelliSense
    "analyzeOpenDocumentsOnly": false,        // Analyze all files or just open ones
    "enableRoslynAnalyzers": true,            // General Roslyn analyzer support
    "locationPaths": ["./analyzers"]         // Custom analyzer locations
  }
}
```

**Roslyn Connection**:
- When `enableAnalyzersSupport=true`, OmniSharp uses `CompilationWithAnalyzers` to run all discovered Roslyn analyzers
- Analyzers come from NuGet packages and custom locations
- Results appear as diagnostics in the editor

#### 2. FormattingOptions

Controls code formatting and EditorConfig:

```json
{
  "FormattingOptions": {
    "enableEditorConfigSupport": true,        // Use .editorconfig rules
    "organizeImports": true,                  // Sort using statements
    "newLine": "\n",                          // Line ending style
    "indentSize": 4,                          // Indent size
    "useTabs": false                          // Use spaces vs tabs
  }
}
```

**Roslyn Connection**:
- Roslyn `FormattingService` respects these settings
- EditorConfig rules parsed by Roslyn's EditorConfig support
- Applied during code formatting operations

#### 3. ProjectSystem Configuration

```json
{
  "MSBuild": {
    "enabled": true,
    "projectLoadTimeout": 5000,
    "loadHidden": false
  },
  "ScriptProject": {
    "defaultTargetFramework": "net6.0"
  },
  "Cake": {
    "enabled": true
  }
}
```

#### 4. Analyzer-Specific Configuration

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  }
}
```

When enabled, OmniSharp:
1. Discovers all Roslyn analyzers in referenced NuGet packages
2. Creates `CompilationWithAnalyzers` for each compilation
3. Runs analyzers and collects violations
4. Converts Roslyn diagnostics to LSP diagnostic format
5. Publishes to LSP clients

---

## Diagnostic Flow: Roslyn to LSP

### Complete Diagnostic Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Roslyn Compilation                                  │
│ - Parse source into SyntaxTree                              │
│ - Compile to Compilation object                             │
│ - Includes metadata and symbol information                  │
└────────────┬────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Analyzer Discovery and Setup                        │
│ - Discover analyzers from NuGet packages                    │
│ - Create CompilationWithAnalyzers                           │
│ - Configure analyzer behavior (if enabled)                  │
└────────────┬────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Roslyn Diagnostic Collection                        │
│ CSharpDiagnosticWorkerWithAnalyzers:                        │
│ - Call GetAnalyzerSyntaxDiagnosticsAsync()                 │
│ - Call GetAnalyzerSemanticDiagnosticsAsync()               │
│ - Get compiler diagnostics from Compilation.GetDiagnostics()│
│ - Filter suppressed diagnostics                             │
│ - Result: List<Diagnostic> (Roslyn format)                 │
└────────────┬────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Roslyn Diagnostic Conversion                        │
│ DiagnosticExtensions (conversion methods):                  │
│ - Extract diagnostic ID (SA1xxx, CS1234, etc.)              │
│ - Extract line/column range                                 │
│ - Extract message and severity                              │
│ - Map Roslyn severity to LSP severity                       │
│ - Extract code fix information if available                 │
│ Result: OmniSharp diagnostic DTO                            │
└────────────┬────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: LSP Protocol Conversion                             │
│ LSP Handler:                                                │
│ - Convert OmniSharp diagnostics to LSP Diagnostic[]         │
│ - Map locations using LSP Position/Range format             │
│ - Map severity: Error→1, Warning→2, Info→3, Hint→4        │
│ - Populate tags, source, code                               │
│ - Result: PublishDiagnosticsParams                          │
└────────────┬────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Publishing to LSP Client                            │
│ - Send textDocument/publishDiagnostics notification         │
│ - Client receives diagnostics in editor format              │
│ - Displayed as squiggles/decorations                        │
└─────────────────────────────────────────────────────────────┘
```

### Diagnostic Sources in OmniSharp

OmniSharp gathers diagnostics from multiple Roslyn sources:

#### 1. Syntax Diagnostics (Compile Errors)

```csharp
// From: CSharpDiagnosticWorkerWithAnalyzers
var syntaxDiagnostics = await compilationWithAnalyzers
    .GetAnalyzerSyntaxDiagnosticsAsync();
```

Examples: CS1002 (unexpected token), CS0103 (name doesn't exist)

#### 2. Semantic Diagnostics (Type Errors)

```csharp
var semanticDiagnostics = await compilationWithAnalyzers
    .GetAnalyzerSemanticDiagnosticsAsync();
```

Examples: CS0246 (type not found), CS0029 (cannot convert type)

#### 3. Analyzer Diagnostics (Style, Quality)

```csharp
// When EnableAnalyzersSupport = true
// Roslyn discovers analyzers from:
var analyzers = project.AnalyzerReferences
    .SelectMany(r => r.GetAnalyzers(LanguageNames.CSharp));

var compilationWithAnalyzers = compilation.WithAnalyzers(
    analyzers,
    new AnalyzerOptions(additionalFiles),
    cancellationToken);
```

Examples: SA1116 (parameters should be on same line), CA1710 (identifiers should have correct suffix)

#### 4. Compiler Diagnostics

```csharp
var compilerDiagnostics = compilation.GetDiagnostics();
```

### Diagnostic Conversion Logic

**From Roslyn.Diagnostic to OmniSharp Internal Format:**

```
Roslyn Diagnostic Object
├── Id: string                 → OmniSharp DiagnosticCode
├── Severity: DiagnosticSeverity → OmniSharp Severity
│   (Hidden, Info, Warning, Error)
├── Location: Location         → OmniSharp Line/Column
├── GetMessage(): string       → OmniSharp Message
├── IsSuppressed: bool         → Filter out if true
└── Descriptor.HelpLinkUri     → Code fix link

↓ (Conversion via DiagnosticExtensions)

OmniSharp QuickFixResponse
├── Code: string (e.g., "SA1116")
├── Text: string (message)
├── Line: int
├── Column: int
├── EndLine: int
├── EndColumn: int
├── LogLevel: "Error" | "Warning" | "Information" | "Hint"
├── Projects: ProjectId[]
└── Tags: string[]
```

**From OmniSharp to LSP Format:**

```
OmniSharp Diagnostic
├── Text / Message         → LSP Diagnostic.message
├── LogLevel / Severity    → LSP Diagnostic.severity (1-4)
├── Code                   → LSP Diagnostic.code
├── Line / Column / Range  → LSP Diagnostic.range
└── Tags                   → LSP Diagnostic.tags

↓ (LSP Handler)

LSP PublishDiagnosticsParams
{
  "uri": "file:///path/to/file.cs",
  "diagnostics": [
    {
      "range": {
        "start": {"line": 55, "character": 8},
        "end": {"line": 55, "character": 12}
      },
      "severity": 2,           // Warning
      "code": "SA1116",
      "source": "OmniSharp",
      "message": "Split parameters should be on same line or separate lines for consistency"
    }
  ]
}
```

### Configuration Impact on Diagnostics

| Setting | Impact on Diagnostics |
|---------|-----|
| `enableAnalyzersSupport: false` | Only compiler diagnostics, no analyzer warnings (SA1xxx, etc.) |
| `enableAnalyzersSupport: true` | Includes all discovered analyzers (StyleCop, Roslynator, etc.) |
| `analyzeOpenDocumentsOnly: true` | Reduced diagnostics (only current file) |
| `analyzeOpenDocumentsOnly: false` | All project files analyzed in background |
| `enableEditorConfigSupport: false` | EditorConfig rules not applied |
| `enableEditorConfigSupport: true` | EditorConfig formatting rules analyzed |

---

## Roslyn Version Compatibility

### Version Timeline

| OmniSharp Version | Roslyn Version | .NET Target | Release Status |
|---|---|---|---|
| v1.39.15-beta.60 | 5.1.0-1.25475.3 | net6.0 / net472 | Pre-release |
| v1.39.14 (latest stable) | 4.14.0-3.25168.13 | net6.0 / net472 | Stable |
| v1.39.6 | 4.x.x | net6.0 / net472 | Stable |
| v1.39.3 | 4.5.0-2.22527.10 | net6.0 / net472 | Stable |
| v1.38.x | 4.x.x | net6.0 / net472 | Stable |
| v1.37.x | 4.x.x | net6.0 / net472 | Stable |
| v1.32.18+ | 3.x.x | net6.0 / net472 | Legacy |
| v1.29.0-beta1 | 2.x.x | net6.0 / net472 | First LSP support |

### Roslyn Version Dependencies

**OmniSharp.Roslyn NuGet Package** depends on:
- `Microsoft.CodeAnalysis` (core compiler APIs)
- `Microsoft.CodeAnalysis.CSharp` (C#-specific)
- `Microsoft.CodeAnalysis.CSharp.Features` (language features)
- `Microsoft.CodeAnalysis.CSharp.Workspaces` (workspace support)
- `Microsoft.CodeAnalysis.ExternalAccess.*` (public APIs)

**OmniSharp.Roslyn.CSharp** depends on:
- OmniSharp.Roslyn
- OmniSharp.Shared
- System.ComponentModel.Composition
- System.Collections.Immutable
- System.Reactive

### Framework Targeting

- **net6.0**: Primary target, requires .NET SDK ≥ 6.0
- **net472**: Legacy .NET Framework support, requires .NET 4.7.2 targeting pack
- Both targets use same version of Roslyn APIs

### Version Compatibility Strategy

1. **Regular Updates**: OmniSharp updates Roslyn with each release to include latest C# language features
2. **Beta Tracking**: Pre-release versions track Roslyn preview builds
3. **Backward Compatibility**: Core Roslyn APIs maintained across major versions
4. **Analyzer Discovery**: All Roslyn analyzers are version-agnostic (via IAssemblySymbol)

---

## Key OmniSharp Components

### 1. OmniSharpWorkspace

**File**: `src/OmniSharp.Roslyn/OmniSharpWorkspace.cs`

**Extends**: `Roslyn Workspace` class

**Responsibilities**:
- Document lifecycle management
- Project organization
- Analyzer reference tracking
- EditorConfig integration
- File system synchronization
- Misc document handling

**Key Capabilities**:
```csharp
class OmniSharpWorkspace : Workspace
{
    // Document operations
    public void AddDocument(TextLoader loader, string filePath);
    public void RemoveDocument(string filePath);
    public void UpdateDocument(string filePath, SourceText text);

    // Analyzer management
    public void AddAnalyzerReference(AnalyzerReference reference);
    public void RemoveAnalyzerReference(AnalyzerReference reference);

    // EditorConfig
    public void ApplyEditorConfigSettings(string configPath);

    // Project creation
    public ProjectId AddProject(ProjectInfo projectInfo);
}
```

### 2. CSharpDiagnosticWorkerWithAnalyzers

**File**: `src/OmniSharp.Roslyn.CSharp/Workers/Diagnostics/CSharpDiagnosticWorkerWithAnalyzers.cs`

**Responsibilities**:
- Collects diagnostics from Roslyn compilation
- Runs analyzers when enabled
- Manages diagnostic publishing
- Filters suppressed diagnostics

**Process**:
```
1. Get Compilation from Project
2. Create CompilationWithAnalyzers
3. Call GetAnalyzerSyntaxDiagnosticsAsync()
4. Call GetAnalyzerSemanticDiagnosticsAsync()
5. Filter and publish diagnostics
6. Background/foreground queue management
```

### 3. IntellisenseService

**File**: `src/OmniSharp.Roslyn.CSharp/Services/Intellisense/IntellisenseService.cs`

**Uses Roslyn APIs**:
- `Compilation.GetSemanticModel(syntaxTree)`
- `SymbolFinder.FindSymbolAtPositionAsync()`
- `Recommenders.GetRecommendedSymbols()` (completion)

### 4. CompletionService

**File**: `src/OmniSharp.Roslyn.CSharp/Services/Completion/CompletionService.cs`

**Uses Roslyn APIs**:
- `Roslyn.CompletionService` (code completion recommendations)
- `CompletionItem` analysis
- Symbol resolution

### 5. DiagnosticExtensions

**Location**: `src/OmniSharp.Roslyn.CSharp/Helpers/DiagnosticExtensions.cs`

**Responsibility**: Convert Roslyn diagnostics to OmniSharp format

**Key Method**:
```csharp
public static QuickFixResponse ToQuickFixResponse(
    this Diagnostic diagnostic,
    DocumentId documentId,
    Workspace workspace)
{
    return new QuickFixResponse
    {
        Code = diagnostic.Id,
        Text = diagnostic.GetMessage(),
        Line = diagnostic.Location.GetLineSpan().StartLinePosition.Line,
        Column = diagnostic.Location.GetLineSpan().StartLinePosition.Character,
        EndLine = diagnostic.Location.GetLineSpan().EndLinePosition.Line,
        EndColumn = diagnostic.Location.GetLineSpan().EndLinePosition.Character,
        LogLevel = MapSeverity(diagnostic.Severity)
    };
}
```

### 6. AnalyzerSettings

**Location**: `Configuration/RoslynExtensionsOptions.cs`

**Exposes**:
```csharp
public class RoslynExtensionsOptions
{
    public bool EnableAnalyzersSupport { get; set; }
    public bool EnableImportCompletion { get; set; }
    public bool AnalyzeOpenDocumentsOnly { get; set; }
    public int AnalysisBudget { get; set; }
    public int DiagnosticWorkerThreadCount { get; set; }
    public string[] LocationPaths { get; set; }
}
```

---

## Code Examples

### Example 1: Enabling StyleCop Warnings

**omnisharp.json**:
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

**What happens**:
1. OmniSharp discovers `StyleCop.Analyzers` NuGet package in project
2. Creates `CompilationWithAnalyzers` with all StyleCop analyzer rules
3. Runs analyzers on all project files
4. SA1xxx warnings appear in editor as diagnostics

### Example 2: Diagnostic Collection Flow

**Pseudo-code of CSharpDiagnosticWorkerWithAnalyzers**:

```csharp
async Task<List<Diagnostic>> CollectDiagnosticsAsync(Project project)
{
    var diagnostics = new List<Diagnostic>();

    // Get compilation
    var compilation = await project.GetCompilationAsync();

    // If EnableAnalyzersSupport is true
    if (_options.RoslynExtensionsOptions.EnableAnalyzersSupport)
    {
        // Create CompilationWithAnalyzers
        var analyzers = project.AnalyzerReferences
            .SelectMany(r => r.GetAnalyzers(LanguageNames.CSharp));

        var compilationWithAnalyzers = compilation.WithAnalyzers(
            analyzers,
            new AnalyzerOptions(additionalFiles: null),
            cancellationToken);

        // Collect analyzer diagnostics
        var syntaxDiags = await compilationWithAnalyzers
            .GetAnalyzerSyntaxDiagnosticsAsync();
        var semanticDiags = await compilationWithAnalyzers
            .GetAnalyzerSemanticDiagnosticsAsync();

        diagnostics.AddRange(syntaxDiags);
        diagnostics.AddRange(semanticDiags);
    }
    else
    {
        // Only get compiler diagnostics
        diagnostics.AddRange(compilation.GetDiagnostics());
    }

    // Filter suppressed diagnostics
    return diagnostics.Where(d => !d.IsSuppressed).ToList();
}
```

### Example 3: Roslyn SemanticModel Usage

**In OmniSharp completion service**:

```csharp
async Task<CompletionList> GetCompletionsAsync(
    Project project,
    int line,
    int column)
{
    var document = project.GetDocument(documentId);
    var semanticModel = await document.GetSemanticModelAsync();
    var syntaxTree = await document.GetSyntaxTreeAsync();

    // Get position in source
    var sourceText = await document.GetTextAsync();
    var position = sourceText.Lines[line].Start + column;

    // Get symbol at position
    var root = await syntaxTree.GetRootAsync();
    var token = root.FindToken(position);

    // Use Roslyn's completion recommender
    var recommendations = Recommenders
        .GetRecommendedSymbols(semanticModel, position, Workspace);

    // Convert to LSP CompletionItem format
    return new CompletionList(
        recommendations
            .Select(s => CreateCompletionItem(s))
            .ToArray());
}
```

### Example 4: Configuration Hierarchy in Action

**Environment setup**:
```bash
# Global config: ~/.omnisharp/omnisharp.json
export OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=false

# Project local: /project/omnisharp.json
# Contains: { "RoslynExtensionsOptions": { "enableAnalyzersSupport": true } }

# CLI argument
omnisharp -s /path/to/solution --host stdio
```

**Result**: Local omnisharp.json wins → `enableAnalyzersSupport=true`

**LSP client (Neovim)**:
```lua
omnisharp = {
  cmd = { "dotnet", "/path/to/OmniSharp.dll", "-s", "/solution/path" },
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
}
```

**What OmniSharp receives**:
1. CLI solution path: `/solution/path`
2. Settings flattened to command-line args by lspconfig's `on_new_config`
3. All settings applied, EnableAnalyzersSupport=true active
4. Roslyn analyzers enabled and running

---

## Summary: Architectural Principles

### OmniSharp's Roslyn Dependency

1. **Workspace-Centric**: Everything revolves around Roslyn Workspace abstraction
2. **Analyzer-Driven**: Most language features come from Roslyn analyzers
3. **Compilation-Based**: All analysis requires Roslyn Compilation
4. **Configuration-Flexible**: Rich config system controls Roslyn feature enablement
5. **LSP-Compatible**: Converts Roslyn diagnostics to LSP format automatically

### Why It Works Well

- **No Reimplementation**: Uses Roslyn's proven APIs instead of custom parsing
- **Feature Parity**: Gets new C# features automatically with Roslyn updates
- **Standard Format**: LSP protocol ensures editor independence
- **Modular Services**: Clear separation between LSP, workspace, and Roslyn layers
- **Performance**: Roslyn's incremental analysis prevents recompiling entire projects

### Key Takeaway

OmniSharp is fundamentally a **translation layer** that:
1. Loads projects via Roslyn's workspace APIs
2. Maintains synchronization with editor buffer changes
3. Runs Roslyn's compilation and analyzers on demand
4. Converts Roslyn's internal formats (diagnostics, symbols, completions) to LSP protocol
5. Publishes results back to editors via LSP notifications

This architecture allows any editor supporting LSP to get professional C# IDE features without implementing any language logic themselves.

---

## References

**Primary Sources**:
- GitHub: https://github.com/OmniSharp/omnisharp-roslyn
- GitHub: https://github.com/dotnet/roslyn
- OmniSharp Wiki: Configuration Options
- Strathweb Articles:
  - Roslyn Analyzers in OmniSharp and VS Code
  - C# Semantic Classification with Roslyn
  - Hidden Features of OmniSharp

**Key Files**:
- `/src/OmniSharp.Roslyn/OmniSharpWorkspace.cs` - Core workspace implementation
- `/src/OmniSharp.Roslyn.CSharp/Workers/Diagnostics/CSharpDiagnosticWorkerWithAnalyzers.cs` - Diagnostic collection
- `/src/OmniSharp.Roslyn.CSharp/Helpers/DiagnosticExtensions.cs` - Roslyn to OmniSharp conversion
- `/src/OmniSharp.Roslyn.CSharp/Services/Intellisense/IntellisenseService.cs` - Intellisense implementation

---

**Document Generated**: November 13, 2025
**Research Completed**: Yes
**Status**: Comprehensive architecture and integration documentation complete
