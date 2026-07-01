---
type: command
version: 1.0.0
created: '2026-05-19'
bl_ref: BL-176
ak_ref: AK-4
chain_position: phase-2.5c
team_based: true
---

# _BDF_berater_blSequencePlanner — Phase 2.5c: Topologische Sequence

```yaml
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _BDF_berater_blSequencePlanner                             ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {vault_root}/Vault/Meta/interest_radius/                          ║
║      bl_dependency_matrix.json  (Output Phase 2.5a)                 ║
║      bl_cluster_map.json        (Output Phase 2.5b)                 ║
║    {vault_root}/Backlog/BL-*/                                        ║
║      Frontmatter: priority:, manual_sequence_override:              ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {vault_root}/Vault/Meta/interest_radius/                          ║
║      bl_sequence.json           (Topologische Reihenfolge)          ║
║                                                                      ║
║  ACTOR: Berater-Worker (min. sonnet)                                 ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Python-Script

`{repo_root}/.claude/scripts/bdf_bl_sequence_planner.py`

CLI: `py -3 bdf_bl_sequence_planner.py --vault-root=... --matrix-file=... --output-dir=...`

## Invarianten

- **INV-BDF-DEP-1:** Zyklen → Hard-Stop (von Phase 2.5a bereits gefangen, aber Sequence prueft nochmals).
- **User-Override:** `manual_sequence_override: <N>` in BL-Frontmatter verschiebt BL auf Position N — NUR wenn dadurch kein Zyklus entsteht. Sonst Override ignoriert + Warning geloggt.

## Pseudocode (Kahn's Algorithm + Priority-Tiebreak)

```
# Input: Dependency-Matrix
matrix = lies_json(matrix_file)
bl_frontmatter = lies_alle_bl_frontmatter(vault_root)

# Kahn's Algorithmus (BFS-basiert)
in_degree = {bl: 0 for bl in matrix.bls}
for bl, deps in matrix.items():
  for dep in deps:
    in_degree[bl] += 1

# Priority-Queue: KRITISCH(4) > HOCH(3) > MITTEL(2) > NIEDRIG(1)
PRIORITY_MAP = {"KRITISCH": 4, "HOCH": 3, "MITTEL": 2, "NIEDRIG": 1, "NONE": 0}
queue = PriorityQueue()
for bl in matrix.bls:
  IF in_degree[bl] == 0:
    prio = PRIORITY_MAP.get(bl_frontmatter[bl].priority, 0)
    queue.push((prio, bl))  # Max-Heap: hoehere Prio zuerst

sequence = []
WHILE NOT queue.empty():
  prio, bl = queue.pop()
  sequence.append(bl)
  for dependent in matrix.get_dependents(bl):  # alle BLs die von bl abhaengen
    in_degree[dependent] -= 1
    IF in_degree[dependent] == 0:
      dep_prio = PRIORITY_MAP.get(bl_frontmatter[dependent].priority, 0)
      queue.push((dep_prio, dependent))

# Zyklus-Check (nicht alle Knoten besucht = Zyklus)
IF len(sequence) != len(matrix.bls):
  HARD-STOP: "Zyklus in Dependency-Matrix — Kahn konnte nicht alle BLs einordnen"

# User-Override anwenden (BL-176 AK-7, INV: Cycle-Check aktiv)
for bl in bl_frontmatter:
  override_pos = bl_frontmatter[bl].get("manual_sequence_override")
  IF override_pos AND bl IN sequence:
    current_pos = sequence.index(bl)
    # Pruefe: verschiebt Override keine Dep-Verletzung (kein BL vor seinen Deps)
    IF is_valid_override(bl, override_pos, sequence, matrix):
      sequence.move(bl, override_pos)
    ELSE:
      Logge: "WARNING: manual_sequence_override fuer {bl} verletzt Dep-Constraint — ignoriert"

# Output schreiben
schreibe_json(output_dir + "/bl_sequence.json", {
  "generated_at": now(),
  "sequence": sequence,
  "overrides_applied": [bl for bl with valid manual_sequence_override]
})
```

## Output-Format (`bl_sequence.json`)

```json
{
  "generated_at": "2026-05-19T...",
  "sequence": ["BL-159", "BL-165", "BL-176", "BL-177"],
  "overrides_applied": []
}
```

## Aufgerufen von

`_BDF_orchestrate.md` Phase 2.5 INTEREST_RADIUS (Step 3/4)

## Naechste Phase

`_BDF_berater_blParallelBucketPlanner` (Step 4/4) konsumiert Sequence + Matrix
