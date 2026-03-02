# Datenfluss-Diagramm: v2.2 (SRP-Refactoring)

**Version:** 2.2
**Datum:** 2026-02-03
**Änderung:** _analyse → 3-Command-Chain (Observe, ModelMaintain, QualityGate)

---

## Übersicht: LEGACY vs v2.2

```mermaid
graph TD
    subgraph "LEGACY <v2.2"
        M_OLD[Model.md]
        E_OLD[ERGEBNIS N-1]
        A_OLD[/_analyse]
        ANALYSE_OLD[ANALYSE N]
        H_OLD[/_SC_hypothese]

        M_OLD --> A_OLD
        E_OLD --> A_OLD
        A_OLD -->|"Sektion A: Findings\n+\nSektion B: Model-Update"| ANALYSE_OLD
        A_OLD -->|updates| M_OLD
        ANALYSE_OLD --> H_OLD
    end

    subgraph "v2.2+ - SRP-Konform"
        M_NEW[Model.md]
        E_NEW[ERGEBNIS N-1]
        O_NEW[/_SC_observe]
        OBS_NEW[OBSERVE N]
        MM_NEW[/_SC_modelMaintain]
        QG_NEW[/_SC_qualityGate]
        QGATE_NEW[QUALITYGATE N]
        H_NEW[/_SC_hypothese]
        PL[_parking-lot.md]

        M_NEW --> O_NEW
        E_NEW --> O_NEW
        O_NEW -->|"Findings\n(keine Interpretation)"| OBS_NEW
        O_NEW -.->|optional| PL

        OBS_NEW --> MM_NEW
        M_NEW --> MM_NEW
        E_NEW --> MM_NEW
        MM_NEW -->|"W{n} +/−/GC\nSplit ausführen"| M_NEW
        MM_NEW -.->|optional| PL

        OBS_NEW --> QG_NEW
        M_NEW --> QG_NEW
        E_NEW --> QG_NEW
        QG_NEW -->|"Quality Gates\nBSD Trigger"| QGATE_NEW
        QG_NEW -.->|optional| PL

        QGATE_NEW --> H_NEW
    end

    style A_OLD fill:#2ECC71,stroke:#27AE60,color:#fff
    style O_NEW fill:#26C6DA,stroke:#0097A7,color:#fff
    style MM_NEW fill:#9C27B0,stroke:#7B1FA2,color:#fff
    style QG_NEW fill:#AB47BC,stroke:#8E24AA,color:#fff
    style PL fill:#FDD835,stroke:#F9A825,color:#000
```

---

## Detaillierter Datenfluss: v2.2 Chain

### Phase 1: Observation (/_SC_observe)

```mermaid
graph LR
    subgraph "Inputs"
        M1[Model.md<br/>v{N}]
        E1[ERGEBNIS N-1<br/>SRS-Score<br/>Widerlegungen]
        CB[Codebase<br/>Glob/Grep/Read]
    end

    subgraph "/_SC_observe"
        D1[Drafter 1-5<br/>Findings sammeln]
        S1[Synthese<br/>OBSERVE{N}.md]
    end

    subgraph "Outputs"
        OBS[OBSERVE N<br/>F1-Fn Findings]
        PL1[_parking-lot.md<br/>Incidental Tasks]
    end

    M1 --> D1
    E1 --> D1
    CB --> D1
    D1 -->|Drafts| S1
    S1 --> OBS
    S1 -.->|optional| PL1

    style M1 fill:#4682B4,color:#fff
    style E1 fill:#3F51B5,color:#fff
    style D1 fill:#26C6DA,color:#fff
    style S1 fill:#26C6DA,color:#fff
    style OBS fill:#26C6DA,color:#fff
    style PL1 fill:#FDD835,color:#000
```

**Actor:** OBSERVER
**Verantwortung:** Findings sammeln (KEINE Interpretation)

**Datenfluss:**
1. Liest Model.md → Weiß, was bereits bekannt ist (W{n})
2. Liest ERGEBNIS{N-1} → Kennt SRS-Score, Widerlegungen
3. Scannt Codebase → Sucht nach Mustern
4. Schreibt OBSERVE{N}.md → F1-Fn Findings
5. Optional: Schreibt _parking-lot.md → Incidental Tasks

---

### Phase 2: Model Maintenance (/_SC_modelMaintain)

```mermaid
graph LR
    subgraph "Inputs"
        M2[Model.md<br/>v{N}]
        OBS2[OBSERVE N<br/>F1-Fn Findings]
        E2[ERGEBNIS N-1<br/>Widerlegungen]
    end

    subgraph "/_SC_modelMaintain"
        GC[GC Engine<br/>WIDERLEGT<br/>ELIMINIERT]
        WN[W{n} Manager<br/>Add/Correct]
        SPLIT[Split Engine<br/>>15 W{n}/TC?]
        K6[Kap. 6a Update<br/>Offene Bereiche]
    end

    subgraph "Outputs"
        M3[Model.md<br/>v{N+1}]
        TOPO[Model-Topologie<br/>bei Split]
        TM[Teilmodelle<br/>TC-spezifisch]
        PL2[_parking-lot.md<br/>Incidental Tasks]
    end

    M2 --> GC
    OBS2 --> WN
    E2 --> GC

    GC --> M3
    WN --> M3
    SPLIT --> M3
    K6 --> M3

    SPLIT -.->|falls >15 W{n}/TC| TOPO
    SPLIT -.->|falls >15 W{n}/TC| TM
    WN -.->|optional| PL2

    style M2 fill:#4682B4,color:#fff
    style OBS2 fill:#26C6DA,color:#fff
    style E2 fill:#3F51B5,color:#fff
    style GC fill:#9C27B0,color:#fff
    style WN fill:#9C27B0,color:#fff
    style SPLIT fill:#9C27B0,color:#fff
    style K6 fill:#9C27B0,color:#fff
    style M3 fill:#4682B4,color:#fff
    style TOPO fill:#4682B4,color:#fff
    style TM fill:#4682B4,color:#fff
    style PL2 fill:#FDD835,color:#000
```

**Actor:** MODEL-MAINTAINER
**Verantwortung:** Model pflegen (W{n}, GC, Split)

**Datenfluss:**
1. Liest Model.md → Aktueller Stand
2. Liest OBSERVE{N}.md → Findings F1-Fn
3. Liest ERGEBNIS{N-1} → Widerlegungen
4. GC Engine: Markiert W{n} als WIDERLEGT/ELIMINIERT
5. W{n} Manager: Fügt neue W{n} hinzu (aus Findings)
6. Split Engine: Prüft >15 W{n}/TC → Bei PFLICHT: Split ausführen
7. Kap. 6a Update: Aktualisiert Offene Bereiche, Aktive TCs
8. Schreibt Model.md (v{N+1})
9. Bei Split: Schreibt Model-Topologie + Teilmodelle
10. Optional: Schreibt _parking-lot.md

---

### Phase 3: Quality Gate (/_SC_qualityGate)

```mermaid
graph LR
    subgraph "Inputs"
        M4[Model.md<br/>v{N+1}]
        OBS4[OBSERVE N<br/>Findings]
        E4[ERGEBNIS N-1<br/>SRS-Score]
        TOPO4[Model-Topologie<br/>falls Split]
    end

    subgraph "/_SC_qualityGate"
        BR[Gate 1<br/>Battle-Royale<br/>SRS-Trend<br/>R-AP1..R-AP5]
        KOH[Gate 2<br/>Kohäsion<br/>W{n}/TC<br/>Split-Trigger]
        FA[Gate 3<br/>Feature-Abschluss<br/>90%+ Coverage]
        BSD[Gate 4<br/>BSD-Trigger<br/>T1-T5 Muster]
        STAG[Gate 5<br/>Stagnation<br/>Fortschritts-Zähler]
    end

    subgraph "Outputs"
        QGATE[QUALITYGATE N<br/>5 Gate Results]
        PL3[_parking-lot.md<br/>Incidental Tasks]
        TRIGGER[Optional Triggers<br/>/_SC_blindspotDetection<br/>/_SC_archBoundaries]
    end

    M4 --> BR
    M4 --> KOH
    OBS4 --> BR
    OBS4 --> FA
    E4 --> BR
    E4 --> STAG
    TOPO4 --> KOH

    BR --> QGATE
    KOH --> QGATE
    FA --> QGATE
    BSD --> QGATE
    STAG --> QGATE

    QGATE --> TRIGGER
    QGATE -.->|optional| PL3

    style M4 fill:#4682B4,color:#fff
    style OBS4 fill:#26C6DA,color:#fff
    style E4 fill:#3F51B5,color:#fff
    style TOPO4 fill:#4682B4,color:#fff
    style BR fill:#AB47BC,color:#fff
    style KOH fill:#AB47BC,color:#fff
    style FA fill:#AB47BC,color:#fff
    style BSD fill:#AB47BC,color:#fff
    style STAG fill:#AB47BC,color:#fff
    style QGATE fill:#AB47BC,color:#fff
    style PL3 fill:#FDD835,color:#000
    style TRIGGER fill:#E91E63,color:#fff
```

**Actor:** QUALITY-GATE
**Verantwortung:** Quality Gates prüfen, Eskalationen triggern

**Datenfluss:**
1. Liest Model.md (v{N+1}) → Aktualisierter Stand nach ModelMaintain
2. Liest OBSERVE{N}.md → Findings für Kontext
3. Liest ERGEBNIS{N-1} → SRS-Score für BR-Bewertung
4. Liest Model-Topologie (falls Split aktiv) → Für Kohäsions-Check
5. **Gate 1 (Battle-Royale):** SRS-Trend, R-AP1..R-AP5
6. **Gate 2 (Kohäsion):** W{n}/TC zählen, Split-Trigger
7. **Gate 3 (Feature-Abschluss):** 90%+ Coverage?
8. **Gate 4 (BSD-Trigger):** T1-T5 Muster detektiert?
9. **Gate 5 (Stagnation):** Fortschritts-Zähler, Schwellen
10. Schreibt QUALITYGATE{N}.md mit 5 Gate-Results
11. Triggert optional: /_SC_blindspotDetection, /_SC_archBoundaries
12. Optional: Schreibt _parking-lot.md

---

## Parking Lot Integration

```mermaid
graph TD
    subgraph "Commands (Writers)"
        OBS[/_SC_observe]
        MM[/_SC_modelMaintain]
        QG[/_SC_qualityGate]
        HYPO[/_SC_hypothese]
        IMPL[/_SC_implement]
        ERG[/_SC_ergebnis]
        KNOW[/_knowledge]
        BSD[/_SC_blindspotDetection]
    end

    subgraph "Parking Lot (APPEND-ONLY)"
        PL[_parking-lot.md<br/>Incidental Findings]
    end

    subgraph "Task Manager (Reader)"
        TD[/_taskDefinition<br/>Proximity-Priorisierung]
    end

    subgraph "Outcomes"
        PROC[Task verarbeitet<br/>→ [x]]
        WAIT[Task warten<br/>→ [ ]]
        DISCARD[Task verworfen<br/>→ [~]]
    end

    OBS -.->|APPEND| PL
    MM -.->|APPEND| PL
    QG -.->|APPEND| PL
    HYPO -.->|APPEND| PL
    IMPL -.->|APPEND| PL
    ERG -.->|APPEND| PL
    KNOW -.->|APPEND| PL
    BSD -.->|APPEND| PL

    PL -->|READ bei Cycle-Ende| TD

    TD --> PROC
    TD --> WAIT
    TD --> DISCARD

    style PL fill:#FDD835,color:#000
    style TD fill:#00BCD4,color:#fff
    style OBS fill:#26C6DA,color:#fff
    style MM fill:#9C27B0,color:#fff
    style QG fill:#AB47BC,color:#fff
    style PROC fill:#4CAF50,color:#fff
    style WAIT fill:#FF9800,color:#fff
    style DISCARD fill:#E74C3C,color:#fff
```

**Konzept:**
- Alle Commands können **APPEND** zu Parking Lot
- Nur **_taskDefinition** liest (bei Cycle-Ende)
- **Proximity-Priorisierung:** Tasks mit gleichem TC = höhere Priorität
- **3 Outcomes:** Verarbeitet [x], Warten [ ], Verworfen [~]

---

## Komplette Chain: v2.2

```mermaid
graph TD
    subgraph "Pre-Cycle"
        TASK[Task.md]
        POM[pileOfMud/*]
        TD[/_taskDefinition]
        CRUMB[crumbs/{NAME}_crumbs.md]
    end

    subgraph "Init"
        MOD[/_model]
        MODEL[models/{NAME}_Model.md]
    end

    subgraph "Cycle N"
        ERES[ERGEBNIS N-1]

        subgraph "Analyse-Phase (3 Commands)"
            OBS[/_SC_observe]
            OBSDOC[OBSERVE N]

            MM[/_SC_modelMaintain]
            MODELUP[Model.md v{N+1}]

            QG[/_SC_qualityGate]
            QGATE[QUALITYGATE N]
        end

        HYPO[/_SC_hypothese]
        HYPODOC[HYPOTHESEN.md]

        IMPL[/_SC_implement]
        CODE[Code Changes]

        ERG[/_SC_ergebnis]
        ERESDOC[ERGEBNIS N]
    end

    subgraph "Optional (Parallel)"
        KNOW[/_knowledge]
        KNOWDOC[{THEMA}_Wissen.md]

        BSD[/_SC_blindspotDetection]
        BSDDOC[BLINDSPOT{N}.md]

        BOUND[/_SC_archBoundaries]
        BOUNDDOC[BOUNDARIES.md]
    end

    subgraph "Infrastructure"
        PL[_parking-lot.md]
        MANIFEST[_manifest.md]
    end

    subgraph "Output"
        PRES[/_presentation]
        PRESDOC[{TICKET}-{TYPE}.md]
    end

    TASK --> TD
    POM --> TD
    TD --> CRUMB

    CRUMB --> MOD
    MOD --> MODEL

    MODEL --> OBS
    ERES --> OBS
    OBS --> OBSDOC
    OBS -.-> PL

    OBSDOC --> MM
    MODEL --> MM
    ERES --> MM
    MM --> MODELUP
    MM -.-> PL

    OBSDOC --> QG
    MODELUP --> QG
    ERES --> QG
    QG --> QGATE
    QG -.-> PL

    QGATE --> HYPO
    MODELUP --> HYPO
    HYPO --> HYPODOC
    HYPO -.-> PL

    HYPODOC --> IMPL
    MODELUP --> IMPL
    IMPL --> CODE
    IMPL --> HYPODOC
    IMPL -.-> PL

    HYPODOC --> ERG
    MODELUP --> ERG
    ERG --> ERESDOC
    ERG -.-> PL

    ERESDOC -->|Loop| OBS

    QG -.->|Trigger T1-T5| BSD
    QG -.->|Trigger Zerlegung| BOUND

    MODEL --> KNOW
    KNOW --> KNOWDOC
    KNOW -.-> PL

    BSD --> BSDDOC
    BOUND --> BOUNDDOC

    ERESDOC --> PRES
    PRES --> PRESDOC

    PL -->|READ bei Cycle-Ende| TD

    style OBS fill:#26C6DA,color:#fff
    style MM fill:#9C27B0,color:#fff
    style QG fill:#AB47BC,color:#fff
    style PL fill:#FDD835,color:#000
    style MANIFEST fill:#00BCD4,color:#fff
```

---

## Actor-Separation: SRP Enforcement

| Actor | Command | Verantwortung | Schreibt | Liest |
|-------|---------|---------------|----------|-------|
| **OBSERVER** | /_SC_observe | Findings sammeln | OBSERVE{N}.md | Model, ERGEBNIS{N-1}, Codebase |
| **MODEL-MAINTAINER** | /_SC_modelMaintain | Model pflegen | Model.md, Topologie | Model, OBSERVE{N}, ERGEBNIS{N-1} |
| **QUALITY-GATE** | /_SC_qualityGate | Quality Gates prüfen | QUALITYGATE{N}.md | Model, OBSERVE{N}, ERGEBNIS{N-1}, Topologie |
| **HYPOTHESIS-DESIGNER** | /_SC_hypothese | Hypothese aufstellen | HYPOTHESEN.md | Model, QUALITYGATE{N} |
| **IMPLEMENTER** | /_SC_implement | Code schreiben | Code, HYPOTHESEN (update) | HYPOTHESEN, Model, Pattern-Lib |
| **MEASURER** | /_SC_ergebnis | Ergebnisse messen | ERGEBNIS{N}.md | HYPOTHESEN, Model, Logs |

**SRP-Prinzip:**
- Jeder Actor hat **EINE** Verantwortung
- **KEINE** überlappenden Verantwortlichkeiten
- Änderungen an einem Actor → **KEIN** Einfluss auf andere

---

## 3-Tupel-Validierung

| Tupel | n-1 SCHREIBT | n LIEST | n+1 LIEST | Status |
|-------|--------------|---------|-----------|--------|
| ERGEBNIS → OBSERVE → MM | ERGEBNIS{N-1}.md | ✅ Model, ERGEBNIS{N-1} | ✅ OBSERVE{N} | ✅ OK |
| OBSERVE → MM → QG | OBSERVE{N}.md | ✅ OBSERVE{N} | ✅ OBSERVE{N} | ✅ OK |
| MM → QG → HYPOTHESE | Model.md (updated) | ✅ Model | ✅ QUALITYGATE{N} | ✅ OK (nach F5/F6 Fix) |
| QG → HYPOTHESE → IMPLEMENT | QUALITYGATE{N}.md | ✅ QUALITYGATE{N} | ✅ HYPOTHESEN | ✅ OK (nach F6 Fix) |
| HYPOTHESE → IMPLEMENT → ERGEBNIS | HYPOTHESEN.md | ✅ HYPOTHESEN | ✅ HYPOTHESEN | ✅ OK |
| IMPLEMENT → ERGEBNIS → OBSERVE | ERGEBNIS{N}.md | ✅ ERGEBNIS{N} | ✅ ERGEBNIS{N} | ✅ OK |

**Ergebnis:** ALLE 3-Tupel valide ✅

---

## Siehe auch

- [[SC_observe]] - Phase 1 Details
- [[SC_modelMaintain]] - Phase 2 Details
- [[SC_qualityGate]] - Phase 3 Details
- [[CMD_parking-lot]] - Parking Lot Pattern
- [[_help]] - System-Übersicht
- [[Topologie-OmniCommand]] - Vollständige Topologie
