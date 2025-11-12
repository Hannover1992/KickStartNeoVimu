# Mason + OmniSharp Implementation Action Plan

## Context
This document provides specific action items for implementing OmniSharp with Mason in the DCSRE project Neovim setup, based on comprehensive research.

---

## Part 1: Pre-Installation Verification

### Step 1: Check Current Mason Status

```bash
# Open Neovim and check Mason
nvim -c ":Mason" -c ":quit"

# Should see Mason UI with list of tools
# If fails: Mason not installed, install via lazy.nvim first
```

### Step 2: Verify Mason Version

```vim
:Mason
# Click on 'Check for updates' or look at version in header
# Target: v2.0.0 or higher (fixes case sensitivity issue)
```

### Step 3: Check Existing OmniSharp Installation

```bash
# Check if already installed
ls ~/.local/share/nvim/mason/packages/ | grep omnisharp

# If yes: verify completeness
ls -la ~/.local/share/nvim/mason/packages/omnisharp/libexec/

# Expected to see: OmniSharp.dll and supporting files
# If missing files: proceed to "Incomplete Installation Fix"
```

---

## Part 2: Installation Steps

### Step 1: Install OmniSharp via Mason

**Method A: Interactive UI (Recommended)**
```vim
nvim
:Mason
# Search for 'omnisharp' (lowercase in search)
# Press 'i' on the omnisharp line
# Wait for installation to complete
# Press 'q' to close Mason
:quit
```

**Method B: Command Line**
```bash
# Start Neovim and let Mason install via lazy.nvim
nvim
# Lazy will auto-install if configured
# This happens on first startup with proper setup
```

### Step 2: Verify Complete Installation

```bash
# Check installed files
ls ~/.local/share/nvim/mason/packages/omnisharp/

# Expected output:
# bin/
# libexec/
# mason-receipt.json

# Check libexec/ contents
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/

# Expected: OmniSharp.dll and runtime files (not just empty)
# If only 1-2 files: INCOMPLETE INSTALLATION - see "Fix Incomplete Installation" section
```

### Step 3: Verify Symlink in bin/

```bash
# Check symlink exists
ls -la ~/.local/share/nvim/mason/bin/ | grep -i omnisharp

# Expected output:
# omnisharp -> ../packages/omnisharp/bin/OmniSharp
# OR
# OmniSharp -> ../packages/omnisharp/bin/OmniSharp

# Note: Case depends on Mason version
# Both lowercase 'omnisharp' and capitalized 'OmniSharp' are valid in v2.0+
```

### Step 4: Test OmniSharp Binary

```bash
# Test if OmniSharp can be executed
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll --version

# Expected output:
# v1.39.x (version number)
# If error: see "Troubleshooting" section
```

---

## Part 3: Configuration in init.lua

### Add OmniSharp Configuration

Add this to your `~/.config/nvim/init.lua` or language server setup file:

```lua
local lspconfig = require('lspconfig')
local mason_registry = require('mason-registry')

-- Configure OmniSharp with Mason
lspconfig.omnisharp.setup({
  -- 1. Use Mason-installed binary
  cmd = { "dotnet", vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll' },

  -- 2. CRITICAL: Set root directory pattern
  -- This tells OmniSharp where to find .sln or .csproj files
  root_dir = lspconfig.util.root_pattern('*.sln', '*.csproj'),

  -- 3. Enable OmniSharp features
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
  enable_import_completion = true,

  -- 4. Pass OmniSharp-specific settings
  init_options = {
    RoslynExtensionsOptions = {
      enableAnalyzersSupport = true,
      enableImportCompletion = true,
      analyzeOpenDocumentsOnly = false,
    },
  },

  -- 5. Optional: Add logging for debugging
  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      local level = result.type
      local message = result.message
      vim.notify(string.format('[OmniSharp] %s', message), level)
    end,
  },

  -- 6. Capabilities (merge with your LSP capabilities if you have them)
  capabilities = vim.lsp.protocol.make_client_capabilities(),
})
```

### Location of init.lua

The configuration should go in one of these locations:

```bash
# Linux/WSL2:
~/.config/nvim/init.lua

# Windows (if not using WSL2):
~\AppData\Local\nvim\init.lua

# Typical structure:
~/.config/nvim/
├── init.lua                 # Main configuration
├── lua/
│   ├── lsp/
│   │   └── omnisharp.lua    # (Optional) Separate file for OmniSharp config
│   └── user/
│       └── settings.lua     # General settings
```

### If Using Separate LSP Configuration File

If you organize LSP configs in separate files (recommended):

**File: `~/.config/nvim/lua/lsp/omnisharp.lua`**
```lua
local lspconfig = require('lspconfig')

return {
  setup = function()
    lspconfig.omnisharp.setup({
      cmd = { "dotnet", vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll' },
      root_dir = lspconfig.util.root_pattern('*.sln', '*.csproj'),
      enable_roslyn_analyzers = true,
      organize_imports_on_format = true,
      enable_import_completion = true,
      -- rest of config...
    })
  end
}
```

**Then in `~/.config/nvim/init.lua`:**
```lua
require('lsp.omnisharp').setup()
```

---

## Part 4: Fix Common Installation Issues

### Issue A: Incomplete Installation

**Symptoms:**
- OmniSharp directory only contains 2-3 files
- Missing libexec/ directory or it's mostly empty
- OmniSharp startup fails silently

**Cause:** Incomplete zip extraction (GitHub Issue #701)

**Solution: Manual Installation**

```bash
# Step 1: Remove broken installation
rm -rf ~/.local/share/nvim/mason/packages/omnisharp/

# Step 2: Download OmniSharp manually
# Get latest version from: https://github.com/OmniSharp/omnisharp-roslyn/releases

# For Linux x64:
wget https://github.com/OmniSharp/omnisharp-roslyn/releases/download/v1.39.10/omnisharp-linux-x64.tar.gz

# For Linux arm64 (Raspberry Pi, etc):
wget https://github.com/OmniSharp/omnisharp-roslyn/releases/download/v1.39.10/omnisharp-linux-arm64.tar.gz

# For macOS x64:
wget https://github.com/OmniSharp/omnisharp-roslyn/releases/download/v1.39.10/omnisharp-osx.tar.gz

# For macOS arm64 (M1/M2):
wget https://github.com/OmniSharp/omnisharp-roslyn/releases/download/v1.39.10/omnisharp-osx-arm64.tar.gz

# Step 3: Extract to Mason directory
mkdir -p ~/.local/share/nvim/mason/packages/omnisharp/libexec/
tar -xzf omnisharp-linux-x64.tar.gz -C ~/.local/share/nvim/mason/packages/omnisharp/libexec/

# Step 4: Create Mason receipt
cat > ~/.local/share/nvim/mason/packages/omnisharp/mason-receipt.json << 'EOF'
{
  "name": "omnisharp",
  "source": "manual",
  "version": "1.39.10"
}
EOF

# Step 5: Create symlink in mason/bin/
mkdir -p ~/.local/share/nvim/mason/bin/
cd ~/.local/share/nvim/mason/bin/
ln -sf ../packages/omnisharp/libexec/OmniSharp omnisharp

# Step 6: Verify
ls -la ~/.local/share/nvim/mason/bin/ | grep omnisharp
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll --version
```

### Issue B: Case Sensitivity Mismatch

**Symptoms:**
- Error: "The language server is either not installed, missing from PATH, or not executable"
- But `:LspStart omnisharp` works fine!

**Cause:** Binary named 'OmniSharp' but trying to launch 'omnisharp' (older Mason versions)

**Solution A: Rename Binary (Quick Fix)**
```bash
cd ~/.local/share/nvim/mason/bin/
# If you see 'OmniSharp' (capital O):
mv OmniSharp omnisharp

# If you see 'omnisharp' (lowercase):
# Already correct, no action needed
```

**Solution B: Update Mason (Permanent Fix)**
```bash
# Mason v2.0+ supports both names
# Update via your plugin manager or:
nvim -c ":Mason" -c ":quit"
# In Mason UI, check for updates

# Or rebuild everything
rm -rf ~/.local/share/nvim/mason/
# Let Mason reinstall everything on next Neovim start
```

**Solution C: Override cmd Path (Configuration Fix)**
```lua
-- If your installation has 'OmniSharp' (capital O), use:
lspconfig.omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },  -- Capital O
  -- rest of config...
})

-- If it has 'omnisharp' (lowercase), use:
lspconfig.omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/omnisharp') },  -- lowercase
  -- rest of config...
})
```

### Issue C: Root Directory Not Detected

**Symptoms:**
- OmniSharp attaches (`:LspInfo` shows it)
- But no intellisense, no go-to-definition
- No diagnostics/warnings appear

**Cause:** OmniSharp can't find `.sln` or `.csproj` files

**Solution:**
```lua
-- Make sure this is in your config:
root_dir = lspconfig.util.root_pattern('*.sln', '*.csproj'),

-- Or for specific DCSRE project:
root_dir = function()
  -- Search up from current file until finding .sln
  return lspconfig.util.search_ancestors(vim.fn.expand('%:p:h'), function(path)
    if vim.loop.fs_stat(path .. '/.git') or
       vim.loop.fs_stat(path .. '/VDEK.DCSP.sln') or
       vim.loop.fs_stat(path .. '/Sources/Backend/') then
      return path
    end
  end) or vim.fn.getcwd()
end,
```

### Issue D: WSL2 + Windows Filesystem NuGet Cache

**Symptoms:**
- Works after opening file in Windows
- Stops working when running same code in WSL2
- Roslyn analyzers unavailable

**Cause:** NuGet packages cached differently between Windows and WSL2

**Solution:**
```bash
# In WSL2 terminal, run in your project directory:
dotnet restore --force-evaluate --no-cache

# Or add to .bashrc/.zshrc for quick access:
alias fixlsp='dotnet restore --force-evaluate --no-cache && pkill -f omnisharp'

# Then when this happens:
fixlsp  # Fixes cache and kills old OmniSharp process
# Then reopen Neovim
```

---

## Part 5: Verification and Testing

### Post-Installation Checklist

**1. Verify Binary Installation**
```bash
ls -la ~/.local/share/nvim/mason/packages/omnisharp/libexec/
# Must have: OmniSharp.dll and supporting files
```

**2. Test Binary Execution**
```bash
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll --version
# Should print version, not error
```

**3. Check Symlink**
```bash
ls -la ~/.local/share/nvim/mason/bin/ | grep omnisharp
# Should show: omnisharp -> ../packages/omnisharp/bin/OmniSharp (or similar)
```

**4. Verify Configuration in Neovim**
```vim
nvim
:LspInfo
# Should show 'omnisharp' in the list
# Look for green bullet (●) indicating attached status
```

**5. Test in DCSRE Project**
```bash
cd /path/to/DCSRE
nvim Sources/Backend/VDEK.DCSP.WebHost/Program.cs
```

In Neovim:
```vim
" Check LSP status
:LspInfo
" Should show 'omnisharp' with green bullet

" Test go-to-definition
gd  (on a class name)
" Should jump to definition

" Test hover
K   (on a method)
" Should show documentation

" Test code actions
<leader>ca  (with cursor on warning)
" Should show quick-fix options
```

### Debugging if Not Working

```vim
" Check LSP log for errors
:LspLog
" Look for omnisharp initialization

" Restart LSP
:LspRestart omnisharp
" Watch for error messages in console

" Check binary path
:echo vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll'
" Verify path exists and points to valid binary

" Manual start
:LspStart omnisharp
" If works manually but not on file open, config issue

" Show attached LSP clients
:LspInfo
" Verify omnisharp is in the list
```

---

## Part 6: Optional - Alternative: csharp.nvim Plugin

If you encounter persistent issues with Mason + OmniSharp, consider the **csharp.nvim** plugin instead:

### When to Use csharp.nvim

- Repeated installation failures
- Platform compatibility issues (macOS M1/M2, Windows)
- Want integrated debugging and project running
- Prefer plugin-managed configuration over manual setup

### Installation (for Lazy.nvim)

**Add to your plugins configuration:**
```lua
{
  'iabdelkareem/csharp.nvim',
  dependencies = {
    'neovim/nvim-lspconfig',
    'mason.nvim',  -- Still needs Mason for other tools
  },
  config = function()
    require('csharp').setup({
      -- Plugin handles OmniSharp installation automatically
      -- No manual binary path needed
    })
  end
}
```

### Important: Remove Conflicting Config

If using csharp.nvim, remove the manual omnisharp setup from lspconfig to avoid conflicts:

```lua
-- Remove this from your config if using csharp.nvim:
-- lspconfig.omnisharp.setup({...})

-- csharp.nvim will handle it automatically
```

### Advantages

- ✓ Automatic OmniSharp installation and updates
- ✓ Better macOS architecture detection (auto-selects arm64 on M1/M2)
- ✓ Integrated debugging with netcoredbg
- ✓ Built-in project running with launch profiles
- ✓ Code fixes for removing unused imports

### Disadvantages

- Additional plugin dependency
- Less fine-grained control over OmniSharp settings
- Larger overhead if only need basic LSP

---

## Part 7: DCSRE Project-Specific Notes

### Project Structure Considerations

```
/path/to/DCSRE/
├── Sources/
│   ├── Backend/
│   │   └── VDEK.DCSP.sln              ← OmniSharp needs to find this
│   │   └── VDEK.DCSP.WebHost/
│   │       └── Program.cs
│   └── Frontend/
│       └── (Angular project)
└── .git/
```

### Root Directory Configuration for DCSRE

```lua
-- More specific to DCSRE project structure:
lspconfig.omnisharp.setup({
  root_dir = function()
    local path = vim.fn.expand('%:p:h')
    -- Look for VDEK.DCSP.sln
    return lspconfig.util.search_ancestors(path, function(dir)
      if vim.fn.glob(dir .. '/VDEK.DCSP.sln') ~= '' then
        return dir
      end
      if vim.fn.glob(dir .. '/Sources/Backend/VDEK.DCSP.sln') ~= '' then
        return dir .. '/Sources/Backend'
      end
    end) or vim.fn.getcwd()
  end,
  -- rest of config...
})
```

### Pre-Opening Checklist for DCSRE Development

1. **Restore NuGet packages:**
   ```bash
   cd /path/to/DCSRE/Sources/Backend
   dotnet restore --force-evaluate --no-cache
   ```

2. **Kill old OmniSharp processes:**
   ```bash
   pkill -f omnisharp
   ```

3. **Then open Neovim:**
   ```bash
   nvim VDEK.DCSP.WebHost/Program.cs
   ```

4. **Verify LSP attached:**
   ```vim
   :LspInfo
   # Should show omnisharp (wait 2-3 seconds for full attach)
   ```

---

## Summary Checklist

- [ ] Mason installed and v2.0.0 or higher
- [ ] OmniSharp installed via `:Mason`
- [ ] Binary verified in libexec/ directory
- [ ] Symlink created in mason/bin/
- [ ] OmniSharp binary executable (dotnet --version works)
- [ ] Configuration added to init.lua
- [ ] root_dir pattern includes '*.sln'
- [ ] Tested with :LspInfo in C# file
- [ ] gd (go-to-definition) works
- [ ] K (hover) shows documentation
- [ ] <leader>ca shows code actions

---

## Quick Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Language server not found" | Binary not found or case mismatch | Check ~/.local/share/nvim/mason/bin/ or rename |
| OmniSharp attaches but no intellisense | root_dir not set | Add `root_dir = lspconfig.util.root_pattern('*.sln')` |
| Works in Windows, fails in WSL2 | NuGet cache issue | Run `dotnet restore --force-evaluate --no-cache` |
| Only works with `:LspStart omnisharp` | Configuration issue | Check init.lua is being loaded |
| Incomplete installation | Extraction failed | Download OmniSharp manually from GitHub |

---

**Next Steps:** Follow Part 1-5 in order. If issues persist, consult the detailed MASON_OMNISHARP_RESEARCH.md document.
