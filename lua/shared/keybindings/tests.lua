-- lua/shared/keybindings/tests.lua
-- E2E + Integration Test Keybindings: reb, reg, rim, rid, riC, riF, rif, ris + TRX Infrastructure
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität

-- Helper: TEMP-Verzeichnis portabel ermitteln (Windows %TEMP%/%TMP%, sonst $TMPDIR/$TEMP, Fallback user_home\AppData\Local\Temp)
-- Ersetzt 8x hardcoded 'C:\Users\Administrator\AppData\Local\Temp' Fallback.
local function tests_temp()
  local t = os.getenv('TEMP') or os.getenv('TMP') or os.getenv('TMPDIR')
  if t and t ~= '' then return t end
  return platform.user_home_windows() .. '\\AppData\\Local\\Temp'
end

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

-- E2E by Tag: prompt fuer Ticket-Nr -> Telescope mit allen @DCSRE-XXXX-getaggten Feature-Files
-- Tab = multi-select, Enter = run alle gewaehlten, <C-h> = headed mode
vim.keymap.set('n', '<leader>ret', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local cypress_path = get_cypress_path_windows()
  if not cypress_path then
    vim.notify('Could not determine Cypress path', vim.log.levels.ERROR)
    return
  end

  vim.ui.input({ prompt = 'DCSRE Ticket-Nr (z.B. 1944 oder DCSRE-1944): ' }, function(input)
    if not input or input == '' then return end
    local tag
    if input:match('^%d+$') then
      tag = '@DCSRE-' .. input
    elseif input:match('^@') then
      tag = input
    elseif input:match('^DCSRE%-') then
      tag = '@' .. input
    else
      tag = '@DCSRE-' .. input
    end

    local e2e_path = cypress_path .. '\\e2e'
    local ps_cmd = string.format(
      'powershell.exe -NoProfile -Command "Get-ChildItem -Path \'%s\' -Filter *.feature -Recurse | Select-String -Pattern \'%s\' -List | Select-Object -ExpandProperty Path"',
      e2e_path,
      tag
    )
    local raw = vim.fn.systemlist(ps_cmd)

    local cypress_fwd = cypress_path:gsub('\\', '/')
    local prefix = cypress_fwd .. '/'
    local results = {}
    for _, line in ipairs(raw) do
      local trimmed = (line or ''):gsub('\r', ''):match('^%s*(.-)%s*$')
      if trimmed and trimmed ~= '' then
        local fwd = trimmed:gsub('\\', '/')
        local rel = vim.startswith(fwd, prefix) and fwd:sub(#prefix + 1) or fwd
        local display = rel:gsub('^e2e/', ''):gsub('%.feature$', '')
        table.insert(results, {
          path = trimmed,
          rel_path = rel,
          display = display,
        })
      end
    end

    if #results == 0 then
      vim.notify('Keine Feature-Files mit Tag ' .. tag .. ' gefunden.', vim.log.levels.WARN)
      return
    end

    table.sort(results, function(a, b) return a.display < b.display end)

    local pickers = require('telescope.pickers')
    local finders = require('telescope.finders')
    local conf = require('telescope.config').values
    local actions = require('telescope.actions')
    local action_state = require('telescope.actions.state')

    local function build_and_run(prompt_bufnr, headed)
      local picker = action_state.get_current_picker(prompt_bufnr)
      local multi = picker:get_multi_selection()
      actions.close(prompt_bufnr)

      local selected = {}
      if #multi > 0 then
        for _, sel in ipairs(multi) do
          table.insert(selected, sel.value.rel_path)
        end
      else
        local single = action_state.get_selected_entry()
        if single then
          table.insert(selected, single.value.rel_path)
        end
      end

      if #selected == 0 then
        vim.notify('Nichts ausgewaehlt', vim.log.levels.WARN)
        return
      end

      local spec_arg = table.concat(selected, ',')
      local headed_flag = headed and ' --headed' or ''
      local cmd = string.format(
        'powershell.exe -Command "Set-Location \'%s\'; npx cypress run%s --spec \'%s\'"',
        cypress_path,
        headed_flag,
        spec_arg
      )

      local mode_label = headed and 'HEADED' or 'HEADLESS'
      vim.notify(string.format('[DCSRE] %s %s: %d Spec(s)', tag, mode_label, #selected), vim.log.levels.INFO)

      local Terminal = require('toggleterm.terminal').Terminal
      local e2e_term = Terminal:new({
        cmd = cmd,
        id = headed and 31 or 30,
        direction = 'horizontal',
        close_on_exit = false,
      })
      e2e_term:toggle()
    end

    pickers.new({}, {
      prompt_title = string.format('E2E %s (%d) | Tab=multi, Enter=run, <C-h>=headed', tag, #results),
      finder = finders.new_table({
        results = results,
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
      attach_mappings = function(prompt_bufnr, map)
        actions.select_default:replace(function() build_and_run(prompt_bufnr, false) end)
        map('i', '<C-h>', function() build_and_run(prompt_bufnr, true) end)
        map('n', '<C-h>', function() build_and_run(prompt_bufnr, true) end)
        return true
      end,
    }):find()
  end)
end, { desc = '[R]un [E]2E by [T]ag | Prompt DCSRE-Nr -> Telescope tagged .feature files' })

-- E2E by Tag HEADED (single spec): prompt fuer Ticket-Nr -> Telescope mit @DCSRE-XXXX
-- Enter = die FOKUSSIERTE Spec im sichtbaren Browser (--headed)
-- Bewusst kein Multi-Select - genau eine Spec zum Debuggen mit den Augen.
vim.keymap.set('n', '<leader>reT', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local cypress_path = get_cypress_path_windows()
  if not cypress_path then
    vim.notify('Could not determine Cypress path', vim.log.levels.ERROR)
    return
  end

  vim.ui.input({ prompt = 'DCSRE Ticket-Nr (z.B. 1944): ' }, function(input)
    if not input or input == '' then return end
    local tag
    if input:match('^%d+$') then
      tag = '@DCSRE-' .. input
    elseif input:match('^@') then
      tag = input
    elseif input:match('^DCSRE%-') then
      tag = '@' .. input
    else
      tag = '@DCSRE-' .. input
    end

    local e2e_path = cypress_path .. '\\e2e'
    local ps_cmd = string.format(
      'powershell.exe -NoProfile -Command "Get-ChildItem -Path \'%s\' -Filter *.feature -Recurse | Select-String -Pattern \'%s\' -List | Select-Object -ExpandProperty Path"',
      e2e_path,
      tag
    )
    local raw = vim.fn.systemlist(ps_cmd)

    local cypress_fwd = cypress_path:gsub('\\', '/')
    local prefix = cypress_fwd .. '/'
    local results = {}
    for _, line in ipairs(raw) do
      local trimmed = (line or ''):gsub('\r', ''):match('^%s*(.-)%s*$')
      if trimmed and trimmed ~= '' then
        local fwd = trimmed:gsub('\\', '/')
        local rel = vim.startswith(fwd, prefix) and fwd:sub(#prefix + 1) or fwd
        local display = rel:gsub('^e2e/', ''):gsub('%.feature$', '')
        table.insert(results, {
          path = trimmed,
          rel_path = rel,
          display = display,
        })
      end
    end

    if #results == 0 then
      vim.notify('Keine Feature-Files mit Tag ' .. tag .. ' gefunden.', vim.log.levels.WARN)
      return
    end

    table.sort(results, function(a, b) return a.display < b.display end)

    local pickers = require('telescope.pickers')
    local finders = require('telescope.finders')
    local conf = require('telescope.config').values
    local actions = require('telescope.actions')
    local action_state = require('telescope.actions.state')

    pickers.new({}, {
      prompt_title = string.format('E2E %s HEADED (%d) | Enter = 1 Spec im Browser', tag, #results),
      finder = finders.new_table({
        results = results,
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
      attach_mappings = function(prompt_bufnr, _map)
        actions.select_default:replace(function()
          local entry = action_state.get_selected_entry()
          actions.close(prompt_bufnr)
          if not entry then
            vim.notify('Nichts ausgewaehlt', vim.log.levels.WARN)
            return
          end
          local spec = entry.value.rel_path
          local cmd = string.format(
            'powershell.exe -Command "Set-Location \'%s\'; npx cypress run --headed --no-exit --spec \'%s\'"',
            cypress_path,
            spec
          )
          vim.notify(string.format('[DCSRE] %s HEADED: %s', tag, entry.value.display), vim.log.levels.INFO)
          local Terminal = require('toggleterm.terminal').Terminal
          local e2e_term = Terminal:new({
            cmd = cmd,
            id = 31,
            direction = 'horizontal',
            close_on_exit = false,
          })
          e2e_term:toggle()
        end)
        return true
      end,
    }):find()
  end)
end, { desc = '[R]un [E]2E by [T]ag HEADED | 1 Spec im sichtbaren Browser' })

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
  local temp = tests_temp()
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
local function run_integration_tests(filter, label, terminal_id)
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
    return
  end

  local script_path = write_it_script(filter, label)

  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
    direction = 'horizontal',
    close_on_exit = false,
    count = terminal_id,
  })
  test:toggle()
  vim.notify('[DCSRE] Running Integration ' .. label .. ' tests...', vim.log.levels.INFO)
end

-- Parse TRX file → Lua table of {outcome, name}
local function parse_trx_results()
  local temp = tests_temp()
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

-- Cache: class_name → file size in KB (avoid repeated disk lookups)
local _file_size_cache = {}

-- Extrahiert Klassenname aus fully-qualified test name und gibt Dateigröße in KB zurück
-- z.B. "VDEK.DCSP.IntegrationTests.Foo.BarTest.Method" → "BarTest" → 14 KB
local function get_test_file_kb(test_name, test_dir)
  -- Klassenname = vorletztes Segment des FQN
  local segments = {}
  for seg in test_name:gmatch('[^.]+') do
    table.insert(segments, seg)
  end
  local class_name = #segments >= 2 and segments[#segments - 1] or segments[#segments]
  if not class_name then return nil end

  if _file_size_cache[class_name] ~= nil then
    return _file_size_cache[class_name]
  end

  local matches = vim.fn.globpath(test_dir, '**\\' .. class_name .. '.cs', false, true)
  -- Filtere obj/ Ordner raus
  local file
  for _, m in ipairs(matches) do
    if not m:match('\\obj\\') then file = m; break end
  end

  local kb = nil
  if file then
    local size = vim.fn.getfsize(file)
    if size > 0 then kb = math.ceil(size / 1024) end
  end
  _file_size_cache[class_name] = kb
  return kb
end

-- Telescope picker for test results (shared by rif and ris)
local function telescope_test_picker(title, test_list)
  local test_dir = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
  local pickers = require('telescope.pickers')
  local finders = require('telescope.finders')
  local conf = require('telescope.config').values
  local actions = require('telescope.actions')
  local action_state = require('telescope.actions.state')
  local entry_display = require('telescope.pickers.entry_display')

  -- Spalten: [icon 2] [testname flex] [KB 7 right]
  local displayer = entry_display.create({
    separator = ' ',
    items = {
      { width = 2 },
      { remaining = true },
      { width = 7, right_justify = true },
    },
  })

  pickers
    .new({}, {
      prompt_title = title,
      finder = finders.new_table({
        results = test_list,
        entry_maker = function(entry)
          local icon = entry.outcome == 'Passed' and 'V ' or entry.outcome == 'Failed' and 'X ' or '- '
          local kb = get_test_file_kb(entry.name, test_dir)
          local kb_str = kb and (kb .. ' KB') or '?'
          local short_name = entry.name:gsub('^.*IntegrationTests%.', '')
          return {
            value = entry.name,
            display = function()
              return displayer({ icon, short_name, kb_str })
            end,
            ordinal = short_name,
          }
        end,
      }),
      sorter = require('telescope.config').values.generic_sorter({}),
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

          local temp = tests_temp()
          local it_trx = temp .. '\\it-latest.trx'
          local rerun_trx = temp .. '\\it-rerun.trx'
          -- Script: re-run mit TRX + merge back into it-latest.trx
          local script_path = temp .. '\\run-it-rerun.ps1'
          local script = string.format([[$ErrorActionPreference = "Continue"
$rerunTrx = "%s"
$mainTrx  = "%s"
if (Test-Path $rerunTrx) { Remove-Item $rerunTrx -Force }
dotnet test '%s' --no-build --no-restore --filter '%s' --verbosity detailed --logger "console;verbosity=detailed" --logger "trx;LogFileName=$rerunTrx"

# Merge re-run results back into main TRX (round-based convergence)
if ((Test-Path $rerunTrx) -and (Test-Path $mainTrx)) {
    [xml]$mainXml  = Get-Content $mainTrx
    [xml]$rerunXml = Get-Content $rerunTrx
    $merged = 0
    foreach ($newTest in $rerunXml.TestRun.Results.UnitTestResult) {
        $match = $mainXml.TestRun.Results.UnitTestResult | Where-Object { $_.testName -eq $newTest.testName }
        if ($match) {
            $match.outcome = $newTest.outcome
            $merged++
        }
    }
    $mainXml.Save($mainTrx)
    $nowGreen = @($rerunXml.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Passed' }).Count
    $stillRed = @($mainXml.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' }).Count
    Write-Host ""
    Write-Host ("  Merge: {0} aktualisiert, {1} jetzt GRUEN, {2} noch FAILED" -f $merged, $nowGreen, $stillRed) -ForegroundColor Magenta
    Write-Host "  Hint: riF = verbleibende Failed anzeigen" -ForegroundColor DarkGray
} elseif (Test-Path $rerunTrx) {
    Write-Host ""
    [xml]$r = Get-Content $rerunTrx
    $p = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Passed' }).Count
    $f = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' }).Count
    Write-Host ("  Re-run: {0} Passed, {1} Failed (kein Merge - it-latest.trx fehlt)" -f $p, $f) -ForegroundColor Yellow
}]], rerun_trx, it_trx, test_dir, filter)
          local file = io.open(script_path, 'w')
          if file then file:write(script); file:close() end

          local Terminal = require('toggleterm.terminal').Terminal
          local test = Terminal:new({
            cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
            direction = 'horizontal',
            close_on_exit = false,
            count = 42,
          })
          test:toggle()
          vim.notify('[DCSRE] Re-running ' .. #selections .. ' test(s)...', vim.log.levels.INFO)
        end)
        return true
      end,
    })
    :find()
end

-- <leader>rim - Run Integration Mock (DicMockServer, TRX summary)
vim.keymap.set('n', '<leader>rim', function()
  run_integration_tests('FullyQualifiedName~IntegrationTests&FullyQualifiedName~DicMockServer', 'Mock', 40)
end, { desc = '[DEPRECATED -> rT3] [R]un [I]ntegration [M]ock | DicMockServer + TRX summary' })

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
    -- DCSRE: Integration DB tests (ohne DicMockServer, TRX summary)
    run_integration_tests('FullyQualifiedName~IntegrationTests&FullyQualifiedName!~DicMockServer', 'DB', 41)
  end
end, { desc = '[DEPRECATED -> rT4/rT3] [R]un [I]ntegration [D]ocker | DCSRE: DB tests | CENCOCD: IsolatedDocker' })

-- <leader>riR - Run Integration Retry (bis zu N Runden, nur noch-fehlgeschlagene)
-- Flaky-Test-Filter: nach 3 Runden bleiben nur wirklich kaputte Tests übrig
vim.keymap.set('n', '<leader>riR', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Retry only for DCSRE', vim.log.levels.WARN)
    return
  end

  local temp = tests_temp()
  if vim.fn.filereadable(temp .. '\\it-latest.trx') == 0 then
    vim.notify('Kein TRX gefunden. Zuerst <leader>rim oder <leader>rid ausführen!', vim.log.levels.WARN)
    return
  end

  vim.ui.input({ prompt = 'Max Runden (default 3): ' }, function(rounds_input)
    if rounds_input == nil then return end
    local max_rounds = tonumber(rounds_input) or 3

    -- Threads NICHT ändern — läuft mit der aktuell gesetzten Zahl aus xunit.runner.json
    local test_dir   = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
      local script_path = temp .. '\\run-it-retry.ps1'
      local trx_path    = temp .. '\\it-latest.trx'

      local script = string.format([[
$ErrorActionPreference = "Continue"
$trx       = "%s"
$testDir   = "%s"
$maxRounds = %d
$prevFailed = 9999

Write-Host ""
Write-Host "=== RETRY-MODUS: bis zu $($maxRounds) Runden ===" -ForegroundColor Cyan

for ($round = 1; $round -le $maxRounds; $round++) {
    if (-not (Test-Path $trx)) {
        Write-Host "  [Round $($round)] Kein TRX - Abbruch." -ForegroundColor Red
        break
    }
    [xml]$r = Get-Content $trx
    $failed = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' })

    if ($failed.Count -eq 0) {
        Write-Host "  [Round $($round)] Alle Tests GRUEN!" -ForegroundColor Green
        break
    }
    if ($failed.Count -eq $prevFailed) {
        Write-Host "  [Round $($round)] Keine Verbesserung ($($failed.Count) fehlgeschlagen) - wirklich kaputt!" -ForegroundColor Red
        break
    }

    Write-Host ""
    Write-Host "  --- Round $($round): $($failed.Count) fehlgeschlagen - erneut starten ---" -ForegroundColor Yellow
    $prevFailed = $failed.Count
    $filterParts = $failed | ForEach-Object { "FullyQualifiedName=" + $_.testName }
    $filter = $filterParts -join "|"
    Remove-Item $trx -Force

    dotnet test $testDir --no-build --no-restore --filter $filter --logger "console;verbosity=detailed" --logger "trx;LogFileName=$trx" --verbosity detailed
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  ERGEBNIS nach $($maxRounds) Runden:" -ForegroundColor Cyan
if (Test-Path $trx) {
    [xml]$r = Get-Content $trx
    $f = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' })
    if ($f.Count -eq 0) {
        Write-Host "  ALLE GRUEN - Tests waren flaky!" -ForegroundColor Green
    } else {
        Write-Host "  WIRKLICH KAPUTT ($($f.Count) Tests):" -ForegroundColor Red
        foreach ($t in $f) {
            Write-Host ("  X " + $t.testName) -ForegroundColor Red
            if ($t.Output -and $t.Output.ErrorInfo -and $t.Output.ErrorInfo.Message) {
                $msg = $t.Output.ErrorInfo.Message
                if ($msg.Length -gt 200) { $msg = $msg.Substring(0, 200) + "..." }
                Write-Host ("    " + $msg) -ForegroundColor Yellow
            }
        }
    }
}
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Hint: <leader>riF = Failed anzeigen" -ForegroundColor DarkGray
]], trx_path, test_dir, max_rounds)

      local file = io.open(script_path, 'w')
      if file then file:write(script); file:close() end

      local Terminal = require('toggleterm.terminal').Terminal
      local term = Terminal:new({
        cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
        direction = 'horizontal',
        close_on_exit = false,
        count = 44,
      })
      term:toggle()
      vim.notify('[DCSRE] Retry-Modus: bis zu ' .. max_rounds .. ' Runden (Threads aus xunit.runner.json)...', vim.log.levels.INFO)
  end)
end, { desc = '[DEPRECATED -> rTR] [R]un [I]ntegration [R]etry | Flaky-Filter (liest it-latest.trx)' })

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
      .. "Write-Host '=== Remove ALL Docker images ===' -ForegroundColor Cyan; "
      .. "docker images -q | ForEach-Object { docker rmi -f $_ }; "
      .. "Write-Host '=== Clear ALL build cache ===' -ForegroundColor Cyan; "
      .. "docker builder prune -f --all; "
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

-- <leader>riD - Run Integration Delete (nur MockServer-Image löschen — der Bottleneck)
vim.keymap.set('n', '<leader>riD', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('riD nur fuer DCSRE', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local clean = Terminal:new({
    cmd = 'powershell.exe -NoProfile -Command "docker rmi dic-mock-server:integration-test -f; Write-Host \'MockServer-Image geloescht. Wird beim naechsten Test neu gebaut.\' -ForegroundColor Green"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 43,
  })
  clean:toggle()
  vim.notify('[DCSRE] Lösche dic-mock-server:integration-test...', vim.log.levels.INFO)
end, { desc = '[R]un [I]ntegration [D]elete | docker rmi dic-mock-server:integration-test (gezielt)' })

-- <leader>riA - Run Integration All (Mock + DB, sequentiell 38T→8T, TRX merge → it-latest.trx)
vim.keymap.set('n', '<leader>riA', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('riA nur fuer DCSRE', vim.log.levels.WARN)
    return
  end

  local temp = tests_temp()
  local it_trx   = temp .. '\\it-latest.trx'
  local db_trx   = temp .. '\\it-db.trx'
  local test_dir = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
  local script_path = temp .. '\\run-it-all.ps1'

  local script = string.format([[$ErrorActionPreference = "Continue"
$trx   = "%s"
$dbTrx = "%s"
$dir   = "%s"
$start = Get-Date

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  riA: ALLE Integration Tests (DCSRE)" -ForegroundColor Cyan
Write-Host "  Start: $($start.ToString('HH:mm:ss'))" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan

# === PHASE 1: Mock ===
Write-Host ""
Write-Host "=== PHASE 1: DicMockServer ===" -ForegroundColor Yellow
if (Test-Path $trx) { Remove-Item $trx -Force }
dotnet test "$dir" --no-build --no-restore --filter "FullyQualifiedName~IntegrationTests&FullyQualifiedName~DicMockServer" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$trx" --verbosity detailed
if (Test-Path $trx) {
    [xml]$r = Get-Content $trx
    $p = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Passed' }).Count
    $f = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' }).Count
    $c = if ($f -gt 0) { 'Red' } else { 'Green' }
    Write-Host ("  => Mock: PASSED={0}  FAILED={1}" -f $p, $f) -ForegroundColor $c
}

# === PHASE 2: DB ===
Write-Host ""
Write-Host "=== PHASE 2: DB Tests ===" -ForegroundColor Yellow
if (Test-Path $dbTrx) { Remove-Item $dbTrx -Force }
dotnet test "$dir" --no-build --no-restore --filter "FullyQualifiedName~IntegrationTests&FullyQualifiedName!~DicMockServer" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$dbTrx" --verbosity detailed
if (Test-Path $dbTrx) {
    [xml]$r = Get-Content $dbTrx
    $p = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Passed' }).Count
    $f = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' }).Count
    $c = if ($f -gt 0) { 'Red' } else { 'Green' }
    Write-Host ("  => DB: PASSED={0}  FAILED={1}" -f $p, $f) -ForegroundColor $c
}

# === MERGE: DB results → it-latest.trx ===
if ((Test-Path $trx) -and (Test-Path $dbTrx)) {
    Write-Host ""
    Write-Host "  Merge DB → it-latest.trx..." -ForegroundColor DarkGray
    [xml]$mainXml = Get-Content $trx
    [xml]$dbXml   = Get-Content $dbTrx
    foreach ($node in $dbXml.TestRun.Results.UnitTestResult) {
        $imp = $mainXml.ImportNode($node, $true)
        $mainXml.TestRun.Results.AppendChild($imp) | Out-Null
    }
    foreach ($node in $dbXml.TestRun.TestDefinitions.UnitTest) {
        $imp = $mainXml.ImportNode($node, $true)
        $mainXml.TestRun.TestDefinitions.AppendChild($imp) | Out-Null
    }
    $mainXml.Save($trx)
} elseif (Test-Path $dbTrx) {
    Copy-Item $dbTrx $trx -Force
}

# === ZUSAMMENFASSUNG ===
$end = Get-Date
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ("  Dauer: $(($end - $start).ToString('hh\:mm\:ss'))") -ForegroundColor Gray
if (Test-Path $trx) {
    [xml]$r = Get-Content $trx
    $all = $r.TestRun.Results.UnitTestResult
    $p = @($all | Where-Object { $_.outcome -eq 'Passed' }).Count
    $f = @($all | Where-Object { $_.outcome -eq 'Failed' }).Count
    $s = @($all | Where-Object { $_.outcome -eq 'NotExecuted' }).Count
    $c = if ($f -gt 0) { 'Red' } else { 'Green' }
    Write-Host ("  TOTAL: PASSED={0}  FAILED={1}  SKIPPED={2}" -f $p, $f, $s) -ForegroundColor $c
    if ($f -gt 0) {
        Write-Host "  Hint: <leader>riF = Failed re-run" -ForegroundColor DarkGray
    }
}
Write-Host "========================================" -ForegroundColor Cyan
]], it_trx, db_trx, test_dir)

  local file = io.open(script_path, 'w')
  if file then file:write(script); file:close() end

  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 44,
  })
  test:toggle()
  vim.notify('[DCSRE] riA: Alle Integration Tests (Mock → DB → merge)...', vim.log.levels.INFO)
end, { desc = '[R]un [I]ntegration [A]ll | DCSRE: Mock(38T) + DB(8T) sequentiell → it-latest.trx → riF' })

-- <leader>riF - Run Integration Failed (Telescope picker, Tab=multi-select, Enter=re-run)
vim.keymap.set('n', '<leader>riF', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
    return
  end

  local temp = tests_temp()
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
end, { desc = '[DEPRECATED -> rTF] [R]un [I]ntegration [F]ailed | Telescope picker (liest it-latest.trx)' })

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
  -- ROBUSTER Prefix-Strip: beide Seiten auf Forward-Slash normalisieren.
  -- Vorher: file:gsub(test_root:gsub('\\','\\\\')..'\\', '') — Lua-Pattern mit
  -- doppelten Backslashes matchte nicht gegen Single-Backslashes in globpath-Ergebnis,
  -- daher landete der FULL PATH im Display → unbrauchbarer Filter.
  local prefix_fwd = (test_root:gsub('\\', '/')) .. '/'
  for _, file in ipairs(all_files) do
    local file_fwd = file:gsub('\\', '/')
    if not file_fwd:match('/obj/') then
      local rel
      if vim.startswith(file_fwd, prefix_fwd) then
        rel = file_fwd:sub(#prefix_fwd + 1)
      else
        rel = file_fwd
      end
      local display = rel:gsub('%.cs$', '')
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
    sorter = require('telescope.config').values.generic_sorter({}),
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
          -- rel ist jetzt forward-slash-normalisiert (siehe rel-fix oben)
          local class_name = sel.rel:match('([^/\\]+)%.cs$')
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

  local temp = tests_temp()
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
end, { desc = '[DEPRECATED -> rTS] [R]un [I]ntegration [S]earch | Telescope picker (liest it-latest.trx)' })

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

-- === Test-Stufen-System (rT*) — Project-aware (DCSRE + CenCoCo) ===
-- 5 Stufen pro Projekt mit TRX-Integration, Telescope-Picker und Retry
-- DCSRE:   BE Unit → FE Unit → Integration Mock (38T) → Integration DB (8T) → E2E Cypress
-- CenCoCo: Unit → Integration → IsolatedDocker → Blazor System → E2E Playwright
-- Alte ri*/re* bleiben als [DEPRECATED] Fallback.

-- Shared state
local rt_temp = tests_temp()
local rt_trx = rt_temp .. '\\rt-latest.trx'
vim.g.cencoco_headed = false

-- Write PowerShell script: dotnet test + TRX summary (rT* version)
-- stage: optional stage number (1-5) → copies TRX to rt-stage{N}.trx for sT*/fT* pickers
-- merge_stage: optional stage number → merges re-run results back into rt-stage{N}.trx (round-based)
local function write_rt_script(dotnet_cmd, stage, merge_stage)
  local script_path = rt_temp .. '\\run-rt.ps1'
  local stage_copy = ''
  if stage then
    stage_copy = string.format('\nif (Test-Path $trx) { Copy-Item $trx "%s\\rt-stage%d.trx" -Force }', rt_temp, stage)
  end
  local merge_back = ''
  if merge_stage then
    local stage_file = rt_temp .. '\\rt-stage' .. merge_stage .. '.trx'
    merge_back = string.format([[

# Merge re-run results back into stage TRX (round-based convergence)
$stageTrx = "%s"
if ((Test-Path $trx) -and (Test-Path $stageTrx)) {
    [xml]$stageXml = Get-Content $stageTrx
    [xml]$newXml = Get-Content $trx
    $merged = 0
    foreach ($newTest in $newXml.TestRun.Results.UnitTestResult) {
        $match = $stageXml.TestRun.Results.UnitTestResult | Where-Object { $_.testName -eq $newTest.testName }
        if ($match) {
            $match.outcome = $newTest.outcome
            $merged++
        }
    }
    $stageXml.Save($stageTrx)
    $nowGreen = @($newXml.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Passed' }).Count
    $stillRed = @($stageXml.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' }).Count
    Write-Host ""
    Write-Host ("  Merge: {0} Tests aktualisiert, {1} jetzt GRUEN, {2} noch FAILED in Stage {3}" -f $merged, $nowGreen, $stillRed, %d) -ForegroundColor Magenta
    Write-Host "  Hint: fT%d = verbleibende Failed anzeigen" -ForegroundColor DarkGray
}]], stage_file, merge_stage, merge_stage)
  end
  local script = string.format([[$ErrorActionPreference = "Continue"
$trx = "%s"
if (Test-Path $trx) { Remove-Item $trx -Force }
%s --logger "trx;LogFileName=$trx"%s%s
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
    Write-Host "  Hint: rTF = Failed | rTS = All (Telescope) | rTR = Retry" -ForegroundColor DarkGray
} else {
    Write-Host "TRX not found - tests may not have run!" -ForegroundColor Red
}]], rt_trx, dotnet_cmd, stage_copy, merge_back)
  local file = io.open(script_path, 'w')
  if file then file:write(script); file:close() end
  return script_path
end

-- Run dotnet test stage with TRX output
local function run_rt_dotnet(label, dotnet_cmd, terminal_id, opts)
  opts = opts or {}

  -- Thread management (DCSRE only)
  if opts.threads and vim.g.project_name == 'DCSRE' then
    if not set_xunit_threads(opts.threads) then return end
    vim.notify('[DCSRE] threads=' .. opts.threads, vim.log.levels.INFO)
  end

  -- Headed mode (CenCoCo Playwright)
  if opts.headed and vim.g.cencoco_headed then
    dotnet_cmd = '$env:HEADED=\\"1\\"; ' .. dotnet_cmd
  end

  local script_path = write_rt_script(dotnet_cmd, opts.stage, opts.merge_stage)
  local on_exit_fn = nil
  if opts.threads and vim.g.project_name == 'DCSRE' then
    on_exit_fn = function()
      set_xunit_threads(1)
      vim.notify('[DCSRE] Reset threads=1', vim.log.levels.INFO)
    end
  end

  local Terminal = require('toggleterm.terminal').Terminal
  local term = Terminal:new({
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
    direction = 'horizontal',
    close_on_exit = false,
    count = terminal_id,
    on_exit = on_exit_fn,
  })
  term:toggle()
  local headed_hint = (opts.headed and vim.g.cencoco_headed) and ' [HEADED]' or ''
  vim.notify('[' .. vim.g.project_name .. '] ' .. label .. headed_hint .. '...', vim.log.levels.INFO)
end

-- Run npm/cypress stage (no TRX)
local function run_rt_npm(label, npm_cmd, cwd, terminal_id)
  local Terminal = require('toggleterm.terminal').Terminal
  local term = Terminal:new({
    cmd = 'powershell.exe -NoProfile -Command "Set-Location \'' .. cwd .. '\'; ' .. npm_cmd .. '"',
    direction = 'horizontal',
    close_on_exit = false,
    count = terminal_id,
  })
  term:toggle()
  vim.notify('[' .. vim.g.project_name .. '] ' .. label .. '...', vim.log.levels.INFO)
end

-- Parse TRX → Lua table of {outcome, name}
-- trx_path: optional, defaults to rt-latest.trx
local function parse_rt_trx(trx_path)
  trx_path = trx_path or rt_trx
  local parsed_file = rt_temp .. '\\rt-parsed.txt'
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

-- Get solution path for re-run from Telescope/Retry
local function get_rt_solution()
  if vim.g.project_name == 'DCSRE' then
    return vim.g.project_backend_windows .. '\\VDEK.DCSP.sln'
  elseif vim.g.project_name == 'CENCOCD' then
    return vim.g.project_root_windows .. '\\src\\CenCoCo.sln'
  end
  return nil
end

-- Telescope picker for rT* results (re-run selected on Enter)
-- opts.merge_stage: if set, merges re-run results back into rt-stage{N}.trx (round-based convergence)
local function telescope_rt_picker(title, test_list, opts)
  opts = opts or {}
  local sln = get_rt_solution()
  if not sln then return end

  local pickers = require('telescope.pickers')
  local finders = require('telescope.finders')
  local conf = require('telescope.config').values
  local actions = require('telescope.actions')
  local action_state = require('telescope.actions.state')

  pickers.new({}, {
    prompt_title = title,
    finder = finders.new_table({
      results = test_list,
      entry_maker = function(entry)
        local icon = entry.outcome == 'Passed' and 'V ' or entry.outcome == 'Failed' and 'X ' or '- '
        local short = entry.name:gsub('^.*IntegrationTests%.', ''):gsub('^.*%.Tests%.', ''):gsub('^.*%.SystemTests%.', ''):gsub('^.*%.E2ETests%.', '')
        return {
          value = entry.name,
          display = icon .. short,
          ordinal = short,
        }
      end,
    }),
    sorter = require('telescope.config').values.generic_sorter({}),
    attach_mappings = function(prompt_bufnr)
      actions.select_default:replace(function()
        local picker = action_state.get_current_picker(prompt_bufnr)
        local selections = picker:get_multi_selection()
        if #selections == 0 then
          local entry = action_state.get_selected_entry()
          if entry then selections = { entry } end
        end
        actions.close(prompt_bufnr)
        if #selections == 0 then return end

        local filter_parts = {}
        for _, sel in ipairs(selections) do
          table.insert(filter_parts, 'FullyQualifiedName=' .. sel.value)
        end
        local filter = table.concat(filter_parts, '|')

        local dotnet_cmd = "dotnet test '" .. sln .. "' --filter \"" .. filter .. "\" --logger \"console;verbosity=detailed\""
        run_rt_dotnet('Re-run ' .. #selections .. ' test(s)', dotnet_cmd, 56, { merge_stage = opts.merge_stage })
      end)
      return true
    end,
  }):find()
end

-- === rT1-rT5: Project-aware Stage Keybindings ===

-- <leader>rT1 - Stufe 1: Unit Tests
vim.keymap.set('n', '<leader>rT1', function()
  if vim.g.project_name == 'DCSRE' then
    local sln = vim.g.project_backend_windows .. '\\VDEK.DCSP.sln'
    run_rt_dotnet('Stufe 1: BE Unit Tests',
      "dotnet test '" .. sln .. "' --filter \"(Category!=Database)&(Category!=Storage)&(Category!=Email)&(Category!=Docker)\" --no-build --logger \"console;verbosity=detailed\"",
      50)
  elseif vim.g.project_name == 'CENCOCD' then
    local sln = vim.g.project_root_windows .. '\\src\\CenCoCo.sln'
    run_rt_dotnet('Stufe 1: Unit Tests (Laserpointer)',
      "dotnet test '" .. sln .. "' --filter \"Category!=E2E&Category!=SystemTest&Category!=IsolatedDocker&Category!=IntegrationTests\" --logger \"console;verbosity=detailed\"",
      50, { stage = 1 })
  else
    vim.notify('rT* nur fuer DCSRE/CenCoCo', vim.log.levels.WARN)
  end
end, { desc = '[R]un [T]est Stufe [1] | DCSRE: BE Unit | CenCoCo: Unit (Laserpointer)' })

-- <leader>rT2 - Stufe 2: FE Unit (DCSRE) / Integration (CenCoCo)
vim.keymap.set('n', '<leader>rT2', function()
  if vim.g.project_name == 'DCSRE' then
    run_rt_npm('Stufe 2: FE Unit Tests (Jest)', 'npm run test:ci', vim.g.project_frontend, 51)
  elseif vim.g.project_name == 'CENCOCD' then
    local sln = vim.g.project_root_windows .. '\\src\\CenCoCo.sln'
    run_rt_dotnet('Stufe 2: Integration Tests (Scheinwerfer)',
      "dotnet test '" .. sln .. "' --filter \"Category=IntegrationTests\" --logger \"console;verbosity=detailed\"",
      51, { stage = 2 })
  else
    vim.notify('rT* nur fuer DCSRE/CenCoCo', vim.log.levels.WARN)
  end
end, { desc = '[R]un [T]est Stufe [2] | DCSRE: FE Unit (Jest) | CenCoCo: Integration (Scheinwerfer)' })

-- <leader>rT3 - Stufe 3: Integration Mock/38T (DCSRE) / IsolatedDocker (CenCoCo)
vim.keymap.set('n', '<leader>rT3', function()
  if vim.g.project_name == 'DCSRE' then
    local it = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
    run_rt_dotnet('Stufe 3: Integration Mock (DicMockServer)',
      "dotnet test '" .. it .. "' --no-build --no-restore --filter \"FullyQualifiedName~IntegrationTests&FullyQualifiedName~DicMockServer\" --logger \"console;verbosity=detailed\"",
      52, { threads = 38 })
  elseif vim.g.project_name == 'CENCOCD' then
    -- 2 Befehle: sln-Filter + separates Accounting-Projekt (nicht in sln!)
    local sln = vim.g.project_root_windows .. '\\src\\CenCoCo.sln'
    local accounting = vim.g.project_root_windows .. '\\tests\\CenCoCo.Accounting.SystemTests'
    local combined_cmd = "dotnet test '" .. sln .. "' --filter \"Category=IsolatedDocker\" --logger \"console;verbosity=detailed\""
      .. "; Write-Host '--- Accounting.SystemTests (nicht in sln) ---' -ForegroundColor Cyan"
      .. "; dotnet test '" .. accounting .. "' --logger \"console;verbosity=detailed\""
    run_rt_dotnet('Stufe 3: Isolated Docker (Taschenlampe)', combined_cmd, 52, { stage = 3 })
  else
    vim.notify('rT* nur fuer DCSRE/CenCoCo', vim.log.levels.WARN)
  end
end, { desc = '[R]un [T]est Stufe [3] | DCSRE: Integration Mock (38T) | CenCoCo: IsolatedDocker (+ Accounting)' })

-- <leader>rT4 - Stufe 4: Integration DB/8T (DCSRE) / Blazor System (CenCoCo)
vim.keymap.set('n', '<leader>rT4', function()
  if vim.g.project_name == 'DCSRE' then
    local it = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
    run_rt_dotnet('Stufe 4: Integration DB',
      "dotnet test '" .. it .. "' --no-build --no-restore --filter \"FullyQualifiedName~IntegrationTests&FullyQualifiedName!~DicMockServer\" --logger \"console;verbosity=detailed\"",
      53, { threads = 8 })
  elseif vim.g.project_name == 'CENCOCD' then
    run_rt_dotnet('Stufe 4: Blazor System Tests (Buehnenbeleuchtung)',
      "dotnet test '" .. vim.g.project_root_windows .. "\\tests\\CenCoCo.Blazor.SystemTests' --filter \"Category=SystemTest\" --logger \"console;verbosity=detailed\"",
      53, { headed = true, stage = 4 })
  else
    vim.notify('rT* nur fuer DCSRE/CenCoCo', vim.log.levels.WARN)
  end
end, { desc = '[R]un [T]est Stufe [4] | DCSRE: Integration DB (8T) | CenCoCo: Blazor System' })

-- <leader>rT5 - Stufe 5: E2E Gesamtsystem (DCSRE) / E2E Playwright (CenCoCo)
vim.keymap.set('n', '<leader>rT5', function()
  if vim.g.project_name == 'DCSRE' then
    local cypress = get_cypress_path_windows()
    if not cypress then
      vim.notify('Cypress path not found', vim.log.levels.ERROR)
      return
    end
    run_rt_npm('Stufe 5: E2E Gesamtsystemtest (Cypress)', 'npm run cypress:run:gesamtsystemtest', cypress, 54)
  elseif vim.g.project_name == 'CENCOCD' then
    run_rt_dotnet('Stufe 5: E2E Tests (Flutlicht)',
      "dotnet test '" .. vim.g.project_root_windows .. "\\tests\\CenCoCo.Blazor.E2ETests' --filter \"Category=E2E\" --logger \"console;verbosity=detailed\"",
      54, { headed = true, stage = 5 })
  else
    vim.notify('rT* nur fuer DCSRE/CenCoCo', vim.log.levels.WARN)
  end
end, { desc = '[R]un [T]est Stufe [5] | DCSRE: E2E Gesamtsystem (Cypress) | CenCoCo: E2E (Flutlicht)' })

-- === rTR/rTF/rTS: Retry, Failed Picker, Search (TRX-basiert) ===

-- <leader>rTR - Retry failed tests from rt-latest.trx (N rounds)
vim.keymap.set('n', '<leader>rTR', function()
  if vim.g.project_name ~= 'DCSRE' and vim.g.project_name ~= 'CENCOCD' then
    vim.notify('rTR nur fuer DCSRE/CenCoCo', vim.log.levels.WARN)
    return
  end
  if vim.fn.filereadable(rt_trx) == 0 then
    vim.notify('Kein TRX gefunden. Zuerst rT1-rT5 ausfuehren!', vim.log.levels.WARN)
    return
  end

  vim.ui.input({ prompt = 'Max Runden (default 3): ' }, function(input)
    if input == nil then return end
    local max_rounds = tonumber(input) or 3
    local sln = get_rt_solution()
    if not sln then return end

    local script_path = rt_temp .. '\\run-rt-retry.ps1'
    local script = string.format([[
$ErrorActionPreference = "Continue"
$trx       = "%s"
$sln       = "%s"
$maxRounds = %d
$prevFailed = 9999

Write-Host ""
Write-Host "=== RETRY-MODUS: bis zu $($maxRounds) Runden ===" -ForegroundColor Cyan

for ($round = 1; $round -le $maxRounds; $round++) {
    if (-not (Test-Path $trx)) {
        Write-Host "  [Round $($round)] Kein TRX - Abbruch." -ForegroundColor Red
        break
    }
    [xml]$r = Get-Content $trx
    $failed = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' })

    if ($failed.Count -eq 0) {
        Write-Host "  [Round $($round)] Alle Tests GRUEN!" -ForegroundColor Green
        break
    }
    if ($failed.Count -eq $prevFailed) {
        Write-Host "  [Round $($round)] Keine Verbesserung ($($failed.Count) fehlgeschlagen) - wirklich kaputt!" -ForegroundColor Red
        break
    }

    Write-Host ""
    Write-Host "  --- Round $($round): $($failed.Count) fehlgeschlagen - erneut starten ---" -ForegroundColor Yellow
    $prevFailed = $failed.Count
    $filterParts = $failed | ForEach-Object { "FullyQualifiedName=" + $_.testName }
    $filter = $filterParts -join "|"
    Remove-Item $trx -Force

    dotnet test $sln --filter $filter --logger "console;verbosity=detailed" --logger "trx;LogFileName=$trx" --verbosity detailed
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  ERGEBNIS nach $($maxRounds) Runden:" -ForegroundColor Cyan
if (Test-Path $trx) {
    [xml]$r = Get-Content $trx
    $f = @($r.TestRun.Results.UnitTestResult | Where-Object { $_.outcome -eq 'Failed' })
    if ($f.Count -eq 0) {
        Write-Host "  ALLE GRUEN - Tests waren flaky!" -ForegroundColor Green
    } else {
        Write-Host "  WIRKLICH KAPUTT ($($f.Count) Tests):" -ForegroundColor Red
        foreach ($t in $f) {
            Write-Host ("  X " + $t.testName) -ForegroundColor Red
            if ($t.Output -and $t.Output.ErrorInfo -and $t.Output.ErrorInfo.Message) {
                $msg = $t.Output.ErrorInfo.Message
                if ($msg.Length -gt 200) { $msg = $msg.Substring(0, 200) + "..." }
                Write-Host ("    " + $msg) -ForegroundColor Yellow
            }
        }
    }
}
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Hint: rTF = Failed anzeigen | rTS = Alle anzeigen" -ForegroundColor DarkGray
]], rt_trx, sln, max_rounds)

    local file = io.open(script_path, 'w')
    if file then file:write(script); file:close() end

    local Terminal = require('toggleterm.terminal').Terminal
    local term = Terminal:new({
      cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
      direction = 'horizontal',
      close_on_exit = false,
      count = 57,
    })
    term:toggle()
    vim.notify('[' .. vim.g.project_name .. '] Retry: bis zu ' .. max_rounds .. ' Runden...', vim.log.levels.INFO)
  end)
end, { desc = '[R]un [T]est [R]etry | Flaky-Filter: N Runden, nur noch-fehlgeschlagene (TRX)' })

-- <leader>rTF - Failed tests from rt-latest.trx (Telescope picker, Tab=multi, Enter=re-run)
vim.keymap.set('n', '<leader>rTF', function()
  if vim.fn.filereadable(rt_trx) == 0 then
    vim.notify('Kein TRX gefunden. Zuerst rT1-rT5 ausfuehren!', vim.log.levels.WARN)
    return
  end
  local all = parse_rt_trx()
  local failed = vim.tbl_filter(function(r) return r.outcome == 'Failed' end, all)
  if #failed == 0 then
    vim.notify('Keine fehlgeschlagenen Tests! Alle ' .. #all .. ' bestanden.', vim.log.levels.INFO)
    return
  end
  telescope_rt_picker('rT* Failed (' .. #failed .. ') | Tab=select, Enter=re-run', failed)
end, { desc = '[R]un [T]est [F]ailed | Telescope picker fuer fehlgeschlagene Tests (TRX)' })

-- <leader>rTS - Search all tests from rt-latest.trx (Telescope picker)
vim.keymap.set('n', '<leader>rTS', function()
  if vim.fn.filereadable(rt_trx) == 0 then
    vim.notify('Kein TRX gefunden. Zuerst rT1-rT5 ausfuehren!', vim.log.levels.WARN)
    return
  end
  local all = parse_rt_trx()
  if #all == 0 then
    vim.notify('Keine Testergebnisse im TRX.', vim.log.levels.WARN)
    return
  end
  telescope_rt_picker('rT* Tests (' .. #all .. ') | Tab=select, Enter=re-run', all)
end, { desc = '[R]un [T]est [S]earch | Telescope picker fuer alle Tests (TRX)' })

-- === sT1-5 / fT1-5: Per-Stage Telescope Pickers (CenCoCo) ===

-- Helper: stage TRX path
local function rt_stage_file(n)
  return rt_temp .. '\\rt-stage' .. n .. '.trx'
end

-- Stage names for CenCoCo
local rt_stage_names = {
  [1] = 'Unit (Laserpointer)',
  [2] = 'Integration (Scheinwerfer)',
  [3] = 'IsolatedDocker (Taschenlampe)',
  [4] = 'Blazor System (Buehne)',
  [5] = 'E2E (Flutlicht)',
}

-- <leader>sT1..5 - Search all tests from stage N (Telescope)
-- <leader>fT1..5 - Failed tests from stage N (Telescope)
for stage = 1, 5 do
  local sname = rt_stage_names[stage]

  -- sT{N}: Search all
  vim.keymap.set('n', '<leader>sT' .. stage, function()
    if vim.g.project_name ~= 'CENCOCD' then
      vim.notify('sT* aktuell nur fuer CenCoCo', vim.log.levels.WARN)
      return
    end
    local trx_path = rt_stage_file(stage)
    if vim.fn.filereadable(trx_path) == 0 then
      vim.notify('Keine TRX fuer Stufe ' .. stage .. '. Zuerst rT' .. stage .. ' ausfuehren!', vim.log.levels.WARN)
      return
    end
    local all = parse_rt_trx(trx_path)
    if #all == 0 then
      vim.notify('Keine Tests in Stufe ' .. stage .. ' TRX.', vim.log.levels.WARN)
      return
    end
    telescope_rt_picker('Stufe ' .. stage .. ': ' .. sname .. ' (' .. #all .. ') | Tab=select, Enter=re-run', all, { merge_stage = stage })
  end, { desc = '[S]earch [T]est Stufe [' .. stage .. '] | CenCoCo: ' .. sname })

  -- fT{N}: Failed only (round-based: re-run merges back, list shrinks each round)
  vim.keymap.set('n', '<leader>fT' .. stage, function()
    if vim.g.project_name ~= 'CENCOCD' then
      vim.notify('fT* aktuell nur fuer CenCoCo', vim.log.levels.WARN)
      return
    end
    local trx_path = rt_stage_file(stage)
    if vim.fn.filereadable(trx_path) == 0 then
      vim.notify('Keine TRX fuer Stufe ' .. stage .. '. Zuerst rT' .. stage .. ' ausfuehren!', vim.log.levels.WARN)
      return
    end
    local all = parse_rt_trx(trx_path)
    local failed = vim.tbl_filter(function(r) return r.outcome == 'Failed' end, all)
    if #failed == 0 then
      vim.notify('Stufe ' .. stage .. ': Alle ' .. #all .. ' Tests bestanden!', vim.log.levels.INFO)
      return
    end
    telescope_rt_picker('Stufe ' .. stage .. ' Failed (' .. #failed .. ') | Tab=select, Enter=re-run', failed, { merge_stage = stage })
  end, { desc = '[F]ailed [T]est Stufe [' .. stage .. '] | CenCoCo: ' .. sname })
end

-- <leader>rTA - Run Test All: Alle 5 Stufen sequentiell, CenCoCo mit auto-rTB zwischen 3→4
vim.keymap.set('n', '<leader>rTA', function()
  if vim.g.project_name ~= 'DCSRE' and vim.g.project_name ~= 'CENCOCD' then
    vim.notify('rTA nur fuer DCSRE/CenCoCo', vim.log.levels.WARN)
    return
  end

  local script_path = rt_temp .. '\\run-rt-all.ps1'
  local script

  if vim.g.project_name == 'CENCOCD' then
    local root = vim.g.project_root_windows
    local sln = root .. '\\src\\CenCoCo.sln'
    local accounting = root .. '\\tests\\CenCoCo.Accounting.SystemTests'
    local blazor_sys = root .. '\\tests\\CenCoCo.Blazor.SystemTests'
    local blazor_e2e = root .. '\\tests\\CenCoCo.Blazor.E2ETests'
    local compose = root .. '\\docker\\docker-compose.all.yml'

    script = string.format([[$ErrorActionPreference = "Continue"
$stageDir = "%s"
$results = @{}
$startTime = Get-Date

function Show-TrxSummary($n) {
    $f = "$stageDir\rt-stage$n.trx"
    if (Test-Path $f) {
        [xml]$r = Get-Content $f
        $a = $r.TestRun.Results.UnitTestResult
        $p = @($a | Where-Object { $_.outcome -eq 'Passed' }).Count
        $fl = @($a | Where-Object { $_.outcome -eq 'Failed' }).Count
        $s = @($a | Where-Object { $_.outcome -eq 'NotExecuted' }).Count
        $c = if ($fl -gt 0) { 'Red' } else { 'Green' }
        Write-Host ("  => PASSED={0}  FAILED={1}  SKIPPED={2}" -f $p, $fl, $s) -ForegroundColor $c
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  rTA: ALLE STUFEN (CenCoCo) + TRX" -ForegroundColor Cyan
Write-Host "  Start: $($startTime.ToString('HH:mm:ss'))" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan

# === STUFE 1: Unit Tests ===
Write-Host ""
Write-Host "=== STUFE 1: Unit Tests (Laserpointer) ===" -ForegroundColor Yellow
$s1 = "$stageDir\rt-stage1.trx"
if (Test-Path $s1) { Remove-Item $s1 -Force }
dotnet test '%s' --filter "Category!=E2E&Category!=SystemTest&Category!=IsolatedDocker&Category!=IntegrationTests" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$s1"
$results['1_Unit'] = $LASTEXITCODE
Show-TrxSummary 1

# === STUFE 2: Integration Tests ===
Write-Host ""
Write-Host "=== STUFE 2: Integration Tests (Scheinwerfer) ===" -ForegroundColor Yellow
$s2 = "$stageDir\rt-stage2.trx"
if (Test-Path $s2) { Remove-Item $s2 -Force }
dotnet test '%s' --filter "Category=IntegrationTests" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$s2"
$results['2_Integration'] = $LASTEXITCODE
Show-TrxSummary 2

# === STUFE 3: Isolated Docker ===
Write-Host ""
Write-Host "=== STUFE 3: Isolated Docker (Taschenlampe) ===" -ForegroundColor Yellow
$s3 = "$stageDir\rt-stage3.trx"
if (Test-Path $s3) { Remove-Item $s3 -Force }
dotnet test '%s' --filter "Category=IsolatedDocker" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$s3"
$results['3a_IsolatedDocker'] = $LASTEXITCODE
Show-TrxSummary 3
Write-Host "--- Accounting.SystemTests (nicht in sln) ---" -ForegroundColor Cyan
dotnet test '%s' --logger "console;verbosity=detailed"
$results['3b_Accounting'] = $LASTEXITCODE

# === rTB: Docker Image Rebuild (auto, Precondition Stufe 4+5) ===
Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  rTB: Docker Image Rebuild (~4 Min)" -ForegroundColor Magenta
Write-Host "  Precondition fuer Stufe 4+5" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Magenta
docker compose -f '%s' --profile all down -v --remove-orphans
docker compose -f '%s' --profile all up -d --build
$results['rTB_Build'] = $LASTEXITCODE

if ($results['rTB_Build'] -ne 0) {
    Write-Host "  rTB FEHLGESCHLAGEN - Stufe 4+5 uebersprungen!" -ForegroundColor Red
} else {
    # === STUFE 4: Blazor System Tests ===
    Write-Host ""
    Write-Host "=== STUFE 4: Blazor System Tests (Buehnenbeleuchtung) ===" -ForegroundColor Yellow
    $s4 = "$stageDir\rt-stage4.trx"
    if (Test-Path $s4) { Remove-Item $s4 -Force }
    dotnet test '%s' --filter "Category=SystemTest" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$s4"
    $results['4_BlazorSystem'] = $LASTEXITCODE
    Show-TrxSummary 4

    # === STUFE 5: E2E Tests ===
    Write-Host ""
    Write-Host "=== STUFE 5: E2E Tests (Flutlicht) ===" -ForegroundColor Yellow
    $s5 = "$stageDir\rt-stage5.trx"
    if (Test-Path $s5) { Remove-Item $s5 -Force }
    dotnet test '%s' --filter "Category=E2E" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$s5"
    $results['5_E2E'] = $LASTEXITCODE
    Show-TrxSummary 5
}

# === ZUSAMMENFASSUNG ===
$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ERGEBNIS: Alle Stufen" -ForegroundColor Cyan
Write-Host "  Dauer: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
$allGreen = $true
foreach ($key in $results.Keys | Sort-Object) {
    $code = $results[$key]
    if ($code -eq 0) {
        Write-Host "  V $($key)" -ForegroundColor Green
    } else {
        Write-Host "  X $($key) (Exit $($code))" -ForegroundColor Red
        $allGreen = $false
    }
}
Write-Host ""
Write-Host "  --- TRX pro Stufe ---" -ForegroundColor Gray
for ($i = 1; $i -le 5; $i++) {
    $sf = "$stageDir\rt-stage$i.trx"
    if (Test-Path $sf) {
        [xml]$r = Get-Content $sf
        $a = $r.TestRun.Results.UnitTestResult
        $p = @($a | Where-Object { $_.outcome -eq 'Passed' }).Count
        $fl = @($a | Where-Object { $_.outcome -eq 'Failed' }).Count
        $c = if ($fl -gt 0) { 'Red' } else { 'Green' }
        Write-Host ("  Stufe {0}: P={1}  F={2}" -f $i, $p, $fl) -ForegroundColor $c
    }
}
Write-Host "========================================" -ForegroundColor Cyan
if ($allGreen) {
    Write-Host "  ALLE STUFEN GRUEN!" -ForegroundColor Green
} else {
    Write-Host "  FEHLER! Hint: fT1..5 = Failed pro Stufe" -ForegroundColor Red
}
Write-Host "  Hint: sT1..5 = Stufe ansehen | fT1..5 = Failed" -ForegroundColor DarkGray
]], rt_temp, sln, sln, sln, accounting, compose, compose, blazor_sys, blazor_e2e)

  elseif vim.g.project_name == 'DCSRE' then
    local sln = vim.g.project_backend_windows .. '\\VDEK.DCSP.sln'
    local it = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
    local xunit = it .. '\\xunit.runner.json'
    local cypress = get_cypress_path_windows() or ''
    local frontend = vim.g.project_frontend or ''

    script = string.format([[$ErrorActionPreference = "Continue"
$stageDir = "%s"
$results = @{}
$xunit = '%s'
$startTime = Get-Date

function Set-Threads($n) {
    $c = Get-Content $xunit -Raw
    $c = $c -replace '"maxParallelThreads": \d+', ('"maxParallelThreads": ' + $n)
    Set-Content $xunit $c
}

function Show-TrxSummary($n) {
    $f = "$stageDir\rt-stage$n.trx"
    if (Test-Path $f) {
        [xml]$r = Get-Content $f
        $a = $r.TestRun.Results.UnitTestResult
        $p = @($a | Where-Object { $_.outcome -eq 'Passed' }).Count
        $fl = @($a | Where-Object { $_.outcome -eq 'Failed' }).Count
        $s = @($a | Where-Object { $_.outcome -eq 'NotExecuted' }).Count
        $c = if ($fl -gt 0) { 'Red' } else { 'Green' }
        Write-Host ("  => PASSED={0}  FAILED={1}  SKIPPED={2}" -f $p, $fl, $s) -ForegroundColor $c
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  rTA: ALLE STUFEN (DCSRE) + TRX" -ForegroundColor Cyan
Write-Host "  Start: $($startTime.ToString('HH:mm:ss'))" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan

# === STUFE 1: BE Unit Tests ===
Write-Host ""
Write-Host "=== STUFE 1: BE Unit Tests ===" -ForegroundColor Yellow
$s1 = "$stageDir\rt-stage1.trx"
if (Test-Path $s1) { Remove-Item $s1 -Force }
dotnet test '%s' --filter "(Category!=Database)&(Category!=Storage)&(Category!=Email)&(Category!=Docker)" --no-build --logger "console;verbosity=detailed" --logger "trx;LogFileName=$s1"
$results['1_BE_Unit'] = $LASTEXITCODE
Show-TrxSummary 1

# === STUFE 2: FE Unit Tests (Jest) ===
Write-Host ""
Write-Host "=== STUFE 2: FE Unit Tests (Jest) ===" -ForegroundColor Yellow
Push-Location '%s'
npm run test:ci
$results['2_FE_Unit'] = $LASTEXITCODE
Pop-Location

# === STUFE 3: Integration Mock (38 Threads) ===
Write-Host ""
Write-Host "=== STUFE 3: Integration Mock (DicMockServer, 38T) ===" -ForegroundColor Yellow
Set-Threads 38
$s3 = "$stageDir\rt-stage3.trx"
if (Test-Path $s3) { Remove-Item $s3 -Force }
dotnet test '%s' --no-build --no-restore --filter "FullyQualifiedName~IntegrationTests&FullyQualifiedName~DicMockServer" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$s3"
$results['3_IntMock'] = $LASTEXITCODE
Show-TrxSummary 3

# === STUFE 4: Integration DB (8 Threads) ===
Write-Host ""
Write-Host "=== STUFE 4: Integration DB (8T) ===" -ForegroundColor Yellow
Set-Threads 8
$s4 = "$stageDir\rt-stage4.trx"
if (Test-Path $s4) { Remove-Item $s4 -Force }
dotnet test '%s' --no-build --no-restore --filter "FullyQualifiedName~IntegrationTests&FullyQualifiedName!~DicMockServer" --logger "console;verbosity=detailed" --logger "trx;LogFileName=$s4"
$results['4_IntDB'] = $LASTEXITCODE
Show-TrxSummary 4

# Thread reset
Set-Threads 1

# === STUFE 5: E2E Gesamtsystemtest (Cypress) ===
Write-Host ""
Write-Host "=== STUFE 5: E2E Gesamtsystemtest (Cypress) ===" -ForegroundColor Yellow
Push-Location '%s'
npm run cypress:run:gesamtsystemtest
$results['5_E2E'] = $LASTEXITCODE
Pop-Location

# === ZUSAMMENFASSUNG ===
$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ERGEBNIS: Alle Stufen" -ForegroundColor Cyan
Write-Host "  Dauer: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
$allGreen = $true
foreach ($key in $results.Keys | Sort-Object) {
    $code = $results[$key]
    if ($code -eq 0) {
        Write-Host "  V $($key)" -ForegroundColor Green
    } else {
        Write-Host "  X $($key) (Exit $($code))" -ForegroundColor Red
        $allGreen = $false
    }
}
Write-Host ""
Write-Host "  --- TRX pro Stufe ---" -ForegroundColor Gray
foreach ($i in 1,3,4) {
    $sf = "$stageDir\rt-stage$i.trx"
    if (Test-Path $sf) {
        [xml]$r = Get-Content $sf
        $a = $r.TestRun.Results.UnitTestResult
        $p = @($a | Where-Object { $_.outcome -eq 'Passed' }).Count
        $fl = @($a | Where-Object { $_.outcome -eq 'Failed' }).Count
        $c = if ($fl -gt 0) { 'Red' } else { 'Green' }
        Write-Host ("  Stufe {0}: P={1}  F={2}" -f $i, $p, $fl) -ForegroundColor $c
    }
}
Write-Host "========================================" -ForegroundColor Cyan
if ($allGreen) {
    Write-Host "  ALLE STUFEN GRUEN!" -ForegroundColor Green
} else {
    Write-Host "  FEHLER! Hint: sT1..5/fT1..5 fuer Details" -ForegroundColor Red
}
]], rt_temp, xunit, sln, frontend, it, it, cypress)
  end

  local file = io.open(script_path, 'w')
  if file then file:write(script); file:close() end

  local Terminal = require('toggleterm.terminal').Terminal
  local term = Terminal:new({
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 58,
    on_exit = function()
      if vim.g.project_name == 'DCSRE' then
        set_xunit_threads(1)
        vim.notify('[DCSRE] Reset threads=1', vim.log.levels.INFO)
      end
    end,
  })
  term:toggle()
  vim.notify('[' .. vim.g.project_name .. '] rTA: Alle Stufen sequentiell...', vim.log.levels.INFO)
end, { desc = '[R]un [T]est [A]ll | Alle 5 Stufen sequentiell (CenCoCo: auto-rTB vor Stufe 4)' })

-- === rTB/rTH: CenCoCo-specific Infrastructure ===

-- <leader>rTB - Docker Image Build (Pflicht vor Stufe 4+5 nach src/-Aenderungen)
vim.keymap.set('n', '<leader>rTB', function()
  if vim.g.project_name ~= 'CENCOCD' then
    vim.notify('rTB nur fuer CenCoCo', vim.log.levels.WARN)
    return
  end

  local compose_file = vim.g.project_root_windows .. '\\docker\\docker-compose.all.yml'
  local Terminal = require('toggleterm.terminal').Terminal
  local build = Terminal:new({
    cmd = 'powershell.exe -NoProfile -Command "'
      .. "Write-Host '=== Docker Image Rebuild (Stufe 4+5 Precondition) ===' -ForegroundColor Cyan; "
      .. "Write-Host 'Dauer: ~4 Minuten (restore + build + publish + wasm-opt)' -ForegroundColor Yellow; "
      .. "docker compose -f '" .. compose_file .. "' --profile all down -v --remove-orphans; "
      .. "docker compose -f '" .. compose_file .. "' --profile all up -d --build; "
      .. "if ($?) { Write-Host '=== Image Rebuild FERTIG ===' -ForegroundColor Green } "
      .. "else { Write-Host '=== Image Rebuild FEHLGESCHLAGEN ===' -ForegroundColor Red }"
      .. '"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 55,
  })
  build:toggle()
  vim.notify('[CENCOCD] Docker Image Rebuild (~4 Min)...', vim.log.levels.INFO)
end, { desc = '[R]un [T]est [B]uild | CenCoCo Docker Image rebuild (Pflicht vor Stufe 4+5)' })

-- <leader>rTH - Toggle Headed-Modus (Browser sichtbar bei Stufe 4/5)
vim.keymap.set('n', '<leader>rTH', function()
  if vim.g.project_name ~= 'CENCOCD' then
    vim.notify('rTH nur fuer CenCoCo', vim.log.levels.WARN)
    return
  end
  vim.g.cencoco_headed = not vim.g.cencoco_headed
  local state = vim.g.cencoco_headed and 'AN' or 'AUS'
  local color = vim.g.cencoco_headed and vim.log.levels.WARN or vim.log.levels.INFO
  vim.notify('[CENCOCD] Headed-Modus: ' .. state .. ' (Browser sichtbar bei rT4/rT5)', color)
end, { desc = '[R]un [T]est [H]eaded | Toggle Playwright Headed-Modus (Browser sichtbar)' })

-- Quickfix: Show only warnings in quickfix list
vim.keymap.set('n', '<leader>qw', function()
  vim.diagnostic.setqflist({ severity = vim.diagnostic.severity.WARN })
  vim.cmd('copen')
end, { desc = '[Q]uickfix [W]arnings only' })
