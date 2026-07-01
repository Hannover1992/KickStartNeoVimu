---
type: building-block
status: active
version: 1.1.0
created: 2026-05-01
updated: 2026-05-02
feature: SemantischePatternLibrary
bl_item: BL-153
ak_ref: AK-D-7
chain_position: standalone (M2 Project-Maturity-Command, einmalig)
arch_delta: ARCH-Delta-6
---

# /_SL_init — Einmalige Initialisierung der SemanticLibrary

**Status:** v1.1.0 (ARCH-Delta-6: layers.yaml dynamisch, Vision V5 _global/)
**Actor:** SEMANTIC-INITIALIZER
**Zweck:** Scannt bestehenden Projektcode layer-weise (parallele Wellen) und extrahiert
semantische Konzepte — Naming-Konventionen, Domänenbegriffe, Interface-Vokabular — in
`{VAULT_ROOT}/Libraries/SemanticLibrary/`. Einmaliger Bootstrap; danach wächst die Library durch
`_PT_extract` und manuelle Ergänzungen.

> **Frequenz:** EINMALIG bei Projektstart (M2-Kommando). Kein Auto-Trigger.
> Re-Run nur mit `--force`.

---

## Aufruf

```
/_SL_init [--scope PFAD] [--force] [--dry-run]
```

| Parameter   | Pflicht | Default            | Beispiel                        |
|-------------|---------|--------------------|---------------------------------|
| `--scope`   | NEIN    | Gesamte Codebase   | `--scope Sources/Backend/`      |
| `--force`   | NEIN    | false              | `--force` (Überschreibt bestehende SL) |
| `--dry-run` | NEIN    | false              | `--dry-run` (Report, kein Schreiben) |

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_SL_init (AK-D-7, BL-153) — v1.1.0 (ARCH-Delta-6)       ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {vault_root}/config/layers.yaml PRIMAER (ARCH-N7 Vault-First)    ║
║    .claude/config/layers.yaml FALLBACK (Repo-Default OmniCommand)   ║
║    {scope}/**/* gemaess path_globs pro Layer (aus layers.yaml)      ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_index.md (Duplikat-Guard)             ║
║    .claude/config/vault-routing.json (VAULT-Pfad)                   ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md  (PRIORITAET)║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/naming-conventions.md ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/domain-terms.md       ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_index.md (aktualisiert)               ║
║    .claude/wissen/sl_init_report_{DATUM}.md (Scan-Report)           ║
║    Bei --dry-run: NUR sl_init_report_{DATUM}.md                     ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    Libraries/PatternLibrary/ (separate Library)                      ║
║    _manifest.md (kein Pipeline-State — standalone)                  ║
║                                                                      ║
║  ACTOR: SEMANTIC-INITIALIZER (Wellen-Pattern)                        ║
║  MODELL-TIER: sonnet (reflektives Reasoning für Semantik-Extraktion) ║
║  INVARIANTEN:                                                        ║
║    INV-SL-INIT-1: Einmalig — Guard ohne --force (Duplikat-Schutz)  ║
║    INV-SL-INIT-2: NON-BLOCKING pro Layer — leerer Layer → Skip      ║
║    INV-SL-INIT-3: Wellen-Pattern — parallele Worker pro Layer       ║
║    INV-SL-INIT-4: --dry-run MUSS verfügbar sein                     ║
║    INV-SL-INIT-5: Konsolidierungs-Welle NACH allen Layer-Wellen     ║
║    INV-SL-INIT-6: layers.yaml PFLICHT — Fallback wenn fehlt: HiL   ║
║    INV-SL-INIT-7: _global/ PRIORITAET — globale SR-* zuerst        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Chain-Position

```
Einmalig (M2 Project-Maturity-Command):
  User → [/_SL_init] → {VAULT_ROOT}/Libraries/SemanticLibrary/ befüllt
                      → _SDF_berater_patternBrief hat Semantik-Basis

Danach (laufend):
  _PT_extract → einzelne semantische Begriffe ergänzen
  Manuell    → /_PT_update für neue Domänenbegriffe
```

---

## Layer-Definition (ARCH-Delta-6: dynamisch aus layers.yaml + ARCH-N7 Vault-First)

> **ARCH-Delta-6 (2026-05-02):** Layer-Liste wird DYNAMISCH geladen — NICHT hardcoded.
> Phase 0 nutzt **Vault-First-Resolution** (ARCH-N7 + ARCH-Delta-8 NEW-U2):
>   1. PRIMAER: `{vault_root}/config/layers.yaml` (projekt-spezifisch)
>   2. FALLBACK: `.claude/config/layers.yaml` (Repo-Default OmniCommand-Self)
> OmniCommand-Layer: COMMANDS, BERATER, ORCHESTRATOR, META, SCRIPTS, HOOKS.
>
> DCSRE BE-* Layer sind archiviert ({VAULT_ROOT}/Libraries/SemanticLibrary/_archive_DCSRE/) —
> fuer OmniCommand nicht relevant (kein .cs/.ts/.py Codebase).

```
# Pseudocode — Layer-Resolution (Phase 0)
# ARCH-N7 Vault-First (Konsistenz mit _PT_arch_init):
# 1. {vault_root}/config/layers.yaml  ← PRIMAER (projekt-spezifisch)
# 2. .claude/config/layers.yaml       ← FALLBACK (Repo-Default fuer OmniCommand-Self)
vault_root = subprocess(.claude/scripts/resolve_vault_root.py).stdout.strip()
layers_yaml_path = "{vault_root}/config/layers.yaml"
IF NOT exists(layers_yaml_path):
  layers_yaml_path = ".claude/config/layers.yaml"  # FALLBACK
  Logge: "[SL_init] Vault-Layers fehlt — Fallback auf Repo-Default ({layers_yaml_path})"

IF layers_yaml_path existiert:
  LAYERS = parse(layers_yaml_path).layers
  # Felder pro Layer: id, label, path_globs, id_prefix, description, vault_folder
  Logge: "[SL_init] layers.yaml geladen — {|LAYERS|} Layer: {[layer.id]}"
ELSE:
  # Fallback: HiL fragen
  → HiL: "layers.yaml nicht gefunden unter {layers_yaml_path}. Bitte Layer-Liste angeben
          ODER Pfad zu layers.yaml."
  IF HiL antwortet mit Pfad:
    LAYERS = parse(hil_pfad).layers
  ELSE IF HiL antwortet mit Layer-IDs:
    LAYERS = [{id: x, path_globs: ["**/*"], vault_folder: "_project/"+x} for x in hil_ids]
  ELSE:
    → STOPP: "layers.yaml fehlt und kein Fallback moeglich."

# OmniCommand-Layer (Referenz, wird durch layers.yaml ueberschrieben):
# COMMANDS   → .claude/commands/**/*.md
# BERATER    → .claude/commands/**/*_berater_*.md
# ORCHESTRATOR → .claude/commands/**/*orchestrate*.md
# SCRIPTS    → .claude/scripts/**/*
# META       → .claude/config/**/*  + CLAUDE.md
# HOOKS      → .claude/settings*.json
```

---

## Vision V5 — _global/ Prioritaet (ARCH-Delta-6)

> **Kern-Insight:** 90% des Extraktions-Volumens sollte in `_global/` landen, NICHT in
> layer-spezifischen Ordnern. Layer-spezifische SR-* sind die AUSNAHME, nicht die Regel.

**Algorithmus-Prinzip fuer Worker:**

```
FRAGE PRO KONZEPT: "Gilt diese Regel in ALLEN Layern?" → JA → _global/
                   "Gilt NUR in diesem Layer?"          → JA → _project/{LAYER}/

Globale Kandidaten (fast immer _global/):
  - Naming-Konventionen (PascalCase, camelCase, Praefixe)
  - Kommentar-Konventionen (wo Kommentare hin, Sprache)
  - Datei-Struktur-Normen (ein Command pro Datei, VERTRAG-Block)
  - LIEST/SCHREIBT-Vokabular
  - Status-Werte (DONE/PARTIAL/OPEN/DEFERRED)

Layer-spezifische Kandidaten (echte Ausnahmen):
  - BERATER: State-Transition-spezifische Felder (unique fuer Berater)
  - ORCHESTRATOR: Wellen-Struktur-Terminologie (unique fuer Orchestratoren)
  - HOOKS: INV-Check-Vokabular (spezifisch fuer Hook-Layer)
  - SCRIPTS: Exit-Code-Semantik (spezifisch fuer Scripts)
```

> Worker-Instruktion (INV-SL-INIT-7): Vor jedem SR-Eintrag explizit prufen:
> "Koennte dieser SR-* globale Gueltigkeit haben?" — wenn unklar → GLOBAL.
> Lieber zu viel in _global/ als zu viel layer-spezifisch.

---

## Ablauf in 3 Phasen

---

### Phase 0: layers.yaml laden + Guard + Laufzeit-Hinweis

```
# Schritt 0a: layers.yaml laden (ARCH-Delta-6, INV-SL-INIT-6, ARCH-N7 Vault-First)
# ARCH-N7 Vault-First (Konsistenz mit _PT_arch_init):
# 1. {vault_root}/config/layers.yaml  ← PRIMAER (projekt-spezifisch)
# 2. .claude/config/layers.yaml       ← FALLBACK (Repo-Default fuer OmniCommand-Self)
vault_root = subprocess(.claude/scripts/resolve_vault_root.py).stdout.strip()
layers_yaml_path = "{vault_root}/config/layers.yaml"
IF NOT exists(layers_yaml_path):
  layers_yaml_path = ".claude/config/layers.yaml"  # FALLBACK
  Logge: "[SL_init] Vault-Layers fehlt — Fallback auf Repo-Default ({layers_yaml_path})"

IF layers_yaml_path existiert:
  LAYERS = parse(layers_yaml_path).layers   # id, path_globs, vault_folder, id_prefix
  Logge: "[SL_init] layers.yaml geladen — {|LAYERS|} Layer: {[layer.id for layer in LAYERS]}"
ELSE:
  # HiL fragen (kein Silent-Fallback bei fehlender Config)
  → HiL: "layers.yaml nicht gefunden unter {layers_yaml_path}.
          Optionen:
          (A) Pfad zur layers.yaml angeben
          (B) Layer-IDs komma-separiert eingeben (Codebase-Detection)
          (C) Abbruch"
  IF HiL → Option A: LAYERS = parse(hil_pfad).layers
  IF HiL → Option B: LAYERS = [{id: x, path_globs:["**/*"], vault_folder:"_project/"+x} for x in hil_ids]
  IF HiL → Option C: → STOPP (User-Entscheidung)

# Schritt 0b: Duplikat-Guard (INV-SL-INIT-1)
# Guard prueft layer._index.md pattern_count > 0 (nicht mehr README.md-Existenz)
befuellte_layer = [L for L in LAYERS IF _project/{L.vault_folder}/_index.md.pattern_count > 0]
IF len(befuellte_layer) > 0:
  IF --force NICHT gesetzt:
    → STOPP: "SemanticLibrary teilweise befuellt (Layer: {befuellte_layer}).
              Verwende --force fuer Re-Init."
  ELSE:
    → WARNUNG: "--force aktiv. Bestehende Semantik in {befuellte_layer} wird ueberschrieben."

# Schritt 0c: Laufzeit-Hinweis PFLICHT
Logge: "[SL_init] START — {|LAYERS|} Layer werden parallel gescannt."
Logge: "[SL_init] Scope: {scope}. Geschätzte Dauer: 3-8 Minuten."
Logge: "[SL_init] Dry-run: {true|false}"
```

---

### Phase 1: WELLE — Parallele Layer-Worker (Sonnet)

**Team Lead spawnt N Sonnet-Worker PARALLEL — einen pro Layer.**

Skalierung: bis zu 9 Worker gleichzeitig (alle Layer in einer Welle).

**Jeder Worker:**

```
WORKER INPUT:
  layer_id    = z.B. "BE-CONT"
  pfad_hint   = z.B. ["Controller"]
  glob        = z.B. "**/*Controller*.cs"
  scope       = {scope}
  dry_run     = {true|false}
  vault_path  = aus vault-routing.json

WORKER AUFGABE (Semantik-Extraktion):

  1. Sammle Dateien: glob({scope}/{glob})
     IF keine Dateien gefunden → Logge "[SL_init][{layer}] SKIP — keine Dateien" → EXIT

  2. Analysiere Naming-Konventionen:
     - Klassen-Suffixe / Präfixe (z.B. *Controller, I*Service, *Repository)
     - Methoden-Naming (z.B. Get*/Create*/Handle*/Validate*)
     - Parameter-Naming (typische Namen pro Kontext)
     - Interface-Konventionen (z.B. I-Prefix ja/nein, Abstract-Basis)
     Mindestens 5 konkrete Beispiele pro Konvention mit Datei-Referenz.

  3. Extrahiere Domänenbegriffe:
     - Fachbegriffe aus Klassen-/Methodennamen (Substantive = Konzepte)
     - Ubiquitous Language des Projekts (welche Begriffe wiederholen sich?)
     - Abkürzungen + ihre Bedeutung (z.B. "QDVS" → ableiten aus Kontext)
     - Layer-spezifisches Vokabular
     Mindestens 8 Begriffe mit Definition + Herkunft-Referenz.

  4. Schreibe (NICHT bei --dry-run):

     Datei 1: {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{layer_id}/naming-conventions.md
     ---
     type: semantic-pattern
     subtype: naming-conventions
     layer: {layer_id}
     library: SemanticLibrary
     status: DRAFT
     created: {DATUM}
     source: /_SL_init v1.0.0
     files_scanned: {N}
     ---
     # {layer_id} — Naming Conventions

     ## Klassen-Naming
     | Konvention | Beispiele | Bedeutung |
     |---|---|---|
     | {pattern} | {Datei:Klasse} | {was signalisiert dieses Naming} |

     ## Methoden-Naming
     | Präfix/Suffix | Beispiele | Kontext |
     |---|---|---|

     ## Parameter-Naming
     | Name | Typ | Konvention |
     |---|---|---|

     ## Interface-Konventionen
     {Freitext, max 3 Sätze}

     ## Anomalien / Ausnahmen
     {Abweichungen vom Muster — wichtig für zukünftige Workers}


     Datei 2: {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{layer_id}/domain-terms.md
     ---
     type: semantic-pattern
     subtype: domain-terms
     layer: {layer_id}
     library: SemanticLibrary
     status: DRAFT
     created: {DATUM}
     source: /_SL_init v1.0.0
     terms_count: {N}
     ---
     # {layer_id} — Domain Terms

     ## Begriffe
     | Begriff | Definition (aus Code abgeleitet) | Herkunft | Layer-spezifisch? |
     |---|---|---|---|
     | {term} | {was es bedeutet} | {Klasse/Methode} | ja/nein |

     ## Abkürzungen
     | Abkürzung | Bedeutung | Beispiel |
     |---|---|---|

     ## Ubiquitous Language (Layer-Kontext)
     {3-5 Sätze: welche Sprache spricht dieser Layer?}

  5. SendMessage an "team-lead":
     "[SL_init][{layer_id}] DONE — {N} Konventionen, {M} Begriffe. files_scanned={K}"
     ODER
     "[SL_init][{layer_id}] SKIP — keine Dateien"
```

---

### Phase 2: KONSOLIDIERUNGS-WELLE (1 Sonnet-Worker)

**Nach Abschluss aller Layer-Worker:**

```
WORKER AUFGABE:

  1. Lies alle frisch erstellten domain-terms.md aller Layer
  2. Identifiziere layer-übergreifende Begriffe:
     - Begriffe die in ≥2 Layern auftauchen → global
     - Widersprüche zwischen Layern → dokumentieren
     - Kern-Domänenbegriffe des Projekts (Top 20)

  3. Schreibe {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md:
     ---
     type: semantic-pattern
     subtype: global-glossary
     layer: _global
     library: SemanticLibrary
     status: DRAFT
     created: {DATUM}
     source: /_SL_init v1.0.0 (Konsolidierung)
     layers_consolidated: {[layer_ids mit Inhalt]}
     ---
     # Global Domain Glossary

     > Automatisch konsolidiert aus Layer-Scans. Manuell pflegbar.

     ## Kern-Domänenbegriffe (Top {N})
     | Begriff | Definition | Vorkommt in Layern | Kanonischer Layer |
     |---|---|---|---|

     ## Layer-übergreifende Naming-Regeln
     {Regeln die in ALLEN Layern gelten — z.B. PascalCase Klassen, I-Prefix Interfaces}

     ## Widersprüche / Inkonsistenzen
     | Begriff/Regel | Layer A sagt | Layer B sagt | Empfehlung |
     |---|---|---|---|

  4. SendMessage an "team-lead":
     "[SL_init][_global] DONE — {N} globale Begriffe, {K} Widersprüche"
```

---

### Phase 3: Index + Report

```
# Index aktualisieren (NICHT bei --dry-run)
Lies {VAULT_ROOT}/Libraries/SemanticLibrary/_index.md
Ergänze/aktualisiere Einträge für alle befüllten Layer:
  ---
  initialized_at: {DATUM}
  layers_active: [{layer_ids mit Inhalt}]
  layers_empty: [{layer_ids SKIP]}
  global_glossary: DRAFT
  total_terms: {Summe aller domain-terms.md terms_count}
  ---

# Scan-Report
Schreibe .claude/wissen/sl_init_report_{DATUM}.md:
  ---
  scan_date: {DATUM}
  scope: {scope}
  dry_run: {true|false}
  layers_done: {N}
  layers_skipped: {K}
  total_conventions: {Summe}
  total_terms: {Summe}
  ---
  # SL_init Report {DATUM}

  ## Ergebnis pro Layer
  | Layer | Status | Konventionen | Begriffe | Dateien gescannt |
  |---|---|---|---|---|
  | BE-CONT | DONE | {N} | {M} | {K} |
  | BE-TEST | SKIP | — | — | 0 |
  ...

  ## Global Glossary
  {N} Begriffe konsolidiert. {K} Widersprüche dokumentiert.

  ## Empfehlungen
  - Layer mit SKIP: manuell prüfen ob Pfad korrekt
  - Widersprüche: {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md → Sektion "Widersprüche"
  - Nächster Schritt: _SDF_berater_patternBrief greift ab sofort auf SemanticLibrary zu

# Abschluss-Log
Logge: "[SL_init] DONE — {layers_done} Layer befüllt, {layers_skipped} übersprungen."
Logge: "[SL_init] SemanticLibrary: {VAULT_ROOT}/Libraries/SemanticLibrary/"
Logge: "[SL_init] Report: .claude/wissen/sl_init_report_{DATUM}.md"
```

---

## Output-Struktur (nach /_SL_init)

```
{VAULT_ROOT}/Libraries/SemanticLibrary/
├── _index.md                          ← aktualisiert (layers_active, total_terms)
├── _global/
│   ├── README.md                      ← bereits vorhanden
│   └── domain-glossary.md             ← NEU (Phase 2 Konsolidierung)
└── _project/
    ├── BE-CONT/
    │   ├── README.md                  ← bereits vorhanden
    │   ├── naming-conventions.md      ← NEU
    │   └── domain-terms.md            ← NEU
    ├── BE-CORE/
    │   ├── naming-conventions.md      ← NEU
    │   └── domain-terms.md            ← NEU
    ├── BE-DOMAIN/
    │   ├── naming-conventions.md      ← NEU
    │   └── domain-terms.md            ← NEU
    ├── BE-DTO/  ...
    ├── BE-MAP/  ...
    ├── BE-MID/  ...
    ├── BE-AUTH/ ...
    ├── BE-MIGRATION/ ...
    └── BE-TEST/ ...
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| Layer-Verzeichnis/Dateien nicht gefunden | SKIP (NON-BLOCKING) — Logge + weiter |
| SemanticLibrary bereits befüllt (ohne --force) | STOPP mit Meldung (INV-SL-INIT-1) |
| SemanticLibrary bereits befüllt (mit --force) | WARNUNG + überschreiben |
| Worker findet < 3 Dateien | Trotzdem extrahieren — weniger Beispiele erlaubt |
| Konsolidierungs-Worker: alle Layer SKIP | domain-glossary.md = EMPTY_SEED mit Hinweis |
| --dry-run | NUR Report, KEIN Schreiben in Libraries/ |
| Vault-Pfad nicht auflösbar | FEHLER + STOPP (Vault-Routing Pflicht) |

---

## Abgrenzung

```
/_SL_init        = SemanticLibrary EINMALIG befüllen (Bootstrap, code-scan)
/_PT_arch_init        = PatternLibrary einmalig befüllen (strukturelle Patterns)
/_PT_extract     = Einzelnes Pattern extrahieren (laufend, nach SC_implement)
/_PT_update      = Pattern manuell registrieren/upgraden

Beide /_SL_init + /_PT_arch_init sind M2-Commands:
  Einmalig, rechenintensiv, bootstrappen die Libraries für den laufenden Betrieb.
  Danach übernehmen _PT_extract und manuelle Updates.
```

---

## Verwandt

- `_SDF_berater_patternBrief` — konsumiert SemanticLibrary (LIEST `_project/{LAYER}/`)
- `_I_patternLibrary` — konsumiert SemanticLibrary (LIEST `_project/{LAYER}/`)
- `_PT_arch_init` — Schwester-Command für PatternLibrary
- `{VAULT_ROOT}/Libraries/SemanticLibrary/_index.md` — Ziel-Index
- `{VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md` — Global-Output
