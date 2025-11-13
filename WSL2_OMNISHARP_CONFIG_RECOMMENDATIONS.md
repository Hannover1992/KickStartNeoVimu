# WSL2 + OmniSharp Configuration Recommendations

**Quick Decision Tree**: Find your scenario and implement the recommended configuration.

---

## Scenario 1: Keep Using /mnt/c Paths (Current Setup)

**Pros**:
- No project duplication
- Changes in Windows immediately visible in WSL2
- Works with existing setup

**Cons**:
- 10x slower than native Linux
- More prone to file locking issues
- Slower OmniSharp initialization

**Implementation**:

### 1. Update init.lua

```lua
-- In /home/uczen/.config/nvim/init.lua

-- Find this section around line 930-980 and update:
omnisharp = {
  -- CRITICAL: Use 'dotnet' + DLL path, NOT OmniSharp.exe
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
      AnalyzeOpenDocumentsOnly = false,  -- Set to true for faster but less thorough analysis
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
  },

  on_init = function(client, initialization_result)
    vim.notify('🔄 OmniSharp initializing (WSL2 + /mnt/c may take 20-30 seconds)...', vim.log.levels.INFO)
  end,

  on_attach = function(client, bufnr)
    vim.notify('✅ OmniSharp ready! (From /mnt/c path)', vim.log.levels.INFO)
  end,
},
```

### 2. Setup ~/.bashrc for NuGet

Add to **~/.bashrc** (at end of file):

```bash
# === NuGet Configuration for WSL2 + Windows Cross-Filesystem ===

# Use native WSL2 NuGet cache (not Windows cache)
export NUGET_PACKAGES="$HOME/.nuget/packages"

# .NET SDK paths
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools"

# Optional but recommended
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=true
export DOTNET_CLI_TELEMETRY_OPTOUT=true

# Recovery alias - use after building in Windows
alias fixlsp='echo "Clearing NuGet cache and restarting OmniSharp..." && \
    dotnet nuget locals all --clear && \
    dotnet restore --force-evaluate --no-cache && \
    pkill -f omnisharp && \
    echo "Done! OmniSharp will restart on next file open."'
```

### 3. Workflow Tips for /mnt/c Users

**When building in Windows first** (Visual Studio or PowerShell):
```bash
# After Windows build completes:
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend

# Clear OmniSharp cache and restore
fixlsp

# Then work in Neovim
nvim UserController.cs
```

**When files seem locked**:
```bash
# Kill OmniSharp immediately
pkill -f omnisharp

# Clear and restore
dotnet restore --force-evaluate --no-cache

# Wait 2-3 seconds, then reopen file in Neovim
```

---

## Scenario 2: Move to Native Linux Filesystem (RECOMMENDED)

**Pros**:
- 10x faster than /mnt/c
- No cross-filesystem conflicts
- Instant intellisense
- Best LSP experience

**Cons**:
- Requires copying/moving project
- Changes not immediately in Windows (need to copy back)
- Extra disk space usage

**Implementation**:

### 1. Copy Project to Linux

```bash
# Create projects directory
mkdir -p ~/projects

# Copy DCSRE project to Linux filesystem
cp -r /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE ~/projects/

# Verify copy
ls -la ~/projects/DCSRE/Sources/Backend/ | head -10
```

### 2. Update init.lua

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    -- Use fast native Linux path instead
    '-s', vim.fn.expand('~/projects/DCSRE/Sources/Backend'),
    '-loglevel', 'Information',
  },

  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,  -- Now can afford thorough analysis
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
  },

  on_init = function(client, initialization_result)
    vim.notify('🔄 OmniSharp initializing (native Linux path - fast!)...', vim.log.levels.INFO)
  end,

  on_attach = function(client, bufnr)
    vim.notify('✅ OmniSharp ready! (From native Linux path)', vim.log.levels.INFO)
  end,
},
```

### 3. Sync Workflow (Optional)

If you want to keep Windows and Linux versions in sync:

```bash
# ~/.bashrc helper functions

# Copy Linux version to Windows (after WSL2 work)
synctows() {
  echo "Syncing ~/projects/DCSRE to Windows..."
  cp -r ~/projects/DCSRE/Sources/Backend/* /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/
  echo "Done!"
}

# Copy Windows version to Linux (after Windows work)
syncfromws() {
  echo "Syncing Windows to ~/projects/DCSRE..."
  cp -r /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/* ~/projects/DCSRE/Sources/Backend/
  echo "Done!"
  pkill -f omnisharp  # Restart OmniSharp
}
```

---

## Scenario 3: Hybrid Approach (Best of Both)

**Concept**: Keep source in Windows, but have WSL2 working copy for LSP

**Pros**:
- Fast intellisense in WSL2
- Can still edit in Windows
- No syncing headaches

**Cons**:
- Extra disk space
- Need to manage two copies

**Implementation**:

### 1. Keep Windows as Primary

Work in Windows (Visual Studio or PowerShell) for normal development:
```
C:\Users\Administrator\Documents\Work\Code2\DCSRE\  (Primary - where you build)
```

### 2. Copy to Linux for WSL2 LSP

```bash
# Initial copy
cp -r /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE ~/projects/DCSRE

# Update init.lua to use Linux path
-s vim.fn.expand('~/projects/DCSRE/Sources/Backend'),
```

### 3. Sync Before WSL2 Session

```bash
# At start of WSL2 work session:
syncfromws  # Copies latest from Windows

# Work in Neovim
nvim ~/projects/DCSRE/Sources/Backend/UserController.cs

# At end of session:
synctows    # Copies changes back to Windows
```

---

## Scenario 4: Use Symlink (Minimal Changes)

**Concept**: Keep everything at /mnt/c, but WSL2 sees a fast symlink

**Pros**:
- Minimal configuration changes
- Single source of truth

**Cons**:
- Symlinks may not work reliably with OmniSharp
- Still have /mnt/c filesystem overhead

**Implementation**:

### 1. Create Symlink (May Not Work with OmniSharp)

```bash
# Create link (probably won't help OmniSharp)
ln -s /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE ~/dcsre-link
```

### 2. Update init.lua

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    -- Try symlink (but may not work)
    '-s', vim.fn.expand('~/dcsre-link/Sources/Backend'),
    '-loglevel', 'Information',
  },
  -- ... rest of settings
},
```

**Note**: This approach is **not recommended** because OmniSharp may not properly follow symlinks on /mnt/c mounts.

---

## Configuration Summary Table

| Setting | /mnt/c | /home | Hybrid | Symlink |
|---------|--------|-------|--------|---------|
| Path in init.lua | `/mnt/c/...` | `~/projects/...` | `~/projects/...` | `~/dcsre-link` |
| Speed | ⚠️ Slow (10x) | ✅ Fast | ✅ Fast | ❌ Still slow |
| Setup complexity | ✅ Easy | ⚠️ Medium | ⚠️ Medium | ✅ Easy |
| Sync needed | No | Yes | Yes | No |
| File locking issues | ⚠️ Possible | ✅ No | ✅ No | ⚠️ Possible |
| Recommended | ⚠️ OK | ✅✅✅ YES | ✅✅ Good | ❌ No |

---

## NuGet Cache Setup (All Scenarios)

Regardless of which scenario you choose, setup NuGet correctly:

### Option A: Use WSL2-Only Cache (RECOMMENDED)

```bash
# Add to ~/.bashrc
export NUGET_PACKAGES="$HOME/.nuget/packages"

# No fallback - only use Linux cache
# This forces clean restores after Windows builds, but prevents confusion
```

### Option B: Share Cache via Windows

```bash
# More complex, but reuses Windows packages

# Create mount point
mkdir -p ~/packages-windows

# Mount Windows cache (optional, requires setup)
# Add to ~/.bashrc:
# mkdir -p ~/packages-windows
# sudo mount -t drvfs 'C:/Users/Administrator/.nuget' ~/packages-windows 2>/dev/null || true

export NUGET_PACKAGES="$HOME/.nuget/packages"
export NUGET_FALLBACK_FOLDERS="$HOME/packages-windows"
```

---

## Quick Verification Script

Test your WSL2 + OmniSharp setup:

```bash
#!/bin/bash
# Save as ~/verify-omnisharp-setup.sh

echo "=== WSL2 + OmniSharp Setup Verification ==="
echo ""

echo "✓ .NET SDK:"
dotnet --version
echo ""

echo "✓ Project path exists:"
if [ -d "/home/uczen/projects/DCSRE/Sources/Backend" ]; then
  echo "  /home/uczen/projects/DCSRE/Sources/Backend ✅"
elif [ -d "/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend" ]; then
  echo "  /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend ✅"
else
  echo "  ❌ No path found!"
fi
echo ""

echo "✓ NuGet cache:"
echo "  NUGET_PACKAGES=$NUGET_PACKAGES"
ls -lh "$HOME/.nuget/packages" 2>/dev/null | head -5 || echo "  (empty or not found)"
echo ""

echo "✓ OmniSharp Mason installation:"
if [ -f ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll ]; then
  echo "  ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll ✅"
else
  echo "  ❌ OmniSharp.dll not found - install via :MasonInstall omnisharp"
fi
echo ""

echo "✓ Neovim LSP setup:"
if grep -q "omnisharp = {" ~/.config/nvim/init.lua; then
  echo "  init.lua has omnisharp config ✅"
else
  echo "  ❌ init.lua missing omnisharp config"
fi
echo ""

echo "=== Setup Verification Complete ==="
```

Run it:
```bash
bash ~/verify-omnisharp-setup.sh
```

---

## Implementation Checklist

### For Scenario 1 (Keep /mnt/c):

- [ ] Add `NUGET_PACKAGES` and `.NET` paths to ~/.bashrc
- [ ] Update init.lua with /mnt/c path (lines 930-980)
- [ ] Clear Lua cache: `rm -rf ~/.cache/nvim/luac/`
- [ ] Kill OmniSharp: `pkill -f omnisharp`
- [ ] Test: Open C# file in Neovim, wait 20-30s for OmniSharp
- [ ] Verify: `:LspInfo` shows correct command

### For Scenario 2 (Move to /home):

- [ ] Create ~/projects directory: `mkdir -p ~/projects`
- [ ] Copy project: `cp -r /mnt/c/.../DCSRE ~/projects/`
- [ ] Update init.lua with ~/projects path (lines 930-980)
- [ ] Clear Lua cache: `rm -rf ~/.cache/nvim/luac/`
- [ ] Kill OmniSharp: `pkill -f omnisharp`
- [ ] Test: Open C# file, wait 2-3s for OmniSharp (much faster!)
- [ ] Verify: `:LspInfo` shows correct command

### For Scenario 3 (Hybrid):

- [ ] Do steps from Scenario 2 (copy to /home)
- [ ] Add helper functions to ~/.bashrc (synctows, syncfromws)
- [ ] Create checklist reminder to sync before/after sessions
- [ ] Update init.lua (lines 930-980)

---

## Performance After Implementation

Expected timing improvements:

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| OmniSharp startup | 25-30s | 2-3s | 8-10x faster ✅ |
| intellisense popup | 3-5s | 300-500ms | 6-10x faster ✅ |
| File open | 500ms | 50ms | 10x faster ✅ |
| `dotnet build` | 45s | 15s | 3x faster ✅ |

---

## Troubleshooting Quick Links

If something breaks after implementation:

1. **OmniSharp won't connect**
   - Check path: `ls -la ~/projects/DCSRE/Sources/Backend/` (or /mnt/c path)
   - Kill and restart: `pkill -f omnisharp`
   - Check logs: `tail -50 ~/.local/state/nvim/lsp.log`

2. **Intellisense very slow**
   - Check path with: `ps aux | grep omnisharp | grep -v grep`
   - If still /mnt/c, move to /home (Scenario 2)
   - Or reduce analysis: `AnalyzeOpenDocumentsOnly = true` in settings

3. **NuGet packages not found**
   - Run: `dotnet restore --force-evaluate --no-cache`
   - Check cache: `echo $NUGET_PACKAGES`
   - Or use alias: `fixlsp`

4. **File lock errors**
   - Kill all builds: `pkill -f dotnet`
   - Kill OmniSharp: `pkill -f omnisharp`
   - Kill Neovim: `pkill -f nvim`
   - Clear and restore: `fixlsp`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-13
**Recommended Implementation**: Scenario 2 (Move to /home) for optimal experience
