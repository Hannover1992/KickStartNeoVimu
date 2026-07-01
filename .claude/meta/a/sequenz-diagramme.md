# Sequenz-Diagramme (A-Pipeline)

Referenz fuer `/_A_orchestrate` — FRESH und RESYNC Modus.

## FRESH-Modus (voller 10-Schritt-Prozess)

```
Team Lead                    Agents                          User
    │                              │                          │
    ├─ TeamCreate ─────────────►   │                          │
    ├─ Modus: FRESH ──────────►    │                          │
    │                              │                          │
    │  ═══ EXTRAKTION (iterativ, max 7 Runden) ═══
    ├─ Findings extrahieren ──►    │                          │
    │  (Runden bis Plateau)        │                          │
    │                              │                          │
    │  ═══ HiL FINDINGS REVIEW ═══                           │
    ├─ AskUserQuestion (4er-Batches) ──────────────────────► │
    │  ◄── korrekt/dismiss/kommentar ───────────────────────┤
    ├─ Findings → Crumbs schreiben │                          │
    │                              │                          │
    │  ═══ W_FETCH (Wellen bei normal/hard) ═══
    ├─ Spawn N Explorer ──────────► │  (PARALLEL)
    │  ◄── "Explorer fertig" ─────┤
    ├─ Spawn M Drafter ───────────► │  (PARALLEL)
    │  ◄── "Drafter fertig" ──────┤
    ├─ Spawn 1 Synthese ──────────► │
    │  ◄── "Wissen geholt" ──────┤
    │                              │
    │  ═══ TASKDEF (Wellen bei normal/hard) ═══
    ├─ Spawn N Explorer ──────────► │  (PARALLEL)
    │  ◄── "Explorer fertig" ─────┤
    ├─ Spawn M Drafter ───────────► │  (PARALLEL)
    │  ◄── "Drafter fertig" ──────┤
    ├─ Spawn 1 Synthese ──────────► │
    │  ◄── "Task definiert" ──────┤
    │                              │
    │  ═══ MODEL (Wellen bei normal/hard) ═══
    ├─ Spawn N Explorer ──────────► │  (PARALLEL)
    │  ◄── "Explorer fertig" ─────┤
    ├─ Spawn M Drafter ───────────► │  (PARALLEL)
    │  ◄── "Drafter fertig" ──────┤
    ├─ Spawn 1 Synthese ──────────► │
    │  ◄── "Model v1.0" ──────────┤
    │                              │
    │  ═══ SPEC (Wellen bei normal/hard, KEIN Explorer — w1:null) ═══
    ├─ Spawn M Drafter ───────────► │  (PARALLEL, kein Explorer)
    │  ◄── "Drafter fertig" ──────┤
    ├─ Spawn 1 Synthese ──────────► │
    │  ◄── "Spec geschrieben" ────┤
    │                              │                          │
    │  ═══ HiL AK REVIEW (Loop bis 0 Korrekturen) ═══       │
    ├─ AskUserQuestion (4er-Batches) ──────────────────────► │
    │  ◄── korrekt/dismiss/kommentar ───────────────────────┤
    │  [Falls Korrekturen: /_spec erneut → AK Review Loop]   │
    │                              │                          │
    │  ═══ GAP (Wellen bei normal/hard) ═══
    ├─ Spawn N Explorer ──────────► │  (PARALLEL)
    │  ◄── "Explorer fertig" ─────┤
    ├─ Spawn M Drafter ───────────► │  (PARALLEL)
    │  ◄── "Drafter fertig" ──────┤
    ├─ Spawn 1 Synthese ──────────► │
    │  ◄── "Gap: X%" ────────────┤
    │                              │                          │
    ├─ AskUserQuestion ──────────────────────────────────►   │
    │  ◄── ACCEPT/REFINE/SC/I ───────────────────────────────┤
    │                              │                          │
    ├─ TeamDelete                  │                          │
    ├─ "Artefakte bereit" ────────────────────────────────►  │
```

## RESYNC-Modus

```
Team Lead                    Agents                          User
    │                              │                          │
    ├─ TeamCreate ─────────────►   │                          │
    ├─ Modus: RESYNC ──────────►   │                          │
    ├─ git diff {sync}..HEAD ──►   │                          │
    │                              │                          │
    ├─ Spawn a-{n}-maintain ─────► │                          │
    │  ◄── "Model v{N+1}" ───────┤                          │
    │                              │                          │
    ├─ [Spawn a-{n}-spec] ────────► │  (falls Drift gross)   │
    │  ◄── "Spec updated" ───────┤                          │
    │                              │                          │
    ├─ Spawn a-{n}-gap ──────────► │                          │
    │  ◄── "Gap: X%" ────────────┤                          │
    │                              │                          │
    ├─ AskUserQuestion ──────────────────────────────────►   │
    │  ◄── ACCEPT/REFINE/SC/I ───────────────────────────────┤
    │                              │                          │
    ├─ TeamDelete                  │                          │
    ├─ "Resync fertig" ──────────────────────────────────►   │
```
