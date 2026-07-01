---
type: satellite
---

# Blind-Spot-Detection + Canary Probes

Du pruefst systematisch ob der aktuelle Fokus korrekt ist.
Dies ist die EXPLORATIVE Phase: Annahmen hinterfragen, Monitoring-Luecken finden,
Canary Probes planen. NICHT im Hauptzyklus — nur bei Trigger oder manuell.

**Epistemologische Grenze (W15):**
Ein System kann seine eigenen Blind Spots nicht vollstaendig erkennen.
Deshalb: Checklisten + Mensch-in-the-Loop als PFLICHT, nicht nur automatischer Trigger.

## Aufruf

```
/_blindspotDetection [normal|hard]
```

Default ohne Parameter: **normal**
Kein easy-Modus (Blind-Spot-Erkennung erfordert diverse Perspektiven).

---

## VERTRAG (Pflicht-I/O)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_blindspotDetection [normal|hard]                             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  LIEST (Input) - PFLICHT:                                                ║
║    1. {VAULT}/_manifest.md                                      ║
║    2. .claude/models/{NAME}_Model.md  ◄── MUSS EXISTIEREN               ║
║       (oder Teilmodelle bei Model-Split + Model-Topologie)               ║
║    3. .claude/analysis/synthese/{NAME}-ANALYSE{CYCLE}.md                 ║
║       ◄── Letzte Analyse (inkl. BSD-Trigger T{x} falls vorhanden)      ║
║    4. .claude/analysis/synthese/{NAME}-ERGEBNIS*.md                      ║
║       ◄── ALLE Ergebnis-Dokumente (Widerspruchs-Muster suchen)         ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. .claude/analysis/synthese/{NAME}-BLINDSPOT{N}.md                   ║
║       → Annahmen-Audit                                                   ║
║       → Monitoring-Luecken                                               ║
║       → Canary-Probe-Plan (max 7, min 1 AUSSERHALB Fokus)              ║
║       → Dead-End-Liste                                                   ║
║       → Empfohlener naechster Schritt                                    ║
║    2. {VAULT}/_manifest.md (aktualisieren)                      ║
║                                                                          ║
║  PFLICHT: MENSCH-IN-THE-LOOP (W15)                                       ║
║    User MUSS Canary-Probe-Platzierung bestaetigen bevor Probes           ║
║    im naechsten _SC_implement-Durchgang umgesetzt werden.                ║
║                                                                          ║
║  CONSTRAINTS (Kap. 2.7):                                                 ║
║    IR-3: BSD-Zyklen zaehlen NICHT fuer Stagnations-Zaehler              ║
║          (solange Erkenntnisse). Ergebnislos = 1 Loop.                   ║
║    IR-4: Max 2 BSD pro Stagnationsphase.                                 ║
║                                                                          ║
║  GRACEFUL DEGRADATION:                                                   ║
║    Ohne diesen Command funktioniert der Zyklus wie bisher.               ║
║    BSD ist OPTIONAL — getriggert von _SC_qualityGate (T1-T5) oder User.        ║
║                                                                          ║
║  3-TUPEL POSITION:                                                       ║
║    [_SC_qualityGate] ──(Trigger T1-T5)──▶ [_blindspotDetection] ──▶ [_SC_observe] ║
║    Erkennt Fokus-Fehler, liefert Canary-Probe-Plan fuer _SC_implement.     ║
║    Erkenntnisse fliessen in die naechste _SC_observe zurueck.               ║
║                                                                          ║
║  COMPACT-SICHER:                                                         ║
║    Nach Welle 1 kann /compact ausgefuehrt werden.                        ║
║    Welle 2 liest aus drafts/{NAME}-blindspot{N}-D*.md.                  ║
║                                                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: Manifest + Inputs lesen

**IMMER als Erstes:**

1. Lies `{VAULT}/_manifest.md`
   - Ermittle den aktuellen {NAME}
   - Lies **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus der System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab (siehe Manifest → Modell-Zuordnung)
   - Lies **STAGNATION** Zaehler (Kontext fuer BSD)
   - Pruefe: Ist dies die 1. oder 2. BSD in der aktuellen Stagnationsphase? (IR-4)
2. Lies `.claude/models/{NAME}_Model.md`
   - Verifizierte Wahrheiten (aktive vs. widerlegte/eliminierte)
   - Offene Fragen
   - Bei Model-Split: Lies Model-Topologie + ALLE Teilmodelle
3. Lies `.claude/analysis/synthese/{NAME}-ANALYSE{CYCLE}.md`
   - Welcher BSD-Trigger wurde erkannt? (T1-T5 aus Sektion B)
   - Aktuelle Findings als Kontext
4. Lies ALLE `.claude/analysis/synthese/{NAME}-ERGEBNIS*.md`
   - Widerlegungs-Muster suchen (welche W{n} wiederholt ZUR PRUEFUNG?)
   - SRS-Verlauf (steigend/stagnierend/fallend?)
5. **Auto-Increment: Bestimme naechste BSD-Nummer {N}**
   - Scanne `.claude/analysis/synthese/{NAME}-BLINDSPOT*.md` auf Disk
   - `{N}` = hoechste gefundene Nummer + 1
   - Suffix-Konvention: `""` fuer 1, `"2"` fuer 2, etc.

**IR-4 Pruefung:**
Falls bereits 2 BSDs in der aktuellen Stagnationsphase existieren:
→ **STOP.** "Maximum 2 BSD pro Stagnationsphase erreicht (IR-4). Zurueck zu /_SC_hypothese."

---

## Kontext

```
    /_SC_qualityGate ──(Trigger T1-T5)──▶ [/_blindspotDetection] ──▶ /_SC_observe
                                          │
                                          ▼
                                   Canary-Probe-Plan
                                          │
                                          ▼
                                   /_SC_implement (Probes einbauen)
                                          │
                                          ▼
                                   /_SC_ergebnis (Probe-Ergebnisse)
                                          │
                                          ▼
                                   /_SC_observe (Erkenntnisse)

    INPUT:  {NAME}_Model.md (alle aktiven W{n})
            {NAME}-ANALYSE{CYCLE}.md (Trigger, Findings)
            {NAME}-ERGEBNIS*.md (ALLE, Widerspruchs-Muster)
    OUTPUT: {NAME}-BLINDSPOT{N}.md (Probes + Dead-Ends + Empfehlung)
```

---

## Trigger-Bedingungen (T1-T5, aus _SC_qualityGate)

| Trigger | Bedingung | DCSRE-881 Beispiel |
|---------|-----------|-------------------|
| T1 | Gleiche Hypothesen-Richtung 2+ mal widerlegt | TLS-Hypothesen 3x widerlegt (Loop 17-31) |
| T2 | Stagnation: 3+ Loops ohne neue W{n} oder Widerlegung | Loop 16-20 ohne starken Fortschritt |
| T3 | Phantom-Erfolg: Teilweise PASS aber Gesamtproblem ungeloest | SSL-Config "gefixt" aber Worker haengt |
| T4 | Fokus-Drift: Fokus weicht von Boundaries-Teilproblemen ab | TLS-Fokus statt Config-Fokus |
| T5 | Model-Explosion: R-AP4 ausgeloest (>25 W{n} UND >4 TC) | 53 W{n}, 6 Concerns bei Loop 25 |

---

## Canary-Probe-Definition (W27, K-R11)

Eine Canary Probe ist eine **temporaere, diagnostische Massnahme** die eine
spezifische Annahme testet. Beispiele:

| Typ | Beispiel | Testet |
|-----|----------|--------|
| **Diagnostisches Logging** | `Console.WriteLine($"Config-Wert: {x}")` | Ob ein Wert zur Laufzeit stimmt |
| **Config-Variante** | Env-Var temporaer aendern | Ob Config die Ursache ist |
| **Infra-Test** | `curl` / `openssl s_client` im Container | Ob Netzwerk/Zertifikate korrekt |
| **Vereinfachung** | Komplexen Code temporaer durch Stub ersetzen | Ob die Komplexitaet die Ursache ist |
| **Isolation** | Nur 1 Komponente starten, Rest deaktivieren | Ob Interaktion die Ursache ist |

**Probes sind TEMPORAER.** Nach Auswertung muessen sie in einem eigenen
_implement-Durchgang entfernt werden.

---

## Schwierigkeits-Parameter

| Schwierigkeit | Drafts (Welle 1) | Synthese (Welle 2) |
|---------------|------------------|-------------------|
| **normal** | --- | 1 (DU, Hauptagent) |
| **hard** | 2-5 Subagenten | 1 (DU, Hauptagent) |

**System-Model (aus Manifest):** Bestimmt welches Modell pro Welle laeuft.
- opus: Drafts=sonnet, Synthese=opus
- sonnet: Drafts=sonnet, Synthese=sonnet
- haiku: Drafts=haiku, Synthese=haiku

---

## Ablauf: Normal (Standard)

```
             ┌──────────────────┐
SYNTHESE     │  DU, Hauptagent  │  ──LIEST──▶ MODEL + ANALYSE + ERGEBNIS*
             │  5 Sektionen     │  ──SCHREIBT──▶ synthese/{NAME}-BLINDSPOT{N}.md
             └──────────────────┘
                     │
                     ▼
             User bestaetigt Canary-Probe-Platzierung
```

Keine Drafts noetig. Du liest alle Inputs und erstellst das BLINDSPOT-Dokument.

---

## Ablauf: Hard

```
Welle 1:  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐
DRAFTS    │ D │ │ D │ │ D │ │ D │ │ D │  ──LIEST──▶ MODEL + ANALYSE + ERGEBNIS*
          └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘  ──SCHREIBT──▶ drafts/{NAME}-blindspot{N}-D*.md
            └─────┴─────┼─────┴─────┘
                        │
                   [/compact moeglich]
                        │
                        ▼
Welle 2:  ┌──────────────────┐
SYNTHESE  │  DU, Hauptagent  │  ──LIEST──▶ drafts/{NAME}-blindspot{N}-D*.md
          │  5 Sektionen     │  ──SCHREIBT──▶ synthese/{NAME}-BLINDSPOT{N}.md
          └──────────────────┘
                        │
                        ▼
             User bestaetigt Canary-Probe-Platzierung
```

---

## Welle 1: Drafts (bei hard)

### Agent-Auftraege

Starte Drafter-Agenten **parallel**. JEDER Agent erhaelt:

```
Du bist Drafter D{NN} fuer die Blind-Spot-Detection von "{NAME}".

INPUT - LIES ZUERST DIESE DATEIEN:
  1. .claude/models/{NAME}_Model.md (alle W{n} + offene Fragen)
  2. .claude/analysis/synthese/{NAME}-ANALYSE{CYCLE}.md (aktuellste)
  3. .claude/analysis/synthese/{NAME}-ERGEBNIS*.md (ALLE)

AUFTRAG: {Fokus-Beschreibung}

TRIGGER-KONTEXT:
  BSD wurde ausgeloest durch: T{x} ({Beschreibung})
  Stagnations-Zaehler: {N}
  Aktuelle SRS-Tendenz: {steigend/stagnierend/fallend}

SCHREIB-PFLICHT:
Du MUSST deine Findings in folgende Datei schreiben:
  .claude/analysis/drafts/{NAME}-blindspot{N}-D{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  name: {NAME}
  phase: blindspot{N}
  wave: drafts
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  agent: D{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  reads: models/{NAME}_Model.md, synthese/{NAME}-ANALYSE{CYCLE}.md, synthese/{NAME}-ERGEBNIS*.md
  status: final
  ---

  # Blind-Spot-Detection D{NN}: {Fokus-Titel}

  ## Gelesene Inputs
  - MODEL: v{X.Y}, {N} aktive W{n}, {M} widerlegte
  - ANALYSE: {Datum}, Trigger T{x}
  - ERGEBNIS: {N} Dokumente, SRS-Verlauf {Tendenz}

  ## Ungepruefte Annahmen
  {Liste von Annahmen die als "gegeben" angenommen aber nie getestet wurden}

  ## Monitoring-Luecken
  {Wo fehlt Logging, Visibility, diagnostischer Zugang?}

  ## Canary-Probe-Vorschlaege
  | # | Probe | Typ (Code/Infra) | Im Fokus? | Aufwand |
  |---|-------|------------------|-----------|---------|

  ## Dead-End-Kandidaten
  {Bereiche die nicht weiter verfolgt werden sollten}

  ## Zusammenfassung
  {5-10 Saetze}

WICHTIG:
- Mindestens 1 Probe AUSSERHALB des aktuellen Fokus-Bereichs vorschlagen (W18)
- Infrastruktur-Probes (Config, Env, Compose) GLEICHBERECHTIGT mit Code-Probes
- KEINE Hypothesen aufstellen — nur Annahmen hinterfragen + Probes planen
- Die Datei MUSS geschrieben werden, NICHT nur als Text zurueckgeben
```

### Drafter-Fokus-Bereiche

| Agent | Fokus | Aufgabe |
|-------|-------|---------|
| D01 | annahmen-audit | Welche aktiven W{n} sind unbewiesen? Welche Annahmen stillschweigend? |
| D02 | monitoring-luecken | Wo fehlt Logging, Visibility? Wo sind "blinde Stellen" im System? |
| D03 | gegen-fokus | BEWUSST ausserhalb des aktuellen Fokus schauen. Was uebersehen wir? |
| D04 | dead-end-analyse | Welche Pfade sind Sackgassen? Welche Patterns wiederholen sich? |
| D05 | alternative-perspektive | First-Principles: Was wuerde ein Neuling anders machen? |

### Nach Welle 1: Manifest aktualisieren

```markdown
**PHASE:** _blindspotDetection{N}
**WELLE:** 1 abgeschlossen, 2 ausstehend
**NAECHSTER SCHRITT:** Welle 2 (Synthese) starten - liest drafts/{NAME}-blindspot{N}-D*.md

### Drafts (_blindspotDetection{N} - Welle 1)
- [x] .claude/analysis/drafts/{NAME}-blindspot{N}-D01-annahmen-audit.md
- [x] .claude/analysis/drafts/{NAME}-blindspot{N}-D02-monitoring-luecken.md
- [x] .claude/analysis/drafts/{NAME}-blindspot{N}-D03-gegen-fokus.md
- [x] .claude/analysis/drafts/{NAME}-blindspot{N}-D04-dead-end-analyse.md
- [x] .claude/analysis/drafts/{NAME}-blindspot{N}-D05-alternative-perspektive.md
```

**NACH dem Manifest-Update kann /compact ausgefuehrt werden.**

---

## Welle 2: Synthese (DU, Hauptagent)

### Voraussetzung (bei hard)

Lies ALLE Dateien in `.claude/analysis/drafts/{NAME}-blindspot{N}-D*.md`

Falls nicht vorhanden → FEHLER: "Welle 1 nicht abgeschlossen."

### Dein Auftrag

Erstelle das BLINDSPOT-Dokument mit 5 Pflicht-Sektionen.

**CANARY-PROBE-REGELN (Kap. 2.4):**
- Maximum 7 Probes pro Durchgang
- Mindestens 1 Probe AUSSERHALB des aktuellen Fokus-Bereichs (W18, Confirmation Bias)
- Probes sind TEMPORAER (muessen nach Nutzung in eigenem _SC_implement-Durchgang entfernt werden)
- Infrastruktur-Probes (Config, Env-Vars, Compose) GLEICHBERECHTIGT mit Code-Probes

**MENSCH-IN-THE-LOOP (W15, PFLICHT):**
Nach Erstellung des Probe-Plans: User-Bestaetigung einholen.
"Folgende {N} Canary Probes sind geplant. Einverstanden? (J/N/Anpassung)"

### Blindspot-Dokument Struktur

**Pfad**: `.claude/analysis/synthese/{NAME}-BLINDSPOT{N}.md`

```markdown
---
name: {NAME}
phase: blindspot{N}
wave: synthese
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: Hauptagent
date: {YYYY-MM-DD}
reads: models/{NAME}_Model.md, synthese/{NAME}-ANALYSE{CYCLE}.md, synthese/{NAME}-ERGEBNIS*.md
trigger: T{x}
status: final
---

# Blind-Spot-Detection: {NAME} (BSD {N})

**Datum:** YYYY-MM-DD
**Trigger:** T{x} ({Beschreibung})
**Model-Basis:** {NAME}_Model.md v{X.Y}
**Stagnations-Zaehler:** {N}
**BSD-Nummer in Stagnationsphase:** {1 oder 2 von max 2, IR-4}

## 1. Annahmen-Audit

Welche Annahmen sind aktuell als "gegeben" angenommen aber nicht explizit bewiesen?

| # | Annahme | Basis (W{n} / implizit) | Zuletzt geprueft | Risiko |
|---|---------|------------------------|-------------------|--------|
| A1 | ... | W{n} / stillschweigend | Loop {X} / nie | hoch/mittel/niedrig |

**Stillschweigende Annahmen** (nicht im Model, aber im Verhalten sichtbar):
- ...

## 2. Monitoring-Luecken

Wo fehlt Logging, Visibility oder diagnostischer Zugang?

| # | Bereich | Was fehlt | Typ (Code/Infra) | Prioritaet |
|---|---------|-----------|------------------|------------|
| M1 | ... | ... | Code / Infra | hoch/mittel/niedrig |

## 3. Canary-Probe-Plan

**Max 7 Probes. Min 1 AUSSERHALB aktueller Fokus (W18).**

| # | Probe | Typ | Im Fokus? | Was testet? | PASS/FAIL |
|---|-------|-----|-----------|-------------|-----------|
| P1 | ... | Code/Infra | JA/NEIN | {Annahme} | {Kriterium} |

**Probes AUSSERHALB Fokus ({N} von min. 1):**
- P{x}: {Beschreibung} — testet Annahme jenseits des aktuellen Suchraums

**HINWEIS:** Probes sind TEMPORAER. Nach Auswertung muessen sie in einem
eigenen _SC_implement-Durchgang entfernt werden.

**User-Bestaetigung erforderlich:** [ ] Einverstanden / [ ] Anpassung gewuenscht

## 4. Dead-End-Liste

Bereiche die NICHT WEITER verfolgt werden sollten:

| # | Bereich | Grund | Evidenz |
|---|---------|-------|---------|
| DE1 | ... | ... | ERGEBNIS{K}, W{n} |

## 5. Empfohlener naechster Schritt

| Option | Beschreibung | Voraussetzung |
|--------|-------------|---------------|
| A | Probes implementieren (/_SC_implement) | User bestaetigt Plan |
| B | Fokus-Wechsel (/_SC_observe mit anderem TC) | Dead-Ends bestaetigt |
| C | Zurueck in Hauptzyklus (/_SC_hypothese) | BSD lieferte keine neuen Erkenntnisse |

**Empfehlung:** {A/B/C} weil {Begruendung}

## Referenzen
| Quelle | Typ |
|--------|-----|
| {NAME}_Model.md | Model (alle W{n}) |
| {NAME}-ANALYSE{CYCLE}.md | Letzte Analyse (Trigger T{x}) |
| {NAME}-ERGEBNIS*.md | Alle Ergebnisse (Muster-Analyse) |
```

### Nach Welle 2: Manifest finalisieren

```markdown
**PHASE:** _blindspotDetection{N} abgeschlossen
**NAECHSTER SCHRITT:** User prueft Canary-Probe-Plan, dann /_SC_implement (Probes) oder /_SC_hypothese

### Blind-Spot-Detection - {Datum}
- [x] .claude/analysis/synthese/{NAME}-BLINDSPOT{N}.md
- [x] Trigger: T{x} ({Beschreibung})
- [x] Probes: {N} geplant ({M} im Fokus, {K} ausserhalb)
- [x] Dead-Ends: {N} identifiziert
- [ ] User-Bestaetigung: AUSSTEHEND
```

---

## Qualitaetskriterien

- Annahmen-Audit: Alle aktiven W{n} auf Evidenz-Basis geprueft
- Monitoring-Luecken: Infrastruktur-Probes gleichberechtigt mit Code-Probes
- Canary-Probe-Plan: Max 7 Probes, min 1 AUSSERHALB aktueller Fokus (W18)
- Probes-Definition: Typ, was testet, PASS/FAIL-Kriterium pro Probe
- Probes als TEMPORAER markiert (eigener _SC_implement-Durchgang zum Entfernen)
- Dead-End-Liste: Begrenzt auf evidenzbasierte Sackgassen
- Mensch-in-the-Loop: User-Bestaetigung fuer Probe-Platzierung (W15)
- IR-3 beachtet: BSD-Zyklus explizit als "nicht fuer Stagnations-Zaehler" dokumentiert
- IR-4 beachtet: Max 2 BSD pro Stagnationsphase geprueft
- Keine Hypothesen — nur Annahmen-Pruefung und Probe-Planung

---

## Naechster Schritt

User prueft Canary-Probe-Plan, dann:
- `/_SC_implement` (Canary Probes einbauen) — falls Probes bestaetigt
- `/_SC_hypothese` — falls BSD keine neuen Erkenntnisse lieferte
- `/_SC_observe` — falls Dead-Ends zu Fokus-Wechsel fuehren

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_blindspotDetection abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
