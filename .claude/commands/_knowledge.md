# Forschung: Knowledge Deep-Dive (Parallel zum Zyklus)

Du fuehrst eine tiefgehende Wissens-Recherche zu einem spezifischen Technologie-Thema durch.
Dieses Command laeuft **PARALLEL** zum Hauptzyklus und blockiert keine andere Phase.

## Aufruf

```
/_knowledge {THEMA} [easy|normal|hard]
```

- **THEMA** (Pflicht): Das zu erforschende Technologie-Thema, z.B. `X509-Zertifikate`, `WCF-Binding`, `SFTP-Protokoll`
- **Schwierigkeit** (Optional): Default `hard`

---

## VERTRAG (Pflicht-I/O)

```
+===============================================================+
|  COMMAND: /_knowledge {THEMA}                                  |
+===============================================================+
|                                                                |
|  LIEST (Input):                                                |
|    1. .claude/analysis/_manifest.md                            |
|    2. .claude/models/{NAME}_Model.md  <-- KONTEXT              |
|       (Was ist unser System? Wo taucht das Thema auf?)         |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|                                                                |
|    Welle 1 (Exploration, max 10):                              |
|      .claude/wissen/{THEMA}/exploration/{THEMA}-E01-{fokus}.md |
|      .claude/wissen/{THEMA}/exploration/{THEMA}-E02-{fokus}.md |
|      ... (pro Agent eine Datei)                                |
|      .claude/wissen/{THEMA}/quellen/bibliographie.md           |
|                                                                |
|    Welle 2 (Drafts, max 5):                                   |
|      .claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D01-{f}.md  |
|      .claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D02-{f}.md  |
|      ... (pro Agent eine Datei)                                |
|                                                                |
|    Welle 3 (Synthese = DU, Hauptagent):                       |
|      .claude/wissen/{THEMA}_Wissen.md                          |
|                                                                |
|    Manifest (IMMER):                                           |
|      .claude/analysis/_manifest.md (Knowledge-Sektion)         |
|                                                                |
|  PARALLEL:                                                     |
|    Dieses Command blockiert KEINE Phase des Hauptzyklus.       |
|    Es laeuft unabhaengig. Das Ergebnis ({THEMA}_Wissen.md)     |
|    kann von _SC_observe, _SC_hypothese etc. als Kontext gelesen|
|    werden.                                                     |
|                                                                |
|  COMPACT-SICHER (4 Checkpoints bei hard):                      |
|    [1a] Nach E01-E07 → Manifest + FUEHRE AUS: /compact        |
|    [1b] Nach E08-E10 → Manifest + FUEHRE AUS: /compact        |
|    [2]  Nach Drafts  → Manifest + FUEHRE AUS: /compact        |
|    [3]  Nach Synthese → Manifest + FUEHRE AUS: /compact       |
|    Die naechste Welle liest aus geschriebenen Dateien,         |
|    NICHT aus dem Konversations-Kontext.                         |
|    Schritt 0 (WAVE-RESUME) erkennt den Status im Manifest.    |
|                                                                |
+===============================================================+
```

---

## POSITION IM SYSTEM

```
  HAUPTZYKLUS (sequenziell):
  _SC_observe --> _SC_hypothese --> _SC_implement --> _SC_ergebnis
       |            |
       |            |    PARALLEL (unabhaengig):
       |            |    /_knowledge {THEMA}
       |            |         |
       |            |         v
       |            |    {THEMA}_Wissen.md
       |            |         |
       v            v         v
  [Kann {THEMA}_Wissen.md als zusaetzlichen Kontext lesen]
```

**Model.md** = Wissen ueber UNSEREN CODE (codebase-spezifisch, dicht, intern)
**{THEMA}_Wissen.md** = Wissen ueber die TECHNOLOGIE (domain-uebergreifend, erklaerend, extern)

---

## Schritt 0: Manifest + Model lesen (WAVE-RESUME)

**IMMER als Erstes:**

1. Lies `.claude/analysis/_manifest.md`
   - Ermittle den aktuellen {NAME} des Hauptzyklus
   - Pruefe ob bereits ein {THEMA}_Wissen.md existiert
   - **Pruefe Knowledge-Sektion fuer {THEMA}** auf Wellen-Status
   - Lies **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus der System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab (siehe Manifest → Modell-Zuordnung)
2. Lies `.claude/models/{NAME}_Model.md`
   - Identifiziere wo das {THEMA} in unserem System relevant ist
   - Welche Wahrheiten W{n} beziehen sich auf das Thema?
   - Welche offenen Fragen betreffen das Thema?
3. Erstelle Verzeichnisstruktur (falls noch nicht vorhanden):
   ```
   .claude/wissen/{THEMA}/
   .claude/wissen/{THEMA}/exploration/
   .claude/wissen/{THEMA}/drafts/
   .claude/wissen/{THEMA}/quellen/
   ```
4. **WAVE-RESUME (nach /compact oder Kontext-Verlust):**
   Falls Manifest eine Knowledge-Sektion fuer {THEMA} enthaelt:
   - `"Welle 1a done, Welle 1b pending"` → Starte bei **Welle 1b** (E08-E10 Dokumentation)
   - `"Welle 1 done, Welle 2 pending"` → Starte bei **Welle 2** (Drafter-Entwuerfe)
   - `"Welle 2 done, Welle 3 pending"` → Starte bei **Welle 3** (Synthese)
   - Kein Knowledge-Status fuer {THEMA} → Beginne bei **Welle 1a**

   **KRITISCH:** Nach /compact geht der gesamte Konversations-Kontext verloren.
   Die naechste Welle liest AUSSCHLIESSLICH aus den geschriebenen Dateien.
   Deshalb MUSS das Manifest vor /compact aktualisiert werden.

---

## Schwierigkeits-Parameter

| Schwierigkeit | Exploration (Welle 1) | Drafts (Welle 2) | Synthese (Welle 3) |
|---------------|----------------------|------------------|-------------------|
| **easy** | --- | --- | 1 (DU, Hauptagent) |
| **normal** | --- | 2-3 Subagenten | 1 (DU, Hauptagent) |
| **hard** | 5-10 Subagenten | 3-5 Subagenten | 1 (DU, Hauptagent) |

**System-Model (aus Manifest):** Bestimmt welches Modell pro Welle laeuft.
- opus: Exploration=haiku, Drafts=sonnet, Synthese=opus
- sonnet: Exploration=haiku, Drafts=sonnet, Synthese=sonnet
- haiku: Exploration=haiku, Drafts=haiku, Synthese=haiku

---

## DIE FEYNMAN-METHODE (Kern-Methodik)

Alle Agenten in diesem Command wenden die Feynman-Methode an.
Diese Methode ist das **paedagogische Betriebssystem** fuer Wissensextraktion.

### Die 5 Stufen

```
Stufe 1: KONZEPTZERLEGUNG
  Regel 1.1: Identifiziere den Kern
    - Was ist der zentrale Mechanismus?
    - Was ist die Hauptidee, die grundlegende Beziehung?
    - Was ist nur Detail, Beispiel oder Kontext?
    --> Das Wesentliche vom Unwesentlichen trennen.

  Regel 1.2: Fachjargon eliminieren, Praezision beibehalten
    - Ersetze Fachbegriffe durch FUNKTIONALE Beschreibungen
    - Beschreibe WAS etwas TUT, nicht nur das Etikett
    - Beispiel: Statt "X.509-Zertifikat mit RSA-2048 Schluessel"
      --> "Ein digitaler Ausweis, der beweist wer du bist,
           gesichert durch ein mathematisches Schloss das nur
           mit dem passenden Schluesselpaar geoeffnet werden kann"


Stufe 2: ANALOGICAL BRIDGING (Bruecken bauen)
  Regel 2.1: Finde STRUKTURELL passende Analogien
    - Beziehungen und Proportionen muessen stimmen
    - Die innere Logik des Konzepts muss sich widerspiegeln
    - Analogie muss an Vorwissen des Lesers anknuepfen
    - Beispiel: Stromfluss = Wasserfluss
      (Spannung=Druck, Widerstand=Rohrverengung, Strom=Durchfluss)

  Regel 2.2: Vom Konkreten zum Abstrakten
    - Starte mit vertrautem Bild (Analogie)
    - Mache Prinzip klar
    - DANN erst formale/abstrakte Darstellung einfuehren
    - Analogie = Geruest fuer Verstaendnis


Stufe 3: SPRACHE & KOGNITIVE LAST
  Regel 3.1: "Erklaere es einem Sechstklaessler"
    - Einfache Satzstrukturen
    - Pro Satz/Abschnitt nur WENIGE neue Informationen
    - Aktive Sprache verwenden
    - Arbeitsgedaechtnis des Lesers NICHT ueberfordern

  Regel 3.2: Narrative Struktur verwenden
    - Klarer Anfang (Problem oder Frage)
    - Konflikt (Warum ist das schwierig?)
    - Aufloesung (Die Erklaerung)
    - Gehirn speichert narrative Muster besser als Faktenlisten


Stufe 4: ITERATIVE VERFEINERUNG
  Regel 4.1: Wissenslücken aktiv identifizieren
    - Konzept erklaeren OHNE auf Notizen zu schauen
    - Wo bleibst du stecken? Wo wirst du vage?
    - Diese Punkte = zurueck zum Quellenmaterial
    - Zyklus: Erklaeren --> Scheitern --> Korrigieren --> Erneut

  Regel 4.2: Verstaendnis auf MEHREREN Ebenen pruefen
    - Verbal: Kannst du es erklaeren?
    - Visuell: Kannst du es als Diagramm darstellen?
    - Formal: Kannst du es mathematisch/logisch fassen?
    - Praktisch: Kannst du ein konkretes Beispiel geben?
    --> Je mehr Zugaenge, desto robuster das Verstaendnis


Stufe 5: BALANCE (Genauigkeit vs. Zugaenglichkeit)
  Regel 5.1: Wesentliche Beziehungen KORREKT wiedergeben
    - Kausalitaeten, Proportionen, Abhaengigkeiten
    - Daran darf Vereinfachung NICHTS aendern

  Regel 5.2: Transparenz ueber Grenzen
    - Explizit sagen wo Vereinfachung ihre Grenzen hat
    - Wo die Analogie nicht mehr traegt
    - Was man nicht weiss oder was noch offen ist
    - Wissenschaftliche Redlichkeit
```

### Warum die Feynman-Methode funktioniert (Wissenschaftliche Basis)

```
KOGNITIONSWISSENSCHAFT:
  - Optimiert kognitive Last (Baddeley Working Memory Model)
  - Foerdert exekutive Funktionen: Planung, Aufmerksamkeit,
    Fehlerkontrolle, flexibles Denken
  - Analogien aktivieren spezifische Hirnnetzwerke
    (linker praefrontaler Cortex)

LERNPSYCHOLOGIE (Selbstbestimmungstheorie):
  - Autonomie: Kontrolle ueber den eigenen Lernprozess
  - Kompetenz: "Ich kann es erklaeren!" = Motivationsschub
  - Soziale Eingebundenheit: Erklaeren hat soziale Komponente

KONSTRUKTIVISMUS (Vygotsky):
  - Wissen wird AKTIV konstruiert, nicht passiv aufgenommen
  - Erklaeren = aktive Konstruktion = tieferes Verstaendnis

ERROR-BASED LEARNING:
  - Stufe 4 (Luecken finden) = systematische Fehlerkorrektur
  - Wir lernen am besten aus erkannten und korrigierten Fehlern

KOMMUNIKATIONSTHEORIE:
  - Reduziert Rauschen (Shannon Informationstheorie)
  - Ethos (Glaubwuerdigkeit durch Klarheit)
  - Pathos (emotionale Einbindung durch Narrative)
  - Logos (klare Argumentation durch logische Zerlegung)
```

---

## Ablauf: hard (Standard)

```
Welle 1a: +---+ +---+ +---+ +---+ +---+ +---+ +---+
EXPLORATION | E | | E | | E | | E | | E | | E | | E |  (PARALLEL, unabhaengig)
          +-+-+ +-+-+ +-+-+ +-+-+ +-+-+ +-+-+ +-+-+
          Kartographie    Quellen
          (E01-E03)      (E04-E07)
            |               |
            +-------+-------+
                    |
   ╔════════════════════════════════════════════════════════════╗
   ║  COMPACT-CHECKPOINT 1a:                                    ║
   ║  1. Manifest: "Welle 1a done, Welle 1b pending"           ║
   ║  2. Dateien: exploration/{THEMA}-E01..E07.md MUESSEN existieren  ║
   ║  3. FUEHRE AUS: /compact                                    ║
   ╚════════════════════════════════════════════════════════════╝
                    |
                    v
Welle 1b: +---+ +---+ +---+
EXPLORATION | E | | E | | E |  <--LIEST-- exploration/{THEMA}-E01..E07.md
          +-+-+ +-+-+ +-+-+  --SCHREIBT--> quellen/bibliographie.md
          Dokumentation                     quellen/{ID}_{name}.md
          (E08-E10)
            |
            +
            |
   ╔════════════════════════════════════════════════════════════╗
   ║  COMPACT-CHECKPOINT 1:                                     ║
   ║  1. Manifest: "Welle 1 done, Welle 2 pending"             ║
   ║  2. Dateien: exploration/*.md + quellen/bibliographie.md   ║
   ║  3. FUEHRE AUS: /compact                                    ║
   ╚════════════════════════════════════════════════════════════╝
                    |
                    v
Welle 2:  +---+ +---+ +---+ +---+ +---+
DRAFTS    | D | | D | | D | | D | | D |  <--LIEST-- exploration/{THEMA}-E*.md
          +-+-+ +-+-+ +-+-+ +-+-+ +-+-+             quellen/bibliographie.md
          FEYNMAN-ENTWUERFE                          models/{NAME}_Model.md
          (verschiedene Perspektiven)  --SCHREIBT--> drafts/entwurf_*.md
            |
            +-------+-------+
                    |
   ╔════════════════════════════════════════════════════════════╗
   ║  COMPACT-CHECKPOINT 2:                                     ║
   ║  1. Manifest: "Welle 2 done, Welle 3 pending"             ║
   ║  2. Dateien: drafts/entwurf_*.md MUESSEN existieren        ║
   ║  3. FUEHRE AUS: /compact                                    ║
   ╚════════════════════════════════════════════════════════════╝
                    |
                    v
Welle 3:  +-------------------+
SYNTHESE  |     SYNTHESE      |  <--LIEST-- drafts/entwurf_*.md
          |  (DU, Hauptagent) |             quellen/bibliographie.md
          +-------------------+             models/{NAME}_Model.md
                    |          --SCHREIBT--> {THEMA}_Wissen.md
                    |
               [Manifest: "Knowledge done"]
```

---

## Welle 1: Exploration (Kartographie + Quellensammlung)

### Ausfuehrungsreihenfolge (WICHTIG)

Welle 1 ist in **zwei Sub-Wellen** aufgeteilt:

```
Welle 1a (PARALLEL):  E01-E07  ──SCHREIBT──▶ exploration/{THEMA}-E*.md
     |
     ▼ [Manifest: "Welle 1a done, Welle 1b pending"]
     |  [FUEHRE AUS: /compact]
     |
Welle 1b (PARALLEL):  E08-E10  ──LIEST──▶ exploration/{THEMA}-E01..E07.md
                                ──SCHREIBT──▶ quellen/bibliographie.md
```

**Grund:** Gruppe C (E08-E10) MUSS die Outputs von E01-E07 lesen.
Sie koennen NICHT gleichzeitig mit E01-E07 laufen.

### Funktionale Gruppen

Die Explorer-Agenten werden in **3 funktionale Gruppen** aufgeteilt:

#### Gruppe A: Kartographie (E01-E03) - "Wo stehen wir?" [Welle 1a]

Aufgabe: Unsere Codebase und unser Model nach dem Thema durchsuchen.

```
Du bist Explorer E{NN} fuer die Wissens-Kartographie von "{THEMA}".

INPUT - LIES ZUERST:
  .claude/models/{NAME}_Model.md

AUFTRAG: {Fokus-Beschreibung}

Suche in der Codebase nach:
- Wo wird {THEMA} verwendet? (Dateien, Zeilen, Konfiguration)
- Welche Versionen/Typen/Varianten sind im Einsatz?
- Welche Wahrheiten W{n} im Model beziehen sich auf {THEMA}?
- Welche offenen Fragen betreffen {THEMA}?

SCHREIB-PFLICHT:
Du MUSST deine Findings in folgende Datei schreiben:
  .claude/wissen/{THEMA}/exploration/{THEMA}-E{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  thema: {THEMA}
  phase: knowledge
  wave: exploration
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  gruppe: kartographie
  agent: E{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  status: final
  ---

  # Kartographie E{NN}: {Fokus-Titel}

  ## Model-Bezug
  {Welche W{n} Wahrheiten betreffen dieses Thema?}

  ## Codebase-Findings
  ### F1: {Finding}
  - **Datei:** {Pfad}:{Zeile}
  - **Version/Typ:** {z.B. TLS 1.2, RSA-2048}
  - **Beschreibung:** ...

  ## Zusammenfassung
  {3-5 Saetze}

WICHTIG:
- NUR Kartografie: Was HABEN wir, was NUTZEN wir
- Versionen, Typen, Konfigurationen erfassen
- JEDES Finding mit Datei:Zeile belegen
```

| Agent | Fokus | Aufgabe |
|-------|-------|---------|
| E01 | codebase-nutzung | Wo wird {THEMA} in unserem Code verwendet? |
| E02 | konfiguration | Welche Config-Parameter betreffen {THEMA}? |
| E03 | model-bezug | Welche Model-Wahrheiten W{n} und offene Fragen betreffen {THEMA}? |

#### Gruppe B: Quellensammlung (E04-E07) - "Was gibt es da draussen?" [Welle 1a]

Aufgabe: Externe Quellen finden und kartographieren.

```
Du bist Explorer E{NN} fuer die Quellensammlung zu "{THEMA}".

AUFTRAG: {Fokus-Beschreibung}

Nutze WebSearch um folgende Quellen-Typen zu finden:
- Offizielle Spezifikationen (RFCs, Standards, Specs)
- Technische Dokumentation (Microsoft Docs, MDN, etc.)
- Erklaerungen und Tutorials (gut bewertete Artikel)
- Akademische Paper (falls relevant)
- Video-Transkripte (Konferenzen, Vortraege)
- Schulungsmaterial (Kurse, Zertifizierungen)

SCHREIB-PFLICHT:
Du MUSST deine Findings in folgende Datei schreiben:
  .claude/wissen/{THEMA}/exploration/{THEMA}-E{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  thema: {THEMA}
  phase: knowledge
  wave: exploration
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  gruppe: quellen
  agent: E{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  status: final
  ---

  # Quellensammlung E{NN}: {Fokus-Titel}

  ## Gefundene Quellen

  ### Q1: {Quellen-Titel}
  - **Typ:** RFC | Dokumentation | Tutorial | Paper | Video | Kurs
  - **URL:** {URL}
  - **Relevanz:** {Warum ist diese Quelle wichtig fuer uns?}
  - **Kerninhalt:** {2-3 Saetze was die Quelle abdeckt}

  ### Q2: ...

  ## Zusammenfassung
  {Welche Aspekte von {THEMA} sind gut dokumentiert?
   Wo gibt es Luecken?}

WICHTIG:
- QUALITAET vor Quantitaet - nur wirklich relevante Quellen
- Offizielle Quellen bevorzugen (RFCs, Specs, offizielle Docs)
- URL MUSS funktionieren und erreichbar sein
- Kurze Erklaerung was jede Quelle abdeckt
```

| Agent | Fokus | Quellen-Typ |
|-------|-------|-------------|
| E04 | spezifikationen | RFCs, Standards, offizielle Specs |
| E05 | dokumentation | Microsoft Docs, offizielle Tutorials, API-Docs |
| E06 | erklaerungen | Artikel, Blog-Posts, Stack Overflow, Community |
| E07 | akademisch | Paper, Konferenz-Vortraege, Schulungsmaterial |

### Nach Welle 1a: Manifest aktualisieren (PFLICHT vor Welle 1b)

```markdown
## Knowledge: {THEMA}
**PHASE:** knowledge
**WELLE:** 1a abgeschlossen, 1b ausstehend
**NAECHSTER SCHRITT:** Welle 1b (E08-E10 Dokumentation) starten - LIEST exploration/{THEMA}-E01..E07.md

### Exploration Gruppe A+B (Welle 1a) - {Datum}
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E01-codebase-nutzung.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E02-konfiguration.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E03-model-bezug.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E04-spezifikationen.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E05-dokumentation.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E06-erklaerungen.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E07-akademisch.md

### Exploration Gruppe C (Welle 1b) - ausstehend
### Drafts (Welle 2) - ausstehend
### Synthese (Welle 3) - ausstehend
```

**FUEHRE JETZT AUS:** `/compact`
Welle 1b (E08-E10) liest dann aus den exploration/*.md Dateien, NICHT aus dem Kontext.

---

#### Gruppe C: Dokumentation (E08-E10) - "Ordnung ins Wissen" [Welle 1b - NACH 1a]

Aufgabe: Quellen organisieren, Bibliographie erstellen, wichtige Inhalte sichern.

```
Du bist Explorer E{NN} fuer die Quellen-Dokumentation von "{THEMA}".

INPUT - LIES ZUERST:
  Alle .claude/wissen/{THEMA}/exploration/{THEMA}-E*.md (vorherige Explorers)

AUFTRAG: {Fokus-Beschreibung}

Erstelle eine strukturierte Bibliographie und sichere die wichtigsten
Inhalte als Referenz-Dokumente.

SCHREIB-PFLICHT (MEHRERE Dateien):

1. Bibliographie:
   .claude/wissen/{THEMA}/quellen/bibliographie.md

   FORMAT:
   # Bibliographie: {THEMA}

   ## Primaerquellen (Spezifikationen, Standards)
   | ID | Titel | Typ | URL/Pfad | Relevanz |
   |-------|-------|-----|----------|----------|
   | P01 | ... | RFC | ... | ... |

   ## Sekundaerquellen (Dokumentation, Tutorials)
   | ID | Titel | Typ | URL/Pfad | Relevanz |
   |-------|-------|-----|----------|----------|
   | S01 | ... | Docs | ... | ... |

   ## Tertinaerquellen (Erklaerungen, Community)
   | ID | Titel | Typ | URL/Pfad | Relevanz |
   |-------|-------|-----|----------|----------|
   | T01 | ... | Blog | ... | ... |

2. Inhaltssicherung (pro wichtige Quelle):
   .claude/wissen/{THEMA}/quellen/{ID}_{kurzname}.md

   FORMAT:
   # {Quellen-Titel}
   **Quelle:** {URL}
   **Typ:** {Typ}
   **Abgerufen:** {Datum}

   ## Kernaussagen
   {Die wichtigsten Punkte aus dieser Quelle}

   ## Relevanz fuer uns
   {Warum ist das fuer unser {THEMA}-Problem wichtig?}

WICHTIG:
- Bibliographie MUSS alle Quellen der vorherigen Explorers enthalten
- Jede Quelle mit eindeutiger ID (P01, S01, T01, ...)
- Bei Videos: Zeitstempel der relevanten Stellen
- Bei Docs: Genaue Seite/Abschnitt
- Bei Code: Genaue Datei:Zeile
```

| Agent | Fokus | Aufgabe |
|-------|-------|---------|
| E08 | bibliographie | Alle Quellen sammeln, ordnen, Bibliographie.md erstellen |
| E09 | inhalt-primaer | Wichtigste Primaerquellen sichern und zusammenfassen |
| E10 | inhalt-sekundaer | Wichtigste Sekundaerquellen sichern und zusammenfassen |

### Nach Welle 1 (gesamt): Manifest aktualisieren (PFLICHT vor Welle 2)

```markdown
## Knowledge: {THEMA}
**PHASE:** knowledge
**WELLE:** 1 abgeschlossen (1a + 1b), 2 ausstehend
**NAECHSTER SCHRITT:** Welle 2 (Drafter-Entwuerfe) starten
  LIEST: exploration/{THEMA}-E*.md + quellen/bibliographie.md + models/{NAME}_Model.md
  SCHREIBT: drafts/entwurf_{THEMA}-D*.md

### Exploration Gruppe A+B (Welle 1a) - {Datum}
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E01-codebase-nutzung.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E02-konfiguration.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E03-model-bezug.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E04-spezifikationen.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E05-dokumentation.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E06-erklaerungen.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E07-akademisch.md

### Exploration Gruppe C (Welle 1b) - {Datum}
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E08-bibliographie.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E09-inhalt-primaer.md
- [x] .claude/wissen/{THEMA}/exploration/{THEMA}-E10-inhalt-sekundaer.md
- [x] .claude/wissen/{THEMA}/quellen/bibliographie.md

### Drafts (Welle 2) - ausstehend
### Synthese (Welle 3) - ausstehend
```

**FUEHRE JETZT AUS:** `/compact`
Welle 2 liest dann aus den Dateien auf Disk, NICHT aus dem Kontext.

---

## Welle 2: Drafts (Feynman-Entwuerfe)

### Voraussetzung (DATEI-BASIERT, nicht Kontext)

**PFLICHT-INPUT - Lies ALLE diese Dateien von Disk:**

1. `.claude/wissen/{THEMA}/exploration/{THEMA}-E*.md` (Kartographie von Welle 1a)
   Falls nicht vorhanden → FEHLER: "Welle 1a nicht abgeschlossen. Starte /_knowledge {THEMA} hard"

2. `.claude/wissen/{THEMA}/quellen/bibliographie.md` (Quellen-Index von Welle 1b)
   Falls nicht vorhanden → FEHLER: "Welle 1b nicht abgeschlossen."

3. `.claude/wissen/{THEMA}/quellen/*.md` (Gesicherte Quellen-Inhalte von Welle 1b)
   **WICHTIG:** Explorer waren NUR Sammler. Die Drafter-Agenten muessen die
   gesicherten Quellen-Inhalte AKTIV nutzen, nicht nur die Kartographie.

4. `.claude/models/{NAME}_Model.md` (System-Kontext)
   Falls nicht vorhanden → FEHLER: "Kein Model gefunden."

**QUELLEN-KETTE:**
```
Explorer (Sammler)   →  quellen/bibliographie.md (Index)
                     →  quellen/P01_*.md, S01_*.md (Inhalte)
                           |
                           ▼
Drafter (Verarbeiter) →  LIEST quellen/*.md Inhalte
                      →  WebFetch fuer fehlende Details (optional)
                      →  SCHREIBT drafts/entwurf_*.md
```

### Methodik: Feynman-Entwuerfe

Jeder Drafter-Agent schreibt einen **Entwurf** der das Thema aus einer
ANDEREN PERSPEKTIVE erklaert. Alle Agenten wenden die Feynman-Methode an
(5 Stufen, siehe oben), aber jeder hat einen anderen FOKUS.

### Agent-Auftraege

```
Du bist Drafter D{NN} fuer den Feynman-Entwurf zu "{THEMA}".

INPUT - LIES ZUERST DIESE DATEIEN (von DISK, nicht aus Kontext):
  1. .claude/models/{NAME}_Model.md (unser System-Kontext)
  2. .claude/wissen/{THEMA}/exploration/{THEMA}-E*.md (Kartographie der Codebase)
  3. .claude/wissen/{THEMA}/quellen/bibliographie.md (Quellen-Index)
  4. .claude/wissen/{THEMA}/quellen/*.md (Gesicherte Quellen-Inhalte)

QUELLEN-NUTZUNG (PFLICHT):
  Explorer waren NUR Sammler. DU musst die Quellen VERARBEITEN:
  - Lies die quellen/*.md Inhaltsdateien (P01_*, S01_*, T01_*)
  - Nutze den INHALT fuer deine Feynman-Erklaerung
  - Falls Details fehlen: WebFetch auf URLs aus bibliographie.md
  - Referenziere Quellen mit ihren IDs (P01, S01, T01, ...)

AUFTRAG: {Fokus-Beschreibung}

FEYNMAN-METHODE (PFLICHT):
Du MUSST die folgenden 5 Stufen anwenden:

  Stufe 1 - KONZEPTZERLEGUNG:
    Identifiziere den KERN des Themas aus deiner Perspektive.
    Ersetze Jargon durch funktionale Beschreibungen.
    Was TUT es? Nicht: Wie HEISST es?

  Stufe 2 - ANALOGICAL BRIDGING:
    Finde mindestens 1 strukturell passende Analogie.
    Die Analogie muss die innere Logik widerspiegeln.
    Starte beim vertrauten Bild, fuehre dann zum Abstrakten.

  Stufe 3 - SPRACHE & KOGNITIVE LAST:
    Einfache Saetze. Wenige neue Informationen pro Abschnitt.
    Aktive Sprache. Narrative Struktur (Problem -> Konflikt -> Aufloesung).

  Stufe 4 - ITERATIVE VERFEINERUNG:
    Identifiziere Luecken in deiner Erklaerung.
    Pruefe auf MEHREREN Ebenen: verbal, visuell (Mermaid!),
    formal (Logik), praktisch (Beispiel aus unserem System).

  Stufe 5 - BALANCE:
    Wesentliche Beziehungen KORREKT wiedergeben.
    Transparenz: Wo vereinfachst du? Wo traegt die Analogie nicht mehr?

DIAGRAMM-PFLICHT:
  Verwende Mermaid-Diagramme fuer:
  - Architektur/Topologie: flowchart oder graph
  - Ablaeufe: sequenceDiagram
  - Zustaende: stateDiagram-v2
  - Beziehungen: classDiagram oder erDiagram
  Mindestens 2 Mermaid-Diagramme pro Entwurf.

SCHREIB-PFLICHT:
Du MUSST deinen Entwurf in folgende Datei schreiben:
  .claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  thema: {THEMA}
  phase: knowledge
  wave: drafts
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  agent: D{NN}
  fokus: {fokus}
  perspektive: {Die Perspektive dieses Entwurfs}
  feynman-stufen: [1,2,3,4,5]
  date: {YYYY-MM-DD}
  reads: exploration/{THEMA}-E*.md, quellen/bibliographie.md, quellen/*.md, models/{NAME}_Model.md
  status: final
  ---

  # Entwurf D{NN}: {Titel} - {Perspektive}

  ## Gelesene Inputs
  {Liste der gelesenen Dateien mit Kurzfassung}

  ## Kern-Analogie
  {Die zentrale Analogie dieses Entwurfs - Stufe 2}

  ## Erklaerung
  {Die Feynman-gemaesse Erklaerung des Themas aus dieser Perspektive}
  {Mit Mermaid-Diagrammen}
  {Narrative Struktur: Problem -> Konflikt -> Aufloesung}

  ## Vereinfachungs-Grenzen
  {Wo vereinfacht dieser Entwurf? Wo traegt die Analogie nicht?}

  ## Quellen-Referenzen
  {Welche Quellen aus bibliographie.md wurden verwendet?}

  ## Zusammenfassung
  {5-10 Saetze}

WICHTIG:
- JEDER Entwurf muss eine ANDERE Perspektive einnehmen
- Mermaid-Diagramme sind PFLICHT (mindestens 2)
- Feynman-Stufen muessen ALLE angewandt werden
- Die Datei MUSS geschrieben werden
```

### Drafter-Perspektiven (Fokus-Bereiche)

| Agent | Fokus | Perspektive | Feynman-Schwerpunkt |
|-------|-------|-------------|---------------------|
| D01 | kern-mechanismus | "Wie funktioniert es?" - Der zentrale Mechanismus von innen | Stufe 1: Konzeptzerlegung |
| D02 | analogie-bruecke | "Wozu ist es vergleichbar?" - Strukturelle Analogien aus Alltag/anderen Domaenen | Stufe 2: Analogical Bridging |
| D03 | visuell-narrativ | "Wie sieht es aus?" - Diagramm-lastig, Story-basiert, Flowcharts | Stufe 3: Sprache + Narrative |
| D04 | fehler-grenzen | "Was kann schiefgehen?" - Edge Cases, haeufige Missverstaendnisse, Anti-Patterns | Stufe 4: Iterative Verfeinerung |
| D05 | unser-system | "Wie betrifft es UNS?" - Konkreter Bezug zu unserem System, Model-Wahrheiten | Stufe 5: Balance + Praxis |

### Nach Welle 2: Manifest aktualisieren (PFLICHT vor Welle 3)

```markdown
**WELLE:** 2 abgeschlossen, 3 ausstehend
**NAECHSTER SCHRITT:** Welle 3 (Synthese) starten
  LIEST: drafts/entwurf_{THEMA}-D*.md + quellen/bibliographie.md + models/{NAME}_Model.md
  SCHREIBT: {THEMA}_Wissen.md

### Drafter-Entwuerfe (Welle 2) - {Datum}
- [x] .claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D01-kern-mechanismus.md
- [x] .claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D02-analogie-bruecke.md
- [x] .claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D03-visuell-narrativ.md
- [x] .claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D04-fehler-grenzen.md
- [x] .claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D05-unser-system.md

### Synthese (Welle 3) - ausstehend
```

**FUEHRE JETZT AUS:** `/compact`
Welle 3 (Synthese) liest dann aus den drafts/entwurf_*.md Dateien, NICHT aus dem Kontext.

---

## Welle 3: Synthese (DU, Hauptagent - Synthese + Feynman-Meisterwerk)

### Voraussetzung (DATEI-BASIERT, nicht Kontext)

**PFLICHT-INPUT - Lies ALLE diese Dateien von Disk:**

1. `.claude/wissen/{THEMA}/drafts/entwurf_{THEMA}-D*.md` (Feynman-Entwuerfe von Welle 2)
   Falls nicht vorhanden → FEHLER: "Welle 2 nicht abgeschlossen. Starte /_knowledge {THEMA} hard"

2. `.claude/models/{NAME}_Model.md` (System-Kontext)
   Falls nicht vorhanden → FEHLER: "Kein Model gefunden."

3. `.claude/wissen/{THEMA}/quellen/bibliographie.md` (Quellen-Index)
   Falls nicht vorhanden → WARNUNG: Ohne Quellenverzeichnis fortfahren.

4. `.claude/wissen/{THEMA}/quellen/*.md` (Gesicherte Quellen-Inhalte)
   Nutze diese fuer Fakten-Check der Drafter-Entwuerfe.

**SYNTHESE-KETTE:**
```
Drafter-Entwuerfe (5 Perspektiven) ──┐
Quellen-Inhalte (quellen/*.md)     ──┤──▶ SYNTHESE ──▶ {THEMA}_Wissen.md
Model (System-Kontext)             ──┘
```

### Dein Auftrag

Du synthetisierst aus allen Drafter-Entwuerfen ein umfassendes
Wissensdokument. Dieses Dokument ist:

1. **KEIN Anfaenger-Tutorial** - Zielgruppe sind Ingenieure die am System arbeiten
2. **DICHT und EXPERT** - Erwartetes Vorwissen wird vorausgesetzt
3. **ABER MAXIMAL KLAR** - Feynman-Methode fuer Klarheit, nicht fuer Vereinfachung
4. **UMFANGREICH** - Ziel: ~25 Seiten, ausfuehrliche Behandlung
5. **DIAGRAMM-REICH** - Mermaid-Diagramme fuer JEDEN wichtigen Aspekt
6. **QUELLENBASIERT** - Jede Aussage mit Quellen-ID (P01, S01, T01) belegt

### Synthese-Methodik

```
1. Lies alle 5 Drafter-Entwuerfe
2. Identifiziere:
   - Wo UEBERLAPPEN sich die Entwuerfe? (= Kern des Themas)
   - Wo WIDERSPRECHEN sie sich? (= Pruefbedarf)
   - Wo ERGAENZEN sie sich? (= Vollstaendigkeit)
3. Pruefe Korrektheit gegen Primaerquellen
4. Synthetisiere EIN kohaerentes Dokument das:
   - Alle 5 Perspektiven integriert
   - Die besten Analogien uebernimmt
   - Die besten Diagramme uebernimmt und erweitert
   - Feynman-Stufen 1-5 ALLE anwendet
   - Vereinfachungs-Grenzen transparent macht
```

### Wissen-Dokument Struktur

**Pfad:** `.claude/wissen/{THEMA}_Wissen.md`

```markdown
# Wissen: {THEMA}

**Version:** 1.0
**Datum:** YYYY-MM-DD
**Model-Kontext:** {NAME}_Model.md v{X.Y}
**Quellen:** bibliographie.md ({Anzahl} Quellen)
**Methodik:** Feynman-Methode (5-Stufen)
**Zielgruppe:** Ingenieure am {NAME}-System

---

## Inhaltsverzeichnis

1. Einfuehrung - Warum dieses Wissen?
2. Das Problem das {THEMA} loest
3. Kern-Konzept (Feynman Stufe 1)
4. Analogie-Bruecke (Feynman Stufe 2)
5. Architektur & Komponenten
6. Ablauf & Protokoll
7. Konfiguration & Parameter
8. Sicherheits-Aspekte
9. Haeufige Fehler & Missverstaendnisse
10. Bezug zu unserem System
11. Weitergehende Themen
12. Glossar
13. Quellen & Referenzen

---

## 1. Einfuehrung - Warum dieses Wissen?

{Warum brauchen WIR dieses Wissen?}
{Bezug zu Model-Wahrheiten W{n}}
{Was passiert wenn man es NICHT versteht?}

---

## 2. Das Problem das {THEMA} loest

{Feynman Stufe 3: Narrative Struktur}
{Problem -> Konflikt -> Aufloesung}

```mermaid
{Diagramm: Das Problem OHNE die Loesung}
```

```mermaid
{Diagramm: Das Problem MIT der Loesung}
```

---

## 3. Kern-Konzept

{Feynman Stufe 1: Konzeptzerlegung}
{Der KERN in funktionalen Beschreibungen}
{Kein Jargon, nur WAS es TUT}

### 3.1 Der zentrale Mechanismus

{Erklaerung}

```mermaid
{Diagramm: Der Mechanismus}
```

### 3.2 Die grundlegenden Beziehungen

{Erklaerung}

```mermaid
{Diagramm: Die Beziehungen}
```

---

## 4. Analogie-Bruecke

{Feynman Stufe 2: Vom Konkreten zum Abstrakten}

### 4.1 Die Analogie

{Vertrautes Bild}

### 4.2 Wo die Analogie traegt

{Strukturelle Uebereinstimmungen}

### 4.3 Wo die Analogie NICHT traegt

{Feynman Stufe 5: Transparenz ueber Grenzen}

```mermaid
{Diagramm: Analogie vs. Realitaet}
```

---

## 5. Architektur & Komponenten

{Tiefe technische Darstellung}
{Jetzt DARF Fachsprache verwendet werden - nach dem die Konzepte klar sind}

```mermaid
{Architektur-Diagramm}
```

---

## 6. Ablauf & Protokoll

{Sequenz-Diagramme, Zustandsdiagramme}

```mermaid
sequenceDiagram
{Der typische Ablauf}
```

```mermaid
stateDiagram-v2
{Zustaende und Transitionen}
```

---

## 7. Konfiguration & Parameter

{Was muss konfiguriert werden?}
{Entscheidungsbaum: Welche Option fuer welchen Fall?}

```mermaid
flowchart TD
{Entscheidungsbaum}
```

---

## 8. Sicherheits-Aspekte

{Feynman Stufe 4: Edge Cases und Fehler}
{Was kann schiefgehen?}
{Angriffsvektoren, Schwachstellen}

---

## 9. Haeufige Fehler & Missverstaendnisse

{Feynman Stufe 4: Wissenslücken}

| Missverstaendnis | Realitaet | Quelle |
|------------------|-----------|--------|
| "Man denkt..." | "Tatsaechlich..." | P01 |

---

## 10. Bezug zu unserem System

{Feynman Stufe 5: Praxis-Bezug}
{Wie betrifft {THEMA} konkret unser {NAME}-System?}
{Model-Wahrheiten W{n} die sich auf {THEMA} beziehen}
{Unsere spezifischen Konfigurationen}

---

## 11. Weitergehende Themen

{Was wurde hier NICHT behandelt?}
{Moegliche weitere /_knowledge Iterationen}

---

## 12. Glossar

| Begriff | Erklaerung | Feynman-Version |
|---------|------------|-----------------|
| {Fachbegriff} | {Formale Definition} | {Funktionale Beschreibung} |

---

## 13. Quellen & Referenzen

### Primaerquellen
| ID | Titel | URL/Pfad |
|----|-------|----------|
| P01 | ... | ... |

### Sekundaerquellen
| ID | Titel | URL/Pfad |
|----|-------|----------|
| S01 | ... | ... |

### Tertinaerquellen
| ID | Titel | URL/Pfad |
|----|-------|----------|
| T01 | ... | ... |

### Entwuerfe (intern)
| Agent | Pfad | Perspektive |
|-------|------|-------------|
| D01 | .claude/wissen/{THEMA}/drafts/entwurf_... | Kern-Mechanismus |
| D02 | ... | Analogie-Bruecke |
| D03 | ... | Visuell-Narrativ |
| D04 | ... | Fehler-Grenzen |
| D05 | ... | Unser-System |
```

### Nach Welle 3: Manifest finalisieren

```markdown
## Knowledge: {THEMA}
**PHASE:** knowledge abgeschlossen
**WELLE:** 3 abgeschlossen (alle Wellen fertig)
**ERGEBNIS:** .claude/wissen/{THEMA}_Wissen.md

### Synthese (Welle 3) - {Datum}
- [x] .claude/wissen/{THEMA}_Wissen.md (v1.0, ~{N} Seiten, {M} Diagramme)
```

**FUEHRE JETZT AUS:** `/compact`
Knowledge-Prozess abgeschlossen. {THEMA}_Wissen.md steht dem Hauptzyklus zur Verfuegung.

---

## Ablauf: normal

```
Welle 1:  +---+ +---+ +---+
DRAFTS    | D | | D | | D |  <--LIEST-- MODEL + WebSearch
          +-+-+ +-+-+ +-+-+  --SCHREIBT--> drafts/entwurf_*.md
            +-----+-----+
                  |
   ╔════════════════════════════════════════════════════════════╗
   ║  COMPACT-CHECKPOINT:                                       ║
   ║  1. Manifest: "Welle 1 done, Welle 2 pending"             ║
   ║  2. Dateien: drafts/entwurf_*.md MUESSEN existieren        ║
   ║  3. FUEHRE AUS: /compact                                    ║
   ╚════════════════════════════════════════════════════════════╝
                  |
                  v
Welle 2:  +-------------------+
SYNTHESE  |     SYNTHESE      |  <--LIEST-- drafts/entwurf_*.md + MODEL
          |  (DU, Hauptagent) |  --SCHREIBT--> {THEMA}_Wissen.md
          +-------------------+
```

Keine Exploration noetig. Drafter-Agenten machen Kartographie, Quellen-Recherche
und Entwuerfe in einem Schritt. WebSearch + WebFetch direkt in Drafts.

---

## Ablauf: easy

```
          +-------------------+
SYNTHESE  |     SYNTHESE      |  <--LIEST-- MODEL + WebSearch
          |  (DU, Hauptagent) |  --SCHREIBT--> {THEMA}_Wissen.md
          +-------------------+
```

Du machst alles selbst: Kartographie, Quellensammlung, Feynman-Erklaerung.
Kuerzeres Dokument (~10 Seiten). Manifest trotzdem aktualisieren.

---

## Dateisystem-Vertrag

```
.claude/wissen/
+-- {THEMA}/
|   +-- exploration/                  <-- Welle 1: Kartographie
|   |   +-- {THEMA}-E01-codebase-nutzung.md
|   |   +-- {THEMA}-E02-konfiguration.md
|   |   +-- {THEMA}-E03-model-bezug.md
|   |   +-- {THEMA}-E04-spezifikationen.md
|   |   +-- {THEMA}-E05-dokumentation.md
|   |   +-- {THEMA}-E06-erklaerungen.md
|   |   +-- {THEMA}-E07-akademisch.md
|   |   +-- {THEMA}-E08-bibliographie.md
|   |   +-- {THEMA}-E09-inhalt-primaer.md
|   |   +-- {THEMA}-E10-inhalt-sekundaer.md
|   +-- drafts/                       <-- Welle 2: Feynman-Entwuerfe
|   |   +-- entwurf_{THEMA}-D01-kern-mechanismus.md
|   |   +-- entwurf_{THEMA}-D02-analogie-bruecke.md
|   |   +-- entwurf_{THEMA}-D03-visuell-narrativ.md
|   |   +-- entwurf_{THEMA}-D04-fehler-grenzen.md
|   |   +-- entwurf_{THEMA}-D05-unser-system.md
|   +-- quellen/                      <-- Quellen-Archiv
|       +-- bibliographie.md          <-- Strukturierte Quellenliste
|       +-- P01_{kurzname}.md         <-- Gesicherte Primaerquelle
|       +-- S01_{kurzname}.md         <-- Gesicherte Sekundaerquelle
|       +-- ...
+-- {THEMA}_Wissen.md                 <-- FINALES ERGEBNIS (Synthese)
```

---

## Integration mit Hauptzyklus

### Wie andere Commands {THEMA}_Wissen.md nutzen

**/_SC_observe** kann in Welle 2 (Synthese) zusaetzlich lesen:
```
Falls .claude/wissen/{THEMA}_Wissen.md existiert UND fuer die
aktuelle Analyse relevant ist → als zusaetzlichen Kontext einbeziehen.
```

**/_SC_hypothese** kann bei der Loesungsrecherche lesen:
```
Falls .claude/wissen/{THEMA}_Wissen.md existiert → als Hintergrundwissen
fuer die Bewertung von Loesungsansaetzen nutzen.
```

**/_SC_ergebnis** kann bei der Interpretation lesen:
```
Falls .claude/wissen/{THEMA}_Wissen.md existiert → als Referenz fuer die
Interpretation von Experiment-Ergebnissen nutzen.
```

### Manifest-Integration

Im Manifest wird eine eigene Knowledge-Sektion gefuehrt:

```markdown
## Knowledge-Base
| Thema | Status | Pfad | Datum |
|-------|--------|------|-------|
| {THEMA} | fertig | .claude/wissen/{THEMA}_Wissen.md | YYYY-MM-DD |
| {THEMA2} | Welle 2 | .claude/wissen/{THEMA2}/ | YYYY-MM-DD |
```

---

## Qualitaetskriterien

| Kriterium | Pruefung |
|-----------|----------|
| Feynman-konform | Alle 5 Stufen angewandt? |
| Diagramm-Dichte | Min. 8-10 Mermaid-Diagramme im Finaldokument? |
| Quellen-Basis | Jede Aussage mit Quellen-ID belegt? |
| Praxis-Bezug | Konkreter Bezug zu unserem System? |
| Transparenz | Vereinfachungs-Grenzen dokumentiert? |
| Glossar | Alle Fachbegriffe erklaert (formal + Feynman)? |
| Umfang | ~25 Seiten bei hard, ~15 bei normal, ~10 bei easy? |
| Zielgruppe | Fuer Ingenieure geschrieben, nicht fuer Anfaenger? |

---

## Weitere Iterationen

Das Wissen-Dokument kann iterativ erweitert werden:

```
/_knowledge {THEMA} easy
  → Liest bestehendes {THEMA}_Wissen.md
  → Ergaenzt neue Erkenntnisse aus dem Hauptzyklus
  → Aktualisiert Version
```

Typische Gruende fuer eine weitere Iteration:
- Neuer Zyklus hat neue Aspekte des Themas aufgedeckt
- Model-Update hat neue Wahrheiten W{n} zum Thema hinzugefuegt
- Tiefere Fragen aus _SC_observe oder _SC_hypothese

---

## Naechster Schritt

Nach Abschluss steht `{THEMA}_Wissen.md` allen Phasen des Hauptzyklus
als zusaetzlicher Kontext zur Verfuegung.

Weitere Themen koennen parallel erforscht werden:
`/_knowledge {ANDERES_THEMA} hard`

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_knowledge abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
