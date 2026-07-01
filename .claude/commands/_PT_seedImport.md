---
type: building-block
status: active
version: 1.0.0
created: 2026-04-30
feature: SemantischePatternLibrary
bl_item: BL-153
ak_ref: AK-C-4
chain_position: standalone (einmalig nach _PT_init, vor erstem _PT_extract)
dependencies: [AK-D-1, AK-D-3]
---

# /_PT_seedImport — Seed-Import der Konventions-Dateien in PatternLibrary

**Status:** v1.0 (AK-C-4, BL-153)
**Actor:** SEED-IMPORTER
**Zweck:** Importiert 14 bestehende Konventions-Dateien (9 codeKonvention + 5 architekturKonventionen)
als Seed-Patterns in die PatternLibrary. Standardisierte Frontmatter-Felder: `seed=true`,
`confidence=low`, `status=experimental`, `needs_organic_validation=true`.

> **Frequenz:** EINMALIG nach `_PT_init`. Idempotent — zweiter Import aendert keine
> bereits korrekt gesetzten Felder.

---

## Aufruf

```
/_PT_seedImport [--dry-run]
```

| Parameter | Pflicht | Default | Beschreibung |
|-----------|---------|---------|-------------|
| `--dry-run` | NEIN | false | Report ohne Schreiben (zeigt was importiert wuerde) |

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_PT_seedImport (AK-C-4, BL-153)                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    .claude/meta/codeKonvention/*.md        (9 Seed-Quellen)         ║
║    .claude/meta/architekturKonventionen/be-*.md (5 Seed-Quellen)    ║
║    Libraries/PatternLibrary/_index.md (Duplikat-Check)              ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    Libraries/PatternLibrary/_generic/{name}.md (pro Seed-Datei)     ║
║    Libraries/PatternLibrary/_index.md (neue Eintraege)              ║
║    .claude/wissen/pattern-usage.log (APPEND: seed imports)          ║
║    Bei --dry-run: NUR Report ausgeben, NICHTS schreiben             ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    _manifest.md (kein State — standalone Command)                   ║
║    Bestehende Pattern-Dateien (idempotent: SKIP wenn vorhanden)     ║
║                                                                      ║
║  ACTOR: SEED-IMPORTER                                                ║
║  MODELL-TIER: floor (haiku) — mechanischer Import, kein Reasoning   ║
║  INVARIANTEN:                                                        ║
║    INV-SEED-1: IDEMPOTENT — zweiter Aufruf aendert keine Felder     ║
║    INV-SEED-2: Genau 4 Pflichtfelder: seed/confidence/status/needs_organic_validation║
║    INV-SEED-3: Fehlende Quelldatei → WARNING + SKIP (kein Abbruch) ║
║    INV-SEED-4: Immer seed=true, confidence=low fuer ALLE 14 Nodes  ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Quell-Dateien (14 fixed)

### 9 codeKonvention

```
.claude/meta/codeKonvention/naming.md
.claude/meta/codeKonvention/formatting.md
.claude/meta/codeKonvention/documentation.md
.claude/meta/codeKonvention/error-handling.md
.claude/meta/codeKonvention/testing.md
.claude/meta/codeKonvention/dependency-injection.md
.claude/meta/codeKonvention/async-patterns.md
.claude/meta/codeKonvention/logging.md
.claude/meta/codeKonvention/security.md
```

### 5 architekturKonventionen

```
.claude/meta/architekturKonventionen/be-core.md
.claude/meta/architekturKonventionen/be-cont.md
.claude/meta/architekturKonventionen/be-dto.md
.claude/meta/architekturKonventionen/be-domain.md
.claude/meta/architekturKonventionen/be-auth.md
```

---

## Ablauf

### Schritt 0: Vorbedingungen

```
Pruefe Libraries/PatternLibrary/_index.md existiert (Vorbedingung: _PT_init gelaufen)
IF NICHT vorhanden:
  FEHLER: "_PT_init muss zuerst laufen. Libraries/PatternLibrary/_index.md fehlt."
  RETURN

Logge: "[PT_seedImport] START — 14 Seed-Quellen."
IF --dry-run: Logge: "[PT_seedImport] DRY-RUN — kein Schreiben."
```

### Schritt 1: Pro Quelldatei importieren (14x)

```
FÜR jede quelldatei in QUELL_DATEIEN:
  # Duplikat-Check (INV-SEED-1: Idempotenz)
  name = quelldatei-Dateiname ohne Extension, kebab-case
  ziel = Libraries/PatternLibrary/_generic/{name}.md

  IF ziel existiert:
    # Pruefe ob Pflichtfelder korrekt gesetzt
    bestehend = lies ziel Frontmatter
    IF bestehend.seed == true AND bestehend.confidence == "low"
       AND bestehend.status == "experimental" AND bestehend.needs_organic_validation == true:
      Logge: "[PT_seedImport] SKIP {name} (bereits korrekt importiert)"
      CONTINUE  # Idempotent
    ELSE:
      Logge: "[PT_seedImport] UPDATE {name} (fehlende/falsche Pflichtfelder)"
      # Update nur die 4 Pflichtfelder, Rest unveraendert

  # Quelldatei lesen
  IF quelldatei NICHT vorhanden:
    Logge WARNUNG: "[PT_seedImport] SKIP {quelldatei} — nicht gefunden (INV-SEED-3)"
    CONTINUE

  inhalt = lies quelldatei

  # Layer bestimmen — Vault-First Layer-Detection (analog _PT_arch_init Phase 0)
  vault_root = python3(.claude/scripts/resolve_vault_root.py).stdout.strip()
  layers_config = lies("{vault_root}/config/layers.yaml") OR lies(".claude/config/layers.yaml")
  layer = "_generic"
  FÜR jeden layer_def in layers_config.layers:
    FÜR jeden glob in layer_def.path_globs:
      IF quelldatei matches glob: layer = layer_def.id; BREAK
  applies_to = [layer] IF layer != "_generic" ELSE [layer_def.id FOR layer_def in layers_config.layers]

  # Pattern-Datei erstellen (INV-SEED-2: 4 Pflichtfelder IMMER gesetzt)
  IF NOT --dry-run:
    Erstelle Libraries/PatternLibrary/_generic/{name}.md:
      ---
      id: PT-GEN-{NAME-UPPER}
      type: pattern
      scope: project
      layer: _generic
      status: experimental
      seed: true
      confidence: low
      applies_to: {applies_to}
      severity: INFO
      seed_source: {quelldatei}
      needs_organic_validation: true
      ---
      # {name (Title Case)}

      {Erste 3-5 Zeilen aus quelldatei als Beschreibung}

      ## Quelle
      Importiert von: `{quelldatei}` via `_PT_seedImport` (AK-C-4, BL-153)
      Status: SEED — noch nicht organisch validiert. `needs_organic_validation=true`.
```

### Schritt 2: _index.md aktualisieren

```
IF NOT --dry-run:
  FÜR jeden neu importierten Eintrag:
    APPEND Libraries/PatternLibrary/_index.md:
      | {id} | {name} | SEED/experimental | _generic | low | {quelldatei} |

  APPEND .claude/wissen/pattern-usage.log:
    {DATUM} | {id} | {name} | _generic | SEED | seed_import_codeKonv
```

### Schritt 3: Abschluss-Report

```
Logge: "[PT_seedImport] DONE — {N_importiert} importiert, {N_skipped} uebersprungen, {N_fehler} WARN."
Logge: "[PT_seedImport] Alle 14 Nodes haben seed=true, confidence=low, needs_organic_validation=true."
IF N_fehler > 0:
  Logge WARNUNG: "[PT_seedImport] {N_fehler} Quelldateien nicht gefunden — pruefe codeKonvention/-architekturKonventionen Verzeichnisse."
```

---

## Smoke-Test (nach Import)

```
FÜR jeden importierten Pattern-Knoten:
  ASSERT seed == true
  ASSERT confidence == "low"
  ASSERT status == "experimental"
  ASSERT needs_organic_validation == true

Import-Count: 9 codeKonvention + 5 architekturKonventionen = genau 14 (INV-SEED-2)
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| Quelldatei fehlt | WARNING + SKIP (INV-SEED-3), kein Abbruch |
| Libraries/_index.md fehlt | FEHLER + STOPP (_PT_init fehlt) |
| Pattern bereits vorhanden + korrekt | SKIP (INV-SEED-1 Idempotenz) |
| Pattern vorhanden + falsche Felder | UPDATE nur 4 Pflichtfelder |
| --dry-run | NUR Report, kein Schreiben |

---

## Verwandt

- `_PT_init` — Library-Struktur aufbauen (Vorbedingung)
- `_PT_extract` — Einzel-Extraktion laufend
- `_PT_arch_init` — Projektweite Erstbefuellung (AK-B-11)
- `Libraries/PatternLibrary/_generic/frontmatter-schema.md` — Pflichtfelder-Schema (AK-D-3)
