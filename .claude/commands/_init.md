# /_init - Neues Projekt mit OmniCommand-Infrastruktur bootstrappen

```yaml
status: active
version: 2.0.0
created: 2026-02-21
updated: 2026-04-07
type: satellite
chain_position: standalone
team_based: false
```

---

```
+======================================================================+
| COMMAND: /_init                                                       |
+======================================================================+
|                                                                        |
| ACTOR: DU (die ausfuehrende Claude-Instanz, KEIN Team)               |
|                                                                        |
| ZWECK: Neues Projekt mit OmniCommand-Infrastruktur bootstrappen.      |
|        5 Teilsysteme: Parameter-Dialog, Vault-Routing, Dual-Git,      |
|        Backlog-Init, Source-Leak-Verifikation.                         |
|                                                                        |
|        Kopiert die TOOLBOX (.claude/commands, agents, scripts, etc.)  |
|        aber NICHT den State (models, synthese, wissen, Task.md).      |
|        vault-routing.json wird NICHT kopiert sondern NEU generiert.   |
|        Das neue Projekt startet mit leerem Manifest (PHASE=READY)    |
|        und leerem Parking-Lot.                                        |
|                                                                        |
| AUFRUF:                                                                |
|   /_init                                                               |
|   (interaktiv — alle 5 Parameter werden per Dialog abgefragt)        |
|                                                                        |
| WAS WIRD KOPIERT (Infra/Toolbox):                                     |
|   .claude/commands/       (alle Commands)                              |
|   .claude/agents/         (Agent-Definitionen)                         |
|   .claude/scripts/        (Bash/PS1 Scripts)                           |
|   .claude/config/         (Konfiguration, OHNE vault-routing.json)    |
|   .claude/patterns/       (Pattern-Library)                            |
|   .claude/tools/          (Tools)                                      |
|   .claude/reference/      (Referenz-Dokumente)                         |
|   .claude/meta/           (Meta-Konventionen)                          |
|   .claude/settings.local.json                                          |
|                                                                        |
| WAS WIRD NEU GENERIERT (Source-Leak-frei):                             |
|   .claude/config/vault-routing.json  (nur eigener Rule + Wildcard)    |
|   CLAUDE.md                          (BDF-Regeln, KEIN Quellballast)  |
|   .claude/INSTRUCTION.md             (Neues Projekt — minimal)        |
|   {VAULT}/_backlog_index.md          (counter=0)                      |
|   config/project.yaml               (name, abbreviation, vault, desc) |
|                                                                        |
| WAS WIRD BLANK ERSTELLT:                                               |
|   {VAULT}/_manifest.md              (PHASE=READY + BACKLOG_STATE)      |
|   {VAULT}/_parking-lot.md           (leer)                              |
|   18 leere State-Verzeichnisse                                         |
|                                                                        |
| MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):                       |
|   Pattern A: Reiner State-Write — kein Protokoll-Eintrag              |
|   SCHREIBT STATE: PHASE=READY (im neuen Projekt-Manifest)             |
|   SCHREIBT NICHT: _manifest_protokoll.md (neues Projekt hat keins)    |
|                                                                        |
| WAS WIRD NICHT KOPIERT (State):                                        |
|   .claude/models/*.md              (Feature-spezifisch)                |
|   .claude/wissen/*.md              (Feature-spezifisch)                |
|   .claude/crumbs/*.md              (Feature-spezifisch)                |
|   .claude/analysis/synthese/*      (Feature-spezifisch)                |
|   .claude/analysis/exploration/*   (Feature-spezifisch)                |
|   .claude/analysis/drafts/*        (Feature-spezifisch)                |
|   .claude/Task*.md                 (Feature-spezifisch)                |
|   .claude/pileOfMud/*              (Feature-spezifisch)                |
|   .claude/output/*                 (Feature-spezifisch)                |
|                                                                        |
| INVARIANTEN:                                                           |
|   INV-1: Source-Leak-Schutz (kein Quellprojekt-State im Ziel)        |
|   INV-2: vault-routing APPEND-only (bestehende Rules unveraendert)    |
|   INV-3: Manifest-Clean (KEIN W_FETCH/A_PIPELINE/SC_PIPELINE/i_core) |
|   INV-4: No-Overwrite (Abbruch bei bestehendem Zielverzeichnis)      |
|   INV-5: Git-Trennung (2 separate Repos, kein submodule/subtree)     |
|   INV-6: Vault-Pfad-Immutable (nach Erstellung nicht aenderbar)      |
+======================================================================+
```

---

## Ablauf

### Schritt 0: Parameter-Sammlung (T1)

5 Pflicht-Parameter per AskUserQuestion-Dialog sammeln.

**0.1: Projekt-Name**

```
AskUserQuestion:
  header: "Projekt-Name"
  question: "Wie soll das neue Projekt heissen?
    (Pflicht, keine Sonderzeichen ausser Bindestrich. Beispiel: MeinProjekt)"
  options:
    - label: "Eingeben"
      description: "Projektname eingeben"
  multiSelect: false
```

Validierung: Nicht leer, nur Buchstaben/Ziffern/Bindestrich.
→ Speichere als `{NAME}`

**0.2: Projekt-Abkuerzung**

```
AskUserQuestion:
  header: "Projekt-Abkuerzung"
  question: "Abkuerzung fuer das Projekt (2-5 Grossbuchstaben)?
    Beispiel: 'JobCenter' → 'JC', 'MeinProjekt' → 'MP'"
  options:
    - label: "Eingeben"
      description: "2-5 Grossbuchstaben"
  multiSelect: false
```

→ Speichere als `{ABKUERZUNG}`

**0.3: Vault-Auswahl**

```
VAULT_ROUTING lesen: .claude/config/vault-routing.json
VAULTS extrahieren: alle Keys aus "vaults" Objekt

AskUserQuestion:
  header: "Vault-Auswahl"
  question: "Welchem Vault soll das Projekt zugeordnet werden?"
  options:
    (fuer jeden Vault-Key eine Option mit description aus vaults.{key}.description)
    Beispiel:
    - label: "DCS"
      description: "Haupt-Vault fuer OmniCommand und DCSRE Projekte"
    - label: "CenCoCo-Vault"
      description: "Vault fuer CenCoCo Consulting"
    - label: "Brain-Vault"
      description: "Persoenlicher Vault"
  multiSelect: false
```

→ Speichere als `{VAULT}`

**0.4: Vault-Pfad**

```
VAULT_PATH = vaults.{VAULT}.linux_path aus vault-routing.json

Falls VAULT_PATH == "UNKLAR":
  AskUserQuestion:
    header: "Vault-Pfad (manuell)"
    question: "Der Vault '{VAULT}' hat keinen bekannten Linux-Pfad.
      Bitte den absoluten Pfad zum Vault-Verzeichnis eingeben.
      Beispiel: /home/uczen/Documents/MeinVault"
    options:
      - label: "Eingeben"
        description: "Absoluter Pfad zum Vault"
    multiSelect: false

  Validierung: test -d {eingegebener Pfad} ODER mkdir -p bei Bedarf
  → VAULT_PATH = eingegebener Pfad

→ Speichere als {VAULT_PATH}
```

**0.5: Projekt-Pfad**

```
AskUserQuestion:
  header: "Projekt-Pfad"
  question: "Wohin soll das neue Projekt initialisiert werden?
    (Absoluter Pfad zum Zielverzeichnis. Darf NICHT existieren.)
    Beispiel: /home/uczen/Projekt/AllProjekt/Projekt/{NAME}"
  options:
    - label: "Eingeben"
      description: "Absoluter Pfad eingeben"
  multiSelect: false
```

Guard (INV-4): Falls Verzeichnis existiert → Abbruch:
```
Falls test -d {PROJEKT_PFAD}:
  "FEHLER: Verzeichnis {PROJEKT_PFAD} existiert bereits.
   Kein Overwrite (INV-4). Falls beabsichtigt: Verzeichnis zuerst manuell entfernen."
  → Abbruch
```

→ Speichere als `{PROJEKT_PFAD}`

**Parameter-Zusammenfassung:**

```
AUSGABE:
  "═══════════════════════════════════════════════════════
   /_init: Parameter gesammelt
   ═══════════════════════════════════════════════════════
   Name:        {NAME}
   Abkuerzung:  {ABKUERZUNG}
   Vault:       {VAULT}
   Vault-Pfad:  {VAULT_PATH}
   Projekt-Pfad: {PROJEKT_PFAD}
   ═══════════════════════════════════════════════════════"
```

---

### Schritt 1: Toolbox kopieren + State-Dirs erstellen (T4)

```bash
bash .claude/scripts/initialize.sh {PROJEKT_PFAD}
```

initialize.sh macht:
- No-Overwrite Guard (INV-4)
- Toolbox-Kopie (commands, agents, config OHNE vault-routing.json, patterns, scripts, tools, reference, meta)
- 18 leere State-Verzeichnisse
- Blank Manifest (PHASE=READY) + Blank Parking-Lot

---

### Schritt 2: vault-routing.json Behandlung (T2)

**2.1: QUELL-vault-routing.json APPEND (INV-2)**

Lese `.claude/config/vault-routing.json` (QUELLPROJEKT).

```
PATTERN-KOLLISIONS-CHECK (AK-08.2):
  Fuer jede bestehende Rule in detection.rules[]:
    Falls {NAME} ist Substring von rule.pattern ODER rule.pattern ist Substring von {NAME}:
      WARNUNG: "Pattern-Kollision: '{NAME}' ueberlappt mit bestehendem Pattern '{rule.pattern}'.
               Bitte pruefen ob Detection korrekt funktioniert."
    Falls rule.pattern == {NAME}:
      FEHLER: "Rule mit pattern='{NAME}' existiert bereits. Abbruch (INV-4)."
      → Abbruch

PRIORITY-BERECHNUNG (AK-08.1):
  priorities = [rule.priority fuer jede Rule in detection.rules[] wo priority != 999]
  NEXT_PRIORITY = max(priorities) + 1

NEUER RULE-EINTRAG konstruieren:
  new_rule = {
    "pattern": "{NAME}",
    "vault": "{VAULT}",
    "priority": {NEXT_PRIORITY},
    "rag_collections": [vaults.{VAULT}.global_rag],
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
    "description": "{NAME}-Projekt → {VAULT} ({vaults.{VAULT}.global_rag})"
  }

  Falls {VAULT} == "DCS":
    new_rule.backlog.subfolder_structure = (kopiere aus OmniCommand-Rule:
      subfolder_structure mit 10 Ordner-Typen + vault_document_frontmatter_schema)

APPEND: Fuege new_rule VOR dem Wildcard-Fallback (priority=999) ein.
Fuege {NAME} zu vaults.{VAULT}.projects[] hinzu.

Python3-Inline:
```

```bash
python3 -c "
import json, sys

with open('.claude/config/vault-routing.json', 'r') as f:
    data = json.load(f)

NAME = sys.argv[1]
VAULT = sys.argv[2]
NEXT_PRIO = int(sys.argv[3])
GLOBAL_RAG = sys.argv[4]
DCS_MODE = sys.argv[5]  # 'true' oder 'false'

# Neuer Rule
new_rule = {
    'pattern': NAME,
    'vault': VAULT,
    'priority': NEXT_PRIO,
    'rag_collections': [GLOBAL_RAG],
    'backlog': {
        'enabled': True,
        'subfolder': f'{NAME}/Backlog',
        'dateiname_convention': 'BL-{NNN:03d}-{slug}.md',
        'id_format': 'BL-{NNN}',
        'id_padding': 3,
        'slug_transform': 'kebab-case',
        'index_file': '{VAULT}/_backlog_index.md',
        'INV-6': 'Vault-Pfad darf nach Erstellung NICHT geaendert werden.'
    },
    'description': f'{NAME}-Projekt → {VAULT} ({GLOBAL_RAG})'
}

# DCS: subfolder_structure aus OmniCommand-Rule kopieren
if DCS_MODE == 'true':
    for rule in data['detection']['rules']:
        if rule.get('pattern') == 'OmniCommand' and 'backlog' in rule:
            bl = rule['backlog']
            if 'subfolder_structure' in bl:
                new_rule['backlog']['subfolder_structure'] = bl['subfolder_structure']
            if 'vault_document_frontmatter_schema' in bl:
                new_rule['backlog']['vault_document_frontmatter_schema'] = bl['vault_document_frontmatter_schema']
            break

# VOR Wildcard (priority=999) einfuegen
rules = data['detection']['rules']
insert_idx = len(rules)
for i, r in enumerate(rules):
    if r.get('priority') == 999:
        insert_idx = i
        break
rules.insert(insert_idx, new_rule)

# Projekt zu vaults.{VAULT}.projects[] hinzufuegen
if VAULT in data.get('vaults', {}):
    projects = data['vaults'][VAULT].get('projects', [])
    if NAME not in projects:
        projects.append(NAME)
        data['vaults'][VAULT]['projects'] = projects

with open('.claude/config/vault-routing.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f' [APPEND] vault-routing.json: pattern={NAME}, vault={VAULT}, priority={NEXT_PRIO}')
" "{NAME}" "{VAULT}" "{NEXT_PRIORITY}" "{GLOBAL_RAG}" "{DCS_MODE}"
```

Wobei:
- `{GLOBAL_RAG}` = `vaults.{VAULT}.global_rag` aus vault-routing.json
- `{DCS_MODE}` = "true" falls `{VAULT}` == "DCS", sonst "false"

**2.2: ZIEL-vault-routing.json NEU generieren**

Erstelle `{PROJEKT_PFAD}/.claude/config/vault-routing.json`:

```json
{
  "$schema": "vault-routing-v3",
  "version": "3.0",
  "description": "Vault-Routing fuer {NAME}. Generiert via /_init.",
  "env_var": "OBSIDIAN_VAULT_PATH",
  "detection": {
    "method": "path-pattern",
    "rules": [
      {
        "pattern": "{NAME}",
        "vault": "{VAULT}",
        "priority": 1,
        "rag_collections": ["{GLOBAL_RAG}"],
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
        "description": "{NAME}-Projekt → {VAULT} ({GLOBAL_RAG})"
      },
      {
        "pattern": "*",
        "vault": "{VAULT}",
        "priority": 999,
        "rag_collections": ["{GLOBAL_RAG}"],
        "warning": "Kein spezifisches Pattern",
        "description": "Default Fallback"
      }
    ]
  },
  "vaults": {
    "{VAULT}": {
      "linux_path": "{VAULT_PATH}",
      "env_var": "{vaults.{VAULT}.env_var}",
      "projects": ["{NAME}"],
      "global_rag": "{GLOBAL_RAG}"
    }
  },
  "notes": [
    "Generiert durch /_init {NAME}",
    "Datum: {DATUM}",
    "Quellprojekt: {QUELLPROJEKT_NAME}"
  ]
}
```

Falls `{VAULT}` == "DCS": backlog.subfolder_structure mit 10 Ordner-Typen + vault_document_frontmatter_schema hinzufuegen (aus OmniCommand-Rule kopiert).

KEINE Quellprojekt-Rules, KEINE local_knowledge_* Collections (INV-1).

---

### Schritt 3: Dual-Git-Init (T3)

```
3.1: Projekt-Git
  cd {PROJEKT_PFAD} && git init
  → "Neues Git-Repo initialisiert: {PROJEKT_PFAD}"
  → KEIN git add, KEIN git commit (AK-03.3)

3.2: Vault-Git (conditional)
  Falls test -d "{VAULT_PATH}/.git":
    → "Vault-Git existiert bereits: {VAULT_PATH}/.git — Skip (Shared Vault)"
  Falls NICHT:
    cd {VAULT_PATH} && git init
    → "Neues Vault-Git initialisiert: {VAULT_PATH}"
    → KEIN git add, KEIN git commit (AK-03.3)
```

---

### Schritt 4: Vault-Ordner erstellen (T4)

```bash
mkdir -p "{VAULT_PATH}/{NAME}/Backlog/"
```

NUR `Backlog/` — weitere Ordner (Model/, Spec/, Gap/, etc.) lazy bei erster Nutzung (ADR-03).

```
AUSGABE:
  " [MKDIR] {VAULT_PATH}/{NAME}/Backlog/"
```

---

### Schritt 4b: layers.yaml Vault-Default anlegen (ARCH-N7)

```
# ARCH-N7 Vault-First: layers.yaml gehoert in {VAULT_PATH}/{NAME}/config/layers.yaml
# Primaerer Lesepfad fuer _PT_arch_init — NICHT .claude/config/layers.yaml des Zielprojekts
LAYERS_VAULT = "{VAULT_PATH}/{NAME}/config/layers.yaml"

IF NOT test -f "$LAYERS_VAULT":
  mkdir -p "{VAULT_PATH}/{NAME}/config/"
  # Default-Template aus OmniCommand-Self kopieren als Ausgangspunkt
  SOURCE_TEMPLATE = ".claude/config/layers.yaml"
  IF test -f "$SOURCE_TEMPLATE":
    cp "$SOURCE_TEMPLATE" "$LAYERS_VAULT"
    # Passe project-Feld an (sed-Ersatz)
    sed -i "s/project: \"OmniCommand\"/project: \"{NAME}\"/" "$LAYERS_VAULT"
    sed -i "s/bl_ref: \"BL-154\"/bl_ref: \"\"/" "$LAYERS_VAULT"
    AUSGABE: " [LAYERS] {LAYERS_VAULT} erstellt (Default-Template aus OmniCommand-Self, ARCH-N7)"
  SONST:
    AUSGABE: " [LAYERS] WARNUNG: Template .claude/config/layers.yaml nicht gefunden — {LAYERS_VAULT} nicht erstellt"
SONST:
  AUSGABE: " [LAYERS] {LAYERS_VAULT} existiert bereits — Skip (INV-4)"
```

---

### Schritt 4c: Stage-Set-Verhandlung (BL-413)

```
# FORWARD-SEAM BL-332: Wenn /_init_orchestrate gebaut wird, wandert dieser
# Schritt dorthin. Heimat: BL-332 (InitOrchestrate).

# Stage-1-Unit: immer, ohne Dialog
Skill(_stage_init 1 unit)
AUSGABE: " [STAGE] stage_1_unit angelegt (Default, kein Dialog)"

# Stage-2+ per iterativem Owner-Dialog
stage_nr = 2
WHILE true:
  AskUserQuestion:
    header: "Stage-Set: Weitere Stage?"
    question: |
      Welche Stages braucht dieses Projekt?
      Stage-1-Unit ist bereits angelegt.
      Weitere Stage hinzufuegen? (Nummer + Name, z.B. '3 integration')
      Oder: 'fertig' um Stage-Set zu bestaetigen.
    options:
      - "{nr} {name}"   # z.B. "3 integration", "5 e2e-live"
      - "fertig"        # Bestaetigung: Stage-Set abgeschlossen

  IF Antwort == "fertig":
    BREAK

  nr, name = parse(Antwort)
  Skill(_stage_init {nr} {name})
  AUSGABE: " [STAGE] stage_{nr}_{name} angelegt via _stage_init"

  # Spawn-Trigger: 2 von 3 Kriterien
  kriterien_erfuellt = 0
  IF Technologie-in-Kontext-unbekannt:      kriterien_erfuellt += 1  # TECH-NEU
  IF setup/teardown-Befehle-unbekannt:      kriterien_erfuellt += 1  # SETUP-UNBEKANNT
  IF resources.infrastruktur != null/skip:  kriterien_erfuellt += 1  # INFRA-REQUIRED

  IF kriterien_erfuellt >= 2:
    /_backlog mit:
      title: "Stage-{nr}-{name}: Explore + Realisierung"
      body: "Offene Slice-Fragen: testbefehl?, setup-commands?, teardown-commands?,
             health_check?, resources.infrastruktur?"
    AUSGABE: " [SPAWN] Exploratives BL fuer Stage-{nr} angelegt"

  stage_nr += 1
```

---

### Schritt 5: CLAUDE.md + INSTRUCTION.md generieren (T4)

**5.1: CLAUDE.md im Zielprojekt (AK-05.1)**

Erstelle `{PROJEKT_PFAD}/CLAUDE.md`:

```markdown
# WICHTIG: LIES ZUERST .claude/INSTRUCTION.md

**STATUS: Neues Projekt. Lies .claude/INSTRUCTION.md fuer naechste Schritte.**

## Regeln

1. LIES SOFORT `.claude/INSTRUCTION.md` — dort steht der aktuelle Stand und naechste Schritt
2. KEIN direkter Push auf main — immer ueber Feature-Branch + PR (BDF v2.7.0)
3. BDF arbeitet in `feature/bdf-YYYY-MM-DD` Branch, PR wird in POST_PHASE erstellt
```

KEINE Feature-Namen, Parking-Lot-Items, OmniCommand-Referenzen (INV-1, AK-05.1).

**5.2: INSTRUCTION.md im Zielprojekt (AK-05.2, AK-05.3)**

Erstelle `{PROJEKT_PFAD}/.claude/INSTRUCTION.md`:

```markdown
# STATUS: Neues Projekt — bereit fuer erste Analyse

**Datum:** {DATUM}
**origin_project:** {QUELLPROJEKT_NAME} (via /_init)
**Branch:** noch nicht erstellt (git init ausgefuehrt)

---

## Naechster Schritt

/_A_orchestrate {NAME}

---

## Projekt-Kontext

Dieses Projekt wurde durch /_init aus {QUELLPROJEKT_NAME} erstellt.
Toolbox-Artefakte (commands/, agents/, scripts/, patterns/) wurden kopiert.
Daten-Artefakte (models/, specs/, crumbs/) sind leer — bereit fuer eigene Analyse.
```

---

### Schritt 6: Backlog-Init (T5)

**6.1: _backlog_index.md (AK-06.1)**

Erstelle `{PROJEKT_PFAD}/{VAULT}/_backlog_index.md`:

```markdown
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
```

**6.2: Manifest BACKLOG_STATE erweitern (AK-06.2)**

Fuege am Ende von `{PROJEKT_PFAD}/{VAULT}/_manifest.md` hinzu:

```
**BACKLOG_STATE:**
  backlog_counter: 0
  backlog_last_id: none
  backlog_last_update: {DATUM}
```

**6.3: config/project.yaml NEU generieren (AK-06.3)**

Erstelle `{PROJEKT_PFAD}/config/project.yaml`:

```yaml
name: {NAME}
abbreviation: {ABKUERZUNG}
vault: {VAULT}
description: ""
```

KEINE `rag`/`wp`-Felder (OmniCommand-spezifisch, INV-1).

---

### Schritt 7: Source-Leak-Check + Abschlussbericht (T6)

**7.1: Source-Leak-Check (AK-07.1)**

```
QUELLPROJEKT_NAME = basename des aktuellen Verzeichnisses (z.B. "OmniCommand")

ALLOWLIST = [
  "{PROJEKT_PFAD}/.claude/INSTRUCTION.md",
  "{PROJEKT_PFAD}/.claude/config/vault-routing.json"
]

PRUEFE: Grep nach "{QUELLPROJEKT_NAME}" in:
  - {PROJEKT_PFAD}/.claude/analysis/
  - {PROJEKT_PFAD}/CLAUDE.md
  - {PROJEKT_PFAD}/{VAULT}/_manifest.md
  - {PROJEKT_PFAD}/{VAULT}/_parking-lot.md
  - {PROJEKT_PFAD}/{VAULT}/_backlog_index.md
  - {PROJEKT_PFAD}/config/project.yaml

Falls Treffer ausserhalb ALLOWLIST:
  WARNUNG: "Source-Leak erkannt: {QUELLPROJEKT_NAME} in {DATEI}:{ZEILE}"
  (kein Abbruch — nur Warnung)

Falls 0 Treffer:
  "Source-Leak-Check: PASS (0 Treffer fuer '{QUELLPROJEKT_NAME}')"
```

**7.1b: Frontmatter-Konsistenz-Check (AK-07.3)**

```
# Frontmatter-Konsistenz (AK-07.3): Pruefe Vault-Knoten-Verdrahtung
ZIEL_VR = "{PROJEKT_PFAD}/.claude/config/vault-routing.json"
FRONTMATTER_CHECK = "PASS"

# Pruefe 1: vault-routing.json parsen → detection.rules[]
#   Gibt es eine Rule mit pattern das "{NAME}" oder "{ABKUERZUNG}" enthaelt?
RULES = JSON parsen aus ZIEL_VR → detection.rules[]
RULE_MATCH = false
FUER rule IN RULES:
  IF rule.pattern enthaelt "{NAME}" ODER rule.pattern enthaelt "{ABKUERZUNG}":
    RULE_MATCH = true

# Pruefe 2: vaults.{VAULT} existiert in der JSON-Struktur?
VAULT_MATCH = JSON parsen aus ZIEL_VR → vaults → hat Key "{VAULT}"?

IF RULE_MATCH UND VAULT_MATCH:
  FRONTMATTER_CHECK = "PASS"
SONST:
  FRONTMATTER_CHECK = "WARN: Vault-Knoten nicht korrekt verdrahtet"
  (kein Abbruch — nur Warnung)
```

**7.2: Abschlussbericht (AK-07.2 - AK-07.5)**

```
DATEIEN_KOPIERT = find {PROJEKT_PFAD}/.claude -type f | wc -l
DIRS_ERSTELLT  = find {PROJEKT_PFAD}/.claude -type d | wc -l

# DNA-Verifikation (AK-07.2): Programmatische Pruefungen
VERIFIKATION_FEHLER = 0

# Pflichtdateien pruefen
FUER datei IN [".claude/INSTRUCTION.md", ".claude/CLAUDE.md",
               ".claude/config/vault-routing.json",
               "{VAULT}/_backlog_index.md",
               "{VAULT}/_manifest.md",
               "config/project.yaml"]:
  IF NOT test -f "{PROJEKT_PFAD}/{datei}":
    WARNUNG: "Pflichtdatei fehlt: {datei}"
    VERIFIKATION_FEHLER += 1

# Pflichtverzeichnisse pruefen (5 kritische)
FUER dir IN [".claude/analysis", ".claude/models", ".claude/commands",
             ".claude/config", ".claude/audit"]:
  IF NOT test -d "{PROJEKT_PFAD}/{dir}":
    WARNUNG: "Pflichtverzeichnis fehlt: {dir}"
    VERIFIKATION_FEHLER += 1

IF VERIFIKATION_FEHLER == 0:
  DNA_CHECK = "PASS (0 Fehler)"
SONST:
  DNA_CHECK = "WARN ({VERIFIKATION_FEHLER} Fehler)"

# Vault-Count (AK-07.4)
VAULT_DATEIEN = find {VAULT_PATH}/{NAME} -type f 2>/dev/null | wc -l
VAULT_ORDNER  = find {VAULT_PATH}/{NAME} -type d 2>/dev/null | wc -l

AUSGABE:
  "═══════════════════════════════════════════════════════
   /_init: Neues Projekt erstellt!
   ═══════════════════════════════════════════════════════

   Projekt:      {NAME}
   Pfad:         {PROJEKT_PFAD}
   Vault:        {VAULT} ({VAULT_PATH})
   Abkuerzung:   {ABKUERZUNG}

   Toolbox kopiert:   {DATEIEN_KOPIERT} Dateien
   Verzeichnisse:     {DIRS_ERSTELLT} (inkl. 18 State-Dirs)
   vault-routing.json: QUELL-APPEND (priority={NEXT_PRIORITY}) + ZIEL-NEU
   Git-Repos:         Projekt (neu) + Vault ({neu|bestehend})
   Vault-Ordner:      {VAULT_PATH}/{NAME}/Backlog/
   Backlog:           counter=0, _backlog_index.md, config/project.yaml
   Source-Leak-Check: {PASS | WARNUNG: N Treffer}
   Frontmatter-Check: {FRONTMATTER_CHECK}
   DNA-Verifikation:  {DNA_CHECK}
   Vault-Dateien:     {VAULT_DATEIEN} Dateien in {VAULT_ORDNER} Ordnern

   NEU generiert (Source-Leak-frei):
     CLAUDE.md, INSTRUCTION.md, vault-routing.json,
     _backlog_index.md, config/project.yaml

   Naechste Schritte:
     cd {PROJEKT_PFAD}
     claude
     /_A_orchestrate {ERSTES_FEATURE}
   ═══════════════════════════════════════════════════════"
```

**7.3: Notify (AK-07.6, Pflicht — allerletzter Schritt)**

```bash
powershell -Command "notify '/_init {NAME} abgeschlossen'"
```

---

ARGUMENTS: $ARGUMENTS
