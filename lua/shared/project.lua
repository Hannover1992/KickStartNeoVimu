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

-- Erkennt das aktuelle Projekt und setzt alle vim.g.project_* Globals.
-- Muss VOR lazy.setup() aufgerufen werden!
-- Verifiziert: init.lua Zeilen 229–268
function M.detect()
  local cwd = vim.fn.getcwd()
  vim.g.project_name = 'UNKNOWN'

  if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
    -- CENCOCD Projekt
    vim.g.project_name = 'CENCOCD'
    local base = platform.is_windows
      and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco'
      or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco'
    vim.g.project_backend         = base .. '/src/Core/CenCoCo.Core.API'
    vim.g.project_frontend        = base .. '/src/Core/CenCoCo.Core.Blazor'
    vim.g.project_webhost         = base .. '/src/Core/CenCoCo.Core.API'
    vim.g.project_docker_root     = base .. '/src'
    vim.g.project_docker_root_windows = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco\\src'
    vim.g.project_git_base        = 'origin/main'
    vim.g.project_launch_profile  = 'https'
    vim.g.project_root_windows    = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco'
    vim.g.project_root_wsl        = '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco'
    vim.g.project_tfs_commit_url  = nil
    vim.g.project_pr_url          = nil

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
