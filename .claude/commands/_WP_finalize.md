---
status: active
version: 1.0
created: 2026-02-11
updated: 2026-02-11
author: Command-System
tags: [research, writepaper, publish, finalize, latex, pdf]
---

# /_WP_finalize - Paper Finalization & Publication

```
+======================================================================+
| VERTRAG: /_WP_finalize                                             |
+======================================================================+
|                                                                      |
| ACTOR: PAPER FINALIZATION & PUBLICATION                              |
|   TUT:                                                               |
|     - Alle chapter-{N}/final-draft.md aus synthesis lesen           |
|     - references.bib und PaperReference.tex lesen                    |
|     - Markdown -> LaTeX via Pandoc (Fallback: sed/regex per M7)     |
|     - LaTeX-Kompilierung: pdflatex + bibtex (Multi-Pass)            |
|     - PDF-Split via pdftk (1 PDF -> N Kapitel-PDFs)                 |
|     - Optional: research_verify als letzter Qualitaets-Check        |
|     - Publish: Copy zu config/output_directory                       |
|     - finalize-report.json generieren (Metriken, Warnings)          |
|   NICHT:                                                             |
|     - Kapitel schreiben oder aendern (-> write, autoGen)             |
|     - Qualitaetsbewertung durchfuehren (-> qualityGate)             |
|     - Figures generieren (-> visual, bereits vorhanden)              |
|     - Research durchfuehren (-> research, discovery)                 |
|     - User-Interaktion / Kapitel-Feedback (-> reflect)               |
|   ESKALIERT:                                                         |
|     - LaTeX-Compilation Error -> STOP + Log + Zeige Fehler          |
|     - references.bib fehlt oder leer -> STOP + empfehle research    |
|     - Pandoc nicht verfuegbar -> FALLBACK sed + WARNUNG (M7)        |
|     - pdftk nicht verfuegbar -> FALLBACK qpdf + WARNUNG (M7)       |
|     - pdflatex nicht verfuegbar -> FALLBACK xelatex (M7)            |
|     - Compilation >Timeout -> ABORT + partial Output                 |
|                                                                      |
| LIEST (Input) - PFLICHT:                                             |
|   1. _manifest.md (all_chapters, total_chapters, paper_title)       |
|   2. session-state.json (difficulty, paper_metadata)                 |
|   3. config/project.yaml (title, author, output_directory)           |
|   4. output/synthesis/chapter-{N}/final-draft.md (alle N Kapitel)   |
|   5. output/references/references.bib (BibTeX Entries)               |
|   6. .claude/reference/PaperReference.tex (LaTeX-Template)           |
|   7. output/figures/*.{png,pdf} (alle generierten Figures)           |
|   8. output/reflection/chapter-{N}/reflection-report.json (Stats)   |
|                                                                      |
| SCHREIBT (Output) - PFLICHT:                                         |
|   1. output/latex/paper.tex (vollstaendiges LaTeX-Dokument)         |
|   2. output/latex/paper.pdf (kompiliertes PDF)                       |
|   3. output/publish/paper.pdf (finales Published PDF)                |
|   4. output/publish/chapters/chapter-{N}.pdf (Split-PDFs)           |
|   5. output/publish/finalize-report.json (Metriken + Warnings)      |
|   6. _manifest.md (UPDATE: finalize_status, pdf_path, warnings)     |
|   7. session-state.json (UPDATE: finalize_timestamp, total_pages)   |
|                                                                      |
| POSITION:                                                            |
|   TYPE: LINEAR                                                       |
|   AFTER: /_WP_reflect (letztes Kapitel ACCEPTED)                   |
|   BEFORE: END (Pipeline abgeschlossen)                               |
|   PHASE: Publish                                                     |
|   CHAIN: [reflect(last)] -> [finalize] -> [END]                     |
|                                                                      |
| SCHWIERIGKEIT:                                                       |
|   | Dimension            | easy   | normal       | hard             |
|   |----------------------|--------|--------------|------------------|
|   | Pandoc Flags         | basic  | +toc         | +toc+biblatex    |
|   | LaTeX Passes         | 2      | 3            | 4                |
|   | PDF Split            | nein   | ja (pdftk)   | ja (pdftk/qpdf)  |
|   | research_verify      | nein   | nein         | ja (MCP 1 Call)  |
|   | Compilation Timeout  | 2 min  | 5 min        | 10 min           |
|                                                                      |
| NOTIFY:                                                              |
|   SUCCESS: "WritePaper FINALIZED: {pages}p, {output_path}"          |
|   WARNING: "WritePaper FINALIZED with {N} warnings"                  |
|   ERROR:   "WritePaper FINALIZE FAILED: {error_type}"                |
|                                                                      |
| TAGS:                                                                |
|   type: finalize                                                     |
|   op: WritePaper                                                     |
|   chain-position: finalize                                           |
|   prev: "[[WritePaper-reflect]]"                                     |
|   next: END                                                          |
+======================================================================+
```

---

## Verantwortlichkeit

### TUT (Kernaufgabe)
- Alle final-draft.md Dateien aus output/synthesis/ sammeln
- references.bib und LaTeX-Template laden
- Markdown zu LaTeX konvertieren (Pandoc primaer, sed Fallback)
- LaTeX zu PDF kompilieren (pdflatex primaer, xelatex Fallback)
- PDF in Kapitel splitten (pdftk primaer, qpdf Fallback)
- Optional: research_verify als finaler Anti-Halluzinations-Check (nur hard)
- finalize-report.json mit Metriken generieren
- State-Update nach M6-Reihenfolge (OUTPUT -> Manifest -> State -> NOTIFY)

### TUT NICHT (Out of Scope)
- Kapitel schreiben oder ueberarbeiten (das macht /_WP_write + /_WP_autoGen)
- Qualitaet bewerten (das macht /_WP_qualityGate)
- Figures generieren (das macht /_WP_visual)
- Quellen recherchieren (das macht /_WP_research + /_WP_discovery)
- User-Feedback einholen (das macht /_WP_reflect)

### Eskalation
- **BLOCKING:** LaTeX-Compilation Error -> STOP + paper.log parsen + Fehlerzeile anzeigen
- **BLOCKING:** references.bib fehlt oder leer -> STOP + empfehle `/_WP_research`
- **BLOCKING:** Alle final-draft.md fehlen -> STOP + empfehle Pipeline-Neustart
- **FALLBACK (M7):** Pandoc fehlt -> sed/regex Conversion (reduzierte Qualitaet)
- **FALLBACK (M7):** pdflatex fehlt -> xelatex (alternative Engine)
- **FALLBACK (M7):** pdftk fehlt -> qpdf (alternative Split-Engine)
- **NON-BLOCKING:** Einzelne Figure fehlt -> LaTeX-Placeholder + WARNUNG
- **NON-BLOCKING:** research_verify FAIL -> Continue (Paper bereits durch Gate 7)

---

## Ablauf

### Schritt 0: Inputs sammeln und validieren

**Ziel:** Alle Kapitel-Drafts, Metadata und Config laden

**Aktionen:**
1. Lese `_manifest.md` -> `total_chapters`, `paper_title`, Chapter-Status
2. Lese `session-state.json` -> `difficulty`, `paper_metadata`
3. Lese `config/project.yaml` -> `title`, `author`, `output_directory`
4. Pro Kapitel N=1..total_chapters:
   - Lese `output/synthesis/chapter-{N}/final-draft.md` -> Content
   - Lese `output/reflection/chapter-{N}/reflection-report.json` -> Stats
5. Lese `output/references/references.bib` -> BibTeX Entries
6. Lese `.claude/reference/PaperReference.tex` -> LaTeX-Template
7. Scanne `output/figures/` -> Liste aller *.png, *.pdf Dateien

**Validierung:**
- Alle total_chapters final-draft.md MUESSEN existieren -> sonst BLOCKING STOP
- references.bib MUSS existieren und >= 1 Entry -> sonst BLOCKING STOP
- PaperReference.tex MUSS existieren -> sonst FALLBACK zu Minimal-Template:
  ```latex
  \documentclass[12pt,a4paper]{article}
  \usepackage[utf8]{inputenc}
  \usepackage{natbib}
  \begin{document}
  {{CONTENT}}
  \end{document}
  ```
- output/figures/ optional (Warnung bei fehlenden [FIGURE: ...] Referenzen)

**Erfolgskriterium:**
- [ ] Alle N Kapitel geladen
- [ ] BibTeX Entries >= 1
- [ ] LaTeX-Template verfuegbar (oder Fallback aktiv)

---

### Schritt 1: Markdown -> LaTeX Conversion

**Ziel:** Alle Kapitel-Drafts zu einem LaTeX-Dokument zusammenfuehren

**M7 Fallback-Kette:** Pandoc -> sed/regex -> BLOCKING STOP

**Methode PRIMAER (Pandoc):**
```bash
pandoc -f markdown -t latex \
  --bibliography=output/references/references.bib \
  --citeproc --natbib \
  -o output/latex/chapter-{N}.tex \
  output/synthesis/chapter-{N}/final-draft.md
```

**Difficulty-Dependent Flags:**
- **easy:** Basic (`-f markdown -t latex`)
- **normal:** `--toc` (Table of Contents)
- **hard:** `--toc --biblatex` (BibLaTeX statt natbib)

**Methode FALLBACK (sed/regex, falls Pandoc fehlt):**
- `# Title` -> `\section{Title}`
- `## Subtitle` -> `\subsection{Subtitle}`
- `### Sub` -> `\subsubsection{Sub}`
- `\cite{key}` bleibt erhalten (LaTeX-native)
- `[FIGURE: desc]` -> `\begin{figure}[htbp]\centering\includegraphics[width=0.8\textwidth]{../figures/{desc}}\end{figure}`
- **WARNUNG:** "Pandoc fehlt, Fallback sed verwendet (reduzierte Qualitaet)"

**LaTeX zusammenfuehren:**
```latex
% Preamble aus PaperReference.tex (mit Platzhalter-Ersetzung)
% {{TITLE}} -> paper_title
% {{AUTHOR}} -> author
% {{DATE}} -> Aktuelles Datum
\begin{document}
\maketitle
\tableofcontents  % nur bei normal/hard
\input{chapter-1.tex}
\input{chapter-2.tex}
...
\input{chapter-{N}.tex}
\bibliographystyle{plain}
\bibliography{../references/references}
\end{document}
```

**Erfolgskriterium:**
- [ ] output/latex/paper.tex generiert
- [ ] Alle \input{chapter-{N}.tex} vorhanden
- [ ] BibTeX korrekt referenziert

---

### Schritt 2: LaTeX -> PDF Compilation

**Ziel:** PDF via pdflatex erzeugen (Multi-Pass)

**M7 Fallback-Kette:** pdflatex -> xelatex -> BLOCKING STOP

**Pre-Flight Check:**
```bash
# Pruefe ob LaTeX-Engine verfuegbar ist
pdflatex --version || xelatex --version || { echo "BLOCKING: Keine LaTeX-Engine"; exit 1; }
```

**Pass-Schema nach Difficulty:**

| Pass | easy | normal | hard |
|------|------|--------|------|
| 1 | pdflatex | pdflatex | pdflatex |
| 2 | pdflatex | bibtex | bibtex |
| 3 | - | pdflatex | pdflatex |
| 4 | - | - | pdflatex |

**Compilation mit Timeout:**
```bash
cd output/latex
timeout {timeout_seconds} pdflatex -interaction=nonstopmode paper.tex
bibtex paper       # nur bei normal/hard
timeout {timeout_seconds} pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex   # nur bei hard (4. Pass)
```

**Timeout nach Difficulty:**
- easy: 120s (2 min)
- normal: 300s (5 min)
- hard: 600s (10 min)

**Error-Handling:**
- **Exit-Code != 0:** Parse paper.log, extrahiere Fehlerzeile, BLOCKING STOP
  Beispiel: `! Undefined control sequence. l.42 \invalidcommand`
- **Timeout:** ABORT + NOTIFY Error "Compilation Timeout nach {timeout}s"
- **Missing Figure:** WARNUNG + Continue (LaTeX fuegt Platzhalter ein)
- **BibTeX Fehler:** BLOCKING STOP + Zeige paper.blg Log

**Erfolgskriterium:**
- [ ] output/latex/paper.pdf existiert
- [ ] PDF hat >= N Seiten (mindestens 1 pro Kapitel)
- [ ] 0 Compilation-Errors

---

### Schritt 3: PDF Split (Difficulty: normal/hard)

**Ziel:** 1 PDF -> N Kapitel-PDFs

**Bedingung:** NUR bei normal/hard difficulty. Bei easy: SKIP.

**M7 Fallback-Kette:** pdftk -> qpdf -> SKIP + WARNUNG

**Seiten-Range-Erkennung:**
1. Lies paper.aux -> Extrahiere `\newlabel{chap:N}{{}{Page}}`
2. Berechne Start/End-Seiten pro Kapitel
3. Validierung: Summe aller Kapitel-Seiten == Total-Seiten

**Split via pdftk (primaer):**
```bash
pdftk output/latex/paper.pdf cat {start}-{end} \
  output output/publish/chapters/chapter-{N}.pdf
```

**Split via qpdf (fallback):**
```bash
qpdf output/latex/paper.pdf --pages . {start}-{end} -- \
  output/publish/chapters/chapter-{N}.pdf
```

**Fallback bei beiden fehlen:**
- SKIP Split
- WARNUNG: "Kein PDF-Split-Tool verfuegbar, nur Haupt-PDF"
- Nur output/publish/paper.pdf verfuegbar

**Erfolgskriterium:**
- [ ] N Split-PDFs in output/publish/chapters/ (falls nicht uebersprungen)
- [ ] Summe Split-Pages == Total-Pages (Validierung)

---

### Schritt 4: Optional research_verify (Difficulty: hard)

**Ziel:** Letzter Anti-Halluzinations-Check

**Bedingung:** NUR bei difficulty=hard. Bei easy/normal: SKIP.

**MCP-Aufruf:**
```
mcp__cleancoder__research_verify(
  project_path = "{project_path}",
  latex_file = "output/latex/paper.tex",
  options = {
    "verify_content": true,
    "strict_mode": false,
    "include_context": true
  }
)
```

**Verarbeitung:**
- Status "verified" -> PASS (alle Citations verifiziert)
- Status "partial" -> WARNUNG + Liste unverified Citations
- Status "failed" -> WARNUNG + Continue (NON-BLOCKING)

**Begruendung:** research_verify ist NON-BLOCKING weil Paper bereits durch
qualityGate Gate 7 (RAG-Verify) gegangen ist. Dieser Check ist zusaetzliche Sicherheit.

**Erfolgskriterium:**
- [ ] research_verify aufgerufen (nur hard)
- [ ] Ergebnis in finalize-report.json dokumentiert

---

### Schritt 5: Publish (Copy & Report)

**Ziel:** PDF zu Ziel-Ordner kopieren, Report generieren

**5a. Dateien kopieren:**
```powershell
Copy-Item output/latex/paper.pdf output/publish/paper.pdf
# Split-PDFs bereits in Schritt 3 nach output/publish/chapters/ geschrieben
```

**5b. finalize-report.json generieren:**
```json
{
  "timestamp": "2026-02-11T10:00:00Z",
  "difficulty": "normal",
  "total_chapters": 5,
  "total_pages": 87,
  "total_words": 32500,
  "total_citations": 215,
  "compilation_time_seconds": 42.3,
  "latex_passes": 3,
  "conversion_method": "pandoc",
  "pdf_split": true,
  "split_tool": "pdftk",
  "research_verify": {
    "enabled": false,
    "status": null
  },
  "fallbacks_used": [],
  "warnings": [],
  "errors": [],
  "output_files": {
    "main_pdf": "output/publish/paper.pdf",
    "chapter_pdfs": ["output/publish/chapters/chapter-1.pdf", "..."],
    "latex_source": "output/latex/paper.tex"
  }
}
```

**5c. Aggregate Stats:**
- total_pages: Aus PDF Metadata (`pdfinfo paper.pdf | grep Pages`)
- total_words: Summe aus reflection-report.json aller Kapitel
- total_citations: Count `\cite{` in paper.tex

**Erfolgskriterium:**
- [ ] paper.pdf in output/publish/
- [ ] finalize-report.json generiert mit allen Metriken

---

### Schritt 6: State aktualisieren (M6 Reihenfolge)

**M6 Pattern: OUTPUT -> Manifest -> State -> NOTIFY**

**6a. OUTPUT** (bereits in Schritt 1-5 geschrieben)

**6b. _manifest.md UPDATE:**
```markdown
## Finalize Status
- **Status:** SUCCESS | WARNING | ERROR
- **Total Pages:** {total_pages}
- **Total Citations:** {total_citations}
- **Compilation Time:** {compilation_time} seconds
- **Warnings:** {warnings_count}
- **Fallbacks:** {fallbacks_used}
- **Output:** output/publish/paper.pdf
- **Next Step:** END (Pipeline abgeschlossen)
```

**6c. session-state.json UPDATE:**
```json
{
  "last_command": "_WP_finalize",
  "finalize_status": "SUCCESS",
  "finalize_timestamp": "2026-02-11T10:00:00Z",
  "total_pages": 87,
  "pdf_path": "output/publish/paper.pdf",
  "phase": "COMPLETED"
}
```

**6d. NOTIFY:**
- SUCCESS (0 warnings): `powershell -Command "notify 'WritePaper FINALIZED: {pages}p, output/publish/paper.pdf'"`
- WARNING (N warnings): `powershell -Command "notify 'WritePaper FINALIZED with {N} warnings'"`
- ERROR: `powershell -Command "notify 'WritePaper FINALIZE FAILED: {error_type}'"`

---

## Error-Handling (3-Stufen nach W3)

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| BLOCKING | LaTeX-Error, references.bib fehlt, alle final-draft.md fehlen | STOP + Log + NOTIFY Error | JA (ERROR) |
| NON-BLOCKING | 1 Figure fehlt, research_verify FAIL, BibTeX unused Entry | CONTINUE + Log Warning + Report | Optional (WARNING) |
| FALLBACK (M7) | Pandoc fehlt, pdflatex fehlt, pdftk fehlt, Template fehlt | Alternative Strategie + WARNUNG | JA (INFO) |

**M7 Fallback-Ketten (3 Stueck):**

| Operation | Primaer | Sekundaer | Tertiaer | Total-Fail |
|-----------|---------|-----------|----------|------------|
| MD -> LaTeX | Pandoc | sed/regex | - | BLOCKING STOP |
| LaTeX -> PDF | pdflatex | xelatex | - | BLOCKING STOP |
| PDF Split | pdftk | qpdf | - | SKIP + WARNUNG |

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] Alle N Kapitel-Drafts gelesen und konvertiert
- [ ] references.bib und PaperReference.tex geladen
- [ ] Markdown -> LaTeX Conversion durchgefuehrt
- [ ] LaTeX -> PDF Compilation durchgefuehrt
- [ ] PDF Split durchgefuehrt (falls normal/hard)
- [ ] research_verify aufgerufen (falls hard)
- [ ] paper.pdf in output/publish/ kopiert
- [ ] finalize-report.json generiert
- [ ] _manifest.md und session-state.json aktualisiert
- [ ] NOTIFY gesendet

### Korrektheit
- [ ] LaTeX-Passes aus difficulty (2|3|4)
- [ ] Timeout aus difficulty (2|5|10 min)
- [ ] PDF-Split nur bei normal/hard
- [ ] research_verify nur bei hard
- [ ] BibTeX-Citations valide
- [ ] M6 State-Sync-Reihenfolge: OUTPUT -> Manifest -> State -> NOTIFY

### Robustheit
- [ ] M7 Fallback fuer Pandoc (sed/regex)
- [ ] M7 Fallback fuer pdflatex (xelatex)
- [ ] M7 Fallback fuer pdftk (qpdf)
- [ ] Missing Figure -> NON-BLOCKING Warning
- [ ] Compilation Timeout -> ABORT + partial Output
- [ ] BibTeX-Error -> BLOCKING STOP + .blg Log
