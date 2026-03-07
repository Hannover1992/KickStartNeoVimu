-- lua/shared/keybindings/backend.lua
-- [R]un [B]ackend* Keybindings: WebHost, Setup, Build, Tests, Watch
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität

-- Watch Backend: Backend with hot reload
vim.keymap.set('n', '<leader>wb', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local profile_arg = vim.g.project_launch_profile and (' --launch-profile ' .. vim.g.project_launch_profile) or ''
  local cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; dotnet watch run' .. profile_arg .. '"'
  local watch = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  watch:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Backend with hot reload...', vim.log.levels.INFO)
end, { desc = '[W]atch [B]ackend (hot reload)' })

-- Watch Test: Tests with hot reload
vim.keymap.set('n', '<leader>bt', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; dotnet watch test"'
  local watch = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  watch:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Tests with hot reload...', vim.log.levels.INFO)
end, { desc = '[B]ackend [T]est (watch hot reload)' })

-- Run Backend WebHost: Start ASP.NET Core backend
vim.keymap.set('n', '<leader>rbw', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    if is_windows then
      cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; dotnet run --launch-profile https"'
    else
      cmd = 'cd ' .. vim.g.project_webhost .. ' && dotnet run --launch-profile https'
    end
  else
    -- DCSRE: Custom URLs (API on https://localhost:5443)
    if is_windows then
      cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_webhost .. '\'; $env:ASPNETCORE_URLS=\'https://localhost:5443;http://localhost:5080\'; $env:ASPNETCORE_ENVIRONMENT=\'Development\'; dotnet run --no-restore"'
    else
      cmd = 'cd ' .. vim.g.project_webhost .. ' && ASPNETCORE_URLS="https://localhost:5443;http://localhost:5080" ASPNETCORE_ENVIRONMENT=Development dotnet run --no-restore'
    end
  end
  local webhost = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 20, -- Separate terminal ID for backend webhost
  })
  webhost:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Backend WebHost...', vim.log.levels.INFO)
end, { desc = '[R]un [B]ackend [W]ebhost | CENCOCD: dotnet run --launch-profile https | DCSRE: dotnet run --no-restore (https://localhost:5443)' })

-- Run Backend Setup: Execute FluentMigrator migrations (DCSRE only)
vim.keymap.set('n', '<leader>rbs', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Setup/Migrations only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; dotnet run --project VDEK.DCSP.Setup"'
  local setup = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  setup:toggle()
  vim.notify('[DCSRE] Running Backend Setup (Migrations)...', vim.log.levels.INFO)
end, { desc = '[R]un [B]ackend [S]etup | dotnet run --project VDEK.DCSP.Setup' })

-- Hilfsfunktion: Projekte aus .sln lesen, Picker öffnen, dann callback(choice, rel_path, backend_win)
local function pick_backend_project(prompt, callback)
  local backend_win = vim.g.project_backend_windows
  if not backend_win then
    vim.notify('project_backend_windows nicht konfiguriert', vim.log.levels.ERROR)
    return
  end

  local sln_files = vim.fn.glob(backend_win .. '\\*.sln', false, true)
  if #sln_files == 0 then
    vim.notify('Keine .sln Datei in: ' .. backend_win, vim.log.levels.ERROR)
    return
  end

  local file = io.open(sln_files[1], 'r')
  if not file then
    vim.notify('.sln nicht lesbar: ' .. sln_files[1], vim.log.levels.ERROR)
    return
  end

  -- Projekte parsen: Project("{GUID}") = "Name", "Path\Name.csproj", "{GUID}"
  local projects = {}
  for line in file:lines() do
    local name, rel_path = line:match('^Project%("[^"]*"%)%s*=%s*"([^"]+)",%s*"([^"]+%.csproj)"')
    if name and rel_path then
      table.insert(projects, { name = name, path = rel_path })
    end
  end
  file:close()
  table.sort(projects, function(a, b) return a.name < b.name end)

  if #projects == 0 then
    vim.notify('Keine .csproj Projekte in .sln gefunden', vim.log.levels.ERROR)
    return
  end

  vim.ui.select(vim.tbl_map(function(p) return p.name end, projects), {
    prompt = prompt,
    format_item = function(item) return item end,
  }, function(choice)
    if not choice then return end
    for _, p in ipairs(projects) do
      if p.name == choice then
        callback(choice, p.path, backend_win)
        return
      end
    end
  end)
end

-- rbp: Schneller Build (nutzt Cache + inkrementellen Build-Mechanismus)
vim.keymap.set('n', '<leader>rbp', function()
  pick_backend_project('Backend Projekt builden (schnell):', function(name, rel_path, backend_win)
    local Terminal = require('toggleterm.terminal').Terminal
    local cmd = 'powershell.exe -Command "Set-Location \'' .. backend_win .. '\'; dotnet build \'' .. rel_path .. '\'"'
    Terminal:new({ cmd = cmd, direction = 'horizontal', close_on_exit = false }):toggle()
    vim.notify('[' .. vim.g.project_name .. '] Building: ' .. name, vim.log.levels.INFO)
  end)
end, { desc = '[R]un [B]ackend [P]roject | Picker schnell (Cache, inkrementell)' })

-- rbP: Nuclear Clean Build (dotnet clean + dotnet build --verbosity detailed)
vim.keymap.set('n', '<leader>rbP', function()
  pick_backend_project('Backend Projekt CLEAN builden:', function(name, rel_path, backend_win)
    local Terminal = require('toggleterm.terminal').Terminal
    local cmd = 'powershell.exe -Command "Set-Location \'' .. backend_win .. '\'; '
      .. 'Write-Host \\'---[ dotnet clean ]-----------\\' -ForegroundColor Yellow; '
      .. 'dotnet clean \'' .. rel_path .. '\'; '
      .. 'Write-Host \\'---[ dotnet build verbose ]---\\' -ForegroundColor Yellow; '
      .. 'dotnet build \'' .. rel_path .. '\' --verbosity detailed"'
    Terminal:new({ cmd = cmd, direction = 'horizontal', close_on_exit = false }):toggle()
    vim.notify('[' .. vim.g.project_name .. '] Clean Build: ' .. name, vim.log.levels.WARN)
  end)
end, { desc = '[R]un [B]ackend [P]rofile clean | dotnet clean + build --verbosity detailed' })

-- rbR: Run Backend — 2-stufiger Picker: Projekt → LaunchProfile (aus launchSettings.json)
vim.keymap.set('n', '<leader>rbR', function()
  pick_backend_project('Backend Projekt starten:', function(name, rel_path, backend_win)
    -- Properties/launchSettings.json im Projektverzeichnis suchen
    local proj_subdir = rel_path:match('^(.+)\\[^\\]+%.csproj$') or ''
    local settings_path = backend_win .. '\\' .. proj_subdir .. '\\Properties\\launchSettings.json'

    local proj_dir = backend_win .. '\\' .. proj_subdir  -- Projektverzeichnis (für appsettings.json etc.)

    local f = io.open(settings_path, 'r')
    if not f then
      -- Kein launchSettings.json → einfach dotnet run ohne Profil, CWD = Projektverzeichnis
      local Terminal = require('toggleterm.terminal').Terminal
      local cmd = 'powershell.exe -Command "Set-Location \'' .. proj_dir .. '\'; dotnet run"'
      Terminal:new({ cmd = cmd, direction = 'horizontal', close_on_exit = false, count = 20 }):toggle()
      vim.notify('[' .. vim.g.project_name .. '] Running: ' .. name .. ' (kein launchSettings)', vim.log.levels.INFO)
      return
    end

    local content = f:read('*a')
    f:close()

    -- Strip UTF-8 BOM (Windows fügt oft \xEF\xBB\xBF hinzu)
    content = content:gsub('^\239\187\191', '')

    local ok, json = pcall(vim.fn.json_decode, content)
    if not ok then
      vim.notify('launchSettings.json JSON-Fehler: ' .. tostring(json), vim.log.levels.ERROR)
      return
    end
    if not json or not json.profiles then
      vim.notify('launchSettings.json: kein "profiles" Schlüssel: ' .. settings_path, vim.log.levels.ERROR)
      return
    end

    -- Nur "Project" Profile (nicht IISExpress)
    local profiles = {}
    for pname, pdata in pairs(json.profiles) do
      if pdata.commandName == 'Project' then
        local url = pdata.applicationUrl and pdata.applicationUrl:match('([^;]+)') or '(kein URL – Background Service)'
        table.insert(profiles, { name = pname, url = url })
      end
    end
    table.sort(profiles, function(a, b) return a.name < b.name end)

    if #profiles == 0 then
      vim.notify('Keine launchbaren Profile in: ' .. settings_path, vim.log.levels.WARN)
      return
    end

    -- Stufe 2: LaunchProfile-Picker (zeigt URL direkt an)
    vim.ui.select(profiles, {
      prompt = 'Launch Profile (' .. name .. '):',
      format_item = function(p) return p.name .. '  →  ' .. p.url end,
    }, function(choice)
      if not choice then return end
      local Terminal = require('toggleterm.terminal').Terminal
      -- CWD = Projektverzeichnis → appsettings.json wird korrekt gefunden
      local cmd = 'powershell.exe -Command "Set-Location \'' .. proj_dir .. '\'; '
        .. 'dotnet run --launch-profile \'' .. choice.name .. '\'"'
      Terminal:new({ cmd = cmd, direction = 'horizontal', close_on_exit = false, count = 20 }):toggle()
      vim.notify('[' .. vim.g.project_name .. '] Running: ' .. name .. ' @ ' .. choice.url, vim.log.levels.INFO)
    end)
  end)
end, { desc = '[R]un [B]ackend [R]un | 2-Stufen: Projekt → LaunchProfile (launchSettings.json)' })

-- Run Backend Build: Compile the backend solution
vim.keymap.set('n', '<leader>rbb', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; dotnet build"'
  local build = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  build:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Building Backend...', vim.log.levels.INFO)
end, { desc = '[R]un [B]ackend [B]uild | dotnet build' })

-- Run Backend Tests
vim.keymap.set('n', '<leader>rbt', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local current_file = vim.fn.expand('%:t:r')
  local is_test_file = current_file:match('Test') or current_file:match('Tests')

  local cmd
  if is_test_file then
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; dotnet test --no-build --no-restore --filter \'FullyQualifiedName~' .. current_file .. '\'"'
  else
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; dotnet test --no-build --no-restore"'
  end

  local test = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  test:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Running Backend Tests...', vim.log.levels.INFO)
end, { desc = '[R]un [B]ackend [T]ests | dotnet test --filter FullyQualifiedName~{file}' })

-- Run Backend Unit Tests: Project-aware (DCSRE: exclude DB/Storage/Docker, CENCOCD: Stufe 1 only)
vim.keymap.set('n', '<leader>rbu', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    -- CenCoCo Stufe 1: Unit Tests only (no Docker, no IntegrationTests)
    local sln = vim.g.project_root_windows .. '\\src\\CenCoCo.sln'
    cmd = "powershell.exe -Command \"dotnet test '" .. sln .. "' --filter 'Category!=IsolatedDocker&Category!=IntegrationTests' --verbosity minimal\""
  else
    -- DCSRE: Unit tests excluding Database/Storage/Docker categories
    cmd = "powershell.exe -Command \"Set-Location '" .. vim.g.project_backend .. "'; dotnet test --filter 'Category!=Database & Category!=Storage & Category!=Docker'\""
  end
  local test = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  test:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Running Unit Tests (Stufe 1)...', vim.log.levels.INFO)
end, { desc = '[R]un [B]ackend [U]nit tests Stufe 1 | DCSRE: --filter Category!=Database&Category!=Storage&Category!=Docker | CENCOCD: --filter Category!=IsolatedDocker&Category!=IntegrationTests' })

-- Run Integration InMemory: CenCoCo Stufe 2 (Integration Tests without Docker)
vim.keymap.set('n', '<leader>rii', function()
  if vim.g.project_name == 'CENCOCD' then
    -- CenCoCo Stufe 2: Integration Tests (InMemory/echte DB, no IsolatedDocker)
    local sln = vim.g.project_root_windows .. '\\src\\CenCoCo.sln'
    local Terminal = require('toggleterm.terminal').Terminal
    local test = Terminal:new({
      cmd = "powershell.exe -Command \"dotnet test '" .. sln .. "' --filter 'Category=IntegrationTests' --verbosity minimal\"",
      direction = 'horizontal',
      close_on_exit = false,
    })
    test:toggle()
    vim.notify('[CENCOCD] Running Integration Tests (Stufe 2)...', vim.log.levels.INFO)
  else
    vim.notify('Use <leader>rid for DCSRE integration tests', vim.log.levels.INFO)
  end
end, { desc = '[R]un [I]ntegration [I]nMemory Stufe 2 | CENCOCD: --filter Category=IntegrationTests' })

-- Test Backend Integration: Run tests for current file
vim.keymap.set('n', '<leader>tbi', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local current_file = vim.fn.expand('%:t:r')

  if not (current_file:match('Test') or current_file:match('Tests')) then
    vim.notify('Not a test file!', vim.log.levels.ERROR)
    return
  end

  local cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_backend .. '\'; dotnet test --filter \'FullyQualifiedName~' .. current_file .. '\'"'

  local test = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  test:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Running Tests for ' .. current_file .. '...', vim.log.levels.INFO)
end, { desc = '[T]est [B]ackend [I]ntegration (current file)' })
