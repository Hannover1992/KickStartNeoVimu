# OmniSharp and nvim-lspconfig Research Documentation

This directory contains comprehensive research and analysis of how nvim-lspconfig handles OmniSharp cmd parameters.

## Research Completed: November 12, 2025

## Available Documentation

### 1. RESEARCH_FINDINGS_SUMMARY.txt (12 KB)
**Best for**: Quick understanding of research methodology and findings

- Detailed answers to the 4 main research questions
- Research sources and documentation links
- Known issues with explanations
- Official recommendations
- Key takeaways and conclusions

**Read this first** if you need a structured overview of the entire research.

### 2. OMNISHARP_CMD_PARAMETER_ANALYSIS.md (13 KB)
**Best for**: Deep technical understanding

10 comprehensive sections:
1. How nvim-lspconfig handles OmniSharp cmd parameters
2. Solution file handling and the `-s` parameter
3. Typical configuration patterns
4. Known issues with cmd parameters
5. Root directory vs solution file path
6. Why cmd parameters might not be applied
7. Debugging cmd parameter issues
8. Best practices for OmniSharp configuration
9. Summary of parameter flow through the system
10. Key takeaways

**Read this** if you need complete technical details and best practices.

### 3. OMNISHARP_CMD_QUICK_REFERENCE.md (4.7 KB)
**Best for**: Quick lookup and common mistakes

- The problem explained simply
- Root cause with code examples
- Critical insight about the `-s` parameter
- Troubleshooting table
- What gets/doesn't get automatically applied
- Correct configuration pattern
- Common mistakes and fixes
- How parameters flow through the system

**Use this** for quick reference during configuration.

---

## Quick Answer to Main Questions

### Q1: How does nvim-lspconfig pass cmd parameters to OmniSharp?

Two-stage process:
1. User provides base cmd: `cmd = { "dotnet", "/path/to/OmniSharp.dll" }`
2. `on_new_config` callback automatically appends arguments when LSP attaches
3. Final cmd includes: `--languageserver`, `--hostPID`, `-z`, `DotNet:enablePackageRestore=false`, `--encoding utf-8`, plus all settings

**Key Point**: Users should only provide the base command. Don't manually add parameters that `on_new_config` appends automatically.

### Q2: How does nvim-lspconfig handle the OmniSharp -s parameter?

The `-s` parameter (for specifying solution files) is **NOT automatically added** by `on_new_config`.

However, **you should NOT manually add it** because:
- nvim-lspconfig uses `root_dir` pattern matching for automatic solution discovery
- Manually adding `-s` conflicts with automatic detection
- Results in malformed commands with duplicate parameters

**Key Point**: Let nvim-lspconfig find solution files automatically through `root_dir`. Don't use the `-s` parameter.

### Q3: Why might cmd parameters not be applied?

Common reasons:
1. Using `vim.lsp.config()` instead of `lspconfig.setup()`
2. Path expansion issues (tilde not expanded, relative paths used)
3. Manually adding parameters that get duplicated by `on_new_config`
4. Type mismatches (numbers instead of strings)
5. Specifying `-s` parameter which conflicts with root_dir detection

**Key Point**: Always use `lspconfig.setup()`, use absolute paths, and trust automatic parameter injection.

### Q4: What are known issues with OmniSharp cmd parameter handling?

- **vim.lsp.config() vs setup()**: vim.lsp.config() doesn't trigger `on_new_config`
- **Path expansion**: Tilde and environment variables not expanded
- **Multiple solutions**: Duplicate `-s` flags in single command
- **mason-lspconfig**: May not configure root_dir correctly
- **Parameter duplication**: Manually adding flags that get added again
- **Type errors**: Numbers instead of strings in cmd array

---

## Correct Configuration Example

```lua
require('lspconfig').omnisharp.setup {
  cmd = { 
    "dotnet",
    vim.fn.expand("~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll")
  },
  
  -- Let on_new_config add: --languageserver, --hostPID, -z
  -- Let root_dir find: .sln, .csproj files
  -- Don't add -s parameter
  
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
  enable_import_completion = true,
  
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = nil,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
  },
}
```

---

## Key Takeaways

1. **Two-stage process**: Base cmd + automatic parameter injection via `on_new_config`

2. **The `-s` parameter**: NOT automatically added, and you shouldn't manually add it

3. **Solution discovery**: Use automatic `root_dir` detection, not `-s` parameter

4. **Path handling**: Always use absolute paths with `vim.fn.expand()` for dynamic paths

5. **Use setup()**: Always use `lspconfig.omnisharp.setup()`, not `vim.lsp.config()`

6. **Don't duplicate**: Don't manually add parameters that `on_new_config` appends

7. **Trust the framework**: nvim-lspconfig is designed to work without `-s` parameter

---

## Debugging Commands

```vim
" Check the actual cmd being executed
:LspInfo

" View LSP errors and logs
:LspLog

" Check detailed OmniSharp logs
:!tail -f ~/.local/state/nvim/lsp.log
```

---

## Documentation Sources

- nvim-lspconfig GitHub: https://github.com/neovim/nvim-lspconfig
- nvim-lspconfig docs: https://www.andersevenrud.net/neovim.github.io/lsp/configurations/omnisharp/
- OmniSharp Configuration: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- Community discussions: Neovim Discourse, Stack Overflow, GitHub Issues

---

## Document Navigation

- **For structured overview**: Read RESEARCH_FINDINGS_SUMMARY.txt first
- **For technical details**: Read OMNISHARP_CMD_PARAMETER_ANALYSIS.md
- **For quick lookup**: Use OMNISHARP_CMD_QUICK_REFERENCE.md

---

Generated: November 12, 2025
