# Neovim LSP Settings Debugging Quick Reference

## Quick Answer: How Settings Are Passed to Language Servers

Neovim's LSP client sends configuration to servers via **two separate channels**:

### Channel 1: init_options (One-time, during initialization)
```lua
vim.lsp.config('omnisharp', {
  init_options = {
    RoslynExtensionsOptions = {
      enableRoslynAnalyzers = true,
    }
  }
})
```
- Sent in `initialize` request
- Can only be sent ONCE
- Not updatable after server starts

### Channel 2: settings (Post-initialization, via workspace/didChangeConfiguration)
```lua
vim.lsp.config('omnisharp', {
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,
      organize_imports_on_format = true,
    }
  }
})
```
- Sent via `workspace/didChangeConfiguration` notification
- Sent AFTER initialization completes
- Theoretically updatable at runtime

---

## Verify Settings Are Being Sent

### 1. Check if Server is Running
```vim
:LspInfo
```
Look for "Running" status with a process ID.

### 2. Check Settings in Active Client
```vim
:lua =vim.lsp.get_clients()[1].config.settings
```
Should print the settings table being used.

### 3. Check Full Client Configuration
```vim
:lua =vim.lsp.get_clients()
```
Returns complete client structure including settings.

### 4. Filter for Current Buffer
```vim
:lua =vim.lsp.get_clients({bufnr = 0})
```
Shows which servers are attached to current buffer.

### 5. Enable Debug Logging
```vim
:lua vim.lsp.set_log_level('debug')
:LspLog
```
Shows actual LSP protocol messages sent and received.

---

## Common Configuration Errors

### Error 1: Using `initializationOptions` instead of `init_options`
```lua
-- WRONG (silently ignored)
require('lspconfig').omnisharp.setup({
  initializationOptions = { ... }
})

-- CORRECT
require('lspconfig').omnisharp.setup({
  init_options = { ... }
})
```
**Why:** nvim-lspconfig uses snake_case. Invalid keys produce no error.

### Error 2: Wrong Settings Structure
```lua
-- WRONG (missing omnisharp wrapper)
settings = {
  enable_roslyn_analyzers = true,
}

-- CORRECT
settings = {
  omnisharp = {
    enable_roslyn_analyzers = true,
  }
}
```
**Why:** OmniSharp expects settings under `omnisharp` key.

### Error 3: Case Sensitivity Issues
```lua
-- WRONG (camelCase)
settings = {
  omnisharp = {
    enableRoslynAnalyzers = true,
  }
}

-- CORRECT (snake_case)
settings = {
  omnisharp = {
    enable_roslyn_analyzers = true,
  }
}
```
**Why:** Each server defines exact key names. Check documentation.

### Error 4: Settings Changed After Initialization
```lua
-- WRONG (doesn't notify server)
local clients = vim.lsp.get_clients()
clients[1].config.settings.omnisharp.enable_roslyn_analyzers = false

-- CORRECT (notifies server of change)
local clients = vim.lsp.get_clients()
if clients[1] then
  clients[1].config.settings.omnisharp.enable_roslyn_analyzers = false
  clients[1].notify('workspace/didChangeConfiguration', {
    settings = clients[1].config.settings
  })
end
```

---

## Debugging Checklist

1. **Is server running?**
   ```vim
   :LspInfo
   ```

2. **Are settings in config?**
   ```vim
   :lua =vim.lsp.get_clients()[1].config.settings
   ```

3. **Settings structure correct?** (should be `{ omnisharp = { ... } }`)
   ```vim
   :lua print(vim.inspect(vim.lsp.get_clients()[1].config.settings))
   ```

4. **Case sensitivity right?** (use snake_case, not camelCase)
   - Check server documentation

5. **Key names spelled correctly?**
   - Check for typos

6. **Settings actually sent?**
   ```vim
   :lua vim.lsp.set_log_level('debug')
   :LspLog
   " Look for: workspace/configuration and workspace/didChangeConfiguration
   ```

7. **Server supports this setting?**
   - Check server's documentation for available settings

8. **No conflicting workspace config?**
   ```bash
   ls -la .editorconfig .omnisharp omnisharp.json
   ```

---

## Essential Debugging Commands

| Command | Purpose |
|---------|---------|
| `:LspInfo` | Show LSP server status and attached buffers |
| `:checkhealth vim.lsp` | Full LSP health check |
| `:LspLog` | View LSP protocol messages |
| `:lua =vim.lsp.get_clients()` | List all active clients |
| `:lua =vim.lsp.get_clients({bufnr = 0})` | Show servers for current buffer |
| `:lua vim.lsp.set_log_level('debug')` | Enable debug logging |
| `:lua vim.lsp.set_log_level('trace')` | Enable verbose trace logging |

---

## Settings Transmission Flow

```
1. vim.lsp.config() or vim.lsp.start() called
   ↓
2. Server process launched
   ↓
3. Initialize request sent with init_options
   ↓
4. Server responds to initialize
   ↓
5. workspace/didChangeConfiguration sent with settings
   ↓
6. Server processes settings
   ↓
7. Server ready and operational
```

---

## OmniSharp-Specific Settings Example

### Correct Configuration Structure
```lua
vim.lsp.config('omnisharp', {
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  filetypes = { 'csharp', 'vb' },
  root_markers = { '.sln', '.csproj', '.git' },

  -- Sent during initialization
  init_options = {
    RoslynExtensionsOptions = {
      enableRoslynAnalyzers = true,
      enableEditorConfigSupport = true,
    },
  },

  -- Sent via workspace/didChangeConfiguration
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,
      organize_imports_on_format = true,
      enable_import_completion = true,
    }
  }
})
```

### Verifying OmniSharp Settings
```vim
" Check what settings are loaded
:lua =vim.lsp.get_clients({ name = 'omnisharp' })[1].config.settings

" Check init options
:lua =vim.lsp.get_clients({ name = 'omnisharp' })[1].config.init_options

" See actual protocol exchange in log
:lua vim.lsp.set_log_level('debug')
:LspLog
```

---

## Log File Examples

### What to look for in :LspLog

**Successful initialization:**
```
[TRACE] -->doc: {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"initializationOptions":{...}}}
[TRACE] <--doc: {"jsonrpc":"2.0","id":1,"result":{...}}
[TRACE] <--doc: {"jsonrpc":"2.0","method":"workspace/configuration","params":{"items":[{"section":"omnisharp"}]},"id":2}
[TRACE] -->doc: {"jsonrpc":"2.0","id":2,"result":[{"omnisharp":{...}}]}
```

**Settings not sent (problem):**
```
[TRACE] -->doc: {"jsonrpc":"2.0","id":1,"method":"initialize"...}
[TRACE] <--doc: {"jsonrpc":"2.0","id":1,"result":{...}}
[ERROR] Server failed to start  <-- Settings not even attempted
```

**Server ignoring settings (problem):**
```
[TRACE] <--doc: {"jsonrpc":"2.0","method":"workspace/configuration"...}
[ERROR] Unknown configuration section: "typo_omnisharp"  <-- Wrong key name
```

---

## Neovim 0.11+ Modern Approach

### File-based LSP Configuration
Create `~/.config/nvim/lsp/omnisharp.lua`:
```lua
return {
  cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') },
  filetypes = { 'csharp', 'vb' },
  root_markers = { '.sln', '.csproj', '.git' },
  init_options = {
    RoslynExtensionsOptions = {
      enableRoslynAnalyzers = true,
    }
  },
  settings = {
    omnisharp = {
      enable_roslyn_analyzers = true,
      organize_imports_on_format = true,
    }
  }
}
```

In `init.lua`:
```lua
vim.lsp.enable('omnisharp')
```

---

## Quick Debugging Function

Add this to your config for quick diagnostics:

```lua
local function lsp_debug()
  print("\n=== LSP Debug ===\n")

  local clients = vim.lsp.get_clients()
  if #clients == 0 then
    print("ERROR: No LSP clients running!")
    return
  end

  for i, client in ipairs(clients) do
    print(string.format("Client %d: %s", i, client.name))
    print("Settings:")
    print(vim.inspect(client.config.settings))
    print("Init Options:")
    print(vim.inspect(client.config.init_options))
    print("---")
  end
end

vim.api.nvim_create_user_command('LspDebug', lsp_debug, {})
```

Usage: `:LspDebug`

---

## Key Takeaways

1. **Settings go in two places:**
   - `init_options` → sent during initialization (one-time)
   - `settings` → sent via workspace/didChangeConfiguration (after init)

2. **Settings are server-specific:**
   - Check the server's documentation for valid keys and structure

3. **Case sensitivity matters:**
   - nvim-lspconfig uses `init_options` (snake_case)
   - Individual setting keys depend on the server (usually snake_case)

4. **Silent failures are common:**
   - Invalid key names don't produce errors, just silently ignored
   - Always verify with `:lua =vim.lsp.get_clients()[1].config.settings`

5. **Debug with `:LspLog`:**
   - See actual protocol messages
   - Verify settings are being sent and received

6. **Server must be running:**
   - Check `:LspInfo` first
   - If not running, check `:checkhealth vim.lsp` and `:LspLog` for errors

---

## References

- Official Neovim LSP docs: `:help lsp`
- OmniSharp LSP config: https://github.com/OmniSharp/omnisharp-roslyn/wiki/LSP-Specific-Configuration
- Neovim 0.11 changes: https://neovim.io/doc/user/lsp.html
