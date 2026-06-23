# INSTRUCTION: rT-Commands Korrektur (CenCoCo Test-Stufen)

**Datum:** 2026-03-16
**Kontext:** Dry-Run `/_TDD_orchestrate` hat 3 Fehler in den rT-Commands aufgedeckt.

---

## Problem

Die aktuellen rT-Commands fuer CenCoCo stimmen nicht mit den Test-Stufen-Metadaten ueberein.
Ergebnis: 7 Failures bei Gesamt-Lauf weil Stufe 3 unvollstaendig, Stufe 4+5 ohne Category-Filter.

---

## Korrekturen (3 Stueck)

### 1. rT3 — Zweiter Befehl fehlt (Accounting.SystemTests nicht in sln)

**IST (falsch):**
```
dotnet test src/CenCoCo.sln --filter "Category=IsolatedDocker" ...
```
Nur ein Befehl — Accounting.SystemTests wird komplett verpasst.

**SOLL (korrekt) — Lua muss BEIDE Befehle automatisch verketten:**
```lua
-- rT3 muss beide sequentiell ausfuehren (ein Tastendruck!):
local cmd = 'dotnet test src/CenCoCo.sln --filter "Category=IsolatedDocker" --logger "console;verbosity=detailed"'
  .. ' && dotnet test tests/CenCoCo.Accounting.SystemTests/ --logger "console;verbosity=detailed"'
```

**WICHTIG:** Der User darf NICHT manuell den zweiten Befehl eintippen muessen.
rT3 = 1 Tastendruck = beide Commands hintereinander.

**Grund:** `CenCoCo.Accounting.SystemTests` ist NICHT in `src/CenCoCo.sln`. Ohne zweiten Befehl werden 7 Tests verpasst.

---

### 2. rT4 — Category-Filter fehlt

**IST (falsch):**
```
dotnet test tests/CenCoCo.Blazor.SystemTests ...
```

**SOLL (korrekt):**
```
dotnet test tests/CenCoCo.Blazor.SystemTests/ --filter "Category=SystemTest" --logger "console;verbosity=detailed" --logger "trx;LogFileName=%TEMP%\rt-latest.trx"
```

**Grund:** Ohne `--filter "Category=SystemTest"` laufen ALLE Tests im Projekt, auch solche die zu anderen Stufen gehoeren oder gar keinen Category-Trait haben.

---

### 3. rT5 — Category-Filter fehlt

**IST (falsch):**
```
dotnet test tests/CenCoCo.Blazor.E2ETests ...
```

**SOLL (korrekt):**
```
dotnet test tests/CenCoCo.Blazor.E2ETests/ --filter "Category=E2E" --logger "console;verbosity=detailed" --logger "trx;LogFileName=%TEMP%\rt-latest.trx"
```

**Grund:** Gleich wie rT4 — ohne Filter keine Stufen-Isolation.

---

### 4. rTB — Docker Cleanup VOR Rebuild

**IST:**
```
docker compose -f docker/docker-compose.all.yml --profile all down -v
docker compose -f docker/docker-compose.all.yml --profile all up -d --build
```

**SOLL (ergaenzen — alte Container aufraemen):**
```
docker compose -f docker/docker-compose.all.yml --profile all down -v --remove-orphans
docker compose -f docker/docker-compose.all.yml --profile all up -d --build
```

**Grund:** Ohne `--remove-orphans` bleiben verwaiste Container (z.B. `cencoco-e2e-minio`) liegen und blockieren den naechsten Start mit "container name already in use".

---

## Vollstaendige rT-Referenz (SOLL nach Korrektur)

```
rT1  Unit Tests (kein Docker)
  dotnet test src/CenCoCo.sln
    --filter "Category!=E2E&Category!=SystemTest&Category!=IsolatedDocker&Category!=IntegrationTests"
    --logger "console;verbosity=detailed"

rT2  Integration Tests (kein Docker, ~120s wegen Polly)
  dotnet test src/CenCoCo.sln
    --filter "Category=IntegrationTests"
    --logger "console;verbosity=detailed"

rT3  Isolated Docker Tests (Docker Desktop noetig, 2 Befehle!)
  dotnet test src/CenCoCo.sln
    --filter "Category=IsolatedDocker"
    --logger "console;verbosity=detailed"
  dotnet test tests/CenCoCo.Accounting.SystemTests/
    --logger "console;verbosity=detailed"

rT4  Blazor System Tests (Docker Compose Stack noetig, rTB vorher!)
  dotnet test tests/CenCoCo.Blazor.SystemTests/
    --filter "Category=SystemTest"
    --logger "console;verbosity=detailed"

rT5  E2E Tests (Docker Compose Stack noetig, rTB vorher!)
  dotnet test tests/CenCoCo.Blazor.E2ETests/
    --filter "Category=E2E"
    --logger "console;verbosity=detailed"

rTB  Docker Image Rebuild (PFLICHT vor rT4/rT5 nach src/-Aenderungen)
  docker compose -f docker/docker-compose.all.yml --profile all down -v --remove-orphans
  docker compose -f docker/docker-compose.all.yml --profile all up -d --build
```

---

## WICHTIG: Windows Server / powershell.exe

Alle Shell-Befehle muessen via `powershell.exe -Command "..."` ausgefuehrt werden.
Das betrifft besonders Docker-Commands in rTB, rT3 Setup, rT4/rT5 Preconditions.

```lua
-- Beispiel in Lua:
vim.fn.system('powershell.exe -Command "docker compose -f docker/docker-compose.all.yml --profile all down -v --remove-orphans"')
```

---

## Quelle

Metadaten: `.claude/meta/implementation/stage_1.md` bis `stage_5.md`
Dry-Run Ergebnis: 2026-03-16 (Session `/_TDD_orchestrate`)
