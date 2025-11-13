# OmniSharp LSP - GitHub Issues and Known Problems Reference

**Purpose**: Catalog of known issues, their causes, and solutions
**Source**: Research from GitHub, Stack Overflow, and issue tracking
**Last Updated**: November 13, 2025

---

## Critical Issues

### Issue 1: lspconfig.setup() Called Multiple Times - MOST COMMON

**Source**: Observed in kickstart.nvim and many user configurations

**Problem**:
When `lspconfig.omnisharp.setup()` is called more than once in the same session, only the first call takes effect. Subsequent calls are silently ignored.

**Root Cause**:
nvim-lspconfig registers servers only on the first setup. The library checks if a server is already registered and skips re-registration on subsequent calls.

**How It Breaks Configuration**:
```lua
-- WRONG PATTERN - Two setup calls
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name])  -- FIRST CALL
    end,
  },
}

-- Later in your config...
require('lspconfig').omnisharp.setup({
  cmd = { ... },  -- IGNORED! Too late.
  settings = { ... },  -- IGNORED! Too late.
})
```

**Solution**:
Configure everything in the `servers` table and let the handler do the single setup:

```lua
local servers = {
  omnisharp = {
    cmd = { ... },
    settings = { ... },
  },
}

require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      require('lspconfig')[server_name].setup(server)  -- Only call once!
    end,
  },
}
-- No second omnisharp.setup() call!
```

**Why This Matters**:
The `on_new_config` function only runs during setup. If setup isn't called with your full config, on_new_config never flattens your settings into command-line arguments.

**Detection**:
```bash
grep -n "omnisharp.setup" ~/.config/nvim/init.lua
# Should return ONLY ONE line (in the handler)
```

---

### Issue 2: Mason Setup Called Twice - kickstart.nvim #1297

**GitHub**: https://github.com/nvim-lua/kickstart.nvim/issues/1297

**Problem**:
In kickstart.nvim, `mason.nvim` was being configured twice:
1. As a dependency of nvim-lspconfig (with config = true)
2. Explicitly via `require('mason').setup()` in nvim-lspconfig's config function

**Symptoms**:
- Configuration options are ignored
- PATH variable has duplicate entries
- Tools behave inconsistently

**Wrong Pattern**:
```lua
{
  'neovim/nvim-lspconfig',
  dependencies = {
    { 'williamboman/mason.nvim', config = true },  -- Setup 1
  },
  config = function()
    require('mason').setup { ... }  -- Setup 2 - WRONG!
    require('mason-lspconfig').setup { ... }
  end,
}
```

**Correct Pattern**:
```lua
{
  'neovim/nvim-lspconfig',
  dependencies = {
    { 'williamboman/mason.nvim', config = true },  -- Setup here
  },
  config = function()
    -- DON'T setup mason again!
    -- Just configure mason-lspconfig
    require('mason-lspconfig').setup { ... }
  end,
}
```

**Why**:
Mason must be in dependencies (to ensure load order) but should only be configured once.

---

### Issue 3: Multi-Workspace Not Supported - omnisharp-roslyn #909

**GitHub**: https://github.com/OmniSharp/omnisharp-roslyn/issues/909

**Problem**:
OmniSharp Roslyn has issues handling multiple workspaces in a single instance.

**Solution**:
The `on_new_config` function in nvim-lspconfig automatically disables this:

```lua
new_config.capabilities.workspace.workspaceFolders = false
```

**What It Means**:
Neovim won't advertise multi-workspace support to OmniSharp, preventing issues from attempting to use unsupported features.

**Impact**: None - this is transparent to users. OmniSharp still works normally.

---

### Issue 4: .editorconfig Settings Not Respected

**Sources**:
- omnisharp-vim #695
- nvim-lspconfig #4145

**Problem**:
Even with `EnableEditorConfigSupport = true`, OmniSharp doesn't pick up rules from `.editorconfig`.

**Causes**:
1. `.editorconfig` file doesn't exist in solution root
2. `.editorconfig` doesn't define the rules you're checking for
3. OmniSharp was started before .editorconfig was created
4. StyleCop.Analyzers package isn't installed in the project

**Verification**:
```bash
# Check if .editorconfig exists
ls /path/to/solution/.editorconfig

# Check if it has content
cat /path/to/solution/.editorconfig

# Check if StyleCop is referenced
grep StyleCop /path/to/project.csproj
```

**Solution**:
1. Create `.editorconfig` in solution root
2. Add StyleCop.Analyzers package to .csproj
3. Restart OmniSharp: `:LspRestart`

**Minimal .editorconfig Example**:
```ini
root = true

[*.cs]
# StyleCop rules
csharp_new_line_before_open_brace = all
csharp_new_line_before_else = true
csharp_new_line_before_catch = true
csharp_new_line_before_finally = true

# Formatting
indent_style = space
indent_size = 4
```

---

### Issue 5: Settings Empty in :LspInfo

**Problem**:
`:LspInfo` shows `settings: {}` even though you configured settings.

**Why This Happens**:
Settings are NOT stored in the LSP client info - they're flattened into command-line arguments by `on_new_config`.

**This Is Expected Behavior**:
Check the actual process instead:

```bash
ps aux | grep omnisharp | grep -v grep
```

Your settings will appear as command-line arguments like:
```
RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

**Real Problem Indicators**:
1. Your settings don't appear in process args → cmd is wrong
2. No `RoslynExtensionsOptions:*` args at all → settings weren't passed to setup()
3. Settings appear but OmniSharp doesn't respect them → project needs rebuild

---

## Configuration Issues

### Issue 6: cmd Format Incorrect

**Problem**:
Using incorrect format for the cmd array.

**Wrong Patterns**:
```lua
-- DON'T use the wrapper script directly
cmd = { vim.fn.expand('~/.local/share/nvim/mason/bin/OmniSharp') }

-- DON'T use just the binary name without path
cmd = { 'OmniSharp' }

-- DON'T forget dotnet
cmd = { '/path/to/OmniSharp.dll' }
```

**Correct Pattern**:
```lua
cmd = {
  'dotnet',  -- The dotnet runtime
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',  -- The DLL
  '-s', '/path/to/solution',  -- Solution path
  '-loglevel', 'Information',  -- Optional but recommended
}
```

**Why**:
- OmniSharp is a .NET application that must be run with `dotnet`
- The wrapper script at mason/bin/OmniSharp is just a convenience
- Direct DLL invocation is more reliable and transparent

---

### Issue 7: Case Sensitivity in Settings

**Problem**:
Using wrong case for setting names.

**Wrong (camelCase in Lua)**:
```lua
settings = {
  roslynExtensionsOptions = {  -- WRONG!
    enableAnalyzersSupport = true,  -- WRONG!
  },
}
```

**Correct (PascalCase in Lua)**:
```lua
settings = {
  RoslynExtensionsOptions = {  -- RIGHT!
    EnableAnalyzersSupport = true,  -- RIGHT!
  },
}
```

**Exception - JSON Files**:
If using `~/.omnisharp/omnisharp.json`, use camelCase:
```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  }
}
```

---

### Issue 8: Settings in Wrong Table

**Problem**:
Putting settings in the wrong place.

**Wrong**:
```lua
require('lspconfig').omnisharp.setup {
  RoslynExtensionsOptions = {  -- WRONG LOCATION!
    EnableAnalyzersSupport = true,
  },
}
```

**Correct**:
```lua
require('lspconfig').omnisharp.setup {
  settings = {  -- Correct location!
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
    },
  },
}
```

---

## Roslyn-Specific Issues

### Issue 9: EnableImportCompletion Slow on First Completion

**Source**: omnisharp-roslyn issue discussion

**Problem**:
The first completion request after opening a file is slow with `EnableImportCompletion = true`.

**Cause**:
OmniSharp scans for available imports on the first completion request.

**Solution**:
This is expected and improves on subsequent completions. You can disable it if it's problematic:

```lua
RoslynExtensionsOptions = {
  EnableImportCompletion = false,  -- Disable if too slow
}
```

---

### Issue 10: Analyzers Not Running on All Files

**Problem**:
Analyzers only run on files you've opened in the editor.

**Likely Cause**:
`AnalyzeOpenDocumentsOnly = true`

**Solution**:
```lua
RoslynExtensionsOptions = {
  AnalyzeOpenDocumentsOnly = false,  -- Analyze everything
}
```

**Tradeoff**:
Analyzing all files uses more CPU and memory but provides complete coverage.

---

### Issue 11: InlayHints Not Working

**Source**: omnisharp-roslyn issue #2550

**Problem**:
Inlay hints (type hints, parameter hints) don't appear.

**Causes**:
1. OmniSharp server capability issue (upstream)
2. Neovim version too old
3. Plugin configuration issue

**Workaround**:
Ensure you have a recent version of OmniSharp:
```bash
:Mason
# Find omnisharp, press 'u' to update to latest
```

---

## LSP Configuration Issues

### Issue 12: Root Directory Detection

**Problem**:
OmniSharp can't find your solution or project.

**Default Behavior**:
OmniSharp searches for:
1. `*.sln` (solution file)
2. `*.csproj` (project file)
3. `omnisharp.json` (configuration file)
4. `function.json` (Azure Functions)

In parent directories starting from the file being opened.

**Solution - Explicit Path**:
Use the `-s` flag:
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', '/absolute/path/to/your/solution',  -- Explicit!
  '-loglevel', 'Information',
}
```

**Solution - Custom Root Pattern**:
If default search doesn't work:
```lua
require('lspconfig').omnisharp.setup {
  root_dir = require('lspconfig.util').root_pattern('your-marker-file.txt'),
}
```

---

### Issue 13: Capabilities Not Properly Merged

**Problem**:
Some LSP capabilities aren't working (hover, completion, etc.).

**Cause**:
Capabilities not properly merged when setting up.

**Solution**:
Always use `tbl_deep_extend` to merge capabilities:

```lua
server.capabilities = vim.tbl_deep_extend(
  'force',
  {},
  capabilities,
  server.capabilities or {}
)
require('lspconfig')[server_name].setup(server)
```

This ensures client capabilities are combined with server capabilities correctly.

---

## Debugging Issues

### How to Get Detailed Logs

**Enable LSP logging**:
```bash
export NVIM_LOG_FILE=~/.cache/nvim/lsp.log
nvim
```

Then check the logs:
```bash
tail -100 ~/.cache/nvim/lsp.log
```

**Look for**:
- OmniSharp initialization messages
- Any error messages about configuration
- The actual command being executed

---

### How to Check What Arguments OmniSharp Receives

Most reliable method:
```bash
ps aux | grep omnisharp | grep -v grep
```

This shows the exact command line being used to start OmniSharp.

Expected to include:
```
dotnet /path/to/OmniSharp.dll -s /path/to/solution RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
```

---

### Clear Cache and Restart

When debugging configuration:
```bash
# Clear Lua bytecode cache (might have cached old config)
rm -rf ~/.cache/nvim/luac/

# Kill running OmniSharp
pkill -f omnisharp

# Clear swap files
rm -f ~/.local/state/nvim/swap/*.swp

# Start fresh
nvim
```

---

## Stack Overflow Solutions

### "How to use OmniSharp with Mason properly?"
**Link**: https://vi.stackexchange.com/questions/43830/

**Key Points**:
1. Must specify cmd with full path
2. root_dir detection can be tricky with WSL paths
3. omnisharp-extended plugin recommended for better navigation
4. Settings should be in the servers table, not in setup() call

---

### "Roslyn EditorConfig Support in Neovim"
**Link**: https://aaronbos.dev/posts/dotnet-roslyn-editorconfig-neovim

**Key Steps**:
1. Create `~/.omnisharp/omnisharp.json`
2. Enable RoslynExtensionsOptions and FormattingOptions
3. Create `.editorconfig` in solution root with rules
4. Restart OmniSharp

**Example omnisharp.json**:
```json
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true
  }
}
```

---

## Version-Specific Issues

### Neovim 0.11+ API Changes

**New API**:
```lua
vim.lsp.config('omnisharp', {
  settings = { ... },
})
vim.lsp.enable('omnisharp')
```

**Status**: Not yet reliable for OmniSharp. Stick with traditional `lspconfig.omnisharp.setup()`.

### Mason-lspconfig v2.0.0 Changes

**Released**: May 6, 2025

**Breaking Changes**:
- `handlers` setting removed
- `setup_handlers()` function removed
- Replaced by native `vim.lsp.config()` and `automatic_enable` setting

**Status**: If using old kickstart, may need to update

**Current Pattern (Still Works)**:
```lua
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup(servers[server_name] or {})
    end,
  },
}
```

---

## Common Workarounds

### If Settings Still Don't Apply

**Workaround 1: Use omnisharp.json File**
```bash
mkdir -p ~/.omnisharp
cat > ~/.omnisharp/omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "enableEditorConfigSupport": true,
    "organizeImports": true
  }
}
EOF
```

**Workaround 2: Explicit root_dir**
```lua
require('lspconfig').omnisharp.setup {
  root_dir = function()
    return vim.loop.cwd()
  end,
  cmd = { ... },
  settings = { ... },
}
```

**Workaround 3: Force Rebuild**
```bash
cd /path/to/solution
dotnet clean
dotnet restore --force-evaluate --no-cache
dotnet build
```

Then restart OmniSharp.

---

## Summary Table: Quick Issue Reference

| Issue | Symptom | Cause | Fix |
|-------|---------|-------|-----|
| Setup called twice | Settings ignored | Multiple setup() calls | One setup() in handler only |
| Mason setup twice | Config inconsistent | Two mason.setup() calls | Setup only in dependency |
| Settings empty in :LspInfo | UI shows {} | Expected behavior | Check `ps aux` instead |
| Analyzers not showing | No warnings appear | EnableAnalyzersSupport not set | Set to true in RoslynExtensionsOptions |
| .editorconfig ignored | Rules not applied | Missing file or StyleCop | Create file and rebuild |
| cmd format wrong | OmniSharp won't start | Missing 'dotnet' prefix | Use `{ 'dotnet', '/path/to/OmniSharp.dll', ... }` |
| Case sensitivity | Settings not applied | camelCase in Lua settings | Use PascalCase in Lua |
| Wrong table | Settings not passed | Not in `settings =` table | Move to settings: { ... } |
| Analyzers slow | First completion slow | EnableImportCompletion = true | Expected; improves after first use |
| Analyzer only on open | Incomplete coverage | AnalyzeOpenDocumentsOnly = true | Set to false |
| Root dir not found | Server can't start | Auto-detection fails | Use -s flag with explicit path |

---

## References

### GitHub Issues Linked
- neovim/nvim-lspconfig (OmniSharp configuration)
- nvim-lua/kickstart.nvim #1297 (Mason setup twice)
- OmniSharp/omnisharp-roslyn #909 (Multi-workspace)
- OmniSharp/omnisharp-roslyn #2550 (InlayHints)
- OmniSharp/omnisharp-roslyn #2667 (Roslynator)
- OmniSharp/omnisharp-roslyn #2573 (Import completion)

### Key Source Files
- `/path/to/nvim/lua/lspconfig/configs/omnisharp.lua` - The on_new_config function
- `~/.omnisharp/omnisharp.json` - User-level OmniSharp config
- `omnisharp.json` in solution root - Project-level OmniSharp config

### Documentation
- OmniSharp Configuration: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig

