# Praesentation: Ergebnisse aufbereiten

Du erstellst eine Praesentation der Arbeitsergebnisse - angepasst an den Kontext.

## Aufruf

```
/_presentation [PR|BRAINSTORM|ZWISCHENERGEBNIS]
```

Default ohne Parameter: **ZWISCHENERGEBNIS**

---

## VERTRAG (Pflicht-I/O)

```
╔═══════════════════════════════════════════════════════════════╗
║  COMMAND: /_presentation                                     ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  LIEST (Input):                                               ║
║    1. .claude/analysis/_manifest.md                            ║
║    2. .claude/models/{NAME}_Model.md (falls vorhanden) ║
║    3. .claude/analysis/synthese/{NAME}-HYPOTHESEN.md (falls vorh.)║
║    4. .claude/analysis/synthese/{NAME}-OBSERVE*.md (v2.2+)    ║
║    5. .claude/analysis/synthese/{NAME}-QUALITYGATE*.md (v2.2+)║
║    6. .claude/analysis/synthese/{NAME}-ANALYSE*.md (LEGACY)   ║
║    7. .claude/analysis/synthese/{NAME}-GAP.md (v3.0)          ║
║    8. .claude/specs/{NAME}_Spec.md (v3.0)                     ║
║    9. git diff (bei PR-Modus)                                 ║
║                                                               ║
║  SCHREIBT (Output) - PFLICHT:                                 ║
║    PR:              .claude/presentation/{TICKET}-PR.md       ║
║    BRAINSTORM:      .claude/presentation/{THEMA}-OPTIONS.md   ║
║    ZWISCHENERGEBNIS:.claude/presentation/{TICKET}-STATUS.md   ║
║                                                               ║
║  Manifest (IMMER):                                            ║
║    .claude/analysis/_manifest.md (aktualisieren)              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: Manifest + Kontext lesen

**Command-Max:** sonnet (effektiv = min(SYSTEM-MODEL, sonnet))

**IMMER als Erstes:**

1. Lies `.claude/analysis/_manifest.md`
   - Ermittle {NAME} und aktuellen Stand
   - Lies SYSTEM-MODEL aus System-Konfiguration
   - Bestimme effektives Modell: min(SYSTEM-MODEL, sonnet)
2. Pruefe welche Analyse-Dateien existieren
3. Lies verfuegbare Dateien als Kontext

---

## Modi

### Modus 1: PR (Pull Request)

**Wann:** Code ist fertig, soll vorgestellt/reviewed werden
**Zielgruppe:** Kollegen, Code-Reviewer, Architekten

```markdown
# {TICKET-ID}: {TITEL} - Technische Dokumentation

**Datum:** YYYY-MM-DD
**Status:** VERIFIZIERT
**Model:** {NAME}_Model.md v{X.Y}

## Executive Summary
{3-5 Saetze: Was, Warum, Wie}

## Problemstellung
{Mermaid-Diagramm: Erwartet vs. Erhalten}

## Architektur-Analyse
{Mermaid-Diagramm aus MODEL oder angepasst}

## Loesung
{Code-Aenderungen mit Mermaid}

## Geaenderte Dateien
| Datei | Aenderung |
|-------|----------|

## Test-Checkliste
- [ ] ...

## Referenzen
- {NAME}_Model.md
- Experiment W{n}
```

### Modus 2: BRAINSTORM

**Wann:** Loesungssuche, Optionen diskutieren

```markdown
# Loesungsoptionen fuer {PROBLEM}

## Problem-Statement
## Option 1: {NAME}
## Option 2: {NAME}

## Entscheidungs-Matrix
| Kriterium | Gewicht | Option 1 | Option 2 |
|-----------|---------|----------|----------|

## Empfehlung
```

### Modus 3: ZWISCHENERGEBNIS

**Wann:** Experiment laeuft, erste Erkenntnisse

```markdown
# Status-Update: {THEMA}

**Phase:** {aus Manifest}
**Model:** {NAME}_Model.md v{X.Y}

## Erkenntnisse
### Bestaetigt: W{n}
### Widerlegt: ...
### Offen: ...

## Naechste Schritte
## Blocker / Risiken
```

---

## Qualitaetskriterien

- Mermaid-Diagramme statt Prosa
- Executive Summary am Anfang
- Model-Referenzen wo moeglich
- Manifest nach Erstellung aktualisieren

---

## Naechster Schritt

Manifest aktualisieren, User informieren.

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_presentation abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
