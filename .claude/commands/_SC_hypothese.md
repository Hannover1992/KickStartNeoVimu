---
type: building-block
depends_on:
  - _SC_qualityGate
  - _SC_observe
feeds_into:
  - _SC_implement
related:
  - _gap
---

# /_SC_hypothese

Du stellst eine Hypothese auf und planst ein Experiment.
Dies ist die KREATIVE Phase: Loesungen ERFINDEN auf Basis der Analyse-Findings.
Der Ist-Zustand ist bekannt (aus _SC_observe). Hier wird VORHERGESAGT, nicht beobachtet.

**Sektions-Sequenzierung (v2.0+):**
Sektion 0 (Garbage Collection, PFLICHT ab Cycle 2) ZUERST, dann Sektion 1 (Hypothese).

## Aufruf

```
/_SC_hypothese [easy|normal|hard]
```

Default ohne Parameter: **normal**

---

## VERTRAG (Pflicht-I/O)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_SC_hypothese                                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  LIEST (Input) - PFLICHT:                                                ║
║    1. {VAULT}/_manifest.md                                      ║
║    2. {WORKING_DIR}/.claude/analysis/synthese/{NAME}-OBSERVE{CYCLE}.md ◄── MUSS EX.  ║
║       Findings aus _SC_observe (Sektion A)                              ║
║    3. {WORKING_DIR}/.claude/analysis/synthese/{NAME}-QUALITYGATE{CYCLE}.md ◄── MUSS  ║
║       Quality Gates (BR-Status, Kohaesion, BSD-Trigger, GC)            ║
║    4. {VAULT}/.../Model/{NAME}_Model.md ◄── MUSS EXISTIEREN             ║
║       FALLBACK: .claude/models/{NAME}_Model.md                          ║
║       Enthaelt GC-Markierungen (WIDERLEGT/ELIMINIERT)                   ║
║       Kap. 6a (Offene Bereiche, Aktive TCs)                             ║
║    5. SC_PIPELINE_STATE.next_cycle_context (aus Manifest, Z3: P2 RF-09)║
║       Falls vorhanden: verify_status, unimplemented_slices,             ║
║       next_focus_override, i_loc_delta, pre_filter_veto                 ║
║       ◄── PFLICHT-Input ab Cycle 2 (wenn I-Pipeline gelaufen)          ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║                                                                          ║
║    Welle 1 (Drafts, bei normal+hard):                                    ║
║      .claude/analysis/drafts/{NAME}-hypothese-D01-{fokus}.md            ║
║      .claude/analysis/drafts/{NAME}-hypothese-D02-{fokus}.md            ║
║      ... (pro Agent eine Datei)                                          ║
║                                                                          ║
║    Welle 2 (Synthese = DU, Hauptagent, BL-050 Vault-First):              ║
║      PRIMAER: {VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HYPOTHESEN.md ║
║      FALLBACK: {WORKING_DIR}/.claude/analysis/synthese/{NAME}-HYPOTHESEN.md            ║
║      → Sektion 0: Garbage Collection (PFLICHT ab Cycle 2)               ║
║      → Sektion 1: Genau 1 falsifizierbare Hypothese                     ║
║                                                                          ║
║    Manifest (IMMER):                                                     ║
║      {VAULT}/_manifest.md (aktualisieren)                       ║
║                                                                          ║
║  MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):                        ║
║    Pattern A: Reiner State-Write — kein Protokoll-Eintrag               ║
║    SCHREIBT STATE: SC_HYPOTHESE_{CYCLE}: {YAML-Block}                   ║
║    SCHREIBT NICHT: _manifest_protokoll.md                               ║
║    (Rollover historischer SC_HYPOTHESE_Z{N-2} Bloecke                  ║
║     → Verantwortung von _SC_orchestrate Phase 3.3.0)                   ║
║                                                                          ║
║  NEUE Pflichtfelder im HYPOTHESEN-Dokument:                              ║
║    ┌──────────────────────┬──────┬──────┬──────────────────────────────┐ ║
║    │ Feld                  │ Typ  │ Ovrd │ Inhalt                      │ ║
║    ├──────────────────────┼──────┼──────┼──────────────────────────────┤ ║
║    │ Widerlegte Annahmen  │ PC2  │ HO   │ GC Sek.0: Nicht mehr        │ ║
║    │ (GC Sektion 0)       │      │      │ gueltige W{n} auflisten     │ ║
║    │ Verifikations-Krit.  │VERSCH│ HO   │ Typ V1-V5, PASS/FAIL-Def.  │ ║
║    │ Scope-Deklaration    │VERSCH│ SO   │ IC-Name, Dateien, LOC       │ ║
║    │ Atomaritaets-Check   │ OPT  │ SO   │ >5 Dateien/>100 LOC:       │ ║
║    │                       │      │      │ Begruendung                 │ ║
║    │ Teilproblem-Fokus    │ PC2  │ SO   │ Bei Split: Welches          │ ║
║    │ (bei Model-Split)    │      │      │ Teilmodel? → ViewModel-Idx  │ ║
║    └──────────────────────┴──────┴──────┴──────────────────────────────┘ ║
║                                                                          ║
║  COMPACT-SICHER:                                                         ║
║    Nach Welle 1 kann /compact ausgefuehrt werden.                        ║
║    Welle 2 liest aus drafts/{NAME}-hypothese-D*.md.                     ║
║                                                                          ║
║  3-TUPEL POSITION:                                                       ║
║    [_SC_qualityGate] ──▶ [_SC_hypothese] ──▶ [_SC_implement]            ║
║    Liest Output von _model + _SC_qualityGate (inkl. GC-Markierungen),          ║
║    schreibt Input fuer _SC_implement (inkl. Verif. + Scope)             ║
║                                                                          ║
║  MCP INTEGRATION (OPTIONAL, Uncle Bob Clean Code):                       ║
║    - mcp__cleancoder__query() fuer Design-Entscheidung                  ║
║    - Query Topics:                                                       ║
║      * "design approach for {hypothesis description}"                   ║
║                                                                          ║
║  MCP-BREMSE:                                                             ║
║    ┌─────────────────────────────────────────────────────────┐           ║
║    │  MIN-Modus → max 1 Query, limit=1                       │           ║
║    │  NUR bei Design-Unsicherheit, nicht routinemaessig       │           ║
║    │  Modi:  min=1Q/1R  middle=3Q/3R  max=5Q/5R            │           ║
║    └─────────────────────────────────────────────────────────┘           ║
║                                                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: Manifest + Inputs lesen

**IMMER als Erstes:**

1. Lies `{VAULT}/_manifest.md`
   - Ermittle den aktuellen {NAME}
   - Pruefe ob Phase _SC_qualityGate abgeschlossen ist
   - Lies **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus der System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab (siehe Manifest → Modell-Zuordnung)
   - Lies **STAGNATION** Zaehler (Kontext fuer Hypothese-Formulierung)
2. Lies `{WORKING_DIR}/.claude/analysis/synthese/{NAME}-OBSERVE{CYCLE}.md`
   - Falls nicht vorhanden → FEHLER: "Keine Observation gefunden. Starte erst /_SC_observe"
   - Lies Sektion A (Findings) fuer Hypothese-Basis
3. Lies `{WORKING_DIR}/.claude/analysis/synthese/{NAME}-QUALITYGATE{CYCLE}.md`
   - Falls nicht vorhanden → FEHLER: "Keine Quality Gates gefunden. Starte erst /_SC_qualityGate"
   - Lies BR-Status, Kohaesion, BSD-Trigger, GC-Markierungen
4. Lies Model (PRIMAER Vault, FALLBACK lokal):
   # PRIMAER: Vault (BL-065)
   `{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md`
   # FALLBACK: lokal (Legacy)
   # fallback-read: expected vault, using .claude/
   ODER `.claude/models/{NAME}_Model.md`
   - Verifizierte Wahrheiten als Basis fuer Hypothese
   - **NEU:** Pruefe auf WIDERLEGT/ELIMINIERT markierte W{n}
   - **NEU:** Lies Kap. 6a (Offene Bereiche, Aktive TCs) fuer Scope-Orientierung
   - **NEU:** Bei Model-Split: Lies Model-Topologie fuer Fokus-Teilmodel

5. **(Z3: P2, RF-09) Lies `SC_PIPELINE_STATE.next_cycle_context` aus Manifest**
   - Falls vorhanden (I-Pipeline war gelaufen):
     - `verify_status`: Ergebnis der letzten I-Pipeline
     - `unimplemented_slices`: Nicht-abgeschlossene Slices → Fokus-Kandidaten
     - `next_focus_override`: I-Empfehlung fuer naechsten Fokus (PRIORITAET)
     - `i_loc_delta`: LOC der letzten Implementierung (Kontext)
     - `pre_filter_veto`: Ob PRE-FILTER VETO gesetzt hat
   - Falls `next_focus_override` nicht leer:
     → Hypothese MUSS diesen Fokus aufnehmen (I-Empfehlung hat Prioritaet)
   - Falls `verify_status != "done"`:
     → Fokus auf `unimplemented_slices` richten
   - Falls nicht vorhanden: SKIP (Zyklus 1 oder kein I-Lauf)

---

## Kontext

```
    /_model ──▶ /_SC_observe ──▶ /_SC_modelMaintain ──▶ /_SC_qualityGate ──▶ [/_SC_hypothese] ──▶ /_SC_implement ──▶ /_SC_ergebnis

    INPUT:  {NAME}_Model.md (inkl. GC-Markierungen, Kap. 6a)
            {NAME}-OBSERVE{CYCLE}.md (Findings)
            {NAME}-QUALITYGATE{CYCLE}.md (Quality Gates)
    OUTPUT: {NAME}-HYPOTHESEN.md (Sek.0: GC, Sek.1: Hypothese + Verif. + Scope)
```

---

## Schwierigkeits-Parameter

| Schwierigkeit | Drafts (Welle 1) | Synthese (Welle 2) |
|---------------|------------------|-------------------|
| **easy** | --- | 1 (DU, Hauptagent) |
| **normal** | 2-3 Subagenten | 1 (DU, Hauptagent) |
| **hard** | 3-5 Subagenten | 1 (DU, Hauptagent) |

**System-Model (aus Manifest):** Bestimmt welches Modell pro Welle laeuft.
- opus: Drafts=sonnet, Synthese=opus
- sonnet: Drafts=sonnet, Synthese=sonnet
- haiku: Drafts=haiku, Synthese=haiku

---

## Ablauf: Normal (Standard)

```
Welle 1:  ┌───┐ ┌───┐ ┌───┐
DRAFTS    │ D │ │ D │ │ D │  ──LIEST──▶ MODEL + OBSERVE + QUALITYGATE
          └─┬─┘ └─┬─┘ └─┬─┘  ──SCHREIBT──▶ drafts/{NAME}-hypothese-D*.md
            └─────┼─────┘
                  │
             [/compact moeglich]
                  │
                  ▼
Welle 2:  ┌──────────────────┐
SYNTHESE  │  DU, Hauptagent  │  ──LIEST──▶ drafts/{NAME}-hypothese-D*.md
          │  Sek.0 → Sek.1   │  ──SCHREIBT──▶ synthese/{NAME}-HYPOTHESEN.md
          └──────────────────┘
```

---

## Welle 1: Drafts (Recherche + Bewertung)

### Agent-Auftraege

```
Du bist Drafter D{NN} fuer die Hypothesen-Recherche von "{NAME}".

INPUT - LIES ZUERST DIESE DATEIEN:
  1. # PRIMAER: Vault (BL-065)
     {VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md
     # FALLBACK: lokal (Legacy)
     # fallback-read: expected vault, using .claude/
     ODER .claude/models/{NAME}_Model.md
  2. {WORKING_DIR}/.claude/analysis/synthese/{NAME}-OBSERVE{CYCLE}.md
  3. {WORKING_DIR}/.claude/analysis/synthese/{NAME}-QUALITYGATE{CYCLE}.md

AUFTRAG: {Fokus-Beschreibung}

WICHTIG - GARBAGE COLLECTION BEACHTEN:
  - Pruefe welche W{n} als WIDERLEGT oder ELIMINIERT markiert sind
  - Dein Loesungsvorschlag darf NICHT auf widerlegten W{n} basieren
  - Falls dein Ansatz auf einer W{n} basiert die ELIMINIERT ist:
    Explizit begruenden warum Re-Aktivierung sinnvoll ist

SCHREIB-PFLICHT:
Du MUSST deine Findings in folgende Datei schreiben:
  .claude/analysis/drafts/{NAME}-hypothese-D{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  name: {NAME}
  phase: hypothese
  wave: drafts
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  agent: D{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  reads: models/{NAME}_Model.md, synthese/{NAME}-OBSERVE{CYCLE}.md, synthese/{NAME}-QUALITYGATE{CYCLE}.md
  status: final
  ---

  # Hypothese-Recherche D{NN}: {Fokus-Titel}

  ## Gelesene Inputs
  - MODEL: v{X.Y}, W1-W{N} Wahrheiten ({M} WIDERLEGT, {K} ELIMINIERT)
  - OBSERVE: {Datum}, {Kern-Findings}

  ## GC-Beruecksichtigung
  Widerlegte W{n} die NICHT als Basis verwendet werden: {Liste}

  ## Loesungsansatz
  {Beschreibung des Ansatzes}

  ## Geplante Aenderungen
  | Datei | Zeile | Aenderung |
  |-------|-------|-----------|

  ## Verifikations-Vorschlag
  Typ: V{1-5}
  PASS-Kriterium: {konkret}
  FAIL-Kriterium: {konkret}

  ## Scope-Einschaetzung
  IC: {Name des Implementierungs-Concerns}
  Dateien: {geschaetzte Anzahl}
  LOC: {geschaetzte Anzahl}

  ## Vor- und Nachteile
  | Pro | Contra |
  |-----|--------|

  ## Risiken
  {Was kann schiefgehen?}

  ## Zusammenfassung
  {5-10 Saetze}

WICHTIG:
- Model-Wahrheiten (W{n}) als Basis nutzen — AKTIVE, nicht WIDERLEGTE!
- Observe-Findings beruecksichtigen
- Der Ist-Zustand ist BEKANNT (aus ANALYSE.md) — NICHT nochmal erheben!
- Fokus auf LOESUNGEN ERFINDEN, nicht Status re-analysieren
- Die Datei MUSS geschrieben werden
```

### Drafter-Fokus-Bereiche

| Agent | Fokus | Aufgabe |
|-------|-------|---------|
| D01 | loesungs-optionen | Welche Loesungswege gibt es? Alternativen bewerten |
| D02 | alternativen | Andere Loesungswege, Best Practices |
| D03 | risiko-analyse | Was kann schiefgehen? Gegen-Hypothesen, Edge Cases |
| D04-D05 | (bei hard) | Tiefere Recherche, weitere Perspektiven |

### Nach Welle 1: Manifest aktualisieren

**NACH dem Manifest-Update kann /compact ausgefuehrt werden.**

---

## Welle 2: Synthese (DU, Hauptagent - Sektions-Sequenzierung)

### Voraussetzung

Lies ALLE Dateien in `.claude/analysis/drafts/{NAME}-hypothese-D*.md`

### Dein Auftrag

**SEKTIONS-SEQUENZIERUNG: Sektion 0 ZUERST (ab Cycle 2), DANN Sektion 1.**

#### SEKTION 0: Garbage Collection (PC2/HO, PFLICHT ab Cycle 2)

**Override:** HARD-OVERRIDE (HO-05). Bei Override: Begruendung dokumentieren.

1. Lies ERGEBNIS-Dokument: Widerlegungs-Marker (DIREKT WIDERSPRUCHLICH)
2. Lies Model: Alle W{n} mit Status WIDERLEGT oder ELIMINIERT
3. Lies QUALITYGATE: GC-Markierungen (BR-Bewertung, Kohaesion)
4. **LISTE AUF:** "Folgende W{n} gelten NICHT MEHR:"
   - W{x}: WIDERLEGT — Grund: {aus ERGEBNIS/QUALITYGATE}
   - W{y}: ELIMINIERT — Grund: {aus QUALITYGATE BR-Bewertung}
5. **PRUEFE:** Basiert ein Drafter-Vorschlag auf einer widerlegten/eliminierten W{n}?
   - Falls JA: Vorschlag VERWERFEN oder ANPASSEN
6. **BESTAETIGE:** "Neue Hypothese basiert NUR auf AKTIVEN W{n}: {Liste}"

**Cycle 1:** Sektion 0 entfaellt (noch keine widerlegten W{n} vorhanden).

#### SEKTION 0b: ANALYSE-Modus-Check (Z5: RF-08, NUR wenn sc_mode == ANALYSE)

```
# (Z5: RF-08, W241) ANALYSE-Modus: Hypothese = Forschungsfragen statt Implementierungs-Plan

IF sc_mode == "ANALYSE":
  → Hypothese formuliert FORSCHUNGSFRAGEN (nicht Implementierungs-Schritte)
  → Format: "Was passiert wenn... / Welchen Effekt hat... / Unter welchen Bedingungen..."
  → Kein "Geplante Aenderungen" Abschnitt (kein Code-Plan)
  → Kein "Scope-Deklaration" (kein IC/LOC)
  → Stattdessen: "Forschungsfragen" Abschnitt + "Erwartete Erkenntnisse" Abschnitt
  → Verifikations-Kriterium: Typ V-ANALYSE (Beobachtung statt Test)
  → Status: "BEREIT FUER ANALYSE" statt "BEREIT FUER IMPLEMENTATION"
  Logge: "[ANALYSE-Modus] Hypothese = Forschungsfragen (RF-08)"
ELSE:
  → Normaler Implementierungs-Plan (siehe Sektion 1 unten)
```

#### SEKTION 1: Hypothese formulieren

7. Lies alle Draft-Reports
8. Bewerte die verschiedenen Ansaetze
9. Waehle den vielversprechendsten
10. Formuliere **genau 1 falsifizierbare Hypothese** (HO-06)
10a. **ADR-COOLING-RULE (Guard):** Pruefe W{n}-Alter fuer ADR-Nutzung:
    - W{n} die im SELBEN Cycle NEU formuliert wurden (nicht aus vorherigen Zyklen
      uebernommen) duerfen NICHT als EINZIGE Basis fuer ADR-Entscheidungen dienen.
    - Cooling-Regel: Mindestens 1 GC-Verifikation (naechster Cycle) bevor
      eine neue W{n} als alleiniges ADR-Fundament gelten darf.
    - AUSNAHME: W{n} die durch externe Evidenz (Tests, Code, Logs) direkt
      belegt sind, koennen sofort als ADR-Basis dienen.
    - Hintergrund: DCSRE-93 ADR v1 basierte auf W39 (im selben Cycle formuliert,
      untracked MockProvider) → ADR v1 komplett invalidiert → 1 Zyklus Overhead.
11. Definiere **Verifikations-Kriterium** (HO-07)
12. Definiere **Scope-Deklaration** (HO-08)
13. Pruefe **Atomaritaets-Check**
14. Plane das Experiment
15. Schreibe `{WORKING_DIR}/.claude/analysis/synthese/{NAME}-HYPOTHESEN.md`

### Hypothesen-Dokument Struktur

```markdown
---
name: {NAME}
phase: hypothese
wave: synthese
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: Hauptagent
date: {YYYY-MM-DD}
reads: models/{NAME}_Model.md, synthese/{NAME}-OBSERVE{CYCLE}.md, synthese/{NAME}-QUALITYGATE{CYCLE}.md
status: final
---

# Hypothese: {NAME}

**Datum:** YYYY-MM-DD
**Iteration:** N
**Model-Basis:** {NAME}_Model.md v{X.Y}
**Observe-Basis:** {NAME}-OBSERVE{CYCLE}.md
**QualityGate-Basis:** {NAME}-QUALITYGATE{CYCLE}.md

============================================================
SEKTION 0: GARBAGE COLLECTION (PFLICHT ab Cycle 2)
============================================================

## Widerlegte Annahmen (PC2/HO)

| W{n} | Status | Grund | Quelle |
|------|--------|-------|--------|
| W{x} | WIDERLEGT | {Beschreibung} | ERGEBNIS{K} / QUALITYGATE{N} |
| W{y} | ELIMINIERT | {Beschreibung} | QUALITYGATE{N} BR-Bewertung |

**Bestaetigung:** Neue Hypothese basiert NUR auf AKTIVEN W{n}: {Liste}

(Cycle 1: "Erster Zyklus, keine widerlegten W{n} vorhanden.")

============================================================
SEKTION 0 ABGESCHLOSSEN
============================================================

============================================================
SEKTION 1: HYPOTHESE
============================================================

## Hypothese (Falsifizierbar)

> Wenn wir [AENDERUNG X] vornehmen,
> dann wird [ERWARTETES VERHALTEN Y] eintreten,
> weil [BEGRUENDUNG Z].

## Begruendung
- Model-Wahrheiten die stuetzen: W{n}, W{m} [alle AKTIV]
- Analyse-Findings: F{n}
- Drafter-Recherche: D{NN}

## Verifikations-Kriterium (VERSCH/HO)

**Override:** HARD-OVERRIDE (HO-07). Bei Override: Begruendung dokumentieren.

| Feld | Wert |
|------|------|
| Typ | V{1-5} ({Beschreibung}) |
| Konkrete Pruefung | {Was genau ausfuehren} |
| PASS-Definition | {Exakt wann PASS} |
| FAIL-Definition | {Exakt wann FAIL} |

**Verifikations-Typen:**

| Typ | Beispiel | Wann geeignet |
|-----|----------|---------------|
| V1 | Projekt kompiliert (`dotnet build`) | Minimaler Chunk, neue Klasse |
| V2 | Unit-Test laeuft gruen | Isolierte Logik |
| V3 | Container startet healthy | Infrastruktur-Aenderung |
| V4 | Log-Pattern erscheint | Integration/Laufzeit |
| V5 | End-to-End Request/Response | Feature-Abschluss |

## Scope-Deklaration (VERSCH/SO)

| Feld | Wert |
|------|------|
| IC (Implementierungs-Concern) | {Name, z.B. "DI-Registration"} |
| Erwartete Dateien | {Anzahl + Liste} |
| Erwartete LOC netto | {Zahl} |
| Teilproblem-Fokus (bei Split) | {TC-Name aus Model-Topologie, oder "Kein Split aktiv"} |

## Atomaritaets-Check (OPT/SO)

| Pruefung | Ergebnis |
|----------|----------|
| Dateien <= 5? | JA / NEIN (→ Begruendung) |
| LOC <= 100? | JA / NEIN (→ Begruendung) |
| Genau 1 IC? | JA / NEIN (→ Atomare Gruppe?) |

**Falls Soft-Limits ueberschritten:**
- [ ] Begruendung dokumentiert ("Warum nicht zerlegbar?")
- [ ] Als EXPLIZITE AUSNAHME deklariert (Atomare Gruppe, W9)
- [ ] User-Signal vorbereitet: "Durchgang ueberschreitet Grenzen. Fortfahren?"

**Falls BEIDE Soft-Limits gleichzeitig ueberschritten:**
→ STOP. Scope verkleinern. Zurueck zu Hypothese-Formulierung.

## Geplante Aenderungen

| # | Datei | Zeile | Aenderung | Typ | AK |
|---|-------|-------|-----------|-----|-----|

## Erwartete Ergebnisse

| Test | Erwartung |
|------|-----------|

## Falsifizierungskriterien
| # | Kriterium | Schwere |
|---|-----------|---------|

## Risiken + Rollback
| Risiko | Mitigation |
|--------|------------|

## Status
BEREIT FUER IMPLEMENTATION

============================================================
SEKTION 1 ABGESCHLOSSEN
============================================================

## Referenzen
| Quelle | Pfad |
|--------|------|
| Drafter D01 | .claude/analysis/drafts/{NAME}-hypothese-D01-*.md |
| OBSERVE | {WORKING_DIR}/.claude/analysis/synthese/{NAME}-OBSERVE{CYCLE}.md |
| QUALITYGATE | {WORKING_DIR}/.claude/analysis/synthese/{NAME}-QUALITYGATE{CYCLE}.md |
| MODEL | .claude/models/{NAME}_Model.md |
```

### Nach Welle 2: Manifest finalisieren

```markdown
**PHASE:** _SC_hypothese abgeschlossen
**NAECHSTER SCHRITT:** /_SC_implement

### Synthese (Welle 2) - {Datum}
- [x] {WORKING_DIR}/.claude/analysis/synthese/{NAME}-HYPOTHESEN.md
- [x] GC Sektion 0: {N} WIDERLEGT, {M} ELIMINIERT (oder "Cycle 1, entfaellt")
- [x] Verifikation: V{x} ({Beschreibung})
- [x] Scope: {IC-Name}, {N} Dateien, {M} LOC
- [x] Atomaritaet: {OK / Ausnahme deklariert}
```

---

## Ablauf: Easy

```
             ┌──────────────────┐
SYNTHESE     │  DU, Hauptagent  │  ──LIEST──▶ MODEL + OBSERVE + QUALITYGATE
             │  Sek.0 → Sek.1   │  ──SCHREIBT──▶ synthese/{NAME}-HYPOTHESEN.md
             └──────────────────┘
```

Keine Drafts noetig. Sektions-Sequenzierung gilt trotzdem (Sek.0 vor Sek.1 ab Cycle 2).

---

## Qualitaetskriterien

- GC Sektion 0 durchgefuehrt (PFLICHT ab Cycle 2, HO-05)
- ADR-COOLING-RULE geprueft: Neu formulierte W{n} (selber Cycle) NICHT als einzige ADR-Basis genutzt, ausser durch externe Evidenz direkt belegt
- Hypothese basiert NUR auf AKTIVEN W{n} (keine WIDERLEGTEN)
- Hypothese ist falsifizierbar (HO-06)
- Genau 1 Hypothese pro Durchgang
- Verifikations-Kriterium definiert mit V1-V5, PASS/FAIL (VERSCH/HO, HO-07)
- Scope-Deklaration: IC benannt, Dateien + LOC geschaetzt (VERSCH/SO, HO-08)
- Atomaritaets-Check: Soft-Limits geprueft, Ausnahme dokumentiert falls noetig
- Aenderungen sind minimal
- Rollback-Plan dokumentiert
- Klare Erfolgskriterien definiert
- Model-Bezug: Welche AKTIVEN W{n} stuetzen die Hypothese
- Draft-Quellen in Referenzen

---

## Naechster Schritt

Nach Abschluss: `/_SC_implement` ausfuehren

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_SC_hypothese abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
