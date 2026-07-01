# PL-Lifecycle State Machine (PN-7, Z1+J3)

Einzige Wahrheitsquelle fuer Status-Format und Transitionen von `_parking-lot.md` Items.
Implementiert in Z1 (2026-03-23). J3 (2026-03-24): QUESTION + STUCKED Terminal-Zustaende.
Nachfolge-Zyklen: Z2 (FREEZE-Logik _finish), Z3+ (ID-Schema).

---

## Status-Format-Tabelle

| Status | Format in `_parking-lot.md` | BDF sieht | Writer |
|--------|----------------------------|-----------|--------|
| OFFEN | `- [ ] **Titel** ...` | `[ ]` → in Batch | — |
| IN_ARBEIT | `- [ ] **Titel** [STATUS: IN_ARBEIT] ...` | `[ ]` → in Batch (Resume-Guard prueft Annotation) | SDF Phase-Start (`task_source=pl`) |
| FREEZE | `- [~] **[FREEZE] Titel** {Snapshot: ...}` | `[~]` → ignoriert (Z251 explizit) | `_finish` / HiL (Z2) |
| QUESTION | `- [?] **[QUESTION] Titel** {Frage: ...}` | `[?]` → ignoriert (Terminal, auto-skip) | SDF Phase 2 (SC OBSERVE: offene Fragen) |
| STUCKED | `- [!] **[STUCKED] Titel** {Grund: ...}` | `[!]` → ignoriert (Terminal, auto-skip) | BDF SCANNING (max_cycles erschoepft) |
| DONE | `- [x] **Titel** (DONE: YYYY-MM-DD)` | `[x]` → ignoriert | SDF GAP=0% |
| ARCHIVIERT | `- [x] ARCHIVIERT (YYYY-MM-DD) **Titel**` | `[x]` → ignoriert | `_finish` / PL-Review (Z2) |

---

## Transitions-Matrix

```
OFFEN       ──────────────→ IN_ARBEIT     SDF Phase-Start: schreibt [STATUS: IN_ARBEIT] (task_source=pl)
IN_ARBEIT   ──────────────→ DONE          SDF GAP=0%: ersetzt [ ] [STATUS: IN_ARBEIT] → [x] (DONE: DATUM)
IN_ARBEIT   ──────────────→ QUESTION      SDF Phase 2: SC OBSERVE findet offene Fragen → [?] (BDF_NEXT_TRIGGER=true)
IN_ARBEIT   ──────────────→ STUCKED       BDF: max_cycles erschoepft (items_failed zaehler > 2) → [!]
IN_ARBEIT   ──────────────→ FREEZE        _finish Dark-Factory-Guard (OUT_OF_SCOPE Z1 → Z2)
IN_ARBEIT   ──────────────→ items_failed  BDF Resume-Guard: IN_ARBEIT + nicht in done/failed → FAILED
FREEZE      ──────────────→ OFFEN         UNFREEZE-Command (OUT_OF_SCOPE Z1 → Z2)
DONE        ──────────────→ ARCHIVIERT    _finish PL-Cleanup (OUT_OF_SCOPE Z1 → Z2)
```

**Trigger-Details:**

| Transition | Trigger | Bedingung |
|-----------|---------|-----------|
| OFFEN → IN_ARBEIT | SDF-Start (`task_source=pl`) | Idempotenz: `IF "[STATUS: IN_ARBEIT]" NOT IN item.text` |
| IN_ARBEIT → DONE | SDF GAP=0% (Phase 2.4d) | `IF task_source == "pl" AND gap_percent == 0` |
| IN_ARBEIT → QUESTION | SDF Phase 2 (SC OBSERVE OQ-Eskalation) | SC findet OQ (offene Fragen) → schreibt `[?]`, setzt BDF_NEXT_TRIGGER=true |
| IN_ARBEIT → STUCKED | BDF SCANNING (max_cycles-Zaehler) | `items_failed[item].retry_count >= 2` → BDF schreibt `[!]` |
| IN_ARBEIT → items_failed | BDF Resume-Guard | Item hat `[STATUS: IN_ARBEIT]` AND `item.name NOT IN items_done AND NOT IN items_failed` |

---

## QUESTION-Semantik: Warum `[?]` Checkbox (J3)

`[?]` signalisiert: Item wurde von SDF analysiert, aber SC hat offene Entscheidungsfragen (OQ)
gefunden, die HiL benoetigen. Das Item ist NICHT fehlgeschlagen — es wartet auf Klaerung.

**BDF-Verhalten:** `[?]`-Items werden in SCANNING wie `[~]`-FREEZE behandelt:
```
open_items = Filtere alle [ ] Items (nicht [x], [~], [?], [!])
```
QUESTION-Items werden UEBERSPRUNGEN — BDF faehrt mit naechsten OFFEN-Items fort.

**ALL_TERMINAL-Check:** Wenn alle verbliebenen Items `[x]`, `[~]`, `[?]`, `[!]` oder `items_blocked`
→ EMPTY (Post-Phase starten), kein unendlicher Loop.

**Writer:** SDF Phase 2 (Schritt 2.3 OQ-Eskalation). Format:
```
- [?] **[QUESTION] Titel** {Frage: Was soll X tun wenn Y? Design-Entscheidung ausstehend.}
```

**Transitionen nach HiL-Antwort:** HiL entscheidet manuell (J3 OUT_OF_SCOPE — kein auto-Resume).
HiL kann Item auf `[ ]` zuruecksetzen → BDF nimmt es beim naechsten Lauf auf.

---

## STUCKED-Semantik: Warum `[!]` Checkbox (J3)

`[!]` signalisiert: Item wurde mehrfach versucht (retry_count >= 2 in BDF items_failed),
konnte aber nicht geloest werden. Max-Zyklen erschoepft.

**BDF-Verhalten:** `[!]`-Items werden in SCANNING wie `[~]`-FREEZE behandelt — uebersprungen.

**Writer:** BDF SCANNING (kein SDF-Aufruf mehr). Format:
```
- [!] **[STUCKED] Titel** {Grund: Max-Zyklen (N Versuche). Letzte Fehler: ...}
```

**Abgrenzung zu BLOCKED:** BLOCKED = externe Abhaengigkeit fehlt. STUCKED = intern erschoepft.
BLOCKED wartet auf Abhaengigkeit, STUCKED wartet auf manuelle Intervention.

---

## FREEZE-Semantik: Warum `[~]` Checkbox

**Verifikation Primaerquelle (`_BDF_orchestrate.md` Z251):**
```
open_items = Filtere alle [ ] Items (offen, nicht [x] oder [~])
```

`[~]` ist BEREITS von BDF-SCANNING explizit ausgeschlossen. Kein zusaetzlicher FREEZE-Guard
in SCANNING erforderlich — nur ein erklaerenden Kommentar (Z251-Naehe).

**Warum NICHT Annotation `[STATUS: FREEZE]`:** Wuerde einen neuen Guard in SCANNING erfordern
und den kritischen Regex-Pfad (Z251) beruehren. `[~]` ist nachweislich bereits ausgeschlossen —
minimales Risiko, Zero-Change fuer BDF-Parsing-Kernlogik.

**Semantik-Fix:** `[~]` war bisher semantisch undefiniert. Nun offiziell: FREEZE-Traeger.

---

## IN_ARBEIT-Semantik: Warum Inline-Annotation

**Anforderung:** OFFEN und IN_ARBEIT muessen beide `[ ]` haben, damit BDF-SCANNING sie findet.
BDF resumt IN_ARBEIT-Items ggf. in neuem Batch — Resume-Guard (Idempotenz-Problem F-02/F-05)
unterscheidet sie via `[STATUS: IN_ARBEIT]` Annotation.

**Format:** `- [ ] **Titel** [STATUS: IN_ARBEIT] ...` (Annotation NACH Item-Name)

**BDF-Regex bleibt unveraendert:** `[ ]` Filter in Z251 schliesst `[x]` und `[~]` aus —
IN_ARBEIT mit `[ ]` wird gefunden, Resume-Guard verhindert Doppel-Verarbeitung.

---

## BDF-Vertrag: SDF schreibt PL, BDF nicht

```
BDF SCHREIBT NICHT: _parking-lot.md (NUR SDF, W16)
```

SDF setzt `[STATUS: IN_ARBEIT]` beim ersten Zugriff auf ein PL-Item (Phase-Start, `task_source=pl`).
BDF liest PL (SCANNING) aber schreibt nie hinein. Vertrag bleibt intakt.

---

## ID-Schema (Z3, Forward-Only)

**Entscheidung (2026-03-24, J5):** Forward-Only — nur neue Items erhalten IDs.
Retroaktive Migration aller bestehenden Items ist OUT_OF_SCOPE (Obsidian-Link-Risiko F-14).

### Praefix-Tabelle

| Praefix | Bereich | Beispiel |
|---------|---------|---------|
| `PN` | PL-Lifecycle / State Machine (Meta) | `[PN-7]` |
| `IF` | Infrastruktur / Framework | `[IF-3]` |
| `TR` | Tracking / Fortschritt | `[TR-1]` |
| `BDF` | BigDarkFactory-spezifisch | `[BDF-2]` |
| `USR` | User-Story / Feature | `[USR-5]` |

### Format

```
[PREFIX-NR] Kurzbeschreibung
```

- `PREFIX`: einer der definierten Praefixe (s.o.)
- `NR`: fortlaufend innerhalb des Praefixes (kein Reset bei neuem Zyklus)
- Ohne Praefix: zulaessig fuer Altlasten, neue Items SOLLEN Praefix erhalten

### Vergabe-Regel

Forward-Only: Neue PL-Items erhalten beim Erstellen eine ID (`PREFIX-NR`).
Keine retroaktive Umbenennung bestehender Items (Link-Stabilitaet).
NR wird fortlaufend vergeben — Luecken sind erlaubt (geloeschte Items hinterlassen keine Luecken-Pflicht).

---

## ARCHIVIERT-Semantik (Z3, J6)

**Entscheidung (2026-03-24, J6):** ARCHIVIERT = Item bleibt in `_parking-lot.md`.
Kein separates `_parking-lot-archiv.md` — Migration der ~121 bestehenden `[x]`-Items waere OUT_OF_SCOPE.

### Format

```
- [x] ARCHIVIERT (YYYY-MM-DD) **Titel** ...
```

- `[x]` bleibt als Checkbox — BDF-SCANNING ignoriert `[x]` bereits (Z251)
- Praefixes `ARCHIVIERT (DATUM)` vor dem Titel signalisiert: Item wurde explizit archiviert
- Kombination DONE + ARCHIVIERT in einem `[x]`-Item: erlaubt und konsistent

### Abgrenzung DONE vs. ARCHIVIERT

| Zustand | Format | Bedeutung |
|---------|--------|-----------|
| DONE | `- [x] **Titel** (DONE: YYYY-MM-DD)` | Implementiert, aktiv in Codebase |
| ARCHIVIERT | `- [x] ARCHIVIERT (YYYY-MM-DD) **Titel**` | Nicht implementiert, bewusst verworfen oder PL-Review-Entscheidung |

### Schreiber

`_finish`-Command oder HiL (PL-Review) — SDF schreibt DONE, nicht ARCHIVIERT.

---

## Teilfortschritt-Felder (Optional)

**Konvention (2026-03-24, J7):** Nur fuer IN_ARBEIT Items die ueber mehrere Sessions laufen.

### Felder

| Feld | Format | Bedeutung |
|------|--------|-----------|
| `Phase` | `**Phase:** SC-Z2` | Wo im Pipeline-Prozess das Item aktuell steht |
| `GAP` | `**GAP:** 71%` | Aktueller GAP-Score (0% = fertig) |
| `Letzter Fortschritt` | `**Letzter Fortschritt:** 2026-03-24` | Datum der letzten Bearbeitung |

### Beispiel

```
- [ ] **[PN-7] Beispiel Item** [STATUS: IN_ARBEIT]
  - **Phase:** SC-Z2
  - **GAP:** 71%
  - **Letzter Fortschritt:** 2026-03-24
  - ...
```

Diese Felder sind OPTIONAL — OFFEN-Items ohne laufende Arbeit benoetigen sie nicht.

---

## ADR: /_PL_orchestrate vs /_PO_orchestrate Domain-Konflikt

**Entscheidung (2026-03-24, J8):** Option A — `/_PL_orchestrate` als separater Command.

**Begruendung (SRP):**
- `/_PO_orchestrate` = Paper-to-UserStory Pipeline (Tandem PO+PE+ARC, `op: ProductOwnerPipeline`)
- PL-Lifecycle-Management (Status-Transitions, Archivierung, Fortschritt-Tracking) ist eine eigene Domaene
- Erweiterung von `/_PO_orchestrate` wuerde SRP verletzen — zwei unverwandte Verantwortlichkeiten in einem Command

**Konsequenz:** `/_PL_orchestrate` = neuer Command fuer PL-Lifecycle-Management (OUT_OF_SCOPE Z1 → Z2+).

---

## Referenzen

- `_BDF_orchestrate.md` Z251: FREEZE `[~]` bereits ausgeschlossen
- `_BDF_orchestrate.md` Z254-261: IN_ARBEIT-Idempotenz-Guard (SCANNING)
- `_BDF_orchestrate.md` Z608: Resume-Guard IN_ARBEIT → items_failed
- `_SDF_orchestrate.md` Z686-689: GAP=0% DONE-Transition
- `_parking-lot.md`: Format-Header Kommentar (STATUS-FORMAT PN-7)
