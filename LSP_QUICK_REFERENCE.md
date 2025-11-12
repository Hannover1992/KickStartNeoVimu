# LSP Settings Quick Reference Card

Fast lookup for LSP configuration mechanisms based on official specification.

---

## One-Minute Overview

```
Three ways to configure LSP servers:

1. cmd                → PROCESS CONTROL (how it starts)
2. init_options       → STARTUP CONFIG (one-time only)
3. settings          → RUNTIME CONFIG (can change)
```

---

## Configuration Comparison

```
WHEN TO USE WHAT:

Need to pass flags to the command?           → Use: cmd
Need startup-only parameters?                → Use: init_options
Need dynamic configuration?                  → Use: settings
Not sure which?                              → Use: settings
```

---

## OmniSharp Configuration Template

```lua
omnisharp = {
  -- T0: How to start the process
  cmd = {
    vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp'),
    '--stdio'
  },

  -- T2: Startup parameters (usually empty for OmniSharp)
  init_options = {},

  -- T5+: Dynamic configuration (what you actually want)
  settings = {
    omnisharp = {
      enableRoslynAnalyzers = true,
      organizeImportsOnFormat = true,
      enableImportCompletion = true,
      enableEditorConfigSupport = true,
      enableReferenceCodeLens = true,
    }
  }
}
```

---

## Timing Reference

```
T0: Process spawns           → cmd takes effect
T1: Server running
T2: Initialize request       → init_options sent
T2.5: Server processes init  → init_options applied
T3: Initialize response
T4: Initialized notification → Server ready
T5: didChangeConfiguration   → settings sent
T5.5: Server processes       → settings applied
T6+: Normal operation        → Everything active
```

---

## Official LSP Field Names

| Concept | Neovim | LSP Spec | Timing |
|---------|--------|----------|--------|
| Process args | `cmd` | (not LSP) | T0 |
| Startup config | `init_options` | `initializationOptions` | T2 |
| Dynamic config | `settings` | (via workspace/didChangeConfiguration) | T5+ |

---

## WRONG vs RIGHT Examples

### WRONG
```lua
-- Putting settings in cmd
cmd = { 'omnisharp', '--enableRoslynAnalyzers=true' }

-- Putting dynamic settings in init_options
init_options = { enableRoslynAnalyzers = true }
```

### RIGHT
```lua
-- Correct: settings for dynamic configuration
settings = {
  omnisharp = {
    enableRoslynAnalyzers = true
  }
}
```

---

## Can It Change After Startup?

| Field | Can Change | How |
|-------|------------|-----|
| `cmd` | No | Must restart server |
| `init_options` | No | One-time only |
| `settings` | Yes | Neovim sends workspace/didChangeConfiguration |

---

## Testing Your Configuration

```vim
" Check if OmniSharp is attached
:LspInfo

" Check if settings are being sent
:!tail -f ~/.local/state/nvim/lsp.log | grep -i "didChangeConfiguration"

" Test a feature that uses settings
gd     " Go to definition
K      " Hover documentation
<leader>ca  " Code actions
```

---

## Debugging

**Settings not working?**
1. Make sure they're in `settings` (not `init_options`)
2. Restart LSP: `:LspRestart`
3. Check logs: `:!tail -f ~/.local/state/nvim/lsp.log`
4. Check server docs for exact setting names

**Command-line args not working?**
1. Check if they're valid OmniSharp args
2. Run manually to test: `omnisharp --help`
3. Check OmniSharp documentation

---

## References

- **LSP Spec:** https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- **Neovim LSP:** https://neovim.io/doc/user/lsp.html
- **Full Research:** See other documents in this directory

---

## Key Points (Remember These!)

1. **Three separate layers** - Don't mix them up
2. **Settings are sent AFTER initialization** - Not during
3. **Settings can change dynamically** - init_options cannot
4. **Use `settings` by default** - It's the most flexible
5. **Check server documentation** - Each server has different option names

---

## Common OmniSharp Settings

```lua
settings = {
  omnisharp = {
    enableRoslynAnalyzers = true,      -- Show analyzer warnings
    enableEditorConfigSupport = true,  -- Respect .editorconfig
    organizeImportsOnFormat = true,    -- Sort using statements
    enableImportCompletion = true,     -- Complete imported types
    enableReferenceCodeLens = true,    -- Show reference count
    enableCodeLensOnMethods = true,    -- Show code metrics
    loggingLevel = "information",      -- Debug: "debug"
  }
}
```

---

## Checklist: Is My Config Correct?

- [ ] `cmd` has `'--stdio'` for Neovim LSP
- [ ] `init_options` is empty or has startup-only params
- [ ] `settings` contains all dynamic configuration
- [ ] Settings are under `omnisharp` key
- [ ] No settings duplicated across `cmd`, `init_options`, and `settings`
- [ ] Tested with `:LspInfo` to verify attachment
- [ ] Checked logs for `workspace/didChangeConfiguration` messages

---

## For the Impatient

Just use this:

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

It works because it follows LSP specification.

