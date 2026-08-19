-- lua/shared/keybindings/review.lua
-- [N]otiz: Self-PR — private Notizen an Datei:Zeile waehrend Diff-Review, ausserhalb
-- des Projekt-Repos gespeichert (stdpath('data')), damit nie versehentlich committed
-- wird. Eine Notiz ist eine Session: <leader>nn oeffnet/versteckt dasselbe Fenster.
-- Der Datei:Zeile-Anker bleibt fix auf der Position wo die Notiz begonnen wurde, auch
-- wenn man zwischendurch anderswo hinspringt um Text/Code zu kopieren und wieder
-- reinzupasten. Erst <C-s> speichert + haengt an die Notiz-Datei an und beendet die
-- Session (danach macht <leader>nn wieder eine neue, an der dann aktuellen Position).

local note_state = {}

local function get_git_branch()
  local branch = vim.fn.systemlist('git rev-parse --abbrev-ref HEAD')[1]
  if not branch or branch == '' then
    return 'unknown'
  end
  return branch
end

local function notes_file_path()
  local data_dir = vim.fn.stdpath('data') .. '/review-notes'
  vim.fn.mkdir(data_dir, 'p')
  local branch = get_git_branch():gsub('[\\/]', '_')
  local project = vim.g.project_name or 'project'
  return data_dir .. '/' .. project .. '_' .. branch .. '.md'
end

local function get_repo_root()
  local root = vim.fn.systemlist('git rev-parse --show-toplevel')[1]
  if vim.v.shell_error == 0 and root and root ~= '' then
    return (root:gsub('\\', '/'))
  end
  return (vim.fn.getcwd():gsub('\\', '/'))
end

-- Diffview-Buffer heissen "diffview://<git-dir>/<rev-context>/<relativer-pfad>".
-- <git-dir> und <rev-context> sind variabel (Worktree-Pfade, Hashes, "null" fuer
-- working tree...) -- statt das zu parsen, probieren wir Suffixe des Pfads von
-- rechts nach links durch, bis einer als echte Datei im Repo aufloest.
local function current_file_label()
  local raw = vim.api.nvim_buf_get_name(0)
  if not raw:match('^diffview://') then
    return vim.fn.fnamemodify(raw, ':.')
  end
  local stripped = raw:gsub('^diffview://', '')
  local parts = {}
  for part in stripped:gmatch('[^/]+') do
    table.insert(parts, part)
  end
  local root = get_repo_root()
  for i = #parts, 1, -1 do
    local candidate = table.concat(parts, '/', i)
    if vim.fn.filereadable(root .. '/' .. candidate) == 1 then
      return candidate
    end
  end
  -- Fallback: letzte 3 Segmente (best effort, falls Repo-Root nicht passt)
  local n = #parts
  return table.concat(parts, '/', math.max(1, n - 2))
end

-- Versteckt das Notiz-Fenster, OHNE den Buffer/Inhalt zu killen (nvim_win_hide
-- versteckt den Buffer explizit, unabhaengig von 'bufhidden').
local function hide_note()
  if note_state.win and vim.api.nvim_win_is_valid(note_state.win) then
    vim.api.nvim_win_hide(note_state.win)
  end
  note_state.win = nil
end

-- Verwirft die Notiz komplett: Fenster zu, Buffer weg, nichts gespeichert.
local function discard_note()
  local buf = note_state.buf
  if note_state.win and vim.api.nvim_win_is_valid(note_state.win) then
    vim.api.nvim_win_close(note_state.win, true)
  end
  if buf and vim.api.nvim_buf_is_valid(buf) then
    vim.api.nvim_buf_delete(buf, { force = true })
  end
  note_state = {}
  vim.notify('Review-Note verworfen', vim.log.levels.WARN)
end

local function save_note()
  local buf = note_state.buf
  local anchor_file, anchor_line = note_state.file, note_state.line
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local text = table.concat(lines, '\n'):gsub('^%s+', ''):gsub('%s+$', '')

  hide_note()
  if vim.api.nvim_buf_is_valid(buf) then
    vim.api.nvim_buf_delete(buf, { force = true })
  end
  note_state = {}

  if text == '' then
    vim.notify('Review-Note leer, verworfen', vim.log.levels.WARN)
    return
  end

  local path = notes_file_path()
  local f = io.open(path, 'a')
  f:write(string.format('## %s:%d  _(%s)_\n\n%s\n\n---\n\n', anchor_file, anchor_line, os.date('%Y-%m-%d %H:%M'), text))
  f:close()
  vim.notify('Note gespeichert: ' .. anchor_file .. ':' .. anchor_line, vim.log.levels.INFO, { title = 'Review Note' })

  -- Auto-Advance zum naechsten Hunk
  local ok_gs, gitsigns = pcall(require, 'gitsigns')
  if ok_gs then
    pcall(gitsigns.nav_hunk, 'next')
  end
end

local function show_note()
  local buf = note_state.buf
  local width = math.floor(vim.o.columns * 0.6)
  local height = math.floor(vim.o.lines * 0.4)
  local win = vim.api.nvim_open_win(buf, true, {
    relative = 'editor',
    width = width,
    height = height,
    row = math.floor((vim.o.lines - height) / 2),
    col = math.floor((vim.o.columns - width) / 2),
    style = 'minimal',
    border = 'rounded',
    title = string.format(' Review Note: %s:%d | <C-s> speichern, t/<Esc> verstecken, q verwerfen ', note_state.file, note_state.line),
    title_pos = 'center',
  })
  note_state.win = win

  vim.keymap.set({ 'n', 'i' }, '<C-s>', save_note, { buffer = buf, desc = 'Review-Note speichern' })
  vim.keymap.set('n', 't', hide_note, { buffer = buf, desc = 'Review-Note verstecken (Toggle, Inhalt bleibt)' })
  vim.keymap.set('n', '<Esc>', hide_note, { buffer = buf, desc = 'Review-Note verstecken (Inhalt bleibt)' })
  vim.keymap.set('n', 'q', discard_note, { buffer = buf, desc = 'Review-Note verwerfen (nicht gespeichert)' })

  vim.cmd('startinsert')
end

-- Notiz Neu/Toggle:
--  * keine Session aktiv         -> neue Notiz, Anker = aktuelle Datei:Zeile
--  * Session aktiv + sichtbar    -> verstecken (Inhalt bleibt im Buffer)
--  * Session aktiv + versteckt   -> wieder anzeigen (gleicher Anker, gleicher Inhalt)
-- So kannst du zwischendurch woanders hinspringen, Code/Text kopieren, und die
-- Notiz danach mit dem Copy-Inhalt weiterschreiben, ohne den Anker zu verlieren.
vim.keymap.set('n', '<leader>nn', function()
  if note_state.buf and vim.api.nvim_buf_is_valid(note_state.buf) then
    if note_state.win and vim.api.nvim_win_is_valid(note_state.win) then
      hide_note()
    else
      show_note()
    end
    return
  end

  local buf = vim.api.nvim_create_buf(false, true)
  vim.bo[buf].filetype = 'markdown'
  vim.bo[buf].bufhidden = 'hide'
  note_state = {
    buf = buf,
    file = current_file_label(),
    line = vim.fn.line('.'),
  }
  show_note()
end, { desc = '[N]otiz [N]eu/Toggle (Self-PR-Kommentar, Anker bleibt fix bis gespeichert)' })

-- Notizen anzeigen: alle bisherigen Notizen fuer diesen Branch
-- + gleichzeitig kompletten Inhalt ins Clipboard (zum direkten Weiterpasten)
vim.keymap.set('n', '<leader>nN', function()
  local path = notes_file_path()
  if vim.fn.filereadable(path) == 0 then
    vim.notify('Noch keine Review-Notes fuer diesen Branch.', vim.log.levels.INFO)
    return
  end
  local content = table.concat(vim.fn.readfile(path), '\n')
  vim.fn.setreg('+', content)
  vim.cmd('vsplit ' .. vim.fn.fnameescape(path))
  vim.notify('Notes geoeffnet + komplett ins Clipboard kopiert', vim.log.levels.INFO, { title = 'Review Notes' })
end, { desc = '[N]otizen [N]-alle anzeigen (alle Notizen dieses Branches + Clipboard)' })

-- Notizen loeschen: leert die Append-Ablage fuer diesen Branch komplett
-- (z.B. nachdem du sie per <leader>nN rauskopiert und verarbeitet hast).
-- Mit Bestaetigung, weil das nicht rueckgaengig zu machen ist.
vim.keymap.set('n', '<leader>nD', function()
  local path = notes_file_path()
  if vim.fn.filereadable(path) == 0 then
    vim.notify('Keine Review-Notes zum Loeschen vorhanden.', vim.log.levels.INFO)
    return
  end
  local line_count = #vim.fn.readfile(path)
  local choice = vim.fn.confirm(
    string.format('Review-Notes fuer diesen Branch wirklich loeschen? (%d Zeilen)', line_count),
    '&Ja\n&Nein',
    2
  )
  if choice ~= 1 then
    vim.notify('Abgebrochen, Notes bleiben erhalten.', vim.log.levels.INFO)
    return
  end
  vim.fn.delete(path)
  vim.notify('Review-Notes geloescht: ' .. vim.fn.fnamemodify(path, ':t'), vim.log.levels.WARN, { title = 'Review Notes' })
end, { desc = '[N]otes [D]elete (Append-Ablage fuer diesen Branch komplett leeren)' })
