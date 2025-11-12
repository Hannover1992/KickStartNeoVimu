# OmniSharp Minimal Configuration Test - Explanation

## Purpose
This test script verifies the minimal working OmniSharp LSP configuration based on Phase 1 research findings. It demonstrates exactly what command-line arguments OmniSharp will receive when started by Neovim.

## How to Run

### Method 1: Headless (Quick Verification)
```bash
cd /mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim
nvim --headless -c "luafile test_omnisharp_config.lua" -c "quit"
```

### Method 2: Interactive (See Output in Neovim)
```bash
nvim test_omnisharp_config.lua
# Then inside Neovim:
:source %
```

### Method 3: Command Line
```bash
nvim -c "luafile test_omnisharp_config.lua"
# Press :quit after viewing output
```

## Expected Output

```
=== OmniSharp Minimal Configuration Test ===

✓ lspconfig loaded successfully

--- Command Configuration ---
cmd[1]: dotnet
cmd[2]: /home/<user>/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

--- LSP Settings (init_options) ---
RoslynExtensionsOptions.EnableAnalyzersSupport = true

--- Path Verification ---
OmniSharp DLL exists: true
  Path: /home/<user>/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
dotnet executable found: true
  Version: 8.0.404 (or your version)

--- Final lspconfig.omnisharp.setup() Configuration ---
lspconfig.omnisharp.setup({
  cmd = { 'dotnet', '/home/<user>/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll' },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
  on_attach = function(client, bufnr)
    -- Your keybindings here
  end,
  capabilities = require('cmp_nvim_lsp').default_capabilities(),
})

--- Testing Configuration Application ---
✓ Configuration applied successfully (no errors)
✓ lspconfig.omnisharp.setup() accepted the config

--- Command That Would Be Executed ---
When OmniSharp starts, this exact command will run:

  dotnet /home/<user>/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

=== Key Research Findings (Phase 1) ===
1. cmd format: {'dotnet', '<path-to-dll>'} (NOT the bash wrapper)
2. Settings: RoslynExtensionsOptions.EnableAnalyzersSupport (NOT enable_roslyn_analyzers)
3. No command-line flags needed (-lsp, -z are automatic)
4. handlers for 'window/logMessage' can be added but are optional
5. organize_imports_on_format, enable_import_completion are NOT OmniSharp settings

=== Test Complete ===
```

## What the Script Tests

### 1. **lspconfig Availability**
- Checks if nvim-lspconfig is installed
- Required for any LSP configuration

### 2. **Command Array Construction**
Based on research finding: *"cmd format is always: ['dotnet', '<path-to-dll>']"*

```lua
cmd = { 'dotnet', mason_path }
```

**NOT:**
```lua
-- WRONG (bash wrapper):
cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') }

-- WRONG (extra flags):
cmd = { 'dotnet', dll_path, '-lsp', '-z' }  -- These are added automatically
```

### 3. **Settings Object Structure**
Based on research finding: *"RoslynExtensionsOptions.EnableAnalyzersSupport = true"*

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- Correct property name
  },
}
```

**NOT:**
```lua
-- WRONG (these don't exist in OmniSharp):
{
  enable_roslyn_analyzers = true,      -- Invalid
  organize_imports_on_format = true,   -- Invalid
  enable_import_completion = true,     -- Invalid
}
```

### 4. **Path Verification**
- Checks if OmniSharp DLL exists at Mason installation path
- Verifies dotnet executable is available
- Shows dotnet version for debugging

### 5. **Configuration Validation**
- Applies configuration to lspconfig
- Catches any Lua errors in config structure
- Does NOT start LSP server (autostart = false)

### 6. **Command Execution Preview**
Shows the EXACT command that will be executed when you open a C# file:
```
dotnet /home/<user>/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
```

## Key Differences from Current Config

### Current init.lua (Potentially Incorrect)
```lua
omnisharp = {
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },  -- Bash wrapper
  enable_roslyn_analyzers = true,           -- Wrong property name
  organize_imports_on_format = true,        -- Not an OmniSharp setting
  enable_import_completion = true,          -- Not an OmniSharp setting
  handlers = { ... },                       -- Optional, but OK
},
```

### Minimal Working Config (Based on Research)
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll')
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,        -- Correct property name
    },
  },
  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      -- Optional logging
    end,
  },
},
```

## Interpreting Results

### ✅ Success Indicators
- `lspconfig loaded successfully`
- `OmniSharp DLL exists: true`
- `dotnet executable found: true`
- `Configuration applied successfully`

### ❌ Failure Indicators

**"lspconfig not found"**
→ Install with: `:Lazy install nvim-lspconfig`

**"OmniSharp DLL exists: false"**
→ Install with: `:Mason` then find omnisharp and press `i`

**"dotnet executable found: false"**
→ Install .NET SDK: https://dotnet.microsoft.com/download

**"Configuration error: ..."**
→ Syntax error in Lua config - check the error message

## Next Steps After Test

### If Test Passes (All ✓)
1. Update your `init.lua` with the minimal config
2. Replace the `omnisharp` section in `servers` table
3. Restart Neovim: `:qa!` then reopen
4. Test on a C# file: `:LspInfo`

### If Test Fails
1. Check error messages in output
2. Install missing components (lspconfig, omnisharp, dotnet)
3. Re-run test script
4. Review Phase 1 research documents:
   - `OMNISHARP_CMD_PARAMETER_ANALYSIS.md`
   - `OMNISHARP_CMD_QUICK_REFERENCE.md`

## Additional Testing

### Test in Real Project
After the script passes:
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
nvim VDEK.DCSP.WebHost/Controllers/UserController.cs
# Inside Neovim:
:LspInfo
# Should show: "Client: omnisharp (id: 1, bufnr: [1])"
```

### Test LSP Features
```vim
gd           → Go to Definition
K            → Hover Documentation
<leader>ca   → Code Actions
grr          → Find References
```

## Reference: Minimal Production Config

Use this in your actual `init.lua`:

```lua
require('lspconfig').omnisharp.setup({
  cmd = {
    'dotnet',
    vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll')
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
  on_attach = function(client, bufnr)
    -- Your standard LSP keybindings
  end,
  capabilities = require('cmp_nvim_lsp').default_capabilities(),
})
```

## Troubleshooting

### "Permission Denied" on DLL
```bash
chmod +x ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
```

### OmniSharp Not Attaching in WSL2
```bash
# In your project directory:
dotnet restore --force-evaluate --no-cache
pkill -f omnisharp
# Then restart Neovim
```

### Want to See OmniSharp Logs
Add to handlers:
```lua
handlers = {
  ['window/logMessage'] = function(err, result, ctx, config)
    vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.INFO)
  end,
},
```

Or check logs:
```vim
:LspLog
```

## Summary

This test script isolates the OmniSharp configuration to verify:
1. ✅ Correct cmd format (dotnet + DLL path)
2. ✅ Correct settings structure (RoslynExtensionsOptions)
3. ✅ All required paths exist
4. ✅ Configuration is syntactically valid
5. ✅ Shows exact command that will execute

Run this test BEFORE modifying your main `init.lua` to ensure the minimal config works.
