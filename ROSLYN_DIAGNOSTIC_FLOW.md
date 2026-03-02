# Roslyn Diagnostic System - Complete Flow Diagram

**Visual representation of how diagnostics are created, configured, and displayed**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ROSLYN COMPILATION                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │   Lexical    │ │   Syntax     │ │   Semantic   │
        │   Analysis   │ │   Analysis   │ │   Analysis   │
        └──────────────┘ └──────────────┘ └──────────────┘
                │             │             │
                │             │      (Performs semantic analysis,
                │             │       registers diagnostic analyzers)
                │             │             │
                ▼             ▼             ▼
        ┌────────────────────────────────────────┐
        │  Compiler Diagnostics Generated (CS)   │
        │  e.g., CS0001, CS0103, CS0219          │
        └────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
    ┌──────────┐  ┌──────────────┐  ┌──────────────┐
    │ Analyzer │  │   Analyzer   │  │   Analyzer   │
    │   Pass   │  │     Pass     │  │     Pass     │
    │   (CA)   │  │    (IDE)     │  │    (SA)      │
    └──────────┘  └──────────────┘  └──────────────┘
        │                │                │
        ▼                ▼                ▼
    ┌──────────────────────────────────────────┐
    │   Analyzer Diagnostics Generated         │
    │   e.g., CA1822, IDE0001, SA1116          │
    └──────────────────────────────────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │ Diagnostic Suppressors  │
            │ (Suppress false-pos)    │
            └─────────────────────────┘
                        │
                        ▼
    ┌────────────────────────────────────────┐
    │       Configuration Application        │
    │   1. Command-line options              │
    │   2. EditorConfig (.editorconfig)      │
    │   3. Global config (.globalconfig)     │
    │   4. MSBuild properties (.csproj)      │
    │   5. Ruleset (.ruleset - deprecated)   │
    │                                        │
    │   Result: Effective Severity Applied   │
    └────────────────────────────────────────┘
                        │
                        ▼
    ┌────────────────────────────────────────┐
    │      Final Diagnostic List             │
    │  - Compiler + Analyzer diagnostics     │
    │  - After suppressions applied          │
    │  - With effective severity levels      │
    │  - Ready for reporting                 │
    └────────────────────────────────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │  OmniSharp LSP Server   │
            │  (Converts to LSP fmt)  │
            └─────────────────────────┘
                        │
                        ▼
    ┌────────────────────────────────────────┐
    │   LSP PublishDiagnostics Notification  │
    │   - Range (line, column)               │
    │   - Message                            │
    │   - Severity (1=Error, 2=Warn, etc)    │
    │   - Code (CA1822, SA1116, etc)         │
    │   - Source ("csharp", "omnisharp")     │
    └────────────────────────────────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │  Neovim (LSP Client)    │
            │  Receives diagnostics   │
            └─────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
    ┌─────────┐   ┌──────────┐  ┌─────────────┐
    │ Squiggle│   │ Error    │  │ Statusline  │
    │ in Edit │   │ List     │  │ Updates     │
    │  (gutter)   │          │  │ Error count │
    └─────────┘   └──────────┘  └─────────────┘
```

---

## Diagnostic Analyzer Execution Flow

```
┌──────────────────────────────────────┐
│   DiagnosticAnalyzer.Initialize()    │
│   (Called once per compilation)      │
└──────────────────────────────────────┘
              │
              ▼
    ┌─────────────────────────────┐
    │  Register Analyzer Actions  │
    │                             │
    │  - CompilationStartAction   │
    │  - SyntaxTreeAction         │
    │  - SyntaxNodeAction         │
    │  - SymbolAction             │
    │  - CodeBlockAction          │
    │  - CompilationEndAction     │
    └─────────────────────────────┘
              │
    ┌─────────┴─────────────────────────────┐
    │                                       │
    ▼                                       ▼
CompilationStart         ┌──────────────────────────┐
Actions Execute          │                          │
First                    │  For each syntax node:   │
    │                    │  - SymbolStart actions   │
    │                    │  - Node analysis         │
    │                    │  - Concurrent ok here   │
    │                    │                          │
    │                    │  SymbolEnd actions       │
    │                    └──────────────────────────┘
    │                              │
    │                    ┌─────────┴──────────┐
    │                    │                    │
    │              ┌─────▼────┐        ┌─────▼────┐
    │              │  Code    │        │CodeBlock │
    │              │  Blocks  │        │ End Actn │
    │              └──────────┘        └──────────┘
    │                                        │
    └────────────────────────────────────────┤
                                             │
                                    ┌────────▼────────┐
                                    │CompilationEnd   │
                                    │Actions Execute  │
                                    │Last             │
                                    └─────────────────┘
                                             │
                                             ▼
                        ┌────────────────────────────────┐
                        │ context.ReportDiagnostic()     │
                        │ Called when violation found    │
                        └────────────────────────────────┘
```

---

## Severity Configuration Priority

```
                    HIGHEST PRIORITY
                         │
                         ▼
            ┌───────────────────────────┐
            │  Command-Line Options     │
            │  dotnet build -p:...      │
            │  /nowarn, /warnaserror    │
            └───────────────────────────┘
                         │
                    (OVERRIDES ALL BELOW)
                         │
                         ▼
            ┌───────────────────────────┐
            │  EditorConfig Files       │
            │  .editorconfig            │
            │  (Deeper = Higher)        │
            └───────────────────────────┘
                         │
                    (OVERRIDES ALL BELOW)
                         │
                         ▼
            ┌───────────────────────────┐
            │  Global Analyzer Config   │
            │  .globalconfig            │
            │  (Higher level = Higher)  │
            └───────────────────────────┘
                         │
                    (OVERRIDES ALL BELOW)
                         │
                         ▼
            ┌───────────────────────────┐
            │  MSBuild Properties       │
            │  .csproj / .props         │
            │  EnforceCodeStyleInBuild  │
            │  AnalysisMode             │
            └───────────────────────────┘
                         │
                    (OVERRIDES BELOW)
                         │
                         ▼
            ┌───────────────────────────┐
            │  Ruleset Files (Legacy)   │
            │  .ruleset                 │
            │  (Deprecated)             │
            └───────────────────────────┘
                         │
                    (OVERRIDES BELOW)
                         │
                         ▼
            ┌───────────────────────────┐
            │  DiagnosticDescriptor     │
            │  DefaultSeverity (in code)│
            │  isEnabledByDefault       │
            └───────────────────────────┘
                         │
                    LOWEST PRIORITY
```

---

## Configuration Application Example

```
Diagnostic: CA1822 (Mark members as static)
DefaultSeverity in DiagnosticDescriptor: Warning

Configuration files (in order):
┌─────────────────────────────────────┐
│ .csproj (MSBuild)                   │
│ <AnalysisMode>Recommended</...>     │
│ (Enables CA1822)                    │
└─────────────────────────────────────┘
                ↓
         (CA1822 enabled)
                ↓
┌─────────────────────────────────────┐
│ .globalconfig                       │
│ is_global = true                    │
│ global_level = 1                    │
│ [No CA1822 setting]                 │
└─────────────────────────────────────┘
                ↓
         (Still Warning)
                ↓
┌─────────────────────────────────────┐
│ /path/to/project/.editorconfig      │
│ [*.cs]                              │
│ dotnet_diagnostic.CA1822.severity = │
│ suggestion                          │
└─────────────────────────────────────┘
                ↓
         (Override to Suggestion!)
                ↓
┌─────────────────────────────────────┐
│ Command-line option                 │
│ dotnet build -p:...                 │
│ (No override for CA1822)            │
└─────────────────────────────────────┘
                ↓
RESULT: Effective Severity = Suggestion
        (Blue squiggle in Neovim)
```

---

## DiagnosticAnalyzer to LSP Message Conversion

```
DiagnosticAnalyzer
┌────────────────────────────────────┐
│ Registers SyntaxNodeAction         │
│ for MethodDeclarationSyntax        │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Detects violation:                 │
│ "UserService.GetName() can be      │
│  static"                           │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Creates Diagnostic using           │
│ DiagnosticDescriptor:              │
│                                    │
│ id: "CA1822"                       │
│ title: "Mark members as static"    │
│ severity: Warning                  │
│ location: Line 42, Column 15       │
│ message: "GetName can be static"   │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ context.ReportDiagnostic()         │
│ (Diagnostic added to collection)   │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Configuration Applied:             │
│ .editorconfig has:                 │
│ dotnet_diagnostic.CA1822.severity  │
│ = suggestion                       │
│                                    │
│ Severity changed: Warning→Sugg.    │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ OmniSharp LSP Server processes:    │
│ Converts severity levels:          │
│ - Error → LSP DiagnosticSeverity.1 │
│ - Warning → .2                     │
│ - Suggestion → .3 (Neovim custom)  │
│ - Hidden → .4 (Neovim custom)      │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ LSP PublishDiagnostics sent:       │
│                                    │
│ {                                  │
│   "uri": "file:///...Service.cs",  │
│   "diagnostics": [                 │
│     {                              │
│       "range": {                   │
│         "start": {line:42,char:15},│
│         "end": {...}               │
│       },                           │
│       "severity": 3,               │
│       "message": "GetName...",     │
│       "code": "CA1822",            │
│       "source": "csharp"           │
│     }                              │
│   ]                                │
│ }                                  │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│ Neovim LSP Client receives &       │
│ processes message                  │
└────────────────────────────────────┘
         │
    ┌────┴────┐
    │          │
    ▼          ▼
Blue line   Error list
(squiggle)  updated
at 42:15    with CA1822
```

---

## Configuration File Hierarchy (Project Root to Parent)

```
/home/user/projects/
├── .editorconfig (Level 0 - highest)
│
├── MyCompany/
│   ├── .editorconfig (Level 1)
│   │
│   └── Backend/
│       ├── .editorconfig (Level 2)
│       ├── .globalconfig
│       ├── Solution.sln
│       │
│       └── CoreService/
│           ├── CoreService.csproj
│           ├── UserService.cs ← File being analyzed
│           └── Program.cs
```

**For UserService.cs**, configuration applied in order:

```
1. /home/user/projects/MyCompany/Backend/.editorconfig
   (Closest to file - HIGHEST PRIORITY)

2. /home/user/projects/MyCompany/Backend/.globalconfig

3. /home/user/projects/MyCompany/.editorconfig

4. /home/user/projects/.editorconfig
   (Furthest from file - LOWEST PRIORITY)

Later values override earlier ones (closer = higher priority)
```

---

## IDE Display Mapping

```
Roslyn Severity  │ LSP Value │ Neovim Display
─────────────────┼───────────┼────────────────────────
Error            │ 1         │ Red squiggle: ~^
Warning          │ 2         │ Yellow squiggle: ~^
Info/Suggestion  │ 3         │ Blue squiggle: ~^
Hidden           │ 4         │ No display (info only)
─────────────────┴───────────┴────────────────────────

Location in Editor:
┌─────────────────────────────────────┐
│  public void GetName()~^~ {         │
│             ^^^^^ Blue squiggle      │
│                                     │
│ :LspInfo shows:                     │
│ - Message: "GetName can be static"  │
│ - Code: CA1822                      │
│ - Severity: Suggestion              │
└─────────────────────────────────────┘

Error List (if opened):
┌──────────────────────────────────┐
│ CA1822: GetName can be static    │
│ UserService.cs(42, 15)           │
│ Severity: Suggestion             │
└──────────────────────────────────┘
```

---

## Concurrent Execution Model

```
CompilationStart Actions
         │
         ▼
    ┌────────┐
    │ SERIAL │ (No concurrency)
    └────────┘
         │
         ▼
    ┌────────────────────┐
    │ Symbol Actions     │
    │ (Can be parallel   │
    │  if explicitly     │
    │  enabled)          │
    │                    │
    │ Constraint:        │
    │ SymbolStart → ...  │
    │           → SymEnd │
    └────────────────────┘
         │
         ▼
    ┌────────┐
    │ SERIAL │ (Compilation end)
    └────────┘


// To enable concurrency:
context.EnableConcurrentExecution();

// Then actions can run in parallel:
Task 1: Analyze Class A ────┬──┐
Task 2: Analyze Class B ──┬─┼──┐
Task 3: Analyze Class C ──┼─┼──┐
                          └─┴──┴─> Join
```

---

## Diagnostic Suppressor Flow

```
Compiler & Analyzer Diagnostics Generated
         │
         ▼
  ┌──────────────────┐
  │ Diagnostic List: │
  │ - CS0219         │
  │ - CA1822         │
  │ - SA1116         │
  └──────────────────┘
         │
         ▼
  ┌──────────────────────────┐
  │ DiagnosticSuppressor     │
  │ subclass runs            │
  │                          │
  │ Evaluates each           │
  │ diagnostic:              │
  │ - Is suppressible?       │
  │ - Does context match?    │
  │ - Should suppress?       │
  └──────────────────────────┘
         │
    ┌────┴─────────────────┐
    │                      │
    ▼ (Yes, suppress)      ▼ (No, keep)

  Suppression.Create()    Diagnostic remains
  (Adds SP0001 record)    in final list
         │
    ┌────┴──────┬──────┐
    │           │      │
    ▼           ▼      ▼
Final        Audit    User
Diagnostic   Trail    Control
List                  (config,
(suppressed           /nowarn)
removed)
```

---

## Real-World: StyleCop + OmniSharp + Neovim

```
User opens C# file in Neovim
         │
         ▼
┌──────────────────────────┐
│ Neovim connects to       │
│ OmniSharp LSP server     │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ OmniSharp loads:         │
│ - Solution file (-s arg) │
│ - .editorconfig          │
│ - StyleCop.Analyzers pkg │
│ - RoslynExtensionsOptions│
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Roslyn compiles & runs:  │
│ - Compiler passes        │
│ - StyleCop analyzer      │
│ - CA code quality        │
│ - IDE code style         │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Diagnostics generated:   │
│ SA1116 (params aligned)  │
│ CA1822 (mark static)     │
│ IDE0001 (simplify names) │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ .editorconfig applied:   │
│                          │
│ SA1116 → Error           │
│ CA1822 → Warning         │
│ IDE0001 → None (hidden)  │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Final Diagnostics:       │
│ - SA1116 (Error)         │
│ - CA1822 (Warning)       │
│ - IDE0001 (Hidden)       │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ OmniSharp sends LSP      │
│ PublishDiagnostics msg   │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Neovim displays:         │
│                          │
│ Line 42: red squiggle    │
│          (SA1116 error)  │
│                          │
│ Line 50: yellow squiggle │
│          (CA1822 warning)│
│                          │
│ IDE0001 hidden           │
│ (not shown)              │
└──────────────────────────┘
```

---

## Troubleshooting Flow

```
User sees no StyleCop warnings in Neovim
         │
         ▼
    Check 1: Analyzer Enabled?
    ┌───────────────────────────┐
    │ :LspInfo → look for:      │
    │ RoslynExtensionsOptions { │
    │   EnableAnalyzersSupport=? │
    │ }                         │
    └───────────────────────────┘
         │
    YES  │  NO → Enable in init.lua
    ─────┴──  and restart
         │
         ▼
    Check 2: .editorconfig exists?
    ┌───────────────────────────┐
    │ ls -la project/.editorconfig
    │ Check it has SA1116 entry │
    └───────────────────────────┘
         │
    YES  │  NO → Create .editorconfig
    ─────┴──  with StyleCop rules
         │
         ▼
    Check 3: Rule not disabled?
    ┌───────────────────────────┐
    │ grep "SA1116" .editorconfig
    │ Check severity != none    │
    └───────────────────────────┘
         │
    GOOD │  BAD → Change severity
    ─────┴──  to warning/error
         │
         ▼
    Check 4: Roslyn support?
    ┌───────────────────────────┐
    │ ps aux | grep omnisharp   │
    │ Check for:                │
    │ RoslynExtensions:Enable=  │
    │ true                      │
    └───────────────────────────┘
         │
    YES  │  NO → Config not applied
    ─────┴──  :LspRestart
         │
         ▼
    ✓ Should see StyleCop warnings!
```

---

**Document Created**: 2025-11-13
**Status**: Complete Diagrams
