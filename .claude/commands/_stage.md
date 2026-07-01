# /_stage $nr — Stage-Slice-Kanal (step-relevante Slice(s) in-Context)

```yaml
status: active
version: 1.0.0
created: 2026-06-19
op: StageSliceChannel
phase: Meta
chain_position: standalone
feature_anchor: BL-392
type: building-block
```

## Zweck
Landet den/die fuer den fragenden Step **relevanten Slice(s)** einer Stage in-Context — **NICHT das ganze
Stage-Doc** (W-STAGE-1, single unit of work). Ein TDD-Green-Worker bekommt `execute` (+`health_check`), nicht
die seitenlange Docker-Setup-Prosa. Read-only Konsum-Kanal ueber den glob-faehigen Resolver
`resolve_vault_stage` (BL-392 AK-GLOB). Migriert wird **nichts** — `/_stage` landet nur SCHON-vorhandene Slices;
Dual-Read (Vault-Slice ⟶ Legacy-Monolith) ist transparent.

**Namens-Abgrenzung (NICHT verwechseln):** `/stage` (ohne Unterstrich) = Commit-Normen-Doc; `/_stage_orchestrate`
= Commit-Normierung + Security-Gate. `/_stage` (mit Unterstrich) = **dieser** Stage-Slice-Kanal.

## Aufruf
```
/_stage $nr                 # ganzer 8-Slice-Satz der Stage N (Identitaet + Slice-Map ueber _index)
/_stage $nr {concern}       # NUR der eine Concern-Slice (z.B. /_stage 3 execute fuer TDD-Red/Green)
```
`{concern}` ∈ den 8 kanonischen Slice-Namen (s.u.). Ohne `{concern}` wird der `_index`-Slice (Identitaet +
`slice_map`) gelandet, damit der Caller sieht, welche Slices existieren / `skip` sind.

## Die 8 kanonischen Concern-Slices (`stage_slice_schema.CANONICAL_SLICES`)
```
_index · execute · setup · teardown · health_check · resources · concurrency_class · exit_criteria
```
(Monitor = wo das Resultat landet = TEIL von `execute`, kein 9. Slice — W-AK-MON.)

## Ablauf (Pseudocode)
```
1. n        = int($nr)
   concern  = $concern ?? null        # optionaler 2. Positions-Param

2. handle = resolve_vault_stage.resolve_stage(n)        # StageHandle | None (Glob {VAULT}/Stage/stage_n_*/)
   IF handle is None:
     -> "NOT_FOUND: keine Stage {n} (weder Vault-Slice-Satz noch Legacy-Monolith)." STOP (read-only, kein Write).

3. # Concern-Selektion: explizit gegeben ODER step-relevant abgeleitet (s. Step->Slice-Tabelle).
   selected = (concern != null) ? [concern]
                                 : step_relevant_slices(caller_step)   # Default ohne Step-Hint: ["_index"]

4. FOR slice IN selected:
     IF slice NOT IN CANONICAL_SLICES:
       -> "UNKNOWN_SLICE: '{slice}' ist kein kanonischer Concern." weiter/STOP.
     IF handle.is_legacy:
       # Dual-Read transparent: Legacy-Monolith hat KEINE Slice-Datei -> in-memory View.
       view = handle.slice_view(slice)                  # dict (aus Monolith-Frontmatter abgeleitet)
       land_in_context(slice, source="legacy:" + str(handle.legacy_path), content=view)
     ELSE:
       path = handle.resolve_slice(slice)               # GENAU dieser {slice}.md-Pfad (single unit of work)
       land_in_context(slice, source=str(path))         # Read den einen Slice (read-only)

5. # NIE das ganze Doc, NIE einen nicht-angefragten Slice landen. Kein Vault-/State-Write.
```

`step_relevant_slices(caller_step)` ist die Selektions-Heuristik aus der Slice-Consumer-Map (BL-392):

| Fragender Step | Gelandete Slice(s) | Begruendung |
|----------------|--------------------|-------------|
| TDD-Red / TDD-Green / `_TDD_execute` | `execute` (+ `health_check`) | Start (testbefehl + Filter + Monitor) + Bereitschafts-Gate — **nicht** setup/teardown/resources |
| Stage-Setup-Step (BL-408) | `setup` (+ `health_check`) | System in Stage-Zustand bringen + Verify |
| Stage-Teardown-Step (BL-408) | `teardown` | sauber hinterlassen (finally) |
| Resource-Claim/Release (BL-368), IDF-Planer (BL-415) | `resources` | Deklaration + teilbar\|unteilbar + Caps |
| Scheduler / Parallel-Suitability (BL-342/368/415) | `concurrency_class` | concurrency_class + depends_on + rationale |
| Precondition-Gate (BL-409) / Stage-Exit | `exit_criteria` | qg/tests_gruen/fan_in/kanarienvogel |
| `/_stage $nr` ohne Concern, sanity-check, Findability | `_index` | Identitaet + Narrativ + `slice_map` |

## `/_stage_init` — STUB (kein Voll-Init in BL-392)
`/_stage_init` ist hier **nur ein Stub**. Der Voll-Init ist bewusst NICHT BL-392-Scope und delegiert:

- **Voll-Init (Stage-Set im Init anlegen):** [[BL-413]] — Stage-Set-Definition im Init.
- **Precondition-Verify (exit_criteria-Gate):** [[BL-409]] — Stage-Precondition-Gate.
- **Command-Familie (`help`/`init`/`add`/`update`/`sanity-check`):** [[BL-412]] — `/_stage`-Familie; `sanity-check`
  prueft die Slice-Vollstaendigkeit gegen `stage_slice_schema` (das Schema = BL-392).

```
/_stage_init [...]   -> STUB: kein Voll-Init. Delegiert an BL-413 (Voll-Init) / BL-409 (Precondition) / BL-412 (Familie).
                        BL-392 liefert NUR den Lese-Kanal /_stage + das Slice-Schema, KEINEN Init-Bau.
```

**Abgrenzung zu [[BL-414]] (NICHT hier):** `/_stage $nr` loest die Slice-Resolution fuer eine **gegebene** Nummer
`n` (BL-392 = WIE: aufloesen). Welche Stage **aktiv** ist (`current_stage` → liefert das `n` + routet den
Orchestrator) gehoert zu BL-414 (WANN/WELCHE). `/_stage` nimmt `n` als Argument; es liest `current_stage` NICHT.

## Invarianten (BL-392, AK-STAGE-CHANNEL)
- **INV-STAGE-CHANNEL-1 (read-only Konsum):** `/_stage` landet nur Context, schreibt NIE Vault/State/Code. Reine
  Resolution + Read ueber `resolve_vault_stage` (das selbst read-only + fail-safe ist).
- **INV-STAGE-CHANNEL-2 (nur SCHON-vorhandene Slices):** `/_stage` migriert/erzeugt KEINE Slices. Fehlt der
  Vault-Slice-Satz, greift der Resolver-Dual-Read auf den Legacy-Monolith — `/_stage` baut nichts.
- **INV-STAGE-CHANNEL-3 (Dual-Read transparent):** Vault-Slice vs. Legacy-Monolith ist fuer den Caller
  unsichtbar: bei `is_legacy` kommt der Inhalt als in-memory `slice_view` (kein Datei-Pfad), bei Vault als
  `{slice}.md`-Pfad — beide landen denselben Concern.
- **INV-STAGE-CHANNEL-4 (single unit of work):** NIE das ganze Doc, NIE einen nicht-angefragten Slice. Der
  fragende Step bekommt GENAU seinen Concern (W-SLICE-2).
- **INV-STAGE-CHANNEL-5 (Stub-Grenze):** `/_stage_init` baut KEINEN Voll-Init (Scope-Creep in BL-413 verboten) —
  nur Delegation.

## Szenario-Verify (markdown_uncoverable — statt TDD)
1. **TDD-Red-Worker ruft `/_stage 3 execute`:** Schritt 3 nimmt `concern="execute"` (explizit) → `selected=["execute"]`.
   Schritt 4 (Vault, `is_legacy=false`) → `handle.resolve_slice("execute")` liefert GENAU den `execute.md`-Pfad;
   gelandet wird NUR der `execute`-Slice (testbefehl + Filter + Monitor) — **nicht** setup/teardown/resources.
   → single unit of work erfuellt (INV-STAGE-CHANNEL-4). Deckt sich mit `_TDD_execute.md` (das real
   `resolve_vault_stage.resolve_slice(N, "execute")` ruft).
2. **Stage 3 noch nicht migriert (Dual-Read):** Schritt 2 `resolve_stage(3)` findet kein `{VAULT}/Stage/stage_3_*/`
   → Dual-Read-Fallback → `is_legacy=true`, `legacy_path=.claude/meta/implementation/stage_3.md`. Schritt 4 nimmt
   den `is_legacy`-Zweig: `handle.slice_view("execute")` liefert die `execute`-Felder in-memory aus dem
   Monolith-Frontmatter. Der Caller sieht denselben Concern, ohne zu wissen, dass es Legacy war
   (INV-STAGE-CHANNEL-3) — und `/_stage` schreibt nichts (INV-STAGE-CHANNEL-2).
3. **Jemand sucht den `/_stage_init`-Voll-Init:** findet im Stub-Abschnitt die explizite Delegation an BL-413
   (Voll-Init) / BL-409 (Precondition) / BL-412 (Familie) + die BL-414-Abgrenzung — KEIN Halb-Init in BL-392
   (INV-STAGE-CHANNEL-5).

## Verwandt
- Resolver: `resolve_vault_stage.py` (`resolve_stage`/`resolve_slice`/`StageHandle.slice_view`, BL-392 AK-GLOB) ·
  Schema: `stage_slice_schema.py` (`CANONICAL_SLICES`, BL-392 AK-SLICE-SCHEMA).
- Consumer (lesen ueber denselben Resolver, AK-CONSUMER-REWRITE): `_TDD_setup`/`_TDD_teardown`/`_TDD_execute` ·
  `_IDF_berater_stagePlanner` · `t_script.py` · `tdd_stages_ready.py` · `stage_infra_schema.py`.
- BL-392 (Heimat) · Epic [[BL-407]] · Atomisierungs-Doktrin [[BL-309]] · Familie [[BL-412]] · Voll-Init [[BL-413]] ·
  Precondition [[BL-409]] · current_stage-Routing [[BL-414]] · Resource-Consumer [[BL-368]]/[[BL-415]].
```
