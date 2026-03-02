# Keybinding Update - Documentation Index

**Date**: February 9, 2026
**Status**: Complete and Deployed
**Commit**: 4c8cedb

## Overview

All `<leader>r*` keybindings in Neovim init.lua have been updated to include actual command descriptions. This makes keybindings self-documenting and searchable.

### What Changed

- **27 keybindings** updated with actual command descriptions
- Format: `[Description] | actual command`
- Deployed to Windows Neovim and WSL2 Neovim
- Committed to git with comprehensive commit message

### Example

**Before:**
```
<leader>rbw → [R]un [B]ackend [W]ebhost
```

**After:**
```
<leader>rbw → [R]un [B]ackend [W]ebhost | dotnet run
```

---

## Documentation Files

### 1. **KEYBINDING_DESCRIPTIONS_UPDATE.md**
Complete reference documentation

- All 27 changes listed by category
- Before/after for each change
- Benefits explained
- How to verify changes
- File locations

**Use this for:** Detailed information about what was changed and why

### 2. **BEFORE_AFTER_COMPARISON.md**
Visual side-by-side comparison

- Real examples from each category
- Pattern explanation
- How to view in Neovim
- Why it matters (6 benefits)
- Keyboard tips

**Use this for:** Understanding the improvements visually

### 3. **KEYBINDING_REFERENCE_CARD.txt**
Quick lookup table

- All 27 keybindings organized by category
- Quick command patterns reference
- Troubleshooting tips
- Config location reference
- Keyboard usage guide

**Use this for:** Fast lookup of specific keybindings

---

## Keybindings Updated (27 Total)

### Backend Operations (5)
- `<leader>rbw` → dotnet run
- `<leader>rbs` → dotnet run --project VDEK.DCSP.Setup
- `<leader>rbb` → dotnet clean && dotnet build
- `<leader>rbt` → dotnet test --filter FullyQualifiedName~{file}
- `<leader>rbu` → dotnet test --filter Category!=Database&Storage&Docker

### Frontend Operations (3)
- `<leader>rfw` → npm start / dotnet run
- `<leader>rfb` → npm run build / docker compose build
- `<leader>rft` → npm test

### E2E Tests (3)
- `<leader>reg` → npm run cypress:run:gesamtsystemtest
- `<leader>res` → npm run cypress:run:systemtest
- `<leader>reo` → npm run cypress:open:systemtest

### Docker Operations (8)
- `<leader>rDi` → docker-up.ps1 / docker compose up
- `<leader>rDa` → docker-up.ps1 -Profile all
- `<leader>rDr` → docker compose down
- `<leader>rDR` → docker compose down -v --rmi all
- `<leader>rdf` → docker compose build frontend
- `<leader>rdF` → docker compose up frontend
- `<leader>rdb` → docker compose build backend
- `<leader>rdB` → docker compose up backend

### Integration Tests (2)
- `<leader>rim` → dotnet test --filter DicMockServer
- `<leader>rid` → dotnet test --filter !DicMockServer

### Manual Test Runner (2)
- `<leader>rmd` → dotnet run --project ManualTestRunner --launch-profile docker
- `<leader>rml` → dotnet run --project ManualTestRunner --launch-profile https

### Git Operations (3)
- `<leader>rc` → Open in TFS browser (from clipboard)
- `<leader>rp` → git push (Windows VPN)
- `<leader>rP` → git pull (Windows VPN)

### Setup Scripts (1)
- `<leader>rsc` → new-research-project.ps1

---

## File Locations

### Repository
- **Master Copy**: `C:\Users\Administrator\Documents\Projekt\KickStartNeoVim\init.lua`
- **Git Commit**: `4c8cedb` on `master` branch

### Neovim Configs (Auto-Synced)
- **Windows**: `C:\Users\Administrator\AppData\Local\nvim\init.lua`
- **WSL2**: `~/.config/nvim/init.lua`

---

## How to Use

### In Neovim

```vim
" See all <leader>r keybindings with descriptions
:map <leader>r

" Search for specific commands
:Telescope keymaps
" Type: "dotnet", "docker", "npm", "git"

" Show all keybindings
:map

" Help on keybindings
:help keybindings
```

### From Command Line

**Windows:**
```powershell
grep "desc = '\[R\]un" "C:\Users\Administrator\AppData\Local\nvim\init.lua"
```

**WSL2:**
```bash
grep "desc = '\[R\]un" ~/.config/nvim/init.lua
```

---

## Deployment Status

✅ **Windows Neovim**
- Path: `C:\Users\Administrator\AppData\Local\nvim\init.lua`
- Status: Updated and active

✅ **WSL2 Neovim**
- Path: `~/.config/nvim/init.lua`
- Status: Updated and active

✅ **Git Repository**
- Commit: `4c8cedb`
- Branch: `master`
- Status: Ready to share/push

---

## Next Steps

1. **Restart Neovim** completely
2. **Press `<leader>`** to see updated keybinding descriptions
3. **Try**: `:Telescope keymaps` and search for "dotnet" or "docker"
4. **Read**: `KEYBINDING_REFERENCE_CARD.txt` for quick lookup

---

## For Your Team

### Sharing the Changes

1. **Pull the latest**: `git pull origin master` (includes commit `4c8cedb`)
2. **Share documentation**:
   - `KEYBINDING_DESCRIPTIONS_UPDATE.md` (detailed)
   - `BEFORE_AFTER_COMPARISON.md` (visual)
   - `KEYBINDING_REFERENCE_CARD.txt` (quick reference)

3. **They'll see** updated descriptions immediately after restarting Neovim

---

## Benefits

✓ **Self-Documenting**: No need to read code to understand commands

✓ **Searchable**: Use Telescope to find keybindings by command

✓ **Consistent**: All 27 follow the same format

✓ **Clear Distinctions**: Similar commands clearly differentiated (e.g., Mock vs DB tests)

✓ **Team Onboarding**: New developers learn commands instantly

✓ **Time Saving**: No more "what's the keybinding for...?" questions

---

## Pattern Format

All descriptions follow this pattern:

```
[Brief Description] | actual-command [with arguments]
```

Examples:
- `[R]un [B]ackend [W]ebhost | dotnet run`
- `[R]un [I]ntegration [M]ock | dotnet test --filter DicMockServer`
- `[R]un [D]ocker [I]nfrastructure | docker-up.ps1 / docker compose up`

The pipe `|` separates the user-friendly description from the technical command.

---

## Statistics

- **Total Keybindings Updated**: 27
- **Categories Covered**: 8
- **Lines Modified in init.lua**: 287
- **Insertions**: 511
- **Deletions**: 86
- **Documentation Files Created**: 4
- **Total Documentation Size**: ~24.6 KB

---

## Git Information

**Commit**: `4c8cedb`
**Author**: Patryk Krzyzanski <Patryk.Krzyzanski@kluger.net>
**Date**: February 9, 2026, 1:15 PM
**Branch**: master

**Message**:
```
feat: Add actual command descriptions to all <leader>r* keybindings

Updated 27 keybinding descriptions to include the actual commands they execute,
following the pattern: [Description] | actual command

Changes include:
- Backend: dotnet run, build, test commands
- Frontend: npm/dotnet and docker commands
- E2E: cypress commands
- Docker: infrastructure, build, and compose commands
- Integration tests: dotnet test filters
- Manual test runner: launch profiles
- Git: push, pull, commit browser
- Setup scripts: new-research-project.ps1

Benefits:
- Self-documenting keybindings
- Searchable in Telescope (:Telescope keymaps)
- Clear distinction between similar commands
- Easier onboarding for new team members

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Troubleshooting

**Keybindings not showing updated descriptions?**
1. Restart Neovim completely
2. Check config file: `:edit ~/.config/nvim/init.lua`
3. Verify changes: `:checkhealth`

**Want to search for specific command?**
```vim
:Telescope keymaps
" Then type: dotnet, docker, npm, git, etc.
```

**Want to see all keybindings?**
```vim
:map                   " All mappings
:map <leader>r         " Just backend/run mappings
:map <leader>R         " Capitalized mappings
```

---

## Related Files in Repository

- `init.lua` - Main Neovim configuration (159 KB)
- `KEYBINDING_DESCRIPTIONS_UPDATE.md` - Detailed documentation (6.1 KB)
- `BEFORE_AFTER_COMPARISON.md` - Visual examples (4.8 KB)
- `KEYBINDING_REFERENCE_CARD.txt` - Quick lookup (9.7 KB)
- `README_KEYBINDING_UPDATE.md` - This file

---

**Last Updated**: February 9, 2026
**Status**: COMPLETE AND DEPLOYED
**Ready to Use**: YES
