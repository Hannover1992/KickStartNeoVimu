-- lua/shared/platform.lua
-- Plattform-Erkennung und systemabhängige Konstanten.
-- Keine Neovim-State-Abhängigkeiten außer vim.fn.has (sicher bei module load time).

local M = {}

-- Plattform-Flag: true auf Windows Neovim, false auf WSL2/Linux Neovim
M.is_windows = vim.fn.has('win32') == 1

-- Chrome executable path (für Markdown-Preview und URL-öffnen)
-- Verifiziert: Zeilen 680–694 (Markdown Preview) und 858–863 (Obsidian Follow Link)
M.chrome_path = M.is_windows
  and 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  or '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'

-- Chrome-Aufruf als Shell-Kommando (inkl. Anführungszeichen für Leerzeichen im Pfad)
M.chrome_cmd = M.is_windows
  and '"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"'
  or '"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"'

-- URL in System-Browser öffnen
-- Verifiziert: Zeilen 858–863 (Obsidian), 934 (Graph View), 4436 (TFS)
---@param url string
function M.open_url(url)
  if M.is_windows then
    vim.fn.system('powershell.exe -Command "Start-Process \'' .. url .. '\'"')
  else
    vim.fn.system('xdg-open "' .. url .. '"')
  end
end

-- Pfad-Utility: Forward-Slashes → Backslashes (für PowerShell-Aufrufe)
---@param path string
---@return string
function M.to_windows_path(path)
  return path:gsub('/', '\\')
end

-- Pfad-Utility: WSL-Pfad → Windows-Pfad
-- /mnt/c/foo → C:\foo
-- Hinweis: Nur nötig wenn path von WSL stammt (z.B. project_root_wsl → windows)
---@param wsl_path string
---@return string
function M.wsl_to_windows(wsl_path)
  return wsl_path:gsub('^/mnt/(%a)/', function(drive)
    return drive:upper() .. ':\\'
  end):gsub('/', '\\')
end

return M
