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

-- Docker All: Start ALL services (Profile=all) - DCSRE + CenCoCo
vim.keymap.set('n', '<leader>rDa', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'DCSRE' then
    cmd = 'powershell.exe -ExecutionPolicy Bypass -Command "Set-Location \'' .. vim.g.project_docker_root_windows .. '\'; .\\docker-up.ps1 -EnvFile \\"./.env.noproxy\\" -Profile all -SkipTests; if ($?) { notify \'Docker All erfolgreich\' } else { notify \'Docker All fehlgeschlagen\' }"'
  elseif vim.g.project_name == 'CENCOCD' then
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_docker_root_windows .. '\'; docker compose --profile app up -d --build"'
  else
    vim.notify('rDa nur fuer DCSRE/CenCoCo', vim.log.levels.WARN)
    return
  end
  local infra = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 23,
  })
  infra:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Docker ALL (full environment)...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [A]ll | DCSRE: docker-up.ps1 -Profile all | CenCoCo: compose.all --profile all' })

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

-- Docker TUI: lazydocker (Ersatz für Docker Desktop GUI, terminal-basiert)
vim.keymap.set('n', '<leader>rDt', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local lazydocker = Terminal:new({
    cmd = 'lazydocker',
    direction = 'float',
    close_on_exit = true,
    count = 24, -- Separate terminal ID für lazydocker
  })
  lazydocker:toggle()
end, { desc = '[R]un [D]ocker [T]UI | lazydocker' })

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

-- Docker Profile Picker: Liest Profile dynamisch aus docker-compose.yml (DCSRE only)
vim.keymap.set('n', '<leader>rDp', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Docker Profile picker nur für DCSRE', vim.log.levels.WARN)
    return
  end

  -- docker-compose.yml dynamisch lesen
  local compose_path = vim.g.project_docker_root_windows .. '\\docker-compose.yml'
  local file = io.open(compose_path, 'r')
  if not file then
    vim.notify('docker-compose.yml nicht gefunden: ' .. compose_path, vim.log.levels.ERROR)
    return
  end

  local profiles = {}
  local seen = {}
  local in_profiles_block = false
  for line in file:lines() do
    if line:match('%s*profiles%s*:') then
      in_profiles_block = true
    elseif in_profiles_block then
      local profile = line:match('%s*%-%s*(.-)%s*$')
      if profile and profile ~= '' then
        if not seen[profile] then
          seen[profile] = true
          table.insert(profiles, profile)
        end
      else
        in_profiles_block = false
      end
    end
  end
  file:close()
  table.sort(profiles)

  if #profiles == 0 then
    vim.notify('Keine Profile in docker-compose.yml gefunden', vim.log.levels.ERROR)
    return
  end

  vim.ui.select(profiles, {
    prompt = 'Docker Profile wählen:',
    format_item = function(item) return item end,
  }, function(choice)
    if not choice then return end
    local Terminal = require('toggleterm.terminal').Terminal
    local cmd = 'powershell.exe -ExecutionPolicy Bypass -Command "'
      .. 'Set-Location \'' .. vim.g.project_docker_root_windows .. '\'; '
      .. '.\\docker-up.ps1 -EnvFile \\"./.env.noproxy\\" -Profile ' .. choice .. ' -SkipTests; '
      .. 'if ($?) { notify \'Docker ' .. choice .. ' erfolgreich\' } else { notify \'Docker ' .. choice .. ' fehlgeschlagen\' }"'
    local docker = Terminal:new({
      cmd = cmd,
      direction = 'horizontal',
      close_on_exit = false,
      count = 22,
    })
    docker:toggle()
    vim.notify('[DCSRE] Docker Profile: ' .. choice, vim.log.levels.INFO)
  end)
end, { desc = '[R]un [D]ocker [P]rofile | Picker (dynamisch aus docker-compose.yml)' })

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
