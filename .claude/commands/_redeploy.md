---
name: _redeploy
description: Deployed Commands + Infrastruktur aus OmniCommand in alle bekannten Projekt-Verzeichnisse
type: satellite
---

# /_redeploy

**Zweck:** Commands und/oder Infrastruktur-Dateien aus OmniCommand in alle Projekt-Verzeichnisse kopieren.

**Aufruf:**
```
/_redeploy <command_name> [pfad1 pfad2 ...]
/_redeploy --all                              → ALLE Commands an alle Projekte
/_redeploy --infra                            → NUR PROZESS-UNIVERSELLE Infra (OHNE typ-spezifische Meta)
/_redeploy --full                             → Commands + Universal-Infra → Live-Projekte (OHNE --meta-snapshot)
/_redeploy --meta-snapshot {pfad...}          → NUR PROJEKT-TYP-SPEZIFISCHE Meta → an EXPLIZITE Pfade (Pfade PFLICHT)
/_redeploy --full --meta-snapshot {pfad...}   → Commands + Universal-Infra + Typ-Meta → an EXPLIZITE Pfade
/_redeploy --template                         → ALLES (Universal + Typ-Spezifisch) → NUR AgentsArchive Templates
```

**Beispiele:**
```
/_redeploy _Pre_PR_DocKlarity
/_redeploy _jira_ticket
/_redeploy --all                              → alle Commands an alle Projekte
/_redeploy --infra                            → Universal-Infra (agents, scripts, meta/{a,sdf,sc,pr})
/_redeploy --full                             → commands + Universal-Infra an alle Projekte (OHNE Typ-Meta)
/_redeploy --meta-snapshot {pfad}             → Typ-Meta (architekturKonv., codeKonv., stage_*, patterns) NUR an {pfad}
/_redeploy --full --meta-snapshot {pfad}      → commands + Universal-Infra + Typ-Meta NUR an {pfad}
/_redeploy --template                         → ALLES an AgentsArchive Templates (inkl. stage_{N}.md, patterns)
```

**WICHTIG (--meta-snapshot Invariante):**
`--meta-snapshot` ist projekt-AGNOSTISCH. Der Command kennt den Inhalt der Typ-Meta-Files NICHT (kann
DCSRE, CenCoCo, GraphRag, etc. sein) und hat KEINE Default-Target-Liste. **Pfad-Argumente sind
PFLICHT.** Aufruf `/_redeploy --meta-snapshot` ohne Pfade → FEHLER: "--meta-snapshot benoetigt explizite Pfade.
Begruendung: Typ-Meta ist projekt-typ-spezifisch — Default-Spread waere Contamination-Risiko."

---

## Schritt 1: Parameter auflösen

### --meta (deprecated)

IF flag == "--meta":
  WARN: "[REDEPLOY] DEPRECATED: --meta ist veraltet ab BL-193."
  WARN: "  Neu: /_redeploy --meta-snapshot {pfad}  (Offline-Snapshot aus Vault-Meta)"
  WARN: "  Alternative: Vault direkt aktualisieren via Obsidian-Sync (kein redeploy noetig)."
  WARN: "  --meta wird in einem kuenftigen Release entfernt."
  ABORT: kein Deploy, kein alter Pfad mehr aktiv.
  EXIT 1

### command_name
Pflicht. Name des Commands ohne `.md` — z.B. `_Pre_PR_DocKlarity`.

Source-Datei: `{OMNICOMMAND_BASE}/.claude/commands/{command_name}.md`

Falls die Datei nicht existiert → Abbruch:
```
FEHLER: .claude/commands/{command_name}.md nicht gefunden in OmniCommand.
Verfuegbare Commands: [ls .claude/commands/*.md]
```

### Projekt-Liste
Reihenfolge der Auflösung:
1. **Argumente** (nach command_name): Werden als Ziel-Pfade verwendet.
2. **Keine Argumente**: Eingebettete Standard-Liste verwenden (siehe unten).

---

## Schritt 2: Standard-Projekt-Liste (eingebettet)

```
BASE = C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure

PROJEKTE:
  DCSRE-1051_einrichtungen_filtern_Analyse
  DCSRE-1212_DatenmodellPE_AdressDeutsch
  DCSRE-133_ProzessverarbeitungPB_StoryKickOff_Analyse
  DCSRE-1412_update_angular_20_PRQuali
  DCSRE-1414_navigation_ungespeicherte_aenderungen_PR_Analyse
  DCSRE-1435_DatenaufbereitungIK_Analyse
  DCSRE-1435_DatenaufbereitungIK_Analyse2
  DCSRE-1605_DicFileImportIntegrationstests2_Analyse2
  DCSRE-603_PruefgrundlageZuordnungsliste_PR
  DCSRE-651_EinrichtungTestdaten_Analyse
  DCSRE-881_DateiabholungAnalyse_DatenTyp
  DCSRE-881_DateiabholungAnalyse_HardcodedString
  DCSRE-881_DateiabholungAnalyse_Profil
  DCSRE-881_DateiabholungAnalyse_TCP-Healthcheck
  DCSRE-881_Dateiabholung_ZeitNormalisieren
  DCSRE-881_Dateiabholung_ZeitNormalisieren_SliceA
  DCSRE-882_MetaDaten
  DCSRE-882_MetaDaten_Analyse_CheckSum
  DCSRE-882_MetaDaten_Analyse_IntegrationTest
  DCSRE-93_Einrichtungsdetails_Analyse
  DCSRE-94_QDVS_Selbstauskunft_bearbeiten_Analyse
  DCSRE-98_QDVS_Selbstauskunft_Anzeigen_Analyse
  DCSRE-1430_QDVTP_Selbstauskunft_Analyse
  DCSRE-486_QDVTPSelbstauskunftBearbeiten_Analyse
  DCSRE-486_QDVTPSelbstauskunftBearbeiten_Frontend_Analyse
  DCSRE-1944_QDVS_TP_SA_Anlegen_Analyse
  DCSRE-1668_IK_Sortiert_Gefiltert_Analyse
  DCSRE-1672_Detail_Ik_Benutzer_Analyse
  DCSRE-AnalyseIntegrationTest
```

### Zusaetzliche Einzelpfade (ausserhalb BASE)

```
EXTRA_PROJEKTE:
  C:/Users/Administrator/Documents/Work/Kluger/cencoco/.claude
  C:/Users/Administrator/Documents/Projekt/GraphRag/.claude
```

### Template-Projekte (haben EIGENE .claude/ Variante — bekommen ALLES bei --template)

```
TEMPLATE_PROJEKTE:
  C:/Users/Administrator/Documents/Projekt/AgentsArchive/.claude_CenCoCo      # CENCOCD → claude_sync.lua
  C:/Users/Administrator/Documents/Projekt/AgentsArchive/.claude_DCSRE        # DCSRE   → claude_sync.lua
  C:/Users/Administrator/Documents/Projekt/AgentsArchive/.claude_OmniCommand  # OMNICOMMAND → claude_sync.lua
```

**NOTE — `.claude` (ohne Suffix) GELOESCHT (Schweizer-Uhrmacher 2026-05-07, Variante b done):**
Symmetrie-Prinzip vollzogen: drei Projekte = drei explizite Suffix-Slots, kein impliziter Default.
`AgentsArchive/.claude` (ohne Suffix) wurde aus EXTRA_PROJEKTE + TEMPLATE_PROJEKTE entfernt und vom User geloescht.
`claude_sync.lua` ROUTING-Tabelle nutzt nur Suffix-Slots — Loeschen unbedenklich fuer DCSRE/CenCoCo/OmniCommand.

**Sister-Session-TODO (KickStartNeoVim/lua/shared/core.lua Z46-95):**
Der `VimEnter`-Bootstrap-Autocmd "Auto-copy .claude folder" liest 6 Pfad-Varianten von
`AgentsArchive/.claude` (ohne Suffix) und kopiert in Worktrees. Nach `.claude`-Loeschung wird dieser
Bootstrap fuer UNKNOWN-Projekte tot (DCSRE/CenCoCo/OmniCommand bleiben funktional via claude_sync.lua).
Empfehlung: Bootstrap-Autocmd entweder entfernen ODER auf Suffix-Slots aware umbauen
(project_name-bewusst, fallback-frei).

**Routing-Kette:** OmniCommand →(/_redeploy --template)→ AgentsArchive {`.claude_DCSRE`, `.claude_CenCoCo`, `.claude_OmniCommand`} →(claude_sync.lua, projekt-spezifisch)→ Worktrees

Vollpfad pro Projekt: `{BASE}/{PROJEKT}/.claude/commands/` bzw. `{EXTRA}/commands/`

---

## Schritt 2b: Deploy-Kategorien (3-Schichten, projekt-agnostisch)

Drei Schichten basierend auf Projekt-Anwendbarkeit. **Der Command ist projekt-typ-agnostisch:** er
kennt den Inhalt der Typ-Spezifischen Files NICHT (kann je nach Source DCSRE, CenCoCo, GraphRag,
oder generisch sein). Routing erfolgt allein ueber Flag + explizite Pfad-Argumente.

**1. PROZESS-UNIVERSELL** (gleich in ALLEN Projekten — bei --all, --infra, --full):

| Verzeichnis | Inhalt | Deploy-Modus |
|-------------|--------|-------------|
| `commands/` | Alle Commands (*.md) | --all, --full, --template, Einzel-Command |
| `agents/` | Agent-Definitionen | --infra, --full, --template |
| `scripts/` | Helper-Scripts | --infra, --full, --template |
| `workflows/` | Deterministische Dispatch-Motoren (`dispatch_implement.js` etc., BL-222 Heilige-Trio) | --infra, --full, --template |
| `meta/a/` | A-Pipeline Referenz | --infra, --full, --template |
| `meta/sdf/` | SDF Referenz (State-Machine) | --infra, --full, --template |
| `meta/sc/` | SC-Zyklus-Protokolle | --infra, --full, --template |
| `meta/pr/` | PR-Workflow-Konfiguration | --infra, --full, --template |
| `meta/implementation/guards.md` | Pre-Pipeline Guards | --infra, --full, --template |
| `meta/implementation/handoff-protocol.md` | SC→I Uebergabe-Protokoll | --infra, --full, --template |
| `pileOfMud/.gitignore` | Briefkasten-Stub — NUR die .gitignore (legt leere git-ignored Inbox an). **NIE der Inhalt** (= instanz-spezifisches Rohmaterial, Contamination-Risiko). | --infra, --full, --template |

**2. PROJEKT-TYP-SPEZIFISCH** (Inhalt typ-abhaengig — bei --meta-snapshot, --template; PFADE PFLICHT bei --meta-snapshot):

> **Agnostik-Invariante:** Der Command kennt den Inhalt dieser Files NICHT. Sie KOENNTEN heute
> typ-X-flavored sein, morgen typ-Y. Deshalb: KEINE Default-Target-Liste fuer `--meta-snapshot`. Pfad-
> Argumente sind PFLICHT bei `--meta-snapshot`. Der User entscheidet je Aufruf, welche Targets
> typ-kompatibel sind.

| Verzeichnis | Inhalt | Deploy-Modus |
|-------------|--------|-------------|
| `meta/architekturKonventionen/` | Architektur-Layer-Definitionen (typ-abhaengig) | --meta-snapshot, --template |
| `meta/codeKonvention/` | Code-Konventionen / Quality-Gate-Regeln (typ-abhaengig) | --meta-snapshot, --template |
| `meta/implementation/stage_*.md` | Test-Stufen-Metadaten (testbefehl, test_projekte — typ-abhaengig) | --meta-snapshot, --template |
| `patterns/` | Pattern Library Index (waechst pro Projekt-Typ) | --meta-snapshot, --template |

**Routing-Kette (3-Slot-Symmetrie, Schweizer-Uhrmacher 2026-05-07):**
- OmniCommand →(--template)→ AgentsArchive/.claude_DCSRE       →(claude_sync.lua, DCSRE)       → DCSRE Worktrees
- OmniCommand →(--template)→ AgentsArchive/.claude_CenCoCo     →(claude_sync.lua, CENCOCD)     → CenCoCo Worktrees
- OmniCommand →(--template)→ AgentsArchive/.claude_OmniCommand →(claude_sync.lua, OMNICOMMAND) → OmniCommand Worktrees (single-branch ueblich)

**3. PROJEKT-INSTANZ-SPEZIFISCH** (NIEMALS ueberschreiben — jedes Projekt hat eigene):

| Verzeichnis | Inhalt | Grund |
|-------------|--------|-------|
| `wissen/` | Projekt-Wissen, Learnings | Jedes Projekt hat eigene Erkenntnisse |
| `models/` | Feature-Models, W{n} | Projekt-spezifische Forschung |
| `analysis/` | Manifest, GAP, Synthese | Projekt-spezifischer Pipeline-State |
| `specs/` | Feature-Spezifikationen | Projekt-spezifische Requirements |
| `crumbs/` | Feature-Kruemmel | Projekt-spezifischer Kontext |
| `output/` | Assays, Presentations | Projekt-spezifische Ausgaben |
| `evidence/` | Evidence-Dokumente | Projekt-spezifische Entscheidungen |
| `_meta/` | Command-Meta-Sidecars + domain-keyed Meta (BL-372 `_meta/commands/{cmd}_Meta.md`, BL-302 `_meta/{domain}/`) | Projekt-spezifischer Command-Inhalt — Meta-Sidecar-Runtime-Konvention (BL-372); Command-File bleibt agnostisch, Inhalt lebt hier |

**REGEL:**
- `/_redeploy --all/--infra/--full` deployt nur **PROZESS-UNIVERSELL** + commands.
- `/_redeploy --meta-snapshot {pfad...}` deployt **PROJEKT-TYP-SPEZIFISCH** an EXPLIZITE Pfade (Pfade PFLICHT).
- `/_redeploy --full --meta-snapshot {pfad...}` kombiniert beide an EXPLIZITE Pfade.
- `/_redeploy --template` deployt alles (Universell + Typ-Spezifisch) an AgentsArchive Templates (3 Slots).
- **PROJEKT-INSTANZ-SPEZIFISCH** wird NIEMALS angefasst.

**Informativ (NICHT command-relevant) — aktueller Stand der Typ-Spezifischen Files:**
Die Files unter `meta/architekturKonventionen/`, `meta/codeKonvention/`, `meta/implementation/stage_*.md`
und `patterns/` enthalten aktuell DCSRE-Backend-Konventionen. **Langfrist-Vision:** Migration nach
`AgentsArchive/.claude_{TYP}/meta/` pro Projekt-Typ (Single-Source-of-Truth pro Typ). Bis dahin:
explizit per `--meta-snapshot {pfad}` an typ-kompatible Targets deployen. Diese Anmerkung steuert KEIN
Command-Verhalten — sie dokumentiert nur den Ist-Stand der Source.

---

## Schritt 2c: Config-Whitelist fuer --infra (ARCH-N11)

**Problem:** `/_redeploy --infra` darf NICHT blind `.claude/config/*` kopieren.
Jedes Projekt hat projekt-spezifische Config-Dateien die nicht ueberschrieben werden duerfen.

**WHITELIST** — diese Config-Dateien werden bei --infra kopiert (projekt-INVARIANT):

| Datei | Grund |
|-------|-------|
| `.claude/config/session_params_default.md` | Globale Session-Default-Parameter — gleich in allen Projekten |
| `.claude/config/model_tiers.yaml` | Model-Tier-Definition — global (ARCH-N8, falls vorhanden) |

**SCHWARZLISTE** — diese Config-Dateien werden NIEMALS bei --infra kopiert (projekt-SPEZIFISCH):

| Datei | Grund |
|-------|-------|
| `.claude/config/layers.yaml` | Jedes Projekt hat eigene Layer-Definition (ARCH-N7, ARCH-N11) |
| `.claude/.vault_root` | Per-Projekt Vault-Pin (INV-VAULT-9) |
| `.claude/config/vault-routing.json` | Projekt-spezifisches Vault-Routing — IMMER projekt-lokal |
| `.claude/config/_session_params.md` | Laufende Session-Parameter (nicht deployable) |

**--force-config Flag:** Explizite Ueberschreibung erlauben:
```
/_redeploy --infra --force-config layers.yaml
```
- Kopiert AUCH Schwarzliste-Files wenn explizit per --force-config angegeben
- Gibt WARNUNG aus: "FORCE-CONFIG: {datei} wird ueberschrieben — Projekt-spezifische Werte gehen verloren"
- Sicherheits-Prompt wenn HiL=true: "Sicher? (j/n)"

**Angepasste --infra Logik:**
```
CONFIG_WHITELIST=["session_params_default.md", "model_tiers.yaml"]
CONFIG_BLACKLIST=["layers.yaml", ".vault_root", "vault-routing.json", "_session_params.md"]
FORCE_CONFIG_FILES = parse --force-config args  # leer wenn nicht angegeben

for dir in {ALLE_PROJEKTE + EXTRA_PROJEKTE}:
  for f in ls .claude/config/*:
    IF basename(f) IN FORCE_CONFIG_FILES:
      cp f dir/config/  # --force-config explizit
      WARNUNG: "FORCE-CONFIG: {basename(f)} kopiert nach {dir}"
    ELIF basename(f) IN CONFIG_WHITELIST:
      cp f dir/config/  # normal
    ELIF basename(f) IN CONFIG_BLACKLIST:
      SKIP: "[REDEPLOY] Schwarzliste: {basename(f)} nicht kopiert (projekt-spezifisch, ARCH-N11)"
    ELSE:
      WARNUNG: "[REDEPLOY] Unbekannte Config-Datei: {basename(f)} — nicht kopiert (Blacklist-Default, ARCH-N11)"
```

---

## Schritt 3: Deploy ausfuehren

### 3a: Einzel-Command Deploy (/_redeploy {command_name})

```bash
OMNICOMMAND_BASE="C:/Users/Administrator/Documents/Projekt/OmniCommand/OmniCommand"  # Schweizer-Uhrmacher 2026-05-07: Source-Move auf Ebene von Documents/Projekt
SRC="$OMNICOMMAND_BASE/.claude/commands/{command_name}.md"

for dir in {ALLE_PROJEKTE + EXTRA_PROJEKTE + TEMPLATE_PROJEKTE}; do
  dest="$dir/commands"  # bzw. $dir/.claude/commands fuer BASE-Projekte
  mkdir -p "$dest"
  cp "$SRC" "$dest/{command_name}.md"
done
```

### 3b: Infrastruktur Deploy (/_redeploy --infra)

Kopiere NUR PROZESS-UNIVERSELLE Infrastruktur (OHNE typ-spezifische Meta, OHNE patterns):

```bash
PROCESS_DIRS="agents scripts workflows"   # workflows/ ERGAENZT 2026-06-03: der BL-222 Dispatch-Motor
                                          # (dispatch_implement.js) ist prozess-universell + MUSS mitdeployen.
                                          # Frueher fehlte er -> Motor-Fixes erreichten die Projekte NICHT (BL-238-Deploy-Befund).
PROCESS_META="meta/a meta/sdf meta/sc meta/pr"   # OHNE codeKonvention, architekturKonventionen
                                                  # (= PROJEKT-TYP-SPEZIFISCH → --meta-snapshot)
PROCESS_FILES="meta/implementation/guards.md meta/implementation/handoff-protocol.md meta/implementation/manifest-write-discipline.md meta/implementation/meta-sidecar-convention.md pileOfMud/.gitignore"
# meta-sidecar-convention.md (BL-372, 2026-06-16): die Meta-Sidecar-Runtime-Konvention ist
# prozess-universell (agnostisch) -> MUSS via --infra mitdeployen. Der projekt-spezifische
# Sidecar-INHALT (_meta/commands/{cmd}_Meta.md) bleibt im Vault (NIEMALS kopieren, siehe oben)."
# pileOfMud/.gitignore (2026-06-01): NUR die Stub — legt leere git-ignored Inbox an.
# Einzel-Datei-Copy (NICHT cp -r pileOfMud/) → der Pile-INHALT wird NIE mitgespread
# (instanz-spezifisches Rohmaterial). Standard-git: .gitignore untrackt KEINE bereits
# getrackten Files im Target — nur kuenftig gedroppte werden ignoriert (kein Surprise).

for dir in {ALLE_PROJEKTE + EXTRA_PROJEKTE}; do
  for share in $PROCESS_DIRS; do
    cp -r "$OMNICOMMAND_BASE/.claude/$share/" "$dir/$share/"
  done
  for meta in $PROCESS_META; do
    mkdir -p "$dir/$meta" && cp -r "$OMNICOMMAND_BASE/.claude/$meta/" "$dir/$meta/"
  done
  for f in $PROCESS_FILES; do
    mkdir -p "$(dirname $dir/$f)" && cp "$OMNICOMMAND_BASE/.claude/$f" "$dir/$f"
  done
done
```

**NICHT kopieren bei --infra:**
- `stage_*.md`, `patterns/`, `meta/codeKonvention/`, `meta/architekturKonventionen/`
- (= **PROJEKT-TYP-SPEZIFISCH** → nur per `--meta-snapshot {pfad}` deployen)
- `pileOfMud/`-INHALT (NUR die `.gitignore`-Stub wird deployt, siehe PROCESS_FILES)

**NIEMALS kopieren:** wissen/, models/, analysis/, specs/, crumbs/, output/, evidence/, _meta/ (BL-372 Command-Sidecars + BL-302 domain-Meta), pileOfMud/*-Inhalt

### 3c: Full Deploy (/_redeploy --full)

Fuehrt 3a (--all) + 3b (--infra) zusammen aus → an Live-Projekte + Extra-Projekte.

### 3d: All Commands Deploy (/_redeploy --all)

```bash
for f in $OMNICOMMAND_BASE/.claude/commands/*.md; do
  # wie 3a, aber fuer jede Datei
done
```

### 3e: Template Deploy (/_redeploy --template) — NEU

Kopiert ALLES shareable (commands + infra + stage-Metadaten + patterns) → NUR an AgentsArchive Templates:

```bash
TEMPLATE_PROJEKTE=(
  "C:/Users/Administrator/Documents/Projekt/AgentsArchive/.claude_CenCoCo"     # CENCOCD claude_sync slot
  "C:/Users/Administrator/Documents/Projekt/AgentsArchive/.claude_DCSRE"       # DCSRE claude_sync slot
  "C:/Users/Administrator/Documents/Projekt/AgentsArchive/.claude_OmniCommand" # OMNICOMMAND claude_sync slot
)
ALL_SHAREABLE="commands agents meta patterns scripts"
TEMPLATE_FILES="pileOfMud/.gitignore"   # Einzel-Datei-Stubs (NICHT via cp -r — kein Inhalt-Spread)

for dir in "${TEMPLATE_PROJEKTE[@]}"; do
  for share in $ALL_SHAREABLE; do
    mkdir -p "$dir/$share" && cp -r "$OMNICOMMAND_BASE/.claude/$share/" "$dir/$share/"
  done
  for f in $TEMPLATE_FILES; do
    mkdir -p "$(dirname $dir/$f)" && cp "$OMNICOMMAND_BASE/.claude/$f" "$dir/$f"
  done
done
```

**Routing danach:** claude_sync.lua kopiert Templates → Worktrees (automatisch bei Neovim-Start)

### 3f: Meta Deploy (/_redeploy --meta-snapshot {pfad...}) — NEU (projekt-agnostisch)

Kopiert PROJEKT-TYP-SPEZIFISCHE Meta-Files an EXPLIZITE Pfade (Pfade PFLICHT — kein Default-Spread):

```bash
TYP_META_DIRS="meta/architekturKonventionen meta/codeKonvention patterns"
TYP_META_GLOBS="meta/implementation/stage_*.md"

# Pre-Check: Pfade PFLICHT
if [ -z "$EXPLIZITE_PFADE" ]; then
  echo "FEHLER: --meta-snapshot benoetigt explizite Pfade."
  echo "Begruendung: Typ-Meta ist projekt-typ-spezifisch — Default-Spread waere"
  echo "             Contamination-Risiko (Inhalt koennte zu Target-Typ inkompatibel sein)."
  echo "Beispiel: /_redeploy --meta-snapshot C:/.../DCSRE-94_.../"
  exit 1
fi

for dir in $EXPLIZITE_PFADE; do
  for share in $TYP_META_DIRS; do
    mkdir -p "$dir/.claude/$share" && cp -r "$OMNICOMMAND_BASE/.claude/$share/" "$dir/.claude/$share/"
  done
  mkdir -p "$dir/.claude/meta/implementation"
  for f in $OMNICOMMAND_BASE/.claude/meta/implementation/stage_*.md; do
    [ -f "$f" ] && cp "$f" "$dir/.claude/meta/implementation/$(basename $f)"
  done
done
```

**Agnostik-Invariante (HARTE REGEL):**
- `--meta-snapshot` darf KEINE Default-Target-Liste haben (kein `ALLE_PROJEKTE`, kein `EXTRA_PROJEKTE`).
- Pfade kommen ausschliesslich aus expliziten Argumenten.
- Der Command kennt den Typ-Inhalt nicht — der User entscheidet, welche Targets typ-kompatibel sind.

**Kombi-Aufruf:**
- `/_redeploy --full --meta-snapshot {pfad...}` → 3a (--all) + 3b (--infra) + 3f (--meta-snapshot) an `{pfad...}`
- `--full` Standard-Spread (alle Projekte) wird durch explizite Pfade UEBERSTEUERT, wenn `--meta-snapshot` mit dabei ist (Pfade gelten dann fuer ALLE Flags der Invocation).
- `/_redeploy --meta-snapshot {pfad}` ohne `--full` → nur Typ-Meta an `{pfad}`.

**Ausgabe:**
```
_redeploy: {command_name | --all | --infra | --full | --meta-snapshot | --full --meta-snapshot | --template}
Quelle: OmniCommand/.claude/
Ziele:  {N} Projekte ({M} Standard + {K} Extra + {T} Template + {E} Explizit-via-Pfad)

  OK    DCSRE-881_DateiabholungAnalyse_DatenTyp
  OK    DCSRE-882_MetaDaten
  OK    AgentsArchive/.claude_CenCoCo (TEMPLATE — CENCOCD)
  OK    AgentsArchive/.claude_DCSRE (TEMPLATE — DCSRE)
  OK    AgentsArchive/.claude_OmniCommand (TEMPLATE — OMNICOMMAND)
  OK    Kluger/cencoco/.claude (EXTRA)
  SKIP  DCSRE-999_Beispiel (Verzeichnis nicht gefunden)

Ergebnis: {N_OK} OK, {N_SKIP} SKIP
```

---

## Schritt 4: Falls ohne Argumente aufgerufen

Analysiere was sich seit dem letzten Commit geaendert hat und schlage den passenden Modus vor:

```
# Pruefe geaenderte Dateien seit letztem Deploy
geaendert = git diff --name-only HEAD~1..HEAD -- .claude/

# Vorschlag basierend auf Aenderungen:
typ_meta_changed = (meta/architekturKonventionen/ ODER
                    meta/codeKonvention/ ODER
                    meta/implementation/stage_*.md ODER
                    patterns/ geaendert)
universal_infra_changed = (meta/{a,sdf,sc,pr}/ ODER
                           meta/implementation/{guards,handoff-protocol}.md ODER
                           agents/ ODER scripts/ geaendert)
commands_changed = (commands/*.md geaendert)

IF nur commands_changed:
  VORSCHLAG: "/_redeploy --all (nur Commands geaendert)"
ELIF typ_meta_changed AND commands_changed:
  VORSCHLAG: "/_redeploy --full --meta-snapshot {pfad...} (Commands + Typ-Meta geaendert — Pfade PFLICHT bei --meta-snapshot)"
ELIF typ_meta_changed:
  VORSCHLAG: "/_redeploy --meta-snapshot {pfad...} (Typ-Meta geaendert — Pfade explizit angeben, kein Default-Spread)"
ELIF universal_infra_changed:
  VORSCHLAG: "/_redeploy --full (Universal-Infra geaendert — kein Typ-Meta-Risiko)"
ELSE:
  VORSCHLAG: "/_redeploy --all (Default)"

# Zeige Vorschlag + Optionen:
AUSGABE:
  Geaenderte Dateien seit letztem Commit:
    [Liste der .claude/ Aenderungen]

  Vorschlag: {VORSCHLAG}

  Alle Modi:
    /_redeploy {command_name}             → einzelnen Command deployen
    /_redeploy --all                      → alle Commands an alle Projekte
    /_redeploy --infra                    → Universal-Infra an alle Projekte (OHNE Typ-Meta)
    /_redeploy --full                     → Commands + Universal-Infra an alle Projekte
    /_redeploy --meta-snapshot {pfad...}           → Typ-Meta an EXPLIZITE Pfade (Pfade PFLICHT)
    /_redeploy --full --meta-snapshot {pfad...}    → Commands + Universal-Infra + Typ-Meta an EXPLIZITE Pfade
    /_redeploy --template                 → ALLES an AgentsArchive Templates (inkl. stage, patterns)

  Welchen Modus? [Vorschlag mit Enter bestaetigen]
```

---

## Hinweise

- `mkdir -p` wird immer ausgefuehrt — fehlende Ordner werden erstellt
- SKIP (nicht ERROR) wenn das Projekt-Verzeichnis selbst nicht existiert
- OmniCommand selbst ist NICHT in der Deploy-Liste (ist die Quelle)
- Neue Projekte zur Standard-Liste hinzufuegen: Diese Datei editieren (Schritt 2)
- **TEMPLATE_PROJEKTE** bekommen die gleichen shareable Dateien wie normale Projekte
- **Projekt-spezifische Dateien werden NIEMALS ueberschrieben** (wissen, models, analysis, specs, crumbs, output, evidence)

---

## Meta-Snapshot (Offline-Worktree)

`/_redeploy --meta-snapshot {pfad...}` deployt Vault-Meta-Files an explizite Ziel-Pfade.
Zusaetzlich kann der Offline-Snapshot-Cache manuell aktualisiert werden:

```
python .claude/scripts/meta_snapshot.py           → Snapshot Vault-Meta → .claude/meta-cache/
python .claude/scripts/meta_snapshot.py --dry-run → Datei-Count ohne Kopieren
python .claude/scripts/meta_snapshot.py --validate → SHA-256-Pruefung des Snapshots
```

Wann nutzen:
  - Nach Vault-Update (neuer Obsidian-Sync) → Snapshot aktualisieren
  - Vor Worktree-Erstellung auf Maschine ohne Vault-Sync

Refresh-Empfehlung:
  Nach jedem `/_redeploy --infra`: optional `python .claude/scripts/meta_snapshot.py` ausfuehren
  (nicht automatisch — Vault-Zugriff nicht immer verfuegbar)

Offline-Fallback:
  `resolve_vault_meta.py` prueft automatisch `.claude/meta-cache/` wenn Vault nicht erreichbar.
  5-Stufen-Resolution: Local → Vault-Typ → meta-cache-Typ → Vault-Universal → meta-cache-Universal

---

## Schritt 5: Post-Redeploy Health-Self-Check (INV-HEALTH-1, BL-337)

Ein Redeploy tauscht die **Engine** (Commands + Scripts + Infrastruktur), NICHT den
**State** (Vault-Artefakte). Daraus entsteht eine Generations-Luecke: die frische Engine
erwartet ein neues Artefakt-Format, der mitgewanderte Alt-Vault traegt es aber noch nicht
(Engine-Austausch am fahrenden Auto). Darum gilt nach JEDEM Redeploy:

> **PFLICHT (INV-HEALTH-1):** Nach Abschluss des Deploys MUSS gegen den Ziel-Vault
> `/_health_orchestrate --mode=report-only` laufen — der Self-Check, BEVOR der frisch
> getauschte Motor den State beruehrt. Der Redeploy ist erst dann abgeschlossen, wenn
> der Health-Self-Check gruen ist (kein offener Format-Drift) ODER die empfohlene Heilung
> ausgefuehrt wurde.

**Ablauf:**
```
1. Deploy ausfuehren (Schritt 3).
2. /_health_orchestrate --mode=report-only --vault={Ziel-Vault}
3a. CLEAN (kein offener Format-Drift) → Redeploy abgeschlossen.
3b. DRIFT-Befund → heal-Empfehlung ausgeben (z.B. {stamp, slim, reconcile}) +
    produktive Nutzung des Ziel-Vaults BLOCKIEREN bis geheilt ODER expliziter
    Owner-Override. Heilung via /_health_orchestrate --mode=heal --vault={Ziel-Vault}
    (safety_class-gegated — auto direkt / lock unter vault_lock / hil mit Freigabe).
```

**Maschinelle Erzwingung:** `guard_redeploy_health.py` (BL-337) erzwingt diese Kette —
ein Redeploy ohne nachfolgenden Health-Lauf wird gemeldet/geblockt. Das Skript ist die
strukturelle Absicherung; diese Sektion ist die menschen-lesbare Doktrin dazu. Bei
git-losen Vaults (T9, `Documents/OmniCommand` ohne `.git`) gilt der report-only-Lauf als
Format-Drift-Pruefung weiterhin — nur der Commit-Seam ist dort N/A.

---

## Schritt 6: PFLASTER `--with-config {source_project}` (BL-366 — Fresh-Project Instanz-Config-Bootstrap)

**Problem (Eigentums-Grenze):** OmniCommand besitzt die UNIVERSAL-Infra (commands/scripts/agents/
workflows/meta-{a,sdf,sc,pr}). Die INSTANZ-Metadaten (`config/vault-routing.json`, `.vault_root`,
`config/layers.yaml`) gehoeren dem jeweiligen PROJEKT-Setup — sie sind ARCH-N11-blacklisted und kommen
NICHT aus OmniCommand. Fuer BESTEHENDE Projekte korrekt. Fuer FRISCHE Projekte (kein vorheriges `.claude/`)
bleibt nach `/_redeploy` eine HALBE Engine zurueck (Universal da, Instanz-Config fehlt) → vault-Resolver
faellt auf falschen Heuristik-Pfad → `/_backlog`/A/IDF/SDF resolven den falschen Vault.

**PFLASTER (interim, bis das Proper-Init-Modul / BL-332 steht):**
```
/_redeploy --full --with-config {source_project_dir}   {target_project_dir}
```
Nach dem Universal-Deploy (3a+3b) kopiert `--with-config` die 3 Instanz-Config-Files
(`config/vault-routing.json`, `.vault_root`, `config/layers.yaml`) aus `{source_project_dir}/.claude/`
ins `{target_project_dir}/.claude/`. So ist das frische `.claude/` *komplett + lauffaehig*.

**HOECHSTE VORSICHT (harte Regel):** `{source_project_dir}` MUSS ein Geschwister-Projekt DESSELBEN
PROJEKT-TYPS sein (DCSRE-Worktree → ein anderer DCSRE-Worktree bzw. das Haupt-`DCSRE/.claude/`; NIE
OmniCommand-Config an ein DCSRE-Ziel — die Detection-Patterns/.vault_root sind typ-spezifisch, falsche
Quelle = Writes in den falschen Vault). Quelle ist PFLICHT (kein Default-Spread, analog --meta-snapshot).
`--with-config` ohne `{source}` → FEHLER.

**Logik:**
```
for f in config/vault-routing.json .vault_root config/layers.yaml:
  if exists({source}/.claude/$f): cp {source}/.claude/$f {target}/.claude/$f
  else: WARN "{f} fehlt auch in der Quelle — manuell pruefen"
LOG: "[REDEPLOY --with-config] Instanz-Config aus {source} → {target} ({n} Files). Vault-Resolver jetzt korrekt."
```

**Proper-Fix (NICHT dieser Pflaster):** ein dediziertes Init-/Geburts-Modul (BL-332 InitOrchestrate) das
ein frisches `.claude/` fresh UND komplett erzeugt (Instanz-Config aus Projekt-Typ-Template + .vault_root-
Pin). `/_redeploy` bleibt dann reiner UPDATE-Mechanismus. Siehe BL-366 / BL-332.
