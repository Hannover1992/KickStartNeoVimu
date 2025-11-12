# OmniSharp LSP Settings Guide

Based on official LSP specification research, this guide shows the correct way to configure OmniSharp in Neovim.

---

## 1. Official OmniSharp Configuration Structure

### 1.1 Three Configuration Layers

According to LSP specification:

```lua
omnisharp = {
  -- Layer 1: PROCESS STARTUP (T0)
  -- Sent when spawning the OmniSharp process
  -- Cannot be changed after startup
  -- Controls OS-level behavior
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--stdio'                          -- Required for LSP over stdin/stdout
  },

  -- Layer 2: INITIALIZATION (T2)
  -- Sent during LSP initialize request (one time only)
  -- Server-specific format (not standardized)
  -- Limited usage for OmniSharp
  init_options = {
    -- Most OmniSharp configuration goes in settings instead
    -- This can be empty for OmniSharp
  },

  -- Layer 3: RUNTIME CONFIGURATION (T5+)
  -- Sent via workspace/didChangeConfiguration (can be updated)
  -- Most OmniSharp settings go here
  -- Can change without server restart
  settings = {
    omnisharp = {
      enableRoslynAnalyzers = true,
      organizeImportsOnFormat = true,
      enableImportCompletion = true,
      -- ... more settings
    }
  }
}
```

---

## 2. OmniSharp LSP Settings Reference

### 2.1 Analyzer Settings

Settings that control code analysis and warnings:

```lua
settings = {
  omnisharp = {
    -- Enable Roslyn Analyzer warnings/suggestions
    enableRoslynAnalyzers = true,

    -- Enable EditorConfig support (.editorconfig file)
    enableEditorConfigSupport = true,

    -- Show code metrics via CodeLens
    enableCodeLensOnFields = false,
    enableCodeLensOnProperties = false,
    enableCodeLensOnMethods = true,
  }
}
```

**Timing:** T5.5 (via workspace/didChangeConfiguration)
**Changeable:** Yes (without server restart)

### 2.2 Formatting Settings

Settings that control code formatting:

```lua
settings = {
  omnisharp = {
    -- Organize using directives when formatting
    organizeImportsOnFormat = true,

    -- Enable completion when typing (not just at completion start)
    enableImportCompletion = true,

    -- Format entire document or just current document
    -- (when :w is pressed)
  }
}
```

**Timing:** T5.5
**Changeable:** Yes
**Related:** When `:w` is pressed, Neovim calls the LSP formatter, which uses these settings

### 2.3 Completion Settings

Settings for code completion behavior:

```lua
settings = {
  omnisharp = {
    -- Enable completion suggestions
    enableImportCompletion = true,

    -- Show detailed completion information
    maxProjectFileCountForDiagnosticAnalysis = 1000,
  }
}
```

**Timing:** T5.5
**Changeable:** Yes

### 2.4 Logging Settings

For debugging and troubleshooting:

```lua
settings = {
  omnisharp = {
    -- Logging level: information, verbose, debug
    loggingLevel = "information",
  }
}
```

**Timing:** T5.5
**Changeable:** Yes (takes effect on next request)

### 2.5 Path and Location Settings

Settings for resolving project and solution paths:

```lua
settings = {
  omnisharp = {
    -- Solution file path (usually auto-detected)
    -- Leave blank to auto-detect from rootUri
    -- solutionPath = "/path/to/solution.sln",

    -- Project file path (usually auto-detected)
    -- projectPath = "/path/to/project.csproj",
  }
}
```

**Timing:** Usually set via InitializeParams.rootUri (T2), not settings
**Note:** OmniSharp automatically searches parent directories for .sln files

### 2.6 Reference Code Lens

Settings for showing code references:

```lua
settings = {
  omnisharp = {
    -- Show "X references" on methods and classes
    enableReferenceCodeLens = true,

    -- Show "X implementations" on interfaces/abstract methods
    enableCodeLensOnFields = false,
  }
}
```

**Timing:** T5.5
**Changeable:** Yes

---

## 3. Command-Line Arguments vs Settings

### 3.1 What OmniSharp Command-Line Arguments Control

OmniSharp accepts command-line arguments for process-level configuration:

```bash
# Launch OmniSharp with stdio transport (REQUIRED for Neovim LSP)
omnisharp --stdio

# Specify language version (if needed)
omnisharp --stdio --languageVersion=latest

# Specify host PID (tells OmniSharp to exit if parent exits)
omnisharp --stdio --hostPID 12345

# Specify solution file
omnisharp --stdio --solution /path/to/solution.sln

# Enable verbose logging
omnisharp --stdio --verbose
```

**Correct Neovim Configuration:**

```lua
omnisharp = {
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--stdio',                    -- Required for LSP communication
    -- Add other args here if needed:
    -- '--languageVersion=latest'
  },
  -- ... rest of config
}
```

### 3.2 What Settings Control (NOT command-line args)

These MUST be in `settings`, not in `cmd`:

```lua
-- WRONG - These are settings, not command-line args:
cmd = {
  'omnisharp',
  '--enableRoslynAnalyzers=true'   -- ❌ This won't work as cmd arg
}

-- CORRECT - Use settings instead:
settings = {
  omnisharp = {
    enableRoslynAnalyzers = true   -- ✓ Correct way
  }
}
```

---

## 4. Complete Working Example

### 4.1 Full OmniSharp Configuration

```lua
-- In your nvim/init.lua or plugin configuration

local lspconfig = require('lspconfig')

lspconfig.omnisharp.setup({
  -- ┌─────────────────────────────────────────────────────────────────────┐
  -- │ LAYER 1: PROCESS STARTUP (T0)                                       │
  -- └─────────────────────────────────────────────────────────────────────┘

  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--stdio',
    -- Uncomment if needed:
    -- '--languageVersion=latest',
    -- '--verbose',
  },

  -- ┌─────────────────────────────────────────────────────────────────────┐
  -- │ LAYER 2: INITIALIZATION (T2)                                        │
  -- │ This is typically empty for OmniSharp                               │
  -- └─────────────────────────────────────────────────────────────────────┘

  init_options = {
    -- OmniSharp doesn't require special init options
    -- Leave empty or add server-specific startup parameters if needed
  },

  -- ┌─────────────────────────────────────────────────────────────────────┐
  -- │ LAYER 3: RUNTIME CONFIGURATION (T5+)                               │
  -- │ These are sent via workspace/didChangeConfiguration                 │
  -- │ They can be updated without server restart                          │
  -- └─────────────────────────────────────────────────────────────────────┘

  settings = {
    omnisharp = {
      -- ┌───────────────────────────────────────────────────────────────┐
      -- │ ANALYZER SETTINGS                                             │
      -- └───────────────────────────────────────────────────────────────┘

      -- Enable Roslyn Analyzer warnings and suggestions
      -- Shows issues detected by Roslyn analyzers
      enableRoslynAnalyzers = true,

      -- Support .editorconfig files in the project
      -- Respects .editorconfig formatting/style rules
      enableEditorConfigSupport = true,

      -- Show CodeLens indicators for method count, references, etc.
      enableCodeLensOnMethods = true,
      enableCodeLensOnProperties = false,
      enableCodeLensOnFields = false,

      -- Show implementation count via CodeLens
      enableReferenceCodeLens = true,

      -- ┌───────────────────────────────────────────────────────────────┐
      -- │ FORMATTING SETTINGS                                           │
      -- └───────────────────────────────────────────────────────────────┘

      -- Automatically organize using statements when formatting
      -- When you press :w, OmniSharp will:
      --  1. Sort using directives
      --  2. Remove unused imports
      --  3. Format code
      organizeImportsOnFormat = true,

      -- Enable completion for imported types
      -- Allows completing types from other namespaces
      enableImportCompletion = true,

      -- ┌───────────────────────────────────────────────────────────────┐
      -- │ DIAGNOSTICS SETTINGS                                          │
      -- └───────────────────────────────────────────────────────────────┘

      -- Maximum project file count for full diagnostic analysis
      -- Larger values = more thorough analysis but slower
      maxProjectFileCountForDiagnosticAnalysis = 1000,

      -- ┌───────────────────────────────────────────────────────────────┐
      -- │ LOGGING SETTINGS (for debugging)                              │
      -- └───────────────────────────────────────────────────────────────┘

      -- Log level: "information", "verbose", "debug"
      -- Set to "debug" if you need to troubleshoot LSP issues
      loggingLevel = "information",

      -- ┌───────────────────────────────────────────────────────────────┐
      -- │ OPTIONAL: SOLUTION/PROJECT PATHS                              │
      -- │ Usually NOT needed - OmniSharp auto-detects                   │
      -- └───────────────────────────────────────────────────────────────┘

      -- If auto-detection fails, explicitly specify solution path:
      -- solutionPath = "/path/to/your/solution.sln",

      -- If working with specific project:
      -- projectPath = "/path/to/your/project.csproj",
    }
  },

  -- ┌─────────────────────────────────────────────────────────────────────┐
  -- │ OPTIONAL: LSP HANDLERS (Neovim-specific)                            │
  -- │ Not part of LSP spec, but useful for Neovim integration             │
  -- └─────────────────────────────────────────────────────────────────────┘

  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      if result.type <= vim.lsp.protocol.MessageType.Warning then
        vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.WARN)
      else
        vim.notify('[OmniSharp] ' .. result.message, vim.log.levels.INFO)
      end
    end,
  },

  -- ┌─────────────────────────────────────────────────────────────────────┐
  -- │ OPTIONAL: Neovim LSP client options (not from LSP spec)             │
  -- └─────────────────────────────────────────────────────────────────────┘

  on_attach = function(client, bufnr)
    -- Set up keybindings, autocommands, etc.
    -- This runs when LSP attaches to a buffer
  end,

  -- Root detection pattern (Neovim-specific)
  -- Looks for these files to detect project root
  root_dir = function()
    return vim.fs.dirname(vim.fs.find({'.sln', '.git'}, {
      upward = true
    })[1])
  end,
})
```

### 4.2 Minimal Configuration

If you just want the essentials:

```lua
lspconfig.omnisharp.setup({
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--stdio'
  },
  settings = {
    omnisharp = {
      enableRoslynAnalyzers = true,
      organizeImportsOnFormat = true,
      enableImportCompletion = true,
    }
  }
})
```

---

## 5. Debugging Configuration Issues

### 5.1 Verify Settings are Being Applied

```vim
" Check if OmniSharp is attached to current buffer
:LspInfo

" Look for OmniSharp in the list
" Should show:
" - Server capabilities
" - Server status (Initialized)
" - Server PID
```

### 5.2 Check What Settings OmniSharp Received

Enable debug logging:

```lua
settings = {
  omnisharp = {
    loggingLevel = "debug"  -- Changed from "information"
  }
}
```

Then check logs:

```vim
" Neovim LSP logs
:e $NVIM_LOG_FILE
" or
:!tail -f ~/.local/state/nvim/lsp.log

" Look for workspace/didChangeConfiguration entries
" to see what settings were sent
```

### 5.3 Test Specific Features

```vim
" Test diagnostics/analyzers
" Should show red/yellow underlines
:e src/Program.cs

" Test code completion
gd              " Go to definition - tests navigation

K               " Hover - shows type information

<leader>ca      " Code actions - shows diagnostics and fixes

]d              " Next diagnostic - tests analyzer output
```

### 5.4 Common Issues

**Issue:** OmniSharp not attaching
```vim
" Solution: Run pkill -f omnisharp, then restart Neovim
:LspInfo       " Verify it's attached
```

**Issue:** Settings not taking effect
```lua
-- Check if you're using init_options for dynamic settings:
-- WRONG:
init_options = {
  enableRoslynAnalyzers = true  -- Won't work here
}

-- CORRECT:
settings = {
  omnisharp = {
    enableRoslynAnalyzers = true  -- Correct location
  }
}
```

**Issue:** Formatting not working
```vim
" Ensure settings are present:
:LspInfo  " Check if formatting capability is enabled

" Manually format:
<leader>f  " Or whatever your format key is

" Check if OmniSharp responds:
" Look for errors in :LspInfo output
```

---

## 6. How Settings Flow in Practice

### 6.1 User Edits init.lua

```lua
omnisharp = {
  settings = {
    omnisharp = {
      enableRoslynAnalyzers = true  -- User enables analyzers
    }
  }
}
```

### 6.2 Neovim Loads Config

```vim
:source ~/.config/nvim/init.lua    " User reloads config
```

### 6.3 LSP Client Sends workspace/didChangeConfiguration

```
Neovim                          OmniSharp
  │                                 │
  ├──→ workspace/didChangeConfiguration
  │    {                            │
  │      "settings": {              │
  │        "omnisharp": {           │
  │          "enableRoslynAnalyzers": true
  │        }                        │
  │      }                          │
  │    }                            │
  │                                 │
  │                            ┌────┴─────────────┐
  │                            │ T5.5: Receive    │
  │                            │ and apply        │
  │                            │ settings         │
  │                            │                  │
  │                            │ Analyzers now    │
  │                            │ enabled          │
  │                            └──────────────────┘
  │                                 │
  │  ←── (no response needed) ──────┤
  │      (notification, not request)
```

### 6.4 New Analysis Results Appear

```vim
:e src/Program.cs              " Reopen file (or it updates automatically)
" Now sees analyzer warnings (red/yellow underlines)
```

---

## 7. LSP Specification Compliance Checklist

- [x] Using `cmd` for process-level control (command-line args)
- [x] Using `init_options` for server startup parameters (if needed)
- [x] Using `settings` for workspace/didChangeConfiguration values
- [x] Settings sent after `initialized` notification (T5+)
- [x] Supports dynamic configuration updates without restart
- [x] Following server-specific setting names (omnisharp.*)
- [x] Not mixing settings into cmd args
- [x] Not mixing settings into init_options (unless truly startup-only)

---

## 8. References

1. **LSP Specification 3.17**
   - Initialize Request: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
   - workspace/didChangeConfiguration: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/

2. **OmniSharp Documentation**
   - GitHub: https://github.com/OmniSharp/omnisharp-roslyn
   - Configuration: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration

3. **Neovim LSP Documentation**
   - https://neovim.io/doc/user/lsp.html
   - https://github.com/neovim/nvim-lspconfig

4. **Related Documents in This Repository**
   - LSP_SPECIFICATION_RESEARCH.md - Official LSP spec details
   - LSP_SETTINGS_TIMING_DIAGRAM.md - Visual timing diagrams

---

## 9. Quick Reference

```lua
-- WHAT YOU NEED:

omnisharp = {
  cmd = { 'omnisharp', '--stdio' },        -- How to start the process
  init_options = {},                        -- Usually empty for OmniSharp
  settings = {                              -- Dynamic configuration
    omnisharp = {
      enableRoslynAnalyzers = true,
      organizeImportsOnFormat = true,
      enableImportCompletion = true,
    }
  }
}

-- WHEN THEY APPLY:

-- cmd          → T0 (spawn process)
-- init_options → T2 (during initialize)
-- settings     → T5+ (after initialized notification)

-- WHEN THEY CHANGE:

-- cmd          → Never (can't change after spawn)
-- init_options → Never (only sent once)
-- settings     → Anytime (dynamic via workspace/didChangeConfiguration)
```

