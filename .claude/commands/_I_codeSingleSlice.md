# /_I_codeSingleSlice

**Status:** V3.0 (Implementierungs-Pipeline - Stufe 4: Single Slice)
**Actor:** SINGLE-SLICE-TESTER
**Zweck:** Single Slice Full-Flow Tests (kompletter vertikaler Durchstich eines Features)

**Umbenannt von:** `/_I_codeSystem` (V3.0)

---

## Vertrag

```
+===============================================================================+
|  COMMAND: /_I_codeSingleSlice {SLICE_NAME}                                    |
+===============================================================================+
|  LIEST (Input) - PFLICHT:                                                     |
|    1. .claude/analysis/_manifest.md                                           |
|    2. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md                           |
|       -> Single Slice Test-Liste (ST1, ST2, ...)                              |
|       -> Full-Flow Szenarien                                                  |
|    3. .claude/analysis/synthese/{NAME}-PARTIALSYSTEM-{SLICE}.md               |
|       -> Abgeschlossene Partial System Tests (Voraussetzung)                  |
|       -> Boundary-Entscheidungen                                              |
|    4. .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md                      |
|       -> Abgeschlossene Unit Tests (Kontext)                                  |
|    5. .claude/meta/DCSRE-BE-TestStufenArchitektur.md                          |
|       -> Stufe 4 Definition: Kompletter Slice-Durchstich                      |
|    6. .claude/Task.md                                                         |
|       -> Akzeptanzkriterien (Slice Tests validieren diese!)                   |
|    7. Codebase (Production Code, Konfiguration)                               |
|    8. MCP Clean Code (Uncle Bob Guidance)                                     |
|                                                                               |
|  SCHREIBT (Output) - PFLICHT:                                                 |
|    1. Code: Single Slice Tests (*IntegrationTests*.cs)                        |
|    2. Code: System-Konfiguration (falls noetig)                               |
|    3. .claude/analysis/synthese/{NAME}-SINGLESLICE-{SLICE}.md                 |
|       -> Abgeschlossene Test-Liste (alle Tests mit Status)                    |
|       -> RGR-Zyklen Protokoll                                                 |
|       -> Akzeptanzkriterien-Mapping (Test -> AK)                              |
|       -> Slice-Abschluss-Erklaerung                                          |
|    4. .claude/analysis/_manifest.md (Slice als ABGESCHLOSSEN markieren)       |
|                                                                               |
|  MCP-BREMSE:                                                                  |
|    IMMER MIN-Modus -> max 1 Query, limit=1                                    |
|    Ausfuehrende Phase: NUR bei echter Unsicherheit fragen                     |
|                                                                               |
|  RED-GREEN-REFACTOR LOOP:                                                     |
|    Fuer JEDEN Single Slice Test aus PLAN.md:                                  |
|      RED:      Full-Flow Test schreiben (MUSS fehlschlagen)                   |
|      GREEN:    System konfigurieren (MUSS Test bestehen)                      |
|      REFACTOR: Test-Code bereinigen                                           |
|      CHECKPOINT: Manifest aktualisieren                                       |
|                                                                               |
|  VORAUSSETZUNG:                                                               |
|    /_I_codePartialSystem {SLICE} MUSS abgeschlossen sein                      |
|    -> Alle vorherigen Tests gruen                                             |
|    -> PARTIALSYSTEM-{SLICE}.md existiert                                      |
|                                                                               |
|  PIPELINE-POSITION:                                                           |
|    [/_I_codePartialSystem] -> [/_I_codeSingleSlice] -> [SLICE ABGESCHLOSSEN]  |
|                                                                               |
|  ACTOR: SINGLE-SLICE-TESTER                                                   |
|    Schreibt Single Slice Full-Flow Tests via TDD.                             |
|    Testet kompletten vertikalen Durchstich eines Features.                    |
|    Bedingte Container: NUR die Container die der Slice braucht.               |
|    Validiert Akzeptanzkriterien aus Task.md.                                  |
|    Erklaert den Slice als ABGESCHLOSSEN nach allen gruenen Tests.             |
+===============================================================================+
```

---

## WICHTIG: Bedingte Container (NICHT alle!)

Stufe 4 nutzt **bedingte Container** - NUR was der Slice tatsaechlich braucht:

| Slice-Typ | Container | Beispiel |
|-----------|-----------|---------|
| DB-Slice | SQL Server | S1_S2_DBSchema, S6_Locking |
| S3-Slice | SQL Server + MinIO | S4_S3Key |
| DIC-Slice | SQL Server + DIC Mock | S5_Retry |
| Full DicImport | SQL Server + MinIO + DIC Mock | Full-Flow |

**KEIN "alle Container starten"!** Stufe 5 (Full Slice nach Merge) macht das.

---

## Verantwortlichkeit

Der **SINGLE-SLICE-TESTER** Actor hat eine einzige Verantwortung:

**Single Slice Full-Flow Tests + Slice-Abschluss-Erklaerung**

Was der Single-Slice-Tester **TUT**:
- Full-Flow Tests schreiben (kompletter vertikaler Durchstich)
- Akzeptanzkriterien aus Task.md durch Tests validieren
- System-Konfiguration anpassen (falls noetig)
- Red-Green-Refactor Zyklus fuer Slice Tests
- Slice als ABGESCHLOSSEN erklaeren
- Manifest final aktualisieren (Slice-Status)

Was der Single-Slice-Tester **NICHT TUT**:
- Unit Tests schreiben (-> /_I_codeAtomic, abgeschlossen)
- Component Tests schreiben (-> /_I_codeComponent, abgeschlossen)
- Partial System Tests schreiben (-> /_I_codePartialSystem, abgeschlossen)
- Naechsten Slice planen (-> /_I_cleanCodeSlice)

---

## Pipeline-Position

```
CODEPARTIALSYSTEM -> **CODESINGLESLICE** -> [SLICE ABGESCHLOSSEN]
                          |
                          v
                    Full-Flow Tests + Config
                    SINGLESLICE-{SLICE}.md
                    -> Naechster Slice ODER Feature fertig
```

**Prev:** /_I_codePartialSystem (Partial System Tests)
**Next:** /_I_cleanCodeSlice {NAECHSTER_SLICE} ODER Feature abgeschlossen

**Eskalation:** Bei Stagnation -> /_SC_observe

---

## Uncle Bob ueber System Tests

> "Tests are the foundation of confidence. The higher-level tests give us
> confidence that the whole system works together. But we want fewer of
> these because they are slow and fragile."

**Bedeutung fuer diese Phase:**
- WENIGE, aber WERTVOLLE Full-Flow Tests
- Testen dass Gesamtsystem VERBUNDEN ist, nicht Business Logic
- Business Logic ist in Unit + Component Tests
- Langsam + Container-Start → bewusst minimieren
- Akzeptanzkriterien als Leitfaden

---

## Schritt 1: Akzeptanzkriterien-Mapping

Fuer jedes AK in Task.md pruefen:
- Hat es einen Full-Flow Test? → Gut
- Abgedeckt durch Unit/Integration Tests? → Dokumentieren

---

## Schritt 2: RGR-Loop (Single Slice Tests)

- RED: Full-Flow Test mit Container-Setup schreiben
- GREEN: System konfigurieren (nur Config, keine neue Business Logic)
- REFACTOR: Test bereinigen

---

## Slice-Abschluss

### Alle Test-Stufen gruen?

```
+=============================================+
|  SLICE-ABSCHLUSS CHECKLISTE                 |
+=============================================+
|                                              |
|  Stufe 1 Atomic:         {N}/{N} GRUEN      |
|  Stufe 2 Component:      {N}/{N} GRUEN      |
|  Stufe 3 Partial System: {N}/{N} GRUEN      |
|  Stufe 4 Single Slice:   {N}/{N} GRUEN      |
|                                              |
|  Akzeptanzkriterien:                         |
|    AK1: Durch ST1 validiert                  |
|    AK2: Durch IT2 + T5 abgedeckt            |
|                                              |
|  SLICE STATUS: ABGESCHLOSSEN                 |
+=============================================+
```

### Naechster Schritt bestimmen

Falls weitere Slices im ARCHITECT.md:
  -> /_I_cleanCodeSlice {NAECHSTER_SLICE}

Falls ALLE Slices abgeschlossen:
  -> Feature KOMPLETT

---

## Output-Format: SINGLESLICE-{SLICE}.md

**Pfad:** `.claude/analysis/synthese/{NAME}-SINGLESLICE-{SLICE}.md`

---

## Qualitaetskriterien

- **Drei Gesetze TDD:** Strikt eingehalten
- **RED:** Jeder ST MUSS fehlschlagen bevor GREEN
- **GREEN:** NUR Konfiguration (keine neue Business Logic!)
- **Bedingte Container:** NUR die Container die der Slice braucht
- **AK-Mapping:** Jedes Akzeptanzkriterium hat mindestens 1 Test
- **Wenige, wertvolle Tests:** Uncle Bob's Prinzip
- **Manifest aktuell:** Slice-Abschluss klar dokumentiert
- **Keine Regression:** Vorherige Test-Stufen duerfen NICHT brechen

---

## Kompakt-Sicherheit

Nach JEDEM gruenen Test:
- State: Manifest mit ST-Fortschritt aktualisiert
- Resume: Naechster ST aus PLAN.md + Manifest-Status

Nach SLICE-ABSCHLUSS:
- State: Slice als ABGESCHLOSSEN im Manifest
- Resume: Naechster Slice oder Feature-Abschluss

---

## Siehe auch

- [[I_codePartialSystem]] - Vorheriger Schritt (Partial System Tests)
- [[I_cleanCodeSlice]] - Naechster Slice planen (falls weitere Slices)
- [[I_cleanCodeArchitect]] - Slice-Uebersicht und Reihenfolge
- [[Task.md]] - Akzeptanzkriterien (Input fuer Single Slice Tests)
- [[SC_observe]] - Eskalation bei Stagnation
