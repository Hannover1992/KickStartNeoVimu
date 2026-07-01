# /_stage help — /_stage Command-Familie (Uebersicht)

```yaml
status: active
version: 1.0.0
created: 2026-06-20
op: StageHelp
phase: Meta
chain_position: standalone
feature_anchor: BL-412
type: satellite
```

## Zweck

Dokumentiert die vollstaendige `/_stage`-Command-Familie (BL-412) und das BL-392
Slice-Schema. Erklaert welcher Command wann genutzt wird und wie die Befehle
zusammenspielen.

**INV-STAGE-HELP-1:** `/_stage help` ist read-only. Kein Write, kein Vault-Zugriff.

**Namens-Abgrenzung:** `/stage` (ohne Unterstrich) = Commit-Normen-Doc;
`/_stage_orchestrate` = Commit-Normierung + Security-Gate;
`/_stage` (mit Unterstrich) = Stage-Slice-Kanal + diese Command-Familie.

---

## Aufruf

```
/_stage help
```

---

## Die /_stage Command-Familie — Uebersicht

| Command | Funktion | Modus | BL |
|---------|----------|-------|-----|
| `/_stage $nr` | Relevante Slice(s) einer Stage in-Context laden (read-only) | Konsum | BL-392 |
| `/_stage help` | Diese Uebersicht — Command-Familie + Slice-Schema erklaert | Doku | BL-412 |
| `/_stage init {nr} {name}` | Kompletten 8-Slice-Satz einer Stage anlegen (merge-idempotent) | Schreib | BL-412 |
| `/_stage add {nr} {name}` | Neue Stage hinzufuegen (Validierung + Delegation an init) | Schreib | BL-412 |
| `/_stage update {nr} {concern} {wert}` | Exakt einen Concern-Slice mutieren | Schreib | BL-412 |
| `/_stage sanity-check {nr}` | Stage N strukturell-deterministisch verifizieren (5 Sub-Checks) | Verify | BL-412 |

---

## Command 1: `/_stage $nr` — Slice-Kanal (read-only, BL-392)

Der read-only Konsum-Kanal. Landet den/die relevanten Slice(s) einer Stage
in-Context — nicht das ganze Stage-Doc (INV-STAGE-CHANNEL-4: single unit of work).

```
/_stage $nr                 # _index-Slice der Stage N (Identitaet + slice_map)
/_stage $nr {concern}       # NUR diesen einen Concern-Slice
```

**Anwendungsbeispiele:**

```
/_stage 3               # _index-Slice von Stage 3 laden (Orientierung, slice_map)
/_stage 3 execute       # execute-Slice fuer TDD-Red/Green Worker
/_stage 3 health_check  # health_check-Slice fuer Setup-Step
/_stage 2 resources     # resources-Slice fuer IDF-Planer
```

**Step-zu-Slice-Zuordnung (BL-392):**

| Fragender Step | Gelandete Slice(s) |
|----------------|--------------------|
| TDD-Red / TDD-Green / `_TDD_execute` | `execute` (+ `health_check`) |
| Stage-Setup-Step (BL-408) | `setup` (+ `health_check`) |
| Stage-Teardown-Step (BL-408) | `teardown` |
| Resource-Claim/Release, IDF-Planer | `resources` |
| Scheduler / Parallel-Suitability | `concurrency_class` |
| Precondition-Gate (BL-409) / Stage-Exit | `exit_criteria` |
| `/_stage $nr` ohne Concern, sanity-check | `_index` |

Kein Write. Kein Vault-State-Zugriff. `/_stage` baut KEINE Slices, es liest
nur schon-vorhandene (INV-STAGE-CHANNEL-2).

---

## Command 2: `/_stage help` — diese Datei

```
/_stage help
```

Gibt diese Uebersicht aus. Kein Vault-Zugriff (INV-STAGE-HELP-1).

---

## Command 3: `/_stage init {nr} {name}` — Slice-Set anlegen

Legt den vollstaendigen 8-Slice-Satz einer Stage idempotent an.
Delegiert Precondition-Verify (exit_criteria-Gate) an BL-409.

```
/_stage init {nr} {name}
```

**Anwendungsbeispiele:**

```
/_stage init 1 unit           # Stage 1 "unit" neu anlegen (8 Skeleton-Slices)
/_stage init 3 integration    # Stage 3 "integration" anlegen
/_stage init 3 integration    # Wiederholt: merge-idempotent, fehlende Slices ergaenzt
```

**Verhalten:**

- **Neu-Anlage:** Alle 8 Skeleton-Slices werden angelegt unter
  `{VAULT}/Stage/stage_{nr}_{name}/`.
  - `ALWAYS_REQUIRED` (`_index`, `execute`, `exit_criteria`): Concern-Leitfeld
    mit `null`-Wert (kein Leer-Defekt).
  - `INFRA_CONDITIONAL` (`setup`, `teardown`, `health_check`): Default `skip: true`
    (expliziter Skip-Sentinel).
  - `DECLARATION` (`resources`, `concurrency_class`): Concern-Leitfeld mit `null`.
- **Merge-Idempotenz:** Existiert das Verzeichnis bereits, werden nur fehlende
  Slices ergaenzt. Vorhandene Slices bleiben unveraendert.
  Ausgabe: `"Stage {nr} existiert bereits — ergaenze fehlende Slices."`
- **Post-Check:** `validate_slice_set(stage_dir)` muss `SliceSchemaResult(valid=True)`
  liefern.
- **BL-409-Delegation:** Precondition-Verify wird an BL-409 delegiert — nicht
  selbst implementiert (INV-STAGE-INIT-2). Falls BL-409 nicht verfuegbar:
  WARN, kein silent skip.

**Invarianten:** INV-STAGE-INIT-1 (merge-Idempotenz), INV-STAGE-INIT-2
(Precondition-Delegation an BL-409, kein eigenes Gate).

---

## Command 4: `/_stage add {nr} {name}` — neue Stage hinzufuegen

Prueft ob die Stage-Nr frei ist, validiert den Namen, dann Delegation an
`/_stage init`.

```
/_stage add {nr} {name}
```

**Anwendungsbeispiele:**

```
/_stage add 4 e2e             # Stage 4 "e2e" hinzufuegen (nach Validierung -> init)
/_stage add 2 api             # FAIL wenn stage_2_* bereits existiert
/_stage add 5 mein name       # FAIL: Leerzeichen im Namen (kein slug)
```

**Verhalten:**

- Validierung Nr-Konflikt: Existiert `{VAULT}/Stage/stage_{nr}_*/`? -> FAIL +
  Fehlermeldung. Kein Write.
- Validierung slug: `{name}` alphanumerisch + Bindestriche/Unterstriche, kein
  Leerzeichen -> sonst FAIL + Fehlermeldung.
- Bei OK: `Skill(_stage_init)` mit `{nr}` und `{name}` — kein Code-Duplikat
  der Init-Logik.

**Invariante:** INV-STAGE-ADD-1: Delegation an `/_stage init` ist obligatorisch;
keine eigene Init-Logik in `/_stage add`.

---

## Command 5: `/_stage update {nr} {concern} {wert}` — Concern-Slice mutieren

Mutiert exakt EINEN Concern-Slice einer Stage. Single-slice-only (kein Monolith-Edit).

```
/_stage update {nr} {concern} {wert}
```

`{concern}` muss eines der 8 kanonischen Slice-Namen sein (s. Slice-Schema unten).
`{wert}` wird als direkter String-Wert uebernommen (kein Editor, kein Datei-Pfad).

**Anwendungsbeispiele:**

```
/_stage update 3 execute "dotnet test --filter Stage3"   # testbefehl setzen
/_stage update 1 concurrency_class "SERIAL"              # concurrency_class setzen
/_stage update 2 resources "docker-compose"              # infrastruktur setzen
/_stage update 3 health_check "false"                    # skip-Sentinel setzen
```

**Fehler-Faelle:**

| Fehler | Meldung |
|--------|---------|
| `{concern}` unbekannt | `"UNKNOWN_CONCERN: '{concern}' nicht in CANONICAL_SLICES"` |
| Stage nicht gefunden | `"NOT_FOUND: Stage {nr} existiert nicht"` |
| Slice-Datei fehlt | `"MISSING_SLICE: {concern}.md nicht angelegt — fuehre /_stage init {nr} ... aus"` |

**Invariante:** INV-STAGE-UPDATE-1: single-slice-only (analog INV-STAGE-CHANNEL-4);
kein anderer Slice wird beruehrt, keine Seiteneffekte.

---

## Command 6: `/_stage sanity-check {nr}` — Stage verifizieren (★ Kern)

Verifiziert Stage N strukturell-deterministisch (laeuft IMMER ohne laufendes System).
Optional mit `--live` fuer live-Tier-Pruefungen.

```
/_stage sanity-check {nr}
/_stage sanity-check {nr} --live
```

**Anwendungsbeispiele:**

```
/_stage sanity-check 3          # Stage 3 strukturell verifizieren
/_stage sanity-check 1 --live   # Stage 1 + live-Tier (TDD-STATE.md Ergebnis-Check)
```

**5 Sub-Checks (alle strukturell-deterministisch):**

| Sub-Check | Was wird geprueft | PASS/WARN/FAIL |
|-----------|------------------|----------------|
| **(a)** Gezielt ein Test starten | `execute.testbefehl` valide (nicht null/leer) | FAIL wenn fehlt |
| **(b)** Subset/Filter-Tests | Filter-Feld im `execute`-Slice vorhanden | WARN wenn fehlt (nicht ALWAYS_REQUIRED) |
| **(c)** Alle Tests vollstaendig | `concurrency_class`-Slice valide + `execute`-Slice vollstaendig | FAIL wenn leer |
| **(d)** Monitor-Kanal ableitbar | Monitor-Kanal (TDD-STATE.md oder TRX) aus `execute`-Slice syntaktisch ableitbar | PASS/FAIL |
| **(e)** Setup + Teardown erreichbar | Jeder `INFRA_CONDITIONAL`-Slice ENTWEDER vollstaendig ODER `skip: true` | FAIL wenn leer |

**Gesamt-Report:** `worst_case(a, b, c, d, e)` — FAIL > WARN > PASS.
Jeder Sub-Check traegt eigenen Status + `recovery_hint`.

Vollstaendigkeits-Check via `stage_slice_schema.validate_slice_set(stage_dir)` —
kein Re-Implement des Validators (INV-STAGE-SC-2).

**Invarianten:** INV-STAGE-SC-1 (strukturell immer lauffaehig, live opt-in),
INV-STAGE-SC-2 (kein Re-Implement von `validate_slice_set`).

---

## Das BL-392 Slice-Schema — 8 kanonische Concern-Slices

Jede Stage ist ein Verzeichnis aus exakt 8 Slice-Dateien (1 Datei pro Concern).
Quelle: `stage_slice_schema.CANONICAL_SLICES` (BL-392, projektagnostisch).

| Slice | Concern-Leitfeld | Typ | Pflicht-Regel |
|-------|-----------------|-----|---------------|
| `_index` | `stufe` | ALWAYS_REQUIRED | Pflicht immer — Identitaet + Narrativ + `slice_map` |
| `execute` | `testbefehl` | ALWAYS_REQUIRED | Pflicht immer — Testbefehl + Filter + Monitor-Kanal |
| `setup` | `commands` | INFRA_CONDITIONAL | Pflicht wenn `resources.infrastruktur` != none/skip |
| `teardown` | `commands` | INFRA_CONDITIONAL | Pflicht wenn `resources.infrastruktur` != none/skip |
| `health_check` | `command` | INFRA_CONDITIONAL | Pflicht wenn `resources.infrastruktur` != none/skip |
| `resources` | `infrastruktur` | DECLARATION | Immer erwartet (Deklaration) |
| `concurrency_class` | `concurrency_class` | DECLARATION | Immer erwartet (Deklaration) |
| `exit_criteria` | `qg` | ALWAYS_REQUIRED | Pflicht immer — QG + Abnahme-Anker |

**Monitor ist KEIN 9. Slice** — er ist Teil von `execute` (W-AK-MON).
`setup`, `teardown`, `health_check` koennen mit `skip: true` explizit
uebersprungen werden (Skip-Sentinel, W-SLICE-3: explizit > implizit).

**Skeleton-Vorlagen fuer `/_stage init`:**

```yaml
# ALWAYS_REQUIRED (_index, execute, exit_criteria) + DECLARATION (resources, concurrency_class):
---
concern: execute
testbefehl: null
---

# INFRA_CONDITIONAL (setup, teardown, health_check) — Default Skip:
---
concern: setup
skip: true
---
```

---

## Zusammenspiel der Commands

```
add → init → [8 Slices angelegt]
               |
               +--> update {concern}   (einzelne Slices befuellen)
               |
               +--> sanity-check       (Vollstaendigkeit pruefen)
               |
               +--> /_stage $nr        (Slices in-Context laden, read-only)
```

**Typischer Workflow:**

1. `/_stage add 3 integration` — Neue Stage hinzufuegen (Validierung + init)
2. `/_stage update 3 execute "dotnet test --filter Stage3"` — Testbefehl setzen
3. `/_stage update 3 resources "docker-compose"` — Infra deklarieren
4. `/_stage update 3 setup "docker-compose up -d"` — Setup-Commands setzen
5. `/_stage sanity-check 3` — Verifizieren: alle Sub-Checks PASS?
6. `/_stage 3 execute` — TDD-Red/Green Worker laedt genau diesen Concern

`/_stage init` kann jederzeit wiederholt werden (merge-idempotent):
ergaenzt fehlende Slices, beruehrt vorhandene nicht.

---

## Verwandt

- Schema: `stage_slice_schema.py` (`CANONICAL_SLICES`, `validate_slice_set`, BL-392
  AK-SLICE-SCHEMA) — Substrat; BL-412 re-implementiert dieses Schema NICHT.
- Resolver: `resolve_vault_stage.py` (`resolve_stage`, `resolve_slice`,
  `StageHandle`, BL-392 AK-GLOB) — Substrat fuer `/_stage $nr`, init, update,
  sanity-check.
- Consumer von `/_stage $nr` (BL-392): `_TDD_setup` / `_TDD_teardown` /
  `_TDD_execute` / `_IDF_berater_stagePlanner` / `t_script.py` /
  `tdd_stages_ready.py`.
- Downstream-Consumer von `/_stage init`: BL-413 (Stage-Set-Init im Init-Flow).
- Precondition-Gate: BL-409 (exit_criteria-Pruefung, von `/_stage init`
  delegiert).
- current_stage-Routing: BL-414 (WANN/WELCHE Stage aktiv ist — nicht hier).
- Epic: BL-407 (Stage-Epic-Parent).
