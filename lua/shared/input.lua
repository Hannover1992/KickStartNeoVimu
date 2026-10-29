-- lua/shared/input.lua
-- vim.fn.input(), das mehrzeiliges Einfuegen versteht.
--
-- Neovims vim.paste nimmt in der Kommandozeile NUR die erste Zeile (runtime/_editor.lua:
-- "cmdline-mode: paste only 1 line"). Eine aus git log kopierte Hash-Spalte kam so nur mit
-- dem ersten Hash an. Hier wird vim.paste fuer die Dauer der Eingabe ersetzt: alle Zeilen
-- werden mit Leerzeichen verbunden eingefuegt. Danach ist das Original wieder aktiv.

local M = {}

function M.multiline(opts)
  local orig_paste = vim.paste
  vim.paste = function(lines, phase)
    if vim.fn.getcmdtype() == '@' then
      -- Ein Paste kann in Stuecken kommen: die letzte Zeile eines Stuecks und die erste des
      -- naechsten sind dieselbe Zeile -> innerhalb eines Stuecks mit ' ' verbinden reicht.
      local text = table.concat(lines, ' '):gsub('%c', ' ')
      vim.api.nvim_feedkeys(text, 'nt', true)
      return true
    end
    return orig_paste(lines, phase)
  end
  local ok, res = pcall(vim.fn.input, opts)
  vim.paste = orig_paste
  if not ok then return nil end
  return res
end

return M
