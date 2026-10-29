-- lua/shared/keybindings/git.lua
-- Git Keybindings: rp (Push), rP (Pull), rc (TFS Browser), git diff helper, Windows path
-- Lade-Voraussetzung: require('shared.core') muss bereits geladen sein (toggleterm, gitsigns etc.)

local platform = require('shared.platform')
local is_windows = platform.is_windows  -- Kompatibilität

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

-- ============================================================================
-- Branch-Review: JEDER Hunk vs Base-Branch, dateiuebergreifend navigierbar
-- ============================================================================
-- Problem: bei >100 geaenderten Dateien ist "durch den Diff gehen" von Hand nicht
-- machbar. gitsigns' ]c/[c springt nur INNERHALB einer Datei. Quickfix ist Vims
-- native dateiuebergreifende Navigationsstruktur -> ]q/[q laeuft ueber Dateigrenzen.
--
-- WARUM EIGENER PARSER statt gitsigns.setqflist('all') -- gemessen 2026-08-21 an
-- DCSRE (887 geaenderte Dateien, 601 davon auf der Platte):
--   1. gitsigns startet EINEN git-Prozess PRO Datei (`git show {base}:{datei}`)
--      und diffed in Lua: 18,7 s. Ein einziges `git diff` braucht 0,47 s.
--   2. gitsigns uebergibt die Eintraege als `filename`. Vim legte nur fuer die
--      ersten 285 von 610 Eintraegen einen Buffer an; die restlichen 325 hatten
--      bufnr=0 und `:cc` sprang sie NICHT an -- die halbe Liste war tot.
--      (Nicht MAX_PATH: der laengste Pfad im Repo hat 252 Zeichen.)
--      Hier wird stattdessen vim.fn.bufadd() benutzt -> jeder Eintrag hat einen
--      echten Buffer, BEVOR die Liste gesetzt wird.
--   3. gitsigns' interner Differ fasst Hunks anders zusammen (610 statt 1409).
--      `git diff` mit Standard-Kontext ist das, was auch der PR-Reviewer sieht.
--
-- BASE: Diff gegen die MERGE-BASE von base und HEAD, nicht gegen die Spitze von
-- base. Das haelt das Ergebnis stabil, wenn origin/develop weitergelaufen ist:
-- fremde Commits erscheinen dann NICHT als deine Aenderungen. Zwei-Punkt gegen die
-- Merge-Base heisst ausserdem: uncommittete Aenderungen sind mit drin.
local function build_branch_hunk_qflist()
  local base = vim.g.project_git_base or 'origin/develop'
  local cwd = vim.fn.getcwd()

  -- vim.system() statt vim.fn.systemlist(): kein Shell dazwischen. Damit sind
  -- Backslash-Pfade, Quoting und ein evtl. fehlkonfiguriertes 'shell'/'shellcmdflag'
  -- (z.B. shell=bash mit cmd-Flags) kein Thema mehr.
  local function git(args)
    local cmd = { 'git', '-C', cwd }
    vim.list_extend(cmd, args)
    local r = vim.system(cmd, { text = true }):wait()
    return vim.split(r.stdout or '', '\r?\n', { regex = true, trimempty = true }), r.code, r.stderr or ''
  end

  local mb_out, mb_err, mb_stderr = git({ 'merge-base', base, 'HEAD' })
  if mb_err ~= 0 or not mb_out[1] or mb_out[1] == '' then
    vim.notify(string.format('merge-base %s HEAD fehlgeschlagen (exit %s):\n%s\n(Base vorhanden? git fetch noetig?)',
      base, tostring(mb_err), mb_stderr), vim.log.levels.ERROR, { title = 'Branch-Review', timeout = 10000 })
    return nil
  end
  local mb = mb_out[1]

  local raw, derr, dstderr = git({ 'diff', '--no-color', mb })
  if derr ~= 0 then
    vim.notify(string.format('git diff fehlgeschlagen (exit %s):\n%s', tostring(derr), dstderr),
      vim.log.levels.ERROR, { title = 'Branch-Review', timeout = 10000 })
    return nil
  end

  local items, files = {}, {}
  local cur_buf, pending = nil, nil
  local n_deleted, n_missing, n_binary = 0, 0, 0

  local function flush()
    if pending then
      table.insert(items, pending)
      pending = nil
    end
  end

  -- Datei aus dem Diff aufnehmen; gibt die bufnr zurueck oder nil (+ zaehlt den Grund).
  local function open_target(rel)
    if not rel then
      n_deleted = n_deleted + 1
      return nil
    end
    local abs = cwd .. '/' .. rel
    if vim.fn.filereadable(abs) ~= 1 then
      n_missing = n_missing + 1
      return nil
    end
    local b = vim.fn.bufadd(abs)
    files[b] = true
    return b
  end

  -- Zustandsautomat statt reiner Praefix-Pruefung: eine INHALTS-Zeile kann selbst
  -- mit '+++ ' beginnen (hinzugefuegte Zeile, deren Text '++ ...' lautet). Nur
  -- innerhalb des Datei-Kopfes (nach 'diff --git', vor dem ersten '@@') gilt
  -- '+++ ' als Dateiname.
  local in_header = false

  for _, line in ipairs(raw) do
    if line:sub(1, 11) == 'diff --git ' then
      flush()
      in_header = true
      cur_buf = nil
    elseif in_header and line:sub(1, 13) == 'Binary files ' then
      -- Binaerdateien haben KEINEN Zeilendiff. Ohne diesen Zweig wuerden sie
      -- lautlos aus dem Review fallen (nachgewiesen 2026-08-21: keycloak.p12).
      local rel = line:match('^Binary files .* and b/(.+) differ$')
      local b = open_target(rel)
      if b then
        n_binary = n_binary + 1
        table.insert(items, {
          bufnr = b,
          lnum = 1,
          col = 1,
          text = 'Binary  geaendert (kein Zeilendiff - Inhalt manuell pruefen)',
        })
      end
      in_header = false
    elseif in_header and line:sub(1, 4) == '+++ ' then
      cur_buf = open_target(line:match('^%+%+%+ b/(.*)$'))
      in_header = false
    elseif not in_header and cur_buf and line:sub(1, 3) == '@@ ' then
      flush()
      local oc, ns, nc = line:match('^@@ %-%d+,?(%d*) %+(%d+),?(%d*) @@')
      if ns then
        oc = (oc == '') and 1 or tonumber(oc)
        nc = (nc == '') and 1 or tonumber(nc)
        local kind = (oc == 0) and 'Added' or (nc == 0) and 'Removed' or 'Changed'
        pending = {
          bufnr = cur_buf,
          lnum = math.max(tonumber(ns), 1),
          col = 1,
          text = string.format('%-7s %s', kind, line:match('^@@ (.-) @@') or ''),
        }
      end
    elseif pending then
      local c = line:sub(1, 1)
      if c == '+' or c == '-' then
        pending.text = pending.text .. ': ' .. vim.trim(line:sub(2))
        table.insert(items, pending)
        pending = nil
      end
    end
  end
  flush()

  return {
    items = items,
    nfiles = vim.tbl_count(files),
    base = base,
    mergebase = mb:sub(1, 8),
    n_deleted = n_deleted,
    n_missing = n_missing,
    n_binary = n_binary,
  }
end

-- <leader>qh -- [Q]uickfix [H]unks: Branch-Review starten.
-- Baut die Liste UND schaltet die gitsigns-Base auf den Base-Branch um, damit die
-- Zeichen im Gutter dasselbe zeigen wie die Liste. Zurueck in den Alltags-Modus
-- (uncommitted, Hunk-Staging) mit <leader>hB.
vim.keymap.set('n', '<leader>qh', function()
  local r = build_branch_hunk_qflist()
  if not r then return end

  if #r.items == 0 then
    vim.notify(string.format('Keine Hunks vs %s.', r.base), vim.log.levels.WARN, { title = 'Branch-Review' })
    return
  end

  vim.fn.setqflist({}, ' ', {
    items = r.items,
    title = string.format('Branch-Hunks vs %s (%s)', r.base, r.mergebase),
  })

  pcall(function()   -- Gutter auf dieselbe Base ziehen; die Liste haengt nicht davon ab
    local gs = require('gitsigns')
    gs.change_base(r.base, true)
    vim.g.gitsigns_branch_mode = true
  end)

  vim.cmd('copen')
  vim.cmd('cfirst')

  local extra = ''
  if r.n_deleted > 0 then
    extra = extra .. string.format('\n%d geloeschte Datei(en) NICHT in der Liste (nichts zum Anspringen)', r.n_deleted)
  end
  if r.n_missing > 0 then
    extra = extra .. string.format('\n%d Datei(en) nicht lesbar -- uebersprungen', r.n_missing)
  end
  if r.n_binary > 0 then
    extra = extra .. string.format('\n%d Binaerdatei(en) als Eintrag in Zeile 1 (kein Zeilendiff moeglich)', r.n_binary)
  end
  vim.notify(string.format('%d Hunks in %d Dateien vs %s (Merge-Base %s)\n]q / [q = naechster / vorheriger Hunk (ueber Dateigrenzen)\n<leader>hB = Gutter zurueck auf uncommitted%s',
    #r.items, r.nfiles, r.base, r.mergebase, extra),
    vim.log.levels.INFO, { title = 'Branch-Review', timeout = 12000 })
end, { desc = '[Q]uickfix: alle [H]unks vs Base-Branch (Branch-Review)' })

-- <leader>hC -- [H]unks fuer [C]ommits: wie qh, aber nur ab einer Commit-Auswahl.
-- Hashes eintippen (wie <leader>sDC); der AELTESTE davon bestimmt die Base = sein
-- Elternteil. Gitsigns-Gutter UND Quickfix messen dann gegen diese Base, also passen
-- ]c/[c und ]q/[q zu genau diesen Commits.
--
-- WARUM NICHT einfach sDC + hB: sDC laedt nur die Dateien, hB misst gegen origin/develop
-- (Branch-Achse). Spaetere Commits ueberschreiben, was ein frueher Commit getan hat --
-- der Hunk des gewaehlten Commits ist dann gegen develop gar nicht mehr sichtbar.
--
-- GRENZE: git diff/gitsigns vergleichen immer gegen den ARBEITSBAUM. Liegen zwischen dem
-- aeltesten Commit und HEAD weitere, nicht angegebene Commits, sind deren Aenderungen mit
-- drin (und uncommittete auch). Das wird als Warnung gemeldet, nicht verschwiegen.
-- Neue Dateien bleiben EIN Hunk -- daran aendert keine Base etwas.
--
-- build_branch_hunk_qflist bleibt unveraendert: sie liest vim.g.project_git_base und
-- bildet daraus die Merge-Base. Ist die Base ein Vorfahre von HEAD, ist die Merge-Base
-- die Base selbst -- also wird die Variable nur fuer den Aufruf umgebogen und danach
-- zurueckgesetzt.
-- prefill: sDC ruft diesen Callback mit den dort eingegebenen Hashes auf, damit man sie nicht
-- zweimal eintippt. Per Tastendruck kommt kein Argument -> normale Abfrage.
vim.keymap.set('n', '<leader>hC', function(prefill)
  local base = vim.g.project_git_base or 'origin/develop'
  local cwd = vim.fn.getcwd()

  local function git(args)
    local cmd = { 'git', '-C', cwd }
    vim.list_extend(cmd, args)
    local r = vim.system(cmd, { text = true }):wait()
    return vim.split(r.stdout or '', '\r?\n', { regex = true, trimempty = true }), r.code, r.stderr or ''
  end

  local input = type(prefill) == 'string' and prefill
    or require('shared.input').multiline({ prompt = 'Commit-Hashes (Leerzeichen/Komma/Zeilen): ' })
  if not input or input:gsub('%s', '') == '' then
    vim.notify('Abgebrochen', vim.log.levels.INFO)
    return
  end

  -- Branch-Commits, aelteste zuerst. Daran wird jeder Hash gemessen: so faellt ein Hash
  -- aus develop sofort auf. MERGE-Commits gehoeren dazu (gemessen 2026-10-12: ein
  -- Merge-Commit des eigenen Branches wurde mit --no-merges faelschlich als "nicht im Branch"
  -- abgelehnt) -- --parents liefert "sha parent1 [parent2]", daran erkennt man sie.
  local rl, berr, bstderr = git({ 'rev-list', '--reverse', '--topo-order', '--parents', base .. '..HEAD' })
  if berr ~= 0 then
    vim.notify(string.format('rev-list %s..HEAD fehlgeschlagen:\n%s', base, bstderr),
      vim.log.levels.ERROR, { title = 'hC', timeout = 10000 })
    return
  end
  local branch, pos, is_merge = {}, {}, {}
  for i, line in ipairs(rl) do
    local fields = vim.split(line, '%s+', { trimempty = true })
    branch[i] = fields[1]
    pos[fields[1]] = i
    is_merge[fields[1]] = #fields > 2
  end

  local wanted, unknown, outside = {}, {}, {}
  local seen = {}
  for tok in input:gmatch('[^%s,;]+') do
    local out, code = git({ 'rev-parse', '--verify', '--quiet', tok })
    local full = out[1]
    if code ~= 0 or not full then
      table.insert(unknown, tok)
    elseif not pos[full] then
      table.insert(outside, tok)
    elseif not seen[full] then
      seen[full] = true
      table.insert(wanted, full)
    end
  end

  if #unknown > 0 or #outside > 0 then
    local msg = {}
    if #unknown > 0 then table.insert(msg, 'Unbekannt: ' .. table.concat(unknown, ', ')) end
    if #outside > 0 then
      table.insert(msg, string.format('Nicht im Branch (%s..HEAD): %s', base, table.concat(outside, ', ')))
    end
    vim.notify(table.concat(msg, '\n'), vim.log.levels.ERROR, { title = 'hC', timeout = 8000 })
    return
  end

  local oldest_i = #branch
  for _, sha in ipairs(wanted) do
    if pos[sha] < oldest_i then oldest_i = pos[sha] end
  end
  local oldest = branch[oldest_i]

  -- '~1' statt '^': git laeuft hier ohne Shell, aber '~' ist auch ueber cmd.exe unkritisch.
  local par, perr, pstderr = git({ 'rev-parse', '--verify', oldest .. '~1' })
  if perr ~= 0 or not par[1] then
    vim.notify(string.format('Elternteil von %s nicht ermittelbar (Root-Commit?):\n%s', oldest:sub(1, 9), pstderr),
      vim.log.levels.ERROR, { title = 'hC', timeout = 8000 })
    return
  end
  local parent = par[1]

  local saved = vim.g.project_git_base
  vim.g.project_git_base = parent
  local ok, r = pcall(build_branch_hunk_qflist)
  vim.g.project_git_base = saved
  if not ok then
    vim.notify('hC: ' .. tostring(r), vim.log.levels.ERROR, { title = 'hC', timeout = 10000 })
    return
  end
  if not r then return end

  -- Nur Hunks aus Dateien, die die gewaehlten Commits selbst anfassen. Der Diff ab dem
  -- Elternteil enthaelt sonst alles bis heute: nicht gewaehlte Commits UND jeden
  -- "develop into feature"-Merge (gemessen 2026-10-29, LaneC: 3 Commits/35 Dateien ->
  -- ungefiltert 213 Dateien). Der Gutter bleibt ungefiltert (gitsigns kennt nur eine Base).
  local function norm(p) return (p:gsub('\\', '/'):lower()) end
  local touched = {}
  for _, sha in ipairs(wanted) do
    local names = git({ 'show', '--name-only', '--format=', sha })
    for _, rel in ipairs(names) do touched[norm(cwd .. '/' .. rel)] = true end
  end
  local total_items, total_files = #r.items, r.nfiles
  local kept, kept_files = {}, {}
  for _, it in ipairs(r.items) do
    if touched[norm(vim.api.nvim_buf_get_name(it.bufnr))] then
      table.insert(kept, it)
      kept_files[it.bufnr] = true
    end
  end
  r.items, r.nfiles = kept, vim.tbl_count(kept_files)

  if #r.items == 0 then
    vim.notify(string.format('Keine Hunks ab %s~1 in den Dateien der gewaehlten Commits.', oldest:sub(1, 9)),
      vim.log.levels.WARN, { title = 'hC' })
    return
  end

  vim.fn.setqflist({}, ' ', {
    items = r.items,
    title = string.format('Hunks ab %s~1 (%d Commit(s) gewaehlt)', oldest:sub(1, 9), #wanted),
  })

  pcall(function()
    require('gitsigns').change_base(parent, true)
    vim.g.gitsigns_branch_mode = true   -- hB schaltet damit zurueck auf HEAD
  end)

  -- Nachzuegler: sDC oeffnet die Dateien unmittelbar vorher, gitsigns haengt sich verzoegert
  -- an. Wer beim change_base noch nicht im Cache war, hat die Base schon VORHER gelesen und
  -- behaelt HEAD -> 0 Hunks, kein Zeichen (gemessen 2026-10-29, LaneC: config.base = Elternteil,
  -- Buffer-Revision nil). Darum ein paar Sekunden nachsehen und die Base erneut setzen, solange
  -- ein angehaengter Buffer eine andere Revision traegt.
  local ok_cache, gs_cache = pcall(function() return require('gitsigns.cache').cache end)
  if ok_cache then
    local tries = 0
    local timer = vim.uv.new_timer()
    timer:start(500, 500, vim.schedule_wrap(function()
      tries = tries + 1
      -- Stop, sobald jemand anders die globale Base umgestellt hat (hB, qh/hO, neues hC)
      -- oder nach 15 s -- sonst wuerde dieser Timer deren Base zurueckdrehen.
      local cur = require('gitsigns.config').config.base
      if cur ~= parent or tries > 30 then
        timer:stop(); timer:close()
        return
      end
      local wrong = false
      for _, bc in pairs(gs_cache) do
        if bc.git_obj and bc.git_obj.revision ~= parent then wrong = true; break end
      end
      if wrong then pcall(require('gitsigns').change_base, parent, true) end
    end))
  end

  vim.cmd('copen')
  vim.cmd('cfirst')

  -- Luecken: alles zwischen dem aeltesten gewaehlten Commit und HEAD, das nicht angegeben wurde.
  -- Merge-Commits zaehlen nicht als Luecke: man gibt sie nicht "als Arbeit" an, ihre
  -- eigene Aenderung ist leer; der Inhalt steckt in den Commits, die sie zusammenfuehren.
  local gap = 0
  for i = oldest_i, #branch do
    if not seen[branch[i]] and not is_merge[branch[i]] then gap = gap + 1 end
  end
  local extra = ''
  if total_files > r.nfiles then
    extra = string.format('\n(begrenzt auf die Dateien der Commits -- ungefiltert waeren es %d Hunks in %d Dateien)',
      total_items, total_files)
  end
  if gap > 0 then
    extra = extra .. string.format('\nWARNUNG: %d Commit(s) im Bereich nicht angegeben -- in diesen Dateien koennen deren Aenderungen mit drin sein', gap)
  end
  if r.n_deleted > 0 then
    extra = extra .. string.format('\n%d geloeschte Datei(en) NICHT in der Liste', r.n_deleted)
  end
  if r.n_binary > 0 then
    extra = extra .. string.format('\n%d Binaerdatei(en) als Eintrag in Zeile 1', r.n_binary)
  end
  vim.notify(string.format('%d Hunks in %d Dateien ab %s~1\n]c/[c = in der Datei, ]q/[q = ueber Dateigrenzen\n<leader>hB = Gutter zurueck auf uncommitted%s',
    #r.items, r.nfiles, oldest:sub(1, 9), extra),
    gap > 0 and vim.log.levels.WARN or vim.log.levels.INFO, { title = 'hC', timeout = 12000 })
end, { desc = '[H]unks fuer [C]ommits: Gutter + Quickfix ab Elternteil des aeltesten gewaehlten Commits' })

-- <leader>hO -- [H]unks [O]hne Auswahl: das Gegenstueck zu hC ohne Commit-Eingabe = ALLE
-- Hunks des Branches (genau die Dateien, die sDo laedt), Gutter + Quickfix. Ruft den
-- bestehenden qh-Callback auf statt ihn zu kopieren -- qh bleibt damit unangetastet.
vim.keymap.set('n', '<leader>hO', function()
  local m = vim.fn.maparg('<leader>qh', 'n', false, true)
  if type(m) == 'table' and m.callback then
    m.callback()
  else
    vim.notify('<leader>qh nicht gemappt', vim.log.levels.ERROR, { title = 'hO' })
  end
end, { desc = '[H]unks: alle [O]ffenen vs Base-Branch (wie qh, Gegenstueck zu hC ohne Commit-Auswahl)' })

-- <leader>sDf -- [D]irty [F]ahrplan / Episoden-Modus: Dateien in LESE-REIHENFOLGE.
-- Eingabe wie bei sDC (Komma/Leerzeichen/Zeilen). Auch ein ganzer kopierter Abschnitt
-- "Quelldateien -- der rote Faden" geht: nur Tokens mit Dateiendung zaehlen, Prosa faellt raus.
-- Namen werden gegen `git ls-files` aufgeloest (Endung des Pfads, ohne Gross/Klein), also reicht
-- der Dateiname; ein Pfadteil davor macht ihn eindeutig.
-- Die Dateien werden als Buffer geladen (wie sDC), auch ohne Hunk-Liste.
-- Die Hunks kommen aus der juengsten Hunk-Liste im Quickfix-Verlauf (hC/sDC, qh/hO) -- auch wenn
-- danach eine Diagnose-Liste per <C-q> drueberkam. Neue Liste = nur diese Dateien, in dieser
-- Reihenfolge, je Datei ihre Hunks; Datei ohne Hunk bekommt einen Eintrag in Zeile 1.
-- ]q geht so die Episode Datei fuer Datei, Hunk fuer Hunk durch. Die Hunk-Liste bleibt im Verlauf
-- (:colder).
vim.keymap.set('n', '<leader>sDf', function()
  local function git(args)
    local cmd = { 'git', '-C', vim.fn.getcwd() }
    vim.list_extend(cmd, args)
    local r = vim.system(cmd, { text = true }):wait()
    return vim.split(r.stdout or '', '\r?\n', { regex = true, trimempty = true }), r.code
  end
  local top_out, top_code = git({ 'rev-parse', '--show-toplevel' })
  if top_code ~= 0 or not top_out[1] then
    vim.notify('Kein git-Repo im aktuellen Ordner', vim.log.levels.ERROR, { title = 'sDf' })
    return
  end
  local top = top_out[1]:gsub('\\', '/')

  local input = require('shared.input').multiline({ prompt = 'Dateien in Lese-Reihenfolge (Komma/Leerzeichen/Zeilen): ' })
  if not input or input:gsub('%s', '') == '' then
    vim.notify('Abgebrochen', vim.log.levels.INFO)
    return
  end

  -- Tokens mit bekannter Datei-Endung; Satzzeichen am Rand und ":Zeile" ab
  -- ("Foo.cs," / "(Foo.cs)" / "Foo.cs:197"). Nur feste Endungen, damit Prosa wie "z.B." oder
  -- "dbContext.Pruefberichte" nicht als Datei gilt.
  local exts = { cs = 1, csproj = 1, ts = 1, html = 1, scss = 1, css = 1, json = 1, md = 1, sql = 1,
    xml = 1, lua = 1, js = 1, yml = 1, yaml = 1, feature = 1, props = 1, targets = 1, ps1 = 1, sh = 1 }
  local tokens = {}
  for tok in input:gmatch('[^%s,;]+') do
    tok = tok:gsub('^[%(%[\'"`]+', ''):gsub(':%d.*$', ''):gsub('[%)%]\'"`:%.]+$', '')
    local ext = tok:match('[%w_%-]%.(%a%w*)$')
    if ext and exts[ext:lower()] and not tok:match('^%a+://') then
      table.insert(tokens, (tok:gsub('\\', '/')))
    end
  end
  if #tokens == 0 then
    vim.notify('Keine Dateinamen in der Eingabe gefunden', vim.log.levels.WARN, { title = 'sDf' })
    return
  end

  local tracked = git({ '-C', top, 'ls-files' })
  local function norm(p) return (p:gsub('\\', '/'):lower()) end
  local files, seen, missing, ambiguous = {}, {}, {}, {}
  for _, tok in ipairs(tokens) do
    local hits = {}
    local t = norm(tok)
    if t:match('^%a:/') then
      -- absoluter Pfad: nur der Teil im Repo zaehlt
      local rel = t:sub(#norm(top) + 2)
      if t:sub(1, #norm(top)) == norm(top) then t = rel end
    end
    for _, rel in ipairs(tracked) do
      local r = norm(rel)
      if r == t or r:sub(-(#t + 1)) == '/' .. t then table.insert(hits, rel) end
    end
    if #hits == 0 then
      table.insert(missing, tok)
    else
      if #hits > 1 then table.insert(ambiguous, string.format('%s (%d)', tok, #hits)) end
      for _, rel in ipairs(hits) do
        if not seen[rel] then
          seen[rel] = true
          table.insert(files, rel)
        end
      end
    end
  end
  if #files == 0 then
    vim.notify('Keine der Dateien im Repo gefunden: ' .. table.concat(missing, ', '),
      vim.log.levels.ERROR, { title = 'sDf' })
    return
  end

  -- Dateien als Buffer laden, exakt wie sDo/sDC: 'silent edit', nicht badd/bufload -- letztere
  -- feuern kein FileType, also kein LSP/gitsigns. Nur genau diese Dateien offen: vorher <leader>bD.
  local original = vim.api.nvim_get_current_buf()
  local opened = 0
  for _, rel in ipairs(files) do
    if pcall(vim.cmd, 'silent edit ' .. vim.fn.fnameescape(top .. '/' .. rel)) then opened = opened + 1 end
  end
  if vim.api.nvim_buf_is_valid(original) and vim.api.nvim_buf_get_name(original) ~= '' then
    vim.api.nvim_set_current_buf(original)
  end

  -- Juengste Hunk-Liste im Quickfix-Verlauf suchen (Titel von hC bzw. qh/hO).
  local hunk_items, hunk_title = nil, nil
  local last = vim.fn.getqflist({ nr = '$' }).nr
  for nr = last, 1, -1 do
    local l = vim.fn.getqflist({ nr = nr, title = 0, items = 0 })
    if l.title and (l.title:match('^Hunks ab ') or l.title:match('^Branch%-Hunks ')) then
      hunk_items, hunk_title = l.items, l.title
      break
    end
  end

  local by_file = {}
  for _, it in ipairs(hunk_items or {}) do
    local k = norm(vim.api.nvim_buf_get_name(it.bufnr))
    by_file[k] = by_file[k] or {}
    table.insert(by_file[k], it)
  end

  local items, n_hunks, no_hunk = {}, 0, 0
  for i, rel in ipairs(files) do
    local abs = top .. '/' .. rel
    local list = by_file[norm(abs)]
    if list and #list > 0 then
      table.sort(list, function(a, b) return a.lnum < b.lnum end)
      for _, it in ipairs(list) do
        table.insert(items, { bufnr = it.bufnr, lnum = it.lnum, col = it.col,
          text = string.format('[%d] %s', i, it.text) })
        n_hunks = n_hunks + 1
      end
    else
      no_hunk = no_hunk + 1
      table.insert(items, { bufnr = vim.fn.bufadd(abs), lnum = 1, col = 1,
        text = string.format('[%d] (keine Hunks in der Liste)', i) })
    end
  end

  vim.fn.setqflist({}, ' ', {
    items = items,
    title = string.format('Lese-Reihenfolge: %d Dateien, %d Hunks', #files, n_hunks),
  })
  vim.cmd('copen')
  vim.cmd('cfirst')

  local msg = { string.format('%d Dateien als Buffer geladen, %d Hunks in Lese-Reihenfolge\n]q / [q = weiter / zurueck, :colder = vorige Liste', opened, n_hunks) }
  if not hunk_items then
    table.insert(msg, 'KEINE Hunk-Liste im Verlauf -- erst sDC/hC oder hO, dann sDf. Jetzt nur Zeile 1 je Datei.')
  else
    table.insert(msg, 'Hunks aus: ' .. hunk_title)
  end
  if no_hunk > 0 and hunk_items then table.insert(msg, no_hunk .. ' Datei(en) ohne Hunk -- Eintrag in Zeile 1') end
  if #missing > 0 then table.insert(msg, 'Nicht gefunden: ' .. table.concat(missing, ', ')) end
  if #ambiguous > 0 then table.insert(msg, 'Mehrdeutig (alle genommen): ' .. table.concat(ambiguous, ', ')) end
  vim.notify(table.concat(msg, '\n'),
    (#missing > 0 or not hunk_items) and vim.log.levels.WARN or vim.log.levels.INFO,
    { title = 'sDf', timeout = 12000 })
end, { desc = '[S]earch [D]irty [F]ahrplan: Dateien in Lese-Reihenfolge -> Quickfix mit ihren Hunks' })

-- ]q / [q -- dateiuebergreifende Quickfix-Navigation mit Wrap.
-- Das ist die eigentliche Review-Bewegung: ein Tastendruck = naechste Aenderung,
-- egal ob sie in dieser Datei oder in der naechsten liegt. Gilt fuer JEDE
-- Quickfix-Liste, also auch fuer <leader>qd / <leader>qD.
local function qf_nav(forward)
  if vim.fn.getqflist({ size = 0 }).size == 0 then
    vim.notify('Quickfix-Liste ist leer (<leader>qh baut die Branch-Hunk-Liste)', vim.log.levels.INFO)
    return
  end
  local step = forward and vim.cmd.cnext or vim.cmd.cprevious
  local wrap = forward and vim.cmd.cfirst or vim.cmd.clast
  if not pcall(step) then pcall(wrap) end
end

vim.keymap.set('n', ']q', function() qf_nav(true) end, { desc = 'Next [q]uickfix entry (cross-file, wrap)' })
vim.keymap.set('n', '[q', function() qf_nav(false) end, { desc = 'Previous [q]uickfix entry (cross-file, wrap)' })

-- Quickfix: Show dirty files in current branch (vs upstream)
vim.keymap.set('n', '<leader>qd', function()
  git_diff_to_quickfix('@{upstream}', 'vs upstream')
end, { desc = '[Q]uickfix [d]irty files (vs upstream)' })

-- Quickfix: Show changed files vs project base branch (auto-detects project)
vim.keymap.set('n', '<leader>qD', function()
  git_diff_to_quickfix(vim.g.project_git_base, 'vs ' .. vim.g.project_git_base .. ' (' .. vim.g.project_name .. ')')
end, { desc = '[Q]uickfix vs [D]evelop/Main (project base)' })

-- Copy Windows path to clipboard
vim.keymap.set('n', '<leader>ypw', function()
  local current_file = vim.fn.expand('%:p')
  local windows_path

  if vim.fn.has('win32') == 1 then
    -- Windows Native: just normalize slashes
    windows_path = current_file:gsub('/', '\\')
  else
    -- WSL2: Convert /mnt/c/... to C:\...
    windows_path = current_file:gsub('/mnt/c/', 'C:\\'):gsub('/', '\\')
  end

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
end, { desc = '[R]un [C]ommit | Open in TFS browser (from clipboard)' })

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

  -- Open in Chrome new window (via PowerShell for both WSL2 and Windows)
  local cmd = string.format([[powershell.exe -Command "Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--new-window', '%s'"]], url)
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
end, { desc = '[R]un [P]ush | git push (Windows VPN)' })

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
end, { desc = '[R]un [P]ull | git pull (Windows VPN)' })

-- Run .claude/ setup script (copies reusable agents/commands/scripts from OmniCommand)
-- Run Swagger: Generate swagger and client via PowerShell script (DCSRE only)
vim.keymap.set('n', '<leader>rS', function()
  if vim.g.project_name ~= 'DCSRE' then
    vim.notify('Swagger generation only available for DCSRE', vim.log.levels.WARN)
    return
  end
  local root = vim.g.project_root_windows
  if not root then
    vim.notify('Could not determine project root', vim.log.levels.ERROR)
    return
  end
  -- Eigenes Skript statt generate-swagger-and-client.ps1 (gemessen 2026-10-12, Lane D): dessen
  -- `docker run` haengt, sobald Docker Desktops Standard-Bridge-Netz haengt -- der Container
  -- bleibt auf "Created" stehen und startet nie. Der Generator braucht kein Netzwerk;
  -- mit `--network none` laeuft derselbe Aufruf in ~7 s durch. Die Schritte und Parameter sind
  -- 1:1 die der Repo-Skripte (generate-swagger.ps1 wird UNVERAENDERT aufgerufen, der Client-Teil
  -- ist generate-api-client.ps1 mit dem einen Zusatz). Das Repo-Skript bleibt unangetastet.
  local script = [=[
$ErrorActionPreference = 'Stop'
$root        = '@@ROOT@@'
$tools       = Join-Path $root 'Sources\Tools'
$base        = Join-Path $root 'Sources'
$clientRel   = 'Frontend/libs/shared/client/src/lib/api-client'
$clientDir   = Join-Path $base $clientRel
$swaggerJson = Join-Path $base 'Api\swagger.json'

Write-Host 'Generiere Swagger JSON...'
& (Join-Path $tools 'generate-swagger.ps1')

if (-not (Test-Path $swaggerJson)) { throw "Swagger-Datei nicht gefunden: $swaggerJson" }

Write-Host ''
Write-Host 'Generiere API Client (docker run --network none)...'
if (Test-Path $clientDir) { Remove-Item -Recurse -Force $clientDir }
New-Item -ItemType Directory -Path $clientDir | Out-Null

docker run --rm --network none -v "${base}:/local" openapitools/openapi-generator-cli:latest generate -g typescript-angular -i /local/Api/swagger.json -o "/local/$clientRel" --additional-properties=supportsES6=true,ngVersion=16.0.0
if ($LASTEXITCODE -ne 0) { throw 'Fehler beim Generieren des Angular Clients.' }

Write-Host ''
Write-Host 'Alles erfolgreich erzeugt!'
]=]
  script = script:gsub('@@ROOT@@', function() return root end)

  local script_path = (os.getenv('TEMP') or vim.fn.stdpath('cache')):gsub('\\', '/') .. '/rS-generate.ps1'
  local fh, err = io.open(script_path, 'w')
  if not fh then
    vim.notify('rS: Skript nicht schreibbar: ' .. tostring(err), vim.log.levels.ERROR)
    return
  end
  fh:write(script)
  fh:close()

  local Terminal = require('toggleterm.terminal').Terminal
  local swagger = Terminal:new({
    cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' .. script_path .. '"',
    direction = 'horizontal',
    close_on_exit = false,
  })
  swagger:toggle()
  vim.notify('[DCSRE] Generating Swagger & Client (docker --network none)...', vim.log.levels.INFO)
end, { desc = '[R]un [S]wagger (capital S) | Swagger + API-Client, docker mit --network none' })

vim.keymap.set('n', '<leader>rsc', function()
  local git_root = vim.fn.system('git rev-parse --show-toplevel'):gsub('%s+$', '')
  if vim.v.shell_error ~= 0 then
    vim.notify('Not in a git repository!', vim.log.levels.ERROR)
    return
  end
  -- Convert WSL path to Windows path for PowerShell
  local win_path = git_root:gsub('^/mnt/(%a)/', function(drive)
    return drive:upper() .. ':\\'
  end):gsub('/', '\\')
  local claude_dir = win_path .. '\\.claude'
  -- Konfigurabel via vim.g.dcsre_azure_script; Default: <USERPROFILE>\Documents\Work\Code2\DCSRE_Azure\...
  local script = vim.g.dcsre_azure_script
    or ((os.getenv('USERPROFILE') or 'C:\\Users\\Administrator')
        .. '\\Documents\\Work\\Code2\\DCSRE_Azure\\OmniCommand\\.claude\\new-research-project.ps1')
  local Terminal = require('toggleterm.terminal').Terminal
  local setup = Terminal:new({
    cmd = 'powershell.exe -ExecutionPolicy Bypass -File "' .. script .. '" -TargetPath "' .. win_path .. '"; pause',
    direction = 'horizontal',
    close_on_exit = false,
  })
  setup:toggle()
  vim.notify('.claude/ Setup gestartet → ' .. win_path, vim.log.levels.INFO)
end, { desc = '[R]un [S]cript [C]laude | new-research-project.ps1' })

-- Claude Archive Sync: AgentsArchive\.claude_DCSRE/.claude_CenCoCo → Projekt-Root\.claude
vim.keymap.set('n', '<leader>rca', function()
  require('shared.claude_sync').sync_with_notify()
end, { desc = '[R]un [C]laude [A]rchive sync | AgentsArchive→Projekt .claude (DCSRE/CenCoCo)' })
