# OmniSharp on_new_config Analysis - Complete Summary

**Analysis Date:** 2025-11-12  
**Request:** Focus on the on_new_config function (lines 46-78) in omnisharp.lua  
**Purpose:** Understand how settings are flattened and what format is expected

---

## Executive Summary

The nvim-lspconfig OmniSharp configuration uses a recursive `flatten()` function to convert nested Lua tables into command-line arguments in the format `ParentKey:ChildKey=value`.

**Critical Requirement:** Settings MUST be nested under parent keys (`RoslynExtensionsOptions`, `FormattingOptions`, etc.) to produce valid OmniSharp arguments.

---

## Key Findings

### 1. The flatten() Function EXISTS (Lines 58-70)

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

- **Function:** Recursive
- **Input:** Nested Lua table
- **Output:** Array of strings in format `Key:SubKey=value`
- **Location:** Defined inline within `on_new_config` (not imported)

### 2. flatten() is Called Correctly (Line 72)

```lua
if new_config.settings then
  vim.list_extend(new_config.cmd, flatten(new_config.settings))
end
```

- **When:** Only if `new_config.settings` is not nil
- **Where:** After hard-coded arguments are added to cmd
- **Result:** Flattened settings are appended to the command array

### 3. Expected Settings Structure

From the `default_config` (lines 5-42):

```lua
settings = {
  FormattingOptions = {           -- Parent key (required)
    EnableEditorConfigSupport = true,
    OrganizeImports = nil,
  },
  MsBuild = {                     -- Parent key (required)
    LoadProjectsOnDemand = nil,
  },
  RoslynExtensionsOptions = {     -- Parent key (required)
    EnableAnalyzersSupport = nil,
    EnableImportCompletion = nil,
    AnalyzeOpenDocumentsOnly = nil,
  },
  Sdk = {                         -- Parent key (required)
    IncludePrereleases = true,
  },
}
```

**Key Requirements:**
1. Settings are nested TWO levels deep
2. Top-level keys are OmniSharp parent categories
3. Child keys are actual OmniSharp properties
4. All keys use PascalCase (not snake_case)
5. nil values are skipped (no argument generated)

### 4. Version-Specific Changes

**Breaking Change in April 2024 (Commit 2054452):**

| Aspect | Before | After |
|--------|--------|-------|
| **Location** | Root level of setup() | Nested in `settings` table |
| **Naming** | snake_case | PascalCase |
| **Structure** | Flat | Nested (2 levels) |
| **Example** | `enable_roslyn_analyzers = true` | `settings.RoslynExtensionsOptions.EnableAnalyzersSupport = true` |

**Migration Table:**

| Old (deprecated) | New (current) |
|------------------|---------------|
| `enable_roslyn_analyzers` | `settings.RoslynExtensionsOptions.EnableAnalyzersSupport` |
| `organize_imports_on_format` | `settings.FormattingOptions.OrganizeImports` |
| `enable_import_completion` | `settings.RoslynExtensionsOptions.EnableImportCompletion` |
| `enable_editorconfig_support` | `settings.FormattingOptions.EnableEditorConfigSupport` |
| `sdk_include_prereleases` | `settings.Sdk.IncludePrereleases` |

---

## Command Generation Process

### Input (User Configuration)
```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', '/path/to/OmniSharp.dll' },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
    }
  }
})
```

### Step 1: on_new_config Called
```lua
on_new_config = function(new_config, _)
```

### Step 2: Base Command Copied
```lua
new_config.cmd = { unpack(new_config.cmd or {}) }
-- Result: { 'dotnet', '/path/to/OmniSharp.dll' }
```

### Step 3: Hard-Coded Arguments Added (Lines 51-55)
```lua
table.insert(new_config.cmd, '-z')
vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
table.insert(new_config.cmd, '--languageserver')
```

### Step 4: Settings Flattened
```lua
flatten(settings) returns:
[
  "FormattingOptions:EnableEditorConfigSupport=true",
  "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
]
```

### Step 5: Flattened Settings Appended
```lua
vim.list_extend(new_config.cmd, flatten(new_config.settings))
```

### Step 6: Final Command Array
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
```

This exact command is what gets executed by Neovim to launch OmniSharp.

---

## Test Results

### Test 1: Correct Nested Settings
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = false,
  }
}

Flattened Output:
"RoslynExtensionsOptions:EnableAnalyzersSupport=true"
"RoslynExtensionsOptions:EnableImportCompletion=false"
```
✅ **Result:** OmniSharp recognizes these arguments

### Test 2: Incorrect Flat Settings
```lua
settings = {
  EnableAnalyzersSupport = true,
  EnableImportCompletion = false,
}

Flattened Output:
"EnableAnalyzersSupport=true"
"EnableImportCompletion=false"
```
❌ **Result:** OmniSharp does NOT recognize these (missing parent key prefix)

### Test 3: Deep Nesting (3 Levels)
```lua
settings = {
  RoslynExtensionsOptions = {
    InlayHints = {
      EnableForParameters = true,
    }
  }
}

Flattened Output:
"RoslynExtensionsOptions:InlayHints:EnableForParameters=true"
```
✅ **Result:** Arbitrary nesting depth supported

---

## Common Mistakes and Fixes

### Mistake 1: Flat Settings (No Parent Key)
```lua
-- WRONG
settings = {
  EnableAnalyzersSupport = true,  -- Missing parent key!
}

-- CORRECT
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  }
}
```

### Mistake 2: Wrong Parent Key
```lua
-- WRONG
settings = {
  omnisharp = {  -- Not an OmniSharp parent key!
    EnableAnalyzersSupport = true,
  }
}

-- CORRECT
settings = {
  RoslynExtensionsOptions = {  -- Valid parent key
    EnableAnalyzersSupport = true,
  }
}
```

### Mistake 3: snake_case Instead of PascalCase
```lua
-- WRONG
settings = {
  RoslynExtensionsOptions = {
    enable_analyzers_support = true,  -- snake_case
  }
}

-- CORRECT
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- PascalCase
  }
}
```

### Mistake 4: Using Deprecated Root-Level Flags
```lua
-- WRONG (deprecated, silently ignored)
require('lspconfig').omnisharp.setup({
  enable_roslyn_analyzers = true,  -- Old syntax
  settings = { ... }
})

-- CORRECT
require('lspconfig').omnisharp.setup({
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    }
  }
})
```

---

## Debugging Commands

### Check Final Command Array
```lua
:lua print(vim.inspect(vim.lsp.get_clients()[1].cmd))
```
Should show arguments like `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

### Check Settings Structure
```lua
:lua print(vim.inspect(vim.lsp.get_clients()[1].config.settings))
```
Should show nested structure with parent keys

### Enable LSP Debug Logging
```lua
:lua vim.lsp.set_log_level('debug')
:LspLog
```
Look for command execution line showing all arguments

---

## Verification Checklist

- [ ] Settings are nested under parent key (`RoslynExtensionsOptions`, etc.)
- [ ] Property names use PascalCase (not snake_case)
- [ ] No deprecated root-level flags (`enable_roslyn_analyzers`, etc.)
- [ ] Parent keys match OmniSharp categories:
  - `FormattingOptions`
  - `MsBuild`
  - `RoslynExtensionsOptions`
  - `Sdk`
- [ ] `:lua print(vim.inspect(vim.lsp.get_clients()[1].cmd))` shows proper format
- [ ] `:LspInfo` shows OmniSharp attached and running

---

## Correct Configuration Template

```lua
require('lspconfig').omnisharp.setup({
  -- Command to start OmniSharp
  cmd = { 
    'dotnet', 
    vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll')
  },
  
  -- Settings (nested under parent keys)
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
    MsBuild = {
      LoadProjectsOnDemand = false,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,        -- Roslyn analyzers
      EnableImportCompletion = true,        -- Auto-import in completion
      AnalyzeOpenDocumentsOnly = false,     -- Analyze entire solution
    },
    Sdk = {
      IncludePrereleases = true,
    },
  },
  
  -- Optional: custom on_attach
  on_attach = function(client, bufnr)
    -- Your keybindings here
  end,
})
```

---

## References

1. **Source File:** `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
2. **Breaking Change Commit:** 2054452 (April 9, 2024) - Changed to standard settings table
3. **flatten() Function:** Lines 58-70
4. **on_new_config Function:** Lines 46-78
5. **default_config:** Lines 4-42 (shows expected structure)

---

## Related Documentation

- **Detailed Analysis:** `OMNISHARP_SETTINGS_FLOW_ANALYSIS.md`
- **Visual Diagram:** `OMNISHARP_SETTINGS_FLOW_DIAGRAM.txt`
- **Command Parameter Analysis:** `OMNISHARP_CMD_PARAMETER_ANALYSIS.md` (Phase 1 findings)
- **Quick Reference:** `OMNISHARP_CMD_QUICK_REFERENCE.md`

---

## Conclusion

The `on_new_config` function in nvim-lspconfig's OmniSharp configuration:

1. **Uses a recursive flatten() function** (lines 58-70) to convert nested tables to command-line args
2. **Expects settings nested under parent keys** (`RoslynExtensionsOptions`, `FormattingOptions`, etc.)
3. **Produces colon-delimited format:** `ParentKey:ChildKey=value`
4. **Appends flattened settings to cmd array** after hard-coded arguments
5. **Requires PascalCase property names** (not snake_case)
6. **Skips nil values** (no argument generated)

**Critical takeaway:** Settings MUST be nested under parent keys to produce valid OmniSharp command-line arguments. Flat settings produce arguments that OmniSharp silently ignores.
