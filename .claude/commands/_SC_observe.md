---
type: building-block
depends_on:
  - _model
  - _gap
feeds_into:
  - _SC_modelMaintain
related:
  - _SC_qualityGate
---

# /_SC_observe

**Status:** NEU v2.2 (ersetzt _analyse Sektion A)
**Actor:** OBSERVER
**Zweck:** Findings sammeln ohne Interpretation

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_SC_observe {NAME} [easy|normal|hard]                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. _manifest.md                                                       ║
║    2. {VAULT}/.../Model/{NAME}_Model.md (MUSS EXISTIEREN)              ║
║       FALLBACK: .claude/models/{NAME}_Model.md                          ║
║    3. synthese/{NAME}-GAP.md (falls vorhanden, Delta IST↔SOLL)         ║
║       ◄── NEU v3.0: Bekannte Gaps fuer gerichtete Observation          ║
║    4. synthese/{NAME}-ERGEBNIS{CYCLE}.md (falls Folge-Zyklus)          ║
║    5. Codebase (direkt via Glob/Grep/Read)                              ║
║    6. .claude/crumbs/{NAME}_crumbs.md (Crumbs aus A-Phase, falls vorh.) ║
║                                                                          ║
║  SCHREIBT (Output) - abhaengig von Worker-Rolle:                         ║
║    Observer-Drafter D{NN}:                                                ║
║      drafts/{NAME}-observe{CYCLE}-D{NN}-{fokus}.md                      ║
║    Observer-Synthesist (BL-050 Vault-First):                              ║
║      PRIMAER: {VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-OBSERVE{CYCLE}.md ║
║      FALLBACK: {WORKING_DIR}/.claude/analysis/synthese/{NAME}-OBSERVE{CYCLE}.md       ║
║      → Sektion A: Findings (NUR aktueller Zyklus)                       ║
║                                                                          ║
║  SCHREIBT (Output) - OPTIONAL:                                           ║
║    _parking-lot.md (APPEND, falls Incidental Findings)                  ║
║      → Neue Tasks die NICHT zum aktuellen Zyklus gehoeren              ║
║                                                                          ║
║  ACTOR: OBSERVER                                                         ║
║    Beobachtet den aktuellen Zyklus, sammelt Findings.                   ║
║    KEINE Interpretation, KEINE Model-Updates.                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **OBSERVER** Actor hat eine einzige Verantwortung:

**Findings sammeln für den aktuellen Zyklus**

Was der Observer **TUT**:
- ✅ Codebase scannen nach relevanten Mustern
- ✅ ERGEBNIS{N-1} auswerten (SRS-Score, Widerlegungen)
- ✅ Findings dokumentieren (F1, F2, F3, ...)
- ✅ Incidental Tasks in Parking Lot ablegen
- ✅ git-Status prüfen vor W{n}-Formulierung (G-UNTRACKED Guard, W92)

Was der Observer **NICHT TUT**:
- ❌ Model updaten (→ _SC_modelMaintain)
- ❌ Quality Gates prüfen (→ _SC_qualityGate)
- ❌ Interpretieren oder bewerten
- ❌ Hypothesen aufstellen
- ❌ Code ändern

---

## Chain-Position

```
MODEL → ERGEBNIS{N-1} → **OBSERVE{N}** → QUALITYGATE{N} → HYPOTHESEN
```

**Prev:** ERGEBNIS{N-1} (oder MODEL bei N=1)
**Next:** QUALITYGATE{N}

---

## Worker-Vertrag: Observer-Drafter (Findings sammeln)

### Voraussetzung

{NAME}_Model.md existiert und wurde gelesen.

### G-UNTRACKED: Quellen-Verifikation (PFLICHT vor jeder W{n}-Formulierung)

**Regel (W92):** Bevor eine W{n} formuliert wird, die ein Code-Artefakt referenziert, pruefe den git-Status dieses Artefakts.

- Untracked files (`??` in `git status`) sind I-Pipeline-Prototypen, temporaere Artefakte oder Arbeits-Entwuerfe — sie sind **KEINE Architektur-Wahrheit**.
- Eine W{n} die auf einem untracked Artefakt basiert erhaelt den Caveat-Marker: **`[QUELLE-UNVERIFIZIERT]`**
- W{n} mit `[QUELLE-UNVERIFIZIERT]` duerfen **NICHT als alleinige Basis fuer ADR-Entscheidungen** dienen.
- Staged aber nicht committete Artefakte (`M`, `A` in `git status`) erhalten ebenfalls `[QUELLE-UNVERIFIZIERT]` wenn sie semantisch noch in Bearbeitung sind.

**Hintergrund:** DCSRE-93 W39 basierte auf einem untracked `MockPflegeeinrichtungProvider.cs` (I-Worker-Artefakt). Ergebnis: ADR v1 komplett invalidiert, 2 Zyklen Overhead. Der git-Status-Check kostet Sekunden; die Folgekosten eines falschen ADRs kosten Stunden.

### Drafter-Auftrag (fuer jeden Drafter-Slot)

Im Wellen-Worker-Modus: Du bist der zugewiesene Drafter (Agent-ID aus Task-Beschreibung).
Im Solo-Modus: Fuehre mehrere Drafter-Durchlaufe sequentiell aus (D01, D02, D03...).

Jeder Drafter erhaelt:

```
Du bist Drafter D{NN} fuer die Observation von "{NAME}" (Cycle {N}).

INPUT - LIES ZUERST DIESE DATEIEN:
  1. .claude/models/{NAME}_Model.md
  2. {WORKING_DIR}/.claude/analysis/synthese/{NAME}-ERGEBNIS{CYCLE}.md (falls vorhanden)
  3. {WORKING_DIR}/.claude/analysis/synthese/{NAME}-GAP.md (falls vorhanden)

AUFTRAG: {Fokus-Beschreibung}

SCHREIB-PFLICHT:
Du MUSST deine Findings in folgende Datei schreiben:
  .claude/analysis/drafts/{NAME}-observe{CYCLE}-D{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  name: {NAME}
  phase: observe{CYCLE}
  wave: drafts
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  agent: D{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  reads: models/{NAME}_Model.md
  status: final
  ---

  # Observe D{NN}: {Fokus-Titel}

  ## Model-Kontext
  {Relevante Sektionen aus {NAME}_Model.md}

  ## Findings

  ### F1: {Finding-Titel}
  - **Datei:** {Pfad}:{Zeile}
  - **Model-Bezug:** W{n} oder "Neu"
  - **Beschreibung:** ...

  ## Zusammenfassung
  {5-10 Saetze}

WICHTIG:
- IMMER Model als Kontext nutzen
- Falls ERGEBNIS-Dateien vorhanden: SRS-Score + Marker als Kontext nutzen
- Falls GAP vorhanden: Bekannte Gaps als Fokus-Richtung nutzen
- Findings mit Datei:Zeile belegen
- Model-Bezug angeben: bestaetigt W{n}, widerspricht W{n}, oder NEU
- KEINE Hypothesen! Nur beobachten und dokumentieren
- **G-UNTRACKED (PFLICHT, W92):** Bevor du eine W{n} formulierst die Code-Artefakte referenziert:
  Pruefe ob der Artefakt git-tracked ist (nicht `??` in `git status`).
  Untracked files sind I-Pipeline-Prototypen — KEINE Architektur-Wahrheit.
  W{n} aus untracked Source erhaelt Caveat `[QUELLE-UNVERIFIZIERT]` und darf NICHT als ADR-Basis dienen.
- Die Datei MUSS geschrieben werden
```

### Drafter-Fokus-Bereiche

| Agent | Fokus | Aufgabe |
|-------|-------|---------|
| D01 | code-analyse | Relevante Code-Pfade, Methoden-Aufrufe, Abhaengigkeiten |
| D02 | infrastruktur | Config-Dateien, Environment, Container, Netzwerk |
| D03 | patterns | Cross-Cutting Concerns, Architektur-Patterns, Anomalien |
| D04-D05 | (bei hard) | Externe Abhaengigkeiten, Gegen-Hypothesen |

---

## Worker-Vertrag: Observer-Synthese

**Rolle:** Synthesist (1 Worker)
**Wann:** Team Lead spawnt dich nach Abschluss aller Observer-Drafter.

### Voraussetzung

Lies ALLE Dateien in `.claude/analysis/drafts/{NAME}-observe{CYCLE}-D*.md`

### Dein Auftrag

1. Lies alle Draft-Reports
2. Konsolidiere Findings (Duplikate entfernen, F-Nummern vereinheitlichen)
3. Kategorisiere nach Technologie-Concern
4. Schreibe `{WORKING_DIR}/.claude/analysis/synthese/{NAME}-OBSERVE{CYCLE}.md`
5. Aktualisiere Manifest
6. Im Worker-Modus: TaskUpdate completed + SendMessage an Team Lead

**KEINE Interpretation, KEINE Model-Updates, KEINE Hypothesen!**

---

## Parking Lot Integration

Falls während der Observation **Incidental Findings** auftauchen (Tasks, die NICHT zum aktuellen Zyklus gehören):

**Beispiel:**
Während Observation von "User-Login Feature" fällt auf: "S3 → MinIO Migration nötig"

→ Schreibe in `_parking-lot.md`:

```markdown
## 2026-02-03 - Von /_SC_observe (Cycle 4)

- [ ] **S3 → MinIO Migration**
  - **Beschreibung:** Aktuelle S3-Integration auf lokalen MinIO umstellen
  - **Grund:** Während User-Login Observation entdeckt
  - **Priorität:** MITTEL
  - **TC-Nähe:** Storage/Infrastructure
  - **Quelle:** Finding F3 in OBSERVE4
```

Der Parking Lot wird von **_taskDefinition** bei Cycle-Ende verarbeitet.

---

## Output-Format: OBSERVE{CYCLE}.md

```markdown
# Observe: {NAME} (Cycle {N})

## Sektion A: Findings

### F1: {Titel des Findings}

**Kategorie:** {Technologie-Concern}
**Quelle:** {Datei/Klasse/Methode}
**Beschreibung:**
{1-3 Sätze}

**Details:**
{Code-Snippets, Stack Traces, Logs}

**Impact:**
{Welche W{n} betroffen? Welche Bereiche?}

---

### F2: {Titel des Findings}
...

---

## Sektion B: Incidental Findings (→ Parking Lot)

Falls vorhanden, Liste der Tasks die in `_parking-lot.md` geschrieben wurden:

- S3 → MinIO Migration (Parking Lot Entry #7)
- ...
```

---

## Kompakt-Sicherheit

Nach jeder Welle kann `/compact` ausgeführt werden:
- Nach Welle 1 (Drafts): State in `_manifest.md`
- Nach Welle 2 (OBSERVE.md): Command abgeschlossen

---

## Obsidian-Tags

```yaml
tags:
  - type/observe
  - op/{FEATURE}
  - topic/{Technologie-Concern}
cycle: {N}
chain-position: observe
prev: [[{NAME}-ERGEBNIS{N-1}]]
next: [[{NAME}-QUALITYGATE{N}]]
```

---

## Siehe auch

- [[SC_modelMaintain]] - Nächster Schritt in der Kette
- [[SC_qualityGate]] - Quality Gates nach Model-Update
- [[_parking-lot]] - Incidental Findings Queue
- [[_analyse]] - LEGACY Command (<v2.2)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_SC_observe abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
