---
name: _roadmap_backlog
description: Backlog-Roadmap-Kompass (Macro) — welches BL als naechstes; Roadmap aufstellen/festhalten + orientieren (wo stehen wir, wohin, welcher Befehl als naechster laut Prozess). Micro-Bruder = /_roadmap_parkingLot.
type: satellite
version: 1.1.0
created: 2026-06-18
updated: 2026-06-19
op: Roadmap
chain_position: standalone
---

# /_roadmap_backlog — der Backlog-Roadmap-Kompass (Macro)

> **BL-418-Aufspaltung:** dies ist die **Macro-Ebene** (welches BL als naechstes ueber den ganzen Backlog).
> Die **Micro-Ebene** (wo INNERHALB eines BL — PL-Items/Sub-Batches/%) ist **`/_roadmap_parkingLot {BL}`**.
> `/_roadmap` ist der duenne Dispatcher (BL-Arg → parkingLot, sonst → backlog). Frueher hiess dieser Command `/_roadmap`.

**Zweck:** ein Satelliten-Command der zweierlei kann —
1. **aufstellen/festhalten** (`set`): eine geordnete Roadmap zu einem Epic erstellen/aktualisieren,
2. **orientieren** (`status`, Default): erinnern **wo wir stehen, wohin wir gehen, und welcher Befehl als
   NAECHSTER laut unserem Prozess ausgefuehrt werden muss**.

Der Command erfindet kein Routing — er spiegelt die `/_help`-Pipeline-Reihenfolge (A → IDF → SDF → SC/I)
auf den Reifegrad des Ziel-BLs. Read-only (status/next); `set` schreibt nur die Roadmap-Doku, keinen Code.

## Aufruf
```
/_roadmap_backlog [status]          # Default: Kompass — WO / WOHIN / NAECHSTER BEFEHL
/_roadmap_backlog next              # nur der naechste prozess-korrekte Befehl (terse)
/_roadmap_backlog set {epic}        # Roadmap aufstellen/aktualisieren (Epic-BLs → geordnete Build-Lane)
```

## Quelle der Wahrheit
- **Build-Reihenfolge:** der `<!-- ROADMAP-ORDER:START..END -->`-Block in `.claude/ROADMAP.md` (kuratierte,
  geordnete BL-Liste — robust gegen BL-Erwaehnungen in der Prosa). Voll-Roadmap = der Block + die Phasen-Prosa.
- **Reifegrad/Status pro BL:** `{vault}/_backlog_index.md` (aktiv) + `_backlog_index_done.md` (archiviert).
- **In-Flight-State (optional):** per-BL `_manifest.md` (A_PIPELINE_STATE / DF_BATCH_STATE) fuer resume-Erkennung.
- **Regent/Termination:** `.claude/GOAL.md` · **Epic-Detail:** `{vault}/Konzepte/Epic-Wahrheiten-Roadmap_*.md`.

## Modus `status` / `next` (der Kompass)
```
1. Vault aufloesen:  py -3 .claude/scripts/current_context.py --format=json  → vault_root
2. Kompass-Kern:
   py -3 .claude/scripts/roadmap_status.py \
        --roadmap .claude/ROADMAP.md \
        --index   {vault_root}/_backlog_index.md \
        --done-index {vault_root}/_backlog_index_done.md \
        --epic    "{Epic-Name}" \
        --lane {A|B|C} --lane-plan {vault_root}/_lane_plan.md   # BL-442 AK-2 (GAP-2): lane-aware
   # BL-442 AK-2 (GAP-2): mit --lane + --lane-plan ueberspringt der Kompass BLs, die eine ANDERE Lane
   # haelt (lane_plan.is_collision) -> blocked_other_lane[]. So schlaegt /_roadmap_backlog NIE ein von
   # einer Schwester-Lane gefahrenes BL vor (Multi-Lane kollisionssicher). Ohne --lane: bisheriges Verhalten
   # (single-lane, backward-compat). Lane-ID = die eigene Worktree-Lane aus _worktree_registry.md.
3. Ausgabe spiegeln (WO / ZIEL / NAECHSTER BEFEHL / BAU-KETTE / WOHIN). Bei `next`: nur BEFEHL + KETTE.
4. Lead-Hinweis IMMER mitgeben (steht im Tool-Output):
   - Lead fuehrt den genannten /_X_orchestrate SELBST aus (INV-AO-CALLER) — NIE via Agent('orchestrate ..') = Mega-Worker.
   - Schwere Pipeline (A/IDF/SDF) → FRISCHE Session. Motor gated-off → altmodisch benanntes Team.
   - enforceProcess=hard empfohlen (Geister blocken Drift + Mega-Worker strukturell).
```
Das Routing (roadmap_status.next_command_for_bl): UNREIF/needs_a_pipeline → `/_A_orchestrate {BL}` ·
reif (READY/SC-REIF) → `/_IDF_orchestrate {BL}` · mid-flight → `/_SDF_orchestrate {BL} --resume` · DONE → naechste BL.

**BAU-KETTE** — direkt nach NAECHSTER BEFEHL zeigt `render_build_chain` die volle Orchestrator-Kette, damit klar
ist welche Orchestratoren in welcher Reihenfolge feuern. Der Start-Punkt ist reifegrad-bewusst:
```
BAU-KETTE (auto-chain ab dem Start-Orchestrator):
  A (/_A_orchestrate {BL})         → Wissensbasis: Model·Spec·K-Score·Gap·PL        [UNREIF]
   ↓ IDF (/_IDF_orchestrate {BL})  → PL-Items → Batches
   ↓ SDF (/_SDF_orchestrate {BL})  → pro Batch: C3-modusEntscheidung(M{N}) → /_I_orchestrate
                                      (bzw. /_SC_orchestrate M4–M7) … ALLE Batches
   ↓ Post (/_SDF_orchestrate_post) → recalibrate·statusTransition·modelSync·loopDecision
  → dann das naechste BL bei A
```
- UNREIF → ab **A** (vollstaendige Kette wie oben).
- READY/SC-REIF → ab **IDF** (A-Zeile entfaellt; A bereits gelaufen).
- mid-flight → ab **SDF {BL} --resume** (Checkpoint-Fortsetzung + Post).
- DONE → kein Block (naechste BL nehmen).

**Tiefer rein (Micro):** fuer die Within-BL-Sicht eines konkreten BL → `/_roadmap_parkingLot {BL}`
(PL-Items + granular-K + Sub-Batches autoritativ-od-Projektion + K-gewichtetes %).

## Modus `set {epic}` (Roadmap aufstellen/festhalten)
Lead-gefuehrt (das, was am 2026-06-18 fuer das Epic Wahrheiten manuell gemacht wurde — jetzt wiederholbar):
```
1. Backlog-Index lesen → alle BLs des Epics (parent_epic == {epic}) + verwandte sammeln.
2. In geordnete Phasen clustern (Substrat → Build → System-Adaptation → Mechanismen → Suche → Goal-Gate),
   Abhaengigkeiten beachten (dependencies/related). Separate Straenge (Repo-Meta/Hygiene/arc42) ausweisen.
3. Schreiben:
   a) `.claude/ROADMAP.md` — den `ROADMAP-ORDER:START..END`-Block mit der geordneten BL-Liste (aktualisieren).
   b) `{vault}/Konzepte/Epic-{Name}-Roadmap_{DATE}.md` — die volle Phasen-Roadmap + Where-we-stand + Fences.
   c) optional `.claude/GOAL.md` — Regent/Termination, wenn dieses Epic der aktive Front ist.
4. Fehlende BLs (vom User-Voice-Dump impliziert, noch nicht gefiled) via /_backlog anlegen (ARCHITEKT-1/2).
```

## Modus `lane-goal {lane}` (Lane-Roadmap + kopierbarer Goal — NEU 2026-06-21, BL-448)
> Encodiert das Muster, das im 3-Lane-Parallel-Lauf ~mehrfach ad-hoc gemacht wurde: der Lead erstellt pro Lane ein
> **detailliertes roadmap.md zum Lesen** (full path zurueck) + einen **kompakten, leicht kopierbaren Goal** (mit expliziten
> `/_X_orchestrate {BL}`-Befehlen) den der User als /goal ins Lane-Terminal pastet. Lead-gefuehrt (kein Auto-Dispatch).

**Aufruf:** `/_roadmap_backlog lane-goal {A|B|C}` (Lane aus `_worktree_registry.md` ableitbar).

**Schritte (der Lead fuehrt sie selbst aus):**
```
1. Lane-Daten: _lane_plan.md (Lane-Queue + done + theme) + je-BL Status/Reifegrad/Titel aus _backlog_index.md +
   Knoten-Inhalt (Problem/Fix) lesen. Blocked/gated markieren.
2. roadmap.md schreiben -> {worktree}/roadmap.md (das LANGE Lese-Dokument, **>3.5k Token**). Pflicht-Sektionen:
   Header/Identitaet · Mission · HARTE PROZESS-GRENZE (A→IDF→SDF→I, INV-AO-CALLER, INV-BUILD-GRAIN RED!=GREEN,
   INV-VEHIKEL, ARCHITEKT-1) · Walker-Loop · Disjunkt-Fence (own/forbidden) · DIE QUEUE (je BL: Problem→Fix mit AKs,
   de-jargoned Klartext) · Reihenfolge-Logik · develop-Sync · Definition-of-Done · SSoT.
3. Full path des roadmap.md ausgeben (+ optional in Clipboard via clip.exe).
4. Kompakten GOAL ausgeben (Code-Block, **<4000 Zeichen, REINES ASCII** — keine Umlaute/Em-Dash/Pfeil-Glyphen:
   `->` statt Pfeil, `ae/ue/oe/ss`, `!=` — sonst Terminal-Encoding-Muell `ÔåÆ`). Goal-Struktur:
     Zeile1: GOAL Lane {X} - {Thema} (branch roadmap-{x}). Vorgaenger-Stand.
     Volle Roadmap: {full path}
     QUEUE (Reihenfolge): BL-a -> BL-b -> ... (gated/GATED markieren)
     WALKER-LOOP: 1.git merge develop 2.Reifegrad->Einstieg 3.Pipeline RED!=GREEN 4.Closure+merge_seam 5.naechstes BL selbst (hil=off)
     JETZT: /_{A|IDF|SDF}_orchestrate {erstes-BL}   <- EXPLIZITER Start-Befehl, reifegrad-korrekt
     HARTE REGELN: INV-AO-CALLER / INV-BUILD-GRAIN RED!=GREEN / FENCE {own} / ARCHITEKT-1 / STUCK->parken+naechstes
5. Verifizieren: roadmap.md >14000 Zeichen; Goal <4000 Zeichen + `LC_ALL=C grep -q '[^ -~]'` == leer (ASCII-rein).
```

**Few-Shot-Beispiel (gekuerzt, real gebaut 2026-06-21 — Lane A v3):**
```
GOAL Lane A v3 - Parallelitaet & Skalierung (branch roadmap-a). v1+v2 KOMPLETT. heal_optimize_first erfuellt -> Ausbau.
Volle Roadmap: C:/Users/hanno/RiderProjects/OmniCommand-wtA/roadmap.md
QUEUE (Reihenfolge): BL-194 -> 230(KROENUNG paralleler I_orchestrate) -> 370 -> 375 -> 332 -> 297 -> 233(GATED, zuletzt).
WALKER-LOOP: 1.git merge develop 2.Reifegrad->Einstieg(UNREIF=/_A_orchestrate|REIF=/_IDF_orchestrate|mid=/_SDF_orchestrate --resume) 3.Pipeline A->IDF->SDF(C3 M{N}->/_I_orchestrate;RED!=GREEN getrennte Worker)->/_SDF_orchestrate_post->C7 exit0 4.commit->merge_seam develop 5.naechstes BL selbst (done/gated skip, hil=off).
JETZT: /_A_orchestrate BL-194 (Multi-Process-Coordinator, Basis fuer BL-230).
HARTE REGELN: INV-AO-CALLER (DU laedst /_X_orchestrate SELBST, NIE via Agent); INV-BUILD-GRAIN (M2/M3 RED-Worker!=GREEN-Worker, kein monolithic-build); FENCE nur Lane-A; ARCHITEKT-1 (Pflaster->proper-fix-BL); STUCK->parken+naechstes.
```
> Weitere reale Beispiele: Lane C v2 (gated Cutover — Goal mit GATE-VERTRAG statt hil=off-Autopilot), Lane B (Walker durch Wissens-Queue). Variante je Lane-Charakter: autonom (A/B) vs gated (C destruktiver Cutover).

**INV-ROADMAP-5 (lane-goal):** der Goal ist IMMER <4000 Zeichen + reines ASCII (kopierbar ohne Encoding-Muell); das roadmap.md ist das lange Lese-Dokument (>3.5k Token); beide trennen Lese-Tiefe (roadmap) von Paste-Knappheit (goal). Der Goal traegt IMMER den expliziten `/_X_orchestrate {BL}`-Start-Befehl (reifegrad-korrekt) — der User soll nichts raten muessen.

## Invarianten
- **INV-ROADMAP-1:** der Command schlaegt NUR prozess-korrekte Befehle vor (A→IDF→SDF→SC/I per Reifegrad). Kein BDF-Auto-Reorder, kein Quick-Fix-Bypass.
- **INV-ROADMAP-2:** der Lead fuehrt den vorgeschlagenen Orchestrator SELBST aus (INV-AO-CALLER) — der Command tut es NIE fuer ihn (kein Auto-Dispatch, kein Mega-Worker).
- **INV-ROADMAP-3:** read-only im status/next-Modus (kein Vault-Write); `set` schreibt nur Roadmap-Doku.
- **INV-ROADMAP-4:** die Build-Reihenfolge ist die kuratierte ORDER-Block-Liste, nicht eine geratene Prosa-Extraktion.

## Verwandte
- `/_roadmap_parkingLot {BL}` (Micro-Bruder, roadmap_parkinglot.py) · `/_roadmap` (Dispatcher Macro↔Micro).
- `/_help` (Pipeline-Spec = SOLL-Quelle des Routings) · `/_goal_backlog` (treibt READY-BLs goal-driven, picks aber Status; /_roadmap_backlog respektiert die kuratierte Reihenfolge) · `/_BDF_orchestrate` (Auto-Reorder — bewusst NICHT der /_roadmap-Pfad).
- Kern: `.claude/scripts/roadmap_status.py` (TDD: `test_roadmap_status.py`).
