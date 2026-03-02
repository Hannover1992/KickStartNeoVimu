# RoslynExtensionsOptions - Quick Reference Guide

**TL;DR**: Configuration for Roslyn analyzers (like StyleCop) in OmniSharp language server.

---

## Minimal Configuration (Copy-Paste)

### For Neovim init.lua

```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,           -- REQUIRED for StyleCop!
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,        -- Analyze all files
      DocumentAnalysisTimeoutMs = 30000,
      DiagnosticWorkersThreadCount = 0,        -- Auto (75% cores)
    },
  },
}
```

### For omnisharp.json (Global or Workspace)

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false,
    "documentAnalysisTimeoutMs": 30000,
    "diagnosticWorkersThreadCount": 0
  }
}
```

**Note**: `omnisharp.json` uses `camelCase`, not `PascalCase`

---

## Options Explained

### EnableAnalyzersSupport ✓ **CRITICAL for StyleCop**

```lua
EnableAnalyzersSupport = true,  -- Must be true for StyleCop warnings
```

- `true` = Run analyzers (StyleCop, Roslynator, etc.)
- `false` = Only refactorings work, no warnings/errors

**StyleCop Check**: If SA11xx warnings don't show, this is usually the problem.

---

### EnableImportCompletion

```lua
EnableImportCompletion = true,  -- Show unimported types in completion
```

- `true` = IntelliSense suggests types you haven't imported yet
- `false` = Only show already-imported types

**Effect**: First completion session is slightly slower, but helpful.

---

### AnalyzeOpenDocumentsOnly ⚡ **Performance Critical**

```lua
AnalyzeOpenDocumentsOnly = false,  -- Analyze all files
-- OR
AnalyzeOpenDocumentsOnly = true,   -- Analyze only open files (faster)
```

**Performance**: Can be 18x faster for large solutions!

| Setting | Scope | Speed | Use Case |
|---------|-------|-------|----------|
| `false` | All files | 📊 Full | Small/medium projects |
| `true` | Open files only | ⚡ Fast | Large solutions (50+) |

---

### DocumentAnalysisTimeoutMs

```lua
DocumentAnalysisTimeoutMs = 30000,  -- 30 seconds per file (in ms)
```

- Prevents analyzer hangs from blocking forever
- Default `30000` (30 seconds) is fine for most projects
- Increase if complex analyzers need more time

**Range**: 10000-120000 reasonable

---

### DiagnosticWorkersThreadCount

```lua
DiagnosticWorkersThreadCount = 0,  -- Auto (75% of CPU cores)
```

- `0` = Automatic (75% of available cores)
- `1` = Sequential (one file at a time, lowest memory)
- `4` = 4 parallel workers
- `8` = 8 parallel workers

**Tradeoff**: More workers = faster but more CPU/memory

---

### LocationPaths

```lua
LocationPaths = {},  -- Custom analyzer DLL paths
```

- Usually leave empty
- Auto-discovers analyzers from NuGet packages
- Only use if loading custom analyzer DLLs from non-standard locations

---

### EnableDecompilationSupport

```lua
EnableDecompilationSupport = true,  -- Enable ILSpy decompilation
```

- `true` = "Go to Definition" works on compiled code (no source)
- `false` = Can't jump into .NET framework or binary libraries

---

## Presets for Different Solution Sizes

### Small Solution (<10 projects)

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  AnalyzeOpenDocumentsOnly = false,
  DiagnosticWorkersThreadCount = 0,
}
```

✅ **Fast enough**, full analysis.

---

### Medium Solution (10-50 projects)

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  AnalyzeOpenDocumentsOnly = false,
  DiagnosticWorkersThreadCount = 4,
  DocumentAnalysisTimeoutMs = 30000,
}
```

⚖️ **Balance** between analysis depth and responsiveness.

---

### Large Solution (50+ projects, Roslyn itself)

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  AnalyzeOpenDocumentsOnly = true,         -- KEY: Only open files!
  DiagnosticWorkersThreadCount = 2,        -- Reduce parallelism
  DocumentAnalysisTimeoutMs = 60000,       -- More time per file
}
```

⚡ **Fast IDE**, but warnings only in open files.

---

### Memory-Constrained Setup

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  AnalyzeOpenDocumentsOnly = true,         -- Fewer compilations
  DiagnosticWorkersThreadCount = 1,        -- Sequential only
  DocumentAnalysisTimeoutMs = 30000,
}
```

💾 **Minimal memory** usage.

---

## Verification Checklist

### StyleCop Not Showing Warnings?

1. ✓ Is `EnableAnalyzersSupport = true`?
2. ✓ Is `StyleCop.Analyzers` in your `.csproj`?
   ```xml
   <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
   ```
3. ✓ Clear cache and restart:
   ```bash
   rm -rf ~/.cache/nvim/luac/
   pkill -f omnisharp
   # Restart Neovim
   ```
4. ✓ Check `:LspInfo` - see any warnings listed?
5. ✓ Run `ps aux | grep omnisharp` - is it running?

---

### High CPU / Slow IDE?

```lua
-- Try this:
AnalyzeOpenDocumentsOnly = true,      -- Only open files
DiagnosticWorkersThreadCount = 1,     -- Sequential
DocumentAnalysisTimeoutMs = 60000,    -- More time
```

---

## How StyleCop + RoslynExtensionsOptions Work

**The Chain**:

```
Neovim Config (init.lua)
  ↓
OmniSharp LSP Server
  ├─ Reads RoslynExtensionsOptions
  ├─ Loads StyleCop.Analyzers from NuGet
  ├─ Starts diagnostic workers
  └─ Analyzes files as you edit
  ↓
StyleCop Analyzer (DiagnosticAnalyzer)
  ├─ Checks naming (SA1101, SA1300, etc.)
  ├─ Checks spacing (SA1002, SA1008, etc.)
  ├─ Checks documentation (SA1600, etc.)
  └─ Reports violations
  ↓
Roslyn Diagnostic (warning/error)
  ↓
LSP Client (Neovim)
  ├─ Shows squiggly line
  ├─ Lists in `:LspInfo`
  └─ Offers code actions to fix
```

**Without `EnableAnalyzersSupport = true`**:
The analyzer never runs, so no warnings appear.

---

## Configuration Locations (Priority Order)

1. **Command-line args** (OmniSharp startup)
2. **Environment variables** (prefixed `OMNISHARP_`)
3. **Local `omnisharp.json`** in workspace root (project-level)
4. **Global `~/.omnisharp/omnisharp.json`** (machine-level)
5. **LSP settings** from client (Neovim)
6. **Built-in defaults**

---

## Environment Variables (Advanced)

```bash
# Enable analyzers via environment variable
export OMNISHARP_RoslynExtensionsOptions__EnableAnalyzersSupport=true

# Note: Use double underscores __ for nested properties, : also works
export OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

---

## Common Problems

| Problem | Cause | Solution |
|---------|-------|----------|
| StyleCop warnings not showing | `EnableAnalyzersSupport` not set | Set to `true` |
| Slow IDE / High CPU | Too many parallel workers | Set `DiagnosticWorkersThreadCount = 1-2` |
| Analyzer timeout | Complex analyzers | Increase `DocumentAnalysisTimeoutMs` |
| Slow on large solution | Analyzing all files | Set `AnalyzeOpenDocumentsOnly = true` |
| IntelliSense slow first time | Import completion | Normal, subsequent are fast |
| Out of memory | Too many workers + large solution | Reduce `DiagnosticWorkersThreadCount`, enable `AnalyzeOpenDocumentsOnly` |

---

## Key Takeaways

1. **StyleCop needs `EnableAnalyzersSupport = true`** ✓
2. **`AnalyzeOpenDocumentsOnly` is the #1 performance lever** ⚡
3. **Use `DiagnosticWorkersThreadCount = 1-2` for stability** 💪
4. **Always clear cache after config changes**: `rm -rf ~/.cache/nvim/luac/`
5. **Increase timeout if analyzers are complex**: `DocumentAnalysisTimeoutMs`

---

## Reference

- **Full Documentation**: See `ROSLYN_EXTENSIONS_OPTIONS_RESEARCH.md`
- **OmniSharp Wiki**: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- **StyleCop.Analyzers**: https://github.com/DotNetAnalyzers/StyleCopAnalyzers

---

**Last Updated**: 2025-11-13
