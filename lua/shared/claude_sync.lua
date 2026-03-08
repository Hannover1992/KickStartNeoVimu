-- lua/shared/claude_sync.lua
-- Synct projekt-spezifisches .claude aus AgentsArchive in den Projekt-Root.
-- Routing: DCSRE → .claude_DCSRE | CENCOCD → .claude_CenCoCo
-- Wird beim Start (init_windows.lua) nach project.detect() aufgerufen.
--
-- Wie /_obsidianSync: Pfad-Pattern → Vault, nur hier: Project-Name → .claude_Variant

local M = {}

local ARCHIVE_BASE = 'C:\\Users\\Administrator\\Documents\\Projekt\\AgentsArchive'

-- Routing-Tabelle: vim.g.project_name → .claude_Variant im AgentsArchive
local ROUTING = {
  DCSRE   = ARCHIVE_BASE .. '\\.claude_DCSRE',
  CENCOCD = ARCHIVE_BASE .. '\\.claude_CenCoCo',
}

-- Synct .claude_X → {project_root}\.claude via robocopy (non-blocking background)
-- robocopy Exit-Codes 0-7 = Success (Bit-Flags, nicht klassische Exit-Codes)
function M.sync()
  local project_name = vim.g.project_name
  local project_root = vim.g.project_root_windows

  if not project_root or not project_name or project_name == 'UNKNOWN' then
    return
  end

  local source = ROUTING[project_name]
  if not source then
    return  -- Kein Mapping für dieses Projekt
  end

  -- Abbruch wenn Quell-Ordner nicht existiert (noch nicht angelegt)
  if vim.fn.isdirectory(source) == 0 then
    vim.notify('[claude_sync] Quelle fehlt: ' .. source, vim.log.levels.WARN)
    return
  end

  local target = project_root .. '\\.claude'

  -- /E = Unterverzeichnisse inkl. leere | /XO = ältere Ziel-Dateien nicht überschreiben
  -- /NJH /NJS /NFL /NDL = stille Ausgabe | /R:0 = kein Retry bei Fehler
  local cmd = string.format(
    'robocopy "%s" "%s" /E /XO /NJH /NJS /NFL /NDL /R:0',
    source, target
  )

  -- PowerShell minimiert, gibt kein Fenster
  vim.fn.jobstart(
    { 'powershell.exe', '-WindowStyle', 'Hidden', '-Command', cmd },
    { detach = true }
  )
end

-- Manueller Trigger: :ClaudeSync oder <leader>cs
-- Gibt Feedback (notify) ob sync lief
function M.sync_with_notify()
  local project_name = vim.g.project_name
  local project_root = vim.g.project_root_windows

  if not project_root or not project_name or project_name == 'UNKNOWN' then
    vim.notify('[claude_sync] Kein Projekt erkannt (UNKNOWN)', vim.log.levels.WARN)
    return
  end

  local source = ROUTING[project_name]
  if not source then
    vim.notify('[claude_sync] Kein Routing für: ' .. project_name, vim.log.levels.WARN)
    return
  end

  if vim.fn.isdirectory(source) == 0 then
    vim.notify('[claude_sync] Quelle fehlt: ' .. source, vim.log.levels.ERROR)
    return
  end

  local target = project_root .. '\\.claude'
  local cmd = string.format(
    'robocopy "%s" "%s" /E /XO /NJH /NJS /NFL /NDL /R:0',
    source, target
  )

  vim.fn.jobstart(
    { 'powershell.exe', '-WindowStyle', 'Hidden', '-Command', cmd },
    {
      detach = false,
      on_exit = function(_, code)
        -- robocopy: 0-7 = success (bit flags)
        if code <= 7 then
          vim.notify(
            string.format('[claude_sync] %s → %s\\  (%s)', project_name, target, ARCHIVE_BASE:match('[^\\]+$') .. '\\.claude_' .. project_name:sub(1,1) .. project_name:sub(2):lower()),
            vim.log.levels.INFO
          )
        else
          vim.notify('[claude_sync] Fehler (Exit ' .. code .. '): ' .. source, vim.log.levels.ERROR)
        end
      end,
    }
  )
end

return M
