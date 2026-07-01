# /_stage add {nr} {name} — neue Stage hinzufuegen (Validierung + Init-Delegation)

```yaml
status: active
version: 1.0.0
created: 2026-06-20
op: StageAdd
phase: Meta
chain_position: standalone
feature_anchor: BL-412
type: building-block
```

## Zweck

Fuegt eine neue Stage mit Nummer `{nr}` und Name `{name}` hinzu. Prueft zuerst, dass die
Nummer noch nicht belegt ist und der Name slug-faehig ist — erst dann delegiert `/_stage add`
die eigentliche Slice-Set-Anlage vollstaendig an `Skill(_stage_init)`.

Kernregel: `/_stage add` implementiert KEINE Init-Logik selbst. Es ist der Validierungs-Kanal
vor dem Init-Kanal (F6 aus BL-412_Model.md — kein Code-Duplikat).

**Namens-Abgrenzung:** `/_stage $nr` (BL-392) = read-only Konsum-Kanal; `/_stage init` =
direkter Slice-Set-Init (idempotent, merge-faehig); `/_stage add` = dieser Validierungs-
Vorkanal fuer neue Stages. `/_stage_orchestrate` = Commit-Normierung (anderer Namespace).

## Aufruf

```
/_stage add {nr} {name}

Parameter:
  nr    — Stage-Nummer (Integer, z.B. 4) — muss noch NICHT belegt sein
  name  — Stage-Name als Slug (alphanumerisch + Bindestriche/Unterstriche, kein Leerzeichen)

Beispiele:
  /_stage add 4 load-test
  /_stage add 6 canary-smoke
```

## Ablauf (Pseudocode)

```
1. PARAMETER-VALIDIERUNG — Nr-Format:
   nr = int({nr})             # muss gueltige Integer-Zahl sein
   IF Konvertierung schlaegt fehl:
     -> FAIL "INVALID_NR: '{nr}' ist keine gueltige Ganzzahl" STOP

2. PARAMETER-VALIDIERUNG — Slug:
   name = str({name})
   IF name enthaelt Leerzeichen oder Zeichen ausserhalb [a-zA-Z0-9_-]:
     -> FAIL "INVALID_NAME: '{name}' ist kein gueltiger Slug (alphanumerisch + - _)" STOP

3. KONFLIKT-PRUEFUNG — Nr bereits belegt?
   existing = glob({VAULT}/Stage/stage_{nr}_*/)
   IF existing nicht leer:
     -> FAIL "CONFLICT: Stage {nr} ist bereits belegt ({existing[0]}) — kein Write" STOP

4. DELEGATION AN /_stage init:
   # INV-STAGE-ADD-1: Delegation ist obligatorisch — kein eigener Slice-Bau
   Skill(_stage_init) {nr} {name}
   # _stage_init legt alle 8 Skeleton-Slices an und laeuft validate_slice_set

5. RETURN:
   Ausgabe von _stage_init (Stage-Dir, Slice-Liste, validate_slice_set-Status)
```

## Szenarien

### Szenario 1 — Neue Stage erfolgreich

```
/_stage add 4 load-test

-> nr=4, name="load-test"
-> glob({VAULT}/Stage/stage_4_*/) = leer
-> Delegation: Skill(_stage_init) 4 load-test
-> Stage 4 (load-test) initialisiert — 8 Slices, validate_slice_set: PASS
```

### Szenario 2 — Nr bereits belegt

```
/_stage add 3 integration   # stage_3_integration/ existiert bereits

-> glob({VAULT}/Stage/stage_3_*/) = [stage_3_integration/]
-> FAIL "CONFLICT: Stage 3 ist bereits belegt (stage_3_integration/) — kein Write"
-> kein Write, kein Init
```

### Szenario 3 — Ungueltige Nr

```
/_stage add abc canary

-> FAIL "INVALID_NR: 'abc' ist keine gueltige Ganzzahl"
-> kein Write
```

### Szenario 4 — Ungueltige Name (Leerzeichen)

```
/_stage add 5 "my stage"

-> FAIL "INVALID_NAME: 'my stage' ist kein gueltiger Slug (alphanumerisch + - _)"
-> kein Write
```

### Szenario 5 — BL-409-Delegation fehlt (via _stage_init)

```
/_stage add 5 e2e-live   # BL-409 nicht verfuegbar

-> Validierung OK
-> Delegation: Skill(_stage_init) 5 e2e-live
-> _stage_init gibt WARN "BL-409 nicht gefunden — Precondition-Gate uebersprungen" aus
-> Ablauf laeuft weiter, alle 8 Slices angelegt
```

## Naht: add vs. init

| Verantwortung | Command |
|---------------|---------|
| Nr-Konflikt pruefen (neue Stage noch frei?) | `/_stage add` |
| Slug-Format pruefen | `/_stage add` |
| Slice-Set anlegen (8 Skeletons) | `/_stage init` (via Delegation) |
| Merge-Idempotenz (fehlende Slices ergaenzen) | `/_stage init` |
| Precondition-Delegation an BL-409 | `/_stage init` |
| validate_slice_set Post-Check | `/_stage init` |

`/_stage add` = Tuer-Check vor dem Einlass; `/_stage init` = das Einrichten danach.
Die Naht ist sauber: add prueft nur den Einzug (keine Kollision), init richtet ein.

## Invarianten

- **INV-STAGE-ADD-1 (Delegation obligatorisch):** `/_stage add` delegiert die Slice-Set-Anlage
  IMMER via `Skill(_stage_init)`. Keine eigene Init-Logik in `/_stage add` — kein Code-Duplikat
  zur `/_stage init`-Implementierung (F6 aus BL-412_Model.md).

- **INV-STAGE-ADD-2 (Fail-before-Write):** Alle Validierungen (Nr-Format, Slug-Format,
  Konflikt-Pruefung) laufen VOR der Delegation. Bei jedem FAIL: kein Write, kein
  `Skill(_stage_init)`-Aufruf, sofortiger STOP.

- **INV-STAGE-ADD-3 (Kein Merge-Anwendungsfall):** `/_stage add` ist fuer neue Stages.
  Merge-Idempotenz (fehlende Slices ergaenzen bei bestehender Stage) gehoert zu `/_stage init`
  — direkt aufrufen wenn eine Stage bereits existiert aber unvollstaendig ist.

## Verwandt

- Init-Delegate: `.claude/commands/_stage_init.md` (BL-412 AK-3 — die tatsaechliche Anlage)
- Schema + Validator: `.claude/scripts/stage_slice_schema.py` (`CANONICAL_SLICES`,
  `validate_slice_set` — BL-392)
- Resolver: `.claude/scripts/resolve_vault_stage.py` (`resolve_stage`, BL-392)
- Konsum-Kanal (read-only): `.claude/commands/_stage.md` (BL-392)
- Downstream-Consumer: BL-413 (Stage-Set-Init nutzt `/_stage init` direkt)
- Verifikation: `/_stage sanity-check {nr}` (BL-412 AK-6)
- Spezifikation: BL-412 AK-4 · Modell: BL-412_Model.md W7 · Epic: BL-407
