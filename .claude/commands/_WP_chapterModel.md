# /_WP_chapterModel - Chapter Knowledge Model

```yaml
status: active
version: 1.0.0
created: 2026-02-08
op: WritePaper
phase: Knowledge
type: building-block
chain_position: chapterModel
difficulty_scaling: true
mcp_critical: false
```

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_WP_chapterModel                                            ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: KNOWLEDGE SYNTHESIZER                                             ║
║   TUT:                                                                   ║
║     - Assessment-JSON lesen (Keywords, Coverage, Chunks)                ║
║     - Keywords nach semantischer Aehnlichkeit zu Themen clustern        ║
║     - Themen zu Sections zuordnen (Section-Mapping)                     ║
║     - BibTeX-Referenzen pro Thema aggregieren                           ║
║     - Kapitel-Model als Markdown-Datei generieren                       ║
║   NICHT:                                                                 ║
║     - RAG-Queries ausfuehren (→ assess)                                 ║
║     - Neue Quellen suchen (→ discovery)                                  ║
║     - Kapitel schreiben (→ write)                                        ║
║     - Luecken bewerten (→ chapterGap)                                   ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md (current_chapter, phase)                               ║
║   2. session-state.json (chapter_keywords, coverage_score)              ║
║   3. output/assess/chapter-{N}-assessment.json (Keywords, Chunks)       ║
║   4. output/chapter-structure.md (Sections fuer current_chapter)        ║
║   5. output/references.bib (BibTeX-Keys fuer Validierung)              ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. output/models/chapter-{N}-model.md (Themen, Keywords, Referenzen) ║
║   2. _manifest.md (UPDATE: next_step=chapterGap, model_complete)        ║
║   3. session-state.json (UPDATE: model_complete, themes_count)          ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LINEAR                                                           ║
║   AFTER: /_WP_assess (Coverage gut, >= 0.85)                          ║
║          /_WP_discovery (Luecken gefuellt, nach Gap-Loop)             ║
║   BEFORE: /_WP_chapterGap                                             ║
║   PHASE: Knowledge                                                      ║
║   CHAIN: [assess|discovery] → [chapterModel] → [chapterGap]            ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   easy:   3 Themen/Kapitel, einfaches Clustering                        ║
║   normal: 5 Themen/Kapitel, regelbasiertes Clustering                   ║
║   hard:   8 Themen/Kapitel, semantisches Clustering                     ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper Kapitel {N} Model erstellt:   ║
║   {M} Themen'"                                                          ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: chapterModel                                                     ║
║   op: WritePaper                                                         ║
║   chapter: {N}                                                           ║
║   chain-position: chapterModel                                           ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

**TUT (Claude):**
- Liest chapter-{N}-assessment.json fuer Keywords, Coverage, Chunk-Daten
- Clustert Keywords nach semantischer Aehnlichkeit (regelbasiert: gemeinsame Wortstamm-Erkennung)
- Erstellt Themen-Liste mit Keywords, Chunk-Counts, BibTeX-Keys
- Ordnet Themen den Sections aus chapter-structure.md zu
- Validiert BibTeX-Keys gegen output/references.bib
- Generiert output/models/chapter-{N}-model.md als strukturiertes Kapitel-Wissensmodell
- Aktualisiert _manifest.md und session-state.json

**TUT NICHT (Claude):**
- RAG-Queries ausfuehren (das macht `/_WP_assess`)
- Neue Quellen suchen oder ingestieren (das macht `/_WP_research` + `/_WP_discovery`)
- Kapitel-Text schreiben (das macht `/_WP_write`)
- Luecken identifizieren oder bewerten (das macht `/_WP_chapterGap`)
- MCP-Tools aufrufen (dieser Command ist MCP-frei)

**ESKALATION:**
- assessment.json fehlt → STOP + empfehle `/_WP_assess` zuerst
- coverage_score < 0.50 → WARNUNG "Sehr niedrige Coverage, Model-Qualitaet eingeschraenkt"
- references.bib fehlt → WARNUNG + Model ohne BibTeX-Validierung erstellen
- 0 Keywords in assessment.json → STOP + empfehle `/_WP_assess` wiederholen

---

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Alle Assessment-Daten und Kontext laden

**Aktionen:**
1. Lies `_manifest.md` → `current_chapter` (z.B. 1), `phase`, `next_step`
2. Lies `session-state.json` → `chapter_keywords`, `coverage_score`
3. Lies `output/assess/chapter-{N}-assessment.json` → Keywords, Chunks, Coverage pro Section
4. Lies `output/chapter-structure.md` → Section-Titel und -Beschreibungen fuer Kapitel {N}
5. Lies `output/references.bib` → Alle BibTeX-Keys fuer Validierung

**Validierung:**
- `next_step` muss `chapterModel` sein → sonst FEHLER
- assessment.json muss `keywords_total > 0` haben → sonst FEHLER
- coverage_score aus assessment.json nehmen (autoritativ)

**Erfolgskriterium:**
- Alle 5 Input-Dateien gelesen
- Keywords mit Coverage-Daten vorhanden
- Sections fuer aktuelles Kapitel bekannt

---

### Schritt 1: Themen-Clustering

**Ziel:** Keywords nach semantischer Aehnlichkeit zu Themen gruppieren

**Aktionen:**
1. Bestimme `max_themes` aus `difficulty`:
   - easy: 3 Themen
   - normal: 5 Themen
   - hard: 8 Themen
2. Extrahiere alle Keywords aus assessment.json (ueber alle Sections)
3. Clustere Keywords nach Aehnlichkeit:

   **Clustering-Algorithmus (regelbasiert):**
   ```
   Pro Keyword-Paar:
     IF gemeinsamer Wortstamm (z.B. "test" in "testing" und "test-driven"):
       → Gleicher Cluster
     IF semantisch verwandt (z.B. "refactoring" und "code smell"):
       → Gleicher Cluster (manuelles Domain-Mapping)
     IF Section-Nachbarschaft (gleiche oder benachbarte Section):
       → Cluster-Bonus (bevorzugt zusammen)
   ```

4. Limitiere auf `max_themes` Cluster (kleinste Cluster mergen)
5. Pro Cluster: Bestimme Theme-Name (haeufigster Keyword oder Domain-Begriff)

**Ergebnis:**
```json
[
  {
    "theme_id": "T1",
    "theme_name": "Clean Code Principles",
    "keywords": ["clean code", "readability", "maintainability"],
    "total_chunks": 18,
    "coverage_status": "COVERED"
  },
  {
    "theme_id": "T2",
    "theme_name": "Test-Driven Development",
    "keywords": ["TDD", "test-driven", "red-green-refactor"],
    "total_chunks": 5,
    "coverage_status": "PARTIAL"
  }
]
```

**Erfolgskriterium:**
- Mindestens 2 Themen extrahiert
- Kein Keyword ohne Cluster-Zuordnung
- Cluster-Groesse >= 2 Keywords (ausser Einzelgaenger)

---

### Schritt 2: Section-Mapping

**Ziel:** Themen den Kapitel-Sections zuordnen

**Aktionen:**
1. Pro Section in chapter-structure.md:
   - Matche Section-Titel gegen Theme-Keywords
   - Berechne Relevanz-Score (Keyword-Overlap)
2. Pro Thema: Ordne 1-3 primaere Sections zu
3. Erstelle Section-Theme-Matrix:
   ```
   Section 1.1 → [T1: Clean Code, T3: SOLID Principles]
   Section 1.2 → [T2: TDD, T4: Quality Assurance]
   Section 1.3 → [T1: Clean Code, T5: Refactoring]
   Section 1.4 → [T3: SOLID Principles]
   ```
4. Validiere: Jede Section hat mindestens 1 Thema

**Erfolgskriterium:**
- Jede Section hat mindestens 1 zugeordnetes Thema
- Jedes Thema hat mindestens 1 zugeordnete Section
- Keine verwaisten Sections oder Themen

---

### Schritt 3: Referenz-Aggregation

**Ziel:** BibTeX-Keys pro Thema sammeln und validieren

**Aktionen:**
1. Pro Thema: Sammle BibTeX-Keys aus assessment.json Chunks
   - Keys kommen aus den RAG-Query-Ergebnissen (Chunk-Metadaten)
2. Pro BibTeX-Key: Validiere gegen output/references.bib
   - Key existiert → "VALID"
   - Key nicht gefunden → "UNVERIFIED" (Chunk-Metadaten inkonsistent)
3. Pro Thema: Erstelle Referenz-Liste:
   ```json
   {
     "theme": "Clean Code Principles",
     "references": [
       {"key": "Martin2008", "status": "VALID", "chunks": 8},
       {"key": "Fowler2018", "status": "VALID", "chunks": 5},
       {"key": "McConnell2004", "status": "UNVERIFIED", "chunks": 2}
     ]
   }
   ```
4. Berechne `references_coverage`: VALID / (VALID + UNVERIFIED)

**Erfolgskriterium:**
- Jedes Thema hat mindestens 1 BibTeX-Referenz
- VALID-Referenzen > 50% pro Thema
- UNVERIFIED-Keys dokumentiert (nicht geloescht)

---

### Schritt 4: Model-Generierung

**Ziel:** Strukturiertes Kapitel-Model als Markdown erstellen

**Aktionen:**
1. Schreibe `output/models/chapter-{N}-model.md`:

```markdown
---
chapter: {N}
title: "{Kapitel-Titel}"
model_date: "2026-02-08"
difficulty: "normal"
coverage_score: 0.78
themes_count: 5
sections_count: 4
references_count: 12
---

# Kapitel-Model: {Kapitel-Titel}

## Meta
- **Coverage Score:** 0.78
- **Themes:** 5
- **References:** 12 (10 VALID, 2 UNVERIFIED)
- **Gap Status:** MODERATE (3 Keywords unter min_coverage)

---

## Section 1.1: Motivation und Kontext

### Themen
1. **Clean Code Principles** (Coverage: COVERED, 8 Chunks)
   - Keywords: clean code, readability, maintainability
   - Referenzen: Martin2008, Fowler2018

2. **SOLID Principles** (Coverage: COVERED, 6 Chunks)
   - Keywords: SOLID, single responsibility, dependency inversion
   - Referenzen: Martin2003, Martin2008

### Schreib-Leitlinie
- Hauptfokus: Clean Code Principles (staerkste Coverage)
- Sekundaer: SOLID Principles (Vertiefung)
- Empfohlene Struktur: Definition → Beispiele → Relevanz

---

## Section 1.2: Forschungsfragen
[... analog ...]

---

## Referenzen-Zusammenfassung

| BibTeX-Key | Themen | Chunks | Status |
|------------|--------|--------|--------|
| Martin2008 | T1, T3 | 8 | VALID |
| Fowler2018 | T1, T5 | 5 | VALID |
| Beck2003 | T2 | 3 | VALID |
| McConnell2004 | T1 | 2 | UNVERIFIED |

---

## Gap-Uebersicht

| Keyword | Section | Status | Deficit |
|---------|---------|--------|---------|
| test-driven development | 1.2 | PARTIAL | 2 Chunks |
| empirical validation | 1.3 | MISSING | 3 Chunks |
```

**Erfolgskriterium:**
- Model-Datei ist vollstaendig und strukturiert
- YAML-Frontmatter mit Meta-Daten
- Pro Section: Themen, Keywords, Referenzen, Schreib-Leitlinie
- Referenzen-Zusammenfassung als Tabelle
- Gap-Uebersicht (falls Gaps vorhanden)

---

### Schritt 5: State aktualisieren

**Ziel:** Model-Status in Manifest und Session-State speichern

**Aktionen:**
1. Update `_manifest.md`:
   ```markdown
   ## Chapter Model Status - Kapitel {N}
   - **Model:** output/models/chapter-{N}-model.md
   - **Themes:** 5
   - **References:** 12
   - **Coverage:** 0.78
   - **Next Step:** chapterGap
   ```
2. Update `session-state.json`:
   ```json
   {
     "last_command": "_WP_chapterModel",
     "model_complete": true,
     "themes_count": 5,
     "references_count": 12,
     "references_valid": 10,
     "references_unverified": 2,
     "next_step": "chapterGap"
   }
   ```
3. **NOTIFY:**
   ```powershell
   powershell -Command "notify 'WritePaper Kapitel {N} Model erstellt: 5 Themen'"
   ```

**Erfolgskriterium:**
- model_complete=true in session-state.json
- next_step=chapterGap gesetzt
- NOTIFY gesendet

---

## Output-Format

### output/models/chapter-{N}-model.md

**Zweck:** Strukturiertes Wissensmodell als Basis fuer chapterGap und write

**Aufbau:**
1. YAML-Frontmatter (Meta-Daten)
2. Pro Section: Themen mit Keywords + Referenzen + Schreib-Leitlinie
3. Referenzen-Zusammenfassung (Tabelle)
4. Gap-Uebersicht (falls Gaps vorhanden)

**Konsumenten:**
- `/_WP_chapterGap`: Prueft Model gegen Coverage-Anforderungen
- `/_WP_write`: Nutzt Themen + Referenzen + Schreib-Leitlinien fuer Kapitel-Text

---

## Qualitaetskriterien

### MUSS-Kriterien
- [ ] Alle Sections aus chapter-structure.md im Model enthalten
- [ ] Jede Section hat mindestens 1 Thema
- [ ] Jedes Thema hat Keywords + mindestens 1 BibTeX-Referenz
- [ ] YAML-Frontmatter vollstaendig (chapter, title, coverage_score, themes_count)
- [ ] output/models/chapter-{N}-model.md existiert
- [ ] _manifest.md und session-state.json aktualisiert

### SOLL-Kriterien
- [ ] Schreib-Leitlinie pro Section (Fokus, Sekundaer, Struktur)
- [ ] Referenzen gegen references.bib validiert
- [ ] Gap-Uebersicht falls Gaps vorhanden
- [ ] Themen-Coverage pro Section berechnet

### KANN-Kriterien
- [ ] Semantisches Clustering bei hard-Modus
- [ ] Cross-Section Themen-Referenzen (Thema in mehreren Sections)
- [ ] Empfohlene Seitenverteilung pro Section

---

## NOTIFY

**Success:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Model erstellt: {M} Themen'"
```

**Warning:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Model: Niedrige Coverage ({X}%)'"
```

**Error:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Model FAILED: Assessment fehlt'"
```

---

## Error Handling

- assessment.json fehlt → BLOCKING STOP + ESKALATION, empfehle /_WP_assess
- 0 Keywords → BLOCKING STOP + ESKALATION, Assessment war leer
- references.bib fehlt → NON-BLOCKING WARNUNG, Model ohne BibTeX-Validierung
- coverage_score < 0.50 → NON-BLOCKING WARNUNG, Model-Qualitaet eingeschraenkt
- Section ohne Keywords → FALLBACK: Section mit "KEINE DATEN" markieren

---

## Hinweise

### Kein MCP
- Dieser Command ruft KEINE MCP-Tools auf
- Alle Daten kommen aus lokalen Dateien (assessment.json, chapter-structure.md, references.bib)
- Budget-schonend im Gap-Loop (kein MCP-Verbrauch)

### Clustering-Strategie
- easy: Einfaches Wortstamm-Matching (z.B. "test" → "testing", "test-driven")
- normal: Regelbasiert mit Domain-Mapping (z.B. "refactoring" ↔ "code smell")
- hard: Semantisches Clustering (Kontext-basiert, aehnliche Chunk-Zuordnungen)

### Chain-Integration
- chapterModel ist ZWISCHEN assess (oder discovery) und chapterGap
- Model ist INPUT fuer chapterGap (Coverage-Pruefung pro Section)
- Model ist INPUT fuer write (Themen + Referenzen + Schreib-Leitlinien)
- LOOP-LEVEL: LINEAR (wird bei Gap-Loop erneut aufgerufen mit neuen assessment.json Daten)
