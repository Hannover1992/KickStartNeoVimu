# 3-Wellen Dokumentations-Generator

Erstelle hochwertige technische Dokumentation für das angegebene Projekt/Komponente mit dem etablierten 3-Wellen-System.

**Ziel-Komponente:** $ARGUMENTS

---

## WORKFLOW-ÜBERSICHT

```
┌─────────────────────────────────────────────────────────────────┐
│  WELLE 1: HAIKU (Kartografie)                                   │
│  → Grober Überblick, Dateien lokalisieren                       │
│  → Output: Datei-Inventar + Komponenten-Map                     │
├─────────────────────────────────────────────────────────────────┤
│  WELLE 2: SONNET (Tiefenanalyse)                                │
│  → Details verstehen, Muster erkennen                           │
│  → Output: Architektur-Analyse + Code-Referenzen                │
├─────────────────────────────────────────────────────────────────┤
│  WELLE 3: OPUS (Synthese)                                       │
│  → Finale Dokumentation schreiben                               │
│  → Output: Produktionsreife MD-Dateien                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: WELLE 1 - HAIKU KARTOGRAFIE

Starte **3-6 Haiku-Agenten parallel** für den groben Überblick:

### Haiku-Aufträge:

**Haiku 1 - Einstiegspunkt:**
```
Finde den Haupteinstiegspunkt für [KOMPONENTE].
Suche nach: Controllers, Program.cs, Startup, Main-Klassen.
Liste alle gefundenen Dateien mit Pfad und Zeilenzahl.
```

**Haiku 2 - Services/Business Logic:**
```
Finde alle Service-Klassen für [KOMPONENTE].
Suche nach: *Service.cs, *Provider.cs, *Handler.cs
Liste: Dateiname, Namespace, wichtigste public Methoden.
```

**Haiku 3 - Datenmodelle:**
```
Finde alle DTOs, Entities, Models für [KOMPONENTE].
Suche nach: *Dto.cs, *Entity.cs, *Model.cs, *Request.cs, *Response.cs
Liste: Klassenname, Properties, Validierungen.
```

**Haiku 4 - Konfiguration:**
```
Finde Konfigurationsdateien für [KOMPONENTE].
Suche nach: appsettings*.json, *Options.cs, *Configuration.cs
Liste: Settings-Keys, Default-Werte, Environment-Variablen.
```

**Haiku 5 - Tests:**
```
Finde Test-Dateien für [KOMPONENTE].
Suche nach: *Tests.cs, *Test.cs im Tests-Ordner
Liste: Test-Klassen, Anzahl Tests, Test-Kategorien.
```

**Haiku 6 - Externe Abhängigkeiten:**
```
Finde externe Abhängigkeiten für [KOMPONENTE].
Analysiere: *.csproj für PackageReferences, Interfaces für externe Services.
Liste: NuGet-Pakete, externe APIs, Datenbank-Connections.
```

### Haiku-Output-Format:
```markdown
## Kartografie: [KOMPONENTE]

### Datei-Inventar
| Kategorie | Datei | Zeilen | Zweck |
|-----------|-------|--------|-------|
| Controller | XyzController.cs | 250 | REST API |
| Service | XyzService.cs | 400 | Business Logic |

### Komponenten-Beziehungen
- Controller → Service → Repository → Database
- Controller → External API Client
```

---

## PHASE 2: WELLE 2 - SONNET TIEFENANALYSE

Starte **3-4 Sonnet-Agenten** basierend auf Haiku-Ergebnissen:

### Sonnet-Aufträge:

**Sonnet 1 - Architektur-Analyse:**
```
Basierend auf der Haiku-Kartografie, analysiere die Architektur von [KOMPONENTE].

Lies die identifizierten Haupt-Dateien und erstelle:
1. Flowchart der Komponenten-Hierarchie (Mermaid)
2. Sequenzdiagramm für Hauptprozess (Mermaid)
3. Klassendiagramm für Datenmodelle (Mermaid)

Dokumentiere:
- Design Patterns (Factory, Strategy, Observer, etc.)
- Dependency Injection Setup
- Error Handling Strategie
```

**Sonnet 2 - API-Dokumentation:**
```
Analysiere alle REST/SOAP-Endpoints von [KOMPONENTE].

Erstelle für jeden Endpoint:
- HTTP-Methode + Route
- Request-Parameter (Query, Body, Header)
- Response-Struktur (JSON/XML)
- Status-Codes + Error-Responses
- Code-Referenz (Datei:Zeile)
```

**Sonnet 3 - Datenfluss-Analyse:**
```
Analysiere den Datenfluss durch [KOMPONENTE].

Erstelle:
1. State-Diagramm für Status-Übergänge
2. Sequenzdiagramm für typischen Request-Flow
3. Tabelle: Input → Transformation → Output

Dokumentiere:
- Validierungsregeln
- Transformation-Logik
- Persistenz-Schicht
```

**Sonnet 4 - Test-Coverage-Analyse:**
```
Analysiere die Test-Abdeckung von [KOMPONENTE].

Erstelle:
- Test-Matrix (Unit/Integration/E2E)
- Pie-Chart der Test-Verteilung
- Typischer Test-Flow (Sequenzdiagramm)
- Wichtige Test-Patterns + Beispiel-Code
```

### Sonnet-Output-Format:
```markdown
## Tiefenanalyse: [KOMPONENTE]

### Architektur-Übersicht
\`\`\`mermaid
flowchart TB
    subgraph Layer1["Presentation"]
        Controller
    end
    subgraph Layer2["Business"]
        Service
    end
\`\`\`

### Code-Referenzen
| Komponente | Datei:Zeile | Zweck |
|------------|-------------|-------|
| Validation | Service.cs:45-67 | Input-Prüfung |

### Qualitäts-Checkliste
- [x] Multi-Layer Architektur
- [x] Dependency Injection
- [ ] Vollständige Error-Handling
```

---

## PHASE 3: WELLE 3 - OPUS SYNTHESE

Erstelle die **finale Dokumentation** im etablierten Format:

### Dokumentations-Template:

```markdown
# [KOMPONENTE] - Architektur-Dokumentation

**Version:** 1.0 | **Stand:** YYYY-MM-DD

> **Navigation:** [INDEX](INDEX.md) | [Verwandte Docs] | **Aktuell**

**Fokus:** [Einzeiler-Beschreibung]

---

## Inhaltsverzeichnis
1. [Big Picture](#1-big-picture)
2. [Architektur](#2-architektur)
3. [API-Referenz](#3-api-referenz)
4. [Datenmodelle](#4-datenmodelle)
5. [Datenfluss](#5-datenfluss)
6. [Konfiguration](#6-konfiguration)
7. [Test-Abdeckung](#7-test-abdeckung)
8. [Quelldateien](#8-quelldateien)

---

## 1. Big Picture

> **Zweck:** [Was macht diese Komponente?]

\`\`\`mermaid
flowchart TB
    subgraph System["[KOMPONENTE]"]
        %% Hauptkomponenten hier
    end
\`\`\`

### Kernmerkmale
- Feature 1
- Feature 2
- Feature 3

---

## 2. Architektur

### 2.1 Design Patterns

| Pattern | Verwendung | Datei |
|---------|------------|-------|
| Factory | Objekt-Erstellung | Factory.cs |
| Strategy | Austauschbare Logik | Strategy.cs |

### 2.2 Schichtarchitektur

\`\`\`mermaid
flowchart TB
    subgraph Presentation
        Controller
    end
    subgraph Business
        Service
    end
    subgraph Data
        Repository
    end
    Controller --> Service --> Repository
\`\`\`

---

## 3. API-Referenz

### 3.1 Endpoints-Übersicht

| Method | Route | Beschreibung | Auth |
|--------|-------|--------------|------|
| GET | /api/v1/resource | Liste abrufen | JWT |
| POST | /api/v1/resource | Neu erstellen | JWT |

### 3.2 Endpoint-Details

#### GET /api/v1/resource

**Parameter:**
| Name | Typ | Required | Default | Beschreibung |
|------|-----|----------|---------|--------------|
| limit | int | nein | 100 | Max. Ergebnisse |

**Response (200 OK):**
\`\`\`json
{
  "totalCount": 42,
  "items": [...]
}
\`\`\`

**Fehler:**
| Status | Beschreibung |
|--------|--------------|
| 400 | Validation Error |
| 404 | Not Found |

---

## 4. Datenmodelle

### 4.1 Haupt-Entity

\`\`\`mermaid
classDiagram
    class Entity {
        +long Id
        +string Name
        +DateTime Created
    }
\`\`\`

### 4.2 DTOs

**RequestDto:**
\`\`\`json
{
  "name": "string",
  "value": 123
}
\`\`\`

**ResponseDto:**
\`\`\`json
{
  "id": 1,
  "name": "string",
  "createdAt": "2025-01-01T00:00:00Z"
}
\`\`\`

---

## 5. Datenfluss

### 5.1 Typischer Request-Flow

\`\`\`mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Controller
    participant Service
    participant Repository
    participant Database

    Client->>Controller: HTTP Request
    Controller->>Service: BusinessMethod()
    Service->>Repository: Query/Command
    Repository->>Database: SQL
    Database-->>Repository: Result
    Repository-->>Service: Entity
    Service-->>Controller: DTO
    Controller-->>Client: HTTP Response
\`\`\`

### 5.2 Status-Übergänge

\`\`\`mermaid
stateDiagram-v2
    [*] --> Created
    Created --> Processing : Start
    Processing --> Completed : Success
    Processing --> Failed : Error
    Failed --> Processing : Retry
    Completed --> [*]
\`\`\`

---

## 6. Konfiguration

### 6.1 appsettings.json

\`\`\`json
{
  "[KOMPONENTE]": {
    "Setting1": "value1",
    "Setting2": 100,
    "Timeout": "00:05:00"
  }
}
\`\`\`

### 6.2 Environment Variables

| Variable | Beschreibung | Default |
|----------|--------------|---------|
| COMPONENT_SETTING1 | Beschreibung | value1 |

---

## 7. Test-Abdeckung

### 7.1 Test-Verteilung

\`\`\`mermaid
pie title Test-Verteilung
    "Unit Tests" : 70
    "Integration Tests" : 25
    "E2E Tests" : 5
\`\`\`

### 7.2 Test-Matrix

| Komponente | Unit | Integration | E2E |
|------------|------|-------------|-----|
| Controller | ✅ | ✅ | ✅ |
| Service | ✅ | ✅ | - |
| Repository | ✅ | - | - |

---

## 8. Quelldateien

| Pfad | Komponente | Zeilen | Beschreibung |
|------|------------|--------|--------------|
| `Controllers/XyzController.cs` | API | 250 | REST Endpoints |
| `Services/XyzService.cs` | Business | 400 | Geschäftslogik |
| `Data/XyzRepository.cs` | Data | 150 | Datenzugriff |

---

## Zusammenfassung

\`\`\`mermaid
mindmap
  root(([KOMPONENTE]))
    API
      REST
      Swagger
    Business
      Services
      Validation
    Data
      Repository
      Database
    Tests
      Unit
      Integration
\`\`\`
```

---

## QUALITÄTS-CHECKLISTE

Prüfe die erstellte Dokumentation gegen diese Kriterien:

### Struktur
- [ ] Header mit Version + Stand
- [ ] Navigationsleiste
- [ ] Inhaltsverzeichnis mit Anker-Links
- [ ] Mindestens 8 Hauptsektionen

### Diagramme
- [ ] Big Picture Flowchart
- [ ] Sequenzdiagramm für Hauptprozess
- [ ] Klassendiagramm für Datenmodelle
- [ ] State-Diagramm (falls Status-Übergänge)
- [ ] Mindmap als Zusammenfassung

### API-Dokumentation
- [ ] Endpoint-Tabelle
- [ ] Parameter-Dokumentation
- [ ] Request/Response JSON-Beispiele
- [ ] Error-Codes + Beschreibung

### Code-Referenzen
- [ ] Datei:Zeile Format
- [ ] Quelldateien-Tabelle am Ende
- [ ] Code-Snippets mit Syntax-Highlighting

### Praktischer Nutzen
- [ ] < 15 Min zum Verstehen
- [ ] Copy-Paste-Ready Beispiele
- [ ] Troubleshooting-Hinweise

---

## AUSFÜHRUNGS-ANLEITUNG

### Schritt 1: Welle 1 starten
```
Starte 6 Haiku-Agenten parallel mit Task-Tool:
- Task(subagent_type="general-purpose", model="haiku", prompt="Haiku 1 Auftrag...")
- Task(subagent_type="general-purpose", model="haiku", prompt="Haiku 2 Auftrag...")
- ...alle 6 parallel in einem Message-Block
```

### Schritt 2: Welle 2 starten
```
Nach Haiku-Ergebnissen, starte 4 Sonnet-Agenten parallel:
- Task(subagent_type="general-sonnet-4", prompt="Sonnet 1 Auftrag + Haiku-Ergebnisse...")
- Task(subagent_type="general-sonnet-4", prompt="Sonnet 2 Auftrag + Haiku-Ergebnisse...")
- ...alle 4 parallel in einem Message-Block
```

### Schritt 3: Welle 3 - Dokumentation schreiben
```
Basierend auf Sonnet-Ergebnissen:
1. Erstelle Dokumentation im Template-Format
2. Speichere unter: [PROJEKT]/Dokumentation/[KOMPONENTE].md
3. Prüfe gegen Qualitäts-Checkliste
4. Iteriere bei Bedarf
```

---

## OUTPUT-STRUKTUR

```
[PROJEKT]/
└── Dokumentation/
    ├── INDEX.md                    # Übersicht aller Docs
    ├── [KOMPONENTE]_OVERVIEW.md    # Big Picture
    ├── [KOMPONENTE]_API.md         # API-Referenz (optional, bei großen APIs)
    ├── [KOMPONENTE]_ARCHITECTURE.md # Tiefe Architektur (optional)
    └── [KOMPONENTE]_TESTING.md     # Test-Dokumentation (optional)
```

---

## BEISPIEL-AUFRUF

```bash
/document VDEK.DCSP.DIC.Client
```

Erstellt Dokumentation für den DIC Client mit:
- 6 Haiku-Agenten für Kartografie
- 4 Sonnet-Agenten für Tiefenanalyse
- Opus für finale Synthese
- Output in `/VDEK.DCSP.DIC.Client/Dokumentation/`

---

**Beginne jetzt mit WELLE 1 für: $ARGUMENTS**
