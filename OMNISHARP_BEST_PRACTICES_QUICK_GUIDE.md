# OmniSharp Best Practices for Your Neovim Setup

**Quick Reference Guide for DCSRE Project Configuration**

---

## TL;DR: The Right Way to Configure OmniSharp

### ✅ CORRECT Configuration

```lua
local servers = {
  omnisharp = {
    -- 1. Explicit path to OmniSharp binary
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',

      -- 2. CRITICAL: Absolute path to solution root (where .sln is)
      '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),

      -- 3. Optional but useful: Set logging level
      '-loglevel', 'Information',
    },

    -- 4. Enable analyzers and other features
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

    -- 5. Optional: Custom root_dir detection
    root_dir = function(fname)
      return require('lspconfig.util').root_pattern('*.sln', '*.csproj')(fname)
        or vim.fn.getcwd()
    end,
  },
}

-- 6. Setup with capabilities
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

---

## Critical Configuration Points for DCSRE

### 1. The `-s` Parameter (Most Important!)

**YOUR PROJECT STRUCTURE:**
```
/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/
├── DCSRE.sln
└── Sources/
    └── Backend/                    ← You're working here
        ├── Backend.sln             ← This is the solution
        ├── VDEK.DCSP.WebApi/
        │   └── Controllers/
        │       └── UserController.cs
        ├── VDEK.DCSP.Services/
        └── [Other projects]
```

**Configuration:**
```lua
'-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
```

**Why this path:**
- ✅ Contains `Backend.sln` (the solution file)
- ✅ All backend projects are inside this directory
- ✅ OmniSharp loads project relationships correctly
- ✅ StyleCop analyzers will run
- ✅ Project references work across projects

**If you used root solution instead:**
```lua
'-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE',
```
- ⚠️ Would also work, but loads extra Frontend projects
- ⚠️ Slower startup
- ⚠️ Unnecessary for backend development

### 2. Verify the Path Exists

```bash
# In your WSL terminal, verify the path:
ls -la "/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/" | grep -E "Backend\.sln|\.csproj"

# Should output something like:
# -rw-r--r-- ... Backend.sln
# -rw-r--r-- ... VDEK.DCSP.WebApi.csproj
# etc.
```

### 3. Enable StyleCop Analyzers

**In settings:**
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,      -- Critical for StyleCop!
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false,  -- Analyze all files, not just open ones
  },
}
```

**Verify it's working:**
```bash
# In Neovim, run this to see settings:
:lua print(vim.inspect(require('lspconfig').omnisharp.settings))

# Should show:
# RoslynExtensionsOptions = {
#   EnableAnalyzersSupport = true,
#   ...
# }
```

### 4. Check the Actual Running Process

**Verify OmniSharp received your settings:**
```bash
# In terminal, run this while Neovim is open with a C# file:
ps aux | grep -i omnisharp | grep -v grep

# Should show something like:
# dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
#   -s /mnt/c/Users/.../DCSRE/Sources/Backend \
#   -loglevel Information \
#   -z --hostPID 12345 \
#   RoslynExtensionsOptions:EnableAnalyzersSupport=true \
#   RoslynExtensionsOptions:EnableImportCompletion=true \
#   ...
```

**Look for these signals that something's wrong:**
- ❌ No `-s /mnt/c/...` parameter → Solution path not being passed
- ❌ Only `-z --hostPID` → Settings not being flattened
- ❌ Missing `EnableAnalyzersSupport=true` → Analyzers won't run

---

## Testing Your Configuration

### Step 1: Check LSP Info

```vim
:LspInfo

# Look for:
# - "omnisharp" server is attached to current buffer
# - root_dir: should be a valid path
# - cmd: should start with "{ "dotnet", "
```

### Step 2: Verify Settings Are Passed

```vim
:lua
print("Current OmniSharp cmd:")
print(vim.inspect(require('lspconfig').omnisharp.cmd))
print("\nCurrent settings:")
print(vim.inspect(require('lspconfig').omnisharp.settings))
```

**Expected output:**
```
Current OmniSharp cmd:
{ "dotnet", "/home/uczen/.../OmniSharp.dll", "-s", "/mnt/c/.../Backend", "-loglevel", "Information" }

Current settings:
{
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    OrganizeImports = true
  }
}
```

### Step 3: Check Running Process

```bash
ps aux | grep omnisharp | grep -o "EnableAnalyzersSupport=[^ ]*"

# Should show: EnableAnalyzersSupport=true
```

### Step 4: Look for StyleCop Warnings

**Open a C# file:**
```bash
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs
```

**Look for red/yellow squiggly lines:**
- Lines with spacing issues (StyleCop warnings like SA1116, SA1117)
- Lines with unused imports
- Lines with naming convention issues

**If no warnings appear:**
1. Check `:LspInfo` - is omnisharp attached?
2. Run `:LspRestart` to reload
3. Check `ps aux | grep omnisharp` for the running command
4. Verify `EnableAnalyzersSupport=true` is in the process line

---

## Common Mistakes and How to Fix Them

### Mistake 1: Relative Path Instead of Absolute

❌ **WRONG:**
```lua
'-s', './Sources/Backend',
'-s', '../DCSRE/Sources/Backend',
```

**Why it fails**: Relative paths are resolved from wherever Neovim was started, not from the config file location.

✅ **CORRECT:**
```lua
'-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
```

### Mistake 2: Pointing to Project File Instead of Solution Root

❌ **WRONG:**
```lua
'-s', '/mnt/c/.../VDEK.DCSP.WebApi.csproj',  -- Points to a single project
```

**Why it fails**: OmniSharp can't see other projects in the solution, project references don't work.

✅ **CORRECT:**
```lua
'-s', '/mnt/c/.../Sources/Backend',  -- Points to solution directory
```

### Mistake 3: Not Using `vim.fn.expand()` for ~

❌ **WRONG:**
```lua
cmd = {
  'dotnet',
  '~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',  -- ~ won't expand
  '-s', '~/path/to/project',
}
```

**Why it fails**: Tilde `~` is not expanded by Lua, only by the shell.

✅ **CORRECT:**
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
}
```

### Mistake 4: Settings Not Applied

❌ **WRONG:**
```lua
omnisharp = {
  cmd = { ... },
  -- settings defined but not being passed by on_new_config
}
```

**Why it fails**: If using an old handler that overwrites the cmd, settings get lost.

✅ **CORRECT:**
```lua
omnisharp = {
  cmd = { 'dotnet', '/path/to/OmniSharp.dll', '-s', '/path' },

  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },

  -- Make sure NO additional handler overwrites this configuration
  -- Let the default lspconfig handler pass these settings
}
```

### Mistake 5: Multiple Omnisharp Setups

❌ **WRONG:**
```lua
-- In servers table:
omnisharp = { cmd = { ... }, settings = { ... } }

-- Later in mason-lspconfig handler:
omnisharp = function()
  require('lspconfig').omnisharp.setup({ cmd = { ... } })  -- Overwrites!
end
```

**Why it fails**: Can only call `lspconfig.setup()` once per server. Second call is ignored.

✅ **CORRECT:**
```lua
-- Option 1: Use servers table only
local servers = {
  omnisharp = { cmd = { ... }, settings = { ... } },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      require('lspconfig')[server_name].setup(server)
    end,
  },
}

-- Option 2: Manual setup for omnisharp only
require('mason-lspconfig').setup {
  handlers = {
    -- Skip omnisharp in default handler
    omnisharp = function() return end,

    -- Handle other servers
    function(server_name)
      ...
    end,
  },
}

-- Then set up omnisharp manually
require('lspconfig').omnisharp.setup(servers.omnisharp)
```

---

## Diagnostics Workflow

### When StyleCop Warnings Don't Show

**1. Check if analyzer is enabled:**
```vim
:lua print(require('lspconfig').omnisharp.settings.RoslynExtensionsOptions.EnableAnalyzersSupport)
# Should print: true
```

**2. Verify OmniSharp is running with the setting:**
```bash
ps aux | grep omnisharp | grep EnableAnalyzersSupport
# Should show the parameter
```

**3. Restart OmniSharp:**
```vim
:LspRestart omnisharp
```

**4. Check LSP logs:**
```bash
tail -50 ~/.local/state/nvim/lsp.log | grep -i analyzer
```

**5. Ensure StyleCop.Analyzers is installed in the project:**
```bash
# Check the csproj file
grep -i "stylecop" /mnt/c/.../VDEK.DCSP.WebApi.csproj
# Should find a PackageReference to StyleCop.Analyzers
```

**6. If still not working:**
```bash
# Full nuclear option: restart everything
pkill -f omnisharp              # Kill OmniSharp processes
rm -rf ~/.cache/nvim/luac/      # Clear Lua cache
# Then restart Neovim
```

---

## WSL2-Specific Notes

### Path Format for WSL

**Windows path:** `C:\Users\Administrator\Documents\Work\Code2\DCSRE`

**In WSL:** `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE`

**In init.lua (use WSL path):**
```lua
'-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
```

**NOT Windows path:**
```lua
'-s', 'C:\\Users\\Administrator\\Documents\\Work\\Code2\\DCSRE\\Sources\\Backend',  -- ❌ Wrong!
```

### NuGet Package Cache Issues

If OmniSharp stops working after building in PowerShell:

```bash
# In WSL, in your Backend directory:
cd /mnt/c/Users/.../DCSRE/Sources/Backend
dotnet restore --force-evaluate --no-cache

# Then restart Neovim
```

---

## Performance Optimization

### For Large Solutions

If OmniSharp is slow:

**1. Use correct `-s` path (not root directory):**
```lua
-- ✅ FAST: Points directly to backend
'-s', '/mnt/c/.../Sources/Backend',

-- ❌ SLOW: Loads frontend too
'-s', '/mnt/c/.../DCSRE',
```

**2. Exclude unnecessary directories:**
```json
{
  "fileOptions": {
    "excludeSearchPatterns": [
      "**/node_modules/**",
      "**/bin/**",
      "**/obj/**",
      "**/.vs/**"
    ]
  }
}
```

**3. Disable unnecessary analyzers:**
```json
{
  "RoslynExtensionsOptions": {
    "AnalyzeOpenDocumentsOnly": true  # Only analyze open files
  }
}
```

---

## Command Reference

### Verification Commands

```bash
# 1. Verify OmniSharp binary exists
ls -la ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

# 2. Check solution file exists
ls -la "/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/Backend.sln"

# 3. Verify OmniSharp is running with correct settings
ps aux | grep omnisharp | grep -E "\-s|EnableAnalyzers"

# 4. Check for OmniSharp errors in logs
tail -100 ~/.local/state/nvim/lsp.log | grep -i omnisharp
```

### Neovim Commands

```vim
# Show LSP info
:LspInfo

# Restart OmniSharp
:LspRestart omnisharp

# Show current OmniSharp command
:lua print(vim.inspect(require('lspconfig').omnisharp.cmd))

# Show current settings
:lua print(vim.inspect(require('lspconfig').omnisharp.settings))

# Show diagnostics
:lua print(vim.inspect(vim.diagnostic.get(0)))

# Navigate diagnostics
]d  - Next diagnostic
[d  - Previous diagnostic
K   - Hover to see details
<leader>ca - Code actions (quick fix)
```

---

## Summary Checklist

Before considering your OmniSharp configuration complete:

- [ ] **Path is absolute**: `/mnt/c/...` not `./` or `~/`
- [ ] **Path points to solution root**: Where `.sln` file is located
- [ ] **Path exists**: `ls -la "/mnt/c/.../Backend"` works
- [ ] **Settings defined**: `RoslynExtensionsOptions.EnableAnalyzersSupport = true`
- [ ] **OmniSharp running**: `ps aux | grep omnisharp` shows the path and settings
- [ ] **LSP attached**: `:LspInfo` shows omnisharp as active
- [ ] **Analyzers working**: Open a C# file, see StyleCop warnings
- [ ] **No handler conflicts**: Only one `omnisharp.setup()` call
- [ ] **Using vim.fn functions**: `vim.fn.stdpath()`, `vim.fn.expand()`

---

**Last Updated**: 2025-11-13
**Status**: Ready to apply to your configuration
