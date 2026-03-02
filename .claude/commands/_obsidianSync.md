# Obsidian Vault Sync

Synchronisiert alle Synthese-Dokumente aus dem wissenschaftlichen
Forschungszyklus in den Obsidian Vault. Fuegt Obsidian-Syntax hinzu (Frontmatter,
Wiki-Links, Callout, Tags) und verlinkt das Feature-Note bidirektional.

**Ersetzt:** `/_knowledgeObsidianSync` (nur Knowledge) → `/_obsidianSync` (ALLE Synthese-Typen)

## Aufruf

```
/_obsidianSync {FEATURE}
```

- **FEATURE** (Pflicht): Die Feature-ID, z.B. `DCSRE-881`
  Falls nicht angegeben → FRAGE den User nach dem Feature

---

## VERTRAG (Pflicht-I/O)

```
+===============================================================+
|  COMMAND: /_obsidianSync {FEATURE}                             |
+===============================================================+
|                                                                |
|  LIEST (Input):                                                |
|    1. .claude/analysis/_manifest.md                            |
|       → Ermittle {NAME}, finde alle Synthese-Dokumente          |
|       → Pruefe Obsidian-Sync-Status                            |
|    2. .claude/models/{NAME}_Model.md                           |
|    3. .claude/specs/{NAME}_Spec.md (v3.0+)                     |
|    4. .claude/analysis/synthese/{NAME}-GAP.md (v3.0+)          |
|    5. .claude/analysis/synthese/{NAME}-OBSERVE*.md (v2.2+)     |
|    6. .claude/analysis/synthese/{NAME}-QUALITYGATE*.md (v2.2+) |
|    7. .claude/analysis/synthese/{NAME}-ANALYSE*.md (LEGACY)    |
|    8. .claude/analysis/synthese/{NAME}-ERGEBNIS*.md                |
|    9. .claude/analysis/synthese/{NAME}-HYPOTHESEN.md               |
|   10. .claude/wissen/*_Wissen.md                               |
|   11. .claude/presentation/{FEATURE}-*.md                      |
|   12. .claude/_parking-lot.md (v2.2+, optional)                |
|   13. {VAULT}/{FEATURE}.md (Feature-Note im Vault)             |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. {VAULT}/{DATEINAME}.md (pro Synthese-Dokument)            |
|       → Vollstaendige Kopie MIT Obsidian-Frontmatter           |
|    2. {VAULT}/{FEATURE}.md                                     |
|       → Wiki-Links in die richtige Sektion                     |
|    3. .claude/analysis/_manifest.md                             |
|       → Obsidian-Sync-Tabelle aktualisieren                   |
|       → Hash-Vergleich pro Datei (Skip bei unveraendert)       |
|    4. Verlinkungs-Topologie (in jedem sync'd Dokument):        |
|       → prev/next Chain-Links als Frontmatter-Felder            |
|       → cycle + chain-position Metadaten                        |
|       → Forschungs-Kette in {FEATURE}.md (Mermaid-Diagramm)    |
|                                                                |
|  HASH-CHECK (Redundanz-Vermeidung):                            |
|    MD5 pro Quelldatei → Vergleich mit Manifest-Hash            |
|    GLEICH → SKIP, UNTERSCHIEDLICH/FEHLT → SYNC                  |
|                                                                |
|  VAULT-PFAD:                                                   |
|    C:\Users\Administrator\Documents\DCS                        |
|    (Obsidian Vault mit .obsidian/ Ordner)                      |
|                                                                |
|  TECHNISCHE EINSCHRAENKUNGEN (hart erlernt):                   |
|    - Synthese-Dateien sind GROSS (500-1100 Zeilen)             |
|    - NICHT mit dem Write-Tool kopieren (haengt sich auf!)      |
|    - IMMER PowerShell fuer Datei-Operationen verwenden         |
|    - KEIN Bash (haengt in dieser Umgebung)                     |
|    - Frontmatter via .ps1 Temp-Script voranstellen             |
|      (PowerShell-Heredoc bricht bei Sonderzeichen)             |
|    - UTF8 Encoding beachten (PowerShell fuegt BOM hinzu)       |
|                                                                |
+===============================================================+
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

**WICHTIG:** Ab v2.2 divergieren die Ketten. Alte Features (<v2.2) nutzen ANALYSE, neue Features (≥v2.2) nutzen OBSERVE→QUALITYGATE.

| Typ | chain-position | prev (Input) | next (Output) | Version |
|-----|---------------|--------------|---------------|---------|
| Model | model | --- | `[[OBSERVE{latest}]]` (v2.2+) oder `[[ANALYSE{latest}]]` (<v2.2) | ALL |
| **Spec** | **spec** | --- | --- (SOLL-Referenz, kein Chain-Glied) | **≥v3.0** |
| **Gap** | **gap** | --- | --- (IST↔SOLL Delta, eigenstaendig) | **≥v3.0** |
| **Observe{N}** | **observe** | `[[ERGEBNIS{N-1}]]` (oder MODEL bei N=1) | `[[QUALITYGATE{N}]]` | **≥v2.2** |
| **QualityGate{N}** | **qualitygate** | `[[OBSERVE{N}]]` | `[[HYPOTHESEN]]` | **≥v2.2** |
| Analyse{N} | analyse | `[[ERGEBNIS{N-1}]]` (oder MODEL bei N=1) | `[[HYPOTHESEN]]` | <v2.2 |
| Hypothesen | hypothese | `[[QUALITYGATE{current}]]` (v2.2+) oder `[[ANALYSE{current}]]` (<v2.2) | `[[ERGEBNIS{current}]]` | ALL |
| Ergebnis{N} | ergebnis | `[[HYPOTHESEN]]` | `[[OBSERVE{N+1}]]` (v2.2+) oder `[[ANALYSE{N+1}]]` (<v2.2) | ALL |
| Wissen | knowledge | --- | --- (kein Chain-Glied) | ALL |
| Presentation | presentation | --- | --- (kein Chain-Glied) | ALL |
| **Parking Lot** | **parking-lot** | --- | --- (globale Queue, kein Chain-Glied) | **≥v2.2** |

### Regeln

1. **prev** ist IMMER gesetzt (zeigt auf Vorgaenger, stabil)
2. **next** wird bei JEDEM Sync aktualisiert (leer wenn Nachfolger noch nicht existiert)
3. **cycle** = Zyklus-Nummer (1, 2, 3, ...)
4. **HYPOTHESEN** ist ein lebendes Dokument (ueberschrieben pro Zyklus) — cycle zeigt AKTUELLEN Zyklus
5. **MODEL** verweist auf die LETZTE Analyse die es aktualisiert hat
6. **Wissen/Presentation** sind NICHT Teil der Kette (eigenstaendig, nur via topic/ verlinkt)

### Externe Referenz-Knoten

Neben den Chain-Gliedern (ANALYSE, HYPOTHESEN, ERGEBNIS) existieren **externe Knoten**
die in der Topologie sichtbar sein MUESSEN, weil sie Input/Output der Kette sind:

```
+------------------+     +-------------------+     +---------------------+
|  MODEL           |     |  WISSEN{*}        |     |  PRESENTATION{*}    |
|  (Stahlblau)     |     |  (Gold)           |     |  (Violett)          |
|  Wird AKTUALISIERT|     |  Wird GELESEN     |     |  Wird ERSTELLT      |
|  durch ANALYSE{N} |     |  von ANALYSE{N}   |     |  aus ERGEBNIS{N}    |
+------------------+     +-------------------+     +---------------------+
```

| Knoten-Typ | Erscheint in Topologie | Kanten-Richtung | Wann sichtbar |
|------------|----------------------|-----------------|---------------|
| MODEL | IMMER (zentraler Hub) | ANALYSE→MODEL (update), MODEL→ANALYSE (input) | Ab erstem Sync |
| WISSEN{*} | Wenn von ANALYSE referenziert | WISSEN→ANALYSE (input) | Ab Referenz |
| PRESENTATION | Wenn existent | ERGEBNIS→PRESENTATION (output) | Ab Erstellung |

### Cross-Reference Kanten (Wissens- und Model-Bezuege)

Kanten zwischen Chain-Gliedern und externen Knoten machen die **Informationsfluesse** sichtbar.
Ohne sie sieht man nur die Reihenfolge, nicht das WARUM.

```
WISSEN ····(input)····▶ ANALYSE{N}
                              │
                        (aktualisiert W{n})
                              │
                              ▼
                           MODEL
```

**Kanten-Typen:**

| Kanten-Typ | Quelle → Ziel | Label | Mermaid-Stil |
|------------|--------------|-------|-------------|
| Chain-Sequenz | ANALYSE→HYPOTHESEN→ERGEBNIS | Kern-Finding / Entscheidung | `-->` (solid) |
| Kausaler Uebergang | ERGEBNIS{N}→ANALYSE{N+1} | `W{n}` die den Zyklus ausloesten | `-->` (solid, bold) |
| Model-Update | ANALYSE{N}→MODEL | `+W{n}` (hinzugefuegte Wahrheiten) | `-->` (solid) |
| Model-Input | MODEL→ANALYSE{N} | `v{VER}` (Model-Version als Input) | `-.->` (dashed) |
| Wissens-Input | WISSEN→ANALYSE{N} | Thema (z.B. "X.509 Trust") | `-.->` (dashed) |
| Ergebnis-Output | ERGEBNIS→PRESENTATION | Deliverable-Typ | `-.->` (dashed) |
| Model-Widerlegung | ERGEBNIS{N}→MODEL | `W{n} WIDERLEGT` | `-->` (solid, red) |

**Dashed (-.->)** = informativer Input (lesen).
**Solid (-->)** = kausaler Output (schreiben/aendern).

### Kausale Kanten-Labels

Jede Chain-Kante traegt ein **kausales Label** — die W{n}-Marker oder Kern-Findings
die den Uebergang begruendeten. Ohne Labels ist die Kette eine Zeitleiste.
MIT Labels ist sie eine **kausale Erklaerung**.

```
ERGEBNIS3 ──"W25 WIDERLEGT, SSL BLOCKER"──▶ ANALYSE4
ANALYSE7  ──"W40-W42, Option F"──▶ ERGEBNIS6
ERGEBNIS6 ──"W35+W37 WIDERLEGT"──▶ MODEL
```

**Label-Quellen (automatisch ableitbar):**

| Kante | Label-Quelle |
|-------|-------------|
| ERGEBNIS{N}→ANALYSE{N+1} | Manifest Zyklus-Historie: Spalte "Ergebnis" von Zeile {N} |
| ANALYSE→HYPOTHESEN | Manifest: Hypothesen-Kandidaten / Kern-Empfehlung |
| ANALYSE→MODEL | Manifest: `W{n}` in Ergebnis-Spalte |
| ERGEBNIS→MODEL | Manifest: `W{n} WIDERLEGT` in Ergebnis-Spalte |

### Battle-Royale-Verlinkung

MODEL bekommt Frontmatter-Feld fuer BR-Bewertung:
```yaml
model-br: '[[{NAME}-ANALYSE{N}#Battle-Royale-Bewertung]]'
```
Ermoeglicht: Von Model direkt zur kompetitiven Bewertung springen.

### Einstiegspunkt: Feature-Note

Von `{FEATURE}.md` → **Forschungs-Kette** zeigt:
- Gesamte Chronologie als Mermaid-Diagramm mit **kausalen Kanten**
- Letzter Stand (aktuellstes Dokument + Status) — **visuell hervorgehoben**
- Zyklus-Anzahl + Model-Version
- **Externe Knoten** (Model, Wissen) mit Informationsfluss-Kanten
- Direkter Einstieg: `{FEATURE}` eingeben → sofort letzte Analyse sichtbar
- Kausale Kette: Rueckwaerts durch W{n}-Labels → warum jeder Zyklus noetig war

---

## TOPOLOGY-GUARDS (Validierung)

Guards laufen NACH Chain-Erkennung (Schritt 0.6) und VOR Mermaid-Generierung (Schritt 3).
Jeder Guard produziert **PASS** oder **WARN**. Bei WARN: Warnung in Zusammenfassung, Sync faehrt fort.
Guards werden in der Zusammenfassung (Schritt 6) als eigene Sektion ausgegeben.

### G-CHAIN: Chain-Vollstaendigkeit

```
Fuer jeden Zyklus N (1..MAX_CYCLE):
  1. ANALYSE{N} existiert?
  2. ERGEBNIS{N} existiert?
     AUSNAHME: Letzter Zyklus darf ERGEBNIS noch nicht haben (in Arbeit)
  3. HYPOTHESEN existiert? (lebendes Dokument)

PASS: Alle erwarteten Knoten vorhanden
WARN: "Zyklus {N} hat kein ERGEBNIS aber ANALYSE{N+1} existiert bereits"
WARN: "HYPOTHESEN-Dokument fehlt"
```

### G-BIDIR: Bidirektionale Konsistenz

```
Fuer jedes Dokument D mit prev=X:
  1. Pruefe: Hat X ein next-Feld?
  2. Pruefe: Zeigt X.next auf D (oder ist leer weil D neuer)?

Fuer jedes Dokument D mit next=Y:
  1. Pruefe: Hat Y ein prev-Feld?
  2. Pruefe: Zeigt Y.prev auf D?

PASS: Alle prev/next-Paare symmetrisch
WARN: "{D}.prev zeigt auf {X}, aber {X}.next zeigt auf {Y} statt {D}"
```

### G-NAME: Vault-Namen-Konsistenz

```
Fuer jeden Eintrag in der Sync-Tabelle:
  1. Quell-Dateiname (ohne Pfad) == Vault-Dateiname?

PASS: Alle Namen identisch
WARN: "{QUELLE} wurde zu {VAULT} umbenannt — Vertrags-Verletzung (Vault-Dateiname = Quell-Dateiname)"
NOTE: Umbenennungen muessen EXPLIZIT im Manifest dokumentiert sein (Spalte "Anmerkung")
```

### G-XREF: Externe Referenz-Kanten

```
Fuer jede ANALYSE{N}:
  1. Referenziert sie MODEL? (Manifest: "Model v{X}" oder "W{n}" in Ergebnis-Spalte)
     → Erzeuge Kante: ANALYSE{N} ──"W{n}"--> MODEL
  2. Referenziert sie WISSEN{*}? (Manifest: Themen-Tags oder explizite Referenz)
     → Erzeuge Kante: WISSEN -.-> ANALYSE{N}

Fuer jedes ERGEBNIS{N}:
  1. Fuegt es W{n} hinzu oder widerlegt W{n}?
     → Erzeuge Kante: ERGEBNIS{N} ──"W{n}+"--> MODEL
     → oder:         ERGEBNIS{N} ──"W{n} WIDERLEGT"--> MODEL

PASS: Jede ANALYSE hat mindestens eine MODEL-Kante
WARN: "ANALYSE{N} hat keine erkennbare MODEL-Referenz"
```

### G-CAUSAL: Kausale Kanten-Labels

```
Fuer jede Chain-Kante zwischen Zyklen (ERGEBNIS{N} → ANALYSE{N+1}):
  1. Gibt es W{n}-Marker im Manifest die den Uebergang begruenden?
  2. Extrahiere Label aus Manifest Zyklus-Historie

Fuer jede Model-Update-Kante:
  1. Welche W{n} wurden hinzugefuegt/korrigiert/widerlegt?
  2. Extrahiere Label aus Manifest

PASS: Jede Kante hat ein kausales Label
WARN: "Uebergang ERGEBNIS{N}→ANALYSE{N+1} hat kein W{n}-Label im Manifest"
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

Gesamt: {N}/5 PASS, {M}/5 WARN
```

---

## HASH-BASIERTE SYNC-OPTIMIERUNG

Vermeidet redundante Datei-Operationen bei unveraenderten Quellen.

### Mechanismus

```
1. VOR Sync: Berechne MD5-Hash der Quelldatei
   PowerShell: (Get-FileHash -Path '{QUELLE}' -Algorithm MD5).Hash

2. VERGLEICH: Lies gespeicherten Hash aus Manifest Sync-Tabelle

3. ENTSCHEIDUNG:
   Hash GLEICH      → SKIP  (Datei unveraendert, kein Sync noetig)
   Hash VERSCHIEDEN → SYNC  (normale Verarbeitung)
   Hash FEHLT       → SYNC  (erstmaliger Sync)
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

→ Immutable Dateien (SPEC, OBSERVE{N}, QUALITYGATE{N}, ANALYSE{N}, ERGEBNIS{N}) werden nach Erst-Sync NIE erneut kopiert.
→ HYPOTHESEN wird IMMER re-synced (lebendes Dokument).
→ GAP wird bei jedem Re-Eval re-synced.
→ Parking Lot waechst laufend → IMMER re-synced.

---

## ABLAUF

### Schritt 0: Manifest lesen + Dokumente finden

**Command-Max:** sonnet (effektiv = min(SYSTEM-MODEL, sonnet))

```
1. Lies .claude/analysis/_manifest.md
   → Ermittle {NAME} (z.B. "Dateiabholung")
   → Ermittle {FEATURE} aus Argument (z.B. "DCSRE-881")
   → Lies SYSTEM-MODEL aus System-Konfiguration
   → Bestimme effektives Modell: min(SYSTEM-MODEL, sonnet)

2. Scanne nach Synthese-Dokumenten auf Disk:
   a) models/{NAME}_Model.md              → existiert?
   b) specs/{NAME}_Spec.md                → existiert? [v3.0+]
   c) analysis/synthese/{NAME}-GAP.md     → existiert? [v3.0+]
   d) analysis/synthese/{NAME}-OBSERVE*.md    → welche existieren? (OBSERVE, OBSERVE2, ...) [v2.2+]
   e) analysis/synthese/{NAME}-QUALITYGATE*.md → welche existieren? (QUALITYGATE, QUALITYGATE2, ...) [v2.2+]
   f) analysis/synthese/{NAME}-ANALYSE*.md    → welche existieren? (ANALYSE, ANALYSE2, ...) [LEGACY]
   g) analysis/synthese/{NAME}-ERGEBNIS*.md   → welche existieren? (ERGEBNIS, ERGEBNIS2, ...)
   h) analysis/synthese/{NAME}-HYPOTHESEN.md  → existiert?
   i) wissen/*_Wissen.md                  → welche existieren?
   j) presentation/{FEATURE}-*.md         → welche existieren?
   k) _parking-lot.md                     → existiert? [v2.2+]

3. Pruefe Manifest "## Obsidian Sync" Sektion:
   → Welche sind bereits SYNCED?
   → ALLE werden trotzdem synchronisiert (Idempotenz: ueberschreiben)

4. Erstelle vollstaendige Sync-Liste mit allen gefundenen Dokumenten

5. HASH-CHECK pro Quelldatei:
   powershell -Command "(Get-FileHash -Path '{QUELLE}' -Algorithm MD5).Hash"
   → Vergleiche mit Hash in Manifest Sync-Tabelle
   → GLEICH: Markiere als SKIP (unveraendert)
   → VERSCHIEDEN/FEHLT: Markiere als SYNC (muss aktualisiert werden)
   → Ausgabe: "{N} zu syncen, {M} unveraendert (Skip)"

6. CHAIN-ERKENNUNG (Version Detection):
   → Erkenne Version: Existieren OBSERVE*.md Dateien? → v2.2+, sonst <v2.2

   V2.2+ (Neue Kette):
     → Sortiere Observe/QualityGate/Ergebnis nach Zyklus-Nummer
     → Bestimme aktuellen Zyklus (hoechste OBSERVE-Nummer)
     → Baue Chain-Map: MODEL → OBSERVE{N} → QUALITYGATE{N} → HYPOTHESEN → ERGEBNIS{N}
     → Fuer jedes Dokument: prev + next bestimmen

   <V2.2 (Legacy Kette):
     → Sortiere Analyse/Ergebnis nach Zyklus-Nummer
     → Bestimme aktuellen Zyklus (hoechste ANALYSE-Nummer)
     → Baue Chain-Map: MODEL → ANALYSE{N} → HYPOTHESEN → ERGEBNIS{N}
     → Fuer jedes Dokument: prev + next bestimmen

7. CROSS-REFERENCE-ERKENNUNG (Externe Kanten):
   → Lies Manifest Zyklus-Historie (Tabelle "## Zyklus-Historie")
   → Fuer jeden Zyklus-Eintrag:
     a) Extrahiere W{n}-Marker aus Ergebnis-Spalte
        → Model-Update-Kanten: ANALYSE{N}/ERGEBNIS{N} ──"W{n}"--> MODEL
     b) Extrahiere "WIDERLEGT"-Marker
        → Widerlegungs-Kanten: ERGEBNIS{N} ──"W{n} WIDERLEGT"--> MODEL (rot)
     c) Extrahiere Kern-Finding/Entscheidung als Kanten-Label
        → Chain-Label: ERGEBNIS{N} ──"Kern-Finding"--> ANALYSE{N+1}
   → Pruefe ob WISSEN-Dokumente in Analyse-Eintraegen referenziert werden
     → Wissens-Kanten: WISSEN -.->|"Thema"| ANALYSE{N}
   → Pruefe ob PRESENTATION-Dokumente aus Ergebnissen abgeleitet wurden
     → Output-Kanten: ERGEBNIS{N} -.-> PRESENTATION

8. TOPOLOGY-GUARDS ausfuehren:
   → G-CHAIN: Chain-Vollstaendigkeit pruefen
   → G-BIDIR: Bidirektionale Konsistenz pruefen
   → G-NAME: Vault-Namen-Konsistenz pruefen
   → G-XREF: Externe Referenz-Kanten pruefen
   → G-CAUSAL: Kausale Kanten-Labels pruefen
   → Sammle PASS/WARN Ergebnisse fuer Schritt 6

9. KNOTEN-ANNOTATION (Zusammenfassung pro Knoten):
   → Fuer jeden Chain-Knoten:
     a) Extrahiere 1-Zeilen-Zusammenfassung aus Manifest Ergebnis-Spalte
     b) Kuerze auf max. 30 Zeichen fuer Mermaid-Label
     c) Bestimme Knoten-Status: AKTUELL (letzter), ABGESCHLOSSEN, IN_ARBEIT
   → Fuer MODEL: Version + aktive W{n} Anzahl
   → Fuer WISSEN: Thema + Seiten-Anzahl
```

### Schritt 1: Vault verifizieren

```
1. Pruefe ob Vault-Pfad existiert:
   C:\Users\Administrator\Documents\DCS
2. Pruefe ob .obsidian/ Ordner existiert (= ist ein Vault)
3. Pruefe ob {FEATURE}.md im Vault existiert
4. Falls {FEATURE}.md nicht existiert:
   → FRAGE: "Feature-Note {FEATURE}.md existiert nicht. Erstellen?"
```

### Schritt 1b: Tag-Index lesen + Topics bestimmen

```
1. Pruefe ob {VAULT}/_Tag-Index.md existiert
   → Falls JA: Lese bestehende topic/-Tags
   → Falls NEIN: Leere Liste (wird in Schritt 5b erstellt)

2. Fuer jedes Synthese-Dokument, bestimme topic/-Tags:
   a) Wissen: {THEMA} ist bekannt → topic/{THEMA}
      Zusaetzlich: Kapitelueberschriften nach weiteren Themen scannen
   b) Model: Kern-Konzepte aus Kapitelueberschriften
   c) Analyse/Hypothese: Untersuchte Themen aus Inhalt
   d) Presentation: Praesentierte Themen

3. VERGLEICHE jeden vorgeschlagenen topic/-Tag mit dem Index:
   → EXAKTER MATCH: Verwende den kanonischen Tag
   → SYNONYM-MATCH: Verwende den kanonischen Tag statt des Synonyms
     (z.B. "SSL" → topic/Zertifikate, weil SSL ein Synonym ist)
   → KEIN MATCH: Neuer Tag → wird in Schritt 5b registriert

4. Ergebnis: Pro Dokument eine Liste von topic/-Tags (kanonisch)
```

**Tag-Index Datei:** `{VAULT}/_Tag-Index.md`
(Lebt im Vault, nicht in .claude/. Enthaelt ALLE registrierten topic/-Tags.
 Format: Tabelle mit kanonischem Tag, Synonymen, Datum, Feature.
 Wird von diesem Command gelesen und erweitert.)

---

### Schritt 2: Fuer jedes Synthese-Dokument → In Vault kopieren

**WICHTIG: PowerShell verwenden, NICHT Write-Tool!**

```
Fuer jedes Dokument in der Sync-Liste:

  1. KOPIERE die Datei mit PowerShell:
     powershell -Command "Copy-Item '{QUELLE}' '{VAULT}\{DATEINAME}'"

  2. BESTIMME Frontmatter-Parameter:
     - id: {Dateiname ohne .md}
     - aliases: (siehe ALIAS-ABLEITUNG unten)
     - tags (Nested Tags, 3 Ebenen):
       a) type/{TYPE_TAG}  (Pflicht: model, analyse, hypothese, knowledge, presentation)
       b) op/{FEATURE}     (Pflicht: z.B. op/DCSRE-881)
       c) topic/{THEMA}    (1-N Stueck, aus Dokument-Inhalt + Tag-Registry)
     - feature: '[[{FEATURE}]]'
     - callout: Typ-spezifische Beschreibung

     TOPIC-BESTIMMUNG:
       - Wissen: {THEMA} ist bekannt (= Ordnername)
       - Model: Kern-Konzepte aus Kapitelueberschriften extrahieren
       - Analyse/Hypothese: Untersuchte Themen aus Inhalt
       - IMMER Tag-Registry im Manifest pruefen (Synonyme vermeiden!)

  3. ERSTELLE ein .ps1 Temp-Script:
     Schreibe via Write-Tool eine .ps1 Datei die:
     a) Den Frontmatter-Header als Array definiert
     b) Die bestehende Vault-Datei liest
     c) Header + Inhalt zusammenfuegt
     d) Mit UTF8 speichert

     TEMPLATE fuer das .ps1 Script:
     ```powershell
     $headerLines = @(
         "---"
         "id: {ID}"
         "aliases:"
         "  - {ALIAS1}"
         "  - {ALIAS2}"
         "tags:"
         "  - type/{TYPE_TAG}"
         "  - op/{FEATURE}"
         "  - topic/{TOPIC1}"
         "  - topic/{TOPIC2}"
         "feature: '[[{FEATURE}]]'"
         "cycle: {CYCLE_NR}"
         "chain-position: {CHAIN_POS}"
         "prev: '[[{PREV_DOC}]]'"
         "next: '[[{NEXT_DOC}]]'"
         "---"
         ""
         "> [!info] Feature-Kontext"
         "> {TYP}-Dokument fuer [[{FEATURE}]]. Zyklus {CYCLE_NR}."
         "> Kette: [[{PREV_DOC}]] → **dieses Dokument** → [[{NEXT_DOC}]]"
         ""
     )

     # Chain-Felder Belegung (aus VERLINKUNGS-TOPOLOGIE):
     #   CHAIN_POS: model|analyse|hypothese|ergebnis|knowledge|presentation
     #   CYCLE_NR:  Zyklus-Nummer (1, 2, 3, ...)
     #   PREV_DOC:  Dateiname des Vorgaengers (ohne .md)
     #   NEXT_DOC:  Dateiname des Nachfolgers (ohne .md, leer wenn noch nicht existent)
     #
     # Bei Wissen/Presentation: cycle=0, prev/next leer, chain-position=knowledge/presentation
     # Bei Model: prev leer, next=ANALYSE{latest}, model-br=ANALYSE{N}#Battle-Royale
     $filePath = "{VAULT}\{DATEINAME}"
     $existing = Get-Content $filePath -Encoding UTF8
     $headerLines + $existing | Set-Content $filePath -Encoding UTF8
     Write-Host "Done. Total lines: $(($headerLines + $existing).Count)"
     ```

  4. FUEHRE das Script aus:
     powershell -ExecutionPolicy Bypass -File "{TEMP_SCRIPT}"

  5. LOESCHE das Temp-Script:
     powershell -Command "Remove-Item '{TEMP_SCRIPT}'"

  6. VERIFIZIERE:
     - Datei existiert im Vault
     - Erste Zeile enthaelt "---" (ggf. mit BOM)
     - Zeilenanzahl = Original + Header-Zeilen
```

### Schritt 3: Feature-Note verlinken + Forschungs-Kette

```
1. Lies {VAULT}/{FEATURE}.md
2. Fuer jedes synchronisierte Dokument:
   a) Bestimme Ziel-Sektion aus der Typ-Tabelle:
      Model → # Model
      Spec → # Spec  (v3.0+, erstelle falls nicht vorhanden)
      Gap → # Gap  (v3.0+, erstelle falls nicht vorhanden)
      Observe → # Observe  (v2.2+, erstelle falls nicht vorhanden)
      QualityGate → # Quality Gate  (v2.2+, erstelle falls nicht vorhanden)
      Analyse → # Analyse  (LEGACY <v2.2)
      Ergebnis → # Ergebnis  (erstelle falls nicht vorhanden)
      Hypothesen → # Hypothese  (erstelle falls nicht vorhanden)
      Wissen → # Wissen
      Presentation → # Presentation
      Parking Lot → # Parking Lot  (v2.2+, globale Queue)
   b) Pruefe ob [[{DATEINAME_OHNE_MD}]] bereits in der Sektion
   c) Falls NICHT → Fuege Wiki-Link unter der Sektion ein
   d) Falls Sektion fehlt → Erstelle sie (Reihenfolge: Model → Spec → Gap → Observe → Quality Gate → Analyse → Hypothese → Ergebnis → Wissen → Presentation → Parking Lot)
3. Keine Duplikate: Bestehende Links nicht wiederholen

4. FORSCHUNGS-KETTE generieren/aktualisieren:
   a) Falls Sektion "## Forschungs-Kette" fehlt → erstelle am ENDE der Note
   b) Generiere Mermaid-Diagramm aus Chain-Map + Cross-Refs + Guards (Schritt 0.6-0.9)
   c) Aktualisiere Letzter-Stand + Zyklus-Info + Model-Version
   d) IDEMPOTENT: Komplette Sektion wird ERSETZT (nicht angehaengt)
   e) Guard-Warnungen als Callout unter dem Diagramm (falls vorhanden)

   TEMPLATE fuer Forschungs-Kette:

   ## Forschungs-Kette

   **Zyklen {NAME}:** {MAX_CYCLE}
   **Model {NAME}:** v{MODEL_VERSION} ({AKTIVE_W} W aktiv, {WIDERLEGT_W} widerlegt)
   **Letzter Stand:** {LETZTES_DOKUMENT} ({STATUS})
   **Guards:** {PASS_COUNT}/5 PASS {WARN_DETAILS}

   ```mermaid
   graph TD
     %% ===== EXTERNE KNOTEN (Hub + Input) =====
     MODEL["{NAME} Model v{VER}\n{AKTIVE_W} W aktiv"]
     WISSEN["{THEMA}_Wissen\n{SEITEN} Seiten"]

     %% ===== ZYKLUS 1 (v2.2+) =====
     subgraph Z1["Zyklus 1: {TITEL_Z1}"]
       O1["{NAME}-OBSERVE\n{KURZTEXT_O1}"]
       Q1["{NAME}-QUALITYGATE\n{KURZTEXT_Q1}"]
       H1["{NAME}-HYPOTHESEN v1\n{KURZTEXT_H1}"]
       E1["{NAME}-ERGEBNIS\n{KURZTEXT_E1}"]
     end

     %% Chain-Kanten Zyklus 1 (v2.2+)
     O1 -->|"Findings"| Q1
     Q1 -->|"Quality Gates OK"| H1
     H1 -->|"_implement"| E1

     %% ===== ZYKLUS 2 (v2.2+) =====
     subgraph Z2["Zyklus 2: {TITEL_Z2}"]
       O2["{NAME}-OBSERVE2\n{KURZTEXT_O2}"]
       Q2["{NAME}-QUALITYGATE2\n{KURZTEXT_Q2}"]
     end

     %% Kausaler Uebergang Z1→Z2 (v2.2+)
     E1 -->|"{W_LABELS_E1_O2}"| O2
     O2 -->|"Findings"| Q2

     %% ===== ALTERNATIVE: LEGACY ZYKLUS (<v2.2) =====
     %% subgraph Z1_LEGACY["Zyklus 1: {TITEL_Z1}"]
     %%   A1["{NAME}-ANALYSE\n{KURZTEXT_A1}"]
     %%   H1_LEGACY["{NAME}-HYPOTHESEN v1\n{KURZTEXT_H1}"]
     %%   E1_LEGACY["{NAME}-ERGEBNIS\n{KURZTEXT_E1}"]
     %% end
     %% A1 -->|"{LABEL_A1_H1}"| H1_LEGACY
     %% H1_LEGACY -->|"_implement"| E1_LEGACY

     %% ... (weitere Zyklen nach gleichem Muster) ...

     %% ===== LETZTER ZYKLUS (hervorgehoben) =====
     subgraph ZN["Zyklus {N}: {TITEL_ZN}"]
       AN["{NAME}-ANALYSE{N}\n{KURZTEXT_AN}"]
       EN["{NAME}-ERGEBNIS{N}\n{KURZTEXT_EN}"]
     end

     %% ===== CROSS-REFERENCE KANTEN =====
     %% Model-Input (dashed = lesen)
     MODEL -.->|"v{VER_INPUT}"| A1

     %% Wissens-Input (dashed = lesen)
     WISSEN -.->|"{THEMA}"| A4

     %% Model-Update (solid = schreiben)
     AN -->|"+W{n1}..W{n2}"| MODEL
     EN -->|"W{n} WIDERLEGT"| MODEL

     %% ===== KNOTEN-FARBEN =====
     %% Externe Knoten
     style MODEL fill:#4682B4,color:#fff
     style WISSEN fill:#FFD700,color:#000

     %% Chain-Knoten v2.2+ (nach Typ)
     style O1 fill:#26C6DA,color:#fff
     style Q1 fill:#AB47BC,color:#fff
     style H1 fill:#E67E22,color:#fff
     style E1 fill:#3F51B5,color:#fff
     style O2 fill:#26C6DA,color:#fff
     style Q2 fill:#AB47BC,color:#fff

     %% Chain-Knoten LEGACY <v2.2 (falls verwendet)
     %% style A1 fill:#2ECC71,color:#fff

     %% AKTUELLER KNOTEN (letzter = hervorgehoben)
     style ON fill:#FF6B6B,color:#fff,stroke:#FF0000,stroke-width:3px

     %% Abgeschlossene Subgraphs: default
     %% Aktueller Subgraph: hervorgehoben
     style ZN fill:#FFF3E0,stroke:#FF6B6B,stroke-width:2px
   ```

   > [!tip] Topologie-Legende
   > **Knoten-Farben (v3.0+):** Stahlblau=Model, **Petrol=Spec**, **Bernstein=Gap**,
   > Gold=Wissen, **Tuerkis=Observe**, **Lila=QualityGate**, Orange=Hypothese,
   > Indigo=Ergebnis, **Gelb=Parking-Lot**, **Rot=Aktuell**
   > **Knoten-Farben (v2.2+):** Stahlblau=Model, Gold=Wissen, **Tuerkis=Observe**,
   > **Lila=QualityGate**, Orange=Hypothese, Indigo=Ergebnis, **Rot=Aktuell**
   > **Knoten-Farben (LEGACY <v2.2):** Stahlblau=Model, Gold=Wissen, Smaragd=Analyse,
   > Orange=Hypothese, Indigo=Ergebnis, **Rot=Aktuell**
   > **Kanten:** ─── solid = kausaler Output (schreibt/aendert)
   > **Kanten:** ╌╌╌ dashed = informativer Input (liest)
   > **Labels:** W{n} = Wahrheiten die den Uebergang begruendeten
   > `prev`/`next` Felder im Frontmatter erlauben sequentielles Durchlaufen.

   KNOTEN-LABEL REGELN:
   - Zeile 1: Dateiname (ohne .md)
   - Zeile 2: Kurztext aus Manifest (max. 30 Zeichen)
     → Extrahiert aus Zyklus-Historie "Ergebnis"-Spalte
     → Nur das Kern-Finding/Ergebnis, keine Details
   - Aktueller Knoten: Zusaetzlich "(AKTUELL)" oder Status

   SUBGRAPH-TITEL REGELN:
   - "Zyklus {N}: {THEMA}"
   - THEMA = Kern-Thema des Zyklus aus Manifest
     → Z.B. "Entity-Provider", "SSL-Debugging", "DURCHBRUCH"
   - Letzter Subgraph bekommt besonderen Stil (hervorgehoben)

   KANTEN-LABEL REGELN:
   - Chain-intern (A→H→E): Entscheidung / Kern-Empfehlung
   - Zyklen-Uebergang (E{N}→A{N+1}): W{n}-Marker aus Manifest
   - Model-Update: "+W{n}" fuer neu, "W{n} KORR" fuer korrigiert
   - Model-Widerlegung: "W{n} WIDERLEGT" (auffaellig)
   - Wissens-Input: Thema-Name
   - LEER lassen wenn Guard G-CAUSAL kein Label findet (→ WARN)

   PRESENTATION-KNOTEN (falls vorhanden):
   - Erscheint AUSSERHALB der Subgraphs
   - Violetter Stil (#9B59B6)
   - Dashed-Kante von ERGEBNIS{N} das die Grundlage lieferte
```

### Schritt 4: Manifest Sync-Tabelle aktualisieren

```
Falls "## Obsidian Sync" Sektion im Manifest existiert → aktualisiere
Falls nicht → fuege am Ende des Manifests ein:

## Obsidian Sync
**VAULT:** C:\Users\Administrator\Documents\DCS
**FEATURE:** {FEATURE}
**LETZTER SYNC:** {DATUM}

| Quelle | Vault-Datei | Hash (MD5) | Chain | Sync | Status |
|--------|-------------|------------|-------|------|--------|
| models/{NAME}_Model.md | {NAME}_Model.md | A1B2C3... | model | {DATUM} | SYNCED |
| analysis/synthese/{NAME}-ANALYSE.md | {NAME}-ANALYSE.md | D4E5F6... | analyse:1 | {DATUM} | SYNCED |
| analysis/synthese/{NAME}-ANALYSE2.md | {NAME}-ANALYSE2.md | G7H8I9... | analyse:2 | {DATUM} | SYNCED |
| analysis/synthese/{NAME}-ERGEBNIS.md | {NAME}-ERGEBNIS.md | J0K1L2... | ergebnis:1 | {DATUM} | SYNCED |
| analysis/synthese/{NAME}-HYPOTHESEN.md | {NAME}-HYPOTHESEN.md | M3N4O5... | hypothese:2 | {DATUM} | SYNCED |
| ... | ... | ... | ... | ... | ... |

**Chain-Spalte:** `{chain-position}:{cycle}` — Position in der ZIP-Kette.
**Hash-Spalte:** MD5 der Quelldatei beim letzten Sync. SKIP wenn identisch.
```

### Schritt 5a: Tag-Registry im Manifest aktualisieren

```
Falls "## Tag-Registry" Sektion im Manifest existiert → aktualisiere
Falls nicht → fuege nach Obsidian Sync ein:

## Tag-Registry (Obsidian) - Nested Tags

Drei Ebenen. Vollstaendige Dokumentation: `/_obsidianHelp`

### System Tags (`type/`) - fest, steuern Graph-Farben
| Tag | Farbe | Fuer | Command | Status |
|-----|-------|------|---------|--------|
| type/knowledge | Gold #FFD700 | Wissens-Dokument (Feynman) | /_knowledge | AKTIV |
| type/model | Stahlblau #4682B4 | System-Modell (Synthese) | /_model | AKTIV |
| **type/spec** | **Petrol #009688** | **Spezifikation (SOLL-Definition)** | **/_spec** | **NEU v3.0** |
| **type/gap** | **Bernstein #FF8F00** | **Gap-Analyse (IST↔SOLL Delta)** | **/_gap** | **NEU v3.0** |
| **type/observe** | **Tuerkis #26C6DA** | **Observe-Synthese (Findings)** | **/_SC_observe** | **NEU v2.2** |
| **type/qualitygate** | **Lila #AB47BC** | **Quality-Gate-Bewertung** | **/_SC_qualityGate** | **NEU v2.2** |
| type/analyse | Smaragd #2ECC71 | Analyse-Synthese | /_analyse | LEGACY <v2.2 |
| type/hypothese | Orange #E67E22 | Hypothesen-Synthese | /_SC_hypothese | AKTIV |
| type/ergebnis | Indigo #3F51B5 | Ergebnis-Messung (Rohdaten) | /_SC_ergebnis | AKTIV |
| type/presentation | Violett #9B59B6 | Praesentation | /_presentation | AKTIV |
| **type/parking-lot** | **Gelb #FDD835** | **Incidental Findings Queue** | **(alle Commands)** | **NEU v2.2** |
| type/user-story | Cyan #00BCD4 | User Story / Feature Note | Vault | AKTIV |
| type/problem | Rot #E74C3C | Problem / Blocker | Vault | AKTIV |

### Operative Tags (`op/`) - pro Feature
| Tag | Feature |
|-----|---------|
| op/{FEATURE} | Aktuelle User Story |

### Thematische Tags (`topic/`) - wachsen, zentral kontrolliert
| Kanonisch | Variationen (VERMEIDEN) | Registriert |
|-----------|------------------------|-------------|
| topic/{THEMA} | (Synonyme hier listen) | {DATUM} |
```

### Schritt 5b: Tag-Index im Vault aktualisieren

```
1. Lese {VAULT}/_Tag-Index.md (oder erstelle neu)
2. Fuer jeden NEUEN topic/-Tag (nicht im Index vorhanden):
   → Fuege Zeile hinzu: | topic/{THEMA} | {SYNONYME} | {DATUM} | {FEATURE} |
3. Schreibe {VAULT}/_Tag-Index.md zurueck

WICHTIG: Tag-Index lebt IM Vault (nicht in .claude/)
         → Sichtbar in Obsidian
         → Manuell pflegbar
         → Wird von Obsidian-Suche gefunden
```

---

### Schritt 6: Zusammenfassung ausgeben

```
/_obsidianSync {FEATURE} - Ergebnis:

## Sync-Status

| Dokument | Chain | Hash | Zeilen | Status |
|----------|-------|------|--------|--------|
| {NAME}_Model.md | model | A1B2.. | {N} | Sync OK |
| {NAME}-ANALYSE.md | analyse:1 | D4E5.. | {N} | SKIP (unveraendert) |
| {NAME}-ANALYSE2.md | analyse:2 | G7H8.. | {N} | Sync OK |
| {NAME}-HYPOTHESEN.md | hypothese:2 | M3N4.. | {N} | Sync OK (lebendes Dok.) |
| {NAME}-ERGEBNIS.md | ergebnis:1 | J0K1.. | {N} | SKIP (immutable) |
| ... | ... | ... | ... | ... |

Hash-Optimierung: {N} gesynced, {M} uebersprungen (unveraendert)

## Topology-Guards

| Guard | Status | Details |
|-------|--------|---------|
| G-CHAIN | PASS | Alle {MAX_CYCLE} Zyklen vollstaendig |
| G-BIDIR | PASS | {N} prev/next-Paare symmetrisch |
| G-NAME | WARN | 3 Umbenennungen: Retrospekt→OmniCommand |
| G-XREF | PASS | {N} ANALYSE→MODEL Kanten, {M} WISSEN→ANALYSE Kanten |
| G-CAUSAL | WARN | Kante E3→A4 ohne W{n}-Label |

Gesamt: {PASS}/5 PASS, {WARN}/5 WARN

## Forschungs-Kette

Topologie in {FEATURE}.md:
  Zyklen: {MAX_CYCLE}, Model: v{VER}
  Letzter Stand: {LETZTES_DOKUMENT} ({STATUS})
  Mermaid-Diagramm: {N} Knoten ({CHAIN} Chain + {EXT} Externe), {M} Kanten ({SOLID} kausal + {DASHED} input)

  Knoten-Typen (v2.2+):
    {N_OBSERVE} Observe (Türkis)
    {N_QUALITYGATE} QualityGate (Lila)
    {N_HYPOTHESE} Hypothese (Orange)
    {N_ERGEBNIS} Ergebnis (Indigo)
    {N_MODEL} Model (Stahlblau)
    {N_WISSEN} Wissen (Gold)
    {N_PRESENTATION} Presentation (Violett)
    1 AKTUELL (Rot, hervorgehoben)

  Knoten-Typen (LEGACY <v2.2):
    {N_ANALYSE} Analyse (Smaragd)
    {N_HYPOTHESE} Hypothese (Orange)
    {N_ERGEBNIS} Ergebnis (Indigo)
    {N_MODEL} Model (Stahlblau)
    {N_WISSEN} Wissen (Gold)
    {N_PRESENTATION} Presentation (Violett)
    1 AKTUELL (Rot, hervorgehoben)

  Kanten-Typen:
    {N_CHAIN_SEQ} Chain-Sequenz (A→H→E)
    {N_CAUSAL} Kausaler Uebergang (E{N}→A{N+1} mit W{n}-Labels)
    {N_MODEL_UPDATE} Model-Update (+W{n})
    {N_MODEL_WIDERL} Model-Widerlegung (W{n} WIDERLEGT)
    {N_WISSEN_INPUT} Wissens-Input (dashed)
    {N_MODEL_INPUT} Model-Input (dashed)

## Verlinkung (prev/next)

  {NAME}-ANALYSE2.md → prev: [[{NAME}-ERGEBNIS]], next: [[{NAME}-HYPOTHESEN]]
  {NAME}-HYPOTHESEN.md → prev: [[{NAME}-ANALYSE2]], next: [[{NAME}-ERGEBNIS2]]
  ...

## Feature-Note

{FEATURE}.md aktualisiert:
  # Model:           [[{NAME}_Model]]
  # Spec (v3.0+):    [[{NAME}_Spec]]
  # Gap (v3.0+):     [[{NAME}-GAP]]
  # Observe (v2.2+): [[{NAME}-OBSERVE]] ... [[{NAME}-OBSERVE{N}]]
  # Quality Gate (v2.2+): [[{NAME}-QUALITYGATE]] ... [[{NAME}-QUALITYGATE{N}]]
  # Analyse (LEGACY): [[{NAME}-ANALYSE]] ... [[{NAME}-ANALYSE{N}]]
  # Hypothese:       [[{NAME}-HYPOTHESEN]]
  # Ergebnis:        [[{NAME}-ERGEBNIS]] ... [[{NAME}-ERGEBNIS{N}]]
  # Wissen:          [[{THEMA}_Wissen]]
  # Parking Lot (v2.2+): [[_parking-lot]]
  # Forschungs-Kette: Mermaid ({N} Knoten, {M} Kanten) + Guards ({PASS}/5)

Manifest: Sync-Tabelle mit Hash ({N} Eintraege)
```

---

## ALIAS-ABLEITUNG PRO TYP

| Typ | Strategie | Beispiel |
|-----|----------|---------|
| Model | Kern-Konzepte des Systems | Dateiabholung, DicImport, FileRetrieval |
| Analyse | Zyklus-Fokus | Analyse1, Verifikation, SSL-Analyse |
| Ergebnis | Zyklus-Messung | Ergebnis1, Testergebnis, Verifikation |
| Hypothesen | Experiment-Bezeichnung | Hypothese, Experiment, ImplementPlan |
| Wissen | Themen-Synonyme (3-5) | X509, TLS, HTTPS, SSL, Zertifikate |
| Presentation | Praes-Typ | PR, Brainstorm, Zwischenergebnis |

Verwende 2-5 Aliases die das Dokument aus verschiedenen Perspektiven
auffindbar machen. Aliases ermoeglichen Wiki-Links wie `[[DicImport]]`
die automatisch auf `Dateiabholung_Model.md` zeigen.

---

## FEHLERBEHANDLUNG

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| Write-Tool haengt | Datei > 500 Zeilen | PowerShell Copy-Item verwenden |
| Bash haengt | Windows/WSL Inkompatibilitaet | PowerShell statt Bash |
| Heredoc bricht | Sonderzeichen (Backticks, Slashes) | .ps1 Temp-Script schreiben |
| Vault nicht gefunden | Pfad falsch | .obsidian/ Ordner suchen |
| Feature-Note fehlt | Noch nicht angelegt | User fragen ob erstellen |
| Synthese-Datei fehlt | Phase nicht abgeschlossen | Skip mit Warnung |
| Encoding BOM | PowerShell UTF8 Standard | `-Encoding UTF8` (BOM akzeptabel) |
| Link-Duplikat | Bereits synchronisiert | Skip, keine Aenderung |
| Sektion fehlt | z.B. kein `# Hypothese` im Feature | Sektion erstellen |

---

## IDEMPOTENZ

Dieses Command ist **idempotent**: Mehrfaches Ausfuehren ist sicher.

- Bereits synchronisierte Dateien werden **ueberschrieben** (neueste Version)
- Bereits vorhandene Wiki-Links werden **nicht dupliziert**
- Frontmatter wird immer **neu generiert** (konsistenter Zustand)
- Manifest-Sync-Tabelle wird **aktualisiert** (neues Datum)
- Fehlende Sektionen im Feature-Note werden **erstellt**

---

## BEISPIEL

```
User: /_obsidianSync DCSRE-881

Agent:
  Schritt 0: Manifest lesen...
    → NAME: Dateiabholung, FEATURE: DCSRE-881
    → Version Detection: OBSERVE-Dateien gefunden → v2.2+
    → Gefunden: Model (1), Observe (4), QualityGate (4), Ergebnis (4), Hypothesen (1), Wissen (1), Parking Lot (1)
    → Presentation: keine
    → LEGACY: Alte ANALYSE-Dateien (4) bleiben erhalten
    → Gesamt: 16 Dokumente

  Schritt 1: Vault verifizieren...
    → C:\Users\Administrator\Documents\DCS\.obsidian\ existiert
    → DCSRE-881.md existiert im Vault

  Schritt 2: Sync...
    → Dateiabholung_Model.md → Vault (model, 842 Zeilen) ✓
    → Dateiabholung-OBSERVE.md → Vault (observe, 280 Zeilen) ✓ [v2.2+]
    → Dateiabholung-OBSERVE2.md → Vault (observe, 290 Zeilen) ✓ [v2.2+]
    → Dateiabholung-OBSERVE3.md → Vault (observe, 270 Zeilen) ✓ [v2.2+]
    → Dateiabholung-OBSERVE4.md → Vault (observe, 285 Zeilen) ✓ [v2.2+]
    → Dateiabholung-QUALITYGATE.md → Vault (qualitygate, 190 Zeilen) ✓ [v2.2+]
    → Dateiabholung-QUALITYGATE2.md → Vault (qualitygate, 200 Zeilen) ✓ [v2.2+]
    → Dateiabholung-QUALITYGATE3.md → Vault (qualitygate, 195 Zeilen) ✓ [v2.2+]
    → Dateiabholung-QUALITYGATE4.md → Vault (qualitygate, 210 Zeilen) ✓ [v2.2+]
    → Dateiabholung-ANALYSE.md → Vault (analyse, 510 Zeilen) ✓ [LEGACY]
    → Dateiabholung-ANALYSE2.md → Vault (analyse, 320 Zeilen) ✓ [LEGACY]
    → Dateiabholung-ANALYSE3.md → Vault (analyse, 290 Zeilen) ✓ [LEGACY]
    → Dateiabholung-ANALYSE4.md → Vault (analyse, 310 Zeilen) ✓ [LEGACY]
    → Dateiabholung-ERGEBNIS.md → Vault (ergebnis, 420 Zeilen) ✓
    → Dateiabholung-ERGEBNIS2.md → Vault (ergebnis, 430 Zeilen) ✓
    → Dateiabholung-ERGEBNIS3.md → Vault (ergebnis, 415 Zeilen) ✓
    → Dateiabholung-ERGEBNIS4.md → Vault (ergebnis, 425 Zeilen) ✓
    → Dateiabholung-HYPOTHESEN.md → Vault (hypothese, 680 Zeilen) ✓
    → Zertifikate_Wissen.md → Vault (knowledge, ueberschrieben) ✓
    → _parking-lot.md → Vault (parking-lot, 120 Zeilen) ✓ [v2.2+]

  Schritt 3: Feature-Note...
    → # Model: [[Dateiabholung_Model]] hinzugefuegt
    → # Observe: Sektion erstellt, [[Dateiabholung-OBSERVE]] ... [[Dateiabholung-OBSERVE4]]
    → # Quality Gate: Sektion erstellt, [[Dateiabholung-QUALITYGATE]] ... [[Dateiabholung-QUALITYGATE4]]
    → # Analyse: [[Dateiabholung-ANALYSE]] ... [[Dateiabholung-ANALYSE4]] (LEGACY)
    → # Hypothese: [[Dateiabholung-HYPOTHESEN]]
    → # Ergebnis: [[Dateiabholung-ERGEBNIS]] ... [[Dateiabholung-ERGEBNIS4]]
    → # Wissen: [[Zertifikate_Wissen]] bereits vorhanden
    → # Parking Lot: Sektion erstellt, [[_parking-lot]]

  Schritt 4: Manifest...
    → Obsidian-Sync-Tabelle: 20 Eintraege, alle SYNCED

  Ergebnis:
  | Dokument | System-Tag | Chain | Zeilen | Status |
  |----------|------------|-------|--------|--------|
  | Dateiabholung_Model.md | type/model | model | 842 | Sync OK |
  | Dateiabholung-OBSERVE4.md | type/observe | observe:4 | 285 | Sync OK |
  | Dateiabholung-QUALITYGATE4.md | type/qualitygate | qualitygate:4 | 210 | Sync OK |
  | Dateiabholung-ANALYSE4.md | type/analyse | analyse:4 | 310 | Sync OK (LEGACY) |
  | Dateiabholung-HYPOTHESEN.md | type/hypothese | hypothese:4 | 680 | Sync OK |
  | Dateiabholung-ERGEBNIS4.md | type/ergebnis | ergebnis:4 | 425 | Sync OK |
  | Zertifikate_Wissen.md | type/knowledge | knowledge | 1043 | Sync OK |
  | _parking-lot.md | type/parking-lot | parking-lot | 120 | Sync OK |
  | ... (12 weitere) | ... | ... | ... | ... |

  Topic-Tags: 6 kanonische Tags vergeben, 2 neue registriert
  Tag-Index: {VAULT}/_Tag-Index.md aktualisiert
  Forschungs-Kette: v2.2+ Chain (Observe→QualityGate→Hypothese) im Mermaid visualisiert
```

---

## HINWEIS: SUPERSESSION

Dieses Command ersetzt `/_knowledgeObsidianSync` vollstaendig.
`/_obsidianSync` synchronisiert ALLE Synthese-Dokumenttypen, nicht nur Knowledge.
`/_knowledgeObsidianSync` kann entfernt oder als Alias beibehalten werden.

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_obsidianSync abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
