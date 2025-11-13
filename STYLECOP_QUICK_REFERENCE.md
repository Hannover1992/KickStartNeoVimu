# StyleCop.Analyzers Quick Reference - One-Pager

## The 5-Point Checklist (Must All Be True)

| # | Component | Status | Critical Setting |
|---|-----------|--------|-------------------|
| 1 | StyleCop.Analyzers in .csproj | ✅ DCSRE | `<IncludeAssets>...analyzers...</IncludeAssets>` |
| 2 | stylecop.json file exists | ✅ DCSRE | Must define rules, linked in .csproj |
| 3 | .editorconfig rule severity | ✅ DCSRE | `dotnet_diagnostic.SA1116.severity = warning` |
| 4 | OmniSharp LSP configured | ❌ NOT YET | **`EnableAnalyzersSupport = true`** |
| 5 | Valid project structure | ✅ DCSRE | Projects restorable with `dotnet restore` |

**If ANY are missing → NO StyleCop warnings appear**

---

## How to Verify

### Command Line (Project Works?)
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet build 2>&1 | grep "SA"
```
Should show warnings like: `warning SA1116: Split parameters should start on line after declaration`

### Neovim (Editor Shows Warnings?)
```vim
:LspInfo              " Shows OmniSharp connected?
:lua =vim.lsp.get_clients()[1].config.settings  " Shows EnableAnalyzersSupport = true?
```

### If warnings appear in build but not editor:
```bash
ps aux | grep omnisharp | grep -v grep
```
Should show: `...RoslynExtensionsOptions:EnableAnalyzersSupport=true...`

---

## The One Critical Neovim Setting

```lua
require('lspconfig').omnisharp.setup({
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,  -- ← THIS OR NOTHING WORKS
      AnalyzeOpenDocumentsOnly = false,
    },
  },
})
```

**Without `EnableAnalyzersSupport = true`, OmniSharp ignores all Roslyn analyzers (including StyleCop)**

---

## Most Common Issues

### Issue 1: "Build shows warnings but editor doesn't"
**Cause**: OmniSharp not configured with `EnableAnalyzersSupport=true`
**Fix**: Add setting to Neovim config and restart OmniSharp

### Issue 2: "No build warnings either"
**Cause**: StyleCop.Analyzers package not installed OR not in `IncludeAssets`
**Fix**: Check .csproj has correct package reference

### Issue 3: "stylecop.json not being read"
**Cause**: File not linked as `<AdditionalFiles>` in .csproj
**Fix**: Add `<AdditionalFiles Include="..\stylecop.json" Link="stylecop.json" />`

### Issue 4: "Rules disabled even though file exists"
**Cause**: Rule severity set to `none` in .editorconfig
**Fix**: Change `dotnet_diagnostic.SA1116.severity = none` to `warning` or `error`

---

## File Locations in DCSRE

```
/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/
├── stylecop.json                        ✅ Exists
├── .editorconfig                        ✅ Exists
├── ITSGrules.ruleset                    ✅ Exists
└── VDEK.DCSP.WebApi/
    └── VDEK.DCSP.WebApi.csproj          ✅ Has StyleCop.Analyzers
```

---

## StyleCop Rule Categories (Common Warnings)

```
SA1116 - Split parameters should start on line after declaration
SA1117 - Parameters should be on same line or separate lines
SA1118 - Parameter should not span multiple lines
SA1309 - Field names should not begin with underscore
SA1310 - Field names should not contain underscore
SA1600 - Elements should be documented (missing /// comments)
SA1601 - Partial elements should be documented
SA1602 - Enumeration items should be documented
```

**Configuration**: Control each with `.editorconfig`:
```editorconfig
[*.cs]
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1600.severity = none
```

---

## What Each File Does

### StyleCop.Analyzers Package (.csproj)
- Adds analyzer to C# compiler
- Detects style violations and reports them

### stylecop.json
- **ENABLES** StyleCop rules and sets configuration
- Without it: ALL rules are disabled (default behavior)
- Sets things like company name for doc rules, using directive placement

### .editorconfig
- Sets severity: error / warning / suggestion / none
- Works ONLY if `EnableEditorConfigSupport=true` in OmniSharp

### OmniSharp LSP config (Neovim)
- Tells OmniSharp to RUN the analyzers
- Without `EnableAnalyzersSupport=true`: Analyzers are skipped
- Tells OmniSharp to report diagnostics to editor

### ruleset file (optional)
- Alternative to .editorconfig for setting rule severity
- DCSRE uses both: `ITSGrules.ruleset` + `.editorconfig`

---

## Minimal Working Example

**That would definitely show StyleCop warnings:**

### VDEK.DCSP.WebApi.csproj
```xml
<ItemGroup>
  <PackageReference Include="StyleCop.Analyzers" Version="1.1.118">
    <PrivateAssets>all</PrivateAssets>
    <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
  </PackageReference>
  <AdditionalFiles Include="..\stylecop.json" Link="stylecop.json" />
</ItemGroup>
```

### Backend/stylecop.json
```json
{
  "$schema": "https://raw.githubusercontent.com/DotNetAnalyzers/StyleCopAnalyzers/master/StyleCop.Analyzers/StyleCop.Analyzers/Settings/stylecop.schema.json",
  "settings": {
    "documentationRules": { "companyName": "ITSG" }
  }
}
```

### Backend/.editorconfig
```editorconfig
root = true
[*.cs]
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1117.severity = warning
```

### Neovim init.lua
```lua
require('lspconfig').omnisharp.setup({
  cmd = { 'dotnet', vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll', '-s', '/mnt/c/.../Backend' },
  settings = {
    RoslynExtensionsOptions = { EnableAnalyzersSupport = true, AnalyzeOpenDocumentsOnly = false },
    FormattingOptions = { EnableEditorConfigSupport = true },
  },
})
```

**Then**: Open C# file → wait for OmniSharp → see StyleCop warnings ✅

---

## Diagnosis Flow

```
❓ No StyleCop warnings in Neovim?

  1️⃣ Does `dotnet build` show warnings?
     NO  → StyleCop.Analyzers package missing from .csproj
     YES → Go to step 2

  2️⃣ Is OmniSharp running?
     NO  → Configure LSP and restart Neovim
     YES → Go to step 3

  3️⃣ Is EnableAnalyzersSupport = true?
     NO  → Add to Neovim config, restart OmniSharp
     YES → Go to step 4

  4️⃣ Are rules set to "none" in .editorconfig?
     YES → Change severity to "warning" or "error"
     NO  → Restart OmniSharp completely
          (pkill -f omnisharp; open file again)
```

---

## Quick Fix Commands

```bash
# 1. Clear everything and rebuild
pkill -f omnisharp
rm -rf ~/.cache/nvim/luac/
rm -rf ~/.local/state/nvim/swap/*.swp
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
dotnet restore --force-evaluate --no-cache
dotnet build

# 2. Verify warnings appear
# Check output for "SA1116", "SA1117", etc.

# 3. Restart Neovim
# - Exit: :qa!
# - Reopen C# file
# - Check :LspInfo
# - Warnings should appear
```

---

## Key Insight

**StyleCop.Analyzers must be told to run via OmniSharp settings.**

Even if everything is configured perfectly:
- ✅ Package installed
- ✅ stylecop.json configured
- ✅ .editorconfig set up
- ✅ Project builds

**WITHOUT** `EnableAnalyzersSupport = true` in OmniSharp config → **ZERO warnings appear**

This is the most commonly missed setting.

---

## Files to Check/Edit

For StyleCop warnings to work in Neovim:

1. ✅ Already OK in DCSRE:
   - `/mnt/c/.../DCSRE/Sources/Backend/VDEK.DCSP.WebApi/VDEK.DCSP.WebApi.csproj` (has package)
   - `/mnt/c/.../DCSRE/Sources/Backend/stylecop.json` (has config)
   - `/mnt/c/.../DCSRE/Sources/Backend/.editorconfig` (has rules)

2. ❌ NEEDS TO BE CONFIGURED:
   - `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/init.lua` (no LSP config yet)

---

## One-Command Diagnostic

```bash
# This tells you EXACTLY what's missing
echo "=== Checking StyleCop Setup ===" && \
grep -l "StyleCop.Analyzers" /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/**/*.csproj | wc -l | xargs echo "Projects with StyleCop:" && \
test -f /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/stylecop.json && echo "✓ stylecop.json found" || echo "✗ stylecop.json missing" && \
test -f /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/.editorconfig && echo "✓ .editorconfig found" || echo "✗ .editorconfig missing" && \
ps aux | grep omnisharp | grep -v grep >/dev/null && echo "✓ OmniSharp running" || echo "✗ OmniSharp not running" && \
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend && dotnet build 2>&1 | grep -c "SA" | xargs echo "Warnings in build:"
```

---

## See Also

- `STYLECOP_ANALYZERS_CHECKLIST.md` - Detailed requirements
- `LSP_CONFIGURATION_EXAMPLES.lua` - Complete Neovim LSP config examples
- `CLAUDE.md` - Full project documentation
