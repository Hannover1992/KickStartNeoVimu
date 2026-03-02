-- lua/shared/keybindings/git.lua
-- Git Keybindings: rp (Push), rP (Pull), rc (TFS Browser), git diff helper, Windows path
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität

-- Helper function for git diff quickfix
local function git_diff_to_quickfix(base_ref, description)
  local handle = io.popen('git diff --name-status ' .. base_ref .. '..HEAD 2>/dev/null')
  if not handle then
    vim.notify('Git command failed - are you in a git repo?', vim.log.levels.ERROR)
    return
  end
  local result = handle:read('*a')
  handle:close()

  -- Parse files into quickfix format with git status
  local qf_list = {}
  local status_map = {
    M = 'Modified',
    A = 'Added',
    D = 'Deleted',
    R = 'Renamed',
    C = 'Copied',
    U = 'Unmerged',
  }

  for line in result:gmatch('[^\r\n]+') do
    local status, file = line:match('^(%S+)%s+(.+)$')
    if status and file then
      local status_text = status_map[status] or status
      table.insert(qf_list, { filename = file, lnum = 1, text = status_text })
    end
  end

  if #qf_list == 0 then
    vim.notify('No changed files found (' .. description .. ')', vim.log.levels.INFO)
    return
  end

  -- Set quickfix list and open
  vim.fn.setqflist(qf_list)
  vim.cmd('copen')
  vim.notify(string.format('Found %d changed files (%s)', #qf_list, description), vim.log.levels.INFO)
end

-- Quickfix: Show dirty files in current branch (vs upstream)
vim.keymap.set('n', '<leader>qd', function()
  git_diff_to_quickfix('@{upstream}', 'vs upstream')
end, { desc = '[Q]uickfix [d]irty files (vs upstream)' })

-- Quickfix: Show changed files vs project base branch (auto-detects project)
vim.keymap.set('n', '<leader>qD', function()
  git_diff_to_quickfix(vim.g.project_git_base, 'vs ' .. vim.g.project_git_base .. ' (' .. vim.g.project_name .. ')')
end, { desc = '[Q]uickfix vs [D]evelop/Main (project base)' })

-- Copy Windows path to clipboard
vim.keymap.set('n', '<leader>ypw', function()
  local current_file = vim.fn.expand('%:p')
  local windows_path

  if vim.fn.has('win32') == 1 then
    -- Windows Native: just normalize slashes
    windows_path = current_file:gsub('/', '\\')
  else
    -- WSL2: Convert /mnt/c/... to C:\...
    windows_path = current_file:gsub('/mnt/c/', 'C:\\'):gsub('/', '\\')
  end

  -- Copy to clipboard
  vim.fn.setreg('+', windows_path)
  vim.notify('Copied Windows path: ' .. windows_path, vim.log.levels.INFO)
end, { desc = '[Y]ank [P]ath [w]indows' })

-- Open commit in TFS browser (reads commit hash from clipboard)
vim.keymap.set('n', '<leader>rc', function()
  if not vim.g.project_tfs_commit_url then
    vim.notify('[' .. vim.g.project_name .. '] TFS commit URL not configured for this project', vim.log.levels.WARN)
    return
  end
  local commit_hash = vim.fn.getreg('+'):gsub('%s+', '') -- Get from clipboard, trim whitespace
  if commit_hash == '' then
    vim.notify('Clipboard is empty!', vim.log.levels.ERROR)
    return
  end
  local url = string.format(vim.g.project_tfs_commit_url, commit_hash)
  -- Open in Chrome (Windows) via PowerShell - runs in background, non-blocking
  local cmd = string.format([[powershell.exe -Command "Start-Process 'chrome.exe' -ArgumentList '--new-window', '%s'"]], url)
  vim.fn.jobstart(cmd, { detach = true }) -- Run async, non-blocking
  vim.notify('[' .. vim.g.project_name .. '] Opening commit in Chrome: ' .. commit_hash, vim.log.levels.INFO)
end, { desc = '[R]un [C]ommit | Open in TFS browser (from clipboard)' })

-- Open file in PR on Azure DevOps (reads PR number from register p)
vim.keymap.set('n', '<leader>rC', function()
  if not vim.g.project_pr_url then
    vim.notify('project_pr_url nicht konfiguriert für ' .. vim.g.project_name, vim.log.levels.ERROR)
    return
  end

  local pr_number = vim.fn.getreg('p'):gsub('%s+', '') -- Get from register p, trim whitespace
  if pr_number == '' or not pr_number:match('^%d+$') then
    vim.notify('PR-Nummer fehlt! Bitte zuerst in Register p kopieren ("py auf die Nummer)', vim.log.levels.ERROR)
    return
  end

  local file_path = vim.fn.expand('%:p') -- Get full path of current file
  -- Normalize path and get relative path from project root
  file_path = file_path:gsub('\\', '/')
  local project_root = vim.g.project_root_windows and vim.g.project_root_windows:gsub('\\', '/') or ''

  local relative_path = file_path:gsub('^' .. project_root:gsub('([%(%)%.%%%+%-%*%?%[%^%$])', '%%%1'), '')
  -- URL-encode the path (spaces, etc.)
  relative_path = relative_path:gsub(' ', '%%20')

  -- Build URL from config
  local url = string.format(vim.g.project_pr_url, pr_number, relative_path)

  -- Open in Chrome new window (via PowerShell for both WSL2 and Windows)
  local cmd = string.format([[powershell.exe -Command "Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--new-window', '%s'"]], url)
  vim.fn.jobstart(cmd, { detach = true })
  vim.notify('[' .. vim.g.project_name .. '] Opening PR #' .. pr_number .. ' at: ' .. relative_path, vim.log.levels.INFO)
end, { desc = '[R]un file in PR (TFS browser, PR# from register P)' })

-- Git Push (Windows PowerShell - VPN requirement)
vim.keymap.set('n', '<leader>rp', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local push = Terminal:new({
    cmd = 'powershell.exe -Command "cd ' .. vim.g.project_root_windows .. '; git push; pause"',
    direction = 'horizontal',
    close_on_exit = false, -- Keep terminal open to see output
  })
  push:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Git Push started...', vim.log.levels.INFO)
end, { desc = '[R]un [P]ush | git push (Windows VPN)' })

-- Git Pull (Windows PowerShell - VPN requirement)
vim.keymap.set('n', '<leader>rP', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local pull = Terminal:new({
    cmd = 'powershell.exe -Command "cd ' .. vim.g.project_root_windows .. '; git pull; pause"',
    direction = 'horizontal',
    close_on_exit = false, -- Keep terminal open to see output
  })
  pull:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Git Pull started...', vim.log.levels.INFO)
end, { desc = '[R]un [P]ull | git pull (Windows VPN)' })

-- Run .claude/ setup script (copies reusable agents/commands/scripts from OmniCommand)
-- Run Swagger: Generate swagger and client via PowerShell script (DCSRE only)
vim.keymap.set('n', '<leader>rS', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Swagger generation only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local root = vim.g.project_root_windows
  if not root then
    vim.notify('Could not determine project root', vim.log.levels.ERROR)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local swagger = Terminal:new({
    cmd = "powershell.exe -ExecutionPolicy Bypass -File \"" .. root .. "\\Sources\\Tools\\generate-swagger-and-client.ps1\"",
    direction = 'horizontal',
    close_on_exit = false,
  })
  swagger:toggle()
  vim.notify('[DCSRE] Generating Swagger & Client...', vim.log.levels.INFO)
end, { desc = '[R]un [S]wagger (capital S) | generate-swagger-and-client.ps1' })

vim.keymap.set('n', '<leader>rsc', function()
  local git_root = vim.fn.system('git rev-parse --show-toplevel'):gsub('%s+$', '')
  if vim.v.shell_error ~= 0 then
    vim.notify('Not in a git repository!', vim.log.levels.ERROR)
    return
  end
  -- Convert WSL path to Windows path for PowerShell
  local win_path = git_root:gsub('^/mnt/(%a)/', function(drive)
    return drive:upper() .. ':\\'
  end):gsub('/', '\\')
  local claude_dir = win_path .. '\\.claude'
  local script = 'C:\\Users\\Administrator\\Documents\\Work\\Code2\\DCSRE_Azure\\OmniCommand\\.claude\\new-research-project.ps1'
  local Terminal = require('toggleterm.terminal').Terminal
  local setup = Terminal:new({
    cmd = 'powershell.exe -ExecutionPolicy Bypass -File "' .. script .. '" -TargetPath "' .. win_path .. '"; pause',
    direction = 'horizontal',
    close_on_exit = false,
  })
  setup:toggle()
  vim.notify('.claude/ Setup gestartet → ' .. win_path, vim.log.levels.INFO)
end, { desc = '[R]un [S]cript [C]laude | new-research-project.ps1' })
