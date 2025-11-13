# MINIMAL OmniSharp Configuration for Kickstart.nvim

## TL;DR - Copy-Paste Solution

Add this to your `servers` table in `init.lua` (around line 673, after `lua_ls` config):

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
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
```

That's it! No other changes needed. The existing mason-lspconfig handler (line 725-734) will automatically pick this up.

## Why This Works

**The Pattern:**
1. Add omnisharp config to the `servers` table (where lua_ls is defined)
2. The mason-lspconfig handler automatically calls `setup()` for each server in this table
3. nvim-lspconfig's `on_new_config` function automatically flattens `settings` into command-line args

**Why previous attempts failed:**
- Calling `lspconfig.omnisharp.setup()` TWICE doesn't work (only first call takes effect)
- If you setup explicitly AFTER mason-lspconfig, the default config was already registered
- Solution: Let mason-lspconfig do its job, just populate the `servers` table correctly

## Installation Steps

1. Install OmniSharp via Mason:
   ```vim
   :Mason
   ```
   Search for "omnisharp" and press `i` to install

2. Edit init.lua - add omnisharp to servers table (line 700):
   ```lua
   local servers = {
     lua_ls = { ... },

     -- Add this:
     omnisharp = {
       cmd = {
         'dotnet',
         vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
         '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
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
   ```

3. Restart Neovim

4. Open a C# file from your project

## Verification

**Check :LspInfo:**
```vim
:LspInfo
```
Should show:
- cmd starts with `{ "dotnet", "/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll", "-s", ... }`
- Client: omnisharp (attached)

**Check running process:**
```bash
ps aux | grep omnisharp | grep -v grep
```
Should show:
- `-s /mnt/c/.../Backend` (solution path)
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
- `RoslynExtensionsOptions:EnableImportCompletion=true`
- `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false`
- `FormattingOptions:EnableEditorConfigSupport=true`
- `FormattingOptions:OrganizeImports=true`

**Test StyleCop warnings:**
Open a C# file with StyleCop warnings (e.g., UserController.cs lines 56-57, 78-79, etc.)
- Wait 10-20 seconds for OmniSharp to fully load
- Should see diagnostic warnings for parameter spacing issues

## Customization

**Different solution path:**
Change the `-s` parameter in `cmd`:
```lua
'-s', vim.fn.expand('~/path/to/your/solution'),
```

**Auto-detect solution:**
To find solution automatically in parent directories:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-loglevel', 'Information',
},
-- Remove the '-s' parameter entirely
```
OmniSharp will search upwards for .sln files.

**Analyze only open files (faster):**
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    AnalyzeOpenDocumentsOnly = true,  -- Changed to true
  },
}
```

## Troubleshooting

**No StyleCop warnings appearing:**
1. Ensure StyleCop.Analyzers NuGet package is installed in project
2. Check `.editorconfig` exists in solution directory
3. Wait longer - OmniSharp takes 10-30 seconds to fully analyze on first load
4. Check logs: `tail -100 ~/.local/state/nvim/lsp.log | grep -i roslyn`

**OmniSharp not starting:**
1. Verify dotnet SDK installed: `dotnet --version`
2. Check OmniSharp DLL exists: `ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll`
3. Clear Lua cache: `rm -rf ~/.cache/nvim/luac/`
4. Restart Neovim

**Settings not loading:**
1. Clear Lua cache: `rm -rf ~/.cache/nvim/luac/`
2. Kill all OmniSharp: `pkill -f omnisharp`
3. Verify config in servers table (not a separate setup call)
4. Check `ps aux | grep omnisharp` shows all settings as command-line args

## Key Lessons

1. **One setup per server** - lspconfig.setup() can only be called once
2. **Use the servers table** - mason-lspconfig handler automatically uses it
3. **Settings auto-flatten** - nvim-lspconfig converts settings to command-line args
4. **Don't setup twice** - Don't call omnisharp.setup() after mason-lspconfig
5. **Trust the handler** - The default handler (line 726-732) is all you need

## References

- Based on working config documented in CLAUDE.md
- Verified working on 2025-11-12
- kickstart.nvim mason-lspconfig pattern (lines 722-735)
- nvim-lspconfig omnisharp on_new_config automatically flattens settings
