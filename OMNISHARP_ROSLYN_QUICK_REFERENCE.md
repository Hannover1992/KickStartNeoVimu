# OmniSharp + Roslyn: Quick Reference Guide

**Purpose**: Quick lookup for OmniSharp developers and LSP users
**Audience**: Developers using OmniSharp in Neovim, VS Code, Emacs, etc.

---

## Quick Start: Enable StyleCop Warnings

### Method 1: omnisharp.json

Create `~/.omnisharp/omnisharp.json`:
```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,
    "organizeImports": true
  }
}
```

### Method 2: Environment Variables

```bash
export OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=true
export OMNISHARP_RoslynExtensionsOptions:EnableImportCompletion=true
export OMNISHARP_RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
export OMNISHARP_FormattingOptions:EnableEditorConfigSupport=true
export OMNISHARP_FormattingOptions:OrganizeImports=true
```

### Method 3: Neovim Configuration

In `init.lua`:
```lua
omnisharp = {
  cmd = { "dotnet", vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', "-s", "/path/to/solution" },
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
  },
},
```

---

## Configuration Quick Reference

### RoslynExtensionsOptions

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `enableAnalyzersSupport` | bool | false | Enable Roslyn analyzer diagnostics (SA1xxx, CA1xxx) |
| `enableImportCompletion` | bool | false | Add unimported types to IntelliSense |
| `analyzeOpenDocumentsOnly` | bool | true | Only analyze current file (faster, less complete) |
| `enableRoslynAnalyzers` | bool | false | General Roslyn analyzer support |
| `analysisBudget` | int | 1000 | Timeout for analyzer execution (ms) |
| `diagnosticWorkerThreadCount` | int | 1 | Parallel diagnostic analysis threads |
| `locationPaths` | string[] | [] | Custom analyzer locations |

### FormattingOptions

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `enableEditorConfigSupport` | bool | false | Use .editorconfig rules |
| `organizeImports` | bool | true | Sort using statements |
| `newLine` | string | "\n" | Line ending (Windows: "\r\n", Unix: "\n") |
| `indentSize` | int | 4 | Spaces per indent level |
| `useTabs` | bool | false | Use tabs instead of spaces |

---

## Diagnostic Sources

When `enableAnalyzersSupport=true`, OmniSharp displays diagnostics from:

### 1. Compiler Errors (CS1xxx)
```
CS1002: ; expected
CS0103: Name 'x' does not exist
```
**Always enabled**, from Roslyn compilation.

### 2. Semantic Warnings (CS4xxx)
```
CS4014: Task not awaited
```
**Always enabled**, from Roslyn semantic analysis.

### 3. Analyzer Diagnostics (SA1xxx, CA1xxx, etc.)
```
SA1116: Parameters should be on same line or all different lines
CA1707: Identifiers should not contain underscores
```
**Only when `enableAnalyzersSupport=true`**, from discovered NuGet packages.

### Configuration Impact

| `enableAnalyzersSupport` | `analyzeOpenDocumentsOnly` | Result |
|---|---|---|
| false | any | Only compiler errors (CS1xxx) |
| true | false | All diagnostics from all project files |
| true | true | All diagnostics but only for open files |

---

## Command-Line Usage

### Start OmniSharp Server

```bash
# Basic
dotnet /path/to/OmniSharp.dll -s /path/to/solution

# With LSP protocol
dotnet /path/to/OmniSharp.dll -s /path/to/solution --lsp

# With logging
dotnet /path/to/OmniSharp.dll -s /path/to/solution -loglevel Information

# With configuration
OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=true \
dotnet /path/to/OmniSharp.dll -s /path/to/solution --lsp
```

### Verify Diagnostics Running

```bash
# Check if OmniSharp process includes analyzer settings
ps aux | grep omnisharp | grep -v grep

# Should contain:
# RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

### Clear Cache and Restart

```bash
# Kill OmniSharp
pkill -f omnisharp

# Clear Lua bytecode (Neovim)
rm -rf ~/.cache/nvim/luac/

# Clear Roslyn cache
rm -rf ~/.omnisharp/cache

# Restart editor and open C# file
nvim /path/to/file.cs
```

---

## Troubleshooting

### Problem: No Analyzer Diagnostics Appearing

**Check 1**: Verify configuration is applied
```vim
:LspInfo
" Look for: RoslynExtensionsOptions { EnableAnalyzersSupport = true }
```

**Check 2**: Verify process has correct parameters
```bash
ps aux | grep omnisharp | grep -v grep
# Should show: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

**Check 3**: Check if analyzers are in project
```bash
# In project directory
dotnet build
# Look for "warning SA1116" or similar in output
```

**Solution**:
```bash
# 1. Add analyzer NuGet package
dotnet add package StyleCop.Analyzers

# 2. Create/update ~/.omnisharp/omnisharp.json with enableAnalyzersSupport=true

# 3. Kill and restart OmniSharp
pkill -f omnisharp
rm -rf ~/.cache/nvim/luac/

# 4. Restart editor and open C# file
nvim project/file.cs

# 5. Wait for OmniSharp to load (30-60 seconds for large projects)

# 6. Run :LspRestart if still no diagnostics
```

### Problem: OmniSharp Slow or Hanging

**Causes**:
- `analyzeOpenDocumentsOnly=false` on large projects
- Too many analyzers installed
- `diagnosticWorkerThreadCount` too high

**Solutions**:
```json
{
  "RoslynExtensionsOptions": {
    "analyzeOpenDocumentsOnly": true,
    "analysisBudget": 500,
    "diagnosticWorkerThreadCount": 1
  }
}
```

### Problem: Incompatible Analyzer Versions

**Symptom**: Analyzer diagnostics not appearing for specific rules

**Solution**:
1. Check project `.csproj` for analyzer version
2. Update to match OmniSharp's Roslyn version (see compatibility table)
3. Run `dotnet restore --force-evaluate --no-cache`

---

## Roslyn Version Compatibility

**Find your OmniSharp version:**
```bash
~/.local/share/nvim/mason/bin/OmniSharp --version
# or
dotnet /path/to/OmniSharp.dll --version
```

| OmniSharp | Roslyn | Notes |
|---|---|---|
| v1.39.15-beta | 5.1.0 | Latest pre-release, C# 13 support |
| v1.39.14 | 4.14.0 | Latest stable |
| v1.39.x | 4.x.x | Modern versions |
| v1.38.x | 4.x.x | Current stable track |
| v1.37.x | 4.x.x | Older stable |
| v1.32.18+ | 3.x.x | Legacy with LSP support |

**Update OmniSharp:**
```bash
# Via Mason (Neovim)
:MasonToolsUpdate

# Via direct download
# See https://github.com/OmniSharp/omnisharp-roslyn/releases

# Via Chocolatey (Windows)
choco upgrade omnisharp
```

---

## LSP Diagnostic Severity Mapping

| LSP Severity | Roslyn Severity | Display |
|---|---|---|
| 1 (Error) | Error | Red squiggle, ❌ in gutter |
| 2 (Warning) | Warning | Yellow squiggle, ⚠️ in gutter |
| 3 (Information) | Info | Blue squiggle, ℹ️ in gutter |
| 4 (Hint) | Hidden | Subtle dot, 💡 light bulb |

---

## Performance Tips

### For Large Projects (1000+ files)

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "analyzeOpenDocumentsOnly": true,
    "analysisBudget": 300,
    "diagnosticWorkerThreadCount": 1
  },
  "MSBuild": {
    "projectLoadTimeout": 5000
  }
}
```

### For Fast Iteration (Development)

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "analyzeOpenDocumentsOnly": false,
    "analysisBudget": 1000,
    "diagnosticWorkerThreadCount": 2
  }
}
```

### For Memory-Constrained Systems

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": false,
    "analyzeOpenDocumentsOnly": true,
    "diagnosticWorkerThreadCount": 1
  }
}
```

---

## Analyzer Discovery

### Where OmniSharp Finds Analyzers

1. **NuGet Packages** in project `.csproj`
   ```xml
   <ItemGroup>
     <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
     <PackageReference Include="Roslynator" Version="4.x.x" />
   </ItemGroup>
   ```

2. **Global analyzers** in omnisharp.json
   ```json
   {
     "RoslynExtensionsOptions": {
       "locationPaths": ["./analyzers", "/global/analyzers/path"]
     }
   }
   ```

3. **Built-in compiler diagnostics** (always)

### Popular Analyzers with OmniSharp

| Package | Purpose | Example Rules |
|---------|---------|---|
| StyleCop.Analyzers | Naming, spacing, documentation | SA11xx, SA12xx |
| Roslynator | Code quality, refactoring | RCS1xxx |
| AsyncFixer | Async/await best practices | AsyncFixer001 |
| Security.CodeAnalysis | Security issues | CA5xxx |

---

## Useful LSP Key Bindings

| Key | Action | Command |
|-----|--------|---------|
| `]d` | Next diagnostic | Jump to next issue |
| `[d` | Previous diagnostic | Jump to previous issue |
| `K` | Hover documentation | See error/warning details |
| `<leader>ca` | Code actions | Apply quick fix |
| `<leader>w` | All diagnostics | Telescope warning list |
| `gd` | Go to definition | Jump to definition |
| `grr` | Find references | Find usages |
| `<leader>rn` | Rename symbol | Refactor rename |

---

## Configuration File Locations

### Global (All Projects)

- **Linux/macOS**: `~/.omnisharp/omnisharp.json`
- **Windows**: `%USERPROFILE%\.omnisharp\omnisharp.json`
- **WSL**: `/home/username/.omnisharp/omnisharp.json`

### Per-Project

- **Location**: `<project-root>/omnisharp.json`
- **Overrides**: Global configuration

### Example Multi-Project Setup

```
solution/
├── omnisharp.json                 (solution-wide config)
├── MyProject/
│   └── omnisharp.json            (MyProject-specific overrides)
└── OtherProject/
    └── omnisharp.json            (OtherProject-specific overrides)
```

---

## Environment Variable Examples

**Enable all diagnostics**:
```bash
OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=true \
OMNISHARP_RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
OMNISHARP_FormattingOptions:EnableEditorConfigSupport=true \
nvim project/Program.cs
```

**Disable analyzers (compiler-only)**:
```bash
OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=false \
nvim project/Program.cs
```

**Custom analysis settings**:
```bash
OMNISHARP_RoslynExtensionsOptions:AnalysisBudget=500 \
OMNISHARP_RoslynExtensionsOptions:DiagnosticWorkerThreadCount=2 \
nvim project/Program.cs
```

---

## Testing Configuration

### Verify Configuration File Format

```bash
# Check if JSON is valid
python3 -m json.tool ~/.omnisharp/omnisharp.json

# View loaded configuration
OMNISHARP_LogLevel=Debug dotnet /path/to/OmniSharp.dll -s /path/to/solution
```

### Manual Configuration Test

1. Create simple test file:
   ```csharp
   class Test
   {
       void Method(
           int param1,
           int param2)
       {
       }
   }
   ```

2. Expected with `enableAnalyzersSupport=true`:
   - Warning SA1116: Parameters on same line or all separate lines

3. Expected with `enableAnalyzersSupport=false`:
   - No analyzer warnings (only compiler errors if any)

---

## Common Error Messages

### "No LSP client attached"

**Cause**: OmniSharp not started or LSP connection failed

**Solution**:
```bash
# Kill and restart
pkill -f omnisharp
# Wait 2 seconds
sleep 2
# Reopen Neovim
nvim /path/to/file.cs
```

### "RoslynExtensionsOptions is empty"

**Cause**: Configuration not being applied to running process

**Solution**:
```bash
# Clear cache and restart
pkill -f omnisharp
rm -rf ~/.cache/nvim/luac/ ~/.omnisharp/cache
nvim /path/to/file.cs
```

### "TimeoutException in analyzer"

**Cause**: Analyzer taking too long (slow project or buggy analyzer)

**Solution**:
```json
{
  "RoslynExtensionsOptions": {
    "analysisBudget": 300,
    "enableAnalyzersSupport": true,
    "analyzeOpenDocumentsOnly": true
  }
}
```

---

## References

**Full Documentation**: See `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md`

**Official Resources**:
- https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- https://github.com/OmniSharp/omnisharp-roslyn
- https://github.com/dotnet/roslyn

**Key Articles**:
- Roslyn Analyzers in OmniSharp and VS Code (Strathweb)
- EditorConfig Support in OmniSharp (Strathweb)
- Enabling Roslyn EditorConfig Support in Neovim (Aaron Bos)

---

**Last Updated**: November 13, 2025
**Status**: Quick reference complete and ready for daily use
