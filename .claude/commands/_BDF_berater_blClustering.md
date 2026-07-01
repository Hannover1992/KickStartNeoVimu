---
type: command
version: 1.0.0
created: '2026-05-19'
bl_ref: BL-176
ak_ref: AK-3
chain_position: phase-2.5b
team_based: true
---

# _BDF_berater_blClustering — Phase 2.5b: Kohaesions-Clustering

```yaml
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _BDF_berater_blClustering                                  ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {vault_root}/Vault/Meta/interest_radius/                          ║
║      bl_dependency_matrix.json  (Output Phase 2.5a)                 ║
║    {vault_root}/Backlog/BL-*/                                        ║
║      Frontmatter: tags:, type:, builds_on:                          ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {vault_root}/Vault/Meta/interest_radius/                          ║
║      bl_cluster_map.json        (Cluster-Zuordnung)                 ║
║                                                                      ║
║  ACTOR: Berater-Worker (min. sonnet)                                 ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Python-Script

`{repo_root}/.claude/scripts/bdf_bl_clustering.py`

CLI: `py -3 bdf_bl_clustering.py --vault-root=... --matrix-file=... --output-dir=...`

## Pseudocode

```
# Input: Dependency-Matrix + BL-Frontmatter
matrix = lies_json(input_dir + "/bl_dependency_matrix.json")
bl_frontmatter = lies_alle_bl_frontmatter(vault_root + "/Backlog/")

# Clustering nach 3 Signalen:
# Signal 1: tags.topic/* — gleiche Topic-Tags
# Signal 2: type/ — gleiche BL-Typen (feature, fix, arch, doc...)
# Signal 3: builds_on-Ketten aus Dependency-Matrix

cluster_map = {}
for bl in matrix.bls:
  clusters = []

  # Topic-Tag-Cluster
  topic_tags = [t for t in bl.tags if t.startswith("topic/")]
  for tag in topic_tags:
    cluster_id = "topic:" + tag
    clusters.append(cluster_id)

  # Type-Cluster
  IF bl.type:
    clusters.append("type:" + bl.type)

  # Dependency-Chain-Cluster (transitive builds_on)
  root = find_dependency_root(bl.id, matrix)
  IF root != bl.id:
    clusters.append("chain:" + root)

  cluster_map[bl.id] = clusters  # Overlap erlaubt (BL kann in mehreren Clustern)

# Output schreiben
schreibe_json(output_dir + "/bl_cluster_map.json", {
  "generated_at": now(),
  "cluster_map": cluster_map,
  "clusters": invert_map(cluster_map)  # Cluster-ID → [BL-IDs]
})
```

## Output-Format (`bl_cluster_map.json`)

```json
{
  "generated_at": "2026-05-19T...",
  "cluster_map": {
    "BL-176": ["topic/bdf", "type:arch", "chain:BL-159"],
    "BL-177": ["topic/bdf", "type:feature"]
  },
  "clusters": {
    "topic/bdf": ["BL-176", "BL-177"],
    "type:arch": ["BL-176"]
  }
}
```

## Aufgerufen von

`_BDF_orchestrate.md` Phase 2.5 INTEREST_RADIUS (Step 2/4)

## Naechste Phase

`_BDF_berater_blSequencePlanner` (Step 3/4) konsumiert Matrix + Cluster-Map
