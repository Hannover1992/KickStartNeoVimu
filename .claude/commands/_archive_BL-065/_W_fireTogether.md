---
type: building-block
version: 1.0.0
created: 2026-04-02
updated: 2026-04-06
status: obsolet
deprecated: true
obsoleted_by: BL-050
obsoleted_reason: "BL-045 Vault-First Write — Commands schreiben direkt in Vault, kein Post-Synthese-Sync mehr noetig"
op: ObsidianFirst_FireTogether
phase: Post-Synthese
depends_on:
  - .claude/meta/adr/ADR-ObsidianFirst-Ablageort.md (RF-01, Vault-Pfade + Artefakt-Taxonomie)
  - .claude/commands/_W_obsidianSync.md (Hash-Check Pattern, Frontmatter-Schema, Guards)
  - .claude/config/vault-routing.json (5-stufige Vault-Pfad-Aufloesung)
  - .claude/models/ObsidianFirst_FireTogether_Model.md (W6-W9, W16-W19, W23, W35)
  - .claude/analysis/synthese/ObsidianFirst_FireTogether-SPEC.md (RF-02, AK-03..AK-07)
ak_coverage: AK-03, AK-04, AK-05, AK-06, AK-07
---

# /_W_fireTogether - Satellit-Command: Synthese → Vault + Verdrahtung

**Status:** v1.0.0
**Actor:** FIRE-TOGETHER-SYNCER
**Zweck:** Nach JEDER Synthese (Model, Spec, GAP, Wissen) das Ergebnis in den Obsidian-Vault schreiben, bidirektionale Links pflegen und Knoten im selben Zyklus verdrahten (Hebb-Prinzip: "Fired together — wired together").

**Abgrenzung zu _W_obsidianSync:** Fire-Together ist der PRIMAERE Sync-Pfad fuer Synthese-Outputs. _W_obsidianSync bleibt fuer Legacy/Standalone/Hard-Sync (Guards, Mermaid, Full-Chain-Validierung). Fire-Together ERGAENZT, ERSETZT NICHT.

---

## Vertrag

```
+======================================================================+
|  COMMAND: /_W_fireTogether {FEATURE} {SYNTHESE_TYP}                   |
|           [--force] [--dry-run]                                       |
+======================================================================+
|                                                                       |
|  KERN-PRINZIP:                                                        |
|    Nach JEDER Synthese: Ergebnis sofort in den Vault schreiben.      |
|    Bidirektionale Links pflegen. Zyklus-Knoten verdrahten.           |
|    Idempotent: gleicher Input-Hash = Skip. (W6, W8)                  |
|                                                                       |
|  LIEST (Input):                                                       |
|    1. Synthese-Output aus .claude/:                                   |
|       - .claude/models/{FEATURE}_Model.md          (Typ: model)      |
|       - .claude/analysis/synthese/{FEATURE}-SPEC.md (Typ: spec)      |
|       - .claude/analysis/synthese/{FEATURE}-GAP.md  (Typ: gap)      |
|       - .claude/wissen/{THEMA}_Wissen.md            (Typ: wissen)    |
|    2. /home/uczen/Documents/DCS/OmniCommand/_manifest.md                                   |
|       → anchor_nodes (Schema W19: file, match_score, relation,       |
|         match_keywords, match_wn, hop, source, merged_into)          |
|       → SC_PIPELINE_STATE (cycle_nr fuer Hebb-Verdrahtung)          |
|    3. Vault-Nachbar-Knoten:                                           |
|       → Ankerknoten-Dateien im Vault (via anchor_nodes.file)         |
|       → Bestehende Frontmatter lesen (based-on, anchor-of,          |
|         co-created-with, cycle-cluster)                               |
|    4. .claude/config/vault-routing.json                               |
|       → Vault-Root bestimmen (5-stufige Pfad-Aufloesung)            |
|    5. .claude/meta/adr/ADR-ObsidianFirst-Ablageort.md                |
|       → Artefakt-Taxonomie: Vault-Zielordner pro Typ                |
|                                                                       |
|  SCHREIBT (Output):                                                   |
|    1. Synthese-Dokument in Vault:                                     |
|       → {VAULT}/{DATEINAME}.md (Typ-basierter Zielordner, RF-01)    |
|       → MIT Obsidian-Frontmatter (Tags, Links, Chain-Metadaten)     |
|    2. Bidirektionale Links in Nachbar-Knoten:                         |
|       → anchor-of Rueckverweise in Ankerknoten (W16, W23)           |
|       → based-on Vorwaerts-Verweise im Synthese-Dokument            |
|    3. Hebb-Verdrahtung in Zyklus-Knoten:                              |
|       → co-created-with + cycle-cluster Frontmatter (W17, W9)       |
|       → Fuer ALLE Knoten im selben Zyklus (G-COWORK Pattern)        |
|    4. .claude/analysis/_vault_index.md (Knoten-Index, RF-07):         |
|       → Inkrementelles Update (kein Full-Scan)                       |
|       → Pfad, Typ, letzte Aktualisierung, Nachbar-Links             |
|    5. /home/uczen/Documents/DCS/OmniCommand/_manifest.md:                                   |
|       → fire_together_status Einzeiler (letzter Sync, Hash)         |
|                                                                       |
|  INVARIANTEN:                                                         |
|    - INV-1: Vault = SSoT fuer persistente Artefakte (W1)            |
|    - INV-2: Nur Synthese-Ergebnisse werden persistiert (W2)          |
|    - INV-3: Fire-Together nach JEDER Synthese (W6)                   |
|    - INV-5: Bidirektionale Verbindungen (based-on/anchor-of, W16)   |
|    - INV-6: Hebb-Prinzip (co-created-with/cycle-cluster, W17)       |
|    - Idempotenz: gleicher md5sum = Skip (W8)                         |
|    - Forward-Only: kein Retrofit bestehender Dokumente (W4)          |
|    - Kein Sub-Agent-Spawn (W7-Constraint)                            |
|                                                                       |
|  PIPELINE-POSITION:                                                   |
|    Wird von Orchestratoren NACH Synthese aufgerufen:                 |
|    - _SC_orchestrate: nach Model-Synthese, nach Spec-Synthese        |
|    - _I_orchestrate: nach GAP-Synthese                                |
|    - _A_orchestrate: nach Model-Synthese, nach Spec-Synthese         |
|    - _WP_orchestrate: nach Wissen-Synthese                            |
|    (RF-09, W21 Trigger-Punkte)                                       |
|                                                                       |
+======================================================================+
```

---

## Parameter

```
/_W_fireTogether {FEATURE} {SYNTHESE_TYP} [--force] [--dry-run]
```

| Parameter | Default | Werte | Beschreibung |
|---|---|---|---|
| `FEATURE` | (PFLICHT) | String | Feature-Name (z.B. ObsidianFirst_FireTogether) |
| `SYNTHESE_TYP` | (PFLICHT) | model, spec, gap, wissen | Welcher Synthese-Output synchronisiert wird |
| `--force` | false | Flag | Hash-Check ueberspringen, immer schreiben |
| `--dry-run` | false | Flag | Nur pruefen, nichts schreiben. Zeigt was passieren wuerde |

**Beispiele:**
```
/_W_fireTogether ObsidianFirst_FireTogether model      → Model-Synthese in Vault
/_W_fireTogether DCSRE-93 spec                          → Spec-Synthese in Vault
/_W_fireTogether OmniCommand gap --force                → GAP erzwingen (kein Hash-Check)
/_W_fireTogether WissensKoaleszenz wissen --dry-run     → Trockenlauf
```

---

## Quell-Pfad-Aufloesung (SYNTHESE_TYP → Datei)

| SYNTHESE_TYP | Quell-Pfad | Vault-Zielordner |
|---|---|---|
| model | `.claude/models/{FEATURE}_Model.md` | `{VAULT}/` |
| spec | `.claude/analysis/synthese/{FEATURE}-SPEC.md` | `{VAULT}/` |
| gap | `.claude/analysis/synthese/{FEATURE}-GAP.md` | `{VAULT}/` |
| wissen | `.claude/wissen/{FEATURE}_Wissen.md` | `{VAULT}/` |

**Vault-Root:** Via vault-routing.json (Stufe 1), dann $OBSIDIAN_VAULT_PATH (Stufe 2), dann Default `/home/uczen/Documents/DCS` (Stufe 4). Identische 5-stufige Aufloesung wie _W_obsidianSync.

**Dateiname im Vault:** Identisch mit Quell-Dateiname (keine Umbenennung).

---

## Ausfuehrungs-Sequenz (6 Schritte, W18)

### Schritt 1: Synthese-Output lesen

```
1. Bestimme Quell-Pfad aus SYNTHESE_TYP (siehe Tabelle oben)
2. Pruefe: Quell-Datei existiert?
   → NEIN: FEHLER "Synthese-Output nicht gefunden: {PFAD}"
   → JA: Lese Datei-Inhalt vollstaendig
3. Extrahiere bestehende Frontmatter (falls vorhanden)
```

### Schritt 2: Ankerknoten aus Manifest lesen

```
1. Lese /home/uczen/Documents/DCS/OmniCommand/_manifest.md
2. Suche Sektion "## W_fetch Ankerpunkte"
   → Nicht gefunden: INFO "Keine Ankerpunkte. Verdrahtung nur via Hebb-Prinzip."
   → Gefunden: Parse anchor_nodes YAML-Block
3. Fuer jeden anchor_node:
   → Extrahiere: file, relation, match_keywords
   → Filtere: nur merged_into=false (noch nicht gemergte Knoten)
4. Lese SC_PIPELINE_STATE → cycle_nr (fuer Hebb-Verdrahtung in Schritt 6)
   → Nicht gefunden: cycle_nr = 1 (Default)
```

### Schritt 3: Nachbar-Knoten im Vault lesen

```
1. Bestimme Vault-Root (vault-routing.json, 5-stufig)
   → FEHLER wenn kein Vault gefunden: STOPP mit WARNING (kein silent degraded mode)
2. Fuer jeden Ankerknoten (aus Schritt 2):
   → Lese Vault-Datei: {VAULT}/{anchor_node.file}
   → Extrahiere Frontmatter: based-on, anchor-of, co-created-with, cycle-cluster
   → Falls Datei nicht existiert: WARNUNG + ueberspringen (Graceful Degradation)
3. Identifiziere Zyklus-Gruppe (alle Vault-Dateien mit cycle = cycle_nr):
   → {FEATURE}-OBSERVE{N}.md, {FEATURE}-QUALITYGATE{N}.md, etc.
   → Fuer Hebb-Verdrahtung in Schritt 6
```

### Schritt 4: Content-Hash berechnen (Idempotenz-Check)

```
1. Berechne md5sum des Synthese-Outputs (Quell-Datei aus Schritt 1)
2. Lese bestehenden Hash aus Manifest (fire_together_status)
   ODER aus Vault-Datei Frontmatter (content-hash Feld)
3. Vergleich:
   → GLEICH und KEIN --force: SKIP
     Ausgabe: "Hash unveraendert ({HASH}). Skip. Nutze --force zum Erzwingen."
     → ENDE (Schritt 5+6 werden uebersprungen)
   → UNTERSCHIEDLICH oder --force oder FEHLT: Weiter zu Schritt 5
4. Bei --dry-run: Ausgabe was passieren wuerde, dann ENDE
```

### Schritt 5: Synthese-Dokument in Vault schreiben

```
1. Generiere Obsidian-Frontmatter (YAML-Block am Dateianfang):

   ---
   type: {model|spec|gap|knowledge}
   feature: {FEATURE}
   created: {DATUM_ERSTELLT oder bestehendes created}
   updated: {DATUM_HEUTE}
   content-hash: {MD5SUM aus Schritt 4}
   source: .claude/{QUELL_PFAD}
   based-on:
     - "[[{ANKERKNOTEN_1}]]"
     - "[[{ANKERKNOTEN_2}]]"
   tags:
     - type/{SYNTHESE_TYP}
     - feature/{FEATURE_SLUG}
     - op/fire-together
   chain-position: {model|spec|gap|knowledge}
   cycle: {CYCLE_NR}
   ---

2. Bestimme Vault-Zielordner (aus ADR-ObsidianFirst-Ablageort Tabelle)
3. Schreibe Datei: {VAULT}/{ZIELORDNER}/{DATEINAME}.md
   → Frontmatter + Quell-Inhalt (Frontmatter des Quell-Dokuments wird ERSETZT)
4. Setze File-Permissions: 644 (lesbar fuer Obsidian)

5. BL-Ordner-Routing (BL-034, RF-02: AK-02-01..04):
   # Nach Vault-Schreiben: Zusaetzliche Kopie in BL-Item-Ordner
   # NUR wenn: (a) BL-Item existiert UND (b) Ordnerstruktur aktiv
   # INV-2: NUR Welle-3-Outputs (Explorer/Drafter bleiben lokal)
   Lies /home/uczen/Documents/DCS/OmniCommand/_manifest.md → BACKLOG_STATE.backlog_last_id
   Lies /home/uczen/Documents/DCS/OmniCommand/_backlog_index.md → Vault-Pfad fuer aktuelles BL-Item
   Lies vault-routing.json → backlog.subfolder_structure

   IF subfolder_structure.enabled == true AND bl_vault_path existiert:
     bl_ordner = DIRNAME(bl_vault_path) + "/" + bl_id + "-" + slug + "/"

     # Typ-zu-Ordner Mapping aus vault-routing.json
     ordner_map = {}
     FUER folder IN subfolder_structure.folders:
       ordner_map[folder.typ] = folder.ordner

     IF SYNTHESE_TYP IN ordner_map:
       ziel_ordner = bl_ordner + ordner_map[SYNTHESE_TYP] + "/"
       mkdir -p ziel_ordner
       KOPIERE vault_ziel_datei → ziel_ordner + DATEINAME
       Logge: "[BL-ROUTING] {SYNTHESE_TYP} → {ziel_ordner}{DATEINAME}"
     ELSE:
       Logge: "[BL-ROUTING] Kein Ordner-Mapping fuer Typ '{SYNTHESE_TYP}' — Skip"
   ELSE:
     Logge: "[BL-ROUTING] Skip (kein BL-Item oder subfolder_structure nicht aktiv)"
```

### Schritt 6: Bidirektionale Links + Knoten-Index aktualisieren

```
TEIL A: Bidirektionale Links (based-on / anchor-of, W16, W23)

  Fuer jeden Ankerknoten aus Schritt 2:
    1. Lese Vault-Datei des Ankerknotens
    2. Pruefe: Hat anchor-of Feld bereits einen Eintrag fuer das aktuelle Dokument?
       → JA: Skip (Idempotenz)
       → NEIN: Appende "[[{AKTUELLES_DOKUMENT}]]" zum anchor-of Array
    3. Schreibe aktualisierte Vault-Datei

TEIL B: Hebb-Verdrahtung (co-created-with / cycle-cluster, W17, W9)

  1. Identifiziere alle Vault-Dateien im selben Zyklus (cycle = cycle_nr)
  2. Fuer JEDE Datei in der Zyklus-Gruppe:
     a) Pruefe: co-created-with enthaelt bereits alle Zyklus-Partner?
        → JA: Skip (Idempotenz)
        → NEIN: Ergaenze fehlende Partner in co-created-with Array
     b) Setze/aktualisiere cycle-cluster: "{FEATURE}-cycle-{CYCLE_NR}"
  3. Setze co-created-with + cycle-cluster auch im neuen Synthese-Dokument

TEIL C: Knoten-Index aktualisieren (RF-07)

  1. Lese .claude/analysis/_vault_index.md (erstelle falls nicht vorhanden)
  2. Suche Eintrag fuer {DATEINAME}:
     → Gefunden: Aktualisiere updated, nachbar-links
     → Nicht gefunden: Neuen Eintrag appenden
  3. Index-Eintrag-Format:
     | Vault-Pfad | Typ | Updated | Nachbar-Links |
     |---|---|---|---|
     | {VAULT}/{DATEINAME}.md | {SYNTHESE_TYP} | {DATUM} | [[A]], [[B]] |

TEIL D: Manifest-Status aktualisieren

  1. Schreibe/aktualisiere in _manifest.md:
     fire_together_status: {SYNTHESE_TYP} synced {DATUM} hash={MD5SUM}
```

---

## Frontmatter-Schema (vollstaendig)

Jedes von Fire-Together geschriebene Vault-Dokument erhaelt:

| Feld | Pflicht | Typ | Beschreibung |
|---|---|---|---|
| type | JA | String | model, spec, gap, knowledge |
| feature | JA | String | Feature-Name |
| created | JA | Date | Erstellt-Datum (beibehalten bei Update) |
| updated | JA | Date | Letztes Update-Datum |
| content-hash | JA | String | md5sum des Quell-Inhalts |
| source | JA | String | Relativer Pfad zur Quelldatei in .claude/ |
| based-on | NEIN | List | Wiki-Links zu Ankerknoten (aus anchor_nodes) |
| anchor-of | NEIN | List | Wiki-Links zu Dokumenten die DIESEN Knoten referenzieren |
| co-created-with | NEIN | List | Wiki-Links zu Zyklus-Partnern (Hebb-Prinzip) |
| cycle-cluster | NEIN | String | Cluster-ID: "{FEATURE}-cycle-{N}" |
| tags | JA | List | type/{typ}, feature/{slug}, op/fire-together |
| chain-position | JA | String | model, spec, gap, knowledge |
| cycle | JA | Integer | Zyklus-Nummer |

---

## Fehlerbehandlung

| Fehler | Aktion |
|---|---|
| Quell-Datei nicht gefunden | FEHLER + STOPP. Synthese muss erst abgeschlossen sein. |
| Vault-Root nicht bestimmbar | FEHLER + STOPP. WARNING-Guard (kein silent degraded mode). |
| Ankerknoten-Datei im Vault fehlt | WARNUNG + ueberspringen. Graceful Degradation. |
| Hash-Match (unveraendert) | SKIP (kein Fehler). Info-Meldung. |
| Keine anchor_nodes im Manifest | INFO. Verdrahtung nur via Hebb-Prinzip (Schritt 6B). |
| Vault-Datei nicht schreibbar | FEHLER + STOPP. Permissions pruefen. |
| _vault_index.md fehlt | Erstelle neu mit Header. Kein Fehler. |
| Frontmatter-Parse-Fehler in Nachbar-Knoten | WARNUNG + ueberspringen. Nachbar nicht aktualisieren. |

---

## Abgrenzung: Fire-Together vs. _W_obsidianSync

```
/_W_fireTogether                    _W_obsidianSync
=====================               =====================
Wann: Nach JEDER Synthese          Wann: Post-Cycle / manuell / Hard-Sync
Was:  1 Synthese-Dokument          Was:  ALLE Synthese-Dokumente
Wie:  6-Schritt-Sequenz            Wie:  Full-Sync mit Guards
Hash: Idempotenz pro Datei         Hash: Idempotenz pro Datei
Links: based-on/anchor-of          Links: prev/next Chain + based-on/anchor-of
Hebb: co-created-with              Hebb: G-COWORK Guard (bei --co-work)
Index: _vault_index.md Update      Index: Kein Index-Update
Guards: KEINE                       Guards: G-CHAIN, G-BIDIR, G-NAME, G-XREF, G-CAUSAL
Mermaid: NEIN                       Mermaid: JA (bei hard)

Koexistenz:
  Fire-Together = primaerer, inkrementeller Sync (nach jeder Synthese)
  _W_obsidianSync = sekundaerer, vollstaendiger Sync (Guards, Validierung, Mermaid)
  Beide nutzen identisches Hash-Schema (md5sum) → kein Doppel-Sync
```

---

## Dual-Mode: Solo vs. Wellen-Worker

**SOLO-MODUS** (User ruft direkt auf: `/_W_fireTogether {FEATURE} model`)
- Fuehre alle 6 Schritte selbst aus, sequentiell
- Kein Team, kein Agent-Spawn

**WELLEN-WORKER-MODUS** (Orchestrator steuert, Task enthaelt Anweisung)
- Lies Task-Beschreibung um Synthese-Typ zu erkennen
- Fuehre 6 Schritte aus. KEIN Sub-Agent-Spawning.
- TaskUpdate completed + SendMessage an Team Lead

**Worker-Vertrag:**
```
Worker liest:  Task-Beschreibung → FEATURE + SYNTHESE_TYP
Worker fuehrt aus: 6-Schritt-Sequenz
Worker schreibt: Vault-Datei + Nachbar-Links + Index + Manifest
Worker meldet: TaskUpdate completed + SendMessage
Worker spawnt: NICHTS (W7-Constraint, kein Sub-Spawning)
```

---

## W{n}-Referenzen

| W{n} | Aussage | Schritt | Status |
|---|---|---|---|
| W1 | Vault = SSoT | Gesamt | BESTAETIGT |
| W6 | Nach JEDER Synthese | Pipeline-Position | BESTAETIGT |
| W7 | LIEST/SCHREIBT-Vertrag | Vertrag | BESTAETIGT |
| W8 | Idempotenz (Hash-basiert) | Schritt 4 | OFFEN |
| W9 | Baut auf G-COWORK | Schritt 6B | BESTAETIGT |
| W16 | Bidirektionale Links | Schritt 6A | BESTAETIGT |
| W17 | Hebb-Prinzip | Schritt 6B | BESTAETIGT |
| W18 | 6-Schritt-Sequenz | Schritt 1-6 | BESTAETIGT |
| W19 | anchor_nodes Schema | Schritt 2 | BESTAETIGT |
| W23 | based-on/anchor-of Schema | Schritt 5+6A | BESTAETIGT |
| W35 | Implementiert W24 (WissensKoaleszenz) | Schritt 6B | BESTAETIGT |

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle 6 Schritte abgeschlossen):

```bash
# Linux:
echo "/_W_fireTogether {FEATURE} {SYNTHESE_TYP} abgeschlossen — {VAULT_DATEI} synced, {N} Links aktualisiert"

# Windows:
powershell -Command "notify '/_W_fireTogether {FEATURE} {SYNTHESE_TYP} abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

---

ARGUMENTS: $ARGUMENTS
