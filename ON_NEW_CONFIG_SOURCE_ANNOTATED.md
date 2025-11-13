# on_new_config Function - Fully Annotated Source Code

**Source File:** `~/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua`
**Lines:** 46-78
**Date Analyzed:** 2025-11-13

---

## Complete Function with Line-by-Line Annotations

```lua
-- LINE 46: Function definition
on_new_config = function(new_config, _)
  -- PARAMETERS:
  -- new_config: The LSP configuration object that will be modified
  --             Contains cmd, settings, capabilities, etc.
  -- _: Second parameter (unused, typically root_dir but we ignore it)

  -- LINE 48: CRITICAL LINE #1 - Copy and validate cmd
  new_config.cmd = { unpack(new_config.cmd or {}) }

  -- ANALYSIS:
  -- What this does:
  --   1. If new_config.cmd is nil → evaluates to {}
  --   2. If new_config.cmd is { "dotnet", "/path" } → stays as is
  --   3. unpack() spreads the array elements
  --   4. { } around it reconstructs as new array
  --
  -- Why this pattern?
  --   - Creates a NEW array (not reference to original)
  --   - Allows safe modification without affecting source
  --   - Ensures cmd is always an array (never nil after this)
  --
  -- EXAMPLE TRANSFORMATIONS:
  -- Input: new_config.cmd = { "dotnet", "/path/to/OmniSharp.dll" }
  -- Output: new_config.cmd = { "dotnet", "/path/to/OmniSharp.dll" }  (copy)
  --
  -- Input: new_config.cmd = nil
  -- Output: new_config.cmd = {}  (empty array)
  --
  -- Input: new_config.cmd = { "OmniSharp" }
  -- Output: new_config.cmd = { "OmniSharp" }  (copy)

  -- LINE 49-52: CRITICAL LINES - Append hard-coded LSP parameters
  -- These are ALWAYS added by on_new_config, regardless of user config

  -- LINE 49: Add "-z" flag
  table.insert(new_config.cmd, '-z')
  -- WHAT: Instructs OmniSharp to use STDIN/STDOUT
  -- WHY: Required for LSP protocol (standard language server communication)
  -- RESULT: cmd gets one more element at the end
  --
  -- EXAMPLE:
  -- Before: { "dotnet", "/path/to/OmniSharp.dll" }
  -- After:  { "dotnet", "/path/to/OmniSharp.dll", "-z" }

  -- LINE 50: Add "--hostPID" with current Neovim process ID
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
  -- WHAT: Tells OmniSharp the parent process ID
  -- WHY: If Neovim dies, OmniSharp can detect it and exit gracefully
  -- HOW:
  --   - vim.fn.getpid() gets Neovim's process ID (e.g., 12345)
  --   - tostring() converts number to string (LSP requirements)
  --   - vim.list_extend adds both elements to array
  -- RESULT: Two more elements added
  --
  -- EXAMPLE:
  -- Before: { "dotnet", "/path/to/OmniSharp.dll", "-z" }
  -- After:  { "dotnet", "/path/to/OmniSharp.dll", "-z", "--hostPID", "12345" }

  -- LINE 51: Add NuGet restore disable flag
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
  -- WHAT: Tells OmniSharp not to restore NuGet packages on startup
  -- WHY: Speeds up LSP initialization (packages should be restored before)
  -- WHEN: Only makes sense if you've run "dotnet restore" beforehand
  -- RESULT: One more element added
  --
  -- EXAMPLE:
  -- Before: { "dotnet", "/path/to/OmniSharp.dll", "-z", "--hostPID", "12345" }
  -- After:  { "dotnet", "/path/to/OmniSharp.dll", "-z", "--hostPID", "12345",
  --          "DotNet:enablePackageRestore=false" }

  -- LINE 52: Add encoding and language server flag
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
  -- WHAT: UTF-8 text encoding for communication
  -- WHY: Standard for modern text editors and LSP
  -- RESULT: Two more elements added
  --
  -- EXAMPLE:
  -- Before: { ..., "DotNet:enablePackageRestore=false" }
  -- After:  { ..., "DotNet:enablePackageRestore=false", "--encoding", "utf-8" }

  -- LINE 53: Add language server mode flag
  table.insert(new_config.cmd, '--languageserver')
  -- WHAT: Tells OmniSharp to run in language server mode
  -- WHY: Required for LSP protocol (alternative is "stdio" mode)
  -- RESULT: One more element added
  --
  -- EXAMPLE:
  -- Final: { "dotnet", "/path/to/OmniSharp.dll", "-z", "--hostPID", "12345",
  --         "DotNet:enablePackageRestore=false", "--encoding", "utf-8",
  --         "--languageserver" }

  -- LINE 54: Empty line

  -- LINE 55-57: CRITICAL SECTION - Flatten settings into command-line args
  if new_config.settings then
    -- CONDITION: Only if user provided settings
    --
    -- WHY NOT AUTOMATIC:
    -- If no settings provided, nothing to flatten → skip
    -- This saves processing and keeps cmd minimal
    --
    -- EXAMPLE:
    -- If settings = {} (empty) → if evaluates to true but flatten returns empty
    -- If settings = nil → if evaluates to false, block skipped entirely

    -- LINE 56: Flatten settings and add to cmd
    vim.list_extend(new_config.cmd, flatten(new_config.settings))
    -- WHAT: Converts nested settings table to flat command-line arguments
    -- HOW:
    --   1. flatten() function processes settings (see below for details)
    --   2. Converts nested structure to array of strings
    --   3. vim.list_extend adds them all to cmd array
    --
    -- EXAMPLE TRANSFORMATION:
    -- Input settings:
    --   {
    --     RoslynExtensionsOptions = {
    --       EnableAnalyzersSupport = true,
    --       EnableImportCompletion = true,
    --     },
    --     FormattingOptions = {
    --       EnableEditorConfigSupport = true,
    --     }
    --   }
    --
    -- After flatten():
    --   {
    --     "FormattingOptions:EnableEditorConfigSupport=true",
    --     "RoslynExtensionsOptions:EnableAnalyzersSupport=true",
    --     "RoslynExtensionsOptions:EnableImportCompletion=true"
    --   }
    --
    -- Added to cmd, result:
    --   { "dotnet", "/path/to/OmniSharp.dll", "-z", "--hostPID", "12345",
    --     "DotNet:enablePackageRestore=false", "--encoding", "utf-8",
    --     "--languageserver",
    --     "FormattingOptions:EnableEditorConfigSupport=true",
    --     "RoslynExtensionsOptions:EnableAnalyzersSupport=true",
    --     "RoslynExtensionsOptions:EnableImportCompletion=true" }
  end

  -- LINE 57: End of if block

  -- LINE 58: Empty line

  -- LINE 59-61: Disable workspace folders capability
  -- LINE 59: Ensure capabilities exist (deep copy to avoid mutation)
  new_config.capabilities = vim.deepcopy(new_config.capabilities)
  -- WHAT: Makes a complete copy of the capabilities table
  -- WHY: Prevents modifying shared parent capability object
  -- RESULT: Safe to modify capabilities without side effects
  --
  -- vim.deepcopy is important:
  -- - Shallow copy would share nested tables (bad)
  -- - Deep copy creates new tables at all levels (good)

  -- LINE 60-61: Disable workspace folders (OmniSharp doesn't support)
  new_config.capabilities.workspace.workspaceFolders = false
  -- WHAT: Sets workspace folders capability to false
  -- WHY: OmniSharp-Roslyn has a known bug with workspace folders
  --      Disabling this prevents LSP from trying to use the feature
  -- RESULT: LSP won't ask OmniSharp for workspace folder operations
  --
  -- WITHOUT THIS:
  -- LSP tries to use workspace.workspaceFolders
  -- OmniSharp doesn't implement it properly
  -- Causes warnings or strange behavior
  --
  -- WITH THIS:
  -- LSP knows not to use this capability
  -- Cleaner interaction

  -- LINE 62: Empty line

  -- LINE 63: End of on_new_config function
end
```

---

## The flatten() Function (Called by on_new_config)

While not part of on_new_config directly, it's called by line 56 and is critical to understand:

```lua
-- SOURCE: Lines 58-70 (before on_new_config)
local function flatten(tbl)
  -- PARAMETERS:
  -- tbl: A nested Lua table (settings)

  local ret = {}
  -- Initialize empty return array

  for k, v in pairs(tbl) do
    -- Iterate through all key-value pairs in the table
    -- k = key (e.g., "RoslynExtensionsOptions")
    -- v = value (e.g., table with settings, or boolean)

    if type(v) == 'table' then
      -- CASE 1: Value is a nested table
      -- Recursively flatten and add parent key prefix

      for _, pair in ipairs(flatten(v)) do
        -- Recursively call flatten on the nested table
        -- This handles arbitrary nesting depth

        ret[#ret + 1] = k .. ':' .. pair
        -- Prepend parent key with ':' separator
        -- Example: k="RoslynExtensionsOptions", pair="EnableAnalyzersSupport=true"
        --          Result: "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
      end
    else
      -- CASE 2: Value is NOT a table (boolean, string, number, etc.)
      -- Format as key=value and add to result

      ret[#ret + 1] = k .. '=' .. vim.inspect(v)
      -- vim.inspect converts any Lua value to string representation
      -- Examples:
      --   true → "true"
      --   false → "false"
      --   "hello" → "\"hello\""
      --   42 → "42"
    end
  end

  return ret
  -- Return array of flattened strings
end
```

### flatten() Examples

**Example 1: Simple nested structure**

```lua
Input:
{
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  }
}

Processing:
1. k = "RoslynExtensionsOptions"
2. v = { EnableAnalyzersSupport = true }
3. type(v) == 'table' → true, recursively flatten
4. Recursive call on { EnableAnalyzersSupport = true }:
   - k = "EnableAnalyzersSupport"
   - v = true
   - type(v) == 'table' → false
   - Add: "EnableAnalyzersSupport=true"
5. Back to outer level:
   - Prepend parent key: "RoslynExtensionsOptions:EnableAnalyzersSupport=true"

Output:
{ "RoslynExtensionsOptions:EnableAnalyzersSupport=true" }
```

**Example 2: Multiple settings in one category**

```lua
Input:
{
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = true,
    AnalyzeOpenDocumentsOnly = false,
  }
}

Output:
{
  "RoslynExtensionsOptions:EnableAnalyzersSupport=true",
  "RoslynExtensionsOptions:EnableImportCompletion=true",
  "RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false"
}
```

**Example 3: Multiple categories**

```lua
Input:
{
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,
  }
}

Output:
{
  "FormattingOptions:EnableEditorConfigSupport=true",  (arbitrary order)
  "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
}
```

**Example 4: Deep nesting (3 levels)**

```lua
Input:
{
  RoslynExtensionsOptions = {
    InlayHints = {
      EnableForParameters = true,
    }
  }
}

Processing:
1. k = "RoslynExtensionsOptions"
2. v = { InlayHints = { EnableForParameters = true } }
3. Recursively flatten level 1:
   - k = "InlayHints"
   - v = { EnableForParameters = true }
   - Recursively flatten level 2:
     - k = "EnableForParameters"
     - v = true
     - Add: "EnableForParameters=true"
   - Prepend: "InlayHints:EnableForParameters=true"
4. Prepend: "RoslynExtensionsOptions:InlayHints:EnableForParameters=true"

Output:
{ "RoslynExtensionsOptions:InlayHints:EnableForParameters=true" }
```

---

## Complete Flow Example: Step by Step

**User Configuration:**
```lua
require('lspconfig').omnisharp.setup {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
    }
  }
}
```

**Step-by-Step Execution:**

```
INITIAL STATE (before on_new_config):
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll'
}
new_config.settings = {
  RoslynExtensionsOptions = { EnableAnalyzersSupport = true, EnableImportCompletion = true },
  FormattingOptions = { EnableEditorConfigSupport = true }
}

STEP 1: new_config.cmd = { unpack(new_config.cmd or {}) }
Result: (no change, cmd copied)
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll'
}

STEP 2: table.insert(new_config.cmd, '-z')
Result:
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z'
}

STEP 3: vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })
Assuming getpid() = 12345
Result:
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z',
  '--hostPID',
  '12345'
}

STEP 4: table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')
Result:
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z',
  '--hostPID',
  '12345',
  'DotNet:enablePackageRestore=false'
}

STEP 5: vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })
Result:
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z',
  '--hostPID',
  '12345',
  'DotNet:enablePackageRestore=false',
  '--encoding',
  'utf-8'
}

STEP 6: table.insert(new_config.cmd, '--languageserver')
Result:
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z',
  '--hostPID',
  '12345',
  'DotNet:enablePackageRestore=false',
  '--encoding',
  'utf-8',
  '--languageserver'
}

STEP 7: flatten(new_config.settings)
Input settings:
{
  RoslynExtensionsOptions = { EnableAnalyzersSupport = true, EnableImportCompletion = true },
  FormattingOptions = { EnableEditorConfigSupport = true }
}

Output flattened:
{
  'FormattingOptions:EnableEditorConfigSupport=true',
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  'RoslynExtensionsOptions:EnableImportCompletion=true'
}

STEP 8: vim.list_extend(new_config.cmd, flattened_settings)
Result:
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z',
  '--hostPID',
  '12345',
  'DotNet:enablePackageRestore=false',
  '--encoding',
  'utf-8',
  '--languageserver',
  'FormattingOptions:EnableEditorConfigSupport=true',
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  'RoslynExtensionsOptions:EnableImportCompletion=true'
}

STEP 9: new_config.capabilities = vim.deepcopy(new_config.capabilities)
Result: (creates copy of capabilities table)

STEP 10: new_config.capabilities.workspace.workspaceFolders = false
Result: (disables workspace folders in capabilities)

FINAL STATE:
new_config.cmd = {
  'dotnet',
  '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-z',
  '--hostPID',
  '12345',
  'DotNet:enablePackageRestore=false',
  '--encoding',
  'utf-8',
  '--languageserver',
  'FormattingOptions:EnableEditorConfigSupport=true',
  'RoslynExtensionsOptions:EnableAnalyzersSupport=true',
  'RoslynExtensionsOptions:EnableImportCompletion=true'
}

This is the command that will be executed:
dotnet /home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll -z --hostPID 12345 DotNet:enablePackageRestore=false --encoding utf-8 --languageserver FormattingOptions:EnableEditorConfigSupport=true RoslynExtensionsOptions:EnableAnalyzersSupport=true RoslynExtensionsOptions:EnableImportCompletion=true
```

---

## Key Implementation Details

### 1. Why unpack(array or {})?

```lua
-- This pattern:
new_config.cmd = { unpack(new_config.cmd or {}) }

-- Is equivalent to:
if new_config.cmd then
  -- Create new array from elements of existing array
  new_config.cmd = { unpack(new_config.cmd) }
else
  -- Create new empty array
  new_config.cmd = { unpack({}) }
end

-- Which simplifies to:
if new_config.cmd then
  new_config.cmd = { unpack(new_config.cmd) }
else
  new_config.cmd = {}
end
```

### 2. Why vim.list_extend Instead of table.insert?

```lua
-- When adding ONE element:
table.insert(cmd, '-z')
-- Result: cmd[n+1] = '-z'

-- When adding MULTIPLE elements:
vim.list_extend(cmd, { '--hostPID', '12345' })
-- Result: cmd[n+1] = '--hostPID', cmd[n+2] = '12345'

-- NOT:
table.insert(cmd, { '--hostPID', '12345' })
-- This would add the array itself as ONE element!
```

### 3. Why vim.deepcopy for Capabilities?

```lua
-- Shallow copy (WRONG):
new_config.capabilities = new_config.capabilities
-- Points to same table, modifications affect parent

-- Deep copy (RIGHT):
new_config.capabilities = vim.deepcopy(new_config.capabilities)
-- Creates new independent copy, safe to modify
```

### 4. Why flatten() is Recursive

```lua
-- Handles arbitrary nesting depth:
{
  Level1 = {
    Level2 = {
      Level3 = {
        Property = true
      }
    }
  }
}

-- Produces:
"Level1:Level2:Level3:Property=true"

-- Without recursion, only 1-2 levels would work
-- With recursion, unlimited nesting supported
```

---

## Summary of on_new_config Behavior

| Line(s) | Purpose | Modifies | User Override? |
|---------|---------|----------|---|
| 48 | Copy cmd array | cmd | No - always executed |
| 49-53 | Add LSP hard-coded args | cmd | No - always added |
| 55-57 | Add flattened settings | cmd | Only if user provides settings |
| 59-61 | Disable workspace folders | capabilities | No - always executed |

---

## Critical Insights

1. **on_new_config ALWAYS modifies cmd**, regardless of user config
2. **Hard-coded args are APPENDED**, not prepended or replaced
3. **User cmd is preserved** - it stays at the beginning
4. **Settings are flattened only if provided** - empty settings skip this step
5. **The function is called automatically** - users don't call it directly
6. **Modifications happen in-place** - the new_config object is modified directly

