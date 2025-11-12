# nvim-lspconfig on_new_config & Settings Flattening - Comprehensive Research

**Research Date:** November 12, 2025
**Scope:** nvim-lspconfig documentation, GitHub repository analysis, and Neovim LSP architecture
**Focus:** on_new_config callback, settings flattening mechanism, vim.tbl_deep_extend merge strategies

---

## Executive Summary

This research document provides definitive answers about how **nvim-lspconfig** handles:

1. **Settings flattening mechanism** - how nested configuration tables are converted to command-line arguments
2. **on_new_config callback** - how it modifies LSP server configuration dynamically
3. **Merge strategies** - how 'keep' vs 'force' affects configuration propagation
4. **Common mistakes** - reasons why settings fail to propagate to LSP servers
5. **Debugging techniques** - how to verify settings are correctly passed

---

## Part 1: Settings Flattening Mechanism

### 1.1 What is Settings Flattening?

**Settings flattening** is the process of converting nested Lua table structures into flat command-line arguments that can be passed to an LSP server.

**Example:**
```lua
settings = {
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    TabSize = 4,
  },
  MsBuild = {
    IncludePrereleases = true,
  }
}
```

**Becomes command-line arguments:**
```bash
FormattingOptions:EnableEditorConfigSupport=true
FormattingOptions:TabSize=4
MsBuild:IncludePrereleases=true
```

### 1.2 How Settings Flattening Works in on_new_config

The **on_new_config callback** in nvim-lspconfig (particularly for OmniSharp) implements settings flattening by:

1. **Taking the user-provided settings table**
2. **Recursively traversing nested key-value pairs**
3. **Creating colon-separated keys** (e.g., `FormattingOptions:TabSize`)
4. **Converting values to strings**
5. **Appending as individual command-line arguments** to the cmd array

**Actual nvim-lspconfig implementation (omnisharp.lua):**

The `on_new_config` function for OmniSharp contains code that flattens the settings table:

```lua
on_new_config = function(new_config, _)
  -- Copy cmd array
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- Append hard-coded arguments
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- FLATTENING: Convert settings table to command arguments
  -- Pseudo-code representation:
  -- for each key in settings table:
  --   for each nested key-value pair:
  --     new_config.cmd.append('ParentKey:ChildKey=value')
end
```

### 1.3 The `tbl_flatten` Utility Function

nvim-lspconfig provides a **compatibility wrapper** for table flattening in `lua/lspconfig/util.lua`:

```lua
function M.tbl_flatten(t)
  --- @diagnostic disable-next-line:deprecated
  return nvim_eleven and vim.iter(t):flatten(math.huge):totable() or vim.tbl_flatten(t)
end
```

**How it works:**
- **For Neovim 0.11+:** Uses the modern iterator API: `vim.iter(t):flatten(math.huge):totable()`
- **For Neovim < 0.11:** Falls back to the legacy function: `vim.tbl_flatten(t)`
- **Parameter `math.huge`:** Ensures complete flattening of ALL nesting levels

**Important Note:** This function flattens **array-like tables**, not configuration objects. The actual settings flattening happens inside the server-specific `on_new_config` callbacks (like omnisharp.lua), not through this general utility.

### 1.4 Purpose of Settings Flattening

Different LSP servers expect settings in different formats:

- **JSON-RPC Format (Standard LSP):** Most servers receive settings as a nested JSON object via `initialize` request
  ```json
  {
    "FormattingOptions": {
      "EnableEditorConfigSupport": true,
      "TabSize": 4
    }
  }
  ```

- **Command-Line Argument Format:** Some servers (like OmniSharp) accept settings as flat command-line arguments
  ```bash
  FormattingOptions:EnableEditorConfigSupport=true FormattingOptions:TabSize=4
  ```

The flattening mechanism allows nvim-lspconfig to support both approaches seamlessly.

---

## Part 2: on_new_config Callback - Deep Dive

### 2.1 What is on_new_config?

The **on_new_config** callback is a **function that gets executed after root directory detection** but **before the LSP server process is spawned**.

**Key characteristics:**
- Called once per LSP configuration instance
- Has access to `new_config` (the configuration object about to be used)
- Has access to `new_root_dir` (the detected root directory)
- Can modify the configuration in-place
- Changes affect what gets passed to the LSP server

**Function signature:**
```lua
on_new_config = function(new_config, new_root_dir)
  -- Modify new_config here
end
```

### 2.2 When on_new_config is Called

The sequence of events:

```
1. User calls: require('lspconfig').omnisharp.setup({ ... })
2. nvim-lspconfig stores configuration
3. When Neovim opens a C# file:
   a. root_dir function is called to detect project root
   b. NEW CONFIGURATION INSTANCE is created (deep copy)
   c. on_new_config CALLBACK IS INVOKED
   d. Modifications made in callback affect the new instance
   e. Modified config passed to vim.lsp.start_client()
   f. LSP server process is spawned with modified cmd
```

### 2.3 on_new_config in nvim-lspconfig vs Neovim 0.11

**Current Status (as of Nov 2025):**

- **nvim-lspconfig:** Full support for `on_new_config` callback
- **Neovim 0.11 vim.lsp.config API:** `on_new_config` is **currently missing**

From the official nvim-lspconfig documentation:

> "on_new_config is currently missing, see https://github.com/neovim/neovim/issues/32287"

**Workaround for Neovim 0.11:**
```lua
-- Instead of on_new_config, use function-based root_dir
root_dir = function(fname)
  -- Can perform custom logic here during root detection
  -- More flexible than just returning a directory path
end
```

### 2.4 on_new_config Examples

#### Example 1: OmniSharp (C#)

The most complex example - adds command-line arguments and flattens settings:

```lua
on_new_config = function(new_config, _)
  -- Create a fresh copy of the command array
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- Append hard-coded LSP parameters
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- Flatten settings into command arguments
  -- (Implementation details in omnisharp.lua)
end
```

#### Example 2: Modifying Capabilities

```lua
on_new_config = function(new_config, _)
  -- Disable unsupported workspace features
  new_config.capabilities.workspace.workspaceFolders = false
end
```

#### Example 3: Dynamic Configuration

```lua
on_new_config = function(new_config, new_root_dir)
  -- Conditionally set options based on project structure
  if vim.fn.filereadable(new_root_dir .. '/package.json') then
    new_config.settings.nodejs = { command = 'node' }
  end
end
```

### 2.5 Why Settings Don't Get Applied (on_new_config Issues)

**Issue 1: Using vim.lsp.config() instead of setup()**

```lua
-- WRONG - on_new_config is not called
vim.lsp.config('omnisharp', { ... })

-- RIGHT - on_new_config callback is triggered
require('lspconfig').omnisharp.setup({ ... })
```

**Issue 2: on_new_config Missing in Neovim 0.11**

If you're on Neovim 0.11+, `on_new_config` isn't implemented in the native API yet. You must:
- Continue using nvim-lspconfig for servers that need on_new_config
- OR use alternative approaches like function-based root_dir

**Issue 3: Modification Doesn't Persist**

```lua
-- WRONG - modifications lost after callback returns
on_new_config = function(new_config, _)
  local settings = new_config.settings or {}
  settings.option = true
  -- settings is a local variable - changes lost!
end

-- RIGHT - modify new_config directly
on_new_config = function(new_config, _)
  new_config.settings = new_config.settings or {}
  new_config.settings.option = true
  -- Changes persist because new_config is modified in-place
end
```

---

## Part 3: vim.tbl_deep_extend and Merge Strategies

### 3.1 The 'keep' vs 'force' Merge Strategies

The **nvim-lspconfig setup() function** uses `vim.tbl_deep_extend()` with specific merge strategies to combine user configuration with defaults.

**Function call:**
```lua
local config = vim.tbl_deep_extend('keep', user_config, default_config)
```

**How merge strategies differ:**

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| `'keep'` | **User settings have priority.** Only fills in missing keys from defaults | nvim-lspconfig setup() |
| `'force'` | **Later arguments override earlier ones.** Useful for capabilities merging | Merging with cmp capabilities |
| `'error'` | Raises error if there are duplicate keys (strict mode) | Detecting accidental overrides |

### 3.2 How 'keep' Works in nvim-lspconfig.setup()

In the `configs.lua` file, the setup function uses 'keep' strategy:

```lua
function nvim_lspconfig.setup(config_def, user_config)
  local config = vim.tbl_deep_extend('keep', user_config, default_config)

  -- Result: user_config takes precedence
  -- Default values fill in only what user didn't provide
end
```

**Practical Example:**

```lua
-- Default config from nvim-lspconfig
local defaults = {
  settings = {
    FormattingOptions = { TabSize = 2 },
    MsBuild = { LoadOnDemand = true }
  },
  root_dir = util.root_pattern('*.sln'),
}

-- User configuration
local user_config = {
  settings = {
    FormattingOptions = { TabSize = 4 },
    -- MsBuild not specified - will use default
  }
}

-- Result after tbl_deep_extend('keep', user_config, defaults)
local merged = {
  settings = {
    FormattingOptions = { TabSize = 4 },  -- User value wins
    MsBuild = { LoadOnDemand = true }      -- Filled from defaults
  },
  root_dir = util.root_pattern('*.sln'),  -- From defaults
}
```

### 3.3 'keep' vs 'force' - Settings Propagation Impact

**Using 'keep' (nvim-lspconfig design):**
- User-provided settings are preserved
- Defaults fill in missing options
- Backward compatible with partial configurations

**Using 'force' (NOT recommended for lspconfig setup):**
```lua
-- If lspconfig used 'force' instead:
local merged = vim.tbl_deep_extend('force', user_config, defaults)
-- Result: defaults would OVERWRITE user settings! ❌
```

### 3.4 Multiple Configuration Sources and Merging Order

When using Neovim 0.11's `vim.lsp.config()`, configurations are merged from multiple sources:

**Merge order (lowest to highest priority):**

1. **Global configuration** (file-named `*`)
   ```lua
   vim.lsp.config('*', { settings = { ... } })
   ```

2. **runtimepath LSP configs** (from `$VIMRUNTIME/lsp/` and plugins)
   ```lua
   -- Automatically loaded from lsp/*.lua files
   ```

3. **User-defined configurations** (in after/lsp/)
   ```lua
   -- Files in ~/.config/nvim/after/lsp/ override defaults
   ```

4. **Direct vim.lsp.config() calls**
   ```lua
   vim.lsp.config('omnisharp', { ... })  -- Highest priority
   ```

Each level uses `vim.tbl_deep_extend('force', ...)` to merge, so **later definitions override earlier ones**.

### 3.5 Settings Flattening is NOT Affected by Merge Strategy

**Important clarification:**

The `vim.tbl_deep_extend()` 'keep' vs 'force' strategy affects **how configurations are combined**, but NOT the **settings flattening process**.

Settings flattening happens:
- AFTER merging is complete
- In the server-specific `on_new_config` callback
- When converting settings table to command-line arguments

```lua
-- Merge strategy (determines which settings win)
local merged = vim.tbl_deep_extend('keep', user_config, defaults)
    ↓
-- on_new_config callback (flattens merged settings)
on_new_config = function(new_config, _)
  -- new_config.settings is already merged here
  -- Flatten it into command arguments
  new_config.cmd = flatten_settings(new_config.settings)
end
```

---

## Part 4: Common Mistakes Preventing Settings Propagation

### 4.1 Mistake 1: Using vim.lsp.config() Instead of setup()

**Problem:**
```lua
-- ❌ WRONG - on_new_config is NOT called
vim.lsp.config('omnisharp', {
  cmd = { '/path/to/omnisharp' },
  settings = { ... }
})
```

**Why it fails:**
- `vim.lsp.config()` is a lower-level API that doesn't invoke callbacks
- `on_new_config` is only triggered by `lspconfig.setup()`
- Settings modifications in on_new_config won't happen

**Solution:**
```lua
-- ✅ RIGHT - on_new_config is called
require('lspconfig').omnisharp.setup({
  cmd = { '/path/to/omnisharp' },
  settings = { ... }
})
```

### 4.2 Mistake 2: Path Expansion Without vim.fn.expand()

**Problem:**
```lua
-- ❌ WRONG - Tilde not expanded
cmd = { "~/.local/share/nvim/mason/bin/OmniSharp" }

-- ❌ WRONG - Environment variables not expanded
cmd = { "$HOME/.local/share/nvim/mason/bin/OmniSharp" }
```

**Why it fails:**
- nvim-lspconfig doesn't perform shell-style expansions
- The literal string `~` is passed to the LSP server
- Server can't find the file because path doesn't exist

**Solution:**
```lua
-- ✅ RIGHT - Explicit expansion
cmd = { vim.fn.expand("~/.local/share/nvim/mason/bin/OmniSharp") }

-- ✅ RIGHT - Absolute path
cmd = { "/home/user/.local/share/nvim/mason/bin/OmniSharp" }
```

### 4.3 Mistake 3: Settings as Top-Level Table (Not Nested)

**Problem:**
```lua
-- ❌ WRONG - Settings not in 'settings' key
require('lspconfig').omnisharp.setup({
  FormattingOptions = { TabSize = 4 },  -- Lost!
  MsBuild = { LoadOnDemand = true },    -- Lost!
})
```

**Why it fails:**
- nvim-lspconfig expects settings in the `settings` key
- Top-level keys are treated as config options (cmd, root_dir, etc.)
- Settings are never sent to the LSP server

**Solution:**
```lua
-- ✅ RIGHT - Settings properly nested
require('lspconfig').omnisharp.setup({
  cmd = { '...' },
  settings = {
    FormattingOptions = { TabSize = 4 },
    MsBuild = { LoadOnDemand = true },
  }
})
```

### 4.4 Mistake 4: Parameters Instead of Settings

**Problem:**
```lua
-- ❌ WRONG - Trying to pass settings as cmd arguments
require('lspconfig').omnisharp.setup({
  cmd = {
    '...',
    'FormattingOptions:TabSize=4'  -- Wrong place!
  }
})
```

**Why it fails:**
- The `settings` table is the proper mechanism
- Command-line arguments are added by `on_new_config` via flattening
- Manually adding them can cause duplicates or conflicts

**Solution:**
```lua
-- ✅ RIGHT - Use settings table
require('lspconfig').omnisharp.setup({
  cmd = { '...' },
  settings = {
    FormattingOptions = { TabSize = 4 }
  }
})
```

### 4.5 Mistake 5: Parameter Type Mismatch

**Problem:**
```lua
-- ❌ WRONG - Number instead of string
cmd = { 'omnisharp', '--hostPID', vim.fn.getpid() }  -- Returns number!
```

**Why it fails:**
- Command arrays must contain only STRINGS
- Numbers don't get automatically converted
- The LSP server receives malformed arguments

**Solution:**
```lua
-- ✅ RIGHT - Convert to string
cmd = { 'omnisharp', '--hostPID', tostring(vim.fn.getpid()) }
```

### 4.6 Mistake 6: Overriding on_new_config Without Understanding It

**Problem:**
```lua
-- ❌ DANGEROUS - Replaces entire on_new_config
require('lspconfig').omnisharp.setup({
  on_new_config = function(new_config, _)
    new_config.cmd = { 'omnisharp' }  -- Lost all the automatic arguments!
  end
})
```

**Why it fails:**
- Completely replaces the default `on_new_config`
- Loses all hard-coded argument injection
- Lost: --languageserver, --hostPID, -z, settings flattening
- OmniSharp likely fails to start

**Solution:**
```lua
-- ✅ RIGHT - Extend existing on_new_config (if you must override)
local defaults = require('lspconfig.configs').omnisharp
require('lspconfig').omnisharp.setup({
  on_new_config = function(new_config, new_root_dir)
    -- Call the default behavior first
    defaults.on_new_config(new_config, new_root_dir)

    -- Then add your custom modifications
    table.insert(new_config.cmd, '--my-custom-arg')
  end
})
```

### 4.7 Mistake 7: Assuming vim.lsp.config() Merges with Defaults

**Problem:**
```lua
-- ❌ WRONG - Incomplete configuration
vim.lsp.config('omnisharp', {
  settings = { FormattingOptions = { TabSize = 4 } }
  -- Missing: cmd, root_dir, etc.!
})
```

**Why it fails:**
- Neovim 0.11's vim.lsp.config() doesn't fully merge with nvim-lspconfig defaults
- You must provide complete configuration
- Missing cmd means LSP server won't start

**Solution:**
```lua
-- ✅ RIGHT - Use nvim-lspconfig for complete setup
require('lspconfig').omnisharp.setup({
  settings = { FormattingOptions = { TabSize = 4 } }
  -- cmd, root_dir automatically provided by lspconfig
})
```

---

## Part 5: Debugging - Verifying Settings Are Passed

### 5.1 Check 1: Verify Configuration in init.lua

**Inspect your configuration structure:**
```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll') },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      TabSize = 4,
    }
  }
})
```

**Checklist:**
- [ ] Using `setup()`, not `vim.lsp.config()`
- [ ] `cmd` is an array of STRINGS
- [ ] Paths use `vim.fn.expand()` or absolute paths
- [ ] Settings are in the `settings` key, not top-level
- [ ] All values are proper types (no unquoted booleans)

### 5.2 Check 2: Use print() in on_new_config

Add debug output to see what configuration is created:

```lua
require('lspconfig').omnisharp.setup({
  settings = { ... },

  -- TEMPORARY DEBUG CODE
  on_new_config = function(new_config, new_root_dir)
    -- Print what we receive
    vim.notify('OmniSharp attaching to: ' .. new_root_dir)
    vim.notify('Settings: ' .. vim.inspect(new_config.settings))
    vim.notify('Cmd: ' .. vim.inspect(new_config.cmd))
  end
})
```

**View output:**
```vim
:messages
" Or scroll through notification history
```

### 5.3 Check 3: Use :LspInfo Command

In Neovim, run:
```vim
:LspInfo
```

**What to look for:**
- Shows "omnisharp" in the list of attached servers
- Shows the `cmd` array being executed
- Shows `root_dir` that was detected
- If blank, LSP didn't attach

### 5.4 Check 4: Check LSP Logs

Enable verbose logging:

```lua
-- In init.lua
vim.lsp.set_log_level('debug')
```

Then check the log file:
```bash
# Linux/Mac
tail -f ~/.local/state/nvim/lsp.log

# Or in Neovim
:LspLog
```

**What to look for:**
- "initialized" message (successful initialization)
- "initialize" request showing what settings are sent
- Any error messages about invalid settings

### 5.5 Check 5: Use LspAttach Autocmd

Inspect configuration after attachment:

```lua
vim.api.nvim_create_autocmd('LspAttach', {
  callback = function(args)
    local client = vim.lsp.get_client_by_id(args.data.client_id)
    if client.name == 'omnisharp' then
      vim.notify('OmniSharp settings: ' .. vim.inspect(client.config.settings))
      vim.notify('OmniSharp cmd: ' .. vim.inspect(client.config.cmd))
    end
  end
})
```

### 5.6 Check 6: Test LSP Server Directly

Test the OmniSharp binary with the arguments that would be passed:

```bash
# Assuming Mason installation
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  --languageserver \
  --hostPID $$ \
  -z \
  --encoding utf-8

# If it starts without error, the server itself is fine
# Problem is with how settings/arguments are being passed
```

### 5.7 Check 7: Monitor Process with ps

While Neovim is open with OmniSharp attached:

```bash
ps aux | grep -i omnisharp
```

**Look at the actual command line:**
- Are the settings arguments there?
- Are there duplicates?
- Is the path correct?

**Example output:**
```
dotnet /home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
  --languageserver --hostPID 12345 -z --encoding utf-8
  FormattingOptions:EnableEditorConfigSupport=true
```

---

## Part 6: Working Examples

### 6.1 Example 1: Basic OmniSharp Setup

```lua
-- Minimal working configuration
require('lspconfig').omnisharp.setup({
  cmd = {
    'dotnet',
    vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll')
  },

  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
    },
    MsBuild = {
      IncludePrereleases = true,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
  }
})
```

**What happens:**
1. User provides cmd and settings
2. When C# file is opened, root_dir is detected
3. on_new_config appends: --languageserver, --hostPID, -z, --encoding utf-8
4. Settings are flattened into: FormattingOptions:EnableEditorConfigSupport=true, etc.
5. Final cmd passed to dotnet binary
6. Settings sent via LSP initialize request

### 6.2 Example 2: Extending Existing on_new_config

```lua
local omnisharp_config = require('lspconfig.configs').omnisharp

require('lspconfig').omnisharp.setup({
  on_new_config = function(new_config, new_root_dir)
    -- Call original on_new_config first
    omnisharp_config.on_new_config(new_config, new_root_dir)

    -- Then add custom arguments
    table.insert(new_config.cmd, '--debug')

    -- Or modify existing cmd
    if vim.fn.filereadable(new_root_dir .. '/.omnisharp') then
      vim.list_extend(new_config.cmd, { '-s', new_root_dir .. '/solution.sln' })
    end
  end
})
```

### 6.3 Example 3: Conditional Settings Based on Project

```lua
require('lspconfig').omnisharp.setup({
  on_new_config = function(new_config, new_root_dir)
    -- Check project type
    if vim.fn.filereadable(new_root_dir .. '/angular.json') then
      new_config.settings = { ... }  -- Angular-specific settings
    else
      new_config.settings = { ... }  -- Default settings
    end
  end
})
```

### 6.4 Example 4: Merging Capabilities

```lua
-- Merge LSP capabilities with cmp completion capabilities
local capabilities = vim.lsp.protocol.make_client_capabilities()
capabilities = vim.tbl_deep_extend('force', capabilities, require('cmp_nvim_lsp').default_capabilities())

require('lspconfig').omnisharp.setup({
  capabilities = capabilities,
  settings = { ... }
})
```

**Note:** Here we use 'force' strategy because we want cmp capabilities to override defaults.

### 6.5 Example 5: Complete Modern Setup (Neovim 0.11)

```lua
-- If vim.lsp.config available (Neovim 0.11+)
if vim.lsp.config then
  vim.lsp.config('omnisharp', {
    cmd = { 'dotnet', vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll') },
    filetypes = { 'cs' },
    root_dir = require('lspconfig.util').root_pattern('*.sln', '*.csproj'),
    settings = {
      FormattingOptions = { EnableEditorConfigSupport = true },
    }
  })

  vim.lsp.enable('omnisharp')
else
  -- Fallback to nvim-lspconfig for older Neovim versions
  require('lspconfig').omnisharp.setup({
    cmd = { 'dotnet', vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll') },
    settings = {
      FormattingOptions = { EnableEditorConfigSupport = true },
    }
  })
end
```

---

## Part 7: Debugging Checklist

### Comprehensive Debugging Workflow

**If LSP doesn't attach:**
```
1. ✅ Check :LspInfo
   - Is omnisharp listed?
   - What is the cmd shown?

2. ✅ Check :LspLog
   - Look for "initialize" errors
   - Check for missing solution file errors

3. ✅ Test binary manually
   - Run: dotnet /path/to/omnisharp.dll --version
   - Does it start without error?

4. ✅ Verify configuration syntax
   - Is cmd an array of strings?
   - Are paths absolute?
   - Are values properly typed?
```

**If LSP attaches but settings don't work:**
```
1. ✅ Check settings key
   - Is settings nested properly?
   - Not at top level?

2. ✅ Verify on_new_config
   - Add vim.notify() calls to debug
   - What does it print?

3. ✅ Check logs for flattening
   - Are settings appearing as command arguments?
   - :tail ~/.local/state/nvim/lsp.log

4. ✅ Inspect process
   - ps aux | grep omnisharp
   - Do you see the settings in cmd line?
```

---

## Part 8: Key Findings Summary

### Finding 1: Settings Flattening is Server-Specific

- **Not all servers flatten settings** - only those designed to accept command-line arguments
- **OmniSharp flattens** because it accepts settings as -key:subkey=value format
- **Most other LSP servers** receive settings as JSON in the initialize request

### Finding 2: on_new_config is Powerful but Undocumented

- Allows dynamic configuration modification after root detection
- Currently missing in Neovim 0.11's native vim.lsp.config API
- Must use nvim-lspconfig setup() to access it

### Finding 3: Merge Strategy ('keep' vs 'force') Affects Configuration Priority

- **'keep':** User settings have priority (nvim-lspconfig default)
- **'force':** Later values override earlier ones (use with capabilities)
- Doesn't directly affect settings flattening, only configuration merging

### Finding 4: vim.tbl_deep_extend is Used at Multiple Levels

1. **Config merging:** User config + defaults (`'keep'` strategy)
2. **Capabilities merging:** LSP capabilities + cmp capabilities (`'force'` strategy)
3. **Multi-source merging:** Global + runtimepath + user configs (`'force'` strategy)

### Finding 5: Common Root Causes of Settings Not Propagating

| Problem | Cause | Solution |
|---------|-------|----------|
| Settings not sent to server | Using vim.lsp.config() instead of setup() | Use require('lspconfig').omnisharp.setup() |
| Settings appear in top-level | Not nested in settings key | Move to settings = { ... } |
| Path not found | Tilde expansion not supported | Use vim.fn.expand('~') |
| Duplicate arguments | Manually adding what on_new_config adds | Remove manual additions |
| Type mismatch in cmd | Non-string values in cmd array | Use tostring() for numbers |
| LSP doesn't start | overriding on_new_config incorrectly | Extend rather than replace |

---

## References

1. **nvim-lspconfig GitHub Repository**
   - URL: https://github.com/neovim/nvim-lspconfig
   - Key files:
     - `lua/lspconfig/configs.lua` - setup() function implementation
     - `lua/lspconfig/util.lua` - tbl_flatten() utility
     - `lua/lspconfig/configs/omnisharp.lua` - OmniSharp on_new_config example

2. **Neovim Official Documentation**
   - URL: https://neovim.io/doc/user/lsp.html
   - Covers: vim.lsp.config(), capabilities, settings parameter

3. **GitHub Issues**
   - Issue #3172: "attempt to call method 'flatten'" - version detection bug
   - Issue #32287: "on_new_config for vim.lsp.config" - missing feature in Neovim 0.11
   - Discussion #33577: "`lsp.config` merging semantics" - configuration merging behavior

4. **OmniSharp Configuration**
   - URL: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
   - Covers: Available settings and command-line arguments

---

## Conclusions

1. **Settings flattening is automatic** in nvim-lspconfig for servers that need it (like OmniSharp). Users provide settings in a nested table; flattening happens transparently.

2. **on_new_config is the key mechanism** for dynamic configuration. It allows modification of cmd, settings, and capabilities after root detection but before server startup.

3. **Merge strategy matters for configuration priority**, not for settings flattening. Use 'keep' for nvim-lspconfig setup (user config wins), 'force' for capabilities merging (cmp overrides defaults).

4. **Most settings propagation failures** are due to using wrong setup method (vim.lsp.config instead of setup), wrong nesting (settings at top-level), or path issues (tilde without expansion).

5. **Debugging is straightforward** with :LspInfo, :LspLog, print statements, and process inspection. These tools show exactly what configuration is being used and what arguments are passed.

---

**Document Generated:** November 12, 2025
**Scope:** nvim-lspconfig settings flattening, on_new_config callback, and configuration merging
