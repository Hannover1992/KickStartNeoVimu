-- lua/shared/keybindings/clipboard.lua
-- Clipboard/Yank Keybindings: yp, yn, yd, yDA, yW, yWA, yC, yI, gyf, gyd
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität

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

-- Markdown PDF Export with Chrome Headless (<leader>mP)
-- Uses markdown-preview.nvim's HTML renderer + Chrome headless print
-- Supports Mermaid, PlantUML, and all markdown-preview features!
vim.keymap.set('n', '<leader>mP', function()
  local file = vim.fn.expand('%:p')
  if vim.bo.filetype ~= 'markdown' then
    vim.notify('Not a markdown file!', vim.log.levels.WARN)
    return
  end

  -- Check if Chrome is available (works in both WSL2 and Windows)
  local chrome_path
  if vim.fn.has('unix') == 1 then
    -- WSL2: Use Windows Chrome via /mnt/c path
    chrome_path = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
  else
    -- Windows native
    chrome_path = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  end

  if vim.fn.filereadable(chrome_path) == 0 then
    vim.notify('Chrome not found! Install Google Chrome.', vim.log.levels.ERROR)
    return
  end

  -- Generate PDF path in SAME directory as markdown file
  local dir = vim.fn.fnamemodify(file, ':h')  -- Get directory
  local filename = vim.fn.fnamemodify(file, ':t:r')  -- Get filename without extension
  local pdf_file = dir .. '/' .. filename .. '.pdf'  -- Combine (forward slash works in both WSL2 and Windows Neovim)

  -- Start markdown preview (generates HTML with Mermaid rendering)
  vim.cmd('MarkdownPreview')

  -- Wait a bit for preview server to start and render
  vim.defer_fn(function()
    -- Get the preview URL from markdown-preview
    local url = vim.fn['mkdp#util#get_url']()
    if not url or url == '' then
      vim.notify('Failed to get preview URL!', vim.log.levels.ERROR)
      vim.cmd('MarkdownPreviewStop')
      return
    end

    -- Convert PDF path for Chrome (WSL2 needs Windows path, Chrome requires backslashes)
    local pdf_path_for_chrome = pdf_file
    if vim.fn.has('unix') == 1 then
      pdf_path_for_chrome = pdf_file:gsub('/mnt/c', 'C:'):gsub('/', '\\')
    else
      pdf_path_for_chrome = pdf_file:gsub('/', '\\')
    end

    -- Use Chrome headless to print to PDF
    local cmd = string.format(
      '"%s" --headless --disable-gpu --print-to-pdf="%s" "%s"',
      chrome_path,
      pdf_path_for_chrome,
      url
    )

    vim.notify('Generating PDF with Mermaid support...', vim.log.levels.INFO)
    vim.fn.system(cmd)

    -- Stop preview after PDF generation
    vim.cmd('MarkdownPreviewStop')

    if vim.v.shell_error == 0 and vim.fn.filereadable(pdf_file) == 1 then
      vim.notify('PDF created: ' .. vim.fn.fnamemodify(pdf_file, ':t'), vim.log.levels.INFO)
      -- Open PDF in default viewer
      if vim.fn.has('unix') == 1 then
        vim.fn.system('explorer.exe "' .. pdf_path_for_chrome .. '"')
      else
        vim.fn.system('start "" "' .. pdf_file .. '"')
      end
    else
      vim.notify('PDF generation failed!', vim.log.levels.ERROR)
    end
  end, 3000) -- Wait 3 seconds for Mermaid to render
end, { desc = '[M]arkdown [P]DF export (with Mermaid)' })

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
