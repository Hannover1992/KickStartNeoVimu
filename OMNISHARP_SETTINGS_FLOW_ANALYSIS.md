# OmniSharp Settings Flow Analysis

**Date:** 2025-11-12  
**Focus:** on_new_config function and settings flattening mechanism  
**Source:** `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`

## Executive Summary

The `on_new_config` function in nvim-lspconfig's OmniSharp configuration:
1. Takes a `settings` table with nested structure
2. Flattens it into command-line arguments using colon-delimited format
3. Appends these arguments to the OmniSharp command

**Critical Finding:** Settings MUST be nested under parent keys (e.g., `RoslynExtensionsOptions`, `FormattingOptions`) to generate correct command-line arguments.

---

## The flatten() Function (Lines 58-70)

### Source Code
```lua
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
```

### Behavior

**Purpose:** Recursively converts nested Lua tables into OmniSharp command-line argument format.

**Algorithm:**
1. Iterate through table key-value pairs
2. If value is a table: recursively flatten and prepend current key with `:` separator
3. If value is scalar: format as `key=value`
4. Return array of formatted strings

**Output Format:**
- Nested: `ParentKey:ChildKey=value`
- Deep nesting: `Level1:Level2:Level3=value`
- Boolean values: converted to strings `"true"` or `"false"`

### Test Results

#### Test Case 1: Correct Nested Structure
```lua
Input:
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = false,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
  }
}

Output:
[1] FormattingOptions:EnableEditorConfigSupport=true
[2] RoslynExtensionsOptions:EnableAnalyzersSupport=true
[3] RoslynExtensionsOptions:EnableImportCompletion=false
```
✅ **Correct format** - OmniSharp will recognize these arguments.

#### Test Case 2: Incorrect Flat Structure
```lua
Input:
settings = {
  EnableAnalyzersSupport = true,
  EnableImportCompletion = false,
}

Output:
[1] EnableAnalyzersSupport=true
[2] EnableImportCompletion=false
```
❌ **Wrong format** - Missing parent key prefix. OmniSharp will ignore these.

#### Test Case 3: Deep Nesting (3 Levels)
```lua
Input:
settings = {
  RoslynExtensionsOptions = {
    InlayHints = {
      EnableForParameters = true,
    }
  }
}

Output:
[1] RoslynExtensionsOptions:InlayHints:EnableForParameters=true
```
✅ **Correct format** - Supports arbitrary nesting depth.

---

## The on_new_config Function (Lines 46-78)

### Full Command Generation Process

```lua
on_new_config = function(new_config, _)
  -- Step 1: Copy base command
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- Step 2: Append hard-coded arguments
  table.insert(new_config.cmd, '-z')
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  table.insert(new_config.cmd, '--languageserver')

  -- Step 3: Flatten and append settings
  if new_config.settings then
    vim.list_extend(new_config.cmd, flatten(new_config.settings))
  end

  -- Step 4: Disable workspace folders
  new_config.capabilities = vim.deepcopy(new_config.capabilities)
  new_config.capabilities.workspace.workspaceFolders = false
end
```

### Command Generation Example

**Configuration:**
```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', '/path/to/OmniSharp.dll' },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
    }
  }
})
```

**Generated Command:**
```
[1]  dotnet
[2]  /path/to/OmniSharp.dll
[3]  -z
[4]  --hostPID
[5]  12345
[6]  DotNet:enablePackageRestore=false
[7]  --encoding
[8]  utf-8
[9]  --languageserver
[10] FormattingOptions:EnableEditorConfigSupport=true
[11] RoslynExtensionsOptions:EnableAnalyzersSupport=true
[12] RoslynExtensionsOptions:EnableImportCompletion=true
```

---

## Settings Structure Requirements

### Expected Format (from default_config, lines 5-42)

```lua
settings = {
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    OrganizeImports = nil,
  },
  MsBuild = {
    LoadProjectsOnDemand = nil,
  },
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = nil,
    EnableImportCompletion = nil,
    AnalyzeOpenDocumentsOnly = nil,
  },
  Sdk = {
    IncludePrereleases = true,
  },
}
```

### Parent Keys (Required)

These are the **only** top-level keys OmniSharp recognizes:

| Parent Key | Purpose |
|------------|---------|
| `FormattingOptions` | Code formatting settings (EditorConfig, import organization) |
| `MsBuild` | MSBuild project system settings |
| `RoslynExtensionsOptions` | Roslyn analyzer, completion, and code analysis settings |
| `Sdk` | .NET SDK version settings |

### Child Keys (OmniSharp Properties)

| Full Path | Type | Description |
|-----------|------|-------------|
| `FormattingOptions:EnableEditorConfigSupport` | boolean | Read .editorconfig rules |
| `FormattingOptions:OrganizeImports` | boolean | Sort using directives on format |
| `MsBuild:LoadProjectsOnDemand` | boolean | Lazy-load projects (for large solutions) |
| `RoslynExtensionsOptions:EnableAnalyzersSupport` | boolean | Enable Roslyn analyzers |
| `RoslynExtensionsOptions:EnableImportCompletion` | boolean | Auto-import suggestions in completion |
| `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly` | boolean | Limit analyzer scope |
| `Sdk:IncludePrereleases` | boolean | Use preview .NET SDK versions |

### Handling nil Values

- `nil` values are **skipped** during flattening (no command-line argument generated)
- This allows defaults to be applied by OmniSharp
- Explicitly set `false` if you want to disable a feature

---

## Version History

### April 2024: Breaking Change (Commit 2054452)

**Before (snake_case flags at root level):**
```lua
require('lspconfig').omnisharp.setup({
  enable_roslyn_analyzers = true,  -- Root level, snake_case
  organize_imports_on_format = false,
})
```

**After (nested PascalCase in settings table):**
```lua
require('lspconfig').omnisharp.setup({
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  -- Nested, PascalCase
    },
    FormattingOptions = {
      OrganizeImports = false,
    }
  }
})
```

**Reason for Change:**
- Standardization with LSP protocol (settings table)
- Flexibility for arbitrary OmniSharp settings without code changes
- Consistency with other language servers in nvim-lspconfig

**Migration:**
| Old (deprecated) | New (current) |
|------------------|---------------|
| `enable_roslyn_analyzers` | `settings.RoslynExtensionsOptions.EnableAnalyzersSupport` |
| `organize_imports_on_format` | `settings.FormattingOptions.OrganizeImports` |
| `enable_import_completion` | `settings.RoslynExtensionsOptions.EnableImportCompletion` |
| `enable_editorconfig_support` | `settings.FormattingOptions.EnableEditorConfigSupport` |
| `sdk_include_prereleases` | `settings.Sdk.IncludePrereleases` |

---

## Common Mistakes

### ❌ Mistake 1: Flat settings (missing parent key)
```lua
settings = {
  EnableAnalyzersSupport = true,  -- WRONG: no parent key
}
-- Generates: EnableAnalyzersSupport=true
-- OmniSharp expects: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

### ❌ Mistake 2: Wrong wrapper key
```lua
settings = {
  omnisharp = {  -- WRONG: not an OmniSharp parent key
    EnableAnalyzersSupport = true,
  }
}
-- Generates: omnisharp:EnableAnalyzersSupport=true
-- OmniSharp expects: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

### ❌ Mistake 3: snake_case instead of PascalCase
```lua
settings = {
  RoslynExtensionsOptions = {
    enable_analyzers_support = true,  -- WRONG: snake_case
  }
}
-- Generates: RoslynExtensionsOptions:enable_analyzers_support=true
-- OmniSharp expects: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

### ❌ Mistake 4: Using deprecated root-level flags
```lua
enable_roslyn_analyzers = true,  -- WRONG: deprecated syntax
settings = { ... }
```
The old flags are **ignored** (silently). Only `settings` table is processed.

---

## Correct Configuration Examples

### Minimal (enable analyzers only)
```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll') },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    }
  }
})
```

### Full-featured
```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll') },
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
    MsBuild = {
      LoadProjectsOnDemand = false,  -- Load all projects
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,  -- Analyze entire solution
    },
    Sdk = {
      IncludePrereleases = true,
    },
  },
  on_attach = function(client, bufnr)
    -- Your keybindings
  end,
})
```

---

## Debugging Settings

### Check what command will be executed

```lua
-- In Neovim, after opening a C# file:
:lua print(vim.inspect(vim.lsp.get_clients()[1].cmd))
```

This shows the **exact command array** passed to OmniSharp, including all flattened settings.

### Verify settings structure

```lua
:lua print(vim.inspect(vim.lsp.get_clients()[1].config.settings))
```

Should show nested structure with parent keys.

### Enable LSP logging

```lua
:lua vim.lsp.set_log_level('debug')
:LspLog
```

Look for the command execution line showing all arguments.

---

## Summary

### Key Takeaways

1. **Settings MUST be nested:**
   ```lua
   settings = {
     RoslynExtensionsOptions = {  -- Parent key required!
       EnableAnalyzersSupport = true,
     }
   }
   ```

2. **flatten() converts to colon-delimited format:**
   - `ParentKey:ChildKey=value`
   - Not `ChildKey=value`

3. **on_new_config appends flattened settings to cmd:**
   - Hard-coded flags first (`-z`, `--hostPID`, etc.)
   - Then flattened settings

4. **Use PascalCase for OmniSharp properties:**
   - `EnableAnalyzersSupport` ✅
   - Not `enable_analyzers_support` ❌

5. **nil values are skipped:**
   - Allows OmniSharp to apply defaults
   - Use `false` to explicitly disable

### Verification Checklist

- [ ] Settings are nested under parent key (`RoslynExtensionsOptions`, etc.)
- [ ] Property names use PascalCase
- [ ] No deprecated root-level flags (`enable_roslyn_analyzers`, etc.)
- [ ] `:LspInfo` shows OmniSharp attached
- [ ] `:lua print(vim.inspect(vim.lsp.get_clients()[1].cmd))` shows `RoslynExtensionsOptions:...` arguments
- [ ] Roslyn analyzers working (warnings from .editorconfig rules appear)

---

## References

- **Source File:** `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
- **Breaking Change Commit:** 2054452 (April 9, 2024)
- **OmniSharp Documentation:** https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
