# OmniSharp cmd Parameter Handling - Quick Reference

## The Problem

Custom cmd parameters you set in nvim-lspconfig often don't work as expected because nvim-lspconfig has an `on_new_config` callback that **automatically appends hard-coded arguments** to your cmd array.

## The Root Cause

```lua
-- You configure:
cmd = { "dotnet", "/path/to/OmniSharp.dll" }

-- But nvim-lspconfig's on_new_config changes it to:
cmd = { 
  "dotnet", "/path/to/OmniSharp.dll",
  "--languageserver", "--hostPID", "12345", "-z",
  "DotNet:enablePackageRestore=false", "--encoding utf-8"
  -- ... plus all your settings as args
}
```

## Critical Insight: The `-s` Parameter is NOT Handled by on_new_config

Unlike `--languageserver`, `--hostPID`, and `-z`, the `-s` parameter (for specifying solution files) is **NOT automatically added** by `on_new_config`. 

However, this doesn't mean you should manually add it because:

1. **nvim-lspconfig uses root_dir for solution discovery** - It automatically searches for `.sln`, `.csproj`, etc.
2. **Duplicate parameters cause issues** - If both root_dir detection and your `-s` parameter find files, you get conflicts
3. **It's not the intended design** - The framework expects you to rely on automatic detection

## Why Your Configuration Might Not Work

| Issue | Reason | Solution |
|-------|--------|----------|
| Settings not applying | Using `vim.lsp.config()` instead of `setup()` | Use `lspconfig.omnisharp.setup()` |
| Path not expanding | Tilde (~) not expanded in cmd | Use `vim.fn.expand("~")` |
| Multiple solution conflicts | Duplicate `-s` flags in cmd | Let root_dir detection handle it |
| LSP won't attach | Invalid cmd path or permissions | Check `:LspLog` for errors |
| Incorrect solution being used | Multiple solutions in workspace | Override `root_dir` pattern if needed |

## What DOES Get Automatically Applied by on_new_config

These are automatically appended and you should NOT manually add them:

```lua
'-z'
'--hostPID' (with your process ID)
'DotNet:enablePackageRestore=false'
'--encoding utf-8'
'--languageserver'
```

Plus all your settings are flattened into command arguments.

## What Does NOT Get Automatically Applied

The `-s` parameter is never automatically added. But you should still rely on automatic root_dir detection instead.

## Correct Configuration Pattern

```lua
require('lspconfig').omnisharp.setup {
  -- Set ONLY the base command
  cmd = { 
    "dotnet",
    vim.fn.expand("~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll")
  },
  
  -- DON'T manually add: --languageserver, --hostPID, -z, etc.
  -- Let on_new_config add those automatically
  
  -- DON'T add -s parameter
  -- Let root_dir detection find solution files
  
  -- DO configure your settings
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
}
```

## How to Debug

1. Open a C# file and check: `:LspInfo`
2. Look at the "cmd:" line to see what's actually being executed
3. If there are errors: `:LspLog`
4. For OmniSharp logs: `:!tail ~/.local/state/nvim/lsp.log`

## Key Takeaways

1. **Don't manually duplicate parameters** that `on_new_config` adds
2. **Don't use `-s` parameter** - rely on automatic root_dir detection  
3. **Use absolute paths** - no tilde or environment variables without `vim.fn.expand()`
4. **Use `setup()` not `vim.lsp.config()`** - only setup() triggers callbacks
5. **Trust the framework** - nvim-lspconfig is designed to work without `-s` parameter

---

## Common Mistakes and Fixes

### Mistake 1: Manually Adding Parameters

```lua
-- WRONG
cmd = { 
  omnisharp_bin, 
  "--languageserver",  -- on_new_config already adds this
  "--hostPID", tostring(pid)  -- on_new_config already adds this
}

-- CORRECT
cmd = { omnisharp_bin }
```

### Mistake 2: Using Tilde in Path

```lua
-- WRONG
cmd = { "~/.local/share/nvim/mason/bin/OmniSharp" }

-- CORRECT
cmd = { vim.fn.expand("~/.local/share/nvim/mason/bin/OmniSharp") }
```

### Mistake 3: Adding Solution File Parameter

```lua
-- WRONG - Creates conflicts with root_dir detection
cmd = { 
  omnisharp_bin,
  "-s", "/path/to/solution.sln"
}

-- CORRECT - Let root_dir find it automatically
cmd = { omnisharp_bin }
-- nvim-lspconfig automatically searches for .sln files
```

### Mistake 4: Using vim.lsp.config() Instead of setup()

```lua
-- WRONG - on_new_config not called
vim.lsp.config("omnisharp", { cmd = { ... } })

-- CORRECT - on_new_config is called
require('lspconfig').omnisharp.setup { cmd = { ... } }
```

---

## How Parameters Flow Through the System

```
Your Config
  ↓
nvim-lspconfig.setup() called
  ↓
on_new_config callback executed
  ↓
Parameters appended to cmd array
  ↓
OmniSharp process spawned with final cmd
  ↓
OmniSharp uses root_dir to find solution files
```

