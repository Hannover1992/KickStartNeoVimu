# KickStartNeoVim — GAP-Analyse: IST vs. SOLL

**Version**: 1.0
**Datum**: 2026-03-02
**Basis**: KickStartNeoVim-SPEC.md (v1.0), KickStartNeoVim_Model.md (v1.0), Task.md, init.lua Spot-Checks

---

## Abschnitt 1: Was existiert heute (IST)

### Dateien

```
KickStartNeoVim/
├── init.lua                    # 4541 Zeilen — EINZIGE Config-Datei
├── omnisharp.json              # OmniSharp-Konfiguration (OUT-of-Scope)
├── CLAUDE.md                   # Nutzerdokumentation + Deployment-Anleitung
└── .claude/
    ├── Task.md                 # Aufgabenbeschreibung
    └── models/
        └── KickStartNeoVim_Model.md
```

**Kein `lua/`-Verzeichnis**: Verifiziert via Glob — `lua/**/*` findet keine Dateien.
**Kein Modulsystem**: Alles ein einziger Top-Level-Lua-Scope ohne `require()`-Aufrufe für eigene Module.

### Was init.lua heute enthält (verifiziert)

| Kategorie | Zeilen | LOC |
|-----------|--------|-----|
| Header/Kommentare | 1–85 | 85 |
| Globals & Leader | 87–111 | 25 |
| Swap-Handling + .claude Auto-Copy | 113–164 | 52 |
| Terminal-Hintergrundfarbe | 166–192 | 27 |
| Platform-Detection (`is_windows`) | 194–200 | 7 |
| Projekt-Detection (CENCOCD/DCSRE) | 202–268 | 67 |
| Welcome-Message | 270–275 | 6 |
| Vim-Options | 277–354 | 78 |
| Basic Keymaps + Autocommands | 356–432 | 77 |
| Lazy.nvim Bootstrap | 434–447 | 14 |
| Plugin-Setup (`lazy.setup`) | 449–3034 | 2586 |
| Custom Keybindings | 3036–4539 | 1504 |
| Modeline | 4540–4541 | 2 |
| **GESAMT** | | **4541** |

### Technische Schulden im IST-Zustand

- `is_windows` als Top-Level-Closure-Variable — nicht modular zugreifbar
- 52 `powershell.exe`-Aufrufe direkt inline — keine Abstraktion
- `find_dcsre_root()` als nicht-testbare Funktion (kein Modul)
- Bug B-001: `project_root_windows` auf WSL2 liefert `\mnt\c\...` statt `C:\...`
- `find_vault_root()`-Logik 3x dupliziert (1x named function, 2x inline)

---

## Abschnitt 2: Was soll existieren (SOLL)

Gemäß Task.md + SPEC (Variante A):

```
KickStartNeoVim/
├── init.lua                    # Dispatcher: ~15 Zeilen
├── init_windows.lua            # Windows Entry-Point: ~50 Zeilen
├── init_linux.lua              # Linux/WSL2 Entry-Point: ~40 Zeilen
│
└── lua/
    ├── shared/
    │   ├── platform.lua        # is_windows, chrome_path, open_url() — ~35 Zeilen
    │   ├── project.lua         # find_dcsre_root(), detect(), vim.g.* — ~120 Zeilen
    │   ├── core.lua            # vim.opt, Keymaps, Lazy-Bootstrap, alle Plugins — ~2700 Zeilen
    │   └── keybindings/
    │       ├── init.lua        # Aggregator — ~20 Zeilen
    │       ├── backend.lua     # rbw, rbs, rbb, rbt, rbW — ~180 Zeilen
    │       ├── frontend.lua    # rfr, rfb, rfi, rft, rfw — ~80 Zeilen
    │       ├── git.lua         # gg, gf, gD, gM, gdc, rp, rP, rc — ~120 Zeilen
    │       ├── docker.lua      # rDi, rDa, rDI — ~140 Zeilen
    │       ├── tests.lua       # rim, rid, reb, rei, reg, res, reo — ~200 Zeilen
    │       └── clipboard.lua   # yp, yn, gyf, gyd — ~80 Zeilen
    │
    └── spec/
        ├── project_spec.lua    # Tests für project.lua — ~150 Zeilen
        └── platform_spec.lua   # Tests für platform.lua — ~80 Zeilen
```

**Neue Dateien insgesamt**: 15 Dateien (zu 0 heute)
**Dispatcher init.lua**: Schrumpft von 4541 auf ~15 Zeilen

---

## Abschnitt 3: GAP-Tabelle

| # | Was fehlt | Typ | Priorität | Aufwand | Abhängigkeiten |
|---|-----------|-----|-----------|---------|----------------|
| G1 | `lua/shared/platform.lua` | Neue Datei | MUSS | Klein (~35 Zeilen) | — |
| G2 | `lua/shared/project.lua` | Neue Datei | MUSS | Mittel (~120 Zeilen) | G1 |
| G3 | `lua/shared/core.lua` | Neue Datei | MUSS | Groß (~2700 Zeilen) | G1, G2 |
| G4 | `lua/shared/keybindings/backend.lua` | Neue Datei | MUSS | Mittel (~180 Zeilen) | G1, G2, G3 |
| G5 | `lua/shared/keybindings/frontend.lua` | Neue Datei | MUSS | Klein (~80 Zeilen) | G1, G2, G3 |
| G6 | `lua/shared/keybindings/git.lua` | Neue Datei | MUSS | Mittel (~120 Zeilen) | G1, G2, G3 |
| G7 | `lua/shared/keybindings/docker.lua` | Neue Datei | MUSS | Mittel (~140 Zeilen) | G1, G2, G3 |
| G8 | `lua/shared/keybindings/tests.lua` | Neue Datei | MUSS | Groß (~200 Zeilen) | G1, G2, G3 |
| G9 | `lua/shared/keybindings/clipboard.lua` | Neue Datei | MUSS | Klein (~80 Zeilen) | G1, G2, G3 |
| G10 | `lua/shared/keybindings/init.lua` | Neue Datei | MUSS | Trivial (~20 Zeilen) | G4–G9 |
| G11 | `lua/spec/project_spec.lua` | Neue Datei | MUSS | Mittel (~150 Zeilen) | G2 |
| G12 | `lua/spec/platform_spec.lua` | Neue Datei | MUSS | Klein (~80 Zeilen) | G1 |
| G13 | `init.lua` zu Dispatcher umschreiben | Änderung bestehend | MUSS | Klein (~15 Zeilen) | G3, G10 |
| G14 | `init_windows.lua` anlegen | Neue Datei | SOLL | Trivial (~50 Zeilen) | G13 |
| G15 | `init_linux.lua` anlegen | Neue Datei | SOLL | Trivial (~40 Zeilen) | G13 |
| G16 | Bug B-001 fixen (`project_root_windows` WSL2) | Bugfix in G2 | MUSS | Trivial (3 Zeilen) | G2 |
| G17 | `CLAUDE.md` Deployment-Anleitung updaten | Doku-Update | SOLL | Trivial | G13 |
| G18 | `find_vault_root()` DRY-Verletzung beheben | Refactoring in G3 | KANN | Klein (~10 Zeilen) | G3 |
| G19 | Verzeichnisstruktur `lua/shared/keybindings/` + `lua/spec/` anlegen | Shell-Aktion | MUSS | Trivial | — |
| G20 | `old_settings/init_windows.lua` löschen | Aufräumen | KANN | Trivial | G14 |

### Klassifikation nach Priorität

**MUSS (kein fertiges Produkt ohne diese):** G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G16, G19

**SOLL (wichtig, kein Blocker):** G14, G15, G17

**KANN (nice-to-have):** G18, G20

**Gesamt: 20 GAPs** — davon 15 MUSS, 3 SOLL, 2 KANN

---

## Abschnitt 4: Kritischer Pfad

Der sicherste Weg zur ersten funktionierenden Version (Neovim startet auf beiden Plattformen):

```
Schritt 0: Verzeichnisse anlegen (G19)
  mkdir -p lua/shared/keybindings
  mkdir -p lua/spec
  → Voraussetzung für alles

Schritt 1: lua/shared/platform.lua (G1)
  → Kleinste Einheit, keine Deps
  → Smoke-Test: require('shared.platform') funktioniert in nvim --headless

Schritt 2: lua/shared/project.lua + Bug B-001 Fix (G2 + G16)
  → Extrahiert find_dcsre_root() + detect()
  → Bug B-001 gleichzeitig gefixt (platform.wsl_to_windows statt gsub)
  → Test sofort: lua/spec/project_spec.lua (G11)
  → Smoke-Test: nvim in DCSRE-Verzeichnis → "Welcome to DCSRE!"

Schritt 3: lua/shared/core.lua (G3)
  → Größter Schritt — Zeilen 270–3034 in core.lua verschieben
  → init.lua: diese Zeilen durch require('shared.core') ersetzen
  → Kritisch: Lazy-Bootstrap-Reihenfolge beibehalten
  → Smoke-Test: :Lazy, :LspInfo, alle Plugins geladen

  ⚠ CHECKPOINT: Neovim startet auf Windows UND WSL2 fehlerfrei
  → ERST DANN weitermachen!

Schritt 4: Keybinding-Module (G4–G10)
  Reihenfolge (geringstes Risiko zuerst):
  4a: clipboard.lua (G9) — reine deklarative Keymaps, kein Terminal
  4b: git.lua (G6)       — Neogit/Diffview + PowerShell Push/Pull
  4c: frontend.lua (G5)  — PowerShell-only Commands
  4d: backend.lua (G4)   — WIN+WSL-Branch in rbw
  4e: docker.lua (G7)    — komplexe PowerShell-Scripts
  4f: tests.lua (G8)     — set_xunit_threads + write_it_script Helper
  Nach JEDEM Modul: alle betroffenen Keybindings manuell testen!

Schritt 5: Dispatcher init.lua fertigstellen (G13)
  → init.lua enthält jetzt nur ~15 Zeilen
  → End-to-End Test: alle <leader>r* Keybindings prüfen

  ⚠ ENDPUNKT MINIMALES ZIEL: Neovim startet auf beiden Plattformen ✓
```

**Optionale Nacharbeiten (SOLL/KANN):**
- Schritt 6: init_windows.lua + init_linux.lua (G14, G15)
- Schritt 7: CLAUDE.md updaten (G17)
- Schritt 8: platform_spec.lua (G12)
- Schritt 9: find_vault_root() bereinigen (G18)
- Schritt 10: old_settings aufräumen (G20)

---

## Abschnitt 5: Bug-Liste

### Bug B-001: `project_root_windows` auf WSL2 liefert ungültigen Pfad

**Fundstelle**: `init.lua` Zeile 259 (verifiziert via Model Kap. 1.4, Befund 2)

**Code (IST):**
```lua
vim.g.project_root_windows = dcsre_root:gsub('/', '\\')
```

**Was auf WSL2 passiert:**
1. `cwd` = `/mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend`
2. `find_dcsre_root(cwd)` normalisiert zu Forward-Slashes → gibt zurück: `/mnt/c/Users/.../DCSRE`
3. `gsub('/', '\\')` → `\mnt\c\Users\...\DCSRE`
4. **Ergebnis: Ungültiger Windows-Pfad!** PowerShell erwartet `C:\Users\...`

**Was auf Windows korrekt ist:**
1. `cwd` = `C:\Users\...\DCSRE\Sources\Backend`
2. `find_dcsre_root()` normalisiert → `C:/Users/.../DCSRE`
3. `gsub('/', '\\')` → `C:\Users\...\DCSRE` ✓

**Sichtbare Auswirkung**: `<leader>rp` und `<leader>rP` (Git Push/Pull via PowerShell) nutzen `vim.g.project_root_windows` — schlagen auf WSL2 mit falschem Pfad fehl.

**Warum bisher nicht aufgefallen**: `project_root_wsl` (Zeile 260) wird korrekt gesetzt. Die meisten Backend/Frontend-Keybindings nutzen `vim.g.project_backend` (Forward-Slashes), nicht `project_root_windows`.

**Fix (in G2 — project.lua):**
```lua
if platform.is_windows then
  vim.g.project_root_windows = platform.to_windows_path(dcsre_root)
else
  -- WSL2: dcsre_root ist "/mnt/c/..." → via wsl_to_windows konvertieren
  vim.g.project_root_windows = platform.wsl_to_windows(dcsre_root)
end
```

---

### Bug B-002: `project_backend_windows` auf WSL2 (DCSRE) — gleiche Ursache wie B-001

**Fundstelle**: `init.lua` Zeile 252

**Code (IST):**
```lua
vim.g.project_backend_windows = platform.to_windows_path(dcsre_root) .. '\\Sources\\Backend'
```

`platform.to_windows_path` = `gsub('/', '\\')` — dasselbe Problem wie B-001 auf WSL2.
`dcsre_root` auf WSL2 = `/mnt/c/...` → nach gsub = `\mnt\c\...` (ungültig).

**Fix**: Gleicher Ansatz wie B-001 — `platform.wsl_to_windows(dcsre_root)` auf WSL2 verwenden.

**Impact**: Mittel — `project_backend_windows` wird in `set_xunit_threads()` (Zeile 3511) und `write_it_script()` (Zeile 3539) verwendet. Integration Tests auf WSL2 schlagen mit falschen Pfaden fehl.

---

### Bug B-003: `project_docker_root_windows` auf WSL2 — gleiche Familie

**Fundstelle**: `init.lua` Zeilen 256/258 (DCSRE und CENCOCD)

Für DCSRE:
```lua
vim.g.project_docker_root_windows = platform.to_windows_path(dcsre_root) .. '\\Sources'
```

Für CENCOCD ist es hardcoded korrekt (absolute Windows-Pfade).

**Fix**: Gleiches Muster wie B-001/B-002.

**Impact**: Niedrig — Docker-Keybindings (`<leader>rDi`) nutzen `project_docker_root_windows` für PowerShell — schlagen auf WSL2 fehl.

---

### Potentieller Bug B-004: Inline `is_windows` in Lazy-Plugin-Specs

**Fundstelle**: Zeilen 745–754 (Obsidian), 1477 (DAP), 2788 (LuaSnip) und weitere

Diese Blöcke verwenden `vim.fn.has('win32')` direkt (nicht die `is_windows`-Variable), weil plugin `opts`-Tabellen lazy evaluiert werden.

**Ist das ein Bug?** Nein — das ist korrekt. `vim.fn.has('win32')` liefert denselben Wert wie `is_windows`. Kein Fix nötig.

**Risiko beim Refactoring**: Falls diese inline-Checks bei der Extraktion in `core.lua` durch `platform.is_windows` ersetzt werden, muss `platform` in `core.lua` verfügbar sein (lokale Variable `local is_windows = require('shared.platform').is_windows` vor `lazy.setup()`).

---

## Abschnitt 6: Risiko-Übersicht

| # | Risiko | Auswirkung | Wahrscheinlichkeit | Mitigation |
|---|--------|------------|-------------------|------------|
| R1 | `require('shared.X')` löst nicht auf (runtimepath fehlt) | Neovim startet nicht | Mittel | Deployment-Skript muss `lua/shared/` mitkopieren; nach Schritt 3 testen |
| R2 | Lazy-Bootstrap-Reihenfolge bricht in `core.lua` | Plugins laden nicht | Mittel | `rtp:prepend(lazypath)` MUSS vor `require('lazy').setup()` stehen — nicht umordnen |
| R3 | `vim.g.project_*` nicht gesetzt wenn Plugins laden | Obsidian-Workspaces falsch | Mittel | `project.detect()` MUSS vor `require('shared.core')` stehen |
| R4 | `is_windows` nicht verfügbar in Modul-Scope | Plugin-Specs mit falschen Pfaden | Hoch | In `core.lua`: `local is_windows = require('shared.platform').is_windows` vor `lazy.setup()` |
| R5 | toggleterm-Commands mit falschen Pfaden nach Keybinding-Split | `<leader>r*` funktioniert nicht | Hoch | Nach JEDEM Keybinding-Modul (G4–G9): alle betroffenen Keybindings manuell testen |
| R6 | Bug B-001/B-002/B-003 wird in neuem Code fortgeschrieben | Git Push/Pull + Tests auf WSL2 fehlerhaft | Mittel | Im GAP G2 explizit als Anforderung aufnehmen; platform.wsl_to_windows verwenden |
| R7 | `set_xunit_threads()` und `write_it_script()` haben Windows-TEMP-Abhängigkeiten | Integration Tests auf WSL2 fehlerhaft | Niedrig | Diese Helper bleiben in `tests.lua` — plattformspezifisch belassen (ist kein Fehler) |
| R8 | Beide Neovim-Instanzen (Win + WSL2) gleichzeitig broken während Migration | User kann nicht arbeiten | Mittel | Schrittweise Migration: Schritt für Schritt testen; nie 2 Schritte gleichzeitig |
| R9 | Entscheidung F1 (init_windows/linux?) nicht getroffen vor Start | Unklare Zieldatei für Dispatcher | Hoch | User muss F1 VOR Schritt 5 entscheiden (nicht Blocker für Schritte 1–4) |
| R10 | DAP `.exe`-Suffix-Logik (Zeile 1477) geht beim Extrahieren verloren | DAP-Debugging kaputt | Niedrig | Zeile 1477 explizit markieren; `platform.is_windows` inline lassen in `core.lua` |

---

## Abschnitt 7: Entscheidungsbedarf (für den User)

### Entscheidung E1: Dispatcher-Schema (BLOCKIERT Schritt 5)

**Frage**: Soll der fertige Dispatcher auf `init_windows.lua` + `init_linux.lua` verweisen (Task.md-Vorgabe), oder soll `init.lua` direkt ohne separate Entry-Points dispatchen?

**Option A — Task.md-konform** (mit `init_windows.lua` + `init_linux.lua`):
```lua
-- init.lua
if vim.fn.has('win32') == 1 then
  require('init_windows')
else
  require('init_linux')
end
```
- Pro: Explizite Plattformtrennung, laut Task.md gefordert
- Con: 2 zusätzliche Dateien (~90 Zeilen) die fast identisch sind

**Option B — Minimaler Dispatcher** (nur `init.lua`, SPEC Abschnitt 4.1):
```lua
-- init.lua  (~15 Zeilen)
require('shared.platform')
require('shared.project').detect()
require('shared.core')
require('shared.keybindings.backend')
-- ...
```
- Pro: Weniger Dateien, einfacher
- Con: Abweichung von Task.md-Vorgabe

**SPEC empfiehlt Option A** (Task.md-Konformität), aber der User muss zustimmen.
**Dieses entscheidet Schritt 5 (G13, G14, G15) — kein Blocker für Schritte 0–4!**

---

### Entscheidung E2: `old_settings/init_windows.lua` löschen?

**Situation**: CLAUDE.md sagt explizit "veraltet, nicht mehr nutzen". Falls G14 umgesetzt wird (neues `init_windows.lua`), gibt es Namenskonflikt-Verwirrungs-Risiko.

**Empfehlung**: Nach erfolgreichem Migrations-Abschluss löschen. Kein Blocker für die Migration selbst.

---

### Entscheidung E3: Bug B-001/B-002/B-003 — separater Commit oder Teil des Refactorings?

**Option A**: Als Teil von Schritt 2 (G2 — project.lua Erstellung) mitfixen → kein separater Commit nötig.
**Option B**: Erst im bestehenden `init.lua` fixen → separater Bugfix-Commit → dann Refactoring.

**Empfehlung**: Option A — fix fällt natürlich in die Extraktion von `project.lua`, kein Extra-Aufwand.

---

### Entscheidung E4: `clipboard.lua` in SPEC vs. Task.md

**Situation**: Task.md listet `keybindings/` Module ohne `clipboard.lua`. SPEC fügt `clipboard.lua` (~80 Zeilen, `<leader>yp`, `<leader>yn`, `<leader>gyf`, `<leader>gyd`) hinzu.

**Empfehlung**: SPEC folgen — `clipboard.lua` ist sinnvolle Gruppierung. Kein Blocker.

---

### Entscheidung E5: CLAUDE.md Update — wer, wann?

CLAUDE.md muss nach Abschluss der Migration um den `lua/shared/` Copy-Schritt erweitert werden (Deployment-Anleitung). Das ist Gap G17.

**Empfehlung**: Als letzten Schritt machen (nach G13 abgeschlossen). Kein Blocker.

---

## Abschnitt 8: Fortschrittsindikator

### Aktueller Stand: ~7% fertig

**Berechnung**:
- Neue Dateien: 0 von 15 existieren → 0%
- init.lua umgeschrieben: 0% → 0%
- Bug B-001 behoben: nein → 0%
- Tests vorhanden: 0 von 2 Spec-Dateien → 0%
- Dokumentation (CLAUDE.md Deploy-Update): nein → 0%

**Was zählt als "fertig"**: Das Modell, die SPEC und diese GAP-Analyse sind vollständig — das ist die Planungsarbeit. Die Implementierung ist 0% fertig.

Rechnet man die Analyse-Artefakte mit (~1500 Zeilen Plan/Doku erstellt):
**~7% Gesamtprojekt-Fortschritt** (Planung vollständig, Implementierung ausstehend).

---

### Was macht die wichtigsten 20% aus?

**Die 20% mit dem höchsten Hebel**: **Schritt 2 (G2) + Schritt 3 (G3)**

- G2 (project.lua): Macht `find_dcsre_root()` testbar + fixt Bug B-001 → Sofort messbarer Qualitätsgewinn
- G3 (core.lua): Reduziert init.lua von 4541 auf ~200 Zeilen → Größtes strukturelles Delta

Diese zwei Schritte erledigen ~80% des LOC-Volumens und schaffen die Grundlage für alle anderen Module.

---

### Quick Win: Schritt 0 + Schritt 1 (G19 + G1)

**Was es ist**: Verzeichnisse anlegen + `lua/shared/platform.lua` schreiben (~35 Zeilen)

**Warum sofort Wert**:
1. Platform-Modul ist ab sofort testbar (G12)
2. Alle nachfolgenden Module können `require('shared.platform')` verwenden
3. `wsl_to_windows()` steht bereit für Bug-Fix B-001

**Aufwand**: ~30 Minuten
**Risiko**: Minimal (keine bestehenden Zeilen geändert, nur neue Datei)
**Ergebnis**: Erstes eigenes Lua-Modul im Repo — psychologischer Durchbruch + technische Basis

---

## Zusammenfassung

| Dimension | IST | SOLL | Delta |
|-----------|-----|------|-------|
| Config-Dateien | 1 (init.lua, 4541 LOC) | 3 Entry-Points + 15 Module | +17 Dateien |
| Lua-Module | 0 | 10 (platform, project, core, 6 keybindings, init) | +10 |
| Test-Dateien | 0 | 2 Spec-Dateien, ~17+ Test-Cases | +2 |
| Testbare Funktionen | 0 | `find_dcsre_root`, Projekt-Detection, Pfad-Konversion | +~10 |
| Bekannte Bugs | 3 (B-001, B-002, B-003) | 0 | -3 |
| init.lua Größe | 4541 Zeilen | ~15 Zeilen (Dispatcher) | -4526 LOC |
| Fortschritt | ~7% | 100% | +93% |

**Kritischste Abhängigkeit**: G3 (core.lua) — größtes Risiko, größter Aufwand, Blocker für alle Keybinding-Module.

**Wichtigste User-Entscheidung vor Start**: E1 (Dispatcher-Schema) — aber kein Blocker für Schritte 0–4.

---

*Dokument-Ende — GAP-Analyse Version 1.0*
