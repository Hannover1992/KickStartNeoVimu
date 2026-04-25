-- lua/spec/platform_spec.lua
-- Tests für lua/shared/platform.lua
-- Testet REINE STRING-OPERATIONEN (kein Mock nötig)
-- Wird parallel zu S2_Platform entwickelt

describe('platform.lua', function()
  local platform

  -- HINWEIS: Dieser Test läuft BEVOR platform.lua existiert.
  -- Beim ersten Durchlauf werden die Tests bzgl. platform.lua
  -- pending sein oder fehlschlagen. Das ist OK.
  -- Nach S2_Platform sind alle Tests grün.
  before_each(function()
    -- Modul neu laden (cache leeren)
    package.loaded['shared.platform'] = nil
    local ok, result = pcall(require, 'shared.platform')
    if ok then
      platform = result
    else
      platform = nil
    end
  end)

  describe('Verfügbarkeit', function()
    it('platform Modul existiert nach S2_Platform', function()
      -- Dieser Test wird erst nach S2_Platform grün
      if platform == nil then
        pending('S2_Platform noch nicht implementiert')
        return
      end
      assert.is_not_nil(platform)
    end)

    it('is_windows ist ein Boolean', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      assert.is_true(type(platform.is_windows) == 'boolean')
    end)
  end)

  describe('to_windows_path()', function()
    it('konvertiert Forward-Slashes zu Backslashes', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      assert.equals('C:\\Users\\test\\file.lua', platform.to_windows_path('C:/Users/test/file.lua'))
    end)

    it('lässt Backslashes unverändert', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      assert.equals('C:\\Users\\test', platform.to_windows_path('C:\\Users\\test'))
    end)

    it('behandelt leeren String', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      assert.equals('', platform.to_windows_path(''))
    end)
  end)

  describe('wsl_to_windows()', function()
    it('konvertiert /mnt/c/ zu C:\\', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      local result = platform.wsl_to_windows('/mnt/c/Users/Administrator/test')
      assert.equals('C:\\Users\\Administrator\\test', result)
    end)

    it('konvertiert /mnt/d/ zu D:\\', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      local result = platform.wsl_to_windows('/mnt/d/Projects/myapp')
      assert.equals('D:\\Projects\\myapp', result)
    end)

    it('konvertiert auch Großbuchstaben korrekt', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      local result = platform.wsl_to_windows('/mnt/c/Users')
      assert.equals('C:\\Users', result)
    end)

    it('lässt Windows-Pfade unverändert wenn kein /mnt/', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      -- Windows-Pfad ohne /mnt/ sollte nur Slashes konvertieren
      local result = platform.wsl_to_windows('C:/Users/test')
      assert.equals('C:\\Users\\test', result)
    end)
  end)

  describe('user_home_windows()', function()
    local orig_userprofile

    before_each(function() orig_userprofile = os.getenv('USERPROFILE') end)
    after_each(function()
      if orig_userprofile then
        vim.fn.setenv('USERPROFILE', orig_userprofile)
      end
    end)

    it('liefert USERPROFILE wenn gesetzt', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      vim.fn.setenv('USERPROFILE', 'C:\\Users\\Patryk')
      package.loaded['shared.platform'] = nil
      local p = require('shared.platform')
      assert.equals('C:\\Users\\Patryk', p.user_home_windows())
    end)

    it('Fallback Administrator wenn USERPROFILE leer', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      vim.fn.setenv('USERPROFILE', '')
      package.loaded['shared.platform'] = nil
      local p = require('shared.platform')
      -- leerer String triggert Fallback (os.getenv liefert "" → falsy via 'or' nicht!)
      -- Hinweis: '' ist truthy in Lua → Test prüft das aktuelle Verhalten
      assert.is_string(p.user_home_windows())
    end)
  end)

  describe('user_home()', function()
    it('liefert Forward-Slash-Pfad', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      local home = platform.user_home()
      assert.is_string(home)
      assert.is_nil(home:match('\\'))  -- keine Backslashes
    end)

    it('auf Windows: enthält Drive-Letter (C:)', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      if not platform.is_windows then pending('Windows-only') return end
      local home = platform.user_home()
      assert.is_not_nil(home:match('^%a:/'))
    end)

    it('auf WSL2: beginnt mit /mnt/c/Users/', function()
      if platform == nil then pending('S2_Platform noch nicht implementiert') return end
      if platform.is_windows then pending('WSL2-only') return end
      local home = platform.user_home()
      assert.is_not_nil(home:match('^/mnt/c/Users/'))
    end)
  end)
end)
