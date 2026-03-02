# /_I_codePartialSystem

**Status:** V3.0 (Implementierungs-Pipeline - Stufe 3: Partial System)
**Actor:** PARTIAL-SYSTEM-CODER
**Zweck:** Partial System Tests + Boundary Code via Red-Green-Refactor (bedingte Container)

**Umbenannt von:** `/_I_codeIntegration` (V3.0)

---

## Vertrag

```
+===============================================================================+
|  COMMAND: /_I_codePartialSystem {SLICE_NAME}                                  |
+===============================================================================+
|  LIEST (Input) - PFLICHT:                                                     |
|    1. .claude/analysis/_manifest.md                                           |
|    2. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md                           |
|       -> Partial System Test-Liste (IT1, IT2, ...)                            |
|       -> Boundary Crossings (DB Zugriff, S3 etc.)                             |
|       -> Architektur-Entscheidungen (DIP, Interfaces)                         |
|    3. .claude/analysis/synthese/{NAME}-COMPONENT-{SLICE}.md                   |
|       ODER .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md                 |
|       -> Abgeschlossene vorherige Tests (Voraussetzung)                       |
|       -> Refactoring-Entscheidungen (Interface-Design)                        |
|    4. .claude/meta/DCSRE-BE-TestStufenArchitektur.md                          |
|       -> Stufe 3 Definition: Bedingte Container, Rest gemockt                 |
|    5. .claude/wissen/ContainerIntegrationTestBase/                            |
|       ContainerIntegrationTestBase_Wissen.md                                  |
|       -> Constructor, Port-Schema, Reset-Methoden                             |
|    6. Codebase (Production Code + bestehende IntTests)                        |
|    7. MCP Clean Code (Uncle Bob Boundary Guidance)                            |
|                                                                               |
|  SCHREIBT (Output) - PFLICHT:                                                 |
|    1. Code: Partial System Tests (*IntegrationTests.cs)                       |
|    2. Code: Boundary Code (Wiring, DI Config, DB Migrations)                  |
|    3. .claude/analysis/synthese/{NAME}-PARTIALSYSTEM-{SLICE}.md               |
|       -> Abgeschlossene Test-Liste (alle Tests mit Status)                    |
|       -> RGR-Zyklen Protokoll                                                 |
|       -> Boundary-Entscheidungen dokumentiert                                 |
|    4. .claude/analysis/_manifest.md (nach JEDEM gruenen Test update)          |
|                                                                               |
|  MCP-BREMSE:                                                                  |
|    IMMER MIN-Modus -> max 1 Query, limit=1                                    |
|    Ausfuehrende Phase: NUR bei echter Unsicherheit fragen                     |
|                                                                               |
|  RED-GREEN-REFACTOR LOOP:                                                     |
|    Fuer JEDEN Partial System Test aus PLAN.md:                                |
|      RED:      Test schreiben (MUSS fehlschlagen)                             |
|      GREEN:    Boundary Code verdrahten (MUSS Test bestehen)                  |
|      REFACTOR: Wiring bereinigen (DI, Config, Abstraktion)                    |
|      CHECKPOINT: Manifest aktualisieren                                       |
|                                                                               |
|  VORAUSSETZUNG:                                                               |
|    /_I_codeComponent {SLICE} ODER /_I_codeAtomic {SLICE}                      |
|    MUSS abgeschlossen sein                                                    |
|    -> Alle vorherigen Tests gruen                                             |
|                                                                               |
|  PIPELINE-POSITION:                                                           |
|    [/_I_codeComponent] -> [/_I_codePartialSystem] -> [/_I_codeSingleSlice]    |
|                                                                               |
|  ACTOR: PARTIAL-SYSTEM-CODER                                                  |
|    Schreibt Partial System Tests via TDD.                                     |
|    Testet Boundary Crossings mit BEDINGTEN Containern.                        |
|    NUR die Container die benoetigt werden (z.B. NUR DB).                      |
|    Machist-Stil an DIP-Grenzen, Statist wo moeglich.                         |
+===============================================================================+
```

---

## WICHTIG: Bedingte Container

Stufe 3 nutzt **bedingte Container** - NUR was der Test tatsaechlich braucht:

| Test-Typ | Container | Constructor |
|-----------|-----------|-------------|
| Provider -> DB | Nur SQL Server | `base(true, false)` |
| Service -> S3 | Nur MinIO | `base(false, false, false, true)` |
| Service -> DIC | Nur DIC Mock | `base(false, false, true)` |

**KEIN "alle Container starten"!** Das waere Stufe 4+.

---

## Verantwortlichkeit

Der **PARTIAL-SYSTEM-CODER** Actor hat eine einzige Verantwortung:

**Partial System Tests + Boundary Code via Red-Green-Refactor schreiben**

Was der Partial-System-Coder **TUT**:
- Partial System Tests schreiben (Boundary Crossings mit echten Containern)
- Boundary Code verdrahten (DI Container, DB Config)
- Mock-Strategien anwenden (Machist an DIP-Grenzen fuer nicht-gestartete Container)
- Test-Isolation durch bedingte Container
- Red-Green-Refactor Zyklus fuer Partial System Tests
- Manifest nach jedem gruenen Test aktualisieren

Was der Partial-System-Coder **NICHT TUT**:
- Unit Tests schreiben (-> /_I_codeAtomic, abgeschlossen)
- Component Tests schreiben (-> /_I_codeComponent, abgeschlossen)
- Single Slice Tests schreiben (-> /_I_codeSingleSlice)
- Production Business Logic aendern (nur Wiring + Boundary Code)

---

## Pipeline-Position

```
CODECOMPONENT -> **CODEPARTIALSYSTEM** -> CODESINGLESLICE
                       |
                       v
                 Partial System Tests + Boundary Code
                 PARTIALSYSTEM-{SLICE}.md
```

**Prev:** /_I_codeComponent (Component Tests)
**Next:** /_I_codeSingleSlice (Single Slice Tests)

**Eskalation:** Bei Stagnation (5+ RGR ohne Fortschritt) -> /_SC_observe

---

## Technische Details (ContainerIntegrationTestBase)

### Constructor

```csharp
protected ContainerIntegrationTestBase(
    bool buildDatabaseContainer,
    bool buildSmtpContainer,
    bool buildDicMockServerContainer = false,
    bool buildMinioContainer = false)
```

### Reset-Methoden

| Methode | Container |
|---------|-----------|
| `ResetDatabaseOnlyAsync(port)` | Nur SQL Server |
| `ResetMinioOnlyAsync(apiPort, consolePort)` | Nur MinIO |
| `ResetDicMockServerOnlyAsync(soap, crud, sftp, health)` | Nur DIC Mock |
| `ResetDatabaseAsync(db, smtp, ...)` | DB + SMTP + optional DIC |

### Verfuegbare Properties nach Reset

- `DbContextFactory` - IDbContextFactory<DcspDbContext>
- `Mapper` - IMapper (AutoMapper)
- `MigrationsSettings` - MigrationsSettings

---

## Schritt 1: Boundary-Analyse

Aus PLAN.md die Boundaries klassifizieren:

| Boundary-Typ | Container benoetigt | Constructor-Parameter |
|--------------|--------------------|-----------------------|
| Provider -> DB | SQL Server | `base(true, false)` |
| Service -> S3 | MinIO | `base(false, false, false, true)` |
| Service -> DIC | DIC Mock Server | `base(false, false, true)` |
| Service -> SMTP | SMTP4Dev | `base(false, true)` |

---

## Schritt 2: RGR-Loop (Partial System Tests)

Identisch zum bisherigen Integration-Test-RGR-Loop:
- RED: Test mit Container-Setup schreiben
- GREEN: Boundary Code verdrahten
- REFACTOR: Wiring bereinigen

---

## Output-Format: PARTIALSYSTEM-{SLICE}.md

**Pfad:** `.claude/analysis/synthese/{NAME}-PARTIALSYSTEM-{SLICE}.md`

---

## Qualitaetskriterien

- **Drei Gesetze TDD:** Strikt eingehalten
- **RED:** Jeder IT MUSS fehlschlagen bevor GREEN
- **GREEN:** NUR Wiring-Code (keine neue Business Logic!)
- **Bedingte Container:** NUR die Container die benoetigt werden
- **SQL Server 2022:** KEIN InMemory DB fuer Stufe 3!
- **Port-Schema:** Keine Port-Konflikte mit anderen Tests

---

## Kompakt-Sicherheit

Nach JEDEM gruenen Test:
- State: Manifest mit IT-Fortschritt aktualisiert
- Resume: Naechster IT aus PLAN.md + Manifest-Status

---

## Siehe auch

- [[I_codeComponent]] - Vorheriger Schritt (Component Tests)
- [[I_codeSingleSlice]] - Naechster Schritt (Single Slice Tests)
- [[I_cleanCodeSlice]] - PLAN.md mit Test-Liste
- [[SC_observe]] - Eskalation bei Stagnation
