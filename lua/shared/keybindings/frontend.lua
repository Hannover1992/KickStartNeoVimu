-- lua/shared/keybindings/frontend.lua
-- [R]un [F]rontend* Keybindings: Dev-Server, Build, Test, Install
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität

-- Run Frontend: Start dev server (web)
vim.keymap.set('n', '<leader>rfw', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; dotnet run --launch-profile https"'
  else
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; npm start"'
  end
  local frontend = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 21, -- Separate terminal ID for frontend
  })
  frontend:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Frontend dev server...', vim.log.levels.INFO)
end, { desc = '[R]un [F]rontend [W]eb | CENCOCD: dotnet run --launch-profile https | DCSRE: npm start' })

-- Run Frontend Build: Build production app
vim.keymap.set('n', '<leader>rfb', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; docker compose build frontend"'
  else
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; npm run build"'
  end
  local build = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  build:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Building Frontend...', vim.log.levels.INFO)
end, { desc = '[R]un [F]ront [B]uild | npm run build / docker compose build' })

-- Run Frontend Unit-Tests: Jest / NX test
-- (Fruehere Bindung <leader>rft → renamed zu rfu; 't' ist mehrdeutig, 'u' = Unit ist klarer.
--  E2E ist <leader>re*, Unit ist <leader>rfu.)
vim.keymap.set('n', '<leader>rfu', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; npm test"',
    direction = 'horizontal',
    close_on_exit = false,
  })
  test:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Running Frontend Unit-Tests (Jest)...', vim.log.levels.INFO)
end, { desc = '[R]un [F]ront [U]nit-Tests | npm test (Jest)' })

-- Run Frontend Install: npm install
vim.keymap.set('n', '<leader>rfi', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local install = Terminal:new({
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; npm install"',
    direction = 'horizontal',
    close_on_exit = false,
  })
  install:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Running npm install...', vim.log.levels.INFO)
end, { desc = '[R]un [F]ront [I]nstall | npm install' })
