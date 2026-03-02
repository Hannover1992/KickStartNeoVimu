-- ============================================================================
-- MINIMAL OMNISHARP CONFIGURATION FOR NEOVIM 0.11
-- ============================================================================
-- This is the absolute minimal configuration to get OmniSharp LSP working.
-- Total: ~30 lines of actual configuration code (excluding comments).
--
-- USAGE:
--   nvim -u minimal_omnisharp.lua /path/to/YourFile.cs
--
-- REQUIREMENTS:
--   1. Neovim 0.11+
--   2. OmniSharp installed via Mason (or manually)
--   3. .NET SDK installed (dotnet command available)
--
-- ============================================================================

-- Set leader key (optional, but useful)
vim.g.mapleader = ' '

-- Basic options for usability
vim.o.number = true
vim.o.signcolumn = 'yes'

-- ============================================================================
-- THE ACTUAL MINIMAL OMNISHARP SETUP (Neovim 0.11 Native API)
-- ============================================================================

-- Path to your C# solution directory (CHANGE THIS!)
local solution_path = vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src')

-- Configure OmniSharp using Neovim 0.11's native vim.lsp.config API
vim.lsp.config('omnisharp', {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', solution_path,
    '-loglevel', 'Information',
  },
  filetypes = { 'cs' },
  root_dir = vim.fs.root(0, { '*.sln', '*.csproj', 'omnisharp.json' }),
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
    Sdk = {
      IncludePrereleases = true,
    },
  },
})

-- Enable OmniSharp when opening C# files
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'cs',
  callback = function(ev)
    vim.lsp.enable('omnisharp', ev.buf)
  end,
})

-- ============================================================================
-- BASIC LSP KEYBINDINGS (Optional but recommended)
-- ============================================================================

vim.api.nvim_create_autocmd('LspAttach', {
  callback = function(event)
    local map = function(keys, func, desc)
      vim.keymap.set('n', keys, func, { buffer = event.buf, desc = 'LSP: ' .. desc })
    end

    map('gd', vim.lsp.buf.definition, '[G]oto [D]efinition')
    map('gr', vim.lsp.buf.references, '[G]oto [R]eferences')
    map('K', vim.lsp.buf.hover, 'Hover Documentation')
    map('<leader>ca', vim.lsp.buf.code_action, '[C]ode [A]ction')
    map('<leader>rn', vim.lsp.buf.rename, '[R]e[n]ame')
  end,
})

-- ============================================================================
-- DIAGNOSTIC CONFIGURATION (Optional but recommended)
-- ============================================================================

vim.diagnostic.config({
  virtual_text = true,
  signs = true,
  underline = true,
  update_in_insert = false,
})

-- Navigation keybinds for diagnostics
vim.keymap.set('n', '[d', vim.diagnostic.goto_prev, { desc = 'Previous diagnostic' })
vim.keymap.set('n', ']d', vim.diagnostic.goto_next, { desc = 'Next diagnostic' })

print('Minimal OmniSharp config loaded. Open a .cs file to start LSP.')
