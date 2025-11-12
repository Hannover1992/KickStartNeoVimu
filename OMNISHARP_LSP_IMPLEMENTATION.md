# OmniSharp LSP Implementation Details

## Understanding the LSP Configuration Flow

When using OmniSharp with Neovim via nvim-lspconfig, here's exactly how configuration reaches OmniSharp:

```
User Lua Config
    ↓
    ├─ cmd: [binary path]
    ├─ settings: {RoslynExtensionsOptions: {...}}
    └─ init_options: {} (empty, ignored for OmniSharp)
    ↓
nvim-lspconfig on_new_config Handler
    ↓
    ├─ Takes settings table
    ├─ Flattens nested keys with colons: RoslynExtensionsOptions:enableAnalyzersSupport=true
    ├─ Appends hard-coded LSP parameters: -z, --hostPID, --encoding, --languageserver
    ├─ Builds final command array
    └─ Passes as command-line arguments to OmniSharp
    ↓
OmniSharp Process
    ↓
    ├─ Parses command-line arguments
    ├─ Merges with omnisharp.json configuration
    ├─ Configuration hierarchy resolves conflicts
    └─ Starts LSP server with final merged config
```

### Key Insight

**OmniSharp does NOT use LSP `initializationOptions`!**

Instead:
1. The Neovim LSP client flattens the `settings` table into command-line arguments
2. These arguments are passed to the OmniSharp process
3. OmniSharp parses them like any CLI configuration

This is why you must use the `settings` table, not `init_options`.

---

## Correct Neovim Configuration Pattern

### Pattern: Basic Setup

```lua
require('lspconfig').omnisharp.setup({
  -- Step 1: Specify the binary
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--languageserver',  -- LSP mode
    '--hostPID', tostring(vim.fn.getpid()),  -- OmniSharp needs this
  },

  -- Step 2: Settings get flattened to CLI args by on_new_config
  settings = {
    RoslynExtensionsOptions = {
      enableAnalyzersSupport = true,
      enableImportCompletion = true,
      analyzeOpenDocumentsOnly = false,
      documentAnalysisTimeoutMs = 30000,
    },
    FormattingOptions = {
      enableEditorConfigSupport = true,
      organizeImportsOnFormat = true,
    },
  },

  -- Step 3: These are OPTIONAL - add only if needed
  capabilities = capabilities,  -- From nvim-cmp setup
  on_attach = on_attach,        -- Custom keybindings

  -- Step 4: DON'T use init_options (OmniSharp ignores it)
  -- init_options = {},  -- Not needed for OmniSharp
})
```

### Pattern: With Solution Path Hint

```lua
local project_root = vim.fn.getcwd()

require('lspconfig').omnisharp.setup({
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '-s', project_root,  -- Explicit solution path
    '--languageserver',
    '--hostPID', tostring(vim.fn.getpid()),
  },
  root_dir = require('lspconfig').util.root_pattern('*.sln', '*.csproj', 'omnisharp.json'),
  settings = {
    RoslynExtensionsOptions = {
      enableAnalyzersSupport = true,
      enableImportCompletion = true,
    },
    FormattingOptions = {
      enableEditorConfigSupport = true,
    },
  },
})
```

### Pattern: With Mason-lspconfig Handler

⚠️ **Warning:** Default mason-lspconfig handler may overwrite your cmd. Use explicit handler:

```lua
require('mason-lspconfig').setup({
  handlers = {
    omnisharp = function()
      require('lspconfig').omnisharp.setup({
        cmd = {
          vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
          '--languageserver',
          '--hostPID', tostring(vim.fn.getpid()),
        },
        settings = {
          RoslynExtensionsOptions = {
            enableAnalyzersSupport = true,
            enableImportCompletion = true,
          },
          FormattingOptions = {
            enableEditorConfigSupport = true,
          },
        },
        capabilities = capabilities,
        on_attach = on_attach,
      })
    end,
  },
})
```

---

## How Settings Are Flattened

### Example: Nested Settings to CLI Arguments

**Your Lua settings:**
```lua
settings = {
  RoslynExtensionsOptions = {
    enableAnalyzersSupport = true,
    enableImportCompletion = true,
    documentAnalysisTimeoutMs = 30000,
  },
  FormattingOptions = {
    enableEditorConfigSupport = true,
    organizeImportsOnFormat = true,
  },
}
```

**Becomes CLI arguments:**
```bash
RoslynExtensionsOptions:enableAnalyzersSupport=true
RoslynExtensionsOptions:enableImportCompletion=true
RoslynExtensionsOptions:documentAnalysisTimeoutMs=30000
FormattingOptions:enableEditorConfigSupport=true
FormattingOptions:organizeImportsOnFormat=true
```

**Final OmniSharp command:**
```bash
~/.local/share/nvim/mason/bin/OmniSharp \
  --languageserver \
  --hostPID 12345 \
  RoslynExtensionsOptions:enableAnalyzersSupport=true \
  RoslynExtensionsOptions:enableImportCompletion=true \
  RoslynExtensionsOptions:documentAnalysisTimeoutMs=30000 \
  FormattingOptions:enableEditorConfigSupport=true \
  FormattingOptions:organizeImportsOnFormat=true
```

---

## Configuration Precedence in OmniSharp

When OmniSharp starts, it merges configuration from multiple sources in this order:

```
1. Hardcoded defaults (lowest priority)
   ↓ overridden by ↓
2. omnisharp.json in ~/.omnisharp/
   ↓ overridden by ↓
3. omnisharp.json in project root/working directory
   ↓ overridden by ↓
4. Environment variables (OMNISHARP_RoslynExtensionsOptions:enableAnalyzersSupport=true)
   ↓ overridden by ↓
5. Command-line arguments (highest priority)
   RoslynExtensionsOptions:enableAnalyzersSupport=true
```

**Result:** Command-line arguments (from Neovim settings) override everything else.

---

## Common Issues and Solutions

### Issue 1: `:LspInfo` Shows Empty RoslynExtensionsOptions

**Symptom:**
```
RoslynExtensionsOptions = {}
```

**Causes:**
1. Settings not defined in Lua config
2. LSP client didn't flatten settings correctly
3. OmniSharp process died before initialization

**Solution:**
```lua
-- Explicitly verify settings in your config
require('lspconfig').omnisharp.setup({
  settings = {
    RoslynExtensionsOptions = {
      enableAnalyzersSupport = true,  -- ← Must be present
    },
  },
})
```

Then:
```vim
:LspRestart
:LspInfo
```

### Issue 2: Settings Passed but Not Applied

**Symptom:** Settings show in `:LspInfo` but analyzers don't run

**Causes:**
1. Value is `nil` instead of `true`
2. Typo in setting name (camelCase required)
3. omnisharp.json overriding with `null`

**Solutions:**
```lua
-- ❌ Wrong
settings = {
  RoslynExtensionsOptions = {
    enableAnalyzersSupport = nil,  -- nil won't apply
  },
}

-- ✅ Correct
settings = {
  RoslynExtensionsOptions = {
    enableAnalyzersSupport = true,  -- explicit true
  },
}
```

Or verify omnisharp.json doesn't contradict:
```bash
cat ~/.omnisharp/omnisharp.json
# Check: enableAnalyzersSupport is true, not null
```

### Issue 3: Mason-lspconfig Handler Overwrites Config

**Symptom:** Your custom cmd is ignored

**Cause:** Default handler doesn't preserve your settings

**Solution:** Define explicit handler:
```lua
require('mason-lspconfig').setup({
  ensure_installed = { 'omnisharp' },
  handlers = {
    omnisharp = function()
      require('lspconfig').omnisharp.setup({
        -- YOUR FULL CONFIG HERE
      })
    end,
  },
})
```

### Issue 4: Large Solutions Timeout

**Symptom:** Analyzers start but don't complete

**Solution:** Increase timeout:
```lua
settings = {
  RoslynExtensionsOptions = {
    enableAnalyzersSupport = true,
    documentAnalysisTimeoutMs = 60000,  -- 60 seconds instead of 30
    diagnosticWorkersThreadCount = 4,   -- More parallel workers
  },
}
```

---

## Debugging: Trace OmniSharp Startup

### Enable Verbose Logging

```lua
require('lspconfig').omnisharp.setup({
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '-loglevel', 'Debug',  -- ← Enable debug logging
    '--languageserver',
    '--hostPID', tostring(vim.fn.getpid()),
  },
  settings = {
    RoslynExtensionsOptions = {
      enableAnalyzersSupport = true,
    },
  },
})
```

### Check OmniSharp Output

```vim
" In Neovim, open the LSP log
:e ~/.local/state/nvim/lsp.log

" Or use tail to watch in real-time
:terminal
$ tail -f ~/.local/state/nvim/lsp.log
```

Look for lines like:
```
[DEBUG] RoslynExtensionsOptions:enableAnalyzersSupport=true
[DEBUG] Roslyn analyzer support enabled
```

### Manually Test OmniSharp

```bash
# Kill existing instance
pkill -f omnisharp

# Start with verbose output
~/.local/share/nvim/mason/bin/OmniSharp \
  -loglevel Debug \
  -s /path/to/solution \
  --languageserver \
  --hostPID $$ \
  RoslynExtensionsOptions:enableAnalyzersSupport=true \
  FormattingOptions:enableEditorConfigSupport=true

# Output should show:
# [DEBUG] Analyzer support enabled
# [DEBUG] RoslynExtensionsOptions:enableAnalyzersSupport = true
```

---

## Best Practices

### 1. Use omnisharp.json + Lua Settings

Store base config in `~/.omnisharp/omnisharp.json`:
```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true
  }
}
```

Then minimal Lua config:
```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'), '--languageserver' },
})
```

Both files merge; omnisharp.json provides defaults, Lua can override.

### 2. Project-Specific Settings

Place `omnisharp.json` in project root for team-wide consistency:
```bash
# In project root
cat > omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  }
}
EOF
git add omnisharp.json
```

### 3. Performance Tuning

For large solutions, tune these:
```lua
settings = {
  RoslynExtensionsOptions = {
    analyzeOpenDocumentsOnly = true,      -- Only analyze open files
    documentAnalysisTimeoutMs = 60000,    -- Increase timeout
    diagnosticWorkersThreadCount = 4,     -- Adjust to CPU cores
  },
}
```

---

## Reference: All RoslynExtensionsOptions

```lua
RoslynExtensionsOptions = {
  -- Analyzers
  enableAnalyzersSupport = true,           -- CRITICAL: enables Roslyn analyzers
  analyzeOpenDocumentsOnly = false,        -- true = faster, only open files
  documentAnalysisTimeoutMs = 30000,       -- Increase for large projects

  -- Completion
  enableImportCompletion = true,           -- Show unimported types in IntelliSense

  -- Advanced
  enableDecompilationSupport = false,      -- ILSpy decompilation
  diagnosticWorkersThreadCount = 4,        -- Parallel analyzer threads
  locationPaths = {},                      -- Custom analyzer DLL paths
}
```

---

## Summary

| Component | Responsibility |
|-----------|-----------------|
| **Neovim Lua config** | Define settings in `settings` table |
| **nvim-lspconfig** | Flatten settings to CLI args and start OmniSharp |
| **OmniSharp process** | Parse CLI args and load configuration |
| **omnisharp.json** | Provide persistent defaults (optional) |

**Key Principle:** Settings flow from Neovim → LSP client → OmniSharp command line → OmniSharp process
