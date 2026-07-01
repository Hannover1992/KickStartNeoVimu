---
feature: BL-113
component: C5
version: 1.0
created: 2026-04-17
updated: 2026-04-17
---

# Hash-Scope-Zuordnung (Sanduhr-Prinzip)

## Ueberblick

Die Hash-Hierarchie besteht aus 3 Ebenen: Target (L1), Feature (L2), Worktree (L3).
Jede Ebene erhaelt einen zusaetzlichen SHA256[:4]-Hash, sodass L1=1 Hash, L2=2 Hashes, L3=3 Hashes.
Zweck: Multi-Tenancy — mehrere parallele Worktrees und Features unter demselben Target ohne Kollisionen.
Separator zwischen Hash-Bloecken: `_` (ADR-G). Trenner zwischen Dateiname und Hash-Block: `$`.
Algorithmus: SHA256 der jeweiligen Scope-ID, gekuerzt auf 4 Hex-Zeichen (lowercase).

## Sanduhr-Split (13 Datei-Typen)

| Datei-Typ | Scope | Ebene | Hash-Tiefe |
|-----------|-------|-------|------------|
| _backlog_index | Target | L1 | 1 Hash |
| _protokoll_index | Target | L1 | 1 Hash |
| _model_index | Target | L1 | 1 Hash |
| BL-* (Backlog-Item) | Feature | L2 | 2 Hashes |
| {NAME}_Model.md | Feature | L2 | 2 Hashes |
| {NAME}_Spec.md | Feature | L2 | 2 Hashes |
| {NAME}-GAP.md | Feature | L2 | 2 Hashes |
| {NAME}-HANDOFF.md | Feature | L2 | 2 Hashes |
| {NAME}_findings_crumbs.md | Feature | L2 | 2 Hashes |
| _manifest | Worktree | L3 | 3 Hashes |
| _manifest_protokoll | Worktree | L3 (ADR-I) | 3 Hashes |
| _session_params | Worktree | L3 | 3 Hashes |
| _guard_log | Worktree | L3 | 3 Hashes |

## Hash-Algorithmus

Algorithmus: SHA256 der Scope-ID (target_id, feature_id, worktree_id), jeweils gekuerzt auf 4 Hex-Zeichen (lowercase).
Separator zwischen Hash-Segmenten: `_` (ADR-G, verhindert Verwechslung mit Dateiname-Teilen).
Trenner zwischen Dateiname und Hash-Block: `$` (eindeutiges Trennzeichen).
Suffix: immer `.md`.

## Beispiele

- _backlog_index (L1): `_backlog_index$aa0b.md`
- BL-113a Model (L2): `BL-113a_Model$aa0b_858a.md`
- _manifest (L3): `_manifest$aa0b_858a_aa40.md`

## Maschinen-lesbarer Block (AK-8a)

```yaml
hash_scope:
  target_level:
    - _backlog_index
    - _protokoll_index
    - _model_index
  feature_level:
    - BL-*
    - "*_Model.md"
    - "*_Spec.md"
    - "*-GAP.md"
    - "*-HANDOFF.md"
    - "*_findings_crumbs.md"
  worktree_level:
    - _manifest
    - _manifest_protokoll  # ADR-I: auf L2 statt L3 reduziert in v1.1 moeglich
    - _session_params
    - _guard_log
  algorithm: "sha256[:4]"
  separator_hashes: "_"
  separator_name_hash: "$"
  suffix: ".md"
```
