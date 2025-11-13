# OmniSharp Solution Path (-s Parameter) Research

**Date**: 2025-11-13
**Topic**: How OmniSharp handles the `-s` parameter and project discovery
**Audience**: Neovim LSP configuration for C# development

---

## Table of Contents

1. [Quick Answer](#quick-answer)
2. [The `-s` Parameter: Detailed Analysis](#the-s-parameter-detailed-analysis)
3. [How OmniSharp Discovers Projects](#how-omnisharp-discovers-projects)
4. [lspconfig root_dir vs -s Parameter](#lspconfig-root_dir-vs--s-parameter)
5. [Configuration Hierarchy](#configuration-hierarchy)
6. [Best Practices](#best-practices)
7. [Practical Examples](#practical-examples)
8. [Troubleshooting](#troubleshooting)
9. [References](#references)

---

## Quick Answer

### Is `-s` required or optional?

**ANSWER**: The `-s` parameter is **OPTIONAL** but **HIGHLY RECOMMENDED** for proper functionality.

| Aspect | With `-s` | Without `-s` |
|--------|-----------|--------------|
| Solution/Project Detection | Finds .sln or project root | Uses current working directory |
| Project References | Works correctly | May fail |
| Multi-Solution Workspace | Fails (OmniSharp only handles 1 solution) | Works for single directory |
| IntelliSense | Full IntelliSense | Basic file-level only |
| Performance | Good (targeted analysis) | Slower (searches recursively) |
| Analyzers/Diagnostics | Works (if solution properly loaded) | May not work |

### What Happens Without `-s`?

If you **don't provide `-s`**:
1. OmniSharp uses the **current working directory** as the project root
2. It searches for `.sln`, `.csproj`, `omnisharp.json`, or `function.json` in that directory
3. If none found, it searches **recursively upward** and **downward** in the directory tree
4. It loads all discovered `.cs` files and projects
5. **Project references DON'T work properly** (can't follow cross-project imports)
6. **Solution metadata is missing** (OmniSharp needs the .sln file to understand project relationships)

### How Does OmniSharp Find .sln Without `-s`?

OmniSharp implements an **automatic discovery algorithm**:

1. **Start at working directory**: The directory where OmniSharp process was started
2. **Search upward**: Check parent directories for `.sln`, `.csproj`, `omnisharp.json`
3. **Search downward**: Recursively scan subdirectories for projects
4. **First match wins**: Loads the first solution/project found
5. **FileOptions filtering**: Uses `omnisharp.json` `fileOptions` patterns to exclude directories

**Key Issue**: Without `-s`, OmniSharp may pick the wrong project if your directory structure has multiple `.sln` files!

---

## The `-s` Parameter: Detailed Analysis

### Command Format

```bash
# Basic usage
dotnet /path/to/OmniSharp.dll -s /path/to/solution

# With additional arguments
dotnet /path/to/OmniSharp.dll -s /path/to/solution -loglevel Information
```

### What `-s` Does

**From OmniSharp Configuration Options documentation:**

The `-s` parameter specifies the **target directory or solution file** that OmniSharp should analyze.

**Behavior:**
- Accepts either a **solution file path** (`.sln`) OR a **folder path**
- OmniSharp will load all projects in that solution
- Becomes the **working directory** for the OmniSharp server
- **Must be an absolute path** (relative paths may not be resolved correctly)

### Path Types and Behavior

#### 1. Solution File Path (`-s /path/to/solution.sln`)

```bash
dotnet OmniSharp.dll -s /mnt/c/Project/DCSRE.sln
```

**Advantages:**
- OmniSharp knows exactly which projects to load
- Project references resolve correctly
- Solution metadata available (solution-level settings)
- Performance optimized (loads only specified projects)

**Behavior:**
- Loads all projects referenced in the .sln file
- Uses solution-level configuration
- Works with multi-project solutions

#### 2. Directory Path (`-s /path/to/directory`)

```bash
dotnet OmniSharp.dll -s /mnt/c/Project/Sources/Backend
```

**Advantages:**
- Works even if no .sln file exists
- Finds projects recursively
- Simpler for single-project structures

**Disadvantages:**
- Project references may not work properly
- OmniSharp must discover projects by scanning
- No solution metadata
- May be slower (recursive search)

### Command-Line Argument Format

**Important**: OmniSharp uses **flattened JSON paths** with `:` as delimiters:

```bash
# Correct format (colon separator)
dotnet OmniSharp.dll -s /path RoslynExtensionsOptions:EnableAnalyzersSupport=true

# WRONG format (won't work)
dotnet OmniSharp.dll -s /path RoslynExtensionsOptions.EnableAnalyzersSupport=true
```

**Setting Value Formats:**
- `boolean`: `true` or `false`
- `string`: `value` (no quotes needed)
- `number`: `123`
- `nested`: `Parent:Child:Property=value`

### Real-World Example

From the DCSRE project in your configuration:

```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
  '-loglevel', 'Information',
}
```

**What this does:**
1. Starts OmniSharp with dotnet runtime
2. Uses the OmniSharp.dll from Mason package cache
3. **`-s`** tells OmniSharp to analyze `/path/to/Backend` directory
4. Sets logging to Information level for debugging

---

## How OmniSharp Discovers Projects

### With `-s` Provided (Explicit Path)

```
-s /path/to/Backend
       ↓
   Look for .sln in /path/to/Backend
       ↓
   If .sln found: Load that solution
   If not: Load all .csproj files found recursively
       ↓
   Use /path/to/Backend as working directory
       ↓
   Load project references, analyzers, etc.
```

### Without `-s` (Default Discovery)

```
Start at current working directory (cwd)
       ↓
   Search upward for .sln, .csproj, omnisharp.json
       ↓
   If found: Use that directory
   If not: Search downward recursively
       ↓
   Apply fileOptions filters from omnisharp.json
       ↓
   Load discovered projects
       ↓
   ⚠️  May pick wrong solution if multiple exist!
```

### Discovery Order (With or Without `-s`)

OmniSharp searches for these markers in order:

1. **`.sln` files** (highest priority - solution files)
2. **`omnisharp.json`** (OmniSharp configuration)
3. **`.csproj` files** (project files)
4. **`function.json`** (Azure Functions)

### Exclusion Patterns

In `omnisharp.json`, you can control which directories to scan:

```json
{
  "fileOptions": {
    "excludeSearchPatterns": [
      "**/node_modules/**",
      "**/.git/**",
      "**/bin/**",
      "**/obj/**"
    ]
  }
}
```

---

## lspconfig root_dir vs -s Parameter

### How They Interact

**Two separate systems**:

1. **lspconfig `root_dir`**: Determines where Neovim will START the LSP server
2. **OmniSharp `-s` parameter**: Where OmniSharp will LOOK for projects

### lspconfig Default root_dir

```lua
root_dir = util.root_pattern('*.sln', '*.csproj', 'omnisharp.json', 'function.json')
```

**What this does:**
- Starts from the current file's directory
- Searches **upward** through parent directories
- Returns the **first directory** containing any of these markers
- **This becomes the working directory** where the LSP server process starts

### OmniSharp's root_dir Handling

**When you open a C# file:**

1. lspconfig calls `root_dir()` to find project root
2. lspconfig spawns OmniSharp process with that as working directory
3. If you **don't specify `-s`**, OmniSharp uses the working directory

**Example scenario:**

```
Project Structure:
/mnt/c/DCSRE/
├── DCSRE.sln
├── Sources/
│   ├── Backend/
│   │   ├── Backend.sln
│   │   ├── Project1.csproj
│   │   └── UserController.cs  ← You open this file
│   └── Frontend/
```

**What happens:**

1. **lspconfig searches**: From `UserController.cs` → upward
   - Finds `Backend.sln` in `Sources/Backend/`
   - Sets root_dir = `/mnt/c/DCSRE/Sources/Backend`

2. **Process starts** in that directory

3. **Without `-s`**: OmniSharp uses the working directory (`Backend/`)
   - Loads `Backend.sln` correctly ✅

4. **With `-s /mnt/c/DCSRE/Sources/Backend`**: Same result ✅

### The Problem Case

If your directory structure is:

```
/mnt/c/Project/
├── Solution.sln              ← Main solution
├── Sources/
│   └── Backend.csproj        ← Project file
```

**Opening** `Backend.csproj` file:

1. lspconfig finds `Backend.csproj` (matches pattern)
2. Sets root_dir to `Sources/` directory
3. Without `-s`, OmniSharp searches from `Sources/`
4. Never finds `Solution.sln` in parent!
5. Treats `Backend.csproj` as standalone project
6. **Project references fail** ❌

**Solution**: Provide `-s /mnt/c/Project` to explicitly point to solution root

---

## Configuration Hierarchy

OmniSharp applies settings in this **exact order** (later overrides earlier):

### 1. Hardcoded Defaults
```lua
-- Built-in defaults in OmniSharp
```

### 2. Environment Variables
```bash
export OMNISHARP_ROSLYN_EXTENSIONS_OPTIONS:ENABLE_ANALYZERS_SUPPORT=true
export OMNISHARP_FORMATTING_OPTIONS:ORGANIZE_IMPORTS=true
```

**Format**: `OMNISHARP_` prefix + flattened path with `:` delimiters

### 3. Command-Line Arguments
```bash
dotnet OmniSharp.dll -s /path \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  FormattingOptions:OrganizeImports=true
```

### 4. Global omnisharp.json
```bash
~/.omnisharp/omnisharp.json
# or Windows:
# %USERPROFILE%/.omnisharp/omnisharp.json
```

### 5. Local omnisharp.json
```bash
# In the working directory (where -s points to)
/path/to/project/omnisharp.json
```

### Example Hierarchy

If you have:

**Global** (`~/.omnisharp/omnisharp.json`):
```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": false
  }
}
```

**Command line**:
```bash
dotnet OmniSharp.dll -s /mnt/c/DCSRE/Sources/Backend \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

**Local** (`/mnt/c/DCSRE/Sources/Backend/omnisharp.json`):
```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": false
  }
}
```

**Final result**: `EnableAnalyzersSupport = false` (local wins!)

---

## Best Practices

### 1. Always Provide `-s` Parameter

**Recommendation**: Always specify `-s` with the **solution root** or **project directory**.

```lua
-- ✅ BEST: Explicit solution path
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/absolute/path/to/solution',  -- Absolute path
  },
}
```

**Why:**
- Prevents OmniSharp from guessing the wrong directory
- Ensures project references work correctly
- Guarantees solution metadata is loaded
- Provides consistent behavior across systems

### 2. Use Absolute Paths

**Never use relative paths:**

```lua
-- ❌ BAD: May not resolve correctly
'-s', './Sources/Backend',

-- ✅ GOOD: Absolute path
'-s', vim.fn.expand('/mnt/c/.../Backend'),
```

**Why**: Relative paths depend on the current working directory where Neovim is started.

### 3. Solution Root vs Backend Directory

For multi-solution projects:

```lua
-- ❌ Projects in multiple solutions won't see each other
'-s', '/mnt/c/DCSRE/Sources/Backend',

-- ✅ Points to root where main solution is
'-s', '/mnt/c/DCSRE',
```

**Decision**: Use solution root (`.sln` location) unless:
- You're working on a single isolated project
- Solution file doesn't exist
- Project is deliberately isolated

### 4. Combine with root_dir Properly

```lua
-- ✅ BEST: Use explicit -s with appropriate root_dir
omnisharp = {
  root_dir = function(fname)
    -- Find solution or project root
    return util.root_pattern('*.sln', '*.csproj')(fname)
      or vim.fn.getcwd()
  end,

  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/absolute/path/to/solution',  -- Explicit, not dependent on root_dir
  },
}
```

### 5. Settings Configuration

Apply settings in order of precedence:

```lua
omnisharp = {
  cmd = { ... },

  -- ✅ BEST: Define in Lua (most convenient)
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

  -- OR in local omnisharp.json (project-specific)
  -- OR in global ~/.omnisharp/omnisharp.json (user defaults)
}
```

### 6. Use omnisharp.json for Complex Configurations

For per-project settings:

**`/mnt/c/DCSRE/Sources/Backend/omnisharp.json`:**
```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  },
  "fileOptions": {
    "excludeSearchPatterns": [
      "**/node_modules/**",
      "**/.vs/**"
    ]
  }
}
```

---

## Practical Examples

### Example 1: Simple Single-Solution Project

**Directory Structure:**
```
/home/user/MyProject/
├── MyProject.sln
├── Project1/
│   ├── Project1.csproj
│   └── Class1.cs
└── Project2/
    └── Project2.csproj
```

**Configuration:**
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/home/user/MyProject',  -- Points to solution root
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
}
```

### Example 2: WSL2 Project with Windows Filesystem

**Directory Structure:**
```
C:\Projects\DCSRE\ (Windows)
= /mnt/c/Projects/DCSRE/ (in WSL)
├── DCSRE.sln
└── Sources/
    └── Backend/
        ├── Backend.sln (separate)
        └── VDEK.DCSP.WebApi/
            └── Controllers/
                └── UserController.cs
```

**Configuration:**
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/mnt/c/Projects/DCSRE/Sources/Backend',  -- WSL path
    '-loglevel', 'Information',
  },
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
}
```

**Why `/Sources/Backend`:**
- That's where `Backend.sln` is
- OmniSharp needs the solution metadata
- Project references inside Backend project work
- WSL path (no `C:\`) needed

### Example 3: Multiple Solutions

**Directory Structure:**
```
/mnt/c/Project/
├── Shared.sln          ← Shared services
├── WebApi.sln          ← Main API
└── Sources/
    ├── Shared/
    │   └── Shared.csproj
    └── Backend/
        └── Api.csproj
```

**When working on WebApi** (`/mnt/c/Project/WebApi`):

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/mnt/c/Project',  -- Root solution
  },
}
```

**Important**: OmniSharp can only work with **one solution at a time**. If you need both solutions loaded:
1. Create a parent `All.sln` that references both
2. Or use root directory and let OmniSharp load all projects

---

## Troubleshooting

### Problem 1: "OmniSharp could not find solution file"

**Symptom**: In `:LspInfo`, you see:
```
cmd: { "OmniSharp", "-z", "--hostPID", ... }
     ↑ Missing -s parameter!
```

**Root Cause**: The `-s` parameter is not being passed to OmniSharp.

**Solutions**:
```lua
-- Option 1: Check if cmd includes -s
:lua print(vim.inspect(require('lspconfig').omnisharp.cmd))

-- Option 2: Explicitly set cmd with -s
omnisharp = {
  cmd = {
    'dotnet',
    '/path/to/OmniSharp.dll',
    '-s', '/absolute/path/to/solution',  -- Must be absolute!
  },
}
```

### Problem 2: Wrong Project Loaded

**Symptom**: IntelliSense shows wrong namespaces, can't find references.

**Root Cause**: OmniSharp loaded the wrong project due to multiple `.sln` files.

**Solution**:
```lua
-- Be explicit about which solution to use
'-s', '/exact/path/to/correct/solution',
```

**Diagnosis**:
```bash
# Check what OmniSharp actually loaded
ps aux | grep omnisharp | grep -o "\-s [^ ]*"

# Should show the correct path
```

### Problem 3: Analyzers Not Running

**Symptom**: StyleCop warnings don't appear even though StyleCop.Analyzers is installed.

**Root Cause**: `EnableAnalyzersSupport` not set or not being passed to OmniSharp.

**Solutions**:
```lua
-- 1. Define in Lua settings
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- Must be true!
  },
}

-- 2. Or in omnisharp.json
-- 3. Check that settings are actually being passed
:lua print(vim.inspect(require('lspconfig').omnisharp.settings))

-- 4. Verify in ps output
ps aux | grep omnisharp | grep -i EnableAnalyzers
```

### Problem 4: Project References Don't Work

**Symptom**: Can't jump to definitions in other projects, "Type not found" errors.

**Root Cause**: OmniSharp is treating a `.csproj` as standalone instead of loading the solution.

**Solution**:
```lua
-- Ensure -s points to solution root with .sln file
'-s', '/path/containing/.sln/file',
```

**NOT:**
```lua
'-s', '/path/to/individual.csproj',  -- ❌ Only loads this project
```

### Problem 5: Performance Issues

**Symptom**: OmniSharp takes forever to start, CPU high.

**Root Cause**: OmniSharp is searching too broadly (no `-s` parameter).

**Solution**:
```lua
-- Provide explicit path to avoid recursive search
'-s', '/exact/path/to/solution',
```

---

## References

### Official Documentation

1. **OmniSharp Configuration Options**
   - URL: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
   - Covers all command-line arguments and settings

2. **nvim-lspconfig OmniSharp**
   - URL: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
   - Default configuration, root_dir pattern, on_new_config function

3. **OmniSharp Roslyn Repository**
   - URL: https://github.com/OmniSharp/omnisharp-roslyn
   - Source code and issue tracker

### How It Works

1. **root_dir Mechanism**
   - Neovim calls `root_dir()` when opening a C# file
   - Uses `util.root_pattern()` to find project markers
   - This becomes the LSP process working directory

2. **on_new_config Function**
   - Flattens `settings` table into command-line arguments
   - Appends hard-coded arguments (`-z`, `--hostPID`, etc.)
   - Converts nested tables to `key:value` format

3. **Configuration Priority**
   - Hardcoded defaults → Env vars → CLI args → Global omnisharp.json → Local omnisharp.json
   - Later values override earlier ones

### Key Insights

1. **The `-s` parameter is optional but essential** for proper functionality
2. **Path must be absolute**, not relative
3. **Solution root (with .sln)** is better than project directory
4. **lspconfig root_dir** controls where LSP starts, `-s` controls what OmniSharp analyzes
5. **Settings can be defined in 3 places**: Lua, omnisharp.json, environment variables
6. **Flattened JSON format** uses `:` separators, not `.` (important!)

---

## Summary Table

| Question | Answer |
|----------|--------|
| **Is `-s` required?** | Optional but highly recommended |
| **What happens without it?** | OmniSharp guesses the project from working directory |
| **Path format** | Absolute path to solution root or project directory |
| **Relative paths** | Don't work reliably; use absolute |
| **Best practice** | Always provide `-s` with absolute path to solution root |
| **Effect on discovery** | Prevents OmniSharp from searching (faster, more predictable) |
| **Project references** | Only work if `-s` points to solution root with `.sln` |
| **Settings format** | Flattened JSON with `:` separators: `Key:SubKey:Property=value` |
| **Override order** | CLI args > env vars > omnisharp.json > defaults |
| **For WSL2 users** | Use WSL paths (`/mnt/c/...`), not Windows paths (`C:\...`) |

---

**Document Version**: 1.0
**Last Updated**: 2025-11-13
**Status**: Comprehensive research complete
