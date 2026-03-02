# /_WP_visual - Visual Figure Generation & Review

---
status: active
version: 1.0.0
created: 2026-02-09
op: WritePaper
phase: Core Transformation
type: HiL-blocking
chain_position: 9
difficulty_scaling: true
---

## VERTRAG

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. ACTOR        = Claude (Sonnet 4.5)                                       │
│ 2. LIEST        = output/drafts/chapter-{N}/*.md (Drafts mit Placeholders)  │
│                   _manifest.md, session-state.json, config/project.yaml     │
│ 3. SCHREIBT     = output/figures/chapter-{N}/fig-{NN}.{ext}                 │
│                   output/figures/chapter-{N}/figure-report.json             │
│                   _manifest.md (UPDATE), session-state.json (UPDATE)        │
│ 4. POSITION     = AFTER /_WP_write, BEFORE /_WP_qualityGate             │
│                   TYPE: LINEAR, PHASE: Core Transformation                  │
│ 5. MCP-BREMSE   = N/A (keine MCP-Tools, lokale Figure-Tools)                │
│ 6. ORCHESTRIERT = NEIN (linearer Step in Kapitel-Loop)                      │
│ 7. ENTSCHEIDET  = NEIN (User entscheidet bei HiL-PAUSE)                     │
│ 8. HiL-PAUSE    = JA (BLOCKING Review nach Figure-Generierung)              │
│                   User-Optionen: APPROVE / REWORK / SKIP                    │
│                   Timeout: difficulty-dependent (5|10|15 min)               │
│ 9. SCHWIERIGKEIT= easy: 2-3 Figures, Mermaid only                           │
│                   normal: 4-6 Figures, Mermaid + matplotlib                 │
│                   hard: 8-12 Figures, Mermaid + matplotlib + TikZ           │
│10. NOTIFY       = Success: "Kapitel {N} Figures: {X}/{Y} generiert"         │
│                   Warning: "{M} Figures fehlgeschlagen (Placeholders)"      │
│                   Error: "output/drafts/ fehlt, run /_WP_write first"     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Verantwortlichkeit

### TUT
- [FIGURE: ...] Placeholders aus allen Drafts extrahieren
- Figures klassifizieren (Mermaid | matplotlib | TikZ)
- Fallback-Kette anwenden: Mermaid → matplotlib → TikZ → [MISSING FIGURE]
- Figures speichern in output/figures/chapter-{N}/
- HiL-PAUSE: User Figure-Report zeigen, auf Aktion warten
- State aktualisieren (_manifest.md, session-state.json)

### TUT NICHT
- Figures ohne User-Review weiterleiten (HiL-PAUSE ist PFLICHT)
- Bei totalem Fehler abbrechen (Placeholder setzen, NOTIFY)
- MCP-Tools verwenden (Figure-Generation ist lokal)
- Difficulty ignorieren (Tool-Auswahl ist difficulty-dependent)

### ESKALATION
- BLOCKING: output/drafts/chapter-{N}/ fehlt → Error + empfehle /_WP_write
- BLOCKING: Alle Tools fehlen (mmdc, python, pdflatex nicht installiert) → Error
- NON-BLOCKING: Einzelne Figures fehlgeschlagen → Fallback-Kette → Placeholder
- User bei HiL-PAUSE timeout (default: APPROVE)

## Ablauf

### Schritt 0: Inputs lesen & Validieren
**Ziel:** Pipeline-Kontext laden, Kapitel-Nummer ermitteln, Drafts validieren

**Aktionen:**
1. Read `_manifest.md` → current_chapter, phase
2. Read `session-state.json` → difficulty, quality_iteration
3. Read `config/project.yaml` → current_chapter (Validation)
4. Read `output/drafts/chapter-{N}/metadata.json` → draft_count, total_figures
5. BLOCKING-Check: Verzeichnis output/drafts/chapter-{N}/ existiert?
6. BLOCKING-Check: Mindestens 1 Draft vorhanden?

**Validierung:**
- `current_chapter` konsistent zwischen _manifest.md und config/project.yaml
- `output/drafts/chapter-{N}/` existiert
- Mindestens 1 Draft-Datei `draft-A{NN}.md` vorhanden
- `difficulty` ∈ {easy, normal, hard}

**Erfolgskriterium:**
- Kapitel-Nummer N bekannt
- Difficulty bekannt
- Drafts-Verzeichnis validiert
- Keine BLOCKING-Errors

---

### Schritt 1: Figure-Placeholder-Extraktion
**Ziel:** Alle [FIGURE: ...] Placeholders aus Drafts extrahieren, deduplizieren

**Aktionen:**
1. Glob alle Drafts: `output/drafts/chapter-{N}/draft-A*.md`
2. Pro Draft: Grep nach Pattern `\[FIGURE:\s*([^\]]+)\]`
3. Extrahiere description aus Capture-Group
4. Dedupliziere nach description (gleiche Beschreibung = 1 Figure)
5. Erstelle Figure-Plan:
   ```json
   {
     "figure_id": "fig-01",
     "description": "System Architecture Overview",
     "draft_source": "draft-A01.md",
     "line_number": 42,
     "suggested_type": null,  // wird in Schritt 2 gesetzt
     "priority": "high"  // high wenn in mehreren Drafts
   }
   ```

**Validierung:**
- Mindestens 1 Figure-Placeholder gefunden (sonst WARNING + SKIP möglich)
- Figure-IDs eindeutig (fig-01, fig-02, ...)
- Descriptions nicht leer

**Erfolgskriterium:**
- Figure-Plan mit N Einträgen erstellt
- N ≤ difficulty_threshold (2-3 easy | 4-6 normal | 8-12 hard)
- Bei N > threshold: WARNING, aber weiter

---

### Schritt 2: Figure-Klassifikation
**Ziel:** Pro Figure bestes Tool bestimmen basierend auf description & difficulty

**Aktionen:**
1. Pro Figure-Plan-Eintrag: Analysiere description
2. Keyword-basierte Klassifikation:
   - Mermaid: "flowchart", "sequence", "class diagram", "state", "ER diagram"
   - matplotlib: "chart", "plot", "graph", "statistics", "data", "histogram"
   - TikZ: "mathematical", "technical", "circuit", "formula", "complex diagram"
3. Difficulty-Filter:
   - easy: Nur Mermaid erlaubt → Falls matplotlib/TikZ: Downgrade zu Mermaid
   - normal: Mermaid + matplotlib erlaubt → TikZ → Downgrade zu matplotlib
   - hard: Alle Tools erlaubt
4. Setze `suggested_type` im Figure-Plan
5. Bestimme Fallback-Kette pro Figure:
   ```
   Primary → Secondary → Tertiary → Placeholder
   Mermaid → matplotlib → TikZ → [MISSING FIGURE]
   ```

**Validierung:**
- Jede Figure hat `suggested_type` ∈ {mermaid, matplotlib, tikz}
- Fallback-Kette definiert
- Tool-Verteilung passt zu difficulty

**Erfolgskriterium:**
- Alle Figures klassifiziert
- Tool-Distribution-Report erstellt:
  ```
  Mermaid: 3, matplotlib: 2, TikZ: 1
  ```

---

### Schritt 3: Figure-Generierung (Fallback-Kette)
**Ziel:** Pro Figure: Generiere Bild mit primary Tool, bei Fehler Fallback

**Aktionen:**
1. Pro Figure im Figure-Plan:

   **A) Mermaid-Generation:**
   - Erstelle .mmd Datei aus description (Mermaid-Syntax generieren)
   - Bash: `mmdc -i temp.mmd -o output/figures/chapter-{N}/fig-{NN}.png`
   - Timeout: 30s
   - Bei Fehler → Fallback zu matplotlib

   **B) matplotlib-Generation:**
   - Erstelle .py Skript aus description (matplotlib-Code generieren)
   - Bash: `python temp.py` (speichert nach output/figures/chapter-{N}/fig-{NN}.png)
   - Timeout: 45s
   - Bei Fehler → Fallback zu TikZ

   **C) TikZ-Generation:**
   - Erstelle .tex Datei mit TikZ-Code aus description
   - Bash: `pdflatex -output-directory=output/figures/chapter-{N}/ temp.tex`
   - Konvertiere PDF → PNG via ImageMagick: `convert fig.pdf fig.png`
   - Timeout: 60s
   - Bei Fehler → Fallback zu Placeholder

   **D) Placeholder-Fallback:**
   - Kein Bild generiert
   - Setze in Figure-Plan: `status: "missing"`
   - Später in Draft einfügen: `[MISSING FIGURE: {description}]`

2. Pro erfolgreich generierte Figure:
   - Speichere in `output/figures/chapter-{N}/fig-{NN}.{ext}`
   - Erstelle Metadata:
     ```json
     {
       "figure_id": "fig-01",
       "description": "...",
       "tool_used": "mermaid",
       "file_path": "output/figures/chapter-1/fig-01.png",
       "fallback_level": 0,  // 0=primary, 1=secondary, 2=tertiary, 3=placeholder
       "status": "success"
     }
     ```

**Validierung:**
- Pro Figure: status ∈ {success, missing}
- Erfolgreiche Figures: Datei existiert, Dateigröße > 0
- Missing Figures: Logged in figure-report.json

**Erfolgskriterium:**
- Mindestens 1 Figure erfolgreich generiert ODER alle Placeholders gesetzt
- Figure-Report komplett:
  ```json
  {
    "total_figures": 6,
    "generated": 4,
    "missing": 2,
    "tool_distribution": {"mermaid": 3, "matplotlib": 1},
    "fallback_stats": {"primary": 3, "secondary": 1, "placeholder": 2}
  }
  ```

---

### Schritt 4: HiL-PAUSE (BLOCKING Review)
**Ziel:** User zeigt Figure-Report, wartet auf User-Aktion

**Aktionen:**
1. Erstelle Human-Readable-Report:
   ```
   ╔═══════════════════════════════════════════════════════╗
   ║ WritePaper Kapitel {N} - Figure Generation Report    ║
   ╠═══════════════════════════════════════════════════════╣
   ║ Total Figures:    6                                   ║
   ║ Generated:        4  (67%)                            ║
   ║ Missing:          2  (33%)                            ║
   ║                                                       ║
   ║ Tool Distribution:                                    ║
   ║   Mermaid:        3                                   ║
   ║   matplotlib:     1                                   ║
   ║   TikZ:           0                                   ║
   ║                                                       ║
   ║ Missing Figures:                                      ║
   ║   - fig-03: "Complex state diagram" (all tools failed)║
   ║   - fig-05: "Data plot" (matplotlib timeout)          ║
   ║                                                       ║
   ║ Location: output/figures/chapter-1/                   ║
   ╚═══════════════════════════════════════════════════════╝

   OPTIONEN:
   [A] APPROVE   - Weiter zu /_WP_qualityGate
   [R] REWORK    - Nochmal generieren mit Korrekturen
   [S] SKIP      - Weiter ohne fehlende Figures (Placeholders bleiben)

   Timeout: {5|10|15} min (difficulty-dependent)
   ```

2. NOTIFY:
   - Success (falls generated > 0): "Kapitel {N} Figures: {X}/{Y} generiert"
   - Warning (falls missing > 0): "{M} Figures fehlgeschlagen (Placeholders)"
   - Info: "Bitte prüfen Sie output/figures/chapter-{N}/"

3. Warte auf User-Input:
   - User gibt APPROVE / REWORK / SKIP
   - Bei REWORK: User gibt Korrekturen (z.B. "fig-03: Use simpler Mermaid flowchart instead of state")
   - Bei Timeout: Default APPROVE

4. Verarbeite User-Aktion:
   - APPROVE: Weiter zu Schritt 5
   - REWORK: Wiederhole Schritt 3 für angegebene Figures
   - SKIP: Alle missing Figures bleiben Placeholders, weiter zu Schritt 5

**Validierung:**
- User-Input ∈ {APPROVE, REWORK, SKIP}
- Bei REWORK: Korrekturen klar spezifiziert

**Erfolgskriterium:**
- User-Aktion verarbeitet
- Bei APPROVE/SKIP: Alle Figures finalized (success oder missing)
- Bei REWORK: Neue Generation erfolgreich

---

### Schritt 5: State aktualisieren (M6 Reihenfolge)
**Ziel:** Outputs schreiben, State-Files aktualisieren, NOTIFY

**Aktionen (M6-konforme Reihenfolge: OUTPUT → MANIFEST → STATE → NOTIFY):**

1. **OUTPUT schreiben:**
   - `output/figures/chapter-{N}/fig-{NN}.{ext}` (bereits in Schritt 3)
   - `output/figures/chapter-{N}/figure-report.json`:
     ```json
     {
       "chapter": 1,
       "total_figures": 6,
       "generated": 4,
       "missing": 2,
       "figures": [
         {
           "figure_id": "fig-01",
           "description": "System Architecture",
           "tool_used": "mermaid",
           "file_path": "output/figures/chapter-1/fig-01.png",
           "status": "success",
           "fallback_level": 0
         },
         {
           "figure_id": "fig-03",
           "description": "Complex state diagram",
           "status": "missing",
           "fallback_level": 3
         }
       ],
       "tool_distribution": {"mermaid": 3, "matplotlib": 1},
       "hil_decision": "APPROVE",
       "timestamp": "2026-02-09T14:30:00Z"
     }
     ```

2. **_manifest.md UPDATE:**
   - Frontmatter aktualisieren:
     ```yaml
     figures_count: 4
     figures_missing: 2
     next_step: qualityGate
     last_updated: 2026-02-09T14:30:00Z
     ```
   - Section "## WritePaper Progress" aktualisieren:
     ```markdown
     - [x] /_WP_write (Kapitel 1)
     - [x] /_WP_visual (Kapitel 1, 4/6 Figures)
     - [ ] /_WP_qualityGate (Kapitel 1)
     ```

3. **session-state.json UPDATE:**
   ```json
   {
     "figures_generated": 4,
     "figures_missing": 2,
     "hil_decision": "APPROVE",
     "visual_iteration": 1,
     "last_command": "/_WP_visual",
     "timestamp": "2026-02-09T14:30:00Z"
   }
   ```

4. **NOTIFY:**
   - Success: "✓ Kapitel {N} Figures: {X}/{Y} generiert. Next: /_WP_qualityGate"
   - Warning (falls missing > 0): "⚠ {M} Figures fehlgeschlagen (Placeholders gesetzt)"
   - Info: "Review: output/figures/chapter-{N}/"

**Validierung:**
- figure-report.json valides JSON
- _manifest.md Frontmatter korrekt
- session-state.json valides JSON
- NOTIFY gesendet

**Erfolgskriterium:**
- Alle State-Updates committed
- User informiert über nächsten Schritt
- Pipeline bereit für /_WP_qualityGate

---

## Output-Format

### output/figures/chapter-{N}/figure-report.json
```json
{
  "chapter": 1,
  "total_figures": 6,
  "generated": 4,
  "missing": 2,
  "figures": [
    {
      "figure_id": "fig-01",
      "description": "System Architecture Overview",
      "tool_used": "mermaid",
      "file_path": "output/figures/chapter-1/fig-01.png",
      "status": "success",
      "fallback_level": 0,
      "draft_source": "draft-A01.md",
      "line_number": 42
    },
    {
      "figure_id": "fig-02",
      "description": "Data Flow Chart",
      "tool_used": "matplotlib",
      "file_path": "output/figures/chapter-1/fig-02.png",
      "status": "success",
      "fallback_level": 1
    },
    {
      "figure_id": "fig-03",
      "description": "Complex state diagram",
      "tool_used": null,
      "file_path": null,
      "status": "missing",
      "fallback_level": 3,
      "error": "All tools failed: mermaid syntax error, matplotlib timeout, tikz not installed"
    }
  ],
  "tool_distribution": {
    "mermaid": 3,
    "matplotlib": 1,
    "tikz": 0
  },
  "fallback_stats": {
    "primary_success": 3,
    "secondary_success": 1,
    "tertiary_success": 0,
    "placeholder": 2
  },
  "hil_decision": "APPROVE",
  "rework_iterations": 0,
  "timestamp": "2026-02-09T14:30:00Z"
}
```

### _manifest.md UPDATE (Frontmatter)
```yaml
---
current_chapter: 1
phase: Core Transformation
figures_count: 4
figures_missing: 2
next_step: qualityGate
last_updated: 2026-02-09T14:30:00Z
---
```

### session-state.json UPDATE
```json
{
  "difficulty": "normal",
  "quality_iteration": 0,
  "figures_generated": 4,
  "figures_missing": 2,
  "hil_decision": "APPROVE",
  "visual_iteration": 1,
  "last_command": "/_WP_visual",
  "timestamp": "2026-02-09T14:30:00Z"
}
```

---

## Qualitätskriterien

- [ ] Alle [FIGURE: ...] Placeholders aus Drafts extrahiert
- [ ] Figures korrekt klassifiziert (Mermaid | matplotlib | TikZ)
- [ ] Fallback-Kette angewendet (Primary → Secondary → Tertiary → Placeholder)
- [ ] Difficulty-Thresholds eingehalten (easy: 2-3, normal: 4-6, hard: 8-12)
- [ ] Difficulty-Tool-Filter angewendet (easy: nur Mermaid)
- [ ] HiL-PAUSE durchgeführt (User-Report + Warten auf Aktion)
- [ ] User-Optionen korrekt verarbeitet (APPROVE / REWORK / SKIP)
- [ ] figure-report.json vollständig und valide
- [ ] Alle erfolgreichen Figures: Datei existiert, Größe > 0
- [ ] Missing Figures: Logged mit error-Grund
- [ ] _manifest.md aktualisiert (figures_count, next_step)
- [ ] session-state.json aktualisiert (figures_generated, hil_decision)
- [ ] M6-Reihenfolge: OUTPUT → MANIFEST → STATE → NOTIFY
- [ ] NOTIFY gesendet (Success + Warning falls missing > 0)
- [ ] Bei BLOCKING-Error: Pipeline gestoppt, Error-NOTIFY, Empfehlung gegeben

---

## NOTIFY

### Success
```
✓ WritePaper Kapitel {N} - Visual Generation abgeschlossen
  Figures: {X}/{Y} generiert ({P}%)
  Tool-Verteilung: Mermaid={M}, matplotlib={P}, TikZ={T}
  Location: output/figures/chapter-{N}/
  Next: /_WP_qualityGate
```

### Warning
```
⚠ WritePaper Kapitel {N} - {M} Figures fehlgeschlagen
  Placeholders gesetzt: [MISSING FIGURE: ...]
  Betroffene Figures: fig-{NN}, fig-{MM}
  Prüfen Sie figure-report.json für Details
  Pipeline fährt fort (Placeholders erlaubt)
```

### Error
```
✗ WritePaper Kapitel {N} - Visual Generation BLOCKIERT
  Grund: {error_reason}

  BLOCKING-Errors:
  - output/drafts/chapter-{N}/ fehlt
    → Run /_WP_write first

  - Keine Drafts vorhanden
    → Run /_WP_write first

  - Alle Tools fehlen (mmdc, python, pdflatex nicht installiert)
    → Install: npm install -g @mermaid-js/mermaid-cli
    → Install: pip install matplotlib
    → Install: apt-get install texlive-latex-base
```

---

## Error Handling

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| **BLOCKING** | output/drafts/chapter-{N}/ fehlt | STOP + Error-NOTIFY + Empfehle /_WP_write | JA (ERROR) |
| **BLOCKING** | Keine Draft-Dateien vorhanden | STOP + Error-NOTIFY + Empfehle /_WP_write | JA (ERROR) |
| **BLOCKING** | Alle Tools fehlen (mmdc, python, pdflatex) | STOP + Error-NOTIFY + Installation-Instructions | JA (ERROR) |
| **NON-BLOCKING** | 1 Figure fehlgeschlagen (Tool-Error) | CONTINUE + Nächstes Tool in Fallback-Kette | Optional (INFO) |
| **NON-BLOCKING** | Tool-Timeout (30s/45s/60s überschritten) | CONTINUE + Nächstes Tool in Fallback-Kette | Optional (INFO) |
| **FALLBACK** | Alle 3 Tools für 1 Figure fehlgeschlagen | [MISSING FIGURE: beschreibung] Placeholder setzen | JA (WARNING) |
| **FALLBACK** | Mehr Figures als difficulty-threshold | WARNING + Weiter (keine harte Grenze) | JA (INFO) |
| **FALLBACK** | HiL-PAUSE Timeout (User reagiert nicht) | Default APPROVE + Weiter | JA (INFO) |

---

## Hinweise

1. **Fallback-Kette ist PFLICHT:** Nie bei erstem Tool-Fehler abbrechen
2. **HiL-PAUSE ist BLOCKING:** User MUSS Figures reviewen (außer Timeout)
3. **Placeholders sind OK:** Missing Figures blockieren Pipeline NICHT
4. **Difficulty steuert Tools:** easy=nur Mermaid, normal=+matplotlib, hard=+TikZ
5. **M6-Reihenfolge:** OUTPUT → MANIFEST → STATE → NOTIFY (immer!)
6. **Tool-Installation:** User muss mmdc/python/pdflatex selbst installieren
7. **Figure-Quality:** User-Verantwortung bei HiL-PAUSE (nicht automatisch)
8. **REWORK-Limit:** Maximal 2 REWORK-Iterationen, dann SKIP empfehlen
9. **Namespace:** KEINE MCP-Tools (lokal: mmdc, python, pdflatex)
10. **Next Step:** Immer /_WP_qualityGate nach APPROVE/SKIP

---

**Pipeline-Position:** [write] → **[visual]** → [qualityGate] → [autoGen] → [convergence]
