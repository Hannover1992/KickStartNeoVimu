---
name: _roadmap
description: Dispatcher (Macro↔Micro) — /_roadmap {BL} → Within-BL-Kompass (parkingLot, Micro: wo im BL); ohne BL / status / next / set → Backlog-Kompass (backlog, Macro: welches BL naechstes).
type: satellite
version: 2.0.0
created: 2026-06-18
updated: 2026-06-19
op: Roadmap
chain_position: standalone
---

# /_roadmap — Dispatcher (Macro ↔ Micro)

Seit **BL-418** ist der Roadmap-Kompass zweigeteilt — Macro (welches BL) + Micro (wo im BL). `/_roadmap`
routet auf den richtigen, je nach Argument:

| Aufruf | → Command | Ebene |
|---|---|---|
| `/_roadmap {BL}` (BL-ID als Arg) | **`/_roadmap_parkingLot {BL}`** | **Micro** — wo INNERHALB des BL (Pipeline-Stufen · PL-Items granular-K/Stage/depends_on · Sub-Batches autoritativ-od-Projektion · Orchestrator-Kette · K-gewichtetes %) |
| `/_roadmap` · `status` · `next` · `set {epic}` | **`/_roadmap_backlog`** | **Macro** — welches BL als naechstes (Lane/Epic-Reihenfolge, ROADMAP-ORDER-Block) |

## Routing-Regel
```
IF arg matcht ^(BL|DCSRE|DCS)-\d+   → Skill(_roadmap_parkingLot, args={BL})     # Micro
ELSE                                 → Skill(_roadmap_backlog, args={rest})      # Macro (status/next/set)
```

## Warum die Aufspaltung (BL-418)
- **Macro** (`/_roadmap_backlog`, `roadmap_status.py`): wo im BACKLOG — welches BL als naechstes, ueber Lanes/Epics.
- **Micro** (`/_roadmap_parkingLot`, `roadmap_parkinglot.py`): wo im BACKLOG-ITEM — PL-Items + Sub-Batches +
  K-gewichtetes %. Template = DCSRE-1648-Kompass. Vor IDF = **Projektion** (simulierter Orchestrator, laut markiert),
  nach IDF = **autoritativ** (aus Manifest).
- Zusammen = volle Aufloesung: **welches BL × wo im BL**.

## Verwandte
- **`/_roadmap_backlog`** (Macro) · **`/_roadmap_parkingLot`** (Micro) · `/_help` (Pipeline-SOLL) · `/_goal_backlog`.
- BL-418 (die Aufspaltung). INV-ROADMAP-1..4 + INV-ROADMAP-PL-1..3 gelten je im Ziel-Command.
