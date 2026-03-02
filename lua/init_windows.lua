-- lua/init_windows.lua
-- Windows Native Neovim Entry-Point
-- Geladen von init.lua wenn: vim.fn.has('win32') == 1
--
-- Lade-Reihenfolge (kritisch!):
--   platform → project → core → keybindings

-- Platform-Assertion (Sicherheitsnetz)
assert(vim.fn.has('win32') == 1, 'FEHLER: init_windows.lua auf nicht-Windows-System geladen!')

-- 1. Platform: is_windows, Chrome-Pfade, open_url(), path-Utilities
local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität: keybindings nutzen is_windows

-- 2. Project: vim.g.project_* Globals setzen (DCSRE / CENCOCD / UNKNOWN)
require('shared.project').detect()

-- 3. Core: vim.g.mapleader, vim.opt, Autocmds, Lazy-Bootstrap, alle Plugins
-- MUSS nach project.detect() laufen (core.lua nutzt vim.g.project_* intern)
require('shared.core')

-- 4. Custom Keybindings (modular, nach core.lua — toggleterm muss geladen sein)
require('shared.keybindings.backend')
require('shared.keybindings.frontend')
require('shared.keybindings.docker')
require('shared.keybindings.tests')
require('shared.keybindings.git')
require('shared.keybindings.clipboard')
