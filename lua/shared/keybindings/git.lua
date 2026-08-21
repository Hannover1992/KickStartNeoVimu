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

-- ============================================================================
-- Branch-Review: JEDER Hunk vs Base-Branch, dateiuebergreifend navigierbar
-- ============================================================================
-- Problem: bei >100 geaenderten Dateien ist "durch den Diff gehen" von Hand nicht
-- machbar. gitsigns' ]c/[c springt nur INNERHALB einer Datei. Quickfix ist Vims
-- native dateiuebergreifende Navigationsstruktur -> ]q/[q laeuft ueber Dateigrenzen.
--
-- WARUM EIGENER PARSER statt gitsigns.setqflist('all') -- gemessen 2026-08-21 an
-- DCSRE (887 geaenderte Dateien, 601 davon auf der Platte):
--   1. gitsigns startet EINEN git-Prozess PRO Datei (`git show {base}:{datei}`)
--      und diffed in Lua: 18,7 s. Ein einziges `git diff` braucht 0,47 s.
--   2. gitsigns uebergibt die Eintraege als `filename`. Vim legte nur fuer die
--      ersten 285 von 610 Eintraegen einen Buffer an; die restlichen 325 hatten
--      bufnr=0 und `:cc` sprang sie NICHT an -- die halbe Liste war tot.
--      (Nicht MAX_PATH: der laengste Pfad im Repo hat 252 Zeichen.)
--      Hier wird stattdessen vim.fn.bufadd() benutzt -> jeder Eintrag hat einen
--      echten Buffer, BEVOR die Liste gesetzt wird.
--   3. gitsigns' interner Differ fasst Hunks anders zusammen (610 statt 1409).
--      `git diff` mit Standard-Kontext ist das, was auch der PR-Reviewer sieht.
--
-- BASE: Diff gegen die MERGE-BASE von base und HEAD, nicht gegen die Spitze von
-- base. Das haelt das Ergebnis stabil, wenn origin/develop weitergelaufen ist:
-- fremde Commits erscheinen dann NICHT als deine Aenderungen. Zwei-Punkt gegen die
-- Merge-Base heisst ausserdem: uncommittete Aenderungen sind mit drin.
local function build_branch_hunk_qflist()
  local base = vim.g.project_git_base or 'origin/develop'
  local cwd = vim.fn.getcwd()

  -- vim.system() statt vim.fn.systemlist(): kein Shell dazwischen. Damit sind
  -- Backslash-Pfade, Quoting und ein evtl. fehlkonfiguriertes 'shell'/'shellcmdflag'
  -- (z.B. shell=bash mit cmd-Flags) kein Thema mehr.
  local function git(args)
    local cmd = { 'git', '-C', cwd }
    vim.list_extend(cmd, args)
    local r = vim.system(cmd, { text = true }):wait()
    return vim.split(r.stdout or '', '\r?\n', { regex = true, trimempty = true }), r.code, r.stderr or ''
  end

  local mb_out, mb_err, mb_stderr = git({ 'merge-base', base, 'HEAD' })
  if mb_err ~= 0 or not mb_out[1] or mb_out[1] == '' then
    vim.notify(string.format('merge-base %s HEAD fehlgeschlagen (exit %s):\n%s\n(Base vorhanden? git fetch noetig?)',
      base, tostring(mb_err), mb_stderr), vim.log.levels.ERROR, { title = 'Branch-Review', timeout = 10000 })
    return nil
  end
  local mb = mb_out[1]

  local raw, derr, dstderr = git({ 'diff', '--no-color', mb })
  if derr ~= 0 then
    vim.notify(string.format('git diff fehlgeschlagen (exit %s):\n%s', tostring(derr), dstderr),
      vim.log.levels.ERROR, { title = 'Branch-Review', timeout = 10000 })
    return nil
  end

  local items, files = {}, {}
  local cur_buf, pending = nil, nil
  local n_deleted, n_missing, n_binary = 0, 0, 0

  local function flush()
    if pending then
      table.insert(items, pending)
      pending = nil
    end
  end

  -- Datei aus dem Diff aufnehmen; gibt die bufnr zurueck oder nil (+ zaehlt den Grund).
  local function open_target(rel)
    if not rel then
      n_deleted = n_deleted + 1
      return nil
    end
    local abs = cwd .. '/' .. rel
    if vim.fn.filereadable(abs) ~= 1 then
      n_missing = n_missing + 1
      return nil
    end
    local b = vim.fn.bufadd(abs)
    files[b] = true
    return b
  end

  -- Zustandsautomat statt reiner Praefix-Pruefung: eine INHALTS-Zeile kann selbst
  -- mit '+++ ' beginnen (hinzugefuegte Zeile, deren Text '++ ...' lautet). Nur
  -- innerhalb des Datei-Kopfes (nach 'diff --git', vor dem ersten '@@') gilt
  -- '+++ ' als Dateiname.
  local in_header = false

  for _, line in ipairs(raw) do
    if line:sub(1, 11) == 'diff --git ' then
      flush()
      in_header = true
      cur_buf = nil
    elseif in_header and line:sub(1, 13) == 'Binary files ' then
      -- Binaerdateien haben KEINEN Zeilendiff. Ohne diesen Zweig wuerden sie
      -- lautlos aus dem Review fallen (nachgewiesen 2026-08-21: keycloak.p12).
      local rel = line:match('^Binary files .* and b/(.+) differ$')
      local b = open_target(rel)
      if b then
        n_binary = n_binary + 1
        table.insert(items, {
          bufnr = b,
          lnum = 1,
          col = 1,
          text = 'Binary  geaendert (kein Zeilendiff - Inhalt manuell pruefen)',
        })
      end
      in_header = false
    elseif in_header and line:sub(1, 4) == '+++ ' then
      cur_buf = open_target(line:match('^%+%+%+ b/(.*)$'))
      in_header = false
    elseif not in_header and cur_buf and line:sub(1, 3) == '@@ ' then
      flush()
      local oc, ns, nc = line:match('^@@ %-%d+,?(%d*) %+(%d+),?(%d*) @@')
      if ns then
        oc = (oc == '') and 1 or tonumber(oc)
        nc = (nc == '') and 1 or tonumber(nc)
        local kind = (oc == 0) and 'Added' or (nc == 0) and 'Removed' or 'Changed'
        pending = {
          bufnr = cur_buf,
          lnum = math.max(tonumber(ns), 1),
          col = 1,
          text = string.format('%-7s %s', kind, line:match('^@@ (.-) @@') or ''),
        }
      end
    elseif pending then
      local c = line:sub(1, 1)
      if c == '+' or c == '-' then
        pending.text = pending.text .. ': ' .. vim.trim(line:sub(2))
        table.insert(items, pending)
        pending = nil
      end
    end
  end
  flush()

  return {
    items = items,
    nfiles = vim.tbl_count(files),
    base = base,
    mergebase = mb:sub(1, 8),
    n_deleted = n_deleted,
    n_missing = n_missing,
    n_binary = n_binary,
  }
end

-- <leader>qh -- [Q]uickfix [H]unks: Branch-Review starten.
-- Baut die Liste UND schaltet die gitsigns-Base auf den Base-Branch um, damit die
-- Zeichen im Gutter dasselbe zeigen wie die Liste. Zurueck in den Alltags-Modus
-- (uncommitted, Hunk-Staging) mit <leader>hB.
vim.keymap.set('n', '<leader>qh', function()
  local r = build_branch_hunk_qflist()
  if not r then return end

  if #r.items == 0 then
    vim.notify(string.format('Keine Hunks vs %s.', r.base), vim.log.levels.WARN, { title = 'Branch-Review' })
    return
  end

  vim.fn.setqflist({}, ' ', {
    items = r.items,
    title = string.format('Branch-Hunks vs %s (%s)', r.base, r.mergebase),
  })

  pcall(function()   -- Gutter auf dieselbe Base ziehen; die Liste haengt nicht davon ab
    local gs = require('gitsigns')
    gs.change_base(r.base, true)
    vim.g.gitsigns_branch_mode = true
  end)

  vim.cmd('copen')
  vim.cmd('cfirst')

  local extra = ''
  if r.n_deleted > 0 then
    extra = extra .. string.format('\n%d geloeschte Datei(en) NICHT in der Liste (nichts zum Anspringen)', r.n_deleted)
  end
  if r.n_missing > 0 then
    extra = extra .. string.format('\n%d Datei(en) nicht lesbar -- uebersprungen', r.n_missing)
  end
  if r.n_binary > 0 then
    extra = extra .. string.format('\n%d Binaerdatei(en) als Eintrag in Zeile 1 (kein Zeilendiff moeglich)', r.n_binary)
  end
  vim.notify(string.format('%d Hunks in %d Dateien vs %s (Merge-Base %s)\n]q / [q = naechster / vorheriger Hunk (ueber Dateigrenzen)\n<leader>hB = Gutter zurueck auf uncommitted%s',
    #r.items, r.nfiles, r.base, r.mergebase, extra),
    vim.log.levels.INFO, { title = 'Branch-Review', timeout = 12000 })
end, { desc = '[Q]uickfix: alle [H]unks vs Base-Branch (Branch-Review)' })

-- ]q / [q -- dateiuebergreifende Quickfix-Navigation mit Wrap.
-- Das ist die eigentliche Review-Bewegung: ein Tastendruck = naechste Aenderung,
-- egal ob sie in dieser Datei oder in der naechsten liegt. Gilt fuer JEDE
-- Quickfix-Liste, also auch fuer <leader>qd / <leader>qD.
local function qf_nav(forward)
  if vim.fn.getqflist({ size = 0 }).size == 0 then
    vim.notify('Quickfix-Liste ist leer (<leader>qh baut die Branch-Hunk-Liste)', vim.log.levels.INFO)
    return
  end
  local step = forward and vim.cmd.cnext or vim.cmd.cprevious
  local wrap = forward and vim.cmd.cfirst or vim.cmd.clast
  if not pcall(step) then pcall(wrap) end
end

vim.keymap.set('n', ']q', function() qf_nav(true) end, { desc = 'Next [q]uickfix entry (cross-file, wrap)' })
vim.keymap.set('n', '[q', function() qf_nav(false) end, { desc = 'Previous [q]uickfix entry (cross-file, wrap)' })

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
  -- Konfigurabel via vim.g.dcsre_azure_script; Default: <USERPROFILE>\Documents\Work\Code2\DCSRE_Azure\...
  local script = vim.g.dcsre_azure_script
    or ((os.getenv('USERPROFILE') or 'C:\\Users\\Administrator')
        .. '\\Documents\\Work\\Code2\\DCSRE_Azure\\OmniCommand\\.claude\\new-research-project.ps1')
  local Terminal = require('toggleterm.terminal').Terminal
  local setup = Terminal:new({
    cmd = 'powershell.exe -ExecutionPolicy Bypass -File "' .. script .. '" -TargetPath "' .. win_path .. '"; pause',
    direction = 'horizontal',
    close_on_exit = false,
  })
  setup:toggle()
  vim.notify('.claude/ Setup gestartet → ' .. win_path, vim.log.levels.INFO)
end, { desc = '[R]un [S]cript [C]laude | new-research-project.ps1' })

-- Claude Archive Sync: AgentsArchive\.claude_DCSRE/.claude_CenCoCo → Projekt-Root\.claude
vim.keymap.set('n', '<leader>rca', function()
  require('shared.claude_sync').sync_with_notify()
end, { desc = '[R]un [C]laude [A]rchive sync | AgentsArchive→Projekt .claude (DCSRE/CenCoCo)' })
