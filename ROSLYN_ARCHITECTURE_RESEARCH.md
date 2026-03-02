# Roslyn GitHub Repository Research - Complete Summary

**Research Date**: 2025-11-13
**Repository**: https://github.com/dotnet/roslyn
**License**: MIT
**Governance**: .NET Foundation Project

---

## Executive Summary

Roslyn is Microsoft's open-source implementation of the C# and Visual Basic compilers with comprehensive APIs for building code analysis tools. It powers Visual Studio's IDE features, the .NET compiler toolchain, and third-party tools like OmniSharp. The architecture separates compiler internals from language services, enabling reusability across different development environments.

---

## What is Roslyn? (Purpose and Scope)

### Official Definition
"The open-source implementation of both the C# and Visual Basic compilers with an API surface for building code analysis tools."

### Core Purpose
Roslyn provides **programmatic access to compiler internals**, enabling developers to build sophisticated code analysis, refactoring, diagnostic, and transformation tools using the same infrastructure that powers the official compilers.

### Scope
The project encompasses:

1. **Language Compilers**
   - Full C# compiler implementation with all language features
   - Complete Visual Basic compiler implementation
   - Support for multiple .NET Framework versions and .NET Core

2. **Analysis APIs**
   - Syntax tree analysis and manipulation
   - Semantic analysis and symbol resolution
   - Diagnostic and analyzer frameworks
   - Code generation and transformation

3. **IDE Integration**
   - Language Server Protocol (LSP) implementation
   - Workspace APIs for IDE integration
   - Editor features (IntelliSense, code completion, etc.)
   - Visual Studio integration

4. **Developer Tools**
   - Interactive scripting capabilities
   - Expression evaluation (debugger support)
   - Code style analysis and enforcement
   - Build and deployment integrations

### Platform Support
- **Operating Systems**: Windows, macOS, Linux
- **Architectures**: x86, x64, ARM64
- **Runtimes**: .NET Framework, .NET Core, .NET 5+
- **Distribution**: Pre-release builds via public NuGet feeds

---

## Major Components and Their Roles

### 1. Compiler Components (`src/Compilers/`)

#### Core Infrastructure (`Core/`)
- **Shared utilities and base classes** for both C# and VB compilers
- **Common compilation pipeline** orchestration
- **Diagnostic reporting** infrastructure
- **Symbol and type system** foundations

#### C# Compiler (`CSharp/`)
A complete C# compiler implementation with these subsystems:

| Component | Role |
|-----------|------|
| **Parser** | Converts C# source code into syntax trees |
| **Syntax** | Defines language syntax nodes and tree structures |
| **Binder** | Performs semantic analysis and symbol binding |
| **Symbols** | Manages type, method, and member symbol definitions |
| **BoundTree** | Represents bound semantic tree (post-binding) |
| **Operations** | Represents semantic operations and expressions |
| **FlowAnalysis** | Analyzes control flow and data flow |
| **Lowering** | Transforms syntax/semantic trees to lower-level IL |
| **CodeGen** | Generates intermediate language (IL) code |
| **Emitter** | Produces final assembly output (PE files) |
| **Errors** | Manages diagnostics and error reporting |

#### Visual Basic Compiler (`VisualBasic/`)
- Complete VB.NET compiler with parallel structure to C# compiler
- Equivalent subsystems for parsing, binding, code generation

#### Compiler Server (`Server/`)
- **Compiler server process** (csc.exe wrapper)
- **In-process caching** for faster incremental compilation
- **Performance optimization** for repeated compilations

#### Extensions (`Extension/`)
- Extensibility points for analyzer integration
- Custom diagnostic providers
- Code fix providers

---

### 2. Language Server Protocol (LSP) Components (`src/LanguageServer/`)

The Roslyn LSP implementation is built as a reusable, extensible system:

#### Core Components

| Component | Purpose |
|-----------|---------|
| **Microsoft.CodeAnalysis.LanguageServer** | Main Roslyn LSP server implementation |
| **Microsoft.CommonLanguageServerProtocol.Framework** | Reusable LSP framework for any .NET language |
| **Protocol/** | LSP protocol definitions and specifications |
| **ExternalAccess/** | External API access layer for third-party tools |

#### LSP Features Supported
- **Diagnostics**: Real-time error and warning reporting
- **Completions**: IntelliSense and code completion
- **Definitions**: Go-to-definition navigation
- **References**: Find all references
- **Hover**: Hover documentation
- **Formatting**: Document and range formatting
- **Refactoring**: Code actions and refactorings
- **Workspace Symbols**: Project-wide symbol search
- **Semantic Highlighting**: Advanced syntax highlighting

---

### 3. Analyzer Framework (`src/Analyzers/`)

#### Analyzer Categories

**C# Analyzers** (`CSharp/`)
- Language feature analyzers
- Code style enforcement
- Performance recommendations
- Portability checks

**Visual Basic Analyzers** (`VisualBasic/`)
- Equivalent VB-specific analyzers
- Style and naming convention enforcement

**Core Analyzers** (`Core/`)
- Shared analyzer infrastructure
- Common patterns and utilities
- Cross-language capabilities

#### Analyzer Patterns

Roslyn supports three analyzer implementation patterns:

1. **Stateless Analyzers**
   - Report diagnostics independently
   - No state maintenance across actions
   - Examples: symbol analyzers, syntax node analyzers
   - Simplest and most common pattern

2. **Stateful Analyzers**
   - Maintain state across multiple actions
   - Access to immutable state objects
   - Mutable state initialized in start actions
   - Examples: compilation-wide analysis, cross-file patterns

3. **Additional File Analyzers**
   - Read data from supplementary project files
   - Support for line-by-line processing
   - XML and structured document parsing
   - Examples: configuration validation, resource analyzers

---

### 4. Workspace and IDE Services (`src/Workspaces/`, `src/Features/`, `src/EditorFeatures/`)

#### Workspaces (`src/Workspaces/`)
- **Project/Solution model** for IDE integration
- **Document management** and editing APIs
- **Refactoring infrastructure**
- **Code fix providers**
- **Rename tracking** and safety

#### Features (`src/Features/`)
- **Core language features** (both C# and VB)
- **Code completion** and IntelliSense
- **Quick fixes** and code actions
- **Refactoring implementations**
- **Navigation features**

#### Editor Features (`src/EditorFeatures/`)
- **Text editor integration**
- **Visual Studio integration**
- **Code classification** (syntax coloring)
- **Outlining** and code folding
- **Brace matching** and highlighting

---

### 5. Supporting Components

#### Code Style and Analysis (`src/CodeStyle/`)
- Style rule definitions
- EditorConfig integration
- Naming convention enforcement
- Code quality analyzers

#### RoslynAnalyzers (`src/RoslynAnalyzers/`)
- Analyzers specifically for Roslyn's own codebase
- Development-oriented diagnostics

#### ExpressionEvaluator (`src/ExpressionEvaluator/`)
- Debugger expression evaluation
- Watch window support
- Breakpoint condition evaluation

#### Interactive / Scripting (`src/Interactive/`, `src/Scripting/`)
- REPL (Read-Eval-Print Loop) support
- C# scripting API
- Dynamic code execution

#### Visual Studio Integration (`src/VisualStudio/`)
- VS-specific UI implementations
- Package management integration
- Project system extensions

---

## How Roslyn Relates to C# Compilation and Language Services

### Compilation Pipeline

```
Source Code (.cs files)
    ↓
Parser → Syntax Tree
    ↓
Binder → Symbols + Bound Tree (Semantic Analysis)
    ↓
FlowAnalysis → Control/Data Flow Information
    ↓
Lowering → IL-compatible Representation
    ↓
CodeGen → Intermediate Language (IL)
    ↓
Emitter → Assembly (.exe/.dll)
```

### Analyzer Integration in Pipeline

```
Compilation Phase:
├─ Compilation Start → All Start Actions Execute
├─ Symbol Walking → Symbol Actions
├─ Syntax/Operation Walking → Syntax/Operation Actions
└─ Compilation End → All End Actions Execute

Each analyzer action:
- Receives immutable compilation state
- Reports diagnostics via context
- No side effects on compilation
- Can run concurrently (if EnableConcurrentExecution=true)
```

### Key Design Principles

1. **Immutability**: Compilation snapshots are immutable
2. **Incremental**: Roslyn caches results for fast re-compilation
3. **Extensibility**: Analyzers can extend without modifying compiler
4. **Concurrency**: Analyzers can run in parallel safely
5. **IDE-Friendly**: Supports interactive, non-blocking analysis

---

## Repository Structure and Key Directories

### Top-Level Organization

```
dotnet/roslyn/
├── .devcontainer/          # Containerized development environment
├── .github/                # GitHub workflows and CI/CD
├── .vscode/                # VS Code workspace configuration
├── docs/                   # Documentation (detailed below)
├── eng/                    # Build and engineering infrastructure
├── scripts/                # Utility scripts for development
├── src/                    # PRIMARY SOURCE CODE
└── build.*                 # Build scripts (Windows/Unix)
```

### Source Code (`src/`) - Main Components

```
src/
├── Compilers/              # ★ Core compiler implementations
│   ├── Core/               # Shared compiler infrastructure
│   ├── CSharp/             # C# compiler
│   ├── VisualBasic/        # VB.NET compiler
│   ├── Server/             # Compiler server (csc.exe)
│   ├── Extension/          # Compiler extensions
│   └── Shared/             # Shared utilities
├── LanguageServer/         # ★ LSP implementation
│   ├── Protocol/           # LSP protocol definitions
│   ├── Microsoft.CodeAnalysis.LanguageServer/
│   ├── Microsoft.CommonLanguageServerProtocol.Framework/
│   └── ExternalAccess/     # Third-party integration
├── Analyzers/              # ★ Diagnostic analyzers
│   ├── CSharp/             # C# analyzers
│   ├── VisualBasic/        # VB analyzers
│   └── Core/               # Shared analyzer logic
├── CodeStyle/              # Code style enforcement
├── Features/               # IDE feature implementations
├── Workspaces/             # Project/solution model APIs
├── EditorFeatures/         # Text editor integration
├── ExpressionEvaluator/    # Debugger support
├── Interactive/            # REPL and scripting
├── VisualStudio/           # VS integration
├── Tools/                  # Development utilities
└── Dependencies/           # External dependencies
```

### Documentation (`docs/`)

#### Main Docs
- **README.md** - Placeholder (see GitHub homepage for main info)
- **Breaking API Changes.md** - Backward compatibility notes
- **Language Feature Status.md** - Feature implementation tracking
- **area-owners.md** - Component maintainers

#### Subdirectories
- **compilers/** - Compiler architecture and design
- **analyzers/** - Analyzer implementation guide
- **contributing/** - Contribution guidelines
- **features/** - Language and IDE features
- **ide/** - IDE integration documentation
- **infrastructure/** - Build and CI/CD setup
- **specs/** - Language specifications
- **wiki/** - Additional reference materials

#### Key Documentation Files

**Analyzers Documentation**
- `Analyzer Actions Semantics.md` - Action execution pipeline
- `Analyzer Samples.md` - Implementation examples
- `DiagnosticSuppressorDesign.md` - Diagnostic suppression patterns
- `FixAllProvider.md` - Batch fix implementations
- `Report Analyzer Format.md` - Performance reporting
- `Using Additional Files.md` - Non-source file integration

**Wiki Resources**
- Getting Started guides (C# and VB syntax/semantic analysis)
- Building, Testing, and Debugging guide
- Performance considerations for large solutions
- Custom Analyzer & Code Fix tutorials
- Syntax Visualizer documentation

---

## Analyzer Framework Details

### Action Execution Model

Analyzers register actions that execute at specific compilation phases:

#### Execution Order Guarantee
```
1. Compilation Start actions
   ↓
2. Symbol/Operation/Syntax actions (in user-defined order)
   ↓
3. Compilation End actions
```

#### Within Symbol Analysis
- Start actions → Member processing → End actions

#### Within Code Blocks
- Start actions → Node actions → End actions

### Concurrency Model

**Sequential by Default**: "No actions of a single analyzer execute concurrently"
- Ensures thread-safety without requiring locks
- Analyzers can opt-in with `EnableConcurrentExecution()`

**Cross-Analyzer Parallelism**: Different analyzers can run concurrently
- System schedules independent analyzers in parallel
- Increases performance on multi-core systems

### Host Flexibility

Hosts (IDE, build system) can:
- Delay action invocation arbitrarily
- Skip compilation end actions if compilation cancelled
- Cache results across compilations with equivalent effects
- Run analyzers incrementally on changed files only

---

## How Roslyn Integrates with LSP Servers (e.g., OmniSharp)

### Architecture Pattern

```
LSP Client (Editor/IDE)
    ↓ (via TCP/stdio)
LSP Server (Roslyn-based)
    ├─ Protocol Handler
    ├─ Roslyn Compilation Manager
    ├─ Analyzer Runner
    └─ Result Formatter
    ↓
Roslyn Compiler APIs
    ├─ Syntax Trees
    ├─ Semantic Analysis
    ├─ Analyzer Infrastructure
    └─ Diagnostic Reporting
```

### OmniSharp as an Example

**OmniSharp** wraps Roslyn to provide LSP support:

1. **Receives LSP requests** (e.g., textDocument/diagnostics)
2. **Translates to Roslyn API calls** (e.g., get diagnostics from compilation)
3. **Runs Roslyn analyzers** including:
   - RoslynExtensionsOptions (StyleCop, import completion, etc.)
   - Custom project analyzers (user-defined)
4. **Formats results** according to LSP protocol
5. **Sends LSP responses** back to client

### Key LSP Features Powered by Roslyn

| LSP Feature | Roslyn Component | Example Use |
|-------------|------------------|-------------|
| **textDocument/diagnostics** | Analyzer framework | StyleCop SA11xx warnings |
| **textDocument/definition** | Binder + Symbols | "Go to definition" |
| **textDocument/references** | Symbol references | "Find all references" |
| **textDocument/completion** | IntelliSense service | Code completion |
| **textDocument/hover** | Binder + Symbols | Hover documentation |
| **textDocument/codeAction** | Code fix providers | Quick fixes |
| **textDocument/formatting** | Formatter | Auto-formatting |

### RoslynExtensionsOptions Configuration

OmniSharp-specific Roslyn settings:

```csharp
RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,           // ← Run code analyzers
    EnableImportCompletion = true,           // ← Auto-complete using statements
    AnalyzeOpenDocumentsOnly = false,        // ← Analyze entire solution
}
```

These are **analyzer framework features** that OmniSharp exposes via LSP:
- `EnableAnalyzersSupport` → Enables analyzer execution pipeline
- `EnableImportCompletion` → Activates import-related analyzers
- `AnalyzeOpenDocumentsOnly` → Controls analyzer scope (perf option)

---

## Analyzer Support and StyleCop Integration

### How Analyzers Work (Complete Flow)

#### 1. Compilation and Analysis Phase
```csharp
var compilation = CSharpCompilation.Create("MyAssembly")
    .AddReferences(...)
    .AddSyntaxTrees(...);

// Analyzers registered here (by OmniSharp or build system)
var diagnostics = compilation.GetDiagnostics();
```

#### 2. Analyzer Action Registration
```csharp
public class MyAnalyzer : DiagnosticAnalyzer {
    public override void Initialize(AnalysisContext context) {
        context.RegisterSymbolAction(AnalyzeSymbol, SymbolKind.Method);
        context.RegisterSyntaxNodeAction(AnalyzeSyntax, SyntaxKind.MethodDeclaration);
    }
}
```

#### 3. Concurrent Execution (if enabled)
- Analyzer framework maintains work queue
- Each action is pushed into queue
- Workers execute actions concurrently
- Results aggregated safely

#### 4. Result Reporting
```csharp
private void AnalyzeSymbol(SymbolAnalysisContext context) {
    context.ReportDiagnostic(
        Diagnostic.Create(rule, location, messageArgs)
    );
}
```

### StyleCop Integration

**StyleCop.Analyzers** package uses this framework:

1. **Defines rules** (SA11xx, SA12xx, etc.)
2. **Implements analyzers** extending `DiagnosticAnalyzer`
3. **Registers actions** for different syntax nodes
4. **Reports violations** via context API

Example analyzers:
- **SA1100+**: Naming conventions
- **SA1200+**: Using statements and imports
- **SA1300+**: Property declarations
- **SA1400+**: Fields and members
- **SA1500+**: Braces and brackets

**When OmniSharp is configured** with `EnableAnalyzersSupport=true`:
1. OmniSharp loads project and its analyzers
2. Creates compilation with loaded assemblies
3. **Analyzer framework processes** StyleCop.Analyzers
4. All SA11xx rules execute
5. Violations reported as LSP diagnostics

### Analyzer Performance Reporting

Use `/reportanalyzer` compiler flag:

```bash
msbuild.exe /p:reportanalyzer=true /v:d MyProject.csproj
```

**Output shows:**
- Total analyzer execution time
- Individual analyzer execution times
- Percentage of total compilation time
- Helps identify performance bottlenecks

Example output:
```
Total analyzer execution time: 2.345 seconds.
Analyzer name                                    Time      % of total
StyleCop.Analyzers                               1.234     52.6%
Microsoft.CodeAnalysis.NetAnalyzers              0.876     37.3%
Custom.MyCompanyAnalyzers                        0.235     10.0%
```

---

## Key Takeaways for LSP and OmniSharp Integration

1. **Roslyn is the foundation** - OmniSharp wraps Roslyn APIs to provide LSP
2. **Analyzers are modular** - StyleCop and other analyzers plug into framework
3. **Immutable compilation model** - Makes concurrent analysis safe
4. **Three-tier action execution** - Start → Process → End
5. **LSP translates to Roslyn calls** - Every LSP request maps to compiler API
6. **Settings flatten to CLI args** - OmniSharp converts settings to command-line parameters
7. **Incremental analysis** - Roslyn caches results for performance

---

## Important Links

### Main Repository
- **GitHub**: https://github.com/dotnet/roslyn
- **License**: MIT
- **NuGet Packages**: https://www.nuget.org/packages/Microsoft.CodeAnalysis/

### Key Documentation Files
- **Analyzer Samples**: https://github.com/dotnet/roslyn-sdk
- **Contributing Guide**: https://github.com/dotnet/roslyn/blob/main/CONTRIBUTING.md
- **Building Guide**: https://github.com/dotnet/roslyn/wiki/Building,-Debugging,-and-Testing-on-Windows

### Related Projects
- **Roslyn Analyzers**: https://github.com/dotnet/roslyn-analyzers
- **StyleCop.Analyzers**: https://github.com/stylecop/StyleCopAnalyzers
- **OmniSharp**: https://github.com/OmniSharp/omnisharp-roslyn

### Community
- **GitHub Discussions**: https://github.com/dotnet/roslyn/discussions
- **Discord**: CSharp Community Discord channel

---

## Architecture Summary Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Roslyn Architecture                       │
└─────────────────────────────────────────────────────────────┘

IDE / Editor Client
        ↓
Language Server Protocol (LSP)
        ↓
┌─────────────────────────────────────────────────────────────┐
│              LSP Server (e.g., OmniSharp)                    │
├─────────────────────────────────────────────────────────────┤
│  Protocol Handler → Roslyn API Adapter → Result Formatter   │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│                 Roslyn Compiler Platform                     │
├─────────────────────────────────────────────────────────────┤
│ ┌───────────────┐   ┌──────────────┐   ┌───────────────┐   │
│ │ C# Compiler   │   │ VB Compiler  │   │ Language Svc  │   │
│ ├───────────────┤   ├──────────────┤   ├───────────────┤   │
│ │ • Parser      │   │ • Parser     │   │ • Workspaces  │   │
│ │ • Binder      │   │ • Binder     │   │ • Features    │   │
│ │ • Symbols     │   │ • Symbols    │   │ • Refactoring │   │
│ │ • CodeGen     │   │ • CodeGen    │   │ • Completion  │   │
│ └───────────────┘   └──────────────┘   └───────────────┘   │
│         ↓                   ↓                   ↓             │
│ ┌───────────────────────────────────────────────────────┐   │
│ │          Analyzer Framework                           │   │
│ ├───────────────────────────────────────────────────────┤   │
│ │ • Action Registration & Execution                     │   │
│ │ • Concurrent Worker Pool                             │   │
│ │ • Diagnostic Reporting                               │   │
│ │ • Code Fix Providers                                 │   │
│ └───────────────────────────────────────────────────────┘   │
│         ↓                                                    │
│ ┌───────────────────────────────────────────────────────┐   │
│ │    Diagnostic Analyzers (Pluggable)                   │   │
│ ├───────────────────────────────────────────────────────┤   │
│ │ • StyleCop.Analyzers (SA11xx rules)                  │   │
│ │ • NetAnalyzers (Microsoft.CodeAnalysis.NetAnalyzers) │   │
│ │ • Custom Project Analyzers                           │   │
│ │ • RoslynExtensionsOptions (OmniSharp-specific)       │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
        ↓
LSP Diagnostics (displayed in editor)
```

---

## Conclusion

Roslyn is a comprehensive, well-architected compiler platform that:

1. **Powers modern development** - Used by Visual Studio, .NET toolchain, and LSP servers
2. **Enables tool development** - Rich APIs for analyzers, code fixes, and refactorings
3. **Supports extensibility** - Modular analyzer framework for third-party tools
4. **Prioritizes performance** - Immutable compilation model with caching and incremental analysis
5. **Integrates with LSP** - Natural integration point for language servers like OmniSharp

For C# development in Neovim via OmniSharp, Roslyn provides the underlying engine that:
- Parses and analyzes code
- Runs StyleCop and other analyzers
- Provides code completion and navigation
- Enables refactoring and code fixes

Understanding Roslyn's architecture helps explain why configuring `RoslynExtensionsOptions` enables features like StyleCop analyzer warnings in LSP-based editors.
