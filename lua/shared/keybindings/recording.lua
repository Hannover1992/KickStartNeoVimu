-- lua/shared/keybindings/recording.lua
-- Screen Recording: ffmpeg gdigrab → MKV → GIF → Clipboard (Datei-Referenz)
-- <leader>rrR  Start Recording (Monitor wo der Cursor ist → recordings/<timestamp>.mkv)
-- <leader>rrS  Stop Recording, Konvertierung zu GIF, GIF-Datei in Zwischenablage
--
-- Output-Verzeichnis: <USERPROFILE>/Recordings/
-- Format MKV waehrend Aufnahme (robust bei abruptem Beenden), GIF nach Stop.
-- Clipboard enthaelt nach Stop die GIF-Datei (Set-Clipboard -Path), pasten in
-- Slack/Discord/Outlook fuegt das GIF als Anhang ein.
--
-- Monitor-Detection: Cursor-Position via System.Windows.Forms.Cursor::Position,
-- dann Screen.FromPoint(cursor).Bounds → x,y,w,h. Fallback bei Fehler: full desktop.

local platform = require('shared.platform')

local function ensure_dir(dir)
  if vim.fn.isdirectory(dir) == 0 then
    vim.fn.mkdir(dir, 'p')
  end
end

local function recordings_dir()
  local dir = platform.user_home() .. '/Recordings'
  ensure_dir(dir)
  return dir
end

local function timestamp()
  return os.date('rec_%Y-%m-%d_%H%M%S')
end

-- Ermittelt Bounds des Monitors auf dem der Maus-Cursor gerade ist.
-- WICHTIG: Bewusst NICHT DPI-aware! ffmpeg gdigrab arbeitet in logischen Pixeln
-- (DPI-unaware durch GDI), also muessen Bounds + Cursor-Coord auch logisch sein,
-- damit -offset/-video_size matchen. DPI-Aware = Region geschnitten/falsch.
-- Returns: x, y, w, h (logische Pixel) ODER nil bei Fehler.
local function get_current_monitor_bounds()
  local ps_cmd =
    'Add-Type -AssemblyName System.Windows.Forms; ' ..
    '$p = [System.Windows.Forms.Cursor]::Position; ' ..
    '$s = [System.Windows.Forms.Screen]::FromPoint($p); ' ..
    '$b = $s.Bounds; ' ..
    "Write-Output ('{0} {1} {2} {3}' -f $b.X, $b.Y, $b.Width, $b.Height)"
  local out = vim.fn.system({'powershell', '-NoProfile', '-Command', ps_cmd})
  out = out:gsub('%s+$', '')
  local x, y, w, h = out:match('(-?%d+)%s+(-?%d+)%s+(%d+)%s+(%d+)')
  if x and y and w and h then
    return tonumber(x), tonumber(y), tonumber(w), tonumber(h)
  end
  return nil
end

-- Liefert die Bounds der GESAMTEN Virtual-Screen-Spanne in PHYSISCHEN Pixeln.
-- Bei DCSRE-Setup (Acer 4K + 2x Portrait): in physisch nochmal groesser als 6360x3440.
-- ffmpeg gdigrab kann auch negative offsets — kapiert alle Monitore gleichzeitig.
-- Returns: x, y, w, h (physische Pixel)
local function get_virtual_screen_bounds()
  local ps_cmd = [[
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class DpiH2 { [DllImport("user32.dll", SetLastError=true)] public static extern IntPtr SetProcessDpiAwarenessContext(IntPtr v); }
'@
try { [DpiH2]::SetProcessDpiAwarenessContext([IntPtr]-4) | Out-Null } catch {}
Add-Type -AssemblyName System.Windows.Forms
$v = [System.Windows.Forms.SystemInformation]::VirtualScreen
Write-Output ('{0} {1} {2} {3}' -f $v.X, $v.Y, $v.Width, $v.Height)
]]
  local out = vim.fn.system({'powershell', '-NoProfile', '-Command', ps_cmd})
  out = out:gsub('%s+$', '')
  local x, y, w, h = out:match('(-?%d+)%s+(-?%d+)%s+(%d+)%s+(%d+)')
  if x and y and w and h then
    return tonumber(x), tonumber(y), tonumber(w), tonumber(h)
  end
  return nil
end

-- Liefert die Bounds des PRIMARY-Monitors (Hauptbildschirm) in PHYSISCHEN Pixeln.
-- Bei DCSRE: Acer XV273K = 3840x2160 (4K) physisch, aber Windows scaliert auf 150%
-- = 2560x1440 logisch. Wir brauchen PHYSISCH damit ffmpeg gdigrab (DPI-aware via
-- Registry-Compat-Flag '~ HIGHDPIAWARE') den vollen 4K-Bereich kapturen kann.
-- Returns: x, y, w, h (physische Pixel)
local function get_primary_monitor_bounds()
  local ps_cmd = [[
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class DpiH { [DllImport("user32.dll", SetLastError=true)] public static extern IntPtr SetProcessDpiAwarenessContext(IntPtr v); }
'@
try { [DpiH]::SetProcessDpiAwarenessContext([IntPtr]-4) | Out-Null } catch {}
Add-Type -AssemblyName System.Windows.Forms
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
Write-Output ('{0} {1} {2} {3}' -f $b.X, $b.Y, $b.Width, $b.Height)
]]
  local out = vim.fn.system({'powershell', '-NoProfile', '-Command', ps_cmd})
  out = out:gsub('%s+$', '')
  local x, y, w, h = out:match('(-?%d+)%s+(-?%d+)%s+(%d+)%s+(%d+)')
  if x and y and w and h then
    return tonumber(x), tonumber(y), tonumber(w), tonumber(h)
  end
  return nil
end

-- Zeigt ein transparentes Vollbild-Overlay ueber alle Monitore.
-- User zieht mit der Maus ein Rechteck, ffmpeg nimmt nur diese Region auf.
-- ESC bricht die Auswahl ab.
-- WICHTIG: KEIN SetProcessDPIAware! ffmpeg gdigrab arbeitet in LOGISCHEN
-- (skalierten) Pixeln. Wenn WinForms physische Coords meldet, kapt gdigrab
-- den falschen Bereich. Beide Seiten muessen das gleiche Koord-System nutzen.
-- Returns: x, y, w, h (logische Pixel) ODER nil bei Abbruch/Fehler.
local function get_user_selected_rect()
  local script_path = vim.fn.tempname() .. '.ps1'
  local script = [[
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$vb = [System.Windows.Forms.SystemInformation]::VirtualScreen
$form = New-Object Windows.Forms.Form
$form.StartPosition = 'Manual'
$form.SetBounds($vb.X, $vb.Y, $vb.Width, $vb.Height)
$form.FormBorderStyle = 'None'
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.BackColor = [System.Drawing.Color]::Black
$form.Opacity = 0.30
$form.Cursor = [System.Windows.Forms.Cursors]::Cross
$form.KeyPreview = $true

$script:sp = $null
$script:ep = $null
$script:dragging = $false
$script:result = 'CANCELLED'

$form.Add_MouseDown({
    $script:sp = $_.Location
    $script:ep = $_.Location
    $script:dragging = $true
})
$form.Add_MouseMove({
    if ($script:dragging) {
        $script:ep = $_.Location
        $form.Invalidate()
    }
})
$form.Add_MouseUp({
    if ($script:dragging -and $script:sp) {
        $script:ep = $_.Location
        $script:dragging = $false
        $x = [Math]::Min($script:sp.X, $script:ep.X) + $vb.X
        $y = [Math]::Min($script:sp.Y, $script:ep.Y) + $vb.Y
        $w = [Math]::Abs($script:ep.X - $script:sp.X)
        $h = [Math]::Abs($script:ep.Y - $script:sp.Y)
        $w = $w - ($w % 2)
        $h = $h - ($h % 2)
        if ($w -gt 8 -and $h -gt 8) {
            $script:result = "$x $y $w $h"
        }
        $form.Close()
    }
})
$form.Add_Paint({
    if ($script:dragging -and $script:sp -and $script:ep) {
        $g = $_.Graphics
        $rx = [Math]::Min($script:sp.X, $script:ep.X)
        $ry = [Math]::Min($script:sp.Y, $script:ep.Y)
        $rw = [Math]::Abs($script:ep.X - $script:sp.X)
        $rh = [Math]::Abs($script:ep.Y - $script:sp.Y)
        $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::Red, 2)
        $g.DrawRectangle($pen, $rx, $ry, $rw, $rh)
        $pen.Dispose()
    }
})
$form.Add_KeyDown({
    if ($_.KeyCode -eq 'Escape') {
        $script:result = 'CANCELLED'
        $form.Close()
    }
})

[void]$form.ShowDialog()
Write-Output $script:result
]]
  local f = io.open(script_path, 'w')
  if not f then return nil end
  f:write(script)
  f:close()

  local out = vim.fn.system({
    'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
    '-File', script_path,
  })
  pcall(os.remove, script_path)
  out = (out or ''):gsub('%s+$', '')

  if out == '' or out:match('^CANCELLED') then
    return nil
  end
  local x, y, w, h = out:match('(-?%d+)%s+(-?%d+)%s+(%d+)%s+(%d+)')
  if x and y and w and h then
    return tonumber(x), tonumber(y), tonumber(w), tonumber(h)
  end
  return nil
end

-- Hilfsfunktion: Sammelt stderr-Output in vim.g.recording_stderr (cap 50 Zeilen)
local function on_recording_stderr(_, data)
  if not data then return end
  vim.g.recording_stderr = vim.g.recording_stderr or {}
  for _, line in ipairs(data) do
    if line and line ~= '' then
      table.insert(vim.g.recording_stderr, line)
      if #vim.g.recording_stderr > 50 then
        table.remove(vim.g.recording_stderr, 1)
      end
    end
  end
end

local function on_recording_exit(_, code)
  vim.schedule(function()
    -- 0 = clean (q), 1/130/143/255 = SIGTERM via jobstop — Datei wird oft korrupt sein
    -- aber wir kuemmern uns drum bei rrS (stderr-tail anzeigen wenn MKV 0 KB)
    if code ~= 0 and code ~= 255 and code ~= 130 and code ~= 1 and code ~= 143 then
      vim.notify('ffmpeg exit code ' .. code, vim.log.levels.WARN)
    end
  end)
end

-- Helper: gemeinsamer Job-Start fuer Recording (vermeidet Code-Duplikation)
local function start_recording(x, y, w, h, region_label)
  local stamp = timestamp()
  local mkv = recordings_dir() .. '/' .. stamp .. '.mkv'
  local mkv_win = mkv:gsub('/', '\\')
  local args = { 'ffmpeg', '-y', '-f', 'gdigrab', '-framerate', '15',
    '-offset_x', tostring(x), '-offset_y', tostring(y),
    '-video_size', w .. 'x' .. h,
    '-i', 'desktop',
    '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
    mkv_win,
  }
  vim.g.recording_stderr = {}
  local job_id = vim.fn.jobstart(args, {
    on_stderr = on_recording_stderr,
    on_exit = on_recording_exit,
  })
  if job_id <= 0 then
    vim.notify('ffmpeg-Start fehlgeschlagen!', vim.log.levels.ERROR)
    return
  end
  vim.g.recording_job = job_id
  vim.g.recording_mkv = mkv
  vim.notify('Recording: ' .. region_label .. ' → ' .. stamp .. '.mkv', vim.log.levels.INFO)
end

-- <leader>rrR — PRIMARY Monitor (deterministisch, immer der Mittlere mit DCSRE-Arbeit)
vim.keymap.set('n', '<leader>rrR', function()
  if vim.g.recording_job and vim.g.recording_job > 0 then
    vim.notify('Recording laeuft bereits (job ' .. vim.g.recording_job .. ')', vim.log.levels.WARN)
    return
  end
  if vim.fn.executable('ffmpeg') == 0 then
    vim.notify('ffmpeg nicht im PATH!', vim.log.levels.ERROR)
    return
  end
  local x, y, w, h = get_primary_monitor_bounds()
  if not (x and w and w > 0 and h > 0) then
    vim.notify('Konnte PRIMARY-Monitor nicht ermitteln.', vim.log.levels.ERROR)
    return
  end
  start_recording(x, y, w, h, string.format('PRIMARY %dx%d @ %d,%d', w, h, x, y))
end, { desc = '[R]un [R]ecord sta[R]t (PRIMARY Monitor → MKV)' })

-- <leader>rrA — ALLE Monitore zusammen (Virtual Screen)
vim.keymap.set('n', '<leader>rrA', function()
  if vim.g.recording_job and vim.g.recording_job > 0 then
    vim.notify('Recording laeuft bereits (job ' .. vim.g.recording_job .. ')', vim.log.levels.WARN)
    return
  end
  if vim.fn.executable('ffmpeg') == 0 then
    vim.notify('ffmpeg nicht im PATH!', vim.log.levels.ERROR)
    return
  end
  local x, y, w, h = get_virtual_screen_bounds()
  if not (x and w and w > 0 and h > 0) then
    vim.notify('Konnte VirtualScreen nicht ermitteln.', vim.log.levels.ERROR)
    return
  end
  start_recording(x, y, w, h, string.format('ALLE Monitore %dx%d @ %d,%d', w, h, x, y))
end, { desc = '[R]un [R]ecord sta[r]t [A]ll (alle Monitore / Virtual Screen)' })

-- <leader>rrA — Optional: Drag-Rechteck-Auswahl (kann hakelig sein bei 4K/DPI-Scaling)
vim.keymap.set('n', '<leader>rrA', function()
  if vim.g.recording_job and vim.g.recording_job > 0 then
    vim.notify('Recording laeuft bereits (job ' .. vim.g.recording_job .. ')', vim.log.levels.WARN)
    return
  end
  if vim.fn.executable('ffmpeg') == 0 then
    vim.notify('ffmpeg nicht im PATH!', vim.log.levels.ERROR)
    return
  end
  vim.notify('Ziehe ein Rechteck mit der Maus — ESC zum Abbrechen', vim.log.levels.INFO)
  local x, y, w, h = get_user_selected_rect()
  if not x then
    vim.notify('Aufnahme abgebrochen (keine Region gewaehlt).', vim.log.levels.WARN)
    return
  end
  local stamp = timestamp()
  local mkv = recordings_dir() .. '/' .. stamp .. '.mkv'
  local mkv_win = mkv:gsub('/', '\\')
  local args = { 'ffmpeg', '-y', '-f', 'gdigrab', '-framerate', '15' }
  vim.list_extend(args, {
    '-offset_x', tostring(x),
    '-offset_y', tostring(y),
    '-video_size', w .. 'x' .. h,
  })
  local region_label = string.format('Auswahl %dx%d @ %d,%d', w, h, x, y)
  vim.list_extend(args, {
    '-i', 'desktop',
    '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
    mkv_win,
  })
  local job_id = vim.fn.jobstart(args, {
    on_stderr = on_recording_stderr,
    on_exit = on_recording_exit,
  })
  if job_id <= 0 then
    vim.notify('ffmpeg-Start fehlgeschlagen!', vim.log.levels.ERROR)
    return
  end
  vim.g.recording_job = job_id
  vim.g.recording_mkv = mkv
  vim.notify('Recording: ' .. region_label .. ' → ' .. stamp .. '.mkv', vim.log.levels.INFO)
end, { desc = '[R]un [R]ecord sta[r]t [A]rea (Drag-Rechteck → MKV)' })

vim.keymap.set('n', '<leader>rrS', function()
  local job_id = vim.g.recording_job
  local mkv = vim.g.recording_mkv
  if not job_id or job_id <= 0 or not mkv then
    vim.notify('Keine laufende Aufnahme.', vim.log.levels.WARN)
    return
  end

  vim.notify('Stoppe Recording (sende q an ffmpeg, finalize MKV)...', vim.log.levels.INFO)
  -- GRACEFUL SHUTDOWN: ffmpeg interpretiert 'q' auf stdin als "quit + finalize".
  -- Vorher: jobstop = SIGTERM/TerminateProcess → MKV bleibt 0 KB!
  local ok = pcall(function() vim.fn.chansend(job_id, 'q') end)
  if not ok then
    -- Fallback: hartes jobstop
    pcall(vim.fn.jobstop, job_id)
  end
  vim.g.recording_job = nil

  -- Hard-Kill-Backup nach 3s falls ffmpeg auf q nicht reagiert (Hang)
  vim.defer_fn(function()
    if vim.fn.jobwait({ job_id }, 0)[1] == -1 then
      vim.notify('ffmpeg reagiert nicht auf q — sende SIGTERM', vim.log.levels.WARN)
      pcall(vim.fn.jobstop, job_id)
    end
  end, 3000)

  -- Warten bis ffmpeg Buffer geflusht hat (3s — Zeit fuer graceful quit)
  vim.defer_fn(function()
    local mkv_win = mkv:gsub('/', '\\')
    local gif = mkv:gsub('%.mkv$', '.gif')
    local gif_win = gif:gsub('/', '\\')

    -- DIAGNOSE: pruefen ob MKV ueberhaupt existiert + Groesse
    if vim.fn.filereadable(mkv_win) == 0 then
      vim.notify('Aufnahmedatei nicht gefunden: ' .. mkv_win, vim.log.levels.ERROR)
      return
    end
    local mkv_size = vim.fn.getfsize(mkv_win) or 0
    if mkv_size <= 0 then
      -- Diagnose: stderr-Tail vom Recording-ffmpeg anzeigen
      local stderr_lines = vim.g.recording_stderr or {}
      local n = #stderr_lines
      local tail_n = math.min(8, n)
      local tail = table.concat(
        { unpack(stderr_lines, math.max(1, n - tail_n + 1)) },
        '\n'
      )
      if tail == '' then tail = '(keine stderr-Ausgabe — ffmpeg startete moeglicherweise gar nicht)' end
      vim.notify(
        'MKV ist 0 KB → Recording fehlgeschlagen\n' ..
        'Pfad: ' .. mkv_win .. '\n' ..
        '--- ffmpeg stderr (letzte ' .. tail_n .. ' Zeilen) ---\n' .. tail,
        vim.log.levels.ERROR,
        { title = 'Recording-Fehler', timeout = 20000 }
      )
      return
    end

    vim.notify(string.format('Konvertiere zu GIF (Quelle %d KB)...', math.floor(mkv_size/1024)), vim.log.levels.INFO)

    -- stderr sammeln fuer Debug
    local stderr_lines = {}

    local convert_id = vim.fn.jobstart(
      {
        'ffmpeg', '-y', '-i', mkv_win,
        '-vf', 'fps=12,scale=1280:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
        gif_win,
      },
      {
        stderr_buffered = false,
        on_stderr = function(_, data)
          if data then
            for _, line in ipairs(data) do
              if line and line ~= '' then
                table.insert(stderr_lines, line)
              end
            end
          end
        end,
        on_exit = function(_, code, _signal)
          vim.schedule(function()
            -- Tail der stderr fuer Debug-Output (letzte 6 Zeilen)
            local tail_n = math.min(6, #stderr_lines)
            local stderr_tail = table.concat(
              { unpack(stderr_lines, math.max(1, #stderr_lines - tail_n + 1)) },
              '\n'
            )

            -- ffmpeg-Konvertierung gescheitert?
            if code ~= 0 then
              vim.notify(
                string.format('GIF-Konvertierung FAILED (exit %d)\n--- stderr (letzte %d Zeilen) ---\n%s',
                  code, tail_n, stderr_tail),
                vim.log.levels.ERROR,
                { title = 'Recording-Fehler', timeout = 15000 }
              )
              return
            end

            -- Wurde GIF wirklich erzeugt?
            if vim.fn.filereadable(gif_win) == 0 then
              vim.notify(
                'GIF wurde nicht erzeugt: ' .. gif_win .. '\n--- stderr ---\n' .. stderr_tail,
                vim.log.levels.ERROR,
                { title = 'Recording-Fehler', timeout = 15000 }
              )
              return
            end

            local size_kb = math.floor((vim.fn.getfsize(gif_win) or 0) / 1024)

            -- GIF-Datei in Windows-Clipboard
            local clip_cmd = string.format(
              'powershell -NoProfile -Command "Set-Clipboard -Path \'%s\'"',
              gif_win
            )
            local clip_out = vim.fn.system(clip_cmd)
            local clip_ok = vim.v.shell_error == 0

            if not clip_ok then
              vim.notify(
                'GIF erstellt, aber Clipboard-Copy fehlgeschlagen.\n' ..
                'Pfad: ' .. gif_win .. '\n' ..
                'Set-Clipboard-Output: ' .. (clip_out or ''),
                vim.log.levels.WARN,
                { title = 'Recording teilweise', timeout = 10000 }
              )
              return
            end

            -- Erfolg!
            vim.notify(
              string.format(
                '✓ GIF in Clipboard — bereit fuer Ctrl+V\n%d KB | %s',
                size_kb,
                vim.fn.fnamemodify(gif, ':t')
              ),
              vim.log.levels.INFO,
              { title = 'Recording fertig', timeout = 8000 }
            )
            vim.g.recording_mkv = nil
          end)
        end,
      }
    )

    if convert_id <= 0 then
      vim.notify('ffmpeg-Konvertierung konnte nicht gestartet werden!', vim.log.levels.ERROR)
    end
  end, 1500)
end, { desc = '[R]un [R]ecord [S]top → GIF → Clipboard' })
