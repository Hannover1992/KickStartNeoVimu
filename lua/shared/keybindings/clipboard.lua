-- lua/shared/keybindings/clipboard.lua
-- Clipboard/Yank Keybindings: yp, yn, yd, yDA, yW, yWA, yC, yI, gyf, gyd
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- KompatibilitÃ¤t

-- Copy relative filepath to clipboard (Windows format)
vim.keymap.set('n', '<leader>yp', function()
  local filepath = vim.fn.expand('%')
  -- Convert WSL path to Windows path
  filepath = filepath:gsub('/', '\\')
  vim.fn.setreg('+', filepath)
  vim.notify('Copied path: ' .. filepath, vim.log.levels.INFO)
end, { desc = '[Y]ank [P]ath (relative, Windows format)' })

-- Copy absolute Windows path to clipboard
vim.keymap.set('n', '<leader>yP', function()
  local filepath = vim.fn.expand('%:p')
  -- Convert /mnt/c/... to C:\...
  filepath = filepath:gsub('^/mnt/(%a)/', function(drive)
    return drive:upper() .. ':\\'
  end)
  filepath = filepath:gsub('/', '\\')
  vim.fn.setreg('+', filepath)
  vim.notify('Copied Windows path: ' .. filepath, vim.log.levels.INFO)
end, { desc = '[Y]ank [P]ath absolute (Windows format)' })

-- Copy only filename (without path) to clipboard
vim.keymap.set('n', '<leader>yn', function()
  local filename = vim.fn.expand('%:t')
  vim.fn.setreg('+', filename)
  vim.notify('Copied filename: ' .. filename, vim.log.levels.INFO)
end, { desc = '[Y]ank file[n]ame only' })

-- Copy diagnostic message under cursor to clipboard (legacy - use yd instead)
vim.keymap.set('n', '<leader>dy', function()
  local diagnostics = vim.diagnostic.get(0, { lnum = vim.fn.line('.') - 1 })
  if #diagnostics > 0 then
    local msg = diagnostics[1].message
    vim.fn.setreg('+', msg)
    vim.notify('Copied: ' .. msg:sub(1, 50) .. (msg:len() > 50 and '...' or ''), vim.log.levels.INFO)
  else
    vim.notify('No diagnostic on this line', vim.log.levels.WARN)
  end
end, { desc = '[D]iagnostic [Y]ank to clipboard' })

-- Yank Diagnostic: Copy full path + line number + diagnostic to clipboard
vim.keymap.set('n', '<leader>yd', function()
  local diagnostics = vim.diagnostic.get(0, { lnum = vim.fn.line('.') - 1 })
  if #diagnostics > 0 then
    local filepath = vim.fn.expand('%:p')
    local line = vim.fn.line('.')
    local msg = diagnostics[1].message
    local full = filepath .. ':' .. line .. ' ' .. msg
    vim.fn.setreg('+', full)
    vim.notify('Yanked diagnostic: ' .. filepath:match('[^/\\]+$') .. ':' .. line, vim.log.levels.INFO)
  else
    vim.notify('No diagnostic on this line', vim.log.levels.WARN)
  end
end, { desc = '[Y]ank [D]iagnostic (path:line msg)' })

-- Yank Diagnostic Append: Append full path + line number + diagnostic to clipboard
vim.keymap.set('n', '<leader>yD', function()
  local diagnostics = vim.diagnostic.get(0, { lnum = vim.fn.line('.') - 1 })
  if #diagnostics > 0 then
    local filepath = vim.fn.expand('%:p')
    local line = vim.fn.line('.')
    local msg = diagnostics[1].message
    local full = filepath .. ':' .. line .. ' ' .. msg
    local current = vim.fn.getreg('+')
    if current ~= '' then
      vim.fn.setreg('+', current .. '\n' .. full)
    else
      vim.fn.setreg('+', full)
    end
    vim.notify('Appended diagnostic: ' .. filepath:match('[^/\\]+$') .. ':' .. line, vim.log.levels.INFO)
  else
    vim.notify('No diagnostic on this line', vim.log.levels.WARN)
  end
end, { desc = '[Y]ank [D]iagnostic append (path:line msg)' })

-- Yank Warning: Copy warning (WARN severity only) to clipboard
vim.keymap.set('n', '<leader>yww', function()
  local diagnostics = vim.diagnostic.get(0, { lnum = vim.fn.line('.') - 1, severity = vim.diagnostic.severity.WARN })
  if #diagnostics > 0 then
    local filepath = vim.fn.expand('%:p')
    local line = vim.fn.line('.')
    local msg = diagnostics[1].message
    local full = filepath .. ':' .. line .. ' ' .. msg
    vim.fn.setreg('+', full)
    vim.notify('Yanked warning: ' .. filepath:match('[^/\\]+$') .. ':' .. line, vim.log.levels.INFO)
  else
    vim.notify('No warning on this line', vim.log.levels.WARN)
  end
end, { desc = '[Y]ank [W]arning [w] (path:line msg)' })

-- Yank Warning Append: Append warning to clipboard
vim.keymap.set('n', '<leader>ywW', function()
  local diagnostics = vim.diagnostic.get(0, { lnum = vim.fn.line('.') - 1, severity = vim.diagnostic.severity.WARN })
  if #diagnostics > 0 then
    local filepath = vim.fn.expand('%:p')
    local line = vim.fn.line('.')
    local msg = diagnostics[1].message
    local full = filepath .. ':' .. line .. ' ' .. msg
    local current = vim.fn.getreg('+')
    if current ~= '' then
      vim.fn.setreg('+', current .. '\n' .. full)
    else
      vim.fn.setreg('+', full)
    end
    vim.notify('Appended warning: ' .. filepath:match('[^/\\]+$') .. ':' .. line, vim.log.levels.INFO)
  else
    vim.notify('No warning on this line', vim.log.levels.WARN)
  end
end, { desc = '[Y]ank [W]arning append [W] (path:line msg)' })

-- Yank Changes: Copy git diff for current file to clipboard
vim.keymap.set('n', '<leader>yc', function()
  local file = vim.fn.expand('%:p')
  if file == '' then
    vim.notify('No file in buffer!', vim.log.levels.ERROR)
    return
  end
  -- Get git root and make path relative
  local git_root = vim.fn.systemlist('git rev-parse --show-toplevel')[1]
  if vim.v.shell_error ~= 0 then
    vim.notify('Not in a git repository!', vim.log.levels.ERROR)
    return
  end
  -- Convert to relative path (works on Windows too)
  local rel_path = vim.fn.fnamemodify(file, ':.')
  -- Try unstaged first, then staged
  local diff = vim.fn.system('git diff -- "' .. rel_path .. '"')
  if diff == '' then
    diff = vim.fn.system('git diff --cached -- "' .. rel_path .. '"')
  end
  if diff ~= '' then
    vim.fn.setreg('+', diff)
    local lines = select(2, diff:gsub('\n', '\n'))
    vim.notify('Yanked diff (' .. lines .. ' lines): ' .. vim.fn.fnamemodify(file, ':t'), vim.log.levels.INFO)
  else
    vim.notify('No changes for this file', vim.log.levels.WARN)
  end
end, { desc = '[Y]ank [C]hanges (git diff for file)' })

-- Yank Issues: Copy all diagnostics for current file to clipboard
vim.keymap.set('n', '<leader>yi', function()
  local diagnostics = vim.diagnostic.get(0) -- 0 = current buffer
  if #diagnostics == 0 then
    vim.notify('No issues in this file', vim.log.levels.WARN)
    return
  end
  local filepath = vim.fn.expand('%:p')
  local lines = {}
  for _, d in ipairs(diagnostics) do
    local severity = ({ 'ERROR', 'WARN', 'INFO', 'HINT' })[d.severity] or 'UNKNOWN'
    local line = string.format('%s:%d [%s] %s', filepath, d.lnum + 1, severity, d.message)
    table.insert(lines, line)
  end
  local result = table.concat(lines, '\n')
  vim.fn.setreg('+', result)
  vim.notify('Yanked ' .. #diagnostics .. ' issues to clipboard', vim.log.levels.INFO)
end, { desc = '[Y]ank [I]ssues (all diagnostics in file)' })

-- Remap Visual Block mode (Ctrl+v conflicts with Windows paste)
vim.keymap.set('n', '<leader>v', '<C-v>', { desc = '[V]isual Block Mode' })

-- Create temporary markdown buffer (scratch) - won't be saved!
vim.keymap.set('n', '<leader>mf', function()
  -- Create new buffer
  vim.cmd('enew')

  -- Set it as markdown
  vim.bo.filetype = 'markdown'

  -- Make it a scratch buffer (won't ask to save)
  vim.bo.buftype = 'nofile'
  vim.bo.bufhidden = 'hide'
  vim.bo.swapfile = false

  -- Optional: Add a nice title
  vim.api.nvim_buf_set_lines(0, 0, -1, false, {
    '# Temporary Notes',
    '',
    '---',
    '',
    ''
  })

  -- Move cursor to line 5 (after the header)
  vim.cmd('normal! 5G')

  vim.notify('Created temporary markdown buffer (won\'t be saved)', vim.log.levels.INFO)
end, { desc = '[M]arkdown [F]oo scratch (temp)' })

-- Markdown PDF Export with Chrome Headless (<leader>mP dark / <leader>mS light)
-- Uses markdown-preview.nvim's HTML renderer + Chrome headless print
-- Supports Mermaid, PlantUML, and all markdown-preview features!
-- Die Preview-URL kommt aus g:mkdp_last_url â€” gesetzt von OpenMarkdownPreview()
-- in core.lua, das vom Plugin als browserfunc mit der echten URL gerufen wird.
--
-- Fehler bleiben stehen: vim.notify verschwindet nach ein paar Sekunden und die
-- Kommandozeile scrollt weg, bevor man sie lesen kann. Darum landet jeder Fehler
-- zusaetzlich in einem Split-Fenster, das offen bleibt bis man es schliesst.
local function show_error(lines)
  vim.schedule(function()
    local buf = vim.api.nvim_create_buf(false, true)
    vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
    vim.bo[buf].bufhidden = 'wipe'
    vim.bo[buf].filetype = 'markdown'
    vim.cmd('botright split')
    vim.api.nvim_win_set_buf(0, buf)
    vim.api.nvim_win_set_height(0, math.min(#lines + 2, 20))
    vim.keymap.set('n', 'q', '<cmd>close<cr>', { buffer = buf, desc = 'Fehlerfenster schliessen' })
  end)
end

-- Markdown -> PDF (<leader>mP dunkel, <leader>mS hell fuer den Drucker)
--
-- Bewusst OHNE markdown-preview.nvim: dessen Preview-Seite haelt per Socket.io
-- dauerhaft eine Verbindung offen und holt ihren Inhalt erst nachtraeglich nach.
-- Chrome-Headless wartet darum entweder ewig auf "Seite fertig" (gemessen: 31s
-- Haenger, Exitcode -1) oder druckt vorher und liefert eine leere Seite (858 Byte).
-- Der Weg ueber Pandoc + lokale HTML-Datei ist gemessen 0.6s und deterministisch.
local MKDP_STATIC = vim.fn.stdpath('data') .. '/lazy/markdown-preview.nvim/app/_static'

local function chrome_binary()
  if vim.fn.has('unix') == 1 then
    return '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
  end
  return 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
end

local function build_html(body, theme)
  local css, maid_theme
  if theme == 'light' then
    -- Druckversion: weisser Grund, dunkle Schrift — spart Toner
    css = 'body{background:#fff;color:#111}pre,code{background:#f4f4f4;color:#111}'
       .. 'th{background:#eaeaea}a{color:#0645ad}blockquote{color:#444;border-left:4px solid #ccc}'
    maid_theme = 'default'
  else
    css = 'body{background:#1e1e1e;color:#e6e6e6}pre,code{background:#2a2a2a;color:#e6e6e6}'
       .. 'th{background:#333}a{color:#6cb6ff}blockquote{color:#bbb;border-left:4px solid #555}'
    maid_theme = 'dark'
  end

  local mermaid_src = (MKDP_STATIC .. '/mermaid.min.js'):gsub('\\', '/')

  return table.concat({
    '<!doctype html><html><head><meta charset="utf-8"><style>',
    'body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:0 auto;padding:24px;line-height:1.6}',
    'pre{padding:10px;border-radius:4px;overflow-x:auto;white-space:pre-wrap}',
    'code{padding:1px 4px;border-radius:3px}',
    'table{border-collapse:collapse}th,td{border:1px solid #999;padding:4px 8px}',
    'img,svg{max-width:100%}blockquote{margin-left:0;padding-left:12px}',
    'h1,h2,h3{line-height:1.25}',
    css,
    '@media print{body{margin:0;padding:0}pre,blockquote,table{break-inside:avoid}}',
    '</style>',
    '<script src="file:///' .. mermaid_src .. '"></script>',
    '</head><body>',
    body,
    '<script>',
    -- Pandoc macht aus ```mermaid je nach Version <pre class="mermaid"> ODER
    -- <pre><code class="language-mermaid">. Beide Formen einsammeln.
    'document.querySelectorAll("pre > code.language-mermaid, pre.mermaid > code").forEach(function(c){',
    '  var d=document.createElement("div"); d.className="mermaid"; d.textContent=c.textContent;',
    '  c.parentNode.replaceWith(d);',
    '});',
    'if (window.mermaid) { mermaid.initialize({startOnLoad:true, theme:"' .. maid_theme .. '"}); }',
    '</script></body></html>',
  }, '\n')
end

local function markdown_export_pdf(theme)
  if vim.bo.filetype ~= 'markdown' then
    vim.notify('Keine Markdown-Datei!', vim.log.levels.WARN)
    return
  end

  if vim.fn.executable('pandoc') == 0 then
    show_error({
      '# PDF-Export nicht moeglich',
      '',
      'pandoc wurde nicht gefunden (wird zum Rendern von Markdown gebraucht).',
      '',
      'Installieren:  winget install --id JohnMacFarlane.Pandoc',
      '',
      'Fenster schliessen mit  q',
    })
    return
  end

  local chrome = chrome_binary()
  if vim.fn.filereadable(chrome) == 0 then
    show_error({
      '# PDF-Export nicht moeglich',
      '',
      'Google Chrome nicht gefunden unter:',
      '  ' .. chrome,
      '',
      'Fenster schliessen mit  q',
    })
    return
  end

  local file = vim.fn.expand('%:p')
  local dir = vim.fn.fnamemodify(file, ':h')
  local stem = vim.fn.fnamemodify(file, ':t:r')
  local pdf_file = dir .. '/' .. stem .. '.pdf'

  -- Aktuellen Buffer-Inhalt exportieren, nicht die Datei auf der Platte:
  -- so landen auch ungespeicherte Aenderungen im PDF.
  local tmp_md = vim.fn.tempname() .. '.md'
  vim.fn.writefile(vim.api.nvim_buf_get_lines(0, 0, -1, false), tmp_md)

  vim.notify('Erzeuge PDF (' .. theme .. ')...', vim.log.levels.INFO)

  -- Markdown -> HTML-Fragment. systemlist wuerde die Zeilenumbrueche verlieren,
  -- was Mermaid-Bloecke zu einer einzigen Zeile macht ("Syntax error in text").
  local body = vim.fn.system({ 'pandoc', '-f', 'gfm', '-t', 'html5', '--mathml', tmp_md })
  if vim.v.shell_error ~= 0 then
    vim.fn.delete(tmp_md)
    local lines = { '# PDF-Export fehlgeschlagen', '', 'pandoc-Exitcode: ' .. vim.v.shell_error, '', '## Ausgabe', '' }
    vim.list_extend(lines, vim.split(body or '', '\n', { trimempty = true }))
    table.insert(lines, '')
    table.insert(lines, 'Fenster schliessen mit  q')
    show_error(lines)
    return
  end

  local html_file = vim.fn.tempname() .. '.html'
  vim.fn.writefile(vim.split(build_html(body, theme), '\n'), html_file)

  local file_url = 'file:///' .. html_file:gsub('\\', '/')
  local pdf_for_chrome = pdf_file
  if vim.fn.has('unix') == 1 then
    pdf_for_chrome = pdf_file:gsub('/mnt/c', 'C:'):gsub('/', '\\')
  else
    pdf_for_chrome = pdf_file:gsub('/', '\\')
  end
  vim.fn.delete(pdf_file)

  -- --virtual-time-budget: Chrome spult seine Timer vor, damit Mermaid fertig
  -- rendert, bevor gedruckt wird — ohne real zu warten.
  local cmd = string.format(
    '"%s" --headless --disable-gpu --no-pdf-header-footer --virtual-time-budget=20000 --print-to-pdf="%s" "%s"',
    chrome, pdf_for_chrome, file_url
  )
  local out = vim.fn.system(cmd)
  local rc = vim.v.shell_error

  vim.fn.delete(tmp_md)

  if vim.fn.filereadable(pdf_file) == 0 then
    local lines = {
      '# PDF-Export fehlgeschlagen',
      '',
      'Chrome-Exitcode: ' .. rc,
      'Ziel-PDF:        ' .. pdf_file,
      'HTML-Zwischendatei (bleibt zum Nachsehen liegen):',
      '  ' .. html_file,
      '',
      '## Chrome-Aufruf',
      '',
      cmd,
      '',
      '## Chrome-Ausgabe',
      '',
    }
    vim.list_extend(lines, vim.split(out or '', '\n', { trimempty = true }))
    table.insert(lines, '')
    table.insert(lines, 'Fenster schliessen mit  q')
    show_error(lines)
    return
  end

  vim.fn.delete(html_file)

  local kb = math.floor(vim.fn.getfsize(pdf_file) / 1024)
  vim.notify('PDF erstellt: ' .. vim.fn.fnamemodify(pdf_file, ':t') .. ' (' .. kb .. ' KB)', vim.log.levels.INFO)

  if vim.fn.has('unix') == 1 then
    vim.fn.system('explorer.exe "' .. pdf_for_chrome .. '"')
  else
    vim.fn.system('start "" "' .. pdf_file .. '"')
  end
end

vim.keymap.set('n', '<leader>mP', function()
  markdown_export_pdf('dark')
end, { desc = '[M]arkdown [P]DF export dark (with Mermaid)' })

-- <leader>me - Fehler/Meldungen nachlesen, die in der Kommandozeile weggescrollt sind.
-- :messages allein scrollt genauso weg; hier landet alles in einem normalen Buffer
-- (scrollbar, durchsuchbar mit /, kopierbar mit y). Schliessen mit q.
vim.keymap.set('n', '<leader>me', function()
  local msgs = vim.fn.execute('messages')
  local lines = vim.split(msgs, '\n', { trimempty = true })
  if #lines == 0 then
    vim.notify('Keine Meldungen vorhanden.', vim.log.levels.INFO)
    return
  end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].bufhidden = 'wipe'
  vim.cmd('botright split')
  vim.api.nvim_win_set_buf(0, buf)
  vim.api.nvim_win_set_height(0, math.min(#lines + 1, 25))
  vim.cmd('normal! G')  -- ans Ende: der neueste Fehler steht unten
  vim.keymap.set('n', 'q', '<cmd>close<cr>', { buffer = buf, desc = 'Meldungen schliessen' })
end, { desc = '[M]essages/[E]rrors nachlesen (scrollbar, q schliesst)' })

-- Druckversion: weisser Hintergrund, schwarzer Text â€” spart Toner
vim.keymap.set('n', '<leader>mS', function()
  markdown_export_pdf('light')
end, { desc = '[M]arkdown [S]ave print-PDF light (Toner-schonend)' })

-- Git Yank File diff vs base branch (<leader>gyf)
-- Copies the git diff for current file against origin/develop (or origin/main) to clipboard
vim.keymap.set('n', '<leader>gyf', function()
  local file = vim.fn.expand('%:.')  -- Relative path from repo root
  if file == '' then
    vim.notify('No file in buffer!', vim.log.levels.WARN)
    return
  end

  -- Check if we're in a git repository
  local is_git_repo = vim.fn.system('git rev-parse --is-inside-work-tree 2>/dev/null'):match('true')
  if not is_git_repo then
    vim.notify('Not in a git repository!', vim.log.levels.WARN)
    return
  end

  -- Auto-detect base branch: use 'main' for CENCOCD, 'develop' for DCSRE
  local base_branch = 'origin/develop'
  local git_root = vim.fn.systemlist('git rev-parse --show-toplevel')[1]
  if git_root and git_root:match('cencoco') then
    base_branch = 'origin/main'
  end

  -- Get diff against base branch for this file
  local cmd = string.format('git diff %s -- "%s"', base_branch, file)
  local diff = vim.fn.system(cmd)

  if vim.v.shell_error ~= 0 then
    vim.notify('Git diff failed! Is the branch fetched?', vim.log.levels.ERROR)
    return
  end

  if diff == '' then
    vim.notify('No changes in this file vs ' .. base_branch, vim.log.levels.INFO)
    return
  end

  -- Copy to clipboard
  vim.fn.setreg('+', diff)
  local line_count = select(2, diff:gsub('\n', '\n'))
  vim.notify('File diff copied! (' .. line_count .. ' lines vs ' .. base_branch .. ')', vim.log.levels.INFO)
end, { desc = '[G]it [Y]ank [F]ile diff vs base branch' })

-- Git Yank entire branch Diff vs base branch (<leader>gyd)
-- Copies the COMPLETE git diff (all files) against origin/develop (or origin/main) to clipboard
vim.keymap.set('n', '<leader>gyd', function()
  -- Check if we're in a git repository
  local is_git_repo = vim.fn.system('git rev-parse --is-inside-work-tree 2>/dev/null'):match('true')
  if not is_git_repo then
    vim.notify('Not in a git repository!', vim.log.levels.WARN)
    return
  end

  -- Auto-detect base branch: use 'main' for CENCOCD, 'develop' for DCSRE
  local base_branch = 'origin/develop'
  local git_root = vim.fn.systemlist('git rev-parse --show-toplevel')[1]
  if git_root and git_root:match('cencoco') then
    base_branch = 'origin/main'
  end

  -- Get FULL diff against base branch (all files)
  local cmd = string.format('git diff %s', base_branch)
  local diff = vim.fn.system(cmd)

  if vim.v.shell_error ~= 0 then
    vim.notify('Git diff failed! Is the branch fetched?', vim.log.levels.ERROR)
    return
  end

  if diff == '' then
    vim.notify('No changes in current branch vs ' .. base_branch, vim.log.levels.INFO)
    return
  end

  -- Copy to clipboard
  vim.fn.setreg('+', diff)
  local line_count = select(2, diff:gsub('\n', '\n'))
  local file_count = select(2, diff:gsub('diff %-%-git', ''))
  vim.notify('Branch diff copied! (' .. file_count .. ' files, ' .. line_count .. ' lines vs ' .. base_branch .. ')', vim.log.levels.INFO)
end, { desc = '[G]it [Y]ank [D]iff entire branch vs base' })
