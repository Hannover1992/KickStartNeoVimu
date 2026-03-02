-- WORKING FIX FOR OMNISHARP IN NEOVIM 0.11.4
-- Copy-paste ready solution using Approach C (Hybrid)
--
-- This file contains the corrected sections from init.lua
-- Replace the corresponding sections in your init.lua with these

-- ============================================================================
-- SECTION 1: Mason-lspconfig setup (Lines 745-749)
-- ============================================================================

require('mason-lspconfig').setup {
  ensure_installed = vim.tbl_keys(servers or {}), -- Ensure all servers in the servers table are installed
  automatic_installation = false,
  -- FIX: Use automatic_enable with exclude instead of false
  -- This lets mason-lspconfig auto-enable all servers EXCEPT omnisharp
  automatic_enable = { exclude = { 'omnisharp' } },
}

-- ============================================================================
-- SECTION 2: Manual OmniSharp Configuration (Replace Lines 754-783)
-- ============================================================================

-- Configure OmniSharp using legacy lspconfig API (still works in Neovim 0.11!)
-- This approach is proven to work and documented in CLAUDE.md
if servers.omnisharp then
  require('lspconfig').omnisharp.setup {
    cmd = servers.omnisharp.cmd,
    settings = servers.omnisharp.settings,
    capabilities = require('blink.cmp').get_lsp_capabilities(),
    -- Optional: Add handlers from servers table if they exist
    handlers = servers.omnisharp.handlers,
    on_init = servers.omnisharp.on_init,
    on_attach = servers.omnisharp.on_attach,
  }
end

-- ============================================================================
-- ALTERNATIVE APPROACH A: Full Auto-Enable (Simplest)
-- ============================================================================

-- If you don't need custom OmniSharp configuration, just use this:
--
-- require('mason-lspconfig').setup {
--   ensure_installed = vim.tbl_keys(servers or {}),
--   automatic_installation = false,
--   automatic_enable = true,  -- Auto-enable ALL servers
-- }
--
-- Then REMOVE lines 754-783 entirely!
-- mason-lspconfig will handle everything automatically.
-- Downside: You lose custom cmd and settings for OmniSharp.

-- ============================================================================
-- ALTERNATIVE APPROACH B: Full Native vim.lsp.config (Advanced)
-- ============================================================================

-- For complete Neovim 0.11 native configuration:
--
-- require('mason-lspconfig').setup {
--   ensure_installed = vim.tbl_keys(servers or {}),
--   automatic_installation = false,
--   automatic_enable = false,
-- }
--
-- if vim.fn.has('nvim-0.11') == 1 then
--   -- Configure OmniSharp with new API
--   vim.lsp.config('omnisharp', {
--     cmd = {
--       'dotnet',
--       vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
--       '-s',
--       vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
--       '-loglevel',
--       'Information',
--     },
--     filetypes = { 'cs' },
--     root_markers = { '*.sln', '*.csproj', '.git' },  -- FIX: Use root_markers instead of root_dir
--     settings = {
--       RoslynExtensionsOptions = {
--         EnableAnalyzersSupport = true,
--         EnableImportCompletion = true,
--         AnalyzeOpenDocumentsOnly = false,
--       },
--       FormattingOptions = {
--         EnableEditorConfigSupport = true,
--         OrganizeImports = true,
--       },
--     },
--     capabilities = require('blink.cmp').get_lsp_capabilities(),
--   })
--
--   -- CRITICAL: Enable the server!
--   vim.lsp.enable('omnisharp')
--
--   -- Configure other servers
--   for server_name, server_config in pairs(servers) do
--     if server_name ~= 'omnisharp' then
--       local config = vim.tbl_deep_extend('force', {}, server_config)
--       config.capabilities = vim.tbl_deep_extend('force', {}, require('blink.cmp').get_lsp_capabilities(), config.capabilities or {})
--
--       -- Get defaults from lspconfig
--       local lspconfig_defaults = require('lspconfig.configs')[server_name]
--       if lspconfig_defaults and lspconfig_defaults.default_config then
--         config.filetypes = config.filetypes or lspconfig_defaults.default_config.filetypes
--
--         -- If lspconfig provides root_markers, use those
--         if lspconfig_defaults.default_config.root_dir and not config.root_markers then
--           -- For simplicity, use root_markers with common patterns
--           config.root_markers = { '.git', 'package.json', 'Cargo.toml', 'go.mod', 'pyproject.toml' }
--         end
--       end
--
--       vim.lsp.config(server_name, config)
--       vim.lsp.enable(server_name)
--     end
--   end
-- else
--   -- Fallback for Neovim < 0.11
--   for server_name, server_config in pairs(servers) do
--     local config = vim.tbl_deep_extend('force', {}, server_config)
--     config.capabilities = vim.tbl_deep_extend('force', {}, require('blink.cmp').get_lsp_capabilities(), config.capabilities or {})
--     require('lspconfig')[server_name].setup(config)
--   end
-- end

-- ============================================================================
-- VERIFICATION STEPS
-- ============================================================================

-- After applying the fix:
--
-- 1. Clear cache and kill OmniSharp:
--    $ rm -rf ~/.cache/nvim/luac/
--    $ pkill -f omnisharp
--
-- 2. Restart Neovim and open a C# file:
--    $ nvim /mnt/c/.../cencoco/src/CenCoCo.Core.API/Program.cs
--
-- 3. Wait 5-10 seconds for OmniSharp to load
--
-- 4. Check LspInfo:
--    :LspInfo
--    Should show omnisharp attached with correct cmd
--
-- 5. Verify process:
--    $ ps aux | grep omnisharp | grep -v grep
--    Should show dotnet process with -s parameter
--
-- 6. Test LSP features:
--    - grd = Go to definition
--    - K = Hover documentation
--    - grr = Find references

-- ============================================================================
-- TECHNICAL EXPLANATION
-- ============================================================================

-- WHY THE CURRENT CODE FAILS:
-- 1. automatic_enable = false prevents mason-lspconfig from auto-enabling servers
-- 2. vim.lsp.config() registers the config but doesn't start the server
-- 3. The root_dir function has wrong signature (lspconfig 0.10 vs vim.lsp.config 0.11)
-- 4. Missing vim.lsp.enable() call to actually start the server
--
-- WHY APPROACH C (RECOMMENDED FIX) WORKS:
-- 1. automatic_enable = { exclude = { 'omnisharp' } } lets mason-lspconfig handle other servers
-- 2. require('lspconfig').omnisharp.setup() uses proven, battle-tested API
-- 3. lspconfig handles root_dir detection automatically (finds .sln files)
-- 4. Custom cmd with -s parameter explicitly specifies solution path
-- 5. Settings are passed correctly to OmniSharp via on_new_config
--
-- NEOVIM 0.11 MIGRATION NOTES:
-- - vim.lsp.config() requires root_dir function with signature: function(bufnr, on_dir)
-- - OR use root_markers array: { '*.sln', '*.csproj', '.git' }
-- - Must call vim.lsp.enable() after vim.lsp.config() to start server
-- - lspconfig's root_dir has incompatible signature: function(filename, bufnr)
-- - The incompatibility causes silent failures when LSP tries to start
