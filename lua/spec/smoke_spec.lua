-- lua/spec/smoke_spec.lua
-- Basis-Test: Prüft ob die spec-Infrastruktur funktioniert
-- Dieser Test muss nach JEDEM Refactoring-Schritt grün bleiben

describe('KickStartNeoVim Smoke Tests', function()
  it('plenary busted framework läuft', function()
    assert.is_true(true)
  end)

  it('vim.fn.has() ist verfügbar', function()
    assert.is_not_nil(vim.fn.has)
  end)

  it('is_windows Detection funktioniert', function()
    local result = vim.fn.has('win32')
    assert.is_true(result == 0 or result == 1)
  end)
end)
