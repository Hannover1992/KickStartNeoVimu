# _PT_berater_materialize (Pattern-Extraction Stage 7)

```yaml
type: berater
status: active
version: 1.0.1
created: 2026-06-02
updated: 2026-06-16   # BL-374 AK-3: --target-vault wird vom Orchestrator IMMER empfangen (deterministischer Vault); vault_root=VAULT in add_arch + lifecycle explizit gethreaded → tier-1-Override, hardcoded resolve_vault_root-Fallback nie erreicht.
op: PatternExtraction
phase: "7"
chain_position: "siebte Stage in _PT_orchestrate — nach forensic, vor report. EINZIGE destruktive Stage."
feature_anchor: BL-237 (EINSTUFIG materialize + Counter via pattern_library.py) + BL-256 (DOM-Write-Seam) + BL-257 (FAC-Write-Seam) — 4-Achsen→4-Library-Routing
model_tier: ceiling  # opus — Materialisierungs-Urteil + Counter-Steuerung
```

## Zweck (EIN Job)

**Materialisiere die geernteten Patterns EINSTUFIG und reife die Counter** — die EINZIGE Stelle im
Orchestrator, die die Welt (Libraries) beruehrt. Aus `.classify` (3-Achsen-Zuweisung) und `.forensic`
(Hypothesen + lifecycle_hint) werden Patterns direkt via `pattern_library.py add` in die **4 Libraries**
(Pattern/Semantic/Domain/Factoring, scope-geroutet via `_SCOPE_LIB`) angelegt und der Counter
via `pattern_library.py lifecycle` (pfad-1 usage++ / pfad-2 broken++) gereift. **EINSTUFIG** — kein
Kandidat→extract-2-Hop (der 95%-Leak von DCSRE-486, INV-PTO-3). **NIE** subprocess `.md`.

> **Single Unit of Work (/_help P-10):** liest .classify + .forensic, materialisiert EINSTUFIG +
> reift Counter, schreibt EINEN eigenen Slot (.materialize), stirbt. **quiescenz-gated VOR jedem Write.**

## Quiescenz-Gate (INV-PTO-2 / INV-PTO-3 — PFLICHT VOR Write)

```
VOR jedem Library-Write (add/lifecycle):
  gate = Bash("py {VAULT}/.claude/scripts/manifest_quiescence.py check {BL_ID}" [+ quiescenz_override_arg])
  IF gate == BUSY AND NOT --quiescenz-override:
    → ABORT diese Stage (kein Write): SCHREIBE materialize={status: DEFERRED_BUSY}; RETURN
    (Stages 1-6/8 sind read-only weiter gelaufen; der Orchestrator-Spine hat Stage 7 ggf. schon
     BUSY-geskippt — dieser Gate ist die zweite, berater-lokale Verteidigung. 486-Incident-Lehre.)
```
Das `quiescenz_override_arg` wird vom Orchestrator-Spine durchgereicht (G-5) — der Berater berechnet das
Gate-Ergebnis nicht neu aus dem Nichts, sondern fuehrt den Gate-Check mit den durchgereichten Args aus.

> **BL-374 AK-3 — `--target-vault` wird jetzt IMMER empfangen** (nicht nur im `--quiescenz-override`-Zweig).
> Der Orchestrator loest `{VAULT}` deterministisch via `current_context.py` auf und reicht `--target-vault={VAULT}`
> bei JEDEM Stage-7-Spawn durch. `VAULT` ist damit der deterministische Ziel-Vault fuer ALLE Library-Writes
> (`add_arch`/`lifecycle`): explizit als `vault_root=VAULT` gethreaded → `pattern_library.resolve_vault_root`'s
> tier-1 (explizites Override) gewinnt IMMER, der hardcoded 4-tier-Fallback wird auf dem Harvest-Pfad nie erreicht.

## WORTHINESS-Seam (B-2 — AUFGELOEST in batch_C5, AK-CTX-WORTHINESS-EXTRACT)

```python
# BL-237 batch_C5 (AK-CTX-WORTHINESS-EXTRACT, F1/§4.1): is_pattern_worthy() ist jetzt eine
# aufrufbare Single-Source in pattern_library.py (5 Signal-Klassen). Der frueher konservative
# no-op-Fallback (INV-MAT-5 worthiness_pending) ist AUFGELOEST — der echte Aufruf gatet jetzt.
import pattern_library as pl
worthy = pl.is_pattern_worthy(candidate)   # echte 5-Signal-Klassen-Heuristik (kein Fallback-Pass)
# worthiness_pending = false (C5 gebaut). KEIN Doppel-Impl der Heuristik hier (Extract-not-reimplement).
```

## VERTRAG

```
LIEST:
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.classify.{semantic,architectural,fachlich,factoring}[]   (4 Achsen → 4 Libraries; was wohin)
    BERATER_OUTPUTS_PT.forensic.verdicts[]                            (lifecycle_hint + boundary_note)
  {VAULT}/Libraries/PatternLibrary/_index.md                          (Dedup vor add, read)
  WORKING_DIR via resolve_bl_path.py

RUFT (Reuse — INV-PTO-3/INV-PTO-6, NIE neu bauen, NIE subprocess .md):
  pattern_library.py add_arch(...)        # EINSTUFIG anlegen
  pattern_library.py lifecycle(... pfad-1|pfad-2 ...)   # usage++ / broken++
  manifest_quiescence.py check {BL_ID}    # Gate VOR Write
  pattern_library.py is_pattern_worthy(...)   # AUFGELOEST batch_C5 (aufrufbare Single-Source)

SCHREIBT (NUR eigener Slot + Libraries via pattern_library.py — INV-PTO-4 Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.materialize:
      created: [{pattern_id, scope, axis, source_signal_ids}]
      updated: [{pattern_id, lifecycle_path: pfad-1|pfad-2, new_status}]
      retired: [{pattern_id, reason}]
      deferred_busy: bool      # true falls Quiescenz=BUSY → kein Write erfolgt
      worthiness_pending: bool # false seit batch_C5 (AK-CTX-WORTHINESS-EXTRACT gebaut; is_pattern_worthy() aufrufbar)
      status: DONE | DEFERRED_BUSY | EMPTY
  {VAULT}/Libraries/{Pattern|Semantic|Domain|Factoring}Library/...   (4 Libraries via _SCOPE_LIB-Routing in pattern_library.py, quiescenz-gated; Domain/Factoring bootstrappen on-demand, AK-7)

  NICHT: andere BERATER_OUTPUTS_PT-Slots, direktes File-Editieren der Libraries (nur via Script-API).

INVARIANTEN:
  INV-MAT-1 (Single-Writer): schreibt NUR BERATER_OUTPUTS_PT.materialize (+ Libraries via Script-API).
  INV-MAT-2 (Quiescenz-Gate, = INV-PTO-2): Gate-Check VOR jedem Write; BUSY ohne Override → DEFERRED_BUSY, kein Write.
  INV-MAT-3 (Einstufig, = INV-PTO-3): add direkt via pattern_library.py — KEIN Kandidat→extract-2-Hop, NIE subprocess _PT_update.md / _pattern_add.md.
  INV-MAT-4 (Counter-Reuse, = INV-PTO-6): Reifung NUR via pattern_library.py lifecycle (pfad-1/pfad-2) — keine Counter-Logik dupliziert.
  INV-MAT-5 (WORTHINESS, AUFGELOEST batch_C5): is_pattern_worthy() ist aufrufbare Single-Source in pattern_library.py (5 Signal-Klassen) — echt aufgerufen, KEIN Fallback-Pass mehr, KEIN Doppel-Impl (Extract-not-reimplement, F1).
  INV-MAT-6 (Graceful): leere classify+forensic → created/updated/retired=[], status=EMPTY.
```

## Aufruf

```
Skill(_PT_berater_materialize, args="{BL_ID} [--dry-run] [--quiescenz-override --target-vault={VAULT}]")
```
Aufgerufen von `_PT_orchestrate` Stage 7 (Worker-Spawn, opus). KEIN direkter User-Aufruf.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID); bl_folder = WORKING_DIR
   # BL-374 AK-3: --target-vault wird vom Orchestrator (G-5) IMMER durchgereicht — deterministischer Vault
   # fuer ALLE Library-Writes. Tier-1-Override fuer pattern_library.resolve_vault_root → hardcoded Fallback nie erreicht.
   VAULT = CLI_PARAM("--target-vault")   # IMMER gesetzt (BL-374 AK-3); Quelle = current_context.py im Orchestrator
   IDEMPOTENZ: IF BERATER_OUTPUTS_PT.materialize.status == DONE: RETURN (Resume-SKIP)

2. classify = .classify; forensic = .forensic.verdicts[]
   IF classify leer AND forensic == []: SCHREIBE materialize={...[], status:EMPTY}; RETURN (INV-MAT-6)

3. QUIESCENZ-GATE (INV-MAT-2 — VOR jedem Write):
   gate = Bash("py {VAULT}/.claude/scripts/manifest_quiescence.py check {BL_ID}" + quiescenz_override_arg)
   IF gate == BUSY AND NOT --quiescenz-override:
     SCHREIBE materialize={deferred_busy: true, status: DEFERRED_BUSY}; RETURN

4. materialisierungs_kandidaten(classify, forensic): pro Achse ein Kandidat, **Achse→scope-Bruecke** (BL-256/257):
     #   classify.semantic      → scope="semantic"  → SemanticLibrary
     #   classify.architectural → scope="arch"      → PatternLibrary
     #   classify.fachlich      → scope="domain"    → DomainLibrary    (BL-256 DOM-Seam)
     #   classify.factoring     → scope="factoring" → FactoringLibrary (BL-257 FAC-Seam)
     #   _SCOPE_LIB in pattern_library.py routet scope→Library; Domain/Factoring bootstrappen on-demand (AK-7).
   FOR cand IN materialisierungs_kandidaten(classify, forensic):
     IF --dry-run: created.append({...}) ohne echten Write; CONTINUE
     IF NOT pattern_library.is_pattern_worthy(cand):   # echte 5-Signal-Heuristik (AUFGELOEST batch_C5, INV-MAT-5)
        log_skip(cand, "not pattern-worthy"); CONTINUE   # worthiness_pending bleibt false
     # EINSTUFIG (INV-MAT-3): add direkt — cand.scope steuert die Ziel-Library (alle 4 via _SCOPE_LIB)
     # BL-374 AK-3: vault_root=VAULT explizit threaden (aus --target-vault) → tier-1-Override, kein Fallback-Guess
     pid = pattern_library.add_arch(scope=cand.scope, vault_root=VAULT, ...)   # KEIN subprocess .md
     created.append({pattern_id: pid, scope: cand.scope, axis: cand.axis, source_signal_ids})

5. FOR v IN forensic:   # Counter-Reifung (INV-MAT-4) — BL-374 AK-3: vault_root=VAULT auch hier threaden
     IF v.lifecycle_hint == "pfad-2-broken":
        pattern_library.lifecycle(v.pattern_id_hint, pfad=2, boundary_note=v.boundary_note, vault_root=VAULT)  # broken++
        updated.append({pattern_id, lifecycle_path: pfad-2, new_status})
     ELSE:  # boundary-only — kein broken++, nur boundary_note ergaenzen
        pattern_library.lifecycle(v.pattern_id_hint, pfad=2, boundary_note=v.boundary_note, broken=false, vault_root=VAULT)

6. Schreibe BERATER_OUTPUTS_PT.materialize = {created, updated, retired, deferred_busy:false, worthiness_pending:false, status: DONE}.
   SendMessage team-lead: "materialize: {created} angelegt / {updated} gereift / {retired} retired (quiescenz=OK, worthiness_pending={worthiness_pending})"
```

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| Quiescenz=BUSY (kein Override) | status=DEFERRED_BUSY, kein Write, Hinweis an Lead (bei Quiescenz erneut --resume) |
| --dry-run | created/updated berechnet, 0 echte Library-Writes (INV-PTO-3 dry verifizierbar) |
| is_pattern_worthy() (batch_C5 gebaut) | echte 5-Signal-Heuristik gatet; nicht-wuerdige Kandidaten geskippt; worthiness_pending=false |
| leere classify+forensic | status=EMPTY |

## Verwandt
- `_PT_berater_classify` (Stage 5) · `_PT_berater_forensic` (Stage 6) — Eingaben ·
  `_PT_berater_report` (Stage 8, konsumiert .materialize) ·
  `pattern_library.py` (add_arch/lifecycle — Reuse-Quelle, P0-fertig 22/22) ·
  `manifest_quiescence.py` (BL-229 AK-E Gate) · `_PT_promoteFromPL` (WORTHINESS-Quelle, batch_C5) ·
  BL-237 EINSTUFIG-Materialisierung (Anschluss 1 / AK-CTX-PTO-7)
