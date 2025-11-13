# OmniSharp LSP Configuration - Quick Reference Card

**One-page cheat sheet for OmniSharp configuration in kickstart.nvim**

---

## The Essential Pattern

```lua
local servers = {
  omnisharp = {
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', '/path/to/your/solution',
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
  },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}
```

**That's it.** Everything else is automatic.

---

## Critical Rules (Don't Break These!)

| Rule | Why | Fix |
|------|-----|-----|
| Don't call setup() twice | Only first call works | One setup() in handler only |
| Don't skip the handler | Ensures correct timing | Use default handler pattern |
| PascalCase in Lua | How nvim-lspconfig expects it | `EnableAnalyzersSupport` not `enableAnalyzersSupport` |
| Start cmd with 'dotnet' | OmniSharp is a .NET app | `{ 'dotnet', '/path/to/dll', ... }` |
| Put settings in 'settings =' table | on_new_config expects it there | `settings = { RoslynExtensionsOptions = { ... } }` |

---

## Verification Checklist

```bash
# Check process has all your settings
ps aux | grep omnisharp | grep -v grep
# Should show: RoslynExtensionsOptions:EnableAnalyzersSupport=true

# Check OmniSharp is installed
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

# Check .editorconfig exists
ls /path/to/solution/.editorconfig

# Check StyleCop package
grep StyleCop /path/to/project.csproj

# Clear cache if needed
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp
```

---

## Essential Settings

### To Enable Roslyn Analyzers (MUST HAVE)
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
}
```

### To Use .editorconfig Rules (RECOMMENDED)
```lua
FormattingOptions = {
  EnableEditorConfigSupport = true,
}
```

### To Show Unimported Types (OPTIONAL)
```lua
RoslynExtensionsOptions = {
  EnableImportCompletion = true,
}
```

### For Large Solutions (OPTIONAL)
```lua
MsBuild = {
  LoadProjectsOnDemand = true,
}
```

---

## Troubleshooting Decision Tree

```
Analyzers not showing?
├─ ps aux shows RoslynExtensionsOptions:EnableAnalyzersSupport=true?
│  ├─ YES → Check .editorconfig and StyleCop package
│  └─ NO → cmd or settings is wrong
├─ OmniSharp running at all?
│  ├─ YES → Keep debugging above
│  └─ NO → Check cmd format or installation
└─ :LspInfo shows omnisharp attached?
   ├─ YES → Everything configured right, problem is elsewhere
   └─ NO → Installation or basic setup issue
```

---

## Quick Commands

```vim
" Check LSP status
:LspInfo

" Restart OmniSharp
:LspRestart

" Show diagnostics
:lua vim.diagnostic.open_float()

" Install OmniSharp
:Mason
```

```bash
# Check actual process
ps aux | grep omnisharp | grep -v grep

# View OmniSharp logs
tail -50 ~/.local/state/nvim/lsp.log

# Clear everything
rm -rf ~/.cache/nvim/luac/ && pkill -f omnisharp
```

---

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Two setup() calls | Second ignored | One in handler only |
| `cmd = { 'OmniSharp' }` | Won't start | Use `{ 'dotnet', '/path/to/OmniSharp.dll', ... }` |
| `enableAnalyzersSupport` in Lua | Not recognized | Use `EnableAnalyzersSupport` (PascalCase) |
| `settings = {` outside of omnisharp config | Ignored | Put inside servers.omnisharp table |
| No .editorconfig | No warnings shown | Create in solution root |
| No StyleCop package | No warnings possible | Add to .csproj: `<PackageReference Include="StyleCop.Analyzers" />` |

---

## What Happens When You Call setup()

1. **on_new_config runs** (automatically)
2. **Settings get flattened** `RoslynExtensionsOptions` → `RoslynExtensionsOptions:*=value`
3. **Hard-coded args added** `-z`, `--hostPID`, etc.
4. **Final cmd built** `{ 'dotnet', '/path/to/dll', ..., 'RoslynExtensionsOptions:EnableAnalyzersSupport=true', ... }`
5. **OmniSharp started** with all arguments
6. **on_attach runs** when server is ready

---

## Files You Need to Edit

1. **Your init.lua** - Add servers.omnisharp config
2. **.editorconfig** - Create in solution root with rules
3. **.csproj** - Ensure StyleCop.Analyzers is referenced

---

## The Three-Part System

```
1. cmd → How to start OmniSharp
          (must be: dotnet /path/to/OmniSharp.dll)

2. settings → What to pass to OmniSharp
              (flattened to cmd args by on_new_config)

3. on_new_config → Automatic transformation
                   (flattens + adds hard-coded args)
```

Result: OmniSharp receives all configuration as command-line arguments.

---

## Verify It's Working

1. `ps aux | grep omnisharp` shows your settings as args
2. `:LspInfo` shows omnisharp as initialized
3. `.editorconfig` file exists with rules
4. `StyleCop.Analyzers` is in `.csproj`
5. Open C# file → warnings appear

---

## Most Important Settings

| Setting | Location | Effect | Required? |
|---------|----------|--------|-----------|
| EnableAnalyzersSupport | RoslynExtensionsOptions | Enable analyzers | YES |
| EnableEditorConfigSupport | FormattingOptions | Read .editorconfig | NO (but recommended) |
| EnableImportCompletion | RoslynExtensionsOptions | Suggest unimported types | NO |
| OrganizeImports | FormattingOptions | Sort using statements | NO |
| AnalyzeOpenDocumentsOnly | RoslynExtensionsOptions | Faster analysis (incomplete) | NO |

---

## For Different Scenarios

### WSL2 with Windows Path
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '/mnt/c/Users/.../Project',  -- WSL path to Windows dir
}
```

### Linux Native
```lua
cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '/home/user/projects/MyProject',
}
```

### macOS
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', vim.fn.expand('~/projects/MyProject'),
}
```

---

## When Something's Wrong

| Symptom | Check | Solution |
|---------|-------|----------|
| Analyzers don't appear | `ps aux \| grep omnisharp` | Check cmd and settings |
| Settings show as `{}` | Use `ps aux` instead | Normal behavior, settings are flattened |
| OmniSharp won't start | Is dotnet installed? | `dotnet --version` |
| Solution not found | Is `-s /path/to/solution` correct? | Fix the path |
| Slow completion | `EnableImportCompletion = true`? | Expected on first use |

---

## Essential Lua Syntax

```lua
-- Correct syntax
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/path/to/OmniSharp.dll',
  '-s', vim.fn.expand('/path/to/solution'),
  '-loglevel', 'Information',
}

-- Correct nested table
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
  },
}

-- Correct setup call
require('lspconfig').omnisharp.setup({
  cmd = { ... },
  settings = { ... },
})
```

---

## Resources

- **Detailed Guide**: OMNISHARP_IMPLEMENTATION_GUIDE.md
- **Technical Deep-Dive**: OMNISHARP_ROSLYN_ANALYZER_RESEARCH.md
- **Troubleshooting**: OMNISHARP_GITHUB_ISSUES_REFERENCE.md
- **Overview**: RESEARCH_SUMMARY_OMNISHARP_ROSLYN.md
- **Navigation**: INDEX_OMNISHARP_RESEARCH.md

---

## The Bottom Line

1. **Define cmd** (how to start OmniSharp)
2. **Define settings** (what settings to pass)
3. **Let handler call setup()** (automatic, don't do it manually)
4. **Verify with ps aux** (check actual process)
5. **Check .editorconfig** (analyzer rules come from there)

Everything else is automatic. The on_new_config function handles flattening settings to arguments.

