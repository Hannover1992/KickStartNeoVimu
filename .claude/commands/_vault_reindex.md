# /_vault_reindex — Paralleler Vault-Reindex (Map-Reduce, BL-274)

```yaml
status: active
version: 1.0.0
created: 2026-06-21
updated: 2026-06-21
op: VaultReindex
phase: Meta
type: command
chain_position: standalone
feature_anchor: BL-274
bl_history:
  - BL-274: "Map-Reduce-Reindex-Orchestrator ueber BL-242-Primitiven + BL-194-Lock"
related:
  scripts:
    - .claude/scripts/reindex_vault.py         # Orchestrator (AK-1/B2)
    - .claude/scripts/build_retrieval_index.py  # BL-242-Primitive (REUSE)
    - .claude/scripts/factory_lock.py           # BL-194-Lock (REUSE)
  bls:
    - BL-242  # Index-Primitive: build_index, merge_vault_indexes, serialize_index_json
    - BL-194  # Parallelitaet + Lock: parallelism_budget, factory_lock
    - BL-262  # Resume-Lehre: committed Cursor (SA-6)
```

## Zweck

`/_vault_reindex` bringt den Vault retroaktiv in einen sauberen Index-Zustand: ein **voller
Reindex von Grund auf**, parallelisiert als **Map-Reduce ueber den existierenden BL-242-Index-
Primitiven**. Jede Index- und Lock-Funktion wird WIEDERVERWENDET, nicht neu definiert (DRY, AK-1/N6).

**Scope-Cut (User-Direktive):** Reine Reindex-Orchestrierung optimiert auf Parallelitaet.
KEIN widerspruchs-aufloesender Orchestrator ueber die Zeitachse (kein Truth-Reconciliation, BL-282-artig).

**Erfolgssignal:** `_W_fetch` (Index-First-Read, Schritt 0d) kann den neu persistierten Index laden.

---

## Aufruf

```
/_vault_reindex
/_vault_reindex --resume
/_vault_reindex --budget {N}
/_vault_reindex --vault {pfad}
```

| Parameter | Default | Bedeutung |
|-----------|---------|-----------|
| `--vault` | session-aufgeloest | Absoluter Pfad zum Vault-Root |
| `--budget` | 1 (seriell) | Parallele Map-Slots = `budget - 1`; B=1 -> seriell |
| `--resume` | false | Ueberspringe bereits committete Sektionen (AK-8, SA-6) |

---

## VERTRAG

**LIEST:** Vault-Sektionen via `cut_sections(vault_root)` (Top-Level-Dir-Range, SA-1).
Referenz-Menge fuer Coverage-Verifikation: `git ls-files` (SA-3).

**SCHREIBT:** `{vault}/.claude/output/retrieval_index/_keyword_index.json`
(deterministisch via `serialize_index_json`, `sort_keys=True`, `_W_fetch`-lesbar, AK-7).

**SCHREIBT (intern):** Resume-Cursor `_resume_cursor.json` im selben Verzeichnis (SA-6, AK-8).

**RUFT:** `reindex_vault(vault_root, budget, resume)` in `reindex_vault.py` (Orchestrator).
Dieser ruft ausschliesslich existierende BL-242/BL-194-Primitive:

| Primitiv | Modul | Zweck |
|----------|-------|-------|
| `cut_sections(vault_root)` | `build_retrieval_index` | MAP: Vault in disjunkte Sektionen schneiden (AK-2) |
| `_derive_map_slots(budget)` | `build_retrieval_index` | Parallele Slot-Ableitung aus Budget (AK-3) |
| `build_index(sektion)` | `build_retrieval_index` | MAP: Teil-Index je Sektion bauen (AK-3) |
| `merge_vault_indexes(a, b)` | `build_retrieval_index` | REDUCE: paarweiser Merge (AK-4/6) |
| `serialize_index_json(index)` | `build_retrieval_index` | PERSIST: deterministisches JSON (AK-7) |
| `factory_lock.acquire/release` | `factory_lock` | REDUCE: single-writer Lock (AK-5, SA-4) |
| `read_resume_cursor(out_dir)` | `reindex_vault` | RESUME: committete Sektionen laden (AK-8) |
| `verify_clean_state(index_files, vault_files)` | `reindex_vault` | CLEAN-STATE: Coverage + stale-Eviction (AK-9/10/11) |

**KEIN** neuer Index-Code. **KEIN** neuer Lock-Code. Jeder Build-Schritt delegiert an die Primitiven.

---

## Ablauf: MAP -> REDUCE -> PERSIST -> RESUME -> CLEAN-STATE-VERIFY

### Phase 1 — MAP

```
cut_sections(vault_root)
  -> N Sektionen (Default: Top-Level-Dir-Range, SA-1)
  -> Vereinigung = vollstaendiger Vault-Walk (keine Knotenluecke, AK-2)

_derive_map_slots(budget)
  -> parallele_slots = budget - 1
  -> B=1 -> 0 Slots -> seriell (heutiges Default-Verhalten)

je Sektion (noch nicht im Resume-Cursor):
  build_index([sektion])
  -> Teil-Index im D2-Format {keyword_index, edge_index, ...}
  -> maximal budget-1 Sektionen gleichzeitig (AK-3/N5)
```

Sektions-Builds sind **lock-frei** (disjunkter Schnitt, SA-1/SA-2): die Teil-Indizes schreiben
nie denselben Ziel-Knoten gleichzeitig.

### Phase 2 — REDUCE (unter factory_lock)

```
factory_lock.acquire(scope="global", purpose="REINDEX", worker_id="reindex_vault")

tree_merge_indexes(teil_indizes)          # aus reindex_vault.py
  -> paarweise Faltung (AK-4):
       Level 0: [A, B, C, D]
       Level 1: [merge(A,B), merge(C,D)]
       Level 2: [merge(merge(A,B), merge(C,D))]
  -> Merge-Tiefe: ceil(log2 N)
  -> Dedup ueber Eintrags-Identitaet (AK-6, SA-2): jeder Eintrag einmal

factory_lock.release("reindex_vault")
```

**Lock-Invariante (AK-5/SA-4):** Zu keinem Zeitpunkt schreiben zwei Merge-Schritte gleichzeitig
auf den geteilten Ziel-Index. Der baumartige Merge haelt die Lock-Zeit kurz (AK-4).

### Phase 3 — PERSIST

```
serialize_index_json(merged_keyword_index)
  -> bit-identisches JSON (sort_keys=True, AK-7/N3)
  -> {vault}/.claude/output/retrieval_index/_keyword_index.json

_write_resume_cursor(out_dir, completed_section_keys)
  -> _resume_cursor.json (committed, SA-6)
```

### Phase 4 — RESUME (bei --resume)

```
read_resume_cursor(out_dir)
  -> Liste committeter Sektions-Keys
  -> Sektionen in done_keys -> SKIP (AK-8/N4)
  -> Sektionen nicht in done_keys -> MAP wie normal
```

**RESUME-Invariante (AK-8, BL-262-Lehre):** Der Cursor liegt committed im persistierten
Index-Verzeichnis — nicht in `.claude`-Transients. „Fertig-aber-unverbucht" ist das BL-262-
Anti-Pattern; hier ist „fertig" = cursor-committed.

### Phase 5 — CLEAN-STATE-VERIFY

```
verify_clean_state(index_files, vault_files)    # aus reindex_vault.py
  -> coverage_ok:       jeder vault_file in index_paths (AK-9/N6)
                        fehlende = missing-Liste
  -> stale_evicted_ok:  kein index-entry-Quellpfad ausserhalb vault_set (AK-10)
                        veraltete = stale-Liste
  -> clean_state:       coverage_ok AND stale_evicted_ok (AK-11)
```

Coverage-Referenz: `git ls-files` (SA-3, kanonischer Vault-Stand).
stale-Kriterium: „fehlend im aktuellen Walk" (SA-5, Full-Rebuild-Eigenschaft).

---

## Exit-Status-Matrix

| Situation | Verhalten | Exit |
|-----------|-----------|------|
| Frischer Lauf, Clean-State gruen | Voller Map-Reduce-Reindex, `_keyword_index.json` korrekt | 0 |
| `--resume`, Cursor vorhanden | Nur nicht-committete Sektionen gebaut, dann REDUCE/PERSIST/VERIFY | 0 |
| Coverage ODER stale-Eviction rot | Reindex lief, Clean-State NICHT erreicht; missing/stale in Report | != 0 |
| Vault nicht erreichbar | Abbruch vor MAP, kein partieller Index-Write | != 0 |
| Lock-Timeout | Abbruch, bestehender Index unangetastet | != 0 |

---

## Parameter-Details

### budget (Parallel-Grad)

`budget` steuert die Anzahl gleichzeitiger Map-Agenten via `_derive_map_slots`:

```python
# build_retrieval_index._derive_map_slots(budget)
# B=1 -> 0 parallele Slots -> serieller Loop (Default, heutiges Verhalten)
# B=3 -> 2 parallele Slots -> maximal 2 Sektionen gleichzeitig
# empirisches Maximum: B=5 (BL-194/W9)
```

Budget-Quelle: `parallelism_budget` (BL-194). INV-MODUS-Familie gilt nicht fuer diesen
Budget-Parameter (er ist kein SDF-Modus-Feld; INV-MODUS-5-Bypass-Felder betreffen SDF/IDF).

### vault_root

Wenn nicht via `--vault` angegeben: session-aufgeloest (analog `_W_fetch`-Konvention).
Muss auf ein valides Vault-Root zeigen mit existierendem Vault-Walk.

---

## API-Referenz (reindex_vault.py)

```python
# Haupt-Einstieg:
reindex_vault(vault_root, budget=1, resume=False)
# -> final_index dict {keyword_index: {...}}
# -> schreibt _keyword_index.json + _resume_cursor.json nach out_dir

# REDUCE-Schritt:
tree_merge_indexes(part_indexes)
# -> baumartige paarweise Faltung via merge_vault_indexes
# -> Dedup ueber Eintrags-Identitaet (_entry_identity: json.dumps sort_keys=True)

# RESUME-Cursor lesen:
read_resume_cursor(out_dir)
# -> Liste committeter Sektions-Keys (oder [] bei Erst-Lauf)

# CLEAN-STATE-Verifikation:
verify_clean_state(index_files, vault_files)
# -> dict {coverage_ok, stale_evicted_ok, clean_state, missing, stale}
```

Alle anderen Funktionen (`cut_sections`, `build_index`, `merge_vault_indexes`,
`serialize_index_json`, `factory_lock.acquire/release`) stammen aus BL-242/BL-194-Modulen
und werden nicht neu definiert (AK-1/N6).

---

## Invarianten

- **INV-REINDEX-1 (DRY):** Keine Neudefinition von `build_index`, `merge_vault_indexes`,
  `serialize_index_json`, `factory_lock`. Jeder Aufruf delegiert an die BL-242/BL-194-Primitive.
- **INV-REINDEX-2 (single-writer):** Jeder Ziel-Index-Write laeuft unter `factory_lock`
  (scope="global", purpose="REINDEX"). Zu keinem Zeitpunkt zwei gleichzeitige Merge-Writes.
- **INV-REINDEX-3 (Budget-Deckelung):** Gleichzeitige Map-Agenten <= budget - 1.
  B=1 -> seriell (heutiges Verhalten bleibt sicher erreichbar).
- **INV-REINDEX-4 (Determinismus):** `serialize_index_json` mit `sort_keys=True` ->
  identischer Vault-Stand -> bit-identischer JSON-Output.
- **INV-REINDEX-5 (committed Cursor):** Der Resume-Cursor liegt im persistierten
  Index-Verzeichnis, nicht in `.claude`-Transients. BL-262-Lehre: fertig = cursor-committed.
- **INV-REINDEX-6 (Clean-State = UND):** `clean_state` ist ausschliesslich
  `coverage_ok AND stale_evicted_ok`. Weder Coverage-only noch stale-only genuegt.
- **INV-REINDEX-7 (Scope-Cut):** Truth-Reconciliation (inhaltliche Widersprueche ueber
  Zeitachse) ist NICHT Scope. `/_vault_reindex` setzt den „korrekten inhaltlichen Stand"
  voraus und bringt nur den Index auf vollen, sauberen Abdeckungs-Stand.

---

## Out-of-Scope

| Ausgeschlossen | Begruendung / Folge-BL |
|----------------|------------------------|
| Truth-Reconciliation (BL-282-artig) | Eigenes BL; `/_vault_reindex` baut keinen „inhalts-richtigen" Index |
| Inkrementeller `patch_index`-Pfad | Gegenpol zum Full-Rebuild; bei Bedarf separates BL |
| Neuer Index-/Lock-Code | DRY via BL-242/BL-194 (INV-REINDEX-1) |
| Budget-Partitionierung / per-Sektion-Lock | Spater Optimierungs-Pfad; ein globaler Lock genuegt (SA-4) |
| Automatisches GC / Vault-Pruning | Separate Engine-Health-Massnahme |

---

## Annahmen (Spec SA-1..SA-6)

| SA | Annahme | Default | Risiko-Mitigation |
|----|---------|---------|------------------|
| SA-1 | Sektions-Schnitt = Top-Level-Dir-Range | `cut_sections` Default | `strategy`-Param offen fuer spaetere Sektion-Strategien |
| SA-2 | Dedup-Key = Eintrags-Identitaet (`json.dumps sort_keys=True`) | `_entry_identity` in reindex_vault.py | Explizit getestet (DoD-6) |
| SA-3 | Coverage-Referenz = `git ls-files` | kanonischer Vault-Stand | Filesystem-Walk als dokumentierte Alternative |
| SA-4 | Lock-Granularitaet = 1 globaler scope | scope="global" | Baumartiger Merge haelt Lock-Zeit kurz (AK-4) |
| SA-5 | stale-Kriterium = fehlend im aktuellen Walk | Full-Rebuild-Eigenschaft | Nur Full-Rebuild; inkrementell = separates BL |
| SA-6 | Resume-Cursor committed im Index-Verzeichnis | `_resume_cursor.json` neben `_keyword_index.json` | BL-262-Lehre; DoD-8 verifiziert explizit |

---

## Verwandt

- `.claude/scripts/reindex_vault.py` — Orchestrator: `reindex_vault`, `tree_merge_indexes`,
  `read_resume_cursor`, `verify_clean_state` (BL-274 batch_1)
- `.claude/scripts/build_retrieval_index.py` — BL-242-Primitive: `cut_sections`,
  `_derive_map_slots`, `build_index`, `merge_vault_indexes`, `serialize_index_json`,
  `compute_coverage` (REUSE)
- `.claude/scripts/factory_lock.py` — BL-194-Lock: `acquire`, `release` (REUSE)
- BL-274 — Feature-Parent (Map-Reduce-Reindex + Command + Tests)
- BL-242 — Index-Primitive-Substrat (REUSE, kein Delta)
- BL-194 — Parallelitaet + Lock-Substrat (REUSE, kein Delta)
- BL-262 — Resume-Lehre: committed Cursor-Anti-Pattern
- `_W_fetch.md` — Konsument des persistierten Index (Index-First-Read, Akzeptanz-Signal)
