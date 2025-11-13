-- COPY THIS: Add to servers table in init.lua (after lua_ls config, around line 700)
-- This is the COMPLETE omnisharp configuration that works.
-- The mason-lspconfig handler will automatically call setup() for you.

omnisharp = {
  -- Direct DLL call with solution path
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
    '-loglevel', 'Information',
  },
  -- Settings are automatically flattened to command-line args by nvim-lspconfig
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,       -- Enables StyleCop analyzers
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,    -- Analyze entire solution
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,    -- Respect .editorconfig
      OrganizeImports = true,
    },
  },
},
