# /_truth_migration_capstone — Capstone Migrations-Orchestrator (Thin-Invoker, BL-483)

```yaml
status: active
version: 1.0.0
created: 2026-06-25
op: TruthMigrationCapstone
phase: Meta
type: orchestration
chain_position: capstone
feature_anchor: BL-483
model_tier: sonnet
related:
  - truth_gate_check
  - truth_pilot_cutover
  - keyword_edge_writer
  - truth_edge_backref
  - wikilink_materializer
  - build_retrieval_index
  - view_projector
  - bl484_post_gate
  - _W_atom_migration_orchestrator
```

---

## Zweck

Dieser Befehl ist ein **Thin-Invoker** (INV-CAPSTONE-1): er ruft
`py -3 .claude/scripts/truth_migration_capstone.py` auf und delegiert
**alle** Stage-Logik an den Python-Treiber. Keine Pseudocode-Reimplementierung
der Stage-Schritte inline — das waere INV-CAPSTONE-1-Verletzung.

**Doktrin:** `--dry-run` ist Default (INV-CAPSTONE-3). `--write` erfordert
`--force-go` oder interaktives "GO" vom User.

---

## VERTRAG

```
LIEST:
  {vault}/**/_truth*.md            (Truth-Atome, via Tools)
  {vault}/**/*.md                   (View-Dateien fuer Stage 7)
  .claude/models/*.md               (Repo-Meta-Models)

SCHREIBT (--write, nach Gate-Gruenlicht):
  Stage 1: {vault}/Backlog/**/2_Model/truths/{id}.md  (truth_pilot_cutover)
  Stage 2: {vault}/**/_truth*.md frontmatter edges[]  (keyword_edge_writer)
  Stage 4: {vault}/**/_truth*.md frontmatter referenced_by[] (truth_edge_backref)
  Stage 5: {vault}/**/*.md wikilink-Sektionen         (wikilink_materializer)
  Stage 6: {vault}/.claude/output/retrieval_index/    (build_retrieval_index)
  Stage 7: {vault}/**/View*.md                        (view_projector)

RUFT (Python, deterministisch):
  Stage 0: py -3 .claude/scripts/truth_gate_check.py      [GATE]
  Stage 1: py -3 .claude/scripts/truth_pilot_cutover.py   [GATE]
  Stage 2: py -3 .claude/scripts/keyword_edge_writer.py
  Stage 3: py -3 .claude/scripts/keyword_edge_writer.py --dry-run  [GATE]
  Stage 4: py -3 .claude/scripts/truth_edge_backref.py    [GATE]
  Stage 5: py -3 .claude/scripts/wikilink_materializer.py [GATE]
  Stage 6: py -3 .claude/scripts/build_retrieval_index.py [GATE]
  Stage 7: py -3 .claude/scripts/view_projector.py        [GATE]
  Stage 8: py -3 .claude/scripts/bl484_post_gate.py       (BL-484, INV-CAPSTONE-4)
```

---

## STATE-MACHINE

| Stage | Name               | Treiber-Tool                    | [GATE] | Rollback bei Fail |
|-------|--------------------|---------------------------------|--------|-------------------|
| Stage 0 | preflight_and_backup | truth_gate_check.py + git tag | [GATE] | aborted_at=PREFLIGHT_CHECK |
| Stage 1 | atomize              | truth_pilot_cutover.py        | [GATE] | content_loss==0 + quarantine_refused==quarantine_count |
| Stage 2 | edges                | keyword_edge_writer.py        | [GATE] | gate_ok check |
| Stage 3 | edge_quality_gate    | keyword_edge_writer.py --dry-run | [GATE] | dangling==0 + max_edges<=15 (BL-455) |
| Stage 4 | backref_inversion    | truth_edge_backref.py         | [GATE] | updated >= 0 |
| Stage 5 | wikilinks            | wikilink_materializer.py      | [GATE] | gate_ok check |
| Stage 6 | edge_index           | build_retrieval_index.py      | [GATE] | gate_ok check |
| Stage 7 | views                | view_projector.py             | [GATE] | gate_ok check |
| Stage 8 | post_gate_bl484      | bl484_post_gate.py (BL-484)   | Optional | WARNING + no-op wenn fehlt (INV-CAPSTONE-4) |

**Zustaende:** INIT → (Stage-Loop) → DONE (alle Gates gruen) ODER ROLLBACK (Gate-Fail).

---

## Aufruf

```bash
# Dry-Run (DEFAULT — kein Vault-Write)
py -3 .claude/scripts/truth_migration_capstone.py run \
  --vault {VAULT} \
  --repo-models .claude/models \
  --force-go \
  --out capstone_report.json

# Write-Modus (gefenced — interaktives GO oder --force-go)
py -3 .claude/scripts/truth_migration_capstone.py run \
  --vault {VAULT} \
  --repo-models .claude/models \
  --write \
  --force-go \
  --out capstone_report.json

# Resume ab Stage 4 (nach bekannt-gutem 0-3)
py -3 .claude/scripts/truth_migration_capstone.py run \
  --vault {VAULT} \
  --repo-models .claude/models \
  --write \
  --force-go \
  --stage-from 4 \
  --out capstone_report_resume.json
```

---

## INVARIANTEN

```
INV-CAPSTONE-1 (Thin-Invoker): Dieses Kommando ruft py -3 .../truth_migration_capstone.py
  auf. Kein Pseudocode, der Stage-Logik inline reimplementiert (kein run_stage/subprocess.run
  Pseudocode-Block). Verletzung = Drift vom VDD-Vertrag (analog INV-MIG-THIN).

INV-CAPSTONE-2 (Drain-Before-Next): Jedes Stage-Gate muss vollstaendig ausgewertet
  (exit code + gate_fn) sein, bevor der naechste Stage-Subprocess gespawnt wird.
  Kein Fire-and-Forget.

INV-CAPSTONE-3 (Write-Fence): --dry-run ist DEFAULT. --write erfordert:
  (a) --force-go ODER (b) interaktives "GO" vom User. --write ohne Bestaetigung
  bricht mit exit 3 ab.

INV-CAPSTONE-4 (Stage-8 Interface Only): Der Capstone RUFT den BL-484-Gate auf.
  Er implementiert die Post-Flight-Logik NICHT selbst. Wenn BL-484 fehlt (FileNotFoundError):
  WARNING + No-Op, KEIN Rollback, KEIN exit 2. overall_ok reflektiert nur Stages 0-7.

INV-CAPSTONE-5 (No Atom-Writer Modification): Der Treiber modifiziert KEINE
  Atom-Writer-Tools (truth_atomizer, truth_normalize, truth_atomize_batch,
  keyword_edge_writer, wikilink_materializer, view_projector, truth_backref_*).
  Lane C besitzt diese Tools. Der Capstone ist reiner Orchestrator.
```

---

## Bericht-Format (JSON)

```json
{
  "vault": "/pfad/zum/vault",
  "run_ts": "2026-06-25T10:00:00+00:00",
  "stages": [
    {"stage_id": 0, "name": "preflight_and_backup", "status": "ok", "gate_ok": true},
    {"stage_id": 1, "name": "atomize", "status": "ok", "gate_ok": true,
     "content_loss": 0, "quarantine_refused": 3, "quarantine_count": 3},
    {"stage_id": 3, "name": "edge_quality_gate", "status": "ok", "gate_ok": true,
     "dangling_count": 0, "max_edges_per_atom": 12},
    "..."
  ],
  "overall_ok": true
}
```

Rollback-Bericht enthaelt zusaetzlich `"aborted_at"` (z.B. `"PREFLIGHT_CHECK"`).
