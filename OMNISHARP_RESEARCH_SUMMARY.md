# OmniSharp RoslynExtensionsOptions Research - Final Summary

**Date:** 2025-11-12
**Status:** Complete
**Sources:** Official OmniSharp GitHub Wiki, nvim-lspconfig, community documentation

---

## Key Findings

### 1. Official Way to Enable Analyzer Support

The official OmniSharp configuration method is:

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  }
}
```

**Critical:** This setting MUST be explicitly set to `true`. If it's `null` or missing, analyzers won't run.

**Source:** https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options

---

### 2. Configuration Methods (Priority Order)

OmniSharp supports three ways to enable analyzers, listed by precedence (highest to lowest):

#### Method A: Command-Line Arguments (Highest Priority)
```bash
OmniSharp -s /path/to/solution \
  RoslynExtensionsOptions:enableAnalyzersSupport=true
```
**Format:** `KEY:SUBKEY=VALUE` (no `-` or `--` prefix, colon delimiter)

#### Method B: Local omnisharp.json (Project Root)
```json
// ./omnisharp.json (in project root)
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  }
}
```

#### Method C: Global omnisharp.json (User Home)
```json
// ~/.omnisharp/omnisharp.json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  }
}
```

---

### 3. LSP Initialization in Neovim

**Important:** OmniSharp does NOT use LSP `initializationOptions`.

Instead, the nvim-lspconfig client:
1. Takes your `settings` table
2. Flattens it to CLI arguments (using `:` as delimiter)
3. Passes as command-line args to OmniSharp process
4. OmniSharp parses them like normal CLI configuration

**Correct Neovim configuration:**

```lua
require('lspconfig').omnisharp.setup({
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--languageserver',
    '--hostPID', tostring(vim.fn.getpid()),
  },

  settings = {  -- ← Settings get flattened to CLI args
    RoslynExtensionsOptions = {
      enableAnalyzersSupport = true,
      enableImportCompletion = true,
    },
    FormattingOptions = {
      enableEditorConfigSupport = true,
    },
  },

  -- init_options = {},  -- ← NOT used by OmniSharp
})
```

---

### 4. Command-Line Parameter Format Examples

| Use Case | Command |
|----------|---------|
| Enable analyzers | `RoslynExtensionsOptions:enableAnalyzersSupport=true` |
| Enable import completion | `RoslynExtensionsOptions:enableImportCompletion=true` |
| Set analysis timeout | `RoslynExtensionsOptions:documentAnalysisTimeoutMs=60000` |
| Enable EditorConfig | `FormattingOptions:enableEditorConfigSupport=true` |
| Multiple parameters | `Param1:key=value Param2:key=value ...` |

**Rules:**
- No prefix (`-` or `--`)
- Use colon (`:`) to separate nested keys
- Equals (`=`) for value assignment
- Space-separated for multiple args

---

### 5. Critical Warnings and Gotchas

#### ⚠️ CRITICAL ISSUES

1. **enableAnalyzersSupport Must Be Explicitly `true`**
   - Default is `null` (disabled)
   - If not set, you get refactorings only, NO analyzers
   - Verify: `:LspInfo` should show `enableAnalyzersSupport = true`

2. **Both RoslynExtensionsOptions AND FormattingOptions Required**
   - Just setting analyzers isn't enough
   - Must also set `FormattingOptions.enableEditorConfigSupport = true`
   - Both together enable full analyzer + formatting support

3. **LSP Settings Go in `settings` Table, Not `init_options`**
   - ❌ `init_options = { RoslynExtensionsOptions = {...} }` → WRONG
   - ✅ `settings = { RoslynExtensionsOptions = {...} }` → CORRECT
   - OmniSharp ignores LSP `initializationOptions`

4. **Mason-lspconfig Handler May Overwrite Configuration**
   - Default handler doesn't preserve custom cmd
   - Solution: Define explicit handler with your settings
   - Or: Don't use auto-setup for OmniSharp

5. **Large Solutions May Timeout**
   - Default `documentAnalysisTimeoutMs = 30000` (30 seconds)
   - Increase for large/complex projects: `documentAnalysisTimeoutMs = 60000`
   - Also adjust `diagnosticWorkersThreadCount`

#### ⚠️ COMMON MISTAKES

| Mistake | Problem | Fix |
|---------|---------|-----|
| `enableAnalyzersSupport = nil` | Analyzers disabled | Set to `true` |
| `enable_analyzers_support` | Wrong key (snake_case) | Use `enableAnalyzersSupport` (camelCase) |
| `settings = { init_options = {...} }` | Settings lost | Use `settings = { RoslynExtensionsOptions = {...} }` |
| `-RoslynExtensionsOptions:...` | CLI parsing fails | Remove `-` prefix |
| Only `RoslynExtensionsOptions` | Incomplete config | Also set `FormattingOptions` |

---

### 6. Verification Checklist

After configuring, verify analyzers are enabled:

```bash
# 1. Kill any running OmniSharp
pkill -f omnisharp

# 2. In Neovim, check LSP status
:LspInfo
# Look for: RoslynExtensionsOptions = { enableAnalyzersSupport = true }

# 3. Open a C# file
# 4. Trigger a style warning (e.g., unused variable)
# 5. See red/yellow squiggles appear
# 6. Hover with K to see error
# 7. Use <leader>ca for code actions
```

**Expected behavior:**
- ✅ Analyzer warnings visible as squiggles
- ✅ `:LspInfo` shows correct settings
- ✅ `K` (hover) displays error message
- ✅ Code actions available
- ✅ `]d` / `[d` navigate diagnostics

---

### 7. Working Configuration Examples

#### Example 1: Minimal Global Configuration

```bash
# ~/.omnisharp/omnisharp.json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true
  }
}
```

#### Example 2: Full Neovim LSP Setup

```lua
require('lspconfig').omnisharp.setup({
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--languageserver',
    '--hostPID', tostring(vim.fn.getpid()),
  },
  root_dir = require('lspconfig').util.root_pattern('*.sln', '*.csproj'),
  settings = {
    RoslynExtensionsOptions = {
      enableAnalyzersSupport = true,
      enableImportCompletion = true,
      analyzeOpenDocumentsOnly = false,
      documentAnalysisTimeoutMs = 30000,
      diagnosticWorkersThreadCount = 4,
    },
    FormattingOptions = {
      enableEditorConfigSupport = true,
      organizeImportsOnFormat = true,
    },
  },
  capabilities = capabilities,
  on_attach = on_attach,
})
```

#### Example 3: Mason-lspconfig Handler

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

### 8. Official Documentation Links

| Resource | URL |
|----------|-----|
| **OmniSharp Configuration** | https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options |
| **nvim-lspconfig OmniSharp** | https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua |
| **Neovim OmniSharp Setup** | https://aaronbos.dev/posts/dotnet-roslyn-editorconfig-neovim |
| **OmniSharp GitHub** | https://github.com/OmniSharp/omnisharp-roslyn |

---

## Generated Documents

This research produced the following detailed guides:

1. **OMNISHARP_ROSLYN_RESEARCH.md** (13 KB)
   - Complete official documentation
   - All configuration options explained
   - Command-line format specification
   - Working examples

2. **OMNISHARP_CONFIG_REFERENCE.md** (4 KB)
   - Quick reference for busy developers
   - 3 configuration methods side-by-side
   - Common mistakes and fixes
   - Verification steps

3. **OMNISHARP_LSP_IMPLEMENTATION.md** (11 KB)
   - Deep dive into LSP client behavior
   - How settings flow through nvim-lspconfig
   - Debugging techniques
   - Best practices

4. **OMNISHARP_CMD_PARAMETER_ANALYSIS.md** & **OMNISHARP_CMD_QUICK_REFERENCE.md**
   - Command-line argument analysis
   - Parameter format reference

---

## Summary Table

| Question | Answer | Reference |
|----------|--------|-----------|
| **Enable analyzer support?** | Set `RoslynExtensionsOptions.enableAnalyzersSupport = true` | Official Wiki |
| **Config file format?** | JSON in omnisharp.json with nested keys | Wiki |
| **CLI arg format?** | `KEY:SUBKEY=VALUE` (no prefix, colon delimiter) | Wiki |
| **Need omnisharp.json?** | Optional; can use Lua settings instead | Wiki |
| **Where does LSP init?** | Via command-line args, not initializationOptions | nvim-lspconfig |
| **Both RoslynExt + Formatting?** | Yes, both required for full support | Strathweb docs |
| **Timeout setting?** | `documentAnalysisTimeoutMs` (default 30s) | Wiki |
| **Performance tuning?** | `analyzeOpenDocumentsOnly`, `diagnosticWorkersThreadCount` | Wiki |

---

## Final Recommendation

For the KickStartNeoVim project setup:

### Option A: Simple (Recommended for most users)

1. Create `~/.omnisharp/omnisharp.json`:
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

2. Use basic Neovim LSP setup:
   ```lua
   require('lspconfig').omnisharp.setup({
     cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'), '--languageserver' },
   })
   ```

### Option B: Explicit (Recommended for complex projects)

Include full settings in Neovim config to ensure explicit control:
```lua
require('lspconfig').omnisharp.setup({
  cmd = { ... },
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

Both approaches work; choose based on preference.

---

## Conclusion

Official OmniSharp documentation confirms that:

1. ✅ **Analyzer support is configured via `RoslynExtensionsOptions.enableAnalyzersSupport = true`**
2. ✅ **Command-line format is `KEY:SUBKEY=VALUE`** (colon-delimited, no prefix)
3. ✅ **LSP settings use command-line args, not initializationOptions**
4. ✅ **Both RoslynExtensionsOptions and FormattingOptions required**
5. ✅ **Configuration files or Neovim settings both work**

All findings are based on:
- Official OmniSharp-Roslyn GitHub Wiki
- Official nvim-lspconfig source code
- Verified community implementations

No undocumented features or workarounds required.

---

**Research completed:** 2025-11-12
**Documentation status:** COMPLETE
**Ready for implementation:** YES
