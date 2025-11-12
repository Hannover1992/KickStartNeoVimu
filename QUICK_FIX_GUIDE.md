# Quick Fix Guide: StyleCop Warnings Missing

**Problem:** StyleCop warnings not showing in Neovim, RoslynExtensionsOptions shows as empty in `:LspInfo`

**Root Cause:** nvim-lspconfig flattens settings into cmd arguments, which OmniSharp doesn't parse correctly. The `-s` parameter points to directory instead of solution file.

---

## The Fix (5 Minutes)

### 1. Edit init.lua

Open `/home/uczen/.config/nvim/init.lua` and find the `omnisharp` section (around line 934).

**Replace this:**
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = { ... },
    FormattingOptions = { ... },
  },
  -- ... rest ...
},
```

**With this:**
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  -- Removed: -s parameter (let root_dir auto-detect)
  -- Removed: settings (use omnisharp.json instead)

  on_init = function(client, initialization_result)
    vim.notify('OmniSharp loading...', vim.log.levels.INFO)
  end,
  on_attach = function(client, bufnr)
    vim.notify('OmniSharp loaded! Check :LspInfo', vim.log.levels.INFO)
  end,
  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      local message = result.message
      if message:match('Successfully loaded') then
        vim.notify('[OmniSharp] ' .. message, vim.log.levels.INFO)
      elseif message:match('Failed') or message:match('Error') then
        vim.notify('[OmniSharp] ERROR: ' .. message, vim.log.levels.ERROR)
      end
    end,
  },
},
```

### 2. Verify omnisharp.json Exists

Check that `/mnt/c/.../Backend/omnisharp.json` contains:

```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
```

It already exists in your project! No need to create it.

### 3. Clear NuGet Cache (WSL2 Fix)

```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet restore --force-evaluate --no-cache
```

### 4. Kill OmniSharp and Clear Cache

```bash
pkill -f omnisharp
rm -f ~/.local/state/nvim/lsp.log
rm -f ~/.local/state/nvim/swap/*.swp
```

### 5. Restart Neovim

```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
nvim VDEK.DCSP.Application/SomeFile.cs
```

### 6. Verify It Works

Wait 30 seconds, then:

```vim
:LspInfo
```

Should show:
```
Settings: {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    ...
  }
}
```

Create a test violation:
```csharp
public class test { }  // Should get yellow underline (SA1300)
```

---

## Why This Works

1. **Removed `-s` parameter:** Let nvim-lspconfig auto-detect the solution via root_dir pattern
2. **Removed settings table:** Let omnisharp.json handle configuration (OmniSharp reads it directly from disk)
3. **Cleared NuGet cache:** Ensure StyleCop analyzer DLLs are accessible from WSL

---

## If It Still Doesn't Work

Try Solution B: Point to the actual .sln file:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.sln',
    -- Point to .sln FILE, not directory
  },
},
```

Then restart Neovim.

---

## Troubleshooting Commands

```vim
:LspInfo          " Check if settings are loaded
:LspLog           " Check for errors
:Telescope diagnostics  " See all warnings
```

```bash
ps aux | grep omnisharp  # Check if running
tail -f ~/.local/state/nvim/lsp.log  # Watch logs
```

---

## Expected Timeline

- T+0s: Neovim starts
- T+5s: OmniSharp loads solution
- T+15s: First diagnostics appear
- T+30s: All StyleCop warnings visible

If nothing after 60 seconds, check `:LspLog` for errors.

---

**Full details:** See `FINAL_SOLUTION.md` for comprehensive explanation and troubleshooting.
