# /_WP_synthesis - Draft Synthesis & Consensus

```yaml
status: active
version: 1.0.0
created: 2026-02-09
op: SYNTHESIS
phase: Core Transformation
type: building-block
chain_position: AFTER=/_WP_review, BEFORE=/_WP_reflect
difficulty_scaling: true
```

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════════╗
║ STANDARD-COMMAND: /_WP_synthesis                                       ║
╠══════════════════════════════════════════════════════════════════════════╣
║ [1] ACTOR:     Sonnet Operator                                          ║
║ [2] LIEST:     review-matrix.json, top-K drafts, chapter-model.md       ║
║ [3] SCHREIBT:  final-draft.md, merge-report.json                        ║
║ [4] POSITION:  LINEAR - AFTER /_WP_review, BEFORE /_WP_reflect      ║
║ [9] SCHWIERIGKEIT: easy (Top-1 Direct), normal (2-Way Merge),           ║
║                    hard (3-Way Consensus)                                ║
║ [10] NOTIFY:   Success → final_draft ready + word_count + citations     ║
║                Warning → Citation gaps detected                          ║
║                Error → No drafts available / review-matrix missing       ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## VERANTWORTLICHKEIT

### TUT dieser Command
- Top-K Drafts aus review-matrix.json selektieren
- Section-by-Section Merge basierend auf difficulty-Level
- Consensus-Building bei 3-Way Merge (hard)
- Figure-Integration aus approved figures
- Final Draft Assembly mit Kohaerenz-Check
- Merge-Report mit Statistiken generieren
- State-Update nach M6-Reihenfolge

### TUT dieser Command NICHT
- Eigene Draft-Bewertung (verwendet NUR Review-Ranking)
- Neue Content-Generierung (nur Merge existierender Drafts)
- Quality-Loop-Entscheidung (ist Worker, kein Controller)
- MCP-Tool-Aufrufe (arbeitet NUR mit lokalen Dateien)
- LaTeX-Rendering oder PDF-Export

### ESKALATION
- Fehlt review-matrix.json → NOTIFY Error → empfehle /_WP_review erneut
- 0 Drafts verfuegbar → BLOCKING Error → Pipeline-Abbruch
- Alle Top-K Drafts unter 50% Word-Count-Target → NOTIFY Warning → weiter mit Best-Effort Merge

---

## ABLAUF

### Schritt 0: Inputs laden

**ZIEL:** Alle benoetigten Dateien und Konfiguration einlesen

**AKTIONEN:**
1. Lese _manifest.md → current_chapter, phase
2. Lese session-state.json → difficulty, quality_iteration
3. Lese config/project.yaml → current_chapter (Fallback)
4. Lese output/reviews/chapter-{N}/review-matrix.json → Top-K Draft-IDs, Scores
5. Lese output/reviews/chapter-{N}/review-summary.md → Feedback-Kontext
6. Lese output/models/chapter-{N}-model.md → Section-Liste, Keywords
7. Lese output/figures/chapter-{N}/ → Approved Figures (falls vorhanden)

**VALIDIERUNG:**
- review-matrix.json existiert? → JA: weiter, NEIN: BLOCKING Error
- Top-K > 0? → JA: weiter, NEIN: BLOCKING Error
- chapter-{N}-model.md existiert? → JA: weiter, NEIN: BLOCKING Error

**ERFOLGSKRITERIUM:**
- [ ] current_chapter identifiziert
- [ ] difficulty-Level bekannt (easy/normal/hard)
- [ ] Top-K Draft-IDs extrahiert
- [ ] Section-Liste aus chapter-model verfuegbar

---

### Schritt 1: Top-K Drafts vorbereiten

**ZIEL:** Top-K Drafts laden und strukturieren

**AKTIONEN:**
1. Bestimme K basierend auf difficulty:
   - easy: Top-1
   - normal: Top-2
   - hard: Top-3
2. Lade Draft-Dateien: output/drafts/chapter-{N}/draft-A{NN}.md (fuer jede Top-K ID)
3. Extrahiere pro Draft:
   - Section-Struktur (Headings ## ...)
   - Citations (\cite{...})
   - Figures ([FIGURE: ...] oder ![...])
   - Word-Count pro Section
4. Validiere Vollstaendigkeit:
   - Jeder Draft hat alle Sections aus chapter-model? → Optional Warning bei Luecken

**VALIDIERUNG:**
- Alle Top-K Draft-Dateien geladen? → JA: weiter, NEIN: BLOCKING Error
- Mind. 1 Draft hat >= 80% Sections aus Model? → JA: weiter, NEIN: Warning + Best-Effort

**ERFOLGSKRITERIUM:**
- [ ] Top-K Drafts geladen (1-3 je nach difficulty)
- [ ] Section-Mapping pro Draft erstellt
- [ ] Citation-Liste pro Draft extrahiert

---

### Schritt 2: Section-by-Section Merge

**ZIEL:** Merged Sections mit optimaler Argumentation und maximaler Citation-Abdeckung

**AKTIONEN:**

**Pro Section aus chapter-{N}-model.md:**

#### easy (Top-1 Direct):
1. Uebernehme Section aus Top-1 Draft
2. Polishing:
   - Sprachliche Glaettung (Wiederholungen, Uebergaenge)
   - Figure-Placeholder pruefen
   - Citations deduplizieren innerhalb Section

#### normal (2-Way Merge):
1. Lade Section aus Draft-1 und Draft-2
2. Vergleiche:
   - Argumentation: Welche Version ist logischer/vollstaendiger?
   - Citations: Merge ALLE unique Citations aus beiden
   - Stil: Vereinheitliche Terminologie
3. Merge-Strategie:
   - Basis: Staerkere Argumentations-Version
   - Ergaenzung: Unique Points und Citations aus anderer Version
   - Uebergaenge: Harmonisieren zwischen eingefuegten Teilen

#### hard (3-Way Consensus):
1. Lade Section aus Draft-1, Draft-2, Draft-3
2. Consensus-Analyse:
   - Identifiziere Aussagen mit >=2/3 Uebereinstimmung → CONSENSUS
   - Identifiziere Aussagen nur in 1 Draft → DISSENT
3. Merge-Strategie:
   - Consensus-Passagen erhalten hohes Gewicht (Kern der Section)
   - Dissent-Passagen integrieren als:
     - Alternativ-Perspektiven: "Eine andere Sichtweise betont..."
     - Fussnoten: "Ergaenzend siehe auch [Citation]..."
   - ALLE unique Citations mergen
   - Cross-References einfuegen: "Wie in Abschnitt X.Y gezeigt..."
4. Kohaerenz-Check:
   - Roter Faden trotz Merge erkennbar?
   - Argumentations-Fluß konsistent?

**VALIDIERUNG:**
- Jede Section aus Model gemerged? → JA: weiter, NEIN: BLOCKING Error
- Mind. 1 Citation pro Section? → JA: ideal, NEIN: [CITATION-NEEDED: section] Marker + Warning

**ERFOLGSKRITERIUM:**
- [ ] Alle Sections gemerged
- [ ] Citations dedupliziert und vollstaendig
- [ ] Kohaerenz zwischen Sections hergestellt

---

### Schritt 3: Figure-Integration

**ZIEL:** Approved Figures in Draft einbinden, Placeholder ersetzen

**AKTIONEN:**
1. Lese output/figures/chapter-{N}/ fuer approved Figures
2. Fuer jeden [FIGURE: beschreibung] Placeholder:
   - Finde passende Figure (Name-Match oder semantisch)
   - Ersetze durch: `![{caption}](figures/chapter-{N}/fig-{NN}.{ext})`
3. Falls keine passende Figure:
   - Behalte [MISSING FIGURE: beschreibung] → spaeter LaTeX-TODO
4. Validiere Figure-Referenzen:
   - Pfade relativ zu project-root korrekt?

**VALIDIERUNG:**
- Mind. 1 Figure pro Kapitel? → Optional (abhaengig von chapter-model)
- Alle Figure-Pfade valide? → JA: weiter, NEIN: Warning (LaTeX wird spaeter fehlschlagen)

**ERFOLGSKRITERIUM:**
- [ ] Figure-Placeholder ersetzt oder als [MISSING FIGURE] markiert
- [ ] Figure-Captions konsistent formatiert

---

### Schritt 4: Final Draft Assembly

**ZIEL:** Kohaerenter, vollstaendiger Kapitel-Draft

**AKTIONEN:**
1. Zusammenfuegen aller Merged Sections in chapter-model Reihenfolge
2. Uebergangs-Saetze zwischen Sections einfuegen:
   - Logische Verknuepfungen: "Aufbauend auf diesen Grundlagen..."
   - Vorausblicke: "Im Folgenden wird untersucht..."
3. Deduplizierung von Citations:
   - Gleicher BibTeX-Key im gesamten Kapitel → nur einmal \cite{}
   - Bei mehrfacher Verwendung: \cite{key} statt wiederholter Erklaerung
4. Word-Count Pruefung:
   - Target: 6250-8750 Worte (bei 25-Seiten-Target aus W10)
   - Falls < 6250: [LOW-WORD-COUNT] Marker + Warning
   - Falls > 8750: [HIGH-WORD-COUNT] Marker + Optional Trimming-Vorschlag
5. Kohaerenz-Check:
   - Roter Faden erkennbar? (Intro → Argument → Conclusion)
   - Terminologie konsistent?
   - Citations ausreichend? (Min: 2.0/3.0/4.0 per Page bei easy/normal/hard)
6. Frontmatter generieren:
   ```yaml
   chapter: {N}
   difficulty: {easy|normal|hard}
   top_k_drafts: [A01, A02, A03]
   merge_strategy: {direct|2-way|3-way}
   word_count: {Zahl}
   citations: {Zahl}
   figures: {Zahl}
   status: final
   synthesized_at: {ISO-Timestamp}
   ```

**VALIDIERUNG:**
- Word-Count im Target-Bereich? → JA: ideal, NEIN: Warning + weiter
- Citation-Density erreicht? → JA: ideal, NEIN: Warning + weiter
- Alle Sections vorhanden? → JA: weiter, NEIN: BLOCKING Error

**ERFOLGSKRITERIUM:**
- [ ] Final Draft kohaerenter Text
- [ ] Frontmatter vollstaendig
- [ ] Word-Count und Citation-Stats dokumentiert

---

### Schritt 5: Output generieren

**ZIEL:** Final Draft und Merge-Report persistieren

**AKTIONEN:**

#### 5.1: final-draft.md schreiben
- Pfad: output/synthesis/chapter-{N}/final-draft.md
- Struktur:
  ```markdown
  ---
  chapter: {N}
  difficulty: {easy|normal|hard}
  top_k_drafts: [A01, A02, ...]
  merge_strategy: {direct|2-way|3-way}
  word_count: {Zahl}
  citations: {Zahl}
  figures: {Zahl}
  status: final
  synthesized_at: {ISO-Timestamp}
  ---

  # Kapitel {N}: {Titel aus chapter-model}

  ## Section 1
  {Merged Content}

  ## Section 2
  {Merged Content}

  ...
  ```

#### 5.2: merge-report.json schreiben
- Pfad: output/synthesis/chapter-{N}/merge-report.json
- Schema:
  ```json
  {
    "chapter": N,
    "difficulty": "easy|normal|hard",
    "merge_strategy": "direct|2-way|3-way",
    "top_k_drafts": ["A01", "A02", "A03"],
    "sections_merged": 5,
    "consensus_ratio": 0.85,  // nur bei 3-way
    "dissent_items": 3,        // nur bei 3-way
    "citations_total": 45,
    "word_count_total": 7200,
    "word_count_delta": "+15%",  // vs. avg of top-k drafts
    "figures_integrated": 4,
    "missing_figures": 1,
    "warnings": [
      "[CITATION-NEEDED: Section 3.2]",
      "[MISSING FIGURE: Architecture Overview]"
    ],
    "timestamp": "2026-02-09T14:30:00Z"
  }
  ```

**VALIDIERUNG:**
- final-draft.md geschrieben? → JA: weiter, NEIN: BLOCKING Error
- merge-report.json geschrieben? → JA: weiter, NEIN: Warning + weiter (nicht kritisch)

**ERFOLGSKRITERIUM:**
- [ ] output/synthesis/chapter-{N}/final-draft.md existiert
- [ ] merge-report.json mit vollstaendigen Stats existiert

---

### Schritt 6: State aktualisieren (M6 Reihenfolge)

**ZIEL:** Pipeline-State fuer /_WP_reflect vorbereiten

**AKTIONEN (REIHENFOLGE M6):**

1. **OUTPUT:** output/synthesis/chapter-{N}/ (bereits in Schritt 5 geschrieben)

2. **_manifest.md UPDATE:**
   ```markdown
   ## Chapter {N} - {Titel}
   - status: synthesis_completed
   - final_draft: output/synthesis/chapter-{N}/final-draft.md
   - word_count: {Zahl}
   - citations: {Zahl}
   - figures: {Zahl}
   - next_step: reflect
   ```

3. **session-state.json UPDATE:**
   ```json
   {
     "current_chapter": N,
     "phase": "synthesis_completed",
     "final_draft_path": "output/synthesis/chapter-{N}/final-draft.md",
     "merge_stats": {
       "strategy": "2-way",
       "word_count": 7200,
       "citations": 45,
       "warnings": 2
     },
     "next_step": "/_WP_reflect",
     "updated_at": "2026-02-09T14:30:00Z"
   }
   ```

4. **NOTIFY:**
   - Success: "Final draft synthesized: {word_count} words, {citations} citations, {merge_strategy} merge"
   - Warning (falls vorhanden): "Citation gaps in {sections}, Missing figures: {count}"
   - Error (falls BLOCKING): "Synthesis failed: {reason}"

**VALIDIERUNG:**
- _manifest.md aktualisiert? → JA: weiter, NEIN: Warning + weiter
- session-state.json aktualisiert? → JA: weiter, NEIN: Warning + weiter
- NOTIFY gesendet? → JA: DONE

**ERFOLGSKRITERIUM:**
- [ ] _manifest.md zeigt synthesis_completed
- [ ] session-state.json zeigt next_step = /_WP_reflect
- [ ] User informiert ueber Ergebnis

---

## OUTPUT-FORMAT

### final-draft.md Schema

```markdown
---
chapter: 2
difficulty: normal
top_k_drafts: [A01, A02]
merge_strategy: 2-way
word_count: 7200
citations: 45
figures: 4
status: final
synthesized_at: 2026-02-09T14:30:00Z
---

# Kapitel 2: Theoretische Grundlagen

## 2.1 Clean Code Prinzipien

{Merged Content aus Top-2 Drafts}

Die Prinzipien des Clean Code \cite{Martin2008} bilden die Grundlage...
Aufbauend auf diesen Grundlagen zeigt sich...

![Clean Code Pyramide](figures/chapter-2/fig-01.png)

## 2.2 Test-Driven Development

{Merged Content}

Wie in Abschnitt 2.1 gezeigt, erfordern Clean Code Prinzipien...

[CITATION-NEEDED: Empirische Studien zu TDD-Effektivitaet]

## 2.3 Refactoring-Strategien

{Merged Content}

[MISSING FIGURE: Refactoring-Workflow]

...
```

### merge-report.json Schema

```json
{
  "chapter": 2,
  "difficulty": "normal",
  "merge_strategy": "2-way",
  "top_k_drafts": ["A01", "A02"],
  "sections_merged": 5,
  "consensus_ratio": null,
  "dissent_items": null,
  "citations_total": 45,
  "word_count_total": 7200,
  "word_count_delta": "+12%",
  "figures_integrated": 4,
  "missing_figures": 1,
  "warnings": [
    "[CITATION-NEEDED: Section 2.2]",
    "[MISSING FIGURE: Refactoring-Workflow]"
  ],
  "timestamp": "2026-02-09T14:30:00Z"
}
```

---

## QUALITAETSKRITERIEN

Nach Abschluss pruefen:

- [ ] Top-K Drafts korrekt aus review-matrix.json selektiert
- [ ] Merge-Strategie entspricht difficulty (Direct/2-Way/3-Way)
- [ ] Alle Sections aus chapter-model gemerged
- [ ] Citations dedupliziert und vollstaendig
- [ ] Consensus/Dissent-Analyse bei hard (3-Way)
- [ ] Figure-Placeholder ersetzt oder als [MISSING FIGURE] markiert
- [ ] Word-Count im Target-Bereich (6250-8750)
- [ ] Citation-Density erreicht (2.0/3.0/4.0 per Page)
- [ ] Kohaerenz zwischen Sections (Roter Faden)
- [ ] Frontmatter vollstaendig in final-draft.md
- [ ] merge-report.json mit Stats geschrieben
- [ ] _manifest.md: synthesis_completed + next_step=reflect
- [ ] session-state.json: final_draft_path + merge_stats
- [ ] NOTIFY mit Word-Count/Citations/Warnings

---

## NOTIFY

### Success
```
✓ Final draft synthesized for Chapter {N}
  - Strategy: {merge_strategy}
  - Drafts merged: {top_k_drafts}
  - Word count: {count} ({delta} vs. avg drafts)
  - Citations: {count} ({density} per page)
  - Figures: {count} ({missing} missing)
  → Next: /_WP_reflect
```

### Warning
```
⚠ Synthesis completed with warnings for Chapter {N}:
  - Citation gaps in {sections}
  - Missing figures: {count}
  - Word count: {count} ({below/above} target)
  → Review final-draft.md before proceeding
```

### Error
```
✗ Synthesis FAILED for Chapter {N}:
  - Reason: {error_message}
  - Missing inputs: {files}
  → Fix: Run /_WP_review again to generate review-matrix.json
```

---

## ERROR HANDLING

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| BLOCKING | review-matrix.json fehlt | STOP + Empfehle /_WP_review erneut | Error |
| BLOCKING | 0 Top-K Drafts verfuegbar | STOP + Pipeline-Abbruch | Error |
| BLOCKING | chapter-{N}-model.md fehlt | STOP + Empfehle /_WP_model pruefung | Error |
| BLOCKING | Keine Section in irgendeinem Draft | STOP + Draft-Qualitaet zu niedrig | Error |
| NON-BLOCKING | 1 Section hat keine Citations | CONTINUE + [CITATION-NEEDED] Marker | Warning |
| NON-BLOCKING | Word-Count < Target | CONTINUE + [LOW-WORD-COUNT] Marker | Warning |
| NON-BLOCKING | Word-Count > Target | CONTINUE + [HIGH-WORD-COUNT] Marker | Warning |
| NON-BLOCKING | Missing Figure | CONTINUE + [MISSING FIGURE] Placeholder | Optional |
| FALLBACK | Top-K == 1 (nur 1 Draft) | Direct Uebernahme + Polishing statt Merge | Info |
| FALLBACK | Alle Drafts < 50% Word-Count | Best-Effort Merge mit allen verfuegbaren Sections | Warning |

---

## HINWEISE

- **Keine eigene Draft-Bewertung:** synthesis verwendet AUSSCHLIESSLICH das Ranking aus review-matrix.json
- **Worker-Rolle:** Dieser Command trifft KEINE Loop-Entscheidungen (Quality-Loop wird durch Controller gesteuert)
- **Kein MCP:** synthesis arbeitet NUR mit lokalen Dateien (Read/Write Tools)
- **Consensus-Building nur bei hard:** 3-Way Merge mit Consensus/Dissent-Analyse nur bei difficulty=hard
- **Pipeline-Position:** NACH review (braucht review-matrix.json), VOR reflect (final-draft ist dessen Input)
- **M6-Reihenfolge:** OUTPUT → _manifest.md → session-state.json → NOTIFY (State-Update-Protokoll)
- **Citation-Density-Thresholds:** easy=2.0, normal=3.0, hard=4.0 Citations per Page (aus W3)
- **Word-Count-Target:** 6250-8750 Worte bei 25-Seiten-Ziel (aus W10)
- **Figure-Integration:** Ersetzt Placeholder durch tatsaechliche Pfade, behaelt [MISSING FIGURE] bei Luecken
- **Kohaerenz-Check:** Roter Faden und Terminologie-Konsistenz explizit pruefen

---

**FINAL NOTE:** Dieser Command ist der SYNTHESIS-Kern der WritePaper-Pipeline. Er transformiert Top-K konkurrierende Drafts in EINEN optimalen Final Draft durch strategischen Merge. Die difficulty-Skalierung (Direct/2-Way/3-Way) stellt sicher, dass der Aufwand der Aufgaben-Komplexitaet entspricht. Nach synthesis ist der Kapitel-Draft bereit fuer Reflection (Learnings extrahieren) und anschliessende LaTeX-Integration.
