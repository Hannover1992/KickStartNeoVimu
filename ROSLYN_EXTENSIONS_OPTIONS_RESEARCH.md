# RoslynExtensionsOptions Research & Documentation

**Research Date**: 2025-11-13
**Source**: dotnet/roslyn, OmniSharp/omnisharp-roslyn repositories + Microsoft Learn

---

## Table of Contents

1. [Overview](#overview)
2. [What Are RoslynExtensionsOptions](#what-are-roslynextensionsoptions)
3. [Key Configuration Options](#key-configuration-options)
4. [Roslyn Analyzers Architecture](#roslyn-analyzers-architecture)
5. [How OmniSharp Uses RoslynExtensionsOptions](#how-omnisharp-uses-roslynextensionsoptions)
6. [Configuration Examples](#configuration-examples)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting](#troubleshooting)

---

## Overview

`RoslynExtensionsOptions` is a configuration section in OmniSharp that controls how Roslyn analyzers, refactorings, and code actions behave. It's **not a core Roslyn feature**, but rather an **OmniSharp-specific configuration** that extends Roslyn's capabilities in language server environments.

**Key Relationship**:
- **Roslyn** = .NET Compiler Platform (analyzers, refactorings, code fixes)
- **OmniSharp** = Language Server (provides IDE features via LSP to editors)
- **RoslynExtensionsOptions** = Configuration for how OmniSharp exposes Roslyn features

When you configure OmniSharp in Neovim, you're configuring how the language server presents Roslyn's capabilities to your editor.

---

## What Are RoslynExtensionsOptions

### Purpose

`RoslynExtensionsOptions` configures Roslyn-powered features in OmniSharp:
- **Analyzer execution** - Whether and how to run code analyzers (e.g., StyleCop)
- **Performance tuning** - Parallelization, timeouts, and scope (all files vs. open files)
- **Feature availability** - Import completion, decompilation support, inlay hints
- **Custom analyzers** - Location paths for third-party analyzer DLLs

### Configuration Scope

Can be configured at three levels:

1. **Global** (machine-wide):
   - Windows: `%USERPROFILE%\.omnisharp\omnisharp.json`
   - Linux/Mac: `~/.omnisharp/omnisharp.json`

2. **Workspace/Project** (team-shared):
   - File: `omnisharp.json` in repository root
   - Committed to version control, shared with team

3. **LSP Settings** (editor-specific):
   - Passed via LSP client configuration (e.g., Neovim init.lua)
   - Used in this project

### How OmniSharp Loads Configuration

OmniSharp reads configuration in this order (first match wins):
1. Command-line arguments
2. Environment variables (prefixed with `OMNISHARP_`, using `:` as path delimiter)
3. Local `omnisharp.json` in workspace
4. Global `~/.omnisharp/omnisharp.json`
5. LSP settings from client
6. Built-in defaults

---

## Key Configuration Options

### Core Analyzer Settings

#### `enableAnalyzersSupport` (Default: `true`)

**What it does**:
- Enables/disables Roslyn analyzer execution
- When disabled: only refactorings work, no diagnostics

**Impact on StyleCop**:
- Must be `true` for StyleCop warnings to appear
- Without this, `dotnet build` shows warnings but editor doesn't

**Type**: Boolean
**Recommendation**: Set to `true` for full analyzer support

**In Neovim Config**:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- Essential for StyleCop!
  },
}
```

---

#### `enableImportCompletion` (Default: `true`)

**What it does**:
- Adds unimported types to IntelliSense completion
- When you type a class name that isn't imported, suggests it
- Automatically adds the `using` directive when you select it

**Performance Impact**:
- First completion session after opening solution may be slower
- Subsequent completions are cached and fast

**Use case**:
- Helpful for discovering available types
- Can be disabled if completion is too slow

**Type**: Boolean
**Recommendation**: `true` (enable for better DX)

**In Neovim Config**:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableImportCompletion = true,
  },
}
```

---

#### `analyzeOpenDocumentsOnly` (Default: `false`)

**What it does**:
- When `true`: Analyzers only run on files you currently have open
- When `false`: Analyzers run on all files in the solution

**Performance Impact** (Very significant!):
- Roslyn solution: 18 minutes (all files) vs. 1 minute (open only) = **18x faster**
- Smaller solutions: Still noticeable improvement
- Tradeoff: You won't see warnings in unopened files

**Use case**:
- `true` for large solutions (better IDE responsiveness)
- `false` if you want comprehensive analysis of entire solution
- Large teams: Use `true`, run full analysis in CI/CD only

**Type**: Boolean
**Recommendation**:
- Set to `true` for large solutions
- Set to `false` for small projects where full analysis is desired

**In Neovim Config**:
```lua
settings = {
  RoslynExtensionsOptions = {
    AnalyzeOpenDocumentsOnly = false,  -- Analyze all files
    -- OR
    AnalyzeOpenDocumentsOnly = true,   -- Analyze only open files (faster)
  },
}
```

---

#### `documentAnalysisTimeoutMs` (Default: `30000`)

**What it does**:
- Maximum milliseconds OmniSharp will spend analyzing a single document
- Prevents analyzer hangs from blocking indefinitely

**Value**: Time in milliseconds

**Use cases**:
- Default (30000 = 30 seconds) works for most projects
- Increase if you have complex analyzers that need more time
- Decrease if analyzers frequently timeout

**Type**: Integer
**Recommendation**: `30000` (default)

**In Neovim Config**:
```lua
settings = {
  RoslynExtensionsOptions = {
    DocumentAnalysisTimeoutMs = 30000,  -- 30 seconds per document
  },
}
```

---

#### `diagnosticWorkersThreadCount` (Default: `8` or 75% of available cores)

**What it does**:
- Number of parallel worker threads running analyzers
- Higher = faster but uses more CPU
- Setting to `1` = sequential analysis (slower but predictable)

**Value**: Positive integer

**Examples**:
- `1` - Sequential (one file at a time)
- `4` - 4 parallel workers
- `0` - Default (75% of available cores)

**Type**: Integer
**Recommendation**: Leave default (`0`) for automatic optimization

**In Neovim Config**:
```lua
settings = {
  RoslynExtensionsOptions = {
    DiagnosticWorkersThreadCount = 0,  -- Auto (75% of cores)
  },
}
```

---

#### `locationPaths` (Default: `[]` empty array)

**What it does**:
- Specifies custom file paths to analyzer DLLs
- Allows loading analyzers from custom locations (outside NuGet)

**Use case**:
- Company-specific analyzers packaged as DLLs
- Custom Roslynator or static analysis tools
- Rarely needed in modern .NET (NuGet is standard)

**Type**: Array of strings (file paths)
**Recommendation**: Leave empty (analyzers auto-discovered from NuGet)

**In Neovim Config**:
```lua
settings = {
  RoslynExtensionsOptions = {
    LocationPaths = {},  -- Auto-discover from NuGet packages
    -- OR
    LocationPaths = {
      "/opt/custom-analyzers/MyAnalyzer.dll",
    },
  },
}
```

---

#### `enableDecompilationSupport` (Default: `true`)

**What it does**:
- Enables ILSpy-powered decompilation
- "Go to Definition" works on compiled code (no source)

**Impact**:
- Minor performance cost (cached after first use)
- Useful for exploring .NET framework source or third-party binaries

**Type**: Boolean
**Recommendation**: `true` (enable unless you have strict restrictions)

**In Neovim Config**:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableDecompilationSupport = true,
  },
}
```

---

#### `inlayHintsOptions`

**What it does**:
- Controls inline type/parameter hints displayed in code
- Example: Shows inferred type of `var` declarations

**Sub-options**:
- `enableForParameters` - Show parameter names in method calls
- `enableForTypes` - Show inferred types for `var` declarations
- `enableForLiteralParameters` - Show hints for literal parameters
- And many more fine-grained options

**Type**: Object with boolean properties
**Recommendation**: Use defaults (all enabled) for better IDE experience

**In Neovim Config**:
```lua
settings = {
  RoslynExtensionsOptions = {
    InlayHintsOptions = {
      EnableForParameters = true,
      EnableForTypes = true,
    },
  },
}
```

---

## Roslyn Analyzers Architecture

### What Are Roslyn Analyzers?

Analyzers are .NET tools that inspect code at **compile time** (and at **edit time** with IDE integration) to find issues:

**Built-in examples**:
- IDE0001 - Naming conventions (PascalCase, camelCase, etc.)
- IDE0005 - Unused imports
- CA1822 - Methods that don't use instance data

**Third-party packages**:
- **StyleCop.Analyzers** - Style & formatting rules (SA11xx, SA13xx, etc.)
- **Roslynator.Analyzers** - Coding style rules
- **AsyncFixer** - Async/await best practices
- **xUnit.Analyzers** - xUnit test patterns

### How Analyzers Work

**1. Analyzer Architecture**

```
Code in Editor
    ↓
Roslyn Compiler Platform
    ├─ Syntax Tree (code structure)
    ├─ Semantic Model (meaning, types, symbols)
    └─ Symbol Information (class/method/variable metadata)
    ↓
DiagnosticAnalyzer (inherits from abstract base class)
    ├─ SupportedDiagnostics (list of rules this analyzer checks)
    ├─ Initialize() (registers actions to run)
    └─ Actions (syntax/semantic/compilation analysis)
    ↓
Diagnostic (warning/error object)
    ↓
IDE (displays squiggly lines, light bulb fixes)
```

**2. Analyzer Discovery Process**

When you open a solution in OmniSharp:

```
Open Solution
    ↓
Read .csproj files
    ├─ Find <PackageReference> entries
    └─ Find <Analyzer> references
    ↓
Look in NuGet cache folders
    ├─ Default: ~/.nuget/packages/
    └─ Extract analyzers/dotnet/cs/*.dll
    ↓
Create AnalyzerFileReference objects
    ├─ Point to analyzer DLL paths
    └─ Load analyzer types via reflection
    ↓
Instantiate DiagnosticAnalyzer classes
    ├─ Call Initialize() on each
    └─ Register callbacks for syntax/semantic events
    ↓
Queue all documents for analysis
    ├─ Analysis workers pick up documents
    └─ Analyzers run as you type
```

**3. Analyzer Execution Flow**

```
1. Document is opened or modified
    ↓
2. CSharpDiagnosticWorkerWithAnalyzers processes document
    ├─ Check: Is enableAnalyzersSupport=true?
    ├─ Check: Is analyzeOpenDocumentsOnly=true?
    │   └─ If true: Skip closed documents
    └─ Queue document for analysis
    ↓
3. Analysis workers (DiagnosticWorkersThreadCount threads)
    ├─ Get next document from queue
    ├─ Start cancellation token (DocumentAnalysisTimeoutMs)
    ├─ Build Roslyn Compilation (syntax + semantics)
    └─ Run all registered analyzers
    ↓
4. Each analyzer inspects code
    ├─ StyleCop checks naming conventions
    ├─ Roslynator checks code style
    └─ Reports violations as Diagnostic objects
    ↓
5. Diagnostics sent to LSP client (Neovim)
    ├─ Display as squiggly underlines
    ├─ Show in diagnostics list
    └─ Offer code fixes (light bulb)
    ↓
6. User can accept fix or ignore warning
```

### Analyzer Package Structure

NuGet analyzer packages follow a standard layout:

```
StyleCop.Analyzers.1.1.118/
├── lib/
│   ├── netstandard2.0/
│   └── other frameworks...
├── analyzers/
│   └── dotnet/
│       └── cs/
│           └── StyleCop.Analyzers.dll        ← Analyzer DLL
│           └── StyleCop.Analyzers.CodeFixes.dll
└── [other files]
```

**Critical**: OmniSharp looks for analyzers at `analyzers/dotnet/cs/` not in `lib/`!

---

## How OmniSharp Uses RoslynExtensionsOptions

### Configuration Flow

**Step 1: Configuration Loading**

```lua
-- Neovim LSP configuration (init.lua)
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
      DocumentAnalysisTimeoutMs = 30000,
      DiagnosticWorkersThreadCount = 0,
    },
  },
}
```

**Step 2: LSP Server Receives Settings**

OmniSharp receives settings via LSP `workspace/didChangeConfiguration` notification:

```
Neovim sends:
{
  "settings": {
    "omnisharp": {
      "RoslynExtensionsOptions": {
        "enableAnalyzersSupport": true,
        ...
      }
    }
  }
}
```

**Step 3: Configuration Parsing**

OmniSharp parses settings and creates `RoslynExtensionsOptions` object:

```csharp
// In OmniSharp.Services (pseudo-code)
var options = new RoslynExtensionsOptions
{
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false,
    DocumentAnalysisTimeoutMs = 30000,
    DiagnosticWorkersThreadCount = 0,
    LocationPaths = new List<string>(),
};
```

**Step 4: Analyzer Discovery**

When projects are loaded, OmniSharp:

1. Reads MSBuild project files (`.csproj`)
2. Extracts `<PackageReference>` entries (e.g., `StyleCop.Analyzers`)
3. Looks in NuGet cache for `analyzers/dotnet/cs/` folder
4. Loads analyzer DLLs via reflection

**Step 5: Worker Initialization**

`CSharpDiagnosticWorkerWithAnalyzers` starts with configuration:

```csharp
// In OmniSharp (pseudo-code)
public class CSharpDiagnosticWorkerWithAnalyzers
{
    private readonly RoslynExtensionsOptions _options;

    public CSharpDiagnosticWorkerWithAnalyzers(RoslynExtensionsOptions options)
    {
        _options = options;

        // Start worker threads
        for (var i = 0; i < _options.DiagnosticWorkersThreadCount; i++)
            Task.Run(() => Worker());
    }
}
```

**Step 6: Document Analysis**

For each document:

```csharp
bool canDoFullAnalysis =
    _options.RoslynExtensionsOptions.EnableAnalyzersSupport  // true?
    && (
        !_options.RoslynExtensionsOptions.AnalyzeOpenDocumentsOnly  // analyze all?
        || _workspace.IsDocumentOpen(document.Id)  // or is this document open?
    );

if (canDoFullAnalysis)
{
    // Run all analyzers on this document
    using var cts = new CancellationTokenSource(
        _options.RoslynExtensionsOptions.DocumentAnalysisTimeoutMs);

    var diagnostics = await compilation.GetDiagnosticsAsync(
        cancellationToken: cts.Token);
}
else
{
    // Only basic syntax diagnostics
    var diagnostics = syntaxTree.GetDiagnostics();
}
```

### Real Example: StyleCop in OmniSharp

**When you open a C# file:**

1. **Load Phase**:
   ```
   Project loaded → Find StyleCop.Analyzers in .csproj
   → Look for ~/.nuget/packages/stylecop.analyzers/*/analyzers/dotnet/cs/
   → Load StyleCop.Analyzers.dll
   → Call its Initialize() method
   ```

2. **Configuration Check**:
   ```
   RoslynExtensionsOptions.EnableAnalyzersSupport = true?
   → YES: Continue to analyzer setup
   → NO: Skip analyzer execution, only show refactorings
   ```

3. **Scope Decision**:
   ```
   if (AnalyzeOpenDocumentsOnly)
       Only analyze files you have open
   else
       Analyze all files in solution
   ```

4. **Analysis Execution**:
   ```
   StyleCop.Analyzers.dll runs:
   - Check naming conventions (SA1101, SA1300, SA1302, etc.)
   - Check spacing rules (SA1002, SA1008, etc.)
   - Check documentation (SA1600, SA1601, etc.)
   - Reports diagnostic for each violation
   → Diagnostic: "SA1101: Parameter 'x' should begin with lowercase letter"
   → Sent to Neovim as LSP diagnostic
   ```

5. **LSP Display**:
   ```
   Neovim receives: Diagnostic(range, severity=warning, message="SA1101...")
   → Shows squiggly line under violation
   → `:LspInfo` shows diagnostic
   → Offers code action to fix
   ```

---

## Configuration Examples

### Minimal Configuration (Just Enable Analyzers)

```lua
-- init.lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
}
```

**Effect**: Uses all defaults, analyzers run on everything

---

### High-Performance Configuration (Large Solutions)

```lua
-- init.lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      AnalyzeOpenDocumentsOnly = true,        -- ONLY open files
      DiagnosticWorkersThreadCount = 4,       -- 4 parallel workers
      DocumentAnalysisTimeoutMs = 60000,      -- 60 seconds (more time)
    },
  },
}
```

**Effect**:
- Faster IDE responsiveness (only analyze open files)
- Parallel execution (4 workers)
- More time per document (60s instead of 30s)

---

### Comprehensive Configuration (For Neovim)

```lua
-- init.lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/path/to/solution'),
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      -- Enable all analyzer features
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      EnableDecompilationSupport = true,

      -- Analysis scope: all files (set to true for large solutions)
      AnalyzeOpenDocumentsOnly = false,

      -- Performance tuning
      DocumentAnalysisTimeoutMs = 30000,
      DiagnosticWorkersThreadCount = 0,  -- Auto (75% of cores)

      -- Inlay hints (inline type information)
      InlayHintsOptions = {
        EnableForParameters = true,
        EnableForTypes = true,
      },
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
  },
}
```

---

### omnisharp.json File (Workspace/Global)

**Local (`.omnisharp/omnisharp.json` in repo root):**

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false,
    "documentAnalysisTimeoutMs": 30000,
    "diagnosticWorkersThreadCount": 0,
    "locationPaths": []
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,
    "organizeImports": true
  }
}
```

**Note**: Property names in `omnisharp.json` use camelCase, not PascalCase!

---

## Performance Considerations

### Analysis Performance Timeline

```
Opening large solution:

With AnalyzeOpenDocumentsOnly = false (Analyze all):
  Time 0s ─── Projects loading ─── 30s ─── All files analyzed ─── 5min ───── Ready

With AnalyzeOpenDocumentsOnly = true (Only open):
  Time 0s ─── Projects loading ─── 30s ───┐
             ├─ Only open file analyzed ─ 1min ─── Ready
             └─ Background analysis on others
```

### Tuning for Your Solution Size

**Small Solution (<10 projects, <100 files)**:
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  AnalyzeOpenDocumentsOnly = false,        -- Analyze all
  DiagnosticWorkersThreadCount = 0,        -- Auto
}
```
✅ Full analysis doesn't hurt

**Medium Solution (10-50 projects)**:
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  AnalyzeOpenDocumentsOnly = false,        -- Analyze all, but...
  DiagnosticWorkersThreadCount = 4,        -- Limit parallelism
  DocumentAnalysisTimeoutMs = 30000,
}
```
⚖️ Balance between analysis depth and IDE responsiveness

**Large Solution (50+ projects)**:
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  AnalyzeOpenDocumentsOnly = true,         -- Only open files!
  DiagnosticWorkersThreadCount = 2,        -- Fewer workers
  DocumentAnalysisTimeoutMs = 60000,       -- More time
}
```
⚡ Prioritize IDE responsiveness

---

### Memory Usage

**Factors**:
- More workers = more memory (parallel compilation instances)
- Larger timeouts = larger compilation cache
- All analyzers active = more DiagnosticAnalyzer instances in memory

**If memory constrained**:
```lua
DiagnosticWorkersThreadCount = 1,          -- Sequential (minimal memory)
AnalyzeOpenDocumentsOnly = true,           -- Fewer compilations
```

---

## Troubleshooting

### Problem: StyleCop Warnings Not Showing

**Checklist**:

1. ✓ `EnableAnalyzersSupport = true` in config?
   ```lua
   settings = {
     RoslynExtensionsOptions = {
       EnableAnalyzersSupport = true,  -- Must be true
     },
   }
   ```

2. ✓ StyleCop.Analyzers package in `.csproj`?
   ```xml
   <ItemGroup>
     <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
   </ItemGroup>
   ```

3. ✓ OmniSharp found the analyzer?
   ```bash
   ls ~/.nuget/packages/stylecop.analyzers/*/analyzers/dotnet/cs/
   # Should show: StyleCop.Analyzers.dll
   ```

4. ✓ Solution path correct in OmniSharp cmd?
   ```
   -s /path/to/solution/directory
   ```

5. ✓ Clear cache and restart:
   ```bash
   rm -rf ~/.cache/nvim/luac/
   pkill -f omnisharp
   # Restart Neovim
   ```

6. ✓ Check logs:
   ```
   tail -50 ~/.local/state/nvim/lsp.log | grep -i analyzer
   ```

---

### Problem: Analyzer Timeouts / "Taking Too Long"

**Solution**: Increase timeout or limit scope

```lua
-- Option 1: Give more time per document
DocumentAnalysisTimeoutMs = 60000,  -- 60 seconds instead of 30

-- Option 2: Only analyze open files
AnalyzeOpenDocumentsOnly = true,

-- Option 3: Use fewer workers
DiagnosticWorkersThreadCount = 1,
```

---

### Problem: High CPU Usage During Analysis

**Solution**: Reduce parallelism

```lua
RoslynExtensionsOptions = {
  DiagnosticWorkersThreadCount = 1,  -- Sequential analysis
  AnalyzeOpenDocumentsOnly = true,   -- Fewer files to analyze
}
```

---

### Problem: First Completion Is Slow (ImportCompletion)

**Solution**: Either accept it or disable

```lua
-- Option 1: Keep it enabled (subsequent completions are fast)
EnableImportCompletion = true,

-- Option 2: Disable if too annoying
EnableImportCompletion = false,
```

**Why**: First completion session builds cache, then it's fast.

---

## Summary

### RoslynExtensionsOptions At A Glance

| Option | Default | For StyleCop | Performance Impact |
|--------|---------|--------------|-------------------|
| `EnableAnalyzersSupport` | `true` | **Must be true** | Critical |
| `EnableImportCompletion` | `true` | No | Minor (first time) |
| `AnalyzeOpenDocumentsOnly` | `false` | No | **Major (18x for large)**|
| `DocumentAnalysisTimeoutMs` | `30000` | No | Prevents hangs |
| `DiagnosticWorkersThreadCount` | `auto (75%)` | No | **Major (CPU/Memory)** |
| `LocationPaths` | `[]` | Optional | Minimal |
| `EnableDecompilationSupport` | `true` | No | Minor (cached) |

### Recommended Configuration for Neovim

**For typical C# projects**:
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,           -- For StyleCop!
  EnableImportCompletion = true,           -- Nice to have
  AnalyzeOpenDocumentsOnly = false,        -- Full analysis
  DocumentAnalysisTimeoutMs = 30000,       -- Standard
  DiagnosticWorkersThreadCount = 0,        -- Auto
}
```

**For large solutions** (Roslyn itself, ASP.NET Core):
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  AnalyzeOpenDocumentsOnly = true,         -- ONLY open files
  DiagnosticWorkersThreadCount = 2,        -- Limit parallelism
  DocumentAnalysisTimeoutMs = 60000,       -- More time
}
```

---

## References

- **OmniSharp Configuration**: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- **Roslyn Analyzers Overview**: https://learn.microsoft.com/en-us/visualstudio/code-quality/roslyn-analyzers-overview
- **OmniSharp Source**: https://github.com/OmniSharp/omnisharp-roslyn
- **StyleCop.Analyzers**: https://github.com/DotNetAnalyzers/StyleCopAnalyzers
- **nvim-lspconfig Omnisharp**: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua

---

**Last Updated**: 2025-11-13
**Research Effort**: Web research + source code analysis from dotnet/roslyn and OmniSharp/omnisharp-roslyn
