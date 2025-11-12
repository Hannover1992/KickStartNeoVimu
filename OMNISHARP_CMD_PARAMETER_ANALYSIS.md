# nvim-lspconfig OmniSharp cmd Parameter Handling Report

## Executive Summary

nvim-lspconfig uses a sophisticated system for handling OmniSharp cmd parameters through the `on_new_config` callback function. The framework automatically appends hard-coded arguments to the initial `cmd` array, which means custom parameters passed in the `cmd` configuration are often overridden or augmented by the LSP configuration system.

---

## 1. How nvim-lspconfig Handles OmniSharp cmd Parameters

### 1.1 Default Configuration

By default, **omnisharp-roslyn doesn't have a cmd set** in nvim-lspconfig because the framework doesn't make assumptions about your system's binary paths. This is a critical design decision: nvim-lspconfig requires users to explicitly configure the absolute path to the OmniSharp binary.

**Important**: Tilde (~) and environment variables are NOT expanded in the cmd path - you must provide absolute paths.

### 1.2 The `on_new_config` Function

The most important mechanism for understanding cmd parameter handling is the `on_new_config` callback. This function:

1. **Copies the initial cmd**: Takes the user-configured `cmd` array
2. **Appends hard-coded arguments**: Automatically adds required LSP parameters
3. **Modifies the configuration object**: Returns the modified configuration

### 1.3 Hard-Coded Arguments Appended by on_new_config

The `on_new_config` function automatically appends:

```
'-z'
'--hostPID' <current_nvim_process_id>
'DotNet:enablePackageRestore=false'
'--encoding utf-8'
'--languageserver'
```

Additionally, all settings from the `settings` table are flattened into command arguments.

**Example of final cmd array**:
```
{ 'path/to/OmniSharp', '--languageserver', '--hostPID', '12345', '-z', 
  'DotNet:enablePackageRestore=false', '--encoding utf-8', '--languageserver',
  'FormattingOptions:EnableEditorConfigSupport=true', ... }
```

---

## 2. Solution File Handling (`-s` Parameter)

### 2.1 Understanding the `-s` Parameter

The `-s` parameter is used by OmniSharp to specify an explicit solution file or project file path:

```bash
OmniSharp --stdio -s /path/to/solution.sln --languageserver --hostPID 12345
```

**Critical requirement**: OmniSharp requires the path specified with `-s` to be an ABSOLUTE PATH.

### 2.2 Root Directory Detection vs. `-s` Parameter

nvim-lspconfig handles solution file discovery through **root_dir configuration** rather than the `-s` parameter:

```lua
root_dir = util.root_pattern('*.sln', '*.csproj', 'omnisharp.json', 'function.json')
```

This pattern searches for:
1. `.sln` files (solution files)
2. `.csproj` files (C# project files)
3. `omnisharp.json` (OmniSharp configuration file)
4. `function.json` (Azure Functions configuration)

### 2.3 Why `-s` Parameters in cmd Might Not Work

**The `on_new_config` function does NOT automatically add the `-s` parameter**. If you manually add `-s` to your cmd array, it will be passed through, but there are several issues:

1. **Duplicate parameters**: If the `root_dir` detection finds a solution file and you also pass `-s`, you may end up with conflicting parameters
2. **Multiple solution conflicts**: In projects with multiple solutions, the cmd can become malformed with duplicate `-s` flags
3. **Path handling**: The path must be absolute, and there's no automatic expansion or normalization

---

## 3. Typical Configuration Patterns

### 3.1 Basic Configuration with Mason

```lua
require('lspconfig').omnisharp.setup {
  cmd = { "dotnet", vim.fn.stdpath("data") .. "/mason/packages/omnisharp/libexec/OmniSharp.dll" },
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
}
```

In this configuration:
- The base `cmd` is: `{ "dotnet", "/path/to/OmniSharp.dll" }`
- nvim-lspconfig appends: `--languageserver`, `--hostPID`, etc.
- Final command becomes: `dotnet /path/to/OmniSharp.dll --languageserver --hostPID 12345 -z ...`

### 3.2 Direct Binary Configuration

```lua
local pid = vim.fn.getpid()
require('lspconfig').omnisharp.setup {
  cmd = { "/path/to/omnisharp/run", "--languageserver", "--hostPID", tostring(pid) },
}
```

**Note**: Even though `--languageserver` and `--hostPID` are included in the cmd array, nvim-lspconfig will ALSO append them again in `on_new_config`, potentially duplicating them.

### 3.3 Configuration with Explicit Solution File (Not Recommended)

```lua
require('lspconfig').omnisharp.setup {
  cmd = { 
    "dotnet", 
    vim.fn.stdpath("data") .. "/mason/packages/omnisharp/libexec/OmniSharp.dll",
    "-s", "/absolute/path/to/solution.sln"
  },
}
```

**Problems with this approach**:
- The `-s` flag is passed through but isn't properly integrated with `on_new_config`
- If automatic root detection also finds the solution, you get conflicting settings
- The path must be absolute and won't be normalized

---

## 4. Known Issues with cmd Parameters

### 4.1 Issue: Multiple Solution Paths

When working with multiple .NET solutions in the same workspace, the cmd can become:

```bash
omnisharp -z -s /path/to/solution1 --hostPID 59024 DotNet:enablePackageRestore=false 
  --encoding utf-8 --languageserver FormattingOptions:EnableEditorConfigSupport=true -z 
  -s /path/to/solution2
```

**This is malformed** because:
- Duplicate `-z` flags
- Duplicate `--languageserver` flags
- Multiple `-s` flags with different paths (OmniSharp doesn't know which one to use)

### 4.2 Issue: vim.lsp.config() Not Applying Settings

When using `vim.lsp.config()` to set server-specific options instead of `lspconfig.omnisharp.setup()`, settings often don't apply. This is because:

1. `vim.lsp.config()` is a lower-level API that doesn't run the `on_new_config` callback
2. The nvim-lspconfig `setup()` function is the proper way to configure servers
3. `on_new_config` is only called during the `setup()` invocation

### 4.3 Issue: mason-lspconfig Configuration

When using mason-lspconfig to auto-configure OmniSharp:
- It may not configure `root_dir` correctly
- The `cmd` might not be properly set
- Settings can be overridden or ignored

**Workaround**: Manually configure lspconfig with explicit `cmd` and `root_dir` settings instead of relying on mason-lspconfig defaults.

### 4.4 Issue: Path Expansion Not Supported

The cmd array doesn't support:
- Tilde (`~`) expansion
- Environment variable expansion (like `$HOME`)
- Relative paths

You must use absolute paths or `vim.fn.expand()`:

```lua
cmd = { vim.fn.expand("~/.local/share/nvim/mason/bin/OmniSharp") }  -- Won't work
cmd = { vim.fn.expand("~") .. "/.local/share/nvim/mason/bin/OmniSharp" }  -- Works
```

---

## 5. Root Directory vs. Solution File Path

### 5.1 How nvim-lspconfig Uses root_dir

The `root_dir` is used by the LSP framework to:
1. Determine where to launch the LSP server
2. Set the working directory for OmniSharp process
3. Auto-discover solution/project files in that directory

OmniSharp then searches the root_dir for `.sln` and `.csproj` files automatically.

### 5.2 Why Automatic Detection Usually Works

OmniSharp doesn't need the `-s` parameter if:
- The root_dir is correctly detected
- The solution/project file exists in that directory or a parent directory
- OmniSharp can traverse upward to find the solution file

**The LSP automatically initializes with the root directory as the working directory, so OmniSharp can find the solution file through parent directory traversal.**

---

## 6. Why cmd Parameters Might Not Be Applied

### 6.1 Parameter Type Issues

Parameters in the `cmd` array must be **strings**. If you pass other types (numbers, booleans), they won't be properly converted:

```lua
-- WRONG - hostPID is a number
cmd = { omnisharp_bin, "--hostPID", 12345 }

-- RIGHT - hostPID converted to string
cmd = { omnisharp_bin, "--hostPID", tostring(vim.fn.getpid()) }
```

### 6.2 Order of Operations

The actual sequence is:
1. User calls `lspconfig.omnisharp.setup(config)`
2. nvim-lspconfig reads the `cmd` from user config
3. When LSP is about to attach, `on_new_config` is called
4. `on_new_config` modifies `cmd` by appending arguments
5. The modified `cmd` is used to spawn the process

**Custom parameters added to cmd are preserved but may be duplicated if also added by on_new_config.**

### 6.3 Initialization Failure

If cmd parameters prevent OmniSharp from starting, you won't get explicit error messages in `:LspInfo`. Instead:
- LSP will fail to attach
- Error messages appear in `:LspLog` (or `:tail ~/.local/state/nvim/lsp.log`)
- The process may spawn but immediately exit

---

## 7. Debugging cmd Parameter Issues

### 7.1 Checking the Actual cmd Being Used

In Neovim:
```vim
:LspInfo
```

Look for the "cmd:" line which shows the actual command being executed.

### 7.2 Checking LSP Logs

```vim
:LspLog
" Or check the log file directly
:!tail -f ~/.local/state/nvim/lsp.log
```

### 7.3 Manual Testing

Test OmniSharp directly in the terminal:

```bash
# Test with explicit path
/path/to/OmniSharp --languageserver --hostPID $$ 

# Or with dotnet
dotnet /path/to/OmniSharp.dll --languageserver --hostPID $$
```

If OmniSharp exits immediately, check:
- File permissions (execute bit)
- Dependencies (dotnet, required libraries)
- Solution file can be found from that directory

---

## 8. Best Practices for OmniSharp Configuration

### 8.1 Recommended Setup with Mason

```lua
require('lspconfig').omnisharp.setup {
  cmd = { 
    vim.fn.expand("~/.local/share/nvim/mason/bin/OmniSharp")
  },
  -- Let root_dir be auto-detected
  -- root_dir = util.root_pattern('*.sln', '*.csproj', 'omnisharp.json', 'function.json'),
  
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
  enable_import_completion = true,
  
  settings = {
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = nil,
    },
    MsBuild = {
      LoadProjectsOnDemand = nil,
    },
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
    },
  },
}
```

### 8.2 Recommended Setup with .NET Binary

```lua
local pid = vim.fn.getpid()
require('lspconfig').omnisharp.setup {
  cmd = { 
    "dotnet",
    vim.fn.expand("~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll")
  },
  -- Don't override on_new_config - let nvim-lspconfig handle it
  
  enable_roslyn_analyzers = true,
  organize_imports_on_format = true,
}
```

### 8.3 Do NOT Do

- Don't manually add `--languageserver`, `--hostPID`, `-z`, or other hard-coded args
- Don't try to pass the solution file with `-s` (let root_dir detection handle it)
- Don't use tilde (~) or environment variables without `vim.fn.expand()`
- Don't override `on_new_config` unless you understand what you're doing
- Don't use relative paths in cmd

---

## 9. Summary: How cmd Parameters Flow

```
User Configuration (init.lua)
    cmd = { "dotnet", "/path/to/OmniSharp.dll" }
           ↓
nvim-lspconfig reads config
           ↓
When LSP attaches, on_new_config is called
           ↓
on_new_config appends:
  --languageserver, --hostPID <pid>, -z,
  DotNet:enablePackageRestore=false, --encoding utf-8,
  + all settings as command arguments
           ↓
Final cmd passed to vim.fn.jobstart():
  { "dotnet", "/path/to/OmniSharp.dll", "--languageserver", 
    "--hostPID", "12345", "-z", ... }
           ↓
OmniSharp process spawned with these arguments
           ↓
OmniSharp searches root_dir for .sln/.csproj files
```

---

## 10. Key Takeaways

1. **nvim-lspconfig uses automatic parameter injection** through `on_new_config` - you shouldn't manually add flags that it adds automatically

2. **Solution file discovery is automatic** - nvim-lspconfig uses `root_dir` pattern matching, you don't need to specify `-s`

3. **Custom cmd parameters ARE passed through** - but may be duplicated if `on_new_config` also adds them

4. **Path must be absolute** - use `vim.fn.expand()` for dynamic paths, not tilde or environment variables

5. **Use `setup()` not `vim.lsp.config()`** - only `setup()` triggers the configuration callbacks

6. **Check `:LspInfo` and `:LspLog`** when debugging cmd parameter issues

7. **Let root_dir detection work** - it's designed to find your solution files automatically without explicit `-s` parameter

---

## References

- Official nvim-lspconfig OmniSharp config: `lua/lspconfig/configs/omnisharp.lua`
- nvim-lspconfig documentation: https://github.com/neovim/nvim-lspconfig
- OmniSharp Configuration Options: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
