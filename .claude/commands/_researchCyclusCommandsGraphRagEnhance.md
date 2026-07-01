---
type: building-block
---

# GraphRAG Enhancement: Forschungszyklus-Commands erweitern

Du analysierst ALLE Forschungszyklus-Commands und erstellst einen strukturierten
Enhancement-Report der exakt definiert, wo und wie GraphRAG-Hooks integriert werden.
Optional wendest du die Aenderungen direkt an.

## Aufruf

```
/_researchCyclusCommandsGraphRagEnhance [--dry-run|--apply]
```

- **--dry-run** (Default): Nur Report erstellen, KEINE Dateien aendern
- **--apply**: Report erstellen UND Aenderungen an Command-Dateien durchfuehren

---

## VERTRAG (Pflicht-I/O)

```
+===============================================================+
|  COMMAND: /_researchCyclusCommandsGraphRagEnhance              |
+===============================================================+
|                                                                |
|  LIEST (Input):                                                |
|    1. .claude/commands/_*.md                                   |
|       -> Alle 14 Command-Dateien des Forschungszyklus          |
|    2. {VAULT}/_manifest.md                            |
|       -> NAME, FEATURE, aktueller Stand                        |
|    3. .mcp.json (falls vorhanden)                              |
|       -> GraphRAG MCP Server Konfiguration pruefen             |
|    4. .claude/commands/_retrospektive.md                       |
|       -> Referenz-Implementation (bereits GraphRAG-integriert) |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. .claude/analysis/synthese/GraphRAG-Enhancement-Report.md |
|       -> Strukturierter Enhancement-Report (IMMER)             |
|    2. .claude/commands/_*.md (NUR bei --apply)                 |
|       -> 10 von 14 Command-Dateien erweitert                   |
|    3. {VAULT}/_manifest.md                            |
|       -> Enhancement-Status aktualisieren                      |
|                                                                |
|  KERNREGEL:                                                    |
|    GraphRAG = ENHANCER, nicht BLOCKER.                         |
|    Kein Command darf durch fehlenden MCP abbrechen.            |
|    Graceful Degradation bei JEDEM Hook.                        |
|                                                                |
+===============================================================+
```

---

## Schritt 0: Command-Inventar + MCP-Status

**Command-Max:** opus (effektiv = min(SYSTEM-MODEL, opus))

```
1. Lies {VAULT}/_manifest.md
   -> Ermittle {NAME}, {FEATURE}
   -> Lies SYSTEM-MODEL aus System-Konfiguration
   -> Bestimme effektives Modell: min(SYSTEM-MODEL, opus)

2. Sammle ALLE Command-Dateien:
   -> Glob: .claude/commands/_*.md
   -> Erwartete Anzahl: 14 Dateien

3. Kategorisiere die Commands:

   CORE-CYCLE (6):
     _analyse, _hypothese, _model, _implement, _ergebnis, _knowledge

   PRE-CYCLE (1):
     _taskDefinition

   META (1):
     _scientific

   OUTPUT (2):
     _presentation, _W_obsidianSync

   REFERENCE (2):
     _help, _obsidianHelp

   ALREADY-GRAPHRAG (1):
     _retrospektive

   SUPERSEDED (1):
     _knowledgeObsidianSync (durch _W_obsidianSync ersetzt)

4. Pruefe .mcp.json auf GraphRAG MCP:
   -> Falls vorhanden: Lies Server-Name und verfuegbare Tools
   -> Falls NICHT vorhanden: WARNUNG ausgeben, Report trotzdem erstellen
   -> MCP-Status = VERFUEGBAR | NICHT_KONFIGURIERT | NICHT_ERREICHBAR
```

---

## Schritt 1: MCP-Tool-Inventar

```
Definiere die erwarteten MCP-Tools in zwei Stufen:

=== MINIMUM VIABLE MCP (5 Tools) ===

Diese Tools MUESSEN vorhanden sein damit --apply funktioniert:

1. graphrag__create_collection(name, description)
   -> Erstellt eine neue Collection (lokal oder global)
   -> Parameter: name: string, description: string
   -> Return: collection_id

2. graphrag__list_collections()
   -> Listet alle vorhandenen Collections
   -> Return: collections[]

3. graphrag__ingest_document(collection, content, metadata)
   -> Speist ein Dokument in eine Collection ein
   -> metadata: {type, tags[], source, date, confidence, feature}
   -> Return: document_id

4. graphrag__query(collection, question, top_k, filters)
   -> Semantische Suche in einer Collection
   -> filters: {type?, tags?, confidence_min?, date_range?}
   -> Return: results[] mit score, content, metadata

5. graphrag__query_negative(collection, question, top_k)
   -> Spezial-Query: NUR Entities mit tag "negativ"
   -> Durchsucht Anti-Patterns, Fehldiagnosen, widerlegte Hypothesen
   -> Return: results[] mit score, content, metadata

=== ERWEITERTE TOOLS (9 Tools) ===

Fuer volle Funktionalitaet (nicht blockierend wenn fehlend):

6. graphrag__ingest_entities(collection, entities[])
   -> Batch-Import atomarer Entities
   -> entity: {name, type, content, tags[], confidence, source}

7. graphrag__create_relationships(collection, relationships[])
   -> Verbindungen zwischen Entities anlegen
   -> relationship: {from_id, to_id, type, metadata}

8. graphrag__tag_entities(collection, entity_ids[], tags[])
   -> Tags zu bestehenden Entities hinzufuegen

9. graphrag__collection_stats(name)
   -> Statistiken einer Collection (Anzahl Entities, Relationships, Tags)

10. graphrag__delete_collection(name)
    -> Collection loeschen (Cleanup)

11. graphrag__get_entity(collection, id)
    -> Einzelnes Entity abrufen

12. graphrag__get_related(collection, entity_id, depth)
    -> Graph-Traversal: Verwandte Entities finden

13. graphrag__search_similar(collection, content, top_k)
    -> Aehnlichkeitssuche basierend auf Inhalt

14. graphrag__update_entity(collection, entity_id, updates)
    -> Entity aktualisieren (Idempotenz)

=== ENTITY-TYPEN (10 Typen) ===

wahrheit, anti-pattern, fehldiagnose, best-practice,
architektur-entscheidung, komponente, risiko,
widerlegte-hypothese, zeitfresser, entscheidung

=== RELATIONSHIP-TYPEN (8 Typen) ===

bestaetigt_durch, widerlegt, geloest_durch, betrifft,
abhaengig_von, alternative_zu, verursacht_durch, anwendbar_in

=== FILTER/TAG-KONVENTIONEN ===

- tag: "negativ"   -> Anti-Patterns, Fehldiagnosen, widerlegte Hypothesen
- tag: "global"    -> Projektuebergreifend relevante Entities
- tag: "topic/{X}" -> Thematische Zuordnung (z.B. topic/wcf, topic/sftp)
- tag: "type/{X}"  -> Entity-Typ (z.B. type/wahrheit, type/anti-pattern)
- tag: "feature/{X}" -> Feature-Zuordnung (z.B. feature/DCSRE-881)
```

---

## Schritt 2: Graceful Degradation Pattern

```
Dieses Pattern wird in JEDEN Enhanced-Command eingefuegt.
Es ist das TEMPLATE fuer Schritt 0b:

┌─────────────────────────────────────────────────────────────┐
│  TEMPLATE: Schritt 0b - GraphRAG-Kontext (OPTIONAL)         │
│                                                              │
│  Falls GraphRAG MCP verfuegbar:                              │
│    1. query({COLLECTION}, "{KONTEXT-FRAGE}", top_k={N})     │
│       -> Relevantes Vorwissen aus bisherigen Zyklen          │
│    2. query_negative("global", "{NEGATIV-FRAGE}", top_k={N})│
│       -> Bekannte Anti-Patterns und Fehldiagnosen            │
│    3. Ergebnisse als "## GraphRAG-Kontext" bereitstellen     │
│       -> Wird als zusaetzlicher Input fuer die Phase genutzt │
│                                                              │
│  Falls GraphRAG MCP NICHT verfuegbar:                        │
│    -> WARNUNG: "GraphRAG nicht verfuegbar -                  │
│       fahre ohne Langzeitgedaechtnis fort"                   │
│    -> KEIN ABBRUCH - normal weiterarbeiten                   │
│    -> Kein Funktionsverlust, nur Wissensverlust              │
│                                                              │
│  Position: NACH Manifest-Lesen, VOR Hauptinputs              │
│  (zwischen Schritt 0, Punkt 1 und Punkt 2)                   │
└─────────────────────────────────────────────────────────────┘

Analog fuer Post-Synthese Ingest:

┌─────────────────────────────────────────────────────────────┐
│  TEMPLATE: Post-Synthese GraphRAG-Ingest (OPTIONAL)          │
│                                                              │
│  Falls GraphRAG MCP verfuegbar:                              │
│    1. ingest_document({COLLECTION}, {DOKUMENT}, {METADATA})  │
│       -> Synthese-Ergebnis im Graph speichern                │
│    2. Metadata: type={TYP}, tags=[...], source={PFAD},       │
│       date={DATUM}, confidence={WERT}, feature={FEATURE}     │
│                                                              │
│  Falls GraphRAG MCP NICHT verfuegbar:                        │
│    -> SKIP (kein Fehler, kein Verlust)                       │
│    -> Dokument existiert auf Disk (Retrospektive holt nach)  │
│                                                              │
│  Position: NACH dem Synthese-Schritt, VOR Manifest-Update    │
└─────────────────────────────────────────────────────────────┘
```

---

## Schritt 3: Enhancement-Spezifikation pro Command

### 3.1 _taskDefinition (PRE-CYCLE)

```
HOOK 1: Schritt 0 - Query (Vorwissen)
  Position: Nach Manifest-Lesen, vor pileOfMud-Lesen
  MCP-Aufruf:
    graphrag__query("global", "Vorwissen zu {NAME} {THEMA}", top_k=5)
  Kontext-Frage: "Was ist bereits bekannt ueber {NAME}?"
  Wert: Vorwissen aus frueheren Features einbeziehen
  Graceful Degradation: Ohne Query → nur pileOfMud als Input

HOOK 2: KEINE
  Begruendung: _taskDefinition erzeugt nur crumbs, keine verifizierten Erkenntnisse

DIFF (Schritt 0):
  VORHER:
    1. Lies {VAULT}/_manifest.md
    2. Lies {VAULT}/Task.md
    3. Lies .claude/pileOfMud/*

  NACHHER:
    1. Lies {VAULT}/_manifest.md
    1b. [GraphRAG] Falls MCP verfuegbar:
        query("global", "Vorwissen zu {NAME}", top_k=5)
        → Ergebnisse als "## Vorwissen (GraphRAG)" bereitstellen
        Falls MCP NICHT verfuegbar: → WARNUNG, weiter ohne
    2. Lies {VAULT}/Task.md
    3. Lies .claude/pileOfMud/*
```

### 3.2 _model (CORE-CYCLE)

```
HOOK 1: Schritt 0 - Query (Anti-Patterns + Vorwissen)
  Position: Nach Manifest-Lesen, vor crumbs-Lesen
  MCP-Aufrufe:
    graphrag__query("global", "Architektur-Wissen zu {NAME}", top_k=5)
    graphrag__query_negative("global", "Anti-Patterns zu {NAME}", top_k=5)
  Wert: Bekannte Fehler und Architektur-Entscheidungen von Anfang an kennen
  Graceful Degradation: Ohne Query → nur crumbs als Input

HOOK 2: Post-Synthese - Ingest (Model speichern)
  Position: Nach Model-Synthese (Welle 3), vor Manifest-Update
  MCP-Aufruf:
    graphrag__ingest_document("local:{FEATURE}",
      content=Model.md,
      metadata={type:"model", tags:["type/model","feature/{FEATURE}"],
                source:"models/{NAME}_Model.md", date:"{DATUM}",
                confidence:80, feature:"{FEATURE}"})
  Wert: Model im Graph querybar machen fuer spaetere Phasen
  Graceful Degradation: Ohne Ingest → Model existiert auf Disk

DIFF (Schritt 0):
  EINFUEGEN nach "Ermittle {NAME}" und vor "Lies crumbs":
    1b. [GraphRAG] Falls MCP verfuegbar:
        query("global", "Architektur zu {NAME}", top_k=5)
        query_negative("global", "Anti-Patterns zu {NAME}", top_k=5)
        → Ergebnisse als "## GraphRAG-Kontext" bereitstellen
        Falls MCP NICHT verfuegbar: → WARNUNG, weiter ohne

DIFF (Post-Synthese):
  EINFUEGEN nach Welle 3 (Synthese), vor Manifest-Update:
    [GraphRAG] Falls MCP verfuegbar:
        ingest_document("local:{FEATURE}", Model.md, {metadata})
        Falls MCP NICHT verfuegbar: → SKIP
```

### 3.3 _analyse (CORE-CYCLE)

```
HOOK 1: Schritt 0 - Query (Bisherige Erkenntnisse + Negativ)
  Position: Nach Manifest-Lesen + Auto-Increment, vor Model-Lesen
  MCP-Aufrufe:
    graphrag__query("local:{FEATURE}", "bisherige Erkenntnisse", top_k=10)
    graphrag__query_negative("global", "Anti-Patterns zu {NAME}", top_k=5)
  Wert: Frueherer Zyklus-Kontext + keine bekannten Fehler wiederholen
  Graceful Degradation: Ohne Query → nur Model als Input

HOOK 2: Post-Synthese - Ingest (Analyse speichern)
  Position: Nach Synthese-Welle, vor Manifest-Update
  MCP-Aufruf:
    graphrag__ingest_document("local:{FEATURE}",
      content=ANALYSE{CYCLE}.md,
      metadata={type:"analyse", tags:["type/analyse","feature/{FEATURE}",
                "cycle/{CYCLE}"],
                source:"synthese/{NAME}-ANALYSE{CYCLE}.md",
                date:"{DATUM}", feature:"{FEATURE}"})
  Wert: Analyse im Graph fuer _hypothese und spaetere Zyklen verfuegbar
  Graceful Degradation: Ohne Ingest → ANALYSE existiert auf Disk

DIFF (Schritt 0):
  EINFUEGEN nach Punkt 4 (Auto-Increment), vor Punkt "Variablen":
    5. [GraphRAG] Falls MCP verfuegbar:
       query("local:{FEATURE}", "Erkenntnisse Zyklus 1-{CYCLE-1}", top_k=10)
       query_negative("global", "Anti-Patterns zu {NAME}", top_k=5)
       → Ergebnisse als "## GraphRAG-Kontext" dem Model-Lesen voranstellen
       Falls MCP NICHT verfuegbar: → WARNUNG, weiter ohne
```

### 3.4 _hypothese (CORE-CYCLE)

```
HOOK 1: Schritt 0 - Query (Gescheiterte Ansaetze)
  Position: Nach Manifest-Lesen, vor ANALYSE-Lesen
  MCP-Aufrufe:
    graphrag__query_negative("global",
      "gescheiterte Ansaetze und widerlegte Hypothesen zu {NAME}", top_k=10)
    graphrag__query("local:{FEATURE}", "bisherige Hypothesen", top_k=5)
  Wert: KRITISCH - keine bereits widerlegten Hypothesen nochmal aufstellen
  Graceful Degradation: Ohne Query → Risiko falscher Hypothesen steigt

HOOK 2: Post-Synthese - Ingest (Hypothesen speichern)
  Position: Nach Hypothesen-Synthese, vor Manifest-Update
  MCP-Aufruf:
    graphrag__ingest_document("local:{FEATURE}",
      content=HYPOTHESEN.md,
      metadata={type:"hypothese", tags:["type/hypothese","feature/{FEATURE}"],
                source:"synthese/{NAME}-HYPOTHESEN.md",
                date:"{DATUM}", feature:"{FEATURE}"})
  Wert: Hypothesen querybar fuer _ergebnis

DIFF (Schritt 0):
  EINFUEGEN nach Manifest-Lesen, vor ANALYSE-Lesen:
    1b. [GraphRAG] Falls MCP verfuegbar:
        query_negative("global", "widerlegte Hypothesen zu {NAME}", top_k=10)
        query("local:{FEATURE}", "bisherige Hypothesen", top_k=5)
        → Ergebnisse als "## ACHTUNG: Bekannte Fehlansaetze" prominent anzeigen
        → Diese Ansaetze NICHT nochmal als Hypothese formulieren!
        Falls MCP NICHT verfuegbar: → WARNUNG, weiter ohne
```

### 3.5 _implement (CORE-CYCLE)

```
HOOK 1: Schritt 0 - Query (Anti-Patterns + Best-Practices)
  Position: Nach Manifest-Lesen, vor HYPOTHESEN-Lesen
  MCP-Aufrufe:
    graphrag__query_negative("global",
      "Implementierungs-Anti-Patterns zu {NAME}", top_k=5)
    graphrag__query("global",
      "Best-Practices Implementierung {NAME}", top_k=5,
      filters={type:"best-practice"})
  Wert: Bekannte Implementierungs-Fehler vermeiden, bewaehrte Muster nutzen
  Graceful Degradation: Ohne Query → Implementation ohne Langzeitgedaechtnis

HOOK 2: KEINE
  Begruendung: Code wird nicht in GraphRAG gespeichert.
  Code-Aenderungen werden ueber _ergebnis als Wahrheiten erfasst.

DIFF (Schritt 0):
  EINFUEGEN nach Manifest-Lesen, vor HYPOTHESEN-Lesen:
    [GraphRAG] Falls MCP verfuegbar:
        query_negative("global", "Implementierungs-Fehler {NAME}", top_k=5)
        query("global", "Best-Practices {NAME}", top_k=5, type="best-practice")
        → Ergebnisse als "## Bekannte Patterns" bereitstellen
        Falls MCP NICHT verfuegbar: → WARNUNG, weiter ohne
```

### 3.6 _ergebnis (CORE-CYCLE - SPEZIAL: 3 Hooks)

```
HOOK 1: Schritt 0 - Query (Bisherige Experiment-Ergebnisse)
  Position: Nach Manifest-Lesen, vor HYPOTHESEN-Lesen
  MCP-Aufrufe:
    graphrag__query("local:{FEATURE}",
      "bisherige Experiment-Ergebnisse", top_k=5)
  Wert: Kontext aus frueheren Iterationen

HOOK 2: Post-Ergebnis bei BESTAETIGT - Ingest Wahrheit
  Position: Nach Schritt 3 (MODEL AKTUALISIEREN), vor Schritt 4
  MCP-Aufruf:
    graphrag__ingest_entities("local:{FEATURE}", [{
      name: "W{n+1}: {Erkenntnis}",
      type: "wahrheit",
      content: "{Vollstaendige Wahrheit mit Kontext}",
      tags: ["type/wahrheit", "feature/{FEATURE}", "global",
             "topic/{THEMA}"],
      confidence: 95,
      source: "models/{NAME}_Model.md"
    }])
    graphrag__ingest_entities("global", [GLEICHE_ENTITY])
  Wert: Sofortige Einspeisung verifizierter Wahrheiten in BEIDE Collections

HOOK 3: Post-Ergebnis bei WIDERLEGT - Ingest Anti-Pattern (KRITISCH!)
  Position: Nach Schritt 3 (MODEL AKTUALISIEREN), vor Schritt 4
  MCP-Aufruf:
    graphrag__ingest_entities("local:{FEATURE}", [{
      name: "WIDERLEGT: {Hypothese}",
      type: "anti-pattern",
      content: "{Was angenommen wurde, warum es falsch ist, was stattdessen gilt}",
      tags: ["type/anti-pattern", "negativ", "feature/{FEATURE}",
             "global", "topic/{THEMA}"],
      confidence: 95,
      source: "synthese/{NAME}-HYPOTHESEN.md"
    }])
    graphrag__ingest_entities("global", [GLEICHE_ENTITY_MIT_TAG_NEGATIV])
  Wert: SOFORTIGE Einspeisung ins Negativ-Gedaechtnis!
        Verhindert dass zukuenftige _hypothese diesen Ansatz nochmal vorschlaegt.

DIFF (Schritt 3 - MODEL AKTUALISIEREN):
  EINFUEGEN nach "Version erhoehen", vor Schritt 4:
    3b. [GraphRAG] Falls MCP verfuegbar:
        Falls Hypothese BESTAETIGT:
          → ingest wahrheit in local:{FEATURE} UND global
          → Tags: type/wahrheit, global, topic/{THEMA}
        Falls Hypothese WIDERLEGT:
          → ingest anti-pattern in local:{FEATURE} UND global
          → Tags: type/anti-pattern, negativ, global, topic/{THEMA}
          → WICHTIG: tag "negativ" ist PFLICHT (query_negative!)
        Falls MCP NICHT verfuegbar: → SKIP
          (Retrospektive holt alle Entities nach)
```

### 3.7 _knowledge (CORE-CYCLE)

```
HOOK 1: Schritt 0 - Query (Vorhandenes Wissen)
  Position: Nach Manifest-Lesen, vor Model-Lesen
  MCP-Aufrufe:
    graphrag__query("global", "Wissen zu {THEMA}", top_k=10)
    graphrag__query("global", "Fehlverstaendnisse zu {THEMA}",
      filters={tags:["negativ"]}, top_k=5)
  Wert: Vorhandenes Wissen nicht nochmal recherchieren,
        bekannte Missverstaendnisse direkt adressieren

HOOK 2: Post-Synthese - Ingest (Wissen in BEIDE Collections)
  Position: Nach Welle 3 (Synthese), vor Manifest-Update
  MCP-Aufrufe:
    graphrag__ingest_document("local:{FEATURE}",
      content="{THEMA}_Wissen.md",
      metadata={type:"knowledge", tags:["type/knowledge","feature/{FEATURE}",
                "global","topic/{THEMA}"],
                source:"wissen/{THEMA}_Wissen.md",
                date:"{DATUM}", confidence:90, feature:"{FEATURE}"})
    graphrag__ingest_document("global",
      content="{THEMA}_Wissen.md",
      metadata={GLEICHE_METADATA})
  Wert: Knowledge ist IMMER global (fundiertes Wissen hat projektuebergreifenden Wert)
```

### 3.8 _scientific (META)

```
HOOK 1: Schritt 0 - Collection erstellen (SPEZIAL)
  Position: Am Anfang, vor Delegation an Sub-Commands
  MCP-Aufrufe:
    graphrag__list_collections()
    Falls "local:{FEATURE}" NICHT existiert:
      graphrag__create_collection("local:{FEATURE}",
        "Lokale Collection fuer {NAME} ({FEATURE})")
    Falls "global" NICHT existiert:
      graphrag__create_collection("global",
        "Globale, projektuebergreifende Wissens-Collection")
  Wert: Collection-Lifecycle Management - einmaliges Setup

HOOK 2: KEINE
  Begruendung: _scientific delegiert an Sub-Commands,
  jeder Sub-Command hat eigene Hooks

DIFF (Schritt 0 / "Starte jetzt"):
  EINFUEGEN vor "Falls Manifest existiert":
    0b. [GraphRAG] Falls MCP verfuegbar:
        → Collections pruefen/erstellen
        → "local:{FEATURE}" fuer Feature-spezifisches Arbeitsgedaechtnis
        → "global" fuer kuratiertes Langzeitgedaechtnis
        Falls MCP NICHT verfuegbar: → WARNUNG, weiter ohne
```

### 3.9 _presentation (OUTPUT)

```
HOOK 1: Schritt 0 - Query (Alle Erkenntnisse)
  Position: Nach Manifest-Lesen, vor Kontext-Dateien lesen
  MCP-Aufrufe:
    graphrag__query("local:{FEATURE}",
      "alle Erkenntnisse und Entscheidungen zu {NAME}", top_k=20)
  Wert: Vollstaendigen Kontext fuer Praesentation abrufen
        (inklusive aller Zyklen, nicht nur der letzte)

HOOK 2: KEINE
  Begruendung: Praesentation ist Output, kein neues Wissen

DIFF (Schritt 0):
  EINFUEGEN nach Manifest-Lesen, vor "Pruefe welche Analyse-Dateien existieren":
    1b. [GraphRAG] Falls MCP verfuegbar:
        query("local:{FEATURE}", "alle Erkenntnisse {NAME}", top_k=20)
        → Ergebnisse als zusaetzlicher Kontext fuer die Praesentation
        Falls MCP NICHT verfuegbar: → weiter mit Disk-Dateien
```

### 3.10 _help (REFERENCE)

```
HOOK: Text-Update (kein MCP-Aufruf)
  Aenderung in der ASCII-Box:

  VORHER:
    Sync:       /_W_obsidianSync (Synthese -> Obsidian Vault)

  NACHHER:
    Sync:       /_W_obsidianSync (Synthese -> Obsidian Vault)
    Memory:     GraphRAG (local:{FEATURE} + global Collection)
    Enhance:    /_researchCyclusCommandsGraphRagEnhance

  Zusaetzlich in DATEISYSTEM-VERTRAG:
    VORHER: (nicht vorhanden)
    NACHHER:
      GraphRAG Collections:
        local:{FEATURE}  <- Arbeitsgedaechtnis pro Feature
        global            <- Kuratiertes Langzeitgedaechtnis
        Tags: negativ, global, type/*, topic/*, feature/*
```

---

## Schritt 4: Nicht geaenderte Commands (4 Stueck)

```
| Command                | Begruendung                                        |
|------------------------|----------------------------------------------------|
| _W_obsidianSync          | Vault-Sync, kein Graph-Bezug                       |
| _knowledgeObsidianSync | SUPERSEDED (durch _W_obsidianSync ersetzt)            |
| _obsidianHelp          | Referenz-Dokument, kein Graph-Bezug                |
| _retrospektive         | HAT BEREITS vollstaendige GraphRAG-Integration     |
|                        | (dient als Referenz fuer alle anderen Hooks)       |
```

---

## Schritt 5: Enhancement-Report schreiben

```
Schreibe: .claude/analysis/synthese/GraphRAG-Enhancement-Report.md

---
type: enhancement-report
name: GraphRAG-Enhancement
datum: {YYYY-MM-DD}
status: {REPORT_ONLY | APPLIED}
mcp_status: {VERFUEGBAR | NICHT_KONFIGURIERT | NICHT_ERREICHBAR}
commands_analysiert: 14
commands_enhanced: 10
commands_unchanged: 4
---

# GraphRAG Enhancement Report

## 1. Executive Summary
- 14 Forschungszyklus-Commands analysiert
- 10 Commands erhalten GraphRAG-Hooks
- 4 Commands bleiben unveraendert
- MCP-Status: {STATUS}
- Graceful Degradation: ALLE Hooks sind optional

## 2. MCP-Tool-Inventar
### Minimum Viable (5 Tools)
{Tabelle aus Schritt 1}

### Erweitert (14 Tools)
{Tabelle aus Schritt 1}

### Entity-Typen und Relationships
{Listen aus Schritt 1}

## 3. Enhancement-Uebersicht
| # | Command | Hook 1 (Query) | Hook 2 (Ingest) | Hook 3 (Spezial) |
|---|---------|----------------|------------------|-------------------|
| 1 | _taskDefinition | global: Vorwissen | - | - |
| 2 | _model | global+negativ | local: Model | - |
| 3 | _analyse | local+negativ | local: Analyse | - |
| 4 | _hypothese | negativ (KRITISCH) | local: Hypothesen | - |
| 5 | _implement | negativ+best-practice | - | - |
| 6 | _ergebnis | local: Experimente | global: Wahrheit | global: Anti-Pattern! |
| 7 | _knowledge | global: Vorwissen | local+global: Wissen | - |
| 8 | _scientific | - | - | create_collection |
| 9 | _presentation | local: Kontext | - | - |
| 10 | _help | - | - | Text-Update |

## 4. Graceful Degradation Pattern
{Template aus Schritt 2}

## 5. Pro-Command Diff-Ansichten
{Fuer jedes der 10 Commands: VORHER/NACHHER aus Schritt 3}

## 6. Implementierungs-Reihenfolge (Empfohlen)
Phase 1 (Fundament):
  1. _scientific (Collection-Setup)
  2. _help (Text-Update, kein MCP noetig)

Phase 2 (Read-Hooks / Query):
  3. _hypothese (HOECHSTER WERT: verhindert falsche Hypothesen)
  4. _implement (Best-Practices abrufen)
  5. _analyse (Zyklus-Kontext)
  6. _ergebnis (Experiment-Historie)
  7. _model (Architektur-Kontext)
  8. _taskDefinition (Vorwissen)
  9. _presentation (Vollstaendiger Kontext)

Phase 3 (Write-Hooks / Ingest):
  10. _ergebnis Hook 2+3 (Wahrheiten + Anti-Patterns → SOFORT)
  11. _knowledge Hook 2 (Wissen → global)
  12. _model Hook 2 (Model → local)
  13. _analyse Hook 2 (Analyse → local)
  14. _hypothese Hook 2 (Hypothesen → local)

## 7. Offene Fragen / Voraussetzungen
- MCP-Server muss konfiguriert und erreichbar sein
- Collection-Naming-Konvention: "local:{FEATURE}" vs. "{FEATURE}"
- Idempotenz: Wie verhindert der MCP Server Duplikate?
- Embedding-Modell: Welches Modell fuer semantische Suche?
- Chunk-Groesse: Wie werden grosse Dokumente (>1000 Zeilen) gesplittet?
```

---

## Schritt 6: --apply Modus (Optional)

```
NUR wenn --apply angegeben:

1. Pruefe MCP-Verfuegbarkeit:
   → Falls NICHT verfuegbar: ABBRUCH
     "MCP nicht konfiguriert. Report wurde geschrieben.
      Konfiguriere zuerst GraphRAG MCP in .mcp.json,
      dann fuehre /_researchCyclusCommandsGraphRagEnhance --apply aus."

2. Fuer jedes der 10 Commands:
   a) Lies die aktuelle Datei
   b) Identifiziere die exakte Insert-Position (aus Schritt 3 DIFF)
   c) Fuege den Hook-Code ein (Schritt 0b bzw. Post-Synthese)
   d) Verifiziere: Datei ist syntaktisch korrekt

3. Reihenfolge der Anwendung:
   → _scientific ZUERST (Collection-Setup)
   → _help ZWEITES (Text-Update)
   → Dann alle anderen (Reihenfolge egal)

4. Manifest aktualisieren:
   → "GraphRAG Enhancement: APPLIED"
   → Liste der geaenderten Commands
   → Datum

5. Zusammenfassung:
   → Welche Dateien wurden geaendert
   → Welche Hooks wurden eingefuegt
   → Was muss der User jetzt tun (MCP testen)
```

---

## Schritt 7: Zusammenfassung ausgeben

```
/_researchCyclusCommandsGraphRagEnhance - Ergebnis:

| Kategorie | Anzahl |
|-----------|--------|
| Commands analysiert | 14 |
| Commands enhanced | 10 |
| Commands unchanged | 4 |
| Query-Hooks (Read) | 9 |
| Ingest-Hooks (Write) | 7 |
| Spezial-Hooks | 2 (collection-create, text-update) |
| MCP-Tools benoetigt (min) | 5 |
| MCP-Tools benoetigt (voll) | 14 |
| Entity-Typen | 10 |
| Relationship-Typen | 8 |

Report: .claude/analysis/synthese/GraphRAG-Enhancement-Report.md
Modus: {--dry-run (nur Report) | --apply (Report + Aenderungen)}
MCP-Status: {VERFUEGBAR | NICHT_KONFIGURIERT}

Naechster Schritt:
  Falls --dry-run: MCP konfigurieren, dann --apply ausfuehren
  Falls --apply: MCP-Tools testen mit /_scientific {NAME}
```

---

## Qualitaetskriterien

- **Graceful Degradation:** KEIN Command bricht durch fehlenden MCP ab
- **Atomare Hooks:** Jeder Hook ist unabhaengig aktivierbar/deaktivierbar
- **Referenz-Konsistenz:** Alle Hooks folgen dem _retrospektive Pattern
- **Idempotenz:** Mehrfaches --apply ueberschreibt, dupliziert nicht
- **Diff-Klarheit:** Jede Aenderung zeigt exakt VORHER/NACHHER
- **Negativ-Bias:** query_negative hat HOECHSTE Prioritaet (Anti-Patterns verhindern)

---

## Voraussetzungen

- Alle 14 Command-Dateien muessen unter .claude/commands/ existieren
- Manifest muss existieren (mindestens mit NAME und FEATURE)
- Fuer --apply: GraphRAG MCP muss in .mcp.json konfiguriert sein
- Fuer --dry-run: Keine Voraussetzungen (immer ausfuehrbar)

ARGUMENTS: $ARGUMENTS


● MCP GraphRAG Tool-Anforderungen

  Minimum Viable (5 Tools - PFLICHT)

  | #   | Tool              | Signatur                               | Zweck                                         |
  |-----|-------------------|----------------------------------------|-----------------------------------------------|
  | 1   | create_collection | (name, description)                    | Collection anlegen (local/global)             |
  | 2   | list_collections  | ()                                     | Vorhandene Collections auflisten              |
  | 3   | ingest_document   | (collection, content, metadata)        | Dokument einspeisen mit Metadata              |
  | 4   | query             | (collection, question, top_k, filters) | Semantische Suche mit Filtern                 |
  | 5   | query_negative    | (collection, question, top_k)          | Spezial-Query: NUR negativ-markierte Entities |

  Erweitert (9 Tools - optional, nicht blockierend)

  | #   | Tool                 | Signatur                           | Zweck                                       |
  |-----|----------------------|------------------------------------|---------------------------------------------|
  | 6   | ingest_entities      | (collection, entities[])           | Batch-Import atomarer Entities              |
  | 7   | create_relationships | (collection, relationships[])      | Graph-Kanten anlegen                        |
  | 8   | tag_entities         | (collection, entity_ids[], tags[]) | Tags nachtraeglich vergeben                 |
  | 9   | collection_stats     | (name)                             | Statistiken (Anzahl Entities/Relationships) |
  | 10  | delete_collection    | (name)                             | Collection loeschen (Cleanup)               |
  | 11  | get_entity           | (collection, id)                   | Einzelnes Entity abrufen                    |
  | 12  | get_related          | (collection, entity_id, depth)     | Graph-Traversal (verwandte Entities)        |
  | 13  | search_similar       | (collection, content, top_k)       | Aehnlichkeitssuche nach Inhalt              |
  | 14  | update_entity        | (collection, entity_id, updates)   | Entity aktualisieren (Idempotenz)           |

  Metadata-Schema (fuer ingest_document)

  metadata: {
    type:       string    // "wahrheit" | "anti-pattern" | "analyse" | ...
    tags:       string[]  // ["type/wahrheit", "negativ", "topic/wcf", ...]
    source:     string    // Quell-Pfad (z.B. "models/Dateiabholung_Model.md")
    date:       string    // YYYY-MM-DD
    confidence: number    // 0-100
    feature:    string    // z.B. "DCSRE-881"
  }

  Entity-Typen (10)

  wahrheit, anti-pattern, fehldiagnose, best-practice, architektur-entscheidung, komponente, risiko, widerlegte-hypothese, zeitfresser, entscheidung

  Relationship-Typen (8)

  bestaetigt_durch, widerlegt, geloest_durch, betrifft, abhaengig_von, alternative_zu, verursacht_durch, anwendbar_in

  Tag-Konventionen

  | Tag         | Bedeutung                                           |
  |-------------|-----------------------------------------------------|
  | negativ     | Anti-Patterns, Fehldiagnosen, widerlegte Hypothesen |
  | global      | Projektuebergreifend relevant                       |
  | topic/{X}   | Thematisch (z.B. topic/wcf, topic/sftp)             |
  | type/{X}    | Entity-Typ (z.B. type/wahrheit)                     |
  | feature/{X} | Feature-Zuordnung (z.B. feature/DCSRE-881)          |

  ---
  Kernaussage: Mit den 5 Minimum-Tools laeuft das System. Die 9 erweiterten Tools ermoeglichen granularere Graph-Operationen (Entities, Relationships, Traversal), sind aber nicht blockierend.
