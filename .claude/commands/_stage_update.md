# /_stage update {nr} {concern} {wert} — Einen Concern-Slice mutieren (single-slice-only)

```yaml
status: active
version: 1.0.0
created: 2026-06-20
op: StageUpdate
phase: Meta
chain_position: standalone
feature_anchor: BL-412
type: building-block
```

## Zweck

Mutiert exakt EINEN Concern-Slice einer Stage: ueberschreibt das Concern-Leitfeld
(`SLICE_CONCERN_FIELD[concern]`) mit dem uebergebenen `{wert}`. Kein anderer Slice
wird beruehrt — kein Monolith-Edit, keine Seiteneffekte.

`{wert}` wird als direkter String-Wert uebernommen (kein Editor, kein interaktiver Prompt,
kein Datei-Pfad). Der Wert `skip` ist explizit akzeptiert (Skip-Sentinel, analog
INFRA_CONDITIONAL-Default aus `/_stage init`).

**Namens-Abgrenzung:** `/_stage $nr` (BL-392) = read-only Konsum; `/_stage init` = Slice-Set
anlegen; `/_stage update` = dieser Single-Slice-Mutations-Kanal. `/_stage_orchestrate` =
Commit-Normierung (anderer Namespace).

## Aufruf

```
/_stage update {nr} {concern} {wert}

Parameter:
  nr      — Stage-Nummer (Integer, z.B. 3)
  concern — Concern-Name aus CANONICAL_SLICES
  wert    — neuer Wert als direkter String (z.B. "dotnet test", "skip", "sequential")

Beispiele:
  /_stage update 3 execute "dotnet test --filter Category=Stage3"
  /_stage update 3 setup skip
  /_stage update 3 concurrency_class sequential
  /_stage update 5 exit_criteria "tests_gruen=true"
```

## Die 8 kanonischen Concern-Slices und ihre Leitfelder

```
concern            Leitfeld (SLICE_CONCERN_FIELD)
─────────────────────────────────────────────────
_index             stufe
execute            testbefehl
setup              commands
teardown           commands
health_check       command
resources          infrastruktur
concurrency_class  concurrency_class
exit_criteria      qg
```

Quelle: `stage_slice_schema.CANONICAL_SLICES` + `SLICE_CONCERN_FIELD` (BL-392).

## Ablauf (Pseudocode)

```
1. PARAMETER-VALIDIERUNG:
   nr      = int({nr})
   concern = str({concern})
   wert    = str({wert})

   IF concern NOT IN stage_slice_schema.CANONICAL_SLICES:
     -> FAIL "UNKNOWN_CONCERN: '{concern}' nicht in CANONICAL_SLICES" STOP

2. STAGE AUFLOESEN:
   handle = resolve_vault_stage.resolve_stage(nr)
   IF handle is None:
     -> FAIL "NOT_FOUND: Stage {nr} existiert nicht" STOP

3. SLICE-PFAD ERMITTELN:
   slice_path = handle.resolve_slice(concern)
   IF slice_path existiert nicht:
     -> FAIL "MISSING_SLICE: {concern}.md nicht angelegt — fuehre /_stage init {nr} ... aus" STOP

4. CONCERN-LEITFELD BESTIMMEN:
   concern_field = stage_slice_schema.SLICE_CONCERN_FIELD[concern]

5. SINGLE-SLICE-MUTATION:
   # Lese vorhandenen Slice-Inhalt (Frontmatter + Body)
   slice_content = lese slice_path

   # Ueberschreibe NUR das Concern-Leitfeld; alle anderen Felder bleiben unveraendert
   slice_content[concern_field] = {wert}

   # Schreibe zurueck
   schreibe slice_path mit aktualisiertem slice_content

6. RETURN:
   -> "{concern}.md aktualisiert — {concern_field}: {wert}"
   -> Pfad: slice_path
```

## Szenarien

### Szenario 1 — testbefehl setzen

```
/_stage update 3 execute "dotnet test --filter Category=Stage3 --logger trx"

-> concern_field = "testbefehl"
-> execute.md: testbefehl wird auf "dotnet test --filter Category=Stage3 --logger trx" gesetzt
-> alle anderen Felder in execute.md (z.B. filter, monitor) bleiben unveraendert
-> Ausgabe: "execute.md aktualisiert — testbefehl: dotnet test --filter Category=Stage3 --logger trx"
```

### Szenario 2 — INFRA_CONDITIONAL aktivieren (skip aufheben)

```
/_stage update 3 setup "docker-compose up -d db"

-> concern_field = "commands"
-> setup.md: commands wird auf "docker-compose up -d db" gesetzt (skip:true bleibt im Frontmatter
   — nur das commands-Feld wird mutiert; validate_slice_set wertet das commands-Feld als Primaer)
-> Ausgabe: "setup.md aktualisiert — commands: docker-compose up -d db"
```

### Szenario 3 — Unbekannter Concern

```
/_stage update 3 monitor "TDD-STATE.md"

-> FAIL "UNKNOWN_CONCERN: 'monitor' nicht in CANONICAL_SLICES"
   (Monitor ist kein eigener Slice — er ist Teil von execute, W-AK-MON)
```

### Szenario 4 — Stage nicht gefunden

```
/_stage update 99 execute "dotnet test"

-> FAIL "NOT_FOUND: Stage 99 existiert nicht"
```

### Szenario 5 — Slice-Datei fehlt (init noch nicht gelaufen)

```
/_stage update 3 health_check "curl http://localhost/health"

-> FAIL "MISSING_SLICE: health_check.md nicht angelegt — fuehre /_stage init 3 ... aus"
```

## Invarianten

- **INV-STAGE-UPDATE-1 (Single-Slice-Only):** `/_stage update` mutiert GENAU EINEN Concern-Slice
  pro Aufruf. Kein Monolith-Edit, keine Batch-Mutation mehrerer Concerns in einem Lauf.
  Jeder weitere Concern braucht einen eigenen `/_stage update`-Aufruf.

- **INV-STAGE-UPDATE-2 (Concern-Feld-Praezision):** Nur das Concern-Leitfeld
  (`SLICE_CONCERN_FIELD[concern]`) des betreffenden Slices wird ueberschrieben. Alle anderen
  Felder im mutierten Slice (z.B. `concern:`, `skip:`, Kommentar-Zeilen) bleiben unveraendert.

- **INV-STAGE-UPDATE-3 (Substrat-Konsum, kein Neubau):** `/_stage update` re-implementiert
  `CANONICAL_SLICES` und `SLICE_CONCERN_FIELD` NICHT. Konsum via `stage_slice_schema`-Import
  (BL-392). Unbekannte Concerns werden via CANONICAL_SLICES-Lookup abgewiesen.

- **INV-STAGE-UPDATE-4 (Direkter String-Wert):** `{wert}` wird ohne Transformation uebernommen.
  Kein Editor wird geoeffnet, kein interaktiver Prompt, kein Datei-Pfad-Aufloesung.
  Der Wert `skip` ist ein akzeptierter expliziter Wert (Skip-Sentinel).

## Verwandt

- Schema + Leitfelder: `.claude/scripts/stage_slice_schema.py` (`CANONICAL_SLICES`,
  `SLICE_CONCERN_FIELD` — BL-392)
- Resolver: `.claude/scripts/resolve_vault_stage.py` (`resolve_stage`, `resolve_slice` — BL-392)
- Konsum-Kanal (read-only): `.claude/commands/_stage.md` (BL-392)
- Slice-Set anlegen: `/_stage init {nr} {name}` (BL-412 AK-3) — Voraussetzung
- Delegation-Parent: `/_stage add {nr} {name}` ruft init auf (kein update)
- Verifikation nach Update: `/_stage sanity-check {nr}` (BL-412 AK-6)
- Spezifikation: BL-412 AK-5 · Modell: BL-412_Model.md W8, W4 · Epic: BL-407
