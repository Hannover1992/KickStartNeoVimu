---
status: final
query_status: skipped (empty collection)
---
# CLEANCODE S3_Project

## Implementiert
- lua/shared/project.lua (~80 LOC): find_dcsre_root() + detect() + Bug B-001 Fix
- init.lua: Project Detection Block ersetzt durch `require('shared.project').detect()`

## Bug B-001 Fix (KRITISCH)
Vorher: `vim.g.project_root_windows = dcsre_root:gsub('/', '\\')`
→ Auf WSL2: `/mnt/c/...` → `\mnt\c\...` (FALSCH! Backslash-Pfad statt C:\)

Nachher:
```lua
if platform.is_windows then
  vim.g.project_root_windows = platform.to_windows_path(dcsre_root)
else
  vim.g.project_root_windows = platform.wsl_to_windows(dcsre_root)
end
```
→ Auf WSL2: `/mnt/c/DCSRE/...` → `C:\DCSRE\...` (KORREKT!)
→ Auf Windows: `C:/DCSRE/...` → `C:\DCSRE\...` (KORREKT!)

## Design-Entscheidungen
- detect() hat KEINEN Rückgabewert — setzt vim.g.* als Side-Effect (intentional)
- find_dcsre_root() ist public (testbar via project_spec.lua)
- cwd wird INTERN in detect() geholt (nicht mehr als init.lua-Variable)

## exit_report
status: final
query_status: skipped (empty collection)
