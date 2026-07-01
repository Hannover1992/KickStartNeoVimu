# /_roadmap_stern — der Nordstern (langfristiges Lane-Ziel, oberste Zoom-Stufe)

> **Die Roadmap-Hierarchie (drei Zoom-Stufen):**
> - **`/_roadmap_stern {lane}`** — der **NORDSTERN**: der mehrphasige End-Zustand einer Lane (Jahre/Endgame).
> - **`/_roadmap_backlog`** — **MAKRO**: welches BL als naechstes, Richtung Stern (A->IDF->SDF per Reifegrad).
> - **`/_roadmap_parkingLot {BL}`** — **MIKRO**: wo INNERHALB eines BL (PL-Items/Sub-Batches/%).
>
> Stern setzt die Richtung, Backlog waehlt das naechste BL dahin, ParkingLot zoomt ins BL. `/_roadmap` ist der duenne Dispatcher (BL-Arg->parkingLot, lane-Arg->stern, sonst->backlog).

**Zweck:** den **langfristigen Endzustand** einer Lane festhalten + spiegeln — die Phasen (P1..Pn), die
Termination ("fertig + selbst-erhaltend", nicht "ausgebaut") und die Fence. Der Stern ueberlebt jedes
`/goal clear` (er liegt in `roadmap.md`, nicht im fluechtigen `/goal`). Read-only im status-Modus; `set` schreibt nur Doku.

## Aufruf
```
/_roadmap_stern {A|B|C}            # Default status: WO stehe ich vs. meinem Nordstern (welche Phase)
/_roadmap_stern set {A|B|C}        # Nordstern aufstellen/aktualisieren (LANGZIEL in roadmap.md)
```

## Kern-Prinzip (was ein Stern IST und NICHT ist)
- Ein Stern ist **Vollenden, nicht Erforschen.** Termination = "das Vorhandene fertig + haelt sich selbst",
  NICHT "neue Vision gebaut". Forschungs-/Wunschdenken-Phasen gehoeren NICHT in einen Stern (-> HOLD-Backlog).
- Ein Stern ist **mehrphasig** (P1..Pn) und damit **Mehr-Session**. Darum: ein Stern ist ein REFERENZ-Nordstern
  in `roadmap.md`. Als aktives `/goal` getrieben NUR mit **work-until-drop** (sonst Stop-Hook-Loop, BL-459) —
  das aktive Tagesziel bleibt sonst ein single-step `/_roadmap_backlog`-Schritt.
- Die drei Lanes sind die drei Teile EINES echten System-Ziels: **A=Engine stabilisiert+selbstheilend ·
  C=Wahrheits-Substrat vollstaendig+verlustfrei · B=Views vollstaendig+selbst-erhaltend.** Wenn alle drei
  terminieren, ist das System fertig.

## Modus `set {lane}` (Stern aufstellen)
```
1. Lane-Daten: aktueller Stand (git/Index/_lane_plan), die committed Richtung, die HOLD/gated Abgrenzung.
2. Phasen ableiten (P1..Pn): vollendende Schritte Richtung Endzustand. Forschung/neue Features AUSSCHLIESSEN
   (die sind HOLD/delay). Jede Phase = ein Buendel verwandter BLs.
3. Termination formulieren: der konkrete "fertig + selbst-erhaltend"-Zustand.
4. Fence: was die Lane besitzt vs. NICHT (disjunkt zu den anderen Sternen).
5. Schreiben: `{worktree}/roadmap.md` Sektion `## NORDSTERN (LANGZIEL)` (oder eigene STERN-Doku).
   + kopierbarer ASCII-LANGZIEL-Block ausgeben (<3.5k, reines ASCII: `->`, `!=`, ae/ue/oe).
6. Hinweis mitgeben: Stern = Referenz; aktives /goal = single-step (oder Stern + work-until-drop).
```

## Few-Shot (real gesetzt 2026-06-23 — das echte 3-Teil-Ziel)
```
LANGZIEL Lane A - ENGINE STABILISIERT + SELBSTHEILEND. Teil 1/3. KEINE Forschung, KEINE neuen Features.
  P1 HEILUNG (BL-443 Vault-Korruption) -> P2 BUG-KLASSEN STRUKTURELL SCHLIESSEN (jeder Bug -> ein Guard:
  456/459/452/454/449/421/437/461/462/366/348 + Counter-Lock) -> P3 SELBST-ERHALTUNG (Deviation-Observer/
  Drift-Guard, ARCHITEKT-1 automatisiert). TERMINATION: 0 manuelle Pflaster, selbstheilende Fabrik.
LANGZIEL Lane C - WAHRHEITS-SUBSTRAT VOLLSTAENDIG+VERLUSTFREI. Teil 2/3.
  P1 SUBSTRAT KOMPLETT (referenced_by-Inversion + Edge-Qualitaet) -> P2 KONSUMENTEN-ABSICHERUNG (Regression
  340/302) -> P3 FORWARD-GARANTIE (Loss=0 vorwaerts). TERMINATION: verbundener verlustfreier Graph, source=atomic.
LANGZIEL Lane B - VIEWS VOLLSTAENDIG+SELBST-ERHALTEND. Teil 3/3.
  P1 VIEW->ATOM-REFERENZIERUNG (BL-460-Schwarm, gated_on BL-443) -> P2 FORWARD-GARANTIE (neue Views auto-ref).
  TERMINATION: jede View projiziert verifiziert aus dem Substrat, selbst-erhaltend.
```

## Invarianten
- **INV-STERN-1:** ein Stern enthaelt NUR vollendende Phasen — Forschung/neue-Features sind ausgeschlossen (HOLD/delay).
- **INV-STERN-2:** Termination ist "fertig + selbst-erhaltend", nicht "ausgebaut".
- **INV-STERN-3:** Stern ist Referenz (`roadmap.md`); aktives /goal = single-step ODER Stern+work-until-drop (BL-459-bewusst).
- **INV-STERN-4:** die Lane-Sterne sind disjunkt (jede besitzt einen Teil des einen System-Ziels).
- **INV-STERN-5 (ROADMAP-2-Erbe):** read-only im status-Modus; der Lead fuehrt die Orchestratoren SELBST (INV-AO-CALLER).

## Verwandte
- `/_roadmap_backlog` (Makro, welches BL) · `/_roadmap_parkingLot {BL}` (Mikro, innerhalb BL) · `/_roadmap` (Dispatcher).
- `/_goal_backlog` (treibt READY-BLs) · `.claude/GOAL.md` (Regent). Befund-/Stand-Doku: `.claude/analysis/_watchdog_log.md`.
