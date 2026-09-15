-- lua/shared/dirty.lua
-- Dirty-Dateien = Branch-geaenderte Dateien gegen die Base (vim.g.project_git_base, z.B. origin/develop).
-- Reine Helfer ohne Telescope-State, ausgelagert aus core.lua, damit sowohl die sD*-Familie (core.lua)
-- als auch die Dirty-Test-Keys sDti/sDtI/sDtu/sDtU (keybindings/tests.lua) dieselbe Liste sehen.
--
-- Bewusst: `base...HEAD` (drei Punkte) = nur COMMITTETE Aenderungen seit dem Merge-Base.
-- Working-Tree/Staged/Untracked sind NICHT enthalten (Verhalten von sDo seit jeher).

local M = {}

-- Endungen, die als Code zaehlen. Profil-uebergreifend: jedes Profil bekommt automatisch
-- nur was es enthaelt (Backend -> .cs, Frontend -> .ts/.html/.scss, Database -> .sql).
M.CODE_EXTS = { 'cs', 'ts', 'js', 'html', 'scss', 'css', 'sql', 'ps1', 'sh', 'yaml', 'yml' }

function M.is_code_file(rel)
  for _, ext in ipairs(M.CODE_EXTS) do
    if rel:match('%.' .. ext .. '$') then return true end
  end
  return false
end

-- Aktives Dirty-Profil (per <leader>sDp umgeschaltet). Default 'Backend'.
function M.profile()
  return vim.g.dirty_profile or 'Backend'
end

-- Profilname als Pfadsegment im git-relativen (Forward-Slash-)Pfad.
function M.in_profile(rel, profile)
  local p = vim.pesc(profile)
  return rel:match('/' .. p .. '/') ~= nil or rel:match('^' .. p .. '/') ~= nil
end

-- Rohe Liste der Branch-geaenderten Dateien (vs Base), ungefiltert.
-- -> raw_lines|nil, base, cwd
function M.git_dirty_raw()
  local base = vim.g.project_git_base or 'origin/develop'
  local cwd = vim.fn.getcwd()
  local raw = vim.fn.systemlist(string.format('git -C "%s" diff --name-only %s...HEAD 2>&1', cwd, base))
  if vim.v.shell_error ~= 0 then
    vim.notify('git diff fehlgeschlagen:\n' .. table.concat(raw, '\n'), vim.log.levels.ERROR, { title = 'Dirty-Dateien', timeout = 10000 })
    return nil, base, cwd
  end
  return raw, base, cwd
end

-- Branch-geaenderte Code-Dateien des Profils als absolute Pfade (gemischte Separatoren auf Windows:
-- cwd-Teil mit Backslash, git-relativer Teil mit Forward-Slash — vor Pfad-Matching normalisieren!).
-- -> files(abs)|nil, base
function M.get_dirty_files(profile)
  profile = profile or M.profile()
  local raw, base, cwd = M.git_dirty_raw()
  if not raw then return nil, base end
  local files = {}
  for _, line in ipairs(raw) do
    local rel = (line or ''):gsub('%s+$', '')
    if rel ~= '' and M.is_code_file(rel) and M.in_profile(rel, profile) then
      local abs = vim.fn.fnamemodify(cwd .. '/' .. rel, ':p')
      if vim.fn.filereadable(abs) == 1 then
        table.insert(files, abs)
      end
    end
  end
  return files, base
end

return M
