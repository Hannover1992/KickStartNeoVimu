# OmniSharp Alternative Configuration Approaches

**Date:** 2025-11-13
**Context:** Traditional mason-lspconfig + lspconfig.omnisharp.setup() has failed multiple times. Need StyleCop warnings in Neovim.

---

## Approach 1: Skip Mason - Manual OmniSharp Installation

### Overview
Completely bypass mason-lspconfig and manually manage OmniSharp installation and configuration. This gives 100% control over the cmd line and settings.

### Complexity Rating
⭐⭐⭐ (3/5) - Medium: Requires manual download/update, but configuration is straightforward

### Pros
- ✅ **Full Control**: No handler conflicts, you own the entire config
- ✅ **Guaranteed Settings**: Settings passed exactly as you write them
- ✅ **Debugging**: Easy to verify what's running with `ps aux`
- ✅ **Stable**: No plugin update surprises
- ✅ **Works Now**: Can test immediately without new plugins

### Cons
- ❌ **Manual Updates**: Must download OmniSharp updates manually
- ❌ **Platform-Specific**: Different setup for Linux/Windows/macOS
- ❌ **No Mason Integration**: Can't use `:Mason` UI to manage it
- ❌ **Extra Maintenance**: One more thing to track outside package manager

### Implementation

#### Step 1: Download OmniSharp Manually

```bash
# Download latest OmniSharp release
cd /tmp
wget https://github.com/OmniSharp/omnisharp-roslyn/releases/download/v1.39.12/omnisharp-linux-x64-net6.0.tar.gz

# Extract to permanent location
sudo mkdir -p /opt/omnisharp
sudo tar -xzf omnisharp-linux-x64-net6.0.tar.gz -C /opt/omnisharp

# Make executable
sudo chmod +x /opt/omnisharp/OmniSharp
```

#### Step 2: Update init.lua

**File:** `/home/uczen/.config/nvim/init.lua`

**Replace the `servers` table section (around line 673-701) with:**

```lua
local servers = {
  -- Manual OmniSharp configuration (NO MASON!)
  omnisharp = {
    cmd = {
      'dotnet',
      '/opt/omnisharp/OmniSharp.dll',  -- Manual installation path
      '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
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
    on_init = function(client, init_result)
      vim.notify('🔄 OmniSharp (Manual) loading projects...', vim.log.levels.INFO)
    end,
    on_attach = function(client, bufnr)
      vim.notify('✅ OmniSharp (Manual) attached successfully!', vim.log.levels.INFO)
    end,
  },

  -- Other servers remain unchanged
  lua_ls = {
    settings = {
      Lua = {
        completion = {
          callSnippet = 'Replace',
        },
      },
    },
  },
}
```

**Update mason-tool-installer to exclude omnisharp:**

```lua
local ensure_installed = vim.tbl_keys(servers or {})
-- Remove omnisharp from mason management
ensure_installed = vim.tbl_filter(function(item) return item ~= 'omnisharp' end, ensure_installed)
vim.list_extend(ensure_installed, {
  'stylua', -- Used to format Lua code
})
require('mason-tool-installer').setup { ensure_installed = ensure_installed }
```

**Keep the standard mason-lspconfig handler:**

```lua
require('mason-lspconfig').setup {
  ensure_installed = {},
  automatic_installation = false,
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

#### Step 3: Setup OmniSharp Manually After mason-lspconfig

**Add this AFTER the mason-lspconfig setup block:**

```lua
-- Manual OmniSharp setup (bypassing Mason)
if servers.omnisharp then
  local omnisharp_config = vim.deepcopy(servers.omnisharp)
  omnisharp_config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, omnisharp_config.capabilities or {})
  require('lspconfig').omnisharp.setup(omnisharp_config)
  vim.notify('🔧 OmniSharp configured manually (no Mason)', vim.log.levels.INFO)
end
```

#### Step 4: Test

```bash
# Restart Neovim
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs

# Verify process
ps aux | grep omnisharp | grep -v grep
# Should show: dotnet /opt/omnisharp/OmniSharp.dll -s /mnt/c/.../Backend -loglevel Information RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
```

### When to Use
- You've tried everything else and nothing works
- You want absolute control over OmniSharp version
- You're debugging complex LSP issues
- Mason keeps breaking your config

---

## Approach 2: Use csharp.nvim Plugin

### Overview
Install `iabdelkareem/csharp.nvim` which handles OmniSharp setup, configuration, and even debugging automatically. Zero-config approach.

### Complexity Rating
⭐⭐ (2/5) - Low: Plugin handles everything, just install and configure

### Pros
- ✅ **Zero Config**: Plugin handles OmniSharp installation/setup
- ✅ **Automatic Settings**: EnableAnalyzersSupport and other settings configured by default
- ✅ **Built-in Debugger**: Includes nvim-dap integration for C# debugging
- ✅ **Active Development**: Modern plugin (2024+), maintained
- ✅ **Mason Compatible**: Works with Mason if desired
- ✅ **No Handler Conflicts**: Plugin manages lifecycle independently

### Cons
- ❌ **Another Plugin**: One more dependency in your stack
- ❌ **Less Control**: Plugin abstracts configuration details
- ❌ **Early Development**: Plugin is still in "early development stage"
- ❌ **Learning Curve**: New plugin commands/API to learn
- ❌ **Potential Conflicts**: Might conflict with existing lspconfig setup

### Implementation

#### Step 1: Add Plugin to init.lua

**File:** `/home/uczen/.config/nvim/init.lua`

**Add to the `lazy.nvim` plugins table (around line 100-993):**

```lua
{
  -- C# Development with OmniSharp
  'iabdelkareem/csharp.nvim',
  dependencies = {
    'williamboman/mason.nvim',
    'mfussenegger/nvim-dap',
    'Tastyep/structlog.nvim',  -- Optional but recommended for debugging
  },
  ft = { 'cs' },  -- Only load for C# files
  config = function()
    require('mason').setup()  -- Ensure Mason is setup first
    require('csharp').setup {
      lsp = {
        -- Use OmniSharp (alternative: roslyn)
        omnisharp = {
          enable = true,
          cmd_path = nil,  -- nil = auto-install via Mason
          enable_editor_config_support = true,
          organize_imports = true,
          enable_analyzers_support = true,  -- KEY SETTING!
          enable_import_completion = true,
          include_prerelease_sdks = true,
          analyze_open_documents_only = false,
          enable_package_auto_restore = false,  -- WSL2 workaround
          default_timeout = 5000,
          on_attach = function(client, bufnr)
            vim.notify('✅ OmniSharp attached via csharp.nvim!', vim.log.levels.INFO)
          end,
        },
      },
      logging = {
        level = 'INFO',
      },
      dap = {
        -- Debugging configuration (optional)
        adapter_name = 'coreclr',
      },
    }
  end,
},
```

#### Step 2: Remove Conflicting OmniSharp Config

**IMPORTANT:** Remove any existing `omnisharp` configuration from the `servers` table:

```lua
local servers = {
  -- REMOVE or comment out any omnisharp config here!
  -- omnisharp = { ... },  -- DELETE THIS

  lua_ls = {
    settings = {
      Lua = {
        completion = {
          callSnippet = 'Replace',
        },
      },
    },
  },
}
```

#### Step 3: Install Dependencies

```bash
# Restart Neovim to install plugins
nvim

# Inside Neovim
:Lazy sync
:Mason  # Verify OmniSharp is installed
```

#### Step 4: Test

```bash
# Open a C# file
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs

# Check LSP status
:LspInfo
# Should show OmniSharp attached

# Check process
ps aux | grep omnisharp | grep -v grep
# Should show EnableAnalyzersSupport=true
```

### Additional Features

**Debug C# Code:**
```vim
:lua require('csharp').debug_project()
```

**Run C# Project:**
```vim
:lua require('csharp').run_project()
```

**Fix Usings:**
```vim
:lua require('csharp').fix_usings()
```

### When to Use
- You want a modern, integrated C# development experience
- You don't want to manually configure OmniSharp
- You need debugging support (nvim-dap) for C#
- You trust the plugin to handle settings correctly

---

## Approach 3: omnisharp.json Configuration File

### Overview
Create `~/.omnisharp/omnisharp.json` or project-level `omnisharp.json` with `enableAnalyzersSupport: true`. OmniSharp reads this file independently of Neovim configuration.

### Complexity Rating
⭐ (1/5) - Very Low: Just create a JSON file

### Pros
- ✅ **Simple**: Create one JSON file and you're done
- ✅ **Editor-Agnostic**: Works for VS Code, Vim, Emacs, etc.
- ✅ **No Config Changes**: Neovim init.lua stays unchanged
- ✅ **Version Control**: Project-level file can be committed to Git
- ✅ **Team-Wide**: Entire team gets same OmniSharp settings
- ✅ **Official Method**: Documented by OmniSharp maintainers

### Cons
- ❌ **Separate File**: One more config file to maintain
- ❌ **Global vs Local**: Must decide between user-wide or project-specific
- ❌ **Not Lua**: JSON format (not a big deal, but less integrated)
- ❌ **Hidden**: Less discoverable than Neovim config
- ❌ **Priority Confusion**: Command-line args override file settings

### Implementation

#### Option A: Global Configuration (User-Wide)

**File:** `~/.omnisharp/omnisharp.json`

```bash
# Create directory
mkdir -p ~/.omnisharp

# Create config file
cat > ~/.omnisharp/omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false,
    "documentAnalysisTimeoutMs": 30000,
    "enableDecompilationSupport": true,
    "diagnosticWorkersThreadCount": 8
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  },
  "fileOptions": {
    "systemExcludeSearchPatterns": [
      "**/node_modules/**/*",
      "**/bin/**/*",
      "**/obj/**/*",
      "**/.git/**/*"
    ]
  }
}
EOF
```

**Applies to:** ALL projects you work on with OmniSharp

#### Option B: Project-Level Configuration (Team-Wide)

**File:** `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/omnisharp.json`

```bash
# Navigate to project root (where .sln is)
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend

# Create project-specific config
cat > omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
EOF

# Add to Git (so team gets same settings)
git add omnisharp.json
git commit -m "Add OmniSharp configuration for analyzer support"
```

**Applies to:** Only this specific project, entire team benefits

#### Configuration Priority

OmniSharp reads settings in this order (later overrides earlier):
1. Hardcoded defaults
2. Environment variables
3. Command-line arguments (from Neovim config)
4. **Global `~/.omnisharp/omnisharp.json`**
5. **Local project `omnisharp.json`** (HIGHEST PRIORITY)

**This means:**
- If Neovim passes `EnableAnalyzersSupport=false` via cmd, but `omnisharp.json` says `true`, **JSON wins**!
- Project-level JSON overrides global JSON
- JSON settings override Neovim LSP settings table

#### Test the Configuration

```bash
# Restart Neovim and open C# file
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs

# Check OmniSharp process
ps aux | grep omnisharp | grep -v grep
# Should show: RoslynExtensionsOptions:enableAnalyzersSupport=true

# Check LSP logs
tail -100 ~/.local/state/nvim/lsp.log | grep -i analyzer
# Should show analyzer loading messages
```

#### Verify JSON is Being Read

Add logging to see if OmniSharp loads the file:

```bash
# Check OmniSharp logs (if you added -loglevel Information to cmd)
tail -f ~/.local/state/nvim/lsp.log | grep -i omnisharp.json
# Should show: "Loaded configuration from ~/.omnisharp/omnisharp.json"
```

### When to Use
- You want the simplest possible solution
- You want to commit settings to Git for your team
- You don't want to touch Neovim config at all
- You use multiple editors (VS Code + Neovim)

---

## Comparison Matrix

| Criteria | Approach 1: Manual | Approach 2: csharp.nvim | Approach 3: omnisharp.json |
|----------|-------------------|------------------------|---------------------------|
| **Complexity** | Medium (3/5) | Low (2/5) | Very Low (1/5) |
| **Setup Time** | 15-20 min | 10 min | 5 min |
| **Control** | Full | Medium | Low |
| **Maintenance** | Manual updates | Auto-updates | None |
| **Team-Friendly** | No | No | YES (commit JSON) |
| **Debugging** | Easy | Medium | Hard |
| **Works Now** | YES | YES | YES |
| **Future-Proof** | YES | Depends on plugin | YES |
| **Integration** | Mason-free | Mason-compatible | Universal |

---

## Recommended Approach: **Approach 3 (omnisharp.json)** ⭐

### Why This is Best

1. **Simplest**: Create one JSON file, done. No Neovim config changes.
2. **Lowest Risk**: Doesn't touch your working Neovim setup
3. **Team Benefit**: Commit to Git, entire team gets StyleCop warnings
4. **Editor Agnostic**: Works if you ever use VS Code too
5. **Official Method**: Documented by OmniSharp team
6. **Highest Priority**: Overrides any conflicting Neovim settings

### Quick Setup Guide (5 Minutes)

#### Step 1: Create Global Config
```bash
mkdir -p ~/.omnisharp
cat > ~/.omnisharp/omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
EOF
```

#### Step 2: Restart OmniSharp
```bash
# Kill running OmniSharp
pkill -f omnisharp

# Open Neovim with C# file
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs
```

#### Step 3: Verify
```bash
# Check process includes enableAnalyzersSupport
ps aux | grep omnisharp | grep -v grep | grep -i enableAnalyzers
# Should return a line with "enableAnalyzersSupport=true"
```

#### Step 4: Test StyleCop Warnings
Open `UserController.cs` and navigate to lines with StyleCop violations:
- Line 56-57, 78-79, 110-111, 152-153, 190-191, 241-243
- You should see warnings like SA1116, SA1117

### If It Still Doesn't Work

**Fallback to Approach 1 (Manual Installation):**
- Gives you full control
- Guaranteed to work if configured correctly
- Easy to debug with `ps aux`

---

## Next Steps

1. **Try Approach 3 first** (5 min setup)
2. **If it works**: Commit `omnisharp.json` to Git for your team
3. **If it fails**: Try Approach 1 (Manual installation)
4. **If you want more features**: Try Approach 2 (csharp.nvim) for debugging

---

## Troubleshooting All Approaches

### StyleCop Warnings Still Don't Appear

Even with `EnableAnalyzersSupport=true`, you might need:

1. **Check StyleCop Package is Installed:**
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
grep -r "StyleCop.Analyzers" *.csproj
# Should show: <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
```

2. **Check .editorconfig Exists:**
```bash
ls -la /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/.editorconfig
# Should exist
```

3. **Check OmniSharp Logs:**
```bash
tail -100 ~/.local/state/nvim/lsp.log | grep -i "StyleCop\|analyzer"
# Should show analyzers loading
```

4. **Force Analyzer Reload:**
```vim
:LspRestart
:e %  " Reload current file
```

### Verify OmniSharp is Using Your Settings

```bash
# Check running process
ps aux | grep omnisharp | grep -v grep

# Should show ALL these parameters:
# - RoslynExtensionsOptions:enableAnalyzersSupport=true
# - RoslynExtensionsOptions:enableImportCompletion=true
# - FormattingOptions:EnableEditorConfigSupport=true
```

---

## Conclusion

**Start with Approach 3 (omnisharp.json)** - it's the simplest, safest, and most team-friendly solution. If that fails for some reason, fall back to Approach 1 (Manual Installation) for full control.

**Approach 2 (csharp.nvim)** is great if you want an all-in-one C# development environment with debugging, but it's overkill if you just need StyleCop warnings.

The core issue with your previous attempts was **configuration conflicts** in Neovim. By using `omnisharp.json`, you bypass the Neovim config system entirely and let OmniSharp read its settings from a file - exactly as the OmniSharp team intended.
