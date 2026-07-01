---
type: building-block
status: obsolet
deprecated: true
obsoleted_by: BL-050
obsoleted_reason: "BL-045 Vault-First Write — Commands schreiben direkt in Vault, kein nachtraeglicher Sync mehr noetig"
updated: 2026-04-06
---

# /_W_obsidianSync

**Status:** v2.2 (Vault-Routing v2.0 + WARNING-Guard + 5-stufige Pfad-Aufloesung)
**Actor:** VAULT-SYNCER
**Zweck:** Synthese-Dokumente aus .claude/ in den Obsidian Vault synchronisieren. Frontmatter, Wiki-Links, Chain-Topologie, Tags.

**Ersetzt:** v1.0 (PowerShell-only, Windows-hardcodiert, keine Schwierigkeitsstufen)

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_W_obsidianSync {FEATURE} [easy|normal|hard]                  ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  KERN-PROBLEM:                                                           ║
║    Synthese-Dokumente existieren nur in .claude/ — unsichtbar fuer       ║
║    Obsidian. Wissen geht verloren weil es nicht im Wissensgraphen        ║
║    verlinkt ist. Cross-Feature-Suche findet nichts.                      ║
║                                                                          ║
║  KERN-PRINZIP:                                                           ║
║    Dokumente → Vault kopieren MIT Obsidian-Syntax.                       ║
║    Frontmatter, Wiki-Links, Chain-Topologie, Tags.                       ║
║    Hash-basiert: Nur geaenderte Dateien synchronisieren.                 ║
║    "Was in .claude/ entsteht, lebt im Vault weiter."                     ║
║                                                                          ║
║  LIEST (Input) - PFLICHT:                                                ║
║    1. /home/uczen/Documents/DCS/OmniCommand/_manifest.md                                      ║
║       → SYSTEM-MODEL, SCHWIERIGKEIT (Ceiling-Hierarchie)                 ║
║       → Ermittle {NAME}, finde alle Synthese-Dokumente                   ║
║       → Pruefe Obsidian-Sync-Status                                      ║
║    2. .claude/models/{NAME}_Model.md                                     ║
║    3. .claude/analysis/synthese/{NAME}-*.md (alle Synthese-Typen)        ║
║    4. .claude/wissen/*_Wissen.md                                         ║
║    5. /home/uczen/Documents/DCS/OmniCommand/_parking-lot.md (optional)                                 ║
║    6. {VAULT}/{FEATURE}.md (Feature-Note im Vault)                       ║
║    7. .claude/patterns/_pl-index.md (RF-OB-003: Vault-Routing-Regeln)   ║
║       → Typ-Routing: Welcher Typ geht in welchen Vault-Zielordner?      ║
║       → Konsumenten-Mapping: Typ-Tags fuer Frontmatter ableiten         ║
║       → Graceful Degradation: Ohne Index → Default-Routing (type/model) ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. {VAULT}/{DATEINAME}.md (pro Synthese-Dokument)                     ║
║       → Vollstaendige Kopie MIT Obsidian-Frontmatter                     ║
║    2. {VAULT}/{FEATURE}.md                                               ║
║       → Wiki-Links in die richtige Sektion                               ║
║    3. /home/uczen/Documents/DCS/OmniCommand/_manifest.md                                      ║
║       → Obsidian-Sync-Tabelle aktualisieren                              ║
║       → Hash-Vergleich pro Datei (Skip bei unveraendert)                 ║
║    4. Verlinkungs-Topologie (in jedem sync'd Dokument):                  ║
║       → prev/next Chain-Links als Frontmatter-Felder                     ║
║       → cycle + chain-position Metadaten                                 ║
║       → Forschungs-Kette in {FEATURE}.md (Mermaid-Diagramm)             ║
║                                                                          ║
║  MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):                        ║
║    Pattern C: Protokoll-Only-Write + State-Einzeiler                    ║
║    SCHREIBT PROTOKOLL: Hash-Sync-Tabelle vollstaendig                   ║
║      (Prepend → _manifest_protokoll.md)                                 ║
║    SCHREIBT STATE: sync_status-Einzeiler in _manifest.md                ║
║    SCHREIBT NICHT: Detaillierte Sync-Logs in _manifest.md               ║
║      (nur sync_status-Einzeiler)                                        ║
║                                                                          ║
║  HASH-CHECK (Redundanz-Vermeidung):                                      ║
║    md5sum pro Quelldatei → Vergleich mit Manifest-Hash                   ║
║    GLEICH → SKIP, UNTERSCHIEDLICH/FEHLT → SYNC                           ║
║                                                                          ║
║  VAULT-PFAD (5-stufig, vault-routing.json zuerst):                       ║
║    1. vault-routing.json: linux_path/windows_path (Stufe 1)              ║
║    2. Environment: $OBSIDIAN_VAULT_PATH (Stufe 2)                        ║
║    3. Fallback: Manifest "## Obsidian Sync" VAULT-Wert                   ║
║    4. Default Linux: /home/uczen/Documents/DCS                           ║
║    5. Default Windows: C:\Users\Administrator\Documents\DCS              ║
║    Falls NICHTS gefunden → SCHRITT W: WARNING-Guard                      ║
║    (KEIN silent degraded mode — IMMER WARNING+FRAGE)                     ║
║                                                                          ║
║  PIPELINE:                                                               ║
║    Prozessbegleitend: Nach Model-Update, nach Ergebnis, Post-Cycle       ║
║    Standalone: /_W_obsidianSync {FEATURE} hard (manuell)                 ║
║                                                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Schwierigkeits-Parameter

| Schwierigkeit | Sync-Umfang | Guards | Mermaid | Feature-Note |
|---------------|-------------|--------|---------|-------------|
| **easy** | Delta-Sync: NUR geaenderte Dateien (Hash-Check) | KEINE | NEIN | Wiki-Links aktualisieren |
| **normal** | Vollstaendig: ALLE Dateien syncen, Hash-Check | G-CHAIN, G-BIDIR, G-NAME, G-XREF, G-CAUSAL | NEIN | Wiki-Links + Sektionen erstellen |
| **hard** | Vollstaendig: ALLE Dateien + Feature-Note + Tag-Index | G-CHAIN, G-BIDIR, G-NAME, G-XREF, G-CAUSAL | JA (Forschungs-Kette) | Wiki-Links + Sektionen + Mermaid + Guards-Report |

**easy = prozessbegleitend (automatisch):** Schneller Delta-Sync nach Model-Update oder Ergebnis. Keine Guards, kein Mermaid. Minimaler Ressourcenverbrauch.

**normal = 1x pro Zyklus:** Vollstaendiger Sync mit Guards-Validierung. Kein Mermaid (spart Komplexitaet). Standard bei manuellem Aufruf.

**hard = Feature-Ende oder manuell:** Kompletter Sync mit Guards, Mermaid-Diagramm, Tag-Index-Update. Separater Prozess, volle Ressourcen.

**System-Model (aus Manifest):** Bestimmt welches Modell pro Welle laeuft.
- opus: floor=haiku, middle=sonnet, ceiling=opus
- sonnet: floor=haiku, middle=sonnet, ceiling=sonnet
- haiku: floor=haiku, middle=haiku, ceiling=haiku

**Ceiling-Hierarchie (W21):** W_obsidianSync erbt Schwierigkeit vom Parent-Prozess.
Falls Parent easy ist, darf W_obsidianSync maximal easy sein (Sub-Prozess <= Parent).

---

## Dual-Mode: Solo vs. Wellen-Worker

**SOLO-MODUS** (User ruft direkt auf: `/_W_obsidianSync {FEATURE} normal`)
- easy: Delta-Sync (du selbst, nur geaenderte Dateien)
- normal: Vollstaendiger Sync SEQUENTIELL, Guards am Ende
- hard: Vollstaendiger Sync SEQUENTIELL → Guards → Mermaid → Tag-Index
- Fuehre alle Schritte selbst aus, sequentiell

**WELLEN-WORKER-MODUS** (Orchestrator steuert, Task enthaelt Anweisung)
- Lies Task-Beschreibung um Rolle zu erkennen
- "W_obsidianSync easy: Delta-Sync nach Model-Update"
  → Fuehre NUR easy-Sync aus. KEIN Spawning.
  → Lese: Manifest + geaenderte Dateien (Hash-Check)
  → Schreibe: Vault-Kopien + Manifest-Update
  → TaskUpdate completed + SendMessage an Team Lead
- "W_obsidianSync normal: Vollstaendiger Post-Cycle Sync"
  → Fuehre normal-Sync aus. KEIN Spawning.
  → Lese: Alle Synthese-Dateien + Guards
  → Schreibe: Vault-Kopien + Feature-Note + Manifest
  → TaskUpdate completed + SendMessage an Team Lead

**Worker-Vertrag:**
```
Worker liest:  Task-Beschreibung → Schwierigkeit + Scope
Worker fuehrt aus: Sync gemaess Schwierigkeit
Worker schreibt: Vault-Dateien + Manifest
Worker meldet: TaskUpdate completed + SendMessage
Worker spawnt: NICHTS (kein Sub-Spawning)
```

---

## DOKUMENT-TYPEN (aus den Vertraegen)

10 Synthese-Dokumenttypen + 1 Infrastruktur-Typ + 6 neue Typen (v2.3+), konsistentes Schema: **IDENTIFIER zuerst, TYPE danach**.

**WICHTIG:** Ab v2.2 ersetzt die 3-Command-Kette (/_SC_observe → /_SC_modelMaintain → /_SC_qualityGate) den monolithischen /_analyse Command.
Alte ANALYSE{N}-Dokumente bleiben zur Kompatibilitaet erhalten (LEGACY).
Ab v3.0 kommen SPEC (SOLL-Definition) und GAP (IST↔SOLL Delta) als neue Dokumenttypen hinzu.
Ab v2.3 kommen 6 neue Typen hinzu: Pattern Library, Meta-Impl, Meta-Conv, Meta-Arch, Blueprint, Evidence.

| # | Typ | Quell-Pfad | System-Tag | Feature-Sektion | Status |
|---|-----|-----------|------------|-----------------|--------|
| 1 | Model | `models/{NAME}_Model.md` | `type/model` | `# Model` | AKTIV |
| 2 | **Spec** | `specs/{NAME}_Spec.md` | `type/spec` | `# Spec` | **NEU v3.0** |
| 3 | **Gap** | `analysis/synthese/{NAME}-GAP.md` | `type/gap` | `# Gap` | **NEU v3.0** |
| 4 | **Observe** | `analysis/synthese/{NAME}-OBSERVE{N}.md` | `type/observe` | `# Observe` | **NEU v2.2** |
| 5 | **Quality Gate** | `analysis/synthese/{NAME}-QUALITYGATE{N}.md` | `type/qualitygate` | `# Quality Gate` | **NEU v2.2** |
| 6 | Analyse | `analysis/synthese/{NAME}-ANALYSE{N}.md` | `type/analyse` | `# Analyse` | LEGACY <v2.2 |
| 7 | Hypothesen | `analysis/synthese/{NAME}-HYPOTHESEN.md` | `type/hypothese` | `# Hypothese` | AKTIV |
| 8 | Ergebnis | `analysis/synthese/{NAME}-ERGEBNIS{N}.md` | `type/ergebnis` | `# Ergebnis` | AKTIV |
| 9 | Wissen | `wissen/{THEMA}_Wissen.md` | `type/knowledge` | `# Wissen` | AKTIV |
| 10 | Presentation | `presentation/{FEATURE}-{TYPE}.md` | `type/presentation` | `# Presentation` | AKTIV |
| 11 | **Parking Lot** | `_parking-lot.md` | `type/parking-lot` | `# Parking Lot` | **NEU v2.2** |
| 12 | **Pattern Library** | `patterns/_pattern-library.md` | `type/pattern-library` | `# Pattern Library` | **NEU v2.3** |
| 13 | **Meta-Impl** | `meta/implementation/*.md` | `type/meta-impl` | `# Meta-Impl` | **NEU v2.3** |
| 14 | **Meta-Conv** | `meta/codeKonvention/*.md` | `type/meta-conv` | `# Meta-Conv` | **NEU v2.3** |
| 15 | **Meta-Arch** | `meta/architekturKonventionen/*.md` | `type/meta-arch` | `# Meta-Arch` | **NEU v2.3** |
| 16 | **Blueprint** | `patterns/blueprints/*.md` | `type/blueprint` | `# Blueprint` | **NEU v2.3** |
| 17 | **Evidence** | `evidence/*.md` | `type/evidence` | `# Evidence` | **NEU v2.3** |
| 18 | **Crumbs** | `crumbs/{NAME}_*.md` | `type/crumbs` | `# Crumbs` | **NEU v2.4 (#19)** |
| 19 | **PileOfMud** | `pileOfMud/{NAME}_*.md` ODER `pileOfMud/*_{NAME}_*.md` | `type/pileofmud` | `# PileOfMud` | **NEU v2.4 (#19)** |

**Typ-Routing (via _pl-index.md):**

| Typ | Vault-Zielordner | Aenderungshaeufigkeit | Chain-Glied? |
|-----|-----------------|----------------------|--------------|
| type/pattern-library | `Patterns/` | Selten (nach Horizontaler Suche) | NEIN |
| type/meta-impl | `Meta/Implementation/` | Gelegentlich (Framework-Aenderungen) | NEIN |
| type/meta-conv | `Meta/Konventionen/` | Gelegentlich (nach Pre-PR) | NEIN |
| type/meta-arch | `Meta/Architektur/` | Selten (nach Architektur-Entscheidungen) | NEIN |
| type/blueprint | `Patterns/Blueprints/` | Selten (neue Blueprint-Pattern) | NEIN |
| type/evidence | `Evidence/` | Pro Entscheidung (atomar) | NEIN |
| type/crumbs | `Crumbs/` | Pro Feature/Zyklus (Primaerquellen) | NEIN |
| type/pileofmud | `PileOfMud/` | Pro Sprachnotiz/Transkript | NEIN |

**Hinweis zu ModelMaintain:** /_SC_modelMaintain erstellt KEIN eigenes Dokument, sondern aktualisiert Model.md.
Daher kein separater Eintrag in der Sync-Liste.

**Tag-Ebenen:** Siehe `/_obsidianHelp` fuer die vollstaendige 3-Ebenen-Taxonomie
(type/ = System, topic/ = Thematisch, op/ = Operativ).

**Vault-Dateiname = Quell-Dateiname** (keine Umbenennung, Typ steckt bereits im Namen).

---

## VERLINKUNGS-TOPOLOGIE (Chain Model)

Forschungs-Dokumente bilden eine **ZIP-Kette** — sie bauen aufeinander auf
wie Reissverschluss-Zaehne. Jedes Dokument verweist auf seinen Vorgaenger
und Nachfolger.

```
V3.0+ Standalone: SPEC (SOLL), GAP (IST↔SOLL Delta)

V2.2+ (Neue Kette):
MODEL ◄──(updated by)── /_SC_modelMaintain
OBSERVE1 ──▶ QUALITYGATE1 ──▶ HYPOTHESEN ──▶ ERGEBNIS1 ──▶ OBSERVE2 ──▶ ...
   │              │                │              │              │
   cycle:1        cycle:1          cycle:1        cycle:1        cycle:2

<V2.2 (Legacy Kette):
MODEL ◄──(updated by)── ANALYSE{N}
ANALYSE1 ──▶ HYPOTHESEN ──▶ ERGEBNIS1 ──▶ ANALYSE2 ──▶ HYPOTHESEN ──▶ ERGEBNIS2
   │              │              │              │              │              │
   cycle:1        cycle:1        cycle:1        cycle:2        cycle:2        cycle:2
```

### Chain-Position pro Typ

| Typ | chain-position | prev (Input) | next (Output) | Version |
|-----|---------------|--------------|---------------|---------|
| Model | model | --- | `[[OBSERVE{latest}]]` (v2.2+) oder `[[ANALYSE{latest}]]` (<v2.2) | ALL |
| **Spec** | **spec** | --- | --- (SOLL-Referenz, kein Chain-Glied) | **>=v3.0** |
| **Gap** | **gap** | --- | --- (IST↔SOLL Delta, eigenstaendig) | **>=v3.0** |
| **Observe{N}** | **observe** | `[[ERGEBNIS{N-1}]]` (oder MODEL bei N=1) | `[[QUALITYGATE{N}]]` | **>=v2.2** |
| **QualityGate{N}** | **qualitygate** | `[[OBSERVE{N}]]` | `[[HYPOTHESEN]]` | **>=v2.2** |
| Analyse{N} | analyse | `[[ERGEBNIS{N-1}]]` (oder MODEL bei N=1) | `[[HYPOTHESEN]]` | <v2.2 |
| Hypothesen | hypothese | `[[QUALITYGATE{current}]]` (v2.2+) oder `[[ANALYSE{current}]]` (<v2.2) | `[[ERGEBNIS{current}]]` | ALL |
| Ergebnis{N} | ergebnis | `[[HYPOTHESEN]]` | `[[OBSERVE{N+1}]]` (v2.2+) oder `[[ANALYSE{N+1}]]` (<v2.2) | ALL |
| Wissen | knowledge | --- | --- (kein Chain-Glied) | ALL |
| Presentation | presentation | --- | --- (kein Chain-Glied) | ALL |
| **Parking Lot** | **parking-lot** | --- | --- (globale Queue, kein Chain-Glied) | **>=v2.2** |

### Regeln

1. **prev** ist IMMER gesetzt (zeigt auf Vorgaenger, stabil)
2. **next** wird bei JEDEM Sync aktualisiert (leer wenn Nachfolger noch nicht existiert)
3. **cycle** = Zyklus-Nummer (1, 2, 3, ...)
4. **HYPOTHESEN** ist ein lebendes Dokument (ueberschrieben pro Zyklus) — cycle zeigt AKTUELLEN Zyklus
5. **MODEL** verweist auf die LETZTE Analyse die es aktualisiert hat
6. **Wissen/Presentation** sind NICHT Teil der Kette (eigenstaendig, nur via topic/ verlinkt)

---

## TOPOLOGY-GUARDS (Schwierigkeit-skaliert)

Guards laufen NUR bei **normal** und **hard** Schwierigkeit. Bei **easy**: KEINE Guards.

| Guard | Beschreibung | easy | normal | hard |
|-------|-------------|------|--------|------|
| G-CHAIN | Chain-Vollstaendigkeit | SKIP | RUN | RUN |
| G-BIDIR | Bidirektionale Konsistenz (prev/next) | SKIP | RUN | RUN |
| G-NAME | Vault-Namen-Konsistenz | SKIP | RUN | RUN |
| G-XREF | Externe Referenz-Kanten | SKIP | RUN | RUN |
| G-CAUSAL | Kausale Kanten-Labels | SKIP | RUN | RUN |
| **Mermaid** | **Forschungs-Kette Diagramm** | **SKIP** | **SKIP** | **RUN** |
| **G-COWORK** | **Co-Working-Links (cycle-cluster)** | **SKIP** | **SKIP (kein Flag)** | **SKIP (kein Flag)** |
| **G-ANCHOR** | **Anchor-Node Kanten in Vault-Frontmatter** | **SKIP** | **RUN** | **RUN** |

**Hinweis G-COWORK:** Wird NICHT durch easy/normal/hard gesteuert, sondern ausschliesslich durch den `--co-work` Flag (via `/_W_sync_orchestrate --co-work`). Bei direktem `/_W_obsidianSync` Aufruf immer SKIP.

### G-CHAIN: Chain-Vollstaendigkeit

```
Fuer jeden Zyklus N (1..MAX_CYCLE):
  1. OBSERVE{N} existiert? (v2.2+)
  2. QUALITYGATE{N} existiert? (v2.2+)
  3. ERGEBNIS{N} existiert?
     AUSNAHME: Letzter Zyklus darf ERGEBNIS noch nicht haben (in Arbeit)
  4. HYPOTHESEN existiert? (lebendes Dokument)

PASS: Alle erwarteten Knoten vorhanden
WARN: "Zyklus {N} hat kein ERGEBNIS aber OBSERVE{N+1} existiert bereits"
```

### G-BIDIR: Bidirektionale Konsistenz

```
Fuer jedes Dokument D mit prev=X:
  1. Pruefe: Hat X ein next-Feld?
  2. Pruefe: Zeigt X.next auf D (oder ist leer weil D neuer)?

PASS: Alle prev/next-Paare symmetrisch
WARN: "{D}.prev zeigt auf {X}, aber {X}.next zeigt auf {Y} statt {D}"
```

### G-NAME: Vault-Namen-Konsistenz

```
Fuer jeden Eintrag in der Sync-Tabelle:
  1. Quell-Dateiname (ohne Pfad) == Vault-Dateiname?

PASS: Alle Namen identisch
WARN: "{QUELLE} wurde zu {VAULT} umbenannt — Vertrags-Verletzung"
```

### G-XREF: Externe Referenz-Kanten

```
Fuer jede OBSERVE{N} / ANALYSE{N}:
  1. Referenziert sie MODEL? → Erzeuge Kante
  2. Referenziert sie WISSEN? → Erzeuge Kante

PASS: Jede OBSERVE/ANALYSE hat mindestens eine MODEL-Kante
WARN: "OBSERVE{N} hat keine erkennbare MODEL-Referenz"
```

### G-CAUSAL: Kausale Kanten-Labels

```
Fuer jede Chain-Kante zwischen Zyklen:
  1. Gibt es W{n}-Marker im Manifest?
  2. Extrahiere Label

PASS: Jede Kante hat ein kausales Label
WARN: "Uebergang ERGEBNIS{N}→OBSERVE{N+1} hat kein W{n}-Label"
```

### G-COWORK: Co-Working-Links (nur bei --co-work Flag)

Wird NUR aktiviert wenn `/_W_sync_orchestrate` mit `--co-work` aufruft.
Direkter `/_W_obsidianSync` Aufruf ohne Flag → SKIP automatisch.

```
Guard-Logik:
  WENN NICHT --co-work → SKIP (PASS automatisch)

  1. Lese SC_PIPELINE_STATE aus Manifest:
     - Falls SC_PIPELINE_STATE fehlt → WARN + SKIP
     - cycle_nr: aktueller Zyklus N

  2. Identifiziere Zyklus-N-Gruppe:
     Dateien in Vault die Zyklus N entsprechen:
       {NAME}-OBSERVE{N}.md, {NAME}-QUALITYGATE{N}.md,
       {NAME}-HYPOTHESEN.md, {NAME}-ERGEBNIS{N}.md
     Filtere: nur tatsaechlich im Vault vorhandene Dateien

  3. Fuer JEDE Datei in der Gruppe:
     a) Lese Vault-Datei: {VAULT}/{DATEINAME}.md
     b) Pruefe ob co-created-with Feld bereits vorhanden (Idempotenz)
     c) Falls NEU: Appende Co-Working-Frontmatter nach dem schliessenden ---
     d) Falls BEREITS VORHANDEN: Pruefen ob alle Partner eingetragen
        → Fehlende Partner ergaenzen

  Co-Working-Frontmatter Template:
  co-created-with:
    - '[[{PARTNER_1_OHNE_MD}]]'
    - '[[{PARTNER_2_OHNE_MD}]]'
  cycle-cluster: {N}

PASS: Alle Dateien haben co-created-with + cycle-cluster Felder
WARN: "SC_PIPELINE_STATE fehlt — G-COWORK nicht moeglich"
WARN: "Keine Zyklus-{N}-Dateien im Vault — G-COWORK uebersprungen"
```

### G-ANCHOR: Anchor-Node Kanten in Vault-Frontmatter (nur normal/hard)

Schreibt bidirektionale Kanten zwischen Feature-Model und Anker-Dateien im Vault.
Basiert auf `anchor_nodes` aus `/_W_fetch` (Manifest ## W_fetch Ankerpunkte).

```
Guard-Logik:
  WENN Schwierigkeit == easy → SKIP (PASS automatisch)

  1. Lese Manifest ## W_fetch Ankerpunkte
     Falls nicht vorhanden → SKIP (PASS, kein Anker-Kontext)

  2. Fuer JEDEN anchor_node mit merged_into != true:
     a) Vault-Datei vorhanden?
        NEIN → WARN "Stale Reference: {file} nicht im Vault" + SKIP diesen Node
     b) Feature-Model im Vault lesen: {VAULT}/{FEATURE}.md
     c) Schreibe based-on in Feature-Model Frontmatter:
        based-on:
          - '[[{ANCHOR_FILE_OHNE_MD}]]'  # {relation}
        IDEMPOTENZ: Pruefe ob Eintrag bereits existiert vor Append
     d) Schreibe anchor-of in Anker-Datei Frontmatter:
        anchor-of:
          - '[[{FEATURE}]]'
        IDEMPOTENZ: Union-Semantik (kein Duplikat)

  3. Fehler-Isolation:
     Fehler bei einzelnem Node → WARN + CONTINUE
     NIEMALS den Gesamt-Sync blockieren (Robustheit > Vollstaendigkeit)

PASS: Alle erreichbaren anchor_nodes verlinkt (bidirektional)
WARN: "{N} Stale References" oder "{N} Fehler bei Frontmatter-Update"
SKIP: easy-Modus ODER keine Ankerpunkte im Manifest
```

### Guard-Zusammenfassung (Template)

```
## Topology-Guards

| Guard | Status | Details |
|-------|--------|---------|
| G-CHAIN | PASS/WARN | {Details} |
| G-BIDIR | PASS/WARN | {Details} |
| G-NAME | PASS/WARN | {Details} |
| G-XREF | PASS/WARN | {Details} |
| G-CAUSAL | PASS/WARN | {Details} |
| G-COWORK | PASS/SKIP/WARN | {Details — nur bei --co-work relevant} |
| G-ANCHOR | PASS/SKIP/WARN | {Details — anchor_nodes aus W_fetch} |

Gesamt: {N}/5 PASS, {M}/5 WARN (G-COWORK + G-ANCHOR zusaetzlich, kontextabhaengig)
```

---

## HASH-BASIERTE SYNC-OPTIMIERUNG

Vermeidet redundante Datei-Operationen bei unveraenderten Quellen.

### Mechanismus

```
1. VOR Sync: Berechne MD5-Hash der Quelldatei
   Linux:   md5sum '{QUELLE}' | cut -d' ' -f1
   Windows: powershell -Command "(Get-FileHash -Path '{QUELLE}' -Algorithm MD5).Hash"

2. VERGLEICH: Lies gespeicherten Hash aus Manifest Sync-Tabelle

3. ENTSCHEIDUNG:
   Hash GLEICH      → SKIP  (Datei unveraendert, kein Sync noetig)
   Hash VERSCHIEDEN → SYNC  (normale Verarbeitung)
   Hash FEHLT       → SYNC  (erstmaliger Sync)

4. Bei easy-Modus: NUR Hash-Check → SKIP/SYNC Entscheidung. Fertig.
   Bei normal/hard: Hash-Check + vollstaendige Verarbeitung.
```

### Typische Aenderungs-Haeufigkeit

| Typ | Aendert sich durch | Haeufigkeit |
|-----|-------------------|-------------|
| Model | `/_SC_modelMaintain` (Model-Update) | Jeder Zyklus |
| Spec | `/_spec` (erstellt) | Einmalig (immutable danach) |
| Gap | `/_gap` (erstellt + Re-Eval) | Pre-Pipeline + nach Slices |
| Observe{N} | `/_SC_observe` (erstellt) | Einmalig pro Zyklus |
| QualityGate{N} | `/_SC_qualityGate` (erstellt) | Einmalig pro Zyklus |
| Analyse{N} | /_analyse (erstellt) | Einmalig (LEGACY, immutable) |
| Hypothesen | `/_SC_hypothese` + `/_SC_implement` | Jeder Zyklus (ueberschrieben) |
| Ergebnis{N} | `/_SC_ergebnis` (erstellt) | Einmalig (immutable danach) |
| Wissen | `/_knowledge` | Selten |
| Parking Lot | (alle Commands, APPEND) | Laufend (wachsend) |

→ Immutable Dateien werden nach Erst-Sync NIE erneut kopiert (Hash GLEICH).
→ HYPOTHESEN wird IMMER re-synced (lebendes Dokument).
→ Parking Lot waechst laufend → IMMER re-synced.

---

## TRIGGER-PUNKTE (RF-OB-002: Wann wird /_W_obsidianSync aufgerufen?)

Erweiterte Trigger-Matrix: Wann welche Schwierigkeit, und warum.

### Bestehende Trigger-Punkte (W68, unveraendert)

| Aufruf-Kontext | Schwierigkeit | Aufruf durch |
|----------------|---------------|-------------|
| Nach /_SC_modelMaintain (Model-Update) | easy | _SC_orchestrate |
| Nach /_SC_ergebnis (Zyklus-Abschluss) | normal | _SC_orchestrate |
| Nach /_I_orchestrate (Post-Pipeline) | normal | _W_push_orchestrate |
| Feature-Ende (manuell oder /_finish) | hard | User / /_finish |

### Neue Trigger-Punkte (RF-OB-002: Pattern Library + Evidence, W226)

| Aufruf-Kontext | Schwierigkeit | Aufruf durch | Begruendung |
|----------------|---------------|-------------|-------------|
| Nach `/_R_orchestrate` (Review abgeschlossen) | easy | _R_orchestrate (Schritt Final) | Review-Dokumente (PRAESENTATION-*.md) und neue Evidence-Dokumente muessen im Vault sichtbar sein. Easy = Delta-Sync genuegt (nur neue Dateien). |
| Nach `/_R_evidence` (Evidence erstellt) | easy | _R_evidence (Schritt Final) | Neues Evidence-Dokument in evidence/ → Vault-Sync damit cross-feature Suche es findet. Atomar: 1 neue Datei → easy Delta-Sync. |

**Aufruf-Template fuer _R_orchestrate:**
```
# Am Ende von /_R_orchestrate (nach PRAESENTATION-Datei erstellt):
/_W_obsidianSync {FEATURE} easy
# Synct: PRAESENTATION-*.md + alle neuen Evidence-Dokumente (Hash-basiert)
```

**Aufruf-Template fuer _R_evidence:**
```
# Am Ende von /_R_evidence (nach Evidence-Datei erstellt):
/_W_obsidianSync {FEATURE} easy
# Synct: evidence/{EVIDENCE_ID}.md → {VAULT}/Evidence/{EVIDENCE_ID}.md
# Frontmatter: type/evidence, op/{FEATURE}, topic/{ENTSCHEIDUNGS-THEMA}
```

**Warum easy (nicht normal)?**
- Evidence-Dokumente sind einzelne Dateien → Hash-Check reicht
- Review ist am Ende des Zyklus (kein Mermaid noetig → hard waere overkill)
- Geschwindigkeit: easy = minimal Ressourcen, sofortiger Sync
- Chain-Guards (G-CHAIN, G-BIDIR) sind fuer diese Typen nicht relevant
  (Evidence + Presentation sind keine Chain-Glieder laut Verlinkungs-Topologie)

---

## ABLAUF

### Schritt 0: Manifest lesen + Dokumente finden

```
1. Lies /home/uczen/Documents/DCS/OmniCommand/_manifest.md
   → Ermittle {NAME} (z.B. "WissensKoaleszenz_Redesign")
   → Ermittle {FEATURE} aus Argument
   → Lies SYSTEM-MODEL und SCHWIERIGKEIT aus System-Konfiguration
   → Bestimme effektives Modell: min(SYSTEM-MODEL, Command-Max=sonnet)
   → Bestimme effektive Schwierigkeit: min(Argument, Ceiling aus Manifest)

2. Scanne nach Synthese-Dokumenten auf Disk (RF-OB-003: _pl-index.md als Routing-Input lesen):
   0) patterns/_pl-index.md              → lesen (Vault-Routing-Regeln + Typ-Tags)
      Falls nicht vorhanden → Graceful Degradation (nur bekannte Basis-Typen verwenden)
   a) models/{NAME}_Model.md              → existiert?
   b) specs/{NAME}_Spec.md                → existiert? [v3.0+]
   c) analysis/synthese/{NAME}-GAP.md     → existiert? [v3.0+]
   d) analysis/synthese/{NAME}-OBSERVE*.md    → welche existieren? [v2.2+]
   e) analysis/synthese/{NAME}-QUALITYGATE*.md → welche existieren? [v2.2+]
   f) analysis/synthese/{NAME}-ANALYSE*.md    → welche existieren? [LEGACY]
   g) analysis/synthese/{NAME}-ERGEBNIS*.md   → welche existieren?
   h) analysis/synthese/{NAME}-HYPOTHESEN.md  → existiert?
   i) wissen/*_Wissen.md                  → welche existieren?
   j) presentation/{FEATURE}-*.md         → welche existieren?
   k) _parking-lot.md                     → existiert? [v2.2+]

3. Erstelle vollstaendige Sync-Liste mit allen gefundenen Dokumenten

4. HASH-CHECK pro Quelldatei:
   Linux:   md5sum '{QUELLE}' | cut -d' ' -f1
   → Vergleiche mit Hash in Manifest Sync-Tabelle
   → GLEICH: Markiere als SKIP (unveraendert)
   → VERSCHIEDEN/FEHLT: Markiere als SYNC (muss aktualisiert werden)
   → Ausgabe: "{N} zu syncen, {M} unveraendert (Skip)"

5. Bei easy-Modus:
   → NUR Dateien mit SYNC-Markierung verarbeiten (Schritt 2)
   → KEINE Chain-Erkennung, KEINE Guards, KEIN Mermaid
   → Springe direkt zu Schritt 2 (nur fuer SYNC-markierte Dateien)

6. Bei normal/hard:
   → CHAIN-ERKENNUNG (Version Detection):
   → Erkenne Version: Existieren OBSERVE*.md? → v2.2+, sonst <v2.2
   → Baue Chain-Map: MODEL → OBSERVE{N} → QUALITYGATE{N} → HYPOTHESEN → ERGEBNIS{N}
   → Fuer jedes Dokument: prev + next bestimmen

7. Bei normal/hard: TOPOLOGY-GUARDS ausfuehren (siehe Guard-Sektion)

8. Bei hard: KNOTEN-ANNOTATION fuer Mermaid
   → Pro Chain-Knoten: 1-Zeilen-Zusammenfassung, Status, Farbe
```

### Schritt 1a: VAULT-ROUTING-LESE-MUSTER

```
SCHRITT 1a: VAULT-ROUTING-LESE-MUSTER
─────────────────────────────────────────────
R1: vault-routing.json lokalisieren
    CONFIG_PATH=".claude/config/vault-routing.json"
    Falls CONFIG_PATH nicht existiert → SCHRITT W (WARNING-Guard)

R2: Pattern-Match gegen $PWD (case-insensitiv)
    Fuer jede Regel in detection.rules (sortiert nach priority aufsteigend):
      Falls $PWD enthaelt rule.pattern (case-insensitiv) → VAULT_KEY=rule.vault, MATCHED_RULE=rule; BREAK
    Falls kein spezifischer Match → Wildcard-Regel (priority 999) verwenden

R3: Vault-Pfad aufloesen (5-stufig)
    Stufe 1: vaults[VAULT_KEY].linux_path (Linux) / windows_path (Windows) aus routing.json
             Falls existiert + erreichbar (test -d + .obsidian/) → VAULT_PATH ✓
    Stufe 2: $OBSIDIAN_VAULT_PATH (Env-Var)
             Falls gesetzt + erreichbar → VAULT_PATH ✓
    Stufe 3: Manifest '## Obsidian Sync' VAULT-Wert
             Falls vorhanden + erreichbar → VAULT_PATH ✓
    Stufe 4: Linux-Default /home/uczen/Documents/DCS → Falls erreichbar → VAULT_PATH ✓
    Stufe 5: Windows-Default C:\Users\Administrator\Documents\DCS → Falls erreichbar → VAULT_PATH ✓
    Falls alle Stufen scheitern → SCHRITT W (WARNING-Guard)

R4: RAG_COLLECTIONS lesen
    RAG_COLLECTIONS = MATCHED_RULE.rag_collections
    (Fuer obsidianSync nicht direkt relevant, aber fuer Konsistenz bereitgestellt)
```

### Schritt W: WARNING-GUARD

```
SCHRITT W: WARNING-GUARD
────────────────────────
AUSLOESER A: vault-routing.json fehlt unter .claude/config/
  → Ausgabe: "WARNING: vault-routing.json fehlt unter .claude/config/"
  → "Vault-Pfad und RAG-Collections koennen nicht automatisch ermittelt werden."

AUSLOESER B: Vault-Pfad nicht erreichbar (alle 5 Stufen in R3 fehlgeschlagen)
  → Ausgabe: "WARNING: Vault-Pfad nicht erreichbar."
  → "Konfigurierter Pfad: [VAULT_PATH falls bekannt, sonst 'unbekannt']"

GEMEINSAMER ZWEIG:
  Falls HiL=on:
    FRAGE: "Darf ich in DEGRADED MODE weitermachen? (Y/N)"
    Y → DEGRADED MODE aktiv (siehe unten)
    N → STOP + "Bitte vault-routing.json unter .claude/config/ konfigurieren."

  Falls HiL=off:
    Lese Manifest DEGRADED_MODE
    = "erlaubt"  → DEGRADED MODE aktiv
    = "verboten" ODER nicht gesetzt → STOP
      + "Autonomer Betrieb ohne funktionierendes Vault-Routing nicht erlaubt."
      + "Bitte vault-routing.json konfigurieren oder DEGRADED_MODE: erlaubt im Manifest setzen."

DEGRADED MODE (falls aktiviert):
  _W_obsidianSync: Vault-Sync SKIP (nur Meldung: "Vault-Sync uebersprungen (DEGRADED MODE)")
```

### Schritt 1: Vault verifizieren

```
1. VAULT_PATH aus Schritt 1a verwenden (bereits 5-stufig aufgeloest)
   Falls VAULT_PATH nicht gesetzt → bereits durch WARNING-Guard behandelt

2. Pruefe ob Vault-Pfad existiert (ls oder test -d)
3. Pruefe ob .obsidian/ Ordner existiert (= ist ein Vault)
4. Pruefe ob {FEATURE}.md im Vault existiert
5. Falls {FEATURE}.md nicht existiert:
   → FRAGE: "Feature-Note {FEATURE}.md existiert nicht. Erstellen?"
   → Bei easy-Modus: SKIP (keine Feature-Note noetig)
```

### Schritt 1b: Tag-Index lesen + Topics bestimmen (nur normal/hard)

```
Bei easy: SKIP (kein Tag-Index Update)
Bei normal/hard:
1. Pruefe ob {VAULT}/_Tag-Index.md existiert
2. Fuer jedes Synthese-Dokument, bestimme topic/-Tags
3. Vergleiche mit Index (Synonyme vermeiden)
4. Ergebnis: Pro Dokument eine Liste von topic/-Tags (kanonisch)
```

### Schritt 2: Fuer jedes Synthese-Dokument → In Vault kopieren

```
Fuer jedes Dokument in der Sync-Liste (bei easy: nur SYNC-markierte):

  1. KOPIERE die Datei:
     cp '{QUELLE}' '{VAULT}/{DATEINAME}'

  2. BESTIMME Frontmatter-Parameter:
     - id: {Dateiname ohne .md}
     - aliases: (typ-spezifisch, siehe ALIAS-ABLEITUNG)
     - tags (Nested Tags, 3 Ebenen):
       a) type/{TYPE_TAG}  (Pflicht)
       b) op/{FEATURE}     (Pflicht)
       c) topic/{THEMA}    (1-N, aus Dokument-Inhalt + Tag-Registry)
     - feature: '[[{FEATURE}]]'
     - cycle: {CYCLE_NR}
     - chain-position: {CHAIN_POS}
     - prev: '[[{PREV_DOC}]]'
     - next: '[[{NEXT_DOC}]]'

  3. ERSTELLE Frontmatter + Callout als String:
     Nutze Write-Tool oder printf+cat um Frontmatter VOR den Inhalt zu setzen.

     TEMPLATE:
     ---
     id: {ID}
     aliases:
       - {ALIAS1}
       - {ALIAS2}
     tags:
       - type/{TYPE_TAG}
       - op/{FEATURE}
       - topic/{TOPIC1}
     feature: '[[{FEATURE}]]'
     cycle: {CYCLE_NR}
     chain-position: {CHAIN_POS}
     prev: '[[{PREV_DOC}]]'
     next: '[[{NEXT_DOC}]]'
     ---

     > [!info] Feature-Kontext
     > {TYP}-Dokument fuer [[{FEATURE}]]. Zyklus {CYCLE_NR}.
     > Kette: [[{PREV_DOC}]] → **dieses Dokument** → [[{NEXT_DOC}]]

     {ORIGINAL-INHALT}

  4. VERIFIZIERE:
     - Datei existiert im Vault (test -f '{VAULT}/{DATEINAME}')
     - Erste Zeile enthaelt "---" (head -1)
```

### Schritt 3: Feature-Note verlinken + Forschungs-Kette (normal/hard)

```
Bei easy: Wiki-Links aktualisieren (nur neue Dokumente hinzufuegen)
Bei normal: Wiki-Links + Sektionen erstellen
Bei hard: Wiki-Links + Sektionen + Mermaid-Diagramm

1. Lies {VAULT}/{FEATURE}.md
2. Fuer jedes synchronisierte Dokument:
   a) Bestimme Ziel-Sektion (Model, Observe, QualityGate, etc.)
   b) Pruefe ob [[{DATEINAME_OHNE_MD}]] bereits in der Sektion
   c) Falls NICHT → Fuege Wiki-Link unter der Sektion ein
   d) Falls Sektion fehlt → Erstelle sie

3. Bei hard: Generiere Mermaid-Diagramm (Forschungs-Kette)
   → Baue aus Chain-Map + Cross-Refs + Guard-Ergebnissen
   → Ersetze/erstelle "## Forschungs-Kette" Sektion
```

### Schritt 4: Manifest Sync-Tabelle aktualisieren

```
Falls "## Obsidian Sync" Sektion im Manifest existiert → aktualisiere
Falls nicht → fuege am Ende des Manifests ein:

## Obsidian Sync
**VAULT:** {VAULT-PFAD}
**FEATURE:** {FEATURE}
**LETZTER SYNC:** {DATUM}
**SCHWIERIGKEIT:** {easy|normal|hard}

| Quelle | Vault-Datei | Hash (MD5) | Chain | Sync | Status |
|--------|-------------|------------|-------|------|--------|
| models/{NAME}_Model.md | {NAME}_Model.md | A1B2C3... | model | {DATUM} | SYNCED |
| ... | ... | ... | ... | ... | ... |
```

### Schritt 5a: Tag-Registry im Manifest aktualisieren (nur normal/hard)

```
Bei easy: SKIP
Bei normal/hard: Aktualisiere Tag-Registry mit neuen topic/-Tags
```

### Schritt 5b: Tag-Index im Vault aktualisieren (nur hard)

```
Bei easy/normal: SKIP
Bei hard:
1. Lese {VAULT}/_Tag-Index.md (oder erstelle neu)
2. Fuer jeden NEUEN topic/-Tag → Fuege Zeile hinzu
3. Schreibe zurueck
```

---

### Schritt 6: Zusammenfassung ausgeben

```
/_W_obsidianSync {FEATURE} {SCHWIERIGKEIT} - Ergebnis:

## Sync-Status

| Dokument | Chain | Hash | Status |
|----------|-------|------|--------|
| {NAME}_Model.md | model | A1B2.. | Sync OK |
| {NAME}-OBSERVE3.md | observe:3 | D4E5.. | SKIP (unveraendert) |
| ... | ... | ... | ... |

Hash-Optimierung: {N} gesynced, {M} uebersprungen (unveraendert)
Schwierigkeit: {easy|normal|hard}

## Topology-Guards (nur bei normal/hard)

| Guard | Status | Details |
|-------|--------|---------|
| G-CHAIN | PASS | ... |
| ... | ... | ... |

## Forschungs-Kette (nur bei hard)

Mermaid-Diagramm in {FEATURE}.md generiert.
```

---

## ALIAS-ABLEITUNG PRO TYP

| Typ | Strategie | Beispiel |
|-----|----------|---------|
| Model | Kern-Konzepte des Systems | WissensKoaleszenz, W-Commands |
| Observe | Zyklus-Fokus | Observe1, IST-Analyse |
| QualityGate | Zyklus-Bewertung | QualityGate1, BR-Check |
| Analyse | Zyklus-Fokus | Analyse1, Verifikation |
| Ergebnis | Zyklus-Messung | Ergebnis1, Testergebnis |
| Hypothesen | Experiment-Bezeichnung | Hypothese, ImplementPlan |
| Wissen | Themen-Synonyme (3-5) | DualSource, RAG, Dual-Source-Architektur |
| Presentation | Praes-Typ | PR, Brainstorm |

---

## FEHLERBEHANDLUNG

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| Vault nicht gefunden | Pfad falsch oder nicht gemountet | SCHRITT W: WARNING-Guard (5-stufige Pfad-Aufloesung via vault-routing.json) |
| Feature-Note fehlt | Noch nicht angelegt | User fragen ob erstellen |
| Synthese-Datei fehlt | Phase nicht abgeschlossen | Skip mit Warnung |
| Hash-Berechnung fehlschlaegt | Datei nicht lesbar | Skip mit Fehler-Meldung |
| Link-Duplikat | Bereits synchronisiert | Skip, keine Aenderung |
| Sektion fehlt im Feature-Note | z.B. kein `# Observe` | Sektion erstellen |
| Grosse Datei (>1000 Zeilen) | Langsamer Write | cp fuer Vault-Kopie verwenden |

---

## IDEMPOTENZ

Dieses Command ist **idempotent**: Mehrfaches Ausfuehren ist sicher.

- Bereits synchronisierte Dateien werden **ueberschrieben** (neueste Version)
- Bereits vorhandene Wiki-Links werden **nicht dupliziert**
- Frontmatter wird immer **neu generiert** (konsistenter Zustand)
- Manifest-Sync-Tabelle wird **aktualisiert** (neues Datum, neuer Hash)
- Fehlende Sektionen im Feature-Note werden **erstellt**
- Hash-Check verhindert unnoetige Operationen

---

## HINWEIS: SUPERSESSION

Dieses Command ersetzt `/_knowledgeObsidianSync` vollstaendig.
`/_W_obsidianSync` synchronisiert ALLE Synthese-Dokumenttypen, nicht nur Knowledge.

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
notify '{FEATURE} /_W_obsidianSync abgeschlossen'
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
