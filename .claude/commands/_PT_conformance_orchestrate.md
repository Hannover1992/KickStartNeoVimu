---
type: command
feature: PatternKonformitaetOrchestrator
bl_item: BL-340
batch: batch_PL3
created: "2026-06-23"
updated: "2026-06-23"
status: active
version: 1.0.0
kernel_ref: "_PostBatch_PatternConformance"
kernel_baseline_sha: "34e2f277b8da93213b556afe39c0923f63ad6907"
ak_scope: "PL3 (Integration-Schicht, 4 Items — Command vollstaendig)"
ak_built_pl2:
  - "AK-6-PL-1 (Layer-Filter, fnmatch gegen _project/{LAYER}/ Basename)"
  - "AK-3-PL-1/AK-5-PL-1 (Teilscan: echter Pre-Filter selektierte_achsen VOR Kern-Invoke)"
  - "AK-11-PL-1 (NL-Scope-Hint, fuzzy-match layers.yaml label+id, optional/tentative)"
ak_built_pl3:
  - "AK-4-PL-1 (Standalone-Entry-Vollausbau: STANDALONE_MODE-Log Phase 1 + Phase 0/1 manifest-frei bestaetigt, INV-M4-BATCH-OPT-1)"
  - "AK-1-PL-1 (scope=branch Default-Verdrahtung vollstaendig: Phase-2-Log + VERTRAG-Bestaetigung, End-to-End)"
  - "AK-5-PL-1 (Teilscan-Vollimpl: selektierte_achsen Phase-1→3b→5 Propagation verifiziert/kommentiert)"
  - "AK-12-PL-1 (achsen-Default alle 4: Default Phase-1 bestaetigt, W14-NON-BLOCKING-Greenfield dokumentiert)"
---

# _PT_conformance_orchestrate (BL-340, batch_PL3 — Command vollstaendig v1.0.0)

**Zweck:** Duenner Standalone-Orchestrator-Mantel um den M-4-Kern `_PostBatch_PatternConformance`.
Schliesst drei strukturelle Luecken: (F-02/W7) fehlende Scope-Achsen `branch`/`commits`,
(F-03/W9) kein Entry-Point ohne DF_BATCH_STATE, (F-04/W10) HiL=off = Auto-Apply statt read-only.

**Kern-Invariante AK-7 (diff=0):** `_PostBatch_PatternConformance.md` wird NIEMALS vom Mantel
veraendert. Nach jedem Build muss gelten:
```
git diff 34e2f277b8da93213b556afe39c0923f63ad6907 -- .claude/commands/_PostBatch_PatternConformance.md
```
Ergebnis = leer. Jede Aenderung am Kernel verletzt DoD-7 und bricht den Build.

---

## VERTRAG (PT-CMD-001, S1)

```
╔══════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _PT_conformance_orchestrate (BL-340, Standalone-Mantel)        ║
╠══════════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                                  ║
║    Git-State (unstaged diff / HEAD..branch / commit-range)              ║
║    DF_BATCH_STATE → batch_current    (OPTIONAL — kein Fehler wenn fehlt) ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/**  (via Kern-Invoke)           ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/** (via Kern-Invoke)           ║
║    {VAULT_ROOT}/Libraries/DomainLibrary/**   (via Kern-Invoke)           ║
║    {VAULT_ROOT}/Libraries/FactoringLibrary/** (via Kern-Invoke)          ║
║    _session_params.md → GLOBAL_HIL  (Kern liest; Mantel ueberschreibt   ║
║      bei mode=report via hil_mode_override=report)                      ║
║                                                                          ║
║  SCHREIBT:                                                               ║
║    Transienter Report (Konsolenausgabe / Verdikt pro Achse)              ║
║    Optionale PL-Item-Vorschlaege bei Findings (WARN/BLOCKER)             ║
║                                                                          ║
║  SCHREIBT NICHT (KRITISCH):                                              ║
║    .claude/commands/_PostBatch_PatternConformance.md  ← NIEMALS (AK-7,  ║
║      INV-M4-KERNEL-1, DoD-7). Kernel-SHA 34e2f277 muss diff=0 bleiben.  ║
║    DF_BATCH_STATE.*     (Standalone-Modus ist read-only, AK-4)          ║
║    PATTERN_CONFORMANCE_STATE.*  (read-only Doktrin QG-2; nur PostBatch  ║
║      Slot schreibt das)                                                  ║
║    ARCHITECT_ESCALATION_QUEUE   (nur Report-Sektion statt Queue-Write;  ║
║      Mantel gibt Findings als Report aus, keine Manifest-State-Write)   ║
║                                                                          ║
║  ARGUMENTE:                                                              ║
║    --scope  unstaged|slice|branch|commits   (Default: unstaged)         ║
║    --range  A..B                            (nur bei --scope commits)   ║
║    --vs     {branch}                        (nur bei --scope branch,    ║
║               Default: develop)                                         ║
║    --mode   report|apply                    (Default: report)           ║
║    --achsen pattern,semantic,domain,factoring  (Default: alle 4)        ║
║    --layer  {GLOB}                          (Default: alle Layer)       ║
║    --nl_hint  {freier Text}                 (AK-11, PL2-optional,       ║
║      tentative/border — fuzzy-match gegen layers.yaml label+id)        ║
║                                                                          ║
║  MODELL-TIER: floor (haiku) — Pattern-Index-Lookup + Diff-Analyse       ║
║    (analog Kern-Tier)                                                    ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
Skill(_PT_conformance_orchestrate, args="[--scope branch|commits|unstaged|slice] [--range A..B] [--vs {branch}] [--mode report|apply] [--achsen pattern,semantic,...] [--layer {GLOB}] [--nl_hint {freier Text}]")
```

**Primar-Use-Case (b2-Reviewer-Modus, DCSRE-1944):**
```
Skill(_PT_conformance_orchestrate, args="--scope branch --mode report")
```

---

## Pseudocode-Struktur (PT-CMD-003, S2)

### Phase 0: Idempotenz-Guard (PT-CMD-007)

```
# AK-4 (INV-M4-BATCH-OPT-1): Phase 0 liest KEIN _manifest.md / DF_BATCH_STATE.
# Der Command ist Standalone-faehig ohne Pipeline-Kontext — kein Manifest-Pflicht-Read.
# Batch-Kontext wird OPTIONAL erst in Phase 5 gelesen (lies_optional ?? null).

# Resume-Erkennung: verhindert Doppel-Lauf bei Session-Unterbrechung
resume_marker = lies_optional("{WORKTREE_PATH}/.claude/output/pt_conformance_resume.json")

IF resume_marker != null AND resume_marker.status == "RUNNING":
  Logge: "[PT_conformance] WARN: Resume-Marker aktiv (letzter Lauf unterbrochen?)"
  Logge: "[PT_conformance] Marker: {resume_marker.started_at} / scope={resume_marker.scope}"
  # Idempotenz: fortfahren (neuer Lauf ueberschreibt; Marker wird in Phase 6 geloescht)
  # Kein Hard-Stop — Resume-Hint fuer Nachvollziehbarkeit
ELSE:
  schreibe resume_marker: {status: "RUNNING", started_at: ISO8601, scope: scope, mode: mode}

Logge: "[PT_conformance] Phase 0 PASS (Idempotenz-Guard, PT-CMD-007) — kein Manifest-Read (AK-4)"
```

### Phase 1: Argument-Parsing

```
# AK-4 (INV-M4-BATCH-OPT-1): Phase 1 liest KEIN _manifest.md / DF_BATCH_STATE.
# Alle Defaults werden aus Args aufgeloest — kein Manifest-Pflicht-Read hier.
# Batch-Kontext wird spaeter in Phase 5 OPTIONAL nachgeladen (lies_optional ?? null).

# Defaults (Standalone-Modus)
scope    = args.scope    ?? "unstaged"
mode     = args.mode     ?? "report"     # WICHTIG: Standalone-Default = report (AK-9, PT-CMD-014)

# AK-12 (PL3): Default = alle 4 Achsen (pattern/semantic/domain/factoring).
# W14 BESTAETIGT: domain+factoring sind Greenfield-tolerant (default-severity INFO, NON-BLOCKING).
# → Default=alle-4 laeuft IMMER durch ohne zu stoppen bei leeren Greenfield-Libs.
achsen   = args.achsen   ?? ["pattern", "semantic", "domain", "factoring"]  # alle 4 (AK-12, W14)

layer    = args.layer    ?? "*"          # alle Layer (AK-6)
nl_hint  = args.nl_hint  ?? null         # freier NL-Scope-Hint (AK-11, PL2-optional, tentative/border)
range    = args.range    ?? null         # nur bei scope=commits

# AK-1 (PL3): scope=branch ist der primaere Reviewer-Use-Case (b2-Modus, DCSRE-1944).
# Default scope=unstaged bleibt fuer Schnell-Check; explizit --scope branch fuer Reviewer.
# Phase 2 hat vollstaendige branch-Logik (git diff HEAD..{vs_branch}) implementiert (W7).
vs       = args.vs       ?? "develop"    # nur bei scope=branch (AK-1, Default: develop)

Logge: "[PT_conformance] Phase 1: scope={scope} mode={mode} achsen={achsen} layer={layer} nl_hint={nl_hint ?? 'null'}"

# AK-4 (PL3): Standalone-Modus-Erkennung — kein Manifest erforderlich.
# batch_kontext wird in Phase 5 aufgeloest (lies_optional ?? null); hier nur Hinweis.
Logge: "[PT_conformance] Phase 1: STANDALONE_MODE aktiv — kein DF_BATCH_STATE-Pflicht-Read (AK-4, INV-M4-BATCH-OPT-1)"

# AK-5 (PL3): selektierte_achsen = achsen aus diesem Parsing (Default alle 4).
# Propagation: Phase 1 (hier) → Phase 3b (selektierte_achsen = achsen) → Phase 5 (kern_args.achsen).
# Teilscan via --achsen pattern,semantic deaktiviert domain+factoring in Phase 3b (INV-M4-FILTER-1).
selektierte_achsen_preview = achsen  # wird in Phase 3b finalisiert (AK-5 Propagations-Anker)

# Argument-Validierung
IF scope == "commits" AND range == null:
  FEHLER: "--scope commits erfordert --range A..B"
  EXIT FAIL.

IF mode NOT IN ["report", "apply"]:
  FEHLER: "--mode muss 'report' oder 'apply' sein"
  EXIT FAIL.
```

### Phase 2: Scope-Ermittlung — DIRTY-Scope-Adapter (PT-CMD-013, S4)

```
# Scope-Ermittlung laeuft VOR Kern-Invoke im Mantel.
# Ergebnis = Datei-Liste fuer Kern-Input (INV-M4-SCOPE-1).

IF scope == "unstaged":
  # Kern-Default — kein Mantel-Adapter noetig
  datei_liste = "unstaged"   # Kern berechnet git_unstaged_files() selbst
  Logge: "[PT_conformance] Scope=unstaged: Kern-Default (kein Mantel-Adapter)"

ELIF scope == "slice":
  # Kern-Default fuer Slice-Scope — kein Mantel-Adapter noetig
  datei_liste = "slice"   # Kern berechnet slice_files() selbst
  Logge: "[PT_conformance] Scope=slice: Kern-Default (kein Mantel-Adapter)"

ELIF scope == "branch":
  # AK-1 (PL3/W7): Branch-Total — git diff HEAD..{vs_branch}
  # Praezedenz: _SL_pre_pr --vs {branch} (A3-Architektur-Entscheidung, BL-340)
  # Referenz-Implementierung: .claude/commands/_SL_pre_pr.md (OQ2: REFERENZIEREN, nicht absorbieren)
  # End-to-End Pfad: --scope branch → Phase 2 (hier) → datei_liste → Phase 3 Filter → Phase 5 Kern.
  # vs-Default (W7): "develop" (gesetzt in Phase 1; ueberschreibbar via --vs {branch}).
  vs_branch = vs  # Default: "develop" (AK-1, Phase 1 vs=args.vs??develop)
  diff_output = Bash("git diff HEAD..{vs_branch} --name-only")
  datei_liste = diff_output.splitlines()
  Logge: "[PT_conformance] Scope=branch (HEAD..{vs_branch}): {|datei_liste|} Dateien (AK-1, W7-Luecke geschlossen)"
  # b2-Reviewer-Komposit: --scope branch --mode report (DCSRE-1944, primaerer Use-Case)

ELIF scope == "commits":
  # NEU (AK-2/W7): Commit-Range via --range A..B
  [A, B] = range.split("..")
  diff_output = Bash("git diff {A}..{B} --name-only")
  datei_liste = diff_output.splitlines()
  Logge: "[PT_conformance] Scope=commits ({A}..{B}): {|datei_liste|} Dateien"

IF |datei_liste| == 0:
  Logge: "[PT_conformance] WARN: Scope ergibt 0 Dateien — kein Diff vorhanden"
  schreibe_report: {status: "PASS", note: "Scope leer — kein Diff zu pruefen", achsen: achsen}
  loesche resume_marker
  RETURN.
```

**Scope-Achsen-Tabelle (PL-1-Fundament):**

| scope | git-Diff-Adapter | Mantel-Adapter noetig | PL-1 |
|---|---|---|---|
| `unstaged` | `git diff HEAD` (Kern-Default) | nein | ja |
| `slice` | Kern `slice_files()` | nein | ja |
| `branch` | `git diff HEAD..{vs}` | ja (neu) | ja (W7) |
| `commits` | `git diff A..B` | ja (neu) | ja (W7) |

### Phase 3: Achsen-/Layer-Filter (Regal-Selektion VOR Kern-Invoke, PL2-Impl)

```
# Pre-Filter-Architektur (INV-M4-FILTER-1, A5-Entscheidung, Spec A5):
# Regal-Selektion im Mantel VOR dem Kern-Invoke. Der Kern erhaelt gefilterte_regale
# statt alle _project/*/-Unterordner. Tempo-Optimierung (QG-4) + Scope-Einschraenkung.

# ── Schritt 3a: Vault-Root + Library-Pfade laden ─────────────────────────────
VAULT_ROOT = resolve_vault_root()  # via .claude/scripts/resolve_vault_root.py

# Achsen → Library-Basispfade (unveraenderlich)
achse_zu_library = {
  "pattern":   "{VAULT_ROOT}/Libraries/PatternLibrary/_project",
  "semantic":  "{VAULT_ROOT}/Libraries/SemanticLibrary/_project",
  "domain":    "{VAULT_ROOT}/Libraries/DomainLibrary/_project",
  "factoring": "{VAULT_ROOT}/Libraries/FactoringLibrary/_project",
}

# ── Schritt 3b: Achsen-Filter (AK-5-PL-1/AK-3-PL-1, Teilscan) ──────────────
# INV-M4-FILTER-1: Nur selektierte_achsen an Kern uebergeben.
# --achsen pattern,semantic -> domain+factoring werden NICHT geladen.
#
# AK-5 (PL3): Propagations-Kette vollstaendig verifiziert:
#   Phase 1: achsen = args.achsen ?? [alle 4]   (Default AK-12)
#   Phase 3b: selektierte_achsen = achsen        (hier — Deaktivierte herausgefiltert)
#   Phase 5: kern_args.achsen = selektierte_achsen (Weiterleitung an Kern)
# Kein Achsen-State zwischen Phase 1 und Phase 5 verloren.
selektierte_achsen = achsen  # aus Phase 1 (Default alle 4 — AK-12); AK-5 Propagations-Anker

FÜR jede achse IN ["pattern", "semantic", "domain", "factoring"]:
  IF achse NOT IN selektierte_achsen:
    Logge: "[PT_conformance] Achse '{achse}' deaktiviert (--achsen Filter, AK-5) — Regal wird nicht geladen"

# ── Schritt 3c: Layer-Filter (AK-6-PL-1, INV-M4-LAYER-GLOB-1) ────────────────
# INV-M4-LAYER-GLOB-1: --layer-Glob via fnmatch gegen _project/{LAYER}/-Basename.
# Beispiele (OmniCommand): --layer COMMANDS, --layer ORCHESTRAT*, --layer *
# Beispiele (DCSRE): --layer FE-*, --layer BE-AUTH (archiviert → 0 Treffer = korrekt)

gefilterte_regale = {}  # achse → [Regal-Pfad-Liste]

FÜR achse IN selektierte_achsen:
  lib_base = achse_zu_library[achse]
  # Alle _project/{LAYER}/-Unterordner dieser Library ermitteln
  alle_regal_pfade = glob("{lib_base}/*/")  # je 1 Unterordner pro Layer-ID

  IF layer == "*":
    # Kein Filter: alle Regale dieser Achse verwenden
    gefilterte_regale[achse] = alle_regal_pfade
  ELSE:
    # Layer-Glob-Filter: nur Regale deren Basename (= Layer-ID) dem Glob matcht
    # INV-M4-LAYER-GLOB-1: fnmatch(basename(regal_pfad), layer)
    passende = []
    FÜR regal_pfad IN alle_regal_pfade:
      layer_id = basename(regal_pfad)  # z.B. "COMMANDS", "FE-COMPONENT", "BERATER"
      IF fnmatch(layer_id, layer):     # case-sensitiv; Glob: * ? [seq] [!seq]
        passende.append(regal_pfad)
    gefilterte_regale[achse] = passende
    Logge: "[PT_conformance]   Achse '{achse}': {|passende|}/{|alle_regal_pfade|} Regale nach Layer-Filter '{layer}'"

  IF |gefilterte_regale[achse]| == 0:
    Logge: "[PT_conformance] WARN: Achse '{achse}' — kein Regal matcht layer='{layer}' (PASS, NON-BLOCKING)"

Logge: "[PT_conformance] Phase 3b/3c: {|selektierte_achsen|} Achsen / layer={layer}"
FÜR achse IN selektierte_achsen:
  Logge: "  {achse}: {|gefilterte_regale[achse]|} Regale aktiv"

# ── Schritt 3d: NL-Scope-Hint (AK-11-PL-1, optional/tentative/border) ─────────
# Fuzzy-Match eines freien Hints gegen layers.yaml label + id.
# Kein harter Block wenn kein Layer matcht — nur Verengung (NICHT Zero-Match-FAIL).

IF nl_hint != null:
  Logge: "[PT_conformance] NL-Hint aktiv: '{nl_hint}' (AK-11, tentative/border)"

  # layers.yaml laden (Vault-First, Fallback .claude/config/layers.yaml)
  layers_yaml_pfad = "{VAULT_ROOT}/config/layers.yaml" IF EXISTS("{VAULT_ROOT}/config/layers.yaml")
                     ELSE ".claude/config/layers.yaml"
  layers_yaml = parse_yaml(layers_yaml_pfad)

  hint_lower = nl_hint.lower()

  # Fuzzy-Match: Layer-ID oder label enthaelt den Hint (substring, case-insensitive)
  nl_matched_layer_ids = []
  FÜR layer_def IN layers_yaml.layers:
    IF hint_lower IN layer_def.id.lower()
       OR hint_lower IN layer_def.label.lower()
       OR layer_def.id.lower() IN hint_lower
       OR layer_def.label.lower() IN hint_lower:
      nl_matched_layer_ids.append(layer_def.id)

  IF |nl_matched_layer_ids| > 0:
    Logge: "[PT_conformance]   NL-Hint '{nl_hint}' → Layer-IDs: {nl_matched_layer_ids}"
    # NL-Verengung: Regale auf gematchte Layer-IDs einschraenken (ZUSAETZLICH zum Layer-Filter)
    FÜR achse IN selektierte_achsen:
      gefilterte_regale[achse] = [
        regal_pfad FÜR regal_pfad IN gefilterte_regale[achse]
        IF basename(regal_pfad) IN nl_matched_layer_ids
      ]
    Logge: "[PT_conformance]   Nach NL-Verengung:"
    FÜR achse IN selektierte_achsen:
      Logge: "    {achse}: {|gefilterte_regale[achse]|} Regale"
  ELSE:
    # Kein Layer-Match fuer NL-Hint — tentative, kein Block (AK-11 border)
    Logge: "[PT_conformance]   WARN: NL-Hint '{nl_hint}' trifft keinen Layer in layers.yaml — Hint ignoriert (NON-BLOCKING, AK-11 tentative)"

# nl_hint-Ergebnis fuer Phase 5 weitergeben
nl_hint_matched_layers = nl_matched_layer_ids ?? []  # leer wenn nl_hint=null oder kein Match

Logge: "[PT_conformance] Phase 3 DONE: gefilterte_regale bereit fuer Kern-Invoke"
```

**Phase-3-Datenfluss-Tabelle (PL2):**

| Schritt | Input | Output | AK |
|---|---|---|---|
| 3a | VAULT_ROOT + selektierte_achsen | alle_regal_pfade pro Achse | — |
| 3b | achsen (aus Phase 1) | selektierte_achsen (deaktivierte entfernt) | AK-5/AK-3-PL-1 |
| 3c | layer (aus Phase 1) + alle_regal_pfade | gefilterte_regale (nur Glob-Treffer) | AK-6-PL-1 |
| 3d | nl_hint (aus Phase 1) + layers.yaml | gefilterte_regale verfeinert (Fuzzy-Match) | AK-11-PL-1 (optional) |

**Abgrenzung PL2 vs PL3:**

| Item | PL2 | PL3 |
|---|---|---|
| Layer-Filter (fnmatch, 3c) | gebaut | — |
| Achsen-Teilscan (3b) | gebaut | — |
| NL-Hint Fuzzy-Match (3d) | gebaut (optional/tentative) | Haertung/Verbesserung |
| --achsen vollstaendige Default-Verdrahtung | AK-5 Stub bleibt | PL3 |
| AK-1/12 Scope-Achsen-Default | Stub bleibt | PL3 |
| AK-4 voller Standalone-Entry | Stub bleibt | PL3 |

### Phase 4: Read-Only-Guard — HiL-Inversion (PT-CMD-014, AK-9, S6)

```
# KRITISCHER GUARD (AK-9, INV-M4-READONLY-1, PT-CMD-014):
# HiL-Semantik-Inversion zwischen PostBatch-Slot und Standalone-Mantel:
#   Im PostBatch-Slot (Kern): hil=off = Auto-Apply (INV-E3-1, Z.201-218)
#   Im Standalone-Mantel: hil=off = Report-only (INVERSION durch Mantel-Guard)
#
# Strategie A2 (Spec Z.101): Mantel betritt den Apply-Pfad des Kerns NIEMALS bei mode=report.
# NIEMALS: _PostBatch_PatternConformance.md HiL-Logik aendern (AK-7).

IF mode == "report":
  # MANTEL-GUARD aktiv: Apply-Pfad des Kerns wird NICHT betreten.
  # Der Kern-Apply-Block (Z.201-218) wird umgangen, indem der Mantel
  # ihn gar nicht erst aufruft. Keine Aenderung am Kern noetig (AK-7).
  hil_mode_override = "report"   # Mantel-seitige Inversion
  Logge: "[PT_conformance] Phase 4: mode=report — Read-only-Guard aktiv (INV-M4-READONLY-1)"
  Logge: "[PT_conformance]   HiL-Inversion: hil=off im Standalone = Report-only (NICHT Auto-Apply)"
  Logge: "[PT_conformance]   Kern-Apply-Block Z.201-218 wird NICHT betreten."

ELIF mode == "apply":
  # Explizit Apply — Mantel-Guard deaktiviert; Kern-Apply-Block erreichbar.
  hil_mode_override = null
  Logge: "[PT_conformance] Phase 4: mode=apply — explizit freigegeben (KEIN Standalone-Default)"
  Logge: "[PT_conformance]   WARN: Apply-Modus schreibt Code. AK-3 gilt nur fuer mode=report."

# Guard-Zusammenfassung:
#   mode=report (Default): apply_happened IMMER false (INV-M4-READONLY-1, AK-3)
#   mode=apply (explizit): apply_happened gemessen (Kern-Verhalten, nicht Mantel-Override)
```

### Phase 5: Kern-Invoke

```
# Ruft _PostBatch_PatternConformance mit gefilterten Inputs auf.
# NIEMALS den Kern aendern (AK-7, INV-M4-KERNEL-1).
# Batch-Kontext OPTIONAL (AK-4, INV-M4-BATCH-OPT-1).

kern_args = {
  scope:             scope,
  datei_liste:       datei_liste,         # berechnet in Phase 2 (branch/commits: Liste; unstaged/slice: Kern-Default)
  achsen:            selektierte_achsen,   # gefiltert in Phase 3b (Achsen-Teilscan, AK-5 Propagation)
  layer:             layer,               # Original-Param (fuer Kern-interne Referenz)
  regal_filter:      gefilterte_regale,   # NEU PL2: eingeschraenkte Regal-Pfade aus Phase 3c/3d (INV-M4-FILTER-1)
  nl_hint_matched:   nl_hint_matched_layers,  # NEU PL2: gematchte Layer-IDs aus AK-11 (leer = kein NL-Filter aktiv)
  batch_kontext:     lies_optional("_manifest.md") ?? null,  # AK-4 (PL3): optional — Standalone-Lauf wenn null
  hil_mode_override: hil_mode_override    # Phase 4: "report" oder null
}

# AK-4 (PL3): Standalone-Modus-Log — batch_kontext null = kein Manifest gefunden = Standalone-Lauf.
IF kern_args.batch_kontext == null:
  Logge: "[PT_conformance] Phase 5: STANDALONE_MODE bestaetigt — batch_kontext=null, kein DF_BATCH_STATE (INV-M4-BATCH-OPT-1)"
ELSE:
  Logge: "[PT_conformance] Phase 5: Pipeline-Modus — batch_kontext geladen (batch_current={kern_args.batch_kontext.batch_current})"

Logge: "[PT_conformance] Phase 5: Kern-Invoke _PostBatch_PatternConformance"
Logge: "  scope={scope} achsen={selektierte_achsen} layer={layer}"
Logge: "  regal_filter: {FÜR achse IN selektierte_achsen: '{achse}:{|regal_filter[achse]|}'}"
Logge: "  batch_kontext={kern_args.batch_kontext != null} nl_hint_matched={nl_hint_matched_layers}"

Skill(_PostBatch_PatternConformance, args="--scope {scope} ...")
# Kern liefert: {findings, blocker_count, warn_count, info_count, apply_happened, escalation_queued}
kern_result = BERATER_OUTPUTS.PatternConformance
```

### Phase 6: Report-Rendering (statt Manifest-State-Write)

```
# Standalone-Modus: KEIN Manifest-State-Write (SCHREIBT-NICHT-Vertrag).
# Output = transienter Report + optionale PL-Item-Vorschlaege.

# Verdikt pro Achse (PASS/FAIL/INFO)
FÜR jede achse in selektierte_achsen:
  achse_findings = [f for f in kern_result.findings IF f.rule_source == achse]
  achse_blocker  = [f for f in achse_findings IF f.severity == "BLOCKER"]
  achse_warn     = [f for f in achse_findings IF f.severity == "WARN"]
  achse_status   = "FAIL" IF |achse_blocker| > 0 ELSE
                   "WARN" IF |achse_warn| > 0 ELSE "PASS"
  Ausgabe: "  [{achse_status}] Achse={achse}: {|achse_blocker|} BLOCKER, {|achse_warn|} WARN"

# Gesamt-Verdikt
gesamt_status = "FAIL" IF kern_result.blocker_count > 0 ELSE
                "WARN" IF kern_result.warn_count > 0 ELSE "PASS"
Ausgabe: "PatternConformance: [{gesamt_status}] BLOCKER={kern_result.blocker_count} WARN={kern_result.warn_count}"

# apply_happened dokumentieren (AK-3)
Ausgabe: "  apply_happened={kern_result.apply_happened}"  # IMMER false bei mode=report
IF kern_result.apply_happened AND mode == "report":
  FEHLER: "INVARIANTE VERLETZT: apply_happened=true bei mode=report (INV-M4-READONLY-1)"
  EXIT FAIL.

# Optionale PL-Item-Vorschlaege bei Findings
IF kern_result.blocker_count > 0 OR kern_result.warn_count > 0:
  Ausgabe: "PL-Item-Vorschlaege:"
  FÜR jedes finding in kern_result.findings IF finding.severity IN ["BLOCKER", "WARN"]:
    Ausgabe: "  [PL] {finding.severity} {finding.rule_id} in {finding.datei}: {finding.beschreibung}"

# AK-10 Tempo-Annotation (OFFEN/border, tentative):
# Parallelisierungs-Option-Slot — floor/haiku-Worker pro Achse ist OPTION, kein Zwang.
# Kein harter Architektur-Entscheid vorab (OQ3). Laufzeit-Ziel: < 3 Min bei ~50-Datei-FE-PR (AK-10).
# IMPL: AK-10 ist TENTATIV/border — kein Bau-Zwang in batch_PL1 (PL3).

# b2-Reviewer-Komposit (AK-8, S5):
# Dieser Lauf ohne A-Pipeline/frisches Model = b2-Modus (DCSRE-1944).
# Komposit: AK-1 (--scope branch) + AK-3 (--mode report) + AK-4 (Standalone-Entry).
# Kein eigener AK-Bau-Block — ergibt sich aus dem Zusammenspiel der anderen Sektionen.
Logge: "[PT_conformance] Phase 6 DONE — b2-Report abgeschlossen (keine A-Pipeline noetig)"

# Aufraumen
loesche resume_marker  # Idempotenz-Guard zuruecksetzen (Phase 0)
```

---

## INVARIANTEN (PT-CMD-004, S3)

```
INV-M4-KERNEL-1 (diff=0, AK-7, DoD-7):
  _PostBatch_PatternConformance.md wird vom Mantel aufgerufen (Read-Invoke), NIEMALS geschrieben.
  Nach Build muss gelten: git diff 34e2f277 -- .claude/commands/_PostBatch_PatternConformance.md = leer.
  Jede Aenderung am Kernel verletzt INV-M4-KERNEL-1 und bricht DoD-7.

INV-M4-READONLY-1 (PT-CMD-014, AK-3, AK-9):
  --mode report (Standalone-Default) betritt den Apply-Pfad des Kerns NIE.
  apply_happened ist IMMER false bei mode=report.
  HiL=off im Standalone-Modus = Report-only (Inversion zum PostBatch-Slot, wo hil=off=Auto-Apply).
  Phase 4 erzwingt dies via Mantel-Guard (hil_mode_override=report) statt den Kern zu aendern.

INV-M4-SCOPE-1 (AK-1, AK-2, PT-CMD-013):
  Scope-Ermittlung (branch/commits) laeuft VOR dem Kern-Invoke im Mantel (Phase 2).
  Der Kern erhaelt immer eine bereits berechnete Datei-Liste oder den Default-Scope-Marker.
  branch: git diff HEAD..{vs_branch} (Default vs=develop, Praezedenz _SL_pre_pr)
  commits: git diff A..B via --range A..B

INV-M4-BATCH-OPT-1 (AK-4):
  DF_BATCH_STATE ist im Standalone-Modus OPTIONAL.
  Fehlendes Manifest = kein Fehler. Batch-Kontext null wird an Kern uebergeben.
  Der Kern behandelt batch_kontext=null als Standalone-Lauf (NON-BLOCKING, INV-B2-1 gilt).

INV-M4-FILTER-1 (AK-5/AK-3-PL-1/AK-6-PL-1, batch_PL2):
  Regal-Selektion (gefilterte_regale) laeuft IMMER im Mantel, BEVOR der Kern aufgerufen wird.
  Phase 3 berechnet gefilterte_regale VOR Phase 5 (Kern-Invoke) — keine Nachfilterung im Kern.
  Der Kern erhaelt regal_filter als expliziten Parameter, kein implizites "lade alles".
  Achsen-Filter (3b): Achsen ohne Treffer in selektierte_achsen = NICHT an Kern uebergeben.
  Layer-Filter (3c): Regale die den Layer-Glob nicht matchen = NICHT in regal_filter.
  Ein leeres regal_filter[achse]-Array ist korrekt (0 Regale matchen Glob) — NON-BLOCKING.

INV-M4-LAYER-GLOB-1 (AK-6-PL-1, batch_PL2):
  Der --layer-Parameter ist ein fnmatch-Glob gegen den Basename der _project/{LAYER}/-Unterordner.
  Baseline (layers.yaml): OmniCommand-Layer IDs = COMMANDS, BERATER, ORCHESTRATOR, SCRIPTS, META, HOOKS.
  Glob-Beispiele: --layer COMMANDS (exakt), --layer ORCHESTRAT* (Praefix), --layer * (alle).
  DCSRE-Layer (FE-*, BE-*) treffen in OmniCommand-Kontext 0 Regale — korrekt (NON-BLOCKING).
  Pro Projekt liefert layers.yaml die kanonischen Layer-IDs (ARCH-N7).
  Der Mantel laedt layers.yaml NICHT fuer den Layer-Glob — er globbt direkt gegen Verzeichnis-Basenames.
  layers.yaml wird NUR in Schritt 3d (NL-Hint) konsultiert (label+id fuer Fuzzy-Match).
```

---

## DIRTY-Scope-Skizze (PT-CMD-013, AK-2-PL-1/W7, S4)

Die 4 Scope-Modi mit ihren git-Diff-Adaptern (implementiert in Phase 2):

| Scope | git-Diff-Adapter | Mantel-Adapter | PL-Status |
|---|---|---|---|
| `unstaged` | `git diff HEAD` | nein (Kern-Default) | PL1 (basis) |
| `slice` | `slice_files(SLICE_NAME)` | nein (Kern-Default) | PL1 (basis) |
| `branch` | `git diff HEAD..{vs_branch}` | ja — neu in batch_PL1 | PL1 (W7) |
| `commits` | `git diff {A}..{B}` via `--range A..B` | ja — neu in batch_PL1 | PL1 (W7) |

**Praezedenz:** `_SL_pre_pr --vs {branch}` als Referenz-Implementierung fuer branch-Total.
`_SL_pre_pr` bleibt eigenstaendig (OQ2-Default: REFERENZIEREN, nicht absorbieren).

**NOTE:** `branch` + `commits` sind die PL-1-Scope-Luecken (F-02/W7), die der Mantel schliesst.
Der Kern kennt nur `unstaged` + `slice` (Kern-Zeile Z.18-20).

---

## Reviewer-Komposit b2 (AK-8-PL-1/W18, S5)

```
b2-Reviewer-Modus = {cmd} --scope branch --mode report

Komposit:
  AK-1 (--scope branch) + AK-3 (--mode report) + AK-4 (Standalone-Entry ohne DF_BATCH_STATE)

Primaerer Treiber: DCSRE-1944 (Reviewer-mit-Kontext ohne laufende Pipeline).
Kein eigener AK-Bau-Block — ergibt sich aus dem Zusammenspiel der anderen Sektionen.
Der b2-Reviewer benoetigt KEINE A-Pipeline + kein frisches Model (AK-8).

Beispiel-Aufruf:
  Skill(_PT_conformance_orchestrate, args="--scope branch --mode report --achsen pattern,semantic --layer FE-*")
```

---

## HiL-Inversion Guard (PT-CMD-014, AK-9-PL-1/W10/W17, S6)

```
HiL-Semantik-Vergleich:

  PostBatch-Slot (Kern, INV-E3-1):
    hil=off → Auto-Apply (trivial-BLOCKERs werden direkt korrigiert, Z.201-218)
    hil=on  → Report + Frage (Apply/Park/Skip)

  Standalone-Mantel (_PT_conformance_orchestrate):
    mode=report (Default) → NIE Apply — unabhaengig von HiL (INVERSION)
    mode=apply (explizit) → Apply-Pfad erreichbar (nur wenn explizit gesetzt)

Strategie A2 (Spec Z.101): Mantel betritt den Apply-Pfad des Kerns NIE bei mode=report.
Impl-Hinweis: Der Mantel setzt hil_mode_override=report in Phase 4, wenn mode=report
UND Standalone-Entry. Der Kern-Apply-Block (Z.201-218) wird umgangen — der Mantel
ruft ihn gar nicht erst auf. NIEMALS _PostBatch_PatternConformance.md aendern (AK-7).

INVARIANTE INV-M4-READONLY-1 (Enforcement):
  IF apply_happened == true AND mode == "report":
    FEHLER: "INVARIANTE VERLETZT: apply_happened=true bei mode=report"
    → STOP + ROLLBACK
```

---

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| PatternLibrary leer (EMPTY_SEED) | NON-BLOCKING Skip via Kern (INV-B2-1), Report: "PatternLibrary leer" |
| Scope ergibt 0 Dateien | PASS sofort (kein Diff = nichts zu pruefen), Logge WARN |
| DF_BATCH_STATE fehlt (Standalone) | kein Fehler — batch_kontext=null (INV-M4-BATCH-OPT-1, AK-4) |
| --range fehlt bei scope=commits | FEHLER mit klarer Meldung |
| Kern nicht erreichbar | FEHLER: "Kern-Invoke fehlgeschlagen" (KEIN Stub-Fallback) |

---

## Out-of-Scope (batch_PL3-Abgrenzung, DoD-12)

**Gebaut in batch_PL1 (Fundament):** VERTRAG, Pseudocode-Struktur, INVARIANTEN (S1-S6), Scope-Skizze, HiL-Inversion-Guard-Konzept.

**Gebaut in batch_PL2 (Filter-Schicht):** Phase-3-Pre-Filter (3a/3b/3c Achsen+Layer), Phase-5-regal_filter-Uebergabe, INV-M4-FILTER-1, INV-M4-LAYER-GLOB-1, NL-Hint Schritt-3d (tentative/optional).

**Gebaut in batch_PL3 (Integration-Schicht — Command vollstaendig):**

| Feature | AK | Status |
|---|---|---|
| Vollstaendiger Standalone-Entry-Vollausbau | AK-4-PL-1 | GEBAUT (batch_PL3) — Phase-0/1-Manifest-frei + STANDALONE_MODE-Log Phase 1+5, INV-M4-BATCH-OPT-1 |
| `--scope branch` Default-Verdrahtung vollstaendig | AK-1-PL-1 | GEBAUT (batch_PL3) — Phase-2-Log + vs-Default-Doku, End-to-End b2-Reviewer-Pfad |
| `--achsen`-Propagation vollstaendig (Teilscan-Vollimpl) | AK-5-PL-1 | GEBAUT (batch_PL3) — Phase-1→3b→5 Propagations-Kette verifiziert/kommentiert |
| achsen-Default alle 4 vollstaendig verdrahtet | AK-12-PL-1 | GEBAUT (batch_PL3) — Default Phase-1 + W14-NON-BLOCKING-Greenfield dokumentiert |

**Defer / Follow-up (kein Bau-Zwang in batch_PL3):**

| Feature | AK | Defer-Status |
|---|---|---|
| AK-10 Tempo-Parallelisierung (floor/haiku-Worker pro Achse) | AK-10 | DEFER — border/tentative, kein Architektur-Entscheid vorab (OQ3). Laufzeit-Ziel <3 Min bleibt als Observatum. Carryforward: naechste PL-Runde falls Laufzeit-Messung Handlungsbedarf zeigt. |
| AK-11 NL-Scope-Hint Haertung / verbesserte Fuzzy-Logik | AK-11 | DEFER — PL2-Impl (optional/tentative) bereits nuetzbar. Haertung nur wenn Praxisfeedback Bedarf zeigt. |
| AK-8 Report-Renderer Vollausbau (DoD-10, structured output) | AK-8 | DEFER — Phase-6-Report funktional (Konsole). Strukturierter Renderer (JSON/MD) als Follow-up wenn Integration noetig. |

**batch_PL3 = Integration-Schicht:** Standalone-Entry-Vollausbau (AK-4), Scope/Achsen-Default-Verdrahtung (AK-1/AK-12), Teilscan-Vollimpl-Verifikation (AK-5). Command vollstaendig (v1.0.0). Kein Kern-Edit (diff=0 34e2f277).

---

## Verwandt

- `_PostBatch_PatternConformance.md` (Kern, UNVERAENDERT, AK-7) — M-4-PostBatch-Slot
- `_SL_pre_pr.md` (Branch-Scope-Praezedenz, OQ2: referenziert, nicht absorbiert)
- `_PostBatch_ArchConformance.md` (BL-154, Schwestern-Skill — Architektur-Konformanz)
- `_PT_orchestrate.md` (PT-Familie Producer/Harvest-Seite)
