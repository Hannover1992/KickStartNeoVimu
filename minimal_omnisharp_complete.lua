-- ============================================================================
-- COMPLETE MINIMAL OMNISHARP CONFIGURATION FOR NEOVIM 0.11
-- ============================================================================
-- This version includes ALL necessary command-line arguments that nvim-lspconfig
-- would normally add automatically. This is the "pure Neovim 0.11" approach
-- with zero external plugin dependencies.
--
-- USAGE:
--   nvim -u minimal_omnisharp_complete.lua /path/to/YourFile.cs
--
-- REQUIREMENTS:
--   1. Neovim 0.11+
--   2. OmniSharp.dll exists at the specified path
--   3. .NET SDK installed (dotnet command available)
--   4. StyleCop.Analyzers NuGet package in your .csproj (for StyleCop warnings)
--
-- ============================================================================

vim.g.mapleader = ' '
vim.o.number = true
vim.o.signcolumn = 'yes'

-- ============================================================================
-- CONFIGURATION - CHANGE THESE PATHS FOR YOUR SYSTEM
-- ============================================================================

-- Path to your C# solution directory (must contain .sln file)
local solution_path = vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src')

-- Path to OmniSharp.dll (if installed via Mason, this should be correct)
local omnisharp_dll = vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll'

-- Alternative if you installed manually:
-- local omnisharp_dll = '/opt/omnisharp/OmniSharp.dll'

-- ============================================================================
-- OMNISHARP CONFIGURATION WITH ALL COMMAND-LINE ARGS
-- ============================================================================

vim.lsp.config('omnisharp', {
  -- Command to start OmniSharp
  cmd = {
    'dotnet',
    omnisharp_dll,

    -- Solution/Project Discovery
    '-s', solution_path,                        -- Solution path (OmniSharp loads all projects in .sln)

    -- Logging
    '-loglevel', 'Information',                 -- Log level (Debug|Information|Warning|Error)

    -- Protocol Settings (normally added by nvim-lspconfig)
    '-z',                                       -- Zero-based line numbers (LSP protocol requirement)
    '--hostPID', tostring(vim.fn.getpid()),    -- Parent process PID (for cleanup on exit)
    'DotNet:enablePackageRestore=false',       -- Disable NuGet restore during LSP operations
    '--encoding', 'utf-8',                     -- Communication encoding
    '--languageserver',                         -- Run in language server mode

    -- Roslyn Analyzers (StyleCop, etc.)
    'RoslynExtensionsOptions:EnableAnalyzersSupport=true',      -- REQUIRED for StyleCop warnings
    'RoslynExtensionsOptions:EnableImportCompletion=true',      -- Show unimported types in completion
    'RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false',   -- Analyze entire solution, not just open files

    -- Formatting
    'FormattingOptions:EnableEditorConfigSupport=true',         -- Respect .editorconfig
    'FormattingOptions:OrganizeImports=true',                   -- Organize usings on format

    -- SDK Settings
    'Sdk:IncludePrereleases=true',                              -- Include .NET preview SDKs
  },

  -- File types that trigger this LSP
  filetypes = { 'cs', 'vb' },

  -- How to find the project root (looks upward for these files)
  root_dir = vim.fs.root(0, { '*.sln', '*.csproj', 'omnisharp.json', 'function.json' }),

  -- Initialize options (can add extra init params here if needed)
  init_options = {},
})

-- ============================================================================
-- LSP ACTIVATION - Enable OmniSharp on C# files
-- ============================================================================

vim.api.nvim_create_autocmd('FileType', {
  pattern = { 'cs', 'vb' },
  callback = function(ev)
    vim.lsp.enable('omnisharp', ev.buf)
  end,
})

-- ============================================================================
-- LSP KEYBINDINGS - Set up when LSP attaches to buffer
-- ============================================================================

vim.api.nvim_create_autocmd('LspAttach', {
  callback = function(event)
    local map = function(keys, func, desc)
      vim.keymap.set('n', keys, func, { buffer = event.buf, desc = 'LSP: ' .. desc })
    end

    -- Navigation
    map('gd', vim.lsp.buf.definition, '[G]oto [D]efinition')
    map('gr', vim.lsp.buf.references, '[G]oto [R]eferences')
    map('gI', vim.lsp.buf.implementation, '[G]oto [I]mplementation')
    map('gD', vim.lsp.buf.declaration, '[G]oto [D]eclaration')
    map('gy', vim.lsp.buf.type_definition, '[G]oto T[y]pe Definition')

    -- Documentation
    map('K', vim.lsp.buf.hover, 'Hover Documentation')
    map('<C-k>', vim.lsp.buf.signature_help, 'Signature Help')

    -- Code Actions
    map('<leader>ca', vim.lsp.buf.code_action, '[C]ode [A]ction')
    map('<leader>rn', vim.lsp.buf.rename, '[R]e[n]ame Symbol')

    -- Formatting
    map('<leader>f', function()
      vim.lsp.buf.format({ async = false })
    end, '[F]ormat Buffer')

    -- Workspace
    map('<leader>wa', vim.lsp.buf.add_workspace_folder, '[W]orkspace [A]dd Folder')
    map('<leader>wr', vim.lsp.buf.remove_workspace_folder, '[W]orkspace [R]emove Folder')
    map('<leader>wl', function()
      print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
    end, '[W]orkspace [L]ist Folders')
  end,
})

-- ============================================================================
-- DIAGNOSTIC CONFIGURATION - Appearance and behavior
-- ============================================================================

vim.diagnostic.config({
  -- Show diagnostics as virtual text at end of line
  virtual_text = {
    spacing = 4,
    prefix = '●',
    format = function(diagnostic)
      return string.format('%s (%s)', diagnostic.message, diagnostic.source)
    end,
  },

  -- Show signs in the sign column (gutter)
  signs = true,

  -- Underline errors/warnings
  underline = true,

  -- Don't update diagnostics while typing (performance)
  update_in_insert = false,

  -- Sort by severity (errors first)
  severity_sort = true,

  -- Float window configuration for diagnostic details
  float = {
    border = 'rounded',
    source = 'if_many',  -- Show source if multiple diagnostics
    header = '',
    prefix = '',
  },
})

-- Diagnostic navigation
vim.keymap.set('n', '[d', vim.diagnostic.goto_prev, { desc = 'Previous Diagnostic' })
vim.keymap.set('n', ']d', vim.diagnostic.goto_next, { desc = 'Next Diagnostic' })
vim.keymap.set('n', '<leader>e', vim.diagnostic.open_float, { desc = 'Show Diagnostic [E]rror' })
vim.keymap.set('n', '<leader>q', vim.diagnostic.setloclist, { desc = 'Open Diagnostic [Q]uickfix List' })

-- ============================================================================
-- VERIFICATION - Print status on load
-- ============================================================================

print('================================')
print('Minimal OmniSharp Config Loaded')
print('================================')
print('Solution: ' .. solution_path)
print('OmniSharp: ' .. omnisharp_dll)
print('')
print('Open a .cs file to start LSP.')
print('Use :lua =vim.lsp.get_clients() to verify.')
print('Press K on a symbol to test hover.')
