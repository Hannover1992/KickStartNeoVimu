# /_SC_modelMaintain

**Status:** NEU v2.2 (ersetzt _analyse Sektion B)
**Actor:** MODEL-MAINTAINER
**Zweck:** Model pflegen, GC, Split ausführen

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_SC_modelMaintain {NAME} [easy|normal|hard]                   ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. _manifest.md                                                       ║
║    2. models/{NAME}_Model.md (MUSS EXISTIEREN)                          ║
║    3. synthese/{NAME}-OBSERVE{CYCLE}.md (Findings aus _SC_observe)      ║
║    4. synthese/{NAME}-ERGEBNIS{CYCLE}.md (Widerlegungs-Marker)         ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    Model-Update (IMMER):                                                 ║
║      models/{NAME}_Model.md (aktualisiert)                              ║
║      → Neue W{n} / korrigierte W{n} / Version erhoehen                 ║
║      → GC: WIDERLEGT/ELIMINIERT markieren                               ║
║      → Kap. 6a pflegen (Offene Bereiche, Aktive TCs)                   ║
║                                                                          ║
║    Model-Split (bei PFLICHT-Trigger):                                   ║
║      models/{NAME}_Model-Topologie.md                                   ║
║      models/{NAME}_{TC}_Model.md (pro Teilmodel)                        ║
║                                                                          ║
║  SCHREIBT (Output) - OPTIONAL:                                           ║
║    _parking-lot.md (APPEND, falls Incidental Findings)                  ║
║                                                                          ║
║  ACTOR: MODEL-MAINTAINER                                                 ║
║    Pflegt das Model: W{n} hinzufuegen/korrigieren/GC,                  ║
║    Model-Split ausfuehren, Kap. 6a aktualisieren.                      ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **MODEL-MAINTAINER** Actor hat eine einzige Verantwortung:

**Model-Pflege: W{n} verwalten, GC, Split**

Was der Model-Maintainer **TUT**:
- ✅ W{n} hinzufügen (aus OBSERVE Findings)
- ✅ W{n} korrigieren (aus ERGEBNIS Widerlegungen)
- ✅ GC: WIDERLEGT/ELIMINIERT markieren
- ✅ Kap. 6a aktualisieren (Offene Bereiche, Aktive TCs)
- ✅ Model-Split ausführen (bei >15 W{n}/TC oder >30 gesamt)
- ✅ Model-Topologie pflegen

Was der Model-Maintainer **NICHT TUT**:
- ❌ Findings sammeln (→ _SC_observe)
- ❌ Quality Gates prüfen (→ _SC_qualityGate)
- ❌ Hypothesen aufstellen (→ _hypothese)
- ❌ Code schreiben (→ _implement)

---

## Chain-Position

```
OBSERVE{N} → **MODEL-MAINTAIN** → QUALITYGATE{N} → HYPOTHESEN
                    |
                    ↓
              MODEL.md (updated)
```

**Prev:** OBSERVE{N}
**Next:** QUALITYGATE{N}

**Side-Effect:** Model.md wird IMMER aktualisiert

---

## Model-Update Workflow

### 1. W{n} hinzufügen

Für jedes Finding in OBSERVE{CYCLE}.md:

```markdown
## Kap. 3: Wahrheiten (W{n})

### W42: {Titel aus Finding F{X}}
**Zyklus:** {N}
**Status:** AKTIV
**Kategorie:** {Technologie-Concern}
**Quelle:** Finding F{X} in OBSERVE{CYCLE}

{Beschreibung: 2-3 Sätze}

**Details:**
{Code-Referenzen, Kontext}

**Widerlegbar durch:**
{Wie könnte diese Wahrheit widerlegt werden?}
```

### 2. Garbage Collection (GC)

Für jede Widerlegung in ERGEBNIS{CYCLE}.md:

```markdown
### W23: {Titel} ~~WIDERLEGT~~
**Zyklus Original:** 2
**Zyklus Widerl.:** 4
**Status:** ~~AKTIV~~ → **WIDERLEGT**
**Grund:** {Beschreibung aus ERGEBNIS}

{Ursprüngliche Beschreibung}
```

Für strategische Elimination (Manual Override):

```markdown
### W18: {Titel} ~~ELIMINIERT~~
**Zyklus Original:** 1
**Zyklus Elim.:** 3
**Status:** ~~AKTIV~~ → **ELIMINIERT**
**Grund:** Battle-Royale Scope-Reduktion (Focus auf TC=Authentication)
```

### 3. Kap. 6a aktualisieren

```markdown
## Kap. 6a: Offene Bereiche & Aktive Technologie-Concerns

### Offene Bereiche
1. {Bereich 1} - {Status}
2. {Bereich 2} - {Status}
...

### Aktive Technologie-Concerns (TC)
| TC | W{n} Anzahl | Status | Priorität |
|----|-------------|--------|-----------|
| Authentication | 8 | FOKUS | HOCH |
| Storage | 3 | OFFEN | MITTEL |
| Logging | 2 | OFFEN | NIEDRIG |

**Fokus-TC:** Authentication (aktueller Zyklus)
**Nächster TC:** Storage (nach Authentication abgeschlossen)
```

---

## Model-Split Trigger

### PFLICHT-Split wenn:
1. **>15 W{n} pro TC** (Kohäsions-Schwelle)
2. **>30 W{n} gesamt** (Komplexitäts-Schwelle)
3. **R-AP4** (Anti-Pattern: Explodierendes Model)

### Split-Ausführung

#### 1. Model-Topologie erstellen

```markdown
# Model-Topologie: {NAME}

**Split-Datum:** {YYYY-MM-DD}
**Zyklus:** {N}
**Grund:** {>15 W{n}/TC in Authentication}

## Teilmodelle

| TC | Pfad | Status | W{n} | Fokus |
|----|------|--------|------|-------|
| Authentication | models/{NAME}_Authentication_Model.md | AKTIV | 18 | ✓ FOKUS |
| Storage | models/{NAME}_Storage_Model.md | OFFEN | 8 | - |
| Logging | models/{NAME}_Logging_Model.md | OFFEN | 4 | - |

**Regeln:**
- VM-1: Nur 1 FOKUS-Teilmodel gleichzeitig
- VM-2: Cross-Cutting-Schutz: Min. 1 Drafter liest ALLE Teilmodelle
- VM-3: Fokus-Wechsel nur nach Feature-Abschluss
```

#### 2. Teilmodelle erstellen

```markdown
# Model: {NAME} - {TC}

**Parent:** {NAME}_Model.md
**Technologie-Concern:** {TC}
**Status:** {FOKUS|OFFEN|ABGESCHLOSSEN}

## Kap. 3: Wahrheiten (W{n})

{Nur W{n} die zu diesem TC gehören}

## Kap. 6a: Offene Bereiche (TC-spezifisch)

{Offene Bereiche innerhalb dieses TC}
```

---

## Parking Lot Integration

Falls während Model-Maintenance Incidental Tasks auffallen:

**Beispiel:**
"W42 lässt vermuten, dass Entity-Framework Upgrade nötig ist (aktuell 6.x → 8.x)"

→ Schreibe in `_parking-lot.md`:

```markdown
## 2026-02-03 - Von /_SC_modelMaintain (Cycle 4)

- [ ] **Entity-Framework 6.x → 8.x Migration**
  - **Beschreibung:** Upgrade EF wegen Performance-Issues (W42)
  - **Grund:** Model-Maintenance ergab Abhängigkeit
  - **Priorität:** HOCH
  - **TC-Nähe:** Data-Access
  - **Quelle:** W42 Implikation
```

---

## Kompakt-Sicherheit

Command schreibt direkt Model.md:
- State: Model.md Version erhöht
- Resume: Nächster Command liest aktualisiertes Model

---

## Obsidian-Tags

**Hinweis:** _SC_modelMaintain erstellt KEIN eigenes Synthese-Dokument.
Es aktualisiert nur Model.md.

Model.md hat bereits Tags:
```yaml
tags:
  - type/model
  - op/{FEATURE}
  - topic/{Kern-Konzepte}
version: {N}
```

---

## Siehe auch

- [[SC_observe]] - Vorheriger Schritt (liefert Findings)
- [[SC_qualityGate]] - Nächster Schritt (prüft Model)
- [[Model-Topologie]] - Bei Model-Split
- [[_analyse]] - LEGACY Command (<v2.2)
