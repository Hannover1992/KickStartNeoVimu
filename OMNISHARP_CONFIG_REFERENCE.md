# OmniSharp Configuration Quick Reference

## TLDR: Enable Roslyn Analyzers

**The single most important setting:**
```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  }
}
```

---

## 3 Ways to Configure

### Method 1: omnisharp.json (Recommended)

**Global (all projects):**
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

**Project-specific:** Place same `omnisharp.json` in project root

### Method 2: Command-Line Arguments

Format: `KEY:SUBKEY=VALUE` (no `-` prefix, colon delimiter)

```bash
OmniSharp -s /path/to/solution \
  RoslynExtensionsOptions:enableAnalyzersSupport=true \
  FormattingOptions:enableEditorConfigSupport=true
```

### Method 3: Neovim LSP Configuration

```lua
require('lspconfig').omnisharp.setup({
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'), '--languageserver' },
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

---

## Critical Settings

| Setting | Type | Default | What It Does |
|---------|------|---------|--------------|
| `enableAnalyzersSupport` | bool | `null` | ⚠️ **MUST BE TRUE** - Enables Roslyn analyzers |
| `enableImportCompletion` | bool | `null` | Shows unimported types in IntelliSense |
| `enableDecompilationSupport` | bool | `null` | ILSpy decompilation access |
| `analyzeOpenDocumentsOnly` | bool | `null` | Only analyze open files (faster) |
| `documentAnalysisTimeoutMs` | int | `30000` | Analyzer timeout (increase for large projects) |

Both `RoslynExtensionsOptions` AND `FormattingOptions` are required.

---

## How It Works

**Configuration Priority (highest to lowest):**
1. Local `omnisharp.json` in working directory
2. Global `~/.omnisharp/omnisharp.json`
3. Command-line arguments
4. Environment variables: `OMNISHARP_RoslynExtensionsOptions:enableAnalyzersSupport=true`
5. Hardcoded defaults

---

## Verify It Works

```bash
# 1. Check OmniSharp binary
ls ~/.local/share/nvim/mason/bin/OmniSharp

# 2. In Neovim, open a C# file
# Then run:
:LspInfo

# Should show:
# RoslynExtensionsOptions = { enableAnalyzersSupport = true }
```

---

## Common Mistakes

| ❌ Wrong | ✅ Correct |
|---------|-----------|
| `-RoslynExtensionsOptions:...` | `RoslynExtensionsOptions:...` |
| `enable_roslyn_analyzers` | `enableAnalyzersSupport` |
| Only `RoslynExtensionsOptions` | Both `RoslynExtensionsOptions` + `FormattingOptions` |
| `init_options` in LSP | `settings` table in LSP config |

---

## If Analyzers Still Don't Work

1. **Kill existing OmniSharp:**
   ```bash
   pkill -f omnisharp
   ```

2. **Clean swap files:**
   ```bash
   rm -f ~/.local/state/nvim/swap/*.swp
   ```

3. **Fix WSL2 NuGet issue (if applicable):**
   ```bash
   dotnet restore --force-evaluate --no-cache
   ```

4. **Restart Neovim and check:**
   ```vim
   :LspRestart
   :LspInfo
   ```

---

## Full Configuration Example

**~/.omnisharp/omnisharp.json:**
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
    "organizeImportsOnFormat": true,
    "tabSize": 4,
    "indentSize": 4,
    "useTabs": false
  },
  "MsBuild": {
    "loadProjectsOnDemand": false
  },
  "Sdk": {
    "includePrereleaseSdks": false
  }
}
```

---

## Official Docs

- **OmniSharp Wiki:** https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- **nvim-lspconfig:** https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/omnisharp.lua
