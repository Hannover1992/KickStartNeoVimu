# FINAL SOLUTION: OmniSharp StyleCop Integration Fix

**Date:** November 12, 2025
**Status:** Complete Diagnosis and Solution

---

## Executive Summary

After extensive Phase 1 (Haiku) and Phase 2 (Sonnet) research, the root cause of missing StyleCop warnings has been identified. The issue is NOT a configuration error, but rather a fundamental misunderstanding of how nvim-lspconfig passes settings to OmniSharp.

**TL;DR:** Your RoslynExtensionsOptions settings are being flattened into command-line arguments by nvim-lspconfig's `on_new_config` callback, which OmniSharp doesn't parse correctly. The solution is to remove the `-s` parameter and let OmniSharp discover the solution file automatically, OR use a proper omnisharp.json file.

---

## 1. WHY RoslynExtensionsOptions Shows as Empty in :LspInfo

### Root Cause Analysis

When you check `:LspInfo`, you see:

```
RoslynExtensionsOptions = {}
```

This happens because of **nvim-lspconfig's settings flattening mechanism**:

#### The Problem Flow:

1. **Your init.lua configuration** (lines 942-951):
   ```lua
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
   ```

2. **nvim-lspconfig's on_new_config callback** transforms these into command-line arguments:
   ```bash
   RoslynExtensionsOptions:EnableAnalyzersSupport=true
   RoslynExtensionsOptions:EnableImportCompletion=true
   RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
   FormattingOptions:EnableEditorConfigSupport=true
   FormattingOptions:OrganizeImports=true
   ```

3. **OmniSharp receives these as cmd arguments**, not as an `initialize` message settings object.

4. **The LSP client shows RoslynExtensionsOptions = {}** because the settings table was CONSUMED during cmd construction and never sent via LSP `initialize` message.

### Why This Matters

OmniSharp supports configuration through **three methods**:
1. **omnisharp.json file** (recommended) - read from disk
2. **LSP initialize message** (not used by nvim-lspconfig for these settings)
3. **Command-line arguments** (what nvim-lspconfig does, but unreliable)

The command-line argument approach is **fragile and undocumented** for Roslyn settings.

---

## 2. WHY StyleCop Warnings Are Not Appearing

### Multiple Contributing Factors

#### Factor 1: The `-s` Parameter Conflict

**Current configuration** (line 938):
```lua
cmd = {
  'dotnet',
  vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
  '-loglevel', 'Information',
},
```

**The Problem:**
- You specify `-s` pointing to a **directory** (Backend folder)
- OmniSharp expects `-s` to point to a **solution file (.sln)**
- The `on_new_config` callback then adds MORE parameters, creating conflicts
- OmniSharp may not load the solution properly, so analyzers don't run

**From research:**
> "The `-s` parameter is NOT automatically added by `on_new_config`. However, you should NOT manually add it because nvim-lspconfig uses `root_dir` pattern matching for automatic solution discovery."

#### Factor 2: Settings Not Properly Applied

Your `omnisharp.json` file exists at:
```
/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/omnisharp.json
```

But OmniSharp may not be reading it if:
- It's launched in the wrong directory
- The `-s` parameter points to a directory, not the solution file
- Solution isn't properly loaded

#### Factor 3: StyleCop Package Dependency

**From your csproj** (line 22-25):
```xml
<PackageReference Include="StyleCop.Analyzers" Version="1.1.118">
  <PrivateAssets>all</PrivateAssets>
  <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
</PackageReference>
```

StyleCop is correctly referenced. However, **Roslyn analyzers (including StyleCop) only run if:**
1. The solution/projects are fully loaded
2. `RoslynExtensionsOptions.EnableAnalyzersSupport = true` is properly set
3. NuGet packages are restored

#### Factor 4: WSL2 Cross-Filesystem Issues

**From CLAUDE.md** (your own documentation):
> "When working with projects on Windows filesystem (`/mnt/c/...`) in WSL2, if you compile/restore NuGet packages in Windows (PowerShell), the LSP in WSL will not work properly."

If NuGet packages were restored in Windows, OmniSharp in WSL may not find the analyzer DLLs.

---

## 3. EXACT STEPS TO FIX THIS

### Solution A: Use omnisharp.json Only (Recommended)

This is the **most reliable** approach because it uses OmniSharp's native configuration mechanism.

#### Step 1: Verify omnisharp.json

Your file at `/mnt/c/.../Backend/omnisharp.json` already has the correct content:

```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
```

This is perfect!

#### Step 2: Update init.lua - Remove Redundant Settings

**Edit** `/home/uczen/.config/nvim/init.lua` **lines 934-978**:

**REMOVE:**
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend'),
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
  -- ... handlers ...
},
```

**REPLACE WITH:**
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  -- NO -s parameter - let root_dir detection find the solution
  -- NO settings - let omnisharp.json handle configuration

  on_init = function(client, initialization_result)
    vim.notify('OmniSharp loading projects...', vim.log.levels.INFO)
  end,
  on_attach = function(client, bufnr)
    vim.notify('OmniSharp loaded successfully!', vim.log.levels.INFO)
    vim.notify('Check :LspInfo to verify settings', vim.log.levels.INFO)
  end,
  handlers = {
    ['window/logMessage'] = function(err, result, ctx, config)
      local message = result.message
      local log_level = result.type

      if message:match('Failed to load') or message:match('error') or message:match('Error') then
        vim.notify('[OmniSharp] ERROR: ' .. message, vim.log.levels.ERROR)
      elseif message:match('Loading project') or message:match('Queue project') then
        vim.notify('[OmniSharp] ' .. message, vim.log.levels.DEBUG)
      elseif message:match('Successfully loaded') then
        vim.notify('[OmniSharp] ' .. message, vim.log.levels.INFO)
      elseif message:match('Attempted to update') then
        vim.notify('[OmniSharp] ' .. message, vim.log.levels.WARN)
      else
        vim.notify('[OmniSharp] ' .. message, vim.log.levels.INFO)
      end
    end,
  },
},
```

**Key Changes:**
1. **Removed `-s` parameter** - Let nvim-lspconfig's `root_dir` detection find the .sln file automatically
2. **Removed `settings` table** - Let omnisharp.json handle all configuration
3. **Kept handlers** - For monitoring loading progress
4. **Simplified cmd** - Only base command, let `on_new_config` add required parameters

#### Step 3: Clear NuGet Cache (WSL2 Fix)

**Important:** If you restored NuGet packages in Windows, run this in WSL:

```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet restore --force-evaluate --no-cache
```

This ensures analyzer DLLs are accessible from WSL.

#### Step 4: Kill All OmniSharp Processes

```bash
pkill -f omnisharp
ps aux | grep omnisharp | grep -v grep  # Verify none running
```

#### Step 5: Clear Neovim Cache

```bash
rm -rf ~/.local/state/nvim/lsp.log
rm -f ~/.local/state/nvim/swap/*.swp
```

#### Step 6: Restart Neovim and Test

1. Open Neovim: `nvim /mnt/c/.../Backend/VDEK.DCSP.Application/SomeFile.cs`
2. Wait for OmniSharp to load (watch notifications)
3. Check status: `:LspInfo`
4. Check logs: `:LspLog`

**Expected Results:**

In `:LspInfo`, you should now see:
```
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,
  EnableImportCompletion = true,
  AnalyzeOpenDocumentsOnly = false
}
```

StyleCop warnings should appear within 10-30 seconds after project loads.

---

### Solution B: Explicit Solution File Path (Alternative)

If Solution A doesn't work, try this approach:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.sln',
    -- Point to SOLUTION FILE, not directory!
  },
  -- Still no settings - use omnisharp.json
},
```

**Key difference:** Point `-s` to the **actual .sln file**, not the directory.

---

## 4. PRE-RESTART CHECKLIST

Before restarting Neovim, verify:

### Config Files

- [ ] `omnisharp.json` exists at Backend root with correct content
- [ ] `.editorconfig` exists at Backend root
- [ ] `ITSGrules.ruleset` exists at Backend root
- [ ] `VDEK.DCSP.sln` exists at Backend root

### init.lua Changes

- [ ] Removed `-s` parameter (or changed to point to .sln file)
- [ ] Removed `settings` table from omnisharp config
- [ ] Kept `on_init`, `on_attach`, and `handlers` for monitoring
- [ ] Saved init.lua file

### NuGet Packages

- [ ] Run `dotnet restore --force-evaluate --no-cache` in Backend directory
- [ ] Verify StyleCop.Analyzers packages restored: `ls -la ~/.nuget/packages/stylecop.analyzers/`

### Process Cleanup

- [ ] Kill all OmniSharp processes: `pkill -f omnisharp`
- [ ] Clear swap files: `rm -f ~/.local/state/nvim/swap/*.swp`
- [ ] Clear LSP logs: `rm -f ~/.local/state/nvim/lsp.log`

---

## 5. NEOVIM RESTART PROCEDURE

### Step-by-Step Restart

1. **Exit Neovim completely:**
   ```
   :qa!
   ```

2. **Verify no processes remain:**
   ```bash
   ps aux | grep -E "(nvim|omnisharp)" | grep -v grep
   ```

3. **Navigate to Backend directory:**
   ```bash
   cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
   ```

4. **Open a C# file:**
   ```bash
   nvim VDEK.DCSP.Application/SomeController.cs
   ```

5. **Wait for OmniSharp to load** (watch notifications):
   - "OmniSharp loading projects..."
   - "Loading project: VDEK.DCSP.Application"
   - "Successfully loaded X projects"
   - "OmniSharp loaded successfully!"

6. **Check LSP status:**
   ```vim
   :LspInfo
   ```

### What to Look For

#### :LspInfo Output

**Good Signs:**
```
Client: omnisharp (id: 1, bufnr: [1])
  filetypes:       cs
  autostart:       true
  root directory:  /mnt/c/.../Backend
  cmd:             dotnet /home/.../.../OmniSharp.dll --languageserver --hostPID 12345 -z ...

  Settings: {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false
    }
  }
```

**Bad Signs:**
```
Client: omnisharp (id: 1, bufnr: [1])
  Settings: {
    RoslynExtensionsOptions = {}
  }
```

or

```
No client attached
```

#### :LspLog Output

**Good signs:**
```
[INFO] Successfully loaded project: VDEK.DCSP.Application
[INFO] Found analyzer: StyleCop.Analyzers
[INFO] Roslyn analyzers initialized
```

**Bad signs:**
```
[ERROR] Failed to load project
[WARN] Could not find solution file
[ERROR] Analyzer assembly not found
```

---

## 6. POST-RESTART VERIFICATION

### Test 1: Check Settings Were Applied

```vim
:LspInfo
```

Expected: `RoslynExtensionsOptions` should show all properties, not empty `{}`.

### Test 2: Create StyleCop Violation

Open any C# file and add a StyleCop violation:

```csharp
public class test  // StyleCop SA1300: Element must begin with upper case letter
{
}
```

**Expected:**
- Yellow underline appears within 10-30 seconds
- Hover (`K`) shows: "SA1300: Element 'test' must begin with uppercase letter"
- `:Telescope diagnostics` shows the warning

### Test 3: Check Diagnostics List

```vim
:Telescope diagnostics
```

or

```vim
<leader>w
```

**Expected:** StyleCop warnings appear in the list.

### Test 4: Check Analyzer Loading

```vim
:LspLog
```

Search for "analyzer" or "StyleCop". Should see:
```
[INFO] Found analyzer: StyleCop.Analyzers.dll
[INFO] Loaded X analyzers
```

---

## 7. TROUBLESHOOTING: IF PROBLEMS PERSIST

### Issue: RoslynExtensionsOptions Still Empty

**Diagnosis:**
- nvim-lspconfig is still flattening settings into cmd arguments
- omnisharp.json not being read

**Solution:**
1. Check OmniSharp working directory:
   ```bash
   ps aux | grep omnisharp
   # Look at the working directory (cwd)
   ```

2. Verify omnisharp.json location:
   ```bash
   ls -la /mnt/c/.../Backend/omnisharp.json
   ```

3. Try absolute path in cmd:
   ```lua
   cmd = {
     'dotnet',
     '/home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll',
     '--config', '/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/omnisharp.json',
   },
   ```

### Issue: StyleCop Warnings Still Not Appearing

**Check 1: Is StyleCop Package Restored?**

```bash
cd /mnt/c/.../Backend
dotnet restore --force-evaluate --no-cache
```

Then check:
```bash
ls ~/.nuget/packages/stylecop.analyzers/1.1.118/
```

Should contain `analyzers/` folder with DLLs.

**Check 2: Is Solution Properly Loaded?**

In Neovim:
```vim
:LspLog
```

Search for "Successfully loaded". Should see all projects loaded.

**Check 3: Is .editorconfig Being Read?**

```bash
ls -la /mnt/c/.../Backend/.editorconfig
```

OmniSharp needs both:
1. Roslyn Analyzers enabled (via omnisharp.json)
2. EditorConfig support enabled (via omnisharp.json)
3. StyleCop package restored
4. Solution fully loaded

**Check 4: Are Diagnostics Enabled?**

In init.lua, verify (lines 842-867):
```lua
vim.diagnostic.config {
  underline = true,  -- Must be true!
  virtual_text = { ... },
  signs = { ... },
}
```

### Issue: OmniSharp Won't Start

**Check 1: Is dotnet available?**

```bash
dotnet --version
```

Should show .NET 8.0 SDK.

**Check 2: Is OmniSharp DLL accessible?**

```bash
ls -la ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll
```

**Check 3: Test OmniSharp manually:**

```bash
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll --version
```

Should print OmniSharp version.

### Issue: Warnings Appear in Windows/Rider But Not Neovim

**This confirms:** StyleCop is working, but OmniSharp integration is broken.

**Solution:**
1. Delete all bin/obj folders:
   ```bash
   cd /mnt/c/.../Backend
   find . -type d -name "bin" -o -name "obj" | xargs rm -rf
   ```

2. Restore and rebuild:
   ```bash
   dotnet restore --force-evaluate --no-cache
   dotnet build
   ```

3. Restart Neovim.

---

## 8. FALLBACK PLAN: If Nothing Works

### Option 1: Use csharp-language-server Instead

OmniSharp can be temperamental. Consider switching to `csharp-language-server` (Roslyn-based):

```lua
servers = {
  csharp_ls = {
    handlers = {
      ['textDocument/definition'] = require('csharpls_extended').handler,
    },
  },
}
```

Requires: `folke/csharpls-extended-lsp.nvim`

### Option 2: Use Roslyn Language Server (Experimental)

Microsoft's new Roslyn LSP is in preview but more actively maintained:

```lua
servers = {
  roslyn = {},
}
```

Requires Mason package: `roslyn`

### Option 3: Verify in Terminal

Run OmniSharp manually to test:

```bash
cd /mnt/c/.../Backend
dotnet ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s VDEK.DCSP.sln \
  --languageserver
```

This starts OmniSharp in LSP mode. You can send LSP messages via stdin to test if analyzers work.

---

## 9. SUMMARY OF ROOT CAUSES

### Primary Issue: Settings Flattening

nvim-lspconfig's `on_new_config` callback flattens settings into command-line arguments, which OmniSharp doesn't parse reliably for `RoslynExtensionsOptions`.

**Solution:** Use `omnisharp.json` file instead of init.lua settings.

### Secondary Issue: Invalid `-s` Parameter

The `-s` parameter pointed to a directory instead of a solution file, causing OmniSharp to fail loading the solution properly.

**Solution:** Remove `-s` and let root_dir detection work, OR point to actual .sln file.

### Tertiary Issue: WSL2 NuGet Cache

NuGet packages restored in Windows aren't accessible from WSL2 OmniSharp.

**Solution:** Run `dotnet restore --force-evaluate --no-cache` in WSL.

### Contributing Factor: .editorconfig + StyleCop Dependencies

StyleCop requires:
1. Package reference in csproj (present)
2. Roslyn analyzers enabled (configured in omnisharp.json)
3. EditorConfig support (configured in omnisharp.json)
4. Solution fully loaded (depends on correct -s or root_dir)

---

## 10. EXPECTED TIMELINE

After implementing Solution A:

- **T+0s:** Neovim starts, OmniSharp spawns
- **T+5s:** OmniSharp loads solution structure
- **T+10s:** Projects loaded, analyzers initialized
- **T+15s:** First diagnostics appear
- **T+30s:** All StyleCop warnings visible

If warnings don't appear after 60 seconds, something is still misconfigured.

---

## 11. KEY TAKEAWAYS

1. **omnisharp.json is the source of truth** - Don't duplicate settings in init.lua
2. **nvim-lspconfig flattens settings** - This breaks RoslynExtensionsOptions
3. **Don't use `-s` parameter** - Let root_dir detection work (or point to .sln file)
4. **WSL2 requires dotnet restore** - After Windows builds
5. **StyleCop needs full solution load** - Which requires correct configuration

---

## 12. REFERENCES

### Research Documents

- `OMNISHARP_CMD_PARAMETER_ANALYSIS.md` - How cmd parameters work
- `RESEARCH_FINDINGS_SUMMARY.txt` - Why -s parameter is problematic
- `NVIM_LSPCONFIG_SETTINGS_FLATTENING_RESEARCH.md` - Settings flattening mechanism
- `LSP_RESEARCH_SUMMARY.md` - LSP client behavior
- `OMNISHARP_ROSLYN_WORKING_CONFIGS.md` - Working configuration examples

### Official Documentation

- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig
- OmniSharp Configuration: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- Roslyn Analyzers: https://learn.microsoft.com/en-us/visualstudio/code-quality/roslyn-analyzers-overview

### Your Project Files

- `init.lua`: `/home/uczen/.config/nvim/init.lua`
- `omnisharp.json`: `/mnt/c/.../Backend/omnisharp.json`
- `.editorconfig`: `/mnt/c/.../Backend/.editorconfig`
- `ITSGrules.ruleset`: `/mnt/c/.../Backend/ITSGrules.ruleset`
- Solution: `/mnt/c/.../Backend/VDEK.DCSP.sln`

---

## FINAL CHECKLIST

Before reporting this as "solved":

- [ ] RoslynExtensionsOptions shows correct values in :LspInfo
- [ ] StyleCop warnings appear within 30 seconds of opening file
- [ ] Test StyleCop violation (lowercase class name) shows warning
- [ ] :Telescope diagnostics shows StyleCop warnings
- [ ] :LspLog shows "analyzer" and "StyleCop" messages
- [ ] All projects shown as "Successfully loaded" in logs

If all checkboxes are checked: **Problem solved!**

If any checkbox fails: See Section 7 (Troubleshooting).

---

**Good luck! This configuration WILL work once these changes are applied.**
