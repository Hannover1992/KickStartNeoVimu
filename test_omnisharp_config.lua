#!/usr/bin/env nvim --headless -c "luafile %" -c "quit"
-- Minimal OmniSharp Configuration Test Script
-- Based on Phase 1 research findings from OMNISHARP_CMD_PARAMETER_ANALYSIS.md
-- Tests the exact command-line arguments that will be passed to OmniSharp

print("=== OmniSharp Minimal Configuration Test ===\n")

-- Phase 1: Load lspconfig
local status_ok, lspconfig = pcall(require, 'lspconfig')
if not status_ok then
  print("ERROR: lspconfig not found!")
  print("Install with: :Lazy install nvim-lspconfig")
  return
end
print("✓ lspconfig loaded successfully")

-- Phase 2: Define minimal configuration
-- Based on research finding: "cmd format is always: ['dotnet', '<path-to-dll>']"
local mason_path = vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll')
local cmd = { 'dotnet', mason_path }

print("\n--- Command Configuration ---")
print("cmd[1]: " .. cmd[1])
print("cmd[2]: " .. cmd[2])

-- Phase 3: Define minimal settings
-- Based on research finding: "RoslynExtensionsOptions.EnableAnalyzersSupport = true (not enable_roslyn_analyzers)"
local settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- Phase 1 research: correct property name
  },
}

print("\n--- LSP Settings (init_options) ---")
print("RoslynExtensionsOptions.EnableAnalyzersSupport = " .. tostring(settings.RoslynExtensionsOptions.EnableAnalyzersSupport))

-- Phase 4: Verify paths exist
print("\n--- Path Verification ---")
local dll_exists = vim.fn.filereadable(mason_path) == 1
print("OmniSharp DLL exists: " .. tostring(dll_exists))
if dll_exists then
  print("  Path: " .. mason_path)
else
  print("  Expected path: " .. mason_path)
  print("  ERROR: DLL not found! Install with :Mason → omnisharp")
end

local dotnet_available = vim.fn.executable('dotnet') == 1
print("dotnet executable found: " .. tostring(dotnet_available))
if dotnet_available then
  local handle = io.popen('dotnet --version 2>&1')
  local dotnet_version = handle:read('*a'):gsub('\n', '')
  handle:close()
  print("  Version: " .. dotnet_version)
end

-- Phase 5: Show the actual configuration that would be applied
print("\n--- Final lspconfig.omnisharp.setup() Configuration ---")
print([[
lspconfig.omnisharp.setup({
  cmd = { 'dotnet', ']] .. mason_path .. [[' },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
  -- Additional standard config:
  on_attach = function(client, bufnr)
    -- Your keybindings here
  end,
  capabilities = require('cmp_nvim_lsp').default_capabilities(),
})
]])

-- Phase 6: Test actual setup (don't attach, just validate config)
print("\n--- Testing Configuration Application ---")
local test_config = {
  cmd = cmd,
  settings = settings,
  -- Don't actually attach or start LSP
  autostart = false,
}

local setup_ok, setup_err = pcall(function()
  lspconfig.omnisharp.setup(test_config)
end)

if setup_ok then
  print("✓ Configuration applied successfully (no errors)")
  print("✓ lspconfig.omnisharp.setup() accepted the config")
else
  print("✗ Configuration error: " .. tostring(setup_err))
end

-- Phase 7: Show what command would be executed
print("\n--- Command That Would Be Executed ---")
print("When OmniSharp starts, this exact command will run:")
print("")
print("  " .. table.concat(cmd, ' '))
print("")

-- Phase 8: Research findings summary
print("\n=== Key Research Findings (Phase 1) ===")
print("1. cmd format: {'dotnet', '<path-to-dll>'} (NOT the bash wrapper)")
print("2. Settings: RoslynExtensionsOptions.EnableAnalyzersSupport (NOT enable_roslyn_analyzers)")
print("3. No command-line flags needed (-lsp, -z are automatic)")
print("4. handlers for 'window/logMessage' can be added but are optional")
print("5. organize_imports_on_format, enable_import_completion are NOT OmniSharp settings")
print("")
print("=== Test Complete ===")
