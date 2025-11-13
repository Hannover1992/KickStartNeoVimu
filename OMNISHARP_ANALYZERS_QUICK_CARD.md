# OmniSharp Roslyn Analyzers - Quick Reference Card

**Problem**: StyleCop analyzer warnings not showing in Neovim LSP

**Solution**: Enable `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

---

## The 5-Second Answer

When `EnableAnalyzersSupport=true` is set, OmniSharp:
1. Discovers StyleCop.Analyzers from .csproj
2. Loads the analyzer DLL
3. Runs Roslyn analysis on your code
4. Sends SA1xxx diagnostics to Neovim
5. You see red/yellow underlines

---

## Critical Checklist

Before troubleshooting, verify these 5 things:

```bash
# 1. StyleCop.Analyzers in .csproj?
grep StyleCop.Analyzers /path/to/*.csproj

# 2. EnableAnalyzersSupport in init.lua?
grep "EnableAnalyzersSupport = true" ~/.config/nvim/init.lua

# 3. NuGet packages restored?
ls ~/.nuget/packages/stylecop.analyzers/

# 4. Cache cleared?
rm -rf ~/.cache/nvim/luac/

# 5. Process killed?
pkill -f omnisharp; sleep 1; ps aux | grep omnisharp | grep -v grep
# (output should be empty)
```

---

## If Warnings Still Don't Appear

### Step 1: Verify OmniSharp Received the Setting

```vim
:LspInfo
" Look for this in output:
" RoslynExtensionsOptions = {
"   EnableAnalyzersSupport = true,  ← MUST be true
"   AnalyzeOpenDocumentsOnly = false,
"   ...
" }
```

### Step 2: Check What's Actually Running

```bash
ps aux | grep omnisharp | grep -v grep
# Should show (on one line):
# dotnet /path/to/OmniSharp.dll -s /path/to/Backend -loglevel Information \
#   RoslynExtensionsOptions:EnableAnalyzersSupport=true \
#   RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
```

### Step 3: Check Logs for Errors

```bash
tail -50 ~/.local/state/nvim/lsp.log | grep -i "analyzer\|stylecop\|error"
```

### Step 4: Check .editorconfig Isn't Disabling Rules

```bash
grep "SA1.*severity = none" /path/to/Backend/.editorconfig
# If it shows rules with "none", change to "warning" or "error"
```

---

## 8 Reasons Analyzers Don't Load

| Reason | Check | Fix |
|--------|-------|-----|
| **EnableAnalyzersSupport not set** | `grep EnableAnalyzersSupport ~/.config/nvim/init.lua` | Add `EnableAnalyzersSupport = true` in settings |
| **StyleCop.Analyzers missing** | `grep StyleCop *.csproj` | `dotnet add <proj>.csproj package StyleCop.Analyzers` |
| **Packages not restored** | `ls ~/.nuget/packages/stylecop.analyzers/` | `dotnet restore --force-evaluate --no-cache` |
| **Windows/WSL2 mismatch** | Built in Windows, running in WSL2 | `dotnet restore --force-evaluate --no-cache` in WSL2 |
| **Cache stale** | Lua bytecode or OmniSharp cached | `rm -rf ~/.cache/nvim/luac/; pkill -f omnisharp` |
| **Analysis times out** | See brief underlines then disappear | Increase `documentAnalysisTimeoutMs` to 60000 |
| **Only analyzing open files** | `AnalyzeOpenDocumentsOnly = true` | Set to `false` (slower but comprehensive) |
| **Rules disabled in .editorconfig** | `grep "severity = none" .editorconfig` | Change to `warning` or `error` |

---

## Expected Output

### In Code (When Working)

```csharp
public void MyMethod(  // ← Line 56
    int param1,        // ← Red underline: SA1116 parameter alignment
    int param2)
```

### When Hovering (K)

```
SA1116: Split parameters must start on line after declaration
Press <leader>ca to see fix options
```

### In :LspInfo

```
omnisharp (running)
  cmd: { "dotnet", "/home/user/.../OmniSharp.dll", "-s", "/path/to/Backend", ... }
  settings:
    RoslynExtensionsOptions:
      EnableAnalyzersSupport = true
      AnalyzeOpenDocumentsOnly = false
      EnableImportCompletion = true
    FormattingOptions:
      EnableEditorConfigSupport = true
      OrganizeImports = true
  Diagnostics: 6 issues
```

### In Process List

```bash
$ ps aux | grep omnisharp | grep -v grep
user 12345 ... dotnet /path/to/OmniSharp.dll \
  -s /path/to/Backend \
  -loglevel Information \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true \
  RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false
```

---

## One-Minute Debug

When nothing is working, run this:

```bash
#!/bin/bash
echo "=== Quick Diagnostics ===" && \
echo "1. StyleCop in .csproj:" && grep -l StyleCop.Analyzers /path/to/*.csproj 2>/dev/null | wc -l && \
echo "2. Config has EnableAnalyzersSupport:" && grep "EnableAnalyzersSupport = true" ~/.config/nvim/init.lua && echo "✅" && \
echo "3. OmniSharp running:" && pgrep -f omnisharp && echo "✅" || echo "Not running - expected, will start with Neovim" && \
echo "4. NuGet cache:" && ls ~/.nuget/packages/stylecop.analyzers/ && echo "✅"
```

---

## The Root Cause (Most Common)

**99% of the time**: The setting is missing or misspelled

```lua
-- WRONG (typo or missing)
RoslynExtensionsOptions = {
  enableAnalyzersSupport = true,  ← Lua case-sensitive! Must be EnableAnalyzersSupport
}

-- CORRECT
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,  ← Uppercase E and A
}
```

---

## Three-Step Fix (If Starting Fresh)

1. **Ensure configuration:**
   ```lua
   -- In ~/.config/nvim/init.lua
   omnisharp = {
     settings = {
       RoslynExtensionsOptions = {
         EnableAnalyzersSupport = true,
         AnalyzeOpenDocumentsOnly = false,
       },
     },
   }
   ```

2. **Clear everything:**
   ```bash
   pkill -f omnisharp
   rm -rf ~/.cache/nvim/luac/
   cd /path/to/Backend
   dotnet restore --force-evaluate --no-cache
   ```

3. **Test:**
   ```bash
   nvim /path/to/UserController.cs
   # Wait 5 seconds for OmniSharp to initialize
   # Look for red underlines (SA1xxx)
   ```

---

## Log Grep Patterns

Copy and run these to analyze LSP logs:

```bash
# Show all analyzer-related messages
tail -100 ~/.local/state/nvim/lsp.log | grep -i "analyzer\|stylecop\|roslyn\|diagnostic"

# Show errors
tail -100 ~/.local/state/nvim/lsp.log | grep "ERROR\|FAIL\|error"

# Show timeouts
tail -100 ~/.local/state/nvim/lsp.log | grep -i "timeout\|timing out"

# Show solution loading
tail -100 ~/.local/state/nvim/lsp.log | grep -i "solution\|project\|loaded"

# Real-time watching (in terminal)
tail -f ~/.local/state/nvim/lsp.log | grep -i analyzer
```

---

## Keybindings to Test Analyzers

Once enabled, test with these:

| Key | Action | Expected |
|-----|--------|----------|
| `]d` | Next diagnostic | Jump to next SA1xxx warning |
| `[d` | Previous diagnostic | Jump to previous warning |
| `K` | Hover | Shows "SA1xxx: rule description" |
| `<leader>ca` | Code actions | Shows "Fix: ..." options |
| `<leader>w` | Warnings list | Telescope with all diagnostics |
| `:LspInfo` | LSP status | Shows RoslynExtensionsOptions |

---

## Performance Tuning

If warnings appear then disappear, or OmniSharp is slow:

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,

  -- Increase timeout for large files (in milliseconds)
  documentAnalysisTimeoutMs = 60000,  -- 60 seconds instead of 30

  -- Reduce parallel threads if CPU is maxed
  diagnosticWorkersThreadCount = 2,   -- Lower number = less CPU but slower

  -- Analyze only open files for speed
  AnalyzeOpenDocumentsOnly = true,    -- Less comprehensive but faster
}
```

---

## Files You Need

### In Your Repository
- ✅ `.csproj` with `<PackageReference Include="StyleCop.Analyzers" />`
- ✅ `.editorconfig` (optional but recommended) with rule configuration
- ✅ `.stylecop.json` (optional) with StyleCop settings

### In Your User Config
- ✅ `~/.config/nvim/init.lua` with `EnableAnalyzersSupport = true`
- ✅ `~/.local/state/nvim/lsp.log` (auto-created, check for errors)

### In NuGet Cache
- ✅ `~/.nuget/packages/stylecop.analyzers/1.1.118/`

---

## When All Else Fails

Nuclear option (last resort):

```bash
# 1. Kill everything
killall nvim 2>/dev/null
pkill -9 -f omnisharp
pkill -9 -f dotnet
sleep 2

# 2. Clear all caches
rm -rf ~/.cache/nvim/luac/
rm -rf ~/.local/state/nvim/swap/*.swp
rm -rf ~/.omnisharp/

# 3. Restore clean
cd /path/to/Backend
dotnet clean
dotnet restore --force-evaluate --no-cache
rm -rf .vscode/.omnisharp

# 4. Start fresh
nvim /path/to/UserController.cs
# Should see: "🔧 OmniSharp explicitly configured..."
```

---

## Success Criteria

You'll know it's working when:

- [ ] Red/yellow underlines appear in C# code
- [ ] Hovering with `K` shows "SA1xxx: ..." messages
- [ ] `:LspInfo` shows `EnableAnalyzersSupport = true`
- [ ] `ps aux | grep omnisharp` shows the setting in command line
- [ ] `~/.local/state/nvim/lsp.log` has no ANALYZER errors

---

## Reference Links

- **OmniSharp Config**: https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options
- **StyleCop.Analyzers**: https://github.com/DotNetAnalyzers/StyleCopAnalyzers
- **Roslyn Analyzers Article**: https://www.strathweb.com/2019/04/roslyn-analyzers-in-code-fixes-in-omnisharp-and-vs-code/

---

**Last Updated**: 2025-11-13
**Verified With**: OmniSharp mason package, Neovim with nvim-lspconfig, StyleCop.Analyzers 1.1.118

