-- lua/shared/core.lua
-- Kern-Konfiguration: Globals, vim.opt, Autocmds, Lazy Bootstrap + Plugins
-- Lade-Reihenfolge: platform.lua → project.lua → DIESE DATEI → keybindings/
--
-- INVARIANTE: vim.g.project_* muss BEREITS gesetzt sein (via require('shared.project').detect())
--             bevor dieses Modul geladen wird.

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität: alle is_windows-Referenzen in diesem Modul

-- Set <space> as the leader key
-- See `:help mapleader`
--  NOTE: Must happen before plugins are loaded (otherwise wrong leader will be used)
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- Set to true if you have a Nerd Font installed and selected in the terminal
vim.g.have_nerd_font = false

-- Notification toggle (vim.notify suppression)
vim.g.notifications_enabled = true
local _original_notify = vim.notify
vim.notify = function(msg, level, opts)
  if vim.g.notifications_enabled then
    _original_notify(msg, level, opts)
  end
end

vim.keymap.set('n', '<leader>tN', function()
  vim.g.notifications_enabled = not vim.g.notifications_enabled
  _original_notify('Notifications: ' .. (vim.g.notifications_enabled and 'ON' or 'OFF'), vim.log.levels.INFO)
end, { desc = '[T]oggle [N]otifications' })

-- Reduce LSP log spam (OmniSharp sends many warnings during startup)
vim.lsp.set_log_level('ERROR')

-- [[ Swap File Handling ]]
-- Automatically handle swap file conflicts (E325: ATTENTION)
-- This fixes errors when plugins (Diffview, Obsidian, Telescope) try to open files programmatically
vim.api.nvim_create_autocmd('SwapExists', {
  callback = function()
    vim.v.swapchoice = 'e' -- Edit anyway (ignore swap file)
  end,
})

-- [[ Windows MAX_PATH Fix fuer Diffview ]]
-- Diffview-Buffer-Namen kombinieren ".git/worktrees/<long-worktree>/<sha-prefix>/<deep-path>"
-- und sprengen damit Windows' 260-Zeichen-Limit beim Swap-File. Resultat:
-- "E303: Unable to open swap file" → "Failed to create diff buffer".
-- Fix: Swap fuer alle diffview://-Buffer global deaktivieren (sind eh read-only Diff-Views).
vim.api.nvim_create_autocmd({ 'BufNew', 'BufAdd', 'BufReadPre' }, {
  pattern = { 'diffview://*', 'diffview:*' },
  callback = function(args)
    pcall(function() vim.bo[args.buf].swapfile = false end)
  end,
})

-- Swap-Directory auf kurzen Pfad legen (defense in depth — kürzt jeden Swap-Pfad
-- um ~50 Zeichen gegenueber dem default ~/AppData/Local/nvim-data/swap/).
-- Das doppelte // am Ende: encode full path in swap filename (verhindert Kollisionen).
if vim.fn.has('win32') == 1 then
  local short_swap = 'C:/.nvim-swp'
  if vim.fn.isdirectory(short_swap) == 0 then
    pcall(vim.fn.mkdir, short_swap, 'p')
  end
  vim.opt.directory = short_swap .. '//'
end

-- [[ Auto-copy .claude folder — ENTFERNT 2026-05-07 (Schweizer-Uhrmacher PL-R) ]]
-- Frueherer VimEnter-Autocmd las AgentsArchive/.claude (ohne Suffix) als Bootstrap-Fallback.
-- Mit der 3-Slot-Symmetrie (DCSRE/.claude_DCSRE, CENCOCD/.claude_CenCoCo, OMNICOMMAND/.claude_OmniCommand)
-- und Loeschung von AgentsArchive/.claude zeigte der Bootstrap auf nicht-existente Pfade.
-- Sync wird jetzt ausschliesslich von claude_sync.lua erledigt (project_name-bewusst, robocopy /E /XO).
-- Fuer UNKNOWN-Projekte: kein Sync (konsistent zur Symmetrie-Doktrin).

-- [[ Project-specific terminal background color ]]
-- Changes terminal background based on project path:
--   DCSRE  = Green tint  (G)
--   CENCOCD = Blue tint  (B)
--   Private = Red tint   (R)
vim.api.nvim_create_autocmd('VimEnter', {
  callback = function()
    local cwd_upper = vim.fn.getcwd():upper()
    if cwd_upper:find('DCSRE') then
      -- Green tint for DCSRE
      io.write('\027]11;rgb:0a/18/0a\027\\')
    elseif cwd_upper:find('CENCOC') then
      -- Blue tint for CENCOCD
      io.write('\027]11;rgb:0a/0a/18\027\\')
    else
      -- Red tint for Private
      io.write('\027]11;rgb:18/0a/0a\027\\')
    end
  end,
})

-- Reset terminal background when leaving Neovim
vim.api.nvim_create_autocmd('VimLeave', {
  callback = function()
    io.write('\027]104\027\\')
  end,
})


-- Welcome message showing which project was detected
vim.api.nvim_create_autocmd('VimEnter', {
  callback = function()
    vim.notify('Welcome to ' .. vim.g.project_name .. '!', vim.log.levels.INFO)
  end,
})

-- [[ Setting options ]]
-- See `:help vim.o`
-- NOTE: You can change these options as you wish!
--  For more options, you can see `:help option-list`

-- Enable 24-bit RGB colors (True Color) - CRITICAL for themes!
vim.o.termguicolors = true

-- Keep cursor centered vertically (8 lines from top/bottom)
vim.o.scrolloff = 8

-- Make line numbers default
vim.o.number = true
-- You can also add relative line numbers, to help with jumping.
--  Experiment for yourself to see if you like it!
-- vim.o.relativenumber = true

-- Enable mouse mode, can be useful for resizing splits for example!
vim.o.mouse = 'a'

-- Don't show the mode, since it's already in the status line
vim.o.showmode = false

-- Sync clipboard between OS and Neovim.
--  Schedule the setting after `UiEnter` because it can increase startup-time.
--  Remove this option if you want your OS clipboard to remain independent.
--  See `:help 'clipboard'`
vim.schedule(function()
  vim.o.clipboard = 'unnamedplus'
end)

-- Enable break indent
vim.o.breakindent = true

-- Save undo history
vim.o.undofile = true

-- Swap-Files global aus: Diffview-Buffer (diffview://...) sprengen auf Windows
-- den MAX_PATH-260-Limit beim Swap-Pfad → E303 "Unable to open swap file" →
-- "Failed to create diff buffer". Lua-Autocmds koennen das nicht abfangen,
-- weil der Swap-Crash INSIDE des nvim_buf_set_name C-Calls passiert, bevor
-- BufFilePre/BufFilePost feuern. Recovery uebernimmt undofile (Zeile 147).
vim.o.swapfile = false

-- Case-insensitive searching UNLESS \C or one or more capital letters in the search term
vim.o.ignorecase = true
vim.o.smartcase = true

-- Keep signcolumn on by default
vim.o.signcolumn = 'yes'

-- Decrease update time
vim.o.updatetime = 250

-- Decrease mapped sequence wait time
vim.o.timeoutlen = 300

-- Configure how new splits should be opened
vim.o.splitright = true
vim.o.splitbelow = true

-- Sets how neovim will display certain whitespace characters in the editor.
--  See `:help 'list'`
--  and `:help 'listchars'`
--
--  Notice listchars is set using `vim.opt` instead of `vim.o`.
--  It is very similar to `vim.o` but offers an interface for conveniently interacting with tables.
--   See `:help lua-options`
--   and `:help lua-options-guide`
vim.o.list = true
vim.opt.listchars = { tab = '» ', trail = '·', nbsp = '␣' }

-- Preview substitutions live, as you type!
vim.o.inccommand = 'split'

-- Show which line your cursor is on
vim.o.cursorline = true

-- Minimal number of screen lines to keep above and below the cursor.
vim.o.scrolloff = 10

-- if performing an operation that would fail due to unsaved changes in the buffer (like `:q`),
-- instead raise a dialog asking if you wish to save the current file(s)
-- See `:help 'confirm'`
vim.o.confirm = true

-- Performance: verhindert Treesitter/Syntax-Highlighter-Aborts bei grossen Diffs.
-- redrawtime: max ms fuer Screen-Redraw bevor Syntax-HL abgeschaltet wird (default 2000).
-- synmaxcol: Zeilen-Spalten-Limit fuer Syntax-HL — fixt Angular/HTML-Templates mit langen Lines.
-- maxmempattern: KB fuer Regex-Speicher (default 1000).
vim.opt.redrawtime    = 10000
vim.opt.synmaxcol     = 500
vim.opt.maxmempattern = 5000

-- [[ Basic Keymaps ]]
--  See `:help vim.keymap.set()`

-- Clear highlights on search when pressing <Esc> in normal mode
--  See `:help hlsearch`
vim.keymap.set('n', '<Esc>', '<cmd>nohlsearch<CR>')

-- Navigate to next/previous warning (like ]d but only for warnings)
vim.keymap.set('n', ']w', function()
  vim.diagnostic.goto_next({ severity = vim.diagnostic.severity.WARN })
end, { desc = 'Next [W]arning' })

vim.keymap.set('n', '[w', function()
  vim.diagnostic.goto_prev({ severity = vim.diagnostic.severity.WARN })
end, { desc = 'Previous [W]arning' })

-- Auto-save when leaving insert mode
vim.api.nvim_create_autocmd('InsertLeave', {
  pattern = '*',
  callback = function()
    if vim.bo.modified and vim.bo.buftype == '' and vim.fn.expand('%') ~= '' then
      vim.cmd('silent! update')
    end
  end,
  desc = 'Auto-save on leaving insert mode',
})

-- Exit terminal mode in the builtin terminal with a shortcut that is a bit easier
-- for people to discover. Otherwise, you normally need to press <C-\><C-n>, which
-- is not what someone will guess without a bit more experience.
--
-- NOTE: This won't work in all terminal emulators/tmux/etc. Try your own mapping
-- or just use <C-\><C-n> to exit terminal mode
vim.keymap.set('t', '<Esc><Esc>', '<C-\\><C-n>', { desc = 'Exit terminal mode' })

-- TIP: Disable arrow keys in normal mode
-- vim.keymap.set('n', '<left>', '<cmd>echo "Use h to move!!"<CR>')
-- vim.keymap.set('n', '<right>', '<cmd>echo "Use l to move!!"<CR>')
-- vim.keymap.set('n', '<up>', '<cmd>echo "Use k to move!!"<CR>')
-- vim.keymap.set('n', '<down>', '<cmd>echo "Use j to move!!"<CR>')

-- Keybinds to make split navigation easier.
--  Use CTRL+<hjkl> to switch between windows
--
--  See `:help wincmd` for a list of all window commands
vim.keymap.set('n', '<C-h>', '<C-w><C-h>', { desc = 'Move focus to the left window' })
vim.keymap.set('n', '<C-l>', '<C-w><C-l>', { desc = 'Move focus to the right window' })
vim.keymap.set('n', '<C-j>', '<C-w><C-j>', { desc = 'Move focus to the lower window' })
vim.keymap.set('n', '<C-k>', '<C-w><C-k>', { desc = 'Move focus to the upper window' })

-- Quick close window/buffer
vim.keymap.set('n', '<leader>q', '<cmd>q<cr>', { desc = '[Q]uit/Close window' })
vim.keymap.set('n', '<leader>bd', '<cmd>bd<cr>', { desc = '[B]uffer [D]elete' })

-- Buffer-Navigation: Alt+h/Alt+l -- vorheriger/naechster Buffer.
-- NICHT Ctrl+h/Ctrl+l: die sind Window-Fokus-Wechsel (Zeile 251-252), Kickstart-
-- Standard, nicht anfassen. NICHT Ctrl+Shift+[/]: das Terminal schluckt die Shift-
-- Modifier-Info bei dieser Kombination, es kam nur <C-]> an (Vims Tag-Jump, daher
-- "E433: No tags file").
vim.keymap.set('n', '<A-l>', '<cmd>bnext<cr>', { desc = 'Next buffer' })
vim.keymap.set('n', '<A-h>', '<cmd>bprevious<cr>', { desc = 'Previous buffer' })

-- Center cursor after half-page jumps
vim.keymap.set('n', '<C-d>', '<C-d>zz', { desc = 'Half page down + center' })
vim.keymap.set('n', '<C-u>', '<C-u>zz', { desc = 'Half page up + center' })

-- NOTE: Some terminals have colliding keymaps or are not able to send distinct keycodes
-- vim.keymap.set("n", "<C-S-h>", "<C-w>H", { desc = "Move window to the left" })
-- vim.keymap.set("n", "<C-S-l>", "<C-w>L", { desc = "Move window to the right" })
-- vim.keymap.set("n", "<C-S-j>", "<C-w>J", { desc = "Move window to the lower" })
-- vim.keymap.set("n", "<C-S-k>", "<C-w>K", { desc = "Move window to the upper" })

-- [[ Basic Autocommands ]]
--  See `:help lua-guide-autocommands`

-- Highlight when yanking (copying) text
--  Try it with `yap` in normal mode
--  See `:help vim.hl.on_yank()`
vim.api.nvim_create_autocmd('TextYankPost', {
  desc = 'Highlight when yanking (copying) text',
  group = vim.api.nvim_create_augroup('kickstart-highlight-yank', { clear = true }),
  callback = function()
    vim.hl.on_yank()
  end,
})

-- [[ Install `lazy.nvim` plugin manager ]]
--    See `:help lazy.nvim.txt` or https://github.com/folke/lazy.nvim for more info
local lazypath = vim.fn.stdpath 'data' .. '/lazy/lazy.nvim'
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local lazyrepo = 'https://github.com/folke/lazy.nvim.git'
  local out = vim.fn.system { 'git', 'clone', '--filter=blob:none', '--branch=stable', lazyrepo, lazypath }
  if vim.v.shell_error ~= 0 then
    error('Error cloning lazy.nvim:\n' .. out)
  end
end

---@type vim.Option
local rtp = vim.opt.rtp
rtp:prepend(lazypath)

-- [[ Configure and install plugins ]]
--
--  To check the current status of your plugins, run
--    :Lazy
--
--  You can press `?` in this menu for help. Use `:q` to close the window
--
--  To update plugins you can run
--    :Lazy update
--
-- NOTE: Here is where you install your plugins.
require('lazy').setup({
  -- NOTE: Plugins can be added with a link (or for a github repo: 'owner/repo' link).
  'NMAC427/guess-indent.nvim', -- Detect tabstop and shiftwidth automatically

  -- OmniSharp Extended - Handles metadata/decompiled source navigation
  -- Fixes "Cursor position outside buffer" errors when using gd on framework symbols
  {
    'Hoffs/omnisharp-extended-lsp.nvim',
    ft = 'cs', -- Load only for C# files
  },

  -- SonarQube - Code quality analysis for C#
  -- Set SONAR_QUBE_ENABLED=1 in .bashrc to enable
  {
    'iamkarasik/sonarqube.nvim',
    ft = 'cs',
    enabled = vim.env.SONAR_QUBE_ENABLED == '1',
    dependencies = { 'neovim/nvim-lspconfig' },
    config = function()
      require('sonarqube').setup({
        server = {
          url = 'https://sonar.itsg.de',
          token = vim.env.SONAR_QUBE,
        },
        csharp = {
          enabled = true,
          omnisharpDirectory = vim.fn.expand('~/.local/share/nvim/mason/packages/omnisharp/'),
        },
      })
    end,
  },

  -- Neogit - Magit for Neovim (Git UI)
  {
    'NeogitOrg/neogit',
    dependencies = {
      'nvim-lua/plenary.nvim', -- required (already in kickstart)
      'sindrets/diffview.nvim', -- optional - better diff viewing
      'nvim-telescope/telescope.nvim', -- optional (already in kickstart)
    },
    cmd = 'Neogit', -- lazy load on command
    keys = {
      { '<leader>gg', '<cmd>Neogit<cr>', desc = '[G]it Neogit UI' },
      {
        '<leader>gD',
        function()
          vim.cmd('DiffviewOpen origin/develop..HEAD')
        end,
        desc = '[G]it [D]iff vs origin/develop',
      },
      {
        '<leader>gM',
        function()
          vim.cmd('DiffviewOpen origin/main..HEAD')
        end,
        desc = '[G]it diff vs [M]ain (CENCOCD)',
      },
      {
        '<leader>gS',
        function()
          require('telescope.builtin').git_branches({
            prompt_title = 'Diff against which branch?',
            attach_mappings = function(prompt_bufnr)
              local actions = require('telescope.actions')
              local action_state = require('telescope.actions.state')
              actions.select_default:replace(function()
                local selection = action_state.get_selected_entry()
                actions.close(prompt_bufnr)
                if selection then
                  local branch = selection.value
                  vim.cmd('DiffviewOpen ' .. branch .. '..HEAD')
                end
              end)
              return true
            end,
          })
        end,
        desc = '[G]it Diff [S]elect branch (Telescope picker)',
      },
      { '<leader>g.', '<cmd>DiffviewClose<cr>', desc = '[G]it [.] close diff (done)' },
      {
        '<leader>gF',
        function()
          local filepath = vim.fn.expand('%')
          if filepath == '' then
            vim.notify('No file in current buffer!', vim.log.levels.ERROR)
            return
          end
          vim.cmd('DiffviewOpen -- ' .. filepath)
          vim.notify('Diff for: ' .. filepath, vim.log.levels.INFO)
        end,
        desc = '[G]it diff [F]ile (unstaged changes)',
      },
      {
        '<leader>gf',
        function()
          local filepath = vim.fn.expand('%')
          if filepath == '' then
            vim.notify('No file in current buffer!', vim.log.levels.ERROR)
            return
          end
          vim.cmd('DiffviewFileHistory ' .. filepath)
          vim.notify('Opened diff history for: ' .. filepath, vim.log.levels.INFO)
        end,
        desc = '[G]it [F]ile history (diff)',
      },
      { '<leader>gd', '<cmd>DiffviewOpen<cr>', desc = '[G]it [D]iff (uncommitted changes)' },
      { '<leader>gl', '<cmd>Neogit log kind=current<cr>', desc = '[G]it [L]og (current branch)' },
      { '<leader>gc', '<cmd>Neogit commit<cr>', desc = '[G]it [C]ommit' },
      {
        '<leader>gh',
        function()
          local clipboard = vim.fn.getreg('+'):gsub('^%s+', ''):gsub('%s+$', '')
          if clipboard == '' then
            vim.notify('Clipboard is empty!', vim.log.levels.ERROR)
            return
          end
          local commit_hash = clipboard:match('^([0-9a-fA-F]+)')
          if not commit_hash or #commit_hash < 7 or #commit_hash > 40 then
            vim.notify('No valid git hash found in clipboard!', vim.log.levels.ERROR)
            return
          end
          -- Show only this single commit's changes
          vim.cmd('DiffviewOpen ' .. commit_hash .. '^..' .. commit_hash)
          vim.notify('Showing commit: ' .. commit_hash, vim.log.levels.INFO)
        end,
        desc = '[G]it [H]ash show (single commit from clipboard)',
      },
      {
        '<leader>gC',
        function()
          local clipboard = vim.fn.getreg('+'):gsub('^%s+', ''):gsub('%s+$', '')
          if clipboard == '' then
            vim.notify('Clipboard is empty!', vim.log.levels.ERROR)
            return
          end
          -- Extract git hash (7-40 hex characters at the beginning)
          local commit_hash = clipboard:match('^([0-9a-fA-F]+)')
          if not commit_hash or #commit_hash < 7 or #commit_hash > 40 then
            vim.notify('No valid git hash found in clipboard!', vim.log.levels.ERROR)
            return
          end
          -- Show changes from this commit to HEAD (current branch)
          vim.cmd('DiffviewOpen ' .. commit_hash .. '..HEAD')
          vim.notify('Opened diff: ' .. commit_hash .. '..HEAD', vim.log.levels.INFO)
        end,
        desc = '[G]it [C]lipboard hash diff (branch changes only)',
      },
    },
    opts = {
      -- Performance optimizations for large repos (especially WSL2 + /mnt/c/)
      disable_insert_on_commit = true, -- Don't enter insert mode on commit
      disable_signs = true, -- Don't show signs in gutter (faster)
      disable_hint = true, -- Don't show hints (faster)
      disable_context_highlighting = true, -- Don't highlight context (faster)
      disable_commit_confirmation = true, -- Skip confirmation dialog
      fetch_after_checkout = false, -- Don't auto-fetch after checkout
      auto_refresh = true, -- Keep auto-refresh but limit what it loads
      auto_show_console = false, -- Don't show console (faster startup)

      -- Limit what's loaded on startup
      status = {
        recent_commit_count = 5, -- Reduced from 10 to 5 (faster)
        show_head_commit_hash = false, -- Don't show hash (faster)
      },

      -- Graph style (unicode is faster than ascii art)
      graph_style = "unicode",

      -- Git settings
      git_services = {}, -- Disable git service integrations (faster)

      -- Commit editor settings
      commit_editor = {
        kind = "tab", -- Open commit editor in tab
        staged_diff_split_kind = "auto", -- Auto split for staged diff
      },

      -- Sections to show (disable what you don't need)
      sections = {
        untracked = { folded = true }, -- Fold untracked by default
        unstaged = { folded = false },
        staged = { folded = false },
        stashes = { folded = true }, -- Fold stashes (you have 33!)
        unpulled_upstream = { folded = true },
        unmerged_upstream = { folded = true },
        unpulled_pushRemote = { folded = true },
        unmerged_pushRemote = { folded = true },
        recent = { folded = true }, -- Fold recent commits
        rebase = { folded = true },
      },

      -- Integrations (keep minimal)
      integrations = {
        diffview = true,
        telescope = false, -- Disable telescope integration (faster)
      },
    },
  },

  -- Diffview explicit setup (vorher nur Neogit-Dependency mit Defaults).
  -- Fix fuer "Failed to create diff buffer" bei grossen HTML/Angular-Templates:
  -- enhanced_diff_hl=false und Treesitter-Abschaltung pro Diff-Buffer verhindern
  -- den synchronen TS-Parse-Crash bei 3-way merge view ueber 1500+ Zeilen.
  {
    'sindrets/diffview.nvim',
    cmd = { 'DiffviewOpen', 'DiffviewClose', 'DiffviewRefresh', 'DiffviewFileHistory', 'DiffviewToggleFiles' },
    opts = {
      diff_binaries = false,
      enhanced_diff_hl = false,
      use_icons = true,
      view = {
        default      = { layout = 'diff2_horizontal', disable_diagnostics = true },
        merge_tool   = { layout = 'diff3_horizontal', disable_diagnostics = true },
        file_history = { layout = 'diff2_horizontal', disable_diagnostics = true },
      },
      hooks = {
        diff_buf_read = function(bufnr)
          -- Treesitter pro Diff-Buffer aus (verhindert Race bei grossen Files)
          pcall(vim.treesitter.stop, bufnr)
          -- LSP-Diagnostics aus (Diff-Buffer braucht keine)
          pcall(vim.diagnostic.enable, false, { bufnr = bufnr })
        end,
      },
    },
  },

  -- Markdown Preview mit Mermaid Support (Browser-based)
  -- Industry standard: 7,540+ GitHub stars
  {
    'iamcco/markdown-preview.nvim',
    cmd = { 'MarkdownPreviewToggle', 'MarkdownPreview', 'MarkdownPreviewStop' },
    ft = { 'markdown' },
    build = 'cd app && npm install',
    init = function()
      vim.g.mkdp_filetypes = { 'markdown' }
      -- Auto-close preview when switching buffers (0 = keep open, 1 = auto-close)
      vim.g.mkdp_auto_close = 0
      -- Theme: 'dark' oder 'light'
      vim.g.mkdp_theme = 'dark'
      -- KEIN fester Port! Ein gepinnter Port kollidiert mit einem noch laufenden
      -- Preview-Prozess: das Plugin ruft plugin.init() erst NACH erfolgreichem listen()
      -- auf (app/server.js), d.h. bei belegtem Port bleibt `app` undefined und jeder
      -- Refresh wirft "Cannot read properties of undefined (reading 'refreshPage')".
      -- Der Zufallsport ist die robuste Variante; die URL fangen wir unten in
      -- OpenMarkdownPreview ab (das Plugin uebergibt sie dort als Argument).
      -- Open in browser - ALWAYS open in NEW Chrome window
      vim.g.mkdp_browserfunc = 'OpenMarkdownPreview'
      -- Die Preview-URL landet hier als Argument; wir merken sie in g:mkdp_last_url,
      -- damit man sie zum Debuggen nachschlagen kann (:echo g:mkdp_last_url).
      -- Der PDF-Export (<leader>mP / <leader>mS) braucht sie NICHT — der geht ueber
      -- Pandoc und eine lokale HTML-Datei, siehe keybindings/clipboard.lua.
      if vim.fn.has('win32') == 1 then
        -- Windows: Chrome mit --new-window Flag
        vim.cmd([[
          function OpenMarkdownPreview(url)
            let g:mkdp_last_url = a:url
            execute 'silent !start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --new-window "' . a:url . '"'
          endfunction
        ]])
      else
        -- WSL: Chrome via Windows path mit --new-window
        vim.cmd([[
          function OpenMarkdownPreview(url)
            let g:mkdp_last_url = a:url
            execute 'silent !/mnt/c/Program\ Files/Google/Chrome/Application/chrome.exe --new-window "' . a:url . '"'
          endfunction
        ]])
      end
      -- Mermaid, PlantUML, Chart.js support included by default
    end,
    keys = {
      { '<leader>mp', '<cmd>MarkdownPreviewToggle<cr>', desc = '[M]arkdown [P]review' },
    },
  },

  -- Obsidian.nvim - Write and navigate Obsidian vaults in Neovim
  -- Community fork (actively maintained): https://github.com/obsidian-nvim/obsidian.nvim
  {
    'obsidian-nvim/obsidian.nvim',
    version = '*',
    lazy = false, -- Load immediately so :Obsidian commands work from startup
    dependencies = {
      'nvim-lua/plenary.nvim',
    },
    init = function()
      -- Set conceallevel for Markdown files (Obsidian wiki links [[link]] → link)
      -- Autocmd ist robuster als globale Einstellung (wird nicht überschrieben)
      vim.api.nvim_create_autocmd('FileType', {
        pattern = { 'markdown' },
        callback = function()
          vim.opt_local.conceallevel = 2
        end,
      })

      -- Disable swap files for Obsidian vault files to avoid E325 swap file conflicts
      -- when opening notes via Telescope picker (the picker can't handle the swap dialog)
      vim.api.nvim_create_autocmd('BufReadPre', {
        pattern = {
          '*/Documents/DCS/*',
          '*/Documents/DCS/**',
          '*/Documents/Obsydian/*',
          '*/Documents/Obsydian/**',
          '*/Documents/Brain/*',
          '*/Documents/Brain/**',
        },
        callback = function()
          vim.opt_local.swapfile = false
        end,
      })
    end,
    ---@module 'obsidian'
    ---@type obsidian.config
    opts = {
      legacy_commands = false, -- Use new command style (will be removed in next major release)

      workspaces = (function()
        local _platform = require('shared.platform')
        local home = _platform.user_home()  -- 'C:/Users/<USER>' oder '/mnt/c/Users/<USER>'
        return {
          { name = 'DCSRE',       path = home .. '/Documents/DCS' },
          { name = 'CenCoCo',     path = home .. '/Documents/Obsydian/CenCoCo' },
          { name = 'Brain',       path = home .. '/Documents/Brain' },
          { name = 'OmniCommand', path = home .. '/Documents/OmniCommand' },
        }
      end)(),

      -- FIX: Neue Notizen im Vault-Root erstellen, nicht im "current_dir"
      -- Das war der Bug! Default war "current_dir" -> Notizen landeten im falschen Ordner
      new_notes_location = 'current_dir',

      -- Note ID: Verwende den Titel als Dateiname (nicht Zettelkasten-ID)
      -- So heißt die Datei "Meine Notiz.md" statt "1705123456.md"
      note_id_func = function(title)
        if title ~= nil then
          -- Titel als Dateiname verwenden (Leerzeichen durch Bindestriche ersetzen)
          return title:gsub(' ', '-'):gsub('[^A-Za-z0-9%-äöüÄÖÜß]', '')
        else
          -- Fallback: Zeitstempel wenn kein Titel
          return tostring(os.time())
        end
      end,

      -- Daily Notes: Konfiguration für :Obsidian today/yesterday
      daily_notes = {
        folder = 'Daily', -- Unterordner für tägliche Notizen
        date_format = '%Y-%m-%d', -- Format: 2025-01-16
        default_tags = { 'daily' }, -- Automatische Tags
      },

      -- Templates: Wiederverwendbare Vorlagen für verschiedene Notiz-Typen
      templates = {
        folder = 'Templates', -- Unterordner für Templates
        date_format = '%Y-%m-%d', -- Format für {{date}}
        time_format = '%H:%M', -- Format für {{time}}
        -- Substitutions: Custom Variablen die du in Templates nutzen kannst
        -- Beispiel in Template: {{feature_number}} → wird zu "881"
        substitutions = {
          feature_number = function()
            return vim.fn.input('Feature Number (z.B. 881): ')
          end,
          topic = function()
            return vim.fn.input('Topic Tag (z.B. DIC, WCF, SFTP): ')
          end,
          goal = function()
            return vim.fn.input('Ziel: ')
          end,
          task1 = function()
            return vim.fn.input('Task 1: ')
          end,
          task2 = function()
            return vim.fn.input('Task 2: ')
          end,
        },
      },

      -- Attachments: Wo Bilder gespeichert werden
      attachments = {
        folder = 'attachments',
        confirm_img_paste = true,
      },

      -- Completion deaktiviert (kein nvim-cmp installiert, blink.cmp wird verwendet)
      completion = {
        nvim_cmp = false,
        blink = false,
      },

      -- UI: Checkbox-Icons ohne Nerd Font (Unicode statt Nerd Font Glyphen)
      -- Fix: Default nutzt Nerd Font Icons die als ? angezeigt werden wenn keine Nerd Font installiert
      ui = {
        enable = true,
        checkboxes = {
          [' '] = { char = '☐', hl_group = 'ObsidianTodo' },
          ['x'] = { char = '✔', hl_group = 'ObsidianDone' },
          ['>'] = { char = '▶', hl_group = 'ObsidianRightArrow' },
          ['~'] = { char = '~', hl_group = 'ObsidianTilde' },
          ['!'] = { char = '!', hl_group = 'ObsidianImportant' },
        },
      },
    },
    keys = {
      -- Notizen erstellen/öffnen
      { '<leader>on', '<cmd>Obsidian new<cr>', desc = '[O]bsidian [N]ew note' },
      { '<leader>oo', '<cmd>Obsidian open<cr>', desc = '[O]bsidian [O]pen in app' },
      { '<leader>os', '<cmd>Obsidian quick_switch<cr>', desc = '[O]bsidian [S]earch titles' },
      { '<leader>og', '<cmd>Obsidian search<cr>', desc = '[O]bsidian [G]rep content' },

      -- Daily Notes
      { '<leader>ot', '<cmd>Obsidian today<cr>', desc = '[O]bsidian [T]oday' },
      { '<leader>oy', '<cmd>Obsidian yesterday<cr>', desc = '[O]bsidian [Y]esterday' },
      { '<leader>od', '<cmd>Obsidian dailies<cr>', desc = '[O]bsidian [D]ailies list' },

      -- Templates
      { '<leader>oT', '<cmd>Obsidian template<cr>', desc = '[O]bsidian [T]emplate insert' },

      -- Links & Navigation
      { '<leader>ob', '<cmd>Obsidian backlinks<cr>', desc = '[O]bsidian [B]acklinks' },
      { '<leader>ol', '<cmd>Obsidian link<cr>', desc = '[O]bsidian [L]ink selection', mode = 'v' },
      -- Follow link: externe URLs in neuem Chrome Fenster, interne Links via Obsidian
      {
        '<leader>of',
        function()
          local line = vim.api.nvim_get_current_line()
          -- Prüfe ob externe URL (http/https)
          local url = line:match('https?://[%w%-%.%_%~%:%/%?%#%[%]%@%!%$%&%\'%(%)%*%+%,%;%=]+')
          if url then
            -- Externe URL in neuem Chrome Fenster öffnen
            if vim.fn.has('win32') == 1 then
              vim.fn.system('start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --new-window "' .. url .. '"')
            else
              -- WSL2: Chrome via Windows path
              vim.fn.system('"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" --new-window "' .. url .. '" &')
            end
            vim.notify('Öffne in Chrome: ' .. url, vim.log.levels.INFO)
          else
            -- Interne Wiki-Links via Obsidian
            vim.cmd('Obsidian follow_link')
          end
        end,
        desc = '[O]bsidian [F]ollow link (URLs in Chrome)',
      },

      -- Bild unter Cursor öffnen (robust - extrahiert Pfad aus Wiki-Link)
      {
        '<leader>op',
        function()
          -- Extrahiere Bild-Name aus Wiki-Link ![[...]]
          local line = vim.api.nvim_get_current_line()
          local img = line:match('!%[%[(.-%.[pP][nN][gG])%]%]') or line:match('!%[%[(.-%.[jJ][pP][eE]?[gG])%]%]')

          if not img then
            vim.notify('Kein Bild-Link auf dieser Zeile gefunden', vim.log.levels.WARN)
            return
          end

          -- Finde Vault-Root (suche nach .obsidian/)
          local current = vim.fn.expand('%:p:h')
          local vault_root = current
          while vault_root ~= '' and vault_root ~= '/' and vault_root ~= 'C:\\' do
            if vim.fn.isdirectory(vault_root .. '/.obsidian') == 1 or vim.fn.isdirectory(vault_root .. '\\.obsidian') == 1 then
              break
            end
            vault_root = vim.fn.fnamemodify(vault_root, ':h')
          end

          -- Vollständiger Pfad zum Bild
          local img_path = vault_root .. '/attachments/' .. img
          local img_path_win = img_path:gsub('/', '\\')
          local img_path_check = img_path:gsub('\\', '/')

          if vim.fn.filereadable(img_path_check) == 1 then
            vim.fn.system('powershell.exe -Command "Start-Process \'' .. img_path .. '\'"')
            vim.notify('Öffne: ' .. img, vim.log.levels.INFO)
          else
            vim.notify('Bild nicht gefunden: ' .. img_path, vim.log.levels.ERROR)
          end
        end,
        desc = '[O]bsidian [P]review image',
      },

      -- Graph View (öffnet Obsidian App mit Graph)
      -- WICHTIG: Braucht "Advanced URI" Plugin in Obsidian!
      -- Install: Settings → Community Plugins → Browse → "Advanced URI"
      {
        '<leader>oG',
        function()
          -- Finde Vault-Root (suche nach .obsidian/)
          local current = vim.fn.expand('%:p:h')
          local vault_root = current
          while vault_root ~= '' and vault_root ~= '/' and vault_root ~= 'C:\\' do
            if vim.fn.isdirectory(vault_root .. '/.obsidian') == 1 or vim.fn.isdirectory(vault_root .. '\\.obsidian') == 1 then
              break
            end
            vault_root = vim.fn.fnamemodify(vault_root, ':h')
          end

          -- Vault-Name aus Pfad ableiten (letzter Ordnername)
          local vault_name = vim.fn.fnamemodify(vault_root, ':t')

          -- Advanced URI zum Öffnen des Graph View
          local uri = 'obsidian://advanced-uri?vault=' .. vault_name .. '&commandid=graph:open'

          -- Öffne in Obsidian (Windows: start, Linux: xdg-open)
          if vim.fn.has('win32') == 1 then
            vim.fn.system('start "" "' .. uri .. '"')
          else
            vim.fn.system('xdg-open "' .. uri .. '"')
          end

          vim.notify('Öffne Graph View für Vault: ' .. vault_name, vim.log.levels.INFO)
        end,
        desc = '[O]bsidian [G]raph view',
      },

      -- Workspace (Vault wechseln)
      { '<leader>ow', '<cmd>Obsidian workspace<cr>', desc = '[O]bsidian [W]orkspace switch' },

      -- Image paste: Wird von img-clip.nvim übernommen (siehe unten)
    },
  },

  -- img-clip.nvim - Screenshot/Image paste für Obsidian Vaults
  -- Besser als obsidian.nvim paste_img: Native Windows Support!
  {
    'HakonHarnes/img-clip.nvim',
    event = 'VeryLazy',
    opts = function()
      -- Helper: Finde Obsidian Vault-Root (sucht nach .obsidian/ Ordner)
      local function find_vault_root()
        local current = vim.fn.expand('%:p:h') -- Verzeichnis der aktuellen Datei
        local root = current

        -- Suche nach oben bis .obsidian/ gefunden wird
        while root ~= '' and root ~= '/' and root ~= 'C:\\' do
          if vim.fn.isdirectory(root .. '/.obsidian') == 1 or vim.fn.isdirectory(root .. '\\.obsidian') == 1 then
            return root
          end
          -- Ein Verzeichnis nach oben
          root = vim.fn.fnamemodify(root, ':h')
        end

        -- Fallback: Aktuelles Verzeichnis wenn kein Vault gefunden
        return current
      end

      return {
        -- Standard-Einstellungen für alle Dateitypen
        default = {
          -- Dynamischer Pfad: Vault-Root/attachments/
          -- Findet automatisch den Obsidian Vault-Root via .obsidian/ Marker
          dir_path = function()
            return find_vault_root() .. '/attachments'
          end,

          -- Absoluter Pfad für dir_path (wir berechnen ihn selbst)
          relative_to_current_file = false,

          -- Relativer Pfad im Link (Obsidian-kompatibel)
          use_absolute_path = false,

          -- Dateiname mit Timestamp: Pasted-20250116-143052.png
          file_name = 'Pasted-%Y%m%d-%H%M%S',

          -- PNG Format (Standard für Screenshots)
          extension = 'png',

          -- Keine Bestätigung - direkt einfügen
          prompt_for_file_name = false,

          -- Drag & Drop aktivieren
          drag_and_drop = {
            enabled = true,
            insert_mode = true,
          },
        },

        -- Markdown-spezifische Einstellungen (Obsidian Wiki-Link Format)
        filetypes = {
          markdown = {
            -- Wiki-Link Format für Obsidian: ![[Pasted-20250116-143052.png]]
            -- $FILE_NAME = nur Dateiname (ohne Pfad), Obsidian findet es im Vault
            template = '![[$FILE_NAME]]',
            url_encode_path = false,
          },
        },
      }
    end,
    keys = {
      -- <leader>oi - Image aus Clipboard einfügen
      { '<leader>oi', '<cmd>PasteImage<cr>', desc = '[O]bsidian [I]mage paste' },
    },
  },

  -- Toggleterm - Terminal that toggles
  {
    'akinsho/toggleterm.nvim',
    version = '*',
    opts = {
      size = 20, -- Height of terminal when horizontal
      open_mapping = [[<C-_>]], -- Toggle with Ctrl+/ (C-_ is how terminals see Ctrl+/)
      direction = 'horizontal', -- Open at bottom
      shade_terminals = true,
      shading_factor = 2,
      start_in_insert = true, -- Start in insert mode
      persist_size = true,
      close_on_exit = true, -- Close terminal when process exits
    },
  },

  -- vim-dadbod - Database client for Neovim (MSSQL, PostgreSQL, MySQL, etc.)
  -- Standard keybindings (in DBUI panel): o=open, R=refresh, d=delete, S=execute, W=save
  {
    'kristijanhusak/vim-dadbod-ui',
    dependencies = {
      { 'tpope/vim-dadbod', lazy = true },
      { 'kristijanhusak/vim-dadbod-completion', ft = { 'sql', 'mysql', 'plsql' }, lazy = true },
    },
    cmd = { 'DBUI', 'DBUIToggle', 'DBUIAddConnection', 'DBUIFindBuffer' },
    keys = {
      {
        '<leader>db',
        function()
          -- Setze nur lokale Connections (DCSRE only)
          if vim.g.db_connections_local then
            vim.g.dbs = vim.g.db_connections_local
          end
          vim.cmd('DBUIToggle')
        end,
        desc = '[D]ata[B]ase UI (Local only)',
      },
      {
        '<leader>dR',
        function()
          -- WARNUNG: Remote Database!
          vim.notify('⚠️  WARNUNG: Du bist auf DEVELOPER Database!', vim.log.levels.WARN)

          -- Setze Remote Connections (DCSRE + Remote)
          if vim.g.db_connections_remote then
            vim.g.dbs = vim.g.db_connections_remote
          else
            vim.notify('Remote Database nicht konfiguriert! (DB_SERVER, DB_USER, DB_PASSWORD fehlen)', vim.log.levels.ERROR)
            return
          end

          -- Schließe DBUI falls offen, dann neu öffnen mit Remote
          vim.cmd('silent! DBUIClose')
          vim.defer_fn(function()
            vim.cmd('DBUI')
          end, 100)
        end,
        desc = '[D]atabase [R]emote (⚠️ WARNING: DEVELOPER DB!)',
      },
      {
        '<leader>dw',
        function()
          local current = vim.g.db_ui_winwidth or 50
          vim.g.db_ui_winwidth = current == 50 and 150 or 50
          for _, win in ipairs(vim.api.nvim_list_wins()) do
            local buf = vim.api.nvim_win_get_buf(win)
            if vim.bo[buf].filetype == 'dbui' then
              vim.api.nvim_win_set_width(win, vim.g.db_ui_winwidth)
              vim.notify('DBUI width: ' .. vim.g.db_ui_winwidth, vim.log.levels.INFO)
              return
            end
          end
        end,
        desc = '[D]atabase [W]idth toggle (50/150)',
      },
    },
    init = function()
      vim.g.db_ui_use_nerd_fonts = 1
      vim.g.db_ui_show_database_icon = 1
      vim.g.db_ui_winwidth = 50

      -- Lese Environment Variables aus PowerShell Profile
      local db_server = vim.env.DB_SERVER
      local db_user = vim.env.DB_USER
      local db_password = vim.env.DB_PASSWORD

      -- Datenbank-Namen
      local db_dev = vim.env.DB_DEV
      local db_qs = vim.env.DB_QS
      local db_keycloak_dev = vim.env.DB_KEYCLOAK_DEV
      local db_keycloak_qs = vim.env.DB_KEYCLOAK_QS

      -- Erstelle LOKALE Connection Liste (nur DCSRE)
      local connections_local = {
        { name = 'DCSRE', url = 'sqlserver://dcsp:dcsp@localhost:5433;database=dcsp;trustServerCertificate=true' },
      }

      -- Erstelle REMOTE Connection Liste (DCSRE + 4 Remote DBs)
      local connections_with_remote = {
        { name = 'DCSRE', url = 'sqlserver://dcsp:dcsp@localhost:5433;database=dcsp;trustServerCertificate=true' },
      }

      -- Erstelle Remote Connections wenn Environment Variables gesetzt sind
      if db_server and db_user and db_password then
        -- Entferne Instance Name (\AP071), behalte nur server,port
        -- server\instance,port → server,port (weil Named Pipes nicht funktioniert, nur TCP/IP Port!)
        local sqlcmd_server = db_server:gsub('\\[^,]+', '')  -- Entferne \AP071

        -- Füge DEV Datenbank hinzu
        if db_dev then
          table.insert(connections_with_remote, {
            name = 'Remote_DEV',
            url = string.format('sqlserver://%s:%s@%s;database=%s;trustServerCertificate=true', db_user, db_password, sqlcmd_server, db_dev),
          })
        end

        -- Füge QS Datenbank hinzu
        if db_qs then
          table.insert(connections_with_remote, {
            name = 'Remote_QS',
            url = string.format('sqlserver://%s:%s@%s;database=%s;trustServerCertificate=true', db_user, db_password, sqlcmd_server, db_qs),
          })
        end

        -- Füge Keycloak DEV Datenbank hinzu
        if db_keycloak_dev then
          table.insert(connections_with_remote, {
            name = 'Remote_Keycloak_DEV',
            url = string.format('sqlserver://%s:%s@%s;database=%s;trustServerCertificate=true', db_user, db_password, sqlcmd_server, db_keycloak_dev),
          })
        end

        -- Füge Keycloak QS Datenbank hinzu
        if db_keycloak_qs then
          table.insert(connections_with_remote, {
            name = 'Remote_Keycloak_QS',
            url = string.format('sqlserver://%s:%s@%s;database=%s;trustServerCertificate=true', db_user, db_password, sqlcmd_server, db_keycloak_qs),
          })
        end

        -- Speichere Remote Connections global für Keybindings
        vim.g.db_connections_remote = connections_with_remote
      end

      -- IMMER lokale Connections speichern (auch ohne Remote Env-Vars)
      vim.g.db_connections_local = connections_local

      -- Standard: Nur DCSRE (sicher)
      vim.g.dbs = connections_local
    end,
  },

  -- Neotest - Modern test runner for Neovim
  {
    'nvim-neotest/neotest',
    dependencies = {
      'nvim-neotest/nvim-nio',
      'nvim-lua/plenary.nvim',
      'antoinemadec/FixCursorHold.nvim',
      'nvim-treesitter/nvim-treesitter',
      -- Test adapters
      'nvim-neotest/neotest-jest', -- For Frontend (Jest/Angular)
      'Issafalcon/neotest-dotnet', -- For Backend (C#/.NET)
    },
    keys = {
      { '<leader>tn', function() require('neotest').run.run() end, desc = '[T]est [N]earest' },
      { '<leader>tf', function() require('neotest').run.run(vim.fn.expand('%')) end, desc = '[T]est [F]ile' },
      { '<leader>ts', function() require('neotest').run.stop() end, desc = '[T]est [S]top' },
      { '<leader>to', function() require('neotest').output.open({ enter = true }) end, desc = '[T]est [O]utput' },
      { '<leader>tO', function() require('neotest').output_panel.toggle() end, desc = '[T]est [O]utput Panel' },
      { '<leader>tt', function() require('neotest').summary.toggle() end, desc = '[T]est [T]oggle Summary' },
      { '[t', function() require('neotest').jump.prev({ status = 'failed' }) end, desc = 'Jump to previous failed test' },
      { ']t', function() require('neotest').jump.next({ status = 'failed' }) end, desc = 'Jump to next failed test' },
    },
    config = function()
      require('neotest').setup({
        adapters = {
          -- C#/.NET adapter - Simple configuration for WSL2 with Docker Desktop
          require('neotest-dotnet')({
            discovery_root = 'project',
            dotnet_additional_args = {
              "--logger", "console;verbosity=detailed",
            },
            custom_attributes = {
              xunit = { "Fact", "Theory" },
              nunit = { "Test" },
              mstest = { "TestMethod" }
            },
          }),
          -- Jest adapter for Frontend
          require('neotest-jest')({
            jestCommand = 'npm test --',
            env = { CI = true },
            cwd = function(path)
              return vim.fn.getcwd()
            end,
          }),
        },
        status = {
          virtual_text = true,
          signs = true,
        },
        output = {
          enabled = true,
          open_on_run = false,
        },
        quickfix = {
          enabled = false,
        },
      })
    end,
  },

  -- undotree - Visualize undo history as a tree
  {
    'mbbill/undotree',
    keys = {
      { '<leader>u', '<cmd>UndotreeToggle<cr>', desc = '[U]ndo Tree' },
    },
  },

  -- neo-tree - File explorer sidebar
  {
    'nvim-neo-tree/neo-tree.nvim',
    branch = 'v3.x',
    dependencies = {
      'nvim-lua/plenary.nvim',
      'nvim-tree/nvim-web-devicons',
      'MunifTanjim/nui.nvim',
    },
    cmd = 'Neotree',
    keys = {
      { '<leader>e', '<cmd>Neotree reveal<cr>', desc = '[E]xplorer Reveal (show current file)' },
      { '<leader>E', '<cmd>Neotree toggle<cr>', desc = '[E]xplorer Toggle (on/off)' },
      {
        '<leader>et',
        function()
          vim.g.neotree_test_filter_active = not vim.g.neotree_test_filter_active
          local patterns = vim.g.neotree_test_filter_active
            and { '*Test*', '*test*', '*Tests*', '*cypress*', '*e2e*' }
            or {}
          require('neo-tree').setup({
            filesystem = { filtered_items = { hide_by_pattern = patterns } },
          })
          require('neo-tree.sources.manager').refresh('filesystem')
          vim.notify(
            vim.g.neotree_test_filter_active and 'Test-Ordner ausgeblendet (nur View, nichts geloescht)'
              or 'Test-Ordner wieder sichtbar',
            vim.log.levels.INFO,
            { title = 'Explorer' }
          )
        end,
        desc = '[E]xplorer [T]oggle Test-Folders (Cypress/e2e/*Test* ein-/ausblenden)',
      },
    },
    config = function()
      -- Enable relative line numbers in neo-tree window
      vim.api.nvim_create_autocmd('FileType', {
        pattern = 'neo-tree',
        callback = function()
          vim.wo.number = true
          vim.wo.relativenumber = true
        end,
      })

      require('neo-tree').setup({
        filesystem = {
          follow_current_file = {
            enabled = true, -- Auto-reveal current file
          },
          hijack_netrw_behavior = 'open_current', -- Replace netrw
        },
        window = {
          position = 'left',
          width = 30,
        },
        default_component_configs = {
          icon = {
            folder_closed = "▶",
            folder_open = "▼",
            folder_empty = "▷",
            default = "*",
            highlight = "NeoTreeFileIcon"
          },
          git_status = {
            symbols = {
              added     = "+",
              modified  = "M",
              deleted   = "D",
              renamed   = "R",
              untracked = "?",
              ignored   = "!",
              unstaged  = "U",
              staged    = "S",
              conflict  = "C",
            }
          },
        },
        use_default_mappings = true,
      })
    end,
  },

  -- aerial.nvim - Code outline sidebar (shows classes, methods, etc.)
  {
    'stevearc/aerial.nvim',
    dependencies = {
      'nvim-treesitter/nvim-treesitter',
      'nvim-tree/nvim-web-devicons',
    },
    keys = {
      { '<leader>a', '<cmd>AerialToggle<cr>', desc = '[A]erial Toggle (Code Structure)' },
    },
    opts = {
      layout = {
        default_direction = 'right',
        min_width = 30,
      },
      on_attach = function(bufnr)
        -- Jump forwards/backwards with '{' and '}'
        vim.keymap.set('n', '{', '<cmd>AerialPrev<CR>', { buffer = bufnr })
        vim.keymap.set('n', '}', '<cmd>AerialNext<CR>', { buffer = bufnr })
      end,
    },
  },

  -- twilight.nvim - Dims inactive portions of code
  {
    'folke/twilight.nvim',
    opts = {
      dimming = {
        alpha = 0.25, -- Amount of dimming (higher = more dim)
      },
    },
  },

  -- zen-mode.nvim - Distraction-free coding (centers code, hides UI)
  {
    'folke/zen-mode.nvim',
    keys = {
      { '<leader>z', '<cmd>ZenMode<cr>', desc = '[Z]en Mode Toggle' },
      {
        '<leader>zc',
        function()
          if vim.b.center_scan_active then
            vim.wo.scrolloff = vim.b.center_scan_saved_scrolloff or 0
            vim.wo.cursorline = vim.b.center_scan_saved_cursorline or false
            vim.b.center_scan_active = false
            vim.notify('Center-Scan: AUS', vim.log.levels.INFO, { title = 'Zen' })
          else
            vim.b.center_scan_saved_scrolloff = vim.wo.scrolloff
            vim.b.center_scan_saved_cursorline = vim.wo.cursorline
            vim.wo.scrolloff = 999
            vim.wo.cursorline = true
            vim.b.center_scan_active = true
            vim.notify(
              'Center-Scan: AN — j/k bewegt den Text durch, Cursor+markierte Zeile bleiben mittig',
              vim.log.levels.INFO,
              { title = 'Zen' }
            )
          end
        end,
        desc = '[Z]en [C]enter-Scan (Cursor mittig fixiert, Zeile highlighted, Text scrollt beim j/k)',
      },
    },
    opts = {
      window = {
        width = 120, -- Width of zen window
        options = {
          number = false, -- Hide line numbers
          relativenumber = false,
          signcolumn = 'no', -- Hide sign column
          list = false, -- Hide whitespace chars
        },
      },
      plugins = {
        twilight = { enabled = true }, -- Enable twilight dimming
      },
    },
  },

  -- neoscroll.nvim - Animiertes (eased) Scrollen statt hartem "Teleport" bei
  -- Sprung-Befehlen. Wichtig: das ist kein echtes Pixel-Smooth-Scrolling (das
  -- kann ein Terminal-UI grundsaetzlich nicht, Text ist Zeichen-Raster) --
  -- einzelne j/k-Presses waren schon vorher atomar/instant. Was hier smooth
  -- wird: Mehrzeilen-Spruenge (Ctrl-D/U/F/B, zz/zt/zb, gg/G) UND Mausrad.
  {
    'karb94/neoscroll.nvim',
    event = 'VeryLazy',
    config = function()
      local neoscroll = require('neoscroll')
      neoscroll.setup({
        mappings = { '<C-u>', '<C-d>', '<C-b>', '<C-f>', '<C-y>', '<C-e>', 'zt', 'zz', 'zb' },
        hide_cursor = true,
        stop_eof = true,
        respect_scrolloff = false,
        cursor_scrolls_alone = true,
        duration_multiplier = 0.85, -- etwas straffer: gleiche Frame-Anzahl, weniger Gesamtzeit -> hoehere gefuehlte fps
        easing = 'sine', -- natuerlicherer Ease-in/out statt quadratic (weniger "ruckartiger" Start/Stop)
        performance_mode = false, -- RTX 2080 Ti + 144Hz -> Performance ist kein Thema
      })

      -- Mausrad ebenfalls animieren (neoscroll deckt das nicht automatisch ab)
      local mouse_opts = { duration = 100, easing = 'sine', info = false }
      vim.keymap.set('n', '<ScrollWheelUp>', function() neoscroll.scroll(-3, mouse_opts) end)
      vim.keymap.set('n', '<ScrollWheelDown>', function() neoscroll.scroll(3, mouse_opts) end)
    end,
  },

  -- nvim-notify - Beautiful notifications with animations
  {
    'rcarriga/nvim-notify',
    config = function()
      local notify = require('notify')
      notify.setup({
        stages = 'fade_in_slide_out', -- Animation style
        timeout = 3000, -- Display time (ms)
        background_colour = '#000000',
        top_down = false, -- false = unten-rechts (statt Default oben-rechts)
        icons = {
          ERROR = '',
          WARN = '',
          INFO = '',
          DEBUG = '',
          TRACE = '✎',
        },
      })
      -- Set as default notify
      vim.notify = notify
    end,
  },

  -- nvim-dap - Debug Adapter Protocol for Neovim
  {
    'mfussenegger/nvim-dap',
    dependencies = {
      -- UI for nvim-dap
      'rcarriga/nvim-dap-ui',
      'nvim-neotest/nvim-nio', -- Required by dap-ui
      -- Virtual text support (shows variable values inline)
      'theHamsta/nvim-dap-virtual-text',
    },
    keys = {
      -- Execution
      {
        '<leader>xc',
        function()
          local dap = require('dap')
          -- If already debugging, just continue
          if dap.session() then
            dap.continue()
            return
          end
          -- If not in a .cs file (e.g. in DAP UI panel), show cs config picker
          if vim.bo.filetype ~= 'cs' and dap.configurations.cs then
            vim.ui.select(dap.configurations.cs, {
              prompt = 'Select debug configuration:',
              format_item = function(cfg) return cfg.name end,
            }, function(cfg)
              if cfg then dap.run(cfg) end
            end)
          else
            dap.continue()
          end
        end,
        desc = 'Debug: [C]ontinue',
      },
      { '<leader>xr', function() require('dap').restart() end, desc = 'Debug: [R]estart' },
      { '<leader>xq', function() require('dap').terminate() end, desc = 'Debug: [Q]uit/Terminate' },
      -- Stepping
      { '<leader>xi', function() require('dap').step_into() end, desc = 'Debug: Step [I]nto' },
      { '<leader>xo', function() require('dap').step_out() end, desc = 'Debug: Step [O]ut' },
      { '<leader>xj', function() require('dap').step_over() end, desc = 'Debug: Step Over/[J]ump' },
      -- Breakpoints
      { '<leader>xt', function() require('dap').toggle_breakpoint() end, desc = 'Debug: [T]oggle Breakpoint' },
      { '<leader>xC', function() require('dap').set_breakpoint(vim.fn.input('Breakpoint condition: ')) end, desc = 'Debug: [C]onditional Breakpoint' },
      -- UI
      { '<leader>xw', function() require('dapui').toggle() end, desc = 'Debug: [W]indow Toggle (DAP UI)' },
      { '<leader>xe', function() require('dapui').eval() end, desc = 'Debug: [E]val', mode = { 'n', 'v' } },
      { '<leader>xh', function() require('dap.ui.widgets').hover() end, desc = 'Debug: [H]over' },
    },
    config = function()
      local dap = require('dap')
      local dapui = require('dapui')

      -- Setup DAP UI
      dapui.setup({
        layouts = {
          {
            elements = {
              { id = 'scopes', size = 0.25 },
              { id = 'breakpoints', size = 0.25 },
              { id = 'stacks', size = 0.25 },
              { id = 'watches', size = 0.25 },
            },
            size = 40,
            position = 'left',
          },
          {
            elements = {
              { id = 'repl', size = 0.5 },
              { id = 'console', size = 0.5 },
            },
            size = 10,
            position = 'bottom',
          },
        },
      })

      -- Setup virtual text
      require('nvim-dap-virtual-text').setup({})

      -- Auto-open/close DAP UI
      dap.listeners.after.event_initialized['dapui_config'] = function()
        dapui.open()
      end
      dap.listeners.before.event_terminated['dapui_config'] = function()
        dapui.close()
      end
      dap.listeners.before.event_exited['dapui_config'] = function()
        dapui.close()
      end

      -- netcoredbg adapter for C#/.NET (use Mason-installed path)
      local netcoredbg_path = vim.fn.stdpath('data') .. '/mason/packages/netcoredbg/netcoredbg/netcoredbg'
      if vim.fn.has('win32') == 1 then
        netcoredbg_path = netcoredbg_path .. '.exe'
      end
      dap.adapters.coreclr = {
        type = 'executable',
        command = netcoredbg_path,
        args = { '--interpreter=vscode' },
      }

      -- Debug configurations for C#/.NET
      -- Workflow: 1) Start server with <leader>rbw  2) Attach debugger with <leader>xc
      --
      -- Auto-Detect findet WebHost-PID in 2 Stufen:
      --   1. Native .exe Prozess by Name (am häufigsten — `dotnet run` baut eine
      --      VDEK.DCSP.WebHost.exe als Child-Prozess die direkt die Assembly hostet)
      --   2. Falls nicht da: WMI-Fallback ueber CommandLine in dotnet.exe-Prozessen
      --      (z.B. `dotnet watch` Setups oder reines `dotnet exec`)
      -- Funktioniert beim DCSRE-Workflow `<leader>rbw` zuverlaessig, weil dotnet
      -- run im Bauen die VDEK.DCSP.WebHost.exe erzeugt und ausfuehrt.
      local function find_webhost_pid()
        local marker = (vim.g.project_name == 'CENCOCD') and 'CenCoCo.Core.API' or 'VDEK.DCSP.WebHost'
        local ps_cmd =
          'powershell.exe -NoProfile -Command "' ..
          '$p = Get-Process -Name \'' .. marker .. '\' -EA SilentlyContinue | Select-Object -First 1 -ExpandProperty Id; ' ..
          'if (-not $p) { $p = (Get-CimInstance Win32_Process -Filter \\"Name=\'dotnet.exe\'\\" | ' ..
          'Where-Object { $_.CommandLine -like \'*' .. marker .. '*\' } | ' ..
          'Select-Object -First 1 -ExpandProperty ProcessId) }; ' ..
          '$p"'
        local out = vim.fn.system(ps_cmd):gsub('%s+', '')
        return tonumber(out), marker
      end

      dap.configurations.cs = {
        {
          type = 'coreclr',
          name = 'Attach - WebHost (auto-detect by assembly)',
          request = 'attach',
          processId = function()
            local pid, marker = find_webhost_pid()
            if pid then
              vim.notify(string.format('[DAP] Auto-attach an dotnet PID %d (CommandLine match: %s)', pid, marker), vim.log.levels.INFO)
              return pid
            end
            vim.notify(string.format('[DAP] Keine dotnet.exe mit %s in CommandLine - laeuft <leader>rbw? Fallback zu Picker.', marker), vim.log.levels.WARN)
            return require('dap.utils').pick_process({ filter = 'dotnet' })
          end,
        },
        {
          type = 'coreclr',
          name = 'Attach - Pick Process',
          request = 'attach',
          processId = require('dap.utils').pick_process,
        },
      }

      -- Signs for breakpoints
      vim.fn.sign_define('DapBreakpoint', { text = '🔴', texthl = 'DiagnosticError', linehl = '', numhl = '' })
      vim.fn.sign_define('DapBreakpointCondition', { text = '🟡', texthl = 'DiagnosticWarn', linehl = '', numhl = '' })
      vim.fn.sign_define('DapStopped', { text = '▶️', texthl = 'DiagnosticInfo', linehl = 'CursorLine', numhl = '' })
    end,
  },

  -- SonarLint Connected Mode: dieselben Issues wie im SonarQube-Server-Dashboard, live in Neovim
  -- Voraussetzung: $env:SONARQUBE_TOKEN / $env:SONARQUBE_URL im PowerShell-Profil (siehe $PROFILE)
  -- LSP-Server via `:MasonInstall sonarlint-language-server` (auch ueber mason-tool-installer.ensure_installed)
  {
    'https://gitlab.com/schrieveslaach/sonarlint.nvim',
    ft = 'cs',
    dependencies = { 'neovim/nvim-lspconfig', 'mason-org/mason.nvim' },
    config = function()
      -- connectionId "itsg" ist frei gewaehlt, muss nur mit der connections-Tabelle unten uebereinstimmen
      local connection_id = 'itsg'
      -- Projekt-Key aus dem SonarQube-Server je Projekt (vim.g.project_name aus shared/project.lua)
      local sonar_project_keys = {
        DCSRE = 'DCSRE_Backend',
      }

      -- Java-Pfad NICHT ueber PATH: der Mason-Wrapper 'sonarlint-language-server' ruft blind
      -- 'java' auf und stirbt still ("'java' is not recognized"), wenn Neovim aus einer Shell
      -- ohne Java im PATH gestartet wurde. Darum absoluter Pfad, dynamisch gesucht.
      local function find_java()
        local from_path = vim.fn.exepath('java')
        if from_path ~= '' then return from_path end
        local candidates = vim.fn.glob('C:/Program Files/Eclipse Adoptium/*/bin/java.exe', false, true)
        if #candidates > 0 then return candidates[1] end
        candidates = vim.fn.glob('C:/Program Files/Microsoft/jdk*/bin/java.exe', false, true)
        if #candidates > 0 then return candidates[1] end
        return nil
      end

      local java_bin = find_java()
      if not java_bin then
        vim.notify('[SonarLint] Kein java gefunden (PATH + Eclipse Adoptium + Microsoft JDK geprueft) - SonarLint deaktiviert', vim.log.levels.WARN)
        return
      end

      local mason_pkg = vim.fn.stdpath('data') .. '/mason/packages/sonarlint-language-server/extension'
      local mason_analyzers = vim.fn.stdpath('data') .. '/mason/share/sonarlint-analyzers'

      require('sonarlint').setup({
        server = {
          cmd = {
            java_bin,
            '-jar',
            mason_pkg .. '/server/sonarlint-ls.jar',
            '-stdio',
            '-analyzers',
            -- C#-Architektur-Eigenheit: NICHT sonarcsharp.jar direkt laden!
            -- sonarlintomnisharp.jar ist das Bruecken-Plugin, das die gebundelte
            -- OmniSharp-Instanz startet; sonarcsharp.jar (die Regeln) wird ihm
            -- ueber init_options.csharpOssPath zugefuettert.
            mason_analyzers .. '/sonarlintomnisharp.jar',
          },
          -- Neovim schickt sonst filetype='cs' als LSP-languageId; VSCode-basierte Server
          -- (SonarLint eingeschlossen) erwarten 'csharp' und ignorieren 'cs' sonst stillschweigend
          get_language_id = function(_bufnr, filetype)
            if filetype == 'cs' then
              return 'csharp'
            end
            return filetype
          end,
          settings = {
            sonarlint = {
              -- Debug-Schalter: Server-eigene Logs kommen als window/logMessage (INFO/DEBUG).
              -- Sichtbar nur wenn vim.lsp.set_log_level('debug') gesetzt ist -> <leader>sQd
              output = { showVerboseLogs = true },
              -- Explizit: ohne das analysiert der Server ggf. gar nicht
              automaticAnalysis = true,
              connectedMode = {
                connections = {
                  sonarqube = {
                    {
                      connectionId = connection_id,
                      serverUrl = vim.env.SONARQUBE_URL,
                      disableNotifications = false,
                    },
                  },
                },
              },
            },
          },
          init_options = {
            omnisharpDirectory = mason_pkg .. '/omnisharp',
            csharpOssPath = mason_analyzers .. '/sonarcsharp.jar',
            csharpEnterprisePath = mason_analyzers .. '/csharpenterprise.jar',
          },
          before_init = function(_params, config)
            local project_key = sonar_project_keys[vim.g.project_name]
            if not project_key then
              vim.notify('[SonarLint] Kein Projekt-Key fuer ' .. tostring(vim.g.project_name) .. ' hinterlegt - Connected Mode inaktiv', vim.log.levels.WARN)
              return
            end
            config.settings.sonarlint.connectedMode.project = {
              connectionId = connection_id,
              projectKey = project_key,
            }
          end,
        },
        connected = {
          get_credentials = function(_client_id, _url)
            return vim.env.SONARQUBE_TOKEN
          end,
        },
        -- root_dir explizit setzen: sonst faellt find_root_dir() bei Buffern ohne Dateinamen
        -- auf dirname('.git') = "." zurueck und legt einen zweiten, kaputten Client an,
        -- der dann echte Buffer abgreift (im Status sichtbar als: root=.)
        root_dir = vim.g.project_root_windows or vim.fn.getcwd(),
        filetypes = { 'cs' },
      })

      -- === SonarQube Debug-Werkzeuge (schrittweise Diagnose) ===
      -- Schritt 1: Debug-Logging an + SonarLint-Client neu starten
      vim.keymap.set('n', '<leader>sQd', function()
        vim.lsp.set_log_level('debug')
        local stopped = 0
        for _, c in ipairs(vim.lsp.get_clients({ name = 'sonarlint.nvim' })) do
          c:stop(true)
          stopped = stopped + 1
        end
        -- interne root_dir->client-Tabelle leeren, sonst startet das Plugin nicht neu
        local sl = package.loaded['sonarlint']
        if sl then sl._client_id_by_root_dir = {} end
        vim.notify(string.format('[SonarQube] Debug-Log AN, %d Client(s) gestoppt.\nJetzt :e! auf die .cs-Datei -> dann <leader>sQl', stopped), vim.log.levels.INFO)
      end, { desc = '[S]onar[Q]ube [d]ebug an (Log=debug + Client-Restart)' })

      -- Schritt 2: Nur die SonarLint-Zeilen aus dem LSP-Log in einem Scratch-Buffer
      vim.keymap.set('n', '<leader>sQl', function()
        local log = vim.lsp.get_log_path()
        if vim.fn.filereadable(log) == 0 then
          vim.notify('LSP-Log nicht gefunden: ' .. log, vim.log.levels.ERROR)
          return
        end
        local all = vim.fn.readfile(log)
        local hits = {}
        for i = math.max(1, #all - 20000), #all do
          local line = all[i]
          if line and (line:lower():find('sonar', 1, true)) then
            table.insert(hits, line)
          end
        end
        if #hits == 0 then
          vim.notify('Keine SonarLint-Zeilen im Log.\nErst <leader>sQd, dann Datei neu oeffnen (:e!), 1-2 Min warten.', vim.log.levels.WARN)
          return
        end
        vim.cmd('new')
        vim.bo.bufhidden = 'wipe'
        vim.bo.filetype = 'log'
        vim.api.nvim_buf_set_lines(0, 0, -1, false, hits)
        vim.bo.modifiable = false
        vim.keymap.set('n', 'q', '<cmd>close<cr>', { buffer = 0, nowait = true })
        vim.cmd('normal! G')
        vim.notify(string.format('[SonarQube] %d Log-Zeilen (q = schliessen)', #hits), vim.log.levels.INFO)
      end, { desc = '[S]onar[Q]ube [l]og anzeigen (nur Sonar-Zeilen)' })

      -- Schritt 3: Status — welche Clients laufen, wer haengt am Buffer, wieviele Diagnostics je Quelle
      vim.keymap.set('n', '<leader>sQs', function()
        local out = {}
        table.insert(out, '=== SonarQube / OmniSharp Status ===')
        table.insert(out, 'Buffer: ' .. vim.api.nvim_buf_get_name(0))
        table.insert(out, 'Filetype: ' .. vim.bo.filetype)
        table.insert(out, '')
        table.insert(out, '--- Alle LSP-Clients ---')
        for _, c in ipairs(vim.lsp.get_clients()) do
          local bufs = {}
          for b, _ in pairs(c.attached_buffers or {}) do table.insert(bufs, b) end
          table.insert(out, string.format('  %s (id=%d) root=%s buffers=[%s]', c.name, c.id, tostring(c.config.root_dir), table.concat(bufs, ',')))
        end
        table.insert(out, '')
        table.insert(out, '--- Diagnostics dieses Buffers nach Quelle ---')
        local by_source = {}
        for _, d in ipairs(vim.diagnostic.get(0)) do
          local s = tostring(d.source)
          by_source[s] = (by_source[s] or 0) + 1
        end
        if vim.tbl_isempty(by_source) then
          table.insert(out, '  (keine)')
        else
          for s, n in pairs(by_source) do
            table.insert(out, string.format('  %s: %d', s, n))
          end
        end
        table.insert(out, '')
        table.insert(out, '--- Umgebung ---')
        table.insert(out, '  SONARQUBE_URL: ' .. tostring(vim.env.SONARQUBE_URL))
        table.insert(out, '  SONARQUBE_TOKEN gesetzt: ' .. tostring(vim.env.SONARQUBE_TOKEN ~= nil and vim.env.SONARQUBE_TOKEN ~= ''))
        table.insert(out, '  LSP-Log-Level: siehe :checkhealth vim.lsp')
        table.insert(out, '  Log-Pfad: ' .. vim.lsp.get_log_path())

        vim.cmd('new')
        vim.bo.bufhidden = 'wipe'
        vim.api.nvim_buf_set_lines(0, 0, -1, false, out)
        vim.bo.modifiable = false
        vim.keymap.set('n', 'q', '<cmd>close<cr>', { buffer = 0, nowait = true })
      end, { desc = '[S]onar[Q]ube [s]tatus (Clients + Diagnostics je Quelle)' })
    end,
  },

  -- NOTE: Plugins can also be added by using a table,
  -- with the first argument being the link and the following
  -- keys can be used to configure plugin behavior/loading/etc.
  --
  -- Use `opts = {}` to automatically pass options to a plugin's `setup()` function, forcing the plugin to be loaded.
  --

  -- Alternatively, use `config = function() ... end` for full control over the configuration.
  -- If you prefer to call `setup` explicitly, use:
  --    {
  --        'lewis6991/gitsigns.nvim',
  --        config = function()
  --            require('gitsigns').setup({
  --                -- Your gitsigns configuration here
  --            })
  --        end,
  --    }
  --
  -- Here is a more advanced example where we pass configuration
  -- options to `gitsigns.nvim`.
  --
  -- See `:help gitsigns` to understand what the configuration keys do
  { -- Adds git related signs to the gutter, as well as utilities for managing changes
    'lewis6991/gitsigns.nvim',
    -- WORKAROUND (2026-08-25) fuer gitsigns-Bug bei change_base auf CRLF-Repos:
    -- Repo:file_info() liefert fuer eine fremde Revision (ls-tree-Pfad) KEINE
    -- eol-Info -- i_crlf/w_crlf bleiben nil. get_show_text() haengt dem Basistext
    -- dann kein \r an, buf_lines() dem Buffertext (fileformat=dos) aber schon:
    -- jede Zeile unterscheidet sich um ein CR, gitsigns markiert die GANZE Datei
    -- als geaendert (gemessen an DCSRE: -1,245 +1,348 statt 24 Hunks). Betrifft
    -- jedes Repo mit autocrlf / `* text=auto`, also <leader>hB und <leader>qh.
    -- Upstream (5be654f, 2026-08-11) hat den Bug ebenfalls -- Update hilft nicht.
    -- Fix an der Wurzel statt am Symptom: eol-Info fuer Tree-Revisionen aus
    -- ls-files nachziehen. Ueberlebt so auch refresh(), das file_info() jedes Mal
    -- neu ruft und die Felder sonst wieder auf nil setzt.
    config = function(_, opts)
      local Repo = require('gitsigns.git.repo')
      local orig_file_info = Repo.file_info
      Repo.file_info = function(self, file, revision)
        local info, err = orig_file_info(self, file, revision)
        if info and revision and info.i_crlf == nil then
          local wt = self:ls_files(file)
          if wt then info.i_crlf, info.w_crlf = wt.i_crlf, wt.w_crlf end
        end
        return info, err
      end
      require('gitsigns').setup(opts)
    end,
    opts = {
      signs = {
        add = { text = '+' },
        change = { text = '»' },
        delete = { text = '_' },
        topdelete = { text = '‾' },
        changedelete = { text = '»' },
      },
      on_attach = function(bufnr)
        local gitsigns = require('gitsigns')

        local function map(mode, l, r, opts)
          opts = opts or {}
          opts.buffer = bufnr
          vim.keymap.set(mode, l, r, opts)
        end

        -- Navigation: ]c/[c (Vim-Standard fuer change in diff-mode) UND ]h/[h (Alias = hunk)
        local function next_hunk()
          if vim.wo.diff then
            vim.cmd.normal({ ']c', bang = true })
          else
            gitsigns.nav_hunk('next')
          end
        end
        local function prev_hunk()
          if vim.wo.diff then
            vim.cmd.normal({ '[c', bang = true })
          else
            gitsigns.nav_hunk('prev')
          end
        end
        map('n', ']c', next_hunk, { desc = 'Next git [c]hange/hunk' })
        map('n', '[c', prev_hunk, { desc = 'Previous git [c]hange/hunk' })
        map('n', ']h', next_hunk, { desc = 'Next git [h]unk (alias for ]c)' })
        map('n', '[h', prev_hunk, { desc = 'Previous git [h]unk (alias for [c)' })

        -- ]a / [a — springt direkt zur PURE-ADD-AREA innerhalb eines Hunks.
        -- In einem Misch-Hunk (~ + +) landet ]a auf der ERSTEN Plus-Zeile,
        -- nicht auf der ersten ~-Zeile. Praktisch wenn du nur die NEUEN Zeilen
        -- ansehen willst, ohne durch die Modifies zu scrollen.
        --
        -- Berechnung: pure_add_start = hunk.added.start + min(hunk.removed.count, hunk.added.count)
        --   - reiner Add-Hunk: removed=0 → pure_add_start = added.start (normaler Hunk-Anfang)
        --   - Misch-Hunk:      pure_add_start = wo removed endet (= wo + beginnt)
        --   - reiner Delete:   added.count=0 → kein pure-add, hunk uebersprungen
        local function nav_add_area(direction)
          local hunks = gitsigns.get_hunks() or {}
          if #hunks == 0 then
            vim.notify('Keine Hunks in dieser Datei', vim.log.levels.INFO)
            return
          end
          local cur = vim.fn.line('.')
          -- pure-add Lines berechnen
          local targets = {}
          for _, h in ipairs(hunks) do
            local rc = h.removed and h.removed.count or 0
            local ac = h.added and h.added.count or 0
            if ac > 0 and h.added.start then
              local offset = math.min(rc, ac)
              table.insert(targets, h.added.start + offset)
            end
          end
          if #targets == 0 then
            vim.notify('Keine + Areas (nur Deletes?)', vim.log.levels.INFO)
            return
          end
          local target
          if direction == 'next' then
            for _, line in ipairs(targets) do
              if line > cur then target = line; break end
            end
            if not target then target = targets[1] end  -- wrap
          else
            for i = #targets, 1, -1 do
              if targets[i] < cur then target = targets[i]; break end
            end
            if not target then target = targets[#targets] end  -- wrap
          end
          vim.api.nvim_win_set_cursor(0, { target, 0 })
          vim.cmd('normal! zz')  -- centre on screen
        end
        map('n', ']a', function() nav_add_area('next') end, { desc = 'Next [a]dded-area (jumps to + start, skipping ~)' })
        map('n', '[a', function() nav_add_area('prev') end, { desc = 'Previous [a]dded-area' })

        -- Staged hunk navigation
        map('n', ']C', function()
          gitsigns.nav_hunk('next', { target = 'staged' })
        end, { desc = 'Next staged [C]hange/hunk' })

        map('n', '[C', function()
          gitsigns.nav_hunk('prev', { target = 'staged' })
        end, { desc = 'Previous staged [C]hange/hunk' })

        -- ENTFERNT 2026-08-21: ]d/[d "Super Hunk" (cross-file).
        -- Die Implementierung war toter Code: gitsigns.nav_hunk ist async.create() und
        -- wirft NIE synchron; bei "kein Hunk mehr" macht nav.lua nur nvim_echo('No hunks')
        -- und return. Das umschliessende pcall() lieferte damit IMMER ok=true, der
        -- Cross-File-Zweig lief nie. Zusaetzlich nutzte er `git diff --name-only`
        -- (nur uncommitted, ohne Base) statt der Branch-Dateien, und ueberschrieb
        -- Neovims Default ]d/[d = naechste/vorherige Diagnose.
        -- Ersatz: <leader>qh baut ALLE Hunks vs Base in die Quickfix-Liste,
        -- ]q/[q navigiert dateiuebergreifend durch (lua/shared/keybindings/git.lua).

        -- Actions
        map('n', '<leader>hs', gitsigns.stage_hunk, { desc = '[H]unk [S]tage' })
        map('n', '<leader>hr', gitsigns.reset_hunk, { desc = '[H]unk [R]eset' })
        map('v', '<leader>hs', function() gitsigns.stage_hunk { vim.fn.line('.'), vim.fn.line('v') } end, { desc = '[H]unk [S]tage (visual)' })
        map('v', '<leader>hr', function() gitsigns.reset_hunk { vim.fn.line('.'), vim.fn.line('v') } end, { desc = '[H]unk [R]eset (visual)' })
        map('n', '<leader>hS', gitsigns.stage_buffer, { desc = '[H]unk [S]tage buffer' })
        map('n', '<leader>hu', gitsigns.undo_stage_hunk, { desc = '[H]unk [U]ndo stage' })
        map('n', '<leader>hR', gitsigns.reset_buffer, { desc = '[H]unk [R]eset buffer' })
        map('n', '<leader>hp', gitsigns.preview_hunk, { desc = '[H]unk [P]review' })
        map('n', '<leader>hb', function() gitsigns.blame_line { full = true } end, { desc = '[H]unk [B]lame line' })
        map('n', '<leader>hd', gitsigns.diffthis, { desc = '[H]unk [D]iff this' })
        map('n', '<leader>hD', function() gitsigns.diffthis('~') end, { desc = '[H]unk [D]iff against ~' })

        -- <leader>hB — Toggle gitsigns Base zwischen HEAD und project-base branch.
        -- ACTIVE: gitsigns zeigt ALLE Branch-Aenderungen als Hunks im Gutter, ]c/[c
        -- (oder ]h/[h Alias) springt durch Branch-Diff-Hunks statt nur durch uncommitted.
        -- <leader>qh (Quickfix ueber alle Hunks) nutzt dieselbe Base.
        -- DEFAULT: HEAD (= klassisches uncommitted-changes Verhalten).
        map('n', '<leader>hB', function()
          if vim.g.gitsigns_branch_mode then
            gitsigns.change_base(nil, true)  -- nil = HEAD, true = global
            vim.g.gitsigns_branch_mode = false
            -- Force re-evaluate alle Buffers (sonst zeigt nur aktiver Buffer neue Hunks)
            pcall(gitsigns.refresh)
            local hcount = #(gitsigns.get_hunks() or {})
            vim.notify(
              string.format('Gitsigns Base → HEAD\nHunks in dieser Datei: %d\n]c/]h zeigt UNCOMMITTED', hcount),
              vim.log.levels.INFO, { title = 'Gitsigns Base', timeout = 4000 })
          else
            local base = vim.g.project_git_base or 'origin/develop'
            gitsigns.change_base(base, true)
            vim.g.gitsigns_branch_mode = true
            pcall(gitsigns.refresh)
            -- Liefert get_hunks() das schon den NEUEN Stand? Nach refresh ggf. async — kurz warten.
            vim.defer_fn(function()
              local hcount = #(gitsigns.get_hunks() or {})
              vim.notify(
                string.format('Gitsigns Base → %s\nHunks in dieser Datei: %d\n]c/]h zeigt BRANCH-CHANGES', base, hcount),
                vim.log.levels.INFO, { title = 'Gitsigns Base', timeout = 4000 })
            end, 300)
          end
        end, { desc = '[H]unk [B]ase toggle (HEAD <-> branch-diff)' })

        -- Yank current hunk as raw diff
        map('n', '<leader>gyH', function()
          local hunks = require('gitsigns').get_hunks()
          if not hunks or #hunks == 0 then
            vim.notify('No hunks in this file', vim.log.levels.WARN)
            return
          end
          local line = vim.fn.line('.')
          for _, hunk in ipairs(hunks) do
            -- Check if current line is within this hunk
            if line >= hunk.added.start and line < hunk.added.start + math.max(hunk.added.count, 1) then
              -- Build diff text from hunk
              local diff_lines = {}
              table.insert(diff_lines, string.format('@@ -%d,%d +%d,%d @@',
                hunk.removed.start, hunk.removed.count,
                hunk.added.start, hunk.added.count))
              for _, l in ipairs(hunk.lines) do
                table.insert(diff_lines, l)
              end
              local diff = table.concat(diff_lines, '\n')
              vim.fn.setreg('+', diff)
              vim.notify('Yanked hunk (' .. #hunk.lines .. ' lines)', vim.log.levels.INFO)
              return
            end
          end
          vim.notify('Cursor not on a hunk', vim.log.levels.WARN)
        end, { desc = '[G]it [Y]ank [H]unk raw diff' })

        -- Yank hunk as readable before/after (for AI review)
        map('n', '<leader>hy', function()
          local filepath = vim.fn.expand('%')
          if filepath == '' then
            vim.notify('No file in buffer', vim.log.levels.ERROR)
            return
          end
          -- Get unstaged diff for this file
          local diff_output = vim.fn.systemlist('git diff -- ' .. vim.fn.shellescape(filepath))
          if #diff_output == 0 then
            -- Try staged diff if no unstaged
            diff_output = vim.fn.systemlist('git diff --cached -- ' .. vim.fn.shellescape(filepath))
          end
          if #diff_output == 0 then
            vim.notify('No changes in this file', vim.log.levels.WARN)
            return
          end
          -- Find hunk near cursor
          local cursor_line = vim.fn.line('.')
          local hunks = {}
          local current_hunk = nil
          local new_line = 0
          for _, line in ipairs(diff_output) do
            if line:match('^@@') then
              if current_hunk then table.insert(hunks, current_hunk) end
              local new_start = line:match('%+(%d+)')
              new_line = tonumber(new_start) or 0
              current_hunk = { header = line, before = {}, after = {}, start = new_line }
            elseif current_hunk then
              if line:match('^%-') and not line:match('^%-%-%-') then
                table.insert(current_hunk.before, line:sub(2))
              elseif line:match('^%+') and not line:match('^%+%+%+') then
                table.insert(current_hunk.after, line:sub(2))
                new_line = new_line + 1
              else
                new_line = new_line + 1
              end
            end
          end
          if current_hunk then table.insert(hunks, current_hunk) end
          -- Find closest hunk to cursor
          local best = hunks[1]
          for _, h in ipairs(hunks) do
            if cursor_line >= h.start then best = h end
          end
          if not best then
            vim.notify('No hunk found', vim.log.levels.WARN)
            return
          end
          -- Format as readable before/after
          local parts = {
            'File: ' .. filepath,
            '',
            '--- VORHER ---',
            #best.before > 0 and table.concat(best.before, '\n') or '(leer)',
            '',
            '+++ NACHHER +++',
            #best.after > 0 and table.concat(best.after, '\n') or '(leer)',
          }
          local result = table.concat(parts, '\n')
          vim.fn.setreg('+', result)
          vim.notify('Hunk kopiert: ' .. #best.before .. ' → ' .. #best.after .. ' Zeilen', vim.log.levels.INFO)
        end, { desc = '[H]unk [Y]ank (before/after für AI)' })

        -- Toggles
        map('n', '<leader>tb', gitsigns.toggle_current_line_blame, { desc = '[T]oggle git [B]lame' })
        map('n', '<leader>td', gitsigns.toggle_deleted, { desc = '[T]oggle git [D]eleted' })
      end,
    },
  },

  -- NOTE: Plugins can also be configured to run Lua code when they are loaded.
  --
  -- This is often very useful to both group configuration, as well as handle
  -- lazy loading plugins that don't need to be loaded immediately at startup.
  --
  -- For example, in the following configuration, we use:
  --  event = 'VimEnter'
  --
  -- which loads which-key before all the UI elements are loaded. Events can be
  -- normal autocommands events (`:help autocmd-events`).
  --
  -- Then, because we use the `opts` key (recommended), the configuration runs
  -- after the plugin has been loaded as `require(MODULE).setup(opts)`.

  { -- Useful plugin to show you pending keybinds.
    'folke/which-key.nvim',
    event = 'VimEnter', -- Sets the loading event to 'VimEnter'
    opts = {
      -- delay between pressing a key and opening which-key (milliseconds)
      -- this setting is independent of vim.o.timeoutlen
      delay = 0,
      icons = {
        -- set icon mappings to true if you have a Nerd Font
        mappings = vim.g.have_nerd_font,
        -- If you are using a Nerd Font: set icons.keys to an empty table which will use the
        -- default which-key.nvim defined Nerd Font icons, otherwise define a string table
        keys = vim.g.have_nerd_font and {} or {
          Up = '<Up> ',
          Down = '<Down> ',
          Left = '<Left> ',
          Right = '<Right> ',
          C = '<C-…> ',
          M = '<M-…> ',
          D = '<D-…> ',
          S = '<S-…> ',
          CR = '<CR> ',
          Esc = '<Esc> ',
          ScrollWheelDown = '<ScrollWheelDown> ',
          ScrollWheelUp = '<ScrollWheelUp> ',
          NL = '<NL> ',
          BS = '<BS> ',
          Space = '<Space> ',
          Tab = '<Tab> ',
          F1 = '<F1>',
          F2 = '<F2>',
          F3 = '<F3>',
          F4 = '<F4>',
          F5 = '<F5>',
          F6 = '<F6>',
          F7 = '<F7>',
          F8 = '<F8>',
          F9 = '<F9>',
          F10 = '<F10>',
          F11 = '<F11>',
          F12 = '<F12>',
        },
      },

      -- Document existing key chains
      spec = {
        { '<leader>s', group = '[S]earch' },
        { '<leader>t', group = '[T]oggle' },
        { '<leader>h', group = 'Git [H]unk', mode = { 'n', 'v' } },
      },
    },
  },

  -- NOTE: Plugins can specify dependencies.
  --
  -- The dependencies are proper plugin specifications as well - anything
  -- you do for a plugin at the top level, you can do for a dependency.
  --
  -- Use the `dependencies` key to specify the dependencies of a particular plugin

  { -- Fuzzy Finder (files, lsp, etc)
    'nvim-telescope/telescope.nvim',
    event = 'VimEnter',
    dependencies = {
      'nvim-lua/plenary.nvim',
      { -- If encountering errors, see telescope-fzf-native README for installation instructions
        'nvim-telescope/telescope-fzf-native.nvim',

        -- `build` is used to run some command when the plugin is installed/updated.
        -- This is only run then, not every time Neovim starts up.
        build = 'make',

        -- `cond` is a condition used to determine whether this plugin should be
        -- installed and loaded.
        cond = function()
          return vim.fn.executable 'make' == 1
        end,
      },
      { 'nvim-telescope/telescope-ui-select.nvim' },

      -- Useful for getting pretty icons, but requires a Nerd Font.
      { 'nvim-tree/nvim-web-devicons', enabled = vim.g.have_nerd_font },
    },
    config = function()
      -- Telescope is a fuzzy finder that comes with a lot of different things that
      -- it can fuzzy find! It's more than just a "file finder", it can search
      -- many different aspects of Neovim, your workspace, LSP, and more!
      --
      -- The easiest way to use Telescope, is to start by doing something like:
      --  :Telescope help_tags
      --
      -- After running this command, a window will open up and you're able to
      -- type in the prompt window. You'll see a list of `help_tags` options and
      -- a corresponding preview of the help.
      --
      -- Two important keymaps to use while in Telescope are:
      --  - Insert mode: <c-/>
      --  - Normal mode: ?
      --
      -- This opens a window that shows you all of the keymaps for the current
      -- Telescope picker. This is really useful to discover what Telescope can
      -- do as well as how to actually do it!

      -- [[ Configure Telescope ]]
      -- See `:help telescope` and `:help telescope.setup()`
      require('telescope').setup {
        -- You can put your default mappings / updates / etc. in here
        --  All the info you're looking for is in `:help telescope.setup()`
        --
        defaults = {
          layout_config = {
            horizontal = {
              width = 0.9,          -- 90% der Bildschirmbreite
              height = 0.85,        -- 85% der Bildschirmhöhe
              preview_width = 0.55, -- Preview nimmt 55% der Breite
            },
          },
          -- Respect .gitignore files (don't show ignored files)
          file_ignore_patterns = { 'node_modules', '.git/' },
          vimgrep_arguments = {
            'rg',
            '--color=never',
            '--no-heading',
            '--with-filename',
            '--line-number',
            '--column',
            '--smart-case',
            '--hidden',         -- Search hidden files
            '--glob', '!.git/', -- But not .git directory
          },
        },
        pickers = {
          find_files = {
            -- Use 'git ls-files' when in a git repo (respects .gitignore)
            find_command = { 'rg', '--files', '--hidden', '--glob', '!.git/' },
            hidden = true,  -- Show hidden files (but still respects .gitignore)
          },
          live_grep = {
            additional_args = function()
              return { '--hidden' }
            end,
          },
        },
        extensions = {
          ['ui-select'] = {
            require('telescope.themes').get_ivy({
              layout_config = {
                width = 0.99,  -- 99% der Breite
                height = 0.95, -- 95% der Höhe
              },
            }),
          },
        },
      }

      -- Enable Telescope extensions if they are installed
      pcall(require('telescope').load_extension, 'fzf')
      pcall(require('telescope').load_extension, 'ui-select')

      -- See `:help telescope.builtin`
      local builtin = require 'telescope.builtin'

      -- Liest Neo-trees aktuell gesetzten Root (per "." in <leader>e narrowed) --
      -- damit <leader>sf/sg/sx im gleichen Scope suchen, den man sich im Explorer
      -- gerade eingestellt hat, statt immer im ganzen Projekt-Root.
      -- Fallback: normales cwd, falls Neo-tree noch nie geoeffnet/kein State.
      local function search_root()
        local ok, manager = pcall(require, 'neo-tree.sources.manager')
        if not ok then return vim.fn.getcwd() end
        local state = manager.get_state('filesystem')
        return (state and state.path) or vim.fn.getcwd()
      end

      vim.keymap.set('n', '<leader>sh', builtin.help_tags, { desc = '[S]earch [H]elp' })
      vim.keymap.set('n', '<leader>sk', builtin.keymaps, { desc = '[S]earch [K]eymaps' })
      vim.keymap.set('n', '<leader>sf', function()
        builtin.find_files({ cwd = search_root() })
      end, { desc = '[S]earch [F]iles (respects .gitignore, Scope = Neo-tree Root)' })
      vim.keymap.set('n', '<leader>sF', function()
        builtin.find_files({ no_ignore = true, hidden = true, cwd = search_root() })
      end, { desc = '[S]earch [F]iles (ALL, including ignored, Scope = Neo-tree Root)' })
      vim.keymap.set('n', '<leader>sc', builtin.colorscheme, { desc = '[S]earch [C]olorscheme (live preview)' })
      vim.keymap.set('n', '<leader>ss', builtin.builtin, { desc = '[S]earch [S]elect Telescope' })
      vim.keymap.set('n', '<leader>sw', function()
        builtin.grep_string({ cwd = search_root() })
      end, { desc = '[S]earch current [W]ord (Scope = Neo-tree Root)' })
      vim.keymap.set('n', '<leader>sg', function()
        builtin.live_grep({ cwd = search_root() })
      end, { desc = '[S]earch by [G]rep (respects .gitignore, Scope = Neo-tree Root)' })
      vim.keymap.set('n', '<leader>sG', function()
        builtin.live_grep({ additional_args = { '--no-ignore', '--hidden' }, cwd = search_root() })
      end, { desc = '[S]earch by [G]rep (ALL, including ignored, Scope = Neo-tree Root)' })
      -- Grep ohne Cypress/E2E-Test-Rauschen (z.B. Suche nach Feld-/Domain-Begriffen
      -- wie "Postleitzahl" im Produktionscode, ohne dass jeder .feature/.ts-Testtreffer mitkommt)
      vim.keymap.set('n', '<leader>sx', function()
        builtin.live_grep({
          cwd = search_root(),
          additional_args = function()
            return { '--hidden', '--iglob', '!**/cypress/**', '--iglob', '!**/e2e/**' }
          end,
        })
      end, { desc = '[S]earch by grep, e[X]cluding Cypress/E2E tests' })
      vim.keymap.set('n', '<leader>sd', builtin.diagnostics, { desc = '[S]earch [D]iagnostics' })
      -- <leader>sD — Search [D]irty/Diff: Dateien geandert in diesem Branch vs Base
      -- Base-Branch via vim.g.project_git_base (origin/develop bei DCSRE, origin/main bei CenCoCo)
      -- Drei-Punkt-Diff (base...HEAD) = symmetric = nur Commits seit Branch-Punkt
      vim.keymap.set('n', '<leader>sD', function()
        local base = vim.g.project_git_base or 'origin/develop'
        local cwd = vim.fn.getcwd()
        -- Branch-Diff: zeigt Dateien die durch Commits in diesem Branch geaendert wurden
        local diff_cmd = string.format('git -C "%s" diff --name-only %s...HEAD 2>&1', cwd, base)
        local raw = vim.fn.systemlist(diff_cmd)
        if vim.v.shell_error ~= 0 then
          vim.notify('git diff fehlgeschlagen:\n' .. table.concat(raw, '\n'), vim.log.levels.ERROR, { title = 'sD Branch-Diff', timeout = 10000 })
          return
        end

        -- Filtere: nicht-leer + existing files (geloschte ueberspringen)
        local files = {}
        local skipped_deleted = 0
        for _, line in ipairs(raw) do
          local rel = (line or ''):gsub('%s+$', '')
          if rel ~= '' then
            local abs = cwd .. '/' .. rel
            if vim.fn.filereadable(abs) == 1 then
              table.insert(files, rel)
            else
              skipped_deleted = skipped_deleted + 1
            end
          end
        end

        if #files == 0 then
          local extra = (skipped_deleted > 0) and string.format(' (%d geloeschte uebersprungen)', skipped_deleted) or ''
          vim.notify('Keine geaenderten Dateien vs ' .. base .. extra, vim.log.levels.INFO)
          return
        end

        table.sort(files)

        local pickers = require('telescope.pickers')
        local finders = require('telescope.finders')
        local conf = require('telescope.config').values
        local actions = require('telescope.actions')
        local action_state = require('telescope.actions.state')

        local title = string.format(
          'Branch-Diff vs %s — %d Dateien%s | Tab=multi, Enter=oeffnen',
          base, #files,
          (skipped_deleted > 0) and (' (+' .. skipped_deleted .. ' geloescht)') or ''
        )

        pickers.new({}, {
          prompt_title = title,
          finder = finders.new_table({
            results = files,
            entry_maker = function(entry)
              return {
                value = entry,
                display = entry,
                ordinal = entry,
                text = entry, -- Quickfix/Export-Spalte relativ statt ~\Documents\...-Vollpfad
                path = cwd .. '/' .. entry,
                filename = cwd .. '/' .. entry,
              }
            end,
          }),
          sorter = conf.generic_sorter({}),
          previewer = conf.file_previewer({}),
          attach_mappings = function(prompt_bufnr, _map)
            actions.select_default:replace(function()
              local picker = action_state.get_current_picker(prompt_bufnr)
              local multi = picker:get_multi_selection()
              actions.close(prompt_bufnr)
              if #multi > 0 then
                for _, sel in ipairs(multi) do
                  vim.cmd('edit ' .. vim.fn.fnameescape(sel.path))
                end
              else
                local single = action_state.get_selected_entry()
                if single then vim.cmd('edit ' .. vim.fn.fnameescape(single.path)) end
              end
            end)
            return true
          end,
        }):find()
      end, { desc = '[S]earch [D]irty/Diff (Branch-changed files vs base)' })

      -- === Dirty-Werkzeuge mit Profil-System (sDp / sDo / sDb / sDS) ===
      -- Profil = ein Quell-Bereich des Repos (Sources/Backend, Sources/Frontend, Sources/Database, ...).
      -- Auto-Discovery aus der Repo-Struktur statt Hardcode. Das aktive Profil steht in
      -- vim.g.dirty_profile (Default 'Backend' — bisheriges Verhalten bleibt) und wird per
      -- <leader>sDp umgeschaltet. sDo (Buffer-Lader) und sDb/sDS (Diagnostics) folgen ihm.

      -- Endungen, die als Code zaehlen. Profil-uebergreifend: jedes Profil bekommt automatisch
      -- nur was es enthaelt (Backend -> .cs, Frontend -> .ts/.html/.scss, Database -> .sql).
      local DIRTY_CODE_EXTS = { 'cs', 'ts', 'js', 'html', 'scss', 'css', 'sql', 'ps1', 'sh', 'yaml', 'yml' }

      local function is_code_file(rel)
        for _, ext in ipairs(DIRTY_CODE_EXTS) do
          if rel:match('%.' .. ext .. '$') then return true end
        end
        return false
      end

      local function dirty_profile()
        return vim.g.dirty_profile or 'Backend'
      end

      local function in_profile(rel, profile)
        local p = vim.pesc(profile)
        return rel:match('/' .. p .. '/') ~= nil or rel:match('^' .. p .. '/') ~= nil
      end

      -- Rohe Liste der Branch-geaenderten Dateien (vs Base), ungefiltert.
      local function git_dirty_raw()
        local base = vim.g.project_git_base or 'origin/develop'
        local cwd = vim.fn.getcwd()
        local raw = vim.fn.systemlist(string.format('git -C "%s" diff --name-only %s...HEAD 2>&1', cwd, base))
        if vim.v.shell_error ~= 0 then
          vim.notify('git diff fehlgeschlagen:\n' .. table.concat(raw, '\n'), vim.log.levels.ERROR, { title = 'Dirty-Dateien', timeout = 10000 })
          return nil, base, cwd
        end
        return raw, base, cwd
      end

      -- Branch-geaenderte Code-Dateien des Profils als absolute Pfade.
      local function get_dirty_files(profile)
        profile = profile or dirty_profile()
        local raw, base, cwd = git_dirty_raw()
        if not raw then return nil, base end
        local files = {}
        for _, line in ipairs(raw) do
          local rel = (line or ''):gsub('%s+$', '')
          if rel ~= '' and is_code_file(rel) and in_profile(rel, profile) then
            local abs = vim.fn.fnamemodify(cwd .. '/' .. rel, ':p')
            if vim.fn.filereadable(abs) == 1 then
              table.insert(files, abs)
            end
          end
        end
        return files, base
      end

      -- <leader>sDp — [P]rofil waehlen: bestimmt den Scope fuer sDo/sDb/sDS.
      -- Zeigt alle Quell-Bereiche des Repos mit der Anzahl ihrer geaenderten Dateien;
      -- das aktive Profil ist mit * markiert.
      vim.keymap.set('n', '<leader>sDp', function()
        local raw, base, cwd = git_dirty_raw()
        if not raw then return end

        local roots = vim.fn.glob(cwd .. '/Sources/*', false, true)
        if #roots == 0 then roots = vim.fn.glob(cwd .. '/*', false, true) end
        local counts, order = {}, {}
        for _, dir in ipairs(roots) do
          if vim.fn.isdirectory(dir) == 1 then
            local name = vim.fn.fnamemodify(dir, ':t')
            if not counts[name] then
              counts[name] = 0
              table.insert(order, name)
            end
          end
        end
        if #order == 0 then
          vim.notify('Keine Quell-Bereiche gefunden (weder Sources/* noch Top-Level)', vim.log.levels.WARN)
          return
        end

        for _, line in ipairs(raw) do
          local rel = (line or ''):gsub('%s+$', '')
          if rel ~= '' and is_code_file(rel) then
            for _, name in ipairs(order) do
              if in_profile(rel, name) then
                counts[name] = counts[name] + 1
                break
              end
            end
          end
        end

        table.sort(order, function(a, b)
          if counts[a] ~= counts[b] then return counts[a] > counts[b] end
          return a < b
        end)

        local active = dirty_profile()
        local entries = {}
        for _, name in ipairs(order) do
          table.insert(entries, {
            name = name,
            display = string.format('%s %-14s %4d geaenderte Datei(en)',
              (name == active) and '*' or ' ', name, counts[name]),
          })
        end

        local pickers = require('telescope.pickers')
        local finders = require('telescope.finders')
        local conf = require('telescope.config').values
        local actions = require('telescope.actions')
        local action_state = require('telescope.actions.state')

        pickers.new({}, {
          prompt_title = string.format('Dirty-Profil waehlen (aktiv: %s | Base: %s)', active, base),
          finder = finders.new_table({
            results = entries,
            entry_maker = function(e)
              return { value = e.name, display = e.display, ordinal = e.name }
            end,
          }),
          sorter = conf.generic_sorter({}),
          attach_mappings = function(prompt_bufnr)
            actions.select_default:replace(function()
              local sel = action_state.get_selected_entry()
              actions.close(prompt_bufnr)
              if sel then
                vim.g.dirty_profile = sel.value
                vim.notify(string.format('Dirty-Profil: %s\nsDo/sDb/sDS arbeiten jetzt in diesem Bereich.', sel.value), vim.log.levels.INFO)
              end
            end)
            return true
          end,
        }):find()
      end, { desc = '[S]earch [D]irty: [P]rofil waehlen (Backend/Frontend/... fuer sDo/sDb/sDS)' })

      -- <leader>sDo — [O]pen all dirty: laedt alle Branch-geaenderten Dateien des aktiven Profils
      -- als echte Buffer. Noetig, weil SonarLint/eslint nur offene Buffer analysieren und
      -- badd/bufload keine FileType-Events feuern (kein LSP-Attach).
      vim.keymap.set('n', '<leader>sDo', function()
        local profile = dirty_profile()
        local files, base = get_dirty_files(profile)
        if not files then return end
        if #files == 0 then
          vim.notify(string.format('Keine geaenderten %s-Dateien vs %s\n(anderes Profil? <leader>sDp)', profile, base), vim.log.levels.INFO)
          return
        end
        local original = vim.api.nvim_get_current_buf()
        local opened = 0
        for _, abs in ipairs(files) do
          local ok = pcall(vim.cmd, 'silent edit ' .. vim.fn.fnameescape(abs))
          if ok then opened = opened + 1 end
        end
        if vim.api.nvim_buf_is_valid(original) and vim.api.nvim_buf_get_name(original) ~= '' then
          vim.api.nvim_set_current_buf(original)
        end
        vim.notify(string.format(
          '%d/%d %s-Dateien geladen (vs %s).\nLSP analysiert jetzt - je nach Menge 1-3 Min warten, dann sDb/sDS',
          opened, #files, profile, base), vim.log.levels.INFO, { timeout = 8000 })
      end, { desc = '[S]earch [D]irty: [O]pen all (Dateien des aktiven Profils in Buffer laden)' })

      -- Gemeinsame Basis fuer sDb/sDS: Diagnostics NUR in Branch-geaenderten Dateien des aktiven Profils.
      -- opts.source_filter: nil = alle Quellen | Funktion(source) -> bool (z.B. nur SonarQube)
      -- opts.severity: nil = alle Stufen | vim.diagnostic.severity.X (exakte Stufe, wie sW/sE)
      -- opts.label: Anzeige-Name im Picker-Titel und in Notify-Meldungen
      local function dirty_diagnostics(opts)
        opts = opts or {}
        local profile = dirty_profile()
        local files, base = get_dirty_files(profile)
        if not files then return end

        if #files == 0 then
          vim.notify(string.format('Keine geaenderten %s-Dateien vs %s\n(anderes Profil? <leader>sDp)', profile, base), vim.log.levels.INFO)
          return
        end

        -- Windows: Pfade case-insensitiv, Lua-Vergleich aber case-sensitiv (Buffer melden mal c:\, mal C:\) -> lowercase-Schluessel
        local function norm_path(p)
          return vim.fn.fnamemodify(p, ':p'):lower():gsub('/', '\\')
        end
        local dirty_set = {}
        for _, abs in ipairs(files) do
          dirty_set[norm_path(abs)] = true
        end

        local severities = vim.diagnostic.severity
        local items, seen = {}, {}
        for _, d in ipairs(vim.diagnostic.get(nil)) do
          local name = vim.api.nvim_buf_get_name(d.bufnr)
          local source_ok = not opts.source_filter or opts.source_filter(tostring(d.source or ''))
          local sev_ok = not opts.severity or d.severity == opts.severity
          if dirty_set[norm_path(name)] and source_ok and sev_ok then
            -- Dedup: OmniSharp published manche Regeln (z.B. IDE0005) aus zwei Analyse-Paessen
            -- doppelt. Schluessel = Datei + Zeile + Spalte + Code + Text.
            local key = table.concat({ norm_path(name), d.lnum, d.col, tostring(d.code), d.message }, '|')
            if not seen[key] then
              seen[key] = true
              table.insert(items, {
                bufnr = d.bufnr,
                -- Relativer Pfad (vs cwd): haelt Telescope-Suche/Anzeige frei vom C:\...\laneA-Prefix
                filename = vim.fn.fnamemodify(name, ':.'),
                lnum = d.lnum + 1,
                col = d.col + 1,
                text = vim.trim(d.message:gsub('[\n]', '')) .. (d.code and (' [' .. tostring(d.code) .. ']') or ''),
                type = severities[d.severity] or severities[1],
              })
            end
          end
        end

        if vim.tbl_isempty(items) then
          vim.notify(string.format('Keine %s-Diagnostics in geaenderten %s-Dateien (evtl. noch nicht analysiert - <leader>sDo zum Laden)', opts.label or '', profile), vim.log.levels.INFO)
          return
        end

        local pickers = require('telescope.pickers')
        local finders = require('telescope.finders')
        local conf = require('telescope.config').values
        local make_entry = require('telescope.make_entry')

        pickers.new({}, {
          prompt_title = string.format('%s in geaenderten %s-Dateien vs %s (%d)', opts.label or 'Diagnostics', profile, base, #items),
          finder = finders.new_table({
            results = items,
            entry_maker = make_entry.gen_from_diagnostics({}),
          }),
          previewer = conf.qflist_previewer({}),
          sorter = conf.generic_sorter({}),
        }):find()
      end

      -- <leader>sDb — ALLE Diagnostics (jede Quelle, jede Severity) im aktiven Profil
      vim.keymap.set('n', '<leader>sDb', function()
        dirty_diagnostics({ label = 'Diagnostics (alle Quellen)' })
      end, { desc = '[S]earch [D]iagnostics: dirty files im aktiven Profil (alle Quellen)' })

      -- <leader>sDw — nur [W]arnings im aktiven Profil (das dirty-Pendant zu <leader>sW)
      -- Exakte Stufe, nicht "WARN und schlimmer": Errors haben mit sDe ihren eigenen Kanal,
      -- damit man die zwei Listen getrennt abarbeiten kann statt sie zu vermischen.
      vim.keymap.set('n', '<leader>sDw', function()
        dirty_diagnostics({ label = 'Warnings', severity = vim.diagnostic.severity.WARN })
      end, { desc = '[S]earch [D]iagnostics: dirty files, [W]arnings only' })

      -- <leader>sDe — nur [E]rrors im aktiven Profil (das dirty-Pendant zu <leader>sE)
      vim.keymap.set('n', '<leader>sDe', function()
        dirty_diagnostics({ label = 'Errors', severity = vim.diagnostic.severity.ERROR })
      end, { desc = '[S]earch [D]iagnostics: dirty files, [E]rrors only' })

      -- <leader>sDi — nur [I]nfo im aktiven Profil
      vim.keymap.set('n', '<leader>sDi', function()
        dirty_diagnostics({ label = 'Info', severity = vim.diagnostic.severity.INFO })
      end, { desc = '[S]earch [D]iagnostics: dirty files, [I]nfo only' })

      -- <leader>sDh — nur [H]ints im aktiven Profil (IDE*/RCS*-Massenware; meist dotnet-format-Stoff)
      vim.keymap.set('n', '<leader>sDh', function()
        dirty_diagnostics({ label = 'Hints', severity = vim.diagnostic.severity.HINT })
      end, { desc = '[S]earch [D]iagnostics: dirty files, [H]ints only' })

      -- <leader>sDS — NUR SonarQube-Diagnostics (Error/Warning/Info/Hint) im aktiven Profil
      vim.keymap.set('n', '<leader>sDS', function()
        dirty_diagnostics({
          label = 'SonarQube',
          source_filter = function(source)
            return source:lower():find('sonar', 1, true) ~= nil
          end,
        })
      end, { desc = '[S]earch [D]iagnostics: dirty files, [S]onarQube only' })

      -- <leader>sDr — [R]un Harvest: sonar_harvest.ps1 headless im HINTERGRUND.
      --
      -- WARUM zusaetzlich zu sDo/sDb: sDo laedt die Dirty-Files als Buffer in DIESE
      -- Session und du wartest 1-3 Min zu, bis OmniSharp+SonarLint durch sind. Das
      -- Harvest-Skript startet ein EIGENES headless-Neovim, das denselben Weg geht,
      -- aber in einem anderen Prozess -- deine Session bleibt benutzbar.
      -- Ergebnis landet in der Quickfix-Liste, also mit ]q/[q dateiuebergreifend
      -- navigierbar (gleiche Mechanik wie <leader>qh).
      --
      -- Das Skript ist selbstversorgend (laedt $PROFILE fuer SONARQUBE_TOKEN/_URL
      -- selbst nach) und faellt LAUT aus: Exit 2 = sonarlint nie attached,
      -- Exit 3 = Env fehlt. Beides wird hier als Fehler gemeldet, nie als "0 Findings".
      vim.keymap.set('n', '<leader>sDr', function()
        local root = vim.g.project_root_windows
        if not root then
          vim.notify('Kein Projekt erkannt (vim.g.project_root_windows fehlt)', vim.log.levels.ERROR)
          return
        end

        local script = root .. '\\.claude\\scripts\\sonar_harvest.ps1'
        if vim.fn.filereadable(script) == 0 then
          vim.notify('Harvest-Skript nicht gefunden:\n' .. script ..
            '\n(Redeploy aus OmniCommand noetig?)', vim.log.levels.ERROR,
            { title = 'Sonar-Harvest', timeout = 10000 })
          return
        end

        local profile = vim.g.dirty_profile or 'Backend'
        local base = vim.g.project_git_base or 'origin/develop'
        local out = vim.fn.stdpath('cache') .. '/sonar_harvest_findings.txt'
        local out_win = out:gsub('/', '\\')

        local started = vim.uv.now()
        vim.notify(string.format(
          'Harvest gestartet (Profil %s vs %s).\nLaeuft im Hintergrund -- du kannst normal weiterarbeiten.\nDauer typisch 3-4 Min (Solution-Kaltstart).',
          profile, base), vim.log.levels.INFO, { title = 'Sonar-Harvest', timeout = 6000 })

        local stdout_lines = {}
        vim.fn.jobstart({
          'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
          '-File', script,
          '-RepoRoot', root,
          '-OutFile', out_win,
          '-Base', base,
          '-ScopeFilter', profile,
        }, {
          on_stdout = function(_, data)
            for _, l in ipairs(data or {}) do
              if l ~= '' then table.insert(stdout_lines, (l:gsub('\r', ''))) end
            end
          end,
          on_exit = vim.schedule_wrap(function(_, code)
            local elapsed = math.floor((vim.uv.now() - started) / 1000)
            local tail = table.concat(stdout_lines, '\n')

            if code ~= 0 then
              vim.notify(string.format('Harvest FEHLGESCHLAGEN (exit %d, nach %ds):\n%s',
                code, elapsed, tail), vim.log.levels.ERROR,
                { title = 'Sonar-Harvest', timeout = 15000 })
              return
            end

            if vim.fn.filereadable(out) == 0 then
              vim.notify('Harvest meldete Erfolg, aber keine Ergebnis-Datei:\n' .. out,
                vim.log.levels.ERROR, { title = 'Sonar-Harvest', timeout = 10000 })
              return
            end

            -- Format: {relpfad}|{zeile}|{spalte}|{severity}|{source}|{code}|{message}
            -- Erste Zeile ist der '# HARVEST ...'-Header.
            local qf, sonar_count = {}, 0
            for _, line in ipairs(vim.fn.readfile(out)) do
              if line ~= '' and not line:match('^#') then
                local f, l, c, sev, src, dcode, msg =
                  line:match('^(.-)|(%d+)|(%d+)|(.-)|(.-)|(.-)|(.*)$')
                if f then
                  if src:lower():find('sonar', 1, true) then sonar_count = sonar_count + 1 end
                  -- bufadd() VOR setqflist(): sonst bleibt bufnr=0 und :cc springt
                  -- den Eintrag nicht an (derselbe Grund wie in git.lua build_branch_hunk_qflist).
                  local abs = root .. '\\' .. f:gsub('/', '\\')
                  table.insert(qf, {
                    bufnr = vim.fn.bufadd(abs),
                    lnum = tonumber(l),
                    col = tonumber(c),
                    type = sev:upper():sub(1, 1),
                    text = string.format('[%s:%s] %s', src, dcode, msg),
                  })
                end
              end
            end

            if #qf == 0 then
              vim.notify(string.format('Harvest sauber: 0 Findings im Profil %s (nach %ds)',
                profile, elapsed), vim.log.levels.INFO, { title = 'Sonar-Harvest' })
              return
            end

            vim.fn.setqflist({}, ' ', {
              title = string.format('Sonar-Harvest %s vs %s', profile, base),
              items = qf,
            })
            vim.notify(string.format(
              '%d Findings (%d davon SonarQube) nach %ds.\n]q / [q = durchnavigieren (dateiuebergreifend)\n:copen = Liste anzeigen',
              #qf, sonar_count, elapsed), vim.log.levels.INFO,
              { title = 'Sonar-Harvest fertig', timeout = 12000 })
          end),
        })
      end, { desc = '[S]earch [D]irty: Harvest headless im Hintergrund ([R]un) -> Quickfix' })

      vim.keymap.set('n', '<leader>sW', function()
        builtin.diagnostics({ severity = vim.diagnostic.severity.WARN })
      end, { desc = '[S]earch [W]arnings only' })
      vim.keymap.set('n', '<leader>sE', function()
        builtin.diagnostics({ severity = vim.diagnostic.severity.ERROR })
      end, { desc = '[S]earch [E]rrors only' })
      vim.keymap.set('n', '<leader>sis', function()
        builtin.diagnostics({ severity = vim.diagnostic.severity.INFO })
      end, { desc = '[S]earch [I]ssues [S]uggestion (Info)' })
      vim.keymap.set('n', '<leader>sih', function()
        builtin.diagnostics({ severity = vim.diagnostic.severity.HINT })
      end, { desc = '[S]earch [I]ssues [H]int' })
      -- Search Issues in current file only (all severities)
      vim.keymap.set('n', '<leader>si', function()
        builtin.diagnostics({ bufnr = 0 })
      end, { desc = '[S]earch [I]ssues (current file only)' })
      vim.keymap.set('n', '<leader>sr', builtin.resume, { desc = '[S]earch [R]esume' })
      vim.keymap.set('n', '<leader>s.', builtin.oldfiles, { desc = '[S]earch Recent Files ("." for repeat)' })
      -- Buffers-Picker mit Delete-Funktion.
      -- Loeschen:  <M-d> (Alt+d, Telescope-Default, Insert-Mode) ODER dd (Normal-Mode).
      -- Tab = multi-select, dann Alt+d / dd loescht alle markierten. Picker bleibt offen.
      -- <C-d> bleibt absichtlich preview_scrolling_down (nicht ueberschrieben).
      vim.keymap.set('n', '<leader><leader>', function()
        builtin.buffers({
          sort_mru = true,
          ignore_current_buffer = false,
          attach_mappings = function(_, map)
            local actions = require('telescope.actions')
            map('n', 'dd', actions.delete_buffer)
            return true
          end,
        })
      end, { desc = '[ ] Find existing buffers (Alt+d/dd = delete)' })

      -- Slightly advanced example of overriding default behavior and theme
      vim.keymap.set('n', '<leader>/', function()
        -- You can pass additional configuration to Telescope to change the theme, layout, etc.
        builtin.current_buffer_fuzzy_find(require('telescope.themes').get_dropdown {
          winblend = 10,
          previewer = false,
        })
      end, { desc = '[/] Fuzzily search in current buffer' })

      -- It's also possible to pass additional configuration options.
      --  See `:help telescope.builtin.live_grep()` for information about particular keys
      vim.keymap.set('n', '<leader>s/', function()
        builtin.live_grep {
          grep_open_files = true,
          prompt_title = 'Live Grep in Open Files',
        }
      end, { desc = '[S]earch [/] in Open Files' })

      -- Shortcut for searching your Neovim configuration files
      vim.keymap.set('n', '<leader>sn', function()
        builtin.find_files { cwd = vim.fn.stdpath 'config' }
      end, { desc = '[S]earch [N]eovim files' })

      -- Search Terminals - Telescope picker for toggleterm terminals
      vim.keymap.set('n', '<leader>st', function()
        local pickers = require('telescope.pickers')
        local finders = require('telescope.finders')
        local conf = require('telescope.config').values
        local actions = require('telescope.actions')
        local action_state = require('telescope.actions.state')

        -- Named terminals (ID → Name)
        local terminal_names = {
          [1] = 'Default',
          [10] = 'Backend',
          [11] = 'Frontend Dev',
          [20] = 'Backend WebHost',
          [21] = 'Frontend',
          [22] = 'Docker Infra',
          [30] = 'E2E Playwright',
          [31] = 'E2E Headed',
          [32] = 'Cypress UI',
          [40] = 'Integration Tests',
        }

        -- Get all toggleterm terminals
        local terms = require('toggleterm.terminal').get_all()
        local results = {}

        for _, term in ipairs(terms) do
          local name = terminal_names[term.id] or ('Terminal #' .. term.id)
          local status = term:is_open() and '●' or '○'
          table.insert(results, {
            id = term.id,
            name = name,
            display = string.format('%s %2d: %s', status, term.id, name),
            term = term,
          })
        end

        -- Sort by ID
        table.sort(results, function(a, b) return a.id < b.id end)

        if #results == 0 then
          vim.notify('No terminals open', vim.log.levels.INFO)
          return
        end

        pickers.new({}, {
          prompt_title = 'Terminals (● open, ○ hidden)',
          finder = finders.new_table({
            results = results,
            entry_maker = function(entry)
              return {
                value = entry,
                display = entry.display,
                ordinal = entry.display,
              }
            end,
          }),
          sorter = conf.generic_sorter({}),
          attach_mappings = function(prompt_bufnr, map)
            actions.select_default:replace(function()
              actions.close(prompt_bufnr)
              local selection = action_state.get_selected_entry()
              if selection then
                selection.value.term:toggle()
              end
            end)
            -- 'd' to close/kill terminal
            map('i', '<C-d>', function()
              local selection = action_state.get_selected_entry()
              if selection then
                selection.value.term:shutdown()
                vim.notify('Terminal #' .. selection.value.id .. ' closed', vim.log.levels.INFO)
              end
            end)
            return true
          end,
        }):find()
      end, { desc = '[S]earch [T]erminals' })

      -- E2E Test Picker - Search and run Cypress feature files
      -- Multi-select with <Tab>, run with <Enter>
      vim.keymap.set('n', '<leader>ref', function()
        local pickers = require('telescope.pickers')
        local finders = require('telescope.finders')
        local conf = require('telescope.config').values
        local actions = require('telescope.actions')
        local action_state = require('telescope.actions.state')

        -- Use dynamic project root (works with worktrees!)
        local project_name = vim.g.project_name
        local is_win = vim.fn.has('win32') == 1
        local project_root = is_win and vim.g.project_root_windows or vim.g.project_root_wsl
        local cypress_path

        if project_name == 'DCSRE' then
          cypress_path = project_root .. (is_win and '\\Sources\\Tests\\Cypress' or '/Sources/Tests/Cypress')
        elseif project_name == 'CENCOCD' then
          cypress_path = project_root .. (is_win and '\\src\\Tests\\Cypress' or '/src/Tests/Cypress')
        else
          vim.notify('Unknown project - cannot find Cypress path', vim.log.levels.ERROR)
          return
        end

        -- Find all .feature files
        local feature_files = vim.fn.globpath(cypress_path .. '/e2e', '**/*.feature', false, true)

        if #feature_files == 0 then
          vim.notify('No .feature files found in: ' .. cypress_path, vim.log.levels.WARN)
          return
        end

        -- Create entries with relative paths
        local results = {}
        for _, file in ipairs(feature_files) do
          local rel_path = file:gsub(cypress_path .. '/', '')
          local display_name = rel_path:gsub('e2e/', ''):gsub('%.feature$', '')
          table.insert(results, {
            path = file,
            rel_path = rel_path,
            display = display_name,
          })
        end

        -- Sort alphabetically
        table.sort(results, function(a, b) return a.display < b.display end)

        pickers.new({}, {
          prompt_title = 'E2E Tests (' .. project_name .. ') - <Tab> multi-select, <Enter> run',
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
            actions.select_default:replace(function()
              local picker = action_state.get_current_picker(prompt_bufnr)
              local multi_selections = picker:get_multi_selection()
              actions.close(prompt_bufnr)

              -- Use multi-selection if available, otherwise single selection
              local selected = {}
              if #multi_selections > 0 then
                for _, sel in ipairs(multi_selections) do
                  table.insert(selected, sel.value.rel_path)
                end
              else
                local single = action_state.get_selected_entry()
                if single then
                  table.insert(selected, single.value.rel_path)
                end
              end

              if #selected == 0 then
                vim.notify('No tests selected', vim.log.levels.WARN)
                return
              end

              -- Build spec argument (comma-separated for multiple)
              local spec_arg = table.concat(selected, ',')

              -- Build and run cypress command (PowerShell for Windows)
              local cmd
              if is_win then
                cmd = string.format(
                  'powershell.exe -Command "Set-Location \'%s\'; npx cypress run --spec \'%s\'"',
                  cypress_path:gsub('/', '\\'),
                  spec_arg
                )
              else
                cmd = string.format(
                  'cd "%s" && npx cypress run --spec "%s"',
                  cypress_path,
                  spec_arg
                )
              end

              vim.notify('Running ' .. #selected .. ' E2E test(s)...', vim.log.levels.INFO)

              -- Open in toggleterm (terminal 30 = E2E Playwright)
              local Terminal = require('toggleterm.terminal').Terminal
              local e2e_term = Terminal:new({
                cmd = cmd,
                id = 30,
                direction = 'horizontal',
                close_on_exit = false,
                on_open = function()
                  vim.notify('E2E Tests started: ' .. table.concat(selected, ', '), vim.log.levels.INFO)
                end,
              })
              e2e_term:toggle()
            end)

            -- Headed mode with <C-h>
            map('i', '<C-h>', function()
              local picker = action_state.get_current_picker(prompt_bufnr)
              local multi_selections = picker:get_multi_selection()
              actions.close(prompt_bufnr)

              local selected = {}
              if #multi_selections > 0 then
                for _, sel in ipairs(multi_selections) do
                  table.insert(selected, sel.value.rel_path)
                end
              else
                local single = action_state.get_selected_entry()
                if single then
                  table.insert(selected, single.value.rel_path)
                end
              end

              if #selected == 0 then return end

              local spec_arg = table.concat(selected, ',')
              local cmd
              if is_win then
                cmd = string.format(
                  'powershell.exe -Command "Set-Location \'%s\'; npx cypress run --headed --spec \'%s\'"',
                  cypress_path:gsub('/', '\\'),
                  spec_arg
                )
              else
                cmd = string.format(
                  'cd "%s" && npx cypress run --headed --spec "%s"',
                  cypress_path,
                  spec_arg
                )
              end

              vim.notify('Running ' .. #selected .. ' E2E test(s) HEADED...', vim.log.levels.INFO)

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
      end, { desc = '[R]un [E]2E [F]ind (Cypress - multi-select with Tab)' })

      -- Integration Test Picker - Search and run backend integration tests
      -- Multi-select with <Tab>, run with <Enter>
      vim.keymap.set('n', '<leader>ris', function()
        local pickers = require('telescope.pickers')
        local finders = require('telescope.finders')
        local conf = require('telescope.config').values
        local actions = require('telescope.actions')
        local action_state = require('telescope.actions.state')

        -- Use dynamic project backend (works with worktrees!)
        local project_name = vim.g.project_name
        local is_win = vim.fn.has('win32') == 1
        local backend_root = is_win and vim.g.project_backend_windows or vim.g.project_backend

        if project_name ~= 'DCSRE' then
          vim.notify('Integration Tests only available for DCSRE', vim.log.levels.ERROR)
          return
        end

        if not backend_root then
          vim.notify('Backend root not found', vim.log.levels.ERROR)
          return
        end

        -- Run dotnet test --list-tests to get all test names
        vim.notify('Loading Integration Tests...', vim.log.levels.INFO)
        local cmd
        if is_win then
          cmd = string.format(
            'powershell.exe -Command "Set-Location \'%s\'; dotnet test --list-tests --no-build 2>&1 | Select-String -Pattern \'VDEK.DCSP\'"',
            backend_root:gsub('/', '\\')
          )
        else
          cmd = string.format('cd "%s" && dotnet test --list-tests --no-build 2>&1 | grep "VDEK.DCSP"', backend_root)
        end

        local output = vim.fn.system(cmd)
        local test_lines = vim.split(output, '\n', { trimempty = true })

        -- Parse test names (filter out non-test lines)
        local results = {}
        for _, line in ipairs(test_lines) do
          line = line:gsub('^%s+', '') -- trim whitespace
          if line:match('^VDEK%.DCSP%.IntegrationTests%.') then
            -- Extract display name (last part after last dot)
            local display_name = line:match('%.([^.]+)$') or line
            -- Extract category (Controllers, Providers, Services, etc.)
            local category = line:match('IntegrationTests%.([^.]+)%.')
            table.insert(results, {
              fqn = line,
              display = category and (category .. '/' .. display_name) or display_name,
              ordinal = line,
            })
          end
        end

        if #results == 0 then
          vim.notify('No Integration Tests found. Run dotnet build first?', vim.log.levels.WARN)
          return
        end

        -- Sort alphabetically
        table.sort(results, function(a, b) return a.display < b.display end)

        pickers.new({}, {
          prompt_title = 'Integration Tests (' .. #results .. ' tests) - <Tab> multi-select, <Enter> run',
          finder = finders.new_table({
            results = results,
            entry_maker = function(entry)
              return {
                value = entry,
                display = entry.display,
                ordinal = entry.ordinal,
              }
            end,
          }),
          sorter = conf.generic_sorter({}),
          attach_mappings = function(prompt_bufnr, map)
            actions.select_default:replace(function()
              local picker = action_state.get_current_picker(prompt_bufnr)
              local multi_selections = picker:get_multi_selection()
              actions.close(prompt_bufnr)

              -- Use multi-selection if available, otherwise single selection
              local selected = {}
              if #multi_selections > 0 then
                for _, sel in ipairs(multi_selections) do
                  table.insert(selected, sel.value.fqn)
                end
              else
                local single = action_state.get_selected_entry()
                if single then
                  table.insert(selected, single.value.fqn)
                end
              end

              if #selected == 0 then
                vim.notify('No tests selected', vim.log.levels.WARN)
                return
              end

              -- Build filter argument (pipe-separated for multiple)
              local filter_arg = table.concat(
                vim.tbl_map(function(fqn)
                  return 'FullyQualifiedName~' .. fqn
                end, selected),
                '|'
              )

              -- Build and run dotnet test command
              local test_cmd
              if is_win then
                test_cmd = string.format(
                  'powershell.exe -Command "Set-Location \'%s\'; dotnet test --no-build --no-restore --filter \'%s\' --verbosity detailed"',
                  backend_root:gsub('/', '\\'),
                  filter_arg
                )
              else
                test_cmd = string.format(
                  'cd "%s" && dotnet test --no-build --no-restore --filter "%s" --verbosity detailed',
                  backend_root,
                  filter_arg
                )
              end

              vim.notify('Running ' .. #selected .. ' Integration Test(s)...', vim.log.levels.INFO)

              -- Open in toggleterm (terminal 40 = Integration Tests)
              local Terminal = require('toggleterm.terminal').Terminal
              local test_term = Terminal:new({
                cmd = test_cmd,
                id = 40,
                direction = 'horizontal',
                close_on_exit = false,
                on_open = function()
                  vim.notify('Integration Tests started: ' .. #selected .. ' test(s)', vim.log.levels.INFO)
                end,
              })
              test_term:toggle()
            end)

            return true
          end,
        }):find()
      end, { desc = '[R]un [I]ntegration [S]earch (Backend - multi-select with Tab)' })
    end,
  },

  -- LSP Plugins
  {
    -- `lazydev` configures Lua LSP for your Neovim config, runtime and plugins
    -- used for completion, annotations and signatures of Neovim apis
    'folke/lazydev.nvim',
    ft = 'lua',
    opts = {
      library = {
        -- Load luvit types when the `vim.uv` word is found
        { path = '${3rd}/luv/library', words = { 'vim%.uv' } },
      },
    },
  },
  {
    -- Main LSP Configuration
    'neovim/nvim-lspconfig',
    dependencies = {
      -- Automatically install LSPs and related tools to stdpath for Neovim
      -- Mason must be loaded before its dependents so we need to set it up here.
      -- NOTE: `opts = {}` is the same as calling `require('mason').setup({})`
      { 'mason-org/mason.nvim', opts = {} },
      'mason-org/mason-lspconfig.nvim',
      'WhoIsSethDaniel/mason-tool-installer.nvim',

      -- Useful status updates for LSP.
      { 'j-hui/fidget.nvim', opts = {} },

      -- Allows extra capabilities provided by blink.cmp
      'saghen/blink.cmp',
    },
    config = function()
      -- Brief aside: **What is LSP?**
      --
      -- LSP is an initialism you've probably heard, but might not understand what it is.
      --
      -- LSP stands for Language Server Protocol. It's a protocol that helps editors
      -- and language tooling communicate in a standardized fashion.
      --
      -- In general, you have a "server" which is some tool built to understand a particular
      -- language (such as `gopls`, `lua_ls`, `rust_analyzer`, etc.). These Language Servers
      -- (sometimes called LSP servers, but that's kind of like ATM Machine) are standalone
      -- processes that communicate with some "client" - in this case, Neovim!
      --
      -- LSP provides Neovim with features like:
      --  - Go to definition
      --  - Find references
      --  - Autocompletion
      --  - Symbol Search
      --  - and more!
      --
      -- Thus, Language Servers are external tools that must be installed separately from
      -- Neovim. This is where `mason` and related plugins come into play.
      --
      -- If you're wondering about lsp vs treesitter, you can check out the wonderfully
      -- and elegantly composed help section, `:help lsp-vs-treesitter`

      --  This function gets run when an LSP attaches to a particular buffer.
      --    That is to say, every time a new file is opened that is associated with
      --    an lsp (for example, opening `main.rs` is associated with `rust_analyzer`) this
      --    function will be executed to configure the current buffer
      vim.api.nvim_create_autocmd('LspAttach', {
        group = vim.api.nvim_create_augroup('kickstart-lsp-attach', { clear = true }),
        callback = function(event)
          -- NOTE: Remember that Lua is a real programming language, and as such it is possible
          -- to define small helper and utility functions so you don't have to repeat yourself.
          --
          -- In this case, we create a function that lets us more easily define mappings specific
          -- for LSP related items. It sets the mode, buffer and description for us each time.
          local map = function(keys, func, desc, mode)
            mode = mode or 'n'
            vim.keymap.set(mode, keys, func, { buffer = event.buf, desc = 'LSP: ' .. desc })
          end

          -- Rename the variable under your cursor.
          --  Most Language Servers support renaming across files, etc.
          map('grn', vim.lsp.buf.rename, '[R]e[n]ame')

          -- Execute a code action, usually your cursor needs to be on top of an error
          -- or a suggestion from your LSP for this to activate.
          map('gra', vim.lsp.buf.code_action, '[G]oto Code [A]ction', { 'n', 'x' })

          -- Find references for the word under your cursor.
          map('grr', require('telescope.builtin').lsp_references, '[G]oto [R]eferences')

          -- Jump to the implementation of the word under your cursor.
          --  Useful when your language has ways of declaring types without an actual implementation.
          map('gri', require('telescope.builtin').lsp_implementations, '[G]oto [I]mplementation')

          -- Jump to the definition of the word under your cursor.
          --  This is where a variable was first declared, or where a function is defined, etc.
          --  To jump back, press <C-t>.
          map('grd', require('telescope.builtin').lsp_definitions, '[G]oto [D]efinition')

          -- WARN: This is not Goto Definition, this is Goto Declaration.
          --  For example, in C this would take you to the header.
          map('grD', vim.lsp.buf.declaration, '[G]oto [D]eclaration')

          -- Fuzzy find all the symbols in your current document.
          --  Symbols are things like variables, functions, types, etc.
          map('gO', require('telescope.builtin').lsp_document_symbols, 'Open Document Symbols')

          -- Fuzzy find all the symbols in your current workspace.
          --  Similar to document symbols, except searches over your entire project.
          map('gW', require('telescope.builtin').lsp_dynamic_workspace_symbols, 'Open Workspace Symbols')

          -- Jump to the type of the word under your cursor.
          --  Useful when you're not sure what type a variable is and you want to see
          --  the definition of its *type*, not where it was *defined*.
          map('grt', require('telescope.builtin').lsp_type_definitions, '[G]oto [T]ype Definition')

          -- OmniSharp-specific overrides for metadata decompilation support
          -- These override the default LSP handlers when attached to a C# file
          -- Fixes "Cursor position outside buffer" errors when navigating to framework symbols
          if vim.lsp.get_client_by_id(event.data.client_id).name == 'omnisharp' then
            map('grd', function()
              require('omnisharp_extended').lsp_definition()
            end, '[G]oto [D]efinition (OmniSharp Extended)')

            map('grr', function()
              require('omnisharp_extended').lsp_references()
            end, '[G]oto [R]eferences (OmniSharp Extended)')

            map('gri', function()
              require('omnisharp_extended').lsp_implementation()
            end, '[G]oto [I]mplementation (OmniSharp Extended)')

            map('grt', function()
              require('omnisharp_extended').lsp_type_definition()
            end, '[G]oto [T]ype Definition (OmniSharp Extended)')

            -- Auto-format C# files on save using OmniSharp
            -- Uses .editorconfig settings automatically (configured in omnisharp.json)
            vim.api.nvim_create_autocmd('BufWritePre', {
              buffer = event.buf,
              callback = function()
                vim.lsp.buf.format({ async = false })
              end,
            })
          end

          -- This function resolves a difference between neovim nightly (version 0.11) and stable (version 0.10)
          ---@param client vim.lsp.Client
          ---@param method vim.lsp.protocol.Method
          ---@param bufnr? integer some lsp support methods only in specific files
          ---@return boolean
          local function client_supports_method(client, method, bufnr)
            if vim.fn.has 'nvim-0.11' == 1 then
              return client:supports_method(method, bufnr)
            else
              return client.supports_method(method, { bufnr = bufnr })
            end
          end

          -- The following two autocommands are used to highlight references of the
          -- word under your cursor when your cursor rests there for a little while.
          --    See `:help CursorHold` for information about when this is executed
          --
          -- When you move your cursor, the highlights will be cleared (the second autocommand).
          local client = vim.lsp.get_client_by_id(event.data.client_id)
          if client and client_supports_method(client, vim.lsp.protocol.Methods.textDocument_documentHighlight, event.buf) then
            local highlight_augroup = vim.api.nvim_create_augroup('kickstart-lsp-highlight', { clear = false })
            vim.api.nvim_create_autocmd({ 'CursorHold', 'CursorHoldI' }, {
              buffer = event.buf,
              group = highlight_augroup,
              callback = vim.lsp.buf.document_highlight,
            })

            vim.api.nvim_create_autocmd({ 'CursorMoved', 'CursorMovedI' }, {
              buffer = event.buf,
              group = highlight_augroup,
              callback = vim.lsp.buf.clear_references,
            })

            vim.api.nvim_create_autocmd('LspDetach', {
              group = vim.api.nvim_create_augroup('kickstart-lsp-detach', { clear = true }),
              callback = function(event2)
                vim.lsp.buf.clear_references()
                vim.api.nvim_clear_autocmds { group = 'kickstart-lsp-highlight', buffer = event2.buf }
              end,
            })
          end

          -- The following code creates a keymap to toggle inlay hints in your
          -- code, if the language server you are using supports them
          --
          -- This may be unwanted, since they displace some of your code
          if client and client_supports_method(client, vim.lsp.protocol.Methods.textDocument_inlayHint, event.buf) then
            map('<leader>th', function()
              vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled { bufnr = event.buf })
            end, '[T]oggle Inlay [H]ints')
          end
        end,
      })

      -- Diagnostic Config
      -- See :help vim.diagnostic.Opts

      -- =======================================================================
      -- DIAGNOSTIC FILTER - Persönliche Ignore-Liste
      -- Füge hier Diagnostic-Codes hinzu die du ausblenden willst
      -- =======================================================================
      local ignored_diagnostics = {
        -- Roslyn/OmniSharp Codes zum Ignorieren:
        -- 'IDE0008',  -- Use explicit type instead of 'var'
        -- 'IDE0058',  -- Expression value is never used
        -- 'CA1707',   -- Identifiers should not contain underscores
        -- 'CA1822',   -- Mark members as static
        -- 'SA1600',   -- Elements should be documented
      }

      -- Convert to lookup table for O(1) access
      local ignored_lookup = {}
      for _, code in ipairs(ignored_diagnostics) do
        ignored_lookup[code] = true
      end

      -- Custom filter function
      local function filter_diagnostics(diagnostics)
        return vim.tbl_filter(function(d)
          if d.code and ignored_lookup[tostring(d.code)] then
            return false
          end
          return true
        end, diagnostics)
      end

      -- Override diagnostic handlers to apply filter
      local orig_signs_handler = vim.diagnostic.handlers.signs
      local orig_virtual_text_handler = vim.diagnostic.handlers.virtual_text
      local orig_underline_handler = vim.diagnostic.handlers.underline

      vim.diagnostic.handlers.signs = {
        show = function(ns, bufnr, diagnostics, opts)
          orig_signs_handler.show(ns, bufnr, filter_diagnostics(diagnostics), opts)
        end,
        hide = orig_signs_handler.hide,
      }

      vim.diagnostic.handlers.virtual_text = {
        show = function(ns, bufnr, diagnostics, opts)
          orig_virtual_text_handler.show(ns, bufnr, filter_diagnostics(diagnostics), opts)
        end,
        hide = orig_virtual_text_handler.hide,
      }

      vim.diagnostic.handlers.underline = {
        show = function(ns, bufnr, diagnostics, opts)
          orig_underline_handler.show(ns, bufnr, filter_diagnostics(diagnostics), opts)
        end,
        hide = orig_underline_handler.hide,
      }

      vim.diagnostic.config {
        severity_sort = true,
        float = { border = 'rounded', source = 'if_many' },
        underline = { severity = vim.diagnostic.severity.ERROR },
        signs = vim.g.have_nerd_font and {
          text = {
            [vim.diagnostic.severity.ERROR] = '󰅚 ',
            [vim.diagnostic.severity.WARN] = '󰀪 ',
            [vim.diagnostic.severity.INFO] = '󰋽 ',
            [vim.diagnostic.severity.HINT] = '󰌶 ',
          },
        } or {},
        virtual_text = {
          source = 'if_many',
          spacing = 2,
          format = function(diagnostic)
            local diagnostic_message = {
              [vim.diagnostic.severity.ERROR] = diagnostic.message,
              [vim.diagnostic.severity.WARN] = diagnostic.message,
              [vim.diagnostic.severity.INFO] = diagnostic.message,
              [vim.diagnostic.severity.HINT] = diagnostic.message,
            }
            return diagnostic_message[diagnostic.severity]
          end,
        },
      }

      -- LSP servers and clients are able to communicate to each other what features they support.
      --  By default, Neovim doesn't support everything that is in the LSP specification.
      --  When you add blink.cmp, luasnip, etc. Neovim now has *more* capabilities.
      --  So, we create new capabilities with blink.cmp, and then broadcast that to the servers.
      local capabilities = require('blink.cmp').get_lsp_capabilities()

      -- Enable the following language servers
      --  Feel free to add/remove any LSPs that you want here. They will automatically be installed.
      --
      --  Add any additional override configuration in the following tables. Available keys are:
      --  - cmd (table): Override the default command used to start the server
      --  - filetypes (table): Override the default list of associated filetypes for the server
      --  - capabilities (table): Override fields in capabilities. Can be used to disable certain LSP features.
      --  - settings (table): Override the default settings passed when initializing the server.
      --        For example, to see the options for `lua_ls`, you could go to: https://luals.github.io/wiki/settings/
      local servers = {
        -- clangd = {},
        -- gopls = {},
        -- pyright = {},
        -- rust_analyzer = {},
        -- ... etc. See `:help lspconfig-all` for a list of all the pre-configured LSPs
        --
        -- Some languages (like typescript) have entire language plugins that can be useful:
        --    https://github.com/pmizio/typescript-tools.nvim
        --
        -- But for many setups, the LSP (`ts_ls`) will work just fine
        -- ts_ls = {},
        --

        lua_ls = {
          -- cmd = { ... },
          -- filetypes = { ... },
          -- capabilities = {},
          settings = {
            Lua = {
              completion = {
                callSnippet = 'Replace',
              },
              -- You can toggle below to ignore Lua_LS's noisy `missing-fields` warnings
              -- diagnostics = { disable = { 'missing-fields' } },
            },
          },
        },

        -- OmniSharp C# LSP - Use defaults (will be configured via omnisharp.json)
        omnisharp = {
          handlers = {
            ['textDocument/definition'] = require('omnisharp_extended').definition_handler,
            ['textDocument/typeDefinition'] = require('omnisharp_extended').type_definition_handler,
            ['textDocument/references'] = require('omnisharp_extended').references_handler,
            ['textDocument/implementation'] = require('omnisharp_extended').implementation_handler,
          },
        },

        -- Angular Language Server
        angularls = {},

        -- TypeScript Language Server
        ts_ls = {},

        -- HTML Language Server (includes Emmet)
        html = {
          filetypes = { 'html', 'htmlangular' },
        },

        -- CSS/SCSS Language Server
        cssls = {
          settings = {
            css = {
              validate = true,
              lint = {
                unknownAtRules = 'ignore', -- Ignore SCSS @rules
              },
            },
            scss = {
              validate = true,
              lint = {
                unknownAtRules = 'ignore',
              },
            },
          },
        },

        -- ESLint Language Server
        eslint = {},
      }

      -- Ensure the servers and tools above are installed
      --
      -- To check the current status of installed tools and/or manually install
      -- other tools, you can run
      --    :Mason
      --
      -- You can press `g?` for help in this menu.
      --
      -- `mason` had to be setup earlier: to configure its options see the
      -- `dependencies` table for `nvim-lspconfig` above.
      --
      -- You can add other tools here that you want Mason to install
      -- for you, so that they are available from within Neovim.
      local ensure_installed = vim.tbl_keys(servers or {})
      vim.list_extend(ensure_installed, {
        'stylua', -- Used to format Lua code
        'prettier', -- Used to format TypeScript, HTML, CSS, SCSS
        'netcoredbg', -- C#/.NET debugger (required for DAP)
        'sonarlint-language-server', -- SonarQube Connected Mode diagnostics
      })
      require('mason-tool-installer').setup { ensure_installed = ensure_installed }

      require('mason-lspconfig').setup {
        ensure_installed = {}, -- explicitly set to an empty table (Kickstart populates installs via mason-tool-installer)
        automatic_installation = false,
        handlers = {
          function(server_name)
            local server = servers[server_name] or {}
            -- This handles overriding only values explicitly passed
            -- by the server configuration above. Useful when disabling
            -- certain features of an LSP (for example, turning off formatting for ts_ls)
            server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
            require('lspconfig')[server_name].setup(server)
          end,
        },
      }
    end,
  },

  { -- Autoformat
    'stevearc/conform.nvim',
    event = { 'BufWritePre' },
    cmd = { 'ConformInfo' },
    keys = {
      {
        '<leader>f',
        function()
          require('conform').format { async = true, lsp_format = 'fallback' }
        end,
        mode = '',
        desc = '[F]ormat buffer',
      },
    },
    opts = {
      notify_on_error = false,
      format_on_save = function(bufnr)
        -- Disable "format_on_save lsp_fallback" for languages that don't
        -- have a well standardized coding style. You can add additional
        -- languages here or re-enable it for the disabled ones.
        local disable_filetypes = { c = true, cpp = true }
        if disable_filetypes[vim.bo[bufnr].filetype] then
          return nil
        else
          return {
            timeout_ms = 500,
            lsp_format = 'fallback',
          }
        end
      end,
      formatters_by_ft = {
        lua = { 'stylua' },
        -- Angular/TypeScript/HTML/CSS/SCSS
        typescript = { 'prettier' },
        javascript = { 'prettier' },
        html = { 'prettier' },
        css = { 'prettier' },
        scss = { 'prettier' },
        json = { 'prettier' },
      },
    },
  },

  { -- Autocompletion
    'saghen/blink.cmp',
    event = 'VimEnter',
    version = '1.*',
    dependencies = {
      -- Snippet Engine
      {
        'L3MON4D3/LuaSnip',
        version = '2.*',
        build = (function()
          -- Build Step is needed for regex support in snippets.
          -- This step is not supported in many windows environments.
          -- Remove the below condition to re-enable on windows.
          if vim.fn.has 'win32' == 1 or vim.fn.executable 'make' == 0 then
            return
          end
          return 'make install_jsregexp'
        end)(),
        dependencies = {
          -- `friendly-snippets` contains a variety of premade snippets.
          --    See the README about individual language/framework/plugin snippets:
          --    https://github.com/rafamadriz/friendly-snippets
          -- {
          --   'rafamadriz/friendly-snippets',
          --   config = function()
          --     require('luasnip.loaders.from_vscode').lazy_load()
          --   end,
          -- },
        },
        opts = {},
      },
      'folke/lazydev.nvim',
    },
    --- @module 'blink.cmp'
    --- @type blink.cmp.Config
    opts = {
      keymap = {
        -- 'default' (recommended) for mappings similar to built-in completions
        --   <c-y> to accept ([y]es) the completion.
        --    This will auto-import if your LSP supports it.
        --    This will expand snippets if the LSP sent a snippet.
        -- 'super-tab' for tab to accept
        -- 'enter' for enter to accept
        -- 'none' for no mappings
        --
        -- For an understanding of why the 'default' preset is recommended,
        -- you will need to read `:help ins-completion`
        --
        -- No, but seriously. Please read `:help ins-completion`, it is really good!
        --
        -- All presets have the following mappings:
        -- <tab>/<s-tab>: move to right/left of your snippet expansion
        -- <c-space>: Open menu or open docs if already open
        -- <c-n>/<c-p> or <up>/<down>: Select next/previous item
        -- <c-e>: Hide menu
        -- <c-k>: Toggle signature help
        --
        -- See :h blink-cmp-config-keymap for defining your own keymap
        preset = 'default',

        -- For more advanced Luasnip keymaps (e.g. selecting choice nodes, expansion) see:
        --    https://github.com/L3MON4D3/LuaSnip?tab=readme-ov-file#keymaps
      },

      appearance = {
        -- 'mono' (default) for 'Nerd Font Mono' or 'normal' for 'Nerd Font'
        -- Adjusts spacing to ensure icons are aligned
        nerd_font_variant = 'mono',
      },

      completion = {
        -- By default, you may press `<c-space>` to show the documentation.
        -- Optionally, set `auto_show = true` to show the documentation after a delay.
        documentation = { auto_show = false, auto_show_delay_ms = 500 },
      },

      sources = {
        default = { 'lsp', 'path', 'snippets', 'lazydev' },
        providers = {
          lazydev = { module = 'lazydev.integrations.blink', score_offset = 100 },
        },
      },

      snippets = { preset = 'luasnip' },

      -- Blink.cmp includes an optional, recommended rust fuzzy matcher,
      -- which automatically downloads a prebuilt binary when enabled.
      --
      -- By default, we use the Lua implementation instead, but you may enable
      -- the rust implementation via `'prefer_rust_with_warning'`
      --
      -- See :h blink-cmp-config-fuzzy for more information
      fuzzy = { implementation = 'lua' },

      -- Shows a signature help window while you type arguments for a function
      signature = { enabled = true },
    },
  },

  -- Tokyonight colorscheme
  {
    'folke/tokyonight.nvim',
    priority = 1000,
    config = function()
      require('tokyonight').setup {
        style = 'night', -- night, storm, day, moon
        styles = {
          comments = { italic = false },
        },
      }
      -- Load tokyonight as default
      vim.cmd.colorscheme 'tokyonight-night'
    end,
  },

  { -- Catppuccin colorscheme - Beautiful pastel theme with great diff colors
    'catppuccin/nvim',
    name = 'catppuccin',
    priority = 1000,
    opts = {
      flavour = 'mocha', -- latte, frappe, macchiato, mocha (mocha = darkest)
      transparent_background = false,
      styles = {
        comments = { 'italic' },
        conditionals = {},
      },
      integrations = {
        neogit = true,
        diffview = true,
        aerial = true,
        treesitter = true,
        notify = true,
        which_key = true,
        telescope = { enabled = true },
        native_lsp = {
          enabled = true,
          underlines = {
            errors = { 'undercurl' },
            hints = { 'undercurl' },
            warnings = { 'undercurl' },
            information = { 'undercurl' },
          },
        },
      },
    },
  },

  -- Highlight todo, notes, etc in comments
  { 'folke/todo-comments.nvim', event = 'VimEnter', dependencies = { 'nvim-lua/plenary.nvim' }, opts = { signs = false } },

  { -- Collection of various small independent plugins/modules
    'echasnovski/mini.nvim',
    config = function()
      -- Better Around/Inside textobjects
      --
      -- Examples:
      --  - va)  - [V]isually select [A]round [)]paren
      --  - yinq - [Y]ank [I]nside [N]ext [Q]uote
      --  - ci'  - [C]hange [I]nside [']quote
      require('mini.ai').setup { n_lines = 500 }

      -- Add/delete/replace surroundings (brackets, quotes, etc.)
      --
      -- - saiw) - [S]urround [A]dd [I]nner [W]ord [)]Paren
      -- - sd'   - [S]urround [D]elete [']quotes
      -- - sr)'  - [S]urround [R]eplace [)] [']
      require('mini.surround').setup()

      -- Simple and easy statusline.
      --  You could remove this setup call if you don't like it,
      --  and try some other statusline plugin
      local statusline = require 'mini.statusline'
      -- set use_icons to true if you have a Nerd Font
      statusline.setup { use_icons = vim.g.have_nerd_font }

      -- You can configure sections in the statusline by overriding their
      -- default behavior. For example, here we set the section for
      -- cursor location to LINE:COLUMN
      ---@diagnostic disable-next-line: duplicate-set-field
      statusline.section_location = function()
        return '%2l:%-2v'
      end

      -- ... and there is more!
      --  Check out: https://github.com/echasnovski/mini.nvim
    end,
  },
  { -- Highlight, edit, and navigate code
    'nvim-treesitter/nvim-treesitter',
    build = ':TSUpdate',
    main = 'nvim-treesitter.configs', -- Sets main module to use for opts
    -- [[ Configure Treesitter ]] See `:help nvim-treesitter`
    opts = {
      ensure_installed = { 'bash', 'c', 'css', 'diff', 'html', 'lua', 'luadoc', 'markdown', 'markdown_inline', 'query', 'scss', 'typescript', 'vim', 'vimdoc' },
      -- Autoinstall languages that are not installed
      auto_install = true,
      highlight = {
        enable = true,
        -- Some languages depend on vim's regex highlighting system (such as Ruby) for indent rules.
        --  If you are experiencing weird indenting issues, add the language to
        --  the list of additional_vim_regex_highlighting and disabled languages for indent.
        additional_vim_regex_highlighting = { 'ruby' },
      },
      indent = { enable = true, disable = { 'ruby' } },
    },
    -- There are additional nvim-treesitter modules that you can use to interact
    -- with nvim-treesitter. You should go explore a few and see what interests you:
    --
    --    - Incremental selection: Included, see `:help nvim-treesitter-incremental-selection-mod`
    --    - Show your current context: https://github.com/nvim-treesitter/nvim-treesitter-context
    --    - Treesitter + textobjects: https://github.com/nvim-treesitter/nvim-treesitter-textobjects
  },

  -- The following comments only work if you have downloaded the kickstart repo, not just copy pasted the
  -- init.lua. If you want these files, they are in the repository, so you can just download them and
  -- place them in the correct locations.

  -- NOTE: Next step on your Neovim journey: Add/Configure additional plugins for Kickstart
  --
  --  Here are some example plugins that I've included in the Kickstart repository.
  --  Uncomment any of the lines below to enable them (you will need to restart nvim).
  --
  -- require 'kickstart.plugins.debug',
  -- require 'kickstart.plugins.indent_line',
  -- require 'kickstart.plugins.lint',
  -- require 'kickstart.plugins.autopairs',
  -- require 'kickstart.plugins.neo-tree',
  -- require 'kickstart.plugins.gitsigns', -- adds gitsigns recommend keymaps

  -- NOTE: The import below can automatically add your own plugins, configuration, etc from `lua/custom/plugins/*.lua`
  --    This is the easiest way to modularize your config.
  --
  --  Uncomment the following line and add your plugins to `lua/custom/plugins/*.lua` to get going.
  -- { import = 'custom.plugins' },
  --
  -- For additional information with loading, sourcing and examples see `:help lazy.nvim-🔌-plugin-spec`
  -- Or use telescope!
  -- In normal mode type `<space>sh` then write `lazy.nvim-plugin`
  -- you can continue same window with `<space>sr` which resumes last telescope search
}, {
  ui = {
    -- If you are using a Nerd Font: set icons to an empty table which will use the
    -- default lazy.nvim defined Nerd Font icons, otherwise define a unicode icons table
    icons = vim.g.have_nerd_font and {} or {
      cmd = '⌘',
      config = '🛠',
      event = '📅',
      ft = '📂',
      init = '⚙',
      keys = '🗝',
      plugin = '🔌',
      runtime = '💻',
      require = '🌙',
      source = '📄',
      start = '🚀',
      task = '📌',
      lazy = '💤 ',
    },
  },
})
