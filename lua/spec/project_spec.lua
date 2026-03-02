-- lua/spec/project_spec.lua
-- Tests für lua/shared/project.lua
-- Verwendet Mocks für vim.fn.isdirectory und vim.fn.getcwd
-- Wird parallel zu S3_Project entwickelt

describe('project.lua', function()
  local project
  local original_isdirectory
  local original_getcwd

  before_each(function()
    -- Original-Funktionen sichern
    original_isdirectory = vim.fn.isdirectory
    original_getcwd = vim.fn.getcwd
    -- Modul-Cache leeren
    package.loaded['shared.project'] = nil
    package.loaded['shared.platform'] = nil
    local ok, result = pcall(require, 'shared.project')
    if ok then
      project = result
    else
      project = nil
    end
  end)

  after_each(function()
    -- Original-Funktionen wiederherstellen
    vim.fn.isdirectory = original_isdirectory
    vim.fn.getcwd = original_getcwd
    -- Modul-Cache leeren
    package.loaded['shared.project'] = nil
    package.loaded['shared.platform'] = nil
  end)

  describe('Verfügbarkeit', function()
    it('project Modul existiert nach S3_Project', function()
      if project == nil then
        pending('S3_Project noch nicht implementiert')
        return
      end
      assert.is_not_nil(project)
    end)
  end)

  describe('find_dcsre_root()', function()
    before_each(function()
      if project == nil then return end
      -- Standard-Mock: simuliere Verzeichnis-Struktur
      vim.fn.isdirectory = function(p)
        local dirs = {
          ['/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources'] = 1,
          ['C:/Users/Administrator/Documents/Work/Code2/DCSRE/Sources'] = 1,
        }
        return dirs[p] or 0
      end
    end)

    it('findet DCSRE-Root via Pattern-Match', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      local result = project.find_dcsre_root('/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend/VDEK.DCSP.WebHost')
      assert.is_not_nil(result)
      assert.is_true(result:find('DCSRE') ~= nil)
    end)

    it('gibt nil zurück wenn kein DCSRE-Root gefunden', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      vim.fn.isdirectory = function(p) return 0 end
      local result = project.find_dcsre_root('/home/user/random/path')
      assert.is_nil(result)
    end)

    it('normalisiert Backslashes zu Forward-Slashes', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      vim.fn.isdirectory = function(p)
        return (p == 'C:/Users/Administrator/Documents/Work/Code2/DCSRE/Sources') and 1 or 0
      end
      local result = project.find_dcsre_root('C:\\Users\\Administrator\\Documents\\Work\\Code2\\DCSRE\\Sources\\Backend')
      assert.is_not_nil(result)
    end)

    it('findet Root auch bei tiefem Pfad via Aufwärts-Suche', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      vim.fn.isdirectory = function(p)
        return (p == '/mnt/c/DCSRE_Azure/Sources') and 1 or 0
      end
      local result = project.find_dcsre_root('/mnt/c/DCSRE_Azure/Sources/Backend/Project/Subdir')
      assert.is_not_nil(result)
    end)

    it('gibt nil zurück bei sehr kurzem Pfad', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      vim.fn.isdirectory = function(p) return 0 end
      local result = project.find_dcsre_root('/a')
      assert.is_nil(result)
    end)
  end)

  describe('detect()', function()
    it('erkennt CENCOCD Projekt', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      vim.fn.getcwd = function() return '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco/src' end
      project.detect()
      assert.equals('CENCOCD', vim.g.project_name)
    end)

    it('erkennt CENCOCD via Kluger im Pfad', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      vim.fn.getcwd = function() return '/mnt/c/Users/Administrator/Documents/Work/Kluger/anything' end
      project.detect()
      assert.equals('CENCOCD', vim.g.project_name)
    end)

    it('setzt UNKNOWN bei unbekanntem Projekt', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      vim.fn.getcwd = function() return '/home/user/random' end
      vim.fn.isdirectory = function(p) return 0 end
      project.detect()
      assert.equals('UNKNOWN', vim.g.project_name)
    end)

    it('setzt vim.g.project_git_base für CENCOCD', function()
      if project == nil then pending('S3_Project noch nicht implementiert') return end
      vim.fn.getcwd = function() return '/mnt/c/Users/Administrator/Documents/Work/Kluger/cencoco' end
      project.detect()
      assert.equals('origin/main', vim.g.project_git_base)
    end)
  end)
end)
