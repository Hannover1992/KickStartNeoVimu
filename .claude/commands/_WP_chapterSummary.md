# /_WP_chapterSummary - Chapter Summary Generator

```yaml
status: active
version: 1.0.0
created: 2026-02-24
op: WritePaper
phase: Post-Synthesis
type: write
chain_position: post-synthesis
difficulty_scaling: false
mcp_critical: false
changelog: |
  v1.0: Initialer Entwurf. One-Shot Learning aus paperSummery.md.
        Liest final-draft.md, generiert strukturierte Kapitel-Zusammenfassung.
        Haengt Summary als letzte Sektion an final-draft.md.
        Schreibt Standalone-Summary fuer Schnell-Referenz.
```

---

```
+======================================================================+
| COMMAND: /_WP_chapterSummary                                         |
+======================================================================+
|                                                                        |
| ACTOR: SUMMARY WRITER (DU - direkt, kein Team)                       |
|                                                                        |
| ZWECK: Generiert eine strukturierte Kapitel-Zusammenfassung aus dem  |
|        fertigen Kapitel-Draft. Zwei Funktionen:                       |
|   1. SCHNELL-REFERENZ: Was wurde in diesem Kapitel behandelt?         |
|      → output/summary/chapter-{N}-summary.md                         |
|   2. KAPITEL-ABSCHLUSS: Letzte Sektion im Kapitel selbst             |
|      → An final-draft.md angehaengt (vor Literaturliste)             |
|                                                                        |
| POSITION IN PIPELINE:                                                  |
|   Task 11 (Synthesis) → [DIESER COMMAND] → Task 12 (PDF)            |
|                                                                        |
| ZWECK SUMMARY:                                                         |
|   - User kann schnell pruefen: "Hast du das Richtige geschrieben?"   |
|   - Kapitel endet mit klarer Zusammenfassung (akademische Konvention) |
|   - Dient als Quality-Signal: Summary lesen = Kapitel verstanden     |
|                                                                        |
| LIEST:                                                                 |
|   output/synthesis/chapter-{N}/final-draft.md  (PFLICHT)            |
|   output/models/chapter-{N}-model.md          (optional, Kontext)   |
|   config/project.yaml                          (Kapitel-Titel)       |
|                                                                        |
| SCHREIBT:                                                              |
|   output/summary/chapter-{N}-summary.md       (Standalone)          |
|   output/synthesis/chapter-{N}/final-draft.md (APPEND: letzter Abschnitt)  |
+======================================================================+
```

---

## Aufruf

```
/_WP_chapterSummary [chapter_number]
```

**Parameter:**

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `chapter_number` | (aus Manifest) | Welches Kapitel |

---

## Ablauf

### Schritt 1: Inputs lesen

1. Lies `output/synthesis/chapter-{N}/final-draft.md` → Kapitelinhalt
2. Lies `output/models/chapter-{N}-model.md` → Themen/Sections (falls vorhanden)
3. Lies `config/project.yaml` → `chapters[N].title` fuer Kapitel-Ueberschrift

Pruefe: Hat final-draft.md bereits eine `## Zusammenfassung` oder `## Summary`
Sektion? Falls ja → SKIP (nichts doppelt schreiben), melde dem Aufrufer.

### Schritt 2: Summary generieren

**FORMAT (One-Shot-Learning aus paperSummery.md):**

```markdown
---

## Kapitel-Zusammenfassung

Dieser Abschnitt gibt einen kompakten Ueberblick ueber die wesentlichen
Erkenntnisse von Kapitel {N}: **{Kapitel-Titel}**.

### 1. {Haupt-Thema 1}

* **{Unterpunkt A}:** {1-2 Saetze Kernaussage}
* **{Unterpunkt B}:** {1-2 Saetze Kernaussage}
* **{Unterpunkt C}:** {1-2 Saetze Kernaussage}

### 2. {Haupt-Thema 2}

* **{Unterpunkt A}:** {1-2 Saetze Kernaussage}
* **{Unterpunkt B}:** {1-2 Saetze Kernaussage}

### 3. {Haupt-Thema 3}

...

---

### Synthese

{2-3 Saetze: Was ist das Kernergebnis dieses Kapitels?
Was wird damit im naechsten Kapitel aufgebaut?}

### Identifizierte Forschungsluecken

* **{Luecke 1}:** {1 Satz}
* **{Luecke 2}:** {1 Satz}

> **Fazit:** {1 praegnanter Satz der den Beitrag dieses Kapitels zur
> Gesamtarbeit beschreibt. Format: "Die [Methode/Analyse] liefert
> [Ergebnis], das in Kapitel [N+1] als Grundlage fuer [naechstes Thema]
> dient."}
```

**REGELN fuer die Summary-Generierung:**
- Pro Haupt-Thema: 2-4 Bullet-Points, jeder 1-2 Saetze
- Keine neuen Argumente einfuehren — NUR was im Kapitel steht zusammenfassen
- Forschungsluecken NUR aus dem Kapitel extrahieren (nicht erfinden)
- Fazit-Satz verbindet mit dem naechsten Kapitel (Kontinuitaet)
- Sprache: Deutsch (wie das Kapitel selbst)
- Laenge: 300-500 Woerter

### Schritt 3: Standalone-Summary schreiben

Erstelle `output/summary/chapter-{N}-summary.md`:

```markdown
# Zusammenfassung: Kapitel {N} - {Titel}

**Erstellt:** {DATUM}
**Status:** Generiert aus final-draft.md

{VOLLSTAENDIGE SUMMARY aus Schritt 2}
```

Erstelle Verzeichnis `output/summary/` falls nicht vorhanden.

### Schritt 4: An final-draft.md anhaengen

Haenge die Summary (Schritt 2) ANS ENDE von `output/synthesis/chapter-{N}/final-draft.md`.

WICHTIG: Vor dem Literaturverzeichnis (`## Literatur` / `## References`),
falls vorhanden. Sonst ganz ans Ende.

Trennzeichen vor Summary:
```
---
```

### Schritt 5: Manifest aktualisieren

Aktualisiere `_manifest.md`:
```
WP_PIPELINE_STATE.stufe: "chapterSummary"
WP_PIPELINE_STATE.resume_zaehler.chapterSummary: +1
```

### Schritt 6: Ergebnis melden

```
OUTPUT:
"═══════════════════════════════════════════════════════
 Chapter Summary: Kapitel {N} - {Titel}
 ═══════════════════════════════════════════════════════

 Standalone:  output/summary/chapter-{N}-summary.md
 Im Kapitel:  output/synthesis/chapter-{N}/final-draft.md (angehaengt)

 Themen abgedeckt: {N} Hauptthemen
 Woerter:     {count}

 Naechster Schritt: /_WP_chapterPDF {N}
 ═══════════════════════════════════════════════════════"
```

---

## Quality-Signal

Die Summary dient als schnelles Quality-Signal:

**Frage:** Liest der User die Summary und denkt "das ist das Kapitel"?
- **JA** → Kapitel gut geschrieben, Weiter zu PDF
- **NEIN** → Kapitel verfehlt Ziel, zurueck zu /_WP_write oder /_WP_synthesis

Der User kann die Summary lesen **BEVOR** er das volle Kapitel liest, um
schnell zu pruefen ob der richtige Inhalt behandelt wurde.

---

## Fehlerbehandlung

| Fehler | Aktion |
|--------|--------|
| final-draft.md fehlt | STOP: "Bitte zuerst /_WP_synthesis ausfuehren." |
| Summary bereits vorhanden | SKIP: Melde "Summary bereits vorhanden in final-draft.md" |
| chapter-{N}-model.md fehlt | Weiter ohne Model (nur aus final-draft.md) |
| output/summary/ existiert nicht | mkdir -p, dann weiter |

---

ARGUMENTS: $ARGUMENTS
