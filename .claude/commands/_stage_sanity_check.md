# /_stage sanity-check {nr} — Stage-Slice-Set strukturell verifizieren

```yaml
status: active
version: 1.0.0
created: 2026-06-20
op: StageSanityCheck
phase: Meta
chain_position: standalone
feature_anchor: BL-412
type: building-block
```

## Zweck

Verifiziert deterministisch, dass Stage N die Hand-und-Brot-Faehigkeiten feuern kann —
ohne laufendes System. Prueft die 5 Kern-Faehigkeiten (a-e) auf Slice-Ebene: Slice vorhanden,
Concern-Felder valide, Skip-Sentinel explizit, Monitor-Kanal ableitbar.

**Zwei Tier:**
- **Strukturell-deterministisch (Pflicht-Tier):** Verifiziert via `stage_slice_schema.validate_slice_set`
  ob der Slice-Set vollstaendig ist und die Concern-Felder syntaktisch valide sind. Laeuft IMMER —
  kein laufendes System, kein Docker, kein Netz vorausgesetzt.
- **Live-Tier (opt-in `--live`):** Fuehrt die Tests echt aus. Der CLI-Wrapper
  `.claude/scripts/sanity_check_stage.py` (kommt in batch_6) uebernimmt den Live-Pfad;
  dieses Command-Doc deckt den strukturellen Pflicht-Tier.

**Keine Re-Implementierung des Slice-Validators:** Konsum via
`stage_slice_schema.validate_slice_set` (BL-392 — INV-STAGE-SC-2).

## Aufruf

```
/_stage sanity-check {nr} [--live]

Parameter:
  nr      — Stage-Nummer (Integer, z.B. 3)
  --live  — opt-in: Live-Tier aktivieren (echter Test-Run via sanity_check_stage.py)

Beispiele:
  /_stage sanity-check 3           # strukturell-Tier (Pflicht, immer)
  /_stage sanity-check 3 --live    # strukturell + live (opt-in)
```

## Ablauf (Pseudocode)

```
0. PARAMETER:
   nr   = int({nr})
   live = "--live" IN args

1. STAGE AUFLOESEN:
   handle = resolve_vault_stage.resolve_stage(nr)
   IF handle is None:
     -> FAIL "NOT_FOUND: Stage {nr} existiert nicht." STOP

   stage_dir = handle.stage_dir   # Pfad zum Slice-Verzeichnis

2. STRUKTURELLER VOLLSTAENDIGKEITS-CHECK (Pflicht-Tier, INV-STAGE-SC-2):
   result = stage_slice_schema.validate_slice_set(stage_dir)
   # SliceSchemaResult: valid, missing_slices, errors (je mit recovery_hint)
   # Skip-Sentinels (skip:true / none:true) werden als konform akzeptiert.

3. SUB-CHECK (a) — Gezielt EIN Test starten:
   execute_slice = handle.slice_view("execute")   # dict aus execute.md
   testbefehl    = execute_slice.get("testbefehl")

   IF testbefehl is None OR testbefehl in (null, ""):
     result_a = FAIL
     hint_a   = "execute.testbefehl fehlt oder Leer-Defekt — fuehre /_stage init {nr} ... aus"
   ELSE:
     result_a = PASS
     hint_a   = null

   # Live-Tier (opt-in):
   IF live:
     dry_run_result = ausfuehren(testbefehl, "--dry-run")   # 1 Test, dry-run
     result_a = PASS IF dry_run_result.ok ELSE FAIL
     hint_a   = dry_run_result.stderr IF FAIL ELSE null

4. SUB-CHECK (b) — Handvoll/Subset Tests:
   # Filter-Parameter im execute-Slice vorhanden?
   hat_filter = ("--filter" IN testbefehl OR "--tests" IN testbefehl
                 OR execute_slice.get("filter") is not None)
                IF testbefehl else False

   IF not hat_filter:
     result_b = WARN
     hint_b   = "execute.testbefehl enthaelt kein --filter / execute.filter fehlt — " +
                "Subset-Aufruf moeglich aber nicht deklariert (kein FAIL, nicht ALWAYS_REQUIRED)"
   ELSE:
     result_b = PASS
     hint_b   = null

   # Live-Tier: kein zusaetzlicher Lauf (strukturelle Pruefung genuegt fuer b)

5. SUB-CHECK (c) — Alle Tests (vollstaendig) ausfuehren koennen:
   cc_slice = handle.slice_view("concurrency_class")
   cc_val   = cc_slice.get("concurrency_class")

   IF "concurrency_class" IN result.missing_slices OR cc_val in (None, null, ""):
     result_c = FAIL
     hint_c   = "concurrency_class-Slice fehlt oder Leer-Defekt — " +
                "fuehre /_stage update {nr} concurrency_class <wert> aus"
   ELIF NOT result.valid:
     result_c = FAIL
     hint_c   = "validate_slice_set meldet Defekte: " + str(result.errors)
   ELSE:
     result_c = PASS
     hint_c   = null

   # Live-Tier: ganzer Stage-Lauf via t_script.py (ohne --filter)

6. SUB-CHECK (d) — Monitoring liest Ergebnis (TDD-STATE.md, F3):
   # Monitor ist kein 9. Slice — er ist Teil von execute (W-AK-MON, W2).
   # Strukturell: ist der Monitor-Kanal aus execute ableitbar?
   monitor_ableitbar = (testbefehl is not None AND
                        ("LogFileName" IN testbefehl OR "TDD-STATE" IN str(execute_slice)))

   IF not monitor_ableitbar:
     result_d = WARN
     hint_d   = "Monitor-Kanal (TDD-STATE.md / LogFileName) nicht aus execute ableitbar — " +
                "pruefe execute.testbefehl auf LogFileName-Parameter"
   ELSE:
     result_d = PASS
     hint_d   = null

   # Live-Tier:
   IF live:
     tdd_state_path = ermittle_tdd_state_pfad(execute_slice)
     IF NOT tdd_state_path.exists():
       result_d = FAIL
       hint_d   = "TDD-STATE.md nicht gefunden unter " + str(tdd_state_path)
     ELIF NOT hat_monitor_sektion(tdd_state_path):
       result_d = WARN
       hint_d   = "TDD-STATE.md existiert, aber monitor-Sektion fehlt — _TDD_monitor noch nicht gelaufen"
     ELSE:
       result_d = PASS

7. SUB-CHECK (e) — Setup + Teardown erreichbar:
   # Fuer jeden INFRA_CONDITIONAL-Slice: vollstaendig ODER explizit skip.
   # Kein Leer-Defekt toleriert (Slice da, Concern-Feld fehlt, kein Skip-Sentinel).
   result_e  = PASS
   hints_e   = []

   FUER slice IN stage_slice_schema.INFRA_CONDITIONAL_SLICES:
     # INFRA_CONDITIONAL = (setup, teardown, health_check)
     IF slice IN result.missing_slices:
       result_e = FAIL
       hints_e.append("{slice}.md fehlt — fuehre /_stage init {nr} ... aus")
     ELSE:
       s = handle.slice_view(slice)
       concern_field = stage_slice_schema.SLICE_CONCERN_FIELD[slice]
       val = s.get(concern_field)
       skip_explicit = s.get("skip") in (True, "true", "none") OR s.get("none") == True

       IF val is None AND NOT skip_explicit:
         result_e = FAIL
         hints_e.append("{slice}.{concern_field} Leer-Defekt — " +
                        "setze skip:true (/_stage update {nr} {slice} skip) oder " +
                        "befuelle den Slice (/_stage update {nr} {slice} <wert>)")
       # PASS wenn val vorhanden ODER skip_explicit (Skip-Sentinel = explizit valide, W-SLICE-3)

   hint_e = "\n".join(hints_e) IF hints_e ELSE null

   # Live-Tier: smoke-call setup/teardown jeweils mit dry-run (kein Datenverlust)

8. GESAMT-REPORT:
   gesamt = worst_case(result_a, result_b, result_c, result_d, result_e)
   # Rang: FAIL > WARN > PASS

   gib aus:
     "=== /_stage sanity-check {nr} ==="
     "  Stage-Dir: {stage_dir}"
     "  Tier: {'strukturell + live' IF live ELSE 'strukturell'}"
     ""
     "  (a) Gezielt EIN Test         : {result_a}"  + (" — " + hint_a IF hint_a)
     "  (b) Handvoll/Subset          : {result_b}"  + (" — " + hint_b IF hint_b)
     "  (c) Alle Tests (vollstaendig): {result_c}"  + (" — " + hint_c IF hint_c)
     "  (d) Monitoring (TDD-STATE.md): {result_d}"  + (" — " + hint_d IF hint_d)
     "  (e) Setup + Teardown         : {result_e}"  + (" — " + hint_e IF hint_e)
     ""
     "  Gesamt: {gesamt}"
     IF gesamt == PASS:
       "  -> Stage {nr} strukturell vollstaendig. Hand-und-Brot-Faehigkeiten: bereit."
     ELIF gesamt == WARN:
       "  -> WARN: Stage {nr} pruefbar, aber nicht alle optionalen Felder deklariert."
     ELSE:
       "  -> FAIL: Stage {nr} hat Pflicht-Defekte. Sieh recovery_hints oben."
```

## Sub-Checks auf einen Blick

| Sub-Check | Prueft | Strukturell (Pflicht) | Live (opt-in) | Status-Typ |
|-----------|--------|-----------------------|---------------|------------|
| (a) EIN Test | `execute.testbefehl` syntaktisch valide | Feld vorhanden + nicht null | dry-run 1 Test | PASS / FAIL |
| (b) Subset | Filter-Parameter deklariert | `--filter` oder `execute.filter` vorhanden | (kein zus. Lauf) | PASS / WARN |
| (c) Alle Tests | `concurrency_class` + `execute` vollstaendig | `validate_slice_set` PASS | ganzer Stage-Lauf | PASS / FAIL |
| (d) Monitoring | Monitor-Kanal ableitbar aus `execute` | `LogFileName`/`TDD-STATE` in `testbefehl` | TDD-STATE.md existiert + monitor-Sektion | PASS / WARN |
| (e) Setup/Teardown | INFRA_CONDITIONAL-Slices vollstaendig oder skip | concern-Feld valide ODER `skip:true` | smoke-call (dry-run) | PASS / FAIL |

**Gesamt-Status = worst_case(a, b, c, d, e).** FAIL > WARN > PASS. Jeder FAIL/WARN traegt
einen `recovery_hint`.

## Strukturell vs. Live — Detail

### Strukturell-Tier (Pflicht, immer ausfuehrbar)

Verifiziert Slice-Vollstaendigkeit und syntaktische Korrektheit:
- `stage_slice_schema.validate_slice_set(stage_dir)` prueft fehlende Slices + Leer-Defekte
- `skip: true` bei INFRA_CONDITIONAL-Slices = explizit valide (kein Leer-Defekt)
- Concern-Felder aus `SLICE_CONCERN_FIELD` werden auf `null` / leer geprueft
- Kein laufendes System, kein Docker, kein Netz vorausgesetzt (INV-STAGE-SC-1)

### Live-Tier (opt-in, `--live`)

Fuehrt die Tests echt aus — als Eskalation zum Strukturell-Tier:
- Delegiert an `.claude/scripts/sanity_check_stage.py` (CLI-Wrapper, kommt in batch_6)
- Sub-Check (a): echter dry-run des `testbefehl`
- Sub-Check (c): ganzer Stage-Lauf via `t_script.py`
- Sub-Check (d): TDD-STATE.md auf Existenz + monitor-Sektion geprueft
- Sub-Check (e): smoke-call setup/teardown (dry-run)
- Timeout-Default: 30 s; FAIL-Kategorie bei Ueberschreitung: `LIVE_TIMEOUT` (SA-1)

## Szenario-Verify

### Szenario 1 — vollstaendiger Slice-Set, strukturell PASS

```
/_stage sanity-check 3

-> handle = resolve_stage(3): OK, stage_dir = {VAULT}/Stage/stage_3_integration/
-> validate_slice_set: valid=True, missing_slices=[], errors=[]
-> (a) execute.testbefehl = "dotnet test --filter ..." -> PASS
-> (b) "--filter" in testbefehl -> PASS
-> (c) concurrency_class.concurrency_class = "sequential" -> PASS
-> (d) "LogFileName" in testbefehl -> PASS (Monitor-Kanal ableitbar)
-> (e) setup: skip=true -> PASS; teardown: skip=true -> PASS; health_check: skip=true -> PASS
-> Gesamt: PASS
-> "Stage 3 strukturell vollstaendig. Hand-und-Brot-Faehigkeiten: bereit."
```

### Szenario 2 — execute.testbefehl fehlt (Leer-Defekt)

```
/_stage sanity-check 5

-> validate_slice_set: errors=[{concern: execute, field: testbefehl, hint: "testbefehl ist null"}]
-> (a) execute.testbefehl = null -> FAIL: "execute.testbefehl fehlt — fuehre /_stage init 5 ... aus"
-> (c) execute nicht vollstaendig -> FAIL
-> Gesamt: FAIL
```

### Szenario 3 — INFRA_CONDITIONAL mit Leer-Defekt (kein skip, kein Wert)

```
/_stage sanity-check 4

-> setup.commands = null, skip nicht gesetzt
-> (e) setup: Leer-Defekt -> FAIL: "setup.commands Leer-Defekt — setze skip:true oder befuelle Slice"
-> Gesamt: FAIL
```

### Szenario 4 — WARN (kein Filter-Feld, alles andere OK)

```
/_stage sanity-check 2

-> alle Slices vorhanden, execute.testbefehl = "dotnet test" (kein --filter)
-> (b) kein Filter -> WARN: "execute.testbefehl enthaelt kein --filter..."
-> (a)(c)(d)(e) alle PASS
-> Gesamt: WARN
```

### Szenario 5 — Stage nicht gefunden

```
/_stage sanity-check 99

-> resolve_stage(99) = None
-> FAIL "NOT_FOUND: Stage 99 existiert nicht." STOP
```

## CLI-Wrapper (kommt in batch_6)

`.claude/scripts/sanity_check_stage.py` ist der optionale CLI-Wrapper (F4, W18), der
`stage_slice_schema.validate_slice_set` aufruft, die 5 Sub-Checks (a-e) ausfuehrt und
strukturierten Report ausgibt. Das `--live`-Flag aktiviert den echten Test-Run.

Verwendung (wenn verfuegbar):
```
py .claude/scripts/sanity_check_stage.py {nr}
py .claude/scripts/sanity_check_stage.py {nr} --live
```

Dieser Command (`_stage_sanity_check.md`) definiert das Pseudocode-Modell und den
Ablauf — `sanity_check_stage.py` ist Automatisierungs-Komfort, kein Ersatz.

## Invarianten

- **INV-STAGE-SC-1 (strukturell immer ausfuehrbar):** Der strukturell-deterministiche Tier laeuft
  IMMER — kein laufendes System, kein Docker, kein Netz vorausgesetzt. Live-Tier ist opt-in
  (`--live`). Kein silent-skip des strukturellen Tiers.

- **INV-STAGE-SC-2 (kein Re-Implement des Slice-Schema-Validators):** `/_stage sanity-check`
  implementiert den Slice-Schema-Validator NICHT neu. Konsum via
  `stage_slice_schema.validate_slice_set(stage_dir)` (BL-392). Die 8 Slice-Namen kommen
  ausschliesslich aus `stage_slice_schema.CANONICAL_SLICES`.

- **INV-STAGE-SC-3 (Skip-Sentinel akzeptiert):** `skip: true` (und `none: true`) bei
  INFRA_CONDITIONAL-Slices ist kein Leer-Defekt — explizit valide. Kein FAIL fuer einen
  Slice mit gesetztem Skip-Sentinel.

- **INV-STAGE-SC-4 (worst-case Gesamt-Status):** Gesamt-Status = worst_case(a, b, c, d, e).
  Kein PASS wenn ein Sub-Check FAIL oder WARN hat. Recovery-Hint bei jedem FAIL/WARN Pflicht.

- **INV-STAGE-SC-5 (kein Write):** `/_stage sanity-check` schreibt NICHTS — weder Slices noch
  State noch TDD-STATE.md. Reine Verifikation (read-only, analog INV-STAGE-CHANNEL-1).

## Verwandt

- Schema + Validator: `.claude/scripts/stage_slice_schema.py` (`CANONICAL_SLICES`,
  `SLICE_CONCERN_FIELD`, `INFRA_CONDITIONAL_SLICES`, `validate_slice_set` — BL-392)
- Resolver: `.claude/scripts/resolve_vault_stage.py` (`resolve_stage`, BL-392)
- Konsum-Kanal (read-only): `.claude/commands/_stage.md` (BL-392)
- Slice-Set anlegen: `.claude/commands/_stage_init.md` (BL-412 AK-3)
- Slice mutieren: `.claude/commands/_stage_update.md` (BL-412 AK-5)
- CLI-Wrapper (kommt): `.claude/scripts/sanity_check_stage.py` (BL-412 batch_6)
- Monitor-Muster: `.claude/commands/_TDD_monitor.md` (TDD-STATE.md-Kanal, F3)
- Test-Start-Muster: `.claude/commands/_T_script.md` (gezielt EIN/Handvoll/alle Tests)
- Setup/Teardown-Muster: `.claude/commands/_TDD_setup.md`, `.claude/commands/_TDD_teardown.md`
- Spezifikation: BL-412 AK-6 · Modell: BL-412_Model.md W13-W18 · Epic: BL-407
