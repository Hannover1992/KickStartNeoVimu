# StyleCop + Roslyn + OmniSharp Integration Guide

**Focus**: How StyleCop analyzer warnings appear in Neovim using RoslynExtensionsOptions

---

## What Is StyleCop?

StyleCop is a **Roslyn-based code analyzer** that enforces C# style and formatting conventions.

**Examples of StyleCop Rules**:
- **SA1101**: Parameter should begin with lowercase letter (e.g., `_parameter` not `_Parameter`)
- **SA1300**: Element should start with uppercase (e.g., `ClassName` not `className`)
- **SA1302**: Interface names should start with `I` (e.g., `IUserService`)
- **SA1402**: File may only contain one public class
- **SA1600**: Elements should be documented (/// comments)
- **SA1309**: Field names should not begin with underscore (`public field` not `_field`)

**Key Characteristic**: StyleCop rules are **Roslyn DiagnosticAnalyzers**.

---

## How StyleCop Works in Visual Studio

```
Visual Studio (Build + Editing)
  ↓
Roslyn Compiler reads code
  ├─ Parses to Syntax Tree (code structure)
  ├─ Builds Semantic Model (types, meanings)
  └─ Loads Analyzers (including StyleCop)
  ↓
StyleCop.Analyzers.dll (Roslyn DiagnosticAnalyzer)
  ├─ Initialize() registers callbacks
  ├─ Receives SyntaxTree + Semantic Model
  ├─ Runs all registered rules
  └─ Reports violations as Diagnostic objects
  ↓
Visual Studio displays squiggly lines + suggestions
  ├─ Right-click → Code Actions → Apply Fix
  └─ Save file → Runs format on save
```

**VS Code + OmniSharp**:
Same flow, but **OmniSharp acts as the language server**, providing diagnostics to VS Code over LSP.

---

## How StyleCop Works in OmniSharp (Language Server)

**Architecture**:

```
Neovim (LSP Client)
  │
  ├─ init.lua configuration
  │  └─ RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... }
  │
  └─→ LSP Protocol
      (textDocument/didOpen, textDocument/didChange, etc.)
      ↓
OmniSharp (LSP Server)
  │
  ├─ Startup: Read configuration
  │  └─ Parse RoslynExtensionsOptions
  │
  ├─ Project Loading: Read .csproj files
  │  ├─ Find <PackageReference Include="StyleCop.Analyzers" />
  │  └─ Store analyzer metadata
  │
  ├─ Analyzer Discovery: Load from NuGet cache
  │  ├─ Path: ~/.nuget/packages/stylecop.analyzers/*/
  │  ├─ Look for: analyzers/dotnet/cs/StyleCop.Analyzers.dll
  │  └─ Load via reflection into memory
  │
  ├─ Document Received: File opened/modified
  │  ├─ Queue document for analysis
  │  └─ Pass to CSharpDiagnosticWorkerWithAnalyzers
  │
  ├─ Analysis Worker (CSharpDiagnosticWorkerWithAnalyzers):
  │  │
  │  ├─ Check: EnableAnalyzersSupport = true?
  │  │  └─ NO → Skip analyzers, only syntax diagnostics
  │  │  └─ YES → Continue
  │  │
  │  ├─ Check: AnalyzeOpenDocumentsOnly = true?
  │  │  └─ YES & document closed → Skip analysis
  │  │  └─ NO or document open → Analyze
  │  │
  │  ├─ Start timer: DocumentAnalysisTimeoutMs (e.g., 30000)
  │  │
  │  ├─ Build Roslyn Compilation:
  │  │  ├─ Parse syntax tree
  │  │  ├─ Build semantic model
  │  │  └─ Create Compilation object
  │  │
  │  ├─ Run StyleCop.Analyzers on compilation:
  │  │  ├─ StyleCop.Analyzers.Initialize() called
  │  │  ├─ Analyzer checks all registered rules
  │  │  ├─ For each violation: Create Diagnostic object
  │  │  │  - Example: Diagnostic(range, "SA1101", "warning", message)
  │  │  └─ Collect all diagnostics
  │  │
  │  └─ Return: List of Diagnostic objects
  │
  ├─ Diagnostic Aggregation:
  │  ├─ Merge StyleCop diagnostics with other analyzers
  │  ├─ Merge syntax diagnostics
  │  └─ Return complete diagnostic list
  │
  └─→ LSP Protocol: textDocument/publishDiagnostics
      ↓
Neovim (LSP Client)
  │
  ├─ Receive diagnostics
  ├─ Display squiggly lines (with severity colors)
  ├─ Populate `:Telescope diagnostics`
  └─ Show on `:LspInfo`
```

---

## Critical Path: Without RoslynExtensionsOptions

**Scenario 1: `EnableAnalyzersSupport` not set or `false`**

```
CSharpDiagnosticWorkerWithAnalyzers:
  ├─ Check: EnableAnalyzersSupport = true?
  ├─ NO! → Skip StyleCop loading
  └─ Return only: Syntax tree diagnostics (no style violations)

Result: ❌ StyleCop warnings DON'T appear
        ✓ Compiler errors still show (syntax errors)
        ✓ Refactorings still work
```

**How to verify it's the problem**:

1. Open C# file in Neovim
2. Run `:LspInfo`
3. Look for analyzer count: Should show many analyzers from StyleCop
4. If shows 0 or very few analyzers: `EnableAnalyzersSupport` likely not set

---

## Critical Path: Without Correct Analysis Scope

**Scenario 2: `AnalyzeOpenDocumentsOnly = true` but file is closed**

```
CSharpDiagnosticWorkerWithAnalyzers:
  ├─ Check: AnalyzeOpenDocumentsOnly = true?
  ├─ YES
  ├─ Is this document open?
  ├─ NO → Skip full analysis
  └─ Return only: Syntax tree diagnostics

Result: ✓ StyleCop warnings appear in open files
        ❌ StyleCop warnings NOT in closed files
```

**Use case**: Large solution where you only want to analyze open files for speed.

---

## Configuration Required for StyleCop

### Minimum (Just Get It Working)

```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  -- ✓ REQUIRED
    },
  },
}
```

### Recommended (Good Balance)

```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,           -- ✓ REQUIRED for StyleCop
      EnableImportCompletion = true,           -- Bonus feature
      AnalyzeOpenDocumentsOnly = false,        -- Analyze all files
      DocumentAnalysisTimeoutMs = 30000,       -- 30 sec per file
      DiagnosticWorkersThreadCount = 0,        -- Auto (75% cores)
    },
  },
}
```

### For Large Solutions (Performance)

```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,           -- ✓ REQUIRED for StyleCop
      AnalyzeOpenDocumentsOnly = true,         -- ⚡ Only open files
      DiagnosticWorkersThreadCount = 2,        -- Limit parallelism
      DocumentAnalysisTimeoutMs = 60000,       -- More time per file
    },
  },
}
```

---

## Step-by-Step: Getting StyleCop Warnings in Neovim

### Prerequisites

1. **StyleCop.Analyzers package installed** in your project:
   ```xml
   <!-- .csproj file -->
   <ItemGroup>
    <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
   </ItemGroup>
   ```

2. **OmniSharp installed via Mason**:
   ```bash
   # In Neovim
   :MasonInstall omnisharp
   ```

3. **nvim-lspconfig configured**:
   ```lua
   -- init.lua
   require('lspconfig').omnisharp.setup { ... }
   ```

### Step 1: Configure RoslynExtensionsOptions

**File**: `~/.config/nvim/init.lua` (or `/mnt/c/Users/.../.../init.lua` if symlinked)

**Add to omnisharp setup**:

```lua
require('lspconfig').omnisharp.setup {
  cmd = { 'dotnet', ... },  -- Your existing cmd config

  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,      -- ← REQUIRED!
      AnalyzeOpenDocumentsOnly = false,   -- All files
    },
  },

  -- ... rest of config
}
```

### Step 2: Clear Cache and Restart

```bash
# Terminal
rm -rf ~/.cache/nvim/luac/        # Clear Lua bytecode cache
pkill -f omnisharp                # Kill any running OmniSharp instances
```

### Step 3: Restart Neovim

```bash
# In terminal
nvim /path/to/CSharp/File.cs
```

### Step 4: Verify

**In Neovim**:

```vim
:LspInfo
```

You should see something like:

```
Language client omnisharp (id: 1) is active for this buffer.
Server capabilities:
...
Attached buffers:
  #1 (File.cs)
...
```

**More detailed check**:

```bash
# Terminal: Check if OmniSharp is running with correct config
ps aux | grep omnisharp | grep -v grep

# Should show something like:
# dotnet /path/to/OmniSharp.dll -s /path/to/solution \
#   RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
```

### Step 5: Open a File with Known StyleCop Violations

**Example file**:

```csharp
namespace MyNamespace
{
    public class UserController  // SA1600: Should have documentation
    {
        public void ProcessUser(User User)  // SA1101: Should be lowercase 'user'
        {
            var Name = user.Name;  // SA1306: Should use _Name for field
        }
    }
}
```

**Expected result in Neovim**:
- Red/yellow squiggly underlines on violations
- Hover (K) shows: "SA1101: Parameter 'User' should begin with lowercase letter"
- `:Telescope diagnostics` lists all violations

---

## Real Example: UserController.cs

### File Content

```csharp
using System.Collections.Generic;
using System.Linq;

namespace VDEK.DCSP.WebApi.Controllers
{
    public class UserController
    {
        public void CreateUser(User User)
        {
            if (User == null) return;

            var result = Repository.AddUser(User);

            LogResult(result);
        }
    }
}
```

### StyleCop Violations Expected

Without fixing, this file would trigger:

1. **SA1600**: `UserController` class lacks documentation
   ```
   Line 6: /// <summary>... required
   ```

2. **SA1101**: Parameter `User` should be lowercase
   ```
   Line 8: public void CreateUser(User user)  // not User
   ```

3. **SA1101**: Parameter `User` should be lowercase in other methods
4. **SA1306**: Field naming conventions if you had private fields

### With RoslynExtensionsOptions Enabled

**In Neovim**:

```
Line 6: ~~~~~~~~~~~~~~~  [W] SA1600: Class must have header documentation
Line 8: ^^^^^^^        [W] SA1101: Parameter should begin with lowercase

Press K to see full message
Press <leader>ca to see code actions
```

### With RoslynExtensionsOptions Disabled

**Same file, but EnableAnalyzersSupport = false**:

```
No warnings shown!
(Compiler errors still show, but StyleCop violations disappear)
```

---

## Debugging: StyleCop Not Showing

### Checklist

```
1. Is EnableAnalyzersSupport = true?
   ✓ Check init.lua

2. Is StyleCop.Analyzers installed in project?
   ✓ Check .csproj file for PackageReference

3. Is NuGet cache populated?
   ✓ Run: dotnet restore
   ✓ Check: ls ~/.nuget/packages/stylecop.analyzers/*/analyzers/dotnet/cs/

4. Is analyzer actually loaded?
   ✓ Restart: pkill -f omnisharp
   ✓ Check process: ps aux | grep omnisharp | grep EnableAnalyzersSupport

5. Is file part of solution?
   ✓ Is C# file in a project that's part of the .sln?

6. Is analysis worker running?
   ✓ Check logs: tail ~/.local/state/nvim/lsp.log | grep -i analyzer
```

### Common Issues

**Issue**: `:LspInfo` shows 0 diagnostics
**Fix**: Increase `DocumentAnalysisTimeoutMs` or check logs

**Issue**: Only syntax errors show, no StyleCop warnings
**Fix**: Verify `EnableAnalyzersSupport = true` is in settings

**Issue**: Very slow after enabling
**Fix**: Set `AnalyzeOpenDocumentsOnly = true` and reduce `DiagnosticWorkersThreadCount`

---

## Performance Impact of StyleCop

### Analysis Time Added

```
Basic syntax checking:        ~100ms per file
+ All Roslyn analyzers:       ~500ms per file
+ StyleCop specifically:      +100-200ms per file (depends on complexity)
```

**For a 100-file solution**:
- With StyleCop: ~50-70 seconds for full analysis
- Without StyleCop: ~50-60 seconds (small difference)

**For 1000-file solution**:
- With StyleCop: ~500-700 seconds (full analysis)
- With `AnalyzeOpenDocumentsOnly=true`: ~1-2 seconds (only open files)

---

## Related Settings

### FormattingOptions (Works with StyleCop)

```lua
settings = {
  RoslynExtensionsOptions = { ... },

  FormattingOptions = {
    EnableEditorConfigSupport = true,  -- Use .editorconfig rules
    OrganizeImports = true,            -- Sort using statements
  },
}
```

**Relationship to StyleCop**:
- StyleCop **detects violations** (SA11xx rules)
- FormattingOptions **automatically fixes** violations on save
- Together = Full style enforcement

---

## Summary

| Aspect | Details |
|--------|---------|
| **What**: StyleCop is a Roslyn analyzer | Checks C# style/naming conventions |
| **Why**: Makes code consistent | Everyone follows same rules |
| **How OmniSharp enables it**: RoslynExtensionsOptions.EnableAnalyzersSupport | Loads analyzer DLLs at startup |
| **Configuration key**: EnableAnalyzersSupport = true | MUST be true for warnings |
| **Performance tuning**: AnalyzeOpenDocumentsOnly | true = only open files |
| **In Neovim**: Added to init.lua settings | Passed to OmniSharp via LSP |
| **Verification**: :LspInfo shows diagnostics | Should list StyleCop violations |

---

## References

- **StyleCop.Analyzers**: https://github.com/DotNetAnalyzers/StyleCopAnalyzers
- **OmniSharp RoslynExtensionsOptions**: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- **Roslyn Analyzers Overview**: https://learn.microsoft.com/en-us/visualstudio/code-quality/roslyn-analyzers-overview
- **Full Documentation**: See `ROSLYN_EXTENSIONS_OPTIONS_RESEARCH.md`

---

**Last Updated**: 2025-11-13
