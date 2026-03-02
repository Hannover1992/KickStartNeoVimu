# OmniSharp Initialization - Quick Fix Guide

## TL;DR - The Problem

**Symptom**: `:LspInfo` shows "No active clients" even though OmniSharp process is running.

**Root Cause**: OmniSharp never completes LSP initialization because NuGet packages are missing (AWSSDK.S3). The entire 45-project solution fails to load, OmniSharp gets stuck retrying, and never sends the "initialize" response to Neovim.

**Evidence**:
- 702 queued notifications ("before initialization was completed")
- 45+ projects showing "not loaded" errors
- Missing package: AWSSDK.S3 version 3.7.415.2

---

## The Fix (3 Steps)

### Step 1: Restore NuGet Packages
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src
dotnet restore --force-evaluate --no-cache
```

**Expected output**:
```
Restore succeeded with N warning(s) in X.Xs
```

**If restore fails**: Fix build errors before proceeding.

### Step 2: Verify Solution Builds
```bash
dotnet build CenCoCo.sln
```

**Expected output**:
```
Build succeeded
```

**If build fails**: OmniSharp will fail too. Fix build issues first.

### Step 3: Clean Restart Neovim
```bash
# Kill stale processes
pkill -f omnisharp

# Clear caches
rm -rf ~/.cache/nvim/luac/

# Start Neovim
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/Core/CenCoCo.Core.API/Program.cs
```

---

## Verification

### 1. Check LSP Client Attached
```vim
:LspInfo
```

**Expected (SUCCESS)**:
```
vim.lsp: Active Clients
 Client: omnisharp (id: 1, bufnr: [1])
   filetypes:       cs
   cmd:             { "dotnet", "/path/to/OmniSharp.dll", "-s", "/path/to/solution", ... }
```

**If still "No active clients"**: Check next steps.

### 2. Check Process Command Line
```bash
ps aux | grep omnisharp | grep -v grep
```

**Expected (SUCCESS)**:
```
uczen ... dotnet .../OmniSharp.dll -s /mnt/c/.../cencoco/src -loglevel Information -z ...
  RoslynExtensionsOptions:EnableAnalyzersSupport=true
  FormattingOptions:EnableEditorConfigSupport=true
```

**Verify**:
- ✓ `-s` parameter present with solution path
- ✓ Settings flattened to CLI args
- ✓ `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

### 3. Monitor Initialization Progress
```bash
tail -f ~/.local/state/nvim/lsp.log | grep -E "initialize|Project.*loaded"
```

**Expected timeline**:
- T+0s: "initialize" request sent
- T+5-15s: Projects start loading
- T+15-60s: "initialize" result received
- **Total**: 15-60 seconds for 45-project solution

**If taking longer than 2 minutes**: Check for errors in log.

---

## Understanding the Timeline

### Normal Initialization (After Fix)
```
0s    - User opens C# file
1s    - Neovim starts OmniSharp
2s    - OmniSharp begins loading solution
15s   - OmniSharp sends "initialize" response
16s   - LSP client attaches (SUCCESS!)
```

### Failed Initialization (Before Fix)
```
0s     - User opens C# file
1s     - Neovim starts OmniSharp
2s     - OmniSharp begins loading solution
30s    - NuGet package error (AWSSDK.S3)
60s    - Dependency cascade: 45 projects fail
300s   - Still retrying project loads
∞      - NEVER sends "initialize" response
```

---

## Why This Happens (WSL2 Specific)

**The WSL2 NuGet Cache Problem**:

1. You run `dotnet restore` in **Windows PowerShell**
2. NuGet packages cached in: `C:\Users\Administrator\.nuget\packages\`
3. OmniSharp runs in **WSL2 Linux**
4. OmniSharp looks in: `~/.nuget/packages/` (different cache!)
5. Packages not found → project loading fails

**Solution**: Always run `dotnet restore` in WSL where OmniSharp runs.

---

## Preventing Future Issues

### 1. Add to Your Workflow
```bash
# Before opening Neovim each day:
cd /mnt/c/.../cencoco/src
dotnet restore --force-evaluate --no-cache
```

### 2. Create Alias
Add to `~/.bashrc` or `~/.zshrc`:
```bash
alias fix-omnisharp='cd /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src && dotnet restore --force-evaluate --no-cache && pkill -f omnisharp'
```

Then just run: `fix-omnisharp`

### 3. Add Timeout to Configuration
Edit `/home/uczen/.config/nvim/init.lua` (lines 704-724):
```lua
omnisharp = {
  cmd = { ... },
  settings = { ... },

  -- Add timeout (60 seconds)
  timeout = 60000,

  -- Add success notification
  on_init = function(client, initialization_result)
    vim.notify('OmniSharp ready!', vim.log.levels.INFO)
  end,

  -- Add failure notification
  on_error = function(err)
    vim.notify('OmniSharp error: ' .. tostring(err), vim.log.levels.ERROR)
  end,
}
```

---

## If Still Not Working

### Check 1: Verify NuGet Packages Exist
```bash
ls ~/.nuget/packages/awssdk.s3/3.7.415.2/
```

**If directory not found**: Run `dotnet restore` again.

### Check 2: Check LSP Log for Errors
```bash
tail -100 ~/.local/state/nvim/lsp.log | grep -i "error\|fail"
```

Look for:
- "Package ... was not found"
- "Attempted to update project that is not loaded"
- "Failed to load project"

### Check 3: Try Smaller Solution
Edit `init.lua` to use sliced solution:
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/.../cencoco/src/CenCoCo_Sliced.sln'),  -- Smaller!
    '-loglevel', 'Information',
  },
  settings = { ... },
}
```

### Check 4: Test Single Project
Load just one project to isolate issue:
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/.../Core.API/Core.API.csproj'),  -- Single project!
    '-loglevel', 'Information',
  },
  settings = { ... },
}
```

If single project works but full solution doesn't: Solution too large or has dependency issues.

---

## Key Metrics for Success

| Metric | Expected | Your Value |
|--------|----------|------------|
| `dotnet restore` time | < 30s | ___ |
| `dotnet build` result | SUCCESS | ___ |
| OmniSharp process running | YES | ___ |
| `:LspInfo` shows client | YES | ___ |
| Initialization time | 15-60s | ___ |
| Settings in cmd line | YES | ___ |

**If all metrics pass**: OmniSharp is working correctly!

---

## Emergency Fallback: Minimal Working Config

If nothing works, use this minimal config for basic LSP:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
  },
  -- No -s parameter (OmniSharp finds .csproj in current directory)
  -- No settings (minimal functionality)
}
```

Open Neovim in project directory:
```bash
cd /mnt/c/.../cencoco/src/Core/CenCoCo.Core.API
nvim Program.cs
```

**Pros**: Usually works immediately
**Cons**: No cross-project features, no analyzers

---

## Summary Checklist

- [ ] Run `dotnet restore --force-evaluate --no-cache` in WSL
- [ ] Verify `dotnet build` succeeds
- [ ] Kill stale OmniSharp processes
- [ ] Clear Neovim caches
- [ ] Start Neovim and open C# file
- [ ] Check `:LspInfo` shows active client
- [ ] Verify LSP features work (gd, grr, K)
- [ ] Check StyleCop warnings appear

**If all checked**: You're done! OmniSharp is working correctly.

---

**Document Status**: Ready for User Testing
**Related Document**: OMNISHARP_INITIALIZATION_ANALYSIS.md (detailed deep-dive)
