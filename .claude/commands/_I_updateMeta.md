# /_I_updateMeta - Implementation-Konvention mit manuellem Fund ergaenzen

**Zweck:** Nach einem manuellen Fix den Code-Generator fuer kuenftige Aufrufe kluegers machen — neue Domain-Konvention als Regel in `.claude/meta/implementation/{topic}.md` schreiben. Damit liest der naechste Worker diese Regel VOR der Generierung und produziert sofort konformen Code.

**Kein Git. Keine Code-Aenderungen. Nur implementation/ Meta-Datei.**

---

```yaml
type: building-block
status: final
version: 1.0.0
```

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_updateMeta                                         ║
╠══════════════════════════════════════════════════════════════════╣
║  LIEST:                                                          ║
║    1. Raw Input (Freitext oder Datei-Pfad vom User)              ║
║    2. .claude/meta/implementation/{topic}.md (Ziel-Datei,        ║
║       falls existiert)                                           ║
║  SCHREIBT:                                                       ║
║    1. .claude/meta/implementation/{topic}.md (+neue Regel,       ║
║       +Version-Update)                                           ║
║  INVARIANTEN:                                                    ║
║    - Kein Git (kein add, commit, push)                           ║
║    - Kein Code (keine .cs, .csproj Dateien)                      ║
║    - Nur implementation/ Dateien schreiben                       ║
║    - Duplikat-Check vor jedem Schreiben                          ║
║    - Format-Konsistenz: R{N}-Schema strikt einhalten             ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Aufruf-Signatur

```
/_I_updateMeta [topic] "[Regel-Beschreibung]"
```

**Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| `topic` | String (6 Optionen) | OPTIONAL | routing \| auth \| testing \| validation \| error-handling \| dto-mapping. Falls fehlt: automatische Klassifizierung via Keyword-Heuristik |
| `Regel-Beschreibung` | Freitext oder Pfad | OPTIONAL | Beschreibung des manuellen Funds. Falls fehlt: interaktiv nachfragen |

**Aufruf-Varianten:**

```
# Vollstaendig (minimale Interaktion):
/_I_updateMeta routing "API-Route Parameter sollten Plural sein"

# Nur Topic (Beschreibung interaktiv):
/_I_updateMeta routing

# Nur Beschreibung (Topic wird klassifiziert):
/_I_updateMeta "API-Route /api/v1/Pflegeeinrichtung gab 404"

# Datei als Input:
/_I_updateMeta /pfad/zur/problemBeschreibung.md

# Ohne Parameter (vollstaendig interaktiv):
/_I_updateMeta
```

---

## Topic-zu-Datei-Mapping

| Ereignis / Fehler | Topic | Datei |
|---|---|---|
| Route gibt 404, falsche URL-Konvention | routing | `.claude/meta/implementation/routing.md` |
| Route-Versioning fehlt (/api/v1/) | routing | `.claude/meta/implementation/routing.md` |
| Auth-Fehler 401, falscher Header | auth | `.claude/meta/implementation/auth.md` |
| [Authorize]-Attribute fehlt am Controller | auth | `.claude/meta/implementation/auth.md` |
| Unit-Test erbt nicht TestBase{T} | testing | `.claude/meta/implementation/testing.md` |
| TestBuilder-Pattern nicht verwendet | testing | `.claude/meta/implementation/testing.md` |
| FluentValidation nicht verwendet | validation | `.claude/meta/implementation/validation.md` |
| Validator nicht per DI injiziert | validation | `.claude/meta/implementation/validation.md` |
| Falsche Exception-Type verwendet | error-handling | `.claude/meta/implementation/error-handling.md` |
| Error Response hat falsches Format | error-handling | `.claude/meta/implementation/error-handling.md` |
| AutoMapper redundante ForMember-Calls | dto-mapping | `.claude/meta/implementation/dto-mapping.md` |
| ProjectTo nicht verwendet fuer Query | dto-mapping | `.claude/meta/implementation/dto-mapping.md` |

---

## Ablauf

### Phase 1: Input validieren + Topic bestimmen

**Schritt 1 — Raw Input lesen:**

```
Eingabe-Quellen:
  A) Freitext (aus Parametern oder interaktiv)
  B) Datei-Pfad (.md, .txt, .log)

Aktion:
  - Falls Pfad erkannt (startet mit / oder ./) → Datei lesen (Read-Tool)
  - Falls Freitext → direkt als content verwenden
  - Falls kein Input → Nachfragen: "Beschreibe den manuellen Fund:"

Output: content (String, nicht leer)
```

**Schritt 2 — Topic klassifizieren (Keyword-Heuristik):**

```
IF content CONTAINS ("Route", "Endpoint", "plural", "/api/v1", "URL", "REST", "Pfad", "404")
  → routing
ELSE IF content CONTAINS ("JWT", "Bearer", "Authorize", "Claims", "Token", "Auth", "401")
  → auth
ELSE IF content CONTAINS ("TestBuilder", "Fixture", "Mock", "TestBase", "xUnit", "Unit Test")
  → testing
ELSE IF content CONTAINS ("FluentValidation", "Validator", "RuleFor", "Validation", "IValidator")
  → validation
ELSE IF content CONTAINS ("Exception", "GlobalHandler", "Error Response", "Status Code", "throw", "ProblemDetails")
  → error-handling
ELSE IF content CONTAINS ("AutoMapper", "ProjectTo", "ForMember", "Mapping", "DTO", "Profile")
  → dto-mapping
ELSE
  → AskUserQuestion (6 Optionen, siehe unten)
```

Falls kein Keyword-Match:

```
AskUserQuestion:
  header: "Topic"
  question: "Welchem I_MetaPattern-Topic gehoert dieser Fund?"
  options:
    - label: "routing"         description: "API-Route Design (Plural, Versioning, URL-Konventionen)"
    - label: "auth"            description: "Authentication & Authorization (JWT, Claims, Bearer)"
    - label: "testing"         description: "Test-Struktur & TestBuilder Patterns (Unit/Integration/E2E)"
    - label: "validation"      description: "Input Validation (FluentValidation, Custom Validators)"
    - label: "error-handling"  description: "Exception Mapping, Global Handler, Response Format"
    - label: "dto-mapping"     description: "AutoMapper Profiles, ProjectTo, Bidirektionale Mappings"
```

---

### Phase 2: Ziel-Datei eroeffnen / oeffnen

**Schritt 3 — Ziel-Datei bestimmen und lesen:**

```
target_file = ".claude/meta/implementation/" + topic + ".md"

WENN target_file existiert:
  → Datei lesen (Read-Tool)
  → Bestimme max_rule_number: Hoechstes N aus allen "### R{N}:" Eintraegen (oder 0)
  → next_rule_number = max_rule_number + 1

WENN target_file NICHT existiert:
  → Erstelle Skeleton (W33-konform, alle 6 Pflichtfelder):
    ---
    (kein YAML Frontmatter — nur Markdown-Header)
    ---
    # Implementation-Konvention: {TopicName}
    **Projekt:** {aus Kontext oder "(Template - OmniCommand)"}
    **Version:** 1.0
    **Letzte Aenderung:** {datum}
    **Kategorie:** FLAECHENDECKEND
    **Schwierigkeit:** NORMAL
    **Auto-Fix:** TEILWEISE

    ## Regeln

    ## Projekt-spezifische Ergaenzungen

  → Melde: "Datei fehlte — Skeleton erstellt: .claude/meta/implementation/{topic}.md"
  → max_rule_number = 0, next_rule_number = 1
```

---

### Phase 3: Duplikat-Check

**Schritt 4 — Bestehende Regeln pruefen:**

```
Fuer jede bestehende Regel R1..R{max_rule_number}:
  Vergleiche content mit (Regel.Titel + Regel.Beschreibung)
  IF Aehnlichkeit > 70% (Keyword-Overlap oder semantische Naehe):
    → AUSGABE:
      "Aehnliche Regel existiert bereits:"
      "  R{N}: {Titel}"
      "  Beschreibung: {erste Zeile der Beschreibung}"
      "Neue Regel wird NICHT geschrieben (Duplikat-Schutz)."
    → EXIT 0 (kein Fehler — Schutz hat funktioniert)

Falls KEIN Duplikat gefunden:
  → Weiter zu Schritt 5
```

---

### Phase 4: R{N} formulieren

**Schritt 5 — Neue Regel im Standardformat erstellen:**

```markdown
### R{N}: {Kurztitel (max 6 Woerter)}
- **Severity:** {BLOCKER|WARNUNG|INFO}
- **Auto-Fix:** {JA|NEIN|TEILWEISE}
- **Beschreibung:** {Vollstaendige Erklaerung WARUM diese Regel existiert — nicht nur WAS.
  Referenz auf konkreten Fehlerfall wenn vorhanden.}
- **Beispiel VORHER:**
  ```csharp
  // Konkretes Beispiel des Problems (kein Pseudocode)
  ```
- **Beispiel NACHHER:**
  ```csharp
  // Konkretes Beispiel der korrekten Loesung
  ```
- **Ausnahmen:** {Aufzaehlung konkreter Ausnahmen oder "Keine"}
- **Herkunft:** Manueller Fund nach I_code* ({YYYY-MM-DD})
```

**Severity-Entscheidung:**
- `BLOCKER` — verhindert korrektes Verhalten (404, Auth-Fehler, Test-Fail): MUSS immer beachtet werden
- `WARNUNG` — sollte beachtet werden, Ausnahmen moeglich
- `INFO` — Empfehlung, Best Practice, nicht kritisch

**Qualitaets-Check vor dem Schreiben:**
- Beschreibung erklaert WARUM (nicht nur WAS)
- Beispiel VORHER zeigt den echten Fehler aus dem tatsaechlichen Fund
- Beispiel NACHHER zeigt korrekte Loesung (kein Pseudocode)
- Kein Duplikat zu bestehenden Regeln (Schritt 4 bestanden)
- Severity korrekt eingestuft

---

### Phase 5: Datei schreiben + Version++

**Schritt 6 — Datei aktualisieren und Bestaetigung ausgeben:**

```
Aktion:
  A) Neue Regel ans Ende der "## Regeln" Section einfuegen
     (vor optionalem "## Projekt-spezifische Ergaenzungen" Block)
  B) Header aktualisieren:
     - **Version:** X.Y → X.(Y+0.1) — z.B. 1.0 → 1.1
     - **Letzte Aenderung:** {heutiges Datum YYYY-MM-DD}
  C) Datei schreiben (Write-Tool oder Edit-Tool)

Ausgabe:
  ✓ Neue Regel R{N} in .claude/meta/implementation/{topic}.md geschrieben

  Topic:     {topic}
  Regel:     R{N} — {Titel}
  Severity:  {severity}
  Auto-Fix:  {auto-fix}
  Datei:     .claude/meta/implementation/{topic}.md

  Das naechste /_I_codeSystem / /_I_codeIntegration / /_I_codeAtomic
  wird diese Regel automatisch beachten.
```

---

## QUICK-START Beispiel (DCSRE-93: routing.md R1 Route-Naming)

**Aufruf:**
```
/_I_updateMeta routing "API Route /api/v1/Pflegeeinrichtung gibt 404, korrekte Route ist /api/v1/pflegeeinrichtungen"
```

**Schritt 1 — Input:**
```
content = "API Route /api/v1/Pflegeeinrichtung gibt 404, korrekte Route ist /api/v1/pflegeeinrichtungen"
```

**Schritt 2 — Klassifizierung:**
```
MATCH: content CONTAINS "/api/v1" → routing
Topic = "routing"
```

**Schritt 3 — Ziel-Datei:**
```
target_file = ".claude/meta/implementation/routing.md"
Existiert? → (neu erstellt falls nicht vorhanden)
max_rule_number = 0, next_rule_number = 1
```

**Schritt 4 — Duplikat-Check:**
```
Vorhandene Regeln: KEINE
→ Kein Duplikat, weiter
```

**Schritt 5 — Neue Regel:**
```markdown
### R1: API-Routes Plural Lowercase
- **Severity:** BLOCKER
- **Auto-Fix:** TEILWEISE
- **Beschreibung:** RESTful API-Routes fuer Sammlungen und CRUD-Operationen
  muessen im Plural und in Kleinschreibung sein. Singular-Routes (z.B.
  /api/v1/Pflegeeinrichtung) sind ein REST-Anti-Pattern und fuehren zu
  404-Fehlern wenn die Konvention nicht bekannt ist.
- **Beispiel VORHER:**
  ```csharp
  [Route("api/v1/Pflegeeinrichtung")]   // Singular + PascalCase → 404!
  public class PflegeeinrichtungController { }
  ```
- **Beispiel NACHHER:**
  ```csharp
  [Route("api/v1/pflegeeinrichtungen")] // Plural + lowercase → 200 OK
  public class PflegeeinrichtungController { }
  ```
- **Ausnahmen:** Spezielle Singleton-Ressourcen (z.B. /api/v1/profile fuer aktuellen User)
- **Herkunft:** Manueller Fund nach I_code* (2026-02-24), Fallstudie DCSRE-93
```

**Schritt 6 — Ausgabe:**
```
✓ Neue Regel R1 in .claude/meta/implementation/routing.md geschrieben

Topic:     routing
Regel:     R1 — API-Routes Plural Lowercase
Severity:  BLOCKER
Auto-Fix:  TEILWEISE
Datei:     .claude/meta/implementation/routing.md

Das naechste /_I_codeSystem / /_I_codeIntegration / /_I_codeAtomic
wird diese Regel automatisch beachten.
```

---

## Lifecycle

### Phase 1: Projekt-Start — Foundation Rules (v1.0)

**Wann:** Vor dem ersten `/_I_codeSystem`-Aufruf auf einem neuen Feature-Branch

**Wer:** Team Lead oder Domain-Expert

**Was wird erstellt:**

```
Feature-Start (z.B. DCSRE-881):
  ├── /_W_fetch → sucht Obsidian Vault nach bestehenden implementation/*.md
  │     WENN gefunden → kopieren als Basis (Wissen wiederverwenden)
  │     WENN nicht gefunden → weiter
  │
  └── /_I_updateMeta {topic} "{Foundation-Regel}"
        → .claude/meta/implementation/{topic}.md erstellen (Skeleton + erste Regeln)
```

**Foundation Rules Charakteristik:**
- Kommen aus Team-Wissen, Standards, Architektur-Entscheidungen
- Herkunft: "Foundation (YYYY-MM-DD)" oder "Team-Entscheidung"
- Typisch 3-5 Regeln pro Topic (Version 1.0)
- NICHT aus Live-Fehlern sondern aus Vorwissen

**Backward-Kompatibilitaet (wenn implementation/ fehlt):**
```
/_I_codeSystem wird gestartet, .claude/meta/implementation/ existiert NICHT:
  → AUSGABE: "Kein implementation/ Folder gefunden."
            "Empfehlung: /_I_updateMeta {topic} (routing, auth, testing, ...)"
            "Weiter ohne Implementation-Regeln (kein Abbruch)."
  → Normale Code-Generierung ohne Meta-Anreicherung
```

### Phase 2: Im Betrieb — Live Rules via /_I_updateMeta (v1.1+)

**Wann:** Waehrend Feature-Entwicklung, nach jedem manuellen Fix

**Trigger-Situationen:**

| Situation | Wer ruft auf | Beispiel |
|-----------|--------------|---------|
| Worker findet Test-Fehler, fixt manuell | Worker oder Lead | Route 404 → Konvention nicht bekannt |
| Code-Review-Kommentar entdeckt Pattern | Lead nach Review | "Immer ValidationResult.IsValid pruefen" |
| Architecture-Meeting-Ergebnis | Lead nach Meeting | "Global Exception Handler Strategy entschieden" |
| Nach Refactoring entdecktes Muster | Worker | "Alle Tests erben TestBase" |

**Lernschleife (Live):**

```
Iteration 1:
  [1] /_I_codeSystem liest routing.md (R1-R4)
  [2] Generiert Test mit /api/v1/pflegeeinrichtungen/{id} ✓
  [3] Test gruengefaerbt ← R1 "Routes Plural" hat funktioniert

Iteration 2 (neue Erkenntnis):
  [1] Worker generiert Test
  [2] Manuell Fix noetig: "Filter-Parameter brauchen ?status_ids nicht ?statusId"
  [3] /_I_updateMeta "Query-Parameter Plural (?status_ids)"
  [4] routing.md: R5 wird hinzugefuegt, Version 1.0 → 1.1

Iteration 3:
  [1] /_I_codeSystem liest routing.md (R1-R5)
  [2] Generiert sofort mit ?status_ids ✓ — kein Manual-Fix
```

**Wachstums-Erwartung:**
- Pro Feature: 2-5 neue Live-Regeln pro Topic (typisch)
- Version-Anstieg: 1.0 → 1.1 → 1.2 ... → ~1.6 nach einem Feature

### Phase 3: Wartung — Regeln reviewen und archivieren

**Wann:** Feature-Ende, oder wenn Regeln veraltet/falsch sind

**Aktionen:**

```
A) Veraltete Regeln markieren:
   - Regel hat Severity WARNUNG aber ist nie mehr relevant
   - Fuege Kommentar hinzu: "<!-- DEPRECATED: {Grund} -->"
   - Oder Severity nach INFO herunfstufen

B) Regeln ins Obsidian Vault exportieren:
   - /_W_modelSplit oder /_W_push_orchestrate
   - implementation/{topic}.md → Vault/implementation/{topic}.md
   - Naechstes Feature kann via /_W_fetch reuse

C) Rules-Konsolidierung:
   - R3 und R7 decken dasselbe ab? → R7 als "Ergaenzung zu R3" markieren
   - Duplikat-Regeln zusammenfuehren (Manual)

D) Pruefung auf codeKonvention-Uebergang:
   - Regel war zuerst in implementation/ (VOR Code) aber eigentlich besser fuer Post-Code?
   - Dann: Regel in codeKonvention/{gate}.md bewegen
   - Aus implementation/{topic}.md entfernen
```

**Invarianten Phase 3:**
- Kein automatisches Loeschen von Regeln (immer manuell bestaetigen)
- Version wird bei jeder Aenderung erhoehen
- Kein git commit in dieser Phase

---

## Abgrenzung zu /_PrePR_Update_Meta

| Dimension | `/_PrePR_Update_Meta` | `/_I_updateMeta` |
|---|---|---|
| **Ziel-Ordner** | `.claude/meta/codeKonvention/` | `.claude/meta/implementation/` |
| **Topics/Gates** | 9 Quality Gates | 6 Domain Topics |
| **Zeitachse** | NACH Code (Post-Review, Quality Gate) | NACH manuellem Fix, Regeln wirken VOR Code |
| **Wer liest Regeln** | `/_Pre_PR_*` Commands | `/_I_codeAtomic`, `/_I_codeIntegration`, `/_I_codeSystem` |
| **Trigger** | "Das haette Pre-PR finden sollen" | "Das haette Code-Generator wissen sollen" |
| **Regel-Format** | R{N} — Severity, AutoFix, VORHER/NACHHER | R{N} — IDENTISCH |
| **Duplikat-Check** | Ja (> 70% Aehnlichkeit) | Ja (> 70% Aehnlichkeit) — IDENTISCH |
| **Skeleton-Erstellung** | NEIN (Dateien existieren bereits) | JA (Datei kann fehlen → Skeleton erstellt) |

**Entscheidungsregel:**
```
"Wann wird die Regel gelesen?"
  VOR Code-Generierung → implementation/ (/_I_updateMeta)
  NACH Code-Generierung → codeKonvention/ (/_PrePR_Update_Meta)
```

**Beide zusammen moeglich:** Ein Problem (z.B. TestBase-Vererbung) kann BEIDE Seiten haben:
- `/_I_updateMeta testing` → naechster Worker generiert sofort mit TestBase (praeventiv)
- `/_PrePR_Update_Meta` → naechstes Pre-PR prueft TestBase nach (korrekturell)

---

## Regeln

- **KEIN Git** — weder `git add` noch `git commit` noch `git diff`
- **NUR implementation/ Dateien** schreiben — kein Code, keine Tests, keine anderen Dateien
- **KEIN YAML-Frontmatter** in Meta-Dateien — nur Markdown-Header (W6/W29)
- **Header-Titel:** immer `# Implementation-Konvention: {TopicName}` (W29) — NICHT `# Code-Konvention:`
- Duplikate vermeiden — vorher pruefen (Schritt 4)
- Format strikt einhalten — alle 8 Felder des R{N}-Schemas sind Pflicht
- Bei fehlendem Pflichtfeld: WARN und User nachfragen

---

## Backward-Kompatibilitaet (Graceful Degradation)

Wenn `/_I_code*` Commands aufgerufen werden und `.claude/meta/implementation/` fehlt:

```
WARN: "⚠️ .claude/meta/implementation/{topic}.md nicht gefunden"
SUGGEST: "Empfehlung: /_I_updateMeta kann Regeln hinzufuegen"
CONTINUE: Weitermachen ohne Meta-Anreicherung (KEIN ABORT)
```

**Garantie:** Alle `/_I_code*` Commands verhalten sich korrekt wenn `implementation/` fehlt, leer oder unvollstaendig ist. Das OPTIONAL-Flag sichert Backward-Kompatibilitaet fuer bestehende Feature-Branches.

---

## Obsidian-Tags

```yaml
tags:
  - type/command
  - pipeline/implementation
  - op/I_MetaPattern
  - topic/MetaPattern
  - topic/Command-Design
  - topic/KnowledgeExternalization
pipeline-position: standalone
related: [[_PrePR_Update_Meta]], [[_I_codeAtomic]], [[_I_codeIntegration]], [[_I_codeSystem]]
```
