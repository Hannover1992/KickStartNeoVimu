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

-- Docker Service Picker: einzelnen Compose-Service starten (DCSRE only)
-- Use-Case: Profil (z.B. dev-backend) laeuft schon, ein Service fehlt darin
-- (z.B. "service" ist nur in all/service) → nachstarten ohne das Profil zu wechseln.
-- --no-deps: Abhaengigkeiten werden NICHT mitgestartet, sonst wuerde z.B. "setup"
-- (Migrations) jedes Mal neu laufen. Deps muessen also schon oben sein.
vim.keymap.set('n', '<leader>rDs', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Docker Service picker nur für DCSRE', vim.log.levels.WARN)
    return
  end

  local compose_path = vim.g.project_docker_root_windows .. '\\docker-compose.yml'
  local file = io.open(compose_path, 'r')
  if not file then
    vim.notify('docker-compose.yml nicht gefunden: ' .. compose_path, vim.log.levels.ERROR)
    return
  end

  local services = {}
  local in_services = false
  for line in file:lines() do
    if line:match('^services%s*:') then
      in_services = true
    elseif in_services and line:match('^%S') then
      in_services = false
    elseif in_services then
      local name = line:match('^  ([%w_%-]+)%s*:%s*$')
      if name then table.insert(services, name) end
    end
  end
  file:close()
  table.sort(services)

  if #services == 0 then
    vim.notify('Keine Services in docker-compose.yml gefunden', vim.log.levels.ERROR)
    return
  end

  local env_file = '.env.noproxy'
  if vim.fn.filereadable(vim.g.project_docker_root_windows .. '\\.env.noproxy') == 0 then
    env_file = '.env'
  end

  vim.ui.select(services, {
    prompt = 'Docker Service starten (--no-deps):',
    format_item = function(item) return item end,
  }, function(choice)
    if not choice then return end
    local Terminal = require('toggleterm.terminal').Terminal
    local cmd = 'powershell.exe -Command "'
      .. 'Set-Location \'' .. vim.g.project_docker_root_windows .. '\'; '
      .. 'docker compose -p dcsp --profile all --env-file ' .. env_file
      .. ' up -d --no-deps ' .. choice .. '; '
      .. 'if ($?) { notify \'Docker ' .. choice .. ' gestartet\' } else { notify \'Docker ' .. choice .. ' fehlgeschlagen\' }"'
    local docker = Terminal:new({
      cmd = cmd,
      direction = 'horizontal',
      close_on_exit = false,
      count = 22,
    })
    docker:toggle()
    vim.notify('[DCSRE] Docker Service: ' .. choice .. ' (' .. env_file .. ')', vim.log.levels.INFO)
  end)
end, { desc = '[R]un [D]ocker [S]ervice | Picker: einzelnen Compose-Service starten (--no-deps)' })

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

-- <leader>rDc - [C]lean: Wegwerf-Images der Integrationstests loeschen.
--
-- Warum ein eigener Key und nicht 'docker image prune': prune kann NICHT nach Namen
-- filtern. Es kennt nur dangling (ohne Tag), --filter until=<alter> und label=<x>.
-- Die Test-Images tragen aber alle einen Tag (testdatabase_...:latest) -- fuer prune
-- sind sie damit unsichtbar. Und 'prune -a' wuerde die Basis-Images (dcsp-*, minio,
-- gotenberg, keycloak) mitnehmen, die danach alle neu gezogen werden muessten.
--
-- Hintergrund: ContainerIntegrationTestBase baut pro Testklasse ein eigenes Image mit
-- Zeitstempel im Namen (testdatabase_<testname>_<ts>_<guid>). Der Cache greift dadurch
-- nie, und niemand raeumt sie ab -- gemessen: 144 Stueck a 2,48 GB = ~357 GB.
--
-- Das Muster greift am PRAEFIX test<typ>_, nicht an "test" irgendwo im Namen. Sonst
-- fiele 'dic-mock-server:integration-test' mit rein, das ein echtes Basis-Image ist.
vim.keymap.set('n', '<leader>rDc', function()
  local ps = 'powershell.exe -NoProfile -Command "' ..
    'docker images --format \'{{.Repository}}:{{.Tag}}|{{.Size}}\' | ' ..
    'Select-String -Pattern \'^test(database|db|minio|gotenberg|smtp|dicmock)_\'"'
  local raw = vim.fn.systemlist(ps)
  if vim.v.shell_error ~= 0 then
    vim.notify('docker images fehlgeschlagen:\n' .. table.concat(raw or {}, '\n'), vim.log.levels.ERROR)
    return
  end

  local images = {}
  for _, line in ipairs(raw or {}) do
    local name = (line or ''):match('^([^|]+)|')
    if name then table.insert(images, (name:gsub('%s+$', ''))) end
  end

  if #images == 0 then
    vim.notify('Keine Test-Wegwerf-Images vorhanden (nichts aufzuraeumen).', vim.log.levels.INFO)
    return
  end

  -- Vorschau: erste 5 zeigen, damit man sieht WAS geloescht wird, bevor man ja sagt.
  local preview = {}
  for i = 1, math.min(#images, 5) do table.insert(preview, '  ' .. images[i]) end
  if #images > 5 then table.insert(preview, '  ... und ' .. (#images - 5) .. ' weitere') end

  local answer = vim.fn.confirm(
    string.format('%d Test-Images loeschen?\n\n%s\n\nBasis-Images (dcsp-*, minio, gotenberg, keycloak) bleiben unangetastet.',
      #images, table.concat(preview, '\n')),
    '&Ja\n&Nein', 2)
  if answer ~= 1 then
    vim.notify('Abgebrochen, nichts geloescht.', vim.log.levels.INFO)
    return
  end

  -- Ueber eine Datei statt langer Kommandozeile: bei 144 Namen platzt sonst das
  -- PowerShell-Limit (~8k Zeichen).
  local temp = os.getenv('TEMP') or os.getenv('TMP')
  local list_file = temp .. [[\docker-test-images.txt]]
  vim.fn.writefile(images, list_file)

  local script = temp .. [[\clean-test-images.ps1]]
  vim.fn.writefile({
    '$ErrorActionPreference = "Continue"',
    '$names = Get-Content "' .. list_file .. '"',
    'Write-Host ("Loesche " + $names.Count + " Test-Images ...") -ForegroundColor Cyan',
    '$ok = 0; $fail = 0',
    'foreach ($n in $names) {',
    '  docker rmi -f $n 2>&1 | Out-Null',
    '  if ($LASTEXITCODE -eq 0) { $ok++ } else { $fail++; Write-Host ("  FEHLER: " + $n) -ForegroundColor Yellow }',
    '}',
    'Write-Host ""',
    'Write-Host ("Geloescht: " + $ok + "   Fehlgeschlagen: " + $fail) -ForegroundColor Green',
    'Write-Host ""',
    'docker system df',
    'Write-Host ""',
    'Write-Host "Fertig. Fenster schliessen mit q." -ForegroundColor DarkGray',
  }, script)

  local Terminal = require('toggleterm.terminal').Terminal
  Terminal:new({
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script .. '"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 26,
  }):toggle()
end, { desc = '[R]un [D]ocker [C]lean | Wegwerf-Images der Integrationstests loeschen (Basis-Images bleiben)' })
