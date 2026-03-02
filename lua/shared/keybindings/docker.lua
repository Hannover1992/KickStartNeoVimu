-- lua/shared/keybindings/docker.lua
-- [R]un [D]ocker* Keybindings: Infrastructure, All, Down, Reset, Build, Up
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität

-- Docker Infrastructure: Start all infrastructure services (postgres, mongodb, minio, smtp4dev)
-- DCSRE uses PowerShell script with specific parameters, CENCOCD uses simple docker compose
vim.keymap.set('n', '<leader>rDi', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'DCSRE' then
    -- DCSRE: Use PowerShell script (needs Windows paths, must run from Sources dir)
    cmd = 'powershell.exe -ExecutionPolicy Bypass -Command "Set-Location \'' .. vim.g.project_docker_root_windows .. '\'; .\\docker-up.ps1 -EnvFile \\"./.env.noproxy\\" -Profile dev-backend -SkipTests; if ($?) { notify \'Docker Infra erfolgreich\' } else { notify \'Docker Infra fehlgeschlagen\' }"'
  else
    -- CENCOCD: Simple docker compose
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_docker_root .. '\'; docker compose up -d"'
  end
  local infra = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 22, -- Separate terminal ID for docker infra
  })
  infra:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Docker Infrastructure...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [I]nfrastructure | docker-up.ps1 / docker compose up' })

-- Docker All: Start ALL services (Profile=all) - DCSRE only
vim.keymap.set('n', '<leader>rDa', function()
  local Terminal = require('toggleterm.terminal').Terminal
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Docker All is only for DCSRE project', vim.log.levels.WARN)
    return
  end
  local cmd = 'powershell.exe -ExecutionPolicy Bypass -Command "Set-Location \'' .. vim.g.project_docker_root_windows .. '\'; .\\docker-up.ps1 -EnvFile \\"./.env.noproxy\\" -Profile all -SkipTests; if ($?) { notify \'Docker All erfolgreich\' } else { notify \'Docker All fehlgeschlagen\' }"'
  local infra = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 23, -- Separate terminal ID for docker all
  })
  infra:toggle()
  vim.notify('[DCSRE] Starting Docker ALL (full environment)...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [A]ll | docker-up.ps1 -Profile all' })

-- Docker Quick Down: Stop containers (keep volumes/images)
vim.keymap.set('n', '<leader>rDr', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'DCSRE' then
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_docker_root .. '\'; docker compose -p dcsp down"'
  else
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_docker_root .. '\'; docker compose down"'
  end
  local infra = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 22,
  })
  infra:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Quick Docker down (keeping data)...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [r]undown | docker compose down' })

-- Docker Full Reset: Stop + remove volumes + remove images (full cleanup)
vim.keymap.set('n', '<leader>rDR', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'DCSRE' then
    -- -v = remove volumes, --rmi all = remove all images
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_docker_root .. '\'; docker compose -p dcsp down -v --rmi all"'
  else
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_docker_root .. '\'; docker compose down -v --rmi all"'
  end
  local infra = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 22,
  })
  infra:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Full Docker RESET (deleting all data)...', vim.log.levels.WARN)
end, { desc = '[R]un [D]ocker [R]eset | docker compose down -v --rmi all' })

-- Docker Build Frontend (for projects using docker)
vim.keymap.set('n', '<leader>rdf', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local build = Terminal:new({
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; docker compose build frontend"',
    direction = 'horizontal',
    close_on_exit = false,
  })
  build:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Building Frontend (docker)...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [F]rontend build | docker compose build frontend' })

-- Docker Up Frontend (for projects using docker)
vim.keymap.set('n', '<leader>rdF', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local start = Terminal:new({
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; docker compose up frontend"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 11, -- Separate terminal ID for frontend
  })
  start:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Frontend (docker up)...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [F]rontend up | docker compose up frontend' })

-- Docker Build Backend (for projects using docker)
vim.keymap.set('n', '<leader>rdb', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local build = Terminal:new({
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; docker compose build backend"',
    direction = 'horizontal',
    close_on_exit = false,
  })
  build:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Building Backend (docker)...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [B]ackend build | docker compose build backend' })

-- Docker Up Backend (for projects using docker)
vim.keymap.set('n', '<leader>rdB', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local start = Terminal:new({
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; docker compose up backend"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 10, -- Separate terminal ID for backend
  })
  start:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Backend (docker up)...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [B]ackend up | docker compose up backend' })
