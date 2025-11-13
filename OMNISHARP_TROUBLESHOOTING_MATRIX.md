# OmniSharp Roslyn Analyzers Troubleshooting Matrix

**Purpose**: Diagnostic decision tree for StyleCop warnings not appearing in Neovim

**How to Use**: Start at "Symptom" and follow the diagnostic steps, checking boxes as you go.

---

## Quick Diagnosis Flow

```
Do you see red/yellow underlines?
├─ YES  → Go to: "Underlines Appearing But Wrong"
├─ NO   → Go to: "No Underlines Appearing"
└─ SOMETIMES → Go to: "Intermittent Warnings"
```

---

## Symptom: No Underlines Appearing at All

### Diagnostic Tree

**Q1: Is OmniSharp even running?**

```bash
ps aux | grep omnisharp | grep -v grep
```

- [ ] **NO** - Go to: [Fix: OmniSharp Won't Start](#fix-omnisharp-wont-start)
- [ ] **YES** - Continue to Q2

---

**Q2: Does `:LspInfo` show OmniSharp attached?**

```vim
:LspInfo
" Look for "omnisharp (running)"
```

- [ ] **NO** - OmniSharp not attached to buffer
  - Go to: [Fix: LSP Client Not Attaching](#fix-lsp-client-not-attaching)
- [ ] **YES** - Continue to Q3

---

**Q3: Does `:LspInfo` show `EnableAnalyzersSupport = true`?**

```vim
:LspInfo
" Look for: RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... }
```

- [ ] **NO** (shows empty or false)
  - Go to: [Fix: Setting Not Being Passed](#fix-setting-not-being-passed-to-omnisharp)
- [ ] **YES** - Continue to Q4

---

**Q4: Check if StyleCop.Analyzers is even installed in the project**

```bash
grep StyleCop.Analyzers /path/to/*.csproj
```

- [ ] **NO matches** - Go to: [Fix: Package Not Installed](#fix-stylecopanalyzers-not-installed)
- [ ] **YES, found** - Continue to Q5

---

**Q5: Check if NuGet packages are restored**

```bash
ls ~/.nuget/packages/stylecop.analyzers/
```

- [ ] **Directory not found** - Go to: [Fix: NuGet Not Restored](#fix-nuget-packages-not-restored)
- [ ] **Directory exists** - Continue to Q6

---

**Q6: Check OmniSharp logs for analyzer errors**

```bash
tail -100 ~/.local/state/nvim/lsp.log | grep -i "error\|fail"
```

- [ ] **Shows analyzer errors** - Go to: [Fix: Analyzer Loading Failed](#fix-analyzer-loading-failed)
- [ ] **No errors visible** - Go to: [Fix: Mystery - Advanced Diagnostics](#fix-mystery-advanced-diagnostics)

---

## Symptom: Underlines Appearing But Wrong

### Issues and Fixes

**Wrong Rules Showing**

- Showing warnings you don't expect?
- Check `.editorconfig` isn't enabling rules you disabled:
  ```bash
  grep "dotnet_diagnostic.SA" /path/to/.editorconfig | grep -v "none"
  ```
- Or check ruleset file isn't overriding settings:
  ```bash
  find . -name "*.ruleset" -type f
  ```

**Only Showing Some Rules**

- Some SA1xxx rules appear, but not others?
- The missing ones are likely disabled in `.editorconfig`:
  ```bash
  grep "dotnet_diagnostic.SA1101.severity" /path/to/.editorconfig
  # If it says "none", change to "warning"
  ```

**Wrong Line Numbers**

- Warnings at wrong lines?
- Might be cache issue. Clear and restart:
  ```bash
  pkill -f omnisharp
  rm -rf ~/.cache/nvim/luac/
  nvim
  ```

---

## Symptom: Intermittent Warnings

### Appears and Disappears

**Red underlines appear when file opens, then disappear after 5-10 seconds**

This is almost always **analysis timeout**.

```bash
# Check if logs show timeout
tail -50 ~/.local/state/nvim/lsp.log | grep -i "timeout\|timing out"
```

**Fix:**

```lua
-- In init.lua, increase timeout
RoslynExtensionsOptions = {
  documentAnalysisTimeoutMs = 60000,  -- Increase from 30s to 60s
  diagnosticWorkersThreadCount = 4,   -- Reduce parallelism
}
```

---

**Only Shows in Some Files**

- Warnings in small files, but not in larger ones?
- Same issue: timeout

---

**Appears When File is Edited, Disappears When Idle**

- Warnings appear while editing, go away when you stop?
- This is expected behavior when `AnalyzeOpenDocumentsOnly = true`
- The analyzer only runs when file changes

**Fix (if you want always-on):**

```lua
RoslynExtensionsOptions = {
  AnalyzeOpenDocumentsOnly = false,  -- Always analyze, not just when editing
}
```

---

## Detailed Fixes

### Fix: OmniSharp Won't Start

**Symptoms:**
- `ps aux | grep omnisharp` shows nothing
- No error messages in Neovim

**Diagnosis:**

```bash
# Check if OmniSharp is even installed
ls ~/.local/share/nvim/mason/packages/omnisharp/

# Check if DLL exists
ls ~/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll

# Check if Mason can find it
nvim -c ":Mason" -c ":q"
# Look for "omnisharp" in list
```

**Solutions:**

1. **Install OmniSharp via Mason:**
   ```vim
   :Mason
   " Search for 'omnisharp'
   " Press 'i' to install
   ```

2. **Or install via command line:**
   ```bash
   nvim +MasonInstall+omnisharp +qa
   ```

3. **Verify path in init.lua is correct:**
   ```lua
   cmd = {
     'dotnet',
     vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',  ← Check this path
     '-s', vim.fn.expand('/path/to/Backend'),
     '-loglevel', 'Information',
   }
   ```

---

### Fix: LSP Client Not Attaching

**Symptoms:**
- `:LspInfo` shows no omnisharp client
- Or shows omnisharp but "not running"

**Diagnosis:**

```bash
# Check if Neovim started LSP
tail -20 ~/.local/state/nvim/lsp.log | head -20
# Should show OmniSharp initialization

# Check if file is recognized as C#
nvim /path/to/file.cs
# Type: :set filetype
# Should show: filetype=cs
```

**Solutions:**

1. **Ensure you're in a C# file:**
   ```vim
   :set filetype?
   " Should show: filetype=cs
   " If not: :set filetype=cs
   ```

2. **Restart LSP:**
   ```vim
   :LspRestart
   ```

3. **Check init.lua has omnisharp setup:**
   ```bash
   grep "lspconfig.*omnisharp" ~/.config/nvim/init.lua
   ```

4. **If none of above work, check logs:**
   ```bash
   tail -50 ~/.local/state/nvim/lsp.log | grep -i "omnisharp\|error"
   ```

---

### Fix: Setting Not Being Passed to OmniSharp

**Symptoms:**
- `:LspInfo` shows RoslynExtensionsOptions = {} (empty!)
- Or shows EnableAnalyzersSupport = false/nil

**Root Cause:**
- Settings defined but not passed to OmniSharp during setup
- Lua scope issue (servers variable out of scope)
- Lua cache preventing config reload

**Diagnosis:**

```bash
# Check if setting is in init.lua at all
grep "EnableAnalyzersSupport = true" ~/.config/nvim/init.lua

# Check Lua cache
ls -la ~/.cache/nvim/luac/ | head -5
```

**Solutions:**

1. **Clear Lua cache (most common fix):**
   ```bash
   rm -rf ~/.cache/nvim/luac/
   pkill -f omnisharp
   nvim
   ```

2. **Verify init.lua structure:**

   The settings MUST be inside the `omnisharp` table in `servers`:
   ```lua
   local servers = {
     omnisharp = {
       cmd = { ... },
       settings = {  -- ← Must have "settings" key
         RoslynExtensionsOptions = {
           EnableAnalyzersSupport = true,  -- ← Inside RoslynExtensionsOptions
         },
       },
     },
   }
   ```

3. **Ensure explicit omnisharp setup:**

   After `mason-lspconfig.setup`, explicitly configure OmniSharp:
   ```lua
   if servers.omnisharp then
     local cfg = vim.deepcopy(servers.omnisharp)
     cfg.capabilities = vim.tbl_deep_extend('force', {}, capabilities, cfg.capabilities or {})
     require('lspconfig').omnisharp.setup(cfg)
   end
   ```

4. **Verify settings aren't nil:**
   ```vim
   :lua print(vim.inspect(require('lspconfig').omnisharp.settings))
   " Should show the full settings table, not empty
   ```

---

### Fix: StyleCop.Analyzers Not Installed

**Symptoms:**
- `:LspInfo` shows EnableAnalyzersSupport = true
- But no SA1xxx warnings appear
- `grep StyleCop *.csproj` returns nothing

**Diagnosis:**

```bash
cd /path/to/DCSRE/Sources/Backend

# Check what packages are installed
dotnet list package | grep -i stylecop

# Check all projects
for f in */VDEK.*.csproj; do
  echo "Checking $f:"
  grep -q "StyleCop.Analyzers" "$f" && echo "  ✅ Has StyleCop" || echo "  ❌ Missing StyleCop"
done
```

**Solutions:**

1. **Add to individual project:**
   ```bash
   cd /path/to/DCSRE/Sources/Backend/VDEK.DCSP.WebApi
   dotnet add VDEK.DCSP.WebApi.csproj package StyleCop.Analyzers
   ```

2. **Or add to all projects at once:**
   ```bash
   cd /path/to/DCSRE/Sources/Backend
   for proj in */VDEK.*.csproj; do
     dotnet add "$proj" package StyleCop.Analyzers
   done
   ```

3. **Then restore:**
   ```bash
   dotnet restore
   ```

4. **Check it's in .csproj (should look like this):**
   ```xml
   <PackageReference Include="StyleCop.Analyzers" Version="1.1.118">
     <PrivateAssets>all</PrivateAssets>
     <IncludeAssets>runtime; build; native; contentfiles; analyzers</IncludeAssets>
   </PackageReference>
   ```

---

### Fix: NuGet Packages Not Restored

**Symptoms:**
- StyleCop.Analyzers in .csproj
- But EnableAnalyzersSupport = true shows no warnings
- OmniSharp logs show "analyzer not found"

**Diagnosis:**

```bash
# Check if StyleCop is in NuGet cache
ls ~/.nuget/packages/stylecop.analyzers/

# Should show version directory like: 1.1.118/
```

**Solutions:**

1. **Simple restore:**
   ```bash
   cd /path/to/DCSRE/Sources/Backend
   dotnet restore
   ```

2. **Force restore (WSL2 specific, if built in Windows):**
   ```bash
   dotnet restore --force-evaluate --no-cache
   ```

3. **Full clean + restore:**
   ```bash
   dotnet clean
   dotnet restore --force-evaluate --no-cache
   ```

4. **Or use Neovim keybinding:**
   ```vim
   <leader>bs    " Runs: dotnet restore --force-evaluate --no-cache
   ```

---

### Fix: Analyzer Loading Failed

**Symptoms:**
- Logs show: `[ERROR] Failed to load analyzer: StyleCop.Analyzers`
- Or: `[ERROR] Analyzer not found at package path`

**Diagnosis:**

```bash
# Check if DLL exists at expected path
ls ~/.nuget/packages/stylecop.analyzers/1.1.118/analyzers/dotnet/cs/StyleCop.Analyzers.dll

# Check if file is corrupted
file ~/.nuget/packages/stylecop.analyzers/1.1.118/analyzers/dotnet/cs/StyleCop.Analyzers.dll
# Should show: "PE32+ executable"
```

**Solutions:**

1. **Clear NuGet cache and restore:**
   ```bash
   rm -rf ~/.nuget/packages/stylecop.analyzers/
   dotnet restore --force-evaluate --no-cache
   ```

2. **Check for corruption:**
   ```bash
   # Remove and re-download
   rm -rf ~/.nuget/packages/stylecop.analyzers
   dotnet restore
   ```

3. **Check if .csproj references are correct:**
   ```bash
   grep -A 2 "StyleCop.Analyzers" *.csproj
   # Should show: <IncludeAssets>...analyzers</IncludeAssets>
   ```

---

### Fix: Mystery - Advanced Diagnostics

**When you've checked everything above and still nothing works**

**Super Detailed Diagnostic:**

```bash
#!/bin/bash
echo "=== COMPREHENSIVE OMNISHARP DIAGNOSTIC ==="

# 1. File type verification
echo "1. File type in Neovim:"
nvim -c "set ft?" -c "q" /path/to/file.cs 2>&1 | grep filetype

# 2. LSP configuration
echo "2. LSP config:"
grep -n "EnableAnalyzersSupport" ~/.config/nvim/init.lua

# 3. Process command line
echo "3. OmniSharp running with:"
if pgrep -f omnisharp > /dev/null; then
  ps aux | grep omnisharp | grep -v grep | tr ' ' '\n' | head -20
else
  echo "Not running"
fi

# 4. NuGet package verification
echo "4. NuGet StyleCop:"
ls -la ~/.nuget/packages/stylecop.analyzers/*/analyzers/dotnet/cs/*.dll

# 5. Config file check
echo "5. Init.lua syntax:"
nvim -c "try | source ~/.config/nvim/init.lua | echo 'OK' | catch | echo 'ERROR:' . v:exception | endtry" -c "q" 2>&1

# 6. Log tail
echo "6. Recent LSP log:"
tail -30 ~/.local/state/nvim/lsp.log | grep -i "omnisharp\|analyzer\|roslyn"

# 7. Cache status
echo "7. Lua cache size:"
du -sh ~/.cache/nvim/luac/ 2>/dev/null || echo "No cache"
```

**Run it and capture output for analysis:**

```bash
bash /path/to/diagnostic.sh > /tmp/diagnostic.txt
# Share the output or use it for comparison
```

---

### Fix: Analyzer Runs but Gives Wrong Results

**Symptoms:**
- Warnings appear, but they're for the wrong rules
- Or pointing to wrong lines
- Or not following project conventions

**Solutions:**

1. **Check .editorconfig exists and is correct:**
   ```bash
   cat /path/to/Backend/.editorconfig | head -20
   ```

2. **Verify rule severity settings:**
   ```bash
   # Example: if SA1101 isn't showing but should be
   grep "SA1101" /path/to/Backend/.editorconfig
   # Should show: dotnet_diagnostic.SA1101.severity = warning
   # NOT:         dotnet_diagnostic.SA1101.severity = none
   ```

3. **Update .editorconfig rules:**
   ```ini
   [*.cs]
   # Enable StyleCop rules
   dotnet_diagnostic.SA1000.severity = warning
   dotnet_diagnostic.SA1001.severity = warning
   dotnet_diagnostic.SA1101.severity = warning
   # ... etc
   ```

4. **Restart OmniSharp to reload config:**
   ```bash
   pkill -f omnisharp
   rm -rf ~/.cache/nvim/luac/
   nvim
   ```

---

## Verification After Each Fix

**After applying any fix, verify with:**

```vim
" 1. Check LSP is still attached
:LspInfo
" Should show: omnisharp (running)

" 2. Check settings updated
:lua print(vim.inspect(require('lspconfig').omnisharp.settings))
" Should show all RoslynExtensionsOptions

" 3. Wait and look for underlines
" Give OmniSharp 5-10 seconds to analyze
" Then look for red/yellow underlines

" 4. Check a diagnostic
" Press: ]d or [d to jump to diagnostics
" Press: K to see what rule it is (should be SA1xxx)

" 5. Check process if still nothing
:terminal
ps aux | grep omnisharp | grep -v grep
" Verify command includes: RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

---

## When to Escalate

If after trying all above fixes warnings still don't appear:

1. **Check OmniSharp version:**
   ```bash
   ls ~/.local/share/nvim/mason/packages/omnisharp/
   # Current version should be recent (2024+)
   ```

2. **Check StyleCop.Analyzers version:**
   ```bash
   ls ~/.nuget/packages/stylecop.analyzers/
   # Current is 1.1.118
   ```

3. **Try updating both:**
   ```bash
   :MasonUpdate omnisharp
   # And in project:
   cd /path/to/Backend
   dotnet add package StyleCop.Analyzers --version 1.2.0-beta.435
   dotnet restore
   ```

4. **Report issue with:**
   - Output of: `bash OMNISHARP_VERIFICATION_SCRIPT.sh`
   - Last 50 lines of: `~/.local/state/nvim/lsp.log`
   - Content of: `grep EnableAnalyzersSupport ~/.config/nvim/init.lua`
   - Content of: `grep StyleCop *.csproj`

---

## Decision Tree Summary

```
Start: No underlines?
├─ OmniSharp not running?
│  └─ Fix: OmniSharp Won't Start
├─ OmniSharp not attached?
│  └─ Fix: LSP Client Not Attaching
├─ EnableAnalyzersSupport = true not in :LspInfo?
│  └─ Fix: Setting Not Being Passed
├─ StyleCop.Analyzers not in .csproj?
│  └─ Fix: StyleCop.Analyzers Not Installed
├─ NuGet package not found?
│  └─ Fix: NuGet Packages Not Restored
├─ Logs show analyzer error?
│  └─ Fix: Analyzer Loading Failed
└─ Everything looks right?
   └─ Fix: Mystery - Advanced Diagnostics
```

---

**Last Updated**: 2025-11-13
**Version**: 1.0
**Tested Against**: OmniSharp (Mason), Neovim, StyleCop.Analyzers 1.1.118

