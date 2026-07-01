# /_stage init {nr} {name} — Stage-Slice-Set anlegen (merge-idempotent)

```yaml
status: active
version: 1.0.0
created: 2026-06-20
op: StageInit
phase: Meta
chain_position: standalone
feature_anchor: BL-412
type: building-block
```

## Zweck

Legt das vollstaendige Slice-Set einer Stage im Vault an — alle 8 kanonischen Concern-Dateien
als Skeleton, direkt nach `stage_slice_schema.CANONICAL_SLICES`. Merge-idempotent: fehlende
Slices werden ergaenzt, vorhandene niemals ueberschrieben (kein Datenverlust).

Parametrierbar via `{nr}` und `{name}`, damit `/_stage add` ohne Code-Duplikat via
`Skill(_stage_init)` delegieren kann (F6 aus BL-412_Model.md).

**Namens-Abgrenzung:** `/_stage $nr` (BL-392) = read-only Konsum-Kanal; `/_stage init` = dieser
Schreib-Init. `/_stage_orchestrate` = Commit-Normierung (anderer Namespace). `/stage` (ohne
Unterstrich) = Commit-Normen-Doc.

## Aufruf

```
/_stage init {nr} {name}

Parameter:
  nr    — Stage-Nummer (Integer, z.B. 3)
  name  — Stage-Name als Slug (alphanumerisch + Bindestriche/Unterstriche, kein Leerzeichen)

Beispiele:
  /_stage init 3 integration
  /_stage init 5 e2e-live
```

## Ablauf (Pseudocode)

```
1. PRECONDITION-GATE (INV-STAGE-INIT-2, BL-409):
   result = check_preconditions(stage_nr=nr, vault_root=VAULT_ROOT, resource_timeout=60.0)
   # CLI-Aequivalent: py -3 .claude/scripts/precondition_gate.py {nr} [--resource-timeout 60]
   IF result.verdict == "BLOCK":
     -> FAIL result.message  STOP
        # category + blocking_item nennen was fehlt (Vorgaenger-Stage / Substrat-Slice)
        # kein Halb-Start, kein Write, kein Verzeichnis
   IF result.verdict == "WAIT":
     -> WARN result.message  STOP  # Ressource temporaer belegt — Caller soll spaeter neu versuchen
        # Gate ist idempotent + stateless: erneuter Aufruf nach Freigabe = sauber
   # PASS -> weiter zu Schritt 2 (Parameter-Validierung)

2. PARAMETER-VALIDIERUNG:
   nr   = int({nr})             # muss gueltige Integer-Zahl sein
   name = str({name})           # muss slug-faehig sein (alphanumerisch + -, _; kein Leerzeichen)
   IF name enthaelt Leerzeichen oder unerlaubte Zeichen:
     -> FAIL "INVALID_NAME: '{name}' ist kein gueltiger Slug (alphanumerisch + - _)" STOP

3. STAGE-VERZEICHNIS-PFAD:
   stage_dir = {VAULT}/Stage/stage_{nr}_{name}/

4. IDEMPOTENZ-PRUEFUNG:
   IF stage_dir existiert:
     -> WARN "Stage {nr} existiert bereits — ergaenze fehlende Slices."
     modus = MERGE
   ELSE:
     -> erstelle stage_dir
     modus = NEU

5. SLICE-SET ANLEGEN (ueber CANONICAL_SLICES aus stage_slice_schema):
   # CANONICAL_SLICES = ("_index", "execute", "setup", "teardown",
   #                      "health_check", "resources", "concurrency_class", "exit_criteria")

   FUER jeden slice IN stage_slice_schema.CANONICAL_SLICES:
     slice_path = stage_dir / "{slice}.md"

     IF slice_path existiert UND modus == MERGE:
       -> skip (INV-STAGE-INIT-1: kein Ueberschreiben)
       CONTINUE

     # Skeleton-Inhalt je nach Slice-Kategorie (W11, AK-3):
     IF slice IN stage_slice_schema.INFRA_CONDITIONAL_SLICES:
       # setup, teardown, health_check — Default skip (kein Infra-Pflicht per Default)
       schreibe slice_path:
         ---
         concern: {slice}
         skip: true
         ---

     ELIF slice IN stage_slice_schema.ALWAYS_REQUIRED_SLICES:
       # _index, execute, exit_criteria — Concern-Leitfeld mit null
       concern_field = stage_slice_schema.SLICE_CONCERN_FIELD[slice]
       schreibe slice_path:
         ---
         concern: {slice}
         {concern_field}: null
         ---

     ELSE:
       # resources, concurrency_class — Deklarations-Slices, Concern-Feld mit null
       concern_field = stage_slice_schema.SLICE_CONCERN_FIELD[slice]
       schreibe slice_path:
         ---
         concern: {slice}
         {concern_field}: null
         ---

6. POST-VALIDIERUNG:
   result = stage_slice_schema.validate_slice_set(stage_dir)
   IF result.valid:
     -> "Stage {nr} ({name}) initialisiert — {len(CANONICAL_SLICES)} Slices, validate_slice_set: PASS"
   ELSE:
     # Sollte nicht vorkommen wenn Schritt 5 korrekt lief — dennoch Report:
     -> WARN "validate_slice_set meldet Defekte: {result.errors}" (kein STOP — Slices wurden geschrieben)

7. RETURN:
   stage_dir-Pfad, Liste der geschriebenen Slices (bei MERGE: nur die neu ergaenzten)
```

## Skeleton-Slice-Referenz

Die folgenden Skeleton-Inhalte entsprechen dem Schema aus `stage_slice_schema.py`:

### ALWAYS_REQUIRED — `_index`, `execute`, `exit_criteria`

```yaml
---
concern: _index
stufe: null
---
```

```yaml
---
concern: execute
testbefehl: null
---
```

```yaml
---
concern: exit_criteria
qg: null
preconditions: null   # optional (BL-409): null = keine Vorgabe, Gate liefert sofort PASS
---
```

### INFRA_CONDITIONAL — `setup`, `teardown`, `health_check`

```yaml
---
concern: setup
skip: true
---
```

```yaml
---
concern: teardown
skip: true
---
```

```yaml
---
concern: health_check
skip: true
---
```

### Deklarations-Slices — `resources`, `concurrency_class`

```yaml
---
concern: resources
infrastruktur: null
---
```

```yaml
---
concern: concurrency_class
concurrency_class: null
---
```

Der explizite `skip: true`-Wert (Skip-Sentinel) bei INFRA_CONDITIONAL-Slices ist kein
Leer-Defekt — `stage_slice_schema.validate_slice_set` akzeptiert ihn als konform
(W-SLICE-3: explizit > implizit).

## Szenarien

### Szenario 1 — Neu-Anlage

```
/_stage init 3 integration

-> stage_dir = {VAULT}/Stage/stage_3_integration/ (existiert nicht)
-> modus = NEU
-> alle 8 Slices angelegt (setup/teardown/health_check mit skip:true, rest mit null)
-> validate_slice_set: PASS
-> Ausgabe: "Stage 3 (integration) initialisiert — 8 Slices, validate_slice_set: PASS"
```

### Szenario 2 — Merge-Idempotenz (F2)

```
/_stage init 3 integration   # erneut — execute.md fehlt, rest vorhanden

-> WARN "Stage 3 existiert bereits — ergaenze fehlende Slices."
-> modus = MERGE
-> nur execute.md wird als Skeleton angelegt (die 7 vorhandenen bleiben unveraendert)
-> validate_slice_set: PASS
-> Exit-Code 0
```

### Szenario 3 — Precondition-Gate BLOCK (Vorgaenger nicht abgeschlossen)

```
/_stage init 5 e2e-live   # Stage 4 noch nicht DONE

-> check_preconditions(5) -> verdict=BLOCK, category=predecessor
-> FAIL "BLOCK: Stage 4 (load-test) nicht abgeschlossen (stufe=IN_PROGRESS, erwartet: DONE).
         Pfad: {VAULT}/Stage/stage_4_load-test/_index.md
         Recovery: Schliesse Stage 4 ab bevor Stage 5 initialisiert wird."
-> STOP — kein Write, kein Verzeichnis
```

### Szenario 4 — Unguealtiger Name

```
/_stage init 4 "mein test"

-> FAIL "INVALID_NAME: 'mein test' ist kein gueltiger Slug (alphanumerisch + - _)"
-> kein Write, kein Verzeichnis
```

## Invarianten

- **INV-STAGE-INIT-1 (Merge-Idempotenz):** `/_stage init` ueberschreibt KEINE vorhandenen
  Slices. Bei Wiederholung werden ausschliesslich fehlende Slices als Skeleton ergaenzt.
  Vorhandene Slices (inkl. ihres Inhalts) bleiben unveraendert. Kein Datenverlust.

- **INV-STAGE-INIT-2 (BL-409-Gate):** VOR jeder Slice-Anlage / Setup laeuft das Precondition-Gate
  (`check_preconditions` aus `.claude/scripts/precondition_gate.py`). BLOCK -> STOP mit klarer
  Meldung (category + blocking_item), kein Halb-Start. WAIT -> STOP mit WARN, Caller soll spaeter
  neu versuchen (Gate ist idempotent + stateless). PASS -> Ablauf faehrt mit Schritt 2 fort.
  `/_stage init` implementiert die Gate-Logik NICHT selbst (INV-STAGE-INIT-3).

- **INV-STAGE-INIT-3 (Substrat-Konsum, kein Neubau):** `/_stage init` re-implementiert
  `CANONICAL_SLICES`, `SLICE_CONCERN_FIELD`, `validate_slice_set` NICHT. Konsum via
  `stage_slice_schema`-Import. Die 8 Slice-Namen kommen ausschliesslich aus
  `stage_slice_schema.CANONICAL_SLICES`.

- **INV-STAGE-INIT-4 (Parametrierbarkeit):** `{nr}` und `{name}` sind positionale Argumente
  (kein interaktiver Modus), damit `/_stage add` via `Skill(_stage_init)` deterministisch
  delegieren kann.

## Verwandt

- Schema + Validator: `.claude/scripts/stage_slice_schema.py` (`CANONICAL_SLICES`,
  `SLICE_CONCERN_FIELD`, `INFRA_CONDITIONAL_SLICES`, `ALWAYS_REQUIRED_SLICES`,
  `validate_slice_set` — BL-392)
- Resolver: `.claude/scripts/resolve_vault_stage.py` (`resolve_stage`, BL-392)
- Konsum-Kanal (read-only): `.claude/commands/_stage.md` (BL-392)
- Delegiert von: `/_stage add` via `Skill(_stage_init)` (BL-412 AK-4, F6)
- Delegation an: BL-409 (Precondition-Gate, exit_criteria-Verify)
- Downstream-Consumer: BL-413 (Stage-Set-Init nutzt `/_stage init`)
- Verifikation: `/_stage sanity-check {nr}` (BL-412 AK-6)
- Spezifikation: BL-412 AK-3 · Modell: BL-412_Model.md W10-W12 · Epic: BL-407
