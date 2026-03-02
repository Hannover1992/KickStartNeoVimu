# /_SC_modelMaintain

**Status:** NEU v2.8 (Mermaid-Typ-Qualitaets-Gate Schritt 3b, EC-1/S1_Gate)
**Actor:** MODEL-MAINTAINER
**Zweck:** Model pflegen, GC, Split ausfuehren, Commit-Tracking

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_SC_modelMaintain {NAME} [easy|normal|hard] [--out-of-cycle] ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. _manifest.md                                                       ║
║    2. models/{NAME}_Model.md (MUSS EXISTIEREN)                          ║
║                                                                          ║
║  LIEST (Input) - MODUS-ABHAENGIG:                                       ║
║    In-Cycle (default):                                                   ║
║      3. synthese/{NAME}-OBSERVE{CYCLE}.md (Findings aus _SC_observe)   ║
║      4. synthese/{NAME}-ERGEBNIS{CYCLE}.md (falls Folge-Zyklus)       ║
║    Out-of-Cycle (--out-of-cycle):                                       ║
║      3. git diff {last_sync_commit}..HEAD (Code-Aenderungen als Input) ║
║      4. spec/{NAME}_SPEC.md (optional, fuer Drift-Erkennung)          ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    Model-Update (IMMER):                                                 ║
║      models/{NAME}_Model.md (aktualisiert)                              ║
║      → Neue W{n} / korrigierte W{n} / Version erhoehen                 ║
║      → GC: WIDERLEGT/ELIMINIERT markieren                               ║
║      → Kap. 6a pflegen (Offene Bereiche, Aktive TCs)                   ║
║      → Mermaid-Diagramme pflegen (Schritt 3a, normal+hard)             ║
║      → Mermaid-Anker aktualisieren bei W{n}-Bestaetigung (MA-1..MA-4) ║
║      → w-confirmed Frontmatter-Zaehler bei BESTAETIGT-Markierung       ║
║      → sync.last_sync_commit aktualisieren (IMMER)                     ║
║      → sync.last_sync_date aktualisieren (IMMER)                       ║
║                                                                          ║
║    Model-Split (bei PFLICHT-Trigger):                                   ║
║      models/{NAME}_Model-Topologie.md                                   ║
║      models/{NAME}_{TC}_Model.md (pro Teilmodel)                        ║
║                                                                          ║
║  SCHREIBT (Output) - OPTIONAL:                                           ║
║    _parking-lot.md (APPEND, falls Incidental Findings)                  ║
║                                                                          ║
║  ACTOR: MODEL-MAINTAINER                                                 ║
║    Pflegt das Model: W{n} hinzufuegen/korrigieren/GC,                  ║
║    Model-Split ausfuehren, Kap. 6a aktualisieren,                      ║
║    Commit-Tracking pflegen.                                              ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **MODEL-MAINTAINER** Actor hat eine einzige Verantwortung:

**Model-Pflege: W{n} verwalten, GC, Split**

Was der Model-Maintainer **TUT**:
- ✅ W{n} hinzufügen (aus OBSERVE Findings ODER git diff)
- ✅ W{n} korrigieren (aus ERGEBNIS Widerlegungen ODER Code-Realitaet)
- ✅ GC: WIDERLEGT/ELIMINIERT markieren
- ✅ Kap. 6a aktualisieren (Offene Bereiche, Aktive TCs)
- ✅ Model-Split ausführen (bei >15 W{n}/TC oder >30 gesamt)
- ✅ Model-Topologie pflegen
- ✅ Commit-Tracking: sync.last_sync_commit + sync.last_sync_date pflegen
- ✅ Out-of-Cycle: Model an Code-Realitaet anpassen (ohne OBSERVE)

Was der Model-Maintainer **NICHT TUT**:
- ❌ Findings sammeln (→ _SC_observe)
- ❌ Quality Gates prüfen (→ _SC_qualityGate)
- ❌ Hypothesen aufstellen (→ _hypothese)
- ❌ Code schreiben (→ _implement)

---

## Chain-Position

**In-Cycle (default):**
```
OBSERVE{N} → **MODEL-MAINTAIN** → QUALITYGATE{N} → HYPOTHESEN
                    |
                    ↓
              MODEL.md (updated + sync.last_sync_commit)
```

**Out-of-Cycle (--out-of-cycle):**
```
git diff → **MODEL-MAINTAIN** → (optional: /_spec → /_gap)
                    |
                    ↓
              MODEL.md (updated + sync.last_sync_commit)
```

**Prev:** OBSERVE{N} (In-Cycle) ODER /_A_orchestrate (Out-of-Cycle)
**Next:** QUALITYGATE{N} (In-Cycle) ODER /_spec (Out-of-Cycle)

**Side-Effect:** Model.md wird IMMER aktualisiert inkl. Commit-Tracking

---

## Schwierigkeits-Parameter

| Schwierigkeit | Verhalten |
|---------------|-----------|
| **easy** | Nur offensichtliche W{n} aus OBSERVE uebernehmen. Kein GC, kein Split. |
| **normal** | W{n} uebernehmen + GC ausfuehren. Split nur bei hartem Trigger (>30 gesamt). |
| **hard** | Vollstaendiges W{n}-Review, GC, Kap. 6a aktualisieren, Split bei >15/TC oder >30 gesamt. |

**System-Model (aus Manifest):** Model-Maintainer laeuft IMMER als Hauptagent (keine Subagenten).
Der Schwierigkeits-Parameter bestimmt die **Gruendlichkeit**, nicht die Parallelitaet.

---

## Schritt 0: SOFT/HARD-Trigger Check (W06) — IMMER ZUERST

Vor allen anderen Schritten: Zeilenzahl des Models pruefen und ggf. Debloat ausloesen.

```bash
# Zeilenzahl ermitteln
ZEILEN=$(wc -l < models/{NAME}_Model.md)
```

**Entscheidungslogik:**

```
IF ZEILEN >= 700:
  → HARD-Trigger (verpflichtend)
  → AUSGABE: "Model hat {ZEILEN} Zeilen (>=700). HARD-Trigger: Debloat verpflichtend."
  → Rufe auf: /_D_orchestrate {NAME} --hard
  → BLOCKIERT: Post-Cycle wird erst fortgesetzt, wenn /_D_orchestrate abgeschlossen.

ELIF ZEILEN >= 500:
  → SOFT-Trigger (Empfehlung, User entscheidet — Human-in-the-Loop)
  → AUSGABE: "Model hat {ZEILEN} Zeilen (>=500). Debloat empfohlen."
  → Frage User: "Model hat {ZEILEN} Zeilen (>500). Debloat jetzt? [j/n]"
    IF User "j": Rufe /_D_orchestrate {NAME} auf, dann weiter mit normaler Pflege.
    IF User "n": Notiz in _parking-lot.md, weiter mit normaler Pflege.

ELSE (ZEILEN < 500):
  → Kein Trigger. Normal weiter.
  → AUSGABE: "Model hat {ZEILEN} Zeilen. OK, kein Debloat noetig."
```

**Regeln:**
- HARD-Trigger blockiert IMMER (kein Ueberspringen, kein --no-trigger Flag)
- SOFT-Trigger ist HiL: User entscheidet, Agent empfiehlt NUR
- Nach Debloat (HARD oder SOFT-ja): Model neu lesen, dann Model-Update Workflow beginnen

---

## Model-Update Workflow

### 1. W{n} hinzufügen

Für jedes Finding in OBSERVE{CYCLE}.md:

```markdown
## Kap. 3: Wahrheiten (W{n})

### W42: {Titel aus Finding F{X}}
**Zyklus:** {N}
**Status:** AKTIV
**Kategorie:** {Technologie-Concern}
**Quelle:** Finding F{X} in OBSERVE{CYCLE}

{Beschreibung: 2-3 Sätze}

**Details:**
{Code-Referenzen, Kontext}

**Widerlegbar durch:**
{Wie könnte diese Wahrheit widerlegt werden?}

**Mermaid-Ziel:** {keins | Kap. X — Diagramm-Typ: Kante/Knoten ergaenzen | NEU: Typ beschreiben}
```

**Regeln fuer das Mermaid-Ziel-Feld (beim Schreiben von Schritt 1 ausfuellen):**

```
Mermaid-Ziel-Entscheidungsbaum:

  1. Beschreibt W{n} einen ABLAUF / ZUSTANDSUEBERGANG / SEQUENZ?
     JA → Suche bestehendes Mermaid im Model.
          Passt W{n} als neue Kante/Knoten in ein bestehendes Diagramm?
          JA → Mermaid-Ziel: "Kap. X — Mermaid-Typ: [Kante|Knoten] '[Text]'"
          NEIN → Mermaid-Ziel: "NEU — [flowchart|stateDiagram|sequenceDiagram]: [Kurzbeschreibung]"

  2. Beschreibt W{n} eine EIGENSCHAFT / REGEL / STATISCHE AUSSAGE?
     JA → Mermaid-Ziel: "keins" (Prosa-Proposition, kein Diagramm-Mehrwert)

  3. Hat W{n} >3 Teil-Aspekte die in Relation zueinander stehen?
     JA → Tendenz zu Mermaid. Zurueck zu Frage 1.
     NEIN → Mermaid-Ziel: "keins"
```

**W{n} BESTAETIGEN (wenn ERGEBNIS KONSISTENT-Marker gesetzt):**

Falls ERGEBNIS{CYCLE}.md fuer ein bestehendes W{n} den Marker "KONSISTENT" enthaelt:

```markdown
### W42: {Titel}
**Zyklus:** {N-original}
**Zyklus bestaetigt:** {N-aktuell}
**Status:** AKTIV (BESTAETIGT)
**[alle anderen Felder unveraendert]**
```

REGEL: "AKTIV (BESTAETIGT)" ist der korrekte Status — NICHT "BESTAETIGT" allein.
Begruendung: W{n} bleibt aktiv (kann weiter widerlegt werden), ist aber empirisch gestuetzt.

Frontmatter-Zaehler:
- `w-confirmed` im Model-Frontmatter um +1 erhoehen
- `w-open` im Model-Frontmatter um -1 verringern

**MERMAID-ANKER: W{n}-Diagramm-Verknuepfung bei BESTAETIGUNG**

Nach jeder W{n}-Bestaetigung (w-confirmed=true): Pruefe ob das bestaetigt W{n} in einem Mermaid-Kommentar-Block referenziert ist.

Regel MA-1: Jedes Mermaid-Diagramm im Model MUSS einen Kommentar-Block am Anfang haben:
```
%% Basiert auf: W10, W11, W81-W82 (letzte Aenderung: Cycle 7)
%% W81: Navigation-Properties VersorgungsvertragEntity (Cycle 7)
%% W82: Include-Chain VersorgungsvertragRepository (Cycle 7)
```

Regel MA-2: Bei W{n}-Bestaetigung — Diagramm-Annotation aktualisieren:
1. Identifiziere ob das bestaetigt W{n} ein Mermaid-Ziel ≠ "keins" hat
2. Falls ja: Pruefe ob dieses W{n} bereits im `%% Basiert auf:` Block des Ziel-Diagramms steht
3. Falls NICHT: Fuege W{n} in `%% Basiert auf:` Block ein + Einzelkommentar-Zeile
4. Falls bereits enthalten: Aktualisiere `letzte Aenderung: Cycle {N}` im Block

Regel MA-3: Bei W{n}-Aenderung (Inhalt oder Status) — UPDATE-KANDIDAT-Markierung:
```
%% Basiert auf: W10, W11, W81-W82 (letzte Aenderung: Cycle 7) [UPDATE-KANDIDAT: W81 geaendert Cycle 9]
```
→ `[UPDATE-KANDIDAT]` bleibt bis das Diagramm manuell geprueft und der Block aktualisiert wurde.
→ Beim naechsten Mermaid-Integration-Check (Schritt 3a) wird der UPDATE-KANDIDAT aufgeloest.

Regel MA-4 (hard only): Pruefe alle Mermaid-Diagramme ob `%% Basiert auf:`-Block fehlt.
→ Falls fehlend: Block erstellen und alle W{n} mit Mermaid-Ziel auf dieses Diagramm eintragen.

**Hintergrund:** DCSRE-93 Include-Chain-Diagramm war von v2.1 bis v12.0 unveraendert (9 Versionen fossilliert), obwohl W81-W82 in Cycle 7 neue Navigation-Properties identifizierten.

### 2. Garbage Collection (GC)

Für jede Widerlegung in ERGEBNIS{CYCLE}.md:

```markdown
### W23: {Titel} ~~WIDERLEGT~~
**Zyklus Original:** 2
**Zyklus Widerl.:** 4
**Status:** ~~AKTIV~~ → **WIDERLEGT**
**Grund:** {Beschreibung aus ERGEBNIS}

{Ursprüngliche Beschreibung}
```

Für strategische Elimination (Manual Override):

```markdown
### W18: {Titel} ~~ELIMINIERT~~
**Zyklus Original:** 1
**Zyklus Elim.:** 3
**Status:** ~~AKTIV~~ → **ELIMINIERT**
**Grund:** Battle-Royale Scope-Reduktion (Focus auf TC=Authentication)
```

**Mermaid-GC bei WIDERLEGT/ELIMINIERT:**

Falls das widerlegte/eliminierte W{n} ein Mermaid-Ziel hatte (Feld gesetzt, nicht "keins"):
- Pruefe ob Kante/Knoten im Ziel-Diagramm entfernt werden muss
- REGEL: Kante/Knoten nur entfernen wenn der gesamte Konzept-Bezug wegfaellt
- REGEL: Kante/Knoten BELASSEN wenn das Diagramm auch ohne dieses W{n} korrekt bleibt
- Bei Entfernung: Kommentar im Model-Dokument "Kante X entfernt wegen W{n} WIDERLEGT Zyklus {N}"

Falls Mermaid-Ziel "keins" war: keine Aktion.

### 3. Kap. 6a aktualisieren

```markdown
## Kap. 6a: Offene Bereiche & Aktive Technologie-Concerns

### Offene Bereiche
1. {Bereich 1} - {Status}
2. {Bereich 2} - {Status}
...

### Aktive Technologie-Concerns (TC)
| TC | W{n} Anzahl | Status | Priorität |
|----|-------------|--------|-----------|
| Authentication | 8 | FOKUS | HOCH |
| Storage | 3 | OFFEN | MITTEL |
| Logging | 2 | OFFEN | NIEDRIG |

**Fokus-TC:** Authentication (aktueller Zyklus)
**Nächster TC:** Storage (nach Authentication abgeschlossen)
```

### 3a. Mermaid-Integration-Check (normal + hard)

Nach W{n}-Hinzufuegung und GC: Mermaid-Ziel-Felder auswerten.

**Schritt A: Neue Kanten/Knoten in bestehende Diagramme einbauen**

Fuer jede neue W{n} mit Mermaid-Ziel ≠ "keins" und ≠ "NEU-...":
1. Lies das Ziel-Kapitel im Model
2. Lokalisiere den Mermaid-Block (```mermaid ... ```)
3. Fuege Kante/Knoten gemaess Mermaid-Ziel-Feld ein
4. Style-konform zum bestehenden Diagramm (gleiche Pfeiltypen, Knotenformen)
5. Notiere: "M{X} aktualisiert: [was hinzugefuegt]"

**Schritt B: Neue Diagramme erstellen**

Fuer jede neue W{n} mit Mermaid-Ziel = "NEU-...":
- Erstelle neuen ```mermaid```-Block im passenden Kapitel des Models
- Ueberschrift: "### [Diagramm-Titel] (W{n}, Zyklus {N})"
- Typ gemaess Mermaid-Ziel-Feld (flowchart / stateDiagram / sequenceDiagram)
- Max. 15 Knoten fuer Lesbarkeit; bei mehr: aufteilen

**Schritt C: Gesamtpruefung (hard only)**

- Sind alle Mermaid-Diagramme noch konsistent mit dem Model-Stand?
- Gibt es AKTIVE W{n} ohne Mermaid-Ziel die eigentlich eines verdienen wuerden?
  → Falls ja: Mermaid-Ziel nachtraeglich ergaenzen (kein Blocker)

**Schritt D: Kein Mermaid-Bedarf**

Falls ALLE neuen W{n} Mermaid-Ziel = "keins" haben:
→ Ausgabe: "Mermaid-Integration-Check: Keine Diagramm-Updates noetig."
→ Weiter mit Schritt 3a-E (falls zutreffend) oder Schritt 4.

**Schritt 3a-E: Mermaid-Inhalts-Update bei bestaetigt W{n} (v2.7+, I-03)**

**Zweck:** Prueft ob bei W{n}-Bestaetigung (OFFEN → BESTAETIGT) die tatsaechlichen
Diagramm-INHALTE (Kanten, Knoten, Zustaende) die Erkenntnis reflektieren.
Dies geht UEBER die MA-1..MA-4 Kommentar-Annotation hinaus.

**Abgrenzung:** MA-Regeln (MA-1..MA-4) pflegen den `%% Basiert auf:`-Kommentar-Block.
Schritt 3a-E prueft ob die Diagramm-INHALTE (Kanten/Knoten/Zustaende) mit der
bestaetigt W{n} inhaltlich uebereinstimmen.

**Eingangsbedingung:**
- Mindestens 1 W{n} hat in DIESEM Zyklus Status-Wechsel: OFFEN/AKTIV → AKTIV (BESTAETIGT)
- UND dieses W{n} hat Mermaid-Ziel ≠ "keins"

Falls Eingangsbedingung NICHT erfuellt: Schritt 3a-E ueberspringen → Schritt 4.

**Pruef-Logik (pro qualifiziertes W{n}):**

```
1. Lies das Mermaid-Ziel-Feld des bestaetigt W{n}
2. Lokalisiere das Ziel-Diagramm im Model (Kapitel + Mermaid-Block)
3. Pruefe: Reflektiert das Diagramm die W{n}-Erkenntnis INHALTLICH?
   - Hat die Erkenntnis Implikationen fuer Kanten (Ablaeufe, Beziehungen)?
   - Hat die Erkenntnis Implikationen fuer Knoten (Komponenten, Zustaende)?
   - Sind diese Implikationen im Diagramm bereits abgebildet?
4. Falls Diagramm AKTUELL: Keine Aktion.
   Ausgabe: "W{n} BESTAETIGT: Diagramm [{Kap}] inhaltlich aktuell."
5. Falls Diagramm VERALTET:
   Fuege Markierung in den Kommentar-Block ein:
   %% [INHALTS-UPDATE NOETIG] W{n} bestaetigt Cycle {N}: {Kurzbeschreibung der fehlenden Inhalte}
   Ausgabe: "W{n} BESTAETIGT: Diagramm [{Kap}] [INHALTS-UPDATE NOETIG] markiert."
```

**WICHTIG:** Schritt 3a-E fuehrt den Diagramm-Update NICHT selbst durch.
Er MARKIERT nur Diagramme die moeglicherweise veraltet sind.
Der tatsaechliche Update geschieht im naechsten Zyklus via Schritt A (Kanten/Knoten einbauen)
oder Schritt B (neue Diagramme erstellen).

**Aufloesungs-Pfad fuer [INHALTS-UPDATE NOETIG]:**
- Beim naechsten Mermaid-Integration-Check (Schritt 3a) erkennt Schritt A die Markierung
- Schritt A fuehrt den inhaltlichen Update durch und entfernt die Markierung
- Alternativ: Schritt C (hard only) loest die Markierung bei Gesamtpruefung auf

**Schwierigkeits-Abstufung:**

| Schwierigkeit | Verhalten |
|---------------|-----------|
| easy | Mermaid-Integration-Check UEBERSPRINGEN (inkl. Schritt 3a-E). |
| normal | Schritt A + B + D + E (Inhalts-Pruefung bei Bestaetigung). |
| hard | Schritt A + B + C + D + E (vollstaendige Pruefung inkl. Inhalts-Check). |

### Schritt 3b: Mermaid-Typ-Qualitaets-Gate (v2.8, NEU)

**Aktivierung:** Schwierigkeit = `normal` ODER `hard` UND Schritt 3a hatte >= 1 Mermaid-Aenderung.
**Ueberspringen:** Schwierigkeit = `easy` ODER keine Mermaid-Aenderungen in Schritt 3a.

**Zweck:** Prueft ob der verwendete Mermaid-Typ semantisch korrekt ist (nicht nur syntaktisch).
Kein Auto-Fix. Kein Gate-Blocking. Nur informative WARN-Meldungen.

---

#### 3b-Algorithmus: 3-Fragen-Check

Fuer JEDEN Mermaid-Block der in Schritt 3a bearbeitet wurde:

**Schritt 1: IST-TYP bestimmen**
- Lese den Mermaid-Typ des Blocks (z.B. `flowchart`, `stateDiagram-v2`, `sequenceDiagram`)

**Schritt 2: 3-Fragen-Check (normative Referenz: ModelBloat_Model.md Kap.7)**

```
FRAGE 1: Hat der Inhalt ZEITLICHE REIHENFOLGE + mehr als 2 AKTEURE?
  JA  → Empfehlung: sequenceDiagram
  NEIN → Frage 2

FRAGE 2: Hat der Inhalt ZUSTANDSUEBERGAENGE + mehr als 3 ZUSTAENDE?
  JA  → Empfehlung: stateDiagram-v2
  NEIN → Frage 3

FRAGE 3: Ist der Inhalt ein Entscheidungsbaum, Ablauf oder Hierarchie?
  JA  → Empfehlung: flowchart
  NEIN → Empfehlung: erDiagram | quadrantChart | Tabelle (Spezialfall)
```

**Schritt 3: Vergleich IST-TYP vs. Empfehlung**

```
WENN IST-TYP == Empfehlung:
  STATUS = PASS
  OUTPUT: "Mermaid [Kapitel] ✓ PASS | Typ: {IST-TYP} | Begruendung: {Grund}"

SONST:
  STATUS = WARN
  OUTPUT: "Mermaid [Kapitel] ⚠ WARN"
  OUTPUT: "  Aktueller Typ: {IST-TYP}"
  OUTPUT: "  Empfohlener Typ: {Empfehlung}"
  OUTPUT: "  Grund: {Frage-1/2/3 Begruendung}"
  OUTPUT: "  Aktion: Manuelle Ueberpruefung. ModelBloat_Model.md Kap.7 konsultieren."
```

**Schritt 4: Zusammenfassung ausgeben**

```
── Schritt 3b Zusammenfassung ──
N Mermaid-Bloecke geprueft | X PASS | Y WARN
→ [Falls Y > 0]: Y Typ-Mismatches gefunden. Manuelle Ueberpruefung empfohlen.
→ [Falls Y = 0]: Alle Typen korrekt. Kein Handlungsbedarf.
```

---

#### 3b-Beispiel-Output

```
══ Schritt 3b: Mermaid-Typ-Qualitaets-Gate ══

Mermaid [0.2 Orchestrator Decision-Tree] ✓ PASS
  Typ: flowchart TD | Grund: Entscheidungsbaum

Mermaid [1.2 SC-Zyklus Ablauf-Sequenz] ⚠ WARN
  Aktueller Typ:   flowchart TB
  Empfohlener Typ: sequenceDiagram
  Grund:           zeitliche Reihenfolge + mehr als 2 Akteure
  Aktion:          Manuelle Ueberpruefung. ModelBloat_Model.md Kap.7 konsultieren.

── Zusammenfassung ──
2 Mermaid-Bloecke geprueft | 1 PASS | 1 WARN
→ 1 Typ-Mismatch gefunden. Manuelle Ueberpruefung empfohlen.
```

---

#### 3b-Regeln (normative Referenz)

| Entscheidung | Wahl | Begruendung |
|--------------|------|-------------|
| Gate-Modus | WARN (informativ) | HiL-Ansatz: Agent empfiehlt, Mensch entscheidet |
| Auto-Fix | NEIN | Mermaid-Typ-Aenderung kann Semantik veraendern |
| Frage-1-Schwelle | > 2 Akteure | < 2 Akteure = keine echte Sequenz |
| Frage-2-Schwelle | > 3 Zustaende | Kap.7: ">3 Zustaende" als stateDiagram-v2-Trigger |
| Gate bei easy | UEBERSPRINGEN | easy = Geschwindigkeit, Mermaid-Check optional |
| Manifest-Eintrag | `mermaid_gate_3b: {N_PASS}/{N_TOTAL}` | Audit-Trail |

#### 3b-Vertrag

**INPUT:** Liste aller Mermaid-Bloecke aus Schritt 3a (diagram_type, chapter, inhalt)
**OUTPUT:** Report-Zeile pro Block + Zusammenfassung + Manifest-Eintrag
**GARANTIE:** Kein Auto-Fix. Gate blockiert NICHT (nur WARN). Immer idempotent.

---

### 4. Commit-Tracking (IMMER - letzter Schritt vor Split-Check)

Nach JEDEM Model-Update wird der sync-Block im Model-Frontmatter aktualisiert:

```bash
# Aktuellen Commit-Hash ermitteln
git rev-parse HEAD
```

```yaml
# Im Model-Frontmatter:
sync:
  last_sync_commit: "abc1234"      # git rev-parse HEAD (kurz oder lang)
  last_sync_date: "2026-02-19"     # Aktuelles Datum
  sync_source: "in-cycle"          # "in-cycle" | "out-of-cycle" | "resync"
```

**Regeln:**
- Commit-Hash wird IMMER am ENDE des Model-Updates geschrieben (nach W{n}, GC, Kap. 6a)
- Falls Model-Frontmatter noch KEINEN sync-Block hat: Erstellen
- Falls sync-Block existiert: Ueberschreiben (last_sync_commit + last_sync_date + sync_source)
- Der Hash referenziert den AKTUELLEN HEAD zum Zeitpunkt des Model-Updates

---

## Out-of-Cycle Modus (--out-of-cycle)

Wenn `--out-of-cycle` Flag gesetzt ist ODER kein OBSERVE{CYCLE}.md existiert,
arbeitet der Model-Maintainer mit **git diff statt OBSERVE** als Input:

### Ablauf

```
1. Lies sync.last_sync_commit aus Model-Frontmatter
2. Berechne Drift: git diff {last_sync_commit}..HEAD --stat
3. Falls kein Drift: "Model ist aktuell" → DONE (nur sync_date aktualisieren)
4. Falls Drift vorhanden:
   a. git diff {last_sync_commit}..HEAD -- *.cs (nur relevante Dateien)
   b. Analysiere Aenderungen als "synthetische Findings"
   c. Fuer jede relevante Aenderung: Neues W{n} ODER Update existierendes W{n}
   d. GC: W{n} die durch Aenderungen obsolet wurden → WIDERLEGT
   e. Kap. 6a aktualisieren
   f. sync.last_sync_commit auf HEAD setzen
```

### Synthetische Findings aus git diff

Statt OBSERVE-Findings werden Code-Aenderungen direkt in W{n} uebersetzt:

```markdown
### W{n}: {Was hat sich geaendert}
**Zyklus:** out-of-cycle
**Status:** AKTIV
**Kategorie:** {TC aus Dateipfad ableiten}
**Quelle:** git diff {old_commit}..{new_commit} -- {dateipfad}

{Beschreibung der Code-Aenderung und was sie fuer das Model bedeutet}

**Details:**
{Relevante Diff-Ausschnitte}

**Widerlegbar durch:**
{Wie koennte diese Aenderung rueckgaengig gemacht werden?}
```

### Drift-Erkennung mit Spec

Falls `spec/{NAME}_SPEC.md` existiert, wird zusaetzlich geprueft:
- Welche Spec-Anforderungen sind durch die Aenderungen NEU erfuellt?
- Welche Spec-Anforderungen sind durch die Aenderungen GEBROCHEN?
- → Ergebnis fliesst in Kap. 6a als Status-Update ein

### Wann Out-of-Cycle nutzen?

| Situation | Empfehlung |
|-----------|-----------|
| Nach /_I_* Pipeline (Code geschrieben) | `/_SC_modelMaintain {NAME} --out-of-cycle` |
| Zwischen Zyklen (Model-Drift korrigieren) | `/_SC_modelMaintain {NAME} --out-of-cycle` |
| Nach externem Merge (andere Branches) | `/_SC_modelMaintain {NAME} --out-of-cycle` |
| Innerhalb /_SC_orchestrate Zyklus | KEIN --out-of-cycle (OBSERVE ist da) |
| Via /_A_orchestrate RESYNC | Automatisch --out-of-cycle |

---

## Model-Split Trigger

### PFLICHT-Split wenn:
1. **>15 W{n} pro TC** (Kohäsions-Schwelle)
2. **>30 W{n} gesamt** (Komplexitäts-Schwelle)
3. **R-AP4** (Anti-Pattern: Explodierendes Model)

### Split-Ausführung

#### 1. Model-Topologie erstellen

```markdown
# Model-Topologie: {NAME}

**Split-Datum:** {YYYY-MM-DD}
**Zyklus:** {N}
**Grund:** {>15 W{n}/TC in Authentication}

## Teilmodelle

| TC | Pfad | Status | W{n} | Fokus |
|----|------|--------|------|-------|
| Authentication | models/{NAME}_Authentication_Model.md | AKTIV | 18 | ✓ FOKUS |
| Storage | models/{NAME}_Storage_Model.md | OFFEN | 8 | - |
| Logging | models/{NAME}_Logging_Model.md | OFFEN | 4 | - |

**Regeln:**
- VM-1: Nur 1 FOKUS-Teilmodel gleichzeitig
- VM-2: Cross-Cutting-Schutz: Min. 1 Drafter liest ALLE Teilmodelle
- VM-3: Fokus-Wechsel nur nach Feature-Abschluss
```

#### 2. Teilmodelle erstellen

```markdown
# Model: {NAME} - {TC}

**Parent:** {NAME}_Model.md
**Technologie-Concern:** {TC}
**Status:** {FOKUS|OFFEN|ABGESCHLOSSEN}

## Kap. 3: Wahrheiten (W{n})

{Nur W{n} die zu diesem TC gehören}

## Kap. 6a: Offene Bereiche (TC-spezifisch)

{Offene Bereiche innerhalb dieses TC}
```

---

## Parking Lot Integration

Falls während Model-Maintenance Incidental Tasks auffallen:

**Beispiel:**
"W42 lässt vermuten, dass Entity-Framework Upgrade nötig ist (aktuell 6.x → 8.x)"

→ Schreibe in `_parking-lot.md`:

```markdown
## 2026-02-03 - Von /_SC_modelMaintain (Cycle 4)

- [ ] **Entity-Framework 6.x → 8.x Migration**
  - **Beschreibung:** Upgrade EF wegen Performance-Issues (W42)
  - **Grund:** Model-Maintenance ergab Abhängigkeit
  - **Priorität:** HOCH
  - **TC-Nähe:** Data-Access
  - **Quelle:** W42 Implikation
```

---

## Kompakt-Sicherheit

Command schreibt direkt Model.md:
- State: Model.md Version erhöht
- Resume: Nächster Command liest aktualisiertes Model

---

## Obsidian-Tags

**Hinweis:** _SC_modelMaintain erstellt KEIN eigenes Synthese-Dokument.
Es aktualisiert nur Model.md.

Model.md hat bereits Tags + NEU sync-Block:
```yaml
tags:
  - type/model
  - op/{FEATURE}
  - topic/{Kern-Konzepte}
version: {N}
sync:
  last_sync_commit: "{HASH}"
  last_sync_date: "{YYYY-MM-DD}"
  sync_source: "{in-cycle|out-of-cycle|resync}"
```

---

## Changelog

- v2.8: Mermaid-Typ-Qualitaets-Gate (EC-1/S1_Gate 2026-02-28): Schritt 3b: 3-Fragen-Check fuer semantisch korrekten Mermaid-Typ. Aktivierung: normal+hard UND >= 1 Mermaid-Aenderung in 3a. Kein Auto-Fix, kein Gate-Blocking, nur WARN. 3-Fragen: sequenceDiagram (zeitl. Reihenfolge + >2 Akteure), stateDiagram-v2 (Zustandsuebergaenge + >3 Zustaende), flowchart (Entscheidungsbaum/Ablauf/Hierarchie). Manifest-Eintrag: mermaid_gate_3b. Normative Referenz: ModelBloat_Model.md Kap.7.
- v2.7: Mermaid-Inhalts-Update bei W{n}-Bestaetigung (I-03/W108 2026-02-27): Schritt 3a-E: Bei W{n}-Bestaetigung (OFFEN→BESTAETIGT) mit Mermaid-Ziel: Pruefe ob Diagramm-INHALTE (Kanten/Knoten) die Erkenntnis reflektieren. Abgrenzung: MA-Regeln = Kommentar-Pflege, Schritt 3a-E = Inhalts-Relevanz-Pruefung. Markierung [INHALTS-UPDATE NOETIG] bei veralteten Diagrammen. Aufloesungs-Pfad via Schritt A/B. Schwierigkeits-Tabelle aktualisiert (normal: A+B+D+E, hard: A+B+C+D+E). Adressiert W108 (BESTAETIGT), W111 (OFFEN), W121 (BESTAETIGT). Verhindert Mermaid-Fossilierung bei bestaetigt W{n}.
- v2.6: Mermaid-Anker W{n}-Verknuepfung (E8/PL-FA-2 2026-02-26): Nach BESTAETIGT-Block: 4 Regeln MA-1..MA-4. MA-1: Pflicht-Kommentar-Block pro Diagramm. MA-2: Annotation bei W{n}-Bestaetigung. MA-3: UPDATE-KANDIDAT bei W{n}-Aenderung. MA-4 (hard): Rueckwirkende Annotation fehlender Bloecke. Verhindert Mermaid-Fossilierung (DCSRE-93: 9 Versionen unveraendert). Vertrag: Mermaid-Anker-Zeile eingefuegt.
- v2.5: Mermaid-First Integration (OP-11 2026-02-26): Schritt 1 W{n}-Template: Mermaid-Ziel-Feld mit Entscheidungsbaum. Schritt 2 GC: Mermaid-GC bei WIDERLEGT/ELIMINIERT. Schritt 3a: Mermaid-Integration-Check (normal+hard). Schritt 1 Zusatz: BESTAETIGT-Status explizit mit w-confirmed Frontmatter-Pflege. Vertrag: SCHREIBT-Block erweitert.
- v2.4: SOFT/HARD-Trigger (W06, ModelBloat 2026-02-26): Zeilenzahl-Check vor allen Schritten. SOFT (>=500Z): HiL-Empfehlung. HARD (>=700Z): /_D_orchestrate verpflichtend.
- v2.3: Commit-Tracking + Out-of-Cycle Support
- v2.2: LEGACY-Referenz entfernt
- v2.0: Initiale Version (Post-Cycle, GC + neue W{n})

---

## Siehe auch

- [[SC_observe]] - Vorheriger Schritt In-Cycle (liefert Findings)
- [[SC_qualityGate]] - Naechster Schritt In-Cycle (prueft Model)
- [[A_orchestrate]] - Orchestrator fuer Out-of-Cycle (RESYNC Modus)
- [[Model-Topologie]] - Bei Model-Split
- [[_analyse]] - LEGACY Command (<v2.2)
- [[D_orchestrate]] - Debloat-Orchestrator (SOFT/HARD-Trigger Ziel)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_SC_modelMaintain abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
