---
type: command
version: 1.0.0
created: '2026-05-19'
bl_ref: BL-176
ak_ref: AK-6
chain_position: phase-2.5a
team_based: true
---

# _BDF_berater_blDependencyAnalyzer — Phase 2.5a: Frontmatter-Reader + LLM-Dep-Inferenz

```yaml
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _BDF_berater_blDependencyAnalyzer                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {vault_root}/Backlog/BL-*/                                        ║
║      Frontmatter: dependencies:, status:, priority:, tags:           ║
║    {vault_root}/Vault/Meta/_factory_manifest.md                      ║
║      → BACKLOG_STATE (aktuelle offene BL-Liste)                      ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {vault_root}/Vault/Meta/interest_radius/                          ║
║      bl_dependency_matrix.json  (2D Adjacency-Matrix)               ║
║    {vault_root}/Vault/Meta/_factory_manifest.md                      ║
║      → BACKLOG_STATE.interest_radius_snapshot.matrix_file           ║
║                                                                      ║
║  ACTOR: Berater-Worker (min. sonnet)                                 ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Python-Script

`{repo_root}/.claude/scripts/bdf_bl_dependency_analyzer.py`

CLI: `py -3 bdf_bl_dependency_analyzer.py --vault-root=... --output-dir=...`

## Invarianten

- **INV-BDF-DEP-1:** Zyklen in der Dependency-Matrix sind ein Hard-Stop (keine zirkulaere Abhaengigkeit erlaubt). Bei Zyklus: Logge alle beteiligten BL-IDs + ABBRUCH mit Fehlermeldung.
- **INV-BDF-DEP-2:** BLs mit status IN {DONE, ARCHIVED, FREEZE, DEFER} werden aus der Matrix GEFILTERT (kein Eintrag als Knoten).
- **INV-BDF-DEP-3:** BLs ohne `dependencies:`-Feld werden als isolierte Graph-Knoten behandelt (leere Adjazenzliste, kein Crash). (BL-176 AK-1 PL-176-002)
- **INV-BDF-MATRIX-FRESHNESS:** Matrix wird bei jedem BDF-Lauf neu generiert — kein Cache ohne Timestamp-Check.

## Pseudocode

```
# Input: alle BL-Ordner im Backlog-Verzeichnis
bl_list = lies_alle_bl_frontmatter(vault_root + "/Backlog/")
active_bls = filter(bl_list, status NOT IN {DONE, ARCHIVED, FREEZE, DEFER})

# 2D Adjacency-Matrix aufbauen
matrix = {}
for bl in active_bls:
  deps = bl.frontmatter.get("dependencies", [])
  # Nur aktive Deps behalten (INV-BDF-DEP-2)
  active_deps = [d for d in deps if get_bl_status(d) NOT IN {DONE, ARCHIVED, FREEZE, DEFER}]
  matrix[bl.id] = active_deps

# Zyklus-Pruefung (INV-BDF-DEP-1)
cycle = detect_cycle(matrix)  # DFS-basiert
IF cycle:
  Logge: "HARD-STOP: Zyklus in BL-Dependency-Matrix: {cycle}"
  ABBRUCH

# LLM-Inferenz: implizite Abhaengigkeiten aus Titel + Beschreibung
# (Nur wenn explizite deps fehlen und BL-Titel aehnliche Keywords hat)
for bl in active_bls:
  IF len(matrix[bl.id]) == 0:
    inferred = llm_infer_deps(bl.title, bl.description, active_bls)
    matrix[bl.id].extend(inferred)  # mit inference_confidence-Flag markiert

# Output schreiben
schreibe_json(output_dir + "/bl_dependency_matrix.json", {
  "generated_at": now(),
  "bl_count": len(active_bls),
  "matrix": matrix
})
```

## Output-Format (`bl_dependency_matrix.json`)

```json
{
  "generated_at": "2026-05-19T...",
  "bl_count": 12,
  "matrix": {
    "BL-176": ["BL-159", "BL-165"],
    "BL-177": ["BL-176"],
    "BL-178": []
  }
}
```

## Aufgerufen von

`_BDF_orchestrate.md` Phase 2.5 INTEREST_RADIUS (Step 1/4)

## Naechste Phase

`_BDF_berater_blClustering` (Step 2/4) konsumiert `bl_dependency_matrix.json`
