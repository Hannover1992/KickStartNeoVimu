# /_WP_structure - Paper-Strukturextraktion

```yaml
status: active
version: 1.0.0
last_updated: 2026-02-08
author: OmniCommand System
category: Research/WritePaper
difficulty: normal
estimated_time: 5min
type: building-block
```

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_WP_structure                                               ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: STRUCTURE EXTRACTOR                                               ║
║   TUT:                                                                   ║
║     - LaTeX-Datei parsen nach \chapter{...}                              ║
║     - Kapitel-Themen extrahieren                                         ║
║     - Archetyp-Klassifikation pro Kapitel (A/B)                          ║
║     - Kapitel-Reihenfolge validieren                                     ║
║   NICHT:                                                                 ║
║     - Inhalte schreiben (→ write)                                        ║
║     - Quellen zuordnen (→ assess)                                        ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md                                                        ║
║   2. session-state.json                                                  ║
║   3. config/project.yaml (research_questions)                            ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. output/chapter-structure.md (5 Kapitel + Sections)                  ║
║   2. output/temperature-profile.json (EXPLORATION_LEVEL pro Kapitel)     ║
║   3. _manifest.md (UPDATE: chapters[], next_step=assess)                 ║
║   4. session-state.json (UPDATE: chapters, archetyps, temperatures)      ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LINEAR                                                           ║
║   AFTER: /_WP_session                                                  ║
║   BEFORE: /_WP_assess (Kapitel 1)                                      ║
║   PHASE: Setup                                                           ║
║   CHAIN: [session] → [structure] → [Kapitel-Loop-Start]                  ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   easy:   3 Sections/Kapitel, einfache Archetyp-Heuristik                ║
║   normal: 4-5 Sections/Kapitel, regelbasierte Archetypen                 ║
║   hard:   5-6 Sections/Kapitel, adaptive Archetyp-Erkennung              ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper Kapitelstruktur erstellt'"     ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: setup                                                            ║
║   op: WritePaper                                                         ║
║   chain-position: structure                                              ║
║   prev: "[[WritePaper-session]]"                                         ║
║   next: "[[WritePaper-assess-ch1]]"                                      ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

### TUT (Kernaufgabe)
- LaTeX-Template parsen oder Standard-Struktur generieren
- Kapitel nach Archetypen klassifizieren (A=Exploration, B=Technical)
- Sections pro Kapitel mit geschätztem Umfang erstellen
- Temperatur-Profil pro Kapitel basierend auf Archetyp berechnen
- Kapitel-Reihenfolge validieren (logischer Fluss)

### TUT NICHT (Out of Scope)
- Inhalte schreiben → Das macht /_WP_write
- Quellen pro Kapitel zuordnen → Das macht /_WP_assess
- RAG-Queries ausführen → Das macht /_WP_assess
- LaTeX-Dokument rendern → Das macht /_WP_finalize

### Eskalation
- **FEHLER:** Falls _manifest.md fehlt oder next_step ≠ structure
  → STOP mit Error-Message: "Vorherige Session nicht abgeschlossen"
- **FEHLER:** Falls config/project.yaml keine research_questions hat
  → STOP mit Error-Message: "Forschungsfragen fehlen in Projekt-Config"
- **WARNUNG:** Falls Template.tex nicht parsbar
  → Fallback auf Standard-5-Kapitel-Struktur

---

## Ablauf

### Schritt 0: Inputs validieren
**Action:**
```bash
# Pruefe Existenz aller Input-Dateien
test -f _manifest.md || { echo "ERROR: _manifest.md fehlt"; exit 1; }
test -f session-state.json || { echo "ERROR: session-state.json fehlt"; exit 1; }
test -f config/project.yaml || { echo "ERROR: project.yaml fehlt"; exit 1; }
```

**Lies:**
- `_manifest.md` → Pruefe: `next_step: structure`
- `session-state.json` → Hole: difficulty, dimensions, temperature_base
- `config/project.yaml` → Hole: research_questions (Liste)

**Validierung:**
- Falls next_step ≠ structure → STOP mit Error
- Falls research_questions leer → STOP mit Error

---

### Schritt 1: Paper-Struktur bestimmen

**Option A: LaTeX-Template vorhanden**
```bash
# Falls output/template.tex existiert
if [ -f output/template.tex ]; then
    # Parse \chapter{...} mit Regex
    grep "\\chapter{" output/template.tex | sed 's/.*\\chapter{\(.*\)}.*/\1/'
fi
```

**Option B: Keine Vorlage → Standard-Struktur**

Generiere Standard-5-Kapitel-Struktur:

1. **Einleitung**
   - Motivation und Kontext
   - Forschungsfragen (aus research_questions)
   - Aufbau der Arbeit

2. **Theoretischer Hintergrund**
   - Stand der Forschung
   - Grundlagen und Konzepte
   - Verwandte Arbeiten

3. **Methodik**
   - Vorgehen und Methoden
   - Tools und Technologien
   - Datenquellen

4. **Ergebnisse**
   - Implementierung
   - Evaluation
   - Diskussion

5. **Fazit**
   - Zusammenfassung
   - Beitrag der Arbeit
   - Ausblick und zukünftige Arbeiten

---

### Schritt 2: Archetyp-Klassifikation

**Archetypen:**
- **Archetyp A (Exploration):** Breite Recherche, hohe Temperatur, viele Quellen
  → Typische Kapitel: Einleitung, Theoretischer Hintergrund
- **Archetyp B (Technical):** Fokussierte Tiefe, niedrige Temperatur, präzise Quellen
  → Typische Kapitel: Methodik, Ergebnisse, Fazit

**Klassifikations-Logik nach Schwierigkeitsgrad:**

**easy:** Heuristik (Position-basiert)
```python
if chapter_number <= 2:
    archetyp = "A"  # Exploration
else:
    archetyp = "B"  # Technical
```

**normal:** Regelbasiert (Keyword-Analyse)
```python
exploration_keywords = ["einleitung", "hintergrund", "stand", "forschung", "verwandt"]
technical_keywords = ["methodik", "implementierung", "ergebnis", "evaluation", "fazit"]

if any(kw in chapter_title.lower() for kw in exploration_keywords):
    archetyp = "A"
elif any(kw in chapter_title.lower() for kw in technical_keywords):
    archetyp = "B"
else:
    archetyp = "A"  # Default
```

**hard:** Adaptiv (Research-Question-Matching)
```python
# Pro Kapitel: Matche Kapitel-Thema gegen research_questions
# Berechne Ähnlichkeit (z.B. Keyword-Overlap)
# Wenn hohe Ähnlichkeit zu explorativen Fragen → A
# Wenn hohe Ähnlichkeit zu technischen Fragen → B
```

---

### Schritt 3: Sections pro Kapitel generieren

**Sections-Anzahl nach Schwierigkeitsgrad:**
- easy: 3 Sections/Kapitel
- normal: 4-5 Sections/Kapitel
- hard: 5-6 Sections/Kapitel

**Sections-Logik:**

Für jedes Kapitel:
1. Bestimme Kern-Themen basierend auf Kapitel-Titel
2. Generiere Section-Titel (logische Unterteilung)
3. Schätze Umfang pro Section (z.B. 2-3 Seiten)

**Beispiel (Kapitel 1 - Einleitung, normal):**
```
1.1 Motivation und Kontext (2 Seiten)
1.2 Forschungsfragen (1 Seite)
1.3 Zielsetzung der Arbeit (1 Seite)
1.4 Aufbau der Arbeit (0.5 Seiten)
```

---

### Schritt 4: Temperatur-Profil erstellen

**Input:** temperature_base aus session-state.json (z.B. 1.0)

**Archetyp-Anpassung:**
- Archetyp A (Exploration): temperature = temperature_base + 0.1 bis +0.2
- Archetyp B (Technical): temperature = temperature_base - 0.1 bis -0.2

**Exploration-Level-Mapping:**
```python
if temperature >= 1.15:
    exploration_level = "high"
elif temperature >= 0.95:
    exploration_level = "medium"
else:
    exploration_level = "low"
```

**Schreibe:** `output/temperature-profile.json`
```json
{
  "base_temperature": 1.0,
  "chapters": {
    "1": {
      "title": "Einleitung",
      "archetyp": "A",
      "temperature": 1.2,
      "exploration_level": "high",
      "sections_count": 4
    },
    "2": {
      "title": "Theoretischer Hintergrund",
      "archetyp": "A",
      "temperature": 1.1,
      "exploration_level": "high",
      "sections_count": 5
    },
    "3": {
      "title": "Methodik",
      "archetyp": "B",
      "temperature": 0.9,
      "exploration_level": "low",
      "sections_count": 4
    },
    "4": {
      "title": "Ergebnisse",
      "archetyp": "B",
      "temperature": 0.85,
      "exploration_level": "low",
      "sections_count": 5
    },
    "5": {
      "title": "Fazit",
      "archetyp": "B",
      "temperature": 0.9,
      "exploration_level": "low",
      "sections_count": 3
    }
  }
}
```

---

### Schritt 5: State aktualisieren

**Schreibe:** `output/chapter-structure.md`
```markdown
# Paper-Struktur

Generiert: 2026-02-08
Schwierigkeitsgrad: normal
Kapitel: 5

---

## Kapitel 1: Einleitung
**Archetyp:** A (Exploration)
**Temperatur:** 1.2 (high)
**Sections:** 4

### 1.1 Motivation und Kontext
Geschätzter Umfang: 2 Seiten

### 1.2 Forschungsfragen
Geschätzter Umfang: 1 Seite

### 1.3 Zielsetzung der Arbeit
Geschätzter Umfang: 1 Seite

### 1.4 Aufbau der Arbeit
Geschätzter Umfang: 0.5 Seiten

---

## Kapitel 2: Theoretischer Hintergrund
**Archetyp:** A (Exploration)
**Temperatur:** 1.1 (high)
**Sections:** 5

### 2.1 Stand der Forschung
Geschätzter Umfang: 3 Seiten

### 2.2 Grundlagen und Konzepte
Geschätzter Umfang: 2 Seiten

### 2.3 Verwandte Arbeiten
Geschätzter Umfang: 2 Seiten

### 2.4 Forschungslücke
Geschätzter Umfang: 1 Seite

### 2.5 Positionierung der Arbeit
Geschätzter Umfang: 1 Seite

---

[... Kapitel 3-5 analog ...]
```

**Update:** `_manifest.md`
```yaml
chapters:
  - id: 1
    title: "Einleitung"
    archetyp: "A"
    status: "pending"
  - id: 2
    title: "Theoretischer Hintergrund"
    archetyp: "A"
    status: "pending"
  - id: 3
    title: "Methodik"
    archetyp: "B"
    status: "pending"
  - id: 4
    title: "Ergebnisse"
    archetyp: "B"
    status: "pending"
  - id: 5
    title: "Fazit"
    archetyp: "B"
    status: "pending"

next_step: assess
next_chapter: 1
```

**Update:** `session-state.json`
```json
{
  "structure_complete": true,
  "chapters": [
    {"id": 1, "title": "Einleitung", "archetyp": "A", "sections": 4},
    {"id": 2, "title": "Theoretischer Hintergrund", "archetyp": "A", "sections": 5},
    {"id": 3, "title": "Methodik", "archetyp": "B", "sections": 4},
    {"id": 4, "title": "Ergebnisse", "archetyp": "B", "sections": 5},
    {"id": 5, "title": "Fazit", "archetyp": "B", "sections": 3}
  ],
  "archetyps": {
    "A_count": 2,
    "B_count": 3
  },
  "temperature_profile": "output/temperature-profile.json"
}
```

---

## Output-Format

### Primäre Outputs

**1. output/chapter-structure.md**
- Markdown-formatierte Kapitel-Liste
- Pro Kapitel: Titel, Archetyp, Temperatur, Sections mit Titeln
- Geschätzter Umfang pro Section

**2. output/temperature-profile.json**
- JSON mit base_temperature und chapters{}
- Pro Kapitel: title, archetyp, temperature, exploration_level, sections_count

**3. _manifest.md (UPDATE)**
- chapters[] Array mit id, title, archetyp, status
- next_step = "assess"
- next_chapter = 1

**4. session-state.json (UPDATE)**
- structure_complete = true
- chapters[] Array
- archetyps{} Statistik
- temperature_profile Pfad

---

## Qualitätskriterien

### MUSS-Kriterien
- [ ] Alle 5 Kapitel haben Titel und Archetyp
- [ ] Jedes Kapitel hat >= 3 Sections (je nach Schwierigkeit)
- [ ] Temperatur-Profil konsistent mit Archetypen (A=höher, B=niedriger)
- [ ] Kapitel-Reihenfolge logisch (Einleitung → Hintergrund → Methodik → Ergebnisse → Fazit)
- [ ] Alle 4 Output-Dateien geschrieben

### SOLL-Kriterien
- [ ] Section-Titel sind präzise und spezifisch
- [ ] Geschätzter Umfang pro Section realistisch (0.5-3 Seiten)
- [ ] Archetyp-Klassifikation passt zu Kapitel-Thema
- [ ] Temperatur-Profil berücksichtigt research_questions

### KANN-Kriterien
- [ ] Adaptive Archetyp-Erkennung bei hard-Modus
- [ ] Section-Titel matchen research_questions
- [ ] Umfang-Schätzung basierend auf Kapitel-Komplexität

---

## NOTIFY

Nach erfolgreicher Ausführung:
```powershell
powershell -Command "notify 'WritePaper Kapitelstruktur erstellt'"
```

**Konsolen-Output:**
```
✓ Paper-Struktur extrahiert
  - 5 Kapitel mit 21 Sections
  - 2 Archetyp-A (Exploration), 3 Archetyp-B (Technical)
  - Temperatur-Profil: 0.85-1.2

→ Nächster Schritt: /_WP_assess (Kapitel 1)
```

---

## Siehe auch
- [[WritePaper-session]] (Vorheriger Schritt)
- [[WritePaper-assess]] (Nächster Schritt)
- [[WritePaper-workflow]] (Gesamt-Ablauf)
