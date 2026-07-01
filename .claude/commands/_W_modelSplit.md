---
type: building-block
---

# /_W_modelSplit

**Status:** v2.0 (MERGE-Logik + Zirkel-Guards implementiert)
**Actor:** KNOWLEDGE-ENGINEER
**Zweck:** Grosses Feature-Model in thematische, wiederverwendbare Teile splitten

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_W_modelSplit {NAME}                                |
+===============================================================+
|                                                                |
|  KERN-PROBLEM:                                                 |
|    Feature-Models werden riesig (1000-2000 Zeilen).            |
|    Sie enthalten wiederverwendbares Wissen UND                 |
|    feature-spezifischen Kontext vermischt.                     |
|    Nach Feature-Ende: Model = totes Dokument.                  |
|    ABER: Thematische Teile sind fuer naechste Features wertvoll.|
|                                                                |
|  KERN-PRINZIP:                                                 |
|    Model aufsplitten → thematisch extrahieren →                |
|    Obsidian-Index pruefen → Merge oder Neu →                   |
|    readonly im Vault ablegen.                                  |
|    /_W_obsidianSync transportiert, /_W_modelSplit extrahiert.    |
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. .claude/models/{NAME}_Model.md                           |
|       → Das vollstaendige Feature-Model                        |
|    2. {VAULT}/_manifest.md                            |
|       → NAME, Feature-ID, Obsidian Sync-Tabelle               |
|    3. {VAULT}/_Tag-Index.md                                    |
|       → Existierende topic/-Tags + Themen                     |
|    4. {VAULT}/ → Glob nach *_Model.md                          |
|       → Existierende thematische Models im Vault               |
|  [BL-236 AK-4] thematische Split-Header tragen truth_grade-    |
|    Spalte (code_verified|vault_hypothesis|code_contradicted)   |
|    + code-grounded Anker -> reusable Twin. ERWEITERT v2.0      |
|    (MERGE/Zirkel-Guards bleiben), ersetzt NICHT (kein          |
|    Zwei-Split-Skill-Split-Brain).                              |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    5. .claude/wissen/*_Wissen.md                               |
|       → Bereits extrahierte Wissens-Dokumente                  |
|       → Thematische Ueberlappung erkennen                      |
|    6. .claude/specs/{NAME}_Spec.md                             |
|       → Welche Themen sind feature-spezifisch vs generisch?    |
|    7. {VAULT}/_manifest.md → ## W_fetch Ankerpunkte   |
|       → anchor_nodes YAML-Liste (file, match_score, relation,  |
|         match_keywords, merged_into)                            |
|       → MERGE-Ziel-Entscheidung auf Basis von _W_fetch-Daten   |
|    8. Model-Split Log (in Manifest, ## Model-Split Log)        |
|       → Fruehere MERGE/SKIP/Guard-Entscheidungen               |
|    9. anchor_node.file Dateien (Ziel-Models im Vault)          |
|       → Bestehende W{n}-Nummern, TCs, Frontmatter lesen        |
|       → Fuer MERGE: max(W{n}) + Konflikt-Erkennung             |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. {VAULT}/{THEMA}_Model.md (pro Thema, NEU oder MERGE)     |
|       → Thematischer Model-Split, readonly nach Ablage         |
|    2. {VAULT}/{NAME}_Model.md                                  |
|       → Feature-Model: Archiviert, nur noch Referenzen         |
|    3. {VAULT}/_manifest.md                            |
|       → Model-Split Tabelle (was wohin extrahiert)             |
|                                                                |
|  SCHREIBT (Output) - MERGE-spezifisch:                         |
|    4. W{n} fortlaufend im Ziel-Model                           |
|       → max(alle W{n} im Ziel) + 1, fortlaufend               |
|       → Verhindert W{n}-Kollision bei MERGE                    |
|    5. Herkunfts-Vermerk pro MERGE-Sektion (PFLICHT)            |
|       → source-feature, source-wn, merged-by, merged-date     |
|       → Rueckverfolgbarkeit + Rollback per git                 |
|    6. merged_into Flag im Manifest (anchor_nodes)              |
|       → Nach MERGE: merged_into: true setzen                   |
|       → Zirkel-Schutz fuer Folge-Features                     |
|    7. Model-Split Log (## Model-Split Log in Manifest)         |
|       → MERGE/SKIP/Guard-Entscheidungen protokollieren         |
|       → Audit-Trail fuer alle Split-Operationen                |
|                                                                |
|  SCHREIBT NICHT:                                               |
|    - Wissen (/_knowledge macht das)                            |
|    - Analyse-Dokumente (bleiben am Feature)                    |
|    - Synthese-Dokumente (bleiben am Feature)                   |
|                                                                |
|  VORAUSSETZUNG:                                                |
|    /_model finish abgeschlossen (Model = IST-Zustand)          |
|    /_W_obsidianSync mindestens 1x gelaufen (Vault existiert)     |
|                                                                |
|  PIPELINE:                                                     |
|    [/_model finish] → [/_W_modelSplit] → [/_W_obsidianSync]      |
|    → [/_retrospektive] → [Pre-PR]                              |
|                                                                |
|  VAULT-PFAD:                                                   |
|    C:\Users\Administrator\Documents\DCS                        |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**KNOWLEDGE-ENGINEER:** Extrahiert wiederverwendbares Wissen aus Feature-Models.

**TUT:** Model lesen, Themen identifizieren, Obsidian durchsuchen (existiert schon?),
thematisch splitten, Merge oder Neu erstellen, Feature-Model archivieren.

**NICHT:** Wissen erstellen (/_knowledge), Analyse aendern, Code schreiben.

---

## Schritt 0: Model + Vault analysieren

```
1. Lies .claude/models/{NAME}_Model.md
   → Identifiziere Sektionen/Kapitel
   → Markiere: THEMATISCH (wiederverwendbar) vs FEATURE (kontextgebunden)

2. Scan Vault: Existierende *_Model.md Dateien
   → Welche Themen sind schon abgedeckt?

3. Scan Tag-Index: topic/-Tags
   → Welche Themen sind schon im System?

4. AUSGABE: Vorgeschlagener Split-Plan:

   | # | Thema | Zeilen | Vault-Datei | Existiert? | Aktion | Quelle |
   |---|-------|--------|-------------|------------|--------|--------|
   | 1 | DIC-Client | ~300 | DIC-Client_Model.md | NEIN | NEU | Glob |
   | 2 | SFTP/Chilkat | ~200 | SFTP-Chilkat_Model.md | NEIN | NEU | Glob |
   | 3 | S3/MinIO | ~150 | S3-MinIO_Model.md | JA (via Wissen) | SKIP | Glob |
   | 4 | SC-Zyklus | ~250 | SCZyklus_Model.md | JA | MERGE | anchor_node (0.87) |
   | 5 | Feature-Rest | ~500 | (bleibt) | - | ARCHIV | - |

   Quelle-Werte: "anchor_node ({score})" | "Glob" | "Tag-Index" | "-"
```

---

## Schritt 0.5a: anchor_nodes laden + Queues aufbauen

```
1. Lies _manifest.md → suche "## W_fetch Ankerpunkte"
   Falls NICHT vorhanden oder anchor_nodes: []:
     HINWEIS: "Keine Ankerpunkte. Fallback auf Glob-Heuristik."
     → Weiter mit Schritt 1 (bestehendes Verhalten)

2. Fuer jeden anchor_node-Eintrag:
   a) Validierung:
      - file vorhanden? (Pflichtfeld)
      - match_score 0.0-1.0? (Pflichtfeld)
      - relation in {THEMATISCH_VERWANDT, UEBERGEORDNET, UNTERGEORDNET, CO_CREATED}? (Pflichtfeld)
   b) merged_into: true? → ignorieren (Guard P2, bereits MERGE-Ziel)
   c) file existiert nicht im Vault? → ignorieren (Stale Reference)
   d) Validierung fehlgeschlagen? → WARNUNG + ignorieren

3. MERGE-Queue aufbauen:
   → Filter: relation = THEMATISCH_VERWANDT UND match_score >= 0.70
   → Sortierung: nach match_score absteigend (hoechste Konfidenz zuerst)
   → Pro Eintrag: Ziel-Model aus Vault lesen, max(W{n}) ermitteln

4. LINK-Queue aufbauen:
   → Filter: relation in {UEBERGEORDNET, UNTERGEORDNET, CO_CREATED}
   → Aktion: co-created-with / based-on Referenzen (keine inhaltliche MERGE)

5. AUSGABE:
   "{N} MERGE-Kandidaten, {M} LINK-Kandidaten, {K} ignoriert (Stale/merged_into/invalid)"
   Falls N > 5: WARNUNG "Ungewoehnlich viele MERGE-Kandidaten — Feature zu breit?"
```

---

## Schritt 0.5b: Zirkel-Prevention Guards

```
Fuer JEDEN MERGE-Queue-Kandidat (aus Schritt 0.5a):

  GUARD P1 (Zeitstempel-Guard — verhindert Muster Z1 bilateral):
    Lies target_model.extracted (oder created) Datum aus Frontmatter
    Lies source_feature.model_date aus Feature-Model Frontmatter
    WENN target_date > source_date:
      → SKIP ("MERGE nur rueckwaerts in der Zeit — Ziel ist neuer als Quelle")
      → Log: {timestamp, action: SKIP, source, target, guard: P1, resolution: NEU}
    WENN kein Datum verfuegbar:
      → P1 PASS (Benefit of Doubt — Datum fehlt ist kein Block-Grund)

  GUARD P2 (merged_into-Flag — verhindert Folge-MERGEs):
    WENN anchor_node.merged_into == true:
      → SKIP + aus MERGE-Queue entfernen
      → Log: {timestamp, action: SKIP, source, target, guard: P2, resolution: IGNORIERT}
    HINWEIS: P2 gilt NUR fuer THEMATISCH_VERWANDT (MERGE-Queue)
    LINK-Queue ist von P2 NICHT betroffen

  GUARD P3 (DAG-Garantie — verhindert Muster Z4 split-into Verletzung):
    Lies source_model.split-into aus Feature-Model Frontmatter
    Lies target_model.split-into aus Ziel-Model Frontmatter
    WENN target IN source.split-into:
      → SKIP ("Ziel ist Child von Quelle — DAG-Verletzung")
      → Log: {timestamp, action: SKIP, source, target, guard: P3, resolution: NEU}
    WENN source IN target.split-into:
      → SKIP ("Quelle ist Child von Ziel — DAG-Verletzung")
      → Log: {timestamp, action: SKIP, source, target, guard: P3, resolution: NEU}

  ABBRUCH-POLICY:
    → WARN + SKIP + Fallback NEU (kein ABORT — Daten gehen nie verloren)
    → Bei Kern-Models (SCZyklus, MetaProzess, WissensKoaleszenz):
      WARN + HiL-Frage an User statt automatisches SKIP
      "MERGE in Kern-Model {NAME} durch Guard {P} blockiert. Trotzdem mergen? [J/N]"

  ERGEBNIS:
    → Bereinigte MERGE-Queue (nur Kandidaten die alle 3 Guards bestanden haben)
    → Alle Guard-Entscheidungen werden in Manifest ## Model-Split Log geschrieben
    → AUSGABE: "{N} MERGE nach Guards, {M} SKIP (P1:{p1}, P2:{p2}, P3:{p3})"
```

---

## Schritt 1: Thematische Extraktion

```
Fuer jedes Thema aus Schritt 0 — Entscheidungsbaum (Prioritaet absteigend):

  ┌─ 1. MERGE-Queue-Match? (aus Schritt 0.5a, Guards bestanden in 0.5b)
  │    → MERGE in anchor_node-Ziel-Model
  │    a) TC-Zuordnung im Ziel-Model:
  │       Keywords-Overlap zwischen Quell-Thema und Ziel-TCs pruefen
  │       Hoher Overlap (>= 0.7): Einbetten in bestehenden TC als Unterabschnitt
  │         Header: "### {FEATURE}-Ergaenzung: {THEMA} ({DATUM})"
  │       Niedriger Overlap: Neuer TC am Ende des Ziel-Models
  │         Header: "## TC-{N+1}: {THEMA} (aus {FEATURE}, {DATUM})"
  │       Entscheidung per Agent-Urteil (semantisch, nicht mechanisch)
  │
  │    b) W{n}-Nummerierung (PFLICHT):
  │       max(alle W{n} im GESAMTEN Ziel-Model) ermitteln
  │       Neue Nummern fortlaufend ab max+1
  │       Beispiel: SCZyklus max W207, TTL W1 wird W208
  │
  │    c) Herkunfts-Vermerk (PFLICHT pro MERGE-Sektion):
  │       source-feature: {FEATURE}
  │       source-wn: {Original W{n}-Nummern z.B. W1-W7}
  │       merged-by: _W_modelSplit
  │       merged-date: {DATUM}
  │
  │    d) Konflikt-Erkennung:
  │       Duplikat (inhaltlich gleich wie bestehende W{n}): SKIP + Duplikat-Vermerk
  │       Ergaenzung (bestehende W{n} wird erweitert): APPEND + Ergaenzungs-Vermerk
  │       Eigenstaendig (neue Information): Normale Einspeisung als neue W{n}
  │       Entscheidung per Agent-Urteil
  │
  │    e) Frontmatter-Update im Ziel-Model:
  │       w-range erweitern (z.B. W1-W207 → W1-W228)
  │       merged-from Sektion hinzufuegen:
  │         feature: {FEATURE}, date: {DATUM}, wn_original: W1-W7, wn_merged: W208-W214, via: _W_modelSplit
  │       Version Minor-Bump (z.B. Split 1.2 → Split 1.3)
  │       sync_source: "organic-merge"
  │
  ├─ 2. LINK-Queue-Match? (aus Schritt 0.5a)
  │    → co-created-with Referenz im Ziel-Model Frontmatter
  │    → Kein inhaltlicher MERGE, nur Verlinkung
  │
  ├─ 3. Glob-Match im Vault? (Schritt 0 Heuristik)
  │    → MERGE mit WARNUNG ("Kein anchor_node — Glob-Heuristik-Match")
  │    → Identisches MERGE-Verfahren wie bei 1., aber niedrigere Konfidenz
  │
  └─ 4. Kein Match
       → NEU (wie bisher, thematisches Model erstellen)

  FRONTMATTER (thematisches Model — nur bei NEU):
    ---
    id: {THEMA}_Model
    type: thematic-model
    source-feature: {FEATURE}
    source-model: {NAME}_Model.md
    extracted: {DATUM}
    readonly: true
    tags:
      - type/model
      - topic/{THEMA}
    ---

  1. Extrahiere relevante Sektionen aus dem Feature-Model
  2. Entferne feature-spezifische Details (Slice-Referenzen, etc.)
  3. Behalte: Architektur, Patterns, Wahrheiten (W{n}), Diagramme

  AUSGABE pro Thema:
    MERGE: "{N} W{n} (W{start}-W{end}) zu {ZIEL}_Model.md gemergt (Quelle: anchor_node, Score: {S})"
    LINK:  "Referenz zu {ZIEL}_Model.md hinzugefuegt (Relation: {R})"
    NEU:   "{THEMA}_Model.md erstellt ({N} Zeilen, {M} W{n})"
```

---

## Schritt 2: Feature-Model archivieren

```
Das Feature-Model ({NAME}_Model.md) im Vault:
  → Frontmatter ergaenzen: archived: true, split-into: [Liste]
  → Callout hinzufuegen:

  > [!warning] Archiviert
  > Dieses Model wurde am {DATUM} thematisch aufgesplittet.
  > Thematische Teile: [[{THEMA1}_Model]], [[{THEMA2}_Model]], ...
  > Feature-spezifischer Rest bleibt hier.

  Feature-Note ({FEATURE}.md):
  → Unter # Model: Links zu thematischen Models ergaenzen
```

---

## Schritt 3: Manifest + Zusammenfassung

```
Manifest aktualisieren:

  ## Model-Split
  **DATUM:** {DATUM}
  **QUELLE:** {NAME}_Model.md ({ZEILEN} Zeilen)

  | Thema | Vault-Datei | Zeilen | Aktion | Status | Quelle |
  |-------|-------------|--------|--------|--------|--------|
  | SC-Zyklus | SCZyklus_Model.md | 250 | MERGE | DONE | anchor_node (0.87) |
  | DIC-Client | DIC-Client_Model.md | 300 | NEU | SYNCED | Glob |
  | SFTP/Chilkat | SFTP-Chilkat_Model.md | 200 | NEU | SYNCED | Glob |
  | Feature-Rest | {NAME}_Model.md | 500 | ARCHIV | SYNCED | - |

  Quelle-Werte: "anchor_node ({score})" | "Glob" | "Tag-Index" | "-"

  ## Model-Split Log
  Chronologisches Protokoll aller MERGE/SKIP/Guard-Entscheidungen:

  | Timestamp | Action | Source | Target | Guard | Resolution | Details |
  |-----------|--------|--------|--------|-------|------------|---------|
  | {DATUM} | MERGE | TTL W1-W7 | SCZyklus W208-W214 | ALL PASS | DONE | anchor_node 0.87 |
  | {DATUM} | SKIP | TTL W21-W24 | MetaProzess | P1 | NEU | target neuer als source |
  | {DATUM} | SKIP | ... | SCZyklus | P2 | IGNORIERT | merged_into=true |

  merged_into-Flag aktualisieren:
    Fuer jeden erfolgreich gemergten anchor_node:
      → merged_into: true im ## W_fetch Ankerpunkte setzen
      → Zirkel-Schutz fuer Folge-Features

AUSGABE:
  "Model-Split abgeschlossen: {N} thematische Models extrahiert."
  "{M} MERGE ({W} W{n} integriert), {L} LINK, {K} NEU, {A} ARCHIV."
  "{G} Guard-SKIPs (P1:{p1}, P2:{p2}, P3:{p3})."
  # V13 (2026-05-08): /_W_obsidianSync wurde mit BL-065 archiviert (Vault-First-Write
  # via BL-045 — Commands schreiben direkt in Vault, kein Post-Synthese-Sync mehr).
  # Naechster Schritt (Vault-First): Folge-Pipeline (PR/Retrospektive) starten.
  "Model-Split fertig — Folge-Pipeline (Pre-PR / Retrospektive) starten."
```

---

## Abgrenzung: Model vs Wissen

```
/_knowledge erstellt _Wissen.md:
  → Erklaerend, Feynman-Stil, menschenlesbar
  → Quellen-basiert (Papers, Docs, Code-Analyse)
  → Breit: "Wie funktionieren Zertifikate?"

/_W_modelSplit extrahiert thematische Models:
  → Technisch, maschinenlesbar, Wahrheiten (W{n})
  → Erfahrungs-basiert (aus Feature-Arbeit gelernt)
  → Spezifisch: "DIC-Client Architektur: Klassen, Flows, Patterns"

BEIDE leben im Vault, BEIDE sind readonly.
Wissen = Was ist es? Model = Wie funktioniert es bei uns?
```

---

## Qualitaetskriterien

- Jedes extrahierte Thema muss OHNE Feature-Kontext verstaendlich sein
- Keine feature-spezifischen Slice-Referenzen in thematischen Models
- Obsidian-Index IMMER pruefen (keine Duplikate!)
- Feature-Model wird ARCHIVIERT, nicht geloescht
- Merge > Neu (wenn Vault-Datei existiert, erweitern statt neu)
- Tags konsistent mit Tag-Registry
- readonly: true im Frontmatter (Schutz vor versehentlicher Aenderung)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_W_modelSplit abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
