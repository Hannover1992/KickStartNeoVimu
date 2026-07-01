---
type: satellite
---

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
║  LIEST (Input) — Vault-First (BL-050):                        ║
║    1. {VAULT}/_manifest.md                            ║
║    2. PRIMAER: {VAULT}/.../Model/{NAME}_Model.md              ║
║       FALLBACK: .claude/models/{NAME}_Model.md                ║
║    3. PRIMAER: {VAULT}/.../SC/{NAME}-HYPOTHESEN.md            ║
║       FALLBACK: .claude/analysis/synthese/{NAME}-HYPOTHESEN.md║
║    4. PRIMAER: {VAULT}/.../SC/{NAME}-OBSERVE*.md (v2.2+)     ║
║       FALLBACK: .claude/analysis/synthese/{NAME}-OBSERVE*.md  ║
║    5. PRIMAER: {VAULT}/.../SC/{NAME}-QUALITYGATE*.md (v2.2+) ║
║       FALLBACK: .claude/analysis/synthese/{NAME}-QUALITYGATE*.md║
║    6. .claude/analysis/synthese/{NAME}-ANALYSE*.md (LEGACY)   ║
║    7. PRIMAER: {VAULT}/.../Gap/{NAME}-GAP.md (v3.0)          ║
║       FALLBACK: .claude/analysis/synthese/{NAME}-GAP.md       ║
║    8. PRIMAER: {VAULT}/.../Spec/{NAME}_Spec.md (v3.0)        ║
║       FALLBACK: .claude/specs/{NAME}_Spec.md                  ║
║    9. git diff (bei PR-Modus)                                 ║
║                                                               ║
║  SCHREIBT (Output) - PFLICHT — Vault-First (BL-050):         ║
║    PR:              PRIMAER: {VAULT}/.../Presentations/{TICKET}-PR.md ║
║                     FALLBACK: .claude/presentation/{TICKET}-PR.md     ║
║    BRAINSTORM:      PRIMAER: {VAULT}/.../Presentations/{THEMA}-OPTIONS.md ║
║                     FALLBACK: .claude/presentation/{THEMA}-OPTIONS.md ║
║    ZWISCHENERGEBNIS:PRIMAER: {VAULT}/.../Presentations/{TICKET}-STATUS.md ║
║                     FALLBACK: .claude/presentation/{TICKET}-STATUS.md ║
║                                                               ║
║  Manifest (IMMER):                                            ║
║    {VAULT}/_manifest.md (aktualisieren)              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: Manifest + Kontext lesen

**Command-Max:** sonnet (effektiv = min(SYSTEM-MODEL, sonnet))

**IMMER als Erstes:**

1. Lies `{VAULT}/_manifest.md`
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

## EMAIL-VERSAND (Pflicht - nach Output-Datei geschrieben)

**NUR wenn Output-Datei erfolgreich geschrieben wurde.**

Sende die Praesentation als **Email-Body** (KEIN Attachment — MD-Inhalt = Email-Inhalt):

```bash
python3 .claude/scripts/email_sender.py \
  "[OmniCommand] /_presentation {NAME} — {MODUS}" \
  --body-from-file "{OUTPUT_DATEI_PFAD}"
```

| Modus | Subject |
|-------|---------|
| PR | `[OmniCommand] PR {TICKET} — Technische Dokumentation` |
| BRAINSTORM | `[OmniCommand] Brainstorm {THEMA} — Optionen` |
| ZWISCHENERGEBNIS | `[OmniCommand] Status {NAME}` |

**Fehlerbehandlung:** Falls Email fehlschlaegt (GMAIL_ADDRESS/GMAIL_APP_PASSWORD nicht gesetzt):
→ WARNUNG ausgeben, NICHT abbrechen. Datei ist trotzdem geschrieben.

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Email versendet oder WARNING):

```bash
powershell -Command "notify '{FEATURE} /_presentation abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
