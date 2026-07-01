# /_I_requirementCheck — Pre-Implementation Anforderungs-Verifikation

```yaml
status: active
version: 1.0.0
created: 2026-03-12
op: ImplementationPipeline
phase: Blueprint
type: building-block
chain_position: post-architect
team_based: false
```

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_requirementCheck {NAME} [--stufe {N}] [--kurskorrekt] ║
╠══════════════════════════════════════════════════════════════════════╣
║  ACTOR: DU direkt (kein Worker-Spawn). Verification-only.           ║
║                                                                      ║
║  ZWECK:                                                              ║
║    Pre-Implementation Sanity Gate.                                   ║
║    Prueft ob jedes geplante DB-Feld durch eine explizite            ║
║    fachliche Anforderung gedeckt ist.                               ║
║    Prueft ob der geplante Architektur-Ansatz mit dem JIRA            ║
║    AK-Text uebereinstimmt.                                          ║
║                                                                      ║
║  PIPELINE-POSITION:                                                  ║
║    /_I_cleanCodeArchitect → **/_I_requirementCheck** → /_I_testSearch║
║                                                                      ║
║  LIEST (PFLICHT):                                                    ║
║    {VAULT}/Task.md                      (AK-Text, JIRA-Referenz)   ║
║    {VAULT}/_manifest.md        (Feature-Name, Phase)       ║
║    .claude/analysis/synthese/{NAME}-ARCHITECT*.md  (Blueprint)      ║
║    .claude/specs/{NAME}_Spec.md         (falls vorhanden)           ║
║    .claude/models/{NAME}_Model.md       (falls vorhanden)           ║
║    Anforderungsquelle (aus Task.md abgeleitet, z.B. EM-Tabelle,    ║
║      Wiki-Datei, JIRA AK woertlich)                                 ║
║                                                                      ║
║  LIEST (OPTIONAL):                                                   ║
║    .claude/crumbs/{NAME}_crumbs.md      (Q-Flaggen, Ambiguitaeten) ║
║    .claude/evidence/*.md               (constraint-Evidence)        ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/analysis/synthese/{NAME}-REQCHECK-S{N}.md               ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    NIE Code aendern                                                  ║
║    NIE Blueprint aendern                                             ║
║    BEI BLOCKER: Pipeline stoppt — kein codeAtomic starten          ║
║    BEI WARNING: Pipeline laeuft weiter, Warnung dokumentiert        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_I_requirementCheck {NAME} [--stufe {N}] [--kurskorrekt]
```

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `NAME` | (PFLICHT) | Feature-Name (z.B. DCSRE-882) |
| `--stufe` | 1 | I-Pipeline Stufe (bestimmt welchen ARCHITECT zu lesen) |
| `--kurskorrekt` | - | Kurskorrektur-Modus: neue Richtung gegen AK-Text verifizieren |

**Beispiele:**
```
/_I_requirementCheck DCSRE-882
/_I_requirementCheck DCSRE-882 --stufe 3
/_I_requirementCheck DCSRE-882 --kurskorrekt
```

---

## ABLAUF

### Schritt 0: Kontext laden

```
1. Lies Task.md → extrahiere AK-Liste (MUSS/SOLL/KANN Felder)
2. Lies ARCHITECT*.md → extrahiere alle neuen DB-Felder aus Slice-Tabelle
3. Bestimme Anforderungsquelle:
   - Task.md referenziert Spec → Spec lesen (z.B. EM0012-Tabelle aus Crumbs)
   - Task.md hat AK-Text woertlich → AK-Text als Quelle
   - Kein Spec vorhanden → WARNING "Keine explizite Anforderungsquelle"
4. Wenn --kurskorrekt: lade KURSKORREKTUR-Dokument oder Manifest-Flag
```

### Schritt 1: Feld-Coverage-Matrix aufbauen

Fuer jedes neue DB-Feld das im Blueprint erscheint:

```
a. Suche im Anforderungsdokument (Tabelle, Spec, AK):
   → Grep nach Feldname, Synonymen, verwandten Begriffen
b. Wenn Match: Status = GEDECKT, notiere Zeile/Abschnitt
c. Wenn kein Match: Status = UNGEDECKT
d. Wenn technisch-intern (Infrastruktur-Feld ohne fachliche Bedeutung):
   Status = TECHNISCH (erfordert dokumentierte Begruendung)
```

**Output-Format:**

```markdown
| # | Feld | Anforderungs-Referenz | Quelle | Status |
|---|------|-----------------------|--------|--------|
| 1 | Richtung | "E=Eingang A=Ausgang" | EM0012 Z.3 | GEDECKT |
| 2 | IkEmpfaenger | "IK-Empfaenger" | EM0012 Z.10 | GEDECKT |
| 3 | FileSize | ??? | EM0012 | UNGEDECKT → BLOCKER |
| 4 | DicPackageId | pragmatisch sinnvoll | KURSKORREKTUR §1.2 | TECHNISCH → WARNING |
```

### Schritt 2: BLOCKER-Entscheidung Felder

```
IF mindestens 1 Feld UNGEDECKT:
  → BLOCKER: "Feld {X} nicht in {Anforderungsquelle} gelistet"
  → Pipeline-Status: GEBLOCKT
  → Optionen:
    (a) Feld aus Blueprint entfernen
    (b) Anforderung beim PO klaeren
    (c) Als TECHNISCH mit Begruendung umklassifizieren

IF nur TECHNISCH-Felder ohne Begruendung:
  → WARNING: "Feld {X} technisch-intern, aber ohne dokumentierte Begruendung"
  → Pipeline laeuft weiter, Blueprint-Kommentar erforderlich
```

### Schritt 3: AK-Text-Verifikation

```
1. Lies AK-Text WOERTLICH aus Task.md
2. Fuer jeden Architektur-Ansatz im Blueprint:
   - "Fordert ein AK explizit diesen Ansatz?"
   - "Widerspricht der Ansatz einem AK-Satz?"
3. Beispiel-Pruefung:
   AK3: "Datenbanktabelle wird um Metadaten ergaenzt"
   → DB-Ansatz: GEDECKT
   → JSON-Sidecar-Ansatz: WIDERSPRUCH → BLOCKER
```

### Schritt 4: Ambiguitaets-Pruefung (aus Crumbs)

```
1. Lies crumbs auf Muster: "OFFEN", "unklar", "PO klaeren", "?"
2. Fuer jedes offene Item das ein MUSS-AK betrifft:
   → Status = BLOCKER (Implementierung nicht starten ohne Klaerung)
3. Fuer SOLL/KANN-Items:
   → Status = WARNING + Annahme dokumentieren
```

### Schritt 5: Kurskorrektur-Modus (nur --kurskorrekt)

```
Zusaetzliche 3-Fragen-Pruefung:
  Q1: "Korrigiert die neue Richtung den Fehler der alten Richtung?"
  Q2: "Ist die neue Richtung durch AK-Text abgedeckt?"
  Q3: "Wurde die alte Richtung klar dokumentiert (Warum war sie falsch)?"

Kein Kurskorrektur-Blueprint ohne explizite Antworten auf alle 3 Fragen.
Fehlende Antwort = BLOCKER.
```

### Schritt 6: Report schreiben

**Dateiname:** `{NAME}-REQCHECK-S{N}.md`
**Speicherort:** `.claude/analysis/synthese/`

```markdown
---
feature: '{NAME}'
stufe: {N}
date: {DATE}
status: PASS | WARN | BLOCKED
feld_coverage: {gedeckt}/{total} ({%})
ak_verifikation: {pass}/{total} ({%})
blocker_count: {N}
warning_count: {N}
modus: normal | kurskorrekt
---

# RequirementCheck: {NAME} Stufe {N}

**Datum:** {DATE}
**Status:** {PASS | WARN | BLOCKED}
**Anforderungsquelle:** {Quelle}

## Feld-Coverage-Matrix

{Tabelle aus Schritt 1}

## AK-Text-Verifikation

{Ergebnis pro AK aus Schritt 3}

## Ambiguitaeten

{Findings aus Schritt 4, falls vorhanden}

## Kurskorrektur-Verifikation (falls --kurskorrekt)

{3-Fragen-Antworten aus Schritt 5}

## Entscheidung

{PASS → "Gate bestanden, weiter zu testSearch"}
{WARN → "Gate bestanden mit Warnungen, Dokumentation erforderlich"}
{BLOCKED → "Gate NICHT bestanden. Naechste Schritte: {konkrete Aktionen}"}
```

### Schritt 7: Ergebnis ausgeben

```
/_I_requirementCheck {NAME} Stufe {N}: {STATUS}

Feld-Coverage: {gedeckt}/{total} ({%})
AK-Verifikation: {pass}/{total}
{Falls BLOCKED:}
  BLOCKER:
    - {Blocker 1}
    - {Blocker 2}
  → Pipeline GESTOPPT. Naechste Schritte: {Aktionen}

{Falls WARN:}
  Warnungen:
    - {Warning 1}
  → Pipeline laeuft weiter.

{Falls PASS:}
  → Weiter zu /_I_testSearch --stufe {N}

Report: .claude/analysis/synthese/{NAME}-REQCHECK-S{N}.md
```

---

## BLOCKER vs. WARNING Kriterien

### BLOCKER (Pipeline stoppt)

1. **Feld ohne Anforderungsdeckung:** Neues DB-Feld hat KEINEN Match in der
   Anforderungsquelle. Kein "macht technisch Sinn" — nur explizite fachliche
   Anforderung zaehlt.

2. **Architektur-Ansatz widerspricht AK-Text:** Plan und AK-Text stehen im
   expliziten Widerspruch (z.B. "DB ergaenzen" vs. JSON-Sidecar-Plan).

3. **Mehrdeutige MUSS-Anforderung ohne Klaerung:** MUSS-Feld hat unklare
   Anforderung UND kein Klaerungsnachweis (Evidence oder PO-Bestaetigung).

4. **Kurskorrektur ohne 3-Fragen-Antworten:** Bei --kurskorrekt fehlt
   mindestens eine der 3 Pflicht-Antworten.

### WARNING (Pipeline laeuft weiter)

1. **Technische Felder:** Feld ist nicht in Anforderung gelistet, hat aber
   dokumentierte technische Begruendung (z.B. Infrastruktur-FK).

2. **Mehrdeutige SOLL/KANN-Anforderung:** Optionales Feature mit unklarer
   Anforderung — Annahme muss dokumentiert sein.

3. **Fehlende Anforderungsquelle:** Kein Spec/AK verfuegbar — kein
   Widerspruch, aber auch kein Nachweis.

---

## Integration mit bestehenden Commands

| Command | Beziehung | Reihenfolge |
|---------|-----------|-------------|
| `/_gap` | Komplementaer: _gap prueft OB Items implementiert, requirementCheck prueft ob GEPLANTE Items anforderungsgedeckt sind | _gap (SC-Phase) → requirementCheck (I-Phase) |
| `/_smoothing` | Klammer: requirementCheck = Pre-Check, smoothing = Post-Check | requirementCheck → [Impl] → smoothing |
| `/_I_verify` | requirementCheck stellt sicher dass Felder korrekt gewaehlt, _I_verify prueft SPEC-Traceability | requirementCheck → [Impl] → _I_verify |
| `/_I_cleanCodeArchitect` | Direkte Abhaengigkeit: requirementCheck liest ARCHITECT-Output | cleanCodeArchitect → **requirementCheck** |

---

## Pipeline-Position

```
BLUEPRINT fuer Stufe N:
  1.  /_I_cleanCodeArchitect --stufe N
  1a. /_I_requirementCheck --stufe N    ← DIESES GATE (BLOCKER-faehig)
  2.  /_I_testSearch --stufe N
  3.  /_I_goldDefine --stufe N
  4.  /_I_patternLibrary --stufe N
  5.  /_I_blueprintQG --stufe N
  6.  /_I_cleanCodeSlice --stufe N

KURSKORREKTUR-MODUS:
  [IST-Analyse: Was wurde falsch gebaut?]
  → /_I_requirementCheck --kurskorrekt    ← Neue Richtung gegen AK verifizieren
  [SOLL-Plan: neuer Blueprint]
  → /_I_codeAtomic (Rueckbau + Neubau)
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Task.md fehlt | ABBRUCH: "Keine Aufgabendefinition. requirementCheck braucht AK-Text." |
| ARCHITECT.md fehlt | ABBRUCH: "Kein Blueprint vorhanden. Erst cleanCodeArchitect ausfuehren." |
| Keine Anforderungsquelle identifizierbar | WARNING + User interaktiv fragen |
| Crumbs nicht vorhanden | Schritt 4 (Ambiguitaets-Pruefung) ueberspringen, WARNING |
| --kurskorrekt ohne KURSKORREKTUR-Dokument | ABBRUCH: "Kein Kurskorrektur-Kontext." |

---

## Case Study: DCSRE-882 MetaDaten

**Haette requirementCheck diese Failures verhindert?**

| Failure | Gate-Schritt | Ergebnis | Zeitersparnis |
|---------|-------------|----------|---------------|
| FM-01: FileSize/CheckSum (kein EM0012-Match) | Schritt 1+2: Feld-Coverage | BLOCKER — 2 Felder UNGEDECKT | ~4h Rueckbau |
| FM-04: JSON-Sidecar (widerspricht AK3 "DB ergaenzen") | Schritt 3: AK-Verifikation | BLOCKER — Ansatz vs. AK-Text | ~1 Tag Blueprint-Verwurf |
| Q3 ".jason"-Ambiguitaet | Schritt 4: Ambiguitaets-Pruefung | BLOCKER — MUSS-Feld ohne Klaerung | ~0.5 Tage Verwirrung |

**Gate-Durchlauf:** ~15 Minuten pro Stufe.
**Vermiedener Schaden:** ~5-8h pro Feature mit aehnlichen Mustern.
**Break-even:** Nach 1-2 Features.

---

ARGUMENTS: $ARGUMENTS
