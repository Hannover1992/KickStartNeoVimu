# Retrospektive: Feature-Abschluss + Wissenstransfer

Du fuehrst eine strukturierte Retrospektive nach Feature-Abschluss durch.
Extrahiert wiederverwendbares Wissen, Anti-Patterns und Architektur-Entscheidungen
aus dem abgeschlossenen Forschungszyklus und bereitet sie fuer das Langzeitgedaechtnis vor.

## Aufruf

```
/_retrospektive {FEATURE} [--dry-run]
```

- **FEATURE** (Pflicht): Feature-ID, z.B. `DCSRE-881`
- **--dry-run** (Optional): Nur analysieren, NICHTS einspeisen

---

## VERTRAG (Pflicht-I/O)

```
+===============================================================+
|  COMMAND: /_retrospektive {FEATURE}                            |
+===============================================================+
|                                                                |
|  LIEST (Input):                                                |
|    1. .claude/analysis/_manifest.md                            |
|       → NAME, Zyklus-Historie, alle Phasen                    |
|    2. .claude/models/{NAME}_Model.md                           |
|       → Wahrheiten (W1-Wn), Architektur-Entscheidungen        |
|    3. .claude/analysis/synthese/{NAME}-OBSERVE*.md (v2.2+)     |
|       → Observations, Findings pro Zyklus                      |
|    4. .claude/analysis/synthese/{NAME}-QUALITYGATE*.md (v2.2+) |
|       → Gate-Ergebnisse, Stagnation, Trigger                  |
|    5. .claude/analysis/synthese/{NAME}-ERGEBNIS*.md            |
|       → Experiment-Ergebnisse, SRS-Verlauf                     |
|    6. .claude/analysis/synthese/{NAME}-ANALYSE*.md (LEGACY)    |
|       → Konsolidierte Findings, Widersprueche                 |
|    7. .claude/analysis/synthese/{NAME}-HYPOTHESEN.md           |
|       → Entscheidungen, Risiken, Gegen-Hypothesen             |
|    8. .claude/analysis/synthese/{NAME}-GAP.md (v3.0)           |
|       → IST-SOLL Delta, Luecken-Analyse                       |
|    9. .claude/wissen/*_Wissen.md                               |
|       → Feynman-Wissens-Dokumente                             |
|   10. GraphRAG MCP: Lokale Collection {FEATURE}                |
|       → Bereits eingespeiste Entities pruefen                  |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. .claude/analysis/synthese/{NAME}-RETROSPEKTIVE.md        |
|       → Strukturiertes Retrospektive-Dokument                 |
|    2. GraphRAG MCP: Lokale Collection {FEATURE}                |
|       → Atomare Wissens-Entities einspeisen                   |
|    3. GraphRAG MCP: Globale Collection                         |
|       → Kuratierte, projektuebergreifende Entities            |
|    4. .claude/analysis/_manifest.md                            |
|       → Retrospektive-Status aktualisieren                    |
|                                                                |
+===============================================================+
```

---

## Schritt 0: Manifest lesen + Vollstaendigkeit pruefen

**Command-Max:** opus (effektiv = min(SYSTEM-MODEL, opus))

```
1. Lies .claude/analysis/_manifest.md
   → Ermittle {NAME}, {FEATURE}
   → Lies SYSTEM-MODEL aus System-Konfiguration
   → Bestimme effektives Modell: min(SYSTEM-MODEL, opus)

2. Pruefe Vollstaendigkeit des Zyklus:
   → _SC_ergebnis muss mindestens 1x mit GELOEST abgeschlossen sein
   → Falls NEUER ZYKLUS noch offen: WARNUNG ausgeben
   → Falls kein _ergebnis: ABBRUCH "Feature noch nicht abgeschlossen"

3. Sammle alle relevanten Dateien:
   → Model, alle Analysen, Hypothesen, Wissen, Ergebnisse
   → Zyklus-Historie aus Manifest (alle Iterationen)
```

---

## Schritt 1: Model analysieren → Wissens-Atome extrahieren

```
Lies {NAME}_Model.md und extrahiere atomare Einheiten:

1. WAHRHEITEN (W1-Wn):
   Jede Wahrheit = 1 Wissens-Atom
   → entity_type: "wahrheit"
   → Attribute: Inhalt, Confidence, Quelle (welche Analyse), Datum
   → Beziehungen: gehoert_zu(Model), bestaetigt_durch(Experiment)

2. ARCHITEKTUR-ENTSCHEIDUNGEN:
   Jede AK = 1 Entscheidungs-Atom
   → entity_type: "architektur-entscheidung"
   → Attribute: Entscheidung, Alternativen, Begruendung, Risiko
   → Beziehungen: betrifft(Komponente), widerlegt(Alternative)

3. RISIKEN (identifiziert + aufgeloest):
   → entity_type: "risiko"
   → Status: AUFGELOEST | AKZEPTIERT | OFFEN
   → Beziehungen: betrifft(Komponente), geloest_durch(Wahrheit)

4. KOMPONENTEN-WISSEN:
   Jede im Model beschriebene Komponente = 1 Entity
   → entity_type: "komponente"
   → Attribute: Name, Rolle, Technologie, Einschraenkungen
   → Beziehungen: abhaengig_von(Komponente), konfiguriert_durch(Config)

Ergebnis: Liste von {entities[], relationships[]}
```

---

## Schritt 2: Analysen durchgehen → Anti-Patterns + Irrwege extrahieren

```
Lies ALLE {NAME}-ANALYSE*.md und extrahiere:

1. WIDERSPRUECHE (aufgeloest):
   Stellen an denen sich Agenten widersprachen und die Wahrheit spaeter
   gefunden wurde.
   → entity_type: "anti-pattern"
   → Attribute: Annahme (falsch), Wahrheit (korrekt), Kontext
   → Beispiel: "ServicePointManager ist wirkungslos fuer WCF"
   → Beziehungen: widerlegt(Annahme), bestaetigt(Wahrheit)

2. FEHLDIAGNOSEN:
   Hypothesen die sich als falsch erwiesen haben.
   → entity_type: "fehldiagnose"
   → Attribute: Was angenommen wurde, Warum falsch, Wie entdeckt
   → Beispiel: "SFTP=SSL angenommen, aber SFTP=SSH (anderes Protokoll)"

3. ZEITFRESSER:
   Probleme an denen mehrere Iterationen gearbeitet wurde bevor die
   Loesung gefunden wurde.
   → entity_type: "zeitfresser"
   → Attribute: Problem, Iterationen, Stunden geschaetzt, Ursache
   → Beziehungen: verursacht_durch(Fehldiagnose), geloest_durch(Wahrheit)

4. POSITIV-PATTERNS:
   Ansaetze die besonders gut funktioniert haben.
   → entity_type: "best-practice"
   → Beispiel: "Entity-Provider Pattern als 1:1 Vorlage fuer neue Entities"
   → Beziehungen: anwendbar_in(Kontext)

Ergebnis: Liste von {anti_patterns[], best_practices[], lessons_learned[]}
```

---

## Schritt 3: Hypothesen analysieren → Entscheidungs-Landkarte

```
Lies {NAME}-HYPOTHESEN.md und extrahiere:

1. ENTSCHEIDUNGS-KASKADE:
   Welche Entscheidungen wurden in welcher Reihenfolge getroffen?
   → Jede Entscheidung mit Alternativen, Begruendung, Konfidenz
   → entity_type: "entscheidung"

2. GEGEN-HYPOTHESEN (widerlegt):
   → entity_type: "widerlegte-hypothese"
   → Attribute: Hypothese, Warum widerlegt, Evidenz
   → WICHTIG: Das ist NEGATIVES Wissen - verhindert Wiederholung

3. RISIKO-BEWERTUNGEN:
   Risiken die eingeschaetzt und dann bestaetigt/widerlegt wurden
   → entity_type: "risiko-bewertung"
   → Attribute: Einschaetzung, Ergebnis, Abweichung

Ergebnis: Entscheidungsbaum als Graph-Struktur
```

---

## Schritt 4: Retrospektive-Dokument schreiben

```
Schreibe .claude/analysis/synthese/{NAME}-RETROSPEKTIVE.md:

---
type: retrospektive
feature: {FEATURE}
name: {NAME}
datum: YYYY-MM-DD
zyklen: {Anzahl Iterationen}
status: ABGESCHLOSSEN
---

# Retrospektive: {NAME} ({FEATURE})

## 1. Zusammenfassung
- Problem: {1 Satz}
- Loesung: {1 Satz}
- Iterationen: {N}
- Schluessel-Erkenntnis: {1 Satz}

## 2. Was hat funktioniert (Best Practices)
| # | Pattern | Kontext | Wiederverwendbar? |
|---|---------|---------|-------------------|
| 1 | ... | ... | JA/NEIN |

## 3. Was NICHT funktioniert hat (Anti-Patterns)
| # | Annahme (FALSCH) | Wahrheit | Zeitverlust | Vermeidbar? |
|---|------------------|----------|-------------|-------------|
| 1 | ServicePointManager fuer WCF | WCF eigene Cert-Pipeline | ~3h | JA |
| 2 | SFTP = SSL-Problem | SFTP = SSH (anderes Protokoll) | ~2h | JA |

## 4. Architektur-Entscheidungen (Finale)
| # | Entscheidung | Alternativen | Begruendung |
|---|-------------|-------------|-------------|

## 5. Wissens-Atome (fuer GraphRAG)
| # | Entity | Typ | Global? | Tags |
|---|--------|-----|---------|------|
| 1 | "WCF nutzt eigene Certificate-Pipeline" | wahrheit | JA | wcf, zertifikate |
| 2 | "MinIO ist S3-kompatibel" | wahrheit | JA | minio, s3 |
| 3 | ... | ... | ... | ... |

## 6. Offene Fragen / Technische Schulden
- {Aus Manifest Backlog-Sektion}

## 7. Empfehlung fuer naechstes Feature
- {Was wuerden wir anders machen?}
```

---

## Schritt 5: GraphRAG einspeisen

```
Falls NICHT --dry-run:

1. LOKALE COLLECTION ({FEATURE}):
   → Alle Entities aus Schritt 1-3 einspeisen
   → Relationships zwischen Entities anlegen
   → Tags vergeben (topic/, type/)

2. GLOBALE COLLECTION:
   → NUR Entities die als "Global? = JA" markiert sind
   → NUR verifizierte Wahrheiten (Confidence >= 90%)
   → NUR Anti-Patterns (IMMER global - verhindert Wiederholung)
   → NUR Best-Practices (IMMER global - foerdert Wiederverwendung)
   → Komponenten-Wissen NUR wenn technologie-uebergreifend

3. NEGATIV-GEDAECHTNIS (Spezial-Tag in Global):
   → Alle Anti-Patterns mit tag: "negativ"
   → Alle Fehldiagnosen mit tag: "negativ"
   → Alle widerlegten Hypothesen mit tag: "negativ"
   → Zweck: Bei zukuenftigen Analysen querybar
     "Gab es schon mal Probleme mit WCF + SSL?"
     → "JA: ServicePointManager ist wirkungslos (DCSRE-881)"

4. MCP-Tool-Aufrufe:
   → graphrag_ingest_entities(collection, entities[])
   → graphrag_create_relationships(collection, relationships[])
   → graphrag_tag_entities(collection, entity_ids[], tags[])
```

---

## Schritt 6: Manifest aktualisieren + Zusammenfassung

```
1. Manifest aktualisieren:
   → Zyklus-Historie: Retrospektive-Eintrag hinzufuegen
   → Status: "RETROSPEKTIVE ABGESCHLOSSEN"

2. Zusammenfassung ausgeben:

/_retrospektive {FEATURE} - Ergebnis:

| Kategorie | Extrahiert | Lokal | Global |
|-----------|-----------|-------|--------|
| Wahrheiten | {N} | {N} | {N} (>= 90% Confidence) |
| Anti-Patterns | {N} | {N} | {N} (ALLE) |
| Best-Practices | {N} | {N} | {N} (ALLE) |
| Architektur-Entscheidungen | {N} | {N} | {N} |
| Komponenten | {N} | {N} | {N} |
| Widerlegte Hypothesen | {N} | {N} | {N} (ALLE → negativ) |
| Risiken (aufgeloest) | {N} | {N} | 0 |

Retrospektive: .claude/analysis/synthese/{NAME}-RETROSPEKTIVE.md
GraphRAG Lokal: {FEATURE} Collection ({N} Entities, {N} Relationships)
GraphRAG Global: {N} neue Entities, {N} neue Relationships
Negativ-Gedaechtnis: {N} Eintraege (querybar via tag: "negativ")
```

---

## Qualitaetskriterien

- **Atomaritaet:** Jedes Entity enthaelt genau EINE Erkenntnis, nicht mehrere
- **Querybarkeit:** Entities muessen per Freitext-Suche auffindbar sein
- **Negativ-Bias:** Anti-Patterns IMMER global einspeisen (wichtiger als Positives)
- **Quellennachweis:** Jedes Entity verweist auf das Quell-Dokument
- **Idempotenz:** Mehrfaches Ausfuehren ueberschreibt, dupliziert nicht

---

## Voraussetzungen

- Feature muss mindestens 1x /_SC_ergebnis mit GELOEST durchlaufen haben
- GraphRAG MCP muss verfuegbar sein (sonst: nur Retrospektive-Dokument schreiben)
- Falls MCP nicht verfuegbar: Retrospektive-Dokument als Standalone nutzbar
  (manuelles Einspeisen spaeter moeglich)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_retrospektive abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
