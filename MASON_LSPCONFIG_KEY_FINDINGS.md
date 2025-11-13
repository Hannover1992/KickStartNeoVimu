# Mason-lspconfig: Key Findings & Critical Insights

## The Essential Truth About Handlers

### Handlers Run DURING setup(), Not After
```
DON'T do this:
require('mason-lspconfig').setup { handlers = {...} }
require('lspconfig').omnisharp.setup(config)  -- ❌ Too late!

DO this:
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(config)  -- ✅ During setup
    end
  }
}
```

This is the #1 mistake that breaks configurations.

---

## The Complete Settings Flow

```
init.lua: Define servers table
    ↓
servers.omnisharp = {
  cmd = {...},
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    }
  }
}
    ↓
mason-lspconfig.setup() called
    ↓
Handler function runs (for omnisharp)
    ↓
Handler calls: lspconfig.omnisharp.setup(servers.omnisharp)
    ↓
lspconfig's on_new_config() function is called
    ↓
on_new_config() recursive flatten() function runs:
    RoslynExtensionsOptions = { EnableAnalyzersSupport = true }
        ↓
    "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
    ↓
Settings appended to cmd array
    ↓
Final command executed:
    dotnet /path/to/OmniSharp.dll [...args...] \
      RoslynExtensionsOptions:EnableAnalyzersSupport=true \
      [...more settings...]
```

Every step is automatic. You just provide the right config.

---

## The Three Critical Requirements

### 1. Override cmd (Use Full DLL Path)
```lua
-- ❌ WRONG: Uses Mason default, loses solution path
omnisharp = {
  settings = { ... }
}

-- ✅ CORRECT: Full control
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/path/to/Backend',
    '-loglevel', 'Information',
  },
  settings = { ... }
}
```

Without this, `on_new_config()` has no base command to append settings to.

### 2. Nest Settings Correctly (2 Levels Deep)
```lua
-- ❌ WRONG: Flat (no parent key)
settings = {
  EnableAnalyzersSupport = true,
}

-- ✅ CORRECT: Nested (parent key required)
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  },
}
```

The `flatten()` function expects parent → child structure.
Output: `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

### 3. Use PascalCase for Keys
```lua
-- ❌ WRONG: snake_case (old deprecated API)
settings = {
  RoslynExtensionsOptions = {
    enable_analyzers_support = true,  -- Wrong!
  },
}

-- ✅ CORRECT: PascalCase
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- Correct!
  },
}
```

OmniSharp command-line arguments are PascalCase.

---

## The Four Handler Patterns

### Pattern A: Default Handler (USE THIS)
✅ **Simplest, works for 99% of cases**

```lua
handlers = {
  function(server_name)
    local server = servers[server_name] or {}
    require('lspconfig')[server_name].setup(server)
  end,
}
```

Pros:
- Automatic for all servers
- Simple code
- Scales well

Cons:
- Less explicit

---

### Pattern B: Named Handler (Use if different behavior needed)
✅ **When you need special handling**

```lua
handlers = {
  function(server_name)
    if server_name == 'omnisharp' then return end
    -- handle others
  end,

  omnisharp = function()
    require('lspconfig').omnisharp.setup(servers.omnisharp)
  end,
}
```

Pros:
- Very explicit
- Can have different config

Cons:
- More code

---

### Pattern C: Setup After (ONLY if handler skips)
⚠️ **Only works if handler explicitly returns**

```lua
handlers = {
  function(server_name)
    if server_name == 'omnisharp' then return end  -- ← MUST skip
    -- handle others
  end,
}

-- NOW safe to setup explicitly
require('lspconfig').omnisharp.setup(servers.omnisharp)
```

Pros:
- Clear separation

Cons:
- Easy to break by forgetting the return
- Less idiomatic

---

### Pattern D: No Mason-lspconfig (Minimal)
⚠️ **Only for simple projects**

```lua
require('lspconfig').omnisharp.setup({
  cmd = {...},
  settings = {...},
})
```

Pros:
- No dependencies
- Simple

Cons:
- No automatic server detection
- Doesn't scale

---

## Verification Checklist

When your configuration isn't working, verify in order:

```
[ ] OmniSharp installed via Mason
    ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

[ ] DLL path in init.lua is correct
    :echo vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll'

[ ] cmd is overridden (not using default wrapper)
    :LspInfo → Look at cmd field

[ ] Solution path in cmd (-s flag)
    :LspInfo → Look for -s /path/to/Backend

[ ] Settings are present in :LspInfo
    :LspInfo → Look for RoslynExtensionsOptions table

[ ] Settings are properly nested (2 levels)
    Check init.lua → RoslynExtensionsOptions → EnableAnalyzersSupport

[ ] Key names are PascalCase
    Check init.lua → EnableAnalyzersSupport (not enable_analyzers_support)

[ ] Process shows flattened settings
    ps aux | grep omnisharp | grep RoslynExtensionsOptions

[ ] Handler is in mason-lspconfig.setup()
    Check init.lua → handlers function defined inside setup()

[ ] No setup() call after mason-lspconfig.setup()
    Grep init.lua for duplicate setup() calls
```

---

## The on_new_config() Function (What Happens Inside)

This function is called automatically by lspconfig when you call setup():

```lua
on_new_config = function(new_config, _)
  -- 1. Copy the cmd array
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- 2. Append hard-coded arguments
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- 3. If settings exist, flatten and append
  if new_config.settings then
    local function flatten(tbl)
      local ret = {}
      for k, v in pairs(tbl) do
        if type(v) == 'table' then
          for _, pair in ipairs(flatten(v)) do
            ret[#ret + 1] = k .. ':' .. pair
          end
        else
          ret[#ret + 1] = k .. '=' .. vim.inspect(v)
        end
      end
      return ret
    end
    vim.list_extend(new_config.cmd, flatten(new_config.settings))
  end
end
```

**Key insight**: The `flatten()` function recursively converts nested tables to `Key:SubKey=value` format.

---

## Common Configuration Mistakes

### Mistake 1: Using Default cmd
```lua
-- ❌ This won't work
omnisharp = {
  settings = { ... }
  -- No cmd override!
}
```
Result: OmniSharp starts but can't find solution, no intellisense.

### Mistake 2: Flat settings (no parent key)
```lua
-- ❌ This breaks flatten()
settings = {
  EnableAnalyzersSupport = true,
  EnableImportCompletion = true,
}
```
Result: Settings ignored by OmniSharp (wrong format).

### Mistake 3: Duplicate setup() calls
```lua
-- ❌ setup() called twice
require('mason-lspconfig').setup { handlers = {...} }
require('lspconfig').omnisharp.setup(servers.omnisharp)
```
Result: Second call is ignored, config from first call used.

### Mistake 4: Handler outside setup()
```lua
-- ❌ Handler defined but not called
local handlers = { function(name) ... end }
require('mason-lspconfig').setup {}  -- Empty handlers!
```
Result: Handler never runs.

### Mistake 5: Solution path missing
```lua
-- ❌ Missing -s flag and path
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  -- Missing: '-s', '/path/to/Backend'
}
```
Result: OmniSharp can't find solution files.

---

## Settings Flattening Examples

### Example 1: Simple
```lua
Input:
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  }
}

Flattened Output:
"RoslynExtensionsOptions:EnableAnalyzersSupport=true"

Command Line:
dotnet /path/to/OmniSharp.dll ... RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

### Example 2: Multiple values
```lua
Input:
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
  }
}

Flattened Output:
"RoslynExtensionsOptions:EnableAnalyzersSupport=true"
"RoslynExtensionsOptions:EnableImportCompletion=true"
"RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false"
"FormattingOptions:EnableEditorConfigSupport=true"

Command Line:
dotnet /path/to/OmniSharp.dll ... RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
  FormattingOptions:EnableEditorConfigSupport=true
```

### Example 3: nil values (skipped)
```lua
Input:
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = nil,  -- nil is skipped
  }
}

Flattened Output:
"RoslynExtensionsOptions:EnableAnalyzersSupport=true"
-- EnableImportCompletion is NOT included (nil values skipped)
```

---

## The Complete Working Example

This is the minimum needed, with every critical piece:

```lua
-- 1. Define servers with omnisharp config
local servers = {
  omnisharp = {
    -- 2. Override cmd with full DLL path and solution path
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s',  -- Solution flag
      '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend',
      '-loglevel', 'Information',
    },

    -- 3. Settings nested 2 levels deep with PascalCase keys
    settings = {
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,
        EnableImportCompletion = true,
        AnalyzeOpenDocumentsOnly = false,
      },
      FormattingOptions = {
        EnableEditorConfigSupport = true,
        OrganizeImports = true,
      },
    },
  },
}

-- 4. Setup mason-lspconfig with handler
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      -- 5. Handler calls setup() DURING setup()
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}

-- 6. DON'T call setup() again after this!
```

When Neovim starts:
1. Handler runs for 'omnisharp'
2. Handler calls lspconfig.omnisharp.setup(servers.omnisharp)
3. lspconfig calls on_new_config()
4. on_new_config() flattens settings:
   - `RoslynExtensionsOptions:EnableAnalyzersSupport=true`
   - `RoslynExtensionsOptions:EnableImportCompletion=true`
   - etc.
5. Final cmd array includes all flattened settings
6. OmniSharp process starts with full command line
7. StyleCop warnings appear in editor

---

## Key Insight: Why This Matters

The reason mason-lspconfig exists is to bridge two tools:
- **Mason**: Manages installation of LSP servers and tools
- **nvim-lspconfig**: Manages configuration and startup of LSP servers

Mason says: "I installed omnisharp"
lspconfig says: "Here's how to configure omnisharp"
mason-lspconfig says: "I'll call the right setup() at the right time"

If you understand this, you understand why handlers run DURING setup(), and why calling setup() twice breaks things.

---

## References

- **Handler Research**: `MASON_LSPCONFIG_HANDLER_RESEARCH.md` (488 lines, complete technical details)
- **Quick Reference**: `MASON_LSPCONFIG_QUICK_REFERENCE.md` (visual patterns)
- **Implementation Guide**: `MASON_LSPCONFIG_IMPLEMENTATION_GUIDE.md` (step-by-step)
- **Research Index**: `MASON_LSPCONFIG_RESEARCH_INDEX.md` (navigation guide)

---

## Summary

1. **Handlers run DURING setup()** - Don't call setup() after
2. **Settings need 2-level nesting** - Parent key required
3. **cmd must be overridden** - Use full DLL path, not wrapper
4. **Keys are PascalCase** - Not snake_case
5. **on_new_config() flattens automatically** - No manual conversion needed
6. **The default handler pattern works** - Simplest, most reliable

Get these 6 points right, and your configuration will work.
