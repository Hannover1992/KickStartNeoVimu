-- lua/shared/keybindings/tests.lua
-- E2E + Integration Test Keybindings: reb, reg, rim, rid, riC, riF, rif, ris + TRX Infrastructure
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität

-- Helper: Get Cypress path dynamically (works with all worktrees)
local function get_cypress_path_windows()
  local root = vim.g.project_root_windows
  if not root then return nil end
  return root .. '\\Sources\\Tests\\Cypress'
end

-- E2E Install: npm install in Cypress directory (needed for new worktrees)
-- E2E Build: TypeScript type-check (npx tsc --noEmit)
vim.keymap.set('n', '<leader>reb', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local cypress_path = get_cypress_path_windows()
  if not cypress_path then
    vim.notify('Could not determine Cypress path', vim.log.levels.ERROR)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local build = Terminal:new({
    cmd = "powershell.exe -Command \"cd '" .. cypress_path .. "'; npx tsc --noEmit\"",
    direction = 'horizontal',
    close_on_exit = false,
  })
  build:toggle()
  vim.notify('[DCSRE] Running E2E TypeScript check...', vim.log.levels.INFO)
end, { desc = '[R]un [E]2E [B]uild | npx tsc --noEmit' })

vim.keymap.set('n', '<leader>rei', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local cypress_path = get_cypress_path_windows()
  if not cypress_path then
    vim.notify('Could not determine Cypress path', vim.log.levels.ERROR)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local install = Terminal:new({
    cmd = "powershell.exe -Command \"cd '" .. cypress_path .. "'; npm install\"",
    direction = 'horizontal',
    close_on_exit = false,
  })
  install:toggle()
  vim.notify('[DCSRE] Running npm install in Cypress...', vim.log.levels.INFO)
end, { desc = '[R]un [E]2E [I]nstall | npm install (Cypress)' })

-- E2E Gesamtsystemtest: Run full integration E2E tests (DCSRE only, headless via PowerShell)
vim.keymap.set('n', '<leader>reg', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local cypress_path = get_cypress_path_windows()
  if not cypress_path then
    vim.notify('Could not determine Cypress path', vim.log.levels.ERROR)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = "powershell.exe -Command \"cd '" .. cypress_path .. "'; npm run cypress:run:gesamtsystemtest\"",
    direction = 'horizontal',
    close_on_exit = false,
    count = 30, -- Separate terminal ID for E2E tests
  })
  test:toggle()
  vim.notify('[DCSRE] Running E2E Gesamtsystemtest (headless)...', vim.log.levels.INFO)
end, { desc = '[R]un [E]2E [G]esamtsystemtest | npm run cypress:run:gesamtsystemtest' })

-- E2E Systemtest: Run isolated system tests (DCSRE only, headless via PowerShell)
vim.keymap.set('n', '<leader>res', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local cypress_path = get_cypress_path_windows()
  if not cypress_path then
    vim.notify('Could not determine Cypress path', vim.log.levels.ERROR)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = "powershell.exe -Command \"cd '" .. cypress_path .. "'; npm run cypress:run:systemtest\"",
    direction = 'horizontal',
    close_on_exit = false,
    count = 31, -- Separate terminal ID for E2E tests
  })
  test:toggle()
  vim.notify('[DCSRE] Running E2E Systemtest (isolated)...', vim.log.levels.INFO)
end, { desc = '[R]un [E]2E [S]ystemtest | npm run cypress:run:systemtest' })

-- E2E Open: Interactive Cypress UI (DCSRE only, via PowerShell)
vim.keymap.set('n', '<leader>reo', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local cypress_path = get_cypress_path_windows()
  if not cypress_path then
    vim.notify('Could not determine Cypress path', vim.log.levels.ERROR)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = "powershell.exe -Command \"cd '" .. cypress_path .. "'; npm run cypress:open:systemtest\"",
    direction = 'horizontal',
    close_on_exit = false,
    count = 32, -- Separate terminal ID for Cypress UI
  })
  test:toggle()
  vim.notify('[DCSRE] Opening Cypress UI...', vim.log.levels.INFO)
end, { desc = '[R]un [E]2E [O]pen | npm run cypress:open:systemtest' })

-- === Integration Tests (TRX Infrastructure) ===

-- Helper function to modify xunit.runner.json maxParallelThreads
local function set_xunit_threads(threads)
  if vim.g.project_name ~= 'DCSRE' then
    return false
  end
  local xunit_file = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests\\xunit.runner.json'
  local file = io.open(xunit_file, 'r')
  if not file then
    vim.notify('xunit.runner.json not found: ' .. xunit_file, vim.log.levels.ERROR)
    return false
  end
  local content = file:read('*all')
  file:close()
  local new_content = content:gsub('"maxParallelThreads": %d+', '"maxParallelThreads": ' .. threads)
  file = io.open(xunit_file, 'w')
  if not file then
    vim.notify('Cannot write xunit.runner.json', vim.log.levels.ERROR)
    return false
  end
  file:write(new_content)
  file:close()
  return true
end

-- === Integration Test Infrastructure (TRX + Telescope) ===

-- Write PowerShell script that runs tests with detailed output + TRX summary at end
-- extra_flags: additional dotnet test flags (e.g. '--no-build --no-restore')
local function write_it_script(filter, label, extra_flags)
  local temp = os.getenv('TEMP') or os.getenv('TMP') or 'C:\\Users\\Administrator\\AppData\\Local\\Temp'
  local script_path = temp .. '\\run-it.ps1'
  local trx_path = temp .. '\\it-latest.trx'
  local test_dir = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
  local flags = extra_flags or '--no-build --no-restore'

  local script = string.format([[$ErrorActionPreference = "Continue"
$trx = "%s"
if (Test-Path $trx) { Remove-Item $trx -Force }
dotnet test "%s" %s --filter "%s" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$trx" --verbosity detailed
if (Test-Path $trx) {
    Write-Host ""
    Write-Host "===============================" -ForegroundColor Cyan
    [xml]$r = Get-Content $trx
    $all = $r.TestRun.Results.UnitTestResult
    $p = @($all | Where-Object { $_.outcome -eq 'Passed' })
    $f = @($all | Where-Object { $_.outcome -eq 'Failed' })
    $s = @($all | Where-Object { $_.outcome -eq 'NotExecuted' })
    $color = if ($f.Count -gt 0) { 'Red' } else { 'Green' }
    Write-Host ("  PASSED: {0}  FAILED: {1}  SKIPPED: {2}" -f $p.Count, $f.Count, $s.Count) -ForegroundColor $color
    if ($f.Count -gt 0) {
        Write-Host ""
        Write-Host "  FAILED TESTS:" -ForegroundColor Red
        foreach ($t in $f) {
            Write-Host ("  X " + $t.testName) -ForegroundColor Red
            if ($t.Output -and $t.Output.ErrorInfo -and $t.Output.ErrorInfo.Message) {
                $msg = $t.Output.ErrorInfo.Message
                if ($msg.Length -gt 200) { $msg = $msg.Substring(0, 200) + "..." }
                Write-Host ("    " + $msg) -ForegroundColor Yellow
            }
        }
    }
    Write-Host "===============================" -ForegroundColor Cyan
    Write-Host ("  TRX: " + $trx) -ForegroundColor Gray
    Write-Host ("  Hint: <leader>riF = Failed Tests | <leader>rif = Find Tests | <leader>ris = All Tests (Telescope)") -ForegroundColor DarkGray
} else {
    Write-Host "TRX file not found - tests may not have run!" -ForegroundColor Red
}]], trx_path, test_dir, flags, filter)

  local file = io.open(script_path, 'w')
  if file then
    file:write(script)
    file:close()
  end
  return script_path
end

-- Run integration tests with TRX summary
local function run_integration_tests(filter, label, threads, terminal_id)
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
    return
  end

  if not set_xunit_threads(threads) then return end
  vim.notify('[DCSRE] Set maxParallelThreads=' .. threads .. ' for ' .. label .. ' tests', vim.log.levels.INFO)

  local script_path = write_it_script(filter, label)

  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
    direction = 'horizontal',
    close_on_exit = false,
    count = terminal_id,
    on_exit = function()
      set_xunit_threads(1)
      vim.notify('[DCSRE] Reset maxParallelThreads=1', vim.log.levels.INFO)
    end,
  })
  test:toggle()
  vim.notify('[DCSRE] Running Integration ' .. label .. ' tests (' .. threads .. ' threads)...', vim.log.levels.INFO)
end

-- Parse TRX file → Lua table of {outcome, name}
local function parse_trx_results()
  local temp = os.getenv('TEMP') or os.getenv('TMP') or 'C:\\Users\\Administrator\\AppData\\Local\\Temp'
  local trx_path = temp .. '\\it-latest.trx'
  local parsed_file = temp .. '\\it-parsed.txt'

  -- PowerShell parses TRX → simple text file (outcome|testName per line)
  vim.fn.system(
    'powershell.exe -NoProfile -Command "'
      .. "[xml]$r=Get-Content '"
      .. trx_path
      .. "'; $r.TestRun.Results.UnitTestResult | ForEach-Object { $_.outcome + '|' + $_.testName } | Out-File -Encoding UTF8 '"
      .. parsed_file
      .. "'\""
  )

  local lines = vim.fn.readfile(parsed_file)
  local results = {}
  for _, line in ipairs(lines) do
    local trimmed = line:match('^%s*(.-)%s*$')
    if trimmed and trimmed ~= '' then
      local outcome, name = trimmed:match('^(.-)|(.*)')
      if outcome and name then
        table.insert(results, { outcome = outcome, name = name })
      end
    end
  end
  return results
end

-- Telescope picker for test results (shared by rif and ris)
local function telescope_test_picker(title, test_list)
  local test_dir = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
  local pickers = require('telescope.pickers')
  local finders = require('telescope.finders')
  local conf = require('telescope.config').values
  local actions = require('telescope.actions')
  local action_state = require('telescope.actions.state')

  pickers
    .new({}, {
      prompt_title = title,
      finder = finders.new_table({
        results = test_list,
        entry_maker = function(entry)
          local icon = entry.outcome == 'Passed' and 'V ' or entry.outcome == 'Failed' and 'X ' or '- '
          return {
            value = entry.name,
            display = icon .. entry.name,
            ordinal = entry.name,
          }
        end,
      }),
      sorter = conf.generic_sorter({}),
      attach_mappings = function(prompt_bufnr)
        actions.select_default:replace(function()
          local picker = action_state.get_current_picker(prompt_bufnr)
          local selections = picker:get_multi_selection()

          if #selections == 0 then
            local entry = action_state.get_selected_entry()
            if entry then
              selections = { entry }
            end
          end

          actions.close(prompt_bufnr)
          if #selections == 0 then return end

          -- Build filter: FullyQualifiedName=Test1|FullyQualifiedName=Test2
          local filter_parts = {}
          for _, sel in ipairs(selections) do
            table.insert(filter_parts, 'FullyQualifiedName=' .. sel.value)
          end
          local filter = table.concat(filter_parts, '|')

          -- Prompt for thread count
          vim.ui.input({ prompt = 'Parallel threads (default 8): ' }, function(input)
            if input == nil then return end -- cancelled
            local threads = tonumber(input) or 8
            if not set_xunit_threads(threads) then return end

            local Terminal = require('toggleterm.terminal').Terminal
            local test = Terminal:new({
              cmd = 'powershell.exe -NoProfile -Command "dotnet test \''
                .. test_dir
                .. '\' --no-build --no-restore --filter \''
                .. filter
                .. '\' --verbosity detailed --logger \'console;verbosity=detailed\'"',
              direction = 'horizontal',
              close_on_exit = false,
              count = 42,
              on_exit = function()
                set_xunit_threads(1)
                vim.notify('[DCSRE] Reset maxParallelThreads=1', vim.log.levels.INFO)
              end,
            })
            test:toggle()
            vim.notify('[DCSRE] Re-running ' .. #selections .. ' test(s) with ' .. threads .. ' threads...', vim.log.levels.INFO)
          end)
        end)
        return true
      end,
    })
    :find()
end

-- <leader>rim - Run Integration Mock (DicMockServer, prompt for threads, TRX summary)
vim.keymap.set('n', '<leader>rim', function()
  vim.ui.input({ prompt = 'Parallel threads (default 38): ' }, function(input)
    if input == nil then return end -- cancelled
    local threads = tonumber(input) or 38
    run_integration_tests('FullyQualifiedName~IntegrationTests&FullyQualifiedName~DicMockServer', 'Mock', threads, 40)
  end)
end, { desc = '[R]un [I]ntegration [M]ock | DicMockServer (prompt threads) + TRX summary' })

-- <leader>rid - Run Integration Docker: Project-aware (DCSRE: DB tests, CENCOCD: Stufe 3 IsolatedDocker)
vim.keymap.set('n', '<leader>rid', function()
  if vim.g.project_name == 'CENCOCD' then
    -- CenCoCo Stufe 3: Isolated Docker tests (ServiceDesk SystemTests project)
    local test_proj = vim.g.project_root_windows .. '\\tests\\CenCoCo.ServiceDesk.SystemTests\\CenCoCo.ServiceDesk.SystemTests.csproj'
    local Terminal = require('toggleterm.terminal').Terminal
    local test = Terminal:new({
      cmd = "powershell.exe -Command \"dotnet test '" .. test_proj .. "' --filter 'Category=IsolatedDocker' --verbosity minimal\"",
      direction = 'horizontal',
      close_on_exit = false,
      count = 41,
    })
    test:toggle()
    vim.notify('[CENCOCD] Running Isolated Docker Tests (Stufe 3)...', vim.log.levels.INFO)
  else
    -- DCSRE: Integration DB tests (ohne DicMockServer, prompt for threads, TRX summary)
    vim.ui.input({ prompt = 'Parallel threads (default 8): ' }, function(input)
      if input == nil then return end -- cancelled
      local threads = tonumber(input) or 8
      run_integration_tests('FullyQualifiedName~IntegrationTests&FullyQualifiedName!~DicMockServer', 'DB', threads, 41)
    end)
  end
end, { desc = '[R]un [I]ntegration [D]ocker | DCSRE: DB tests + TRX | CENCOCD: Stufe 3 IsolatedDocker' })

-- <leader>riC - Run Integration Clean (Docker prune + rebuild test project)
vim.keymap.set('n', '<leader>riC', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Clean only for DCSRE', vim.log.levels.WARN)
    return
  end
  local test_proj = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests\\VDEK.DCSP.IntegrationTests.csproj'
  local Terminal = require('toggleterm.terminal').Terminal
  local clean = Terminal:new({
    cmd = "powershell.exe -NoProfile -Command \""
      .. "Write-Host '=== Docker Cleanup ===' -ForegroundColor Cyan; "
      .. "docker container prune -f; "
      .. "docker volume prune -f; "
      .. "docker builder prune -f; "
      .. "Write-Host '=== Remove ALL Docker images ===' -ForegroundColor Cyan; "
      .. "docker images -q | ForEach-Object { docker rmi -f $_ }; "
      .. "Write-Host '=== Rebuild IntegrationTests ===' -ForegroundColor Cyan; "
      .. "dotnet build '" .. test_proj .. "'; "
      .. "Write-Host '=== Clean complete ===' -ForegroundColor Green\"",
    direction = 'horizontal',
    close_on_exit = false,
    count = 43,
  })
  clean:toggle()
  vim.notify('[DCSRE] Cleaning Docker + rebuilding IntegrationTests...', vim.log.levels.INFO)
end, { desc = '[R]un [I]ntegration [C]lean | Docker prune + remove testdatabase images + rebuild' })

-- <leader>riF - Run Integration Failed (Telescope picker, Tab=multi-select, Enter=re-run)
vim.keymap.set('n', '<leader>riF', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
    return
  end

  local temp = os.getenv('TEMP') or os.getenv('TMP') or 'C:\\Users\\Administrator\\AppData\\Local\\Temp'
  if vim.fn.filereadable(temp .. '\\it-latest.trx') == 0 then
    vim.notify('No TRX results found. Run <leader>rim or <leader>rid first!', vim.log.levels.WARN)
    return
  end

  local all_results = parse_trx_results()
  local failed = vim.tbl_filter(function(r) return r.outcome == 'Failed' end, all_results)

  if #failed == 0 then
    vim.notify('No failed tests! All ' .. #all_results .. ' tests passed.', vim.log.levels.INFO)
    return
  end

  telescope_test_picker('Failed Integration Tests (' .. #failed .. ') | Tab=select, Enter=re-run', failed)
end, { desc = '[R]un [I]ntegration [F]ailed (capital F) | Telescope picker for failed tests' })

-- <leader>rif - Run Integration Find (Telescope picker for test files, Tab=multi-select, Enter=run)
vim.keymap.set('n', '<leader>rif', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
    return
  end

  local test_root = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
  -- Find all *Tests*.cs files, excluding obj/ directories
  local all_files = vim.fn.globpath(test_root, '**/*Tests*.cs', false, true)
  local test_files = {}
  for _, file in ipairs(all_files) do
    if not file:match('\\obj\\') then
      local rel = file:gsub(test_root:gsub('\\', '\\\\') .. '\\', '')
      local display = rel:gsub('\\', '/'):gsub('%.cs$', '')
      table.insert(test_files, { path = file, rel = rel, display = display })
    end
  end

  if #test_files == 0 then
    vim.notify('No test files found in: ' .. test_root, vim.log.levels.WARN)
    return
  end

  table.sort(test_files, function(a, b) return a.display < b.display end)

  local pickers = require('telescope.pickers')
  local finders = require('telescope.finders')
  local conf = require('telescope.config').values
  local actions = require('telescope.actions')
  local action_state = require('telescope.actions.state')

  pickers.new({}, {
    prompt_title = 'Integration Tests (' .. #test_files .. ') | Tab=multi-select, Enter=run',
    finder = finders.new_table({
      results = test_files,
      entry_maker = function(entry)
        return {
          value = entry,
          display = entry.display,
          ordinal = entry.display,
          path = entry.path,
        }
      end,
    }),
    sorter = conf.generic_sorter({}),
    previewer = conf.file_previewer({}),
    attach_mappings = function(prompt_bufnr)
      actions.select_default:replace(function()
        local picker = action_state.get_current_picker(prompt_bufnr)
        local multi = picker:get_multi_selection()
        actions.close(prompt_bufnr)

        local selected = {}
        if #multi > 0 then
          for _, sel in ipairs(multi) do
            table.insert(selected, sel.value)
          end
        else
          local single = action_state.get_selected_entry()
          if single then
            table.insert(selected, single.value)
          end
        end

        if #selected == 0 then
          vim.notify('No tests selected', vim.log.levels.WARN)
          return
        end

        -- Build filter: FullyQualifiedName~ClassName1|FullyQualifiedName~ClassName2
        local filters = {}
        for _, sel in ipairs(selected) do
          local class_name = sel.rel:match('([^\\]+)%.cs$')
          if class_name then
            table.insert(filters, 'FullyQualifiedName~' .. class_name)
          end
        end
        local filter_str = table.concat(filters, '|')

        -- Ask for thread count
        local names = {}
        for _, sel in ipairs(selected) do table.insert(names, sel.display) end
        vim.ui.input({ prompt = 'Parallel threads (default 8): ' }, function(input)
          if input == nil then return end -- cancelled
          local threads = tonumber(input) or 8
          if not set_xunit_threads(threads) then return end

          local label = #selected .. ' classes, ' .. threads .. ' threads'
          local script_path = write_it_script(filter_str, label, '')

          vim.notify('[DCSRE] ' .. label .. ': ' .. table.concat(names, ', '), vim.log.levels.INFO)

          local Terminal = require('toggleterm.terminal').Terminal
          local term = Terminal:new({
            cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
            direction = 'horizontal',
            close_on_exit = false,
            count = 42,
            on_exit = function()
              set_xunit_threads(1)
              vim.notify('[DCSRE] Reset maxParallelThreads=1', vim.log.levels.INFO)
            end,
          })
          term:toggle()
        end)
      end)
      return true
    end,
  }):find()
end, { desc = '[R]un [I]ntegration [F]ind | Telescope picker for test files' })

-- <leader>ris - Run Integration Search (all tests from last TRX, Telescope picker)
vim.keymap.set('n', '<leader>ris', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
    return
  end

  local temp = os.getenv('TEMP') or os.getenv('TMP') or 'C:\\Users\\Administrator\\AppData\\Local\\Temp'
  if vim.fn.filereadable(temp .. '\\it-latest.trx') == 0 then
    vim.notify('No TRX results found. Run <leader>rim or <leader>rid first!', vim.log.levels.WARN)
    return
  end

  local all_results = parse_trx_results()
  if #all_results == 0 then
    vim.notify('No test results found in TRX.', vim.log.levels.WARN)
    return
  end

  telescope_test_picker('Integration Tests (' .. #all_results .. ') | Tab=select, Enter=re-run', all_results)
end, { desc = '[R]un [I]ntegration [S]earch | Telescope picker for all tests' })

-- Run Backend Build (clean + build) - works for DCSRE and CENCOCD
vim.keymap.set('n', '<leader>rbb', function()
  local build_target
  if vim.g.project_name == 'DCSRE' then
    build_target = vim.g.project_backend_windows
  elseif vim.g.project_name == 'CENCOCD' then
    build_target = vim.g.project_docker_root_windows .. '\\CenCoCo.sln'
  else
    vim.notify('Backend Build: unknown project', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd = 'dotnet clean "' .. build_target .. '" && dotnet build "' .. build_target .. '"'
  local build = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 44,
  })
  build:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Backend clean + build gestartet', vim.log.levels.INFO)
end, { desc = '[R]un [B]ackend [B]uild [C]lean | dotnet clean && dotnet build' })

-- Run ManualTestRunner (Docker profile) - assumes MockServer is already running in Docker
vim.keymap.set('n', '<leader>rmd', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('ManualTestRunner only for DCSRE', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local project = vim.g.project_backend_windows .. '\\VDEK.DCSP.DIC.MockServer.ManualTestRunner'
  local cmd = 'dotnet run --project "' .. project .. '" --launch-profile docker'
  local runner = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 42,
  })
  runner:toggle()
  vim.notify('[DCSRE] ManualTestRunner (Docker) gestartet', vim.log.levels.INFO)
end, { desc = '[R]un [M]ock [D]ocker | dotnet run --project ManualTestRunner --launch-profile docker' })

-- Run ManualTestRunner (Local profile) - assumes MockServer is already running locally
vim.keymap.set('n', '<leader>rml', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('ManualTestRunner only for DCSRE', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local project = vim.g.project_backend_windows .. '\\VDEK.DCSP.DIC.MockServer.ManualTestRunner'
  local cmd = 'dotnet run --project "' .. project .. '" --launch-profile https'
  local runner = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 43,
  })
  runner:toggle()
  vim.notify('[DCSRE] ManualTestRunner (Local) gestartet', vim.log.levels.INFO)
end, { desc = '[R]un [M]ock [L]ocal | dotnet run --project ManualTestRunner --launch-profile https' })

-- Quickfix: Show only warnings in quickfix list
vim.keymap.set('n', '<leader>qw', function()
  vim.diagnostic.setqflist({ severity = vim.diagnostic.severity.WARN })
  vim.cmd('copen')
end, { desc = '[Q]uickfix [W]arnings only' })
