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
║    2. models/{NAME}_Model.md (MUSS EXISTIEREN)                          ║
║    3. synthese/{NAME}-GAP.md (falls vorhanden, Delta IST↔SOLL)         ║
║       ◄── NEU v3.0: Bekannte Gaps fuer gerichtete Observation          ║
║    4. synthese/{NAME}-ERGEBNIS{CYCLE}.md (falls Folge-Zyklus)          ║
║    5. Codebase (direkt via Glob/Grep/Read)                              ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    Welle 1: drafts/{NAME}-observe{CYCLE}-D01-{f}.md                     ║
║    Welle 2: synthese/{NAME}-OBSERVE{CYCLE}.md                            ║
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
