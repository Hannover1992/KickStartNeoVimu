# /_SC_ergebnis

Du sammelst Rohdaten, strukturierst sie und fuehrst MECHANISCHE ABLEITUNGEN durch.
Dies ist die NIEDRIG-KOGNITIVE Phase: Sammeln, Strukturieren, Formeln anwenden.
Interpretation macht /_SC_observe, Model-Update macht /_SC_modelMaintain im naechsten Zyklus.
OPTIONAL: Skip wenn Ergebnisse offensichtlich (Build OK/FAIL, Test passed/failed).

## Aufruf

```
/_SC_ergebnis [easy|normal|hard]
```

Default ohne Parameter: **easy**

---

## DUAL-MODE: Solo vs. Wellen-Worker

Dieses Command kann in zwei Modi laufen:

**SOLO-MODUS** (User ruft direkt auf: `/_SC_ergebnis [easy|normal|hard]`)
- easy: 1 Agent (DU) sammelt ALLE Quellen sequentiell, fuehrt alle Schritte (0-5) aus
- normal/hard: 1 Agent (DU) sammelt alle Quellen sequentiell (kein paralleles Spawning)
- Alle Schritte (0-5) werden von dir ausgefuehrt

**WELLEN-WORKER-MODUS** (Team Lead hat Task erstellt, Task-Beschreibung enthaelt "Welle X:")
- Lies die Task-Beschreibung via TaskGet um deinen Modus zu erkennen
- "Welle 1: Datensammlung, Sammler-ID: DS{NN}, Quellen: {quellen-liste}"
  → Sammle NUR die zugewiesenen Quellen
  → Schreibe: `.claude/analysis/synthese/{NAME}-DATA{CYCLE}-DS{NN}.md`
  → Kein Spawning. Kein Manifest-Update. SendMessage an Team Lead wenn fertig.
- "Welle 2: Synthese + SRS"
  → Lies ALLE `.claude/analysis/synthese/{NAME}-DATA{CYCLE}-DS*.md`
  → Konsolidiere Rohdaten, berechne SRS, Widerlegungs-Marker, Stagnation
  → Schreibe: `.claude/analysis/synthese/{NAME}-ERGEBNIS{CYCLE}.md`
  → Aktualisiere Manifest, sende SendMessage an Team Lead

**Erkennung:** Kein Wellen-Hinweis in Task-Beschreibung → Solo-Modus.

---

## VERTRAG (Pflicht-I/O)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_SC_ergebnis [easy|normal|hard]                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  LIEST (Input) - PFLICHT:                                                ║
║    1. .claude/analysis/_manifest.md                                      ║
║    2. .claude/analysis/synthese/{NAME}-HYPOTHESEN.md                     ║
║       ◄── Erwartete Ergebnisse + Falsifizierungskriterien                ║
║    3. Logs, Container-Status, Test-Output, User-Feedback                 ║
║    4. .claude/crumbs/{NAME}_crumbs.md (Crumbs aus A-Phase, fuer Kontext)║
║                                                                          ║
║  LIEST (Input) - NEU ab Cycle 2 (PC2):                                   ║
║    5. .claude/models/{NAME}_Model.md  ◄── DATENBANK-MODUS (nur Listen)  ║
║       → W{n}-Status zaehlen (D2)                                         ║
║       → Offene-Bereiche-Liste lesen (D1, Kap. 6a)                       ║
║       → TC-Liste / Model-Topologie lesen (D4)                            ║
║    6. Vorheriges ERGEBNIS-Dokument  ◄── SRS-VORHER, Stagnations-Zaehler ║
║                                                                          ║
║  DATENBANK-MODUS (W29, Kap. 3.4):                                       ║
║    _SC_ergebnis liest das Model NUR als Datenbank:                      ║
║    → Extrahiert NUMERISCHE WERTE aus VORDEFINIERTEN LISTEN               ║
║    → Liest KEINE Prosa, KEINE Analyse-Befunde, KEINE Hypothesen         ║
║    → Jeder Lesezugriff muss ZAEHLEN oder ABLESEN sein                   ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. .claude/analysis/synthese/{NAME}-ERGEBNIS{CYCLE}.md                ║
║       → Strukturierte Rohdaten                                           ║
║       → SRS-Score VORHER/NACHHER (ab Cycle 2, PC2/HO)                   ║
║       → Widerlegungs-Marker (VERSCH/HO)                                 ║
║       → Stagnations-Check (VERSCH/HO)                                   ║
║    2. .claude/analysis/_manifest.md (aktualisieren)                      ║
║       → inkl. Stagnations-Zaehler Update                                 ║
║                                                                          ║
║  SCHREIBT (Output) - WELLEN-WORKER-MODUS Welle 1:                       ║
║    .claude/analysis/synthese/{NAME}-DATA{CYCLE}-DS{NN}.md               ║
║    → Rohdaten einer zugewiesenen Quellen-Gruppe                          ║
║    → YAML-Frontmatter: name, phase, wave=datensammlung, agent=DS{NN},   ║
║      quellen, date, status=final                                         ║
║                                                                          ║
║  SCHREIBT NICHT:                                                         ║
║    ✗ KEIN Model-Update (macht /_SC_modelMaintain)                        ║
║    ✗ KEINE Interpretation (macht /_SC_observe)                           ║
║    ✗ KEINE Schlussfolgerungen                                            ║
║    ✗ KEINE Battle-Royale-BEWERTUNG (macht /_SC_qualityGate)              ║
║    ✗ Im WORKER-MODUS: Welle-1-Agents schreiben KEIN Manifest-Update      ║
║                                                                          ║
║  DREI-KATEGORIEN-REGEL (H2, Kap. 3.4):                                  ║
║    ┌──────────────────────┬─────────────────────┬──────────────────────┐ ║
║    │ ROHDATEN             │ MECH. ABLEITUNG      │ INTERPRETATION       │ ║
║    │ Sammeln, zaehlen,    │ Formeln anwenden,    │ **VERBOTEN**         │ ║
║    │ woertlich zitieren   │ boolesche Ausdruecke,│ Gehoert in           │ ║
║    │                      │ Zaehler fuehren      │ /_SC_observe           │ ║
║    ├──────────────────────┼─────────────────────┼──────────────────────┤ ║
║    │ Kann ein Skript das  │ Kann ein Skript das  │ 2 Ausfuehrer =       │ ║
║    │ OHNE Kontext?        │ MIT fester Regel?    │ verschiedene Erg.?   │ ║
║    │ → JA = erlaubt       │ → JA = erlaubt       │ → JA = VERBOTEN      │ ║
║    └──────────────────────┴─────────────────────┴──────────────────────┘ ║
║                                                                          ║
║  3-TUPEL POSITION:                                                       ║
║    [_SC_implement] ──▶ [_SC_ergebnis] ──▶ [_SC_observe] (neuer Zyklus)  ║
║    Sammelt Rohdaten + mech. Ableitungen fuer _SC_observe.                   ║
║    OPTIONAL: Skip wenn Ergebnisse offensichtlich.                        ║
║                                                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: Manifest + Inputs lesen

**IMMER als Erstes:**

1. Lies `.claude/analysis/_manifest.md`
   - Ermittle den aktuellen {NAME}
   - Lies **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus der System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=sonnet)`
   - Lies **STAGNATION** Zaehler (falls vorhanden)
2. Lies `.claude/analysis/synthese/{NAME}-HYPOTHESEN.md`
   - Lies erwartete Ergebnisse und Falsifizierungskriterien
   - Lies Verifikations-Kriterium (V1-V5) und Verifikations-Anleitung
   - Diese dienen als CHECKLISTE fuer die Datensammlung
3. **Ab Cycle 2 (PC2):** Lies Model im DATENBANK-MODUS
   - **Bei Model-Split:** Lies `.claude/models/{NAME}_Model-Topologie.md` zuerst
     → Identifiziere FOKUS-Teilmodel → Lies `.claude/models/{NAME}_{TC}_Model.md`
   - **Ohne Split:** Lies `.claude/models/{NAME}_Model.md`
   - ZAEHLE aktive W{n} (Status=AKTIV) → D2
   - ZAEHLE Offene Hypothesen-Bereiche (Kap. 6a) → D1
   - ZAEHLE betroffene Dateien (aus HYPOTHESEN.md) → D3
   - ZAEHLE Aktive TCs (Kap. 6a oder Model-Topologie) → D4
   - **Bei Split:** SRS pro FOKUS-Teilmodel (D4_teil = 1)
   - **LIES KEINE PROSA. NUR LISTEN ABZAEHLEN.**
4. **Ab Cycle 2 (PC2):** Lies vorheriges `.claude/analysis/synthese/{NAME}-ERGEBNIS*.md`
   - Lies SRS-VORHER-Wert
   - Lies Stagnations-Zaehler-Stand
5. **Auto-Increment: Bestimme naechste Ergebnis-Nummer {CYCLE}**
   - Scanne `.claude/analysis/synthese/{NAME}-ERGEBNIS*.md` auf Disk
   - `{CYCLE}` = hoechste gefundene Nummer + 1
   - Suffix-Konvention: `""` fuer 1, `"2"` fuer 2, etc.

**Fallback bei leerem Kap. 6a (Q19):**
Falls "Offene Hypothesen-Bereiche" in Kap. 6a noch leer ist (z.B. Cycle 1→2 Uebergang):
D1 als Dreipunkt-Schaetzung (min/mid/max) mit [PROVISORISCH]-Marker dokumentieren.

---

## Kontext

```
    /_model ──▶ /_SC_observe ──▶ /_SC_modelMaintain ──▶ /_SC_qualityGate ──▶ /_SC_hypothese ──▶ /_SC_implement ──▶ [/_SC_ergebnis]
                    ▲                                              │
                    └──────────────────────────────────────────────┘
                         (SRS + Rohdaten + Mech.Abl. fuer _SC_observe)

    INPUT:  {NAME}-HYPOTHESEN.md (erwartete Ergebnisse, Verif.-Kriterium)
            {NAME}_Model.md (DATENBANK-MODUS: D1-D4 zaehlen, ab Cycle 2)
            Vorheriges ERGEBNIS (SRS-VORHER, ab Cycle 2)
            Logs, Container, Tests, User-Feedback
    OUTPUT: {NAME}-ERGEBNIS{CYCLE}.md (Rohdaten + Mech.Abl., KEINE Interpr.)
```

---

## Schritt 1: Rohdaten sammeln (PROAKTIV!)

Du MUSST selbst Informationen sammeln - nicht nur auf User warten!

| Quelle | Befehl | Was suchen |
|--------|--------|------------|
| Container | `docker ps` | Alle healthy? |
| Service-Logs | `docker logs {service}` | Relevante Marker |
| Weitere Logs | `docker logs {service}` | Fehler, Warnungen |
| Tests | Test-Runner | Pass/Fail pro Test |
| User | Fragen | Beobachtungen |

### Sensitive Daten beachten

- Tokens NICHT vollstaendig loggen
- Nur die ersten/letzten Zeichen zeigen

### Verifikations-Anleitung ausfuehren

Falls HYPOTHESEN.md eine Verifikations-Anleitung (V1-V5) enthaelt:
1. Fuehre die 3-5 Test-Schritte EXAKT wie beschrieben aus
2. Dokumentiere den exakten Output pro Schritt
3. Notiere PASS/FAIL als BEOBACHTUNG (keine Interpretation)

---

## Schritt 2: Mechanische Ableitungen (ab Cycle 2)

**DREI-KATEGORIEN-REGEL:** Alles in diesem Schritt muss den Test bestehen:
"Koennen zwei Ausfuehrer verschiedene Ergebnisse bekommen?" → Falls JA = VERBOTEN, gehoert in _SC_observe.

### 2a: Battle-Royale-Score berechnen (PC2/HO)

**Override:** HARD-OVERRIDE (HO-11). Bei Override: Begruendung dokumentieren.

```
SRS = (D1 * 3) + (D2 * 1) + (D3 * 0.5) + (D4 * 5)

D1: Offene Hypothesen-Bereiche    (aus Model Kap. 6a, NUR ZAEHLEN)
D2: Aktive W{n}                   (aus Model W{n}-Liste, Status=AKTIV, NUR ZAEHLEN)
D3: Betroffene Dateien             (aus HYPOTHESEN.md geplante Dateien, NUR ZAEHLEN)
D4: Aktive Technologie-Concerns    (aus Model Kap. 6a / Model-Topologie, NUR ZAEHLEN)
```

**Dokumentation:**

| Dimension | VORHER (aus letztem ERGEBNIS) | NACHHER (jetzt gezaehlt) | Delta |
|-----------|-------------------------------|--------------------------|-------|
| D1 (Bereiche) | {Zahl} | {Zahl} | {+/-} |
| D2 (Aktive W{n}) | {Zahl} | {Zahl} | {+/-} |
| D3 (Dateien) | {Zahl} | {Zahl} | {+/-} |
| D4 (TCs) | {Zahl} | {Zahl} | {+/-} |
| **SRS** | **{Zahl}** | **{Zahl}** | **{+/- %}** |

**Eliminierte / Verbliebene / Neue Bereiche:** NUR AUFLISTEN, NICHT BEWERTEN.

**WICHTIG:** Die SRS-BEWERTUNG (GESCHRUMPFT/STAGNIERT/GEWACHSEN) macht /_SC_qualityGate!
Hier wird NUR GEMESSEN.

### 2b: Widerlegungs-Marker setzen (VERSCH/HO)

**Override:** HARD-OVERRIDE (HO-12). Bei Override: Begruendung dokumentieren.

Fuer JEDE aktive W{n} die im aktuellen Zyklus getestet/beruehrt wurde, setze einen Marker:

| Stufe | Bedeutung | Wann setzen |
|-------|-----------|-------------|
| **DIREKT WIDERSPRUCHLICH** | Beobachtung widerspricht W{n} direkt | Rohdaten zeigen klaren Widerspruch |
| **ZUR PRUEFUNG** | Unklar ob W{n} noch gilt (Default) | Keine direkte Bestaetigung gefunden |
| **KONSISTENT** | Beobachtung stuetzt W{n} | Rohdaten bestaetigen W{n} ausdruecklich |

**WICHTIG:** Dies sind BEOBACHTUNGEN, keine Interpretationen.
"Rohdaten X widersprechen W{n}" ist eine Beobachtung.
"W{n} ist falsch weil..." ist eine Interpretation (→ VERBOTEN).

### 2c: Stagnations-Check (VERSCH/HO)

**Override:** HARD-OVERRIDE (HO-13). Bei Override: Begruendung dokumentieren.

Bestimme den Fortschritts-Typ dieses Zyklus:

```
STARK (Zaehler-Reset auf 0.0):
  - Widerlegung einer aktiven W{n} (DIREKT WIDERSPRUCHLICH Marker gesetzt)
  - Eliminierung eines Hypothesen-Bereichs (Battle-Royale)
  - SRS-Reduktion >= 5% gegenueber Vorzyklus
  - Fokus-Wechsel auf anderes Teilmodel (bei Model-Split)

SCHWACH (Zaehler += 0.5):
  - Neue W{n} hinzugefuegt OHNE SRS-Reduktion >= 5%
  - SRS-Reduktion < 5% (marginal)
  - Diagnostische Erkenntnisse (z.B. Canary-Probe-Ergebnisse)

KEINER (Zaehler += 1.0):
  - Keine neue W{n}, keine Widerlegung, kein SRS-Delta
  - Loop war rein reproduktiv (gescheiterter Build ohne neue Info)
```

**Loop-Definition [PROVISORISCH, W36]:** 1 Loop = 1 vollstaendiger Phasen-Durchlauf
(\_SC_observe + \_SC_modelMaintain + \_SC_qualityGate + \_SC_hypothese + \_SC_implement + \_SC_ergebnis). Interne Wellen (Drafter+Synthese)
zaehlen als TEIL eines Loops, nicht als separate Loops.

**Zaehler-Berechnung:**
```
NEUER ZAEHLER = {
  STARK:  0.0
  SCHWACH: ALTER ZAEHLER + 0.5
  KEINER:  ALTER ZAEHLER + 1.0
}
```

**Schwellenwerte dokumentieren (NUR FAKTEN, _SC_qualityGate entscheidet Massnahme):**

| Zaehler | Status |
|---------|--------|
| < 3.0 | NORMAL |
| >= 3.0 | SCHWELLE WARNUNG ERREICHT |
| >= 5.0 | SCHWELLE PFLICHT ERREICHT |
| >= 7.0 | SCHWELLE ABORT ERREICHT |

---

## Schwierigkeits-Parameter

| Schwierigkeit | Wellen-Worker-Modus (Team Lead steuert) | Solo-Modus (DU machst alles) |
|---------------|----------------------------------------|------------------------------|
| **easy** | 1 Task (Welle 1+2 kombiniert, 1 Agent) | 1 Agent (DU, sequentiell) |
| **normal** | 5 Sammler-Tasks (DS01-DS05) + 1 Synthese-Task | 1 Agent (DU, sequentiell) |
| **hard** | 9 Sammler-Tasks (DS01-DS09) + 1 Synthese-Task | 1 Agent (DU, sequentiell) |

**Sammler-Fokus-Bereiche (Wellen-Worker-Modus Welle 1):**

| Sammler | Quellen | Aufgabe |
|---------|---------|---------|
| DS01 | Container + Service-Logs | docker ps, docker logs (main services) |
| DS02 | Test-Output + Build | Test-Runner, Build-Logs, Code-Coverage |
| DS03 | Browser/UI + User | Browser-Tests, User-Feedback, manuelle Pruefung |
| DS04-DS09 | (bei hard) | Weitere spezialisierte Quellen (Datenbankabfragen, externe APIs, etc.) |

**Modell-Downgrade (BEIBEHALTEN - niedrig-kognitiv, Rohdaten-Sammlung):**

| System-Model | Sammler (Welle 1) | Synthese-Agent (Welle 2 / Solo) |
|-------------|-------------------|--------------------------------|
| opus | sonnet | sonnet |
| sonnet | haiku | sonnet |
| haiku | haiku | haiku |

**Begruendung Downgrade:** `_SC_ergebnis` ist explizit NIEDRIG-KOGNITIV (docker ps parsen,
Zahlen abzaehlen, SRS-Formel anwenden). Hochkognitive Interpretation bleibt `_SC_observe`
und `_SC_modelMaintain` (die opus behalten). Sonnet/Haiku reichen fuer mechanische Sammlung.

---

## Schritt 2.5: Wellen-Worker-Modus Welle 1 (Datensammlung)

**NUR ausfuehren wenn Task-Beschreibung "Welle 1: Datensammlung" enthaelt.**

Falls du als Sammler DS{NN} vom Team Lead gespawnt wurdest:

1. Lies die Task-Beschreibung (TaskGet) um deine Quellen-Zuweisung zu erkennen
2. Sammle NUR die dir zugewiesenen Quellen (aus Task-Beschreibung)
3. Schreibe `.claude/analysis/synthese/{NAME}-DATA{CYCLE}-DS{NN}.md`:

```markdown
---
name: {NAME}
phase: ergebnis{CYCLE}
wave: datensammlung
agent: DS{NN}
quellen: {quellen-liste, z.B. "Container, Service-Logs"}
date: {YYYY-MM-DD}
status: final
---

# Daten DS{NN}: {Quellen-Beschreibung}

## Quelle 1: {Quell-Typ}
{Raw-Daten, woertlich, unkommentiert}

## Quelle 2: {Quell-Typ}
{Raw-Daten}
```

4. **Kein** Manifest-Update (macht Welle-2-Agent oder Team Lead)
5. **Kein** Spawning von Sub-Agents
6. TaskUpdate completed
7. SendMessage an Team Lead: "DS{NN} fertig: DATA{CYCLE}-DS{NN}.md ({Zusammenfassung})"

**Warte nicht auf andere Sammler.** Deine Aufgabe ist abgeschlossen.

Falls Task "Welle 2: Synthese + SRS" enthaelt:
1. Lies ALLE `.claude/analysis/synthese/{NAME}-DATA{CYCLE}-DS*.md`
2. Konsolidiere Rohdaten in Schritt-3-Format
3. Weiter mit Schritt 2a-2c (SRS, Widerlegungs-Marker, Stagnation)
4. Schreibe ERGEBNIS{CYCLE}.md (Schritt 3)
5. Aktualisiere Manifest (Schritt 5)

---

## Schritt 3: Ergebnis-Dokument schreiben

**Pfad**: `.claude/analysis/synthese/{NAME}-ERGEBNIS{CYCLE}.md`

```markdown
---
name: {NAME}
phase: ergebnis{CYCLE}
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: Hauptagent
date: {YYYY-MM-DD}
reads: synthese/{NAME}-HYPOTHESEN.md, models/{NAME}_Model.md (DB-Modus)
status: final
---

# Ergebnis: {NAME} (Zyklus {CYCLE})

**Datum:** YYYY-MM-DD
**Hypothese-Basis:** {NAME}-HYPOTHESEN.md
**Verifikations-Typ:** V{1-5}

## Rohdaten

### Quelle 1: Container-Status
{docker ps Output, strukturiert}

### Quelle 2: Service-Logs
{Relevante Log-Auszuege, strukturiert}

### Quelle 3: Test-Output / Verifikations-Anleitung
{Test-Ergebnisse, exakter Output pro Verifikations-Schritt}

### Quelle 4: Browser-Beobachtung
{Screenshot-Beschreibung, sichtbares Verhalten}

### Quelle 5: User-Feedback
{Falls vorhanden}

## Zusammenfassung (NUR Fakten, KEINE Interpretation)

| Test/Kriterium | Ergebnis (Pass/Fail) | Rohdaten-Referenz |
|----------------|---------------------|-------------------|
| {aus HYPOTHESEN.md} | PASS/FAIL | Quelle {N} |

## Battle-Royale-Score (PC2/HO, ab Cycle 2)

| Dimension | VORHER | NACHHER | Delta |
|-----------|--------|---------|-------|
| D1 (Offene Bereiche) | {Zahl} | {Zahl} | {+/-} |
| D2 (Aktive W{n}) | {Zahl} | {Zahl} | {+/-} |
| D3 (Betroffene Dateien) | {Zahl} | {Zahl} | {+/-} |
| D4 (Aktive TCs) | {Zahl} | {Zahl} | {+/-} |
| **SRS** | **{Zahl}** | **{Zahl}** | **{+/- %}** |

Eliminierte Bereiche: {Liste oder "keine"}
Verbliebene Bereiche: {Liste}
Neue Bereiche: {Liste oder "keine"}

(BEWERTUNG GESCHRUMPFT/STAGNIERT/GEWACHSEN macht /_SC_qualityGate)

## Widerlegungs-Marker (VERSCH/HO)

| W{n} | Marker | Beobachtung |
|------|--------|-------------|
| W{x} | KONSISTENT / ZUR PRUEFUNG / DIREKT WIDERSPRUCHLICH | {Rohdaten-Referenz} |

## Stagnations-Check (VERSCH/HO)

**Fortschritts-Typ dieses Zyklus:** STARK / SCHWACH / KEINER
**Begruendung:** {Welches Kriterium erfuellt}
**Zaehler VORHER:** {N}
**Zaehler NACHHER:** {N ± Delta}
**Schwelle:** NORMAL / WARNUNG / PFLICHT / ABORT

(MASSNAHMEN-ENTSCHEIDUNG bei Schwelle macht /_SC_qualityGate)

## W{n}-Abdeckung (v2.1, mechanisch)

| Feld | Wert |
|------|------|
| AKTIV gesamt | {N} |
| BESTAETIGT | {N} ({%}) |
| WIDERLEGT | {N} ({%}) |
| OFFEN | {N} ({%}) |
| Abdeckung | {%} |

(INTERPRETATION ABGESCHLOSSEN/FAST_FERTIG/OFFEN macht /_SC_qualityGate)

## Referenzen
| Quelle | Typ |
|--------|-----|
| docker ps | Container-Status |
| docker logs {service} | Service-Logs |
| {NAME}_Model.md (DB-Modus) | D1-D4 Zaehlung |
| Vorheriges ERGEBNIS | SRS-VORHER |
```

**WICHTIG:**
- NUR Fakten und mechanische Ableitungen. KEINE Schlussfolgerungen.
- KEINE "Hypothese bestaetigt/widerlegt" — das entscheidet /_SC_observe.
- KEIN Model-Update — das macht /_SC_modelMaintain.
- Pass/Fail ist eine BEOBACHTUNG, keine Interpretation.
- SRS-Score ist eine MECHANISCHE ABLEITUNG (Formel), keine Interpretation.
- Widerlegungs-Marker sind BEOBACHTUNGEN (Fakten-Vergleich), keine Interpretation.
- Stagnations-Typ ist eine MECHANISCHE ABLEITUNG (Regel-Anwendung).

---

## Schritt 3a: W{n}-Abdeckungs-Zaehlung (NEU v2.1, mechanisch)

**Zweck:** Mechanische Zaehlung der W{n}-Abdeckung als Input fuer die
Feature-Abschluss-Erkennung in `/_SC_qualityGate`. Dies ist KEINE Interpretation,
sondern reines Zaehlen (wie SRS-Score).

**Nur ausfuehren wenn:** Model im DATENBANK-MODUS gelesen wurde (ab Cycle 2).

```
W{n}-Abdeckung (mechanisch gezaehlt):
  AKTIV gesamt:      {N} (aus Model, Status=AKTIV)
  BESTAETIGT:        {N} (W{n} mit mindestens 1 KONSISTENT-Marker ueber alle ERGEBNIS-Dateien)
  WIDERLEGT:         {N} (W{n} mit DIREKT WIDERSPRUCHLICH-Marker)
  OFFEN:             {N} (W{n} ohne Marker in irgendeinem ERGEBNIS)
  Abdeckung:         {%} ((BESTAETIGT + WIDERLEGT) / AKTIV * 100)
```

**WICHTIG:** Dies ist eine MECHANISCHE ABLEITUNG (Zaehlen + Division).
Die INTERPRETATION (ABGESCHLOSSEN / FAST_FERTIG / OFFEN) macht `/_SC_qualityGate`.

---

## Schritt 4: Naechsten Schritt bestimmen

```
Rohdaten + Mech. Ableitungen gesammelt
        │
        ▼
   /_SC_observe (IMMER)
   (interpretiert Rohdaten + SRS,
    bewertet BR-Trend,
    Feature-Abschluss-Erkennung (v2.1),
    aktualisiert Model,
    entscheidet ob geloest/weiter/ABORT/finish)
```

**Hinweis:** Die Entscheidung ob "geloest", "neuer Zyklus", "ABORT", "Model Review"
oder "Model-Finish" trifft /_SC_observe — NICHT /_SC_ergebnis.
/_SC_ergebnis liefert die Daten, mech. Ableitungen und W{n}-Zaehlung.

---

## Schritt 5: Manifest finalisieren

```markdown
**PHASE:** _SC_ergebnis{CYCLE} abgeschlossen
**NAECHSTER SCHRITT:** /_SC_observe (interpretiert Rohdaten + SRS, aktualisiert Model)

**STAGNATION:** {NEUER ZAEHLER}
**LETZTER STARKER FORTSCHRITT:** Loop {X}, Typ: {Beschreibung}
**LETZTER SCHWACHER FORTSCHRITT:** Loop {Y}, Typ: {Beschreibung}

### Ergebnis - {Datum}
- [x] .claude/analysis/synthese/{NAME}-ERGEBNIS{CYCLE}.md (Rohdaten + Mech.Abl.)
- [x] SRS-Score: {VORHER} → {NACHHER} ({+/- %}%)
- [x] Stagnation: {ALTER ZAEHLER} → {NEUER ZAEHLER} ({FORTSCHRITTS-TYP})
- [x] W{n}-Abdeckung: {%}% ({BESTAETIGT}B + {WIDERLEGT}W / {AKTIV} gesamt)
```

---

## Qualitaetskriterien

- Alle verfuegbaren Quellen geprueft
- Verifikations-Anleitung exakt ausgefuehrt (falls vorhanden)
- Rohdaten objektiv dokumentiert (NUR Fakten)
- Sensitive Infos maskiert
- KEINE Interpretation, KEINE Schlussfolgerungen
- KEIN Model-Update (das macht /_SC_modelMaintain)
- Pass/Fail pro Test als Beobachtung dokumentiert
- Drei-Kategorien-Regel eingehalten (Rohdaten + Mech.Abl., KEINE Interpretation)
- SRS-Score berechnet mit Formel (ab Cycle 2, PC2/HO)
- Widerlegungs-Marker gesetzt als Beobachtung (VERSCH/HO)
- Stagnations-Check durchgefuehrt (VERSCH/HO)
- Manifest mit Stagnations-Zaehler aktualisiert
- **NEU (v2.1):** W{n}-Abdeckung mechanisch gezaehlt (ab Cycle 2)
- **NEU (v2.1):** Abdeckungs-Tabelle im ERGEBNIS-Dokument dokumentiert

---

## Naechster Schritt

Nach Abschluss: `/_SC_observe` ausfuehren (interpretiert Rohdaten + SRS, aktualisiert Model)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_SC_ergebnis abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
