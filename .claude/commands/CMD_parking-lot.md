# CMD: _parking-lot.md

**Status:** NEU v2.2 (Shared Infrastructure)
**Typ:** APPEND-ONLY Queue
**Zweck:** Incidental Findings sammeln

---

## Konzept

Der **Parking Lot** ist eine **globale Queue** für **Incidental Findings** - Tasks, die während der Arbeit entdeckt werden, aber NICHT zum aktuellen Zyklus gehören.

### Problem (vor v2.2)

**Beispiel:**
```
User arbeitet an: "User-Login Feature (Cycle 4)"

Während /_SC_observe fällt auf:
  "S3-Integration sollte auf MinIO migriert werden"

Frage: Wohin mit diesem Task?
  ❌ In aktuellen Cycle? → Nein, gehört nicht zu User-Login
  ❌ Vergessen? → Nein, Task geht verloren
  ❌ In neuem Cycle? → Nein, _taskDefinition würde falsche Priorität setzen
```

### Lösung (v2.2)

**Parking Lot Pattern (Uncle Bob):**

> "Separate concerns from current work. Maintain a shared, visible parking lot where any team member can drop incidental findings. Process at natural boundaries (end of cycle, planning sessions)."

```
Während Arbeit:
  Task entdeckt → _parking-lot.md (APPEND)

Bei Cycle-Ende:
  _taskDefinition LIEST _parking-lot.md
  → Verarbeitet Tasks mit Proximity-Priorisierung
  → Markiert als [x] (verarbeitet) oder [~] (verworfen)
```

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  FILE: _parking-lot.md                                                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  SCHREIBT (APPEND-ONLY):                                                  ║
║    - ALLE Commands können schreiben:                                      ║
║      /_SC_observe, /_SC_modelMaintain, /_SC_qualityGate,                          ║
║      /_SC_hypothese, /_SC_implement, /_SC_ergebnis,                                ║
║      /_knowledge, /_blindspotDetection, etc.                              ║
║                                                                          ║
║  LIEST (READ-ONLY):                                                       ║
║    - /_taskDefinition (bei Cycle-Ende)                                   ║
║      → Verarbeitet [  ] offene Tasks                                     ║
║      → Markiert [x] (aufgenommen) oder [~] (verworfen)                   ║
║                                                                          ║
║  REGELN:                                                                  ║
║    1. APPEND-ONLY: Commands fügen hinzu, NIEMALS löschen                 ║
║    2. Checkboxes: [ ] offen, [x] verarbeitet, [~] verworfen             ║
║    3. Timestamp + Quelle PFLICHT                                          ║
║    4. TC-Nähe angeben (für Proximity-Priorisierung)                      ║
║    5. Format einhalten (siehe unten)                                      ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Format-Template

```markdown
# Parking Lot: Incidental Findings

**Letzte Aktualisierung:** {YYYY-MM-DD HH:MM}

## Legende
- [ ] Offen
- [x] In _taskDefinition aufgenommen (Cycle {N})
- [~] Verworfen (Grund: ...)

---

## {YYYY-MM-DD} - Von /{COMMAND} (Cycle {N})

- [ ] **{Task-Titel}**
  - **Beschreibung:** {1-2 Sätze}
  - **Grund:** {Warum aufgefallen?}
  - **Priorität:** HOCH / MITTEL / NIEDRIG
  - **TC-Nähe:** {Technologie-Concern oder "NONE"}
  - **Quelle:** {Finding F{N} / Model W{n} / Gate Check / ...}

- [ ] **{Weiterer Task}**
  - ...

---

## {YYYY-MM-DD} - Von /{ANDERES_COMMAND} (Cycle {M})

- [x] **{Verarbeiteter Task}**
  - **Beschreibung:** ...
  - **Status:** Aufgenommen in Cycle {M+1} (Task: {NAME})
  - **Grund:** ...

- [~] **{Verworfener Task}**
  - **Beschreibung:** ...
  - **Status:** Verworfen (Grund: Außerhalb Scope, geringe Priorität)
  - **Grund:** ...
```

---

## Beispiel: Real-World Usage

### Während /_SC_observe (Cycle 4)

**Aktueller Task:** User-Login Feature

**Incidental Finding:**
"Bei Observation von AuthController fällt auf: S3BucketService verwendet veraltete AWS SDK v2, Migration zu v3 empfohlen"

**Action:**
```bash
# Während /_SC_observe läuft:
APPEND zu _parking-lot.md:
```

```markdown
## 2026-02-03 14:35 - Von /_SC_observe (Cycle 4)

- [ ] **AWS SDK v2 → v3 Migration**
  - **Beschreibung:** S3BucketService nutzt veraltete SDK v2, v3 bringt Performance-Verbesserungen
  - **Grund:** Entdeckt während AuthController Observation (Finding F3)
  - **Priorität:** MITTEL
  - **TC-Nähe:** Storage (nicht aktueller Fokus: Authentication)
  - **Quelle:** Finding F3 in OBSERVE4.md, Datei: S3BucketService.cs:15
```

### Während /_SC_qualityGate (Cycle 4)

**Incidental Finding:**
"Gate 2 (Kohäsion) zeigt: Logging-TC hat nur 4 W{n}, evtl. Structured Logging einführen?"

**Action:**
```markdown
## 2026-02-03 15:10 - Von /_SC_qualityGate (Cycle 4)

- [ ] **Structured Logging evaluieren**
  - **Beschreibung:** Logging-TC hat aktuell nur 4 W{n}, Structured Logging (Serilog?) könnte Observability verbessern
  - **Grund:** Quality-Gate Kohäsions-Check ergab geringe W{n}-Dichte
  - **Priorität:** NIEDRIG
  - **TC-Nähe:** Logging
  - **Quelle:** Gate 2 (Kohäsions-Check) in QUALITYGATE4.md
```

### Bei Cycle-Ende: /_taskDefinition (Cycle 5)

**_taskDefinition liest _parking-lot.md:**

```markdown
## Parking Lot Processing (Cycle 5)

**Offene Tasks:** 2

### Task 1: AWS SDK v2 → v3 Migration
- **TC-Nähe:** Storage
- **Aktueller Fokus:** Authentication
- **Proximity-Score:** 0.3 (niedriger, da anderer TC)
- **Entscheidung:** Warten (nicht im Fokus)

### Task 2: Structured Logging evaluieren
- **TC-Nähe:** Logging
- **Aktueller Fokus:** Authentication
- **Proximity-Score:** 0.1 (sehr niedrig)
- **Entscheidung:** Warten (niedrige Priorität)

**Feature-Status User-Login:** 90% Coverage
**Empfehlung:** 1 weiterer Cycle für User-Login, DANN Parking Lot erneut prüfen
```

**_parking-lot.md bleibt unverändert** (Tasks bleiben [ ] offen)

### Nach Feature-Abschluss: /_taskDefinition (Cycle 6)

**User-Login Feature:** ✅ ABGESCHLOSSEN (95% Coverage)

**_taskDefinition verarbeitet Parking Lot:**

```markdown
## 2026-02-05 09:00 - Verarbeitung durch /_taskDefinition (Cycle 6)

- [x] **AWS SDK v2 → v3 Migration**
  - **Beschreibung:** ...
  - **Status:** Aufgenommen als nächstes Feature (Task: S3-Modernisierung)
  - **Grund:** Feature-Abschluss User-Login, Storage-TC ist next
  - **Proximity-Score:** 0.8 (hoch, weil nächster TC)

- [~] **Structured Logging evaluieren**
  - **Beschreibung:** ...
  - **Status:** Verworfen (Grund: Logging funktioniert ausreichend, niedrige Priorität)
  - **Entscheidung:** Prof. Feedback: "Nice-to-have, aber nicht kritisch"
```

---

## Integration in Commands

### /_SC_observe

```python
# Pseudo-Code
if incidental_finding_detected():
    append_to_parking_lot(
        title="AWS SDK v2 → v3 Migration",
        description="...",
        reason="Entdeckt während AuthController Observation",
        priority="MITTEL",
        tc_proximity="Storage",
        source="Finding F3 in OBSERVE4.md"
    )
```

### /_SC_modelMaintain

```python
if w_n_implies_external_task():
    append_to_parking_lot(
        title="Entity-Framework 6.x → 8.x Upgrade",
        description="W42 lässt vermuten, dass EF-Upgrade nötig",
        reason="Model-Maintenance ergab Abhängigkeit",
        priority="HOCH",
        tc_proximity="Data-Access",
        source="W42 Implikation"
    )
```

### /_SC_qualityGate

```python
if gate_reveals_improvement():
    append_to_parking_lot(
        title="Structured Logging evaluieren",
        description="Logging-TC hat nur 4 W{n}",
        reason="Quality-Gate Kohäsions-Check",
        priority="NIEDRIG",
        tc_proximity="Logging",
        source="Gate 2 (Kohäsions-Check)"
    )
```

### /_taskDefinition

```python
# Bei Cycle-Ende:
open_tasks = read_parking_lot()
for task in open_tasks:
    proximity_score = calculate_proximity(task.tc, current_focus_tc)
    if proximity_score > 0.7:
        mark_as_processed(task, reason="Aufgenommen in nächsten Cycle")
        create_new_task(task)
    else:
        # Warten auf besseren Zeitpunkt
        pass
```

---

## Proximity-Priorisierung

Tasks im Parking Lot werden nach **TC-Nähe** priorisiert:

```python
def calculate_proximity(task_tc, current_focus_tc):
    if task_tc == current_focus_tc:
        return 1.0  # Gleicher TC = höchste Priorität
    elif task_tc in get_cross_cutting_tcs():
        return 0.7  # Cross-Cutting (z.B. Logging) = hohe Priorität
    elif task_tc in get_active_tcs():
        return 0.5  # Aktiver TC (nicht Fokus) = mittlere Priorität
    elif task_tc == get_next_tc():
        return 0.8  # Nächster geplanter TC = hohe Priorität
    else:
        return 0.2  # Weit entfernt = niedrige Priorität
```

---

## Vorteile

1. **Task Continuity:** Keine verlorenen Tasks
2. **Fokus:** Aktueller Cycle wird nicht unterbrochen
3. **Visibility:** Alle sehen, was "geparkt" wurde
4. **Proximity-Based:** Intelligente Priorisierung
5. **Simple:** APPEND-ONLY, keine komplexen Regeln

---

## Anti-Patterns

### ❌ Task sofort starten

```
# FALSCH:
if incidental_task_detected():
    start_new_cycle(task)  # Unterbricht aktuellen Cycle!
```

### ❌ Task vergessen

```
# FALSCH:
if incidental_task_detected():
    pass  # Task geht verloren!
```

### ❌ Parking Lot ignorieren

```
# FALSCH bei _taskDefinition:
# Parking Lot wird nicht gelesen
→ Tasks bleiben ewig [ ] offen
```

### ✅ Richtig: Parking Lot Pattern

```
# RICHTIG:
if incidental_task_detected():
    append_to_parking_lot(task)  # Parken
    continue_current_cycle()     # Weitermachen

# Bei Cycle-Ende:
process_parking_lot_with_proximity()
```

---

## Obsidian-Tags

```yaml
tags:
  - type/parking-lot
  - topic/Task-Management
  - topic/Workflow
```

---

## Siehe auch

- [[_taskDefinition]] - Verarbeitet Parking Lot bei Cycle-Ende
- [[SC_observe]] - Schreibt Incidental Findings
- [[SC_modelMaintain]] - Schreibt Incidental Findings
- [[SC_qualityGate]] - Schreibt Incidental Findings
- [[Uncle Bob: Parking Lot Pattern]] - Theoretische Basis
