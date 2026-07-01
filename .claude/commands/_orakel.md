---
status: active
version: 1.0.0
created: 2026-03-23
updated: 2026-03-24
op: OrakelQuery
phase: Meta
type: satellite
chain_position: entry
team_based: false
---

# /_orakel - Frage-Beantworter mit Evidence-Archivierung

```
+======================================================================+
| STANDALONE COMMAND: /_orakel {FRAGE} [--routing=wiki|po|stakeholder]|
+======================================================================+
|                                                                       |
| ACTOR: DU (die ausfuehrende Claude-Instanz, kein Team noetig)       |
|                                                                       |
| ZWECK: Beantwortet eine Frage durch Evidence-Sammlung aus bekannten  |
|        Quellen (Wiki, PO, Stakeholder). Archiviert Evidence und      |
|        speist Erkenntnisse als W{n} in das aktive Feature-Model.    |
|                                                                       |
| ANWENDUNGSFALL:                                                        |
|   - PL-Item mit QUESTION-Status: Klaerungsbedarf ohne HiL-Dialog    |
|   - Unbekanntes Verhalten: "Wie soll X reagieren wenn Y passiert?"  |
|   - PO-Anforderungen nachschlagen bevor Implementierung beginnt      |
|   - QUESTION-Eskalation aus SDF Phase 2 (SC OBSERVE OQ-Eskalation)  |
|                                                                       |
| DESIGN-ZIEL (v1.0):                                                   |
|   Autonome Klaerung ohne User-Unterbrechung — BDF/SDF kann Orakel   |
|   aufrufen und Evidence-gestuetzt weitermachen statt zu blockieren.  |
+======================================================================+
```

---

## Aufruf

```
/_orakel {FRAGE} [--routing=wiki|po|stakeholder]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `FRAGE` | (Pflicht) | String | Freie Frage, z.B. "Wie soll das System bei Timeout reagieren?" |
| `--routing` | auto | `wiki`, `po`, `stakeholder` | Ziel-Quelle. `auto` = System entscheidet (Schritt 2) |

**Beispiele:**
```
/_orakel "Was ist das erwartete Verhalten bei doppeltem Auftrag?"
/_orakel "Gibt es eine Retry-Policy fuer externen Service X?" --routing=wiki
/_orakel "Muss Audit-Log DSGVO-konform sein?" --routing=po
```

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_orakel {FRAGE} [--routing=wiki|po|stakeholder]          ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {VAULT}/_manifest.md (aktives Feature, NAME)            ║
║    .claude/models/{NAME}_Model.md (aktueller W{n}-Zaehler)          ║
║    {VAULT}/_parking-lot.md (QUESTION-Items, Duplikat-Ref)  ║
║    .claude/evidence/ (bestehende Evidence, Duplikat-Pruefung)        ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/evidence/{DATUM}_{THEMA}.md (Evidence-Archiv)            ║
║    .claude/models/{NAME}_Model.md (neuer W{n} mit Evidence-Ref)     ║
║    {VAULT}/_parking-lot.md (QUESTION-Item → [?] markieren) ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    - FRAGE muss als Pflichtargument angegeben sein                   ║
║    - Evidence-Datei IMMER anlegen (auch bei "kein Fund")            ║
║    - Model NUR aktualisieren wenn echte Erkenntnis vorhanden        ║
║    - Kein HiL-Dialog im autonomen Modus (BDF/SDF Kontext)           ║
║    - Duplikat-Check VOR Schritt 3 (keine doppelten Evidence-Dateien) ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## SCHRITTE

### Schritt 1: Frage formalisieren

```
Eingabe: {FRAGE} (Freitext)

1. Keywords extrahieren (3-5 Schluesselwoerter)
2. Thema bestimmen (1 Satz, praezise)
3. Kontext aus Manifest lesen:
   - Aktives Feature (NAME aus SC_PIPELINE_STATE oder I_PIPELINE_STATE)
   - Offener PL-Item-Kontext (falls Orakel von BDF aufgerufen)
4. THEMA-Slug generieren (fuer Dateinamen): snake_case, max 40 Zeichen

OUTPUT:
  keywords: [k1, k2, k3]
  thema: "Kurze Thema-Beschreibung"
  feature: {NAME}
  thema_slug: "erwartetes_verhalten_bei_timeout"
```

### Schritt 2: Routing entscheiden

```
IF --routing explizit angegeben:
  routing = --routing Wert (wiki | po | stakeholder)
ELSE (auto):
  Analysiere Keywords + Thema:
  IF thema betrifft: Architektur, API, Infrastruktur, Konfiguration
    → routing = wiki
  IF thema betrifft: Anforderungen, Akzeptanzkriterien, Business-Regeln, DSGVO
    → routing = po
  IF thema betrifft: Stakeholder-Entscheidungen, Priorisierung, Release
    → routing = stakeholder

Logge: "Routing entschieden: {routing} (Grund: {thema})"
```

### Schritt 2.5: Duplikat-Check

```
Pruefe .claude/evidence/ auf bestehende Evidence fuer dieselbe Frage:

1. Liste alle Dateien in .claude/evidence/ (glob: *.md)
2. Lies Frontmatter jeder Evidence-Datei (frage + keywords Felder)
3. Vergleiche:
   - Exakter Frage-Match (frage == {FRAGE}) → DUPLIKAT
   - Hohes Keyword-Overlap (>= 3 von 5 Keywords identisch) → AEHNLICH

IF DUPLIKAT gefunden:
  Logge: "ORAKEL: Duplikat gefunden → .claude/evidence/{DATEI}"
  Lies bestehende Evidence-Datei
  Rueckfluss-Check: Ist W{n} im Model bereits angelegt?
    IF nein → springe zu Schritt 5 (Model aktualisieren)
    IF ja   → ORAKEL DONE (Evidence bereits vorhanden, kein weiterer Aufwand)

IF AEHNLICH gefunden:
  Logge: "ORAKEL: Aehnliche Evidence gefunden → .claude/evidence/{DATEI}"
  Weiter mit Schritt 3 (neue Evidence fuer spezifischere Frage)

IF kein Treffer:
  Weiter mit Schritt 3
```

### Schritt 3: Evidence sammeln

```
Fuehre routing-spezifische Suche durch:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
routing = wiki
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAG-Query mit Keywords aus Schritt 1:

1. Suche in globalem Wissens-Verzeichnis:
   - Glob: {META}/**/*.md, .claude/analysis/**/*.md
   - Glob: docs/**/*.md, *.md (Projekt-Root)
   - Grep: keywords[0], keywords[1], keywords[2] in gefundenen Dateien

2. Suche in bestehenden Evidence-Dateien:
   - Glob: .claude/evidence/**/*.md
   - Grep: keywords in Evidence-Dateien (Querverweise)

3. Suche in Model + Spec (falls aktives Feature vorhanden):
   - .claude/models/{NAME}_Model.md → Grep keywords
   - .claude/analysis/specs/{NAME}*.md → Grep keywords
   - .claude/analysis/drafts/{NAME}*.md → Grep keywords

4. Ergebnis-Bewertung:
   IF mind. 1 relevanter Treffer (Datei + Zeile):
     ergebnis = "gefunden"
     evidence_text = Zusammenfassung der Fundstellen + Zitat + Dateipfad:Zeile
   ELSE:
     ergebnis = "nicht_gefunden"
     evidence_text = "Wiki-Suche ergab keine relevanten Treffer fuer Keywords: {keywords}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
routing = po
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Frage formalisieren + HiL-Prompt erstellen:

1. Frage-Praezisierung (maximal spezifisch):
   - Original-Frage: {FRAGE}
   - Kontext (Feature, PL-Item falls vorhanden)
   - Was genau muss der PO entscheiden?
   - Welche Optionen gibt es? (falls aus Code/Model ableitbar)
   - Welche Auswirkung hat die Entscheidung?

2. HiL-Prompt-Format erstellen:
   ┌─────────────────────────────────────────────────────┐
   │ ORAKEL: PO-Entscheidung erforderlich                │
   │                                                     │
   │ Feature: {NAME}                                     │
   │ Kontext: {PL-Item oder Analyse-Phase}               │
   │                                                     │
   │ Frage: {FRAGE_PRAEZISIERT}                          │
   │                                                     │
   │ Optionen:                                           │
   │   A) {Option A aus Code/Spec ableitbar}             │
   │   B) {Option B}                                     │
   │   C) Sonstiges (bitte beschreiben)                  │
   │                                                     │
   │ Auswirkung: {Was wird mit der Antwort gemacht}      │
   └─────────────────────────────────────────────────────┘

3. ergebnis = "placeholder" (HiL muss antworten)
   evidence_text = HiL-Prompt (zur Archivierung + spaeterer Nachverfolgung)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
routing = stakeholder
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Frage formalisieren + Evidence-Vorlage erstellen:

1. Entscheidungs-Kontext aufbereiten:
   - Wer ist der relevante Stakeholder? (aus Feature/Kontext ableiten)
   - Was ist der geschaeftliche Impact?
   - Gibt es Deadline oder Sprint-Einfluss?
   - Welche Abhaengigkeiten haengen an der Entscheidung?

2. Evidence-Vorlage erstellen (befuellbar durch User/Stakeholder):
   ┌─────────────────────────────────────────────────────┐
   │ STAKEHOLDER-ENTSCHEIDUNG ERFORDERLICH               │
   │                                                     │
   │ Frage: {FRAGE}                                      │
   │ Feature: {NAME}                                     │
   │ Stakeholder: {abgeleiteter Stakeholder-Typ}         │
   │                                                     │
   │ Kontext:                                            │
   │   {Kurze Beschreibung warum diese Entscheidung      │
   │    aus dem technischen Kontext heraus noetig ist}   │
   │                                                     │
   │ Impact:                                             │
   │   {Was passiert wenn Entscheidung NICHT getroffen}  │
   │                                                     │
   │ Entscheidung (ausfuellen):                          │
   │   [ ] Option A: ___________                        │
   │   [ ] Option B: ___________                        │
   │   [ ] Sonstiges: __________                        │
   │                                                     │
   │ Begruendung: _______________                        │
   │ Datum: _______________                              │
   └─────────────────────────────────────────────────────┘

3. ergebnis = "placeholder" (Stakeholder muss antworten)
   evidence_text = Entscheidungs-Vorlage (zur Archivierung)
```

### Schritt 3.5: QUESTION-Status Integration

```
Dieser Schritt greift WENN /_orakel aus SDF-Kontext aufgerufen wird
(Erkennungsmerkmale: PL-Item im Kontext, task_source=pl, OQ-Eskalation).

IF aufgerufen_aus_sdf UND pl_item_vorhanden:

  1. PL-Item identifizieren:
     - Lies {VAULT}/_parking-lot.md
     - Finde Item das dem aktiven Feature + der Frage entspricht

  2. PL-Item → [?] QUESTION markieren:
     Format: - [?] **[QUESTION] {Titel}** {Frage: {FRAGE_KURZ}. Orakel-Evidence: .claude/evidence/{DATUM}_{THEMA_SLUG}.md}
     Ersetze bestehende [ ] oder [STATUS: IN_ARBEIT] Zeile des Items

  3. Logge: "QUESTION-Status gesetzt fuer PL-Item: {Titel}"

  HINWEIS: BDF-SCANNING ignoriert [?]-Items (wie [~] FREEZE).
  Item wartet auf HiL-Klaerung. Nach HiL-Antwort: HiL setzt manuell
  auf [ ] zurueck → BDF nimmt es beim naechsten Lauf auf.

IF NICHT aus SDF-Kontext:
  Kein PL-Item-Update (direkter Aufruf ohne PL-Kontext)
```

### Schritt 4: Evidence archivieren

```
Dateiname: .claude/evidence/{DATUM}_{THEMA_SLUG}.md

FORMAT:
---
datum: {YYYY-MM-DD}
frage: "{FRAGE}"
routing: {routing}
feature: {NAME}
keywords: [{k1}, {k2}, {k3}]
ergebnis: gefunden | nicht_gefunden | placeholder
pl_item: {PL-Item-Titel oder "direkt" wenn kein PL-Kontext}
---

# Orakel Evidence: {THEMA}

## Frage
{FRAGE}

## Routing
{routing} — {Begruendung}

## Evidence
{Evidence-Text aus Schritt 3: Fundstellen + Zitat + Pfade ODER HiL-Prompt ODER Stakeholder-Vorlage}

## Fazit
{1-3 Saetze: Was ist die Antwort? Was bleibt offen?
 Bei placeholder: Was muss der Mensch entscheiden/recherchieren?}

## Quelle
{Quelle: Datei+Zeile (wiki), HiL-Prompt (po), Vorlage (stakeholder)}
```

### Schritt 5: Rueckfluss in Model

```
IF ergebnis == "gefunden" UND echte Erkenntnis vorhanden:
  Lese .claude/models/{NAME}_Model.md
  Bestimme naechste W{n}-Nummer
  Fuege W{n} ein:
    ## W{n}: Orakel-Erkenntnis — {THEMA}
    **Frage:** {FRAGE}
    **Antwort:** {Fazit aus Schritt 4}
    **Evidence:** .claude/evidence/{DATUM}_{THEMA_SLUG}.md
    **Status:** OFFEN (muss in naechstem SC-Zyklus bestaetigt werden)

ELSE (nicht_gefunden oder placeholder):
  Kein Model-Update (keine gesicherte Erkenntnis)
  Logge: "Kein W{n} angelegt — Evidence unvollstaendig (routing={routing}, ergebnis={ergebnis})"

Abschluss-Output:
  "ORAKEL DONE:
   Frage:    {FRAGE}
   Routing:  {routing}
   Evidence: .claude/evidence/{DATUM}_{THEMA_SLUG}.md
   Model W{n}: {angelegt | nicht angelegt (Begruendung)}
   QUESTION: {PL-Item markiert | kein PL-Kontext}"
```

---

## Bekannte Einschraenkungen (v1.0)

| Einschraenkung | Status | Ziel |
|----------------|--------|------|
| Kein Multi-Routing (nur 1 Quelle) | v1.0 | v1.1: parallele Quellen-Abfrage |
| Kein autonomer externer Wiki-Zugriff | v1.0 | v1.1: MCP-Integration fuer externe URLs |
| HiL-Antwort nicht automatisch eingepflegt | v1.0 | v1.1: auto-Resume nach HiL-Antwort |
| QUESTION-Auto-Resume nach HiL | v1.0 | v1.1: BDF-Trigger nach HiL-Antwort |

---

## Chain-Position

```
BDF → SDF → [QUESTION-Item] → **/_orakel** → Evidence-Archiv → Model W{n} → SDF weiter
                                    ↑
                            User (direkter Aufruf)
                                    ↑
                    /_A_orchestrate (SPEC-Readiness Gate, IF-7)
```

**Prev:** Kein Pflicht-Vorgaenger (Standalone). Typisch von BDF/SDF bei QUESTION-Items.
**Next:** Kein Pflicht-Nachfolger. Evidence steht in Archiv, Model hat neuen W{n}.

---

## Referenz

- PL-Item: IF-6 in `{VAULT}/_parking-lot.md`
- Evidence-Verzeichnis: `.claude/evidence/` (angelegt v1.0)
- QUESTION-Status: `{META}/sdf/pl-state-machine.md` (J3, Transitions-Matrix)
- Konvention: `{META}/commandKonvention/name-herleitung.md` (NAME-Fallback)
