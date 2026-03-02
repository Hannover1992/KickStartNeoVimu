# OmniSharp on_new_config Execution Flow Analysis

## Mission Objective
Understand why OmniSharp's custom `cmd` isn't being applied correctly in init.lua.

---

## Key Findings

### 1. on_new_config Execution Timing

**Source**: `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs.lua` (lines 177-190)

```lua
local make_config = function(root_dir)
  local new_config = tbl_deep_extend('keep', vim.empty_dict(), config)  -- line 178

  -- Step 1: Default on_new_config runs FIRST
  if config_def.on_new_config then
    pcall(config_def.on_new_config, new_config, root_dir)  -- line 185-186
  end

  -- Step 2: User on_new_config runs SECOND
  if config.on_new_config then
    pcall(config.on_new_config, new_config, root_dir)  -- line 188-189
  end

  -- Step 3: LSP client starts with new_config
end
```

**Execution order**:
1. `make_config()` is called by manager when creating LSP client
2. Default `on_new_config` runs (from `omnisharp.lua`)
3. User `on_new_config` runs (from `init.lua`)
4. Both run **BEFORE** LSP client starts
5. Both can mutate `new_config` in-place

**Answer**: on_new_config runs **BEFORE** client starts, default runs **BEFORE** user override.

---

### 2. Config Merge Order

**Source**: `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs.lua` (line 70)

```lua
function M.setup(user_config)
  local config = tbl_deep_extend('keep', user_config, default_config)
  -- 'keep' means: user_config values OVERRIDE default_config values
end
```

**Merge priority**:
- **Highest**: `user_config` (from `init.lua`)
- **Lowest**: `default_config` (from `omnisharp.lua`)

**Answer**: User config **OVERRIDES** default config.

---

### 3. Why cmd Is Being Overridden

**Problem location**: `/home/uczen/.config/nvim/init.lua` (lines 710-726)

```lua
on_new_config = function(new_config, new_root_dir)
  -- PROBLEM: This runs AFTER default on_new_config already ran!
  new_config.cmd = {  -- ❌ OVERWRITES cmd (loses appended args)
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s',
    vim.fn.expand('/mnt/c/.../cencoco/src'),
    '-loglevel',
    'Information',
  }
  -- Then tries to call default on_new_config again
  local omnisharp_config = require('lspconfig.configs').omnisharp
  if omnisharp_config and omnisharp_config.default_config and omnisharp_config.default_config.on_new_config then
    omnisharp_config.default_config.on_new_config(new_config, new_root_dir)  -- ❌ Already ran!
  end
end
```

**Execution flow**:
1. **Step 1** (line 185-186 in configs.lua): Default `on_new_config` runs
   - Takes `cmd` from user config (line 704-707)
   - Appends `-z`, `--hostPID`, `DotNet:enablePackageRestore=false`, etc.
   - Flattens settings: `RoslynExtensionsOptions:EnableAnalyzersSupport=true`, etc.
   - Result: `cmd` is correct!

2. **Step 2** (line 188-189 in configs.lua): User `on_new_config` runs
   - **OVERWRITES** `cmd` entirely (line 712-719)
   - Loses all appended args from step 1
   - Tries to call default `on_new_config` again (line 724)
   - But it's already in `lspconfig.configs.omnisharp.default_config.on_new_config`, which is the SAME function that already ran!

3. **Result**: `cmd` only has base command, missing:
   - `-z`, `--hostPID`, `DotNet:enablePackageRestore=false`, etc.
   - Flattened settings args

**Answer**: cmd is overridden because user `on_new_config` runs AFTER default, replacing cmd instead of preserving it.

---

### 4. What Default on_new_config Does

**Source**: `/home/uczen/.local/share/nvim/lazy/nvim-lspconfig/lua/lspconfig/configs/omnisharp.lua` (lines 46-78)

```lua
on_new_config = function(new_config, _)
  -- Step 1: Copy existing cmd
  new_config.cmd = { unpack(new_config.cmd or {}) }  -- line 48

  -- Step 2: Append hard-coded args
  table.insert(new_config.cmd, '-z')  -- line 51
  vim.list_extend(new_config.cmd, { '--hostPID', tostring(vim.fn.getpid()) })  -- line 52
  table.insert(new_config.cmd, 'DotNet:enablePackageRestore=false')  -- line 53
  vim.list_extend(new_config.cmd, { '--encoding', 'utf-8' })  -- line 54
  table.insert(new_config.cmd, '--languageserver')  -- line 55

  -- Step 3: Flatten settings into command-line args
  local function flatten(tbl)
    -- Converts { RoslynExtensionsOptions = { EnableAnalyzersSupport = true } }
    -- Into: "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
  end
  if new_config.settings then
    vim.list_extend(new_config.cmd, flatten(new_config.settings))  -- line 72
  end
end
```

**What it does**:
1. **PRESERVES** existing `cmd` from user config
2. **APPENDS** hard-coded args (-z, --hostPID, etc.)
3. **FLATTENS** settings table into command-line args

**Critical insight**: Default `on_new_config` EXPECTS `cmd` to already exist! It doesn't SET cmd, it APPENDS to it.

---

### 5. Correct Way to Set Custom cmd

**DON'T** override `on_new_config`. The default one does everything correctly!

**Correct configuration**:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/.../cencoco/src'),
    '-loglevel', 'Information',
  },
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
}
```

**No `on_new_config` override needed!**

**Execution flow**:
1. User provides `cmd` (lines 704-707)
2. Default `on_new_config` runs (automatically)
3. Default appends hard-coded args to `cmd`
4. Default flattens `settings` into `cmd`
5. LSP client starts with complete `cmd`

**Result**:
```bash
dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /mnt/c/.../cencoco/src \
  -loglevel Information \
  -z \
  --hostPID 12345 \
  DotNet:enablePackageRestore=false \
  --encoding utf-8 \
  --languageserver \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false \
  FormattingOptions:EnableEditorConfigSupport=true \
  FormattingOptions:OrganizeImports=true
```

---

## Solution

### Fix for init.lua

**Remove** lines 708-726 (the entire `on_new_config` override):

```diff
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
+   '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
+   '-loglevel', 'Information',
  },
- -- CRITICAL: We must set cmd here in `default_cmd` format AND preserve on_new_config
- -- lspconfig's on_new_config will append args and flatten settings
- on_new_config = function(new_config, new_root_dir)
-   -- Start with our custom cmd
-   new_config.cmd = {
-     'dotnet',
-     vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
-     '-s',
-     vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src'),
-     '-loglevel',
-     'Information',
-   }
-   -- Call the original on_new_config to flatten settings
-   local lspconfig = require('lspconfig')
-   local omnisharp_config = require('lspconfig.configs').omnisharp
-   if omnisharp_config and omnisharp_config.default_config and omnisharp_config.default_config.on_new_config then
-     omnisharp_config.default_config.on_new_config(new_config, new_root_dir)
-   end
- end,
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
```

**Change summary**:
1. ✅ Keep `cmd` definition
2. ✅ Add `-s` and `-loglevel` to `cmd` array (move from `on_new_config`)
3. ❌ **DELETE** entire `on_new_config` override (lines 708-726)
4. ✅ Keep `settings` definition

---

## Answers to Original Questions

### 1. When does on_new_config run?

**Answer**: `on_new_config` runs **BEFORE** the LSP client starts, inside `make_config()` function (configs.lua line 177).

**Timing**:
- Default `on_new_config` runs first (line 185-186)
- User `on_new_config` runs second (line 188-189)
- Both run before `vim.lsp.start_client()`

---

### 2. What overrides what?

**Answer**:

**Config merge** (line 70):
- User config **OVERRIDES** default config
- `tbl_deep_extend('keep', user_config, default_config)` → user wins

**on_new_config execution**:
- Default `on_new_config` runs **FIRST** (modifies config)
- User `on_new_config` runs **SECOND** (can override changes)
- If user `on_new_config` sets `new_config.cmd = {...}`, it **OVERWRITES** what default did

**Priority**:
1. **Highest**: User `on_new_config` (runs last, can overwrite everything)
2. **Middle**: Default `on_new_config` (runs first, transforms config)
3. **Lowest**: `default_config` values (merged before on_new_config runs)

---

### 3. Why is cmd showing "OmniSharp" instead of "dotnet OmniSharp.dll"?

**Answer**: The user `on_new_config` (init.lua lines 710-726) runs AFTER default and:
1. **Overwrites** `cmd` completely (line 712-719)
2. Loses all appended args from default `on_new_config`
3. Tries to call default `on_new_config` again, but at that point it's calling `require('lspconfig.configs').omnisharp.default_config.on_new_config`, which is accessing the CONFIG definition, not re-running the function in the execution flow

The result is an incomplete `cmd` array missing the hard-coded args.

---

### 4. Correct way to set custom cmd for OmniSharp?

**Answer**:

**DON'T override `on_new_config`!**

Just provide:
- `cmd`: Base command with your custom args (`-s`, `-loglevel`, etc.)
- `settings`: OmniSharp settings

Default `on_new_config` will:
- Append hard-coded args (-z, --hostPID, etc.)
- Flatten settings into command-line args

**Example**:
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/path/to/solution'),
    '-loglevel', 'Information',
  },
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
}
```

No `on_new_config` needed! ✅

---

## Verification Commands

After applying fix:

```bash
# 1. Clear cache
rm -rf ~/.cache/nvim/luac/

# 2. Kill OmniSharp
pkill -f omnisharp

# 3. Restart Neovim and open C# file
nvim /path/to/file.cs

# 4. Check :LspInfo
:LspInfo
# Should show:
# cmd: { "dotnet", "/home/uczen/.../OmniSharp.dll", "-s", "/mnt/c/.../cencoco/src", "-loglevel", "Information", ... }

# 5. Check running process
ps aux | grep omnisharp | grep -v grep
# Should include all args:
# -s /mnt/c/.../cencoco/src
# -loglevel Information
# -z --hostPID 12345
# RoslynExtensionsOptions:EnableAnalyzersSupport=true
# etc.
```

---

## Conclusion

The current `on_new_config` override in init.lua is **fundamentally flawed** because:
1. It runs AFTER default `on_new_config` already processed the config
2. It OVERWRITES `cmd`, losing the appended args
3. It tries to call default `on_new_config` again, but that's just accessing a config property, not re-running in the execution flow

**Solution**: Remove the override entirely. The default `on_new_config` is perfectly designed to handle custom `cmd` and `settings`. Just provide them in the config, and let lspconfig do its job!
