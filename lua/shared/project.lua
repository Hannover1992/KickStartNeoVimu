-- lua/shared/project.lua
-- Projekt-Erkennung (CENCOCD / DCSRE / UNKNOWN) und Setzen von vim.g.project_*
-- Basiert auf IST-Code Zeilen 202–268 (verifiziert via Spot-Check)
-- Bug B-001 Fix: project_root_windows auf WSL2 nutzt jetzt platform.wsl_to_windows()

local M = {}
local platform = require('shared.platform')

-- Findet den DCSRE-Root-Ordner ausgehend von einem Pfad.
-- Sucht aufwärts nach einem Ordner der "Sources" enthält.
-- Verifiziert: init.lua Zeilen 203–227
---@param path string  Startpfad (z.B. cwd), Forward- oder Backslash
---@return string|nil  Normalisierter Pfad (Forward-Slashes) oder nil
function M.find_dcsre_root(path)
  path = path:gsub('\\', '/')

  -- Strategie 1: Pattern-Match auf .../DCSRE.../Sources/...
  local root = path:match('(.*/DCSRE[^/]*)/Sources')
  if root and vim.fn.isdirectory(root .. '/Sources') == 1 then
    return root
  end

  -- Strategie 2: Aufwärts suchen
  local check_path = path
  while check_path and #check_path > 3 do
    if vim.fn.isdirectory(check_path .. '/Sources') == 1 then
      return check_path
    end
    local nested = check_path .. '/DCSRE'
    if vim.fn.isdirectory(nested .. '/Sources') == 1 then
      return nested
    end
    check_path = check_path:match('(.+)/[^/]+$')
  end
  return nil
end

-- Findet den OmniCommand-Worktree-Root ausgehend von einem Pfad.
-- Worktree-Struktur: Documents/Projekt/OmniCommand/<worktree-name>/  (z.B. OmniCommand, OmniCommand2)
---@param path string  Startpfad (z.B. cwd), Forward- oder Backslash
---@return string|nil  Normalisierter Pfad (Forward-Slashes) oder nil
function M.find_omnicommand_root(path)
  path = path:gsub('\\', '/')

  -- Strategie 1: Pattern auf .../Documents/Projekt/OmniCommand/<worktree>/...
  local root = path:match('(.*/Documents/Projekt/OmniCommand/[^/]+)')
  if root then
    return root
  end

  -- Strategie 2: Aufwaerts suchen — Parent muss "OmniCommand" sein (Container)
  local check_path = path
  while check_path and #check_path > 3 do
    local parent = check_path:match('(.+)/[^/]+$')
    if parent and parent:match('/Documents/Projekt/OmniCommand$') then
      return check_path
    end
    check_path = parent
  end
  return nil
end

-- Findet den CenCoCo-Worktree-Root ausgehend von einem Pfad.
-- Worktree-Struktur: Kluger/cencoco/<worktree-name>/  (z.B. cencoco, 88-E2E_Analyse, BL-XXX)
-- Container `Kluger/cencoco/` ist eindeutig genug — kein src/-Marker noetig
-- (Branches koennen unterschiedliche Layouts haben, z.B. Doku-only-Branches).
---@param path string  Startpfad (z.B. cwd), Forward- oder Backslash
---@return string|nil  Normalisierter Pfad (Forward-Slashes) oder nil
function M.find_cencoco_root(path)
  path = path:gsub('\\', '/')

  -- Strategie 1: Pattern auf .../Kluger/cencoco/<worktree>/...
  local root = path:match('(.*/Kluger/cencoco/[^/]+)')
  if root then
    return root
  end

  -- Strategie 2: Aufwaerts — Parent muss "Kluger/cencoco" sein (Container)
  local check_path = path
  while check_path and #check_path > 3 do
    local parent = check_path:match('(.+)/[^/]+$')
    if parent and parent:match('/Kluger/cencoco$') then
      return check_path
    end
    check_path = parent
  end
  return nil
end

-- Erkennt das aktuelle Projekt und setzt alle vim.g.project_* Globals.
-- Muss VOR lazy.setup() aufgerufen werden!
-- Verifiziert: init.lua Zeilen 229–268
function M.detect()
  local cwd = vim.fn.getcwd()
  vim.g.project_name = 'UNKNOWN'

  -- WICHTIG: Reihenfolge ist spezifisch → allgemein.
  -- OmniCommand zuerst, weil Pfade wie .../DCSRE_Azure/OmniCommand/ sonst
  -- als DCSRE fehl-matchen würden (Schweizer-Uhrmacher PL-P).
  if cwd:match('OmniCommand') then
    -- OMNICOMMAND Projekt — Worktree-Root dynamisch finden
    -- Container: Documents/Projekt/OmniCommand/, Worktrees: OmniCommand/, OmniCommand2/, BL-XXX/
    local oc_root = M.find_omnicommand_root(cwd)
    if oc_root then
      vim.g.project_name = 'OMNICOMMAND'
      vim.g.project_git_base = 'origin/main'
      vim.g.project_tfs_commit_url = nil
      vim.g.project_pr_url         = nil
      if platform.is_windows then
        vim.g.project_root_windows = platform.to_windows_path(oc_root)
      else
        vim.g.project_root_windows = platform.wsl_to_windows(oc_root)
      end
      vim.g.project_root_wsl = oc_root:gsub('^C:', '/mnt/c'):gsub('\\', '/')
    end

  elseif cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
    -- CENCOCD Projekt — Worktree-Root dynamisch finden
    -- Struktur: Kluger/cencoco/<worktree-name>/  (z.B. cencoco2, BL-XXX-feature, ...)
    local cencoco_root = M.find_cencoco_root(cwd)
    if cencoco_root then
      vim.g.project_name            = 'CENCOCD'
      vim.g.project_backend         = cencoco_root .. '/src/Core/CenCoCo.Core.API'
      vim.g.project_frontend        = cencoco_root .. '/src/Core/CenCoCo.Core.Blazor'
      vim.g.project_webhost         = cencoco_root .. '/src/Core/CenCoCo.Core.API'
      vim.g.project_docker_root     = cencoco_root .. '/src'
      vim.g.project_git_base        = 'origin/main'
      vim.g.project_launch_profile  = 'https'
      if platform.is_windows then
        vim.g.project_root_windows        = platform.to_windows_path(cencoco_root)
        vim.g.project_docker_root_windows = platform.to_windows_path(cencoco_root) .. '\\src'
      else
        vim.g.project_root_windows        = platform.wsl_to_windows(cencoco_root)
        vim.g.project_docker_root_windows = platform.wsl_to_windows(cencoco_root) .. '\\src'
      end
      vim.g.project_root_wsl        = cencoco_root:gsub('^C:', '/mnt/c'):gsub('\\', '/')
      vim.g.project_tfs_commit_url  = nil
      vim.g.project_pr_url          = nil
    end

  elseif cwd:match('DCSRE') then
    -- DCSRE Projekt — Root dynamisch finden
    local dcsre_root = M.find_dcsre_root(cwd)
    if dcsre_root then
      vim.g.project_name            = 'DCSRE'
      vim.g.project_backend         = dcsre_root .. '/Sources/Backend'
      vim.g.project_backend_windows = platform.to_windows_path(dcsre_root) .. '\\Sources\\Backend'
      vim.g.project_frontend        = dcsre_root .. '/Sources/Frontend'
      vim.g.project_webhost         = dcsre_root .. '/Sources/Backend/VDEK.DCSP.WebHost'
      vim.g.project_docker_root     = dcsre_root .. '/Sources'
      vim.g.project_docker_root_windows = platform.to_windows_path(dcsre_root) .. '\\Sources'
      vim.g.project_git_base        = 'origin/develop'
      vim.g.project_launch_profile  = 'WebHost'
      -- BUG B-001 FIX: Auf WSL2 muss dcsre_root (Forward-Slash) via wsl_to_windows()
      -- konvertiert werden statt einfachem gsub('/', '\\').
      -- Vorher: dcsre_root:gsub('/', '\\') → auf WSL2: \mnt\c\... (FALSCH!)
      -- Jetzt:  platform.to_windows_path(dcsre_root) auf Windows (korrekt)
      --         platform.wsl_to_windows(dcsre_root) auf WSL2 → C:\... (KORREKT!)
      if platform.is_windows then
        vim.g.project_root_windows  = platform.to_windows_path(dcsre_root)
      else
        vim.g.project_root_windows  = platform.wsl_to_windows(dcsre_root)
      end
      vim.g.project_root_wsl        = dcsre_root:gsub('^C:', '/mnt/c'):gsub('\\', '/')
      vim.g.project_tfs_commit_url  = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/commit/%s'
      vim.g.project_pr_url          = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/pullrequest/%s?path=%s'
    end
  end
end

return M
