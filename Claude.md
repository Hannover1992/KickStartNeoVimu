# LSP OmniSharp C# Fix Documentation

## Problem
OmniSharp LSP was not attaching to C# files in Neovim. Error message: "No LSP client attached"

## Root Causes
1. OmniSharp command path not properly configured
2. Multiple OmniSharp instances running simultaneously
3. Swap file conflicts preventing proper file access
4. OmniSharp not finding the solution file properly

## Solution Steps

### 1. Kill All Running OmniSharp Processes
```bash
pkill -f omnisharp
# Verify no processes running
ps aux | grep omnisharp | grep -v grep
```

### 2. Clean Swap Files
```bash
rm -f ~/.local/state/nvim/swap/*.swp
```

### 3. Fix OmniSharp Configuration in init.lua
Updated the OmniSharp configuration to use the correct Mason installation path:

```lua
omnisharp = {
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
  enable_import_completion = true,
  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.INFO)
    end,
  },
},
```

### 4. Verify Installation
```bash
# Check OmniSharp is installed via Mason
ls ~/.local/share/nvim/mason/bin/ | grep -i omni

# Test OmniSharp can start
~/.local/share/nvim/mason/bin/OmniSharp --version
```

### 5. Restart Neovim
1. Exit Neovim: `:qa!`
2. Open a C# file in your project
3. Check LSP status with `:LspInfo`
4. OmniSharp should now attach automatically

## Verification
- Run `:LspInfo` - should show OmniSharp as attached
- Test `gd` (Go to Definition) on a C# symbol
- Test `grr` (Find References) on a C# symbol
- Test `K` (Hover) for documentation

## Additional Notes
- OmniSharp automatically finds the solution file in parent directories
- No need to specify the solution file path in the command
- The LSP will load all projects in the solution (may take a moment for large solutions)