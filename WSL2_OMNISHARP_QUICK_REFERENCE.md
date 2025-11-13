# WSL2 + OmniSharp Quick Reference Card

**Print this page or bookmark it!**

---

## Does OmniSharp Work with /mnt/c Paths?

### ✅ YES - But with caveats:

| Aspect | Status | Notes |
|--------|--------|-------|
| **Works at all?** | ✅ YES | OmniSharp can load projects from /mnt/c |
| **Path format** | ✅ YES | `-s /mnt/c/Users/Administrator/...` works |
| **File access** | ✅ YES | Can read/write files, intellisense works |
| **Case sensitive** | ⚠️ CAREFUL | Windows is case-insensitive, WSL2 is case-sensitive |
| **Speed** | ❌ SLOW | 10x slower than native Linux paths (/home) |
| **File locking** | ⚠️ POSSIBLE | Windows may lock files while WSL2 accesses |
| **NuGet cache** | ❌ SEPARATE | Windows and WSL2 have different caches |

### Recommendation
- **Small projects**: /mnt/c is OK (2-5 second OmniSharp startup)
- **Large projects**: Move to /home (50+ MB or 500+ files)
- **Best practice**: Use /home with sync workflow

---

## The Key Issues Explained Simply

### 1. **Speed Issue** (10x slower)
```
Native Linux: /home/uczen/.../Backend  →  2-3s OmniSharp startup
Windows via WSL: /mnt/c/Users/...     → 25-30s OmniSharp startup ❌
```
**Why**: Windows filesystem accessed through DrvFs layer = overhead
**Fix**: Move to /home

### 2. **NuGet Cache Separate**
```
Build in Windows: C:\Users\Admin\.nuget\packages    ← Windows cache
Build in WSL2:   /home/uczen/.nuget/packages        ← Different cache
Result: Packages restored in Windows don't help WSL2
```
**Fix**: Set `export NUGET_PACKAGES="$HOME/.nuget/packages"` in ~/.bashrc

### 3. **Case Sensitivity**
```
Windows: USERCONTROLLER.CS == usercontroller.cs == UserController.cs ✅
WSL2:    USERCONTROLLER.CS ≠ usercontroller.cs ≠ UserController.cs ❌
```
**Fix**: Use exact casing in paths: `/mnt/c/Users/.../VDEK.DCSP.WebApi/...` (exact case)

### 4. **File Locking**
```
Scenario:
1. Visual Studio (Windows) builds → locks .dll files
2. WSL2 OmniSharp tries to load → "file locked" error
3. Can't proceed until Windows releases lock
```
**Fix**: Don't build in Windows and WSL2 simultaneously. Use `fixlsp` alias to recover.

---

## Quick Fixes (Copy-Paste)

### Fix 1: Setup NuGet (Always Do This)

**Add to ~/.bashrc** (at bottom):
```bash
export NUGET_PACKAGES="$HOME/.nuget/packages"
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools"
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=true
export DOTNET_CLI_TELEMETRY_OPTOUT=true

alias fixlsp='dotnet restore --force-evaluate --no-cache && pkill -f omnisharp'
```

Then run:
```bash
source ~/.bashrc
```

### Fix 2: Update init.lua (Correct OmniSharp Setup)

**Find this in /home/uczen/.config/nvim/init.lua** (around line 930-980):

```lua
omnisharp = {
  cmd = {
    'dotnet',  -- ✅ Use 'dotnet', not 'OmniSharp'
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
},
```

### Fix 3: Clear Caches and Restart

```bash
# Kill OmniSharp
pkill -f omnisharp

# Clear Lua bytecode cache
rm -rf ~/.cache/nvim/luac/

# Force NuGet restore
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet restore --force-evaluate --no-cache

# Restart Neovim and open C# file
nvim UserController.cs
```

---

## Symptoms and Solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| **OmniSharp takes 30+ seconds to start** | /mnt/c path or slow restore | `fixlsp` or move to /home |
| **"No LSP client attached"** | OmniSharp can't load project | Check path: `ls -la /mnt/c/.../Backend/` |
| **Intellisense popup appears in 3-5 seconds** | /mnt/c filesystem overhead | Move to /home (Scenario 2) or set `AnalyzeOpenDocumentsOnly = true` |
| **"The file is being used by another process"** | Windows holds file locks | Stop Windows builds, run `fixlsp` |
| **NuGet packages not found after Windows build** | Separate caches | Run `fixlsp` |
| **`:LspInfo` shows empty RoslynExtensionsOptions** | Config not loading | Clear cache `rm -rf ~/.cache/nvim/luac/` and restart |
| **Case sensitivity errors in paths** | Mixed case in /mnt/c path | Use exact Windows casing: `/mnt/c/Users/...` |

---

## Which Scenario Are You In?

### Scenario A: "I just want it working NOW"
→ **Use /mnt/c with quick fixes above**
- Accept 20-30s OmniSharp startup
- Run `fixlsp` after Windows builds
- Done!

### Scenario B: "I want it FAST"
→ **Move to /home (Scenario 2 in recommendations)**
```bash
mkdir -p ~/projects
cp -r /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE ~/projects/
# Update init.lua: -s vim.fn.expand('~/projects/DCSRE/Sources/Backend')
```
- 2-3s OmniSharp startup (10x faster!)
- Zero file locking issues
- Pure Linux performance

### Scenario C: "I need both Windows and WSL2 access"
→ **Use /home with sync (Scenario 3 in recommendations)**
```bash
# Setup like Scenario B, then add to ~/.bashrc:
synctows() { cp -r ~/projects/DCSRE/Sources/Backend/* \
  /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/; }
syncfromws() { cp -r /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/* \
  ~/projects/DCSRE/Sources/Backend/; pkill -f omnisharp; }
```
- Work in WSL2 with full speed
- Sync to Windows when done: `synctows`
- Sync from Windows when needed: `syncfromws`

---

## Performance Chart

```
╔═══════════════════════════════════════════════════════╗
║ OmniSharp Startup Time (Seconds)                      ║
╠═══════════════════════════════════════════════════════╣
║ Native Windows (Local):        [I] 1-2s               ║
║ Native Linux (/home):         [II] 2-3s               ║
║ WSL2 /mnt/c:                [IIIIII] 25-30s           ║
╚═══════════════════════════════════════════════════════╝

Bottom line: /home is 10x FASTER than /mnt/c
```

---

## Path Comparison Table

| Aspect | /mnt/c Path | /home Path |
|--------|------------|-----------|
| **Current Location** | `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE` | `~/projects/DCSRE` |
| **in init.lua** | `'/mnt/c/Users/Administrator/.../Backend'` | `'~/projects/DCSRE/Sources/Backend'` |
| **Speed** | ⚠️ 10x slower | ✅ Native speed |
| **File locking** | ⚠️ Windows may lock | ✅ No locks |
| **Setup effort** | ✅ No copy needed | ⚠️ Need to copy |
| **Windows access** | ✅ Direct | ⚠️ Via /mnt/c |
| **NuGet cache** | ❌ Separate from Windows | ✅ Unified in Linux |
| **Recommended** | ⚠️ Only if small project | ✅✅✅ Best choice |

---

## Environment Variables (Copy-Paste)

### ~/.bashrc (or ~/.zshrc)

```bash
# === .NET and NuGet Configuration ===

# Use WSL2's native NuGet cache
export NUGET_PACKAGES="$HOME/.nuget/packages"

# .NET SDK paths
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools"

# Performance flags
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=true
export DOTNET_CLI_TELEMETRY_OPTOUT=true

# Recovery command - use after building in Windows
alias fixlsp='echo "Fixing OmniSharp..." && \
    dotnet nuget locals all --clear && \
    dotnet restore --force-evaluate --no-cache && \
    pkill -f omnisharp && \
    echo "OmniSharp restarted. Open file in Neovim."'
```

Save, then:
```bash
source ~/.bashrc
```

---

## One-Minute Troubleshooting

**OmniSharp not connecting in 30+ seconds?**
```bash
pkill -f omnisharp
rm -rf ~/.cache/nvim/luac/
fixlsp
# Wait, then reopen file in Neovim
```

**After building in Windows?**
```bash
fixlsp
```

**Want maximum speed?**
```bash
mkdir -p ~/projects
cp -r /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE ~/projects/
# Update init.lua path to ~/projects/DCSRE/Sources/Backend
```

---

## Key Takeaways

✅ **DO:**
- Use `dotnet` + OmniSharp.dll (not .exe)
- Set `NUGET_PACKAGES=$HOME/.nuget/packages` in ~/.bashrc
- Use exact Windows casing in /mnt/c paths
- Run `fixlsp` after Windows builds
- Consider moving to /home for production workflows

❌ **DON'T:**
- Use OmniSharp.exe in WSL2 (Windows-only binary)
- Expect fast intellisense from /mnt/c (it's 10x slower)
- Build in Windows and WSL2 simultaneously
- Use /mnt/c paths if project is large (500+ files)
- Use symlinks on /mnt/c (OmniSharp may not follow them)

🎯 **IDEAL SETUP:**
- Copy project to ~/projects/DCSRE
- Use ~/projects path in init.lua
- Enjoy 2-3 second startup, zero locking issues
- Sync back to Windows when needed

---

## Files to Read

**For comprehensive details:**
1. `WSL2_OMNISHARP_RESEARCH.md` - Full technical research
2. `WSL2_OMNISHARP_CONFIG_RECOMMENDATIONS.md` - Implementation scenarios

**Quick reference:** This file

---

## Support Checklist

Before asking for help, verify:

- [ ] `export NUGET_PACKAGES="$HOME/.nuget/packages"` in ~/.bashrc
- [ ] `dotnet --version` works (returns 9.0.x)
- [ ] Path exists: `ls -la /mnt/c/Users/.../Backend/` or `ls -la ~/projects/DCSRE/`
- [ ] init.lua has correct path with correct casing
- [ ] Ran `pkill -f omnisharp` to clear old process
- [ ] Ran `rm -rf ~/.cache/nvim/luac/` to clear cache
- [ ] Waited 20-30 seconds for OmniSharp startup (or 2-3 if using /home)

✅ If all above are done and still not working → Check `~/.local/state/nvim/lsp.log`

---

**Version**: 1.0 | **Date**: 2025-11-13 | **Platform**: WSL2 Ubuntu 24.04 + Neovim 0.11.4 + .NET 9.0.306

**TL;DR**: Yes, /mnt/c works but is 10x slower. Use ~/projects for best experience. Always set NUGET_PACKAGES.
