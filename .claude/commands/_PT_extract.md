---
type: building-block
---

# /_PT_extract

**Status:** v1.0 (W245 PT-Command-Familie 2/3, W259 Auto-Kontext)
**Actor:** PATTERN-EXTRACTOR
**Zweck:** Automatische Pattern-Extraktion wenn _SC_implement RED-Klassifikation meldet (1.5g PT-Trigger). Leitet Parameter aus Code-Kontext ab — KEIN AskUserQuestion fuer Pflichtfelder.

> **MIGRATION (ARCH-4, BL-153):** Standard-Pfad seit BL-151 migriert auf
> `Libraries/PatternLibrary/` (Vault-First). `.claude/patterns/` ist DEPRECATED.
> Bestehende Einträge unter `.claude/patterns/` können via `_PT_seedImport`
> migriert werden. Canonical-Path: `Libraries/PatternLibrary/_project/{LAYER}/`.

---

## Aufruf

```
/_PT_extract [code-context-file] [layer] [pattern-name]
```

| Parameter | Pflicht | Format | Beispiel |
|-----------|---------|--------|----------|
| code-context-file | NEIN (Auto-Ableitung) | Dateipfad | `.claude/commands/_PT_extract.md` |
| layer | NEIN (Auto-Ableitung) | Layer-Kuerzel aus _pl-index.md 2.3 | `cmd`, `be-cont`, `fe-comp` |
| pattern-name | NEIN (Auto-Ableitung) | kebab-case | `vertrag-block`, `auto-kontext` |
| --parking-lot-walk | NEIN | Flag | Durchsucht Parking-Lot nach offenen Pattern-Kandidaten (AK-B-6, BL-153). Manuell aufrufen — kein Auto-Trigger (AK-B-7: Frequenz=manuell). |

**Alle Parameter sind optional.** Fehlende Werte werden aus Code-Kontext abgeleitet (Schritt 0).

**Frequenz (AK-B-7):** `_PT_extract` wird MANUELL aufgerufen — kein automatischer Trigger ausser dem expliziten `_SC_implement 1.5g RED`-Pfad. `--parking-lot-walk` immer manuell.

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_PT_extract [code-context-file] [layer] [pattern]   |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. Libraries/PatternLibrary/_index.md                       |
|       -> Duplikat-Check: existiert Pattern bereits?            |
|       -> Layer-Routing: Layer validieren                       |
|    2. Code-Kontext (Datei oder HYPOTHESEN.md Auto-Ableitung)   |
|       -> Layer, pattern-name, beschreibung ableiten            |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    3. .claude/analysis/synthese/{NAME}-HYPOTHESEN.md           |
|       -> "Durchgefuehrte Aenderungen" fuer Auto-Kontext        |
|       -> "Horizontale Suche" fuer Layer + Blueprint             |
|    4. Libraries/PatternLibrary/_generic/*.md                   |
|       -> Aktueller Library-Stand fuer Kontext                  |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md |
|       -> Neue Pattern-Datei, status: experimental              |
|    2. .claude/wissen/pattern-usage.log                         |
|       -> APPEND: Datum, Pattern-Name, Kontext, Quelle          |
|    3. Libraries/PatternLibrary/_index.md                       |
|       -> Neuen Pattern-Link hinzufuegen                        |
|                                                                |
|  ACTOR: PATTERN-EXTRACTOR                                      |
|    Extrahiert Pattern automatisch aus Code-Kontext und          |
|    persistiert als DRAFT in der Pattern Library.                |
|    Kein AskUserQuestion fuer Pflichtfelder — Auto-Ableitung.   |
|                                                                |
+===============================================================+
```

---

## Modus-Verträge (AK-F-1, BL-153)

### M1: --parking-lot-walk VERTRAG

> **INV-EINSCHUB (AK-F-4, BL-153):** Dieser Modus ist ein Einschub in Schritt 0 —
> bestehender Standard-Pfad unveraendert.

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_PT_extract --parking-lot-walk (M1)                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {VAULT}/ParkingLotGlobal/*.md         (INV-D4: NUR Vault-PL)     ║
║    Libraries/PatternLibrary/_index.md    (Duplikat-Check)           ║
║    Libraries/PatternLibrary/_project/{LAYER}/*.md (Layer-Kontext)   ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md      ║
║      status: experimental, seed: false, confidence: low             ║
║      source_tag: parking-lot                                         ║
║    Libraries/PatternLibrary/_index.md (neuer Eintrag)               ║
║    .claude/wissen/pattern-usage.log (APPEND)                        ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    .claude/_parking-lot.md (Legacy, BLOCKIERT via INV-D4)           ║
║    DF_BATCH_STATE oder BERATER_OUTPUTS (kein Manifest-Zugriff)      ║
║                                                                      ║
║  ACTOR: PATTERN-EXTRACTOR (manueller Aufruf, AK-B-7)               ║
║  MODELL-TIER: floor                                                  ║
║  INVARIANTEN:                                                        ║
║    INV-D4: Vault-Only-Quelle — .claude/_parking-lot.md BLOCKIERT    ║
║    INV-D5: ApplicationTrail OPTIONAL bei M1 (kein Auto-Create)      ║
║    AK-B-7: Frequenz = manuell (KEIN Auto-Trigger)                   ║
║    AK-C-3: source_tag=parking-lot → MAX confidence=low (INV-D5)    ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Frontmatter fuer M1-extrahierte Patterns:**

```yaml
source_tag: parking-lot
confidence: low      # MAX: low (INV-D5 Cap)
seed: false
status: experimental
needs_organic_validation: true
```

---

### M2: --semantic --full-codebase VERTRAG

> **INV-EINSCHUB (AK-F-4, BL-153):** Dieser Modus ist ein neuer Einschub-Pfad
> in Schritt 0 — Standard-Pfad und --parking-lot-walk unveraendert.

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_PT_extract --semantic --full-codebase (M2)              ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    .claude/commands/*.md         (alle Command-Dateien)             ║
║    .claude/meta/**/*.md          (alle Meta-Dateien)                ║
║    src/**/*.cs (oder projektspez. Code-Verzeichnisse)               ║
║    Libraries/PatternLibrary/_index.md (Duplikat-Check/Kontext)      ║
║    Libraries/PatternLibrary/_project/**/*.md (bestehende Patterns)  ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md      ║
║      status: experimental, seed: false, confidence: medium          ║
║      source_tag: r_orchestrate                                       ║
║    Libraries/PatternLibrary/_index.md (neue Eintraege)              ║
║    .claude/wissen/pattern-usage.log (APPEND pro Pattern)            ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    Pattern-Knoten-Dateien anderer Patterns (read-only fuer Kontext) ║
║    DF_BATCH_STATE oder BERATER_OUTPUTS (kein Manifest-Zugriff)      ║
║                                                                      ║
║  ACTOR: PATTERN-EXTRACTOR (manueller Aufruf oder deliberativer      ║
║         M2-Scan nach SC-Zyklus)                                      ║
║  MODELL-TIER: ceiling (opus) — deliberative Analyse, M2-Qualitaet  ║
║  INVARIANTEN:                                                        ║
║    INV-D5: ApplicationTrail EMPFOHLEN (nicht PFLICHT) bei M2        ║
║    AK-B-7: Frequenz = manuell oder explizit SC-getriggert           ║
║    AK-C-3: source_tag=r_orchestrate → MAX confidence=medium        ║
║    INV-M2-1: Full-Codebase-Scan nur auf expliziten Flag — KEIN Auto ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Ablauf M2 --semantic --full-codebase:**

```
IF --semantic AND --full-codebase:
  Logge: "[PT_extract M2] Full-Codebase semantischer Scan gestartet."

  # Schritt M2-0: Scope laden
  scan_targets = [".claude/commands/", ".claude/meta/", "src/"]
  existing_patterns = lies Libraries/PatternLibrary/_index.md

  # Schritt M2-1: Muster suchen
  FÜR jede Datei IN scan_targets:
    analysiere Datei auf wiederkehrende Strukturen:
      - VERTRAG-Block-Muster (╔══╗ Format)
      - INV-EINSCHUB-Muster
      - Worker-Spawn-Muster (spawne_worker / Agent(...))
      - Dual-Write-Muster (State + Protokoll)
      - Graceful-Degradation-Muster

    IF Muster erkannt UND kein Duplikat in existing_patterns:
      pattern_kandidaten.append({
        name: abgeleiteter_kebab_name,
        layer: abgeleiteter_layer,
        beschreibung: Muster-Beschreibung,
        source_file: datei_pfad,
        confidence: "medium",
        source_tag: "r_orchestrate"
      })

  Logge: "[PT_extract M2] {N} Pattern-Kandidaten gefunden."

  # Schritt M2-2: Pro Kandidat → Schritt 1..4 (Standard-Pfad)
  FÜR jeden kandidaten in pattern_kandidaten:
    → weiter mit Schritt 1 (Duplikat-Check)
    frontmatter.source_tag = "r_orchestrate"
    frontmatter.confidence = "medium"
    frontmatter.seed = false
    frontmatter.status = "experimental"

  Logge: "[PT_extract M2] DONE — {N} Patterns erstellt, {M} Duplikate uebersprungen."
```

**Frontmatter fuer M2-extrahierte Patterns:**

```yaml
source_tag: r_orchestrate
confidence: medium   # MAX: medium (INV-D5 Cap fuer r_orchestrate)
seed: false
status: experimental
needs_organic_validation: true
```

---

## Chain-Position

```
[_SC_implement 1.5g RED] --> [/_PT_extract] --> [/_Pre_PR_orchestrate Battle-Test]
       PT-TRIGGER                 DRAFT                PROMOTED
    (automatisch,              (persistiert,           (battle-tested,
     Code-Kontext)             Blueprint-Kandidat)      W257)

/_SC_implement 1.5g PT-TRIGGER-CHECK:
  RED-Klassifikation + Custom-Implementation
  -> Existiert .claude/commands/_PT_extract.md?
     JA: /_PT_extract ausfuehren (W246)
     NEIN: PT-SKIP (W245 offen)
```

**Prev:** _SC_implement 1.5g RED-Klassifikation (PT-Trigger, W246) ODER /_I_patternLibrary KEIN PATTERN
<!-- V14 (2026-05-08): _I_blueprintArchitect deprecated, ersetzt durch _I_patternLibrary -->

**Next:** /_Pre_PR_orchestrate (Battle-Test fuer PROMOTION, W257)

---

## Status-Schema (W258 Pattern-Maturity-System)

| Status | Beschreibung | Gesetzt durch | Persistiert? |
|--------|-------------|---------------|-------------|
| KANDIDAT | Mentale Notiz: Mensch erkennt wiederkehrendes Muster | Mensch (Review/Abnahme) | NEIN (nur im Kopf) |
| DRAFT | /_PT_extract hat Pattern automatisch registriert | /_PT_extract | JA (Libraries/PatternLibrary/_project/{LAYER}/{name}.md) |
| PROMOTED | /_Pre_PR_orchestrate Battle-Test bestanden. Alle Gates PASS. | /_Pre_PR_orchestrate (W257) | JA (status update) |
| MATURE | Mehrfach in Production genutzt, eigene Usage-Bounds bekannt. | /_PT_extract (W254) | JA (status update + bounds) |

**Transition-Matrix:** Siehe `_PT_update.md` Sektion "Transition-Matrix (RF-PT7, W258)" fuer die vollstaendige normative Transition-Matrix mit 4 Transitionen und Bedingungen.

**Konsistenz-Check:** _PT_extract MUSS das gleiche Frontmatter-Schema verwenden wie in der Transition-Matrix definiert:
- DRAFT: `status: draft`, `battle_test: pending` (von /_PT_extract gesetzt)
- PROMOTED: `status: promoted`, `battle_test: passed`, `promoted_at` (von _Pre_PR_orchestrate)
- MATURE: `status: mature`, `bounds:` Block (von /_PT_update Update-Modus)
- DEPRECATED: `status: deprecated`, `deprecated_reason:`, `deprecated_at:` (manuell, Evidenz-Pflicht)

---

## Schritte

### Schritt 0: Auto-Kontext-Ableitung (KERN-UNTERSCHIED zu /_PT_update, W259)

```
IF code-context-file angegeben:
  -> Lies die Datei direkt
  -> layer = Verzeichnis-Pfad analysieren:
       be-cont/ -> "be-cont"
       fe-comp/ -> "fe-comp"
       .claude/commands/ -> "cmd"
       test/ -> "test-unit"
       Fallback: Dateipfad-Segmente als Layer-Kuerzel
  -> pattern-name = Dateiname ohne Extension, kebab-case
  -> beschreibung = Erste Zeile/Kommentar/Zweck-Sektion der Datei

ELSE (kein code-context-file):
  -> Lies .claude/analysis/synthese/{NAME}-HYPOTHESEN.md
  -> Sektion "Durchgefuehrte Aenderungen":
       -> Extrahiere geaenderte Dateien (Spalte "Datei")
       -> code-context-file = letzte geaenderte Datei
  -> Sektion "Horizontale Suche" / "Blueprint":
       -> Extrahiere layer aus "Layer" oder "Ziel-Bereich"
       -> Falls Blueprint vorhanden: blueprint-pfad notieren
  -> pattern-name = letzter Dateiname ohne Extension, kebab-case
  -> beschreibung = IC-Beschreibung aus HYPOTHESEN.md

ENDIF

FALLBACK (Layer nicht ableitbar):
  -> layer = "cmd" (Default)
  -> WARNUNG: "Layer nicht automatisch erkannt, Default 'cmd' verwendet."

FALLBACK (pattern-name nicht ableitbar):
  -> AskUserQuestion "Pattern-Name (kebab-case)?"
  -> WARNUNG: "Pattern-Name konnte nicht abgeleitet werden."

# --parking-lot-walk Pfad (AK-B-6, BL-153, manuell)
IF --parking-lot-walk:
  # INV-D4 Guard (AK-C-1, BL-153): NUR Vault-PL-Items — KEIN Legacy-Glob
  # BLOCKER wenn Legacy-Pfad (.claude/_parking-lot.md) explizit uebergeben
  IF expliziter Pfad angegeben:
    IF Pfad enthaelt ".claude/_parking-lot.md" OR Pfad startswith ".claude/":
      BLOCKER: "[INV-D4] --parking-lot-walk BLOCKIERT: Legacy-Pfad '.claude/_parking-lot.md' verboten.
               Nur Vault-PL-Items erlaubt: {VAULT}/ParkingLotGlobal/*.md
               Begruendung: .claude/_parking-lot.md ist lokales Scratch-Pad (nicht Vault-Kontext)."
      RETURN  # Kein SKIP — INV-D4 ist hart (BLOCKER-Severity)
  # KORREKTE Quelle: Vault ParkingLotGlobal (INV-D4: Vault-Only)
  pl_quelle = "{VAULT}/ParkingLotGlobal/*.md"
  Lies Libraries/PatternLibrary/_index.md (oder .claude/patterns/_pl-index.md als Fallback)
  Lies Vault-PL-Items aus pl_quelle
  Suche PL-Items mit Tag "PT-Kandidat" oder Kategorie "Pattern"
  FÜR jeden gefundenen Kandidaten:
    code-context-file = PL-Item-Beschreibung / verknuepfte Datei
    source = "parking-lot"
    seed = false
    confidence = "low"
    → weiter mit Schritt 1 (Duplikat-Check) pro Kandidat
  Logge: "[PT_extract --parking-lot-walk] {N} Kandidaten gefunden (Vault-PL: {pl_quelle})."
```

### Schritt 1: Duplikat-Check

```
1. Lies Libraries/PatternLibrary/_index.md
2. Grep nach {pattern-name} (case-insensitive)
3. Falls TREFFER:
   -> WARNUNG: "Pattern '{pattern-name}' existiert bereits in _index.md."
   -> Suffix -v2 anhaengen (kein Abbruch, NON-BLOCKING)
   -> pattern-name = {pattern-name}-v2
4. Falls KEIN TREFFER: Weiter (neues Pattern)
```

### Schritt 2: Pattern-Datei erstellen

Erstelle `Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md`:

```markdown
---
id: PT-{LAYER-UPPER}-{NAME-UPPER}
type: pattern
scope: local
layer: {LAYER}
status: experimental
seed: false
confidence: low
applies_to: [{LAYER}]
severity: WARN
source_tag: r_orchestrate
extracted_from: {code-context-file}
date_added: {YYYY-MM-DD}
added_by: /_PT_extract
---

# Source-Tag → Confidence Mapping (AK-B-8, BL-153, aus frontmatter-schema.md)
# | Quelle                      | seed  | confidence |
# | codeKonvention/*.md         | true  | low        |
# | architekturKonventionen/*.md| true  | low        |
# | Parking-Lot (manuell)       | false | low        |
# | M2 deliberativ              | false | medium+    |
# | auto-extract (dieser Pfad)  | false | low        |

# {Pattern-Name (Title Case)}

## Zweck

{beschreibung — aus Auto-Kontext abgeleitet}

## Wann anwenden

- Trigger-Bedingung (abgeleitet aus Code-Kontext)

## Beispiel

{Konkretes Code-Beispiel aus der tatsaechlichen Implementation.
 Extrahiert aus code-context-file — KEIN Platzhalter.}

## Nicht anwenden wenn

- Anti-Pattern-Bedingung (aus Code-Kontext oder Graceful Degradation)

## Bekannte Verwendungen

- {feature}: {code-context-file} ({YYYY-MM-DD})

## Referenzen

- Erstellt von: /_PT_extract (Auto-Extraktion)
- Datum: {YYYY-MM-DD}
- Cluster: {cluster}
- W{n}-Bezug: {falls bekannt, sonst "keiner"}
- Naechster Schritt: PROMOTED wenn /_Pre_PR_orchestrate Battle-Test bestanden (3+ Verwendungen, 2+ Features)
```

**Verzeichnis-Erstellung:**
Falls `Libraries/PatternLibrary/_project/{LAYER}/` nicht existiert -> `mkdir -p Libraries/PatternLibrary/_project/{LAYER}/`

### Schritt 2.5: Confidence-Upgrade-Check (AK-B-9, BL-153)

```
# Nach Pattern-Datei-Erstellung: pruefe ob bestehende Patterns upgegradet werden sollen
# Gilt fuer Pattern-Knoten in Libraries/PatternLibrary/ (BL-153 Vault-Struktur)
# AK-B-9: low → medium nach 3+ bestaetigten Anwendungen

FÜR jeden bereits existierenden Pattern-Knoten der HEUTE benutzt wurde:
  usage_count = lies pattern_node.usage_count ?? 0
  IF confidence == "low" AND usage_count >= 3:
    Schreibe pattern_node.confidence = "medium"
    Logge: "[PT_extract] Confidence-Upgrade: {pattern_id} low→medium (usage_count={usage_count})"
    # OPTIONAL: ApplicationTrail-Eintrag erstellen (INV-D5)

# Fuer NEUE Patterns (auto-extract): Immer low starten (AK-B-8)
# medium nur durch explizites Upgrade (M2 deliberativ oder usage_count>=3)
```

### Schritt 3: pattern-usage.log aktualisieren

```
Datei: .claude/wissen/pattern-usage.log
Falls nicht vorhanden: Erstellen mit Header-Zeile.

Format:
  {YYYY-MM-DD} | {pattern-id} | {pattern-name} | {cluster} | DRAFT | auto-extract

Beispiel:
  2026-03-07 | P-CMD-AUTO-KONTEXT | auto-kontext | cmd | DRAFT | auto-extract
```

### Schritt 3.5: Referenz-Update bei VERIFIED (RF-MAT3, AC-MAT3-2)

```
1. Lies .claude/wissen/pattern-usage.log
   Suche: Eintrag mit {pattern-id} und Status VERIFIED
   → NICHT vorhanden oder pattern-usage.log fehlt: SKIP (Graceful Degradation)
   → VERIFIED-Eintrag gefunden: Weiter

2. Lies Pattern-Datei (Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md)
   Suche: Sektion "## Bekannte Verwendungen"

3. Extrahiere Code-Pfad aus VERIFIED-Eintrag in pattern-usage.log
   Format: {DATUM} | {pattern-id} | ... | VERIFIED | {feature}

4. Fuege Referenz hinzu in "## Bekannte Verwendungen":
   - {feature}: {code-context-file} ({DATUM}, VERIFIED)

5. Schwelle: >= 1 VERIFIED-Eintrag → Referenz-Befuellung PFLICHT (AC-MAT3-3)
   Referenz-Feld DARF NICHT dauerhaft leer bleiben nach VERIFIED-Nutzung (AC-MAT3-1)
```

### Schritt 4: _index.md aktualisieren

```
1. Lies Libraries/PatternLibrary/_index.md
2. Finde Sektion oder Table für neue Pattern-Einträge
3. Fuege neuen Eintrag hinzu:
   | `_project/{LAYER}/{pattern-name}.md` | {beschreibung} | PT-{LAYER}-{NAME} (experimental) | v1.0 |
4. Falls Konsumenten-Sektion existiert:
   -> Pruefe ob /_PT_extract bereits als Schreiber gelistet ist
   -> Falls NEIN: Hinzufuegen (Graceful: nur wenn Sektion erkennbar)
```

### Schritt 5: User-Feedback

```
Ausgabe:
  "Pattern '{pattern-name}' als DRAFT in {cluster}/ gespeichert."
  "  Datei: Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md"
  "  Status: DRAFT (W258 Maturity-System, Auto-Extraktion)"
  "  Quelle: {code-context-file} (Auto-Kontext-Ableitung)"
  "  Naechster Schritt: Battle-Test via /_Pre_PR_orchestrate fuer PROMOTION."
  "  pattern-usage.log: Eintrag hinzugefuegt."
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| HYPOTHESEN.md nicht lesbar | WARNUNG + Fallback: AskUserQuestion fuer code-context-file. NON-BLOCKING. |
| _pl-index.md existiert nicht | Pattern-Datei trotzdem erstellen. WARNUNG: "_pl-index.md nicht gefunden, Pattern nur als Datei gespeichert." pattern-usage.log Eintrag schreiben. |
| layer nicht ableitbar | Default "cmd". WARNUNG ausgeben. NON-BLOCKING. |
| pattern-name nicht ableitbar | Fallback: AskUserQuestion "Pattern-Name (kebab-case)?". NON-BLOCKING. |
| Duplikat gefunden | WARNUNG + Suffix -v2. NON-BLOCKING (kein Abbruch). |
| Libraries/PatternLibrary/_project/{LAYER}/ Verzeichnis fehlt | mkdir -p erstellen. |
| pattern-usage.log existiert nicht | Erstellen mit Header: `# Pattern Usage Log` + `# Format: DATUM | PATTERN-ID | NAME | CLUSTER | STATUS | QUELLE` |
| Code-Kontext-Datei nicht lesbar | WARNUNG + Beispiel-Sektion: "Kein Code-Beispiel verfuegbar (Datei nicht lesbar)". NON-BLOCKING. |

---

## Qualitaetskriterien

- VERTRAG-Block vorhanden (LIEST/SCHREIBT Sektionen)
- Auto-Kontext-Ableitung in Schritt 0 (KEIN AskUserQuestion fuer Pflichtfelder, W259)
- Status-Schema KANDIDAT/DRAFT/PROMOTED/MATURE dokumentiert (W258)
- Duplikat-Check gegen _pl-index.md als Guard
- Pattern-Datei-Format mit Frontmatter (id, status, cluster, battle_test, source, extracted_from)
- Echtes Code-Beispiel aus Code-Kontext (nicht Platzhalter)
- Schritte klar und ausfuehrbar (0-5)
- Graceful Degradation fuer fehlende Dateien/Verzeichnisse
- pattern-usage.log Eintrag fuer Audit-Trail (W250)

---

## Arch-Modus: usage_count Auto-Update (BL-154 AK-7-4)

> **EINSCHUB (BL-154, AK-7-4):** Bei architektonischen Patterns (Libraries/PatternLibrary/_project/
> {LAYER}/, Frontmatter `status: experimental|active|PROVEN`) ruft `_PT_extract` nach der
> Standard-Extraktion automatisch `_PT_update --arch-lifecycle {pattern_id} pfad-1` auf.
> Dies implementiert die "usage_count Aktualisierung automatisch" Anforderung (AK-7-4, W24, W8).

```
# Arch-Modus Auto-Update (AK-7-4)
# EINSCHUB nach Schritt 3 (pattern-usage.log) fuer arch. Patterns

IF pattern_ist_architektonisch(pattern_path):
  # Erkennung: Dateipfad enthaelt 'Libraries/PatternLibrary/_project/'
  # UND Frontmatter.status IN ["experimental","active","PROVEN"]
  pattern_fm = lies_frontmatter(pattern_path)
  IF pattern_fm.status IN ["experimental", "active", "PROVEN"]:
    Logge: "[PT_extract AK-7-4] Arch-Pattern erkannt → usage_count Auto-Update via _PT_update Pfad-1"
    # Delegiere an _PT_update --arch-lifecycle fuer konsistente Lifecycle-Logik
    # (Schwellwerte, Status-Upgrade experimental→active@5, active→PROVEN@10,
    #  ApplicationTrail-Erstellung bei PROVEN — AK-7-3)
    /_PT_update --arch-lifecycle {pattern_id} pfad-1
    Logge: "[PT_extract AK-7-4] usage_count aktualisiert. Status-Upgrade geprft. Trail-Check DONE."
  ELSE:
    Logge: "[PT_extract AK-7-4] Pattern status={pattern_fm.status} — kein arch. Auto-Update (Semantic oder unbekannt)."
```

**Invarianten:**
- INV-AK-7-4-1: Arch-Update NUR wenn `_project/{LAYER}/` im Pfad UND semantischer Status.
- INV-AK-7-4-2: Delegation an `_PT_update --arch-lifecycle pfad-1` fuer ALLE Lifecycle-Logik (keine Duplizierung).
- INV-AK-7-4-3: Semantic Patterns (`.claude/patterns/` DEPRECATED oder `_generic/`) sind NICHT betroffen.

---

## Abgrenzung

```
/_PT_update      = Pattern REGISTRIEREN (KANDIDAT -> DRAFT, manuell, AskUserQuestion)
/_PT_extract     = Pattern EXTRAHIEREN aus Code-Kontext (Auto-Ableitung, PT-Trigger, W259)
/_PT_init        = Pattern Library INITIALISIEREN (Template-Setup, W252)
/_PT_arch_init   = Arch. Pattern Library INITIALISIEREN (Initial-Bootstrap, BL-154)

Kernunterschied /_PT_extract vs /_PT_update:
  - Schritt 0: Auto-Kontext-Ableitung (/_PT_extract) vs AskUserQuestion (/_PT_update)
  - source: "auto-extract" (/_PT_extract) vs "review|abnahme|beobachtung" (/_PT_update)
  - Duplikat: Suffix -v2 (/_PT_extract) vs User-Entscheidung (/_PT_update)
  - Schritte 1-5: Identische Struktur (Reuse)
  - Arch-Modus: usage_count Auto-Update via _PT_update Pfad-1 (AK-7-4, BL-154)
```

---

## Siehe auch

- [[_SC_implement]] - Schritt 1.5g: PT-TRIGGER-CHECK (Trigger fuer /_PT_extract)
- [[_PT_update]] - Manuelles Pattern-Registrierung (Blueprint fuer Schritte 1-5)
- [[_pattern-library]] - Bestehender Pattern-Katalog
- [[_pl-index]] - Pattern Library Index (Routing + Konsumenten)
- [[_Pre_PR_orchestrate]] - Battle-Test Gate fuer PROMOTION (W257)

---

ARGUMENTS: $ARGUMENTS
