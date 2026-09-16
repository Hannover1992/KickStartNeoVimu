# Neovim-Config Update — Maschine A (Windows)

Stand: 2026-09-16. Voraussetzung: Neovim ist auf Maschine A schon eingerichtet
(kein Fresh-Setup — nur das Update auf den aktuellen `develop`-Stand).

---

## 1. Repo aktualisieren

```powershell
cd C:\Users\<DEIN-USER>\Documents\Projekt\KickStartNeoVim
git pull origin develop
```

Erwartete neue Commits (letzte 5):
```
e9d0257  feat: Dirty-Tests sDti/sDtI/sDtu/sDtU + rif Picker ueber alle Integrationstests
8ca05e4  feat: rDs Compose-Service-Picker (--no-deps) + rbR eigener Terminal-Slot pro Projekt
7155f19  feat: <leader>sDkt (Test-Buffer schliessen) + Buffer-Picker Ctrl+A Select-All
08f4ee4  fix: gitsigns CRLF-Bug bei change_base (Branch-Diff zeigte ganze Datei als geaendert)
5c3edab  feat: dateiuebergreifende Branch-Hunk-Navigation (qh/]q) + gitsigns Change-Sign
```

Falls `git pull` mit lokalen Aenderungen kollidiert: **nicht** `git reset --hard`.
Erst `git status` pruefen, dann `git stash` falls es eigene Anpassungen sind,
die behalten werden sollen.

---

## 2. Config deployen

```powershell
Copy-Item -Recurse -Force 'C:\Users\<DEIN-USER>\Documents\Projekt\KickStartNeoVim\lua\*' "$env:LOCALAPPDATA\nvim\lua\"
Copy-Item -Force 'C:\Users\<DEIN-USER>\Documents\Projekt\KickStartNeoVim\init.lua' "$env:LOCALAPPDATA\nvim\init.lua"
```

**Wichtig:** `lua\*` mit Stern — kopiert den Inhalt des Ordners, nicht den
Ordner selbst. Ohne Stern landet die Struktur eine Ebene zu tief und nichts
greift.

---

## 3. Neovim neu starten

Alle laufenden Neovim-Instanzen schliessen und neu oeffnen. Ein `:source` auf
`init.lua` reicht **nicht** fuer alle Aenderungen — die gitsigns-Plugin-Spec
(Punkt 4 unten) greift nur bei echtem Neustart, weil sie `config = function()`
statt nur `opts = {}` nutzt.

---

## 4. Was sich inhaltlich geaendert hat

### gitsigns CRLF-Fix (wichtigster Punkt)
Vorher zeigte `<leader>hB` (Base-Toggle auf `origin/develop`) bei jeder
geaenderten Datei die **komplette Datei** als geaendert an, statt nur der
echten Hunks. Ursache: ein gitsigns-Bug beim Diff gegen eine fremde Revision
in CRLF-Repos (betrifft jedes Repo mit `core.autocrlf=true` / `* text=auto`
in `.gitattributes` — also DCSRE). Der Fix sitzt direkt in der Plugin-Spec
(`lua/shared/core.lua`, Suche nach `Repo.file_info`), kein Plugin-Update noetig
(upstream hat denselben Bug, Stand 2026-08-11).

**Test nach dem Deploy:** `<leader>hB` in einer Datei mit echten Branch-
Aenderungen druecken, dann `]c`/`[c`. Sollte durch einzelne Hunks springen,
nicht die ganze Datei als einen Block markieren.

### Neue/geaenderte Keybindings

| Key | Was |
|---|---|
| `<leader>hB` | gitsigns-Base umschalten: HEAD ↔ `origin/develop` (steuert `]c`/`[c`) |
| `<leader>qh` | Quickfix-Liste aus ALLEN Hunks vs. Base ueber alle geaenderten Dateien |
| `]q` / `[q` | dateiuebergreifend durch die Quickfix-Hunks navigieren (mit Wrap) |
| `Alt+l` / `Alt+h` | naechster / vorheriger Buffer (`Ctrl+Shift+[`/`]` geht NICHT zuverlaessig — Terminal schluckt die Shift-Info bei dieser Kombi) |
| `<leader>sDr` | SonarQube/Roslyn-Findings-Harvest headless im Hintergrund starten (dauert 3-4 Min, Session bleibt nutzbar), Ergebnis landet in Quickfix |
| `<leader>sDkt` | alle offenen Buffer mit "Test" im Pfad schliessen (Nachschlag zu `sDo`) |
| `<leader><leader>` → `Ctrl+A` | im Buffer-Picker: alle aktuell gefilterten Eintraege markieren (fuer `dd`-Bulk-Close) |
| `<leader>ret` | E2E-Tag-Picker akzeptiert jetzt mehrere Ticket-Nummern (Komma/Space-getrennt), filtert per `--env tags` echt auf die getaggten Szenarien, `--browser chrome` |
| gitsigns Change-Sign | `~` → `»` (bei vielen Misch-Hunks war `~` visuell nicht von echten Aenderungen zu unterscheiden) |
| `<leader>rDs` | Docker-Service-Picker (DCSRE): Compose-Service waehlen → `docker compose up -d --no-deps <service>` (nachstarten ohne das laufende Profil zu wechseln) |
| `<leader>rbR` | **Fix:** eigener Terminal-Slot pro Projekt (60–89, aus Projektname abgeleitet). Vorher teilte sich `rbR` den Slot mit `rbw` — ein zweiter Start hat nur das bestehende Terminal ein-/ausgeblendet statt ein neues zu oeffnen. Terminal-Anzeigename = Projektname (sichtbar in `<leader>st`). |
| `<leader>rif` | Integration-Test-Picker: statischer Scan aller `[Fact]`/`[Theory]`-Methoden im IntegrationTests-Projekt (kein Build, < 1s) — tippen filtert, `Tab` markiert mehrere, `Enter` startet NUR die markierten |
| `<leader>sDti` / `sDtI` | **Dirty Integration Tests**: Picker bzw. "alle" NUR ueber Tests aus Integrationstest-Dateien, die gegen `origin/develop` geaendert sind |
| `<leader>sDtu` / `sDtU` | **Dirty Unit Tests**: dasselbe fuer `*.UnitTests`-Projekte (Domain.UnitTests, Data.UnitTests, …) — `sDtU` startet pro Projekt ein eigenes `dotnet test` (Terminal 46) |

### Empfohlener Workflow: Branch-Review in Neovim
```
<leader>hB    -- Base auf origin/develop
<leader>sDo   -- Dirty-Files des aktiven Profils als Buffer laden
Alt+h / Alt+l -- zwischen Dateien springen
]c / [c       -- durch die echten Hunks pro Datei
<leader>sDkt  -- Test-Dateien wieder raus, wenn nur Produktionscode interessiert
<leader>sDti  -- NUR die geaenderten Integrationstests picken und laufen lassen
<leader>sDtu  -- NUR die geaenderten Unit-Tests picken und laufen lassen
```

---

## 5. Bekannte Stolpersteine

- **`telescope-fzf-native.nvim` ist in der Config referenziert, aber NICHT
  kompiliert** (kein `.dll` im Plugin-Ordner). Folge: kein `!ausschluss`-Syntax
  in Telescope-Picker-Prompts, nur normales Fuzzy-Matching. Wer das braucht,
  muesste das Plugin manuell bauen (braucht `make` + C-Compiler, z.B. MinGW).
  Nicht kritisch, nur eine fehlende Komfortfunktion.
- **Fuzzy-Matching ist kein Substring-Matching**: Tippen von "Test" im
  Buffer-/Datei-Picker filtert NICHT zuverlaessig auf Dateien mit "Test" im
  Namen — bei langen Pfaden matcht Fuzzy fast alles. Fuer "Test-Dateien raus"
  `<leader>sDkt` nutzen (echter Substring-Check), nicht auf den Picker-Filter
  verlassen.
- Nach `git pull` mit CRLF-Warnungen (`LF will be replaced by CRLF`) ist
  normal bei diesem Repo (`.gitattributes` normalisiert C#-Dateien) — keine
  Aktion noetig.

---

## 6. Kurzcheck nach dem Update

```vim
:Lazy sync      " falls Plugin-Versionen sich geaendert haben (i.d.R. nicht noetig)
:LspInfo        " OmniSharp sollte weiterhin normal attachen
```

Dann eine Datei mit Branch-Aenderungen oeffnen, `<leader>hB` + `]c` testen
(siehe Punkt 4, gitsigns-Fix).
