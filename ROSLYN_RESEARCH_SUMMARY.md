# RoslynExtensionsOptions Research - Executive Summary

**Research Date**: November 13, 2025
**Sources**: dotnet/roslyn, OmniSharp/omnisharp-roslyn, Microsoft Learn
**Status**: Complete

---

## Documents Created

Three comprehensive guides have been created in this directory:

1. **ROSLYN_EXTENSIONS_OPTIONS_RESEARCH.md** (Full technical reference)
   - 400+ lines
   - Architecture diagrams
   - All configuration options explained
   - Performance considerations
   - Troubleshooting guide

2. **ROSLYNEXTENSIONSOPTIONS_QUICK_REFERENCE.md** (For daily use)
   - Quick copy-paste configs
   - 4 preset configurations
   - Common problems & solutions
   - Verification checklist

3. **STYLECOP_ROSLYN_INTEGRATION.md** (StyleCop-specific)
   - How StyleCop works in OmniSharp
   - Step-by-step setup guide
   - Real examples with violations
   - Debugging guide

---

## Key Findings

### What Are RoslynExtensionsOptions?

`RoslynExtensionsOptions` is an **OmniSharp-specific configuration** (not core Roslyn) that controls:

1. **Analyzer execution** - Whether code analyzers (like StyleCop) run
2. **Performance tuning** - Parallelization, timeouts, analysis scope
3. **Feature availability** - Import completion, decompilation support
4. **Custom analyzers** - Paths to analyzer DLLs

**Critical Insight**: This is NOT a Roslyn feature, but rather how OmniSharp exposes Roslyn capabilities to LSP clients (like Neovim).

---

## Core Configuration Options

### For StyleCop to Work

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- ✓ REQUIRED! StyleCop doesn't work without this
  },
}
```

**Without this**: No StyleCop warnings appear, even if StyleCop.Analyzers is installed.

### Essential Options

| Option | Default | For StyleCop | Performance Impact |
|--------|---------|--------------|-------------------|
| `EnableAnalyzersSupport` | true | **CRITICAL** | Determines if analyzers run |
| `AnalyzeOpenDocumentsOnly` | false | Optional | **Major** (18x for large) |
| `DocumentAnalysisTimeoutMs` | 30000 | Optional | Prevents hangs |
| `DiagnosticWorkersThreadCount` | auto(75%) | Optional | CPU/Memory usage |
| `EnableImportCompletion` | true | No | Minor (first time) |
| `EnableDecompilationSupport` | true | No | Minor (cached) |

### Key Insights

1. **`EnableAnalyzersSupport`**: Must be `true` for StyleCop warnings
   - When `false`: Only refactorings work, no diagnostics
   - When `true`: All Roslyn analyzers (including StyleCop) run

2. **`AnalyzeOpenDocumentsOnly`**: Major performance lever
   - When `false`: Analyzers run on all files → comprehensive but slow
   - When `true`: Only open files → fast but incomplete analysis
   - Impact: Can be **18x faster** for large solutions (Roslyn itself: 18min vs 1min)

3. **`DiagnosticWorkersThreadCount`**: Parallelization control
   - Default (`0`): 75% of available CPU cores
   - Set to `1`: Sequential analysis (lowest memory, most stable)
   - Set to `4-8`: Balance between speed and resources

4. **`DocumentAnalysisTimeoutMs`**: Hang protection
   - Default: 30 seconds per file
   - Increase if complex analyzers timeout
   - Prevents LSP from blocking forever

---

## How StyleCop Works in OmniSharp

### The Critical Path

**WITHOUT `EnableAnalyzersSupport = true`:**
```
File opens
  → OmniSharp checks: EnableAnalyzersSupport = true?
    → NO!
      → Skip analyzer loading
      → Skip StyleCop execution
      → Return syntax diagnostics only
      → ❌ No StyleCop warnings appear
```

**WITH `EnableAnalyzersSupport = true`:**
```
File opens
  → OmniSharp checks: EnableAnalyzersSupport = true?
    → YES!
      → Load StyleCop.Analyzers.dll
      → Build compilation
      → Run StyleCop analyzer
      → StyleCop reports: "SA1101: Parameter should be lowercase"
      → ✓ Warning appears in Neovim
```

---

## Roslyn Analyzers Basics

### What Are They?

Roslyn analyzers are **.NET code analysis tools** built on the Compiler Platform that:
- Inspect code at **design time** (as you type)
- Report issues as **diagnostics** (warnings/errors/suggestions)
- Provide **code fixes** (auto-corrections via light bulb)
- Can be **custom** (company-specific rules) or **third-party** (StyleCop, Roslynator, etc.)

### Analyzer Discovery

OmniSharp discovers analyzers automatically:

1. **Read .csproj file**
   ```xml
   <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
   ```

2. **Look in NuGet cache**
   ```
   ~/.nuget/packages/stylecop.analyzers/1.1.118/
     └─ analyzers/dotnet/cs/
        ├─ StyleCop.Analyzers.dll
        └─ StyleCop.Analyzers.CodeFixes.dll
   ```

3. **Load via reflection** and queue documents for analysis

---

## Recommended Configurations

### For Small/Medium Projects (<50 files)

```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,         -- ✓ Required
      EnableImportCompletion = true,         -- Nice to have
      AnalyzeOpenDocumentsOnly = false,      -- Analyze all
      DocumentAnalysisTimeoutMs = 30000,     -- Standard
      DiagnosticWorkersThreadCount = 0,      -- Auto (75% cores)
    },
  },
}
```

**Result**: Full analysis, fast IDE responsiveness

### For Large Solutions (50+ projects)

```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,         -- ✓ Required
      AnalyzeOpenDocumentsOnly = true,       -- ⚡ Only open files
      DiagnosticWorkersThreadCount = 2,      -- Reduce parallelism
      DocumentAnalysisTimeoutMs = 60000,     -- More time per file
    },
  },
}
```

**Result**: Fast IDE, but warnings only in open files

---

## Quick Fix Checklist

To get StyleCop warnings in Neovim:

- [ ] `EnableAnalyzersSupport = true` in init.lua RoslynExtensionsOptions
- [ ] `StyleCop.Analyzers` package in .csproj
- [ ] Run `dotnet restore`
- [ ] Clear cache: `rm -rf ~/.cache/nvim/luac/`
- [ ] Kill OmniSharp: `pkill -f omnisharp`
- [ ] Restart Neovim
- [ ] Open C# file
- [ ] Check `:LspInfo` for diagnostics
- [ ] Verify process: `ps aux | grep omnisharp | grep EnableAnalyzersSupport`

---

## Summary

**RoslynExtensionsOptions** controls how OmniSharp exposes Roslyn analyzers (like StyleCop) to editors like Neovim. The key option is **`EnableAnalyzersSupport = true`** which enables analyzer execution. Without it, StyleCop warnings won't appear even if the package is installed. Other options control performance (parallelism, timeouts) and scope (all files vs. open only). For StyleCop to work: enable the option, install the package, clear cache, and restart.

---

**Research Completed**: November 13, 2025
**Total Research Effort**: Web search + source code analysis
**Documentation**: 3 comprehensive guides created
