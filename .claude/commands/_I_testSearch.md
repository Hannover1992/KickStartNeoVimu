# /_I_testSearch — Test-Suche & Kategorisierung

```yaml
status: active
version: 1.1.0
created: 2026-03-08
updated: 2026-04-02
op: TestSearch
phase: Architect
type: building-block
chain_position: architect-2-of-5
team_based: false
```

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_testSearch {NAME} --stufe {N} [--global] [--mode=tR] [--user-story {SCOPE}] ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                            ║
║    1. {VAULT}/_manifest.md                                  ║
║       (Pipeline-State, Blueprint-Pfad)                               ║
║    2. .claude/meta/implementation/stage_{N}.md                       ║
║       (Testtyp, Mock-Regeln, Scope — bestimmt Such-Strategie)       ║
║    3. .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md        ║
║       (Architektur — OPTIONAL bei --global/--mode=testRun)           ║
║    4. Codebase: Test-Verzeichnisse durchsuchen                       ║
║       (Glob/Grep nach *Tests.cs, *Test.cs, *.spec.ts, etc.)         ║
║    5. CLI-Param --user-story {SCOPE} (OPTIONAL, BL-011 RF-TS-003)   ║
║       (Keywords aus User Story — fuer Scope-basierte K/B/A            ║
║        Kategorisierung bei testRun statt Blind-K-Fallback)            ║
║       Wenn nicht uebergeben → KANARIENVOGEL-Fallback wie v1.0        ║
║                                                                      ║
║  SCHREIBT (Output) - PFLICHT:                                        ║
║    .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md           ║
║      UPDATE: ## Test-Inventar Sektion wird befuellt                  ║
║    {VAULT}/_manifest.md                                     ║
║      s{N}_testSearch: done                                           ║
║      s{N}_testSearch_at: "{DATUM}"                                   ║
║      s{N}_test_inventar_counts: {K}/{B}/{A} (Kanarien/Boundary/Betr)║
║                                                                      ║
║  HAUPTPRODUKT:                                                       ║
║    Aktualisierter Blueprint mit ## Test-Inventar Sektion             ║
║    (kategorisierte Liste bestehender Tests)                          ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    - Aendert NUR ## Test-Inventar Sektion im Blueprint               ║
║    - Loescht KEINE anderen Blueprint-Sektionen                       ║
║    - Schreibt KEINE Tests, aendert KEINEN Code                       ║
║    - Durchsucht NUR den Code — KEIN Ausfuehren von Tests             ║
║                                                                      ║
║  PIPELINE-POSITION:                                                  ║
║    [cleanCodeArchitect] -> [testSearch] -> [goldDefine]              ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_I_testSearch {NAME} --stufe {N} [--global] [--mode=testRun] [--user-story {SCOPE}]

Parameter:
  NAME:            Feature-Name (PFLICHT)
  --stufe:         Teststufe 1-5 (PFLICHT)
  --global:        Blueprint-Pflicht auf OPTIONAL setzen (KANARIENVOGEL-Modus)
  --mode=testRun:  Alias fuer --global: alle Tests der Stufe, kein Blueprint-Filter
  --user-story:    User-Story-Scope als Keyword-String (OPTIONAL, BL-011 RF-TS-002)
                   Wenn vorhanden: Scope-basierte K/B/A statt Blind-K bei testRun.
                   Wenn nicht vorhanden: KANARIENVOGEL-Fallback wie v1.0.

Beispiele:
  /_I_testSearch DCSRE-881 --stufe 1              -> Unit-Test-Suche (breit, billig)
  /_I_testSearch DCSRE-31 --stufe 5               -> E2E-Test-Suche (selektiv, teuer)
  /_I_testSearch MyFeature --stufe 3 --global     -> KANARIENVOGEL-Modus (kein Blueprint)
  /_I_testSearch MyFeature --stufe 2 --mode=testRun -> Alle Tests S2, KANARIENVOGEL-Fallback
  /_I_testSearch MyFeature --stufe 5 --mode=testRun --user-story "benutzerverwaltung anzeigen filtern IK-Sort"
                                                   -> Scope-basierte K/B/A (BL-011)
```

---

## Die 3 Kategorien

```
KANARIENVOGEL (K):
  Bestehende Tests die GRUEN bleiben MUESSEN.
  Regressions-Schutz. Diese Tests werden MIT-gestartet bei jedem
  TDD-Execute. Wenn ein Kanarienvogel bricht → SOFORT stoppen.

  Kriterien:
    - Test prueft Funktionalitaet die NICHT veraendert wird
    - Test liegt im gleichen Modul/Layer wie die Aenderung
    - Test ist schnell genug um mitlaufen zu koennen

BOUNDARY (B):
  Tests die nahe liegen aber NICHT betroffen sind.
  Safe Zone — koennen durch unsere Aenderungen nicht kaputt gehen.
  Werden NICHT im TDD-Zyklus mitgestartet (sparen Laufzeit).

  Kriterien:
    - Test prueft anderen Code-Pfad
    - Keine Abhaengigkeit zu geaenderten Dateien
    - In einem angrenzenden Modul/Feature

BETROFFEN (A = affected):
  Tests die durch Aenderungen veralten und angepasst werden muessen.
  Diese Tests werden im TDD-Zyklus AKTUALISIERT
  (Signatur-Aenderungen, neue Parameter, geaendertes Verhalten).

  Kriterien:
    - Test prueft Funktionalitaet die veraendert wird
    - Test-Assertions werden durch Implementation ungueltig
    - Test-Setup muss an neue Struktur angepasst werden
```

---

## Ablauf

### Schritt 1: Kontext laden

```
# testRun/Global-Fallback (ADR-FTR-05, erweitert BL-011 RF-TS-003)
IF CLI-Param --mode=testRun ODER CLI-Param --global:
  # testRun: kein Feature-Blueprint vorhanden
  blueprint_scope = null

  # BL-011 RF-TS-003: Scope-basierte Kategorisierung bei --user-story
  IF CLI-Param --user-story VORHANDEN UND NICHT LEER:
    user_story_scope = CLI-Param --user-story   # z.B. "benutzerverwaltung anzeigen filtern IK-Sort"
    user_story_keywords = user_story_scope.split(" ")  # Keyword-Array fuer Substring-Matching
    kategorisierungs_fallback = "SCOPE"  # Scope-basierte K/B/A statt Blind-K
    Logge: "[testRun-Scope] --user-story vorhanden — Scope-Filter aktiv: {user_story_scope}"
  ELSE:
    # RF-TS-004: Backward-Kompatibilitaet — ohne --user-story identisch zu v1.0
    kategorisierungs_fallback = "K"
    user_story_keywords = null
    Logge: "[testRun-Fallback] Kein Blueprint, kein --user-story — KANARIENVOGEL-Modus aktiv (alle Tests = K)"

  # Lies stage_N.md fuer Testtyp (Suche-Strategie bleibt aktiv)
  Lies .claude/meta/implementation/stage_{N}.md:
    - Testtyp (Unit/Modul/Integration/System/E2E)
    - Bestimmt Such-Radius und Kosten-Bewusstsein

ELSE:
  # Normaler Modus: Blueprint PFLICHT (unveraendert)
  1. Lies .claude/analysis/blueprints/{NAME}/S{N}/blueprint.md ## Architektur:
     - Welche Dateien/Layer sind betroffen?
     - Welche Slices gibt es?
     - Extrahiere betroffene Namespaces/Module
     blueprint_scope = gefundene Architektur-Informationen
     IF blueprint_scope == null:
       → FEHLER: "blueprint.md nicht gefunden — ABBRUCH"
     kategorisierungs_fallback = null

  2. Lies .claude/meta/implementation/stage_{N}.md:
     - Testtyp (Unit/Modul/Integration/System/E2E)
     - Bestimmt Such-Radius und Kosten-Bewusstsein
```

### Schritt 2: Test-Dateien suchen

```
Such-Strategie (stufen-adaptiv):

  Stufe 1-2 (Unit/Modul — Tests sind BILLIG):
    Breite Suche. Viele Kanarienvogel einschliessen.
    Radius: Alle Tests im betroffenen Projekt/Modul.
    Glob: tests/**/*Tests.cs, **/*.spec.ts im betroffenen Bereich

  Stufe 3-4 (Integration/System — Tests sind MITTELTEUER):
    Gezielte Suche. Nur direkt relevante Tests.
    Radius: Tests die betroffene Services/Controller direkt testen.

  Stufe 5 (E2E — Tests sind TEUER):
    MINIMALE Kanarienvogel-Menge. Nur die kritischsten.
    Radius: Nur E2E-Tests die den betroffenen User Flow abdecken.
    WICHTIG: Wir koennen NICHT alle E2E-Tests starten.
    Nur Tests die den geaenderten Flow direkt beruehren.

Fuer jede gefundene Test-Datei:
  - Test-Klassen-Name
  - Test-Methoden (Glob der Methodennamen)
  - Welcher Code wird getestet? (SUT = System Under Test)
  - Pfad zur Test-Datei
```

### Schritt 3: Tests kategorisieren

```
# KANARIENVOGEL-Fallback (ADR-FTR-05: --global oder --mode=testRun)
# BL-011 RF-TS-003: Erweitert um SCOPE-Branch bei --user-story
IF kategorisierungs_fallback == "SCOPE":
  # --user-story vorhanden → Scope-basierte K/B/A (ADR-TS-002: Keyword-Matching)
  FUER JEDEN gefundenen Test:
    test_identifiers = Test-Datei-Name + Test-Klassen-Name + SUT-Name (lowercase)
    scope_match = IRGENDEIN keyword IN user_story_keywords TRIFFT AUF test_identifiers
                  (Substring-Match, case-insensitive)

    IF scope_match:
      → Kategorie K (KANARIENVOGEL) — Test liegt im Scope, muss gruen bleiben
    ELSE:
      → Kategorie B (BOUNDARY) — Test liegt AUSSERHALB des Scope, Safe Zone

    # ADR-TS-004: Keine BETROFFEN (A) Kategorie im testRun-Modus
    # (kein Blueprint = keine Info ueber Funktionalitaets-Aenderungen)
    # Im Zweifel: KANARIENVOGEL (bestehende Regel, unveraendert)

  Logge: "[testSearch] Scope-Filter aktiv: {user_story_scope}. K={K_count}, B={B_count}, A=0"

ELIF kategorisierungs_fallback == "K":
  # RF-TS-004: Backward-Kompatibilitaet — kein --user-story, kein Blueprint
  # Alle Tests konservativ als KANARIENVOGEL klassifizieren
  JEDER gefundene Test → Kategorie K (KANARIENVOGEL)
  # Keine BOUNDARY, keine BETROFFEN — alles muss gruen bleiben
  Logge: "[testRun-Fallback] {N} Tests als KANARIENVOGEL klassifiziert (kein Blueprint-Scope)"

ELSE:
  # Normaler 3-Kategorien-Entscheidungsbaum (unveraendert)
  Fuer JEDEN gefundenen Test:

    1. Ist der SUT (System Under Test) in der Liste betroffener Dateien?
       → JA: Weiter zu Frage 2
       → NEIN: Ist der SUT in einem angrenzenden Modul?
         → JA: BOUNDARY
         → NEIN: Ignorieren (zu weit entfernt)

    2. Wird die getestete Funktionalitaet veraendert?
       → JA: BETROFFEN
       → NEIN: KANARIENVOGEL

    Unsicher? → Im Zweifel KANARIENVOGEL (lieber mitleufen als uebersehen)
```

### Schritt 4: Blueprint aktualisieren

Schreibe/ersetze `## Test-Inventar` Sektion im Blueprint:

```markdown
## Test-Inventar

<!-- Erstellt von _I_testSearch, {DATUM} -->
<!-- Stufe {N}: {Such-Strategie-Beschreibung} -->

### Kanarienvogel (K) — Regressions-Schutz, werden MIT-gestartet

| Test-Klasse | Methoden | SUT | Pfad |
|-------------|----------|-----|------|
| {Klasse1}   | {N}      | {Was wird getestet} | {Pfad} |
| {Klasse2}   | {N}      | {Was wird getestet} | {Pfad} |

### Boundary (B) — Safe Zone, werden NICHT mitgestartet

| Test-Klasse | Methoden | SUT | Pfad |
|-------------|----------|-----|------|
| {Klasse1}   | {N}      | {Was wird getestet} | {Pfad} |

### Betroffen (A) — Muessen im TDD-Zyklus angepasst werden

| Test-Klasse | Methoden | Grund der Betroffenheit | Pfad |
|-------------|----------|------------------------|------|
| {Klasse1}   | {N}      | {Warum veraltet}       | {Pfad} |

### Zusammenfassung

- **Kanarienvogel:** {K} Test-Klassen ({K_methods} Methoden)
- **Boundary:** {B} Test-Klassen
- **Betroffen:** {A} Test-Klassen ({A_methods} Methoden)
- **Such-Radius:** {Beschreibung}
- **Kosten-Einschaetzung:** {billig|mittel|teuer}
```

### Schritt 5: Manifest + Exit-Report

```yaml
# Manifest
s{N}_testSearch: done
s{N}_testSearch_at: "{DATUM}"
s{N}_test_inventar_counts: "{K}/{B}/{A}"
s{N}_user_story_provided: "{ja|nein}"   # BL-011 RF-TS-005: --user-story uebergeben?
```

```
# SendMessage an team-lead
_I_testSearch {NAME} --stufe {N}: FINAL
Test-Inventar: {K} Kanarienvogel, {B} Boundary, {A} Betroffen.
Such-Radius: {Beschreibung}
User-Story-Scope: {user_story_scope ?? "nicht uebergeben (Blind-K Fallback)"}
Blueprint aktualisiert.
```

---

## Abgrenzung

- **Schreibt KEINE Tests** (-> TDD-Zyklus)
- **Definiert KEIN Gold** (-> _I_goldDefine)
- **Aendert KEINE Architektur** (-> cleanCodeArchitect)
- **Fuehrt KEINE Tests aus** (-> _TDD_execute)
- **Weist KEINE Patterns zu** (-> _I_patternLibrary)

---

## Pipeline-Position

```
[/_I_cleanCodeArchitect]   Schritt 1: Architektur
          |
          v
[/_I_testSearch]           Schritt 2: Test-Suche  <-- DIESER COMMAND
          |
          v
[/_I_goldDefine]           Schritt 3: Gold-Definition
          |
          v
[/_I_patternLibrary]       Schritt 4: Pattern Library
          |
          v
[/_I_blueprintQG]          Schritt 5: Quality Gate
```

**Prev:** `/_I_cleanCodeArchitect` (erstellt Architektur)
**Next:** `/_I_goldDefine` (definiert Gold aus Test-Inventar + SPEC)
