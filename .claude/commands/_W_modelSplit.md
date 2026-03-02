# /_W_modelSplit

**Status:** v1.0 (Placeholder — Vertrag definiert, Ablauf skizziert)
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
|    2. .claude/analysis/_manifest.md                            |
|       → NAME, Feature-ID, Obsidian Sync-Tabelle               |
|    3. {VAULT}/_Tag-Index.md                                    |
|       → Existierende topic/-Tags + Themen                     |
|    4. {VAULT}/ → Glob nach *_Model.md                          |
|       → Existierende thematische Models im Vault               |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    5. .claude/wissen/*_Wissen.md                               |
|       → Bereits extrahierte Wissens-Dokumente                  |
|       → Thematische Ueberlappung erkennen                      |
|    6. .claude/specs/{NAME}_Spec.md                             |
|       → Welche Themen sind feature-spezifisch vs generisch?    |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. {VAULT}/{THEMA}_Model.md (pro Thema, NEU oder MERGE)     |
|       → Thematischer Model-Split, readonly nach Ablage         |
|    2. {VAULT}/{NAME}_Model.md                                  |
|       → Feature-Model: Archiviert, nur noch Referenzen         |
|    3. .claude/analysis/_manifest.md                            |
|       → Model-Split Tabelle (was wohin extrahiert)             |
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

   | # | Thema | Zeilen | Vault-Datei | Existiert? | Aktion |
   |---|-------|--------|-------------|------------|--------|
   | 1 | DIC-Client | ~300 | DIC-Client_Model.md | NEIN | NEU |
   | 2 | SFTP/Chilkat | ~200 | SFTP-Chilkat_Model.md | NEIN | NEU |
   | 3 | S3/MinIO | ~150 | S3-MinIO_Model.md | JA (via Wissen) | SKIP |
   | 4 | Feature-Rest | ~500 | (bleibt) | - | ARCHIV |
```

---

## Schritt 1: Thematische Extraktion

```
Fuer jedes Thema mit Aktion NEU oder MERGE:

  1. Extrahiere relevante Sektionen aus dem Feature-Model
  2. Entferne feature-spezifische Details (Slice-Referenzen, etc.)
  3. Behalte: Architektur, Patterns, Wahrheiten (W{n}), Diagramme
  4. Erstelle thematisches Model mit eigenem Frontmatter

  FRONTMATTER (thematisches Model):
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

  Falls MERGE (Vault-Datei existiert bereits):
    → Lies bestehende Vault-Datei
    → Identifiziere NEUE Inhalte (nicht schon vorhanden)
    → APPEND neue Sektionen mit Herkunfts-Vermerk
    → AUSGABE: "{N} neue Sektionen zu {THEMA}_Model.md hinzugefuegt"
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

  | Thema | Vault-Datei | Zeilen | Aktion | Status |
  |-------|-------------|--------|--------|--------|
  | DIC-Client | DIC-Client_Model.md | 300 | NEU | SYNCED |
  | SFTP/Chilkat | SFTP-Chilkat_Model.md | 200 | NEU | SYNCED |
  | Feature-Rest | {NAME}_Model.md | 500 | ARCHIV | SYNCED |

AUSGABE:
  "Model-Split abgeschlossen: {N} thematische Models extrahiert."
  "{M} Zeilen wiederverwendbar, {K} Zeilen feature-spezifisch (archiviert)."
  "Naechster Schritt: /_W_obsidianSync {FEATURE} (falls nicht automatisch)"
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
