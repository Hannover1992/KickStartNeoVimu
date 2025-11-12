-- Neovim LSP Configuration Examples
-- Demonstrates how to configure language servers with proper settings handling

-- ============================================================================
-- EXAMPLE 1: OmniSharp (C#) Configuration - Complete Example
-- ============================================================================

local omnisharp_config = {
  -- Command to start the server
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },

  -- File types to attach to
  filetypes = { 'csharp', 'vb' },

  -- Root directory markers (detects project root)
  root_markers = { '.sln', '.csproj', '.git' },

  -- Initialization options (sent during initialize request)
  -- These are OmniSharp-specific and configure Roslyn
  init_options = {
    RoslynExtensionsOptions = {
      enableRoslynAnalyzers = true,
      enableEditorConfigSupport = true,
      enableNugetMetadataInformation = true,
      analyzeOpenDocumentsOnly = false,
    },
    FormattingOptions = {
      insertSpaces = true,
      tabSize = 4,
      indentStyle = 'space',
    },
  },

  -- Settings (sent via workspace/didChangeConfiguration after init)
  -- These control OmniSharp behavior
  settings = {
    omnisharp = {
      -- Roslyn analyzers
      enable_roslyn_analyzers = true,
      organize_imports_on_format = true,
      enable_import_completion = true,

      -- Code generation
      code_generation_options = {
        property_generation_behavior = 'auto',
      },

      -- Completion
      enable_completion = true,
      max_completion_details = 25,
    }
  },

  -- Optional: Callback when server initializes
  on_init = function(client)
    print('[OmniSharp] Initialization successful!')

    -- You could send additional notifications here if needed
    client.notify('workspace/didChangeConfiguration', {
      settings = client.config.settings
    })
  end,

  -- Optional: Called when server attaches to buffer
  on_attach = function(client, bufnr)
    print('[OmniSharp] Attached to buffer ' .. bufnr)

    -- Can set buffer-local keybindings here
    -- Example:
    -- vim.keymap.set('n', 'gd', vim.lsp.buf.definition, { buffer = bufnr })
  end,
}

-- Configure with Neovim 0.11+ API
vim.lsp.config('omnisharp', omnisharp_config)

-- Or with nvim-lspconfig
-- require('lspconfig').omnisharp.setup(omnisharp_config)

---

-- ============================================================================
-- EXAMPLE 2: Rust-Analyzer Configuration
-- ============================================================================

local rust_analyzer_config = {
  cmd = { 'rust-analyzer' },
  filetypes = { 'rust' },
  root_markers = { 'Cargo.toml' },

  settings = {
    ['rust-analyzer'] = {
      cargo = {
        allFeatures = true,
      },
      checkOnSave = {
        command = 'clippy',
      },
      inlayHints = {
        enable = true,
        typeHints = {
          enable = true,
        },
        chainingHints = {
          enable = true,
        },
      },
    }
  }
}

vim.lsp.config('rust_analyzer', rust_analyzer_config)

---

-- ============================================================================
-- EXAMPLE 3: Lua Language Server Configuration
-- ============================================================================

local lua_ls_config = {
  cmd = { 'lua-language-server' },
  filetypes = { 'lua' },
  root_markers = { '.luarc.json', '.luarc.jsonc' },

  settings = {
    Lua = {
      runtime = {
        version = 'LuaJIT',
        path = { 'lua/?.lua', 'lua/?/init.lua' },
      },
      diagnostics = {
        globals = { 'vim' },
      },
      telemetry = {
        enable = false,
      },
      workspace = {
        checkThirdParty = false,
        library = {
          vim.env.VIMRUNTIME,
        },
      },
    },
  }
}

vim.lsp.config('lua_ls', lua_ls_config)

---

-- ============================================================================
-- EXAMPLE 4: TypeScript/JavaScript Configuration
-- ============================================================================

local typescript_config = {
  cmd = { 'typescript-language-server', '--stdio' },
  filetypes = { 'typescript', 'typescriptreact', 'javascript', 'javascriptreact' },
  root_markers = { 'tsconfig.json', 'package.json' },

  settings = {
    typescript = {
      tsdk = '/path/to/node_modules/typescript/lib',
      enablePromptUseWorkspaceTsdk = true,
    }
  }
}

vim.lsp.config('typescript_language_server', typescript_config)

---

-- ============================================================================
-- EXAMPLE 5: Debugging LSP Configuration - Utility Functions
-- ============================================================================

--- Print all active LSP clients and their settings
local function debug_lsp_clients()
  print("\n=== LSP Clients Debug ===\n")

  local clients = vim.lsp.get_clients()

  if #clients == 0 then
    print("ERROR: No LSP clients active!")
    return
  end

  for i, client in ipairs(clients) do
    print(string.format("Client %d: %s (ID: %d, PID: %s)", i, client.name, client.id, client.pid or "N/A"))
    print(string.format("  Command: %s", table.concat(client.cmd, " ")))
    print(string.format("  Filetypes: %s", table.concat(client.config.filetypes or {}, ", ")))
    print(string.format("  Root: %s", client.config.root_dir or "N/A"))

    -- Show init_options
    if client.config.init_options and next(client.config.init_options) then
      print("  Init Options:")
      local inspect_str = vim.inspect(client.config.init_options)
      for line in inspect_str:gmatch("[^\n]+") do
        print("    " .. line)
      end
    else
      print("  Init Options: (none)")
    end

    -- Show settings
    if client.config.settings and next(client.config.settings) then
      print("  Settings:")
      local inspect_str = vim.inspect(client.config.settings)
      for line in inspect_str:gmatch("[^\n]+") do
        print("    " .. line)
      end
    else
      print("  Settings: (none)")
    end

    -- Show attached buffers
    local attached_buffers = vim.lsp.get_buffers_by_client_id(client.id)
    print(string.format("  Attached Buffers: %s", table.concat(attached_buffers, ", ") or "(none)"))

    -- Show server capabilities
    print("  Capabilities:")
    if client.server_capabilities then
      local caps = client.server_capabilities
      if caps.codeActionProvider then print("    - Code Actions") end
      if caps.completionProvider then print("    - Completion") end
      if caps.definitionProvider then print("    - Definition") end
      if caps.hoverProvider then print("    - Hover") end
      if caps.referencesProvider then print("    - References") end
      if caps.renameProvider then print("    - Rename") end
    end

    print()
  end
end

--- Print settings for a specific client
local function debug_client_settings(client_name)
  local clients = vim.lsp.get_clients({ name = client_name })

  if #clients == 0 then
    print(string.format("ERROR: Client '%s' not found", client_name))
    return
  end

  local client = clients[1]
  print(string.format("\n=== %s Settings ===\n", client_name))
  print(vim.inspect(client.config.settings))
end

--- Verify settings are being sent to server
local function verify_settings_transmission(client_name)
  print(string.format("\n=== Verifying %s Settings Transmission ===\n", client_name))

  local clients = vim.lsp.get_clients({ name = client_name })

  if #clients == 0 then
    print(string.format("ERROR: Client '%s' not running!", client_name))
    print("Check: :LspInfo")
    return
  end

  local client = clients[1]

  print("1. Client running: YES")
  print(string.format("   PID: %s", client.pid or "N/A"))

  print("\n2. Settings configured:")
  if client.config.settings and next(client.config.settings) then
    print("   YES")
    print("   " .. vim.inspect(client.config.settings):gsub("\n", "\n   "))
  else
    print("   NO (settings table is empty)")
  end

  print("\n3. Init options configured:")
  if client.config.init_options and next(client.config.init_options) then
    print("   YES")
    print("   " .. vim.inspect(client.config.init_options):gsub("\n", "\n   "))
  else
    print("   NO (init_options table is empty)")
  end

  print("\n4. Buffers attached:")
  local attached = vim.lsp.get_buffers_by_client_id(client.id)
  if #attached > 0 then
    print(string.format("   YES - %d buffer(s)", #attached))
  else
    print("   NO (not attached to any buffers)")
  end

  print("\n5. To view protocol messages:")
  print("   Run: :lua vim.lsp.set_log_level('debug')")
  print("   Then: :LspLog")
  print("   Look for: 'workspace/didChangeConfiguration'")
end

--- Send settings to server after initialization
local function send_settings_to_server(client_name, settings)
  local clients = vim.lsp.get_clients({ name = client_name })

  if #clients == 0 then
    print(string.format("ERROR: Client '%s' not found", client_name))
    return
  end

  local client = clients[1]
  client.config.settings = settings

  print(string.format("Sending settings to %s...", client_name))
  client.notify('workspace/didChangeConfiguration', {
    settings = settings
  })
  print("Settings sent!")
end

---

-- ============================================================================
-- EXAMPLE 6: Using Debugging Functions
-- ============================================================================

-- Create commands to use the debugging functions
vim.api.nvim_create_user_command('LspDebugAll', debug_lsp_clients,
  { desc = 'Debug all LSP clients' })

vim.api.nvim_create_user_command('LspDebugClient', function(opts)
  debug_client_settings(opts.args)
end, {
  nargs = 1,
  desc = 'Debug specific LSP client',
  complete = function()
    return vim.tbl_map(function(c) return c.name end, vim.lsp.get_clients())
  end
})

vim.api.nvim_create_user_command('LspVerify', function(opts)
  verify_settings_transmission(opts.args)
end, {
  nargs = 1,
  desc = 'Verify LSP settings transmission',
  complete = function()
    return vim.tbl_map(function(c) return c.name end, vim.lsp.get_clients())
  end
})

-- Usage:
-- :LspDebugAll           - Show all clients and settings
-- :LspDebugClient omnisharp - Show OmniSharp settings
-- :LspVerify omnisharp   - Verify OmniSharp settings transmission

---

-- ============================================================================
-- EXAMPLE 7: Settings Validation Utility
-- ============================================================================

--- Validate that settings structure matches server expectations
local function validate_omnisharp_settings(settings)
  print("\n=== Validating OmniSharp Settings ===\n")

  -- Check top-level key
  if not settings.omnisharp then
    print("ERROR: Settings missing 'omnisharp' top-level key!")
    print("Current structure:")
    print(vim.inspect(settings))
    return false
  end

  local omni_settings = settings.omnisharp

  -- Check known keys
  local known_keys = {
    'enable_roslyn_analyzers',
    'organize_imports_on_format',
    'enable_import_completion',
    'enable_completion',
    'max_completion_details',
  }

  print("Checking settings keys...")
  for _, key in ipairs(known_keys) do
    if omni_settings[key] ~= nil then
      print(string.format("  [OK] %s = %s", key, tostring(omni_settings[key])))
    end
  end

  print("\nValidation complete!")
  return true
end

---

-- ============================================================================
-- EXAMPLE 8: Enabling LSP Servers (Neovim 0.11+)
-- ============================================================================

-- After configuring, enable the servers:

-- vim.lsp.enable('omnisharp')
-- vim.lsp.enable('rust_analyzer')
-- vim.lsp.enable('lua_ls')
-- vim.lsp.enable('typescript_language_server')

-- Or enable all configured servers:
-- vim.lsp.enable()

---

-- ============================================================================
-- EXAMPLE 9: Common Issues and Solutions
-- ============================================================================

-- Issue 1: Settings in wrong format
-- WRONG:
-- settings = {
--   enable_roslyn_analyzers = true,  -- Missing omnisharp wrapper!
-- }

-- CORRECT:
-- settings = {
--   omnisharp = {
--     enable_roslyn_analyzers = true,
--   }
-- }

---

-- Issue 2: Using initializationOptions instead of init_options
-- WRONG (nvim-lspconfig specific):
-- require('lspconfig').omnisharp.setup({
--   initializationOptions = { ... }
-- })

-- CORRECT:
-- require('lspconfig').omnisharp.setup({
--   init_options = { ... }
-- })

-- CORRECT (native vim.lsp.config):
-- vim.lsp.config('omnisharp', {
--   init_options = { ... }
-- })

---

-- Issue 3: Case sensitivity in setting keys
-- WRONG:
-- settings = {
--   omnisharp = {
--     enableRoslynAnalyzers = true,  -- camelCase, but OmniSharp expects snake_case
--   }
-- }

-- CORRECT:
-- settings = {
--   omnisharp = {
--     enable_roslyn_analyzers = true,  -- snake_case
--   }
-- }

---

-- ============================================================================
-- EXAMPLE 10: Testing Settings Application
-- ============================================================================

-- After configuring and starting a server, verify:

-- 1. Server is running
--    :LspInfo

-- 2. Settings are configured
--    :lua =vim.lsp.get_clients()[1].config.settings

-- 3. Settings match expected structure
--    :lua print(vim.inspect(vim.lsp.get_clients()[1].config.settings))

-- 4. Settings were sent to server
--    :lua vim.lsp.set_log_level('debug')
--    :LspLog
--    (Search for "workspace/didChangeConfiguration")

-- 5. Server capabilities include what you expect
--    :lua =vim.lsp.get_clients()[1].server_capabilities

---

-- ============================================================================
-- Quick Reference Summary
-- ============================================================================

--[[
SETTINGS TRANSMISSION PATHS:

1. init_options (one-time, during initialization):
   vim.lsp.config() → cmd launched → initialize request sent
   ↓
   Server receives initializationOptions in response to initialize

2. settings (after init, via workspace/didChangeConfiguration):
   vim.lsp.config() → workspace/didChangeConfiguration notification sent
   ↓
   Server responds to workspace/configuration requests

KEY DEBUGGING COMMANDS:

- :LspInfo                          - Server status
- :checkhealth vim.lsp              - Health check
- :LspLog                           - Protocol messages
- :lua =vim.lsp.get_clients()       - All clients with full config
- :lua vim.lsp.set_log_level('debug')  - Enable debug logging
- :LspDebugAll                      - Show all settings (custom command)
- :LspVerify omnisharp              - Verify settings sent (custom command)

COMMON MISTAKES:

1. Using initializationOptions instead of init_options
2. Settings not wrapped in server key (e.g., missing omnisharp wrapper)
3. camelCase instead of snake_case for setting keys
4. Invalid key names (silently ignored, no error message)
5. Not checking server documentation for setting names

VERIFICATION FLOW:

1. vim.lsp.config() called
   ↓ Check: :LspInfo (should show server running)
   ↓
2. Settings passed to LSP client
   ↓ Check: :lua =vim.lsp.get_clients()[1].config.settings
   ↓
3. workspace/didChangeConfiguration sent
   ↓ Check: :LspLog (look for workspace/configuration)
   ↓
4. Server processes settings
   ↓ Check: Server behavior matches settings
]]
