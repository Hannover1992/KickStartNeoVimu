---
status: active
version: 0.2.0
type: berater
parent: _A_orchestrate
phase: phase_0.2
model_tier: middle
created: 2026-04-25
updated: 2026-05-06
feature_anchor: BL-142
optional: true
changelog_0_2_0: |
  v0.2.0 (2026-05-06): Skelett -> produktiv.
    - Header-Extraktion (H1/H2 oder Filename-Fallback) implementiert.
    - Slug-Normalisierung (kebab-case, ASCII-Folding).
    - Kollisions-Check + Disambiguierungs-Suffix.
    - Vault-First fuer anchor_nodes (mit Lokal-Fallback).
contract:
  reads:
    - {file: ".claude/pileOfMud/", path: "Erste *.md/*.txt mit Top-Section", purpose: "Themen-Headline ableiten"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE", purpose: "Resync-Vorabwert pruefen"}
    - {file: "{VAULT}/_anchor_nodes.md", path: "Anchor-Liste", purpose: "Vault-First Anchor-Knoten"}
    - {file: ".claude/analysis/_anchor_nodes.md", path: "Anchor-Liste FALLBACK", purpose: "Legacy-Lokal"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.derived_name", purpose: "Abgeleiteter Feature-Name (slug)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.discovery", purpose: "Output-Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (excluding discovery)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.modus / routing_target"}
  calls: []
---

# _A_berater_discovery (Phase 0.2 in _A_orchestrate)

> **Zweck:** Aus pileOfMud-Header einen kanonischen Feature-Namen (slug) ableiten — NUR aktiv bei `name=auto`.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_discovery                                       |
+======================================================================+
|  LIEST:                                                              |
|    {pileOfMud}                                                       |
|      Headers / Top-Section (erste sinntragende Ueberschrift)         |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      A_PIPELINE_STATE.derived_name (Resync-Schutz)                   |
|    .claude/analysis/_anchor_nodes.md                                 |
|      bestehende Feature-Namen / slugs (Kollisions-Check)             |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      A_PIPELINE_STATE.derived_name = "{slug}"                        |
|      BERATER_OUTPUTS.discovery = {                                   |
|        derived_name, source_header, collisions_avoided[]             |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser discovery)                              |
|    A_PIPELINE_STATE.modus / routing_target                           |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 0.2 (NUR bei name=auto)                 |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Header-Parsing + Slug-Ableitung mit                  |
|    Kollisions-Check, kein tiefes Reasoning noetig.                   |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-DISC-1: derived_name ist slug-konform (lowercase, kebab-case) |
|    INV-DISC-2: Kollision mit anchor_nodes ausgeschlossen             |
|    INV-DISC-3: Schreib-Isolation auf BERATER_OUTPUTS.discovery       |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - name == "auto" in _A_orchestrate Args                           |
|    - pileOfMud-Pfad gesetzt im Manifest                              |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - A_PIPELINE_STATE.derived_name gesetzt                           |
|    - BERATER_OUTPUTS.discovery vollstaendig                          |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_discovery, args="{NAME=auto}")

Parameter:
  {NAME} - "auto" (sonst Phase uebersprungen)

Ausgabe:
  - A_PIPELINE_STATE.derived_name
  - BERATER_OUTPUTS.discovery
  - Exitcode: 0=OK, 2=FAIL (kein Header gefunden / Kollisions-Sackgasse)

Logging-Format:
  [A_DISCOVERY] ENTRY pileOfMud={path}
  [A_DISCOVERY] EXIT duration={ms}ms derived_name={slug} status={OK|FAIL}
```

## Output-Schema

```yaml
A_PIPELINE_STATE:
  derived_name: "feature-foo"

BERATER_OUTPUTS:
  discovery:
    derived_name: "feature-foo"
    source_header: "Feature Foo - Erste Untersuchung"
    collisions_avoided: []
    last_berater: "discovery"
```

## Logik (v0.2.0 produktiv)

```
SCHRITT 0: Entry + Vorbedingung
  NAME = args[0]
  Logge: "[A_DISCOVERY] ENTRY pileOfMud=.claude/pileOfMud/"
  IF NAME != "auto":
    Logge: "[A_DISCOVERY] SKIP — name={NAME} != auto"
    EXIT 0   # nur bei name=auto aktiv (siehe Frontmatter optional: true)

SCHRITT 1: pileOfMud durchsuchen
  pile_files = Glob(".claude/pileOfMud/*.{md,txt}")
  IF |pile_files| == 0:
    Logge: "[A_DISCOVERY] FAIL — pileOfMud leer"
    EXIT 2

  # Sortiere nach modification time (neueste zuerst)
  pile_files = sort_by_mtime_desc(pile_files)
  primary = pile_files[0]
  content = Read(primary)

SCHRITT 2: Header-Extraktion (H1 > H2 > Filename-Fallback)
  header = null
  source_kind = null

  # H1 zuerst (groesste Aussage)
  h1_match = regex(content, "^# (.+)$", multiline=true).first
  IF h1_match != null:
    header = h1_match.trim()
    source_kind = "h1"

  # H2 falls kein H1
  IF header == null:
    h2_match = regex(content, "^## (.+)$", multiline=true).first
    IF h2_match != null:
      header = h2_match.trim()
      source_kind = "h2"

  # Filename-Fallback
  IF header == null:
    base = basename(primary).strip_extension()
    # Strip RAW_/Datum-Praefixe
    header = base.replace("_RAW_", "_").replace("-RAW-", "_")
                 .regex_replace(r"\d{4}-\d{2}-\d{2}", "")
                 .regex_replace(r"\d{8}", "")
                 .strip("_-")
    source_kind = "filename"

SCHRITT 3: Slug-Normalisierung (kebab-case, ASCII)
  slug = header.lower()
  slug = ascii_fold(slug)              # ae/oe/ue -> ae/oe/ue (oder a/o/u)
  slug = regex_replace(slug, r"[^a-z0-9]+", "-")
  slug = slug.strip("-")
  IF slug == "":
    Logge: "[A_DISCOVERY] FAIL — slug leer nach Normalisierung (header={header})"
    EXIT 2

SCHRITT 4: Anchor-Liste laden (Vault-First, Lokal-Fallback)
  anchor_path = "{VAULT}/_anchor_nodes.md"
  IF NOT exists(anchor_path):
    anchor_path = ".claude/analysis/_anchor_nodes.md"
  existing_slugs = []
  IF exists(anchor_path):
    existing_slugs = parse_slug_list(Read(anchor_path))

SCHRITT 5: Kollisions-Check + Disambiguierung
  original_slug = slug
  collisions_avoided = []
  suffix = 2
  WHILE slug IN existing_slugs:
    collisions_avoided.append(slug)
    slug = "{original_slug}-{suffix}"
    suffix += 1
    IF suffix > 99:
      Logge: "[A_DISCOVERY] FAIL — Kollisions-Sackgasse (>99 Suffixes)"
      EXIT 2

SCHRITT 6: Output schreiben (INV-DISC-3 Schreib-Isolation)
  Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.derived_name = slug)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.discovery = {
    derived_name: slug,
    source_header: header,
    source_kind: source_kind,
    source_file: basename(primary),
    collisions_avoided: collisions_avoided,
    last_berater: "discovery"
  })

SCHRITT 7: Exit
  Logge: "[A_DISCOVERY] EXIT derived_name={slug} source={source_kind}"
  EXIT 0
```

## Begruendung Modell-Tier

sonnet — Header-Parsing + Slug-Normalisierung + Listen-Vergleich. Kein Deep-Reasoning, kein Schreib-Volumen jenseits eines kleinen Output-Blocks.
