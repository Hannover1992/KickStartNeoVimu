# Roslyn Analyzer Architecture & Visual Guides

Comprehensive visual documentation of Roslyn analyzer architecture and integration points.

---

## 1. Analyzer Execution Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ Source Code (*.cs files)                                        │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Compiler                                                        │
│ ├─ Parse source → Syntax Trees (immutable AST)                │
│ └─ Resolve symbols → Semantic Model                           │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Analyzer Discovery Phase                                       │
│ ├─ Scan referenced NuGet packages                             │
│ ├─ Look for [ExportDiagnosticAnalyzer] attribute             │
│ ├─ Instantiate DiagnosticAnalyzer implementations            │
│ └─ Create Compilation context                                │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Analyzer Initialization (per compilation)                      │
│ ├─ Call Initialize(AnalysisContext) on each analyzer         │
│ ├─ Analyzer registers action callbacks:                       │
│ │  ├─ RegisterSyntaxNodeAction                               │
│ │  ├─ RegisterSymbolAction                                    │
│ │  ├─ RegisterSemanticModelAction                            │
│ │  ├─ RegisterCodeBlockStartAction                           │
│ │  ├─ RegisterCompilationStartAction                         │
│ │  └─ RegisterCompilationEndAction                           │
│ └─ Mark as initialized (guaranteed once per compilation)    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Action Execution Phase                                         │
│ └─ For each code element:                                      │
│    ├─ Traverse syntax tree, symbol table, semantic model      │
│    ├─ Invoke registered callbacks matching criteria          │
│    └─ Analyzer processes element and reports diagnostics    │
│       (e.g., "Parameter SA1116 on line 42, column 15")      │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Suppression Phase (after all analyzers)                       │
│ ├─ All suppressors (DiagnosticSuppressor) run                │
│ ├─ Each suppressor reviews reported diagnostics             │
│ ├─ Suppressors report which diagnostics to hide              │
│ └─ Results union together                                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Diagnostic Collection                                          │
│ ├─ Compiler diagnostics                                        │
│ ├─ Analyzer diagnostics (minus suppressions)                 │
│ └─ Severity assigned (Error, Warning, Info, Hidden)         │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Host Delivery (IDE / Build System / LSP)                       │
│ ├─ Visual Studio: Display squiggles, error list              │
│ ├─ Build system: Report in output, fail if Error             │
│ ├─ OmniSharp/LSP: Send via textDocument/publishDiagnostics   │
│ └─ Editor display: Show warnings, enable code fixes          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Analyzer Action Execution Order

```
Timeline of Action Execution (Hierarchical)

Compilation Start
  │
  ├─► Compilation Start Actions
  │   └─► Analyzer processes entire compilation
  │
  ├─► Symbol Start Actions (for each symbol)
  │   │
  │   ├─► Symbol Actions (analyze symbol)
  │   │
  │   ├─► Semantic Model Actions (per file)
  │   │
  │   ├─► Code Block Start Actions (for each method/property)
  │   │   │
  │   │   ├─► Syntax Node Actions (for each matching node)
  │   │   │   └─► Example: Check parameter formatting
  │   │   │
  │   │   ├─► Operation Actions (analyze semantic operations)
  │   │   │
  │   │   └─► Code Block End Actions
  │   │       └─► Analyzer aggregates block-level findings
  │   │
  │   └─► Symbol End Actions
  │       └─► Analyzer finalizes symbol analysis
  │
  └─► Compilation End Actions
      └─► Analyzer processes final compilation-wide results
```

**Key Guarantee:**
- Start actions execute BEFORE content actions
- Content actions execute BEFORE end actions
- NO guaranteed order between different action types
- Enables safe parallelization

**Concurrency Model:**
- Single analyzer's actions: NEVER concurrent (thread-safe)
- Different analyzers: CAN run concurrent (framework handles sync)

---

## 3. IDE Integration (Visual Studio / OmniSharp)

```
┌──────────────────────────────────────────────────────────────────┐
│ Integrated Development Environment (IDE)                         │
└──────────────────────────────────────────────────────────────────┘
           │
           ├─────────────────────────┬──────────────────────────┐
           │                         │                          │
           ▼                         ▼                          ▼
    ┌────────────────┐       ┌────────────────┐      ┌────────────────┐
    │ Workspace      │       │ Analyzer       │      │ Diagnostics    │
    │                │       │ Processor      │      │ Collector      │
    ├─ Projects     │       ├─ Discovery    │      ├─ Receives       │
    ├─ Documents    │       ├─ Initialization│     │  diagnostics   │
    ├─ Symbols      │       ├─ Action Reg   │      ├─ Filters by     │
    ├─ Compilation  │       ├─ Execution    │      │  severity      │
    └────────────────┘       └────────────────┘      └────────────────┘
           │                         │                          │
           └─────────────────────────┴──────────────────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────┐
            │ Editor Display                        │
            ├─ Squiggles (colored underlines)      │
            ├─ Error List window                    │
            ├─ Light Bulbs (code fixes)            │
            ├─ Hover information                    │
            └───────────────────────────────────────┘
```

---

## 4. OmniSharp/LSP Integration

```
┌─────────────────────────────────────────────────────────────────┐
│ OmniSharp Language Server                                        │
└─────────────────────────────────────────────────────────────────┘
           │
           ├─────────────────┬──────────────────┬──────────────┐
           │                 │                  │              │
           ▼                 ▼                  ▼              ▼
    ┌────────────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────┐
    │ Project Loader │ │ Analyzer    │ │ Diagnostic  │ │ LSP      │
    │                │ │ Service     │ │ Processor   │ │ Protocol │
    ├─ Load .csproj │ ├─ Discovery │ ├─ Collects   │ ├─ Sends  │
    ├─ Restore NuGt │ ├─ Read       │ │ diagnostics │ │ via      │
    ├─ Create       │ │ RoslynExt   │ ├─ Filters    │ │ textDoc/ │
    │  Compilation  │ │ Options     │ │ by config   │ │ publish  │
    └────────────────┘ ├─ Instantiate│ ├─ Respects   │ │ Diag    │
                       │ Analyzers   │ │ suppression │ └──────────┘
                       ├─ Initialize │ └──────────────┘      │
                       └─────────────┘                        ▼
                                                    ┌──────────────────┐
Configuration Sources:                             │ Editor Client    │
  ├─ omnisharp.json                               │                  │
  │  └─ RoslynExtensionsOptions                   ├─ Displays        │
  │     └─ EnableAnalyzersSupport (CRITICAL!)    │  squiggles      │
  │     └─ AnalyzeOpenDocumentsOnly               ├─ Code completion │
  ├─ .editorconfig                                ├─ Go to definition │
  │  └─ dotnet_diagnostic.SA1116.severity        ├─ Find references  │
  ├─ .ruleset files                               └─ Code actions    │
  ├─ .csproj properties                                      │
  └─ Command-line arguments                                  │
                                                            ▼
                                                   ┌──────────────────┐
                                                   │ Neovim / VS Code │
                                                   │ / Other Editor   │
                                                   └──────────────────┘
```

---

## 5. Analyzer Discovery Mechanism

```
┌─────────────────────────────────────────────────────────┐
│ Analyzer Discovery Process                              │
└─────────────────────────────────────────────────────────┘

Step 1: Locate Analyzer Packages
  ├─ Parse .csproj: <PackageReference Include="StyleCop.Analyzers" />
  ├─ NuGet package installed in: ~/.nuget/packages/
  └─ Extracted to project: bin/Debug/net6.0/.../analyzers/

Step 2: Scan Assembly Files
  ├─ Reflection on *.dll files in analyzers/ folder
  ├─ Look for [ExportDiagnosticAnalyzer("CSharp")] attribute
  └─ Find types derived from DiagnosticAnalyzer

Step 3: Create Instances
  ├─ Invoke parameterless constructor on each found type
  ├─ Each analyzer instance created
  └─ Ready for initialization

Step 4: Configuration Load
  ├─ omnisharp.json: RoslynExtensionsOptions
  ├─ .editorconfig: dotnet_diagnostic.* severity settings
  ├─ .ruleset: Rule Action (Warning, Error, None)
  └─ .csproj: AnalysisMode, EnableNETAnalyzers

Step 5: Initialization
  ├─ Call Initialize(AnalysisContext) on each analyzer
  ├─ Analyzer registers action callbacks
  └─ Guaranteed once per compilation

Result: Active Analyzers
  ├─ All discoverable analyzers instantiated
  ├─ Actions registered and ready to fire
  └─ Configuration applied for severity/suppression
```

---

## 6. DiagnosticAnalyzer Class Hierarchy

```
DiagnosticAnalyzer (Abstract Base)
│
├─► Concrete Analyzer Implementations
│   │
│   ├─ StyleCopAnalyzer (SA rules)
│   │  └─ Provided by: StyleCop.Analyzers NuGet
│   │
│   ├─ CodeQualityAnalyzer (CA rules)
│   │  └─ Provided by: Microsoft.CodeAnalysis.NetAnalyzers
│   │
│   ├─ CodeStyleAnalyzer (IDE rules)
│   │  └─ Built into: Visual Studio / OmniSharp
│   │
│   └─ Custom Analyzers
│      └─ User-written or organizational analyzers
│
└─► DiagnosticSuppressor (Special: Suppress false positives)
    │
    ├─ Runs AFTER all analyzers complete
    ├─ Can hide specific diagnostics
    └─ Example: Unity magic method suppressor
```

---

## 7. Configuration Mechanism (Precedence)

```
┌───────────────────────────────────────────────────────────┐
│ Configuration Priority (Highest to Lowest)                │
└───────────────────────────────────────────────────────────┘

Level 1 (Highest Priority): Command-Line Arguments
  ├─ dotnet build /p:EnableNETAnalyzers=true
  ├─ omnisharp -s /path/to/solution RoslynExtensionsOptions:EnableAnalyzersSupport=true
  └─ Overrides everything else

Level 2: Environment Variables
  ├─ DOTNET_ANALYZER_DIAGNOSTICS_ENABLED=true
  └─ Project-specific env vars

Level 3: omnisharp.json (LSP Configuration)
  ├─ ~/.omnisharp/omnisharp.json (global)
  ├─ /project/omnisharp.json (project-specific)
  └─ RoslynExtensionsOptions, FormattingOptions

Level 4: .editorconfig (Per-file Configuration)
  ├─ /project/.editorconfig
  ├─ dotnet_diagnostic.SA1116.severity = warning
  ├─ indent_style = space
  └─ Search up directory tree until root

Level 5: .ruleset Files (Batch Configuration)
  ├─ /project/MyRules.ruleset
  ├─ Referenced in .csproj
  ├─ <Rule Id="SA1116" Action="Warning" />
  └─ XML-based ruleset definition

Level 6: Project File (.csproj Properties)
  ├─ <EnableNETAnalyzers>true</EnableNETAnalyzers>
  ├─ <AnalysisMode>All</AnalysisMode>
  ├─ <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  └─ MSBuild properties

Level 7 (Lowest Priority): Analyzer Defaults
  ├─ DiagnosticDescriptor.DefaultSeverity
  ├─ Hardcoded in analyzer implementation
  └─ Used only if no override found
```

---

## 8. Analyzer Lifecycle States

```
Analyzer Instance Lifecycle
┌──────────────────────────────────────────────────────┐

1. Discovered
   ├─ Found via reflection in NuGet packages
   └─ Type identified: StyleCopAnalyzer : DiagnosticAnalyzer

2. Instantiated
   ├─ New instance created
   └─ Awaiting initialization

3. Initialized (per compilation)
   ├─ Initialize(AnalysisContext context) called
   ├─ Actions registered via RegisterXxxAction()
   └─ Ready to process code

4. Processing
   ├─ Actions fire as code elements encountered
   ├─ Analyzer examines syntax/symbols/semantics
   ├─ Diagnostics reported via context.ReportDiagnostic()
   └─ Can maintain internal state (for stateful analyzers)

5. Suppression Review
   ├─ Suppressors examine reported diagnostics
   ├─ Can hide false positives
   └─ Results merged with analyzer output

6. Delivery
   ├─ Diagnostics collected
   ├─ Severity applied (Error, Warning, Info)
   └─ Sent to IDE/Build System/LSP

Lifecycle can repeat for new compilations or file changes
└──────────────────────────────────────────────────────┘
```

---

## 9. Syntax Tree Traversal Example

```
Source Code:
─────────────
public void MyMethod(
    int parameter1,
    int parameter2)
{
}

Syntax Tree (Simplified):
──────────────────────
MethodDeclarationSyntax
├─ Identifier: "MyMethod"
├─ ParameterListSyntax  ◄─── SA1116 checker watches for this
│  ├─ ParameterSyntax("parameter1")
│  ├─ ParameterSyntax("parameter2")
│  └─ Location: line 1-4
└─ BlockSyntax (method body)

Analyzer Action Flow:
─────────────────────
1. RegisterSyntaxNodeAction(CheckParameterList, SyntaxKind.ParameterList)

2. Compiler encounters ParameterListSyntax

3. CheckParameterList(SyntaxNodeAnalysisContext context) invoked
   ├─ context.Node = ParameterListSyntax
   ├─ Extract parameters from context.Node
   ├─ Check if all on same line vs split across lines
   ├─ If SA1116 violation found:
   │  └─ Report diagnostic with violation details
   └─ Violation visible in editor as squiggle

4. LSP sends diagnostic to editor client:
   ├─ Location: line 1, column 26
   ├─ Message: "Parameters must be on same line or all on separate lines"
   ├─ Severity: Warning
   └─ Code: SA1116
```

---

## 10. OmniSharp Configuration for StyleCop

```
Required Configuration to Enable StyleCop in OmniSharp
═════════════════════════════════════════════════════

omnisharp.json:
┌──────────────────────────────────────────────────────┐
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,        ◄─── CRITICAL!
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,     ◄─── Load .editorconfig
    "OrganizeImports": true
  }
}
└──────────────────────────────────────────────────────┘

OR Command-Line Arguments:
┌──────────────────────────────────────────────────────┐
dotnet /path/to/OmniSharp.dll \
  -s /path/to/solution \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
  FormattingOptions:EnableEditorConfigSupport=true
└──────────────────────────────────────────────────────┘

Process Verification:
┌──────────────────────────────────────────────────────┐
ps aux | grep omnisharp

Expected output includes:
  RoslynExtensionsOptions:EnableAnalyzersSupport=true
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
  FormattingOptions:EnableEditorConfigSupport=true
└──────────────────────────────────────────────────────┘

Configuration File (.editorconfig):
┌──────────────────────────────────────────────────────┐
# Enable StyleCop rules
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1117.severity = warning
dotnet_diagnostic.SA1101.severity = warning

# Disable specific rules
dotnet_diagnostic.SA1600.severity = none
└──────────────────────────────────────────────────────┘
```

---

## 11. Complete Analysis Flow (Example: StyleCop SA1116)

```
User edits C# file:
  public void MyMethod(
      int parameter1,
      int parameter2)

Events triggered:
─────────────────
1. File changed event
   └─ OmniSharp workspace updated

2. Compiler recompiles changed file
   ├─ Parses source → MethodDeclarationSyntax
   ├─ Builds ParameterListSyntax subtree
   └─ Creates semantic model

3. Analyzer discovery
   ├─ StyleCop.Analyzers assembly loaded
   ├─ Reflects: StyleCopAnalyzer : DiagnosticAnalyzer
   └─ Instance created

4. Initialize phase
   ├─ StyleCopAnalyzer.Initialize(context) called
   ├─ Registers: RegisterSyntaxNodeAction(CheckParameterList, ParameterList)
   └─ Prepared for action invocation

5. Action execution
   ├─ Compiler traverses syntax tree
   ├─ Encounters ParameterListSyntax node
   ├─ Invokes CheckParameterList(SyntaxNodeAnalysisContext)
   ├─ Analyzer checks:
   │  ├─ Parameter1 at line 1-2
   │  ├─ Parameter2 at line 2-3
   │  └─ Spans multiple lines → Violation detected
   └─ Calls: context.ReportDiagnostic(Diagnostic.Create(...))

6. Diagnostic collection
   ├─ Diagnostic created:
   │  ├─ id: "SA1116"
   │  ├─ location: line 2, column 15
   │  ├─ message: "Parameters must be on same line or all on separate lines"
   │  ├─ severity: Warning
   │  └─ code: "SA1116"
   └─ Added to results

7. Suppression phase
   ├─ All suppressors run
   ├─ Check if SA1116 should be hidden
   └─ Result: not suppressed (SA1116 passes through)

8. LSP delivery
   ├─ Diagnostic sent via textDocument/publishDiagnostics
   ├─ JSON:
   │  {
   │    "range": { "start": { "line": 1, "character": 4 }, ... },
   │    "message": "Parameters must be on same line...",
   │    "severity": 2,
   │    "code": "SA1116"
   │  }
   └─ Sent to editor

9. Editor display
   ├─ Yellow squiggle appears on line 2
   ├─ Hover shows message
   ├─ Diagnostics panel lists violation
   └─ Light bulb offers fixes (if CodeFixProvider exists)
```

---

## Key Architecture Principles

**1. Automatic Discovery**
- No registry or configuration file needed
- Reflection-based detection of DiagnosticAnalyzer types
- Highly extensible without code changes

**2. Declarative Action Registration**
- Analyzers declare what they want to analyze
- Framework handles traversal and invocation
- Enables optimization and parallelization

**3. Immutable Data Structures**
- Syntax trees are immutable (thread-safe)
- Enables safe concurrent access
- Multiple analyzers can analyze simultaneously

**4. Hierarchical Configuration**
- Multiple configuration sources
- Command-line overrides files
- Clear precedence rules prevent surprises

**5. Extensibility Points**
- DiagnosticAnalyzer - Custom analysis logic
- DiagnosticSuppressor - Suppress false positives
- CodeFixProvider - Automated fixes
- FixAllProvider - Batch fixes

**6. Performance Optimization**
- Single compilation reused across analyzers
- Caching of results
- Incremental analysis on changes
- Optional concurrent execution

---

## References

- **Roslyn Compiler Platform**: https://github.com/dotnet/roslyn
- **Analyzer Actions Semantics**: dotnet/roslyn/docs/analyzers/Analyzer%20Actions%20Semantics.md
- **OmniSharp**: https://github.com/OmniSharp/omnisharp-roslyn
- **StyleCop.Analyzers**: https://github.com/StyleCop/StyleCop.Analyzers
