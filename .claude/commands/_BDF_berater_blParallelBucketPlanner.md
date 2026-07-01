---
type: command
version: 1.0.0
created: '2026-05-19'
bl_ref: BL-176
ak_ref: AK-5
chain_position: phase-2.5d
team_based: true
---

# _BDF_berater_blParallelBucketPlanner — Phase 2.5d: Parallel-Buckets

```yaml
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _BDF_berater_blParallelBucketPlanner                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {vault_root}/Vault/Meta/interest_radius/                          ║
║      bl_dependency_matrix.json  (Output Phase 2.5a)                 ║
║      bl_sequence.json           (Output Phase 2.5c)                 ║
║      bl_cluster_map.json        (Output Phase 2.5b)                 ║
║    {vault_root}/Backlog/BL-*/                                        ║
║      Frontmatter: foundation_bl:, priority:                         ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {vault_root}/Vault/Meta/interest_radius/                          ║
║      bl_parallel_buckets.json   (Bucket-Zuteilung)                  ║
║    {vault_root}/Vault/Meta/interest_radius/                          ║
║      _interest_radius.md        (Mermaid-Graph + ASCII-Tabelle)     ║
║                                                                      ║
║  ACTOR: Berater-Worker (min. sonnet)                                 ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Python-Script

`{repo_root}/.claude/scripts/bl_parallel_buckets.py`

CLI: `py -3 bl_parallel_buckets.py --vault-root=... --sequence-file=... --output-dir=...`

## Invarianten

- **INV-BDF-PARALLEL-1:** Kein BL in Bucket-A darf von einem BL in Bucket-B abhaengen (transitive Closure). Jede Bucket-Zuordnung wird via Independence-Constraint-Check verifiziert.
- **INV-BDF-PARALLEL-2:** BLs mit `foundation_bl: true` im Frontmatter gehen IMMER in bucket-0 (Single-Stream, sequentiell vor allen anderen Buckets).
- **INV-BDF-MIGRATION-COMPAT:** Falls kein `bl_parallel_buckets.json` vorhanden → Phase 2b BATCH_PLANNING faellt auf Legacy-Flat-List-Modus zurueck (kein Breaking Change).

## Pseudocode

```
# Input: Sequence + Matrix + Cluster-Map
sequence = lies_json(sequence_file)
matrix = lies_json(matrix_file)
bl_frontmatter = lies_alle_bl_frontmatter(vault_root)

# Schritt 1: foundation_bl → bucket-0 (INV-BDF-PARALLEL-2)
bucket_0 = [bl for bl in sequence IF bl_frontmatter[bl].get("foundation_bl") == True]
remaining = [bl for bl in sequence IF bl NOT IN bucket_0]

# Schritt 2: Transitive-Closure berechnen
# transitive_closure[bl] = alle BLs die bl (direkt oder indirekt) abhaengen
transitive_closure = compute_transitive_closure(matrix)

# Schritt 3: Bucket-Assignment fuer verbleibende BLs
# Ziel: moeglichst viele unabhaengige BLs in denselben Bucket
buckets = [bucket_0]  # bucket-0 ist reserviert
assigned = set(bucket_0)

for bl in remaining:
  # Finde ersten Bucket in dem bl kein Dep auf bereits zugewiesene BLs hat
  placed = False
  for bucket_idx, bucket in enumerate(buckets):
    IF is_independent_of_all(bl, bucket, transitive_closure):
      bucket.append(bl)
      placed = True
      BREAK
  IF NOT placed:
    # Neuen Bucket eroeffnen
    buckets.append([bl])
  assigned.add(bl)

# Schritt 4: Independence-Constraint-Check (INV-BDF-PARALLEL-1)
for bucket_a in buckets:
  for bucket_b in buckets:
    IF bucket_a == bucket_b: CONTINUE
    for bl_a in bucket_a:
      for bl_b in bucket_b:
        IF bl_a IN transitive_closure[bl_b]:  # bl_b haengt von bl_a ab (oder umgekehrt)
          IF bucket_a_idx > bucket_b_idx:
            HARD-STOP: "INV-BDF-PARALLEL-1 verletzt: {bl_a} in bucket-{bucket_a_idx} wird von {bl_b} in bucket-{bucket_b_idx} benoetigt"

# Schritt 5: JSON Output
schreibe_json(output_dir + "/bl_parallel_buckets.json", {
  "generated_at": now(),
  "bucket_count": len(buckets),
  "buckets": {
    f"bucket-{i}": {"bls": bucket, "parallel": i > 0}
    for i, bucket in enumerate(buckets)
  }
})

# Schritt 6: Mermaid-Visualisierung (BL-176 AK-8, PL-176-024)
# Delegiert an bdf_bl_visualize.py (oder inline)
mermaid_output = generate_mermaid(buckets, matrix)
ascii_table = generate_ascii_table(buckets, bl_frontmatter)
schreibe_md(output_dir + "/_interest_radius.md", mermaid_output + "\n\n" + ascii_table)
Logge: "INTEREST_RADIUS: _interest_radius.md generiert (Mermaid + ASCII)"
```

## Output-Format (`bl_parallel_buckets.json`)

```json
{
  "generated_at": "2026-05-19T...",
  "bucket_count": 3,
  "buckets": {
    "bucket-0": {"bls": ["BL-159", "BL-165"], "parallel": false},
    "bucket-1": {"bls": ["BL-176", "BL-178"], "parallel": true},
    "bucket-2": {"bls": ["BL-177"], "parallel": true}
  }
}
```

## Konsumenten

- `_BDF_orchestrate.md` Phase 2b BATCH_PLANNING liest `bl_parallel_buckets.json` statt flacher unified-Liste
- `bdf_bl_visualize.py` (Sub-Batch 6) konsumiert `_interest_radius.md` fuer erweiterte Ausgaben

## Aufgerufen von

`_BDF_orchestrate.md` Phase 2.5 INTEREST_RADIUS (Step 4/4, letzter Schritt)

## Naechste Phase

`_BDF_orchestrate.md` Phase 2b BATCH_PLANNING konsumiert sequence + parallel_buckets
