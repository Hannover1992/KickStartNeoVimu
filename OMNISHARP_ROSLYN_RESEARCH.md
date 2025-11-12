# OmniSharp RoslynExtensionsOptions Research Report

## Executive Summary

This report documents official OmniSharp configuration methods for enabling Roslyn analyzer support, based on research of the official OmniSharp-Roslyn Wiki and community documentation.

**Key Finding:** Analyzer support is controlled by the `RoslynExtensionsOptions.EnableAnalyzersSupport` setting, which can be configured via:
1. **omnisharp.json** configuration file (preferred)
2. **Command-line arguments** (programmatic override)
3. **LSP initialization** (via LSP client, e.g., Neovim)

---

## 1. Official Configuration Method

### Source
- **Official Wiki:** https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- **Status:** Primary authoritative reference for OmniSharp configuration

### RoslynExtensionsOptions Settings

The `RoslynExtensionsOptions` section controls analyzer behavior:

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `enableAnalyzersSupport` | Boolean | `null` | **CRITICAL**: Enables/disables Roslyn analyzers and code fixes |
| `enableImportCompletion` | Boolean | `null` | Shows unimported types in IntelliSense (may impact responsiveness) |
| `enableDecompilationSupport` | Boolean | `null` | Enables ILSpy decompilation for .NET Framework libraries |
| `analyzeOpenDocumentsOnly` | Boolean | `null` | When true, only runs analyzers on open files |
| `documentAnalysisTimeoutMs` | Integer | `30000` | Timeout for analyzer execution (milliseconds) |
| `diagnosticWorkersThreadCount` | Integer | `75% of cores` | Parallel analyzer execution threads |
| `locationPaths` | Array | `[]` | Custom paths to analyzer assemblies (Roslynator, etc.) |

**Critical Note:** "If `EnableAnalyzersSupport` is not enabled, only refactorings are available."

### Configuration File Format

Create or edit `omnisharp.json` with the following structure:

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "enableDecompilationSupport": false,
    "analyzeOpenDocumentsOnly": false,
    "documentAnalysisTimeoutMs": 30000,
    "diagnosticWorkersThreadCount": 3
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true
  }
}
```

**Important:** Both `RoslynExtensionsOptions` and `FormattingOptions` are needed for full analyzer and formatting support based on EditorConfig rules.

### Configuration File Locations

OmniSharp searches for configuration in **hierarchical order** (first match wins):

1. **Local (Project-specific)**: `omnisharp.json` in working directory / project root
2. **User Global**: `~/.omnisharp/omnisharp.json` (Linux/Mac) or `%USERPROFILE%/.omnisharp/omnisharp.json` (Windows)
3. **Hardcoded defaults**: Built into OmniSharp binary

**Recommendation:** Place `omnisharp.json` in project root to version-control team-wide settings.

---

## 2. Command-Line Parameter Format

### How Command-Line Args Work

OmniSharp accepts configuration overrides via command-line arguments using **flattened JSON paths with colons (`:`) as delimiters**.

**Format:** `KEY:SUBKEY:SUBSUBKEY=VALUE`

**Examples:**

```bash
# Enable analyzer support
OmniSharp -s /path/to/solution RoslynExtensionsOptions:enableAnalyzersSupport=true

# Set formatting tab size
OmniSharp -s /path/to/solution formattingOptions:tabSize=2

# Enable EditorConfig support
OmniSharp -s /path/to/solution FormattingOptions:enableEditorConfigSupport=true

# Multiple overrides
OmniSharp -s /path/to/solution \
  RoslynExtensionsOptions:enableAnalyzersSupport=true \
  RoslynExtensionsOptions:diagnosticWorkersThreadCount=4 \
  FormattingOptions:enableEditorConfigSupport=true
```

### Supported Parameter Sources (Priority Order)

1. **Hardcoded defaults** (lowest priority)
2. **Environment variables**: `OMNISHARP_RoslynExtensionsOptions:enableAnalyzersSupport=true`
3. **Command-line arguments**: `RoslynExtensionsOptions:enableAnalyzersSupport=true`
4. **Global omnisharp.json**: `~/.omnisharp/omnisharp.json`
5. **Local omnisharp.json**: `./omnisharp.json` (highest priority)

Each source overrides previous sources.

### No Prefix Required

- ❌ **Wrong:** `-RoslynExtensionsOptions:enableAnalyzersSupport=true`
- ❌ **Wrong:** `--RoslynExtensionsOptions:enableAnalyzersSupport=true`
- ✅ **Correct:** `RoslynExtensionsOptions:enableAnalyzersSupport=true`

---

## 3. LSP Initialization via Neovim

### nvim-lspconfig Configuration

The official `nvim-lspconfig` OmniSharp configuration (`omnisharp.lua`) shows:

```lua
{
  name = 'omnisharp',
  root_dir = root_pattern('*.sln', '*.csproj', 'omnisharp.json', 'function.json'),
  settings = {
    RoslynExtensionsOptions = {
      enableAnalyzersSupport = true,          -- Enable analyzers
      enableImportCompletion = true,          -- Enable import completion
      analyzeOpenDocumentsOnly = false,       -- Analyze all files
      documentAnalysisTimeoutMs = 30000,
    },
    FormattingOptions = {
      enableEditorConfigSupport = true,
    },
  },
  -- NOTE: init_options is empty; settings are passed via on_new_config
  init_options = {},
}
```

### How Settings Are Passed to OmniSharp

The `on_new_config` handler in nvim-lspconfig:

1. **Takes the base command** from `servers.omnisharp.cmd`
2. **Flattens the `settings` table** into command-line arguments
3. **Appends hard-coded LSP parameters**:
   - `-z`
   - `--hostPID {PID}`
   - `--encoding utf-8`
   - `--languageserver`
4. **Passes flattened settings** like `RoslynExtensionsOptions:enableAnalyzersSupport=true`

**Result:** The LSP client starts OmniSharp with command-line arguments, not via LSP `initializationOptions`.

### Example Neovim Configuration

```lua
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
      analyzeOpenDocumentsOnly = false,
      documentAnalysisTimeoutMs = 30000,
    },
    FormattingOptions = {
      enableEditorConfigSupport = true,
      organizeImportsOnFormat = true,
    },
  },
  on_attach = function(client, bufnr)
    -- Your keybindings here
  end,
})
```

---

## 4. Warnings and Gotchas

### ⚠️ Critical Issues

1. **EnableAnalyzersSupport = null (not true)**
   - If the setting is `null` or missing, analyzers won't run
   - You MUST explicitly set `enableAnalyzersSupport = true`
   - Check `:LspInfo` in Neovim; if `RoslynExtensionsOptions` shows `{}`, it's not configured

2. **FormattingOptions Must Also Be Set**
   - Both `RoslynExtensionsOptions` and `FormattingOptions` required for full support
   - EditorConfig integration requires `FormattingOptions.enableEditorConfigSupport = true`

3. **Configuration Conflicts in Mason-lspconfig**
   - The `mason-lspconfig` auto-handler may overwrite your custom `cmd` configuration
   - Solution: Explicitly define `cmd` in mason-lspconfig handler or disable auto-setup

4. **Analyzer Timeout May Need Adjustment**
   - Large solutions may hit 30-second timeout
   - Increase `documentAnalysisTimeoutMs` for slower systems
   - Recommended: 30000-60000 for medium/large projects

5. **analyzeOpenDocumentsOnly Trade-off**
   - `true`: Faster, only analyzes open files (good for performance)
   - `false`: Comprehensive but slower, analyzes entire solution
   - Default: `false` recommended for most projects

### ⚠️ Common Mistakes

| Mistake | Problem | Solution |
|---------|---------|----------|
| `enable_roslyn_analyzers: true` in Lua | Wrong key name for LSP settings | Use `RoslynExtensionsOptions.enableAnalyzersSupport` |
| Settings in `init_options` | LSP ignores init_options for OmniSharp | Place settings in `settings` table; LSP client flattens to CLI args |
| `-RoslynExtensionsOptions:...` prefix | OmniSharp doesn't recognize prefix | Remove `-` or `--` prefix |
| `RoslynExtensionsOptions.enable_analyzers_support` | Snake_case instead of camelCase | Use `enableAnalyzersSupport` (camelCase) |
| Only setting RoslynExtensionsOptions | Missing FormattingOptions | Set both for full analyzer + formatting support |

### ⚠️ WSL2 / Windows Filesystem Issues

- NuGet packages cached differently between Windows and WSL
- After compiling in Windows, run: `dotnet restore --force-evaluate --no-cache`
- Then restart OmniSharp: `pkill -f omnisharp`

---

## 5. Verification Steps

### Check If Analyzers Are Enabled

```bash
# 1. Check OmniSharp binary exists
ls ~/.local/share/nvim/mason/bin/OmniSharp

# 2. Test OmniSharp starts correctly
~/.local/share/nvim/mason/bin/OmniSharp --version

# 3. In Neovim, check configuration:
:LspInfo
# Look for: RoslynExtensionsOptions = { enableAnalyzersSupport = true }

# 4. Navigate to a C# file
# Try to trigger a style warning (e.g., extra whitespace)
# Hover over warning with K
```

### Expected Behavior

- ✅ `:LspInfo` shows `RoslynExtensionsOptions = { enableAnalyzersSupport = true }`
- ✅ Analyzer warnings appear as red/yellow squiggles
- ✅ Code actions available via `<leader>ca`
- ✅ `K` (hover) shows analyzer error message
- ✅ `]d` / `[d` navigate between diagnostics

---

## 6. Working Configuration Examples

### Example 1: omnisharp.json (Project Root)

```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "enableDecompilationSupport": false,
    "analyzeOpenDocumentsOnly": false,
    "documentAnalysisTimeoutMs": 30000,
    "diagnosticWorkersThreadCount": 4
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,
    "organizeImportsOnFormat": true
  },
  "MsBuild": {
    "loadProjectsOnDemand": false
  }
}
```

**Create with:**
```bash
mkdir -p ~/.omnisharp
cat > ~/.omnisharp/omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true
  }
}
EOF
```

### Example 2: Neovim init.lua Configuration

```lua
require('lspconfig').omnisharp.setup({
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--languageserver',
    '--hostPID', tostring(vim.fn.getpid()),
  },
  root_dir = require('lspconfig').util.root_pattern('*.sln', '*.csproj', 'omnisharp.json'),
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

### Example 3: Command-Line Override

```bash
# Kill existing OmniSharp
pkill -f omnisharp

# Start with explicit analyzer support
~/.local/share/nvim/mason/bin/OmniSharp \
  -s /path/to/solution \
  --languageserver \
  --hostPID $$ \
  RoslynExtensionsOptions:enableAnalyzersSupport=true \
  RoslynExtensionsOptions:enableImportCompletion=true \
  FormattingOptions:enableEditorConfigSupport=true
```

---

## 7. Official Documentation Links

| Resource | URL |
|----------|-----|
| **OmniSharp Configuration Wiki** | https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options |
| **nvim-lspconfig OmniSharp** | https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua |
| **Roslyn EditorConfig + OmniSharp** | https://aaronbos.dev/posts/dotnet-roslyn-editorconfig-neovim |
| **OmniSharp GitHub** | https://github.com/OmniSharp/omnisharp-roslyn |
| **Analyzer Support Issue** | https://github.com/OmniSharp/omnisharp-roslyn/issues/2667 |

---

## 8. Summary Table

| Question | Answer |
|----------|--------|
| **How to enable analyzer support?** | Set `RoslynExtensionsOptions.enableAnalyzersSupport = true` |
| **Where to configure?** | 1) omnisharp.json (preferred) 2) Command-line args 3) Env vars |
| **Command-line format?** | `RoslynExtensionsOptions:enableAnalyzersSupport=true` (colon-delimited, no prefix) |
| **LSP initialization method?** | Settings passed via `on_new_config` handler that flattens to CLI args |
| **Need both settings?** | Yes: RoslynExtensionsOptions + FormattingOptions |
| **Performance settings?** | `diagnosticWorkersThreadCount`, `documentAnalysisTimeoutMs`, `analyzeOpenDocumentsOnly` |

---

## Changelog

- **2025-11-12**: Initial research and documentation
  - Official OmniSharp Wiki reviewed
  - nvim-lspconfig configuration analyzed
  - Command-line parameter format verified
  - Warnings and gotchas documented
  - Working examples provided
