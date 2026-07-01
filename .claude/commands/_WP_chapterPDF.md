# /_WP_chapterPDF - Chapter PDF Generation & Email Delivery

```yaml
status: active
version: 2.0.0
created: 2026-02-14
updated: 2026-02-15
op: WritePaper
phase: Core Transformation
type: building-block
chain_position: chapterPDF
difficulty_scaling: true
mcp_critical: false
loop_controller: false
decision_type: false
```

---

```
+======================================================================+
| VERTRAG: /_WP_chapterPDF v2.0                                       |
+======================================================================+
|                                                                        |
| ACTOR: FERTIGES KAPITEL-PRODUKT (PDF + Email)                          |
|   TUT:                                                                 |
|     - final-draft.md aus synthesis lesen (Kapitel-Inhalt)             |
|     - references.bib laden (BibTeX Entries)                            |
|     - Figures aus output/figures/ kopieren + einbinden                |
|     - Markdown -> LaTeX konvertieren (sed/regex + Figures)            |
|     - Standalone LaTeX-Dokument fuer Kapitel generieren               |
|     - pdflatex + bibtex kompilieren (3-Pass)                          |
|     - PDF Quality Gate pruefen (Figures, Bib, Zitate, Seiten)        |
|     - PDF per Email an User senden (Python smtplib, Gmail SMTP)      |
|     - chapter-pdf-report.json generieren (Metriken + QG-Status)      |
|   NICHT:                                                               |
|     - Kapitel schreiben oder aendern (-> write, autoGen)               |
|     - Qualitaet bewerten (-> qualityGate, convergence)                |
|     - Figures generieren (-> visual)                                   |
|     - Research durchfuehren (-> research, discovery)                   |
|     - Gesamt-Paper zusammenfuegen (-> finalize)                        |
|     - COVERED markieren (-> reflect)                                   |
|     - User-Decision verarbeiten (-> reflect)                           |
|   ESKALIERT:                                                           |
|     - LaTeX-Compilation Error -> WARNUNG + Markdown-PDF Fallback      |
|     - pdflatex nicht verfuegbar -> WARNUNG + Skip PDF                 |
|     - Email-Versand fehlgeschlagen -> WARNUNG + PDF lokal verfuegbar  |
|     - references.bib fehlt -> WARNUNG + Continue ohne Bibliographie   |
|     - Gmail Credentials fehlen -> WARNUNG + Skip Email                |
|     - Figure fehlt -> [MISSING FIGURE] Placeholder + WARNUNG          |
|                                                                        |
| LIEST (Input) - PFLICHT:                                               |
|   1. _manifest.md (current_chapter, chapter_title)                    |
|   2. session-state.json (difficulty, email_address)                   |
|   3. config/project.yaml (title, author, email)                       |
|   4. output/synthesis/chapter-{N}/final-draft.md (Kapitel-Content)    |
|   5. output/references/references.bib (BibTeX Entries)                |
|   6. output/figures/chapter-{N}/figure-report.json (Figure-Manifest) |
|   7. output/figures/chapter-{N}/*.png (Figure-Dateien)               |
|                                                                        |
| SCHREIBT (Output) - PFLICHT:                                           |
|   1. output/pdf/chapter-{N}/chapter-{N}.tex (LaTeX-Source)            |
|   2. output/pdf/chapter-{N}/chapter-{N}.pdf (kompiliertes PDF)        |
|   3. output/pdf/chapter-{N}/figures/*.png (kopierte Figures)          |
|   4. output/pdf/chapter-{N}/chapter-pdf-report.json (Metriken + QG)  |
|   5. _manifest.md (UPDATE: pdf_status, pdf_path, qg_status)          |
|   6. session-state.json (UPDATE: last_command, pdf_path)              |
|                                                                        |
| POSITION:                                                              |
|   TYPE: LINEAR                                                         |
|   AFTER: /_WP_synthesis (final-draft.md fertig)                      |
|   BEFORE: /_WP_reflect (User-Review mit PDF)                         |
|   PHASE: Core Transformation                                          |
|   CHAIN: [synthesis] -> [chapterPDF] -> [reflect]                    |
|                                                                        |
| SCHWIERIGKEIT:                                                         |
|   | Dimension          | easy        | normal      | hard            |
|   |--------------------|-------------|-------------|-----------------|
|   | LaTeX Passes       | 2           | 3           | 3               |
|   | Email              | ja          | ja          | ja              |
|   | Compilation Timeout| 60s         | 120s        | 180s            |
|   | Include TOC        | nein        | nein        | ja              |
|   | PDF Quality Gate   | 2 Gates     | 3 Gates     | 4 Gates         |
|                                                                        |
| NOTIFY:                                                                |
|   SUCCESS: "Kapitel {N} PDF: {pages}p, QG {status}, Email an {addr}" |
|   WARNING: "Kapitel {N} PDF mit Warnungen: {warnings}"                |
|   ERROR:   "Kapitel {N} PDF FAILED: {error}"                          |
|                                                                        |
| TAGS:                                                                  |
|   type: publish                                                        |
|   op: WritePaper                                                       |
|   chapter: {N}                                                         |
|   chain-position: chapterPDF                                           |
|   prev: "[[WritePaper-synthesis]]"                                     |
|   next: "[[WritePaper-reflect]]"                                       |
+======================================================================+
```

---

## Design-Philosophie

chapterPDF ist das **fertige Produkt** das der User per Email bekommt — chapter by chapter. Die Email IST das Ergebnis. Jedes Kapitel-PDF muss vollstaendig sein: Content, Figures, Bibliographie.

**BLOCKING bei:** final-draft.md fehlt (wie bisher)
**NON-BLOCKING bei:** Figure fehlt (Placeholder), Bibliographie fehlt (Warnung), Email-Fehler (PDF lokal)

---

## Verantwortlichkeit

### TUT (Kernaufgabe)
- Liest final-draft.md (Markdown) aus synthesis Output
- Liest references.bib (fuer Bibliographie)
- Kopiert Figures aus output/figures/chapter-{N}/ in PDF-Verzeichnis
- Konvertiert Markdown zu LaTeX inkl. Figure-Einbindung via \includegraphics
- Generiert standalone LaTeX-Dokument mit Chapter-Template
- Kompiliert mit pdflatex + bibtex (Multi-Pass, bibtex PFLICHT)
- Fuehrt PDF Quality Gate durch (4 Gates)
- Sendet PDF per Email an User (Gmail SMTP via Python smtplib) — NUR nach QG
- Generiert chapter-pdf-report.json mit Metriken + QG-Status
- State-Update nach M6-Reihenfolge (OUTPUT -> Manifest -> State -> NOTIFY)

### TUT NICHT (Out of Scope)
- Kapitel schreiben oder ueberarbeiten (das macht /_WP_write + /_WP_autoGen)
- Qualitaet bewerten (das macht /_WP_qualityGate)
- Figures generieren (das macht /_WP_visual)
- COVERED Collection markieren (das macht /_WP_reflect)
- User-Decision verarbeiten (das macht /_WP_reflect)
- Gesamt-Paper PDF (das macht /_WP_finalize — Sonderfall: alle Kapitel zusammen)

### Eskalation
- **NON-BLOCKING:** LaTeX-Error -> Fallback: pandoc md->pdf oder plain text
- **NON-BLOCKING:** pdflatex nicht verfuegbar -> Skip PDF, WARNUNG
- **NON-BLOCKING:** Email-Fehler -> PDF lokal verfuegbar, WARNUNG
- **NON-BLOCKING:** references.bib fehlt -> WARNUNG + Continue ohne Bibliographie
- **NON-BLOCKING:** Gmail Credentials fehlen -> Skip Email, WARNUNG
- **NON-BLOCKING:** Figure fehlt -> [MISSING FIGURE] Placeholder + Recompile
- **KEINE BLOCKING Errors** - chapterPDF darf Pipeline NIEMALS stoppen

---

## Ablauf

### Schritt 0: Inputs sammeln

**Ziel:** Kapitel-Draft, Figures und Metadata laden

**Aktionen:**
1. Lese `_manifest.md` -> `current_chapter`, `chapter_title`
2. Lese `session-state.json` -> `difficulty`
3. Lese `config/project.yaml` -> `title`, `author`
4. Lese `output/synthesis/chapter-{N}/final-draft.md` -> Markdown Content
5. Lese `output/references/references.bib` -> BibTeX
6. Lese `output/figures/chapter-{N}/figure-report.json` -> Figure-Manifest
7. Scanne `output/figures/chapter-{N}/*.png` -> Figure-Dateien
8. Email-Adresse bestimmen:
   - Aus `config/project.yaml` -> `email` (primaer)
   - Aus `session-state.json` -> `email_address` (sekundaer)
   - Aus `~/.bashrc` -> `GMAIL_ADDRESS` (fallback)

**Validierung:**
- final-draft.md MUSS existieren -> sonst SKIP gesamten Command + WARNUNG
- references.bib: WARNUNG falls fehlt, weiter ohne Bibliographie
- figure-report.json: WARNUNG falls fehlt, weiter ohne Figure-Verifikation
- Alles andere ist optional mit Fallbacks

**Erfolgskriterium:**
- Markdown Content geladen
- Figure-Liste bekannt (oder leer)
- Email-Adresse bestimmt (oder Skip Email)

---

### Schritt 0.5: Figures vorbereiten

**Ziel:** Figures aus visual-Output in PDF-Verzeichnis kopieren und Placeholder ersetzen

**Aktionen:**
1. Erstelle `output/pdf/chapter-{N}/figures/` Verzeichnis
2. Kopiere alle `output/figures/chapter-{N}/*.png` nach `output/pdf/chapter-{N}/figures/`
3. Erstelle Figure-Mapping aus figure-report.json:
   - `[FIGURE: description]` -> `\begin{figure}[htbp]\centering\includegraphics[width=0.8\textwidth]{figures/fig-NN}\caption{description}\end{figure}`
4. Falls Figure fehlt (in Markdown referenziert aber Datei nicht vorhanden):
   - Ersetze durch: `\begin{figure}[htbp]\centering\fbox{\parbox{0.8\textwidth}{\centering [MISSING FIGURE: description]}}\end{figure}`
   - Trage in `missing_figures[]` ein

**Erfolgskriterium:**
- Alle verfuegbaren Figures kopiert
- Figure-Mapping bereit fuer LaTeX-Conversion
- missing_figures[] Liste fuer QG

---

### Schritt 1: Markdown -> LaTeX Conversion

**Ziel:** Standalone LaTeX-Dokument fuer dieses Kapitel erzeugen

**1a. Markdown-zu-LaTeX Regeln:**
```
# Title           -> \section{Title}
## Subtitle       -> \subsection{Subtitle}
### Sub           -> \subsubsection{Sub}
**bold**          -> \textbf{bold}
*italic*          -> \textit{italic}
`code`            -> \texttt{code}
\cite{key}        -> bleibt (LaTeX-native)
- item            -> \begin{itemize}\item ... \end{itemize}
1. item           -> \begin{enumerate}\item ... \end{enumerate}
> blockquote      -> \begin{quote} ... \end{quote}
[FIGURE: desc]    -> \includegraphics (aus Schritt 0.5 Mapping)
```

**1b. LaTeX-Template (Chapter-Level):**
```latex
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[ngerman]{babel}
\usepackage{geometry}
\geometry{a4paper, left=25mm, right=25mm, top=25mm, bottom=25mm}
\usepackage{natbib}
\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue]{hyperref}
\usepackage{graphicx}
\graphicspath{{figures/}}
\usepackage{fancyhdr}
\usepackage{parskip}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{{{PAPER_TITLE}} -- Kapitel {N}}
\fancyhead[R]{\thepage}

\title{Kapitel {N}: {{CHAPTER_TITLE}}}
\author{{{AUTHOR}}}
\date{\today}

\begin{document}
\maketitle

{{CONTENT}}

\bibliographystyle{plainnat}
\bibliography{references}

\end{document}
```

**1c. Platzhalter ersetzen:**
- `{{PAPER_TITLE}}` -> aus project.yaml `title`
- `{{CHAPTER_TITLE}}` -> aus manifest `chapter_title`
- `{{AUTHOR}}` -> aus project.yaml `author`
- `{{CONTENT}}` -> konvertierter LaTeX-Content (inkl. \includegraphics)
- `{N}` -> aktuelle Kapitelnummer

**1d. Aenderungen gegenueber v1.0:**
- `\graphicspath{{figures/}}` hinzugefuegt (Figure-Pfad)
- `citecolor=blue` statt `citecolor=green` (Zitate als klickbare blaue Links)
- `[FIGURE: ...]` Placeholder durch `\includegraphics` ersetzt (aus Schritt 0.5)

**Erfolgskriterium:**
- output/pdf/chapter-{N}/chapter-{N}.tex generiert
- references.bib nach output/pdf/chapter-{N}/ kopiert (falls vorhanden)
- Figures in output/pdf/chapter-{N}/figures/ kopiert

---

### Schritt 2: LaTeX -> PDF Compilation

**Ziel:** PDF via pdflatex erzeugen

**Pre-Flight Check:**
```bash
pdflatex --version || { echo "WARNUNG: pdflatex nicht verfuegbar"; }
```

**Compilation (3-Pass mit bibtex PFLICHT):**
```bash
cd output/pdf/chapter-{N}
timeout {timeout} pdflatex -interaction=nonstopmode chapter-{N}.tex
bibtex chapter-{N}                                                    # PFLICHT
timeout {timeout} pdflatex -interaction=nonstopmode chapter-{N}.tex
timeout {timeout} pdflatex -interaction=nonstopmode chapter-{N}.tex   # nur bei hard
```

**Timeout nach Difficulty:**
- easy: 60s
- normal: 120s
- hard: 180s

**Error-Handling:**
- Exit-Code != 0: Parse .log, extrahiere Fehler -> WARNUNG (NON-BLOCKING)
- Timeout: WARNUNG + Skip PDF
- BibTeX-Error: WARNUNG + Continue ohne Bibliographie (Fallback)
- **NIEMALS BLOCKING** - Pipeline darf nicht stoppen

**Fallback bei Compilation-Fehler (M7 Pattern):**
1. Versuche ohne Bibliographie (entferne \bibliography Zeile)
2. Versuche ohne Figures (entferne \includegraphics Zeilen)
3. Falls immer noch Fehler: Skip PDF komplett

**Erfolgskriterium:**
- output/pdf/chapter-{N}/chapter-{N}.pdf existiert
- ODER: Klare WARNUNG warum PDF nicht erzeugt werden konnte

---

### Schritt 2.5: PDF Quality Gate

**Ziel:** Pruefen ob das PDF vollstaendig ist BEVOR es per Email versendet wird

**4 Gates (Difficulty-skaliert):**

| Gate | Name | Pruefung | Methode | Difficulty |
|------|------|----------|---------|------------|
| QG1 | Figures | Alle Figures aus figure-report.json im PDF referenziert | Grep in .tex nach \includegraphics, Vergleich mit figure-report.json | normal, hard |
| QG2 | Bibliographie | \bibliography vorhanden + bibtex erfolgreich | Check .bbl Datei existiert + hat Eintraege | easy, normal, hard |
| QG3 | Zitate | Keine unaufgeloesten Referenzen | Grep in .log nach "undefined references" | normal, hard |
| QG4 | Seitenzahl | Mindestens 3 Seiten | pdfinfo oder .log parsen | hard |

**Gate-Selektion nach Difficulty:**
- easy: QG2
- normal: QG1, QG2, QG3
- hard: QG1, QG2, QG3, QG4

**Bei Gate-FAIL (NON-BLOCKING):**

| Gate | FAIL-Response |
|------|---------------|
| QG1 FAIL | Fehlende Figures als [MISSING FIGURE] einsetzen, recompile |
| QG2 FAIL | WARNUNG, weiter ohne Bibliographie |
| QG3 FAIL | WARNUNG, Liste der unaufgeloesten Zitate im Report |
| QG4 FAIL | WARNUNG (Kapitel ist kurz) |

**QG-Status:**
- `ALL_PASS`: Alle aktivierten Gates bestanden
- `PASS_WITH_WARNINGS`: Gates bestanden, aber mit Warnungen
- `DEGRADED`: Ein oder mehrere Gates FAIL, PDF trotzdem generiert

**Erfolgskriterium:**
- QG-Status bestimmt
- Bei FAIL: Korrektur-Massnahmen durchgefuehrt (Recompile bei QG1)
- Report-Daten fuer chapter-pdf-report.json gesammelt

---

### Schritt 3: Email-Versand (NUR nach Quality Gate)

**Ziel:** PDF per Gmail an User senden

**Voraussetzung:** Schritt 2.5 (Quality Gate) muss abgeschlossen sein

**Methode:** Python smtplib (Gmail SMTP_SSL, Port 465)

**Credentials laden:**
```bash
source ~/.bashrc
# GMAIL_ADDRESS und GMAIL_APP_PASSWORD muessen gesetzt sein
```

**Email-Script (Python):**
```python
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

gmail_user = os.environ.get('GMAIL_ADDRESS')
gmail_pass = os.environ.get('GMAIL_APP_PASSWORD')
recipient = "{email_address}"

msg = MIMEMultipart()
msg['From'] = gmail_user
msg['To'] = recipient
msg['Subject'] = 'WritePaper: Kapitel {N} - {chapter_title}'

body = """Kapitel {N}: {chapter_title}

Paper: {paper_title}
Seiten: {pages}
Woerter: {word_count}
Zitate: {citations}
Figures: {figure_count}

PDF Quality Gate: {qg_status}
{qg_warnings}

Bitte reviewen und Feedback geben.
Naechster Schritt: /_WP_reflect (ACCEPT / RETRY / ABORT)
"""

msg.attach(MIMEText(body, 'plain'))

# PDF Attachment
with open(pdf_path, 'rb') as f:
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition',
                    f'attachment; filename="chapter-{N}.pdf"')
    msg.attach(part)

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    server.login(gmail_user, gmail_pass)
    server.sendmail(gmail_user, recipient, msg.as_string())
```

**Email-Body enthaelt QG-Status:**
- Bei ALL_PASS: "PDF Quality Gate: PASS (alle {n} Gates bestanden)"
- Bei PASS_WITH_WARNINGS: "PDF Quality Gate: PASS mit Warnungen: {liste}"
- Bei DEGRADED: "PDF Quality Gate: DEGRADED - {liste der FAIL-Gates}"

**Error-Handling:**
- Credentials fehlen: WARNUNG + Skip Email
- SMTP-Fehler: WARNUNG + Skip Email (PDF bleibt lokal)
- PDF existiert nicht: Skip Email + WARNUNG
- **NIEMALS BLOCKING**

**Erfolgskriterium:**
- Email gesendet mit PDF-Attachment + QG-Status im Body
- ODER: Klare WARNUNG warum Email nicht gesendet werden konnte

---

### Schritt 4: Report generieren

**Ziel:** Metriken + QG-Status dokumentieren

**chapter-pdf-report.json:**
```json
{
  "chapter": 1,
  "timestamp": "2026-02-15T10:00:00Z",
  "version": "2.0.0",
  "difficulty": "normal",
  "pdf_generated": true,
  "pdf_path": "output/pdf/chapter-1/chapter-1.pdf",
  "pdf_pages": 4,
  "latex_passes": 3,
  "compilation_time_seconds": 12.3,
  "figures": {
    "total": 5,
    "included": 4,
    "missing": 1,
    "missing_list": ["fig-03"]
  },
  "bibliography": {
    "bib_found": true,
    "bbl_generated": true,
    "citations_total": 15,
    "citations_undefined": 0
  },
  "quality_gate": {
    "status": "PASS_WITH_WARNINGS",
    "gates_activated": 3,
    "gates_passed": 2,
    "gates_warned": 1,
    "gates_failed": 0,
    "details": {
      "QG1_figures": "WARN (1 missing)",
      "QG2_bibliography": "PASS",
      "QG3_citations": "PASS"
    }
  },
  "email_sent": true,
  "email_recipient": "hannover1992@googlemail.com",
  "word_count": 3200,
  "warnings": ["QG1: Figure fig-03 nicht gefunden, Placeholder eingefuegt"],
  "fallbacks_used": []
}
```

---

### Schritt 5: State aktualisieren (M6 Reihenfolge)

**5a. OUTPUT** (bereits in Schritten 0.5-4)

**5b. _manifest.md UPDATE:**
```markdown
## Chapter PDF - Kapitel {N}
- **PDF:** {GENERATED|FAILED}
- **Path:** output/pdf/chapter-{N}/chapter-{N}.pdf
- **Pages:** {pages}
- **Figures:** {included}/{total} ({missing} missing)
- **Bibliography:** {YES|NO}
- **Quality Gate:** {ALL_PASS|PASS_WITH_WARNINGS|DEGRADED}
- **Email:** {SENT|FAILED|SKIPPED}
- **Next Step:** /_WP_reflect
```

**5c. session-state.json UPDATE:**
```json
{
  "last_command": "_WP_chapterPDF",
  "pdf_status": "GENERATED",
  "pdf_path": "output/pdf/chapter-{N}/chapter-{N}.pdf",
  "pdf_qg_status": "ALL_PASS",
  "email_status": "SENT",
  "next_step": "/_WP_reflect"
}
```

**5d. NOTIFY:**
```bash
notify "WritePaper Kapitel {N} PDF: {pages}p, QG {status}, Email an {address}"
```

---

## Error Handling

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| BLOCKING | final-draft.md fehlt | Skip Command + WARNUNG | WARNING |
| NON-BLOCKING | LaTeX-Compilation Error | Fallback ohne Bib/Figures + WARNUNG | WARNING |
| NON-BLOCKING | pdflatex nicht verfuegbar | Skip PDF + WARNUNG | WARNING |
| NON-BLOCKING | Email-Credentials fehlen | Skip Email + PDF lokal | WARNING |
| NON-BLOCKING | SMTP-Error | Skip Email + PDF lokal | WARNING |
| NON-BLOCKING | references.bib fehlt | WARNUNG + LaTeX ohne Bibliographie | WARNING |
| NON-BLOCKING | Figure fehlt | [MISSING FIGURE] Placeholder + Recompile | WARNING |
| NON-BLOCKING | QG Gate FAIL | WARNUNG + Korrektur + Continue | WARNING |
| FALLBACK | Compilation Error nach allen Fallbacks | Skip PDF komplett | WARNING |

**KRITISCH: Dieses Command hat nur EINEN BLOCKING Error (final-draft.md fehlt).**
Alle anderen Fehler werden per Fallback oder Placeholder behandelt.
Das PDF ist das fertige Produkt — es soll so vollstaendig wie moeglich sein,
aber die Pipeline darf NICHT wegen PDF-Problemen stoppen.

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] final-draft.md gelesen und Content extrahiert
- [ ] Figures kopiert und in LaTeX eingebunden
- [ ] Markdown zu LaTeX konvertiert (inkl. Figure-Mapping)
- [ ] LaTeX-Dokument mit Template generiert (inkl. \graphicspath)
- [ ] pdflatex + bibtex Compilation durchgefuehrt (oder Fallback)
- [ ] PDF Quality Gate durchgefuehrt (difficulty-skaliert)
- [ ] Email mit PDF-Attachment gesendet (oder Fallback) — NACH QG
- [ ] chapter-pdf-report.json geschrieben (inkl. QG-Status)
- [ ] _manifest.md und session-state.json aktualisiert
- [ ] NOTIFY gesendet

### Korrektheit
- [ ] LaTeX-Passes aus difficulty (2|3|3)
- [ ] Timeout aus difficulty (60|120|180s)
- [ ] QG-Gates aus difficulty (1|3|4)
- [ ] Email-Adresse aus project.yaml oder session-state
- [ ] BibTeX-Pass ist PFLICHT (nicht optional)
- [ ] Figures per \includegraphics eingebunden (nicht nur Placeholder)
- [ ] Email erst NACH Quality Gate versendet
- [ ] M6 State-Sync: OUTPUT -> Manifest -> State -> NOTIFY

### Robustheit
- [ ] NUR 1 BLOCKING Error (final-draft.md fehlt)
- [ ] Fallback ohne Bibliographie bei BibTeX-Error
- [ ] Fallback [MISSING FIGURE] bei fehlenden Figures
- [ ] Skip Email bei fehlenden Credentials
- [ ] Skip PDF bei fehlender LaTeX-Engine
- [ ] M7 Fallback-Kette: mit Bib+Figures -> ohne Bib -> ohne Figures -> Skip PDF
- [ ] Pipeline laeuft weiter auch bei komplettem Fehlschlag

---

## Hinweise

### Fertiges-Produkt Design-Philosophie (v2.0)
- chapterPDF ist das **fertige Produkt**, nicht ein "nice-to-have" Delivery-Schritt
- Die Email IST das Ergebnis — der User bekommt ein vollstaendiges Kapitel-PDF
- Figures, Bibliographie und Zitate muessen im PDF enthalten sein
- Quality Gate stellt Vollstaendigkeit sicher BEVOR die Email rausgeht
- Bei Problemen: Fallbacks greifen, PDF wird so vollstaendig wie moeglich
- reflect kann auch ohne PDF arbeiten (degradiert), aber das ist der AUSNAHMEFALL

### Email-Pattern (aus MEMORY.md)
- Credentials in `~/.bashrc`: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`
- Methode: Python smtplib, SMTP_SSL, smtp.gmail.com:465
- Pattern: `source ~/.bashrc && python3` -> smtplib

### Chain-Integration
- ENTRY: synthesis -> chapterPDF (final-draft.md fertig)
- EXIT: chapterPDF -> reflect (PDF generiert + gesendet + QG geprueft)
- reflect zeigt Summary + Learnings, User hat PDF bereits per Email

### Referenzen
- Previous: /_WP_synthesis.md (final-draft.md Input)
- Next: /_WP_reflect.md (User-Review + OUTER-Loop Decision)
- Related: /_WP_finalize.md (Sonderfall: alle Kapitel zusammen versenden)
- Related: /_WP_visual.md (generiert Figures die chapterPDF einbindet)

---

**Command-Version:** 2.0.0
**Letzte Aenderung:** 2026-02-15
