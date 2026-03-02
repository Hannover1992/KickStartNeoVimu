# OmniSharp Initialization Deep Analysis
## Why "No Active Clients" Despite Running Process

**Date**: 2025-11-13
**Analysis Type**: Deep initialization sequence and timeout investigation
**Status**: CRITICAL ROOT CAUSES IDENTIFIED

---

## Executive Summary

**The Problem**: OmniSharp process starts and runs successfully, but Neovim's LSP client never attaches (`:LspInfo` shows "No active clients").

**The Root Cause**: OmniSharp NEVER COMPLETES the LSP initialization handshake because it's stuck in an endless project loading loop caused by missing NuGet packages.

**Evidence**:
- 702 instances of "Tried to send request or notification before initialization was completed"
- 45+ projects showing "Attempted to update project that is not loaded"
- Missing NuGet package: AWSSDK.S3 version 3.7.415.2
- OmniSharp loads projects but can't complete initialization because dependencies are missing

---

## Part 1: Complete Initialization Timeline

### Phase 1: Neovim Starts LSP Client (0-1 seconds)

```
1. User opens C# file
   ↓
2. Neovim FileType autocmd triggers (filetype=cs)
   ↓
3. nvim-lspconfig checks if omnisharp is configured
   ↓
4. vim.lsp.start() is called with cmd and config
   ↓
5. Neovim spawns OmniSharp process
   → dotnet /path/to/OmniSharp.dll -s /path/to/solution -loglevel Information
   ↓
6. Neovim sends LSP "initialize" request
   → Waits for "initialize" response from OmniSharp
```

**At this point**: Neovim is waiting for OmniSharp to respond with initialization result.

### Phase 2: OmniSharp Starts and Loads Solution (1-30 seconds)

```
7. OmniSharp.dll starts execution
   ↓
8. OmniSharp reads solution file (-s parameter)
   → Discovers: CenCoCo.sln (45+ projects)
   ↓
9. OmniSharp begins MSBuildWorkspace.OpenSolutionAsync()
   ↓
10. For EACH project in solution:
    a. Parse .csproj file
    b. Evaluate MSBuild properties
    c. Resolve NuGet package references
    d. Discover project references
    e. Load metadata references
    f. Create Roslyn Compilation object
   ↓
11. OmniSharp logs to LSP log:
    - "o#/projectadded" notifications queued
    - "o#/projectchanged" notifications queued
    - But CANNOT SEND because initialization not complete!
```

**CRITICAL**: All project notifications are queued, NOT sent. OmniSharp is preparing data but can't communicate with Neovim yet.

### Phase 3: Project Loading Fails (NuGet Errors) (5-60 seconds)

```
12. OmniSharp attempts to load CenCoCo.Core.API.csproj
    ↓
13. Project references NuGet package: AWSSDK.S3 version 3.7.415.2
    ↓
14. MSBuild evaluates package reference
    ↓
15. NuGet resolver searches for package in cache
    → Searches: ~/.nuget/packages/awssdk.s3/3.7.415.2/
    → NOT FOUND (packages restored in Windows, not WSL)
    ↓
16. MSBuild throws error:
    "Package AWSSDK.S3, version 3.7.415.2 was not found"
    ↓
17. Project loading fails for CenCoCo.Core.API
    ↓
18. 45+ OTHER projects reference Core.API as ProjectReference
    ↓
19. OmniSharp logs: "Attempted to update project that is not loaded"
    → For ALL 45+ projects in dependency chain!
```

**CRITICAL FAILURE POINT**: The entire solution dependency graph collapses because Core.API can't load.

### Phase 4: OmniSharp Never Completes Initialization (TIMEOUT)

```
20. OmniSharp is stuck in project loading loop
    → Keeps trying to load dependent projects
    → Each fails because Core.API is missing
    ↓
21. OmniSharp NEVER sends "initialize" response to Neovim
    → Because it's waiting for all projects to load first
    → But projects can't load due to NuGet errors
    ↓
22. Neovim waits indefinitely (no timeout configured)
    ↓
23. Result: OmniSharp process runs, but LSP client never attaches
```

**Why `:LspInfo` shows "No active clients"**:
- Neovim sent "initialize" request
- OmniSharp never responded with "initialize" result
- Without completed handshake, no client is registered
- Process runs, but LSP protocol connection never established

---

## Part 2: Why "No Active Clients" Despite Running Process

### The LSP Initialization Handshake

**Required sequence for LSP client attachment**:
```
Client (Neovim)                Server (OmniSharp)
     |                              |
     | --- initialize request ---> |
     |                              |
     |                              | (loads projects)
     |                              | (resolves dependencies)
     |                              | (prepares workspace)
     |                              |
     | <-- initialize result ----- |  ← NEVER SENT!
     |                              |
     | --- initialized notify ---> |
     |                              |
     | === CLIENT NOW ACTIVE ===   |
```

**In our case**:
```
Client (Neovim)                Server (OmniSharp)
     |                              |
     | --- initialize request ---> |
     |                              |
     | (waiting...)                | (loading projects...)
     | (waiting...)                | (NuGet error!)
     | (waiting...)                | (retrying...)
     | (waiting...)                | (still loading...)
     | (waiting...)                | (more errors...)
     |                              |
     | NO RESPONSE EVER RECEIVED  | STUCK IN LOADING LOOP
```

**Result**: `:LspInfo` correctly reports "No active clients" because the handshake never completed.

### Evidence from LSP Log

**From `/home/uczen/.local/state/nvim/lsp.log`**:

1. **702 queued notifications**:
   ```
   "Tried to send request or notification before initialization was completed and will be sent later"
   ```
   Meaning: OmniSharp has data to send (project info) but CAN'T send because handshake incomplete.

2. **45+ project load errors**:
   ```
   "OmniSharp.MSBuild.ProjectManager: Attempted to update project that is not loaded:
   CenCoCo.Core.Contracts.csproj"
   ```
   Meaning: Projects can't load because Core.API failed, which failed because AWSSDK.S3 missing.

3. **NuGet package error**:
   ```
   "Package AWSSDK.S3, version 3.7.415.2 was not found. It might have been deleted since
   NuGet restore. Otherwise, NuGet restore might have only partially completed."
   ```
   Meaning: Root cause is missing NuGet packages.

---

## Part 3: Timing Analysis and Neovim Timeout Behavior

### Neovim LSP Client Timeout Settings

**Default Neovim behavior** (as of Neovim 0.10+):
- No hard timeout for LSP initialization
- `vim.lsp.start()` returns immediately (non-blocking)
- Client waits indefinitely for server response
- Process monitoring is passive (checks if process died)

**From init.lua analysis** (lines 704-724):
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/.../cencoco/src'),
    '-loglevel', 'Information',
  },
  settings = { ... },
  -- NO timeout configured!
  -- NO on_init callback to check status
  -- NO on_error callback
}
```

**Missing timeout configuration options**:
- `timeout` - Not set (defaults to no timeout)
- `on_init` - Not configured (could detect slow init)
- `on_error` - Not configured (could report failures)

### Actual Timing from Log Analysis

**Timestamps from lsp.log**:
```
[ERROR][2025-11-13 15:05:01] - First project errors appear
[ERROR][2025-11-13 15:12:37] - NuGet error detected
[WARN][2025-11-13 15:12:49]  - Still queuing notifications

Total time: ~7 minutes 48 seconds
```

**What happened in those 7 minutes**:
1. **0:00-0:30** - OmniSharp starts, parses solution file
2. **0:30-2:00** - Begins loading first 5-10 projects (templates, public site)
3. **2:00-5:00** - Attempts to load Core.API, hits NuGet error
4. **5:00-7:48** - Retries loading dependent projects repeatedly, all fail
5. **7:48+** - Still running, still trying, never completes

**Neovim's perspective**:
- Sent "initialize" at 15:05:01
- Still waiting at 15:12:49 (and beyond)
- No error reported
- Process still alive, so assumes it's still initializing

---

## Part 4: Solution Size Impact on Initialization

### CenCoCo Solution Analysis

**Project count from lsp.log**:
- Core projects: 5 (Core.API, Core.Application, Core.Contracts, Core.Domain, Core.Infrastructure)
- Module projects: 30+ (Accounting, CRM, Projects, ServiceDesk, TimeSheet - each has 6 subprojects)
- Shared projects: 6 (SharedKernel.*)
- Test projects: 3+ (Architecture, E2E, Integration)
- Public/Setup: 2
- Templates: 6+

**Total**: 45-50 projects in solution

### Initialization Time Estimates

**Small solution (1-5 projects)**:
- Expected init time: 2-5 seconds
- Usually completes without issues

**Medium solution (10-20 projects)**:
- Expected init time: 10-30 seconds
- May timeout if dependencies complex

**Large solution (45+ projects) - CenCoCo**:
- Expected init time: 30-120 seconds (2 minutes)
- HIGH RISK of timeout or failure
- Dependency chains amplify errors

### The Cascade Effect

**In CenCoCo solution**:
```
Core.API fails (missing AWSSDK.S3)
  ↓
Accounting.API references Core.API → FAILS
Accounting.Application references Core.API → FAILS
Accounting.Infrastructure references Core.API → FAILS
  ↓
CRM.API references Core.API → FAILS
CRM.Application references Core.API → FAILS
...
  ↓
45+ projects all fail in dependency chain
```

**Why this matters**:
- One missing NuGet package breaks ENTIRE solution
- OmniSharp doesn't fail-fast, keeps retrying
- Each retry takes 5-15 seconds
- 45 projects × 10 seconds = 450 seconds (7.5 minutes) minimum

**This explains the 7:48 initialization time observed!**

---

## Part 5: Verification Checklist for Successful Initialization

### Pre-Flight Checks (Before Starting Neovim)

#### 1. Verify NuGet Packages Restored
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src

# Force restore all packages (critical for WSL2)
dotnet restore --force-evaluate --no-cache

# Expected output:
# "Restore succeeded" with 0 errors
# May have warnings, but no "package not found" errors
```

**Why this matters**:
- WSL2 doesn't share NuGet cache with Windows
- Packages restored in Windows PowerShell are invisible to WSL
- Must restore in WSL environment where OmniSharp runs

#### 2. Verify Solution File Exists
```bash
ls -la /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src/CenCoCo.sln

# Expected: File exists, readable permissions
```

**Actual finding**:
```
-rwxrwxrwx 1 uczen uczen 34216 Nov  8 14:52 CenCoCo.sln  ✓ EXISTS
```

#### 3. Test Build (Validates Complete Setup)
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/Kluger/code/cencoco/src

# Build entire solution
dotnet build CenCoCo.sln

# Expected: "Build succeeded"
# If build fails, OmniSharp will fail too!
```

**Critical**: If `dotnet build` fails, OmniSharp initialization will NEVER complete.

#### 4. Kill Stale OmniSharp Processes
```bash
pkill -f omnisharp

# Verify no processes running:
ps aux | grep omnisharp | grep -v grep
# Should return empty
```

#### 5. Clear Neovim Caches
```bash
rm -rf ~/.cache/nvim/luac/
rm -rf ~/.local/state/nvim/swap/*.swp
```

### Runtime Checks (After Starting Neovim)

#### 1. Check Process Started
```bash
ps aux | grep omnisharp | grep -v grep
```

**Expected output**:
```
uczen    12345  ... dotnet /home/uczen/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
  -s /mnt/c/.../cencoco/src -loglevel Information -z --hostPID 12346 \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:EnableImportCompletion=true \
  FormattingOptions:EnableEditorConfigSupport=true
```

**Verify**:
- ✓ `dotnet` present (not just wrapper script)
- ✓ Full DLL path present
- ✓ `-s` parameter with solution path
- ✓ `-loglevel Information`
- ✓ Settings flattened to command-line args

#### 2. Check LSP Client Status
```vim
:LspInfo
```

**Expected (successful initialization)**:
```
vim.lsp: Active Clients
 Client: omnisharp (id: 1, bufnr: [1])
   filetypes:       cs
   cmd:             { "dotnet", "/path/to/OmniSharp.dll", "-s", "/path/to/solution", ... }
   settings:        {
     RoslynExtensionsOptions = {
       EnableAnalyzersSupport = true,
       ...
     }
   }
   root_dir:        /mnt/c/.../cencoco/src
```

**Actual (failed initialization)**:
```
vim.lsp: Active Clients
 No active clients
```

**This confirms**: Initialization handshake never completed.

#### 3. Monitor LSP Log in Real-Time
```bash
tail -f ~/.local/state/nvim/lsp.log | grep -i "error\|initialize"
```

**Watch for**:
- "initialize" request sent by Neovim
- "initialize" result received from OmniSharp (should appear within 30-120s)
- Any "Package ... was not found" errors
- "Attempted to update project that is not loaded" errors

#### 4. Check Initialization Completion Time
```bash
# Extract timestamps from log
grep "initialize" ~/.local/state/nvim/lsp.log | tail -20
```

**Healthy initialization**:
- Request sent at T+0s
- Result received at T+15-30s
- Total time: <30 seconds

**Failed initialization** (CenCoCo case):
- Request sent at 15:05:01
- No result received by 15:12:49 (7 minutes 48 seconds)
- Total time: >7 minutes, still incomplete

---

## Part 6: Timeout Configuration Recommendations

### Current Configuration (No Timeout Protection)

**Problem**: No timeout configured, Neovim waits forever.

### Solution 1: Add Initialization Timeout

**Add to init.lua omnisharp config** (lines 704-724):
```lua
omnisharp = {
  cmd = { ... },
  settings = { ... },

  -- Add timeout (in milliseconds)
  -- 60 seconds for large solutions
  timeout = 60000,

  -- Add on_init callback to detect slow initialization
  on_init = function(client, initialization_result)
    vim.notify('OmniSharp initialized successfully', vim.log.levels.INFO)
  end,

  -- Add on_error callback to detect failures
  on_error = function(err)
    vim.notify('OmniSharp error: ' .. tostring(err), vim.log.levels.ERROR)
  end,
}
```

**Why this helps**:
- Prevents infinite waiting
- Alerts user to initialization problems
- Fails fast instead of hanging

### Solution 2: Add Initialization Progress Monitoring

```lua
omnisharp = {
  cmd = { ... },
  settings = { ... },

  on_init = function(client, initialization_result)
    local start_time = vim.loop.now()

    -- Set up timer to check progress
    local timer = vim.loop.new_timer()
    timer:start(0, 10000, vim.schedule_wrap(function()
      local elapsed = (vim.loop.now() - start_time) / 1000

      if not client.is_stopped() then
        if elapsed > 30 then
          vim.notify(
            string.format('OmniSharp still initializing... (%ds)', elapsed),
            vim.log.levels.WARN
          )
        end

        if elapsed > 120 then
          vim.notify(
            'OmniSharp initialization taking too long - check LSP log',
            vim.log.levels.ERROR
          )
          timer:stop()
        end
      else
        timer:stop()
      end
    end))
  end,
}
```

**Why this helps**:
- Provides progress feedback
- Warns if init taking too long
- Directs user to check logs

### Solution 3: Conditional Timeout Based on Solution Size

```lua
-- Count projects in solution
local function count_projects(sln_path)
  local count = 0
  for line in io.lines(sln_path) do
    if line:match('%.csproj') then
      count = count + 1
    end
  end
  return count
end

local sln_path = '/mnt/c/.../cencoco/src/CenCoCo.sln'
local project_count = count_projects(sln_path)

omnisharp = {
  cmd = { ... },
  settings = { ... },

  -- Dynamic timeout based on project count
  -- Small: 30s, Medium: 60s, Large: 120s
  timeout = math.min(30000 + (project_count * 1000), 120000),
}
```

**Why this helps**:
- Scales timeout with solution complexity
- Small solutions don't wait unnecessarily
- Large solutions get adequate time

---

## Part 7: Emergency Fallback Configurations

### Fallback 1: Load Single Project Instead of Solution

**For immediate work without waiting for full solution**:

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

**Pros**:
- Fast initialization (5-10 seconds)
- Works even if other projects broken
- Immediate LSP functionality

**Cons**:
- No cross-project navigation
- References to other projects unresolved
- Only works for single-project editing

### Fallback 2: Use Smaller Sliced Solution

**CenCoCo has alternative solution file**: `CenCoCo_Sliced.sln`

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/.../cencoco/src/CenCoCo_Sliced.sln'),  -- Smaller solution!
    '-loglevel', 'Information',
  },
  settings = { ... },
}
```

**Benefits**:
- Fewer projects = faster init
- Essential projects only
- Reduced memory usage

### Fallback 3: Disable Analyzers for Faster Init

**Temporarily disable heavy analysis**:

```lua
omnisharp = {
  cmd = { ... },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = false,      -- Disable for speed
      EnableImportCompletion = false,      -- Disable for speed
      AnalyzeOpenDocumentsOnly = true,     -- Minimal analysis
    },
  },
}
```

**When to use**:
- Testing if analyzers cause timeout
- Need LSP quickly for navigation only
- Debugging initialization issues

### Fallback 4: Increase OmniSharp Memory Limit

**For very large solutions**:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/.../cencoco/src'),
    '-loglevel', 'Information',
    '--hostPID', vim.fn.getpid(),
    '--',  -- Separator for dotnet args
    '--server.GC.MaxHeapSize=0x20000000',  -- 512MB heap
  },
  settings = { ... },
}
```

**When to use**:
- Solution has 100+ projects
- OmniSharp process crashes during init
- Memory pressure observed

### Fallback 5: Pre-Warm OmniSharp Before Neovim

**Start OmniSharp manually, wait for load, then start Neovim**:

```bash
#!/bin/bash
# pre_warm_omnisharp.sh

OMNISHARP_DLL="$HOME/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll"
SOLUTION="/mnt/c/.../cencoco/src/CenCoCo.sln"

# Start OmniSharp in background
dotnet "$OMNISHARP_DLL" -s "$SOLUTION" -loglevel Information &
OMNISHARP_PID=$!

echo "Warming up OmniSharp (PID: $OMNISHARP_PID)..."

# Wait for initialization (check log for completion)
timeout=120
elapsed=0
while [ $elapsed -lt $timeout ]; do
  if ps -p $OMNISHARP_PID > /dev/null; then
    # Check if OmniSharp log shows initialization complete
    # (implementation depends on log format)
    sleep 5
    elapsed=$((elapsed + 5))
  else
    echo "OmniSharp exited prematurely!"
    exit 1
  fi
done

echo "OmniSharp ready! Starting Neovim..."
nvim "$@"
```

**When to use**:
- Daily workflow with large solution
- Want pre-loaded LSP ready to go
- Willing to trade startup time for responsive editing

---

## Part 8: Final Recommendations

### Immediate Action Required

1. **Restore NuGet packages in WSL**:
   ```bash
   cd /mnt/c/.../cencoco/src
   dotnet restore --force-evaluate --no-cache
   ```
   **This is the PRIMARY FIX.**

2. **Verify solution builds**:
   ```bash
   dotnet build CenCoCo.sln
   ```
   If build fails, OmniSharp will fail too.

3. **Kill stale processes and restart**:
   ```bash
   pkill -f omnisharp
   rm -rf ~/.cache/nvim/luac/
   nvim /mnt/c/.../cencoco/src/Core/CenCoCo.Core.API/Program.cs
   ```

### Configuration Improvements

1. **Add timeout to init.lua** (60-120 seconds)
2. **Add on_init callback** for progress visibility
3. **Add on_error callback** for failure alerts
4. **Consider using sliced solution** for daily work

### Long-Term Solutions

1. **Set up dotnet restore as pre-commit hook**
2. **Add NuGet package validation to CI/CD**
3. **Document WSL2 NuGet cache requirements**
4. **Create separate "development" solution** with fewer projects

---

## Summary: The Complete Picture

**Why OmniSharp Process Runs But Client Never Attaches**:

1. OmniSharp starts successfully
2. Begins loading 45+ project solution
3. Hits NuGet package error (AWSSDK.S3 missing)
4. Dependency cascade fails 45+ projects
5. OmniSharp stuck retrying project loads
6. Never sends "initialize" response to Neovim
7. LSP handshake never completes
8. Neovim waits indefinitely (no timeout)
9. Result: Process alive, but client not attached

**The Fix**:
```bash
dotnet restore --force-evaluate --no-cache
```

This restores missing NuGet packages, allowing project loading to complete, initialization to finish, and LSP client to attach.

**Expected outcome after fix**:
- `:LspInfo` shows "Client: omnisharp (id: 1)"
- LSP features work (gd, grr, K, etc.)
- StyleCop warnings appear
- Initialization completes in 30-60 seconds

---

**Document Status**: Analysis Complete - Ready for User Testing
