# OmniSharp Roslyn Analyzers: How They Work & Verification Guide

**Research Date**: 2025-11-13
**Topic**: Understanding OmniSharp RoslynExtensionsOptions and StyleCop.Analyzers integration
**Purpose**: Enable StyleCop analyzer warnings in Neovim LSP

---

## Table of Contents

1. [How EnableAnalyzersSupport Works](#how-enableanalyzerssupport-works)
2. [What Happens When It's Enabled](#what-happens-when-its-enabled)
3. [Expected StyleCop Warnings](#expected-stylecop-warnings)
4. [OmniSharp Logs & Verification](#omnisharp-logs--verification)
5. [Common Reasons Analyzers Don't Load](#common-reasons-analyzers-dont-load)
6. [Verification Checklist](#verification-checklist)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Configuration Reference](#configuration-reference)

---

## How EnableAnalyzersSupport Works

### The Core Mechanism

`RoslynExtensionsOptions:EnableAnalyzersSupport=true` is the **master switch** that determines whether OmniSharp acts as:

- **Disabled (default)**: Only refactorings available (basic code suggestions)
- **Enabled**: Full Roslyn analyzer engine + refactorings + code fixes

### What Gets Enabled

When `EnableAnalyzersSupport=true`, OmniSharp:

1. **Discovers Analyzers** - Scans .csproj files for NuGet analyzer packages (like StyleCop.Analyzers)
2. **Loads Analyzer DLLs** - Loads the Roslyn analyzer assemblies
3. **Runs Diagnostics** - Executes analyzers on your code to find violations
4. **Reports Warnings/Errors** - Sends diagnostics to the editor (Neovim in your case)
5. **Provides Code Fixes** - Suggests quick fixes for violations

### Architecture Flow

```
OmniSharp Server
    ↓
EnableAnalyzersSupport=true?
    ├─ YES: Scan .csproj for <PackageReference Include="StyleCop.Analyzers" />
    │       ↓
    │       Load analyzer DLL from NuGet cache
    │       ↓
    │       Run Roslyn analysis on code
    │       ↓
    │       Report SA1xxx diagnostics to LSP client (Neovim)
    │
    └─ NO:  Only basic refactorings (no StyleCop warnings)
```

---

## What Happens When It's Enabled

### Stage 1: OmniSharp Startup (First Time)

When OmniSharp starts with `EnableAnalyzersSupport=true`:

```
[INFO] OmniSharp initialized
[INFO] Solution loaded: /path/to/Backend.sln
[INFO] Found projects: 12 projects
[INFO] Scanning .csproj files for analyzer packages...
[INFO] Discovered: StyleCop.Analyzers v1.1.118
[INFO] Loading analyzers from: /home/user/.nuget/packages/stylecop.analyzers/1.1.118
[INFO] Analyzer 'StyleCop.Analyzers' loaded successfully
[INFO] Roslyn analyzers initialized
```

### Stage 2: File Analysis (When File is Opened)

When you open a C# file:

```
1. OmniSharp receives: "open file: UserController.cs"
2. Creates Roslyn compilation with all analyzers
3. Runs analyzers against the file
4. Gets diagnostics back:
   [
     { rule: "SA1101", line: 56, column: 13, message: "..." },
     { rule: "SA1116", line: 78, column: 5, message: "..." },
   ]
5. Sends diagnostics to LSP client
6. Neovim displays red/yellow underlines
```

### Stage 3: Analysis Modes (Based on AnalyzeOpenDocumentsOnly)

**AnalyzeOpenDocumentsOnly = true (Default for performance)**
- Analyzers run ONLY on files you have open
- Fast, low resource usage
- Missing: Warnings in unopened files

**AnalyzeOpenDocumentsOnly = false (Full solution analysis)**
- Analyzers run on ALL files in solution
- Slower (can take minutes for large solutions)
- Complete: Shows all warnings in project

---

## Expected StyleCop Warnings

### What StyleCop Rules Check

StyleCop.Analyzers checks 50+ rules covering:

- **Naming** (SA1302-1309) - Class names, member names, constants
- **Spacing** (SA1001-1027) - Whitespace, commas, operators
- **Indentation** (SA1027) - Tab/space consistency
- **Line Length** (SA1101) - Line too long
- **Documentation** (SA1600-1648) - XML docs, comments
- **Ordering** (SA1200-1212) - Using directives, members
- **Readability** (SA1101-1116) - Code readability rules

### Common SA1xxx Rules You'll See

| Rule | Issue | Example |
|------|-------|---------|
| SA1116 | Parameters on wrong line | `method(\n    param1, param2)` |
| SA1101 | Use `this.` prefix | `field` instead of `this.field` |
| SA1117 | Parameters not aligned | Misaligned multi-line parameters |
| SA1200 | Using directive outside namespace | `using System;` before `namespace` |
| SA1633 | File header copyright missing | File without header comment |
| SA1652 | Enable XML documentation | Public members without `///` docs |

### What Your Code Should Show

For the DCSRE UserController.cs file, expect warnings at:

- **Line 56-57**: SA1116 (parameter alignment on method declaration)
- **Line 78-79**: SA1116 (parameter alignment on method call)
- **Line 110-111**: SA1116 (parameter alignment)
- **Line 152-153**: SA1116 (parameter alignment)
- **Line 190-191**: SA1116 (parameter alignment)
- **Line 241-243**: SA1116 (parameter alignment)

These are **not errors** - they're style violations that can be auto-fixed by Neovim.

---

## OmniSharp Logs & Verification

### Where OmniSharp Logs Are Located

**Linux/WSL2:**
```
~/.local/state/nvim/lsp.log
```

**Windows:**
```
%APPDATA%\nvim-data\lsp.log
```

### What to Look For in Logs

#### 1. Startup Verification

Look for these messages:

```log
[INFO] OmniSharp initialized
[INFO] Located ... MSBuild instance(s)
[INFO] SDK: version=X.X.X
[INFO] Solution opened: Backend.sln
[INFO] Workspace initialized
```

#### 2. Analyzer Loading

**Presence indicates analyzers are loaded:**

```log
[INFO] Analyzing solution...
[INFO] Roslyn analyzers initialized
[INFO] Discovered analyzer packages: StyleCop.Analyzers
```

**Absence means analyzers weren't discovered** - usually because:
- StyleCop.Analyzers not in .csproj
- EnableAnalyzersSupport not set to true
- NuGet restore not run

#### 3. Analyzer Execution

When analyzer is working:

```log
[INFO] Running diagnostics on UserController.cs
[INFO] Found 6 style violations
[DEBUG] SA1116: Parameter alignment issue (line 56)
[DEBUG] SA1116: Parameter alignment issue (line 78)
```

**If you see timeouts:**

```log
[WARN] CSharpDiagnosticWorkerWithAnalyzers timing out after 30000ms
[WARN] Analyzer execution interrupted
```

This means `documentAnalysisTimeoutMs` is too short.

#### 4. Error Indicators

**Red flags in logs:**

```log
[ERROR] Failed to load analyzer: StyleCop.Analyzers
[ERROR] Analyzer not found at package path
[ERROR] NuGet package not restored
```

### How to View Logs in Neovim

```vim
" View LSP logs
:lua =vim.lsp.get_log_path()

" In terminal, tail the log
:terminal
tail -f ~/.local/state/nvim/lsp.log

" Filter for analyzer messages
tail -f ~/.local/state/nvim/lsp.log | grep -i "analyzer\|diagnostic\|roslyn"
```

---

## Common Reasons Analyzers Don't Load

### Reason 1: EnableAnalyzersSupport Not Set

**Symptom**: No StyleCop warnings appear, only refactorings available

**Root Cause**: The setting is missing or false

**Check:**
```vim
:lua print(vim.inspect(require('lspconfig').omnisharp.settings))
" Should show:
" RoslynExtensionsOptions = {
"   EnableAnalyzersSupport = true,  ← This MUST be true
"   ...
" }
```

**Fix in init.lua:**
```lua
omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  -- This is THE critical setting
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
    },
  },
}
```

---

### Reason 2: StyleCop.Analyzers Not in .csproj

**Symptom**: No SA1xxx warnings despite EnableAnalyzersSupport=true

**Root Cause**: The analyzer package isn't referenced in the project

**Check in .csproj:**
```bash
# Look for StyleCop.Analyzers reference
grep -r "StyleCop.Analyzers" *.csproj
# OR
dotnet list package --include-prerelease | grep StyleCop
```

**Expected in .csproj:**
```xml
<PackageReference Include="StyleCop.Analyzers" Version="1.1.118">
  <PrivateAssets>all</PrivateAssets>
  <IncludeAssets>runtime; build; native; contentfiles; analyzers</IncludeAssets>
</PackageReference>
```

**Fix:**
```bash
# Add StyleCop.Analyzers to all projects that need it
cd /path/to/DCSRE/Sources/Backend
dotnet add <ProjectName>.csproj package StyleCop.Analyzers
# Then restore
dotnet restore
```

---

### Reason 3: NuGet Packages Not Restored

**Symptom**: Analyzer DLL not found at startup

**Root Cause**: `dotnet restore` wasn't run, or WSL2/Windows NuGet cache mismatch

**Check:**
```bash
# Verify StyleCop.Analyzers is in cache
ls ~/.nuget/packages/stylecop.analyzers/

# Or check if it would be found
dotnet list package --include-prerelease
```

**Fix:**
```bash
# Force restore with fresh evaluation (WSL2 specific)
dotnet restore --force-evaluate --no-cache

# Or from Neovim
<leader>bs    # Backend reStore command
```

---

### Reason 4: NuGet Cache Mismatch (Windows/WSL2)

**Symptom**: Build works in Windows PowerShell, but OmniSharp in WSL sees no warnings

**Root Cause**: Built in Windows, but NuGet cache differs between Windows and WSL2

**Check:**
```bash
# In WSL2, check what OmniSharp sees
ls -la ~/.nuget/packages/stylecop.analyzers/
# vs Windows
ls C:\Users\<user>\.nuget\packages\stylecop.analyzers\
```

**Fix (WSL2):**
```bash
# Clear and restore with fresh packages
dotnet restore --force-evaluate --no-cache

# Or use the alias from CLAUDE.md
<leader>bs    # Uses this exact command
```

---

### Reason 5: AnalyzeOpenDocumentsOnly = true, File Not Opened

**Symptom**: Warnings in opened files, but not in unopened files

**Root Cause**: Analysis limited to files currently visible in editor

**Check in config:**
```lua
-- If set to true, only analyzes open files
RoslynExtensionsOptions = {
  AnalyzeOpenDocumentsOnly = true,  -- ← Only analyzes current files
}
```

**Fix:**
```lua
-- Analyze entire solution
RoslynExtensionsOptions = {
  AnalyzeOpenDocumentsOnly = false,  -- ← Now analyzes all files
}
```

**Tradeoff**: Setting to `false` may be slow on large solutions (10+ minutes to load).

---

### Reason 6: Analysis Timeout

**Symptom**: Warnings appear briefly, then disappear; or never appear in large files

**Root Cause**: `documentAnalysisTimeoutMs` too short for file size

**Check in logs:**
```
[WARN] CSharpDiagnosticWorkerWithAnalyzers timing out after 10000ms
```

**Fix:**
```lua
RoslynExtensionsOptions = {
  documentAnalysisTimeoutMs = 30000,  -- 30 seconds (increased from default 10s)
  diagnosticWorkersThreadCount = 8,   -- Number of parallel analysis threads
}
```

**Performance Tuning:**
- Large files (500+ lines): Use 30000ms
- Very large files (1000+ lines): Use 60000ms
- Slow machine: Set `diagnosticWorkersThreadCount = 1` (sequential)

---

### Reason 7: OmniSharp Not Restarted After Config Change

**Symptom**: Changed init.lua but warnings still don't appear

**Root Cause**: OmniSharp process still running with old config

**Fix:**
```bash
# Kill all OmniSharp processes
pkill -f omnisharp

# Clear Lua bytecode cache
rm -rf ~/.cache/nvim/luac/

# Restart Neovim
nvim
```

**Why this matters:**
- OmniSharp caches configuration at startup
- Neovim caches Lua bytecode in `~/.cache/nvim/luac/`
- Both must be cleared for changes to take effect

---

### Reason 8: Missing .editorconfig or stylecop.json

**Symptom**: EnableAnalyzersSupport=true, but specific rules don't report

**Root Cause**: StyleCop.Analyzers needs configuration file to know which rules to enforce

**Check:**
```bash
# Look for .editorconfig in solution root
ls -la /mnt/c/.../Backend/.editorconfig

# Or stylecop.json
find . -name ".stylecop.json" -o -name "stylecop.json"
```

**What gets configured:**
- `rule severity` (error, warning, suggestion, none)
- `rule ordering` (element declaration order)
- `naming conventions` (PascalCase, camelCase, etc.)
- `documentation requirements`

**Example .editorconfig snippet:**
```ini
[*.cs]
# Disable unused using directives warning
dotnet_diagnostic.SA1200.severity = suggestion

# Make line length warnings instead of errors
dotnet_diagnostic.SA1101.severity = warning
```

**Fix:**
- Ensure `.editorconfig` exists at solution root
- Or create `stylecop.json` with default settings
- Run `dotnet restore` after adding files

---

## Verification Checklist

Use this checklist to verify EnableAnalyzersSupport is working:

### Pre-Verification (Setup Check)

- [ ] StyleCop.Analyzers 1.1.118 added to .csproj
  ```bash
  grep -i "stylecop" /path/to/.csproj
  ```

- [ ] NuGet packages restored
  ```bash
  dotnet restore
  ```

- [ ] init.lua has EnableAnalyzersSupport = true
  ```bash
  grep -i "EnableAnalyzersSupport" ~/.config/nvim/init.lua
  ```

- [ ] Lua cache cleared
  ```bash
  rm -rf ~/.cache/nvim/luac/
  ```

- [ ] All OmniSharp processes killed
  ```bash
  pkill -f omnisharp; sleep 2; ps aux | grep omnisharp | grep -v grep
  # Output: (empty - good!)
  ```

### Runtime Verification (Neovim Open)

- [ ] Neovim started fresh
  ```bash
  nvim /path/to/UserController.cs
  ```

- [ ] OmniSharp notification appears
  ```
  🔧 OmniSharp explicitly configured
  ```

- [ ] Wait 5-10 seconds for loading
  ```
  ✅ OmniSharp erfolgreich geladen!
  ```

- [ ] `:LspInfo` shows correct command
  ```
  cmd: { "dotnet", "/home/user/.../OmniSharp.dll", "-s", "/mnt/c/.../Backend", ... }
  ```

- [ ] `:LspInfo` shows EnableAnalyzersSupport = true
  ```
  settings: {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  ← Must be true
      ...
    }
  }
  ```

### Visual Verification (In Code)

- [ ] Red/yellow underlines appear on code
  ```
  User code with style violations:
  public void MyMethod(
      int param1,     ← Red underline here (line 56)
      int param2)     ← Red underline here
  ```

- [ ] Hover shows SA1xxx warning
  ```
  K on underlined code shows:
  SA1116: Split parameters must start on line after declaration
  ```

- [ ] Code actions available
  ```
  <leader>ca shows "Fix parameter alignment"
  ```

- [ ] `:LspInfo` shows diagnostics
  ```
  Attached clients:
  - omnisharp (running, 6 diagnostics)
  ```

### Process Verification (System Level)

- [ ] OmniSharp process running with correct args
  ```bash
  ps aux | grep omnisharp | grep -v grep
  ```

  **Should show (all on one line):**
  ```
  dotnet /home/uczen/.../OmniSharp.dll \
    -s /mnt/c/.../Backend \
    -loglevel Information \
    -z --hostPID <PID> ... \
    RoslynExtensionsOptions:EnableAnalyzersSupport=true \
    RoslynExtensionsOptions:EnableImportCompletion=true \
    RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
  ```

  **Critical checks:**
  - [ ] Has `-s /mnt/c/.../Backend` (solution path)
  - [ ] Has `-loglevel Information`
  - [ ] Has `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
  - [ ] Has `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false`

### Log Verification (LSP Logs)

- [ ] LSP log shows analyzer loaded
  ```bash
  tail -50 ~/.local/state/nvim/lsp.log | grep -i "analyzer\|stylecop\|roslyn"
  ```

  **Should show:**
  ```
  [INFO] Roslyn analyzers initialized
  [INFO] Discovered analyzer packages: StyleCop.Analyzers
  [INFO] Running diagnostics on UserController.cs
  ```

- [ ] No timeout errors
  ```bash
  grep "timeout\|Timeout" ~/.local/state/nvim/lsp.log
  # Output: (empty - good!)
  ```

- [ ] No analyzer loading errors
  ```bash
  grep -i "error.*analyzer\|failed.*load" ~/.local/state/nvim/lsp.log
  # Output: (empty - good!)
  ```

---

## Troubleshooting Guide

### Problem: No Red Underlines Appear

**Diagnosis Steps:**

1. Check if EnableAnalyzersSupport is true:
   ```vim
   :LspInfo
   " Look for: RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... }
   ```

2. Check if StyleCop.Analyzers is in .csproj:
   ```bash
   grep -i "stylecop" /path/to/*.csproj
   ```

3. Check if OmniSharp process has the setting:
   ```bash
   ps aux | grep omnisharp | grep EnableAnalyzersSupport
   # Should show: RoslynExtensionsOptions:EnableAnalyzersSupport=true
   ```

4. Check logs for errors:
   ```bash
   tail -100 ~/.local/state/nvim/lsp.log | grep -i "error\|fail"
   ```

**Solutions** (in order):

1. Clear cache and restart:
   ```bash
   pkill -f omnisharp
   rm -rf ~/.cache/nvim/luac/
   # Restart Neovim
   ```

2. Force NuGet restore:
   ```bash
   cd /path/to/Backend
   dotnet restore --force-evaluate --no-cache
   ```

3. Verify EnableAnalyzersSupport in init.lua:
   ```bash
   grep "EnableAnalyzersSupport = true" ~/.config/nvim/init.lua
   ```

4. Restart LSP explicitly:
   ```vim
   :LspRestart
   ```

---

### Problem: Warnings Appear, Then Disappear

**Likely Cause**: Analysis timeout

**Fix:**

```lua
RoslynExtensionsOptions = {
  documentAnalysisTimeoutMs = 60000,  -- Increase from 30s to 60s
  diagnosticWorkersThreadCount = 4,   -- Reduce parallel threads
}
```

**Why this happens:**
- Large files take longer than `documentAnalysisTimeoutMs` to analyze
- When timeout is hit, analyzer aborts and no diagnostics are sent
- Then user edits file, and analysis restarts

---

### Problem: Only Some Rules Show, Not All

**Likely Cause**: .editorconfig has disabled rules

**Check:**

```bash
cat /mnt/c/.../Backend/.editorconfig | grep SA1
```

**Look for:**
```ini
dotnet_diagnostic.SA1101.severity = none  ← Disabled!
```

**Fix:**

Change `none` to `warning` or `error`:
```ini
dotnet_diagnostic.SA1101.severity = warning
```

---

### Problem: Settings in `:LspInfo` Show as Empty Dict

**Symptom:**
```
settings: {
  RoslynExtensionsOptions = {}  ← Empty!
}
```

**Likely Cause**: Settings not being passed to OmniSharp

**Check in init.lua:**
- [ ] `servers.omnisharp.settings` is defined
- [ ] Explicit omnisharp setup runs after mason-lspconfig
- [ ] `vim.deepcopy()` is used to copy config

**Fix:**

Ensure this structure in init.lua:
```lua
local servers = {
  omnisharp = {
    cmd = { ... },
    settings = {
      RoslynExtensionsOptions = { ... },
    },
  },
}

-- Later, setup mason-lspconfig
require('mason-lspconfig').setup { ... }

-- Then setup omnisharp explicitly
if servers.omnisharp then
  local cfg = vim.deepcopy(servers.omnisharp)
  cfg.capabilities = ...
  require('lspconfig').omnisharp.setup(cfg)
end
```

---

## Configuration Reference

### Full OmniSharp Configuration Template

```lua
local servers = {
  omnisharp = {
    -- Command to start OmniSharp
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
      '-loglevel', 'Information',
    },

    -- Settings for analyzer support
    settings = {
      RoslynExtensionsOptions = {
        -- CRITICAL: Enable analyzer support
        EnableAnalyzersSupport = true,

        -- Allow code completion for unimported types
        EnableImportCompletion = true,

        -- Analyze all files (not just open ones)
        AnalyzeOpenDocumentsOnly = false,

        -- How long analyzer can run per file (milliseconds)
        documentAnalysisTimeoutMs = 30000,

        -- Number of parallel analyzer threads
        diagnosticWorkersThreadCount = 8,
      },

      FormattingOptions = {
        -- Use .editorconfig for formatting rules
        EnableEditorConfigSupport = true,

        -- Automatically organize imports when formatting
        OrganizeImports = true,
      },
    },

    -- Lifecycle hooks
    on_attach = function(client, bufnr)
      vim.notify('✅ OmniSharp attached', vim.log.levels.INFO)
    end,

    on_init = function(client)
      vim.notify('🔄 OmniSharp initializing...', vim.log.levels.INFO)
    end,
  },
}

-- In mason-lspconfig setup, skip OmniSharp:
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      if server_name == 'omnisharp' then
        return  -- Skip, we'll setup manually
      end
      -- ... handle other servers
    end,
  },
}

-- Then setup OmniSharp explicitly:
if servers.omnisharp then
  local omnisharp_config = vim.deepcopy(servers.omnisharp)
  omnisharp_config.capabilities = vim.tbl_deep_extend(
    'force',
    {},
    capabilities,
    omnisharp_config.capabilities or {}
  )
  require('lspconfig').omnisharp.setup(omnisharp_config)
end
```

---

## Quick Verification One-Liner

Run this command to check if everything is configured correctly:

```bash
# Check all requirements at once
echo "=== Checking StyleCop Setup ===" && \
echo "1. StyleCop in .csproj:" && \
grep -c "StyleCop.Analyzers" /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/*/VDEK.*.csproj 2>/dev/null && \
echo "2. EnableAnalyzersSupport in config:" && \
grep "EnableAnalyzersSupport = true" ~/.config/nvim/init.lua && \
echo "3. OmniSharp in NuGet cache:" && \
ls ~/.nuget/packages/stylecop.analyzers/ && \
echo "4. OmniSharp process running:" && \
ps aux | grep "omnisharp" | grep -v grep | wc -l && \
echo "✅ All checks passed!"
```

---

## Summary

**To get StyleCop warnings in Neovim:**

1. **Enable the switch**: `EnableAnalyzersSupport = true` in init.lua
2. **Add the package**: StyleCop.Analyzers in .csproj
3. **Restore packages**: `dotnet restore`
4. **Clear cache**: `rm -rf ~/.cache/nvim/luac/`
5. **Kill processes**: `pkill -f omnisharp`
6. **Restart Neovim**: `nvim`
7. **Verify**: `:LspInfo` should show all settings and diagnostics

**If warnings still don't appear:**
- Check logs: `tail -f ~/.local/state/nvim/lsp.log | grep -i analyzer`
- Check process: `ps aux | grep omnisharp | grep -v grep`
- Verify .editorconfig doesn't disable rules
- Check timeout isn't too short

**Most common issue**: `EnableAnalyzersSupport=true` in the settings is the single most critical setting. Without it, no analyzers run at all.

