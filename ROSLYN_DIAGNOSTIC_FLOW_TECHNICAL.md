# Roslyn Diagnostic Flow - Technical Deep Dive

**For Developers Debugging Configuration Issues**

---

## Table of Contents

1. [Complete Diagnostic Lifecycle](#complete-diagnostic-lifecycle)
2. [Configuration Transformation Pipeline](#configuration-transformation-pipeline)
3. [Analyzer Registration and Execution](#analyzer-registration-and-execution)
4. [LSP Protocol Messages](#lsp-protocol-messages)
5. [OmniSharp Handler Architecture](#omnisharp-handler-architecture)
6. [Roslyn Workspace Model](#roslyn-workspace-model)
7. [Performance Characteristics](#performance-characteristics)
8. [Debugging Techniques](#debugging-techniques)

---

## Complete Diagnostic Lifecycle

### Phase 1: Initialization (LSP Initialize Request)

**Client → Server (Editor → OmniSharp):**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "processId": 12345,
    "clientInfo": {
      "name": "Neovim",
      "version": "0.9.0"
    },
    "rootUri": "file:///c%3A/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend",
    "capabilities": {
      "textDocument": {
        "synchronization": {"didSave": true},
        "completion": {"completionItem": {"snippetSupport": true}},
        "publishDiagnostics": {"relatedInformation": true},
        "diagnostic": {"dynamicRegistration": false}
      }
    },
    "initializationOptions": {
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
  }
}
```

**OmniSharp Processing (LanguageServerHost.cs):**

```csharp
// Pseudocode representation
void Initialize(InitializeParams @params)
{
    // 1. Extract rootUri
    var workspaceRoot = @params.RootUri;  // file:///c%3A/.../Backend

    // 2. Load configuration hierarchy
    var config = new ConfigurationLoader()
        .LoadHardcodedDefaults()                          // Level 5
        .LoadEnvironmentVariables("OMNISHARP_")           // Level 4
        .LoadCommandLineArguments()                       // Level 3
        .LoadGlobalOmniSharpJson("~/.omnisharp/")        // Level 2
        .LoadLocalOmniSharpJson(workspaceRoot);          // Level 1 (highest)

    // 3. Merge initialization options (highest priority)
    config.RoslynExtensionsOptions = @params.InitializationOptions
        ?.RoslynExtensionsOptions ?? config.RoslynExtensionsOptions;

    // 4. Create composition host (dependency injection)
    this.CompositionHost = CreateCompositionHost(
        workspaceRoot: workspaceRoot,
        configuration: config,
        capabilities: @params.Capabilities);

    // 5. Register handlers
    this.RegisterHandlers();

    // 6. Load solution and projects
    LoadSolution(workspaceRoot);

    // 7. Initialize Roslyn workspace
    roslyWorksapce.OpenSolutionAsync(solutionPath);
}
```

**Server → Client (OmniSharp → Editor):**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "capabilities": {
      "textDocumentSync": 1,
      "completionProvider": {
        "resolveProvider": true,
        "triggerCharacters": ["."]
      },
      "hoverProvider": true,
      "definitionProvider": true,
      "referencesProvider": true,
      "codeActionProvider": true,
      "documentFormattingProvider": true,
      "renameProvider": true,
      "workspaceSymbolProvider": true,
      "diagnosticProvider": {
        "interFileDependencies": true,
        "workspaceDiagnostics": false
      }
    },
    "serverInfo": {
      "name": "OmniSharp",
      "version": "1.39.14"
    }
  }
}
```

---

### Phase 2: Document Opening (textDocument/didOpen)

**Client → Server:**

```json
{
  "jsonrpc": "2.0",
  "method": "textDocument/didOpen",
  "params": {
    "textDocument": {
      "uri": "file:///c%3A/Users/.../UserController.cs",
      "languageId": "csharp",
      "version": 1,
      "text": "using System;\npublic class UserController {\n  public void GetUser(int id,\nstring name) {\n  }\n}"
    }
  }
}
```

**OmniSharp Processing:**

```csharp
// TextDocumentSyncHandler.cs
void Handle(DidOpenTextDocumentParams @params)
{
    // 1. Extract document info
    var uri = @params.TextDocument.Uri;              // file URI
    var text = @params.TextDocument.Text;             // file contents
    var version = @params.TextDocument.Version;       // version 1

    // 2. Normalize path
    var filePath = ConvertUriToFilePath(uri);

    // 3. Update Roslyn workspace
    workspace.AddDocument(filePath, text);

    // 4. Request initial diagnostics
    RequestDiagnosticsAsync(filePath);
}
```

---

### Phase 3: Document Modification (textDocument/didChange)

**Client → Server:**

```json
{
  "jsonrpc": "2.0",
  "method": "textDocument/didChange",
  "params": {
    "textDocument": {
      "uri": "file:///c%3A/.../UserController.cs",
      "version": 2
    },
    "contentChanges": [
      {
        "range": {
          "start": {"line": 2, "character": 30},
          "end": {"line": 2, "character": 30}
        },
        "text": "\n"
      }
    ]
  }
}
```

**OmniSharp Processing:**

```csharp
// TextDocumentSyncHandler.cs
async Task Handle(DidChangeTextDocumentParams @params)
{
    // 1. Extract changes
    var uri = @params.TextDocument.Uri;
    var changes = @params.ContentChanges;

    // 2. Apply to Roslyn workspace
    var document = workspace.GetDocument(uri);
    foreach (var change in changes)
    {
        document.ApplyChange(change.Range, change.Text);
    }

    // 3. Update semantic model (triggers re-analysis)
    workspace.UpdateDocument(document);

    // 4. Queue diagnostic analysis
    DiagnosticAnalysisQueue.Enqueue(uri);
}
```

---

### Phase 4: Roslyn Semantic Analysis

**Workspace Update Triggers Analysis:**

```csharp
// When workspace.UpdateDocument() is called:

// 1. Roslyn re-parses file
SyntaxTree newSyntaxTree = CSharpSyntaxTree.ParseText(newText);

// 2. Roslyn updates compilation (if needed)
compilation = compilation.ReplaceSyntaxTree(
    oldTree: currentSyntaxTree,
    newTree: newSyntaxTree);

// 3. Roslyn updates semantic model
semanticModel = compilation.GetSemanticModel(newSyntaxTree);

// 4. Roslyn runs diagnostic analyzers
List<Diagnostic> diagnostics = GetDiagnostics(
    compilation: compilation,
    syntaxTree: newSyntaxTree,
    semanticModel: semanticModel);
```

---

### Phase 5: Analyzer Execution (StyleCop Example)

**For each loaded analyzer (StyleCop.Analyzers package):**

```csharp
// StyleCop: SA1116 Rule
public class ParameterFormattingAnalyzer : DiagnosticAnalyzer
{
    public override void Initialize(AnalysisContext context)
    {
        // Register to analyze ParameterListSyntax nodes
        context.RegisterSyntaxNodeAction(
            action: AnalyzeParameterList,
            syntaxKinds: new[] { SyntaxKind.ParameterList });
    }

    private void AnalyzeParameterList(SyntaxNodeAnalysisContext context)
    {
        var parameterList = (ParameterListSyntax)context.Node;

        // Check: Are all parameters on same line?
        var firstLine = parameterList.Parameters[0].GetLocation().GetLineSpan().StartLinePosition.Line;
        var otherLinesPresent = parameterList.Parameters
            .Skip(1)
            .Any(p => p.GetLocation().GetLineSpan().StartLinePosition.Line != firstLine);

        if (otherLinesPresent)
        {
            // Violation: SA1116 - Parameters on different lines
            var diagnostic = Diagnostic.Create(
                descriptor: SA1116_DESCRIPTOR,
                location: parameterList.GetLocation(),
                messageArgs: null);

            context.ReportDiagnostic(diagnostic);
        }
    }
}
```

**Example Matching (UserController.cs):**

```csharp
public void GetUser(int id,      // Line 3, same as first param
string name) {                    // Line 4, DIFFERENT LINE!
    // ...
}

// SA1116 violation detected:
// - Start: Line 3, Column 30 (after "id,")
// - End: Line 4, Column 0 (before "string")
```

---

### Phase 6: Diagnostic Collection

**OmniSharp DiagnosticsHandler:**

```csharp
// DiagnosticsHandler.cs (oversimplified)
async Task<PublishDiagnosticsParams> CollectDiagnostics(string uri)
{
    var document = workspace.GetDocument(uri);

    // 1. Get compilation diagnostics (syntax, semantic errors)
    var compilationDiagnostics = document.Compilation
        .GetDiagnostics()
        .Where(d => d.Location.SourceTree == document.SyntaxTree)
        .ToList();

    // 2. Run analyzers
    var analyzerDiagnostics = new List<Diagnostic>();
    foreach (var analyzer in LoadedAnalyzers)  // StyleCop, FxCop, etc.
    {
        // Only if EnableAnalyzersSupport=true
        if (config.RoslynExtensionsOptions.EnableAnalyzersSupport)
        {
            var results = analyzer.Analyze(document.Compilation);
            analyzerDiagnostics.AddRange(results);
        }
    }

    // 3. Combine and convert to LSP format
    var allDiagnostics = compilationDiagnostics
        .Concat(analyzerDiagnostics)
        .Select(d => ConvertToLspDiagnostic(d))
        .ToArray();

    return new PublishDiagnosticsParams
    {
        Uri = uri,
        Diagnostics = allDiagnostics,
        Version = document.Version
    };
}

private LSP.Diagnostic ConvertToLspDiagnostic(Roslyn.Diagnostic roslyDiag)
{
    var location = roslyDiag.Location;
    var lineSpan = location.GetLineSpan();

    return new LSP.Diagnostic
    {
        Range = new Range
        {
            Start = new Position(
                line: lineSpan.StartLinePosition.Line,
                character: lineSpan.StartLinePosition.Character),
            End = new Position(
                line: lineSpan.EndLinePosition.Line,
                character: lineSpan.EndLinePosition.Character)
        },
        Severity = ConvertSeverity(roslyDiag.Severity),  // 1=Error, 2=Warning
        Code = roslyDiag.Id,                              // "SA1116"
        Source = "csharp",
        Message = roslyDiag.GetMessage()                  // "Split parameters..."
    };
}
```

---

### Phase 7: LSP Notification Sent to Client

**Server → Client:**

```json
{
  "jsonrpc": "2.0",
  "method": "textDocument/publishDiagnostics",
  "params": {
    "uri": "file:///c%3A/Users/.../UserController.cs",
    "version": 3,
    "diagnostics": [
      {
        "range": {
          "start": {"line": 55, "character": 25},
          "end": {"line": 56, "character": 0}
        },
        "severity": 2,
        "code": "SA1116",
        "source": "csharp",
        "message": "Split parameters must begin on new line",
        "tags": []
      },
      {
        "range": {
          "start": {"line": 56, "character": 0},
          "end": {"line": 56, "character": 6}
        },
        "severity": 2,
        "code": "SA1100",
        "source": "csharp",
        "message": "Do not prefix local calls with 'this.'",
        "tags": []
      }
    ]
  }
}
```

---

### Phase 8: Client Display

**Neovim LSP Client:**

```lua
-- Received publishDiagnostics in nvim_lsp.lua
function handle_publish_diagnostics(_, result, ctx)
    local uri = result.uri
    local bufnr = vim.uri_to_bufnr(uri)

    -- Convert LSP diagnostics to Neovim format
    local diagnostics = {}
    for _, diag in ipairs(result.diagnostics) do
        table.insert(diagnostics, {
            lnum = diag.range.start.line,           -- Line (0-indexed)
            col = diag.range.start.character,       -- Column (0-indexed)
            end_lnum = diag.range["end"].line,
            end_col = diag.range["end"].character,
            severity = diag.severity,               -- 1=Error, 2=Warning
            message = diag.message,
            code = diag.code,
            source = diag.source
        })
    end

    -- Add to buffer diagnostics
    vim.diagnostic.set(namespace, bufnr, diagnostics)
end
```

**Result in Editor:**

```
Line 56:  public void GetUser(int id,     ← Squiggly yellow underline
          │                           │
          └─ Character 25
          String name) {
Line 57:  │
          └─ Character 0: Start of "string"

Hover Shows:
  [csharp] SA1116
  Split parameters must begin on new line
```

---

## Configuration Transformation Pipeline

### Entry Points

**Configuration can come from 5 sources (evaluated in order):**

```
┌─────────────────────────────────────────┐
│  Hardcoded Defaults (Lowest Priority)   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│  Environment Variables                  │
│  OMNISHARP_RoslynExtensionsOptions:...   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│  Command-Line Arguments                 │
│  RoslynExtensionsOptions:EnableAnalyz... │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│  ~/.omnisharp/omnisharp.json (Global)   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│  ./omnisharp.json (Local - Highest)     │
│  OR initializationOptions (LSP init)    │
└─────────────────────────────────────────┘
```

### Example Transformation

**Starting point (Neovim init.lua):**

```lua
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
        EnableAnalyzersSupport = true,
        EnableImportCompletion = true,
        AnalyzeOpenDocumentsOnly = false,
      },
    },
  }
}
```

**Step 1: nvim-lspconfig processes this**

nvim-lspconfig's `on_new_config` function is called:

```lua
-- ~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua
-- (This is internal, not user code)
local function on_new_config(new_config, new_root_dir)
    -- Extract settings table
    local settings = new_config.settings or {}

    -- Flatten settings into command-line arguments
    local cmd_args = {}

    -- Start with base cmd
    for _, part in ipairs(new_config.cmd) do
        table.insert(cmd_args, part)
    end

    -- Flatten settings recursively
    local function flatten_table(tbl, prefix)
        for key, value in pairs(tbl) do
            if type(value) == "table" then
                flatten_table(value, prefix .. key .. ":")
            else
                -- Convert Lua boolean to string
                local str_value = tostring(value):lower()
                table.insert(cmd_args, prefix .. key .. "=" .. str_value)
            end
        end
    end

    if settings then
        flatten_table(settings, "")
    end

    -- Result: cmd_args now contains flattened args
    new_config.cmd = cmd_args
end
```

**Step 2: Lua booleans converted to strings**

```
Lua:     EnableAnalyzersSupport = true
String:  "EnableAnalyzersSupport=true"

Lua:     AnalyzeOpenDocumentsOnly = false
String:  "AnalyzeOpenDocumentsOnly=false"
```

**Step 3: Final command line constructed**

```bash
dotnet \
  /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /path/to/solution.sln \
  -loglevel Information \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
```

**Step 4: OmniSharp parses command-line arguments**

```csharp
// OmniSharp startup code
void ParseCommandLineArguments(string[] args)
{
    // args[0] = "/path/OmniSharp.dll"
    // args[1] = "-s"
    // args[2] = "/path/to/solution.sln"
    // args[3] = "-loglevel"
    // args[4] = "Information"
    // args[5] = "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
    // args[6] = "RoslynExtensionsOptions:EnableImportCompletion=true"
    // args[7] = "RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false"

    foreach (var arg in args)
    {
        if (arg.Contains(":"))
        {
            var parts = arg.Split('=');
            var key = parts[0];      // "RoslynExtensionsOptions:EnableAnalyzersSupport"
            var value = parts[1];    // "true"

            // Nested key structure
            SetConfigValue(key, value);
            // Internally: config["RoslynExtensionsOptions"]["EnableAnalyzersSupport"] = true
        }
    }
}
```

**Step 5: OmniSharp creates Roslyn workspace with configuration**

```csharp
var workspace = new AdhocWorkspace();

// Apply configuration to workspace options
var options = workspace.Options;
options = options.WithChangedOption(
    FormattingOptions.UseTabs, LanguageNames.CSharp, false);
options = options.WithChangedOption(
    FormattingOptions.TabSize, LanguageNames.CSharp, 4);

// Create analyzer with settings
var analyzerConfiguration = new AnalyzerConfiguration(
    enableAnalyzersSupport: true,        // ← From command line!
    analyzeOpenDocumentsOnly: false,
    documentAnalysisTimeoutMs: 30000);

this.AnalyzerService = new AnalyzerService(analyzerConfiguration);
```

**Step 6: Analyzers now enabled and running**

```csharp
public class AnalyzerService
{
    private bool _enableAnalyzersSupport;  // true

    public async Task<IEnumerable<Diagnostic>> AnalyzeAsync(Document doc)
    {
        if (_enableAnalyzersSupport)  // ← TRUE!
        {
            // Load StyleCop, FxCop, and other analyzers
            var analyzers = CompilationWithAnalyzers.Create(
                compilation,
                analyzers: new[] { StyleCopAnalyzers, FxCopAnalyzers, ... });

            // Run analyzers
            var diagnostics = await analyzers.GetAnalyzerDiagnosticsAsync();

            return diagnostics;
        }

        return Enumerable.Empty<Diagnostic>();  // No analyzers run
    }
}
```

---

## Analyzer Registration and Execution

### Detailed Analyzer Lifecycle

```
Analyzer Package Loaded (StyleCop.Analyzers.dll)
  ↓
OmniSharp Reflection Discovery
  └─ Find all classes inheriting from DiagnosticAnalyzer
    ├─ ParameterFormattingAnalyzer (SA1116)
    ├─ PropertyDeclarationAnalyzer (SA1101)
    ├─ SingleLineCommentAnalyzer (SA1120)
    └─ ... (200+ analyzers)
  ↓
For each analyzer:
  ├─ Instantiate: new ParameterFormattingAnalyzer()
  ├─ Call: Initialize(AnalysisContext context)
  │  └─ Registers actions
  │    └─ SyntaxNodeAction for ParameterListSyntax
  └─ Store in analyzer registry
  ↓
Compilation created, analyzers attached
  ↓
For each syntax tree in compilation:
  ├─ For each SyntaxNodeAction:
  │  └─ Visit every ParameterListSyntax node
  │    ├─ Call AnalyzeParameterList()
  │    ├─ Check formatting rule
  │    └─ Report diagnostic if violated
  ├─ For each SymbolAction:
  │  └─ Visit every symbol
  └─ For each CompilationAction:
     └─ Run once per compilation
  ↓
All diagnostics collected in list
  ↓
Diagnostics sorted by severity, location
  ↓
Return to OmniSharp for transmission to client
```

### Execution Order Guarantees

**Within single analyzer:**
```
CompilationStartAction
  ↓ (runs once)
All SymbolStartAction for all symbols
  ↓ (in order)
SyntaxNodeAction + OperationAction (for that symbol)
  ↓ (may run concurrently)
All SymbolEndAction
  ↓ (reverse order of Start)
CompilationEndAction
  ↓ (runs once)
```

**Between analyzers:**
- No guaranteed order
- May run concurrently (if `EnableConcurrentExecution` not set)
- OmniSharp may run multiple analyzers in parallel

---

## LSP Protocol Messages

### Request-Response Pattern

**Standard LSP Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "method": "textDocument/completion",
  "params": { ... }
}
```

**LSP Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "result": [ ... ] or "error": { "code": -32600, "message": "..." }
}
```

**OmniSharp expects `id` to track request:**
- If missing, treated as notification
- Response must include same `id`
- Enables request/response matching

### Notification Pattern (No Response Expected)

**Client → Server:**
```json
{
  "jsonrpc": "2.0",
  "method": "textDocument/didChange",
  "params": { ... }
  /* NO "id" field */
}
```

**Server → Client (Unsolicited):**
```json
{
  "jsonrpc": "2.0",
  "method": "textDocument/publishDiagnostics",
  "params": { ... }
  /* NO "id" field */
}
```

### Diagnostic Message Structure

**Full DiagnosticContainer Message:**

```
┌──────────────────────────────────────┐
│ Diagnostic                           │
├──────────────────────────────────────┤
│ · range: Range                       │
│   · start: Position                  │
│     · line: number (0-indexed)       │
│     · character: number (0-indexed)  │
│   · end: Position                    │
│     · line: number                   │
│     · character: number              │
├──────────────────────────────────────┤
│ · severity: DiagnosticSeverity?      │
│   1 = Error, 2 = Warning,            │
│   3 = Information, 4 = Hint          │
├──────────────────────────────────────┤
│ · code: string | number              │
│   "SA1116" or 1116                   │
├──────────────────────────────────────┤
│ · source: string?                    │
│   "csharp"                           │
├──────────────────────────────────────┤
│ · message: string                    │
│   "Split parameters must..."         │
├──────────────────────────────────────┤
│ · tags: DiagnosticTag[]?             │
│   [1] = Unnecessary                  │
│   [2] = Deprecated                   │
├──────────────────────────────────────┤
│ · codeDescription: CodeDescription?  │
│   · href: URI to online documentation│
├──────────────────────────────────────┤
│ · relatedInformation:                │
│   DiagnosticRelatedInformation[]?    │
│   · location: Location (another place)
│   · message: string                  │
├──────────────────────────────────────┤
│ · data: unknown?                     │
│   Custom server-specific data        │
└──────────────────────────────────────┘
```

---

## OmniSharp Handler Architecture

### Handler Execution Flow

```
LSP Request Arrives
  ↓
RequestRouter.Route(method, @params)
  ↓
Find matching handler by method name
  ├─ "textDocument/completion" → CompletionHandler
  ├─ "textDocument/hover" → HoverHandler
  ├─ "textDocument/definition" → DefinitionHandler
  └─ "textDocument/diagnostic" → DiagnosticsHandler (not used - uses push model)
  ↓
Cast @params to specific type
  ├─ CompletionParams
  ├─ HoverParams
  ├─ DefinitionParams
  └─ TextDocumentParams
  ↓
Call handler.Handle(params)
  ├─ Extract uri, position, etc.
  ├─ Call Roslyn workspace API
  ├─ Process results
  └─ Return LSP-formatted response
  ↓
Send response with same request ID
```

### Example: HoverHandler

```csharp
public class OmniSharpHoverHandler : IRequestHandler<HoverParams, Hover>
{
    public async Task<Hover> Handle(HoverParams @params, CancellationToken token)
    {
        var file = @params.TextDocument.Uri;
        var position = @params.Position;

        // 1. Get Roslyn document and semantic model
        var document = workspace.GetDocument(file);
        var compilation = await document.Project.GetCompilationAsync(token);
        var semanticModel = await document.GetSemanticModelAsync(token);

        // 2. Find symbol at position
        var sourceText = await document.GetTextAsync(token);
        var offset = sourceText.Lines.GetPosition(
            new LinePosition(position.Line, position.Character));

        var node = await document.GetSyntaxRootAsync(token);
        var token_at_cursor = node.FindToken(offset);

        // 3. Get symbol information
        var symbol = semanticModel.GetSymbolInfo(token_at_cursor.Parent);

        // 4. Format for LSP
        if (symbol.Symbol != null)
        {
            var contents = FormatSymbolForHover(symbol.Symbol);
            return new Hover
            {
                Contents = new MarkedStringsOrMarkupContent(contents)
            };
        }

        return null;
    }
}
```

---

## Roslyn Workspace Model

### Document and Project Hierarchy

```
Solution
├─ Project 1 (VDEK.DCSP.WebHost.csproj)
│  ├─ Document: Program.cs
│  ├─ Document: Startup.cs
│  └─ Document: Controllers/UserController.cs ← We're analyzing this
├─ Project 2 (VDEK.DCSP.Core.csproj)
│  ├─ Document: Models/User.cs
│  └─ Document: Services/UserService.cs
└─ Project 3 (VDEK.DCSP.Tests.csproj)
   ├─ Document: UserControllerTests.cs
   └─ Document: UserServiceTests.cs
```

### Compilation Dependency Chain

```
Solution Compilation
  ├─ References all projects
  └─ For WebHost project:
     ├─ Project compilation (metadata)
     └─ SyntaxTree for each document
        ├─ Program.cs → SyntaxTree
        ├─ Startup.cs → SyntaxTree
        ├─ UserController.cs → SyntaxTree ← Current
        └─ ... all others
```

### Semantic Model Scope

```
UserController.cs semantic model only understands:
├─ Types within this file
├─ Types in using directives
└─ Types from referenced assemblies

Cannot directly reference:
├─ Internal types in other project files
└─ Private members in other classes
```

**Why solution path (-s) matters:**

```
Without -s:
  └─ OmniSharp may find only one project
     └─ Compilation includes only that project
        └─ Cross-project types unresolved
           └─ IntelliSense and diagnostics incomplete

With -s /path/solution.sln:
  └─ OmniSharp loads all projects
     └─ Compilation includes all projects
        └─ Cross-project types fully resolved
           └─ Complete analysis and diagnostics
```

---

## Performance Characteristics

### Analyzer Execution Timeline

```
File Edit (Character Typed)
  ↓
textDocument/didChange notified to OmniSharp
  ↓
Workspace updated
  ↓
Compilation invalidated
  ↓ (can be 100-500ms)
Compilation recreated
  ↓
Analyzers queued for execution
  ↓ (depends on settings)
[Async] Analyzers run in background thread
  │
  ├─ CompilationStartAction: ~1ms
  │
  ├─ StyleCop analyzers: ~50-200ms
  │  ├─ Check formatting
  │  ├─ Check naming conventions
  │  └─ Check style rules
  │
  ├─ FxCop analyzers: ~30-100ms
  │  ├─ Security checks
  │  └─ Design checks
  │
  ├─ Custom analyzers: ~10-50ms
  │
  └─ CompilationEndAction: ~1ms
  ↓ (Total: ~100-350ms)
Diagnostics collected
  ↓
publishDiagnostics sent to client
  ↓ (~50ms network)
Neovim receives and displays
  ↓
User sees red squiggles
```

### Timeout Configuration

```
documentAnalysisTimeoutMs: 30000
  ↓
If analysis takes >30 seconds
  ├─ Kill analyzer execution
  ├─ Return partial diagnostics
  ├─ Log timeout error
  └─ User sees incomplete diagnostics

Common timeout triggers:
├─ Very large files (100,000+ lines)
├─ Slow machine
├─ Too many concurrent analyzers
└─ Network/filesystem delays (WSL2)
```

### AnalyzeOpenDocumentsOnly Performance Impact

**False (recommended for style checking):**
```
Files analyzed: ALL in solution (~500 files)
Analyzer runs per file: 1 time each
Total analyzer runs: ~500
Time impact: ~15-30 seconds total

Benefit: Comprehensive StyleCop coverage
Drawback: Slower overall response
```

**True (recommended for large projects):**
```
Files analyzed: Only open in editor (1-5 files typically)
Analyzer runs per file: 1 time each
Total analyzer runs: ~5
Time impact: ~1-5 seconds total

Benefit: Faster feedback
Drawback: Only current files checked
```

---

## Debugging Techniques

### 1. Verify Configuration Applied

**Check running process:**
```bash
ps aux | grep omnisharp | grep -v grep

# Should show command including all flattened args:
# /path/OmniSharp.dll -s /solution.sln RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
```

**Check in Neovim:**
```vim
:LspInfo
" Should show all settings under server config
```

### 2. Monitor Analyzer Execution

**Enable debug logging in OmniSharp:**
```bash
# Option 1: Command line argument
dotnet /path/OmniSharp.dll -loglevel Debug

# Option 2: Environment variable
export OMNISHARP_LOGLEVEL=Debug
```

**Option 3: omnisharp.json:**
```json
{
  "loggingLevel": "Debug"
}
```

**Watch logs:**
```bash
tail -f ~/.local/state/nvim/lsp.log | grep -i analyzer
```

### 3. Trace Diagnostic Reporting

**Look for in logs:**
```
[DEBUG] Analyzing document: /path/UserController.cs
[DEBUG] Running analyzer: StyleCop.ParameterFormattingAnalyzer
[DEBUG] Diagnostic: SA1116 at line 56, column 25
[DEBUG] Publishing 5 diagnostics for UserController.cs
```

### 4. Check if Analyzers Load

**Commands in Neovim:**
```vim
" Clear cache (stale config often the problem)
:!rm -rf ~/.cache/nvim/luac/

" Kill processes
:!pkill -f omnisharp

" Restart LSP
:LspRestart

" Check :messages for startup logs
:messages
```

### 5. Verify Solution Loading

**In logs, look for:**
```
[INFO] Loading solution: /path/to/solution.sln
[INFO] Loaded project: VDEK.DCSP.WebHost.csproj
[INFO] Loaded project: VDEK.DCSP.Core.csproj
[INFO] Loaded project: VDEK.DCSP.Tests.csproj
[INFO] All projects loaded, compilation created
```

### 6. Test Analyzer Directly

**Manual test with dotnet CLI:**
```bash
cd /path/to/Backend
dotnet build /p:reportanalyzer=true

# Shows analyzer performance and which ran
```

### 7. Compare Configurations

**Before (not working):**
```bash
ps aux | grep omnisharp
# Output: dotnet /path/OmniSharp.dll -z --hostPID ...
# Missing: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

**After (working):**
```bash
ps aux | grep omnisharp
# Output: dotnet /path/OmniSharp.dll -s /solution.sln \
#         RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
```

---

## Common Debugging Scenarios

### Scenario 1: Settings Not Applied

**Problem:** `RoslynExtensionsOptions = {}` in `:LspInfo`

**Debugging steps:**
1. Check init.lua has settings table ✓
2. `ps aux | grep omnisharp` - are args included? ✗
3. Clear cache: `rm -rf ~/.cache/nvim/luac/`
4. Kill omnisharp: `pkill -f omnisharp`
5. Restart Neovim
6. Retry `ps` check

**Root causes found:**
- Stale bytecode cache (90% of cases)
- Settings not in servers table (9%)
- nvim-lspconfig version mismatch (1%)

### Scenario 2: Analyzers Not Running

**Problem:** No StyleCop warnings appear

**Debugging steps:**
1. Verify `EnableAnalyzersSupport=true` in process ✓
2. Verify StyleCop.Analyzers NuGet installed ✓
3. Check solution loads: logs say "Loaded 3 projects" ✓
4. But diagnostics section empty: `diagnostics: []` ✗

**Likely cause:** Analyzer timeout exceeded

**Fix:**
```json
{
  "RoslynExtensionsOptions": {
    "DocumentAnalysisTimeoutMs": 60000
  }
}
```

### Scenario 3: Cross-Project References Unresolved

**Problem:** Types from other projects show red squiggles

**Debugging steps:**
1. Check `-s` parameter in process
2. Logs show "Loaded 1 project" (should be 3) ✗

**Root cause:** Solution path not provided

**Fix:**
```lua
cmd = {
  'dotnet',
  '/path/OmniSharp.dll',
  '-s', '/path/to/COMPLETE_SOLUTION.sln',  -- Not single project!
}
```

### Scenario 4: WSL2 NuGet Cache Issues

**Problem:** Works in Windows, not in WSL

**Debugging steps:**
1. Verified same `omnisharp.json` ✓
2. Verified `-s` path points to WSL path ✓
3. But compilation fails: "cannot resolve types" ✗

**Root cause:** NuGet cache out of sync between Windows and WSL

**Fix:**
```bash
cd /path/to/solution
dotnet restore --force-evaluate --no-cache

pkill -f omnisharp
# Restart Neovim
```

---

## Complete Example: Debugging StyleCop Issue

**Symptom:** User opens C# file, no StyleCop SA1116 warning appears, but

 `dotnet build` shows it.

**Investigation:**

```bash
# Step 1: Check running process
ps aux | grep omnisharp | grep -v grep

# Result:
# dotnet /path/OmniSharp.dll -z --hostPID 12345 --languageserver
# Missing: RoslynExtensionsOptions:EnableAnalyzersSupport=true
# Problem found!

# Step 2: Check init.lua
cat ~/.config/nvim/init.lua | grep -A 10 "omnisharp ="

# Result:
# omnisharp = {
#   cmd = { "OmniSharp" },  # Wrong! Should be full path
#   settings = {
#     RoslynExtensionsOptions = {
#       EnableAnalyzersSupport = false  # FALSE! Should be true
#     }
#   }
# }
# Multiple problems!

# Step 3: Fix init.lua
# Change EnableAnalyzersSupport = true
# Change cmd to full dotnet path

# Step 4: Clear cache
rm -rf ~/.cache/nvim/luac/

# Step 5: Kill OmniSharp
pkill -f omnisharp

# Step 6: Restart Neovim
nvim /path/to/file.cs

# Step 7: Verify
ps aux | grep omnisharp

# Result:
# dotnet /path/OmniSharp.dll -s /solution.sln \
# RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
# Configuration applied!

# Step 8: Open file and wait for diagnostics
# After 1-2 seconds, SA1116 warning appears in gutter
# Success!
```

---

## Conclusion

The complete diagnostic flow involves:

1. **Configuration** - Settings flow through 5 layers to reach analyzers
2. **Initialization** - LSP handshake establishes capabilities
3. **Document Sync** - Changes transmitted to OmniSharp
4. **Semantic Analysis** - Roslyn re-parses and re-compiles
5. **Analyzer Execution** - StyleCop and other analyzers run
6. **Diagnostic Collection** - OmniSharp gathers results
7. **LSP Transmission** - Formatted diagnostics sent to editor
8. **Display** - Editor shows warnings to user

Missing or misconfigured settings at step 1 cause the entire chain to fail silently.

