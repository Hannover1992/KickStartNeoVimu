--[[

=====================================================================
==================== READ THIS BEFORE CONTINUING ====================
=====================================================================
========                                    .-----.          ========
========         .----------------------.   | === |          ========
========         |.-""""""""""""""""""-.|   |-----|          ========
========         ||                    ||   | === |          ========
========         ||   KICKSTART.NVIM   ||   |-----|          ========
========         ||                    ||   | === |          ========
========         ||                    ||   |-----|          ========
========         ||:Tutor              ||   |:::::|          ========
========         |'-..................-'|   |____o|          ========
========         `"")----------------(""`   ___________      ========
========        /::::::::::|  |::::::::::\  \ no mouse \     ========
========       /:::========|  |==hjkl==:::\  \ required \    ========
========      '""""""""""""'  '""""""""""""'  '""""""""""'   ========
========                                                     ========
=====================================================================
=====================================================================

What is Kickstart?

  Kickstart.nvim is *not* a distribution.

  Kickstart.nvim is a starting point for your own configuration.
    The goal is that you can read every line of code, top-to-bottom, understand
    what your configuration is doing, and modify it to suit your needs.

    Once you've done that, you can start exploring, configuring and tinkering to
    make Neovim your own! That might mean leaving Kickstart just the way it is for a while
    or immediately breaking it into modular pieces. It's up to you!

    If you don't know anything about Lua, I recommend taking some time to read through
    a guide. One possible example which will only take 10-15 minutes:
      - https://learnxinyminutes.com/docs/lua/

    After understanding a bit more about Lua, you can use `:help lua-guide` as a
    reference for how Neovim integrates Lua.
    - :help lua-guide
    - (or HTML version): https://neovim.io/doc/user/lua-guide.html

Kickstart Guide:

  TODO: The very first thing you should do is to run the command `:Tutor` in Neovim.

    If you don't know what this means, type the following:
      - <escape key>
      - :
      - Tutor
      - <enter key>

    (If you already know the Neovim basics, you can skip this step.)

  Once you've completed that, you can continue working through **AND READING** the rest
  of the kickstart init.lua.

  Next, run AND READ `:help`.
    This will open up a help window with some basic information
    about reading, navigating and searching the builtin help documentation.

    This should be the first place you go to look when you're stuck or confused
    with something. It's one of my favorite Neovim features.

    MOST IMPORTANTLY, we provide a keymap "<space>sh" to [s]earch the [h]elp documentation,
    which is very useful when you're not exactly sure of what you're looking for.

  I have left several `:help X` comments throughout the init.lua
    These are hints about where to find more information about the relevant settings,
    plugins or Neovim features used in Kickstart.

   NOTE: Look for lines like this

    Throughout the file. These are for you, the reader, to help you understand what is happening.
    Feel free to delete them once you know what you're doing, but they should serve as a guide
    for when you are first encountering a few different constructs in your Neovim config.

If you experience any errors while trying to install kickstart, run `:checkhealth` for more info.

I hope you enjoy your Neovim journey,
- TJ

P.S. You can delete this when you're done too. It's your config now! :)
--]]

-- Set <space> as the leader key
-- See `:help mapleader`
--  NOTE: Must happen before plugins are loaded (otherwise wrong leader will be used)
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- Set to true if you have a Nerd Font installed and selected in the terminal
vim.g.have_nerd_font = false

-- Reduce LSP log spam (OmniSharp sends many warnings during startup)
vim.lsp.set_log_level('ERROR')

-- [[ Project Detection ]]
-- Automatically detect which project we're in based on current working directory
-- This enables project-specific keybindings and settings
local cwd = vim.fn.getcwd()

-- Platform detection helper
local is_windows = vim.fn.has('win32') == 1

-- Helper: Find DCSRE root dynamically (looks for folder containing "Sources")
local function find_dcsre_root(path)
  -- Normalize path separators
  path = path:gsub('\\', '/')

  -- Strategy 1: Extract from path pattern .../DCSRE.../Sources/...
  local root = path:match('(.*/DCSRE[^/]*)/Sources')
  if root and vim.fn.isdirectory(root .. '/Sources') == 1 then
    return root
  end

  -- Strategy 2: Search upward for Sources folder
  local check_path = path
  while check_path and #check_path > 3 do
    if vim.fn.isdirectory(check_path .. '/Sources') == 1 then
      return check_path
    end
    -- Also check for nested DCSRE folder with Sources (e.g., DCSRE_Azure/DCSRE/Sources)
    local nested = check_path .. '/DCSRE'
    if vim.fn.isdirectory(nested .. '/Sources') == 1 then
      return nested
    end
    check_path = check_path:match('(.+)/[^/]+$')
  end
  return nil
end

-- Detect project and set paths dynamically
vim.g.project_name = 'UNKNOWN'

if cwd:match('Kluger') or cwd:match('CENCOCD') or cwd:match('CenCoCo') or cwd:match('cencoco') then
  -- CENCOCD project
  vim.g.project_name = 'CENCOCD'
  vim.g.project_backend = is_windows and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API' or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API'
  vim.g.project_frontend = is_windows and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.Blazor' or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.Blazor'
  vim.g.project_webhost = is_windows and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API' or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src/Core/CenCoCo.Core.API'
  vim.g.project_docker_root = is_windows and 'C:/Users/Administrator/Documents/Work/Kluger/cencoco/src' or '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src'
  vim.g.project_docker_root_windows = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco\\src'
  vim.g.project_git_base = 'origin/main'
  vim.g.project_launch_profile = 'https'
  vim.g.project_root_windows = 'C:\\Users\\Administrator\\Documents\\Work\\Kluger\\cencoco'
  vim.g.project_root_wsl = '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco'
  vim.g.project_tfs_commit_url = nil
  vim.g.project_pr_url = nil -- TODO: Add CENCOCD Azure DevOps URL wenn vorhanden
elseif cwd:match('DCSRE') then
  -- DCSRE project - find root dynamically (works with DCSRE, DCSRE_Azure, worktrees, etc.)
  local dcsre_root = find_dcsre_root(cwd)
  if dcsre_root then
    vim.g.project_name = 'DCSRE'
    vim.g.project_backend = dcsre_root .. '/Sources/Backend'
    vim.g.project_backend_windows = dcsre_root:gsub('/', '\\') .. '\\Sources\\Backend'
    vim.g.project_frontend = dcsre_root .. '/Sources/Frontend'
    vim.g.project_webhost = dcsre_root .. '/Sources/Backend/VDEK.DCSP.WebHost'
    vim.g.project_docker_root = dcsre_root .. '/Sources'
    vim.g.project_docker_root_windows = dcsre_root:gsub('/', '\\') .. '\\Sources'
    vim.g.project_git_base = 'origin/develop'
    vim.g.project_launch_profile = 'WebHost'
    vim.g.project_root_windows = dcsre_root:gsub('/', '\\')
    vim.g.project_root_wsl = dcsre_root:gsub('C:', '/mnt/c')
    -- OLD TFS (auskommentiert, falls noch gebraucht):
    -- vim.g.project_tfs_commit_url = 'https://tfs.itsg.de/tfs/ITSGCollection/DCS_Pflege/_git/DCSRE/commit/%s'
    -- vim.g.project_pr_url = 'https://tfs.itsg.de/tfs/ITSGCollection/DCS_Pflege/_git/DCSRE/pullrequest/%s?path=%s'
    -- NEW Azure DevOps:
    vim.g.project_tfs_commit_url = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/commit/%s'
    vim.g.project_pr_url = 'https://dev.azure.com/ITSGGMBH/AP0071%%20Daten%%20Clearing%%20Stelle%%20Pflege/_git/DCSRE/pullrequest/%s?path=%s'
  end
end

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
      { '<leader>gc', '<cmd>Neogit commit kind=commit<cr>', desc = '[G]it [C]ommit' },
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
      -- Open in browser - ALWAYS open in NEW Chrome window
      vim.g.mkdp_browserfunc = 'OpenMarkdownPreview'
      if vim.fn.has('win32') == 1 then
        -- Windows: Chrome mit --new-window Flag
        vim.cmd([[
          function OpenMarkdownPreview(url)
            execute 'silent !start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --new-window "' . a:url . '"'
          endfunction
        ]])
      else
        -- WSL: Chrome via Windows path mit --new-window
        vim.cmd([[
          function OpenMarkdownPreview(url)
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
    end,
    ---@module 'obsidian'
    ---@type obsidian.config
    opts = {
      legacy_commands = false, -- Use new command style (will be removed in next major release)

      workspaces = {
        {
          name = 'DCSRE',
          path = vim.fn.has('win32') == 1 and 'C:/Users/Administrator/Documents/DCS' or '/mnt/c/Users/Administrator/Documents/DCS',
        },
        {
          name = 'CenCoCo',
          path = vim.fn.has('win32') == 1 and 'C:/Users/Administrator/Documents/Obsydian/CenCoCo' or '/mnt/c/Users/Administrator/Documents/Obsydian/CenCoCo',
        },
        {
          name = 'Brain',
          path = vim.fn.has('win32') == 1 and 'C:/Users/Administrator/Documents/Brain' or '/mnt/c/Users/Administrator/Documents/Brain',
        },
      },

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
              vim.fn.system('google-chrome --new-window "' .. url .. '" &')
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
  {
    'kristijanhusak/vim-dadbod-ui',
    dependencies = {
      { 'tpope/vim-dadbod', lazy = true },
      { 'kristijanhusak/vim-dadbod-completion', ft = { 'sql', 'mysql', 'plsql' }, lazy = true },
    },
    cmd = { 'DBUI', 'DBUIToggle', 'DBUIAddConnection', 'DBUIFindBuffer' },
    keys = {
      { '<leader>db', '<cmd>DBUIToggle<cr>', desc = '[D]ata[B]ase UI toggle' },
      { '<leader>da', '<cmd>DBUIAddConnection<cr>', desc = '[D]atabase [A]dd connection' },
    },
    init = function()
      vim.g.db_ui_use_nerd_fonts = 1
      vim.g.db_ui_show_database_icon = 1
      -- MSSQL Connection Beispiel (auskommentiert):
      -- vim.g.dbs = {
      --   { name = 'DCSRE_Local', url = 'sqlserver://localhost:1433;database=DCSP;user=sa;password=YourPassword;trustServerCertificate=true' },
      --   { name = 'DCSRE_Docker', url = 'sqlserver://localhost:1434;database=DCSP;user=sa;password=YourPassword;trustServerCertificate=true' },
      -- }
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
      { '<leader>o', '<cmd>AerialToggle<cr>', desc = '[O]utline Toggle (Code Structure)' },
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

  -- nvim-notify - Beautiful notifications with animations
  {
    'rcarriga/nvim-notify',
    config = function()
      local notify = require('notify')
      notify.setup({
        stages = 'fade_in_slide_out', -- Animation style
        timeout = 3000, -- Display time (ms)
        background_colour = '#000000',
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
    opts = {
      signs = {
        add = { text = '+' },
        change = { text = '~' },
        delete = { text = '_' },
        topdelete = { text = '‾' },
        changedelete = { text = '~' },
      },
      on_attach = function(bufnr)
        local gitsigns = require('gitsigns')

        local function map(mode, l, r, opts)
          opts = opts or {}
          opts.buffer = bufnr
          vim.keymap.set(mode, l, r, opts)
        end

        -- Navigation
        map('n', ']c', function()
          if vim.wo.diff then
            vim.cmd.normal({ ']c', bang = true })
          else
            gitsigns.nav_hunk('next')
          end
        end, { desc = 'Next git [c]hange/hunk' })

        map('n', '[c', function()
          if vim.wo.diff then
            vim.cmd.normal({ '[c', bang = true })
          else
            gitsigns.nav_hunk('prev')
          end
        end, { desc = 'Previous git [c]hange/hunk' })

        -- Staged hunk navigation
        map('n', ']C', function()
          gitsigns.nav_hunk('next', { target = 'staged' })
        end, { desc = 'Next staged [C]hange/hunk' })

        map('n', '[C', function()
          gitsigns.nav_hunk('prev', { target = 'staged' })
        end, { desc = 'Previous staged [C]hange/hunk' })

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
            require('telescope.themes').get_dropdown(),
          },
        },
      }

      -- Enable Telescope extensions if they are installed
      pcall(require('telescope').load_extension, 'fzf')
      pcall(require('telescope').load_extension, 'ui-select')

      -- See `:help telescope.builtin`
      local builtin = require 'telescope.builtin'
      vim.keymap.set('n', '<leader>sh', builtin.help_tags, { desc = '[S]earch [H]elp' })
      vim.keymap.set('n', '<leader>sk', builtin.keymaps, { desc = '[S]earch [K]eymaps' })
      vim.keymap.set('n', '<leader>sf', builtin.find_files, { desc = '[S]earch [F]iles (respects .gitignore)' })
      vim.keymap.set('n', '<leader>sF', function()
        builtin.find_files({ no_ignore = true, hidden = true })
      end, { desc = '[S]earch [F]iles (ALL, including ignored)' })
      vim.keymap.set('n', '<leader>sc', builtin.colorscheme, { desc = '[S]earch [C]olorscheme (live preview)' })
      vim.keymap.set('n', '<leader>ss', builtin.builtin, { desc = '[S]earch [S]elect Telescope' })
      vim.keymap.set('n', '<leader>sw', builtin.grep_string, { desc = '[S]earch current [W]ord' })
      vim.keymap.set('n', '<leader>sg', builtin.live_grep, { desc = '[S]earch by [G]rep (respects .gitignore)' })
      vim.keymap.set('n', '<leader>sG', function()
        builtin.live_grep({ additional_args = { '--no-ignore', '--hidden' } })
      end, { desc = '[S]earch by [G]rep (ALL, including ignored)' })
      vim.keymap.set('n', '<leader>sd', builtin.diagnostics, { desc = '[S]earch [D]iagnostics' })
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
      vim.keymap.set('n', '<leader>sr', builtin.resume, { desc = '[S]earch [R]esume' })
      vim.keymap.set('n', '<leader>s.', builtin.oldfiles, { desc = '[S]earch Recent Files ("." for repeat)' })
      vim.keymap.set('n', '<leader><leader>', builtin.buffers, { desc = '[ ] Find existing buffers' })

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

-- Custom keybindings for project-specific tasks
-- Uses vim.g.project_* variables set in Project Detection section

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
end, { desc = '[R]un [B]ackend [W]ebhost' })

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
end, { desc = '[R]un [B]ackend [S]etup (Migrations)' })

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
end, { desc = '[R]un [B]ackend [B]uild (dotnet build)' })

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
end, { desc = '[R]un [B]ackend [T]ests' })

-- Run Backend Unit Tests: Run tests excluding Database/Storage/Docker
vim.keymap.set('n', '<leader>rbu', function()
  local Terminal = require('toggleterm.terminal').Terminal
  -- PowerShell: Single quotes für Filter (keine Escape-Probleme)
  local cmd = "powershell.exe -Command \"Set-Location '" .. vim.g.project_backend .. "'; dotnet test --filter 'Category!=Database & Category!=Storage & Category!=Docker'\""
  local test = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  test:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Running Unit Tests (no DB/Storage/Docker)...', vim.log.levels.INFO)
end, { desc = '[R]un [B]ackend [U]nit tests (no DB/Storage/Docker)' })

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

-- Run Frontend: Start dev server (web)
vim.keymap.set('n', '<leader>rfw', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; dotnet run --launch-profile https"'
  else
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; npm start"'
  end
  local frontend = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 21, -- Separate terminal ID for frontend
  })
  frontend:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Starting Frontend dev server...', vim.log.levels.INFO)
end, { desc = '[R]un [F]rontend [W]eb (dev server)' })

-- Run Frontend Build: Build production app
vim.keymap.set('n', '<leader>rfb', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local cmd
  if vim.g.project_name == 'CENCOCD' then
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; docker compose build frontend"'
  else
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; npm run build"'
  end
  local build = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
  })
  build:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Building Frontend...', vim.log.levels.INFO)
end, { desc = '[R]un [F]ront [B]uild (production)' })

-- Run Frontend Test: Execute tests
vim.keymap.set('n', '<leader>rft', function()
  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = 'powershell.exe -Command "Set-Location \'' .. vim.g.project_frontend .. '\'; npm test"',
    direction = 'horizontal',
    close_on_exit = false,
  })
  test:toggle()
  vim.notify('[' .. vim.g.project_name .. '] Running Frontend tests...', vim.log.levels.INFO)
end, { desc = '[R]un [F]ront [T]est' })

-- E2E Gesamtsystemtest: Run full integration E2E tests (DCSRE only, headless via PowerShell)
vim.keymap.set('n', '<leader>reg', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = 'powershell.exe -Command "cd \'C:\\Users\\Administrator\\Documents\\Work\\Code2\\DCSRE\\Sources\\Tests\\Cypress\'; npm run cypress:run:gesamtsystemtest"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 30, -- Separate terminal ID for E2E tests
  })
  test:toggle()
  vim.notify('[DCSRE] Running E2E Gesamtsystemtest (headless)...', vim.log.levels.INFO)
end, { desc = '[R]un [E]2E [G]esamtsystemtest (full integration)' })

-- E2E Systemtest: Run isolated system tests (DCSRE only, headless via PowerShell)
vim.keymap.set('n', '<leader>res', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = 'powershell.exe -Command "cd \'C:\\Users\\Administrator\\Documents\\Work\\Code2\\DCSRE\\Sources\\Tests\\Cypress\'; npm run cypress:run:systemtest"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 31, -- Separate terminal ID for E2E tests
  })
  test:toggle()
  vim.notify('[DCSRE] Running E2E Systemtest (isolated)...', vim.log.levels.INFO)
end, { desc = '[R]un [E]2E [S]ystemtest (isolated)' })

-- E2E Open: Interactive Cypress UI (DCSRE only, via PowerShell)
vim.keymap.set('n', '<leader>reo', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('E2E Tests only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local test = Terminal:new({
    cmd = 'powershell.exe -Command "cd \'C:\\Users\\Administrator\\Documents\\Work\\Code2\\DCSRE\\Sources\\Tests\\Cypress\'; npm run cypress:open:systemtest"',
    direction = 'horizontal',
    close_on_exit = false,
    count = 32, -- Separate terminal ID for Cypress UI
  })
  test:toggle()
  vim.notify('[DCSRE] Opening Cypress UI...', vim.log.levels.INFO)
end, { desc = '[R]un [E]2E [O]pen (interactive UI)' })

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
end, { desc = '[R]un [D]ocker [I]nfrastructure (up)' })

-- Docker All: Start ALL services (Profile=all) - DCSRE only
vim.keymap.set('n', '<leader>rDa', function()
  local Terminal = require('toggleterm.terminal').Terminal
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Docker All is only for DCSRE project', vim.log.levels.WARN)
    return
  end
  local cmd = 'powershell.exe -ExecutionPolicy Bypass -Command "Set-Location \'' .. vim.g.project_docker_root_windows .. '\'; .\\docker-up.ps1 -EnvFile \\"./.env.noproxy\\" -Profile all -SkipTests; if ($?) { notify \'Docker All erfolgreich\' } else { notify \'Docker All fehlgeschlagen\' }"'
  local infra = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 23, -- Separate terminal ID for docker all
  })
  infra:toggle()
  vim.notify('[DCSRE] Starting Docker ALL (full environment)...', vim.log.levels.INFO)
end, { desc = '[R]un [D]ocker [A]ll (Profile=all, DCSRE)' })

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
end, { desc = '[R]un [D]ocker [r]undown (quick, keep data)' })

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
end, { desc = '[R]un [D]ocker [R]eset (full cleanup)' })

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
end, { desc = '[R]un [D]ocker [F]rontend build' })

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
end, { desc = '[R]un [D]ocker [F]rontend up' })

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
end, { desc = '[R]un [D]ocker [B]ackend build' })

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
end, { desc = '[R]un [D]ocker [B]ackend up' })

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

-- Run Integration Mock: Tests with DicMockServer (high parallelism - 38 threads)
vim.keymap.set('n', '<leader>rim', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
    return
  end
  -- Set 38 threads for mock tests (no DB conflicts)
  if not set_xunit_threads(38) then return end
  vim.notify('[DCSRE] Set maxParallelThreads=38 for Mock tests', vim.log.levels.INFO)

  local Terminal = require('toggleterm.terminal').Terminal
  local test_dir = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
  local cmd = 'dotnet test "' .. test_dir .. '" --filter "FullyQualifiedName~IntegrationTests&FullyQualifiedName~DicMockServer" --verbosity detailed'
  local test = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 40, -- Separate terminal ID for integration tests
    on_exit = function()
      -- Reset to 1 thread when terminal closes
      set_xunit_threads(1)
      vim.notify('[DCSRE] Reset maxParallelThreads=1', vim.log.levels.INFO)
    end,
  })
  test:toggle()
  vim.notify('[DCSRE] Running Integration Mock tests (38 threads)...', vim.log.levels.INFO)
end, { desc = '[R]un [I]ntegration [M]ock (DicMockServer, 38 threads)' })

-- Run Integration DB: Tests WITHOUT DicMockServer (lower parallelism - 8 threads)
vim.keymap.set('n', '<leader>rid', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Integration Tests only for DCSRE', vim.log.levels.WARN)
    return
  end
  -- Set 8 threads for DB tests (avoid conflicts)
  if not set_xunit_threads(8) then return end
  vim.notify('[DCSRE] Set maxParallelThreads=8 for DB tests', vim.log.levels.INFO)

  local Terminal = require('toggleterm.terminal').Terminal
  local test_dir = vim.g.project_backend_windows .. '\\VDEK.DCSP.IntegrationTests'
  local cmd = 'dotnet test "' .. test_dir .. '" --filter "FullyQualifiedName~IntegrationTests&FullyQualifiedName!~DicMockServer" --verbosity detailed'
  local test = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 41, -- Separate terminal ID for integration DB tests
    on_exit = function()
      -- Reset to 1 thread when terminal closes
      set_xunit_threads(1)
      vim.notify('[DCSRE] Reset maxParallelThreads=1', vim.log.levels.INFO)
    end,
  })
  test:toggle()
  vim.notify('[DCSRE] Running Integration DB tests (8 threads)...', vim.log.levels.INFO)
end, { desc = '[R]un [I]ntegration [D]B (non-mock, 8 threads)' })

-- Run Backend Build (clean + build)
vim.keymap.set('n', '<leader>rbb', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Backend Build only for DCSRE', vim.log.levels.WARN)
    return
  end
  local Terminal = require('toggleterm.terminal').Terminal
  local backend_dir = vim.g.project_backend_windows
  local cmd = 'dotnet clean "' .. backend_dir .. '" && dotnet build "' .. backend_dir .. '"'
  local build = Terminal:new({
    cmd = cmd,
    direction = 'horizontal',
    close_on_exit = false,
    count = 44,
  })
  build:toggle()
  vim.notify('[DCSRE] Backend clean + build gestartet', vim.log.levels.INFO)
end, { desc = '[R]un [B]ackend [B]uild (clean + build)' })

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
end, { desc = '[R]un [M]ock [D]ocker (ManualTestRunner)' })

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
end, { desc = '[R]un [M]ock [L]ocal (ManualTestRunner)' })

-- Quickfix: Show only warnings in quickfix list
vim.keymap.set('n', '<leader>qw', function()
  vim.diagnostic.setqflist({ severity = vim.diagnostic.severity.WARN })
  vim.cmd('copen')
end, { desc = '[Q]uickfix [W]arnings only' })

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

-- Quickfix: Show dirty files in current branch (vs upstream)
vim.keymap.set('n', '<leader>qd', function()
  git_diff_to_quickfix('@{upstream}', 'vs upstream')
end, { desc = '[Q]uickfix [d]irty files (vs upstream)' })

-- Quickfix: Show changed files vs project base branch (auto-detects project)
vim.keymap.set('n', '<leader>qD', function()
  git_diff_to_quickfix(vim.g.project_git_base, 'vs ' .. vim.g.project_git_base .. ' (' .. vim.g.project_name .. ')')
end, { desc = '[Q]uickfix vs [D]evelop/Main (project base)' })

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

-- Copy Windows path to clipboard
vim.keymap.set('n', '<leader>ypw', function()
  local current_file = vim.fn.expand('%:p')

  -- Convert WSL path to Windows path
  local windows_path = current_file:gsub('/mnt/c/', 'C:\\'):gsub('/', '\\')

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
end, { desc = '[R]un [C]ommit (open in TFS browser)' })

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

  -- Open in Chrome new window
  local cmd = string.format([[start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --new-window "%s"]], url)
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
end, { desc = '[R]un [P]ush (Windows VPN)' })

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
end, { desc = '[R]un [P]ull (Windows VPN)' })

-- The line beneath this is called `modeline`. See `:help modeline`
-- vim: ts=2 sts=2 sw=2 et
