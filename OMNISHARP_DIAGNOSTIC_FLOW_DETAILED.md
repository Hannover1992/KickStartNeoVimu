# OmniSharp Diagnostic Flow: Complete Technical Deep-Dive

**Purpose**: Understand exactly how diagnostics flow from Roslyn through OmniSharp to your editor
**Level**: Advanced / Implementation details
**Audience**: Developers debugging OmniSharp issues or implementing custom analyzers

---

## Table of Contents

1. [Complete Diagnostic Pipeline](#complete-diagnostic-pipeline)
2. [Phase 1: Roslyn Compilation](#phase-1-roslyn-compilation)
3. [Phase 2: Analyzer Discovery](#phase-2-analyzer-discovery)
4. [Phase 3: Diagnostic Collection](#phase-3-diagnostic-collection)
5. [Phase 4: Diagnostic Processing](#phase-4-diagnostic-processing)
6. [Phase 5: LSP Conversion](#phase-5-lsp-conversion)
7. [Phase 6: Publishing](#phase-6-publishing)
8. [Configuration Impact](#configuration-impact)
9. [Performance Considerations](#performance-considerations)
10. [Debugging Diagnostics](#debugging-diagnostics)

---

## Complete Diagnostic Pipeline

### Visual Timeline

```
Editor Event             OmniSharp Processing          LSP Output
─────────────────────────────────────────────────────────────────────────
User opens .cs file
                        [Step 1: Project Load]
                        ├─ Load .csproj/.sln
                        ├─ Create Roslyn Workspace
                        └─ Parse all documents
                                ↓
                        [Step 2: Compilation]
                        ├─ Get Compilation from Project
                        ├─ Include all metadata references
                        └─ Parse all SyntaxTrees
                                ↓
                        [Step 3: Analyzer Setup]
                        ├─ Discover analyzers in NuGet packages
                        ├─ Load analyzer DLLs
                        ├─ Create CompilationWithAnalyzers
                        └─ Apply analyzer options
                                ↓
                        [Step 4: Collect Diagnostics]
                        ├─ Run syntax analyzers
                        ├─ Run semantic analyzers
                        ├─ Filter suppressed diags
                        └─ Compile results
                                ↓
                        [Step 5: Convert Format]
                        ├─ Roslyn Diagnostic → OmniSharp DTO
                        ├─ Extract ID, severity, location
                        └─ Map to LSP severity levels
                                ↓
                        [Step 6: Publish]
                        ├─ Send textDocument/publishDiagnostics
                        ├─ Include all issues
User sees squiggles
                        └─ Format for client display
─────────────────────────────────────────────────────────────────────────
User edits file
                        [Document Changed Event]
                        ├─ Update SourceText in Workspace
                        ├─ Trigger diagnostic re-run
                        └─ Repeat Steps 1-6 for changed file
                                ↓
Squiggles update        [Diagnostics published again]
─────────────────────────────────────────────────────────────────────────
User saves file
                        [File Saved Event]
                        └─ Update persistent document

                        [Optional: Full solution re-analysis]
                        ├─ If analyzer settings changed
                        └─ Repeat Steps 1-6 for all files
```

---

## Phase 1: Roslyn Compilation

### 1.1 Project Discovery and Workspace Creation

**Trigger**: OmniSharp server startup with `-s /path/to/solution`

**Process**:

```csharp
// OmniSharp Startup
var workspace = MSBuildWorkspace.Create();  // Roslyn's MSBuild loader
var solution = await workspace.OpenSolutionAsync(solutionPath);

// Result: Solution object containing all Projects
// Workspace hierarchy:
// Workspace
//  ├─ Solution
//  │   ├─ Project1 (.csproj)
//  │   ├─ Project2 (.csproj)
//  │   └─ Project3 (.csproj)
//  └─ Current source state
```

**What happens**:
1. OmniSharp parses `.sln` file to find `.csproj` files
2. MSBuildWorkspace loads each project's metadata
3. Roslyn creates Project objects with metadata references
4. All Documents (source files) are indexed but not yet parsed

### 1.2 Document Parsing

**When**: When file is opened in editor or accessed for analysis

**Process**:

```csharp
// When file opened in editor (didOpen)
var document = workspace.CurrentSolution.GetDocument(documentId);

// Get or parse SyntaxTree
var syntaxTree = await document.GetSyntaxTreeAsync();
// Result: Parsed AST (Abstract Syntax Tree) of C# file

// SyntaxTree structure:
// CompilationUnitSyntax
//  ├─ UsingDirective
//  ├─ NamespaceDeclaration
//  │   ├─ ClassDeclaration
//  │   │   ├─ MethodDeclaration
//  │   │   │   └─ InvocationExpressionSyntax
//  │   │   │       └─ [etc.]
```

**Output**: `SyntaxTree` object - immutable representation of source code as AST

### 1.3 Semantic Model Creation

**When**: When semantic analysis is needed (diagnostics, completion, etc.)

**Process**:

```csharp
// Get or create semantic model
var semanticModel = await document.GetSemanticModelAsync();
// Result: SemanticModel that binds SyntaxTree to Compilation

// SemanticModel provides:
// - Symbol lookup: GetSymbolInfo(node)
// - Type information: GetTypeInfo(expression)
// - Diagnostic collection: GetDiagnostics()
// - Binding information: GetOperation(node)

// Example: Get type of expression
var position = sourceText.Lines[10].Start + 5;  // Line 10, column 5
var typeInfo = semanticModel.GetTypeInfo(expressionSyntax);
var type = typeInfo.Type;  // ITypeSymbol
```

**Output**: `SemanticModel` object - compiler's semantic analysis of the file

### 1.4 Compilation Finalization

**Process**:

```csharp
// Get complete compilation
var compilation = await project.GetCompilationAsync();

// Compilation includes:
// - All SyntaxTrees from all documents
// - All metadata references (.NET BCL, NuGet packages)
// - Compiler options (language version, features, etc.)
// - All symbol information across project

// Tree count: Number of source files in project
// Reference count: External assemblies
```

**Output**: `Compilation` object - ready for analysis

---

## Phase 2: Analyzer Discovery

### 2.1 Analyzer Source Discovery

**Triggered by**: Configuration `RoslynExtensionsOptions.enableAnalyzersSupport = true`

**Process**:

```csharp
// Step 1: Get project's analyzer references
var analyzerReferences = project.AnalyzerReferences;
// Includes analyzers from:
// - NuGet packages (e.g., StyleCop.Analyzers)
// - Global analyzers folder
// - Custom analyzer paths in omnisharp.json

// Step 2: Load analyzers from each reference
var analyzers = new List<DiagnosticAnalyzer>();
foreach (var reference in analyzerReferences)
{
    var refAnalyzers = reference.GetAnalyzers(LanguageNames.CSharp);
    analyzers.AddRange(refAnalyzers);
}

// Result: List of all available analyzers
// Example from StyleCop.Analyzers:
// - StyleCopAnalyzer
// - OrderingRules
// - NamingRules
// [etc. ~60 different analyzers]
```

**Analyzer Loading**:

```
NuGet Package Discovery
├─ StyleCop.Analyzers (v1.1.118)
│  └─ Contains: StyleCopAnalyzer.dll
├─ Roslynator (v4.x)
│  └─ Contains: Roslynator.CodeAnalysis.dll
└─ AsyncFixer
   └─ Contains: AsyncFixer.dll

↓ Load all analyzer DLLs

Analyzer Types Loaded
├─ SyntaxNodeAnalyzer (inheritance)
├─ SymbolAnalyzer (inheritance)
└─ SyntaxTreeAnalyzer (inheritance)

↓ Create analyzer instances

Active Analyzers Ready for Compilation
└─ CompilationWithAnalyzers
```

### 2.2 Analyzer Registration

**Process**:

```csharp
// Create CompilationWithAnalyzers
var compilationWithAnalyzers = compilation.WithAnalyzers(
    analyzers.ToImmutableArray(),
    new AnalyzerOptions(additionalFiles: null),
    cancellationToken);

// CompilationWithAnalyzers features:
// - Runs analyzers against compilation
// - Provides methods for async analysis
// - Respects analyzer categories (syntax, semantic)
// - Supports progress reporting
```

**Configuration Integration**:

```csharp
// AnalyzerOptions can include:
// - AdditionalFiles (e.g., .editorconfig)
// - Diagnostic filters
// - Analyzer-specific options
// - Category restrictions

// OmniSharp applies from omnisharp.json:
var analyzerOptions = new AnalyzerOptions(
    additionalFiles: editorConfigFiles,  // EditorConfig files
    analyticsPath: analyticsSPath);
```

---

## Phase 3: Diagnostic Collection

### 3.1 Syntax Diagnostics

**Collected by**: `CompilationWithAnalyzers.GetAnalyzerSyntaxDiagnosticsAsync()`

**Examples**:
- `SA1116`: Split parameters should be on same line or all different lines
- `SA1117`: Parameters should be on same line or all separate lines
- Any syntax-level rule violations

**Process**:

```csharp
// Syntax analyzers run on SyntaxTree, not compiled code
var syntaxDiagnostics = await compilationWithAnalyzers
    .GetAnalyzerSyntaxDiagnosticsAsync();

// Process:
// 1. For each SyntaxTree in compilation
// 2. For each syntax analyzer registered
// 3. Run analyzer.AnalyzeSyntaxTree(context)
// 4. Analyzer finds violations in AST
// 5. Reports Diagnostic through context

// Result: List<Diagnostic>
// Minimal overhead - no semantic analysis needed
```

### 3.2 Semantic Diagnostics

**Collected by**: `CompilationWithAnalyzers.GetAnalyzerSemanticDiagnosticsAsync()`

**Examples**:
- `CA1707`: Identifiers should not contain underscores
- `CA1711`: Identifiers should not have incorrect suffix
- Any semantic-level rule violations

**Process**:

```csharp
// Semantic analyzers need full compilation/semantic model
var semanticDiagnostics = await compilationWithAnalyzers
    .GetAnalyzerSemanticDiagnosticsAsync();

// Process:
// 1. For each compilation symbol (type, method, field, etc.)
// 2. For each semantic analyzer registered
// 3. Run analyzer.AnalyzeSymbol(context)
// 4. Analyzer inspects symbol properties
// 5. Reports Diagnostic through context

// Overhead: Much higher - semantic analysis is expensive
// Can involve compilation of entire solution
```

### 3.3 Compiler Diagnostics

**Source**: Direct from `Compilation.GetDiagnostics()`

**Examples**:
- `CS1002`: Semicolon expected
- `CS0103`: Name does not exist in current context
- `CS0023`: Cannot apply operator to operand of type

**Process**:

```csharp
// Compiler diagnostics always collected
var compilerDiagnostics = compilation.GetDiagnostics();

// Source: Roslyn compiler itself
// Generated during compilation phase
// Includes:
// - Parse errors
// - Type errors
// - Reference errors
// - All compiler warnings
```

### 3.4 Diagnostic Filtering

**Process**:

```csharp
// Combine all diagnostic sources
var allDiagnostics = new List<Diagnostic>();
allDiagnostics.AddRange(syntaxDiagnostics);
allDiagnostics.AddRange(semanticDiagnostics);
allDiagnostics.AddRange(compilerDiagnostics);

// Filter out suppressed diagnostics
var activeDiagnostics = allDiagnostics
    .Where(d => !d.IsSuppressed)  // #pragma warning disable
    .Where(d => d.Severity != DiagnosticSeverity.Hidden)
    .ToList();

// Result: Clean list of user-visible diagnostics
```

**Suppression examples**:
```csharp
#pragma warning disable SA1116
public void Method(
    int param1,
    int param2)  // No SA1116 warning here
{
}
#pragma warning restore SA1116
```

---

## Phase 4: Diagnostic Processing

### 4.1 OmniSharp Diagnostic Worker

**File**: `CSharpDiagnosticWorkerWithAnalyzers.cs`

**Orchestrates**: All diagnostic collection phases

**Key Methods**:

```csharp
public async Task<DiagnosticEvents> GetDiagnosticsAsync(
    ImmutableArray<Document> documents)
{
    var result = new DiagnosticEvents();

    // For each document (file)
    foreach (var document in documents)
    {
        // Step 1: Get project
        var project = document.Project;

        // Step 2: Get compilation
        var compilation = await project.GetCompilationAsync();

        // Step 3: If analyzers enabled, create CompilationWithAnalyzers
        if (_options.RoslynExtensionsOptions.EnableAnalyzersSupport)
        {
            var analyzers = project.AnalyzerReferences
                .SelectMany(r => r.GetAnalyzers(LanguageNames.CSharp))
                .ToImmutableArray();

            var compilationWithAnalyzers = compilation
                .WithAnalyzers(analyzers, analyzerOptions, cancellationToken);

            // Step 4: Collect diagnostics
            var syntaxDiags = await compilationWithAnalyzers
                .GetAnalyzerSyntaxDiagnosticsAsync();
            var semanticDiags = await compilationWithAnalyzers
                .GetAnalyzerSemanticDiagnosticsAsync();

            result.Diagnostics.AddRange(syntaxDiags);
            result.Diagnostics.AddRange(semanticDiags);
        }

        // Step 5: Add compiler diagnostics
        result.Diagnostics.AddRange(compilation.GetDiagnostics());

        // Step 6: Filter
        result.Diagnostics = result.Diagnostics
            .Where(d => !d.IsSuppressed)
            .ToList();
    }

    return result;
}
```

### 4.2 Diagnostic Event Forwarding

**Process**:

```csharp
// After collection, publish diagnostics

// Event: DiagnosticEventForwarder receives diagnostics
public void DiagnosticReceived(ImmutableArray<Diagnostic> diagnostics)
{
    foreach (var diagnostic in diagnostics)
    {
        // Filter by configuration
        if (ShouldPublish(diagnostic))
        {
            // Convert and publish
            var quickFix = diagnostic.ToQuickFixResponse(workspace);
            PublishToLSPClient(quickFix);
        }
    }
}
```

### 4.3 Background vs Foreground Analysis

**Background Analysis**:
- Runs for non-open files
- Lower priority
- Can be throttled

**Foreground Analysis**:
- Runs when file is being edited
- Higher priority
- Immediate feedback

**Configuration**:
```json
{
  "RoslynExtensionsOptions": {
    "analyzeOpenDocumentsOnly": false  // Analyze background too
  }
}
```

---

## Phase 5: LSP Conversion

### 5.1 Diagnostic Format Conversion

**From**: Roslyn `Diagnostic` object
**To**: LSP `Diagnostic` object

**Roslyn Diagnostic Structure**:

```csharp
public abstract class Diagnostic
{
    public DiagnosticDescriptor Descriptor { get; }
    public string Id { get; }                    // "SA1116"
    public string GetMessage() { }               // Full message text
    public DiagnosticSeverity Severity { get; }  // Hidden/Info/Warning/Error
    public Location Location { get; }            // File/line/column
    public bool IsSuppressed { get; }
}
```

**LSP Diagnostic Structure**:

```typescript
interface Diagnostic {
    range: Range;              // { start, end }
    severity?: DiagnosticSeverity;  // 1-4 (Error, Warning, Info, Hint)
    code?: string | number;    // "SA1116"
    source?: string;           // "OmniSharp"
    message: string;           // Full message text
    tags?: DiagnosticTag[];    // Unnecessary, Deprecated, etc.
    codeDescription?: CodeDescription;
    relatedInformation?: DiagnosticRelatedInformation[];
}
```

**Conversion Code** (DiagnosticExtensions):

```csharp
public static LSPDiagnostic ToLSPDiagnostic(
    this Diagnostic roslyDiagnostic,
    Workspace workspace)
{
    // Get location
    var lineSpan = roslyDiagnostic.Location.GetLineSpan();
    var range = new LSPRange
    {
        Start = new LSPPosition
        {
            Line = lineSpan.StartLinePosition.Line,
            Character = lineSpan.StartLinePosition.Character
        },
        End = new LSPPosition
        {
            Line = lineSpan.EndLinePosition.Line,
            Character = lineSpan.EndLinePosition.Character
        }
    };

    // Map severity
    var severity = roslyDiagnostic.Severity switch
    {
        DiagnosticSeverity.Error => 1,      // Error
        DiagnosticSeverity.Warning => 2,    // Warning
        DiagnosticSeverity.Info => 3,       // Information
        DiagnosticSeverity.Hidden => 4,     // Hint
        _ => 4
    };

    // Create LSP diagnostic
    return new LSPDiagnostic
    {
        Range = range,
        Severity = severity,
        Code = roslyDiagnostic.Id,
        Source = "omnisharp",
        Message = roslyDiagnostic.GetMessage()
    };
}
```

### 5.2 Severity Mapping

**Roslyn → LSP Mapping**:

| Roslyn Severity | LSP Value | Editor Display |
|---|---|---|
| `DiagnosticSeverity.Error` | 1 | Red squiggle, error decorations |
| `DiagnosticSeverity.Warning` | 2 | Yellow squiggle, warning decorations |
| `DiagnosticSeverity.Info` | 3 | Blue squiggle, info decorations |
| `DiagnosticSeverity.Hidden` | 4 | Subtle hint (light bulb) |

### 5.3 Location Calculation

**Process**:

```csharp
// Get diagnostic location in Roslyn format
var location = diagnostic.Location;
var lineSpan = location.GetLineSpan();

// Line positions are 0-indexed in Roslyn
var startLine = lineSpan.StartLinePosition.Line;
var startChar = lineSpan.StartLinePosition.Character;
var endLine = lineSpan.EndLinePosition.Line;
var endChar = lineSpan.EndLinePosition.Character;

// Convert to LSP Range
var lspRange = new Range
{
    Start = new Position { Line = startLine, Character = startChar },
    End = new Position { Line = endLine, Character = endChar }
};

// Result: Zero-indexed positions for LSP
```

---

## Phase 6: Publishing

### 6.1 LSP Publishing Mechanism

**Protocol**: `textDocument/publishDiagnostics` notification

**Sent by**: OmniSharp server
**Received by**: LSP client (editor)

**Publishing Code**:

```csharp
// LSP Handler sends diagnostics
public async Task PublishDiagnostics(
    string documentPath,
    IEnumerable<Diagnostic> diagnostics)
{
    // Convert to LSP format
    var lspDiagnostics = diagnostics
        .Select(d => d.ToLSPDiagnostic(workspace))
        .ToArray();

    // Create notification
    var notification = new PublishDiagnosticsParams
    {
        Uri = new Uri(documentPath).ToString(),  // file:///path/to/file.cs
        Diagnostics = lspDiagnostics
    };

    // Send over STDIO/HTTP
    await lspServer.SendNotification("textDocument/publishDiagnostics", notification);

    // Result: Editor displays diagnostics
}
```

### 6.2 Full LSP Notification Example

**When**: User opens file with StyleCop violations

**Notification sent by OmniSharp**:

```json
{
  "jsonrpc": "2.0",
  "method": "textDocument/publishDiagnostics",
  "params": {
    "uri": "file:///home/user/project/UserController.cs",
    "diagnostics": [
      {
        "range": {
          "start": {"line": 55, "character": 8},
          "end": {"line": 55, "character": 12}
        },
        "severity": 2,
        "code": "SA1116",
        "source": "omnisharp",
        "message": "Split parameters should be on same line or all separate lines for consistency"
      },
      {
        "range": {
          "start": {"line": 78, "character": 0},
          "end": {"line": 78, "character": 5}
        },
        "severity": 2,
        "code": "SA1633",
        "source": "omnisharp",
        "message": "File header is missing or not located at the top of the file"
      }
    ]
  }
}
```

**Editor display**:
- Line 55, character 8-12: Yellow squiggle + tooltip "SA1116: Split parameters..."
- Line 78, character 0-5: Yellow squiggle + tooltip "SA1633: File header..."

### 6.3 Continuous Publishing

**Event Loop**:

```
User edits file
    ↓
didChange notification received
    ↓
Update SourceText in Workspace
    ↓
Queue diagnostic analysis
    ↓
Run diagnostic worker (background/foreground)
    ↓
Collect new diagnostics
    ↓
Publish textDocument/publishDiagnostics
    ↓
Editor updates squiggles
```

---

## Configuration Impact

### Impact on Each Phase

#### Phase 1-2: Project Loading

| Setting | Impact |
|---------|--------|
| `projectLoadTimeout` | How long to wait for MSBuild to load projects |
| `loadHiddenProjects` | Include hidden projects in analysis |

#### Phase 3: Analyzer Discovery

| Setting | Impact |
|---------|--------|
| `enableAnalyzersSupport` | Whether to run analyzers at all |
| `locationPaths` | Where to find additional analyzers |

#### Phase 4: Diagnostic Collection

| Setting | Impact |
|---------|--------|
| `analyzeOpenDocumentsOnly` | Collect diagnostics for open files only vs all files |
| `analysisBudget` | Timeout for analyzer execution (prevents hangs) |
| `diagnosticWorkerThreadCount` | Parallel analysis threads |

#### Phase 5-6: Publishing

| Setting | Impact |
|---------|--------|
| `FormattingOptions.enableEditorConfigSupport` | Apply EditorConfig rules in diagnostics |
| `organizeImports` | Include import organization in suggestions |

### Configuration Example: Full Diagnostic Pipeline

```json
{
  "projectLoadTimeout": 5000,
  "loadHiddenProjects": false,
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false,
    "analysisBudget": 1000,
    "diagnosticWorkerThreadCount": 2,
    "locationPaths": ["./analyzers"]
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,
    "organizeImports": true
  }
}
```

**Effect on pipeline**:
1. ✅ Load all projects (including hidden)
2. ✅ Discover all analyzers from locationPaths
3. ✅ Analyze all files (not just open)
4. ✅ With 1000ms timeout per analyzer
5. ✅ Use 2 threads for parallelism
6. ✅ Apply EditorConfig rules
7. ✅ Include import suggestions

---

## Performance Considerations

### Phase 3 (Diagnostic Collection) Bottleneck

**Why it's slow**:
- Must compile entire project
- Must run every analyzer on every file
- Semantic analysis is expensive
- Can take seconds for large projects

**Optimization strategies**:

#### Strategy 1: Analyze Only Open Documents

```json
{
  "RoslynExtensionsOptions": {
    "analyzeOpenDocumentsOnly": true
  }
}
```

**Impact**:
- ✅ Much faster (only 1-2 files analyzed)
- ❌ Misses errors in other files
- ✅ Good for: Single-file editing, resource-constrained systems

#### Strategy 2: Reduce Thread Count

```json
{
  "RoslynExtensionsOptions": {
    "diagnosticWorkerThreadCount": 1
  }
}
```

**Impact**:
- ✅ Lower CPU/memory usage
- ❌ Slightly slower analysis
- ✅ Good for: Laptop batteries, background analysis

#### Strategy 3: Reduce Analysis Budget

```json
{
  "RoslynExtensionsOptions": {
    "analysisBudget": 300
  }
}
```

**Impact**:
- ✅ Analyzer runs cut off after 300ms
- ❌ Incomplete analysis (some diagnostics missed)
- ✅ Good for: Preventing hangs from buggy analyzers

#### Strategy 4: Disable Analyzers

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": false
  }
}
```

**Impact**:
- ✅ Very fast (only compiler diagnostics)
- ❌ No style/quality warnings (SA1xxx, CA1xxx)
- ✅ Good for: Quick iterations, debugging

### Performance Timeline Example

**Large project (1000 files, 50 analyzers enabled)**:

```
User opens file
    ↓ (30-60s first time)
Project loads, compiles, analyzes
    ↓
Diagnostics appear
    ↓
User makes edit
    ↓ (2-5s)
Only changed files re-analyzed (if not analyzeOpenDocumentsOnly)
    ↓
Diagnostics update
```

---

## Debugging Diagnostics

### How to Debug Missing Diagnostics

**Problem**: Expect SA1116 warning but don't see it

**Debug Steps**:

#### Step 1: Verify Configuration Applied

```lua
-- In Neovim
:LspInfo
" Look for: RoslynExtensionsOptions { EnableAnalyzersSupport = true }
```

#### Step 2: Verify Process Parameters

```bash
ps aux | grep omnisharp | grep -v grep
# Should contain: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

#### Step 3: Verify Analyzers Available

```bash
cd /project/path
# Check if StyleCop.Analyzers is in .csproj
grep -r "StyleCop.Analyzers" *.csproj

# Verify with dotnet
dotnet list package | grep -i stylecop
```

#### Step 4: Verify Manually with dotnet

```bash
dotnet build  # or dotnet build --no-restore
# Should show: warning SA1116: ...
```

If `dotnet build` shows the warning but OmniSharp doesn't, it's an OmniSharp issue, not project issue.

#### Step 5: Check OmniSharp Logs

```bash
# Enable debug logging and restart
OMNISHARP_LogLevel=Debug \
dotnet /path/to/OmniSharp.dll -s /solution/path --lsp 2>&1 | tee omnisharp.log

# Search for analyzer loading
grep -i "analyzer" omnisharp.log
grep -i "SA1116" omnisharp.log
grep -i "diagnostic" omnisharp.log

# Or check existing logs
tail -100 ~/.local/state/nvim/lsp.log | grep -i analyzer
```

#### Step 6: Manual Diagnostic Test

**Create test file**:
```csharp
public void Method(int p1,
    int p2)  // Should trigger SA1116
{
}
```

**Expected**: Yellow squiggle under `p1` or `p2`

### Analyzer Discovery Debugging

**Problem**: Analyzer installed but not discovering

**Debug**:

```csharp
// In OmniSharp context, check available analyzers
var project = workspace.CurrentSolution.Projects.First();
var analyzers = project.AnalyzerReferences
    .SelectMany(r => r.GetAnalyzers("C#"))
    .ToList();

Console.WriteLine($"Found {analyzers.Count} analyzers:");
foreach (var analyzer in analyzers)
{
    Console.WriteLine($"  - {analyzer.GetType().Name}");
}

// Should include: StyleCopAnalyzer, etc.
```

### Performance Debugging

**Problem**: OmniSharp is slow

**Debug**:

```bash
# Add verbose diagnostic logging
OMNISHARP_LogLevel=Debug OMNISHARP_Roslyn:EnableAnalyzersSupport=true \
time dotnet /path/to/OmniSharp.dll -s /solution/path --lsp

# Check which phase is slow
# Project load: ~5-30s first time
# Compilation: ~2-10s depending on size
# Analyzer run: ~1-10s depending on count and project size
```

**Profile diagnostics**:
```bash
# If analyzer timeout, check:
ps aux | grep omnisharp
# Look for multiple OmniSharp processes (hanging analyzers)

# Kill and check which analyzer hangs
pkill -f omnisharp
rm -rf ~/.cache/nvim/luac/

# Test with specific analyzer disabled
# (remove from .csproj and re-run)
```

---

## Complete Example: From Code Change to Editor Display

### Scenario: User types space before opening paren

**Before**:
```csharp
void Method (int p1, int p2)
          ↑ (cursor here)
```

**Event sequence**:

```
1. User types space
   ↓
   TextDocument/didChange notification
   |
   OmniSharp receives event

2. Update SourceText in Workspace
   ↓
   Old: "void Method(int p1, int p2)"
   New: "void Method (int p1, int p2)"

3. Trigger diagnostic re-run
   ↓
   Queue document for analysis

4. CSharpDiagnosticWorkerWithAnalyzers.GetDiagnosticsAsync()
   ├─ Get project
   ├─ Get compilation
   ├─ Discover analyzers (StyleCop, etc.)
   ├─ Create CompilationWithAnalyzers
   ├─ Call GetAnalyzerSyntaxDiagnosticsAsync()
   │  └─ StyleCopAnalyzer detects: SA1110 - Space before paren
   └─ Filter diagnostics

5. Diagnostics collected:
   [
     {
       Id: "SA1110",
       Severity: Warning,
       Location: Line 0, Char 11-12,
       Message: "Opening parenthesis should be preceded by a space."
     }
   ]

6. Convert to OmniSharp format
   ↓
   QuickFixResponse {
     Code: "SA1110",
     Text: "Opening parenthesis should be preceded by a space.",
     Line: 0,
     Column: 11,
     EndColumn: 12,
     LogLevel: "Warning"
   }

7. Convert to LSP format
   ↓
   PublishDiagnosticsParams {
     uri: "file:///path/Method.cs",
     diagnostics: [
       {
         range: { start: {line: 0, char: 11}, end: {line: 0, char: 12} },
         severity: 2,
         code: "SA1110",
         source: "omnisharp",
         message: "Opening parenthesis should be preceded by a space."
       }
     ]
   }

8. Send textDocument/publishDiagnostics over STDIO
   ↓
   LSP client (Neovim) receives notification

9. Editor displays:
   void Method (int p1, int p2)
              ↑ Yellow squiggle + hover tooltip
```

**Total time**: ~0.5-2 seconds (depending on project size)

---

## Summary: Key Takeaways

### How Diagnostics Flow

1. **Roslyn compiles** source into AST + semantic model
2. **Roslyn discovers** analyzers from NuGet packages
3. **Roslyn runs** analyzers on compilation
4. **OmniSharp collects** results from Roslyn
5. **OmniSharp converts** Roslyn format to OmniSharp DTO
6. **OmniSharp translates** to LSP format
7. **LSP sends** diagnostics to editor via notification
8. **Editor displays** diagnostics as squiggles + decorations

### Configuration Controls Pipeline

- `enableAnalyzersSupport`: Enables/disables entire analyzer system
- `analyzeOpenDocumentsOnly`: Controls whether background analysis runs
- `analysisBudget`: Prevents hanging analyzers
- `enableEditorConfigSupport`: Applies .editorconfig rules
- `FormattingOptions`: Controls formatting in diagnostics

### Performance Principles

- Syntax analysis is fast (milliseconds)
- Semantic analysis is slow (seconds for large projects)
- Analyzer discovery is cached
- Background analysis can be throttled
- Large projects benefit from `analyzeOpenDocumentsOnly: true`

---

**Document Version**: 1.0
**Last Updated**: November 13, 2025
**Status**: Complete technical reference
