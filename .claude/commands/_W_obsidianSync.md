# /_W_obsidianSync

**Status:** v2.0 (Blueprint-Redesign: Schwierigkeitsstufen + Dual-Mode + Linux-Port + Guard-Scaling)
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
║    1. .claude/analysis/_manifest.md                                      ║
║       → SYSTEM-MODEL, SCHWIERIGKEIT (Ceiling-Hierarchie)                 ║
║       → Ermittle {NAME}, finde alle Synthese-Dokumente                   ║
║       → Pruefe Obsidian-Sync-Status                                      ║
║    2. .claude/models/{NAME}_Model.md                                     ║
║    3. .claude/analysis/synthese/{NAME}-*.md (alle Synthese-Typen)        ║
║    4. .claude/wissen/*_Wissen.md                                         ║
║    5. .claude/_parking-lot.md (optional)                                 ║
║    6. {VAULT}/{FEATURE}.md (Feature-Note im Vault)                       ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. {VAULT}/{DATEINAME}.md (pro Synthese-Dokument)                     ║
║       → Vollstaendige Kopie MIT Obsidian-Frontmatter                     ║
║    2. {VAULT}/{FEATURE}.md                                               ║
║       → Wiki-Links in die richtige Sektion                               ║
║    3. .claude/analysis/_manifest.md                                      ║
║       → Obsidian-Sync-Tabelle aktualisieren                              ║
║       → Hash-Vergleich pro Datei (Skip bei unveraendert)                 ║
║    4. Verlinkungs-Topologie (in jedem sync'd Dokument):                  ║
║       → prev/next Chain-Links als Frontmatter-Felder                     ║
║       → cycle + chain-position Metadaten                                 ║
║       → Forschungs-Kette in {FEATURE}.md (Mermaid-Diagramm)             ║
║                                                                          ║
║  HASH-CHECK (Redundanz-Vermeidung):                                      ║
║    md5sum pro Quelldatei → Vergleich mit Manifest-Hash                   ║
║    GLEICH → SKIP, UNTERSCHIEDLICH/FEHLT → SYNC                           ║
║                                                                          ║
║  VAULT-PFAD (konfigurierbar, 4-stufig):                                  ║
║    1. Environment: $OBSIDIAN_VAULT_PATH                                  ║
║    2. Fallback: Manifest "## Obsidian Sync" VAULT-Wert                   ║
║    3. Default Linux: /home/uczen/Documents/DCS                           ║
║    4. Default Windows: C:\Users\Administrator\Documents\DCS              ║
║    Falls Vault nicht erreichbar → FEHLER (kein Sync moeglich)            ║
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

10 Synthese-Dokumenttypen + 1 Infrastruktur-Typ, konsistentes Schema: **IDENTIFIER zuerst, TYPE danach**.

**WICHTIG:** Ab v2.2 ersetzt die 3-Command-Kette (/_SC_observe → /_SC_modelMaintain → /_SC_qualityGate) den monolithischen /_analyse Command.
Alte ANALYSE{N}-Dokumente bleiben zur Kompatibilitaet erhalten (LEGACY).
Ab v3.0 kommen SPEC (SOLL-Definition) und GAP (IST↔SOLL Delta) als neue Dokumenttypen hinzu.

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

Gesamt: {N}/5 PASS, {M}/5 WARN (G-COWORK zusaetzlich, nur bei --co-work)
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

## ABLAUF

### Schritt 0: Manifest lesen + Dokumente finden

```
1. Lies .claude/analysis/_manifest.md
   → Ermittle {NAME} (z.B. "WissensKoaleszenz_Redesign")
   → Ermittle {FEATURE} aus Argument
   → Lies SYSTEM-MODEL und SCHWIERIGKEIT aus System-Konfiguration
   → Bestimme effektives Modell: min(SYSTEM-MODEL, Command-Max=sonnet)
   → Bestimme effektive Schwierigkeit: min(Argument, Ceiling aus Manifest)

2. Scanne nach Synthese-Dokumenten auf Disk:
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

### Schritt 1: Vault verifizieren

```
1. Bestimme Vault-Pfad (4-stufig):
   a) Environment: $OBSIDIAN_VAULT_PATH (falls gesetzt)
   b) Manifest: "## Obsidian Sync" VAULT-Wert (falls vorhanden)
   c) Linux-Default: /home/uczen/Documents/DCS
   d) Windows-Default: C:\Users\Administrator\Documents\DCS

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
| Vault nicht gefunden | Pfad falsch oder nicht gemountet | 4-stufige Pfad-Aufloesung pruefen |
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
