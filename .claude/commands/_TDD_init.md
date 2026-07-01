---
status: active
version: 1.1.0
created: 2026-04-05
updated: 2026-05-12
type: playbook
op: TDD
phase: Init
chain_position: vor _TDD_orchestrate
model_tier: sonnet   # BL-NEW-51 2026-05-12 — Haiku VERBOTEN im TDD-Zyklus (komplexe Sequenzen: Stage-Setup, Test-Stage-Routing)
forbidden_models: [haiku]   # Crown SCHRITT 1.0 MODEL-VALIDATION blockiert haiku-Spawn
depends_on: []
feeds_into:
  - _TDD_orchestrate
related:
  - _TDD_help
  - _TDD_orchestrate
  - _TDD_red
  - _TDD_green
bl_item: BL-033
bl_new_51: 2026-05-12   # Anti-Haiku im TDD-Zyklus
---

# /_TDD_init - HiL-Wizard fuer Teststufen-Initialisierung

**Status:** v1.0.0
**Typ:** Playbook (HiL-Wizard, kein Agent-Execution-Command)
**Zweck:** Projektspezifische Konfiguration der 5 Teststufen. Erzeugt `stage_{N}.md` Dateien und Backlog-Item.

**Abgrenzung:** Init (Konfiguration) ist getrennt von Runtime (Progression, RED/GREEN). Die 8 bestehenden `_TDD_*` Commands werden NICHT modifiziert (INV-1).

---

## Aufruf

```
/_TDD_init [--target-dir={META}/implementation/] [--project-name=auto]
```

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `--target-dir` | `{META}/implementation/` | Zielverzeichnis fuer stage-Dateien |
| `--project-name` | auto (aus pwd/git) | Projektname fuer stage-Konfiguration |

---

## VERTRAG

```
+===============================================================+
|  COMMAND: /_TDD_init [--target-dir] [--project-name]           |
+===============================================================+
|                                                                |
|  LIEST:                                                        |
|    .claude/meta/implementation/stage_{1-5}.md (Existenz-Check) |
|    {VAULT}/_manifest.md (BACKLOG_STATE)               |
|    {VAULT}/_backlog_index.md (Counter)                |
|    .claude/config/vault-routing.json (BL-Item Vault-Pfad)     |
|                                                                |
|  SCHREIBT:                                                     |
|    .claude/meta/implementation/stage_{1-5}.md (NEU/OVERWRITE)  |
|    DCS-Vault: BL-Item mit Teststufen-Ueberblick               |
|    {VAULT}/_backlog_index.md (APPEND)                 |
|    {VAULT}/_manifest.md (BACKLOG_STATE Update)        |
|                                                                |
|  SCHREIBT NICHT:                                               |
|    Bestehende _TDD_*.md Commands (INV-1)                      |
|    Bestehende stage_{1-5}.md bei Re-Init ohne Bestaetigung    |
|                                                                |
|  INVARIANTEN:                                                  |
|    INV-1: Bestehende _TDD_* Commands NICHT modifiziert        |
|    INV-2: Bestehende stage-Dateien NICHT ueberschrieben       |
|           (ohne HiL-Bestaetigung, NFR-3)                      |
|    INV-3: Stage-Progression-Logik wird NICHT angefasst        |
|    INV-4: Puppet-Master-Prinzip gewahrt                       |
|    INV-5: Konzentrische-Ringe-Prinzip in Metadaten            |
|    INV-6: Jede Stufe eigenstaendig deaktivierbar              |
+===============================================================+
```

---

## Pseudocode

```
FUNCTION _TDD_init(target_dir, project_name):

  # ============================================================
  # SCHRITT 0: NFR-3 Idempotenz-Guard (Re-Init-Erkennung)
  # ============================================================

  bestehende_stages = []
  FUER N IN [1, 2, 3, 4, 5]:
    pfad = target_dir + "/stage_" + N + ".md"
    IF DATEI_EXISTIERT(pfad):
      bestehende_stages.append(N)

  IF bestehende_stages.length > 0:
    Logge: "[TDD-INIT] Bestehende stage-Dateien gefunden: {bestehende_stages}"
    AskUserQuestion:
      header: "TDD Init: Bestehende Konfiguration erkannt"
      question: |
        Folgende stage-Dateien existieren bereits:
        {FUER N IN bestehende_stages: "  - stage_{N}.md"}

        Optionen:
        1. UEBERSCHREIBEN — Neue Konfiguration generieren (bestehende werden ersetzt)
        2. ABBRECHEN — Keine Aenderung
      options: ["UEBERSCHREIBEN", "ABBRECHEN"]

    IF user_choice == "ABBRECHEN":
      Logge: "[TDD-INIT] Abgebrochen durch User (bestehende Dateien beibehalten)"
      RETURN

  # ============================================================
  # SCHRITT 1: Projektname bestimmen
  # ============================================================

  IF project_name == "auto":
    # Aus Git-Remote oder Verzeichnisname ableiten
    git_remote = `git remote get-url origin 2>/dev/null`
    IF git_remote != null:
      project_name = BASENAME(git_remote).replace(".git", "")
    ELSE:
      project_name = BASENAME(pwd)
  Logge: "[TDD-INIT] Projekt: {project_name}"

  # ============================================================
  # SCHRITT 2: HiL-Wizard — 6 Kategorien abfragen (RF-02)
  # AK-02-01: 6 Kategorien sequentiell
  # AK-02-02: Projektspezifische Defaults
  # AK-02-03: Antworten bestimmen Stage-Konfiguration
  # ============================================================

  # Kategorie 1: Sprachen/Runtimes
  AskUserQuestion:
    header: "TDD Init (1/6): Sprachen & Runtimes"
    question: |
      Welche Sprachen/Runtimes werden verwendet?
      Default: C# (.NET)
      Beispiele: C# (.NET), Python, TypeScript, Java, Go, Rust
    options: ["C# (.NET)", "Python", "TypeScript", "Java", "Go", "Andere"]
  sprache = user_choice ?? "C# (.NET)"

  # Kategorie 2: Test-Frameworks
  # Defaults basierend auf Sprache
  test_defaults = {
    "C# (.NET)": "xUnit + FluentAssertions",
    "Python": "pytest",
    "TypeScript": "Jest/Vitest",
    "Java": "JUnit 5",
    "Go": "go test",
  }
  AskUserQuestion:
    header: "TDD Init (2/6): Test-Frameworks"
    question: |
      Welches Test-Framework?
      Default: {test_defaults[sprache] ?? "Bitte angeben"}
    options: [test_defaults[sprache], "Anderes Framework"]
  test_framework = user_choice ?? test_defaults[sprache]

  # Kategorie 3: UI-Arten
  AskUserQuestion:
    header: "TDD Init (3/6): UI-Arten"
    question: |
      Welche UI-Art hat das Projekt?
      Default: API-only (keine UI)
    options: ["API-only", "Web (SPA)", "Web (SSR)", "Mobile", "Desktop", "Keine UI"]
  ui_art = user_choice ?? "API-only"

  # Kategorie 4: Datenbank-Technologien
  AskUserQuestion:
    header: "TDD Init (4/6): Datenbank"
    question: |
      Welche Datenbank-Technologie?
      Default: Keine (oder in-memory)
    options: ["PostgreSQL", "SQL Server", "SQLite", "MongoDB", "Keine", "Andere"]
  datenbank = user_choice ?? "Keine"

  # Kategorie 5: Externe Systeme
  AskUserQuestion:
    header: "TDD Init (5/6): Externe Systeme"
    question: |
      Welche externen Systeme werden integriert?
      Default: Keine
      Beispiele: Identity/Auth (Keycloak, Auth0), Messaging (RabbitMQ, Kafka), Storage (S3, Azure Blob)
    options: ["Keine", "Identity/Auth", "Messaging", "Storage", "Mehrere"]
  externe_systeme = user_choice ?? "Keine"

  # Kategorie 6: Container/Infrastruktur
  AskUserQuestion:
    header: "TDD Init (6/6): Container & Infrastruktur"
    question: |
      Welches Container-/Infra-Setup?
      Default: Docker Compose
    options: ["Docker Compose", "Kubernetes", "Kein Container", "Andere"]
  container_setup = user_choice ?? "Docker Compose"

  Logge: "[TDD-INIT] Technologie-Profil:"
  Logge: "  Sprache: {sprache}"
  Logge: "  Test-Framework: {test_framework}"
  Logge: "  UI: {ui_art}"
  Logge: "  DB: {datenbank}"
  Logge: "  Extern: {externe_systeme}"
  Logge: "  Container: {container_setup}"

  # ============================================================
  # SCHRITT 3: Stufen-Aktivierung (RF-07)
  # AK-07-01: Jede Stufe einzeln deaktivierbar
  # AK-07-02: Mindestens Stufe 1 muss aktiv bleiben
  # AK-07-03: Deaktivierte Stufen = keine stage-Datei
  # ============================================================

  stufen_config = {
    1: {name: "Atomic (Unit)", aktiv: true, deaktivierbar: false},
    2: {name: "Wiring (Integration)", aktiv: true, deaktivierbar: true},
    3: {name: "System (Container)", aktiv: true, deaktivierbar: true},
    4: {name: "Journey (E2E)", aktiv: true, deaktivierbar: true},
    5: {name: "Manual (Explorativ)", aktiv: true, deaktivierbar: true},
  }

  AskUserQuestion:
    header: "TDD Init: Stufen-Konfiguration"
    question: |
      Welche Stufen sollen aktiviert sein? (Stufe 1 ist Pflicht)

      | Stufe | Name | Default | Deaktivierbar? |
      |-------|------|---------|----------------|
      | S1 | Atomic (Unit) | AKTIV | Nein (Pflicht) |
      | S2 | Wiring (Integration) | AKTIV | Ja |
      | S3 | System (Container) | AKTIV | Ja |
      | S4 | Journey (E2E) | AKTIV | Ja |
      | S5 | Manual (Explorativ) | AKTIV | Ja |

      Welche Stufen deaktivieren? (Komma-separiert, z.B. "3,5" oder "keine")
    options: ["keine", "5", "3,5", "4,5", "Andere"]
  deaktivieren = user_choice ?? "keine"

  IF deaktivieren != "keine":
    deaktivierte = deaktivieren.split(",").map(s => int(s.strip()))
    FUER stufe_nr IN deaktivierte:
      IF stufe_nr == 1:
        Logge: "[TDD-INIT] Stufe 1 kann nicht deaktiviert werden (INV-6, AK-07-02)"
        CONTINUE
      IF stufe_nr IN [2, 3, 4, 5]:
        stufen_config[stufe_nr].aktiv = false
        Logge: "[TDD-INIT] Stufe {stufe_nr} deaktiviert"

  aktive_stufen = [N FOR N IN [1,2,3,4,5] IF stufen_config[N].aktiv == true]
  Logge: "[TDD-INIT] Aktive Stufen: {aktive_stufen}"

  # ============================================================
  # SCHRITT 4: Stage-Dateien generieren (RF-03)
  # AK-03-01: 11 Pflichtfelder
  # AK-03-02: exit_criteria als strukturierte Liste
  # AK-03-03: Stufen-spezifische Erweiterungsfelder
  # AK-03-04: Blueprint-Perspektiven feste Zuordnung
  # AK-03-05: Konzentrische-Ringe-Prinzip
  # ============================================================

  # Mapping Sprache → testbefehl/testpfad
  test_config = berechne_test_config(sprache, test_framework, datenbank, container_setup)
  # test_config = {
  #   testbefehl: {S1: "dotnet test --filter Category=Unit", S2: "...", ...},
  #   test_projekte: {S1: ["*.UnitTests"], S2: ["*.IntegrationTests"], ...},
  #   testpfad: {S1: "Tests/Unit/", S2: "Tests/Integration/", ...},
  # }

  perspektiven = {1: "Laserpointer", 2: "Taschenlampe", 3: "Scheinwerfer", 4: "Flutlicht", 5: "Vogelperspektive"}
  testtypen = {1: "unit", 2: "integration", 3: "system", 4: "e2e", 5: "manual"}
  fokus = {
    1: "Isolierte Inseln — einzelne Schichten, Funktionen, Klassen",
    2: "Verdrahtung — Zusammenspiel zwischen 2-3 Komponenten",
    3: "Gesamtsystem — alle Schichten mit echter Infrastruktur",
    4: "User Journey — End-to-End Geschaeftsprozesse",
    5: "Exploratives/Manuelles Testing — Entdeckung unerwarteter Fehler",
  }
  namen = {1: "Atomic", 2: "Wiring", 3: "System", 4: "Journey", 5: "Manual"}

  mkdir -p target_dir

  FUER stufe_nr IN aktive_stufen:
    pfad = target_dir + "/stage_" + stufe_nr + ".md"

    # 11 Pflichtfelder (AK-03-01)
    frontmatter = {
      stufe: stufe_nr,
      name: namen[stufe_nr],
      fokus: fokus[stufe_nr],
      testbefehl: test_config.testbefehl[stufe_nr],
      test_projekte: test_config.test_projekte[stufe_nr],
      testpfad: test_config.testpfad[stufe_nr],
      fanout: (stufe_nr <= 2) ? "hoch" : (stufe_nr == 3) ? "mittel" : "niedrig",
      mocks_erlaubt: (stufe_nr == 1) ? "ja" : (stufe_nr == 2) ? "teilweise" : "nein",
      blueprint_perspektive: perspektiven[stufe_nr],
      testtyp: testtypen[stufe_nr],
      exit_criteria: [
        "blueprint_qg: pass",
        "stufen_tests_gruen: ja",
        "fan_in_merge: pass",
      ],
    }

    # Stufen-spezifische Erweiterungsfelder (AK-03-03)
    IF stufe_nr == 1:
      frontmatter.kanarienvogel_zone = "Benachbarte Klassen, Unit-Tests uebergeordneter Schicht"
      frontmatter.kanarienvogel_bootstrap = "verify_guard_tests | spec_systemgrenze"
    frontmatter.ressourcen_constraints = {
      parallelitaet_max: (stufe_nr <= 2) ? 8 : (stufe_nr == 3) ? 4 : 2,
      timeout_per_test_min: (stufe_nr <= 2) ? 1 : (stufe_nr == 3) ? 5 : 15,
    }
    IF stufe_nr >= 3 AND container_setup != "Kein Container":
      frontmatter.max_container_parallel = (stufe_nr == 3) ? 3 : 2
      frontmatter.container_isolation = true
      frontmatter.infrastruktur = container_setup

    # Stage-Datei schreiben
    SCHREIBE pfad:
      ---
      {frontmatter als YAML}
      ---

      # Stufe {stufe_nr}: {namen[stufe_nr]}

      ## Fokus
      {fokus[stufe_nr]}

      ## Blueprint-Perspektive: {perspektiven[stufe_nr]}
      Konzentrische Ringe: Stufe {stufe_nr} erweitert den Testradius
      von Stufe {stufe_nr - 1} (INV-5).

      ## Technologie-Profil
      - Sprache: {sprache}
      - Test-Framework: {test_framework}
      - UI: {ui_art}
      - DB: {datenbank}
      - Container: {container_setup}

    Logge: "[TDD-INIT] stage_{stufe_nr}.md generiert ({namen[stufe_nr]}, {perspektiven[stufe_nr]})"

  Logge: "[TDD-INIT] {aktive_stufen.length} stage-Dateien generiert"

  # ============================================================
  # SCHRITT 5: Guard G-TDD-STAGES-READY definieren (RF-04)
  # AK-04-01: Existenz-Pruefung
  # AK-04-02: Pflichtfeld-Validierung
  # AK-04-03: Blocking bei Fehlschlag
  # ============================================================

  # Guard wird als INLINE-BLOCK dokumentiert (nicht als separate Datei)
  # _TDD_orchestrate soll diesen Guard VOR dem Loop pruefen
  guard_definition = """
  ## Guard: G-TDD-STAGES-READY

  **Zweck:** Voraussetzungspruefung VOR TDD-Loop-Start.
  **Position:** Erste Pruefung in /_TDD_orchestrate, VOR Stufen-Iteration.

  ### Pruefung
  1. FUER JEDE aktive Stufe (aus _session_params.md oder Default 1-5):
     - Pruefe: stage_{N}.md existiert in {target_dir}
     - Pruefe: 11 Pflichtfelder vorhanden und nicht leer
       (stufe, name, fokus, testbefehl, test_projekte, testpfad,
        fanout, mocks_erlaubt, blueprint_perspektive, testtyp, exit_criteria)
  2. Bei Fehlschlag:
     - TDD-Loop wird NICHT gestartet (Blocking)
     - Fehlermeldung mit konkreten Maengeln
     - Verweis: "Ausfuehren: /_TDD_init"
  3. Bei Erfolg:
     - Logge: "G-TDD-STAGES-READY: PASS ({N} aktive Stufen validiert)"
  """

  # ============================================================
  # SCHRITT 6: testing=true Default (RF-05)
  # AK-05-01: Default dokumentiert
  # AK-05-02: Persistierungsort (session_params)
  # AK-05-03: Opt-out-Mechanismus
  # ============================================================

  # testing=true wird als Empfehlung im Playbook dokumentiert
  # Persistierungsort: _session_params.md (via /_param tdd=true)
  Logge: "[TDD-INIT] testing=true: Default-Empfehlung."
  Logge: "[TDD-INIT] Setze via: /_param tdd=true (session-weit)"
  Logge: "[TDD-INIT] Opt-out via: /_param tdd=false (mit Begruendung)"

  # ============================================================
  # SCHRITT 7: Backlog-Item erzeugen (RF-06)
  # AK-06-01: Teststufen-Ueberblick
  # AK-06-02: Bestehendes BL-Format
  # ============================================================

  bl_teststufen_text = """
  Teststufen-Initialisierung fuer Projekt '{project_name}'.
  Aktive Stufen: {aktive_stufen}
  Technologien: {sprache}, {test_framework}, {ui_art}, {datenbank}
  Container: {container_setup}
  Externe Systeme: {externe_systeme}
  Generierte Dateien: {aktive_stufen.length} stage-Dateien in {target_dir}
  """

  # BL-Item via /_backlog erstellen (INV-4: Puppet-Master)
  Logge: "[TDD-INIT] Backlog-Item wird erstellt (Teststufen-Ueberblick)"
  # Hinweis: /_backlog wird extern aufgerufen, nicht inline
  # Der Wizard gibt dem User die Zusammenfassung

  # ============================================================
  # SCHRITT 8: Zusammenfassung und Abschluss
  # ============================================================

  Logge: "=== TDD INIT ABGESCHLOSSEN ==="
  Logge: ""
  Logge: "Projekt:           {project_name}"
  Logge: "Aktive Stufen:     {aktive_stufen} ({aktive_stufen.length}/5)"
  Logge: "Deaktivierte:      {[N FOR N IN [1..5] IF N NOT IN aktive_stufen]}"
  Logge: "Stage-Dateien:     {target_dir}/stage_{1-5}.md"
  Logge: "Guard:             G-TDD-STAGES-READY (in stage-Dateien definiert)"
  Logge: "testing=true:      Empfohlen (/_param tdd=true)"
  Logge: ""
  Logge: "Naechste Schritte:"
  Logge: "  1. /_param tdd=true                    (TDD als Default)"
  Logge: "  2. Stage-Dateien bei Bedarf anpassen    (testbefehl, testpfad)"
  Logge: "  3. /_TDD_orchestrate {NAME}             (TDD-Loop starten)"

  RETURN


# ============================================================
# Hilfsfunktion: Test-Konfiguration aus Technologie-Profil
# ============================================================
FUNCTION berechne_test_config(sprache, test_framework, datenbank, container_setup):

  config = {testbefehl: {}, test_projekte: {}, testpfad: {}}

  IF sprache == "C# (.NET)":
    config.testbefehl[1] = "dotnet test --filter Category=Unit"
    config.testbefehl[2] = "dotnet test --filter Category=Integration"
    config.testbefehl[3] = "dotnet test --filter Category=System"
    config.testbefehl[4] = "dotnet test --filter Category=E2E"
    config.testbefehl[5] = "# Manuelles Testing (Checkliste)"
    config.test_projekte[1] = ["*.UnitTests"]
    config.test_projekte[2] = ["*.IntegrationTests"]
    config.test_projekte[3] = ["*.SystemTests"]
    config.test_projekte[4] = ["*.E2ETests"]
    config.test_projekte[5] = []
    config.testpfad[1] = "Tests/Unit/"
    config.testpfad[2] = "Tests/Integration/"
    config.testpfad[3] = "Tests/System/"
    config.testpfad[4] = "Tests/E2E/"
    config.testpfad[5] = "Tests/Manual/"

  ELIF sprache == "Python":
    config.testbefehl[1] = "pytest tests/unit/ -v"
    config.testbefehl[2] = "pytest tests/integration/ -v"
    config.testbefehl[3] = "pytest tests/system/ -v"
    config.testbefehl[4] = "pytest tests/e2e/ -v"
    config.testbefehl[5] = "# Manuelles Testing (Checkliste)"
    config.test_projekte[1] = ["tests/unit/"]
    config.test_projekte[2] = ["tests/integration/"]
    config.test_projekte[3] = ["tests/system/"]
    config.test_projekte[4] = ["tests/e2e/"]
    config.test_projekte[5] = []
    config.testpfad[1] = "tests/unit/"
    config.testpfad[2] = "tests/integration/"
    config.testpfad[3] = "tests/system/"
    config.testpfad[4] = "tests/e2e/"
    config.testpfad[5] = "tests/manual/"

  ELIF sprache == "TypeScript":
    config.testbefehl[1] = "npx vitest run --reporter=verbose tests/unit/"
    config.testbefehl[2] = "npx vitest run --reporter=verbose tests/integration/"
    config.testbefehl[3] = "npx vitest run --reporter=verbose tests/system/"
    config.testbefehl[4] = "npx playwright test"
    config.testbefehl[5] = "# Manuelles Testing (Checkliste)"
    config.test_projekte[1] = ["tests/unit/"]
    config.test_projekte[2] = ["tests/integration/"]
    config.test_projekte[3] = ["tests/system/"]
    config.test_projekte[4] = ["tests/e2e/"]
    config.test_projekte[5] = []
    config.testpfad[1] = "tests/unit/"
    config.testpfad[2] = "tests/integration/"
    config.testpfad[3] = "tests/system/"
    config.testpfad[4] = "tests/e2e/"
    config.testpfad[5] = "tests/manual/"

  ELSE:
    # Generische Defaults fuer andere Sprachen
    FUER N IN [1..5]:
      config.testbefehl[N] = "# TODO: Testbefehl fuer {sprache} konfigurieren"
      config.test_projekte[N] = []
      config.testpfad[N] = "tests/stage_{N}/"

  # Container-spezifische Anpassungen (Stage 3+)
  IF container_setup != "Kein Container":
    IF sprache == "C# (.NET)":
      config.testbefehl[3] = "dotnet test --filter Category=System -- TestRunParameters.Parameter(name=\"UseContainer\", value=\"true\")"
    ELIF sprache == "Python":
      config.testbefehl[3] = "pytest tests/system/ -v --docker"
    ELIF sprache == "TypeScript":
      config.testbefehl[3] = "npx vitest run tests/system/ --config vitest.system.config.ts"

  # DB-spezifische Anpassungen (Stage 2+)
  IF datenbank != "Keine":
    # Integrationstests brauchen DB-Konnektivitaet
    Logge: "[TDD-INIT] DB={datenbank}: Stage 2+ Tests brauchen DB-Connection"

  RETURN config
```

---

## Guard-Definition: G-TDD-STAGES-READY

Dieser Guard wird von `/_TDD_orchestrate` VOR dem Stufen-Loop geprueft.

**TESTBARER HELPER (BL-329 AK-3):** Das Gate ist als reiner, testbarer Python-Helper
materialisiert — `.claude/scripts/tdd_stages_ready.py` (Tests:
`test_tdd_stages_ready.py`). Aufruf:

```bash
py -3 .claude/scripts/tdd_stages_ready.py --target-dir .claude/meta/implementation --stages 1,2,3,4,5,6
# exit 0 = PASS, exit 2 = BLOCK (mit korrektivem Recovery-Hint pro Stage)
```

Der untenstehende Pseudocode ist die Referenz-Semantik; die Wahrheit ist der Helper.

```
FUNCTION G_TDD_STAGES_READY(target_dir, aktive_stufen):
  # AK-04-01: Existenz-Pruefung
  fehlende = []
  FUER stufe_nr IN aktive_stufen:
    pfad = target_dir + "/stage_" + stufe_nr + ".md"
    IF NOT DATEI_EXISTIERT(pfad):
      fehlende.append(stufe_nr)

  IF fehlende.length > 0:
    # AK-04-03: Blocking
    Logge: "G-TDD-STAGES-READY: FAIL — Fehlende stage-Dateien: {fehlende}"
    Logge: "  → Ausfuehren: /_TDD_init"
    RETURN FAIL

  # AK-04-02: Pflichtfeld-Validierung — 11 BASIS-Pflichtfelder.
  # Semantik (BL-329 AK-3 Behavior-Catch): "fehlt" = Key NICHT vorhanden ODER null.
  # Ein EXPLIZIT gesetzter Leer-Wert (test_projekte: [] / testpfad: "") ist eine bewusste
  # Autoren-Wahl und gilt als VORHANDEN (reale stage_1 BL-111 / stage_6 PS-Script). Das
  # Gate guardet UNKONFIGURIERTE Felder, NICHT intentional-blanke. Kein Bruch fuer Bestand.
  PFLICHTFELDER = ["stufe", "name", "fokus", "testbefehl", "test_projekte",
                   "testpfad", "fanout", "mocks_erlaubt", "blueprint_perspektive",
                   "testtyp", "exit_criteria"]
  ungueltige = []
  FUER stufe_nr IN aktive_stufen:
    pfad = target_dir + "/stage_" + stufe_nr + ".md"
    frontmatter = LIES_FRONTMATTER(pfad)
    FUER feld IN PFLICHTFELDER:
      IF feld NOT IN frontmatter OR frontmatter[feld] == null:
        ungueltige.append({stufe: stufe_nr, feld: feld})

    # AK-3 (BL-329): Infra-Stages tragen 3 ZUSAETZLICHE Pflicht-Sektionen (11 -> 14).
    # NUR fuer infrastruktur != "none" (Container/DB/WebHost-Spinup). none-Stages
    # (oder Stages ohne infrastruktur-Key, Abwaertskompat) bleiben unveraendert.
    IF frontmatter.infrastruktur != null AND frontmatter.infrastruktur != "none":
      INFRA_SEKTIONEN = ["setup", "teardown", "health_check"]
      FUER sektion IN INFRA_SEKTIONEN:
        IF sektion NOT IN frontmatter OR frontmatter[sektion] == null:
          ungueltige.append({stufe: stufe_nr, feld: sektion,
            recovery_hint: "stage_{stufe_nr}.md {sektion}-Sektion ergaenzen: "
                           "setup.commands + health_check + teardown.commands "
                           "(Infra-Stage braucht alle 3 Sektionen, BL-329 AK-3). "
                           "Vorlage: stage_3.md / stage_6.md."})

  IF ungueltige.length > 0:
    Logge: "G-TDD-STAGES-READY: BLOCK — Ungueltige Pflichtfelder:"
    FUER item IN ungueltige:
      Logge: "  stage_{item.stufe}.md: '{item.feld}' fehlt oder null"
      IF item.recovery_hint: Logge: "    → {item.recovery_hint}"   # korrektiv, nicht nur blocken
    Logge: "  → Ausfuehren: /_TDD_init (oder Gate-Helper tdd_stages_ready.py)"
    RETURN FAIL

  Logge: "G-TDD-STAGES-READY: PASS ({aktive_stufen.length} aktive Stufen validiert)"
  RETURN PASS
```

---

## Abgrenzung zu bestehenden Commands

| Command | Zweck | Von BL-033 betroffen? |
|---------|-------|----------------------|
| `_TDD_orchestrate` | Stufen-Loop Runtime | NEIN (INV-1) |
| `_TDD_red` | Failing Test schreiben | NEIN (INV-1) |
| `_TDD_green` | Minimaler Code | NEIN (INV-1) |
| `_TDD_execute` | Test-Suite ausfuehren | NEIN (INV-1) |
| `_TDD_check` | GOLD erreicht? | NEIN (INV-1) |
| `_TDD_help` | Hilfe | NEIN (INV-1) |
| `_TDD_refactorTests` | Tests spezifischer | NEIN (INV-1) |
| `_TDD_refactorCode` | Code generischer | NEIN (INV-1) |
| **`_TDD_init`** | **Initialisierung** | **NEU (dieses Playbook)** |
