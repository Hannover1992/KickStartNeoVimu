# QUICK FIX: OmniSharp StyleCop Warnings Not Showing

## TL;DR - 5 Minute Solution ⚡

```bash
# 1. Create config file
mkdir -p ~/.omnisharp
cat > ~/.omnisharp/omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
EOF

# 2. Kill OmniSharp
pkill -f omnisharp

# 3. Restart Neovim
nvim /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebApi/Controllers/UserController.cs

# 4. Verify it works
ps aux | grep omnisharp | grep -v grep | grep -i enableAnalyzers
```

**That's it!** StyleCop warnings should now appear.

---

## Why This Works

- **OmniSharp reads `~/.omnisharp/omnisharp.json` automatically**
- **File settings override Neovim LSP config** (highest priority)
- **No changes needed to init.lua** (zero risk)
- **Works with ANY editor** (VS Code, Vim, Emacs)

---

## Alternative: Project-Level Config (Recommended for Teams)

```bash
# Create config in project root (commit to Git!)
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
cat > omnisharp.json << 'EOF'
{
  "RoslynExtensionsOptions": {
    "enableAnalyzersSupport": true,
    "enableImportCompletion": true,
    "analyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
EOF

# Commit to Git
git add omnisharp.json
git commit -m "Enable OmniSharp analyzer support for StyleCop warnings"
```

**Benefits:**
- ✅ Entire team gets StyleCop warnings
- ✅ Version controlled
- ✅ Project-specific (doesn't affect other projects)

---

## Verification Checklist

### ✅ Config file exists
```bash
ls -la ~/.omnisharp/omnisharp.json
# OR
ls -la /mnt/c/.../Backend/omnisharp.json
```

### ✅ OmniSharp process uses the config
```bash
ps aux | grep omnisharp | grep -v grep
# Should show: RoslynExtensionsOptions:enableAnalyzersSupport=true
```

### ✅ LSP logs show analyzer loading
```bash
tail -100 ~/.local/state/nvim/lsp.log | grep -i "analyzer\|stylecop"
# Should show analyzer-related messages
```

### ✅ StyleCop warnings appear in Neovim
Open `UserController.cs` and check lines:
- 56-57, 78-79, 110-111, 152-153, 190-191, 241-243
- Should see warnings like SA1116, SA1117

---

## Troubleshooting

### Still no warnings?

**1. Check StyleCop package is installed:**
```bash
cd /mnt/c/.../Backend
grep -r "StyleCop.Analyzers" *.csproj
# Should show: <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
```

**2. Check .editorconfig exists:**
```bash
ls -la /mnt/c/.../Backend/.editorconfig
```

**3. Restart LSP in Neovim:**
```vim
:LspRestart
:e %
```

**4. Clear LSP cache:**
```bash
rm -rf ~/.cache/nvim/lsp/
pkill -f omnisharp
```

---

## Other Approaches (If This Fails)

See detailed analysis in: `OMNISHARP_ALTERNATIVE_APPROACHES.md`

1. **Manual OmniSharp Installation** - Full control, no Mason
2. **csharp.nvim Plugin** - Zero-config, includes debugger
3. **omnisharp.json** - ⭐ Recommended (you're here!)

---

## Quick Script

Run the automated setup script:

```bash
# Global config (all projects)
bash setup_omnisharp_config.sh global

# Project-level config (DCSRE only)
bash setup_omnisharp_config.sh project
```

---

## Summary

**Problem:** StyleCop warnings not showing in Neovim
**Root Cause:** OmniSharp not loading analyzer settings from Neovim config
**Solution:** Use `omnisharp.json` file (OmniSharp's official config method)
**Time:** 5 minutes
**Risk:** Zero (doesn't touch Neovim config)

**Result:** ✅ StyleCop warnings appear, team benefits, editor-agnostic solution!
