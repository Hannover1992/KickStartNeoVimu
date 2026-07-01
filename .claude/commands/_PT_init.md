---
type: building-block
---

# /_PT_init

**Status:** v1.0.0 (W245 KERN-BLOCKER geloest — PT-Command-Familie 3/3 komplett)
**Actor:** PATTERN-INITIALIZER
**Zweck:** Initialisiert die Pattern Library bei Projektstart durch Template-Copy aus dem Obsidian Vault oder lokalem Fallback. Erstes Glied der PT-Command-Familie: /_PT_init (einmalig) vor /_PT_update (laufend) und /_PT_extract (automatisch).

> **DEPRECATED (ARCH-4, BL-153, 2026-05-01):** `.claude/patterns/` ist der
> Legacy-Initialisierungspfad. Canonical Pattern-Library ist seit BL-151
> `Libraries/PatternLibrary/` im Vault. `_PT_init` NICHT für neue Projekte
> verwenden — `Libraries/PatternLibrary/` muss direkt erstellt werden (Vault-Struktur).
> Bestehende `.claude/patterns/` Einträge via `_PT_seedImport` nach
> `Libraries/PatternLibrary/` migrieren.

---

## Aufruf

```
/_PT_init [NAME] [--force]
```

| Parameter | Pflicht | Format | Beispiel |
|-----------|---------|--------|----------|
| NAME | NEIN (Auto-Ableitung aus Projekt-Kontext) | PascalCase oder kebab-case | `OmniCommand`, `DCSRE` |
| --force | NEIN | Flag (kein Wert) | `--force` (Ueberschreibung bei bestehender PL) |

**Beispiele:**

```
/_PT_init OmniCommand           # Initialisiert PL fuer Projekt OmniCommand
/_PT_init                       # Auto-Ableitung des Projekt-Namens
/_PT_init OmniCommand --force   # Ueberschreibt bestehende PL-Struktur
```

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_PT_init [NAME] [--force]                           |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. .claude/patterns/_pl-index.md                            |
|       -> Cluster-Struktur (Sektion 2.3 Layer-Routing)          |
|       -> Verzeichnis-Taxonomie (Sektion 1)                     |
|    2. $OBSIDIAN_VAULT_PATH/patterns/ (Template-Quelle)         |
|       -> Vault-Patterns als Kopier-Vorlage                     |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    3. .claude/models/{NAME}_Model.md                           |
|       -> Projekt-Name Auto-Ableitung                           |
|    4. .claude/templates/pattern-library/                       |
|       -> Lokaler Template-Fallback                             |
|    5. .claude/patterns/_pattern-library.md                     |
|       -> Bestehender Library-Stand (bei --force)               |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. .claude/patterns/ (Verzeichnisstruktur)                  |
|       -> Cluster-Unterverzeichnisse gemaess _pl-index.md 2.3   |
|    2. .claude/patterns/_pattern-library.md                     |
|       -> Pattern-Katalog (kopiert oder initialisiert)          |
|    3. .claude/patterns/_pl-index.md                            |
|       -> Projekt-spezifisch angepasster Index                  |
|    4. .claude/wissen/pattern-usage.log                         |
|       -> INIT-Eintrag (W250 Audit-Trail)                       |
|    5. .claude/patterns/.pt_hash_baseline                       |
|       -> Hash-Baseline fuer Sync-Pruefung (W253)               |
|                                                                |
|  ACTOR: PATTERN-INITIALIZER                                    |
|    Fuehrt einmalige Template-Copy bei Projektstart durch.      |
|    Erstellt Verzeichnisstruktur, kopiert Templates,            |
|    setzt Projekt-Frontmatter und Hash-Baseline.                |
|    Kein laufender Update — nur Initialisierung.                |
|                                                                |
|  SCHREIBT NICHT (canonical path):                              |
|    Libraries/PatternLibrary/ (Vault-Canonical — nicht von init)|
|                                                                |
+===============================================================+
```

---

## Chain-Position

```
[Neues Projekt] --> [/_PT_init] --> [/_PT_update / /_PT_extract / /_SC_implement]
     SETUP             INIT                    LAUFEND
  (kein PL-            (Template-Copy,         (Pattern registrieren,
   Verzeichnis)         Verzeichnisstruktur,    extrahieren, nutzen)
                        Hash-Baseline)

/_PT_init = EINMALIG bei Projektstart (oder --force bei Reset)
/_PT_update = MANUELL, laufend (Mensch findet Pattern → DRAFT)
/_PT_extract = AUTOMATISCH, post-impl (1.5g PT-Trigger → DRAFT)
```

**Prev:** Neues Projekt angelegt (kein .claude/patterns/ Verzeichnis vorhanden)
**Next:** /_PT_update (manuelle Pattern-Registrierung) ODER /_PT_extract (automatische Extraktion)

---

## Status-Schema (W258 Pattern-Maturity-System)

| Status | Beschreibung | Gesetzt durch | Persistiert? |
|--------|-------------|---------------|-------------|
| KANDIDAT | Mentale Notiz: Mensch erkennt wiederkehrendes Muster | Mensch (Review/Abnahme) | NEIN (nur im Kopf) |
| DRAFT | /_PT_update oder /_PT_extract hat Pattern registriert | /_PT_update / /_PT_extract | JA (.claude/patterns/{cluster}/{name}.md) |
| PROMOTED | /_Pre_PR_orchestrate Battle-Test bestanden. Alle Gates PASS. | /_Pre_PR_orchestrate (W257) | JA (status update) |
| MATURE | Mehrfach in Production genutzt, eigene Usage-Bounds bekannt. | /_PT_extract (W254) | JA (status update + bounds) |

---

## Schritte

### Schritt 0: Pre-Check (Duplikat-Schutz + Guards)

```
1. Pruefe ob .claude/patterns/ bereits existiert:
   IF .claude/patterns/ EXISTIERT:
     IF --force NICHT gesetzt:
       -> WARNUNG: "Pattern Library existiert bereits unter .claude/patterns/."
       -> "Verwende --force um die bestehende Struktur zu ueberschreiben."
       -> STOPP (Duplikat-Schutz aktiv)
     ELSE (--force gesetzt):
       -> WARNUNG: "Force-Modus aktiv. Bestehende PL wird ueberschrieben."
       -> FORTFAHREN (bestehende Dateien werden ueberschrieben)
   ELSE:
     -> .claude/patterns/ existiert NICHT → Normaler Init-Pfad
     -> FORTFAHREN

2. $OBSIDIAN_VAULT_PATH Guard (W248):
   IF $OBSIDIAN_VAULT_PATH definiert UND Pfad existiert:
     -> vault_available = TRUE
     -> TEMPLATE_SOURCE = "$OBSIDIAN_VAULT_PATH/patterns/"
   ELSE:
     -> vault_available = FALSE
     -> WARNUNG: "$OBSIDIAN_VAULT_PATH nicht definiert oder Pfad nicht erreichbar."
     -> Fallback in Schritt 1

3. Pruefe _pl-index.md auf Cluster-Definitionen:
   IF .claude/patterns/_pl-index.md existiert (lokal oder in Template-Quelle):
     -> cluster_definitions = Sektion 2.3 Layer-Routing auslesen
   ELSE:
     -> WARNUNG: "_pl-index.md nicht gefunden. Minimaler Index wird erstellt."
     -> cluster_definitions = DEFAULT_CLUSTERS (siehe Graceful Degradation)
```

### Schritt 1: Template-Quelle lokalisieren

```
Priorisierungs-Reihenfolge (Wasserfall):

PRIORITAET 1: Obsidian Vault (W252 Template-Copy, W253 Hash-Sync)
  IF vault_available == TRUE:
    source_path = "$OBSIDIAN_VAULT_PATH/patterns/"
    IF source_path enthaelt mindestens _pattern-library.md ODER _pl-index.md:
      -> TEMPLATE_SOURCE = source_path
      -> source_type = "obsidian-vault"
      -> Notiere: "Template-Quelle: Obsidian Vault ($OBSIDIAN_VAULT_PATH/patterns/)"
    ELSE:
      -> WARNUNG: "Obsidian Vault erreichbar aber /patterns/ leer oder unvollstaendig."
      -> Fallback auf PRIORITAET 2

PRIORITAET 2: Lokale Template-Ablage
  IF .claude/templates/pattern-library/ existiert:
    source_path = ".claude/templates/pattern-library/"
    IF source_path enthaelt mindestens 1 .md Datei:
      -> TEMPLATE_SOURCE = source_path
      -> source_type = "local-template"
      -> Notiere: "Template-Quelle: Lokale Ablage (.claude/templates/pattern-library/)"
    ELSE:
      -> WARNUNG: "Lokale Template-Ablage leer."
      -> Fallback auf PRIORITAET 3

PRIORITAET 3: Minimal-Bootstrap
  -> TEMPLATE_SOURCE = NONE
  -> source_type = "minimal-bootstrap"
  -> Notiere: "Keine Template-Quelle gefunden. Minimal-Bootstrap aktiv."
  -> Nur Shell-Dateien (_pl-index.md + _pattern-library.md Grundgeruest)

Hash-Berechnung (W253):
  IF source_type != "minimal-bootstrap":
    -> Berechne MD5/SHA256 der Template-Dateien
    -> template_hash = Hash-Wert
    -> Notiere fuer Schritt 6 (Hash-Baseline)
```

### Schritt 2: Verzeichnisstruktur erstellen

```
1. mkdir -p .claude/patterns/ (Root-Verzeichnis)

2. Lies Cluster-Definitionen aus _pl-index.md Sektion 2.3:
   Erwartete Cluster (Default):
     be-cont   (Backend Controller)
     be-core   (Backend Core/Service)
     be-dto    (Backend DTO/Mapping)
     be-map    (Backend Mapping)
     be-mid    (Backend Middleware)
     fe-comp   (Frontend Component)
     fe-svc    (Frontend Service)
     db-ent    (Database/Entity)
     test-unit (Tests Unit)
     test-int  (Tests Integration)
     cmd       (Commands/CLI)
     arch      (Architektur)

3. Fuer jeden Cluster:
   mkdir -p .claude/patterns/{cluster}/

4. Zaehle erstellte Verzeichnisse:
   dirs_created = Anzahl der neu erstellten Cluster-Verzeichnisse
```

### Schritt 3: Template-Dateien kopieren

```
IF source_type == "obsidian-vault" OR source_type == "local-template":

  1. _pattern-library.md kopieren:
     IF TEMPLATE_SOURCE/_pattern-library.md existiert:
       -> Kopiere nach .claude/patterns/_pattern-library.md
       -> files_copied += 1
     ELSE:
       -> Erstelle minimale _pattern-library.md (Shell, siehe Schritt 4)

  2. _pl-index.md kopieren/anpassen:
     IF TEMPLATE_SOURCE/_pl-index.md existiert:
       -> Kopiere nach .claude/patterns/_pl-index.md
       -> files_copied += 1
     ELSE:
       -> Erstelle minimale _pl-index.md (Shell, siehe Schritt 4)

  3. Cluster-Pattern-Dateien kopieren:
     FOR EACH Datei in TEMPLATE_SOURCE/{cluster}/*.md:
       -> Kopiere nach .claude/patterns/{cluster}/{dateiname}.md
       -> files_copied += 1
     ENDFOR

  4. Zaehle:
     files_total = files_copied
     Notiere: "{files_total} Dateien aus Template-Quelle kopiert."

ELSE IF source_type == "minimal-bootstrap":

  1. Erstelle minimale _pattern-library.md:
     -> Header + Uebersicht + leerer Pattern-Katalog
     -> files_created = 1

  2. Erstelle minimale _pl-index.md:
     -> Header + Verzeichnis-Taxonomie + leere Sektionen
     -> files_created += 1

  3. files_total = files_created
     Notiere: "Minimal-Bootstrap: {files_total} Shell-Dateien erstellt."

ENDIF
```

### Schritt 4: Projekt-Anpassung

```
1. Frontmatter-Felder in _pattern-library.md setzen/aktualisieren:
   ---
   project: {NAME}
   date_initialized: {YYYY-MM-DD}
   initialized_by: /_PT_init
   version: "1.0.0"
   source_type: {obsidian-vault|local-template|minimal-bootstrap}
   ---

2. Frontmatter-Felder in _pl-index.md setzen/aktualisieren:
   ---
   project: {NAME}
   date_initialized: {YYYY-MM-DD}
   initialized_by: /_PT_init
   ---

3. Falls NAME nicht angegeben:
   -> Versuche Auto-Ableitung:
      a) Lies .claude/models/*_Model.md → Extrahiere Projekt-Name aus Dateiname
      b) Lies CLAUDE.md → Suche nach Projekt-Bezeichnung
      c) Fallback: Verzeichnisname des Projekt-Roots
   -> NAME = abgeleiteter Projekt-Name

4. Projekt-spezifische Layer in _pl-index.md:
   -> Pruefe welche Layer im Projekt tatsaechlich vorkommen
   -> Markiere ungenutzte Layer als "(leer)" in Sektion 2.3
```

### Schritt 5: pattern-usage.log initialisieren (W250)

```
Datei: .claude/wissen/pattern-usage.log

1. Erstelle Header:
   # Pattern Usage Log
   # Format: DATUM | PATTERN-ID | NAME | CLUSTER | STATUS | QUELLE
   # Erstellt von: /_PT_init ({YYYY-MM-DD})

2. Schreibe INIT-Eintrag:
   {YYYY-MM-DD} | PT_INIT | project={NAME}, source={source_type} | {files_total} Dateien | /_PT_init v1.0.0

3. Notiere: "pattern-usage.log initialisiert mit INIT-Eintrag."
```

### Schritt 6: Hash-Baseline setzen (W253)

```
Datei: .claude/patterns/.pt_hash_baseline

1. Berechne Hash ueber alle kopierten/erstellten Pattern-Dateien:
   Fuer jede Datei in .claude/patterns/**/*.md:
     -> hash = SHA256(Datei-Inhalt)
     -> Speichere: {relativer_pfad} | {hash} | {YYYY-MM-DD}

2. Schreibe .pt_hash_baseline:
   # PT Hash Baseline
   # Erstellt von: /_PT_init ({YYYY-MM-DD})
   # Projekt: {NAME}
   # Source: {source_type}
   # Template-Hash: {template_hash} (falls vorhanden)
   #
   # Format: PFAD | SHA256 | DATUM
   _pattern-library.md | {hash} | {YYYY-MM-DD}
   _pl-index.md | {hash} | {YYYY-MM-DD}
   {cluster}/{pattern-name}.md | {hash} | {YYYY-MM-DD}
   ...

3. Notiere: "Hash-Baseline gesetzt ({N} Eintraege) unter .claude/patterns/.pt_hash_baseline"

4. Zweck der Hash-Baseline:
   -> _SC_orchestrate kann pruefen ob Patterns seit Init geaendert wurden
   -> _W_obsidianSync kann Delta zum Vault berechnen (W253)
   -> _PT_update/_PT_extract koennen Aenderungs-Tracking nutzen
```

### Schritt 7: User-Feedback

```
Ausgabe:
  "Pattern Library fuer '{NAME}' initialisiert."
  ""
  "  Quelle:           {source_type} ({TEMPLATE_SOURCE oder 'Minimal-Bootstrap'})"
  "  Dateien kopiert:   {files_total}"
  "  Cluster erstellt:  {dirs_created}"
  "  Hash-Baseline:     .claude/patterns/.pt_hash_baseline ({N} Eintraege)"
  "  Usage-Log:         .claude/wissen/pattern-usage.log (INIT-Eintrag)"
  ""
  "  Naechste Schritte:"
  "    - /_PT_update {pattern-name} {cluster}  → Pattern manuell registrieren"
  "    - /_PT_extract                          → Pattern automatisch extrahieren"
  "    - /_SC_implement (1.5g PT-Trigger)      → Pattern aus Implementation ableiten"
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| Template-Quelle NICHT GEFUNDEN (Obsidian + lokal) | Minimal-Bootstrap: Nur Shell-Dateien (_pattern-library.md + _pl-index.md Grundgeruest). WARNUNG ausgeben. Alle Schritte ausfuehrbar — nur mit leeren Templates. |
| Obsidian Vault nicht erreichbar ($OBSIDIAN_VAULT_PATH fehlt oder Pfad ungueltig) | Fallback auf lokale Template-Ablage (.claude/templates/pattern-library/). Falls auch nicht vorhanden: Minimal-Bootstrap. WARNUNG ausgeben. |
| .claude/patterns/ EXISTIERT bereits (ohne --force) | STOPP mit Meldung: "Pattern Library existiert bereits. Verwende --force fuer Ueberschreibung." Kein Datenverlust. |
| .claude/patterns/ EXISTIERT bereits (mit --force) | FORTFAHREN: Bestehende Dateien werden ueberschrieben. WARNUNG: "Force-Modus aktiv." Hash-Baseline wird neu berechnet. |
| _pl-index.md FEHLT (weder lokal noch in Template-Quelle) | Erstelle minimalen Index mit Default-Clustern (be-cont, be-core, fe-comp, fe-svc, test-unit, cmd). WARNUNG: "Minimaler _pl-index.md erstellt — manuelle Anpassung empfohlen." |
| NAME nicht ableitbar (kein Parameter, kein Model, kein CLAUDE.md) | Fallback: Verzeichnisname des Projekt-Roots. WARNUNG: "Projekt-Name nicht erkannt, verwende Verzeichnisname." |
| Hash-Berechnung fehlgeschlagen | WARNUNG: "Hash-Baseline konnte nicht berechnet werden." .pt_hash_baseline wird mit Platzhalter erstellt. Init wird NICHT abgebrochen. |

**DEFAULT_CLUSTERS (fuer Minimal-Bootstrap):**

```
be-cont, be-core, be-dto, be-map, be-mid,
fe-comp, fe-svc,
db-ent,
test-unit, test-int,
cmd, arch
```

---

## Qualitaetskriterien

- Pre-Check: Duplikat-Schutz aktiv (Schritt 0: STOPP bei bestehender PL ohne --force)
- Template-Quelle: 3-stufiger Wasserfall (Obsidian → Lokal → Minimal-Bootstrap)
- Hash-Baseline: Gesetzt nach erfolgreicher Init (W253, Schritt 6)
- pattern-usage.log: INIT-Eintrag vorhanden (W250, Schritt 5)
- Graceful Degradation: Alle 7 Szenarien behandelt
- Verzeichnisstruktur: Cluster-Verzeichnisse aus _pl-index.md 2.3 erstellt
- Projekt-Anpassung: Frontmatter mit project + date_initialized gesetzt

---

## Abgrenzung

```
/_PT_init        = Pattern Library INITIALISIEREN (einmalig, Projektstart, Template-Copy, W252)
/_PT_update      = Pattern REGISTRIEREN (KANDIDAT -> DRAFT, manuell, laufend, AskUserQuestion)
/_PT_extract     = Pattern EXTRAHIEREN aus Code-Kontext (automatisch, PT-Trigger, W259)

Kernunterschied /_PT_init vs /_PT_update/_PT_extract:
  - /_PT_init: EINMALIG bei Projektstart (oder --force Reset)
  - /_PT_update: LAUFEND, manuell (Mensch findet Pattern)
  - /_PT_extract: LAUFEND, automatisch (1.5g PT-Trigger nach Implement)

  - /_PT_init erstellt STRUKTUR (Verzeichnisse, Templates, Hash-Baseline)
  - /_PT_update/_PT_extract erstellen INHALTE (einzelne Pattern-Dateien)
```

---

## Siehe auch

- [[_PT_update]] - Manuelles Pattern-Registrierung (DRAFT, laufend)
- [[_PT_extract]] - Automatische Pattern-Extraktion (DRAFT, post-impl)
- [[_pattern-library]] - Bestehender Pattern-Katalog
- [[_pl-index]] - Pattern Library Index (Routing + Konsumenten)
- [[_SC_implement]] - Schritt 1.5g: PT-TRIGGER-CHECK
- [[_Pre_PR_orchestrate]] - Battle-Test Gate fuer PROMOTION (W257)
- [[_W_obsidianSync]] - Obsidian Sync (nutzt Hash-Baseline aus /_PT_init)

---

ARGUMENTS: $ARGUMENTS
