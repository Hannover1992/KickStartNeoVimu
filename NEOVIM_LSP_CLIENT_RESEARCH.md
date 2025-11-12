# Neovim LSP Client Documentation Research

## Overview
This document details Neovim's LSP client settings handling mechanism, debugging methods, and common configuration errors. It covers both the traditional `vim.lsp` API and the modern Neovim 0.11+ `vim.lsp.config` approach.

**Last Updated:** November 12, 2025
**Neovim Versions Covered:** 0.9.x to 0.11+
**Focus Areas:**
- Settings transmission and handling
- Verification methods for configuration
- Common pitfalls and solutions
- Debugging techniques

---

## Part 1: Neovim's Settings Handling Mechanism

### 1.1 Core Concepts

Neovim's LSP client handles server configuration through two distinct channels:

#### vim.lsp.ClientConfig Structure
The configuration passed to `vim.lsp.start()` or `vim.lsp.config()` includes:

```lua
{
  name = 'server_name',              -- Server identifier
  cmd = { executable, args... },     -- Command to start server
  filetypes = { 'lang1', 'lang2' }, -- File types to attach to
  root_markers = { '.git', 'file' }, -- Project root detection
  init_options = {...},              -- Initialization options (sent once)
  settings = {...},                  -- Workspace settings (sent via didChangeConfiguration)
  workspace_folders = {...},         -- Workspace folder configuration
  on_init = function(client) end,    -- Initialization callback
}
```

### 1.2 The Two Configuration Channels

#### Channel 1: init_options (Initialization Phase)

**What it is:**
- Corresponds to `initializationOptions` in LSP specification
- Sent in `initialize` request during server startup
- Can only be sent ONCE during initial connection
- Server-specific, varies by language server

**When it's used:**
- During the LSP initialization handshake
- Before the server is fully initialized
- Not updatable after initialization

**Example (Clangd):**
```lua
init_options = {
  fallbackFlags = { '--std=c23' },
  clangdOnChange = 3000,  -- debounce in ms
}
```

**Example (Omnisharp):**
```lua
init_options = {
  RoslynExtensionsOptions = {
    enableRoslynAnalyzers = true,
    enableEditorConfigSupport = true,
  },
}
```

#### Channel 2: settings (Post-Initialization via workspace/didChangeConfiguration)

**What it is:**
- Server-specific configuration settings
- Sent via `workspace/didChangeConfiguration` notification
- Sent AFTER initialization completes
- Can be updated dynamically during session (in theory)
- Maps directly to LSP `workspace/configuration` requests

**When it's used:**
- After server initialization
- When server requests configuration via `workspace/configuration`
- Runtime configuration updates

**Example (Lua Language Server):**
```lua
settings = {
  Lua = {
    runtime = {
      version = 'LuaJIT',
      path = { 'lua/?.lua', 'lua/?/init.lua' },
    },
    diagnostics = {
      globals = { 'vim' },
    },
    workspace = {
      checkThirdParty = false,
      library = {
        vim.env.VIMRUNTIME,
      },
    },
  },
}
```

**Example (Python Pylance):**
```lua
settings = {
  pylance = {
    disableLanguageServices = false,
    typeCheckingMode = 'strict',
  },
}
```

### 1.3 How Settings Are Transmitted

#### Transmission Flow (Initialization)

```
1. vim.lsp.start() or vim.lsp.config() called
   ↓
2. LSP client launches server with command
   ↓
3. Initialize request sent with init_options
   ↓
4. Server responds with initialize response
   ↓
5. workspace/didChangeConfiguration notification sent with settings
   ↓
6. Server fully initialized and operational
```

#### Key Code Points

**In vim.lsp.start() (Traditional approach):**
```lua
vim.lsp.start({
  name = 'omnisharp',
  cmd = { '/path/to/omnisharp' },
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,
      organize_imports_on_format = true,
    }
  }
})
```

Neovim automatically:
1. Launches the server with `cmd`
2. Sends `initialize` with `init_options`
3. Sends `workspace/didChangeConfiguration` with `settings`

**In vim.lsp.config() (Neovim 0.11+):**
```lua
vim.lsp.config('omnisharp', {
  cmd = { '/path/to/omnisharp' },
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,
    }
  }
})

-- Then enable it
vim.lsp.enable('omnisharp')
```

### 1.4 Settings Case Sensitivity and Nesting

**Important:** Settings are **case-sensitive** and must match server expectations exactly.

```lua
-- CORRECT - OmniSharp expects this structure
settings = {
  omnisharp = {
    enable_roslyn_analyzers = true,
    organize_imports_on_format = true,
  }
}

-- WRONG - Capitalization matters
settings = {
  OmniSharp = {  -- Wrong key name
    enableRoslynAnalyzers = true,
  }
}

-- WRONG - Nested incorrectly
settings = {
  enable_roslyn_analyzers = true,  -- Missing 'omnisharp' wrapper
}
```

#### Server-Specific Settings Keys

Each language server expects different top-level settings keys:

| Server | Settings Key | Example |
|--------|--------------|---------|
| OmniSharp | `omnisharp` | `{ omnisharp = { enable_roslyn_analyzers = true } }` |
| rust-analyzer | `['rust-analyzer']` | `{ ['rust-analyzer'] = { ... } }` |
| Lua LS | `Lua` | `{ Lua = { runtime = {...} } }` |
| Python (Pylance) | `pylance` | `{ pylance = {...} }` |
| TypeScript | `typescript` | `{ typescript = {...} }` |

---

## Part 2: Verifying Settings Are Sent

### 2.1 Debugging with vim.lsp.get_clients()

#### Basic Status Check

**List all active LSP clients:**
```vim
:lua =vim.lsp.get_clients()
```

**Expected output (table structure):**
```lua
{
  {
    id = 1,
    name = 'omnisharp',
    attached_buffers = { 1, 2, 3 },
    cmd = { '/home/user/.local/share/nvim/mason/bin/OmniSharp' },
    config = {
      settings = {
        omnisharp = {
          enable_roslyn_analyzers = true,
          organize_imports_on_format = true,
        }
      },
      -- ... other config fields
    },
    resolved_capabilities = { ... },
  },
  -- ... more clients
}
```

#### Filter for Current Buffer Only

**Check which servers are attached to current buffer:**
```vim
:lua =vim.lsp.get_clients({bufnr = 0})
```

**Or using Neovim's built-in:**
```vim
:LspInfo
```

#### Access Client Settings Programmatically

```lua
-- Get first active client
local clients = vim.lsp.get_clients()
if #clients > 0 then
  local client = clients[1]

  -- Print entire config
  print(vim.inspect(client.config))

  -- Access settings specifically
  print(vim.inspect(client.config.settings))

  -- Check specific setting
  print(client.config.settings.omnisharp.enable_roslyn_analyzers)
end
```

### 2.2 Using :LspInfo Command

**Built-in command to check LSP status:**
```vim
:LspInfo
```

**What it shows:**
- List of configured language servers
- Which servers are running
- Which buffers are attached to which server
- Server capabilities
- Per-client information

**Key information visible:**
- Server name and process ID
- Attached buffers
- Workspace folders
- Capabilities offered by server

### 2.3 LSP Logging and Debugging

#### Enable Debug Logging

```lua
-- Enable debug-level logging
vim.lsp.set_log_level('debug')

-- Enable trace logging (most verbose)
vim.lsp.set_log_level('trace')

-- Normal level
vim.lsp.set_log_level('info')
```

#### View LSP Log File

```vim
:LspLog
```

Opens the LSP log in a new buffer showing all LSP communication.

**Log file location:**
```bash
# On Linux/macOS
~/.local/state/nvim/lsp.log

# On Windows
$env:LOCALAPPDATA\nvim-data\lsp.log
```

**What to look for:**
```
[TRACE] -->doc:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "initializationOptions": { ... },
    ...
  }
}

[TRACE] <--doc:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { ... }
}

[TRACE] <--doc:
{
  "jsonrpc": "2.0",
  "method": "workspace/configuration",
  "params": { "items": [ { "section": "omnisharp" } ] },
  "id": 1
}

[TRACE] -->doc:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": [ { "omnisharp": { "enable_roslyn_analyzers": true } } ]
}
```

#### Check Health Status

```vim
:checkhealth vim.lsp
```

Provides comprehensive health check including:
- LSP client availability
- Buffer attachment status
- Configuration issues
- Common problems

### 2.4 Creating a Debugging Function

**Useful Lua function to inspect settings:**

```lua
local function inspect_lsp_settings()
  local clients = vim.lsp.get_clients()

  for _, client in ipairs(clients) do
    print(string.format("Client: %s (ID: %d)", client.name, client.id))
    print("Settings:")
    print(vim.inspect(client.config.settings))
    print("Init Options:")
    print(vim.inspect(client.config.init_options))
    print("---")
  end
end

-- Make it a command
vim.api.nvim_create_user_command(
  'LspDebug',
  inspect_lsp_settings,
  { desc = 'Inspect LSP client settings' }
)
```

**Usage in Neovim:**
```vim
:LspDebug
```

---

## Part 3: Common Configuration Errors

### 3.1 Settings Not Applied - Root Causes

#### Error 1: Wrong Settings Key Name

**Problem:** Settings silently ignored with no error message

```lua
-- WRONG - Uses initializationOptions (LSP spec name)
require('lspconfig').omnisharp.setup({
  initializationOptions = {  -- Invalid for nvim-lspconfig
    RoslynExtensionsOptions = {
      enableRoslynAnalyzers = true,
    }
  }
})

-- CORRECT - Uses init_options (Neovim convention)
require('lspconfig').omnisharp.setup({
  init_options = {
    RoslynExtensionsOptions = {
      enableRoslynAnalyzers = true,
    }
  }
})
```

**Why:** nvim-lspconfig uses snake_case (`init_options`) instead of camelCase (`initializationOptions`). Invalid keys are silently ignored.

**Detection:**
```lua
-- Check what keys were actually recognized
local clients = vim.lsp.get_clients()
if clients[1].config.initializationOptions then
  print("ERROR: initializationOptions not recognized (use init_options)")
else
  print("OK: Configuration loaded")
end
```

#### Error 2: Wrong Settings Structure

**Problem:** Settings sent to server but nested incorrectly

```lua
-- WRONG - Missing omnisharp wrapper
settings = {
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
}

-- CORRECT - Wrapped in omnisharp key
settings = {
  omnisharp = {
    enable_roslyn_analyzers = true,
    organize_imports_on_format = true,
  }
}
```

**Why:** OmniSharp expects settings under the `omnisharp` key. Settings at top level are ignored.

#### Error 3: Settings Sent to Wrong Server

**Problem:** Settings configured for one server but used for another

```lua
-- If using nvim-lspconfig with multiple servers:
require('lspconfig').omnisharp.setup({
  settings = {
    -- These should be under a key, but might be top-level
    enable_roslyn_analyzers = true,
  }
})

-- Better: use server-specific top-level key
require('lspconfig').omnisharp.setup({
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,
    }
  }
})
```

#### Error 4: Wrong Case in Configuration Keys

**Problem:** Lua is case-sensitive, configuration keys must match exactly

```lua
-- WRONG - camelCase when server expects snake_case
settings = {
  omnisharp = {
    enableRoslynAnalyzers = true,      -- Wrong case
    organizeImportsOnFormat = true,    -- Wrong case
  }
}

-- CORRECT - Check server documentation for exact keys
settings = {
  omnisharp = {
    enable_roslyn_analyzers = true,    -- Correct
    organize_imports_on_format = true, -- Correct
  }
}
```

#### Error 5: Language Server Not Starting

**Problem:** Settings configured but server never starts, so they're never sent

```lua
-- Common reasons:
-- 1. Command path wrong
cmd = { '/wrong/path/to/omnisharp' }

-- 2. Missing root markers - server can't find project root
root_markers = { '.csproj', '.sln' }  -- Might be too restrictive

-- 3. Filetypes don't match current buffer
filetypes = { 'csharp' }  -- Won't attach to 'cs' filetype
```

**Detection:**
```vim
" Check if server is running
:LspInfo

" If server not listed, check logs
:LspLog

" Or run health check
:checkhealth vim.lsp
```

### 3.2 When Settings Are Sent But Not Working

#### Scenario 1: Server Doesn't Support Setting

**Problem:** Setting is valid but server doesn't recognize it

```lua
-- Check server documentation for supported settings
-- OmniSharp supports: https://github.com/OmniSharp/omnisharp-roslyn

settings = {
  omnisharp = {
    enable_roslyn_analyzers = true,     -- Valid
    unknown_setting_here = true,        -- Server ignores this silently
  }
}
```

**Solution:** Review server documentation for exact supported settings

#### Scenario 2: Settings Overridden by editorconfig or other files

**Problem:** Settings sent correctly but server has higher-priority config

```bash
# OmniSharp loads settings in this order (highest priority first):
# 1. .editorconfig files
# 2. omnisharp.json workspace config
# 3. LSP settings from client
```

**Solution:** Check for `.editorconfig` or workspace configuration files overriding settings

#### Scenario 3: Server Hasn't Fully Initialized

**Problem:** Settings sent before server ready

```lua
-- Verify settings sent AFTER server initialization
-- Use on_init callback to confirm

on_init = function(client)
  print("Server initialized, sending settings...")
  client.notify('workspace/didChangeConfiguration',
    { settings = client.config.settings })
  print("Settings sent!")
end
```

#### Scenario 4: Changes to Settings After Server Start

**Problem:** Modifying settings after initialization doesn't send notification

```lua
-- WRONG - Just changing config doesn't notify server
local clients = vim.lsp.get_clients()
clients[1].config.settings.omnisharp.enable_roslyn_analyzers = false

-- CORRECT - Must explicitly notify with workspace/didChangeConfiguration
local clients = vim.lsp.get_clients()
if clients[1] then
  clients[1].config.settings.omnisharp.enable_roslyn_analyzers = false
  clients[1].notify('workspace/didChangeConfiguration', {
    settings = clients[1].config.settings
  })
end
```

---

## Part 4: Debugging Commands and Techniques

### 4.1 Essential Debugging Commands

#### Command 1: :LspInfo

```vim
:LspInfo
```

**Output shows:**
```
Language server protocol (LSP) client:
Version: nvim 0.9.4
- Omnisharp: [-] Stopped (exited with code -1) command: /home/user/.local/share/nvim/mason/bin/OmniSharp
- Rust-analyzer: [✓] Running (pid: 12345) command: rust-analyzer

Server omnisharp (ID: 1):
  filetypes: csharp, vb
  root: /home/user/project
  cmd: /home/user/.local/share/nvim/mason/bin/OmniSharp
  attached buffers: []
  clients:
    id: 1
    workspace folders:
```

**What to check:**
- Is server listed?
- Status: Running or Stopped?
- Process ID?
- Attached buffers?
- Error messages?

#### Command 2: :checkhealth vim.lsp

```vim
:checkhealth vim.lsp
```

**Output includes:**
```
vim.lsp: health#lsp#check
========================================================================
- OK: LSP client is fully functional
- OK: Configured language servers:
  - omnisharp
  - rust_analyzer
```

#### Command 3: :LspLog

```vim
:LspLog
```

**Shows:**
- All LSP protocol messages
- Initialization sequence
- workspace/didChangeConfiguration calls
- workspace/configuration requests
- Server responses
- Error traces

**Example from log:**
```
[DEBUG] 2025-11-12 14:23:45 omnisharp: initialize returned
[TRACE] <--doc:
{
  "jsonrpc": "2.0",
  "method": "workspace/configuration",
  "params": {
    "items": [
      {
        "section": "omnisharp"
      }
    ]
  },
  "id": 2
}
[TRACE] -->doc:
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": [
    {
      "omnisharp": {
        "enable_roslyn_analyzers": true,
        "organize_imports_on_format": true
      }
    }
  ]
}
```

#### Command 4: Inspect Active Clients

```lua
-- List all details
:lua print(vim.inspect(vim.lsp.get_clients()))

-- Or in a more readable way
:lua for _, c in ipairs(vim.lsp.get_clients()) do
  print("Server: " .. c.name)
  print("Settings: " .. vim.inspect(c.config.settings))
end
```

### 4.2 Debugging Script

**Complete debugging Lua script:**

```lua
local function lsp_debug()
  print("\n=== LSP Configuration Debug ===\n")

  local clients = vim.lsp.get_clients()

  if #clients == 0 then
    print("ERROR: No LSP clients running!")
    return
  end

  for i, client in ipairs(clients) do
    print(string.format("Client %d: %s (ID: %d)", i, client.name, client.id))
    print(string.format("  Command: %s", table.concat(client.cmd, " ")))
    print(string.format("  Filetypes: %s", table.concat(client.config.filetypes or {}, ", ")))
    print(string.format("  Root: %s", client.config.root_dir or "N/A"))

    -- Show init_options
    if client.config.init_options and next(client.config.init_options) then
      print("  Init Options:")
      print("    " .. vim.inspect(client.config.init_options):gsub("\n", "\n    "))
    else
      print("  Init Options: (none)")
    end

    -- Show settings
    if client.config.settings and next(client.config.settings) then
      print("  Settings:")
      print("    " .. vim.inspect(client.config.settings):gsub("\n", "\n    "))
    else
      print("  Settings: (none)")
    end

    -- Show attached buffers
    local buffers = vim.lsp.get_buffers_by_client_id(client.id)
    print(string.format("  Attached Buffers: %s", table.concat(buffers, ", ") or "(none)"))

    print()
  end

  print("=== Enable Logging ===")
  print("Run: vim.lsp.set_log_level('debug')")
  print("Then check: :LspLog")
end

-- Create command
vim.api.nvim_create_user_command('LspDebug', lsp_debug, {})
```

**Usage:**
```vim
:LspDebug
```

### 4.3 Log Level Configuration

```lua
-- In init.lua or config

-- Debug level - shows detailed messages
vim.lsp.set_log_level('debug')

-- Trace level - shows everything including full message bodies
vim.lsp.set_log_level('trace')

-- Info level - normal operation (default)
vim.lsp.set_log_level('info')

-- Warn level - only warnings and errors
vim.lsp.set_log_level('warn')

-- Error level - only errors
vim.lsp.set_log_level('error')
```

**Check current log level:**
```lua
:lua print(vim.lsp.get_log_level())
```

### 4.4 Per-Client Debugging

```lua
-- Get specific client
local client = vim.lsp.get_clients({ name = 'omnisharp' })[1]

if client then
  -- Check if server is responsive
  print("Sending test notification...")
  client.notify('workspace/didChangeConfiguration', {
    settings = client.config.settings
  })
  print("Notification sent!")
else
  print("OmniSharp client not found")
end
```

---

## Part 5: Neovim 0.11+ Configuration Changes

### 5.1 Modern vim.lsp.config() Approach

**Neovim 0.11+ introduces new unified API:**

```lua
-- Define configuration
vim.lsp.config('omnisharp', {
  cmd = { '/path/to/omnisharp' },
  filetypes = { 'csharp', 'vb' },
  root_markers = { '.sln', '.csproj', '.git' },
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,
      organize_imports_on_format = true,
    }
  },
  init_options = {
    RoslynExtensionsOptions = {
      enableRoslynAnalyzers = true,
    }
  }
})

-- Enable it
vim.lsp.enable('omnisharp')
```

### 5.2 Advantages Over nvim-lspconfig

| Feature | nvim-lspconfig | vim.lsp.config |
|---------|----------------|----------------|
| Plugin dependency | Yes (separate plugin) | No (built-in) |
| API stability | Stable but plugin updates | Core API stability |
| Configuration method | `setup()` function | `config()` function |
| Key naming | `init_options`, `settings` | `init_options`, `settings` (same) |
| Workspace/configuration | Automatic | Automatic |
| Feature parity | Full | Full (as of 0.11) |

### 5.3 File-Based Configuration (Neovim 0.11+)

**Can store configs in `lsp/` directory:**

```
~/.config/nvim/
├── init.lua
└── lsp/
    ├── omnisharp.lua
    ├── rust_analyzer.lua
    └── lua_ls.lua
```

**Example: ~/.config/nvim/lsp/omnisharp.lua**
```lua
return {
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  filetypes = { 'csharp', 'vb' },
  root_markers = { '.sln', '.csproj' },
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,
      organize_imports_on_format = true,
    }
  }
}
```

**In init.lua:**
```lua
-- Automatically discovers configs from lsp/ folder
vim.lsp.enable('omnisharp')
```

---

## Part 6: OmniSharp-Specific Settings

### 6.1 OmniSharp Settings Reference

**Common OmniSharp settings:**

```lua
settings = {
  omnisharp = {
    -- Roslyn analyzers
    enable_roslyn_analyzers = true,
    organize_imports_on_format = true,
    enable_import_completion = true,

    -- Roslyn extensions
    enable_editorconfig_support = true,

    -- Code generation
    code_generation_options = {
      property_generation_behavior = "auto",
    },

    -- Completion
    enable_completion = true,
    max_completion_details = 25,

    -- Roslyn analyzers list
    roslyn_analyzers_enabled = {
      'CA1001',  -- Types that own disposable fields
      'CA1009',  -- Declare event handlers correctly
    },
  }
}
```

### 6.2 OmniSharp Init Options

**OmniSharp-specific initialization options:**

```lua
init_options = {
  RoslynExtensionsOptions = {
    enableRoslynAnalyzers = true,
    enableEditorConfigSupport = true,
    enableNugetMetadataInformation = true,
    analyzeOpenDocumentsOnly = false,
    documentAnalysisTimeoutMs = 30000,
    inlayHintsOptions = {
      enableForParameters = true,
      enableForLiteralParameters = false,
      enableForObjectCreationParameters = false,
      enableForIndexerParameters = false,
      enableForOtherParameters = false,
    },
  },
  FormattingOptions = {
    insertSpaces = true,
    tabSize = 4,
    indentStyle = 'space',
  },
}
```

---

## Part 7: Debugging Checklist

### 7.1 Settings Not Working? Follow This Checklist:

- [ ] **Server running?**
  ```vim
  :LspInfo
  ```
  Look for "Running" status

- [ ] **Server attached to buffer?**
  ```vim
  :lua =vim.lsp.get_clients({bufnr = 0})
  ```
  Should return non-empty table

- [ ] **Correct settings key name?**
  ```vim
  :lua =vim.lsp.get_clients()[1].config.settings
  ```
  Check output matches expected structure

- [ ] **Settings properly nested?**
  ```lua
  -- Should be: settings = { omnisharp = { ... } }
  -- NOT: settings = { enable_roslyn_analyzers = true }
  ```

- [ ] **Case sensitivity correct?**
  ```lua
  -- Use lowercase with underscores (snake_case)
  -- enable_roslyn_analyzers (correct)
  -- enableRoslynAnalyzers (wrong - this is camelCase)
  ```

- [ ] **Server documentation checked?**
  - OmniSharp: https://github.com/OmniSharp/omnisharp-roslyn/wiki/LSP-Specific-Configuration
  - rust-analyzer: https://rust-analyzer.github.io/manual.html
  - Lua LS: https://luals.github.io/wiki/configuration/

- [ ] **Workspace/didChangeConfiguration sent?**
  ```vim
  :LspLog
  ```
  Search for "workspace/didChangeConfiguration" in log

- [ ] **Server responds to configuration request?**
  ```vim
  :LspLog
  ```
  Look for "workspace/configuration" responses

- [ ] **No conflicting workspace config?**
  ```bash
  # Check for these files that might override settings:
  ls -la .editorconfig .omnisharp omnisharp.json
  ```

- [ ] **LSP log shows errors?**
  ```vim
  :LspLog
  ```
  Look for ERROR or exception messages

### 7.2 Quick Diagnostic Commands

```vim
" Full LSP status
:LspInfo

" Health check
:checkhealth vim.lsp

" View LSP log
:LspLog

" Enable debug logging
:lua vim.lsp.set_log_level('debug')

" List active clients with settings
:lua for _, c in ipairs(vim.lsp.get_clients()) do
  print(c.name .. ": " .. vim.inspect(c.config.settings))
end

" Get all capabilities reported by server
:lua print(vim.inspect(vim.lsp.get_clients()[1].server_capabilities))

" Restart LSP for current buffer
:LspStop
:LspStart
```

---

## Part 8: Common Issues and Solutions

### Issue 1: "No LSP client attached"

**Cause:** Server isn't attached to current buffer

**Solution:**
```vim
" Check attached clients
:lua =vim.lsp.get_clients({bufnr = 0})

" Or use built-in command
:LspInfo

" If empty, check:
" 1. Server running? :LspInfo should show it
" 2. Filetype correct? :echo &filetype
" 3. Root markers found? Server might not recognize project root
```

### Issue 2: Settings sent but ignored by server

**Cause:** Settings key wrong or server doesn't support setting

**Solution:**
```vim
" Check exact settings structure sent
:lua print(vim.inspect(vim.lsp.get_clients()[1].config.settings))

" Check server capabilities for configuration support
:lua print(vim.inspect(vim.lsp.get_clients()[1].server_capabilities))

" Enable debug logging to see actual protocol messages
:lua vim.lsp.set_log_level('debug')
:LspLog

" Look for 'workspace/configuration' messages showing what was sent
```

### Issue 3: init_options not recognized

**Cause:** Using wrong key name in nvim-lspconfig

**Solution:**
```lua
-- WRONG (from LSP spec)
require('lspconfig').omnisharp.setup({
  initializationOptions = { ... }
})

-- CORRECT (nvim-lspconfig uses snake_case)
require('lspconfig').omnisharp.setup({
  init_options = { ... }
})

-- OR with vim.lsp.config (Neovim 0.11+)
vim.lsp.config('omnisharp', {
  init_options = { ... }
})
```

### Issue 4: Settings lost after restart

**Cause:** Configuration not persisted

**Solution:**
```lua
-- Make sure settings are in your config file
-- Not just set temporarily via command
vim.lsp.config('omnisharp', {
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,  -- This must be in persistent config
    }
  }
})
```

---

## Summary Table: Settings Transmission

| Aspect | init_options | settings |
|--------|-------------|----------|
| **LSP Protocol** | initializationOptions | workspace/didChangeConfiguration |
| **When sent** | During initialize request | After initialization |
| **Frequency** | Once | Can update later |
| **Updatable** | No | Yes (theoretically) |
| **Server-specific** | Yes (varies by server) | Yes (varies by server) |
| **nvim-lspconfig key** | `init_options` | `settings` |
| **vim.lsp.config key** | `init_options` | `settings` |
| **Debugging command** | `:LspLog` (see initialize) | `:LspLog` (search workspace/configuration) |

---

## References and Further Reading

### Official Documentation
- **Neovim LSP**: `:help lsp` (in Neovim)
- **Neovim 0.11 LSP**: https://neovim.io/doc/user/lsp.html
- **nvim-lspconfig**: https://github.com/neovim/nvim-lspconfig

### Detailed Guides
- **Neovim LSP Client Guide**: https://vonheikemen.github.io/devlog/tools/neovim-lsp-client-guide/
- **Neovim 0.11 LSP Changes**: https://xnacly.me/posts/2025/neovim-lsp-changes/
- **LSP Specification**: https://microsoft.github.io/language-server-protocol/

### Server-Specific Documentation
- **OmniSharp**: https://github.com/OmniSharp/omnisharp-roslyn/wiki/LSP-Specific-Configuration
- **Rust-analyzer**: https://rust-analyzer.github.io/manual.html
- **Lua LS**: https://luals.github.io/wiki/configuration/

---

## Document Metadata

- **Created**: November 12, 2025
- **Neovim Versions**: 0.9.x, 0.10.x, 0.11.x
- **Plugins Referenced**: nvim-lspconfig, Neovim native LSP
- **Related Documents**:
  - `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/CLAUDE.md`
  - `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/LSP_SPECIFICATION_RESEARCH.md`
  - `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/OMNISHARP_ROSLYN_RESEARCH.md`
