# OmniSharp LSP Configuration for Neovim - Step by Step

## Context

The DCSRE project already has StyleCop.Analyzers properly configured:
- ✅ StyleCop.Analyzers 1.1.118 in VDEK.DCSP.WebApi.csproj
- ✅ stylecop.json configured at Backend root
- ✅ .editorconfig with rule severity set up
- ❌ **MISSING**: OmniSharp LSP configuration in Neovim

When you open a C# file in Neovim with a configured OmniSharp LSP, StyleCop warnings will automatically appear.

---

## What the Current Neovim Config Is

File: `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua`

Currently: **Minimal Kickstart configuration** - No LSP, No OmniSharp setup

To add OmniSharp support, you need to:
1. Install/enable LSP plugins (nvim-lspconfig, mason, mason-lspconfig)
2. Configure OmniSharp server settings
3. Set up keybindings for LSP functionality

---

## Option A: Add to Existing Kickstart (Minimal)

If you want to keep the Kickstart minimal, add these lines to `init.lua`:

```lua
-- At the end of the file (before the final comment)

-- LSP Configuration
local lspconfig = require('lspconfig')

-- OmniSharp for C# development
lspconfig.omnisharp.setup({
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
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

  on_attach = function(client, bufnr)
    vim.notify('OmniSharp attached to buffer ' .. bufnr, vim.log.levels.INFO)
  end,
})

-- LSP Keybindings
vim.keymap.set('n', 'gd', vim.lsp.buf.definition, { noremap = true, silent = true })
vim.keymap.set('n', 'K', vim.lsp.buf.hover, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, { noremap = true, silent = true })
```

### Prerequisites for Option A:
```lua
-- Make sure these plugins are in your lazy.nvim spec:
{
  'neovim/nvim-lspconfig',
  lazy = true,
}
```

---

## Option B: Use nvim-lspconfig Plugin (Recommended)

If using Lazy.nvim (which Kickstart does), add this to your plugin spec:

### Create file: `lua/custom/plugins/lsp.lua`

```lua
return {
  {
    'neovim/nvim-lspconfig',
    dependencies = {
      'williamboman/mason.nvim',
      'williamboman/mason-lspconfig.nvim',
    },
    config = function()
      require('mason').setup()

      local lspconfig = require('lspconfig')

      -- Configure OmniSharp
      lspconfig.omnisharp.setup({
        cmd = {
          'dotnet',
          vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
          '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
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

        on_attach = function(client, bufnr)
          vim.api.nvim_buf_set_option(bufnr, 'omnifunc', 'v:lua.vim.lsp.omnifunc')

          local opts = { noremap = true, silent = true, buffer = bufnr }

          vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
          vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
          vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts)
          vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, opts)
          vim.keymap.set('n', 'grr', vim.lsp.buf.references, opts)
          vim.keymap.set('n', '<leader>f', function()
            vim.lsp.buf.format({ async = true })
          end, opts)
        end,
      })
    end,
  }
}
```

Then in `init.lua`, make sure to include custom plugins:

```lua
-- Around line 987 in the default Kickstart, uncomment:
{ import = 'custom.plugins' },
```

---

## Full Detailed Configuration Explained

### Command Configuration

```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
  '-loglevel', 'Information',
}
```

| Part | Purpose |
|------|---------|
| `'dotnet'` | Use dotnet CLI to run the server |
| `vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll'` | Full path to OmniSharp.dll (Mason installs here) |
| `'-s'` | Solution path flag |
| `/mnt/c/.../Backend` | Path to the Backend folder (where projects are) |
| `'-loglevel', 'Information'` | Verbose logging for debugging |

### Critical Settings

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,          -- MUST be true for StyleCop warnings
  EnableImportCompletion = true,          -- Auto-complete for missing imports
  AnalyzeOpenDocumentsOnly = false,       -- Analyze all files, not just open ones
},
FormattingOptions = {
  EnableEditorConfigSupport = true,       -- Read .editorconfig rules
  OrganizeImports = true,                 -- Remove unused imports on format
},
```

**Why `EnableAnalyzersSupport = true` is critical:**
- Without this, OmniSharp doesn't run Roslyn analyzers (StyleCop, FxCop, etc.)
- Even with StyleCop.Analyzers installed, no warnings will appear in the editor
- Build from command line will still show warnings, but not in Neovim

---

## How to Verify It Works

### Step 1: Install OmniSharp via Mason

```vim
:Mason
" Then search for and install 'omnisharp'
```

Or manually:
```bash
mkdir -p ~/.local/share/nvim/mason/packages/omnisharp
# Mason handles this automatically when you install
```

### Step 2: Open a C# File

```bash
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs
```

### Step 3: Check if OmniSharp Connected

```vim
:LspInfo
```

Should show:
```
Client: omnisharp (id: 1, pid: 12345)
  filetypes: csharp
  cmd: dotnet /home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll -s /mnt/c/.../Backend -loglevel Information
```

### Step 4: Verify Settings Are Applied

```vim
:lua print(vim.inspect(vim.lsp.get_clients()[1].config.settings))
```

Should show:
```
{
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    OrganizeImports = true
  },
  RoslynExtensionsOptions = {
    AnalyzeOpenDocumentsOnly = false,
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true
  }
}
```

### Step 5: Check for Warnings

In the editor, you should see:
- Red/yellow squiggles for StyleCop warnings
- In gutter: Line numbers with diagnostic indicators
- In problems panel: List of warnings with descriptions

Navigate with:
```vim
]d  " Next diagnostic
[d  " Previous diagnostic
K   " Show error details
```

---

## Troubleshooting

### OmniSharp doesn't start

```bash
# Check if DLL path exists
test -f ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll && echo "DLL found" || echo "DLL not found - install with :Mason"

# Check if dotnet is available
which dotnet || echo "dotnet not found"

# Try starting manually
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll --version
```

### OmniSharp starts but no warnings appear

```bash
# Kill OmniSharp
pkill -f omnisharp

# Clear Lua cache
rm -rf ~/.cache/nvim/luac/

# Restart Neovim
# Open C# file again
```

### Verify from command line

```bash
# This should show StyleCop warnings
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet build 2>&1 | grep "SA"
```

If no SA warnings appear from command line:
- StyleCop.Analyzers package is missing
- stylecop.json is missing
- Rules are disabled in .editorconfig
- See STYLECOP_ANALYZERS_CHECKLIST.md

---

## Complete Example Configuration

Here's a complete, working LSP configuration you can use:

### File: `lua/custom/lsp.lua`

```lua
-- Complete OmniSharp and LSP Configuration for DCSRE Project

local lspconfig = require('lspconfig')

-- Global LSP configuration
local on_attach = function(client, bufnr)
  -- Enable completion triggered by <c-x><c-o>
  vim.api.nvim_buf_set_option(bufnr, 'omnifunc', 'v:lua.vim.lsp.omnifunc')

  local opts = { noremap = true, silent = true, buffer = bufnr }

  -- Keybindings
  vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
  vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
  vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
  vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
  vim.keymap.set('n', 'grr', vim.lsp.buf.references, opts)
  vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts)
  vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, opts)
  vim.keymap.set('n', '<leader>f', function()
    vim.lsp.buf.format({ async = true })
  end, opts)

  -- Show diagnostic on hover
  vim.cmd [[autocmd CursorHold <buffer> lua vim.diagnostic.open_float()]]

  vim.notify(string.format('LSP %s attached', client.name), vim.log.levels.INFO)
end

-- OmniSharp Configuration
lspconfig.omnisharp.setup({
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
    '-loglevel', 'Information',
  },

  filetypes = { 'csharp', 'vb' },
  root_markers = { '.sln', '.csproj' },

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

  on_attach = on_attach,
})

-- Diagnostic configuration
vim.diagnostic.config({
  virtual_text = true,
  signs = true,
  underline = true,
  update_in_insert = false,
})

-- Diagnostic signs
local signs = { Error = '✗', Warn = '▲', Hint = '◆', Info = '●' }
for type, icon in pairs(signs) do
  local hl = 'DiagnosticSign' .. type
  vim.fn.sign_define(hl, { text = icon, texthl = hl, numhl = '' })
end
```

### File: `lua/custom/plugins/lsp.lua`

```lua
return {
  {
    'neovim/nvim-lspconfig',
    event = { 'BufReadPre', 'BufNewFile' },
    dependencies = {
      'williamboman/mason.nvim',
      'williamboman/mason-lspconfig.nvim',
    },
    config = function()
      require('mason').setup()
      require('custom.lsp')
    end,
  }
}
```

### Enable in init.lua

Make sure this line is uncommented around line 987:

```lua
{ import = 'custom.plugins' },
```

---

## What You Get

Once configured, you'll have:

### LSP Features
- `gd` - Go to definition
- `grr` - Find references
- `K` - Hover documentation
- `<leader>rn` - Rename symbol
- `<leader>ca` - Code actions (refactorings, fixes)
- `<leader>f` - Format code

### Diagnostics
- Red squiggles for errors
- Yellow squiggles for warnings
- Blue squiggles for suggestions
- `]d` / `[d` - Navigate diagnostics

### StyleCop Specific
- SA1116, SA1117, etc. warnings appear immediately
- Configured via .editorconfig rules
- Auto-format respects EditorConfig settings

---

## Next Steps

1. **Choose configuration option** (A or B above)
2. **Install via Mason**: `:Mason` → search omnisharp → install
3. **Add configuration** to init.lua or lua/custom/plugins/lsp.lua
4. **Restart Neovim**: `:qa!` then reopen
5. **Open C# file**: `:edit /path/to/UserController.cs`
6. **Verify**: `:LspInfo` should show omnisharp connected
7. **See warnings**: StyleCop warnings should appear in editor

---

## Related Documentation

- `STYLECOP_ANALYZERS_CHECKLIST.md` - Complete requirements
- `STYLECOP_QUICK_REFERENCE.md` - Quick troubleshooting
- `LSP_CONFIGURATION_EXAMPLES.lua` - More LSP config examples
- `CLAUDE.md` - Full project setup documentation
