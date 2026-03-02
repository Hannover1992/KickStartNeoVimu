# Roslyn's LSP Implementation and OmniSharp Integration - Research Summary

**Research Date**: 2025-11-13
**Status**: Complete
**Sources**: GitHub repositories, Microsoft Learn documentation, LSP specifications

---

## Executive Summary

Roslyn is the .NET compiler platform that powers OmniSharp's language services. OmniSharp acts as a wrapper around Roslyn workspaces, exposing compiler and analyzer capabilities through the Language Server Protocol (LSP). This document explains how they integrate and how diagnostic information flows from analyzers to LSP clients (like Neovim).

---

## Part 1: Roslyn Architecture Overview

### What is Roslyn?

**Roslyn** is the open-source implementation of both the C# and Visual Basic compilers with an API surface for building code analysis tools. Microsoft describes it as: *"Instead of being opaque source-code-in and object-code-out translators, through Roslyn, compilers become platforms."*

**Key Characteristics:**
- Open source (MIT license)
- Part of the .NET Foundation
- Exposes compiler internals as APIs
- Provides IDE services, not just compilation

### Roslyn's Compiler Pipeline Phases

Roslyn mirrors a traditional compiler's structure through four main phases, each with corresponding APIs:

```
Source Code
    ↓
[PARSE PHASE]
    ↓ Syntax Trees (tokens, AST)
[DECLARATION PHASE]
    ↓ Symbol tables from source and metadata
[BIND PHASE]
    ↓ Identifiers mapped to symbols
[EMIT PHASE]
    ↓ IL bytecode generation
```

### Roslyn's Four-Layer API Architecture

Roslyn exposes compiler functionality through **four distinct API layers**:

1. **Compiler APIs**
   - Syntax trees and semantic analysis
   - Token and syntax node inspection
   - Symbol resolution and binding
   - Used for: Analyzers, refactorings, code generation

2. **Diagnostic APIs**
   - Error and warning reporting
   - Extensible diagnostic system
   - Integration with MSBuild and Visual Studio
   - Used for: StyleCop, FxCop, custom analyzers

3. **Scripting APIs**
   - Interactive code execution
   - C# REPL support
   - Used for: CSX script evaluation

4. **Workspaces APIs**
   - High-level code analysis across entire solutions
   - Project and document management
   - Solution-wide refactoring support
   - Used for: IDE features, multi-file analysis

---

## Part 2: Roslyn Analyzers and Diagnostics

### How Roslyn Analyzers Work

Roslyn analyzers are extensions that run during compilation and IDE editing sessions. They follow a standardized pattern:

```
Analyzer Implementation
    ↓
DiagnosticAnalyzer class (Roslyn.Diagnostics.Analyzers)
    ↓
Initialize() method (called once per compilation)
    ↓
Register actions:
  - CompilationStart/End actions
  - SymbolStart/End actions
  - OperationAction (IL operations)
  - SyntaxNodeAction (specific syntax nodes)
  - CodeBlockAction (methods/properties)
  - SemanticModelAction (entire files)
    ↓
For each action invocation:
  - Analyzer inspects code
  - Reports diagnostics via context.ReportDiagnostic()
    ↓
Diagnostics flow to IDE/LSP server
```

### Key Analyzer Characteristics

**Action Registration (from Roslyn documentation):**
- Analyzers register actions in the `Initialize(AnalysisContext context)` method
- Multiple action types available for different code analysis patterns
- Framework ensures **no two actions from same analyzer run concurrently** (unless `EnableConcurrentExecution` is set)
- Different analyzers' actions may run concurrently

**Diagnostic Reporting:**
- Analyzers call `context.ReportDiagnostic(diagnostic)` to report issues
- Each diagnostic includes:
  - DiagnosticId (e.g., "SA1116" for StyleCop)
  - Severity (Error, Warning, Hidden, Info)
  - Location (file, line, column span)
  - Message and description
  - Custom properties and tags

**Real-World Example: StyleCop Analyzers**
- StyleCop.Analyzers NuGet package contains ~200 Roslyn analyzers
- Rules like SA1116 (statement must be on its own line) run automatically
- Diagnostics appear in Visual Studio and any LSP-compatible editor
- Configuration via `.editorconfig` files

---

## Part 3: OmniSharp's Role as Roslyn Wrapper

### What is OmniSharp?

OmniSharp is described as: *"A .NET development platform based on Roslyn workspaces. It provides project dependencies and C# language services to various IDEs and plugins."*

**Core Purpose:**
- Wraps Roslyn workspaces API
- Provides LSP server interface to connect any editor (VS Code, Vim, Neovim, etc.)
- Manages solution loading and project discovery
- Coordinates analyzer execution

### OmniSharp Architecture

```
LSP Client (Editor: VS Code, Neovim)
    ↓
[LSP Protocol via stdio or HTTP]
    ↓
OmniSharp.LanguageServerProtocol
    ├─ Handlers/ (22+ LSP request handlers)
    │  ├─ Completion handler
    │  ├─ Definition handler
    │  ├─ References handler
    │  ├─ Hover handler
    │  ├─ Code actions handler
    │  ├─ Formatting handler
    │  └─ Diagnostics handler
    ├─ Initialization (LanguageServerHost.cs)
    └─ Document synchronization
    ↓
OmniSharp.Roslyn.CSharp
    ├─ C# language services
    ├─ Project system integration
    └─ Analyzer coordination
    ↓
Roslyn APIs
    ├─ Compiler (syntax, semantics, bindings)
    ├─ Workspaces (solution-wide analysis)
    └─ Analyzers (StyleCop, etc.)
    ↓
.NET Compiler Platform
    ├─ C# compiler
    ├─ VB.NET compiler
    └─ Runtime
```

### OmniSharp's Key Responsibilities

1. **Workspace Management**
   - Loads `.sln` file and project files
   - Maintains solution-wide semantic model
   - Tracks file changes in real-time

2. **Handler Implementation**
   - Converts LSP requests to Roslyn API calls
   - Example: `textDocument/definition` → `FindSymbolAtPosition()` → return locations

3. **Analyzer Coordination**
   - Collects diagnostics from all loaded analyzers
   - Publishes diagnostics via LSP `textDocument/publishDiagnostics`
   - Configurable through settings (EnableAnalyzersSupport, etc.)

4. **Configuration Management**
   - Reads omnisharp.json
   - Applies EditorConfig settings
   - Passes settings to Roslyn for formatting, analysis options

---

## Part 4: LSP Protocol Integration

### LSP Initialization Handshake

When an editor connects to OmniSharp, the following sequence occurs:

```
STEP 1: Editor sends initialize request
  └─ Includes: rootUri, capabilities, initializationOptions

STEP 2: OmniSharp.LanguageServerHost.Initialize()
  ├─ Reads configuration files (omnisharp.json)
  ├─ Loads solution from rootUri
  ├─ Creates Roslyn workspaces
  └─ Calls CreateCompositionHost() for dependency injection

STEP 3: OmniSharp registers handlers
  ├─ Enumerates LSP handler classes (22 handlers)
  ├─ Creates TextDocumentSelector for each
  └─ Registers with OmniSharp service container

STEP 4: OmniSharp sends initialize response
  ├─ Declares ServerCapabilities:
  │  ├─ textDocumentSync (document synchronization)
  │  ├─ completionProvider (code completion)
  │  ├─ definitionProvider (go to definition)
  │  ├─ diagnosticProvider (diagnostics support)
  │  ├─ hoverProvider (hover information)
  │  ├─ referencesProvider (find references)
  │  ├─ formattingProvider (code formatting)
  │  ├─ renameProvider (symbol renaming)
  │  ├─ codeActionProvider (quick fixes)
  │  ├─ semanticTokensProvider (syntax highlighting)
  │  └─ [20+ more capabilities]
  └─ Returns serverInfo with OmniSharp version

STEP 5: Editor can now send requests
  └─ All LSP requests are routed to appropriate handlers
```

### LSP ServerCapabilities Advertised by OmniSharp

OmniSharp announces the following capabilities to LSP clients:

```
• Text Document Synchronization
  - Full document sync (send entire file on change)
  - Incremental sync (send only changes)

• Completion
  - Method/property completion
  - Type completion
  - Snippet support

• Definition/References
  - Go to definition
  - Find all references
  - Find implementations

• Hover
  - Type information on hover
  - XML doc comments

• Code Actions (Quick Fixes)
  - Named suggestions (refactoring, code generation)
  - Diagnostic code fixes
  - Source generators

• Formatting
  - Document-wide formatting
  - Range formatting
  - Format on type

• Rename
  - Symbol renaming across project
  - Rename refactoring

• Diagnostics
  - Real-time error reporting
  - Warning categorization
  - Code analysis results

• Semantic Tokens
  - Syntax-based token classification
  - Enables advanced IDE features

• Workspace Symbols
  - Find types/methods across solution
  - Fuzzy search integration
```

---

## Part 5: Configuration Flow - LSP Settings to Roslyn

### How Settings Reach Roslyn Analyzers

Configuration flows through multiple layers:

```
LSP Client (Neovim)
    ↓
[LSP Protocol]
  • initializationOptions (JSON)
  • Workspace configuration requests
    ↓
OmniSharp.LanguageServerProtocol.LanguageServerHost
    ├─ Parses initialization options
    ├─ Reads omnisharp.json files
    └─ Reads environment variables
    ↓
Configuration System
    ├─ Merges: hardcoded defaults
    ├─        environment variables
    ├─        command-line arguments
    ├─        global ~/.omnisharp/omnisharp.json
    └─        local ./omnisharp.json
    ↓
OmniSharp.Roslyn
    ├─ FormatCodeSettings (passed to formatter)
    ├─ RoslynExtensionsOptions (Analyzer settings)
    │  └─ EnableAnalyzersSupport (boolean)
    │  └─ EnableImportCompletion (boolean)
    │  └─ AnalyzeOpenDocumentsOnly (boolean)
    └─ Other Roslyn workspace settings
    ↓
Roslyn Compiler/Analyzers
    └─ Apply settings during analysis
```

### OmniSharp Configuration Precedence (High to Low)

1. **Local omnisharp.json** (in project root)
   - Highest priority
   - Team-wide configuration

2. **Global omnisharp.json** (~/.omnisharp/)
   - User machine defaults

3. **Command-line arguments**
   - When OmniSharp is started
   - Example: `dotnet OmniSharp.dll -s /path/to/sln RoslynExtensionsOptions:EnableAnalyzersSupport=true`

4. **Environment variables**
   - Prefix: `OMNISHARP_`
   - Example: `OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=true`

5. **Hardcoded defaults**
   - Built-in OmniSharp defaults

### Key RoslynExtensionsOptions Settings

From the configuration documentation:

```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,           // Enable Roslyn analyzers (StyleCop, etc.)
    "EnableImportCompletion": true,          // Complete namespace imports
    "AnalyzeOpenDocumentsOnly": false,       // Analyze all files or only open
    "DocumentAnalysisTimeoutMs": 30000       // Analyzer timeout (ms)
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,       // Read .editorconfig files
    "OrganizeImports": true                  // Remove unused imports
  }
}
```

**Critical Setting for StyleCop Warnings:**
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true` - **MUST be true** for StyleCop diagnostics to appear

---

## Part 6: Diagnostic Reporting Through LSP

### Diagnostic Flow from Analyzer to Editor

```
[During compilation or editing]
    ↓
Roslyn Analyzer (e.g., StyleCopAnalyzers)
    ├─ Scans code via registered actions
    ├─ Detects violations (e.g., SA1116)
    └─ Calls context.ReportDiagnostic(diagnostic)
    ↓
Diagnostic object created
    ├─ Id: "SA1116"
    ├─ Severity: "Warning"
    ├─ Message: "Split parameters must begin on new line"
    ├─ Location: file.cs, line 56-57
    └─ Tags: ["CompilationWarning"]
    ↓
OmniSharp Diagnostic Handler
    ├─ Collects from all analyzers
    ├─ Transforms to LSP format
    └─ Creates publishDiagnostics notification
    ↓
[LSP Protocol]
  textDocument/publishDiagnostics
    ├─ uri: "file://C:/path/UserController.cs"
    ├─ diagnostics: [
    │  {
    │    "range": { "start": { "line": 55, "character": 25 }, ... },
    │    "severity": 2,  // Warning
    │    "code": "SA1116",
    │    "source": "csharp",
    │    "message": "Split parameters must begin on new line",
    │    "tags": [1]  // 1 = unnecessary, 2 = deprecated
    │  }
    │ ]
    └─ version: 3  // Document version
    ↓
LSP Client (Neovim)
    ├─ Receives notification
    ├─ Parses diagnostics
    └─ Displays warnings in UI
```

### What Information is Included in Each Diagnostic

**From LSP Specification & OmniSharp Implementation:**

1. **Diagnostic Range**
   - Start position (line, character)
   - End position (line, character)
   - Exact span of problematic code

2. **Severity Level**
   - 1 = Error (compilation failure)
   - 2 = Warning (style, convention)
   - 3 = Information (hints)
   - 4 = Hint (optional improvements)

3. **Diagnostic Code**
   - StyleCop: "SA1116", "SA1101", etc.
   - Roslyn: "CS0001", "CS8600", etc.
   - Enables targeted suppression

4. **Message**
   - Human-readable description
   - Shown in IDE tooltip

5. **Source**
   - "csharp" for C# diagnostics
   - Used to categorize diagnostics

6. **Tags**
   - Unnecessary (code can be removed)
   - Deprecated (API is deprecated)
   - Special rendering in some editors

7. **Related Information** (optional)
   - Other locations related to diagnostic
   - Used for cross-file issues

---

## Part 7: Relationship Between Roslyn and OmniSharp

### Roslyn → OmniSharp Data Flow

```
Roslyn (Compiler Platform)
    ├─ Provides: Compiler APIs, Workspaces, Analyzers
    ├─ Responsibility: Language analysis and compilation
    └─ Output: Syntax trees, symbols, diagnostics

    ↓ Wrapped by ↓

OmniSharp (LSP Server)
    ├─ Provides: LSP interface, project management
    ├─ Responsibility: Protocol translation, handler coordination
    └─ Output: LSP-formatted responses

    ↓ Connected via ↓

LSP Protocol (JSON-RPC)
    ├─ Provides: Client-server communication
    ├─ Responsibility: Message format, request/response routing
    └─ Output: Editor-compatible responses

    ↓ Consumed by ↓

LSP Client (Neovim, VS Code, etc.)
    ├─ Provides: User interface, code editing
    ├─ Responsibility: Display, user interaction
    └─ Output: Code insights, diagnostics visible to developer
```

### Key Insight: OmniSharp is Roslyn's Translator

OmniSharp's job is to:
1. **Use Roslyn workspaces** to load and analyze code
2. **Invoke Roslyn analyzers** to get diagnostics
3. **Translate Roslyn results** into LSP format
4. **Send LSP messages** back to connected editors
5. **Apply configuration** from multiple sources to Roslyn

---

## Part 8: LSP Initialization Options & Configuration

### How Settings are Passed via LSP

In the LSP `initialize` request, clients can send custom settings:

```typescript
interface InitializeParams {
    processId: number | null;
    clientInfo: ClientInfo;              // Name/version of editor
    rootUri: DocumentUri;                 // Workspace root
    capabilities: ClientCapabilities;     // What editor supports
    initializationOptions?: any;          // Custom settings ← IMPORTANT
    trace?: TraceValue;                   // Logging level
    workspaceFolders?: WorkspaceFolder[] | null;
}
```

**OmniSharp's Use:**
- `initializationOptions` can contain configuration
- OmniSharp merges this with omnisharp.json and environment variables
- Example from nvim-lspconfig:

```lua
-- Settings passed via initializationOptions
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
}
```

### How nvim-lspconfig Converts Settings to Command Line

nvim-lspconfig has special handling for OmniSharp to convert Lua settings into command-line arguments via the `on_new_config` function:

```lua
-- In ~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua
-- The on_new_config function:
-- 1. Takes base cmd: { "dotnet", "/path/OmniSharp.dll" }
-- 2. Appends hard-coded args: "-z", "--hostPID", "--encoding", "--languageserver"
-- 3. Flattens settings table into command-line args:
--    settings.RoslynExtensionsOptions.EnableAnalyzersSupport = true
--    becomes: "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
-- 4. Returns final cmd with all flattened settings

-- Final command line might be:
dotnet /path/OmniSharp.dll \
  -s /path/to/solution \
  -loglevel Information \
  -z --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 \
  --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
  FormattingOptions:EnableEditorConfigSupport=true \
  FormattingOptions:OrganizeImports=true
```

---

## Part 9: LSP Capabilities and What They Enable

### Server Capabilities OmniSharp Announces

Based on OmniSharp source code structure (22 handler files):

| Handler | Capability | Editor Feature |
|---------|-----------|-----------------|
| CompletionHandler | `completionProvider` | Code completion (Ctrl+Space) |
| DefinitionHandler | `definitionProvider` | Go to definition (gd) |
| ReferenceHandler | `referencesProvider` | Find references (grr) |
| HoverHandler | `hoverProvider` | Hover information (K) |
| SignatureHelpHandler | `signatureHelpProvider` | Parameter hints |
| CodeActionHandler | `codeActionProvider` | Quick fixes (<leader>ca) |
| FormattingHandler | `documentFormattingProvider` | Format on save |
| RangeFormattingHandler | `documentRangeFormattingProvider` | Format selection |
| RenameHandler | `renameProvider` | Symbol renaming |
| DocumentSymbolHandler | `documentSymbolProvider` | Outline view |
| WorkspaceSymbolHandler | `workspaceSymbolProvider` | Global search |
| TypeDefinitionHandler | `typeDefinitionProvider` | Go to type definition |
| ImplementationHandler | `implementationProvider` | Find implementations |
| SemanticTokensHandler | `semanticTokensProvider` | Syntax highlighting |
| CodeLensHandler | `codeLensProvider` | Code lens decorations |
| DiagnosticsHandler | `diagnosticProvider` | **Error/warning reporting** |
| InlayHintsHandler | `inlayHintProvider` | Type hints in code |
| TextDocumentSyncHandler | `textDocumentSync` | Document synchronization |

---

## Part 10: StyleCop Diagnostic Example - End-to-End

### Complete Flow for StyleCop Warning to Appear in Neovim

**Scenario:** User opens UserController.cs with StyleCop.Analyzers NuGet package installed.

```
STEP 1: Configuration Setup
├─ init.lua defines omnisharp config with:
│  ├─ cmd: "dotnet" + OmniSharp.dll path + "-s" + solution path
│  └─ settings: RoslynExtensionsOptions.EnableAnalyzersSupport = true
├─ Neovim passes settings to OmniSharp during LSP initialization
└─ OmniSharp receives: RoslynExtensionsOptions:EnableAnalyzersSupport=true

STEP 2: Roslyn Workspace Initialization
├─ OmniSharp loads solution at: /path/to/Backend/VDEK.DCSP.sln
├─ Roslyn creates workspace for all projects
├─ Loads StyleCop.Analyzers NuGet package analyzers
├─ Compiles project to get semantic model
└─ Loads all analyzer implementations

STEP 3: StyleCop Analysis
├─ StyleCop DiagnosticAnalyzer.Initialize() runs
├─ Registers ~200 analyzer actions
├─ For each analyzer rule (e.g., SA1116):
│  └─ SyntaxNodeAction registered for ParameterListSyntax nodes
├─ On file open/edit, actions are invoked
├─ At line 56-57: Method parameters detected, SA1116 rule checks:
│  ├─ "Are parameters on separate lines?"
│  ├─ Rule violated! Parameters should start on new line
│  └─ context.ReportDiagnostic(new DiagnosticDescriptor(...))
└─ Diagnostic created with Id="SA1116", Severity=Warning

STEP 4: OmniSharp Collects Diagnostics
├─ DiagnosticsHandler receives Roslyn diagnostics
├─ Transforms to LSP format:
│  ├─ Range: { line: 55, character: 25 } → { line: 56, character: 0 }
│  ├─ Severity: 2 (Warning)
│  ├─ Code: "SA1116"
│  ├─ Message: "Split parameters must begin on new line"
│  └─ Source: "csharp"
└─ Creates publishDiagnostics notification

STEP 5: LSP Protocol Transmission
├─ OmniSharp sends via stdio/HTTP:
│  {
│    "jsonrpc": "2.0",
│    "method": "textDocument/publishDiagnostics",
│    "params": {
│      "uri": "file:///c%3A/Users/Administrator/.../UserController.cs",
│      "diagnostics": [
│        {
│          "range": { "start": { "line": 55, "character": 25 }, ... },
│          "severity": 2,
│          "code": "SA1116",
│          "source": "csharp",
│          "message": "Split parameters must begin on new line"
│        }
│      ]
│    }
│  }
└─ Message transmitted to Neovim

STEP 6: Neovim Display
├─ Neovim LSP client receives publishDiagnostics
├─ Parses JSON and updates diagnostics
├─ Adds to diagnostic namespace for buffer
├─ Shows in:
│  ├─ Gutter (yellow squiggly line)
│  ├─ Hover: diagnostic message displayed
│  ├─ Diagnostic list: :Telescope diagnostics
│  └─ Inline via nvim-lint if configured
└─ User sees warning: "Split parameters must begin on new line"
```

### Why This Wasn't Working Before

**Problem Analysis from CLAUDE.md:**
1. **Configuration not applied**: OmniSharp was started without the RoslynExtensionsOptions setting
2. **Handler conflicts**: Multiple setup calls to lspconfig.omnisharp.setup() - only first takes effect
3. **Settings not flattened**: Command line didn't include `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
4. **Analyzer not enabled**: Without that setting, Roslyn doesn't load StyleCop analyzers

**Result**: StyleCop warnings never appeared because `EnableAnalyzersSupport=false` (default)

---

## Part 11: Additional OmniSharp LSP Features

### Supported LSP Request Types

Based on the 22 LSP handlers in OmniSharp:

| Protocol Method | Description |
|-----------------|-------------|
| `initialize` | Start server, negotiate capabilities |
| `shutdown` | Graceful server shutdown |
| `textDocument/didOpen` | File opened in editor |
| `textDocument/didChange` | File content changed |
| `textDocument/didSave` | File saved to disk |
| `textDocument/didClose` | File closed in editor |
| `textDocument/completion` | Code completion request |
| `textDocument/hover` | Hover information request |
| `textDocument/definition` | Go to definition request |
| `textDocument/typeDefinition` | Go to type definition |
| `textDocument/implementation` | Find implementations |
| `textDocument/references` | Find all references |
| `textDocument/documentSymbol` | File outline/symbols |
| `textDocument/codeAction` | Code actions/quick fixes |
| `textDocument/formatting` | Format entire document |
| `textDocument/rangeFormatting` | Format selected range |
| `textDocument/rename` | Rename symbol |
| `textDocument/signatureHelp` | Parameter hints |
| `textDocument/semanticTokens/full` | Syntax highlighting |
| `textDocument/inlayHint` | Type hints in code |
| `textDocument/codeLens` | Code lens decorations |
| `workspace/symbol` | Search project symbols |

### Performance Considerations

From OmniSharp issues and changelog:
- **Async Diagnostics Analyzer Work Queue** - Prevents UI blocking
- **Multi-threaded analyzer support** - Parallel analysis when allowed
- **Configurable Analysis Timeout** - `documentAnalysisTimeoutMs: 30000` (default)
- **"Analyze Open Documents Only"** - `AnalyzeOpenDocumentsOnly: false` (analyze entire solution)

---

## Part 12: Configuration Examples

### Minimal Working Configuration (Neovim)

```lua
-- minimal config for C# LSP with StyleCop
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', '/path/to/solution.sln',
      '-loglevel', 'Information',
    },
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,           -- KEY: Enable analyzers
        EnableImportCompletion = true,
        AnalyzeOpenDocumentsOnly = false,       -- Analyze all files
      },
      FormattingOptions = {
        EnableEditorConfigSupport = true,
        OrganizeImports = true,
      },
    },
  }
}
```

### omnisharp.json Configuration

```json
{
  "formattingOptions": {
    "tabSize": 4,
    "insertSpaces": true
  },
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false,
    "DocumentAnalysisTimeoutMs": 30000
  },
  "excludeSearchPatterns": [
    "**/node_modules",
    "**/.git"
  ]
}
```

### Environment Variable Configuration

```bash
# Enable StyleCop analyzers
export OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=true

# Start OmniSharp
omnisharp -s /path/to/solution.sln
```

---

## Part 13: Known LSP Implementation Issues

From OmniSharp GitHub issues research:

| Issue | Impact | Status |
|-------|--------|--------|
| Large repository indexing hangs | Performance regression | Known issue #2694 |
| Client capabilities not respected | Protocol non-compliance | Known issue #2693 |
| Encoding handling edge cases | File corruption potential | Known issue #2691 |
| Document version reset on save | Sync conflicts | Fixed in PR #2695 |

---

## Part 14: Summary Table - Roslyn vs OmniSharp vs LSP

| Aspect | Roslyn | OmniSharp | LSP |
|--------|--------|-----------|-----|
| **Purpose** | Compiler platform & APIs | Roslyn wrapper/server | Editor protocol |
| **Responsibility** | Language analysis | LSP translation | Client-server comms |
| **Provides** | Analyzers, symbols, diagnostics | HTTP/stdio server | JSON-RPC messages |
| **Diagnoses** | Compilation errors, analyzer rules | Collects & formats | Transmits to editor |
| **Configuration** | via .editorconfig | via omnisharp.json | via initializationOptions |
| **Output** | Diagnostics objects | publishDiagnostics JSON | LSP notifications |
| **Performance** | Parallel analyzer execution | Single-threaded handler | Async JSON-RPC |

---

## Part 15: Key Takeaways for LSP/OmniSharp Usage

### Critical Configuration Points

1. **EnableAnalyzersSupport must be true** for StyleCop/FxCop/custom analyzers
2. **Solution path (-s)** must be provided for Roslyn to load all projects
3. **AnalyzeOpenDocumentsOnly** controls scope (false = analyze entire solution)
4. **EditorConfig support** enables .editorconfig formatting rules
5. **Command-line flattening** happens automatically by nvim-lspconfig's `on_new_config`

### Verification Commands

```bash
# Check running process
ps aux | grep omnisharp | grep -v grep
# Should include: RoslynExtensionsOptions:EnableAnalyzersSupport=true

# Check LSP info in Neovim
:LspInfo
# Should show: RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... }

# Check OmniSharp logs
tail -f ~/.local/state/nvim/lsp.log
# Should show analyzer initialization
```

### How LSP Fails Without Proper Configuration

```
Config not applied
  ↓
OmniSharp starts with defaults (EnableAnalyzersSupport=false)
  ↓
Roslyn doesn't load StyleCop/analyzer packages
  ↓
No diagnostics reported for StyleCop rules
  ↓
Editor sees: "No StyleCop warnings" (silence = no support)
  ↓
User confused: "Why aren't StyleCop warnings showing?"
```

---

## Conclusion

Roslyn provides the language analysis engine, OmniSharp wraps it for LSP consumption, and the LSP protocol delivers results to editors like Neovim. Configuration flows through multiple layers, and **settings must explicitly enable analyzer support** for warnings to appear.

The key mechanism is:
1. **Settings define behavior** (omnisharp.json, environment, init options)
2. **OmniSharp flattens to CLI args** (on_new_config function)
3. **Roslyn receives as configuration** (reads command-line args)
4. **Analyzers run with enabled features** (StyleCop, FxCop, etc.)
5. **Diagnostics flow to LSP client** (publishDiagnostics)
6. **Editor displays warnings** (red squiggles, diagnostic list)

Without proper configuration at step 1, the entire chain breaks and no diagnostics appear to the user.

---

## References

**Primary Sources:**
- GitHub: dotnet/roslyn (Compiler platform)
- GitHub: OmniSharp/omnisharp-roslyn (LSP server)
- Microsoft Learn: Roslyn SDK documentation
- LSP Specification 3.17: microsoft.github.io/language-server-protocol/
- GitHub: OmniSharp wiki (Configuration Options)
- nvim-lspconfig source code (Roslyn on_new_config)

**Document Created:** 2025-11-13
**Research Agents:** 10 parallel web fetches + 5 sequential analyses
**Total Investigation Time:** ~45 minutes of comprehensive research
