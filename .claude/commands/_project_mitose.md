# /_project_mitose - Projekt-DNA in neues Projekt kopieren (biologische Zellteilung)

```yaml
status: active
version: 1.0.0
created: 2026-04-06
op: ProjectMitose
phase: Bootstrap
type: building-block
chain_position: standalone
team_based: false
```

---

```
+===============================================================+
|  COMMAND: /_project_mitose {NAME} [--dcs-pfad PFAD]           |
|                            [--source QUELL-PFAD]              |
+===============================================================+
|                                                               |
|  ACTOR: DU (ausfuehrende Claude-Instanz, KEIN Team)          |
|                                                               |
|  ZWECK: Neues Projekt mit DNA aus Quellprojekt bootstrappen.  |
|         Biologische Mitose: Tochterzelle erhaelt vollstaendige|
|         DNA (Commands, Agents, Meta, Patterns, Scripts),      |
|         aber eigene Daten (Manifest, Models, States leer).    |
|                                                               |
|  LIEST (aus Quellprojekt — Read-Only, INV-1):                |
|    .claude/commands/     (alle Commands — DNA)                |
|    .claude/agents/       (Agent-Definitionen — DNA)           |
|    .claude/meta/         (Meta-Konventionen — DNA)            |
|    .claude/patterns/     (Pattern-Library — DNA)              |
|    .claude/scripts/      (Bash/PS1 Scripts — DNA)             |
|    .claude/tools/        (Tools — DNA, falls vorhanden)       |
|    .claude/reference/    (Referenz-Dokumentation — DNA)       |
|    CLAUDE.md             (Basis-Regeln — angepasste DNA)      |
|                                                               |
|  Parameter:                                                   |
|    {NAME}          PFLICHT   Name des neuen Projekts          |
|    --dcs-pfad      Optional  DCS-Zielpfad im Obsidian-Vault   |
|                              Default: ~/Documents/DCS/{NAME}  |
|    --source        Optional  Quellprojekt-Verzeichnis         |
|                              Default: aktuelles Verzeichnis   |
|                                                               |
|  SCHREIBT (ins neue Projekt {NAME}/):                         |
|    .claude/commands/     (identische Kopie)                   |
|    .claude/agents/       (identische Kopie)                   |
|    .claude/meta/         (identische Kopie)                   |
|    .claude/patterns/     (identische Kopie)                   |
|    .claude/scripts/      (identische Kopie)                   |
|    .claude/tools/        (identische Kopie, falls vorhanden)  |
|    .claude/reference/    (identische Kopie, falls vorhanden)  |
|    .claude/config/vault-routing.json  (NEU generiert)         |
|    .claude/config/project.yaml        (NEU generiert)         |
|    {VAULT}/_manifest.md     (LEER initialisiert)     |
|    {VAULT}/_backlog_index.md (LEER initialisiert)    |
|    {VAULT}/_parking-lot.md  (LEER initialisiert)     |
|    CLAUDE.md             (bereinigt — keine Quellprojekt-Refs)|
|    .claude/INSTRUCTION.md (generiert — neues Projekt)         |
|    .git/                 (git init — eigene Historie, ADR-02) |
|                                                               |
|  SCHREIBT NICHT (INV-1):                                      |
|    Quellprojekt bleibt UNVERAENDERT (Read-Only-Invariante)    |
|                                                               |
|  ABGRENZUNG:                                                  |
|    /_init:           Leeres Projekt (Tabula Rasa), ruft       |
|                      initialize.sh auf. Kein Quellprojekt-    |
|                      Cleanup, kein vault-routing NEU.         |
|    /_I_mitose:       Git Worktrees INNERHALB eines Features   |
|                      (gleicher Repo, parallele Slices).       |
|    /_project_mitose: DNA-Kopie ZWISCHEN Projekten (Meta-Level)|
|                      Eigenes Repo, eigene Historie, eigener   |
|                      DCS-Pfad. Biologische Zellteilung.       |
|                                                               |
+===============================================================+
```

---

## Schritt 1: VALIDIERUNG

```
INPUTS ERMITTELN:
  NAME       = {NAME} (Pflichtparameter)
  SOURCE     = --source ODER aktuelles Verzeichnis (pwd)
  DCS_PFAD   = --dcs-pfad ODER ~/Documents/DCS/{NAME}
  DATUM      = aktuelles Datum (YYYY-MM-DD)
  QUELLPROJEKT_NAME = basename(SOURCE)

GUARDS:

  a) NAME vorhanden?
     NEIN → "FEHLER: NAME ist Pflichtparameter."
            "Aufruf: /_project_mitose {NAME} [--dcs-pfad PFAD] [--source QUELL-PFAD]"
            → Abbruch

  b) SOURCE/.claude/commands/ existiert?
     NEIN → "FEHLER: Quellprojekt hat keine .claude/commands/: {SOURCE}"
            "Ist {SOURCE} ein OmniCommand-Projekt?"
            → Abbruch

  c) Zielverzeichnis {NAME}/ existiert bereits?
     JA  → "FEHLER: Verzeichnis {NAME}/ existiert bereits. Kein Overwrite."
           "Falls beabsichtigt: Verzeichnis zuerst manuell entfernen."
           → Abbruch

AUSGABE:
  "══════════════════════════════════════════════════════════════
   /_project_mitose: Starte Projekt-DNA-Kopie
   ══════════════════════════════════════════════════════════════
   Quelle:  {SOURCE} ({QUELLPROJEKT_NAME})
   Ziel:    {NAME}/ (wird erstellt)
   DCS:     {DCS_PFAD}
   ══════════════════════════════════════════════════════════════"
```

---

## Schritt 2: DNA-KOPIE

```
VERZEICHNIS ERSTELLEN:
  mkdir -p {NAME}/.claude/

DNA-VERZEICHNISSE KOPIEREN (Quellprojekt → neues Projekt):
  cp -r {SOURCE}/.claude/commands/   → {NAME}/.claude/commands/
  cp -r {SOURCE}/.claude/agents/     → {NAME}/.claude/agents/
  cp -r {SOURCE}/.claude/meta/       → {NAME}/.claude/meta/
  cp -r {SOURCE}/.claude/patterns/   → {NAME}/.claude/patterns/
  cp -r {SOURCE}/.claude/scripts/    → {NAME}/.claude/scripts/
  cp -r {SOURCE}/.claude/tools/      → {NAME}/.claude/tools/       (falls vorhanden)
  cp -r {SOURCE}/.claude/reference/  → {NAME}/.claude/reference/   (falls vorhanden)

DNA-EINZELDATEIEN KOPIEREN:
  cp {SOURCE}/.claude/settings.local.json → {NAME}/.claude/  (falls vorhanden)
  cp {SOURCE}/.claude/session-params.md   → {NAME}/.claude/  (falls vorhanden)

NICHT KOPIEREN (projekt-spezifisch — INV-3, AK-03-04):
  config/          → wird in Schritt 3 NEU generiert
  models/*.md      → Quellprojekt-spezifisch
  specs/*.md       → Quellprojekt-spezifisch
  crumbs/*.md      → Quellprojekt-spezifisch
  analysis/*       → Quellprojekt-spezifisch
  pileOfMud/*.md   → Quellprojekt-spezifisch
  wissen/*.md      → Quellprojekt-spezifisch
  Task.md          → Quellprojekt-spezifisch
  INSTRUCTION.md   → wird in Schritt 3 NEU generiert
  CLAUDE.md        → wird in Schritt 3 BEREINIGT kopiert

ZAEHLER MERKEN:
  DNA_COMMANDS  = Anzahl Dateien in {NAME}/.claude/commands/
  DNA_AGENTS   = Anzahl Dateien in {NAME}/.claude/agents/
  DNA_META     = Anzahl Dateien in {NAME}/.claude/meta/
  DNA_PATTERNS = Anzahl Dateien in {NAME}/.claude/patterns/
  DNA_SCRIPTS  = Anzahl Dateien in {NAME}/.claude/scripts/
```

---

## Schritt 3: DATEN-INIT + SPEZIAL

```
LEERE STATE-VERZEICHNISSE ANLEGEN:
  mkdir -p {NAME}/.claude/models/
  mkdir -p {NAME}/.claude/specs/
  mkdir -p {NAME}/.claude/crumbs/
  mkdir -p {NAME}/.claude/pileOfMud/
  mkdir -p {NAME}/.claude/wissen/
  mkdir -p {NAME}/.claude/output/
  mkdir -p {NAME}/.claude/temp/
  mkdir -p {NAME}/.claude/presentation/
  mkdir -p {NAME}/.claude/audit/
  mkdir -p {NAME}/.claude/analysis/synthese/
  mkdir -p {NAME}/.claude/analysis/exploration/
  mkdir -p {NAME}/.claude/analysis/drafts/
  mkdir -p {NAME}/.claude/analysis/blueprints/
  mkdir -p {NAME}/.claude/analysis/plans/
  mkdir -p {NAME}/.claude/analysis/findings/
  mkdir -p {NAME}/.claude/analysis/archive/
  mkdir -p {NAME}/.claude/analysis/integration/
  mkdir -p {NAME}/.claude/analysis/evidence/
  mkdir -p {NAME}/.claude/config/

───────────────────────────────────────────────────
CLAUDE.md BEREINIGT KOPIEREN (AK-02-05):
───────────────────────────────────────────────────
  Kopiere {SOURCE}/CLAUDE.md → {NAME}/CLAUDE.md
  Bereinige im Ziel:
    - STATUS-Zeilen ("**STATUS:...") → "**STATUS: Neues Projekt. Lies .claude/INSTRUCTION.md.**"
    - Feature-Aufzaehlungen ("Features DONE:", Feature-Namen) → entfernen
    - Parking-Lot-Referenzen ("Parking-Lot Items") → entfernen
    - Behalte: INSTRUCTION.md-Verweis, BDF-Regeln (Feature-Branch, kein Push auf main)

───────────────────────────────────────────────────
_MANIFEST.MD NEU GENERIEREN (AK-03-01):
───────────────────────────────────────────────────
  Erstelle {NAME}/{VAULT}/_manifest.md:
  ---
  # Manifest
  **Projekt:** {NAME}
  **Erstellt:** {DATUM}
  **Phase:** READY
  ---
  ## Status
  | Feld | Wert |
  |------|------|
  | NAME | (kein aktives Feature) |
  | PHASE | READY |
  | COVERAGE | 0% |
  | SRS | 0.0 |
  | STAGNATION | 0.0 |
  | ZYKLEN | 0 |
  | MODUS | - |
  | NAECHSTER_SCHRITT | /_A_orchestrate oder /_SC_orchestrate |
  ---
  ## History
  (keine bisherigen Features)

  Invariante: KEIN W_FETCH_STATUS, KEIN A_PIPELINE_STATE (INV-3)

───────────────────────────────────────────────────
_BACKLOG_INDEX.MD LEER INITIALISIEREN (AK-03-02):
───────────────────────────────────────────────────
  Erstelle {NAME}/{VAULT}/_backlog_index.md:
  ---
  type: backlog-index
  version: 1.0
  created: {DATUM}
  backlog_counter: 0
  backlog_last_update: {DATUM}
  backlog_last_id: (noch kein Item)
  ---
  # Backlog Index
  ## Items
  | BL-ID | Title | Status | Vault-Pfad | Created | Updated | Spec-Link | Reifegrad |
  |-------|-------|--------|------------|---------|---------|-----------|-----------|
  (keine Items)

───────────────────────────────────────────────────
_PARKING-LOT.MD LEER INITIALISIEREN:
───────────────────────────────────────────────────
  Erstelle {NAME}/{VAULT}/_parking-lot.md:
  # Parking Lot: Incidental Findings
  **Letzte Aktualisierung:** (initialisiert)
  ## Legende
  - [ ] Offen
  - [x] In _taskDefinition aufgenommen
  - [~] Verworfen
  ---
  (keine Eintraege)

───────────────────────────────────────────────────
INSTRUCTION.MD NEU GENERIEREN (AK-03-03):
───────────────────────────────────────────────────
  Erstelle {NAME}/.claude/INSTRUCTION.md:
  # STATUS: Neues Projekt — bereit fuer erste Analyse
  **Datum:** {DATUM}
  **origin_project:** {SOURCE} (via /_project_mitose, W12)
  **Branch:** noch nicht erstellt (git init ausgefuehrt)
  ---
  ## Naechster Schritt
  /_A_orchestrate {NAME}
  ---
  ## Projekt-Kontext
  Dieses Projekt wurde durch /_project_mitose {NAME} aus {SOURCE} erstellt.
  DNA-Artefakte (commands/, agents/, meta/, patterns/) wurden kopiert.
  Daten-Artefakte (models/, specs/, crumbs/) sind leer — bereit fuer eigene Analyse.

───────────────────────────────────────────────────
CONFIG/PROJECT.YAML NEU GENERIEREN:
───────────────────────────────────────────────────
  Erstelle {NAME}/.claude/config/project.yaml:
  name: {NAME}
  description: ""
  rag:
    collections: []
    auto_ingest: false

───────────────────────────────────────────────────
VAULT-ROUTING.JSON NEU GENERIEREN (AK-04-01, AK-04-02):
───────────────────────────────────────────────────
  Erstelle {NAME}/.claude/config/vault-routing.json:
  {
    "$schema": "vault-routing-v3",
    "version": "3.0",
    "description": "Vault-Routing fuer {NAME}. Generiert via /_project_mitose.",
    "env_var": "OBSIDIAN_VAULT_PATH",
    "detection": {
      "method": "path-pattern",
      "rules": [
        {
          "pattern": "{NAME}",
          "vault": "DCS",
          "priority": 1,
          "rag_collections": ["global_knowledge"],
          "backlog": {
            "enabled": true,
            "subfolder": "{NAME}/Backlog",
            "dateiname_convention": "BL-{NNN:03d}-{slug}.md",
            "id_format": "BL-{NNN}",
            "id_padding": 3,
            "slug_transform": "kebab-case",
            "index_file": "{VAULT}/_backlog_index.md",
            "INV-6": "Vault-Pfad darf nach Erstellung NICHT geaendert werden."
          },
          "description": "{NAME}-Projekt → DCS Vault (global_knowledge)"
        },
        {
          "pattern": "*",
          "vault": "DCS",
          "priority": 999,
          "rag_collections": ["global_knowledge"],
          "warning": "Kein spezifisches Pattern",
          "description": "Default Fallback"
        }
      ]
    },
    "vaults": {
      "DCS": {
        "linux_path": "{DCS_PFAD}",
        "env_var": "OBSIDIAN_VAULT_PATH",
        "projects": ["{NAME}"],
        "global_rag": "global_knowledge"
      }
    },
    "notes": [
      "Generiert durch /_project_mitose {NAME}",
      "Datum: {DATUM}",
      "Quellprojekt: {SOURCE}"
    ]
  }

  KEINE Quellprojekt-Pfade (AK-04-02, INV-4)
  KEINE local_knowledge_* Collections vom Quellprojekt

  Falls DCS-Verzeichnis {DCS_PFAD} nicht existiert (AK-04-03):
    "HINWEIS: Bitte erstelle {DCS_PFAD}/{NAME}/Backlog/ im Obsidian-Vault."
    → KEIN Fehler, KEIN Abbruch — nur Hinweis in Ausgabe

───────────────────────────────────────────────────
GIT INIT (ADR-02, INV-2):
───────────────────────────────────────────────────
  cd {NAME}/ && git init
  → Eigene Git-Historie, vollstaendige Isolation
  → KEIN automatischer git add oder git commit
```

---

## Schritt 4: VERIFIZIERUNG

```
a) DNA komplett?
   ls {NAME}/.claude/commands/ | wc -l == ls {SOURCE}/.claude/commands/ | wc -l
   ls {NAME}/.claude/agents/   | wc -l == ls {SOURCE}/.claude/agents/   | wc -l
   (analog fuer meta/, patterns/, scripts/)
   Falls Abweichung → WARNUNG (kein Abbruch)

b) Daten leer?
   _manifest.md hat KEIN "W_FETCH_STATUS", KEIN "A_PIPELINE_STATE"
   _backlog_index.md hat "backlog_counter: 0"

c) Quellprojekt unveraendert? (INV-1, TC-03)
   git -C {SOURCE} diff → 0 neue Aenderungen durch Mitose
   Falls Aenderungen → "FEHLER: Quellprojekt wurde veraendert! INV-1 verletzt."

d) Source-Leak-Check (TC-02):
   ALLOWLIST = ["INSTRUCTION.md", "vault-routing.json"]
   Grep "{QUELLPROJEKT_NAME}" in {NAME}/.claude/analysis/ → 0 Treffer
   Grep "{QUELLPROJEKT_NAME}" in {NAME}/CLAUDE.md → 0 Treffer
   Falls Treffer ausserhalb Allowlist → WARNUNG (kein Abbruch)
```

---

## Ausgabe (nach erfolgreicher Verifizierung)

```
"═══════════════════════════════════════════════════════
 /_project_mitose: Neues Projekt erstellt!
 ═══════════════════════════════════════════════════════

 Projekt: {NAME}/
 Quelle:  {SOURCE} ({QUELLPROJEKT_NAME})

 DNA kopiert:
   commands/  ({DNA_COMMANDS} Dateien)
   agents/    ({DNA_AGENTS} Dateien)
   meta/      ({DNA_META} Dateien)
   patterns/  ({DNA_PATTERNS} Dateien)
   scripts/   ({DNA_SCRIPTS} Dateien)

 Leer initialisiert:
   _manifest.md       (PHASE=READY)
   _backlog_index.md  (backlog_counter=0)
   _parking-lot.md    (leer)
   INSTRUCTION.md     (Neues Projekt, origin: {SOURCE})
   vault-routing.json (DCS: {DCS_PFAD})
   project.yaml       (name: {NAME})
   + 18 leere Verzeichnisse (models/, specs/, crumbs/ etc.)

 Git: Neues Repo (git init) — eigene Historie.

 Quellprojekt {SOURCE}: UNVERAENDERT (INV-1 verifiziert)
 Source-Leak-Check: {OK | WARNUNG: N Treffer}
 DCS-Verzeichnis: {existiert | HINWEIS: bitte erstellen}

 Naechster Schritt:
   cd {NAME}/
   claude
   Dann: /_A_orchestrate {ERSTES_FEATURE}
 ═══════════════════════════════════════════════════════"
```

---

## Qualitaetskriterien (AK-01-03)

1. **DNA komplett:** Alle 7 DNA-Verzeichnisse (commands/, agents/, meta/, patterns/, scripts/, tools/, reference/) identisch zum Quellprojekt
2. **Daten leer:** Keine Altlasten — Manifest READY, Backlog leer, keine Pipeline-States
3. **Quellprojekt unveraendert:** git diff im Quellprojekt = 0 Aenderungen (INV-1)
4. **Kein Source-Leak:** Kein Quellprojekt-Name in Daten-Artefakten (ausser Allowlist)
5. **Eigener DCS-Pfad:** vault-routing.json hat {NAME}-Pattern mit {DCS_PFAD} (INV-4)

---

## NOTIFY (Pflicht — allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle 4 Schritte + Verifizierung abgeschlossen):

```bash
powershell -Command "notify '/_project_mitose {NAME} abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

---

ARGUMENTS: $ARGUMENTS
