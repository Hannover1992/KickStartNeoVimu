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

-- Backend Project Picker: Projekte aus .sln auslesen, ein Projekt bauen (analog rDp)
vim.keymap.set('n', '<leader>rbp', function()
  local backend_win = vim.g.project_backend_windows
  if not backend_win then
    vim.notify('project_backend_windows nicht konfiguriert', vim.log.levels.ERROR)
    return
  end

  -- .sln Datei finden (Windows-Pfad für io.open)
  local sln_files = vim.fn.glob(backend_win .. '\\*.sln', false, true)
  if #sln_files == 0 then
    vim.notify('Keine .sln Datei in: ' .. backend_win, vim.log.levels.ERROR)
    return
  end

  local sln_path = sln_files[1]
  local file = io.open(sln_path, 'r')
  if not file then
    vim.notify('.sln nicht lesbar: ' .. sln_path, vim.log.levels.ERROR)
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

  local display = vim.tbl_map(function(p) return p.name end, projects)

  vim.ui.select(display, {
    prompt = 'Backend Projekt builden:',
    format_item = function(item) return item end,
  }, function(choice)
    if not choice then return end
    local rel_path
    for _, p in ipairs(projects) do
      if p.name == choice then rel_path = p.path; break end
    end
    if not rel_path then return end

    local Terminal = require('toggleterm.terminal').Terminal
    local cmd = 'powershell.exe -Command "Set-Location \'' .. backend_win .. '\'; dotnet build \'' .. rel_path .. '\'"'
    local build = Terminal:new({
      cmd = cmd,
      direction = 'horizontal',
      close_on_exit = false,
    })
    build:toggle()
    vim.notify('[' .. vim.g.project_name .. '] Building: ' .. choice, vim.log.levels.INFO)
  end)
end, { desc = '[R]un [B]ackend [P]roject | Picker (dynamisch aus .sln)' })

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
